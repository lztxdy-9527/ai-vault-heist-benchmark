"""
《阴间地牢：金库攻防战》参赛提交 (submission.py)
双角色：魔王造图 + 自证通关；BLIND 迷雾勇者增量建图破阵。
仅使用纯算法标准库，无任何文件/网络/进程/反射能力。
"""

import heapq
import math
from collections import deque

# ==============================================================================
# 官方规则常量
# ==============================================================================
GRID_WIDTH = 40
GRID_HEIGHT = 26
MAX_BUDGET = 3000
MAX_TURNS = 240
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
    "CRACK": 20, "SWITCH": 30, "R_GATE": 20, "B_GATE": 20,
    "TNT": 40, "BOX": 30, "HEAL": 30, "MIMIC": 60,
    "PORTAL_1A": 40, "PORTAL_1B": 40, "PORTAL_2A": 40, "PORTAL_2B": 40,
}

HIGH_WALL_TILES = {"W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R"}
MOMENTUM_TILES = {"ICE", "MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW",
                  "SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R",
                  "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B"}
EXPLODE_DESTROY = {"W", "ICE", "MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW",
                   "SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R",
                   "LASER_U", "LASER_D", "LASER_L", "LASER_R",
                   "SWITCH", "R_GATE", "B_GATE", "HEAL", "MIMIC"}
EXPLODE_IMMUNE = {"T_W", "K1", "K2", "V", "PIT",
                  "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B"}


def in_bounds(x, y):
    return 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT


def is_high_wall(tile, gates_flipped):
    if tile in HIGH_WALL_TILES:
        return True
    if tile == "R_GATE":
        return not gates_flipped
    if tile == "B_GATE":
        return gates_flipped
    return False


def is_spawn_zone(x, y):
    return 1 <= x <= 3 and 12 <= y <= 14


# ==============================================================================
# 完整确定性物理引擎（用于魔王 author_solution 回放自证 / 勇者信念模拟）
# ==============================================================================
class Engine:
    def __init__(self, grid, hero=None, gates_flipped=False, turn=0):
        self.terrain = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.occ = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.clues = [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.mimic_clue = {}
        portal_pos = {}
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                t = grid[y][x]
                if t in ("BOX", "TNT"):
                    self.terrain[y][x] = "EMPTY"
                    self.occ[y][x] = t
                else:
                    self.terrain[y][x] = t
                if t.startswith("PORTAL_"):
                    portal_pos[t] = (x, y)
        self.portal_pos = portal_pos
        self._bind_clues(grid)
        if hero is None:
            hero = {"x": SPAWN_POS[0], "y": SPAWN_POS[1], "hp": 100,
                    "k1": False, "k2": False, "jumps": 3, "throws": 3, "bombs": 2}
        self.hx = hero["x"]; self.hy = hero["y"]; self.hp = hero["hp"]
        self.k1 = hero.get("k1", False); self.k2 = hero.get("k2", False)
        self.jumps = hero.get("jumps", 3); self.throws = hero.get("throws", 3)
        self.bombs_left = hero.get("bombs", 2)
        self.gates = gates_flipped
        self.bombs = []
        self.bomb_id = 0
        self.turn = turn
        self.status = "ALIVE"
        self.exposed = set()
        self.trap_damage = 0.0
        self.tnt_armed = set()
        self.last_steps = 0
        self.last_portal_count = 0

    def _bind_clues(self, grid):
        mimics = []
        chests = set()
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if grid[y][x] == "MIMIC":
                    mimics.append((x, y))
                if grid[y][x] in ("MIMIC", "HEAL"):
                    chests.add((x, y))
        for (mx, my) in mimics:
            for (dx, dy) in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = mx + dx, my + dy
                if not in_bounds(nx, ny):
                    continue
                if self.terrain[ny][nx] != "EMPTY" or self.occ[ny][nx] is not None:
                    continue
                if is_spawn_zone(nx, ny):
                    continue
                if self.clues[ny][nx]:
                    continue
                ok = True
                for (ax, ay) in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    cx, cy = nx + ax, ny + ay
                    if (cx, cy) in chests and (cx, cy) != (mx, my):
                        ok = False
                        break
                if ok:
                    self.clues[ny][nx] = True
                    self.mimic_clue[(mx, my)] = (nx, ny)
                    break

    def _clear_mimic(self, x, y):
        self.terrain[y][x] = "EMPTY"
        c = self.mimic_clue.pop((x, y), None)
        if c is not None:
            self.clues[c[1]][c[0]] = False

    def t(self, x, y):
        return self.terrain[y][x]

    def high(self, x, y):
        return is_high_wall(self.terrain[y][x], self.gates)

    def can_enter(self, x, y, entity):
        if not in_bounds(x, y):
            return False
        if self.high(x, y):
            return False
        o = self.occ[y][x]
        if o in ("BOX", "TNT"):
            return False
        if entity == "BOX":
            if (x, y) == (self.hx, self.hy):
                return False
            if self.terrain[y][x] in ("K1", "K2", "V"):
                return False
        return True

    # ---- 8 步原子位移 ----
    def _atomic(self, entity, x0, y0, x1, y1, dname, steps, portals, suppress):
        steps += 1
        # 离开钩子
        if self.terrain[y0][x0] == "CRACK":
            self.terrain[y0][x0] = "PIT"
        stop = False
        if entity == "BOX":
            self.occ[y0][x0] = None
            self.occ[y1][x1] = "BOX"
            tt = self.terrain[y1][x1]
            if tt == "PIT":
                self.occ[y1][x1] = None
                self.terrain[y1][x1] = "EMPTY"
                self.last_steps = steps
                return
            if tt == "MIMIC":
                self._clear_mimic(x1, y1)
            elif tt == "SWITCH":
                self.gates = not self.gates
        else:
            self.hx, self.hy = x1, y1
            self.exposed.add((x1, y1))
            tt = self.terrain[y1][x1]
            if tt == "PIT":
                self.hp -= 100
                self.trap_damage += min(max(0, self.hp + 100), 100)
            elif tt == "MIMIC":
                self.hp -= 45
                self.trap_damage += min(max(0, self.hp + 45), 45)
                self._clear_mimic(x1, y1)
                stop = True
            elif tt == "HEAL":
                self.hp = min(100, self.hp + 30)
                self.terrain[y1][x1] = "EMPTY"
            elif tt == "SWITCH":
                self.gates = not self.gates
            if self.hp <= 0:
                self.status = "DEAD"
                self.last_steps = steps
                return
            if tt == "K1":
                self.k1 = True
                self.terrain[y1][x1] = "EMPTY"
            elif tt == "K2":
                self.k2 = True
                self.terrain[y1][x1] = "EMPTY"
            elif tt == "V" and self.k1 and self.k2 and self.hp > 0:
                self.status = "CLEARED"
                self.last_steps = steps
                return
        if steps >= 32 or stop:
            self.last_steps = steps
            return
        # 动量延续
        tt = self.terrain[y1][x1]
        dx, dy = DIRS[dname]
        if tt == "ICE":
            nx, ny = x1 + dx, y1 + dy
            if self.can_enter(nx, ny, entity):
                self._atomic(entity, x1, y1, nx, ny, dname, steps, portals, False)
            else:
                self.last_steps = steps
        elif tt in MIRROR_MAP:
            nd = MIRROR_MAP[tt][dname]
            ndx, ndy = DIRS[nd]
            nx, ny = x1 + ndx, y1 + ndy
            if self.can_enter(nx, ny, entity):
                self._atomic(entity, x1, y1, nx, ny, nd, steps, portals, False)
            else:
                self.last_steps = steps
        elif tt.startswith("SPRING_"):
            sd = tt.split("_")[1]
            sdx, sdy = DIRS[sd]
            blocked_k = None
            for k in (1, 2, 3):
                px, py = x1 + k * sdx, y1 + k * sdy
                blk = (not in_bounds(px, py)) or self.high(px, py) or self.occ[py][px] in ("BOX", "TNT")
                if entity == "BOX" and in_bounds(px, py):
                    if (px, py) == (self.hx, self.hy) or self.terrain[py][px] in ("K1", "K2", "V"):
                        blk = True
                if blk:
                    blocked_k = k
                    if entity == "BOX" and in_bounds(px, py) and self.occ[py][px] == "TNT":
                        self.tnt_armed.add((px, py))
                    break
            if blocked_k is None:
                self._atomic(entity, x1, y1, x1 + 3 * sdx, y1 + 3 * sdy, sd, steps, portals, False)
            elif blocked_k == 1:
                self.last_steps = steps
            else:
                k = blocked_k
                self._atomic(entity, x1, y1, x1 + (k - 1) * sdx, y1 + (k - 1) * sdy, sd, steps, portals, False)
        elif tt in PORTAL_PAIR and not suppress:
            pair = self.portal_pos.get(PORTAL_PAIR[tt])
            if pair is not None:
                px, py = pair
                enterable = in_bounds(px, py) and self.occ[py][px] is None
                if entity == "BOX" and (px, py) == (self.hx, self.hy):
                    enterable = False
                if enterable:
                    portals += 1
                    self._atomic(entity, x1, y1, px, py, dname, steps, portals, True)
                    if self.status != "ALIVE":
                        return
                    if portals >= 2:
                        self.last_steps = self.last_steps
                        return
                    ndx, ndy = DIRS[dname]
                    nx, ny = px + ndx, py + ndy
                    if self.can_enter(nx, ny, entity):
                        self._atomic(entity, px, py, nx, ny, dname, self.last_steps, portals, False)
                    else:
                        pass
                else:
                    self.last_steps = steps
            else:
                self.last_steps = steps
        else:
            self.last_steps = steps

    def _move(self, dname):
        dx, dy = DIRS[dname]
        x0, y0 = self.hx, self.hy
        x1, y1 = x0 + dx, y0 + dy
        if not in_bounds(x1, y1):
            return
        if self.high(x1, y1) or self.occ[y1][x1] == "TNT":
            return
        if self.occ[y1][x1] == "BOX":
            x2, y2 = x0 + 2 * dx, y0 + 2 * dy
            if self.can_enter(x2, y2, "BOX"):
                self._atomic("BOX", x1, y1, x2, y2, dname, 0, 0, False)
                if self.status != "ALIVE":
                    return
                if self.can_enter(x1, y1, "hero"):
                    self._atomic("hero", x0, y0, x1, y1, dname, 0, 0, False)
            return
        self._atomic("hero", x0, y0, x1, y1, dname, 0, 0, False)

    def _jump(self, dname):
        if self.jumps <= 0:
            return
        self.jumps -= 1
        dx, dy = DIRS[dname]
        x0, y0 = self.hx, self.hy
        x1, y1 = x0 + dx, y0 + dy
        x2, y2 = x0 + 2 * dx, y0 + 2 * dy
        if not in_bounds(x2, y2):
            return
        if self.high(x1, y1) or self.high(x2, y2) or self.occ[y2][x2] in ("BOX", "TNT"):
            return
        self._atomic("hero", x0, y0, x2, y2, dname, 0, 0, False)

    def _throw(self, dname):
        if self.throws <= 0:
            return
        self.throws -= 1
        dx, dy = DIRS[dname]
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
            if self.high(sx, sy) or self.occ[sy][sx] == "BOX":
                shattered = True
                break
            if self.occ[sy][sx] == "TNT":
                self.tnt_armed.add((sx, sy))
                shattered = True
                break
            tt = self.terrain[sy][sx]
            if tt == "SWITCH":
                self.gates = not self.gates
                shattered = True
                break
            if tt == "MIMIC":
                self._clear_mimic(sx, sy)
                shattered = True
                break
            if tt in MIRROR_MAP:
                dname = MIRROR_MAP[tt][dname]
                dx, dy = DIRS[dname]
                continue
            if tt in PORTAL_PAIR and sp < 2:
                pair = self.portal_pos.get(PORTAL_PAIR[tt])
                if pair is not None:
                    px, py = pair
                    if in_bounds(px, py) and self.occ[py][px] not in ("BOX", "TNT"):
                        sx, sy = px, py
                        sp += 1
                        if sp == 2:
                            shattered = True
                            break
                continue
        if rng == 0 and not shattered:
            tt = self.terrain[sy][sx]
            if tt == "ICE" or tt in MIRROR_MAP:
                if tt in MIRROR_MAP:
                    dname = MIRROR_MAP[tt][dname]
                    dx, dy = DIRS[dname]
                for _ in range(32):
                    sx += dx; sy += dy
                    if not in_bounds(sx, sy):
                        break
                    if self.high(sx, sy) or self.occ[sy][sx] == "BOX":
                        break
                    if self.occ[sy][sx] == "TNT":
                        self.tnt_armed.add((sx, sy))
                        break
                    tt = self.terrain[sy][sx]
                    if tt == "SWITCH":
                        self.gates = not self.gates
                        break
                    if tt == "MIMIC":
                        self._clear_mimic(sx, sy)
                        break
                    if tt in MIRROR_MAP:
                        dname = MIRROR_MAP[tt][dname]
                        dx, dy = DIRS[dname]
                        continue
                    if tt == "ICE":
                        continue
                    if tt in PORTAL_PAIR and sp < 2:
                        pair = self.portal_pos.get(PORTAL_PAIR[tt])
                        if pair is not None:
                            px, py = pair
                            if in_bounds(px, py) and self.occ[py][px] not in ("BOX", "TNT"):
                                sx, sy = px, py
                                sp += 1
                                if sp == 2:
                                    break
                        continue
                    break

    def _bomb(self):
        if self.bombs_left <= 0:
            return
        for b in self.bombs:
            if b["x"] == self.hx and b["y"] == self.hy:
                return
        self.bombs_left -= 1
        self.bomb_id += 1
        self.bombs.append({"id": self.bomb_id, "x": self.hx, "y": self.hy, "timer": 3})

    def _explode(self, sources):
        if not sources:
            return
        queue = deque(sources)
        exploded = set(sources)
        src_list = list(sources)
        while queue:
            ex, ey = queue.popleft()
            for yy in range(ey - 1, ey + 2):
                for xx in range(ex - 1, ex + 2):
                    if not in_bounds(xx, yy):
                        continue
                    if self.occ[yy][xx] == "TNT" and (xx, yy) not in exploded:
                        exploded.add((xx, yy))
                        queue.append((xx, yy))
                        src_list.append((xx, yy))
                    for b in self.bombs:
                        if b["x"] == xx and b["y"] == yy and (xx, yy) not in exploded:
                            exploded.add((xx, yy))
                            queue.append((xx, yy))
                            src_list.append((xx, yy))
        a = 0; b = 0
        for (ex, ey) in src_list:
            if abs(ex - self.hx) <= 1 and abs(ey - self.hy) <= 1:
                is_tnt = self.occ[ey][ex] == "TNT"
                if is_tnt:
                    a += 60
                else:
                    b += 50
        if a + b > 0:
            h = max(0, self.hp)
            self.trap_damage += min(h, a + b) * (a / (a + b))
            self.hp -= (a + b)
        self.bombs = [bb for bb in self.bombs if (bb["x"], bb["y"]) not in exploded]
        union = set()
        for (ex, ey) in src_list:
            for yy in range(ey - 1, ey + 2):
                for xx in range(ex - 1, ex + 2):
                    if in_bounds(xx, yy):
                        union.add((xx, yy))
        for (xx, yy) in union:
            if self.occ[yy][xx] == "BOX":
                self.occ[yy][xx] = None
            tt = self.terrain[yy][xx]
            if tt in EXPLODE_IMMUNE:
                continue
            if tt == "CRACK":
                self.terrain[yy][xx] = "PIT"
            elif tt in EXPLODE_DESTROY:
                if tt == "MIMIC":
                    self._clear_mimic(xx, yy)
                else:
                    self.terrain[yy][xx] = "EMPTY"
        for yy in range(GRID_HEIGHT):
            for xx in range(GRID_WIDTH):
                if self.occ[yy][xx] == "BOX" and self.terrain[yy][xx] == "PIT":
                    self.occ[yy][xx] = None
                    self.terrain[yy][xx] = "EMPTY"
        if self.hp > 0 and self.terrain[self.hy][self.hx] == "PIT":
            self.trap_damage += min(self.hp, 100)
            self.hp -= 100
        if self.hp <= 0:
            self.status = "DEAD"

    def _phase_c(self):
        for b in self.bombs:
            b["timer"] -= 1
        sources = [(b["x"], b["y"]) for b in self.bombs if b["timer"] == 0]
        sources += list(self.tnt_armed)
        self.tnt_armed = set()
        if sources:
            self._explode(sources)

    def laser_rays(self):
        rays = []
        armed = set()
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                tt = self.terrain[y][x]
                if tt.startswith("LASER_"):
                    d = tt.split("_")[1]
                    dx, dy = DIRS[d]
                    cells = set()
                    for k in range(1, 11):
                        cx, cy = x + k * dx, y + k * dy
                        if not in_bounds(cx, cy):
                            break
                        if self.high(cx, cy) or self.occ[cy][cx] == "BOX":
                            break
                        if self.occ[cy][cx] == "TNT":
                            cells.add((cx, cy))
                            armed.add((cx, cy))
                            break
                        cells.add((cx, cy))
                    rays.append(cells)
        return rays, armed

    def _phase_d(self):
        rays, armed = self.laser_rays()
        m = 0
        for cells in rays:
            if cells & self.exposed:
                m += 1
        if m > 0:
            dmg = 50 * m
            self.trap_damage += min(max(0, self.hp), dmg)
            self.hp -= dmg
            if self.hp <= 0:
                self.status = "DEAD"
                return
        if armed:
            self._explode(list(armed))

    def step(self, action):
        if self.status != "ALIVE":
            return self.status
        self.turn += 1
        self.exposed = {(self.hx, self.hy)}
        self.tnt_armed = set()
        if action == "WAIT":
            pass
        elif action == "BOMB":
            self._bomb()
        elif action.startswith("MOVE_"):
            self._move(action[5:])
        elif action.startswith("JUMP_"):
            self._jump(action[5:])
        elif action.startswith("THROW_"):
            self._throw(action[6:])
        if self.status == "ALIVE":
            self._phase_c()
        if self.status == "ALIVE" and self.turn % 3 == 0:
            self._phase_d()
        return self.status

    def run(self, actions):
        for a in actions:
            self.step(a)
            if self.status != "ALIVE":
                break
        return self.status


# ==============================================================================
# 魔王造图
# ==============================================================================
def _blank_grid():
    return [
        ["T_W" if (x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1) else "EMPTY"
         for x in range(GRID_WIDTH)]
        for y in range(GRID_HEIGHT)
    ]


def _spend(grid):
    total = 0
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1:
                continue
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


def _author_bfs(grid):
    """在‘安全走廊全为平地’假设下，用简化模型 BFS 找一条无伤通关路径。"""
    # 预计算两种门态下的激光射线格
    eng0 = Engine(grid)
    rays_false, _ = eng0.laser_rays()
    beam_false = set().union(*rays_false) if rays_false else set()
    eng0.gates = True
    rays_true, _ = eng0.laser_rays()
    beam_true = set().union(*rays_true) if rays_true else set()

    terrain = eng0.terrain
    k1 = k2 = v = None
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if terrain[y][x] == "K1":
                k1 = (x, y)
            elif terrain[y][x] == "K2":
                k2 = (x, y)
            elif terrain[y][x] == "V":
                v = (x, y)

    def beam(gates):
        return beam_true if gates else beam_false

    start = (SPAWN_POS[0], SPAWN_POS[1], False, False, False, 0)
    # state: x,y,k1,k2,gates,turn_mod3 ; 记录路径
    from collections import deque as _dq
    parent = {start: None}
    q = _dq([start])
    goal = None
    while q:
        st = q.popleft()
        x, y, hk1, hk2, g, mod = st
        if (x, y) == v and hk1 and hk2:
            goal = st
            break
        turn = mod  # 即将执行的回合编号 mod3（下一步 turn = 已走步数+1）
        # 已走步数 = 路径长度；下一回合 turn%3 == (mod+1)%3 ? 我们用 mod 表示‘当前已执行回合数%3’
        next_mod = (mod + 1) % 3
        fire = (next_mod == 0)
        for act in ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT"):
            nx, ny, nk1, nk2, ng = x, y, hk1, hk2, g
            if act != "WAIT":
                d = act[5:]
                dx, dy = DIRS[d]
                nx, ny = x + dx, y + dy
                if not in_bounds(nx, ny):
                    continue
                tt = terrain[ny][nx]
                if is_high_wall(tt, g):
                    continue
                if tt in ("PIT", "MIMIC", "TNT", "BOX"):
                    continue
                if tt in MOMENTUM_TILES:
                    continue  # 安全走廊不含动量格
                if tt == "SWITCH":
                    ng = not g
                if tt == "K1":
                    nk1 = True
                if tt == "K2":
                    nk2 = True
            # 激光：开火回合需起点与终点都不在射线内（用新门态）
            if fire:
                bm = beam(ng)
                if (x, y) in bm or (nx, ny) in bm:
                    continue
            nst = (nx, ny, nk1, nk2, ng, next_mod)
            if nst not in parent:
                parent[nst] = (st, act)
                q.append(nst)
    if goal is None:
        return None
    path = []
    cur = goal
    while parent[cur] is not None:
        prev, act = parent[cur]
        path.append(act)
        cur = prev
    path.reverse()
    return path


def _main_grid():
    grid = _blank_grid()

    def setc(x, y, t):
        grid[y][x] = t

    def wall_line_v(x, y0, y1, gaps=()):
        for y in range(y0, y1 + 1):
            if y not in gaps:
                setc(x, y, "W")

    def wall_line_h(y, x0, x1, gaps=()):
        for x in range(x0, x1 + 1):
            if x not in gaps:
                setc(x, y, "W")

    # ---- 三条纵向屏障，强制 S 形长路线 ----
    wall_line_v(11, 1, 24, gaps=(3,))
    wall_line_v(23, 1, 24, gaps=(22,))
    wall_line_v(32, 1, 24, gaps=(6,))
    # 金库主门（红门，初始关，必须踩开关翻转后才开）
    setc(32, 6, "R_GATE")

    # ---- 各区内部迷宫墙，增加绕路 ----
    # 左区
    wall_line_h(8, 2, 9, gaps=(5,))
    wall_line_h(17, 2, 9, gaps=(8,))
    wall_line_v(6, 3, 7)
    wall_line_v(6, 18, 23, gaps=(20,))
    # 中区
    wall_line_h(10, 13, 21, gaps=(17,))
    wall_line_h(15, 13, 21, gaps=(15,))
    setc(15, 15, "B_GATE")  # 中区捷径蓝门：开关翻转后关闭，诱敌深入
    wall_line_v(18, 11, 14)
    wall_line_v(18, 16, 21, gaps=(19,))
    # 右中区（开关区）
    wall_line_h(9, 25, 30, gaps=(27,))
    wall_line_h(17, 25, 30, gaps=(29,))
    wall_line_v(27, 10, 16, gaps=(13,))

    # ---- 地标 ----
    setc(17, 5, "K1")
    setc(28, 21, "K2")
    setc(36, 13, "V")
    # 开关（右中区）
    setc(26, 13, "SWITCH")

    # ---- 激光（覆盖必经走廊，制造时序压力）----
    setc(9, 5, "LASER_R")     # 横切左区上行通道 x=10（单格射线）
    setc(16, 1, "LASER_D")    # 顶部横穿 y=3 的纵向火力
    setc(22, 24, "LASER_U")   # 中区下行 x=22
    setc(31, 22, "LASER_L")   # 底部横穿 y=22
    setc(26, 22, "W")         # 截断底部激光，仅留短射线
    setc(31, 1, "LASER_D")    # 右区上行 x=31
    setc(33, 13, "LASER_R")   # 金库最后冲刺 y=13

    # ---- 深渊（惩罚直线莽撞与冰道）----
    for (px, py) in [(7, 6), (8, 5), (4, 9), (16, 12), (17, 13),
                     (20, 18), (25, 20), (29, 15), (34, 8), (35, 18)]:
        setc(px, py, "PIT")

    # ---- 冰道滑向深渊 ----
    setc(17, 11, "ICE")
    setc(17, 12, "ICE")
    # (17,13) 已是 PIT：冰道下滑坠坑

    # ---- 脆冰桥（诱饵捷径，走过即塌）----
    setc(14, 13, "CRACK")
    setc(15, 13, "CRACK")
    setc(19, 13, "CRACK")
    setc(20, 13, "CRACK")

    # ---- 伪装宝箱怪 + 真补给（彼此远离，保证线索合法）----
    setc(4, 4, "MIMIC")
    setc(16, 20, "MIMIC")
    setc(26, 4, "MIMIC")
    setc(35, 20, "MIMIC")
    setc(9, 21, "HEAL")
    setc(29, 7, "HEAL")

    # ---- TNT（诱饵死路，远离安全走廊与激光射线）----
    setc(3, 3, "TNT")
    setc(20, 23, "TNT")
    setc(36, 4, "TNT")

    # ---- 弹簧（把莽撞者弹进深渊）----
    setc(13, 20, "SPRING_D")
    setc(30, 10, "SPRING_U")

    # ---- 折跃镜（冰道折转陷阱）----
    setc(21, 12, "MIRROR_SW")
    setc(34, 16, "MIRROR_NE")

    # ---- 传送门陷阱：入口在诱饵直线，出口封死小室 ----
    setc(14, 8, "PORTAL_1A")
    setc(36, 22, "PORTAL_1B")
    for (wx, wy) in [(35, 21), (37, 21), (35, 23), (37, 23), (36, 21), (36, 23)]:
        if in_bounds(wx, wy) and grid[wy][wx] == "EMPTY":
            setc(wx, wy, "W")
    setc(35, 22, "W")
    setc(37, 22, "W")

    # ---- 出生净空区强制 EMPTY ----
    for y in range(12, 15):
        for x in range(1, 4):
            setc(x, y, "EMPTY")
    return grid


def _layout_ok(grid):
    """魔王图硬性约束全量自检；任一不符即回退，杜绝废标。"""
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
    (kx1, ky1), = lm["K1"]; (kx2, ky2), = lm["K2"]; (vx, vy), = lm["V"]
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
        ("LASER_U", "LASER_D", "LASER_L", "LASER_R"): 12,
        ("CRACK",): 40, ("SWITCH",): 6,
        ("R_GATE", "B_GATE"): 16, ("TNT",): 12,
        ("BOX",): 4, ("HEAL",): 4, ("MIMIC",): 4,
    }
    for group, cap in caps.items():
        if sum(counts.get(t, 0) for t in group) > cap:
            return False
    for n in ("1", "2"):
        a = counts.get("PORTAL_%sA" % n, 0)
        b = counts.get("PORTAL_%sB" % n, 0)
        if (a > 0) != (b > 0) or a > 1 or b > 1:
            return False
    eng = Engine(grid)
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if grid[y][x] == "MIMIC" and (x, y) not in eng.mimic_clue:
                return False
    return True


def build_dungeon() -> dict:
    grid = _main_grid()

    # ---- 预算与合法性兜底 ----
    if not _layout_ok(grid):
        return _fallback_dungeon()

    sol = _author_bfs(grid)
    if sol is None or not (1 <= len(sol) <= MAX_TURNS):
        return _fallback_dungeon()

    # 用完整引擎回放自证
    eng = Engine(grid)
    status = eng.run(sol)
    if status != "CLEARED" or eng.turn != len(sol):
        return _fallback_dungeon()
    # 确保最后一步恰好首次通关（run 已在 CLEARED 时停止）
    return {
        "taunt": "迷雾深处，金库冷笑；勇者枯骨，铺我王座。",
        "grid": grid,
        "author_solution": sol,
    }


# ==============================================================================
# 勇者：BLIND 迷雾增量建图 + 安全 A* 破阵
# ==============================================================================
def _light_slide(terrain, occ, gates, sx, sy, dname, hero_pos, portal_pos):
    """在信念地图上模拟一次动量滑行，返回 (rest, cells, touched_unknown, hit_hazard)。
    仅用于规划；UNKNOWN 视为可入但标记。已知 PIT/MIMIC 视为危险。"""
    x, y = sx, sy
    cells = [(x, y)]
    touched_unknown = terrain[y][x] == "UNKNOWN"
    hazard = False
    steps = 0
    portals = 0
    suppress = False

    def high(xx, yy):
        if not in_bounds(xx, yy):
            return True
        return is_high_wall(terrain[yy][xx], gates)

    def enterable(xx, yy):
        if not in_bounds(xx, yy):
            return False
        if high(xx, yy):
            return False
        if occ[yy][xx] in ("BOX", "TNT"):
            return False
        return True

    cur_dir = dname
    while True:
        tt = terrain[y][x]
        if tt == "UNKNOWN":
            touched_unknown = True
        if tt in ("PIT", "MIMIC"):
            hazard = True
            return (x, y), cells, touched_unknown, hazard
        if steps >= 32:
            return (x, y), cells, touched_unknown, hazard
        dx, dy = DIRS[cur_dir]
        if tt == "ICE":
            nx, ny = x + dx, y + dy
            if enterable(nx, ny):
                x, y = nx, ny
                steps += 1
                cells.append((x, y))
                continue
            return (x, y), cells, touched_unknown, hazard
        if tt in MIRROR_MAP:
            cur_dir = MIRROR_MAP[tt][cur_dir]
            dx, dy = DIRS[cur_dir]
            nx, ny = x + dx, y + dy
            if enterable(nx, ny):
                x, y = nx, ny
                steps += 1
                cells.append((x, y))
                continue
            return (x, y), cells, touched_unknown, hazard
        if tt.startswith("SPRING_"):
            sd = tt.split("_")[1]
            sdx, sdy = DIRS[sd]
            bk = None
            for k in (1, 2, 3):
                px, py = x + k * sdx, y + k * sdy
                if not in_bounds(px, py) or high(px, py) or occ[py][px] in ("BOX", "TNT"):
                    bk = k
                    break
            if bk is None:
                nx, ny = x + 3 * sdx, y + 3 * sdy
            elif bk == 1:
                return (x, y), cells, touched_unknown, hazard
            else:
                nx, ny = x + (bk - 1) * sdx, y + (bk - 1) * sdy
            cur_dir = sd
            x, y = nx, ny
            steps += 1
            cells.append((x, y))
            continue
        if tt in PORTAL_PAIR and not suppress:
            pair = portal_pos.get(PORTAL_PAIR[tt])
            if pair is not None:
                px, py = pair
                if in_bounds(px, py) and occ[py][px] is None:
                    x, y = px, py
                    portals += 1
                    steps += 1
                    cells.append((x, y))
                    suppress = True
                    if portals >= 2:
                        return (x, y), cells, touched_unknown, hazard
                    continue
            return (x, y), cells, touched_unknown, hazard
        # 普通地面
        return (x, y), cells, touched_unknown, hazard


def _compute_beams(terrain, occ, gates, portal_pos):
    beams = set()
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            tt = terrain[y][x]
            if tt.startswith("LASER_"):
                d = tt.split("_")[1]
                dx, dy = DIRS[d]
                for k in range(1, 11):
                    cx, cy = x + k * dx, y + k * dy
                    if not in_bounds(cx, cy):
                        break
                    if is_high_wall(terrain[cy][cx], gates) or occ[cy][cx] == "BOX":
                        break
                    if occ[cy][cx] == "TNT":
                        beams.add((cx, cy))
                        break
                    beams.add((cx, cy))
    return beams


def decide_action(state: dict, memory: dict) -> str:
    try:
        return _decide(state, memory)
    except Exception:
        try:
            return _safe_fallback(state, memory)
        except Exception:
            return "WAIT"


def _safe_fallback(state, memory):
    hero = state["hero"]
    hx, hy = hero["x"], hero["y"]
    terrain = state.get("terrain")
    gates = state.get("gates_flipped", False)
    turn = state.get("turn", 1)
    beams = set()
    if turn % 3 == 0:
        for w in state.get("laser_warnings", []):
            beams.add((w["x"], w["y"]))
    best = "WAIT"
    targets = state.get("targets", {})
    keys = hero.get("keys", [False, False])
    if not keys[0]:
        tgt = targets.get("K1")
    elif not keys[1]:
        tgt = targets.get("K2")
    else:
        tgt = targets.get("V")
    bestd = None
    for d in DIR_NAMES:
        dx, dy = DIRS[d]
        nx, ny = hx + dx, hy + dy
        if not in_bounds(nx, ny):
            continue
        tt = terrain[ny][nx] if terrain else "UNKNOWN"
        if is_high_wall(tt, gates) or tt in ("PIT", "TNT", "BOX", "MIMIC"):
            continue
        if turn % 3 == 0 and ((nx, ny) in beams or (hx, hy) in beams):
            continue
        if tgt:
            dist = abs(nx - tgt[0]) + abs(ny - tgt[1])
            if bestd is None or dist < bestd:
                bestd = dist
                best = "MOVE_" + d
    if turn % 3 == 0 and (hx, hy) in beams and best == "WAIT":
        for d in DIR_NAMES:
            dx, dy = DIRS[d]
            nx, ny = hx + dx, hy + dy
            if in_bounds(nx, ny) and (nx, ny) not in beams:
                tt = terrain[ny][nx] if terrain else "UNKNOWN"
                if not is_high_wall(tt, gates) and tt not in ("PIT",):
                    return "MOVE_" + d
    return best


def _decide(state, memory):
    hero = state["hero"]
    hx, hy = hero["x"], hero["y"]
    hp = hero["hp"]
    keys = hero.get("keys", [False, False])
    jumps = hero.get("jumps", 0)
    throws = hero.get("throws", 0)
    bombs = hero.get("bombs", 0)
    gates = state.get("gates_flipped", False)
    turn = state.get("turn", 1)
    vis = state.get("visible_mask")
    sterr = state.get("terrain")
    socc = state.get("occupant")
    sclues = state.get("clues")
    targets = state.get("targets", {})
    warnings = state.get("laser_warnings") or []

    # ---- 增量记忆建图 ----
    if "kmap" not in memory:
        memory["kmap"] = [["UNKNOWN"] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        memory["omap"] = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        memory["clues_seen"] = set()
        memory["chest_class"] = {}
        memory["beam_zones"] = set()
        memory["plan"] = []
        memory["plan_key"] = None
        memory["plan_pos"] = None
        memory["last_pos"] = None
        memory["pos_hist"] = deque(maxlen=24)
        memory["stuck"] = 0
        memory["bomb_site"] = None
        memory["bomb_turn"] = -1
    kmap = memory["kmap"]
    omap = memory["omap"]

    # 推断：上一回合离开 CRACK -> 永久 PIT
    lp = memory.get("last_pos")
    if lp is not None and lp != (hx, hy):
        px, py = lp
        if kmap[py][px] == "CRACK":
            kmap[py][px] = "PIT"

    # 可见信息更新
    if vis and sterr:
        for y in range(GRID_HEIGHT):
            row_v = vis[y]
            for x in range(GRID_WIDTH):
                if row_v[x]:
                    kmap[y][x] = sterr[y][x]
                    omap[y][x] = socc[y][x] if socc else None
                    if sclues and sclues[y][x]:
                        memory["clues_seen"].add((x, y))

    # 宝箱分类：邻接骸骨线索 => MIMIC；四邻全可见且无线索 => HEAL
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if kmap[y][x] == "CHEST":
                adj_clue = any((x + dx, y + dy) in memory["clues_seen"]
                               for (dx, dy) in ((0, -1), (0, 1), (-1, 0), (1, 0)))
                if adj_clue:
                    memory["chest_class"][(x, y)] = "MIMIC"
                else:
                    all_vis = all(in_bounds(x + dx, y + dy) and vis and vis[y + dy][x + dx]
                                  for (dx, dy) in ((0, -1), (0, 1), (-1, 0), (1, 0)))
                    if all_vis:
                        memory["chest_class"][(x, y)] = "HEAL"
                    elif (x, y) not in memory["chest_class"]:
                        memory["chest_class"][(x, y)] = "UNKNOWN_CHEST"
            elif (x, y) in memory["chest_class"]:
                del memory["chest_class"][(x, y)]

    # 卡住检测
    ph = memory["pos_hist"]
    if ph.count((hx, hy)) >= 3:
        memory["stuck"] += 1
    else:
        memory["stuck"] = 0
    ph.append((hx, hy))
    memory["last_pos"] = (hx, hy)
    stuck = memory["stuck"]

    # ---- 由激光预警反推潜在射线区（含未见炮座的延伸段）----
    if turn % 3 == 0 and warnings:
        groups = {}
        for w in warnings:
            x, y = w["x"], w["y"]
            memory["beam_zones"].add((x, y))
            d = w.get("dir", "U")
            key = ("V", x) if d in ("U", "D") else ("H", y)
            groups.setdefault(key, []).append((x, y))
        bz = memory["beam_zones"]
        for (orient, c), cells in groups.items():
            if orient == "V":
                ys = [p[1] for p in cells]
                lo, hi = min(ys), max(ys)
                for yy in range(lo + 1, min(GRID_HEIGHT - 2, lo + 9) + 1):
                    if is_high_wall(kmap[yy][c], gates):
                        break
                    bz.add((c, yy))
                for yy in range(hi - 1, max(1, hi - 9) - 1, -1):
                    if is_high_wall(kmap[yy][c], gates):
                        break
                    bz.add((c, yy))
            else:
                xs = [p[0] for p in cells]
                lo, hi = min(xs), max(xs)
                for xx in range(lo + 1, min(GRID_WIDTH - 2, lo + 9) + 1):
                    if is_high_wall(kmap[c][xx], gates):
                        break
                    bz.add((xx, c))
                for xx in range(hi - 1, max(1, hi - 9) - 1, -1):
                    if is_high_wall(kmap[c][xx], gates):
                        break
                    bz.add((xx, c))

    # ---- 目标选择 ----
    def md(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    k1 = tuple(targets["K1"]) if targets.get("K1") else None
    k2 = tuple(targets["K2"]) if targets.get("K2") else None
    v = tuple(targets["V"]) if targets.get("V") else None
    if not keys[0] and not keys[1]:
        if k1 and k2:
            tgt = k1 if md((hx, hy), k1) <= md((hx, hy), k2) else k2
        else:
            tgt = k1 or k2
    elif not keys[0]:
        tgt = k1
    elif not keys[1]:
        tgt = k2
    else:
        tgt = v
    if tgt is None:
        return "WAIT"
    # 低血量优先找真补给
    if hp <= 55:
        heals = [p for p, c in memory["chest_class"].items()
                 if c == "HEAL" and kmap[p[1]][p[0]] == "CHEST"]
        if heals:
            bh = min(heals, key=lambda p: md((hx, hy), p))
            if md((hx, hy), bh) <= 18:
                tgt = bh

    # ---- 激光威胁集合 ----
    portal_pos = {}
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if kmap[y][x] in PORTAL_PAIR:
                portal_pos[kmap[y][x]] = (x, y)
    beams_now = _compute_beams(kmap, omap, gates, portal_pos)
    warn_cells = {(w["x"], w["y"]) for w in warnings}
    laser_danger = beams_now | memory["beam_zones"] | warn_cells

    # ---- 信念地图与阻挡表 ----
    belief = [["EMPTY"] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    blocked = [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    cost = [[1.0] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            tt = kmap[y][x]
            belief[y][x] = "EMPTY" if tt == "UNKNOWN" else tt
            o = omap[y][x]
            if is_high_wall(tt, gates) or tt == "PIT" or o in ("TNT", "BOX"):
                blocked[y][x] = True
            if tt == "UNKNOWN":
                cost[y][x] = 2.5
            if tt == "CHEST":
                cls = memory["chest_class"].get((x, y), "UNKNOWN_CHEST")
                if cls == "MIMIC":
                    blocked[y][x] = True
                    belief[y][x] = "MIMIC"
                elif cls == "UNKNOWN_CHEST":
                    blocked[y][x] = True
                    belief[y][x] = "MIMIC"
                else:
                    belief[y][x] = "HEAL"
                    if hp < 100:
                        cost[y][x] = 0.4
            if tt == "MIMIC":
                blocked[y][x] = True

    # 动量格滑行预计算
    momentum_rest = {}
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            tt = belief[y][x]
            if tt in MOMENTUM_TILES and not blocked[y][x]:
                for d in DIR_NAMES:
                    momentum_rest[(x, y, d)] = _light_slide(
                        belief, omap, gates, x, y, d, (hx, hy), portal_pos)

    relax = stuck > 12
    fire_this = (turn % 3 == 0)
    vault_goal = (v is not None and tgt == v and keys[0] and keys[1])

    # ---- 炸弹撤退模式 ----
    bs = memory.get("bomb_site")
    if bs is not None:
        bt = memory["bomb_turn"]
        if turn > bt + 2:
            memory["bomb_site"] = None
        else:
            cheb = max(abs(hx - bs[0]), abs(hy - bs[1]))
            if cheb >= 2:
                return _wait_or_safe(state, memory, belief, omap, gates, kmap,
                                     laser_danger, hx, hy, hp, keys, turn, relax)
            # 尚未安全：本回合必须移动到切比雪夫距离>=2 的格子
            for d in DIR_NAMES:
                dx, dy = DIRS[d]
                nx, ny = hx + dx, hy + dy
                if not in_bounds(nx, ny):
                    continue
                if max(abs(nx - bs[0]), abs(ny - bs[1])) < 2:
                    continue
                act = "MOVE_" + d
                vv = _validate_action(state, memory, act, belief, omap, gates, kmap,
                                      laser_danger, hx, hy, hp, keys, turn, relax)
                if vv is not None:
                    return vv
            if turn < bt + 2:
                # 还有一回合缓冲：先挪向远离爆心的可入格
                best = None
                for d in DIR_NAMES:
                    dx, dy = DIRS[d]
                    nx, ny = hx + dx, hy + dy
                    if not in_bounds(nx, ny) or blocked[ny][nx]:
                        continue
                    nd = max(abs(nx - bs[0]), abs(ny - bs[1]))
                    if best is None or nd > best[0]:
                        best = (nd, "MOVE_" + d)
                if best is not None:
                    vv = _validate_action(state, memory, best[1], belief, omap, gates,
                                          kmap, laser_danger, hx, hy, hp, keys, turn, relax)
                    if vv is not None:
                        return vv
            return _wait_or_safe(state, memory, belief, omap, gates, kmap,
                                 laser_danger, hx, hy, hp, keys, turn, relax)

    # ---- 计划承诺：沿已验证的时序计划连续执行 ----
    plan_key = (tgt, bool(keys[0]), bool(keys[1]), bool(gates))
    plan = memory.get("plan") or []
    if plan and memory.get("plan_key") == plan_key and memory.get("plan_pos") == (hx, hy):
        act, rest = plan[0]
        vv = _validate_action(state, memory, act, belief, omap, gates, kmap,
                              laser_danger, hx, hy, hp, keys, turn, relax)
        if vv is not None:
            memory["plan"] = plan[1:]
            memory["plan_pos"] = rest
            return vv
        memory["plan"] = []

    # ---- 相位感知 A* 重规划 ----
    path = _plan_path(belief, blocked, cost, kmap, omap, gates, (hx, hy), tgt, turn,
                      laser_danger, momentum_rest, jumps, vault_goal, stuck)
    if path:
        act, rest = path[0]
        vv = _validate_action(state, memory, act, belief, omap, gates, kmap,
                              laser_danger, hx, hy, hp, keys, turn, relax)
        if vv is not None:
            memory["plan"] = path[1:]
            memory["plan_key"] = plan_key
            memory["plan_pos"] = rest
            return vv

    # ---- 炸弹破墙：若已贴墙则直接炸，否则先导航到可炸墙边 ----
    if bombs > 0 and bs is None:
        ba = _bomb_opportunity(state, memory, belief, omap, gates, kmap,
                               laser_danger, hx, hy, hp, keys, turn, tgt, blocked)
        if ba is not None:
            return ba
        stand = _bomb_approach_target(belief, blocked, kmap, gates, (hx, hy), tgt)
        if stand is not None and stand != (hx, hy):
            path2 = _plan_path(belief, blocked, cost, kmap, omap, gates, (hx, hy), stand,
                               turn, laser_danger, momentum_rest, jumps, False, stuck)
            if path2:
                act, rest = path2[0]
                vv = _validate_action(state, memory, act, belief, omap, gates, kmap,
                                      laser_danger, hx, hy, hp, keys, turn, relax)
                if vv is not None:
                    memory["plan"] = path2[1:]
                    memory["plan_key"] = plan_key
                    memory["plan_pos"] = rest
                    return vv

    # ---- 道具破局：飞石引爆 TNT / 触发开关 ----
    if throws > 0:
        ta = _throw_opportunity(state, memory, belief, omap, gates, kmap,
                                laser_danger, hx, hy, hp, keys, turn, tgt)
        if ta is not None:
            return ta

    # ---- 探索兜底 ----
    act = _explore_move(kmap, omap, gates, hx, hy, tgt, turn, laser_danger,
                        memory, belief, blocked, relax)
    vv = _validate_action(state, memory, act, belief, omap, gates, kmap,
                          laser_danger, hx, hy, hp, keys, turn, relax)
    if vv is not None:
        return vv
    return _wait_or_safe(state, memory, belief, omap, gates, kmap,
                         laser_danger, hx, hy, hp, keys, turn, relax)


def _dir_toward(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if abs(dx) >= abs(dy):
        if dx > 0:
            return "R"
        if dx < 0:
            return "L"
    if dy > 0:
        return "D"
    if dy < 0:
        return "U"
    return None


def _forward_exit(rest, came_from, belief, omap, laser_danger, gates):
    """rest 若是激光格，必须存在一个‘非激光且可入’的前向出口（不等于来路），否则是死路。"""
    rx, ry = rest
    if rest not in laser_danger:
        return True
    for d in DIR_NAMES:
        dx, dy = DIRS[d]
        nx, ny = rx + dx, ry + dy
        if not in_bounds(nx, ny) or (nx, ny) == came_from:
            continue
        tt = belief[ny][nx]
        if is_high_wall(tt, gates) or tt in ("PIT", "MIMIC"):
            continue
        if omap[ny][nx] in ("BOX", "TNT"):
            continue
        if (nx, ny) in laser_danger:
            continue
        return True
    return False


def _retreat_cells(kmap, omap, gates, site, belief, blocked):
    out = []
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if max(abs(x - site[0]), abs(y - site[1])) >= 2 and not blocked[y][x]:
                if belief[y][x] not in ("PIT", "MIMIC"):
                    out.append((x, y))
    return out


def _wait_or_safe(state, memory, belief, omap, gates, kmap, laser_danger,
                  hx, hy, hp, keys, turn, relax):
    if not (turn % 3 == 0 and (hx, hy) in laser_danger):
        return "WAIT"
    for d in DIR_NAMES:
        act = "MOVE_" + d
        vv = _validate_action(state, memory, act, belief, omap, gates, kmap,
                              laser_danger, hx, hy, hp, keys, turn, relax)
        if vv is not None:
            return vv
    return _safe_fallback(state, memory)


def _plan_path(belief, blocked, cost, kmap, omap, gates, start, goal, turn,
               laser_danger, momentum_rest, jumps, vault_goal, stuck):
    """相位感知 A*：状态=(x,y,turn%3)，支持 WAIT 调相与动量折叠。返回 [(action, rest), ...]。"""
    gx, gy = goal
    sx, sy = start
    start_state = (sx, sy, turn % 3)

    def h(x, y):
        return (abs(x - gx) + abs(y - gy)) * 0.9

    gscore = {start_state: 0.0}
    parent = {start_state: None}
    heap = [(h(sx, sy), 0.0, start_state)]
    closed = set()
    found = None
    exp = 0
    unk_penalty = 2.0 if stuck > 8 else 8.0
    while heap and exp < 9000:
        _, g, st = heapq.heappop(heap)
        if st in closed:
            continue
        closed.add(st)
        exp += 1
        x, y, mod = st
        if (x, y) == (gx, gy):
            found = st
            break
        nmod = (mod + 1) % 3
        fire = (mod == 0)
        next_fire = (nmod == 0)
        # WAIT 调相
        if not (fire and (x, y) in laser_danger) and not (next_fire and (x, y) in laser_danger):
            if (x, y) not in laser_danger or _forward_exit((x, y), (x, y), belief, omap, laser_danger, gates):
                ns = (x, y, nmod)
                ng = g + 1.15
                if ns not in gscore or ng < gscore[ns]:
                    gscore[ns] = ng
                    parent[ns] = (st, "WAIT", (x, y))
                    heapq.heappush(heap, (ng + h(x, y), ng, ns))
        # MOVE（含推箱近似）
        for d in DIR_NAMES:
            dx, dy = DIRS[d]
            nx, ny = x + dx, y + dy
            if not in_bounds(nx, ny):
                continue
            push = False
            if omap[ny][nx] == "BOX":
                # 推箱：箱后一格须可入且非动量；箱下若是 CRACK 则推后塌坑，禁止
                bx, by = nx + dx, ny + dy
                if not in_bounds(bx, by) or blocked[by][bx]:
                    continue
                if belief[by][bx] in MOMENTUM_TILES or belief[by][bx] in ("PIT", "MIMIC", "K1", "K2", "V"):
                    continue
                if kmap[ny][nx] == "CRACK":
                    continue
                push = True
            elif blocked[ny][nx]:
                continue
            if push:
                tt = belief[ny][nx]
                if tt in MOMENTUM_TILES:
                    mr = momentum_rest.get((nx, ny, d))
                    if mr is None:
                        continue
                    rest, cells, unk, haz = mr
                    if haz or (unk and stuck <= 8):
                        continue
                    exposure = [(x, y)] + cells
                    risk = unk_penalty if unk else 0.0
                else:
                    rest = (nx, ny)
                    exposure = [(x, y), (nx, ny)]
                    risk = 0.0
                ng = g + 1.6 + risk
            else:
                tt = belief[ny][nx]
                if tt in MOMENTUM_TILES:
                    mr = momentum_rest.get((nx, ny, d))
                    if mr is None:
                        continue
                    rest, cells, unk, haz = mr
                    if haz:
                        continue
                    if blocked[rest[1]][rest[0]]:
                        continue
                    exposure = [(x, y)] + cells
                    risk = unk_penalty if unk else 0.0
                else:
                    rest = (nx, ny)
                    exposure = [(x, y), (nx, ny)]
                    risk = 0.0
                ng = g + cost[ny][nx] + risk
            is_goal_edge = vault_goal and rest == (gx, gy)
            if not is_goal_edge:
                if fire and any(c in laser_danger for c in exposure):
                    continue
                if next_fire and rest in laser_danger:
                    continue
                if rest in laser_danger and not _forward_exit(rest, (x, y), belief, omap, laser_danger, gates):
                    continue
            ns = (rest[0], rest[1], nmod)
            if ns not in gscore or ng < gscore[ns]:
                gscore[ns] = ng
                parent[ns] = (st, "MOVE_" + d, rest)
                heapq.heappush(heap, (ng + h(rest[0], rest[1]), ng, ns))
        # JUMP（保留资源，仅必要时用）
        if jumps > 0:
            for d in DIR_NAMES:
                dx, dy = DIRS[d]
                mx, my = x + dx, y + dy
                nx, ny = x + 2 * dx, y + 2 * dy
                if not in_bounds(nx, ny) or not in_bounds(mx, my):
                    continue
                if is_high_wall(belief[my][mx], gates):
                    continue
                if is_high_wall(belief[ny][nx], gates) or omap[ny][nx] in ("BOX", "TNT"):
                    continue
                if blocked[ny][nx]:
                    continue
                tt = belief[ny][nx]
                if tt in MOMENTUM_TILES:
                    mr = momentum_rest.get((nx, ny, d))
                    if mr is None:
                        continue
                    rest, cells, unk, haz = mr
                    if haz or unk:
                        continue
                    exposure = [(x, y)] + cells
                else:
                    rest = (nx, ny)
                    exposure = [(x, y), (nx, ny)]
                is_goal_edge = vault_goal and rest == (gx, gy)
                if not is_goal_edge:
                    if fire and any(c in laser_danger for c in exposure):
                        continue
                    if next_fire and rest in laser_danger:
                        continue
                ng = g + 6.0
                ns = (rest[0], rest[1], nmod)
                if ns not in gscore or ng < gscore[ns]:
                    gscore[ns] = ng
                    parent[ns] = (st, "JUMP_" + d, rest)
                    heapq.heappush(heap, (ng + h(rest[0], rest[1]), ng, ns))
    if found is None:
        return None
    path = []
    cur = found
    while parent[cur] is not None:
        prev, act, rest = parent[cur]
        path.append((act, rest))
        cur = prev
    path.reverse()
    return path


def _throw_opportunity(state, memory, belief, omap, gates, kmap, laser_danger,
                       hx, hy, hp, keys, turn, tgt):
    """飞石：引爆挡路 TNT 或远程触发开关（引擎全程验证，含爆炸自伤检查）。"""
    grid = [row[:] for row in belief]
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if omap[y][x] in ("BOX", "TNT"):
                grid[y][x] = omap[y][x]
    hero = {"x": hx, "y": hy, "hp": hp, "k1": keys[0], "k2": keys[1],
            "jumps": state["hero"].get("jumps", 0),
            "throws": state["hero"].get("throws", 0),
            "bombs": state["hero"].get("bombs", 0)}
    best = None
    tnt_before = sum(1 for y in range(GRID_HEIGHT) for x in range(GRID_WIDTH)
                     if omap[y][x] == "TNT")
    for d in DIR_NAMES:
        eng = Engine(grid, hero=dict(hero), gates_flipped=gates, turn=turn - 1)
        eng.step("THROW_" + d)
        if eng.status == "DEAD" or eng.hp < hp:
            continue
        if turn % 3 == 0 and (eng.exposed & laser_danger):
            continue
        tnt_after = sum(1 for y in range(GRID_HEIGHT) for x in range(GRID_WIDTH)
                        if eng.occ[y][x] == "TNT")
        useful = (tnt_after < tnt_before) or (eng.gates != gates)
        if not useful:
            continue
        # 爆炸波及检查已在 eng.hp 中体现；TNT 待爆将在阶段C引爆
        dd = abs(hx - tgt[0]) + abs(hy - tgt[1])
        if best is None or dd < best[0]:
            best = (dd, "THROW_" + d)
    return best[1] if best else None


def _bomb_approach_target(belief, blocked, kmap, gates, start, tgt):
    """寻路失败时：找一面可炸的 W 墙（英雄侧可达、墙后非钛金/深渊），返回贴墙站立格。"""
    seen = {start}
    q = deque([start])
    reach = []
    while q:
        p = q.popleft()
        reach.append(p)
        for d in DIR_NAMES:
            dx, dy = DIRS[d]
            nx, ny = p[0] + dx, p[1] + dy
            if not in_bounds(nx, ny) or (nx, ny) in seen:
                continue
            if blocked[ny][nx] or belief[ny][nx] in MOMENTUM_TILES:
                continue
            seen.add((nx, ny))
            q.append((nx, ny))
    best = None
    for r in reach:
        for d in DIR_NAMES:
            dx, dy = DIRS[d]
            wx, wy = r[0] + dx, r[1] + dy
            if not in_bounds(wx, wy) or kmap[wy][wx] != "W":
                continue
            fx, fy = wx + dx, wy + dy
            if not in_bounds(fx, fy):
                continue
            ft = kmap[fy][fx]
            if ft == "T_W" or ft == "PIT" or is_high_wall(ft, gates):
                continue
            score = md2((fx, fy), tgt) + 0.3 * md2(start, r)
            if best is None or score < best[0]:
                best = (score, r)
    return best[1] if best else None


def _bomb_opportunity(state, memory, belief, omap, gates, kmap, laser_danger,
                      hx, hy, hp, keys, turn, tgt, blocked):
    """炸弹破墙： adjacent W 且墙后 toward-target 可入；随后进入撤退模式。"""
    for d in DIR_NAMES:
        dx, dy = DIRS[d]
        wx, wy = hx + dx, hy + dy
        if not in_bounds(wx, wy) or kmap[wy][wx] != "W":
            continue
        bx, by = hx + 2 * dx, hy + 2 * dy
        if not in_bounds(bx, by):
            continue
        if blocked[by][bx] and kmap[by][bx] != "UNKNOWN":
            continue
        if abs(bx - tgt[0]) + abs(by - tgt[1]) >= abs(hx - tgt[0]) + abs(hy - tgt[1]):
            continue
        # 必须存在撤退格
        retreat = [p for p in _retreat_cells(kmap, omap, gates, (hx, hy), belief, blocked)
                   if md2(p, (hx, hy)) <= 2]
        if not retreat:
            continue
        # 验证本回合 BOMB 安全
        vv = _validate_action(state, memory, "BOMB", belief, omap, gates, kmap,
                              laser_danger, hx, hy, hp, keys, turn, False)
        if vv is None:
            continue
        memory["bomb_site"] = (hx, hy)
        memory["bomb_turn"] = turn
        memory["plan"] = []
        return "BOMB"
    return None


def md2(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _explore_move(kmap, omap, gates, hx, hy, tgt, turn, laser_danger,
                  memory, belief, blocked, relax):
    fire_this = (turn % 3 == 0)
    fire_next = ((turn + 1) % 3 == 0)
    cands = []
    ph = memory["pos_hist"]
    for d in DIR_NAMES:
        dx, dy = DIRS[d]
        nx, ny = hx + dx, hy + dy
        if not in_bounds(nx, ny):
            continue
        tt = kmap[ny][nx]
        if is_high_wall(tt, gates) or tt in ("PIT", "MIMIC", "TNT", "BOX"):
            continue
        if omap[ny][nx] in ("TNT", "BOX"):
            continue
        if tt == "CHEST" and memory["chest_class"].get((nx, ny)) != "HEAL":
            continue
        if tt in MOMENTUM_TILES and not relax:
            continue
        if fire_this and ((nx, ny) in laser_danger or (hx, hy) in laser_danger):
            continue
        if fire_next and (nx, ny) in laser_danger:
            continue
        if (nx, ny) in laser_danger and not _forward_exit((nx, ny), (hx, hy), belief, omap, laser_danger, gates):
            continue
        dist = abs(nx - tgt[0]) + abs(ny - tgt[1])
        unk_bonus = 0.0 if tt == "UNKNOWN" else 0.6
        revisit = ph.count((nx, ny)) * 1.5
        cands.append((dist + unk_bonus + revisit, d))
    if cands:
        cands.sort()
        return "MOVE_" + cands[0][1]
    return "WAIT"


def _validate_action(state, memory, action, belief, omap, gates, kmap,
                     laser_danger, hx, hy, hp, keys, turn, relax):
    """完整引擎在信念世界上回放一步：拒绝已知死亡/掉血/开火受击/滑入未知。"""
    if action is None:
        return None
    if action == "WAIT":
        if turn % 3 == 0 and (hx, hy) in laser_danger:
            return None
        return action
    grid = [row[:] for row in belief]
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if omap[y][x] in ("BOX", "TNT"):
                grid[y][x] = omap[y][x]
    hero = {"x": hx, "y": hy, "hp": hp, "k1": keys[0], "k2": keys[1],
            "jumps": state["hero"].get("jumps", 0),
            "throws": state["hero"].get("throws", 0),
            "bombs": state["hero"].get("bombs", 0)}
    eng = Engine(grid, hero=hero, gates_flipped=gates, turn=turn - 1)
    before_hp = eng.hp
    eng.step(action)
    if eng.status == "CLEARED":
        return action
    if eng.status == "DEAD" or eng.hp < before_hp:
        return None
    if turn % 3 == 0 and (eng.exposed & laser_danger):
        return None
    rest = (eng.hx, eng.hy)
    if (turn + 1) % 3 == 0 and rest in laser_danger:
        return None
    if rest in laser_danger and not _forward_exit(rest, (hx, hy), belief, omap, laser_danger, gates):
        return None
    if not relax:
        for (cx, cy) in eng.exposed:
            if kmap[cy][cx] == "UNKNOWN":
                return None
    return action