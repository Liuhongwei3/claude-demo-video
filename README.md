# 生产工单全流程管理 · 竖屏产品宣传 Demo

本仓库把一段真实的生产管理系统录屏（B 站 [BV1j8pq6oEqi](https://www.bilibili.com/video/BV1j8pq6oEqi/)）程序化地剪成 1080×1920 的中文竖屏宣传片，并按版本管理。

| 版本 | 成片 | 说明 |
|---|---|---|
| v2（最新） | [`deliverables/v2/production-workflow-demo.mp4`](deliverables/v2/production-workflow-demo.mp4) | 50.8 s，女声，画面更大，形变叠化转场 |
| v1 | [`deliverables/v1/production-workflow-demo.mp4`](deliverables/v1/production-workflow-demo.mp4) | 28.8 s，男声，首版 |

各版本的旁白、字幕、镜头清单和交付说明在 `deliverables/<版本>/` 下，版本差异见 [`deliverables/CHANGELOG.md`](deliverables/CHANGELOG.md)。

## 目录

```
.cursor/skills/screen-recording-promo/   Cursor Skill：用新录屏按 v2 效果制作竖屏 Demo 的完整流程与规范
tools/ingest.py                  导入录屏（本地文件或 B 站），统一转为 30 fps 恒定帧率 → source/<名称>/source.mp4
tools/fetch_bilibili.py          从 B 站拉取原片（WBI 签名接口，可选 SESSDATA 获取 1080P/4K）
tools/new_version.py             从已有版本或 _template 新建版本，并指定原片
tools/survey.py                  原片摸底：划分稳定画面状态，输出缩略图联系表和时间表
tools/source_sheet.py            原片某段时间的时间码联系表（可裁切）
tools/frame.py / activity.py     查看原片帧（带参考坐标网格）、按帧差定位点击和加载时刻
tools/review.py                  成片自检联系表（全片 / 逐转场）和分镜图 storyboard.jpg
tools/eval_voices.py             TTS 音色评测（ASR 字错率、基频、语速），可用本版文案评测
tools/asr_mix.py                 对混音成片逐句做 ASR，检查配音清晰度
project/edlkit.py                编写 edl.py 用的辅助函数（kf / hl / sweep / ripple / blur）和 v2 版式预设
project/versions/_template/      新录屏的版本骨架（edl.py、script.py、素材地图 NOTES.md）
project/versions/<v>/script.py   该版本的文案：旁白、字幕断行、屏幕标题、收尾文案
project/versions/<v>/edl.py      该版本的剪辑决策表：镜头、原片时间映射、虚拟镜头关键帧、
                                 高亮/涟漪/模糊、音效点、版式（LAYOUT）、配乐参数（MUSIC）
project/config.py                按 VIDEO_VERSION 选择版本（默认最新），决定 build/<v>/ 和 deliverables/<v>/
project/voiceover.py             离线中文 TTS（Kokoro v1.1-zh）+ ASR 自检
project/audio.py                 合成背景音乐与音效，配音压低音乐、响度标准化
project/render.py                逐帧渲染：解码 → 裁切缩放 → 卡片/转场/动效/字幕 → H.264
project/subtitles.py             生成 SRT 与旁白文案
project/build.sh                 一键构建
deliverables/<v>/                各版本交付物
```

## 环境准备

```bash
./project/setup.sh                                   # ffmpeg、字体、Python 依赖、离线 TTS/ASR 模型
python3 tools/fetch_bilibili.py BV1j8pq6oEqi source/ # 生成 source/source.mp4（未登录为 720P）
```

如需 4K 或 1080P 原片，可以带上自己账号的 Cookie。原片会被替换为高清版本，所有镜头坐标自动适配：

```bash
BILIBILI_SESSDATA=xxxx python3 tools/fetch_bilibili.py BV1j8pq6oEqi source/
```

## 构建

```bash
./project/build.sh                          # 构建最新版本（v2），约 3.5 分钟
VIDEO_VERSION=v1 ./project/build.sh         # 重新构建旧版本
VIDEO_VERSION=v2 python3 project/render.py --stills 5.5 12.9   # 只渲染几张静帧到 build/v2/stills/
```

## 新建一个版本

```bash
python3 tools/new_version.py v3 --from v2       # 同一段录屏改剪辑：复制 v2，在副本上修改 edl.py / script.py
./project/build.sh                              # 自动构建最新的 v3，输出到 deliverables/v3/
```

## 用新录屏制作同样效果的视频

完整流程、规则和踩坑记录写在 Skill [`.cursor/skills/screen-recording-promo/SKILL.md`](.cursor/skills/screen-recording-promo/SKILL.md) 中。在 Cursor 里提供录屏并说明要做竖屏 Demo，Agent 会按这个 Skill 执行。手动操作的骨架如下：

```bash
python3 tools/ingest.py ~/录屏.mp4 --name order-flow                         # 或 B 站 BV 号
python3 tools/new_version.py v3 --from _template --source source/order-flow/source.mp4
python3 tools/survey.py                                                    # 摸底，填写 project/versions/v3/NOTES.md
# 编写 script.py → python3 project/voiceover.py → 按配音时长编写 edl.py
python3 project/render.py --stills 3.5 8.0                                 # 静帧迭代
./project/build.sh && python3 tools/review.py sheets && python3 tools/asr_mix.py
```

- 改文案或字幕：编辑 `script.py`。
- 改镜头、构图或节奏：编辑 `edl.py`。坐标统一使用 1280 px 宽的参考坐标（16:9 原片即 1280×720）；`s` 是放大倍数，`h` / `w` 是卡片尺寸。
- 改版式：设置 `edl.py` 里的 `LAYOUT`（卡片尺寸、标题和字幕位置、渐变时长、`morph` 转场等），未设置的项沿用 v1 的默认值（见 `project/config.py`）。
- 换真人配音：覆盖 `build/<v>/vo/line_XX.wav`，运行 `VIDEO_VERSION=<v> python3 project/audio.py` 和 `project/subtitles.py`，再执行 `build.sh` 末尾的 ffmpeg 封装命令即可，不需要重新渲染画面。
