
# S1d · Opus 1029 行重跑

只替换原三波赛配置的 opus_quota 版本。第一波两套阵容仍从 opus_40m 取历史数据。第二、三波按原对局位置复跑 Opus 攻或守的场次。相同勇者代码 SHA-256 和网格 SHA-256 的重复场次共享一份回放。工作进程、规则、原种子与地图使用原引擎。每次只跑一个 worker。

- versions_manifest.json 锁定参赛文件路径、哈希和准入配置。
- run_config.json 记录四组阵容、种子、时间阈值和引擎指纹。original_inputs_sha256.json 记录原始档案指纹。
- admission_and_benchmarks.json 包含正式准入与双基准实测。
- 各波的 matches.json 保留原赛程 ID 和顺序。leaderboard.json 重新汇总攻方、守方和攻守之和。
- changed_unique_replays.jsonl.gz 保留执行局的完整逐帧回放。changed_replay_index.json 将 52 个受影响赛程 ID 指向对应回放。未受影响的逐帧回放继续使用原目录的压缩缓存，原行与本包 matches.json 逐字段相等。
- opus_attack_worker_timings.json 记录 Opus 攻方调用限时实测。delta_by_seat.json 提供逐席版本差分。submission_function_diff.json 提供代码函数定位。
- reproduce/admission.py 与 reproduce/rerun_affected.py 为此次调用脚本。复制两者到可写空目录，依次运行 python -B admission.py 和 python -B rerun_affected.py。脚本读取原归档与候选原件，在当前脚本旁生成新输出。使用壁钟截止的搜索可能随主机负载产生结果差异。

面向制作的对照表和不确定性说明见 [S1d 对照](<part2_full_mode/audit/evidence_v2/stats/opus1029_vs_891.md>)。

