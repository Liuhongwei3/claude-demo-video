---
name: screen-recording-promo
description: 把产品录屏（本地视频文件或 B 站链接）程序化剪成 1080×1920 中文竖屏产品宣传 / 演示短视频，复用本仓库 v2 的效果：大卡片裁切放大、形变叠化转场、高亮与点击涟漪、女声 TTS 配音、烧录字幕、合成配乐，按版本管理并自检。用户提供录屏并要求做竖屏 demo、宣传片、功能演示视频，或要求在已有成片基础上改出新版本时使用。
---

# 录屏 → 竖屏产品宣传 Demo（v2 效果）

本仓库是一条可复现的程序化剪辑流水线：录屏 → 剪辑决策表（`edl.py`）+ 文案（`script.py`）→ `project/build.sh` → 成片和交付文档。参考成片 `deliverables/v2/`，参考写法 `project/versions/v2/`（16 个镜头、13 句旁白、50.8 s）。

所有回复和交付文档用简体中文。

## 硬性规则（每次都适用）

1. **只用原片里真实存在的画面**。功能、页面、成功提示和业务结果都必须能在录屏里找到；找不到就改文案的说法（例如「通过操作列发起报工」，而不是展示报工成功），并在交付说明里列为「素材缺口」，建议补录多少秒。不得伪造提示、页面或 Logo。
2. **不登录、不修改任何业务系统**，只使用用户提供的录屏。
3. **隐私**：人名、手机号、客户名、账号头像、下拉选项里的姓名或工号，全部 `blur`，全片固定位置的放进 `GLOBAL_BLUR`。浏览器地址栏、任务栏和录屏软件界面不能进画面（用 `SAFE_REF` 或 `safe` 裁掉）。
4. **素材授权**：配乐和音效由 `project/audio.py` 合成，TTS 用 Kokoro（Apache-2.0），字体用思源黑体（OFL）。不下载来源不明的音乐或音效。
5. **版本管理**：已交付的版本（`project/versions/vN/`、`deliverables/vN/`）不再修改。有新反馈就新建 vN+1，并打 `video-vN` 标签。
6. **去掉瑕疵**：加载白屏、骨架屏、误点、滚动抖动、弹窗外的灰色遮罩、录屏工具界面都不能出现在成片里。

## 工作流程

复制下面的清单并逐项推进。各步骤的细节、参数和数值见 [reference/edl-reference.md](reference/edl-reference.md)，自检和交付见 [reference/qa-checklist.md](reference/qa-checklist.md)。

```
- [ ] 1. 环境：./project/setup.sh（ffmpeg、思源黑体、Python 依赖、.cache/tts 下的 TTS/ASR 模型）
- [ ] 2. 原片：tools/ingest.py → source/<名称>/source.mp4（统一转为 30 fps 恒定帧率）
- [ ] 3. 新版本：tools/new_version.py vN --from _template --source source/<名称>/source.mp4
- [ ] 4. 摸底：survey → source_sheet → frame / activity，写出素材地图
- [ ] 5. 叙事与文案：每个卖点对应一段真实画面，写 script.py
- [ ] 6. 配音：voiceover.py，根据 ASR 结果改写，直到每句都能听清
- [ ] 7. 时间线：按配音时长排镜头、标题、音效，写 edl.py
- [ ] 8. 静帧迭代：render.py --stills，逐一查看后调整
- [ ] 9. 全片构建：build.sh，再用 review.py 和 asr_mix.py 自检
- [ ] 10. 交付文档：storyboard、shot-list.md、DELIVERY.md、CHANGELOG、README
- [ ] 11. Git：每完成一步提交一次，打 video-vN 标签，推送，创建或更新 PR
```

### 1–3 环境、原片、版本

```bash
./project/setup.sh
python3 tools/ingest.py ~/录屏.mp4 --name order-flow [--trim 2.2 118]   # 本地文件
python3 tools/ingest.py BV1xxxxxxxxx --name order-flow                 # B 站；高清需要 BILIBILI_SESSDATA
python3 tools/new_version.py v3 --from _template --source source/order-flow/source.mp4
export VIDEO_VERSION=v3   # 版本名是 v<数字> 时会被自动当作最新版本，设置此变量更稳妥
```

- 同一段录屏只改剪辑时，用 `--from vN` 复制上一版。换新录屏时，用 `--from _template`，写法照抄 `v2`。
- 原片低于 1080p 时，卡片放大约 2 倍后小字会发软。在交付说明里注明，并建议提供高清录屏。B 站未登录最高只有 720P。

### 4 摸底：先看懂原片，再动手

```bash
python3 tools/survey.py                          # 划分稳定画面状态 → build/vN/survey/survey.md + survey-NN.jpg
python3 tools/source_sheet.py 53.5 58 --step 0.25 [--crop x0 y0 x1 y1]   # 某段时间的时间码联系表
python3 tools/frame.py 107.9 [--crop 190 110 1090 550]                   # 带参考坐标网格的单帧，用来量矩形
python3 tools/activity.py 103 112 [--rect x0 y0 x1 y1]                   # 帧差事件：点击、加载、提示的时刻
```

用 Read 工具查看生成的 jpg 和 png（刚写出的图片偶尔提示 File not found，稍等后重读即可）。然后在 `project/versions/vN/NOTES.md` 写出**素材地图**：

- 每个页面或弹窗对应的原片时间段，以及它能证明的功能点；
- 点击时刻（activity 中的 spike，同时也是涟漪和 tick 音效的时间点）；
- 加载和骨架屏时段（survey 标记的 `blank`、`bright+`，以及 activity 中持续较长的 run），这些时段必须跳过或定格避开；
- 抽屉和弹窗的参考坐标矩形（用作 `safe`）；
- 敏感信息的位置和出现时段（用作 `blur`）；
- 误点、滚动、重复操作等要舍弃的段落（以后写进 shot-list 的「未使用的原片段落」）。

### 5 叙事与文案（`script.py`）

- 结构沿用 v2：**开场钩子（痛点问句 + 一句话价值）→ 每个功能 2–4 个镜头 → 价值收束**。按用户 brief 的功能顺序组织，每个功能都要有真实画面作为证据。
- 旁白每句 12–20 字，约 4.9 字/秒（Kokoro speed 1.42，首尾两句用 1.36），句与句之间至少留 0.25 s。
- 屏幕主标题 `HEADLINES`：kicker 写成「01  模块 · 角色」，主标题 8–12 字，在章节切换处更换。
- 收尾 `CLOSING_CHAIN` 用 4–6 个关键词串成闭环，再配两行收尾文案。没有 Logo 时用纯文字收尾。
- 避免使用「还能」（会被听成「才能」）这类易混词。句首避开 r- 等弱声母，混音后容易被音乐和音效吃掉。

### 6 配音

```bash
python3 project/voiceover.py                      # build/vN/vo/line_XX.wav + durations.json，并逐句打印 ASR 结果
python3 tools/eval_voices.py 21 21 --script       # 用本版文案评测音色（换音色时：3–57 为女声，58–102 为男声）
```

ASR 结果与原文不同、而且不是同音字时，就要处理：改写句子（首选），或者用该行的 `say` 字段改变实际朗读的文字。同音字（如「链路 / 练路」「报工 / 报供」）可以忽略。

### 7 时间线（`edl.py`）

- 先用 `durations.json` 确定每句的 `start`，再排镜头：镜头的 `t0` 比讲它的那句早约 0.3–0.5 s，相邻镜头重叠 `xfade` 0.45–0.6 s。
- 镜头时长 1.2–4.5 s。开场先给全景（s≈1.4），再缓慢推近；功能镜头的放大倍数 s≈2.0–2.25（卡片宽 1040，高度不超过 `CARD_H`=1300）。
- **同一页面上相邻的镜头**：上一镜头末帧的机位等于下一镜头首帧的机位（写成共享的 `CAM_*` 字典），并设 `xzoom=0.0`，叠化时画面不跳。
- 高亮在镜头开始后至少 0.3 s 才出现，同时最多两个；标签 4–9 字，不能压住其他高亮或要点击的目标（放不下就改用 `label_pos="bottom"`）。
- 涟漪放在 activity 测出的点击帧上，并配一个 `tick` 音效。
- 跳过加载：在点击后、骨架屏出现前**定格**（`src` 中两个时间点取同一个原片时间），下一镜头从内容完整出现之后开始。
- 抽屉和弹窗镜头设置 `safe`，卡片不会露出遮罩层。
- 收尾：最后一个镜头在 `closing_t` 时缩小上移并压暗；`MUSIC["resolve_bar"] × 2.4 s` 约等于 `closing_t`；`riser_end` 和 `chime_end` 分别对齐缩小的起点和终点。
- `DURATION` = 最后一句结束时间 + 约 4 s（留给收尾文案和 0.7 s 淡出）。

### 8–9 迭代与构建

```bash
python3 project/render.py --stills 3.5 7.9 12.6   # 几秒钟出静帧（build/vN/stills/），改 edl 后先看静帧
./project/build.sh                                 # 配音 → 配乐 → 画面 → 字幕 → 封装，50 s 的成片约 3–4 分钟
python3 tools/review.py sheets                     # 每 0.5 s 抽一帧做联系表
python3 tools/review.py transitions                # 每个转场按 0.1 s 间隔展开
python3 tools/asr_mix.py                           # 对混音逐句做 ASR：被音效或音乐盖住的句子会暴露出来
```

按 [reference/qa-checklist.md](reference/qa-checklist.md) 逐项检查。发现问题就修改并重新构建，直到全部通过。只改音频时，可以只跑 `audio.py` 并重新封装，不用重新渲染画面。

### 10–11 交付与提交

- `python3 tools/review.py storyboard` 生成 `deliverables/vN/storyboard.jpg`，`build.sh` 已生成成片、`subtitles.srt` 和 `voiceover-script.txt`。
- 参照 `deliverables/v2/` 的格式手写 `shot-list.md` 和 `DELIVERY.md`（模板要点见 qa-checklist），在 `deliverables/CHANGELOG.md` 和 `README.md` 的版本表里加上新版本。
- 把成片和分镜复制到 `/opt/cursor/artifacts/`，方便在对话中展示。
- 每完成一个逻辑步骤提交一次；交付后执行 `git tag video-vN && git push origin video-vN`，推送分支并创建或更新 PR。

## 踩过的坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 某句开头被 ASR 听错（如「任务」→「政务」） | 前一个 whoosh 的混响尾巴盖住句首 | 删掉或挪开该音效，与句首至少间隔 0.4 s；`duck_lookahead` 0.12 |
| 画面发灰、像蒙了一层 | 原片处于加载或刷新状态，或设置了 spot 聚光 | 从内容完整出现后开始，把 spot 降到 0.12 左右 |
| 镜头末尾闪出骨架屏 | 点击后页面开始加载 | 在点击后、加载前定格 |
| 弹窗镜头边缘出现灰条 | 卡片超出弹窗，露出遮罩层 | 为该镜头设置弹窗矩形作为 `safe` |
| 转场时画面跳动 | 同一页面相邻镜头的机位不一致 | 共享 `CAM_*` 机位，并设 `xzoom=0.0` |
| 字幕末尾有「，」 | 文案以逗号断句 | 渲染时已自动去掉；`SUBTITLE_BREAKS` 中也不要带逗号 |
| 标签挡住点击目标 | 标签位置和目标重叠 | 改为 `label_pos="bottom"`，或错开出现时间 |
| 素材加帧后出现卡顿和时间漂移 | 录屏是可变帧率 | 先用 `ingest.py` 转为恒定 30 fps |
