"""Read-only: compare two rendered videos frame-by-frame and sample-by-sample.

Usage: ~/dev/ComfyUI/.venv/bin/python scripts/compare_outputs.py A.mp4 B.mp4

Compares decoded pixels and decoded audio (not file bytes: containers may embed timestamps or
metadata that differ even when the content is identical).
"""
import json
import sys

import av
import numpy as np


def load(path):
    with av.open(path) as c:
        frames = np.stack([f.to_ndarray(format="rgb24") for f in c.decode(video=0)]).astype(np.int16)
    with av.open(path) as c:
        audio = (np.concatenate([f.to_ndarray().reshape(-1) for f in c.decode(audio=0)]).astype(np.float64)
                 if c.streams.audio else np.zeros(0))
    return frames, audio


a_frames, a_audio = load(sys.argv[1])
b_frames, b_audio = load(sys.argv[2])
out = {"video_shapes": [list(a_frames.shape), list(b_frames.shape)], "audio_samples": [a_audio.size, b_audio.size]}
if a_frames.shape == b_frames.shape:
    d = np.abs(a_frames - b_frames)
    out.update(video_identical=bool((d == 0).all()), video_max_diff=int(d.max()), video_mean_diff=round(float(d.mean()), 4),
               video_pct_pixels_changed=round(100 * float((d.max(axis=-1) > 0).mean()), 3))
if a_audio.size == b_audio.size and a_audio.size:
    d = np.abs(a_audio - b_audio)
    out.update(audio_identical=bool((d == 0).all()), audio_max_diff=float(d.max()))
print(json.dumps(out, indent=1))
