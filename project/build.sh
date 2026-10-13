#!/usr/bin/env bash
# One-shot pipeline: voice-over -> soundtrack -> picture -> mux -> subtitles.
# Requires source/source.mp4 (see tools/fetch_bilibili.py) and the offline TTS models in .cache/tts
# (see README "环境准备").
set -euo pipefail
cd "$(dirname "$0")/.."

python3 project/voiceover.py
python3 project/audio.py
python3 project/render.py "$@"
python3 project/subtitles.py

mkdir -p deliverables
ffmpeg -y -loglevel error -i build/video.mp4 -i build/audio/mix.wav \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -shortest -movflags +faststart \
  -metadata title="生产工单全流程管理 · 产品宣传 Demo" \
  deliverables/production-workflow-demo.mp4

ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate,sample_rate \
  -of compact deliverables/production-workflow-demo.mp4
