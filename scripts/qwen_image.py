"""Qwen-Image 2.1 pictures through ComfyUI, built like the official templates (D17).

    PY=~/dev/ComfyUI/.venv/bin/python
    $PY scripts/qwen_image.py t2i  --name Q1 --size 1024x1536 --seed 1 --prompt "..."  [--turbo] [--steps 25]
    $PY scripts/qwen_image.py edit --name Q5 --image inputs/sunlight/ref_lin_v1.png --seed 1 --prompt "..."

Graphs follow image_qwen_image_2_1_{t2i,turbo_t2i,image_edit,background_removal}.json (ComfyUI templates
0.1.115): UNETLoader -> QwenImage21Cache -> KSampler (25 steps, cfg 1, euler/simple) or, for turbo, the
template's 8 manual sigmas; CLIPLoader qwen3vl_8b (type qwen_image) -> TextEncodeQwenImage21. The prompt
enhancer (an extra 9B LLM) is off, as in the templates' default: our prompts are already written in full.
MPS: start ComfyUI with --bf16-text-enc for edits (scripts/launch_comfyui.sh --bf16-text-enc). The text
encoder runs on the CPU in fp16 and overflowed to NaN on reference images (all-black edits, Q5/Q6);
bf16 has fp32's range. Text-to-image works either way. Do not use the flag for H3 renders.
Writes ~/AI_renders/comfyui/qwen_image/<name>_*.png and runs/<date>/qwen_image__<name>__s<seed>.json
(time, memory, inputs with sha256, the API graph).

LICENCE: Qwen RESEARCH LICENSE - research/evaluation only. Pictures made here are NON-COMMERCIAL.
"""
import argparse
import asyncio
import datetime as dt
import json
import pathlib
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import episode as E  # noqa: E402
from run_h3_t2v import MemorySampler, run as run_ws  # noqa: E402

MODELS = {"unet": "qwen_image_2.1_int8_convrot.safetensors",
          "unet_turbo": "qwen_image_2.1_turbo_int8_convrot.safetensors",
          "clip": "qwen3vl_8b_int8_convrot.safetensors",
          "vae": "qwen_image_2.1_vae_bf16.safetensors"}
TURBO_SIGMAS = "1.0, 0.978453, 0.95418, 0.926626, 0.89508, 0.845148, 0.704534, 0.414568, 0"
NOTICE = "Qwen-Image 2.1, Qwen RESEARCH LICENSE: non-commercial (research/evaluation) only"


def base(turbo=False):
    return {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": MODELS["unet_turbo" if turbo else "unet"],
                                                        "weight_dtype": "default"}},
        "cache": {"class_type": "QwenImage21Cache", "inputs": {"model": ["unet", 0], "device": "auto", "dtype": "default"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": MODELS["clip"], "type": "qwen_image", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": MODELS["vae"]}},
    }


def sample(g, latent, seed, steps, turbo):
    if turbo:  # template: SamplerCustomAdvanced + CFGGuider(1) + ManualSigmas
        g.update({
            "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
            "guider": {"class_type": "CFGGuider", "inputs": {"model": ["cache", 0], "positive": ["enc", 0],
                                                             "negative": ["enc", 1], "cfg": 1.0}},
            "sampler": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
            "sigmas": {"class_type": "ManualSigmas", "inputs": {"sigmas": TURBO_SIGMAS}},
            "ks": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["noise", 0], "guider": ["guider", 0],
                                                                    "sampler": ["sampler", 0], "sigmas": ["sigmas", 0],
                                                                    "latent_image": latent}},
        })
    else:
        g["ks"] = {"class_type": "KSampler", "inputs": {"model": ["cache", 0], "positive": ["enc", 0], "negative": ["enc", 1],
                                                       "latent_image": latent, "seed": seed, "steps": steps, "cfg": 1.0,
                                                       "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}}
    g["decode"] = {"class_type": "VAEDecode", "inputs": {"samples": ["ks", 0], "vae": ["vae", 0]}}


def graph_t2i(prompt, negative, w, h, seed, steps=25, turbo=False, prefix="qwen_image/x"):
    g = base(turbo)
    g["enc"] = {"class_type": "TextEncodeQwenImage21", "inputs": {"clip": ["clip", 0], "prompt": prompt,
                                                                 "negative_prompt": negative, "resolution": 1024}}
    g["latent"] = {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}}
    sample(g, ["latent", 0], seed, steps, turbo)
    g["save"] = {"class_type": "SaveImage", "inputs": {"images": ["decode", 0], "filename_prefix": prefix}}
    return g


def graph_edit(image_names, prompt, negative, seed, steps=25, resolution=0, prefix="qwen_image/x"):
    """Image edit / background removal: references enter the text encoder and as VAE latents; the output
    latent takes the first reference's size (template switch = False). resolution 0 (template) keeps the
    references' size; 1024 upscaled a 480x864 reference and gave embossed, sketch-like faces (2026-10-26,
    Q5b/Q6b), and two references at 1024 ran out of memory (Q7)."""
    g = base(False)
    for i, name in enumerate(image_names, 1):
        g[f"img{i}"] = {"class_type": "LoadImage", "inputs": {"image": name}}
    enc = {"clip": ["clip", 0], "vae": ["vae", 0], "prompt": prompt, "negative_prompt": negative, "resolution": resolution}
    for i in range(1, len(image_names) + 1):
        enc[f"images.image_{i}"] = [f"img{i}", 0]
    g["enc"] = {"class_type": "TextEncodeQwenImage21", "inputs": enc}
    sample(g, ["enc", 2], seed, steps, False)
    g["save"] = {"class_type": "SaveImage", "inputs": {"images": ["decode", 0], "filename_prefix": prefix}}
    return g


def is_blank(path):
    """All-zero picture (colour and alpha): what NaN values become when ComfyUI saves them (Q5/Q6)."""
    return not np.asarray(Image.open(path)).any()


def run(graph, name, seed, meta):
    labels = {k: v["class_type"] for k, v in graph.items()}
    mem = MemorySampler(); mem.start()
    started = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    prompt_id, wall, times, events, error, hist = asyncio.run(run_ws(graph, labels))
    mem.stop.set(); mem.join()
    outs = [E.RENDERS / im.get("subfolder", "") / im["filename"]
            for o in (hist or {}).get("outputs", {}).values() for im in o.get("images", [])]
    rec = {"tool": "qwen_image", "name": name, "seed": seed, "started": started, "status": "error" if error else "success",
           "error": error and {k: error.get(k) for k in ("node_type", "exception_type", "exception_message")},
           "wall_seconds": wall, "node_seconds": {labels.get(k, k): v for k, v in times.items()},
           "memory_gib": {"system_used_before": round(mem.base_used, 1), "system_used_peak": round(mem.peak_used, 1),
                          "swap_peak": round(mem.peak_swap, 2)},
           "outputs": [{"file": str(p), "sha256": E.sha256(p)} for p in outs if p.exists()],
           "comfyui_argv": E.api_get("/system_stats")["system"].get("argv"),  # e.g. --bf16-text-enc
           "licence": NOTICE, "meta": meta, "api_prompt": graph}
    blank = [o["file"] for o in rec["outputs"] if is_blank(o["file"])]
    if blank and not error:  # NaN in sampling is saved as an all-zero picture without any error
        rec["status"], rec["error"] = "failed_checks", {"checks": [f"blank (all-zero) picture: {b}" for b in blank]}
    path = E.REPO / "runs" / dt.date.today().isoformat() / f"qwen_image__{name}__s{seed}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, default=str))
    print(json.dumps({k: rec[k] for k in ("name", "status", "error", "wall_seconds", "memory_gib")}), flush=True)
    print("record:", path.relative_to(E.REPO), [o["file"] for o in rec["outputs"]], flush=True)
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("t2i", "edit"):
        sp = sub.add_parser(c)
        sp.add_argument("--name", required=True); sp.add_argument("--prompt", required=True)
        sp.add_argument("--negative", default=""); sp.add_argument("--seed", type=int, default=1)
        sp.add_argument("--steps", type=int, default=25)
        if c == "t2i":
            sp.add_argument("--size", default="1024x1024"); sp.add_argument("--turbo", action="store_true")
        else:
            sp.add_argument("--image", action="append", required=True); sp.add_argument("--resolution", type=int, default=0,
                            help="pixel budget for the references; 0 = keep their size (template default)")
    a = ap.parse_args()
    prefix = f"qwen_image/{a.name}_s{a.seed}"
    if a.cmd == "t2i":
        w, h = (int(x) for x in a.size.split("x"))
        g = graph_t2i(a.prompt, a.negative, w, h, a.seed, a.steps, a.turbo, prefix)
        meta = {"mode": "turbo_t2i" if a.turbo else "t2i", "width": w, "height": h, "steps": 8 if a.turbo else a.steps,
                "prompt": a.prompt, "negative": a.negative}
    else:
        names, inputs = [], []
        for p in a.image:
            sha = E.sha256(E.REPO / p if not pathlib.Path(p).is_absolute() else p)
            names.append(E.upload(E.REPO / p if not pathlib.Path(p).is_absolute() else p, sha))
            inputs.append({"file": p, "sha256": sha})
        g = graph_edit(names, a.prompt, a.negative, a.seed, a.steps, a.resolution, prefix)
        meta = {"mode": "edit", "inputs": inputs, "resolution": a.resolution, "steps": a.steps,
                "prompt": a.prompt, "negative": a.negative}
    run(g, a.name, a.seed, meta)


if __name__ == "__main__":
    main()
