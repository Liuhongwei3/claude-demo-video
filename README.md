# 生产工单全流程管理 · 竖屏产品宣传 Demo

本仓库把一段真实的生产管理系统录屏（B 站 [BV1j8pq6oEqi](https://www.bilibili.com/video/BV1j8pq6oEqi/)）程序化地剪成 1080×1920 的中文竖屏宣传片，并按版本管理。

| 版本 | 成片 | 说明 |
|---|---|---|
| v2（最新） | [`deliverables/v2/production-workflow-demo.mp4`](deliverables/v2/production-workflow-demo.mp4) | 50.8 s，女声，画面更大，形变叠化转场 |
| v1 | [`deliverables/v1/production-workflow-demo.mp4`](deliverables/v1/production-workflow-demo.mp4) | 28.8 s，男声，首版 |

各版本的旁白、字幕、镜头清单和交付说明在 `deliverables/<版本>/` 下，版本差异见 [`deliverables/CHANGELOG.md`](deliverables/CHANGELOG.md)。

## 目录

```
tools/fetch_bilibili.py          从 B 站拉取原片（WBI 签名接口，可选 SESSDATA 获取 1080P/4K）
tools/eval_voices.py             TTS 音色评测（ASR 字错率、基频、语速）
tools/asr_mix.py                 对混音成片逐句做 ASR，检查配音清晰度
tools/frame.py / activity.py     查看原片帧（带参考坐标网格）、定位原片中的点击和加载时刻
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
cp -r project/versions/v2 project/versions/v3   # 在副本上修改 edl.py / script.py
./project/build.sh                              # 自动构建最新的 v3，输出到 deliverables/v3/
```

- 改文案或字幕：编辑 `script.py`。
- 改镜头、构图或节奏：编辑 `edl.py`。坐标统一使用 1280×720 参考坐标；`s` 是放大倍数，`h` / `w` 是卡片尺寸。
- 改版式：设置 `edl.py` 里的 `LAYOUT`（卡片尺寸、标题和字幕位置、渐变时长、`morph` 转场等），未设置的项沿用 v1 的默认值（见 `project/config.py`）。
- 换真人配音：覆盖 `build/<v>/vo/line_XX.wav`，运行 `VIDEO_VERSION=<v> python3 project/audio.py` 和 `project/subtitles.py`，再执行 `build.sh` 末尾的 ffmpeg 封装命令即可，不需要重新渲染画面。
