"""Start a new cut: copy an existing version (or the skeleton) and point it at a recording.

    python3 tools/new_version.py v3 --from v2                                   # same recording, new edit
    python3 tools/new_version.py v3 --from _template --source source/order-flow/source.mp4

Versions named v<number> are picked up as "latest" automatically; any other name needs
VIDEO_VERSION=<name>. Earlier versions are never touched, so every cut stays reproducible.
"""
import argparse
import re
import shutil
import sys

from srcutil import ROOT

VERSIONS = ROOT / "project/versions"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--from", dest="base", default="_template")
    ap.add_argument("--source", help="recording path relative to the repo root")
    args = ap.parse_args()

    dst, base = VERSIONS / args.name, VERSIONS / args.base
    if dst.exists():
        sys.exit(f"{dst.relative_to(ROOT)} already exists")
    if not base.is_dir():
        sys.exit(f"no such version: {args.base}")
    shutil.copytree(base, dst, ignore=shutil.ignore_patterns("__pycache__"))

    if args.source:
        if not (ROOT / args.source).exists():
            print(f"warning: {args.source} does not exist yet")
        edl = dst / "edl.py"
        text = edl.read_text(encoding="utf-8")
        line = f'SOURCE = "{args.source}"'
        if re.search(r"^SOURCE = .*$", text, re.M):
            text = re.sub(r"^SOURCE = .*$", line, text, count=1, flags=re.M)
        else:
            text = re.sub(r"^FPS = ", f"{line}\nFPS = ", text, count=1, flags=re.M)
        edl.write_text(text, encoding="utf-8")

    print(f"created {dst.relative_to(ROOT)} from {args.base}")
    env = "" if re.fullmatch(r"v\d+", args.name) else f"VIDEO_VERSION={args.name} "
    print(f"next: {env}python3 tools/survey.py   then edit {dst.relative_to(ROOT)}/script.py and edl.py")


if __name__ == "__main__":
    main()
