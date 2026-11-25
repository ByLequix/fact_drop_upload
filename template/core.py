import math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
OUT = os.path.dirname(os.path.abspath(__file__))

POP = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
POPM = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"
INTB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
_fc = {}
def font(p, s):
    k = (p, s)
    if k not in _fc: _fc[k] = ImageFont.truetype(p, s)
    return _fc[k]

BG1 = (8, 22, 48); BG2 = (14, 52, 92)
CORAL = (255, 112, 92); BLUE = (64, 170, 255); YEL = (255, 214, 64)
WHITE = (255, 255, 255); SOFT = (170, 195, 225)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_back(t):
    t = clamp(t); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2

# ---------- background (cached) ----------
def make_bg():
    bg = Image.new("RGB", (W, H))
    px = bg.load()
    col = []
    for y in range(H):
        f = y / H
        col.append(tuple(int(BG1[i] + (BG2[i] - BG1[i]) * (0.5 - 0.5 * math.cos(f * math.pi))) for i in range(3)))
    d = ImageDraw.Draw(bg)
    for y in range(H): d.line([(0, y), (W, y)], fill=col[y])
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([140, 560, 940, 1360], fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    bg = Image.composite(Image.new("RGB", (W, H), (40, 110, 170)), bg, glow)
    return bg
BG = make_bg()

# bubbles drift upward for life
import random
random.seed(4)
BUBBLES = [(random.uniform(40, W - 40), random.uniform(0, H), random.uniform(5, 16), random.uniform(25, 70)) for _ in range(26)]
def draw_bubbles(d, t):
    for x, y0, r, sp in BUBBLES:
        y = (y0 - t * sp) % (H + 40) - 20
        x2 = x + 10 * math.sin(t * 0.8 + y0)
        d.ellipse([x2 - r, y - r, x2 + r, y + r], outline=(60, 110, 165), width=2)

# ---------- text helpers ----------
def text_c(d, xy, s, f, fill, anchor="mm"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)

def overlay_alpha(base, layer, a):
    if a <= 0: return base
    if a >= 1: return Image.alpha_composite(base, layer)
    r, g, b, al = layer.split()
    al = al.point(lambda v: int(v * a))
    return Image.alpha_composite(base, Image.merge("RGBA", (r, g, b, al)))

# ---------- shapes (drawn at 2x then downscaled) ----------
S = 2
def shape_layer(size):
    return Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
def paste_shape(frame, layer, cx, cy, scale=1.0, alpha=1.0):
    size = layer.width // S
    sz = max(2, int(size * scale))
    small = layer.resize((sz, sz), Image.LANCZOS)
    if alpha < 1:
        a = small.split()[3].point(lambda v: int(v * alpha)); small.putalpha(a)
    frame.alpha_composite(small, (int(cx - sz / 2), int(cy - sz / 2)))

def octopus(t, size=760, wave=1.0):
    L = shape_layer(size); d = ImageDraw.Draw(L)
    k = S * size / 760
    cx, hy = 380 * k, 300 * k
    # tentacles
    for i in range(8):
        sx = (215 + i * 47) * k
        dirx = (i - 3.5) / 3.5
        pts = 60
        for j in range(pts):
            u = j / (pts - 1)
            x = sx + dirx * 170 * k * u + math.sin(u * 5 + t * 3 + i) * 34 * k * u * wave
            y = hy + 110 * k + u * 330 * k - (u ** 2) * 40 * k * abs(dirx)
            r = (30 - 22 * u) * k
            d.ellipse([x - r, y - r, x + r, y + r], fill=CORAL if i % 2 == 0 else (240, 96, 80))
    # head
    bob = math.sin(t * 2) * 10 * k
    d.ellipse([cx - 210 * k, hy - 250 * k + bob, cx + 210 * k, hy + 170 * k + bob], fill=CORAL)
    d.ellipse([cx - 150 * k, hy - 200 * k + bob, cx - 40 * k, hy - 110 * k + bob], fill=(255, 150, 130))
    for ex in (-80, 80):
        ex = cx + ex * k; ey = hy + 40 * k + bob
        d.ellipse([ex - 46 * k, ey - 46 * k, ex + 46 * k, ey + 46 * k], fill=WHITE)
        d.ellipse([ex - 22 * k, ey - 18 * k, ex + 26 * k, ey + 30 * k], fill=(20, 30, 50))
    d.arc([cx - 50 * k, hy + 80 * k + bob, cx + 50 * k, hy + 140 * k + bob], 20, 160, fill=(150, 50, 45), width=int(10 * k))
    return L

def heart_pts(cx, cy, s):
    pts = []
    for i in range(120):
        a = i / 120 * 2 * math.pi
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((cx + x * s, cy - y * s))
    return pts

def drop(size=600):
    L = shape_layer(size); d = ImageDraw.Draw(L)
    c = size * S / 2; r = size * S * 0.30; cy = c + size * S * 0.1
    tip = (c, cy - r * 2.1)
    pts = [tip]
    a0 = math.asin(r / (cy - tip[1]))  # tangent angle
    for i in range(101):
        a = -math.pi / 2 + a0 + (math.pi * 2 - 2 * a0) * i / 100
        pts.append((c + r * math.cos(a + math.pi), cy + r * math.sin(a + math.pi)))
    # rebuild with tangent geometry: simple arc from right tangent to left tangent around bottom
    pts = [tip]
    ang_t = math.pi / 2 - a0
    for i in range(101):
        a = -ang_t + (math.pi + 2 * ang_t) * i / 100
        pts.append((c + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=BLUE)
    d.ellipse([c - r * 0.6, cy - r * 0.55, c - r * 0.25, cy - r * 0.05], fill=(160, 215, 255))
    return L

# ---------- captions ----------
def chunk_words(text, maxw=4, maxc=24):
    words = text.split(); out = []; cur = []
    for w in words:
        if cur and (len(cur) >= maxw or len(" ".join(cur + [w])) > maxc):
            out.append(cur); cur = []
        cur.append(w)
    if cur: out.append(cur)
    return out

def build_caps(lines):
    """lines: list of (start, end, text). Returns list of (start,end,words,[word times])."""
    caps = []
    for st, en, txt in lines:
        chunks = chunk_words(txt)
        total = sum(len(w) + 2 for c in chunks for w in c)
        t = st
        for c in chunks:
            ws = []
            for w in c:
                dur = (en - st) * (len(w) + 2) / total
                ws.append((t, t + dur)); t += dur
            caps.append([ws[0][0], ws[-1][1], c, ws])
    for i in range(len(caps) - 1):
        caps[i][1] = caps[i + 1][0]
    if caps: caps[-1][1] += 0.3
    return caps

def draw_caption(frame, t, caps, y=1440):
    for st, en, words, wt in caps:
        if st <= t < en:
            f = font(INTB, 70)
            d0 = ImageDraw.Draw(frame)
            sp = d0.textlength(" ", font=f)
            widths = [d0.textlength(w, font=f) for w in words]
            tw = sum(widths) + sp * (len(words) - 1)
            pop = ease_back((t - st) / 0.18)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            pad = 34
            d.rounded_rectangle([W / 2 - tw / 2 - pad, y - 62, W / 2 + tw / 2 + pad, y + 62], radius=34, fill=(5, 12, 28, 200))
            x = W / 2 - tw / 2
            for w, wd, (a, b) in zip(words, widths, wt):
                col = YEL if a <= t < b else WHITE
                d.text((x, y), w, font=f, fill=col, anchor="lm", stroke_width=0)
                x += wd + sp
            if pop < 0.999:
                sc = 0.85 + 0.15 * pop
                box = lay.crop((0, y - 120, W, y + 120))
                nw, nh = int(W * sc), int(240 * sc)
                box = box.resize((nw, nh), Image.LANCZOS)
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                lay.alpha_composite(box, ((W - nw) // 2, y - nh // 2))
            frame.alpha_composite(lay)
            return

# ---------- chrome ----------
def draw_label(frame, t, n, a=1.0):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    f = font(POP, 40)
    s = f"FACT {n}/3"
    tw = d.textlength(s, font=f)
    d.rounded_rectangle([W / 2 - tw / 2 - 36, 220, W / 2 + tw / 2 + 36, 300], radius=40, fill=CORAL)
    d.text((W / 2, 262), s, font=f, fill=WHITE, anchor="mm")
    for i in range(3):
        x = W / 2 - 60 + i * 60
        d.ellipse([x - 10, 340, x + 10, 360], fill=WHITE if i < n else (70, 100, 140))
    return overlay_alpha(frame, lay, a)

def headline(frame, lines, t0, t, y=500, size=104, colors=None, a=1.0):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for i, s in enumerate(lines):
        p = ease_out((t - t0 - i * 0.12) / 0.45)
        if p <= 0: continue
        col = (colors[i] if colors else WHITE) + (int(255 * p),)
        d.text((W / 2, y + i * size * 1.1 + (1 - p) * 50), s, font=font(POP, size), fill=col, anchor="mm")
    return overlay_alpha(frame, lay, a)

# ---------- scenes ----------
def scene_alpha(t, dur, fin=0.35, fout=0.35):
    return clamp(t / fin) * clamp((dur - t) / fout)

def s_hook(t, dur, T):
    f = BG.convert("RGBA"); d = ImageDraw.Draw(f); draw_bubbles(d, T)
    a = scene_alpha(t, dur, 0.01)
    f = headline(f, ["Are octopuses", "aliens?"], 0.1, t, y=380, size=120, colors=[WHITE, CORAL], a=a)
    sc = 0.6 + 0.4 * ease_back((t - 0.3) / 0.6)
    if t > 0.3: paste_shape(f, octopus(T), W / 2, 1000, sc, a)
    return f

def s_hearts(t, dur, T):
    f = BG.convert("RGBA"); d = ImageDraw.Draw(f); draw_bubbles(d, T)
    a = scene_alpha(t, dur)
    f = draw_label(f, t, 1, a)
    f = headline(f, ["3 Hearts"], 0.15, t, y=520, size=130, colors=[CORAL], a=a)
    L = shape_layer(900); ld = ImageDraw.Draw(L)
    beat = 1 + 0.07 * max(0, math.sin(T * 7)) ** 6
    specs = [(-270, 60, 9.0, (255, 140, 120), 0.6), (270, 60, 9.0, (255, 140, 120), 0.75), (0, 0, 15.0, CORAL, 0.35)]
    for dx, dy, s, col, ap in specs:
        p = ease_back((t - ap) / 0.45)
        if p <= 0: continue
        ld.polygon(heart_pts((450 + dx) * S, (450 + dy) * S, s * S * p * beat), fill=col)
    paste_shape(f, L, W / 2, 960, 1, a)
    # labels under small hearts
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(lay)
    p = ease_out((t - 2.3) / 0.4)
    if p > 0:
        for x, s in ((W / 2 - 270, "Gills"), (W / 2 + 270, "Gills"), (W / 2, "Body")):
            dd.text((x, 1265 if s == "Body" else 1215), s, font=font(POPM, 42), fill=SOFT + (int(255 * p),), anchor="mm")
    f = overlay_alpha(f, lay, a)
    return f

def s_blood(t, dur, T):
    f = BG.convert("RGBA"); d = ImageDraw.Draw(f); draw_bubbles(d, T)
    a = scene_alpha(t, dur)
    f = draw_label(f, t, 2, a)
    f = headline(f, ["Blue Blood"], 0.15, t, y=520, size=130, colors=[BLUE], a=a)
    p = ease_back((t - 0.4) / 0.6)
    if p > 0:
        D = drop(620)
        dd = ImageDraw.Draw(D)
        c = 310 * S
        dd.text((c, c + 70 * S), "Cu", font=font(POP, 150 * S), fill=WHITE, anchor="mm")
        paste_shape(f, D, W / 2, 960 + math.sin(T * 2) * 8, p, a)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(lay)
    q = ease_out((t - 2.4) / 0.4)
    if q > 0:
        dd.text((W / 2, 1255), "Copper, not iron", font=font(POPM, 46), fill=SOFT + (int(255 * q),), anchor="mm")
    return overlay_alpha(f, lay, a)

def s_arms(t, dur, T):
    f = BG.convert("RGBA"); d = ImageDraw.Draw(f); draw_bubbles(d, T)
    a = scene_alpha(t, dur)
    f = draw_label(f, t, 3, a)
    f = headline(f, ["Arms that", "think"], 0.15, t, y=470, size=112, colors=[WHITE, YEL], a=a)
    L = shape_layer(620); ld = ImageDraw.Draw(L)
    c = 310 * S; r = 250 * S; w = 64 * S
    ld.ellipse([c - r, c - r, c + r, c + r], outline=(50, 80, 120), width=w)
    prog = ease_out((t - 0.7) / 1.6) * 240
    if prog > 0.5:
        ld.arc([c - r, c - r, c + r, c + r], -90, -90 + prog, fill=YEL, width=w)
    pct = int(round(prog / 360 * 100))
    ld.text((c, c - 30 * S), "2/3" if prog > 239 else f"{pct} %", font=font(POP, 140 * S), fill=WHITE, anchor="mm")
    paste_shape(f, L, W / 2, 1000, 1, a)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(lay)
    q = ease_out((t - 2.4) / 0.4)
    if q > 0:
        dd.text((W / 2, 1000 + 80), "of its neurons", font=font(POPM, 34), fill=SOFT + (int(255 * q),), anchor="mm")
    return overlay_alpha(f, lay, a)

def s_outro(t, dur, T):
    f = BG.convert("RGBA"); d = ImageDraw.Draw(f); draw_bubbles(d, T)
    a = clamp(t / 0.35)
    f = headline(f, ["Which fact", "surprised you?"], 0.1, t, y=380, size=92, colors=[WHITE, YEL], a=a)
    sc = 0.75 + 0.25 * ease_back((t - 0.2) / 0.6)
    paste_shape(f, octopus(T, wave=1.6), W / 2, 960, sc * 0.85, a)
    return f


# ---------------- generic renderer (grain + high bitrate) ----------------
import json
import numpy as _np
_rng = _np.random.default_rng(11)
_GRAIN = [_rng.normal(0, 2.2, (H, W, 1)).astype(_np.float32) for _ in range(6)]

def add_grain(img, i):
    a = _np.asarray(img, dtype=_np.float32) + _GRAIN[i % len(_GRAIN)]
    return Image.fromarray(_np.clip(a, 0, 255).astype(_np.uint8))

def load_timeline(path):
    return json.load(open(path))

def render_frame(fns, tl, idx, t):
    sc = tl[idx]; T = sum(s["dur"] for s in tl[:idx]) + t
    fr = fns[idx](t, sc["dur"], T)
    draw_caption(fr, t, build_caps([(a, b, txt) for a, b, txt, *_ in sc["caps"]]))
    return fr.convert("RGB")

def render_scene(fns, tl, idx, out_path):
    """Render one scene to out_path (mp4, ~11 Mbit/s, grain dithering)."""
    n = int(round(tl[idx]["dur"] * FPS))
    tmp = out_path[:-4] + ".tmp.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-b:v", "11M", "-maxrate", "14M", "-bufsize", "22M", "-tune", "grain",
                          "-pix_fmt", "yuv420p", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(add_grain(render_frame(fns, tl, idx, i / FPS), i).tobytes())
    p.stdin.close()
    if p.wait() == 0: os.replace(tmp, out_path)
    else: sys.exit("ffmpeg failed")
