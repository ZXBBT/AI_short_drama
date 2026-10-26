"""Offline tests for scripts/assemble.py (no ComfyUI needed).

    ~/dev/ComfyUI/.venv/bin/python scripts/test_assemble.py
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import assemble as A  # noqa: E402

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures.append(name)


# loudness: a 997 Hz sine of amplitude 0.1 in both channels measures about -20 LUFS (BS.1770)
t = np.arange(A.SR * 5) / A.SR
sine = np.vstack([0.1 * np.sin(2 * np.pi * 997 * t)] * 2)
lufs, tp = A.measure(sine)
check("sine -20 dBFS -> about -20 LUFS", abs(lufs + 20) < 0.3, lufs)
check("sine true peak about -20 dBTP", abs(tp + 20) < 0.3, tp)
lufs6, _ = A.measure(sine * 2)
check("+6 dB gain -> +6 LU", abs(lufs6 - lufs - 6.02) < 0.1, lufs6 - lufs)

# fades: start and end at zero, middle untouched
seg = A.fade(np.ones((2, A.SR)), 10)
check("fade starts and ends at 0", seg[0, 0] == 0 and seg[0, -1] == 0)
check("fade is 10 ms long", seg[0, 480] == 1.0 and seg[0, 478] < 1.0)
check("fade leaves the middle", seg[0, A.SR // 2] == 1.0)

# SRT timestamps
check("srt time", A.srt_time(9.7667) == "00:00:09,767", A.srt_time(9.7667))
check("srt time over a minute", A.srt_time(75.5) == "00:01:15,500", A.srt_time(75.5))

# per-shot auto levelling (Stage 7.3), Midnight Call v1 measurements
v = {"S001": -18.4, "S002": -10.0, "S003": -17.2, "S004a": -20.0, "S004": -14.5, "S005": -31.6, "S005b": -29.8}
g = A.auto_gains(v, set())
check("auto: loud outlier pulled down to median+6", g["S002"] == -2.4, g)
check("auto: quiet outliers pulled up to median-6", (g["S005"], g["S005b"]) == (7.2, 5.4), g)
check("auto: shots inside the window untouched", g["S001"] == g["S004"] == 0.0, g)
check("auto: explicit gain_db wins", "S002" not in A.auto_gains(v, {"S002"}))
check("auto: capped at 10 dB", A.auto_gains({"a": -20, "b": -20, "c": -60.5, "d": -45}, set())["d"] == 10.0)

# --init writes a valid cut list in episode file order and never overwrites
import shutil, tempfile, yaml  # noqa: E401,E402
d = pathlib.Path(tempfile.mkdtemp(prefix="ep_init_"))
(d / "episode.yaml").write_text("episode: t\nrecipe: h3_base_v1\nshots:\n  B: {type: t2v, prompt: b, seed: 1}\n  A: {type: t2v, prompt: a, seed: 1}\n")
A.init_cut(d)
c = yaml.safe_load((d / "cut.yaml").read_text())
check("init: sequence in file order", [e["shot"] for e in c["sequence"]] == ["B", "A"], c["sequence"])
check("init: auto levelling on by default", c["loudness"]["per_shot"] == "auto")
try:
    A.init_cut(d); check("init: refuses to overwrite", False)
except SystemExit:
    check("init: refuses to overwrite", True)
shutil.rmtree(d)

# Stage 8.5: generated cut list from picks (temporary copy of Midnight Call with its real takes)
import episode as E  # noqa: E402
with tempfile.TemporaryDirectory() as td:
    t_ = pathlib.Path(td) / "midnight_call"; t_.mkdir()
    for f in ("episode.yaml", "selections.yaml"):
        shutil.copy(E.REPO / "episodes/midnight_call" / f, t_ / f)
    y = (t_ / "episode.yaml").read_text()
    y = y.replace("    allow_cuts: true     # H3's own cut (wide -> door) is used in the edit", "    allow_cuts: false")
    y = y.replace("    note: she answers; close-up", "    note: she answers; close-up\n    dialogue: [{character: woman, line: 'Hello?'}]")
    (t_ / "episode.yaml").write_text(y)
    cut = yaml.safe_load(A.generate_cut(E.Episode(t_), "v1").read_text())
    seq = {e["shot"]: e for e in cut["sequence"]}
    check("generated cut: every shot, in file order", [e["shot"] for e in cut["sequence"]] == list(E.Episode(t_).shots),
          [e["shot"] for e in cut["sequence"]])
    check("generated cut is marked and versioned", cut["generated"] is True and cut["version"] == "v1")
    check("unwanted H3 cut -> longest uncut part (S004 frames 0-68)", (seq["S004"].get("in", 0), seq["S004"].get("out")) == (0, 68),
          seq["S004"])
    check("shots without cuts are used whole", "in" not in seq["S001"] and "out" not in seq["S001"])
    subs = seq["S002"].get("subs") or []
    check("dialogue becomes a voice-timed subtitle", len(subs) == 1 and subs[0]["text"] == "Hello?" and 4.4 < subs[0]["start"] < 4.9,
          subs)
    check("1080p output and auto levelling by default", "1080x1920" in cut["sizes"] and cut["loudness"]["per_shot"] == "auto")
    y16 = (t_ / "episode.yaml").read_text().replace('aspect: "9:16"', 'aspect: "16:9"').replace("aspect: '9:16'", "aspect: '16:9'")
    (t_ / "episode.yaml").write_text(y16)
    check("landscape episode -> 1920x1080", A.hd_size(E.Episode(t_)) == "1920x1080", A.hd_size(E.Episode(t_)))
check("cover size: 864x480 -> 1920x1080 trims the sides", A.cover_size(864, 480, 1920, 1080) == (1944, 1080),
      A.cover_size(864, 480, 1920, 1080))
check("cover size: 352x608 -> 1080x1920 trims the sides (as before)", A.cover_size(352, 608, 1080, 1920) == (1112, 1920),
      A.cover_size(352, 608, 1080, 1920))
check("cover size: 480x864 -> 1080x1920 trims top/bottom", A.cover_size(480, 864, 1080, 1920) == (1080, 1944),
      A.cover_size(480, 864, 1080, 1920))
check("cover size: 352x608 -> 720x1280 unchanged from v1 (742x1280)", A.cover_size(352, 608, 720, 1280) == (742, 1280))
check("next version v1 -> v2", A.next_version("v1") == "v2" and A.next_version("v9") == "v10")

# V2 layered soundtrack: a 4 s tone looped to 10 s, placed relative to a shot, ducked under a voice
import av as _av  # noqa: E402
with tempfile.TemporaryDirectory() as td:
    def tone(path, secs, hz, amp=0.1):
        t_ = np.arange(int(A.SR * secs)) / A.SR
        x = (amp * np.sin(2 * np.pi * hz * t_)).astype(np.float32)
        c = _av.open(str(path), "w"); s_ = c.add_stream("pcm_s16le", rate=A.SR, layout="stereo")
        for i in range(0, x.size, 4800):
            f = _av.AudioFrame.from_ndarray(np.ascontiguousarray(np.stack([x[i:i + 4800]] * 2)), format="fltp", layout="stereo")
            f.sample_rate, f.pts = A.SR, i
            for pk in s_.encode(f):
                c.mux(pk)
        for pk in s_.encode():
            c.mux(pk)
        c.close()
        return path
    bed, voice = tone(pathlib.Path(td) / "bed.wav", 4, 220), tone(pathlib.Path(td) / "voice.wav", 1, 880, 0.3)
    starts = {"X": 0.0, "Y": 2.0}
    st_, arr = A.layer_audio({"source": str(bed), "at": {"shot": "Y", "offset": -1.0}, "length": 10,
                              "loop_xfade": 0.5, "fade_in": 0.2}, starts, 15)
    check("layer: placed relative to a shot (Y at 2 s, offset -1 s)", st_ == A.SR * 1)
    check("layer: short source looped to the requested length", arr.shape[1] == A.SR * 10)
    check("layer: fade-in starts from silence", abs(arr[0, 0]) < 1e-6)
    rms = [np.sqrt(np.mean(arr[0, k * A.SR:(k + 1) * A.SR] ** 2)) for k in range(1, 10)]
    check("layer: no gap or jump at the loop joins", min(rms) > 0.05, [round(r, 3) for r in rms])
    mix = np.zeros((2, A.SR * 12))
    mix, rows = A.mix_layers(mix, [{"role": "bed", "source": str(bed), "at": 0, "length": 12},
                                   {"role": "voice", "source": str(voice), "at": 6}], starts, {"db": -12, "ramp_ms": 100})
    bed_rms = lambda a_, b_: np.sqrt(np.mean(mix[0, int(a_ * A.SR):int(b_ * A.SR)] ** 2))  # noqa: E731
    check("duck: the bed keeps its full level away from the voice line",
          bed_rms(2, 3) > 0.06 and len(rows) == 2, round(bed_rms(2, 3), 3))
    ly = {"source": str(bed), "at": 0, "length": 4, "target_lufs": -30}
    _, arr = A.layer_audio(ly, starts, 15)
    check("layer: target_lufs levels the layer by measurement", abs(A.measure(arr)[0] + 30) < 0.5, A.measure(arr)[0])
    quiet = tone(pathlib.Path(td) / "quiet.wav", 4, 220, 0.0005)
    _, arr = A.layer_audio({"source": str(quiet), "at": 0, "length": 4, "target_lufs": -20}, starts, 15)
    check("layer: target levelling never boosts a near-silent source by more than 12 dB",
          abs(20 * np.log10(np.abs(arr).max() / 0.0005) - A.MAX_AUTO_BOOST_DB) < 0.5)
    music = np.zeros((2, A.SR * 12))
    music, _ = A.mix_layers(music, [{"role": "music", "source": str(bed), "at": 0, "length": 12},
                                    {"role": "voice", "source": str(voice), "at": 6, "gain_db": -60}], starts,
                            {"db": -12, "ramp_ms": 100})
    m = lambda a_, b_: np.sqrt(np.mean(music[0, int(a_ * A.SR):int(b_ * A.SR)] ** 2))  # noqa: E731
    check("duck: music drops ~12 dB under a voice line and recovers after it",
          abs(20 * np.log10(m(6.3, 6.7) / m(2, 3)) + 12) < 1.5 and abs(m(9, 10) - m(2, 3)) < 0.01,
          (round(20 * np.log10(m(6.3, 6.7) / m(2, 3)), 1)))
check("no voice found (silence) -> lines spread evenly over the take",
      A.time_lines(np.zeros((2, A.SR * 4)), ["a", "b"]) == [(0.0, 2.0, "a"), (2.0, 4.0, "b")])

print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED: {failures}'}")
sys.exit(1 if failures else 0)
