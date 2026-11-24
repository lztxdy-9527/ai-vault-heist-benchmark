# 下半场七席 · 作答决策复盘

范围为 11 月 19 日已完成的七席，时间均为 JST。选手当时的判断来自对用户可见的进度消息或最终汇报，代码和工具记录用于确认实际上改了什么。没有公开说明的动机保留为未知。对局数字分别标注本地自测或官方引擎兼容复测。

## SOL · 三次跳跃留给金库

- **20:27，先处理上半场已知失误。** SOL 公开说明，上半场最贵的错误是提前耗尽炸弹或跳跃，以及只规划下一把钥匙。这次在搜索状态里保留资源、箱位、门态和激光相位，并检查集齐钥匙后是否还有路进金库。 [阶段发言](<LOCAL_USER_HOME>/.codex/sessions/2026/11/16/rollout-2026-11-16T04-08-45-01a1e09c-a981-7fb1-988d-14dc0b2e33c9.jsonl:852)
- **20:32–20:36，强基准和自建图各暴露一次跳跃预留不足。** 中途回放显示强基准在深渊前用光跳跃。后来强基准已过，自建图仍出现压板门打开后跳跃不足的反例。SOL 加入金库最低跳跃库存检查，最终自建图第 150 回合通关，余 50 HP。官方引擎兼容复测的强基准仍为 126 回合满血通关。 [中途回放](part2_full_mode/audit/process_recovery_20261119/sol_process/results_first.txt:33) · [资源约束发言](<LOCAL_USER_HOME>/.codex/sessions/2026/11/16/rollout-2026-11-16T04-08-45-01a1e09c-a981-7fb1-988d-14dc0b2e33c9.jsonl:1052)

## Carbon · 双方都在争夺同一批箱子

- **22:02，公开解释攻守设计。** 防图把一只箱子推上看似正确的压板，就会减少后续填坑所需的箱数。勇者端则用宏动作和箱位匹配剪掉死锁。20:58 至 21:23 之间有一次可见的等待续跑间隔。第一份能恢复的完整双端稿在 22:00 落盘。 [首份恢复稿](part2_full_mode/audit/process_recovery_20261119/carbon/01_seq2013_1_submission.py)
- **22:07–22:13，先增加诱饵箱，再缩小勇者候选箱范围。** 公开进度称，修改了咽喉深渊的识别、直隧道连推、游离箱过滤，并让待压板或必经深渊优先匹配可达箱。代码重放也显示这几版主要修改求解器。官方引擎兼容复测中，Carbon 的勇者满血通关两张基准，防图守住 8 次进攻。公开消息在 OpenCode 会话 `ses_e1f81f5d2ffeEcNqEZUPLt4y8T` 的 `seq=2043/2100/2131/2162`。 [最后一版恢复稿](part2_full_mode/audit/process_recovery_20261119/carbon/08_seq2172_1_submission.py)

## Hydrogen · 环境恢复后先压测勇者，再用勇者反测防图

- **20:25–20:28，开局确有工具阻塞。** 两次公开说明都指向旧工作目录不存在，终端无法启动。用户两次要求继续后，20:32 已报告本地裁判和黄金向量。21:18 另有一次 API 请求中断，记录无法解释整段等待。 [工作目录报错](<LOCAL_USER_HOME>/.gemini/antigravity/brain/8f2819f2-dbcb-4245-9911-819a9edbbff3/.system_generated/logs/transcript.jsonl:396) · [API 错误事件](<LOCAL_USER_HOME>/.gemini/antigravity/brain/8f2819f2-dbcb-4245-9911-819a9edbbff3/.system_generated/logs/transcript.jsonl:484)
- **21:23–22:04，先修勇者，再改金库入口。** 公开进度把本地双基准的进展归因于预留跳跃和调整启发函数，随后继续处理压板箱复用等卡点。22:01 的消息说正在检查自己的勇者在自家图找到的 123 回合路线，下一次工具修改后又专门验证封闭的 `y=8` 金库通道。记录能确认这一轮先发现可走路线、再改动并验证通道。最终合并后，正式验收仍因发卷未列出的嘲讽长度上限拒绝原稿造图。 [路线检查](<LOCAL_USER_HOME>/.gemini/antigravity/brain/8f2819f2-dbcb-4245-9911-819a9edbbff3/.system_generated/logs/transcript.jsonl:799) · [封口后验证](<LOCAL_USER_HOME>/.gemini/antigravity/brain/8f2819f2-dbcb-4245-9911-819a9edbbff3/.system_generated/logs/transcript.jsonl:808)

## DeepSeek · 用旧轨迹校准模拟器，强基准依赖一次算出整条路

- **先补物理再做前向搜索。** DSH 收题消息 `seq=8` 包含用户明确附上的上半场会话 ZIP。操作记录 `seq=104/120/136/160` 显示它把附件解包到临时目录并查阅，随后 `seq=205` 写本地裁判，`seq=229` 开始回放考场发放的上半场轨迹。最终公开汇报说，靠回放定位了弹簧落点、激光相位和起点暴露三个问题。旧会话附件由用户随本场发出，其他席是否也有同类附件尚未核对。 [DSH 会话容器](<<LOCAL_USER_HOME>/.dsh/sessions/--REPO-part2_full-exam_rooms-P2_07_deepseek_dsh--/session-a11cda84-af09-4635-97b0-2a5db66db350/session.v4.jsonl.zstd>) · [本地自测摘要](part2_full_mode/exam_rooms/P2_07_deepseek_dsh/SELFTEST_RESULT.txt)
- **它自己也报告强基准不稳定。** 最终公开回复 `seq=1620` 报告本地十次过六次，并把差异归因于首回合 1.6 秒内部预算能否算完整路线。它留下的一份自测记录就包含一局双钥、240 回合未过。正式引擎兼容复测中，第 85 回合拿齐双钥，后段在 `(24,12)` 和 `(24,13)` 上下往返直至结束。具体是哪个搜索分支让它开始循环，现有记录无法确认。 [正式复测 `P2_RETEST_020`](part2_full_mode/audit/retest_20261119/matches.json)

## GLM · 两次能定位到代码的调试转折

- **20:42–20:46，先怀疑搜索量，后抓到冰面模拟错误。** 当时公开消息称，给搜索 6 万节点仍找不到 6 步推箱。改成单独跑冰面和镜面复现后，它发现 `_atomic` 只移动了计算中的坐标，没有更新占位层中的箱子。修复后，第一块压板的搜索降到 188 个节点。OpenCode 会话 `ses_e1f1d00daffe6T2J1fhNxFBDC5`，`seq=1167/1219/1265`。 [冰面调试脚本](part2_full_mode/exam_rooms/P2_08_glm_opencode/debug_ice.py)
- **21:10，抓到启发式错误。** 选手公开解释，之前为了忽略已上板箱子，把它们也排除在搜索节点的距离评分之外，结果箱子真正上板后，目标状态反被打成 999 的高代价。在节点评分里恢复这些箱子后，它用自己的模拟器报告弱 74、强 120 回合满血通关。正式复测的弱基准仍是 74 回合，强基准却在第 11 回合到 `(3,21)`，从第 12 回合一直 `WAIT` 到第 240 回合。已核对考场导出的强基准格子与裁判格子完全相同。正式停滞的内部触发原因尚未定位。OpenCode `seq=1847/1868`。 [本地步进使用选手自己的 `step_world`](part2_full_mode/exam_rooms/P2_08_glm_opencode/test_extra.py:37) · [正式复测 `P2_RETEST_025`](part2_full_mode/audit/retest_20261119/matches.json)

## 混元 HY4 · 从单次 A* 切成阶段搜索

- **20:29–20:31，连着换了两次搜索组织方式。** CodeBuddy 保存史先出现 `_astar`，两分钟后改为 `_stage_search`，规划按压板、钥匙等阶段测试目标。20:51 后又调整了路径回溯和计划恢复，21:04 增加放炸弹后寻找安全落点的 `_bomb_escape`，最后一版修改了造图。可定位这些改动，尚未找到每次转向对应的公开解释。 [首次阶段搜索稿](part2_full_mode/audit/process_recovery_20261119/hy4/05_SZfR_submission.py) · [加入炸弹避险的版本](part2_full_mode/audit/process_recovery_20261119/hy4/22_5P3x_submission.py:1056)
- **复测给了明确的成效边界。** 混元在官方引擎上过了弱 69、强 108 回合，七席交叉中攻下两张图。两张基准能过，仍有四张交叉对手图耗尽回合。 [正式复测 `P2_RETEST_029/030`](part2_full_mode/audit/retest_20261119/matches.json)

## 豆包 · 多次重写求解器，实际没离开第 7 回合的卡点

- **21:12、21:30 两次完整写稿的重心都在勇者。** 源码对比显示，第二稿加入距离场、状态签名相关修改和安全兜底。随后终端继续重写搜索会话与动作入口。22:32 最后一次把内部预算从首回合 `1.8s`、后续 `0.40s` 收紧到 `1.7s / 0.35s`。这些动作能确认它一直在改搜索和控制耗时，缺少公开文本解释每个选择。 [第一份写入稿](part2_full_mode/audit/process_recovery_20261119/doubao/01_line1385_submission.py) · [第二份写入稿](part2_full_mode/audit/process_recovery_20261119/doubao/02_line3890_submission.py)
- **强基准的失败是局内持续无位移。** 复测中第 7 回合到 `(10,13)` 后没有再移动，后段反复发 `MOVE_R`。最终自测用普通 Python 装载，之前的静态命令也只扫导入。魔王图外圈 `W` 是另一起明确的规则问题。 [实际自测脚本](part2_full_mode/audit/process_recovery_20261119/doubao/03_line8587__final_check.py) · [正式复测 `P2_RETEST_035`](part2_full_mode/audit/retest_20261119/matches.json)

同一强基准提供了三种可直接剪辑的失败方式。GLM 在未得钥匙时开始连续 `WAIT`，DeepSeek 双钥到手后在金库前往返，豆包频繁尝试右移却一直在同一格。逐回合数据见复测回放。 [回放数据](part2_full_mode/audit/retest_20261119/replays.jsonl.gz)
