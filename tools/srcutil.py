"""Shared helpers for the source-survey tools: locate / probe a recording and read frames in ref space.

Reference space = the recording scaled to 1280 px wide (height follows its aspect ratio); every EDL
coordinate is expressed in it, whatever the recording's real resolution.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
REF_W = 1280


def version_paths():
    """(SOURCE, BUILD) of the selected version (VIDEO_VERSION, default latest)."""
    sys.path.insert(0, str(ROOT / "project"))
    import config
    return config.SOURCE, config.BUILD


def source_path(arg=None):
    if arg:
        return Path(arg)
    if os.environ.get("SOURCE"):
        return Path(os.environ["SOURCE"])
    return version_paths()[0]


def out_dir(arg, sub):
    d = Path(arg) if arg else version_paths()[1] / sub
    d.mkdir(parents=True, exist_ok=True)
    return d


def probe(path):
    """dict(w, h, fps, dur, ref_h) of the first video stream."""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True)
    j = json.loads(out.stdout)
    st = j["streams"][0]
    num, den = map(int, st["r_frame_rate"].split("/"))
    w, h = st["width"], st["height"]
    return dict(w=w, h=h, fps=num / den, dur=float(j["format"]["duration"]),
                ref_h=int(round(REF_W * h / w)))


def grab(path, t, width=REF_W, info=None):
    """One BGR frame at source time t, scaled to `width` px wide."""
    info = info or probe(path)
    hh = int(round(width * info["h"] / info["w"]))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", str(path), "-frames:v", "1",
                          "-vf", f"scale={width}:{hh}:flags=area", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    if len(raw) < width * hh * 3:
        raise ValueError(f"no frame at {t:.3f}s")
    return np.frombuffer(raw, np.uint8)[:width * hh * 3].reshape(hh, width, 3).copy()


def read_range(path, t0, t1, width=REF_W, fps=None, gray=True, info=None):
    """(times, frames) for source [t0, t1), scaled to `width`; fps=None keeps the source rate."""
    info = info or probe(path)
    hh = int(round(width * info["h"] / info["w"]))
    rate = fps or info["fps"]
    vf = f"fps={rate},scale={width}:{hh}:flags=area" if fps else f"scale={width}:{hh}:flags=area"
    ch = 1 if gray else 3
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t0):.3f}", "-i", str(path),
                          "-t", f"{t1 - t0:.3f}", "-vf", vf, "-f", "rawvideo",
                          "-pix_fmt", "gray" if gray else "bgr24", "-"], capture_output=True, check=True).stdout
    n = len(raw) // (width * hh * ch)
    frames = np.frombuffer(raw, np.uint8)[:n * width * hh * ch].reshape(n, hh, width, *(() if gray else (3,)))
    return t0 + np.arange(n) / rate, frames


def label(img, text, org=(8, 28), scale=0.8):
    import cv2
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 255, 255), 2, cv2.LINE_AA)
    return img


def sheet(tiles, cols, gap=4):
    """Grid of equally sized BGR tiles."""
    blank = np.zeros_like(tiles[0])
    tiles = list(tiles) + [blank] * (-len(tiles) % cols)
    rows = []
    for i in range(0, len(tiles), cols):
        row = tiles[i:i + cols]
        sep = np.zeros((row[0].shape[0], gap, 3), np.uint8)
        rows.append(np.hstack([x for t in row for x in (t, sep)][:-1]))
    sep = np.zeros((gap, rows[0].shape[1], 3), np.uint8)
    return np.vstack([x for r in rows for x in (r, sep)][:-1])
