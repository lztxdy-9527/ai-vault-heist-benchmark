# 《阴间地牢》下半场 · 过程稿恢复与加载复盘

覆盖 11 月 19 日已做完的 SOL、Carbon、Hydrogen、DeepSeek、GLM、混元 HY4、豆包。时刻均为 JST。按第一条本场请求回推 40 分钟。七席均缺正式开表和封卷记录，因此下面能确认的是原生记录所见的写稿时间、版本内容及现行加载器结果。

选手对用户可见的解释、主要策略转折和正式回放差异见 [七席作答决策复盘](part2_full_mode/audit/process_recovery_20261119/decision_trace.md)。

## 能还原到什么程度

- **SOL** · Codex 日志恢复了约 20:27 的勇者搜索代码追加片段、约 20:30 的第一版造图脚本。现存回归脚本和 20:34 的 `results_first.txt` 记录初版在强基准耗尽跳跃，后续修改保留跳跃资源，20:36 写入当前稿，20:39 回复。可以复盘这一轮修正，追加片段本身不足以还原当时的完整 `submission.py`。 [途中测试结果](part2_full_mode/audit/process_recovery_20261119/sol_process/results_first.txt:33)
- **Carbon** · 从 OpenCode 成功执行的写入和编辑恢复 8 版，22:00:35–22:13:32，最后一版与当前稿 SHA-256 一致。可复盘落盘后追加的压板配对、诱饵箱过滤与推箱宏动作。已找到的 8 次保存都在推算窗口之后。 [第一份恢复稿](part2_full_mode/audit/process_recovery_20261119/carbon/01_seq2013_1_submission.py)
- **Hydrogen** · 原件保留了勇者、造图、合并脚本及回归脚本。AGY 日志能定位本地裁判、压力验证、分开编写攻守和 22:04 合并，部分写入内容在日志中截断，无法逐版重建整份答卷。 [合并脚本](part2_full_mode/audit/process_recovery_20261119/hydrogen_process/assemble_submission.py)
- **DeepSeek** · DSH 压缩日志恢复了两份完整写入与随后四版可连续应用的编辑，其中五份在推算窗口内。后续有编辑与上一份已知内容对不上，完整版本从考场 `history` 找回 21:36 和 21:50 两份，后者与当前稿 SHA-256 一致。 [首次完整写入](part2_full_mode/audit/process_recovery_20261119/deepseek_tools/01_seq311_submission.py:74) · [考场历史](part2_full_mode/exam_rooms/P2_07_deepseek_dsh/history/timeline.jsonl)
- **GLM** · OpenCode 记录可重放 42 版，前 40 分钟内 30 版，最后一版与当前稿 SHA-256 一致。20:24 首次完整写入，之后留下推箱卡位、冰面及 A* 调试。 [推算窗口内最后一版](part2_full_mode/audit/process_recovery_20261119/glm/30_seq1339_0_submission.py:182) · [推箱调试](part2_full_mode/exam_rooms/P2_08_glm_opencode/debug_stall3.py)
- **混元 HY4** · CodeBuddy 本地历史保存 26 份原件，前 40 分钟内 13 份。最后一份历史原件与当前稿 SHA-256 一致。 [推算窗口内最后一版](part2_full_mode/audit/process_recovery_20261119/hy4/13_xYy9_submission.py)
- **豆包** · Trae 日志保存了 21:12:51 和 21:30:18 两次写 `submission.py` 的完整内容，另找回末段 `_final_check.py`。源码从 PowerShell 参数提取，含完整代码，原始磁盘字节无法逐一核对。 [35:22 写入稿](part2_full_mode/audit/process_recovery_20261119/doubao/01_line1385_submission.py:113) · [最终自测脚本](part2_full_mode/audit/process_recovery_20261119/doubao/03_line8587__final_check.py:3)

[恢复文件清单和 SHA-256](part2_full_mode/audit/process_recovery_20261119/manifest.json) · [用时与原始日志索引](part2_full_mode/docs/evidence_index_part2_20261119.md) · [Token 台账](part2_full_mode/docs/token_ledger_part2_20261119.md)

## 加载失败定位

把七份当前稿及四席在推算窗口内找到的最早、最晚稿件送入现行官方 worker。四席当前稿均返回 `ValueError`，这四席被抽查的早期稿也都被拒。下列时间为距本场请求的经过时间，保留至秒。

- **DeepSeek** · `07:27` 首稿已声明 `__slots__`。`08:24` 的第二次完整写入已有 `_Sim.__new__(_Sim)`，用于复制模拟状态。已能连续恢复的最晚窗口内稿件 `14:16`，也加载失败。其自测直接 `import submission`。 [当前稿](part2_full_mode/exam_rooms/P2_07_deepseek_dsh/submission.py:77) · [本地自测入口](part2_full_mode/exam_rooms/P2_07_deepseek_dsh/selftest.py:14)
- **GLM** · `13:11` 首稿和 `38:15` 窗口内最后一次可定位保存都含 `__slots__`。这是类字段布局声明，现行扫描按双下划线名称拒绝。其本地测试直接 `import submission`。 [当前稿](part2_full_mode/exam_rooms/P2_08_glm_opencode/submission.py:182) · [本地自测入口](part2_full_mode/exam_rooms/P2_08_glm_opencode/test_full.py:7)
- **混元 HY4** · `15:57` 第一份 IDE 保存和 `39:44` 窗口内最后一次保存都被拒。当前稿在 `_Sim.clone()` 中调用 `_Sim.__new__(_Sim)`。其本地测试直接 `import submission`。 [当前稿](part2_full_mode/exam_rooms/P2_09_hunyuan_codebuddy/submission.py:247) · [本地自测入口](part2_full_mode/exam_rooms/P2_09_hunyuan_codebuddy/v22_local_test.py:14)
- **豆包** · `35:22` 写入稿已有两处 `__new__`，用于从观察状态构造对象、复制模拟状态。22:24 的静态检查只列出 `Import` 和 `ImportFrom` 节点，22:25 的最终验证又用普通 Python 导入。两次检查都未覆盖官方拒绝的属性节点。 [当前稿](part2_full_mode/exam_rooms/P2_11_doubao_vscode/submission.py:144) · [AST 检查原始命令](<LOCAL_USER_HOME>/.marscode/logs/2026-11-19/clients/203414-393-39404-vscode-2026-11-19-39404.log:8546)
- **Hydrogen** · 官方 worker 成功加载，魔王随后被正式入口的返回值校验拒绝。`taunt` 有 61 字符，入口上限 40；考场规则书、提示词和模板均未写这项上限。上半场继承稿已有 `taunt` 字段，本次重写保留了该字段。单验格子与作者路线通过，当前稿勇者也通过了两张基准。 [造图返回值](part2_full_mode/exam_rooms/P2_05_hydrogen_agy/build_demon_v22.py:241) · [正式入口校验](part2_full_mode/run_tournament_full.py:327)

官方 worker 在导入前扫描整个文件。`Class.__new__` 属于 `ast.Attribute`，`__slots__ = ...` 左侧属于 `ast.Name`，现行规则对两类节点都拒绝 `__` 前缀。发卷规则禁止动态反射并列举 `__class__`、`__globals__` 等，未明写这个全前缀限制。扫描抛出的错误跨进程后只保留异常类型，正式入口看不到触发词和行号。这三点解释了普通导入和本地回归为何能过，正式加载为何能失败。源码能确认这些写法的实际用途，日志无法证实选手有意违背规则。 [发卷规则](part2_full_mode/exam_rooms/P2_08_glm_opencode/RULES_FULL_v22.md:27) · [静态扫描](part2_full_mode/submission_worker_full.py:124) · [异常回传](part2_full_mode/submission_worker_full.py:181) · [加载复验与哈希](part2_full_mode/audit/process_recovery_20261119/load_checks.json)

漏开监考造成卡点留证缺失。发卷规则、考场自测与正式验收之间的差异造成加载问题，四席的早稿复验已能确认这一点。归档只增补证据，赛场原件和赛果保持原状。
