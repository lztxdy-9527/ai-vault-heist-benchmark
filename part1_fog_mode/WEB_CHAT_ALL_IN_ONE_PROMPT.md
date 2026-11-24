# 🏆 网页端一贴即用版：全球顶尖大模型 60 分钟算法对抗赛《阴间地牢·金库攻防战》

*(主办方说明：若某模型在纯网页对话框中参赛，可直接将本文件从下方分割线起复制发送给它。不含任何解题或造工具提示，纯冷面考官发卷。)*

---

## 一、 考场通告与参赛阵容

欢迎来到《阴间地牢：金库攻防战》60 分钟封闭式算法对抗赛。
本场比赛共有 **11 位全球顶尖大模型** 同场竞技：
* `ASTRA`、`SOL`、`ARGON`、`CARBON`、`HYDROGEN`、`Claude Opus 5.5`
* `DeepSeek`、`Qwen`、`GLM`、`混元 HY4`、`豆包 (Doubao)`

所有参赛选手接收完全相同的考题，在相同的规则下同时扮演**【地下城魔王（关卡建造者）】**与**【闯关勇者（破阵闯关者）】**，进行交叉对抗评测。

## 二、 考场铁律与判罚

1. **🚫 严禁联网与外部检索**：**严禁调用任何联网搜索工具（Web Search / Browser / Fetch）、严禁查询外部代码库**，只能依靠你自身的能力独立完成。
2. **⏱️ 严格限时 60 分钟，提前交卷无任何奖励**：考试总时长为 **60 分钟**。提前交卷没有任何加分或额外奖励。倒计时 60:00 结束瞬间，以最后一次完整输出的 `submission.py` 为准。
3. **💀 零容忍废标红线**：
   * 导入或造图报错、超时按 `RULES.md` 相应条款判罚；勇者接口错误按连续三次错误规则结算；调用禁止的文件/系统/网络/进程/双下划线反射能力直接判 **0 分**。
   * 魔王建图违章（预算 $>3000\text{G}$、地标越界、组件超上限、伪装宝箱怪缺少合法专属线索位） $\rightarrow$ 魔王榜直接判 **0 分**。
   * 作者自证失败（提交的 `author_solution` 在裁判物理引擎回放中未能存活通关，或未恰好在最后一个动作首次达成通关） $\rightarrow$ 魔王榜直接判 **0 分**。

## 三、 答题步骤

1. **第一步（赛前狠话环节）**：请先阅读下方规则，并在回复开头先输出一段你的**【赛前垃圾话 / 参赛宣言】（50~100 字，向同场的其他 10 位大模型放狠话）**。
2. **第二步（正式作答）**：完成完整 **`submission.py`** 的编写（必须完整实现 `build_dungeon()` 与 `decide_action(state, memory)` 两个顶层函数）。**注：第一场正赛勇者对局 100% 仅运行在 `BLIND` 迷雾盲视模式下**（`FULL` 全图明牌破阵将作为独立第二场另行发卷），请让 `decide_action` 专注于局部圆形 LOS 迷雾探索与防暗算避险！

---

## 四、 官方完整技术规则与物理引擎规范 (`RULES.md`)

### 1. 运行环境与限制
* **开放算法库权限（禁作弊黑名单）**：可自由使用 Python 计算与数据结构标准库（`math`, `heapq`, `collections`, `queue`, `array`, `statistics`, `decimal`, `fractions`, `graphlib`, `itertools`, `copy`, `random`, `typing`, `dataclasses`, `enum`, `bisect`, `functools`, `time`, `json`, `re`, `operator` 等）与预装科学计算/图论库（`numpy`, `networkx`, `sympy`, `mpmath`），并允许正常类私有属性/方法（如 `self._visited`、`self._bfs()`）。**严禁**文件 I/O（含 `open`、`np.load`/`fromfile`/`tofile`/`loadtxt`/`memmap`/`save*`、`nx.read_*`/`write_*`）、网络、`os/sys/subprocess/ctypes/inspect/types/pickle` 及双下划线反射（如 `__class__`、`__globals__`）。
* **隔离与计时**：每个 `(勇者, 地图, 模式)` 在独立干净子进程运行（初始 `memory = {}`）。`import submission` 限时 `1.5s`；`build_dungeon()` 限时 `2.0s`；`decide_action(state, memory)` 单步限时 `0.5s`（超时/异常/非法返回值计 1 次接口错误并按 `"WAIT"` 处理，连续 3 次接口错误直接判负；合法枚举返回即清零错误计数；技能库存为 0 时调用对应技能按 `"WAIT"` 处理且不计接口错误）。

### 2. 画布空间与地标硬性约束（违反任意一条则魔王 0 分废标）
* **网格尺寸**：`40` 列（$x \in [0, 39]$）$\times$ `26` 行（$y \in [0, 25]$），按 `grid[y][x]` 索引。
* **免费外框**：最外圈 128 格（$x \in \{0, 39\}$ 或 $y \in \{0, 25\}$）必须全部填 `"T_W"`，**造价 `0G`，不占 `"T_W"` 的 120 格配额**。
* **出生净空区**：勇者出生在 `S = (2, 13)`。以 `(2, 13)` 为中心的 $3\times 3$ 区域（$x \in [1, 3], y \in [12, 14]$）在提交的 `grid` 中**必须全部填 `"EMPTY"`**（且不得被分配为 `MIMIC` 专属线索格）。
* **三座必放地标（均 `0G`，全图各恰 1 个，坐标互异）**：
  * `"K1"`：$x \in [12, 34], y \in [2, 10]$；
  * `"K2"`：$x \in [12, 34], y \in [15, 23]$，且 $|x_{K1}-x_{K2}| + |y_{K1}-y_{K2}| \ge 12$；
  * `"V"`（终极金库）：$x \in [33, 37], y \in [4, 21]$。
* **通关条件**：先拾取 `"K1"` 和 `"K2"`（顺序不限），随后在 $\text{HP} > 0$ 状态下踏上 `"V"`。

### 3. 组件造价、数量上限与四层真值解码（总预算上限 `3000G`）
* **墙体**：`"W"` 普通砖墙 (`5G`, 无上限, 可炸毁)；`"T_W"` 钛金承重墙 (`25G`, 内圈上限 120 格, 不可摧毁)。
* **动量与深渊**：
  * `"ICE"` 溜冰滑道 (`10G`, 无上限)；
  * `"MIRROR_NE"`, `"MIRROR_SE"`, `"MIRROR_SW"`, `"MIRROR_NW"` 90°折跃斜坡 (`25G`, 四种合计上限 30 个)。折转表：
    * `MIRROR_NE (↗)`: `L/R -> U`, `U/D -> R`
    * `MIRROR_SE (↘)`: `L/R -> D`, `U/D -> R`
    * `MIRROR_SW (↙)`: `L/R -> D`, `U/D -> L`
    * `MIRROR_NW (↖)`: `L/R -> U`, `U/D -> L`
  * `"SPRING_U"`, `"SPRING_D"`, `"SPRING_L"`, `"SPRING_R"` 强力弹簧板 (`35G`, 四种合计上限 20 个)；
  * `"PIT"` 致命深渊坑 (`40G`, 无上限, 勇者落入 `-100 HP`, `BOX` 落入同归于尽填平为 `"EMPTY"`)。
* **时序与逻辑**：
  * `"LASER_U"`, `"LASER_D"`, `"LASER_L"`, `"LASER_R"` 周期激光炮 (`75G`, 四种合计上限 12 门, 炮座本身为可被炸毁的高墙, `turn % 3 == 0` 时射出最长 10 格射线, 伤 `-50 HP`, 可引爆 `TNT`)；
  * `"CRACK"` 脆冰断桥 (`20G`, 上限 40 格, 踏上即停, 离开瞬间变为 `"PIT"`)；
  * `"SWITCH"` 红蓝开关 (`30G`, 上限 6 个)；`"R_GATE"`, `"B_GATE"` 红蓝门 (`20G`, 合计上限 16 扇；初始 `gates_flipped=False` 时 `R_GATE` 关闭为高墙、`B_GATE` 开启为平地)。
* **爆破、交互与拓扑**：
  * `"TNT"` 连锁火药桶 (`40G`, 上限 12 个, 占用层阻挡物, $3\times 3$ 爆炸伤 `-60 HP` 并炸墙)；
  * `"BOX"` 重型合金箱 (`30G`, 上限 4 个, 占用层可推实体)；
  * `"HEAL"` 真补给箱 (`30G`, 上限 4 个, 恢复 `+30 HP`)；
  * `"MIMIC"` 伪装宝箱怪 (`60G`, 上限 4 个, 扣 `-45 HP` 并终止本回合动量)；
  * `"PORTAL_1A/1B"`, `"PORTAL_2A/2B"` 双子传送门 (`80G/对`, 最多 2 对, 必须成对出现)。
* **四层解码与 `MIMIC` 专属线索绑定**：
  * 裁判将提交的 `grid` 拆分为 `terrain`（其中 `"BOX"`/`"TNT"` 脚下设为 `"EMPTY"`）、`occupant`（`None|"BOX"|"TNT"`）、`bombs`（`[]`）、`clues`（`26x40 bool`）。
  * 对每个 `"MIMIC"` 按行优先遍历，按 **`U(0,-1), D(0,1), L(-1,0), R(1,0)`** 顺序寻找第 1 个满足：`terrain=="EMPTY"` 且 `occupant is None`、不在出生净空区、且**正交四邻中无任何其他宝箱（`HEAL`或`MIMIC`）**且未被占用的格子，置 `clues[ny][nx] = True`（找不到则地图判违章 0 分；当该 `MIMIC` 被触发或销毁时同步清除其 `clue`）。

### 4. 单次成功位移 8 步原子序 & 单回合 4 阶段管线
* **高墙集合 `HIGH_WALL`**：`"W"`, `"T_W"`, `"LASER_*"`, 以及当前处于关闭状态的门（关闭时若门格上已有实体，该实体可离开，其他实体禁入）。
* **单次成功位移 8 步原子序（从 `p0` 进入 `p1`）**：
  1. `steps_taken += 1`；
  2. **原格离开**：若 `terrain[p0] == "CRACK"`，立即变为 `"PIT"`；
  3. **坐标更新**：更新实体位置为 `p1`（若为勇者则将 `p1` 加入本回合 `exposed_cells`）；
  4. **落点即时交互**：
     * `BOX` 落点：`"PIT"` $\to$ 箱子销毁且坑填平为 `"EMPTY"`（箱链终止）；`"MIMIC"` $\to$ 碾碎为 `"EMPTY"`（清线索）；`"SWITCH"` $\to$ 翻转 `gates_flipped`。
     * `hero` 落点：`"PIT"` $\to$ `hp -= 100`；`"MIMIC"` $\to$ `hp -= 45`, 变 `"EMPTY"`（清线索）, `stop_momentum = True`；`"HEAL"` $\to$ `hp = min(100, hp + 30)`, 变 `"EMPTY"`；`"SWITCH"` $\to$ 翻转 `gates_flipped`。
  5. **判死**：若 `hero.hp <= 0`，立即终止整局判死；
  6. **拾取与判胜**：若勇者踏上 `"K1"`/`"K2"` 则拾取并变 `"EMPTY"`；若踏上 `"V"` 且双钥已齐且 `hp > 0`，**立即终止整局判存活通关（不执行阶段 C/D）**！
  7. **熔断检查**：若 `steps_taken >= 32` 或 `stop_momentum == True`，终止动量停在 `p1`；
  8. **动量延续**：
     * `"ICE"`：沿当前 `dir` 请求进入下一格（遇 `HIGH_WALL`/`BOX`/`TNT`，或箱子遇勇者/`K1`/`K2`/`V` 则受阻停在 `p1`）；
     * `"MIRROR_*"`：按折转表改 `dir` 后请求进入下一格（受阻停在斜坡上）；
     * `"SPRING_*"`：改 `dir` 为弹簧方向，探测 $k=1,2,3$：若第 $k$ 格受阻（若弹射实体为 `BOX` 且阻挡物为 `TNT` 则标记该 `TNT` 待爆），$k=1$ 留在原弹簧格停稳，$k\in\{2,3\}$ 腾空飞越中间格提前落在 $k-1$ 格执行 8 步原子序；若 3 格均无阻挡则飞越第 1,2 格直接落在第 3 格执行 8 步原子序；
     * `"PORTAL_*"`（非刚从配对端传出）：若配对端 `p_pair` 无占用阻挡，传至 `p_pair`（计 1 次位移，`portal_count += 1`，抑制 `p_pair` 回吸）；若 `portal_count >= 2` 则在 `p_pair` 直接停稳，否则沿 `dir` 向门外请求迈出 1 格。
* **单回合 4 阶段（Turn = 1..240）**：
  * **阶段 A & B**：
    * `"WAIT"`：不动；
    * `"BOMB"`：若 `bombs > 0` 且脚下无炸弹，`bombs -= 1`，放置 `timer = 3` 炸弹；
    * `"MOVE_*"`：若前方 `p1` 为 `"BOX"` 且箱后 `p2` 可入，**先让箱子独立跑完完整动量链（勇者原格阻挡箱子）**，结束后若 `p1` 仍可入则勇者迈入 `p1` 跑完动量链；
    * `"JUMP_*"`：扣 1 次 `jumps`；若第 1 格为 `HIGH_WALL` 或第 2 格为 `HIGH_WALL`/`BOX`/`TNT` 则失败留原地；否则跃过第 1 格落在第 2 格执行 8 步原子序；
    * `"THROW_*"`：扣 1 次 `throws`；飞石空中沿直线飞最多 6 格（遇 `HIGH_WALL`/`BOX` 碎裂；遇 `SWITCH` 翻门碎裂；遇 `TNT` 标记待爆碎裂；遇 `MIMIC` 清除并碎裂；遇 `MIRROR_*` 折转继续飞；遇 `PORTAL_*` 不耗射程传送继续飞，受 2 次传送上限约束；飞越 `PIT`/`ICE`/`SPRING` 等）。飞满 6 格未碎裂且第 6 格为 `ICE`/`MIRROR_*` 时转入地面滑行（最多 32 步）。
  * **阶段 C（炸弹与 TNT 链式爆炸）**：全场 `bombs` 的 `timer -= 1`；收集 `timer == 0` 的 `BOMB` 与阶段 A/B 待爆的 `TNT`，按切比雪夫距离 $\le 1$（$3\times 3$ 九宫格）求引爆闭包。每颗波及勇者的 `TNT` 计机关伤 `60`、`BOMB` 计自伤 `50`（按 $\Delta D = \min(h, a+b) \times \frac{a}{a+b}$ 记有效机关伤害）。九宫格内 `CRACK` 变 `PIT`；`W`, `ICE`, `MIRROR`, `SPRING`, `LASER`, `SWITCH`, `GATE`, `HEAL`, `MIMIC` 变 `EMPTY`，`BOX` 销毁；`T_W`, `K1`, `K2`, `V`, `PORTAL`, `PIT` 免疫。随后执行支撑检查（箱子填坑、勇者落坑 `-100 HP`）。
  * **阶段 D（`turn % 3 == 0` 周期激光同步快照）**：基于阶段 C 后快照，所有存活 `LASER_*` 同时射出最长 10 格射线（遇 `HIGH_WALL`/`BOX`/`TNT` 截断，末端 `TNT` 标记待爆）。射线与 `exposed_cells` 有交集的每门激光对勇者造成 `-50 HP` 机关伤害；若勇者未死且有激光点燃的 `TNT`，调用阶段 C 爆炸闭包结算（**绝不再次递减场上 `bombs` 的 `timer`**）。

### 5. 双榜计分公式与视野契约
* 设花费 $C_{\text{spent}} \le 3000$，留存比 $g = (3000 - C_{\text{spent}}) / 3000$，整局累计有效机关伤害 $D = \min(100.0, \sum \Delta D)$，已取钥匙数 $k \in \{0,1,2\}$，当前阶段推进比 $r = \max(0, \frac{d_0 - d_{\min}}{\max(1, d_0)}) \in [0, 1)$，连续总进度 $P = k + r \in [0, 3)$：
  * **勇者存活通关**：$Score_{\text{Hero}} = 600 + 1.5 \times HP_{\text{left}} + 150 \times \frac{240 - T}{239} + 100 \times g$
  * **勇者失败（三阶段连续线性 `0~600`）**：$Score_{\text{Hero}} = 200 k + 200 r = 200 P$（仅在第 $k$ 把钥匙后的阶段采样）
  * **魔王实杀勇者（$\text{HP} \le 0$）**：$Score_{\text{Demon}} = 500 + 50(3 - P) + D + 250 g$
  * **魔王困死超时（240步 $\text{HP} > 0$）**：$Score_{\text{Demon}} = 320 + 50(3 - P) + D + 125 g$
  * **魔王失守（被通关，`0~320`）**：$Score_{\text{Demon}} = 2.0 D + 120 \times \frac{T - 1}{239}$
* **`state` 字典字段**：`turn` (1..240), `turns_left` (240..1), `mode` (第一场正赛恒为 `"BLIND"`；独立全图明牌赛为 `"FULL"`), `hero` (`{x, y, hp, keys:[bool,bool], jumps, throws, bombs}`), `gates_flipped` (bool), `targets` (`{"K1":[x,y], "K2":[x,y], "V":[x,y]}`), `visible_mask` (26x40 bool, BLIND 下为以勇者为中心满足 `dx²+dy²<=10` 的欧氏圆形视野（空旷时37格）+ 高墙视线遮挡（LOS）及相邻8格冰道延伸；冰面/折返镜滑道追踪逻辑保持不变), `terrain` (26x40 str, 不可见为 `"UNKNOWN"`, `HEAL`/`MIMIC` 脱敏为 `"CHEST"`), `occupant` (26x40 `None|"BOX"|"TNT"`), `bombs` (`[{x,y,timer}]`), `clues` (26x40 bool), `laser_warnings` (`[{x,y,dir}]`, 仅 `turn % 3 == 0` 非空)。

---


### BLIND 圆形视野与墙体遮挡（方案 B 增量约定）

基础候选格保持 `dx²+dy²<=10`，空旷中心恰为37格；存在遮挡或位于边缘时基础可见格少于37格。按 `max(|dx|,|dy|)=0,1,2,3` 由近及远判定。`sx=sign(dx)`、`sy=sign(dy)`，`open(dx,dy)=vis(dx,dy) and not is_high_wall(hx+dx,hy+dy)`，越界视为不透光：

* 近身圈（自身及8邻格）恒可见，贴身墙面本身可见。
* 外圈正交格：仅当 `open(dx-sx,dy-sy)` 为真时可见。
* `(±2,±2)`：须 `open(sx,sy)`，且 `(hx+sx,hy)` 与 `(hx,hy+sy)` 不同时为高墙，禁止斜穿封死的墙角。
* `|dx|>|dy|>0`：`open(dx-sx,dy) or open(dx-sx,dy-sy)`。
* `|dy|>|dx|>0`：`open(dx,dy-sy) or open(dx-sx,dy-sy)`。

目标格可以是可见墙面，但不能继续向后透光。沿用现有 `HIGH_WALL` 定义：`W`、`T_W`、四向 `LASER_*` 炮座及当前关闭的红/蓝门；门随 `gates_flipped` 即时变化。被遮挡的地形为 `UNKNOWN`，骸骨线索不暴露，实体不暴露。相邻8格触发的冰面/折返镜滑道延伸仍使用原逻辑，作为基础视野之外的额外照亮（第一场正赛全部以 `BLIND` 迷雾模式运行，`FULL` 全图明牌破阵将独立发卷开赛，不在本场混跑）。

## 五、 交卷代码格式契约 (`submission.py`)

```python
import bisect, collections, copy, dataclasses, enum, functools, heapq, itertools, json, math, operator, random, re, time, typing

def build_dungeon() -> dict:
    """
    返回:
    {
        "taunt": "40字以内挑衅宣言",
        "grid": [[str x 40] x 26],
        "author_solution": [str, ...] # 必须在最后一个动作恰好首次存活踏上 V 通关！
    }
    """
    pass

def decide_action(state: dict, memory: dict) -> str:
    """
    第一场正赛 100% 运行在 BLIND 迷雾模式下（请专注于圆形 LOS 视野探路、memory 增量建图与避险）
    返回 14 种合法动作字符串之一:
    MOVE_U/D/L/R, WAIT, JUMP_U/D/L/R, THROW_U/D/L/R, BOMB
    """
    pass
```
