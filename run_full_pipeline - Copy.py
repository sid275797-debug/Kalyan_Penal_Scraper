#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
v10pipeline.py — FINAL VERSION (Engine writes directly to Flutter assets)
- No predictions inside /output/
- Only predictions: Android assets/todays_predictions.json
- Pipeline reads that file ONLY
- Pushes same file to Firebase
"""

from __future__ import annotations
import os, sys, json, subprocess, traceback, random, datetime, re, shutil
from pathlib import Path
from typing import Any, List, Dict, Tuple

# ---------- Console encoding fix ----------
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------- CONFIG ----------
ROOT = Path(__file__).parent.resolve()
PYTHON = sys.executable

RUN_SCRAPER    = True
RUN_AGGREGATOR = True
RUN_BUILD      = True
RUN_YESTERDAY  = True
RUN_DNA        = True
RUN_ENGINE     = True
RUN_SCORE      = False
RUN_AUTOTUNE   = False



# ---------- SCRAPER ----------
SCRAPER_CANDIDATES = [
    [PYTHON, "multi_market_scraperrr.py"],
    [PYTHON, str(ROOT / "scripts" / "multi_market_scraperrr.py")],
    [PYTHON, str(ROOT / "tools"   / "multi_market_scraperrr.py")],
    [str(ROOT / "multi_market_scraperrr.bat")],
    [str(ROOT / "scripts" / "multi_market_scraperrr.bat")],
    [str(ROOT / "tools"   / "multi_market_scraperrr.bat")],
]


# ==========================================
# MAIN SOURCE OF TRUTH (Flutter app assets)
# ==========================================
ASSETS_TODAY = Path(
    r"C:\Users\VCOM\AndroidStudioProjects\multi_market_predictions_v3\assets\todays_predictions.json"
)

ASSETS_DIR = ASSETS_TODAY.parent

# Other pipeline files
DATA_DIR     = ROOT / "output"
HISTORY_JSON = DATA_DIR / "all_markets_history.json"
YEST_JSON    = DATA_DIR / "yesterday_results.json"
SCORE_JSON   = DATA_DIR / "prediction_score_report.json"
ARCHIVE_DIR  = DATA_DIR / "history"

# Firebase nodes
NODE_TODAY     = "app_data/todays_predictions"
NODE_YESTERDAY = "app_data/yesterday_results"
NODE_SCORE     = "app_data/prediction_score_report"
NODE_PARAMS    = "app_data/params"

# Firebase key
DEFAULT_KEY_PATH   = ROOT / "firebase" / "serviceAccountKey.json"
FIREBASE_RTDB_URL  = os.environ.get(
    "FIREBASE_RTDB_URL",
    "https://sattamatkaai-77102-default-rtdb.firebaseio.com"
)

# ---------- UTILS ----------
def log(*a): print("▶", *a, flush=True)

UNICODE_ERR_RE = re.compile(
    r"UnicodeEncodeError: 'charmap'.*cp1252.*\\u2705", re.IGNORECASE
)

def run(cmd: List[str]) -> Tuple[int, bool]:
    new_cmd = list(cmd)
    exe = os.path.basename(new_cmd[0]).lower()

    if exe.startswith("python"):
        inject = []
        if len(new_cmd) < 2 or new_cmd[1] != "-X":
            inject += ["-X", "utf8"]
        if "-u" not in new_cmd[:3]:
            inject += ["-u"]
        new_cmd = [new_cmd[0]] + inject + new_cmd[1:]

    log("Running:", " ".join(new_cmd))
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    p = subprocess.Popen(
        new_cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env,
    )
    assert p.stdout
    ign = False
    for line in p.stdout:
        sys.stdout.write(line.rstrip() + "\n")
        if UNICODE_ERR_RE.search(line):
            ign = True
    return p.wait(), ign

def load_json(p: Path):
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(p: Path, obj: Any):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def utc_iso(): 
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

# ---------- ENGINE (v10 / v8 / v5) ----------
ENGINE_CANDIDATES = [
    [PYTHON, "v10.py"],
    [PYTHON, str(ROOT / "v10.py")],
    [PYTHON, str(ROOT / "engine" / "v10.py")],
    [PYTHON, r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\v10.py"],

    [PYTHON, "v8.py"],
    [PYTHON, str(ROOT / "v8.py")],
    [PYTHON, str(ROOT / "engine" / "v8.py")],
    [PYTHON, r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\v8.py"],

    [PYTHON, "prediction_engine_v5.py"],
    [PYTHON, str(ROOT / "prediction_engine_v5.py")],
    [PYTHON, str(ROOT / "engine" / "prediction_engine_v5.py")],
    [PYTHON, r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\prediction_engine_v5.py"],
]

# --------------------------------------------
# This is the ONLY source of predictions now:
# --------------------------------------------
ENGINE_SOURCES = [ASSETS_TODAY]

def _is_valid_predictions_file(p: Path) -> bool:
    try:
        if not p.exists() or p.stat().st_size == 0:
            return False
        j = load_json(p)
        if not isinstance(j, dict): return False
        if not isinstance(j.get("markets"), list): return False
        if len(j["markets"]) == 0: return False
        return True
    except Exception:
        return False

def _run_engine():
    for cmd in ENGINE_CANDIDATES:
        code, ign = run(cmd)
        if code == 0:
            log("Engine completed.")
            return
    raise RuntimeError("No engine succeeded (v10/v8/v5).")

def _confirm_engine_output():
    if not _is_valid_predictions_file(ASSETS_TODAY):
        raise RuntimeError(f"Engine did not write a valid file: {ASSETS_TODAY}")
    log("Engine output confirmed:", ASSETS_TODAY)

# ---------- HISTORY / DNA ----------
def step_scrape():
    for cmd in SCRAPER_CANDIDATES:
        code, ign = run(cmd)
        if code == 0:
            log("Scraper done.")
            return
    raise RuntimeError("All scrapers failed.")

def step_aggregate():
    code, ign = run([PYTHON, "aggregate_history.py"])
    if code != 0:
        raise RuntimeError("aggregate_history failed")

def step_build_history():
    script = ROOT / "build_history_json.py"
    if not script.exists():
        log("build_history_json.py not found — skipping.")
        return

    code, ign = run([PYTHON, "build_history_json.py"])
    if code != 0:
        if HISTORY_JSON.exists():
            log("build_history_json failed, but history exists — continuing.")
            return
        raise RuntimeError("build_history_json failed")

def step_generate_yesterday():
    script = ROOT / "generate_yesterday_results.py"
    if script.exists():
        code, ign = run([PYTHON, "generate_yesterday_results.py"])
        if code != 0:
            raise RuntimeError("generate_yesterday failed")

def step_market_dna():
    cmd = [
        PYTHON, "market_dna_builder.py",
        "--history", str(HISTORY_JSON),
        "--out",     str(DATA_DIR / "market_dna.json")
    ]
    code, ign = run(cmd)
    if code != 0:
        raise RuntimeError("market_dna_builder failed")
    log("Market DNA build completed.")

def step_score():
    code, ign = run([PYTHON, "score_only_json_verbose.py"])
    if code != 0:
        raise RuntimeError("score failed")

def step_autotune():
    code, ign = run([PYTHON, "auto_tune_params.py"])
    if code != 0:
        raise RuntimeError("autotune failed")

# ---------- FIREBASE ----------
_fb = False

def _find_key():
    envp = os.environ.get("FIREBASE_ADMIN_KEY")
    if envp and Path(envp).exists():
        return Path(envp)

    for p in [
        ROOT / "firebase" / "serviceAccountKey.json",
        ROOT / "serviceAccountKey.json"
    ]:
        if p.exists():
            return p

    return DEFAULT_KEY_PATH

def rtdb_init():
    global _fb
    if _fb:
        return
    import firebase_admin
    from firebase_admin import credentials
    key = _find_key()
    firebase_admin.initialize_app(
        credentials.Certificate(str(key)),
        {"databaseURL": FIREBASE_RTDB_URL}
    )
    _fb = True

def rtdb_set(path, obj):
    rtdb_init()
    from firebase_admin import db
    db.reference(path).set(obj)
    log("Pushed:", path)

# ---------- MAIN ----------
def main():
    try:
        log("ROOT:", ROOT)

        if RUN_SCRAPER:    step_scrape()
        if RUN_AGGREGATOR: step_aggregate()
        if RUN_BUILD:      step_build_history()
        if RUN_YESTERDAY:  step_generate_yesterday()
        if RUN_DNA:        step_market_dna()
        if RUN_ENGINE:
            _run_engine()
            _confirm_engine_output()
        if RUN_SCORE:      step_score()
        if RUN_AUTOTUNE:   step_autotune()

        log("Skipping history upload — internal use only.")

        # ===== PUSH TODAY =====
        if _is_valid_predictions_file(ASSETS_TODAY):
            # Backup
            bak = ASSETS_DIR / f"backup_todays_predictions_{datetime.date.today().isoformat()}.json"
            if not bak.exists():
                shutil.copy2(ASSETS_TODAY, bak)
                log("Backup saved:", bak)

            predictions = load_json(ASSETS_TODAY)
            rtdb_set(NODE_TODAY, predictions)
        else:
            log("TODAY JSON invalid — NOT PUSHING.")

        # ===== PUSH YESTERDAY =====
        if YEST_JSON.exists():
            rtdb_set(NODE_YESTERDAY, load_json(YEST_JSON))

        # ===== PUSH SCORE =====
        if SCORE_JSON.exists():
            rtdb_set(NODE_SCORE, load_json(SCORE_JSON))

        # ===== PUSH PARAMS =====
        for f in [
            ROOT / "data" / "auto_tuned_params.json",
            ROOT / "data" / "params.json",
            ROOT / "data" / "market_params.json",
        ]:
            if f.exists():
                rtdb_set(NODE_PARAMS, load_json(f))
                break

        log("Pipeline completed successfully.")
        return 0

    except Exception as e:
        log("Pipeline crashed:", e)
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
