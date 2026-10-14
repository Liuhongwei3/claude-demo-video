"""Start a new video: a module's first cut from the template, or the next version of an existing one.

    python3 tools/new_video.py inventory --title 库存管理 --source source/inventory/source.mp4   # inventory/v1
    python3 tools/new_video.py inventory                                                     # inventory/v2 from v1
    python3 tools/new_video.py purchasing --from production-order/v3 --source source/purchasing/source.mp4

Creates project/versions/<module>/<version>/ with spec.yaml and NOTES.md (material map). A new version
copies the previous one's spec; delivered versions are never modified.
"""
import argparse
import re
import shutil
import sys

from srcutil import ROOT

VERSIONS = ROOT / "project/versions"
TEMPLATES = ROOT / "project/templates"


def set_key(text, key, value):
    line = f"{key}: {value}"
    if re.search(rf"^{key}:.*$", text, re.M):
        return re.sub(rf"^{key}:.*$", line, text, count=1, flags=re.M)
    return f"{line}\n{text}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("module", help="folder name, e.g. inventory, quality-trace, purchasing")
    ap.add_argument("--version", help="default: next v<N> of the module")
    ap.add_argument("--from", dest="base", help="<module>/<version> to copy (default: latest of this module, else template)")
    ap.add_argument("--title", help="module display name, e.g. 库存管理")
    ap.add_argument("--source", help="recording path relative to the repo root")
    args = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.module):
        sys.exit("module: lowercase letters, digits and '-' only")
    mdir = VERSIONS / args.module
    existing = sorted((p.name for p in mdir.glob("v*") if re.fullmatch(r"v\d+", p.name)), key=lambda n: int(n[1:])) \
        if mdir.exists() else []
    version = args.version or f"v{int(existing[-1][1:]) + 1 if existing else 1}"
    dst = mdir / version
    if dst.exists():
        sys.exit(f"{dst.relative_to(ROOT)} already exists")

    base = args.base or (f"{args.module}/{existing[-1]}" if existing else None)
    if base:
        src_dir = VERSIONS / base
        if not (src_dir / "spec.yaml").exists():
            sys.exit(f"{base} has no spec.yaml to copy")
        spec = (src_dir / "spec.yaml").read_text(encoding="utf-8")
        notes = (src_dir / "NOTES.md") if (src_dir / "NOTES.md").exists() else TEMPLATES / "NOTES.md"
        for key in ("changes", "review_notes"):
            spec = re.sub(rf"^{key}:\n(?:  .*\n|\n)*", f"{key}: []\n", spec, flags=re.M)
    else:
        spec = (TEMPLATES / "spec.yaml").read_text(encoding="utf-8")
        notes = TEMPLATES / "NOTES.md"
        spec = set_key(spec, "out_name", f"{args.module}-demo")
    if args.title:
        spec = set_key(spec, "module", args.title)
    if args.source:
        if not (ROOT / args.source).exists():
            print(f"warning: {args.source} does not exist yet")
        spec = set_key(spec, "source", args.source)

    dst.mkdir(parents=True)
    (dst / "spec.yaml").write_text(spec, encoding="utf-8")
    shutil.copy(notes, dst / "NOTES.md")
    video = f"{args.module}/{version}"
    print(f"created project/versions/{video}/ (spec.yaml, NOTES.md) from {base or 'template'}")
    print(f"next: export VIDEO={video}; python3 tools/survey.py; edit spec.yaml; "
          f"python3 project/compile_spec.py --estimate; ./project/build.sh")


if __name__ == "__main__":
    main()
