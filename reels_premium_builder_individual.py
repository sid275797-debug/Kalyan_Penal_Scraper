#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reels_premium_builder_individual.py
- Produces ONE MP4 per premium market (single-slide video per market)
- Keeps Type-1 visuals, Ken-Burns, music, logo, and compatibility fixes
- Place in project folder and run as before.
"""

import os, re, json, math, datetime
from typing import Dict, Any, List, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# MoviePy 2.x
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip

# ===== CONFIG =====
BASE_DIR    = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper"
JSON_PATH   = os.path.join(BASE_DIR, "sattaboss-data", "data", "todays_predictions.json")
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
MUSIC_DIR   = os.path.join(BASE_DIR, "music")
LOGO_PATH   = os.path.join(ASSETS_DIR, "logo.png")
OUT_ROOT    = os.path.join(BASE_DIR, "video_output")

# Force premium keywords — includes Time Bazar and Main Bazar (variants)
FORCE_PREMIUM_KEYWORDS = (
    "kalyan","rajdhani","milan",
    "time bazar","timebazar","time-bazar","time bazaar","timebazaar",
    "main bazar","mainbazar","main-bazar","main bazaar","mainbazaar",
    "starline","supreme"
)

# Behavior flags
GENERATE_PREMIUM_ONLY = True
PER_MARKET_ONLY = True          # <-- produce one file per market
GENERATE_VERTICAL_SHORT = True  # per-market short as well
GENERATE_AGGREGATE = False      # if True, also produce combined video (set as needed)
MAX_MARKETS = None
TEST_MARKET_SUBSTR = ""

# Video params
W, H = 1080, 1920
FPS = 30
PER_SLIDE_SEC = 3.6
ZOOM_START, ZOOM_END = 1.00, 1.06

# Visual
PAD  = 84
SAFE_TOP, SAFE_BOTTOM = 100, 170
BG_TOP=(5,6,10); BG_BOT=(2,2,5)
WHITE=(255,255,255); DIM=(222,226,234)
CYAN=(0,229,255); MAGENTA=(255,29,206); YELLOW=(255,214,51)
CARD_BG=(12,14,22,230); CARD_ST=(0,229,255,60)
PILL_BG=(8,10,16,230);  PILL_ST=(0,229,255,220)

# Fonts
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
]

BASE_SIZES = {
    "title": 68, "date": 50, "tag": 46,
    "open": 136, "close": 136,
    "jodi": 64, "chip_h": 96, "chip_gap": 18, "chip_pad_x": 40,
    "pill": 42, "pill_h": 72, "pill_gap": 14,
}

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
    except: a,d = font.getmetrics(); return int(a + d)

def bg_make(size):
    w,h=size
    t=np.linspace(0,1,h)[:,None,None]
    top=np.array(BG_TOP,dtype=np.float32)[None,None,:]
    bot=np.array(BG_BOT,dtype=np.float32)[None,None,:]
    grad=top*(1-t)+bot*t
    arr=np.repeat(grad,w,axis=1).astype(np.uint8)
    img=Image.fromarray(arr).convert("RGBA")
    sl=Image.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(sl)
    for yy in range(0,h,10): d.line([(0,yy),(w,yy)], fill=(255,255,255,12), width=1)
    img.alpha_composite(sl); return img

def glow_text(canvas, draw, xy, text, font, fill, glow, radius=6):
    if not text: return
    g=Image.new("RGBA",canvas.size,(0,0,0,0)); gd=ImageDraw.Draw(g)
    gd.text(xy,text,font=font,fill=(glow[0],glow[1],glow[2],255))
    g=g.filter(ImageFilter.GaussianBlur(radius))
    canvas.alpha_composite(g); draw.text(xy,text,font=font,fill=fill)

def rounded_rect_on(canvas, xy, radius, fill, outline=None, width=2, blur=0):
    tmp=Image.new("RGBA",canvas.size,(0,0,0,0)); td=ImageDraw.Draw(tmp)
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
    if isinstance(v, str): return [p for p in re.split(r'[,\n;]+', v.strip()) if p.strip()]
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

# ===== Premium detection =====
def load_excluded_markets() -> set:
    names=set()
    try:
        ex = os.path.join(ASSETS_DIR, "exclude_markets.txt")
        if os.path.exists(ex):
            with open(ex, "r", encoding="utf-8") as f:
                for ln in f:
                    s=ln.strip()
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
    if any(kw in name for kw in ("premium","vip")):
        return True
    return False

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
        name_lower = str(flat.get("market") or flat.get("market_name") or k or "").lower()
        forced_premium = any(kw in name_lower for kw in FORCE_PREMIUM_KEYWORDS)
        premium = is_premium_entry(flat) or forced_premium
        if GENERATE_PREMIUM_ONLY and not premium: continue
        market = flat.get("market") or flat.get("market_name") or k or f"MARKET_{i}"
        if market and market.lower() in exclude_names: continue
        entries.append({
            "market": market,
            "open_digits": extract_field(flat, ["Open Digit","open_digit","open"]),
            "close_digits": extract_field(flat, ["Close Digit","close_digit","close"]),
            "jodis": extract_field(flat, ["Jodi","jodi","pair"]),
            "open_pannas": extract_field(flat, ["Open Panna","open_panna","openpanna"]),
            "close_pannas": extract_field(flat, ["Close Panna","close_panna","closepanna"]),
            "premium": premium
        })
    if TEST_MARKET_SUBSTR:
        t = TEST_MARKET_SUBSTR.lower().strip()
        entries = [e for e in entries if t in (e["market"] or "").lower()]
    if MAX_MARKETS:
        entries = entries[:MAX_MARKETS]
    return entries

# ===== Slide drawing (same as Type-1) =====
def draw_header_centered(canvas, d, y, title_txt, date_txt):
    date_f = load_font(PRIMARY_FONT_CANDS, BASE_SIZES["date"])
    t_w = tw(d, date_f, date_txt)
    glow_text(canvas, d, ((W - t_w)//2, y), date_txt, date_f, DIM, MAGENTA, 5)
    y += th(date_f) + 10
    title_f = load_font(PRIMARY_FONT_CANDS, BASE_SIZES["title"])
    t_w = tw(d, title_f, title_txt)
    glow_text(canvas, d, ((W - t_w)//2, y), title_txt, title_f, WHITE, CYAN, 8)
    y += th(title_f) + 18
    return y

def measure_digits_uniform(draw, font, digits: List[str], tracking: int) -> (int,int,int):
    h = th(font)
    samples = [str(x) for x in digits if str(x).strip()] or ["0"]
    max_w = max(tw(draw, font, ch) for ch in samples + list("0123456789"))
    block_w = len(samples)*max_w + (len(samples)-1)*tracking
    return block_w, h, max_w

def draw_digits_row_centered(canvas, d, y, label: str, digits: List[str], base_size: int, tracking: int = 30):
    digits = [str(x) for x in (digits or []) if str(x).strip()] or ["—","—","—","—"]
    size = base_size
    while size >= 96:
        f = load_font(PRIMARY_FONT_CANDS, size)
        block_w, block_h, box_w = measure_digits_uniform(d, f, digits, tracking)
        if block_w <= (W - 2*PAD): break
        size -= 4
    f = load_font(PRIMARY_FONT_CANDS, size)
    tag_f = load_font(PRIMARY_FONT_CANDS, BASE_SIZES["tag"])
    lbl_w = tw(d, tag_f, label)
    glow_text(canvas, d, ((W - lbl_w)//2, y), label, tag_f, DIM, WHITE, 4)
    y += th(tag_f) + BASE_SIZES["pill_gap"]//2 + 2
    block_w, block_h, box_w = measure_digits_uniform(d, f, digits, tracking)
    start_x = (W - block_w)//2
    row_y = y
    x = start_x
    for i, ch in enumerate(digits):
        g_w = tw(d, f, ch)
        gx = x + (box_w - g_w)//2
        glow_text(canvas, d, (gx, row_y), ch, f, WHITE, WHITE, 6)
        x += box_w
        if i < len(digits) - 1: x += tracking
    return row_y + block_h + 22

def draw_jodi_flow(canvas, d, y, chips: List[str]):
    tag_f = load_font(PRIMARY_FONT_CANDS, BASE_SIZES["tag"])
    ttl = "JODI"
    glow_text(canvas, d, ((W - tw(d, tag_f, ttl))//2, y), ttl, tag_f, DIM, YELLOW, 4)
    y += th(tag_f) + 8
    inner_w = W - 2*PAD
    chip_f = load_font(PRIMARY_FONT_CANDS, BASE_SIZES["jodi"])
    pad_x = BASE_SIZES["chip_pad_x"]; gap = BASE_SIZES["chip_gap"]; h = BASE_SIZES["chip_h"]
    chips = chips or ["—"]
    chips = chips[:10]
    chip_w = [tw(d, chip_f, s) + 2*pad_x for s in chips]
    total_w = sum(chip_w) + gap*(len(chip_w)-1)
    x = PAD + max(0,(inner_w - total_w)//2)
    for s,w in zip(chips, chip_w):
        rounded_rect_on(canvas, (x, y, x+w, y+h), 36, PILL_BG, PILL_ST, 2, blur=4)
        glow_text(canvas, d, (x + (w - tw(d, chip_f, s))//2, y + (h - th(chip_f))//2), s, chip_f, WHITE, CYAN, 3)
        x += w + gap
    return y + h + 26

def render_slide(entry: Dict[str, Any], date_str: str) -> Image.Image:
    canvas = bg_make((W,H)); d = ImageDraw.Draw(canvas, "RGBA")
    title_txt = clean_market_title(entry["market"])
    date_txt = f"DATE: {date_str}"
    y = SAFE_TOP
    y = draw_header_centered(canvas, d, y, title_txt, date_txt)
    y = draw_digits_row_centered(canvas, d, y, "OPEN", entry.get("open_digits"), BASE_SIZES["open"])
    y = draw_digits_row_centered(canvas, d, y, "CLOSE", entry.get("close_digits"), BASE_SIZES["close"])
    y = draw_jodi_flow(canvas, d, y, entry.get("jodis"))
    # PANNA card
    tag_f = load_font(PRIMARY_FONT_CANDS, BASE_SIZES["tag"])
    open_list = (entry.get("open_pannas") or [])[:8] or ["—"]
    close_list = (entry.get("close_pannas") or [])[:8] or ["—"]
    card_left, card_right = PAD, W - PAD
    inner_l = card_left + 24; inner_r = card_right - 24
    col_w = (inner_r - inner_l - 16)//2
    yy = H - SAFE_BOTTOM - (BASE_SIZES["pill_h"]*2 + 120)
    rounded_rect_on(canvas, (card_left, yy, card_right, yy + 180), 28, CARD_BG, CARD_ST, 2, blur=0)
    pill_f = load_font(SECONDARY_FONT_CANDS, BASE_SIZES["pill"])
    glow_text(canvas, d, (inner_l, yy + 18), "OPEN PANNA", tag_f, DIM, CYAN, 4)
    glow_text(canvas, d, (inner_l + col_w + 16, yy + 18), "CLOSE PANNA", tag_f, DIM, CYAN, 4)
    ay = yy + 18 + th(tag_f) + 8
    xL = inner_l
    for p in open_list[:4]:
        wbox = tw(d, pill_f, p) + 28
        rounded_rect_on(canvas, (xL, ay, xL + wbox, ay + BASE_SIZES["pill_h"]), 20, PILL_BG, PILL_ST, 2, blur=4)
        glow_text(canvas, d, (xL + (wbox - tw(d, pill_f, p))//2, ay + (BASE_SIZES["pill_h"] - th(pill_f))//2), p, pill_f, WHITE, CYAN, 3)
        xL += wbox + 12
    xR = inner_l + col_w + 16
    for p in close_list[:4]:
        wbox = tw(d, pill_f, p) + 28
        rounded_rect_on(canvas, (xR, ay, xR + wbox, ay + BASE_SIZES["pill_h"]), 20, PILL_BG, PILL_ST, 2, blur=4)
        glow_text(canvas, d, (xR + (wbox - tw(d, pill_f, p))//2, ay + (BASE_SIZES["pill_h"] - th(pill_f))//2), p, pill_f, WHITE, CYAN, 3)
        xR += wbox + 12
    # logo
    if os.path.exists(LOGO_PATH):
        try:
            raw = Image.open(LOGO_PATH).convert("RGBA")
            w0,h0 = raw.size; scale = 100 / max(1,h0)
            logo = raw.resize((int(w0*scale), int(h0*scale)), Image.LANCZOS)
            canvas.alpha_composite(logo, (W-PAD-logo.size[0], H-PAD-logo.size[1]))
        except: pass
    return canvas

# ===== Video utilities =====
def _list_audio(dir_path: str) -> List[str]:
    try:
        if not os.path.isdir(dir_path): return []
        return [os.path.join(dir_path, fn) for fn in os.listdir(dir_path) if fn.lower().endswith((".mp3",".m4a",".aac",".wav",".ogg",".flac"))]
    except Exception:
        return []

def pick_music_path() -> Optional[str]:
    if os.path.isdir(MUSIC_DIR):
        pref = os.path.join(MUSIC_DIR, "bgm.mp3")
        if os.path.exists(pref): return pref
        cand = _list_audio(MUSIC_DIR)
        if cand: return sorted(cand)[0]
    if os.path.isdir(ASSETS_DIR):
        pref = os.path.join(ASSETS_DIR, "bgm.mp3")
        if os.path.exists(pref): return pref
        cand = _list_audio(ASSETS_DIR)
        if cand: return sorted(cand)[0]
    return None

def ken_burns_zoom(clip, start=1.0, end=1.05):
    dur = max(clip.duration, 1e-6)
    def scale(t): return start + (end - start) * (t / dur)
    zoomed = clip.resized(lambda t: scale(t)).with_duration(clip.duration).with_fps(FPS)
    bg = ImageClip(np.zeros((clip.size[1], clip.size[0], 3), dtype=np.uint8)).with_duration(clip.duration).with_fps(FPS)
    return CompositeVideoClip([bg, zoomed.with_position(("center","center"))], size=(clip.size[0], clip.size[1])).with_fps(FPS)

def sanitize_filename(s: str) -> str:
    safe = re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_')
    return safe or "MARKET"

def build_video(slide_imgs: List[Image.Image], out_path: str, size=(W,H)):
    ensure_dir(os.path.dirname(out_path))
    clips, tmp_paths = [], []
    for idx, im in enumerate(slide_imgs):
        tmp_png = out_path.replace(".mp4","") + f"_frame_{idx:03d}.png"
        im.save(tmp_png, optimize=True); tmp_paths.append(tmp_png)
        base = ImageClip(tmp_png).with_duration(PER_SLIDE_SEC).with_fps(FPS)
        # MoviePy API compatibility
        try:
            base_resized = base.resized(new_size=size)
        except TypeError:
            try: base_resized = base.resized(newsize=size)
            except: base_resized = base
        s, e = (ZOOM_START, ZOOM_END) if idx % 2 == 0 else (ZOOM_END, ZOOM_START)
        clips.append(ken_burns_zoom(base_resized, s, e))

    if not clips:
        raise SystemExit("No clips to render.")
    video = concatenate_videoclips(clips).with_fps(FPS)

    music_path = pick_music_path()
    if music_path:
        try:
            music = AudioFileClip(music_path)
            if music.duration >= video.duration:
                music = music.subclip(0, video.duration)
            music = music.audio_fadein(0.6).audio_fadeout(0.9)
            video = video.set_audio(music.volumex(0.45))
            print("♪ Using audio:", music_path)
        except Exception as e:
            print("⚠️ Audio load failed:", e)
    else:
        print("ℹ️ No audio found.")

    video.write_videofile(out_path, fps=FPS, codec="libx264", audio_codec="aac",
                          audio=True, threads=4, preset="medium", bitrate="6000k",
                          ffmpeg_params=["-pix_fmt","yuv420p"], logger="bar")

    for p in tmp_paths:
        try: os.remove(p)
        except: pass

# ===== Main =====
def main():
    now = datetime.datetime.now()
    date_disp = now.strftime("%d-%m-%Y")
    out_dir = os.path.join(OUT_ROOT, now.strftime("%Y-%m-%d")); ensure_dir(out_dir)

    entries = load_entries()
    print(f"Found {len(entries)} premium markets to render.")
    if not entries:
        raise SystemExit("No premium entries found (check FORCE_PREMIUM_KEYWORDS & JSON).")

    # PER-MARKET loop
    created = []
    for e in entries:
        safe = sanitize_filename(clean_market_title(e["market"]))
        ts = now.strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(out_dir, f"Premium_{safe}_{ts}.mp4")
        img = render_slide(e, date_disp)
        build_video([img], out_path, size=(W,H))
        print("✅ Created:", out_path)
        created.append(out_path)

        if GENERATE_VERTICAL_SHORT:
            short_out = os.path.join(out_dir, f"Premium_{safe}_SHORT_{ts}.mp4")
            build_video([img], short_out, size=(W,H))
            print("✅ Created short:", short_out)
            created.append(short_out)

    # optional aggregate (disabled by default)
    if GENERATE_AGGREGATE:
        slides = [render_slide(e, date_disp) for e in entries]
        agg_path = os.path.join(out_dir, f"Premium_Aggregate_{now.strftime('%Y%m%d_%H%M%S')}.mp4")
        build_video(slides, agg_path, size=(W,H))
        print("✅ Aggregate video:", agg_path)
        created.append(agg_path)

    print(f"Done. Created {len(created)} file(s) in {out_dir}")

if __name__ == "__main__":
    main()
