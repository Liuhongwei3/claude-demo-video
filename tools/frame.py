"""Dump source frames (with a 50px reference grid) for composing shots: python3 tools/frame.py 104.5 110.6"""
import subprocess, sys
import cv2, numpy as np
for t in map(float, sys.argv[1:]):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", "source/source.mp4", "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(720, 1280, 3).copy()
    for x in range(0, 1280, 50):
        cv2.line(f, (x, 0), (x, 6 if x % 100 else 12), (0, 0, 255), 1)
        if x % 100 == 0:
            cv2.putText(f, str(x), (x + 2, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
    for y in range(0, 720, 50):
        cv2.line(f, (0, y), (6 if y % 100 else 12, y), (0, 0, 255), 1)
        if y % 100 == 0:
            cv2.putText(f, str(y), (14, y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
    cv2.imwrite(f"build/v2/probe/f_{t:07.3f}.png", f)
