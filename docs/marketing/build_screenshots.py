"""Compose App Store screenshots: real app captures + cosmic backdrop + Didot serif headline.
Usage: python build_screenshots.py <captures_dir> <out_dir>   (requires Pillow + macOS system fonts)"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H = 1290, 2796
DIDOT = "/System/Library/Fonts/Supplemental/Didot.ttc"
HELV = "/System/Library/Fonts/Helvetica.ttc"

FRAMES = [
    ("now_focus.png",  "Know the\nbest next step", "AI recommendations from your schedule,\ntasks, health, and location."),
    ("now_health.png", "Work with\nyour energy",   "Reads your sleep and activity to choose\nfocus, movement, or rest."),
    ("capture.png",    "Just say it.",             "Speak or type — TimeSense turns it\ninto a scheduled plan."),
    ("why.png",        "Understand\nevery call",   "See exactly why — calendar, energy,\ntime, and place."),
    ("insights.png",   "Plan, reflect,\nimprove",  "Turns your routines and patterns into\nbetter decisions over time."),
]

def lerp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def background():
    img = Image.new("RGB", (W, H)); px = img.load()
    for y in range(H):
        c = lerp((11, 14, 32), (6, 7, 16), y / H)
        for x in range(W): px[x, y] = c
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    for cx, cy, r, color in [(W + 120, 180, 900, (120, 70, 240)), (-120, H - 260, 900, (40, 90, 230)), (W // 2, H // 2, 700, (30, 40, 120))]:
        g = Image.new("L", (W, H), 0); d = ImageDraw.Draw(g)
        for i in range(30):
            rr = int(r * (1 - i / 30)); d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=int(90 * i / 30))
        glow = Image.composite(Image.new("RGB", (W, H), color), glow, g)
    return ImageChops.screen(img, glow)

def rounded(im, rad):
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, *im.size], radius=rad, fill=255)
    o = Image.new("RGBA", im.size, (0, 0, 0, 0)); o.paste(im, (0, 0), m); return o

def center(draw, cx, y, text, fnt, fill, gap=1.12):
    for ln in text.split("\n"):
        bb = draw.textbbox((0, 0), ln, font=fnt); w = bb[2] - bb[0]; h = bb[3] - bb[1]
        draw.text((cx - w / 2, y - bb[1]), ln, font=fnt, fill=fill)
        y += int(h * gap) + int(fnt.size * 0.18)
    return y

def run(shots, out):
    hf, sf, wf = ImageFont.truetype(DIDOT, 116), ImageFont.truetype(HELV, 42), ImageFont.truetype(DIDOT, 46)
    for i, (src, head, sub) in enumerate(FRAMES, 1):
        c = background().convert("RGBA"); d = ImageDraw.Draw(c); cx = W // 2
        tot = d.textbbox((0, 0), "TimeSense", font=wf)[2]; sx = cx - tot / 2
        d.text((sx, 70), "Time", font=wf, fill=(255, 255, 255))
        d.text((sx + d.textbbox((0, 0), "Time", font=wf)[2], 70), "Sense", font=wf, fill=(150, 110, 255))
        ye = center(d, cx, 190, head, hf, (255, 255, 255)); center(d, cx, ye + 30, sub, sf, (176, 184, 208))
        shot = Image.open(f"{shots}/{src}").convert("RGB")
        sc = 1980 / shot.height; shot = rounded(shot.resize((int(shot.width * sc), 1980), Image.LANCZOS), 60)
        px = (W - shot.width) // 2; py = 760
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.paste(rounded(Image.new("RGB", shot.size, (90, 110, 255)), 60), (px, py + 18))
        c = Image.alpha_composite(c, sh.filter(ImageFilter.GaussianBlur(38))); c.alpha_composite(shot, (px, py))
        c.convert("RGB").save(f"{out}/{i:02d}_{src.replace('.png', '')}.png")

if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
