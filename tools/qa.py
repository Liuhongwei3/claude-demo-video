"""Automatic QA of a delivered cut -> deliverables/<module>/<version>/qa-report.md (+ DELIVERY.md for spec versions).

    VIDEO=inventory/v1 python3 tools/qa.py

Measured: container / codec specs, loudness and true peak, per-line ASR of the mix, subtitle length and
punctuation, card / headline / subtitle overlap for every camera keyframe. What a machine cannot judge
(loading frames, alignment of highlights, privacy) stays a manual checklist: review the sheets from
tools/review.py, then record the findings under `review_notes:` in spec.yaml.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "project"))
sys.path.insert(0, str(ROOT / "tools"))
import config  # noqa: E402
import style as house  # noqa: E402

MANUAL = [
    "没有浏览器栏、任务栏、录屏工具界面、水印",
    "没有加载白屏、骨架屏、发灰的刷新态、弹窗外灰色遮罩",
    "转场平滑，同页衔接不跳，没有两张卡片的重影",
    "高亮和标签对准目标，标签不压其他高亮或点击目标；涟漪与原片点击帧重合",
    "所有人名、手机号、客户名、下拉框中的姓名或工号已模糊",
    "旁白描述的功能在同一时间段画面中可见，没有伪造的结果、页面或 Logo",
]


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,codec_name,profile,width,height,r_frame_rate,pix_fmt,"
                          "sample_rate,channels", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def loudness(path):
    err = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summary = err[err.rfind("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    tp = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary).group(1))
    return i, tp


def layout_checks():
    edl, L = config.edl, config.LAYOUT
    top_limit = L["title_y"] + L["title_size"] + 16
    bottom_limit = L["sub_top"] - 12
    bad = []
    for sh in edl.SHOTS:
        for k in sh["cam"]:
            ccy, h = k.get("ccy", L["card_cy"]), k.get("h")
            if h is None:
                continue
            if ccy - h / 2 < top_limit - 1 or ccy + h / 2 > bottom_limit + 1:
                bad.append(f"{sh['id']} @ {k['t']:.2f}s: card {ccy - h / 2:.0f}-{ccy + h / 2:.0f} px "
                           f"(free area {top_limit}-{bottom_limit})")
    return bad


def subtitle_checks():
    s = config.script
    maxc = house.SUBTITLE["max_chars"] + 2
    bad = []
    for i, line in enumerate(s.VO_LINES):
        rows = getattr(s, "SUBTITLE_BREAKS", {}).get(i) or [line["text"].rstrip("。，")]
        for r in rows:
            if len(r) > maxc:
                bad.append(f"line {i + 1}: row longer than {maxc} chars: {r}")
            if r.endswith(("，", "、")):
                bad.append(f"line {i + 1}: row ends with punctuation: {r}")
    return bad


def main():
    mp4 = config.DELIVER / f"{config.OUT_NAME}.mp4"
    edl = config.edl
    rows, fails = [], 0

    def item(ok, name, detail):
        nonlocal fails
        fails += not ok
        rows.append(f"| {'通过' if ok else '**未通过**'} | {name} | {detail} |")

    j = probe(mp4)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), {})
    dur = float(j["format"]["duration"])
    item((v["width"], v["height"]) == (1080, 1920) and v["r_frame_rate"] == "30/1", "画面规格",
         f"{v['width']}×{v['height']}，{v['r_frame_rate']} fps，{v['codec_name']} {v.get('profile', '')}，{v.get('pix_fmt')}")
    item(a.get("codec_name") == "aac" and a.get("sample_rate") == "48000" and a.get("channels") == 2, "音频规格",
         f"{a.get('codec_name')} {a.get('sample_rate')} Hz，{a.get('channels')} 声道")
    item(abs(dur - edl.DURATION) < 0.1, "时长", f"{dur:.3f} s（剪辑表 {edl.DURATION} s）")
    lufs, tp = loudness(mp4)
    item(abs(lufs + 16) <= 1.0 and tp <= -1.0, "响度", f"{lufs:.1f} LUFS，真峰值 {tp:.1f} dBTP（目标 −16 LUFS / ≤ −1 dBTP）")

    asr_rows = []
    try:
        from asr_mix import check
        res = check()
        mean = float(np.mean([r[0] for r in res]))
        item(mean <= 0.06, "配音清晰度", f"混音逐句 ASR 平均字错率 {mean:.3f}（≤ 0.06；同音字差异可接受）")
        asr_rows = [f"| {e:.2f} | {t} | {h} |" for e, t, h in res]
    except Exception as e:  # ASR model missing etc.
        item(False, "配音清晰度", f"未能运行 ASR：{e}")

    sub_bad = subtitle_checks()
    item(not sub_bad, "字幕", "每行长度和句末标点正常" if not sub_bad else "；".join(sub_bad))
    lay_bad = layout_checks()
    item(not lay_bad, "版面", "卡片不与标题、字幕区域重叠" if not lay_bad else "；".join(lay_bad))

    out = [f"# 自动质检报告 · {config.VIDEO}", "", f"成片：`{mp4.relative_to(ROOT)}`", "",
           "| 结果 | 项目 | 实测 |", "|---|---|---|", *rows, ""]
    if asr_rows:
        out += ["## 混音逐句 ASR", "", "| 字错率 | 旁白 | 识别结果 |", "|---|---|---|", *asr_rows, ""]
    out += ["## 需人工确认（查看 tools/review.py 生成的联系表）", ""] + [f"- [ ] {m}" for m in MANUAL] + [""]
    (config.DELIVER / "qa-report.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(rows))
    print(config.DELIVER / "qa-report.md")

    spec_path = config.DIR / "spec.yaml"
    if spec_path.exists():
        write_delivery(yaml.safe_load(spec_path.read_text(encoding="utf-8")), mp4, dur, rows)
    sys.exit(1 if fails else 0)


def write_delivery(spec, mp4, dur, rows):
    d = config.DELIVER
    size = mp4.stat().st_size / 1e6
    out = [f"# 交付说明 · {spec.get('module', config.MODULE)}产品宣传 Demo（{config.VIDEO}）", "",
           "本文件由 `tools/qa.py` 根据 spec.yaml 和实测结果生成。", "", "## 交付物", "",
           "| 文件 | 说明 |", "|---|---|",
           f"| `{mp4.name}` | 成片：1080×1920 竖屏，30 fps，H.264 / AAC，时长 {dur:.1f} s，约 {size:.0f} MB |",
           "| `voiceover-script.txt` | 旁白文案（带时间码）、屏幕主标题、收尾文案 |",
           "| `subtitles.srt` | 简体中文字幕，与旁白逐句同步（成片已烧录） |",
           "| `shot-list.md` | 镜头清单：原片时间、展示的真实功能、裁切放大、旁白、敏感信息处理 |",
           "| `storyboard.jpg` | 分镜缩略图 |",
           "| `qa-report.md` | 自动质检明细 |",
           f"| `../../../project/versions/{config.VIDEO}/spec.yaml` | 本版的功能描述、镜头清单与旁白，"
           f"`VIDEO={config.VIDEO} ./project/build.sh` 一键复现 |", ""]
    feats = [s for s in spec.get("sections", []) if s.get("kind", "feature") == "feature"]
    if feats:
        out += ["## 展示的功能", ""] + [f"- **{s.get('title', '')}**：{s.get('desc', '')}" for s in feats] + [""]
    if spec.get("changes"):
        out += ["## 相对上一版的改动", ""] + [f"- {c}" for c in spec["changes"]] + [""]
    out += ["## 质检结果", "", "| 结果 | 项目 | 实测 |", "|---|---|---|", *rows, ""]
    if spec.get("review_notes"):
        out += ["人工检查（逐帧查看联系表和转场）：", ""] + [f"- {n}" for n in spec["review_notes"]] + [""]
    if spec.get("gaps"):
        out += ["## 素材缺口", ""] + [f"- {g}" for g in spec["gaps"]] + [""]
    out += ["## 素材与授权", "",
            "- 产品界面只使用提供的录屏，没有登录或修改任何业务系统数据。",
            "- 背景音乐和音效由代码合成（`project/audio.py`），不含第三方音频。",
            "- 配音为离线 TTS（Kokoro v1.1-zh，Apache-2.0），字体为思源黑体（SIL OFL 1.1），均可商用。", ""]
    (d / "DELIVERY.md").write_text("\n".join(out), encoding="utf-8")
    print(d / "DELIVERY.md")


if __name__ == "__main__":
    main()
