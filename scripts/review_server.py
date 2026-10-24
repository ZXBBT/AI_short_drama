"""Local review page: watch every take of an episode and pick one per shot with a click.

    ~/dev/ComfyUI/.venv/bin/python scripts/review_server.py episodes/midnight_call [--port 8189]
    then open http://127.0.0.1:8189 in a browser on this Mac. Stop with Ctrl+C.

Only listens on 127.0.0.1 (this Mac). Serves only videos named in take records and the latest
assembled cut; "Pick" writes selections.yaml through the same code as `episode.py select`.
Reads the episode fresh on every request, so it reflects new renders without restarting.
"""
import argparse
import html
import json
import pathlib
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import autopick as AP  # noqa: E402
import episode as E  # noqa: E402

PAGE_CSS = """
:root { --bg:#f6f5f2; --card:#fff; --ink:#1d1d1f; --muted:#6b6b70; --line:#e2e0db; --accent:#2f6fde;
        --good:#1f8a4c; --warn:#b26a00; --bad:#c23b2a; }
@media (prefers-color-scheme: dark) { :root { --bg:#141416; --card:#1e1e21; --ink:#ececee; --muted:#9a9aa2;
        --line:#2e2e33; --accent:#6c9cff; --good:#4cc27e; --warn:#e0a040; --bad:#ff6b5b; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.45 -apple-system, system-ui, sans-serif; }
header { padding:20px 24px 8px; } h1 { margin:0 0 4px; font-size:22px; } .muted { color:var(--muted); }
main { padding:8px 24px 40px; display:grid; gap:18px; }
section { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; }
.head { display:flex; gap:10px; align-items:baseline; flex-wrap:wrap; } .head h2 { margin:0; font-size:18px; }
.chip { font-size:12px; padding:2px 8px; border-radius:999px; border:1px solid var(--line); color:var(--muted); }
.chip.done { color:var(--good); border-color:var(--good); } .chip.todo, .chip.blocked { color:var(--warn); border-color:var(--warn); }
.chip.needs_review { color:var(--bad); border-color:var(--bad); }
details { margin:8px 0; } summary { cursor:pointer; color:var(--muted); } pre { white-space:pre-wrap; font-size:13px; }
.takes { display:flex; gap:14px; flex-wrap:wrap; margin-top:10px; }
.take { width:236px; border:2px solid transparent; border-radius:10px; padding:6px; }
.take.picked { border-color:var(--accent); } video { width:100%; border-radius:6px; background:#000; display:block; }
.meta { font-size:12px; color:var(--muted); margin:6px 0; } .warn { color:var(--bad); font-size:12px; }
button { width:100%; padding:7px; border-radius:8px; border:1px solid var(--accent); background:transparent;
         color:var(--accent); font-weight:600; cursor:pointer; } .picked button { background:var(--accent); color:#fff; }
.final video { width:min(360px,100%); }
.badge { font-size:11px; padding:1px 6px; border-radius:999px; background:var(--accent); color:#fff; margin-left:4px; }
.banner { display:flex; gap:14px; align-items:center; flex-wrap:wrap; }
.banner button { width:auto; padding:7px 16px; } .ok { color:var(--good); font-weight:600; }
"""

PAGE_JS = """
async function confirmPicks(btn) {
  btn.disabled = true;
  const r = await fetch('/confirm', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
  if (r.ok) { location.reload(); } else { btn.disabled = false; btn.textContent = 'Confirm failed: ' + (await r.text()); }
}
async function pick(shot, take, btn) {
  btn.disabled = true; btn.textContent = 'Saving…';
  const r = await fetch('/select', {method:'POST', headers:{'Content-Type':'application/json'},
                                    body: JSON.stringify({shot, take})});
  if (r.ok) { location.reload(); } else { btn.disabled = false; btn.textContent = 'Pick (failed: ' + (await r.text()) + ')'; }
}
"""


def esc(x):
    return html.escape(str(x))


def latest_cut(ep):
    found = sorted(E.REPO.glob(f"runs/*/{ep.name}__cut_*.json"), key=lambda p: p.stat().st_mtime)
    return json.loads(found[-1].read_text()) if found else None


def render_page(ep):
    parts = [f"<header><h1>{esc(ep.data.get('title', ep.name))}</h1>"
             f"<div class='muted'>Episode <b>{esc(ep.name)}</b> · pick one take per shot · "
             f"choices are saved to <code>episodes/{esc(ep.name)}/selections.yaml</code></div></header><main>"]
    if ep.review.get("final", True):
        c = ep.selections.get(AP.CONFIRM_KEY) or {}
        ok = AP.confirmed(ep, [s for s in ep.shots if ep.selected_take(s)]) and c
        state = (f"<span class='ok'>Picks confirmed {esc(c.get('at', ''))}</span>" if ok else
                 "<span>Picks not confirmed yet: the episode is assembled after you confirm.</span>")
        mode = "auto-picked takes are marked" if ep.review.get("picks") == "auto" else "you pick each shot"
        parts.append(f"<section class='banner'>{state}<span class='muted'>({mode})</span>"
                     f"<button onclick='confirmPicks(this)'>Confirm picks</button></section>")
    cut = latest_cut(ep)
    if cut:
        vids = "".join(f"<div><video controls preload='metadata' src='/final/{i}'></video>"
                       f"<div class='meta'>{o['width']}×{o['height']}</div></div>" for i, o in enumerate(cut["outputs"]))
        parts.append(f"<section class='final'><div class='head'><h2>Latest cut: {esc(cut['version'])}</h2>"
                     f"<span class='chip'>{esc(cut['created'])}</span></div><div class='takes'>{vids}</div></section>")
    for sid in E.order(ep):
        st = E.shot_status(ep, sid)
        s = ep.shots[sid]
        recs = {r["take_id"]: r for r in ep.takes(sid) if r.get("fingerprint") == st.get("fp") and r.get("status") == "success"}
        takes = []
        for tid in st.get("done") or []:
            r, picked = recs[tid], tid == st["selected"]
            problems = st["rejected"].get(tid, [])
            mem = r.get("memory_gib") or {}
            cache = pathlib.Path(r["output"]["file"]).with_suffix(".faces.json")
            fs = json.loads(cache.read_text())["summary"] if cache.exists() else None
            face = (f" · face q {fs['quality_median']} / {fs['face_h_median']} px"
                    if fs and fs.get("quality_median") is not None else "")
            badge = "<span class='badge'>auto-picked</span>" if picked and AP.is_auto(ep, sid) else ""
            takes.append(
                f"<div class='take{' picked' if picked else ''}'>"
                f"<video controls preload='metadata' src='/video/{esc(sid)}/{esc(tid)}'></video>"
                f"<div class='meta'>seed {esc(r['seed'])} · {r['wall_seconds'] / 60:.1f} min · swap "
                f"{mem.get('swap_peak', '?')} GiB{esc(face)}{badge}</div>"
                + "".join(f"<div class='warn'>⚠ {esc(p)}</div>" for p in problems)
                + f"<button onclick=\"pick('{esc(sid)}','{esc(tid)}',this)\">{'Picked' if picked else 'Pick'}</button></div>")
        reason = f"<div class='warn'>{esc(st['reason'])}</div>" if st.get("reason") else ""
        prompt = esc(E.Episode.params(ep, sid)["prompt"])
        parts.append(
            f"<section><div class='head'><h2>{esc(sid)}</h2><span class='chip'>{esc(st['type'])}</span>"
            f"<span class='chip {esc(st['state'])}'>{esc(st['state'])}</span>"
            f"<span class='chip'>{len(st.get('good') or [])}/{st['needed']} good</span></div>"
            f"<div class='muted'>{esc(s.get('note', ''))}</div>{reason}"
            f"<details><summary>Prompt</summary><pre>{prompt}</pre></details>"
            f"<div class='takes'>{''.join(takes) or '<span class=muted>No takes of the current version yet.</span>'}</div></section>")
    parts.append("</main>")
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'><title>Review · {esc(ep.name)}</title>"
            f"<style>{PAGE_CSS}</style><script>{PAGE_JS}</script></head><body>{''.join(parts)}</body></html>")


class Handler(BaseHTTPRequestHandler):
    episode_dir = None
    port = None

    def log_message(self, fmt, *args):  # quiet: only errors
        pass

    def _host_ok(self):
        # refuse requests addressed to other host names (DNS-rebinding protection)
        return self.headers.get("Host", "") in (f"127.0.0.1:{self.port}", f"localhost:{self.port}")

    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path):
        size = path.stat().st_size
        rng = re.match(r"bytes=(\d*)-(\d*)$", self.headers.get("Range", ""))
        start, end = 0, size - 1
        if rng:  # Safari's video player needs byte ranges
            if rng.group(1):
                start = int(rng.group(1))
                end = int(rng.group(2)) if rng.group(2) else size - 1
            else:
                start = max(0, size - int(rng.group(2)))
            end = min(end, size - 1)
            if start > end:
                self.send_response(416); self.send_header("Content-Range", f"bytes */{size}"); self.end_headers(); return
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, "forbidden host")
        ep = E.Episode(self.episode_dir)
        if self.path == "/":
            return self._send(200, render_page(ep), "text/html; charset=utf-8")
        m = re.match(r"/video/([\w.-]+)/([\w.-]+)$", self.path)
        if m and m.group(1) in ep.shots:
            rec = ep.take_record(m.group(1), m.group(2))
            if rec and "output" in rec:
                return self._send_file(pathlib.Path(rec["output"]["file"]))
        m = re.match(r"/final/(\d+)$", self.path)
        if m:
            cut = latest_cut(ep)
            if cut and int(m.group(1)) < len(cut["outputs"]):
                return self._send_file(pathlib.Path(cut["outputs"][int(m.group(1))]["file"]))
        return self._send(404, "not found")

    def do_POST(self):
        if not self._host_ok() or self.path not in ("/select", "/confirm"):
            return self._send(403, "forbidden")
        origin = self.headers.get("Origin")
        if origin and origin not in (f"http://127.0.0.1:{self.port}", f"http://localhost:{self.port}"):
            return self._send(403, "forbidden origin")
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            ep = E.Episode(self.episode_dir)
            if self.path == "/confirm":
                AP.confirm(ep)
                return self._send(200, "ok")
            if body.get("shot") not in ep.shots:
                return self._send(400, "unknown shot")
            E.write_selection(ep, body["shot"], str(body["take"]), note=None)
        except SystemExit as e:
            return self._send(400, str(e))
        except (ValueError, KeyError) as e:
            return self._send(400, f"bad request: {e}")
        return self._send(200, "ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--port", type=int, default=8189)
    a = ap.parse_args()
    Handler.episode_dir, Handler.port = str(pathlib.Path(a.episode).resolve()), a.port
    E.Episode(Handler.episode_dir)  # fail early on a bad episode
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"Review page: http://127.0.0.1:{a.port}  (Ctrl+C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
