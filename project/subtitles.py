"""Write deliverables/<version>/subtitles.srt and voiceover-script.txt from the copy deck."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "project"))
from config import BUILD, DELIVER, edl, script  # noqa: E402

OUT = DELIVER


def ts(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    info = json.loads((BUILD / "vo/durations.json").read_text())
    blocks = []
    for i, (line, meta) in enumerate(zip(script.VO_LINES, info)):
        start = line["start"]
        end = start + meta["duration"] + 0.25
        if i + 1 < len(script.VO_LINES):
            end = min(end, script.VO_LINES[i + 1]["start"] - 0.08)
        end = min(end, edl.DURATION)
        rows = script.SUBTITLE_BREAKS.get(i) or [line["text"]]
        text = "\n".join(r.rstrip("。，") for r in rows)
        blocks.append(f"{i + 1}\n{ts(start)} --> {ts(end)}\n{text}\n")
    (OUT / "subtitles.srt").write_text("\n".join(blocks), encoding="utf-8")

    shots = getattr(script, "VO_SECTIONS", None) or [
        f"镜头{i + 1} · {name}" for i, name in enumerate([
            "开场钩子", "工单详情与工序链路", "工序动态调整", "个人工作台与任务报工",
            "负责人任务管理与批量派发", "价值收束"])]
    lines = ["《生产工单全流程管理》产品宣传短视频 · 旁白文案",
             f"总时长 {edl.DURATION:.1f} 秒 | {getattr(script, 'VOICE_DESC', '普通话男声，沉稳专业 | 语速约 4.5 字/秒')}", ""]
    for i, (line, meta, name) in enumerate(zip(script.VO_LINES, info, shots)):
        st = line["start"]
        lines.append(f"[{st:05.2f}s – {st + meta['duration']:05.2f}s] {name}")
        lines.append(f"    {line['text']}")
        lines.append("")
    lines += ["画面主标题（屏幕大字）："]
    lines += [f"    [{a:05.2f}s – {b:05.2f}s] {title}" for a, b, _, title in script.HEADLINES]
    lines += ["", "收尾文案：", f"    {script.CLOSING_LINE_1}", f"    {script.CLOSING_LINE_2}", ""]
    (OUT / "voiceover-script.txt").write_text("\n".join(lines), encoding="utf-8")
    print("wrote", OUT / "subtitles.srt", "and", OUT / "voiceover-script.txt")


if __name__ == "__main__":
    main()
