# S1e-2 搜索插桩与 GLM 反事实

以下搜索轨迹和改法结果均为**赛后实验 / 插桩，非正式赛**。

## GLM 的终局回放

第三波强基准原始回放为 featured_matches[176]。它与 P2_RETEST_025 的源码哈希、逐拍动作、坐标和血量一致。T11 勇者到 (3,21)，T12–T240 共 229 拍 WAIT。冷开场可直接取第三波原始回放。[第三波原始回放](<part2_full_mode/audit/three_waves_20261120/wave3_final_11seats/replays/tournament_results_full.json>) · [四份哈希核验](<part2_full_mode/audit/evidence_v2/code/_sandbox/s1e2/glm_archive_check.json>)。

## 搜索动画

- **Neon**　T1 展开 24012 节点（macro 34、local 23978），记录 72966 次舍弃，导出 120 帧。插桩推荐动作与 119 拍归档回放一致。[逐回合 CSV](<part2_full_mode/audit/evidence_v2/code/neon/search_trace/per_turn.csv>) · [动画 JSONL](<part2_full_mode/audit/evidence_v2/code/neon/search_trace/turn1_frontier.jsonl>) · [挂点与归档定位](<part2_full_mode/audit/evidence_v2/code/neon/search_trace/metadata.json>)。
- **Carbon**　T1 展开 5922 节点（macro 10、local 5912），记录 16278 次舍弃，导出 119 帧。插桩推荐动作与 131 拍归档回放一致。[逐回合 CSV](<part2_full_mode/audit/evidence_v2/code/carbon/search_trace/per_turn.csv>) · [动画 JSONL](<part2_full_mode/audit/evidence_v2/code/carbon/search_trace/turn1_frontier.jsonl>) · [挂点与归档定位](<part2_full_mode/audit/evidence_v2/code/carbon/search_trace/metadata.json>)。
- **Opus 1029 行**　T1 展开 1189 节点（weighted 1189），记录 10214 次舍弃，导出 119 帧。插桩推荐动作与 117 拍归档回放一致。[逐回合 CSV](<part2_full_mode/audit/evidence_v2/code/opus/search_trace/per_turn.csv>) · [动画 JSONL](<part2_full_mode/audit/evidence_v2/code/opus/search_trace/turn1_frontier.jsonl>) · [挂点与归档定位](<part2_full_mode/audit/evidence_v2/code/opus/search_trace/metadata.json>)。
- **Astra**　T1 展开 2226 节点（crate_walk 2216、crates 10），记录 5538 次舍弃，导出 118 帧。插桩推荐动作与 111 拍归档回放一致。[逐回合 CSV](<part2_full_mode/audit/evidence_v2/code/astra/search_trace/per_turn.csv>) · [动画 JSONL](<part2_full_mode/audit/evidence_v2/code/astra/search_trace/turn1_frontier.jsonl>) · [挂点与归档定位](<part2_full_mode/audit/evidence_v2/code/astra/search_trace/metadata.json>)。
- **GLM**　T12 展开 512 节点（astar 512），记录 1373 次舍弃，导出 103 帧。插桩推荐动作与 12 拍归档回放一致。[逐回合 CSV](<part2_full_mode/audit/evidence_v2/code/glm/search_trace/per_turn.csv>) · [动画 JSONL](<part2_full_mode/audit/evidence_v2/code/glm/search_trace/t12_frontier.jsonl>) · [挂点与归档定位](<part2_full_mode/audit/evidence_v2/code/glm/search_trace/metadata.json>)。

GLM 的 512 次 T12 展开全部发生在首个目标 (8,22)。本次插桩最后展开的勇者格为 (4, 23)，随后出现 deadline；其余三个子目标在同一截止后直接停止。最终动作 WAIT。S1e 的 448 与这次的 512 分属两次不同负载的插桩，镜头计数应与所用轨迹配套。[逐回合 CSV](<part2_full_mode/audit/evidence_v2/code/glm/search_trace/per_turn.csv>) · [动画 JSONL](<part2_full_mode/audit/evidence_v2/code/glm/search_trace/t12_frontier.jsonl>) · [挂点与归档定位](<part2_full_mode/audit/evidence_v2/code/glm/search_trace/metadata.json>)。

动画按展开节点数分帧。每条 events 记录含全序 seq、阶段 stage、坐标 cell 和原因 reason。expand 点亮，discard 可置灰；同一格可因资源、相位或棋盘不同多次出现。GLM 的 trial 标子目标，stop 标预算截止。计数只覆盖各席埋点队列，含各自列出的局部搜索，预处理未纳入，勿用节点数排序能力。

CSV 的 found_full_path 表示该回合新找到整图通关路线，缓存续走为 False；found_subgoal 仅用于 GLM 的子目标搜索记录。search_seconds 在被埋点的搜索调用外层计时，嵌套调用只记一次；decision_seconds 计副本决策函数，worker_roundtrip_seconds 含往返。时间为插桩实测。

## GLM 反事实

- **A　仅加倍内部预算**　原提交源码完全同字节。副本 worker 将程序内部单调钟走速减半，使 1.30 / 0.25 秒对应实际 2.60 / 0.50 秒。三次均 T9 接口弃权，结算 HP 0，钥匙 0。
- **B　仅保留无伤首步推箱**　部分路径第一步若确为推箱且存活无损血，则保留这一拍，后续过滤及兜底沿用原逻辑。三次均在 T12 执行 MOVE_R 推箱，T120 通关，HP 100、两把钥匙，全程 WAIT 0 次。
- **C　A 与 B 同时启用**　三次均 T9 接口弃权，结算 HP 0，钥匙 0。

裁判调用上限保持 T1 为 2.0 秒、后续为 0.5 秒。A、C 各自的单步核验在 T7 重现调用超时。整局回放在 T7–T9 记录 WAIT，并在 T9 记为接口错误三连弃权。HP 0 为弃权结算值。该实验没有测放宽裁判时限后的通关情况。[T7 错误类型](<part2_full_mode/audit/evidence_v2/code/_sandbox/s1e2/glm_case_deadline_probe.json>) · [九次结果和独立回放路径](<part2_full_mode/audit/evidence_v2/code/_sandbox/s1e2/glm_counterfactual_runs.jsonl>)。

事实编号 E-7421 至 E-7436，共 16 条。[v2 台账](<part2_full_mode/audit/evidence_v2/evidence_ledger_v2.jsonl>)。
