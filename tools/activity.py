"""Print per-frame change in a ref-space region: python3 tools/activity.py t0 t1 x0 y0 x1 y1 [thresh]"""
import subprocess, sys
import numpy as np
t0, t1 = float(sys.argv[1]), float(sys.argv[2])
x0, y0, x1, y1 = map(int, sys.argv[3:7])
th = float(sys.argv[7]) if len(sys.argv) > 7 else 0.5
raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-i", "source/source.mp4", "-t", str(t1 - t0),
                      "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
F = np.frombuffer(raw, np.uint8).reshape(-1, 720, 1280)[:, y0:y1, x0:x1].astype(np.int16)
for i in range(1, len(F)):
    d = np.abs(F[i] - F[i - 1]).mean()
    if d > th:
        print(f"{t0 + i / 30:.3f}  {d:.2f}  mean {F[i].mean():.0f}")
