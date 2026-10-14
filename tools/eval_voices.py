"""Rank Kokoro speakers for the voice-over: ASR character error rate, pitch and speaking rate.

    python3 tools/eval_voices.py 3 57 --speed 1.3     # Mandarin female speakers
    python3 tools/eval_voices.py 21 21 --script       # one speaker on the selected version's own copy
Writes build/voice-eval/{report.json, sid_XX.wav}.
"""
import argparse
import json
import sys
from pathlib import Path

import librosa
import numpy as np
import sherpa_onnx
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "project"))
from voiceover import ASR, make_tts, trim  # noqa: E402

TESTS = [
    "工单、工序与任务，一个系统高效协同。",
    "负责人在任务派发管理中，集中管理负责的任务，支持批量派发。",
    "计划有变？直接在链路中插入新工序，确认后链路即时更新。",
]


def cer(ref, hyp):
    strip = lambda s: [c for c in s if "\u4e00" <= c <= "\u9fff"]
    r, h = strip(ref), strip(hyp)
    d = np.arange(len(h) + 1)
    for i, rc in enumerate(r, 1):
        prev, d[0] = d.copy(), i
        for j, hc in enumerate(h, 1):
            d[j] = min(prev[j] + 1, d[j - 1] + 1, prev[j - 1] + (rc != hc))
    return d[-1] / max(1, len(r))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("first", type=int)
    ap.add_argument("last", type=int)
    ap.add_argument("--speed", type=float, default=1.3)
    ap.add_argument("--script", action="store_true", help="test on the VO lines of the selected VIDEO instead")
    a = ap.parse_args()
    tests = TESTS
    if a.script:
        from config import script
        tests = [line.get("say", line["text"]) for line in script.VO_LINES]
    out = ROOT / "build/voice-eval"
    out.mkdir(parents=True, exist_ok=True)
    tts = make_tts()
    asr = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=str(ASR / "model.int8.onnx"), tokens=str(ASR / "tokens.txt"),
        language="zh", use_itn=False, num_threads=4)
    report = []
    for sid in range(a.first, a.last + 1):
        errs, f0s, rates, clips = [], [], [], []
        for text in tests:
            au = tts.generate(text, sid=sid, speed=a.speed)
            x = trim(np.asarray(au.samples, dtype=np.float32), au.sample_rate)
            sr = au.sample_rate
            st = asr.create_stream()
            st.accept_waveform(sr, x)
            asr.decode_stream(st)
            errs.append(cer(text, st.result.text))
            f0, vf, _ = librosa.pyin(x, fmin=80, fmax=500, sr=sr, frame_length=1024)
            f0s.append(f0[vf])
            rates.append(sum("\u4e00" <= c <= "\u9fff" for c in text) / (len(x) / sr))
            clips.append(x)
            if a.script and errs[-1] > 0:
                print(f"  sid {sid}: {text} -> ASR {st.result.text}")
        f0 = np.concatenate(f0s)
        row = dict(sid=sid, cer=round(float(np.mean(errs)), 3),
                   f0_median=round(float(np.median(f0)), 1),
                   f0_spread=round(float(np.percentile(f0, 90) - np.percentile(f0, 10)), 1),
                   chars_per_s=round(float(np.mean(rates)), 2))
        report.append(row)
        sf.write(out / f"sid_{sid:02d}.wav", np.concatenate([np.r_[c, np.zeros(sr // 3)] for c in clips]), sr)
        print(row, flush=True)
    (out / "report.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
