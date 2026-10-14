"""Timestamped contact sheet of a source range, optionally cropped (ref coords) -- for picking exact src times.

    python3 tools/source_sheet.py 53.5 58 --step 0.25
    python3 tools/source_sheet.py 106 111 --step 0.5 --crop 190 110 1090 550 --cols 3
"""
import argparse

import cv2
import numpy as np

from srcutil import REF_W, grab, label, out_dir, probe, sheet, source_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("t0", type=float)
    ap.add_argument("t1", type=float)
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--crop", nargs=4, type=int, metavar=("X0", "Y0", "X1", "Y1"))
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--tile", type=int, default=480, help="tile width (px)")
    ap.add_argument("--src")
    ap.add_argument("--out", help="output jpg (default build/<module>/<version>/probe/sheet_<t0>-<t1>.jpg)")
    args = ap.parse_args()

    src = source_path(args.src)
    info = probe(src)
    x0, y0, x1, y1 = args.crop or (0, 0, REF_W, info["ref_h"])
    tiles = []
    for t in np.arange(args.t0, args.t1 + 1e-6, args.step):
        f = grab(src, float(t), REF_W, info)[y0:y1, x0:x1]
        f = cv2.resize(f, (args.tile, int(f.shape[0] * args.tile / f.shape[1])), interpolation=cv2.INTER_AREA)
        tiles.append(label(np.ascontiguousarray(f), f"{t:.2f}", (6, 24), 0.7))
    path = args.out or str(out_dir(None, "probe") / f"sheet_{args.t0:06.2f}-{args.t1:06.2f}.jpg")
    cv2.imwrite(path, sheet(tiles, args.cols), [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(path)


if __name__ == "__main__":
    main()
