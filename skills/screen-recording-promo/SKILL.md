---
name: screen-recording-promo
description: 用本仓库的「产品宣传视频生产模板」把业务系统录屏（本地文件或 B 站链接）制作成 1080×1920 中文竖屏产品宣传 / 演示视频。每个模块（生产工单、库存管理、质量追溯、采购管理等）只需编写 spec.yaml（功能描述、镜头清单、旁白），按统一视觉规范自动生成成片、字幕、镜头清单、分镜和质检报告。用户提供录屏并要求做竖屏 demo、宣传片、功能演示视频，或要求修改、迭代已有视频版本时使用。
---

# 录屏 → 竖屏产品宣传视频（生产模板）

本仓库是一套可复用的生产模板：

- **统一规范** `project/style.py`：版式、配色、镜头节奏、女声配音、配乐，所有模块共用一套视觉语言。
- **每个视频只写一份** `project/versions/<模块>/<版本>/spec.yaml`：功能描述 + 镜头清单 + 旁白。
- **编译器** `project/compile_spec.py`：根据 spec 自动排时间线、机位缓动、转场、音效、标题、字幕断行、收尾和配乐。
- **一键构建** `VIDEO=<模块>/<版本> ./project/build.sh`：生成成片、字幕、旁白文案、镜头清单、分镜，再自动质检并生成交付说明。

完整示例：`project/versions/production-order/v3/spec.yaml`（生产工单，16 个镜头，49.9 s）。所有字段见 [reference/spec-reference.md](reference/spec-reference.md)，各业务模块的叙事建议见 [reference/module-playbooks.md](reference/module-playbooks.md)，自检见 [reference/qa-checklist.md](reference/qa-checklist.md)。

所有回复和交付文档用简体中文。

## 工作区

本 Skill 依赖仓库中的脚本。如果当前目录里没有 `project/compile_spec.py`（例如 Skill 是作为全局 Skill 安装的），先切换到视频工作区；没有工作区时，执行 `git clone https://github.com/Liuhongwei3/claude-demo-video` 后在其中工作。下文的路径都相对于该仓库根目录。

## 开始前向用户确认

缺少的信息用一句话问清楚，能从录屏推断的就不要问：

- 录屏文件或链接（B 站需要高清时，请用户提供 `BILIBILI_SESSDATA`）；
- 模块名称和要突出的功能点（brief）。没有 brief 时，根据录屏实际能证明的功能来提炼；
- 目标时长（默认 40–55 s）。有特殊要求时问清楚，例如是否需要男声、是否允许变更配色。

## 硬性规则

1. **只用录屏里真实存在的画面**。每句旁白描述的功能，都必须能在同一时间段的画面里看到。不伪造成功提示、业务结果、页面或 Logo。brief 要求但录屏里没有的内容，写进 spec 的 `gaps`（素材缺口），并建议补录多少秒；旁白改成画面能支撑的说法。
2. **不登录、不修改任何业务系统**，只使用用户提供的录屏。
3. **隐私**：人名、手机号、客户 / 供应商名、单价金额（用户未允许展示时）、账号头像、下拉框里的姓名或工号，一律模糊（`privacy` 或镜头的 `blur`）。浏览器栏、任务栏、录屏软件界面不能进画面（`regions.app`、`within`）。
4. **素材授权**：配乐和音效由代码合成，TTS 用 Kokoro（Apache-2.0），字体用思源黑体（OFL）。不下载来源不明的素材。
5. **统一规范**：不在单个视频里改 `project/style.py`。确有需要时，用 spec 的 `style:` 做局部覆盖，并在 `changes` 里写明。
6. **版本管理**：已交付的版本不再修改，有新反馈就 `new_video.py` 出下一个版本；交付后打 `video-<模块>-vN` 标签。

## 工作流程

复制清单并逐项推进：

```
- [ ] 1. 环境：./project/setup.sh（只需一次；检查 .cache/tts 下的模型）
- [ ] 2. 导入：python3 tools/ingest.py <录屏或BV号> --name <模块>
- [ ] 3. 建版本：python3 tools/new_video.py <模块> --title <模块名称> --source source/<模块>/source.mp4
- [ ] 4. 摸底：export VIDEO=<模块>/v1；survey → source_sheet → frame / activity，写 NOTES.md 素材地图
- [ ] 5. 写 spec：regions / privacy → 开场 → 每个功能一节（desc、beats：旁白 + 镜头）→ 收尾
- [ ] 6. 草稿：compile_spec.py --estimate，消除全部 WARNING；render.py --stills 抽查构图
- [ ] 7. 构建：./project/build.sh（会合成配音、渲染、自动质检；qa.py 未通过时返回非零）
- [ ] 8. 复查：review.py sheets / transitions 逐帧看；有问题就改 spec 后重新构建
- [ ] 9. 收尾：把人工检查结论写进 review_notes，重新运行 tools/qa.py 生成 DELIVERY.md
- [ ] 10. 提交：每个逻辑步骤一个 commit，打标签，推送，创建或更新 PR
```

### 4 摸底

```bash
python3 tools/survey.py                         # 稳定画面状态表 + 缩略图（标记 blank / bright+ 可疑加载）
python3 tools/source_sheet.py 53.5 58 --step 0.25 [--crop x0 y0 x1 y1]
python3 tools/frame.py 107.9 [--crop 190 110 1090 550]   # 带参考坐标网格，量矩形
python3 tools/activity.py 103 112 [--rect ...]            # 帧差事件：点击 spike、加载 run
```

用图片查看工具读取生成的 jpg 或 png（刚写出的文件偶尔读不到，稍等后重读）。按 `NOTES.md` 的表格记录：每个页面能证明的功能、点击时刻、要避开的加载时段、抽屉和弹窗矩形、敏感信息位置、要舍弃的段落。

### 5 写 spec 的要点

- **结构**：`hook`（痛点问句 + 一句话价值）→ 每个功能一节（2–4 句旁白、2–4 个镜头）→ `closing`（4–6 个关键词组成的闭环 + 两行收尾）。
- **旁白**：每句 12–20 字，一句讲一件画面里正在发生的事。避开「还能」这类易被听错的词，句首避开 r- 等弱声母。
- **镜头**：同一页面上的相邻镜头用 `match: prev`；抽屉和弹窗必须写 `within`；点击写 `click: [原片时间, x, y]`（时间取 activity 测出的 spike）；跳过加载时，在点击后、骨架屏出现前结束 `src`，下一镜头从内容完整出现后开始。
- **高亮**：同时最多两个；标签 4–9 字，不压其他高亮或点击目标（放不下就改用 `pos: bottom`）。成功提示配 `chime: true`。
- **镜头说明**：每个镜头写 `shows`（展示的真实功能）和 `note`（敏感信息 / 缺陷处理），它们会进入镜头清单。

### 6–8 编译警告与修正

| 警告 | 处理 |
|---|---|
| `shot is Xs but src a-b needs Ys` | 加大该镜头的 `min`、给下一句加 `pause`，或缩短 `src` |
| `starts ... after ... (< min)` | 调大同一句里后一个镜头的 `at` |
| `would need zoom ...; capped` | 区域太小，换更大的 `view`，或请用户提供高清录屏 |
| `subtitle longer than 16 chars` | 在旁白里加逗号，或写 `break: [第一行, 第二行]` |
| qa：配音清晰度未通过 | 看 qa-report 里听错的句子：改写，或用 `tts:` 改读法 |
| qa：版面未通过 | 该镜头的 `view` 太高，换更宽、更矮的区域 |

## 踩过的坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 句首被听错（「任务」→「政务」） | 转场 whoosh 的尾音盖住句首 | 编译器已自动避让；仍有问题时给该句加 `pause` |
| 画面发灰 | 原片处于加载或刷新态，或 spot 太重 | `src` 从内容完整出现后开始，spot 不超过 0.12 |
| 镜头末尾闪出骨架屏 | 点击后页面开始加载 | `src` 在加载前结束，后面自动定格 |
| 弹窗镜头边缘出现灰条 | 取景超出弹窗 | 写 `within: <弹窗区域>` |
| 转场时画面跳动 | 同一页面相邻镜头的机位不同 | 写 `match: prev` |
| 小字发糊 | 原片分辨率低，放大倍数过高 | 换高清录屏；`view` 不要小于约 450 px 宽 |
| 时间漂移、卡顿 | 录屏是可变帧率 | 必须先用 `ingest.py` 导入 |
