"""
《阴间地牢：金库攻防战》下半场 FULL 全图明牌攻守双重构提交 (v2.2)
build_dungeon(): 多箱压板 + 单向门 + 双频激光逻辑迷宫，内置全量合规自检与作者自证。
decide_action(): 全图明牌全局状态空间加权 A*（相位 x 钥匙 x 门态 x 箱位 x 地形差分），
                 Turn1 全局搜索预算，计划承诺执行，失配即时重规划，永不抛异常。
仅使用纯计算标准库；全文件无任何双下划线名称/属性、无 I/O、无网络、无反射。
"""

import heapq
import math
import time
from collections import deque

GRID_WIDTH = 40
GRID_HEIGHT = 26
NCELL = GRID_WIDTH * GRID_HEIGHT
MAX_BUDGET = 3000
MAX_TURNS = 240
MAX_AUTHOR_STEPS = 200
SPAWN_POS = (2, 13)

VALID_ACTIONS = (
    "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R",
    "WAIT",
    "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
    "THROW_U", "THROW_D", "THROW_L", "THROW_R",
    "BOMB",
)

DIRS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
DIR_NAMES = ("U", "D", "L", "R")
DOFF = {"U": -GRID_WIDTH, "D": GRID_WIDTH, "L": -1, "R": 1}

MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}

PORTAL_PAIR = {
    "PORTAL_1A": "PORTAL_1B", "PORTAL_1B": "PORTAL_1A",
    "PORTAL_2A": "PORTAL_2B", "PORTAL_2B": "PORTAL_2A",
}

TILE_COSTS = {
    "EMPTY": 0, "K1": 0, "K2": 0, "V": 0,
    "W": 5, "T_W": 25, "ICE": 10,
    "MIRROR_NE": 25, "MIRROR_SE": 25, "MIRROR_SW": 25, "MIRROR_NW": 25,
    "SPRING_U": 35, "SPRING_D": 35, "SPRING_L": 35, "SPRING_R": 35,
    "PIT": 40,
    "LASER_U": 75, "LASER_D": 75, "LASER_L": 75, "LASER_R": 75,
    "LASER2_U": 90, "LASER2_D": 90, "LASER2_L": 90, "LASER2_R": 90,
    "CRACK": 20, "SWITCH": 30, "R_GATE": 20, "B_GATE": 20,
    "PLATE": 45, "P_GATE": 30,
    "ONEWAY_U": 30, "ONEWAY_D": 30, "ONEWAY_L": 30, "ONEWAY_R": 30,
    "TNT": 40, "BOX": 30, "HEAL": 30, "MIMIC": 60,
    "PORTAL_1A": 40, "PORTAL_1B": 40, "PORTAL_2A": 40, "PORTAL_2B": 40,
}

STATIC_HIGH = {"W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R",
               "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R"}
MOMENTUM_TILES = {"ICE", "MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW",
                  "SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R",
                  "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B"}
EXPLODE_DESTROY = {"W", "ICE", "MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW",
                   "SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R",
                   "LASER_U", "LASER_D", "LASER_L", "LASER_R",
                   "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R",
                   "SWITCH", "R_GATE", "B_GATE", "HEAL", "MIMIC"}
EXPLODE_IMMUNE = {"T_W", "K1", "K2", "V", "PIT", "PLATE", "P_GATE",
                  "ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R",
                  "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B"}


def in_bounds(x, y):
    return 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT


def idx_of(x, y):
    return y * GRID_WIDTH + x


def laser_info(tile):
    if tile[:7] == "LASER2_":
        return tile[7:], 4
    if tile[:6] == "LASER_":
        return tile[6:], 3
    return None, 0


def is_high_wall(tile, gates, plates):
    if tile in STATIC_HIGH:
        return True
    if tile == "R_GATE":
        return not gates
    if tile == "B_GATE":
        return gates
    if tile == "P_GATE":
        return not plates
    return False


def oneway_block(tile, d):
    return tile[:7] == "ONEWAY_" and tile[7:] != d


def is_spawn_zone(x, y):
    return 1 <= x <= 3 and 12 <= y <= 14


# ==============================================================================
# v2.2 完整确定性物理引擎（魔王自证 / 勇者全局搜索 / 本地裁判共用）
# 扁平数组 + 增量差分追踪，支持高速克隆与状态键导出。
# ==============================================================================
class Eng:
    def setup(self, grid, hero=None, gates=False, turn=0):
        self.base_ter = ["EMPTY"] * NCELL
        self.base_occ = [None] * NCELL
        self.ter = ["EMPTY"] * NCELL
        self.occ = [None] * NCELL
        self.terdiff = {}
        self.box_set = set()
        self.tnt_set = set()
        self.plate_idx = []
        self.cannons = []
        self.portal_pos = {}
        self.mimic_clue = {}
        self.clues = [False] * NCELL
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                t = grid[y][x]
                i = y * GRID_WIDTH + x
                if t in ("BOX", "TNT"):
                    self.base_ter[i] = "EMPTY"
                    self.base_occ[i] = t
                    if t == "BOX":
                        self.box_set.add(i)
                    else:
                        self.tnt_set.add(i)
                else:
                    self.base_ter[i] = t
                if t == "PLATE":
                    self.plate_idx.append(i)
                d, p = laser_info(t)
                if d is not None:
                    self.cannons.append((i, d, p))
                if t[:7] == "PORTAL_":
                    self.portal_pos[t] = i
        self.ter = self.base_ter[:]
        self.occ = self.base_occ[:]
        self._bind_clues(grid)
        if hero is None:
            hero = {"x": SPAWN_POS[0], "y": SPAWN_POS[1], "hp": 100,
                    "keys": [False, False], "jumps": 3, "throws": 3, "bombs": 2}
        self.hx = hero["x"]
        self.hy = hero["y"]
        self.hp = hero["hp"]
        ks = hero.get("keys", [False, False])
        self.kmask = (1 if ks[0] else 0) | (2 if ks[1] else 0)
        self.jumps = hero.get("jumps", 3)
        self.throws = hero.get("throws", 3)
        self.bombs_left = hero.get("bombs", 2)
        self.gates = gates
        self.turn = turn
        self.status = "ALIVE"
        self.bombs = []
        self.exposed = []
        self.tnt_armed = set()
        self.trap_damage = 0
        self._plates()
        return self

    def setup_flat(self, base_ter, base_occ, meta):
        self.base_ter = base_ter
        self.base_occ = base_occ
        self.ter = base_ter[:]
        self.occ = base_occ[:]
        self.terdiff = {}
        self.box_set = set(meta["boxes"])
        self.tnt_set = set(meta["tnts"])
        self.plate_idx = meta["plates"]
        self.cannons = meta["cannons"]
        self.portal_pos = meta["portals"]
        self.mimic_clue = {}
        self.clues = [False] * NCELL
        self.hx = SPAWN_POS[0]
        self.hy = SPAWN_POS[1]
        self.hp = 100
        self.kmask = 0
        self.jumps = 3
        self.throws = 3
        self.bombs_left = 2
        self.gates = False
        self.turn = 0
        self.status = "ALIVE"
        self.bombs = []
        self.exposed = []
        self.tnt_armed = set()
        self.trap_damage = 0
        self._plates()
        return self

    def _bind_clues(self, grid):
        mimics = []
        chests = set()
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                t = grid[y][x]
                if t == "MIMIC":
                    mimics.append((x, y))
                if t in ("MIMIC", "HEAL"):
                    chests.add((x, y))
        for (mx, my) in mimics:
            for (dx, dy) in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = mx + dx, my + dy
                if not in_bounds(nx, ny):
                    continue
                i = ny * GRID_WIDTH + nx
                if self.ter[i] != "EMPTY" or self.occ[i] is not None:
                    continue
                if is_spawn_zone(nx, ny) or self.clues[i]:
                    continue
                ok = True
                for (ax, ay) in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    cx, cy = nx + ax, ny + ay
                    if (cx, cy) in chests and (cx, cy) != (mx, my):
                        ok = False
                        break
                if ok:
                    self.clues[i] = True
                    self.mimic_clue[(mx, my)] = (nx, ny)
                    break

    def clone(self):
        e = Eng()
        e.base_ter = self.base_ter
        e.base_occ = self.base_occ
        e.ter = self.ter[:]
        e.occ = self.occ[:]
        e.terdiff = dict(self.terdiff)
        e.box_set = set(self.box_set)
        e.tnt_set = set(self.tnt_set)
        e.plate_idx = self.plate_idx
        e.cannons = self.cannons
        e.portal_pos = self.portal_pos
        e.mimic_clue = self.mimic_clue
        e.clues = self.clues
        e.hx = self.hx; e.hy = self.hy; e.hp = self.hp
        e.kmask = self.kmask; e.jumps = self.jumps
        e.throws = self.throws; e.bombs_left = self.bombs_left
        e.gates = self.gates; e.turn = self.turn; e.status = self.status
        e.bombs = [b[:] for b in self.bombs]
        e.exposed = self.exposed[:]
        e.tnt_armed = set(self.tnt_armed)
        e.trap_damage = self.trap_damage
        e.plates = self.plates
        return e

    def load(self, st):
        (hx, hy, hp, kmask, gates, turn, jumps, throws, bombs_left,
         bombs_t, boxes_t, tnts_t, terdiff_t) = st
        ter = self.base_ter[:]
        for i, t in terdiff_t:
            ter[i] = t
        occ = [None] * NCELL
        for i in boxes_t:
            occ[i] = "BOX"
        for i in tnts_t:
            occ[i] = "TNT"
        self.ter = ter
        self.occ = occ
        self.terdiff = dict(terdiff_t)
        self.box_set = set(boxes_t)
        self.tnt_set = set(tnts_t)
        self.hx = hx; self.hy = hy; self.hp = hp
        self.kmask = kmask; self.gates = gates; self.turn = turn
        self.jumps = jumps; self.throws = throws; self.bombs_left = bombs_left
        self.bombs = [[i, t] for (i, t) in bombs_t]
        self.status = "ALIVE"
        self.exposed = []
        self.tnt_armed = set()
        self._plates()

    def state(self):
        return (self.hx, self.hy, self.hp, self.kmask, self.gates, self.turn,
                self.jumps, self.throws, self.bombs_left,
                tuple(sorted((i, t) for (i, t) in self.bombs)),
                tuple(sorted(self.box_set)), tuple(sorted(self.tnt_set)),
                tuple(sorted(self.terdiff.items())))

    def key(self):
        return (self.hx, self.hy, self.kmask, self.gates, self.turn % 12,
                self.jumps, self.throws, self.bombs_left,
                tuple(sorted((i, t) for (i, t) in self.bombs)),
                tuple(sorted(self.box_set)), tuple(sorted(self.tnt_set)),
                tuple(sorted(self.terdiff.items())))

    def _set_ter(self, i, v):
        self.ter[i] = v
        if v == self.base_ter[i]:
            self.terdiff.pop(i, None)
        else:
            self.terdiff[i] = v

    def _plates(self):
        if self.plate_idx:
            occ = self.occ
            self.plates = all(occ[i] == "BOX" for i in self.plate_idx)
        else:
            self.plates = False

    def high(self, i):
        return is_high_wall(self.ter[i], self.gates, self.plates)

    def can_enter(self, i, entity, d):
        x = i % GRID_WIDTH
        y = i // GRID_WIDTH
        if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT):
            return False
        if self.high(i):
            return False
        o = self.occ[i]
        if o == "BOX" or o == "TNT":
            return False
        if oneway_block(self.ter[i], d):
            return False
        if entity == "BOX":
            if i == self.hy * GRID_WIDTH + self.hx:
                return False
            if self.ter[i] in ("K1", "K2", "V"):
                return False
        return True

    def _clear_mimic(self, i):
        self._set_ter(i, "EMPTY")
        x = i % GRID_WIDTH
        y = i // GRID_WIDTH
        c = self.mimic_clue.pop((x, y), None)
        if c is not None:
            self.clues[c[1] * GRID_WIDTH + c[0]] = False

    def _damage(self, amount):
        self.trap_damage += min(max(0, self.hp), amount)
        self.hp -= amount
        if self.hp <= 0:
            self.status = "DEAD"

    # ---- 原子位移（含动量、单向门、压板实时派生）----
    def _atomic(self, entity, frm, to, d, steps, portals, suppress):
        steps += 1
        if self.ter[frm] == "CRACK":
            self._set_ter(frm, "PIT")
        stop = False
        if entity == "BOX":
            self.occ[frm] = None
            self.occ[to] = "BOX"
            self.box_set.discard(frm)
            self.box_set.add(to)
            self._plates()
            tt = self.ter[to]
            if tt == "PIT":
                self.occ[to] = None
                self.box_set.discard(to)
                self._set_ter(to, "EMPTY")
                self._plates()
                return
            if tt == "MIMIC":
                self._clear_mimic(to)
            elif tt == "SWITCH":
                self.gates = not self.gates
        else:
            self.hx = to % GRID_WIDTH
            self.hy = to // GRID_WIDTH
            self.exposed.append(to)
            tt = self.ter[to]
            if tt == "PIT":
                self._damage(100)
                return
            elif tt == "MIMIC":
                self._damage(45)
                self._clear_mimic(to)
                stop = True
                if self.status != "ALIVE":
                    return
            elif tt == "HEAL":
                self.hp = min(100, self.hp + 30)
                self._set_ter(to, "EMPTY")
            elif tt == "SWITCH":
                self.gates = not self.gates
            if tt == "K1":
                self.kmask |= 1
                self._set_ter(to, "EMPTY")
            elif tt == "K2":
                self.kmask |= 2
                self._set_ter(to, "EMPTY")
            elif tt == "V" and self.kmask == 3 and self.hp > 0:
                self.status = "CLEARED"
                return
        if steps >= 32 or stop:
            return
        tt = self.ter[to]
        if tt == "ICE":
            nxt = to + DOFF[d]
            if self.can_enter(nxt, entity, d):
                self._atomic(entity, to, nxt, d, steps, portals, False)
        elif tt in MIRROR_MAP:
            nd = MIRROR_MAP[tt][d]
            nxt = to + DOFF[nd]
            if self.can_enter(nxt, entity, nd):
                self._atomic(entity, to, nxt, nd, steps, portals, False)
        elif tt[:7] == "SPRING_":
            sd = tt[7:]
            sdx, sdy = DIRS[sd]
            x1 = to % GRID_WIDTH
            y1 = to // GRID_WIDTH
            blocked_k = None
            for k in (1, 2, 3):
                px, py = x1 + k * sdx, y1 + k * sdy
                if not in_bounds(px, py):
                    blocked_k = k
                    break
                pi = py * GRID_WIDTH + px
                blk = (self.high(pi) or self.occ[pi] == "BOX"
                       or self.occ[pi] == "TNT" or oneway_block(self.ter[pi], sd))
                if entity == "BOX":
                    if pi == self.hy * GRID_WIDTH + self.hx or self.ter[pi] in ("K1", "K2", "V"):
                        blk = True
                if blk:
                    blocked_k = k
                    if entity == "BOX" and self.occ[pi] == "TNT":
                        self.tnt_armed.add(pi)
                    break
            if blocked_k is None:
                self._atomic(entity, to, to + 3 * DOFF[sd], sd, steps, portals, False)
            elif blocked_k > 1:
                self._atomic(entity, to, to + (blocked_k - 1) * DOFF[sd], sd, steps, portals, False)
        elif tt in PORTAL_PAIR and not suppress:
            pair = self.portal_pos.get(PORTAL_PAIR[tt])
            if pair is not None and self.occ[pair] is None:
                if entity == "BOX" and pair == self.hy * GRID_WIDTH + self.hx:
                    return
                portals += 1
                steps += 1
                if entity == "BOX":
                    self.occ[to] = None
                    self.occ[pair] = "BOX"
                    self.box_set.discard(to)
                    self.box_set.add(pair)
                    self._plates()
                else:
                    self.hx = pair % GRID_WIDTH
                    self.hy = pair // GRID_WIDTH
                    self.exposed.append(pair)
                if portals >= 2 or steps >= 32:
                    return
                nxt = pair + DOFF[d]
                if self.can_enter(nxt, entity, d):
                    self._atomic(entity, pair, nxt, d, steps, portals, False)

    def _move(self, d):
        dx, dy = DIRS[d]
        x0, y0 = self.hx, self.hy
        x1, y1 = x0 + dx, y0 + dy
        if not in_bounds(x1, y1):
            return
        p1 = y1 * GRID_WIDTH + x1
        if self.high(p1) or oneway_block(self.ter[p1], d) or self.occ[p1] == "TNT":
            return
        if self.occ[p1] == "BOX":
            x2, y2 = x0 + 2 * dx, y0 + 2 * dy
            if not in_bounds(x2, y2):
                return
            p2 = y2 * GRID_WIDTH + x2
            if not self.can_enter(p2, "BOX", d):
                return
            self._atomic("BOX", p1, p2, d, 0, 0, False)
            if self.status != "ALIVE":
                return
            if not self.high(p1) and not oneway_block(self.ter[p1], d) and self.occ[p1] is None:
                self._atomic("hero", y0 * GRID_WIDTH + x0, p1, d, 0, 0, False)
            return
        self._atomic("hero", y0 * GRID_WIDTH + x0, p1, d, 0, 0, False)

    def _jump(self, d):
        if self.jumps <= 0:
            return
        self.jumps -= 1
        dx, dy = DIRS[d]
        x0, y0 = self.hx, self.hy
        x1, y1 = x0 + dx, y0 + dy
        x2, y2 = x0 + 2 * dx, y0 + 2 * dy
        if not in_bounds(x2, y2):
            return
        p1 = y1 * GRID_WIDTH + x1
        p2 = y2 * GRID_WIDTH + x2
        if self.high(p1) or self.high(p2):
            return
        if self.occ[p2] == "BOX" or self.occ[p2] == "TNT":
            return
        if oneway_block(self.ter[p1], d) or oneway_block(self.ter[p2], d):
            return
        self._atomic("hero", y0 * GRID_WIDTH + x0, p2, d, 0, 0, False)

    def _throw(self, d):
        if self.throws <= 0:
            return
        self.throws -= 1
        dx, dy = DIRS[d]
        sx, sy = self.hx, self.hy
        rng = 6
        sp = 0
        shattered = False
        while rng > 0:
            sx += dx; sy += dy
            rng -= 1
            if not in_bounds(sx, sy):
                shattered = True
                break
            i = sy * GRID_WIDTH + sx
            if self.high(i) or self.occ[i] == "BOX":
                shattered = True
                break
            if self.occ[i] == "TNT":
                self.tnt_armed.add(i)
                shattered = True
                break
            tt = self.ter[i]
            if tt == "SWITCH":
                self.gates = not self.gates
                shattered = True
                break
            if tt == "MIMIC":
                self._clear_mimic(i)
                shattered = True
                break
            if tt in MIRROR_MAP:
                d = MIRROR_MAP[tt][d]
                dx, dy = DIRS[d]
                continue
            if tt in PORTAL_PAIR and sp < 2:
                pair = self.portal_pos.get(PORTAL_PAIR[tt])
                if pair is not None and self.occ[pair] != "BOX" and self.occ[pair] != "TNT":
                    sx = pair % GRID_WIDTH
                    sy = pair // GRID_WIDTH
                    sp += 1
                    if sp == 2:
                        shattered = True
                        break
                continue
        if rng == 0 and not shattered:
            i = sy * GRID_WIDTH + sx
            tt = self.ter[i]
            if tt == "ICE" or tt in MIRROR_MAP:
                if tt in MIRROR_MAP:
                    d = MIRROR_MAP[tt][d]
                    dx, dy = DIRS[d]
                for _ in range(32):
                    sx += dx; sy += dy
                    if not in_bounds(sx, sy):
                        break
                    i = sy * GRID_WIDTH + sx
                    if self.high(i) or self.occ[i] == "BOX":
                        break
                    if self.occ[i] == "TNT":
                        self.tnt_armed.add(i)
                        break
                    tt = self.ter[i]
                    if tt == "SWITCH":
                        self.gates = not self.gates
                        break
                    if tt == "MIMIC":
                        self._clear_mimic(i)
                        break
                    if tt[:7] == "ONEWAY_":
                        break
                    if tt in MIRROR_MAP:
                        d = MIRROR_MAP[tt][d]
                        dx, dy = DIRS[d]
                        continue
                    if tt == "ICE":
                        continue
                    if tt in PORTAL_PAIR and sp < 2:
                        pair = self.portal_pos.get(PORTAL_PAIR[tt])
                        if pair is not None and self.occ[pair] != "BOX" and self.occ[pair] != "TNT":
                            sx = pair % GRID_WIDTH
                            sy = pair // GRID_WIDTH
                            sp += 1
                            if sp == 2:
                                break
                        continue
                    break

    def _bomb(self):
        if self.bombs_left <= 0:
            return
        hi = self.hy * GRID_WIDTH + self.hx
        for b in self.bombs:
            if b[0] == hi:
                return
        self.bombs_left -= 1
        self.bombs.append([hi, 3])

    def _explode(self, sources):
        if not sources:
            return
        queue = deque(sources)
        exploded = set(sources)
        src_list = list(sources)
        while queue:
            e = queue.popleft()
            ex = e % GRID_WIDTH
            ey = e // GRID_WIDTH
            for yy in range(ey - 1, ey + 2):
                for xx in range(ex - 1, ex + 2):
                    if not in_bounds(xx, yy):
                        continue
                    i = yy * GRID_WIDTH + xx
                    if self.occ[i] == "TNT" and i not in exploded:
                        exploded.add(i)
                        queue.append(i)
                        src_list.append(i)
                    for b in self.bombs:
                        if b[0] == i and i not in exploded:
                            exploded.add(i)
                            queue.append(i)
                            src_list.append(i)
        a = 0
        b = 0
        for e in src_list:
            ex = e % GRID_WIDTH
            ey = e // GRID_WIDTH
            if abs(ex - self.hx) <= 1 and abs(ey - self.hy) <= 1:
                if self.occ[e] == "TNT":
                    a += 60
                else:
                    b += 50
        if a + b > 0:
            self._damage(a + b)
        self.bombs = [bb for bb in self.bombs if bb[0] not in exploded]
        union = set()
        for e in src_list:
            ex = e % GRID_WIDTH
            ey = e // GRID_WIDTH
            for yy in range(ey - 1, ey + 2):
                for xx in range(ex - 1, ex + 2):
                    if in_bounds(xx, yy):
                        union.add(yy * GRID_WIDTH + xx)
        for i in union:
            if self.occ[i] == "BOX":
                self.occ[i] = None
                self.box_set.discard(i)
            elif self.occ[i] == "TNT":
                self.occ[i] = None
                self.tnt_set.discard(i)
            tt = self.ter[i]
            if tt in EXPLODE_IMMUNE:
                continue
            if tt == "CRACK":
                self._set_ter(i, "PIT")
            elif tt in EXPLODE_DESTROY:
                if tt == "MIMIC":
                    self._clear_mimic(i)
                else:
                    self._set_ter(i, "EMPTY")
        self._plates()
        for i in list(self.box_set):
            if self.ter[i] == "PIT":
                self.occ[i] = None
                self.box_set.discard(i)
                self._set_ter(i, "EMPTY")
        self._plates()
        hi = self.hy * GRID_WIDTH + self.hx
        if self.hp > 0 and self.ter[hi] == "PIT":
            self._damage(100)

    def _phase_c(self):
        for b in self.bombs:
            b[1] -= 1
        sources = [b[0] for b in self.bombs if b[1] == 0]
        sources += list(self.tnt_armed)
        self.tnt_armed = set()
        if sources:
            self._explode(sources)

    def rays(self, periods):
        rays = []
        armed = set()
        for (ci, d, p) in self.cannons:
            if p not in periods:
                continue
            if self.ter[ci] not in ("LASER_" + d, "LASER2_" + d):
                continue
            dx, dy = DIRS[d]
            cx = ci % GRID_WIDTH
            cy = ci // GRID_WIDTH
            cells = set()
            for k in range(1, 11):
                nx, ny = cx + k * dx, cy + k * dy
                if not in_bounds(nx, ny):
                    break
                i = ny * GRID_WIDTH + nx
                if self.high(i) or self.occ[i] == "BOX":
                    break
                if self.occ[i] == "TNT":
                    cells.add(i)
                    armed.add(i)
                    break
                cells.add(i)
            rays.append(cells)
        return rays, armed

    def _phase_d(self):
        periods = set()
        if self.turn % 3 == 0:
            periods.add(3)
        if self.turn % 4 == 0:
            periods.add(4)
        rays, armed = self.rays(periods)
        m = 0
        exposed = set(self.exposed)
        for cells in rays:
            if cells & exposed:
                m += 1
        if m > 0:
            self._damage(50 * m)
            if self.status != "ALIVE":
                return
        if armed:
            self._explode(list(armed))

    def warnings(self, next_turn):
        periods = set()
        if next_turn % 3 == 0:
            periods.add(3)
        if next_turn % 4 == 0:
            periods.add(4)
        if not periods:
            return []
        out = []
        for (ci, d, p) in self.cannons:
            if p not in periods:
                continue
            if self.ter[ci] not in ("LASER_" + d, "LASER2_" + d):
                continue
            dx, dy = DIRS[d]
            cx = ci % GRID_WIDTH
            cy = ci // GRID_WIDTH
            for k in range(1, 11):
                nx, ny = cx + k * dx, cy + k * dy
                if not in_bounds(nx, ny):
                    break
                i = ny * GRID_WIDTH + nx
                if self.high(i) or self.occ[i] == "BOX":
                    break
                if self.occ[i] == "TNT":
                    out.append({"x": nx, "y": ny, "dir": d, "period": p,
                                "cannon": [cx, cy]})
                    break
                out.append({"x": nx, "y": ny, "dir": d, "period": p,
                            "cannon": [cx, cy]})
        out.sort(key=lambda w: (w["y"], w["x"], w["dir"], w["period"],
                                w["cannon"][0], w["cannon"][1]))
        return out

    def step(self, action):
        if self.status != "ALIVE":
            return self.status
        self.turn += 1
        self.exposed = [self.hy * GRID_WIDTH + self.hx]
        self.tnt_armed = set()
        if action == "WAIT":
            pass
        elif action == "BOMB":
            self._bomb()
        elif action[:5] == "MOVE_":
            self._move(action[5:])
        elif action[:5] == "JUMP_":
            self._jump(action[5:])
        elif action[:6] == "THROW_":
            self._throw(action[6:])
        if self.status == "ALIVE":
            self._phase_c()
        if self.status == "ALIVE" and (self.turn % 3 == 0 or self.turn % 4 == 0):
            self._phase_d()
        return self.status

    def run(self, actions):
        for a in actions:
            self.step(a)
            if self.status != "ALIVE":
                break
        return self.status


# ==============================================================================
# 魔王造图（v2.2 逻辑迷宫）
# ==============================================================================
def _blank_grid():
    return [
        ["T_W" if (x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1) else "EMPTY"
         for x in range(GRID_WIDTH)]
        for y in range(GRID_HEIGHT)
    ]


def _spend(grid):
    total = 0
    for y in range(1, GRID_HEIGHT - 1):
        for x in range(1, GRID_WIDTH - 1):
            total += TILE_COSTS.get(grid[y][x], 0)
    return total


def _fallback_dungeon():
    grid = _blank_grid()
    grid[5][20] = "K1"
    grid[20][20] = "K2"
    grid[13][35] = "V"
    sol = (["MOVE_R"] * 18 + ["MOVE_U"] * 8 + ["MOVE_D"] * 15
           + ["MOVE_U"] * 7 + ["MOVE_R"] * 15)
    return {"taunt": "空城一座，也敢来取？", "grid": grid, "author_solution": sol}


def _grid_to_terocc(grid):
    ter = ["EMPTY"] * NCELL
    occ = [None] * NCELL
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            t = grid[y][x]
            i = y * GRID_WIDTH + x
            if t in ("BOX", "TNT"):
                occ[i] = t
            else:
                ter[i] = t
    return ter, occ


def _walk_path(eng, goal, allow_switch=False):
    """作者自证用：当前局面下激光时序安全的纯平地步行 BFS（状态=格x12相位）。"""
    start = eng.hy * GRID_WIDTH + eng.hx
    if start == goal:
        return []
    danger = [set() for _ in range(12)]
    for ph in range(12):
        t = ph if ph != 0 else 12
        periods = set()
        if t % 3 == 0:
            periods.add(3)
        if t % 4 == 0:
            periods.add(4)
        if periods:
            rays, armed = eng.rays(periods)
            for cells in rays:
                danger[ph] |= cells
            for ti in armed:
                tx = ti % GRID_WIDTH
                ty = ti // GRID_WIDTH
                for yy in range(ty - 1, ty + 2):
                    for xx in range(tx - 1, tx + 2):
                        if in_bounds(xx, yy):
                            danger[ph].add(yy * GRID_WIDTH + xx)
    ter = eng.ter
    occ = eng.occ
    gates = eng.gates
    plates = eng.plates

    def ok_cell(i, d):
        if i < 0 or i >= NCELL:
            return False
        x = i % GRID_WIDTH
        if d == "L" and x == GRID_WIDTH - 1:
            return False
        if d == "R" and x == 0:
            return False
        tt = ter[i]
        if is_high_wall(tt, gates, plates):
            return False
        if tt in ("PIT", "MIMIC", "CRACK") or tt in MOMENTUM_TILES:
            return False
        if tt == "SWITCH" and not allow_switch:
            return False
        if occ[i] is not None:
            return False
        if oneway_block(tt, d):
            return False
        return True

    parent = {(start, eng.turn % 12): None}
    q = deque([(start, eng.turn % 12)])
    seen = {(start, eng.turn % 12)}
    found = None
    while q:
        cur, ph = q.popleft()
        if cur == goal:
            found = (cur, ph)
            break
        nph = (ph + 1) % 12
        fire = (nph % 3 == 0) or (nph % 4 == 0)
        for d in DIR_NAMES:
            nxt = cur + DOFF[d]
            if not ok_cell(nxt, d):
                continue
            if fire and (cur in danger[nph] or nxt in danger[nph]):
                continue
            st = (nxt, nph)
            if st not in seen:
                seen.add(st)
                parent[st] = ((cur, ph), "MOVE_" + d)
                q.append(st)
        if fire and cur in danger[nph]:
            pass
        else:
            st = (cur, nph)
            if st not in seen:
                seen.add(st)
                parent[st] = ((cur, ph), "WAIT")
                q.append(st)
    if found is None:
        return None
    path = []
    cur = found
    while parent[cur] is not None:
        prev, act = parent[cur]
        path.append(act)
        cur = prev
    path.reverse()
    return path


def _author_plan(grid, segments):
    """按宏段落（步行/推箱/炸弹）生成并引擎验证作者解；返回动作列表或 None。"""
    eng = Eng().setup(grid)
    actions = []
    v_idx = None
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if grid[y][x] == "V":
                v_idx = y * GRID_WIDTH + x

    def walk_to(x, y, allow_switch=False):
        goal = y * GRID_WIDTH + x
        p = _walk_path(eng, goal, allow_switch)
        if p is None:
            return False
        for a in p:
            eng.step(a)
            if eng.hp < 100 or eng.status == "DEAD":
                return False
            if eng.status == "CLEARED" and goal != v_idx:
                return False
            actions.append(a)
        return (eng.hx, eng.hy) == (x, y)

    def safe_act(a):
        for _ in range(12):
            e2 = eng.clone()
            e2.step(a)
            if e2.status in ("ALIVE", "CLEARED") and e2.hp == 100:
                eng.step(a)
                actions.append(a)
                return True
            ew = eng.clone()
            ew.step("WAIT")
            if ew.status != "ALIVE" or ew.hp < 100:
                return False
            eng.step("WAIT")
            actions.append("WAIT")
        return False

    def push(bx, by, d, n):
        dx, dy = DIRS[d]
        if not walk_to(bx - dx, by - dy):
            return False
        for _ in range(n):
            bi = by * GRID_WIDTH + bx
            if eng.occ[bi] != "BOX":
                return False
            if not safe_act("MOVE_" + d):
                return False
            bx += dx
            by += dy
        return True

    for seg in segments:
        kind = seg[0]
        if kind == "walk":
            if not walk_to(seg[1], seg[2], seg[3] if len(seg) > 3 else False):
                return None
        elif kind == "push":
            if not push(seg[1], seg[2], seg[3], seg[4]):
                return None
        elif kind == "bomb":
            bx, by, rx, ry, waits = seg[1], seg[2], seg[3], seg[4], seg[5]
            if not walk_to(bx, by):
                return None
            eng.step("BOMB")
            actions.append("BOMB")
            if not walk_to(rx, ry):
                return None
            for _ in range(waits):
                eng.step("WAIT")
                if eng.status != "ALIVE" or eng.hp < 100:
                    return None
                actions.append("WAIT")
        elif kind == "act":
            if not safe_act(seg[1]):
                return None
    if eng.status != "CLEARED" or eng.turn != len(actions):
        return None
    if not (1 <= len(actions) <= MAX_AUTHOR_STEPS):
        return None
    return actions


def _main_grid():
    grid = _blank_grid()

    def setc(x, y, t):
        grid[y][x] = t

    def wall_v(x, y0, y1, gaps=()):
        for y in range(y0, y1 + 1):
            if y not in gaps:
                setc(x, y, "T_W")

    def wall_h(y, x0, x1, mat="W", gaps=()):
        for x in range(x0, x1 + 1):
            if x not in gaps:
                setc(x, y, mat)

    # 三条纵向钛金屏障（分区），缺口即谜题锁
    wall_v(11, 1, 24, gaps=(20,))
    wall_v(23, 1, 24, gaps=(13,))
    wall_v(32, 1, 24, gaps=(6, 13))
    setc(11, 20, "B_GATE")     # A->B 主通道：初始开，翻开关后关
    setc(11, 4, "ONEWAY_R")    # A->B 顶部单向备用通道（顺箭头可入）
    setc(23, 13, "PIT")        # B->C 唯一通道：必须推箱填坑
    setc(32, 13, "P_GATE")     # 金库正门：三板全压才开
    setc(32, 6, "CRACK")       # D 区顶部诱饵入口：一次性脆冰桥

    # 地标
    setc(19, 3, "K1")
    setc(28, 21, "K2")
    setc(36, 13, "V")

    # K1 红门密室（开关翻转后可入）
    setc(19, 4, "R_GATE")
    for (wx, wy) in ((18, 3), (20, 3), (18, 4), (20, 4)):
        setc(wx, wy, "W")
    setc(21, 12, "SWITCH")

    # K2 单向炸弹密室（四面封死，仅炸弹可开）
    setc(28, 19, "ONEWAY_D")
    setc(28, 20, "W")
    setc(27, 21, "W")
    setc(29, 21, "W")
    setc(28, 22, "W")

    # 三压板 + 单向推入口 + 侧壁
    for (px, py, oy) in ((14, 10, 11), (19, 17, 18), (29, 9, 10)):
        setc(px, py, "PLATE")
        setc(px - 1, py, "T_W")
        setc(px + 1, py, "T_W")
        setc(px, py - 1, "W")
        setc(px, oy, "ONEWAY_U")

    # 四箱：A 区一箱必须先在翻开关前推过 B_GATE
    setc(5, 17, "BOX")
    setc(14, 20, "BOX")
    setc(19, 21, "BOX")
    setc(29, 14, "BOX")

    # 双频激光：x=27 红(3拍)y2..11 + 蓝(4拍)y13..22；y14 红炮与蓝柱交叠 (27,14) 12拍瞬杀
    setc(27, 1, "LASER_D")
    setc(27, 12, "LASER2_D")
    setc(24, 14, "LASER_R")

    # D 区顶部诱饵密室（脆冰桥进入即封死，钛金南墙不可炸穿）
    wall_h(7, 33, 38, "T_W")
    setc(33, 12, "W")
    setc(33, 14, "W")

    # 伪装宝箱怪（明牌下由骸骨线索可辨）
    setc(8, 8, "MIMIC")

    # 少量迷宫墙增加绕路
    wall_h(8, 2, 6, "W", gaps=(4,))
    wall_h(16, 2, 6, "W", gaps=(5,))
    wall_h(10, 15, 21, "W", gaps=(18,))
    wall_h(19, 25, 30, "W", gaps=(28,))

    # 出生净空区
    for y in range(12, 15):
        for x in range(1, 4):
            setc(x, y, "EMPTY")
    return grid


def _author_segments():
    return [
        # 1) B 箱直上压板1
        ("walk", 14, 21),
        ("push", 14, 20, "U", 10),     # B -> (14,10) 压板1
        # 2) A 箱下行右移过 B_GATE，C 箱让位后 A 上压板2
        ("walk", 5, 18),
        ("push", 5, 17, "D", 3),       # A -> (5,20)
        ("walk", 4, 20),
        ("push", 5, 20, "R", 14),      # A -> (19,20)
        ("walk", 18, 21),
        ("push", 19, 21, "R", 1),      # C -> (20,21)
        ("push", 19, 20, "U", 3),      # A -> (19,17) 压板2
        # 3) C 箱右移上行再填坑
        ("walk", 19, 21),
        ("push", 20, 21, "R", 2),      # C -> (22,21)
        ("walk", 22, 22),
        ("push", 22, 21, "U", 8),      # C -> (22,13)
        ("walk", 21, 13),
        ("push", 22, 13, "R", 1),      # C 填 (23,13)
        # 4) D 箱上压板3，P_GATE 开
        ("walk", 29, 15),
        ("push", 29, 14, "U", 5),      # D -> (29,9) 压板3
        # 5) K2：炸开单向密室
        ("walk", 28, 18),
        ("act", "MOVE_D"),             # -> (28,19) ONEWAY_D
        ("bomb", 28, 19, 28, 17, 1),
        ("walk", 28, 21),              # 取 K2
        # 6) 翻开关（R_GATE 开 / B_GATE 关）
        ("walk", 21, 13),
        ("act", "MOVE_U"),             # 踩 SWITCH (21,12)
        # 7) K1
        ("walk", 19, 5),
        ("act", "MOVE_U"),
        ("act", "MOVE_U"),             # (19,3) K1
        # 8) 金库冲刺（卡蓝炮 4 拍）
        ("walk", 19, 13),
        ("walk", 36, 13),
    ]


def _spawn_admission(grid):
    """出生 4 回合准入：>=2 个不同 Turn1 零伤落点，各自可零伤活过 Turn4。"""
    base = Eng().setup(grid)
    landings = set()
    for a in VALID_ACTIONS:
        e = base.clone()
        e.step(a)
        if e.status != "ALIVE" or e.hp < 100 or e.trap_damage > 0:
            continue
        pos = (e.hx, e.hy)
        if pos in landings:
            continue
        # turns 2..4 零伤生存 BFS（按 (pos,turn) 去重，保留最高 hp）
        frontier = {pos: e}
        ok = False
        for t in (2, 3, 4):
            nxt = {}
            for p, eng in frontier.items():
                for a2 in VALID_ACTIONS:
                    e2 = eng.clone()
                    e2.step(a2)
                    if e2.status != "ALIVE" or e2.hp < 100 or e2.trap_damage > 0:
                        continue
                    k2 = (e2.hx, e2.hy)
                    if k2 not in nxt or nxt[k2].hp < e2.hp:
                        nxt[k2] = e2
            frontier = nxt
            if not frontier:
                break
        if frontier:
            ok = True
        if ok:
            landings.add(pos)
        if len(landings) >= 2:
            return True
    return len(landings) >= 2


def _layout_ok(grid):
    if len(grid) != GRID_HEIGHT or any(len(r) != GRID_WIDTH for r in grid):
        return False
    legal = set(TILE_COSTS)
    counts = {}
    inner_tw = 0
    lm = {"K1": [], "K2": [], "V": []}
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            t = grid[y][x]
            if t not in legal:
                return False
            border = (x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1)
            if border:
                if t != "T_W":
                    return False
            else:
                counts[t] = counts.get(t, 0) + 1
                if t == "T_W":
                    inner_tw += 1
            if t in lm:
                lm[t].append((x, y))
    for y in range(12, 15):
        for x in range(1, 4):
            if grid[y][x] != "EMPTY":
                return False
    if any(len(v) != 1 for v in lm.values()):
        return False
    (kx1, ky1), = lm["K1"]
    (kx2, ky2), = lm["K2"]
    (vx, vy), = lm["V"]
    if not (12 <= kx1 <= 34 and 2 <= ky1 <= 10):
        return False
    if not (12 <= kx2 <= 34 and 15 <= ky2 <= 23):
        return False
    if abs(kx1 - kx2) + abs(ky1 - ky2) < 12:
        return False
    if not (33 <= vx <= 37 and 4 <= vy <= 21):
        return False
    if _spend(grid) > MAX_BUDGET or inner_tw > 120:
        return False
    caps = {
        ("MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW"): 30,
        ("SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R"): 20,
        ("LASER_U", "LASER_D", "LASER_L", "LASER_R",
         "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R"): 12,
        ("CRACK",): 40, ("SWITCH",): 6,
        ("R_GATE", "B_GATE"): 16, ("TNT",): 12,
        ("BOX",): 6, ("HEAL",): 4, ("MIMIC",): 4,
        ("PLATE",): 4, ("P_GATE",): 8,
        ("ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R"): 12,
    }
    for group, cap in caps.items():
        if sum(counts.get(t, 0) for t in group) > cap:
            return False
    nplate = counts.get("PLATE", 0)
    nbox = counts.get("BOX", 0)
    if counts.get("P_GATE", 0) > 0 and not (1 <= nplate <= nbox):
        return False
    for n in ("1", "2"):
        a = counts.get("PORTAL_%sA" % n, 0)
        b = counts.get("PORTAL_%sB" % n, 0)
        if (a > 0) != (b > 0) or a > 1 or b > 1:
            return False
    eng = Eng().setup(grid)
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if grid[y][x] == "MIMIC" and (x, y) not in eng.mimic_clue:
                return False
    return True


def build_dungeon() -> dict:
    grid = _main_grid()
    if not _layout_ok(grid):
        return _fallback_dungeon()
    if not _spawn_admission(grid):
        return _fallback_dungeon()
    sol = _author_plan(grid, _author_segments())
    if sol is None:
        return _fallback_dungeon()
    eng = Eng().setup(grid)
    status = eng.run(sol)
    if status != "CLEARED" or eng.turn != len(sol) or eng.hp <= 0:
        return _fallback_dungeon()
    return {
        "taunt": "三板压金库，十二拍断魂；单向门后，再无归途。",
        "grid": grid,
        "author_solution": sol,
    }


# ==============================================================================
# 勇者：FULL 全图明牌全局状态空间搜索
# ==============================================================================
def _ingest(state, memory):
    terr = state.get("terrain")
    occg = state.get("occupant")
    clues = state.get("clues")
    hero = state["hero"]
    turn = state.get("turn", 1)
    gates = state.get("gates_flipped", False)
    base_ter = ["EMPTY"] * NCELL
    base_occ = [None] * NCELL
    chest_cells = []
    for y in range(GRID_HEIGHT):
        row = terr[y]
        orow = occg[y] if occg else None
        for x in range(GRID_WIDTH):
            t = row[x]
            i = y * GRID_WIDTH + x
            if t == "CHEST":
                chest_cells.append(i)
                base_ter[i] = "HEAL"
            else:
                base_ter[i] = t
            if orow:
                o = orow[x]
                if o == "BOX" or o == "TNT":
                    base_occ[i] = o
    if clues:
        for i in chest_cells:
            x = i % GRID_WIDTH
            y = i // GRID_WIDTH
            mimic = False
            for (dx, dy) in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = x + dx, y + dy
                if in_bounds(nx, ny) and clues[ny][nx]:
                    mimic = True
                    break
            if mimic:
                base_ter[i] = "MIMIC"
    targets = state.get("targets") or {}
    k1 = k2 = v = None
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            t = base_ter[y * GRID_WIDTH + x]
            if t == "K1":
                k1 = y * GRID_WIDTH + x
            elif t == "K2":
                k2 = y * GRID_WIDTH + x
            elif t == "V":
                v = y * GRID_WIDTH + x
    if targets.get("K1"):
        k1 = targets["K1"][1] * GRID_WIDTH + targets["K1"][0]
    if targets.get("K2"):
        k2 = targets["K2"][1] * GRID_WIDTH + targets["K2"][0]
    if targets.get("V"):
        v = targets["V"][1] * GRID_WIDTH + targets["V"][0]
    plates = [i for i in range(NCELL) if base_ter[i] == "PLATE"]
    cannons = []
    portals = {}
    heals = []
    boxes = []
    tnts = []
    for i in range(NCELL):
        t = base_ter[i]
        d, p = laser_info(t)
        if d is not None:
            cannons.append((i, d, p))
        if t[:7] == "PORTAL_":
            portals[t] = i
        if t == "HEAL":
            heals.append(i)
        if base_occ[i] == "BOX":
            boxes.append(i)
        elif base_occ[i] == "TNT":
            tnts.append(i)
    meta = {"plates": plates, "cannons": cannons, "portals": portals,
            "heals": heals, "boxes": boxes, "tnts": tnts,
            "k1": k1, "k2": k2, "v": v}
    ks = hero.get("keys", [False, False])
    kmask = (1 if ks[0] else 0) | (2 if ks[1] else 0)
    mb = memory.get("my_bombs") or []
    bombs_t = tuple(sorted((i, t - turn + 1) for (i, t) in mb if t >= turn))
    st = (hero["x"], hero["y"], hero["hp"], kmask, gates, turn - 1,
          hero.get("jumps", 3), hero.get("throws", 3), hero.get("bombs", 2),
          bombs_t, tuple(sorted(boxes)), tuple(sorted(tnts)), ())
    return base_ter, base_occ, meta, st


def _bfs_field(base_ter, base_occ, goal, gf, pf, pit_pass=False, wall_pass=False):
    blocked = [False] * NCELL
    for i in range(NCELL):
        t = base_ter[i]
        if is_high_wall(t, gf, pf):
            blocked[i] = True
        elif t in ("PIT", "MIMIC") or base_occ[i] == "TNT":
            blocked[i] = True
    if pit_pass:
        for i in range(NCELL):
            if base_ter[i] == "PIT":
                blocked[i] = False
    if wall_pass:
        for i in range(NCELL):
            if base_ter[i] == "W":
                blocked[i] = False
    dist = [-1] * NCELL
    if goal is None or blocked[goal]:
        return dist
    dist[goal] = 0
    q = deque([goal])
    while q:
        cur = q.popleft()
        dc = dist[cur]
        cx = cur % GRID_WIDTH
        cy = cur // GRID_WIDTH
        for d in DIR_NAMES:
            dx, dy = DIRS[d]
            px, py = cx - dx, cy - dy
            if not (0 <= px < GRID_WIDTH and 0 <= py < GRID_HEIGHT):
                continue
            pi = py * GRID_WIDTH + px
            if dist[pi] >= 0 or blocked[pi]:
                continue
            if oneway_block(base_ter[cur], d):
                continue
            dist[pi] = dc + 1
            q.append(pi)
    return dist


def _route_fields(base_ter, base_occ, meta, gates, plates):
    goals = [g for g in (meta["k1"], meta["k2"], meta["v"]) if g is not None]
    fields = {}
    for gf in (False, True):
        for pf in (False, True):
            ff = {}
            for goal in goals:
                ff[goal] = _bfs_field(base_ter, base_occ, goal, gf, pf)
            fields[(gf, pf)] = ff
    return fields


def _push_field(base_ter, base_occ, meta, target, gates, plates):
    """反向推箱 BFS：箱从哪来才能到 target（忽略其它箱/勇者，乐观）。"""
    dist = [-1] * NCELL
    if base_ter[target] in ("K1", "K2", "V"):
        return dist
    dist[target] = 0
    q = deque([target])
    while q:
        cur = q.popleft()
        dc = dist[cur]
        cx = cur % GRID_WIDTH
        cy = cur // GRID_WIDTH
        for d in DIR_NAMES:
            dx, dy = DIRS[d]
            px, py = cx - dx, cy - dy
            hx, hy = cx - 2 * dx, cy - 2 * dy
            if not (0 <= px < GRID_WIDTH and 0 <= py < GRID_HEIGHT):
                continue
            if not (0 <= hx < GRID_WIDTH and 0 <= hy < GRID_HEIGHT):
                continue
            pi = py * GRID_WIDTH + px
            hi = hy * GRID_WIDTH + hx
            if dist[pi] >= 0:
                continue
            tp = base_ter[pi]
            tc = base_ter[cur]
            if is_high_wall(tp, gates, plates) or tp in ("PIT", "K1", "K2", "V", "MIMIC"):
                continue
            if oneway_block(tp, d):
                continue
            if is_high_wall(tc, gates, plates) or oneway_block(tc, d):
                continue
            if tc in ("K1", "K2", "V"):
                continue
            th = base_ter[hi]
            if is_high_wall(th, gates, plates) or th == "PIT":
                continue
            dist[pi] = dc + 1
            q.append(pi)
    return dist


def _plate_terms(st, pushf, meta):
    missing = 0
    push_sum = 0
    useful = []
    boxes = st[10]
    for idx, p in enumerate(meta["plates"]):
        if p not in boxes:
            missing += 1
            best = 999
            bb = None
            if idx < len(pushf):
                pf = pushf[idx]
                for b in boxes:
                    dd = pf[b]
                    if 0 <= dd < best:
                        best = dd
                        bb = b
            push_sum += best if best < 999 else 30
            if bb is not None:
                useful.append(bb)
    return missing, push_sum, useful


def _select_goal(bt, bo, meta, st, fields, plates):
    gates = st[4]
    kmask = st[3]
    hi = st[1] * GRID_WIDTH + st[0]
    k1, k2, v = meta["k1"], meta["k2"], meta["v"]
    if kmask == 3:
        final = v
    elif kmask == 1:
        final = k2
    elif kmask == 2:
        final = k1
    else:
        final = None
        bd = 100000
        for g in (k1, k2):
            if g is None:
                continue
            for cfg in ((gates, plates), (not gates, plates), (gates, True), (not gates, True)):
                dd = fields[cfg][g][hi]
                if 0 <= dd < bd:
                    bd = dd
                    final = g
        if final is None:
            bd = 100000
            for g in (k1, k2):
                if g is None:
                    continue
                md = abs(hi % GRID_WIDTH - g % GRID_WIDTH) + abs(hi // GRID_WIDTH - g // GRID_WIDTH)
                if md < bd:
                    bd = md
                    final = g
    if final is None:
        return ("cell", v, {})
    if st[2] <= 45 and meta["heals"]:
        best_h = None
        bd = 100000
        for hc in meta["heals"]:
            f = _bfs_field(bt, bo, hc, gates, plates)
            if 0 <= f[hi] < bd:
                bd = f[hi]
                best_h = hc
        if best_h is not None and bd <= 25:
            return ("cell", best_h, {"goal_fields": {(gates, plates): _bfs_field(bt, bo, best_h, gates, plates)}})
    missing = sum(1 for p in meta["plates"] if p not in st[10])
    if fields[(gates, plates)][final][hi] >= 0:
        return ("cell", final, {})
    need_plates = missing > 0 and (fields[(gates, True)][final][hi] >= 0
                                   or fields[(not gates, True)][final][hi] >= 0)
    if need_plates:
        for b in st[10]:
            if _bfs_field(bt, bo, b, gates, plates)[hi] >= 0:
                return ("plates", None, {})
    if fields[(not gates, plates)][final][hi] >= 0:
        sw = _nearest_switch(bt, bo, hi, gates, plates)
        if sw is not None:
            return ("switch", sw, {})
        sw2 = _nearest_switch(bt, bo, hi, gates, True)
        if sw2 is not None and missing > 0:
            return ("plates", None, {})
    fp = _bfs_field(bt, bo, final, gates, plates, pit_pass=True)
    if fp[hi] >= 0:
        pit = _first_special(bt, fp, hi, final, "PIT")
        if pit is not None:
            pfield = _push_field(bt, bo, meta, pit, gates, plates)
            if any(0 <= pfield[b] for b in st[10]):
                return ("pit", pit, {})
            ov = {}
            for gf in (False, True):
                for pf in (False, True):
                    ov[(gf, pf)] = _bfs_field(bt, bo, final, gf, pf, pit_pass=True)
            return ("cell", final, {"override_fields": ov})
    fw = _bfs_field(bt, bo, final, gates, plates, wall_pass=True)
    if fw[hi] >= 0 and st[8] > 0:
        wc = _first_special(bt, fw, hi, final, "W", last=True)
        if wc is not None:
            return ("bomb", wc, {})
    if fw[hi] >= 0:
        ov = {}
        for gf in (False, True):
            for pf in (False, True):
                ov[(gf, pf)] = _bfs_field(bt, bo, final, gf, pf, wall_pass=True)
        return ("cell", final, {"override_fields": ov})
    return ("cell", final, {})


def _nearest_switch(bt, bo, hi, gates, plates):
    best = None
    bd = 100000
    for i in range(NCELL):
        if bt[i] == "SWITCH":
            f = _bfs_field(bt, bo, i, gates, plates)
            if 0 <= f[hi] < bd:
                bd = f[hi]
                best = i
    return best


def _first_special(bt, field, hi, final, tile, last=False):
    cur = hi
    found = None
    for _ in range(NCELL):
        if cur == final:
            return found if last else None
        dc = field[cur]
        cx = cur % GRID_WIDTH
        cy = cur // GRID_WIDTH
        nxt = None
        for d in DIR_NAMES:
            dx, dy = DIRS[d]
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT):
                continue
            ni = ny * GRID_WIDTH + nx
            if field[ni] == dc - 1 and not oneway_block(bt[ni], d):
                if bt[ni] == tile:
                    if not last:
                        return ni
                    found = ni
                if nxt is None and bt[ni] not in ("PIT", "MIMIC"):
                    nxt = ni
        if nxt is None:
            return found
        cur = nxt
    return found


def _heuristic(st, gtype, gcell, fields, pushf, meta, gates, plates, extra):
    hx, hy = st[0], st[1]
    hi = hy * GRID_WIDTH + hx
    if gtype == "plates":
        missing, push_sum, useful = _plate_terms(st, pushf, meta)
        app = 999
        for b in useful:
            md = abs(hx - b % GRID_WIDTH) + abs(hy - b // GRID_WIDTH)
            if md < app:
                app = md
        return push_sum + 3 * missing + 0.5 * (app if app < 999 else 0)
    if gtype == "pit":
        pf = extra.get("pit_field")
        boxes = st[10]
        best = 999
        app = 999
        for b in boxes:
            dd = pf[b] if pf is not None else -1
            if 0 <= dd < best:
                best = dd
                app = abs(hx - b % GRID_WIDTH) + abs(hy - b // GRID_WIDTH)
        return (best if best < 999 else 40) + 0.5 * (app if app < 999 else 0)
    if gtype == "bomb":
        return abs(hx - gcell % GRID_WIDTH) + abs(hy - gcell // GRID_WIDTH) + 3
    missing, push_sum, _ = _plate_terms(st, pushf, meta)
    best = 100000
    for (gf, pf), ff in fields.items():
        fd = extra.get("override_fields", {}).get((gf, pf))
        if fd is None:
            fd = ff.get(gcell)
        if fd is None:
            fd = extra.get("goal_fields", {}).get((gf, pf))
        if fd is None:
            continue
        dd = fd[hi]
        if dd < 0:
            continue
        pen = 0
        if gf != gates:
            pen += 6
        if pf and not plates and missing > 0:
            pen += 10 * missing + push_sum
        if dd + pen < best:
            best = dd + pen
    if best >= 100000:
        if gcell is not None:
            best = 300 + abs(hx - gcell % GRID_WIDTH) + abs(hy - gcell // GRID_WIDTH)
        else:
            best = 300
    return best


def _search(base_ter, base_occ, meta, root, budget, memory):
    t0 = time.monotonic()
    deadline = t0 + budget
    gates = root[4]
    eng = Eng().setup_flat(base_ter, base_occ, meta)
    eng.load(root)
    plates = eng.plates
    fields = _route_fields(base_ter, base_occ, meta, gates, plates)
    pushf = [_push_field(base_ter, base_occ, meta, p, gates, True) for p in meta["plates"]]
    gtype, gcell, extra = _select_goal(base_ter, base_occ, meta, root, fields, plates)
    if gtype == "pit":
        extra["pit_field"] = _push_field(base_ter, base_occ, meta, gcell, gates, plates)
    if gtype == "switch" or (gtype == "cell" and gcell not in (meta["k1"], meta["k2"], meta["v"])):
        gflds = {}
        for gf in (False, True):
            for pf in (False, True):
                gflds[(gf, pf)] = _bfs_field(base_ter, base_occ, gcell, gf, pf)
        extra["goal_fields"] = gflds
    root_key_bit = 0
    if gtype == "cell" and gcell == meta["k1"]:
        root_key_bit = 1
    elif gtype == "cell" and gcell == meta["k2"]:
        root_key_bit = 2

    def goal_hit(nst, e):
        if gtype == "switch":
            return nst[4] != root[4]
        if gtype == "plates":
            return e.plates
        if gtype == "pit":
            return e.ter[gcell] != "PIT"
        if gtype == "bomb":
            return e.ter[gcell] == "EMPTY"
        if gcell == meta["v"]:
            return e.status == "CLEARED"
        if root_key_bit:
            return (nst[3] & root_key_bit) != (root[3] & root_key_bit)
        return e.ter[gcell] == "EMPTY"

    h0 = _heuristic(root, gtype, gcell, fields, pushf, meta, gates, plates, extra)
    nodes = [(None, None, root)]
    root_key = (root[0], root[1], root[3], root[4], root[5] % 12,
                root[6], root[7], root[8], root[9], root[10], root[11], root[12])
    seen = {root_key: (0, root[2])}
    counter = 0
    heap = [(1.5 * h0, 0, counter, 0)]
    best_partial = 0
    best_partial_h = h0 + (100 - root[2]) * 1.0
    fallback_goal = None
    pops = 0
    while heap:
        if pops % 128 == 0 and time.monotonic() > deadline:
            break
        if len(nodes) > 150000:
            break
        f, neg_g, _, nid = heapq.heappop(heap)
        pops += 1
        parent, act, st = nodes[nid]
        g = -neg_g
        eng.load(st)
        turn = st[5]
        hi = st[1] * GRID_WIDTH + st[0]
        ter = eng.ter
        occ = eng.occ
        nturn = turn + 1
        fires = (nturn % 3 == 0) or (nturn % 4 == 0)
        danger = None
        if fires:
            periods = set()
            if nturn % 3 == 0:
                periods.add(3)
            if nturn % 4 == 0:
                periods.add(4)
            rays, _ = eng.rays(periods)
            danger = set()
            for cells in rays:
                danger |= cells
        nturn2 = turn + 2
        danger2 = None
        if nturn2 % 3 == 0 or nturn2 % 4 == 0:
            periods2 = set()
            if nturn2 % 3 == 0:
                periods2.add(3)
            if nturn2 % 4 == 0:
                periods2.add(4)
            rays2, _ = eng.rays(periods2)
            danger2 = set()
            for cells in rays2:
                danger2 |= cells
        nturn3 = turn + 3
        if nturn3 % 3 == 0 or nturn3 % 4 == 0:
            periods3 = set()
            if nturn3 % 3 == 0:
                periods3.add(3)
            if nturn3 % 4 == 0:
                periods3.add(4)
            rays3, _ = eng.rays(periods3)
            for cells in rays3:
                if danger2 is None:
                    danger2 = set()
                danger2 |= cells
        acts = []
        if fires or st[9]:
            acts.append("WAIT")
        hx, hy = st[0], st[1]
        for d in DIR_NAMES:
            dx, dy = DIRS[d]
            x1, y1 = hx + dx, hy + dy
            if not in_bounds(x1, y1):
                continue
            p1 = y1 * GRID_WIDTH + x1
            t1 = ter[p1]
            if eng.high(p1) or oneway_block(t1, d) or occ[p1] == "TNT":
                continue
            if occ[p1] == "BOX":
                x2, y2 = hx + 2 * dx, hy + 2 * dy
                if in_bounds(x2, y2) and eng.can_enter(y2 * GRID_WIDTH + x2, "BOX", d):
                    acts.append("MOVE_" + d)
                continue
            if t1 in ("PIT", "MIMIC"):
                continue
            acts.append("MOVE_" + d)
        if st[6] > 0:
            for d in DIR_NAMES:
                dx, dy = DIRS[d]
                x1, y1 = hx + dx, hy + dy
                x2, y2 = hx + 2 * dx, hy + 2 * dy
                if not in_bounds(x2, y2):
                    continue
                p1 = y1 * GRID_WIDTH + x1
                p2 = y2 * GRID_WIDTH + x2
                if eng.high(p1) or eng.high(p2) or occ[p2] == "BOX" or occ[p2] == "TNT":
                    continue
                if oneway_block(ter[p1], d) or oneway_block(ter[p2], d):
                    continue
                if occ[p1] == "BOX" or ter[p1] == "PIT" or (danger and p1 in danger):
                    acts.append("JUMP_" + d)
        if st[7] > 0:
            for d in DIR_NAMES:
                dx, dy = DIRS[d]
                sx, sy = hx, hy
                useful = False
                for _ in range(6):
                    sx += dx; sy += dy
                    if not in_bounds(sx, sy):
                        break
                    i = sy * GRID_WIDTH + sx
                    if eng.high(i) or occ[i] == "BOX":
                        break
                    if occ[i] == "TNT" or ter[i] in ("SWITCH", "MIMIC"):
                        useful = True
                        break
                    if ter[i] in MIRROR_MAP:
                        nd = MIRROR_MAP[ter[i]][d]
                        dx, dy = DIRS[nd]
                if useful:
                    acts.append("THROW_" + d)
        if st[8] > 0:
            has_target = False
            for b in eng.bombs:
                if b[0] == hi:
                    has_target = True
            if not has_target:
                for yy in range(hy - 1, hy + 2):
                    for xx in range(hx - 1, hx + 2):
                        if in_bounds(xx, yy):
                            i = yy * GRID_WIDTH + xx
                            if ter[i] == "W" or occ[i] == "TNT":
                                has_target = True
            if has_target:
                acts.append("BOMB")
        for a in acts:
            eng.load(st)
            status = eng.step(a)
            if status == "DEAD":
                continue
            ng = g + 1
            nst = eng.state()
            if goal_hit(nst, eng):
                path = [a]
                cur = nid
                while nodes[cur][0] is not None:
                    path.append(nodes[cur][1])
                    cur = nodes[cur][0]
                path.reverse()
                if nst[2] >= root[2]:
                    return path, True
                if fallback_goal is None:
                    fallback_goal = path
                continue
            nkey = (nst[0], nst[1], nst[3], nst[4], nst[5] % 12,
                    nst[6], nst[7], nst[8], nst[9], nst[10], nst[11], nst[12])
            nhp = nst[2]
            old = seen.get(nkey)
            if old is not None and old[0] <= ng and old[1] >= nhp:
                continue
            seen[nkey] = (ng, nhp)
            h = _heuristic(nst, gtype, gcell, fields, pushf, meta, nst[4], eng.plates, extra)
            pm = h + (100 - nhp) * 1.0
            if danger2 is not None and (nst[1] * GRID_WIDTH + nst[0]) in danger2:
                pm += 500
            if pm < best_partial_h:
                best_partial_h = pm
                best_partial = len(nodes)
            counter += 1
            nodes.append((nid, a, nst))
            ff = ng + 1.5 * h + (100 - nhp) * 0.5 + (2 - nst[8]) * 1.2 + (3 - nst[6]) * 0.25
            heapq.heappush(heap, (ff, -ng, counter, len(nodes) - 1))
    if fallback_goal is not None:
        return fallback_goal, True
    path = []
    cur = best_partial
    while nodes[cur][0] is not None:
        path.append(nodes[cur][1])
        cur = nodes[cur][0]
    path.reverse()
    return path, False


def _greedy_fallback(base_ter, base_occ, meta, st, memory):
    eng = Eng().setup_flat(base_ter, base_occ, meta)
    eng.load(st)
    gates = st[4]
    fields = _route_fields(base_ter, base_occ, meta, gates, eng.plates)
    pushf = [_push_field(base_ter, base_occ, meta, p, gates, True) for p in meta["plates"]]
    gtype, gcell, extra = _select_goal(base_ter, base_occ, meta, st, fields, eng.plates)
    if gtype == "pit":
        extra["pit_field"] = _push_field(base_ter, base_occ, meta, gcell, gates, eng.plates)
    if gtype == "switch" or (gtype == "cell" and gcell not in (meta["k1"], meta["k2"], meta["v"])):
        gflds = {}
        for gf in (False, True):
            for pf in (False, True):
                gflds[(gf, pf)] = _bfs_field(base_ter, base_occ, gcell, gf, pf)
        extra["goal_fields"] = gflds

    def hval(e):
        nst = e.state()
        return _heuristic(nst, gtype, gcell, fields, pushf, meta, nst[4], e.plates, extra)

    best_a = "WAIT"
    best_score = 1e18
    for a in VALID_ACTIONS:
        e1 = eng.clone()
        e1.load(st)
        s1 = e1.step(a)
        if s1 == "DEAD":
            continue
        if s1 == "CLEARED":
            return a
        h1 = hval(e1)
        two_ok = False
        best_h2 = 1e18
        for a2 in VALID_ACTIONS:
            e2 = e1.clone()
            s2 = e2.step(a2)
            if s2 == "DEAD":
                continue
            if s2 == "CLEARED":
                return a
            two_ok = True
            h2 = hval(e2)
            if h2 < best_h2:
                best_h2 = h2
        score = h1 + (0.1 * best_h2 if two_ok else 500) + (100 - e1.hp) * 2
        if score < best_score:
            best_score = score
            best_a = a
    return best_a


def decide_action(state: dict, memory: dict) -> str:
    try:
        return _decide(state, memory)
    except Exception:
        try:
            hero = state.get("hero") or {}
            turn = state.get("turn", 1)
            if turn % 3 == 0 or turn % 4 == 0:
                warns = state.get("laser_warnings") or []
                hx, hy = hero.get("x", 2), hero.get("y", 13)
                if any(w["x"] == hx and w["y"] == hy for w in warns):
                    for d in DIR_NAMES:
                        dx, dy = DIRS[d]
                        nx, ny = hx + dx, hy + dy
                        if in_bounds(nx, ny) and not any(
                                w["x"] == nx and w["y"] == ny for w in warns):
                            return "MOVE_" + d
            return "WAIT"
        except Exception:
            return "WAIT"


def _decide(state, memory):
    base_ter, base_occ, meta, st = _ingest(state, memory)
    turn = st[5]
    eng = Eng().setup_flat(base_ter, base_occ, meta)
    eng.load(st)
    actual_key = eng.key()
    plan = memory.get("plan")
    pkeys = memory.get("pkeys")
    pidx = memory.get("pidx", 0)
    if plan and pkeys and 0 < pidx < len(plan):
        if pkeys[pidx - 1] == actual_key:
            a = plan[pidx]
            memory["pidx"] = pidx + 1
            if a == "BOMB":
                mb = memory.get("my_bombs") or []
                mb.append((st[1] * GRID_WIDTH + st[0], turn + 3))
                memory["my_bombs"] = mb
            if a not in VALID_ACTIONS:
                return "WAIT"
            return a
    budget = 1.55 if turn == 0 else 0.36
    path, complete = _search(base_ter, base_occ, meta, st, budget, memory)
    if not path:
        a = _greedy_fallback(base_ter, base_occ, meta, st, memory)
        memory["plan"] = None
        memory["pkeys"] = None
        memory["pidx"] = 0
        if a == "BOMB":
            mb = memory.get("my_bombs") or []
            mb.append((st[1] * GRID_WIDTH + st[0], turn + 3))
            memory["my_bombs"] = mb
        return a
    # 计算计划每步期望状态键（用于承诺执行与失配检测）
    e = Eng().setup_flat(base_ter, base_occ, meta)
    e.load(st)
    keys = []
    safe_path = path
    for i, a in enumerate(path):
        e.step(a)
        if e.status == "DEAD":
            safe_path = path[:i]
            break
        keys.append(e.key())
        if e.status != "ALIVE":
            break
    path = safe_path
    if not path:
        a = _greedy_fallback(base_ter, base_occ, meta, st, memory)
        memory["plan"] = None
        memory["pkeys"] = None
        memory["pidx"] = 0
        if a == "BOMB":
            mb = memory.get("my_bombs") or []
            mb.append((st[1] * GRID_WIDTH + st[0], turn + 3))
            memory["my_bombs"] = mb
        return a
    memory["plan"] = path
    memory["pkeys"] = keys
    memory["pidx"] = 1
    a = path[0]
    if a == "BOMB":
        mb = memory.get("my_bombs") or []
        mb.append((st[1] * GRID_WIDTH + st[0], turn + 3))
        memory["my_bombs"] = mb
    if a not in VALID_ACTIONS:
        return "WAIT"
    return a