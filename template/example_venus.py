"""Example video: 3 Venus facts. Copy this file per topic and replace the scene functions.
Usage: python3 example_venus.py <timeline.json> <scene_index> <out.mp4>
       python3 example_venus.py <timeline.json> preview <t0,t1,t2,t3,t4> <out_prefix>
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as M
from PIL import Image, ImageDraw, ImageFilter
W, H, FPS, S = M.W, M.H, M.FPS, M.S

ORANGE = (240, 165, 80); VLIGHT = (250, 205, 140); VDARK = (205, 120, 55)
HOT = (255, 86, 60)

_planet_cache = {}
def venus(size, T):
    key = (size, int(T * 15))
    if key in _planet_cache: return _planet_cache[key]
    n = size * S
    L = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    base = Image.new("RGBA", (n, n), ORANGE + (255,))
    d = ImageDraw.Draw(base)
    ph = T * 0.35
    for i in range(9):
        y0 = n * (0.08 + i * 0.105)
        col = VLIGHT if i % 2 else VDARK
        pts = []
        for k in range(41):
            x = n * k / 40
            pts.append((x, y0 + math.sin(k / 40 * 6.28 * 1.5 + ph + i) * n * 0.018))
        for k in range(40, -1, -1):
            x = n * k / 40
            pts.append((x, y0 + n * 0.045 + math.sin(k / 40 * 6.28 * 1.5 + ph + i * 1.7) * n * 0.015))
        d.polygon(pts, fill=col + (170,))
    base = base.filter(ImageFilter.GaussianBlur(n * 0.006))
    # shading: darker toward lower right edge
    shade = Image.new("L", (n, n), 0)
    sd = ImageDraw.Draw(shade)
    sd.ellipse([n * 0.22, n * 0.18, n * 1.25, n * 1.2], fill=140)
    shade = shade.filter(ImageFilter.GaussianBlur(n * 0.12))
    dark = Image.new("RGBA", (n, n), (60, 25, 20, 255))
    base = Image.composite(dark, base, shade.point(lambda v: int(v * 0.75)))
    hl = Image.new("L", (n, n), 0)
    ImageDraw.Draw(hl).ellipse([n * 0.12, n * 0.1, n * 0.5, n * 0.45], fill=90)
    hl = hl.filter(ImageFilter.GaussianBlur(n * 0.08))
    base = Image.composite(Image.new("RGBA", (n, n), (255, 240, 210, 255)), base, hl)
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, n - 1, n - 1], fill=255)
    L.paste(base, (0, 0), mask)
    _planet_cache.clear(); _planet_cache[key] = L
    return L

def glow(frame, cx, cy, r, col, a):
    g = Image.new("L", (W, H), 0)
    ImageDraw.Draw(g).ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(110 * a))
    g = g.filter(ImageFilter.GaussianBlur(r * 0.35))
    frame.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H), col).split(), g)))

def base_frame(T):
    f = M.BG.convert("RGBA"); M.draw_bubbles(ImageDraw.Draw(f), T); return f

def s_hook(t, dur, T):
    f = base_frame(T); a = M.clamp(t / 0.01) * M.clamp((dur - t) / 0.35)
    f = M.headline(f, ["The weirdest", "planet?"], 0.1, t, y=380, size=120, colors=[M.WHITE, ORANGE], a=a)
    p = M.ease_back((t - 0.3) / 0.7)
    if p > 0:
        glow(f, W / 2, 1000, 380, ORANGE, a * M.clamp(p))
        M.paste_shape(f, venus(560, T), W / 2, 1000, 0.6 + 0.4 * p, a)
    return f

def s_day(t, dur, T):
    f = base_frame(T); a = M.scene_alpha(t, dur)
    f = M.draw_label(f, t, 1, a)
    f = M.headline(f, ["Day > Year"], 0.15, t, y=520, size=130, colors=[M.YEL], a=a)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    x0, maxw = 160, 760
    rows = [("1 day", 243, M.YEL, 2.9, 830), ("1 year", 225, (120, 175, 235), 6.2, 1080)]
    for lab, val, col, st, y in rows:
        p = M.ease_out((t - st) / 1.2)
        if t < st: continue
        d.text((x0, y), lab, font=M.font(M.POPM, 48), fill=M.SOFT, anchor="ls")
        w = maxw * val / 243 * p
        d.rounded_rectangle([x0, y + 25, x0 + max(w, 40), y + 115], radius=45, fill=col)
        d.text((x0 + max(w, 40) - 30, y + 70), f"{int(round(val * p))}", font=M.font(M.POP, 52), fill=M.BG1 if p > 0.25 else col, anchor="rm")
        q = M.clamp((t - st - 0.9) / 0.4)
        if q > 0:
            d.text((x0 + maxw, y), "Earth days", font=M.font(M.POPM, 38), fill=M.SOFT + (int(255 * q),), anchor="rs")
    return M.overlay_alpha(f, lay, a)

def arrow_arc(d, cx, cy, r, a0, a1, col, w):
    # draw arc from a0 to a1 (degrees, PIL convention) with arrowhead at a0 (counter-clockwise direction)
    d.arc([cx - r, cy - r, cx + r, cy + r], a0, a1, fill=col, width=w)
    ang = math.radians(a0)
    hx, hy = cx + r * math.cos(ang), cy + r * math.sin(ang)
    tx, ty = math.sin(ang), -math.cos(ang)  # tangent pointing toward decreasing angle
    nx, ny = math.cos(ang), math.sin(ang)
    L = w * 2.2
    pts = [(hx + tx * L, hy + ty * L), (hx + nx * L * 0.8, hy + ny * L * 0.8), (hx - nx * L * 0.8, hy - ny * L * 0.8)]
    d.polygon(pts, fill=col)

def s_back(t, dur, T):
    f = base_frame(T); a = M.scene_alpha(t, dur)
    f = M.draw_label(f, t, 2, a)
    f = M.headline(f, ["Spins", "backwards"], 0.15, t, y=470, size=112, colors=[M.WHITE, M.CORAL], a=a)
    p = M.ease_back((t - 0.4) / 0.6)
    if p > 0:
        M.paste_shape(f, venus(400, T * -1.5), W / 2, 1010, 0.6 + 0.4 * p, a)
    q = M.ease_out((t - 0.8) / 0.6)
    if q > 0:
        L = Image.new("RGBA", (700 * S, 700 * S), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        c = 350 * S; rot = -T * 60
        arrow_arc(d, c, c, 300 * S, 200 + rot, 200 + rot + 120 * q, M.CORAL, 16 * S)
        arrow_arc(d, c, c, 300 * S, 20 + rot, 20 + rot + 120 * q, M.CORAL, 16 * S)
        M.paste_shape(f, L, W / 2, 1010, 1, a)
    return f

def s_hot(t, dur, T):
    f = base_frame(T); a = M.scene_alpha(t, dur)
    f = M.draw_label(f, t, 3, a)
    p = M.ease_out((t - 1.9) / 2.2)
    temp = int(round(465 * p))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    hp = M.ease_out((t - 0.15) / 0.45)
    if p <= 0:
        d.text((W / 2, 470 + (1 - hp) * 50), "Hottest", font=M.font(M.POP, 112), fill=M.WHITE + (int(255 * hp),), anchor="mm")
        d.text((W / 2, 593 + (1 - hp) * 50), "planet", font=M.font(M.POP, 112), fill=HOT + (int(255 * hp),), anchor="mm")
    else:
        d.text((W / 2, 520), f"{temp} °C", font=M.font(M.POP, 140), fill=HOT, anchor="mm")
    f = M.overlay_alpha(f, lay, a)
    L = Image.new("RGBA", (500 * S, 700 * S), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    cx = 250 * S
    d.rounded_rectangle([cx - 60 * S, 40 * S, cx + 60 * S, 520 * S], radius=60 * S, fill=(40, 70, 110))
    d.ellipse([cx - 120 * S, 440 * S, cx + 120 * S, 680 * S], fill=(40, 70, 110))
    d.ellipse([cx - 92 * S, 468 * S, cx + 92 * S, 652 * S], fill=HOT)
    top = 520 - 440 * p
    d.rounded_rectangle([cx - 34 * S, top * S, cx + 34 * S, 540 * S], radius=34 * S, fill=HOT)
    for i in range(5):
        y = (110 + i * 85) * S
        d.line([cx + 70 * S, y, cx + 110 * S, y], fill=(120, 160, 210), width=8 * S)
    sq = Image.new("RGBA", (700 * S, 700 * S), (0, 0, 0, 0)); sq.paste(L, (100 * S, 0))
    if p > 0.6: glow(f, W / 2, 1060, 260, HOT, a * (p - 0.6) / 0.4)
    M.paste_shape(f, sq, W / 2, 1000, 0.82, a)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    q = M.ease_out((t - 5.0) / 0.4)
    if q > 0:
        d.text((W / 2, 1320), "Hotter than Mercury", font=M.font(M.POPM, 46), fill=M.SOFT + (int(255 * q),), anchor="mm")
    return M.overlay_alpha(f, lay, a)

def s_outro(t, dur, T):
    f = base_frame(T); a = M.clamp(t / 0.35)
    f = M.headline(f, ["Which fact", "surprised you?"], 0.1, t, y=380, size=92, colors=[M.WHITE, M.YEL], a=a)
    p = M.ease_back((t - 0.2) / 0.6)
    glow(f, W / 2, 980, 330, ORANGE, a)
    M.paste_shape(f, venus(500, T), W / 2, 980, 0.75 + 0.25 * p, a)
    return f

FNS = [s_hook, s_day, s_back, s_hot, s_outro]


if __name__ == "__main__":
    tl = M.load_timeline(sys.argv[1])
    if sys.argv[2] == "preview":
        for i, t in enumerate(float(x) for x in sys.argv[3].split(",")):
            M.render_frame(FNS, tl, i, t).save(f"{sys.argv[4]}{i}.png")
    else:
        M.render_scene(FNS, tl, int(sys.argv[2]), sys.argv[3])
