"""Measure faces in takes: size in pixels and macOS Vision's face capture quality, plus a sheet of
zoomed face crops for side-by-side comparison. Runs entirely on this Mac (Apple Vision framework).

    PY=~/dev/ComfyUI/.venv/bin/python
    $PY scripts/face_check.py episodes/_quality QB Q1M Q1S        # selected or first good take per shot
    $PY scripts/face_check.py --video a.mp4 --video b.mp4

Per take: median face height (px), median / minimum face quality (0-1), share of sampled frames
with a detected face. Quality is a ranking aid, not a verdict: compare takes of the same person.
Writes ~/AI_renders/comfyui/episodes/<ep>/_review/faces_<shots>.png (or _quality/ for --video).
"""
import argparse
import json
import pathlib
import subprocess
import sys
import tempfile

import av
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import episode as E  # noqa: E402

SRC = E.REPO / "scripts/face_boxes.swift"
BIN = E.RENDERS / "_bin/face_boxes"  # compiled helper lives outside Git
EVERY = 6  # sample every 6th frame (4 per second)


def helper():
    if not BIN.exists() or BIN.stat().st_mtime < SRC.stat().st_mtime:
        BIN.parent.mkdir(parents=True, exist_ok=True)
        print("compiling face helper (once, ~30 s)...", flush=True)
        subprocess.run(["swiftc", "-O", str(SRC), "-o", str(BIN)], check=True)
    return BIN


def faces_in_video(path):
    with av.open(str(path)) as c:
        frames = [f.to_image() for i, f in enumerate(c.decode(video=0))]
    idx = list(range(0, len(frames), EVERY))
    with tempfile.TemporaryDirectory() as td:
        files = []
        for i in idx:
            p = pathlib.Path(td) / f"f{i:04d}.png"
            frames[i].save(p); files.append(str(p))
        out = subprocess.run([str(helper())] + files, capture_output=True, text=True, check=True).stdout
    rows = [json.loads(line) for line in out.splitlines() if line.strip()]
    per = []
    for i, r in zip(idx, rows):
        f = max(r.get("faces") or [{}], key=lambda x: x.get("h", 0))  # main (largest) face
        per.append({"frame": i, "h": f.get("h"), "quality": f.get("quality"), "box": f if f else None})
    found = [p for p in per if p["h"]]
    q = [p["quality"] for p in found if p["quality"] is not None]
    summary = {"frames_sampled": len(per), "face_found_pct": round(100 * len(found) / max(1, len(per))),
               "face_h_median": round(float(np.median([p["h"] for p in found])), 1) if found else None,
               "quality_median": round(float(np.median(q)), 3) if q else None,
               "quality_min": round(min(q), 3) if q else None}
    return summary, per, frames


def crops(frames, per, n=4, size=150):
    """n face crops spread over the clip (square, padded around the box, scaled to size)."""
    found = [p for p in per if p["box"]]
    pick = [found[round(k * (len(found) - 1) / max(1, n - 1))] for k in range(n)] if found else []
    out = []
    for p in pick:
        b, im = p["box"], frames[p["frame"]]
        cx, cy, s = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2, max(b["w"], b["h"]) * 1.6
        box = tuple(int(v) for v in (cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2))
        out.append((im.crop(box).resize((size, size), Image.LANCZOS), p))
    return out


def sheet(rows, path, size=150):
    """rows: [(label, summary, crops)] -> one row per take."""
    W, H = 260 + 4 * (size + 6), len(rows) * (size + 10) + 10
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    for r, (label, s, cs) in enumerate(rows):
        y = 10 + r * (size + 10)
        d.text((8, y), label, fill="black")
        d.text((8, y + 20), f"face height {s['face_h_median']} px", fill="black")
        d.text((8, y + 38), f"quality median {s['quality_median']}", fill="black")
        d.text((8, y + 56), f"quality min {s['quality_min']}", fill="black")
        d.text((8, y + 74), f"face found {s['face_found_pct']}%", fill="black")
        for k, (c, p) in enumerate(cs):
            x = 260 + k * (size + 6)
            img.paste(c, (x, y))
            d.rectangle([x, y, x + 64, y + 14], fill="black")
            d.text((x + 3, y + 1), f"f{p['frame']} q{p['quality'] or 0:.2f}", fill="white")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode", nargs="?")
    ap.add_argument("shots", nargs="*")
    ap.add_argument("--video", action="append", default=[])
    a = ap.parse_args()
    targets = [(pathlib.Path(v).stem, pathlib.Path(v)) for v in a.video]
    out_dir = E.RENDERS / "episodes" / "_quality" / "_review"
    if a.episode:
        ep = E.Episode(a.episode)
        out_dir = E.RENDERS / "episodes" / ep.name / "_review"
        for sid in a.shots or list(ep.shots):
            st = E.shot_status(ep, sid)
            take = st.get("selected") or ((st.get("good") or st.get("done") or [None])[0])
            rec = take and ep.take_record(sid, take)
            if rec:
                targets.append((f"{sid} {take}", pathlib.Path(rec["output"]["file"])))
            else:
                print(f"{sid}: no take")
    rows = []
    for label, path in targets:
        s, per, frames = faces_in_video(path)
        print(f"{label:40} face {s['face_h_median']} px  quality median {s['quality_median']} "
              f"min {s['quality_min']}  found {s['face_found_pct']}%", flush=True)
        rows.append((label, s, crops(frames, per)))
    name = "faces_" + "_".join(lbl.split()[0] for lbl, _ in targets)[:80] + ".png"
    print("sheet:", sheet(rows, out_dir / name))


if __name__ == "__main__":
    main()
