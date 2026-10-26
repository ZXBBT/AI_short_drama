"""Assemble an episode from its cut list: selected takes, trims, audio joins, loudness, subtitles.

    PY=~/dev/ComfyUI/.venv/bin/python
    $PY scripts/assemble.py episodes/midnight_call/cut.yaml [--dry-run]

Uses only PyAV (bundled FFmpeg libraries); no ComfyUI, no new software. Writes
  ~/AI_renders/comfyui/episodes/<ep>/_final/<ep>_<version>_<size>.mp4 (+ .srt next to each),
  subtitles/<ep>_<version>.srt (in Git) and runs/<date>/<ep>__cut_<version>.json (manifest).
Video is re-encoded once (H.264 CRF 18); audio is resampled to 48 kHz, faded at every cut,
levelled as a whole to the target loudness (never compressed; limited only with `loudness.limiter: true`,
which lets a cut reach the target when a few peaks would hit the ceiling), AAC 192 kb/s.

V2 (2026-10-25, revision brief sections 7-9 and 15): a cut can build its soundtrack in layers.
Sequence entries may set `audio: off` (picture only) or `video_file:` (a composited or SeedVR2-upscaled
version of the take: same frame count and aspect, any size; smaller shots are scaled up to match) or
`upscale: 7b_sharp` (use the SeedVR2 upscale of this exact take, found by its sha256; scripts/upscale.py) or
`mirror: true` (flip the picture left-right, e.g. to match a look direction across
a cut; the face is mirrored too, so check identity by eye; the sound is left as rendered).
Top-level `layers:` add music / voice / ambience beds / effects on the timeline:
  - {role: music, source: <file or {episode, shot}>, at: 0, src_in: 0, length: 15, gain_db: -20,
     fade_in: 0.5, fade_out: 1.0, loop_xfade: 1.0}
`at` / `until` are seconds or {shot: S3A, offset: -0.8} (relative to that shot's start in this cut);
`until` sets the length; a source shorter than the length is looped with a crossfade; `target_lufs`
levels a layer by measurement (instead of gain_db). `loudness.sync_target_lufs` sets every take's own
sound to one level so it sits under the music and voice layers. A voice layer with
`text` also becomes a subtitle. `duck: {db: -6, ramp_ms: 250}` lowers music and beds while a voice
layer plays.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess
import sys

import av
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import episode as E  # noqa: E402

REPO = E.REPO
SR = 48000
FPS = 24
SPF = SR // FPS  # audio samples per video frame (2000)
MAX_AUTO_BOOST_DB = 12.0  # target levelling never boosts more: a near-silent source would turn into hiss (V2 home bed)


# ---------- loudness (FFmpeg's ebur128 filter = ITU-R BS.1770 / EBU R128) ----------

def measure(audio):
    """Integrated loudness (LUFS) and true peak (dBTP) of a (2, N) float array at 48 kHz."""
    g = av.filter.Graph()
    src = g.add_abuffer(format="fltp", sample_rate=SR, layout="stereo", time_base=f"1/{SR}")
    eb = g.add("ebur128", "metadata=1:peak=true")
    sink = g.add("abuffersink")
    src.link_to(eb); eb.link_to(sink); g.configure()
    md = {}

    def drain():
        while True:
            try:
                f = g.pull()
            except (av.BlockingIOError, av.EOFError):
                return
            if "lavfi.r128.I" in f.metadata:
                md.update(f.metadata)
    for i in range(0, audio.shape[1], 4800):
        fr = av.AudioFrame.from_ndarray(np.ascontiguousarray(audio[:, i:i + 4800], dtype=np.float32),
                                        format="fltp", layout="stereo")
        fr.sample_rate, fr.pts = SR, i
        g.push(fr); drain()
    g.push(None); drain()
    peaks = [float(v) for k, v in md.items() if k.startswith("lavfi.r128.true_peaks_ch")]
    tp_lin = max(peaks) if peaks else float(np.abs(audio).max())
    return float(md["lavfi.r128.I"]), 20 * np.log10(max(tp_lin, 1e-9))


# ---------- sources ----------

def load_entry(ep, entry):
    sid = entry["shot"]
    if sid not in ep.shots:
        raise SystemExit(f"cut: shot {sid} not in episode")
    take = entry.get("take") or ep.selected_take(sid)
    if not take:
        raise SystemExit(f"cut: {sid} has no selected take")
    rec = ep.take_record(sid, take)
    if not rec or "output" not in rec:
        raise SystemExit(f"cut: no successful record for {sid} {take}")
    path = pathlib.Path(rec["output"]["file"])
    sha = E.sha256(path)
    if rec["output"].get("sha256") and sha != rec["output"]["sha256"]:
        raise SystemExit(f"cut: {path} changed since it was rendered (sha256 mismatch)")
    with av.open(str(path)) as c:
        frames = [f for f in c.decode(video=0)]
    n = len(frames)
    a, b = int(entry.get("in", 0)), int(entry.get("out", n - 1))
    if not 0 <= a <= b < n:
        raise SystemExit(f"cut: {sid} in/out {a}/{b} outside 0..{n - 1}")
    if entry.get("upscale") and not entry.get("video_file"):  # SeedVR2 version of exactly this take
        entry = dict(entry, video_file=upscaled_file(sha, entry["upscale"], sid))
    if entry.get("video_file"):  # e.g. the take with a composited phone screen (screen_insert.py)
        vf = resolve_source_path(entry["video_file"])
        with av.open(str(vf)) as c:
            vframes = [f for f in c.decode(video=0)]
        if len(vframes) != n:  # same frames; the size may differ (an upscaled take, scripts/upscale.py)
            raise SystemExit(f"cut: {sid} video_file has {len(vframes)} frames, the take has {n}")
        frames = vframes
    if entry.get("mirror"):
        frames = mirror_frames(frames)
    audio = take_audio(path)
    if entry.get("audio", "sync") in ("off", False):  # YAML reads a bare `off` as false
        audio = np.zeros_like(audio)
    want = n * SPF
    audio_len_diff = audio.shape[1] - want
    audio = np.pad(audio, ((0, 0), (0, max(0, -audio_len_diff))))[:, :want]  # exactly n frames long
    seg = audio[:, a * SPF:(b + 1) * SPF] * 10 ** (float(entry.get("gain_db", 0)) / 20)
    st = E.shot_status(ep, sid)
    return {"shot": sid, "take": take, "file": str(path), "sha256": sha, "frames_in_take": n,
            "in": a, "out": b, "frames": b - a + 1, "video": frames[a:b + 1], "audio": seg,
            "audio_len_diff_samples": int(audio_len_diff), "gain_db": float(entry.get("gain_db", 0)),
            "stale": st.get("fp") is not None and not take.startswith(st["fp"][:8]),
            "subs": entry.get("subs") or [], "video_file": entry.get("video_file"),
            "audio_mode": "off" if entry.get("audio", "sync") in ("off", False) else "sync",
            "mirror": bool(entry.get("mirror")), "upscale": entry.get("upscale")}


def upscaled_file(take_sha, model, sid=""):
    """Newest successful scripts/upscale.py output for the take with this sha256 and model (3b | 7b_sharp)."""
    for rec_path in sorted((REPO / "runs").glob("*/upscale__*.json"), key=lambda q: q.stat().st_mtime, reverse=True):
        r = json.loads(rec_path.read_text())
        if (r.get("status") == "success" and r["input"]["sha256"] == take_sha and model in r["model"]
                and r.get("outputs") and pathlib.Path(r["outputs"][0]["file"]).exists()):
            return r["outputs"][0]["file"]
    raise SystemExit(f"cut: {sid} has no {model} upscale of its take yet: "
                     f"scripts/upscale.py episodes/<ep> {sid} --model {model}")


def mirror_frames(frames):
    """Left-right flip of decoded frames."""
    return [av.VideoFrame.from_ndarray(np.ascontiguousarray(f.to_ndarray(format="rgb24")[:, ::-1]), format="rgb24")
            for f in frames]


LIMITER_MAX_DB = 6.0  # more peak reduction than this audibly squashes a shout or a door slam


def limit(audio, ceiling_dbtp, lookahead_ms=5.0, release_ms=150.0, margin_db=0.5, _tries=3):
    """Look-ahead peak limiter (Stage 8, optional via `loudness.limiter: true`): the gain falls before a
    peak (look-ahead window) and recovers smoothly (release), so only the loudest moments are turned down;
    everything under the ceiling is untouched. Returns (audio, largest reduction in dB). The margin keeps
    the true peak (between samples) under the ceiling; if it still overshoots, the margin is widened."""
    c = 10 ** ((ceiling_dbtp - margin_db) / 20)
    peak = np.abs(audio).max(axis=0)
    need = np.minimum(1.0, c / np.maximum(peak, 1e-9))
    w = max(1, int(SR * lookahead_ms / 1000))
    padded = np.concatenate([need, np.ones(w)])
    ahead = np.lib.stride_tricks.sliding_window_view(padded, w + 1).min(axis=1)[:need.size]
    rel = 1 - np.exp(-1 / (SR * release_ms / 1000))
    g = np.empty_like(ahead)
    prev = 1.0
    for i, v in enumerate(ahead):  # instant attack (already ahead of the peak), smooth release
        prev = v if v < prev else prev + (min(1.0, v) - prev) * rel
        g[i] = prev
    # soften the attack: a trailing average over the look-ahead window still sits under every peak's need
    g = np.convolve(np.concatenate([np.full(w - 1, g[0]), g]), np.ones(w) / w, mode="valid")
    out = audio * g
    tp = measure(out)[1]
    if tp > ceiling_dbtp:  # overshoot between samples: limit again with a wider margin, trim only as last resort
        if _tries > 1:
            return limit(audio, ceiling_dbtp, lookahead_ms, release_ms, margin_db + tp - ceiling_dbtp + 0.1, _tries - 1)
        out *= 10 ** ((ceiling_dbtp - tp) / 20)
    return out, float(-20 * np.log10(max(g.min(), 1e-9)))


# ---------- layered soundtrack (V2) ----------

def resolve_source_path(src):
    """A layer/video source: a path (absolute, repo-relative or under ~/AI_renders/comfyui) or
    {episode, shot[, take]} = that shot's selected (or given) take."""
    if isinstance(src, dict):
        other = E.Episode(REPO / "episodes" / src["episode"])
        take = src.get("take") or other.selected_take(src["shot"])
        rec = take and other.take_record(src["shot"], take)
        if not rec:
            raise SystemExit(f"cut: no picked/successful take for {src}")
        return pathlib.Path(rec["output"]["file"])
    p = pathlib.Path(str(src)).expanduser()
    for cand in (p, REPO / p, E.RENDERS / p):
        if cand.exists():
            return cand
    raise SystemExit(f"cut: source not found: {src}")


def timeline_time(v, starts):
    if isinstance(v, dict):
        if v["shot"] not in starts:
            raise SystemExit(f"cut: layer refers to shot {v['shot']} which is not in the sequence")
        return starts[v["shot"]] + float(v.get("offset", 0))
    return float(v)


def ramp(n, kind="in"):
    r = np.linspace(0.0, 1.0, max(n, 1))
    return r if kind == "in" else r[::-1]


def layer_audio(layer, starts, total_s):
    """(start_sample, (2, N) array) for one layer, with gain, fades and looping applied."""
    src = take_audio(resolve_source_path(layer["source"]))
    a = int(round(float(layer.get("src_in", 0)) * SR))
    b = int(round(float(layer["src_out"]) * SR)) if "src_out" in layer else src.shape[1]
    src = src[:, a:b]
    at = timeline_time(layer.get("at", 0), starts)
    if "until" in layer:
        length = timeline_time(layer["until"], starts) - at
    else:
        length = float(layer.get("length", src.shape[1] / SR))
    n = int(round(length * SR))
    if n <= 0:
        raise SystemExit(f"cut: layer {layer.get('name', layer['source'])} has no length")
    x = int(round(float(layer.get("loop_xfade", 1.0)) * SR))
    out = src.copy()
    while out.shape[1] < n:  # loop beds with a crossfade so the join is inaudible
        if src.shape[1] <= 2 * x:
            raise SystemExit(f"cut: layer source too short to loop: {layer['source']}")
        k = x
        out = np.concatenate([out[:, :-k], out[:, -k:] * ramp(k, "out") + src[:, :k] * ramp(k, "in"),
                              src[:, k:]], axis=1)
    gain_db = float(layer.get("gain_db", 0))
    if "target_lufs" in layer:  # level the layer by measurement instead of a guessed gain
        gain_db += min(MAX_AUTO_BOOST_DB, float(layer["target_lufs"]) - measure(out[:, :n])[0])
    layer["_gain_db"] = round(gain_db, 1)
    out = out[:, :n] * 10 ** (gain_db / 20)
    fi, fo = int(float(layer.get("fade_in", 0)) * SR), int(float(layer.get("fade_out", 0)) * SR)
    if fi:
        out[:, :fi] *= ramp(min(fi, n), "in")[:fi]
    if fo:
        out[:, -fo:] *= ramp(min(fo, n), "out")[-fo:]
    return int(round(at * SR)), out


def mix_layers(mix, layers, starts, duck=None):
    """Add layers to the sequence's sync sound; music and beds duck under voice layers."""
    total = mix.shape[1]
    placed = []
    for ly in layers or []:
        st, arr = layer_audio(ly, starts, total / SR)
        placed.append((ly, st, arr))
    gain = {}
    if duck:
        env = np.zeros(total)
        for ly, st, arr in placed:
            if ly.get("role") == "voice":
                env[max(0, st):max(0, min(total, st + arr.shape[1]))] = 1.0
        r = max(1, int(SR * float(duck.get("ramp_ms", 250)) / 1000))
        env = np.convolve(env, np.ones(r) / r, mode="same")  # smooth ramps around each line
        gain = 10 ** (float(duck.get("db", -6)) * env / 20)
    rows = []
    for ly, st, arr in placed:
        a, b = max(0, st), min(total, st + arr.shape[1])
        if b <= a:
            continue
        seg = arr[:, a - st:b - st]
        if duck and ly.get("role") in ("music", "bed"):
            seg = seg * gain[a:b]
        mix[:, a:b] += seg
        rows.append({"name": ly.get("name"), "role": ly.get("role"), "source": str(ly["source"]),
                     "start_s": round(a / SR, 3), "end_s": round(b / SR, 3), "gain_db": ly.get("_gain_db", 0.0)})
    return mix, rows


def auto_gains(per_shot_lufs, explicit, window_lu=6.0, max_db=10.0):
    """Per-shot gains that pull outliers to within +-window_lu of the median shot loudness.

    Shots with an explicit gain_db, and near-silent shots (< -60 LUFS), are left alone. Keeps the
    order of loudness (a crash stays louder than breathing) but narrows the extremes.
    """
    vals = sorted(v for s, v in per_shot_lufs.items() if s not in explicit and v > -60)
    if not vals:
        return {}
    med = vals[len(vals) // 2] if len(vals) % 2 else (vals[len(vals) // 2 - 1] + vals[len(vals) // 2]) / 2
    out = {}
    for s, v in per_shot_lufs.items():
        if s in explicit or v <= -60:
            continue
        g = (med + window_lu - v) if v > med + window_lu else (med - window_lu - v) if v < med - window_lu else 0.0
        out[s] = round(max(-max_db, min(max_db, g)), 1)
    return out


DEFAULT_CUT = """# Edit decision list (created by assemble.py --init; edit freely). Assemble with:
#   ~/dev/ComfyUI/.venv/bin/python scripts/assemble.py episodes/{ep}/cut.yaml
# in/out = first/last frame used (inclusive); gain_db = per-shot audio adjustment;
# subs = subtitles, times in seconds from the start of the take.
episode: {ep}
version: v1
loudness:
  target_lufs: -14.0
  ceiling_dbtp: -1.0
  per_shot: auto         # auto = narrow shot-to-shot jumps to +-6 LU of the median shot; off = as rendered
audio_fade_ms: 10
sizes:
  - native
  - 720x1280

sequence:
{seq}"""


def init_cut(ep_dir):
    ep = E.Episode(ep_dir)
    path = ep.dir / "cut.yaml"
    if path.exists():
        raise SystemExit(f"{path} exists; not overwriting")
    path.write_text(DEFAULT_CUT.format(ep=ep.name, seq="".join(f"  - shot: {s}\n" for s in ep.shots)))
    print(f"wrote {path} with {len(ep.shots)} shots in file order")


def take_audio(path):
    """A take's audio as a (2, N) float array at 48 kHz."""
    with av.open(str(path)) as c:
        rs = av.AudioResampler(format="fltp", layout="stereo", rate=SR)
        chunks = [x.to_ndarray() for f in c.decode(audio=0) for x in rs.resample(f)]
        chunks += [x.to_ndarray() for x in rs.resample(None)]
    return np.concatenate(chunks, axis=1).astype(np.float64)


def speech_segments(audio, win_s=0.05, min_s=0.2, gap_s=0.2):
    """Voiced stretches [(start_s, end_s, strength)]: speech-band (300-3400 Hz) energy within 25 dB of the
    clip's loudest moment and tonal (low spectral flatness). Found "Hello?" at 4.6-5.1 s in S002 (6.4)."""
    x = audio.mean(axis=0)
    w = int(SR * win_s)
    if x.size < w:
        return []
    fq = np.fft.rfftfreq(w, 1 / SR)
    band = (fq > 300) & (fq < 3400)
    hann = np.hanning(w)
    energy, flat = [], []
    for i in range(0, x.size - w + 1, w):
        spec = np.abs(np.fft.rfft(x[i:i + w] * hann)) ** 2
        b = spec[band] + 1e-12
        energy.append(10 * np.log10(b.sum()))
        flat.append(float(np.exp(np.mean(np.log(b))) / np.mean(b)))
    energy = np.array(energy)
    voiced = (energy > energy.max() - 25) & (np.array(flat) < 0.2)
    segs, start = [], None
    for k, v in enumerate(list(voiced) + [False]):
        if v and start is None:
            start = k
        elif not v and start is not None:
            segs.append([start, k]); start = None
    merged = []
    for s in segs:  # bridge short pauses inside a sentence
        if merged and (s[0] - merged[-1][1]) * win_s <= gap_s:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return [(a * win_s, b * win_s, float(energy[a:b].mean() + 10 * np.log10((b - a) * win_s)))
            for a, b in merged if (b - a) * win_s >= min_s]


def time_lines(audio, lines, start_s=0.0, min_len_s=0.8):
    """Place dialogue lines on the strongest voiced stretches, in time order. Returns [(start, end, text)]
    in take time, or the lines spread evenly over the take if no voice is found (both 'estimated')."""
    segs = speech_segments(audio)
    dur = audio.shape[1] / SR
    if len(segs) >= len(lines):
        chosen = sorted(sorted(segs, key=lambda s: -s[2])[:len(lines)])
        spans = [(a, max(b, a + min_len_s)) for a, b, _ in chosen]
    else:
        step = dur / max(1, len(lines))
        spans = [(k * step, (k + 1) * step) for k in range(len(lines))]
    return [(round(start_s + a, 2), round(min(start_s + b, start_s + dur), 2), txt) for (a, b), txt in zip(spans, lines)]


def hd_size(ep):
    """1080p in the episode's orientation: 9:16 -> 1080x1920, 16:9 -> 1920x1080, square -> 1080x1080."""
    w, h = E.ASPECTS[ep.params(next(iter(ep.shots)))["aspect"]]
    return "1080x1920" if w < h else "1920x1080" if w > h else "1080x1080"


def generate_cut(ep, version="v1"):
    """Stage 8.5: cut list from the picks: story (file) order, trims around unwanted H3 cuts,
    voice-timed subtitles from each shot's dialogue, auto levelling, native + 1080p in the episode's aspect."""
    out = ["# GENERATED by scripts/assemble.py (Stage 8.5). The pipeline regenerates it as a new version",
           "# when picks change. To edit by hand, set `generated: false` first (then it is never touched).",
           f"episode: {ep.name}", f"version: {version}", "generated: true",
           "generated_from:  # the picks this cut was built from (subtitle timing depends on them)",
           *[f"  {s}: {ep.selected_take(s)}" for s in ep.shots],
           "loudness: {target_lufs: -14.0, ceiling_dbtp: -1.0, per_shot: auto}", "audio_fade_ms: 10",
           f"sizes: [native, {hd_size(ep)}]", "", "sequence:"]
    for sid in ep.shots:
        take = ep.selected_take(sid)
        rec = take and ep.take_record(sid, take)
        if not rec:
            raise SystemExit(f"cannot generate the cut: {sid} has no picked take")
        p = ep.params(sid)
        n = rec["output"]["video"]["frames"]
        a, b, why = 0, n - 1, ""
        cuts = [c["frame"] for c in (rec.get("continuity") or {}).get("cuts", [])]
        if cuts and not p["allow_cuts"]:
            bounds = [0] + cuts + [n]
            a, b = max(((bounds[k], bounds[k + 1] - 1) for k in range(len(bounds) - 1)), key=lambda r: r[1] - r[0])
            why = f"  # H3 cut at frame(s) {cuts}: longest uncut part"
        out.append(f"  - shot: {sid}{why}")
        if a:
            out.append(f"    in: {a}")
        if b != n - 1:
            out.append(f"    out: {b}")
        lines = [d["line"] for d in ep.shots[sid].get("dialogue") or []]
        if lines:
            audio = take_audio(rec["output"]["file"])[:, a * SPF:(b + 1) * SPF]
            out.append("    subs:  # timing estimated from the voice: check by ear")
            for s, e, txt in time_lines(audio, lines, start_s=a / FPS):
                out.append(f"      - {{start: {s}, end: {e}, text: {json.dumps(txt, ensure_ascii=False)}}}")
    path = ep.dir / "cut.yaml"
    path.write_text("\n".join(out) + "\n")
    return path


def next_version(v):
    m = re.fullmatch(r"v(\d+)", str(v))
    return f"v{int(m.group(1)) + 1}" if m else f"{v}_2"


def fade(seg, ms):
    n = min(int(SR * ms / 1000), seg.shape[1] // 2)
    if n:
        ramp = np.linspace(0.0, 1.0, n)
        seg[:, :n] *= ramp
        seg[:, -n:] *= ramp[::-1]
    return seg


# ---------- encoding ----------

def base_size(frames):
    """Largest frame size in the cut; every size must share one aspect ratio (within 1 %)."""
    sizes = {(f.width, f.height) for f in frames}
    w, h = max(sizes, key=lambda s: s[0] * s[1])
    for sw, sh in sizes:
        if abs(sw / sh - w / h) > 0.01 * (w / h):
            raise SystemExit(f"cut: frame sizes {sorted(sizes)} have different aspect ratios")
    return w, h


def cover_size(w0, h0, w, h):
    """Smallest even size with the source's aspect that covers w x h (the excess is centre-cropped).
    352x608 -> 1080x1920: 1112x1920 (trim the sides); 480x864 -> 1080x1920: 1080x1944 (trim top/bottom)."""
    s = max(w / w0, h / h0)
    sw, sh = round(w0 * s / 2) * 2, round(h0 * s / 2) * 2
    return max(sw, w + (w % 2)), max(sh, h + (h % 2))


def encode(path, frames, audio, size):
    """frames: decoded VideoFrames; size 'native' (the largest frame size in the cut) or 'WxH'. Frames smaller
    than the largest (e.g. 480p takes next to SeedVR2-upscaled ones) are scaled up to it first (lanczos)."""
    w0, h0 = base_size(frames)
    graph = None
    if size == "native":
        w, h = w0, h0
    else:
        w, h = (int(x) for x in size.split("x"))
        sw, sh = cover_size(w0, h0, w, h)
        graph = av.filter.Graph()
        src = graph.add_buffer(width=w0, height=h0, format="yuv420p", time_base=f"1/{FPS}")
        sc = graph.add("scale", f"{sw}:{sh}:flags=lanczos")
        cr = graph.add("crop", f"{w}:{h}")  # centred by default
        sink = graph.add("buffersink")
        src.link_to(sc); sc.link_to(cr); cr.link_to(sink); graph.configure()
    out = av.open(str(path), "w")
    vs = out.add_stream("libx264", rate=FPS, options={"crf": "18", "preset": "medium"})
    vs.width, vs.height, vs.pix_fmt = w, h, "yuv420p"
    aus = out.add_stream("aac", rate=SR, layout="stereo")
    aus.bit_rate = 192000
    for i, fr in enumerate(frames):
        if (fr.width, fr.height) != (w0, h0):
            fr = fr.reformat(width=w0, height=h0, format="yuv420p", interpolation="LANCZOS")
        fr = fr.reformat(format="yuv420p")
        fr.pts, fr.time_base = i, vs.codec_context.time_base
        if graph:
            graph.push(fr); fr = graph.pull()
            fr.pts = i
        for p in vs.encode(fr):
            out.mux(p)
    for p in vs.encode():
        out.mux(p)
    a32 = audio.astype(np.float32)
    for i in range(0, a32.shape[1], 1024):
        af = av.AudioFrame.from_ndarray(np.ascontiguousarray(a32[:, i:i + 1024]), format="fltp", layout="stereo")
        af.sample_rate, af.pts = SR, i
        for p in aus.encode(af):
            out.mux(p)
    for p in aus.encode():
        out.mux(p)
    out.close()
    return w, h


def srt_time(t):
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cut", help="cut.yaml (or the episode folder with --init)")
    ap.add_argument("--dry-run", action="store_true", help="print the timeline only")
    ap.add_argument("--init", action="store_true", help="write a default cut.yaml for the episode folder")
    args = ap.parse_args()
    if args.init:
        init_cut(args.cut); return
    cut_path = pathlib.Path(args.cut).resolve()
    cut = E.load_yaml(cut_path)
    ep = E.Episode(REPO / "episodes" / cut["episode"])
    name = f"{ep.name}_{cut['version']}"

    entries = [load_entry(ep, e) for e in cut["sequence"]]
    t, subs, timeline, starts = 0.0, [], [], {}
    for e in entries:
        starts.setdefault(e["shot"], t)
        dur = e["frames"] / FPS
        timeline.append({k: e[k] for k in ("shot", "take", "in", "out", "frames", "gain_db", "stale")}
                        | {"start_s": round(t, 3), "end_s": round(t + dur, 3)})
        for s in e["subs"]:
            a = max(float(s["start"]), e["in"] / FPS) - e["in"] / FPS
            b = min(float(s["end"]), (e["out"] + 1) / FPS) - e["in"] / FPS
            if b > a:
                subs.append((t + a, t + b, s["text"]))
        t += dur
    for ly in cut.get("layers") or []:
        if ly.get("role") == "voice" and ly.get("text"):
            a = timeline_time(ly.get("at", 0), starts)
            subs.append((a, a + float(ly.get("sub_s", ly.get("length", 2.5))), ly["text"]))
    subs.sort()
    for row in timeline:
        print(f"{row['start_s']:6.2f}-{row['end_s']:6.2f}s  {row['shot']:6} {row['take']:28} "
              f"frames {row['in']}-{row['out']}" + ("  WARNING: take is from an older version of the shot" if row["stale"] else ""))
    print(f"total {t:.2f} s, {sum(e['frames'] for e in entries)} frames, {len(subs)} subtitle(s)")
    if args.dry_run:
        return

    per_shot = {}
    for e in entries:
        if not np.any(e["audio"]):  # audio: off (the layers carry the sound)
            per_shot[e["shot"]] = {"lufs": None, "true_peak_dbtp": None}
            continue
        lufs, tp = measure(e["audio"])
        per_shot[e["shot"]] = {"lufs": round(lufs, 1), "true_peak_dbtp": round(tp, 1)}
    explicit = {e["shot"] for e, raw in zip(entries, cut["sequence"]) if "gain_db" in raw}
    suggested = auto_gains({s: v["lufs"] for s, v in per_shot.items() if v["lufs"] is not None}, explicit)
    use_auto = cut["loudness"].get("per_shot", "off") == "auto"
    print("per-shot loudness: " + ", ".join(f"{s} {v['lufs'] if v['lufs'] is not None else 'off'}" for s, v in per_shot.items()))
    print(("auto per-shot gains: " if use_auto else "suggested per-shot gains (set loudness.per_shot: auto to apply): ")
          + (", ".join(f"{s} {g:+.1f} dB" for s, g in suggested.items() if g) or "none"))
    sync_target = cut["loudness"].get("sync_target_lufs")  # V2: sync sound sits under music/voice layers
    for e in entries:
        if sync_target is not None and per_shot[e["shot"]]["lufs"] is not None and e["shot"] not in explicit:
            g = min(MAX_AUTO_BOOST_DB, float(sync_target) - per_shot[e["shot"]]["lufs"])
            e["audio"] *= 10 ** (g / 20)
            per_shot[e["shot"]]["sync_gain_db"] = round(g, 1)
            continue
        if use_auto and suggested.get(e["shot"]):
            e["audio"] *= 10 ** (suggested[e["shot"]] / 20)
            per_shot[e["shot"]]["auto_gain_db"] = suggested[e["shot"]]
        fade(e["audio"], cut.get("audio_fade_ms", 10))
    mix = np.concatenate([e["audio"] for e in entries], axis=1)
    mix, layer_rows = mix_layers(mix, cut.get("layers"), starts, cut.get("duck"))
    for r in layer_rows:
        print(f"layer {r['role'] or '-':6} {r['name'] or '-':14} {r['start_s']:6.2f}-{r['end_s']:6.2f}s  {r['gain_db']:+.1f} dB")
    lufs, tp = measure(mix)
    target, ceiling = cut["loudness"]["target_lufs"], cut["loudness"]["ceiling_dbtp"]
    gain = target - lufs
    limited = tp + gain > ceiling
    use_limiter = bool(cut["loudness"].get("limiter")) and limited
    reduction = 0.0
    if limited and not use_limiter:
        gain = ceiling - tp
    if use_limiter:  # reach the target; only the loudest peaks are pulled under the ceiling
        base, best = mix, None
        for _ in range(4):  # limiting lowers the loudness a little: raise the gain and limit again
            out, red = limit(base * 10 ** (gain / 20), ceiling)
            got = measure(out)[0]
            if best is None or got > best[0]:  # keep the loudest result (a shout cannot be pushed further)
                best = (got, out, red, gain)
            if target - got < 0.3 or red >= LIMITER_MAX_DB:
                break
            gain += target - got
        _, mix, reduction, gain = best
    else:
        mix *= 10 ** (gain / 20)
    lufs_out, tp_out = measure(mix)
    print(f"loudness {lufs:.1f} LUFS / {tp:.1f} dBTP -> gain {gain:+.1f} dB -> {lufs_out:.1f} LUFS / {tp_out:.1f} dBTP"
          + (f"  (limiter: peaks reduced by up to {reduction:.1f} dB)" if use_limiter else "")
          + ("  (peak ceiling reached: quieter than target; `limiter: true` can raise it)" if limited and not use_limiter else ""))
    if reduction >= LIMITER_MAX_DB:
        print(f"warning: the limiter stopped at {reduction:.1f} dB of peak reduction (cap {LIMITER_MAX_DB} dB), so the "
              f"cut stays under the target: lower the loudest shot with gain_db, or accept the quieter level")

    final = E.RENDERS / "episodes" / ep.name / "_final"
    final.mkdir(parents=True, exist_ok=True)
    srt = "".join(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{txt}\n\n" for i, (a, b, txt) in enumerate(subs, 1))
    srt_repo = REPO / "subtitles" / f"{name}.srt"
    srt_repo.write_text(srt)
    frames = [f for e in entries for f in e["video"]]
    outputs = []
    for size in cut["sizes"]:
        w, h = base_size(frames) if size == "native" else map(int, size.split("x"))
        path = final / f"{name}_{w}x{h}.mp4"
        encode(path, frames, mix, size)
        shutil.copyfile(srt_repo, path.with_suffix(".srt"))
        with av.open(str(path)) as c:
            nv = sum(1 for _ in c.decode(video=0))
        outputs.append({"file": str(path), "width": w, "height": h, "frames": nv, "bytes": path.stat().st_size,
                        "sha256": E.sha256(path)})
        print(f"wrote {path}  ({nv} frames, {path.stat().st_size / 1e6:.1f} MB)")

    manifest = {
        "episode": ep.name, "version": cut["version"],
        "created": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "cut_file": str(cut_path.relative_to(REPO)), "cut_sha256": E.sha256(cut_path),
        "timeline": timeline,
        "sources": [{k: e[k] for k in ("shot", "take", "file", "sha256", "frames_in_take", "in", "out",
                                        "audio_len_diff_samples", "video_file", "audio_mode", "mirror", "upscale")} for e in entries],
        "layers": layer_rows, "duck": cut.get("duck"),
        "audio": {"sample_rate": SR, "fade_ms": cut.get("audio_fade_ms", 10), "per_shot_before_mix": per_shot,
                  "per_shot_mode": cut["loudness"].get("per_shot", "off"),
                  "mix_lufs": round(lufs, 2), "mix_true_peak_dbtp": round(tp, 2), "gain_db": round(gain, 2),
                  "peak_limited": bool(limited), "out_lufs": round(lufs_out, 2), "out_true_peak_dbtp": round(tp_out, 2),
                  "codec": "aac 192k"},
        "video": {"codec": "libx264", "crf": 18, "preset": "medium", "pix_fmt": "yuv420p", "fps": FPS,
                  "upscale": "lanczos to target height, centre crop"},
        "subtitles": {"file": str(srt_repo.relative_to(REPO)), "entries": len(subs)},
        "outputs": outputs,
        "env": {"pyav": av.__version__, "libavcodec": ".".join(map(str, av.library_versions["libavcodec"])),
                "repo_commit": subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                                              capture_output=True, text=True).stdout.strip(),
                "repo_dirty": bool(subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"],
                                                  capture_output=True, text=True).stdout.strip())},
    }
    mp = REPO / "runs" / dt.date.today().isoformat() / f"{ep.name}__cut_{cut['version']}.json"
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(json.dumps(manifest, indent=1))
    print("manifest:", mp.relative_to(REPO))


if __name__ == "__main__":
    main()
