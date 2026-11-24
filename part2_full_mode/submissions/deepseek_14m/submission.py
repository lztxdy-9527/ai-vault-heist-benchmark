"""
《阴间地牢：金库攻防战》 下半场 v2.2 (FULL 全图明牌 · 攻守双重构) 参赛提交
DeepSeek V4.1 Flash 1017 (max) — 席位 `deepseek`

  魔王侧 `build_dungeon()`：
    在 v2.2 新机关（PLATE/P_GATE + LASER2 双频 12 拍 + ONEWAY）上重构的"金库三重门"逻辑迷宫，
    全部机关均为"必须真实求解"的多步骤谜题：推箱压板开门 / 单向阀门单向通行 / 双频激光节拍窗；
    附 1..200 步作者自证路线（最后一步恰好首次踏上 V）。

  勇者侧 `decide_action()`：
    FULL 明牌下的时间展开分层规划器：
      · `_World` 从观测快照还原真值图（CHEST + clues 反解 HEAL/MIMIC）；
      · 时间展开 A*（cell × gates × turn%12）算最短安全路线，激光按 3/4 双频 12 拍相位记账；
      · 推箱子规划（Sokoban-push BFS，含冰面/斜坡/弹簧动量链）解决 PLATE/P_GATE 与填坑；
      · 飞石引爆 TNT 破墙子规划；
      · 每个候选计划都用内置前向引擎 `_Sim` 全量复演校验，只走校验通过的计划。
    Turn 1 用 1.60s 全局规划；Turn>=2 用 0.42s 复核（计划有效则直接执行首步，否则重规划）。
    进程被重建（memory 清空）时，Turn>1 也能在预算内重新规划，最差降级为安全保守动作。
"""

import heapq
import time

GRID_W = 40
GRID_H = 26
CELLS = GRID_W * GRID_H
MAX_TURNS = 240
MAX_AUTHOR_STEPS = 200
SPAWN = (2, 13)

DIRV = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
DIR_OF = {(0, -1): "U", (0, 1): "D", (-1, 0): "L", (1, 0): "R"}
DIR_KEYS = ("U", "D", "L", "R")
MOVE_ACT = {"U": "MOVE_U", "D": "MOVE_D", "L": "MOVE_L", "R": "MOVE_R"}
JUMP_ACT = {"U": "JUMP_U", "D": "JUMP_D", "L": "JUMP_L", "R": "JUMP_R"}
THROW_ACT = {"U": "THROW_U", "D": "THROW_D", "L": "THROW_L", "R": "THROW_R"}

VALID_ACTIONS = frozenset((
    "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT",
    "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
    "THROW_U", "THROW_D", "THROW_L", "THROW_R", "BOMB",
))

HIGH_WALL = frozenset(("W", "T_W",
                       "LASER_U", "LASER_D", "LASER_L", "LASER_R",
                       "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R"))
LASER_TILES = {"LASER_U": "U", "LASER_D": "D", "LASER_L": "L", "LASER_R": "R"}
LASER2_TILES = {"LASER2_U": "U", "LASER2_D": "D", "LASER2_L": "L", "LASER2_R": "R"}
MIRROR_FOLD = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}
SPRING_DIR = {"SPRING_U": "U", "SPRING_D": "D", "SPRING_L": "L", "SPRING_R": "R"}
ONEWAY_DIR = {"ONEWAY_U": "U", "ONEWAY_D": "D", "ONEWAY_L": "L", "ONEWAY_R": "R"}
PORTAL_PAIR = {"PORTAL_1A": "PORTAL_1B", "PORTAL_1B": "PORTAL_1A",
               "PORTAL_2A": "PORTAL_2B", "PORTAL_2B": "PORTAL_2A"}
PORTALS = frozenset(PORTAL_PAIR)
BLAST_IMMUNE = frozenset(("T_W", "K1", "K2", "V", "PIT",
                          "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
                          "PLATE", "P_GATE",
                          "ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R"))
BLAST_WIPE = frozenset(("W", "ICE", "SWITCH", "R_GATE", "B_GATE", "HEAL", "MIMIC",
                        "MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW",
                        "SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R",
                        "LASER_U", "LASER_D", "LASER_L", "LASER_R",
                        "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R"))
CHEST_TILES = frozenset(("HEAL", "MIMIC"))


# =============================================================================
# 一、前向仿真内核（v2.2 规则逐字实现；用于计划校验与战斗推演）
# =============================================================================

class _Sim:

    def __init__(self, ter=None, occ=None, hero=None, gates=None, turn=1):
        if ter is None:
            return
        self.ter = [row[:] for row in ter]
        self.occ = [row[:] for row in occ]
        self.hx, self.hy = hero[0], hero[1]
        self.hp = hero[2]
        self.k1, self.k2 = bool(hero[3]), bool(hero[4])
        self.jumps, self.throws, self.bombs = hero[5], hero[6], hero[7]
        self.gates = bool(gates)
        self.turn = turn
        self.bmap = {}
        self.dmg = 0.0
        self.status = None
        self.exposed = set()
        self.tnt_armed = set()

    def clone(self):
        s = _Sim()
        s.ter = [row[:] for row in self.ter]
        s.occ = [row[:] for row in self.occ]
        s.hx, s.hy, s.hp = self.hx, self.hy, self.hp
        s.k1, s.k2 = self.k1, self.k2
        s.jumps, s.throws, s.bombs = self.jumps, self.throws, self.bombs
        s.gates = self.gates
        s.turn = self.turn
        s.bmap = dict(self.bmap)
        s.dmg = self.dmg
        s.status = self.status
        s.exposed = set()
        s.tnt_armed = set()
        return s

    def inside(self, x, y):
        return 0 <= x < GRID_W and 0 <= y < GRID_H

    def plates_active(self):
        found = False
        for y in range(1, GRID_H - 1):
            row = self.ter[y]
            for x in range(1, GRID_W - 1):
                if row[x] == "PLATE":
                    found = True
                    if self.occ[y][x] != "BOX":
                        return False
        return found

    def high_wall(self, x, y):
        t = self.ter[y][x]
        if t in HIGH_WALL:
            return True
        if t == "R_GATE":
            return not self.gates
        if t == "B_GATE":
            return self.gates
        if t == "P_GATE":
            return not self.plates_active()
        return False

    def blocks_oneway(self, x, y, dirv):
        d = ONEWAY_DIR.get(self.ter[y][x])
        return (d is not None) and (dirv != DIRV[d])

    def _trap(self, amt):
        self.dmg += min(self.hp, amt) if self.hp > 0 else 0
        self.hp -= amt

    def _can_enter(self, x, y, dirv, kind):
        if not (0 <= x < GRID_W and 0 <= y < GRID_H):
            return False
        if self.high_wall(x, y):
            return False
        o = self.occ[y][x]
        if o == "BOX" or o == "TNT":
            return False
        if kind == "BOX":
            if (x, y) == (self.hx, self.hy):
                return False
            if self.ter[y][x] in ("K1", "K2", "V"):
                return False
        if self.blocks_oneway(x, y, dirv):
            return False
        return True

    def _portal_other(self, tile):
        other = PORTAL_PAIR[tile]
        for y in range(GRID_H):
            for x in range(GRID_W):
                if self.ter[y][x] == other:
                    return (x, y)
        return None

    def _move_entity(self, kind, p0, p1, dirv):
        steps = 0
        portal_count = 0
        suppress = False
        stop_momentum = False
        while True:
            steps += 1
            if self.ter[p0[1]][p0[0]] == "CRACK":
                self.ter[p0[1]][p0[0]] = "PIT"
            if kind == "BOX":
                self.occ[p0[1]][p0[0]] = None
                self.occ[p1[1]][p1[0]] = "BOX"
            else:
                self.hx, self.hy = p1
                self.exposed.add(p1)
            t1 = self.ter[p1[1]][p1[0]]
            if kind == "BOX":
                if t1 == "PIT":
                    self.occ[p1[1]][p1[0]] = None
                    self.ter[p1[1]][p1[0]] = "EMPTY"
                    stop_momentum = True
                elif t1 == "MIMIC":
                    self.ter[p1[1]][p1[0]] = "EMPTY"
                elif t1 == "SWITCH":
                    self.gates = not self.gates
            else:
                if t1 == "PIT":
                    self._trap(100)
                elif t1 == "MIMIC":
                    self._trap(45)
                    self.ter[p1[1]][p1[0]] = "EMPTY"
                    stop_momentum = True
                elif t1 == "HEAL":
                    self.hp = min(100, self.hp + 30)
                    self.ter[p1[1]][p1[0]] = "EMPTY"
                elif t1 == "SWITCH":
                    self.gates = not self.gates
            if kind != "BOX" and self.hp <= 0:
                self.status = "DEAD"
                return True
            if kind != "BOX":
                if t1 == "K1":
                    self.k1 = True
                    self.ter[p1[1]][p1[0]] = "EMPTY"
                elif t1 == "K2":
                    self.k2 = True
                    self.ter[p1[1]][p1[0]] = "EMPTY"
                elif t1 == "V" and self.k1 and self.k2 and self.hp > 0:
                    self.status = "CLEARED"
                    return True
            if steps >= 32 or stop_momentum:
                break
            t1 = self.ter[p1[1]][p1[0]]
            nxt = None
            newdir = dirv
            if t1 == "ICE":
                nx, ny = p1[0] + dirv[0], p1[1] + dirv[1]
                if self._can_enter(nx, ny, dirv, kind):
                    nxt = (nx, ny)
            elif t1 in MIRROR_FOLD:
                newdir = DIRV[MIRROR_FOLD[t1][DIR_OF[dirv]]]
                nx, ny = p1[0] + newdir[0], p1[1] + newdir[1]
                if self._can_enter(nx, ny, newdir, kind):
                    nxt = (nx, ny)
            elif t1 in SPRING_DIR:
                sd = DIRV[SPRING_DIR[t1]]
                newdir = sd
                land = (p1[0] + 3 * sd[0], p1[1] + 3 * sd[1])
                if not (0 <= land[0] < GRID_W and 0 <= land[1] < GRID_H):
                    land = None
                for k in (1, 2, 3):
                    px, py = p1[0] + k * sd[0], p1[1] + k * sd[1]
                    blocked = (not (0 <= px < GRID_W and 0 <= py < GRID_H)) or \
                        self.high_wall(px, py) or self.occ[py][px] in ("BOX", "TNT") or \
                        self.blocks_oneway(px, py, sd)
                    if kind == "BOX" and 0 <= px < GRID_W and 0 <= py < GRID_H:
                        if (px, py) == (self.hx, self.hy) or \
                                self.ter[py][px] in ("K1", "K2", "V"):
                            blocked = True
                    if blocked:
                        if kind == "BOX" and 0 <= px < GRID_W and 0 <= py < GRID_H and \
                                self.occ[py][px] == "TNT":
                            self.tnt_armed.add((px, py))
                        land = (p1[0] + (k - 1) * sd[0], p1[1] + (k - 1) * sd[1]) if k >= 2 else None
                        break
                nxt = land
            elif t1 in PORTALS and not suppress:
                pp = self._portal_other(t1)
                ok = pp is not None and self.occ[pp[1]][pp[0]] is None
                if kind == "BOX" and ok and pp == (self.hx, self.hy):
                    ok = False
                if ok:
                    portal_count += 1
                    nxt = pp
                    suppress = True
            elif t1 in PORTALS and suppress:
                suppress = False
                if portal_count < 2:
                    fx, fy = p1[0] + dirv[0], p1[1] + dirv[1]
                    if self._can_enter(fx, fy, dirv, kind):
                        nxt = (fx, fy)
            if nxt is None:
                break
            p0, p1 = p1, nxt
            dirv = newdir
        return False

    def _explode(self, sources):
        q, seen = [], set()
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
                    if not (0 <= cx < GRID_W and 0 <= cy < GRID_H) or (cx, cy) in seen:
                        continue
                    if self.occ[cy][cx] == "TNT" or (cx, cy) in self.bmap:
                        seen.add((cx, cy))
                        q.append((cx, cy))
        a = b = 0
        for (sx, sy) in all_src:
            if abs(sx - self.hx) <= 1 and abs(sy - self.hy) <= 1:
                if self.occ[sy][sx] == "TNT":
                    a += 60
                elif (sx, sy) in self.bmap:
                    b += 50
        if a + b > 0:
            self.dmg += min(self.hp, a + b) * (a / float(a + b))
            self.hp -= (a + b)
        for (sx, sy) in all_src:
            if self.occ[sy][sx] == "TNT":
                self.occ[sy][sx] = None
            self.bmap.pop((sx, sy), None)
        union = set()
        for (sx, sy) in all_src:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cx, cy = sx + dx, sy + dy
                    if 0 <= cx < GRID_W and 0 <= cy < GRID_H:
                        union.add((cx, cy))
        for (cx, cy) in union:
            if self.occ[cy][cx] == "BOX":
                self.occ[cy][cx] = None
            t = self.ter[cy][cx]
            if t in BLAST_IMMUNE:
                continue
            if t == "CRACK":
                self.ter[cy][cx] = "PIT"
            elif t in BLAST_WIPE:
                self.ter[cy][cx] = "EMPTY"
        for (cx, cy) in union:
            if self.occ[cy][cx] == "BOX" and self.ter[cy][cx] == "PIT":
                self.occ[cy][cx] = None
                self.ter[cy][cx] = "EMPTY"
        if self.hp > 0 and self.ter[self.hy][self.hx] == "PIT":
            self._trap(100)
        if self.hp <= 0:
            self.status = "DEAD"

    def _rays(self, red, blue):
        out, armed = [], set()
        for y in range(GRID_H):
            for x in range(GRID_W):
                t = self.ter[y][x]
                if t in LASER_TILES:
                    if not red:
                        continue
                    d = LASER_TILES[t]
                elif t in LASER2_TILES:
                    if not blue:
                        continue
                    d = LASER2_TILES[t]
                else:
                    continue
                dx, dy = DIRV[d]
                cells = []
                for step in range(1, 11):
                    nx, ny = x + dx * step, y + dy * step
                    if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                        break
                    if self.high_wall(nx, ny) or self.occ[ny][nx] == "BOX":
                        break
                    if self.occ[ny][nx] == "TNT":
                        armed.add((nx, ny))
                        break
                    cells.append((nx, ny))
                out.append(cells)
        return out, armed

    def _throw(self, sx, sy, dirv):
        rng = 6
        while rng > 0:
            nx, ny = sx + dirv[0], sy + dirv[1]
            if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                return
            rng -= 1
            sx, sy = nx, ny
            if self.high_wall(nx, ny) or self.occ[ny][nx] == "BOX":
                return
            if self.occ[ny][nx] == "TNT":
                self.tnt_armed.add((nx, ny))
                return
            t = self.ter[ny][nx]
            if t == "SWITCH":
                self.gates = not self.gates
                return
            if t == "MIMIC":
                self.ter[ny][nx] = "EMPTY"
                return
            if t in MIRROR_FOLD:
                dirv = DIRV[MIRROR_FOLD[t][DIR_OF[dirv]]]
                continue
        t = self.ter[sy][sx]
        if t != "ICE" and t not in MIRROR_FOLD:
            return
        for _ in range(32):
            nx, ny = sx + dirv[0], sy + dirv[1]
            if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                return
            sx, sy = nx, ny
            if self.high_wall(nx, ny) or self.occ[ny][nx] == "BOX":
                return
            if self.occ[ny][nx] == "TNT":
                self.tnt_armed.add((nx, ny))
                return
            t = self.ter[ny][nx]
            if t == "SWITCH":
                self.gates = not self.gates
                return
            if t == "MIMIC":
                self.ter[ny][nx] = "EMPTY"
                return
            if t in MIRROR_FOLD:
                dirv = DIRV[MIRROR_FOLD[t][DIR_OF[dirv]]]
                continue
            if t == "ICE":
                continue
            return

    def apply(self, action):
        if self.status is not None:
            return self.status
        self.turn += 1
        self.exposed = {(self.hx, self.hy)}
        self.tnt_armed = set()
        if action not in VALID_ACTIONS:
            action = "WAIT"
        hx, hy = self.hx, self.hy
        if action == "BOMB":
            if self.bombs > 0 and (hx, hy) not in self.bmap:
                self.bombs -= 1
                self.bmap[(hx, hy)] = 3
        elif action.startswith("MOVE_"):
            d = action[5]
            dx, dy = DIRV[d]
            p1 = (hx + dx, hy + dy)
            if not (0 <= p1[0] < GRID_W and 0 <= p1[1] < GRID_H):
                pass
            elif self.high_wall(p1[0], p1[1]) or self.occ[p1[1]][p1[0]] == "TNT":
                pass
            elif self.occ[p1[1]][p1[0]] == "BOX":
                if not self.blocks_oneway(p1[0], p1[1], (dx, dy)):
                    p2 = (hx + 2 * dx, hy + 2 * dy)
                    if self._can_enter(p2[0], p2[1], (dx, dy), "BOX"):
                        self._move_entity("BOX", p1, p2, (dx, dy))
                        if self.status is None and \
                                self._can_enter(p1[0], p1[1], (dx, dy), "HERO"):
                            self._move_entity("HERO", (hx, hy), p1, (dx, dy))
            elif not self.blocks_oneway(p1[0], p1[1], (dx, dy)):
                self._move_entity("HERO", (hx, hy), p1, (dx, dy))
        elif action.startswith("JUMP_"):
            if self.jumps > 0:
                self.jumps -= 1
                d = action[5]
                dx, dy = DIRV[d]
                p1 = (hx + dx, hy + dy)
                p2 = (hx + 2 * dx, hy + 2 * dy)
                bad = (not (0 <= p1[0] < GRID_W and 0 <= p1[1] < GRID_H)) or \
                    self.high_wall(p1[0], p1[1]) or self.blocks_oneway(p1[0], p1[1], (dx, dy))
                if not bad:
                    if (not (0 <= p2[0] < GRID_W and 0 <= p2[1] < GRID_H)) or \
                            self.high_wall(p2[0], p2[1]) or \
                            self.occ[p2[1]][p2[0]] in ("BOX", "TNT") or \
                            self.blocks_oneway(p2[0], p2[1], (dx, dy)):
                        bad = True
                if not bad:
                    self._move_entity("HERO", (hx, hy), p2, (dx, dy))
        elif action.startswith("THROW_"):
            if self.throws > 0:
                self.throws -= 1
                self._throw(hx, hy, DIRV[action[6]])
        if self.status is None:
            for k in list(self.bmap.keys()):
                self.bmap[k] -= 1
            srcs = [p for p, t in self.bmap.items() if t <= 0] + list(self.tnt_armed)
            if srcs:
                self._explode(srcs)
        if self.status is None:
            red = (self.turn % 3 == 0)
            blue = (self.turn % 4 == 0)
            if red or blue:
                rays, armed = self._rays(red, blue)
                m = 0
                for cells in rays:
                    for c in cells:
                        if c in self.exposed:
                            m += 1
                            break
                if m:
                    self.dmg += min(self.hp, 50 * m)
                    self.hp -= 50 * m
                    if self.hp <= 0:
                        self.status = "DEAD"
                if self.status is None and armed:
                    self._explode(list(armed))
        if self.status is None and self.turn > MAX_TURNS:
            self.status = "TIMEOUT"
        return self.status


# =============================================================================
# 二、静态地图解析 + 时间展开求路 + 推箱/引爆子规划
# =============================================================================

def _world_from_state(state):
    """从 FULL 观测快照还原真值地形与实体（CHEST 用 clues 反解 HEAL/MIMIC）。"""
    ter = []
    occ = []
    clues = state.get("clues") or [[False] * GRID_W for _ in range(GRID_H)]
    for y in range(GRID_H):
        trow = state["terrain"][y]
        orow = state["occupant"][y]
        tr = []
        for x in range(GRID_W):
            t = trow[x]
            if t == "CHEST":
                t = "MIMIC" if clues[y][x] else "HEAL"
            tr.append(t)
        ter.append(tr)
        occ.append([orow[x] for x in range(GRID_W)])
    h = state["hero"]
    hero = (int(h["x"]), int(h["y"]), int(h["hp"]),
            bool(h["keys"][0]), bool(h["keys"][1]),
            int(h["jumps"]), int(h["throws"]), int(h["bombs"]))
    return ter, occ, hero, bool(state["gates_flipped"]), int(state["turn"])


class _Plan:
    """规划上下文：一份可增量推进的 _Sim + 计算好的危险表 / 加速结构。"""

    def __init__(self, sim, targets):
        self.sim = sim
        self.targets = targets
        self.cache = {}
        self.cannons = []
        for y in range(GRID_H):
            for x in range(GRID_W):
                t = sim.ter[y][x]
                if t in LASER_TILES:
                    self.cannons.append((x, y, LASER_TILES[t], 3))
                elif t in LASER2_TILES:
                    self.cannons.append((x, y, LASER2_TILES[t], 4))
        self.haz = self._hazard()

    def _hazard(self):
        """haz[phase][cell] = 该相位下覆盖此格的激光门数（0..2+）。"""
        haz = [[0] * CELLS for _ in range(12)]
        active = self.sim.plates_active()
        g = self.sim.gates
        for (cx, cy, d, period) in self.cannons:
            dx, dy = DIRV[d]
            phases = [p for p in range(1, 12) if (p % 3 == 0 if period == 3 else p % 4 == 0)]
            phases.append(12)
            cells = []
            for step in range(1, 11):
                nx, ny = cx + dx * step, cy + dy * step
                if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                    break
                t = self.sim.ter[ny][nx]
                if t in HIGH_WALL or self.sim.occ[ny][nx] == "BOX":
                    break
                if t == "R_GATE" and not g:
                    break
                if t == "B_GATE" and g:
                    break
                if t == "P_GATE" and not active:
                    break
                if self.sim.occ[ny][nx] == "TNT":
                    break
                cells.append(ny * GRID_W + nx)
            for p in phases:
                pp = 0 if p == 12 else p
                for c in cells:
                    haz[pp][c] += 1
        return haz

    def moved(self, cell, d, gates=None):
        key = (cell, d, self.sim.gates if gates is None else gates)
        r = self.cache.get(key)
        if r is None:
            r = _static_move(self.sim.ter, self.sim.occ, key[2], cell % GRID_W,
                             cell // GRID_W, d, self.cannons)
            self.cache[key] = r
        return r


def _static_move(ter, occ, gates, x, y, d, cannons):
    """静态地形上的 MOVE 仿真（不解引用真实地图），返回 (end_cell, dmg, flip, exposed)。"""
    dx, dy = DIRV[d]
    p0 = (x, y)
    p1 = (x + dx, y + dy)

    def hw(nx, ny):
        if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
            return True
        t = ter[ny][nx]
        if t in HIGH_WALL:
            return True
        if t == "R_GATE":
            return not gates
        if t == "B_GATE":
            return gates
        return False

    def bo(nx, ny, dv):
        dd = ONEWAY_DIR.get(ter[ny][nx])
        return (dd is not None) and (dv != DIRV[dd])

    if not (0 <= p1[0] < GRID_W and 0 <= p1[1] < GRID_H):
        return y * GRID_W + x, 0, False, ()
    if hw(p1[0], p1[1]) or occ[p1[1]][p1[0]] in ("TNT", "BOX"):
        return y * GRID_W + x, 0, False, ()
    if bo(p1[0], p1[1], (dx, dy)):
        return y * GRID_W + x, 0, False, ()
    cur = p1
    dmg = 0
    flip = False
    dv = (dx, dy)
    steps = 0
    stop = False
    ex = [p1]
    while True:
        steps += 1
        t = ter[cur[1]][cur[0]]
        if t == "PIT":
            dmg += 100
            stop = True
        elif t == "MIMIC":
            dmg += 45
            stop = True
        elif t == "HEAL":
            dmg -= 30
        elif t == "SWITCH":
            flip = not flip
        if steps >= 32 or stop:
            break
        nxt = None
        nd = dv
        if t == "ICE":
            nx, ny = cur[0] + dv[0], cur[1] + dv[1]
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H and not hw(nx, ny) and \
                    occ[ny][nx] not in ("BOX", "TNT") and not bo(nx, ny, dv):
                nxt = (nx, ny)
        elif t in MIRROR_FOLD:
            nd = DIRV[MIRROR_FOLD[t][DIR_OF[dv]]]
            nx, ny = cur[0] + nd[0], cur[1] + nd[1]
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H and not hw(nx, ny) and \
                    occ[ny][nx] not in ("BOX", "TNT") and not bo(nx, ny, nd):
                nxt = (nx, ny)
        elif t in SPRING_DIR:
            sd = DIRV[SPRING_DIR[t]]
            nd = sd
            land = (cur[0] + 3 * sd[0], cur[1] + 3 * sd[1])
            if not (0 <= land[0] < GRID_W and 0 <= land[1] < GRID_H):
                land = None
            for k in (1, 2, 3):
                px, py = cur[0] + k * sd[0], cur[1] + k * sd[1]
                blocked = (not (0 <= px < GRID_W and 0 <= py < GRID_H)) or hw(px, py) or \
                    occ[py][px] in ("BOX", "TNT") or bo(px, py, sd)
                if blocked:
                    land = (cur[0] + (k - 1) * sd[0], cur[1] + (k - 1) * sd[1]) if k >= 2 else None
                    break
            nxt = land
        if nxt is None:
            break
        cur = nxt
        dv = nd
        ex.append(cur)
    return cur[1] * GRID_W + cur[0], dmg, flip, tuple(ex)


def _dijkstra(plan, goal_cells, deadline, weight_dmg=4.0, node_cap=60000,
              allow_wait=True):
    """时间展开 A*：状态 (cell, gates, phase)，代价 = 回合数 + 权重×伤害。"""
    sim = plan.sim
    start = sim.hy * GRID_W + sim.hx
    goal_set = set(goal_cells)
    if start in goal_set:
        return []
    if not goal_set:
        return None
    phase0 = sim.turn % 12
    dist = {(start, sim.gates, phase0): 0.0}
    prev = {}
    h0 = min(abs(start % GRID_W - g % GRID_W) + abs(start // GRID_W - g // GRID_W)
             for g in goal_set)
    pq = [(h0, 0.0, start, sim.gates, phase0)]
    expanded = 0
    while pq:
        f, d, cell, gates, phase = heapq.heappop(pq)
        st = (cell, gates, phase)
        if dist.get(st, 1e18) < d - 1e-9:
            continue
        if cell in goal_set:
            acts = []
            while st in prev:
                st, act = prev[st]
                acts.append(act)
            acts.reverse()
            return acts
        expanded += 1
        if expanded > node_cap:
            break
        if (expanded & 511) == 0 and time.monotonic() > deadline:
            break
        nphase = (phase + 1) % 12
        for dk in DIR_KEYS:
            end, dmg, flip, ex = plan.moved(cell, dk, gates)
            if end == cell and dmg == 0 and not flip:
                continue
            laser = 0
            if nphase % 3 == 0 or nphase % 4 == 0:
                hz = 0
                for (exx, exy) in ex:
                    v = plan.haz[nphase][exy * GRID_W + exx]
                    if v > hz:
                        hz = v
                laser = hz
            cost = d + 1.0 + weight_dmg * (dmg + 50 * laser)
            ngates = (not gates) if flip else gates
            nst = (end, ngates, nphase)
            if cost < dist.get(nst, 1e18) - 1e-9:
                dist[nst] = cost
                prev[nst] = (st, MOVE_ACT[dk])
                hh = min(abs(end % GRID_W - g % GRID_W) + abs(end // GRID_W - g // GRID_W)
                         for g in goal_set)
                heapq.heappush(pq, (cost + hh, cost, end, ngates, nphase))
        if allow_wait:
            laser = 0
            if nphase % 3 == 0 or nphase % 4 == 0:
                laser = plan.haz[nphase][cell]
            if laser == 0 or sim.hp > 100:
                cost = d + 1.0 + weight_dmg * 50 * laser
                nst = (cell, gates, nphase)
                if cost < dist.get(nst, 1e18) - 1e-9:
                    dist[nst] = cost
                    prev[nst] = ((cell, gates, phase), "WAIT")
                    heapq.heappush(pq, (cost, cost, cell, gates, nphase))
    return None


def _bfs_cells(plan, start_cell, blocked_extra=()):
    """忽略相位的连通距离场（推箱子规划用近似代价）。"""
    sim = plan.sim
    dist = {start_cell: 0}
    dq = [start_cell]
    head = 0
    blocked = set(blocked_extra)
    while head < len(dq):
        c = dq[head]
        head += 1
        d = dist[c]
        for dk in DIR_KEYS:
            end, dmg, flip, ex = plan.moved(c, dk)
            if flip or dmg > 0 or end == c or end in blocked:
                continue
            if end in dist:
                continue
            dist[end] = d + 1
            dq.append(end)
    return dist


def _box_after_push(sim, box_cell, d):
    """箱子被推动一次后的落点（含冰/镜/弹簧动量链）；None 表示推不动或箱子消失。"""
    bx, by = box_cell % GRID_W, box_cell // GRID_W
    dx, dy = DIRV[d]
    p1 = (bx + dx, by + dy)
    if not (0 <= p1[0] < GRID_W and 0 <= p1[1] < GRID_H):
        return None
    if not sim._can_enter(p1[0], p1[1], (dx, dy), "BOX"):
        return None
    s = sim.clone()
    s._move_entity("BOX", (bx, by), p1, (dx, dy))
    found = None
    for y in range(GRID_H):
        for x in range(GRID_W):
            if s.occ[y][x] == "BOX":
                found = y * GRID_W + x
                break
        if found is not None:
            break
    return found


def _push_plan(plan, box_start, target_cells, deadline, max_pushes=14):
    """Sokoban 推箱子规划：返回 [(box_cell, dir), ...] 推步序列。"""
    sim = plan.sim
    hero_cell = sim.hy * GRID_W + sim.hx
    targets = set(target_cells)
    # 状态：box_cell；锚点（推完后人站在箱原位）
    best = {box_start: (0.0, None, None, hero_cell)}
    pq = [(0.0, box_start, hero_cell)]
    seen_expand = 0
    result = None
    while pq:
        cost, bcell, anchor = heapq.heappop(pq)
        if bcell in targets:
            result = bcell
            break
        cur = best.get(bcell)
        if cur is not None and cost > cur[0] + 1e-9:
            continue
        seen_expand += 1
        if seen_expand > 4000 or time.monotonic() > deadline:
            break
        dist = _bfs_cells(plan, anchor, blocked_extra=(bcell,))
        bx, by = bcell % GRID_W, bcell // GRID_W
        for dk in DIR_KEYS:
            dx, dy = DIRV[dk]
            pc = (bx - dx) * 1 + (by - dy) * GRID_W
            pcx, pcy = bx - dx, by - dy
            if not (0 <= pcx < GRID_W and 0 <= pcy < GRID_H):
                continue
            pc = pcy * GRID_W + pcx
            if pc not in dist:
                continue
            nb = _box_after_push(sim, bcell, dk)
            if nb is None or nb == bcell:
                continue
            if plan.sim.occ[nb // GRID_W][nb % GRID_W] == "TNT":
                continue
            ncost = cost + dist[pc] + 1
            if nb in best and best[nb][0] <= ncost:
                continue
            best[nb] = (ncost, bcell, dk, bcell)
            heapq.heappush(pq, (ncost, nb, bcell))
    if result is None:
        return None
    # 回溯
    seq = []
    cur = result
    while best.get(cur) and best[cur][1] is not None:
        _c, prevb, dk, _a = best[cur]
        seq.append((prevb, dk))
        cur = prevb
    seq.reverse()
    return seq


def _execute_pushes(plan, seq, deadline):
    """把推步序列展开成动作列表（每推一步前先用时间展开求路走到推箱位）。"""
    acts = []
    for (bcell, dk) in seq:
        sim = plan.sim
        dx, dy = DIRV[dk]
        pcx = bcell % GRID_W - dx
        pcy = bcell // GRID_W - dy
        pc = pcy * GRID_W + pcx
        walk = _dijkstra(plan, [pc], deadline, weight_dmg=8.0, node_cap=30000)
        if walk is None:
            return None
        for a in walk:
            sim.apply(a)
            if sim.status is not None:
                return None
        acts.extend(walk)
        before = bcell
        sim.apply(MOVE_ACT[dk])
        acts.append(MOVE_ACT[dk])
        if sim.status is not None:
            return None
        nxt = None
        for y in range(GRID_H):
            for x in range(GRID_W):
                if sim.occ[y][x] == "BOX" and y * GRID_W + x != before:
                    nxt = y * GRID_W + x
        if nxt is None:
            return None
        plan.invalidate()
    return acts
