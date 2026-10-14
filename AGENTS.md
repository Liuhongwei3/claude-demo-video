# Agent 说明

本仓库是「产品宣传视频生产模板」：把业务系统录屏做成 1080×1920 中文竖屏宣传视频，所有模块共用一套视觉规范。

- 用户要求根据录屏制作或修改宣传 / 演示视频时，先读取并严格遵循 `skills/screen-recording-promo/SKILL.md`。
- 回复和交付文档使用简体中文。
- 每个视频只编辑 `project/versions/<模块>/<版本>/spec.yaml`（以及素材地图 `NOTES.md`）。同目录下的 `edl.py` 和 `script.py` 由编译器生成，不要手改。
- `project/style.py` 是所有模块共用的视觉规范，不要为单个视频修改它；需要局部调整时，用 spec 的 `style:` 覆盖。
- 已交付的版本（`deliverables/<模块>/<版本>/`）不再修改；有新反馈就用 `tools/new_video.py` 创建下一个版本。
- 构建与自检：`VIDEO=<模块>/<版本> ./project/build.sh`。`tools/qa.py` 未通过时，不要交付。
- 环境准备：`./project/setup.sh`（ffmpeg、思源黑体、Python 依赖、`.cache/tts` 下的离线 TTS / ASR 模型）。
