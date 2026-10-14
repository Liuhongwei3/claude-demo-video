"""ASR every voice-over line out of the final mix (checks intelligibility over music / SFX).

    python3 tools/asr_mix.py [mix.wav]     # default build/<module>/<version>/audio/mix.wav
"""
import json
import sys
from pathlib import Path

import numpy as np
import sherpa_onnx
import soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "project"))
sys.path.insert(0, str(ROOT / "tools"))
from config import BUILD, script  # noqa: E402
from eval_voices import cer  # noqa: E402
from voiceover import ASR  # noqa: E402


def check(mix_path=None):
    """[(cer, text, heard), ...] for every VO line."""
    x, sr = sf.read(mix_path or BUILD / "audio/mix.wav")
    x = resample_poly(x.mean(1) if x.ndim > 1 else x, 16000, sr).astype(np.float32)
    asr = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=str(ASR / "model.int8.onnx"), tokens=str(ASR / "tokens.txt"),
        language="zh", use_itn=False, num_threads=4)
    info = json.loads((BUILD / "vo/durations.json").read_text())
    out = []
    for line, m in zip(script.VO_LINES, info):
        a, b = int((line["start"] - 0.15) * 16000), int((line["start"] + m["duration"] + 0.15) * 16000)
        st = asr.create_stream()
        st.accept_waveform(16000, x[max(0, a):b])
        asr.decode_stream(st)
        out.append((cer(line["text"], st.result.text), line["text"], st.result.text))
    return out


if __name__ == "__main__":
    res = check(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    for e, text, heard in res:
        print(f"{e:.2f}  {text}  ->  {heard}")
    print(f"mean CER {np.mean([r[0] for r in res]):.3f}")
