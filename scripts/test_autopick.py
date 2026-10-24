"""Offline tests for scripts/autopick.py with fake take records and fake face scores.

    ~/dev/ComfyUI/.venv/bin/python scripts/test_autopick.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import autopick as AP  # noqa: E402
import episode as E  # noqa: E402

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures.append(name)


with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td)
    ep_dir = td / "t"; ep_dir.mkdir()
    (ep_dir / "episode.yaml").write_text(
        "episode: t\nrecipe: h3_base_v2\nreview: {picks: auto, final: true}\nshots:\n"
        "  A: {type: t2v, prompt: a, seeds: [1, 2, 3], max_rerolls: 0}\n"
        "  B: {type: t2v, prompt: b, seed: 7}\n"
        "  C: {type: t2v, prompt: c, seeds: [4, 5]}\n")
    runs = td / "runs" / "2026-10-24"; runs.mkdir(parents=True)
    ep = E.Episode(ep_dir, runs_dir=runs.parent)
    fps = {s: E.shot_status(ep, s)["fp"] for s in ("A", "B", "C")}
    faces = {}

    def fake(sid, seed, quality, h=100.0, found=100, cuts=()):
        tid = f"{fps[sid][:8]}_s{seed}"
        (runs / f"t__{sid}__{tid}.json").write_text(json.dumps({
            "shot": sid, "take_id": tid, "fingerprint": fps[sid], "seed": seed, "status": "success",
            "output": {"file": f"/nonexistent/{tid}.mp4", "sha256": tid},
            "continuity": {"cuts": [{"frame": c} for c in cuts]}}))
        faces[tid] = {"face_found_pct": found, "quality_median": quality, "face_h_median": h}
        return tid

    AP.face_score = lambda rec: faces[rec["take_id"]]  # no video decoding in this test
    a1, a2, a3 = fake("A", 1, 0.40), fake("A", 2, 0.62), fake("A", 3, 0.90, cuts=[30])  # best face but a cut
    b1 = fake("B", 7, None, h=None, found=0)                                          # establishing shot
    c1, c2 = fake("C", 4, 0.70, found=30), fake("C", 5, 0.20)                          # face found rarely
    ep = E.Episode(ep_dir, runs_dir=runs.parent)
    check("auto_pick picks every finished shot", AP.auto_pick(ep) == 3)
    ep = E.Episode(ep_dir, runs_dir=runs.parent)
    check("best face among good takes wins (a take with an unwanted cut is skipped)", ep.selected_take("A") == a2,
          ep.selected_take("A"))
    check("shot without faces gets its first good take", ep.selected_take("B") == b1)
    check("a face seen in <50 % of frames ranks below a clear face", ep.selected_take("C") == c2, ep.selected_take("C"))
    check("auto picks are marked", AP.is_auto(ep, "A") and "face quality 0.62" in ep.selections["A"]["note"])
    check("not confirmed before the owner confirms", not AP.confirmed(ep, ["A", "B", "C"]))
    AP.confirm(ep); ep = E.Episode(ep_dir, runs_dir=runs.parent)
    check("confirmed after confirm", AP.confirmed(ep, ["A", "B", "C"]))
    E.write_selection(ep, "A", a1); ep = E.Episode(ep_dir, runs_dir=runs.parent)
    check("owner changing a pick invalidates the confirmation", not AP.confirmed(ep, ["A", "B", "C"]))
    check("owner's pick is not marked as auto", not AP.is_auto(ep, "A"))
    check("auto_pick never overrides an existing pick", AP.auto_pick(ep) == 0 and
          E.Episode(ep_dir, runs_dir=runs.parent).selected_take("A") == a1)
    errs, warns = E.validate(E.Episode(ep_dir, runs_dir=runs.parent))
    check("_confirmed metadata does not upset validation", not any("_confirmed" in w for w in warns), warns)

print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED: {failures}'}")
sys.exit(1 if failures else 0)
