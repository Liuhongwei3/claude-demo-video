"""Edit decision list -- skeleton for a new recording (copy with tools/new_version.py).

Coordinates are in the reference space of the recording (1280 px wide, height follows its aspect ratio;
1280x720 for 16:9). `src` values are source seconds; every other time is seconds in the final cut.
Measure rects with tools/frame.py, find click / load times with tools/activity.py.

Workflow: write the copy deck (script.py) first, run voiceover.py, then lay shots on the voice-over
timing -- each shot starts ~0.3-0.5 s before the line that talks about it.
"""
from edlkit import CARD_H, LAYOUT_V2, MUSIC_V2, blur, hl, kf, ripple, sweep, sweep_path  # noqa: F401

SOURCE = "source/source.mp4"  # TODO: tools/ingest.py output
FPS = 30
DURATION = 20.0               # TODO: last VO line end + ~4 s for the closing copy and outro fade
OUT_W, OUT_H = 1080, 1920

SAFE_REF = (0, 64, 1280, 700)  # TODO: app viewport without browser chrome / recorder UI
GLOBAL_BLUR = [
    # (x0, y0, x1, y1),        # TODO: user name / avatar / phone visible on every frame
]

LAYOUT = dict(LAYOUT_V2, closing_t=15.0)                  # closing copy appears at closing_t
MUSIC = dict(MUSIC_V2, resolve_bar=6)                     # 6 * 2.4 s = 14.4 s, just before closing_t

SHOTS = [
    # ---------------------------------------------------------------- 1. hook: the main list page
    dict(
        id="S1", t0=0.00, t1=6.30, enter=0.9,
        src=[(0.00, 3.00), (6.30, 5.00)],            # TODO: (cut time, source time) pairs; equal src = freeze
        cam=[
            kf(0.00, cx=640, cy=382, s=1.40, h=900),  # wide: whole table readable
            kf(5.80, cx=420, cy=382, s=2.10, h=CARD_H),
        ],
        fx=[
            # blur((398, 136, 478, 700)),            # TODO: customer / person names
            # hl(4.6, 6.2, (283, 141, 330, 161), label="点击工单", label_pos="bottom"),
            # ripple(5.9, 312, 152),
        ],
    ),
    # ---------------------------------------------------------------- 2. one feature, proven on screen
    dict(
        id="S2", t0=5.80, t1=12.00, xfade=0.50,
        # safe=[(0, (266, 64, 1280, 700))],          # drawer / modal: keep the card inside it
        src=[(5.80, 6.00), (12.00, 12.20)],
        cam=[
            kf(5.80, cx=640, cy=382, s=1.40, h=900),
            kf(11.50, cx=600, cy=360, s=2.00, h=CARD_H),
        ],
        fx=[],
    ),
    # ---------------------------------------------------------------- 3. close: result state, card shrinks
    dict(
        id="S3", t0=11.50, t1=DURATION, xfade=0.50,
        src=[(11.50, 20.00), (DURATION, 20.00)],
        cam=[
            kf(11.50, cx=640, cy=360, s=1.36, h=820, w=1040, ccy=945),
            kf(14.20, cx=640, cy=360, s=1.38, h=820, w=1040, ccy=945),
            kf(15.00, cx=640, cy=360, s=1.17, h=470, w=900, ccy=560),
        ],
        dim=[(14.20, 0.0), (15.00, 0.18)],
        fx=[],
    ),
]

# (time, kind): whoosh, whoosh_soft, tick, chime_soft, chime, riser_end, chime_end.
# Keep ticks on ripples; keep whooshes >= 0.4 s away from VO line onsets (their tail masks the first syllable).
SFX = [
    (0.00, "whoosh_soft"), (5.80, "whoosh_soft"), (11.50, "whoosh_soft"),
    (14.20, "riser_end"), (15.00, "chime_end"),
]
