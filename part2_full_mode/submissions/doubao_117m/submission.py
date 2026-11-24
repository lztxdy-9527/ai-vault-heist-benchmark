import heapq
import time
import collections

GRID_WIDTH = 40
GRID_HEIGHT = 26
GW = 40
GH = 26
MAX_BUDGET = 3000
MAX_TURNS = 240
MAX_AUTHOR_STEPS = 200
SPAWN_POS = (2, 13)

VALID_ACTIONS = (
    "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT",
    "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
    "THROW_U", "THROW_D", "THROW_L", "THROW_R", "BOMB",
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
    "R_GATE": "EMPTY", "B_GATE": "EMPTY", "SWITCH": "EMPTY",
    "HEAL": "EMPTY", "MIMIC": "EMPTY",
    "SPRING_U": "EMPTY", "SPRING_D": "EMPTY", "SPRING_L": "EMPTY", "SPRING_R": "EMPTY",
    "MIRROR_NE": "EMPTY", "MIRROR_SE": "EMPTY", "MIRROR_SW": "EMPTY", "MIRROR_NW": "EMPTY",
}

TILE_COSTS = {
    "EMPTY": 0, "K1": 0, "K2": 0, "V": 0, "W": 5, "T_W": 25, "ICE": 10,
    "MIRROR_NE": 25, "MIRROR_SE": 25, "MIRROR_SW": 25, "MIRROR_NW": 25,
    "SPRING_U": 35, "SPRING_D": 35, "SPRING_L": 35, "SPRING_R": 35, "PIT": 40,
    "LASER_U": 75, "LASER_D": 75, "LASER_L": 75, "LASER_R": 75,
    "LASER2_U": 90, "LASER2_D": 90, "LASER2_L": 90, "LASER2_R": 90,
    "CRACK": 20, "SWITCH": 30, "R_GATE": 20, "B_GATE": 20,
    "PLATE": 45, "P_GATE": 30,
    "ONEWAY_U": 30, "ONEWAY_D": 30, "ONEWAY_L": 30, "ONEWAY_R": 30,
    "TNT": 40, "BOX": 30, "HEAL": 30, "MIMIC": 60,
    "PORTAL_1A": 40, "PORTAL_1B": 40, "PORTAL_2A": 40, "PORTAL_2B": 40,
}

PERM_WALL = ("W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R",
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
    if tile in PERM_WALL[2:]:
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
        self._init_static()
        self._beams_cache = {}
        self._scan_features()

    def _init_static(self):
        self.static_terrain = True
        for y in range(GH):
            for x in range(GW):
                t = self.terrain[y][x]
                if t == "CRACK" or t == "PIT":
                    self.static_terrain = False
                    return

    def _scan_features(self):
        self._plates = []
        self._emitters = []
        self._tnt_present = False
        self._has_R_gate = False
        self._has_B_gate = False
        for y in range(GH):
            for x in range(GW):
                t = self.terrain[y][x]
                if t == "PLATE":
                    self._plates.append((x, y))
                elif t.startswith("LASER2_"):
                    self._emitters.append((x, y, "B", t.split("_")[1]))
                elif t.startswith("LASER_"):
                    self._emitters.append((x, y, "R", t.split("_")[1]))
                elif t == "TNT":
                    self._tnt_present = True
                elif t == "R_GATE":
                    self._has_R_gate = True
                elif t == "B_GATE":
                    self._has_B_gate = True
        self._boxes = set()
        for y in range(GH):
            for x in range(GW):
                if self.occ[y][x] == "BOX":
                    self._boxes.add((x, y))

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
        w._init_static()
        w._beams_cache = {}
        w._scan_features()
        return w

    def clone(self):
        w = World()
        if self.static_terrain:
            w.terrain = self.terrain
        else:
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
        w.static_terrain = self.static_terrain
        w._beams_cache = {}
        w._plates = self._plates
        w._emitters = self._emitters
        w._tnt_present = self._tnt_present
        w._has_R_gate = self._has_R_gate
        w._has_B_gate = self._has_B_gate
        w._boxes = set(self._boxes)
        return w

    def _find(self, t):
        for y in range(GH):
            for x in range(GW):
                if self.terrain[y][x] == t:
                    return [x, y]
        return None

    def pa(self):
        if not self._plates:
            return False
        for p in self._plates:
            if p not in self._boxes:
                return False
        return True

    def boxes_tuple(self):
        return tuple(sorted(self._boxes))

    def blocks_oneway(self, x, y, dname):
        t = self.terrain[y][x]
        if not t.startswith("ONEWAY_"):
            return False
        return t.split("_")[1] != dname

    def laser_beams(self, turn):
        fire_red = (turn % 3 == 0)
        fire_blue = (turn % 4 == 0)
        if not (fire_red or fire_blue):
            return set()
        if self.static_terrain:
            key = (turn % 12, self.gf, self.boxes_tuple(), self.pa())
            cached = self._beams_cache.get(key)
            if cached is not None:
                return cached
        cells = set()
        pa = self.pa()
        for (x, y, color, d) in self._emitters:
            if color == "R" and not fire_red:
                continue
            if color == "B" and not fire_blue:
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
        if self.static_terrain:
            self._beams_cache[key] = cells
        return cells

    def hero_in_beam(self, turn, pos):
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
        self._boxes.discard((fx, fy))
        t = self.terrain[ty][tx]
        if t == "PIT":
            self.terrain[ty][tx] = "EMPTY"
            self.occ[fy][fx] = None
            return
        self.occ[fy][fx] = None
        self.occ[ty][tx] = "BOX"
        self._boxes.add((tx, ty))
        if self.terrain[ty][tx] == "SWITCH":
            self.gf = not self.gf
        if self.terrain[ty][tx] == "ICE":
            bx, by, _ = self._slide(tx, ty, dname, pa)
            if (bx, by) != (tx, ty):
                self.occ[ty][tx] = None
                self._boxes.discard((tx, ty))
                if self.terrain[by][bx] == "PIT":
                    self.terrain[by][bx] = "EMPTY"
                else:
                    self.occ[by][bx] = "BOX"
                    self._boxes.add((bx, by))
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
                        self._boxes.discard((nx, ny))
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
                        self._boxes.discard((nx, ny))
                        self.occ[ny][nx] = None

    def _resolve_lasers(self, pos=None):
        h = self.hero
        if pos is None:
            pos = (h["x"], h["y"])
        if self.turn % 3 != 0 and self.turn % 4 != 0:
            return
        fire_red = (self.turn % 3 == 0)
        fire_blue = (self.turn % 4 == 0)
        pa = self.pa()
        hit = 0
        for (x, y, color, d) in self._emitters:
            if color == "R" and not fire_red:
                continue
            if color == "B" and not fire_blue:
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
                    elif self.occ[ty][tx] is None and not any(b["x"] == tx and b["y"] == ty for b in self.bombs):
                        self._move_hero_into(tx, ty, ox, oy, dname, pa)
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

    def sig(self):
        h = self.hero
        return (h["x"], h["y"], h["keys"][0], h["keys"][1], self.gf,
                self.turn % 12, h["jumps"], self.boxes_tuple())


# ---------------- static BFS distance fields (lower bound) ----------------

def _static_passable(terrain):
    """Return 2D bool: tile is passable ignoring gates/boxes/oneway/laser-timing (lower bound)."""
    P = [[False] * GW for _ in range(GH)]
    for y in range(GH):
        for x in range(GW):
            t = terrain[y][x]
            if t in PERM_WALL:
                continue
            if t == "PIT":
                continue
            P[y][x] = True
    return P


def _bfs_field(P, sx, sy):
    INF = 10 ** 9
    dist = [[INF] * GW for _ in range(GH)]
    if not (0 <= sx < GW and 0 <= sy < GH) or not P[sy][sx]:
        return dist
    dist[sy][sx] = 0
    q = collections.deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        d = dist[y][x]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < GW and 0 <= ny < GH and P[ny][nx] and dist[ny][nx] > d + 1:
                dist[ny][nx] = d + 1
                q.append((nx, ny))
    return dist


def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Solver:
    def __init__(self, world):
        self.world0 = world
        t = world.terrain
        self.P = _static_passable(t)
        # collect waypoints
        self.wp = {}  # name -> (x,y)
        if world.k1:
            self.wp["K1"] = tuple(world.k1)
        if world.k2:
            self.wp["K2"] = tuple(world.k2)
        if world.v:
            self.wp["V"] = tuple(world.v)
        for y in range(GH):
            for x in range(GW):
                tt = t[y][x]
                if tt == "SWITCH":
                    self.wp.setdefault("SWITCH", (x, y))
                if tt == "PLATE":
                    self.wp.setdefault("PLATE_%d_%d" % (x, y), (x, y))
        self.boxes0 = []
        for y in range(GH):
            for x in range(GW):
                if world.occ[y][x] == "BOX":
                    self.boxes0.append((x, y))
        self.plates = [p for n, p in self.wp.items() if n.startswith("PLATE_")]
        self._has_R = world._has_R_gate
        self._has_B = world._has_B_gate
        self._has_tnt = world._tnt_present
        # precompute BFS field for each waypoint + each initial box
        self.fields = {}
        for n, p in self.wp.items():
            self.fields[n] = _bfs_field(self.P, p[0], p[1])
        for i, b in enumerate(self.boxes0):
            self.fields["BOX0_%d" % i] = _bfs_field(self.P, b[0], b[1])
        # pairwise waypoint distances
        self.names = list(self.wp.keys())
        self.wpd = {}
        for a in self.names:
            for b in self.names:
                pa = self.wp[a]
                self.wpd[(a, b)] = self.fields[b][pa[1]][pa[0]]

    def _dist(self, fieldname, x, y):
        f = self.fields.get(fieldname)
        if f is None:
            return _manhattan((x, y), self.wp.get(fieldname, (x, y)))
        d = f[y][x]
        if d >= 10 ** 8:
            return _manhattan((x, y), self.wp.get(fieldname, (x, y)))
        return d

    def _plate_penalty(self, w, hx, hy):
        inactive = [p for p in self.plates if w.occ[p[1]][p[0]] != "BOX"]
        if not inactive:
            return 0
        boxes = [(x, y) for y in range(GH) for x in range(GW) if w.occ[y][x] == "BOX"]
        avail = list(boxes)
        used = set()
        total = 0
        for p in inactive:
            best = None
            bestd = 10 ** 9
            for i, b in enumerate(avail):
                if i in used:
                    continue
                d = _manhattan(b, p)
                if d < bestd:
                    bestd = d
                    best = i
            if best is not None:
                used.add(best)
                total += bestd
        approach = min((_manhattan((hx, hy), b) for b in avail), default=0)
        return total + approach

    def heuristic(self, w):
        # hero mandatory visits: missing keys + V
        hx, hy = w.hero["x"], w.hero["y"]
        tour = []
        if not w.hero["keys"][0] and "K1" in self.wp:
            tour.append("K1")
        if not w.hero["keys"][1] and "K2" in self.wp:
            tour.append("K2")
        switch_needed = False
        if "SWITCH" in self.wp:
            if (self._has_R and not w.gf) or (self._has_B and w.gf):
                switch_needed = True
        if switch_needed:
            tour.append("SWITCH")
        plate_penalty = self._plate_penalty(w, hx, hy)
        tour.append("V")
        # greedy nearest-neighbour tour from hero using static fields
        cx, cy = hx, hy
        total = 0
        rem = list(tour)
        while rem:
            best = min(rem, key=lambda n: self._dist(n, cx, cy))
            total += self._dist(best, cx, cy)
            cx, cy = self.wp[best]
            rem.remove(best)
        return total + plate_penalty
    def _dist_from_pt(self, name, x, y):
        return self._dist(name, x, y)

    def _reachable(self, w):
        hx, hy = w.hero["x"], w.hero["y"]
        pa = w.pa()
        gf = w.gf
        t = self.world0.terrain
        occ = w.occ
        seen = [[False] * GW for _ in range(GH)]
        q = collections.deque()

        def walk(x, y):
            if not (0 <= x < GW and 0 <= y < GH):
                return False
            tt = t[y][x]
            if tt in PERM_WALL or tt == "PIT":
                return False
            if tt == "R_GATE" and not gf:
                return False
            if tt == "B_GATE" and gf:
                return False
            if tt == "P_GATE" and not pa:
                return False
            if occ[y][x] == "BOX":
                return False
            return True

        if walk(hx, hy):
            seen[hy][hx] = True
            q.append((hx, hy))
        while q:
            x, y = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if walk(nx, ny) and not seen[ny][nx]:
                    seen[ny][nx] = True
                    q.append((nx, ny))
        res = set()
        for n in ("K1", "K2", "V", "SWITCH"):
            if n in self.wp:
                px, py = self.wp[n]
                if seen[py][px]:
                    res.add(n)
        return res


def _actions(w):
    acts = []
    for d in ("U", "D", "L", "R"):
        acts.append("MOVE_" + d)
    if w.hero["jumps"] > 0:
        for d in ("U", "D", "L", "R"):
            acts.append("JUMP_" + d)
    if w._tnt_present and w.hero["throws"] > 0:
        for d in ("U", "D", "L", "R"):
            acts.append("THROW_" + d)
    if w.hero["bombs"] > 0:
        hx, hy = w.hero["x"], w.hero["y"]
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = hx + dx, hy + dy
            if in_b(nx, ny) and w.terrain[ny][nx] in ("W", "ICE", "CRACK", "R_GATE", "B_GATE"):
                acts.append("BOMB")
                break
    acts.append("WAIT")
    return acts



class SearchSession:
    NODE_CAP = 600000

    def __init__(self, world, solver=None, weight=2.5, max_depth=200, shared_visited=None):
        self.solver = solver if solver is not None else Solver(world)
        self.weight = weight
        self.max_depth = max_depth
        self.root = world.clone()
        self.root_key = _state_key(world)
        self.counter = 0
        self.came_from = {0: None}
        self.visited = shared_visited if shared_visited is not None else {}
        h0 = self.solver.heuristic(world)
        self.heap = [(h0 * weight, 0, 0, 0, world)]
        self.best_node = 0
        self.best_h = h0
        self.best_pain = 10 ** 9
        self.clearing_plan = None
        self.overflow = False

    def _reconstruct(self, nid):
        acts = []
        while self.came_from[nid] is not None:
            pid, a = self.came_from[nid]
            acts.append(a)
            nid = pid
        acts.reverse()
        return acts

    def run(self, time_limit):
        if self.overflow or self.clearing_plan is not None:
            return
        start = time.monotonic()
        heap = self.heap
        visited = self.visited
        solver = self.solver
        weight = self.weight
        md = self.max_depth
        cf = self.came_from
        while heap:
            if time.monotonic() - start > time_limit:
                return
            if self.counter > self.NODE_CAP:
                self.overflow = True
                return
            f, pain, g, cur_id, cur = heapq.heappop(heap)
            if cur.cleared():
                self.clearing_plan = self._reconstruct(cur_id)
                self.best_node = cur_id
                self.best_h = 0
                return
            sig = cur.sig()
            prev = visited.get(sig)
            if prev is not None and prev[0] <= g and prev[1] <= pain:
                continue
            visited[sig] = (g, pain)
            h = solver.heuristic(cur)
            if h < self.best_h or (h == self.best_h and pain < self.best_pain):
                self.best_h = h
                self.best_node = cur_id
                self.best_pain = pain
            if g >= md:
                continue
            for a in _actions(cur):
                nw = cur.clone()
                hp0 = nw.hero["hp"]
                nw.step(a)
                if nw.dead() or nw.turn > 240:
                    continue
                if nw.cleared():
                    self.counter += 1
                    cf[self.counter] = (cur_id, a)
                    self.clearing_plan = self._reconstruct(self.counter)
                    self.best_node = self.counter
                    self.best_h = 0
                    return
                dmg = max(0, hp0 - nw.hero["hp"])
                newpain = pain + dmg
                newg = g + 1
                nh = solver.heuristic(nw)
                nf = newg + newpain * 30 + nh * weight
                self.counter += 1
                cf[self.counter] = (cur_id, a)
                heapq.heappush(heap, (nf, newpain, newg, self.counter, nw))

    def current_plan(self):
        if self.clearing_plan is not None:
            return self.clearing_plan
        return self._reconstruct(self.best_node)


def _state_key(w):
    h = w.hero
    return (h["x"], h["y"], h["keys"][0], h["keys"][1], w.gf,
            h["hp"], h["jumps"], w.boxes_tuple(), w.turn)


def search(world, time_limit, weight=2.5, max_depth=200):
    if world.cleared():
        return [], True
    sess = SearchSession(world, None, weight, max_depth)
    sess.run(time_limit)
    found = sess.clearing_plan is not None
    plan = sess.clearing_plan if found else sess.current_plan()
    return plan, found


def _safe_fallback(w):
    if w.cleared():
        return "WAIT"
    sol = Solver(w)
    best_a = "WAIT"
    best_score = 10 ** 9
    for a in ("MOVE_R", "MOVE_D", "MOVE_L", "MOVE_U", "WAIT"):
        nw = w.clone()
        nw.step(a)
        if nw.dead() or nw.turn > 240:
            continue
        sc = sol.heuristic(nw) + nw.hero["x"] * 0 + (0 if nw.hero["hp"] >= w.hero["hp"] else 50)
        if sc < best_score:
            best_score = sc
            best_a = a
    return best_a


def decide_action(state, memory):
    w = World.from_state(state)
    turn = state.get("turn", 1)
    start_t = time.monotonic()
    hard = 1.7 if turn == 1 else 0.35
    cur_key = _state_key(w)
    solver = memory.get("solver")
    if solver is None:
        solver = Solver(w)
        memory["solver"] = solver
    sess = memory.get("session")
    plan = memory.get("plan")
    pidx = memory.get("pidx", 0)
    trace = memory.get("trace")
    aligned = (sess is not None and plan is not None and trace is not None
               and 0 <= pidx < len(trace) and trace[pidx] == cur_key)
    if not aligned:
        sess = SearchSession(w, solver, 2.5, 200)
        memory["session"] = sess
        plan = None
        pidx = 0
        trace = [cur_key]
        memory["stagnant"] = 0
        memory["last_h"] = None
    stagnant = memory.get("stagnant", 0)
    steps_left = (len(plan) - pidx) if plan else 0
    need_search = (not aligned) or turn == 1 or (steps_left <= 3 and stagnant < 5)
    if need_search:
        prev_h = memory.get("last_h")
        remaining = hard - (time.monotonic() - start_t) - 0.02
        if remaining > 0.03:
            sess.run(remaining)
        if sess.clearing_plan is not None:
            memory["stagnant"] = 0
        elif prev_h is not None and sess.best_h >= prev_h:
            memory["stagnant"] = stagnant + 1
        else:
            memory["stagnant"] = 0
        memory["last_h"] = sess.best_h
    cp = sess.current_plan()
    if plan is None or pidx == 0 or (len(cp) >= pidx and cp[:pidx] == plan[:pidx]):
        plan = cp
        steps_left = len(plan) - pidx
    if plan and pidx < len(plan):
        a = plan[pidx]
        nw = w.clone()
        nw.step(a)
        if not nw.dead() and nw.turn <= 240:
            trace.append(_state_key(nw))
            memory["trace"] = trace
            memory["plan"] = plan
            memory["pidx"] = pidx + 1
            return a
    memory["plan"] = None
    return _safe_fallback(w)


def _grid_cost(grid):
    c = 0
    for row in grid:
        for t in row:
            c += TILE_COSTS.get(t, 0)
    return c


def build_dungeon():
    grid = [["EMPTY"] * GW for _ in range(GH)]
    for x in range(GW):
        grid[0][x] = "W"
        grid[GH - 1][x] = "W"
    for y in range(GH):
        grid[y][0] = "W"
        grid[y][GW - 1] = "W"
    for y in range(1, GH - 1):
        grid[y][19] = "W"
    grid[13][19] = "P_GATE"
    grid[13][6] = "PLATE"
    grid[13][10] = "BOX"
    grid[18][14] = "K1"
    grid[8][25] = "K2"
    grid[8][37] = "V"
    grid[1][30] = "LASER2_D"
    grid[8][28] = "ONEWAY_R"
    for y in range(1, 7):
        grid[y][24] = "W"
    grid[8][22] = "W"
    for y in range(9, GH - 1):
        grid[y][22] = "W"
    w0 = World(grid)
    plan, found = search(w0, 1.9)
    if not found or len(plan) > 200 or len(plan) == 0:
        grid2 = [["EMPTY"] * GW for _ in range(GH)]
        for x in range(GW):
            grid2[0][x] = "W"
            grid2[GH - 1][x] = "W"
        for y in range(GH):
            grid2[y][0] = "W"
            grid2[y][GW - 1] = "W"
        grid2[13][15] = "K1"
        grid2[13][20] = "K2"
        grid2[13][36] = "V"
        w0 = World(grid2)
        plan, found = search(w0, 1.9)
        grid = grid2
    if not found or len(plan) > 200 or len(plan) == 0:
        plan = ["MOVE_R"] * 34
        grid = [["EMPTY"] * GW for _ in range(GH)]
        for x in range(GW):
            grid[0][x] = "W"
            grid[GH - 1][x] = "W"
        for y in range(GH):
            grid[y][0] = "W"
            grid[y][GW - 1] = "W"
        grid[13][15] = "K1"
        grid[13][20] = "K2"
        grid[13][36] = "V"
    return {"grid": grid, "author_solution": plan}
