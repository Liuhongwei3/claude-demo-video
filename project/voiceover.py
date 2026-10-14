"""Generate the Mandarin voice-over offline with Kokoro v1.1-zh (Apache-2.0) via sherpa-onnx.

Each line is synthesised separately, trimmed, and written to build/<version>/vo/line_XX.wav;
measured durations go to build/<version>/vo/durations.json so the edit can be timed to speech.
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import sherpa_onnx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "project"))
from config import BUILD, script  # noqa: E402

VO_LINES, VOICE_SID = script.VO_LINES, script.VOICE_SID

MODEL = ROOT / ".cache/tts/kokoro-multi-lang-v1_1"
ASR = ROOT / ".cache/tts/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
OUT = BUILD / "vo"


def make_tts():
    d = str(MODEL) + "/"
    cfg = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                model=d + "model.onnx", voices=d + "voices.bin", tokens=d + "tokens.txt",
                data_dir=d + "espeak-ng-data", dict_dir=d + "dict",
                lexicon=d + "lexicon-us-en.txt," + d + "lexicon-zh.txt"),
            num_threads=4),
        rule_fsts=d + "date-zh.fst," + d + "phone-zh.fst," + d + "number-zh.fst",
        max_num_sentences=1)
    return sherpa_onnx.OfflineTts(cfg)


def trim(x, sr, thresh=0.01, pad=0.03):
    idx = np.where(np.abs(x) > thresh)[0]
    if not len(idx):
        return x
    a = max(0, idx[0] - int(pad * sr))
    b = min(len(x), idx[-1] + int(pad * sr))
    return x[a:b]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tts = make_tts()
    asr = None
    if ASR.exists():
        asr = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(ASR / "model.int8.onnx"), tokens=str(ASR / "tokens.txt"),
            language="zh", use_itn=False, num_threads=4)
    info = []
    for i, line in enumerate(VO_LINES):
        audio = tts.generate(line.get("say", line["text"]), sid=line.get("sid", VOICE_SID), speed=line.get("speed", 1.1))
        x = trim(np.asarray(audio.samples, dtype=np.float32), audio.sample_rate,
                 pad=getattr(script, "TRIM_PAD", 0.03))
        x = x / (np.abs(x).max() + 1e-9) * 0.89
        path = OUT / f"line_{i:02d}.wav"
        sf.write(path, x, audio.sample_rate)
        heard = ""
        if asr:
            st = asr.create_stream()
            pad = np.zeros(int(0.3 * audio.sample_rate), np.float32)
            st.accept_waveform(audio.sample_rate, np.concatenate([pad, x, pad]))
            asr.decode_stream(st)
            heard = st.result.text
        dur = len(x) / audio.sample_rate
        info.append({"file": path.name, "text": line["text"], "say": line.get("say", line["text"]),
                     "sid": line.get("sid", VOICE_SID), "speed": line.get("speed", 1.1), "duration": round(dur, 3),
                     "sample_rate": audio.sample_rate, "asr_check": heard})
        print(f"{i}: {dur:.2f}s  {line['text']}  |  ASR: {heard}")
    (OUT / "durations.json").write_text(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
