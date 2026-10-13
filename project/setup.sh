#!/usr/bin/env bash
# Environment setup for the render pipeline (Ubuntu 24.04, Python 3.12).
set -euo pipefail
cd "$(dirname "$0")/.."

sudo apt-get install -y -q ffmpeg fonts-noto-cjk
pip install -q opencv-python-headless pillow numpy scipy soundfile pyloudnorm sherpa-onnx librosa

mkdir -p .cache/tts
cd .cache/tts
REL=https://github.com/k2-fsa/sherpa-onnx/releases/download
[ -d kokoro-multi-lang-v1_1 ] || { curl -sSL "$REL/tts-models/kokoro-multi-lang-v1_1.tar.bz2" | tar xj; }
[ -d sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17 ] || \
  { curl -sSL "$REL/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2" | tar xj; }
echo "setup done"
