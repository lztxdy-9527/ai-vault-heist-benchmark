# 《阴间地牢》下半场 · 七席兼容复测

使用 2026-11-19 取证时的七席当前稿，按完整 SHA-256 锁定。时间来源是已完成会话的当前稿，七席都缺正式 40:00 封卷。本轮保留同一套官方 worker、FULL 物理、出生准入、作者自证和 `2.0s / 0.5s` 单步时限。

## 复测准入

- **SOL、Carbon**直接使用原始字节。
- **DeepSeek、GLM**的普通字段由 Python 默认对象布局存储，去掉 `__slots__` 声明及冗余显式 `object` 基类。**DeepSeek、混元 HY4、豆包**的本类对象构造改走普通构造器，原有状态复制和初始化逻辑继续填充字段。对象布局和初始化路径变化可能影响单步耗时。
- **Hydrogen**只缩短展示用 `taunt`，维持正式入口的 40 字符校验。造图、自证与勇者算法保持原提交内容。
- **豆包**通过模块加载。`build_dungeon` 在主图和回退图的最外圈写入 `W`，发卷明确要求 `T_W`。勇者正常上场，该魔王席使用 `BACKUP_FULL_01`，魔王分置 0。

可从 [准入与 SHA-256](part2_full_mode/audit/retest_20261119/admissions.json) 找到每个复测副本。对照 [DeepSeek](part2_full_mode/audit/retest_20261119/submissions/deepseek/review.diff)、[GLM](part2_full_mode/audit/retest_20261119/submissions/glm/review.diff)、[混元 HY4](part2_full_mode/audit/retest_20261119/submissions/hunyuan/review.diff)、[豆包](part2_full_mode/audit/retest_20261119/submissions/doubao/review.diff) 和 [Hydrogen](part2_full_mode/audit/retest_20261119/submissions/hydrogen/review.diff) 的差异可复核本次的兼容处理。 [豆包外圈代码](part2_full_mode/exam_rooms/P2_11_doubao_vscode/submission.py:1003) · [发卷规则](part2_full_mode/exam_rooms/P2_11_doubao_vscode/RULES_FULL_v22.md:43)

## 对局与复盘

赛程含七席各打三张官方图、攻打两张基准图、由两名基准勇者各打七席防图，以及七席双向交叉，共 91 局。逐局记录保留 `match_id`、双方、实际地图 ID、供评测的源码哈希、局内回合、状态、分数、进程重启次数和回放帧。备用图结果按该席魔王 0 分记账。

前 30 局顺序执行，后续最多六局独立 worker 并行。并行结果遇到 worker 重启或 DQ 时，以独占重跑的结果入档。局内 `TIMEOUT` 表示用完 240 回合。单步超时触发的重启另记在 `worker_respawns`。

七席均攻下弱基准。SOL、Carbon、Hydrogen、混元 HY4 也攻下了强基准，分别用 126、131、115、108 回合。SOL、Carbon、Hydrogen 各通关三张官方图，混元通关两张，DeepSeek 和 GLM 各通关一张。豆包打完三张官方图，其中两局耗尽回合，一局阵亡。

42 局交叉赛有 18 局通关、23 局耗尽回合、1 局阵亡。SOL、Carbon、Hydrogen 的防图分别接战 6 名选手和 2 名基准勇者，均守住 8 局。91 份最终对局无 DQ，无 worker 重启。已逐局核对压缩回放与成绩记录，并重算七席原稿及复测副本的哈希。

[复测脚本](part2_full_mode/audit/retest_20261119/run_retest.py) · [逐局成绩](part2_full_mode/audit/retest_20261119/matches.json) · [回放帧 JSONL（gzip）](part2_full_mode/audit/retest_20261119/replays.jsonl.gz)
