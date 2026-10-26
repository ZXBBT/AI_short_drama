"""Offline tests for scripts/take_checks.py (no ComfyUI, no Vision: synthetic measurements).

    ~/dev/ComfyUI/.venv/bin/python scripts/test_take_checks.py
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import take_checks as T  # noqa: E402

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures.append(name)


# what the prompt allows
e = T.expectations('With a bright voice she calls: <d>[English] Over here!</d> There is no text anywhere.')
check("dialogue is speech, never allowed text", e["speech"] == "speaks" and e["allowed_text"] == [], e)
e = T.expectations('He lifts a can printed "SUPER DRY". His lips stay closed. He never looks into the lens.')
check("quoted packaging text allowed", e["allowed_text"] == ["SUPERDRY"], e)
check("'lips stay closed' -> silent", e["speech"] == "silent", e)
check("'never looks into the lens' -> no lens contact", not e["lens_contact_ok"], e)
e = T.expectations("She looks straight into the lens and smiles.")
check("asked lens contact is allowed", e["lens_contact_ok"], e)
e = T.expectations("He (S1) says in an off-screen voiceover: <d>[English] Be brave.</d>")
check("voice-over counts as silent on screen", e["speech"] == "silent", e)

# allowed text matching
check("garbled packaging still matches its quote", T.allowed("SUPER DRY", ["SUPERDRY"]) and T.allowed("SUPFR DRY", ["SUPERDRY"]))
check("unrelated text does not match", not T.allowed("Over here!", ["SUPERDRY"]))

# lip cycles: jitter below the step is ignored, real open/close counted
check("jitter is not speech", T.cycles([0.10, 0.11, 0.105, 0.112, 0.10], 0.025) == 0)
check("three open/close cycles", T.cycles([0, .05, 0, .05, 0, .05, 0], 0.025) == 3)
check("one slow open-close", T.cycles([0, .03, .06, .03, 0], 0.025) == 1)

# iris position: dark blob on the left / centre of an eye outline
gray = np.full((20, 40), 200, np.float32)
eye = [(0, 10), (10, 2), (30, 2), (39, 10), (30, 18), (10, 18)]
g = gray.copy(); g[6:14, 17:23] = 20
check("centred iris ~0", abs(T.iris_offset(g, eye)) < 0.06, T.iris_offset(g, eye))
g = gray.copy(); g[6:14, 4:10] = 20
check("iris at the left corner < -0.2", T.iris_offset(g, eye) < -0.2, T.iris_offset(g, eye))


# verdicts from per-frame measurements
def face(yaw=30, iris=(0.3, 0.3), mouth=0.05, texts=()):
    return {"texts": [{"text": t, "confidence": 0.9} for t in texts], "face_h": 150, "yaw": yaw, "pitch": 0,
            "iris": list(iris), "mouth": mouth}


idx = list(range(0, 80, 2))
silent = T.expectations("His lips stay closed.")
_, w = T.analyse([face() for _ in idx], idx, silent)
check("clean take has no warnings", w == [], w)
_, w = T.analyse([face(texts=["Over here!"] if i > 40 else ()) for i in idx], idx, silent)
check("burned-in caption warns (old Sunlight P4)", any("Over here!" in x for x in w), w)
_, w = T.analyse([face(texts=["Over here!"] if i in (40, 42) else ()) for i in idx], idx, silent)
check("text in only 2 frames is noise", w == [], w)
_, w = T.analyse([face(yaw=3, iris=(0.02, -0.03)) if 30 <= i < 46 else face() for i in idx], idx, silent)
check("lens contact in 20 % of face frames warns (V1 S2B: 22 %)", any("lens" in x for x in w), w)
_, w = T.analyse([face(yaw=3, iris=(0.02, -0.03))] * len(idx), idx, T.expectations("She looks into the lens."))
check("asked lens contact does not warn", w == [], w)
talk = [face(mouth=0.02 if (i // 4) % 2 else 0.08) for i in idx]
_, w = T.analyse(talk, idx, silent)
check("lips moving in a silent shot warn", any("lips move" in x for x in w), w)
_, w = T.analyse([face(mouth=0.03)] * len(idx), idx, T.expectations("She says <d>[English] Hi!</d>"))
check("a speaking shot with still lips warns", any("lip sync" in x for x in w), w)

print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED: {failures}'}")
sys.exit(1 if failures else 0)
