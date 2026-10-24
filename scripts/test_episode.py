"""Offline tests for scripts/episode.py (no rendering; ComfyUI does not need to run).

    ~/dev/ComfyUI/.venv/bin/python scripts/test_episode.py

Checks the size/length arithmetic, that generated graphs equal graphs already proven on this
Mac (Stage 5 T2V run and the owner's UI I2V run), validation of good and bad episodes,
render ordering, fingerprints and frame picking.
"""
import json
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import episode as E  # noqa: E402

REPO = E.REPO
failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def temp_episode(yaml_text):
    d = pathlib.Path(tempfile.mkdtemp(prefix="ep_test_"))
    (d / "episode.yaml").write_text(yaml_text)
    return d


# 1. arithmetic = ResolutionSelector / template math (values from the templates' size note)
for (a, mp), wh in {("16:9", 0.2): (608, 352), ("16:9", 0.4): (864, 480), ("9:16", 0.2): (352, 608),
                    ("9:16", 0.4): (480, 864), ("1:1", 0.4): (640, 640), ("16:9", 0.5): (960, 544)}.items():
    check(f"resolution {a} {mp}", E.resolution(a, mp) == wh, E.resolution(a, mp))
for sec, n in {0.2: 5, 0.9: 22, 1: 39, 2: 56, 3: 73, 5: 124}.items():
    check(f"frames {sec}s", E.frames_for(sec) == n, E.frames_for(sec))

# 2. T2V graph == the graph that produced Stage 5's verified video
st = E.Episode(REPO / "episodes/_selftest")
p = st.params("T1")
proven = json.loads((REPO / "runs/2026-10-23/stage5_repro_a.json").read_text())["api_prompt"]
mine = E.build_graph(p, {}, proven["save"]["inputs"]["filename_prefix"], 757358688076805)
check("T2V graph identical to stage5_repro_a", mine == proven,
      [k for k in set(mine) | set(proven) if mine.get(k) != proven.get(k)])

# 3. I2V graph == owner's UI graph (UI graph has switch/math nodes; resolve them by hand)
ui = json.loads((REPO / "runs/2026-10-23/ui_midnight_call_S001_take01_00001.json").read_text())["api_prompt"]
mc = E.Episode(REPO / "episodes/midnight_call")
p = mc.params("S001")
g = E.build_graph(p, {"first": "x.png"}, "p", 757358688076805)
res = ui["115"]["inputs"]
aspect = res["aspect_ratio"].split(" ")[0]
ui_sem = {
    "unet": ui["140:127"]["inputs"]["unet_name"], "clip": ui["140:128"]["inputs"]["clip_name"],
    "vae_v": ui["140:119"]["inputs"]["vae_name"], "vae_a": ui["140:120"]["inputs"]["vae_name"],
    "prompt": ui["140:131"]["inputs"]["prompt"], "seed": ui["140:129"]["inputs"]["noise_seed"],
    "sampler": ui["140:123"]["inputs"]["sampler_name"], "scheduler": ui["140:124"]["inputs"]["scheduler"],
    "steps": ui["140:137"]["inputs"]["value"] if ui["140:139"]["inputs"]["value"] is False else None,
    "wh": E.resolution(aspect, res["megapixels"]), "length": E.frames_for(ui["140:133"]["inputs"]["value"]),
    "fps": ui["140:130"]["inputs"]["fps"], "bit_depth": ui["140:130"]["inputs"]["bit_depth"],
    "first_frame": "first_frame" in ui["140:131"]["inputs"], "last_frame": "last_frame" in ui["140:131"]["inputs"],
}
my_sem = {
    "unet": g["unet"]["inputs"]["unet_name"], "clip": g["clip"]["inputs"]["clip_name"],
    "vae_v": g["vae_v"]["inputs"]["vae_name"], "vae_a": g["vae_a"]["inputs"]["vae_name"],
    "prompt": g["cond"]["inputs"]["prompt"], "seed": g["noise"]["inputs"]["noise_seed"],
    "sampler": g["sampler"]["inputs"]["sampler_name"], "scheduler": g["sigmas"]["inputs"]["scheduler"],
    "steps": g["sigmas"]["inputs"]["steps"], "wh": (g["cond"]["inputs"]["width"], g["cond"]["inputs"]["height"]),
    "length": g["cond"]["inputs"]["length"], "fps": g["video"]["inputs"]["fps"],
    "bit_depth": g["video"]["inputs"]["bit_depth"],
    "first_frame": "first_frame" in g["cond"]["inputs"], "last_frame": "last_frame" in g["cond"]["inputs"],
}
check("I2V graph matches owner's UI run", ui_sem == my_sem,
      {k: (ui_sem[k], my_sem[k]) for k in ui_sem if ui_sem[k] != my_sem[k]})
ui_img = pathlib.Path.home() / "dev/ComfyUI/input" / ui[ui["140:131"]["inputs"]["first_frame"][0]]["inputs"]["image"]
check("I2V keyframe asset is byte-identical to the UI input",
      E.sha256(ui_img) == E.sha256(REPO / mc.assets["kf_S001_desk"]))

# 4. validation of the real episodes
for name in ("midnight_call", "_selftest"):
    errs, warns = E.validate(E.Episode(REPO / "episodes" / name))
    check(f"validate {name}: no errors", not errs, errs)

# 5. validation catches mistakes
BASE = """episode: t
recipe: h3_base_v1
assets: {kf: inputs/midnight_call/kf_S001_desk_v1.png}
shots:
"""
bad = {
    "missing seed": "  A: {type: t2v, prompt: hi}",
    "unknown type": "  A: {type: v2v, prompt: hi, seed: 1}",
    "i2v without first": "  A: {type: i2v, prompt: hi, seed: 1}",
    "t2v with first": "  A: {type: t2v, first: kf, prompt: hi, seed: 1}",
    "bad asset id": "  A: {type: i2v, first: nope, prompt: hi, seed: 1}",
    "picture tag out of range": "  A: {type: i2v, first: kf, prompt: '<Picture 2> waves', seed: 1}",
    "r2v audio tag": "  A: {type: r2v, refs: [kf], prompt: '<Picture 1> sings <Audio 1>', seed: 1}",
    "unknown key (typo)": "  A: {type: t2v, promt: hi, prompt: hi, seed: 1}",
    "cycle": "  A: {type: i2v, first: {shot: B}, prompt: a, seed: 1}\n  B: {type: i2v, first: {shot: A}, prompt: b, seed: 1}",
    "continues missing shot": "  A: {type: i2v, first: {shot: Z}, prompt: a, seed: 1}",
    "bad frame spec": "  A: {type: t2v, prompt: a, seed: 1}\n  B: {type: i2v, first: {shot: A, frame: middle}, prompt: b, seed: 1}",
    "bad override": "  A: {type: t2v, prompt: a, seed: 1, recipe_overrides: {cfg: 5}}",
}
for name, shots in bad.items():
    d = temp_episode(BASE + shots)
    errs, _ = E.validate(E.Episode(d))
    check(f"rejects: {name}", bool(errs), "no error raised")
    shutil.rmtree(d)
d = temp_episode(BASE + "  A: {type: t2v, prompt: a, seed: 1}\n  A: {type: t2v, prompt: b, seed: 2}")
try:
    E.Episode(d); check("rejects: duplicate shot id", False)
except Exception:  # noqa: BLE001
    check("rejects: duplicate shot id", True)
shutil.rmtree(d)

# 6. ordering: dependencies first, then fewest model switches
d = temp_episode(BASE + """  A: {type: t2v, prompt: a, seed: 1}
  B: {type: r2v, refs: [kf], prompt: '<Picture 1>', seed: 1}
  C: {type: t2v, prompt: c, seed: 1}
  D: {type: i2v, first: {shot: B}, prompt: d, seed: 1}
  F: {type: r2v, refs: [kf], prompt: '<Picture 1>', seed: 1}""")
o = E.order(E.Episode(d))
check("order groups families and respects links", o == ["A", "C", "B", "F", "D"], o)
shutil.rmtree(d)

# 7. fingerprints: seed-independent, prompt- and image-dependent; downstream blocked until selection
p = st.params("I1")
fp1 = E.fingerprint(p, {"first": "aa"})
check("fingerprint ignores seed", fp1 == E.fingerprint(dict(p, seeds=[99]), {"first": "aa"}))
check("fingerprint changes with prompt", fp1 != E.fingerprint(dict(p, prompt=p["prompt"] + "!"), {"first": "aa"}))
check("fingerprint changes with input pixels", fp1 != E.fingerprint(p, {"first": "bb"}))
check("fingerprint changes with steps override",
      fp1 != E.fingerprint(dict(p, recipe=dict(p["recipe"], steps=8)), {"first": "aa"}))
s = E.shot_status(st, "C1")
check("continuation blocked until upstream take selected",
      s["state"] == "blocked" or st.selected_take("I1") is not None, s.get("reason"))

# 8. frame picking on the owner's take (owner hand-picked frame 122 of 124 for take 2)
vid = pathlib.Path.home() / "AI_renders/comfyui/video/midnight_call/S001_take01_00001_.mp4"
if vid.exists():
    i_last, _, _ = E.extract_frame(vid, "last")
    i_best, _, info = E.extract_frame(vid, "best")
    i_t, _, _ = E.extract_frame(vid, "1.0")
    check("frame last", i_last == 123, i_last)
    check("frame at 1.0 s", i_t == 24, i_t)
    check("frame best within last second", 100 <= i_best <= 123, i_best)
    print(f"     info: best frame = {i_best}, sharpness {info['sharpness']}")

print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED: {failures}'}")
sys.exit(1 if failures else 0)
