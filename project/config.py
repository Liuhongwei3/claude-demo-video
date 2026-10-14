"""Video selection: every pipeline step works on project/versions/<module>/<version>/.

    VIDEO=production-order/v2 ./project/build.sh   # one cut of one module
    VIDEO=inventory ./project/build.sh             # latest version of a module
    ./project/build.sh                             # only allowed while there is a single module

VIDEO_VERSION is accepted as an alias of VIDEO; a bare version name (v1) works when only one module has it.
Outputs go to build/<module>/<version>/ and deliverables/<module>/<version>/.
`edl` / `script` and everything derived from them load lazily, so compile_spec.py can run before
the generated edl.py exists.
"""
import importlib.util
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "project"))  # lets version files import edlkit
VERSIONS = ROOT / "project/versions"


def modules():
    return sorted(p.name for p in VERSIONS.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))


def versions(module):
    names = [p.name for p in (VERSIONS / module).iterdir() if p.is_dir() and re.fullmatch(r"v\d+", p.name)]
    return sorted(names, key=lambda n: int(n[1:]))


def resolve(name=None):
    """'<module>/<version>' for a VIDEO value (None, module, module/version or a bare version)."""
    mods = modules()
    if not name:
        if len(mods) != 1:
            sys.exit(f"set VIDEO=<module>[/<version>]; modules: {', '.join(mods)}")
        name = mods[0]
    name = name.strip("/")
    if "/" in name:
        return name
    if name in mods:
        vs = versions(name)
        if not vs:
            sys.exit(f"module {name} has no v<N> versions")
        return f"{name}/{vs[-1]}"
    hits = [m for m in mods if (VERSIONS / m / name).is_dir()]
    if len(hits) == 1:
        return f"{hits[0]}/{name}"
    sys.exit(f"cannot resolve VIDEO={name}; modules: {', '.join(mods)}")


VIDEO = resolve(os.environ.get("VIDEO") or os.environ.get("VIDEO_VERSION"))
MODULE, VERSION_NAME = VIDEO.split("/", 1)
VERSION = VIDEO
DIR = VERSIONS / VIDEO
BUILD = ROOT / "build" / VIDEO
DELIVER = ROOT / "deliverables" / VIDEO
if not DIR.is_dir():
    sys.exit(f"no such video: project/versions/{VIDEO}")


def _load(name):
    path = DIR / f"{name}.py"
    if not path.exists():
        hint = " (run python3 project/compile_spec.py first)" if (DIR / "spec.yaml").exists() else ""
        sys.exit(f"missing {path.relative_to(ROOT)}{hint}")
    spec = importlib.util.spec_from_file_location(f"{MODULE}_{VERSION_NAME}_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


from style import LAYOUT as LAYOUT_DEFAULTS  # noqa: E402  house style; edl.LAYOUT overrides keys

_cache = {}
_NEEDS = dict(edl="edl", SOURCE="edl", LAYOUT="edl", script="script", TITLE="script", OUT_NAME="script")


def __getattr__(name):
    if name not in _NEEDS:
        raise AttributeError(name)
    kind = _NEEDS[name]
    if kind not in _cache:
        mod = _cache[kind] = _load(kind)
        if kind == "edl":
            _cache.update(SOURCE=ROOT / getattr(mod, "SOURCE", "source/source.mp4"),
                          LAYOUT={**LAYOUT_DEFAULTS, **getattr(mod, "LAYOUT", {})})
        else:
            _cache.update(TITLE=getattr(mod, "TITLE", MODULE), OUT_NAME=getattr(mod, "OUT_NAME", MODULE))
    return _cache[name]
