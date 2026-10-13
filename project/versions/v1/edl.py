"""Edit decision list for production-workflow-demo.mp4.

All UI coordinates are in the 1280x720 *reference* space of the source recording
(scaled automatically when a 4K source is used). Times are seconds in the final cut,
except `src` values which are seconds in the source recording.

Camera keyframes: cx, cy = view centre (ref px), s = output px per ref px,
h / w = card size on the 1080x1920 canvas, ccy = card centre y on the canvas.
"""

FPS = 30
DURATION = 28.8
OUT_W, OUT_H = 1080, 1920

# Visible UI area in the reference frame: below the browser chrome/watermark, above the taskbar.
SAFE_REF = (0, 64, 1280, 700)

# The work-order detail drawer (hides the list page behind it)
DRAWER = (266, 64, 1280, 700)

# Personal / third-party details that must never be readable in the cut.
GLOBAL_BLUR = [
    (1150, 64, 1278, 84),   # logged-in user name, top-right
]

# Process-node boxes of the routing chain (ref px)
NODES_BEFORE = [(291, 300, 391, 405), (418, 294, 518, 412), (546, 300, 645, 406),
                (673, 316, 770, 388), (800, 316, 898, 388)]
NODES_AFTER = [(291, 300, 391, 405), (418, 294, 518, 412), (546, 300, 645, 406),
               (673, 308, 772, 405), (800, 316, 898, 388), (927, 314, 1025, 388)]


def kf(t, **kw):
    return dict(t=t, **kw)


def hl(t_in, t_out, rect, label=None, label_pos="top", spot=0.0, color=None):
    return dict(kind="hl", t_in=t_in, t_out=t_out, rect=rect, label=label,
                label_pos=label_pos, spot=spot, color=color)


def sweep(t_in, t_out, path, spot=0.0, label=None):
    """A focus box gliding through a list of (t, rect) keyframes."""
    return dict(kind="sweep", t_in=t_in, t_out=t_out, path=path, spot=spot, label=label)


def ripple(t, x, y):
    return dict(kind="ripple", t=t, x=x, y=y)


def blur(rect, src_from=None, src_to=None):
    return dict(kind="blur", rect=rect, src_from=src_from, src_to=src_to)


def _sweep_path(t0, step, nodes, pad=6):
    return [(t0 + i * step, (x0 - pad, y0 - pad, x1 + pad, y1 + pad))
            for i, (x0, y0, x1, y1) in enumerate(nodes)]


SHOTS = [
    # ---- Shot 1: work-order list -> click work order Z26-0218
    dict(
        id="S1", t0=0.00, t1=4.30, enter=0.7,
        safe=[(0.0, (84, 64, 1280, 700))],
        src=[(0.00, 2.40), (1.30, 2.40), (4.05, 4.47), (4.30, 4.72)],
        cam=[
            kf(0.00, cx=520, cy=330, s=1.30, h=820),
            kf(1.30, cx=520, cy=330, s=1.30, h=820),
            kf(3.55, cx=330, cy=250, s=2.20, h=1000),
        ],
        fx=[
            blur((398, 136, 478, 700), src_to=4.50),           # customer-name column of the list
            hl(2.85, 4.20, (283, 141, 330, 161), label="点击工单", label_pos="bottom"),
            ripple(3.80, 312, 152),
        ],
    ),
    # ---- Shot 2a: detail drawer (loaded) -> routing chain overview -> push in on the first processes
    dict(
        id="S2a", t0=4.00, t1=6.50, xfade=0.30, safe=[(0, DRAWER)],
        src=[(4.00, 5.42), (6.50, 7.92)],
        cam=[
            kf(4.00, cx=640, cy=300, s=1.32, h=900),
            kf(5.00, cx=600, cy=345, s=1.45, h=900),
            kf(5.95, cx=600, cy=345, s=1.45, h=900),
            kf(6.50, cx=494, cy=350, s=2.10, h=1000),
        ],
        fx=[
            sweep(5.05, 6.15, _sweep_path(5.10, 0.22, NODES_BEFORE), spot=0.28),
        ],
    ),
    # ---- Shot 2b: click a process node -> its task detail (with previous / next process)
    dict(
        id="S2b", t0=6.35, t1=8.95, xfade=0.15, safe=[(0, DRAWER)],
        src=[(6.35, 12.80), (8.95, 15.40)],
        cam=[
            kf(6.35, cx=494, cy=350, s=2.10, h=1000),
            kf(7.05, cx=494, cy=350, s=2.10, h=1000),
            kf(7.65, cx=580, cy=330, s=1.50, h=900),
        ],
        fx=[
            ripple(6.97, 338, 342),
            hl(7.75, 8.95, (258, 140, 520, 178)),
            hl(8.05, 8.95, (640, 312, 760, 334), label="工序前后衔接", label_pos="bottom"),
        ],
    ),
    # ---- Shot 3a: hover the "+" insert point between two processes and click it
    dict(
        id="S3a", t0=8.70, t1=10.35, xfade=0.30, safe=[(0, DRAWER)],
        src=[(8.70, 33.95), (10.35, 35.60)],
        cam=[
            kf(8.70, cx=630, cy=330, s=2.15, h=860),
            kf(10.35, cx=655, cy=335, s=2.45, h=860),
        ],
        fx=[
            hl(9.55, 10.35, (645, 340, 673, 362)),
            ripple(10.13, 659, 351),
        ],
    ),
    # ---- Shot 3b: insert dialog, filled in: previous / chosen / next process
    dict(
        id="S3b", t0=10.10, t1=12.10, xfade=0.25,
        src=[(10.10, 54.55), (12.10, 56.55)],
        cam=[
            kf(10.10, cx=640, cy=345, s=1.20, h=760),
            kf(10.75, cx=690, cy=298, s=2.00, h=760),
        ],
        fx=[
            hl(10.85, 12.10, (497, 146, 640, 182)),
            hl(10.85, 12.10, (797, 146, 905, 182)),
            hl(11.10, 12.10, (497, 197, 785, 234), label="插入新工序：段差磨", label_pos="bottom"),
        ],
    ),
    # ---- Shot 3c: result -- "新增成功" toast, chain now has the new node
    dict(
        id="S3c", t0=11.95, t1=13.85, xfade=0.20, safe=[(0, DRAWER)],
        src=[(11.95, 57.62), (13.85, 59.52)],
        cam=[
            kf(11.95, cx=725, cy=260, s=2.30, h=900),
            kf(13.85, cx=725, cy=265, s=2.42, h=900),
        ],
        fx=[
            hl(12.15, 13.85, (606, 70, 676, 92), spot=0.16),
            hl(12.40, 13.85, (668, 302, 777, 410), label="新增工序", label_pos="bottom", spot=0.16),
        ],
    ),
    # ---- Shot 4a: switch to the personal workbench (sidebar)
    dict(
        id="S4a", t0=13.65, t1=14.60, xfade=0.30,
        src=[(13.65, 94.85), (14.60, 95.80)],
        cam=[
            kf(13.65, cx=215, cy=210, s=2.25, h=700),
            kf(14.60, cx=200, cy=210, s=2.40, h=700),
        ],
        fx=[
            hl(13.85, 14.60, (6, 92, 106, 111)),
            ripple(14.22, 58, 101),
        ],
    ),
    # ---- Shot 4b: personal task list -- tasks of Z26-0218 dispatched to this user
    dict(
        id="S4b", t0=14.40, t1=16.45, xfade=0.25,
        src=[(14.40, 97.35), (16.45, 99.40)],
        cam=[
            kf(14.40, cx=410, cy=356, s=1.55, h=900),
            kf(16.45, cx=410, cy=356, s=1.62, h=900),
        ],
        fx=[
            hl(14.65, 15.55, (99, 89, 153, 109)),
            hl(15.35, 16.45, (103, 146, 716, 226), label="派发给我的工序任务", label_pos="bottom"),
        ],
    ),
    # ---- Shot 4c: live progress chain of each task + operation column
    dict(
        id="S4c", t0=16.25, t1=18.75, xfade=0.25,
        src=[(16.25, 100.90), (18.75, 103.40)],
        cam=[
            kf(16.25, cx=975, cy=330, s=1.65, h=900),
            kf(18.75, cx=985, cy=330, s=1.72, h=900),
        ],
        fx=[
            hl(16.55, 17.85, (742, 144, 1114, 186)),
            hl(17.55, 18.75, (1212, 116, 1266, 520), label="任务操作入口", label_pos="left"),
        ],
    ),
    # ---- Shot 5a: dispatch management list (owner's view) with multi-select
    dict(
        id="S5a", t0=18.55, t1=20.55, xfade=0.30,
        src=[(18.55, 106.55), (19.30, 106.55), (20.55, 107.80)],
        cam=[
            kf(18.55, cx=430, cy=370, s=1.45, h=900),
            kf(20.55, cx=420, cy=370, s=1.52, h=900),
        ],
        fx=[
            hl(18.85, 20.00, (99, 89, 153, 109)),
            hl(19.20, 20.40, (112, 116, 139, 560), label="批量勾选", label_pos="right"),
            hl(19.20, 20.40, (682, 90, 745, 109)),
            ripple(20.30, 184, 167),
        ],
    ),
    # ---- Shot 5b: dispatch form -- add several dispatch entries in one go
    dict(
        id="S5b", t0=20.40, t1=22.95, xfade=0.20,
        src=[(20.40, 113.95), (21.00, 113.95), (22.55, 115.50), (22.95, 115.50)],
        cam=[
            kf(20.40, cx=560, cy=256, s=1.95, h=580),
            kf(21.00, cx=550, cy=256, s=2.00, h=595),
            kf(21.55, cx=525, cy=252, s=2.30, h=680),
        ],
        fx=[
            ripple(21.47, 660, 331),
            hl(21.75, 22.95, (282, 287, 668, 350), label="一次添加多条派发", label_pos="top"),
        ],
    ),
    # ---- Shot 6: back to the evolved 6-process chain, then the value close
    dict(
        id="S6", t0=22.80, t1=28.80, xfade=0.30, safe=[(0, DRAWER)],
        src=[(22.80, 88.25), (28.80, 88.25)],
        cam=[
            kf(22.80, cx=655, cy=314, s=1.24, h=620, w=960, ccy=960),
            kf(25.10, cx=655, cy=314, s=1.27, h=620, w=960, ccy=960),
            kf(25.90, cx=655, cy=345, s=1.06, h=440, w=820, ccy=640),
        ],
        dim=[(25.10, 0.0), (25.90, 0.18)],
        fx=[
            sweep(23.25, 25.00, _sweep_path(23.30, 0.26, NODES_AFTER), spot=0.22),
        ],
    ),
]

# Light sound cues (output time, kind)
SFX = [
    (0.00, "whoosh_soft"), (3.80, "tick"), (4.10, "whoosh_soft"), (5.05, "chime_soft"),
    (6.97, "tick"), (8.70, "whoosh"), (10.13, "tick"), (12.05, "chime"),
    (13.65, "whoosh"), (14.22, "tick"), (18.55, "whoosh"), (20.30, "tick"),
    (21.47, "tick"), (22.80, "whoosh"), (25.30, "riser_end"), (26.20, "chime_end"),
]
