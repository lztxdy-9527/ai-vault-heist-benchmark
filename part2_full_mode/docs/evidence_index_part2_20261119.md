# 《阴间地牢》下半场 · 已完成七席取证索引

范围为 2026-11-19 的 SOL、Carbon、Hydrogen、DeepSeek、GLM、混元 HY4、豆包。日期和时刻均为 JST（UTC+9）。Astra、Qwen、Opus、Neon 暂未纳入。

用时以每席第一条能识别为本场的请求至答复、请求结束或终端活动为准，另记当前 `submission.py` 最后写入。时长以原生时间戳计算、秒级显示，包含等待和续跑。七席目录均未找到正式 `.exam_start_ts` 或 `CUTOFF_40m00s_*.py`，所以“前 40 分钟”是从请求起点回推的审计窗口，**七席正式卡点版本均未确认**。BASELINE 的时间是准备考场时间，DeepSeek 的 FINAL_SUBMIT 是会话制作的快照。

| 选手 | 本场起点 | 当前稿最后写入 | 结束或最后活动 | 会话经过 | 超过 40:00 |
|---|---:|---:|---:|---:|---:|
| SOL | 20:22:12 | 20:36:17（14分05秒） | 20:39:46 | 17分34秒 | 0秒 |
| Carbon | 20:10:14 | 22:13:32（123分18秒） | 22:23:52 | 133分38秒 | 93分38秒 |
| Hydrogen | 20:24:19 | 22:04:15（99分56秒） | 22:05:38 | 101分19秒 | 61分19秒 |
| DeepSeek | 20:17:25 | 21:51:51（94分26秒） | 21:52:50 | 95分25秒 | 55分25秒 |
| GLM | 20:11:16 | 21:17:02（65分45秒） | 21:19:51 | 68分34秒 | 28分34秒 |
| 混元 HY4 | 20:08:05 | 21:10:06（62分01秒） | 21:11:22 | 63分17秒 | 23分17秒 |
| 豆包 | 20:37:29 | 22:32:20（114分51秒） | 22:34:20（最后相关操作） | 至少 116分51秒 | 至少 76分51秒 |

## 作答与剪辑定位

- **SOL** · 20:22:12 开始，约 20:29 建立回归脚本，20:30–20:36 多次调整地牢与跳跃储备，20:36:17 写入当前答卷，20:39:46 回复交付。求解器重点是避免过早耗掉后续咽喉所需跳跃。20:34 的第一轮结果仍能看到强基准上用光跳跃后卡在深渊的轨迹，最终复验从这个卡点翻盘。主会话行 754–1250，审批侧日志有对应写入与测试命令。[主会话](<<LOCAL_USER_HOME>/.codex/sessions/2026/11/16/rollout-2026-11-16T04-08-45-01a1e09c-a981-7fb1-988d-14dc0b2e33c9.jsonl:754>) · [中途强基准轨迹](part2_full_mode/exam_rooms/P2_02_sol_codex/results_first.txt:33)
- **Carbon** · 20:10:14 开始，20:15 本地裁判，20:20 起做求解回归，20:58:08 第一段结束后，21:23:27 用户要求继续（中间约 25 分 19 秒）。21:41:21 再续跑，22:02 后出现双端已落盘的公开回复，随后继续改压板配对、游离诱饵箱过滤与推箱宏动作，22:13:32 写入当前稿，22:23:52 收尾。可按 OpenCode `session_message.seq` 定位首次请求 606、续跑 1455/1792/2209、公开阶段稿 2043/2100/2131/2162、超时催收 2251、收尾 2252。会话 ID `ses_e1f81f5d2ffeEcNqEZUPLt4y8T`。[OpenCode 原始库](<<LOCAL_USER_HOME>/.local/share/opencode/opencode.db>) · [自测脚本](part2_full_mode/exam_rooms/P2_04_carbon_opencode/verify_submission_v22.py)
- **Hydrogen** · 20:24:19 收题，20:27/20:28 用户分别要求继续，20:31 建本地裁判、20:35 制作压力用例、20:37 开始留下独立勇者稿。21:14:49 用户追问进程，21:18:37 有错误事件，21:28 日志出现会话压缩恢复；21:46 后可见独立魔王造图，22:04:15 合并写入当前稿，22:05:38 最终回复。日志行 334、397、405、450、484、530、838。等待空档与后续重构都在壁钟内，现有证据不足以给每个空档判定原因。[AGY 原始日志](<<LOCAL_USER_HOME>/.gemini/antigravity/brain/8f2819f2-dbcb-4245-9911-819a9edbbff3/.system_generated/logs/transcript.jsonl:334>) · [合并脚本](part2_full_mode/exam_rooms/P2_05_hydrogen_agy/assemble_submission.py)
- **DeepSeek** · 20:17:25 收题；20:21–20:22 建裁判和黄金样例验证；随后对抗、本地自测及攻防重写。21:36:50 的 `v01` 标注 FULL 重构，21:50:24 的 `v02` 标注最终提交，和当前稿 SHA-256 一致，21:52:50 会话完成。原生压缩日志 `seq=4` 起、`seq=1623` 完成、`seq=1615` 为提交展示。本地自测的过关次数与官方 worker 是否允许加载，是两项独立的结果。[DSH 原始会话](<<LOCAL_USER_HOME>/.dsh/sessions/--REPO-part2_full-exam_rooms-P2_07_deepseek_dsh--/session-a11cda84-af09-4635-97b0-2a5db66db350/session.v4.jsonl.zstd>) · [版本记录](part2_full_mode/exam_rooms/P2_07_deepseek_dsh/history/timeline.jsonl) · [自测结果](part2_full_mode/exam_rooms/P2_07_deepseek_dsh/SELFTEST_RESULT.txt)
- **GLM** · 20:11:16 收题，20:25 建完整自测；20:29–21:10 留下回放、推箱停滞、冰面与 A* 的专项脚本；21:17:02 写入当前稿，21:19:51 最终回复。原生 OpenCode 会话 `ses_e1f1d00daffe6T2J1fhNxFBDC5`，`seq=670` 收题、`1985` 最终答复、`1993` 闲置结束。[OpenCode 原始库](<<LOCAL_USER_HOME>/.local/share/opencode/opencode.db>) · [推箱排查](part2_full_mode/exam_rooms/P2_08_glm_opencode/debug_stall3.py) · [最终自测](part2_full_mode/exam_rooms/P2_08_glm_opencode/test_final.py)
- **混元 HY4** · 20:08:05.750 进入 CodeBuddy 本场请求，20:24:03 首次留存 `submission.py`，之后改求解器并反复本地测试，21:10:06 写最终稿、21:11:22.520 请求完成。IDE 历史有 **26** 份保存记录。按会话起点推算，前 40 分钟内找到最后一份保存于 **20:47:50.590（39:44.840）** 的 `xYy9.py`（SHA 前缀 `a889f4bd`），官方 worker 试加载仍返回 `ValueError`。这份是有原件的回溯候选，尚无正式封卷记录。后续版本 `m1hm.py` 与当前稿逐字节相同。[请求开端](<<LOCAL_USER_HOME>/AppData/Roaming/CodeBuddy CN/logs/20261119T200317/window1/exthost/Tencent-Cloud.coding-copilot/腾讯云代码助手.1.log:2095>) · [原始保存史](<<LOCAL_USER_HOME>/AppData/Roaming/CodeBuddy CN/User/History/-58277a96/entries.json>) · [39:44 候选](<<LOCAL_USER_HOME>/AppData/Roaming/CodeBuddy CN/User/History/-58277a96/xYy9.py>) · [完成事件](<<LOCAL_USER_HOME>/AppData/Roaming/CodeBuddy CN/logs/20261119T200317/window1/exthost/Tencent-Cloud.coding-copilot/腾讯云代码助手.log:6371>)
- **豆包** · 20:37:29 Trae 路由记录题目，20:39 读取旧稿，21:12:51 日志出现写 `submission.py` 的命令。22:22–22:30 继续多次写入和验查，当前稿 mtime 为 22:32:20，22:34:20 仍有相关工具调用。最后一个时间是可见活动下限，未找到对应最终回复时间或可核算的逐次用量。[收题记录](<<LOCAL_USER_HOME>/.marscode/logs/2026-11-19/servers/203417-035/connections/203417-665-2026-11-19-7f45b70d-8a9d-4619-b419-0dac53137197.log:276>) · [写稿命令](<<LOCAL_USER_HOME>/.marscode/logs/2026-11-19/clients/203414-393-39404-vscode-2026-11-19-39404.log:1385>) · [末段工具记录](<<LOCAL_USER_HOME>/.marscode/logs/2026-11-19/servers/203417-035/connections/203417-665-2026-11-19-7f45b70d-8a9d-4619-b419-0dac53137197.log:2801>)

## 当前稿结果复验

通过现行官方 worker 加载，魔王用官方准入、自证及接口检查。可加载的三席另以 **当前稿** 对弱、强基准图各跑一局，均为满血通关。表中的回合数是游戏局内回合，不是笔试分钟。下面的结果适用于所列 SHA-256 前缀。

| 选手 | 当前稿 SHA-256 前缀 | 魔王 | 勇者 |
|---|---|---|---|
| SOL | `cecd9485` | 合格，2610G，192 步自证 | 弱 72 / 强 126 回合 |
| Carbon | `329a5198` | 合格，2930G，181 步自证 | 弱 98 / 强 131 回合 |
| Hydrogen | `8f1f2da9` | 返回的 taunt 有 61 字符，超过 40；单验格子与自证通过，2775G / 151 步 / 100 HP | 弱 98 / 强 115 回合 |
| DeepSeek | `bc1bad22` | worker 拒绝加载，`ValueError` | 同一模块无法加载，检测到第 77 行 `__slots__`、第 97 行 `__new__` |
| GLM | `a3362cd2` | worker 拒绝加载，`ValueError` | 同一模块无法加载，检测到第 182 行 `__slots__` |
| 混元 HY4 | `18e5edc8` | worker 拒绝加载，`ValueError` | 同一模块无法加载，检测到第 247 行 `__new__` |
| 豆包 | `9f951f4a` | worker 拒绝加载，`ValueError` | 同一模块无法加载，检测到第 144、173 行 `__new__` |

沙盒同时检查属性节点和名称节点。`__new__` 命中属性访问检查，`__slots__` 声明命中名称检查。DeepSeek、GLM、混元 HY4、豆包各有推算 40 分钟内的过程稿复现加载失败。七席正式卡点仍未确认。[过程稿恢复与加载复盘](part2_full_mode/audit/process_recovery_20261119/README.md) · [加载检查](part2_full_mode/submission_worker_full.py:124) · [正式赛入口](part2_full_mode/run_tournament_full.py)
