"""
judge_v22.py — 《阴间地牢：金库攻防战》v2.2 (FULL) 本地裁判内核（逐字复刻实现）

来源：
  * v2.1 完整物理引擎契约（四层真值模型 / 8 步原子位移 / 4 阶段主循环 / 计分公式）
    已从上半场官方 RULES.md 全文逐条移植；
  * v2.2 增量（RULES_FULL_v22.md）：PLATE / P_GATE / LASER2 双频 12 拍 / ONEWAY 全场景裁决 /
    出生 4 回合准入 / author_solution <= 200 / CLEARED 计分 1.7D + 150(T-1)/239。

用途：
  1. 校验 build_dungeon() 的合法性（预算、配额、地标、MIMIC 线索、出生准入、自证路线）；
  2. 无人值守跑 decide_action() 的整局对抗（含超时/异常三振 DQ 模拟）；
  3. 逐拍回放上半场 23 局真实轨迹，回归校验本内核与官方裁判的一致性。

禁止事项与赛场一致：本文件只做纯计算，不做任何 I/O 以外的副作用（离线工具允许 I/O）。
"""

from __future__ import annotations

import heapq

W = 40
H = 26
MAX_TURNS = 240
MAX_BUDGET = 3000
MAX_AUTHOR_STEPS = 200

SPAWN = (2, 13)
SPAWN_ZONE = [(x, y) for y in (12, 13, 14) for x in (1, 2, 3)]

DIRV = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
DIR_OF = {(0, -1): "U", (0, 1): "D", (-1, 0): "L", (1, 0): "R"}

VALID_ACTIONS = frozenset((
    "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT",
    "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
    "THROW_U", "THROW_D", "THROW_L", "THROW_R", "BOMB",
))

MIRROR_FOLD = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}
SPRING_DIR = {"SPRING_U": "U", "SPRING_D": "D", "SPRING_L": "L", "SPRING_R": "R"}
PORTAL_PAIR = {
    "PORTAL_1A": "PORTAL_1B", "PORTAL_1B": "PORTAL_1A",
    "PORTAL_2A": "PORTAL_2B", "PORTAL_2B": "PORTAL_2A",
}
PORTALS = frozenset(PORTAL_PAIR)
LASER_TILES = {"LASER_U": "U", "LASER_D": "D", "LASER_L": "L", "LASER_R": "R"}
LASER2_TILES = {"LASER2_U": "U", "LASER2_D": "D", "LASER2_L": "L", "LASER2_R": "R"}
ONEWAY_TILES = {"ONEWAY_U": "U", "ONEWAY_D": "D", "ONEWAY_L": "L", "ONEWAY_R": "R"}

TILE_COST = {
    "EMPTY": 0, "K1": 0, "K2": 0, "V": 0,
    "W": 5, "T_W": 25, "ICE": 10,
    "MIRROR_NE": 25, "MIRROR_SE": 25, "MIRROR_SW": 25, "MIRROR_NW": 25,
    "SPRING_U": 35, "SPRING_D": 35, "SPRING_L": 35, "SPRING_R": 35,
    "PIT": 40, "CRACK": 20, "SWITCH": 30, "R_GATE": 20, "B_GATE": 20,
    "PLATE": 45, "P_GATE": 30,
    "LASER_U": 75, "LASER_D": 75, "LASER_L": 75, "LASER_R": 75,
    "LASER2_U": 90, "LASER2_D": 90, "LASER2_L": 90, "LASER2_R": 90,
    "ONEWAY_U": 30, "ONEWAY_D": 30, "ONEWAY_L": 30, "ONEWAY_R": 30,
    "TNT": 40, "BOX": 30, "HEAL": 30, "MIMIC": 60,
    "PORTAL_1A": 40, "PORTAL_1B": 40, "PORTAL_2A": 40, "PORTAL_2B": 40,
}

# 静态高墙（不含随状态变化的门）
HIGH_WALL_STATIC = frozenset((
    "W", "T_W",
    "LASER_U", "LASER_D", "LASER_L", "LASER_R",
    "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R",
))
# 防爆免疫地形（v2.2 新增 PLATE / P_GATE / ONEWAY_*）
BLAST_IMMUNE = frozenset((
    "T_W", "K1", "K2", "V", "PIT",
    "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
    "PLATE", "P_GATE",
    "ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R",
))
# 被炸毁 -> EMPTY
BLAST_WIPE = frozenset((
    "W", "ICE", "SWITCH", "R_GATE", "B_GATE", "HEAL", "MIMIC",
    "MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW",
    "SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R",
    "LASER_U", "LASER_D", "LASER_L", "LASER_R",
    "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R",
))


# =============================================================================
# 合法性校验
# =============================================================================

def validate_dungeon(grid):
    """返回 (ok, errors, info)。info 含 spent_gold / vault_gold / 各类计数。"""
    errs = []
    info = {}
    if not isinstance(grid, (list, tuple)) or len(grid) != H:
        return False, ["grid 行数必须为 26"], info
    for y in range(H):
        row = grid[y]
        if not isinstance(row, (list, tuple)) or len(row) != W:
            return False, ["grid[%d] 列数必须为 40" % y], info

    counts = {}
    spent = 0
    for y in range(H):
        for x in range(W):
            t = grid[y][x]
            if not isinstance(t, str) or t not in TILE_COST:
                errs.append("非法组件 %r @ (%d,%d)" % (t, x, y))
                continue
            counts[t] = counts.get(t, 0) + 1
            if x in (0, W - 1) or y in (0, H - 1):
                if t != "T_W":
                    errs.append("外框 (%d,%d) 必须为 T_W，实为 %s" % (x, y, t))
            else:
                spent += TILE_COST[t]

    # 出生净空区
    for (x, y) in SPAWN_ZONE:
        if grid[y][x] != "EMPTY":
            errs.append("出生净空区 (%d,%d) 必须为 EMPTY，实为 %s" % (x, y, grid[y][x]))

    # 地标
    def _find(tile):
        return [(x, y) for y in range(1, H - 1) for x in range(1, W - 1) if grid[y][x] == tile]

    k1 = _find("K1")
    k2 = _find("K2")
    vv = _find("V")
    if len(k1) != 1:
        errs.append("K1 必须恰 1 个，实为 %d" % len(k1))
    if len(k2) != 1:
        errs.append("K2 必须恰 1 个，实为 %d" % len(k2))
    if len(vv) != 1:
        errs.append("V 必须恰 1 个，实为 %d" % len(vv))
    if len(k1) == 1:
        x, y = k1[0]
        if not (12 <= x <= 34 and 2 <= y <= 10):
            errs.append("K1 坐标 (%d,%d) 越界" % (x, y))
    if len(k2) == 1:
        x, y = k2[0]
        if not (12 <= x <= 34 and 15 <= y <= 23):
            errs.append("K2 坐标 (%d,%d) 越界" % (x, y))
    if len(k1) == 1 and len(k2) == 1:
        d = abs(k1[0][0] - k2[0][0]) + abs(k1[0][1] - k2[0][1])
        if d < 12:
            errs.append("K1/K2 曼哈顿距离 %d < 12" % d)
        info["key_dist"] = d
    if len(vv) == 1:
        x, y = vv[0]
        if not (33 <= x <= 37 and 4 <= y <= 21):
            errs.append("V 坐标 (%d,%d) 越界" % (x, y))

    # 内圈配额
    def inner(tile):
        return sum(1 for y in range(1, H - 1) for x in range(1, W - 1) if grid[y][x] == tile)

    def group(tiles):
        return sum(counts.get(t, 0) for t in tiles)

    limits = {
        "T_W(inner)": (inner("T_W"), 120),
        "MIRROR*": (group(MIRROR_FOLD), 30),
        "SPRING*": (group(SPRING_DIR), 20),
        "LASER*+LASER2*": (group(LASER_TILES) + group(LASER2_TILES), 12),
        "CRACK": (counts.get("CRACK", 0), 40),
        "SWITCH": (counts.get("SWITCH", 0), 6),
        "R_GATE+B_GATE": (counts.get("R_GATE", 0) + counts.get("B_GATE", 0), 16),
        "PLATE": (counts.get("PLATE", 0), 4),
        "P_GATE": (counts.get("P_GATE", 0), 8),
        "ONEWAY*": (group(ONEWAY_TILES), 12),
        "TNT": (counts.get("TNT", 0), 12),
        "BOX": (counts.get("BOX", 0), 6),
        "HEAL": (counts.get("HEAL", 0), 4),
        "MIMIC": (counts.get("MIMIC", 0), 4),
    }
    for k, (have, cap) in limits.items():
        if have > cap:
            errs.append("配额超限 %s: %d > %d" % (k, have, cap))
        info[k] = have

    # 传送门成对
    for a, b in (("PORTAL_1A", "PORTAL_1B"), ("PORTAL_2A", "PORTAL_2B")):
        if counts.get(a, 0) != counts.get(b, 0):
            errs.append("传送门 %s/%s 未成对" % (a, b))
        if counts.get(a, 0) > 1 or counts.get(b, 0) > 1:
            errs.append("传送门 %s/%s 同编号重复" % (a, b))

    # 压板硬约束
    if counts.get("P_GATE", 0) > 0:
        p = counts.get("PLATE", 0)
        b = counts.get("BOX", 0)
        if not (1 <= p <= b):
            errs.append("使用 P_GATE 必须满足 1 <= PLATE(%d) <= BOX(%d)" % (p, b))

    if spent > MAX_BUDGET:
        errs.append("预算超限 %d > %d" % (spent, MAX_BUDGET))

    info["spent_gold"] = spent
    info["vault_gold"] = MAX_BUDGET - spent
    info["g"] = (MAX_BUDGET - spent) / MAX_BUDGET
    info["counts"] = counts
    return (len(errs) == 0), errs, info


def bind_clues(grid):
    """按官方行优先顺序为每个 MIMIC 绑定专属骸骨线索格。返回 (clues, mimic_binding, errs)。"""
    terrain = [[("EMPTY" if grid[y][x] in ("BOX", "TNT") else grid[y][x]) for x in range(W)] for y in range(H)]
    occ = [[(grid[y][x] if grid[y][x] in ("BOX", "TNT") else None) for x in range(W)] for y in range(H)]
    clues = [[False] * W for _ in range(H)]
    binding = {}
    errs = []
    chests = set()
    for y in range(H):
        for x in range(W):
            if grid[y][x] in ("HEAL", "MIMIC"):
                chests.add((x, y))
    for y in range(H):
        for x in range(W):
            if grid[y][x] != "MIMIC":
                continue
            best = None
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < W and 0 <= ny < H):
                    continue
                if terrain[ny][nx] != "EMPTY" or occ[ny][nx] is not None:
                    continue
                if 1 <= nx <= 3 and 12 <= ny <= 14:
                    continue
                if clues[ny][nx]:
                    continue
                # 该格四邻中不得存在除当前 MIMIC 外的其他宝箱
                bad = False
                for ddx, ddy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    px, py = nx + ddx, ny + ddy
                    if (px, py) in chests and (px, py) != (x, y):
                        bad = True
                        break
                if bad:
                    continue
                best = (nx, ny)
                break
            if best is None:
                errs.append("MIMIC@(%d,%d) 找不到合法专属线索格" % (x, y))
            else:
                clues[best[1]][best[0]] = True
                binding[(x, y)] = best
    return clues, binding, errs


# =============================================================================
# 计分
# =============================================================================

def hero_score(cleared, turns, hp_left, keys, progress_p, g):
    if cleared:
        return 600.0 + 1.5 * max(0, hp_left) + 150.0 * (MAX_TURNS - turns) / 239.0 + 100.0 * g
    return 200.0 * progress_p


def demon_score(outcome, turns, damage, progress_p, g):
    """outcome in {DEAD, TIMEOUT, CLEARED, DQ}"""
    D = min(100.0, damage)
    if outcome == "DEAD":
        return 500.0 + 50.0 * (3.0 - progress_p) + D + 250.0 * g
    if outcome in ("TIMEOUT", "DQ"):
        return 320.0 + 50.0 * (3.0 - progress_p) + D + 125.0 * g
    # CLEARED
    return 1.7 * D + 150.0 * (turns - 1) / 239.0


# =============================================================================
# 裁判内核
# =============================================================================

class Judge:
    def __init__(self, grid, seed=20261115):
        self.grid0 = [list(r) for r in grid]
        self.terrain = [[("EMPTY" if self.grid0[y][x] in ("BOX", "TNT") else self.grid0[y][x])
                         for x in range(W)] for y in range(H)]
        self.occ = [[(self.grid0[y][x] if self.grid0[y][x] in ("BOX", "TNT") else None)
                     for x in range(W)] for y in range(H)]
        self.clues, self.mimic_binding, _e = bind_clues(self.grid0)
        self.plate_cells = [(x, y) for y in range(H) for x in range(W) if self.terrain[y][x] == "PLATE"]
        self.pair_pos = {}
        for y in range(H):
            for x in range(W):
                t = self.terrain[y][x]
                if t in PORTALS:
                    self.pair_pos[t] = (x, y)
        self.turn = 0
        self.hero = {"x": SPAWN[0], "y": SPAWN[1], "hp": 100,
                     "keys": [False, False], "jumps": 3, "throws": 3, "bombs": 2}
        self.gates_flipped = False
        self.bombs = {}          # (x,y) -> timer
        self.damage_total = 0.0  # 累计有效机关伤害（用于 D）
        self.exposed = set()
        self.tnt_armed = set()
        self.status = None       # None / CLEARED / DEAD / TIMEOUT
        self.events = []         # 关键事件（供战报）
        self.trace = [(SPAWN[0], SPAWN[1], 100, (False, False), False)]  # 每回合末

    # ---------------- 基础查询 ----------------
    def inside(self, x, y):
        return 0 <= x < W and 0 <= y < H

    def plates_active(self):
        if not self.plate_cells:
            return False
        for (x, y) in self.plate_cells:
            if self.occ[y][x] != "BOX":
                return False
        return True

    def is_high_wall(self, x, y):
        t = self.terrain[y][x]
        if t in HIGH_WALL_STATIC:
            return True
        if t == "R_GATE":
            return not self.gates_flipped
        if t == "B_GATE":
            return self.gates_flipped
        if t == "P_GATE":
            return not self.plates_active()
        return False

    def blocks_oneway(self, x, y, dirv):
        t = self.terrain[y][x]
        d = ONEWAY_TILES.get(t)
        if d is None:
            return False
        return dirv != DIRV[d]

    def _trap(self, amt, kind, pos):
        """机关伤害：累计有效机关伤害 min(hp, amt)。"""
        eff = min(self.hero["hp"], amt)
        self.damage_total += eff
        self.hero["hp"] -= amt
        self.events.append("T%d:%s %s @(%d,%d) HP->%d" % (
            self.turn, kind, "%.0f" % amt, pos[0], pos[1], self.hero["hp"]))

    def _can_enter(self, x, y, dirv, kind, box_avoid_hero=True):
        if not self.inside(x, y):
            return False
        if self.is_high_wall(x, y):
            return False
        o = self.occ[y][x]
        if o in ("BOX", "TNT"):
            return False
        if kind == "BOX":
            if box_avoid_hero and (x, y) == (self.hero["x"], self.hero["y"]):
                return False
            if self.terrain[y][x] in ("K1", "K2", "V"):
                return False
        if self.blocks_oneway(x, y, dirv):
            return False
        return True

    # ---------------- 8 步原子位移 ----------------
    def _move_entity(self, kind, p0, p1, dirv):
        """kind: 'HERO' / 'BOX'。返回是否通关/死亡（已写入 self.status）。"""
        steps = 0
        portal_count = 0
        suppress = False
        stop_momentum = False
        while True:
            steps += 1
            # 2. 离开钩子
            if self.terrain[p0[1]][p0[0]] == "CRACK":
                self.terrain[p0[1]][p0[0]] = "PIT"
                self.events.append("T%d:裂板坍塌@(%d,%d)" % (self.turn, p0[0], p0[1]))
            # 3. 更新坐标
            if kind == "BOX":
                self.occ[p0[1]][p0[0]] = None
                self.occ[p1[1]][p1[0]] = "BOX"
            else:
                self.hero["x"], self.hero["y"] = p1
                self.exposed.add(p1)
            # 4. 落点钩子
            t1 = self.terrain[p1[1]][p1[0]]
            if kind == "BOX":
                if t1 == "PIT":
                    self.occ[p1[1]][p1[0]] = None
                    self.terrain[p1[1]][p1[0]] = "EMPTY"
                    stop_momentum = True
                    self.events.append("T%d:箱子填坑@(%d,%d)" % (self.turn, p1[0], p1[1]))
                elif t1 == "MIMIC":
                    self.terrain[p1[1]][p1[0]] = "EMPTY"
                    self._clear_clue(p1)
                elif t1 == "SWITCH":
                    self.gates_flipped = not self.gates_flipped
                    self.events.append("T%d:拨开关(BOX)@(%d,%d)" % (self.turn, p1[0], p1[1]))
            else:
                if t1 == "PIT":
                    self._trap(100, "PIT", p1)
                elif t1 == "MIMIC":
                    self._trap(45, "MIMIC", p1)
                    self.terrain[p1[1]][p1[0]] = "EMPTY"
                    self._clear_clue(p1)
                    stop_momentum = True
                elif t1 == "HEAL":
                    self.hero["hp"] = min(100, self.hero["hp"] + 30)
                    self.terrain[p1[1]][p1[0]] = "EMPTY"
                    self.events.append("T%d:回血+30(HP->%d)@(%d,%d)" % (
                        self.turn, self.hero["hp"], p1[0], p1[1]))
                elif t1 == "SWITCH":
                    self.gates_flipped = not self.gates_flipped
                    self.events.append("T%d:拨开关(HERO)@(%d,%d)" % (self.turn, p1[0], p1[1]))
            # 5. 死亡截断
            if kind == "HERO" and self.hero["hp"] <= 0:
                self.status = "DEAD"
                return True
            # 6. 钥匙 / 通关
            if kind == "HERO":
                if t1 == "K1":
                    self.hero["keys"][0] = True
                    self.terrain[p1[1]][p1[0]] = "EMPTY"
                    self.events.append("T%d:拾取K1@(%d,%d)" % (self.turn, p1[0], p1[1]))
                    self._note_progress()
                elif t1 == "K2":
                    self.hero["keys"][1] = True
                    self.terrain[p1[1]][p1[0]] = "EMPTY"
                    self.events.append("T%d:拾取K2@(%d,%d)" % (self.turn, p1[0], p1[1]))
                    self._note_progress()
                elif t1 == "V" and self.hero["keys"][0] and self.hero["keys"][1] and self.hero["hp"] > 0:
                    self.status = "CLEARED"
                    self.events.append("T%d:破库通关@(%d,%d)" % (self.turn, p1[0], p1[1]))
                    return True
            # 7. 位移上限
            if steps >= 32 or stop_momentum:
                break
            # 8. 动量延续
            t1 = self.terrain[p1[1]][p1[0]]
            nxt = None
            newdir = dirv
            if t1 == "ICE":
                nxt = (p1[0] + dirv[0], p1[1] + dirv[1])
                if not self._can_enter(nxt[0], nxt[1], dirv, kind):
                    nxt = None
            elif t1 in MIRROR_FOLD:
                nd = MIRROR_FOLD[t1][DIR_OF[dirv]]
                newdir = DIRV[nd]
                nxt = (p1[0] + newdir[0], p1[1] + newdir[1])
                if not self._can_enter(nxt[0], nxt[1], newdir, kind):
                    nxt = None
            elif t1 in SPRING_DIR:
                sd = DIRV[SPRING_DIR[t1]]
                newdir = sd
                land = (p1[0] + 3 * sd[0], p1[1] + 3 * sd[1])
                if not self.inside(land[0], land[1]):
                    land = None
                for k in (1, 2, 3):
                    px, py = p1[0] + k * sd[0], p1[1] + k * sd[1]
                    blocked = (not self.inside(px, py)) or self.is_high_wall(px, py) or \
                        self.occ[py][px] in ("BOX", "TNT") or self.blocks_oneway(px, py, sd)
                    if kind == "BOX" and self.inside(px, py):
                        if (px, py) == (self.hero["x"], self.hero["y"]) or \
                                self.terrain[py][px] in ("K1", "K2", "V"):
                            blocked = True
                    if blocked:
                        if kind == "BOX" and self.inside(px, py) and self.occ[py][px] == "TNT":
                            self.tnt_armed.add((px, py))
                        land = (p1[0] + (k - 1) * sd[0], p1[1] + (k - 1) * sd[1]) if k >= 2 else None
                        break
                nxt = land
            elif t1 in PORTALS and not suppress:
                pairpos = self.pair_pos.get(PORTAL_PAIR[t1])
                okp = pairpos is not None and self.occ[pairpos[1]][pairpos[0]] is None
                if kind == "BOX" and okp and pairpos == (self.hero["x"], self.hero["y"]):
                    okp = False
                if okp:
                    portal_count += 1
                    nxt = pairpos
                    newdir = dirv
                    suppress = True
                else:
                    nxt = None
            elif t1 in PORTALS and suppress:
                suppress = False
                if portal_count >= 2:
                    nxt = None
                else:
                    fx, fy = p1[0] + dirv[0], p1[1] + dirv[1]
                    if self._can_enter(fx, fy, dirv, kind):
                        nxt = (fx, fy)
                    else:
                        nxt = None
            if nxt is None:
                break
            p0, p1 = p1, nxt
            dirv = newdir
        return False

    def _clear_clue(self, pos):
        c = self.mimic_binding.get(pos)
        if c is not None:
            self.clues[c[1]][c[0]] = False
            del self.mimic_binding[pos]

    def _note_progress(self):
        pass

    # ---------------- 爆炸 ----------------
    def _explode(self, sources):
        """sources: iterable of (x,y) 爆源（TNT 或 BOMB）。"""
        q = []
        seen = set()
        for s in sources:
            if s not in seen:
                seen.add(s)
                q.append(s)
        all_src = []
        while q:
            s = q.pop()
            all_src.append(s)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cx, cy = s[0] + dx, s[1] + dy
                    if not self.inside(cx, cy):
                        continue
                    if (cx, cy) in seen:
                        continue
                    if self.occ[cy][cx] == "TNT" or (cx, cy) in self.bombs:
                        seen.add((cx, cy))
                        q.append((cx, cy))
        # 伤害
        a = 0
        b = 0
        hx, hy = self.hero["x"], self.hero["y"]
        for (sx, sy) in all_src:
            if abs(sx - hx) <= 1 and abs(sy - hy) <= 1:
                if self.occ[sy][sx] == "TNT":
                    a += 60
                elif (sx, sy) in self.bombs:
                    b += 50
        if a + b > 0:
            hp = self.hero["hp"]
            eff = min(hp, a + b) * (a / float(a + b))
            self.damage_total += eff
            self.hero["hp"] -= (a + b)
            self.events.append("T%d:爆炸 机关%d 自伤%d HP->%d" % (self.turn, a, b, self.hero["hp"]))
        # 移除爆源
        for (sx, sy) in all_src:
            if self.occ[sy][sx] == "TNT":
                self.occ[sy][sx] = None
            self.bombs.pop((sx, sy), None)
        # 地形
        union = set()
        for (sx, sy) in all_src:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cx, cy = sx + dx, sy + dy
                    if self.inside(cx, cy):
                        union.add((cx, cy))
        for (cx, cy) in union:
            if self.occ[cy][cx] == "BOX":
                self.occ[cy][cx] = None
            t = self.terrain[cy][cx]
            if t in BLAST_IMMUNE:
                continue
            if t == "CRACK":
                self.terrain[cy][cx] = "PIT"
            elif t in BLAST_WIPE:
                self.terrain[cy][cx] = "EMPTY"
                if t == "MIMIC":
                    self._clear_clue((cx, cy))
        # 支撑检查
        for (cx, cy) in union:
            if self.occ[cy][cx] == "BOX" and self.terrain[cy][cx] == "PIT":
                self.occ[cy][cx] = None
                self.terrain[cy][cx] = "EMPTY"
        if self.hero["hp"] > 0 and self.terrain[self.hero["y"]][self.hero["x"]] == "PIT":
            self._trap(100, "PIT(塌陷)", (self.hero["x"], self.hero["y"]))
        if self.hero["hp"] <= 0:
            self.status = "DEAD"

    # ---------------- 激光 ----------------
    def _rays(self, red, blue, snapshot=True):
        """返回 [(lx,ly,dir,period,[(x,y),...]), ...] 与 armed TNT 集合。"""
        out = []
        armed = set()
        for y in range(H):
            for x in range(W):
                t = self.terrain[y][x]
                if t in LASER_TILES:
                    if not red:
                        continue
                    d = LASER_TILES[t]
                    period = 3
                elif t in LASER2_TILES:
                    if not blue:
                        continue
                    d = LASER2_TILES[t]
                    period = 4
                else:
                    continue
                dx, dy = DIRV[d]
                cells = []
                for step in range(1, 11):
                    nx, ny = x + dx * step, y + dy * step
                    if not self.inside(nx, ny):
                        break
                    if self.is_high_wall(nx, ny) or self.occ[ny][nx] == "BOX":
                        break
                    if self.occ[ny][nx] == "TNT":
                        armed.add((nx, ny))
                        break
                    cells.append((nx, ny))
                out.append((x, y, d, period, cells))
        return out, armed

    def laser_firing(self, turn):
        return (turn % 3 == 0, turn % 4 == 0)

    # ---------------- 回合推进 ----------------
    def play(self, action):
        if self.status is not None:
            return self.status
        self.turn += 1
        if action not in VALID_ACTIONS:
            action = "WAIT"
        self.exposed = {(self.hero["x"], self.hero["y"])}
        self.tnt_armed = set()

        # ---- 阶段 A/B
        hx, hy = self.hero["x"], self.hero["y"]
        if action == "WAIT":
            pass
        elif action == "BOMB":
            if self.hero["bombs"] > 0 and (hx, hy) not in self.bombs:
                self.hero["bombs"] -= 1
                self.bombs[(hx, hy)] = 3
        elif action.startswith("MOVE_"):
            d = action[5]
            dx, dy = DIRV[d]
            p1 = (hx + dx, hy + dy)
            if not self.inside(*p1) or self.is_high_wall(*p1) or self.occ[p1[1]][p1[0]] == "TNT":
                pass
            elif self.occ[p1[1]][p1[0]] == "BOX":
                if self.blocks_oneway(p1[0], p1[1], (dx, dy)):
                    pass  # 逆向推箱 -> 整次动作拒绝，箱子不动、CRACK 不塌
                else:
                    p2 = (hx + 2 * dx, hy + 2 * dy)
                    if self._can_enter(p2[0], p2[1], (dx, dy), "BOX"):
                        self._move_entity("BOX", p1, p2, (dx, dy))
                        if self.status is None and self._can_enter(p1[0], p1[1], (dx, dy), "HERO"):
                            self._move_entity("HERO", (hx, hy), p1, (dx, dy))
            elif self.blocks_oneway(p1[0], p1[1], (dx, dy)):
                pass
            else:
                self._move_entity("HERO", (hx, hy), p1, (dx, dy))
        elif action.startswith("JUMP_"):
            d = action[5]
            if self.hero["jumps"] > 0:
                self.hero["jumps"] -= 1
                dx, dy = DIRV[d]
                p1 = (hx + dx, hy + dy)
                p2 = (hx + 2 * dx, hy + 2 * dy)
                bad = (not self.inside(*p1)) or self.is_high_wall(*p1) or \
                    self.blocks_oneway(p1[0], p1[1], (dx, dy))
                if not bad:
                    if (not self.inside(*p2)) or self.is_high_wall(*p2) or \
                            self.occ[p2[1]][p2[0]] in ("BOX", "TNT") or \
                            self.blocks_oneway(p2[0], p2[1], (dx, dy)):
                        bad = True
                if not bad:
                    self._move_entity("HERO", (hx, hy), p2, (dx, dy))
        elif action.startswith("THROW_"):
            d = action[6]
            if self.hero["throws"] > 0:
                self.hero["throws"] -= 1
                self._throw(hx, hy, DIRV[d])

        if self.status is None:
            # ---- 阶段 C
            for k in list(self.bombs.keys()):
                self.bombs[k] -= 1
            srcs = [p for p, t in self.bombs.items() if t <= 0]
            srcs += list(self.tnt_armed)
            if srcs:
                self._explode(srcs)

        if self.status is None:
            # ---- 阶段 D
            red, blue = self.laser_firing(self.turn)
            if red or blue:
                rays, armed = self._rays(red, blue)
                m = 0
                for (lx, ly, d, period, cells) in rays:
                    for c in cells:
                        if c in self.exposed:
                            m += 1
                            break
                if m > 0:
                    eff = min(self.hero["hp"], 50 * m)
                    self.damage_total += eff
                    self.hero["hp"] -= 50 * m
                    self.events.append("T%d:激光命中 x%d HP->%d" % (self.turn, m, self.hero["hp"]))
                    if self.hero["hp"] <= 0:
                        self.status = "DEAD"
                if self.status is None and armed:
                    self._explode(list(armed))

        if self.status is None and self.turn >= MAX_TURNS:
            self.status = "TIMEOUT"
        self._record()
        return self.status

    def _record(self):
        self.trace.append((self.hero["x"], self.hero["y"], self.hero["hp"],
                           tuple(self.hero["keys"]), self.gates_flipped))

    def _throw(self, sx, sy, dirv):
        range_left = 6
        stone_portals = 0
        dirv = tuple(dirv)
        while range_left > 0:
            nx, ny = sx + dirv[0], sy + dirv[1]
            if not self.inside(nx, ny):
                return
            range_left -= 1
            sx, sy = nx, ny
            if self.is_high_wall(nx, ny) or self.occ[ny][nx] == "BOX":
                return
            if self.occ[ny][nx] == "TNT":
                self.tnt_armed.add((nx, ny))
                return
            t = self.terrain[ny][nx]
            if t == "SWITCH":
                self.gates_flipped = not self.gates_flipped
                self.events.append("T%d:飞石拨开关@(%d,%d)" % (self.turn, nx, ny))
                return
            if t == "MIMIC":
                self.terrain[ny][nx] = "EMPTY"
                self._clear_clue((nx, ny))
                return
            if t in MIRROR_FOLD:
                nd = MIRROR_FOLD[t][DIR_OF[dirv]]
                dirv = DIRV[nd]
                continue
            if t in PORTALS and stone_portals < 2:
                pp = self.pair_pos.get(PORTAL_PAIR[t])
                if pp is not None and self.occ[pp[1]][pp[0]] not in ("BOX", "TNT"):
                    sx, sy = pp
                    stone_portals += 1
                    if stone_portals >= 2:
                        return
                    continue
        # 第 6 格落地滑行
        t = self.terrain[sy][sx]
        if t not in ("ICE",) and t not in MIRROR_FOLD:
            return
        for _ in range(32):
            nx, ny = sx + dirv[0], sy + dirv[1]
            if not self.inside(nx, ny):
                return
            sx, sy = nx, ny
            if self.is_high_wall(nx, ny) or self.occ[ny][nx] == "BOX":
                return
            if self.occ[ny][nx] == "TNT":
                self.tnt_armed.add((nx, ny))
                return
            t = self.terrain[ny][nx]
            if t == "SWITCH":
                self.gates_flipped = not self.gates_flipped
                self.events.append("T%d:飞石拨开关@(%d,%d)" % (self.turn, nx, ny))
                return
            if t == "MIMIC":
                self.terrain[ny][nx] = "EMPTY"
                self._clear_clue((nx, ny))
                return
            if t in MIRROR_FOLD:
                nd = MIRROR_FOLD[t][DIR_OF[dirv]]
                dirv = DIRV[nd]
                continue
            if t == "ICE":
                continue
            if t in PORTALS and stone_portals < 2:
                pp = self.pair_pos.get(PORTAL_PAIR[t])
                if pp is not None and self.occ[pp[1]][pp[0]] not in ("BOX", "TNT"):
                    sx, sy = pp
                    stone_portals += 1
                    if stone_portals >= 2:
                        return
                    continue
            return

    # ---------------- 观测 ----------------
    def observe(self):
        terr = []
        for y in range(H):
            row = []
            for x in range(W):
                t = self.terrain[y][x]
                row.append("CHEST" if t in ("HEAL", "MIMIC") else t)
            terr.append(row)
        left = MAX_TURNS - self.turn
        state = {
            "turn": self.turn + 1,
            "turns_left": max(0, left),
            "mode": "FULL",
            "hero": {"x": self.hero["x"], "y": self.hero["y"], "hp": self.hero["hp"],
                     "keys": list(self.hero["keys"]), "jumps": self.hero["jumps"],
                     "throws": self.hero["throws"], "bombs": self.hero["bombs"]},
            "gates_flipped": self.gates_flipped,
            "targets": self._targets(),
            "visible_mask": [[True] * W for _ in range(H)],
            "terrain": terr,
            "occupant": [row[:] for row in self.occ],
            "bombs": [{"x": p[0], "y": p[1], "timer": t} for p, t in self.bombs.items()],
            "clues": [row[:] for row in self.clues],
            "laser_warnings": [],
            "plates_active": self.plates_active(),
        }
        nt = self.turn + 1
        red, blue = self.laser_firing(nt)
        if red or blue:
            rays, _armed = self._rays(red, blue)
            warn = []
            for (lx, ly, d, period, cells) in rays:
                for (cx, cy) in cells:
                    warn.append({"x": cx, "y": cy, "dir": d, "period": period,
                                 "cannon": [lx, ly]})
            warn.sort(key=lambda o: (o["y"], o["x"], o["dir"], o["period"], o["cannon"][0], o["cannon"][1]))
            state["laser_warnings"] = warn
        return state

    def _targets(self):
        t = {}
        for name in ("K1", "K2", "V"):
            for y in range(H):
                for x in range(W):
                    if self.terrain[y][x] == name:
                        t[name] = [x, y]
                        break
                if name in t:
                    break
        return t

    # ---------------- 进度 P ----------------
    def progress_now(self):
        keys = sum(1 for k in self.hero["keys"] if k)
        tgt = self._targets()
        hx, hy = self.hero["x"], self.hero["y"]
        if keys == 0:
            cands = [tgt.get("K1"), tgt.get("K2")]
            cands = [c for c in cands if c]
            if not cands:
                return 0.0
            dmin = min(abs(c[0] - hx) + abs(c[1] - hy) for c in cands)
        elif keys == 1:
            rem = [tgt.get(n) for n in (("K2",) if self.hero["keys"][0] else ("K1",))]
            rem = [c for c in rem if c]
            if not rem:
                return 1.0
            dmin = min(abs(c[0] - hx) + abs(c[1] - hy) for c in rem)
        else:
            v = tgt.get("V")
            if not v:
                return 2.0
            dmin = abs(v[0] - hx) + abs(v[1] - hy)
        return keys, dmin


class ProgressTracker:
    """按官方口径维护 P = k + r（阶段内最小距离推进比）。"""

    def __init__(self, judge):
        self.j = judge
        self.best = {}

    def update(self):
        j = self.j
        keys = sum(1 for k in j.hero["keys"] if k)
        tgt = j._targets()
        hx, hy = j.hero["x"], j.hero["y"]
        if keys == 0:
            cands = [tgt.get("K1"), tgt.get("K2")]
            cands = [c for c in cands if c]
            if not cands:
                return 0.0
            d = min(abs(c[0] - hx) + abs(c[1] - hy) for c in cands)
        elif keys == 1:
            name = "K2" if j.hero["keys"][0] else "K1"
            c = tgt.get(name)
            d = abs(c[0] - hx) + abs(c[1] - hy) if c else 0
        else:
            c = tgt.get("V")
            d = abs(c[0] - hx) + abs(c[1] - hy) if c else 0
        st = self.best.get(keys)
        if st is None:
            self.best[keys] = [d, d]
        else:
            st[0] = min(st[0], d)
        d0 = self.best[keys][0]
        dmin = self.best[keys][1]
        r = max(0.0, (d0 - dmin) / max(1, d0))
        return keys + r


def replay(grid, actions, max_turns=MAX_TURNS):
    """按给定动作序列跑完一局，返回 (judge, outcome)。"""
    j = Judge(grid)
    for a in actions:
        if j.status is not None:
            break
        j.play(a)
    if j.status is None:
        j.status = "TIMEOUT" if j.turn >= MAX_TURNS else "UNDONE"
    return j, j.status
