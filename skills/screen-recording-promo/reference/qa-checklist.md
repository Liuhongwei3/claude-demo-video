# 自检与交付清单

`./project/build.sh` 的最后一步会运行 `tools/qa.py`，自动检查下表各项，结果写进 `deliverables/<模块>/<版本>/qa-report.md`；有任何一项未通过时，脚本返回非零。自动检查全部通过后，还要做人工检查。

## 自动检查（tools/qa.py）

| 项目 | 标准 |
|---|---|
| 画面规格 | 1080×1920、30/1 fps、H.264、yuv420p |
| 音频规格 | AAC、48 kHz、立体声 |
| 时长 | 与编译出的 DURATION 相差不超过 0.1 s |
| 响度 | −16 ± 1 LUFS，真峰值不超过 −1 dBTP |
| 配音清晰度 | 混音逐句 ASR 的平均字错率不超过 0.06。逐句结果在 qa-report 中，同音字差异可以接受 |
| 字幕 | 每行不超过 18 字，行尾没有逗号或顿号 |
| 版面 | 每个机位关键帧的卡片都不进入标题区和字幕区 |

## 人工检查（看 `tools/review.py` 生成的图）

```bash
python3 tools/review.py sheets          # 每 0.5 s 一帧 -> build/<模块>/<版本>/review/sheet-NN.jpg
python3 tools/review.py transitions     # 每个转场按 0.1 s 展开 -> review/xfade-*.jpg
```

- [ ] 没有浏览器栏、任务栏、录屏工具界面、水印
- [ ] 没有加载白屏、骨架屏、发灰的刷新态、弹窗外灰色遮罩
- [ ] 转场平滑，同页衔接不跳，没有两张卡片的重影
- [ ] 高亮和标签对准目标，标签不压其他高亮或点击目标；涟漪与原片点击帧重合
- [ ] 所有人名、手机号、客户 / 供应商名、金额（未获允许时）、下拉框中的姓名或工号已模糊（放大查看表格和弹窗）
- [ ] 每句旁白描述的功能在同一时间段的画面中可见；没有伪造的结果、页面或 Logo
- [ ] 收尾：卡片缩小 → 关键词链 → 两行文案 → 淡出，与配乐的解决点对齐

发现问题就修改 spec.yaml 并重新构建。全部通过后，把检查结论（包括修过的问题）写进 spec 的 `review_notes`，再运行 `python3 tools/qa.py` 重新生成 `DELIVERY.md`。

## 交付物（deliverables/<模块>/<版本>/，全部自动生成）

| 文件 | 来源 |
|---|---|
| `<out_name>.mp4`、`subtitles.srt`、`voiceover-script.txt` | build.sh |
| `shot-list.md` | compile_spec.py，内容来自 spec 的 `shows` / `note` / `unused` / `gaps` / `privacy` |
| `storyboard.jpg` | review.py storyboard |
| `qa-report.md`、`DELIVERY.md` | qa.py，内容来自实测结果和 spec 的 `desc` / `changes` / `review_notes` / `gaps` |

最后在 `deliverables/<模块>/CHANGELOG.md` 记一节（反馈原话和改动要点），在 README 的视频列表里加一行，然后打标签 `video-<模块>-vN`。
