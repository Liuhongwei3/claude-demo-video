"""House style for every product-promo video: the v2 visual language, motion rhythm, voice and soundtrack.

All modules (production orders, inventory, quality traceability, purchasing, ...) share STYLE so the
series looks and sounds the same. A spec can override single keys under `style:`; keep overrides
rare and recorded in the spec so they stay visible in review.
"""

LAYOUT = dict(
    card_w=1040, card_cy=945, card_radius=28,
    kicker_y=92, kicker_size=27, title_y=154, title_size=58, hook_title_size=64,
    sub_top=1650, sub_size=44, sub_line_h=62,
    head_fade_in=0.55, head_fade_out=0.4, sub_fade=0.22,
    hl_fade_in=0.4, hl_fade_out=0.35,
    morph=True, xzoom=0.035, outro_fade=0.7,
    closing_step=0.18, closing_l1_delay=0.75, closing_l2_delay=1.2,
    closing_chain_y=930, closing_l1_y=1080, closing_l2_y=1166,
)

COLORS = dict(
    accent="#1e88f3",     # highlight boxes, ripples, closing underline
    ui_bg="#f5f6f7",      # fills the card outside the app viewport; match the product UI background
)

MUSIC = dict(kick_bar=2, shaker_bar=4, music_lufs=-28.0, duck_lookahead=0.12, duck_depth=0.72)

VOICE = dict(
    sid=21,               # Kokoro v1.1-zh female, chosen by tools/eval_voices.py (CER + pitch)
    speed=1.42,           # ~4.9 Chinese characters per second
    edge_speed=1.36,      # first and last line, slightly calmer
    trim_pad=0.06,
    desc="普通话女声，干练清晰",
)

TIMING = dict(
    first_line=0.40,      # first VO onset
    gap=0.30,             # silence between lines of one section
    section_gap=0.50,     # silence before the first line of a new section
    lead=0.30,            # a shot starts this long before the line it is attached to
    xfade=0.45,           # morph-dissolve inside a section
    section_xfade=0.55,   # morph-dissolve into a new section
    min_shot=1.2,         # shortest time a shot is on screen alone
    hook_enter=0.9,       # first shot scales in
    headline_delay=0.15,  # headline changes this long after the shot that introduces it
    whoosh_clear=0.45,    # no transition whoosh within this long before a VO onset
    closing_after=1.9,    # closing copy appears this long after the last line starts
    closing_shrink=0.85,  # card shrink duration, ends 0.15 s after the closing copy appears
    tail=1.5,             # video continues this long after the last line ends
    min_tail=3.5,         # ... and at least this long after the closing copy appears
)

CAMERA = dict(
    card_h_max=1300,      # tallest card between headline and subtitles
    card_h_min=560,
    s_max=2.4,            # beyond this a 720p recording gets visibly soft
    closing=dict(w=900, h=470, ccy=560, s_factor=0.85, dim=0.18),
)

SUBTITLE = dict(max_chars=16)  # longer lines are split at the comma nearest the middle

STYLE = dict(layout=LAYOUT, colors=COLORS, music=MUSIC, voice=VOICE, timing=TIMING,
             camera=CAMERA, subtitle=SUBTITLE)


def hex_to_bgr(h):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (b, g, r)


def merged(overrides=None):
    """STYLE with a spec's `style:` overrides applied one level deep."""
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in STYLE.items()}
    for k, v in (overrides or {}).items():
        if k not in out:
            raise KeyError(f"unknown style group: {k} (expected one of {', '.join(out)})")
        out[k].update(v)
    return out
