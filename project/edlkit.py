"""Building blocks for version EDLs (project/versions/<v>/edl.py): `from edlkit import kf, hl, ...`.

Coordinates are in the reference space of the recording (1280 px wide, height follows its aspect ratio);
`src` values are source seconds; every other time is seconds in the final cut.
"""

__all__ = ["kf", "hl", "sweep", "ripple", "blur", "sweep_path", "LAYOUT_V2", "MUSIC_V2", "CARD_H"]


def kf(t, **kw):
    """Camera keyframe: cx, cy = view centre (ref px), s = output px per ref px,
    h / w = card size on the 1080x1920 canvas, ccy = card centre y. Omitted keys carry over."""
    return dict(t=t, **kw)


def hl(t_in, t_out, rect, label=None, label_pos="top", spot=0.0, color=None):
    """Highlight box. label_pos: top / bottom / left / right. spot > 0 dims everything else."""
    return dict(kind="hl", t_in=t_in, t_out=t_out, rect=rect, label=label,
                label_pos=label_pos, spot=spot, color=color)


def sweep(t_in, t_out, path, spot=0.0, label=None):
    """A highlight that glides through [(t, rect), ...] -- e.g. along a process chain or with the cursor."""
    return dict(kind="sweep", t_in=t_in, t_out=t_out, path=path, spot=spot, label=label)


def ripple(t, x, y):
    """Click ripple at a ref-space point; place it on the frame where the source shows the click."""
    return dict(kind="ripple", t=t, x=x, y=y)


def blur(rect, src_from=None, src_to=None):
    """Privacy blur of a ref-space rect, optionally only while the source time is in [src_from, src_to]."""
    return dict(kind="blur", rect=rect, src_from=src_from, src_to=src_to)


def sweep_path(t0, step, nodes, pad=6):
    """Sweep path visiting `nodes` (ref rects) one after another every `step` seconds."""
    return [(t0 + i * step, (x0 - pad, y0 - pad, x1 + pad, y1 + pad))
            for i, (x0, y0, x1, y1) in enumerate(nodes)]


# The v2 look: large 1040 px card, headline at the top, subtitles below, morph dissolves.
# closing_* times / positions depend on the cut and must be set per version.
LAYOUT_V2 = dict(
    card_w=1040, card_cy=945, card_radius=28,
    kicker_y=92, kicker_size=27, title_y=154, title_size=58, hook_title_size=64,
    sub_top=1650, sub_size=44, sub_line_h=62,
    head_fade_in=0.55, head_fade_out=0.4, sub_fade=0.22,
    hl_fade_in=0.4, hl_fade_out=0.35,
    morph=True, xzoom=0.035, outro_fade=0.7,
    closing_step=0.18, closing_l1_delay=0.75, closing_l2_delay=1.2,
    closing_chain_y=930, closing_l1_y=1080, closing_l2_y=1166,
)

# Soundtrack: 100 BPM, one bar = 2.4 s. resolve_bar should land where the closing copy appears
# (resolve_bar * 2.4 ~= LAYOUT["closing_t"]).
MUSIC_V2 = dict(kick_bar=2, shaker_bar=4, music_lufs=-28.0, duck_lookahead=0.12, duck_depth=0.72)

CARD_H = 1300   # tallest card that fits between the headline and the subtitles with LAYOUT_V2
