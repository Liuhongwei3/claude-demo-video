"""Version selection: every pipeline step loads its EDL / copy deck from project/versions/<VIDEO_VERSION>/.

    VIDEO_VERSION=v1 ./project/build.sh      # reproduce the first cut
    ./project/build.sh                       # defaults to the latest version
"""
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "project"))  # lets version files `from edlkit import *`
VERSIONS = ROOT / "project/versions"
LATEST = max((p.name for p in VERSIONS.iterdir() if p.is_dir() and p.name[1:].isdigit()),
             key=lambda n: int(n[1:]), default="v1")
VERSION = os.environ.get("VIDEO_VERSION", LATEST)

BUILD = ROOT / "build" / VERSION
DELIVER = ROOT / "deliverables" / VERSION


def _load(name):
    path = VERSIONS / VERSION / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{VERSION}_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


edl = _load("edl")
script = _load("script")

SOURCE = ROOT / getattr(edl, "SOURCE", "source/source.mp4")
TITLE = getattr(script, "TITLE", "生产工单全流程管理")
OUT_NAME = getattr(script, "OUT_NAME", "production-workflow-demo")  # deliverables/<version>/<OUT_NAME>.mp4

# Layout defaults reproduce v1; a version can override any key via edl.LAYOUT.
LAYOUT = dict(
    card_w=960, card_cy=960, card_radius=26,
    kicker_y=188, kicker_size=28, title_y=246, title_size=64, hook_title_size=72,
    sub_top=1556, sub_size=44, sub_line_h=62,
    head_fade_in=0.45, head_fade_out=0.28, sub_fade=0.18,
    hl_fade_in=0.3, hl_fade_out=0.25,
    closing_chain_y=1000, closing_l1_y=1150, closing_l2_y=1236,
)
LAYOUT.update(getattr(edl, "LAYOUT", {}))
