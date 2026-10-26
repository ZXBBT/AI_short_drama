"""Stage 8: from an episode brief to a checked shot list.

    PY=~/dev/ComfyUI/.venv/bin/python
    $PY scripts/brief.py validate   episodes/<name>     # check brief.yaml, measure reference faces
    $PY scripts/brief.py scaffold   episodes/<name>     # write episode.yaml without shots (once)
    $PY scripts/brief.py check-plan episodes/<name>     # check the drafted shots against the rules

Format: docs/stage8-brief-format.md. The shots themselves are drafted by Claude from the brief and
approved by the owner; check-plan enforces what Stages 6-7 and the quality track taught us.
Exit code 1 when there are errors.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import statistics
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import episode as E  # noqa: E402

REPO = E.REPO
# (max pixels, max frames) combinations that rendered successfully on this Mac (64 GB, MPS)
PROVEN = [(352 * 608, 124), (480 * 864, 107), (544 * 960, 73), (768 * 1376, 5)]
REF_FACE_MIN_PX, REF_FACE_MIN_Q = 300, 0.5  # owner's selfie reference: 1031 px / 0.70 -> photoreal
LENGTH_TOLERANCE = 0.3
# MiniMax's official prompt structure (h3-prompt-writing skill, MiniMax-AI/MiniMax-H3 @ d21241f)
OFFICIAL_SECTIONS = {"r2v": ["subject_definitions:", "summary:", "retention_analysis:", "detailed_description:",
                             "overall_soundscape:", "non_diegetic_music:"],
                     "base": ["integrated_multimodal_description:", "overall_soundscape:", "non_diegetic_music:"]}
I2V_FIRST_LINE = "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced."
FLF2V_FIRST_LINE = "How the reference pictures align with the target video"
CUT_TIME = re.compile(r"\[Shot \d+\] At (\d+):(\d+(?:\.\d+)?)")
ENV_SUBJECT = re.compile(r"<Subject \d+> is the [^.\n]*\b(?:environment|location|place|room|park|street)\b[^.\n]*<Picture \d+>", re.I)
R2V_MIN_WORDS = 350  # ref-en.txt: "detailed_description is normally 350-500 English words" (generation tasks)


def official_format_problems(p, dialogue_lines):
    """Differences from H3's official prompt format (the h3-prompt-writing guides)."""
    text, out = p["prompt"], []
    kind = "r2v" if p["type"] == "r2v" else "base"
    missing = [s for s in OFFICIAL_SECTIONS[kind] if s not in text]
    if missing:
        out.append(f"not in H3's official prompt format: missing {', '.join(missing)} (see the h3-prompt-writing skill)")
    if kind == "r2v" and "detailed_description:" in text:
        words = len(re.split(r"overall_soundscape:", text.split("detailed_description:", 1)[1])[0].split())
        if words < R2V_MIN_WORDS and "<d>" not in text:  # dialogue-dense shots may be shorter (guide)
            out.append(f"detailed_description has {words} words; the official guide asks for 350-500 for "
                       f"generation (a single shot does not justify a shorter one)")
    if p["type"] == "i2v" and not text.startswith(I2V_FIRST_LINE):
        out.append("I2V prompts start with the official first-frame line: " + I2V_FIRST_LINE)
    if p["type"] == "flf2v" and not text.startswith(FLF2V_FIRST_LINE):
        out.append("FLF2V prompts start with the official alignment line ('How the reference pictures align ...')")
    for line in dialogue_lines:
        if f'"{line}"' in text and f"<d>" not in text:
            out.append(f'dialogue {line!r} is in double quotes: H3 treats quoted text as visible on-screen text (P4 '
                       f'burned-in caption). Write it as (S1) says: <d>[English] {line}</d>')
    dur = p["length"] / 24
    for m in CUT_TIME.finditer(text):
        t_ = int(m.group(1)) * 60 + float(m.group(2))
        if t_ >= dur:
            out.append(f"cut at {m.group(1)}:{m.group(2)} is after the clip ends ({dur:.2f} s)")
    return out


SCREEN_TEXT = re.compile(r"\b(?:screen|interface|app)\b[^.]*\"[^\"]+\"", re.I)
MUSIC_NONE = re.compile(r"non_diegetic_music:\s*N/A", re.I)
TRAINED_MIN_FRAMES = 124  # H3's trained clip length is ~124-362 frames (ComfyUI node tooltip)


def direction_problems(p, sound_in_edit=False):
    """The h3-short-drama-direction skill's checkable rules (V2 revision brief, 2026-10-25)."""
    text, out = p["prompt"], []
    if SCREEN_TEXT.search(text):
        out.append("asks H3 to draw text on a screen/interface (V1 S5B came out unreadable): render the screen as "
                   "flat chroma-key green and composite the graphic with scripts/screen_insert.py")
    if sound_in_edit:
        if "off-screen voiceover" in text:
            out.append("narration is mixed in the edit (brief sound: edit): remove the voice-over from the picture "
                       "render and say his lips stay closed")
        if not MUSIC_NONE.search(text):
            out.append("music is one continuous track in the edit (brief sound: edit): set non_diegetic_music: N/A")
    if p["length"] < 73:
        out.append(f"{p['length']} frames is far below H3's trained length ({TRAINED_MIN_FRAMES}-362); keep "
                   f"performance shots at 90-107 frames")
    return out


TOPS = r"t-?shirts?|shirts?|blouses?|sweaters?|jumpers?|hoodies?|jackets?|coats?|overshirts?|cardigans?|tops?|vests?|tank tops?|polos?|sweatshirts?|blazers?"
BOTTOMS = r"trousers|pants|jeans|skirts?|shorts|leggings|slacks|chinos|joggers"
ONE_PIECE = r"dress(?:es)?|suits?|uniforms?|jumpsuits?|overalls|robes?|gowns?"
SHOES = r"shoes|sneakers|trainers|boots|sandals|heels|loafers|slippers|flats|barefoot"
LOWER_BODY = re.compile(r"full[- ]body|full[- ]length|head to toe|wide shot|wide view|\bwalks?\b|walking|stands? up|"
                        r"gets? up|\bsteps?\b|\blegs?\b|\bknees?\b|\blap\b|\bfeet\b|\bfoot\b", re.I)
FEET = re.compile(r"full[- ]body|full[- ]length|head to toe|\bfeet\b|\bfoot\b|\bshoes?\b|walks?\b|walking", re.I)

OTHERS = re.compile(r"\b(?:nobody|no one|background|behind (?:her|him|them)|in the distance|passers?-?by|"
                    r"other people|a man|a woman|two (?:older )?(?:women|men|people))\b", re.I)


def has(words, text):
    return re.search(rf"\b(?:{words})\b", text, re.I) is not None


def outfit_problems(cid, description, prompt):
    """Outfit completeness (Sunlight P5: the description named only the T-shirt and H3 changed her trousers
    between shots). Whatever the description leaves out, H3 invents per shot, so it drifts."""
    out, desc = [], description or ""
    # sentences about other people (background, "nobody walks across") do not show this character's legs
    prompt = " ".join(s for s in re.split(r"(?<=[.;!?])\s+", prompt) if not OTHERS.search(s))
    one_piece = has(ONE_PIECE, desc)
    if not (has(TOPS, desc) or one_piece):
        out.append(f"character '{cid}': the description names no top (shirt, jacket, dress...); H3 will invent "
                   f"one per shot and it can change between shots")
    if LOWER_BODY.search(prompt) and not (has(BOTTOMS, desc) or one_piece):
        out.append(f"character '{cid}': the shot shows the lower body but the description names no trousers/skirt/"
                   f"dress; add them so they stay the same in every shot (Sunlight P5)")
    if FEET.search(prompt) and not has(SHOES, desc):
        out.append(f"character '{cid}': the shot may show the feet but the description names no shoes")
    return out


def load_brief(ep_dir):
    path = pathlib.Path(ep_dir) / "brief.yaml"
    if not path.exists():
        raise SystemExit(f"{path} not found")
    return E.load_yaml(path), path


def repo_path(p):
    p = pathlib.Path(p)
    return p if p.is_absolute() else REPO / p


# ---------- 8.1 validate ----------

def validate_brief(b, ep_dir):
    errors, warnings, info = [], [], []
    for k in ("episode", "title", "plot", "target", "characters"):
        if not b.get(k):
            errors.append(f"missing '{k}'")
    if b.get("episode") and b["episode"] != pathlib.Path(ep_dir).resolve().name:
        errors.append(f"episode '{b['episode']}' must match the folder name '{pathlib.Path(ep_dir).resolve().name}'")
    t = b.get("target") or {}
    if not isinstance(t.get("length_s"), (int, float)) or not 3 <= t["length_s"] <= 300:
        errors.append("target.length_s must be a number of seconds (3-300)")
    if t.get("aspect", "9:16") not in E.ASPECTS:
        errors.append(f"target.aspect must be one of {sorted(E.ASPECTS)}")
    review = b.get("review") or {}
    if review.get("picks", "owner") not in ("owner", "auto"):
        errors.append("review.picks must be owner or auto")
    if not isinstance(review.get("final", True), bool):
        errors.append("review.final must be true or false")
    budget = b.get("budget") or {}
    if not 1 <= int(budget.get("takes_per_shot", 2)) <= 6:
        errors.append("budget.takes_per_shot must be 1-6")
    images = []
    for kind in ("characters", "locations"):
        for cid, c in (b.get(kind) or {}).items():
            if kind == "characters" and (c or {}).get("kind", "person") not in ("person", "object"):
                errors.append(f"character '{cid}': kind must be person (default) or object")
            if not re.fullmatch(r"[A-Za-z_][\w-]*", str(cid)):
                errors.append(f"{kind} id '{cid}' must be a simple name (letters, digits, _ or -)")
            if not (c or {}).get("description"):
                errors.append(f"{kind[:-1]} '{cid}' needs a description")
            for i, img in enumerate((c or {}).get("images") or []):
                if not repo_path(img).exists():
                    errors.append(f"{kind[:-1]} '{cid}': image not found: {img}")
                elif kind == "characters" and (c or {}).get("kind", "person") == "person":
                    images.append((cid, i, repo_path(img)))  # objects (kind: object, e.g. a product) have no face
    if (b.get("characters") or {}) and not images:
        warnings.append("no character images: H3 will invent the look and it may drift between shots")
    if images:
        import face_check  # noqa: E402 (only needed here; compiles the Swift helper once)
        for (cid, i, path), f in zip(images, face_check.faces_in_images([p for _, _, p in images])):
            label = f"character '{cid}' image {i + 1} ({path.name}): {f['width']:.0f}x{f['height']:.0f}"
            if not f["h"]:
                (warnings if i else errors).append(f"{label}: no face found")
                continue
            info.append(f"{label}, face {f['h']:.0f} px, quality {f['quality']:.2f}")
            if i == 0 and (f["h"] < REF_FACE_MIN_PX or f["quality"] < REF_FACE_MIN_Q):
                warnings.append(f"{label}: main reference face is small or soft (want >= {REF_FACE_MIN_PX} px and "
                                f"quality >= {REF_FACE_MIN_Q}); a large, sharp, real-looking face gives the most "
                                f"realistic results")
    for d in b.get("dialogue") or []:
        if (d or {}).get("character") not in (b.get("characters") or {}):
            errors.append(f"dialogue line for unknown character: {d}")
    return errors, warnings, info


# ---------- scaffold ----------

def scaffold(b, ep_dir, brief_path):
    out = pathlib.Path(ep_dir) / "episode.yaml"
    if out.exists():
        raise SystemExit(f"{out} exists; not overwriting (scaffold only starts a new episode)")
    assets, chars, locs = {}, {}, {}
    for cid, c in (b.get("characters") or {}).items():
        names = []
        for i, img in enumerate(c.get("images") or []):
            a = f"char_{cid}_{i + 1}"; assets[a] = str(img); names.append(a)
        chars[cid] = {"description": " ".join(str(c["description"]).split())}
        if names:
            chars[cid]["refs"] = names[:1]  # one picture per character: extra pictures changed the acting (Q1S)
        if c.get("voice"):
            chars[cid]["voice"] = c["voice"]
        if c.get("kind", "person") != "person":
            chars[cid]["kind"] = c["kind"]
    for lid, loc in (b.get("locations") or {}).items():
        names = []
        for i, img in enumerate(loc.get("images") or []):
            a = f"loc_{lid}_{i + 1}"; assets[a] = str(img); names.append(a)
        locs[lid] = {"description": " ".join(str(loc["description"]).split())}
        if names:
            locs[lid]["plates"] = names  # use only as `first:` of establishing shots (location test L1/L2)
    budget = b.get("budget") or {}
    head = {
        "episode": b["episode"], "title": b["title"], "recipe": "h3_base_v2",
        "defaults": {"aspect": (b.get("target") or {}).get("aspect", "9:16"), "megapixels": 0.4, "duration": 3,
                     "takes": int(budget.get("takes_per_shot", 2)), "max_rerolls": 1},
        "review": {"picks": (b.get("review") or {}).get("picks", "owner"),
                   "final": (b.get("review") or {}).get("final", True)},
        "assets": assets, "characters": chars,
    }
    if locs:
        head["locations"] = locs
    text = (f"# Generated by scripts/brief.py scaffold from {brief_path.name} "
            f"(sha256 {E.sha256(brief_path)[:16]}) on {dt.date.today().isoformat()}.\n"
            "# Shots are drafted by Claude from the brief and approved by the owner; then run\n"
            "#   scripts/brief.py check-plan episodes/" + b["episode"] + "\n"
            + yaml.safe_dump(head, sort_keys=False, allow_unicode=True, width=100)
            + "\nshots: {}\n")
    out.write_text(text)
    return out


# ---------- 8.2 check-plan ----------

def render_rates():
    """Seconds per (pixel x frame) by model family, fitted from this Mac's successful take records."""
    rates = {}
    for f in REPO.glob("runs/*/*__*__*.json"):
        try:
            r = json.loads(f.read_text())
        except ValueError:
            continue
        p = r.get("params") or {}
        if r.get("status") != "success" or not p.get("width") or (r.get("wall_seconds") or 0) < 60:
            continue  # skip cached / tiny runs
        fam = E.FAMILY.get(p.get("type"))
        rates.setdefault(fam, []).append((r["wall_seconds"] - 60) / (p["width"] * p["height"] * p["length"]))
    return {k: statistics.median(v) for k, v in rates.items() if v}


def estimate_minutes(p, rates):
    rate = rates.get(E.FAMILY[p["type"]]) or max(rates.values(), default=2e-5)
    return (60 + rate * p["width"] * p["height"] * p["length"]) / 60


def proven(px, frames):
    return any(px <= mp and frames <= mf for mp, mf in PROVEN)


def check_plan(ep_dir):
    b, _ = load_brief(ep_dir)
    ep = E.Episode(ep_dir)
    errors, warnings = E.validate(ep)
    errors, warnings = list(errors), list(warnings)
    if not ep.shots:
        errors.append("no shots drafted yet")
    plates = {a for loc in ep.locations.values() for a in (loc.get("plates") or [])}
    rates = render_rates()
    total_s, minutes, used_chars, lines = 0.0, 0.0, set(), set()
    for sid, s in ep.shots.items():
        p = ep.params(sid)
        total_s += p["length"] / 24
        takes = len(p["seeds"]) or 1
        minutes += takes * estimate_minutes(p, rates)
        refs = s.get("refs") or []
        # official format with the plate defined as an environment <Subject N> (_multiref M1-M3, 2026-10-26:
        # room/park kept, frontal faces 165-231 px) - the old free-text L1/L2 problems do not apply
        env_subject = "subject_definitions:" in (s.get("prompt") or "") and ENV_SUBJECT.search(s.get("prompt") or "")
        if p["type"] == "r2v":
            chars = [r for r in refs if r in ep.characters]
            others = [r for r in refs if r not in ep.characters]
            if len(chars) != 1 or (others and not env_subject):
                errors.append(f"shot {sid}: R2V must reference exactly one character (two references pulled the "
                              f"camera back and shrank faces: S005, L1); a location picture is fine only in the "
                              f"official format as an environment <Subject N> (_multiref); has {refs}")
            used_chars.update(chars)
        for k in ("first", "last"):
            if isinstance(s.get(k), str) and s[k] in plates and p["type"] != "i2v":
                errors.append(f"shot {sid}: location plates only as the start frame of an I2V establishing shot")
        if any(r in plates for r in refs) and not env_subject:
            errors.append(f"shot {sid}: a location plate as an R2V reference takes over the camera (L2); "
                          f"use it as `first:` of an establishing shot instead")
        for cid in ep.characters:
            if cid in used_chars and p["type"] == "r2v" and cid in refs and "{" + cid + "}" not in (s.get("prompt") or ""):
                warnings.append(f"shot {sid}: prompt should name the character with {{{cid}}} so the wording never drifts")
        if not proven(p["width"] * p["height"], p["length"]):
            errors.append(f"shot {sid}: {p['width']}x{p['height']} x {p['length']} frames has not been rendered "
                          f"successfully on this Mac; use 480x864 (0.4 MP) up to 4.5 s or 352x608 up to 5.2 s")
        shot_lines = [d["line"] for d in s.get("dialogue") or [] if isinstance(d, dict) and d.get("line")]
        lines.update(shot_lines)
        warnings += [f"shot {sid}: {w}" for w in official_format_problems(p, shot_lines)]
        warnings += [f"shot {sid}: {w}" for w in direction_problems(p, sound_in_edit=b.get("sound") == "edit")]
        for cid, c in ep.characters.items():
            if c.get("kind") != "object" and (cid in refs or "{" + cid + "}" in (s.get("prompt") or "")):
                warnings += [f"shot {sid}: {w}" for w in outfit_problems(cid, c.get("description"), p["prompt"])]
    for cid in (b.get("characters") or {}):
        if cid not in ep.characters:
            errors.append(f"brief character '{cid}' is missing from episode.yaml (run scaffold for a new episode)")
        elif ep.shots and not any(cid in (s.get("refs") or []) or "{" + cid + "}" in (s.get("prompt") or "")
                                  for s in ep.shots.values()):
            warnings.append(f"character '{cid}' appears in no shot")
    for d in b.get("dialogue") or []:
        if d.get("line") not in lines:
            warnings.append(f"brief dialogue {d.get('character')}: {d.get('line')!r} is in no shot's dialogue")
    target = (b.get("target") or {}).get("length_s", 0)
    if ep.shots and target and abs(total_s - target) > LENGTH_TOLERANCE * target:
        warnings.append(f"shots add up to {total_s:.1f} s before trims; the brief asks for about {target} s")
    hours = (b.get("budget") or {}).get("max_render_hours")
    if hours and minutes / 60 > hours:
        warnings.append(f"estimated rendering {minutes / 60:.1f} h exceeds budget.max_render_hours {hours}")
    return errors, warnings, {"shots": len(ep.shots), "length_s": round(total_s, 1), "render_hours": round(minutes / 60, 1),
                              "rates": {k: f"{v * 1e6:.2f} s per megapixel-frame" for k, v in rates.items()}}


def report(errors, warnings, info):
    for i in info if isinstance(info, list) else [json.dumps(info)]:
        print("info:", i)
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    print("OK" if not errors else f"{len(errors)} error(s)")
    return 1 if errors else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["validate", "scaffold", "check-plan"])
    ap.add_argument("episode_dir")
    a = ap.parse_args()
    if a.cmd == "check-plan":
        sys.exit(report(*check_plan(a.episode_dir)))
    b, path = load_brief(a.episode_dir)
    errors, warnings, info = validate_brief(b, a.episode_dir)
    if a.cmd == "validate" or errors:
        sys.exit(report(errors, warnings, info))
    print("wrote", scaffold(b, a.episode_dir, path).resolve().relative_to(REPO))


if __name__ == "__main__":
    main()
