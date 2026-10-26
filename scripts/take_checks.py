"""Stage 8 picture checks for a take, with macOS's built-in Vision framework (scripts/frame_checks.swift):

  text      - words drawn in the picture (burned-in captions, fake signs). Text the prompt asks for in double
              quotes (packaging, signs) is allowed; dialogue inside <d>...</d> is never allowed as text.
  eyes      - looks into the lens: head facing the camera (yaw/pitch) and both irises centred in the eyes.
              Allowed only when the prompt asks for it ("looks into the lens/camera") without a "never".
  lips      - mouth movement: open/close cycles of the inner lips. Warns when lips move in a shot where the
              character should be silent (narration in the edit, "lips stay closed", no <d> line), and when
              a speaking shot shows almost no movement.

    PY=~/dev/ComfyUI/.venv/bin/python
    $PY scripts/take_checks.py episodes/sunlight [P2 P4]        # selected (or every good) take per shot
    $PY scripts/take_checks.py --video a.mp4 --prompt-file p.txt

Results are warnings for the review page, never automatic rejections: the measurements are heuristics
(thresholds below, calibrated 2026-10-26 on takes the owner reviewed). Per-frame measurements are cached
next to each video as <video>.checks.json (keyed by the video's sha256).
"""
import argparse
import difflib
import json
import pathlib
import re
import subprocess
import sys
import tempfile

import av
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import episode as E  # noqa: E402

SRC = E.REPO / "scripts/frame_checks.swift"
BIN = E.RENDERS / "_bin/frame_checks"  # compiled helper lives outside Git
VERSION = 3  # bump when a per-frame measurement changes, so cached ones are measured again

EVERY = 2               # sample every 2nd frame (12 per second): enough for lip cycles
TEXT_MIN_CONF = 0.5     # Vision text confidence
TEXT_MIN_FRAMES = 3     # the same word in at least 3 sampled frames (noise in foliage reads as single letters)
FACE_MIN_H = 60         # px; smaller faces are too small to judge eyes or lips
CONTACT_YAW = 12.0      # degrees: head roughly facing the camera
CONTACT_PITCH = 15.0
CONTACT_IRIS = 0.12     # iris centre within +-12 % of the eye width from the eye centre
CONTACT_SHARE = 0.15    # warn when >= 15 % of face frames look into the lens (owner-confirmed V1 S2B: 22 %)
LIP_CYCLE = 0.025       # an open/close cycle = mouth opening changes by >= 2.5 % of the face height
LIP_TALK_CYCLES = 3     # >= 3 cycles per 4 s reads as talking
SILENT_WORDS = re.compile(r"lips (?:stay|remain)\w* (?:completely )?closed|does not speak|doesn't speak|"
                          r"says nothing|off-screen voice-?over", re.I)
LENS_OK = re.compile(r"(?:looks?|gazes?|stares?|looking)\s+(?:straight\s+|directly\s+)?(?:in)?to\s+the\s+"
                     r"(?:lens|camera)", re.I)
LENS_NEVER = re.compile(r"(?:never|not|n't|without|avoid\w*)\s+(?:\w+\s+){0,2}(?:look\w*|gaz\w*|stare\w*)\s+"
                        r"(?:straight\s+|directly\s+)?(?:in)?to\s+the\s+(?:lens|camera)", re.I)
DIALOGUE = re.compile(r"<d>(.*?)</d>", re.S)


def helper():
    if not BIN.exists() or BIN.stat().st_mtime < SRC.stat().st_mtime:
        BIN.parent.mkdir(parents=True, exist_ok=True)
        print("compiling frame-check helper (once, ~30 s)...", flush=True)
        subprocess.run(["swiftc", "-O", str(SRC), "-o", str(BIN)], check=True)
    return BIN


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def expectations(prompt):
    """What the prompt allows: quoted on-screen text, lens contact, speech."""
    no_dialogue = DIALOGUE.sub(" ", prompt)
    quoted = [norm(q) for q in re.findall(r"\"([^\"]+)\"", no_dialogue) if norm(q)]
    lens = bool(LENS_OK.search(prompt)) and not LENS_NEVER.search(prompt)
    if SILENT_WORDS.search(prompt) or not DIALOGUE.search(prompt):
        speech = "silent"
    else:
        speech = "speaks"
    return {"allowed_text": quoted, "lens_contact_ok": lens, "speech": speech}


def allowed(word, quoted):
    w = norm(word)
    return any(w in q or (len(q) >= 3 and q in w) or difflib.SequenceMatcher(None, w, q).ratio() >= 0.6
               for q in quoted)


def iris_offset(gray, eye):
    """Horizontal iris position in an eye outline: -0.5 (left corner) .. +0.5 (right corner), 0 = centred.
    Vision's own pupil points sit near the eye centre too often to tell gaze, so the iris is found here."""
    if len(eye) < 3:
        return None
    xs, ys = [p[0] for p in eye], [p[1] for p in eye]
    x0, x1, y0, y1 = int(min(xs)), int(max(xs)) + 1, int(min(ys)), int(max(ys)) + 1
    if x1 - x0 < 6 or y1 - y0 < 2:
        return None
    mask = Image.new("L", (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(mask).polygon([(x - x0, y - y0) for x, y in eye], fill=1)
    m = np.asarray(mask, bool)
    patch = gray[y0:y1, x0:x1]
    if patch.shape != m.shape or m.sum() < 6:
        return None
    # darkness-weighted centroid: pixels darker than the eye's median pull the centre (iris + pupil)
    wgt = np.where(m, np.clip(np.median(patch[m]) - patch, 0, None), 0)
    if wgt.sum() <= 0:
        return None
    cx = (wgt.sum(axis=0) * np.arange(wgt.shape[1])).sum() / wgt.sum()
    return float(cx / (x1 - x0 - 1) - 0.5)


def measure_frames(images):
    """Run the Vision helper on PIL images; returns one dict per image (main face only)."""
    with tempfile.TemporaryDirectory() as td:
        files = []
        for i, im in enumerate(images):
            p = pathlib.Path(td) / f"f{i:04d}.png"
            im.save(p); files.append(str(p))
        out = subprocess.run([str(helper())] + files, capture_output=True, text=True, check=True).stdout
    rows = [json.loads(line) for line in out.splitlines() if line.strip().startswith("{")]
    res = []
    for im, r in zip(images, rows):
        gray = np.asarray(im.convert("L"), np.float32)
        f = max(r.get("faces") or [{}], key=lambda x: x.get("h", 0))
        d = {"texts": [t for t in r.get("texts", []) if t.get("confidence", 0) >= TEXT_MIN_CONF]}
        if f.get("h", 0) >= FACE_MIN_H:
            inner = f.get("inner_lips") or []
            d.update(face_h=f["h"], yaw=f.get("yaw"), pitch=f.get("pitch"),
                     iris=[iris_offset(gray, f.get("left_eye") or []), iris_offset(gray, f.get("right_eye") or [])],
                     mouth=(max(p[1] for p in inner) - min(p[1] for p in inner)) / f["h"] if inner else None)
        res.append(d)
    return res


def cycles(series, step):
    """Open/close cycles: moves of at least `step` in alternating directions (hysteresis, so jitter does
    not count); one cycle = one opening plus one closing."""
    moves, direction, ext = 0, 0, series[0]
    for v in series[1:]:
        if direction <= 0 and v >= ext + step:
            moves, direction, ext = moves + 1, 1, v
        elif direction >= 0 and v <= ext - step:
            moves, direction, ext = moves + 1, -1, v
        elif (direction == 1 and v > ext) or (direction == -1 and v < ext):
            ext = v  # follow the current move to its extreme
    return moves // 2


def analyse(per, frame_idx, expect, fps=24):
    out, warn = {"frames_sampled": len(per)}, []
    # text: same normalised word in >= TEXT_MIN_FRAMES sampled frames and not asked for in the prompt
    seen = {}
    for i, d in zip(frame_idx, per):
        for t in d["texts"]:
            w = norm(t["text"])
            if len(w) >= 2:
                seen.setdefault(w, {"text": t["text"], "frames": []})["frames"].append(i)
    texts = [dict(v, allowed=allowed(v["text"], expect["allowed_text"])) for v in seen.values()
             if len(v["frames"]) >= TEXT_MIN_FRAMES]
    out["text"] = texts
    bad = [t for t in texts if not t["allowed"]]
    if bad:
        warn.append("text in the picture that the prompt did not ask for: "
                    + ", ".join(f"'{t['text']}' (from frame {t['frames'][0]})" for t in bad[:4]))
    # eyes: lens contact
    faces = [(i, d) for i, d in zip(frame_idx, per) if "face_h" in d]
    contact = [i for i, d in faces
               if d.get("yaw") is not None and abs(d["yaw"]) <= CONTACT_YAW and abs(d.get("pitch") or 0) <= CONTACT_PITCH
               and all(x is not None and abs(x) <= CONTACT_IRIS for x in d["iris"])]
    out["eyes"] = {"face_frames": len(faces), "lens_contact_frames": contact,
                   "lens_contact_share": round(len(contact) / len(faces), 2) if faces else None}
    if faces and len(contact) >= 3 and len(contact) / len(faces) >= CONTACT_SHARE and not expect["lens_contact_ok"]:
        warn.append(f"looks into the lens in {len(contact)}/{len(faces)} sampled face frames "
                    f"(from frame {contact[0]}); check by eye")
    # lips
    mouth = [d["mouth"] for _, d in faces if d.get("mouth") is not None]
    if len(mouth) >= 6:
        seconds = len(frame_idx) * EVERY / fps
        c = cycles(mouth, LIP_CYCLE)
        per4 = c * 4 / max(seconds, 0.5)
        out["lips"] = {"cycles": c, "cycles_per_4s": round(per4, 1), "range": round(max(mouth) - min(mouth), 3),
                       "expected": expect["speech"]}
        if expect["speech"] == "silent" and per4 >= LIP_TALK_CYCLES:
            warn.append(f"lips move like speech ({c} open/close cycles) in a shot where nobody on screen speaks; "
                        f"check by eye (a smile also moves the lips)")
        if expect["speech"] == "speaks" and c == 0:
            warn.append("a line is spoken on screen but the lips barely move (lip sync)")
    return out, warn


def check_video(video, prompt, compute=True):
    """(result, warnings) for a take. The per-frame Vision measurements are cached next to the video
    (keyed by its sha256); the verdict is recomputed from them each time, so threshold or prompt changes
    apply without measuring again. compute=False returns None when nothing is cached (review page)."""
    video = pathlib.Path(video)
    cache = video.with_suffix(".checks.json")
    c = json.loads(cache.read_text()) if cache.exists() else {}
    if c.get("version") != VERSION or (compute and c.get("sha256") != E.sha256(video)):
        if not compute:
            return None
        with av.open(str(video)) as f:
            frames = [x.to_image() for x in f.decode(video=0)]
        idx = list(range(0, len(frames), EVERY))
        c = {"sha256": E.sha256(video), "version": VERSION, "frames": idx,
             "measurements": measure_frames([frames[i] for i in idx])}
        cache.write_text(json.dumps(c))
    expect = expectations(prompt)
    result, warn = analyse(c["measurements"], c["frames"], expect)
    result["expect"] = expect
    return result, warn


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode", nargs="?")
    ap.add_argument("shots", nargs="*")
    ap.add_argument("--video", action="append", default=[])
    ap.add_argument("--prompt-file", help="prompt for --video (default: none = silent, no text allowed)")
    ap.add_argument("--all", action="store_true", help="every good take, not only the selected one")
    a = ap.parse_args()
    targets = []
    prompt = pathlib.Path(a.prompt_file).read_text() if a.prompt_file else ""
    targets += [(pathlib.Path(v).stem, v, prompt) for v in a.video]
    if a.episode:
        ep = E.Episode(a.episode)
        for sid in a.shots or E.order(ep):
            st = E.shot_status(ep, sid)
            tids = (st.get("good") or []) if a.all else [st.get("selected") or next(iter(st.get("good") or []), None)]
            for tid in [t for t in tids if t]:
                rec = ep.take_record(sid, tid)
                if rec and rec.get("output"):
                    targets.append((f"{sid} {tid}", rec["output"]["file"], ep.params(sid)["prompt"]))
    for label, video, pr in targets:
        res, warn = check_video(video, pr)
        eyes, lips = res["eyes"], res.get("lips") or {}
        print(f"{label:28s} text {len(res['text'])} (not asked {sum(not t['allowed'] for t in res['text'])})  "
              f"lens {eyes['lens_contact_share']}  lips {lips.get('cycles_per_4s')}/4s ({lips.get('expected')})")
        for w in warn:
            print("   warning:", w)


if __name__ == "__main__":
    main()
