"""Dump source frames in ref space with a coordinate grid, for measuring rects / camera centres.

    python3 tools/frame.py 104.5 110.6                         # whole frame, grid every 50 ref px
    python3 tools/frame.py 107.9 --crop 190 110 1090 550       # zoomed crop (2x) of a modal
    python3 tools/frame.py 5.4 --src source/other/source.mp4 --out /tmp/probe

Output: <out>/f_<t>.png (default build/<version>/probe). Read the PNG and take coordinates off the grid.
"""
import argparse

import cv2
import numpy as np

from srcutil import REF_W, grab, out_dir, probe, source_path


def draw_grid(img, x0, y0, scale, step=50):
    h, w = img.shape[:2]
    over = img.copy()
    for gx in range((x0 // step + 1) * step, x0 + int(w / scale) + 1, step):
        x = int(round((gx - x0) * scale))
        cv2.line(over, (x, 0), (x, h), (0, 0, 255) if gx % 100 == 0 else (0, 140, 255), 1)
        if gx % 100 == 0:
            cv2.putText(img, str(gx), (x + 2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)
    for gy in range((y0 // step + 1) * step, y0 + int(h / scale) + 1, step):
        y = int(round((gy - y0) * scale))
        cv2.line(over, (0, y), (w, y), (0, 0, 255) if gy % 100 == 0 else (0, 140, 255), 1)
        if gy % 100 == 0:
            cv2.putText(img, str(gy), (2, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)
    cv2.addWeighted(over, 0.35, img, 0.65, 0, img)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("times", nargs="+", type=float)
    ap.add_argument("--src")
    ap.add_argument("--out")
    ap.add_argument("--crop", nargs=4, type=int, metavar=("X0", "Y0", "X1", "Y1"))
    ap.add_argument("--scale", type=float, help="zoom of the crop (default 2, or 1 without --crop)")
    ap.add_argument("--no-grid", action="store_true")
    args = ap.parse_args()

    src = source_path(args.src)
    info = probe(src)
    out = out_dir(args.out, "probe")
    x0, y0, x1, y1 = args.crop or (0, 0, REF_W, info["ref_h"])
    scale = args.scale or (2.0 if args.crop else 1.0)
    for t in args.times:
        f = grab(src, t, int(REF_W * scale), info)
        f = np.ascontiguousarray(f[int(y0 * scale):int(y1 * scale), int(x0 * scale):int(x1 * scale)])
        if not args.no_grid:
            draw_grid(f, x0, y0, scale)
        path = out / f"f_{t:07.3f}{'_crop' if args.crop else ''}.png"
        cv2.imwrite(str(path), f)
        print(path)


if __name__ == "__main__":
    main()
