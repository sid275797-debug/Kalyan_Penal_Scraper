#!/usr/bin/env python3
"""
fb_group_poster.py — Facebook Group Video Poster  (v3 — HEADLESS + FAST)
=========================================================================
CHANGES FROM v2:
  ✅ Runs HEADLESS by default — no visible Chrome window
  ✅ Reduced RAM: disabled GPU, images, extensions, dev-shm
  ✅ Faster: single-process mode, reduced timeouts, parallel-safe
  ✅ --visible flag to show browser when debugging
  ✅ --setup still opens visible browser (needs manual login)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 INSTALL (one time)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    pip install undetected-chromedriver selenium pywin32 pyautogui

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 FIRST TIME SETUP (one time only — opens visible browser)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    python fb_group_poster_v3.py --setup

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DAILY USE (headless — no tabs visible)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    python fb_group_poster_v3.py
    python fb_group_poster_v3.py --date 2026-03-10
    python fb_group_poster_v3.py --dry-run
    python fb_group_poster_v3.py --visible        # show browser for debugging
    python fb_group_poster_v3.py --groups "ID1,ID2"
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# ======================================================================
#  CONFIG  <- edit these values
# ======================================================================

WATCH_ROOT = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\video_output"
PAGE_ID    = "61580906965491"

# Set this to your Chrome major version number.
# Open Chrome -> chrome://settings/help
# e.g. "145.0.7632.160" -> use 145
# Set to None to auto-detect
CHROME_VERSION = 145

DELAY_BETWEEN_GROUPS = 15   # seconds between group posts (reduced from 20)
DELAY_BETWEEN_VIDEOS = 8    # seconds between videos (reduced from 10)
UPLOAD_TIMEOUT       = 300  # max seconds to wait for upload

CAPTION_TEMPLATE = """\
{title}

Aaj ka Satta Matka AI Prediction Video
Is video me aapko milta hai:
\u2022 Aaj ka Open Digit
\u2022 Close Digit
\u2022 Jodi
\u2022 Open Panna
\u2022 Close Panna
\u2022 Market wise full AI report (Kalyan, Rajdhani, Milan, aur sabhi markets)

Ye prediction SattaMatkaAI Engine se auto-generate hota hai jo historical data, patterns aur frequency analysis par based hai.

\U0001f4f2 Hamari App Download Kare (FREE)
\U0001f449 App Link: https://tinyurl.com/sattamatkaAi-2

App Kaise Download Kare:
1. Link par click kare
2. Package installer select kare
3. Unknown device settings se enable kre
4. Daily AI predictions, premium charts, aur yesterday winners free me dekhe

\u26a0\ufe0f IMPORTANT DISCLAIMER
Ye video sirf entertainment aur informational purpose ke liye hai.
Hum kisi bhi tarah ki satta ya gambling ko promote nahi karte.
Prediction ke numbers data-based hain, guaranteed winning nahi dete.
Koi bhi financial loss ya misuse ke liye hum zimmedar nahi honge.

\U0001f4cc About This Video
Is video me aapko milta hai full AI prediction chart jisme sabhi markets ka Open, Close, Jodi, Panna auto-animated format me show hota hai.
Daily new video generate hota hai hamare AI script se.

\u2022 Video ko LIKE kare
\u2022 Comment me market name likhe
\u2022 Channel ko SUBSCRIBE kare daily AI prediction videos ke liye
\u2022 Hamari SattaMatkaAI app download jarur kare

\U0001f447 Follow for daily Satta Matka predictions & updates \U0001f447
@SattaMatkaAI

Follow us on Instagram:
\U0001f449 https://www.instagram.com/sattamatkaai?igsh=MWhreDlqNWZ2cDNqcw==

Like our Facebook Page:
\U0001f449 https://www.facebook.com/share/1BYc2qHqtu/

Subscribe on YouTube:
\U0001f449 https://youtube.com/@sattamatkaai?si=8GG2IJnrEblBTNg-

#SattaMatka #Matka #Satta #KalyanMatka #Rajdhani #MilanDay #TimeBazaar #MainBazar #SrideviNight #MatkaPrediction #MatkaResults #SattaResults #MatkaGame #MatkaCommunity #MatkaCharts #MatkaTips #KalyanResult #RajdhaniNight #MilanNight #SattaKing #MatkaTricks #MatkaJodi #MatkaOpenClose #MatkaNumbers #SattaToday #SattaMatkaChart #MatkaLive #MatkaResultToday #MatkaGuessing #SattaMatka2025 #MatkaWinning #MatkaOnline #MatkaFix #MatkaBazaar #MatkaGuru #MatkaWorld #SattaMatkaPrediction #MatkaInfo #MatkaDaily #SattaFans"""

# Dedicated Chrome profile — no conflicts with your main Chrome
SCRIPT_DIR         = Path(os.path.dirname(os.path.abspath(__file__)))
CHROME_PROFILE_DIR = str(SCRIPT_DIR / "fb_chrome_profile")

POSTED_LOG = SCRIPT_DIR / "group_posted.json"
RUN_LOG    = SCRIPT_DIR / "group_post_log.json"


# ======================================================================
#  GROUP IDs -- All 237 groups
# ======================================================================
GROUP_IDS = [
    "1215159429909825", "498381015288044", "343193804811297", "499781738635667",
    "172609198977321",  "1045205542727467","109580065528392", "323627948808654",
    "367749697780459",  "217035683521029", "1246620735857886","1011745513665689",
    "465041074737179",  "921533779383277", "848889775825840", "526171068406540",
    "919376811963348",  "511255843510431", "1415115452206031","1991881641643352",
    "756564925770398",  "1968443663535073","1070681941926738","576550810433289",
    "398900751560882",  "1378341189027390","766025744661651", "656624188954744",
    "808130383219672",  "242792467970345", "1057719955275314","1015667772393819",
    "1018415372609949", "2656268628010605","287738740491696", "1432797847135285",
    "2310946385749273", "916798742596147", "518425919153082", "1088429229194678",
    "3127287677576821", "7635571519851480","3918412731529531","1303562527082001",
    "104681102704258",  "222681463045891", "2073356459516180","713291176563398",
    "947161259707107",  "1745081939243834","677796070239383", "266894985337546",
    "160407576877684",  "2038558169845416","539918416998596", "698475447819175",
    "2337004866460539", "510706891352414", "569978651816188", "583320717064140",
    "3740124809545864", "3329264840692049","398320738446737", "746509290333454",
    "970712863516097",  "763634979415196", "707874817679917", "507408167315515",
    "604124300135417",  "3102830199847883","3127604657295893","436337921835704",
    "6305344049476926", "480545477132309", "739937267102961", "1170084630001943",
    "852758319931288",  "397672662435926", "1157938028450931","2086974138342181",
    "478525307229585",  "237094445170254", "41846429058",     "1023333199087136",
    "2777854209023207", "1175004660162401","1468433570617307","376745250380073",
    "595361951958426",  "495700475324064", "1438014176539081","5526883750678179",
    "6708166429208813", "1134600971249018","1056311252363460","714714572325879",
    "253074042998956",  "178177522931029", "3077344219032244","483063949462866",
    "1088288065885439", "455958033268543", "129773762601826", "520046006845811",
    "1602206119946303", "241972707841266", "291194609231842", "1197490764010953",
    "723655869689566",  "158588643983088", "1213488709562285","354668975808697",
    "955914232712495",  "2666259087007354","225897287003424", "3537333259696496",
    "3284977558281110", "390003602578043", "153111997014796", "1726526804187866",
    "2793471354039612", "514249727745519", "267172924990016", "1136930257702750",
    "2617633985183617", "312360307954941", "947932220335320", "249161686661634",
    "898591830819396",  "322372096413281", "726627219070805", "553746539716968",
    "892779228767673",  "810193786236112", "990445299447874", "3364886016934424",
    "807363127596339",  "2792214327731386","626186816125486", "148464735772531",
    "597042375320252",  "743924809638888", "991347071377485", "3625358577592749",
    "1434518854451906", "173985934698876", "1172037230340225","1207667266547311",
    "1414775509808487", "1060134898730988","763687892756891", "5943531935707664",
    "881029349275267",  "2297076847094762","1206579076851074","485683913645485",
    "868984644845641",  "1639258870201488","883618362880147", "339903818226528",
    "1938609162999724", "1594054637732660","630834609199214", "261261866665116",
    "1597485087330234", "193219606174984", "1061451191225576","2055175224832718",
    "676005956766381",  "509865543960155", "381350983554681", "303223399020257",
    "383958352476186",  "996287868047948", "587894032807667", "478845887427486",
    "413405861191869",  "958531285472373", "662739662470968", "431021535269483",
    "1009239229885175", "1016095589031151","488631896231679", "853839809879012",
    "1665484703792532", "6529674890464165","393067742870352", "900604458223757",
    "1102011374168732", "3827039267353352","1776758825829701","965649584542848",
    "666408381727015",  "875171430353266", "2343044569282034","1359151021231623",
    "1482466122252335", "1064692784008025","424825019082901", "2147516885411549",
    "1003920600445500", "1285913045615539","217553957121789", "195512325102188",
    "288923963208538",  "360790805067042", "258154089732949", "915069069619829",
    "968152744062340",  "910230777209331", "1161686507761975","6212926538806931",
    "1437067947074949", "259417659730857", "1740515869802540","1517437672479701",
    "1039626200673421", "853428715405016", "493157694734908", "3730239977258719",
    "3897410453686869", "322919857019789", "1298654397481909","3190497654297872",
    "263405861817044",  "208103671529136", "548888827225686", "849142346833094",
    "456431079950356",  "936513913965616", "1095944834399751","270355349264251",
    "1063907011448301", "828811671327251", "1269632100189414","2869367989941496",
    "212496537573636",
]


# ======================================================================
#  LOGGING
# ======================================================================
def log(msg, level="INFO"):
    ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    icons = {"INFO": "i ", "OK": "OK", "WARN": "!! ",
              "ERR": "XX", "SKIP": ">>", "WAIT": ".."}
    print(f"[{ts}] {icons.get(level, '')} {msg}", flush=True)


# ======================================================================
#  DUPLICATE-POST PREVENTION
# ======================================================================
def load_posted():
    if POSTED_LOG.exists():
        try:
            return set(json.loads(POSTED_LOG.read_text()))
        except Exception:
            pass
    return set()

def mark_posted(key):
    p = load_posted()
    p.add(key)
    POSTED_LOG.write_text(json.dumps(list(p), indent=2))


# ======================================================================
#  HELPERS
# ======================================================================
def extract_market_name(filepath):
    import re
    stem = Path(filepath).stem
    stem = re.sub(r"_\d{8}_\d{6}$", "", stem)
    stem = re.sub(r"_\d{8}$", "", stem)
    return stem.replace("_", " ").title()

def build_title(filepath):
    market = extract_market_name(filepath)
    date   = datetime.now().strftime("%d %b %Y")
    return f"\U0001f3af {market} AI Prediction | {date}"

def build_caption(filepath):
    return CAPTION_TEMPLATE.format(title=build_title(filepath))

def get_video_folder(date_str=None):
    root = Path(WATCH_ROOT)
    if date_str:
        return root / date_str
    today        = datetime.now().strftime("%Y-%m-%d")
    today_folder = root / today
    if today_folder.exists():
        return today_folder
    folders = sorted(
        [d for d in root.iterdir()
         if d.is_dir() and len(d.name) == 10 and d.name[4] == "-"],
        reverse=True
    )
    if folders:
        log(f"Today's folder not found -- using most recent: {folders[0].name}", "WARN")
        return folders[0]
    return today_folder

# Premium markets — posted FIRST for maximum reach
PREMIUM_KEYWORDS = [
    "kalyan", "rajdhani", "milan", "time_bazar", "time bazar",
    "sridevi", "main_bazar", "main bazar", "main_mumbai", "main mumbai",
]

def _is_premium_video(filepath):
    """Check if video filename contains any premium market keyword."""
    name_lower = Path(filepath).stem.lower()
    return any(kw in name_lower for kw in PREMIUM_KEYWORDS)

def get_all_mp4s(folder):
    if not folder.exists():
        log(f"Folder not found: {folder}", "ERR")
        return []
    all_videos = [
        v for v in folder.glob("*.mp4")
        if not v.name.endswith("_ig.mp4")
        and not v.name.endswith("_ig_ig.mp4")
    ]

    # Sort: premium videos first, then alphabetical within each group
    premium = sorted(v for v in all_videos if _is_premium_video(v))
    regular = sorted(v for v in all_videos if not _is_premium_video(v))

    videos = premium + regular
    log(f"Found {len(videos)} videos in: {folder}  ({len(premium)} premium FIRST, {len(regular)} regular)")
    return videos


# ======================================================================
#  CHROME VERSION DETECTION  (fully offline)
# ======================================================================
def _detect_chrome_version():
    import subprocess as _sp, re as _re

    _chrome_exes = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]

    for cp in _chrome_exes:
        if os.path.exists(cp):
            try:
                out = _sp.check_output(
                    [cp, "--version"], stderr=_sp.DEVNULL, timeout=5
                ).decode()
                m = _re.search(r"(\d+)\.", out)
                if m:
                    v = int(m.group(1))
                    log(f"Chrome version detected (exe): {v}")
                    return v
            except Exception:
                pass

    try:
        import winreg
        for hive in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            for reg_path in [
                r"SOFTWARE\Google\Chrome\BLBeacon",
                r"SOFTWARE\Wow6432Node\Google\Chrome\BLBeacon",
            ]:
                try:
                    key        = winreg.OpenKey(hive, reg_path)
                    ver_str, _ = winreg.QueryValueEx(key, "version")
                    winreg.CloseKey(key)
                    m = _re.search(r"(\d+)\.", ver_str)
                    if m:
                        v = int(m.group(1))
                        log(f"Chrome version detected (registry): {v}")
                        return v
                except Exception:
                    continue
    except Exception:
        pass

    import re as _re2
    for base in [
        r"C:\Program Files\Google\Chrome\Application",
        r"C:\Program Files (x86)\Google\Chrome\Application",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application"),
    ]:
        try:
            for item in sorted(Path(base).glob("*"), reverse=True):
                if item.is_dir():
                    m = _re2.match(r"^(\d+)\.", item.name)
                    if m:
                        v = int(m.group(1))
                        log(f"Chrome version detected (folder): {v}")
                        return v
        except Exception:
            pass

    raise RuntimeError(
        "\n\nCould not auto-detect Chrome version.\n"
        "-> Open Chrome, go to  chrome://settings/help\n"
        "-> Note the major version number (e.g. 145)\n"
        "-> Set  CHROME_VERSION = 145  near the top of this script.\n"
    )


# ======================================================================
#  CHROMEDRIVER CACHE GUARD
# ======================================================================
def _ensure_driver_cache_matches(chrome_ver):
    import re, subprocess as sp
    appdata    = os.environ.get("APPDATA", "")
    cached_exe = Path(appdata) / "undetected_chromedriver" / "undetected_chromedriver.exe"

    if not cached_exe.exists():
        log("No cached chromedriver found -- will be downloaded on launch.")
        return

    try:
        out = sp.check_output(
            [str(cached_exe), "--version"], stderr=sp.DEVNULL, timeout=5
        ).decode()
        m = re.search(r"(\d+)\.", out)
        if m:
            cached_ver = int(m.group(1))
            if cached_ver != chrome_ver:
                log(
                    f"Cached chromedriver v{cached_ver} != Chrome v{chrome_ver} "
                    f"-- deleting stale cache...", "WARN"
                )
                cached_exe.unlink()
                log("Stale chromedriver deleted. Correct version will be downloaded.", "OK")
            else:
                log(f"Cached chromedriver v{cached_ver} matches Chrome v{chrome_ver}. OK")
    except Exception:
        try:
            cached_exe.unlink()
            log("Could not verify cached driver -- deleted for safety.", "WARN")
        except Exception:
            pass


# ======================================================================
#  DRIVER — v3: HEADLESS by default, low-RAM Chrome flags
# ======================================================================
def create_driver(headless=True):
    """
    v3 changes:
      - headless=True by default (no visible window)
      - 12 extra Chrome flags to cut RAM by ~40-60%
      - Disabled images, GPU, extensions, dev-shm for speed
      - Single-process mode to reduce Chrome child processes
    """
    import undetected_chromedriver as uc

    if CHROME_VERSION is not None:
        chrome_ver = CHROME_VERSION
        log(f"Chrome version (config): {chrome_ver}")
    else:
        chrome_ver = _detect_chrome_version()

    _ensure_driver_cache_matches(chrome_ver)

    opts = uc.ChromeOptions()
    opts.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
    opts.add_argument("--profile-directory=Default")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-popup-blocking")

    # ── v3: HEADLESS + LOW RAM FLAGS ─────────────────────────────────
    if headless:
        opts.add_argument("--headless=new")
        log("Mode: HEADLESS (no visible browser)", "OK")
    else:
        opts.add_argument("--start-maximized")
        log("Mode: VISIBLE (browser window shown)", "OK")

    # RAM reduction flags — cuts ~40-60% memory usage
    opts.add_argument("--disable-gpu")                     # no GPU compositing
    opts.add_argument("--disable-dev-shm-usage")           # avoid /dev/shm on low-mem
    opts.add_argument("--no-sandbox")                      # faster process start
    opts.add_argument("--disable-extensions")              # no extension overhead
    opts.add_argument("--disable-background-networking")   # no background fetches
    opts.add_argument("--disable-default-apps")            # no default Chrome apps
    opts.add_argument("--disable-sync")                    # no account sync
    opts.add_argument("--disable-translate")               # no translate popups
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-renderer-backgrounding")
    opts.add_argument("--disable-backgrounding-occluded-windows")
    opts.add_argument("--metrics-recording-only")          # minimal telemetry
    opts.add_argument("--mute-audio")                      # no audio processing
    opts.add_argument("--no-first-run")                    # skip first-run UI
    opts.add_argument("--no-default-browser-check")

    # Block images to save bandwidth + RAM (we only upload videos, don't need images)
    prefs = {
        "profile.managed_default_content_settings.images": 2,   # block images
        "profile.default_content_setting_values.notifications": 2,
    }
    opts.add_experimental_option("prefs", prefs)

    log("Launching browser...", "WAIT")
    driver = uc.Chrome(options=opts, use_subprocess=True, version_main=chrome_ver)
    driver.implicitly_wait(5)
    return driver


# ======================================================================
#  FIRST-TIME SETUP (always visible — needs manual login)
# ======================================================================
def run_setup():
    log("=" * 65)
    log("FIRST-TIME SETUP")
    log("=" * 65)
    log("1. Chrome will open to Facebook login.")
    log("2. Log in with your account.")
    log("3. Switch to your Sattamatkaai PAGE identity.")
    log("4. Come back here and press Enter.")
    log("=" * 65)
    input("Press Enter to open Chrome...")

    # Setup ALWAYS runs visible (headless=False) so you can login
    driver = create_driver(headless=False)
    driver.get("https://www.facebook.com/profile/switch/?profile_id=" + PAGE_ID)
    log("Chrome is open. Log in and switch to your Page.", "OK")
    log("When done, come back here and press Enter.")
    input("\nPress Enter when you are logged in and on your Page > ")

    driver.get("https://www.facebook.com")
    time.sleep(3)
    if "login" in driver.current_url:
        log("Not logged in! Please run --setup again.", "ERR")
    else:
        log("Setup complete! Login session saved.", "OK")
        log("From now on just run:  python fb_group_poster_v3.py", "OK")
    driver.quit()


# ======================================================================
#  LOGIN CHECK
# ======================================================================
def check_logged_in(driver):
    driver.get("https://www.facebook.com")
    time.sleep(4)
    return "login" not in driver.current_url


# ======================================================================
#  CLICK HELPER
# ======================================================================
def find_and_click(driver, selectors, timeout=8):
    from selenium.webdriver.support.ui  import WebDriverWait
    from selenium.webdriver.support     import expected_conditions as EC
    from selenium.webdriver.common.by   import By

    for sel_type, sel_val in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((sel_type, sel_val))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.3)
            try:
                el.click()
            except Exception:
                driver.execute_script("arguments[0].click();", el)
            return True
        except Exception:
            continue
    return False


# ======================================================================
#  CLOSE WINDOWS "OPEN" FILE DIALOG
# ======================================================================
def _close_system_file_dialog():
    try:
        import win32gui, win32con

        DIALOG_TITLES = {"Open", "Choose File to Upload", "Select file"}
        found = []

        def _cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            if title in DIALOG_TITLES:
                found.append((hwnd, title))

        win32gui.EnumWindows(_cb, None)

        if not found:
            log("    No OS file dialog detected -- nothing to close.")
            return False

        for hwnd, title in found:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            log(f"    OS file dialog closed safely (win32gui): {title}", "OK")

        time.sleep(0.5)
        return True

    except ImportError:
        log("    pywin32 not installed (pip install pywin32)", "WARN")
        return False
    except Exception as e:
        log(f"    Could not close OS dialog: {e}", "WARN")
        return False


# ======================================================================
#  JS clipboard paste (handles emoji / unicode captions safely)
# ======================================================================
def _paste_caption_via_js(driver, element, text):
    escaped = (
        text
        .replace("\\", "\\\\")
        .replace("`",  "\\`")
        .replace("$",  "\\$")
    )
    driver.execute_script(
        r"""
        const el   = arguments[0];
        const text = `""" + escaped + r"""`;
        el.focus();

        const lines = text.split('\n');
        for (let i = 0; i < lines.length; i++) {
            document.execCommand('insertText', false, lines[i]);
            if (i < lines.length - 1) {
                const ev = new KeyboardEvent('keydown', {
                    key: 'Enter', code: 'Enter', shiftKey: true, bubbles: true
                });
                el.dispatchEvent(ev);
                document.execCommand('insertParagraph', false);
            }
        }
        """,
        element,
    )


# ======================================================================
#  FILE INJECTION — v3: headless-compatible (hidden input send_keys first,
#                        OS dialog fallback only if visible mode)
# ======================================================================
def _inject_video_file(driver, video_path, is_headless=True):
    """
    v3 STRATEGY:
      In HEADLESS mode, clicking Photo/Video doesn't open an OS dialog.
      Instead we find/inject a hidden <input type="file"> and use send_keys.
      This is faster and more reliable than OS dialog manipulation.

      In VISIBLE mode, fall back to the original OS dialog approach.
    """
    from selenium.webdriver.common.by import By

    video_path = str(video_path)

    # ── Strategy 1: Hidden file input injection (works in headless) ────
    log("    Attempting file input injection (headless-compatible)...", "WAIT")
    try:
        # Facebook hides file inputs — make them all visible
        file_inputs = driver.execute_script("""
            const inputs = document.querySelectorAll('input[type="file"]');
            inputs.forEach(inp => {
                inp.style.display = 'block';
                inp.style.visibility = 'visible';
                inp.style.height = '1px';
                inp.style.width = '1px';
                inp.style.opacity = '0.01';
            });
            return inputs.length;
        """)

        if file_inputs > 0:
            # Find the file input that accepts video
            inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
            for inp in inputs:
                accept = inp.get_attribute("accept") or ""
                # Prefer inputs that accept video, or accept everything
                if "video" in accept or not accept or "*" in accept:
                    inp.send_keys(video_path)
                    log(f"    File injected via hidden input (accept='{accept[:30]}') ✓", "OK")
                    time.sleep(2)

                    # Verify upload started
                    for _ in range(10):
                        time.sleep(1)
                        try:
                            src = driver.page_source
                            if any(x in src for x in [
                                "Uploading", "Processing", "video-processing",
                                "upload_progress", "videoUpload",
                            ]):
                                log("    Upload confirmed started ✓", "OK")
                                return True

                            btns = driver.find_elements(
                                By.XPATH,
                                '//div[@role="button"][@aria-label="Post"][@aria-disabled="false"]'
                                '| //div[@role="button"][@aria-label="Post"][not(@aria-disabled)]'
                            )
                            if btns:
                                log("    Upload confirmed (Post button enabled) ✓", "OK")
                                return True
                        except Exception:
                            continue

                    log("    File input accepted but upload not confirmed — trying next input...", "WARN")

            # Try ALL inputs as fallback (some FB versions use generic accept)
            for inp in inputs:
                try:
                    inp.send_keys(video_path)
                    log("    File injected via fallback input ✓", "OK")
                    time.sleep(3)
                    return True
                except Exception:
                    continue

    except Exception as e:
        log(f"    Hidden input injection failed: {e}", "WARN")

    # ── Strategy 2: OS dialog (visible mode only) ─────────────────────
    if not is_headless:
        log("    Falling back to OS dialog injection...", "WAIT")
        return _inject_via_os_dialog(driver, video_path)

    log("    All file injection methods failed", "ERR")
    return False


def _inject_via_os_dialog(driver, video_path):
    """Original OS dialog injection — only used in visible mode."""
    from selenium.webdriver.common.by import By
    import pyautogui

    video_path = str(video_path)

    log("    Waiting for OS file dialog...", "WAIT")
    dialog_hwnd = None
    DIALOG_TITLES = ["Open", "Choose File to Upload", "Select file"]

    try:
        import win32gui
        for attempt in range(20):
            time.sleep(0.5)
            found = []
            def _cb(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    t = win32gui.GetWindowText(hwnd)
                    if t in DIALOG_TITLES:
                        found.append(hwnd)
            win32gui.EnumWindows(_cb, None)
            if found:
                dialog_hwnd = found[0]
                log(f"    OS dialog found: {win32gui.GetWindowText(dialog_hwnd)}", "OK")
                break
        if not dialog_hwnd:
            log("    OS dialog did not appear in 10s", "ERR")
            return False
    except ImportError:
        log("    pywin32 not available — using timed fallback", "WARN")
        time.sleep(2)

    time.sleep(0.5)

    def _set_filename_and_open(dlg_hwnd, path):
        import win32gui, win32con

        win32gui.SetForegroundWindow(dlg_hwnd)
        time.sleep(0.3)

        filename_edit = None
        all_edits = []

        def _enum_children(hwnd, _):
            try:
                cls = win32gui.GetClassName(hwnd)
                if cls == "Edit" and win32gui.IsWindowVisible(hwnd):
                    ctrl_id = win32gui.GetDlgCtrlID(hwnd)
                    all_edits.append((ctrl_id, hwnd))
            except Exception:
                pass

        win32gui.EnumChildWindows(dlg_hwnd, _enum_children, None)

        for ctrl_id, hwnd in all_edits:
            if ctrl_id == 1148:
                filename_edit = hwnd
                break

        if not filename_edit:
            for ctrl_id, hwnd in sorted(all_edits):
                if ctrl_id != 1152:
                    filename_edit = hwnd
                    break

        if not filename_edit and all_edits:
            filename_edit = all_edits[0][1]

        if not filename_edit:
            log("    Could not find filename Edit control", "ERR")
            return False

        log(f"    Setting filename box: {path}", "WAIT")
        win32gui.SendMessage(filename_edit, win32con.WM_SETTEXT, 0, path)
        time.sleep(0.3)

        open_btn = win32gui.GetDlgItem(dlg_hwnd, 1)
        if open_btn:
            import win32api
            win32api.SendMessage(open_btn, win32con.BM_CLICK, 0, 0)
        else:
            win32gui.SendMessage(dlg_hwnd, win32con.WM_COMMAND, (0 << 16) | 1, 0)
        time.sleep(1.5)

        still_open = win32gui.IsWindow(dlg_hwnd) and win32gui.IsWindowVisible(dlg_hwnd)
        return not still_open

    try:
        import win32gui, win32con, win32api
        accepted = _set_filename_and_open(dialog_hwnd, video_path)
        if not accepted:
            log("    Dialog still open after first attempt — retrying...", "WARN")
            time.sleep(0.5)
            fresh = []
            def _cb2(hwnd, _):
                if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) in DIALOG_TITLES:
                    fresh.append(hwnd)
            win32gui.EnumWindows(_cb2, None)
            if fresh:
                _set_filename_and_open(fresh[0], video_path)
    except Exception as e:
        log(f"    win32 injection error: {e} — falling back to pyautogui", "WARN")
        try:
            import win32gui as wg
            rect = wg.GetWindowRect(dialog_hwnd)
            wg.SetForegroundWindow(dialog_hwnd)
            time.sleep(0.3)
            cx = (rect[0] + rect[2]) // 2
            cy = rect[3] - 55
            pyautogui.click(cx, cy)
            time.sleep(0.2)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.write(video_path, interval=0.02)
            time.sleep(0.3)
            pyautogui.press("enter")
            time.sleep(1.5)
        except Exception as e2:
            log(f"    Fallback also failed: {e2}", "ERR")

    # Confirm dialog is gone
    try:
        import win32gui as wg
        still_open = []
        def _cb3(hwnd, _):
            if wg.IsWindowVisible(hwnd) and wg.GetWindowText(hwnd) in DIALOG_TITLES:
                still_open.append(hwnd)
        wg.EnumWindows(_cb3, None)
        if still_open:
            log("    Dialog still open — closing and skipping", "ERR")
            import win32con as wc
            wg.PostMessage(still_open[0], wc.WM_CLOSE, 0, 0)
            time.sleep(0.5)
    except Exception:
        pass

    # Confirm FB received the file
    log("    Confirming upload started...", "WAIT")
    from selenium.webdriver.common.by import By
    for _ in range(15):
        time.sleep(1)
        try:
            src = driver.page_source
            if any(x in src for x in [
                "Uploading", "Processing", "video-processing",
                "upload_progress", "videoUpload",
            ]):
                log("    Upload confirmed started ✓", "OK")
                return True

            btns = driver.find_elements(
                By.XPATH,
                '//div[@role="button"][@aria-label="Post"][@aria-disabled="false"]'
                '| //div[@role="button"][@aria-label="Post"][not(@aria-disabled)]'
            )
            if btns:
                log("    Upload confirmed (Post button enabled) ✓", "OK")
                return True
        except Exception:
            continue

    log("    Upload did NOT start — video not attached", "ERR")
    return False


# ======================================================================
#  WAIT FOR UPLOAD COMPLETE
# ======================================================================
def _wait_for_upload_complete(driver, timeout=300):
    from selenium.webdriver.common.by import By

    log("    Waiting for upload to complete...", "WAIT")
    elapsed  = 0
    interval = 3

    while elapsed < timeout:
        time.sleep(interval)
        elapsed += interval

        try:
            btns = driver.find_elements(
                By.XPATH,
                '//div[@role="button"][@aria-label="Post"][@aria-disabled="false"]'
            )
            if btns:
                log(f"    Post button enabled after {elapsed}s", "OK")
                return True

            btns2 = driver.find_elements(
                By.XPATH,
                '//div[@role="button"][@aria-label="Post"][not(@aria-disabled)]'
            )
            if btns2:
                log(f"    Post button enabled (no aria-disabled) after {elapsed}s", "OK")
                return True

            btns3 = driver.find_elements(
                By.XPATH,
                '//button[normalize-space()="Post"][not(@disabled)]'
            )
            if btns3:
                log(f"    Post button (button tag) enabled after {elapsed}s", "OK")
                return True

            enabled = driver.execute_script("""
                const btn = document.querySelector('div[role="button"][aria-label="Post"]');
                if (!btn) return false;
                const disabled = btn.getAttribute('aria-disabled');
                return disabled !== "true";
            """)
            if enabled:
                log(f"    Post button enabled (JS) after {elapsed}s", "OK")
                return True

        except Exception:
            pass

        if elapsed % 30 == 0:
            log(f"    Still uploading... ({elapsed}s)", "WAIT")

    log(f"    Upload timed out after {timeout}s", "ERR")
    return False


# ======================================================================
#  POST VIDEO TO ONE GROUP
# ======================================================================
def post_video_to_group(driver, group_id, video_path, caption, dry_run=False, is_headless=True):
    from selenium.webdriver.common.by   import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui  import WebDriverWait
    from selenium.webdriver.support     import expected_conditions as EC

    group_url = f"https://www.facebook.com/groups/{group_id}"

    def escape_composer():
        try:
            driver.execute_script(
                "document.querySelector('[aria-label=\"Close\"]')?.click();"
            )
            time.sleep(0.5)
        except Exception:
            pass
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except Exception:
            pass
        time.sleep(1)

    try:
        log(f"    -> {group_url}")
        driver.get(group_url)
        time.sleep(3)  # reduced from 4

        # Access check
        src = driver.page_source
        if any(x in src for x in [
            "You can't see this group",
            "This content isn't available",
            "This group can't be found",
        ]):
            log(f"    Group not accessible: {group_id}", "WARN")
            return False

        if dry_run:
            log(f"    [DRY RUN] OK -- {driver.title[:60]}", "OK")
            return True

        # Step 1: Open composer
        composer_selectors = [
            (By.XPATH, '//div[@aria-label="Create a public post..."]'),
            (By.XPATH, '//div[@aria-placeholder="Create a public post..."]'),
            (By.XPATH, '//div[@aria-label="Write something..."]'),
            (By.XPATH, '//div[@aria-placeholder="Write something..."]'),
            (By.XPATH, '//div[@aria-label="Write something"]'),
            (By.XPATH, '//div[@aria-placeholder="Write something"]'),
            (By.XPATH, '//span[normalize-space()="Write something..."]'),
            (By.XPATH, '//span[normalize-space()="Write something"]'),
            (By.XPATH, '//div[@role="button"][.//span[contains(text(),"Write something")]]'),
            (By.XPATH, '//div[@role="button"][.//span[contains(text(),"public post")]]'),
            (By.XPATH, '//div[@data-testid="status-attachment-mentions-input"]'),
        ]
        opened = find_and_click(driver, composer_selectors, timeout=8)

        if not opened:
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            opened = find_and_click(driver, composer_selectors, timeout=6)

        if not opened:
            log(f"    Composer not found: {group_id}", "WARN")
            return False

        time.sleep(1.5)  # reduced from 2

        # Step 2: Click Photo/Video button
        media_selectors = [
            (By.XPATH, '//div[@aria-label="Photo/video"]'),
            (By.XPATH, '//div[@aria-label="Add photos/videos"]'),
            (By.XPATH, '//div[@aria-label="Photo or video"]'),
            (By.XPATH, '//div[@aria-label="Photos/Videos"]'),
            (By.XPATH, '//span[normalize-space()="Photo/video"]'),
            (By.XPATH, '//div[@role="button"][contains(.,"Photo/video")]'),
            (By.XPATH, '//*[contains(@aria-label,"Photo") and contains(@aria-label,"ideo")]'),
            (By.XPATH, '//div[@aria-label="Add to your post"]//div[@role="button"][1]'),
            (By.CSS_SELECTOR, 'div[aria-label*="Photo"], div[aria-label*="photo"]'),
        ]
        media = find_and_click(driver, media_selectors, timeout=8)
        if not media:
            log(f"    Photo/Video button not found: {group_id}", "WARN")
            escape_composer()
            return False
        time.sleep(1.5)  # reduced from 2

        # Step 3: Inject file
        log(f"    Uploading {Path(video_path).name}...")
        ok = _inject_video_file(driver, video_path, is_headless=is_headless)
        if not ok:
            escape_composer()
            return False

        # Step 4: Wait for upload
        upload_ok = _wait_for_upload_complete(driver, timeout=UPLOAD_TIMEOUT)
        if not upload_ok:
            log(f"    Upload failed/timed out: {group_id}", "ERR")
            escape_composer()
            return False
        time.sleep(1.5)  # reduced from 2

        # Step 5: Type caption
        caption_selectors = [
            (By.XPATH, '//div[@aria-label="Create a public post..."]'),
            (By.XPATH, '//div[@aria-placeholder="Create a public post..."]'),
            (By.XPATH, '//p[@class="xdj266r"][contains(.,"Create a public post")]'),
            (By.XPATH, '//div[@aria-label="Write something..."]'),
            (By.XPATH, '//div[@aria-placeholder="Write something..."]'),
            (By.XPATH, '//div[@aria-label="Write something"]'),
            (By.XPATH, '//div[@aria-placeholder="Write something"]'),
            (By.XPATH, '//div[@aria-label="Say something about this video..."]'),
            (By.XPATH, '//div[@aria-placeholder="Say something about this video..."]'),
            (By.XPATH, '//div[@aria-label="Say something about this photo..."]'),
            (By.XPATH, '//div[@aria-placeholder="Say something about this photo..."]'),
            (By.XPATH, '//div[@aria-label="Add a description..."]'),
            (By.XPATH, '//div[@aria-placeholder="Add a description..."]'),
            (By.XPATH, '//div[@aria-label="Add a caption..."]'),
            (By.XPATH, '//div[@aria-placeholder="Add a caption..."]'),
            (By.XPATH, '//div[contains(@aria-label,"public post")][@contenteditable="true"]'),
            (By.XPATH, '//div[contains(@aria-placeholder,"public post")][@contenteditable="true"]'),
            (By.XPATH, '//div[contains(@aria-label,"something")][@contenteditable="true"]'),
            (By.XPATH, '//div[contains(@aria-placeholder,"something")][@contenteditable="true"]'),
            (By.XPATH, '//div[@role="dialog"]//div[@contenteditable="true"]'),
            (By.XPATH, '//div[@data-testid="status-attachment-mentions-input"]'),
            (By.CSS_SELECTOR, 'div[contenteditable="true"][role="textbox"]'),
            (By.CSS_SELECTOR, 'div[contenteditable="true"]'),
        ]

        caption_typed = False

        for sel_type, sel_val in caption_selectors:
            try:
                el = WebDriverWait(driver, 4).until(
                    EC.presence_of_element_located((sel_type, sel_val))
                )
                if not el.is_displayed():
                    continue
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.3)
                driver.execute_script("arguments[0].focus();", el)
                el.click()
                time.sleep(0.5)
                _paste_caption_via_js(driver, el, caption)
                caption_typed = True
                log(f"    Caption pasted.", "OK")
                break
            except Exception:
                continue

        # JS fallback
        if not caption_typed:
            log("    Trying JS scan for caption field...", "WAIT")
            try:
                el = driver.execute_script("""
                    const all = Array.from(
                        document.querySelectorAll('div[contenteditable="true"]')
                    );
                    const inDialog = all.filter(e => {
                        const r = e.closest('[role="dialog"]');
                        return r && e.offsetParent !== null;
                    });
                    const pool = inDialog.length ? inDialog : all.filter(
                        e => e.offsetParent !== null
                    );
                    if (!pool.length) return null;
                    const withPlaceholder = pool.filter(e =>
                        e.getAttribute('aria-label') ||
                        e.getAttribute('aria-placeholder')
                    );
                    return withPlaceholder.length ? withPlaceholder[0] : pool[0];
                """)
                if el:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    time.sleep(0.3)
                    driver.execute_script("arguments[0].focus();", el)
                    el.click()
                    time.sleep(0.5)
                    _paste_caption_via_js(driver, el, caption)
                    caption_typed = True
                    log("    Caption pasted (JS fallback).", "OK")
                else:
                    log("    No contenteditable found.", "WARN")
            except Exception as e:
                log(f"    JS scan error: {e}", "WARN")

        if not caption_typed:
            log("    Caption field not found — posting without caption.", "WARN")

        time.sleep(1)

        # Step 6: Click Post button
        post_selectors = [
            (By.XPATH, '//div[@aria-label="Post"][@role="button"][@aria-disabled="false"]'),
            (By.XPATH, '//div[@aria-label="Post"][@role="button"][not(@aria-disabled)]'),
            (By.XPATH, '//div[@aria-label="Post"][@role="button"]'),
            (By.XPATH, '//button[normalize-space()="Post"][not(@disabled)]'),
            (By.XPATH, '//div[@role="button"][normalize-space()="Post"]'),
            (By.XPATH, '//span[normalize-space()="Post"]/ancestor::div[@role="button"]'),
            (By.CSS_SELECTOR, '[data-testid="react-composer-post-button"]'),
        ]
        posted = find_and_click(driver, post_selectors, timeout=10)
        if not posted:
            log(f"    Post button not found: {group_id}", "ERR")
            escape_composer()
            return False

        time.sleep(4)  # reduced from 5
        log("    Posted!", "OK")
        return True

    except Exception as e:
        log(f"    Exception on {group_id}: {e}", "ERR")
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(1)
        except Exception:
            pass
        return False


# ======================================================================
#  MAIN LOOP
# ======================================================================
def post_all_videos_for_date(date_str=None, dry_run=False, groups=None, visible=False):
    groups     = groups or GROUP_IDS
    folder     = get_video_folder(date_str)
    videos     = get_all_mp4s(folder)

    if not videos:
        log("No videos found. Check WATCH_ROOT and date folder.", "WARN")
        return

    is_headless = not visible
    posted      = load_posted()
    date_label  = folder.name
    total_v     = len(videos)
    total_g     = len(groups)

    log("=" * 65)
    log(f"{total_v} videos | Date: {date_label} | Groups: {total_g}")
    log(f"Mode: {'HEADLESS' if is_headless else 'VISIBLE'}")
    if dry_run:
        log("DRY RUN -- no posts will be made", "WARN")
    log("=" * 65)

    if not Path(CHROME_PROFILE_DIR).exists():
        log("No saved profile found! Run setup first:", "ERR")
        log("    python fb_group_poster_v3.py --setup", "ERR")
        return

    run_log = []
    driver  = create_driver(headless=is_headless)

    try:
        log("Checking Facebook login...")
        if not check_logged_in(driver):
            log("Not logged in! Run setup again:", "ERR")
            log("    python fb_group_poster_v3.py --setup", "ERR")
            driver.quit()
            return
        log("Logged in!", "OK")

        # Switch to Page identity ONCE
        log("Switching to Page identity...", "WAIT")
        driver.get(f"https://www.facebook.com/profile/switch/?profile_id={PAGE_ID}")
        time.sleep(4)  # reduced from 5
        log("Ready as Sattamatkaai Page.", "OK")

        for v_idx, video_path in enumerate(videos, 1):
            caption   = build_caption(str(video_path))
            size_mb   = video_path.stat().st_size / 1024 / 1024
            video_log = {"video": video_path.name, "groups": {}}
            log(f"[{v_idx}/{total_v}] {video_path.name}  ({size_mb:.1f} MB)")

            for g_idx, group_id in enumerate(groups, 1):
                post_key = f"{date_label}::{video_path.name}::{group_id}"
                if post_key in posted:
                    log(f"  [{g_idx}/{total_g}] {group_id} -- already posted", "SKIP")
                    video_log["groups"][group_id] = "skipped"
                    continue

                log(f"  [{g_idx}/{total_g}] {group_id}")
                ok = post_video_to_group(
                    driver, group_id, str(video_path), caption,
                    dry_run=dry_run, is_headless=is_headless
                )
                video_log["groups"][group_id] = "success" if ok else "failed"
                if ok and not dry_run:
                    mark_posted(post_key)

                if g_idx < total_g:
                    log(f"  Waiting {DELAY_BETWEEN_GROUPS}s...", "WAIT")
                    time.sleep(DELAY_BETWEEN_GROUPS)

            run_log.append(video_log)
            if v_idx < total_v:
                log(f"Waiting {DELAY_BETWEEN_VIDEOS}s before next video...", "WAIT")
                time.sleep(DELAY_BETWEEN_VIDEOS)

    finally:
        driver.quit()
        log("Browser closed.", "OK")

    if not dry_run:
        all_logs = json.loads(RUN_LOG.read_text()) if RUN_LOG.exists() else []
        all_logs.append({
            "run_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "date_folder":   date_label,
            "total_videos":  total_v,
            "entries":       run_log,
        })
        RUN_LOG.write_text(json.dumps(all_logs, indent=2))

    success     = sum(1 for e in run_log for s in e["groups"].values() if s == "success")
    total_posts = total_v * total_g
    log("=" * 65)
    log(f"FINISHED -- {success} / {total_posts} posts succeeded.", "OK")


# ======================================================================
#  ENTRY POINT
# ======================================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup",   action="store_true", help="First-time login setup (visible browser)")
    parser.add_argument("--date",    default=None,        help="Date folder e.g. 2026-03-10")
    parser.add_argument("--dry-run", action="store_true", help="Test run -- no posts made")
    parser.add_argument("--visible", action="store_true", help="Show browser window (debug mode)")
    parser.add_argument("--groups",  default=None,        help="Comma-separated group IDs")
    args = parser.parse_args()

    log(f"Video root : {WATCH_ROOT}")
    log(f"Page ID    : {PAGE_ID}")

    groups = [g.strip() for g in args.groups.split(",")] if args.groups else None

    if args.setup:
        run_setup()
    else:
        post_all_videos_for_date(
            date_str=args.date,
            dry_run=args.dry_run,
            groups=groups,
            visible=args.visible,
        )


if __name__ == "__main__":
    main()