"""One command for an episode: validate -> (start ComfyUI) -> render with re-rolls -> review sheets
-> assemble when every shot in the cut has a picked take -> summary.

    PY=~/dev/ComfyUI/.venv/bin/python
    $PY scripts/pipeline.py episodes/midnight_call [--stop-comfyui] [--no-render]

Safe to run again at any time: finished takes are recognised by fingerprint and skipped.
Exit codes: 0 = episode assembled (or already up to date); 2 = waiting for a human decision
(pick takes, review a shot that used up its re-rolls, bump the cut version); 1 = error.
Writes ~/AI_renders/comfyui/episodes/<ep>/_logs/pipeline_<time>.json (summary).
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import episode as E  # noqa: E402
import review_sheet as R  # noqa: E402

REPO = E.REPO


def comfyui_up():
    try:
        urllib.request.urlopen(f"http://{E.API}/system_stats", timeout=3).read()
        return True
    except OSError:
        return False


def start_comfyui(log_path, timeout_s=900):
    """Start ComfyUI with the project launch script (localhost only); wait until it answers."""
    log = open(log_path, "a")
    proc = subprocess.Popen(["/bin/zsh", str(REPO / "scripts/launch_comfyui.sh")], stdout=log,
                            stderr=subprocess.STDOUT, start_new_session=True)
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if proc.poll() is not None:
            raise SystemExit(f"ComfyUI exited during start-up (code {proc.returncode}); see {log_path}")
        if comfyui_up():
            print(f"ComfyUI started by the pipeline (pid {proc.pid}) in {time.time() - t0:.0f} s", flush=True)
            return proc
        time.sleep(5)
    os.killpg(proc.pid, signal.SIGINT)
    raise SystemExit(f"ComfyUI did not answer within {timeout_s} s; see {log_path}")


def stop_comfyui(proc):
    os.killpg(proc.pid, signal.SIGINT)  # same as Ctrl+C in its Terminal
    try:
        proc.wait(60)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM); proc.wait(30)
    print("ComfyUI stopped (it was started by the pipeline)")


def cut_state(ep):
    """('missing'|'waiting'|'current'|'stale'|'ready', detail) for episodes/<ep>/cut.yaml."""
    path = ep.dir / "cut.yaml"
    if not path.exists():
        return "missing", "no cut.yaml (create one with: assemble.py --init)"
    cut = E.load_yaml(path)
    unpicked = [e["shot"] for e in cut["sequence"] if not (e.get("take") or ep.selected_take(e["shot"]))]
    if unpicked:
        return "waiting", f"no picked take for {unpicked}"
    manifest = REPO / "runs"
    found = sorted(manifest.glob(f"*/{ep.name}__cut_{cut['version']}.json"))
    if not found:
        return "ready", f"cut {cut['version']} not assembled yet"
    m = json.loads(found[-1].read_text())
    now = [(e["shot"], e.get("take") or ep.selected_take(e["shot"])) for e in cut["sequence"]]
    before = [(s["shot"], s["take"]) for s in m["sources"]]
    if m["cut_sha256"] == E.sha256(path) and now == before:
        return "current", f"cut {cut['version']} already assembled ({found[-1].relative_to(REPO)})"
    return "stale", (f"cut {cut['version']} was assembled from different takes or a different cut.yaml; "
                     f"change 'version' in cut.yaml (e.g. v2) to assemble a new version without overwriting")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--no-render", action="store_true", help="skip rendering (review/assemble only)")
    ap.add_argument("--stop-comfyui", action="store_true", help="stop ComfyUI at the end if the pipeline started it")
    ap.add_argument("--swap-limit", type=float, default=20.0)
    a = ap.parse_args()
    ep = E.Episode(a.episode)
    logs = E.RENDERS / "episodes" / ep.name / "_logs"
    logs.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    summary = {"episode": ep.name, "started": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
               "rendered": 0, "error": None}
    t0, proc, code = time.time(), None, 1
    try:
        errors, warnings = E.validate(ep)
        summary["warnings"] = warnings
        if errors:
            summary["error"] = {"validation": errors}
            raise SystemExit("validation failed: " + "; ".join(errors))
        if not a.no_render and any(E.shot_status(ep, s)["state"] == "todo" for s in ep.shots):
            if not comfyui_up():
                proc = start_comfyui(logs / f"comfyui_{stamp}.log")
            summary["comfyui_started_by_pipeline"] = proc is not None
            summary["rendered"] = E.cmd_render(ep, None, False, False, a.swap_limit) or 0
        # fresh view after rendering
        ep = E.Episode(a.episode)
        shots = {}
        for sid in E.order(ep):
            st = E.shot_status(ep, sid)
            shots[sid] = {k: st.get(k) for k in ("state", "reason", "needed", "selected")} | {
                "good": len(st.get("good") or []), "rejected": st.get("rejected") or {}}
            if st["state"] in ("done", "needs_review") and st["done"] and not st["selected"]:
                shots[sid]["review_sheet"] = str(R.sheet(ep, sid))
        summary["shots"] = shots
        cs, detail = cut_state(ep)
        summary["cut"] = {"state": cs, "detail": detail}
        if cs == "ready":
            subprocess.run([sys.executable, str(REPO / "scripts/assemble.py"), str(ep.dir / "cut.yaml")], check=True)
            cs, detail = cut_state(ep)
            summary["cut"] = {"state": cs, "detail": detail}
        waiting = [s for s, v in shots.items() if v["state"] in ("blocked", "needs_review", "todo")
                   or (v["state"] == "done" and not v["selected"])]
        summary["waiting_for_human"] = waiting
        code = 0 if cs == "current" and not waiting else 2
    except SystemExit as e:
        summary["error"] = summary["error"] or str(e)
        code = 1
    finally:
        if proc and a.stop_comfyui:
            stop_comfyui(proc)
        summary["minutes"] = round((time.time() - t0) / 60, 1)
        summary["exit_code"] = code
        out = logs / f"pipeline_{stamp}.json"
        out.write_text(json.dumps(summary, indent=1, default=str))
        print(json.dumps({k: summary.get(k) for k in ("rendered", "waiting_for_human", "cut", "error", "minutes", "exit_code")},
                         indent=1, default=str))
        print("summary:", out)
    sys.exit(code)


if __name__ == "__main__":
    main()
