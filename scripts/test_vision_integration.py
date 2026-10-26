"""Optional integration check of the real macOS Vision face check (scripts/face_boxes.swift).

    ~/dev/ComfyUI/.venv/bin/python scripts/test_vision_integration.py
    RUN_VISION_INTEGRATION=1 scripts/check.sh

Not one of the standard checks: its result depends on this Mac's Vision framework, so scripts/check.sh
runs it only when RUN_VISION_INTEGRATION=1. No ComfyUI, no rendering, no downloads, no network; it only
measures two reference pictures that are in Git. Like every face check it may (re)compile the helper
into ~/AI_renders/comfyui/_bin.

Exit 0 = PASS, 1 = FAIL, 77 = SKIP. SKIP only when the environment clearly cannot run Vision (not macOS,
no Swift compiler for a helper that needs compiling, a recognisable sandbox/permission limit). Anything
that cannot be classified as the environment is a FAIL.
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import brief as B  # noqa: E402
import episode as E  # noqa: E402
import face_check as FC  # noqa: E402

SKIP = 77
IMAGES = [E.REPO / "inputs/midnight_call/kf_S001_desk_v1.png", E.REPO / "inputs/sunlight/ref_lin_v1.png"]
# Helper messages that clearly mean "Vision is not allowed here". Kept short on purpose: add a pattern
# only after seeing it in a real restricted environment; any other message is a FAIL.
ENV_LIMIT = re.compile(r"operation not permitted|not permitted|sandbox|not authorized", re.I)

failures = []


def finish(code, reason=""):
    print({0: "PASS", SKIP: f"SKIP: {reason}"}.get(code, f"FAIL: {reason}"))
    sys.exit(code)


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures.append(name)


# --- environment (SKIP only for clear causes) ---
if sys.platform != "darwin":
    finish(SKIP, f"macOS Vision needs macOS (this is {sys.platform})")
if not FC.BIN.exists() or FC.BIN.stat().st_mtime < FC.SRC.stat().st_mtime:  # face_check.helper() will compile
    if not shutil.which("swiftc"):
        finish(SKIP, f"no Swift compiler (swiftc) to build {FC.BIN}")
    d = next(p for p in [FC.BIN.parent, *FC.BIN.parent.parents] if p.exists())
    if not os.access(d, os.W_OK):
        finish(SKIP, f"cannot write {d} to build the face helper (sandbox/permission limit)")
try:
    FC.helper()
except PermissionError as e:
    finish(SKIP, f"not allowed to build the face helper: {e}")
except subprocess.CalledProcessError as e:
    finish(1, f"the Swift face helper failed to compile (swiftc exit {e.returncode}; its messages are above)")
except OSError as e:
    finish(1, f"could not build the face helper: {e!r}")

# --- the helper on two known-readable pictures ---
try:
    res = FC.faces_in_images(IMAGES)
except PermissionError as e:
    finish(SKIP, f"not allowed to run the face helper: {e}")
except subprocess.CalledProcessError as e:
    finish(1, f"the face helper exited with {e.returncode}: {(e.stderr or '').strip()[:300]}")
except (OSError, ValueError) as e:
    finish(1, f"face helper: {type(e).__name__}: {e}")
errors = [(pathlib.Path(r["path"]).name, r["error"]) for r in res if r.get("error")]
if any(not ENV_LIMIT.search(str(msg)) for _, msg in errors):
    finish(1, f"the face helper could not measure readable pictures: {errors}")
if errors:
    finish(SKIP, f"Vision is not available here (sandbox/permission): {errors}")

for path, r in zip(IMAGES, res):
    with Image.open(path) as im:
        size = im.size
    check(f"{path.name}: size {size[0]}x{size[1]}", (r["width"], r["height"]) == size, (r["width"], r["height"]))
    check(f"{path.name}: face found", (r["h"] or 0) > 0, r)
    check(f"{path.name}: quality between 0 and 1", r["quality"] is not None and 0 <= r["quality"] <= 1, r["quality"])

# --- validate_brief with the real face check (the checks test_brief.py makes with synthetic values) ---
tmp = pathlib.Path(tempfile.mkdtemp(prefix="vision_test_"))
ep_dir = tmp / "vtest"
ep_dir.mkdir()
brief = {"episode": "vtest", "title": "Vision test", "plot": "A woman waits for a call.",
         "target": {"length_s": 9, "aspect": "9:16"},
         "characters": {"woman": {"description": "young woman", "images": [str(IMAGES[0].relative_to(E.REPO))]}}}
errs, warns, info = B.validate_brief(brief, ep_dir)
shutil.rmtree(tmp)
check("validate_brief: good brief has no errors", not errs, errs)
check("validate_brief: reference face is measured", any("face" in i and "px" in i for i in info), info)

# --- the real command ---
r = subprocess.run([sys.executable, str(E.REPO / "scripts/brief.py"), "validate", "episodes/sunlight"],
                   cwd=E.REPO, capture_output=True, text=True)
print(r.stdout.rstrip())
check("brief.py validate episodes/sunlight: exit 0", r.returncode == 0, r.returncode)
check("brief.py validate episodes/sunlight: face measured", "face" in r.stdout and "px" in r.stdout, r.stdout)
check("brief.py validate episodes/sunlight: no traceback", "Traceback" not in r.stdout + r.stderr, r.stderr[-500:])

finish(1 if failures else 0, f"{len(failures)} check(s): {failures}")
