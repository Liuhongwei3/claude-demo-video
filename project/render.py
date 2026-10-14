"""Programmatic renderer: source screen recording + EDL -> 1080x1920 promo video (no audio).

    python3 project/render.py                      # full render -> build/<version>/video.mp4
    python3 project/render.py --stills 3.5 7.9     # PNG previews -> build/<version>/stills/
    VIDEO_VERSION=v1 python3 project/render.py     # re-render an earlier version
"""
import argparse
import json
import math
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "project"))
from config import BUILD, LAYOUT, SOURCE, edl, script  # noqa: E402

L = LAYOUT
W, H, FPS = edl.OUT_W, edl.OUT_H, edl.FPS
REF_W = 1280

FONT_BOLD = ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 2)
FONT_REG = ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 2)

# Palette sampled from the product UI (sidebar navy, primary blue)
BLUE = tuple(L.get("accent", (243, 136, 30)))    # BGR of #1e88f3
BLUE_LIGHT = tuple(int(c + (255 - c) * 0.45) for c in BLUE) if "accent" in L else (255, 190, 110)
NAVY = (40, 26, 14)            # deep background
UI_BG = tuple(L.get("ui_bg", (247, 246, 245)))
CARD_X_CENTER = W // 2
CARD_RADIUS = L["card_radius"]


# ----------------------------------------------------------------------------- helpers
def clamp(x, a, b):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x, 0.0, 1.0)
    return x * x * x * (x * (6 * x - 15) + 10)


def ease_out(x):
    x = clamp(x, 0.0, 1.0)
    return 1 - (1 - x) ** 3


def piecewise(points, t):
    if t <= points[0][0]:
        return points[0][1]
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * (t - t0) / max(t1 - t0, 1e-9)
    return points[-1][1]


def interp_cam(keys, t):
    params = {}
    for k in ("cx", "cy", "s", "h", "w", "ccy"):
        pts, last = [], None
        for key in keys:
            if k in key:
                last = key[k]
            if last is not None:
                pts.append((key["t"], last))
        if not pts:
            continue
        if t <= pts[0][0]:
            params[k] = pts[0][1]
            continue
        val = pts[-1][1]
        for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
            if t <= t1:
                u = ease((t - t0) / max(t1 - t0, 1e-9))
                if k == "s":
                    val = math.exp(math.log(v0) + (math.log(v1) - math.log(v0)) * u)
                else:
                    val = v0 + (v1 - v0) * u
                break
        params[k] = val
    params.setdefault("w", L["card_w"])
    params.setdefault("ccy", L["card_cy"])
    return params


def fade_window(t, t_in, t_out, fin=0.3, fout=0.25):
    if t < t_in or t > t_out:
        return 0.0
    return min(ease((t - t_in) / fin), ease((t_out - t) / fout) if t_out - t < fout else 1.0)


def blend_color(dst, mask, color, alpha=1.0):
    """dst uint8 HxWx3, mask float HxW in [0,1]."""
    if alpha <= 0:
        return
    m = (mask * alpha)[..., None]
    dst[:] = (dst * (1 - m) + np.asarray(color, np.float32) * m).astype(np.uint8)


def blend_rgba(dst, rgba, x, y, alpha=1.0):
    """Alpha-blend an RGBA (BGRA order) patch onto dst at integer (x, y), clipped."""
    if alpha <= 0:
        return
    h, w = rgba.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 <= x0 or y1 <= y0:
        return
    patch = rgba[y0 - y:y1 - y, x0 - x:x1 - x]
    a = patch[..., 3:4].astype(np.float32) / 255.0 * alpha
    reg = dst[y0:y1, x0:x1]
    reg[:] = (reg * (1 - a) + patch[..., :3].astype(np.float32) * a).astype(np.uint8)


def round_rect_mask(w, h, r, ss=3):
    """Anti-aliased filled rounded-rectangle mask (float32, h x w)."""
    w, h = max(1, int(round(w))), max(1, int(round(h)))
    r = int(min(r, w / 2, h / 2))
    W2, H2, R2 = w * ss, h * ss, r * ss
    m = np.zeros((H2, W2), np.uint8)
    if R2 > 0:
        cv2.rectangle(m, (R2, 0), (W2 - R2 - 1, H2 - 1), 255, -1)
        cv2.rectangle(m, (0, R2), (W2 - 1, H2 - R2 - 1), 255, -1)
        for cx, cy in ((R2, R2), (W2 - R2 - 1, R2), (R2, H2 - R2 - 1), (W2 - R2 - 1, H2 - R2 - 1)):
            cv2.circle(m, (cx, cy), R2, 255, -1, cv2.LINE_AA)
    else:
        m[:] = 255
    return cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0


@lru_cache(maxsize=64)
def card_mask(w, h):
    return round_rect_mask(w, h, CARD_RADIUS)


@lru_cache(maxsize=64)
def card_shadow(w, h):
    pad = 90
    q = 4
    m = np.zeros(((h + 2 * pad) // q, (w + 2 * pad) // q), np.float32)
    cv2.rectangle(m, (pad // q, pad // q), ((pad + w) // q, (pad + h) // q), 1.0, -1)
    m = cv2.GaussianBlur(m, (0, 0), 36 / q)
    return cv2.resize(m, (w + 2 * pad, h + 2 * pad), interpolation=cv2.INTER_LINEAR), pad


def stroke_mask(w, h, r, t):
    outer = round_rect_mask(w, h, r)
    inner = np.zeros_like(outer)
    if w > 2 * t and h > 2 * t:
        inner[int(t):int(t) + int(round(h - 2 * t)), int(t):int(t) + int(round(w - 2 * t))] = \
            round_rect_mask(w - 2 * t, h - 2 * t, max(0, r - t))[:int(round(h - 2 * t)), :int(round(w - 2 * t))]
    return np.clip(outer - inner, 0, 1)


# ----------------------------------------------------------------------------- text
@lru_cache(maxsize=256)
def font(path_idx, size):
    return ImageFont.truetype(path_idx[0], size, index=path_idx[1])


@lru_cache(maxsize=256)
def text_rgba(text, size, color=(255, 255, 255), bold=True, spacing=0, shadow=0, gradient=None):
    """Render a single line of text to a BGRA numpy patch."""
    f = font(FONT_BOLD if bold else FONT_REG, size)
    widths = [f.getlength(ch) for ch in text]
    tw = int(sum(widths) + spacing * max(0, len(text) - 1)) + 4
    asc, desc = f.getmetrics()
    th = asc + desc + 4
    pad = shadow * 3
    img = Image.new("L", (tw + 2 * pad, th + 2 * pad), 0)
    d = ImageDraw.Draw(img)
    x = pad + 2
    for ch, cw in zip(text, widths):
        d.text((x, pad + 2), ch, font=f, fill=255)
        x += cw + spacing
    a = np.asarray(img, np.float32) / 255.0
    rgba = np.zeros(a.shape + (4,), np.float32)
    if gradient:
        c0, c1 = (np.asarray(c, np.float32) for c in gradient)
        u = np.linspace(0, 1, a.shape[1])[None, :, None]
        rgba[..., :3] = c0 * (1 - u) + c1 * u
    else:
        rgba[..., :3] = color[::-1]
    rgba[..., 3] = a
    if shadow:
        sh = cv2.GaussianBlur(a, (0, 0), shadow)
        sh = np.roll(sh, shadow, axis=0)
        out_a = a + sh * 0.55 * (1 - a)
        rgb = (rgba[..., :3] * a[..., None] + np.array([12, 8, 4], np.float32) * (sh * 0.55 * (1 - a))[..., None])
        rgba[..., :3] = rgb / np.maximum(out_a[..., None], 1e-6)
        rgba[..., 3] = out_a
    out = np.empty(rgba.shape, np.uint8)
    out[..., :3] = np.clip(rgba[..., :3], 0, 255)
    out[..., 3] = np.clip(rgba[..., 3] * 255, 0, 255)
    return out


@lru_cache(maxsize=128)
def pill_rgba(text, size=26, fg=(255, 255, 255), bg=(30, 136, 243), bg_alpha=0.96,
              border=None, padx=16, pady=7, bold=True, radius=None):
    t = text_rgba(text, size, fg, bold)
    tw, th = t.shape[1], t.shape[0]
    w, h = tw + 2 * padx, th + 2 * pady - 6
    r = radius if radius is not None else h // 2
    m = round_rect_mask(w, h, r)
    out = np.zeros((h, w, 4), np.float32)
    out[..., :3] = bg[::-1]
    out[..., 3] = m * bg_alpha
    if border:
        sm = stroke_mask(w, h, r, 2)
        bcol = np.asarray(border[::-1], np.float32)
        out[..., :3] = out[..., :3] * (1 - sm[..., None]) + bcol * sm[..., None]
        out[..., 3] = np.maximum(out[..., 3], sm)
    ta = t[..., 3:4].astype(np.float32) / 255.0
    oy = (h - th) // 2
    reg = out[oy:oy + th, padx:padx + tw]
    reg[..., :3] = reg[..., :3] * (1 - ta) + t[..., :3] * ta
    reg[..., 3:4] = reg[..., 3:4] + ta * (1 - reg[..., 3:4])
    res = np.empty(out.shape, np.uint8)
    res[..., :3] = np.clip(out[..., :3], 0, 255)
    res[..., 3] = np.clip(out[..., 3] * 255, 0, 255)
    return res


# ----------------------------------------------------------------------------- source
def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True)
    st = json.loads(out.stdout)["streams"][0]
    num, den = map(int, st["r_frame_rate"].split("/"))
    return st["width"], st["height"], num / den


class SegReader:
    """Forward-only frame reader for one source time range (keeps memory low even for 4K)."""

    def __init__(self, path, t_start, t_end, work_w, work_h, src_size, fps):
        self.t_start, self.fps = t_start, fps
        self.w, self.h = work_w, work_h
        vf = [] if (work_w, work_h) == src_size else ["-vf", f"scale={work_w}:{work_h}:flags=lanczos"]
        cmd = ["ffmpeg", "-loglevel", "error", "-ss", f"{max(0, t_start):.3f}", "-i", str(path),
               "-t", f"{t_end - t_start + 0.4:.3f}", *vf, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=work_w * work_h * 3 * 2)
        self.idx, self.frame = -1, None

    def get(self, t_src):
        want = max(0, int(round((t_src - self.t_start) * self.fps)))
        n = self.w * self.h * 3
        while self.idx < want:
            buf = self.proc.stdout.read(n)
            if len(buf) < n:
                break
            self.frame = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3)
            self.idx += 1
        return self.frame

    def close(self):
        self.proc.kill()


# ----------------------------------------------------------------------------- background
def make_background():
    y = np.linspace(0, 1, H)[:, None]
    top = np.array([34, 20, 10], np.float32)
    mid = np.array([58, 36, 20], np.float32)
    g = np.where(y < 0.5, top + (mid - top) * (y / 0.5), mid + (top - mid) * ((y - 0.5) / 0.5))
    bg = np.repeat(g[:, None, :], W, axis=1).reshape(H, W, 3).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    glow = np.exp(-(((xx - W / 2) / 620) ** 2 + ((yy - 980) / 760) ** 2))
    bg += glow[..., None] * np.array([120, 60, 12], np.float32) * 0.55
    grid = np.zeros((H, W), np.float32)
    grid[::60, :] = 1
    grid[:, ::60] = 1
    bg += grid[..., None] * 7 * (0.4 + 0.6 * glow[..., None])
    vign = np.exp(-(((xx - W / 2) / 900) ** 2 + ((yy - H / 2) / 1400) ** 2))
    bg *= (0.72 + 0.28 * vign)[..., None]
    return np.clip(bg, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------------------- shot renderer
class ShotRenderer:
    def __init__(self, shot, src_info):
        self.shot = shot
        self.src_path, (self.sw, self.sh, self.sfps) = SOURCE, src_info
        self.k = min(self.sw / REF_W, 2.0)
        # reference space is 1280 px wide; its height follows the recording's aspect ratio
        self.ww, self.wh = int(round(REF_W * self.k)), int(round(REF_W * self.sh / self.sw * self.k))
        srcs = [p[1] for p in shot["src"]]
        self.reader = None
        self.src_range = (min(srcs), max(srcs))

    def src_time(self, t):
        return piecewise(self.shot["src"], t)

    def frame(self, t):
        if self.reader is None:
            self.reader = SegReader(self.src_path, self.src_range[0], self.src_range[1],
                                    self.ww, self.wh, (self.sw, self.sh), self.sfps)
        ts = self.src_time(t)
        f = self.reader.get(ts)
        f = f.copy()
        blurs = [dict(rect=r) for r in getattr(edl, "GLOBAL_BLUR", [])] + \
                [e for e in self.shot["fx"] if e["kind"] == "blur"]
        for b in blurs:
            if b.get("src_from") is not None and ts < b["src_from"]:
                continue
            if b.get("src_to") is not None and ts > b["src_to"]:
                continue
            x0, y0, x1, y1 = (int(round(v * self.k)) for v in b["rect"])
            reg = f[y0:y1, x0:x1]
            if reg.size:
                small = cv2.resize(reg, (max(1, reg.shape[1] // 10), max(1, reg.shape[0] // 10)),
                                   interpolation=cv2.INTER_AREA)
                f[y0:y1, x0:x1] = cv2.GaussianBlur(cv2.resize(small, (reg.shape[1], reg.shape[0]),
                                                              interpolation=cv2.INTER_LINEAR), (0, 0), 3)
        return f

    def safe(self, t):
        rect = getattr(edl, "SAFE_REF", None) or (0, 0, REF_W, self.wh / self.k)
        for t0, r in self.shot.get("safe", []):
            if t >= t0:
                rect = r
        return rect

    def geom(self, t):
        cam = interp_cam(self.shot["cam"], t)
        return dict(w=cam["w"], h=cam["h"], ccy=cam["ccy"])

    def view(self, t, geom=None, zoom=1.0):
        cam = interp_cam(self.shot["cam"], t)
        if geom:
            cam.update(geom)
        scale = 1.0
        alpha = 1.0
        enter = self.shot.get("enter")
        if enter and t - self.shot["t0"] < enter:
            p = ease_out((t - self.shot["t0"]) / enter)
            scale, alpha = 0.92 + 0.08 * p, ease((t - self.shot["t0"]) / (enter * 0.8))
        w, h = cam["w"] * scale, cam["h"] * scale
        s = cam["s"] * scale * zoom
        cw, ch = w / s, h / s
        sx0, sy0, sx1, sy1 = self.safe(t)
        cx = clamp(cam["cx"], sx0 + cw / 2, sx1 - cw / 2) if cw < sx1 - sx0 else (sx0 + sx1) / 2
        cy = clamp(cam["cy"], sy0 + ch / 2, sy1 - ch / 2) if ch < sy1 - sy0 else (sy0 + sy1) / 2
        return dict(w=int(round(w)), h=int(round(h)), s=s, x0=cx - cw / 2, y0=cy - ch / 2,
                    ccy=cam["ccy"], alpha=alpha, safe=(sx0, sy0, sx1, sy1))

    def to_card(self, v, x, y):
        return (x - v["x0"]) * v["s"], (y - v["y0"]) * v["s"]

    def render_content(self, t, v):
        src = self.frame(t)
        k = self.k
        ratio = k / v["s"]
        if ratio > 1.15:
            f = 1.05 / ratio
            src = cv2.resize(src, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
            k = k * f
        M = np.array([[k / v["s"], 0, k * v["x0"]], [0, k / v["s"], k * v["y0"]]], np.float64)
        content = cv2.warpAffine(src, M, (v["w"], v["h"]), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP,
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=UI_BG)
        sx0, sy0, sx1, sy1 = v["safe"]
        u0, v0 = self.to_card(v, sx0, sy0)
        u1, v1 = self.to_card(v, sx1, sy1)
        if v0 > 0:
            content[:int(math.ceil(v0))] = UI_BG
        if v1 < v["h"]:
            content[int(v1):] = UI_BG
        if u0 > 0:
            content[:, :int(math.ceil(u0))] = UI_BG
        if u1 < v["w"]:
            content[:, int(u1):] = UI_BG
        return content

    def active_boxes(self, t):
        """Yield (rect_ref, alpha, fx) for highlight-like effects at time t."""
        for e in self.shot["fx"]:
            if e["kind"] == "hl":
                a = fade_window(t, e["t_in"], e["t_out"], L["hl_fade_in"], L["hl_fade_out"])
                if a > 0:
                    yield e["rect"], a, e, ease_out((t - e["t_in"]) / 0.35)
            elif e["kind"] == "sweep":
                a = fade_window(t, e["t_in"], e["t_out"], L["hl_fade_in"], L["hl_fade_out"])
                if a > 0:
                    path = e["path"]
                    rect = path[0][1]
                    for (t0, r0), (t1, r1) in zip(path, path[1:]):
                        if t >= t1:
                            rect = r1
                        elif t >= t0:
                            u = ease((t - t0) / (t1 - t0))
                            rect = tuple(a0 + (a1 - a0) * u for a0, a1 in zip(r0, r1))
                            break
                    yield rect, a, e, 1.0

    def draw_fx(self, content, t, v):
        boxes = list(self.active_boxes(t))
        # spotlight: dim everything outside the focused boxes
        spot = max([a * e.get("spot", 0) for _, a, e, _ in boxes] + [0])
        if spot > 0:
            keep = np.zeros(content.shape[:2], np.float32)
            for rect, a, e, _ in boxes:
                if not e.get("spot"):
                    continue
                u0, v0 = self.to_card(v, rect[0], rect[1])
                u1, v1 = self.to_card(v, rect[2], rect[3])
                pad = 10
                x0, y0 = int(u0 - pad), int(v0 - pad)
                m = round_rect_mask(u1 - u0 + 2 * pad, v1 - v0 + 2 * pad, 16)
                m = cv2.GaussianBlur(m, (0, 0), 6)
                _paste_max(keep, m, x0, y0)
            dim = (1 - keep) * spot
            blend_color(content, dim, (60, 40, 25), 1.0)
        for rect, a, e, grow in boxes:
            u0, v0 = self.to_card(v, rect[0], rect[1])
            u1, v1 = self.to_card(v, rect[2], rect[3])
            pad = 6 + 14 * (1 - grow)
            u0, v0, u1, v1 = u0 - pad, v0 - pad, u1 + pad, v1 + pad
            bw, bh = u1 - u0, v1 - v0
            if bw < 4 or bh < 4:
                continue
            gpad = 18
            glow = np.zeros((int(bh + 2 * gpad), int(bw + 2 * gpad)), np.float32)
            sm = stroke_mask(bw, bh, 12, 3.5)
            glow[gpad:gpad + sm.shape[0], gpad:gpad + sm.shape[1]] = sm
            glow_b = cv2.GaussianBlur(glow, (0, 0), 7)
            _blend_mask_at(content, glow_b, int(u0) - gpad, int(v0) - gpad, BLUE, 0.55 * a)
            fill = round_rect_mask(bw, bh, 12)
            _blend_mask_at(content, fill, int(u0), int(v0), BLUE, 0.07 * a)
            _blend_mask_at(content, sm, int(u0), int(v0), BLUE, 0.95 * a)
            if e.get("label"):
                p = pill_rgba(e["label"], 26)
                ph, pw = p.shape[:2]
                pos = e.get("label_pos", "top")
                if pos == "top":
                    px, py = u0, v0 - ph - 10
                elif pos == "bottom":
                    px, py = u0, v1 + 10
                elif pos == "left":
                    px, py = u0 - pw - 12, v0 + 8
                else:
                    px, py = u1 + 12, v0 + 8
                px = clamp(px, 12, content.shape[1] - pw - 12)
                py = clamp(py, 12, content.shape[0] - ph - 12)
                blend_rgba(content, p, int(px), int(py), a)
        for e in self.shot["fx"]:
            if e["kind"] != "ripple":
                continue
            dt = t - e["t"]
            if -0.12 <= dt <= 0.75:
                u, w_ = self.to_card(v, e["x"], e["y"])
                pre = ease((dt + 0.12) / 0.12) if dt < 0 else 1.0
                p = ease_out(max(0, dt) / 0.7)
                _draw_ring(content, u, w_, 10 + 46 * p, 4.0, BLUE, 0.9 * (1 - p) * pre)
                _draw_disc(content, u, w_, 16 * (1 - 0.4 * p), (255, 255, 255), 0.55 * (1 - p) * pre)
                _draw_disc(content, u, w_, 9 * (1 - 0.3 * p), BLUE, 0.75 * (1 - p) * pre)
        dim = self.shot.get("dim")
        if dim:
            d = piecewise(dim, t)
            if d > 0:
                content[:] = (content.astype(np.float32) * (1 - d) + np.array(NAVY, np.float32) * d).astype(np.uint8)

    def render(self, t, canvas, geom=None, zoom=1.0):
        v = self.view(t, geom, zoom)
        content = self.render_content(t, v)
        self.draw_fx(content, t, v)
        w, h = v["w"], v["h"]
        x0 = int(round(CARD_X_CENTER - w / 2))
        y0 = int(round(v["ccy"] - h / 2))
        sh, pad = card_shadow(w, h)
        _blend_mask_at(canvas, sh, x0 - pad, y0 - pad + 26, (8, 4, 2), 0.7 * v["alpha"])
        m = card_mask(w, h)
        reg_x0, reg_y0 = max(0, x0), max(0, y0)
        reg_x1, reg_y1 = min(W, x0 + w), min(H, y0 + h)
        mm = m[reg_y0 - y0:reg_y1 - y0, reg_x0 - x0:reg_x1 - x0][..., None] * v["alpha"]
        cc = content[reg_y0 - y0:reg_y1 - y0, reg_x0 - x0:reg_x1 - x0]
        reg = canvas[reg_y0:reg_y1, reg_x0:reg_x1]
        reg[:] = (reg * (1 - mm) + cc * mm).astype(np.uint8)
        ring = stroke_mask(w + 4, h + 4, CARD_RADIUS + 2, 2)
        _blend_mask_at(canvas, ring, x0 - 2, y0 - 2, (255, 200, 140), 0.35 * v["alpha"])

    def close(self):
        if self.reader:
            self.reader.close()
            self.reader = None


def _paste_max(dst, m, x, y):
    h, w = m.shape
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 > x0 and y1 > y0:
        dst[y0:y1, x0:x1] = np.maximum(dst[y0:y1, x0:x1], m[y0 - y:y1 - y, x0 - x:x1 - x])


def _blend_mask_at(dst, m, x, y, color, alpha):
    if alpha <= 0:
        return
    h, w = m.shape
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 > x0 and y1 > y0:
        blend_color(dst[y0:y1, x0:x1], m[y0 - y:y1 - y, x0 - x:x1 - x], color, alpha)


def _draw_ring(img, x, y, r, t, color, alpha):
    if alpha <= 0:
        return
    s = 4
    R = int(r + t + 4)
    patch = np.zeros((2 * R * s, 2 * R * s), np.uint8)
    cv2.circle(patch, (R * s, R * s), int(r * s), 255, int(t * s), cv2.LINE_AA)
    m = cv2.resize(patch, (2 * R, 2 * R), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    _blend_mask_at(img, m, int(x) - R, int(y) - R, color, alpha)


def _draw_disc(img, x, y, r, color, alpha):
    if alpha <= 0:
        return
    s = 4
    R = int(r + 3)
    patch = np.zeros((2 * R * s, 2 * R * s), np.uint8)
    cv2.circle(patch, (R * s, R * s), int(r * s), 255, -1, cv2.LINE_AA)
    m = cv2.resize(patch, (2 * R, 2 * R), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    _blend_mask_at(img, m, int(x) - R, int(y) - R, color, alpha)


# ----------------------------------------------------------------------------- global overlays
def load_vo():
    p = BUILD / "vo/durations.json"
    durs = json.loads(p.read_text()) if p.exists() else [{"duration": 3.5}] * len(script.VO_LINES)
    out = []
    for i, (line, d) in enumerate(zip(script.VO_LINES, durs)):
        start = line["start"]
        end = start + d["duration"] + 0.25
        if i + 1 < len(script.VO_LINES):
            end = min(end, script.VO_LINES[i + 1]["start"] - 0.08)
        end = min(end, getattr(script, "SUBTITLE_HIDE_AFTER", {}).get(i, 1e9), edl.DURATION)
        rows = getattr(script, "SUBTITLE_BREAKS", {}).get(i) or [line["text"].rstrip("。，")]
        out.append(dict(start=start, end=end, rows=rows, text=line["text"]))
    return out


def draw_headlines(canvas, t):
    heads = script.HEADLINES
    fin, fout = L["head_fade_in"], L["head_fade_out"]
    for i, (t_in, t_out, kicker, title) in enumerate(heads):
        if not (t_in - 0.01 <= t <= t_out):
            continue
        a_in = ease((t - t_in) / fin)
        a_out = ease((t_out - t) / fout) if t_out - t < fout else 1.0
        dy = int(26 * (1 - ease_out((t - t_in) / (fin + 0.05))))
        prev_same = i > 0 and heads[i - 1][2] == kicker and abs(heads[i - 1][1] - t_in) < 0.02
        next_same = i + 1 < len(heads) and heads[i + 1][2] == kicker and abs(heads[i + 1][0] - t_out) < 0.02
        ka = min(1.0 if prev_same else a_in, 1.0 if next_same else a_out)
        kp = pill_rgba(kicker, L["kicker_size"], fg=(214, 234, 255), bg=(30, 136, 243), bg_alpha=0.18,
                       border=(30, 136, 243), padx=20, pady=9)
        blend_rgba(canvas, kp, (W - kp.shape[1]) // 2, L["kicker_y"] + (0 if prev_same else dy), ka)
        size = L["hook_title_size"] if i == 0 else L["title_size"]
        tt = text_rgba(title, size, (255, 255, 255), True, 2, 4)
        blend_rgba(canvas, tt, (W - tt.shape[1]) // 2, L["title_y"] + dy, min(a_in, a_out))


def draw_subtitles(canvas, t, vo):
    fd = L["sub_fade"]
    for sub in vo:
        if not (sub["start"] - 0.05 <= t <= sub["end"]):
            continue
        a = min(ease((t - sub["start"] + 0.05) / fd), ease((sub["end"] - t) / fd))
        rows = [text_rgba(r, L["sub_size"], (255, 255, 255), True, 1, 2) for r in sub["rows"]]
        lh = L["sub_line_h"]
        bw = max(r.shape[1] for r in rows) + 56
        bh = lh * len(rows) + 30
        box = np.zeros((bh, bw, 4), np.uint8)
        box[..., :3] = (24, 14, 8)
        box[..., 3] = (round_rect_mask(bw, bh, 22) * 150).astype(np.uint8)
        bx, by = (W - bw) // 2, L["sub_top"]
        blend_rgba(canvas, box, bx, by, a)
        for i, r in enumerate(rows):
            blend_rgba(canvas, r, (W - r.shape[1]) // 2, by + 12 + i * lh, a)


def draw_closing(canvas, t):
    t0 = L.get("closing_t", 25.45)
    if t < t0 - 0.15:
        return
    labels = script.CLOSING_CHAIN
    pw, ph, gap = 120, 66, 36
    total = len(labels) * pw + (len(labels) - 1) * gap
    x = (W - total) // 2
    y = L["closing_chain_y"]
    for i, lab in enumerate(labels):
        t_i = t0 + i * L.get("closing_step", 0.16)
        p = ease_out((t - t_i) / 0.4)
        if p <= 0:
            x += pw + gap
            continue
        if i:
            lt = ease((t - t_i + 0.08) / 0.25)
            line = np.zeros((6, gap), np.float32)
            cv2.line(line, (4, 3), (int(4 + (gap - 8) * lt), 3), 1.0, 2, cv2.LINE_AA)
            _blend_mask_at(canvas, line, x - gap, y + ph // 2 - 3, BLUE_LIGHT, 0.9)
            if lt > 0.9:
                tri = np.zeros((14, 10), np.uint8)
                cv2.fillPoly(tri, [np.array([[0, 1], [9, 7], [0, 13]])], 255, cv2.LINE_AA)
                _blend_mask_at(canvas, tri.astype(np.float32) / 255, x - 10, y + ph // 2 - 7, BLUE_LIGHT, 0.9)
        pill = pill_rgba(lab, 32, fg=(255, 255, 255), bg=(30, 136, 243),
                         bg_alpha=0.22 if i < len(labels) - 1 else 0.95,
                         border=(110, 190, 255), padx=(pw - 2 * 32 - 4) // 2, pady=14, radius=20)
        sc = 0.88 + 0.12 * p
        pr = cv2.resize(pill, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        blend_rgba(canvas, pr, int(x + (pw - pr.shape[1]) / 2), int(y + (ph - pr.shape[0]) / 2), p)
        x += pw + gap
    t1, t2 = t0 + L.get("closing_l1_delay", 0.70), t0 + L.get("closing_l2_delay", 1.10)
    a1 = ease((t - t1) / 0.5)
    if a1 > 0:
        l1 = text_rgba(script.CLOSING_LINE_1, 50, (214, 228, 245), False, 2, 2)
        blend_rgba(canvas, l1, (W - l1.shape[1]) // 2,
                   L["closing_l1_y"] + int(18 * (1 - ease_out((t - t1) / 0.6))), a1)
    a2 = ease((t - t2) / 0.55)
    if a2 > 0:
        l2 = text_rgba(script.CLOSING_LINE_2, 68, bold=True, spacing=3, shadow=3,
                       gradient=((255, 220, 140), (255, 160, 60)))
        y2 = L["closing_l2_y"] + int(18 * (1 - ease_out((t - t2) / 0.6)))
        blend_rgba(canvas, l2, (W - l2.shape[1]) // 2, y2, a2)
        bar_w = int(140 * ease_out((t - t2 - 0.25) / 0.6))
        if bar_w > 2:
            bar = round_rect_mask(bar_w, 6, 3)
            _blend_mask_at(canvas, bar, (W - bar_w) // 2, L["closing_l2_y"] + 116, BLUE, 0.95)


# ----------------------------------------------------------------------------- main loop
def active_shots(t):
    out = []
    for i, sh in enumerate(edl.SHOTS):
        if sh["t0"] <= t < sh["t1"] or (i == len(edl.SHOTS) - 1 and t >= sh["t0"]):
            out.append(i)
    return out


def render_morph(t, renderers, bg, a, b):
    """Overlap of two shots as one card: its frame glides from shot a's geometry to shot b's while
    the content cross-dissolves, with an optional slight push-through zoom."""
    sb = edl.SHOTS[b]
    p = ease((t - sb["t0"]) / max(sb.get("xfade", 0), 1e-6))
    ga, gb = renderers[a].geom(t), renderers[b].geom(t)
    g = {k: ga[k] + (gb[k] - ga[k]) * p for k in ga}
    xz = sb.get("xzoom", L.get("xzoom", 0.0))
    out = bg.copy()
    renderers[a].render(t, out, g, 1 + xz * p)
    if p <= 0:
        return out
    inc = bg.copy()
    renderers[b].render(t, inc, g, 1 + xz * (1 - p))
    return cv2.addWeighted(out, 1 - p, inc, p, 0) if p < 1 else inc


def render_frame(t, renderers, bg, vo):
    idx = active_shots(t)
    layers = []
    if L.get("morph") and len(idx) >= 2 and t < edl.SHOTS[idx[-1]]["t0"] + edl.SHOTS[idx[-1]].get("xfade", 0):
        frame = render_morph(t, renderers, bg, idx[-2], idx[-1])
        draw_headlines(frame, t)
        draw_subtitles(frame, t, vo)
        draw_closing(frame, t)
        return outro(frame, t)
    for i in idx:
        sh = edl.SHOTS[i]
        canvas = bg.copy()
        renderers[i].render(t, canvas)
        xf = sh.get("xfade", 0)
        p = ease((t - sh["t0"]) / xf) if xf and t < sh["t0"] + xf else 1.0
        layers.append((canvas, p))
    if not layers:
        frame = bg.copy()
    else:
        frame = layers[0][0]
        for canvas, p in layers[1:]:
            frame = cv2.addWeighted(frame, 1 - p, canvas, p, 0) if p < 1 else canvas
    draw_headlines(frame, t)
    draw_subtitles(frame, t, vo)
    draw_closing(frame, t)
    return outro(frame, t)


def outro(frame, t):
    fo = L.get("outro_fade", 0)
    left = edl.DURATION - 1 / FPS - t
    if fo and left < fo:
        k = ease(max(left, 0) / fo)
        frame = (frame.astype(np.float32) * k).astype(np.uint8)
    return frame


def main():
    global SOURCE
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", nargs="*", type=float)
    ap.add_argument("--out", default=str(BUILD / "video.mp4"))
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=edl.DURATION)
    ap.add_argument("--source", default=str(SOURCE))
    args = ap.parse_args()

    SOURCE = Path(args.source)
    BUILD.mkdir(parents=True, exist_ok=True)
    src_info = probe(SOURCE)
    print("source", src_info)
    bg = make_background()
    vo = load_vo()

    if args.stills:
        d = BUILD / "stills"
        d.mkdir(exist_ok=True)
        for t in args.stills:
            renderers = [ShotRenderer(s, src_info) for s in edl.SHOTS]
            img = render_frame(t, renderers, bg, vo)
            cv2.imwrite(str(d / f"still_{t:05.2f}.png"), img)
            for r in renderers:
                r.close()
        print("stills ->", d)
        return

    renderers = [ShotRenderer(s, src_info) for s in edl.SHOTS]
    n0, n1 = int(round(args.start * FPS)), int(round(args.end * FPS))
    enc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
         "-crf", "16", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
         "-x264-params", "keyint=60:min-keyint=30", "-movflags", "+faststart", args.out],
        stdin=subprocess.PIPE)
    t_start = time.time()
    for n in range(n0, n1):
        t = n / FPS
        for i, sh in enumerate(edl.SHOTS):
            if t > sh["t1"] + 0.05 and renderers[i].reader:
                renderers[i].close()
        frame = render_frame(t, renderers, bg, vo)
        enc.stdin.write(frame.tobytes())
        if n % 60 == 0:
            el = time.time() - t_start
            print(f"frame {n}/{n1}  t={t:5.2f}s  {el:6.1f}s elapsed", flush=True)
    enc.stdin.close()
    enc.wait()
    for r in renderers:
        r.close()
    print("video ->", args.out, f"({time.time() - t_start:.0f}s)")


if __name__ == "__main__":
    main()
