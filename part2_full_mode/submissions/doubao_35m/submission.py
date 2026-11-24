import heapq
import time
import collections
import copy
import math

GRID_WIDTH = 40
GRID_HEIGHT = 26
GW = 40
GH = 26
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
DIR_NAME = {(0, -1): "U", (0, 1): "D", (-1, 0): "L", (1, 0): "R"}

MIRROR = {
    "MIRROR_NE": {"R": "D", "D": "R", "U": "L", "L": "U"},
    "MIRROR_SW": {"R": "D", "D": "R", "U": "L", "L": "U"},
    "MIRROR_NW": {"R": "U", "U": "R", "D": "L", "L": "D"},
    "MIRROR_SE": {"R": "U", "U": "R", "D": "L", "L": "D"},
}

DESTRUCT_TO = {
    "W": "EMPTY", "ICE": "EMPTY", "CRACK": "PIT",
    "R_GATE": "EMPTY", "B_GATE": "EMPTY",
    "SWITCH": "EMPTY", "HEAL": "EMPTY", "MIMIC": "EMPTY",
    "SPRING_U": "EMPTY", "SPRING_D": "EMPTY", "SPRING_L": "EMPTY", "SPRING_R": "EMPTY",
    "MIRROR_NE": "EMPTY", "MIRROR_SE": "EMPTY", "MIRROR_SW": "EMPTY", "MIRROR_NW": "EMPTY",
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

# Tiles that count toward the 120 interior T_W / component caps etc.
HIGH_WALL_BASE = ("W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R",
                  "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R")


def in_b(x, y):
    return 0 <= x < GW and 0 <= y < GH


def plates_active(terrain, occ):
    found = False
    for y in range(GH):
        for x in range(GW):
            if terrain[y][x] == "PLATE":
                found = True
                if occ[y][x] != "BOX":
                    return False
    return found


def is_high_wall(tile, gf, pa):
    if tile in ("W", "T_W"):
        return True
    if tile in ("LASER_U", "LASER_D", "LASER_L", "LASER_R",
                "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R"):
        return True
    if tile == "R_GATE":
        return not gf
    if tile == "B_GATE":
        return gf
    if tile == "P_GATE":
        return not pa
    return False


class World:
    def __init__(self, grid=None):
        if grid is None:
            return
        self.terrain = [row[:] for row in grid]
        self.occ = [[None] * GW for _ in range(GH)]
        for y in range(GH):
            for x in range(GW):
                t = self.terrain[y][x]
                if t in ("BOX", "TNT"):
                    self.occ[y][x] = t
                    self.terrain[y][x] = "EMPTY"
        self.hero = {"x": 2, "y": 13, "hp": 100, "keys": [False, False],
                     "jumps": 3, "throws": 3, "bombs": 2}
        self.gf = False
        self.turn = 1
        self.bombs = []
        self.status = "PLAYING"
        self.k1 = self._find("K1")
        self.k2 = self._find("K2")
        self.v = self._find("V")

    @classmethod
    def from_state(cls, state):
        w = cls()
        terrain = [row[:] for row in state["terrain"]]
        occ = [row[:] for row in state["occupant"]]
        clues = state.get("clues")
        if clues:
            for y in range(GH):
                for x in range(GW):
                    if terrain[y][x] == "CHEST":
                        terrain[y][x] = "MIMIC" if clues[y][x] else "HEAL"
        w.terrain = terrain
        w.occ = occ
        h = state["hero"]
        w.hero = {"x": h["x"], "y": h["y"], "hp": h["hp"],
                  "keys": list(h["keys"]), "jumps": h["jumps"],
                  "throws": h["throws"], "bombs": h["bombs"]}
        w.gf = state.get("gates_flipped", False)
        w.turn = state.get("turn", 1)
        w.bombs = [dict(b) for b in state.get("bombs", [])]
        tg = state.get("targets", {})
        w.k1 = tg.get("K1") or [0, 0]
        w.k2 = tg.get("K2") or [0, 0]
        w.v = tg.get("V") or [0, 0]
        w.status = "PLAYING"
        return w

    def clone(self):
        w = World()
        w.terrain = [row[:] for row in self.terrain]
        w.occ = [row[:] for row in self.occ]
        h = self.hero
        w.hero = {"x": h["x"], "y": h["y"], "hp": h["hp"],
                  "keys": list(h["keys"]), "jumps": h["jumps"],
                  "throws": h["throws"], "bombs": h["bombs"]}
        w.gf = self.gf
        w.turn = self.turn
        w.bombs = [dict(b) for b in self.bombs]
        w.k1 = self.k1
        w.k2 = self.k2
        w.v = self.v
        w.status = self.status
        return w

    def _find(self, t):
        for y in range(GH):
            for x in range(GW):
                if self.terrain[y][x] == t:
                    return [x, y]
        return None

    def pa(self):
        return plates_active(self.terrain, self.occ)

    def blocks_oneway(self, x, y, dname):
        t = self.terrain[y][x]
        if not t.startswith("ONEWAY_"):
            return False
        return t.split("_")[1] != dname

    def laser_beams(self, turn):
        cells = set()
        fire_red = (turn % 3 == 0)
        fire_blue = (turn % 4 == 0)
        if not (fire_red or fire_blue):
            return cells
        pa = self.pa()
        for y in range(GH):
            for x in range(GW):
                t = self.terrain[y][x]
                if t.startswith("LASER2_") and fire_blue:
                    d = t.split("_")[1]
                elif t.startswith("LASER_") and fire_red:
                    d = t.split("_")[1]
                else:
                    continue
                dx, dy = DIRS[d]
                for k in range(1, 11):
                    nx, ny = x + dx * k, y + dy * k
                    if not in_b(nx, ny):
                        break
                    nt = self.terrain[ny][nx]
                    if is_high_wall(nt, self.gf, pa) or self.occ[ny][nx] == "BOX":
                        break
                    cells.add((nx, ny))
        return cells

    def laser_danger_at(self, turn, pos):
        """True if a hero standing at pos at start of turn would be hit."""
        if turn % 3 != 0 and turn % 4 != 0:
            return False
        beams = self.laser_beams(turn)
        return pos in beams

    def _enterable(self, x, y, dname, pa):
        if not in_b(x, y):
            return False
        t = self.terrain[y][x]
        if is_high_wall(t, self.gf, pa):
            return False
        if self.blocks_oneway(x, y, dname):
            return False
        if self.occ[y][x] in ("BOX", "TNT"):
            return False
        if any(b["x"] == x and b["y"] == y for b in self.bombs):
            return False
        return True

    def _slide(self, x, y, dname, pa):
        d = dname
        while True:
            t = self.terrain[y][x]
            if t.startswith("MIRROR_"):
                nd = MIRROR[t].get(d, d)
                dx, dy = DIRS[nd]
                nx, ny = x + dx, y + dy
                if self._enterable(nx, ny, nd, pa):
                    x, y = nx, ny
                    d = nd
                    continue
                else:
                    break
            if t != "ICE":
                break
            dx, dy = DIRS[d]
            nx, ny = x + dx, y + dy
            if not self._enterable(nx, ny, d, pa):
                break
            x, y = nx, ny
            nt = self.terrain[y][x]
            if nt != "ICE" and not nt.startswith("MIRROR_"):
                break
        return x, y, d

    def _portal_dest(self, x, y, t):
        grp = t.split("_")[1]
        target = "PORTAL_" + grp[0] + ("B" if grp[1] == "A" else "A")
        for yy in range(GH):
            for xx in range(GW):
                if (xx, yy) != (x, y) and self.terrain[yy][xx] == target:
                    return (xx, yy)
        return None

    def _resolve_momentum(self, x, y, dname, pa):
        pc = 0
        d = dname
        for _ in range(80):
            t = self.terrain[y][x]
            if t.startswith("PORTAL_") and pc < 2:
                dest = self._portal_dest(x, y, t)
                if dest is None:
                    break
                pc += 1
                px, py = dest
                dx0, dy0 = DIRS[d]
                nx, ny = px + dx0, py + dy0
                if self._enterable(nx, ny, d, pa):
                    x, y = nx, ny
                else:
                    x, y = px, py
                continue
            if t.startswith("SPRING_"):
                sd = t.split("_")[1]
                dx0, dy0 = DIRS[sd]
                land = None
                for k in range(1, 4):
                    nx, ny = x + dx0 * k, y + dy0 * k
                    if not self._enterable(nx, ny, sd, pa):
                        break
                    land = (nx, ny)
                if land is None:
                    break
                x, y = land
                d = sd
                continue
            if t == "ICE" or t.startswith("MIRROR_"):
                nx, ny, nd = self._slide(x, y, d, pa)
                if (nx, ny) == (x, y):
                    break
                x, y = nx, ny
                d = nd
                continue
            break
        return x, y

    def _leave_crack(self, x, y):
        if self.terrain[y][x] == "CRACK":
            self.terrain[y][x] = "PIT"

    def _tile_effect_enter(self, x, y):
        t = self.terrain[y][x]
        if t == "PIT":
            self.hero["hp"] -= 100
        elif t == "K1":
            self.hero["keys"][0] = True
        elif t == "K2":
            self.hero["keys"][1] = True
        elif t == "SWITCH":
            self.gf = not self.gf
        elif t == "HEAL":
            self.hero["hp"] = min(100, self.hero["hp"] + 50)
        elif t == "MIMIC":
            self.hero["hp"] -= 50
        if t == "V" and self.hero["keys"][0] and self.hero["keys"][1]:
            self.status = "CLEARED"

    def _box_can_enter(self, x, y, dname, pa):
        if not in_b(x, y):
            return False
        t = self.terrain[y][x]
        if is_high_wall(t, self.gf, pa):
            return False
        if self.blocks_oneway(x, y, dname):
            return False
        if self.occ[y][x] in ("BOX", "TNT"):
            return False
        if any(b["x"] == x and b["y"] == y for b in self.bombs):
            return False
        return True

    def _move_box(self, fx, fy, tx, ty, dname, pa):
        t = self.terrain[ty][tx]
        if t == "PIT":
            self.terrain[ty][tx] = "EMPTY"
            self.occ[fy][fx] = None
            return
        self.occ[fy][fx] = None
        self.occ[ty][tx] = "BOX"
        if self.terrain[ty][tx] == "SWITCH":
            self.gf = not self.gf
        if self.terrain[ty][tx] == "ICE":
            bx, by, _ = self._slide(tx, ty, dname, pa)
            if (bx, by) != (tx, ty):
                self.occ[ty][tx] = None
                if self.terrain[by][bx] == "PIT":
                    self.terrain[by][bx] = "EMPTY"
                else:
                    self.occ[by][bx] = "BOX"
                    if self.terrain[by][bx] == "SWITCH":
                        self.gf = not self.gf

    def _move_hero_into(self, tx, ty, ox, oy, dname, pa):
        self._leave_crack(ox, oy)
        fx, fy = self._resolve_momentum(tx, ty, dname, pa)
        if (fx, fy) != (tx, ty):
            self._leave_crack(tx, ty)
        self.hero["x"], self.hero["y"] = fx, fy
        self._tile_effect_enter(fx, fy)

    def _throw(self, dname):
        h = self.hero
        if h["throws"] <= 0:
            return
        dx, dy = DIRS[dname]
        x, y = h["x"], h["y"]
        for k in range(1, 7):
            nx, ny = x + dx * k, y + dy * k
            if not in_b(nx, ny):
                break
            nt = self.terrain[ny][nx]
            if is_high_wall(nt, self.gf, self.pa()):
                break
            if self.occ[ny][nx] == "BOX":
                break
            if self.occ[ny][nx] == "TNT":
                self._detonate_tnt(nx, ny)
                break
            if nt == "SWITCH":
                self.gf = not self.gf
                break
        h["throws"] -= 1

    def _resolve_bombs(self):
        explode = set()
        for b in self.bombs:
            b["fuse"] -= 1
            if b["fuse"] <= 0:
                explode.add((b["x"], b["y"]))
        changed = True
        while changed:
            changed = False
            for y in range(GH):
                for x in range(GW):
                    if self.occ[y][x] == "TNT":
                        for (ex, ey) in list(explode):
                            if abs(ex - x) <= 1 and abs(ey - y) <= 1:
                                if (x, y) not in explode:
                                    explode.add((x, y))
                                    changed = True
        for (ex, ey) in explode:
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    nx, ny = ex + dx, ey + dy
                    if not in_b(nx, ny):
                        continue
                    if self.hero["x"] == nx and self.hero["y"] == ny:
                        self.hero["hp"] -= 60
                    t = self.terrain[ny][nx]
                    if t in DESTRUCT_TO:
                        self.terrain[ny][nx] = DESTRUCT_TO[t]
                    if self.occ[ny][nx] in ("BOX", "TNT"):
                        self.occ[ny][nx] = None
        self.bombs = [b for b in self.bombs if (b["x"], b["y"]) not in explode]

    def _detonate_tnt(self, x, y):
        explode = {(x, y)}
        changed = True
        while changed:
            changed = False
            for yy in range(GH):
                for xx in range(GW):
                    if self.occ[yy][xx] == "TNT":
                        for (ex, ey) in list(explode):
                            if abs(ex - xx) <= 1 and abs(ey - yy) <= 1 and (xx, yy) not in explode:
                                explode.add((xx, yy))
                                changed = True
        for (ex, ey) in explode:
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    nx, ny = ex + dx, ey + dy
                    if not in_b(nx, ny):
                        continue
                    if self.hero["x"] == nx and self.hero["y"] == ny:
                        self.hero["hp"] -= 60
                    t = self.terrain[ny][nx]
                    if t in DESTRUCT_TO:
                        self.terrain[ny][nx] = DESTRUCT_TO[t]
                    if self.occ[ny][nx] in ("BOX", "TNT"):
                        self.occ[ny][nx] = None

    def _resolve_lasers(self, pos=None):
        h = self.hero
        if pos is None:
            pos = (h["x"], h["y"])
        if self.turn % 3 != 0 and self.turn % 4 != 0:
            return
        hit = 0
        fire_red = (self.turn % 3 == 0)
        fire_blue = (self.turn % 4 == 0)
        pa = self.pa()
        for y in range(GH):
            for x in range(GW):
                t = self.terrain[y][x]
                if t.startswith("LASER2_") and fire_blue:
                    d = t.split("_")[1]
                elif t.startswith("LASER_") and fire_red:
                    d = t.split("_")[1]
                else:
                    continue
                dx, dy = DIRS[d]
                for k in range(1, 11):
                    nx, ny = x + dx * k, y + dy * k
                    if not in_b(nx, ny):
                        break
                    nt = self.terrain[ny][nx]
                    if is_high_wall(nt, self.gf, pa) or self.occ[ny][nx] == "BOX":
                        break
                    if nx == pos[0] and ny == pos[1]:
                        hit += 1
                        break
                    if self.occ[ny][nx] == "TNT":
                        self._detonate_tnt(nx, ny)
                        break
        h["hp"] -= 50 * hit

    def step(self, action):
        if self.status != "PLAYING":
            return
        h = self.hero
        pa = self.pa()
        start_pos = (h["x"], h["y"])
        ox, oy = h["x"], h["y"]
        moved = False
        if action.startswith("MOVE_") or action.startswith("JUMP_"):
            kind, dname = action.split("_")
            dx, dy = DIRS[dname]
            if kind == "MOVE":
                tx, ty = ox + dx, oy + dy
                if in_b(tx, ty) and not is_high_wall(self.terrain[ty][tx], self.gf, pa) \
                        and not self.blocks_oneway(tx, ty, dname):
                    if self.occ[ty][tx] == "BOX":
                        bx, by = tx + dx, ty + dy
                        if self._box_can_enter(bx, by, dname, pa):
                            self._move_box(tx, ty, bx, by, dname, pa)
                            self._move_hero_into(tx, ty, ox, oy, dname, pa)
                            moved = True
                    elif self.occ[ty][tx] is None and not any(b["x"] == tx and b["y"] == ty for b in self.bombs):
                        self._move_hero_into(tx, ty, ox, oy, dname, pa)
                        moved = True
            else:
                if h["jumps"] > 0:
                    m1x, m1y = ox + dx, oy + dy
                    lx, ly = ox + 2 * dx, oy + 2 * dy
                    if in_b(m1x, m1y) and in_b(lx, ly):
                        mid_ok = (not is_high_wall(self.terrain[m1y][m1x], self.gf, pa)
                                  and not self.blocks_oneway(m1x, m1y, dname))
                        land_ok = (not is_high_wall(self.terrain[ly][lx], self.gf, pa)
                                   and not self.blocks_oneway(lx, ly, dname)
                                   and self.occ[ly][lx] is None
                                   and not any(b["x"] == lx and b["y"] == ly for b in self.bombs))
                        if mid_ok and land_ok:
                            h["jumps"] -= 1
                            self._leave_crack(ox, oy)
                            fx, fy = self._resolve_momentum(lx, ly, dname, pa)
                            if (fx, fy) != (lx, ly):
                                self._leave_crack(lx, ly)
                            h["x"], h["y"] = fx, fy
                            self._tile_effect_enter(fx, fy)
                            moved = True
        elif action == "BOMB":
            if h["bombs"] > 0 and not any(b["x"] == ox and b["y"] == oy for b in self.bombs):
                self.bombs.append({"x": ox, "y": oy, "fuse": 3})
                h["bombs"] -= 1
        elif action.startswith("THROW_"):
            dname = action.split("_")[1]
            self._throw(dname)
        if self.status == "CLEARED":
            self.turn += 1
            return
        self._resolve_bombs()
        self._resolve_lasers(start_pos)
        if self.hero["hp"] <= 0:
            self.status = "DEAD"
        if self.status == "PLAYING" and self.hero["keys"][0] and self.hero["keys"][1] \
                and (h["x"], h["y"]) == tuple(self.v):
            self.status = "CLEARED"
        self.turn += 1

    def cleared(self):
        return self.status == "CLEARED"

    def dead(self):
        return self.status == "DEAD"

    def boxes_sig(self):
        b = []
        for y in range(GH):
            for x in range(GW):
                if self.occ[y][x] == "BOX":
                    b.append((x, y))
        return tuple(b)

    def sig(self):
        h = self.hero
        return (h["x"], h["y"], h["keys"][0], h["keys"][1], self.gf,
                self.turn % 12, h["hp"], h["jumps"], self.boxes_sig())


def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def heuristic(w):
    hx, hy = w.hero["x"], w.hero["y"]
    pts = []
    if not w.hero["keys"][0] and w.k1:
        pts.append((w.k1[0], w.k1[1]))
    if not w.hero["keys"][1] and w.k2:
        pts.append((w.k2[0], w.k2[1]))
    pts.append((w.v[0], w.v[1]))
    cx, cy = hx, hy
    total = 0
    rem = list(pts)
    while rem:
        best = min(rem, key=lambda p: abs(p[0] - cx) + abs(p[1] - cy))
        total += abs(best[0] - cx) + abs(best[1] - cy)
        cx, cy = best
        rem.remove(best)
    return total


def _action_list(w):
    acts = []
    for d in ("U", "D", "L", "R"):
        acts.append("MOVE_" + d)
    if w.hero["jumps"] > 0:
        for d in ("U", "D", "L", "R"):
            acts.append("JUMP_" + d)
    if w.hero["bombs"] > 0:
        acts.append("BOMB")
    if w.hero["throws"] > 0:
        for d in ("U", "D", "L", "R"):
            acts.append("THROW_" + d)
    acts.append("WAIT")
    return acts


def search(w, time_limit):
    """A* search for a clearing plan. Returns (plan_list, found)."""
    start = time.monotonic()
    if w.cleared():
        return [], True
    h0 = heuristic(w)
    best_path = []
    best_h = h0
    best_pain = 10 ** 9
    counter = 0
    heap = [(h0, 0, 0, counter, w, [])]
    visited = {}
    while heap:
        if time.monotonic() - start > time_limit:
            break
        f, pain, g, _, cur, path = heapq.heappop(heap)
        if cur.cleared():
            return path, True
        sig = cur.sig()
        if sig in visited and visited[sig] <= f:
            continue
        visited[sig] = f
        h = heuristic(cur)
        if h < best_h or (h == best_h and pain < best_pain):
            best_h = h
            best_path = path
            best_pain = pain
        for a in _action_list(cur):
            nw = cur.clone()
            hp0 = nw.hero["hp"]
            nw.step(a)
            if nw.dead():
                continue
            if nw.turn > 240:
                continue
            if nw.cleared():
                return path + [a], True
            dmg = max(0, hp0 - nw.hero["hp"])
            newpain = pain + dmg
            newg = g + 1
            nh = heuristic(nw)
            nf = newg + newpain * 40 + nh
            counter += 1
            heapq.heappush(heap, (nf, newpain, newg, counter, nw, path + [a]))
    return best_path, (best_h == 0)


def decide_action(state, memory):
    w = World.from_state(state)
    turn = state.get("turn", 1)
    plan = memory.get("plan")
    pidx = memory.get("pidx", 0)
    if plan and 0 <= pidx < len(plan):
        a = plan[pidx]
        nw = w.clone()
        nw.step(a)
        if not nw.dead() and nw.turn <= 240:
            memory["pidx"] = pidx + 1
            return a
    time_limit = 1.6 if turn == 1 else 0.35
    plan, found = search(w, time_limit)
    if plan:
        a = plan[0]
        memory["plan"] = plan
        memory["pidx"] = 1
        return a
    for a in ("MOVE_R", "MOVE_D", "MOVE_L", "MOVE_U", "MOVE_U", "WAIT"):
        nw = w.clone()
        nw.step(a)
        if not nw.dead():
            return a
    return "WAIT"
