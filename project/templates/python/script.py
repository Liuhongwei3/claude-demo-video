"""Copy deck -- skeleton. Every claim must be visible in the recording (no invented results)."""

TITLE = "产品名称"                 # TODO: shown in metadata / voiceover-script.txt
OUT_NAME = "product-demo"          # deliverables/<version>/<OUT_NAME>.mp4

VOICE_SID = 21    # Kokoro v1.1-zh: 3-57 female, 58-102 male; compare with tools/eval_voices.py
TRIM_PAD = 0.06
VOICE_DESC = "普通话女声，干练清晰 | 语速约 4.9 字/秒"

# start = VO start (s) in the cut; speed 1.36-1.42 ~ 4.9 chars/s. Optional per line:
# "say" = text actually spoken (to dodge ASR / TTS misreads), "sid" = other voice.
VO_LINES = [
    {"start": 0.40, "text": "痛点问题一句话？", "speed": 1.36},
    {"start": 3.20, "text": "产品一句话价值。", "speed": 1.42},
    {"start": 6.30, "text": "功能一：画面里正在发生的操作，", "speed": 1.42},
    {"start": 9.20, "text": "以及它带来的结果。", "speed": 1.42},
    {"start": 12.20, "text": "收尾价值主张，清晰、灵活、高效。", "speed": 1.36},
]

VO_SECTIONS = ["镜头1 · 开场钩子", "镜头1 · 开场钩子", "镜头2 · 功能一", "镜头2 · 功能一", "镜头3 · 价值收束"]

SUBTITLE_BREAKS = {
    # 2: ["功能一", "画面里正在发生的操作"],       # lines > ~16 chars: split into two rows
}
SUBTITLE_HIDE_AFTER = {4: 15.6}  # closing copy takes over on screen

# (t_in, t_out, kicker, headline)
HEADLINES = [
    (0.15, 5.90, "产品名称", "一句话主张"),
    (5.90, 11.60, "01  功能一", "功能一标题"),
    (11.60, 14.40, "闭环", "收束标题"),
]

CLOSING_CHAIN = ["步骤一", "步骤二", "步骤三", "步骤四"]
CLOSING_LINE_1 = "收尾第一行"
CLOSING_LINE_2 = "收尾第二行"
