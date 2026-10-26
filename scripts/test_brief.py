"""Offline tests for scripts/brief.py (no rendering, no macOS Vision: the face check is stubbed).

    ~/dev/ComfyUI/.venv/bin/python scripts/test_brief.py

The real Vision face check is tested separately: scripts/test_vision_integration.py
(RUN_VISION_INTEGRATION=1 scripts/check.sh).
"""
import contextlib
import io
import pathlib
import shutil
import subprocess
import sys
import tempfile
from unittest import mock

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import brief as B  # noqa: E402
import episode as E  # noqa: E402
import face_check as FC  # noqa: E402

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


# The face check is replaced by fixed, synthetic measurements (deterministic: never what Vision happens to
# see on this Mac). The guard fails loudly if anything still reaches the Swift/Vision helper.
REAL_FACES = FC.faces_in_images
WOMAN_IMG = E.REPO / "inputs/midnight_call/kf_S001_desk_v1.png"
ROOM_IMG = E.REPO / "inputs/_location/room_plate_v1.png"
FACE = {"width": 704, "height": 1216, "h": 489.0, "quality": 0.85, "error": None}  # above 300 px / 0.5
NO_SIZE = {"width": None, "height": None, "h": None, "quality": None, "error": None}
vision_guard = mock.patch.object(FC, "helper", side_effect=AssertionError("standard tests must not call macOS Vision")).start()
s0 = mock.patch.object(FC, "faces_in_images", side_effect=lambda paths: [dict(FACE, path=str(p)) for p in paths]).start()

# validate
write_brief(GOOD)
errs, warns, info = B.validate_brief(GOOD, ep_dir)
check("good brief has no errors", not errs, errs)
check("reference face is measured", any("face" in i and "px" in i for i in info), info)
check("face check gets the character reference", s0.call_args.args[0] == [WOMAN_IMG], s0.call_args)
check("good brief: no face warning", not any("face" in w for w in warns), warns)
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


# face check results and failures (brief.py validate crashed with a TypeError when the helper returned
# no width/height). Every case must give a clear error/warning, never a traceback.
def validate_with(name, *per_image, raises=None, images=(WOMAN_IMG,)):
    """validate_brief with the face check returning per_image[k] for image k (or raising `raises`)."""
    brief = dict(GOOD, characters={"woman": {"description": "young woman",
                                             "images": [str(p.relative_to(E.REPO)) for p in images]}})
    stub = (lambda paths: [dict(r, path=str(p)) for p, r in zip(paths, per_image)]) if raises is None else None
    with mock.patch.object(FC, "faces_in_images", side_effect=raises or stub) as m:
        try:
            result = B.validate_brief(brief, ep_dir)
        except Exception as e:  # noqa: BLE001 - reported as a test failure, not a crash of the test file
            check(f"{name}: no exception", False, repr(e))
            return [], [], []
    check(f"{name}: no exception", True)
    check(f"{name}: face check gets the brief's images", m.call_args.args[0] == list(images), m.call_args)
    return result


errs, warns, info = validate_with("A", NO_SIZE)
check("A: no face, no width/height -> clear error", any(e.endswith("size unknown: no face found") for e in errs), errs)
errs, warns, info = validate_with("B", dict(FACE, h=None))
check("B: no face, known size -> today's message", any(e.endswith("704x1216: no face found") for e in errs), errs)
errs, warns, info = validate_with("C", FACE)
check("C: face found -> info line, no errors or warnings",
      not errs and not warns and info == ["character 'woman' image 1 (kf_S001_desk_v1.png): 704x1216, face 489 px, "
                                          "quality 0.85"], (errs, warns, info))
errs, warns, info = validate_with("C2", dict(FACE, quality=None))
check("C2: face found, quality unknown", not errs and any(i.endswith("quality unknown") for i in info), (errs, info))
errs, warns, info = validate_with("C3", dict(FACE, h=299.0))
check("C3: main reference face under 300 px warns", not errs and any("small or soft" in w for w in warns), (errs, warns))
errs, warns, info = validate_with("D1", dict(NO_SIZE, error="unreadable"))
check("D1: helper error -> face check failed", any("size unknown: face check failed (unreadable)" in e for e in errs), errs)
errs, warns, info = validate_with("D2", raises=subprocess.CalledProcessError(1, ["face_boxes"]))
check("D2: helper exits non-zero -> face check failed", any("face check failed (CalledProcessError" in e for e in errs), errs)
errs, warns, info = validate_with("D3", raises=FileNotFoundError(2, "No such file or directory", "swiftc"))
check("D3: helper cannot run -> face check failed", any("face check failed (FileNotFoundError" in e for e in errs), errs)
errs, warns, info = validate_with("E", FACE, NO_SIZE, images=(WOMAN_IMG, ROOM_IMG))
check("E: second image without a face is a warning, not an error",
      not errs and any("image 2" in w and w.endswith("no face found") for w in warns), (errs, warns))

out, err = io.StringIO(), io.StringIO()
with mock.patch.object(FC, "faces_in_images", side_effect=lambda paths: [dict(NO_SIZE, path=str(p)) for p in paths]):
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = B.report(*B.validate_brief(GOOD, ep_dir))
    except Exception as e:  # noqa: BLE001
        rc = repr(e)
check("F: validate output is an ERROR line and exit code 1, no traceback",
      rc == 1 and "ERROR: character 'woman' image 1" in out.getvalue() and "no face found" in out.getvalue()
      and "Traceback" not in out.getvalue() + err.getvalue(), (rc, out.getvalue(), err.getvalue()))


def helper_prints(stdout):
    """The real faces_in_images with the Swift helper replaced by fixed output (no Vision)."""
    run = mock.Mock(return_value=subprocess.CompletedProcess([], 0, stdout=stdout, stderr=""))
    return mock.patch.multiple(FC, faces_in_images=REAL_FACES, helper=mock.Mock(return_value=pathlib.Path("/fake/face_boxes")),
                               subprocess=mock.Mock(run=run))


def attempt(fn):
    """(result, None) or (None, exception)."""
    try:
        return fn(), None
    except Exception as e:  # noqa: BLE001
        return None, e


ERR_LINE = '{"file": "a.png", "error": "unreadable"}\n'
FACE_LINE = '{"file": "b.png", "width": 704, "height": 1216, "faces": [{"h": 100, "quality": 0.5}, {"h": 489, "quality": 0.85}]}\n'
with helper_prints(ERR_LINE + FACE_LINE):
    r = FC.faces_in_images([WOMAN_IMG, ROOM_IMG])
check("G1: helper error line -> no size, error kept",
      r[0]["width"] is None and r[0]["height"] is None and r[0]["h"] is None and r[0].get("error") == "unreadable", r)
check("G1: measurement line -> largest face", (r[1]["width"], r[1]["height"], r[1]["h"], r[1]["quality"], r[1].get("error"))
      == (704, 1216, 489, 0.85, None), r)
with helper_prints(FACE_LINE):
    _, e = attempt(lambda: FC.faces_in_images([WOMAN_IMG, ROOM_IMG]))
check("G2: two images, one result -> ValueError naming both images",
      isinstance(e, ValueError) and "1 result(s) for 2 image(s)" in str(e)
      and "kf_S001_desk_v1.png" in str(e) and "room_plate_v1.png" in str(e), repr(e))
two = dict(GOOD, characters={"woman": {"description": "young woman", "images": [str(WOMAN_IMG.relative_to(E.REPO)),
                                                                              str(ROOM_IMG.relative_to(E.REPO))]}})
with helper_prints(FACE_LINE):
    res, e = attempt(lambda: B.validate_brief(two, ep_dir))
errs, warns, _ = res or ([], [], [])
MISMATCH = "face check failed (ValueError: face helper returned 1 result(s) for 2 image(s)"
check("G2b: result count mismatch -> no image passes silently",
      e is None and any("image 1" in x and MISMATCH in x for x in errs) and any("image 2" in x and MISMATCH in x for x in warns),
      (repr(e), errs, warns))
with helper_prints("not json\n"):
    _, e = attempt(lambda: FC.faces_in_images([WOMAN_IMG]))
    res, v = attempt(lambda: B.validate_brief(GOOD, ep_dir))
errs = res[0] if res else []
check("G3: output that is not JSON -> ValueError with the line number",
      isinstance(e, ValueError) and "line 1 is not JSON" in str(e), repr(e))
check("G3: ... and a face-check error from validate",
      v is None and any("face check failed (ValueError: face helper output line 1 is not JSON" in x for x in errs), (repr(v), errs))
for line, kind in (("[]", "list"), ("null", "NoneType")):  # valid JSON, but not one object per image
    with helper_prints(line + "\n"):
        _, e = attempt(lambda: FC.faces_in_images([WOMAN_IMG]))
        res, v = attempt(lambda: B.validate_brief(GOOD, ep_dir))
    errs = res[0] if res else []
    check(f"G4: helper prints {line} -> ValueError with the line number and type",
          isinstance(e, ValueError) and f"line 1 is a JSON {kind}, not an object" in str(e), repr(e))
    check(f"G4: helper prints {line} -> a face-check error from validate, no traceback",
          v is None and any("face check failed (ValueError: face helper output line 1 is a JSON" in x for x in errs),
          (repr(v), errs))

# G5: field types in a helper record (numbers or null; faces a list of objects; bool is not a number)
for line, msg in (('{"faces": "x"}', "line 1: faces is a str, not a list"),
                  ('{"faces": ["x"]}', "line 1: faces[0] is a str, not an object"),
                  ('{"width": "704", "height": 1216, "faces": []}', "line 1: width is a str, not a number"),
                  ('{"width": 704, "height": 1216, "faces": [{"h": true, "quality": 0.5}]}', "line 1: faces[0].h is a bool, not a number")):
    with helper_prints(line + "\n"):
        _, e = attempt(lambda: FC.faces_in_images([WOMAN_IMG]))
    check(f"G5: {line} -> ValueError naming the field", isinstance(e, ValueError) and msg in str(e), repr(e))
for line, msg in (('{"width": "704", "height": 1216, "faces": []}', "width is a str"),
                  ('{"width": 704, "height": 1216, "faces": [{"h": 489, "quality": "0.85"}]}', "faces[0].quality is a str")):
    with helper_prints(line + "\n"):
        res, v = attempt(lambda: B.validate_brief(GOOD, ep_dir))
    errs = res[0] if res else []
    check(f"G5: {msg} -> face check failed from validate, no traceback",
          v is None and any("face check failed (ValueError: face helper output line 1: " + msg in x for x in errs),
          (repr(v), errs))
with helper_prints('{"width": 704, "height": 1216, "faces": [{"h": null, "quality": null}, {"h": 489, "quality": 0.85}]}\n'
                   '{"width": 704, "height": 1216, "faces": [{"h": null, "quality": null}]}\n'):
    r, e = attempt(lambda: FC.faces_in_images([WOMAN_IMG, ROOM_IMG]))
check("G5: faces with h null and a number -> the measured face", e is None and (r[0]["h"], r[0]["quality"]) == (489, 0.85),
      (repr(e), r))
check("G5: only h null -> no face", e is None and r[1]["h"] is None, (repr(e), r))

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

check("H: standard tests never called macOS Vision", vision_guard.call_count == 0, vision_guard.call_count)
mock.patch.stopall()
shutil.rmtree(root)
print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED: {failures}'}")
sys.exit(1 if failures else 0)
