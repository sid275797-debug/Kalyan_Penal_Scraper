#!/usr/bin/env python3
# reels_premium_builder.py
# Unified script: generates videos for ALL markets (premium + free) by default.
# Preserves original visuals & behavior; toggle via GENERATE_ALL_MARKETS.

import os, re, json, math, datetime, glob, sys
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Robust MoviePy imports (works across versions)
try:
    from moviepy.video.VideoClip import ImageClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.video.io.ffmpeg_tools import ffmpeg_merge_video_audio
except Exception:
    try:
        from moviepy import ImageClip, AudioFileClip, CompositeVideoClip
    except Exception as e:
        raise ImportError("MoviePy not importable. Install moviepy or use compatible version. Err: " + str(e))

# ---------------- CONFIG ----------------
BASE_DIR    = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper"
JSON_PATH   = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\output\todays_predictions.json"
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
MUSIC_DIR   = os.path.join(BASE_DIR, "music")
LOGO_PATH   = os.path.join(ASSETS_DIR, "logo.png")
OUT_ROOT    = os.path.join(BASE_DIR, "video_output")

PREFERRED_MUSIC_NAME = "bgm.mp3"
AUDIO_EXTS = (".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac")

# Visual params (copied from working script)
W, H = 1080, 1920
FPS = 30
PER_MARKET_SECONDS = 15
ZOOM_START, ZOOM_END = 1.00, 1.06

PAD  = 84
SAFE_TOP, SAFE_BOTTOM = 100, 170
BG_TOP=(5,6,10); BG_BOT=(2,2,5)
WHITE=(255,255,255); DIM=(222,226,234)
CYAN=(0,229,255); MAGENTA=(255,29,206); YELLOW=(255,214,51)
CARD_BG=(12,14,22,230); CARD_ST=(0,229,255,60)
PILL_BG=(8,10,16,230);  PILL_ST=(0,229,255,220)

PRIMARY_FONT_CANDS = [
    r"C:\Windows\Fonts\Orbitron-Bold.ttf",
    r"C:\Windows\Fonts\AUDIOWIDE-REGULAR.TTF",
    r"C:\Windows\Fonts\Exo2-Bold.ttf",
    r"C:\Windows\Fonts\Montserrat-Bold.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
]
SECONDARY_FONT_CANDS = [
    r"C:\Windows\Fonts\Exo2-Regular.ttf",
    r"C:\Windows\Fonts\Montserrat-Regular.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
]

BASE = {
    "title": 68, "date": 50, "tag": 46,
    "open": 136, "close": 136,
    "jodi": 64, "chip_h": 96, "chip_gap": 18, "chip_pad_x": 40,
    "pill": 42, "pill_h": 72, "pill_gap": 14,
    "pad": 24, "gap_s": 12, "gap_m": 22, "gap_l": 28
}
LIMITS = {"jodi_cap": 10, "pill_cap": 12}

# Premium detection & fallback (kept)
FORCE_PREMIUM_KEYWORDS = (
    "kalyan","rajdhani","milan",
    "time bazar","timebazar","time-bazar","time bazaar","timebazaar",
    "main bazar","mainbazar","main-bazar","main bazaar","mainbazaar",
    "starline","supreme"
)
AUTO_PICK_IF_NO_PREMIUM = True
AUTO_PICK_N = 6
GENERATE_VERTICAL_SHORT = False

# NEW: generate all markets toggle
GENERATE_ALL_MARKETS = True  # <-- SET True to render every market; False to use premium-only behavior

# Exclude list file
EXCLUDE_FILE = os.path.join(ASSETS_DIR, "exclude_markets.txt")

# ===== helpers (copied & small robust additions) =====
def ensure_dir(p):
    if p: os.makedirs(p, exist_ok=True)

def load_font(cands, size):
    for fp in cands:
        if os.path.exists(fp):
            try: return ImageFont.truetype(fp, size)
            except: pass
    return ImageFont.load_default()

def tw(draw, font, s):
    try: return int(draw.textlength(s, font=font))
    except Exception:
        try: return int(font.getsize(s)[0])
        except: return len(s)*10

def th(font):
    try: b = font.getbbox("Hg0123456789"); return int(b[3] - b[1])
    except Exception:
        try: a, d = font.getmetrics(); return int(a + d)
        except: return 24

def bg_make(size):
    w,h = size
    t = np.linspace(0,1,h)[:,None,None]
    top = np.array(BG_TOP,dtype=np.float32)[None,None,:]
    bot = np.array(BG_BOT,dtype=np.float32)[None,None,:]
    grad = top*(1-t)+bot*t
    arr = np.repeat(grad,w,axis=1).astype(np.uint8)
    img = Image.fromarray(arr,mode="RGB").convert("RGBA")
    sl=Image.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(sl)
    for yy in range(0,h,10): d.line([(0,yy),(w,yy)], fill=(255,255,255,12), width=1)
    img.alpha_composite(sl); return img

def glow_text(canvas, draw, xy, text, font, fill, glow, radius=6):
    if not text: return
    g = Image.new("RGBA", canvas.size, (0,0,0,0))
    gd = ImageDraw.Draw(g)
    try:
        gd.text(xy, text, font=font, fill=(glow[0],glow[1],glow[2],255))
        g = g.filter(ImageFilter.GaussianBlur(radius))
        canvas.alpha_composite(g)
    except Exception:
        pass
    draw.text(xy, text, font=font, fill=fill)

def rounded_rect_on(canvas, xy, radius, fill, outline=None, width=2, blur=0):
    tmp = Image.new("RGBA", canvas.size, (0,0,0,0))
    td = ImageDraw.Draw(tmp)
    td.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    if blur: tmp = tmp.filter(ImageFilter.GaussianBlur(4))
    canvas.alpha_composite(tmp)

def clean_market_title(s: str) -> str:
    s = (s or "").replace("_"," ")
    s = re.sub(r"(?:\bpanel\b|\bpenal\b|\bchart\b)", "", s, flags=re.I)
    s = re.sub(r"\s{2,}"," ", s).strip()
    return s.upper()

def norm_key(s: str) -> str: return re.sub(r'[^a-z0-9]+','', (s or '').lower())

def listify(v):
    if v is None: return []
    if isinstance(v, list): return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, (int,float)): return [str(v)]
    if isinstance(v, str): return [p for p in re.split(r'[,\s]+', v.strip()) if p]
    return [str(v)]

def flatten_shallow(d: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten one or more nested layers of predictions-like dicts."""
    flat = dict(d)
    for _ in range(3):  # try multiple layers deep
        new_items = {}
        for k, v in list(flat.items()):
            if isinstance(v, dict) and norm_key(k) in ("predictions","data","result","values","payload"):
                for k2, v2 in v.items():
                    if k2 not in flat:
                        new_items[k2] = v2
        if not new_items:
            break
        flat.update(new_items)
    return flat





def extract_field_strict(flat: Dict[str, Any], aliases: List[str]) -> List[str]:
    """Exact-key lookup only; ignores dict values to avoid whole-payload leaks."""
    table = {norm_key(k): k for k in flat.keys()}
    for alias in aliases:
        n = norm_key(alias)
        if n in table:
            v = flat[table[n]]
            if isinstance(v, dict):   # guard: never return nested dicts
                continue
            return listify(v)
    return []

def clamp_digits(items: List[str], max_len: int = 4) -> List[str]:
    """Return up to max_len single-digit strings."""
    out = []
    for x in listify(items):
        s = str(x).strip()
        if len(s) == 1 and s.isdigit():
            out.append(s)
        elif s.isdigit():             # e.g., "123" -> "1","2","3"
            out.extend(list(s))
        if len(out) >= max_len:
            break
    return out[:max_len]









def auto_fit_font(draw, cands, base_size, text, max_width, min_size=36, step=2):
    size = base_size
    while size > min_size:
        f = load_font(cands, size)
        if tw(draw, f, text) <= max_width: return f
        size -= step
    return load_font(cands, max(min_size, 24))

def load_excluded_markets() -> set:
    names = set()
    try:
        if os.path.exists(EXCLUDE_FILE):
            with open(EXCLUDE_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if s: names.add(s.lower())
    except Exception:
        pass
    return names

def is_premium_entry(flat: Dict[str, Any]) -> bool:
    for k in ("premium","is_premium","vip"):
        if k in flat and str(flat[k]).lower() in ("1","true","yes","y"):
            return True
    if str(flat.get("tier","")).lower() in ("premium","vip","gold"):
        return True
    name = str(flat.get("market") or flat.get("market_name") or "").lower()
    if any(kw in name for kw in ("premium","vip")): return True
    return False

def _list_audio(dir_path: str) -> List[str]:
    try:
        if not os.path.isdir(dir_path): return []
        return [os.path.join(dir_path, fn) for fn in os.listdir(dir_path) if fn.lower().endswith(AUDIO_EXTS)]
    except Exception:
        return []

def pick_music_path() -> Optional[str]:
    if os.path.isdir(MUSIC_DIR):
        pref = os.path.join(MUSIC_DIR, PREFERRED_MUSIC_NAME)
        if os.path.exists(pref): return pref
        cands = _list_audio(MUSIC_DIR)
        if cands:
            ranked = sorted(cands, key=lambda p: (not any(k in os.path.basename(p).lower() for k in ("bgm","music","beat","loop")), os.path.basename(p).lower()))
            return ranked[0]
    if os.path.isdir(ASSETS_DIR):
        pref = os.path.join(ASSETS_DIR, PREFERRED_MUSIC_NAME)
        if os.path.exists(pref): return pref
        cands = _list_audio(ASSETS_DIR)
        if cands:
            ranked = sorted(cands, key=lambda p: (not any(k in os.path.basename(p).lower() for k in ("bgm","music","beat","loop")), os.path.basename(p).lower()))
            return ranked[0]
    return None

# ===== Slide drawing (unchanged) =====
def draw_header_centered(canvas, d, y, title_txt, date_txt):
    date_f = auto_fit_font(d, PRIMARY_FONT_CANDS, BASE["date"], date_txt, W - 2*PAD, min_size=38)
    date_w = tw(d, date_f, date_txt)
    glow_text(canvas, d, ((W - date_w)//2, y), date_txt, date_f, DIM, MAGENTA, 5)
    y += th(date_f) + 10

    title_f = auto_fit_font(d, PRIMARY_FONT_CANDS, BASE["title"], title_txt, W - 2*PAD, min_size=40)
    t_w = tw(d, title_f, title_txt)
    glow_text(canvas, d, ((W - t_w)//2, y), title_txt, title_f, WHITE, CYAN, 8)
    y += th(title_f) + BASE["gap_m"]
    return y

def measure_digits_uniform(draw, font, digits: List[str], tracking: int) -> Tuple[int,int,int]:
    h = th(font)
    samples = [str(x) for x in digits if str(x).strip()] or ["0"]
    max_w = max(tw(draw, font, ch) for ch in samples + list("0123456789"))
    block_w = len(samples)*max_w + (len(samples)-1)*tracking
    return block_w, h, max_w

def draw_digits_row_centered(canvas, d, y, label: str, digits: List[str], base_size: int, tracking: int = 30):
    digits = [str(x) for x in digits if str(x).strip()] or ["—","—","—","—"]
    size = base_size
    while size >= 96:
        f = load_font(PRIMARY_FONT_CANDS, size)
        block_w, block_h, box_w = measure_digits_uniform(d, f, digits, tracking)
        if block_w <= (W - 2*PAD): break
        size -= 4
    f = load_font(PRIMARY_FONT_CANDS, size)

    tag_f = load_font(PRIMARY_FONT_CANDS, BASE["tag"])
    lbl_w = tw(d, tag_f, label)
    glow_text(canvas, d, ((W - lbl_w)//2, y), label, tag_f, DIM, WHITE, 4)
    y += th(tag_f) + BASE["gap_s"] + 2

    block_w, block_h, box_w = measure_digits_uniform(d, f, digits, tracking)
    start_x = (W - block_w)//2
    row_y = y
    x = start_x
    for i, ch in enumerate(digits):
        g_w = tw(d, f, ch)
        gx = x + (box_w - g_w)//2
        glow_text(canvas, d, (gx, row_y), ch, f, WHITE, WHITE, 6)
        x += box_w
        if i < len(digits) - 1:
            x += tracking

    return row_y + block_h + BASE["gap_l"]

def draw_jodi_flow(canvas, d, y, chips: List[str]):
    tag_f = load_font(PRIMARY_FONT_CANDS, BASE["tag"])
    ttl = "JODI"
    ttl_w = tw(d, tag_f, ttl)
    glow_text(canvas, d, ((W - ttl_w)//2, y), ttl, tag_f, DIM, YELLOW, 4)
    y += th(tag_f) + BASE["gap_s"]

    inner_w = W - 2*PAD
    chip_f = load_font(PRIMARY_FONT_CANDS, BASE["jodi"])
    pad_x = BASE["chip_pad_x"]; gap = BASE["chip_gap"]; h = BASE["chip_h"]

    chips = chips or ["—"]
    if len(chips) > LIMITS["jodi_cap"]:
        chips = chips[:LIMITS["jodi_cap"]] + [f"+{len(chips)-LIMITS['jodi_cap']} MORE"]

    chip_w = [tw(d, chip_f, s) + 2*pad_x for s in chips]
    rows: List[List[Tuple[str,int]]] = [[]]
    used = 0
    for s, w in zip(chips, chip_w):
        if not rows[-1]:
            rows[-1].append((s, min(w, inner_w))); used = min(w, inner_w)
        else:
            if used + gap + w <= inner_w:
                rows[-1].append((s, w)); used += gap + w
            else:
                if len(rows) == 2: break
                rows.append([]); used = 0
                rows[-1].append((s, min(w, inner_w))); used = min(w, inner_w)

    for r_i, row in enumerate(rows):
        if not row: continue
        row_w = sum(w for _,w in row) + gap*(len(row)-1)
        x = PAD + (inner_w - row_w)//2
        for s, w in row:
            rect = (x, y, x+w, y+h)
            rounded_rect_on(canvas, rect, 36, PILL_BG, PILL_ST, 2, blur=4)
            glow_text(canvas, d, (x + (w - tw(d, chip_f, s))//2,
                                  y + (h - th(chip_f))//2), s, chip_f, WHITE, CYAN, 3)
            x += w + gap
        y += h + (BASE["chip_gap"] if r_i < len(rows)-1 else BASE["gap_l"])
    return y

def render_slide(entry: Dict[str, Any], date_str: str) -> Image.Image:
    canvas = bg_make((W,H)); d = ImageDraw.Draw(canvas,"RGBA")
    title_txt = clean_market_title(entry.get("market") or entry.get("market_name") or "MARKET")
    date_txt  = f"DATE: {date_str}"

    y = SAFE_TOP
    y = draw_header_centered(canvas, d, y, title_txt, date_txt)
    y = draw_digits_row_centered(canvas, d, y, "OPEN",  entry.get("open_digits",  ["—","—","—","—"]), base_size=BASE["open"],  tracking=30)
    y = draw_digits_row_centered(canvas, d, y, "CLOSE", entry.get("close_digits", ["—","—","—","—"]), base_size=BASE["close"], tracking=30)
    y = draw_jodi_flow(canvas, d, y, entry.get("jodis", ["—"]))

    # PANNA card
    tag_f = load_font(PRIMARY_FONT_CANDS, BASE["tag"])
    open_list  = (entry.get("open_pannas")  or ["—"])[:LIMITS["pill_cap"]]
    close_list = (entry.get("close_pannas") or ["—"])[:LIMITS["pill_cap"]]

    card_left, card_right = PAD, W - PAD
    inner_l = card_left + BASE["pad"]; inner_r = card_right - BASE["pad"]
    inner_w2 = inner_r - inner_l
    col_w2 = (inner_w2 - BASE["pill_gap"]) // 2

    rows_o = max(1, math.ceil(len(open_list)/2))
    rows_c = max(1, math.ceil(len(close_list)/2))
    tag_h  = th(tag_f)
    card_h = (BASE["pad"] + tag_h + BASE["gap_s"] +
              rows_o*BASE["pill_h"] + (rows_o-1)*BASE["pill_gap"] +
              BASE["gap_m"] + 1 + BASE["gap_m"] +
              tag_h + BASE["gap_s"] +
              rows_c*BASE["pill_h"] + (rows_c-1)*BASE["pill_gap"] +
              BASE["pad"])

    rounded_rect_on(canvas, (card_left, y, card_right, y+card_h), 28, CARD_BG, CARD_ST, 2, blur=0)
    pill_f = load_font(SECONDARY_FONT_CANDS, BASE["pill"])
    yy = y + BASE["pad"]

    def draw_pills(items: List[str], title: str, yy: int) -> int:
        glow_text(canvas, d, (inner_l, yy), title, tag_f, DIM, CYAN, 4)
        yy += tag_h + BASE["gap_s"]
        if len(items) % 2: items += [""]
        xL = inner_l; xR = inner_l + col_w2 + BASE["pill_gap"]
        for i in range(0, len(items), 2):
            a, b = items[i], items[i+1]
            rounded_rect_on(canvas, (xL, yy, xL+col_w2, yy+BASE["pill_h"]), 26, PILL_BG, PILL_ST, 2, blur=4)
            if a:
                glow_text(canvas, d, (xL+(col_w2 - tw(d, pill_f, a))//2, yy+(BASE["pill_h"]-th(pill_f))//2), a, pill_f, WHITE, CYAN, 3)
            rounded_rect_on(canvas, (xR, yy, xR+col_w2, yy+BASE["pill_h"]), 26, PILL_BG, PILL_ST, 2, blur=4)
            if b:
                glow_text(canvas, d, (xR+(col_w2 - tw(d, pill_f, b))//2, yy+(BASE["pill_h"]-th(pill_f))//2), b, pill_f, WHITE, CYAN, 3)
            yy += BASE["pill_h"] + BASE["pill_gap"]
        return yy

    yy = draw_pills(open_list, "OPEN PANNA", yy)
    d.line([(inner_l, yy + BASE["gap_m"]//2), (inner_r, yy + BASE["gap_m"]//2)], fill=(255,255,255,42), width=1)
    yy += BASE["gap_m"] + 1 + BASE["gap_m"]//2
    yy = draw_pills(close_list, "CLOSE PANNA", yy)

    # watermark logo (optional)
    if os.path.exists(LOGO_PATH):
        try:
            raw = Image.open(LOGO_PATH).convert("RGBA")
            w0,h0=raw.size; scale=100/max(1,h0)
            logo=raw.resize((int(w0*scale), int(h0*scale)), Image.LANCZOS)
            canvas.alpha_composite(logo, (W-PAD-logo.size[0], H-PAD-logo.size[1]))
        except: pass

    return canvas

# ===== Data load & selection (modified: optionally include all markets) =====

def load_entries() -> List[Dict[str, Any]]:
    """
    Production loader for v4 engine outputs.
    - Reads ONLY from /output folder.
    - Auto-selects latest .json file.
    - Parses structure: { "meta":{}, "markets":[ {"market":..,"predictions":{...}} ] }
    """

    OUTPUT_DIR = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\output"

    # --- Strictly pick JSON from /output ---
    try:
        files = [os.path.join(OUTPUT_DIR, f) for f in os.listdir(OUTPUT_DIR) if f.lower().endswith(".json")]
        if not files:
            raise SystemExit(f"❌ No JSON files found in {OUTPUT_DIR}")
        JSON_PATH = max(files, key=os.path.getmtime)  # latest one
        print(f"📄 Using latest prediction JSON → {os.path.basename(JSON_PATH)}")
    except Exception as e:
        raise SystemExit(f"❌ Failed to locate JSON in {OUTPUT_DIR}: {e}")

    # --- Load data ---
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    exclude_names = load_excluded_markets()
    entries: List[Dict[str, Any]] = []

    # --- Select iterable (v4 = markets) ---
    if isinstance(raw, dict) and isinstance(raw.get("markets"), list):
        iterable = raw["markets"]
    elif isinstance(raw, dict) and isinstance(raw.get("data"), list):
        iterable = raw["data"]
    elif isinstance(raw, list):
        iterable = raw
    else:
        iterable = [v for v in raw.values() if isinstance(v, dict)]

    # --- Extract each market prediction ---
    for v in iterable:
        if not isinstance(v, dict):
            continue

        market = (v.get("market") or v.get("market_name") or "").strip()
        if not market or market.lower() in exclude_names:
            continue

        # nested predictions dict
        pred = v.get("predictions") if isinstance(v.get("predictions"), dict) else {}

        # merge for strict extractor
        flat: Dict[str, Any] = {"market": market}
        for k, val in pred.items():
            flat[k] = val

        open_digits = clamp_digits(
            extract_field_strict(flat, ["Open Digits", "Open Digit", "open_digits", "open_digit", "openDigits"]), 4
        )
        close_digits = clamp_digits(
            extract_field_strict(flat, ["Close Digits", "Close Digit", "close_digits", "close_digit", "closeDigits"]), 4
        )
        jodis = extract_field_strict(flat, ["Jodis", "Jodi", "jodis", "jodi"])[:LIMITS["jodi_cap"]]
        open_pannas = extract_field_strict(flat, ["Open Pannas", "Open Panna", "open_pannas", "open_panna", "openPanna"])[:LIMITS["pill_cap"]]
        close_pannas = extract_field_strict(flat, ["Close Pannas", "Close Panna", "close_pannas", "close_panna", "closePanna"])[:LIMITS["pill_cap"]]

        if not any([open_digits, close_digits, jodis, open_pannas, close_pannas]):
            print(f"⚠️ Empty payload for {market} | keys={list(flat.keys())}")

        entries.append({
            "market": market,
            "open_digits": open_digits or ["—"],
            "close_digits": close_digits or ["—"],
            "jodis": jodis or ["—"],
            "open_pannas": open_pannas or ["—"],
            "close_pannas": close_pannas or ["—"],
            "is_premium": is_premium_entry(flat),
        })

    # --- Final filtering ---
    if not entries:
        print("⚠️ No valid entries parsed from prediction JSON.")

    if not GENERATE_ALL_MARKETS:
        premium_entries = [e for e in entries if e.get("is_premium")]
        if premium_entries:
            entries = premium_entries
        elif AUTO_PICK_IF_NO_PREMIUM:
            print(f"⚠️ No premium entries found; auto-picking {AUTO_PICK_N}")
            entries = sorted(entries, key=lambda x: (x.get("market") or "").upper())[:AUTO_PICK_N]

    entries.sort(key=lambda e: (e.get("market") or "").upper())

    print(f"✅ Loaded {len(entries)} entries from {os.path.basename(JSON_PATH)}")
    if entries:
        sample = entries[0]
        print(f"Example → {sample['market']} | Open: {sample['open_digits']} | Jodi: {sample['jodis']}")
    return entries




# ===== Ken-burns + compatibility helpers (unchanged) =====
def _ensure_even_image(img_pil: Image.Image) -> Image.Image:
    w,h = img_pil.size
    add_w = 1 if (w % 2) != 0 else 0
    add_h = 1 if (h % 2) != 0 else 0
    if add_w == 0 and add_h == 0: return img_pil
    new_w, new_h = w + add_w, h + add_h
    bg = Image.new("RGB", (new_w, new_h), (0,0,0))
    paste_x = (new_w - w)//2; paste_y = (new_h - h)//2
    bg.paste(img_pil, (paste_x, paste_y))
    return bg

def _set_duration(clip, duration):
    if hasattr(clip,"set_duration"):
        try: return clip.set_duration(duration)
        except Exception: pass
    if hasattr(clip,"with_duration"):
        try: return clip.with_duration(duration)
        except Exception: pass
    try: clip.duration = duration
    except: pass
    return clip

def _set_fps(clip, fps):
    if hasattr(clip, "set_fps"):
        try: return clip.set_fps(fps)
        except Exception: pass
    if hasattr(clip, "with_fps"):
        try: return clip.with_fps(fps)
        except Exception: pass
    return clip

def _resize_clip(clip, size):
    if hasattr(clip, "resize"):
        try:
            return clip.resize(newsize=size)
        except TypeError:
            try: return clip.resize(size)
            except: pass
    if hasattr(clip, "resized"):
        try: return clip.resized(size)
        except TypeError:
            try: return clip.resized(newsize=size)
            except: pass
    try:
        from moviepy.video.fx import resize as vfx_resize
        try: return vfx_resize(clip, newsize=size)
        except TypeError: return vfx_resize(clip, size)
    except Exception:
        pass
    return clip

def ken_burns_zoom(clip, start=1.0, end=1.05):
    dur = max(getattr(clip, "duration", 1.0), 1e-6)
    def scale(t): return start + (end - start) * (t / dur)
    try:
        zoomed = clip.resized(lambda t: scale(t)).with_duration(clip.duration).with_fps(FPS)
    except Exception:
        try:
            clip = _set_duration(clip, clip.duration)
            clip = _resize_clip(clip, (W, H))
            zoomed = clip.resize(lambda t: scale(t))
            zoomed = _set_fps(zoomed, FPS)
        except Exception:
            zoomed = clip
    bg = ImageClip(np.zeros((H, W, 3), dtype=np.uint8)).with_duration(clip.duration).with_fps(FPS)
    try:
        return CompositeVideoClip([bg, zoomed.with_position(("center","center"))], size=(W,H)).with_fps(FPS)
    except Exception:
        return CompositeVideoClip([bg, zoomed.set_position(("center","center"))], size=(W,H)).with_fps(FPS)

def write_single_market_video(img_pil: Image.Image, out_path: str, duration: float):
    ensure_dir(os.path.dirname(out_path))
    safe_img = _ensure_even_image(img_pil)
    tmp_png = out_path + ".png"
    safe_img.save(tmp_png, optimize=True)

    try:
        base = ImageClip(tmp_png)
        base = _set_duration(base, duration)
        base = _resize_clip(base, (W,H))
        base = _set_fps(base, FPS)
    except Exception as e:
        try:
            from moviepy.editor import ImageClip as _IC
            base = _IC(tmp_png).with_duration(duration).with_fps(FPS)
        except Exception as e2:
            raise RuntimeError("Failed to create ImageClip: " + str(e2))

    s,e = (ZOOM_START, ZOOM_END)
    clip = ken_burns_zoom(base, s, e)

    music = pick_music_path()
    if music and os.path.exists(music):
            try:
                aud = AudioFileClip(music)

                # safely trim or loop to match clip duration
                if hasattr(aud, "subclip"):
                    aud = aud.subclip(0, min(aud.duration, getattr(clip, "duration", aud.duration)))
                else:
                    try:
                        from moviepy.audio.fx.all import audio_loop
                        aud = audio_loop(aud, duration=getattr(clip, "duration", aud.duration))
                    except Exception:
                        pass

                # add gentle fade in/out
                try:
                    if hasattr(aud, "audio_fadein"):
                        aud = aud.audio_fadein(1.0)
                    if hasattr(aud, "audio_fadeout"):
                        aud = aud.audio_fadeout(1.0)
                except Exception:
                    pass

                # --- attach audio safely & compatibly ---
                try:
                    if hasattr(aud, "volumex"):
                        aud = aud.volumex(0.8)
                except Exception:
                    pass

                attached = False
                try:
                    # Method 1: set_audio (newer MoviePy)
                    if hasattr(clip, "set_audio"):
                        clip = clip.set_audio(aud)
                        attached = True
                    # Method 2: with_audio (older builds)
                    elif hasattr(clip, "with_audio"):
                        clip = clip.with_audio(aud)
                        attached = True
                    # Method 3: assign CompositeAudioClip directly
                    else:
                        from moviepy.audio.AudioClip import CompositeAudioClip
                        clip.audio = CompositeAudioClip([aud])
                        attached = True
                except Exception as ex:
                    print("⚠️ Primary attach failed:", ex)
                    try:
                        from moviepy.audio.AudioClip import CompositeAudioClip
                        clip.audio = CompositeAudioClip([aud])
                        attached = True 
                    except Exception as e2:
                        print("⚠️ Secondary attach failed:", e2)

                if attached:
                    print("♪ Audio attached successfully →", music)
                else:
                    print("⚠️ Audio could not be attached, video will be silent.")

            except Exception as ex:
                print("⚠️ Audio attach failed safely:", ex)
    else:
            print("⚠️ No audio found or invalid path:", music)

    try:
        clip.write_videofile(out_path, fps=FPS, codec="libx264", audio_codec="aac",
                             threads=4, preset="medium", ffmpeg_params=["-pix_fmt","yuv420p"])
    except TypeError:
        try:
            clip.write_videofile(out_path, fps=FPS, codec="libx264", audio_codec="aac")
        except Exception:
            clip.write_videofile(out_path)
    finally:
        try: os.remove(tmp_png)
        except: pass

# ===== Main runner: per-market outputs =====
def main():
    now = datetime.datetime.now()
    date_str = now.strftime("%d-%m-%Y")
    out_dir = os.path.join(OUT_ROOT, now.strftime("%Y-%m-%d"))
    ensure_dir(out_dir)

    entries = load_entries()
    if not entries:
        print("No entries found. Exiting.")
        return

    created = []
    for entry in entries:
        market = entry.get("market") or "MARKET"
        safe = re.sub(r'[^A-Za-z0-9]+', '_', market).strip('_') or "MARKET"
        ts = now.strftime("%Y%m%d_%H%M%S")
        out_file = os.path.join(out_dir, f"{safe}_{ts}.mp4")
        print("→ Rendering:", market, "->", out_file)
        slide_img = render_slide(entry, date_str)
        write_single_market_video(slide_img, out_file, duration=PER_MARKET_SECONDS)
        created.append(out_file)

        if GENERATE_VERTICAL_SHORT:
            short_out = os.path.join(out_dir, f"{safe}_SHORT_{ts}.mp4")
            print("   • Writing short:", short_out)
            write_single_market_video(slide_img, short_out, duration=PER_MARKET_SECONDS)
            created.append(short_out)

    print(f"Done. Created {len(created)} files in {out_dir}")
    for p in created:
        print(" -", p)


if __name__ == "__main__":
    main()
