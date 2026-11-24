# AI Vault Heist Benchmark（《AI 算法对抗赛：金库攻防战》官方开源验证仓）

本仓库完整开源《AI 算法对抗赛：金库攻防战》**上半场（迷雾模式 / Fog Mode）**与**下半场（全图明牌攻守重构赛 / Full Mode v2.2）**的全部确定性评测引擎、官方地图、沙盒机制、考题 Prompt、选手全部版本源码（含 **Opus 1029 行续跑版**）、考场迭代过程日志、脱敏后的思考与 Token 账本、三波全量对局回放及噪声/反事实审计脚本，供社区独立复现与核验跑分真实性。

---

## 仓库目录结构

```text
.
├── part1_fog_mode/                 # 上半场 · 迷雾模式（Fog-of-War）
│   ├── engine.py                   # 确定性游戏引擎（纯 Python 标准库）
│   ├── official_maps.py            # 官方试金石地图
│   ├── submission_sandbox.py       # 进程隔离与超时沙盒
│   ├── submission_worker.py        # 选手代码执行 Worker
│   ├── run_tournament.py           # 上半场全交叉评测与回放导出器
│   ├── test_engine.py              # 8 个 Golden Vectors 与引擎回归测试
│   ├── arena_stage.html            # 浏览器可视化回放舞台（开箱即播）
│   ├── starter_kit/                # 原始规则书、Golden Vectors 与答题模板
│   ├── submissions/                # 11 席正式参赛源码
│   ├── submissions_easter_eggs/    # 彩蛋源码（opus_fixed, astra_6.2_medium）
│   ├── exam_rooms/                 # 11 席考场原始迭代历史与日志（已脱敏）
│   ├── replays/                    # 全量压缩回放 tournament_bundle.json.gz + 精选 demo_bundle.js
│   └── audit/                      # 上半场赛事结果、SHA-256 校验与复仇赛数据
│
├── part2_full_mode/                # 下半场 · 全图明牌模式（Full Mode v2.2）
│   ├── engine_full.py              # v2.2 引擎（压板门 PLATE/P_GATE、双频激光、单向门）
│   ├── official_maps_full.py       # 下半场官方试金石与替补图
│   ├── submission_sandbox_full.py  # 首回合 2.0s / 常规回合 0.5s 沙盒与三振 DQ 机制
│   ├── submission_worker_full.py   # 下半场 Worker
│   ├── run_tournament_full.py      # 下半场 110 场全交叉调度器
│   ├── test_engine_full.py         # 下半场双审回归测试套件
│   ├── arena_stage_full.html       # 下半场浏览器可视化回放舞台（开箱即播）
│   ├── starter_kit_v22/            # RULES_FULL_v22.md、考题 Prompt、Golden Vectors
│   ├── benchmarks/                 # 官方弱基准 / 强基准参考实现
│   ├── tools/                      # 考场部署、实时监控与 Token 采集脚本
│   ├── submissions/                # 三波全部 21 份时间节点源码 + opus_resumed_1029
│   ├── exam_rooms/                 # 11 席考场源码与历史截断快照（已脱敏）
│   ├── opus_resumed_sandbox/       # Opus 1029 行续跑沙盒、转录与重跑对照证据
│   ├── replays/                    # 精选 demo_bundle_full.js + 一键全量解压脚本
│   ├── audit/
│   │   ├── three_waves/            # 三波评测脚本、汇总及全量去重对局 all_unique_matches.jsonl.gz
│   │   ├── opus1029_re_eval/       # Opus 1029 行重跑对照与差异回放
│   │   ├── noise_and_hybrid/       # CPU 计时噪声测量与混合榜单审计（S1d2）
│   │   ├── counterfactual_and_code_analysis/ # 代码插桩与 GLM 反事实实验
│   │   ├── process_recovery/       # 考场迭代历史恢复清单
│   │   ├── thinking_and_tokens/    # 11 席思考日志与 Token 索引（路径已脱敏）
│   │   └── retest_20261119/        # 早期复测归档
│   └── docs/                       # 赛制设计文档、Token 账本与证据索引
│
├── assets/                         # 轻量自制角色头像与像素小人（供两个 HTML 舞台使用）
├── LICENSE                         # 代码开源协议：MIT
└── LICENSE-DATA                    # 数据与文档协议：CC-BY-4.0
```

---

## 快速复现指南（Python 3.11+ 纯标准库）

### 1. 验证确定性引擎（零外部依赖）
```bash
# 上半场（迷雾模式）引擎与 Golden Vectors 回归测试
cd part1_fog_mode
python test_engine.py

# 下半场（全图明牌 v2.2）双审回归测试
cd ../part2_full_mode
python test_engine_full.py
```

### 2. 复现官方跑分
```bash
# 上半场全交叉评测
cd part1_fog_mode
python run_tournament.py

# 下半场三波时间切片评测（Wave 1 / Wave 2 / Wave 3）
cd ../part2_full_mode/audit/three_waves
python run_three_waves.py
```

### 3. 浏览器打开可视化回放舞台
直接用现代浏览器打开以下任一 HTML 文件即可回放精选名局（零构建、无需后端）：
- 上半场舞台：`part1_fog_mode/arena_stage.html`
- 下半场舞台：`part2_full_mode/arena_stage_full.html`

如需在舞台中加载**全部完整对局**，先运行对应解压脚本：
```bash
python part1_fog_mode/replays/unpack_full_bundle.py
python part2_full_mode/replays/unpack_wave3_bundle.py
```

---

## 口径与隐私说明

1. **三波时间切片（Three Waves）与 Opus 1029 行续跑口径**：
   - 下半场按考场实时截断时间划分 Wave 1（早交卷 / 40m 截断）、Wave 2（60m 增援）、Wave 3（11 席终稿），所有版本快照均保留在 `part2_full_mode/submissions/` 与 `part2_full_mode/exam_rooms/`。
   - Opus 在原考场因平台额度中断于 891 行稿；续跑后的 **1029 行完整稿** 单独归档在 `part2_full_mode/opus_resumed_sandbox/` 与 `part2_full_mode/audit/opus1029_re_eval/`，并与 891 行稿及混合榜单做严格区分对比（详见 `part2_full_mode/audit/noise_and_hybrid/opus1029_vs_891.md`）。
2. **隐私脱敏**：
   - 所有考场日志、思考记录与索引中的本机用户目录均已统一脱敏为 `<LOCAL_USER_HOME>`，工作区绝对路径已转为仓库相对路径；
   - 计费后台 UI 截图未收录进公开仓库，仅保留核验后的文字/JSON Token 账本；
   - 第三方参考视频与视频剪辑工程资产未包含在本仓库中。

---

## 开源协议

- **代码**（引擎、评测框架、工具脚本、选手源码）：[MIT License](LICENSE)
- **数据与文档**（规则书、Prompt、对局回放、审计日志与账本）：[CC BY 4.0](LICENSE-DATA)
