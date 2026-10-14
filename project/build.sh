#!/usr/bin/env bash
# One-shot pipeline: voice-over -> soundtrack -> picture -> mux -> subtitles.
# Requires the recording named by edl.SOURCE (default source/source.mp4, see tools/fetch_bilibili.py) and the offline TTS models in .cache/tts
# (see README "环境准备").
#
#   ./project/build.sh                    # latest version under project/versions/
#   VIDEO_VERSION=v1 ./project/build.sh   # rebuild an earlier cut
set -euo pipefail
cd "$(dirname "$0")/.."

VIDEO_VERSION="${VIDEO_VERSION:-$(python3 -c 'import sys; sys.path.insert(0, "project"); import config; print(config.VERSION)')}"
TITLE="$(VIDEO_VERSION="$VIDEO_VERSION" python3 -c 'import sys; sys.path.insert(0, "project"); import config; print(config.TITLE)')"
export VIDEO_VERSION
BUILD="build/$VIDEO_VERSION"
OUT="deliverables/$VIDEO_VERSION"
echo "== building $VIDEO_VERSION"

python3 project/voiceover.py
python3 project/audio.py
python3 project/render.py "$@"
python3 project/subtitles.py

mkdir -p "$OUT"
ffmpeg -y -loglevel error -i "$BUILD/video.mp4" -i "$BUILD/audio/mix.wav" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -shortest -movflags +faststart \
  -metadata title="$TITLE · 产品宣传 Demo ($VIDEO_VERSION)" \
  "$OUT/production-workflow-demo.mp4"

ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate,sample_rate \
  -of compact "$OUT/production-workflow-demo.mp4"
