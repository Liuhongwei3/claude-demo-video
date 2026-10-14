"""Bring a new screen recording into the project as source/<name>/source.mp4.

    python3 tools/ingest.py ~/Downloads/录屏.mov --name order-flow
    python3 tools/ingest.py BV1j8pq6oEqi --name order-flow             # Bilibili (BILIBILI_SESSDATA for HD)
    python3 tools/ingest.py rec.mp4 --name order-flow --trim 2.2 118   # drop recorder start/stop chrome

The file is re-encoded to constant 30 fps H.264 with a keyframe every second and no audio: the renderer
addresses frames by (seek point + frame count), which drifts on variable-frame-rate recordings, and short
GOPs keep the many small seeks of the survey tools fast. Resolution is kept (4K is fine).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

from srcutil import ROOT, probe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="local video file, Bilibili BV id or URL")
    ap.add_argument("--name", required=True, help="folder under source/")
    ap.add_argument("--trim", nargs=2, type=float, metavar=("T0", "T1"))
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--crf", type=int, default=14)
    args = ap.parse_args()

    dest = ROOT / "source" / args.name
    dest.mkdir(parents=True, exist_ok=True)
    src = Path(args.input).expanduser()
    bv = re.search(r"BV[0-9A-Za-z]{10}", args.input)
    if not src.exists() and bv:
        raw = dest / "raw"
        subprocess.run([sys.executable, str(ROOT / "tools/fetch_bilibili.py"), bv.group(0), str(raw)], check=True)
        src = raw / "source.mp4"
    if not src.exists():
        sys.exit(f"not found: {args.input}")

    out = dest / "source.mp4"
    trim = ["-ss", f"{args.trim[0]:.3f}", "-to", f"{args.trim[1]:.3f}"] if args.trim else []
    tmp = dest / "source.tmp.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-stats", *trim, "-i", str(src), "-an",
                    "-vf", f"fps={args.fps},format=yuv420p", "-c:v", "libx264", "-preset", "medium",
                    "-crf", str(args.crf), "-g", str(int(args.fps)), "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(out)
    info = probe(out)
    rel = out.relative_to(ROOT)
    print(f"saved {rel}: {info['w']}x{info['h']} @ {info['fps']:.2f} fps, {info['dur']:.2f} s "
          f"(reference space 1280x{info['ref_h']})")
    if info["w"] < 1920:
        print("note: below 1080p -- the card zooms ~2x, so UI text will look soft; get a higher-res recording if possible")
    print(f"next: python3 tools/new_video.py {args.name} --title <模块名称> --source {rel}")


if __name__ == "__main__":
    main()
