"""Download the source screen recording from Bilibili via the WBI-signed public API.

Usage:
    python3 tools/fetch_bilibili.py BV1j8pq6oEqi source/
    BILIBILI_SESSDATA=xxxx python3 tools/fetch_bilibili.py BV1j8pq6oEqi source/   # 1080P/4K

Without a login cookie Bilibili only serves 480P DASH or a 720P progressive MP4;
the best available stream is saved as <out_dir>/source.mp4.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from functools import reduce
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
MIXIN = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
         33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
         61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
         36, 20, 34, 44, 52]


def get(url, cookie):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": "https://www.bilibili.com/", "Cookie": cookie})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def mixin_key(orig):
    return reduce(lambda s, i: s + orig[i], MIXIN, "")[:32]


def sign(params, img_key, sub_key):
    key = mixin_key(img_key + sub_key)
    params = dict(params, wts=int(time.time()))
    params = {k: "".join(c for c in str(v) if c not in "!'()*") for k, v in sorted(params.items())}
    query = urllib.parse.urlencode(params)
    params["w_rid"] = hashlib.md5((query + key).encode()).hexdigest()
    return urllib.parse.urlencode(params)


def curl(url, path):
    subprocess.run(["curl", "-sSL", "--retry", "3", "-A", UA, "-e", "https://www.bilibili.com/",
                    "-o", str(path), url], check=True)


def main(bvid, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    spi = get("https://api.bilibili.com/x/frontend/finger/spi", "")["data"]
    cookie = f"buvid3={spi['b_3']}; buvid4={spi['b_4']}"
    if os.environ.get("BILIBILI_SESSDATA"):
        cookie += f"; SESSDATA={os.environ['BILIBILI_SESSDATA']}"
    nav = get("https://api.bilibili.com/x/web-interface/nav", cookie)["data"]
    print("logged in:", nav.get("isLogin"), "| vip:", (nav.get("vipStatus") or 0) == 1)
    img_key = nav["wbi_img"]["img_url"].rsplit("/", 1)[1].split(".")[0]
    sub_key = nav["wbi_img"]["sub_url"].rsplit("/", 1)[1].split(".")[0]

    view = get("https://api.bilibili.com/x/web-interface/wbi/view?"
               + sign({"bvid": bvid}, img_key, sub_key), cookie)
    (out / "view.json").write_text(json.dumps(view, ensure_ascii=False, indent=2))
    cid = view["data"]["cid"]

    play = get("https://api.bilibili.com/x/player/wbi/playurl?" + sign(
        {"bvid": bvid, "cid": cid, "qn": 127, "fnval": 4048, "fourk": 1}, img_key, sub_key), cookie)
    (out / "play.json").write_text(json.dumps(play, ensure_ascii=False, indent=2))
    dash = play["data"]["dash"]
    videos = sorted(dash["video"], key=lambda v: (v["height"], "avc" in v["codecs"], v["bandwidth"]))
    best = videos[-1]
    print("best DASH stream:", best["width"], "x", best["height"], best["codecs"])

    if best["height"] >= 1080:
        curl(best["baseUrl"], out / "video.m4s")
        audio = (dash.get("audio") or [None])[0]
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(out / "video.m4s")]
        if audio:
            curl(audio["baseUrl"], out / "audio.m4s")
            cmd += ["-i", str(out / "audio.m4s")]
        subprocess.run(cmd + ["-c", "copy", str(out / "source.mp4")], check=True)
    else:
        html5 = get("https://api.bilibili.com/x/player/wbi/playurl?" + sign(
            {"bvid": bvid, "cid": cid, "qn": 80, "fnval": 1, "platform": "html5", "high_quality": 1},
            img_key, sub_key), cookie)["data"]
        print("progressive MP4 quality:", html5["quality"], html5["format"])
        curl(html5["durl"][0]["url"], out / "source.mp4")
    print("saved", out / "source.mp4")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
