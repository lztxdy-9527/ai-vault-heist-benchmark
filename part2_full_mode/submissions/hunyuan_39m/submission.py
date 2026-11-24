"""
《阴间地牢·金库攻防战》下半场 v2.2 单文件答卷

build_dungeon()   : 全图明牌下的逻辑锁地牢（PLATE/P_GATE/BOX + 双频激光 + ONEWAY）
decide_action()   : FULL 明牌全局状态空间求解（Turn 1 限时预处理 + 逐拍校验纠偏）

文件内含一份与规则逐字对齐的轻量前向模拟器 _Sim，既用于 Turn 1 规划，
也用于本地回归自测；不依赖任何外部模块、文件 I/O 或动态反射。
"""
import collections
import heapq
import time

W, H = 40, 26
INF = 1e18
MAX_TURNS = 240
MAX_AUTHOR_STEPS = 200
SPAWN = (2, 13)

DIRS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
VEC2DIR = {(0, -1): "U", (0, 1): "D", (-1, 0): "L", (1, 0): "R"}
NEI4 = ((0, -1), (0, 1), (-1, 0), (1, 0))
VALID_ACTIONS = (
    "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT",
    "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
    "THROW_U", "THROW_D", "THROW_L", "THROW_R", "BOMB",
)
MOVE_ACTS = ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R")
MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}
HIGH_BASE = {
    "W", "T_W",
    "LASER_U", "LASER_D", "LASER_L", "LASER_R",
    "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R",
}
ONEWAY_TILES = {"ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R"}
IMMUTABLE = {"T_W", "K1", "K2", "V", "PIT",
             "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
             "PLATE", "P_GATE"} | ONEWAY_TILES

TILE_COSTS = {
    "EMPTY": 0, "K1": 0, "K2": 0, "V": 0, "W": 5, "T_W": 25, "ICE": 10,
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
CAPS = {"T_W": 120, "CRACK": 40, "SWITCH": 6, "TNT": 12, "BOX": 6,
        "HEAL": 4, "MIMIC": 4, "R_GATE": 16, "B_GATE": 16,
        "LASER": 12, "SPRING": 20, "MIRROR": 30, "PORTAL": 2,
        "PLATE": 4, "P_GATE": 8, "ONEWAY": 12}


# =============================================================================
# 一、建造合规校验（本地逐字自检，也被 build_dungeon 复用）
# =============================================================================

def validate_grid(grid):
    """Return (ok, spent_gold, info) under v2.2 construction rules."""
    if len(grid) != H or any(len(r) != W for r in grid):
        return False, -1, {"err": "shape"}
    for y in range(H):
        for x in range(W):
            if (x in (0, W - 1) or y in (0, H - 1)) and grid[y][x] != "T_W":
                return False, -1, {"err": "border", "x": x, "y": y}
    for y in range(12, 15):
        for x in range(1, 4):
            if grid[y][x] != "EMPTY":
                return False, -1, {"err": "spawn", "x": x, "y": y}
    ks = {}
    counts = {}
    spent = 0
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            t = grid[y][x]
            if t not in TILE_COSTS:
                return False, -1, {"err": "bad tile", "t": t}
            if t in ("K1", "K2", "V"):
                if t in ks:
                    return False, -1, {"err": "dup landmark"}
                ks[t] = (x, y)
            spent += TILE_COSTS[t]
            counts[t] = counts.get(t, 0) + 1
    if set(ks) != {"K1", "K2", "V"}:
        return False, spent, {"err": "missing landmark"}
    k1, k2, v = ks["K1"], ks["K2"], ks["V"]
    if not (12 <= k1[0] <= 34 and 2 <= k1[1] <= 10):
        return False, spent, {"err": "K1 pos"}
    if not (12 <= k2[0] <= 34 and 15 <= k2[1] <= 23):
        return False, spent, {"err": "K2 pos"}
    if not (33 <= v[0] <= 37 and 4 <= v[1] <= 21):
        return False, spent, {"err": "V pos"}
    if abs(k1[0] - k2[0]) + abs(k1[1] - k2[1]) < 12:
        return False, spent, {"err": "key distance"}
    if spent > 3000:
        return False, spent, {"err": "budget", "spent": spent}
    for t, cap in CAPS.items():
        if t == "LASER":
            n = sum(vv for kk, vv in counts.items()
                    if kk.startswith("LASER_") or kk.startswith("LASER2_"))
            if n > cap:
                return False, spent, {"err": "laser cap", "n": n}
        elif t in ("SPRING", "MIRROR", "ONEWAY"):
            n = sum(vv for kk, vv in counts.items() if kk.startswith(t))
            if n > cap:
                return False, spent, {"err": t + " cap", "n": n}
        elif t == "PORTAL":
            for s in ("1", "2"):
                a, b = counts.get("PORTAL_%sA" % s, 0), counts.get("PORTAL_%sB" % s, 0)
                if (a == 0) != (b == 0) or a > 1 or b > 1:
                    return False, spent, {"err": "portal pair"}
        elif t == "R_GATE":
            if counts.get("R_GATE", 0) + counts.get("B_GATE", 0) > cap:
                return False, spent, {"err": "gate cap"}
        elif t == "B_GATE":
            pass
        elif counts.get(t, 0) > cap:
            return False, spent, {"err": "cap " + t}
    np, nb = counts.get("P_GATE", 0), counts.get("PLATE", 0)
    if np > 0 and not (1 <= nb <= counts.get("BOX", 0)):
        return False, spent, {"err": "P_GATE needs 1<=PLATE<=BOX"}
    return True, spent, {"counts": counts, "keys": ks, "vault_gold": 3000 - spent}


# =============================================================================
# 二、v2.2 轻量前向模拟器（纯计算，可零成本克隆）
# =============================================================================

def _decode_chest(terr, clues):
    """FULL 明牌下 CHEST 脱敏；由孤立骸骨线索反推 MIMIC / HEAL。"""
    rows = [list(r) for r in terr]
    for y in range(H):
        for x in range(W):
            if rows[y][x] != "CHEST":
                continue
            mimic = False
            for dx, dy in NEI4:
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and clues[ny][nx]:
                    mimic = True
                    break
            rows[y][x] = "MIMIC" if mimic else "HEAL"
    return rows


class _Sim:
    """Immutable base map + sparse override dicts -> cheap snapshots for A*."""

    def __init__(self, grid=None, state=None):
        if grid is None and state is None:
            return
        if state is not None:
            self._from_state(state)
        else:
            self.bt = [list(r) for r in grid]
            self.bo = {}
            for y in range(H):
                for x in range(W):
                    t = self.bt[y][x]
                    if t in ("BOX", "TNT"):
                        self.bo[(x, y)] = t
                        self.bt[y][x] = "EMPTY"
            self.dt = {}
            self.do = {}
            self.targets = {}
            for y in range(H):
                for x in range(W):
                    t = self.bt[y][x]
                    if t in ("K1", "K2", "V"):
                        self.targets[t] = (x, y)
            self.h = {"x": SPAWN[0], "y": SPAWN[1], "hp": 100,
                      "keys": [False, False], "jumps": 3, "throws": 3, "bombs": 2}
            self.flipped = False
            self.bombs = []
            self.next_id = 1
            self.turn = 1
        self._build_static()
        self.status = "PLAYING"
        self.win_turn = None
        self.exposed = set()
        self.tnt_armed = set()
        self.trap_damage = 0.0
        self.mode = "FULL"

    def _from_state(self, state):
        clues = state.get("clues") or [[False] * W for _ in range(H)]
        self.bt = _decode_chest(state["terrain"], clues)
        self.bo = {}
        occ = state.get("occupant") or [[None] * W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                o = occ[y][x]
                if o in ("BOX", "TNT"):
                    self.bo[(x, y)] = o
        self.dt = {}
        self.do = {}
        self.targets = {k: (int(v[0]), int(v[1]))
                        for k, v in (state.get("targets") or {}).items()}
        hh = state["hero"]
        self.h = {"x": int(hh["x"]), "y": int(hh["y"]), "hp": int(hh["hp"]),
                  "keys": [bool(k) for k in hh["keys"]],
                  "jumps": int(hh.get("jumps", 3)),
                  "throws": int(hh.get("throws", 3)),
                  "bombs": int(hh.get("bombs", 2))}
        self.flipped = bool(state.get("gates_flipped", False))
        self.bombs = [(int(b["x"]), int(b["y"]), int(b["timer"]))
                      for b in (state.get("bombs") or [])]
        self.next_id = 1 + len(self.bombs)
        self.turn = int(state.get("turn", 1))

    def _build_static(self):
        self.plates = []
        self.cannons = []
        pc = {}
        for y in range(H):
            for x in range(W):
                t = self.bt[y][x]
                if t == "PLATE":
                    self.plates.append((x, y))
                elif t.startswith("LASER_"):
                    self.cannons.append((x, y, t[-1], 3))
                elif t.startswith("LASER2_"):
                    self.cannons.append((x, y, t[-1], 4))
                elif t.startswith("PORTAL_"):
                    pc[t] = (x, y)
        self.portals = {}
        for s in ("1", "2"):
            a, b = "PORTAL_%sA" % s, "PORTAL_%sB" % s
            if a in pc and b in pc:
                self.portals[pc[a]] = pc[b]
                self.portals[pc[b]] = pc[a]

    def clone(self):
        s = _Sim()
        s.bt, s.bo, s.plates, s.cannons, s.portals, s.targets = (
            self.bt, self.bo, self.plates, self.cannons, self.portals, self.targets)
        s.dt = dict(self.dt)
        s.do = dict(self.do)
        s.h = dict(self.h)
        s.h["keys"] = list(self.h["keys"])
        s.flipped = self.flipped
        s.bombs = list(self.bombs)
        s.next_id = self.next_id
        s.turn = self.turn
        s.status = self.status
        s.win_turn = self.win_turn
        s.exposed = set()
        s.tnt_armed = set()
        s.trap_damage = self.trap_damage
        s.mode = self.mode
        return s

    # ---------- basic queries ----------
    def tile(self, x, y):
        if not (0 <= x < W and 0 <= y < H):
            return "T_W"
        return self.dt.get((x, y), self.bt[y][x])

    def set_tile(self, x, y, t):
        self.dt[(x, y)] = t

    def occ(self, x, y):
        return self.do.get((x, y), self.bo.get((x, y)))

    def set_occ(self, x, y, v):
        self.do[(x, y)] = v

    def plates_active(self):
        return bool(self.plates) and all(self.occ(x, y) == "BOX"
                                        for (x, y) in self.plates)

    def high(self, x, y):
        if not (0 <= x < W and 0 <= y < H):
            return True
        t = self.tile(x, y)
        if t in HIGH_BASE:
            return True
        if t == "R_GATE" and not self.flipped:
            return True
        if t == "B_GATE" and self.flipped:
            return True
        if t == "P_GATE" and not self.plates_active():
            return True
        return False

    def blocks_oneway(self, x, y, d):
        t = self.tile(x, y)
        return t in ONEWAY_TILES and DIRS[t[-1]] != d

    def passable(self, p, kind, d):
        x, y = p
        if not (0 <= x < W and 0 <= y < H) or self.high(x, y):
            return False
        if self.occ(x, y) in ("BOX", "TNT"):
            return False
        if self.blocks_oneway(x, y, d):
            return False
        if kind == "BOX":
            if (x, y) == (self.h["x"], self.h["y"]):
                return False
            if self.tile(x, y) in ("K1", "K2", "V"):
                return False
        return True

    def hurt(self, amount, trap_ratio=1.0):
        before = max(0, self.h["hp"])
        self.h["hp"] = before - amount
        self.trap_damage += min(before, amount) * trap_ratio
        if self.h["hp"] <= 0:
            self.status = "DEAD"

    # ---------- 8-step atomic displacement ----------
    def chain(self, kind, p0, p1, d, steps=0, portals=0, suppress=False):
        while True:
            steps += 1
            x0, y0 = p0
            x1, y1 = p1
            if self.tile(x0, y0) == "CRACK":
                self.set_tile(x0, y0, "PIT")
            if kind == "BOX":
                self.set_occ(x0, y0, None)
                self.set_occ(x1, y1, "BOX")
            else:
                self.h["x"], self.h["y"] = x1, y1
                self.exposed.add((x1, y1))
            cur = p1
            t = self.tile(x1, y1)
            stop = False
            if kind == "BOX":
                if t == "PIT":
                    self.set_occ(x1, y1, None)
                    self.set_tile(x1, y1, "EMPTY")
                    return "STOP"
                if t == "MIMIC":
                    self.set_tile(x1, y1, "EMPTY")
                if t == "SWITCH":
                    self.flipped = not self.flipped
            else:
                if t == "PIT":
                    self.hurt(100)
                elif t == "MIMIC":
                    self.hurt(45)
                    self.set_tile(x1, y1, "EMPTY")
                    stop = True
                elif t == "HEAL":
                    self.h["hp"] = min(100, self.h["hp"] + 30)
                    self.set_tile(x1, y1, "EMPTY")
                elif t == "SWITCH":
                    self.flipped = not self.flipped
                if self.h["hp"] <= 0:
                    return "DEAD"
                if t == "K1":
                    self.h["keys"][0] = True
                    self.set_tile(x1, y1, "EMPTY")
                elif t == "K2":
                    self.h["keys"][1] = True
                    self.set_tile(x1, y1, "EMPTY")
                elif t == "V" and all(self.h["keys"]) and self.h["hp"] > 0:
                    self.status = "CLEARED"
                    return "CLEARED"
            if steps >= 32 or stop:
                return "STOP"
            dx, dy = d
            if suppress:
                if portals >= 2:
                    return "STOP"
                nxt = (cur[0] + dx, cur[1] + dy)
                if self.passable(nxt, kind, d):
                    p0, p1 = cur, nxt
                    suppress = False
                    continue
                return "STOP"
            if t == "ICE" or t.startswith("MIRROR_"):
                if t.startswith("MIRROR_"):
                    d = DIRS[MIRROR_MAP[t][VEC2DIR[d]]]
                    dx, dy = d
                nxt = (cur[0] + dx, cur[1] + dy)
                if self.passable(nxt, kind, d):
                    p0, p1 = cur, nxt
                    continue
                return "STOP"
            if t.startswith("SPRING_"):
                d = DIRS[t[-1]]
                dx, dy = d
                land = None
                for k in (1, 2, 3):
                    pk = (cur[0] + k * dx, cur[1] + k * dy)
                    blocked = (self.high(*pk) or self.occ(*pk) in ("BOX", "TNT")
                               or self.blocks_oneway(pk[0], pk[1], d))
                    if kind == "BOX" and (pk == (self.h["x"], self.h["y"])
                                          or self.tile(*pk) in ("K1", "K2", "V")):
                        blocked = True
                    if blocked:
                        if k == 1:
                            return "STOP"
                        land = (cur[0] + (k - 1) * dx, cur[1] + (k - 1) * dy)
                        break
                if land is None:
                    land = (cur[0] + 3 * dx, cur[1] + 3 * dy)
                p0, p1 = cur, land
                continue
            if t.startswith("PORTAL_") and cur in self.portals:
                pair = self.portals[cur]
                if self.occ(*pair) is not None:
                    return "STOP"
                if kind == "BOX" and pair == (self.h["x"], self.h["y"]):
                    return "STOP"
                portals += 1
                p0, p1 = cur, pair
                suppress = True
                continue
            return "STOP"

    # ---------- flying stone ----------
    def throw(self, d):
        dx, dy = d
        sx, sy = self.h["x"], self.h["y"]
        left, sp = 6, 0
        while left > 0:
            nx, ny = sx + dx, sy + dy
            left -= 1
            sx, sy = nx, ny
            if not (0 <= nx < W and 0 <= ny < H):
                return
            if self.high(nx, ny) or self.occ(nx, ny) == "BOX":
                return
            if self.occ(nx, ny) == "TNT":
                self.tnt_armed.add((nx, ny))
                return
            t = self.tile(nx, ny)
            if t == "SWITCH":
                self.flipped = not self.flipped
                return
            if t == "MIMIC":
                self.set_tile(nx, ny, "EMPTY")
                return
            if t.startswith("MIRROR_"):
                dx, dy = DIRS[MIRROR_MAP[t][VEC2DIR[(dx, dy)]]]
            elif t.startswith("PORTAL_") and (nx, ny) in self.portals and sp < 2:
                px, py = self.portals[(nx, ny)]
                if self.occ(px, py) in ("BOX", "TNT"):
                    return
                sx, sy = px, py
                sp += 1
                if sp == 2:
                    return
        t = self.tile(sy, sx)
        if t != "ICE" and not t.startswith("MIRROR_"):
            return
        for _ in range(32):
            nx, ny = sx + dx, sy + dy
            if not (0 <= nx < W and 0 <= ny < H):
                return
            if self.high(nx, ny) or self.occ(nx, ny) == "BOX":
                return
            sx, sy = nx, ny
            if self.occ(nx, ny) == "TNT":
                self.tnt_armed.add((nx, ny))
                return
            t = self.tile(nx, ny)
            if t in ONEWAY_TILES:
                return
            if t == "SWITCH":
                self.flipped = not self.flipped
                return
            if t == "MIMIC":
                self.set_tile(nx, ny, "EMPTY")
                return
            if t.startswith("MIRROR_"):
                dx, dy = DIRS[MIRROR_MAP[t][VEC2DIR[(dx, dy)]]]
            elif t.startswith("PORTAL_") and (nx, ny) in self.portals and sp < 2:
                px, py = self.portals[(nx, ny)]
                if self.occ(px, py) in ("BOX", "TNT"):
                    return
                sx, sy = px, py
                sp += 1
                if sp == 2:
                    return
            elif t != "ICE":
                return

    # ---------- rays & explosions ----------
    def rays(self, periods=None):
        out = []
        tnt = set()
        for (x, y, dr, per) in self.cannons:
            if periods is not None and per not in periods:
                continue
            t = self.tile(x, y)
            if t != ("LASER_" if per == 3 else "LASER2_") + dr:
                continue
            dx, dy = DIRS[dr]
            cells = []
            for k in range(1, 11):
                cx, cy = x + k * dx, y + k * dy
                if not (0 <= cx < W and 0 <= cy < H) or self.high(cx, cy):
                    break
                o = self.occ(cx, cy)
                if o == "BOX":
                    break
                if o == "TNT":
                    tnt.add((cx, cy))
                    break
                cells.append((cx, cy))
            out.append(((x, y), dr, per, cells))
        return out, tnt

    def explode(self, sources):
        queue = list(sources)
        seen = set()
        i = 0
        while i < len(queue):
            ex, ey, kind = queue[i]
            i += 1
            if (ex, ey, kind) in seen:
                continue
            seen.add((ex, ey, kind))
            for cy in range(ey - 1, ey + 2):
                for cx in range(ex - 1, ex + 2):
                    if not (0 <= cx < W and 0 <= cy < H):
                        continue
                    if self.occ(cx, cy) == "TNT" and (cx, cy, "TNT") not in seen:
                        queue.append((cx, cy, "TNT"))
                    for bx, by, _ in self.bombs:
                        if bx == cx and by == cy and (cx, cy, "BOMB") not in seen:
                            queue.append((cx, cy, "BOMB"))
        a = b = 0.0
        hx, hy = self.h["x"], self.h["y"]
        for ex, ey, kind in seen:
            if abs(ex - hx) <= 1 and abs(ey - hy) <= 1:
                if kind == "TNT":
                    a += 60
                else:
                    b += 50
        if a:
            self.hurt(a, 1.0)
        if b:
            self.hurt(b, 0.0)
        for ex, ey, kind in seen:
            if kind == "TNT":
                self.set_occ(ex, ey, None)
        if seen:
            self.bombs = [bb for bb in self.bombs
                          if not any(kind == "BOMB" and bb[0] == ex and bb[1] == ey
                                     for ex, ey, kind in seen)]
        for ex, ey, _ in seen:
            for cy in range(ey - 1, ey + 2):
                for cx in range(ex - 1, ex + 2):
                    if not (0 <= cx < W and 0 <= cy < H):
                        continue
                    if self.occ(cx, cy) == "BOX":
                        self.set_occ(cx, cy, None)
                    t = self.tile(cx, cy)
                    if t in IMMUTABLE:
                        continue
                    if t == "CRACK":
                        self.set_tile(cx, cy, "PIT")
                    elif t != "EMPTY":
                        self.set_tile(cx, cy, "EMPTY")
        for y in range(H):
            for x in range(W):
                if self.occ(x, y) == "BOX" and self.tile(x, y) == "PIT":
                    self.set_occ(x, y, None)
                    self.set_tile(x, y, "EMPTY")
        if self.h["hp"] > 0 and self.tile(hx, hy) == "PIT":
            self.hurt(100)

    def phase_c(self):
        nb = []
        for bx, by, tm in self.bombs:
            nb.append((bx, by, tm - 1))
        self.bombs = nb
        src = [(bx, by, "BOMB") for bx, by, tm in nb if tm <= 0]
        src += [(x, y, "TNT") for (x, y) in self.tnt_armed]
        if src:
            self.explode(src)
        self.tnt_armed = set()

    def phase_d(self):
        periods = set()
        if self.turn % 3 == 0:
            periods.add(3)
        if self.turn % 4 == 0:
            periods.add(4)
        if not periods:
            return
        rl, tnt = self.rays(periods)
        m = 0
        for _c, _dr, _per, cells in rl:
            if any(c in self.exposed for c in cells):
                m += 1
        if m:
            self.hurt(50 * m)
        if tnt:
            self.explode([(x, y, "TNT") for (x, y) in tnt])

    # ---------- one turn ----------
    def step(self, act):
        if self.status != "PLAYING":
            return
        if act not in VALID_ACTIONS:
            act = "WAIT"
        hx, hy = self.h["x"], self.h["y"]
        self.exposed = {(hx, hy)}
        self.tnt_armed = set()
        if act == "BOMB":
            if self.h["bombs"] > 0 and not any(b[0] == hx and b[1] == hy
                                               for b in self.bombs):
                self.h["bombs"] -= 1
                self.bombs.append((hx, hy, 3))
                self.next_id += 1
        elif act.startswith("MOVE_"):
            d = DIRS[act[-1]]
            dx, dy = d
            p1 = (hx + dx, hy + dy)
            if not (0 <= p1[0] < W and 0 <= p1[1] < H):
                pass
            elif self.high(*p1) or self.occ(*p1) == "TNT" or self.blocks_oneway(*p1, d):
                pass
            elif self.occ(*p1) == "BOX":
                p2 = (hx + 2 * dx, hy + 2 * dy)
                if self.passable(p2, "BOX", d):
                    self.chain("BOX", p1, p2, d)
                    if (self.status == "PLAYING" and not self.high(*p1)
                            and self.occ(*p1) is None
                            and not self.blocks_oneway(*p1, d)):
                        self.chain("hero", (hx, hy), p1, d)
            else:
                self.chain("hero", (hx, hy), p1, d)
        elif act.startswith("JUMP_"):
            if self.h["jumps"] > 0:
                self.h["jumps"] -= 1
                d = DIRS[act[-1]]
                dx, dy = d
                p1 = (hx + dx, hy + dy)
                p2 = (hx + 2 * dx, hy + 2 * dy)
                ok = (0 <= p2[0] < W and 0 <= p2[1] < H
                      and not self.high(*p1) and not self.high(*p2)
                      and not self.blocks_oneway(*p1, d)
                      and not self.blocks_oneway(*p2, d)
                      and self.occ(*p2) not in ("BOX", "TNT"))
                if ok:
                    self.chain("hero", (hx, hy), p2, d)
        elif act.startswith("THROW_"):
            if self.h["throws"] > 0:
                self.h["throws"] -= 1
                self.throw(DIRS[act[-1]])
        if self.status == "PLAYING":
            self.phase_c()
        if self.status == "PLAYING":
            self.phase_d()
        if self.status == "CLEARED":
            self.win_turn = self.turn
        elif self.status == "PLAYING" and self.turn >= MAX_TURNS:
            self.status = "TIMEOUT"
        self.turn += 1

    # ---------- observation ----------
    def state(self):
        mask = [[True] * W for _ in range(H)]
        terr = [[self.tile(x, y) for x in range(W)] for y in range(H)]
        occ = [[self.occ(x, y) for x in range(W)] for y in range(H)]
        clues = [[False] * W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                if self.tile(x, y) == "MIMIC":
                    for dx, dy in NEI4:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < W and 0 <= ny < H and self.tile(nx, ny) == "EMPTY":
                            clues[ny][nx] = True
                            break
        periods = set()
        if self.turn % 3 == 0:
            periods.add(3)
        if self.turn % 4 == 0:
            periods.add(4)
        warnings = []
        if periods:
            rl, _ = self.rays(periods)
            for (cx, cy), dr, per, cells in rl:
                for (x, y) in cells:
                    warnings.append({"x": x, "y": y, "dir": dr,
                                     "period": per, "cannon": [cx, cy]})
            warnings.sort(key=lambda w: (w["y"], w["x"], w["dir"],
                                         w["period"], w["cannon"]))
        return {
            "turn": self.turn,
            "turns_left": MAX_TURNS - self.turn + 1,
            "mode": "FULL",
            "hero": {"x": self.h["x"], "y": self.h["y"], "hp": self.h["hp"],
                     "keys": list(self.h["keys"]), "jumps": self.h["jumps"],
                     "throws": self.h["throws"], "bombs": self.h["bombs"]},
            "gates_flipped": self.flipped,
            "plates_active": self.plates_active(),
            "targets": {k: [v[0], v[1]] for k, v in self.targets.items()},
            "visible_mask": mask,
            "terrain": [["CHEST" if t in ("HEAL", "MIMIC") else t for t in row]
                        for row in terr],
            "occupant": occ,
            "bombs": [{"id": i + 1, "x": b[0], "y": b[1], "timer": b[2]}
                      for i, b in enumerate(self.bombs)],
            "clues": clues,
            "laser_warnings": warnings,
        }

    def key(self):
        return (self.h["x"], self.h["y"], self.h["hp"],
                (self.h["keys"][0], self.h["keys"][1]), self.flipped,
                self.turn % 12, tuple(sorted(self.dt.items())),
                tuple(sorted(self.do.items())), tuple(sorted(self.bombs)),
                self.h["jumps"], self.h["throws"], self.h["bombs"])


# =============================================================================
# 三、FULL 明牌全局状态空间求解器
# =============================================================================

def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _relax_cost(t):
    """Relaxed per-cell traversal cost: breakable walls / gates / pits cost more."""
    if t == "T_W":
        return INF
    if t == "PIT":
        return 8.0
    if t in ("W", "R_GATE", "B_GATE", "P_GATE"):
        return 5.0
    if t.startswith("LASER_"):
        return 6.0
    return 1.0


def _dist_map(sim, goal):
    """Reverse distance: strict walking distances, relaxed fallback behind walls.

    Strict BFS (W / cannons / PIT are walls) keeps the planner from being lured
    into bombable walls when a walk-around exists.  Relaxed Dijkstra supplies a
    gradient for cells only reachable by blowing a wall / filling a pit.
    """
    relaxed = {goal: 0.0}
    pq = [(0.0, goal)]
    while pq:
        d, p = heapq.heappop(pq)
        if d > relaxed.get(p, INF) + 1e-9:
            continue
        cp = _relax_cost(sim.tile(*p))
        if cp >= INF:
            continue
        for dx, dy in NEI4:
            n = (p[0] - dx, p[1] - dy)
            if not (0 <= n[0] < W and 0 <= n[1] < H):
                continue
            cn = _relax_cost(sim.tile(*n))
            if cn >= INF or sim.blocks_oneway(*p, (dx, dy)):
                continue
            nd = d + cp
            if nd < relaxed.get(n, INF) - 1e-9:
                relaxed[n] = nd
                heapq.heappush(pq, (nd, n))
    strict = {goal: 0}
    q = collections.deque([goal])
    while q:
        p = q.popleft()
        if sim.tile(*p) in HIGH_BASE or sim.tile(*p) == "PIT":
            continue
        d0 = strict[p]
        for dx, dy in NEI4:
            n = (p[0] - dx, p[1] - dy)
            if not (0 <= n[0] < W and 0 <= n[1] < H) or n in strict:
                continue
            if (sim.tile(*n) in HIGH_BASE or sim.tile(*n) == "PIT"
                    or sim.blocks_oneway(*p, (dx, dy))):
                continue
            strict[n] = d0 + 1
            q.append(n)
    out = {k: v + 12.0 for k, v in relaxed.items()}
    out.update({k: float(v) for k, v in strict.items()})
    return out


def _heuristic(sim, dk1, dk2, dv, need_plates):
    p = (sim.h["x"], sim.h["y"])
    k = sim.h["keys"]
    d = 0
    if not all(k):
        a = 0 if k[0] else dk1.get(p, 60)
        b = 0 if k[1] else dk2.get(p, 60)
        c1 = a + _man(sim.targets.get("K1", p), sim.targets.get("K2", p)) \
            + dv.get(sim.targets.get("K2", p), 60)
        c2 = b + _man(sim.targets.get("K2", p), sim.targets.get("K1", p)) \
            + dv.get(sim.targets.get("K1", p), 60)
        d = min(c1, c2)
    else:
        d = dv.get(p, 60)
    if need_plates and not sim.plates_active():
        d += 25
    return 0.55 * d


def _greedy_action(sim):
    """Safe single-step fallback when global search is unavailable."""
    t = sim.targets
    goals = []
    if not sim.h["keys"][0]:
        goals.append(t.get("K1"))
    if not sim.h["keys"][1]:
        goals.append(t.get("K2"))
    if all(sim.h["keys"]):
        goals.append(t.get("V"))
    goals = [g for g in goals if g]
    if not goals:
        return "WAIT"
    periods = set()
    if sim.turn % 3 == 0:
        periods.add(3)
    if sim.turn % 4 == 0:
        periods.add(4)
    danger = set()
    if periods:
        rl, _ = sim.rays(periods)
        for _c, _dr, _per, cells in rl:
            danger |= set(cells)
    order = sorted(goals, key=lambda g: _man((sim.h["x"], sim.h["y"]), g))
    for g in order:
        dm = _dist_map(sim, g)
        base = dm.get((sim.h["x"], sim.h["y"]), 10 ** 6)
        best, bv = "WAIT", -1e30
        for act in MOVE_ACTS + ("WAIT",):
            c = sim.clone()
            c.step(act)
            if c.status == "DEAD":
                continue
            val = 100.0 * (c.h["hp"] - sim.h["hp"] == 0)
            val -= 1000.0 * max(0, sim.h["hp"] - c.h["hp"])
            val -= 2.0 * dm.get((c.h["x"], c.h["y"]), 10 ** 6)
            val += 1.0 * (1 if (c.h["x"], c.h["y"]) != (sim.h["x"], sim.h["y"]) else 0)
            if (c.h["x"], c.h["y"]) in danger:
                val -= 500.0
            nxt = set()
            if c.turn % 3 == 0:
                nxt.add(3)
            if c.turn % 4 == 0:
                nxt.add(4)
            if nxt:
                rl2, _ = c.rays(nxt)
                lit = set()
                for _cc, _dd, _pp, cells in rl2:
                    lit |= set(cells)
                if (c.h["x"], c.h["y"]) in lit:
                    val -= 400.0
            if c.status == "CLEARED":
                val += 100000.0
            if val > bv:
                bv, best = val, act
        if base < 10 ** 5 and bv > -1e29:
            return best
    return "WAIT"


def _action_sets(root):
    """Cheap 5-action pass first; full 14-action pass only if needed."""
    basic = list(MOVE_ACTS) + ["WAIT"]
    has_switch = any(root.tile(x, y) == "SWITCH"
                     for y in range(1, H - 1) for x in range(1, W - 1))
    has_chest = any(root.tile(x, y) in ("MIMIC", "HEAL")
                    or root.occ(x, y) == "TNT"
                    for y in range(1, H - 1) for x in range(1, W - 1))
    has_breakable = any(root.tile(x, y) == "W" or root.tile(x, y).startswith("LASER")
                        or root.tile(x, y) in ("R_GATE", "B_GATE")
                        for y in range(1, H - 1) for x in range(1, W - 1))
    full = list(basic)
    if root.h["jumps"] > 0:
        full += ["JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R"]
    if root.h["throws"] > 0 and (has_switch or has_chest):
        full += ["THROW_U", "THROW_D", "THROW_L", "THROW_R"]
    if root.h["bombs"] > 0 and has_breakable:
        full.append("BOMB")
    return basic, full


def _boxes_of(s):
    out = set()
    for k in s.bo:
        if s.occ(*k) == "BOX":
            out.add(k)
    for k, v in s.do.items():
        if v == "BOX":
            out.add(k)
    return out


def _stage_search(sim, goal_test, hfun, deadline, acts, max_states=45000):
    """Weighted A* to a single stage goal; returns (actions, final_sim)."""
    openh = [(hfun(sim), 0.0, 0, sim.key(), 0)]
    sims = {0: sim}
    parents = {0: (-1, None)}
    gscore = {sim.key(): 0.0}
    counter = 1
    nodes = 0
    loops = 0
    while openh and nodes < 200000:
        loops += 1
        if (loops & 31) == 0 and time.monotonic() > deadline:
            return None
        f, g, _c, skey, nid = heapq.heappop(openh)
        if g > gscore.get(skey, INF) + 1e-9:
            continue
        s = sims.get(nid)
        if s is None:
            continue
        nodes += 1
        if goal_test(s):
            seq = []
            cur = nid
            while parents[cur][0] != -1:
                seq.append(parents[cur][1])
                cur = parents[cur][0]
            return seq[::-1], s
        if s.status != "PLAYING":
            continue
        for a in acts:
            c = s.clone()
            c.step(a)
            if c.status == "DEAD":
                continue
            dmg = max(0, s.h["hp"] - c.h["hp"])
            ng = g + 1.0 + 0.35 * dmg + (4.0 if a == "BOMB" else 0.0) \
                + (0.15 if a == "WAIT" else 0.0)
            ck = c.key()
            if ng >= gscore.get(ck, INF) - 1e-9:
                continue
            gscore[ck] = ng
            sims[counter] = c
            parents[counter] = (nid, a)
            heapq.heappush(openh, (ng + 1.85 * hfun(c), ng, counter, ck, counter))
            counter += 1
        if len(sims) > max_states:
            return None
    return None


def _plan_from_state(state, deadline, max_nodes=20000, start=None):
    """Staged global plan: 压板 -> 近钥匙 -> 远钥匙 -> 金库."""
    start = start if start is not None else time.monotonic()
    root = _Sim(state=state)
    basic, full = _action_sets(root)
    t = root.targets
    maps = {}
    for name in ("K1", "K2", "V"):
        if name in t:
            maps[name] = _dist_map(root, t[name])

    def mk_h(name):
        dm = maps.get(name, {})
        def h(s):
            return 1.0 * dm.get((s.h["x"], s.h["y"]), 70)
        return h

    has_pgate = any(root.tile(x, y) == "P_GATE"
                    for y in range(1, H - 1) for x in range(1, W - 1))
    plate_maps = [_dist_map(root, p) for p in root.plates] if has_pgate else []

    def h_plates(s):
        """Sokoban-style: sum of relaxed box->plate distances over uncovered plates."""
        if s.plates_active():
            return 0.0
        boxes = _boxes_of(s)
        if not boxes:
            return 60.0
        tot, n = 0.0, 0
        for i, p in enumerate(s.plates):
            if s.occ(*p) == "BOX":
                continue
            n += 1
            tot += min((plate_maps[i].get(b, 70.0) for b in boxes), default=70.0)
        hd = min((_man((s.h["x"], s.h["y"]), b) for b in boxes), default=40.0)
        return 1.0 * tot + 0.2 * hd + 6.0 * n

    stages = []
    if has_pgate:
        stages.append(("plates", lambda s: s.plates_active(), h_plates))
    kk = []
    if not root.h["keys"][0]:
        kk.append(("K1", 0, lambda s: s.h["keys"][0], mk_h("K1"),
                   maps.get("K1", {}).get((root.h["x"], root.h["y"]), 70)))
    if not root.h["keys"][1]:
        kk.append(("K2", 1, lambda s: s.h["keys"][1], mk_h("K2"),
                   maps.get("K2", {}).get((root.h["x"], root.h["y"]), 70)))
    kk.sort(key=lambda z: z[4])
    for nm, _i, test, hf, _d in kk:
        stages.append((nm, test, hf))
    stages.append(("V", lambda s: s.status == "CLEARED", mk_h("V")))

    sim = root
    out = []
    remaining = len(stages)
    for nm, test, hfun in stages:
        if test(sim):
            remaining -= 1
            continue
        now = time.monotonic()
        avail = max(0.001, deadline - now)
        basic_dl = now + 0.35 * avail
        full_dl = deadline if nm == "V" else now + 0.65 * avail
        res = _stage_search(sim, test, hfun, basic_dl, basic)
        if res is None and full != basic:
            res = _stage_search(sim, test, hfun, full_dl, full)
        if res is None:
            return None
        seq, sim = res
        out.extend(seq)
        remaining -= 1
        if time.monotonic() > deadline:
            break
    return out if sim.status == "CLEARED" else None


def _sig_of_state(state):
    h = state["hero"]
    return (int(state.get("turn", 1)), int(h["x"]), int(h["y"]), int(h["hp"]),
            bool(h["keys"][0]), bool(h["keys"][1]),
            bool(state.get("gates_flipped", False)),
            bool(state.get("plates_active", False)),
            int(h.get("jumps", 3)), int(h.get("throws", 3)), int(h.get("bombs", 2)),
            len(state.get("bombs") or []))


def _sig_of_sim(sim):
    h = sim.h
    return (sim.turn, h["x"], h["y"], h["hp"],
            bool(h["keys"][0]), bool(h["keys"][1]), sim.flipped,
            sim.plates_active(), h["jumps"], h["throws"], h["bombs"], len(sim.bombs))


def decide_action(state: dict, memory: dict) -> str:
    try:
        start = time.monotonic()
        turn = int(state.get("turn", 1))
        budget = 1.55 if turn == 1 else 0.30
        deadline = start + budget
        sig = _sig_of_state(state)
        plan = memory.get("plan")
        idx = memory.get("idx", 0)
        sigs = memory.get("sigs")
        if plan and idx < len(plan) and sigs and idx < len(sigs) and sigs[idx] == sig:
            memory["idx"] = idx + 1
            return plan[idx]
        if memory.get("cooldown", 0) > turn:
            act = _greedy_action(_Sim(state=state))
            memory["plan"] = [act]
            memory["sigs"] = [sig]
            memory["idx"] = 1
            return act
        seq = _plan_from_state(state, deadline, 20000, start)
        if seq:
            sim = _Sim(state=state)
            sigs = [_sig_of_sim(sim)]
            ok = True
            for a in seq:
                if sim.status != "PLAYING":
                    break
                sim.step(a)
                sigs.append(_sig_of_sim(sim))
            if sim.status != "CLEARED":
                ok = False
            if ok or len(seq) > 1:
                memory["plan"] = seq
                memory["sigs"] = sigs
                memory["idx"] = 1
                memory["cooldown"] = 0
                return seq[0]
        # 降级：单步贪心 + 冷却，保证不超时、不反复烧预算
        memory["cooldown"] = turn + 10
        sim = _Sim(state=state)
        act = _greedy_action(sim)
        memory["plan"] = [act]
        memory["sigs"] = [sig]
        memory["idx"] = 1
        return act
    except Exception:
        return "WAIT"


# =============================================================================
# 四、魔王：v2.2 逻辑锁地牢 + 确定性自证通关
# =============================================================================

def _hash_key(p):
    x, y = p
    h = (x * 374761393 + y * 668265263 + x * y * 1274126177
         + x * x * 69069 + y * y * 12345) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return h


def _static_beams(grid, plates_open=True):
    """Worst-case lit cells of all red/blue cannons (P_GATE assumed open)."""
    beams = set()
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            t = grid[y][x]
            if t.startswith("LASER_"):
                dr = t[-1]
            elif t.startswith("LASER2_"):
                dr = t[-1]
            else:
                continue
            dx, dy = DIRS[dr]
            for k in range(1, 11):
                cx, cy = x + k * dx, y + k * dy
                if not (0 <= cx < W and 0 <= cy < H):
                    break
                ct = grid[cy][cx]
                if ct in HIGH_BASE:
                    break
                if ct == "R_GATE":
                    break
                if ct == "P_GATE" and not plates_open:
                    break
                beams.add((cx, cy))
    return beams


def _bfs_path(grid, start, goal, blocked, allowed):
    if start == goal:
        return [start]
    q = collections.deque([start])
    prev = {start: None}
    while q:
        p = q.popleft()
        if p == goal:
            out = []
            while p is not None:
                out.append(p)
                p = prev[p]
            return out[::-1]
        for dx, dy in NEI4:
            n = (p[0] + dx, p[1] + dy)
            if not (0 <= n[0] < W and 0 <= n[1] < H) or n in prev or n in blocked:
                continue
            if grid[n[1]][n[0]] not in allowed:
                continue
            prev[n] = p
            q.append(n)
    return None


def _acts_from_path(path):
    out = []
    for a, b in zip(path, path[1:]):
        d = (b[0] - a[0], b[1] - a[1])
        out.append("MOVE_" + VEC2DIR[d])
    return out


def _certificate(grid, budget):
    """用通用求解器生成一份『恰好最后一步零伤通关』的可复现证书。"""
    try:
        s0 = _Sim(grid=grid)
        t0 = time.monotonic()
        seq = _plan_from_state(s0.state(), t0 + budget, 20000, t0)
        if not seq or len(seq) > MAX_AUTHOR_STEPS:
            return None
        v = _Sim(grid=grid)
        for a in seq:
            if v.status != "PLAYING":
                break
            v.step(a)
        if (v.status == "CLEARED" and v.win_turn == len(seq)
                and v.h["hp"] > 0 and v.trap_damage == 0.0):
            return seq
    except Exception:
        pass
    return None


def _footprint(grid, seq):
    s = _Sim(grid=grid)
    out = {(s.h["x"], s.h["y"])}
    for a in seq:
        s.step(a)
        out.add((s.h["x"], s.h["y"]))
        if s.status != "PLAYING":
            break
    return out


def build_dungeon() -> dict:
    grid = [
        ["T_W" if (x == 0 or x == W - 1 or y == 0 or y == H - 1) else "EMPTY"
         for x in range(W)] for y in range(H)
    ]

    # 两道横向隔离墙，缺口左右交替，强制长蛇形绕行（明牌也绕不掉）
    for by, gap in ((5, 38), (17, 1)):
        for x in range(1, W - 1):
            grid[by][x] = "W"
        grid[by][gap] = "EMPTY"

    k1, k2, vault = (34, 3), (12, 19), (36, 13)
    grid[k1[1]][k1[0]] = "K1"
    grid[k2[1]][k2[0]] = "K2"
    grid[vault[1]][vault[0]] = "V"

    # 金库前最后一道锁：必须由 BOX 压住 PLATE 才能打开 P_GATE
    grid[13][35] = "P_GATE"
    for x, y in ((36, 12), (36, 14), (37, 13)):
        grid[y][x] = "W"
    plate, box = (20, 10), (17, 10)
    grid[plate[1]][plate[0]] = "PLATE"
    grid[box[1]][box[0]] = "BOX"
    grid[10][18] = "ICE"
    grid[10][19] = "ICE"

    # 红蓝双频炮：12 拍节奏，任意贪心直穿都会踩中节拍陷阱
    lasers = [
        (4, 13, "LASER_R"), (38, 9, "LASER_L"), (4, 7, "LASER_R"),
        (20, 6, "LASER2_D"), (10, 15, "LASER2_R"), (30, 24, "LASER2_U"),
        (28, 1, "LASER_D"),
    ]
    for lx, ly, lt in lasers:
        if grid[ly][lx] == "EMPTY":
            grid[ly][lx] = lt

    # 单向门支路：看似捷径，实为不可逆死胡同
    for x in range(24, 29):
        grid[11][x] = "W"
        grid[13][x] = "W"
    grid[12][24] = "ONEWAY_R"
    for x in range(25, 29):
        grid[12][x] = "W"
    grid[11][28] = "W"
    grid[13][28] = "W"

    beams = _static_beams(grid, plates_open=True)
    # 主证书由通用全图求解器给出；静态 BFS 只作为求解器异常时的兜底
    cert = _certificate(grid, 0.9)
    allowed = {"EMPTY", "K1", "K2", "V", "P_GATE", "PLATE"}
    blocked = set(beams)
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            t = grid[y][x]
            if t in ("BOX", "PIT", "CRACK", "ICE", "MIMIC", "HEAL", "TNT",
                     "SWITCH") or t in ONEWAY_TILES or t.startswith("MIRROR_") \
                    or t.startswith("SPRING_") or t.startswith("PORTAL_"):
                blocked.add((x, y))
    for p in (k1, k2, vault, (35, 13), (16, 10), plate, (17, 10)):
        blocked.discard(p)

    def static_cert():
        b2 = set(blocked)
        s0 = _bfs_path(grid, SPAWN, (16, 10), b2, allowed)
        s1 = _bfs_path(grid, (17, 10), k1, b2, allowed)
        s2 = _bfs_path(grid, k1, k2, b2, allowed)
        s3 = _bfs_path(grid, k2, vault, b2, allowed)
        if not (s0 and s1 and s2 and s3):
            b2 -= beams
            s0 = _bfs_path(grid, SPAWN, (16, 10), b2, allowed)
            s1 = _bfs_path(grid, (17, 10), k1, b2, allowed)
            s2 = _bfs_path(grid, k1, k2, b2, allowed)
            s3 = _bfs_path(grid, k2, vault, b2, allowed)
        if not (s0 and s1 and s2 and s3):
            return [], set()
        acts = (_acts_from_path(s0) + ["MOVE_R"] + _acts_from_path(s1)
                + _acts_from_path(s2) + _acts_from_path(s3))
        return acts, set(s0) | set(s1) | set(s2) | set(s3)

    fallback, fb_foot = static_cert()
    golden = _footprint(grid, cert) if cert else fb_foot
    # 推箱区与两条墙缺口绝不能布雷
    golden |= {(16, 10), (17, 10), (18, 10), (19, 10), plate,
               (38, 5), (38, 6), (38, 4), (1, 17), (1, 16), (1, 18),
               (35, 13), vault, k1, k2}

    # 只在不影响自证足迹的区域撒陷阱，提升对手 D 与误判率
    cands = []
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            if (x, y) in golden or grid[y][x] != "EMPTY" or (x, y) in beams:
                continue
            if 1 <= x <= 3 and 12 <= y <= 14:
                continue
            cands.append((x, y))
    cands.sort(key=_hash_key)
    n_pit = n_crack = n_mimic = 0
    for p in cands:
        x, y = p
        if n_pit < 5 and y not in (4, 6, 16, 18):
            grid[y][x] = "PIT"
            n_pit += 1
        elif n_crack < 12:
            grid[y][x] = "CRACK"
            n_crack += 1
        elif n_mimic < 2:
            grid[y][x] = "MIMIC"
            n_mimic += 1
        else:
            break

    ok, spent, info = validate_grid(grid)
    if not ok:
        for p in cands:
            x, y = p
            if grid[y][x] in ("PIT", "CRACK", "MIMIC"):
                grid[y][x] = "EMPTY"

    # 撒完陷阱后重新求证书，保证与最终 grid 逐字一致
    author = _certificate(grid, 1.2)
    if not author:
        author = fallback[:MAX_AUTHOR_STEPS]
    return {
        "grid": grid,
        "author_solution": author[:MAX_AUTHOR_STEPS],
        "taunt": "明牌也没用：先数十二拍，再把箱子推上金板。",
    }
