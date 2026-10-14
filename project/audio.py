"""Soundtrack: procedurally synthesised BGM + UI sound cues + voice-over, ducked and loudness-normalised.

Everything here is generated from code (no third-party audio), so there are no licensing questions.
Outputs build/<version>/audio/{music,sfx,vo,mix}.wav  (48 kHz stereo).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pyloudnorm
import soundfile as sf
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "project"))
from config import BUILD, edl, script
import style  # noqa: E402

SR = 48000
DUR = edl.DURATION + 0.4
N = int(DUR * SR)
OUT = BUILD / "audio"
VO_DIR = BUILD / "vo"
rng = np.random.default_rng(7)

BPM = 100
BEAT = 60 / BPM
BAR = 4 * BEAT  # 2.4 s

# Bar on which the progression resolves to Cmaj9 under the closing line (v1: bar 11 = 26.4 s).
MUSIC = dict(resolve_bar=11, **style.MUSIC)
MUSIC.update(getattr(edl, "MUSIC", {}))
R = MUSIC["resolve_bar"]
T_LIFT = (R - 0.5) * BAR
T_RESOLVE = R * BAR


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def env_adsr(n, a, d, s, r, sr=SR):
    t = np.arange(n) / sr
    total = n / sr
    e = np.where(t < a, t / max(a, 1e-6),
                 np.where(t < a + d, 1 - (1 - s) * (t - a) / max(d, 1e-6), s))
    rel = np.clip((total - t) / max(r, 1e-6), 0, 1)
    return e * rel


def lowpass(x, fc, order=2):
    return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x)


def highpass(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)


def bandpass(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def add(buf, sig, t0, gain=1.0):
    i = int(t0 * SR)
    if i < 0:
        sig, i = sig[-i:], 0
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[:j - i] * gain


def reverb_ir(seconds=2.2, damp=3.2):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-damp * t)[:, None]
    ir[:, 0] = lowpass(ir[:, 0], 5000)
    ir[:, 1] = lowpass(ir[:, 1], 5000)
    return ir / np.sqrt((ir ** 2).sum(0))


def reverb(x_st, mix=0.25, ir=None):
    ir = reverb_ir() if ir is None else ir
    wet = np.stack([fftconvolve(x_st[:, c], ir[:, c])[:len(x_st)] for c in range(2)], 1)
    return x_st * (1 - mix) + wet * mix * 3


# ----------------------------------------------------------------------------- music
# Chord per bar (IV - V - iii - vi in C), resolving to Cmaj9 under the closing line.
LOOP = [
    [53, 57, 60, 64],    # Fmaj7
    [55, 59, 62, 64],    # G6
    [52, 55, 59, 62],    # Em7
    [57, 60, 64, 67],    # Am7
]
PROG = [(float(bar), LOOP[bar % 4]) for bar in range(R - 1)] + [
    (R - 1.0, [53, 57, 60, 64]),    # Fmaj7
    (R - 0.5, [55, 59, 62, 65]),    # G7    - lift
    (float(R), [48, 55, 59, 62, 64]),   # Cmaj9 - resolve, held to the end
]
BASS_ROOT = {53: 41, 55: 43, 52: 40, 57: 45, 48: 36}


def chord_spans():
    spans = []
    for k, (bar, notes) in enumerate(PROG):
        t0 = bar * BAR
        t1 = PROG[k + 1][0] * BAR if k + 1 < len(PROG) else DUR
        spans.append((t0, t1, notes))
    return spans


def pad_voice(freq, n):
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for det in (-0.06, 0.0, 0.07):
        f = freq * 2 ** (det / 12)
        ph = (f * t + rng.random()) % 1.0
        sig += 2 * ph - 1
    sig += 0.6 * np.sin(2 * np.pi * freq * 0.5 * t)
    return lowpass(sig / 3, 1100)


def make_music():
    pad = np.zeros(N)
    pluck_l, pluck_r = np.zeros(N), np.zeros(N)
    bass = np.zeros(N)
    drums = np.zeros(N)
    for t0, t1, notes in chord_spans():
        n = int((t1 - t0 + 1.2) * SR)
        e = env_adsr(n, 0.5, 0.6, 0.8, 1.4)
        for note in notes:
            add(pad, pad_voice(midi(note), n) * e, t0, 0.11)
        root = BASS_ROOT.get(notes[0], notes[0] - 12)
        if t0 >= BAR * 1 - 0.01:
            beats = np.arange(t0, t1 - 0.01, BEAT * 2)
            for b in beats:
                if T_LIFT <= b < T_RESOLVE:
                    continue
                m = int(BEAT * 1.9 * SR)
                tt = np.arange(m) / SR
                s = np.sin(2 * np.pi * midi(root) * tt) + 0.25 * np.sin(4 * np.pi * midi(root) * tt)
                add(bass, s * env_adsr(m, 0.02, 0.3, 0.6, 0.4), b, 0.30)
        # arpeggio: 8th notes through chord tones, one octave up
        if t0 >= 1.2 and not (T_LIFT <= t0 < T_RESOLVE):
            seq = [notes[0] + 12, notes[1] + 12, notes[2] + 12, notes[3] + 12, notes[2] + 12, notes[1] + 12]
            step = BEAT / 2
            k = 0
            for tt0 in np.arange(max(t0, 1.2), min(t1, T_LIFT if t0 < T_LIFT else t1) - 0.01, step):
                f = midi(seq[k % len(seq)])
                m = int(0.5 * SR)
                tt = np.arange(m) / SR
                s = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 9)
                vel = 0.75 + 0.25 * ((k % 4) == 0)
                add(pluck_l, s, tt0, 0.055 * vel * (1.0 if k % 2 == 0 else 0.6))
                add(pluck_r, s, tt0, 0.055 * vel * (0.6 if k % 2 == 0 else 1.0))
                k += 1
    # soft kick on every beat, light shaker on off-beats, both stopping for the lift
    for b in np.arange(MUSIC["kick_bar"] * BAR, T_LIFT - 0.01, BEAT):
        m = int(0.32 * SR)
        tt = np.arange(m) / SR
        f = 45 + 75 * np.exp(-tt * 28)
        k = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 11)
        add(drums, k, b, 0.20)
    for b in np.arange(MUSIC["shaker_bar"] * BAR + BEAT / 2, T_LIFT - 0.01, BEAT):
        m = int(0.08 * SR)
        nz = highpass(rng.standard_normal(m), 6000) * np.exp(-np.arange(m) / SR * 50)
        add(drums, nz, b, 0.025)
    # riser into the resolve + soft impact
    r0, r1 = T_RESOLVE - 2.0, T_RESOLVE
    m = int((r1 - r0) * SR)
    tt = np.linspace(0, 1, m)
    nz = rng.standard_normal(m)
    riser = bandpass(nz, 800, 6000) * (tt ** 2.2) * 0.05
    add(drums, riser, r0)
    m = int(1.6 * SR)
    tt = np.arange(m) / SR
    boom = np.sin(2 * np.pi * (40 + 40 * np.exp(-tt * 9)) * tt) * np.exp(-tt * 3.0)
    add(drums, boom, T_RESOLVE, 0.22)

    pluck = np.stack([pluck_l, pluck_r], 1)
    # simple stereo delay on the plucks
    d = int(BEAT * 0.75 * SR)
    delayed = np.zeros_like(pluck)
    delayed[d:, 0] = pluck[:-d, 1] * 0.35
    delayed[d:, 1] = pluck[:-d, 0] * 0.35
    pluck = pluck + delayed
    pad_st = np.stack([pad, pad], 1)
    mus = reverb(pad_st, 0.35) + reverb(pluck, 0.30) + np.stack([bass, bass], 1) + np.stack([drums, drums], 1)
    mus = highpass(mus.T, 30).T
    fade_in = np.clip(np.arange(N) / (0.6 * SR), 0, 1)
    fade_out = np.clip((N - np.arange(N)) / (1.0 * SR), 0, 1)
    return mus * (fade_in * fade_out)[:, None]


# ----------------------------------------------------------------------------- sfx
def sfx_whoosh(gain=1.0, dur=0.55):
    m = int(dur * SR)
    tt = np.linspace(0, 1, m)
    nz = rng.standard_normal(m)
    out = np.zeros(m)
    seg = 32
    for i in range(seg):
        a, b = i * m // seg, (i + 1) * m // seg
        fc = 400 + 3200 * np.sin(np.pi * (i + 0.5) / seg) ** 1.5
        out[a:b] = bandpass(nz[max(0, a - 2000):b], fc * 0.6, min(fc * 1.6, 20000))[-(b - a):]
    e = np.sin(np.pi * tt) ** 2
    return out * e * 0.10 * gain


def sfx_tick(gain=1.0):
    m = int(0.06 * SR)
    tt = np.arange(m) / SR
    s = np.sin(2 * np.pi * 2300 * tt) * np.exp(-tt * 90) + 0.4 * np.sin(2 * np.pi * 1200 * tt) * np.exp(-tt * 60)
    return s * 0.10 * gain


def sfx_chime(gain=1.0, notes=(88, 95)):
    m = int(1.4 * SR)
    tt = np.arange(m) / SR
    s = np.zeros(m)
    for i, n in enumerate(notes):
        f = midi(n)
        s += np.sin(2 * np.pi * f * tt) * np.exp(-tt * (3.2 + i)) * (1 if i == 0 else 0.6)
        s += 0.15 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 8)
    return s * 0.05 * gain


def make_sfx():
    buf = np.zeros(N)
    for t, kind in edl.SFX:
        if kind == "whoosh":
            add(buf, sfx_whoosh(), t - 0.18)
        elif kind == "whoosh_soft":
            add(buf, sfx_whoosh(0.55, 0.45), t - 0.15)
        elif kind == "tick":
            add(buf, sfx_tick(), t)
        elif kind == "chime_soft":
            add(buf, sfx_chime(0.55, (84, 91)), t)
        elif kind == "chime":
            add(buf, sfx_chime(1.0, (88, 95)), t)
        elif kind == "riser_end":
            add(buf, sfx_whoosh(0.5, 0.9), t)
        elif kind == "chime_end":
            add(buf, sfx_chime(1.1, (84, 88, 91, 95)), t)
    st = np.stack([buf, buf], 1)
    return reverb(st, 0.25)


# ----------------------------------------------------------------------------- voice-over
def make_vo():
    info = json.loads((VO_DIR / "durations.json").read_text())
    buf = np.zeros(N)
    for line, meta in zip(script.VO_LINES, info):
        x, sr = sf.read(VO_DIR / meta["file"])
        if x.ndim > 1:
            x = x.mean(1)
        x = resample_poly(x, SR, sr)
        x = highpass(x, 85)
        # gentle presence lift and soft compression
        x = x + 0.25 * bandpass(x, 2500, 6000)
        thr = 0.35
        x = np.where(np.abs(x) > thr, np.sign(x) * (thr + (np.abs(x) - thr) * 0.5), x)
        x = x / (np.abs(x).max() + 1e-9) * 0.8
        add(buf, x, line["start"])
    return buf


def envelope(x, attack=0.03, release=0.35):
    a = np.exp(-1 / (attack * SR))
    r = np.exp(-1 / (release * SR))
    env = np.zeros_like(x)
    lvl = 0.0
    ax = np.abs(x)
    # downsampled follower for speed
    hop = 48
    for i in range(0, len(x), hop):
        v = ax[i:i + hop].max()
        c = a if v > lvl else r
        lvl = c ** hop * lvl + (1 - c ** hop) * v
        env[i:i + hop] = lvl
    return env


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    music = make_music()
    sfx = make_sfx()
    vo = make_vo()
    env = envelope(vo)
    look = int(MUSIC["duck_lookahead"] * SR)
    if look:
        # start ducking just before each line so soft initials (r-, sh-) are not masked
        env = np.maximum(env, np.concatenate([env[look:], np.zeros(look)]))
    duck = 1 - MUSIC["duck_depth"] * np.clip(env / 0.25, 0, 1)
    music_d = music * duck[:, None]
    meter = pyloudnorm.Meter(SR)
    music_d *= 10 ** ((MUSIC["music_lufs"] - meter.integrated_loudness(music_d)) / 20)
    vo_st = np.stack([vo, vo], 1)
    vo_st *= 10 ** ((-17.0 - meter.integrated_loudness(vo_st)) / 20)
    sfx *= 10 ** ((-31.0 - meter.integrated_loudness(sfx)) / 20)
    mix = vo_st + music_d + sfx
    mix *= 10 ** ((-16.0 - meter.integrated_loudness(mix)) / 20)
    peak = np.abs(mix).max()
    ceiling = 10 ** (-1.5 / 20)
    if peak > ceiling:
        mix = np.tanh(mix / ceiling) * ceiling
    for name, sig in (("music", music_d), ("sfx", sfx), ("vo", vo_st), ("mix", mix)):
        sf.write(OUT / f"{name}.wav", sig.astype(np.float32), SR, subtype="PCM_24")
    print("integrated loudness of mix: %.1f LUFS, peak %.2f dBFS"
          % (meter.integrated_loudness(mix), 20 * np.log10(np.abs(mix).max())))


if __name__ == "__main__":
    main()
