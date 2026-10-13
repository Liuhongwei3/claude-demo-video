"""Contact sheet of rendered stills: python3 tools/contact.py build/v2/stills out.jpg [cols] [width]"""
import sys, glob
import cv2, numpy as np
d, out = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 4
w = int(sys.argv[4]) if len(sys.argv) > 4 else 360
files = sorted(glob.glob(f"{d}/*.png"))
tiles = []
for f in files:
    im = cv2.imread(f)
    im = cv2.resize(im, (w, int(im.shape[0] * w / im.shape[1])), interpolation=cv2.INTER_AREA)
    cv2.putText(im, f.split("_")[-1][:-4], (6, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    tiles.append(im)
while len(tiles) % cols:
    tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(out, np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]),
            [cv2.IMWRITE_JPEG_QUALITY, 85])
