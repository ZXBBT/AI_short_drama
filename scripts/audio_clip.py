"""Cut a piece of a take's soundtrack into a WAV file (48 kHz stereo), for use as an audio asset:
the end of a music piece to continue (`audio_anchor`) or a narrator line as voice reference (`audio_refs`).

    PY=~/dev/ComfyUI/.venv/bin/python
    $PY scripts/audio_clip.py <take.mp4> <out.wav> [--from 11.0] [--to 15.0]

Writes <out.wav> and <out.wav>.json (source file + sha256 + times), so every asset is traceable.
"""
import argparse
import json
import pathlib
import sys

import av
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import assemble as A  # noqa: E402
import episode as E  # noqa: E402


def write_wav(path, audio):
    """(2, N) float array at 48 kHz -> 16-bit PCM WAV."""
    c = av.open(str(path), "w", format="wav")
    s = c.add_stream("pcm_s16le", rate=A.SR, layout="stereo")
    x = np.clip(audio, -1, 1).astype(np.float32)
    for i in range(0, x.shape[1], 4800):
        f = av.AudioFrame.from_ndarray(np.ascontiguousarray(x[:, i:i + 4800]), format="fltp", layout="stereo")
        f.sample_rate, f.pts = A.SR, i
        for p in s.encode(f):
            c.mux(p)
    for p in s.encode():
        c.mux(p)
    c.close()


def clip(src, out, t0=0.0, t1=None):
    audio = A.take_audio(src)
    a, b = int(t0 * A.SR), audio.shape[1] if t1 is None else int(t1 * A.SR)
    out = pathlib.Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    write_wav(out, audio[:, a:b])
    info = {"source": str(src), "source_sha256": E.sha256(src), "from_s": t0, "to_s": b / A.SR,
            "wav_sha256": E.sha256(out)}
    out.with_suffix(out.suffix + ".json").write_text(json.dumps(info, indent=1))
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source"); ap.add_argument("out")
    ap.add_argument("--from", dest="t0", type=float, default=0.0); ap.add_argument("--to", dest="t1", type=float)
    a = ap.parse_args()
    print(json.dumps(clip(a.source, a.out, a.t0, a.t1)))


if __name__ == "__main__":
    main()
