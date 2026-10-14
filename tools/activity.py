"""Frame-difference activity of a ref-space region: find clicks, page loads, toasts, cursor moves.

    python3 tools/activity.py 103 112                          # whole frame, grouped into events
    python3 tools/activity.py 56 60 --rect 266 64 1280 700     # only the drawer area
    python3 tools/activity.py 56 60 --frames --th 0.3          # every changed frame (old behaviour)

Event columns: start-end (source s), peak diff, mean brightness before -> after.
A short spike = click / hover / toast; a long run = animation or loading; brightness jumping towards
white = blank / skeleton screen (freeze the shot before it, or start after it).
"""
import argparse

import numpy as np

from srcutil import REF_W, probe, read_range, source_path


def events(times, diffs, means, th, gap):
    out, cur = [], None
    for i, d in enumerate(diffs):
        t = times[i + 1]
        if d > th:
            if cur and t - cur["end"] <= gap:
                cur["end"], cur["peak"] = t, max(cur["peak"], d)
                if d >= cur["peak"]:
                    cur["peak_t"] = t
            else:
                cur = dict(start=times[i], end=t, peak=d, peak_t=t, before=means[i])
                out.append(cur)
            cur["after_idx"] = i + 1
    for e in out:
        e["after"] = means[min(e.pop("after_idx") + 2, len(means) - 1)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("t0", type=float, nargs="?", default=0.0)
    ap.add_argument("t1", type=float, nargs="?")
    ap.add_argument("--rect", nargs=4, type=int, metavar=("X0", "Y0", "X1", "Y1"))
    ap.add_argument("--th", type=float, default=0.5, help="mean abs diff (0-255) that counts as change")
    ap.add_argument("--gap", type=float, default=0.25, help="merge changes closer than this (s)")
    ap.add_argument("--frames", action="store_true", help="print every changed frame instead of events")
    ap.add_argument("--src")
    args = ap.parse_args()

    src = source_path(args.src)
    info = probe(src)
    t1 = args.t1 if args.t1 is not None else info["dur"]
    times, F = read_range(src, args.t0, t1, REF_W, info=info)
    x0, y0, x1, y1 = args.rect or (0, 0, REF_W, info["ref_h"])
    F = F[:, y0:y1, x0:x1].astype(np.int16)
    diffs = np.abs(np.diff(F, axis=0)).mean(axis=(1, 2))
    means = F.mean(axis=(1, 2))
    if args.frames:
        for i, d in enumerate(diffs):
            if d > args.th:
                print(f"{times[i + 1]:.3f}  {d:.2f}  mean {means[i + 1]:.0f}")
        return
    for e in events(times, diffs, means, args.th, args.gap):
        dur = e["end"] - e["start"]
        kind = "spike" if dur < 0.2 else "run"
        print(f"{e['start']:8.3f} - {e['end']:8.3f}  ({dur:4.2f}s {kind:5s})  peak {e['peak']:5.2f} @ {e['peak_t']:.3f}"
              f"  brightness {e['before']:5.1f} -> {e['after']:5.1f}")


if __name__ == "__main__":
    main()
