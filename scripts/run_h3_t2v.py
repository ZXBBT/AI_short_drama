"""Run one MiniMax H3 text-to-video render through the local ComfyUI API and record everything.

Defaults come from the official template copy in workflows/official/. Only the values passed
on the command line (and the MPS-required fp16 video VAE, decision D5) differ from it.
The template's turbo switch / frame-count math nodes are replaced by their resolved values
(turbo off -> UNET goes straight to the scheduler and guider), which is graph-equivalent.

Run with ComfyUI already started via scripts/launch_comfyui.sh:
    ~/dev/ComfyUI/.venv/bin/python scripts/run_h3_t2v.py --name stage4_a --width 608 --height 352 --length 5

Writes runs/<date>/<name>.json (params, API prompt, timings, memory, output checks).
"""
import argparse
import asyncio
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import threading
import time
import uuid

import aiohttp
import av
import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "workflows/official/video_minimax_h3_t2v__templates-0.11.89.json"
API = "127.0.0.1:8188"
MPS_VIDEO_VAE = "minimax_h3_video_vae_fp16.safetensors"  # decision D5


def template_defaults():
    wf = json.loads(TEMPLATE.read_text())
    outer = next(n for n in wf["nodes"] if n["id"] == 140)["widgets_values"]
    inner = {n["id"]: n.get("widgets_values") for n in wf["definitions"]["subgraphs"][0]["nodes"]}
    return {
        "prompt": outer[0], "seed": outer[4], "unet": outer[5], "clip": outer[6],
        "video_vae": outer[7], "audio_vae": outer[8],
        "sampler": inner[123][0], "scheduler": inner[124][0], "steps": inner[137][0],
        "fps": inner[130][0], "bit_depth": inner[130][1],
    }


def build_prompt(p):
    return {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": p["unet"], "weight_dtype": "default"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": p["clip"], "type": "minimax", "device": "default"}},
        "vae_v": {"class_type": "VAELoader", "inputs": {"vae_name": p["video_vae"]}},
        "vae_a": {"class_type": "VAELoader", "inputs": {"vae_name": p["audio_vae"]}},
        "cond": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {
            "clip": ["clip", 0], "vae": ["vae_v", 0], "prompt": p["prompt"],
            "width": p["width"], "height": p["height"], "length": p["length"]}},
        "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": p["seed"]}},
        "sampler": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": p["sampler"]}},
        "sigmas": {"class_type": "BasicScheduler", "inputs": {
            "model": ["unet", 0], "scheduler": p["scheduler"], "steps": p["steps"], "denoise": 1.0}},
        "guider": {"class_type": "BasicGuider", "inputs": {"model": ["unet", 0], "conditioning": ["cond", 0]}},
        "sample": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["noise", 0], "guider": ["guider", 0], "sampler": ["sampler", 0],
            "sigmas": ["sigmas", 0], "latent_image": ["cond", 1]}},
        "decode_v": {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae_v", 0]}},
        "decode_a": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["sample", 0], "vae": ["vae_a", 0]}},
        "video": {"class_type": "CreateVideo", "inputs": {
            "images": ["decode_v", 0], "audio": ["decode_a", 0], "fps": p["fps"], "bit_depth": p["bit_depth"]}},
        "save": {"class_type": "SaveVideo", "inputs": {
            "video": ["video", 0], "filename_prefix": p["prefix"], "format": "auto", "format.codec": "auto"}},
    }


class MemorySampler(threading.Thread):
    """System-wide memory (unified: CPU + GPU) and swap, sampled once per second."""

    def __init__(self):
        super().__init__(daemon=True)
        self.peak_used = self.peak_swap = 0.0
        self.base_used = self._used()
        self.stop = threading.Event()

    @staticmethod
    def _used():
        out = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
        page = int(out.split("page size of ")[1].split()[0])
        get = lambda k: int(next(l for l in out.splitlines() if l.startswith(k)).split()[-1].rstrip("."))  # noqa: E731
        return (get("Pages active") + get("Pages wired down") + get("Pages occupied by compressor")) * page / 2**30

    @staticmethod
    def _swap():
        s = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True).stdout
        v = s.split("used = ")[1].split()[0]
        return float(v[:-1]) / (1024 if v.endswith("M") else 1)

    def run(self):
        while not self.stop.is_set():
            self.peak_used = max(self.peak_used, self._used())
            self.peak_swap = max(self.peak_swap, self._swap())
            time.sleep(1)


async def run(prompt, labels):
    client_id = str(uuid.uuid4())
    times, events, error = {}, [], None
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect(f"ws://{API}/ws?clientId={client_id}", max_msg_size=0) as ws:
            async with s.post(f"http://{API}/prompt", json={"prompt": prompt, "client_id": client_id}) as r:
                resp = await r.json()
                if "prompt_id" not in resp:
                    raise SystemExit(f"prompt rejected: {json.dumps(resp, indent=1)}")
                prompt_id = resp["prompt_id"]
            t0 = time.time(); current = None
            async for msg in ws:
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue
                m = json.loads(msg.data); d = m.get("data", {})
                if d.get("prompt_id") not in (None, prompt_id):
                    continue
                now = time.time() - t0
                if m["type"] == "executing":
                    if current:
                        times[current] = round(now - times[current], 1)
                    current = d.get("node")
                    if current:
                        times[current] = now
                        print(f"[{now:7.1f}s] {labels.get(current, current)}", flush=True)
                    else:
                        break
                elif m["type"] == "progress" and d.get("value") in (1, d.get("max")):
                    print(f"[{now:7.1f}s]   step {d['value']}/{d['max']}", flush=True)
                elif m["type"] in ("execution_error", "execution_interrupted"):
                    error = d; events.append(m["type"])
                    break
                elif m["type"] in ("execution_start", "execution_success", "execution_cached"):
                    events.append(m["type"])
            wall = round(time.time() - t0, 1)
        async with s.get(f"http://{API}/history/{prompt_id}") as r:
            hist = (await r.json()).get(prompt_id, {})
    return prompt_id, wall, times, events, error, hist


def check_video(path):
    out = {"file": str(path), "bytes": path.stat().st_size}
    with av.open(str(path)) as c:
        vs = c.streams.video[0]
        frames = [f.to_ndarray(format="rgb24") for f in c.decode(video=0)]
        out["video"] = {"frames": len(frames), "width": vs.width, "height": vs.height,
                        "fps": float(vs.average_rate) if vs.average_rate else None, "codec": vs.codec_context.name}
        means = [float(f.mean()) for f in frames]; stds = [float(f.std()) for f in frames]
        out["video"].update({"mean_min": round(min(means), 1), "mean_max": round(max(means), 1),
                             "std_min": round(min(stds), 1), "black_frames": sum(m < 8 and s < 4 for m, s in zip(means, stds))})
    with av.open(str(path)) as c:
        if c.streams.audio:
            a = np.concatenate([f.to_ndarray().astype(np.float64).reshape(-1) for f in c.decode(audio=0)])
            out["audio"] = {"samples": int(a.size), "sample_rate": c.streams.audio[0].rate,
                            "finite": bool(np.isfinite(a).all()), "rms": float(np.sqrt(np.mean(a ** 2))),
                            "peak": float(np.abs(a).max())}
        else:
            out["audio"] = None
    return out


def main():
    d = template_defaults()
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--width", type=int, default=608)
    ap.add_argument("--height", type=int, default=352)
    ap.add_argument("--length", type=int, default=5, help="frames; must be 17k+5")
    ap.add_argument("--steps", type=int, default=d["steps"])
    ap.add_argument("--seed", type=int, default=d["seed"])
    ap.add_argument("--prompt-file", type=pathlib.Path, help="default: template prompt")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.length % 17 != 5 or a.width % 32 or a.height % 32:
        raise SystemExit("length must be 17k+5, width/height multiples of 32")

    p = dict(d, width=a.width, height=a.height, length=a.length, steps=a.steps, seed=a.seed,
             video_vae=MPS_VIDEO_VAE, prefix=f"h3/{a.name}")
    if a.prompt_file:
        p["prompt"] = a.prompt_file.read_text().strip()
    prompt = build_prompt(p)
    deviations = {"video_vae": [d["video_vae"], MPS_VIDEO_VAE]}
    deviations.update({k: [d.get(k), p[k]] for k in ("steps", "seed", "prompt") if p[k] != d.get(k)})
    if a.dry_run:
        print(json.dumps(prompt, indent=1)); return

    labels = {k: v["class_type"] for k, v in prompt.items()}
    mem = MemorySampler(); mem.start()
    started = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    prompt_id, wall, times, events, error, hist = asyncio.run(run(prompt, labels))
    mem.stop.set(); mem.join()

    import urllib.request
    stats = json.load(urllib.request.urlopen(f"http://{API}/system_stats"))
    record = {
        "name": a.name, "started": started, "prompt_id": prompt_id, "status": "error" if error else "success",
        "error": error and {k: error.get(k) for k in ("node_type", "exception_type", "exception_message")},
        "events": events, "wall_seconds": wall,
        "node_seconds": {labels.get(k, k): v for k, v in times.items()},
        "memory_gib": {"system_used_before": round(mem.base_used, 1), "system_used_peak": round(mem.peak_used, 1),
                       "swap_peak": round(mem.peak_swap, 2)},
        "params": {k: p[k] for k in ("width", "height", "length", "fps", "steps", "seed", "sampler", "scheduler")},
        "duration_seconds": round(p["length"] / p["fps"], 2),
        "models": {k: p[k] for k in ("unet", "clip", "video_vae", "audio_vae")},
        "prompt_text": p["prompt"],
        "template": {"file": str(TEMPLATE.relative_to(REPO)),
                     "sha256": hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()},
        "deviations_from_template": deviations,
        "env": {"comfyui": stats["system"]["comfyui_version"], "pytorch": stats["system"].get("pytorch_version"),
                "python": stats["system"].get("python_version", "").split()[0],
                "device": [x.get("type") for x in stats.get("devices", [])],
                "repo_commit": subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                                              capture_output=True, text=True).stdout.strip()},
        "api_prompt": prompt,
    }
    if not error:
        vids = [v for o in hist.get("outputs", {}).values() for v in (o.get("images", []) + o.get("videos", []))]
        if vids:
            v = vids[0]
            path = pathlib.Path.home() / "AI_renders/comfyui" / v.get("subfolder", "") / v["filename"]
            record["output"] = check_video(path)
    out = REPO / "runs" / dt.date.today().isoformat() / f"{a.name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1))
    print(json.dumps({k: record[k] for k in ("status", "error", "wall_seconds", "node_seconds", "memory_gib")}, indent=1))
    if "output" in record:
        print(json.dumps(record["output"], indent=1))
    print("record:", out.relative_to(REPO))


if __name__ == "__main__":
    main()
