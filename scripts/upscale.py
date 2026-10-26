"""Upscale a picked take with SeedVR2 (one-step video restoration, Apache 2.0) through ComfyUI, built like the
official template workflows/official/utility_seedvr2_3b_int8_upscale_video__templates-0.11.89.json.

    PY=~/dev/ComfyUI/.venv/bin/python
    $PY scripts/upscale.py episodes/sunlight P2                  # the picked take, 3B, x2
    $PY scripts/upscale.py episodes/sunlight P2 --model 7b_sharp
    $PY scripts/upscale.py --video some.mp4 --name test --scale 2
    $PY scripts/upscale.py --cut episodes/sunlight/cut.yaml      # every shot with `upscale: 7b_sharp` in the cut

Graph (template, subgraph "Upscale Video (SeedVR2 3B Int8)", split_latent off): LoadVideo ->
GetVideoComponents -> ResizeImageMaskNode (scale by multiplier, lanczos) -> SeedVR2Preprocess ->
VAEEncodeTiled (512/128/64/8) -> SeedVR2Conditioning -> KSampler (1 step, cfg 1, euler/simple, denoise 1)
-> VAEDecodeTiled -> SeedVR2PostProcessing -> CreateVideo (+ the take's own audio) -> SaveVideo.
--chunk N turns on the template's temporal split (SeedVR2TemporalChunk/Merge, manual N frames) when a
whole clip does not fit in memory.

Writes ~/AI_renders/comfyui/upscaled/<name>_<model>_x<scale>_*.mp4 and runs/<date>/upscale__<name>__<model>.json
(time, memory, input sha256, the API graph). Structure before polish: upscale only takes that are picked.
"""
import argparse
import asyncio
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import episode as E  # noqa: E402
from run_h3_t2v import MemorySampler, check_video, run as run_ws  # noqa: E402

MODELS = {"3b": "seedvr2_3b_int8_convrot.safetensors", "7b_sharp": "seedvr2_7b_sharp_int8_convrot.safetensors"}
VAE = "seedvr2_ema_vae_fp16.safetensors"
TILES = {"tile_size": 512, "overlap": 128, "temporal_size": 64, "temporal_overlap": 8}  # template values


def graph(video_name, model, scale, seed, color, chunk=None, prefix="upscaled/x", fps=24):
    g = {
        "load": {"class_type": "LoadVideo", "inputs": {"file": video_name}},
        "parts": {"class_type": "GetVideoComponents", "inputs": {"video": ["load", 0]}},
        "resize": {"class_type": "ResizeImageMaskNode", "inputs": {
            "input": ["parts", 0], "resize_type": "scale by multiplier", "resize_type.multiplier": scale,
            "scale_method": "lanczos"}},
        "pre": {"class_type": "SeedVR2Preprocess", "inputs": {"resized_images": ["resize", 0]}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": MODELS[model], "weight_dtype": "default"}},
        "enc": {"class_type": "VAEEncodeTiled", "inputs": dict(TILES, pixels=["pre", 0], vae=["vae", 0])},
    }
    latent = ["enc", 0]
    if chunk:
        g["split"] = {"class_type": "SeedVR2TemporalChunk", "inputs": {
            "latent": latent, "temporal_overlap": 0, "chunking_mode": "manual", "chunking_mode.frames_per_chunk": chunk}}
        latent = ["split", 0]
    g["cond"] = {"class_type": "SeedVR2Conditioning", "inputs": {"model": ["unet", 0], "vae_conditioning": latent}}
    g["ks"] = {"class_type": "KSampler", "inputs": {
        "model": ["unet", 0], "positive": ["cond", 0], "negative": ["cond", 1], "latent_image": latent,
        "seed": seed, "steps": 1, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}}
    out = ["ks", 0]
    if chunk:
        g["merge"] = {"class_type": "SeedVR2TemporalMerge", "inputs": {"latents": out, "temporal_overlap": ["split", 1]}}
        out = ["merge", 0]
    g["dec"] = {"class_type": "VAEDecodeTiled", "inputs": dict(TILES, samples=out, vae=["vae", 0])}
    g["post"] = {"class_type": "SeedVR2PostProcessing", "inputs": {
        "images": ["dec", 0], "original_resized_images": ["resize", 0], "color_correction_method": color}}
    g["video"] = {"class_type": "CreateVideo", "inputs": {"images": ["post", 0], "fps": float(fps), "audio": ["parts", 1]}}
    g["save"] = {"class_type": "SaveVideo", "inputs": {"video": ["video", 0], "filename_prefix": prefix,
                                                      "format": "auto", "format.codec": "auto"}}
    return g


def upscale(src, name, model="7b_sharp", scale=2.0, seed=1, color="lab", chunk=None, meta=None):
    src = pathlib.Path(src)
    sha = E.sha256(src)
    uploaded = asyncio.run(E._upload(src, f"{E.UPLOAD_SUBFOLDER}_{sha[:16]}{src.suffix.lower()}", audio=True))
    tag = f"{name}_{model}_x{scale:g}" + (f"_c{chunk}" if chunk else "")
    g = graph(uploaded, model, scale, seed, color, chunk, prefix=f"upscaled/{tag}")
    labels = {k: v["class_type"] for k, v in g.items()}
    mem = MemorySampler(); mem.start()
    started = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    prompt_id, wall, times, events, error, hist = asyncio.run(run_ws(g, labels))
    mem.stop.set(); mem.join()
    outs = [E.RENDERS / v.get("subfolder", "") / v["filename"]
            for o in (hist or {}).get("outputs", {}).values() for v in (o.get("images", []) + o.get("videos", []))]
    rec = {"tool": "seedvr2_upscale", "name": name, "model": MODELS[model], "vae": VAE, "scale": scale, "seed": seed,
           "color_correction": color, "chunk": chunk, "started": started, "status": "error" if error else "success",
           "error": error and {k: error.get(k) for k in ("node_type", "exception_type", "exception_message")},
           "input": {"file": str(src), "sha256": sha}, "wall_seconds": wall,
           "node_seconds": {labels.get(k, k): v for k, v in times.items()},
           "memory_gib": {"system_used_before": round(mem.base_used, 1), "system_used_peak": round(mem.peak_used, 1),
                          "swap_peak": round(mem.peak_swap, 2)},
           "outputs": [dict(check_video(p), sha256=E.sha256(p)) for p in outs if p.exists()],
           "comfyui_argv": E.api_get("/system_stats")["system"].get("argv"),
           "meta": meta or {}, "api_prompt": g}
    path = E.REPO / "runs" / dt.date.today().isoformat() / f"upscale__{tag}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, default=str))
    print(json.dumps({k: rec[k] for k in ("name", "model", "status", "error", "wall_seconds", "memory_gib")}), flush=True)
    print("record:", path.relative_to(E.REPO), [o.get("file") for o in rec["outputs"]], flush=True)
    return rec


def upscale_cut(cut_path, seed=1, color="lab"):
    """Optional step before assembly: SeedVR2 for the picked takes a cut asks for (`upscale: 7b_sharp`)."""
    import assemble as AS  # noqa: E402
    cut = E.load_yaml(pathlib.Path(cut_path))
    ep = E.Episode(E.REPO / "episodes" / cut["episode"])
    for entry in cut["sequence"]:
        model, sid = entry.get("upscale"), entry["shot"]
        if not model:
            continue
        take = entry.get("take") or ep.selected_take(sid)
        rec = ep.take_record(sid, take)
        try:
            print(f"{sid}: {model} upscale exists: {AS.upscaled_file(E.sha256(rec['output']['file']), model, sid)}")
        except SystemExit:
            upscale(rec["output"]["file"], f"{ep.name}_{sid}_{take}", model, 2.0, seed, color, None,
                    {"episode": ep.name, "shot": sid, "take": take, "cut": str(cut_path)})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode", nargs="?")
    ap.add_argument("shot", nargs="?")
    ap.add_argument("--video")
    ap.add_argument("--name")
    ap.add_argument("--model", choices=sorted(MODELS), default="7b_sharp",
                    help="7b_sharp (default: cleaner than 3b, which adds sparkle in foliage; similar time)")
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--color", choices=["none", "lab", "wavelet", "adain"], default="lab",
                    help="lab (default here; the template uses none, which warmed the picture and raised contrast)")
    ap.add_argument("--chunk", type=int, help="frames per temporal chunk (4n+1), when a clip does not fit")
    ap.add_argument("--cut", help="upscale every shot of this cut.yaml that sets `upscale: <model>` and has no "
                                  "upscale of its picked take yet")
    a = ap.parse_args()
    if a.cut:
        return upscale_cut(a.cut, a.seed, a.color)
    if a.video:
        src, name, meta = a.video, a.name or pathlib.Path(a.video).stem, {}
    else:
        ep = E.Episode(a.episode)
        take = ep.selected_take(a.shot)
        rec = take and ep.take_record(a.shot, take)
        if not rec or "output" not in rec:
            raise SystemExit(f"{a.shot}: no picked take with a video")
        src, name = rec["output"]["file"], a.name or f"{ep.name}_{a.shot}_{take}"
        meta = {"episode": ep.name, "shot": a.shot, "take": take}
    upscale(src, name, a.model, a.scale, a.seed, a.color, a.chunk, meta)


if __name__ == "__main__":
    main()
