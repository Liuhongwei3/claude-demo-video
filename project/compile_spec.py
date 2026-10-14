"""Compile a video spec (功能描述 + 镜头清单 + 旁白) into the edl.py / script.py the renderer reads.

    VIDEO=inventory/v1 python3 project/compile_spec.py              # synthesise VO if needed, then time everything
    VIDEO=inventory/v1 python3 project/compile_spec.py --estimate   # no TTS: estimated durations, for drafts

Reads  project/versions/<module>/<version>/spec.yaml (format: project/templates/spec.yaml)
Writes project/versions/<module>/<version>/{script.py, edl.py}   (generated -- edit spec.yaml instead)
       deliverables/<module>/<version>/shot-list.md
The house style (layout, colours, rhythm, voice, soundtrack) comes from project/style.py.

Timing model: every beat is one voice-over line plus the shots that start during it. Lines follow each
other with the style's gaps; a shot starts `lead` before its line (plus `at`). If a shot would get less
than `min` seconds on screen, the next line waits. Source playback, ripples, headlines, subtitle breaks,
SFX, music resolve and the closing animation are all derived from that timeline.
"""
import argparse
import json
import pprint
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "project"))
import config  # noqa: E402
import style as house  # noqa: E402

WARN = []
CLOSING_HOLD = 0.7      # subtitles of the closing line give way to the closing copy this long after it appears


class SpecError(SystemExit):
    pass


def warn(msg):
    WARN.append(msg)


def r3(x):
    if isinstance(x, float):
        return round(x, 3)
    if isinstance(x, (list, tuple)):
        return type(x)(r3(v) for v in x)
    if isinstance(x, dict):
        return {k: r3(v) for k, v in x.items()}
    return x


def clamp(x, a, b):
    return max(a, min(b, x))


# ----------------------------------------------------------------------------- spec helpers
class Spec:
    def __init__(self, data):
        self.d = data
        self.style = house.merged(data.get("style"))
        self.regions = {k: tuple(v) for k, v in (data.get("regions") or {}).items()}
        self.sections = data.get("sections") or []
        if not self.sections:
            raise SpecError("spec.yaml: `sections` is empty")
        if self.sections[-1].get("kind") != "closing":
            raise SpecError("spec.yaml: the last section must have `kind: closing`")

    def rect(self, v, where):
        if isinstance(v, str):
            if v not in self.regions:
                raise SpecError(f"{where}: unknown region '{v}' (define it under `regions:`)")
            return self.regions[v]
        if isinstance(v, (list, tuple)) and len(v) == 4:
            return tuple(float(x) for x in v)
        raise SpecError(f"{where}: expected a region name or [x0, y0, x1, y1], got {v!r}")


def section_title(sec):
    return sec.get("title") or {"hook": "开场钩子", "closing": "价值收束"}.get(sec.get("kind"), "")


def split_subtitle(text, max_chars):
    t = text.rstrip("。，")
    if len(t) <= max_chars:
        return None
    for marks in ("，？！；：", "、"):
        cands = [i + 1 for i, c in enumerate(t[:-1]) if c in marks]
        if cands:
            best = min(cands, key=lambda i: abs(i - len(t) / 2))
            return [t[:best].rstrip("，、"), t[best:]]
    warn(f"subtitle longer than {max_chars} chars and no comma to split at: {t}")
    return None


# ----------------------------------------------------------------------------- voice-over
def flatten_lines(spec):
    V = spec.style["voice"]
    lines = []
    for si, sec in enumerate(spec.sections):
        beats = sec.get("beats") or []
        if not beats:
            raise SpecError(f"section {si + 1} ({sec.get('title', '')}): no beats")
        for bi, beat in enumerate(beats):
            if not beat.get("vo"):
                raise SpecError(f"section {si + 1} beat {bi + 1}: `vo` (voice-over line) is required")
            lines.append(dict(text=beat["vo"], say=beat.get("tts", beat["vo"]), sid=beat.get("sid", V["sid"]),
                              speed=beat.get("speed"), si=si, bi=bi, beat=beat, sec=sec))
    for i, ln in enumerate(lines):
        if ln["speed"] is None:
            ln["speed"] = V["edge_speed"] if i in (0, len(lines) - 1) else V["speed"]
    return lines


def write_script_stub(spec, lines):
    """script.py with untimed lines: enough for voiceover.py to synthesise them."""
    V = spec.style["voice"]
    vo = [dict(start=0.0, text=ln["text"], speed=ln["speed"], **({"say": ln["say"]} if ln["say"] != ln["text"] else {}),
               **({"sid": ln["sid"]} if ln["sid"] != V["sid"] else {})) for ln in lines]
    body = (f"TITLE = {spec.d.get('module', config.MODULE)!r}\nVOICE_SID = {V['sid']}\nTRIM_PAD = {V['trim_pad']}\n"
            f"VO_LINES = {pprint.pformat(vo, width=110, sort_dicts=False)}\n")
    (config.DIR / "script.py").write_text('"""GENERATED stub (voice-over only) -- see compile_spec.py."""\n' + body,
                                          encoding="utf-8")


def durations(spec, lines, estimate):
    if estimate:
        return [round(sum("\u4e00" <= c <= "\u9fff" for c in ln["say"]) / 4.9 * 1.42 / ln["speed"] + 0.15, 3)
                for ln in lines]
    path = config.BUILD / "vo/durations.json"

    def cached():
        if not path.exists():
            return None
        info = json.loads(path.read_text())
        ok = len(info) == len(lines) and all(
            m.get("say") == ln["say"] and m.get("sid") == ln["sid"] and abs(m.get("speed", 0) - ln["speed"]) < 1e-6
            for m, ln in zip(info, lines))
        return [m["duration"] for m in info] if ok else None

    d = cached()
    if d is None:
        write_script_stub(spec, lines)
        subprocess.run([sys.executable, str(ROOT / "project/voiceover.py")], check=True)
        d = cached()
    return d


# ----------------------------------------------------------------------------- camera / source
def cam_from(spec, v, where):
    """Camera params from a region / rect ("show this area") or an explicit {cx, cy, s, h} dict."""
    C, card_w = spec.style["camera"], spec.style["layout"]["card_w"]
    if isinstance(v, dict):
        cam = {k: float(v[k]) for k in ("cx", "cy", "s") if k in v}
        if "h" in v:
            cam["h"] = float(v["h"])
        return cam
    x0, y0, x1, y1 = spec.rect(v, where)
    w, h = x1 - x0, y1 - y0
    s = min(card_w / w, C["card_h_max"] / h)
    if s > C["s_max"]:
        warn(f"{where}: area {w:.0f}x{h:.0f} would need zoom {s:.2f}; capped at {C['s_max']}")
        s = C["s_max"]
    return dict(cx=(x0 + x1) / 2, cy=(y0 + y1) / 2, s=s, h=clamp(h * s, C["card_h_min"], C["card_h_max"]))


def src_points(sh, t0, t1, where):
    src = sh["src"]
    if isinstance(src, (int, float)):
        return [(t0, float(src)), (t1, float(src))]
    a, b = map(float, src)
    if b < a:
        raise SpecError(f"{where}: src end before start")
    delay = float(sh.get("delay", 0.0))
    avail = t1 - t0 - delay
    if avail <= 0:
        raise SpecError(f"{where}: delay {delay} longer than the shot")
    speed = sh.get("speed")
    speed = float(speed) if speed not in (None, "fit") else clamp((b - a) / avail, 0.55, 1.0) if b > a else 1.0
    play = (b - a) / speed
    if play > avail + 1e-6:
        b2 = a + avail * speed
        warn(f"{where}: shot is {avail:.2f}s but src {a}-{b} needs {play:.2f}s at {speed:.2f}x; "
             f"cut at src {b2:.2f} (raise `min`, add `pause`, or shorten src)")
        b, play = b2, avail
    p0 = t1 - play if sh.get("align") == "end" else t0 + delay
    pts = [(t0, a)]
    if p0 > t0 + 1e-3:
        pts.append((p0, a))
    pts.append((p0 + play, b))
    if t1 > p0 + play + 1e-3:
        pts.append((t1, b))
    return pts


def src_to_cut(pts, ts, where):
    for (ta, sa), (tb, sb) in zip(pts, pts[1:]):
        if sb > sa and sa - 1e-6 <= ts <= sb + 1e-6:
            return ta + (ts - sa) / (sb - sa) * (tb - ta)
    raise SpecError(f"{where}: source time {ts} is not played in this shot (plays {pts[0][1]:.2f}-{pts[-1][1]:.2f})")


# ----------------------------------------------------------------------------- timeline
def schedule(spec, lines, durs):
    T = spec.style["timing"]
    starts, placed = [], []          # placed: dict(spec, t0, sec, si, first_in_section, beat line index)
    for i, ln in enumerate(lines):
        beat = ln["beat"]
        if i == 0:
            start = T["first_line"]
        else:
            start = starts[-1] + durs[i - 1] + (T["section_gap"] if ln["bi"] == 0 else T["gap"])
        start += float(beat.get("pause", 0.0))
        shots = beat.get("shots") or []
        ats = [float(s.get("at", 0.0)) for s in shots]
        for k in range(1, len(shots)):
            need = float(shots[k - 1].get("min", T["min_shot"]))
            if ats[k] - ats[k - 1] < need:
                warn(f"line {i + 1}: shot {shots[k].get('id')} starts {ats[k] - ats[k - 1]:.2f}s after "
                     f"{shots[k - 1].get('id')} (< min {need}); moved")
                ats[k] = ats[k - 1] + need
        if shots and placed and not (i == 0):
            prev = placed[-1]
            first_t0 = start - T["lead"] + ats[0]
            need = prev["t0"] + float(prev["spec"].get("min", T["min_shot"])) - first_t0
            if need > 0:
                start += need
        starts.append(start)
        for k, sh in enumerate(shots):
            t0 = 0.0 if (i == 0 and k == 0) else start - T["lead"] + ats[k]
            placed.append(dict(spec=sh, t0=t0, si=ln["si"], line=i,
                               first_in_section=not any(p["si"] == ln["si"] for p in placed)))
    if not placed or placed[0]["t0"] != 0.0:
        raise SpecError("the first beat must contain the opening shot")
    ends = [s + d for s, d in zip(starts, durs)]
    closing_line = next(i for i, ln in enumerate(lines) if ln["si"] == len(spec.sections) - 1)
    closing_t = starts[closing_line] + T["closing_after"]
    duration = max(ends[-1] + T["tail"], closing_t + T["min_tail"])
    for j, p in enumerate(placed):
        nxt = placed[j + 1] if j + 1 < len(placed) else None
        p["xfade"] = 0.0 if j == 0 else float(p["spec"].get(
            "xfade", T["section_xfade"] if p["first_in_section"] else T["xfade"]))
        p["tc"] = nxt["t0"] if nxt else duration           # cut point: the next shot starts dissolving in
    for j, p in enumerate(placed):
        nxt = placed[j + 1] if j + 1 < len(placed) else None
        p["t1"] = nxt["t0"] + nxt["xfade"] if nxt else duration
    return starts, ends, placed, closing_t, duration


def rel(p, x):
    """Shot-relative time: >= 0 from the shot start, < 0 back from its cut point."""
    x = float(x)
    return p["t0"] + x if x >= 0 else p["tc"] + x


def build_shot(spec, p, prev_shot, closing):
    sh, where = p["spec"], f"shot {p['spec'].get('id', '?')}"
    T, C = spec.style["timing"], spec.style["camera"]
    if "src" not in sh:
        raise SpecError(f"{where}: `src` is required")
    t0, t1, tc = p["t0"], p["t1"], p["tc"]
    out = dict(id=sh.get("id", f"S{p['index'] + 1}"), t0=t0, t1=t1)
    if p["xfade"]:
        out["xfade"] = p["xfade"]
    if p["index"] == 0:
        out["enter"] = T["hook_enter"]
    if sh.get("within"):
        out["safe"] = [(0.0, spec.rect(sh["within"], where))]
    pts = src_points(sh, t0, t1, where)
    out["src"] = pts

    # camera
    if sh.get("cam"):
        cam = [dict(t=rel(p, t), **cam_from(spec, v, where)) for t, v in sh["cam"]]
    else:
        view = sh.get("view", sh.get("within", "app" if "app" in spec.regions else None))
        if view is None and not sh.get("match"):
            raise SpecError(f"{where}: set `view` (region / rect to show), `cam`, or `match: prev`")
        first = dict(prev_shot["cam"][-1]) if sh.get("match") == "prev" and prev_shot else None
        if first:
            first.pop("t")
        start = first or cam_from(spec, view, where)
        cam = [dict(t=t0, **start)]
        if sh.get("to"):
            m0, m1 = sh.get("move", [0.0, -0.0001])
            end = cam_from(spec, sh["to"], where)
            if rel(p, m0) > t0 + 1e-3:
                cam.append(dict(t=rel(p, m0), **start))
            cam.append(dict(t=min(rel(p, m1), tc), **end))
    if sh.get("match") == "prev":
        out["xzoom"] = 0.0
    if closing:
        k = C["closing"]
        last = {key: v for key, v in cam[-1].items() if key != "t"}
        cs0, cs1 = closing["shrink"]
        cam = [c for c in cam if c["t"] < cs0 - 1e-3]
        cam.append(dict(t=cs0, **last))
        cam.append(dict(t=cs1, cx=last["cx"], cy=last["cy"] + 22, s=last["s"] * k["s_factor"],
                        h=k["h"], w=k["w"], ccy=k["ccy"]))
        for c in cam[:-1]:
            c.setdefault("w", spec.style["layout"]["card_w"])
            c.setdefault("ccy", spec.style["layout"]["card_cy"])
        out["dim"] = [(cs0, 0.0), (cs1, k["dim"])]
    out["cam"] = cam

    fx, sfx = [], []
    for b in sh.get("blur") or []:
        if isinstance(b, dict):
            a_, b_ = (b.get("src") or [None, None])
            fx.append(dict(kind="blur", rect=spec.rect(b["rect"], where), src_from=a_, src_to=b_))
        else:
            fx.append(dict(kind="blur", rect=spec.rect(b, where), src_from=None, src_to=None))
    for b in spec.d.get("privacy") or []:
        if b.get("src"):
            a_, b_ = map(float, b["src"])
            lo, hi = min(q[1] for q in pts), max(q[1] for q in pts)
            if a_ <= hi and b_ >= lo:
                fx.append(dict(kind="blur", rect=spec.rect(b["rect"], "privacy"), src_from=a_, src_to=b_))
    for h in sh.get("highlight") or []:
        if "src_at" in h:
            a_, b_ = (src_to_cut(pts, float(x), where) for x in h["src_at"])
        else:
            at = h.get("at", [0.5])
            a_ = rel(p, at[0])
            b_ = rel(p, at[1]) if len(at) > 1 else t1
        fx.append(dict(kind="hl", t_in=a_, t_out=b_, rect=spec.rect(h["rect"], where), label=h.get("label"),
                       label_pos=h.get("pos", "top"), spot=float(h.get("spot", 0.0)), color=None))
        if h.get("chime"):
            sfx.append((a_, "chime"))
    sw = sh.get("sweep")
    if sw:
        if sw.get("nodes"):
            first_t = rel(p, sw.get("at", 0.9))
            step, pad = float(sw.get("step", 0.33)), 6
            path = [(first_t + i * step, (x0 - pad, y0 - pad, x1 + pad, y1 + pad))
                    for i, (x0, y0, x1, y1) in enumerate(spec.rect(n, where) for n in sw["nodes"])]
            t_out = path[-1][0] + 0.3
            if sw.get("chime", True):
                sfx.append((first_t, "chime_soft"))
            fx.append(dict(kind="sweep", t_in=first_t - 0.05, t_out=t_out, path=path,
                           spot=float(sw.get("spot", 0.18)), label=sw.get("label")))
        else:
            path = [(rel(p, t), spec.rect(r, where)) for t, r in sw["path"]]
            fx.append(dict(kind="sweep", t_in=path[0][0] - 0.1, t_out=path[-1][0] + 0.6, path=path,
                           spot=float(sw.get("spot", 0.0)), label=sw.get("label")))
    clicks = sh.get("click") or []
    if clicks and not isinstance(clicks[0], (list, tuple)):
        clicks = [clicks]
    for c in clicks:
        ts, x, y = map(float, c)
        tcut = src_to_cut(pts, ts, where)
        fx.append(dict(kind="ripple", t=tcut, x=x, y=y))
        sfx.append((tcut, "tick"))
    for t, kind in sh.get("sfx") or []:
        sfx.append((rel(p, t), kind))
    out["fx"] = fx
    return out, sfx


def place_whoosh(t_shot, onsets, clear, after):
    for c in (t_shot - 0.15, t_shot - 0.3, t_shot - 0.45):
        if c > after and not any(-0.1 <= o - c < clear for o in onsets):
            return c
    return None


# ----------------------------------------------------------------------------- outputs
def emit(path, doc, assigns):
    parts = [f'"""{doc}"""\n']
    for name, val in assigns:
        parts.append(f"{name} = {pprint.pformat(r3(val), width=110, sort_dicts=False)}\n")
    path.write_text("\n".join(parts), encoding="utf-8")


def shot_list_md(spec, shots, placed, lines, starts, heads, duration):
    d = spec.d
    out = [f"# 镜头清单 · {d.get('out_name', config.MODULE)}.mp4（{config.VIDEO}）", ""]
    if d.get("source_note"):
        out += [f"- 原片：{d['source_note']}"]
    out += [f"- 成片：1080×1920 竖屏，30 fps，{duration:.1f} 秒。",
            "- 坐标：以原片缩放到 1280 px 宽的参考坐标描述；s 为放大倍数（成片像素 / 参考像素）。",
            "- 转场：形变叠化，同一页面相邻镜头同机位衔接。", "",
            "| 镜头 | 成片时间 | 原片时间 | 展示的真实功能 | 裁切 / 放大 | 屏幕标题 · 旁白 | 敏感信息 / 缺陷处理 |",
            "|---|---|---|---|---|---|---|"]
    for sh, p in zip(shots, placed):
        sp = p["spec"]
        s0, s1 = sh["src"][0][1], sh["src"][-1][1]
        played = [(b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(sh["src"], sh["src"][1:]) if b[1] > a[1]]
        src = f"{s0:.2f}（定格）" if s0 == s1 else f"{s0:.2f}–{s1:.2f}"
        if played and abs(played[0] - 1) > 0.03:
            src += f"（{played[0]:.2f} 倍速）"
        cams = sh["cam"]
        crop = f"s {cams[0]['s']:.2f}" + (f"→{cams[-1]['s']:.2f}" if abs(cams[-1]["s"] - cams[0]["s"]) > 0.01 else "")
        crop += f"，卡片 {cams[-1].get('w', spec.style['layout']['card_w']):.0f}×{cams[-1]['h']:.0f}"
        if sp.get("within"):
            crop += f"，限定在 {sp['within']} 内"
        if sp.get("match") == "prev":
            crop += "，与上一镜头同机位衔接"
        head = next((h[3] for h in reversed(heads) if h[0] <= sh["t0"] + 0.3), "")
        vo = [ln["text"] for ln, st in zip(lines, starts) if sh["t0"] - 0.2 <= st < p["tc"] - 0.2]
        blurs = sum(1 for e in sh["fx"] if e["kind"] == "blur")
        note = "；".join(x for x in [sp.get("note", ""), f"模糊 {blurs} 处" if blurs else ""] if x) or "—"
        sec = section_title(spec.sections[p["si"]])
        out.append(f"| {sh['id']} {sec} | {sh['t0']:.2f}–{sh['t1']:.2f} | {src} | {sp.get('shows', '')} | {crop} | "
                   f"{head} ·「{''.join(vo)}」 | {note} |")
    if d.get("unused"):
        out += ["", "## 未使用的原片段落", "", "| 原片时间 | 内容 | 舍弃原因 |", "|---|---|---|"]
        out += [f"| {u['src'][0]}–{u['src'][1]} | {u.get('what', '')} | {u.get('why', '')} |" for u in d["unused"]]
    if d.get("gaps"):
        out += ["", "## 素材缺口", ""] + [f"- {g}" for g in d["gaps"]]
    if d.get("privacy"):
        out += ["", "## 全片隐私处理", ""] + [f"- {b.get('note', '模糊')}：{b['rect']}"
                                         + (f"（原片 {b['src'][0]}–{b['src'][1]} s）" if b.get("src") else "")
                                         for b in d["privacy"]]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimate", action="store_true", help="estimate VO durations instead of running TTS")
    args = ap.parse_args()
    path = config.DIR / "spec.yaml"
    if not path.exists():
        sys.exit(f"no spec.yaml in {config.DIR.relative_to(ROOT)}")
    spec = Spec(yaml.safe_load(path.read_text(encoding="utf-8")))
    S, T = spec.style, spec.style["timing"]

    lines = flatten_lines(spec)
    durs = durations(spec, lines, args.estimate)
    starts, ends, placed, closing_t, duration = schedule(spec, lines, durs)
    shrink = (closing_t - (T["closing_shrink"] - 0.15), closing_t + 0.15)
    closing_si = len(spec.sections) - 1

    shots, sfx = [], [(0.0, "whoosh_soft")]
    for j, p in enumerate(placed):
        p["index"] = j
        is_closing = p["si"] == closing_si and j == len(placed) - 1
        sh, fx_sfx = build_shot(spec, p, shots[-1] if shots else None, dict(shrink=shrink) if is_closing else None)
        shots.append(sh)
        sfx += fx_sfx
    onsets = starts
    for p in placed[1:]:
        if p["first_in_section"]:
            w = place_whoosh(p["t0"], onsets, T["whoosh_clear"], after=max(t for t, _ in sfx if t <= p["t0"]) + 0.3)
            if w is not None:
                sfx.append((w, "whoosh_soft"))
    sfx += [(shrink[0] + 0.05, "riser_end"), (shrink[1], "chime_end")]
    sfx.sort()

    # headlines
    changes = []        # (t, kicker, headline)
    n_feature = 0
    for si, sec in enumerate(spec.sections):
        kind = sec.get("kind", "feature")
        if kind == "feature":
            n_feature += 1
        kicker = sec.get("kicker") or (spec.d.get("module", config.MODULE) if kind == "hook" else
                                       f"{n_feature:02d}  {sec.get('title', '')}" if kind == "feature" else "闭环")
        for i, ln in enumerate(lines):
            if ln["si"] != si or not (ln["bi"] == 0 or ln["beat"].get("headline")):
                continue
            head = ln["beat"].get("headline") or sec.get("headline")
            if not head:
                raise SpecError(f"section {si + 1}: `headline` is required")
            first = next((p for p in placed if p["line"] == i), None)
            t = 0.15 if i == 0 else (first["t0"] if first else starts[i] - T["lead"]) + T["headline_delay"]
            changes.append((t, kicker, head))
    heads = []
    for k, (t, kicker, head) in enumerate(changes):
        t_out = changes[k + 1][0] if k + 1 < len(changes) else shrink[0] + 0.05
        heads.append((t, t_out, kicker, head))

    closing = spec.sections[-1]
    chain = closing.get("chain") or []
    cl = closing.get("closing_lines") or []
    if len(cl) != 2:
        raise SpecError("closing section: `closing_lines` must have exactly two lines")

    V, maxc = S["voice"], S["subtitle"]["max_chars"]
    vo_lines, breaks = [], {}
    for i, (ln, st) in enumerate(zip(lines, starts)):
        item = dict(start=st, text=ln["text"], speed=ln["speed"])
        if ln["say"] != ln["text"]:
            item["say"] = ln["say"]
        if ln["sid"] != V["sid"]:
            item["sid"] = ln["sid"]
        vo_lines.append(item)
        br = ln["beat"].get("break")
        if br is None:
            br = split_subtitle(ln["text"], maxc)
        if br:
            breaks[i] = list(br)
    n_chars = sum(sum("\u4e00" <= c <= "\u9fff" for c in ln["text"]) for ln in lines)
    rate = n_chars / sum(durs)
    sections_names = [f"镜头{ln['si'] + 1} · {section_title(ln['sec'])}" for ln in lines]
    emit(config.DIR / "script.py",
         f"GENERATED by project/compile_spec.py from spec.yaml -- edit spec.yaml, not this file.\n\n"
         f"{spec.d.get('module', '')} · {config.VIDEO}",
         [("TITLE", spec.d.get("module", config.MODULE)), ("OUT_NAME", spec.d.get("out_name", config.MODULE)),
          ("VOICE_SID", V["sid"]), ("TRIM_PAD", V["trim_pad"]),
          ("VOICE_DESC", f"{V['desc']} | 语速约 {rate:.1f} 字/秒"),
          ("VO_LINES", vo_lines), ("VO_SECTIONS", sections_names), ("SUBTITLE_BREAKS", breaks),
          ("SUBTITLE_HIDE_AFTER", {len(lines) - 1: closing_t + CLOSING_HOLD}),
          ("HEADLINES", heads), ("CLOSING_CHAIN", chain), ("CLOSING_LINE_1", cl[0]), ("CLOSING_LINE_2", cl[1])])

    layout = dict(S["layout"], closing_t=closing_t,
                  accent=house.hex_to_bgr(S["colors"]["accent"]), ui_bg=house.hex_to_bgr(S["colors"]["ui_bg"]))
    music = dict(S["music"], resolve_bar=max(3, round(shrink[0] / 2.4)))
    global_blur = [spec.rect(b["rect"], "privacy") for b in spec.d.get("privacy") or [] if not b.get("src")]
    if not spec.d.get("source"):
        raise SpecError("spec.yaml: `source` (recording path) is required")
    emit(config.DIR / "edl.py",
         f"GENERATED by project/compile_spec.py from spec.yaml -- edit spec.yaml, not this file.\n\n"
         f"{spec.d.get('module', '')} · {config.VIDEO}",
         [("SOURCE", spec.d["source"]), ("FPS", 30), ("DURATION", round(duration, 2)), ("OUT_W", 1080), ("OUT_H", 1920),
          ("SAFE_REF", spec.regions.get("app")), ("GLOBAL_BLUR", global_blur), ("LAYOUT", layout), ("MUSIC", music),
          ("SHOTS", shots), ("SFX", sfx)])

    config.DELIVER.mkdir(parents=True, exist_ok=True)
    (config.DELIVER / "shot-list.md").write_text(
        shot_list_md(spec, shots, placed, lines, starts, heads, duration), encoding="utf-8")

    print(f"{config.VIDEO}: {len(lines)} lines, {len(shots)} shots, {duration:.2f} s"
          f"{' (estimated VO)' if args.estimate else ''}, closing copy at {closing_t:.2f} s")
    for (st, en), ln in zip(zip(starts, ends), lines):
        print(f"  {st:6.2f}-{en:6.2f}  {ln['text']}")
    for sh in shots:
        print(f"  {sh['id']:>5} {sh['t0']:6.2f}-{sh['t1']:6.2f}  src {sh['src'][0][1]:.2f}-{sh['src'][-1][1]:.2f}")
    for w in WARN:
        print("WARNING:", w)


if __name__ == "__main__":
    main()
