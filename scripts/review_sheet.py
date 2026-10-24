"""Contact sheet of all successful takes of one or more shots, for choosing takes.

    ~/dev/ComfyUI/.venv/bin/python scripts/review_sheet.py episodes/midnight_call S003 S005

One row per take (current fingerprint only), frames at 0/25/50/75/100 % plus the frames around
any detected hard cut. Writes ~/AI_renders/comfyui/episodes/<episode>/_review/<shot>_takes.png.
"""
import sys

import av
from PIL import Image, ImageDraw

import episode as E


def sheet(ep, sid):
    st = E.shot_status(ep, sid)
    recs = [r for r in ep.takes(sid) if r.get("status") == "success" and r.get("fingerprint") == st["fp"]]
    if not recs:
        print(f"{sid}: no successful takes of the current version"); return None
    rows = []
    for r in sorted(recs, key=lambda r: r["seed"]):
        fs = [f.to_image() for f in av.open(r["output"]["file"]).decode(video=0)]
        n, fps = len(fs), r["recipe"]["effective"]["fps"]
        cuts = [c["frame"] for c in (r.get("continuity") or {}).get("cuts", [])]
        idx = sorted({round(q * (n - 1)) for q in (0, .25, .5, .75, 1)} | set(cuts) | {c - 1 for c in cuts})
        warn = "; ".join(r.get("warnings") or []) or "no warnings"
        rows.append((f"{sid}  take {r['take_id']}  seed {r['seed']}  {r['wall_seconds']:.0f}s  {warn}",
                     [(i, fs[i], fps) for i in idx]))
    w, h = rows[0][1][0][1].size
    ncol = max(len(fr) for _, fr in rows)
    out = Image.new("RGB", (w * ncol, (h + 30) * len(rows)), "white")
    d = ImageDraw.Draw(out)
    for ri, (title, frames) in enumerate(rows):
        y = ri * (h + 30)
        d.text((6, y + 8), title, fill="black")
        for ci, (i, im, fps) in enumerate(frames):
            im = im.copy(); dd = ImageDraw.Draw(im)
            dd.rectangle([0, 0, 92, 18], fill="black"); dd.text((4, 3), f"f{i} {i / fps:.1f}s", fill="white")
            out.paste(im, (ci * w, y + 30))
    out = out.resize((out.width // 2, out.height // 2))
    path = E.RENDERS / "episodes" / ep.name / "_review" / f"{sid}_takes.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(path)
    print(path)
    return path


if __name__ == "__main__":
    ep = E.Episode(sys.argv[1])
    for sid in sys.argv[2:] or list(ep.shots):
        sheet(ep, sid)
