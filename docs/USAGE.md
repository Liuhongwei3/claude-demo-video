# 使用指南：用这套模板做下一个模块的宣传视频

这套模板与具体工具无关：核心是仓库里的一组脚本（`project/`、`tools/`）和一份 Skill 文档（`skills/screen-recording-promo/`）。Cursor、Claude Code 或其他编码 Agent 都按同一份 Skill 执行；不用 Agent 时，也可以照着命令手动完成。

---

## 1. 每次需要准备什么

| 内容 | 要求 |
|---|---|
| **录屏** | 本地视频文件或 B 站链接。建议 1080p 及以上（720p 放大后小字会发软）。每个要宣传的功能都完整操作一遍，并停留到结果出现（成功提示、状态变化），每个结果停 1–2 秒。尽量使用演示数据；真实姓名、金额等会被模糊，但不能事后补拍 |
| **模块名称** | 例如「库存管理」，以及一个英文目录名，例如 `inventory` |
| **功能点（brief）** | 3–4 个要突出的功能，按想讲的顺序列出，一句话说明每个功能的价值。没有 brief 时，Agent 会根据录屏里实际能证明的功能来提炼 |
| 可选 | 目标时长（默认 40–55 s）；是否需要男声；产品界面背景色不是浅灰时说明一下 |

需要你说明或确认的只有这些。镜头怎么剪、时间怎么排、视觉风格怎么做，都由模板统一处理。

## 2. 在 Cursor 中使用

仓库里的 `.cursor/skills/screen-recording-promo/` 会被 Cursor 自动识别（本地 Agent 和 Cloud Agent 都可以）。

1. 用 Cursor 打开本仓库（Cloud Agent 选择本仓库即可）。
2. 把录屏放进仓库，或者给出路径或 B 站链接，然后直接描述需求，例如：

   > 这是库存管理的录屏 `~/Downloads/库存.mp4`，按我们的宣传视频模板做一个竖屏 demo。重点讲：库存台账、入库审核、调拨、盘点预警。

3. Agent 会按 Skill 依次完成：导入录屏、摸底、编写 spec、构建、质检、交付，最后提交并创建 PR。
4. 需要修改时，直接说修改意见（例如「第三段太快，换成男声」）。Agent 会新建 `inventory/v2`，不会覆盖 v1。

Cloud Agent 首次运行时，会自动执行 `./project/setup.sh` 安装 ffmpeg、字体和离线 TTS 模型。

## 3. 在 Claude Code 中使用

仓库里有 `.claude/skills/screen-recording-promo/`（Skill 入口）和 `CLAUDE.md`（它导入 `AGENTS.md` 中的项目规则），Claude Code 启动时会自动加载。

```bash
cd claude-demo-video        # 本仓库
./project/setup.sh          # 首次使用：安装依赖和离线模型
claude
```

然后像在 Cursor 里一样描述需求。如果没有自动触发 Skill，可以明确说「使用 screen-recording-promo skill」，或者「先阅读 skills/screen-recording-promo/SKILL.md 再开始」。

## 4. 在其他 Agent 中使用（Codex、Gemini CLI、Windsurf、GitHub Copilot 等）

- 大多数工具会读取仓库根目录的 `AGENTS.md`（Codex 默认读取它；Gemini CLI 可以在设置中把上下文文件名配置为 `AGENTS.md`）。
- 不确定工具会读什么时，在第一条消息里写上：

  > 先完整阅读 `skills/screen-recording-promo/SKILL.md` 和其中引用的 reference 文档，严格按其流程执行。

这些工具需要能运行 shell 命令、读取图片：Skill 依赖查看抽帧图来判断画面。

## 5. 在别的仓库或全局使用

这个 Skill 依赖本仓库的脚本，不能只复制 Skill 文件。推荐的做法是：

- **把本仓库作为固定的「视频工作区」**：所有模块的视频都放在这里，按 `project/versions/<模块>/` 区分。也可以在 GitHub 上把本仓库设为 Template repository，给每个产品线单独生成一个仓库。
- 需要在其他项目里随时调用时，可以把入口装成全局 Skill，并让它切换到视频工作区：

  ```bash
  # Claude Code（个人级）
  mkdir -p ~/.claude/skills && cp -r skills/screen-recording-promo ~/.claude/skills/
  # Cursor（个人级）
  mkdir -p ~/.cursor/skills && cp -r skills/screen-recording-promo ~/.cursor/skills/
  ```

  Skill 第一步会检查当前目录里是否有 `project/compile_spec.py`。没有时，会先克隆或切换到视频工作区（默认 `https://github.com/Liuhongwei3/claude-demo-video`），再开始工作。

## 6. 不用 Agent，手动操作

```bash
./project/setup.sh                                                        # 首次
python3 tools/ingest.py ~/Downloads/库存.mp4 --name inventory             # → source/inventory/source.mp4
python3 tools/new_video.py inventory --title 库存管理 --source source/inventory/source.mp4
export VIDEO=inventory/v1

python3 tools/survey.py                                                   # 摸底：build/inventory/v1/survey/
python3 tools/frame.py 12.5 --crop 200 100 1000 600                       # 量坐标
# 编辑 project/versions/inventory/v1/spec.yaml：功能描述、镜头清单、旁白
python3 project/compile_spec.py --estimate                                # 草稿：检查时间线和警告
python3 project/render.py --stills 3 8 15                                 # 抽查构图
./project/build.sh                                                        # 成片 + 文档 + 自检
python3 tools/review.py sheets && python3 tools/review.py transitions     # 人工复查
```

成片和文档输出到 `deliverables/inventory/v1/`。

## 7. 目录与约定

```
project/style.py                     统一视觉规范（版式、配色、节奏、配音、配乐），所有模块共用
project/templates/spec.yaml          新模块的 spec 骨架（带全部字段注释）
project/versions/<模块>/<版本>/       spec.yaml（手写）、NOTES.md（素材地图）、edl.py / script.py（生成）
deliverables/<模块>/<版本>/           成片、字幕、旁白、镜头清单、分镜、质检报告、交付说明
deliverables/<模块>/CHANGELOG.md     该模块的版本记录
skills/screen-recording-promo/       Skill 正本；.cursor/ 和 .claude/ 下是入口
```

- 每个版本自包含：改需求就新建版本，旧版本的成片文件保持不变。
- **修改 `project/style.py` 会影响之后所有重新构建的视频**。需要逐帧复现某个旧版本时，检出它交付时的 git 标签（`video-<模块>-vN`）再构建。

## 8. 常见问题

| 问题 | 做法 |
|---|---|
| 换男声或换音色 | 在 spec 中写 `style: {voice: {sid: 68}}`。挑选音色：`python3 tools/eval_voices.py 58 102 --script`（58–102 为男声） |
| 产品界面不是浅灰背景 | 写 `style: {colors: {ui_bg: "#ffffff"}}`，让卡片空白处的填充色与界面一致 |
| 想更长或更短 | 增减 beat（旁白句）。时长由旁白自动决定 |
| 换真人配音 | 按 `voiceover-script.txt` 的时间码录制，覆盖 `build/<模块>/<版本>/vo/line_XX.wav`，运行 `python3 project/audio.py`，再执行 `build.sh` 末尾的 ffmpeg 封装命令 |
| B 站原片只有 720P | 设置 `BILIBILI_SESSDATA=<登录 Cookie>` 后重新运行 `ingest.py`，坐标不用改 |
| 录屏里缺某个功能的结果 | 写进 `gaps`，旁白改成画面能支撑的说法；补录后用 `new_video.py` 出新版本 |
