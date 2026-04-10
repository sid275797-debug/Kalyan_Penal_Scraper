#!/usr/bin/env python3 
# -*- coding: utf-8 -*-

"""
Reels Video Builder — Slide Type 1 (per-market output)
Creates one MP4 per market (single-slide video) using the same slide layout,
music selection and ken-burns zoom as the original script.
"""

import os, re, json, math, datetime
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# MoviePy 2.x (works with moviepy 2.x API)
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip

# ======= CONFIG =======
DEBUG = False
SHOW_VERSION = False  # keep False (no bottom-left version text)

# ---- Paths
BASE_DIR    = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper"
JSON_PATH   = os.path.join(BASE_DIR, "sattaboss-data", "data", "todays_predictions.json")
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
MUSIC_DIR   = os.path.join(BASE_DIR, "music")  # <— NEW preferred music folder
LOGO_PATH   = os.path.join(ASSETS_DIR, "logo.png")
OUT_ROOT    = os.path.join(BASE_DIR, "video_output")

# audio handling
PREFERRED_MUSIC_NAME = "bgm.mp3"
AUDIO_EXTS = (".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac")

# market filtering
EXCLUDE_FILE = os.path.join(ASSETS_DIR, "exclude_markets.txt")

# ---- Market selection
TEST_MARKET_SUBSTR = ""      # e.g., "KALYAN" to filter; empty = all
MAX_MARKETS        = 12      # None for all

# ---- Video params
W, H = 1080, 1920
FPS = 30
PER_SLIDE_SEC = 15.0
ZOOM_START, ZOOM_END = 1.00, 1.06

# ---- Canvas + Colors
PAD  = 84
SAFE_TOP, SAFE_BOTTOM = 100, 170
BG_TOP=(5,6,10); BG_BOT=(2,2,5)
WHITE=(255,255,255); DIM=(222,226,234)
CYAN=(0,229,255); MAGENTA=(255,29,206); YELLOW=(255,214,51)
CARD_BG=(12,14,22,230); CARD_ST=(0,229,255,60)
PILL_BG=(8,10,16,230);  PILL_ST=(0,229,255,220)

# ---- Fonts
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

# ---- Sizes (Slide Type 1)
BASE = {
    "title": 68, "date": 50, "tag": 46,
    "open": 136, "close": 136,
    "jodi": 64, "chip_h": 96, "chip_gap": 18, "chip_pad_x": 40,
    "pill": 42, "pill_h": 72, "pill_gap": 14,
    "pad": 24, "gap_s": 12, "gap_m": 22, "gap_l": 28
}
LIMITS = {"jodi_cap": 10, "pill_cap": 12}

# ===== Helpers =====
def ensure_dir(p): os.makedirs(p, exist_ok=True)

def load_font(cands, size):
    for fp in cands:
        if os.path.exists(fp):
            try: return ImageFont.truetype(fp, size)
            except: pass
    return ImageFont.load_default()

def tw(draw, font, s): return int(draw.textlength(s, font=font))
def th(font):
    try: b = font.getbbox("Hg0123456789"); return int(b[3] - b[1])
    except: a, d = font.getmetrics(); return int(a + d)

def bg_make(size):
    w,h=size
    t=np.linspace(0,1,h)[:,None,None]
    top=np.array(BG_TOP,dtype=np.float32)[None,None,:]
    bot=np.array(BG_BOT,dtype=np.float32)[None,None,:]
    grad=top*(1-t)+bot*t
    arr=np.repeat(grad,w,axis=1).astype(np.uint8)
    img=Image.fromarray(arr,mode="RGB").convert("RGBA")
    sl=Image.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(sl)
    for yy in range(0,h,10): d.line([(0,yy),(w,yy)], fill=(255,255,255,12), width=1)
    img.alpha_composite(sl); return img

def glow_text(canvas, draw, xy, text, font, fill, glow, radius=6):
    if not text: return
    g=Image.new("RGBA",canvas.size,(0,0,0,0))
    gd=ImageDraw.Draw(g); gd.text(xy,text,font=font,fill=(glow[0],glow[1],glow[2],255))
    g=g.filter(ImageFilter.GaussianBlur(radius))
    canvas.alpha_composite(g); draw.text(xy,text,font=font,fill=fill)

def rounded_rect_on(canvas, xy, radius, fill, outline=None, width=2, blur=0):
    tmp=Image.new("RGBA",canvas.size,(0,0,0,0))
    td=ImageDraw.Draw(tmp)
    td.rounded_rectangle(xy,radius=radius,fill=fill,outline=outline,width=width)
    if blur: tmp=tmp.filter(ImageFilter.GaussianBlur(4))
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
    flat=dict(d)
    for k in list(d.keys()):
        if isinstance(d[k], dict) and norm_key(k) in ("predictions","data","result","values","payload"):
            for k2,v2 in d[k].items():
                if k2 not in flat: flat[k2]=v2
    return flat

def extract_field(flat, aliases):
    table={norm_key(k):k for k in flat.keys()}
    for alias in aliases:
        n=norm_key(alias)
        if n in table: return listify(flat[table[n]])
        for nk,orig in table.items():
            if n in nk or nk in n: return listify(flat[orig])
    return []

def auto_fit_font(draw, cands, base_size, text, max_width, min_size=36, step=2):
    size = base_size
    while size > min_size:
        f = load_font(cands, size)
        if tw(draw, f, text) <= max_width: return f
        size -= step
    return load_font(cands, max(min_size, 24))

# ===== Exclusions & Music =====
def load_excluded_markets() -> set:
    names = set()
    try:
        if os.path.exists(EXCLUDE_FILE):
            with open(EXCLUDE_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if s: names.add(s.lower())
    except Exception as e:
        print("⚠️ Could not read exclude_markets.txt:", e)
    return names

def is_premium_entry(flat: Dict[str, Any]) -> bool:
    for k in ("premium", "is_premium", "vip"):
        if k in flat and str(flat[k]).lower() in ("1","true","yes","y"):
            return True
    if str(flat.get("tier","")).lower() in ("premium","vip","gold"):
        return True
    name = str(flat.get("market") or flat.get("market_name") or "").lower()
    if any(kw in name for kw in ("premium","vip")):
        return True
    return False

def _list_audio(dir_path: str) -> List[str]:
    try:
        if not os.path.isdir(dir_path): return []
        return [os.path.join(dir_path, fn) for fn in os.listdir(dir_path)
                if fn.lower().endswith(AUDIO_EXTS)]
    except Exception:
        return []

def pick_music_path() -> Optional[str]:
    # 1) Preferred folder: /music
    if os.path.isdir(MUSIC_DIR):
        pref = os.path.join(MUSIC_DIR, PREFERRED_MUSIC_NAME)
        if os.path.exists(pref):
            return pref
        # any audio in music/
        candidates = _list_audio(MUSIC_DIR)
        if candidates:
            ranked = sorted(
                candidates,
                key=lambda p: (not any(k in os.path.basename(p).lower() for k in ("bgm","music","beat","loop")),
                               os.path.basename(p).lower())
            )
            return ranked[0]

    # 2) Fallback: /assets
    if os.path.isdir(ASSETS_DIR):
        pref = os.path.join(ASSETS_DIR, PREFERRED_MUSIC_NAME)
        if os.path.exists(pref):
            return pref
        candidates = _list_audio(ASSETS_DIR)
        if candidates:
            ranked = sorted(
                candidates,
                key=lambda p: (not any(k in os.path.basename(p).lower() for k in ("bgm","music","beat","loop")),
                               os.path.basename(p).lower())
            )
            return ranked[0]

    return None

# ===== Slide Drawing (same as before) =====
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

def draw_digits_row_centered(canvas, d, y, label: str, digits: List[str],
                             base_size: int, tracking: int = 30):
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
    title_txt = clean_market_title(entry["market"])
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

    if SHOW_VERSION:
        small = load_font(SECONDARY_FONT_CANDS, 22)
        glow_text(canvas, d, (PAD, H - PAD - 22), "v4.6.2", small, (200,200,200), (0,0,0), 2)

    if DEBUG:
        dd = ImageDraw.Draw(canvas)
        dd.rectangle((PAD, SAFE_TOP, W-PAD, H-SAFE_BOTTOM), outline=(255,0,0), width=2)

    return canvas

# ===== Data load =====
def load_entries() -> List[Dict[str, Any]]:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    exclude_names = load_excluded_markets()
    entries=[]; iterable=[]
    if isinstance(raw, list): iterable=[(None,x) for x in raw]
    elif isinstance(raw, dict): iterable=list(raw.items())

    for i,(k,v) in enumerate(iterable):
        if not isinstance(v, dict): continue
        flat = flatten_shallow(v)

        if is_premium_entry(flat):
            continue

        market = flat.get("market") or flat.get("market_name") or k or f"MARKET_{i}"
        if market and market.lower() in exclude_names:
            continue

        open_digits  = extract_field(flat, ["Open Digit","open_digit","openDigits","opendigit","o_digit","open"])
        close_digits = extract_field(flat, ["Close Digit","close_digit","closeDigits","closedigit","c_digit","close"])
        jodis        = extract_field(flat, ["Jodi","jodi","jodis","pair","pair_jodi","jodi_list"])
        open_pannas  = extract_field(flat, ["Open Panna","open_panna","openPanna","openpanna","open_pannas","o_panna"])
        close_pannas = extract_field(flat, ["Close Panna","close_panna","closePanna","closepanna","close_pannas","c_panna"])

        entries.append({
            "market": market,
            "open_digits": open_digits, "close_digits": close_digits,
            "jodis": jodis, "open_pannas": open_pannas, "close_pannas": close_pannas
        })

    t = (TEST_MARKET_SUBSTR or "").lower().strip()
    if t:
        entries = [e for e in entries if t in (e["market"] or "").lower()]
    if MAX_MARKETS:
        entries = entries[:MAX_MARKETS]
    return entries

# ===== Video build =====
def ken_burns_zoom(clip, start=1.0, end=1.05):
    dur = max(clip.duration, 1e-6)
    def scale(t): return start + (end - start) * (t / dur)
    zoomed = clip.resized(lambda t: scale(t)).with_duration(clip.duration).with_fps(FPS)
    bg = ImageClip(np.zeros((H, W, 3), dtype=np.uint8)).with_duration(clip.duration).with_fps(FPS)
    return CompositeVideoClip([bg, zoomed.with_position(("center","center"))], size=(W,H)).with_fps(FPS)

def build_video(slide_imgs: List[Image.Image], out_path: str):
    ensure_dir(os.path.dirname(out_path))
    clips, tmp_paths = [], []

    for idx, im in enumerate(slide_imgs):
        tmp_png = out_path.replace(".mp4","") + f"_frame_{idx:03d}.png"
        im.save(tmp_png, optimize=True); tmp_paths.append(tmp_png)
        base = ImageClip(tmp_png).with_duration(PER_SLIDE_SEC).with_fps(FPS)
        s, e = (ZOOM_START, ZOOM_END) if idx % 2 == 0 else (ZOOM_END, ZOOM_START)
        clips.append(ken_burns_zoom(base, s, e))

    if not clips:
        raise SystemExit("No clips to render (slides list empty).")

    video = concatenate_videoclips(clips).with_fps(FPS)

    # —— Music selection (music/ preferred, then assets/)
    music_path = pick_music_path()
    if music_path and os.path.exists(music_path):
        try:
            print(f"♪ Using audio: {music_path}")
            music = AudioFileClip(music_path)
            if music.duration >= video.duration:
                music = music.subclip(0, video.duration)
            music = music.audio_fadein(0.6).audio_fadeout(0.9)
            video = video.set_audio(music.volumex(0.45))
        except Exception as e:
            print(f"⚠️ Audio load failed ({music_path}):", e)
    else:
        # Helpful debug: list what we can see in both folders
        print("ℹ️ No audio found. Looked here:")
        print("   MUSIC_DIR:", MUSIC_DIR)
        print("   ASSETS_DIR:", ASSETS_DIR)
        print("   Files in MUSIC_DIR:", _list_audio(MUSIC_DIR))
        print("   Files in ASSETS_DIR:", _list_audio(ASSETS_DIR))

    video.write_videofile(
        out_path, fps=FPS, codec="libx264", audio_codec="aac",
        audio=True,
        threads=4, preset="medium", bitrate="6000k",
        ffmpeg_params=["-pix_fmt","yuv420p"],
        logger="bar"
    )

    for p in tmp_paths:
        try: os.remove(p)
        except: pass

def safe_filename(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+","_", s).strip("_") or "MARKET"

def main():
    now = datetime.datetime.now()
    date_disp = now.strftime("%d-%m-%Y")
    out_dir = os.path.join(OUT_ROOT, now.strftime("%Y-%m-%d"))
    slides_dir = os.path.join(out_dir, "slides_type1")
    ensure_dir(slides_dir)

    entries = load_entries()
    if not entries:
        raise SystemExit("No entries found in todays_predictions.json")

    # For each entry, render a single slide and build a per-market video
    for idx, e in enumerate(entries, start=1):
        try:
            img = render_slide(e, date_disp)
            safe = safe_filename(clean_market_title(e["market"]))
            slide_file = os.path.join(slides_dir, f"{safe}.png")
            img.save(slide_file, optimize=True)

            # Build a small list (single-slide). Keeps API consistent so build_video works unchanged.
            slide_imgs = [img]

            # Per-market video path (unique)
            timestamp = now.strftime('%Y%m%d_%H%M%S')
            market_out = os.path.join(out_dir, f"Reels_{safe}_{timestamp}.mp4")

            print(f"▶ Rendering video for ({idx}/{len(entries)}) : {e['market']} -> {market_out}")
            build_video(slide_imgs, market_out)
            print("  ✅ Done:", market_out)
        except Exception as ex:
            print(f"⚠️ Failed to render market '{e.get('market')}' : {ex}")

    print("✅ All done. Videos are in:", out_dir)

if __name__ == "__main__":
    main()
