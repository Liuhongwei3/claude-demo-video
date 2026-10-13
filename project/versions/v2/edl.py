"""Edit decision list v2 -- longer, calmer cut with a larger picture.

Same conventions as v1: UI coordinates in the 1280x720 reference space of the source recording,
`src` values are source seconds, all other times are seconds in the final cut.
Camera keyframes: cx, cy = view centre (ref px), s = output px per ref px,
h / w = card size on the 1080x1920 canvas, ccy = card centre y on the canvas.

Transitions are "morph dissolves" (LAYOUT["morph"]): during an overlap the card frame glides from the
outgoing shot's size to the incoming one's while the content cross-dissolves. Where two shots show the
same page, the outgoing camera ends exactly where the incoming one starts, so the dissolve is seamless.
"""

FPS = 30
DURATION = 50.8
OUT_W, OUT_H = 1080, 1920

SAFE_REF = (0, 64, 1280, 700)
DRAWER = (266, 64, 1280, 700)
TASK_MODAL = (255, 110, 1023, 550)        # 工序任务详情 (from the routing chain)
INSERT_MODAL = (191, 110, 1086, 582)      # 插入目标任务
DETAIL_MODAL = (190, 110, 1088, 546)      # 任务详情 (from dispatch management)
DISPATCH_MODAL = (256, 110, 1022, 431)    # 任务派发 form

GLOBAL_BLUR = [
    (1150, 64, 1278, 84),   # logged-in user name, top-right
]

NODES_BEFORE = [(291, 300, 391, 405), (418, 294, 518, 412), (546, 300, 645, 406),
                (673, 316, 770, 388), (800, 316, 898, 388)]
NODES_AFTER = [(291, 300, 391, 405), (418, 294, 518, 412), (546, 300, 645, 406),
               (673, 308, 772, 405), (800, 316, 898, 388), (927, 314, 1025, 388)]

LAYOUT = dict(
    card_w=1040, card_cy=945, card_radius=28,
    kicker_y=92, kicker_size=27, title_y=154, title_size=58, hook_title_size=64,
    sub_top=1650, sub_size=44, sub_line_h=62,
    head_fade_in=0.55, head_fade_out=0.4, sub_fade=0.22,
    hl_fade_in=0.4, hl_fade_out=0.35,
    morph=True, xzoom=0.035, outro_fade=0.7,
    closing_t=46.15, closing_step=0.18, closing_l1_delay=0.75, closing_l2_delay=1.2,
    closing_chain_y=930, closing_l1_y=1080, closing_l2_y=1166,
)

# Soundtrack: Cmaj9 resolve on bar 19 (45.6 s), under the card shrinking into the closing copy.
MUSIC = dict(resolve_bar=19, kick_bar=2, shaker_bar=4, music_lufs=-28.0, duck_lookahead=0.12, duck_depth=0.72)

CARD_H = 1300   # tallest card: 1040 x 1300 between the headline and the subtitles


def kf(t, **kw):
    return dict(t=t, **kw)


def hl(t_in, t_out, rect, label=None, label_pos="top", spot=0.0, color=None):
    return dict(kind="hl", t_in=t_in, t_out=t_out, rect=rect, label=label,
                label_pos=label_pos, spot=spot, color=color)


def sweep(t_in, t_out, path, spot=0.0, label=None):
    return dict(kind="sweep", t_in=t_in, t_out=t_out, path=path, spot=spot, label=label)


def ripple(t, x, y):
    return dict(kind="ripple", t=t, x=x, y=y)


def blur(rect, src_from=None, src_to=None):
    return dict(kind="blur", rect=rect, src_from=src_from, src_to=src_to)


def _sweep_path(t0, step, nodes, pad=6):
    return [(t0 + i * step, (x0 - pad, y0 - pad, x1 + pad, y1 + pad))
            for i, (x0, y0, x1, y1) in enumerate(nodes)]


# camera positions shared by consecutive shots of the same page (seamless dissolves)
CAM_CHAIN_CLOSE = dict(cx=520, cy=381, s=1.95, h=1240)
CAM_CHAIN_CLICK = dict(cx=470, cy=381, s=2.05, h=CARD_H)
CAM_SIDEBAR = dict(cx=231, cy=353, s=2.25, h=CARD_H)
CAM_LIST_LEFT = dict(cx=365, cy=381, s=2.0, h=1272)

SHOTS = [
    # ================================================================ 1. hook: work-order list
    dict(
        id="S1", t0=0.00, t1=7.30, enter=0.9,
        safe=[(0.0, (84, 64, 1280, 700))],
        src=[(0.00, 2.40), (4.30, 2.40), (6.35, 4.45), (7.30, 4.45)],
        cam=[
            kf(0.00, cx=600, cy=382, s=1.42, h=900),
            kf(4.30, cx=520, cy=382, s=1.55, h=985),
            kf(6.30, cx=330, cy=345, s=2.25, h=CARD_H),
        ],
        fx=[
            blur((398, 136, 478, 700)),                         # customer-name column
            hl(5.30, 6.75, (283, 141, 330, 161), label="点击工单", label_pos="bottom"),
            ripple(6.18, 312, 152),
        ],
    ),
    # ================================================================ 2. detail drawer + routing chain
    dict(
        id="S2a", t0=6.70, t1=10.95, xfade=0.60, safe=[(0, DRAWER)],
        src=[(6.70, 5.42), (7.60, 6.32), (10.95, 6.32)],
        cam=[
            kf(6.70, cx=643, cy=382, s=1.38, h=878),
            kf(8.90, cx=643, cy=382, s=1.38, h=878),
            kf(10.35, **CAM_CHAIN_CLOSE),
        ],
        fx=[
            blur((845, 560, 965, 700)),                        # executor names in the task table
            sweep(7.55, 9.20, _sweep_path(7.60, 0.33, NODES_BEFORE), spot=0.18),
        ],
    ),
    # hovering the nodes: inspection status pop-ups, insert points
    dict(
        id="S2b", t0=10.50, t1=14.45, xfade=0.45, xzoom=0.0, safe=[(0, DRAWER)],
        src=[(10.50, 7.45), (14.45, 10.80)],
        cam=[
            kf(10.50, **CAM_CHAIN_CLOSE),
            kf(14.20, **CAM_CHAIN_CLICK),
        ],
        fx=[
            blur((845, 560, 965, 700)),
            sweep(10.75, 13.10, [(10.85, (285, 288, 397, 418)), (11.75, (412, 288, 524, 418)),
                                 (12.35, (540, 294, 651, 412))]),
        ],
    ),
    # click the first process node
    dict(
        id="S2c", t0=14.00, t1=15.20, xfade=0.45, xzoom=0.0, safe=[(0, DRAWER)],
        src=[(14.00, 12.95), (15.20, 14.15)],
        cam=[kf(14.00, **CAM_CHAIN_CLICK)],
        fx=[
            blur((845, 560, 965, 700)),
            ripple(14.47, 338, 342),
        ],
    ),
    # its task detail: status, progress, previous / next process, execution record
    dict(
        id="S2d", t0=14.70, t1=18.55, xfade=0.50, safe=[(0, TASK_MODAL)],
        src=[(14.70, 13.85), (18.55, 17.70)],
        cam=[
            kf(14.70, cx=512, cy=330, s=2.04, h=898),
            kf(18.55, cx=512, cy=330, s=2.10, h=924),
        ],
        fx=[
            hl(15.30, 18.55, (262, 145, 520, 172)),
            hl(16.00, 18.55, (262, 296, 335, 322)),
            hl(16.00, 18.55, (638, 296, 760, 322), label="工序前后衔接", label_pos="bottom"),
        ],
    ),
    # ================================================================ 3. insert a process
    dict(
        id="S3a", t0=18.00, t1=20.85, xfade=0.55, safe=[(0, DRAWER)],
        src=[(18.00, 33.70), (18.60, 33.70), (20.32, 35.42), (20.85, 35.62)],
        cam=[
            kf(18.00, cx=600, cy=381, s=1.95, h=1240),
            kf(20.30, cx=650, cy=360, s=2.30, h=CARD_H),
        ],
        fx=[
            blur((845, 560, 965, 700)),
            hl(19.20, 20.75, (645, 340, 673, 362)),
            ripple(20.32, 659, 351),
        ],
    ),
    # the insert dialog, filled in: previous / chosen / next process, then 确认新增
    dict(
        id="S3b", t0=20.35, t1=23.40, xfade=0.50, safe=[(0, INSERT_MODAL)],
        src=[(20.35, 54.00), (23.00, 56.65), (23.40, 56.69)],
        cam=[
            kf(20.35, cx=690, cy=346, s=1.96, h=925),
            kf(21.90, cx=700, cy=346, s=2.00, h=944),
            kf(22.85, cx=826, cy=346, s=2.00, h=944),
        ],
        fx=[
            blur((495, 310, 660, 332)),                        # executor name in 派发1
            hl(20.80, 22.30, (497, 146, 640, 182)),
            hl(20.80, 22.30, (797, 146, 905, 182)),
            hl(21.05, 22.30, (497, 197, 785, 234), label="插入新工序：段差磨", label_pos="bottom"),
            hl(22.35, 23.40, (1034, 561, 1081, 582)),
            ripple(22.97, 1056, 571),
        ],
    ),
    # result: 新增成功 toast, the chain now contains the new node
    dict(
        id="S3c", t0=22.95, t1=25.70, xfade=0.45, safe=[(0, DRAWER)],
        src=[(22.95, 57.65), (25.70, 60.30)],
        cam=[
            kf(22.95, cx=700, cy=381, s=2.00, h=1272),
            kf(25.70, cx=712, cy=381, s=2.05, h=CARD_H),
        ],
        fx=[
            blur((845, 560, 965, 700)),
            hl(23.55, 25.70, (606, 70, 676, 92), spot=0.12),
            hl(23.85, 25.70, (668, 302, 777, 410), label="新增工序", label_pos="bottom", spot=0.12),
        ],
    ),
    # ================================================================ 4. personal workbench
    dict(
        id="S4a", t0=25.15, t1=26.95, xfade=0.55,
        src=[(25.15, 94.90), (26.05, 95.42), (26.95, 95.85)],
        cam=[
            kf(25.15, cx=246, cy=353, s=2.18, h=1270),
            kf(26.95, **CAM_SIDEBAR),
        ],
        fx=[
            hl(25.55, 26.95, (6, 92, 106, 111)),
            ripple(26.05, 58, 101),
        ],
    ),
    dict(
        id="S4b", t0=26.45, t1=30.10, xfade=0.50,
        src=[(26.45, 97.40), (30.10, 99.62)],
        cam=[
            kf(26.45, **CAM_LIST_LEFT),
            kf(30.10, cx=400, cy=381, s=2.04, h=1290),
        ],
        fx=[
            hl(26.95, 28.30, (99, 89, 153, 109)),
            hl(27.70, 30.10, (103, 146, 640, 226), label="派发给我的工序任务", label_pos="bottom"),
        ],
    ),
    # live progress of every task + operation column
    dict(
        id="S4c", t0=29.55, t1=33.55, xfade=0.55,
        src=[(29.55, 100.95), (33.55, 103.40)],
        cam=[
            kf(29.55, cx=1005, cy=381, s=2.00, h=1272),
            kf(33.55, cx=1015, cy=381, s=2.05, h=CARD_H),
        ],
        fx=[
            hl(30.05, 31.90, (742, 144, 1114, 186)),
            hl(31.30, 33.55, (1212, 116, 1266, 520), label="任务操作入口", label_pos="left"),
        ],
    ),
    # ================================================================ 5. dispatch management (owner)
    dict(
        id="S5a", t0=33.00, t1=34.95, xfade=0.55,
        src=[(33.00, 103.45), (34.20, 104.15), (34.95, 104.22)],
        cam=[
            kf(33.00, cx=246, cy=353, s=2.18, h=1270),
            kf(34.95, **CAM_SIDEBAR),
        ],
        fx=[
            hl(33.45, 34.95, (6, 116, 106, 135)),
            ripple(34.20, 30, 125),
        ],
    ),
    dict(
        id="S5b", t0=34.45, t1=37.25, xfade=0.50,
        safe=[(0.0, (84, 64, 1280, 700))],
        src=[(34.45, 106.30), (36.80, 107.55), (37.25, 107.62)],
        cam=[
            kf(34.45, cx=370, cy=381, s=2.00, h=1272),
            kf(36.70, cx=345, cy=360, s=2.15, h=CARD_H),
        ],
        fx=[
            blur((835, 140, 935, 700)),                        # participant names
            hl(34.95, 36.10, (110, 89, 152, 107)),
            hl(35.25, 36.85, (112, 116, 139, 560), label="批量勾选", label_pos="bottom"),
            ripple(36.80, 184, 167),
        ],
    ),
    # task detail: routing progress + execution record, then 派发任务
    dict(
        id="S5c", t0=36.80, t1=41.05, xfade=0.45, safe=[(0, DETAIL_MODAL)],
        src=[(36.80, 107.95), (40.62, 110.70), (41.05, 110.98)],
        cam=[
            kf(36.80, cx=455, cy=328, s=1.96, h=855),
            kf(38.30, cx=460, cy=328, s=2.00, h=872),
            kf(40.20, cx=828, cy=328, s=2.00, h=872),
        ],
        fx=[
            blur((200, 415, 285, 500)),                        # executor names in the record
            hl(37.30, 38.55, (200, 325, 540, 365)),
            hl(38.45, 39.90, (198, 395, 700, 505), label="执行记录", label_pos="bottom"),
            hl(40.00, 41.05, (1000, 522, 1046, 545)),
            ripple(40.62, 1022, 534),
        ],
    ),
    # dispatch form: choose process / executor, 添加派发 -> a second dispatch row
    dict(
        id="S5d", t0=40.60, t1=44.10, xfade=0.45, safe=[(0, DISPATCH_MODAL)],
        src=[(40.60, 112.60), (42.70, 114.45), (44.10, 115.50)],
        cam=[
            kf(40.60, cx=640, cy=290, s=2.08, h=668),
            kf(42.30, cx=560, cy=290, s=2.16, h=694),
        ],
        fx=[
            blur((755, 305, 990, 350), src_from=113.3, src_to=114.47),   # executor dropdown
            hl(42.30, 42.95, (290, 322, 990, 342)),
            ripple(42.70, 660, 331),
            hl(43.00, 44.10, (282, 287, 668, 350), label="一次添加多条派发", label_pos="top"),
        ],
    ),
    # ================================================================ 6. the evolved chain, then the close
    dict(
        id="S6", t0=43.60, t1=DURATION, xfade=0.50, safe=[(0, DRAWER)],
        src=[(43.60, 88.25), (DURATION, 88.25)],
        cam=[
            kf(43.60, cx=658, cy=330, s=1.36, h=820, w=1040, ccy=945),
            kf(45.45, cx=658, cy=330, s=1.38, h=820, w=1040, ccy=945),
            kf(46.30, cx=658, cy=352, s=1.17, h=470, w=900, ccy=560),
        ],
        dim=[(45.45, 0.0), (46.30, 0.18)],
        fx=[
            blur((845, 560, 965, 700)),
            sweep(44.05, 45.55, _sweep_path(44.10, 0.27, NODES_AFTER), spot=0.22),
        ],
    ),
]

SFX = [
    (0.00, "whoosh_soft"), (6.18, "tick"), (6.75, "whoosh_soft"), (7.60, "chime_soft"),
    (14.47, "tick"), (18.00, "whoosh_soft"), (20.32, "tick"), (22.97, "tick"), (23.40, "chime"),
    (26.05, "tick"), (32.85, "whoosh_soft"), (34.20, "tick"),
    (40.62, "tick"), (42.70, "tick"), (43.60, "whoosh_soft"),
    (45.50, "riser_end"), (46.30, "chime_end"),
]
