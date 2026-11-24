# 混元 HY4 下半场Thinking 原文摘录

来源为 CodeBuddy 历史会话导出 `hunyuan_codebuddy_export.zip` 内的 `勇者迷宫AI调试与修正.json`。请求 `fe4d83df1f9d4926bd7df4bf1ff54128` 于 2026-11-19T20:08:05.749000+09:00 开始。按导出消息与内容块原序排列，逐条时间以导出字段为准，缺时使用序号定位。


## 002.1 · Thinking

```
用户要求阅读 part2_full_mode/exam_rooms\P2_09_hunyuan_codebuddy 下的所有文件，并按要求完成任务，写成的一切文件均放在该文件夹。还提示"打过强基准也不代表强，它只是一个正常基准"。

首先我需要列出该文件夹下的所有文件并阅读。让我开始。
```

## 004.1 · Thinking

```
让我读取所有文件。先看主提示文件和规则文件。文件可能很大，让我分别读取。也看看 history 目录。
```

## 008.1 · Thinking

```
用户要求：阅读所有文件，按要求完成任务，写成的一切文件均放在该文件夹。还提示"打过强基准也不代表强，它只是一个正常基准"。

首先按考场纪律第2步：读完规则与本人战报后，在对话区先发一段 50~100 字的下半场放话。我需要先读规则与战报，然后发放话。

让我继续读其他文件。规则书可能很长，先读。
```

## 010.1 · Thinking

```
继续读规则后半部分（Schema 等）。文件到第115行结束？read_file 显示到115行。让我确认是否还有更多。看起来文件到115行。让我读 PART1_BATTLE_REPORT.md 和模板、golden vectors、benchmarks、submission.py、timeline。

先读战报（可能很长）。让我并行读几个。
```

## 016.1 · Thinking

```
接下来读 PART1_BATTLE_REPORT.md，可能很长。先看看大小。用 read_file 分段。也读 submission.py（上半场继承的答卷），benchmarks。

让我并行读多个文件。由于可能很长，先读战报的前面部分。
```

## 018.1 · Thinking

```
战报很长，已读完。接下来读 benchmarks JSON（可能很大）、当前 submission.py（上半场继承）、timeline.jsonl、baseline 文件。

先读 v22_sparring_benchmarks.json 和 part1_dungeons_benchmark.json 的结构。用 python 脚本查看结构（避免超长输出）。但注意"写成的一切文件均放在该文件夹"——我可以用临时脚本，但最好放在该文件夹里或者用命令行直接执行 python -c，不写文件。用 execute_command 执行 python -c 读取 JSON 结构，不创建文件。

不过用户说"写成的一切文件均放在该文件夹"，所以如果我写测试脚本，必须放在该文件夹。我会把测试脚本写成该文件夹下的一个文件（比如 local_test.py），但要注意不要污染提交——提交只看 submission.py，其他文件应该无所谓。不过为了保险，也可以只用 python -c 内联。

先了解 JSON 结构。
```

## 022.1 · Thinking

```
grid 是 list of lists of strings（26x40）。好。

现在读 part1_dungeons_benchmark.json 结构，还有 my_hero_matches 里的轨迹（可能有用）。以及当前 submission.py（上半场答卷，888 行）需要读，因为要继承并重构。还有 history/timeline.jsonl 和 v00_baseline_363ac007.py。

让我先看 timeline 和 baseline 文件的大小。
```

## 024.1 · Thinking

```
还有 .baseline_sha256 隐藏文件。让我读 timeline.jsonl 和 .baseline_sha256，以及当前 submission.py 全文（29956 字节，888 行）。这个 submission.py 是上半场的答卷，我需要理解它，然后重构。

先读 timeline 和 hidden 文件。
```

## 028.1 · Thinking

```
现在读当前 submission.py（上半场答卷）全文。888 行，一次读完可能大但可行。让我分段读，因为需要理解其引擎（用于本地前向模拟器）。实际上上半场我的 submission.py 只有造图和决策，不含完整引擎（引擎在 d:/ai_work/hunyuan_lab/engine.py）。让我看看。

关键：我这次任务需要写一个 v2.2 的完整引擎用于本地测试（模拟 FULL 模式、新机关），以及新的 submission.py 里的 build_dungeon() 和 decide_action()。用户说"写成的一切文件均放在该文件夹"，所以测试脚本也应该放在该文件夹（比如 local_engine.py、local_test.py）。但是评测只看 submission.py，多几个文件应该没关系。不过为了避免混淆，可以把测试脚本也放这里，明确命名。

先读 submission.py。
```

## 030.1 · Thinking

```
这是上半场答卷，我不需要全部读完（我已知其内容，且要彻底重构）。但了解其引擎/模拟部分会有用。不过 v2.2 引擎差异大，我可能重写一个独立的本地模拟引擎用于测试。

关键任务：
1. 发 50~100 字宣告（在对话区）。
2. 重构 submission.py：
   - build_dungeon(): v2.2 新机关逻辑迷宫，author_solution ≤ 200 步，出生 4 回合准入合规，预算 ≤3000G。
   - decide_action(): FULL 全图明牌全局搜索求解器，Turn 1 用 1.6s 预算，Turn>1 快速恢复/降级。
3. 本地回归自测：覆盖 golden vectors、BENCH_WEAK、BENCH_STRONG 以及上半场 14 张图（FULL 模式），并检验新地图的合规与自证。

用户提示"打过强基准也不代表强，它只是一个正常基准"——意思是不要只针对基准过拟合，要写通用求解器，真正做强。这点很重要。所以要写通用的全图明牌搜索求解器（考虑新机关：PLATE/P_GATE/BOX/LASER2/ONEWAY），而不是硬编码两张基准图的答案。

时间：40 分钟倒计时是情境设定，我实际要在合理时间内完成。让我高效推进。

策略设计：

**A. 本地前向引擎（测试用，写在文件夹里 `local_engine_v22.py`）**
需要精确模拟 v2.2 物理，用于：
- 验证 build_dungeon() 的地图合规性（预算、上限、坐标、P_GATE 约束、出生 4 回合准入）
- 回放 author_solution（≤200 步，恰好最后一步通关）
- 对 BENCH_WEAK/BENCH_STRONG 和 14 张 part1 图跑我的 decide_action，评估表现
- 校验 golden vectors

这是关键工作量。规则里给出了详细语义，但有些细节需要推断（与上半场 v2.1 引擎一致的部分）。我手上有上半场本地引擎 `d:/ai_work/hunyuan_lab/engine.py`（在另一个 workspace）。不过用户说"写成的一切文件均放在该文件夹"——读取其他文件夹的文件应该没问题，但写文件必须放在该文件夹。我可以复用上半场引擎的代码作为参考，但需要扩展 v2.2。

关键：decide_action 在评测时只拿到 state（不含引擎），所以它必须自己实现物理预判/搜索。因此我需要在 submission.py 内部实现一个轻量的"动作模拟"函数，用于 Turn 1 的全局搜索（BFS/A* over full state space）。这是核心。

**B. decide_action 全图明牌求解器**

思路：Turn 1 有 2.0s，可以用 1.6s 做一次全局搜索，把「完整动作序列」算出来存进 memory，之后每回合直接取下一个动作（O(1)）。但问题：如果模拟有偏差，实际状态会偏离计划；需要每回合校验（对比 state 的实际英雄位置/HP/钥匙/翻门状态），若偏离则在 Turn>1 用 0.5s 内做快速重规划（或从当前状态重新做有限深度搜索）。

状态空间：网格 40x26 = 1040 格，动作 14 种，还有箱子位置、门开关、压板、炸弹、跳跃次数、投掷次数、钥匙、HP、时间（激光周期 12 拍）。完整状态空间 BFS 太大。但可以用简化：
- 忽略大部分机关的精确动态，用「可通行静态图 + 时间相位」做加权 A*，考虑激光格在特定回合危险。
- 对每张图，目标是：拿 K1、K2（顺序可选）、然后 V。用 A* 在「位置 × 时间相位（12）× 钥匙位（4）× 翻门状态（2）× 压板状态（2）」上搜索，边是 MOVE/JUMP/THROW/BOMB/WAIT。这个状态空间 ~1040*12*4*2*2 ≈ 200k，边 14 → 2.8M，在 1.6s Python 内有点吃紧但可优化（主要用 MOVE + WAIT，偶尔 JUMP/THROW/BOMB）。

实际上更实用：分层规划
1. 用静态几何（考虑墙、门状态、单向门、坑、激光炮座）建图，计算从当前位置 → K1 → K2 → V 的最短路径（Dijkstra/BFS），允许「等待」来避开激光拍。
2. 时间维度：激光只在 turn%3==0（红）、turn%4==0（蓝）伤害。预警射线格是静态的（除非门开关/箱子遮挡变化）。我们可以把「危险格 × 拍相位」纳入 A* 状态：state = (x, y, t mod 12, keys_mask, flipped, plates_active)。转移：MOVE 到相邻格（含 ICE 滑行、弹簧、传送门等静态可预测位移），或 WAIT，或 JUMP（消耗次数）、THROW（改变 flipped）、BOMB（改变地形，复杂）。
3. 对于需要推箱子压板的图（BENCH_STRONG），必须处理 BOX 推动。这是更难的部分。可以在搜索状态里加入箱子位置集合（最多 6 个）——状态爆炸。可以用分阶段：先做「推箱子计划」（用 A* 在箱子状态空间），再做路径。

考虑时间限制（我作为 AI 实际也要高效），我打算实现一个务实的方案：

**核心：Turn 1 做一次带时间相位的 A*/Dijkstra 规划，输出动作序列；Turn>1 每步校验实际 state 与预期，若一致直接取下一动作；若偏离，用剩余预算（0.35s 内）从当前状态重规划（同样算法，但缩短）。**

规划器需要处理：
- 静态高墙（W/T_W/炮座/关闭的门/P_GATE 关闭时）、坑（PIT，除非有 BOX 填）、CRACK（可走一次，之后变 PIT；简化为可走）、ICE 滑行、MIRROR、SPRING、PORTAL、ONEWAY 方向限制、SWITCH 翻转（MOVO 踏上或 THROW 命中）、PLATE/P_GATE（需 BOX 压板）。
- 激光：按 12 拍周期，计算每个危险格在哪几拍是危险的（红 3,6,9,12；蓝 4,8,12；12 拍双射 -100）。搜索时避免在这些拍进入/停留危险格；必要时 WAIT 到安全拍。
- 钥匙顺序：两种顺序都试，取总步数小的。
- HP：尽量 0 伤。

对于 BENCH_STRONG 的压板/推箱：需要更完整的处理。我可以实现一个「子目标推箱」规划：如果需要 P_GATE 打开，找到 PLATE 和 BOX，规划把 BOX 推到 PLATE 上（Sokoban 式 BFS，状态 = 箱子位置 + 英雄位置，在小范围内），然后路径通行。这个实现量不小，但可以尝试。

另外提示"打过强基准也不代表强"——说明要通用，不要硬编码。我会写通用求解器。

**C. build_dungeon 新魔王图**

需要设计一个在 FULL 明牌下依然能困住/杀死多数勇者的逻辑谜题，同时满足：
- budget ≤ 3000G
- author_solution ≤ 200 步（我自己要给出一条 ≤200 步、恰好最后一步通关、满血/存活的解）
- 出生 4 回合准入（至少 2 个不同 Turn-1 零伤落点各自能 0 伤活过 Turn 4）
- 组件上限：PLATE≤4, P_GATE≤8, BOX≤6, LASER2+红≤12, ONEWAY≤12, T_W≤120, CRACK≤40, MIRROR≤30, SPRING≤20, SWITCH≤6, R/B_GATE≤16, TNT≤12, HEAL/MIMIC≤4 each, PORTAL≤2 pairs
- P_GATE 使用时必须 1<=PLATE<=BOX

设计目标：造一个「必须用新机关才能破解」的多步逻辑锁，且不依赖迷雾。勇者分低 = 魔王分高。

思路：真实求解难度来自：
1. **12 拍双频激光节拍**：在必经通道上设置红蓝交叉射线，使勇者必须精确等待某拍才能通过；一步走错 -100 瞬杀。明牌下仍需精确计时，勇者求解器若不做时间相位搜索就会死。
2. **PLATE/P_GATE + BOX 推箱**：必需推箱子到压板才能开门；多数勇者不做 Sokoban 搜索就卡住（TIMEOUT）。
3. **ONEWAY 单向门**：制造不可逆路径，走错就要绕远或困死。
4. **长路径**：≤200 步自证，但让最短路径接近 190 步，勇者容易超时（240 回合其实够，但如果有强制等待激光节拍 + 推箱，可能超）。

但注意：**我们自己也要能通关（author_solution ≤200）**，所以不能造得自己也解不了。而且我们的 decide_action 会被用来打别人的图，自己的图是给对手打。

关键洞察：评分魔王分：实杀 500+..., 困死 320+..., 失守 1.7D+150*(T-1)/239。即使对手通关，只要 T 大（比如 190 步），魔王也能拿 ~120 分。要拿高分最好让对手 DEAD/TIMEOUT。

上半场冠军 ASTRA 造价 575G 就拿了 949 分（10 实杀），靠的是「出生点秒杀」：三个 LASER_D 在 (1,7),(2,7),(3,7) 向下扫，加上 LASER_U 在 (1,19),(2,19),(3,19) 向上扫，勇者第一步 JUMP_U 两下到 (2,11)... 实际上 T3 死。下半场出生 4 回合准入规则禁止开局强杀。

但准入规则只要求「存在至少 2 个不同 Turn-1 零伤落点能 0 伤活过 Turn 4」。我们可以设计：出生区周围有安全格，但通往目标的所有路径都要经过致命激光节拍/推箱逻辑。

设计草图（需要仔细算）：

**核心杀招：12 拍双频激光 + 单向门构成的「节拍锁」，配合 PLATE 推箱开门。**

不过，要考虑对手的求解器水平：提示说 BENCH_STRONG 只是"正常基准"，暗示正赛对手可能有很强的全局搜索求解器（比如 GPT-6.2 Sol 写的）。所以不能只靠一个小 trick；要做真正需要复杂推理的图。

一个稳健的思路：**让最短通关路径本身接近 200 步**（author_solution ≤200），且路径上有多个「必须等待特定拍」的激光交叉点、单向门、以及推箱开门。对手若求解器不强，会超时或死；即使强，T 接近 190-200，魔王失守分也有 ~120-125（不算高但保底）。同时大量陷阱提高 D。

另外，D（trap damage）也是魔王分的一部分：实杀 500+50*(3-P)+D+250g，困死 320+50*(3-P)+D+125g。P = 钥匙数+进度。让对手拿不到钥匙（P 低）分更高。

我认为最有效且合规的做法是：**用 PLATE/P_GATE + BOX 造一个"必须推箱"的门，把 V 和钥匙锁在门后；同时在唯一通道布 12 拍双频激光交叉火力，使通过必须精确计时；再放单向门让走错不可逆。** 并且自己给出 ≤200 步解。

但推箱 + 激光 + 单向门的组合，我自己的本地引擎必须能精确模拟验证。工作量大但可控。

让我先看上半场引擎代码，可以复用大部分物理逻辑（在 d:/ai_work/hunyuan_lab/engine.py），然后扩展 v2.2。但"写成的一切文件均放在该文件夹"——我可以把引擎复制/扩展后写到该文件夹 `local_engine_v22.py`。读旧引擎是允许的。

不过读取 d:/ai_work/hunyuan_lab/engine.py 是另一个 workspace 的文件，用户说"请阅读 part2_full_mode/... 下的所有文件"——只读该文件夹即可，但复用自己上半场写的引擎代码不算违规（也不联网）。不过为了避免麻烦，我可以基于规则重新写一个精简的 v2.2 引擎，放在该文件夹下作为测试工具。

考虑时间效率：我需要写：
1. `local_engine_v22.py`：完整 v2.2 前向模拟（用于验证 + 求解器开发 + 回归）。这也基本就是 decide_action 里需要的"单步模拟"逻辑，可以共享设计。
2. `submission.py`：build_dungeon + decide_action（内含轻量模拟/搜索）。
3. 测试脚本 `local_test.py`：跑 golden vectors、benchmarks、自己地图。

其实可以把引擎写在 submission.py 里（作为内部函数），然后测试脚本 import submission 来用它的模拟器——这样代码复用且提交自包含。但评测机 import submission 时不应有副作用；函数定义没问题。不过 submission.py 应当尽量精简，且不能导入 os/json 等？规则允许 json、time、math、heapq、collections、bisect、itertools、copy、random。禁止文件 I/O、eval/exec/getattr/setattr 等。所有引擎逻辑都是纯计算，OK。

我倾向于：**submission.py 内实现完整 v2.2 前向模拟器** `_Sim`（供 decide_action 的搜索使用），并让测试脚本直接 import 它来验证 build_dungeon 与基准图。这样一份代码两用，减少不一致风险。

但注意：完整模拟器（含箱子、炸弹、爆炸、激光、TNT、传送门、飞石、弹簧、镜面、单向门）代码量约 400-600 行。加上求解器 ~300 行，加上造图 ~150 行，总共 ~1000 行。可行。

不过要小心：Turn 1 的 1.6s 预算内做全局搜索，如果用完整模拟器逐步模拟，每个状态转移都要复制整个地图（1040 格）+ 占用层，太慢。需要优化：
- 预计算静态信息（地形、危险格按拍）。
- 搜索状态只包含 (pos, t%12, keys, flipped, plates, boxes 位置/或忽略)，转移用轻量函数计算落点（不含完整爆炸/推箱）。
- 对需要推箱的门，单独处理。

让我设计更实际的求解器：

**阶段式规划（Turn 1，1.6s 内）**：
1. 解析 state：terrain（全图）、occupant、targets、clues、plates_active、laser_warnings、hero（位置/HP/keys/jumps/throws/bombs）、turn、gates_flipped、bombs（在场）。
2. 构造静态图：
   - `high(x,y,flipped,plates_active)`：W/T_W/炮座/关门/P_GATE 未激活 → 阻挡。
   - `oneway`：进入方向限制。
   - 危险：`pit`（不可走，除非 BOX 填）、`crack`（可走一次）、`mimic/heal`（CHEST，可能是伤害 45；clues 可辨）、`tnt`（阻挡，且 3x3 爆炸风险）。
   - 激光射线格：按周期 3/4 计算每条炮的射线（考虑高墙遮挡、BOX 遮挡），得到 danger[(x,y)] = set of phases (0..11) 中危险。注意 turn 是从 state['turn'] 开始，动作发生在 turn，那么 danger 判定用 turn 的 mod。
3. 目标：依次拿 K1、K2（顺序两种）、到 V。
4. 用 A* / Dijkstra 在状态 `(x, y, phase, keys_mask, flipped)` 上搜索，动作集合：4 MOVE + WAIT + JUMP(4) + THROW(4) + BOMB（可选，简化）。移动落点用简化物理（普通摩擦地面 + ICE/MIRROR/SPRING/PORTAL 的确定性位移 + ONEWAY 限制）。
   - 代价：每步 1，加上危险惩罚（进入激光格在危险拍 = 禁止/极大代价），HP 损失惩罚。
   - 找到 keys==3 且位置==V 的状态，回溯动作序列。
5. 把动作序列存入 memory['plan']，memory['plan_idx']=0，同时记录预期状态签名（pos, hp, keys, flipped, plates, turn）。
6. Turn>1：比对实际 state 与 plan 的预期；若匹配，返回 plan[next]；否则快速重规划（在 0.4s 内，用更浅的搜索或重新跑一次 A*，一般 A* 很快）。

这个方案对 BENCH_WEAK/SRONG 能否通关？BENCH_WEAK 需要：翻红门（SWITCH at (12,10) 或 THROW）、推 BOX 到 PLATE(11,17) 开 P_GATE(35,15)、通过 ONEWAY、避开激光。BENCH_STRONG 需要 3 个 PLATE 全被 BOX 压住、填两格深渊、单向门、避开双频激光。这些都是"Sokoban + 时序"问题，单纯位置 A* 不够。

考虑到"打过强基准也不代表强"，我应该努力做通用求解器，但也要务实：先保证 BENCH_WEAK（0 分水位线，绝不能低于它！），再尽力 BENCH_STRONG。

**关键点：展示分 = 原始均分 - 弱基准均分。低于弱基准记负分。** 所以必须在 BENCH_WEAK 上至少达到弱基准水平（81 步 100HP 通关）。BENCH_WEAK 需要推箱，所以求解器必须支持推箱。

让我设计支持推箱的搜索：
状态包含：`(hx, hy, phase, keys, flipped, boxes_frozenset)`。箱子最多 6，位置 1040，状态空间大，但实际可达状态有限（箱子推动是确定性的）。可用 A* 带启发式：
- 若需要 P_GATE 打开（plates_active 的目标），计算所有 PLATE 位置，需要 BOX 占住它们。可以用一个「推箱子 Sokoban 求解」子程序：把箱子推到 PLATE 上（BFS over (box_pos, hero_pos)），输出推箱动作序列。
- 简化：把箱子纳入状态，用 A* 搜索到目标；启发式 = 到 V 的曼哈顿距离 + 未拿钥匙的估计 + 压板未激活的惩罚。

这样状态数可能爆炸，但有 1.6s 和启发式，可以处理。

**替代更稳妥方案**：分层目标规划
- 目标 1：让 plates_active 变 True（若图中有 P_GATE 且当前未激活）。用 Sokoban BFS 找到把 BOX 推上所有 PLATE 的动作序列。
- 目标 2：拿 K1、K2（顺序择优），期间可 THROW 翻门、可 BOMB 炸墙、可 WAIT 避激光。
- 目标 3：到 V。
每阶段用「位置 × phase × flipped × boxes」的 A*，但阶段目标单一，搜索空间小。

我觉得这是可行的。但完整实现 + 测试需要不少时间。让我先发宣告（按要求第一步），然后开始编码。

**宣告**（50~100 字，中文，面向全场）：
"上半场靠迷雾偷袭，下半场明牌开卷，正好换个打法：造图不再藏，直接上压板推箱、双频十二拍与单向闸门，把题目写成必须真解的逻辑锁；破阵也不再贪心试探，Turn 1 一次性全局状态搜索，之后逐拍校验纠偏。强基准只是及格线，我要的是通用解算器。"

数一下字数：约 100 字左右。稍长，控制到 50-100。让我写 80 字左右：
"上半场靠迷雾偷袭，下半场明牌开卷，正好换打法：魔王图上压板推箱、十二拍双频激光、单向闸门，把路写成必须真解的逻辑锁；勇者侧 Turn 1 一次性全局状态搜索，之后逐拍校验纠偏。强基准只是正常基准，通用求解器才是目标。" 约 95 字。好。

现在开始。先规划 TODO。

需要仔细设计实现。让我先看旧引擎代码以复用物理细节（读取 d:/ai_work/hunyuan_lab/engine.py）——这是上半场我自己写的引擎，包含 v2.1 的完整物理。这样能大幅减少重写工作，且保证与规则一致。用户要求"阅读 part2_full_mode/... 下的所有文件"，没禁止读其他文件；但"写成的一切文件均放在该文件夹"——我写的所有文件都放该文件夹。读取旧引擎可以。

不过，旧引擎在另一个 workspace（d:/ai_work/hunyuan_lab），可能仍存在。让我检查。

实际上，为了自包含和减少依赖，我打算把 v2.2 引擎写成 `local_engine_v22.py` 放在考场文件夹，从旧引擎复制并扩展。让我先读旧引擎。

时间考量：这是个大任务，我要高效。让我用 todo_write 建立计划，然后并行读旧引擎的若干部分。

先发放话（对话区）。按考场纪律"第一步：读完规则与本人战报后，在对话区先发一段 50~100 字下半场放话"。我已在分析，现在输出到对话区。

注意：不能在最终答案前就结束；要先发放话，然后继续工作。工具调用中间的 assistant 文本可以发放话。

让我开始。
```

## 032.1 · Thinking

```
先读旧引擎（上半场我自己写的），复用物理。检查是否存在。
```

## 040.1 · Thinking

````
好，上半场引擎完整。我可以复用它并扩展 v2.2。需要修改：
- COSTS/CAPS 增加新 tile、BOX cap 6、PLATE 4、P_GATE 8、ONEWAY 12、LASER2 + 红合计 12。
- HIGH 增加 LASER2_*、P_GATE（未激活时）、ONEWAY 不算高墙但进入方向限制。
- plates_active 实时计算。
- ONEWAY blocks_oneway 在 chain 中检查（普通移动/推箱/跳跃/冰面/镜面/弹簧/传送门/飞石/激光）。
- phase_d：turn%3==0 红炮，turn%4==0 蓝炮，同一快照齐射，每门 50 伤。
- laser_warnings 带 period 与 cannon。
- state 增加 plates_active。
- GATE 关闭时 P_GATE 处理；闭门滞留规则（实体停在开门内，门关不受挤压）。
- 出生 4 回合准入校验（用引擎模拟所有 Turn1 动作 + Turn2-4 序列，找 ≥2 个不同 Turn-1 末坐标 0 伤存活）。

我会写一个新文件 `local_engine_v22.py`（放在考场文件夹），基于旧引擎扩展。同时 decide_action 里的模拟器也要实现，但为了不重复太多，我可以让 submission.py 内含一个"轻量版"模拟（用于搜索），而本地引擎独立用于验证。不过保持一致很重要。

考虑时间，我打算：
- `local_engine_v22.py`：完整引擎（测试用）。
- `submission.py`：内含 `_Solver`，实现基于"抽象状态"的规划（不复制完整引擎，但内部实现单步转移函数，复用类似逻辑）。

两者共享物理规则理解，代码可以相似但不必完全相同。

先写 local_engine_v22.py。为了避免从零重写，我用 Python 脚本读取旧引擎并做替换生成新文件？不行，那是"用命令写文件"，但允许我用 write_to_file 写完整文件。我可以直接把旧引擎内容复制过来（我已读到全部 682 行，但我只读了 1-440 和 440-682 的部分，中间 200-440 已读，1-200 已读；实际上我读了 1-200, 200-440, 440-682，全部覆盖）。我可以重写一个新引擎文件，包含所有逻辑 + v2.2 扩展。约 700 行。

不过写 700 行比较耗时。更高效：用 execute_command 复制旧引擎文件到考场文件夹，然后用 replace_in_file 做针对性修改。但"写成的一切文件均放在该文件夹"——复制过来是写文件，放在该文件夹，符合要求。不过用 copy 命令可能被视为"临时文件"？不是，是本地测试工具，允许。

但风险：旧引擎在另一 workspace，评测机可能没有那个文件；但本地测试工具只在本地用，不影响 submission.py。OK。

不过更干净的做法：我自己写完整的 v2.2 引擎文件（自包含），这样不依赖外部文件。让我评估时间……我可以写，因为逻辑我已完全掌握。约 500-600 行。

我决定：写 `v22_local_engine.py`，自包含，基于旧引擎逻辑 + v2.2 扩展。然后写 `submission.py`（含求解器），再写 `v22_test.py` 做回归。

让我开始写引擎。为了效率，我会精简（不需要 BLIND 的 visible() LOS，因为 FULL 全图明牌；但为了测试 part1 图在 FULL 模式，visible 全部 True 即可，简化）。

引擎设计：

```python
"""v2.2 local forward simulator (testing only)."""
import copy
W,H=40,26
DIRS=...
COSTS (v2.2 单价)
CAPS
VALID_ACTIONS

def validate(grid, require_plate_box=True):
    # v2.2 检查：外框、spawn、地标坐标、距离、预算、各上限、portal 对、P_GATE 约束
    returns (ok, spent, info)

class Game:
    __init__(grid, mode="FULL"):
        terrain/occupant decode BOX/TNT
        portals
        clues bind (MIMIC)
        targets
        hero
        gates_flipped=False
        plates_active computed
        bombs=[]
        turn=1
        status
        exposed
        tnt_armed
        trap_damage
    def is_plates_active(self):
        plates = self.plate_positions
        return bool(plates) and all(occupant[y][x]=='BOX' for p in plates)
    def high(x,y,terr=None,occ=None,flip=None,plates=None):
        t = ...
        if t in HIGH (W,T_W,LASER*,LASER2*): True
        if t=='R_GATE' and not flip: True
        if t=='B_GATE' and flip: True
        if t=='P_GATE' and not plates_active: True
    def blocks_oneway(x,y,d,terr=None): 
        t = terr[y][x]; if t.startswith('ONEWAY_') and d != DIRS[t[-1]]: True
    def passable(p,kind,d=None): high, occ, oneway check
    def chain(kind,p0,p1,d,...): 与旧引擎类似，加入 oneway 检查
    def throw(d): 空中 6 格穿透 ONEWAY；地面滑行检查 ONEWAY
    def rays(period_filter=None): 返回 (cannon, dir, cells, period)，射线遇 BOX/TNT/high 停；ONEWAY 不阻挡激光
    def explode / phase_c / phase_d
    def action(act)
    def state(): 全图明牌；laser_warnings 含 period/cannon；plates_active
```

对于 ONEWAY 在 chain 中的处理，规则说：
1. 普通 MOVE 与推箱：前置先验 p1；若该格上停 BOX 逆向推动整次拒绝；推箱时 BOX 目标格 p2 验 dir，箱链完成后勇者跟进 p1 再验 dir。
2. JUMP：p1 与 p2 都要满足非高墙且不 blocks_oneway(..., jump_dir)。
3. ICE/MIRROR：按当前 dir（镜面折转后 new_dir）检查下一格。
4. SPRING：逐格检测 k=1,2,3，遇逆向 ONEWAY 阻挡停于 k-1。
5. PORTAL：到达 B 后保持原方向尝试向前 1 格时，若前方为逆向 ONEWAY 则停稳在 B。
6. THROW：空中 6 格自由穿过 ONEWAY；地面滑行撞到 ONEWAY 按普通非冰地面立即停稳消失。
7. LASER：自由穿过 ONEWAY（但站在 ONEWAY 上的 BOX 遮挡）。

我实现一个统一的 `blocked(x,y,d,kind)`：high || occ BOX/TNT || blocks_oneway。对激光射线只用 high || BOX（TNT 截断），不用 oneway。

phase_d：当 turn%3==0 或 turn%4==0：
- 快照 terr/occ/flip/plates（阶段 C 后）。
- 对每条存活炮（period 匹配），射线格集合；统计与 exposed 有交集的炮数 m；伤害 50*m。
- 同时击中 TNT 只引爆炸一次。
- 注意 GV22_03：turn=12, 红 LASER_D(15,8) 向下射线覆盖 (15,9),(15,10)...；蓝 LASER2_R(12,10) 向右覆盖 (13,10)...(15,10)。hero 在 (15,10) WAIT，exposed={(15,10)}，两门都命中 → 100 伤。

state() 里 laser_warnings 要包含 period 和 cannon，且是"当前阶段 A 前快照"（即刚调用 action 前的状态）。我在 state() 里用当前 terrain/occupant 计算 rays（未修改），过滤 period。

plates_active 在 state 里输出。

validate 里 P_GATE 约束：`1 <= PLATE <= BOX`。注意 BOX 数量也算 occupant 层的 BOX tile。

出生 4 回合准入：我需要一个函数在 validate 或 test 中做：模拟所有可能的 Turn1 动作（14 种）得到不同的 (pos, hp==100) 落点，然后对每个落点，检查存在 Turn2-4 的 0 伤行动序列（BFS over states 到第 4 回合结束）。这需要用 Game 复制状态（deepcopy）。可以做简化：从初始 Game 出发，枚举 Turn1 的所有动作，记录 hp==100 且 status PLAYING 的落点；对每个落点，BFS 深度 3（turn 2,3,4），枚举动作，只要存在一条 0 伤序列即可。状态用 deepcopy(game)。数量：14 * 14^3 = ~38k deepcopy，每个 deepcopy 26x40 列表 ~ 1000 元素，可能有点慢（几十秒）。可以剪枝：Turn1 后按落点去重（最多 ~10 个），每个落点 BFS 只需找到一条安全序列即可（早停）。Turn2-4 每回合只需找至少一个 hp 不变的动作，不用全枚举？但"存在零机关伤害安全行动序"需要序列，且后续回合可能因状态变化（如 CRACK 坍塌、激光拍）导致之前安全的动作变危险。可以逐回合贪心地找第一个 hp 不变的动作，若找到就继续；若某回合找不到，回溯。简化为 DFS 带早停，通常第一个 WAIT 就安全。可以做：对每个落点，DFS 深度 3，每层枚举 14 动作，找到 hp 不变且 PLAYING 就递归。这样很快。

好，写引擎。

关于 decide_action 的求解器，先想清楚再写。

**求解器架构**

Turn 1（1.6s 预算）：
1. 从 state 解析静态地图（terrain 全图明牌）。注意 state['terrain'] 中 HEAL/MIMIC 显示为 'CHEST'，clues 可辨（clues[y][x]=True 表示邻近有 MIMIC → 该 CHEST 是 MIMIC）。occupant 提供 BOX/TNT 位置。
2. 计算静态激光射线（按周期），得到 `danger[phase][cell]`，phase = turn % 12（0..11）。红炮在 phase%3==0 且 !=0? 实际 turn%3==0 → phase ∈ {0,3,6,9}（因为 turn mod 12 = phase，turn%3==0 对应 phase ∈ {0,3,6,9}）。蓝 turn%4==0 → phase ∈ {0,4,8}。phase 0 即 12k 双射。
   注意：turn 从 1 开始，phase = turn % 12。
3. 搜索状态：`(x, y, phase, keys_mask, flipped, plates_mask?, boxes?)`。为了处理 P_GATE/PLATE/BOX，我需要把箱子纳入状态，但只在有 P_GATE 时。

嗯，让我重新考虑：也许更简单有效的办法是**用完整引擎做前向搜索（A*）**，状态 = 序列化 Game 的关键字段（hero pos, hp, keys, flipped, terrain 可变部分, occupant, bombs, turn%12）。用启发式（到目标的曼哈顿距离 + 未拿钥匙惩罚）。每个节点扩展 14 个动作，模拟一回合。1.6s 内大约能扩展几千到几万节点（取决于模拟成本）。用 `copy.deepcopy` 太慢；可以用轻量状态 + 增量模拟。

我觉得务实做法：**分层规划 + 静态 A*（不模拟完整引擎）**，并针对"推箱开门"和"翻门"做专门处理。

具体：
- 建立"抽象转移" `step(pos, phase, keys, flipped, plates, boxes, act)` → (new_pos, damage, new_keys, new_flipped, new_plates, new_boxes, moved)。用纯静态地形 + occupant（BOX 可变）。
- 抽象状态包含 boxes（frozenset of positions，最多 6）。
- A* 目标：`keys==3 and pos==V`（且 hp>0）。
- 启发式：`dist(pos→V) + (未拿钥匙 ? min(dist→K) : 0)`，加上 plates 未激活惩罚。
- 代价：1/步，damage 惩罚大（如 100/伤），优先 0 伤。
- 允许动作：MOVE×4、WAIT、JUMP×4（保留次数）、THROW×4（保留次数，用于翻 SWITCH）、BOMB（可选，用于炸 W / 炸炮，但会让状态复杂；先支持简化：BOMB 炸掉 3x3 内 W/炮座/箱，需要 timer 3 回合，复杂 → 暂不支持或仅作为"炸墙开路"的特殊处理）。
- 钥匙顺序：目标函数本身会引导拿钥匙；但 A* 状态含 keys_mask，会自动选择顺序。
- 输出动作序列 + 预期状态签名。

Turn>1：
- 如果 memory 有 plan 且当前 state 与预期一致 → 返回下一个动作。
- 否则重新规划（同样 A*，从当前 state 出发），限时 0.4s。

**关键难点：A* 状态空间 (x,y,phase,keys,flipped,plates,boxes)** 可能很大。但用 A* + 好启发式，通常几千节点就够。注意 laser danger 依赖 phase（12 拍），所以状态含 phase 是必要的。

对 BENCH_WEAK：
- 红门 R_GATE(17,8) 挡 K1，需要翻门 → THROW 或踩 SWITCH(12,10)。SWITCH 在 (12,10)，从 spawn 可走到 → 踩上即翻转。路径规划需要知道踩 SWITCH 会 flip。抽象转移里：踏上 SWITCH 自动 flip。
- P_GATE(35,15) 挡 V，需要 PLATE(11,17) 被 BOX 压住。BOX(8,17) 在 ICE(9,17),(10,17) 左边，PLATE 在 (11,17)。推箱：勇者从 (7,17) 向右推 BOX，箱子经 ICE 滑行会一直滑到... (8,17)→(9,17) ICE→(10,17) ICE→(11,17) PLATE→(12,17) EMPTY 继续? 普通地面摩擦：箱子 chain 中 ICE 会继续滑，直到非 ICE 格停止。PLATE(11,17) 是普通地面，箱子到 (11,17) 后检查 terrain 不是 ICE/MIRROR/SPRING/PORTAL → STOP。所以一次推动箱子从 (8,17) 滑到 (11,17) 压板！漂亮。这符合基准设计。
- ONEWAY_D(24,20),(24,22) 围绕 K2(24,21)：只能从上方 D 进入 (24,20)，从下方? ONEWAY_D 在 (24,22) 意味着进入方向必须是 D（从 (24,21) 向下到 (24,22) 是 D，OK）；K2 在 (24,21)，从 (24,20) 向下进入 K2 是 D 方向（但 K2 格不是 ONEWAY）；要离开 K2 向下到 (24,22)，进入 (24,22) 方向是 D，符合 ONEWAY_D。所以只能从上往下穿过 K2 区。从 (24,22) 想回 (24,21) 是 U 方向进入 (24,21)（非 ONEWAY，OK）但再想到 (24,20) 是 U 方向进入 ONEWAY_D(24,20) → 被拒。所以是单向。
- ONEWAY_R(34,15) 在 P_GATE(35,15) 前，V(36,15)。进入 (34,15) 必须方向 R。
- LASER2_D(34,9) 蓝炮向下，LASER_R(26,15) 红炮向右。需要计时避开。

如果我的求解器把 ONEWAY 和推箱和激光相位都建模，就能解出 BENCH_WEAK。

BENCH_STRONG：
- 3 个 PLATE (7,6),(8,18),(8,22)，2 个 P_GATE (11,13),(35,13)。需要 3 个 BOX 压住全部 PLATE（BOX 有 4 个：(3,9),(23,13),(4,17),(4,21)）。且有 MIRROR_SE(8,17)、ICE(5,17),(6,17),(7,17)、SPRING_R(5,21)、TNT(18,22)、PIT 两格 (25,13),(26,13)、ONEWAY_U(7,7)、ONEWAY_R(27,13)、R_GATE(20,7)、SWITCH(15,13)、LASER_D(31,8)、LASER_L(38,12)、LASER2_U(34,18)。这确实需要真正的多步推理（推 3 个箱子上板，还要用 BOX 填两格 PIT，或者 JUMP 跨过）。

我的通用 A* 若把 boxes 纳入状态，状态空间会很大（6 箱 1040 格组合），但搜索时只会推少量箱子；Sokoban 是 PSPACE-hard，但小地图可以 heuristic。1.6s 可能不够完全解 BENCH_STRONG。提示也说"打过强基准也不代表强，它只是一个正常基准"，意味着强基准难，且不代表最终实力。我需要尽力但优先保证通用性和弱基准。

**重要**：我还需要考虑"正赛地图"是其他选手造的新图，可能很刁钻。通用求解器的稳健性比过两个基准更重要。所以设计要通用、避免崩溃、有降级策略。

让我把 A* 搜索设计得高效：
- 状态：`(pos_idx, phase, keys, flipped, plates_on, boxes_tuple)`，其中 plates_on 可由 boxes 与 plate 位置推出，不必单独存。boxes_tuple 是排序后的箱子位置索引元组。
- 为减少状态，只在地图含 P_GATE 时才把 boxes 纳入；否则 boxes 固定（但箱子会挡路，且可以被推 → 忽略推箱以简化，若箱子挡住唯一路径再考虑）。
- 转移：对每个动作，计算结果位置/damage/keys/flip/boxes。
- 激光伤害：若 turn phase 命中（红 phase∈{0,3,6,9}, 蓝 phase∈{0,4,8}），检查 exposed 格（起点+经过的格）与射线格的交集 → 按炮数 50 伤。为简化，抽象转移只记录"经过的格子集合"，用于判定。
- PIT：进入即 -100 死（除非 BOX 填）。CRACK：走一次后变 PIT（状态里要记录，复杂 → 简化：CRACK 视为可走，之后不再回头，或标记为 PIT 状态的一部分）。为了通用，可以把"可变地形"用 bitmask 记录哪些 CRACK 已坍塌 —— 但状态膨胀。嗯。

考虑到实现复杂度，我打算把"地形可变性"简化：只跟踪 boxes、flipped、plates、keys、phase、pos、hp、jumps/throws/bombs 剩余。对于 BOMB 炸墙：允许作为一个动作但简化处理（3 回合后爆炸，摧毁 3x3 的 W/炮/箱，把 CRACK 变 PIT）。可以把 bombs 也纳入状态（timer），但复杂。我先不把 BOMB 纳入默认动作集，除非检测到"所有路径都被 W/门挡住且无其他解"，再做特殊处理。

实际上，对于正赛，很多图会用 W 墙造迷宫（可炸），BOMB 是重要工具。上半场我自己的图就被 SOL 用炸弹炸穿了。所以求解器需要 BOMB。

嗯，让我换个思路：**用完整引擎做搜索，状态序列化为紧凑元组，节点扩展用引擎的轻量副本**。为了避免 deepcopy 慢，实现一个 `FastSim` 类，状态用可变数组 + 记录变更日志（undo）。或者每次复制几个小结构（terrain 用 dict of overrides、occupant 用 dict、hero 用 tuple），这样复制成本低。

我觉得这个方案最稳：**把地图表示为不可变基础 + 覆盖字典（overrides）**。状态 = (hx,hy,hp,keys,jumps,throws,bombs_left,flipped, overrides_terrain, overrides_occ, bombs_list, turn, phase)。转移时只复制 overrides（小 dict）。这样 A* 每节点扩展 14 个动作，成本低。

但完整实现 phase_c/d、爆炸、TNT、激光、ONEWAY、推箱……代码量大。不过我可以把"本地引擎"和"求解器用的模拟器"做成同一份代码，放在 submission.py 里！这样：
- submission.py 内含 `Sim` 类（完整 v2.2 前向模拟，支持 copy/undo 或轻量复制）。
- decide_action 用 A* 搜索 Sim 状态。
- 本地测试脚本 import submission 的 Sim 来验证地图和基准。

这样一份代码两用，避免不一致，且提交自包含（评测时需要模拟器做规划，合理）。

但注意：submission.py 会很长（~1000+ 行），import 时间要 <1.5s（纯函数定义，没问题）。build_dungeon <2s，decide_action Turn1 <2s。

我决定：**写一个统一的 `Sim` 类到 submission.py**，同时外部测试脚本 import 它。这样 `local_test.py` 只需少量代码。

不过 Sim 要支持"从任意 state 构造"（评测时 decide_action 拿到 state，需要重建 Sim 状态）。state 里包含 terrain（全图）、occupant、bombs、hero、gates_flipped、plates_active、clues、targets、turn。够用。

设计 Sim：
```
class _Sim:
    def __init__(self, base_terrain, base_occ, ...):
        self.t = base_terrain  # list of lists (mutable)
        self.o = base_occ
        ...
    def snapshot(self) -> tuple (紧凑)
    def restore(self, s)
    def step(self, act): 修改状态，返回 info
```
用深拷贝列表进行 A* 每次扩展会很慢（26*40*2 = 2080 引用复制，几十微秒），1.6s 内可扩 ~1-2 万节点 → 可能够，但 A* 需要更多。用 `copy.deepcopy` 更慢。

优化：状态用「基础不变地形 + 变更字典」。我实现：
```
self.base_t = tuple of tuples (初始 terrain，其中 BOX/TNT 已解码为 EMPTY)
self.dt = {}  # (x,y) -> tile override
self.base_o = {}  # (x,y) -> 'BOX'/'TNT'
self.do = {}      # occupant overrides
self.bombs = tuple of (x,y,timer)
self.hero = (x,y,hp,keys_mask,jumps,throws,bombs_left)
self.flipped = bool
self.turn = int
self.status
```
`tile(x,y) = self.dt.get((x,y), base_t[y][x])`，`occ(x,y) = self.do.get((x,y), base_o.get((x,y)))`。
snapshot 复制 dt/do/bombs/hero 等小结构。dt/do 通常很小。这样每节点复制成本 ~ 微秒级。

good。A* 状态 key = (hx,hy,hp,keys,flipped,turn%12, tuple(sorted(dt.items())), tuple(sorted(do.items())), bombs, jumps, throws, bombs_left)。为避免爆炸，限制搜索节点数（如 60k）和时间。

启发式：静态几何距离（预计算从每个目标到所有格的最短距离，忽略激光但考虑静态墙/坑/单向门），h = dist_to_next_key + dist_to_V。可以用 BFS 从 K1/K2/V 反向计算（考虑单向门方向！）。简单起见用曼哈顿距离（可采纳但弱），或者用 BFS on passable static graph（忽略激光/相位）得到更紧的启发。

实现 BFS 距离图：从目标格反向 BFS，边为「从 n 到 p 可移动」。考虑 ONEWAY 时方向性：从 p 移动到 n 需要 p→n 的方向满足 n 的 ONEWAY 要求。反向 BFS 时，从 n 扩展到 p（前驱），检查 p→n 合法。

好。

**A* 代价**：每步 cost=1 + damage*10（希望 0 伤），另外对 WAIT 加小惩罚（避免原地等待过多，但必要时要等相位）。找到目标（hp>0, keys==3, pos==V, status CLEARED）即回溯。

**动作集**：14 种全部，但 BOMB 会引入 3 回合延迟爆炸（状态含 bombs 与 timer），可以支持。JUMP/THROW 消耗次数（纳入状态）。

**phase_d 激光判定**：需要从当前状态计算 rays（可缓存基础 rays，但门开关/箱子/炮被炸会变 → 动态计算）。每节点 12 门炮 * 10 格 = 120 次查询，14 动作 → 1680 查询/节点，偏重。优化：只在 phase 是激光拍时计算（每 12 拍中有 6 拍：{0,3,4,6,8,9}），其余跳过。还可以预计算炮位列表与方向。

嗯，这个搜索会比较重。让我先实现，测性能再优化。

**时间预算管理**：Turn 1 用 `time.monotonic()` 截止 `start + 1.6`。搜索中定期检查。若超时，用当前最优（best partial plan）或返回一个贪心安全动作。Turn>1 用 0.4s 截止。

**计划执行与校验**：Turn1 搜索得到完整动作序列 → 存 memory。之后每回合：
- 用 Sim 从当前 state 重建，执行 plan 中剩余的第一个动作前，先比对"执行前的预期状态签名"与当前实际 state（pos,hp,keys,flipped,plates,turn）。若一致 → 返回动作。
- 若不一致 → 重新规划（限时 0.4s），并更新 plan。

更简单：每回合都用 Sim 从当前 state 重建并"重放 plan 的第一个动作"验证结果是否符合预期；其实只要每次执行后检查 state 与预期一致即可。若不一致就重规划。

其实最稳的是：**每回合都重新规划**（用当前 state 做 A*），但只在需要时（Turn1 或偏离）做完整搜索，其他回合用缓存 plan。为了省时，缓存 plan。

**降级**：如果 A* 找不到解，用「贪心」：向最近目标走，避开当前回合危险格，避免 PIT。保证不死、不超时太多。

好，现在开始写代码。先写 `submission.py`（含 Sim + 求解器 + 造图）。这个文件会很大，我分块写：先写 Sim 引擎部分，再写求解器，再写造图。可以用 write_to_file 一次性写完整，但内容很长容易出错。我分多次：先写完整文件框架（Sim），然后用 replace_in_file 追加？replace_in_file 需要 old_str 唯一匹配，可以用文件末尾的标记。或者一次写完整个文件（我会小心）。

考虑可维护性，我打算：
1. 先写 `submission.py` 的第一版：完整的 Sim + 求解器 + 造图（我尽量一次写好）。
2. 写 `v22_local_test.py` 测试脚本（import submission，验证 golden vectors、基准图、自造图、跑 FULL 对局）。
3. 迭代修正。

由于代码量大，先写 Sim 与求解器，造图暂时放一个占位实现，随后补。不，还是一次写完更省事。让我组织代码结构：

```
"""docstring"""
import heapq, collections, time, itertools, bisect, math, copy  (只用允许的库)

W,H,INF,DIRS,VEC2DIR,VALID_ACTIONS,NEI4
TILE_COSTS (v2.2)
CAPS
HIGH_BASE = {W,T_W,LASER_*,LASER2_*}
MIRROR_MAP

# ---------- v2.2 合规校验（供 build_dungeon 自检/本地测试） ----------
def _validate_grid(grid) -> (ok, spent, info)

# ---------- 完整前向模拟器 ----------
class _Sim:
   __init__(self, grid or state)
   ...
   def step(self, act)
   def state() (给 decide_action 重建用/测试)
   ...

# ---------- 求解器 ----------
def _plan(state, deadline, max_nodes) -> list of actions
def _greedy(state) -> action
def decide_action(state, memory) -> str

# ---------- 造图 ----------
def build_dungeon() -> dict
```

关于 `_Sim` 从 state 构造：
- terrain 是 state['terrain']（CHEST 代表 HEAL/MIMIC，需结合 clues 判断）。为了模拟 MIMIC/HEAL 效果，需要知道哪个是 MIMIC。规则：clues 全露，孤立线索可 100% 辨别真假。实现：对每个 CHEST 格，若其 4 邻有 clues=True 且该 clue 只对应这一个 CHEST → MIMIC；否则 HEAL。简化：若 CHEST 的 4 邻存在 clues True → MIMIC，否则 HEAL。（对自造图/基准图应足够。）
- occupant: state['occupant']。
- bombs: state['bombs']（列表 of dict with x,y,timer,id）。
- hero: state['hero']（x,y,hp,keys,jumps,throws,bombs）。
- gates_flipped, turn。
- targets: K1/K2/V 位置（从 terrain 或 targets）。
- plates_active 可由 occupant 与 PLATE 位置派生。

注意：state['terrain'] 在 FULL 模式全为真实 tile（除 CHEST）。K1/K2/V 会在 terrain 里显示（未拾取时）。拾取后变 EMPTY。

`_Sim.step(act)` 完全复刻引擎的 8 步阶段：
- A: 解析动作，位移/推箱/跳跃/投掷/放炸弹；exposed 集合。
- B: （规则里阶段顺序？上半场引擎：action → phase_c → phase_d → win check）。实际规则 v2.1 阶段：A 动作、B 机关、C 爆炸、D 激光。上半场引擎把 C/D 放最后，且 CLEARED 判定在位移里立即返回（V 立即通关，先于 D）。GV22_08 说"V instant win before phase D"。OK，保持：V 立即 CLEARED，跳过 C/D。
- C: 炸弹 timer-1，爆炸（TNT、连锁），plates_active 重算。
- D: 若 turn%3==0 或 turn%4==0，按快照计算射线，伤害 50*命中炮数，TNT 引爆。
- turn += 1。

`exposed` = 起点 + 所有经过格（chain 中每个 p1）。激光判定用 exposed。

`hurt(amount, trap)`：trap_damage 累加（用于本地测试计分），hp 减少。

`plates_active`：PLATE 位置列表 + 每个 occupant=='BOX'。注意：BOX 在 PIT 上会填坑并消失（chain 中处理）。

`ONEWAY` 检查函数 `blocks_oneway(x,y,d)`：tile.startswith('ONEWAY_') and d != DIRS[tile[-1]]。

`passable(p, kind, d)`：high false, occupant 不是 BOX/TNT（对 BOX 移动还要检查 hero 位置和 K/V），且 not blocks_oneway(p, d)。

`chain` 里，进入每格都要检查 blocks_oneway。对 ICE/MIRROR 的下一格，用 cur_dir（镜面折转后的 new_dir）检查。SPRING 逐格检测时用 sdir 检查。PORTAL 到达 B 后向前 1 格时用原 dir 检查。

`throw`：空中 6 格忽略 ONEWAY；地面滑行时若遇 ONEWAY 逆向则停。规则 6："飞石空中 6 格飞行自由穿过所有方向的 ONEWAY_*（正常消耗射程）；若第 6 格落入 ICE/MIRROR_* 转入地面滑行，滑行撞到 ONEWAY_* 时按普通非冰地面立即停稳消失。" 所以滑行中遇到 ONEWAY 格就停（不论方向？"按普通非冰地面立即停稳"→ 遇到 ONEWAY 就停）。实现：若 t 是 ONEWAY → return（停稳，不触发后方）。

`rays`：只在 period 匹配时列出炮座，射线 10 格，遇 high 或 BOX 停；遇 TNT 记录并停（TNT 格不是"lit cell"？GV22_03 不涉及；上半场引擎 rays 里 TNT 格不加入 cells。保持一致）。ONEWAY 不阻挡。P_GATE 关闭时算 high → 阻挡（规则说 high wall 集合含关闭的 P_GATE）。

`explode`：3x3，TNT 连锁，BOMB 连锁，摧毁非免疫格（immutable = T_W, K1,K2,V,PIT,PORTAL,PLATE,P_GATE,ONEWAY,TNT? 规则：PLATE/P_GATE/ONEWAY 防爆免疫；TNT 被引爆消失；BOX 被炸毁；CRACK 变 PIT；W/ICE/MIRROR/SPRING/LASER/SWITCH/R_GATE/B_GATE/HEAL/MIMIC → EMPTY 或摧毁）。
伤害：TNT 60/个，BOMB 50/个，3x3 内叠加。

`phase_c` 里 bombs timer 从 3 减到 0 时爆炸（上半场引擎 timer 初始 3，每回合 -1，<=0 爆炸，即第 3 回合爆炸）。

好，开始写。为了控制篇幅，我把 Sim 写得紧凑但完整。

另外 build_dungeon 的设计，我需要先确定地图，再用 Sim 验证。让我现在设计地图。

**新地图设计（v2.2 逻辑锁）**

目标：
- 合法、≤200 步自证、出生 4 回合准入、预算 ≤3000G
- 对强求解器也有难度；对弱求解器造成 TIMEOUT/DEAD
- 用上新机关：PLATE/P_GATE/BOX、LASER2、ONEWAY

核心构想：**双压板 + 单向门 + 12 拍激光节拍 + 长蛇形路径**。

但注意：我们的 author_solution 必须是 ≤200 步的实际动作序列，且自己能通关。我要能构造并验证。

简化设计思路：沿用上半场成功的"四道横向隔离墙 + 蛇形绕行"结构（229 步太长，需压缩到 ≤200）。改成 3 道墙 → 约 150 步。然后加：
- 一道 P_GATE 锁在通往 V 的必经位置，需要把 BOX 推到 PLATE 上（给 author 解留一条简单推箱路径）。
- 若勇者不会推箱 → TIMEOUT。
- 在必经的开阔带放红蓝交叉激光，使勇者必须按 12 拍相位等待（否则 -100 瞬杀）。author 解里安排 WAIT。
- ONEWAY 门布置在关键窄道，走错不可逆（增加难度）。

但问题：这些机关对我自己的求解器也是可解的（我写的求解器会处理推箱和相位），所以自证没问题。而对手若不实现同样能力就会卡住。

预算：3 道墙 * 38 W * 5 = 570G；激光 4 红 + 4 蓝 = 4*75+4*90=660G；PLATE 2*45=90G，P_GATE 2*30=60G，BOX 3*30=90G；ONEWAY 6*30=180G；PIT/ICE/CRACK/MIMIC 等 ~600G；T_W 少量。总计 ~2200-2600G，留 g=(3000-spent)/3000 给魔王分。g 越大魔王分越高：实杀 +250g，困死 +125g。所以造价低更好！上半场 ASTRA 575G 拿 949 分（10 实杀）。所以**低造价 + 高杀伤**是最优。

但低造价意味着机关少，可能困不住强勇者。权衡：用便宜但巧妙的机关。W 只要 5G/格，很便宜。PIT 40G，激光 75/90G。

让我设计**低造价高效**地图：
- 用 W 墙造"逻辑迷宫"（便宜）。
- 用少量激光造"节拍锁"（关键杀招）。
- 用 PLATE/P_GATE/BOX 造"必需推箱"（约 200G）。
- ONEWAY 少量（约 90-180G）。

**核心杀伤机制：出生点附近的 12 拍双频激光通道？** 但出生 4 回合准入禁止开局强杀。规则要求"至少 2 个不同 Turn-1 零伤落点能 0 伤活过 Turn 4"。所以不能一开局就死。可以在稍远处（Turn 5+）设杀招。

**更稳的杀伤：利用激光节拍在唯一通道上**。例如一条 1 格宽的走廊，长度 10，被一门红炮（period 3）沿走廊纵向照射；另有一门蓝炮（period 4）横向照射走廊中段。在交叉点，phase 0（12k）双射 -100。勇者必须在特定拍进入/通过；若求解器不考虑相位，就会死。

但强求解器会考虑。那怎么办？让"通道长度 >10"，使单回合无法一次通过，必须停留多个拍；并且每个拍的安全位置不同 → 需要精确 12 拍规划。强求解器也能解，但会增加 T（等待），提高魔王失守分。

嗯，更重要：**对手求解器未必实现了推箱 + 相位的联合搜索**。若 P_GATE 锁住 V，且需要推箱，很多求解器会直接 TIMEOUT（上半场我的 BLIND 求解器就多次 TIMEOUT）。这很可能是主要得分点。

我决定设计一个**"必须推箱开门 + 单向门 + 双频激光节拍 + 蛇形长路"**的图，造价控制在 ~1200-1800G（g 较大），author 解 ~150-190 步。

具体布局（40x26）：

参考上半场我自己的图：4 道墙 y=4,8,17,21，缺口 x=38,1,38,1，路径 229 步。改成 3 道墙 y=5 (gap x=1), y=12? 不行，spawn 在 y=13 附近，净空区 x∈[1,3], y∈[12,14] 必须 EMPTY，墙不能在 y=12..14 覆盖 x=1..3（但可以在 x≥4）。

让我设计新的墙布局，使蛇形路径约 150 步：
- 墙 A: y=6, x=1..38 全 W，缺口 gA=38（右）
- 墙 B: y=16, x=1..38 全 W，缺口 gB=1（左）
- K1 在 y=2..10 区（比如 (14,3)），K2 在 y=15..23（比如 (20,20)），V 在 (36,13)。

路径：spawn(2,13) → 上到 y=5 → 右到 x=38 → 穿墙 A 到 y=5? 等等。

上半场路径 229 步是因为 4 道墙 + 缺口交替 + 目标位置。3 道墙约 150-170 步。

但还要放推箱逻辑。让我把 P_GATE 放在通往 V 的走廊上，PLATE+BOX 放在一个容易到达的小区域。

具体：
- V 在 (36,13)。用 W 墙把 V 周围三面围住，只留一个入口 (35,13) 放 P_GATE。即 (35,12),(35,14),(36,12),(36,14),(37,13) 设为 W 或 T_W；入口 (35,13)=P_GATE。勇者必须让 plates_active=True 才能进。
- PLATE 在 (10,17)（左侧区域），BOX 在 (7,17)，中间 ICE (8,17),(9,17) 让一次推动把箱子滑到 PLATE。类似 BENCH_WEAK（但不能照抄太多；可以用不同布局）。
- 实际上为了让"必须推箱"更硬，用 2 个 PLATE + 2 个 BOX，且 BOX 推到板上的路径需要绕。但复杂 → 先用 1 PLATE + 1 BOX，简单可靠。

- ONEWAY：在必经通道上放几个单向门，比如 (36,13)? 不行 V 在那。放在墙缺口处：墙 A 缺口 (38,6) 放 ONEWAY_D（只能向下通过）？注意墙缺口必须让勇者双向通过才能完成蛇形（拿钥匙后要回来）。单向门会让路径不可逆 → 需要重新设计路径为单向环路。这增加难度但也增加 author 解设计复杂度。可以在非关键处放 ONEWAY 制造"陷阱"（比如一个诱人的捷径是单向的，进去就出不来 → 对手求解器若不考虑会卡死）。

- 双频激光：在墙 A 与墙 B 之间的开阔带（y=7..15）布置红炮与蓝炮交叉。比如 LASER_D 在 (20,7) 向下扫 y=8..17（10 格），LASER2_R 在 (10,11) 向右扫 x=11..20（10 格）。交叉区域 (20,11) 在 phase 0 双射。再放几门形成"节拍走廊"。

关键：author 解必须避开所有激光射线格（在危险拍），或者用 WAIT 调整相位。为简单，我让 author 解走一条完全不经过任何射线格的路径（像上半场那样），这样自证 100 HP。而对手若不避开则死。为让"避开"需要真实推理，把射线覆盖在宽带的中间，逼勇者走边缘或精确计时。

嗯，其实若存在完全避开射线的路径，强求解器会找到并通关，T 约 150-190 → 魔王失守分 ~100-120。这不算高但保底。加上推箱锁，多数对手 TIMEOUT → 320+ 分。

我觉得可以接受。但为了更高分，可以**让所有到 V 的路径都必须穿过至少一个激光射线格**，且只能在特定相位通过（即不存在"完全避开"的路径）。这样 author 解需要精确 WAIT。强求解器也能解（因为它搜索相位），但弱求解器会死。这样更体现"必须真解"。

设计：把 P_GATE 入口前的一段窄走廊用两门炮覆盖：
- 红 LASER_R 在 (30,13) 向右扫 (31..40,13)，覆盖 (31,13)...(36,13)（含 V！）。等等，V 被射线覆盖的话，到达 V 那一拍必须不是红炮开火拍。可以安排。
- 蓝 LASER2_D 在 (33,10) 向下扫 (33,11..20)，覆盖 (33,13)。
- 交叉格 (33,13) 在 phase 0 双射。

如果 V 在 (36,13)，走廊从 (31,13) 到 (36,13)，红炮扫整条，那么勇者在走廊里的每一拍若是红炮开火（phase 3,6,9,0）就会挨 50；若同时蓝炮（phase 4,8,0）在 (33,13) 又 50。要 0 伤，必须整段走廊只在"红不开火"的拍停留/通过，且经过 (33,13) 时蓝也不开火。红开火 phase {0,3,6,9}，蓝 {0,4,8}。安全 phase（红蓝都不开火）：{1,2,5,7,10,11}。连续可通行窗口：phase 1,2（2 拍），5（1 拍），7（1 拍），10,11（2 拍）。走廊长 6 格，需要 6 个连续安全拍 —— 不可能！所以必须挨伤，除非用 JUMP 或 ICE 滑行一次跨过多格。

嗯，可以改：让走廊短一些（2-3 格），或用 JUMP 跨 2 格。或者让 author 解允许吃一点伤但活着（HP 100，吃 50 也能通关，D=50 → 魔王分 +85 for cleared）。但 author_solution 只要求"恰好最后一步存活踏上 V"，没要求满血。所以可以允许挨 50 伤。

不过如果 author 解带伤，D 会让魔王分在对局中更高？不，D 是对手实际受到的伤害，与 author 无关。author 解只是可达性证书。

所以我可以让 author 解吃一点伤，只要活着通关。但更稳妥是 0 伤。

让我简化：走廊用 **红蓝同相位覆盖关键 1 格**，author 解在那个格只在安全拍通过。设计一条 1 格窄门 (34,13)，红炮横扫 (31..39,13)，蓝炮纵扫 (34,11..20)。要通过 (34,13) 必须在 phase ∈ {1,2,5,7,10,11}。走廊长度 2（(33,13),(34,13),(35,13) P_GATE,(36,13) V）。从 (33,13) 出发，phase 需要：进入 (34,13) 时安全，进入 (35,13) 时？ (35,13) 在红炮射线上（红扫到 x=40），所以进入 (35,13) 那一拍也要红不开火。连续 2 拍安全：phase 1,2 或 10,11。可行（2 连续）。加上 (36,13) V 也在红炮射线，到达 V 那一拍也需红不开火 → 需要 3 连续安全拍。红不开火连续最多：phase 1,2（2 拍），4? 4 是蓝开火但红不开；5 红不开；7 红不开；10,11（2 拍）。红不开火拍集合 = {1,2,4,5,7,8,10,11}（因为红 phase {0,3,6,9}）。连续段：{1,2} (2), {4,5} (2), {7,8} (2), {10,11} (2)。只有 2 连续。所以需要 3 拍连续 → 不可能 0 伤，除非用 JUMP（一回合跨 2 格）。

可以让 author 解在 (33,13) 用 JUMP_R 跨到 (35,13)（跳过 (34,13)），然后 MOVE_R 到 V。JUMP 的 exposed 包含 (33,13),(35,13)？规则 JUMP 中间飞越格 p1 与落点 p2 都算进入；exposed 应包含起点、p1? 上半场引擎 chain("hero", p0, p2, d) 里 exposed.add(p1) 只是 p2=(x1,y1)，即落点。JUMP 从 (33,13) 到 (35,13)，chain 的 p0=(33,13), p1=(35,13)，exposed={(33,13),(35,13)}。中间 (34,13) 不算暴露。这样避开蓝炮交叉格。红炮仍覆盖 (35,13) 和 V。

嗯，这个设计有点绕。让我简化，别过度设计。**保留"存在完全避开射线的路径"**，但把 P_GATE 推箱锁作为主要难点，激光作为"贪心求解器的死因"（放在诱人的直线上）。这样：
- 弱/中求解器走直线 → 撞激光死或撞 P_GATE 卡住 TIMEOUT。
- 强求解器找到绕行 + 推箱 → 通关，T 大 → 魔王分中等。
- 我们的 author 解 0 伤 ≤200 步。

这已经不错。上半场我 2735G 的图拿了 421.79 分；这次造价压到 ~1500G，g 更高，且新机关更刁钻，应该更好。

再加一个重要杀伤：**ONEWAY 陷阱**——造一个"看似捷径"的通道，进去后单向门让勇者无法返回，且通道尽头是死路（W 围住）→ 一旦走进去就 TIMEOUT。明牌下强求解器会看出，弱求解器不会。这是低造价高收益（ONEWAY 30G/个 + W 墙）。

好，还有一个：**出生 4 回合准入**必须满足。我的图出生点 (2,13) 周围应干净，前 4 拍无激光覆盖出生区。只要激光炮放远（≥10 格）即可。规则要求至少 2 个不同 Turn-1 零伤落点各自有 0 伤序列到 Turn4。我的图 spawn 区开阔，满足。

现在具体设计地图（我会用代码生成 + 本地引擎验证，迭代调整）：

布局：
```
y=0,25 外框 T_W
三道横墙：
  WA: y=5, x=1..38 W, gap x=38 (EMPTY)  [从上到下]
  WB: y=17, x=1..38 W, gap x=1 (EMPTY)
  另外一道? 上半场 4 道 → 229 步。3 道 → 约 170 步。用 3 道：y=5 gap38, y=17 gap1, y=21 gap38? 但 K2 在 y=15..23；y=21 墙会把 K2 区切开。
```
让我算路径长度：spawn (2,13) 位于 y=13（墙 y=5 与 y=17 之间）。K1 在 (14,3)（y<5 区），K2 在 (20,20)（y>17 区），V 在 (36,13)（中间带）。

要拿 K1：从 (2,13) 到 y=5 墙的缺口 x=38 → 需要沿中间带从 x=2 走到 x=38（36 步），上到 y=4（1 步），穿过 y=5 缺口（1 步）到 y=6？不对，y=5 墙缺口在 x=38，穿过后到 y=6 是中间带另一侧？我搞混了。

重新定义：墙 y=5 把地图分成上部（y=1..4）与中部（y=6..16）。缺口 x=38 允许从 y=4 ↔ y=6 通过（在 x=38）。墙 y=17 把中部（y=6..16）与下部（y=18..24）分开，缺口 x=1 允许 y=16 ↔ y=18 通过（x=1）。

spawn (2,13) 在中部。K1 在 (14,3) 上部。要到上部：从 (2,13) → 沿中部走到 x=38（36 步）→ 上到 y=4? 但 y=5 是墙，x=38 是缺口，所以从 (38,6) 上到 (38,5) 再上到 (38,4)（2 步）→ 沿上部走到 x=14（24 步）→ 上到 y=3（1 步）→ K1。然后返回中部：从 (14,3) → 到 x=38（24 步）→ 下到 y=6（2 步）→ 沿中部走到 x=1（37 步）→ 下到 y=18（2 步）→ 到 K2(20,20)（~21 步）→ 返回 (1,18) 或走到 x=38? 再回到中部到 V(36,13)：从下部到中部只能经 x=1 缺口 → 从 (20,20) 走到 (1,18)（~21 步），上到 (1,16)（2 步），沿中部走到 x=36（35 步）→ V。

总步数估算：36+2+24+1 + 24+2 + 37+2 + 21 + 21+2 + 35 ≈ 207 步。超过 200！需要压缩。

优化：把 K1/K2 放在靠近缺口的位置，减少横向往返。或者把墙缺口位置与地标对齐。

改：缺口交替但让目标靠近缺口：
- 墙 y=5 gap x=38；墙 y=17 gap x=1。
- K1 放在 (34,3)（上部靠右，靠近 x=38 缺口）→ 从缺口 (38,4) 到 (34,3) 只要 5 步。
- K2 放在 (6,19)（下部靠左，靠近 x=1 缺口）→ 从 (1,18) 到 (6,19) 6 步。
- V 在 (36,13)（中部靠右）。
路径：spawn(2,13) → x=38 (36 步) → y=4 (2步) → (34,3) K1 (5步) → 回 (38,4) (5步) → y=6 (2步) → x=1 (37步) → y=18 (2步) → (6,19) K2 (6步) → 回 (1,18) (6步) → y=16 (2步) → (36,13) V (35步 + 3 up) ≈ 36+2+5+5+2+37+2+6+6+2+35+3 = 141 步。很好，≤200，留了余量给推箱/等待激光。

K1 (34,3) 合法（12≤x≤34, 2≤y≤10）✓；K2 (6,19)? x 必须 12..34！K2 x∈[12,34], y∈[15,23]。所以 K2 最小 x=12。改 K2=(12,19)，从 (1,18) 到 (12,19) 12 步。总 ~153 步。K1 (34,3) 与 K2 (12,19) 曼哈顿距 = 22+16=38 ≥12 ✓。V (36,13) ✓ (33..37, 4..21)。

推箱锁：V 周围用 W 围，入口 (35,13)=P_GATE。PLATE 放在中部带 (20,10)，BOX 放在 (17,10)，中间 (18,10),(19,10) 是 ICE → 一次 MOVE_R 推箱滑到 (20,10) 压板。但注意：中部带是勇者横向主干道（y=13 附近），PLATE/BOX 在 y=10 不挡主路。author 解需要专门绕去推箱（+ ~10 步）。

不过要小心：如果 BOX 被推到 PLATE 上，plates_active=True，P_GATE 打开，勇者才能进 V。但勇者推箱后要走到 V，箱子留在板上 → P_GATE 保持开。✓

还要注意：`1 <= PLATE <= BOX` 约束：1 PLATE, 1 BOX ✓。

再加激光杀招：在中部带 y=13 主路上放红蓝炮，让直走的勇者挨打。但 author 解也走 y=13 主路（从 x=2 到 x=38，以及最后从 x=1 到 x=36）。若主路被炮覆盖，author 解要绕或计时。为简化，把炮放在 y=12 或 y=14 的平行行，射线沿水平方向覆盖那些行，而 author 走 y=13 安全？不行，横向射线在 y=13 才覆盖主路。

改为：炮沿**纵向**扫，覆盖若干列（x 固定），author 解需在这些列避开（走别的 y 或计时）。例如 LASER_D 在 (20,7) 向下扫 (20,8..17)。这列 x=20 在中部带；author 横向走 y=13 时会经过 (20,13)（在射线内）→ 危险。可以安排 author 在 phase 安全时经过，或绕行（上下移 1 格避开 x=20 列？纵向射线覆盖整列 y=8..17，绕不开，除非走到 y<8 或 y>17，但中部带 y=6..16，y=6,7 不在射线（8..17），可以走 y=7 绕过！）嗯，那 author 可以在经过 x=20 时改走 y=7（在射线起点之上）。但 x=20,y=7 是普通 EMPTY，可以。

这变得复杂。让我采用**更简单的杀伤**：把激光炮放在"诱人的捷径"上，author 完全避开。比如中部带 y=13 是主路；我在 y=11 放一排激光炮横扫，形成"看似更快"的平行通道；贪心勇者可能走那条。但明牌下 solver 会选最短路径，不一定走陷阱。

嗯。也许最有效的：**让 V 前的 P_GATE 走廊被双频激光覆盖，且必须精确计时**（author 解用 WAIT 调相位）。这样所有勇者都必须做相位规划；不做就死。我来实现这个，author 解里加几个 WAIT。

具体：
- 入口走廊：(33,13),(34,13),(35,13)=P_GATE,(36,13)=V。
- 红炮 LASER_L 在 (39,13)? 那是外框 T_W，不能放炮。改 LASER_L 在 (38,13)：向左扫 (37,13),(36,13),...,(28,13)。但 (38,13) 在中部带 x=38 是墙 y=5 的缺口列，y=13 处是 EMPTY，可以放炮。射线覆盖 V(36,13)、P_GATE(35,13)、(34,13),(33,13)... 
- 蓝炮 LASER2_D 在 (34,10)：向下扫 (34,11..20)，覆盖 (34,13)。
- 红炮开火 phase {0,3,6,9}，蓝 {0,4,8}。
- 要通过走廊 (33,13)→(34,13)→(35,13)→(36,13) 共 3 次移动（从 33 出发），每回合的 exposed 包含起点和落点。红炮覆盖所有这些格。所以每个"红开火拍"都会挨 50（只要 exposed 与射线有交集）。红不开火拍：{1,2,4,5,7,8,10,11}，连续最长 2 拍。3 次移动需要 3 个连续安全拍（从进入 (33,13) 那一拍开始算，因为 (33,13) 也在射线内，起点暴露也算）。

嗯，起点 (33,13) 也在红射线内（红从 x=38 向左 10 格 → x=28..37）。所以勇者站在 (33,13) 的任何红开火拍都会挨打。要 0 伤通过，需要在红不开火的连续窗口内完成所有移动，且不能在任何红开火拍停留在射线内。窗口最长 2 拍 → 无法完成 3 步。

解决：用 **JUMP** 跨 2 格减少步数：从 (32,13)（不在射线? x=32 在 28..37 内，也在）… 嗯射线覆盖 x=28..37，很长。

改：让红炮射程只覆盖 V 前 3 格：把炮放在 (37,13)? V 在 (36,13)，P_GATE 在 (35,13)。若 LASER_L 在 (37,13)，向左扫 (36,13),(35,13),(34,13),(33,13),(32,13)... 还是 10 格。

除非用高墙截断射线：在 (33,13) 左边放一个 W 或 T_W？但那样勇者过不去。可以用 ONEWAY 门？ONEWAY 不挡激光。用 BOX 挡？箱子可推走。用 P_GATE 关闭时挡激光（高墙）——但我们需要它开。

**替代方案：用"等待 + 吃一次 50 伤"** 让 author 解接受 50 伤通关。规则没要求 0 伤。但 author 解带伤会让"精确自证通过"仍成立（存活踏上 V）。不过 D 不影响证书。可以。

但更优雅：让走廊只有 **1 格** 在红蓝射线内，且用 WAIT 选安全拍通过。例如：
- 红炮 LASER_R 在 (30,13) 向右扫 (31..40,13)。
- 用 W 墙把 (31,13),(32,13) 封住？那勇者怎么进？
- 把 V 房间入口设计成从上方进入：V 在 (36,13)，入口在 (36,12)（P_GATE 在 (36,12)），勇者从 (36,11) 向下进入。红炮横扫 y=13 只覆盖 y=13 行；勇者在 y=11,12 不受影响，进入 V 那一拍落在 y=13 → 需要红不开火。只需 1 个安全拍！蓝炮纵扫 x=36 列覆盖 (36,11),(36,12),(36,13)? 若蓝炮 LASER2_U 在 (36,20) 向上扫 (36,19..10)，覆盖 (36,11),(36,12),(36,13) → 蓝开火拍也会打。交叉格在 phase 0 双射 -100。

要 0 伤到达 V：选择 phase 使红蓝都不开火 → {1,2,5,7,10,11}，且到达 V 那一拍的 exposed = {(36,12),(36,13)}（或含更多），两格都在红/蓝射线 → 只要该拍红蓝都不开火即可。而之前站在 (36,11),(36,12) 的拍也需要在射线内且红蓝不开火。连续安全拍（红蓝都不开火）：{1,2} (2), {5}(1), {7}(1), {10,11}(2)。所以最多连续 2 拍。若勇者从 (36,11) 开始等，然后 MOVE_D 到 (36,12)（P_GATE），再 MOVE_D 到 V，需要 3 拍连续安全（含起点停留）→ 不行。

除非起点 (36,11) 不在射线内。让蓝炮向上只扫到 y=12：LASER2_U 在 (36,22) 向上扫 (36,21..12)。覆盖 (36,12),(36,13)... 不含 (36,11)。红炮扫 y=13 不含 (36,11),(36,12)。所以：
- (36,11): 完全安全（不在任何射线）。
- (36,12): 蓝射线内。
- (36,13): 红+蓝射线内。
勇者在 (36,11) 等到合适拍，然后 MOVE_D 到 (36,12)（该拍 exposed={(36,11),(36,12)}，(36,12) 在蓝射线 → 该拍必须蓝不开火：phase ∉{0,4,8}），再 MOVE_D 到 V（该拍 exposed={(36,12),(36,13)}，红+蓝都覆盖 → 必须红蓝都不开火：phase ∈{1,2,5,7,10,11}）。
需要连续 2 拍：第一拍蓝不开火，第二拍红蓝不开火。可选：phase 1→2（第一拍 phase1 蓝不开✓，第二拍 phase2 红蓝不开✓）。可行！
所以 author 解在 (36,11) WAIT 到 phase 1，然后 MOVE_D, MOVE_D 到 V，0 伤通关。

这很棒：**必须精确计算 12 拍相位**，否则吃 50/100 伤。同时 V 入口是 P_GATE（需推箱开板）。这就是"逻辑锁"。

但注意：P_GATE 在 (36,12) 若关闭则是高墙，**会阻挡激光射线**（P_GATE 关闭时是 HIGH_WALL）。蓝炮从下方 (36,22) 向上扫，遇 (36,12) 关闭的 P_GATE 会停 → 覆盖不到 (36,13)。当 P_GATE 打开（plates_active True），射线穿过。所以射线状态依赖压板。author 解先推箱开板，再走相位。合理。

不过为简化，我把 P_GATE 放在 (35,12)（房间左侧入口），V 房间结构再设计。让我不要过度复杂化，先做一个能验证的版本，然后迭代。

**决定：先用较简单的地图，确保合法 + 自证 + 有推箱 + 有双频激光 + ONEWAY 陷阱，再用本地引擎验证并调整。** 迭代比空想快。

地图生成代码结构（build_dungeon）：
1. 初始化全 EMPTY + 外框 T_W。
2. 放两道横墙 y=5 (gap 38), y=17 (gap 1)，W。
3. 放 K1(34,3), K2(12,19), V(36,13)。
4. V 房间：用 W 围住 V 的三面，(35,13)=P_GATE 入口，(36,12),(36,14),(37,13) 设 W，(35,12),(35,14) W。这样只能从 (34,13) 向右进入 (35,13) P_GATE 再到 (36,13) V。
   但 P_GATE 关闭时是高墙，还挡激光。
5. PLATE (20,10)，BOX (17,10)，ICE (18,10),(19,10)。勇者从 (16,10) MOVE_R 推箱：箱子 (17,10)→(18,10) ICE→(19,10) ICE→(20,10) PLATE（普通地面停）。✓ 但注意：MOVE_R 推箱时，箱子 chain 从 p1=(17,10) 到 p2=(18,10)，之后 ICE 继续滑到 (20,10)。然后勇者跟进到 p1=(17,10)（因为箱子已离开），再普通地面 → 停在 (17,10)（不是 ICE）。嗯，勇者 chain("hero",(16,10),(17,10),R)，terrain (17,10) 是 EMPTY（箱子去哪了？箱子初始在 occupant 层，terrain 是 EMPTY）→ 停。✓ plates_active 变 True。
   注意：PLATE 是地形层，勇者可以站上去但不触发（仅 BOX）。✓
6. 双频激光：
   - 红 LASER_L 在 (38,13)：向左扫 (37,13),(36,13),... 但 (37,13) 我设为 W（V 房间右墙）→ 射线立刻被 W 挡住，覆盖不到 V。改：V 房间右墙 (37,13) 用 W 会挡。那把红炮放在 (34,13) 向右扫？那 (34,13) 是勇者来路，炮座本身是高墙会挡路。
   - 换方案：红炮放在 (36,10) 向下扫 (36,11..19)，覆盖 (36,12),(36,13) 等（但 (36,12) 是 W 房间上墙 → 挡住）。
   
   嗯，V 房间用 W 围会挡激光。改用 **T_W?** 也挡。那就不围房间，只用 ONEWAY 和 P_GATE 控制：
   - V 在 (36,13)。
   - (35,13)=P_GATE（唯一入口，左边是开阔带）。
   - (37,13)=T_W? 但 V x≤37，V 在 36，右边 37 可以是 T_W 挡住从右侧进入；不过 x=38 还有路，可以从 (36,12)/(36,14) 上下进入 V。要封住上下：(36,12)=W, (36,14)=W。这些 W 会挡纵向激光但横向激光可穿过 (36,13)。
   - 红炮 LASER_L 在 (38,13)：向左扫 (37,13),(36,13),(35,13),(34,13)... 若 (37,13)=T_W 会挡。所以 (37,13) 设为 EMPTY，但勇者可以从 (37,13) 到 V 绕过 P_GATE！需要用其他方式封：把 (37,13) 设为 **ONEWAY_L**（只能向左进入 → 从 (38,13) 向左进入 (37,13) 可以，然后从 (37,13) 向左进入 V(36,13) 也可以，绕过 P_GATE）。不行。
   - 用 P_GATE 两个：在 (35,13) 和 (37,13) 都放 P_GATE，这样两边都需开板。但 P_GATE 关闭时是高墙，会挡红炮射线（从 x=38 向左第一格就是 (37,13) P_GATE 关闭 → 挡）。不过当 plates_active=True 时两者都开，射线穿过 → V 被覆盖。✓ 这可行！而且增加了"必须开板"的确定性。
   - 上下面：(36,12),(36,14) 设 W（挡纵向进入）。
   - 红炮 LASER_L 在 (38,13)：向左扫 (37,13)P_GATE(开),(36,13)V,(35,13)P_GATE(开),(34,13)... 共 10 格到 x=28。
   - 蓝炮 LASER2_U 在 (34,20)? 向上扫 (34,19..10)，覆盖 (34,13)（红蓝交叉在 (34,13)，phase 0 双射）。或 LASER2_D 在 (34,6) 向下扫 (34,7..16)，覆盖 (34,13)。
   
   这样从左侧 (34,13) 往 V 走的最后 3 格 (34,13),(35,13),(36,13) 都在红射线内；(34,13) 还在蓝射线内。要 0 伤通过需要连续 3 拍红不开火 → 不可能（最长 2 连续）。用 JUMP 从 (33,13) 跳到 (35,13)：exposed={(33,13),(35,13)}，若 (35,13) 在红射线 → 该拍需红不开火；再 MOVE_R 到 V 需下一拍红不开火 → 2 连续安全拍可行（phase 1,2）。但 JUMP 中间格 (34,13) 不暴露（上半场引擎 chain 从 p0 直接到 p2，exposed 只加落点）。规则里 JUMP 说"中间飞越格 p1 与落点格 p2 若均不阻挡"，但 exposed 是否包含 p1？规则 v2.1 "每回合开始时 exposed_cells = {(hx,hy)}；勇者每进入一格（含位移终点）加入"，JUMP 是"腾空飞越"，可能只算落点。上半场引擎只加落点。我按"只加落点"处理（与官方引擎一致的可能性大，因为 golden vector 里 JUMP_R 阵亡记录是"经SPRING_R@(7,13) -> PIT"，没提中间格）。
   
   但这依赖引擎细节，风险高。更稳妥：让 author 解**接受 50 伤**（吃一次红炮），只要 HP>0 通关。author 只需存活。这样自证稳。而对手若吃 100（phase 0 双射）就死。
   
   嗯，但是"精确自证通过"要求恰好最后一步存活踏上 V；吃 50 伤 HP=50 仍存活 ✓。

   不过，如果 author 解吃伤，实战中对手也可能吃伤通关 → 魔王分 1.7*D + 150*(T-1)/239，D 越大越好。有伤反而有利。

   我决定：让 author 解**完全避开所有射线**，通过设计一条不经过射线的进入路线。例如：V 从上方进入，而红炮只扫 y=13 行；蓝炮扫某列但避开上方进入格。设 (36,12)=P_GATE（不是 W），(35,13),(37,13),(36,14)=T_W/W，(36,11) 是来路。红炮扫 y=13 不覆盖 (36,12),(36,11)。蓝炮 LASER2_U 在 (36,22) 向上扫 (36,21..12)，覆盖 (36,12) 和 (36,13)? (36,13)=V 在 (36,12) 之上，射线从下往上遇到 (36,12) P_GATE 关闭会停；打开则继续到 (36,13) V、(36,11)... 实际上蓝炮向上 10 格：y=21,20,...,12。只到 y=12，不到 y=13。所以 V 不在蓝射线内。
   - 红炮 LASER_L 在 (38,13) 向左扫 y=13 行，但 (37,13)=W 会挡住 → 射线覆盖不到 (36,13)。嗯，那 V 就完全没激光覆盖，太安全。
   - 把红炮放在 (34,13) 向右扫？(34,13) 是炮座（高墙），左边来路被挡。

   算了，让 V 房间右侧不封：把 (37,13) 设为 **P_GATE**，红炮 LASER_L 在 (38,13) 向左扫，板开时射线穿过 (37,13)→(36,13) V→(35,13)... 若 (35,13) 也是 P_GATE 或 W。若 (35,13)=W 则射线在 x=35 停，但 V(36,13) 已被覆盖 ✓。(36,12)=P_GATE（入口），(36,14)=W。这样：
   - 进入 V 只能从 (36,12) 向下（P_GATE 开时）。
   - (36,12) 在蓝射线内（若蓝炮向上扫到 y=12）。
   - V(36,13) 在红射线内。
   - 到达 V 那一拍：exposed={(36,12),(36,13)}，红射线含 (36,13) → 该拍红不开火；蓝射线含 (36,12) → 该拍蓝不开火。所以到达拍必须是 {1,2,5,7,10,11} 之一。
   - 前一拍从 (36,11) 到 (36,12)：exposed={(36,11),(36,12)}，蓝射线含 (36,12) → 该拍蓝不开火。
   - (36,11) 不在任何射线，可以随意等待。
   - 需要连续 2 拍：蓝不开 → 红蓝不开。phase 1(蓝不开)→2(红蓝不开) ✓，或 10→11 ✓。
   - 所以 author 解：在 (36,11) 等到 phase 1（或 10），MOVE_D 到 (36,12)，MOVE_D 到 V，0 伤通关。
   
   很好！这实现了"必须精确 12 拍规划"，且 0 伤可行。

   但 (36,12)=P_GATE 与 (37,13)=P_GATE 两块板门，PLATE 只有 1 个，plates_active 时两者同开 ✓。P_GATE 上限 8 ✓。

   还要注意：红炮 (38,13) 向左扫时，(37,13)=P_GATE 打开后不是高墙 → 射线穿过；(36,13)=V（不是高墙）→ 穿过；(35,13)=W → 停。所以红射线 = {(37,13),(36,13)}（若 37 开）。等等，射线从炮 (38,13) 向左 k=1 →(37,13) P_GATE 开 → 加入；k=2 →(36,13) V → 加入；k=3 →(35,13) W → 停。所以红射线只有 2 格。好，更容易避开（但 V 在其中，必须计时）。

   蓝炮 LASER2_U 在 (36,22)：向上 k=1..10 → y=21..12。途经 (36,14)=W？我设 (36,14)=W → 射线在 k=8 (y=14) 被 W 挡住，覆盖不到 (36,12)。所以 (36,14) 不能是 W。改成 (36,14)=P_GATE? 那也是高墙（关闭时）/开时通畅。若开，射线穿过 (36,14) 到 (36,13)=V、(36,12)=P_GATE 等。嗯。
   
   要不把蓝炮放在 (36,24) 向上扫 y=23..14（10 格），覆盖不到 12。不行。
   
   简化：把蓝炮放在 (33,20) 向上扫 (33,19..10)，覆盖 (33,13) 列。红炮 LASER_R 在 (30,13) 向右扫 (31..40,13)。交叉格 (33,13) 在 phase 0 双射。V 房间入口在 (35,13)（P_GATE），勇者从 (34,13) 向右进入。红炮从 x=30 向右扫会覆盖 (31..39,13)，包括 (35,13),(36,13) V。但 (35,13)=P_GATE 关闭时挡射线；打开时穿过。
   
   唉，太绕。让我**降低复杂度**：不追求"V 在射线内"，而是让**通往 V 的必经窄道**被双频激光覆盖，需要计时通过；V 本身安全。这样 author 解在窄道前 WAIT 到安全拍，快速通过，到 V 安全。

设计窄道：
- 中部带 y=13 主路，从 x=1 到 x=34。
- 在 x=30..34 之间造一条 1 格宽走廊（y=13），上下用 W 封（y=12 和 y=14 在 x=28..34 放 W）。
- 红炮 LASER_R 在 (28,13)? 炮座是高墙，不能放在走廊里。放在 (28,12) 不行（方向 R 沿 y=12）。
- 用 **纵向炮** 覆盖走廊的某几列：红 LASER_D 在 (31,11) 向下扫 (31,12..21)；但 (31,12)=W 会挡。改：走廊上下封墙用 W 只封 x=28..30，让 x=31 列的 y=12 是 EMPTY 供炮射线通过？炮座 (31,11) 在高处，射线向下穿过 (31,12),(31,13),(31,14)... 若 (31,12) 不放 W，勇者可以从 y=12 绕进走廊。可以接受（多一条路），只要所有路都经过被激光覆盖的格。

我觉得我在过度设计。让我采取**务实方案**：

**地图 = 3 道蛇形墙 + 推箱 P_GATE 锁 + 几条双频激光射线覆盖主路的若干格 + ONEWAY 死胡同陷阱**。author 解用本地引擎的 A* 自动求出（≤200 步、0 伤优先），而不是手工设计路径！这才是最高效的方法：**用我写的通用求解器在 build_dungeon 里（离线）跑一遍，把得到的动作序列作为 author_solution**。但 build_dungeon 在评测时也有 2s 限制，不能跑重搜索。所以我在本地离线生成 author_solution，然后把它作为常量列表写进 submission.py（或用一个确定性算法在 build_dungeon 内快速重算）。

更好：build_dungeon 里用**简化的确定性 BFS**（不含相位）生成一条安全路径，再手工插入必要的 WAIT 与推箱动作，并用本地引擎验证；最后把验证过的序列写成常量。但序列 ~150 步，写成常量列表会占空间但没问题（可以用字符串编码压缩，如 "R"*n 之类的 RLE）。

或者：build_dungeon 内用确定性算法生成路径（BFS 绕开静态射线 + 推箱 + WAIT），保证 ≤200 步且可复现，然后用本地引擎验证。我倾向于**在 build_dungeon 内实现一个专门的"自证路径生成器"**（比通用求解器简单，因为知道地图结构），返回一个动作列表。这样代码自洽、可复现、且不依赖硬编码长序列。

嗯，但这仍需要 map 与 solver 耦合。可行：我设计地图时让路径结构清晰（蛇形 + 推箱 + 相位 WAIT），然后写一个 `_author_path()` 用 BFS 在"静态安全图"上找路径（避开静态射线格与 PIT），拼接：spawn→PLATE 推箱点→K1→K2→V，并在进入激光区前插入 WAIT 调整相位。最后用本地引擎验证。

OK，时间不早了（我作为 AI 有大量 token 但要高效）。让我**先写引擎与求解器**，再写地图，边写边测。

先写 `submission.py` 的 Sim 部分。我会一次性写一个较完整的文件，然后调试。

实际上，考虑到复杂度，我把 Sim 单独写成 `v22_engine.py`（测试工具，放考场文件夹），submission.py 里 `from v22_engine import ...`？不行，评测机只保证 submission.py 可用，不能 import 同目录其他文件（可能可以，但风险高，且"单文件交付"）。所以 Sim 必须在 submission.py 内。

那我就把 Sim 写在 submission.py 里，测试脚本 import submission 使用它。文件会很长（~900-1100 行），但没问题。

让我组织并写出。为了 manageable，我分两步：
1. write_to_file 写 submission.py 第一部分：常量、validate、Sim 类、辅助函数、decide_action（求解器）、build_dungeon。一次写完（我会尽量正确）。
2. 写测试脚本。

我先写 Sim。仔细写。

```python
"""
v2.2 FULL ... 
"""
import heapq
import collections
import time

W, H = 40, 26
INF = 1e18
DIRS = {"U": (0,-1), "D": (0,1), "L": (-1,0), "R": (1,0)}
VEC2DIR = {(0,-1):"U",(0,1):"D",(-1,0):"L",(1,0):"R"}
NEI4 = ((0,-1),(0,1),(-1,0),(1,0))
VALID_ACTIONS = (...)
MIRROR_MAP = {...}
HIGH_BASE = {"W","T_W","LASER_U","LASER_D","LASER_L","LASER_R",
             "LASER2_U","LASER2_D","LASER2_L","LASER2_R"}
TILE_COSTS = {...}
CAPS = {...}
IMMUTABLE_EXPLOSION = {"T_W","K1","K2","V","PIT","PORTAL_1A","PORTAL_1B","PORTAL_2A","PORTAL_2B","PLATE","P_GATE","ONEWAY_U","ONEWAY_D","ONEWAY_L","ONEWAY_R"}
```

Sim:
```python
class _Sim:
    def __init__(self, grid=None, state=None, start_turn=1):
        if state is not None:
            self._from_state(state)
        else:
            self._from_grid(grid)
        self.turn = start_turn if state is None else int(state.get("turn",1))
        ...
```
为简洁，我让 `_from_grid` 与 `_from_state` 都填充：
- `self.bt`: base terrain 2D list of str（BOX/TNT 解码为 EMPTY；CHEST→MIMIC/HEAL 判定）
- `self.dt`: dict overrides（初始为空；游戏过程中 CRACK→PIT、K→EMPTY、MIMIC→EMPTY、炸毁 W→EMPTY 等）
- `self.bo`: dict (x,y)->"BOX"/"TNT"（初始占用层）
- `self.do`: dict overrides for occupant（初始为空，用 .get((x,y), self.bo.get(...))）
- `self.plates`: list of PLATE positions（从 bt 扫描；PLATE 免疫，不会被炸，所以固定）
- `self.cannons`: list of (x,y,dir,period)（从 bt 扫描；可能被炸毁 → 通过 tile 检查）
- `self.portals`: dict
- `self.targets`: dict K1/K2/V
- `self.clue_of`: dict for MIMIC clue clearing（用于 clues 显示；模拟中 MIMIC 消失时清 clue，可简化忽略）
- `self.hero`: dict or tuple. 用 dict 便于修改，但 snapshot 要复制。用 tuple: (x,y,hp,keys_mask,jumps,throws,bombs_left)。
- `self.flipped`: bool
- `self.bombs`: tuple of (x,y,timer)
- `self.status`: "PLAYING"/"CLEARED"/"DEAD"
- `self.exposed`: set（每回合重置）
- `self.tnt_armed`: set（每回合重置）
- `self.trap_damage`: float（累计，用于测试计分；A* 里不需要但无害）
- `self.mode = "FULL"`

方法：
```
def tile(self, x, y): 
    if not (0<=x<W and 0<=y<H): return "T_W"  # 外框高墙
    return self.dt.get((x,y), self.bt[y][x])
def occ(self,x,y): return self.do.get((x,y), self.bo.get((x,y)))
def set_tile(self,x,y,t): self.dt[(x,y)] = t
def set_occ(self,x,y,v): self.do[(x,y)] = v
def plates_active(self): return bool(self.plates) and all(self.occ(px,py)=="BOX" for ...)
def high(self,x,y,terr=None,flip=None,plates=None):
    t = self.tile(x,y) ...
def blocks_oneway(self,x,y,d):
    t=self.tile(x,y); return t.startswith("ONEWAY_") and DIRS[t[-1]] != d
def passable(self,p,kind,d):
    x,y=p
    if not (0<=x<W and 0<=y<H): return False
    if self.high(x,y): return False
    o=self.occ(x,y)
    if o in ("BOX","TNT"): return False
    if self.blocks_oneway(x,y,d): return False
    if kind=="BOX":
        if (x,y)==(self.hx,self.hy): return False
        if self.tile(x,y) in ("K1","K2","V","PIT"): return False   # PIT handled separately
    return True
```
注意 PIT 对 BOX：BOX 进入 PIT 会填坑变 EMPTY（chain 里处理），所以 passable 不能因 PIT 拒绝 BOX。上半场引擎 passable 只检查 high/occ/K1K2V，PIT 允许。保持。

`chain(kind, p0, p1, d, steps=0, portals=0, suppress=False)`：与旧引擎相同，但 passable 增加 oneway 检查；SPRING 逐格检测时用 sdir 检查 oneway；PORTAL 的 suppress 前进也要检查 oneway。

具体修改点：
- `self.passable(nxt, kind, d)`（d 是当前方向；镜面折转后 d 更新）。
- SPRING 的 `blocked` 计算里加 `self.blocks_oneway(pk[0],pk[1],d)`。
- MOVE 动作前置：`p1` 检查 `self.high(*p1)` 与 occ TNT，另外若 occ[p1]=="BOX" 且 blocks_oneway(p1,d) → 整次拒绝。

规则 1："前置先验 (x1,y1)（若该格上停着一个 BOX，逆向推动会直接整次拒绝，箱子绝不移动且脚下 CRACK 不坍塌）"。这里指 p1 是 ONEWAY 逆向时整次拒绝（即使没有 BOX？措辞是"若该格上停着一个 BOX，逆向推动会直接整次拒绝"，可能特指推箱情况）。我实现：若 blocks_oneway(p1,d) → 整次拒绝（对所有 MOVE），这更严格且符合"勇者仅可顺箭头方向进入"。GV22_04(a): BOX 停在 ONEWAY_L(6,13)，勇者站 CRACK(5,13) 执行 MOVE_R（方向 R，ONEWAY_L 要求 L）→ 整次拒绝，BOX 未动且 CRACK 不坍塌。✓ 若 p1 是 ONEWAY 逆向且没有 BOX，也应拒绝进入（不能逆向进入 ONEWAY 格）。✓

- JUMP：`not self.high(*p1) and not self.high(*p2)` 且 `not blocks_oneway(p1, d)` 且 `not blocks_oneway(p2,d)`，occ p2 不是 BOX/TNT。
- THROW：空中 6 格忽略 oneway；其他 high/BOX/TNT/SWITCH/MIMIC/MIRROR/PORTAL 逻辑保持；地面滑行遇 ONEWAY → return。

`rays(period_filter, terr_snapshot=None)`：
```
out=[]; tnt=set()
for (x,y,dr,per) in self.cannons:
    if period_filter and per not in period_filter: continue
    t = self.tile(x,y)
    if t not in ("LASER_"+dr, "LASER2_"+dr): continue  # 被炸毁
    dx,dy=DIRS[dr]
    cells=[]
    for k in 1..10:
        cx,cy=x+k*dx,y+k*dy
        if not in bounds: break
        if self.high(cx,cy): break    # 含关闭 P_GATE/R_GATE
        o=self.occ(cx,cy)
        if o=="BOX": break
        if o=="TNT": tnt.add((cx,cy)); break
        cells.append((cx,cy))
    out.append(((x,y),dr,per,cells))
return out,tnt
```
注意 `self.high` 用当前 plates_active（实时）。规则说 phase D 基于阶段 C 结束后的同一快照；我在 step 的 D 阶段直接调用（此时状态已是 C 后），OK。

`phase_d`:
```
periods=set()
if self.turn%3==0: periods.add(3)
if self.turn%4==0: periods.add(4)
if not periods: return
rl,tnt = self.rays(periods)
m=0
for (c,dr,per,cells) in rl:
    if any(c in self.exposed for c in cells): m+=1
if m: self.hurt(50*m)
if tnt: self.explode([(x,y,"TNT") for ...])
```
注意 12k 时红蓝同帧，每门分别计 50（不同炮座）。✓ GV22_03.

`explode(sources)`: 与旧引擎类似，但 immutable 增加 PLATE/P_GATE/ONEWAY_*，且 TNT  occupant 清除，BOX 清除，CRACK→PIT，其他→EMPTY（含 LASER2 炮座被炸）。伤害 TNT 60 / BOMB 50 每 source 3x3 覆盖。连锁 BOMB。注意爆炸后 plates_active 重算（GV22_07：阶段 C 炸毁箱子后 P_GATE 立即关闭，挡住同回合阶段 D 的激光）。我的 high() 实时计算 plates_active ✓。

`hurt(amount, trap=True)`: hp -= amount; trap_damage += min(max(hp_before,0), amount) * (trap ratio). 简化：
```
def hurt(self, amount, trap_ratio=1.0):
    before = max(0,self.hp)
    self.hp -= amount
    self.trap_damage += min(before, amount) * trap_ratio
    if self.hp<=0: self.status="DEAD"
```
爆炸伤害里 TNT 部分算 trap，BOMB 部分不算（a=0 → ratio 0 处理）。上半场引擎有 a,b 区分。我保留简化：`explode` 里计算 tnt_damage 与 bomb_damage，调用两次 hurt。

`step(act)`:
```
if self.status!="PLAYING": return
hx,hy = self.hx,self.hy
self.exposed={(hx,hy)}
self.tnt_armed=set()
if act=="BOMB": ...
elif MOVE_: ...
elif JUMP_: ...
elif THROW_: ...
# V 立即通关已由 chain 设置 status=CLEARED
if self.status=="PLAYING": self.phase_c()
if self.status=="PLAYING": self.phase_d()
if self.status=="CLEARED": self.win_turn=self.turn
elif self.status=="PLAYING" and self.turn>=240: self.status="TIMEOUT"
self.turn+=1
```
注意 GV22_08: V instant win before phase D，且 turn=240 时仍 CLEARED（不是 TIMEOUT）→ 我的顺序 CLEARED 优先 ✓。

`_from_state(state)`:
- terrain rows: state["terrain"]（list of list of str）。CHEST 判定：clues 全图；对每个 CHEST 格，若其四邻存在 clues True → MIMIC 否则 HEAL。注意 clues 可能是 list of list of bool。
- occupant: state["occupant"]（list of list of None/"BOX"/"TNT"）。
- bombs: state["bombs"] list of dict。
- hero: state["hero"]。
- flipped: state["gates_flipped"]。
- turn: state["turn"]。
- targets: state["targets"]（可能 terrain 中 K1/K2/V 已被拾取变 EMPTY，所以 targets 更可靠）。
- plates/cannons/portals 从 terrain 扫描（PLATE/ONEWAY 免疫不会被炸，炮座可能被炸 → tile 会变 EMPTY，用 tile 检查）。

`state()`：为测试输出 state dict（全图明牌），包含 laser_warnings（带 period/cannon）、plates_active、clues（简化：MIMIC 的四邻 clue）。用于本地测试中把 Sim 状态喂给 decide_action。

`clone()`: 复制 dt/do/bombs/hero/flipped/turn/status/trap_damage 等（bt/bo/plates/cannons/portals/targets 共享不可变）。供 A* 扩展。
```
def clone(self):
    s = _Sim.__new__(_Sim)
    s.bt=self.bt; s.bo=self.bo; ... (共享)
    s.dt=dict(self.dt); s.do=dict(self.do); s.bombs=list(self.bombs)
    s.hero=self.hero (tuple, immutable)
    s.flipped=self.flipped; s.turn=self.turn; s.status=self.status
    s.exposed=set(); s.tnt_armed=set(); s.trap_damage=self.trap_damage
    s.win_turn=self.win_turn
    return s
```
hero 用 tuple (x,y,hp,keys_mask,jumps,throws,bombs_left)，修改时整体替换。为方便，我用属性 hx/hy/hp 派生自 tuple？不如用 dict 并在 clone 时 copy。dict copy 成本低。用 `self.h = {...}`，clone 时 `dict(self.h)`。

`key()`：A* 状态键 = (hx,hy,hp,keys,flipped,turn%12, tuple(sorted(dt.items())), tuple(sorted(do.items())), tuple(sorted(bombs)), jumps,throws,bombs_left)。注意 dt 可能增长（CRACK 变 PIT 等），但通常小。turn%12 用于相位；但 turn 绝对值影响 laser 吗？只 mod 12 即可（3 和 4 的最小公倍数 12）✓。炸弹 timer 也计入 bombs。

好。现在求解器。

**A\***：
```
def _solve(state, deadline, max_nodes):
    root = _Sim(state=state)
    # 预计算静态几何距离（用于启发式）：从目标反向 BFS，考虑静态可通行（不含激光/相位），方向性 oneway
    # 直接用曼哈顿距离 + 未拿钥匙估计（弱但可采纳）
    h(node) = manhattan(pos, next_target) + ...
```
启发式必须可采纳（不超过真实代价）。用曼哈顿距离（每步最多移动 1 格，但 JUMP/ICE/SPRING 可移动多格 → 曼哈顿可能高估！）。若用 JUMP 一步 2 格，真实代价 1 < 曼哈顿 2 → 启发式高估 → A* 可能非最优但仍有解（不会漏解，只是可能不是最短）。可接受（我们只要能通关，不必最短）。但为了避免高估导致找不到低代价解，用 `manhattan/2`? 嗯。用 `0.5*manhattan` 更保守。或者用 A* 加权（weighted A*，f = g + 1.5*h）加快搜索。

我用 weighted A*：`f = g + 1.2*h`，h = 曼哈顿到下一个目标 + 剩余目标间曼哈顿（下界估计）。并加 `damage*cost`。

代价函数 `g`：每步 1 + 0.02*damage? 为了强烈偏好 0 伤，用 `g += 1 + damage*0.5`（damage 50 → +25）。这样宁愿多走几步也不吃伤。但 WAIT 也要 cost 1。

目标：`status=="CLEARED"`（V 且 keys 齐）。

状态键里包含 hp，所以吃伤与不吃伤是不同状态；OK。

节点扩展：14 个动作，但为避免爆炸，我们可限制 BOMB（只在必要时）与 THROW（只在有 SWITCH 且需要 flip 时）。先全开，测性能。

每个动作：clone root state → step(act) → 得到新状态。计算 g/h，push。记录 parent 与 action 用于回溯。

时间检查：每 64 节点检查 `time.monotonic() > deadline`。

若无解（超时/节点上限），回退到 `_greedy`：
- 用静态 BFS 到最近目标，避开当前回合危险格（用 laser_warnings 或自算 rays），避免 PIT/MIMIC，返回第一步动作。
- 若完全无路，返回 "WAIT"。

**计划缓存**：
```
def decide_action(state, memory):
    deadline = start + (1.55 if state.turn==1 else 0.42)
    sig = (turn, hx,hy,hp,keys,flipped,plates_active, jumps,throws,bombs_left, tuple(sorted(bombs)))
    plan = memory.get("plan")
    if plan and memory.get("plan_idx")<len(plan) and memory.get("expected_sig")==sig:
        act = plan[idx]; memory["plan_idx"]=idx+1
        # 计算执行后的预期 sig 并存入 expected_sig（用 Sim 模拟一步）
        ...
        return act
    else:
        plan = _solve(state, deadline, ...)
        memory["plan"]=plan; memory["plan_idx"]=0...
```
更简单的做法：**每回合都用 Sim 从当前 state 重建，并从 memory 里取 plan 的剩余动作序列，先验证"plan 第一个动作执行后的状态"是否与上次预期一致**。太复杂。

最简单稳妥：**每回合都重新规划**，但只在 Turn 1 做完整搜索；Turn>1 若上次的 plan 仍有效（通过比对 state 与 plan 的预期序列）就直接取。实现：
- Turn1 求解得到 plan = [a1,...,an]，同时记录 `expected_states = [sig0, sig1, ..., sig_n]`，其中 sig_i 是执行完 a_i 后的状态签名。生成方式：从当前 Sim 克隆，逐步执行 plan 并记录 sig。
- Turn t：检查 `memory["expected"][idx] == current_sig`。若相等 → 返回 plan[idx]（第 idx+1 个动作），idx+=1。若不等 → 重新规划。

这样只需 O(1) 每回合。sig 用 Sim 的状态键（含 turn%12 等）。

不过 `state` 里有些字段（clues、terrain）可能变化（K 拾取变 EMPTY、CRACK 坍塌），这些都在 Sim 的 dt/do 里，sig 已包含 dt/do 的排序项。但 sim 从 state 重建时，dt 是空的（把当前 terrain 作为 bt），而 plan 执行中 dt 会记录变化 → sig 不一致。解决：sig 只含**最小必要字段**：(turn%12, hx,hy,hp,keys_mask,flipped, plates_active, bombs_left/jumps/throws, 在场炸弹, 以及"关键地形变化"如已拾取的 K、已坍塌的 CRACK)。太麻烦。

**替代更简单方案：不缓存完整 plan，每回合重新规划**，但用"增量/轻量"搜索。Turn>1 只有 0.5s，重新跑 A* 可能超时。不过 A* 每次从当前状态出发，通常比 Turn1 快（离目标更近）。若 Turn1 能在 1.5s 内解出，Turn>1 大概率也能在 0.4s 内。但风险是每回合都花 0.4s，总计没问题（单回合限制）。

其实**每回合重新规划是最稳健的**（自动纠错，无需状态同步）。性能：A* 节点数 ~几万，每节点 14 次 clone + step。每次 step 涉及 rays（仅激光拍）。估计每节点 ~0.5ms → 1.5s 约 3000 节点。可能不够解复杂图。

优化：Turn1 做完整搜索并缓存 plan；Turn>1 用"校验 + 取下一动作"；只在校验失败时重规划。校验用**轻量签名**：从 state 提取 (turn, hx, hy, hp, keys, flipped, plates_active, jumps, throws, bombs_left, 在场炸弹数, K1/K2 是否还在 terrain, 当前 laser_warnings 数量)。Turn1 时用 Sim 逐步执行 plan 并记录这些签名。这样 sig 可从真实 state 计算，也可从 Sim 计算，一致。

实现 `_sig(state)` 和 `_sig_sim(sim)`：
```
def _sig_from_state(state):
    h=state["hero"]
    return (int(state["turn"]), h["x"],h["y"],h["hp"], tuple(h["keys"]), bool(state["gates_flipped"]), bool(state["plates_active"]), h["jumps"],h["throws"],h["bombs"], len(state["bombs"]), 
            tuple(sorted((x,y) for y,row in enumerate(state["terrain"]) for x,t in enumerate(row) if t in ("K1","K2","V"))))  # 太慢
```
简化：只比较 (turn, pos, hp, keys, flipped, plates_active)。这些足以检测大多数偏离。加 jumps/throws/bombs_left。

`_sig_sim(sim)` 需要从 sim 构造 plates_active 等；可以直接调用 `sim.state()` 然后 `_sig_from_state`。但 sim.state() 生成 26x40 矩阵，较慢；Turn1 记录 n~150 个签名 → 150 次 state() 生成 ~4M 字符串操作，可能 0.2s，可接受但浪费。我可以写 `_sig_sim` 直接读 sim 字段。

好，实现 `_sig(sim_or_state)` 两个版本返回同样 tuple。

计划：
```
def decide_action(state, memory):
    start=time.monotonic()
    budget = 1.55 if turn==1 else 0.42
    sig = _sig_state(state)
    plan = memory.get("plan"); idx = memory.get("idx",0); sigs = memory.get("sigs")
    if plan and idx < len(plan) and sigs and sigs[idx] == sig:
        memory["idx"] = idx+1
        return plan[idx]
    # 重规划
    plan, sigs = _solve(state, start+budget, ...)
    memory["plan"]=plan; memory["sigs"]=sigs; memory["idx"]=1
    return plan[0] if plan else "WAIT"
```
其中 sigs[i] 是"执行 plan[i] 之前的状态签名"，sigs[0] = 当前 state 签名；sigs[i+1] = 执行 plan[i] 后的签名。生成：从 Sim(state) 开始，sig0=_sig_sim(sim)，对每个 action：sim.step(a); sig_{i+1}=_sig_sim(sim)。注意 sim.step 会推进 turn；状态可能被 CLEARED 终止。若最后 CLEARED，OK。

若 plan 为空 → 用贪心动作，并让 plan=[greedy_action]，sigs=[sig0]。

重规划失败（超时）时也要给一个安全动作：用贪心。

**贪心动作** `_greedy(state, sim)`：
- 计算当前回合危险格（laser_warnings 的格 + 自算 rays for current turn periods）。
- 目标：最近的未拿钥匙 / V。
- 用 BFS（静态，考虑 high/PIT/oneway）到目标，取第一步；若第一步危险（在危险格且该拍开火），改为 WAIT。
- 避免 PIT、MIMIC（clues 可辨）、TNT occupant。

好，开始写代码。我会写得紧凑但清晰。先写 submission.py 第一版（含 Sim、validate、solver、build_dungeon 初步），然后测试迭代。

由于文件很长，我分块用 write_to_file 写一次（完整内容）。让我认真写。

关于 build_dungeon 的地图，我先给一个具体实现，然后用测试脚本验证并迭代。

地图 v1（我先定）：
```
外框 T_W
墙 A: y=5, x=1..38 = W, gap x=38
墙 B: y=17, x=1..38 = W, gap x=1
K1=(34,3), K2=(12,19), V=(36,13)
V 房间:
  (35,13) = P_GATE   (左入口)
  (37,13) = P_GATE   (右，防绕)
  (36,12) = P_GATE   (上入口)
  (36,14) = W        (下封)
  V(36,13)
  (35,12),(35,14),(37,12),(37,14) = W  (防止从旁边绕到 (36,12) 以外... 其实 (36,12) 已是 P_GATE)
```
嗯，3 个 P_GATE 有点多（3*30=90G，OK）。但要保证勇者不能从 (37,13) 右侧绕到 V：(37,13)=P_GATE 开着时可以从 (38,13)→(37,13)→(36,13) 直接进 V，绕过 (36,12) 的上方入口。那激光相位约束就不适用了（V 仍在红射线内）。可以接受（多一条路）。

其实我不需要 V 房间这么复杂。**简化**：V(36,13)，四周用 W 围三面，只留左边 (35,13)=P_GATE。即：
- (36,12)=W, (36,14)=W, (37,13)=W, (35,12)=EMPTY, (35,14)=EMPTY, (37,12)/(37,14) 随意。
- 勇者只能从 (34,13)→(35,13)P_GATE→(36,13)V。
- 红炮 LASER_L 放在 (38,13)：向左扫，(37,13)=W 立刻挡 → 射线只有 0 格，V 不受激光。不好。

把红炮放在 (34,13)? 那炮座是高墙，挡住来路。除非放在 (34,12) 方向 L/R 沿 y=12 扫，不覆盖 y=13。

**换：用纵向红炮覆盖 (35,13)**：LASER_D 在 (35,9) 向下扫 (35,10..19)，覆盖 (35,13)=P_GATE（关闭时是 high → 挡；打开时射线穿过到 (35,14)...）。V(36,13) 不在该列。
蓝炮 LASER2_R 在 (30,13) 向右扫 (31..39,13)，覆盖 (35,13),(36,13) V。但 (37,13)=W 会挡在 x=37，射线到 x=36 V 包含 ✓。
所以：
- 红炮 (35,9) LASER_D 纵扫 x=35 列 y=10..19，经过 (35,13)（P_GATE 开时）。
- 蓝炮 (30,13) LASER2_R 横扫 y=13, x=31..39，经过 (35,13),(36,13)V.
- 交叉格 (35,13) 在 phase 0 红蓝双射 -100（但 P_GATE 开时）。
- 通过路径 (34,13)→(35,13)→(36,13)：
  - 到达 (35,13) 那一拍 exposed={(34,13),(35,13)}；(34,13) 在蓝射线内（x=34 属于 31..39）→ 该拍蓝开火则伤；(35,13) 在红+蓝 → 该拍红开火也伤。所以需要红蓝都不开火：phase ∈{1,2,5,7,10,11}。
  - 到达 V(36,13) 那一拍 exposed={(35,13),(36,13)}，两者都在蓝射线，(35,13) 还在红射线 → 需要红蓝都不开火。
  - (34,13) 在蓝射线 → 勇者站在 (34,13) 等相位时，蓝开火拍会挨伤！所以不能在 (34,13) 等。需要更左边（x≤30? 蓝射线从 x=31 开始）→ 在 (30,13) 左边 (29,13) 等待安全。然后从 (29,13) 一路走到 (36,13) 需要 7 步，其中经过蓝射线 x=31..36 共 6 格，需要 6 个连续"蓝不开火"拍 + 最后 2 拍还要红不开火。蓝不开火 phase = {1,2,3,5,6,7,9,10,11}（蓝 {0,4,8}），连续最长：{1,2,3}(3), {5,6,7}(3), {9,10,11}(3)。红不开火 {1,2,4,5,7,8,10,11}。红蓝都不开火 = {1,2,5,7,10,11}，连续最长 2。
  所以无法 0 伤走完 6 格走廊（需要 6 连续蓝不开火）。最多 3 连续。→ 必须吃伤，或用 JUMP 跨 2 格 + ICE 滑行。

太苛刻。**放宽**：让蓝炮射线只覆盖 2 格（用 W 截断），比如把 (32,13) 设为 W？那勇者过不去。

**结论：让 author 解吃 50 伤通关即可**（HP 100 → 50，存活）。或者干脆**不把 V 入口放在激光里**，而是把激光放在主路的一小段（1-2 格），author 解用 WAIT 调相位 0 伤通过，或者吃一点伤。

我决定采用**简单可靠**方案：
- 激光射线覆盖主路若干格，但存在"绕行路径"（走 y=12 或 y=14 避开横向炮，或绕开纵向炮的列），author 解走绕行路径 0 伤。
- 对手若走最短直线 → 撞激光（可能死）。
- 加上 P_GATE 推箱锁（主要难点）。
- 加上 ONEWAY 死胡同陷阱。
- 加上长蛇形路径（T 大）。

这样 author 解容易生成（BFS 避开静态射线格），且稳健。

**具体布局**（最终）：
```
墙 A y=5 gap=38；墙 B y=17 gap=1。
K1=(34,3), K2=(12,19), V=(36,13)。
V 房间：(35,13)=P_GATE；(36,12)=W,(36,14)=W,(37,13)=W。
PLATE=(20,10), BOX=(17,10), ICE=(18,10),(19,10)。
激光（4 红 + 3 蓝，共 7 门 ≤12）：
  红 LASER_R (4,13) 向右扫 (5..14,13)  —— 覆盖主路左侧
  红 LASER_L (38,9) 向左扫 (28..37,9)
  红 LASER_R (4,7) 向右扫 (5..14,7)
  蓝 LASER2_D (20,6) 向下扫 (20,7..16) —— 纵列
  蓝 LASER2_R (10,15) 向右扫 (11..20,15)
  蓝 LASER2_U (30,24) 向上扫 (30,14..23)
  红 LASER_D (28,1) 向下扫 (28,2..11)
```
这些射线覆盖中部带主路的若干格，author 解 BFS 避开。但注意：主路 y=13 上，红 LASER_R(4,13) 覆盖 x=5..14；蓝 LASER2_D(20,6) 覆盖 (20,13)；蓝 LASER2_R(10,15) 覆盖 y=15 不挡 y=13。所以 y=13 主路在 x=5..14 与 x=20 被覆盖，author 可走 y=14 或 y=12 绕过（这些行是 EMPTY，除非有墙）。

但等等：如果绕行这么容易，对手也能绕。不过对手需要"知道"避开射线（明牌，laser_warnings 只给当前拍的射线格，但炮位可见可推算）。强求解器会绕，弱的可能不会。OK。

ONEWAY 陷阱：在 (24,12) 放 ONEWAY_R，后面接一个死胡同（W 围），诱使勇者进入后出不来。或者在墙缺口处放 ONEWAY 让路径单向，增加求解难度。为简单，放几个 ONEWAY 在"看似捷径"的支路上，不影响主路径。

MIMIC/PIT/CRACK：撒一些陷阱（用 hash 分布），不放在 author 路径上。

预算估算：
- W: 墙 A 38 + 墙 B 38 = 76 格 *5 = 380G；V 房间 3 W = 15G；ONEWAY 陷阱周围 W ~20 格 = 100G。合计 ~495G。
- 激光 4*75 + 3*90 = 300+270 = 570G。
- PLATE 45 + P_GATE 30 + BOX 30 + 2 ICE 20 = 125G。
- ONEWAY 4*30 = 120G。
- PIT 6*40=240G, CRACK 12*20=240G, ICE 额外 10*10=100G, MIMIC 2*60=120G, HEAL 1*30=30G。
- T_W 内墙少量 0G（外框不计）。
总计 ~2000G。g=(3000-2000)/3000=0.33。不错。可以再降（少放激光炮，因为 90G 一门）。用 3 红 + 2 蓝 = 225+180=405G → 总 ~1835G，g=0.39。

嗯，但激光是主要杀伤，多放几门值得。折中：3 红 + 3 蓝 = 495G。

author 路径生成：用 BFS 在静态图（避开：PIT、MIMIC、所有激光射线格、W/T_W/炮座/关闭 P_GATE 前先推箱、CRACK 可选、ONEWAY 方向）上求：
spawn → (16,10)（推箱点）→ K1 → K2 → (34,13) → (35,13) P_GATE（此时应已开）→ V。
但推箱后勇者位置在 (17,10)，且必须保证推箱动作序列正确。

其实我可以让 author_solution 由**通用求解器离线生成**（在 build_dungeon 内不允许慢，但我可以在本地测试时生成，然后把结果作为压缩字符串常量嵌入 submission.py）。这样最稳：用我写的 A* 在离线跑出 ≤200 步解，编码成 RLE 字符串，build_dungeon 直接解码返回。

这很实用！author_solution 只是个动作列表，可以硬编码（自己的图，允许）。这样避免 build_dungeon 内复杂路径生成，且保证与引擎一致。

但硬编码序列 ~150 步，RLE 压缩后可能 ~100 字符。可行。

不过要注意：`author_solution` 必须"恰好最后一步首次通关"，且 ≤200 步。离线验证后写入即可。

好，方案确定：
1. 写 submission.py：Sim、validate、solver、decide_action、build_dungeon（地图生成 + 从内置 RLE 常量解码 author_solution）。
2. 写本地测试脚本，先用 Sim 验证地图合规 + author 解；若 author 解不通，用 solver 生成一条（求解器在 FULL 明牌下应该能解自己的图），然后把生成的序列编码回写进 submission.py。
3. 回归基准。

由于 author_solution 需要与地图一致，我先写地图生成，用测试脚本跑 solver 得到解，再写入常量。这需要两轮。可以先在 build_dungeon 里放一个占位（比如先用 BFS 生成），后面替换成 RLE。

其实更简单：**build_dungeon 内部直接调用一个轻量的确定性路径生成器 `_author_path(grid)`**，用 BFS（避开静态射线格 + PIT + MIMIC + 关闭的 P_GATE 视为可通过但记录推箱）+ 固定推箱动作 + WAIT（其实不需要 WAIT，因为避开射线格）。这样每次调用都能生成合法解，且 ≤2s（BFS 很快）。然后本地验证。

我采用这个：路径生成器在 submission.py 内，build_dungeon 调用它。生成逻辑：
- 用 BFS 求 `spawn → (16,10)`（推箱起点左侧），执行推箱动作 MOVE_R（把 BOX 从 (17,10) 推到 PLATE(20,10)），此时勇者在 (17,10)。
- 然后 BFS 求 `(17,10) → K1(34,3)`，`K1 → K2(12,19)`，`K2 → V(36,13)`，拼接。
- BFS 允许经过的地形：EMPTY/K1/K2/V/CRACK/ICE? ICE 会滑行导致位移不确定 → BFS 避开 ICE/MIRROR/SPRING/PORTAL/ONEWAY（简化，只允许 EMPTY/K1/K2/V/CRACK，CRACK 走一次后变 PIT，不能重复经过 → BFS 路径不重复所以 OK）。
- 避开静态激光射线格（所有炮的射线，不管相位，保守）。
- 避开 PIT、MIMIC（用 clues 判定或直接避开所有 CHEST）、W/T_W/炮座/关闭的门。
- P_GATE：推箱后 plates_active=True，所以视为可通过。
- ONEWAY：避开（不走进 ONEWAY 格），除非必要。

这样 BFS 得到的路径每步是相邻格移动，动作 = MOVE_dir。总步数 ≤200。

风险：BFS 路径经过 CRACK 后变 PIT，若后续路径再经过该格会死。BFS 路径不重复格，且后续段路径可能重复经过前面段的格（比如 K1→K2 会经过 spawn 附近）。为了安全，让 BFS 完全避开 CRACK（只允许 EMPTY/K/V/P_GATE(开)/PLATE? PLATE 可走）。简化：allowed = {EMPTY, K1, K2, V, P_GATE, PLATE, SWITCH? 避免}。避开 CRACK/ICE/ONEWAY/MIRROR/SPRING/PORTAL/CHEST/PIT/W/T_W/炮。

这样路径全在平地，非常稳。但 P_GATE 是地形（开着时可走）✓。

BFS 避开的"静态射线格"：计算所有炮（红+蓝）的射线（忽略相位），全避开。这样 0 伤。

段间衔接：拼接头尾位置连续即可。

总长度估算 ~150 步 + 1 推箱。≤200 ✓。

还要注意：`_author_path` 生成的动作序列回放时，激光在 phase 3/4/0 会开火，但路径全避开射线格 → exposed 不含射线格 → 0 伤 ✓。但注意**爆炸/箱子推动可能改变射线**（P_GATE 开/关）。推箱前 plates_active=False → P_GATE 关闭（高墙）→ 某些炮射线被挡；推箱后打开 → 射线变长。我在计算"静态射线格"时用**推箱后的状态**（P_GATE 开，最坏情况），这样全程避开 ✓。

另外 BOX 推到 PLATE 后，BOX 会挡住经过 (20,10) 的激光射线（如果有炮扫过该格）。我用最坏情况（无 BOX 遮挡）计算射线 → 保守 ✓。

好，开始写代码。我尽量一次写对。

关于 validate：build_dungeon 内部可以调用本地合规检查（不需要，但测试脚本会用）。

让我写。

由于代码很长，我会写成一个文件，约 900 行。开始。

注意一些细节：
- `state["plates_active"]` 可能为 None → bool()。
- `state["laser_warnings"]` 可能含 period/cannon，我不用它做规划（自己算 rays），但可用于校验。
- `state["terrain"]` 中 `CHEST` 需要区分 MIMIC/HEAL：用 clues。
- `state["clues"]` 是 26x40 bool。

MIMIC 判定简化：对每个 CHEST 格 c，若其 4 邻任一 clues=True → MIMIC，否则 HEAL。但如果有多个 CHEST 相邻一个 clue，会误判。为了自造图，我保证 CHEST 孤立。对基准图（BENCH_STRONG 无 chest? 战报里有 MIMIC 吗？没有）应该 OK。

- `state["occupant"]` 可能是 list of list with None/'BOX'/'TNT'。

我要小心：`_Sim._from_state` 里 bt 包含 CHEST→MIMIC/HEAL，而 `K1/K2/V` 在 terrain 里可能已被拾取（EMPTY）→ 用 targets 补充？如果 K1 已拾取，terrain 变 EMPTY，后续模拟不需要再拾取（keys 已有）。OK。但 targets 用于启发式，直接从 state['targets'] 取。

- 端口：`self.portals` 从 bt 扫描 PORTAL_* 成对。

好，写吧。

我先写文件的前半部分（常量 + validate + Sim），然后后半部分（solver + build_dungeon）用 replace_in_file 追加？write_to_file 一次写完更稳。但内容太长可能出错。我分两次：第一次写完整文件（包含所有部分），我尽量精确。

考虑 token 预算，直接写。

对了，还要遵守"严禁 eval/exec/getattr/setattr"。我不会用。允许 `time`, `heapq`, `collections`, `itertools`, `math`, `json`（虽然不用）。

另外，用户说"写成的一切文件均放在该文件夹"——测试脚本也放该文件夹：`v22_local_test.py`。

开始写 submission.py。

我需要写 `_author_path` 使用 BFS，注意 P_GATE 在"推箱后打开"的假设。但 author 解回放时，第一段是 spawn→(16,10) 然后 MOVE_R 推箱。推箱前 P_GATE 关闭；路径第一段不经过 P_GATE（在 x≤16），OK。之后 P_GATE 打开。

但 BFS 计算射线时，用 P_GATE 开（最坏）。而推箱前 P_GATE 关时射线更短（更少的危险格），保守避开更多格，OK。

还有：BOX 初始在 (17,10)，勇者 spawn→(16,10) 的 BFS 要把 (17,10) 视为障碍（有 BOX）✓。推箱 MOVE_R 后勇者在 (17,10)，箱子在 (20,10)。之后 BFS 从 (17,10) 出发，(20,10) 有 BOX → 障碍 ✓。

推箱动作细节：勇者在 (16,10)，MOVE_R，p1=(17,10) 有 BOX，p2=(18,10) ICE，passable(BOX) ✓ → chain("BOX",(17,10),(18,10),R)：箱子到 (18,10) ICE → 继续滑 (19,10) ICE → (20,10) PLATE（普通地面）→ STOP。然后勇者跟进 chain("hero",(16,10),(17,10),R)：terrain (17,10)=EMPTY → STOP。✓ plates_active=True。

注意：ICE 滑行时，箱子在 (18,10)→(19,10)→(20,10)，每一步都检查 passable(nxt,"BOX",d)。(20,10) 是 PLATE，不是 high，occ None → 可进入 ✓。到 (20,10) 后 terrain 不是 ICE/MIRROR/SPRING/PORTAL → STOP ✓。

好。

还有 V 房间：`(35,13)=P_GATE`，从 (34,13) MOVE_R 进入。P_GATE 是地形（非 high 当 plates_active）✓。V(36,13) 从 (35,13) MOVE_R 进入 → CLEARED ✓（keys 齐）。

注意：如果 P_GATE 开着，勇者站在 (35,13) 时，plates_active 仍 True（BOX 在板上）✓。

现在写。

关于 `_solve` 的细节，我再想一下如何让它能解 BENCH_WEAK（含推箱）。A* 状态包含 boxes（通过 sim.do 的 BOX 项），动作 MOVE_R 推箱会改变 do → 状态变化 → 可以搜索。启发式需要考虑"必须推箱"：若目标被 P_GATE 挡住且 plates 未激活，h 应该加一个惩罚，引导去推箱。否则 A* 可能一直朝 V 走撞墙。我在 h 里加：若 `not plates_active` 且存在 P_GATE，则 h += 20 + 到最近 (BOX→PLATE) 的估计距离。但更简单：把"plates_active"作为状态，A* 自然会探索推箱（因为不开板无法到达 V，所有到达 V 的路径都要求 plates_active=True）。只要搜索空间包含推箱动作，A* 会找到。但推箱需要勇者走到 BOX 后方特定位置，A* 的启发式（曼哈顿到 V）会把它拉向 V，可能不探索远离 V 的推箱准备动作 → 搜索效率低下，可能超时。

改进启发式：分阶段目标。先求 "让 plates_active=True" 的子目标，再求到钥匙/V。实现为两阶段 A*：
- 阶段 1（仅当存在 P_GATE 且当前未激活）：目标 = plates_active True。启发式 = min over (BOX,PLATE) of (dist(hero, push_pos) + dist(box,plate))，其中 push_pos 是能推动 box 朝 plate 的勇者站位。粗略用曼哈顿。
- 阶段 2：目标 = CLEARED，启发式 = 到钥匙/V 的距离和。

但阶段 1 的目标是"3 个 PLATE 全被压"（BENCH_STRONG），需要多次推箱。A* 状态含 boxes，能处理，只是慢。

考虑实现复杂度与时间，我先实现**单阶段 A\***，状态含 boxes，启发式含"压板未激活惩罚"，并给 A* 较大的节点预算 + weighted heuristic。然后测试 BENCH_WEAK/STRONG，看效果再优化。

启发式：
```
def h(sim):
    pos=(hx,hy)
    keys=...
    # 目标序列估计
    if keys != 3:
        # 到最近未拿钥匙 + 该钥匙到另一钥匙 + 另一钥匙到 V
        d = min over order of (dist(pos, kA) + dist(kA,kB) + dist(kB,V))
    else:
        d = dist(pos,V)
    d += 15 * (number of plates not covered) if P_GATE exists
    return 0.5*d  # 保守（因为 JUMP/滑行可多格）
```
dist 用曼哈顿（可采纳性存疑但作为 weighted 使用）。

嗯，加上"未压板惩罚"可能让启发式不可采纳，但没关系（找得到解就行）。

节点预算：Turn1 1.5s，用 deadline 控制。Turn>1 0.42s。

动作集：14 个全开。但 BOMB 会导致状态爆炸（炸弹 timer、爆炸改变地形），且多数图不需要。我默认包含 BOMB（因为正赛可能需要炸墙），但给 BOMB 的动作加一个较大 cost（如 +3）以降低优先级。

另外 THROW 动作会翻门（需要时有用），保留。

好，写代码。

一个性能关键：`clone()` 每次复制 dt/do（小 dict），`step()` 里 rays 只在激光拍计算。`state()` 不调用。A* 节点数几千到几万，应该 OK。

`sig` 生成：Turn1 求解后，用 root clone 依次执行 plan 记录 `_sig_sim`。这是 O(n) 次 clone+step，很快。

现在真正开始写文件。

我还要写 `_validate_grid` 供本地测试（含 v2.2 规则）。放在 submission.py 里也无害（纯计算）。

写吧。为控制长度，我尽量紧凑。

注意：`TILE_COSTS` 中 `PORTAL_1A` 等单价 40 each（对 80G）。GV22_01 验证 225G = PLATE45+BOX30+P_GATE30+LASER2_D90+ONEWAY_R30 = 225 ✓。

CAPS: T_W 120 (inner), CRACK 40, SWITCH 6, TNT 12, BOX 6, HEAL 4, MIMIC 4, R_GATE+B_GATE 16, LASER+LASER2 12, SPRING 20, MIRROR 30, PORTAL 2 pairs, PLATE 4, P_GATE 8, ONEWAY 12.

P_GATE 约束：if P_GATE>0: 1<=PLATE<=BOX.

出生 4 回合准入：在测试脚本里做（不在 submission.py 里，因为评测机会自己校验）。不过我可以在 submission.py 里提供一个 `_birthcheck` 函数供测试调用。放测试脚本里更合适，但需要 Sim。测试脚本可以 import submission 的 `_Sim`。好。

现在写 submission.py。

我会把地图生成写得确定、简单。让我把 ONEWAY 陷阱简化：在 (10,8)..(14,8) 造一条"死胡同"支路，入口 ONEWAY_R，尽头 W 围。不影响主路径。

PIT/CRACK/MIMIC 撒在 author 路径之外（用 hash 排序选点，避开路径/射线/墙）。为简单，先不撒太多，避免破坏 author 路径。用 `_author_path` 计算出的路径作为 forbidden。但 build_dungeon 内先生成地图再算路径，陷阱放置需要知道路径 → 顺序：先放墙/地标/推箱/激光/ONEWAY，再算 author 路径 BFS，再撒陷阱（避开路径），再重新算一次 author 路径（因为陷阱可能挡路，但避开路径就不会）。OK。

但陷阱放置也可能挡住 BFS 的唯一通道（如果通道很窄）。为安全，撒陷阱只在"非通道"格，或者干脆**不撒随机陷阱**，只用少量固定的 PIT/CRACK/MIMIC 放在明显不影响主路的位置。为降低风险，我撒少量（~10 个），并检查 BFS 仍通。

嗯，还有个问题：撒 PIT/CRACK 在中部带 y=13 主路旁边会挡住 BFS 绕行（若 BFS 需要绕开射线）。我让 BFS 在陷阱放置前算一次路径，把路径格加入 forbidden，然后撒陷阱后再算一次确认。若不通，减少陷阱。

好，开始写代码，边写边简化。

关于 `author_solution` 生成函数 `_author_path(grid)`：需要知道静态射线（P_GATE 视为开）与 forbidden tiles。BFS allowed = {EMPTY, K1, K2, V, P_GATE, PLATE}（PLATE 可站，不触发；但 BOX 在 (20,10) 占着，BFS 需把有 BOX 的格视为障碍）。我把 BOX 初始位置也 forbidden。

段：
1. spawn(2,13) → (16,10)：BFS。
2. "MOVE_R"（推箱）。
3. (17,10) → K1(34,3)：BFS。
4. K1 → K2(12,19)：BFS。
5. K2 → V(36,13)：BFS（经过 (35,13) P_GATE）。
拼接每段动作，去掉段首（当前位置）。

注意段 3 的起点是推箱后勇者位置 (17,10)。段 1 终点 (16,10)。

BFS 每段用同一个 forbidden 集合（静态射线格 + PIT + MIMIC + W/T_W/炮 + ICE/CRACK/ONEWAY/MIRROR/SPRING/PORTAL/BOX 位置 + CHEST）。注意 K1/K2/V 是目标，允许进入。但为避免提前踏上 V（未拿齐钥匙时踏上 V 不会通关，只是普通格？规则：先拿齐钥匙再进 V 立刻通关；未齐时进入 V 无害？上半场引擎 chain 里 `elif t == "V" and keys both` → CLEARED，否则无效果，V 保留。所以可以经过 V 而不通关。但为了简单，BFS 把 V 作为 forbidden 除了最后一段）。

嗯，K1/K2 在 BFS 中作为中间格可能被提前拾取，没关系。

段 4 从 K1 出发，K1 已被拾取变 EMPTY，BFS 允许。

好。总步数 ~150。

现在写代码。真的开始。

关于 `_Sim.state()`：我需要它来在测试中把 sim 状态喂给 decide_action 以及验证 golden vectors。实现全图明牌输出。

我还需要 `Game` 类似接口供测试：`v22_local_test.py` 里直接用 `_Sim`。

好。写。

（代码量大，我一次性 write_to_file。）

注意 Python 3.11+，允许 f-string 等。

最后 decide_action 的 try/except 兜底返回 "WAIT"。

开始。
````

## 042.1 · Thinking

```
我写了一个半成品 `_solve`（占位）没用，实际用 `_plan_from_state`。还有 `_plan_from_state` 中有 bug：`heapq.heappush(openh, (ng + 1.25*hh, ng, nnid, ck, nnid))`，第 3 个 counter 与 nid 混用，但 tuple 比较时如果前两项相同会比较 nnid（int）然后 ck（tuple）——OK 可比较。但 `openh` 初始 push 是 `(h0, 0.0, counter, root.key(), 0)`；pop 时解包 `f, g, _c, skey, nid`，一致 ✓。

不过 `gscore` 用 `skey` 检查，而 `skey` 是 `c.key()`；但 `g > gscore.get(skey, INF)` 的判断：pop 出的 g 与 gscore[skey] 比较 —— 但 skey 是当前节点的 key，g 是到达它的代价。若有更优路径到达同一 key，gscore[skey] 会更小，旧条目被跳过 ✓。

`sims` 字典会存所有节点（可能很大），限制 120000。内存可能吃紧但 OK。

问题：`_plan_from_state` 中 `parents[nnid] = (nid, act)`，回溯用 nid 链 ✓。但 `sims[nid]` 在 pop 时可能因为覆盖了？不会覆盖。

还有一个严重问题：`_Sim.key()` 包含 `self.turn % 12` 但不包含绝对 turn；A* 搜索可能无限循环（例如 WAIT 循环），但 gscore 阻止重复状态 ✓。不过 `turn % 12` 相同但 turn 不同，状态相同 → 合并，OK（因为后续只依赖 mod 12 和剩余回合数）。但 MAX_TURNS 限制会导致 TIMEOUT 状态，A* 里 `sim.status != "PLAYING"` → skip ✓。不过如果 turn 超过 240，step 会设 TIMEOUT，A* 会跳过。由于状态合并（mod 12），一个节点可能代表 turn=13 或 turn=25，若前者能继续而后者会 TIMEOUT，合并会出错。实践中搜索深度不会接近 240（路径 ≤200），且启发式引导，风险可接受。但为了安全，可以在 key 里加 `min(turn, 240)//12`? 不必要。

另一个问题：`_greedy_action` 里有奇怪的 `val = -10 * c.h["hp"] if False else 0` 残留，无害但难看，稍后清理。

还有：`_static_dist_map` 里 `if sim.high(*p) or sim.tile(*p) == "PIT": continue` —— 这是检查目标格 p 是否高墙，但 p 是从 goal 扩展出来的当前格；应该检查**前驱 n** 是否可站立，以及从 n 到 p 的移动是否合法（p 的 ONEWAY 方向）。我写反了：`sim.blocks_oneway(*p, d)` 检查 p 的进入方向（从 n 到 p 的方向是 (dx,dy)，因为 p = n + (dx,dy)... 等等：n = (p[0]-dx, p[1]-dy)，所以从 n 到 p 的方向是 (dx,dy) ✓。检查 `blocks_oneway(p, (dx,dy))` ✓。但 `if sim.high(*p)` 应该是检查 p 是否可进入（是），以及 n 是否可站立（n 是前驱，需要 n 不是高墙/PIT）。我写成检查 p，且没检查 n。修正：检查 `sim.high(*n) or sim.tile(*n)=="PIT" or sim.occ(*n) in ("BOX","TNT")` 以及 `sim.high(*p)`、`blocks_oneway(p,d)`。

嗯，BFS 是反向（从 goal 往前驱扩展），dist[n] = dist[p]+1 表示从 n 走到 p 一步。需要 n 可站立且 p 可进入。让我修正。

另外 `_plan_from_state` 里 `need_plates` 计算有两行冗余（第一行赋值后又覆盖），清理。

还有 `_solve` 是没用的占位函数，应删除（避免混淆）。

更重要：`_plan_from_state` 里 `if (nodes & 31) == 0 and time.monotonic() > deadline: return None` —— 如果超时返回 None，decide_action 会走贪心。但 Turn1 若超时（1.55s），就没有完整计划，之后每回合都尝试重规划（0.4s）可能一直超时 → 贪心。这不好。应该在 Turn1 用更长预算但确保能出解；同时贪心要足够好。

还有个**重大问题**：`_plan_from_state` 的状态空间包含 `dt`（地形变化）和 `do`（占用变化），`key()` 里 `tuple(sorted(self.dt.items()))` —— dt 的 key 是 (x,y) tuple，value str；排序 OK。但如果 dt 很大（例如炸弹摧毁很多格），key 变长，A* 变慢。可接受。

现在先写测试脚本，跑起来看问题。测试脚本要：
1. 验证 golden vectors（用 _Sim）。
2. 验证 build_dungeon 合规 + author_solution 回放（≤200 步、CLEARED、HP>0）。
3. 出生 4 回合准入检查。
4. 跑 BENCH_WEAK / BENCH_STRONG / part1 14 图（FULL）对局，统计。
5. 测 decide_action 耗时。

先写测试脚本。

注意：测试脚本也放在该文件夹（用户要求）。命名 `v22_local_test.py`。

golden vectors：
- GV22_01: budget 225G（用 validate_grid 构造网格）；initial_plates_active false。
- GV22_02: PLATE(5,13), P_GATE(34,13), BOX(7,13)。步骤：勇者从 (4,13) MOVE_R → 踏上 PLATE(5,13)，plates_active 仍 False，P_GATE 关闭。然后从 (8,13) MOVE_L, MOVE_L 推 BOX(7,13)→(6,13)→(5,13) PLATE → plates_active True, P_GATE 开。注意 (6,13) 得是 EMPTY。
- GV22_03: turn=12, hero(15,10), LASER_D(15,8), LASER2_R(12,10), WAIT → hp 0, DEAD, warnings periods [3,4] at (15,10)。
- GV22_04/05/06/07/08: 需要精细场景，比较费事。我可以做部分。

先做核心验证，再补。

关于出生 4 回合准入：用 _Sim 从 grid 构造，枚举 Turn1 动作，收集 hp==100 且 PLAYING 的不同落点；对每个落点用 DFS 深度 3（turn 2,3,4）找一条 0 伤序列。注意要 clone 状态。实现 DFS 早停。

写测试脚本。
```

## 044.1 · Thinking

```
先跑 own + golden 看基本情况。
```

## 046.1 · Thinking

```
几个问题：
1. author 解吃了 50 伤（D=50）——虽然合法（存活通关），但说明路径经过激光射线格（可能因为推箱后 P_GATE 打开导致射线变化，或者第三段路径穿过射线但相位安全？不，D=50 说明某回合挨了一次红/蓝炮）。可以接受，但更好是 0 伤。稍后看。
2. self-play DEAD at T=51 —— 求解器死了！而且 wall 22s（每回合 1.59s，说明 plan 一直失效，每回合都重规划超时）。worst_step 1.594s 说明 Turn>1 也用了 1.55s？不对，budget 是 0.40，但 `_plan_from_state` 内部 `time.monotonic() > deadline` 只在 `(nodes & 31)==0` 时检查，若节点循环很快但总时间…… 实际上 1.594s 可能是 Turn1（1.55+开销）。但 wall=22s for 51 turns → 平均 0.43s，说明每回合都在重规划并耗尽 0.40s 预算 → plan 从未生效！

原因：`sigs[idx] == sig` 校验失败。可能因为 `_sig_of_sim` 与 `_sig_of_state` 不一致，或者 plan 生成后 sim 回放的状态与真实不一致。

让我诊断：Turn1 生成 plan 后，我回放 sim.step 生成 sigs。Turn2 时，`idx=1`，`sigs[1]` 应为执行 plan[0] 后的 sim 签名；实际 state 的 sig 应该一致。但 `play()` 里 Turn1 调用 decide_action 返回 plan[0]，然后 sim.step(plan[0])；Turn2 state 来自 sim.state()。理论上一致。

可能问题：`_sig_of_state` 的 `plates_active` 与 `_sig_of_sim` 一致吗？`_Sim._from_state` 用 `_decode_chest` + occupant 重建 bo；plates 从 bt 扫描。如果 PLATE 格在 state terrain 里是 "PLATE"，OK。但 **state 的 terrain 中 CHEST 被解码**：我 `_decode_chest` 把 CHEST 转成 MIMIC/HEAL。如果 state 里的 clues 是 `_Sim.state()` 生成的（对每个 MIMIC 在其四邻 EMPTY 标 clue）—— 我的 `_decode_chest` 判定 CHEST 四邻有 clue → MIMIC ✓。一致。

但另一个可能：**plan 生成失败（返回 None），走贪心分支**，此时 `memory["plan"]=[act]`, `sigs=[sig]`, `idx=1`。Turn2 时 `idx=1 >= len(plan)=1` → 重新规划。每回合都重新规划 → 每回合 0.4s。而 worst_step=1.594 是 Turn1。且 DEAD 说明贪心不好。

Turn1 的 `_plan_from_state` 超时返回 None 了吗？1.59s 说明它跑满了 1.55s，然后返回 None（超时）→ 贪心。所以求解器没能在 1.55s 内解出自己的图！这是个大问题。

需要诊断 A* 性能与行为。可能：
- 状态空间太大（含 dt/do/bombs 的完整 key），gscore 检查阻止重复，但每个新状态都不同（因为 dt 变化？不，dt 只在某些地形变化时变）。
- `sims` 字典保存所有节点，内存/时间开销。
- A* 的启发式弱 → 展开大量节点。
- 每节点 14 次 clone + step，step 里 `phase_d` 在激光拍调用 `rays`（遍历所有炮，每炮 10 格）+ `high()` 里 `plates_active()` 每次遍历 plates（小）。`rays` 里 `self.high(cx,cy)` 会调用 `plates_active()`（遍历 plates），还好。
- 但 `explode` 里有一个 O(H*W) 循环（只在爆炸时）。
- `key()` 里 `tuple(sorted(self.dt.items()))` 每次排序，若 dt 大则慢。

主要瓶颈可能是节点数太多 + 每步 14 个 clone/step。

让我加诊断：统计 Turn1 的 nodes 数、是否超时、返回什么。我可以临时在测试脚本里直接调用 `_plan_from_state` 并计时，打印 len(seq)。

另外 self-play DEAD 也可能是因为贪心动作走到激光里。

先诊断。让我写个快速命令。
```

## 048.1 · Thinking

````
即使 5 秒、20 万节点也没找到解。说明搜索本身有 bug 或状态空间设计有问题。

可能 bug：
1. `_plan_from_state` 中 `if sim.status != "PLAYING": continue` —— 但 `sim.status == "CLEARED"` 的检查在前面，OK。
2. `gscore` 用 `skey` = `c.key()`，但 pop 时 `if g > gscore.get(skey, INF)`：注意 `skey` 是 **当前节点** 的 key，而 `g` 是到达当前节点的代价。初始 push 是 `(h0, 0.0, counter, root.key(), 0)`；gscore[root.key()]=0 ✓。
3. 但是 `heapq` 元组第 3 个元素 `nnid`（int）与第 4 个 `ck`（tuple），第 5 个 `nnid`。初始第 3 个是 counter=0。比较时若前两项相同，比较 int 与 int OK。
4. **关键 bug**：`sims[nnid] = c`，但 `nnid = counter`，而 `counter` 从 1 开始（root 是 0）。`heapq.heappush(openh, (ng + 1.25*hh, ng, nnid, ck, nnid))` —— 这里把 nnid 同时当作 counter 和 nid，OK。
5. **状态 key 包含 `dt`**：每走一步，`chain` 里若 tile 是 CRACK 会 set_tile，但普通 EMPTY 不会。所以 dt 通常空。但 `do` 呢？`set_occ` 只在推箱/爆炸时。所以 key 主要是位置/相位/keys 等 → 状态数 ~1040*12*4*2 = 100k。A* 应该能搜到。
6. **启发式问题**：`_heuristic` 用 `_static_dist_map` 计算距离。`_static_dist_map` 有 bug：我检查 `sim.high(*p)`（p 是已扩展的格）而不是 n；如果 p 是高墙（比如 goal 是 V，V 不是高墙），那么从 V 扩展时 `sim.high(*V)` false，OK。但加入 n 时不检查 n 是否可站立！所以 dist map 会给 W 墙、PIT 等格也赋距离，导致启发式低估（安全）甚至把不可达格算成可达。低估不会导致找不到解，只是慢。

7. **更严重的 bug**：A* 里 `c.step(act)` 后，`c.status` 可能是 "TIMEOUT"（若 turn>240），但不会。关键是 **`if c.status == "DEAD": continue`** —— 但我们希望 0 伤通关，吃伤不 DEAD。OK。

8. **最可能**：目标判定 `sim.status == "CLEARED"`，但 `step()` 里 V 通关需要 `all(keys)` 且 hp>0。要到 V，keys 必须齐。搜索需要拿两把钥匙。启发式应该引导。但 `_heuristic` 里：
```
a = 0 if k[0] else dk1.get(p,60)
b = 0 if k[1] else dk2.get(p,60)
c1 = a + man(K1,K2) + dv.get(K2,60)
c2 = b + man(K2,K1) + dv.get(K1,60)
d = min(c1,c2)
```
这个估计没问题（粗略）。但 `dk1` 等 `_static_dist_map` 可能给出错误值。

9. **致命问题**：`_plan_from_state` 里的 `gscore` 检查用 `skey`，但我 push 的是 `ck`（子节点的 key），而 pop 时改名为 `skey`。`gscore[ck]=ng` 在 push 前设置 ✓。所以一致。

10. **重大 bug**：`parents[nnid] = (nid, act)` 但 `nid` 是父节点的 id；而 `sims[nid]` 在 pop 时取到。可是 **`counter` 与 `nnid` 相同，但 `sims` 字典的 key 是 `nnid`**；初始 root id=0 ✓。

嗯，让我直接调试：统计 nodes 数、找到的最好状态（最小 h）、是否曾接近目标。写个诊断脚本。

另一个可能：**`_Sim.step` 的 `phase_d` 会误伤** —— 如果 rays 覆盖了几乎所有格（因为我的地图有 7 门炮，射线覆盖很多格），A* 在激光拍会大量 DEAD（吃 100 伤），导致搜索树被剪枝到只剩 WAIT 循环。但 WAIT 也是一步，相位变化，可以等。不过如果 hero 所在格在射线内，WAIT 也会挨伤。

关键：`_static_beams` 计算的 beams 用于 author 路径避开。但 author 路径 D=50 说明有一段路径仍挨伤。也就是说，即使 BFS 避开了静态 beams，推箱后 P_GATE 打开可能让某条射线延长，导致路径上某格变成射线格。我在 `_static_beams(grid, plates_open=True)` 里把 P_GATE 视为开，所以已经考虑。但 **BOX 被推到 PLATE 后会遮挡射线**（减少危险），不会增加。所以为什么 D=50？

可能：`_static_beams` 里我用 `grid` 是**撒陷阱之前**的地图，且 P_GATE 视为开。但 `beams` 里我没有把 LASER2 的周期考虑进去——避开所有射线格即可 0 伤。除非路径经过射线格但那回合没开火（D=50 说明有一回合开火了）。

或者：`_static_beams` 里射线遇到 `R_GATE` 停止；但我的图没有 R_GATE。遇到 `P_GATE` 时（plates_open=True）不停止，继续。但**实际引擎里 P_GATE 关闭时是高墙，会挡射线**；打开时不挡。我用打开（最坏）✓。

还有：`_static_beams` 里 `if ct in HIGH_BASE: break` —— 包括 LASER 炮座本身。但 `LASER2_*` 也在 HIGH_BASE ✓。

嗯，等一下：**`_static_beams` 从 `grid` 计算，但 `grid` 中 P_GATE 在 (35,13)，而红炮 LASER_R(4,13) 向右扫到 (14,13)；LASER_L(38,9) 向左扫到 (28,9)；LASER_D(28,1) 向下扫 (28,2..11)；LASER2_D(20,6) 向下扫 (20,7..16)；LASER2_R(10,15) 向右扫 (11..20,15)；LASER2_U(30,24) 向上扫 (30,14..23)。**

注意：`LASER2_D(20,6)` 向下扫时遇到 (20,10)=PLATE（不是高墙）→ 继续；(20,17)=W（墙 B y=17）→ 停。所以覆盖 (20,7..16)。

`LASER2_R(10,15)` 向右扫 y=15, x=11..20：遇到 (20,15) 是射线内（也是 LASER2_D 的列）→ 交叉。

`LASER2_U(30,24)` 向上扫 x=30, y=23..14：遇到 (30,17)=W 墙 → 停在 y=18? 从 (30,24) 向上 k=1..10 → y=23,22,21,20,19,18,17(墙 W) → 停在 y=17 之前，覆盖 (30,18..23)。所以 (30,17)=W 挡住。

`LASER_D(28,1)` 向下扫 x=28, y=2..11：遇到 (28,5)=W 墙 → 停在 y=4，覆盖 (28,2..4)。

`LASER_L(38,9)` 向左扫 y=9, x=37..28：遇到 (28,9)? 空。覆盖 (28..37,9)。

`LASER_R(4,13)` 向右扫 y=13, x=5..14。

`LASER_R(4,7)` 向右扫 y=7, x=5..14。

还有 **ONEWAY 陷阱的 W 墙** 在 y=11,13 x=24..28，会挡某些射线吗？y=13 的 W 在 x=24..28 不挡 x=5..14 的射线。OK。

那么 author 路径避开所有 beams，为何 D=50？可能是 **推箱动作 MOVE_R 使勇者进入 (17,10)**，而 (17,10) 是否在某射线内？LASER2_D(20,6) 是列 x=20，不在。LASER_L(38,9) 是 y=9。所以 (17,10) 不在。

或者：**`_static_beams` 只在 `grid` 上算，但撒陷阱后 PIT/CRACK/MIMIC 可能挡射线？** 不会增加射线。

或者，**射线在引擎中因 BOX 位置变化而变长**：初始 BOX 在 (17,10)，可能挡住某条射线；推到 (20,10) 后，(17,10) 不再挡，射线变长覆盖新格！例如 LASER_R(4,10)? 没有。LASER_L(38,9) 是 y=9。嗯，(17,10) 不在任何炮的射线上（炮位：y=13 行 x=5..14；y=9 行 x=28..37；y=7 行 x=5..14；x=20 列 y=7..16；y=15 行 x=11..20；x=30 列 y=18..23；x=28 列 y=2..4）。(17,10) 不在。所以不是。

也许 D=50 来自 **MIMIC**：我撒了 2 个 MIMIC，author 路径 BFS 避开所有 MIMIC（`blocked` 包含 MIMIC）。但 `blocked` 是在撒陷阱**之前**构建的！撒陷阱后，PIT/CRACK/MIMIC 放在了 `cands`（避开 golden 路径）里，所以不在路径上。除非 `golden` 集合计算有误：`golden = set(seg0)|...`，但 `seg0` 等可能来自退化分支（`blocked -= beams`）—— 不，第一次 BFS 成功了（author 170 步）。

嗯，还有一个可能：**V 房间 (36,12),(36,14),(37,13)=W**，但 P_GATE(35,13) 打开后，红炮 LASER_L(38,9)? 不涉及 y=13。等等，`LASER_L(38,9)` 在 y=9。没有炮扫 y=13 的右侧。所以 V 安全。

让我直接回放 author 解，找出哪一回合掉血。用测试脚本 trace 或写个命令。

另外，A* 找不到解的原因可能是 **`_static_dist_map` 的 BFS 方向性 bug** 导致启发式极度低估（比如所有格 dist=0），使得 A* 退化成 Dijkstra，展开巨量节点。让我检查 `_static_dist_map`：
```
q = deque([goal]); dist={goal:0}
while q:
  p=q.popleft(); d0=dist[p]
  for dx,dy in NEI4:
    n=(p[0]-dx,p[1]-dy)
    if ... or n in dist: continue
    if sim.high(*p) or sim.tile(*p)=="PIT": continue
    d=(dx,dy)
    if sim.blocks_oneway(*p,d): continue
    if sim.occ(*n) in ("BOX","TNT"): continue
    dist[n]=d0+1; q.append(n)
```
这里 `sim.high(*p)` 检查 p（当前格）——如果 p 是高墙，就不会扩展。但 goal 是 V/K，不是高墙。然而 **P_GATE 关闭时是高墙**：V 到不了？不对，BFS 从 V 出发，V 本身不是高墙，扩展到 p=V 的邻居 n=(35,13)（P_GATE）：`sim.blocks_oneway(*V,d)`? V 不是 ONEWAY。`sim.occ(*n)`? None。所以 dist[(35,13)]=1。但 **没有检查 n 是否高墙**！(35,13)=P_GATE 关闭时 high=True，但 dist 仍赋 1。继续从 (35,13) 扩展，它 `sim.high(*p)`=True → 不再扩展。所以 BFS 到 (35,13) 就停了，启发式认为从 (34,13) 到 V 的距离是 2（(34,13)→(35,13)→V），但 (35,13) 是关闭的 P_GATE → 实际上启发式**低估**，OK（可采纳）。但更糟：BFS 从 (35,13) 不再扩展 → 所有左侧格的 dist 都是 INF → `dk1.get(p,60)` 默认 60，启发式变成常数 60*0.55=33，A* 退化成 Dijkstra（因为 h 几乎常数）→ 搜索巨大。

这很可能是主因！启att式无效导致搜索空间爆炸。

修正 `_static_dist_map`：应该检查 **n**（前驱格）是否可站立，以及从 n→p 是否可进入（p 的 ONEWAY 方向、p 是否高墙/PIT）。而且对于"目标规划"，应该**假设 P_GATE 可打开**（即把 P_GATE 当作可通行），因为求解器可以推箱开板。否则 dist map 全 INF。

修正：
```
for dx,dy in NEI4:
   n=(p[0]-dx,p[1]-dy)
   d=(dx,dy)  # 从 n 到 p 的方向
   if n in dist: continue
   if sim.high(*p) or sim.tile(*p)=="PIT": continue   # p 必须可进入
   if sim.blocks_oneway(*p,d): continue
   if sim.high(*n) or sim.tile(*n)=="PIT": continue  # n 必须可站立
   if sim.occ(*n) in ("BOX","TNT") or sim.occ(*p) in ("BOX","TNT"): continue
   dist[n]=d0+1
```
但 `sim.high(*p)` 对 V 是 False ✓；对 P_GATE 关闭时是 True → 从 P_GATE 节点不会扩展其前驱。为了让 dist map 覆盖全图，应该**忽略门状态**（把 R_GATE/B_GATE/P_GATE 都视为可通行）用于启发式。这是常见的做法（relaxed problem）。我给 `_static_dist_map` 加参数 `relax=True`，用一个自定义 `walkable` 判断，忽略动态门（GATE 类）与占用层（BOX 可推）。

实现：
```
def _static_dist_map(sim, goal):
    def blocked_high(x,y):
        t=sim.tile(x,y)
        if t in HIGH_BASE: return True
        if t=="PIT": return True
        return False
    ...
    if blocked_high(*p) or blocked_high(*n): continue
    if sim.blocks_oneway(*p,d): continue
    dist[n]=d0+1
```
这样把门都当通路（relaxation），启发式可采纳（真实代价 ≥ relaxed 距离，因为真实可能要绕/开门），✓。

还要注意 `sim.tile(*p)=="PIT"` 阻挡；`MIMIC`（CHEST）不阻挡（可走但掉血）。

另外，`_heuristic` 里 `dv.get(K2,60)` 等使用 `sim.targets` 坐标 ✓。

另一个大问题：**A* 状态 key 不含"绝对 turn"**，只含 turn%12。但由于 `sim.status` 会在 turn>240 变 TIMEOUT，而 A* 合并了 turn=13 与 turn=25 的状态 —— 这条影响不大。

再一个：**A\* 每节点扩展 14 个动作，其中 BOMB/THROW/JUMP 会引入大量无用状态**。可以裁剪：
- 只在 `throws>0` 且地图有 SWITCH 时保留 THROW；
- 只在地图有 W/炮且 bombs>0 时保留 BOMB；
- JUMP 保留（跨坑有用）。
这能显著减少分支。

还有：**`WAIT` 动作在 A\* 里很重要**（调相位），保留。

再者，A* 的 `gscore` 用完整 key（含 dt/do/bombs），但 `sims` 存所有节点对象（每个含 dict），内存大。可以只存 `(parent_id, action)` 并在 pop 时从 key 重建 sim？不行，需要 sim 对象。可以限制节点数 30000。

让我先修 `_static_dist_map` 并加动作裁剪，再测。

另外，author 解 D=50 的问题也要查。先查哪一回合掉血。

让我并行做：修 dist map + 查 author 掉血。

先查 author 掉血（快速命令）。
````

## 050.1 · Thinking

```
t=24 蓝炮（period 4, turn 24 = 4*6 ✓）命中 (20,7)。BFS 应该避开 (20,7)（在 beams 中）。但为什么路径经过？

因为 `_static_beams` 计算时，LASER2_D(20,6) 向下扫，第一格 (20,7) 是 EMPTY → 加入 beams。所以 (20,7) 应在 blocked。但 BFS 走了 (20,7)？

啊，可能是 **退化分支**：第一次 BFS 失败（因为 beams 把通路全挡了），于是 `blocked -= beams` 重新 BFS，走射线格。让我检查第一次 BFS 是否成功。

从输出看 author 170 步，合理。但可能第一次 BFS 失败。让我检查。

另外注意：`_bfs_path` 的 allowed 集合包含 "EMPTY","K1","K2","V","P_GATE","PLATE"，但 `blocked` 里加入了所有非平地格。若 beams 挡住通往 K1 的唯一缺口，BFS 会失败 → 退化。

让我直接测。
```

## 052.1 · Thinking

````
确实：避开所有射线格后，K1/K2/V 不可达（因为某些必经窄道被射线完全覆盖）。所以退化分支生效，走了射线格，吃 50 伤。

这其实**不是坏事**：说明我的地图"必须真解 12 拍相位"——不存在完全避开射线的路径，任何通关都必须精确计时！这正是设计目标。author 解吃 50 伤通关也合法。但为了让自证更稳（且展示"精确计时"），我应该让 author 解通过**等待相位**做到 0 伤，而不是硬穿射线。这样也更符合"必须真解"的宣言。

不过 author 解只要求存活通关，50 伤完全合法。但有个风险：**如果实际评测引擎的激光判定与我的模拟器有细微差异（比如 exposed 包含中间格），author 解可能吃 100 伤死亡 → 废标！** 这很危险。让 author 解 0 伤更稳妥。

如何实现 0 伤？需要按相位规划：在射线格上只在"不开火拍"进入/停留。这需要一个带相位的 BFS（状态 (pos, phase)），且判定"该拍的 exposed 集合中所有格都不在当期开火炮的射线内"。

我可以写一个 `_timed_bfs`：状态 (x,y,t%12)，转移 = 移动一步（或 WAIT），检查该回合是否会受伤：
- 该回合的 exposed = {起点, 终点}（普通 MOVE 一步）。
- 当期开火炮：红 if t%3==0, 蓝 if t%4==0。
- 若 exposed 与任一开火炮射线格相交 → 该转移非法。
- 起点格在下一回合也可能被扫（但那是下一回合的事，由下一状态处理）。
- 另外，站在某格上"经过"该回合时（起点暴露）也会被扫 → 所以状态 (pos, phase) 的合法性还要求：在 phase 拍，起点格不被当期开火射线覆盖。这个在转移时检查（转移的 exposed 含起点）。

实现：BFS over (pos, phase)，边：
```
for act in MOVE_4 + WAIT:
   new_pos = pos + dir (若可走)
   t = phase (当前回合)
   periods = {3 if t%3==0} | {4 if t%4==0}
   if periods:
       lit = union of cells of cannons with those periods (静态，考虑门态最坏)
       if (pos in lit) or (new_pos in lit): illegal
   new_phase = (t+1)%12
```
注意：激光射线是静态的（除了门开关/箱子遮挡）。我用最坏情况（P_GATE 开，无 BOX 遮挡）计算 lit。但 P_GATE 关闭时挡射线 → 实际更安全。用最坏保守 ✓。

但这样 BFS 状态数 = 1040*12 = 12480，可行。找到从 spawn 到各目标（依次）的 0 伤路径，且拼接时相位连续。

不过还有一个复杂点：推箱动作会改变 plates_active → P_GATE 打开 → 射线变长。用最坏（开）✓。

另外 V 通关：到达 V 那一回合若 V 在射线内且当期开火 → 会掉血后才通关？规则：V 立即通关（先于 D）→ 不掉血！`step()` 里 chain 返回 CLEARED 后跳过 phase_c/d ✓。所以到达 V 的那一步是安全的（即使 V 在射线内）。不过 BFS 保守要求也行。

好，我改 `_author_path` 用带相位的 BFS。这样 0 伤且 ≤200 步（可能因为等待增加步数，需检查 ≤200）。

但相位 BFS 拼接多段时，相位要连续：段 0 从 phase=1（turn 1）开始，段 0 结束相位 p1；推箱动作占 1 回合 → phase p1+1；段 1 从该相位开始；等等。我需要在生成时跟踪 turn，逐段用起始 turn 做 BFS。

设计 `_timed_path(grid, start, goal, blocked, allowed, t0, beams_by_period)`：返回 (动作列表, 结束 turn)。BFS 状态 (pos, t)，t 从 t0 到 t0+200（限制）。用 (pos, t%12) 作为 visited（因为周期 12，且 t 增加；但 t 受 240 上限，路径 ≤200 → 不会超）。visited 用 (pos, t%12) 即可，因为周期性；但要记录实际 t 以便返回结束 turn。BFS 按层推进，每步 t+1。

实现 BFS：
```
q=deque([(start, t0)])
prev={(start,t0%12): None}  # 但 t0 可能 >12
```
为简单，用状态 (pos, t) 其中 t 从 t0 递增，visited 用 (pos, t%12)。记录 step_action 和 parent。BFS 找到 goal 时回溯动作序列，返回 (actions, t_found)。

每步检查：
```
for act in MOVE_ACTS+('WAIT',):
   nxt = pos + dir (or same for WAIT)
   if nxt not allowed / blocked: continue (WAIT 时 nxt=pos，pos 本身可能不在 allowed? 允许)
   # 判定伤害
   periods = ...
   if periods:
       lit = beams_red if 3 in periods else ... (合并)
       if pos in lit or nxt in lit: continue
   newt = t+1
   key=(nxt,newt%12)
   ...
```
注意 WAIT 时 nxt=pos，exposed={pos}；若 pos 在 lit → 不允许 WAIT（会被打）。所以"站在射线格等相位"也不行，必须站在安全格等。这符合真实物理。

`beams_by_period`：
- period 3: 所有 LASER_* 炮的射线（静态，P_GATE 开）。
- period 4: 所有 LASER2_* 炮的射线。
- phase 0（turn%12==0）：两者都开火 → lit = red ∪ blue。

我用 `_static_beams(grid, periods)` 返回对应集合。修改 `_static_beams` 支持参数。

然后 author 解拼接：
```
t = 1
seg0, t = timed_path(spawn,(16,10),...,t)
push: 需要检查该回合是否受伤（推箱时 exposed={start,(17,10)}？推箱动作勇者从 (16,10)→(17,10)，exposed={(16,10),(17,10)}）。若 (16,10) 或 (17,10) 在当期 lit → 需 WAIT 到安全拍。加入若干 WAIT 再 MOVE_R。
t += 1 + waits
seg1, t = timed_path((17,10), K1, ..., t)
...
```
推箱后 plates_active=True（P_GATE 开）→ 射线用最坏（开）✓，全程一致。

还有：箱子推到 PLATE 后，BOX 在 (20,10) 可能挡住某条射线 → 实际射线更短（更安全）。用最坏（不挡）✓。

另外，段间衔接时目标格（如 K1）在下一回合作为起点，若 K1 在 lit 且下回合开火 → 下一转移会被判非法 → BFS 会要求先在 K1 等待？不行，站在 K1 也会被扫。这就是真实约束：不能在射线格上停留到开火拍。BFS 会自然处理（从 K1 出发的第一转移若非法则无解）。所以路径必须"踩上 K1 后立即离开，且离开那一拍 K1 与下一格都不在 lit"。这正确。

好，实现。但需要检查 ≤200 步。之前 170 步（无等待）。加等待可能到 190-200，可能超。要留意。如果超 200，可以简化地图（减少绕行）或减少等待需求。

另一个风险：**如果 timed BFS 找不到 0 伤路径**（比如必须穿过一条被红蓝交替覆盖的单格走廊且没有连续安全拍），则回退到"允许吃 ≤50 伤"的路径或原退化路径。为稳妥，保留退化：若 timed 失败，用原 BFS（可能带伤）但确保 HP>0（吃 ≤50）。

嗯，但带伤的 author 解风险如前所述。让我先试 timed BFS，看能否 0 伤且 ≤200。

**先修 A\* 的 dist map**，这是求解器能工作的关键。然后修 author path。

让我一起改。

修改点：
1. `_static_dist_map`：relax 门/占用，正确检查 n 和 p。
2. `_plan_from_state`：动作裁剪（去掉不必要的 BOMB/THROW/JUMP），减少分支；增大效率；修 `if g > gscore.get(skey, INF)`（skey 变量名 ok）；限制 sims 大小；返回 None 时给 partial？先测。
3. 删除未使用的 `_solve`。
4. `_greedy_action` 清理残留。
5. `_static_beams` 支持 periods。
6. build_dungeon：用 timed BFS 生成 author 解。

先做 1、3、4、2（裁剪），测求解器。

动作裁剪逻辑：
```
acts = list(MOVE_ACTS) + ["WAIT"]
has_switch = any tile SWITCH
has_wall = any tile W / R_GATE / B_GATE / P_GATE / LASER... (可炸目标)
if root.h["jumps"]>0: acts += JUMP_*
if root.h["throws"]>0 and has_switch: acts += THROW_*
if root.h["bombs"]>0 and has_wall: acts += ["BOMB"]
```
但注意：**THROW 也可能用于击碎 MIMIC**（飞石命中 MIMIC 使其消失）或引爆炸药。为通用性，若地图有 CHEST 或 TNT 也可保留 THROW。简化：若 `has_switch or has_chest or has_tnt` 保留。

BOMB：若地图有 W 或炮座或 R/B_GATE 保留（炸墙开路）。

这样我的地图：有 W（91 格）、无 SWITCH、有 MIMIC（2）→ acts = 4 MOVE + WAIT + 4 JUMP + 4 THROW + BOMB = 14。嗯，仍然 14。为了效率，可以只在必要时启用 JUMP/THROW/BOMB：例如先用 5 个基础动作搜，若找不到再启用全部。实现"两阶段"：先跑 A* 用基础动作集（5 个），限时 0.8*budget；若无解，再用全动作集重跑。这样常见图很快。

实际上 A* 找不到解的主要原因可能是 dist map。先修 dist map 再测。

让我改代码。
````

## 054.1 · Thinking

```
现在改 `_plan_from_state`：动作裁剪 + 两阶段 + 删除 `_solve` + 清理 `_greedy_action`。

先看 `_plan_from_state` 当前代码，我需要精确替换。让我读一下相关行。
```

## 058.1 · Thinking

````
我发现一个**严重 bug** 在 `_plan_from_state`：`heapq.heappush(openh, (h0 + 0.0, 0.0, counter, root.key(), 0))` —— 初始项的 f = h0，但后续项 f = ng + 1.25*hh。不一致但无大碍。

更严重：`gscore` 用的是 `skey`（= c.key()），但 pop 出来的 `skey` 是**当前节点**的 key，而 `g` 是当前节点的 g。检查 `g > gscore.get(skey, INF)` 正确。

但 **`sims` 只保存被 push 的节点，且 nid=counter**。初始 root 是 0。OK。

问题在于：**A\* 找到 CLEARED 状态时，`sim.status` 是 "CLEARED"，但 push 时 `if c.status == "DEAD": continue` 只跳过 DEAD，CLEARED 会被 push ✓，然后 pop 时检测到 found ✓**。OK。

那为什么找不到解？启发式修好后再测。另外动作集全 14 导致分支太大。

让我删掉 `_solve`，改 `_plan_from_state` 支持动作集参数，并在 decide_action 里做两阶段：先用基础动作集（5）搜 60% 预算，失败再用全动作集。

另外，`_plan_from_state` 里 `if (nodes & 31) == 0 and time.monotonic() > deadline: return None` —— 超时直接 None。两阶段时第一阶段超时会消耗预算；需要给每阶段分配子预算。

实现：
```
def _astar(state, deadline, max_nodes, acts):
    ...
    return seq or None
```
decide_action:
```
budget = 1.55 if turn==1 else 0.40
t0=start
seq = _astar(state, t0+budget*0.55, 15000, basic_acts)
if seq is None:
    seq = _astar(state, t0+budget*0.95, 25000, full_acts)
```
但第二阶段如果也超时，返回 None → 贪心。

还要注意：`_astar` 里 `sims` 字典会占用大量内存；限制节点数。

另外**关键优化**：A* 的 key 包含 `dt`/`do`/`bombs`，但每次 `c.step()` 都会修改 `h["jumps"]` 等，key 里包含 jumps/throws/bombs_left，这让"同一位置不同跳跃次数"成为不同状态 → 状态爆炸（3*3*2=18 倍）。可以**从 key 中移除 jumps/throws/bombs_left**（近似），大幅减少状态。但会导致计划执行时资源不一致（比如计划用跳跃但真实已用完）——不过 sig 校验会捕获（sig 含 jumps/throws/bombs）。嗯，但如果在搜索中合并了不同资源的状态，输出的动作序列可能包含不可用的动作 → 执行时该动作无效（如 JUMP 无次数 → step 里不移动）→ sig 偏离 → 重规划。可接受，但不理想。

更好：保留资源在 key 中，但**只在基础动作集里不用 JUMP/THROW/BOMB**，这样资源不变。第二阶段用全动作集时才变化。这自然减少状态。

所以：第一阶段只 5 个动作（MOVE×4 + WAIT），key 里资源恒定 → 状态数 ~1040*12*4*2 = 100k（加上 hp/flip），可控。

好，实施。

还有一个重要的搜索效率问题：**`_Sim.clone()` 复制 dt/do（dict），`step()` 里每次 `high()` 调用 `plates_active()` 遍历 plates（1 个），OK。`rays()` 只在激光拍（6/12 拍）遍历 7 门炮 ×10 格 = 70 次 high()，每次 high 调 plates_active → 70 次遍历。还好。

估计每节点扩展 5 个动作 ~0.2ms → 1.5s 约 7500 节点。可能仍不够。需要更高效的启发式（weighted 1.25 → 可能够）。

再考虑：**用"分阶段目标"而非一次性找 CLEARED**。一次性 A* 要同时拿两把钥匙再到 V，状态空间大但启发式引导。可以改为分阶段：每阶段只找一个目标（K1 或 K2 或 V 或 推箱），阶段内 A* 状态空间小很多。这是更实际的做法。

设计 `_stage_astar(state, deadline, goals)`：阶段目标列表，例如：
- 若需要开板：阶段 0 目标 = plates_active True。
- 阶段 1：拿到 K1（或最近的钥匙）。
- 阶段 2：拿到另一把钥匙。
- 阶段 3：CLEARED。
每阶段用 A* 到"状态满足目标"，输出该阶段动作序列；然后从该状态继续下一阶段。这样每阶段搜索浅，总时间可控。

启发式：阶段内 h = dist(pos, stage_goal)（用 relaxed BFS），加上压板惩罚。对于"plates_active"阶段，h 需要估计推箱代价：min over (BOX, PLATE) of (dist(hero, push_behind_box) + dist(box,plate))。粗略用 `dist(hero, box) + dist(box, plate)`。但 A* 需要探索推箱动作；`sims` 状态含 boxes → 可行。

不过分阶段可能陷入局部最优（例如先拿 K1 再 K2 不一定最优），但能通关就行。

时间考虑：我先修好一次性 A* 并测试，如果不行再改分阶段。

让我先做最小修改：删除 `_solve`，把 `_plan_from_state` 改为 `_astar(state, deadline, max_nodes, acts)`，decide_action 两阶段。然后测。

同时修 `_greedy_action` 的残留行。

写替换。
````

## 062.1 · Thinking

```
现在测 A* 是否能解自己的图。同时也要修 author 解（timed BFS）与 `_static_beams` 支持 periods。

先测 A*。
```

## 064.1 · Thinking

```
还是无解。让我诊断 A* 的搜索过程：节点数、最好状态、是否曾拿到钥匙、是否曾开板。加 debug 输出。

可能是根本问题：**A\* 的 `sims` 字典 + `gscore` 检查有 bug**，导致搜索几乎不扩展。让我写一个诊断版 `_astar` 的复制（在命令里）统计。

或者更简单：检查 `_astar` 里 `if g > gscore.get(skey, INF) + 1e-9: continue` —— 初始 push 的 `skey = root.key()`，`gscore[root.key()] = 0.0`，`g=0.0` → 0 > 0 false ✓。

`heapq.heappush(openh, (ng + 1.3*hh, ng, nnid, ck, nnid))` —— 注意 tuple 第 3 个元素是 `nnid`（int），第 4 个 `ck`（tuple），第 5 个 `nnid`。初始 tuple 是 `(h0, 0.0, 0, root.key(), 0)`。比较时若 f 和 g 相同，比较第 3 个（int vs int）OK。

嗯，但 **`sims[nnid]` 的 key 是 `nnid = counter`，而 `counter` 在每次 push 时递增**——但 `parents[nnid] = (nid, act)` 里 `nid` 是父节点 id ✓。

问题可能是：**`_Sim.key()` 包含 `self.h["hp"]` 与 `dt/do`**，而 `dt` 在每次 `chain` 里若 tile 是 CRACK 会变化；但我的地图 CRACK 不在主路。不过 `do` 在推箱时变化。

更可能：**A\* 根本没朝目标走，因为 `_heuristic` 返回值有问题**。`_static_dist_map` 修好后，dist map 应该覆盖全图（relax 门）。让我检查 dist 值。

还有一个可能：**A\* 搜索中 `sim.status != "PLAYING"` 的节点被跳过，但 CLEARED 节点在 push 时 `c.status == "CLEARED"`，`c.step()` 已把 `turn += 1`，`key()` 里 `turn%12` 变化，OK。**

让我直接加诊断跑一次小型 A*（限制 2000 节点），打印：
- 扩展节点数
- 出现过的最小 heuristic
- 是否出现 keys 变化、plates_active
- 最优 g 的状态

写一个临时诊断脚本（放在文件夹里，或 python -c 内联）。用 python -c 复制 `_astar` 逻辑并加统计比较麻烦，不如临时修改 submission.py 加一个可选 debug 参数？我不想污染交付文件。

可以在测试脚本里 monkeypatch？我可以写 `v22_diag.py`（放文件夹）导入 submission 并复制 A* 循环加统计。写吧。

其实更快的办法：检查 `_static_dist_map` 输出。也许它把所有格的距离都算成很小（因为 `solid(p)` 里 `sim.tile(*p) in HIGH_BASE` —— `sim.tile(*p)` 传入的是 p 作为 (x,y) 解包，正确）。但如果 `goal` 是 V(36,13)，而 V 周围被 W 围（(36,12),(36,14),(37,13) 都是 W），只有 (35,13)=P_GATE（relaxed 后可通行）。BFS 从 V 扩展到 (35,13)（P_GATE 不是 HIGH_BASE，不是 PIT）→ dist=1；再从 (35,13) 扩展到 (34,13) → dist=2；... 应该能覆盖全图 ✓。

但 **`sim.blocks_oneway(*p, (dx,dy))`** 里 p 是当前格，(dx,dy) 是从 n 到 p 的方向。对于 ONEWAY 格 (24,12)=ONEWAY_R，从 n=(23,12) 到 p=(24,12) 方向 R ✓ 允许。BFS 里 `n = (p[0]-dx, p[1]-dy)`，方向 (dx,dy) 从 n 到 p ✓。

让我检查 dist map 的值和 A* 的节点扩展。写诊断脚本。

另外有一个我忽略的**重大问题**：`_Sim.step()` 在 `phase_d` 里若 hero 在射线格且当期开火会掉血；A* 会尽量避开，但**如果 spawn 附近或必经区被射线覆盖且没有安全拍**，搜索可能大量状态 DEAD。不过我的地图 author 解都能 50 伤通关，说明有路。

再一个可能：**A\* 的 `gscore` 用 `skey` 但 `sims` 用 `nnid`，两者不一致导致 pop 时 `sim = sims.get(nid)` 为 None？** 不会。

让我写诊断。
```

## 068.1 · Thinking

````
诊断结果：
- 距离正常（spawn→K1=50, spawn→K2=18, spawn→V=36；K1→K2=68, K2→V=52）。
- 搜索 14304 节点，1.55s 超时；状态里 keys_seen 有 (False,True) 即拿到 K2，plates_active True 有 3471 个状态（说明推箱成功过！）。best_h 在 K2 位置 (12,19)，keys=[False,True]，plates 已开。
- 但从未拿到 K1（True,False）或两把都齐。为什么？

因为启发式 `_heuristic` 在拿了一把钥匙后：
```
a = 0 if k[0] else dk1.get(p,60)   # k[0]=False -> dk1[p]
b = 0 if k[1] else dk2.get(p,60)   # k[1]=True -> 0
c1 = a + man(K1,K2) + dv.get(K2,60)
c2 = b + man(K2,K1) + dv.get(K1,60)
d = min(c1,c2)
```
c2 = 0 + 38 + dv(K1) —— dv(K1) 是从 K1 到 V 的距离，约 52？`man(K2,K1)=38`，`dv.get(K1)` 是从 K1 到 V 的 relaxed 距离。等等，`dv.get(sim.targets.get("K1", p))` = K1 到 V 的距离。c2 = 0 + man(K2,K1) + dv(K1) = 38 + dv(K1). 但这是"从当前位置（k2 已拿）到 K1 再到 V"的估计，其中 `b=0` 是错的——b 应该是"到 K2 的距离"，但 K2 已拿，所以为 0；c2 用 `man(K2,K1)` 是从 K2 到 K1 的距离，而不是从当前位置 p 到 K1 的距离！这是 bug：`c2` 应该用 `dk1.get(p)`（当前位置到 K1 的距离）。

同理 c1 = a + man(K1,K2) + dv(K2)，其中 a=dk1[p]（当前到 K1），man(K1,K2)=38 是 K1→K2 距离，dv(K2)= K2→V。这个 c1 合理。

但 c2 = b(=0) + man(K2,K1)=38 + dv(K1) —— 忽略了当前位置 p 到 K1 的距离，可能低估很多（如果 p 远离 K1）。低估是可采纳的，但会让 A* 优先探索"拿 K2 后原地不动"的状态，浪费搜索。不过不至于完全找不到 K1。

关键问题可能是：**A\* 因为 h 低估且 weighted 1.3，导致大量状态在 K2 附近徘徊**？best_h 在 (12,19) 说明确实到了 K2。

更可能：**K1 位于上部区域（y=3），被墙 y=5 隔开，只能通过缺口 x=38 到达**。而从 spawn 到 x=38 的路径要穿过中部带；中部带被激光射线覆盖，且路上有很多 CRACK/PIT 陷阱。A* 需要走 50+ 步才能到 K1，而搜索预算只够 14k 节点 → 深度不够。

h0 = 54.45（0.55 * 99），weighted A* 会优先扩展 f 小的节点。要到达 K1 需要 50 步，A* 在深度 50 附近需要扩展大量节点（因为每层有很多格子）。14k 节点可能不够。

**改进方向**：
1. **分阶段 A\***：先只求"拿 K2"（近，18 步）、"开板"（推箱）、"拿 K1"（远）、"到 V"。每阶段搜索深度小，节点数少。这是最有效的改进。
2. 或者提高 weighted 系数（1.3 → 2.0），更贪心，更快深入。但可能牺牲 0 伤。
3. 或者增加节点预算（但时间限制 1.55s，每节点 ~0.1ms → 14k）。

分阶段方案最好。让我实现 `_staged_plan`：

阶段列表：
- 若有 P_GATE 且未激活：stage "PLATES"（目标 plates_active True）。
- 拿钥匙：选择顺序。可以按"先近后远"：从当前位置到 K1/K2 的 relaxed 距离，选近的先。但要注意门的开关状态可能改变可达性。简单：先近后远。
- 最后 "V"（CLEARED）。

每阶段 A* 到"满足阶段目标"的状态，返回动作序列；把该状态作为下一阶段的起点（用 sim.step 推进），直到全部完成。

阶段 A* 的启发式：`_heuristic_stage(sim, goal_dist_map, stage_kind)`：
- 对钥匙/V 阶段：h = 0.55 * dist_map[pos]，加上"若需要开板但未开"的惩罚（但开板阶段在前，已完成）。
- 对 PLATES 阶段：h = 0.55 * (min over box/plate of (dist(hero, push_pos) + dist(box,plate)))。简化：h = 0.55 * min over (b,p) of (dist_hero_to_b + dist(b,p))，其中 dist 用曼哈顿或 relaxed map。但推箱需要勇者站在箱子后面；dist_hero_to_b 近似。

实际上，PLATES 阶段在诊断里 3471 个状态已开板，说明 A* 自然能找到（因为要到达 V 必须开板）。分阶段后更容易。

但注意：**阶段目标的判定**：
- 钥匙阶段：`sim.h["keys"][i] == True`。
- V 阶段：`sim.status == "CLEARED"`。
- PLATES 阶段：`sim.plates_active()`。

阶段 A* 的目标判定在 pop 时检查（或在生成 c 时立即返回）。为了效率，在生成子节点时若满足阶段目标，立即回溯返回。

实现：
```
def _stage_astar(sim, goal_test, hfun, deadline, max_nodes, acts):
    openh=[...]; ...
    while ...:
        pop sim
        if goal_test(sim): reconstruct and return seq
        expand...
```
注意 goal_test(root) 可能为 True（阶段已完成）→ 返回空列表。

阶段衔接：用一个 `_Sim` 对象累积，每阶段结束把动作执行到该 sim 上（用找到的 seq 重放），得到新的 sim，再用它构造 state 给下一阶段。但 `_astar` 从 state 构造 root；我可以直接传 sim 的 state()（会重建，开销小）。或者直接把 `_stage_astar` 改成接受 sim 对象。

我重构：`_stage_astar(sim, goal_test, h, deadline, acts)`，内部用 sim.clone() 扩展。返回 (seq, final_sim)。final_sim 通过重放 seq 得到（或直接保存目标节点的 sim）。

然后 `_plan_from_state(state, deadline, ...)`:
```
root = _Sim(state=state)
basic, full = _action_sets(root)
sim = root
all_seq = []
stages = build_stages(root)  # list of (goal_test, dist_map or h)
for (name, goal_test, hfun) in stages:
    budget_share = remaining_time / remaining_stages
    res = _stage_astar(sim, goal_test, hfun, deadline_stage, basic)
    if res is None: res = _stage_astar(sim, goal_test, hfun, deadline_stage2, full)
    if res is None: return None
    seq, sim = res
    all_seq += seq
return all_seq
```
时间分配：Turn1 1.55s，4 个阶段 → 每阶段 ~0.38s。可能不够（远阶段需要更多）。可以按阶段难度分配（远目标给更多）。或者用总 deadline，每阶段用 `deadline` 但内部限时 `min(deadline, now + share)`。

嗯，还有：**阶段顺序可能导致次优甚至不可行**（比如先拿 K1 再拿 K2，但拿 K1 后门关了导致 K2 不可达）。可以两种顺序都试，但时间不够。先按"近的先"。

另外，PLATES 阶段：如果没有 P_GATE，跳过。BENCH_WEAK 有 P_GATE，BENCH_STRONG 有 2 个 P_GATE + 3 PLATE。

对于 BENCH_STRONG 的 3 个 PLATE，需要推 3 个箱子 → Sokoban 较难，阶段 A* 状态含 boxes，可能仍慢。尽力。

让我实现分阶段。同时保持 `_astar` 作为"一次性"备用（也许不需要，删掉简化）。实际上分阶段更通用，我把 `_plan_from_state` 改为分阶段，保留 `_astar` 作为阶段搜索引擎（改成接受 sim + goal_test + hfun）。

重构代码：

```python
def _stage_search(sim, goal_test, hfun, deadline, acts, max_states=50000):
    openh=[]
    counter=0
    heapq.heappush(openh, (hfun(sim), 0.0, 0, sim.key(), 0))
    sims={0:sim}; parents={0:(-1,None)}; gscore={sim.key():0.0}
    counter=1; nodes=0
    while openh and nodes<200000:
        if (nodes & 15)==0 and time.monotonic()>deadline: return None
        f,g,_c,skey,nid=heapq.heappop(openh)
        if g>gscore.get(skey,INF)+1e-9: continue
        s=sims.get(nid)
        if s is None: continue
        nodes+=1
        if goal_test(s):
            seq=[]; cur=nid
            while parents[cur][0]!=-1: seq.append(parents[cur][1]); cur=parents[cur][0]
            return seq[::-1], s
        if s.status!="PLAYING": continue
        for a in acts:
            c=s.clone(); c.step(a)
            if c.status=="DEAD": continue
            dmg=max(0,s.h["hp"]-c.h["hp"])
            ng=g+1.0+0.35*dmg+(4.0 if a=="BOMB" else 0)+(0.15 if a=="WAIT" else 0)
            ck=c.key()
            if ng>=gscore.get(ck,INF)-1e-9: continue
            gscore[ck]=ng
            sims[counter]=c; parents[counter]=(nid,a)
            heapq.heappush(openh,(ng+1.3*hfun(c),ng,counter,ck,counter))
            counter+=1
        if len(sims)>max_states: return None
    return None
```

`hfun` 需要预计算 dist maps。阶段 h：
```
def make_h(sim, dist_map, plates_penalty=False):
    def h(s):
        d = dist_map.get((s.h["x"],s.h["y"]), 70)
        return 0.55*d
    return h
```
对 PLATES 阶段：
```
def h_plates(s):
    if s.plates_active(): return 0
    # 估计：到最近 BOX 的距离 + BOX 到最近未压 PLATE 的距离
    ...
```
计算 box 位置需要遍历 s.do/s.bo（最多 6 个），plate 位置 s.plates。用曼哈顿：
```
best = 1e9
boxes = [(x,y) for (x,y),o in s.bo.items() if s.occ(x,y)=="BOX"] ... 
```
注意 s.bo 是初始占用，s.do 是覆盖；要枚举所有格找 BOX 会很慢（1040 格/节点）。可以维护：从 s.bo 的 keys 加上 s.do 中 value=="BOX" 的 keys。实现：
```
def _boxes(s):
    out=set()
    for k,v in s.bo.items():
        if s.occ(*k)=="BOX": out.add(k)
    for k,v in s.do.items():
        if v=="BOX": out.add(k)
    return out
```
每个节点 O(6+small)，OK。

h_plates = 0.55 * (min over box b, plate p of (dist_hero[b] + dist(b,p)) + (num_plates-1)*8)，其中 dist_hero 用 relaxed map from hero? 需要 dist map to box —— 可以预计算从"所有 box 初始位置"的 dist map？简化用曼哈顿。

嗯，也许可行。

阶段顺序：
1. PLATES（若 P_GATE 存在且未激活）
2. KEY near（ relaxed dist 小的）
3. KEY far
4. V

但注意：如果先开板再拿钥匙，PLATES 阶段可能需要走到地图另一边推箱，然后回来。总步数增加，但 ≤240 应该 OK。BENCH_WEAK author 81 步，我的路径可能 100+ 步，仍 OK。

另一个考虑：**阶段目标"拿钥匙"时，若路上顺手拿到另一把钥匙，goal_test 只检查目标钥匙 → 会提前结束阶段，下一阶段仍会要求拿另一把（若已拿，goal_test 立即 True → 空序列）**。✓ 处理：每阶段开始先检查 goal_test(sim) 是否 True，是则跳过。

好，实现。同时删掉 `_astar`（或保留但不用）。为简洁，我把 `_astar` 替换为 `_stage_search`，并重写 `_plan_from_state`。

另外，`_heuristic` 函数可以保留但改用分阶段 h。我保留它作为备用（不用），或者直接删。为减少混乱，我重写这一段。

让我替换从 `_heuristic` 到 `_plan_from_state` 的整块。先读当前范围确认。

实际上我用 replace_in_file 替换 `_astar` + `_plan_from_state` 部分，并修改 `_heuristic` 为 `_make_h`。

让我写替换。
````

## 070.1 · Thinking

```
注意 `_plan_from_state` 里 `return out if sim.status == "CLEARED" else None`。`sim` 是最后阶段找到的 CLEARED 状态 ✓。但如果 stages 里所有阶段都被跳过（已 CLEARED? 不可能），sim=root。

还有个 bug：`kk.sort` 里 K1 的距离用 `maps.get("K1",{}).get(SPAWN,70)`（写死 SPAWN），应该用当前 hero 位置。修正为 `(root.h["x"], root.h["y"])`。

另外：`h_plates` 里 `max(0, len(s.plates) - sum(...))` —— 当所有板都被压时 plates_active 已 True，返回 0；否则惩罚。OK。

还有 `_stage_search` 里 `if len(sims) > max_states: return None` —— 45000 状态可能内存大但 OK。

`_plan_from_state` 的 `share` 计算：第一次 remaining=4（plates + 2 keys + V），deadline-now≈1.55 → share≈0.39。plates 阶段给 0.39s，若失败再给 0.08s 用 full。之后 remaining=3，share=(deadline-now)/3 约 0.39。V 阶段给全部剩余。

现在测。
```

## 072.1 · Thinking

````
1.125s 就返回 None（未用完预算），说明某个阶段搜索失败（返回 None）——`_stage_search` 返回 None 有两种情况：超时、或 openh 耗尽（无解）。1.125s 说明前面阶段花了一些时间，然后某阶段 openh 耗尽（基础动作集下无解），full 也失败，直接 return None。

让我加诊断：在 `_plan_from_state` 里打印每个阶段结果。我可以用一个临时脚本复制逻辑，或在 submission.py 里加一个模块级调试开关……更简单：写个诊断脚本调用 `_stage_search` 分阶段打印。

让我写 `v22_diag2.py`（放文件夹）。

阶段诊断：
```
root = _Sim(state=st)
stages 手工构造同 _plan_from_state
for each: res=_stage_search(...); print(name, None if res is None else (len(seq), sim.status, pos, keys, plates))
```
并打印每阶段耗时、返回时 openh 是否耗尽（我需要知道是超时还是无解）。`_stage_search` 返回 None 时不区分。我可以在诊断脚本里复制一份带统计的 `_stage_search`。

或者临时给 `_stage_search` 加一个全局 debug flag（比如模块变量 `_DEBUG`），在返回 None 时 print。但这会污染交付文件（虽然可以之后清理）。我用诊断脚本复制逻辑更干净。

写 diag2。
````

## 076.1 · Thinking

```
K1 阶段超时（0.75s 限制）。从 K2(12,19) 到 K1(34,3) 需要绕墙（经 x=1 缺口回中部，再 x=38 缺口到上部），距离 68 步。搜索深度 68，节点数大。需要更强的启发式或更高效的搜索。

改进方向：
1. **提高 weighted 系数**（1.35 → 2.5~3.0），让搜索更贪心、更快深入。牺牲最优性但能找到解。
2. **启发式用精确的 relaxed 距离**（已经是），但 `0.55*d` 缩放让它太弱。改为 `1.0*d`（标准 A*），配合 weighted 1.5。0.55 是为了"可采纳"因为 JUMP/滑行可多格，但基础动作集只有 MOVE/WAIT，每步最多 1 格（除了 ICE/SPRING 滑行）—— 在基础动作集下 dist map（relaxed）是真实距离下界，可以用 1.0*d。滑行会让真实距离更短，所以 1.0*d 可能高估 → 但 weighted A* 不要求可采纳，只要找到解。用 1.0*d 会显著加速。

让我把 `mk_h` 改为 `1.0 * dm.get(...,70)`，weighted 系数从 1.35 提到 1.8。h_plates 也调整。

另外，阶段顺序：先 K2（近）再 K1（远）导致 K1 阶段从地图下方出发，路程 68 步。若先 K1 再 K2：spawn→K1 50 步，K1→K2 68 步，K2→V 52 步，总 170（与 author 一致）。差不多。

还有一个关键优化：**A\* 状态包含 hp、flipped、dt/do/bombs、jumps/throws/bombs_left**，在基础动作集下这些大多不变，但 `turn%12` 变化 → 状态数 ×12。距离 68 的路径，每层 ~几十个候选 → ~几千到上万节点。0.75s 内 5552 节点，不够。提速方法：
- 减少每节点开销（clone + step + rays）。
- 提高启发式权重。

让我先试 1.0*d + weight 2.0，看是否能解。

另外，可以把 K1 阶段预算给更多（阶段预算按剩余阶段均分，K1 是第 3 阶段，remaining=2 → share=(1.55-0.31)/2≈0.62s）。诊断里我给了 limit/4=0.75s，差不多。

还有：**Turn 1 有 1.55s，但如果分阶段都成功，总时间可能够**。K1 阶段需要 >0.75s。可以给 K1 更多时间：按阶段 estimated distance 分配预算，而不是均分。例如 K1 距离 68，K2 距离 18，V 52 → 按比例分配。实现：给每个阶段一个 weight（基于 relaxed 距离），share = total_remaining * w_i / sum(w)。

更简单：把 weighted 系数调大先试。

让我改：
- `mk_h`: `return 1.0 * dm.get(..., 70)`
- `_stage_search` weighted: `1.35` → `1.8`
- `h_plates`: `0.55*min(best,120)` → `0.8*min(best,120)`（plates 阶段很快，无所谓）

测试。
```

## 082.1 · Thinking

````
太好了！0.016s 解出，141 步，100 HP，0 伤，CLEARED。加权启发式让它非常贪心且高效。

但要注意：**过度贪心可能导致在某些图上找不到解**（比如需要绕远路或等待相位）。不过我们有 full 动作集回退 + 贪心降级。而且 Turn>1 会重规划。

现在跑完整测试：own + golden + bench。

自建图的 author 解仍有 D=50，需要改成 0 伤（用 timed BFS）。但既然求解器能在 0.016s 解出 141 步 0 伤的序列，我可以让 `build_dungeon()` 直接调用求解器生成 author_solution！但 build_dungeon 需要 state；可以构造 `_Sim(grid=grid).state()` 然后调用 `_plan_from_state(..., deadline=now+1.0)`。build_dungeon 限时 2.0s，求解器 0.016s → 完全可行！而且保证 0 伤、≤200 步。

这是最优雅的方案：**自证解由通用求解器生成**，不是手工路径。这样：
- 保证与引擎一致（0 伤通关）
- 展示"真解"
- 代码更简洁（可删掉 `_bfs_path`/`_acts_from_path` 的复杂逻辑？保留做回退）

但要小心：评测时 build_dungeon() 会被调用，若 `_plan_from_state` 因某种原因超时/失败，需要有回退（用静态 BFS 路径）。我保留现有 BFS 路径作为回退，主路径用求解器。

实现：
```
# 在所有陷阱放置完成后
sim0 = _Sim(grid=grid)
st = sim0.state()
try:
    seq = _plan_from_state(st, time.monotonic()+0.9, 20000, time.monotonic())
    # 验证
    if seq and len(seq) <= 200:
        v = _Sim(grid=grid)
        for a in seq: v.step(a)
        if v.status == "CLEARED" and v.win_turn == len(seq) and v.h["hp"] > 0:
            author = seq
except Exception:
    pass
```
注意 `_plan_from_state` 内部会 check `sim.status == "CLEARED"` 才返回。✓

但要小心：**求解器生成的序列可能 >200 步**（141 步，OK）。若 >200，用 BFS 路径（170 步）或截断。截断不行（必须恰好最后一步通关）。用回退 BFS 路径。

还有一个风险：评测环境里 `build_dungeon()` 被调用时 `time.monotonic()` 可用 ✓。

另外，求解器生成的序列可能包含 WAIT/JUMP/THROW 等，但都是合法动作 ✓。

让我修改 build_dungeon：在 `return` 前加入求解器生成 author。同时保留 BFS 路径作为 `fallback_author`。

需要先确认撒陷阱后求解器仍能 0 伤解出（陷阱可能挡路）。跑一次测试。

让我改代码。

另外还要修 `kk.sort` 里 K1 距离用 SPAWN 的 bug。

还有：`_plan_from_state` 返回 `out if sim.status == "CLEARED" else None` —— 若所有 stages 都完成，sim 是最后 V 阶段的 CLEARED 状态 ✓。

改 build_dungeon。让我读当前 build_dungeon 尾部。
````

## 086.1 · Thinking

````
现在改：在 return 前用求解器生成 author_solution，并验证；若失败用 fallback_author。

注意：`golden` 集合用于撒陷阱，若用求解器路径，最好也用求解器路径作为 golden（避免陷阱挡住求解器路径）。但求解器在撒陷阱前生成路径，撒陷阱避开该路径 → 撒完后路径仍有效。这样更好。

所以顺序改为：
1. 生成地图骨架（墙/地标/推箱/激光/ONEWAY），撒陷阱之前。
2. 用 `_plan_from_state` 生成路径 `cert`，得到 `golden = set of visited positions`（需要重放 cert 记录位置）。
3. 撒陷阱避开 golden。
4. 撒完后再用 `_plan_from_state` 重新生成最终 author_solution（因为陷阱可能改变最优路径），验证 0 伤通关且 ≤200。
5. 若失败，用 fallback BFS 路径。

这样代码更简洁，且 author 解保证 0 伤。但 BFS fallback 代码仍保留（防御）。

不过要小心：**求解器在撒陷阱前生成的路径用于 golden，撒陷阱后重新求解** —— 两次求解都很快（0.016s），build_dungeon <2s ✓。

让我重构 build_dungeon 的后半部分。我会替换从 `beams = _static_beams(...)` 到 return 的整块。

新代码：
```
    beams = _static_beams(grid, plates_open=True)
    # 先用通用求解器求一条零伤路径，用其足迹作为"不可布雷"保护带
    cert = _certificate(grid, 0.9)
    if cert:
        golden = _footprint(grid, cert)
    else:
        # 回退：静态 BFS 走廊
        ... (原逻辑)
    # 撒陷阱避开 golden
    ...
    # 最终证书：撒陷阱后重新求解
    final = _certificate(grid, 1.2)
    if final is None:
        final = fallback_author
    return {... "author_solution": final}
```

`_certificate(grid, budget)` 辅助函数：
```
def _certificate(grid, budget):
    try:
        s0 = _Sim(grid=grid)
        st = s0.state()
        t0 = time.monotonic()
        seq = _plan_from_state(st, t0 + budget, 20000, t0)
        if not seq or len(seq) > MAX_AUTHOR_STEPS:
            return None
        v = _Sim(grid=grid)
        for a in seq:
            if v.status != "PLAYING": break
            v.step(a)
        if v.status == "CLEARED" and v.win_turn == len(seq) and v.h["hp"] > 0:
            return seq
    except Exception:
        pass
    return None
```
注意 `_plan_from_state` 里 `sim.status == "CLEARED"` 才返回 out ✓。

`_footprint(grid, seq)`：重放并记录每个 visited 位置（含起点）。
```
def _footprint(grid, seq):
    s = _Sim(grid=grid)
    out = {(s.h["x"], s.h["y"])}
    for a in seq:
        s.step(a)
        out.add((s.h["x"], s.h["y"]))
        if s.status != "PLAYING": break
    return out
```

fallback_author 用原 BFS 逻辑（保留但简化：只在 cert 为 None 时计算）。

让我写替换。为减少复杂度，我保留原 BFS 段作为 fallback（放在一个 `if cert is None` 分支里）。但原 BFS 代码较长。我可以只保留一个简化 fallback：直接返回 `[]`？不行，必须有合法证书。

其实 cert 几乎必然成功（0.016s）。fallback 用原 BFS 路径更稳妥。保留。

我重写 build_dungeon 后半部分为：

```
    beams = _static_beams(grid, plates_open=True)
    cert = _certificate(grid, 0.9)
    # 静态 BFS 回退走廊（仅在求解器异常时使用），同时用于确定保护带
    allowed = {...}
    blocked = ...
    seg0..seg3 ... (原逻辑)
    fallback_author = ...
    if cert:
        golden = _footprint(grid, cert)
    else:
        golden = set(...) | ...
    # 撒陷阱
    ...
    # 合规
    ...
    # 最终证书
    final = _certificate(grid, 1.2) or fallback_author[:MAX_AUTHOR_STEPS]
    return {...}
```

注意 `fallback_author` 可能 >200 步 → 截断会破坏"恰好最后一步通关"。若 fallback 也 >200，危险。但 cert 应该总成功。为保险，若 fallback >200，则... 可以缩短路径（简化地图）。实际上原 BFS 170 步 ✓。

好，写替换。同时修 `kk.sort` 的 SPAWN bug。

先修 kk.sort。
````

## 090.1 · Thinking

```
现在改 build_dungeon 后半部分：用 cert 的 footprint 作为 golden，最后用 _certificate 生成 author。

替换从 `beams = _static_beams(...)` 到 `return {...}`。

注意：`_certificate` 要求 trap_damage == 0.0（零伤）。求解器生成 141 步 0 伤 ✓。但撒陷阱后可能路径变化，仍应 0 伤（求解器避开伤害）。若求解器失败（返回 None），用 fallback BFS 路径（带 50 伤，但仍合法）。

不过 `_certificate` 里 `v.trap_damage == 0.0` 这个要求可能过严（有些地图无法 0 伤通关）。对于我自己的地图，应该能。但如果不能，会导致每次都用 fallback（带伤）。算了，为稳妥，我放宽为 `v.h["hp"] > 0`，但优先 0 伤。其实 0 伤更稳，保留；fallback 兜底。

写代码。
```

## 092.1 · Thinking

```
现在跑 own + golden 测试。
```

## 094.1 · Thinking

```
太好了：
- 自建图：合规、造价 1740G、141 步零伤自证、出生准入通过、自战 141 步通关 100HP，最慢单步 0.046s。
- Golden vectors 全部符合（GV22_01/02/03/04a/05/05b/07/08）。GV22_04b、06 未测（可选）。

现在跑基准（BENCH_WEAK / BENCH_STRONG + part1 14 图）。这是关键。
```

## 096.1 · Thinking

````
结果分析：
- **BENCH_WEAK: CLEARED 69 步 100HP**（弱基准参考 81 步 100HP）→ 超过弱基准 ✓ 展示分为正。
- **BENCH_STRONG: TIMEOUT** —— 没打过强基准。用户提示"打过强基准也不代表强，它只是一个正常基准"，说明强基准是正常基准，打不过会扣分？展示分 = 原始均分 - 弱基准均分；弱基准是 0 水位线，强基准只是"检验"。打不过强基准不直接扣分，但正赛地图可能类似强基准难度。要尽力。
- part1 14 图：10 通关、0 阵亡、4 超时（OFFICIAL_02、argon、glm、sol）。
- 有几个 worst_step 超过 0.5s（0.625、1.578、1.593、0.469）—— 这**违反 Turn>1 的 0.5s 限制**！会导致 WAIT 甚至 DQ。必须修。

先看超时原因：
1. **单步耗时超标**：`OFFICIAL_02` 0.625s、`hunyuan` 1.578s、`sol` 1.593s、`argon/glm` 0.625s、`BENCH_STRONG` 0.469s。这些是 Turn>1 重规划超时（budget 0.40 + 开销），或者 Turn1 1.55+ 开销 = 1.59s（Turn1 允许 2.0s，所以 1.59 OK）。但 0.625s 出现在 Turn>1（超 0.5s）→ 违规。

`hunyuan` 1.578s 可能是 Turn1（允许 2.0s）✓，但 `sol` 1.593 也可能是 Turn1。OFFICIAL_02 0.625s 呢？可能是 Turn1（0.625 <2.0 但 >0.5 只在 Turn1 允许）。需要区分。让我在测试里记录最大单步出现在哪个 turn。

无论如何，我要确保 Turn>1 严格 <0.5s（留余量，设 budget=0.35 且 `_stage_search` 检查更频繁）。当前 `budget = 0.40`，加上 `_plan_from_state` 的 full 回退 `min(deadline, dl + 0.20*share)` 可能超过 deadline？`min(deadline, ...)` ✓ 不会超。但 `_stage_search` 里时间检查每 16 节点一次，若单个节点循环耗时（比如 14 个动作 × clone/step）可能 0.01s，最坏超 0.01s，不至于 0.625s。

0.625s 可能是 Turn1 的 `budget=1.55` 但 `_plan_from_state` 提前返回？不对，0.625 <1.55。也可能是某个 Turn>1 的 `_plan_from_state` 用了 `budget=0.40`，但实际 0.625 > 0.40 → 说明超时检查失效或 `_stage_search` 第二阶段用了 `dl + 0.20*share` 超过了 deadline？`min(deadline, dl + 0.20*share)` 保证 ≤ deadline。但 `deadline` 是 `start + 0.40`，而 `start` 是 decide_action 开始时间；`_plan_from_state(state, deadline, ..., start)` 里 `span = deadline - start`；`dl = now + share`，`now` 可能已晚；`min(deadline, dl+...)` ✓。

嗯，可能是 `_plan_from_state` 里 **`_stage_search` 的 `time.monotonic() > deadline` 检查只在 `(nodes & 15)==0`**，若 `openh` 元素很多且 `g > gscore` 导致大量 `continue`（这些不计入 nodes！），时间检查不触发 → 可能长时间不检查时间。看代码：
```
while openh and nodes < 200000:
    if (nodes & 15) == 0 and time.monotonic() > deadline: return None
    pop...
    if g > gscore...: continue   # nodes 不增加 → 时间检查条件 (nodes&15)==0 一直为真，但每次循环都会检查时间！
```
实际上 `(nodes & 15)==0` 当 nodes=0 时恒真，直到 nodes 变化。若 nodes 卡在某个非 16 倍数，时间检查不执行 → 可能超时。例如 nodes=100 且后面全是 `continue`，时间检查永远不触发 → 无限循环直到 openh 耗尽。这可能造成 0.625s。

修：每 N 次循环检查时间（用单独的 loop counter），而不是依赖 nodes。

另外，**BENCH_STRONG TIMEOUT** 且 wall 32s（240 回合 × ~0.13s），说明每回合都在重规划但找不到解 → 贪心兜底 → 无法通关。需要改进对强基准的求解。

还有 part1 的 4 个 TIMEOUT（OFFICIAL_02、argon、glm、sol）——这些地图需要**炸墙/翻门/推箱**等操作。例如 OFFICIAL_02 是"红门炸弹生死锁"：K1/K2 被 W 墙围，需要 BOMB 炸开；V 前有 R_GATE 需 SWITCH 翻门。我的求解器 full 动作集包含 BOMB 和 THROW，但分阶段启发式可能没引导去炸墙（因为 relaxed dist map 把 W 当墙 → dist 到 K1 是 INF → h=70 常数 → 搜索盲目）。

**这是关键缺陷**：`_static_dist_map` 把 W 当 solid，但 W 可以被 BOMB 炸开。应该把可炸的 W / R_GATE / B_GATE / 炮座视为"代价更高但可通行"，这样 dist map 能给出引导。

改进 `_static_dist_map`：加入"可炸代价"，用 Dijkstra（0-1 BFS 或小堆）而非 BFS：
- 普通格 cost 1
- W / R_GATE / B_GATE / P_GATE / 炮座 cost `+6`（炸墙需要放炸弹 + 等待 3 回合 + 移动，约 6 步）
- T_W / PIT cost INF（不可通过）
这样距离图能引导"炸墙"。

同时，阶段搜索里 BOMB 动作需要真的能炸开墙：我的 `_Sim.explode` 会把 W → EMPTY ✓，但 BOMB 需要 3 回合（timer 3→2→1→0 爆炸），且勇者要远离避免 -50。A* 会处理（cost +4）。

不过 OFFICIAL_02 的 K1 被 W 三面围（(20,4)=W,(19,5)=W,(21,5)=W,(20,6)=W），需要炸开一格。BOMB 放在旁边，3 回合后炸开。可行。

另外 R_GATE(34,13) 挡 V，需要 SWITCH(4,13) 翻转（勇者踩上或 THROW 命中）。分阶段 A* 里 THROW 动作需启用（有 SWITCH ✓），但启发式不知道要翻门 → 可能找不到。改进：dist map 把 R_GATE/B_GATE 视为可通行（relax），这样 h 会引导到 V 附近，然后 A* 发现门关着会尝试 THROW/踩 SWITCH。但启发式引导的方向是"向 V 走"，SWITCH 在 (4,13) 远离 V，A* 可能不会去踩。不过 THROW 可以从远处打 SWITCH？SWITCH 在 (4,13)，V 在 (35,13)，距离 31 > 飞石 6 格射程。所以必须走回 (4,13) 踩开关。这需要"知道要翻门"。

改进：在分阶段规划里，若存在 R_GATE/B_GATE 且当前门态关闭、且目标被门阻挡，增加一个额外阶段："翻转门"（goal_test: flipped == needed）。但这需要知道哪个 flip 状态是需要的。可以简单加阶段：`("flip", lambda s: s.flipped != root.flipped, h_to_switch)`，其中 h_to_switch 用 dist map 到最近 SWITCH。但并非所有图都需要翻门（有些图 SWITCH 是陷阱）。加这个阶段可能导致无谓绕路，但代价可控。

更稳妥：**在 V 阶段的启发式里加"门状态"惩罚**：若 V 被关闭的门包围且 flipped 不对，h 加一个到 SWITCH 的距离。复杂。

考虑到时间，我优先解决：
1. **单步耗时 >0.5s**（违规，必须修）。
2. **dist map 支持炸墙**（提升 OFFICIAL_02 / carbon / 等）。
3. **BENCH_STRONG**：尝试改进（3 个 PLATE 推箱）。
4. part1 的 argon/glm/sol 超时：这些图有大量 W 墙和激光，可能类似问题。

让我先修时间检查与 budget，再改 dist map。

**修时间检查**：在 `_stage_search` 加 `loops` 计数，每 32 次循环检查时间。

**budget**：Turn>1 设 0.30（留 0.2s 余量给开销）。Turn1 设 1.55（<1.6 安全线）。

另外，`decide_action` 里若 plan 校验成功（缓存命中），直接返回 O(1)，不耗时。只有重规划才耗时。TIMEOUT 的图之所以每回合 0.4s，是因为 plan 一直失效（重规划找不到解 → 贪心 → plan=[act]，idx=1 后下回合又重规划）。应该改：当重规划失败时，**缓存贪心策略若干回合**，避免每回合重跑 A*。例如 `memory["cooldown"] = turn + 8`，在冷却期内直接用 `_greedy_action`（O(几毫秒)），冷却后再尝试全规划。这样单步耗时大幅降低。

实现：
```
if memory.get("cooldown",0) > turn: 
    return _greedy_action(_Sim(state=state))
```
但 `_greedy_action` 每次构造 `_static_dist_map`（BFS 1040 格）→ ~1ms，OK。

还要注意：`_greedy_action` 目前只在 MOVE+WAIT 里选，且用 `_static_dist_map`（把 W 当墙）→ 对需要炸墙的图会原地打转。但至少不违规。

**改进贪心**：加入 JUMP/THROW/BOMB 候选？可以，但保持简单。

让我先做这些修复，然后重测。

**dist map 支持炸墙**：改用 Dijkstra，代价：
```
def _static_dist_map(sim, goal):
    dist={goal:0}; heap=[(0,goal)]
    while heap:
      d,p=heappop
      if d>dist[p]: continue
      for n in neighbors (predecessor):
         # 从 n 走到 p
         if solid(n) or solid(p): continue  # solid = T_W or PIT (and border)
         if blocks_oneway(p, dir): continue
         w = 1
         if tile(p) in BREAKABLE or tile(n) in BREAKABLE: w = 5
         nd = d + w
         if nd < dist.get(n,INF): update
```
BREAKABLE = {"W","R_GATE","B_GATE","P_GATE"} | LASER/LASER2 炮座 | TNT occupant? 简单用 W + gates + 炮座。

但注意：把 W 视为可通行会让启发式**低估**（真实需要炸墙 6+ 步，估算 5）→ 可采纳 ✓。而且能引导 A* 朝目标走。

不过对有 195 个 W 的 CARBON 图，dist map 会穿过墙 → 启发式可能引导走向墙 → A* 会尝试 BOMB。可能有效。

还有 **ONEWAY**：`blocks_oneway(p, dir)` 已考虑。

**PIT**：不可通行（除非 BOX 填坑），视为 solid。但 BENCH_STRONG 有两格 PIT(25,13),(26,13) 需用 BOX 填或 JUMP 跨。若视为 solid，dist map 会绕行（可能绕不过 → INF → h=70 常数）。可以允许 PIT 以高代价通过（cost 8，表示填坑/跳跃）。这样 h 更合理。我把 PIT 也纳入 BREAKABLE（cost 8）。

嗯，但 `solid(p)` 里排除 PIT 会让 dist map 直接穿过深渊，启发式严重低估 → A* 可能被误导。用加权 Dijkstra 代价 8 就好。

好，实现 Dijkstra 版本。

另外 **BENCH_STRONG 的 3 PLATE**：阶段 "plates" 的 goal_test 是 `s.plates_active()`（3 个板全被 BOX 压）。启发式 `h_plates` 只估计单个 box→plate，且 A* 状态含 boxes。搜索空间大。可能 0.4s 不够。给 plates 阶段更多预算（Turn1 1.55s，分阶段 share 均分 4 阶段 → 0.39s；plates 阶段可能需要更多）。可以按阶段类型分配：plates 给 40% 预算。

不过 BENCH_STRONG 还涉及 R_GATE(20,7)、SWITCH(15,13)、ONEWAY 等。复杂。尽力而为。

**关于用户提示**："打过强基准也不代表强，它只是一个正常基准" —— 我理解为：不要为了过强基准而硬编码，要写通用求解器；强基准只是普通检验。所以我应该专注于通用能力提升（炸墙、翻门、推箱），而不是特化。

让我实施修复。

先改 `_static_dist_map` 为加权 Dijkstra。注意它被调用多次（每个阶段 3 次 + greedy 多次），Dijkstra 用堆 1040 节点，很快。

代码：
```
BREAKABLE = {"W","R_GATE","B_GATE","P_GATE"} | HIGH_BASE 里 LASER* (already), plus PIT
def _step_cost(t):
    if t == "PIT": return 8.0
    if t == "W" or t in ("R_GATE","B_GATE","P_GATE"): return 5.0
    if t.startswith("LASER"): return 6.0
    return 1.0
```
`solid` 只 T_W（外框+内墙）和边界外。PIT 允许（cost 8）。

```
def _static_dist_map(sim, goal):
    import heapq (already)
    dist={goal:0.0}
    pq=[(0.0, goal)]
    while pq:
        d,p=heapq.heappop(pq)
        if d>dist.get(p,INF)+1e-9: continue
        cp=_step_cost(sim.tile(*p))
        if cp>=INF: continue
        for dx,dy in NEI4:
            n=(p[0]-dx,p[1]-dy)
            if not in bounds: continue
            cn=_step_cost(sim.tile(*n))
            if cn>=INF: continue
            if sim.blocks_oneway(*p,(dx,dy)): continue
            nd=d+max(cp,cn)   # 进入 p 的代价 + 站在 n 的代价？
            ...
```
嗯，代价设计：从 n 走到 p 的成本应该是"进入 p 的成本"（p 是目标格）。但 Dijkstra 反向（从 goal 到 n），边 n→p 的成本 = cost of entering p。所以 `nd = d + cp`。但起点 n 若本身是 W，站在上面也难 → 用 `max(cp, cn)` 或 `cp + (cn-1)*0.5`。简单用 `cp`，并把 n 的 solid 检查（T_W）保留。

`cost(t)`:
- T_W → INF (skip)
- PIT → 8
- W / gates / 炮座 → 5
- otherwise → 1

这样启发式 h = dist（可能高估吗？真实一步 MOVE 到普通格 cost 1，到 W 需要 BOMB 若干步 ≥5；滑行可能一次多格 → 真实代价可能小于 dist（因为 dist 假设每格 1 步，但 ICE 可滑多格）→ h 高估。weighted A* 不要求可采纳，能找到解即可）。

好，实施。

同时修 `_stage_search` 时间检查与 `decide_action` 冷却。

让我批量替换。
````

## 098.1 · Thinking

```
注意：`_heuristic` 函数现在还在但不再被 `_plan_from_state` 使用（我用 `mk_h`）。`_heuristic` 只被 `v22_diag.py` 调用（诊断工具），交付文件里是死代码。可以保留（无害）或删除。稍后清理。

现在修 `_stage_search` 时间检查。
```

## 100.1 · Thinking

````
现在修 `decide_action`：
- budget Turn>1 改为 0.30。
- 加冷却机制（重规划失败后若干回合用贪心，避免每回合重跑 A*）。
- 记录最大单步耗时到测试（测试脚本已有 worst）。

实现：
```
turn = ...
budget = 1.55 if turn==1 else 0.30
deadline = start + budget
if memory.get("cooldown", 0) > turn:
    sim = _Sim(state=state); act = _greedy_action(sim)
    memory["plan"]=[act]; memory["sigs"]=[sig]; memory["idx"]=1
    return act
... 
seq = _plan_from_state(...)
if seq: ... return
# 失败
memory["cooldown"] = turn + 10
act = greedy...
```
但注意：如果 Turn1 规划失败，设置 cooldown=turn+10，则 Turn2..11 都贪心，Turn12 再尝试。合理。

另外，plan 缓存命中时也要检查 cooldown？如果 plan 有效，直接返回（优先）。把 cooldown 检查放在 plan 校验之后。

还有：**如果 plan 有效但很长（141 步），每回合 O(1)** ✓。

让我改。也把 `_plan_from_state` 的 `start` 传对。

当前 decide_action 代码：
```
        budget = 1.55 if turn == 1 else 0.40
        deadline = start + budget
        sig = ...
        plan = memory.get("plan"); idx=...; sigs=...
        if plan and ... and sigs[idx]==sig: return plan[idx]
        seq = _plan_from_state(state, deadline, 20000)
        ...
```
改为传 start，并加 cooldown。

另外 `_greedy_action` 里 `_static_dist_map` 现在是 Dijkstra（heap），每次调用 3 个目标 × 1040 节点 → 几 ms，OK。

写替换。
````

## 104.1 · Thinking

```
还要清除 cooldown 当 plan 成功时（避免 stale cooldown 影响后续重规划）。在成功设置 plan 后加 `memory["cooldown"] = 0`。

另外测试脚本需要记录"最大单步出现在哪个 turn"，以判断是否违规。让我改测试脚本的 play 返回 worst 与 worst_turn。

先改 submission 的 cooldown 清除。
```

## 106.1 · Thinking

````
现在改测试脚本记录 worst_turn，并重跑。也检查 BENCH_STRONG 的规划诊断。

先改测试脚本 play() 返回 worst 与 worst_turn（保持接口兼容：`sim, worst, acts`，我改为返回 4 元组会破坏调用处。改为在 play 里打印 worst_turn，或返回 (sim, worst, acts, worst_turn) 并更新调用）。简单：在 play 里加一个全局变量或打印。我改成返回 4 元组并更新两处调用。

其实最直接：在 `play` 里当 dt > worst 时记录 `wturn = sim.turn`，并 print 一行 "worst step at turn X"。然后返回不变。让我加个 print。

修改测试脚本：
```
worst = 0.0; worst_turn = 0
...
if dt > worst: worst=dt; worst_turn=st['turn']
...
print(... )  # 在调用处
```
返回 4 元组更清晰。让我改。
````

## 118.1 · Thinking

````
好消息：所有 worst_step 都在 @t1（Turn 1，允许 2.0s，最大 1.594s ✓）。Turn>1 都很快（cooldown + plan 缓存生效）。所以**时限合规**。

但结果变差了：
- part1 hunyuan（我上半场的图）从 CLEARED 229 → TIMEOUT。
- argon/glm 从 TIMEOUT → DEAD（贪心走进陷阱死了）。
- carbon 从 157 → 184，hydrogen 81（不变）。
- OFFICIAL_02 仍 TIMEOUT。

原因分析：
1. `_static_dist_map` 改成加权 Dijkstra 后，启发式把 W 当可炸（cost 5），导致 A* 朝墙走、尝试 BOMB，可能绕远或找不到解。对某些图（hunyuan）反而更差。
2. DEAD：贪心降级走进 PIT/激光（因为没有 plan，冷却期用贪心）。贪心只看 MOVE+WAIT，且 `_greedy_action` 的 val 设计有问题（`val = 100.0 * (hp 不变)`，然后 `-1000*damage`，`-2*dist`）。当所有动作都掉血时，它会选掉血最少的；但 PIT -100 会 DEAD → 被跳过 ✓。argon/glm 的 DEAD 是 -100（双激光或 PIT）。可能贪心走到激光射线格。

需要改进：
- **贪心加入"未来伤害"检查**：选择动作时，模拟 2-3 回合看是否会被激光打；或者用 `sim.rays` 检查当前 exposed。实际上 `c.step(act)` 已经结算了本回合伤害（含 phase_d），所以 `dmg` 会体现。但如果英雄走进一个"下一回合才会被扫"的格子，贪心不知道。加一个"下一回合预测"：对候选 c，检查 c 的状态下 `turn%3/4` 的射线是否覆盖 c 的位置（若下回合开火且起点在射线内 → 会挨打）。
- 更重要的是：**尽量让 Turn1 规划成功**，避免长期贪心。

关键问题：**为什么 Turn1 规划在很多图上失败？** 让我诊断 OFFICIAL_02、hunyuan、sol、BENCH_STRONG 的分阶段结果。

之前（BFS dist map 版本）hunyuan 是 CLEARED 229（说明求解器成功），改 Dijkstra 后 TIMEOUT。所以 Dijkstra 启发式对某些图有害。也许应该**两种启发式都试**：先用 relaxed BFS（把 W 当墙）跑，失败再用 Dijkstra 版本。或者用"可炸代价 2"（更接近 1）而非 5，减少偏差。

其实问题在于 `_relax_cost` 让 h 变小（穿过墙），weighted A* 1.85*h 会强烈引导朝墙走，导致在墙前反复尝试 BOMB，而不是绕路。对于我的 hunyuan 图（有很多 W 墙隔离带），Dijkstra 会引导"直接穿墙"，但 BOMB 只有 2 颗，A* 可能浪费。

改进方案：**用两种 dist map，取 max（更接近真实）**：
- `dm_strict`：W/T_W/PIT 为 INF（不可穿）
- `dm_relax`：可炸代价
- h = max(dm_strict_可达? ...) 嗯。

其实更简单：**把可炸代价设得更高**（比如 W=12, PIT=20），这样 Dijkstra 会优先绕路，只在无路可走时才考虑穿墙。这样对 hunyuan（有绕路）会选绕路，对 OFFICIAL_02（必须炸墙）会选炸墙。

让我设：W/gates = 12，炮座 = 12，PIT = 20。这样启发式更保守（接近 strict），但保留可炸通路。

不过 weighted 1.85 会放大，仍可能误导。可以把 weight 降到 1.3（之前 1.35 太慢，但配合 1.0*h 和分阶段，也许够）。之前用 BFS dist (0.55*h) + weight 1.35 很慢；改成 1.0*h + weight 1.85 后 0.016s。中间值 1.0*h + weight 1.4 可能平衡。

让我先诊断具体失败阶段，再决定。用 `v22_diag2.py` 对 OFFICIAL_02 / hunyuan / BENCH_STRONG 跑分阶段（但 diag2 用的是自己复制的 stage 逻辑，dist map 已随 submission 改变，所以能用）。不过 diag2 的阶段顺序固定为 plates/K2/K1/V，不含翻门阶段，且 h 用 0.55*dm（旧），与现在不一致。让我更新 diag2 或直接写个新的诊断命令，调用 `submission._plan_from_state` 并分阶段打印。

更简单：给 `_plan_from_state` 加一个可选参数 `debug`（默认 False），当 True 时打印每阶段结果；交付文件里保留这个参数（无害，但可能被认为调试代码）。或者用一个模块级变量 `_VERBOSE` 由测试脚本设置。我倾向临时加，测完删。

其实我可以直接在测试脚本里 monkeypatch `_stage_search` 包装一层打印。写个诊断命令：

```python
import submission as S, json, time
orig = S._stage_search
def wrap(sim, goal_test, hfun, deadline, acts, max_states=45000):
    t=time.monotonic(); res=orig(...); print('stage', 'OK' if res else 'FAIL', 't',..., 'pos'...); return res
S._stage_search = wrap
...
```
这样能看到哪些阶段失败。让我这么做，针对 BENCH_STRONG / OFFICIAL_02 / hunyuan。

同时考虑用户提示：强基准只是正常基准，重点通用。但 BENCH_STRONG 是重要检验。

让我跑诊断。
````

## 120.1 · Thinking

````
诊断显示：
- STRONG/OFF02/hunyuan：第一个阶段就 FAIL（basic 0.39/0.516s，full 0.078/0.125s）。第一个阶段是什么？对于 STRONG：`has_pgate=True` → 阶段 "plates"（3 个 PLATE 全压）。这很难，0.39s 不够 → FAIL → 整个规划返回 None。
- OFF02/hunyuan：`has_pgate`? 这些是 v2.1 地图，没有 P_GATE → 第一个阶段是"近钥匙"。为什么 FAIL？可能是 dist map 改变导致启发式误导，或者基础动作集下 h 引导朝墙走，搜索预算耗尽。

hunyuan（我上半场的图）有 4 道 W 墙，路径 229 步。之前 BFS dist map 版本能解（CLEARED 229）。现在 Dijkstra 版本 FAIL。所以 **Dijkstra 启发式有害**。

OFFICIAL_02：K1/K2 被 W 围，必须炸墙 → 基础动作集（5 个）不含 BOMB，必然 FAIL；full 阶段只有 0.125s（因为 `min(deadline, dl + 0.20*share)` 给的额外时间很少）→ 也 FAIL。这是**时间分配 bug**：full 回退给的预算太少。

修正方向：
1. **恢复启发式为"strict + 可炸高代价"**：用两套 dist map 取更保守值，或把可炸代价提高到接近 INF 但保留引导。更简单：恢复原 BFS（strict，W/T_W/PIT 为墙），但**额外给"需要炸墙"的图一个专用阶段**（先 BOMB 炸开）。嗯。

其实我可以用 **max(strict_dist, relax_dist)**？strict_dist 对穿墙不可达 → INF，取 max 会变 INF，等于 strict。不行。

折中：**用 strict BFS dist（原版）作为主启发式**，但在 `_plan_from_state` 里，如果基础动作集阶段失败，用 full 动作集并给**充足预算**（至少 0.3s）。这样 OFFICIAL_02 能通过 BOMB 阶段。

2. **时间分配**：给 full 回退至少 `0.35 * span` 或固定 0.3s（Turn1）。目前 `min(deadline, dl + 0.20*share)` 只有 share 的 20%，太少。改为：
```
res = _stage_search(sim, test, hfun, dl, basic)
if res is None:
    full_dl = min(deadline, time.monotonic() + max(0.25, 0.5 * share))
    res = _stage_search(sim, test, hfun, full_dl, full)
```
但总 deadline 是 1.55s，若前几个阶段用完，full 也没时间。可以按阶段优先级：Turn1 允许 1.55s，4 个阶段，每阶段 ~0.39s。full 回退需要至少 0.25s → 总可能超。可以让后续阶段预算动态减少。

3. **STRONG 的 plates 阶段**：3 个 PLATE 需要推 3 个 BOX，Sokoban 搜索很难。0.39s 不够。给 plates 阶段更多预算（比如 0.7s）。但即使如此，能否解出？让我单独测试：给 plates 阶段 3 秒看能否找到。

4. **贪心降级踩雷**：改进贪心，加入"下一回合安全"预测，且优先 WAIT 当所有动作危险。

让我按优先级处理：
- (A) 恢复启发式（strict BFS）+ 提高 full 回退预算 → 修复 hunyuan/OFF02/argon/glm 的 DEAD/TIMEOUT。
- (B) 改进贪心安全性。
- (C) 尝试 STRONG（增加 plates 预算 + 检查是否可解）。
- (D) sol 的 V 阶段 FAIL（可能是 PIT 桥 + 门，需要 JUMP/BOMB）→ full 回退预算增加可能有帮助。

先做 (A)：把 `_static_dist_map` 改回 strict BFS，但保留一个 `_relax_dist_map` 供"需要炸墙"时备用？先简单恢复 strict，测试整体。

实际上更好的做法：**启发式用 strict dist，但把不可达（INF）的格用 relax dist 的值**（这样被墙隔开的目标仍有引导，但不会让近路被低估）：
```
h(s) = strict_dm.get(p, relax_dm.get(p, 70))
```
即：优先 strict 距离；若 strict 不可达（INF），用 relax（穿墙）距离。这样：
- 有绕路的图（hunyuan）→ strict 距离有效 → 不误导。
- 必须炸墙的图（OFFICIAL_02）→ K1 被 W 围，strict 下 K1 不可达（除了炸开），从 spawn 到 K1 的 strict dist 可能是 INF（因为 K1 被墙围）→ 用 relax dist → 有引导 ✓。

这个方案很优雅！实现：
```
def _dist_maps(sim, goal):
    strict = _strict_dist_map(sim, goal)   # BFS, W/T_W/PIT/gates 视为墙? gates 关闭时是墙，但可翻 → 视为可通行（relax）
    relax = _relax_dist_map(sim, goal)     # Dijkstra with costs
    return {p: strict[p] if p in strict else relax.get(p, 70+...) for p in ...}
```
简化：在 `mk_h` 里：
```
def h(s):
    p=(x,y)
    d = strict.get(p)
    if d is None: d = relax.get(p, 70)
    return d
```
需要计算两套 map（3 个目标 × 2 = 6 次 BFS/Dijkstra，很快）。

我把 `_static_dist_map` 改回 strict BFS（原版，但 gates 视为可通行、PIT 视为墙），并新增 `_relax_dist_map`（Dijkstra）。`mk_h` 合并。

代码：
```
def _strict_dist_map(sim, goal):
    def solid(p):
        t=sim.tile(*p)
        return t=="T_W" or t=="PIT" or t in HIGH_BASE - {"W"}? 
```
嗯，strict 应该把 W 当墙（因为正常绕路不应穿墙）、T_W、PIT、炮座当墙；gates（R/B/P_GATE）视为可通行（可翻/压板）。ONEWAY 方向性保留。

```
def _strict_dist_map(sim, goal):
    def solid(p):
        t=sim.tile(*p)
        return t in HIGH_BASE or t=="T_W" or t=="PIT"   # HIGH_BASE 含 W 和炮座
    # BFS 同原版
```
然后 `_relax_dist_map` 用现有 Dijkstra。

`mk_h`:
```
dm_s = strict[name]; dm_r = relax[name]
def h(s):
    p=(x,y)
    d = dm_s.get(p)
    if d is None: d = dm_r.get(p, 70) + 10   # 加一点惩罚，表示需要炸墙
    return d
```
这样被墙围的目标仍有引导但略保守。

好，实施。同时 (B) 改进贪心，(C) 给 plates 阶段更多预算。

先做 (A) 和 full 预算。

另外注意 `_greedy_action` 用 `_static_dist_map`（现在改名），要更新调用。

让我写代码。

具体替换：
1. `_relax_cost` 保留；`_static_dist_map` 改名为 `_relax_dist_map`（Dijkstra），新增 `_strict_dist_map`（BFS）。
2. `_greedy_action` 调用改为 `_strict_dist_map` 或合并 map（用 `_dist_map` 合并版）。为简单，我定义一个 `_dist_map(sim, goal)` 返回合并 dict，供所有地方使用。这样只需一个函数。

```
def _dist_map(sim, goal):
    strict = {} # BFS
    relax = {}  # Dijkstra
    out = dict(relax)  # fallback
    out.update(strict) # strict overrides
    return out
```
但注意：strict 中不可达的格在 relax 中可能有值 → 保留 relax 值 ✓。strict 可达的格用 strict 值（可能比 relax 大，因为绕路）✓。完美。

实现 `_dist_map` 包含 BFS + Dijkstra 两个循环。

好，写。
````

## 122.1 · Thinking

```
注意：`out = {k: v + 12.0 for relaxed}` 加 12 惩罚，然后 strict 覆盖。这样 strict 可达格用真实距离（不含 +12），不可达格用 relax+12 ✓。

现在替换所有 `_static_dist_map` 调用为 `_dist_map`。有几处：
- `_heuristic`（死代码）
- `_greedy_action`
- `_plan_from_state`（`maps[name] = _static_dist_map(...)`）
- `v22_diag.py`/`v22_diag2.py`（测试工具，也要改）

先改 submission.py 内的。用 replace_all。
```

## 124.1 · Thinking

````
等等，replace_all 只替换了 2 处？让我检查有多少处 `_static_dist_map`。可能 `_heuristic` 里没有调用（它接收 dm 参数），`_greedy_action` 1 处，`_plan_from_state` 1 处，诊断脚本 2 处。submission.py 里应该是 2 处 ✓。

现在改 full 回退预算和 plates 阶段预算。

当前 `_plan_from_state` 里：
```
        now = time.monotonic()
        share = (deadline - now) / max(1, remaining)
        dl = now + share
        if nm == "V":
            dl = deadline
        res = _stage_search(sim, test, hfun, dl, basic)
        if res is None:
            res = _stage_search(sim, test, hfun,
                                min(deadline, dl + 0.20 * share), full)
```
问题：full 的 deadline 是 `dl + 0.20*share`，但 `_stage_search` 从 `now` 开始跑，实际可用时间 = `0.20*share`（很小）。而且如果 basic 跑满了 share，now 已经 ≈ dl，full 只有 0.2*share。

改：给 full 至少 0.25s 或 share 的 60%，取 deadline 上限：
```
if res is None:
    now2 = time.monotonic()
    full_dl = min(deadline, now2 + max(0.22, 0.6 * share))
    res = _stage_search(..., full_dl, full)
```
但如果 basic 用完了 share，now2 + 0.6*share 会超过 deadline 被截断 → full 没有时间。所以应该**减少 basic 的预算**，给 full 留空间：
```
dl = now + 0.55 * share
res = basic(dl)
if None: res = full(min(deadline, time.monotonic() + 0.45*share + ...))
```
更简单：把每个阶段的 budget 分成 basic 55% + full 45%：
```
stage_budget = share
res = _stage_search(sim, test, hfun, now + 0.55*stage_budget, basic)
if res is None:
    res = _stage_search(sim, test, hfun, now + stage_budget, full)
```
这样 full 有 45% 的 share。对 4 阶段，share=0.39s → basic 0.21s, full 0.18s。OFFICIAL_02 需要 BOMB 阶段，full 0.18s 可能不够（要放炸弹+等3回合+移动，状态空间不小）。

嗯。另一个思路：**基础动作集里直接包含 BOMB**（成本 +4），这样不需要 full 回退就能炸墙。BOMB 会引入状态（timer），但只在需要时才被 A* 选择（因为cost高）。这可能最好。同样 THROW 用于翻门。但 JUMP 用于跨坑。

让我把 basic 动作集扩展为：MOVE×4 + WAIT + BOMB（若有可炸物）+ THROW×4（若有 SWITCH）+ JUMP×4（若有 PIT）。这样"basic"就是 full，一次搜索搞定，不需要两阶段回退。但状态空间会大（14 分支）。之前 14 分支 + 弱启发式很慢；现在启发式更强（1.0*h + weight 1.85 + 分阶段），可能可以承受。

折中：basic = MOVE×4 + WAIT；full = basic + JUMP×4 + THROW×4 + BOMB。**先跑 basic（55% 预算），失败则 full（剩余 45% + 该阶段全部剩余预算）**。并且**允许阶段"借用"后续阶段预算**（因为如果某阶段失败，整个规划失败，不如把时间都给它）。

实现：
```
for nm, test, hfun in stages:
    if test(sim): ...
    now = time.monotonic()
    remaining_time = deadline - now
    share = remaining_time / remaining
    # 给当前阶段最多 remaining_time * 0.7（借用）
    stage_dl = now + min(remaining_time * 0.7, max(share, 0.15))
    res = _stage_search(sim, test, hfun, min(stage_dl, now+0.55*share), basic)
    if res is None:
        res = _stage_search(sim, test, hfun, stage_dl, full)
    ...
```
嗯，复杂。让我简化为：**每个阶段用全部剩余时间的 60% 作为上限，basic 用其中 45%，full 用全部**：
```
now = time.monotonic()
avail = deadline - now
stage_dl = now + avail * (0.6 if remaining > 1 else 1.0)
res = basic(now + avail*0.30)
if None: res = full(stage_dl)
```
对 4 阶段：avail=1.55 → stage_dl=0.93s，basic 0.47s，full 0.93s。这样每阶段最多 0.93s，第二阶段 avail=0.62 → stage_dl=0.37... 够用吗？如果第一阶段只用 0.016s（常见），avail 仍 1.53 → 均分好。

其实简单点：**basic 给 0.3*avail，full 给 0.6*avail**，剩余 0.4*avail 留给后续阶段。但如果阶段都很快，avail 几乎不减少，每阶段都能用 0.6*avail。可行。

我采用：
```
avail = deadline - now
basic_dl = now + 0.35 * avail
full_dl = now + 0.65 * avail
if nm == "V": full_dl = deadline
res = _stage_search(sim, test, hfun, basic_dl, basic)
if res is None and full != basic:
    res = _stage_search(sim, test, hfun, full_dl, full)
```
这样 OFFICIAL_02 的 K1 阶段（第 1 阶段，avail=1.55）：basic 0.54s（失败），full 1.0s → 有充足时间炸墙 ✓。

对 STRONG 的 plates 阶段：basic 0.54s，full 1.0s → 1.5s 用于推 3 个箱子，可能够？试试。

另外，plates 阶段的 hfun `h_plates` 可能不够好。先看效果。

还要注意：`_action_sets` 里 full 只在 `has_switch or has_chest` 时含 THROW，在 `has_breakable` 时含 BOMB。OFFICIAL_02 有 W → BOMB ✓，有 SWITCH → THROW ✓。STRONG 有 PIT → JUMP ✓（jumps>0 总加 JUMP）。

好，实施。

另外改进贪心安全性：在 `_greedy_action` 里，对候选 c 加"下一回合起点是否在当期开火射线内"的惩罚。实现：
```
def _future_risk(c):
    periods = {3 if c.turn%3==0} | {4 if c.turn%4==0}
    if not periods: return 0
    rl,_ = c.rays(periods)
    lit=set(...)
    return 1 if (c.h['x'],c.h['y']) in lit else 0
```
若 c 的位置在下回合开火射线内 → 该位置会挨打（因为 exposed 含起点）→ 重罚。这能避免贪心走进"下一拍必被打"的格子。

但 WAIT 候选若当前位置安全而下回合会开火，也会被罚 → 可能选一个"移动"动作但落点也危险。嗯，至少避免送死。

实现：在 `_greedy_action` 的循环里：
```
risk = 0
if periods_next:
    rl,_ = c.rays(periods_next)
    if (c.h['x'],c.h['y']) in set(cells...): risk = 400
val -= risk
```
注意 `c.turn` 已 +1（step 后），所以 `c.turn % 3` 是下一回合 ✓。

好，一起改。

让我写替换。
````

## 128.1 · Thinking

```
注意 `remaining` 变量现在没用了（除了递减），但不影响。

现在重跑测试。先看 own（确保自证仍 0 伤）+ bench。
```

## 130.1 · Thinking

```
改善：
- DEAD 归零（贪心改进生效）。
- hunyuan 恢复 CLEARED 229。
- carbon 157（恢复）。
- 10/14 通关，0 死，4 超时（OFFICIAL_02、argon、glm、sol），BENCH_STRONG TIMEOUT。
- 所有 worst_step @t1 ≤1.594s ✓（Turn1 限 2.0s）。

现在要攻克的：
1. **BENCH_STRONG**（3 板推箱 + 深渊桥）。
2. OFFICIAL_02（炸墙 + 翻门）。
3. argon / glm / sol（复杂墙阵/激光）。

这些是"正常基准"难度，用户提示强基准只是正常基准，看来正赛对手图也会类似。提升通用性有价值。

让我诊断 BENCH_STRONG 的 plates 阶段：给它 5 秒看能否找到解。

用命令直接调用 `_stage_search` 针对 plates 目标，预算 5s。

另外 OFFICIAL_02：第一阶段（近钥匙）失败，需要 BOMB。让我看 full 动作集是否能解（给 3s）。

写诊断命令。
```

## 132.1 · Thinking

````
- OFFICIAL_02 的 K1 阶段用 full 动作集 0.91s 可解（28 步，炸墙）。但我的 `_plan_from_state` 里 basic 0.35*avail=0.54s 失败，full deadline = now+0.65*avail = 1.0s（从 now 算），full 从 basic 结束后开始（约 0.54s），实际只有 0.46s < 0.91s → 失败。所以**full 预算不足**。

修正：full 阶段应该有自己的**时长预算**，而不是绝对 deadline 从阶段开始算。`_stage_search` 的 deadline 参数是绝对时间；如果 basic 用掉 0.54s，full 应该给 0.9s → deadline = now_after_basic + 0.9s，可能超过总 deadline（1.55s）。Turn1 允许 2.0s，我可以把总 budget 设为 1.85s（<2.0，留 0.15 余量），并让 full 阶段借用更多。

但更重要：**Turn1 总预算 1.55s 内要跑完 4 个阶段**。OFFICIAL_02 第一阶段就要 0.91s（full）+ 0.54s（basic 浪费）。可以**跳过 basic 直接跑 full** 对于某些情况？或者**减少 basic 预算**（比如 0.1s），把大部分时间给 full。

改进策略：
- 若 `full != basic`（即存在 BOMB/THROW/JUMP 需求），直接先用 **full** 动作集跑，给较多预算；因为 full 包含 basic，只是分支多。但 full 分支多可能慢。
- 或者：basic 给很短（0.12s）试探，失败则 full 给 (avail - 0.12) 的大部分。

我采用：
```
basic_dl = now + min(0.18, 0.25*avail)
full_dl = now + min(avail * 0.85, avail - 0.05)  # 但要考虑后续阶段
```
更精确：每个阶段可用 `avail / remaining` 的份额，但如果阶段需要更多，可以借用。简单方案：
```
share = avail / remaining
basic_dl = now + min(0.15, 0.3*share)
full_dl = now + min(avail * 0.75, max(share, 0.9))   # 上限 0.9s 或 share
```
嗯，这会导致第一个阶段最多用 0.75*1.55=1.16s，后续阶段剩 0.39s 分 3 个 → 紧张。

**关键洞察**：与其在 Turn1 一次性规划全程，不如**分阶段规划也分布在多个回合执行**：Turn1 只规划第一个阶段（比如拿到第一把钥匙/开板），把动作序列缓存；执行完后再在 Turn>1 规划下一阶段（0.3s 预算可能不够，但可以多次尝试/分解）。不过 Turn>1 只有 0.5s，规划 0.91s 的阶段不行。

但 Turn1 有 2.0s。让我把 Turn1 budget 提到 1.85s，并优化分配：
- 只在必要时用 full（即 basic 快速失败后）。
- basic 试探 0.12s。
- full 给 `min(1.0, avail * 0.7)` 秒。
- 后续阶段用剩余时间。

对 OFFICIAL_02：阶段1 basic 0.12s 失败 → full 0.91s 成功（总 1.03s）；剩余 0.8s 给阶段 2、3、4。K2 阶段也要炸墙（同样 28 步左右），可能需要 0.9s → 不够。但 K2 阶段可以从"已炸开的墙"状态出发，且 A* 有经验？不，是新搜索。嗯。

也许可以**在 full 搜索里一次性完成多个阶段**？即回到"一次性 A* 到 CLEARED"，但用强启发式。之前一次性 A* 用 0.55*h 很慢；现在用 `_dist_map`（1.0*h）+ weight 1.85，可能能解！让我测试：对 OFFICIAL_02 用 `_stage_search` goal_test = CLEARED，h = 分阶段启发式（`_heuristic` 旧函数用 dk1/dk2/dv），看能否在 1.5s 内解出。

嗯，这值得一试。如果一次性 A* 能解，就不需要分阶段（分阶段反而重复搜索）。

让我测：对 OFFICIAL_02、STRONG、sol、argon、glm 用一次性 A*（goal CLEARED，full 动作集，h 用 `_heuristic` 的修正版）给 3s 看结果。

`_heuristic(sim, dk1, dk2, dv, need_plates)` 用的 dk1/dk2/dv 是 `_dist_map`。让我写个测试。

实际上，我可以直接修改 `_plan_from_state` 为"两路并行"：
1. 先用分阶段（快，解决大多数图）。
2. 若分阶段失败，用一次性 A* 兜底（在剩余时间内）。

但 Turn1 时间有限。

让我先测一次性 A* 的效果。

写命令：
```
def once(g, lim):
  root=_Sim(grid=g); maps...
  h=lambda s: _heuristic(s, dk1,dk2,dv,need)
  r=_stage_search(root, lambda s: s.status=='CLEARED', h, t+lim, full, 200000)
```
注意 `_heuristic` 有 need_plates 惩罚 +25，可能有用。

测试。
````

## 134.1 · Thinking

````
一次性 A* 都失败（2s）。分阶段更合适。

关键洞察：**OFFICIAL_02 每个阶段需要 ~0.9s（full 动作集炸墙）**，Turn1 1.85s 只够 2 个阶段。但**后续阶段可以在后续回合继续规划**——只要 plan 缓存的动作执行完后，Turn>1 再规划下一阶段。Turn>1 只有 0.5s，但如果阶段变短（比如 K2 阶段从已炸开的 K1 出发，且墙已炸开，可能不需要再炸，A* 会快），可能够。

其实更简单：**让 Turn1 只规划"第一个阶段"，把剩余阶段留到 Turn>1 逐次规划**。但 Turn>1 预算 0.3s，对炸墙阶段不够。

**替代方案**：Turn1 用 1.85s 做分阶段规划，但**允许阶段规划跨越到 Turn>1**：即 Turn1 输出第一个阶段的动作序列，执行完后再规划。为了保证 Turn>1 也能规划复杂阶段，可以把预算提到 0.45s（<0.5 限制，留 0.05 余量）。0.45s 对炸墙阶段（0.91s）不够。

嗯。但注意：**BOMB 炸墙需要 3 回合等待**，A* 搜索时会展开这些状态；0.91s 是因为 full 动作集 14 分支 + 状态空间大。可以优化：
- 减小分支：THROW 只在有 SWITCH 且门是障碍时启用；JUMP 只在有 PIT/深渊时启用；BOMB 只在有 W 阻挡时启用。
- 对 OFFICIAL_02：有 SWITCH（1个）、有 W（11格）、有 PIT? 无。JUMP 不需要 → 去掉 JUMP 4 个分支，从 14 → 10。
- 还可以把 THROW 只在"门关闭且目标被门挡"时启用。

另外，**A\* 的状态 key 含 `dt`（地形覆盖）**：BOMB 炸墙后 dt 增加（W→EMPTY），状态变化，这是必要的。

让我优化 `_action_sets`：
- JUMP：只在地图有 PIT 或 CRACK 或有"两格空隙"时启用。简化：有 PIT 时启用（BENCH_STRONG 有 PIT）。
- THROW：有 SWITCH 且（有 R_GATE/B_GATE）时启用；或有 CHEST/TNT。
- BOMB：有 W 或 gates 时启用。

对 OFFICIAL_02：no PIT → 无 JUMP；有 SWITCH+gates → THROW；有 W → BOMB → full = 5 + 4 THROW + 1 BOMB = 10 分支。

还有一个大优化：**A\* 里 `WAIT` 动作在 BOMB 等待期间很重要**，但 WAIT 会产生大量状态（turn%12 变化）。 inevitable.

让我测：OFF02 K1 阶段用 10 分支（去掉 JUMP）需要多久？

另外，我意识到一个更根本的问题：**分阶段规划的阶段顺序可能导致"重复炸墙"**。比如先 K1（炸墙进入）再 K2（也要炸墙），每次都要从头搜索。但 K1/K2 的墙是不同位置，必须分别炸（2 颗炸弹刚好）。

嗯，让我换个思路：**对于这些难题，接受 TIMEOUT 但不 DEAD**（当前已经 0 死）。评分：TIMEOUT hero 分 = 200*k + 200*r，k=钥匙数，r=进度。如果拿到 0 钥匙，分很低（~180）。而 CLEARED 分 ~900+。差距大。所以提升有价值，但也要权衡时间。

不过用户特别提示"打过强基准也不代表强，它只是一个正常基准"，暗示强基准是普通水平，正赛对手可能都接近这个难度。我应该努力打过 BENCH_STRONG。

**BENCH_STRONG 的核心难点**：3 个 PLATE 全被 BOX 压住。这是 Sokoban。我的 A* 在 4s 内都找不到（basic 和 full 都失败）。需要专门的推箱求解器。

让我分析 BENCH_STRONG 布局（从战报 ASCII）：
```
PLATE: (7,6), (8,18), (8,22)
P_GATE: (11,13), (35,13)
BOX: (3,9), (23,13), (4,17), (4,21)
ICE: (5,17),(6,17),(7,17)
MIRROR_SE: (8,17)
SPRING_R: (5,21)
PORTAL etc.
```
推箱路径：
- BOX(4,17) → 经 ICE(5,17),(6,17),(7,17) → MIRROR_SE(8,17) 折转 → 可能到 PLATE(8,18)? MIRROR_SE 把方向 R 折成 D（MIRROR_SE: R→D）→ 从 (8,17) 向下到 (8,18)=PLATE ✓。所以推 BOX(4,17) 向右，箱子滑到 (8,18) 压板！
- BOX(4,21) → SPRING_R(5,21) 弹射 → 到 (8,21)? 但 PLATE 在 (8,22)。嗯，SPRING_R 弹 3 格 → (8,21)，然后继续？弹簧后是普通地面，停。要到 (8,22) 需要另一个机制。可能 BOX(4,21) 推到 (5,21) 弹簧 → 弹到 (8,21)，然后再从下方推上 (8,22)？复杂。
- BOX(3,9) → 到 PLATE(7,6)：需要向上推；(7,7)=ONEWAY_U 只能向上进入 → 从 (7,8) 向上推箱子到 (7,7) 再 (7,6)=PLATE ✓。但要把 BOX 从 (3,9) 移到 (7,8) 下方……复杂。
- BOX(23,13) → 可能用于填两格 PIT(25,13),(26,13)。

这确实是设计精巧的 Sokoban，需要真正的规划。我的通用 A* 状态含 boxes 应该能解，但搜索空间太大（4 个箱子 × 1040 格）。4s 内找不到。

要打过它，需要专门的 Sokoban 启发式 + 更大的搜索预算。Turn1 只有 2s，不可能。除非用"离线预计算"——但正赛不允许针对基准硬编码（而且用户提示不要过拟合）。

**结论**：BENCH_STRONG 可能超出 2s 预算的通用求解能力。我应接受它 TIMEOUT，但保证不死、且尽量拿钥匙（P 值）。目前 BENCH_STRONG keys=[False,False]，P 低 → hero 分低。改进：**贪心降级时应主动去拿钥匙/推进**，而不是原地打转。

当前 BENCH_STRONG TIMEOUT 且 keys 0/2，说明贪心没拿到任何钥匙。让我看贪心在做什么——可能被 P_GATE(11,13) 挡住（关闭时高墙），而 `_dist_map` 的 relax 让 dist 到 K1 可穿过 P_GATE，贪心朝它走但撞墙，然后在附近徘徊。改进贪心：加入 THROW/JUMP/BOMB 候选，且当静态距离长期不下降时切换目标。

嗯，时间成本在上升。让我做一个**高收益的改进**：改进降级策略，让贪心在无法规划时也能拿到钥匙/推进，从而提升 TIMEOUT 局的 hero 分（200*k + 200*r）。具体：
- 贪心候选动作加入 JUMP/THROW/BOMB（各 1 个最优方向）。
- 用"访问计数"避免原地循环（memory 里记录 visited cells，贪心偏好未访问格）。
- 目标切换：若最近 N 回合没拿到钥匙且距离没缩短，改去另一个钥匙。

但更简单有效：**当 Turn1 规划失败时，改用"分阶段规划的逐回合版本"**：每回合用 0.3s 尝试规划一个**较短的子目标**（比如"到最近钥匙"），并在 0.3s 内用 basic 动作集（5 分支，快）。对于 OFFICIAL_02 的炸墙阶段需要 full，但可以在 cooldown 结束后用 0.3s full 搜索——可能部分成功。

嗯。让我换个角度：**Turn>1 的 0.5s 限制其实允许 0.45s 搜索**；多次回合累积，每回合重新规划一个短阶段，逐步推进是可行的。关键是每回合规划要能产出**至少 1 个有效动作**。当前 `_plan_from_state` 若某阶段失败就返回 None（整盘放弃）。改为：**返回"部分计划"**——如果某阶段成功、后续阶段失败，仍返回已成功的动作序列（至少能执行一段），而不是 None。这样 Turn1 可以给出部分路径，执行完后再规划。

这个改进很实用！实现：在 `_plan_from_state` 里，如果某阶段失败：
- 若 `out` 非空（前面阶段有成果）→ 返回 `out`（部分计划）。
- 否则返回 None。
然后 `decide_action` 里接受部分计划（`ok or len(seq)>1` 条件已允许 `len(seq)>1`，即使 sim 不是 CLEARED）。注意当前代码：
```
sim = _Sim(state=state)
for a in seq: sim.step(a); sigs.append(...)
if sim.status != "CLEARED": ok = False
if ok or len(seq) > 1: 缓存 seq 并返回 seq[0]
```
`len(seq)>1` 允许部分计划 ✓。但 `_certificate` 要求 CLEARED（用于自证），不受影响。

好，实现"部分计划"：阶段失败时返回已有 out（若非空）。

这样 OFFICIAL_02：Turn1 阶段1（K1）若 full 0.46s 失败 → out 为空 → None。仍失败。嗯。

那么先给阶段1更多时间：把 basic 试探缩到 0.10s，full 给 `min(avail*0.7, 1.1)` 秒。OFFICIAL_02 阶段1 full 0.91s → 成功（out=28 步）。剩余时间 ~0.5s，阶段2（K2）可能失败 → 返回部分计划 28 步。执行 28 步后（Turn 29），再规划：此时 K1 已拿，阶段列表只剩 K2 + V，且墙已炸开一部分 → K2 阶段可能快。Turn>1 预算 0.3s，可能不够炸第二面墙。但可以尝试多次（每回合重规划，cooldown）。

嗯，也许能逐步推进。让我实现并测试。

另外还有个重要点：**Turn 1 的 budget 1.55s，规则给 2.0s**。我可以提到 1.8s（留 0.2s 余量）。这多出 0.25s 很有价值。设 `budget = 1.80 if turn==1 else 0.32`。但要保证总耗时 <2.0s（含 `_Sim(state)` 构造等开销 ~0.01s）✓。

用户提示"1.6s 安全截止线"（考卷提示）。规则说 2.0s，提示建议 1.6s 安全线。我用 1.6s 更保守？但 1.55 已接近。为了性能，用 1.75s（<2.0，且比 1.6 略高，风险小）。嗯，提示明确说"请用 time.monotonic() 给 Turn 1 全局搜索设好 1.6s 安全截止线"。遵守提示更安全：用 1.6s。当前 1.55 已符合。保持 1.55。

那就靠优化动作集和部分计划。

让我做：
1. `_action_sets` 优化分支（JUMP 仅在有 PIT/CRACK 时；THROW 仅在有 SWITCH+门 或 CHEST/TNT 时）。
2. full 预算：`basic_dl = now + min(0.10, 0.2*avail)`；`full_dl = now + min(avail*0.72, 1.05)`（上限 1.05s）。
3. 阶段失败时返回部分计划（若 out 非空）。
4. `decide_action` 对部分计划：缓存后执行；执行完再规划（已有机制）。

测试。

先改 `_action_sets`。当前：
```
full = list(basic)
if jumps>0: full += JUMP_*4
if throws>0 and (has_switch or has_chest): full += THROW_*4
if bombs>0 and has_breakable: full.append("BOMB")
```
改：
```
has_pit = any(tile in ("PIT","CRACK") ...)  # 或 CRACK 变 PIT
if jumps>0 and has_pit: full += JUMP_*
if throws>0 and (has_switch or has_chest): full += THROW_*
if bombs>0 and has_breakable: full.append("BOMB")
```
对 BENCH_STRONG：有 PIT → JUMP ✓；有 SWITCH → THROW ✓；有 W → BOMB ✓ → 14 分支。嗯，还是 14。但 STRONG 主要难在推箱（MOVE 就够），JUMP/THROW/BOMB 是浪费。可以按阶段裁剪：
- plates 阶段：只需要 MOVE + WAIT（推箱靠 MOVE），不需要 JUMP/THROW/BOMB。
- 钥匙/V 阶段：可能需要 JUMP（跨 PIT）、THROW（翻门）、BOMB（炸墙）。

在 `_plan_from_state` 里为 plates 阶段单独用 basic（5 分支），其他阶段用 full。这能大幅加速 plates 阶段。当前代码 plates 阶段也用 basic 先、再 full（浪费）。改：若 nm=="plates"，只用 basic，且给更多时间。

实现：
```
if nm == "plates":
    dl = now + min(avail*0.8, 1.2)
    res = _stage_search(sim, test, hfun, dl, basic)
else:
    ...
```
但 plates 阶段 4s 都找不到（basic），1.2s 更不可能。所以 STRONG 的 plates 阶段仍失败。除非改进 `h_plates` 启发式或 Sokoban 搜索。

**改进 h_plates**：当前 h_plates 只估计一个 box→plate 的最小距离，没有考虑"必须推 3 个箱子"。而且 A* 状态含 boxes，搜索空间巨大。启发式应估计"所有未完成压板的总代价"：
```
h = 0.55 * sum over uncovered plates of min over boxes of (dist(hero, box) + dist(box, plate))  # 太高估
```
或 `0.55 * (min + 20*(n_uncovered-1))`（当前有 12*n）。当前已有 `0.55*12*max(0, n - covered)`，还行。

问题可能是 **A\* 状态 key 含 `do`（箱子覆盖）**，每推一步箱子 do 变化 → 状态多。但 4s 内只扩展了有限节点。

另一个可能：**BENCH_STRONG 的 plates 阶段根本无法只用 MOVE+WAIT 完成**（需要 JUMP 或 BOMB？）。BOX(4,21) 需要 SPRING_R(5,21) 弹射到 (8,21)，然后可能要用 JUMP 或别的推到 (8,22)。也可能 BOX(23,13) 需要跨 PIT。嗯。

让我看看 plates 阶段用 full（14 分支）4s 也失败了。说明搜索空间确实太大或存在物理障碍。

考虑到时间，我决定：**不强求 BENCH_STRONG 通关**，但要保证：
- 不死（已做到）
- 尽量拿钥匙、推进（提高 TIMEOUT 分）
- 其他图尽量通关

对 STRONG，让贪心/部分计划能拿到钥匙。K1(20,6)、K2(19,22) 都在 P_GATE(11,13) 右侧区域？从 ASCII 看，P_GATE(11,13) 是横向通道的关卡，勇者 spawn(2,13) 在左侧，要过 (11,13) 必须开板。所以拿不到钥匙。除非绕路（地图有 T_W 竖墙 x=11 从 y=1..24？看 ASCII：x=11 列有多处 `#`(T_W)，确实是一堵竖墙，只有 (11,13)=P_GATE 一个缺口）。所以必须开板才能到右侧。因此 STRONG 若不开板，keys=0，P 低。

嗯。这需要真正的 Sokoban 解法。

**我可以专门实现一个"推箱子到压板"的子求解器**（Sokoban BFS），作为 plates 阶段的专用算法，而不是通用 A*。这能大幅提升。设计：
- 状态：(hero_pos, frozenset(box_positions))。
- 动作：MOVE 4 方向（含 WAIT）。
- 目标：所有 PLATE 被 BOX 覆盖。
- BFS/A* 在 (hero, boxes) 状态空间，用启发式 = sum of min dist(box, plate) + ...。
- 用 `_Sim` 的逐步模拟来生成转移（或直接实现简化推箱物理）。
- 简化物理：推箱时箱子沿方向移动 1 格（含 ICE/MIRROR/SPRING/PORTAL 链），复用 `_Sim.chain`。

状态数：hero 1040 × boxes C(1040,4) 巨大，但实际可达状态有限（箱子只在可推区域）。用 BFS + visited 剪枝，可能几万状态。1.2s 内可能可行。

但实现工作量不小。而且这属于"针对推箱机制的通用能力"，符合"通用求解器"目标（不是硬编码基准）。值得做。

不过时间/复杂度：我需要写一个 `_sokoban_plan(sim, deadline)`，用 `_Sim.clone()` 每一步 MOVE，状态 key = (hx,hy, boxes_tuple, turn%12, flipped?) —— 注意激光相位！BENCH_STRONG 有 3 门炮，推箱路上可能被打。可以把 turn%12 纳入状态。

启发式：对每个未覆盖的 PLATE，找最近的 BOX，估计 `manhattan(box, plate)`；加上 hero 到该 box 的距离；取总和/最大值。

搜索用 A*（weighted）。节点数上限 ~30000，限时 0.8s。

实现位置：在 `_plan_from_state` 的 plates 阶段，先调用 `_sokoban_plan`，若成功直接用；否则退回 `_stage_search`。

让我写 `_sokoban_plan`：
```
def _sokoban_plan(sim, deadline, max_states=40000):
    def goal(s): return s.plates_active()
    if goal(sim): return [], sim
    def h(s):
        boxes = _boxes_of(s); covered = sum(1 for p in s.plates if s.occ(*p)=="BOX")
        if covered == len(s.plates): return 0
        # 对每个未覆盖 plate，估计最近 box 到它的距离
        tot = 0
        for p in s.plates:
            if s.occ(*p)=="BOX": continue
            best = min((_man(b,p) for b in boxes), default=40)
            tot += best
        return 0.8*tot + 0.3*min((_man((s.h["x"],s.h["y"]),b) for b in boxes), default=20)
    acts = MOVE_ACTS + ("WAIT",)
    # A* 同 _stage_search 但状态 key 用 (pos, boxes, turn%12, flipped, dt?)
    ...
```
注意 `_stage_search` 的 key 是 `s.key()`（含 dt/do/bombs/hp/flip/phase/jumps...），已经包含 boxes（do/bo 通过 do 反映）。等等：`s.key()` 包含 `tuple(sorted(self.do.items()))` 和 `dt`，但**不包含 `bo`**（bo 是不可变基础）。箱子移动通过 `set_occ` 写入 `do`，所以 boxes 变化会反映在 do ✓。但初始 bo 是固定的；如果箱子被推回原位，do 里会有显式值，与 key 一致。OK。

所以 `_stage_search` 已经能处理 Sokoban，只是启发式弱 + 分支多。我可以直接给 plates 阶段用一个专门的强启发式 + basic 动作集 + 更大预算。

让我测试：用 `_stage_search(sim, goal=plates_active, hfun=更强启发式, acts=basic, deadline=1.5s)` 对 STRONG。

先测不同启发式。写命令试几个。

启发式候选：
```
h = 0.9 * sum over uncovered plates of min_man(box, plate) + 0.4*min_man(hero, box)
```
或用 `_dist_map` 到 plate 的距离（考虑墙）：
```
dm_p = {p: _dist_map(sim, p) for p in plates}
h = sum over uncovered p of min over boxes of dm_p[p].get(b, 60)
```
这更精确（考虑墙）。但计算 3 次 `_dist_map`（每次 BFS+Dijkstra 1040 节点）→ ~0.02s，一次性预计算。

让我测试这个启发式在 STRONG plates 阶段 2s 内的效果。

写命令。
````

## 136.1 · Thinking

````
太好了！用"每个未覆盖压板到最近箱子的 relaxed 距离之和"作为启发式，0.11s 就解出 plates 阶段（38 步）！之前的 `h_plates` 只用了曼哈顿最小值且没按每个压板求和，太弱。

现在把这个启发式集成到 `_plan_from_state` 的 plates 阶段。需要预计算 `dms = [_dist_map(root, p) for p in root.plates]`。注意：这些 dist map 是从**初始状态**算的，箱子移动后墙不变，仍适用 ✓。

实现：
```
plate_maps = [_dist_map(root, p) for p in root.plates] if has_pgate else []
def h_plates(s):
    if s.plates_active(): return 0.0
    bs = _boxes_of(s)
    if not bs: return 60.0
    tot = 0.0; n=0
    for i,p in enumerate(s.plates):
        if s.occ(*p)=="BOX": continue
        n+=1
        tot += min((plate_maps[i].get(b,70.0) for b in bs), default=70.0)
    hd = min((_man((s.h["x"],s.h["y"]),b) for b in bs), default=40.0)
    return 1.0*tot + 0.2*hd + 6.0*n
```
用 (1.0, 0.2, 6.0)（0.11s 解出）。

然后 plates 阶段用 basic 动作集（5 分支）即可，不需要 full。

集成后重测 STRONG 全流程（plates → K1 → K2 → V）。

注意 `_plan_from_state` 里 plates 阶段目前用 basic 先、full 后。可以改成只用 basic（因为推箱不需要 JUMP/THROW/BOMB），并给足预算。但为了通用（有些图可能需要炸开箱子周围），保留 full 回退。

改代码：
1. 在 `_plan_from_state` 里预计算 plate_maps。
2. 替换 `h_plates`。
3. plates 阶段给更多预算（比如 `min(avail*0.5, 0.8)` 秒，basic）。

让我先只改启发式，看全流程效果（预算保持现状：basic 0.35*avail≈0.54s，够 0.11s）。

改 `h_plates`。需要 `plate_maps` 变量在作用域内。

写替换。
````

## 138.1 · Thinking

```
现在也把 `_action_sets` 优化（减少 JUMP 分支）和 full 预算调整，以及"部分计划"返回。

先测 STRONG 全流程，看新启发式效果。
```

## 140.1 · Thinking

```
进展！STRONG：
- plates 阶段 38 步成功（3 板全压）
- K1 阶段 27 步成功
- 某个阶段 FAIL 0.484s（basic），然后 K2 阶段 17 步成功（0.000s？看起来是 basic 失败后 full 成功，或者 wrap 打印顺序）
- V 阶段 FAIL 0.313s 和 0.562s → 总规划失败。

V 阶段从 (19,22) 到 V(36,13)，需要经过 P_GATE(35,13)（已开）、PIT(25,13),(26,13) 两格深渊、ONEWAY_R(27,13)、以及可能的激光。需要 JUMP 跨两格 PIT 或 BOX 填坑。BOX(23,13) 可能还在（用于填坑）。

V 阶段失败原因：basic（MOVE+WAIT）无法跨两格 PIT；full（含 JUMP/BOMB）0.56s 可能不够，或启发式 `_dist_map` 到 V 的距离把 PIT 当 cost 8（relax），引导走 PIT 方向，但 A* 不知道要 JUMP/填坑。

让我诊断 V 阶段单独给更长预算和 full 动作集。

另外注意：K2 阶段"OK seq=17"在 0.000s，可能是 basic 或 full 之一。总之成功。

V 阶段：从 (19,22) 出发，keys 齐，plates 开。目标 CLEARED。需要跨 (25,13),(26,13) 两格 PIT。BOX(23,13) 在 (23,13)，勇者可以推它填坑？箱子推到 PIT 会填一格，但有两格 PIT。或者用 JUMP 跨 2 格（JUMP_R 从 (24,13) 跳到 (26,13)？落点是 PIT → 死）。需要 JUMP 从 (24,13) 跳到 (26,13) 会落在 PIT 上 → 死。除非先填一格。

看 ASCII：`#..........g...!.......B.OOe.......gV#.#` y=13：x=1..38，其中 (23,13)=B BOX, (25,13)=O PIT, (26,13)=O PIT, (27,13)=e ONEWAY_R, (35,13)=g P_GATE, (36,13)=V。
所以从左侧到 V 必须过 x=25,26 两格 PIT。可以用 BOX 填一格（推 BOX(23,13) 向右 → (24,13)→(25,13) PIT 填平消失），然后剩 (26,13) 一格 PIT，用 JUMP_R 从 (25,13)（现在是 EMPTY）跳到 (27,13)（ONEWAY_R，方向 R ✓）→ 跨过 (26,13)。可行！

这需要 A* 组合"推箱填坑 + JUMP"，full 动作集包含 BOMB/JUMP，但**推箱是 MOVE 动作**（basic 已有）。所以 full 应该能找到。0.56s 可能不够（状态空间大）。

让我单独测 V 阶段给 2s full。

先构造状态：执行上面成功的阶段序列，然后从该状态跑 V 阶段。我用命令重现。

其实更简单：直接改 `_plan_from_state` 让 V 阶段有更多预算，然后测全流程。但总时间 1.55s 已用完。

**关键改进**：Turn1 只规划到"部分"，让后续阶段在 Turn>1 规划。即返回部分计划（而不是 None）。这样：
- Turn1 输出 plates+K1+K2 阶段的动作（38+27+17=82 步），缓存执行。
- 执行到 Turn 83 时，重新规划 V 阶段（此时状态更近，且阶段列表只有 V），Turn>1 预算 0.3s。V 阶段需要 >0.56s → 可能仍失败。但 cooldown 机制会周期性重试，也许某次 0.3s 能解（因为启发式更准、状态更近）。

嗯，或者：**Turn1 用 1.55s 规划，但把 V 阶段的预算最大化**（前面的阶段都很快，0.125+0.078+0.484+0.000 ≈ 0.69s，剩 0.86s 给 V）。当前 V 阶段 `full_dl = deadline`（因为 nm=="V"），basic 0.35*avail≈0.30s，full 从 0.30s 后到 deadline 1.55s → 约 0.86s。诊断显示 full 0.562s 后失败？可能是 `max_states` 限制或 openh 耗尽（无解），不是超时。

看诊断：V 阶段两次 FAIL：0.313s（basic）、0.562s（full）。如果 full 是超时，会用满 0.86s；0.562s 说明**openh 耗尽或 states 超限**（无解）。也就是说 full 动作集下 V 阶段**无解**。

为什么？可能：
1. `_action_sets` 的 full 不含 JUMP（因为 `has_pit`? 我还没改 `_action_sets`，当前 full 总是含 JUMP 若 jumps>0 ✓）。
2. JUMP 落点检查：`p2` 不能是 PIT？我的 `JUMP` 检查 `not self.high(*p2)` 和 occ，但**不检查 p2 是否是 PIT**！`chain` 落到 PIT 会 hurt(100) → DEAD → A* 跳过。所以 JUMP 到 (27,13)（ONEWAY_R）需要 p1=(26,13) PIT（不是 high，可以飞越），p2=(27,13) ONEWAY_R（方向 R ✓）→ 可行！但 JUMP 的 `ok` 检查里 `self.high(*p1)` —— p1=(26,13) 是 PIT，不是 high ✓。所以 JUMP_R 从 (25,13) 到 (27,13) 应该可行。

但 (25,13) 需要先填平（BOX 推入 PIT）。推箱：勇者在 (23,13)? BOX 在 (23,13)，勇者需站在 (22,13) 向右推 → 箱子到 (24,13)，然后 (25,13) PIT 填平。但箱子 chain 从 (23,13)→(24,13)（EMPTY，停），不会自动进 PIT。需要再推一次：勇者到 (23,13)，MOVE_R 推箱 (24,13)→(25,13) PIT → 填平 ✓。

嗯，这些都需要 A* 探索。0.56s + 14 分支可能不够。

**另一个可能**：V 阶段的 goal_test 是 `s.status == "CLEARED"`，但 A* 在 `c.step(a)` 后如果 `c.status=="CLEARED"` 会被 push，然后 pop 时 goal_test 命中 ✓。没问题。

让我单独测 V 阶段（从正确状态）给 3s，看是否可解。构造：用 `_plan_from_state` 的部分结果。我改 `_plan_from_state` 先返回部分计划，或者手动重放前 3 阶段。

写命令：直接调用 `_stage_search` 依次执行 plates/K1/K2，然后从结果状态跑 V 阶段 3s。

需要 h_V = `_dist_map(root, V)`。

让我跑。
```

## 142.1 · Thinking

````
咦，plates 阶段用 full 动作集 1.0s 失败了！之前用 basic 0.11s 成功。说明 full 的额外分支（JUMP/THROW/BOMB）反而干扰了搜索（状态爆炸）。所以 plates 阶段应**只用 basic**。

这印证了：**按阶段裁剪动作集**很重要。

让我改 `_plan_from_state`：
- plates 阶段：只用 basic（5 动作），用强 Sokoban 启发式，预算充足。
- 其他阶段：basic 先，full 后。
- V 阶段：可能仍需 full（JUMP 跨坑）。

另外，从之前全流程诊断看，V 阶段失败可能是因为前面的 K2 阶段用了 full 导致状态不同，或者 V 阶段启发式/动作集问题。让我重新按顺序跑一次，plates 用 basic。

写命令重测（plates basic，K1/K2/V 用 basic 先 full 后）。

其实我直接改代码并测全流程更省事。改动：
```
if nm == "plates":
    dl = now + min(avail*0.6, 0.9)
    res = _stage_search(sim, test, hfun, dl, basic)
else:
    ... (现有)
```
然后重测 STRONG。

另外 V 阶段 full 可能仍失败。让我先改，再诊断。

还有"部分计划"返回：阶段失败时返回已有 out。加上。

写代码。
````

## 144.1 · Thinking

```
注意 `_plan_from_state` 最后 `return out if sim.status == "CLEARED" else None` —— 如果我返回部分计划（`out` 非空但 sim 不是 CLEARED），最后一行的 `return` 不会被走到（因为阶段循环里 return out 已提前返回）。但如果所有阶段都成功（sim CLEARED），最后返回 out ✓。如果所有阶段都 `test(sim)` 为 True 被跳过（初始就满足所有，不可能），sim=root 不是 CLEARED → 返回 None。OK。

但 `_certificate` 调用 `_plan_from_state` 时要求完整解（会验证 CLEARED），部分计划不会通过验证 ✓。

现在 `decide_action` 接受部分计划（`len(seq)>1`），会缓存执行。执行完后重新规划 ✓。

重测 STRONG 全流程。
```

## 146.1 · Thinking

```
现在 Turn1 返回 82 步部分计划（plates+K1+K2），执行到 Turn 83 时重新规划 V 阶段。V 阶段 0.703s 仍失败（full，从 now 到 deadline）。

需要让 V 阶段可解。让我单独诊断：从执行完 82 步的状态，给 3s，用 basic/full，看是否可解。

写命令。
```

## 148.1 · Thinking

```
V 阶段从 (19,22) 出发完全无解（4s，basic 和 full 都失败）。而且 `jumps=0`（前面阶段把 3 次跳跃用掉了！）—— 这是问题：plates/K1/K2 阶段的 full 动作集用了 JUMP，把跳跃次数耗尽，导致 V 阶段无法跨坑。

`_action_sets` 在 root（初始状态）计算 full 包含 JUMP。K1/K2 阶段用 full 时 A* 可能选择 JUMP 来抄近路，消耗 jumps。到 V 阶段就没跳跃了。

而且 `full` 动作集在 `_plan_from_state` 开头基于 root 计算一次，后续阶段复用同一个 full（含 JUMP），但实际 jumps 已用完 → `c.step(JUMP)` 不移动但扣次数（我的 `_Sim.step` 里 `if h["jumps"]>0` 才扣，0 次时不扣也不移动 → 产生无效状态，A* 会浪费）。

修正：
1. **按阶段动态生成动作集**（基于当前 sim 的剩余资源）。
2. **限制 JUMP 只在必要时**：只在地图有 PIT 且 V 阶段等需要跨坑时启用；或者保守地**不在基本规划里使用 JUMP**，把它留给最后阶段。更好：给 JUMP 动作加一个较大的 cost（比如 +3），让 A* 优先不用跳跃，只在必须时使用。
3. 对 V 阶段，若 jumps=0，仍可能用 BOX 填坑 + BOMB？两格 PIT 需要两箱或一箱+跳。BOX 数量 4，其中 3 个在压板上（不能动，否则门关），剩 1 个 BOX(23,13) 可填一格，另一格需要跳。若 jumps=0，可能无法通关。

所以关键是**保留跳跃次数**。让我：
- 在 `_action_sets` 里给 JUMP 加 cost（在 `_stage_search` 的 cost 计算里）。
- 或者更简单：**只在 V 阶段启用 JUMP**（其他阶段用 basic + THROW/BOMB）。但 plates/K1/K2 阶段可能也需要 JUMP（跨坑）。嗯。

我采用：**给 JUMP 动作在 A* 里加 cost +6**（相当于珍惜资源），并**动态生成动作集**（每阶段根据 `sim.h["jumps"]` 等）。这样 A* 会优先普通移动，只在必要时跳。

另外，V 阶段即使有 jumps，能否解？让我测试：从 (19,22) 状态，但把 jumps 改回 3，看 V 阶段是否可解。

还有一点：**dist to V = 56**，路径长；A* 4s 没找到，可能因为 PIT 阻断了 relaxed 距离（PIT cost 8）但 strict 不可达 → 用 relax+12。启发式可能误导。

让我测：手动设置 jumps=3 后 V 阶段 full 4s。

另外考虑：V 阶段可能需要推 BOX(23,13) 填坑。BOX 在 (23,13)，而勇者在 (19,22)（下方区域）。要到 (23,13) 需要绕过 T_W 竖墙 x=26? 从 ASCII 看 x=26 有竖墙（y=1..24 多处 #）。地图被分成左右两半，中间通道在 y=13（含 PIT）。勇者从 (19,22) 要到 V(36,13) 必须经过 y=13 的通道（x=25,26 PIT + x=27 ONEWAY_R + x=35 P_GATE）。从下方 (19,22) 到 y=13 通道的左端需要走 x<26 区域，然后 y=13。

嗯，两格 PIT + ONEWAY_R：用 BOX 填一格 + JUMP 跨一格是预期解法。BOX(23,13) 就在附近 ✓。

让我测 jumps=3 的情况。
```

## 150.1 · Thinking

````
确认：保留 jumps 后 V 阶段可解（25 步，3.69s 搜索）。但 3.69s 远超 Turn1 1.55s / Turn>1 0.5s 预算！所以即使保留跳跃，也无法在时限内解出。

要让 V 阶段快速解出，需要更强的启发式或更好的搜索。3.69s 太慢，因为：
- A* 从 (19,22) 到 V 距离 56，状态空间大（14 分支，含 JUMP/BOMB/THROW）。
- PIT/ONEWAY 让启发式不准。

优化方向：
1. **减少动作分支**：V 阶段只需要 MOVE + JUMP（+ WAIT）。去掉 THROW/BOMB（不需要）。10 → 6 分支。
2. **更强的启发式**：用 `_dist_map` 到 V 的 strict 距离（56），但 PIT 段让 strict 不可达 → 用 relax。可以专门计算"考虑可填坑/跳跃"的距离：把 PIT 视为 cost 2（而非 8）并加一个"可用跳跃次数"的惩罚。或者用一个"路标"启发式：从当前位置到 V 的关键路标（比如 (27,13) ONEWAY_R）的距离。
3. **给 V 阶段更长的预算**：Turn>1 只有 0.5s。但可以在多个回合分摊搜索？不行，A* 是单次调用。

不过有一个技巧：**Turn1 可以规划全部阶段，只要总时间 ≤1.55s**。当前 plates+K1+K2 用了 ~0.9s（含失败的 basic 尝试），V 只剩 0.7s。如果优化前面阶段（减少浪费）并优化 V 阶段搜索，也许能在 1.55s 内完成。

但 V 阶段单独需要 3.69s（即使 6 分支可能降到 1-2s）。仍超。

**关键改进：启发式**。V 阶段 A* 慢是因为 h 低估（relax+12 对 PIT），导致搜索像 Dijkstra 一样扩散。让我用一个更精确的启发式：预计算"从每个格到 V 的加权距离"，其中 PIT 视为可通过（cost 2，代表跳跃/填坑），ONEWAY 方向性保留。这已经接近 `_dist_map` 的 relax 部分（PIT cost 8）。把 PIT cost 降到 2，能更准确（JUMP 一步跨 2 格 cost 1）。这会让 h 更大（更接近真实），A* 更聚焦。

但 `_dist_map` 的 strict 部分在 PIT 阻断时给 INF，用 relax+12 兜底 → 值偏大（+12）。这应该让 A* 更贪心才对。weighted 1.85 又放大。Hmm，但 3.69s 说明搜索仍扩散很大。

也许问题在于 **A\* 的状态 key 含 `dt`（地形覆盖）**：BOMB 炸墙会改变 dt；但 V 阶段不需要 BOMB。JUMP 不改变 dt。所以状态数主要来自 pos × phase(12) × hp × jumps × keys × flipped × do(boxes)。boxes 有 4 个，推箱会改变 do → 状态多。

嗯，3.69s 找到的是 25 步解，但搜索了大量状态。

**替代思路**：不必在 Turn1 解完；让 Turn>1 每回合重规划，但**每次只规划一个短视界**（比如 8 步），逐步向 V 推进。当前 `_plan_from_state` 要求完整 CLEARED 才返回，失败就部分计划。可以改成：**若完整规划失败，返回"朝目标推进 N 步的最优前缀"**（从 A* 搜索中取 g 最小/h 最小的节点，回溯其路径）。这样每回合都能产出有效动作，逐步推进，最终到达 V。

这是很实用的改进！实现：在 `_stage_search` 里记录"最佳部分节点"（h 最小的状态），若搜索失败（超时/无解），返回到该节点的动作序列（前缀）。这样即使找不到完整解，也能给出"朝目标推进若干步"的计划。然后 `decide_action` 执行该前缀，之后重新规划。多个回合累积，逐步逼近。

风险：可能卡在局部最优（比如 PIT 前无法前进）。但对多数图有效。

让我实现：
```
def _stage_search(..., allow_partial=False):
    ...
    best_node = (hfun(sim), 0, 0)  # (h, nid, g)
    ...
    while ...:
        ...
        h = hfun(s)
        if h < best_node[0] - 1e-9 or (h == best_node[0] and g > best_node[2]):
            best_node = (h, nid, g)
        ...
        if goal_test(s): return full seq
    # 失败：返回到 best_node 的路径（前缀）
    if allow_partial and best_node[1] != 0:
        seq = reconstruct(best_node[1])
        return seq, sims[best_node[1]]
    return None
```
但注意：部分计划可能很长（很多步），且不一定推进（best_node 可能是某个 h 小的死角）。可以限制前缀长度（比如最多 12 步）。

然后 `_plan_from_state` 在阶段失败时用部分结果继续（但不标记为"阶段完成"，直接返回累计 out）。

不过这会让 `_certificate` 也拿到部分计划 → 验证不通过（要求 CLEARED）→ 用 fallback。OK，`_certificate` 会检查。

嗯，但 `_plan_from_state` 里 `return out if sim.status == "CLEARED" else None` 最后一行 —— 如果用了部分计划，最后应返回 out（不管是否 CLEARED）。我要调整：
- 加一个标志 `partial_ok`，若某阶段返回部分计划，则 `return out`（不要求 CLEARED）。

这样 `decide_action` 会缓存部分计划并执行，逐步推进。

让我实现。这可能是提升 TIMEOUT 局分数（拿钥匙/推进）的关键。

不过要小心：`_certificate` 用 `_plan_from_state` 生成自证解，如果返回部分计划，验证失败 → fallback（170 步带伤）。但我自己的图规划完整成功（0.016s），不受影响 ✓。

实现细节：
- `_stage_search` 增加参数 `allow_partial=False`。
- 记录 `best = (h, nid, g)`，只在 `s.status == "PLAYING"` 时更新。
- 失败时若 `allow_partial` 且 `best[1] != 0`，返回 `(seq, sims[best[1]])`，并标记 `partial=True`（通过返回值第三项）。
- 为简化，我让 `_stage_search` 返回 `(seq, sim, is_partial)` 三元组？会破坏现有调用（诊断脚本、命令）。改为：返回 `(seq, sim)` 二元组不变，但在 `_plan_from_state` 里通过 `sim.status != "CLEARED"` 判断最后阶段是否部分。嗯，对于非 V 阶段，goal_test 不是 CLEARED，所以无法用 status 判断。

更简单：给 `_stage_search` 加 `allow_partial` 参数，返回 `(seq, sim, partial_flag)`；更新所有调用点（submission 内部 1 处 + 诊断脚本/命令里的调用）。诊断脚本是我自己的工具，可以更新或忽略（它们只是临时工具）。但刚才我用的 python -c 命令直接调用 `_stage_search` 并解包 2 元组，只用于诊断，不影响交付。

我决定：保持 `_stage_search` 返回二元组，但**新增一个函数 `_stage_search_partial`**（包装），或者直接在 `_stage_search` 里通过模块级变量记录？太 hacky。

干脆修改 `_stage_search` 返回三元组，并更新 `v22_diag.py`/`v22_diag2.py`（它们是我写的临时工具，可以更新），以及 `_plan_from_state`。命令里的诊断调用会报错，但我不再用那些命令。

嗯，为了少改动，我用一个折中：`_stage_search` 保持二元组，但**增加一个可选参数 `partial_out`（list）**，函数把部分计划放进这个 list。调用方检查 list 是否非空。有点丑但改动小。

其实最干净：新增函数 `_stage_prefix(sim, hfun, deadline, acts, max_states)` 专门做"限时找最优前缀"，只在 `_plan_from_state` 阶段失败时调用。它内部逻辑与 `_stage_search` 类似但目标是最小化 h。重复代码，但独立清晰。

考虑时间，我采用**改 `_stage_search` 返回三元组**，并同步更新两个诊断脚本（不重要，可以删除它们——它们是临时工具，最后清理时删掉）。实际上最后我会删除 diag 脚本（用户要求文件都放该文件夹，但临时工具可以保留或删除；为整洁，最后删掉）。

好，实施：

```
def _stage_search(sim, goal_test, hfun, deadline, acts, max_states=45000, allow_partial=False):
    ...
    best = (hfun(sim), 0, 0.0)  # (h, nid, g)
    while ...:
        ...
        hh = hfun(s)
        if s.status == "PLAYING" and (hh < best[0] - 1e-9 or
            (abs(hh-best[0])<1e-9 and g > best[2])):
            best = (hh, nid, g)
        if goal_test(s): return seq[::-1], s, False
        ...
    if allow_partial and best[1] != 0 and best[1] in sims:
        seq = reconstruct(best[1])
        if seq: return seq[:12], sims[best[1]], True
    return None
```
注意：返回 `None` 时调用方需要检查。现在统一返回三元组或 None。

`_plan_from_state`:
```
res = _stage_search(..., allow_partial=(nm==last? no, all))
if res is None: return out if out else None
seq, sim, partial = res
out.extend(seq)
if partial: return out   # 前缀计划，后续回合再规划
```
但要小心：部分计划返回时，`sim` 是部分状态，后续阶段不该继续（因为阶段未完成）。直接 return out ✓。

另外 `_certificate` 调用 `_plan_from_state` 会拿到部分计划 → 验证 CLEARED 失败 → 返回 None → fallback。对我自己的图，完整规划成功（不触发部分）✓。

还要注意：`_stage_search` 的 `best` 更新要避免把"高 g 但低 h"的死角当最佳。用 `hh` 最小优先 ✓。

以及前缀长度限制 12 步 —— 太短会导致每 12 步重规划一次（Turn>1 0.3s），可能反复。但至少推进。可以设 20。

让我实现，然后重测所有图。

另外，还要**动态动作集**（避免 jumps 耗尽）：在 `_plan_from_state` 的阶段循环里，每阶段根据当前 sim 重新计算 `_action_sets(sim)`。并给 JUMP 加 cost（在 `_stage_search` 的 cost 里 `+3.0 if a.startswith("JUMP_")`）。

这样保留跳跃资源，V 阶段才有机会。

实施。
````

## 152.1 · Thinking

```
我需要重新读该段代码确认当前内容。可能之前的替换改变了 `1.35` → `1.85`？我记得我改的是 `1.35` → `1.85`，但后来写的代码里是 1.85。让我读。
```

## 156.1 · Thinking

````
好，代码是 2 元组返回。我决定**不改成 3 元组**（避免破坏诊断命令），而是新增一个模块级辅助函数 `_stage_prefix`，在阶段失败时单独调用，做一个短的"贪心推进"搜索。这样改动小且清晰。

`_stage_prefix(sim, hfun, deadline, acts, max_states=20000, max_len=20)`：
- 用 A* 类似循环，但不找 goal，只找"h 最小的状态"，限时。
- 返回到该状态的动作序列（最多 20 步）。
- 为避免与 `_stage_search` 重复，我可以让它调用 `_stage_search` 并传一个永远 False 的 goal_test，同时 `allow_partial` 参数…… 嗯，还是需要改 `_stage_search`。

好，我改 `_stage_search` 增加一个**可选参数 `allow_partial=False`**，返回类型根据参数变化（调用方知道）。为了兼容，当 `allow_partial=True` 且失败时返回 `(seq, sim, True)`，成功时返回 `(seq, sim, False)`；当 `allow_partial=False`（默认）时保持 2 元组。这样现有调用（诊断命令）不受影响，但 `_plan_from_state` 用 allow_partial=True 并处理 3 元组。

这有点不一致但可行。或者更简单：**保持 2 元组，失败时返回部分计划**（若 allow_partial=True），调用方通过 `sim` 是否满足 goal_test 判断是否完整。但 `_plan_from_state` 里可以检查 `test(sim2)` 是否为 True 来判断。这更简洁！

实现：
```
def _stage_search(..., allow_partial=False):
    ... 记录 best ...
    if goal_test(s): return seq, s
    ... 失败时 ...
    if allow_partial and best_nid != 0:
        return _reconstruct(parents, best_nid)[:20], sims[best_nid]
    return None
```
调用方：
```
res = _stage_search(..., allow_partial=True)
if res is None: ...
seq2, sim2 = res
out.extend(seq2)
if not test(sim2): return out  # 部分计划，交给后续回合
sim = sim2
```
✓ 干净。

让我做这个替换（用当前精确文本）。
````

## 158.1 · Thinking

```
现在改 `_plan_from_state` 的阶段循环，使用 `allow_partial=True`，动态动作集，并检查 `test(sim2)`。

当前代码（读一下）。
```

## 160.1 · Thinking

```
改阶段循环：
- 每阶段动态 `basic, full = _action_sets(sim)`。
- `allow_partial=True` 传给所有 `_stage_search`。
- 若 `test(sim)` 为 False（部分计划未完成阶段），返回 out（部分计划）。
- 最后 `return out`（不再强制 CLEARED；但 `_certificate` 会验证）。

注意：如果返回部分计划，`decide_action` 里 `ok` 会是 False，但 `len(seq)>1` 允许缓存 ✓。

还要考虑：**部分计划可能导致 `_certificate` 拿到非完整解** → 验证失败 → fallback ✓。

另外 `_plan_from_state` 返回空列表 `[]` 时，`decide_action` 的 `if seq:` 为 False → 走贪心 ✓。

写替换。
```

## 162.1 · Thinking

````
注意：现在 `_plan_from_state` 总是返回 out（可能部分计划）。`_certificate` 会验证 CLEARED ✓。`decide_action` 的 `if seq:` 会接受部分计划 ✓。

但有个问题：如果部分计划只有 1 步（比如 best prefix 1 步），`decide_action` 里 `if ok or len(seq)>1` → len=1 且 ok=False → 不缓存，走贪心。这没关系（贪心也能动）。但更好是允许 1 步部分计划。改条件为 `if seq:` 即可（我们已确认 seq 非空且动作合法）。不过 `ok` 检查是为了确保计划有效；部分计划也是有效的动作序列（只是不完整）。让我把条件放宽：`if ok or seq:` → 总是 True（因为 seq 非空）。但要注意：**部分计划可能是"prefix 到某个 h 最小状态"，该状态可能不是最优方向**，但仍可执行。执行后 Turn>1 重规划。合理。

改 `if ok or len(seq) > 1:` → `if seq:`。

另外要检查 `decide_action` 里生成 sigs 的循环：
```
for a in seq:
    if sim.status != "PLAYING": break
    sim.step(a); sigs.append(...)
```
若部分计划执行完 sim 仍 PLAYING ✓，sigs 长度 = len(seq)+1 ✓。

让我改条件。

还有 `memory["cooldown"]=0` 在成功时设置 → 部分计划也算成功，会清除 cooldown，导致每回合重规划（部分计划可能只有 20 步），OK。

改。
````

## 164.1 · Thinking

```
现在 `ok` 变量没用了（只在赋值），可以保留（无害）或删。稍后清理。

重跑完整测试（own + bench）。注意 `_certificate` 现在可能拿到部分计划 → fallback。我自己的图应该仍完整解。

跑。
```

## 166.1 · Thinking

````
**BENCH_STRONG CLEARED 108 步 100HP！** 强基准打过了（参考 115 步 100HP）。很棒。

但 part1 结果变差：8 通关、1 死、5 超时（之前 10 通关、0 死、4 超时）。而且 hunyuan 从 CLEARED 229 → TIMEOUT，hydrogen 从 CLEARED 81 → TIMEOUT。

原因：**部分计划机制让 Turn1 返回"不完整"的前缀计划**，而不是完整解；执行完前缀后 Turn>1 重规划（0.3s）可能失败 → 贪心/冷却 → 卡住。之前一次性完整解在 Turn1 内完成，直接执行到底。

具体：我的 `_plan_from_state` 现在在阶段失败时返回部分计划，即使**后续阶段本来能成功**（只是预算不够）。而且 `break` 条件 `if not test(sim) or time.monotonic() > deadline: break` —— 如果 basic 阶段返回部分计划（`test(sim)` False），且 `full` 搜索也没完成，就 break 返回部分。之前会返回 None → 贪心。嗯。

更糟：**`_plan_from_state` 现在总是返回 out**（即使不完整），导致 `decide_action` 不再走"完整规划失败"的逻辑；Turn1 缓存部分计划，执行 20 步后重规划，但 Turn>1 只有 0.3s，可能找不到完整解 → 又部分计划 20 步……逐步推进但可能卡在局部（比如需要长距离绕行时，每 20 步重规划，启发式引导可能重复）。

hunyuan（我的旧图）路径 229 步，Turn1 应该能完整解（之前 1.594s 刚好）。现在部分计划机制让某些阶段返回前缀，导致失败。

**改进**：让部分计划只在"确实无法完成全部阶段"时作为最后手段，且**优先尝试完整规划**。具体：
- 阶段搜索先用 `allow_partial=False`（严格），只在该阶段完全失败且 `out` 为空或无法继续时，才用 `allow_partial=True` 生成前缀。
- 或者：先跑一遍完整规划（所有阶段 allow_partial=False），若成功返回；若失败，再跑一次"宽松模式"（allow_partial=True）生成部分计划。

这样 Turn1 优先给完整解（像之前那样），强基准则需要部分计划（因为 V 阶段需要 3.69s，Turn1 无法完成）。

实现：给 `_plan_from_state` 加参数 `allow_partial`（bool）。`decide_action`：
```
seq = _plan_from_state(state, deadline1, ..., allow_partial=False)
if seq is None and time left:
    seq = _plan_from_state(state, deadline, ..., allow_partial=True)
```
但两遍会消耗时间。Turn1 1.55s：第一遍完整规划可能用满 1.55s（hunyuan 1.59s 超了？之前 1.594 是含开销，budget 1.55 → 应该 1.55 内）。若第一遍失败，剩很少时间做第二遍。

嗯。折中：**阶段内先严格搜索（allow_partial=False），失败后再用 allow_partial=True 在同一 deadline 内重试**？重试会浪费。

更简单的方案：**部分计划只在最后一个阶段（V）或"阶段完全无解"时启用**，且**返回部分计划时不做 `break`，而是继续尝试后续阶段**（如果前缀状态已满足某些条件）。

其实核心问题是：为什么 hunyuan/hydrogen 变 TIMEOUT？让我诊断一下 Turn1 的完整规划是否成功。

之前（无部分计划）hunyuan CLEARED 229，hydrogen CLEARED 81。现在 TIMEOUT。差别是：
1. 部分计划机制。
2. 动态 `_action_sets(sim)`（每阶段重新计算）。
3. JUMP cost +3。
4. `_stage_search` 里 best 记录（轻微开销）。
5. 阶段循环里 `basic` 结果若 `not test(res[1])` 就用 full 重搜（现在 basic 允许部分计划，所以 `res` 几乎总非 None → 总是跑 full 重搜，浪费时间！）。

看代码：
```
res = _stage_search(..., basic, allow_partial=True)   # 即使失败也返回部分计划（非 None）
if res is not None and not test(res[1]) and full != basic:
    res2 = _stage_search(..., full, allow_partial=True)
    ...
```
所以 basic 失败（返回部分）→ 仍跑 full，且 full 的 deadline 是 `now + 0.72*avail`（比 basic 的 0.28*avail 大）→ full 从 now 开始跑，可能用 0.72*avail。这本身没问题。但 `res2` 也可能返回部分计划，`hfun(res2[1]) < hfun(res[1])` 比较 → 选更好的。OK。

但 **`if not test(sim): break`** 让部分计划提前终止，不再尝试后续阶段。这是有意的（阶段未完成，后续阶段基于未完成状态无意义）。

然而对 hunyuan：Turn1 完整规划应该能成功（之前能）。现在为什么不能？可能是 `full` 动作集变化（动态生成，含 JUMP cost）导致搜索变慢？或者 best 记录开销？

让我直接诊断 hunyuan 的 Turn1 规划结果。

另外 **glm DEAD**（D=100）—— 部分计划把勇者带进了危险区，Turn>1 重规划失败 + 贪心 → 死。

我需要更谨慎：**部分计划应只在确实能保证安全的情况下返回**（best prefix 的状态 hp==100 且不在激光射线内）。而且部分计划返回的动作序列必须安全（A* 已排除 DEAD，但可能吃 50 伤）。

让我重新设计，回到更稳健的架构：

**方案：Turn1 优先完整规划；若失败，才用部分计划，并保证部分计划质量。**

具体：
```
def _plan_from_state(..., allow_partial=False):
    # 阶段循环，_stage_search(..., allow_partial=allow_partial)
    # 若某阶段返回部分（not test(sim)）:
    #   若 allow_partial: break 并返回 out
    #   否则: return None
```
`decide_action`：
```
seq = _plan_from_state(state, deadline, ..., allow_partial=False)
if not seq:
    # 用剩余时间（如果有）做宽松规划
    seq = _plan_from_state(state, deadline, ..., allow_partial=True)
```
但两遍搜索时间翻倍。Turn1 1.55s：第一遍严格规划若用满 1.55s 仍失败，第二遍没时间。

**替代**：在阶段循环里，**只有到最后一个阶段仍无法完成时才启用部分计划**。即：先尝试所有阶段的严格搜索；若某阶段严格失败，记录失败但继续？不行，状态没推进。

嗯。让我用另一种方式：**保留部分计划，但让 Turn>1 的重规划更可靠**。Turn>1 预算 0.3s；但如果 plan 执行完（20 步）后重规划，此时离目标更近，搜索应该更快。对 hunyuan（229 步长路径），每 20 步重规划一次，0.3s 内能否找到"到 K1"的阶段？可能不够（K1 距离 50 步）。

**关键**：可以让 Turn>1 的预算更大（0.45s，仍 <0.5s），并且**只在 plan 耗尽时重规划**（20 步一次，频率低）。而且 cooldown 不要过早触发。

但 hunyuan 的 Turn1 完整规划本来能成功（1.59s >1.55 budget，所以之前是 `worst_step 1.594@t1`，说明 Turn1 用了 1.594s，超过我设的 1.55 budget？`_plan_from_state` 的 deadline = start+1.55，但阶段循环的 full 搜索 `deadline if nm=="V"` 用的是传入 deadline ✓。1.594 包含 `_Sim(state)` 构造 + sigs 生成等开销。所以规划本身 ≤1.55s。刚好够。

现在加了部分计划 + 动态动作集 + best 记录，规划变慢 → 1.55s 不够 → 某阶段返回部分 → 整体不完整 → TIMEOUT。

**结论**：需要提高搜索效率或减少开销。

优化：
1. **去掉动态 `_action_sets(sim)` 每阶段调用**（遍历 1040 格 × 3 次，~3ms，不大）。
2. **`_stage_search` 的 `hfun(s)` 每次 pop 调用**（之前只在 push 时算）——我加的 best 记录调用 `hfun(s)` 每节点一次，增加开销。`hfun` 是 dict.get，很快。
3. **JUMP cost +3** 改变搜索路径（可能更慢）。
4. **basic 阶段返回部分计划后仍跑 full**（浪费 basic 的时间 0.28*avail）。

嗯，效率问题可能主要是 4：basic 用了 0.28*avail（~0.43s）却只得到部分计划（无用），然后 full 从 now 开始（now 已过 0.43s）到 0.72*avail（0.72*1.55=1.12s，绝对时间），所以 full 实际只有 ~0.7s。之前 basic 失败返回 None（快速，0.43s）→ full 同样 0.7s。一样。

之前 hunyuan 完整规划成功用了 1.594s（Turn1 总耗时）。现在 TIMEOUT 说明规划没成功。

让我直接诊断：对 hunyuan 跑 `_plan_from_state` 看返回什么、各阶段耗时。用 wrap（2 元组解包仍适用）。

我先做诊断，再决定。

同时，我注意到 **BENCH_STRONG CLEARED 108 步** 是重大成果（强基准打过），但用户提示"打过强基准也不代表强" —— 意味着不要因为打过强基准就自满，通用性更重要。所以我要兼顾 part1 的通关率。

让我诊断 hunyuan/hydrogen/glm。
````

## 168.1 · Thinking

````
诊断清楚了：

- **hunyuan**：前两阶段（K2 59 步、K1 132 步）成功，V 阶段失败返回 20 步前缀（两次尝试）。总序列 211 步，重放到 (33,3) 仍 PLAYING。所以 Turn1 给了 211 步部分计划，执行到 Turn 212 才重规划，只剩 28 回合 → 来不及到 V → TIMEOUT。之前完整规划（229 步）在 Turn1 内成功。现在 V 阶段 0.42s+1.14s 都失败（部分计划），而之前完整 V 阶段能成功（总 1.594s）。

  关键：**V 阶段从 (14,2) 到 (37,13) 需要 ~38 步（含绕障碍）**，之前完整规划能找到；现在因为 JUMP cost +3、动态动作集、以及 basic 先跑 0.28*avail 浪费，full 时间不足。

- **hydrogen**：Turn1 完整规划成功（81 步，0.672s）！但测试结果显示 TIMEOUT。说明**执行阶段出问题**：plan 缓存校验失败导致重规划/贪心。为什么？`sigs` 校验应该一致…… 可能因为 `_Sim.state()` 里 `terrain` 的 CHEST 解码、或 `plates_active` 等不一致，导致 sig 不匹配 → 每回合重规划 → 但重规划应该也能成功（0.3s）→ 也许 cooldown 触发导致贪心。

  等等，hydrogen 完整规划 81 步，但测试里 TIMEOUT keys=[False,True]。说明勇者只拿到 1 把钥匙，没按计划走。可能是 plan 执行几步后 sig 不匹配 → 重规划 → 新规划可能只给部分计划（20 步）→ 逐步推进但卡住。

  **sig 不匹配的原因**：`_sig_of_sim(sim)` 用 `sim.turn`，`_sig_of_state(state)` 用 `state["turn"]`。一致。但 **`_Sim._from_state` 用 `_decode_chest` 重建 bt，而 plan 执行中的 sim 是从 `_Sim(grid=grid)`（或 `_Sim(state=state)`）构造的**。两者对 CHEST 的解码可能不同：从 `state` 构造时，clues 来自 `_Sim.state()` 生成的 clues（每个 MIMIC 在其四邻 EMPTY 标一个 clue）；`_decode_chest` 把"四邻有 clue 的 CHEST"判为 MIMIC。如果地图中有 HEAL 且恰好邻着一个 MIMIC 的 clue 格，会被误判为 MIMIC → 状态不一致（但 sig 不含地形，所以不影响 sig）。sig 只含 turn/pos/hp/keys/flip/plates/jumps/throws/bombs/炸弹数。这些应该一致。

  除非：**`plates_active` 不一致**。`_Sim.state()` 输出 `plates_active()`；`_sig_of_state` 用它。`_sig_of_sim` 用 `sim.plates_active()`。一致。

  嗯，那为什么 hydrogen TIMEOUT？让我直接跑 play 并打印前几回合的动作与 plan 状态。

  等等，可能是 **memory 的 cooldown**：Turn1 完整规划成功 → `memory["cooldown"]=0`。执行中 sig 匹配 → 直接返回 plan[idx]。若某步 sig 不匹配 → 重规划（0.3s）→ 新规划可能返回部分计划 → 缓存 → ... 逐步但可能偏离。

  让我直接诊断 hydrogen 的 play 前 20 回合。

- **glm**：所有阶段都返回部分计划（20 步前缀），没有真正完成 K1/K2/V。但阶段循环里 `if not test(sim): break` 应该在第一阶段就 break。诊断显示 4 个 stage 都跑了？因为 wrap 打印了 4 次，说明 `test(sim)` 在部分计划后仍为 False 但循环没 break？看代码：`if not test(sim) or time.monotonic() > deadline: break` —— 应该 break。但诊断里 4 个 stage 都执行了，说明 `test(sim)` 返回 True？第一个 stage 是 K1 或 K2，`done=False` 打印说明 `goal(r[1])` 为 False。但 `test` 在 `_plan_from_state` 里是 `lambda s: s.h["keys"][0]` 等，与 wrap 里的 `goal` 相同。所以 `test(sim)` 应为 False → break。为什么没 break？

  哦！我看错了：wrap 打印的 "stage OK seq=20 done=False" 中 `done` 是 `goal(r[1])`。但 `_plan_from_state` 里 `res` 可能被 `res2` 替换（full 搜索结果），而 wrap 打印的是每次 `_stage_search` 调用（包括 basic 和 full）。所以 4 次打印 = 2 个阶段 × 2 次调用（basic + full）。glm 第一阶段 basic 部分 + full 部分 → break。TOTAL 32 步（20+12）。嗯，打印显示 4 次，但只有 2 个阶段。

  OK。**glm DEAD** 是执行部分计划后重规划 + 贪心导致。

**核心问题**：部分计划机制让很多图退化。我需要**让完整规划优先**，部分计划只在完整规划彻底失败时作为兜底。

方案：**两遍法，但第一遍快**。
```
def decide_action(...):
    seq = _plan_from_state(state, deadline, ..., mode="exact")   # 严格，allow_partial=False
    if seq is None:
        seq = _plan_from_state(state, deadline, ..., mode="partial")  # allow_partial=True
```
但第二遍没时间。不过**第一遍严格搜索会快速失败**（因为阶段失败就返回 None，不浪费在部分计划上），可能只花 0.3-0.5s，然后第二遍有 1.0s 可用。

实际上，之前（无部分计划）hunyuan 完整规划成功用了 ~1.59s（几乎全部预算）。所以第一遍严格搜索对 hunyuan 会用满 1.55s 并成功 ✓。对 BENCH_STRONG，第一遍严格搜索会失败（V 阶段需 3.69s），花掉 1.55s，第二遍没时间 → 强基准又打不过。

矛盾。

**解决**：让 `_plan_from_state` 在阶段循环里**对每个阶段先严格搜索；若该阶段严格失败，则生成部分计划并立即返回**（这就是当前行为）。区别在于：当前实现里 **basic 阶段用 allow_partial=True**，导致 basic 失败时返回部分计划，然后还跑 full（浪费）。应该：
- basic **严格**（allow_partial=False），失败返回 None。
- full **严格**，失败返回 None。
- 只有 **当所有尝试都失败且 out 为空时**，才做一次 allow_partial=True 的前缀搜索（用剩余时间）。

这样：
- hunyuan：basic/full 严格搜索 V 阶段。之前完整规划成功（无部分计划版本），应该仍成功。
- BENCH_STRONG：V 阶段严格失败 → 生成前缀 → 返回部分计划 → 后续回合重规划 → 最终通关（之前就是这样成功的）。

嗯，但 BENCH_STRONG 的成功依赖部分计划。而 hunyuan 的失败也因为部分计划。区别：hunyuan 的 V 阶段**可以严格成功**（若给足时间），BENCH_STRONG 的 V 阶段严格失败。

所以：严格优先 + 失败才部分 = 两全。

实现：
```
for nm, test, hfun in stages:
    ...
    res = _stage_search(..., basic, allow_partial=False)
    if res is None and full != basic:
        res = _stage_search(..., full, allow_partial=False)
    if res is None:
        # 最后手段：前缀
        now2 = time.monotonic()
        if now2 < deadline - 0.02:
            res = _stage_search(sim, test, hfun, deadline, full_or_basic, allow_partial=True)
        if res is None:
            return out if out else None
    seq, sim2 = res
    out.extend(seq)
    if not test(sim2):
        return out  # 部分计划
    sim = sim2
```
关键：**basic 与 full 的时间分配**。之前 basic 0.28*avail、full 到 0.72*avail。对 hunyuan 的 V 阶段（第 3 阶段，前面用了 0.047s，avail≈1.5s）：basic 0.42s（可能失败），full 到 1.08s（绝对）→ full 从 0.42s 开始，只有 0.66s。之前完整规划成功用了 ~1.5s（V 阶段占了 ~1.5s）。所以 full 需要更多时间。

让我给 full 更多：`now + 0.95 * avail`（几乎全部剩余）。basic 用 `now + 0.15*avail`（短试探）。这样 V 阶段 full 有 ~1.4s。

对 BENCH_STRONG：plates 0.11s + K1 0.06s + K2 0.016s ≈ 0.19s，V 阶段 basic 0.2s（失败），full 到 deadline（1.55s）→ 1.35s → 严格失败 → 前缀搜索（没时间了）→ 返回 None？那就打不过强基准了。

嗯。之前 BENCH_STRONG 成功是因为**部分计划**：V 阶段返回 20 步前缀，执行 20 步后 Turn>1 重规划（0.3s），逐步推进到 V。实际 CLEARED 108 步（不是 82+25=107，接近）。所以 Turn>1 的重规划成功了（因为离 V 更近，0.3s 够）。

所以部分计划机制对 STRONG 有效，对 hunyuan 有害（因为 hunyuan 的路径太长，每 20 步重规划 0.3s 不够，且部分计划把 V 阶段的完整解拆散）。

**折中方案**：让部分计划的**前缀长度更长**（比如 60 步而不是 20），这样 hunyuan 的每个前缀更长，重规划次数少。但 V 阶段严格搜索失败时，前缀状态 h 最小可能是"局部最优"，60 步前缀可能走进死角。

嗯，让我换个思路：**hunyuan 的 V 阶段其实可以严格成功**（之前版本可以）。让我检查当前为什么不行：之前（无部分计划、无 JUMP cost、静态动作集）hunyuan 完整规划 229 步成功，耗时 1.594s（Turn1）。现在 V 阶段 basic 0.422s 部分、full 1.140s 部分 —— full 用了 1.14s 但返回部分（不是严格失败，因为 allow_partial=True 让它在搜索耗尽时返回前缀）。也就是说 **full 严格搜索在 1.14s 内没找到 V**，但之前版本在 ~1.5s 内找到了。

差别：JUMP cost +3、动态动作集、以及 best 记录开销。还有 `basic_dl = now+0.28*avail`（0.42s）先浪费了。如果给 full 从 0 到 deadline（1.55s）的完整时间，应该能找到。

所以：**basic 严格短试探（0.08s），full 严格到 deadline**。若 full 严格失败 → 前缀兜底。

让我重新设计时间分配：
```
now = time.monotonic(); avail = deadline-now
if nm == "plates":
    res = strict(sim, test, hfun, now + min(0.9, 0.6*avail), basic)
else:
    res = strict(sim, test, hfun, now + 0.12*avail, basic)   # 短试探
    if res is None and full != basic:
        res = strict(sim, test, hfun, deadline, full)         # 用满剩余
    if res is None:
        res = prefix(..., deadline, full)
```
问题：非最后阶段用满 deadline 会让后续阶段没时间。但若该阶段是必需的，宁可完成它。对 hunyuan：V 是最后阶段，用满 ✓。对 STRONG：V 是最后阶段，用满 → 严格失败 → 前缀兜底（但没时间了）→ 返回 None。

嗯，可以给 V 阶段"部分计划"预留时间：full 严格搜索到 `now + 0.75*avail`，然后前缀搜索 `deadline`。这样 STRONG 的 V 阶段前缀有时间，hunyuan 的 V 阶段 full 有 0.75*1.5=1.13s（可能不够 1.5s）。

难以两全。

**另一个思路**：识别"V 阶段是否需要跨坑/复杂机关"，对复杂图用部分计划，对简单图用完整规划。太 hacky。

**更实际的思路**：接受 hunyuan/hydrogen 等部分退化，但通过**改进 Turn>1 重规划**让部分计划也能最终通关。Turn>1 预算 0.30s，可以提到 **0.45s**（<0.5s，留 0.05 余量）。并且**部分计划长度设为 40 步**（减少重规划次数）。这样 hunyuan 211 步部分计划后，重规划 0.45s 可能找到剩余 18 步到 V（离目标近，搜索快）。

而且 hydrogen 的完整规划（81 步）在 Turn1 成功，但测试中 TIMEOUT —— 这更可能是 **plan sig 校验失败** 导致重规划。让我先诊断这个，因为它可能是个 bug（修了能恢复多张图）。

让我跑 hydrogen 的 play 前 15 回合，打印 decide_action 是否走缓存。用 monkeypatch 包装 `_plan_from_state` 统计调用次数。

写命令。
````

## 170.1 · Thinking

```
缓存工作正常！hydrogen 前 21 步按计划执行。那为什么测试里 TIMEOUT？可能在某一步 sig 失配导致重规划。让我跑完整 240 回合看何时 calls 增加。

注意 t=4：`MOVE_R pos=(4,13)` 但 t=3 也是 pos=(4,13) 且动作 MOVE_U → 说明 t=3 的 MOVE_U 被阻挡（可能墙），实际位置没变。但 plan 预期 t=4 的位置是 (5,13)? 实际 t=4 pos=(4,13)。等等：
- t=2 pos=(3,13), 动作 MOVE_R → t=3 pos=(4,13) ✓
- t=3 pos=(4,13), 动作 MOVE_U → t=4 pos=(4,13)（被阻挡，没动）
- t=4 pos=(4,13), 动作 MOVE_R → t=5 pos=(5,13) ✓

嗯，plan 里 MOVE_U 在 t=3 被阻挡但计划继续执行，说明我的 A* 模拟与实际一致（A* 也知道被阻挡），所以没问题。

让我跑到 240 看 calls。
```

## 172.1 · Thinking

```
单独跑 hydrogen 是 CLEARED 81！但 `v22_local_test.py bench` 里显示 TIMEOUT。为什么？可能是**测试脚本里连续跑多张图，`submission` 模块状态被污染**？不，`_Sim` 是纯对象，`memory` 每次新建。

哦！可能是 `random.seed(20261115)` 全局状态？我没用 random。

或者：**测试脚本里 `play()` 用 `S._Sim(grid=grid)`，`grid` 来自 JSON（list of lists）**，与我刚才命令一样。

等等，测试脚本输出 `part1 hydrogen TIMEOUT T=240 hp=100 keys=[False, True]`。而我单独跑 CLEARED 81。差异可能是**测试脚本先跑了其他图，某些模块级状态被改变**？`submission` 里没有全局可变状态（除了常量）。

啊，我知道了：**测试脚本 `benchmarks()` 里先跑 BENCH_WEAK 和 BENCH_STRONG，然后跑 part1**。BENCH_STRONG 的部分计划可能让 `time.monotonic()` 无关…… 不，没有全局状态。

嗯，或者是**测试脚本里 `play()` 的 `max_turns=240` 循环条件**：`while sim.status == "PLAYING" and len(acts) < max_turns`。一样。

让我重新跑 bench 单独看 hydrogen，或者直接检查测试脚本里 hydrogen 的 grid 是否与 part1 JSON 一致。可能是 `d2["dungeons"]` 的迭代顺序导致…… 不。

等等！我刚改了 `decide_action` 的条件 `if seq:`（之前 `ok or len(seq)>1`）。测试脚本是在我改动**之后**跑的吗？让我看时间线：
- 我改了 `if seq:` 之后跑了 `own` + `bench`（输出 hydrogen TIMEOUT）。
- 然后诊断 `_plan_from_state`（返回 81 完整序列）。
- 然后单独跑 hydrogen play → CLEARED 81。

所以同一份代码，单独跑 CLEARED，bench 里 TIMEOUT。说明**测试脚本有状态污染或差异**。

啊，我怀疑是 `v22_local_test.py` 里 `play()` 调用 `S.decide_action(st, mem)`，而 `st = sim.state()`。`sim.state()` 会生成 `clues`（对每个 MIMIC 在其四邻 EMPTY 标 True）。`_Sim._from_state` 用 `_decode_chest` 把 CHEST 判为 MIMIC/HEAL。这与从 grid 构造的 sim 一致…… 应该。

让我直接在测试脚本里单跑 hydrogen：`python v22_local_test.py` 不支持指定 part1 某图，但我可以写命令调用 `v22_local_test.play`。

让我做：import v22_local_test as T; T.play(g) 打印结果。看是否 CLEARED。

另一个可能：**`bench` 输出里 hydrogen TIMEOUT 是旧结果**（我可能看的是上一次运行的输出？不，最后一次运行输出里有 `hydrogen TIMEOUT T=240`）。

让我复现：连续跑 BENCH_WEAK、BENCH_STRONG、然后 hydrogen，看是否 TIMEOUT。可能 **BENCH_STRONG 的部分计划导致 `time.monotonic()` 无关，但 `random` 无关**……

哦！我想到了：**`_Sim` 的 `bt` 是 list of lists，从 grid 构造时用 `[list(r) for r in grid]` —— 浅拷贝每行**，OK。但 `_Sim._from_state` 里 `self.bt = _decode_chest(state["terrain"], clues)` 生成新列表，OK。

嗯，还有一个可能：测试脚本 `benchmarks()` 里对 part1 图调用 `play(g)`，但 `g = dd["grid"]` 是**从 JSON 加载的 list of lists**，与 `v22_sparring_benchmarks` 的 grid 一样。没问题。

让我直接复现连续运行。写命令。
```

## 174.1 · Thinking

````
有意思：`T.play(g)` 单独跑 TIMEOUT，但我之前手写的循环（用 `sim.state()` + `decide_action`）CLEARED 81。差异在哪？

看 `T.play`：
```
def play(grid, verbose=False, max_turns=240):
    sim = S._Sim(grid=grid)
    mem = {}
    ...
    while sim.status == "PLAYING" and len(acts) < max_turns:
        st = sim.state()
        a = S.decide_action(st, mem)
        sim.step(a)
    return ...
```
我的手写循环：
```
while sim.status=='PLAYING' and sim.turn<=240:
    st=sim.state(); act=S.decide_action(st,mem); sim.step(act)
```
几乎一样！唯一差别：我手写循环里 monkeypatch 了 `_plan_from_state` 来计数（wrap 调用 orig(*a,**kw)）—— 这不该改变行为。

啊！**`T.play` 里 `max_turns=240` 用 `len(acts) < max_turns`，我的手写用 `sim.turn<=240`**。都跑 240 回合。

另一个差别：**我手写循环里 wrap 了 `_plan_from_state`，但 `decide_action` 内部调用的是模块全局 `_plan_from_state`，wrap 生效**。wrap 只是计数，不改变参数。

嗯，等等 —— 关键差别可能是 **`T.play` 里 `st = sim.state()` 每回合调用，而我手写也是**。

让我看 worst=1.125s@t1 —— Turn1 用了 1.125s，而我手写跑时 Turn1 用了 0.703s（完整规划 81 步）。**同一个图，Turn1 规划时间不同！** 说明 `_plan_from_state` 的结果不同（完整 vs 部分）。这是**非确定性**！

非确定性来源：`time.monotonic()` 截止时间。规划结果依赖机器负载/运行速度：如果在 1.55s 内某阶段严格搜索成功 → 完整计划；若超时 → 部分计划。而且 `_stage_search` 的 `best` 记录依赖搜索进度。

在我手写循环里（第一次运行，机器空闲），Turn1 0.703s → 完整 81 步。在 `T.play` 里，Turn1 1.125s → 部分计划 → 后续退化。

为什么同一份代码两次运行耗时差这么多？可能因为 **`_stage_search` 的搜索路径受 `deadline` 影响**：如果某阶段在 basic 短试探内没成功，就跑 full；full 到 deadline。不同运行中，basic 是否成功取决于时间…… 但 basic 是确定性算法（不受时间影响，除非超时）。`allow_partial=True` 让 basic 在超时时返回前缀；但 basic 的 deadline 是 `now + 0.28*avail`，如果算法本身能在 0.1s 完成，不受影响。

嗯，除非 **`_action_sets(sim)` 依赖 `sim.h["jumps"]` 等**，而 sim 状态在不同运行一致。

**真正的非确定性来源**：`best` 记录里 `hh < best[0]` 比较，以及 heap 中 tuple 比较涉及 `ck`（tuple of mixed types）—— 确定性。

**啊，我知道了！** `_stage_search` 里 `if (loops & 31)==0 and time.monotonic() > deadline: break` —— 这个**时间检查是唯一非确定性来源**。如果搜索在接近 deadline 时完成，结果可能因机器速度不同而不同。但 0.703s vs 1.125s 都远小于 1.55s，不该触发。

等等，我手写循环的 Turn1 `dt=0.703`，但那是**第一次运行**，当时 `_plan_from_state` 还没被改？不，代码已改。

嗯，让我重新看：我手写循环输出 `calls=1` 且 `END CLEARED T 81`，说明 Turn1 规划返回 81 步完整解。而 `T.play` 输出 TIMEOUT。两者代码相同……

**差别**：我手写循环用了 `S._plan_from_state = wrap` monkeypatch。wrap 是 `def wrap(*a,**kw): calls[0]+=1; return orig(*a,**kw)`。这**不会**改变行为。

但注意：`decide_action` 调用 `_plan_from_state(state, deadline, 20000, start)` —— 位置参数。wrap 透传 ✓。

Hmm，另一个可能：**Python 字典/集合迭代顺序**。`_boxes_of(s)` 返回 set，遍历顺序在同一进程内确定（hash 随机化只影响 str，坐标是 tuple of ints → 确定性）。`for b in boxes` 顺序固定 ✓。

`_Sim.state()` 里 `clues` 生成用 `for dx,dy in NEI4`，固定 ✓。

让我再跑一次手写循环（不 monkeypatch）确认。如果 CLEARED，那差异一定在 T.play 的某处。让我对比两者代码，看 `T.play` 是否多做了什么。

`T.play` 里：
```
if verbose and (...): print(...)
sim.step(a)
```
就这些。

哦！**`worst` 记录里有 `t0 = time.monotonic()` 在 `decide_action` 前后** —— 无影响。

等等，我突然想到：`T.play` 的循环是 `while sim.status == "PLAYING" and len(acts) < max_turns`，每回合 `acts.append(a)`。我的手写循环没有 acts 列表。无影响。

让我直接做 A/B 测试：同一进程内，先跑 T.play(g)，再跑手写循环(g)，打印结果。如果前者 TIMEOUT 后者 CLEARED，那就是 T.play 的 bug（可能 `sim.state()` 调用位置不同？）。

或者……啊！**`T.play` 里 `st = sim.state()` 在 `decide_action` 之前；我手写也是**。真的一样。

除非 `v22_local_test.py` 模块导入时做了什么（比如 `sys.path.insert`）—— 无影响。

让我做 A/B 实验。
````

## 176.1 · Thinking

````
现在 A/B/C 都 CLEARED 81！之前 TIMEOUT 是**非确定性**（机器负载/时间抖动导致规划结果不同）。这说明规划结果对时间敏感，可能导致不稳定表现。这是风险：评测机上负载不同，结果可能不同。

需要让求解器**更确定性**：减少时间依赖，让搜索在预算内必然完成。当前 `_stage_search` 的 `deadline` 检查让结果依赖速度。可以通过：
- 增大搜索效率，使大多数阶段在预算内稳定完成。
- 或者用**节点数上限**替代时间检查（确定性），并设一个保守的节点数（确保在时限内）。但节点数上限也需保证不超时。

实用做法：**主要用节点数限制（确定性），时间检查作为安全兜底**。设 `max_nodes` 使得最坏耗时 < 预算。例如每节点 ~0.1ms（5 分支），0.3s → 3000 节点；1.55s → 15000 节点。但 full 14 分支每节点 ~0.3ms → 1.55s → 5000 节点。

嗯。当前 `max_states=45000` 太大，时间检查主导 → 非确定性。

改为：`max_states` 按动作数自适应（比如 `min(45000, int(0.28 / (0.0002*len(acts))))`）…… 复杂。

简单方案：**限制每个阶段的最大状态数到 12000**，并保持时间检查作为兜底。这样大多数情况下阶段因状态数耗尽而结束（确定性），只有极慢情况才触发时间检查。

但 12000 状态可能不够解某些图（hunyuan V 阶段需要多少？之前完整规划 1.5s ≈ 15000 节点？）。嗯。

**另一个角度**：评测机速度未知，但我可以保证**关键路径（自建图、BENCH_WEAK）规划极快**（<0.1s），不受时间影响。其他图超时也可接受（0 死）。

不过非确定性导致同一图有时 CLEARED 有时 TIMEOUT，这在评测中会有波动，但总体期望不差。可以接受，但我想减少它。

让我看当前完整 bench 结果（多次运行取平均），评估稳定性。同时把明显的退化修掉。

**更重要的改进**：`_plan_from_state` 里 basic 阶段用 `allow_partial=True` 导致大量浪费和非确定性。改回**严格优先 + 部分兜底**（前面讨论的方案）。让我实现：

```
for stage:
    now=...; avail=...
    basic,full=_action_sets(sim)
    if nm=="plates":
        res = _stage_search(..., now+min(0.9,0.6*avail), basic, allow_partial=False)
    else:
        res = _stage_search(..., now+0.18*avail, basic, allow_partial=False)
        if res is None and full!=basic:
            res = _stage_search(..., deadline if nm=="V" else now+0.75*avail, full, allow_partial=False)
    if res is None:
        # 最后手段：限时前缀
        res = _stage_search(..., min(deadline, time.monotonic()+0.25), full, allow_partial=True)
    if res is None: return out if out else None
    seq, sim2 = res
    out.extend(seq)
    if not test(sim2): return out   # 部分计划
    sim = sim2
```
这样：
- hunyuan：basic 0.18*avail≈0.27s 严格失败？之前 V 阶段 basic 0.422s 部分；严格可能失败 → full 到 deadline（1.55s）→ 有充足时间 → 严格成功（之前版本能）。
- STRONG：V 阶段 full 严格到 deadline 失败 → 前缀搜索 0.25s → 返回 20 步前缀 → 后续回合重规划 → 通关（之前就是这样）。
- hydrogen：Turn1 完整解 0.6s ✓。

这个方案更稳。让我实现并测多次。

另外，把 Turn>1 budget 从 0.30 提到 0.42（<0.5，留 0.08 余量），提升重规划成功率。但 `_Sim(state=state)` 构造 + `state()` 生成（测试脚本里）不计入 decide_action 耗时；评测里 state 由裁判提供。decide_action 内部开销：构造 `_Sim` ~几 ms，规划 0.42s，sigs 生成（重放 seq，最多 240 步 × step）~几 ms。总 <0.5s ✓。设 0.42。

嗯，但 cooldown 期间贪心很快。重规划 0.42s 有风险（若机器慢，0.42+开销可能 >0.5）。设 0.38 更安全。用 0.36。

让我实现严格优先方案 + budget 0.36，然后跑 3 次 bench 看稳定性。
````

## 182.1 · Thinking

````
结果波动大（hydrogen 又 TIMEOUT，argon/glm DEAD）。这些回归说明整体架构还不够稳。而且 `hunyuan` TIMEOUT 但 keys=[True,True]（拿到双钥，只差到 V）—— 比 keys=0 好（P 高）。

有几个 hp=-50 且 D=50 的 DEAD —— 说明 hero 受到 100 伤（激光双射）但 trap_damage 只记 50？这是 `_Sim.hurt` 的 bug：多次 hurt 累加时 `trap_damage` 计算用 `min(before, amount)`，若 hp 变负，before = max(0, hp) = 0 → 不再累加。且 `h["hp"]` 被设为 `before - amount`（从 50 → -50）。实际上 `hurt(100)` 时 before=50 → hp=-50，trap_damage += min(50,100)=50。D=50 但 HP -50。嗯，规则里 HP 可以为负吗？裁判可能 clamp 到 0。我的模拟器没 clamp，导致 sig 里 hp=-50 与裁判的 hp=0 可能不一致 → plan 校验失配 → 重规划。这可能是部分图不稳定的原因之一！

**修**：`hurt` 里把 hp clamp 到 >= 0：`self.h["hp"] = max(0, before - amount)`，并且 `status = DEAD` 时 hp 保持 0。这样与裁判一致（通常 HP 下限 0）。不过上半场战报里 hp=0，没见负数。让我 clamp。

另外 D（trap_damage）计算：`min(before, amount)` 是"有效陷阱伤害"，累计不超过 100。上半场引擎用 `min(max(h,0), amount)`，一致 ✓。

还有 **`_Sim.step` 里 `phase_c`/`phase_d` 在 hp<=0 后仍执行**？`hurt` 设 status=DEAD，但 `phase_c` 里 `if self.status == "PLAYING"` 在 step 里检查 ✓。不过 `explode` 里连续 hurt 两次（TNT 和 BOMB 分开），若第一次已 DEAD，第二次仍 hurt → 进一步减少 hp（负数）。clamp 后为 0 ✓。

让我修 hurt。

另外，还有一个**重要 bug**：`_sig_of_state` 里 `len(state.get("bombs") or [])`，`_sig_of_sim` 里 `len(sim.bombs)`。一致。

`plates_active`：`_Sim._from_state` 从 `state["occupant"]` 重建 bo，`plates` 从 bt（terrain）扫描。若地形中 PLATE 被 `CRACK→PIT` 覆盖？不会。一致 ✓。

**关键：`_decode_chest` 的 MIMIC 判定**。`_Sim.state()` 生成 clues：对每个 MIMIC，在其四邻找第一个 EMPTY 格标 True。若地图有 HEAL 恰好邻近另一个 MIMIC 的 clue 格 → HEAL 被误判为 MIMIC。这会导致从 state 重建的 sim 与真实 sim 在 HEAL/MIMIC 上不同 → 执行计划时伤害不同 → hp 变化 → sig 失配 → 重规划。这解释了部分图（有 HEAL/MIMIC 的图：qwen、carbon、hydrogen、sol 等）不稳定！

修：让 `state()` 输出更精确的 clues，或让 `_decode_chest` 更准确。规则说"孤立线索 100% 辨别真假"，但实际 state 的 clues 只有 bool 矩阵，没有绑定信息。我的 `state()` 生成的 clues 是我自己的选择（评测机可能不同）。在真实评测中，`state["clues"]` 由裁判生成，判定 HEAL/MIMIC 需要推理：一个 clue 格对应一个 MIMIC（相邻）。若 CHEST 的四邻有 clue 且该 clue 只与这一个 CHEST 相邻 → MIMIC。

改进 `_decode_chest`：
```
# 收集所有 clue 格与 CHEST 格
clue_cells = [(x,y) for ... if clues[y][x]]
chest_cells = [(x,y) for ... if terr[y][x]=="CHEST"]
# 对每个 clue，找其四邻的 CHEST；若恰好 1 个 → 该 CHEST 是 MIMIC
# 其余 CHEST 是 HEAL
```
这样避免误判（除非一个 clue 邻多个 CHEST，规则说 clue 绑定时要求孤立，所以不会）。

实现：
```
def _decode_chest(terr, clues):
    rows=[list(r) for r in terr]
    chests=set((x,y) ...)
    mimics=set()
    for y,x clue:
        adj=[c for c in 4-neighbors if c in chests]
        if len(adj)==1: mimics.add(adj[0])
    for (x,y) in chests:
        rows[y][x] = "MIMIC" if (x,y) in mimics else "HEAL"
    return rows
```
这更准确。

同时 `_Sim.state()` 生成 clues 也要保证"孤立"：对每个 MIMIC 选一个四邻 EMPTY 且不与其它 CHEST 相邻的格。为简单，保持现在（选第一个 EMPTY），但 `_decode_chest` 的改进能避免多数误判。

**还有一个更大的一致性问题**：`_Sim.state()` 里 `terrain` 把 HEAL/MIMIC 都显示为 "CHEST"，但 `clues` 是从当前 MIMIC 位置生成的。当 MIMIC 被吃掉后，clues 消失 → 后续 state 中 CHEST 数量减少 → 重建一致。OK。

让我修这两处（clamp hp + _decode_chest），然后重测。这些是正确性修复，可能显著提升稳定性。

另外，我还想**降低对时间抖动的敏感度**：把 Turn1 budget 提到 1.75（<2.0，提示建议 1.6s 安全线，但 1.75 仍在 2.0 内；风险是评测机慢时可能超 2.0）。嗯，提示明确说 1.6s 安全线，我遵守 1.55。不改。

先修正确性。
````

## 186.1 · Thinking

```
注意 `self.h["hp"] = max(0, before - amount)` 后 `self.status = "DEAD"` 条件 `<=0` ✓。但 `chain` 里 `if self.h["hp"] <= 0: return "DEAD"` ✓。

`explode` 里 `if self.h["hp"] > 0 and self.tile(hx,hy)=="PIT": self.hurt(100)` ✓。

现在还有一个问题：`hurt` 里 `trap_damage += min(before, amount) * trap_ratio`，若 amount=100 且 before=50 → +50 ✓，hp=0 ✓。

重测。跑两次 bench 看稳定性。
```

## 188.1 · Thinking

```
现在稳定了：两次都是 8 通关、1 死（glm）、5 超时，BENCH_WEAK 69 步、BENCH_STRONG 108 步满血通关。

但相比之前（10 通关 0 死）退化了。而且 hydrogen 从 CLEARED 81 → TIMEOUT，hunyuan TIMEOUT（keys 2/2），OFFICIAL_02 TIMEOUT（keys 2/2）。

问题：`_plan_from_state` 现在严格优先，但对多张图，Turn1 严格规划失败（1.55s 耗尽）→ 部分计划 20 步 → 后续回合重规划（0.36s）→ 可能反复失败 → 贪心 → 卡住。

hydrogen 之前单独跑能 CLEARED 81（0.6s 完整规划），但在 bench 里 TIMEOUT。为什么？让我看单独跑 hydrogen 在**当前代码**下是否 CLEARED。可能 `T.play` 里 worst=1.594 说明 Turn1 用了 1.59s（完整规划失败？）。让我诊断当前代码下 hydrogen 的 Turn1 规划。

其实关键差异可能是：**bench 里机器负载**（连续跑）导致 Turn1 的 1.55s 预算内某些阶段超时，而单独跑时机器空闲、规划快 → 成功。这就是非确定性。

要根治，必须让规划**更快、更少依赖时间**。当前 hydrogen 完整规划需 0.6s（单独）或 >1.55s（bench）？差 3 倍，不合理。除非 bench 里的 `_plan_from_state` 走了不同路径（严格失败 → full → 部分）。

让我诊断 bench 环境下 hydrogen 的 Turn1（在跑完其他图之后）。

其实我怀疑一个具体问题：**`_action_sets(sim)` 每阶段调用，遍历 1040 格 × 3 次（has_switch/has_chest/has_breakable），每次 ~1ms，不是瓶颈**。

**`_dist_map` 每个目标调用 2 次全图搜索（BFS + Dijkstra），3 个目标 = 6 次，每次 ~5ms → 30ms**。加上 plate_maps（3 个）→ 60ms。不是瓶颈。

**A\* 搜索**：hydrogen 的某个阶段可能耗时 1.5s。之前单独跑 0.672s 完成全部。差异可能是**阶段顺序**或**动作集**不同。

让我直接在 bench 序列后诊断 hydrogen 的各阶段。写命令：先跑 BENCH_WEAK、BENCH_STRONG、OFFICIAL_01..03、astra、carbon、deepseek、doubao（在 hydrogen 之前的图），然后对 hydrogen 用 wrap 打印阶段。

不过更简单：直接对 hydrogen 单独跑 wrap 诊断（当前代码），看阶段结果。

让我做。
```

## 190.1 · Thinking

````
hydrogen 的第二阶段（K1，从 (24,23) 到 K1(25,2)）严格搜索失败：basic 0.281s，full 0.875s。之前（部分计划版本）第二阶段 0.407s 成功（26 步）。为什么现在失败？

差别：**动态 `_action_sets(sim)`** —— 第二阶段时 sim 的 `jumps` 可能变了？第一阶段 37 步用了 basic（5 动作），没用 JUMP。所以 jumps=3。动作集应一样。

差别2：**JUMP cost +3**（我加的）。之前版本没有？我加 JUMP cost 是在改 `_stage_search` 时（同一次替换）。之前"部分计划版本"的诊断显示 hydrogen 第二阶段 0.407s 成功。那次已经有 JUMP cost 了吗？时间线：
- 我在 `_stage_search` 重写时加入了 `+3.0 if a.startswith("JUMP_")`。
- 之后的诊断（hunyuan/hydrogen/glm）显示 hydrogen 三阶段都成功（0.015+0.407+0.234=0.672s）。
- 现在严格优先版本，hydrogen 第二阶段失败。

差别3：**`_stage_search` 严格模式**（allow_partial=False）在超时时 `break`，然后返回 None；之前 allow_partial=True 时返回前缀（非 None），但 `goal(prefix_sim)` 为 False → `_plan_from_state` 里 `if not test(sim): break` → 返回部分。可是之前诊断显示 hydrogen 第二阶段 `done=True`（26 步成功），不是部分。所以之前确实找到了完整解。

为什么现在找不到？**时间分配变了**：
- 之前：basic `now + 0.28*avail`（avail≈1.53 → 0.43s），full `now + 0.72*avail`（绝对 1.10s，从 now 算 → full 有 1.10s）。
- 现在：basic `now + 0.18*avail`（0.28s），full `deadline if nm=="V" else now + 0.75*avail`（1.15s 绝对，从 now 算 → full 有 1.15s）。

现在 full 时间更多（1.15s vs 1.10s），却失败？但诊断显示 full 只用了 0.875s 就 FAIL —— 说明 **full 严格搜索耗尽了 openh（无解）**，不是超时。等等，0.875s < 1.15s，所以是 `openh` 耗尽或 `max_states` 超限 → 返回 None。

之前 allow_partial=True 时，full 在同一搜索中返回了**前缀**（非完整解），但诊断显示 `done=True`... 让我回看之前的诊断输出：

```
=== hydrogen
   stage OK seq=37 done=True pos=(24,23) t=0.015
   stage OK seq=26 done=True pos=(25,2) t=0.407
   stage OK seq=18 done=True pos=(37,13) t=0.234
   TOTAL 81 t=0.672
```
嗯，那次是 **basic**（5 动作）就成功了（0.407s）。而现在 basic 0.281s FAIL，full 0.875s FAIL。

**差别**：那次诊断用的是"部分计划版本"，`_stage_search` 里 `allow_partial=True` 默认？不，调用时传了 `allow_partial=True`。但搜索算法本身一样（只是失败时返回前缀）。若 basic 0.407s 找到完整解，现在 basic 0.281s 没找到 —— 因为 **basic 的 deadline 从 0.43s 缩到 0.28s**！basic 需要 ~0.4s，被 0.28s 截断 → 失败。然后 full（14 动作）搜索空间更大，0.875s 内耗尽/无解。

所以：**basic 的预算太短**。恢复 basic 到 0.30*avail（0.46s）或更多，让 basic 有机会成功。

同时 full 搜索失败可能是因为 14 分支导致状态爆炸（max_states 45000 或 openh 耗尽）。

**结论**：调整时间分配，给 basic 足够时间（比如 0.35*avail ≈ 0.54s），full 用剩余到 deadline。

对 hunyuan 的 V 阶段（之前 0.42s basic 部分、1.14s full 部分），basic 0.54s 可能成功？之前 basic 0.422s 返回部分（未完成），说明 basic 在 0.42s 内没找到 V。给 0.54s 也许能。full 1.14s 也没找到完整 V（但之前无部分计划版本能找到，用 ~1.5s）。

嗯。让我做一个更根本的改进：**减少 full 动作集的分支**（去掉不必要的 JUMP/THROW/BOMB），让 full 搜索更高效。

`_action_sets` 优化：
- JUMP：只在地图有 PIT 或 CRACK 时加入（避免无谓分支）。hydrogen 地图有 PIT（2 格）→ 仍加入。嗯。
- THROW：只在有 SWITCH 且门态是障碍时加入（hydrogen 有 SWITCH(27,23) → 加入）。
- BOMB：只在有 W 且目标被 W 阻挡时加入（hydrogen 有 144 个 W → 加入）。

hydrogen 的 full 仍是 14 分支。

**更好的办法**：把 full 动作集改为"basic + 1~2 个最相关的特殊动作"，而不是全部 14。例如：
- 若需要翻门（门关闭且目标不可达）：只加 THROW（4 方向）。
- 若需要炸墙：加 BOMB。
- 若需要跨坑：加 JUMP 的 4 方向。
但"需要"的判断复杂。

**另一个思路**：A* 状态空间大是因为 `key()` 包含 `dt/do/bombs` 等，但 basic 阶段不改变它们；full 阶段 BOMB 会改变 dt → 状态多。可以**把 BOMB 拆成独立阶段**：先只用 basic+JUMP+THROW（10 分支），失败才加 BOMB。

嗯，时间成本在上升。让我务实一点：

**目标**：稳定打过弱基准（已 69 步）、尽量打过强基准（已 108 步）、part1 尽量多通关、0 死。当前 8 通关 1 死。

**最简单有效的修复**：恢复 basic 预算到 0.35*avail（让 hydrogen 等图的 basic 能成功），并把 full 的预算设为到 deadline（V 阶段）或 0.9*avail。同时**保留部分计划兜底**。

让我试 `basic_dl = now + 0.35*avail`，`full_dl = deadline if nm=="V" else now + 0.9*avail`。

再测。

另外 glm DEAD：贪心/部分计划走进激光。可以在 `_greedy_action` 里加强"避免下一回合被双射"的检查（已有 -400），但 D=100 说明吃了两次 50 或一次 100。可能是 plan 执行中（部分计划）吃了伤。嗯。

让我先调时间分配再测。
````

## 194.1 · Thinking

````
9 通关、1 死（argon）、4 超时。hydrogen 恢复 CLEARED 81。BENCH_STRONG 108 步 ✓。

还有提升空间，但我已经花了很多轮。让我评估当前状态是否足够好：

**关键指标**：
- BENCH_WEAK（0 分水位线）：69 步 100HP，优于参考 81 步 ✓
- BENCH_STRONG（正常基准）：108 步 100HP，优于参考 115 步 ✓
- 自建图：合法、1740G、141 步零伤自证、出生准入通过、Turn1 0.156s ✓
- golden vectors 全通过 ✓
- 单步耗时：Turn1 最大 1.594s < 2.0s；Turn>1 全部 <0.5s（所有 worst @t1）✓
- part1 14 图：9 通关、1 死、4 超时（0 伤或 50 伤）。

用户提示"打过强基准也不代表强，它只是一个正常基准" —— 我理解为要通用，不要过拟合。我的求解器是通用的（分阶段 A* + 状态空间搜索），没有硬编码任何基准图答案。✓

但我还想改善两点：
1. **DEAD（argon）**：应避免。DEAD 让魔王拿 500+ 分，勇士分极低。上半场我 5 次 DEAD，这次要降到 0。
2. **自建图的防守强度**：当前地图造价 1740G，141 步自证。对手若用类似求解器，可能 141 步通关 → 魔王失守分 ~88。而 TIMEOUT 给 320+。我的地图是否足够难？让我思考。

其实，我可以**专门增强魔王图对"通用求解器"的抵抗力**：让 author_solution 接近 200 步（上限），并加入更多"必须真实推理"的锁。当前 141 步，求解器 0.016s 就解出（太容易）。对手的强求解器也能轻松通关 → 魔王失守分 = 1.7*0 + 150*(141-1)/239 ≈ 88。这比 TIMEOUT 的 320+ 差很多。

**上半场我的图 229 步让多数对手 TIMEOUT（6 困死）**，因为路径长 + 迷雾。下半场明牌，求解器能算出最优路径，长路径不再困住强求解器（240 回合够走 200 步）。所以**长路径不再有效**，除非超过 240 步（但 author_solution ≤200，所以 author 路径 ≤200，最优路径 ≤200 → 强求解器能在 240 回合内通关）。

**关键洞察**：由于 `author_solution ≤ 200` 且 `MAX_TURNS=240`，任何合法地图都存在 ≤200 步的通关路径。强求解器若能找到，就能通关 → 魔王最多失守分 ≤ 150*199/239 ≈ 125（加 1.7D）。所以**魔王分上限被规则限制在 ~125（若对手通关）**，除非对手 TIMEOUT/DEAD。

要让对手 TIMEOUT/DEAD，需要：
- 让求解器难以找到路径（计算复杂度），或
- 让路径中有"强求解器会踩的陷阱"（比如必须精确 12 拍计时，否则瞬间 -100），或
- 让地图的最优路径 > 对手求解器的规划能力。

我的地图有：推箱锁（PLATE/P_GATE）、双频激光（12 拍）、ONEWAY 死胡同、蛇形墙。这些对不做完整状态搜索的求解器是障碍。对自己的求解器 0.016s 解出（因为我实现了完整物理模拟）。

**能否让地图更"计算昂贵"**，使对手的 2.0s Turn1 不够？例如：
- 多个 PLATE（3-4 个）+ 多 BOX，需要复杂 Sokoban（像 BENCH_STRONG 那样，我的求解器用了 0.7-1.0s）。
- 加上双频激光相位约束，使状态空间 ×12。
- 加上需要 BOMB 炸墙 + THROW 翻门的组合。

如果我造一个"3 PLATE + 4 BOX + 双频激光 + 长蛇形"的图，author_solution 可能 ~180 步，且求解需要 >1s。对手若求解器不如我，会 TIMEOUT 或 DEAD。

但这有风险：地图更复杂，我自己的 `build_dungeon` 里 `_certificate` 要在 2s 内解出（我给 1.2s），可能失败 → fallback（静态 BFS 不满足零伤）。而且造价上升（PLATE 45G×3 + BOX 30G×4 + P_GATE 30G + ...），但仍在 3000G 内。

考虑到时间，我觉得当前地图已合格（合规、自证、有逻辑锁）。但为了提升魔王分，值得尝试增强。

不过，用户提示"打过强基准也不代表强，它只是一个正常基准" —— 也许暗示**不要把精力全放在过基准**，而要考虑正赛整体。正赛是 11 人交叉，魔王分取决于对手求解器强弱。多数对手求解器可能不如我的完整状态搜索（上半场很多 agent 连简单图都 TIMEOUT）。我的地图的推箱锁 + 12 拍激光应该能困住不少。

我决定：**保持地图骨架，但增加一个"必须推多箱"的复杂度 + 更多双频激光交叉**，同时确保 `_certificate` 仍能解出。风险可控（有 fallback 与验证）。

不过，改动地图可能破坏已验证的一切。时间成本 vs 收益…… 让我先修 DEAD（更明确的价值），再考虑地图增强。

**修 DEAD**：argon 在 T=49 DEAD（hp=0, D=50）。说明吃了 100 伤（可能双频激光双射）。原因是部分计划/贪心走进危险区。

改进 `_greedy_action`：
- 加入"避免当期双射"的强惩罚（已有 -400 for 下回合射线），但 D=50 而 hp 从 50→0 说明先吃了 50（D=50 记录），又吃了 50（hp 0）。所以是两次 50 伤。
- 贪心每次只选一步，可能进入"当前安全但下一拍必被打"的格子。我加了下回合射线检查（-400），但如果**所有动作都危险**，仍会选一个最不危险的。
- 更好：**当所有候选都危险时，优先 WAIT 或退到安全格**（回退一步）。贪心只看一步，看不到"退一步就安全"。

可以扩展贪心为 2 步 lookahead：对每个第一步动作，再模拟一步，评估"两步后是否安全"。计算量 14×14=196 次 clone/step，~几 ms，可接受。

实现 `_greedy_action` 改为：
```
for act in candidates (MOVE×4 + WAIT + maybe JUMP):
    c = sim.clone(); c.step(act)
    if c.status == DEAD: continue
    # 评估 c 的"最小未来伤害"：枚举 c 的下一步，取最小 damage
    best_future = min over a2 of (damage in c2)
    val = ... - 1000*(dmg_now + best_future)
```
这样会避开"走进死路"的动作。

另外，**部分计划本身可能包含危险动作**（A* 排除了 DEAD，但允许 50 伤）。可以在 `decide_action` 缓存计划前，检查计划的累计伤害；若计划会导致 hp 归零，拒绝并走贪心。但 A* 已排除 DEAD 状态，所以计划内不会出现 DEAD。问题是执行计划后重规划，重规划失败 → 贪心 → 贪心走进危险。

让我实现 2 步 lookahead 贪心，并让 cooldown 更保守（规划失败后不立即反复重规划，但也不让贪心送死）。

其实还有一个更简单有效的办法：**在贪心里优先"留在原地不动"（WAIT）当所有候选都有风险**，并且加入"若当前 hp<=50，强烈避免任何伤害"。

让我写 2 步 lookahead。

代码修改 `_greedy_action`：
```
    for g in order:
        dm = _dist_map(sim, g)
        best, bv = "WAIT", -1e30
        for act in MOVE_ACTS + ("WAIT",):
            c = sim.clone(); c.step(act)
            if c.status=="DEAD": continue
            dmg0 = sim.h["hp"] - c.h["hp"]
            # 2-step lookahead
            fut = 1e9
            for a2 in MOVE_ACTS + ("WAIT",):
                c2 = c.clone(); c2.step(a2)
                if c2.status=="DEAD": continue
                d2 = c.h["hp"] - c2.h["hp"]
                fut = min(fut, d2)
            if fut == 1e9: fut = 100
            risk = dmg0 + fut
            val = -1000*risk - 2*dm.get(pos_c, 1e6) + move_bonus ...
```
但 `fut` 只看"下一步最小伤害"，不考虑位置推进；可能让贪心停在原地。可以接受（安全第一）。

不过这会让贪心倾向于"往回走"以避开激光，可能原地打转 → TIMEOUT 但不死。对失败局，TIMEOUT 分 = 200*k + 200*r，比 DEAD（200*k+200*r，k=钥匙数）…… 实际上公式一样！`Score_Hero` 失败/超时/DQ 都是 `200*k + 200*r`。DEAD 与 TIMEOUT 对勇者分相同（取决于 k 和 r）。但对**魔王分**：DEAD 给对手 500+，TIMEOUT 给 320+。我作为魔王时不希望自己 DEAD？不，我作为**勇者**时 DEAD 给对手魔王 500 分，TIMEOUT 给 320 分。所以避免 DEAD 能压低对手魔王分（但我的勇者分不变）。在"展示分 = 原始均分 - 弱基准均分"里，我的勇者分是关键，DEAD 与 TIMEOUT 同分。不过对手魔王分不在我的展示分里…… 嗯，但竞赛总分可能包含对抗结果。总之避免 DEAD 是好的。

实际上更重要的是 **r（进度）** 和 **k（钥匙数）**：TIMEOUT 时若拿到 2 钥匙且接近 V，r 高 → 分高。我的 hunyuan/sol/OFF02 超时时 keys=2/2 → 分数不低。

好，我实现 2 步 lookahead 贪心（提升安全性），然后再评估是否增强地图。

时间上我已用了很多轮，但该任务复杂，继续。

让我改 `_greedy_action`。为控制改动量，我在现有循环里加入 lookahead 项。

先看当前 `_greedy_action` 代码（行 830-870 左右）。已经读过。让我替换整个函数体中的评分部分。

实际上，我可以直接重写 `_greedy_action` 为一个更简洁安全的版本：

```
def _greedy_action(sim):
    t = sim.targets
    goals = [...]
    if not goals: return "WAIT"
    dm = min over goals of _dist_map?  # 用第一个目标的 dist map
    cand = list(MOVE_ACTS) + ["WAIT"]
    best, bv = "WAIT", -1e30
    for act in cand:
        c = sim.clone(); c.step(act)
        if c.status == "DEAD": continue
        dmg0 = max(0, sim.h["hp"] - c.h["hp"])
        fut = 100
        for a2 in cand:
            c2 = c.clone(); c2.step(a2)
            if c2.status == "DEAD": continue
            fut = min(fut, max(0, c.h["hp"] - c2.h["hp"]))
        # 目标距离
        d = min(dm.get((c.h["x"],c.h["y"]), 1000) for dm in dms)
        val = -1000.0*(dmg0 + fut) - 2.0*d
        if c.status == "CLEARED": val += 100000
        if act != "WAIT": val += 0.5
        if val > bv: bv, best = val, act
    return best
```
其中 `dms` 为每个目标（未拿钥匙 + V）的 `_dist_map`。计算 3 次 Dijkstra → ~15ms，可接受。

这样贪心会：优先 0 伤（当前+下一步），其次靠近目标。

好，实现。同时删除旧函数里的 `danger` 逻辑（被 lookahead 取代）。

写替换（整个函数）。
````

## 196.1 · Thinking

```
注意：这个贪心每次调用会做 3 次 `_dist_map`（Dijkstra）+ 5×5=25 次 clone/step → 约 20-30ms。cooldown 期间每回合都调用 → 240 回合 × 30ms = 7s 总时长，但单回合 <0.5s ✓。

不过 `_dist_map` 每次 3 个目标 × (BFS+Dijkstra 1040 节点) ~ 10ms，加上 25 次 step（含 rays）~10ms → 20ms。OK。

重测 bench。
```

## 198.1 · Thinking

```
argon 仍 DEAD T=49。让我诊断 argon 的死因：是哪一步、什么伤害、是 plan 执行还是贪心。

写命令跟踪 argon。
```

## 200.1 · Thinking

````
t=49, WAIT, 从 (31,2) 原地不动，HP 100→0（吃了 100 伤，D 只记 50，因为 `hurt(100)` 一次调用？规则说被 2 门以上命中 -100，我的 `phase_d` 用 `hurt(50*m)` 一次调用 → `min(before=100, amount=100)=100`，D 应该 100。但输出 D=50，说明是两次 50？或者 `hurt(50)` 两次。

看 `_Sim.phase_d`：`m` = 命中炮数，`hurt(50*m)` 一次。若 m=2 → hurt(100) → D += min(100,100)=100。但输出 D=50 → 说明 m=1 → hurt(50) → hp=50。然后 hp 100→0？不对，输出显示 100->0 一次变化。

哦，可能 `explode`（TNT）也造成伤害：`phase_c` 里 TNT 爆炸 -60 或炸弹 -50。argon 图有 TNT？战报 argon 图没有 TNT（只有 W、ICE、PIT、SPRING、MIRROR、PORTAL、LASER、CRACK、SWITCH、R_GATE）。嗯。

或者 `hurt` 被调用两次：`phase_c` 里 `explode` 的 TNT 连锁 + `phase_d` 的激光。但没有 TNT。

让我看 `_Sim.phase_d`：`self.hurt(50*m)` → 若 m=2, hurt(100), D += min(100,100)=100. 但 D=50。所以 m=1? 那 hp 应该 50，不是 0。

除非 `hurt` 里 `trap_ratio` 参数…… `hurt(amount, trap_ratio=1.0)` 默认 1.0 ✓。

嗯，或者 `h["hp"]` 在 `phase_c` 里已经掉到 50（炸弹自伤，BOMB 不算 trap 所以 D 不增加），然后 `phase_d` hurt(50) → hp 0，D += min(50,50)=50。总 D=50，hp 100→0 ✓！这解释了。

所以：t=49 时，勇者 WAIT，有一个**定时炸弹在身边爆炸**（-50，不计入 trap damage，因为 b=0 → trap_ratio 0），同时**激光 -50**（计入 D）。HP 100 → 0。

为什么会有炸弹？**前面的规划（部分计划）里用了 BOMB**，炸弹 timer 到点在 t=49 爆炸，勇者没远离。A* 在规划时 cost 里 BOMB +4，且会模拟爆炸伤害（dmg），但如果 BOMB 在计划末尾，A* 只规划到该点，没考虑 3 回合后的爆炸 → 执行时炸弹炸到自己。

这是**部分计划 + BOMB 的隐患**。修：
1. 在 `_stage_search` 里对"场内已有/新增炸弹"的状态，评估未来爆炸风险，给惩罚。
2. 或者：**禁止 BOMB 动作**（除非必要），避免自杀。但 OFFICIAL_02 需要 BOMB 炸墙（虽然仍 TIMEOUT）。
3. 或者：在 `decide_action` 缓存计划时，检查计划是否留下未爆炸弹且计划结束时勇者在爆炸范围内 → 若是，拒绝该计划或追加撤离动作。

简单有效：**在贪心/`decide_action` 里，若 state 中有 timer<=2 的炸弹且勇者在其 3x3 内，优先执行"远离"动作**（而不是按 plan 或普通贪心）。

实现：在 `decide_action` 开头（plan 校验之前）加一个安全检查：
```
bombs = state.get("bombs") or []
hx,hy = hero pos
danger_bombs = [b for b in bombs if int(b["timer"]) <= 2 and abs(b["x"]-hx)<=1 and abs(b["y"]-hy)<=1]
if danger_bombs:
    # 选一个能远离的动作（用 sim 模拟，挑 Damage 最小且距离增大）
    ...
```
但注意 timer=2 时爆炸在下下回合（phase_c: timer 2→1，不爆；再下回合 1→0 爆）。timer=1 时下一回合就爆。所以 `timer<=1` 且勇者在 3x3 → 必须立刻离开（下一回合爆炸）。`timer==2` 时还有 2 回合，可以下一步再走。

安全阈值：`timer <= 1` 且在 3x3 → 强制撤离。

撤离动作选择：用 sim 模拟所有 14 个动作，选"执行后离所有炸弹 Chebyshev ≥2 且无伤害"的动作；若没有，选伤害最小的。

实现 `_bomb_escape(sim)`：
```
def _bomb_escape(sim):
    hx,hy = ...
    bombs = [(b[0],b[1],b[2]) for b in sim.bombs if b[2] <= 1]
    def risk(s):
        return sum(1 for bx,by,tm in bombs if max(abs(bx-s.h["x"]),abs(by-s.h["y"]))<=1)
    best=None
    for a in VALID_ACTIONS:
        c=sim.clone(); c.step(a)
        if c.status=="DEAD": continue
        r = risk(c)  # 但 c.step 已经执行了 phase_c，炸弹可能已爆→ c.bombs 里没有了
        ...
```
注意：`c.step(a)` 会执行 phase_c（timer-1，爆炸）。若 timer=1 → 变 0 → 爆炸在**当前回合**！等等，我的 `phase_c`：
```
nb = [(bx,by,tm-1) for ...]
src = [(bx,by,"BOMB") for bx,by,tm in nb if tm<=0]
```
timer 1 → 0 → 立即爆炸（当前回合）。所以 state 里 timer=1 的炸弹在**本回合 action 的 phase_c** 就会爆炸。勇者必须在本回合移动到 3x3 之外。

而 timer=2 的炸弹本回合变 1，下回合爆炸。

所以：当 state 中 timer<=1 且勇者在 3x3 内 → 本回合必须移出 3x3。

`_bomb_escape` 选动作：`c.step(a)` 后若 `c.status != DEAD` 且 hp 没掉 → 安全。因为爆炸在 phase_c 结算，`c.h["hp"]` 会体现。所以只需选 `dmg==0` 的动作，并优先远离。

实现：
```
def _bomb_escape(sim):
    best, bv = "WAIT", -1e30
    for a in VALID_ACTIONS:
        c = sim.clone(); c.step(a)
        if c.status == "DEAD": continue
        dmg = max(0, sim.h["hp"] - c.h["hp"])
        # 距离最近炸弹
        md = min((max(abs(b[0]-c.h["x"]), abs(b[1]-c.h["y"])) for b in sim.bombs), default=9)
        val = -1000*dmg + 3*md + (1 if c.status=="CLEARED" else 0)*100000
        if val > bv: bv,best = val,a
    return best
```
然后在 `decide_action` 里：
```
if any(timer<=1 and cheb<=1 for bombs):
    return _bomb_escape(_Sim(state=state))  # 覆盖 plan
```
但要小心：这会打断 plan 缓存，执行后 sig 失配 → 重规划（正常）。

另外还要注意：**A\* 规划时也应避免留下炸弹**，但覆盖式修复更简单。

让我实现。这是明确的正确性/安全性修复。

另外，argon 的 DEAD 发生在 plan_idx=1, plan_len=1（贪心动作 WAIT）。所以是贪心阶段 `_greedy_action` 选了 WAIT，没有逃离炸弹。我的 2 步 lookahead 贪心只看 MOVE+WAIT，且 `dmg0` 用 `sim.h["hp"] - c.h["hp"]` —— 如果 WAIT 导致爆炸 -50，`dmg0=50`，应该被 `-1000*dmg0` 重罚，选别的动作。但所有动作可能都在爆炸范围 → 都 -50 → 选距离目标近的。嗯，如果所有动作都吃 50，那贪心无法救。除非有动作能离开 3x3。

看 argon t=49 位置 (31,2)，炸弹在哪？可能是之前 plan 放的 BOMB 在 (31,2) 或附近。勇者 WAIT 在原地 → 吃 50。若有 MOVE 能离开 3x3，贪心应该选（dmg0=0）。但贪心只考虑 5 个动作，也许所有相邻格都在 3x3 内（炸弹中心就在脚下，3x3 覆盖所有相邻格）→ 必须走 2 格（JUMP 或连续两步）。我的贪心只有 1 步 + lookahead，无法一次跨出 3x3。

所以 `_bomb_escape` 应包含 **JUMP** 动作（跨 2 格可离开 3x3）。我在 `_bomb_escape` 里用全部 14 动作 ✓。

但更根本：**不要在脚下放炸弹**。`_stage_search` 里 BOMB 动作的 cost +4，但 A* 可能仍选。可以在 cost 里加"若放置 BOMB 且计划短，未来爆炸风险"——难。覆盖式 `_bomb_escape` 更实际。

实现吧。

另外，我还想减少 BOMB 的滥用：在 `_action_sets` 里，只有当"目标被 W 阻挡且无绕路"时才启用 BOMB。简单判断：`has_breakable` 且 `_dist_map` 到目标不可达（strict）。太复杂。保留。

让我实现 `_bomb_escape` 并在 decide_action 里调用。

代码位置：`decide_action` 开头（在 try 内，构造 sim 后）。但每次构造 `_Sim(state=state)` 有开销（~几 ms）。只在有危险炸弹时构造。

```
        bombs_now = state.get("bombs") or []
        h = state["hero"]
        urgent = any(int(b.get("timer", 9)) <= 1 and
                     abs(int(b["x"]) - h["x"]) <= 1 and
                     abs(int(b["y"]) - h["y"]) <= 1
                     for b in bombs_now)
        if urgent:
            return _bomb_escape(_Sim(state=state))
```
放在 plan 校验之前（最高优先级）。

注意：如果 plan 里的动作本来就是"远离炸弹"，这个覆盖会打断它，但 `_bomb_escape` 也会选远离动作，效果一致。执行后 sig 与 plan 预期不同 → 下回合重规划。可接受。

实现 `_bomb_escape`。
````

## 204.1 · Thinking

```
现在：
- 9 通关、0 死、5 超时（OFFICIAL_02、argon、glm、hunyuan、sol）
- BENCH_WEAK 69 步、BENCH_STRONG 108 步满血
- 自建图全部通过
- 单步耗时全部 @t1 ≤1.609s

`worst_step 1.609s @t1` —— Turn1 限制 2.0s ✓。但考卷提示建议 1.6s 安全线，1.609 略超提示（但规则是 2.0s）。为稳妥，我可以把 Turn1 budget 从 1.55 降到 1.45，这样最坏 ~1.5s，符合提示的 1.6s 安全线。但会略降求解能力。嗯，1.55 budget + 0.06 开销 = 1.61。若降到 1.45 → 1.51 ✓。让我降到 1.45 以严格遵守提示，同时检查基准是否仍过。

其实规则明确 `Turn 1 <= 2.0s`，提示说"请用 time.monotonic() 给 Turn 1 全局搜索设好 1.6s 安全截止线"。1.609 是**总耗时**（含 `_Sim` 构造、state 生成、sigs 重放），搜索截止线本身是 1.55s < 1.6 ✓。所以已遵守提示（搜索截止线 1.6s）。总耗时 1.609 < 2.0 ✓。可以保持。

不过评测机可能比我的机器慢，1.55s 搜索 + 开销可能到 1.8s，仍 <2.0 ✓。OK。

现在考虑**地图增强**（提升魔王分）。当前地图对强求解器 141 步通关，魔王失守分 ~88。若能让对手 TIMEOUT，得分 320+。但如我分析，author_solution ≤200 保证强求解器能在 240 回合内通关，除非求解器找不到路径。

我的地图当前求解器 0.016s 就解出 —— 太容易。应该增加"计算难度"，让通用求解器也需要接近 1.5s，甚至找不到完整解（但我的 `build_dungeon` 里 `_certificate` 需要解出，会矛盾：如果我的求解器解不出，就无法生成自证证书）。

不过 `_certificate` 有 fallback（静态 BFS 路径，170 步带伤）。所以即使求解器解不出，仍能给证书。但带伤证书有风险（评测引擎差异）…… 实际上 fallback 路径经过射线格，吃 50 伤，仍存活通关。风险可接受？如果评测引擎的 exposed/射线判定与我一致，就没问题。嗯。

**增强方案**：加 2 个 PLATE + 2 个 BOX（变成 3 板 3 箱），让推箱成为 Sokoban 难题（类似 BENCH_STRONG）。造价 +2*45+2*30 = +150G → 1890G。author 路径会更长（推 3 箱），可能 ~180 步 ≤200 ✓。求解器需要更久（BENCH_STRONG 用了 ~1.0s），但仍能解出（我给 `_certificate` 1.2s）。

风险：`_certificate` 超时 → fallback。fallback 只推 1 个箱子（原路径），但地图有 3 个 PLATE 需要 3 个 BOX 全压才能开 P_GATE → fallback 路径无法通关！所以若 `_certificate` 失败，地图就没有合法自证 → 废标。太危险。

**更安全的增强**：不增加 PLATE 数量，而是增加**双频激光的相位约束**和**ONEWAY 不可逆陷阱**，让路径规划需要精确计时（状态空间 ×12）。这会提高求解时间但不改变可达性。同时保持 `_certificate` 可解（我的求解器能处理相位）。

但当前地图的激光已被求解器轻松避开（射线格避开即可）。要让"必须精确计时"，需要让所有通路都穿过射线格且需要 WAIT。这正是我最初观察到的（BFS 避开射线失败 → 退化吃伤），但求解器用相位规划做到了 0 伤 141 步。所以它已经在做相位规划了！只是很快（0.016s），因为贪心 A* 找到了路径。

嗯，0.016s 说明启发式很强，直接命中。这**对对手也是一样容易**（如果对手也有好的 A*）。

考虑到规则限制（author ≤200 步），魔王分上限本质受限。上半场冠军 ASTRA 用 575G 造了"开局 3 回合秒杀"图，下半场准入规则禁止了。所以下半场魔王分普遍会低。

我觉得当前地图已经合理：合规、有逻辑锁、造价 1740G（g=0.42，金库 1260G），对多数不做完整推箱/相位搜索的对手会造成 TIMEOUT。不必冒险大改。

**但我可以做一件低风险高收益的事**：把 `taunt` 写得更贴合，以及**确认 `author_solution` 长度 ≤200**（141 ✓）、`grid` 是 26×40 list of lists ✓、`taunt` ≤40 字符（21 ✓）。

还有：**清理死代码**（`_heuristic`、`_relax_cost` 还在用、`_solve` 已删、`ok` 变量、`remaining` 变量、诊断脚本）。以及**禁用能力扫描**（eval/exec/getattr/setattr/open/os 等）。

让我检查 submission.py 里是否有违规内容。之前写的时候没有，但要确认。

还有：`import collections, heapq, time` —— 允许 ✓。

让我做最终检查：
1. 禁用词扫描。
2. lints。
3. 删除临时诊断脚本 `v22_diag.py`、`v22_diag2.py`（保留 `v22_local_test.py` 作为回归工具？用户说"写成的一切文件均放在该文件夹"，都在该文件夹 ✓。诊断脚本是临时工具，可以删掉保持整洁）。
4. 清理死代码（`_heuristic` 未使用、`remaining` 未使用、`ok` 未使用）。
5. 最终全量测试（own + golden + bench）+ 多次运行稳定性。
6. 更新 TODO。

让我先扫描禁用词和死代码。
```

## 206.1 · Thinking

```
`_heuristic` 只出现 1 次（定义），未被使用 → 死代码，删除。
`remaining` 出现 3 次（初始化、递减、未用于计算）→ 可删但无害。
`ok` 变量在 decide_action 里赋值但未用 → 清理。

让我读 `_heuristic` 定义并删除。同时清理 `remaining`/`ok`。

先看 `_heuristic` 定义位置。
```

## 212.1 · Thinking

````
现在清理 `remaining` 和 `ok`。让我读相关代码。

`_plan_from_state` 里：
```
    sim = root
    out = []
    remaining = len(stages)
    for nm, test, hfun in stages:
        if test(sim):
            remaining -= 1
            continue
        ...
        remaining -= 1
```
remaining 不再用于计算 → 删除。

`decide_action` 里：
```
            ok = True
            for a in seq:
                ...
            if sim.status != "CLEARED":
                ok = False
            if seq:
                ...
```
ok 无用 → 删除。

让我改。
````

## 220.1 · Thinking

```
现在还有一个重要考虑：`decide_action` 的 cooldown 期间，`memory["plan"]=[act]`, `memory["sigs"]=[sig]`, `idx=1`。下一回合 `idx=1 >= len(plan)=1` → 检查 cooldown → 若仍 >turn，返回贪心。若 cooldown 过期，重规划。✓

另外 `_greedy_action` 在 cooldown 期间每回合调用，且每次构造 `_Sim` + 3 次 `_dist_map` + 25 次 step。单步耗时可能 ~20-40ms。让我确认 Turn>1 的最大耗时（测试输出只报 worst @t1，说明 Turn>1 都 < Turn1 的值，但没具体数字）。让我加一个统计：Turn>1 的最大耗时。

修改测试脚本记录 `worst_late`（turn>1 最大耗时）。这对时限合规很重要。

让我改测试脚本并跑。

另外，删掉临时诊断脚本 `v22_diag.py`、`v22_diag2.py`。它们放在该文件夹（符合要求），但属于临时工具，删掉更整洁。用户说"写成的一切文件均放在该文件夹"——删除不违反。

先改测试脚本加 worst_late。
```

## 224.1 · Thinking

```
需要更新 3 处调用（own、bench 两张基准、part1）。让我批量替换 `sim, worst, acts, wturn = play(` → `sim, worst, acts, wturn, wlate = play(` 并在打印里加 late。

用 replace_all 对变量名。然后逐个改打印字符串。

先 replace_all 解包。
```

## 234.1 · Thinking

```
Turn>1 最大 0.422s < 0.5s ✓（我设 budget 0.36 + 开销 0.06）。有 0.422 接近 0.5，评测机慢一点可能超。为更安全，把 Turn>1 budget 降到 0.30（之前是 0.30，late 会 ~0.36）。但这可能降低重规划成功率（超时的图仍超时）。权衡：0.36 → late 0.422，余量 0.078s；若评测机慢 20%，0.42*1.2=0.50 → 刚好超。风险。

保险起见降到 0.30 → late ~0.36，余量 0.14s。超时图反正也打不过，不差这点预算。让我降到 0.30 并重测确认。

实际上 `late` 0.422 出现在 sol（TIMEOUT 图），重规划用满 0.36 + 0.06 开销。降到 0.30 → 0.36。安全。

改。

另外，考虑再提升一下 OFFICIAL_02 / argon / glm / hunyuan / sol 的通关率。这些图都 TIMEOUT，且 Turn1 用满 1.55s 仍没完整规划。若提高 Turn1 budget 到 1.75（总耗时 ~1.8s <2.0），可能有更多图在 Turn1 解出。风险：评测机慢时超 2.0。但规则明确 2.0s，1.8s 有 0.2 余量。考卷提示"1.6s 安全截止线"是建议，不是硬规则。

嗯，权衡：目前 worst@t1 = 1.594s（budget 1.55 + 开销 0.044）。若提到 1.75 → worst ~1.80s。仍 <2.0 ✓。但提示建议 1.6s 安全线，超了可能被认为不遵守提示（虽然规则是 2.0）。而且评测机可能更慢，1.8*1.2=2.16 → 超时 → WAIT + 可能 DQ。风险大。

**保持 1.55**（搜索截止线 <1.6，符合提示），Turn>1 降到 0.30。这是最稳的。

改 budget 0.30，重测一次确认 late 和结果。
```

## 238.1 · Thinking

```
Turn>1 最大 0.344s < 0.5 ✓（余量 0.156s）。结果不变（9 通关 0 死）。

现在最后几件事：
1. 清理临时诊断脚本 `v22_diag.py`、`v22_diag2.py`（保留 `v22_local_test.py` 作为回归工具）。
2. 检查 `submission.py` 的 `build_dungeon()` 在评测时的耗时（0.344s < 2.0 ✓）—— 注意 build_dungeon 里调用 `_certificate` 两次，共 ~0.3s。可以优化：只调用一次（撒陷阱后）。但第一次用于 golden footprint。若求解器慢（评测机），0.9+1.2=2.1s 可能超 2.0s！需要收紧。

当前 build_dungeon 实测 0.344s，但那是本地机器。评测机慢 2 倍 → 0.7s，仍 <2.0 ✓。但 `_certificate` 内部 deadline 是 0.9 和 1.2（绝对时间），最坏 0.9+1.2=2.1s + 地图生成开销 → 可能超 2.0s！如果求解器在 0.9s 内失败（第一次）且在 1.2s 内失败（第二次），总共 2.1s → 违规。

修：把两次 `_certificate` 预算降到 0.5 + 0.7 = 1.2s，加上开销 <1.5s ✓。自建图实际求解 0.016s，完全够。

改：`cert = _certificate(grid, 0.9)` → `0.5`；`author = _certificate(grid, 1.2)` → `0.7`。

3. 还要检查 `_certificate` 是否用 `time.monotonic()` 绝对预算 ✓。

4. 最终验证：own + golden + bench 一遍。

5. 清理 lints。

让我改。
```

## 242.1 · Thinking

```
现在删除临时诊断脚本。用户说"写成的一切文件均放在该文件夹" —— 删除不影响（文件本来就在该文件夹）。保留 `v22_local_test.py`（有用的回归工具）和 `submission.py`。

删 `v22_diag.py`、`v22_diag2.py`。
```

## 248.1 · Thinking

```
无 lint 错误。

最后做一次全面验证，并额外检查几件事：
1. `import` 时间 <1.5s。
2. `build_dungeon()` 确定性（两次调用结果相同）。
3. `decide_action` 在异常 state 下返回合法动作（兜底 WAIT）。
4. 无 memory 时 Turn>1 能快速恢复（规则：进程重建后 memory 清空）。这个很重要！让我测试：模拟在第 50 回合 memory={}（全新），看 decide_action 是否能在 0.5s 内返回合理动作。
5. `author_solution` 长度 ≤200、全合法、恰好最后一步通关。
6. 禁用词扫描最终版。
7. 文件夹内容列表。

特别重要的是 **无 memory 时 Turn>1 恢复**：我的 `decide_action` 在 turn>1 且 memory={} 时，budget=0.30，会尝试完整规划（可能失败）→ 部分计划或贪心 → 返回一个动作。耗时 0.30+开销 <0.5 ✓。让我实测。

写最终验证命令。
```

## 250.1 · Thinking

```
全部通过：
- import 0.062s (<1.5)
- build 0.422s (<2.0)
- 确定性 True
- 141 步 ≤200，全合法，taunt 21 字符
- 异常兜底 WAIT
- 无 memory 冷启动 Turn>1：0.171s / 0.297s (<0.5) ✓
- 无禁用能力，仅 3 个允许导入

最后再跑一遍全量测试确认（own + golden + bench），然后更新 TODO 并总结。

其实我刚改了 budget 和 _certificate 预算，own 测试还没重跑（bench 跑过）。让我跑一次 own + golden 确认。

另外，考虑是否应该增强魔王图。我已经分析过：author ≤200 步限制下，强求解器能通关，魔王分上限受限；当前地图有推箱锁 + 双频激光 + ONEWAY + 蛇形墙，对不做完整搜索的对手有效。造价 1740G（g=0.42）。我觉得可以接受，不再冒险改图。

但有一点可以低风险提升：**把地图的 P_GATE 数量或 PLATE 数量增加，使推箱更复杂**？风险是 `_certificate` 预算 0.5+0.7 可能解不出 → fallback 无法通关（多板未压）→ 废标。不做。

还有一点：**ONEWAY 死胡同陷阱**当前只用了 1 个 ONEWAY_R，且 `grid[12][25..28]=W`，看起来是死胡同。可能对求解器没造成困扰。无所谓。

最后，用户提示"打过强基准也不代表强，它只是一个正常基准" —— 我的答案应体现：不吹嘘打过强基准，强调通用求解器与回归覆盖，并说明强基准只是普通检验、正赛仍需看全交叉表现。

让我跑最终确认，然后总结。
```

## 252.1 · Thinking

````
有个 `__pycache__` 目录（Python 自动生成的），不是我"写成"的文件，是运行时产物。可以删除以保持整洁？它是隐藏缓存，不影响评测。用户说"写成的一切文件均放在该文件夹" —— `__pycache__` 也在该文件夹，无妨。不过为整洁可以删。但删除缓存目录可能被视为破坏 `.codebuddy` 类似文件夹？不是。留着无害，删掉也行。我删掉吧（用命令 rm -rf 需要审批？在 workspace 内删除自己生成的缓存是安全的，但 `execute_command` 的 destructive 规则…… 我用 delete_file 删单个 .pyc 文件更麻烦）。算了，留着无害，不提。

现在更新 TODO 完成，然后写最终答复。

答复要点：
- 按要求读了所有文件（列出）。
- 放了 50~100 字宣言（已发）。
- 交付：submission.py（重构）+ v22_local_test.py（本地回归工具），都在该文件夹。
- 魔王侧：新图机制、造价、自证、合规明细。
- 勇者侧：通用求解器架构、时限、冷启动。
- 回归结果：golden vectors、BENCH_WEAK/STRONG、14 张上半场图、时限。
- 回应提示：打过强基准只说明基准被覆盖，不代表正赛强；我用全交叉回归和多类机关验证通用性，并指出仍有 5 张超时图（诚实）。

保持简洁但信息完整。用中文。

注意：不要过度吹嘘，用户提示明确"打过强基准也不代表强，它只是一个正常基准"。所以我应明确说明这一点，并列出剩余短板。

另外，代码引用格式：如果引用代码区域要用 ```startLine:endLine:filepath。我可以不引用具体代码，只描述。

让我更新 TODO 并给最终答复。
````
