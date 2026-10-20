#!/usr/bin/env bash
# One-shot pipeline: (spec ->) voice-over -> soundtrack -> picture -> subtitles -> mux -> storyboard -> QA.
# Requires the recording named in the spec / edl and the offline TTS models in .cache/tts (./project/setup.sh).
#
#   VIDEO=inventory/v1 ./project/build.sh              # one cut of one module
#   VIDEO=production-order ./project/build.sh          # latest version of a module
#   VIDEO=inventory/v1 ./project/build.sh --end 12     # extra args go to render.py
set -euo pipefail
cd "$(dirname "$0")/.."

eval "$(python3 -c 'import sys; sys.path.insert(0, "project"); import config; print(f"VIDEO={config.VIDEO}")')"
export VIDEO
DIR="project/versions/$VIDEO"
echo "== building $VIDEO"

if [ -f "$DIR/spec.yaml" ]; then
  python3 project/compile_spec.py          # writes edl.py / script.py, runs voiceover.py when lines changed
else
  python3 project/voiceover.py
fi

eval "$(python3 -c 'import sys; sys.path.insert(0, "project"); import config, shlex
print(f"BUILD={shlex.quote(str(config.BUILD))} OUT={shlex.quote(str(config.DELIVER))}")
print(f"TITLE={shlex.quote(config.TITLE)} OUT_NAME={shlex.quote(config.OUT_NAME)}")')"

python3 project/audio.py
python3 project/render.py "$@"
python3 project/subtitles.py

mkdir -p "$OUT"
ffmpeg -y -loglevel error -i "$BUILD/video.mp4" -i "$BUILD/audio/mix.wav" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -shortest -movflags +faststart \
  -metadata title="$TITLE · 产品宣传 Demo ($VIDEO)" \
  "$OUT/$OUT_NAME.mp4"

python3 tools/review.py storyboard
python3 tools/qa.py
