# 自检与交付清单

每次 `build.sh` 之后都要实际检查一遍。只有全部通过，才写交付文档。

## 规格

```bash
ffprobe -v error -show_entries format=duration:stream=codec_name,profile,width,height,r_frame_rate,pix_fmt,sample_rate,channels \
  -of compact deliverables/$VIDEO_VERSION/*.mp4
ffmpeg -i deliverables/$VIDEO_VERSION/*.mp4 -af ebur128=peak=true -f null - 2>&1 | tail -12
```

- [ ] 1080×1920、30/1 fps、H.264 High、yuv420p、AAC 48 kHz 立体声，时长等于 `DURATION`
- [ ] 整体响度约 −16 LUFS，真峰值不超过 −1.5 dBTP

## 画面（`review.py sheets` 每 0.5 s 一帧，`review.py transitions` 展开每个转场）

- [ ] 没有浏览器地址栏、任务栏、录屏工具界面或水印
- [ ] 没有加载白屏、骨架屏、发灰的刷新态，也没有弹窗外的灰色遮罩
- [ ] 转场时卡片尺寸平滑变化，同一页面衔接处画面不跳，没有两张卡片的重影
- [ ] 高亮框和标签对准目标，标签不压其他高亮或点击目标，同时最多两个高亮
- [ ] 涟漪与原片中的点击帧重合
- [ ] 卡片、标题、字幕三者互不重叠，字幕不遮挡关键界面
- [ ] 所有人名、手机号、客户名、下拉框中的姓名或工号都已模糊（逐帧放大检查表格和弹窗）
- [ ] 结尾：卡片缩小 → 关键词链 → 两行文案 → 淡出，节奏与配乐的解决点一致

## 声音（`asr_mix.py`）

- [ ] 混音逐句 ASR 的平均字错率不超过约 5%，剩余差异都是同音字
- [ ] 句首没有被音效或音乐吃掉（某句开头错了，先查它前面 0.5 s 内的音效）
- [ ] 每个点击有 tick，成功提示有 chime，whoosh 与句首至少间隔 0.4 s
- [ ] 句与句之间不重叠（`voiceover.py` 打印的时长 + start 小于下一句的 start）

## 文案与真实性

- [ ] 字幕与旁白逐字一致，没有错字，句末不带逗号，每行不超过约 16 字
- [ ] 每句旁白描述的功能都能在同一时间段的画面里看到
- [ ] 没有伪造的成功提示、业务结果、页面或 Logo；原片没有的结果写进素材缺口

## 交付文档（`deliverables/vN/`）

| 文件 | 来源 |
|---|---|
| `<OUT_NAME>.mp4`、`subtitles.srt`、`voiceover-script.txt` | `build.sh` 自动生成 |
| `storyboard.jpg` | `python3 tools/review.py storyboard` |
| `shot-list.md` | 手写，格式照搬 `deliverables/v2/shot-list.md`：开头说明原片来源和分辨率、坐标约定、转场方式；表格列为「镜头 / 成片时间 / 原片时间 / 展示的真实功能 / 裁切放大 / 屏幕标题·旁白 / 敏感信息与缺陷处理」；然后列出「未使用的原片段落」和舍弃原因 |
| `DELIVERY.md` | 手写，格式照搬 `deliverables/v2/DELIVERY.md`：交付物表、相对上一版的改动（如有）、**实测**的质检结果（数值来自上面的命令）、素材缺口与补录建议、素材与授权 |

最后更新 `deliverables/CHANGELOG.md`（版本表加一行，并写一节反馈原话和改动要点）和 `README.md` 的版本表。
