# 生产工单全流程管理 · 竖屏产品宣传 Demo

本仓库把一段真实的生产管理系统录屏（B 站 [BV1j8pq6oEqi](https://www.bilibili.com/video/BV1j8pq6oEqi/)）程序化地剪成一条 28.8 秒、1080×1920 的中文竖屏宣传片。

- 成片：[`deliverables/production-workflow-demo.mp4`](deliverables/production-workflow-demo.mp4)
- 旁白 / 字幕 / 镜头清单 / 交付说明：见 [`deliverables/`](deliverables/)

## 目录

```
tools/fetch_bilibili.py   从 B 站拉取原片（WBI 签名接口，可选 SESSDATA 获取 1080P/4K）
project/script.py         文案：旁白、字幕断行、屏幕标题、收尾文案
project/edl.py            剪辑决策表：镜头、原片时间映射、虚拟镜头关键帧、高亮/涟漪/模糊、音效点
project/voiceover.py      离线中文 TTS（Kokoro v1.1-zh）+ ASR 自检
project/audio.py          合成背景音乐与音效，配音压低音乐、响度标准化
project/render.py         逐帧渲染：解码 → 裁切缩放 → 卡片/动效/字幕 → H.264
project/subtitles.py      生成 SRT 与旁白文案
project/build.sh          一键构建
deliverables/             交付物
```

## 环境准备

```bash
./project/setup.sh                                   # ffmpeg、字体、Python 依赖、离线 TTS/ASR 模型
python3 tools/fetch_bilibili.py BV1j8pq6oEqi source/ # 生成 source/source.mp4（未登录为 720P）
```

如需 4K 或 1080P 原片，可以带上自己账号的 Cookie，原片会被替换为高清版本，所有镜头坐标自动适配：

```bash
BILIBILI_SESSDATA=xxxx python3 tools/fetch_bilibili.py BV1j8pq6oEqi source/
```

## 构建

```bash
./project/build.sh                       # 约 1.5 分钟，输出 deliverables/production-workflow-demo.mp4
python3 project/render.py --stills 5.5 12.9   # 只渲染几张静帧到 build/stills/ 预览构图
```

常见修改：

- 改文案或字幕：编辑 `project/script.py`，然后重跑 `build.sh`。
- 改镜头、构图或节奏：编辑 `project/edl.py`。坐标统一使用 1280×720 参考坐标；`s` 是放大倍数，`h` 是卡片高度。
- 换真人配音：覆盖 `build/vo/line_XX.wav`，依次运行 `python3 project/audio.py`、`python3 project/subtitles.py`，再执行 `build.sh` 末尾的 ffmpeg 封装命令即可，不需要重新渲染画面。
