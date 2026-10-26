"""Put a clean phone interface onto a green screen in a rendered take (V2 revision brief, section 10).

H3 cannot draw interface text or avatars reliably (V1 S5B), so the shot is rendered with the phone screen
as flat chroma-key green and the interface is drawn here and tracked onto it frame by frame:

    PY=~/dev/ComfyUI/.venv/bin/python
    $PY scripts/screen_insert.py ui  <out_dir>                         # draw the SUPER DRY CLUB screens
    $PY scripts/screen_insert.py comp <take.mp4> <out.mp4> <ui.png>@0 [<ui2.png>@2.1 ...]

`comp` finds the green area in every frame, fits the screen's four corners (smoothed over neighbouring
frames), warps the interface onto it with a perspective transform, keeps fingers in front (they are not
green), removes green spill on their edges, softens the graphic slightly to match the footage, and copies
the take's sound. Only numpy + Pillow + PyAV (no new software).
"""
import argparse
import json
import pathlib
import sys

import av
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import episode as E  # noqa: E402

UI_W, UI_H = 720, 1560  # portrait phone screen (~9:19.5)
BLUE, WHITE, INK, GREY = (22, 92, 214), (255, 255, 255), (28, 34, 46), (120, 128, 140)
FONT = "/System/Library/Fonts/HelveticaNeue.ttc"


# ---------- interface graphics ----------

def font(size, bold=False):
    return ImageFont.truetype(FONT, size, index=1 if bold else 0)


def avatar(d, xy, r, colour, initials):
    x, y = xy
    d.ellipse([x - r, y - r, x + r, y + r], fill=colour, outline=WHITE, width=4)
    f = font(int(r * 0.8), True)
    w = d.textlength(initials, font=f)
    d.text((x - w / 2, y - r * 0.5), initials, font=f, fill=WHITE)


def draw_ui(state, can_png=None):
    """state 'invite' (Join button) or 'joined' (after the tap). Short, correctly spelled English only."""
    im = Image.new("RGB", (UI_W, UI_H), (244, 247, 252))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, UI_W, 230], fill=BLUE)
    t = "SUPER DRY CLUB"
    d.text(((UI_W - d.textlength(t, font=font(64, True))) / 2, 120), t, font=font(64, True), fill=WHITE)
    # invitation card
    d.rounded_rectangle([40, 280, UI_W - 40, 1340], radius=36, fill=WHITE)
    if can_png:
        can = Image.open(can_png).convert("RGB")
        cw, ch = can.size
        h = round(cw * 520 / 600)  # card photo is 600x520: crop to that shape (no stretching), top of the
        y0 = int(ch * 0.22)        # can and the label only (the model's small capacity print is not shown)
        can = can.crop((0, y0, cw, y0 + h)).resize((600, 520), Image.Resampling.LANCZOS)
        im.paste(can, (60, 300))
    d.text((80, 850), "Riverside Meetup", font=font(58, True), fill=INK)
    d.text((80, 930), "Tonight 8:30 PM - East Bank Steps", font=font(36), fill=GREY)
    for i, (col, ini) in enumerate([((231, 111, 81), "AL"), ((42, 157, 143), "MJ"),
                                    ((233, 196, 106), "SK"), ((120, 104, 230), "WY")]):
        avatar(d, (120 + i * 70, 1040), 42, col, ini)
    d.text((420, 1018), "12 going", font=font(40, True), fill=INK)
    if state == "invite":
        d.rounded_rectangle([80, 1150, UI_W - 80, 1290], radius=70, fill=BLUE)
        t, f = "Join", font(64, True)
        d.text(((UI_W - d.textlength(t, font=f)) / 2, 1182), t, font=f, fill=WHITE)
    else:
        d.rounded_rectangle([80, 1150, UI_W - 80, 1290], radius=70, fill=WHITE, outline=BLUE, width=6)
        t, f = "Joined", font(64, True)
        d.text(((UI_W - d.textlength(t, font=f)) / 2, 1182), t, font=f, fill=BLUE)
        d.rounded_rectangle([40, 1380, UI_W - 40, 1500], radius=30, fill=(225, 236, 253))
        t, f = "See you there!", font(48, True)
        d.text(((UI_W - d.textlength(t, font=f)) / 2, 1412), t, font=f, fill=BLUE)
    return im


# ---------- tracking and compositing ----------

def green_mask(rgb):
    """Chroma-key green (H3 renders it slightly lit, not pure #00FF00)."""
    r, g, b = (rgb[..., i].astype(np.float32) for i in range(3))
    return (g > 90) & (g > r * 1.35) & (g > b * 1.35)


def corners(mask):
    """Four screen corners (tl, tr, br, bl) of the largest green area via extreme points; None if too small."""
    ys, xs = np.nonzero(mask)
    if xs.size < 400:
        return None
    s, d = xs + ys, xs - ys
    pts = [(xs[s.argmin()], ys[s.argmin()]), (xs[d.argmax()], ys[d.argmax()]),
           (xs[s.argmax()], ys[s.argmax()]), (xs[d.argmin()], ys[d.argmin()])]
    return np.array(pts, dtype=np.float64)


def homography(src, dst):
    """3x3 H with dst ~ H @ src for 4 point pairs (direct linear transform)."""
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.array(A))
    H = vt[-1].reshape(3, 3)
    return H / H[2, 2]


def warp(ui, quad, size):
    """Warp the interface image onto quad (tl, tr, br, bl) in an image of `size`."""
    w, h = ui.size
    rect = np.array([(0, 0), (w, 0), (w, h), (0, h)], dtype=np.float64)
    Hinv = homography(quad, rect)  # PIL maps output pixels back to input pixels
    coeffs = (Hinv / Hinv[2, 2]).flatten()[:8]
    return ui.transform(size, Image.Transform.PERSPECTIVE, tuple(coeffs), Image.Resampling.BICUBIC)


def smooth_tracks(tracks, radius=2):
    """Median of each corner over +-radius frames (removes jitter from fingers touching the edge)."""
    ok = [i for i, q in enumerate(tracks) if q is not None]
    out = []
    for i in range(len(tracks)):
        near = [tracks[j] for j in ok if abs(j - i) <= radius]
        out.append(np.median(np.stack(near), axis=0) if near else None)
    return out


def composite(take, out, uis, blur=0.7, brightness=0.92):
    """uis: [(png, start_s)] sorted by start; the last one that started is shown."""
    with av.open(str(take)) as c:
        frames = [f.to_ndarray(format="rgb24") for f in c.decode(video=0)]
    masks = [green_mask(f) for f in frames]
    tracks = smooth_tracks([corners(m) for m in masks])
    images = [(Image.open(p).convert("RGB").filter(ImageFilter.GaussianBlur(blur)), float(t)) for p, t in uis]
    result, found = [], 0
    for i, (f, m, q) in enumerate(zip(frames, masks, tracks)):
        if q is None:
            result.append(f); continue
        found += 1
        ui = [im for im, t in images if t <= i / 24][-1] if any(t <= i / 24 for _, t in images) else images[0][0]
        warped = np.asarray(warp(ui, q, (f.shape[1], f.shape[0])), dtype=np.float32) * brightness
        # alpha: the green pixels (fingers stay in front), slightly feathered
        a = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
        a = np.asarray(a, dtype=np.float32)[..., None] / 255
        g = f.astype(np.float32)
        spill = g[..., 1] > np.maximum(g[..., 0], g[..., 2])  # green fringe on fingers and bezel
        g[..., 1] = np.where(spill, np.maximum(g[..., 0], g[..., 2]), g[..., 1])
        result.append(np.clip(g * (1 - a) + warped * a, 0, 255).astype(np.uint8))
    src = av.open(str(take))
    dst = av.open(str(out), "w")
    vs = dst.add_stream("libx264", rate=24, options={"crf": "14", "preset": "medium"})
    vs.width, vs.height, vs.pix_fmt = frames[0].shape[1], frames[0].shape[0], "yuv420p"
    aus = dst.add_stream("aac", rate=48000, layout="stereo") if src.streams.audio else None  # all streams first
    for i, f in enumerate(result):
        vf = av.VideoFrame.from_ndarray(f, format="rgb24")
        vf.pts = i
        for p in vs.encode(vf):
            dst.mux(p)
    for p in vs.encode():
        dst.mux(p)
    if aus:
        rs, n = av.AudioResampler(format="fltp", layout="stereo", rate=48000), 0
        for fr in list(src.decode(audio=0)) + [None]:
            for x in rs.resample(fr):
                x.pts, n = n, n + x.samples
                for p in aus.encode(x):
                    dst.mux(p)
        for p in aus.encode():
            dst.mux(p)
    src.close(); dst.close()
    info = {"take": str(take), "take_sha256": E.sha256(take), "out": str(out), "frames": len(frames),
            "frames_with_screen": found, "uis": [{"file": str(p), "sha256": E.sha256(p), "from_s": float(t)} for p, t in uis]}
    pathlib.Path(out).with_suffix(".json").write_text(json.dumps(info, indent=1))
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("ui"); u.add_argument("out_dir"); u.add_argument("--can", help="product picture for the card")
    c = sub.add_parser("comp"); c.add_argument("take"); c.add_argument("out"); c.add_argument("ui", nargs="+")
    a = ap.parse_args()
    if a.cmd == "ui":
        d = pathlib.Path(a.out_dir); d.mkdir(parents=True, exist_ok=True)
        for st in ("invite", "joined"):
            draw_ui(st, a.can).save(d / f"ui_{st}.png"); print("wrote", d / f"ui_{st}.png")
    else:
        uis = [(x.rsplit("@", 1)[0], float(x.rsplit("@", 1)[1]) if "@" in x else 0.0) for x in a.ui]
        info = composite(a.take, a.out, sorted(uis, key=lambda u: u[1]))
        print(json.dumps({k: info[k] for k in ("out", "frames", "frames_with_screen")}))


if __name__ == "__main__":
    main()
