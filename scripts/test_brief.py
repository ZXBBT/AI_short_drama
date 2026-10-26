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
# a product reference (kind: object) has no face: no face check, no "no face found" error
obj = dict(GOOD, characters=dict(GOOD["characters"], can={"description": "a beer can", "kind": "object",
                                                          "images": ["inputs/_location/room_plate_v1.png"]}))
errs, _, info = B.validate_brief(obj, ep_dir)
check("object reference: no face check", not errs and not any("'can'" in i for i in info), (errs, info))
errs, _, _ = B.validate_brief(dict(GOOD, characters={"can": {"description": "x", "kind": "thing"}}), ep_dir)
check("rejects an unknown character kind", any("kind must be" in e for e in errs), errs)

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
errs, _, _ = with_shots("  A: {type: r2v, refs: [woman, loc_room_1], seed: 1, prompt: 'subject_definitions: <Subject 1> is "
                        "the woman in <Picture 1>: {woman}. <Subject 2> is the room environment in <Picture 2>: a lamp.'}\n")
check("official format: person + environment <Subject 2> allowed (_multiref)", not errs, errs)
errs, _, _ = with_shots("  A: {type: r2v, refs: [woman], seed: 1, megapixels: 0.4, duration: 5, prompt: '<Picture 1> is {woman}.'}\n")
check("rejects an unproven size/length (0.4 MP x 5 s)", any("not been rendered" in e for e in errs), errs)
_, warns, _ = with_shots("  A: {type: r2v, refs: [woman], seed: 1, prompt: '<Picture 1> is a woman.'}\n")
check("warns when the character placeholder is missing", any("{woman}" in w for w in warns), warns)
check("warns when brief dialogue is unused", any("Hello?" in w for w in warns), warns)
_, warns, _ = with_shots("".join(f"  S{i}: {{type: r2v, refs: [woman], seed: {i}, prompt: '<Picture 1> is {{woman}}.'}}\n"
                                 for i in range(12)))
check("warns when the plan is far longer than the target", any("add up to" in w for w in warns), warns)
check("warns when the render budget is exceeded", any("exceeds budget" in w for w in warns), warns)

# official H3 prompt format (h3-prompt-writing skill)
OFFICIAL_R2V = (
    "subject_definitions:\n<Subject 1> is {woman}, from <Picture 1>.\n\nsummary:\n[reference generation] She greets someone.\n\n"
    "retention_analysis:\n<Subject 1> (appears in [Shot 1]): fully_preserved - face, hair and outfit.\n\n"
    "detailed_description:\nThe target video is live-action with soft daylight.\n[Shot 1] A close-up of <Subject 1> (S1), who says: "
    "<d>[English] Hello?</d>\n\noverall_soundscape: Birdsong.\n\nnon_diegetic_music: N/A")
def r2v_shot(prompt, sid="B"):
    return (f"  {sid}:\n    type: r2v\n    refs: [woman]\n    seed: 2\n    dialogue: [{{character: woman, line: 'Hello?'}}]\n"
            "    prompt: |-\n" + "".join(f"      {l}\n" for l in prompt.splitlines()))
_, warns, _ = with_shots(r2v_shot(OFFICIAL_R2V))
check("official-format R2V prompt: no format warnings", not any("official" in w or "double quotes" in w for w in warns), warns)
_, warns, _ = with_shots(r2v_shot('<Picture 1> is {woman}. She says "Hello?"'))
check("quoted dialogue warns (on-screen text risk)", any("double quotes" in w for w in warns), warns)
check("free-form R2V prompt warns about the official format", any("subject_definitions" in w for w in warns), warns)
_, warns, _ = with_shots("  C: {type: i2v, first: loc_room_1, seed: 3, prompt: 'integrated_multimodal_description: [Shot 1] room. "
                         "overall_soundscape: quiet. non_diegetic_music: N/A'}\n")
check("I2V without the official first-frame line warns", any("first-frame line" in w for w in warns), warns)
_, warns, _ = with_shots("  D: {type: t2v, seed: 4, prompt: 'integrated_multimodal_description: [Shot 1] a. [Shot 2] At 00:05.000, b. "
                         "overall_soundscape: x. non_diegetic_music: N/A'}\n")
check("a cut after the end of a 3 s clip warns", any("after the clip ends" in w for w in warns), warns)

# direction skill (V2 revision brief): screen text, sound mixed in the edit, very short clips
P = {"type": "t2v", "length": 73, "prompt": 'A phone screen shows the app title "SUPER DRY CLUB". non_diegetic_music: soft pads'}
w = B.direction_problems(P)
check("screen/interface text warns (composite instead)", any("chroma-key" in x for x in w), w)
check("music in the picture is fine unless sound is mixed in the edit", not any("continuous track" in x for x in w), w)
w = B.direction_problems(dict(P, prompt="He (S1) says in an off-screen voiceover: <d>[English] Hi.</d>"), sound_in_edit=True)
check("sound: edit -> voice-over and music in a picture render warn",
      any("lips stay closed" in x for x in w) and any("continuous track" in x for x in w), w)
w = B.direction_problems(dict(P, prompt="A wide view. non_diegetic_music: N/A", length=56), sound_in_edit=True)
check("sound: edit + music N/A is clean; 56 frames warns about the trained length",
      len(w) == 1 and "trained length" in w[0], w)

# official guide: R2V detailed_description 350-500 words
R = "subject_definitions: a. summary: b. retention_analysis: c. detailed_description: {} overall_soundscape: d. non_diegetic_music: N/A"
w = B.official_format_problems({"type": "r2v", "length": 90, "prompt": R.format("word " * 200)}, [])
check("R2V description under 350 words warns", any("350-500" in x for x in w), w)
w = B.official_format_problems({"type": "r2v", "length": 90, "prompt": R.format("word " * 360)}, [])
check("R2V description of 360 words is fine", not any("350-500" in x for x in w), w)

# outfit completeness (Sunlight P5: trousers changed between shots)
w = B.outfit_problems("lin", "young woman, long dark hair, white T-shirt", "She stands up from the bench and walks away.")
check("outfit: lower body shown, no trousers named -> warns", any("trousers" in x for x in w), w)
check("outfit: walking shot without shoes named -> warns", any("shoes" in x for x in w), w)
w = B.outfit_problems("lin", "young woman, white T-shirt, black trousers, white sneakers", "She walks away along the path.")
check("outfit: complete description is clean", w == [], w)
w = B.outfit_problems("lin", "young woman, white T-shirt", "A close-up of her face as she smiles.")
check("outfit: close-up needs only the top", w == [], w)
w = B.outfit_problems("mia", "woman in a long red dress", "Full-body shot: she walks in.")
check("outfit: a dress counts as top and bottom", len(w) == 1 and "shoes" in w[0], w)
w = B.outfit_problems("lin", "woman, white T-shirt, black trousers", "She sits on the bench. Nobody walks across the frame.")
check("outfit: other people walking do not count", w == [], w)
w = B.outfit_problems("max", "young man with short hair", "A close-up of his face.")
check("outfit: no top named -> warns", any("no top" in x for x in w), w)

shutil.rmtree(root)
print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED: {failures}'}")
sys.exit(1 if failures else 0)
