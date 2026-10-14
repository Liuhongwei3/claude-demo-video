# spec.yaml 字段参考

带注释的骨架见 `project/templates/spec.yaml`，完整示例见 `project/versions/production-order/v3/spec.yaml`。编译器：`project/compile_spec.py`；统一规范：`project/style.py`。

## 约定

- **参考坐标**：原片缩放到 1280 px 宽，高度按宽高比换算（16:9 时为 1280×720）。矩形写成 `[x0, y0, x1, y1]`，也可以写 `regions` 里的名字。换成 4K 原片后坐标不用改。
- **原片时间**：`src`、`click`、`src_at`、`privacy.src`、`blur.src`、`unused` 都使用原片秒数。
- **镜头内时间**：`at`、`cam`、`move`、`highlight.at`、`sweep.at`、`sfx` 用秒表示。正数从镜头开始算；负数从「下一镜头开始叠化进来」的时刻往回算。

## 顶层字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `module` | 是 | 模块显示名，用于片头小标题和文档标题 |
| `out_name` | 是 | 成片文件名（不含 .mp4） |
| `source` | 是 | 录屏路径（`tools/ingest.py` 的输出） |
| `source_note` | 否 | 原片来源说明，写进镜头清单 |
| `style` | 否 | 局部覆盖统一规范，如 `{colors: {ui_bg: "#ffffff"}}`，分组见下文 |
| `regions` | 是 | 命名矩形。`app` 必填，表示系统界面的可用区域 |
| `privacy` | 否 | `[{rect, src?, note}]`。不写 `src` 时整片模糊；写了只在该原片时段内模糊 |
| `sections` | 是 | 第一个是 `kind: hook`，最后一个是 `kind: closing`，中间是功能节 |
| `unused` / `gaps` / `changes` / `review_notes` | 否 | 写进镜头清单和交付说明：未使用的原片段落、素材缺口、相对上一版的改动、人工检查结论 |

## section（章节）

| 字段 | 说明 |
|---|---|
| `kind` | `hook` / `closing`；功能节不写 |
| `title` | 段名，用于镜头清单和旁白文档 |
| `kicker` | 屏幕小标题。功能节默认是「01  <title>」，hook 默认是 `module`，closing 默认是「闭环」 |
| `headline` | 屏幕主标题，8–12 字，在该节的第一个镜头出现后 0.15 s 切换 |
| `desc` | 功能描述，写进交付说明的「展示的功能」 |
| `beats` | 每个 beat 是一句旁白加上这句话期间开始的镜头 |
| `chain`、`closing_lines` | 仅 closing 使用：4–6 个闭环关键词；恰好两行的收尾文案 |

## beat（一句旁白）

| 字段 | 说明 |
|---|---|
| `vo` | 旁白文字，同时作为字幕 |
| `tts` | 实际朗读的文字（字幕不变），用来规避 TTS 或 ASR 的误读 |
| `speed`、`sid` | 单句的语速或音色。默认值来自统一规范，首尾两句会稍慢 |
| `pause` | 本句前额外停顿的秒数 |
| `headline` | 从本句起换一个主标题（同一功能内两个标题时使用） |
| `break` | 字幕手动分行 `[第一行, 第二行]`。默认超过 16 字时在中间的逗号处自动分行 |
| `shots` | 本句期间开始的镜头。不写时，上一个镜头继续 |

## shot（镜头）

| 字段 | 说明 |
|---|---|
| `id` | 镜头编号，用于镜头清单和 review 文件名 |
| `shows` / `note` | 写进镜头清单：展示的真实功能；敏感信息与缺陷处理 |
| `src` | `[a, b]` 播放原片区间；写单个数字表示定格 |
| `speed` | 默认 `fit`：在 0.55–1 倍速之间自动放慢以填满镜头，放不满时末帧定格。写 `1` 表示原速 |
| `delay` | 开始播放前先定格的秒数 |
| `align` | `end` 表示播放段贴着镜头结尾（前面定格） |
| `at` | 镜头在本句中的起始偏移。镜头开始时间 = 句子开始时间 − 0.3 s + `at` |
| `min` | 本镜头至少单独停留的秒数（默认 1.2）。不够时，后面的旁白整体顺延 |
| `xfade` | 本镜头入场的叠化时长（默认：同节 0.45 s，换节 0.55 s） |
| `view` / `to` / `move` | 起始和结束时展示的区域，在 `move: [起, 止]` 期间缓慢推拉（默认整段）。不写 `view` 时用 `within` 或 `app` |
| `cam` | `[[时间, 区域], ...]`，需要多段运动时代替 view / to。区域也可以写成 `{cx, cy, s, h}` |
| `match: prev` | 沿用上一镜头的末帧机位，且不推镜。同一页面无缝衔接时使用 |
| `within` | 取景限定在该区域内，抽屉和弹窗必须写 |
| `blur` | `[区域, {rect, src: [a, b]}]`，本镜头的额外模糊 |
| `highlight` | `[{rect, at: [起, 止?], label, pos: top/bottom/left/right, spot, chime}]`。也可以用 `src_at: [a, b]` 按原片时间出现 |
| `sweep` | 依次扫过节点：`{nodes: [...], at, step, spot, chime}`；或沿路径移动：`{path: [[时间, 区域], ...]}`（跟随鼠标） |
| `click` | `[原片时间, x, y]` 或其列表：点击涟漪加点击音效，自动换算到成片时间 |
| `sfx` | `[[时间, 种类]]`，额外音效：whoosh / whoosh_soft / tick / chime_soft / chime |

**区域到机位的换算**：放大倍数 s = min(1040 / 区域宽, 1300 / 区域高)，上限 2.4；卡片高度 = 区域高 × s，限制在 560–1300 px。

## 自动生成的内容

| 内容 | 规则（参数见 `project/style.py`） |
|---|---|
| 旁白时间 | 首句 0.40 s；句间 0.30 s，换节 0.50 s，再加 `pause`；镜头不够 `min` 时顺延 |
| 镜头时间 | 开始时间 = 句子开始时间 − 0.30 s + `at`；结束于下一镜头叠化完成时；第一个镜头从 0 s 开始，并有 0.9 s 的入场动画 |
| 收尾 | 收尾句开始后 1.9 s 出现关键词链；卡片在之前 0.7 s 内缩小上移并压暗；字幕在关键词链出现 0.7 s 后隐藏；成片在最后一句结束后 1.5 s 结束（关键词链出现后至少 3.5 s），最后 0.7 s 淡出 |
| 音效 | 0 s 和每个换节镜头前放 whoosh（句首前 0.45 s 内不放）；每个 click 配 tick；节点 sweep 配 chime_soft；`chime: true` 配 chime；收尾配 riser 和终止和弦 |
| 配乐 | 100 BPM，一小节 2.4 s；在卡片开始缩小的那一小节解决到主和弦；配音时自动压低音乐 |
| 文档 | `shot-list.md`（编译时生成）；`storyboard.jpg`、`qa-report.md`、`DELIVERY.md`（构建时生成） |

## `style` 可覆盖的分组

`layout`（卡片、标题、字幕的位置与字号）、`colors`（`accent` 强调色，`ui_bg` 卡片空白处的填充色，应与产品界面背景一致）、`voice`（`sid`、`speed`、`edge_speed`、`desc`）、`timing`（上表中的节奏参数）、`camera`（`card_h_max`、`s_max`、`closing`）、`music`、`subtitle`（`max_chars`）。
