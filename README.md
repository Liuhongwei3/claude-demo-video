# 产品宣传视频生产模板（录屏 → 9:16 竖屏）

把业务系统录屏程序化地做成 1080×1920 中文竖屏产品宣传视频。所有模块共用一套视觉语言和制作流程（生产工单、库存管理、质量追溯、采购管理等）。每次只需要提供新录屏，并编写一份 `spec.yaml`：

- **功能描述**：每个功能点证明了什么；
- **镜头清单**：每个镜头用原片哪一段、展示哪块区域、高亮什么、点击在哪；
- **旁白**：每句话的文案。

时间线、机位缓动、形变叠化转场、高亮动效、屏幕标题、字幕断行、收尾动画、女声配音、配乐与音效，全部按统一规范（`project/style.py`）自动生成；最后自动质检，并输出交付文档。

**怎么用（Cursor、Claude Code、其他 Agent 或手动）见 [docs/USAGE.md](docs/USAGE.md)。** Agent 执行时遵循的 Skill 是 [skills/screen-recording-promo/SKILL.md](skills/screen-recording-promo/SKILL.md)。

## 已有视频

| 模块 / 版本 | 成片 | 说明 |
|---|---|---|
| 生产工单 v3（最新） | [`deliverables/production-order/v3/`](deliverables/production-order/v3/) | v2 的同一套剪辑改用 spec 编写，作为模板的标准示例（[spec.yaml](project/versions/production-order/v3/spec.yaml)），49.9 s |
| 生产工单 v2 | [`deliverables/production-order/v2/`](deliverables/production-order/v2/) | 50.8 s，女声，大卡片，形变叠化。视觉规范即来源于此版 |
| 生产工单 v1 | [`deliverables/production-order/v1/`](deliverables/production-order/v1/) | 历史版本，只保留成片和文档（源文件见 git 标签 `video-v1`） |

版本记录见 [`deliverables/production-order/CHANGELOG.md`](deliverables/production-order/CHANGELOG.md)。

## 快速开始

```bash
./project/setup.sh                                                   # 首次：ffmpeg、思源黑体、Python 依赖、离线 TTS/ASR 模型
python3 tools/fetch_bilibili.py BV1j8pq6oEqi source/                 # 示例原片 → source/source.mp4
VIDEO=production-order/v3 ./project/build.sh                         # 构建示例，约 3 分钟

# 新模块
python3 tools/ingest.py ~/Downloads/库存.mp4 --name inventory
python3 tools/new_video.py inventory --title 库存管理 --source source/inventory/source.mp4
export VIDEO=inventory/v1
python3 tools/survey.py                                              # 摸底录屏
# 编辑 project/versions/inventory/v1/spec.yaml
python3 project/compile_spec.py --estimate                           # 草稿：时间线与警告
./project/build.sh                                                   # 成片 + 文档 + 自检
```

## 目录

```
skills/screen-recording-promo/   Skill 正本：流程、规则、spec 字段参考、各模块叙事建议、自检清单
.cursor/skills/  .claude/skills/  Cursor 与 Claude Code 的 Skill 入口（指向正本）
AGENTS.md  CLAUDE.md             给各类编码 Agent 的项目规则
docs/USAGE.md                    使用指南

project/style.py                 统一视觉规范：版式、配色、镜头节奏、配音、配乐
project/templates/spec.yaml      新模块的 spec 骨架（全部字段带注释）；NOTES.md 为素材地图模板
project/compile_spec.py          spec.yaml → edl.py + script.py（自动排时间线）+ shot-list.md
project/versions/<模块>/<版本>/   spec.yaml（手写）、NOTES.md、edl.py / script.py（生成）
project/build.sh                 一键构建：编译 → 配音 → 配乐 → 渲染 → 字幕 → 封装 → 分镜 → 质检
project/voiceover.py             离线中文 TTS（Kokoro v1.1-zh）+ ASR 自检
project/audio.py                 合成配乐与音效，配音时压低音乐，响度标准化
project/render.py                逐帧渲染：解码 → 虚拟镜头裁切放大 → 卡片 / 转场 / 动效 / 字幕 → H.264
project/subtitles.py             SRT 与旁白文案
project/config.py                VIDEO=<模块>/<版本> 选择视频

tools/ingest.py                  导入录屏（本地或 B 站），转为 30 fps 恒定帧率
tools/new_video.py               新建模块或下一个版本
tools/survey.py                  录屏摸底：稳定画面状态 + 缩略图，标记可疑加载
tools/source_sheet.py            原片某段时间的时间码联系表
tools/frame.py / activity.py     带坐标网格的单帧；按帧差定位点击和加载
tools/review.py                  成片联系表（全片 / 逐转场）与分镜图
tools/qa.py                      自动质检，生成 qa-report.md 与 DELIVERY.md
tools/eval_voices.py / asr_mix.py  音色评测；混音逐句 ASR

deliverables/<模块>/<版本>/       成片、字幕、旁白、镜头清单、分镜、质检报告、交付说明
```
