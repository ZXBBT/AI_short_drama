"""Stage 8.4: automatic take picking and the owner's confirmation.

Auto-pick (episodes with `review: {picks: auto}`): for every shot that has takes but no pick, choose
the good take whose main face scores best (macOS Vision face quality, then face size; the score
matched every blur verdict the owner gave on Midnight Call). Shots without a face (establishing
shots) get their first good take. Picks are written with a note "auto-pick: ...", so the review
page can mark them; any pick made by the owner replaces them.

Confirmation (`review: {final: true}`, the default): the owner presses "Confirm picks" on the review
page; the pipeline assembles only while the confirmed picks equal the current picks.
"""
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import episode as E  # noqa: E402

CONFIRM_KEY = "_confirmed"


def face_score(rec):
    """Face summary of a take's video, cached next to the video (keyed by the video's sha256)."""
    video = pathlib.Path(rec["output"]["file"])
    cache = video.with_suffix(".faces.json")
    sha = rec["output"].get("sha256") or E.sha256(video)
    if cache.exists():
        c = json.loads(cache.read_text())
        if c.get("sha256") == sha:
            return c["summary"]
    import face_check  # noqa: E402 (compiles the Swift helper on first use)
    summary, _, _ = face_check.faces_in_video(video)
    cache.write_text(json.dumps({"sha256": sha, "summary": summary}, indent=1))
    return summary


def rank_key(summary):
    """Higher is better; takes without a clearly visible face rank last."""
    if not summary or (summary.get("face_found_pct") or 0) < 50 or summary.get("quality_median") is None:
        return (0, 0.0, 0.0)
    return (1, summary["quality_median"], summary.get("face_h_median") or 0.0)


def auto_pick(ep):
    """Pick a take for every finished shot without a pick. Returns the number of picks written."""
    n = 0
    for sid in E.order(ep):
        if ep.selected_take(sid):
            continue
        st = E.shot_status(ep, sid)
        if st["state"] not in ("done", "needs_review") or not st["done"]:
            continue
        candidates = st["good"] or st["done"]
        scored = []
        for tid in candidates:
            rec = ep.take_record(sid, tid)
            scored.append((rank_key(face_score(rec)), tid, face_score(rec)))
        scored.sort(key=lambda x: x[0], reverse=True)
        key, tid, s = scored[0]
        why = (f"face quality {s['quality_median']}, {s['face_h_median']} px" if key[0]
               else "no clear face in any take; first good take")
        extra = "" if st["good"] else " (all takes failed checks)"
        E.write_selection(ep, sid, tid, note=f"auto-pick: {why}{extra}; confirm on the review page")
        n += 1
    return n


def is_auto(ep, sid):
    v = ep.selections.get(sid)
    return isinstance(v, dict) and str(v.get("note", "")).startswith("auto-pick")


def current_picks(ep, shots=None):
    return {s: ep.selected_take(s) for s in (shots or ep.shots) if ep.selected_take(s)}


def confirm(ep):
    """Record the owner's confirmation of the current picks (review page button)."""
    ep.selections[CONFIRM_KEY] = {"at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                                  "picks": current_picks(ep)}
    E.write_selections_file(ep)


def confirmed(ep, shots):
    """True if the owner confirmed exactly the current picks of these shots."""
    c = ep.selections.get(CONFIRM_KEY) or {}
    return bool(c) and all(c.get("picks", {}).get(s) == ep.selected_take(s) for s in shots)
