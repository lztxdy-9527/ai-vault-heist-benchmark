# 《阴间地牢》下半场 · 七席 Token 与原生用量台账

2026-11-19 JST。前 40 分钟从可定位的本场请求起算，按用量事件完成/记录时刻取窗。整场为该席本场赛题至完成的观测范围。切窗处跨界的请求整体归入其记录时刻所在窗。非缓存、缓存读取、缓存写入、输出相加为下表总量。推理列是输出中的已记录部分，勿重复累加。单位价格与账单凭证不足，原单位不转人民币或跨平台比较。

| 选手与时段 | 状态 | 非缓存输入 | 缓存读取 | 缓存写入 | 输出（含已记录推理） | 其中推理 | 总 Token |
|---|---|---:|---:|---:|---:|---:|---:|
| SOL · 前 40 分钟与整场 | 本地实测 | 218,546 | 14,444,544 | 0 | 33,474 | 11,442 | 14,696,564 |
| Carbon · 前 40 分钟 | 本地实测 | 1,025,535 | 28,990,435 | 0 | 121,839 | 56,722 | 30,137,809 |
| Carbon · 整场 | 本地实测 | 5,134,996 | 77,851,513 | 0 | 277,120 | 113,060 | 83,263,629 |
| Hydrogen · 前 40 分钟 | 本地实测 | 428,573 | 7,804,307 | 0 | 88,362 | — | 8,321,242 |
| Hydrogen · 整场 | 本地实测 | 1,884,060 | 43,465,527 | 0 | 411,018 | — | 45,760,605 |
| DeepSeek · 前 40 分钟 | 本地实测 | 83,767 | 12,171,264 | 0 | 137,320 | — | 12,392,351 |
| DeepSeek · 整场 | 本地实测 | 124,509 | 52,807,040 | 0 | 259,967 | — | 53,191,516 |
| GLM · 前 40 分钟 | 本地实测 | 422,038 | 26,887,424 | 0 | 131,476 | 92,657 | 27,440,938 |
| GLM · 整场 | 本地实测 | 510,045 | 54,435,328 | 0 | 198,685 | 135,951 | 55,144,058 |
| 混元 HY4 · 前 40 分钟 | 本地实测 | 304,288 | 15,904,512 | 0 | 111,803 | 72,416 | 16,320,603 |
| 混元 HY4 · 整场 | 本地实测 | 375,078 | 35,641,216 | 0 | 157,900 | 101,963 | 36,174,194 |
| 豆包 · 整场 | 缺失 | — | — | — | — | — | — |

## 原始来源与费用口径

| 选手 | 原生额度或费用（前 40 分钟 → 整场） | 证据 |
|---|---|---|
| SOL | 订阅用量 Token，实际费用缺失 | [Codex 主 rollout](<<LOCAL_USER_HOME>/.codex/sessions/2026/11/16/rollout-2026-11-16T04-08-45-01a1e09c-a981-7fb1-988d-14dc0b2e33c9.jsonl:748>)，再比对行 1249 |
| Carbon | 本地 cost 6.1685035 → 20.8263433，非账单 | [OpenCode](<<LOCAL_USER_HOME>/.local/share/opencode/opencode.db>)，`ses_e1f81f5d2ffeEcNqEZUPLt4y8T` |
| Hydrogen | 实际费用缺失 | [AGY](<<LOCAL_USER_HOME>/.gemini/antigravity/brain/8f2819f2-dbcb-4245-9911-819a9edbbff3/.system_generated/logs/transcript.jsonl:334>)，第 334–838 行 |
| DeepSeek | 整场 ¥2.2205178，前 40 分钟金额无分拆 | [DSH 会话](<<LOCAL_USER_HOME>/.dsh/sessions/--REPO-part2_full-exam_rooms-P2_07_deepseek_dsh--/session-a11cda84-af09-4635-97b0-2a5db66db350/session.v4.jsonl.zstd>) |
| GLM | 记录 cost=0；订阅额度/实付未确认 | [OpenCode](<<LOCAL_USER_HOME>/.local/share/opencode/opencode.db>)，`ses_e1f1d00daffe6T2J1fhNxFBDC5` |
| 混元 HY4 | 187.92 → 341.67 credits | [CodeBuddy 滚动日志](<<LOCAL_USER_HOME>/AppData/Roaming/CodeBuddy CN/logs/20261119T200317/window1/exthost/Tencent-Cloud.coding-copilot/腾讯云代码助手.1.log:2095>)及[完成记录](<<LOCAL_USER_HOME>/AppData/Roaming/CodeBuddy CN/logs/20261119T200317/window1/exthost/Tencent-Cloud.coding-copilot/腾讯云代码助手.log:6371>) |
| 豆包 | 用量和账单均待补 | [Trae 本场入口](<<LOCAL_USER_HOME>/.marscode/logs/2026-11-19/servers/203417-035/connections/203417-665-2026-11-19-7f45b70d-8a9d-4619-b419-0dac53137197.log:276>) |

### 复算方法

- SOL 用主会话行 1249 减行 748，避开上半场累计。行 754–1250 的本场用时约 17:34。独立审批侧会话另记录 775,131 Token，主表未并入，避免把审批成本与选手求解混成同一字段。
- Carbon / GLM 对 OpenCode 的 `session_message` 按本场首条 user 请求、末尾 idle 切片，逐条读取本场 assistant 用量。`tokens.output` 与独立 `tokens.reasoning` 在输出栏合计。Carbon 的整场含同一任务的多次继续与收尾。
- Hydrogen 从日志行 334 的本场请求开始，对 183 条 `PLANNER_RESPONSE` 用量求和。输出采用 AGY 原生 `output_tokens`，推理拆分和价格缺失。
- DeepSeek 解开 DSH 的拼接 Zstandard 帧，对 216 条本场 `assistant/message` usage 求和，整场总数与当晚对应的 `.dshw-usage.json` 结算事件一致。金额按平台原生元保留。
- 混元 HY4 按 request ID `fe4d83df1f9d4926bd7df4bf1ff54128` 对 127 条 `notifyStepEnd` 求和，已与 `Agent execution successful with usage` 完成汇总对平，未重复累加 AgentReporter 的同一条记录。
- 豆包的 Trae 文本日志能匹配请求、终端作业和最终文件时间。日志中可见的 `last_turn_total_tokens` 出现在 20:35，早于 20:37 的本场任务，并有重复记录，不能当作本场用量。待补 Trae 会话用量导出或平台仪表盘截图。

**覆盖率**：6/7 有可归属本场的原生 Token（85.7%）。区分本地日志中的 DSH 金额、CodeBuddy credits、OpenCode cost 和可核验实付账单。现有原生单位不足以给出跨平台统一总价、人民币性价比排名或完整实付覆盖率。
