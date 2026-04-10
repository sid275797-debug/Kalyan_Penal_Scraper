#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v3 — Fixes: debug logging, totals slide, improved pill layout & sizing
Reads prediction_score_report.json (local or uploaded fallback). :contentReference[oaicite:1]{index=1}
"""

import os, json, datetime, math, re
from typing import Dict, Any, List
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip

# ===== CONFIG =====
BASE_DIR = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper"
REPORT_PATHS = [
    os.path.join(BASE_DIR, "sattaboss-data", "data", "prediction_score_report.json"),
    os.path.join(BASE_DIR, "sattaboss-data", "data", "score_only_json_verbose.json"),
    "/mnt/data/prediction_score_report.json"
]
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
MUSIC_DIR = os.path.join(BASE_DIR, "music")
OUT_ROOT = os.path.join(BASE_DIR, "video_output")

W, H = 1080, 1920
FPS = 30
PER_SLIDE_SEC = 3.6
ZOOM_START, ZOOM_END = 1.00, 1.06

BG_TOP=(5,6,10); BG_BOT=(2,2,5)
WHITE=(255,255,255); DIM=(222,226,234)
CYAN=(0,229,255); MAGENTA=(255,29,206)
GOOD=(24,200,100)

PAD = 84
SAFE_TOP, SAFE_BOTTOM = 100, 170

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

GENERATE_VERTICAL_SHORT = False
MAX_MARKETS = None

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
    try:
        b = font.getbbox("Hg0123456789"); return int(b[3] - b[1])
    except Exception:
        a,d = font.getmetrics(); return int(a + d)

def bg_make(size):
    w,h = size
    t = np.linspace(0,1,h)[:,None,None]
    top = np.array(BG_TOP, dtype=np.float32)[None,None,:]
    bot = np.array(BG_BOT, dtype=np.float32)[None,None,:]
    grad = top*(1-t) + bot*t
    arr = np.repeat(grad, w, axis=1).astype(np.uint8)
    img = Image.fromarray(arr).convert("RGBA")
    sl = Image.new("RGBA", (w,h), (0,0,0,0)); d = ImageDraw.Draw(sl)
    for yy in range(0,h,10): d.line([(0,yy),(w,yy)], fill=(255,255,255,10), width=1)
    img.alpha_composite(sl)
    return img

def glow_text(canvas, draw, xy, text, font, fill, glow, radius=6):
    if not text: return
    g = Image.new("RGBA", canvas.size, (0,0,0,0))
    gd = ImageDraw.Draw(g)
    gd.text(xy, text, font=font, fill=(glow[0],glow[1],glow[2],255))
    g = g.filter(ImageFilter.GaussianBlur(radius))
    canvas.alpha_composite(g); draw.text(xy, text, font=font, fill=fill)

def rounded_rect_on(canvas, xy, radius, fill, outline=None, width=2, blur=0):
    tmp = Image.new("RGBA", canvas.size, (0,0,0,0))
    td = ImageDraw.Draw(tmp)
    td.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    if blur: tmp = tmp.filter(ImageFilter.GaussianBlur(4))
    canvas.alpha_composite(tmp)

# ===== IO =====
def load_report(paths):
    for p in paths:
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data, p
        except Exception:
            pass
    raise FileNotFoundError("No report JSON found in: " + ", ".join(paths))

# ===== Renderers =====
def render_title(report, path_used, size=(W,H)):
    canvas = bg_make(size); d = ImageDraw.Draw(canvas, "RGBA")
    title_f = load_font(PRIMARY_FONT_CANDS, 72)
    small_f = load_font(SECONDARY_FONT_CANDS, 30)
    title = "SCORE SUMMARY (HITS)"
    date_txt = datetime.datetime.now().strftime("%d-%m-%Y")
    glow_text(canvas, d, ((size[0]-tw(d,title_f,title))//2, PAD), title, title_f, WHITE, CYAN, 8)
    glow_text(canvas, d, ((size[0]-tw(d,small_f,date_txt))//2, PAD+th(title_f)+12), date_txt, small_f, DIM, MAGENTA, 4)
    footer = f"Source: {os.path.basename(path_used)}"
    d.text((PAD, size[1]-PAD-th(small_f)), footer, font=small_f, fill=DIM)
    return canvas

def render_totals_slide(report, size=(W,H)):
    canvas = bg_make(size); d = ImageDraw.Draw(canvas, "RGBA")
    title_f = load_font(PRIMARY_FONT_CANDS, 56)
    big_f = load_font(PRIMARY_FONT_CANDS, 44)
    small_f = load_font(SECONDARY_FONT_CANDS, 32)
    glow_text(canvas, d, ((size[0]-tw(d,title_f,"TOTALS"))//2, PAD), "TOTALS", title_f, WHITE, CYAN, 8)
    summary = report.get("summary", {})
    counts = summary.get("hit_counts", {})
    lines = [
        f"Markets scored: {summary.get('markets_scored',0)}",
        f"Open Digit hits: {counts.get('open_digit',0)}",
        f"Close Digit hits: {counts.get('close_digit',0)}",
        f"Jodi hits: {counts.get('jodi',0)}",
        f"Open Panna hits: {counts.get('open_panna',0)}",
        f"Close Panna hits: {counts.get('close_panna',0)}"
    ]
    y = PAD + th(title_f) + 24
    for i,ln in enumerate(lines):
        fnt = big_f if i==0 else big_f
        color = WHITE if i==0 else DIM
        glow_text(canvas, d, (PAD+10, y + i*(th(big_f)+12)), ln, fnt, color, CYAN, 3)
    return canvas

def render_market_slide(mk, obj, size=(W,H)):
    canvas = bg_make(size); d = ImageDraw.Draw(canvas, "RGBA")
    title_f = load_font(PRIMARY_FONT_CANDS, 56)
    pill_f = load_font(SECONDARY_FONT_CANDS, 40)  # slightly larger for readability
    name = str(mk).replace("_"," ").upper()
    glow_text(canvas, d, ((size[0]-tw(d,title_f,name))//2, SAFE_TOP), name, title_f, WHITE, CYAN, 8)

    hits = obj.get("hits", {}) if isinstance(obj, dict) else {}
    labels = [("open_digit","OPEN"), ("close_digit","CLOSE"), ("jodi","JODI"),
              ("open_panna","OPEN PANNA"), ("close_panna","CLOSE PANNA")]

    true_pills = []
    for key,label in labels:
        val = hits.get(key)
        if isinstance(val,bool) and val: true_pills.append(label)
        elif isinstance(val,(int,float)) and int(val)==1: true_pills.append(label)
        elif isinstance(val,str) and val.strip().lower() in ("1","true","yes","y"): true_pills.append(label)

    y = SAFE_TOP + th(title_f) + 36
    inner_w = size[0] - 2*PAD
    pill_h = 78
    gap = 20

    if not true_pills:
        glow_text(canvas, d, ((size[0]-tw(d,pill_f,"NO HITS"))//2, y), "NO HITS", pill_f, DIM, MAGENTA, 4)
    else:
        # Layout: try one row, otherwise wrap automatically with balanced centering
        rows = []
        cur = []
        cur_w = 0
        for p in true_pills:
            wbox = tw(d,pill_f,p) + 56
            if cur and (cur_w + gap + wbox) > inner_w:
                rows.append(cur); cur = [ (p,wbox) ]; cur_w = wbox
            else:
                cur.append((p,wbox)); cur_w += (wbox if cur_w==0 else (gap + wbox))
        if cur: rows.append(cur)

        row_y = y
        for row in rows:
            total_w = sum(w for _,w in row) + (len(row)-1)*gap
            cur_x = PAD + (inner_w - total_w)//2
            for ptxt,wbox in row:
                rect = (cur_x, row_y, cur_x + wbox, row_y + pill_h)
                rounded_rect_on(canvas, rect, 36, (24,200,100,230), None, 0, blur=4)
                glow_text(canvas, d, (cur_x + (wbox - tw(d,pill_f,ptxt))//2, row_y + (pill_h - th(pill_f))//2),
                          ptxt, pill_f, WHITE, (0,140,80), 3)
                cur_x += wbox + gap
            row_y += pill_h + gap

    if os.path.exists(LOGO_PATH):
        try:
            raw = Image.open(LOGO_PATH).convert("RGBA")
            w0,h0 = raw.size; scale = 100 / max(1,h0)
            logo = raw.resize((int(w0*scale), int(h0*scale)), Image.LANCZOS)
            canvas.alpha_composite(logo, (size[0]-PAD-logo.size[0], size[1]-PAD-logo.size[1]))
        except Exception:
            pass
    return canvas

# ===== Video helpers =====
def _list_audio(dir_path):
    try:
        if not os.path.isdir(dir_path): return []
        return [os.path.join(dir_path, fn) for fn in os.listdir(dir_path) if fn.lower().endswith((".mp3",".m4a",".aac",".wav",".ogg",".flac"))]
    except: return []

def pick_music_path():
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

def build_video(slide_imgs: List[Image.Image], out_path: str, size=(W,H)):
    ensure_dir(os.path.dirname(out_path))
    clips=[]; tmp_paths=[]
    for idx, im in enumerate(slide_imgs):
        tmp = out_path.replace(".mp4","") + f"_frame_{idx:03d}.png"
        im.save(tmp, optimize=True); tmp_paths.append(tmp)
        base = ImageClip(tmp).with_duration(PER_SLIDE_SEC).with_fps(FPS)
        # compatibility handling
        try:
            base_resized = base.resized(new_size=size)
        except TypeError:
            base_resized = base.resized(newsize=size) if hasattr(base, "resized") else base
        s,e = (ZOOM_START, ZOOM_END) if idx%2==0 else (ZOOM_END, ZOOM_START)
        clips.append(ken_burns_zoom(base_resized, s, e))

    if not clips:
        raise SystemExit("No slides to render.")
    video = concatenate_videoclips(clips).with_fps(FPS)
    music = pick_music_path()
    if music:
        try:
            audio = AudioFileClip(music)
            if audio.duration >= video.duration: audio = audio.subclip(0, video.duration)
            audio = audio.audio_fadein(0.6).audio_fadeout(0.9)
            video = video.set_audio(audio.volumex(0.45))
            print("♪ Using audio:", music)
        except Exception as e:
            print("Warning: audio load failed:", e)
    else:
        print("ℹ️ No audio found.")
    video.write_videofile(out_path, fps=FPS, codec="libx264", audio_codec="aac", threads=4, preset="medium", bitrate="5000k", ffmpeg_params=["-pix_fmt","yuv420p"])
    for p in tmp_paths:
        try: os.remove(p)
        except: pass

# ===== Main =====
def main():
    report, path_used = load_report(REPORT_PATHS)
    print("Loaded report from:", path_used)
    markets = report.get("markets", {}) if isinstance(report, dict) else {}
    print(f"Total markets in report: {len(markets)}")

    # Collect markets that have at least one hit == true
    selected = []
    for mk, obj in markets.items():
        hits = obj.get("hits", {}) if isinstance(obj, dict) else {}
        if any(
            (isinstance(hits.get(k), bool) and hits.get(k)) or
            (isinstance(hits.get(k),(int,float)) and int(hits.get(k))==1) or
            (isinstance(hits.get(k), str) and hits.get(k).strip().lower() in ("1","true","yes","y"))
            for k in ("open_digit","close_digit","jodi","open_panna","close_panna")
        ):
            selected.append((mk, obj))

    print(f"Markets with at least one hit: {len(selected)}")
    if len(selected) > 0:
        # print first 10 for quick inspection
        print("Sample selected markets (up to 10) and their hits:")
        for mk, obj in selected[:10]:
            print(f" - {mk} -> {obj.get('hits')}")

    if not selected:
        raise SystemExit("No markets with hits found in report (exiting).")

    if MAX_MARKETS:
        selected = selected[:MAX_MARKETS]

    now = datetime.datetime.now()
    date_dir = now.strftime("%Y-%m-%d")
    out_dir = os.path.join(OUT_ROOT, date_dir); ensure_dir(out_dir)

    slides = []
    slides.append(render_title(report, path_used, size=(W,H)))
    for mk, obj in selected:
        slides.append(render_market_slide(mk, obj, size=(W,H)))
    slides.append(render_totals_slide(report, size=(W,H)))

    ts = now.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"Score_Summary_PremiumStyle_{ts}.mp4")
    build_video(slides, out_path, size=(W,H))
    print("✅ Video written:", out_path)

if __name__ == "__main__":
    main()
