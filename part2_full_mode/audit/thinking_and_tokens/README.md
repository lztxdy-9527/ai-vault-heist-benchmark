# 下半场思考与Token补采

## 已完成
7位磁盘来源（Astra、SOL、Neon、Carbon、GLM、DeepSeek、Qwen）按JST时间顺序导出平台实际保存的明文思考、回复、用户指令与工具决策/自测证据，并附来源行号或seq。SOL覆盖05:06加时最终回复。Astra审批配套独立保存且不叠加。DSH使用read_across_frames=True解压全部拼接帧。OpenCode通过mode=ro和query_only读取，未依赖空session_part表。

## Token 补采结果

- Astra、SOL、Neon、Carbon、GLM、DeepSeek、HY4 的会话总量均有原始依据。DSH 的推理分项以官方 V4.1 Flash 分词器重算保存的推理文本。它是估算，已含在实测输出中。
- Qwen 采用用户提供的千问平台 Token Plan 截图。四项可见数字是 11 月 20 日按模型汇总的日用量，作为会话用量代理。缓存写入未单列，维持 null。推理按 Qoder 会话中保存的 Thinking 使用公开千问分词器估算。
- 豆包取回三轮各自最后一次调用的原始计量，并用 159 个有生成时间戳的记录作为请求数代理估算整场用量。三笔实测与整场估算分别记录。完整的已保存 Thinking 见 `doubao_trae_logged_thinking.md`，含首轮。
- HY4 的原生导出和 Token 截图均保留。Astra 和 SOL 的推理原文覆盖平台保存的明文摘要。
- `known_totals_only` 仍只累加七位选手的已核实会话总量。推理属于输出的子项。

## 完整性
exam_rooms_integrity.json对纳入范围考场所有文件逐一SHA-256比对，确认提取前后未改。AGY Hydrogen和Opus均排除；Neon虽目录后缀_agy，按OpenCode纳入。

## 复现
现有归档上运行 `python -X utf8 supplement_token_gaps.py` 可复算本次补采。分词器和校验哈希见 `token_gap_evidence.json`。若从零重建，先执行 `extract_readonly.py` 和 `finalize_supplement.py`，再应用桌面导出补采与本次脚本。脚本只向审计目录写入。
