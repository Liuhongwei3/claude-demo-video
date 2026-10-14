"""First look at a new recording: split it into stable screen states and the changes between them.

    python3 tools/survey.py                                   # source of the selected version
    python3 tools/survey.py --src source/foo/source.mp4 --out build/foo/survey

Writes <out>/survey.md (table of states, flags) and <out>/survey-NN.jpg (labelled thumbnails, 24 per
sheet). Read the sheets, then fill the material map in the version's notes: which page each state is,
where the clicks / loads / modals are, what is sensitive. Flags:
  blank    near-uniform frame (white screen, loading, recorder chrome) -> never use
  bright+  brightness jumped up from the previous state -> possibly a skeleton / loading state
"""
import argparse

import cv2
import numpy as np

from srcutil import grab, label, out_dir, probe, read_range, sheet, source_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--out")
    ap.add_argument("--fps", type=float, default=10)
    ap.add_argument("--th", type=float, default=0.6, help="mean abs diff (0-255, 320 px gray) that counts as change")
    ap.add_argument("--min-len", type=float, default=0.6, help="shortest stable state to list (s)")
    ap.add_argument("--thumb", type=int, default=480)
    args = ap.parse_args()

    src = source_path(args.src)
    info = probe(src)
    out = out_dir(args.out, "survey")
    times, F = read_range(src, 0, info["dur"], 320, fps=args.fps, info=info)
    F = F.astype(np.int16)
    diffs = np.abs(np.diff(F, axis=0)).mean(axis=(1, 2))
    quiet = np.concatenate([[True], diffs < args.th])

    states, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j + 1 < len(quiet) and quiet[j + 1]:
                j += 1
            if times[j] - times[i] + 1 / args.fps >= args.min_len:
                states.append((i, j))
            i = j + 1
        else:
            i += 1

    rows, tiles, prev_mean = [], [], None
    for n, (a, b) in enumerate(states):
        t0, t1 = times[a], times[b] + 1 / args.fps
        mid = (a + b) // 2
        m, sd = F[mid].mean(), F[mid].std()
        flags = []
        if sd < 12:
            flags.append("blank")
        if prev_mean is not None and m - prev_mean > 12:
            flags.append("bright+")
        prev_mean = m
        change = ""
        if n + 1 < len(states):
            seg = diffs[b:states[n + 1][0]]
            if len(seg):
                k = int(np.argmax(seg))
                change = f"{times[b + k + 1]:.2f}s (peak {seg[k]:.1f})"
        rows.append(f"| {n:02d} | {t0:7.2f} | {t1:7.2f} | {t1 - t0:5.2f} | {' '.join(flags)} | {change} |")
        th = grab(src, float(times[mid]), args.thumb, info)
        label(th, f"#{n:02d} {t0:.1f}-{t1:.1f}s {' '.join(flags)}", (6, 22), 0.6)
        tiles.append(th)

    md = [f"# Survey of `{src}`", "",
          f"{info['w']}x{info['h']} @ {info['fps']:.2f} fps, {info['dur']:.2f} s; reference space 1280x{info['ref_h']}", "",
          f"{len(states)} stable states (>= {args.min_len}s, diff < {args.th} at {args.fps:g} fps).", "",
          "| # | from (s) | to (s) | len | flags | next change |", "|---|---|---|---|---|---|", *rows]
    (out / "survey.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    for k in range(0, len(tiles), 24):
        path = out / f"survey-{k // 24:02d}.jpg"
        cv2.imwrite(str(path), sheet(tiles[k:k + 24], 4), [cv2.IMWRITE_JPEG_QUALITY, 82])
        print(path)
    print(out / "survey.md")


if __name__ == "__main__":
    main()
