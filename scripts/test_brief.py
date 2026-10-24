"""Offline tests for scripts/brief.py (no rendering).

    ~/dev/ComfyUI/.venv/bin/python scripts/test_brief.py
"""
import pathlib
import shutil
import sys
import tempfile

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import brief as B  # noqa: E402
import episode as E  # noqa: E402

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures.append(name)


root = pathlib.Path(tempfile.mkdtemp(prefix="brief_test_"))
ep_dir = root / "tstory"
ep_dir.mkdir()
GOOD = {
    "episode": "tstory", "title": "Test story", "plot": "A woman waits for a call.",
    "target": {"length_s": 9, "aspect": "9:16"},
    "style": "realistic", "characters": {"woman": {"description": "young woman,\n  dark hair",
                                                   "images": ["inputs/midnight_call/kf_S001_desk_v1.png"]}},
    "locations": {"room": {"description": "small dim room", "images": ["inputs/_location/room_plate_v1.png"]}},
    "dialogue": [{"character": "woman", "line": "Hello?"}],
    "budget": {"takes_per_shot": 2, "max_render_hours": 1},
    "review": {"picks": "auto", "final": True},
}


def write_brief(d):
    (ep_dir / "brief.yaml").write_text(yaml.safe_dump(d, sort_keys=False))


# validate
write_brief(GOOD)
errs, warns, info = B.validate_brief(GOOD, ep_dir)
check("good brief has no errors", not errs, errs)
check("reference face is measured", any("face" in i and "px" in i for i in info), info)
bad = dict(GOOD, episode="other", target={"length_s": 1000, "aspect": "5:4"}, review={"picks": "maybe"})
errs, _, _ = B.validate_brief(bad, ep_dir)
for what in ("folder name", "length_s", "aspect", "review.picks"):
    check(f"rejects bad {what}", any(what in e for e in errs), errs)
errs, _, _ = B.validate_brief(dict(GOOD, characters={"woman": {"description": "x", "images": ["nope.png"]}}), ep_dir)
check("rejects missing image", any("not found" in e for e in errs), errs)

# scaffold
out = B.scaffold(GOOD, ep_dir, ep_dir / "brief.yaml")
ep_yaml = yaml.safe_load(out.read_text())
check("scaffold uses recipe v2 (PyTorch attention)", ep_yaml["recipe"] == "h3_base_v2")
check("scaffold: one reference per character", ep_yaml["characters"]["woman"]["refs"] == ["char_woman_1"])
check("scaffold: description collapsed to one line", ep_yaml["characters"]["woman"]["description"] == "young woman, dark hair")
check("scaffold: location plates listed", ep_yaml["locations"]["room"]["plates"] == ["loc_room_1"])
check("scaffold: review settings copied", ep_yaml["review"] == {"picks": "auto", "final": True})
try:
    B.scaffold(GOOD, ep_dir, ep_dir / "brief.yaml"); check("scaffold refuses to overwrite", False)
except SystemExit:
    check("scaffold refuses to overwrite", True)


SCAFFOLD_TEXT = out.read_text()


def with_shots(shots_yaml):
    text = SCAFFOLD_TEXT.replace("shots: {}\n", "shots:\n" + shots_yaml)
    (ep_dir / "episode.yaml").write_text(text)
    return B.check_plan(ep_dir)


# a plan that follows every rule
errs, warns, info = with_shots(
    "  A: {type: i2v, first: loc_room_1, duration: 2, seed: 1, prompt: '<Picture 1> shows {room}, empty. No cut.'}\n"
    "  B: {type: r2v, refs: [woman], seed: 2, prompt: '<Picture 1> is {woman}. Close-up, she says \"Hello?\"',\n"
    "      dialogue: [{character: woman, line: 'Hello?'}]}\n")
check("rule-following plan: no errors", not errs, errs)
check("estimates render time", info["render_hours"] > 0, info)
check("location placeholder expands", "small dim room" in E.Episode(ep_dir).params("A")["prompt"])

# rule violations
errs, _, _ = with_shots("  A: {type: r2v, refs: [woman, loc_room_1], seed: 1, prompt: '<Picture 1> is {woman}. <Picture 2>'}\n")
check("rejects a location plate as R2V reference", any("plate" in e for e in errs), errs)
check("rejects two references in one R2V shot", any("exactly one character" in e for e in errs), errs)
errs, _, _ = with_shots("  A: {type: r2v, refs: [woman], seed: 1, megapixels: 0.4, duration: 5, prompt: '<Picture 1> is {woman}.'}\n")
check("rejects an unproven size/length (0.4 MP x 5 s)", any("not been rendered" in e for e in errs), errs)
_, warns, _ = with_shots("  A: {type: r2v, refs: [woman], seed: 1, prompt: '<Picture 1> is a woman.'}\n")
check("warns when the character placeholder is missing", any("{woman}" in w for w in warns), warns)
check("warns when brief dialogue is unused", any("Hello?" in w for w in warns), warns)
_, warns, _ = with_shots("".join(f"  S{i}: {{type: r2v, refs: [woman], seed: {i}, prompt: '<Picture 1> is {{woman}}.'}}\n"
                                 for i in range(12)))
check("warns when the plan is far longer than the target", any("add up to" in w for w in warns), warns)
check("warns when the render budget is exceeded", any("exceeds budget" in w for w in warns), warns)

shutil.rmtree(root)
print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED: {failures}'}")
sys.exit(1 if failures else 0)
