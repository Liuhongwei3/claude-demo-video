"""ASR every voice-over line out of the final mix (checks intelligibility over music/SFX)."""
import json, sys
from pathlib import Path
import numpy as np, sherpa_onnx, soundfile as sf
from scipy.signal import resample_poly
sys.path.insert(0, "project"); sys.path.insert(0, "tools")
from config import BUILD, script
from voiceover import ASR
from eval_voices import cer
mix_path = Path(sys.argv[1]) if len(sys.argv) > 1 else BUILD / "audio/mix.wav"
x, sr = sf.read(mix_path)
x = resample_poly(x.mean(1) if x.ndim > 1 else x, 16000, sr).astype(np.float32)
asr = sherpa_onnx.OfflineRecognizer.from_sense_voice(model=str(ASR / "model.int8.onnx"), tokens=str(ASR / "tokens.txt"),
                                                     language="zh", use_itn=False, num_threads=4)
info = json.loads((BUILD / "vo/durations.json").read_text())
errs = []
for line, m in zip(script.VO_LINES, info):
    a, b = int((line["start"] - 0.15) * 16000), int((line["start"] + m["duration"] + 0.15) * 16000)
    st = asr.create_stream(); st.accept_waveform(16000, x[a:b]); asr.decode_stream(st)
    e = cer(line["text"], st.result.text); errs.append(e)
    print(f"{e:.2f}  {line['text']}  ->  {st.result.text}")
print(f"mean CER {np.mean(errs):.3f}")
