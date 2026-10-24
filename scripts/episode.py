"""Episode pipeline: validate, plan and render the shots of an episode through the local ComfyUI API.

    PY=~/dev/ComfyUI/.venv/bin/python
    $PY scripts/episode.py validate episodes/midnight_call
    $PY scripts/episode.py plan     episodes/midnight_call
    $PY scripts/episode.py render   episodes/midnight_call [--shot S001] [--dry-run]
    $PY scripts/episode.py select   episodes/midnight_call S001 <take_id>
    $PY scripts/episode.py frame    some.mp4 best|last|<seconds> out.png

Design: docs/automation-plan.md. Episode format: episodes/README.md.
Graphs use the same node ids and values as scripts/run_h3_t2v.py, so a T2V shot with the
same parameters produces the identical API graph (checked by scripts/test_episode.py).
"""
import argparse
import asyncio
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

import aiohttp
import av
import numpy as np
import yaml
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from run_h3_t2v import API, MemorySampler, check_video, run as run_ws  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
RENDERS = pathlib.Path.home() / "AI_renders/comfyui"
MODELS = pathlib.Path.home() / "AI_models/comfyui"
UPLOAD_SUBFOLDER = "ai_short_drama"  # inside ~/dev/ComfyUI/input/
ASPECTS = {"1:1": (1, 1), "2:3": (2, 3), "3:2": (3, 2), "3:4": (3, 4), "4:3": (4, 3),
           "9:16": (9, 16), "16:9": (16, 9), "21:9": (21, 9)}  # = ResolutionSelector's table
FAMILY = {"t2v": "fl2va", "i2v": "fl2va", "flf2v": "fl2va", "r2v": "ref2va"}
IMAGE_INPUTS = {"t2v": (), "i2v": ("first",), "flf2v": ("first", "last"), "r2v": ()}
TESTED = {"pixels": 864 * 480, "frames": 124}  # largest sizes rendered successfully on this Mac
OVERRIDABLE = ("sampler", "scheduler", "steps", "ref_image_size")
SHOT_KEYS = {"type", "prompt", "prompt_file", "seed", "seeds", "takes", "aspect", "megapixels", "duration",
             "first", "last", "refs", "recipe_overrides", "note"}
BEST_WINDOW_S = 1.0  # frame: best = sharpest frame within the last second


# ---------- small helpers ----------

class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate keys (plain YAML silently keeps the last one)."""


def _unique_mapping(loader, node, deep=False):
    keys = [loader.construct_object(k, deep=deep) for k, _ in node.value]
    dup = {k for k in keys if keys.count(k) > 1}
    if dup:
        raise yaml.constructor.ConstructorError(None, None, f"duplicate keys {sorted(dup)}", node.start_mark)
    return loader.construct_mapping(node, deep)


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def load_yaml(path):
    return yaml.load(path.read_text(), Loader=UniqueKeyLoader) or {}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolution(aspect, megapixels, multiple=32):
    """Same arithmetic as ComfyUI's ResolutionSelector node."""
    w, h = ASPECTS[aspect]
    scale = (megapixels * 1024 * 1024 / (w * h)) ** 0.5
    return round(w * scale / multiple) * multiple, round(h * scale / multiple) * multiple


def frames_for(duration, fps=24):
    """Same formula as the templates' ComfyMathExpression: seconds -> 17k+5 frames."""
    n = max(5, round(duration * fps))
    return n + (5 - n % 17) % 17


def manifest():
    rows = {}
    for line in (REPO / "models/manifest.tsv").read_text().splitlines():
        if line.startswith("#") or line.startswith("repo_path"):
            continue
        rel, size, sha, _ = line.split("\t", 3)
        rows[pathlib.Path(rel).name] = (rel, int(size), sha)
    return rows


def api_get(path):
    return json.load(urllib.request.urlopen(f"http://{API}{path}", timeout=10))


def api_post(path, body):
    req = urllib.request.Request(f"http://{API}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=30).read()


# ---------- frames ----------

def sharpness(rgb):
    """Variance of a 3x3 Laplacian on luminance: higher = sharper (less blur)."""
    g = rgb.astype(np.float64) @ [0.299, 0.587, 0.114]
    lap = g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:] - 4 * g[1:-1, 1:-1]
    return float(lap.var())


def extract_frame(video, spec):
    """Return (index, rgb array, info) for spec 'last', 'best' or a time in seconds."""
    with av.open(str(video)) as c:
        fps = float(c.streams.video[0].average_rate)
        frames = [f.to_ndarray(format="rgb24") for f in c.decode(video=0)]
    n = len(frames)
    info = {"frames": n, "spec": spec}
    if spec == "last":
        idx = n - 1
    elif spec == "best":
        lo = n - max(1, min(round(BEST_WINDOW_S * fps), n // 4))  # short clips: last quarter only
        lo = max(0, lo)
        scores = {i: sharpness(frames[i]) for i in range(lo, n)}
        idx = max(scores, key=scores.get)
        info["sharpness"] = {"chosen": round(scores[idx], 1), "last": round(scores[n - 1], 1), "window": [lo, n - 1]}
    else:
        idx = min(n - 1, max(0, round(float(spec) * fps)))
    info["index"] = idx
    return idx, frames[idx], info


CUT_RATIO, CUT_MIN = 10, 30  # a frame change >10x the clip's median and >30/255 = hard cut
FIRST_FRAME_MAX_DIFF = 20    # i2v: frame 0 vs input image; owner's good take = 3.8, ignored = 73


def continuity(video, first_image=None):
    """Hard-cut detection and (for i2v) how closely frame 0 follows the input image.

    Measured 2026-10-23: owner's take01 had an unwanted cut at frame 36 (29x median), take02 none
    (max 5x); a 5-frame i2v ignored its first image (diff 73 vs 3.8 for a 124-frame take).
    """
    with av.open(str(video)) as c:
        fs = [f.to_ndarray(format="rgb24").astype(np.int16) for f in c.decode(video=0)]
    out, warn = {}, []
    if len(fs) > 2:
        d = np.array([np.abs(fs[i + 1] - fs[i]).mean() for i in range(len(fs) - 1)])
        med = max(float(np.median(d)), 0.5)
        cuts = [{"frame": int(i) + 1, "diff": round(float(d[i]), 1), "x_median": round(float(d[i]) / med, 1)}
                for i in np.flatnonzero((d > CUT_RATIO * med) & (d > CUT_MIN))]
        out.update(median_frame_diff=round(med, 2), max_frame_diff=round(float(d.max()), 1), cuts=cuts)
        if cuts:
            warn.append(f"hard cut(s) at frame {[c['frame'] for c in cuts]}")
    if first_image is not None:
        h, w = fs[0].shape[:2]
        ref = np.asarray(Image.open(first_image).convert("RGB").resize((w, h), Image.BILINEAR)).astype(np.int16)
        out["first_frame_diff"] = round(float(np.abs(fs[0] - ref).mean()), 1)
        if out["first_frame_diff"] > FIRST_FRAME_MAX_DIFF:
            warn.append(f"frame 0 does not follow the input image (diff {out['first_frame_diff']})")
    return out, warn


# ---------- episode model ----------

class Episode:
    def __init__(self, path):
        self.dir = pathlib.Path(path).resolve()
        self.data = load_yaml(self.dir / "episode.yaml")
        self.name = self.data.get("episode", self.dir.name)
        self.recipe_name = self.data.get("recipe")
        rp = REPO / "config/recipes" / f"{self.recipe_name}.yaml"
        self.recipe = load_yaml(rp) if rp.exists() else None
        self.recipe_path = rp
        self.shots = self.data.get("shots") or {}
        self.assets = self.data.get("assets") or {}
        self.characters = self.data.get("characters") or {}
        self.sel_path = self.dir / "selections.yaml"
        self.selections = load_yaml(self.sel_path) if self.sel_path.exists() else {}

    # -- shot parameters --
    def params(self, sid):
        s, d = self.shots[sid], self.data.get("defaults") or {}
        get = lambda k, default=None: s.get(k, d.get(k, default))  # noqa: E731
        p = {"id": sid, "type": s.get("type"), "aspect": get("aspect", "9:16"),
             "megapixels": float(get("megapixels", 0.2)), "duration": float(get("duration", 1))}
        p["width"], p["height"] = resolution(p["aspect"], p["megapixels"])
        p["length"] = frames_for(p["duration"])
        if "prompt_file" in s:
            text = (REPO / s["prompt_file"]).read_text()
            p["prompt"] = text[:-1] if text.endswith("\n") else text  # editors add one newline
        else:
            p["prompt"] = s.get("prompt", "")
        if "seeds" in s:
            p["seeds"] = [int(x) for x in s["seeds"]]
        elif "seed" in s:
            p["seeds"] = [int(s["seed"]) + i for i in range(int(get("takes", 1)))]
        else:
            p["seeds"] = []
        r = dict(self.recipe or {})
        r.update(s.get("recipe_overrides") or {})
        p["recipe"] = r
        return p

    def deps(self, sid):
        """Shots this shot continues from (via first/last frame links)."""
        s = self.shots[sid]
        return [v["shot"] for k in ("first", "last") if isinstance(v := s.get(k), dict) and "shot" in v]

    def ref_assets(self, sid):
        out = []
        for r in self.shots[sid].get("refs") or []:
            out += list((self.characters.get(r) or {}).get("refs") or []) if r in self.characters else [r]
        return out

    def selected_take(self, sid):
        v = self.selections.get(sid)
        return v.get("take") if isinstance(v, dict) else v

    # -- takes on disk --
    def takes(self, sid):
        recs = []
        for f in sorted(REPO.glob(f"runs/*/{self.name}__{sid}__*.json")):
            r = json.loads(f.read_text())
            r["_record"] = str(f.relative_to(REPO))
            recs.append(r)
        return recs

    def take_record(self, sid, take_id):
        return next((r for r in self.takes(sid) if r.get("take_id") == take_id and r.get("status") == "success"), None)


# ---------- validation ----------

def validate(ep):
    errors, warnings = [], []
    E, W = errors.append, warnings.append
    if not ep.recipe:
        E(f"recipe '{ep.recipe_name}' not found at {ep.recipe_path.relative_to(REPO)}")
    else:
        man = manifest()
        for role, fname in (ep.recipe.get("models") or {}).items():
            if fname not in man:
                E(f"recipe model {role}={fname} is not in models/manifest.tsv")
                continue
            rel, size, _ = man[fname]
            f = MODELS / rel
            if not f.exists():
                E(f"model file missing: {f}")
            elif f.stat().st_size != size:
                E(f"model file size mismatch: {f} (run scripts/verify_models.sh)")
    for aid, rel in ep.assets.items():
        f = REPO / rel
        if not f.exists():
            E(f"asset {aid}: file missing {rel}")
        else:
            try:
                Image.open(f).verify()
            except Exception as e:  # noqa: BLE001
                E(f"asset {aid}: not a readable image ({e})")
    for cid, c in ep.characters.items():
        for r in (c or {}).get("refs") or []:
            if r not in ep.assets:
                E(f"character {cid}: ref '{r}' is not an asset id")
    if not ep.shots:
        E("no shots")
    for sid, s in ep.shots.items():
        pre = f"shot {sid}:"
        if not isinstance(s, dict):
            E(f"{pre} must be a mapping"); continue
        for k in set(s) - SHOT_KEYS:
            E(f"{pre} unknown key '{k}'")
        t = s.get("type")
        if t not in FAMILY:
            E(f"{pre} type must be one of {sorted(FAMILY)}"); continue
        try:
            p = ep.params(sid)
        except (OSError, ValueError, KeyError) as e:
            E(f"{pre} {e}"); continue
        if p["aspect"] not in ASPECTS:
            E(f"{pre} aspect must be one of {sorted(ASPECTS)}"); continue
        if not p["prompt"].strip():
            E(f"{pre} empty prompt")
        if not p["seeds"]:
            E(f"{pre} needs 'seed' (+ optional 'takes') or 'seeds' — explicit seeds keep takes reproducible")
        if len(set(p["seeds"])) != len(p["seeds"]):
            E(f"{pre} duplicate seeds")
        for k in set(s.get("recipe_overrides") or {}) - set(OVERRIDABLE):
            E(f"{pre} recipe_overrides may only set {OVERRIDABLE}")
        for k in ("first", "last"):
            v = s.get(k)
            if v is None:
                if k in IMAGE_INPUTS[t]:
                    E(f"{pre} type {t} needs '{k}'")
                continue
            if k not in IMAGE_INPUTS[t]:
                E(f"{pre} type {t} does not take '{k}'")
            elif isinstance(v, str):
                if v not in ep.assets:
                    E(f"{pre} {k}: '{v}' is not an asset id")
            elif isinstance(v, dict):
                if v.get("shot") not in ep.shots:
                    E(f"{pre} {k}: shot '{v.get('shot')}' does not exist")
                fr = v.get("frame", "best")
                if fr not in ("best", "last"):
                    try:
                        float(fr)
                    except (TypeError, ValueError):
                        E(f"{pre} {k}: frame must be best, last or seconds")
            else:
                E(f"{pre} {k}: must be an asset id or {{shot: ..., frame: ...}}")
        refs = s.get("refs")
        n_img = len(IMAGE_INPUTS[t])
        if t == "r2v":
            if not refs:
                E(f"{pre} r2v needs refs")
            for r in refs or []:
                if r not in ep.assets and r not in ep.characters:
                    E(f"{pre} ref '{r}' is not an asset or character id")
            n_img = len(ep.ref_assets(sid))
            if n_img > 9:
                E(f"{pre} at most 9 reference images (has {n_img})")
            if re.search(r"<(Video|Audio) \d+>", p["prompt"]):
                E(f"{pre} <Video n>/<Audio n> tags need video/audio references, not supported yet")
            if not re.search(r"<Picture \d+>", p["prompt"]):
                W(f"{pre} r2v prompt has no <Picture n> tags; references work best when named")
            W(f"{pre} r2v has not been rendered on this Mac yet (Stage 6.2 smoke test)")
        elif refs:
            E(f"{pre} only r2v takes refs")
        for m in re.findall(r"<Picture (\d+)>", p["prompt"]):
            if not 1 <= int(m) <= n_img:
                E(f"{pre} prompt mentions <Picture {m}> but the shot has {n_img} image(s)")
        if p["width"] * p["height"] > TESTED["pixels"] or p["length"] > TESTED["frames"]:
            W(f"{pre} {p['width']}x{p['height']}x{p['length']} is larger than anything tested here "
              f"({TESTED['pixels']} px, {TESTED['frames']} frames) — watch swap")
    # cycles
    state = {}

    def visit(sid, stack):
        if state.get(sid) == 1:
            E(f"dependency cycle: {' -> '.join(stack + [sid])}"); return
        if state.get(sid) == 2:
            return
        state[sid] = 1
        for d in ep.deps(sid):
            if d in ep.shots:
                visit(d, stack + [sid])
        state[sid] = 2
    for sid in ep.shots:
        if isinstance(ep.shots[sid], dict):
            visit(sid, [])
    for sid in ep.selections:
        if sid not in ep.shots:
            W(f"selections.yaml: shot {sid} no longer exists")
    return errors, warnings


# ---------- graph + fingerprint ----------

def build_graph(p, images, prefix, seed):
    """API graph for one take. images: {'first'|'last'|'ref0'..: 'subfolder/name.png'}."""
    r, t = p["recipe"], p["type"]
    g = {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": r["models"][FAMILY[t]], "weight_dtype": "default"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": r["models"]["clip"], "type": "minimax", "device": "default"}},
        "vae_v": {"class_type": "VAELoader", "inputs": {"vae_name": r["models"]["video_vae"]}},
        "vae_a": {"class_type": "VAELoader", "inputs": {"vae_name": r["models"]["audio_vae"]}},
    }
    for key, name in images.items():
        g[f"img_{key}"] = {"class_type": "LoadImage", "inputs": {"image": name}}
    common = {"clip": ["clip", 0], "prompt": p["prompt"], "width": p["width"], "height": p["height"], "length": p["length"]}
    if t == "r2v":
        cond = {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": dict(
            common, vae=["vae_v", 0], audio_vae=["vae_a", 0], ref_image_size=r["ref_image_size"])}
        for key in sorted((k for k in images if k.startswith("ref")), key=lambda k: int(k[3:])):
            cond["inputs"][f"ref_images.ref_image_{key[3:]}"] = [f"img_{key}", 0]
    else:
        cond = {"class_type": "MiniMaxH3ImageToVideo", "inputs": dict(common, vae=["vae_v", 0])}
        for key in ("first", "last"):
            if key in images:
                cond["inputs"][f"{key}_frame"] = [f"img_{key}", 0]
    g.update({
        "cond": cond,
        "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "sampler": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": r["sampler"]}},
        "sigmas": {"class_type": "BasicScheduler", "inputs": {
            "model": ["unet", 0], "scheduler": r["scheduler"], "steps": r["steps"], "denoise": 1.0}},
        "guider": {"class_type": "BasicGuider", "inputs": {"model": ["unet", 0], "conditioning": ["cond", 0]}},
        "sample": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["noise", 0], "guider": ["guider", 0], "sampler": ["sampler", 0],
            "sigmas": ["sigmas", 0], "latent_image": ["cond", 1]}},
        "decode_v": {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae_v", 0]}},
        "decode_a": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["sample", 0], "vae": ["vae_a", 0]}},
        "video": {"class_type": "CreateVideo", "inputs": {
            "images": ["decode_v", 0], "audio": ["decode_a", 0], "fps": r["fps"], "bit_depth": r["bit_depth"]}},
        "save": {"class_type": "SaveVideo", "inputs": {
            "video": ["video", 0], "filename_prefix": prefix, "format": "auto", "format.codec": "auto"}},
    })
    return g


def fingerprint(p, image_shas):
    """Hash of everything that determines a take except the seed: graph, model checksums, input pixels."""
    g = build_graph(p, {k: f"<{v}>" for k, v in image_shas.items()}, prefix="", seed=0)
    man = manifest()
    models = {f: man[f][2] for f in p["recipe"]["models"].values() if f in man}
    blob = json.dumps({"graph": g, "models": models}, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()


def resolve_images(ep, sid, materialize):
    """Map image slots to local files. Returns ({slot: (path, provenance)}, blocked_reason)."""
    s, out = ep.shots[sid], {}
    for key in ("first", "last"):
        v = s.get(key)
        if isinstance(v, str):
            out[key] = (REPO / ep.assets[v], {"asset": v, "file": ep.assets[v]})
        elif isinstance(v, dict):
            up, spec = v["shot"], str(v.get("frame", "best"))
            take = ep.selected_take(up)
            if not take:
                return None, f"needs a selected take of {up}"
            rec = ep.take_record(up, take)
            if not rec or "output" not in rec:
                return None, f"selected take {take} of {up} has no successful record"
            frame_png = RENDERS / "episodes" / ep.name / "_frames" / f"{up}_{take}_{spec}.png"
            prov = {"shot": up, "take": take, "frame": spec, "video": rec["output"]["file"]}
            if materialize or frame_png.exists():
                if not frame_png.exists():
                    _, rgb, info = extract_frame(rec["output"]["file"], spec)
                    frame_png.parent.mkdir(parents=True, exist_ok=True)
                    Image.fromarray(rgb).save(frame_png)
                    (frame_png.with_suffix(".json")).write_text(json.dumps(info, indent=1))
                prov.update(json.loads(frame_png.with_suffix(".json").read_text()))
                out[key] = (frame_png, prov)
            else:
                return None, f"frame from {up}/{take} not extracted yet (render will extract it)"
    for i, aid in enumerate(ep.ref_assets(sid)):
        out[f"ref{i}"] = (REPO / ep.assets[aid], {"asset": aid, "file": ep.assets[aid]})
    return out, None


# ---------- plan ----------

def order(ep):
    """Topological order; among ready shots prefer the current model family, then file order."""
    remaining, done, seq, fam = list(ep.shots), set(), [], None
    while remaining:
        ready = [s for s in remaining if all(d in done for d in ep.deps(s))]
        if not ready:
            raise SystemExit("dependency cycle (run validate)")
        pick = next((s for s in ready if FAMILY[ep.shots[s]["type"]] == fam), ready[0])
        fam = FAMILY[ep.shots[pick]["type"]]
        seq.append(pick); done.add(pick); remaining.remove(pick)
    return seq


def shot_status(ep, sid, materialize=False):
    p = ep.params(sid)
    imgs, blocked = resolve_images(ep, sid, materialize)
    st = {"id": sid, "type": p["type"], "family": FAMILY[p["type"]], "size": f"{p['width']}x{p['height']}",
          "frames": p["length"], "seeds": p["seeds"], "selected": ep.selected_take(sid)}
    if blocked:
        return dict(st, state="blocked", reason=blocked, fp=None, todo=p["seeds"], done=[])
    shas = {k: sha256(v[0]) for k, v in imgs.items()}
    fp = fingerprint(p, shas)
    ok = {r["seed"]: r["take_id"] for r in ep.takes(sid) if r.get("fingerprint") == fp and r.get("status") == "success"}
    todo = [x for x in p["seeds"] if x not in ok]
    sel = st["selected"]
    stale_sel = bool(sel) and not sel.startswith(fp[:8])
    return dict(st, state="done" if not todo else "todo", fp=fp, todo=todo, done=list(ok.values()),
                stale_selection=stale_sel, images=imgs, shas=shas, params=p)


def cmd_plan(ep):
    print(f"episode {ep.name}  recipe {ep.recipe_name}")
    print(f"{'shot':6} {'type':5} {'model':6} {'size':9} {'frames':>6}  {'state':8} {'takes':>9}  selected / note")
    for sid in order(ep):
        st = shot_status(ep, sid)
        takes = f"{len(st['done'])}/{len(st['seeds'])}"
        note = st.get("reason") or (st["selected"] or "-")
        if st.get("stale_selection"):
            note += "  (selection is from an older version of this shot)"
        print(f"{sid:6} {st['type']:5} {st['family']:6} {st['size']:9} {st['frames']:>6}  {st['state']:8} {takes:>9}  {note}")


# ---------- render ----------

class SwapGuard(MemorySampler):
    """MemorySampler that interrupts the render once swap exceeds a limit (stop rule)."""

    def __init__(self, limit_gib):
        super().__init__()
        self.limit, self.tripped = limit_gib, False

    def run(self):
        while not self.stop.is_set():
            self.peak_used = max(self.peak_used, self._used())
            self.peak_swap = max(self.peak_swap, self._swap())
            if self.peak_swap > self.limit and not self.tripped:
                self.tripped = True
                print(f"!! swap {self.peak_swap:.1f} GiB > {self.limit} GiB: interrupting", flush=True)
                try:
                    api_post("/interrupt", {})
                except OSError:
                    pass
            time.sleep(1)


async def _upload(path, name):
    data = aiohttp.FormData()
    data.add_field("image", open(path, "rb"), filename=name, content_type="image/png")
    data.add_field("subfolder", UPLOAD_SUBFOLDER)
    data.add_field("type", "input")
    data.add_field("overwrite", "true")
    async with aiohttp.ClientSession() as s:
        async with s.post(f"http://{API}/upload/image", data=data) as r:
            r.raise_for_status()
            j = await r.json()
    return f"{j['subfolder']}/{j['name']}" if j.get("subfolder") else j["name"]


def upload(path, sha):
    """Upload under a content-addressed name, so the graph names exactly these pixels."""
    return asyncio.run(_upload(path, f"{sha[:16]}{pathlib.Path(path).suffix.lower()}"))


def render_take(ep, st, seed, swap_limit):
    p, take_id = st["params"], f"{st['fp'][:8]}_s{seed}"
    prefix = f"episodes/{ep.name}/{p['id']}/{p['id']}_{take_id}"
    names = {k: upload(v[0], st["shas"][k]) for k, v in st["images"].items()}
    graph = build_graph(p, names, prefix, seed)
    labels = {k: v["class_type"] for k, v in graph.items()}
    print(f"== {p['id']} take {take_id}  {p['type']} {p['width']}x{p['height']}x{p['length']}", flush=True)
    mem = SwapGuard(swap_limit); mem.start()
    started = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    prompt_id, wall, times, events, error, hist = asyncio.run(run_ws(graph, labels))
    mem.stop.set(); mem.join()
    stats = api_get("/system_stats")
    status = "stopped_swap" if mem.tripped else ("error" if error else "success")
    rec = {
        "episode": ep.name, "shot": p["id"], "take_id": take_id, "fingerprint": st["fp"], "seed": seed,
        "started": started, "prompt_id": prompt_id, "status": status,
        "error": error and {k: error.get(k) for k in ("node_type", "exception_type", "exception_message")},
        "events": events, "wall_seconds": wall,
        "node_seconds": {labels.get(k, k): v for k, v in times.items()},
        "memory_gib": {"system_used_before": round(mem.base_used, 1), "system_used_peak": round(mem.peak_used, 1),
                       "swap_peak": round(mem.peak_swap, 2), "swap_limit": swap_limit},
        "params": {k: p[k] for k in ("type", "aspect", "megapixels", "duration", "width", "height", "length")},
        "recipe": {"name": ep.recipe_name, "sha256": sha256(ep.recipe_path), "effective": p["recipe"]},
        "inputs": {k: dict(v[1], sha256=st["shas"][k], uploaded_as=names[k]) for k, v in st["images"].items()},
        "prompt_text": p["prompt"],
        "episode_file_sha256": sha256(ep.dir / "episode.yaml"),
        "env": {"comfyui": stats["system"]["comfyui_version"], "pytorch": stats["system"].get("pytorch_version"),
                "python": stats["system"].get("python_version", "").split()[0],
                "comfyui_argv": stats["system"].get("argv"),
                "repo_commit": subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                                              capture_output=True, text=True).stdout.strip(),
                "repo_dirty": bool(subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"],
                                                  capture_output=True, text=True).stdout.strip())},
        "api_prompt": graph,
    }
    if status == "success":
        vids = [v for o in hist.get("outputs", {}).values() for v in (o.get("images", []) + o.get("videos", []))]
        if vids:
            out = RENDERS / vids[0].get("subfolder", "") / vids[0]["filename"]
            rec["output"] = check_video(out)
            rec["output"]["sha256"] = sha256(out)
            problems = []
            if rec["output"]["video"]["frames"] != p["length"]:
                problems.append(f"frames {rec['output']['video']['frames']} != {p['length']}")
            if rec["output"]["video"]["black_frames"]:
                problems.append(f"{rec['output']['video']['black_frames']} black frames")
            if not (rec["output"].get("audio") or {}).get("finite", False):
                problems.append("audio missing or non-finite")
            if problems:
                rec["status"], rec["error"] = "failed_checks", {"checks": problems}
            first = st["images"].get("first")
            rec["continuity"], rec["warnings"] = continuity(out, first[0] if first else None)
        else:
            rec["status"], rec["error"] = "error", {"checks": ["no output file in history"]}
    path = REPO / "runs" / dt.date.today().isoformat() / f"{ep.name}__{p['id']}__{take_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, default=str))  # default=str: e.g. YAML dates
    print(json.dumps({k: rec.get(k) for k in ("status", "error", "warnings", "wall_seconds", "memory_gib")}, indent=1))
    print("record:", path.relative_to(REPO), flush=True)
    return rec


def cmd_render(ep, shots, dry_run, auto_select, swap_limit):
    errors, warnings = validate(ep)
    for w in warnings:
        print("warning:", w)
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(1)
    if not dry_run:
        q = api_get("/queue")
        if q["queue_running"] or q["queue_pending"]:
            raise SystemExit("ComfyUI is busy (a render is running or queued, maybe from the UI). Try again when idle.")
        # unknown models may still be loaded (UI session, other family): start clean (D14)
        api_post("/free", {"unload_models": True, "free_memory": True}); time.sleep(3)
    last_family = None
    for sid in order(ep):
        if shots and sid not in shots:
            continue
        st = shot_status(ep, sid, materialize=not dry_run)
        if st["state"] == "blocked":
            print(f"-- {sid}: blocked, {st['reason']}"); continue
        if st["state"] == "done":
            print(f"-- {sid}: done ({len(st['done'])} takes)")
        for seed in st["todo"]:
            if dry_run:
                names = {k: f"{UPLOAD_SUBFOLDER}/{st['shas'][k][:16]}.png" for k in st["images"]}
                print(f"-- {sid}: would render seed {seed}, take {st['fp'][:8]}_s{seed}")
                print(json.dumps(build_graph(st["params"], names, "<prefix>", seed)["cond"], indent=1)[:1500])
                continue
            if last_family and last_family != st["family"]:
                print(f"-- switching model family {last_family} -> {st['family']}: unloading models", flush=True)
                api_post("/free", {"unload_models": True, "free_memory": True}); time.sleep(3)
            last_family = st["family"]
            rec = render_take(ep, st, seed, swap_limit)
            if rec["status"] != "success":
                raise SystemExit(f"stopping batch: {sid} {rec['status']}")
        if auto_select and not dry_run and not ep.selected_take(sid):
            st = shot_status(ep, sid)
            if st["done"]:
                write_selection(ep, sid, st["done"][0], note="auto-selected (--auto-select, tests only)")


def write_selection(ep, sid, take_id, note=None):
    if not ep.take_record(sid, take_id):
        raise SystemExit(f"no successful take {take_id} for {sid}; see 'plan' / runs/")
    ep.selections[sid] = {"take": take_id, "note": note} if note else take_id
    ep.sel_path.write_text("# Chosen take per shot (take id = fingerprint prefix + seed). Edit by hand or via\n"
                           "# scripts/episode.py select. Shots that continue another shot use this take.\n"
                           + yaml.safe_dump(ep.selections, sort_keys=False, allow_unicode=True))
    print(f"selected {sid} -> {take_id}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("validate", "plan", "render", "select"):
        sp = sub.add_parser(c)
        sp.add_argument("episode")
        if c == "render":
            sp.add_argument("--shot", action="append", help="only these shots (repeatable)")
            sp.add_argument("--dry-run", action="store_true", help="show what would render; no ComfyUI calls")
            sp.add_argument("--auto-select", action="store_true", help="select the first take of unselected shots (tests)")
            sp.add_argument("--swap-limit", type=float, default=20.0, help="GiB; interrupt and stop above this")
        if c == "select":
            sp.add_argument("shot"); sp.add_argument("take")
    fp = sub.add_parser("frame")
    fp.add_argument("video"); fp.add_argument("spec"); fp.add_argument("out")
    a = ap.parse_args()
    if a.cmd == "frame":
        _, rgb, info = extract_frame(a.video, a.spec)
        Image.fromarray(rgb).save(a.out); print(json.dumps(info)); return
    ep = Episode(a.episode)
    if a.cmd == "validate":
        errors, warnings = validate(ep)
        for w in warnings:
            print("warning:", w)
        for e in errors:
            print("ERROR:", e)
        print("OK" if not errors else f"{len(errors)} error(s)")
        raise SystemExit(1 if errors else 0)
    if a.cmd == "plan":
        cmd_plan(ep)
    elif a.cmd == "render":
        cmd_render(ep, a.shot, a.dry_run, a.auto_select, a.swap_limit)
    elif a.cmd == "select":
        write_selection(ep, a.shot, a.take)


if __name__ == "__main__":
    main()
