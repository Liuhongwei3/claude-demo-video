"""Building blocks for version EDLs (project/versions/<v>/edl.py): `from edlkit import kf, hl, ...`.

Coordinates are in the reference space of the recording (1280 px wide, height follows its aspect ratio);
`src` values are source seconds; every other time is seconds in the final cut.
"""

import style as _style

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


# The house style (project/style.py). closing_t / resolve_bar depend on the cut and are set per version.
LAYOUT_V2 = dict(_style.LAYOUT)
MUSIC_V2 = dict(_style.MUSIC)
CARD_H = _style.CAMERA["card_h_max"]
