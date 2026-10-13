"""Copy deck: voice-over lines, on-screen headlines and closing copy (single source of truth)."""

VOICE_SID = 68  # Kokoro v1.1-zh male voice, picked by ASR intelligibility + steady ~103 Hz pitch

# start = voice-over start time (s) in the final cut; speed = Kokoro speaking-rate factor
VO_LINES = [
    {"start": 0.40, "text": "工单、工序与任务，一个系统高效协同。", "speed": 1.2},
    {"start": 4.45, "text": "点击工单，即可查看完整工序链路与各工序任务。", "speed": 1.12},
    {"start": 9.05, "text": "工序可按需插入调整，让生产流程更灵活。", "speed": 1.12},
    {"start": 13.95, "text": "执行人员在个人工作台查看任务与进度，直接报工。", "speed": 1.12},
    {"start": 18.85, "text": "负责人统一管理任务，支持批量派发。", "speed": 1.12},
    {"start": 23.05, "text": "从工单到执行反馈，让生产流程清晰、灵活、高效。", "speed": 1.08},
]

# Burned-in subtitle line breaks (the SRT keeps the plain sentence).
SUBTITLE_BREAKS = {
    1: ["点击工单，即可查看", "完整工序链路与各工序任务"],
    3: ["执行人员在个人工作台", "查看任务与进度，直接报工"],
    5: ["从工单到执行反馈", "让生产流程清晰、灵活、高效"],
}
SUBTITLE_HIDE_AFTER = {5: 26.05}  # closing copy takes over on screen

# (t_in, t_out, kicker, headline)
HEADLINES = [
    (0.15, 4.05, "生产工单全流程管理", "让生产工单，真正流转起来"),
    (4.05, 8.75, "01  工单详情 · 工序链路", "工序链路，一目了然"),
    (8.75, 13.70, "02  工序动态调整", "工序灵活调整，流程随需演进"),
    (13.70, 16.30, "03  个人工作台 · 执行人员", "任务直达个人工作台"),
    (16.30, 18.65, "03  个人工作台 · 执行人员", "执行进度，及时反馈"),
    (18.65, 22.85, "04  任务派发管理 · 负责人", "任务集中管理，支持批量派发"),
    (22.85, 25.20, "生产协同闭环", "一条链路，串起生产全流程"),
]

CLOSING_CHAIN = ["工单", "工序", "任务", "派发", "报工", "演进"]
CLOSING_LINE_1 = "从工单生成，到任务执行与反馈"
CLOSING_LINE_2 = "让生产流程清晰、灵活、高效"
