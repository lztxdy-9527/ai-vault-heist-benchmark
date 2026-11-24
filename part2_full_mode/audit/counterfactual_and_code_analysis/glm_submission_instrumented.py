# -*- coding: utf-8 -*-
"""
《阴间地牢·金库攻防战》下半场 FULL 明牌双重构 submission.py —— 参赛者：GLM

build_dungeon() : "CHRONOLOCK VAULT"（拍频锁金库, 2020G）
  - 双频激光 12 拍杀阵：K1 跳板湾红蓝 m=2（t%12k 齐射瞬杀）+ V 甬道红蓝交错；
  - 压板锁：3 PLATE 全部压箱才开 V 的 P_GATE；
  - 炸弹经济：K2 密室 TNT 陪绑须 1 弹爆破；双厚 W 水坝须 2 弹——勇者仅 2 弹，
    故深坑箱桥（填坑+跳跃）为过坝唯一解，全局恰好 3 跳无余量。
decide_action() : FULL 全图明牌全局求解器 —— 内嵌 v2.2 精确前向模拟器 +
  A*（动作含推箱/跳跃/炸弹/等待，模 12 时间感知去重）+ 逐拍安全校验与快速降级。
"""

import heapq
import time

GRID_W = 40
GRID_H = 26
MAX_TURNS = 240
MAX_AUTHOR_STEPS = 200

VALID_ACTIONS = frozenset([
    "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT",
    "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
    "THROW_U", "THROW_D", "THROW_L", "THROW_R", "BOMB",
])

DIRS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
DIR_CH = {(0, -1): "U", (0, 1): "D", (-1, 0): "L", (1, 0): "R"}

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

MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}

PORTAL_PAIR = {"PORTAL_1A": "PORTAL_1B", "PORTAL_1B": "PORTAL_1A",
               "PORTAL_2A": "PORTAL_2B", "PORTAL_2B": "PORTAL_2A"}

# 防爆免疫地形（爆炸不动它们）
BLAST_IMMUNE = frozenset([
    "T_W", "K1", "K2", "V", "PIT", "PLATE", "P_GATE",
    "ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R",
    "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
])


# ==============================================================================
# 参赛入口 1：魔王造图与自证函数 —— CHRONOLOCK VAULT
# ==============================================================================

def build_dungeon() -> dict:
    grid = [["EMPTY" for _ in range(GRID_W)] for _ in range(GRID_H)]
    for y in range(GRID_H):
        for x in range(GRID_W):
            if x == 0 or x == GRID_W - 1 or y == 0 or y == GRID_H - 1:
                grid[y][x] = "T_W"

    P = {}
    # ---- 地标 ----
    P[(17, 5)] = "K1"     # x∈[12,34] y∈[2,10] 合法
    P[(17, 20)] = "K2"    # y∈[15,23] 合法; |17-17|+|5-20| = 15 ≥ 12
    P[(36, 13)] = "V"     # x∈[33,37] y∈[4,21] 合法

    # ---- K1 密室：T_W 密封 + 北面深坑跃入 + 南面弹簧单向阀 + 阀前深坑 ----
    P[(16, 4)] = "T_W"; P[(18, 4)] = "T_W"; P[(17, 4)] = "PIT"
    P[(16, 5)] = "T_W"; P[(18, 5)] = "T_W"
    P[(16, 6)] = "T_W"; P[(18, 6)] = "T_W"; P[(17, 6)] = "SPRING_D"
    P[(17, 7)] = "PIT"
    # 跳板湾 (15..19,3)：红蓝双炮夹击, t%12k 齐射 100 伤瞬杀
    P[(14, 3)] = "LASER_R"
    P[(20, 3)] = "LASER2_L"
    P[(15, 4)] = "T_W"; P[(19, 4)] = "T_W"   # 湾南封口

    # ---- K2 密室：底面三 W + TNT 陪绑（错撤方向者吃 110 伤）----
    P[(16, 19)] = "T_W"; P[(17, 19)] = "T_W"; P[(18, 19)] = "T_W"
    P[(16, 20)] = "T_W"; P[(18, 20)] = "T_W"
    P[(16, 21)] = "W"; P[(17, 21)] = "W"; P[(18, 21)] = "W"
    P[(16, 22)] = "TNT"

    # ---- V 壁龛：T_W 全密封 + P_GATE ----
    P[(35, 12)] = "T_W"; P[(36, 12)] = "T_W"; P[(37, 12)] = "T_W"
    P[(37, 13)] = "T_W"
    P[(35, 14)] = "T_W"; P[(36, 14)] = "T_W"; P[(37, 14)] = "T_W"
    P[(35, 13)] = "P_GATE"

    # ---- 双厚 W 水坝（x=27,28 全高, 仅 y=13 留双深坑）----
    for y in range(1, 25):
        if y == 13:
            continue
        P[(27, y)] = "W"
        P[(28, y)] = "W"
    P[(27, 13)] = "PIT"; P[(28, 13)] = "PIT"
    P[(26, 13)] = "BOX"     # 过坝箱：推入 (27,13) 填坑

    # ---- V 甬道双频激光 ----
    P[(31, 9)] = "LASER_D"      # 红周期3: (31,10..19) ∋ (31,13)
    P[(33, 9)] = "LASER2_D"     # 蓝周期4: (33,10..19) ∋ (33,13)
    P[(33, 16)] = "LASER_U"     # 红周期3: (33,10..15) ∋ (33,13) —— 与蓝构成 t%12k 双杀
    P[(34, 16)] = "LASER2_U"    # 蓝周期4: (34,6..15) ∋ (34,13) —— 惩罚跳跃捷径

    # ---- 三压板 + 配箱 ----
    P[(5, 5)] = "PLATE"; P[(5, 7)] = "BOX"                    # A: 直推×2
    P[(25, 21)] = "PLATE"; P[(24, 21)] = "ONEWAY_R"; P[(23, 21)] = "BOX"  # B: 经单向门推×2
    P[(30, 7)] = "PLATE"; P[(30, 8)] = "ONEWAY_U"; P[(30, 9)] = "BOX"    # C: 自下而上推×2

    # ---- 诱杀撒布 ----
    P[(12, 9)] = "MIMIC"; P[(22, 17)] = "MIMIC"   # 线索位 (12,8)/(22,16) 合法
    for c in [(16, 9), (18, 9), (16, 10), (18, 10)]:
        P[c] = "CRACK"

    for (x, y), t in P.items():
        grid[y][x] = t
    for y in range(12, 15):
        for x in range(1, 4):
            grid[y][x] = "EMPTY"

    # ---- 作者自证路径（155 步逐拍验证, 末步恰达 V）----
    a = []
    a += ["MOVE_R"] * 3                 # t1-3   -> (5,13)
    a += ["MOVE_U"] * 5                 # t4-8   -> (5,8)
    a += ["MOVE_U", "MOVE_U"]           # t9-10  推箱A上压板 (5,5)
    a += ["MOVE_D"] * 12                # t11-22 -> (5,18)  (绕开 K2 壁龛)
    a += ["MOVE_R"] * 17                # t23-39 -> (22,18)
    a += ["MOVE_D"] * 3                 # t40-42 -> (22,21)
    a += ["MOVE_R", "MOVE_R"]           # t43-44 推箱B经单向门上压板 (25,21)
    a += ["MOVE_U"] * 3                 # t45-47 -> (24,18)
    a += ["MOVE_L"] * 11                # t48-58 -> (13,18)
    a += ["MOVE_U"] * 16                # t59-74 -> (13,2)
    a += ["MOVE_R"] * 4                 # t75-78 -> (17,2)
    a += ["WAIT"] * 6                   # t79-84 等待 t≡1 (mod 12)
    a += ["MOVE_D", "JUMP_D"]           # t85-86 ≡1 进湾 ≡2 跃入 K1 [跳#1]
    a += ["MOVE_D"]                     # t87    弹簧阀 -> (17,9)
    a += ["MOVE_D"] * 9                 # t88-96 -> (17,18)
    a += ["MOVE_L"] * 2                 # t97-98 -> (15,18)
    a += ["MOVE_D"] * 5                 # t99-103 -> (15,23)
    a += ["MOVE_R"] * 2                 # t104-105 -> (17,23)
    a += ["MOVE_U"]                     # t106   -> (17,22) 炸点
    a += ["BOMB", "MOVE_D", "MOVE_D",   # t107-109 放弹南撤2格引爆
          "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U"]  # t110-113 破墙取 K2
    a += ["MOVE_D"] * 3                 # t114-116 -> (17,23)
    a += ["MOVE_R"] * 9                 # t117-125 -> (26,23)
    a += ["MOVE_U"] * 9                 # t126-134 -> (26,14)
    a += ["MOVE_L", "MOVE_U"]           # t135-136 -> (25,13)
    a += ["MOVE_R", "MOVE_R"]           # t137-138 推箱D填坑+踏上 (27,13)
    a += ["JUMP_R"]                     # t139   跃过 (28,13) -> (29,13) [跳#2]
    a += ["MOVE_R"]                     # t140   -> (30,13)
    a += ["MOVE_U"] * 3                 # t141-143 -> (30,10)
    a += ["MOVE_U", "MOVE_U"]           # t144-145 推箱C经单向门上压板 (30,7) —— 三板齐, P_GATE 开
    a += ["MOVE_D"] * 5                 # t146-150 -> (30,13)
    # t151 ≡ 7 (mod 12)：R(31) t151%3=1, R(32) t152%3=2, JUMP(34) t153%4=1, R,R,V
    a += ["MOVE_R", "MOVE_R", "JUMP_R", "MOVE_R", "MOVE_R"]  # t151-155 [跳#3] 末步踏上 V 通关!

    return {
        "taunt": "明牌？正合我意——看得见的是路，看不见的是拍子。",
        "grid": grid,
        "author_solution": a,
    }


# ==============================================================================
# v2.2 精确前向模拟器（世界 = 静态基图 + 小型覆盖层, 求解器与自证共用）
# ==============================================================================

class _World:

    def __init__(self, base, ovl, occ, hx, hy, hp, k1, k2, jumps, bombs,
                 gates, bl, turn, status, cannons=None, plates=None, portals=None):
        self.base = base; self.ovl = ovl; self.occ = occ
        self.hx = hx; self.hy = hy; self.hp = hp
        self.k1 = k1; self.k2 = k2; self.jumps = jumps; self.bombs = bombs
        self.gates = gates; self.bl = bl; self.turn = turn; self.status = status
        self.cannons = cannons if cannons is not None else []
        self.plates = plates if plates is not None else []
        self.portals = portals if portals is not None else {}
        self._ck = None
        self._zk = None

    def key(self):
        if self._ck is None:
            self._ck = (self.hx, self.hy, self.turn % 12, self.k1, self.k2,
                        self.jumps, self.bombs, self.gates, self.hp,
                        tuple(sorted(self.ovl.items())),
                        tuple(sorted(self.occ.items())),
                        tuple(self.bl))
        return self._ck

    def plates_active(self):
        if not self.plates:
            return False
        for p in self.plates:
            if self.occ.get(p) != "BOX":
                return False
        return True

    def t(self, x, y):
        o = self.ovl.get((x, y))
        if o is not None:
            return o
        return self.base[y][x]

    def is_wall(self, x, y):
        if x < 0 or x >= GRID_W or y < 0 or y >= GRID_H:
            return True
        o = self.ovl.get((x, y))
        if o is not None:
            t = o
        else:
            t = self.base[y][x]
        if t == "EMPTY" or t == "ICE" or t == "CRACK" or t == "SWITCH" \
                or t == "K1" or t == "K2" or t == "V" or t == "PLATE" \
                or t == "HEAL" or t == "MIMIC" or t.startswith("ONEWAY"):
            pass
        elif t == "W" or t == "T_W" or t.startswith("LASER"):
            return True
        elif t == "R_GATE":
            return not self.gates
        elif t == "B_GATE":
            return self.gates
        elif t == "P_GATE":
            return not self.plates_active()
        elif t.startswith("MIRROR") or t.startswith("SPRING") or t.startswith("PORTAL"):
            pass
        return False


def _scan_static(base):
    cannons = []
    plates = []
    portals = {}
    for y in range(GRID_H):
        row = base[y]
        for x in range(GRID_W):
            t = row[x]
            if t.startswith("LASER"):
                cannons.append((x, y))
            elif t == "PLATE":
                plates.append((x, y))
            elif t.startswith("PORTAL_"):
                portals.setdefault(t, []).append((x, y))
    pair = {}
    for t, cells in portals.items():
        if len(cells) >= 2:
            pair[cells[0]] = cells[1]
            pair[cells[1]] = cells[0]
    return cannons, plates, pair


def _blocks_oneway(w, x, y, dch):
    t = w.t(x, y)
    if t.startswith("ONEWAY_"):
        return t[-1] != dch
    return False


def _hero_enterable(w, x, y, dch):
    """勇者以方向 dch 进入 (x,y) 的可入性（含单向门）。"""
    if w.is_wall(x, y):
        return False
    if w.occ.get((x, y)) in ("BOX", "TNT"):
        return False
    if _blocks_oneway(w, x, y, dch):
        return False
    return True


def _box_enterable(w, x, y, dch):
    """箱子以方向 dch 进入 (x,y) 的可入性。"""
    if w.is_wall(x, y):
        return False
    if w.occ.get((x, y)) is not None:
        return False
    t = w.t(x, y)
    if t in ("K1", "K2", "V"):
        return False
    if _blocks_oneway(w, x, y, dch):
        return False
    return True


def _slide_tile(t):
    return t == "ICE" or t.startswith("MIRROR_") or t.startswith("SPRING_") \
        or t.startswith("PORTAL_")


def _explode(w, sources):
    """阶段 C/D 爆炸闭包（就地修改 w）。sources: [(x,y)]。"""
    done = set(sources)
    q = list(sources)
    while q:
        ex, ey = q.pop()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                cx, cy = ex + dx, ey + dy
                if not (0 <= cx < GRID_W and 0 <= cy < GRID_H):
                    continue
                if w.occ.get((cx, cy)) == "TNT" and (cx, cy) not in done:
                    done.add((cx, cy)); q.append((cx, cy))
                for b in w.bl:
                    if (b[0], b[1]) == (cx, cy) and (cx, cy) not in done:
                        done.add((cx, cy)); q.append((cx, cy))
    a = b = 0
    for (ex, ey) in done:
        if abs(w.hx - ex) <= 1 and abs(w.hy - ey) <= 1:
            if w.occ.get((ex, ey)) == "TNT":
                a += 60
            else:
                b += 50
    if a + b > 0:
        w.hp -= (a + b)
    for (ex, ey) in done:
        w.bl = [bm for bm in w.bl if (bm[0], bm[1]) != (ex, ey)]
        if w.occ.get((ex, ey)) == "TNT":
            w.occ.pop((ex, ey), None)
    for (ex, ey) in done:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                cx, cy = ex + dx, ey + dy
                if not (0 <= cx < GRID_W and 0 <= cy < GRID_H):
                    continue
                if w.occ.get((cx, cy)) == "BOX":
                    w.occ.pop((cx, cy))
                t = w.t(cx, cy)
                if t in BLAST_IMMUNE:
                    continue
                if t == "CRACK":
                    w.ovl[(cx, cy)] = "PIT"
                else:
                    w.ovl[(cx, cy)] = "EMPTY"
                if t.startswith("LASER"):
                    if (cx, cy) in w.cannons:
                        w.cannons = [c for c in w.cannons if c != (cx, cy)]
    # 爆后支撑：箱落新坑
    for (cx, cy) in list(w.occ.keys()):
        if w.occ.get((cx, cy)) == "BOX" and w.t(cx, cy) == "PIT":
            w.occ.pop((cx, cy))
            w.ovl[(cx, cy)] = "EMPTY"
    if w.hp > 0 and w.t(w.hx, w.hy) == "PIT":
        w.hp -= 100
    if w.hp <= 0:
        w.status = "DEAD"


def _arrive(w, x, y, is_hero):
    t = w.t(x, y)
    if is_hero:
        if t == "PIT":
            w.hp -= 100
        elif t == "MIMIC":
            w.hp -= 45
            w.ovl[(x, y)] = "EMPTY"
        elif t == "HEAL":
            w.hp = min(100, w.hp + 30)
            w.ovl[(x, y)] = "EMPTY"
        elif t == "SWITCH":
            w.gates = not w.gates
        elif t == "K1":
            w.k1 = True; w.ovl[(x, y)] = "EMPTY"
        elif t == "K2":
            w.k2 = True; w.ovl[(x, y)] = "EMPTY"
        elif t == "V" and w.k1 and w.k2 and w.hp > 0:
            w.status = "CLEARED"
    else:
        if t == "PIT":
            w.occ.pop((x, y))
            w.ovl[(x, y)] = "EMPTY"
            return True     # 箱链终止
        if t == "MIMIC":
            w.ovl[(x, y)] = "EMPTY"
        elif t == "SWITCH":
            w.gates = not w.gates
    return False


def _atomic(w, x0, y0, x1, y1, dch, is_hero, steps, exposure):
    """一次成功位移的 8 步原子序（含动量链）。返回 True 若链被终止/死亡。"""
    px, py = x0, y0
    cx, cy = x1, y1
    while True:
        steps += 1
        lt = w.t(px, py)
        if lt == "CRACK":
            w.ovl[(px, py)] = "PIT"
        if is_hero:
            w.hx, w.hy = cx, cy
            exposure.add((cx, cy))
        else:
            if (cx, cy) != (px, py):
                w.occ.pop((px, py), None)
                w.occ[(cx, cy)] = "BOX"
        stop = _arrive(w, cx, cy, is_hero)
        if not is_hero and stop:
            return True
        if w.hp <= 0:
            w.status = "DEAD"
            return True
        if is_hero and w.status == "CLEARED":
            return True
        if steps >= 32:
            return True
        t = w.t(cx, cy)
        if t == "ICE":
            dx, dy = DIRS[dch]
            nx, ny = cx + dx, cy + dy
            if is_hero:
                ok = _hero_enterable(w, nx, ny, dch)
            else:
                ok = _box_enterable(w, nx, ny, dch) and (nx, ny) != (w.hx, w.hy)
            if not ok:
                return True
            px, py = cx, cy
            cx, cy = nx, ny
            continue
        if t.startswith("MIRROR_"):
            nd = MIRROR_MAP[t][dch]
            dx, dy = DIRS[nd]
            nx, ny = cx + dx, cy + dy
            if is_hero:
                ok = _hero_enterable(w, nx, ny, nd)
            else:
                ok = _box_enterable(w, nx, ny, nd) and (nx, ny) != (w.hx, w.hy)
            if not ok:
                return True
            px, py = cx, cy
            cx, cy = nx, ny
            dch = nd
            continue
        if t.startswith("SPRING_"):
            sd = t[-1]
            dx, dy = DIRS[sd]
            blocked = None
            for k in (1, 2, 3):
                pkx, pky = cx + k * dx, cy + k * dy
                if w.is_wall(pkx, pky) or w.occ.get((pkx, pky)) in ("BOX", "TNT") \
                        or _blocks_oneway(w, pkx, pky, sd):
                    blocked = k
                    break
                if not is_hero and (pkx, pky) == (w.hx, w.hy):
                    blocked = k
                    break
            if blocked is None:
                px, py = cx, cy
                cx, cy = cx + 3 * dx, cy + 3 * dy
                dch = sd
                continue
            if blocked == 1:
                return True
            px, py = cx, cy
            cx, cy = cx + (blocked - 1) * dx, cy + (blocked - 1) * dy
            dch = sd
            continue
        if t.startswith("PORTAL_"):
            found = w.portals.get((cx, cy))
            if found is None:
                return True
            px, py = cx, cy
            cx, cy = found
            stop = _arrive(w, cx, cy, is_hero)
            if not is_hero and stop:
                return True
            if w.hp <= 0:
                w.status = "DEAD"; return True
            if is_hero and w.status == "CLEARED":
                return True
            # 传送后保持方向迈 1 步
            dx, dy = DIRS[dch]
            nx, ny = cx + dx, cy + dy
            if is_hero:
                ok = _hero_enterable(w, nx, ny, dch)
            else:
                ok = _box_enterable(w, nx, ny, dch) and (nx, ny) != (w.hx, w.hy)
            if not ok:
                return True
            px, py = cx, cy
            cx, cy = nx, ny
            continue
        return True


def step_world(w, action):
    """执行一整回合（阶段 A/B/C/D）。w.turn = 本回合号；返回下一回合的新世界。"""
    nw = _World(w.base, dict(w.ovl), dict(w.occ), w.hx, w.hy, w.hp,
                w.k1, w.k2, w.jumps, w.bombs, w.gates, list(w.bl),
                w.turn + 1, "ALIVE", list(w.cannons), list(w.plates), dict(w.portals))
    exposure = {(nw.hx, nw.hy)}
    armed = []
    ch = action[-1] if action not in ("WAIT", "BOMB") else None

    if action == "WAIT":
        pass
    elif action == "BOMB":
        if nw.bombs > 0 and not any(b[0] == nw.hx and b[1] == nw.hy for b in nw.bl):
            nw.bombs -= 1
            nw.bl.append((nw.hx, nw.hy, 3))
    elif action.startswith("MOVE_"):
        dx, dy = DIRS[ch]
        tx, ty = nw.hx + dx, nw.hy + dy
        if _blocks_oneway(nw, tx, ty, ch) or nw.is_wall(tx, ty) or \
                nw.occ.get((tx, ty)) == "TNT":
            pass
        elif nw.occ.get((tx, ty)) == "BOX":
            bx, by = tx + dx, ty + dy
            if _box_enterable(nw, bx, by, ch):
                nw.occ.pop((tx, ty))
                _atomic(nw, tx, ty, bx, by, ch, False, 0, exposure)
            if _hero_enterable(nw, tx, ty, ch):
                _atomic(nw, nw.hx, nw.hy, tx, ty, ch, True, 0, exposure)
        else:
            _atomic(nw, nw.hx, nw.hy, tx, ty, ch, True, 0, exposure)
    elif action.startswith("JUMP_"):
        if nw.jumps > 0:
            nw.jumps -= 1
            dx, dy = DIRS[ch]
            p1 = (nw.hx + dx, nw.hy + dy)
            p2 = (nw.hx + 2 * dx, nw.hy + 2 * dy)
            ok1 = not nw.is_wall(p1[0], p1[1]) and not _blocks_oneway(nw, p1[0], p1[1], ch)
            ok2 = (not nw.is_wall(p2[0], p2[1])
                   and nw.occ.get(p2) not in ("BOX", "TNT")
                   and not _blocks_oneway(nw, p2[0], p2[1], ch))
            if ok1 and ok2:
                _atomic(nw, nw.hx, nw.hy, p2[0], p2[1], ch, True, 0, exposure)

    if nw.status == "DEAD":
        return nw

    # ---- 阶段 C：炸弹倒计时与链式爆炸 ----
    nbl = []
    src = []
    for b in nw.bl:
        t2 = b[2] - 1
        if t2 == 0:
            src.append((b[0], b[1]))
        else:
            nbl.append((b[0], b[1], t2))
    nw.bl = nbl
    src.extend(armed)
    if src:
        _explode(nw, src)
        if nw.status == "DEAD":
            return nw

    # ---- 阶段 D：双频激光（本回合 w.turn 发射）----
    turn = w.turn
    if turn % 3 == 0 or turn % 4 == 0:
        fires_red = (turn % 3 == 0)
        fires_blue = (turn % 4 == 0)
        hits = 0
        lsrc = []
        for (x, y) in w.cannons:
            t = nw.t(x, y)
            if not t or not t.startswith("LASER"):
                continue
            blue = t.startswith("LASER2")
            if (blue and not fires_blue) or ((not blue) and not fires_red):
                continue
            dch = t[-1]
            dx, dy = DIRS[dch]
            ray = set()
            cx, cy = x, y
            for _ in range(10):
                cx += dx; cy += dy
                if cx < 0 or cx >= GRID_W or cy < 0 or cy >= GRID_H:
                    break
                if nw.is_wall(cx, cy) or nw.occ.get((cx, cy)) == "BOX":
                    break
                if nw.occ.get((cx, cy)) == "TNT":
                    lsrc.append((cx, cy))
                    break
                ray.add((cx, cy))
            if ray & exposure:
                hits += 1
        if hits > 0:
            nw.hp -= 50 * hits
            if nw.hp <= 0:
                nw.status = "DEAD"
                return nw
        if lsrc:
            _explode(nw, lsrc)
    return nw


def decode_state(state):
    """从 FULL state 构造世界（CHEST 经线索解码为 HEAL/MIMIC）。"""
    terr = state.get("terrain") or []
    occ = state.get("occupant") or []
    clues = state.get("clues") or []
    hero = state.get("hero", {}) or {}
    base = []
    for y in range(GRID_H):
        row = []
        for x in range(GRID_W):
            t = terr[y][x] if y < len(terr) and x < len(terr[y]) else "EMPTY"
            if t in ("BOX", "TNT"):
                t = "EMPTY"       # 占用层实体不入地形层（与裁判四层模型一致）
            row.append(t)
        base.append(row)
    # CHEST 解码
    for y in range(GRID_H):
        for x in range(GRID_W):
            if base[y][x] == "CHEST":
                is_mimic = False
                for d in DIRS.values():
                    nx, ny = x + d[0], y + d[1]
                    if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                        if clues and ny < len(clues) and nx < len(clues[ny]) and clues[ny][nx]:
                            is_mimic = True
                            break
                base[y][x] = "MIMIC" if is_mimic else "HEAL"
    occd = {}
    for y in range(GRID_H):
        for x in range(GRID_W):
            o = occ[y][x] if y < len(occ) and x < len(occ[y]) else None
            if o in ("BOX", "TNT"):
                occd[(x, y)] = o
    bl = []
    for b in (state.get("bombs") or []):
        bl.append((int(b["x"]), int(b["y"]), int(b.get("timer", 3))))
    keys = hero.get("keys", [False, False]) or [False, False]
    cannons, plates, portals = _scan_static(base)
    return _World(base, {}, occd, int(hero.get("x", 2)), int(hero.get("y", 13)),
                  int(hero.get("hp", 100)), bool(keys[0]), bool(keys[1]),
                  int(hero.get("jumps", 0)), int(hero.get("bombs", 2)),
                  bool(state.get("gates_flipped", False)), bl,
                  int(state.get("turn", 1)), "ALIVE", cannons, plates, portals)


# ==============================================================================
# 参赛入口 2：FULL 明牌全局求解器
# ==============================================================================

def _relaxed_dist(w, gx, gy):
    """乐观反向 BFS 距离（门全开、箱可穿、坑/墙/宝箱怪阻挡、单向门守向）。"""
    dist = {(gx, gy): 0}
    dq = [(gx, gy)]
    head = 0
    while head < len(dq):
        cx, cy = dq[head]
        head += 1
        d0 = dist[(cx, cy)]
        for dch, (dx, dy) in DIRS.items():
            ax, ay = cx - dx, cy - dy
            if (ax, ay) in dist or not (0 <= ax < GRID_W and 0 <= ay < GRID_H):
                continue
            t = w.t(ax, ay)
            if t in ("PIT", "MIMIC") or t == "W" or t == "T_W" or t.startswith("LASER"):
                continue
            if t.startswith("ONEWAY") and t[-1] != dch:
                # b=(cx,cy) 若为逆向单向则该边不通；此处 b 是目标格
                pass
            if _blocks_oneway(w, cx, cy, dch):
                continue
            dist[(ax, ay)] = d0 + 1
            dq.append((ax, ay))
    return dist


def _ray_cells(w):
    """缓存所有炮座的 (period, cells) 射线（含当前墙/箱阻挡）。"""
    rc = []
    for (x, y) in w.cannons:
        t = w.t(x, y)
        if not t or not t.startswith("LASER"):
            continue
        blue = t.startswith("LASER2")
        period = 4 if blue else 3
        dch = t[-1]
        dx, dy = DIRS[dch]
        cells = []
        cx, cy = x, y
        for _ in range(10):
            cx += dx; cy += dy
            if cx < 0 or cx >= GRID_W or cy < 0 or cy >= GRID_H:
                break
            if w.is_wall(cx, cy) or w.occ.get((cx, cy)) == "BOX":
                break
            cells.append((cx, cy))
            if w.occ.get((cx, cy)) == "TNT":
                break
        rc.append((period, cells, (x, y)))
    return rc


def _actions(w, rays):
    """动作剪枝：WAIT 仅在危险邻域或炸弹倒计时；JUMP 仅在跨坑/裂板时。"""
    acts = ["MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R"]
    danger = False
    for (period, cells, _) in rays:
        if (w.hx, w.hy) in cells:
            danger = True
            break
        for d in DIRS.values():
            if (w.hx + d[0], w.hy + d[1]) in cells:
                danger = True
                break
        if danger:
            break
    if danger or w.bl:
        acts.append("WAIT")
    if w.jumps > 0:
        rayset = set()
        for (_, cells, _) in rays:
            rayset.update(cells)
        for ch, (dx, dy) in DIRS.items():
            p1 = w.t(w.hx + dx, w.hy + dy)
            inb = 0 <= w.hx + 2 * dx < GRID_W and 0 <= w.hy + 2 * dy < GRID_H
            p2t = w.t(w.hx + 2 * dx, w.hy + 2 * dy) if inb else "EMPTY"
            p1k = (w.hx + dx, w.hy + dy)
            p2k = (w.hx + 2 * dx, w.hy + 2 * dy)
            if p1 in ("PIT", "CRACK") or p2t in ("PIT", "CRACK") \
                    or p1k in rayset or p2k in rayset:
                acts.append("JUMP_" + ch)
    if w.bombs > 0 and not any(b[0] == w.hx and b[1] == w.hy for b in w.bl):
        near_blastable = False
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                t = w.t(w.hx + dx, w.hy + dy)
                if t not in BLAST_IMMUNE and t != "EMPTY":
                    near_blastable = True
                    break
            if near_blastable:
                break
        if near_blastable:
            acts.append("BOMB")
    return acts


def _ray_zone(w, rays):
    """射线危险区 + 2 格余量（去重键仅在区内保留 tmod）。"""
    zone = set()
    for (_, cells, _) in rays:
        for (cx, cy) in cells:
            for dy in (-2, -1, 0, 1, 2):
                for dx in (-2, -1, 0, 1, 2):
                    zone.add((cx + dx, cy + dy))
    return zone


def _node_key(w, zone):
    if w._zk is None:
        w._zk = (w.k1, w.k2, w.jumps, w.bombs, w.gates, w.hp,
                 tuple(sorted(w.ovl.items())),
                 tuple(sorted(w.occ.items())),
                 tuple(w.bl))
    tm = (w.turn % 12) if (w.hx, w.hy) in zone else -1
    return (w.hx, w.hy, tm) + w._zk


def _astar(w, goal_test, h_fn, deadline, max_nodes, w_h=3.0, push_guard=None):
    """加权 A*：安全动作搜索。goal_test(world)->bool；h_fn(node)->int 为启发函数。
    去重键采用射线区感知的模 12 时间维度（区外折叠，靠边界 WAIT 重新对拍）。
    push_guard: 板目标距离场 —— 推箱后新位距离不得变大（单调剪枝）。"""
    rays0 = _ray_cells(w) if w.cannons else []
    zone = _ray_zone(w, rays0)
    h0 = h_fn(w)
    start_key = _node_key(w, zone)
    open_heap = [(w_h * h0, 0, 0, w)]
    came = {start_key: None}
    best_g = {start_key: 0}
    counter = 1
    best_node = None
    best_score = None
    nodes = 0
    while open_heap:
        if (nodes & 7) == 0 and time.monotonic() > deadline:
            break
        f, g, _, cur = heapq.heappop(open_heap)
        if g > best_g.get(_node_key(cur, zone), 1 << 30):
            continue
        nodes += 1
        if nodes > max_nodes:
            break
        h = h_fn(cur)
        sc = (h, g)
        if best_score is None or sc < best_score:
            best_score = sc
            best_node = cur
        if goal_test(cur):
            path = []
            node = cur
            while _node_key(node, zone) != start_key:
                parent, act = came[_node_key(node, zone)]
                path.append(act)
                node = parent
            path.reverse()
            return path, True, nodes
        rays = _ray_cells(cur) if cur.cannons else []
        for act in _actions(cur, rays):
            nw = step_world(cur, act)
            if nw.status == "DEAD" or nw.hp < cur.hp:
                continue
            if push_guard is not None:
                gone = [p for p in cur.occ if cur.occ[p] == "BOX" and p not in nw.occ]
                new = [p for p in nw.occ if nw.occ[p] == "BOX" and p not in cur.occ]
                if gone:
                    # 已压板之箱不得推走；板试验中箱不得消失（掉坑）
                    if any(g in cur.plates for g in gone):
                        continue
                    if not new:
                        continue
                    old_best = min(push_guard.get(p, 999) for p in gone)
                    new_best = min(push_guard.get(p, 999) for p in new)
                    if new_best > old_best:
                        continue
            k = _node_key(nw, zone)
            ng = g + 1
            if best_g.get(k, 1 << 30) <= ng:
                continue
            best_g[k] = ng
            came[k] = (cur, act)
            hh = h_fn(nw)
            heapq.heappush(open_heap, (ng + w_h * hh, ng, counter, nw))
            counter += 1
    if best_node is not None and _node_key(best_node, zone) != start_key:
        path = []
        node = best_node
        while _node_key(node, zone) != start_key:
            info = came.get(_node_key(node, zone))
            if info is None:
                return None, False, nodes
            path.append(info[1])
            node = info[0]
        path.reverse()
        if path:
            return path, False, nodes
    return None, False, nodes


_s1e_trace = {}
def _reactive(w, dist):
    """降级决策：安全动作中选静态距离最小者。"""
    best = None
    best_sc = None
    rays = _ray_cells(w) if w.cannons else []
    _s1e_trace["reactive"] = []
    for act in _actions(w, rays) + ["WAIT"]:
        nw = step_world(w, act)
        if nw.status == "DEAD":
            _s1e_trace["reactive"].append([act, "dead", [nw.hx, nw.hy]])
            continue
        if nw.occ != w.occ:
            _s1e_trace["reactive"].append([act, "occupant_change", [nw.hx, nw.hy]])
            continue          # 兜底模式绝不推箱
        pen = 0 if nw.hp >= w.hp else 1
        d = dist.get((nw.hx, nw.hy))
        if d is None:
            d = 999
        sc = (pen, d, 0 if act == "WAIT" else 1)
        _s1e_trace["reactive"].append([act, "scored", [nw.hx, nw.hy], sc])
        if best_sc is None or sc < best_sc:
            best_sc = sc
            best = act
    return best or "WAIT"


def decide_action(state: dict, memory: dict) -> str:
    _s1e_trace.clear()
    _s1e_trace["cached_plan_before"] = len(memory.get("plan") or [])
    _s1e_trace["trials"] = []
    try:
        act = _decide(state, memory)
        if act in VALID_ACTIONS:
            return act
        _s1e_trace["invalid"] = str(act)
        return "WAIT"
    except Exception as exc:
        _s1e_trace["exception"] = str(exc)
        return "WAIT"


def _exec_plan(w, memory):
    plan = memory.get("plan")
    if plan:
        a = plan[0]
        nw = step_world(w, a)
        if nw.status != "DEAD" and nw.hp >= w.hp:
            plan.pop(0)
            if not plan:
                memory["plan"] = None
            return a
        memory["plan"] = None
    return None


def _decide(state, memory):
    w = decode_state(state)
    turn = w.turn
    t0 = time.monotonic()
    budget = 1.3 if turn <= 1 else 0.25
    deadline = t0 + budget
    max_nodes = 22000 if turn <= 1 else 4000

    # 已有计划：逐拍安全校验后执行
    a = _exec_plan(w, memory)
    if a is not None:
        _s1e_trace["branch"] = "cached_plan"
        return a

    tg = state.get("targets", {}) or {}
    k1 = tg.get("K1"); k2 = tg.get("K2"); vv = tg.get("V")

    def _pos(cell):
        return (int(cell[0]), int(cell[1])) if cell else None

    def _box_dist_field(free_only=False):
        dist = {}
        src = [p for p, v in w.occ.items() if v == "BOX"]
        if free_only:
            src = [p for p in src if p not in w.plates]
        for (bx, by) in src:
            d2 = _relaxed_dist(w, bx, by)
            for kk, vv2 in d2.items():
                if vv2 < dist.get(kk, 999):
                    dist[kk] = vv2
        return dist

    # ---- 子目标梯队：逐压板解锁 -> 缺失钥匙 -> V ----
    plates_locked = bool(w.plates) and not w.plates_active()
    trials = []
    if plates_locked:
        unpressed = [p for p in w.plates if w.occ.get(p) != "BOX"]
        bdf = _box_dist_field(free_only=True)
        if bdf:
            unpressed.sort(key=lambda p: bdf.get(p, 999))
        for pp in unpressed:
            trials.append(("plate", pp))
    if k1 and not w.k1:
        trials.append(("pos", _pos(k1)))
    if k2 and not w.k2:
        trials.append(("pos", _pos(k2)))
    if vv and not (k1 and not w.k1) and not (k2 and not w.k2):
        trials.append(("pos", _pos(vv)))

    def _pos_h(gx, gy):
        d = _relaxed_dist(w, gx, gy)
        return (lambda node: d.get((node.hx, node.hy), 999))

    def _plate_h(pp):
        field_p = _relaxed_dist(w, pp[0], pp[1])
        box_field = _box_dist_field(free_only=True)
        return (lambda node:
                min([field_p.get(b, 999) for b, v in node.occ.items()
                     if v == "BOX"] or [999])
                + box_field.get((node.hx, node.hy), 999))

    _s1e_trace["queued_trials"] = trials
    best_partial = None
    for (kind, cell) in trials:
        trial_t0 = time.monotonic()
        if kind == "pos":
            gx, gy = cell
            h_fn = _pos_h(gx, gy)
            test = (lambda c: (c.hx, c.hy) == (gx, gy))
            res, complete, _ = _astar(w, test, h_fn, deadline, max_nodes)
        elif kind == "plate":
            field_p = _relaxed_dist(w, cell[0], cell[1])
            h_fn = _plate_h(cell)
            test = (lambda c, pp=cell: c.occ.get(pp) == "BOX")
            res, complete, _ = _astar(w, test, h_fn, deadline, max_nodes,
                                      push_guard=field_p)
        else:
            continue
        _s1e_trace["trials"].append({"kind": kind, "cell": cell, "complete": complete, "nodes": _,
                                      "prefix": res, "elapsed_sec": time.monotonic()-trial_t0,
                                      "remaining_sec": deadline-time.monotonic()})
        if complete and res:
            memory["plan"] = res
            a = _exec_plan(w, memory)
            if a is not None:
                _s1e_trace["branch"] = "new_complete_plan"
                return a
            continue
        if res and best_partial is None:
            best_partial = res
    # 无完整解：执行最优部分前缀（截断到首次推箱前，避免破坏箱位）
    if best_partial:
        _s1e_trace["partial_in"] = best_partial
        safe_prefix = []
        ww = w
        for act in best_partial[:60]:
            ww2 = step_world(ww, act)
            if ww2.occ != ww.occ:
                _s1e_trace["partial_cut_at"] = act
                break
            safe_prefix.append(act)
            ww = ww2
        _s1e_trace["partial_safe"] = safe_prefix
        if safe_prefix:
            memory["plan"] = safe_prefix
            a = _exec_plan(w, memory)
            if a is not None:
                _s1e_trace["branch"] = "partial_plan"
                return a
    # 反应式兜底
    if trials:
        kind, cell = trials[0]
        if kind == "pos" and cell:
            dist = _relaxed_dist(w, cell[0], cell[1])
        else:
            dist = _box_dist_field()
        _s1e_trace["branch"] = "reactive"
        return _reactive(w, dist)
    _s1e_trace["branch"] = "no_trials"
    return "WAIT"
