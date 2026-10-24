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

print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED: {failures}'}")
sys.exit(1 if failures else 0)
