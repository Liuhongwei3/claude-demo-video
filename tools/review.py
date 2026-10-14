"""Contact sheets of a rendered cut, for QA and for the storyboard deliverable.

    python3 tools/review.py sheets [--step 0.5]       # whole cut, one frame every step -> review/sheet-NN.jpg
    python3 tools/review.py transitions                # each shot boundary, 0.1 s apart -> review/xfade-<shot>.jpg
    python3 tools/review.py storyboard [t ...]         # one frame per shot (or given times) -> deliverables/<module>/<version>/storyboard.jpg

The video defaults to build/<module>/<version>/video.mp4 (picture only, available before muxing); pass --video
to review the delivered mp4 instead.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

from srcutil import ROOT, label, sheet

sys.path.insert(0, str(ROOT / "project"))
import config  # noqa: E402


def frames_at(video, times, w):
    out = []
    for t in times:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                              "-vf", f"scale={w}:-2:flags=area", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                             capture_output=True, check=True).stdout
        h = len(raw) // (w * 3)
        out.append(np.frombuffer(raw, np.uint8)[:w * h * 3].reshape(h, w, 3).copy())
    return out


def save(img, path, q=85):
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, q])
    print(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["sheets", "transitions", "storyboard"])
    ap.add_argument("times", nargs="*", type=float)
    ap.add_argument("--video", default=str(config.BUILD / "video.mp4"))
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--per-sheet", type=int, default=24)
    ap.add_argument("--cols", type=int, default=8)
    ap.add_argument("--tile", type=int, default=270)
    ap.add_argument("--out")
    args = ap.parse_args()
    video = Path(args.video)
    edl = config.edl
    shots = edl.SHOTS
    out = Path(args.out) if args.out else config.BUILD / "review"

    if args.mode == "sheets":
        times = np.arange(0, edl.DURATION - 1e-3, args.step)
        for k in range(0, len(times), args.per_sheet):
            ts = times[k:k + args.per_sheet]
            tiles = [label(f, f"{t:.1f}") for f, t in zip(frames_at(video, ts, args.tile), ts)]
            save(sheet(tiles, args.cols), out / f"sheet-{k // args.per_sheet:02d}.jpg")

    elif args.mode == "transitions":
        for prev, sh in zip(shots, shots[1:]):
            xf = sh.get("xfade", 0.0)
            ts = np.arange(sh["t0"] - 0.2, sh["t0"] + xf + 0.25, 0.1)
            tiles = [label(f, f"{t:.2f}") for f, t in zip(frames_at(video, ts, args.tile), ts)]
            save(sheet(tiles, min(args.cols, len(tiles))), out / f"xfade-{prev['id']}-{sh['id']}.jpg")

    else:
        ts = args.times or [min(s["t1"] - 0.3, s["t0"] + 0.65 * (s["t1"] - s["t0"])) for s in shots]
        tiles = [label(f, f"{t:.1f}s") for f, t in zip(frames_at(video, ts, args.tile), ts)]
        cols = args.cols if len(tiles) > args.cols else len(tiles)
        save(sheet(tiles, cols, gap=0), Path(args.out) if args.out else config.DELIVER / "storyboard.jpg")


if __name__ == "__main__":
    main()
