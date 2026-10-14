# EDL / 文案字段参考

字段以 `project/render.py`、`project/audio.py`、`project/voiceover.py` 的实际读取为准，默认值见 `project/config.py`。辅助函数在 `project/edlkit.py` 中（`from edlkit import kf, hl, …`）。

## 坐标与时间

- **参考坐标**：把录屏缩放到 1280 px 宽，高度按原片宽高比换算（16:9 时为 1280×720）。所有矩形都写成 `(x0, y0, x1, y1)`。换成 4K 原片后坐标不用改。
- **时间**：`src` 里的第二个值是原片秒数，其余时间都是成片秒数。
- **放大倍数 `s`**：成片像素 / 参考像素。卡片宽 1040、s=2.0 时，取景宽度为原片的 520 参考像素。

## `edl.py`

| 字段 | 必填 | 说明 |
|---|---|---|
| `SOURCE` | 是 | 原片路径（相对仓库根目录），由 `new_version.py --source` 写入 |
| `FPS`, `OUT_W`, `OUT_H` | 是 | 30, 1080, 1920 |
| `DURATION` | 是 | 成片时长 |
| `SAFE_REF` | 否 | 默认的可用区域，用来裁掉浏览器栏、任务栏和录屏界面。不设时为整帧 |
| `GLOBAL_BLUR` | 否 | 全片模糊的矩形列表（如登录用户名） |
| `LAYOUT` | 否 | 版式，v2 写法：`dict(LAYOUT_V2, closing_t=…)` |
| `MUSIC` | 否 | 配乐，v2 写法：`dict(MUSIC_V2, resolve_bar=…)` |
| `SHOTS` | 是 | 镜头列表，见下文 |
| `SFX` | 是 | `[(time, kind), …]` |

### 镜头 `dict`

| 键 | 说明 |
|---|---|
| `id` | 镜头编号，如 `"S3b"`。用于 review 输出文件名和 shot-list |
| `t0`, `t1` | 成片起止时间。下一镜头的 `t0` 应早于本镜头的 `t1`，两者重叠的部分就是转场 |
| `xfade` | 本镜头**入场**转场的时长（0.45–0.6）。首个镜头不需要 |
| `xzoom` | 本镜头入场时的推镜幅度，覆盖 `LAYOUT["xzoom"]`。同页无缝衔接时设为 `0.0` |
| `enter` | 首个镜头的入场时长（从 0.92 倍缩放渐显），v2 用 0.9 |
| `src` | `[(成片 t, 原片 t), …]` 分段线性映射。两点的原片时间相同表示**定格**；斜率小于 1 是慢放（0.55–0.85 倍可以接受）；不要明显快放 |
| `cam` | `[kf(t, cx=, cy=, s=, h=, w=, ccy=), …]`。省略的键沿用上一关键帧；`w` 和 `ccy` 默认取 `LAYOUT` 中的 `card_w` 和 `card_cy`。关键帧之间做缓动插值，`s` 按对数插值 |
| `safe` | `[(从成片 t 起, 矩形), …]`。取景会被限制在矩形内，矩形外用界面背景色填充。抽屉和弹窗镜头必须设置 |
| `dim` | `[(t, 0..1), …]` 整张卡片压暗，收尾时使用（v2 为 0.18） |
| `fx` | 效果列表，见下表 |

### 效果（`fx`）

| 函数 | 用途与要点 |
|---|---|
| `hl(t_in, t_out, rect, label=None, label_pos="top", spot=0.0)` | 蓝色描边高亮，`label_pos` 可选 top / bottom / left / right。`spot>0` 会压暗其余区域，最多 0.22，内容较浅的页面用 0.12 |
| `sweep(t_in, t_out, path, spot=0.0)` | 沿 `[(t, rect), …]` 移动的高亮，可以跟随鼠标，也可以依次扫过链路节点 |
| `sweep_path(t0, step, nodes, pad=6)` | 由节点矩形列表生成 `sweep` 路径 |
| `ripple(t, x, y)` | 点击涟漪，`t` 取 activity 测出的点击帧，并在 `SFX` 中同一时刻加 `tick` |
| `blur(rect, src_from=None, src_to=None)` | 马赛克加高斯模糊；`src_from` 和 `src_to` 按**原片时间**限定生效区间（例如下拉框只在展开期间模糊） |

### 典型机位（v2，16:9 原片）

| 场景 | 关键帧 |
|---|---|
| 列表全景（开场） | `kf(0, cx=600, cy=382, s=1.42, h=900)` |
| 推近到点击目标 | `s=2.25, h=CARD_H` |
| 抽屉全宽 | `s=1.38, h=878`，并设置 `safe=[(0, DRAWER)]` |
| 弹窗 | `s≈2.0`，`h` 取弹窗高 × s，`safe` 设为弹窗矩形 |
| 侧栏切换 | `cx=231, cy=353, s=2.25`（相邻两次侧栏点击共用这个机位） |
| 收尾缩小 | `kf(t, cx, cy, s=1.17, h=470, w=900, ccy=560)` 并设置 `dim` |

### 音效 `SFX` 种类

`whoosh`、`whoosh_soft`（转场）、`tick`（点击）、`chime_soft`（扫过链路时）、`chime`（成功提示）、`riser_end`（收尾前的上扬）、`chime_end`（收尾落点）。whoosh 与旁白句首至少间隔 0.4 s。

## `LAYOUT`（v2 取值即 `LAYOUT_V2`）

| 键 | v2 | 说明 |
|---|---|---|
| `card_w`, `card_cy`, `card_radius` | 1040, 945, 28 | 卡片默认宽度、中心 y、圆角 |
| `kicker_y`, `kicker_size`, `title_y`, `title_size`, `hook_title_size` | 92, 27, 154, 58, 64 | 顶部标题区；第一条标题使用 `hook_title_size` |
| `sub_top`, `sub_size`, `sub_line_h` | 1650, 44, 62 | 字幕区。卡片底部（ccy + h/2 = 945 + 650 = 1595）要高于 `sub_top` |
| `head_fade_in/out`, `sub_fade`, `hl_fade_in/out` | 0.55/0.4, 0.22, 0.4/0.35 | 渐入渐出时长 |
| `morph`, `xzoom`, `outro_fade` | True, 0.035, 0.7 | 形变叠化、推镜幅度、结尾淡出时长 |
| `closing_t` | 每版单独设置 | 收尾关键词链出现的时间 |
| `closing_step`, `closing_l1_delay`, `closing_l2_delay` | 0.18, 0.75, 1.2 | 关键词逐个出现的间隔，以及两行收尾文案的延迟 |
| `closing_chain_y`, `closing_l1_y`, `closing_l2_y` | 930, 1080, 1166 | 收尾元素的 y 坐标（位于缩小后卡片的下方） |

## `MUSIC`

100 BPM，一小节 2.4 s，IV–V–iii–vi 循环，在 `resolve_bar` 解决到 Cmaj9。

| 键 | v2 | 说明 |
|---|---|---|
| `resolve_bar` | 19 | 让 `resolve_bar × 2.4` 约等于 `closing_t`；前半小节进入 G7 上扬，riser 在解决前 2 s 开始 |
| `kick_bar`, `shaker_bar` | 2, 4 | 底鼓和沙锤从第几小节进入 |
| `music_lufs` | −28 | 配乐自身响度。成片整体统一到 −16 LUFS |
| `duck_lookahead`, `duck_depth` | 0.12, 0.72 | 旁白前多少秒开始压低音乐，以及压低深度（约 11 dB） |

## `script.py`

| 字段 | 说明 |
|---|---|
| `TITLE`, `OUT_NAME` | 产品名（写入元数据和旁白文案标题）；成片文件名 `deliverables/vN/<OUT_NAME>.mp4` |
| `VOICE_SID`, `TRIM_PAD`, `VOICE_DESC` | 音色编号（v2 用 21）、句尾保留的时长、交付文档中的音色描述 |
| `VO_LINES` | `{"start", "text", "speed"}`，可选 `"say"`（实际朗读的文字）和 `"sid"` |
| `VO_SECTIONS` | 每句旁白所属的镜头段名称，写入 voiceover-script.txt |
| `SUBTITLE_BREAKS` | `{行号: ["第一行", "第二行"]}`。超过约 16 字的句子在逗号处分成两行 |
| `SUBTITLE_HIDE_AFTER` | `{行号: t}` 到时间后隐藏字幕，让位给收尾文案 |
| `HEADLINES` | `[(t_in, t_out, kicker, 主标题), …]` |
| `CLOSING_CHAIN`, `CLOSING_LINE_1`, `CLOSING_LINE_2` | 收尾关键词链和两行收尾文案 |
