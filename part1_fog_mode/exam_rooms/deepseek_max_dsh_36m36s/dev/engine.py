"""Local re-implementation of the RULES.md v2.1 judge engine (validation only).

This file is NOT part of the submission. It exists so we can:
  * replay golden vectors,
  * validate dungeon legality (budget / landmarks / quotas / mimic clues),
  * replay an author_solution on a dungeon,
  * generate BLIND-mode observations and test our hero policy.
"""
from collections import deque

W, H = 40, 26
SPAWN = (2, 13)
MAX_TURNS = 240
BUDGET = 3000

DIRS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
ACTION_DIR = {
    "MOVE_U": "U", "MOVE_D": "D", "MOVE_L": "L", "MOVE_R": "R",
    "JUMP_U": "U", "JUMP_D": "D", "JUMP_L": "L", "JUMP_R": "R",
    "THROW_U": "U", "THROW_D": "D", "THROW_L": "L", "THROW_R": "R",
}

HIGH_WALL_BASE = {"W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R"}
LASERS = {"LASER_U", "LASER_D", "LASER_L", "LASER_R"}
MIRRORS = {"MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW"}
SPRINGS = {"SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R"}
PORTALS = {"PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B"}
GATES = {"R_GATE", "B_GATE"}

MIRROR_MAP = {
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

COSTS = {
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
LEGAL_TILES = set(COSTS)

EXPLOSION_IMMUNE = {"T_W", "K1", "K2", "V", "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B", "PIT"}


def in_bounds(x, y):
    return 0 <= x < W and 0 <= y < H


def in_spawn_zone(x, y):
    return 1 <= x <= 3 and 12 <= y <= 14


# ---------------------------------------------------------------------------
# legality validation
# ---------------------------------------------------------------------------

def validate_grid(grid):
    """Return (ok, errors, info). info holds spent gold etc."""
    errors = []
    if not isinstance(grid, list) or len(grid) != H:
        return False, ["grid must be 26 rows"], {}
    for y, row in enumerate(grid):
        if not isinstance(row, list) or len(row) != W:
            errors.append("row %d must have 40 columns" % y)
            continue
        for x, cell in enumerate(row):
            if not isinstance(cell, str) or cell not in LEGAL_TILES:
                errors.append("illegal tile %r at (%d,%d)" % (cell, x, y))
    if errors:
        return False, errors[:20], {}

    # outer frame
    for y in range(H):
        for x in range(W):
            if x in (0, W - 1) or y in (0, H - 1):
                if grid[y][x] != "T_W":
                    errors.append("frame cell (%d,%d) must be T_W" % (x, y))
    # spawn clearance
    for y in range(12, 15):
        for x in range(1, 4):
            if grid[y][x] != "EMPTY":
                errors.append("spawn zone cell (%d,%d) must be EMPTY, got %s" % (x, y, grid[y][x]))

    counts = {}
    for y in range(H):
        for x in range(W):
            counts[grid[y][x]] = counts.get(grid[y][x], 0) + 1

    # landmarks
    k1 = [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "K1"]
    k2 = [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "K2"]
    vv = [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "V"]
    if len(k1) != 1:
        errors.append("need exactly one K1, got %d" % len(k1))
    if len(k2) != 1:
        errors.append("need exactly one K2, got %d" % len(k2))
    if len(vv) != 1:
        errors.append("need exactly one V, got %d" % len(vv))
    if len(k1) == 1:
        x, y = k1[0]
        if not (12 <= x <= 34 and 2 <= y <= 10):
            errors.append("K1 out of region at (%d,%d)" % (x, y))
    if len(k2) == 1:
        x, y = k2[0]
        if not (12 <= x <= 34 and 15 <= y <= 23):
            errors.append("K2 out of region at (%d,%d)" % (x, y))
    if len(vv) == 1:
        x, y = vv[0]
        if not (33 <= x <= 37 and 4 <= y <= 21):
            errors.append("V out of region at (%d,%d)" % (x, y))
    if len(k1) == 1 and len(k2) == 1:
        d = abs(k1[0][0] - k2[0][0]) + abs(k1[0][1] - k2[0][1])
        if d < 12:
            errors.append("K1/K2 manhattan distance %d < 12" % d)

    # budget
    spent = 0
    for y in range(H):
        for x in range(W):
            if x in (0, W - 1) or y in (0, H - 1):
                continue
            spent += COSTS[grid[y][x]]
    # portal pairs are charged 80 per pair: 40+40 already sums to 80
    if spent > BUDGET:
        errors.append("budget exceeded: %d > %d" % (spent, BUDGET))

    inner = lambda t: sum(1 for y in range(1, H - 1) for x in range(1, W - 1) if grid[y][x] == t)
    if inner("T_W") > 120:
        errors.append("inner T_W count %d > 120" % inner("T_W"))
    if inner("MIRROR_NE") + inner("MIRROR_SE") + inner("MIRROR_SW") + inner("MIRROR_NW") > 30:
        errors.append("mirror count > 30")
    if inner("SPRING_U") + inner("SPRING_D") + inner("SPRING_L") + inner("SPRING_R") > 20:
        errors.append("spring count > 20")
    if inner("LASER_U") + inner("LASER_D") + inner("LASER_L") + inner("LASER_R") > 12:
        errors.append("laser count > 12")
    if inner("CRACK") > 40:
        errors.append("crack count > 40")
    if inner("SWITCH") > 6:
        errors.append("switch count > 6")
    if inner("R_GATE") + inner("B_GATE") > 16:
        errors.append("gate count > 16")
    if inner("TNT") > 12:
        errors.append("tnt count > 12")
    if inner("BOX") > 4:
        errors.append("box count > 4")
    if inner("HEAL") > 4:
        errors.append("heal count > 4")
    if inner("MIMIC") > 4:
        errors.append("mimic count > 4")
    for pair in (("PORTAL_1A", "PORTAL_1B"), ("PORTAL_2A", "PORTAL_2B")):
        a, b = inner(pair[0]), inner(pair[1])
        if a != b:
            errors.append("portal pair %s mismatch (%d vs %d)" % (pair[0], a, b))
        if a > 1:
            errors.append("too many %s" % pair[0])

    info = {
        "spent": spent,
        "counts": counts,
        "inner_tw": inner("T_W"),
        "k1": k1[0] if len(k1) == 1 else None,
        "k2": k2[0] if len(k2) == 1 else None,
        "v": vv[0] if len(vv) == 1 else None,
    }
    return (len(errors) == 0), errors, info


# ---------------------------------------------------------------------------
# engine
# ---------------------------------------------------------------------------

class Engine:
    def __init__(self, grid=None, direct=None):
        self.terrain = [["EMPTY"] * W for _ in range(H)]
        self.occ = [[None] * W for _ in range(H)]
        self.clues = [[False] * W for _ in range(H)]
        self.mimic_clue = {}
        self.bombs = []
        self.next_id = 1
        self.gates_flipped = False
        self.turn = 1
        self.exposed = set()
        self.trap_damage = 0.0
        self.status = "ALIVE"
        self.tnt_armed = set()
        self.hero = {"x": 2, "y": 13, "hp": 100, "keys": [False, False],
                     "jumps": 3, "throws": 3, "bombs": 2}
        self.trace = []
        self.stage = {"k": 0, "d0": None, "dmin": None}
        self._grid = None
        if grid is not None:
            self._load_grid(grid)
        if direct is not None:
            self._load_direct(direct)

    # -- construction ------------------------------------------------------
    def _load_grid(self, grid):
        self._grid = [list(r) for r in grid]
        for y in range(H):
            for x in range(W):
                g = grid[y][x]
                if g in ("BOX", "TNT"):
                    self.terrain[y][x] = "EMPTY"
                    self.occ[y][x] = g
                else:
                    self.terrain[y][x] = g
        # mimic clue binding
        for y in range(H):
            for x in range(W):
                if self.terrain[y][x] != "MIMIC":
                    continue
                found = None
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = x + dx, y + dy
                    if not in_bounds(nx, ny):
                        continue
                    if self.terrain[ny][nx] != "EMPTY" or self.occ[ny][nx] is not None:
                        continue
                    if in_spawn_zone(nx, ny):
                        continue
                    if self.clues[ny][nx]:
                        continue
                    bad = False
                    for ddx, ddy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                        mx, my = nx + ddx, ny + ddy
                        if (mx, my) == (x, y):
                            continue
                        if in_bounds(mx, my) and self.terrain[my][mx] in ("HEAL", "MIMIC"):
                            bad = True
                            break
                    if bad:
                        continue
                    found = (nx, ny)
                    break
                if found is None:
                    raise ValueError("MIMIC at (%d,%d) has no legal clue slot" % (x, y))
                self.clues[found[1]][found[0]] = True
                self.mimic_clue[(x, y)] = found
        self._init_stage()

    def _load_direct(self, direct):
        for key, tile in direct.get("local_tiles", {}).items():
            xs, ys = key.strip("()").split(",")
            x, y = int(xs), int(ys)
            self.terrain[y][x] = tile["terrain"]
            self.occ[y][x] = tile.get("occupant")
        h = direct.get("hero", {})
        for k in ("x", "y", "hp", "jumps", "throws", "bombs"):
            if k in h:
                self.hero[k] = h[k]
        if "keys" in h:
            self.hero["keys"] = list(h["keys"])
        self.turn = direct.get("turn", 1)
        self.gates_flipped = direct.get("gates_flipped", False)
        # mimic clue binding for direct tiles
        for y in range(H):
            for x in range(W):
                if self.terrain[y][x] != "MIMIC":
                    continue
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = x + dx, y + dy
                    if not in_bounds(nx, ny):
                        continue
                    if self.terrain[ny][nx] == "EMPTY" and self.occ[ny][nx] is None and not self.clues[ny][nx]:
                        self.clues[ny][nx] = True
                        self.mimic_clue[(x, y)] = (nx, ny)
                        break
        self._init_stage()

    def _init_stage(self):
        self.stage = {"k": 0, "d0": None, "dmin": None}
        self._begin_stage()

    def _targets(self):
        k1 = k2 = v = None
        for y in range(H):
            for x in range(W):
                t = self.terrain[y][x]
                if t == "K1":
                    k1 = (x, y)
                elif t == "K2":
                    k2 = (x, y)
                elif t == "V":
                    v = (x, y)
        return k1, k2, v

    def _begin_stage(self):
        k1, k2, v = self._targets()
        hk1, hk2 = self.hero["keys"]
        hx, hy = self.hero["x"], self.hero["y"]
        if not (hk1 or hk2):
            targets = [p for p in (k1, k2) if p]
        elif hk1 and hk2:
            targets = [v] if v else []
        else:
            targets = [k2 if hk1 else k1]
            targets = [p for p in targets if p]
        if not targets:
            self.stage = {"k": self.stage.get("k", 0), "d0": 0, "dmin": 0}
            return
        d = min(abs(hx - t[0]) + abs(hy - t[1]) for t in targets)
        self.stage = {"k": self.stage.get("k", 0), "d0": d, "dmin": d}

    # -- helpers -----------------------------------------------------------
    def is_wall(self, x, y):
        if not in_bounds(x, y):
            return True
        t = self.terrain[y][x]
        if t in HIGH_WALL_BASE:
            return True
        if t == "R_GATE" and not self.gates_flipped:
            return True
        if t == "B_GATE" and self.gates_flipped:
            return True
        return False

    def occ_is_blocker(self, x, y):
        return self.occ[y][x] in ("BOX", "TNT")

    def enterable(self, x, y):
        return (not self.is_wall(x, y)) and self.occ[y][x] is None

    def _hero(self, x, y):
        self.hero["x"] = x
        self.hero["y"] = y

    def _clear_clue(self, x, y):
        c = self.mimic_clue.pop((x, y), None)
        if c is not None:
            self.clues[c[1]][c[0]] = False

    def _damage(self, dmg, is_self=False):
        h = self.hero["hp"]
        eff = min(max(h, 0), dmg)
        self.hero["hp"] = h - dmg
        if not is_self:
            self.trap_damage += eff
        return eff

    # -- atomic displacement with momentum ---------------------------------
    def run_chain(self, kind, x0, y0, x1, y1, dkey, steps=0, portal_count=0, blocker=None):
        """kind: 'HERO' or 'BOX'. blocker: hero cell treated as an obstacle for boxes."""
        stop_momentum = False
        while True:
            steps += 1
            # 2. leave hook
            if self.terrain[y0][x0] == "CRACK":
                self.terrain[y0][x0] = "PIT"
            # 3. update coords / exposed
            if kind == "BOX":
                self.occ[y0][x0] = None
                self.occ[y1][x1] = "BOX"
            else:
                self._hero(x1, y1)
                self.exposed.add((x1, y1))
            # 4. arrive hooks
            t = self.terrain[y1][x1]
            if kind == "BOX":
                if t == "PIT":
                    self.occ[y1][x1] = None
                    self.terrain[y1][x1] = "EMPTY"
                    return (x1, y1, steps, portal_count, "stopped")
                if t == "MIMIC":
                    self.terrain[y1][x1] = "EMPTY"
                    self._clear_clue(x1, y1)
                elif t == "SWITCH":
                    self.gates_flipped = not self.gates_flipped
            else:
                if t == "PIT":
                    self._damage(100)
                elif t == "MIMIC":
                    self._damage(45)
                    self.terrain[y1][x1] = "EMPTY"
                    self._clear_clue(x1, y1)
                    stop_momentum = True
                elif t == "HEAL":
                    self.hero["hp"] = min(100, self.hero["hp"] + 30)
                    self.terrain[y1][x1] = "EMPTY"
                elif t == "SWITCH":
                    self.gates_flipped = not self.gates_flipped
            # 5. death
            if kind != "BOX" and self.hero["hp"] <= 0:
                self.status = "DEAD"
                return (x1, y1, steps, portal_count, "dead")
            # 6. keys / vault
            if kind != "BOX":
                t2 = self.terrain[y1][x1]
                if t2 == "K1" and not self.hero["keys"][0]:
                    self.hero["keys"][0] = True
                    self.terrain[y1][x1] = "EMPTY"
                    self._key_stage(0)
                elif t2 == "K2" and not self.hero["keys"][1]:
                    self.hero["keys"][1] = True
                    self.terrain[y1][x1] = "EMPTY"
                    self._key_stage(1)
                elif t2 == "V" and self.hero["keys"][0] and self.hero["keys"][1] and self.hero["hp"] > 0:
                    self.status = "CLEARED"
                    return (x1, y1, steps, portal_count, "cleared")
            # 7. step cap / momentum stop
            if steps >= 32 or stop_momentum:
                return (x1, y1, steps, portal_count, "stopped")
            # 8. momentum continuation
            t = self.terrain[y1][x1]
            dx, dy = DIRS[dkey]
            if t in MIRRORS:
                dkey = MIRROR_MAP[t][dkey]
                dx, dy = DIRS[dkey]
                nx, ny = x1 + dx, y1 + dy
                if self._can_enter(kind, nx, ny, blocker):
                    x0, y0, x1, y1 = x1, y1, nx, ny
                    continue
                return (x1, y1, steps, portal_count, "stopped")
            if t == "ICE":
                nx, ny = x1 + dx, y1 + dy
                if self._can_enter(kind, nx, ny, blocker):
                    x0, y0, x1, y1 = x1, y1, nx, ny
                    continue
                return (x1, y1, steps, portal_count, "stopped")
            if t in SPRINGS:
                dkey = SPRING_DIR[t]
                dx, dy = DIRS[dkey]
                land = None
                for k in (1, 2, 3):
                    px, py = x1 + k * dx, y1 + k * dy
                    blocked = self._spring_blocked(kind, px, py, blocker)
                    if blocked:
                        if kind == "BOX" and self.occ[py][px] == "TNT":
                            self.tnt_armed.add((px, py))
                        if k == 1:
                            land = None
                        else:
                            land = (x1 + (k - 1) * dx, y1 + (k - 1) * dy)
                        break
                else:
                    land = (x1 + 3 * dx, y1 + 3 * dy)
                if land is None or (land[0] == x1 and land[1] == y1):
                    return (x1, y1, steps, portal_count, "stopped")
                x0, y0, x1, y1 = x1, y1, land[0], land[1]
                continue
            if t in PORTALS:
                pairtile = PORTAL_PAIR[t]
                px = py = None
                for yy in range(H):
                    for xx in range(W):
                        if self.terrain[yy][xx] == pairtile:
                            px, py = xx, yy
                if px is None:
                    return (x1, y1, steps, portal_count, "stopped")
                ok = self.occ[py][px] is None
                if kind == "BOX" and (px, py) == (self.hero["x"], self.hero["y"]) and blocker is None:
                    ok = False
                if kind == "BOX" and blocker is not None and (px, py) == blocker:
                    ok = False
                if kind == "BOX" and self.terrain[py][px] in ("K1", "K2", "V"):
                    ok = False
                if not ok:
                    return (x1, y1, steps, portal_count, "stopped")
                portal_count += 1
                # teleport as a displacement (steps 1..7 semantics)
                steps += 1
                if self.terrain[y1][x1] == "CRACK":
                    self.terrain[y1][x1] = "PIT"
                if kind == "BOX":
                    self.occ[y1][x1] = None
                    self.occ[py][px] = "BOX"
                else:
                    self._hero(px, py)
                    self.exposed.add((px, py))
                x1, y1 = px, py
                t = self.terrain[y1][x1]
                if kind == "BOX":
                    if t == "PIT":
                        self.occ[y1][x1] = None
                        self.terrain[y1][x1] = "EMPTY"
                        return (x1, y1, steps, portal_count, "stopped")
                    if t == "MIMIC":
                        self.terrain[y1][x1] = "EMPTY"
                        self._clear_clue(x1, y1)
                    elif t == "SWITCH":
                        self.gates_flipped = not self.gates_flipped
                else:
                    if t == "PIT":
                        self._damage(100)
                    elif t == "MIMIC":
                        self._damage(45)
                        self.terrain[y1][x1] = "EMPTY"
                        self._clear_clue(x1, y1)
                        stop_momentum = True
                    elif t == "HEAL":
                        self.hero["hp"] = min(100, self.hero["hp"] + 30)
                        self.terrain[y1][x1] = "EMPTY"
                    elif t == "SWITCH":
                        self.gates_flipped = not self.gates_flipped
                if kind != "BOX" and self.hero["hp"] <= 0:
                    self.status = "DEAD"
                    return (x1, y1, steps, portal_count, "dead")
                if kind != "BOX":
                    t2 = self.terrain[y1][x1]
                    if t2 == "K1" and not self.hero["keys"][0]:
                        self.hero["keys"][0] = True
                        self.terrain[y1][x1] = "EMPTY"
                        self._key_stage(0)
                    elif t2 == "K2" and not self.hero["keys"][1]:
                        self.hero["keys"][1] = True
                        self.terrain[y1][x1] = "EMPTY"
                        self._key_stage(1)
                    elif t2 == "V" and self.hero["keys"][0] and self.hero["keys"][1] and self.hero["hp"] > 0:
                        self.status = "CLEARED"
                        return (x1, y1, steps, portal_count, "cleared")
                if steps >= 32 or stop_momentum or portal_count >= 2:
                    return (x1, y1, steps, portal_count, "stopped")
                # one step forward
                dx, dy = DIRS[dkey]
                nx, ny = x1 + dx, y1 + dy
                if self._can_enter(kind, nx, ny, blocker):
                    x0, y0, x1, y1 = x1, y1, nx, ny
                    continue
                return (x1, y1, steps, portal_count, "stopped")
            # normal friction
            return (x1, y1, steps, portal_count, "stopped")

    def _key_stage(self, which):
        k = 1 if which == 0 or self.hero["keys"][0] else 1
        got = sum(1 for b in self.hero["keys"] if b)
        self.stage = {"k": got, "d0": None, "dmin": None}
        self._begin_stage()

    def _can_enter(self, kind, x, y, blocker):
        if not in_bounds(x, y):
            return False
        if self.is_wall(x, y):
            return False
        if self.occ[y][x] in ("BOX", "TNT"):
            return False
        if kind == "BOX":
            if blocker is not None and (x, y) == blocker:
                return False
            if self.terrain[y][x] in ("K1", "K2", "V"):
                return False
        return True

    def _spring_blocked(self, kind, x, y, blocker):
        if not in_bounds(x, y):
            return True
        if self.is_wall(x, y):
            return True
        if self.occ[y][x] in ("BOX", "TNT"):
            return True
        if kind == "BOX":
            if blocker is not None and (x, y) == blocker:
                return True
            if self.terrain[y][x] in ("K1", "K2", "V"):
                return True
        return False

    # -- turn --------------------------------------------------------------
    def play_turn(self, action):
        if self.status != "ALIVE":
            return
        if self.turn > MAX_TURNS:
            self.status = "TIMEOUT"
            return
        self.exposed = {(self.hero["x"], self.hero["y"])}
        self.tnt_armed = set()
        self.trace.append(action)
        self._phase_ab(action)
        if self.status != "ALIVE":
            self.turn += 1
            return
        self._phase_c()
        if self.status != "ALIVE":
            self.turn += 1
            return
        if self.turn % 3 == 0:
            self._phase_d()
            if self.status != "ALIVE":
                self.turn += 1
                return
        if self.turn >= MAX_TURNS:
            self.status = "TIMEOUT"
        self.turn += 1
        # stage distance tracking
        if self.stage.get("d0") is not None:
            k1, k2, v = self._targets()
            hk1, hk2 = self.hero["keys"]
            hx, hy = self.hero["x"], self.hero["y"]
            if hk1 and hk2:
                tg = [v] if v else []
            elif hk1 or hk2:
                tg = [(k2 if hk1 else k1)]
                tg = [p for p in tg if p]
            else:
                tg = [p for p in (k1, k2) if p]
            if tg:
                d = min(abs(hx - t[0]) + abs(hy - t[1]) for t in tg)
                self.stage["dmin"] = min(self.stage["dmin"], d)

    def _phase_ab(self, action):
        hx, hy = self.hero["x"], self.hero["y"]
        if action == "WAIT":
            return
        if action == "BOMB":
            if self.hero["bombs"] > 0 and not any(b["x"] == hx and b["y"] == hy for b in self.bombs):
                self.hero["bombs"] -= 1
                self.bombs.append({"id": self.next_id, "x": hx, "y": hy, "timer": 3})
                self.next_id += 1
            return
        if action.startswith("MOVE_"):
            dkey = ACTION_DIR[action]
            dx, dy = DIRS[dkey]
            p1 = (hx + dx, hy + dy)
            p2 = (hx + 2 * dx, hy + 2 * dy)
            if self.is_wall(*p1) or (in_bounds(*p1) and self.occ[p1[1]][p1[0]] == "TNT"):
                return
            if in_bounds(*p1) and self.occ[p1[1]][p1[0]] == "BOX":
                box_ok = (not self.is_wall(*p2)) and in_bounds(*p2) and self.occ[p2[1]][p2[0]] is None \
                    and self.terrain[p2[1]][p2[0]] not in ("K1", "K2", "V")
                if not box_ok:
                    return
                self.run_chain("BOX", p1[0], p1[1], p2[0], p2[1], dkey, blocker=(hx, hy))
                if not self.enterable(*p1):
                    return
                self.run_chain("HERO", hx, hy, p1[0], p1[1], dkey)
                return
            if in_bounds(*p1) and self.occ[p1[1]][p1[0]] is None:
                self.run_chain("HERO", hx, hy, p1[0], p1[1], dkey)
            return
        if action.startswith("JUMP_"):
            if self.hero["jumps"] == 0:
                return
            self.hero["jumps"] -= 1
            dkey = ACTION_DIR[action]
            dx, dy = DIRS[dkey]
            p1 = (hx + dx, hy + dy)
            p2 = (hx + 2 * dx, hy + 2 * dy)
            blocked = self.is_wall(*p1) or self.is_wall(*p2)
            if in_bounds(*p2) and self.occ[p2[1]][p2[0]] in ("BOX", "TNT"):
                blocked = True
            if blocked:
                return
            self.run_chain("HERO", hx, hy, p2[0], p2[1], dkey)
            return
        if action.startswith("THROW_"):
            if self.hero["throws"] == 0:
                return
            self.hero["throws"] -= 1
            dkey = ACTION_DIR[action]
            self._throw(dkey)
            return

    def _throw(self, dkey):
        sx, sy = self.hero["x"], self.hero["y"]
        range_left = 6
        stone_portals = 0
        destroyed = False
        while range_left > 0:
            dx, dy = DIRS[dkey]
            nx, ny = sx + dx, sy + dy
            range_left -= 1
            sx, sy = nx, ny
            if not in_bounds(sx, sy):
                destroyed = True
                break
            if self.is_wall(sx, sy) or self.occ[sy][sx] == "BOX":
                destroyed = True
                break
            if self.occ[sy][sx] == "TNT":
                self.tnt_armed.add((sx, sy))
                destroyed = True
                break
            t = self.terrain[sy][sx]
            if t == "SWITCH":
                self.gates_flipped = not self.gates_flipped
                destroyed = True
                break
            if t == "MIMIC":
                self.terrain[sy][sx] = "EMPTY"
                self._clear_clue(sx, sy)
                destroyed = True
                break
            if t in MIRRORS:
                dkey = MIRROR_MAP[t][dkey]
                continue
            if t in PORTALS and stone_portals < 2:
                pairtile = PORTAL_PAIR[t]
                px = py = None
                for yy in range(H):
                    for xx in range(W):
                        if self.terrain[yy][xx] == pairtile:
                            px, py = xx, yy
                if px is not None and self.occ[py][px] not in ("BOX", "TNT"):
                    sx, sy = px, py
                    stone_portals += 1
                    if stone_portals == 2:
                        destroyed = True
                        break
                    continue
        if destroyed or range_left != 0:
            return
        # 6th cell landing -> ground slide
        t = self.terrain[sy][sx]
        if t not in ("ICE",) and t not in MIRRORS:
            return
        for _ in range(32):
            dx, dy = DIRS[dkey]
            nx, ny = sx + dx, sy + dy
            if not in_bounds(nx, ny):
                return
            if self.is_wall(nx, ny) or self.occ[ny][nx] == "BOX":
                return
            sx, sy = nx, ny
            if self.occ[sy][sx] == "TNT":
                self.tnt_armed.add((sx, sy))
                return
            t = self.terrain[sy][sx]
            if t == "SWITCH":
                self.gates_flipped = not self.gates_flipped
                return
            if t == "MIMIC":
                self.terrain[sy][sx] = "EMPTY"
                self._clear_clue(sx, sy)
                return
            if t in MIRRORS:
                dkey = MIRROR_MAP[t][dkey]
                continue
            if t == "ICE":
                continue
            if t in PORTALS:
                pairtile = PORTAL_PAIR[t]
                px = py = None
                for yy in range(H):
                    for xx in range(W):
                        if self.terrain[yy][xx] == pairtile:
                            px, py = xx, yy
                if px is not None and self.occ[py][px] not in ("BOX", "TNT"):
                    sx, sy = px, py
                    continue
                return
            return

    def _explosion(self, sources):
        """sources: list of (x, y, kind) kind in ('TNT','BOMB'); chain closure + damage."""
        if not sources:
            return
        queue = deque(sources)
        seen = set()
        exploded_tnt = []
        exploded_bomb_pos = []
        a = 0
        b = 0
        cells = set()
        while queue:
            ex, ey, kind = queue.popleft()
            key = (ex, ey, kind)
            if key in seen:
                continue
            seen.add(key)
            if kind == "TNT":
                exploded_tnt.append((ex, ey))
            else:
                exploded_bomb_pos.append((ex, ey))
            hx, hy = self.hero["x"], self.hero["y"]
            if abs(hx - ex) <= 1 and abs(hy - ey) <= 1:
                if kind == "TNT":
                    a += 60
                else:
                    b += 50
            for cy in range(ey - 1, ey + 2):
                for cx in range(ex - 1, ex + 2):
                    if not in_bounds(cx, cy):
                        continue
                    cells.add((cx, cy))
                    if self.occ[cy][cx] == "TNT" and (cx, cy, "TNT") not in seen:
                        queue.append((cx, cy, "TNT"))
                    for bm in self.bombs:
                        if bm["x"] == cx and bm["y"] == cy and (cx, cy, "BOMB") not in seen:
                            queue.append((cx, cy, "BOMB"))
        h = self.hero["hp"]
        if a + b > 0:
            eff = min(h, a + b) * (a / (a + b))
            self.trap_damage += eff
            self.hero["hp"] = h - (a + b)
        # remove exploded entities
        for (x, y) in exploded_tnt:
            if self.occ[y][x] == "TNT":
                self.occ[y][x] = None
        self.bombs = [bm for bm in self.bombs if (bm["x"], bm["y"]) not in set(exploded_bomb_pos)]
        # terrain changes
        for (cx, cy) in cells:
            if self.occ[cy][cx] == "BOX":
                self.occ[cy][cx] = None
            t = self.terrain[cy][cx]
            if t in EXPLOSION_IMMUNE:
                continue
            if t == "CRACK":
                self.terrain[cy][cx] = "PIT"
            elif t in ("W", "ICE", "SWITCH", "R_GATE", "B_GATE", "HEAL", "MIMIC") or t in MIRRORS or t in SPRINGS or t in LASERS:
                if t == "MIMIC":
                    self._clear_clue(cx, cy)
                self.terrain[cy][cx] = "EMPTY"
        # support check
        for y in range(H):
            for x in range(W):
                if self.occ[y][x] == "BOX" and self.terrain[y][x] == "PIT":
                    self.occ[y][x] = None
                    self.terrain[y][x] = "EMPTY"
        if self.hero["hp"] > 0:
            hx, hy = self.hero["x"], self.hero["y"]
            if self.terrain[hy][hx] == "PIT":
                self._damage(100)
        if self.hero["hp"] <= 0:
            self.status = "DEAD"

    def _phase_c(self):
        for bm in self.bombs:
            bm["timer"] -= 1
        sources = []
        for bm in self.bombs:
            if bm["timer"] == 0:
                sources.append((bm["x"], bm["y"], "BOMB"))
        for (x, y) in self.tnt_armed:
            if self.occ[y][x] == "TNT":
                sources.append((x, y, "TNT"))
        self.tnt_armed = set()
        if sources:
            self._explosion(sources)

    def _phase_d(self):
        beams = []
        for y in range(H):
            for x in range(W):
                t = self.terrain[y][x]
                if t not in LASERS:
                    continue
                dkey = {"LASER_U": "U", "LASER_D": "D", "LASER_L": "L", "LASER_R": "R"}[t]
                dx, dy = DIRS[dkey]
                cells = set()
                for d in range(1, 11):
                    nx, ny = x + d * dx, y + d * dy
                    if not in_bounds(nx, ny):
                        break
                    if self.is_wall(nx, ny) or self.occ[ny][nx] == "BOX":
                        break
                    if self.occ[ny][nx] == "TNT":
                        self.tnt_armed.add((nx, ny))
                        break
                    cells.add((nx, ny))
                beams.append(cells)
        m = sum(1 for cells in beams if cells & self.exposed)
        if m > 0:
            self.trap_damage += min(max(self.hero["hp"], 0), 50 * m)
            self.hero["hp"] -= 50 * m
            if self.hero["hp"] <= 0:
                self.status = "DEAD"
                return
        if self.tnt_armed:
            armed = [(x, y, "TNT") for (x, y) in self.tnt_armed if self.occ[y][x] == "TNT"]
            self.tnt_armed = set()
            self._explosion(armed)

    # -- scoring -----------------------------------------------------------
    def progress(self):
        k = sum(1 for b in self.hero["keys"] if b)
        d0 = self.stage.get("d0")
        dmin = self.stage.get("dmin")
        if d0 is None or d0 == 0:
            r = 0.0
        else:
            r = max(0.0, (d0 - (dmin if dmin is not None else d0)) / max(1, d0))
        return min(k + r, 3.0), k, r

    def scores(self):
        P, k, r = self.progress()
        g = None
        spent = None
        if self._grid is not None:
            ok, errs, info = validate_grid(self._grid)
            spent = info.get("spent", 0)
            g = (BUDGET - spent) / BUDGET
        if self.status == "CLEARED":
            T = self.turn - 1 if self.turn > 1 else 1
            T = min(max(T, 1), 240)
            hsc = 600 + 1.5 * max(0, self.hero["hp"]) + 150 * (240 - T) / 239 + 100 * (g or 0)
        else:
            T = 240
            hsc = 200 * P
        if g is None:
            dsc = None
        else:
            D = min(100.0, self.trap_damage)
            if self.status == "DEAD":
                dsc = 500 + 50 * (3 - P) + D + 250 * g
            elif self.status == "TIMEOUT":
                dsc = 320 + 50 * (3 - P) + D + 125 * g
            else:
                dsc = 2.0 * D + 120 * (T - 1) / 239
        return {
            "status": self.status, "turns": self.turn - 1, "hp": self.hero["hp"],
            "keys": list(self.hero["keys"]), "P": P, "D": min(100.0, self.trap_damage),
            "g": g, "spent": spent, "hero_score": round(hsc, 2),
            "demon_score": None if dsc is None else round(dsc, 2),
        }


# ---------------------------------------------------------------------------
# convenience runners
# ---------------------------------------------------------------------------

def run_actions(grid, actions, max_turns=MAX_TURNS):
    eng = Engine(grid=grid)
    cleared_at = None
    for i, a in enumerate(actions):
        if eng.status != "ALIVE":
            break
        eng.play_turn(a)
        if eng.status == "CLEARED":
            cleared_at = i + 1
            break
    return eng, cleared_at


def check_author_solution(grid, actions):
    """Return (ok, message)."""
    if not isinstance(actions, (list, tuple)):
        return False, "author_solution must be a list"
    if not (1 <= len(actions) <= 240):
        return False, "author_solution length %d out of range" % len(actions)
    for a in actions:
        if a not in ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT", "JUMP_U", "JUMP_D",
                     "JUMP_L", "JUMP_R", "THROW_U", "THROW_D", "THROW_L", "THROW_R", "BOMB"):
            return False, "illegal action %r" % (a,)
    eng, cleared_at = run_actions(grid, actions)
    if cleared_at is None:
        return False, "did not clear (status=%s turn=%d hp=%s keys=%s)" % (
            eng.status, eng.turn - 1, eng.hero["hp"], eng.hero["keys"])
    if cleared_at != len(actions):
        return False, "cleared at step %d but solution has %d steps" % (cleared_at, len(actions))
    return True, "ok: cleared at step %d with hp=%d" % (cleared_at, eng.hero["hp"])


# ---------------------------------------------------------------------------
# BLIND observation generator
# ---------------------------------------------------------------------------

def vision_mask(eng, hx, hy):
    vis = [[False] * W for _ in range(H)]

    def open_(dx, dy):
        x, y = hx + dx, hy + dy
        if not in_bounds(x, y):
            return False
        if not vis_ok(dx, dy):
            return False
        return not eng.is_wall(x, y)

    def vis_ok(dx, dy):
        if dx * dx + dy * dy > 10:
            return False
        m = max(abs(dx), abs(dy))
        if m == 0:
            return True
        sx = (dx > 0) - (dx < 0)
        sy = (dy > 0) - (dy < 0)
        if m == 1:
            return True
        if dx == 0 or dy == 0:
            return open_(dx - sx, dy - sy)
        if abs(dx) == 2 and abs(dy) == 2:
            if not open_(sx, sy):
                return False
            x1, y1 = hx + sx, hy + sy
            wx = eng.is_wall(x1, hy) or not in_bounds(hx + sx, hy)
            wy = eng.is_wall(hx, hy + sy) or not in_bounds(hx, hy + sy)
            return not (wx and wy)
        if abs(dx) > abs(dy):
            return open_(dx - sx, dy) or open_(dx - sx, dy - sy)
        return open_(dx, dy - sy) or open_(dx - sx, dy - sy)

    for dy in range(-3, 4):
        for dx in range(-3, 4):
            if vis_ok(dx, dy):
                x, y = hx + dx, hy + dy
                if in_bounds(x, y):
                    vis[y][x] = True
    # adjacent ice / mirror slide extension
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        x, y = hx + dx, hy + dy
        if not in_bounds(x, y):
            continue
        if eng.terrain[y][x] not in ("ICE",) and eng.terrain[y][x] not in MIRRORS:
            continue
        dkey = "R" if dx > 0 else ("L" if dx < 0 else ("D" if dy > 0 else "U"))
        cx, cy = x, y
        for _ in range(12):
            cdx, cdy = DIRS[dkey]
            nx, ny = cx + cdx, cy + cdy
            if not in_bounds(nx, ny) or eng.is_wall(nx, ny):
                break
            vis[ny][nx] = True
            if eng.terrain[ny][nx] in MIRRORS:
                dkey = MIRROR_MAP[eng.terrain[ny][nx]][dkey]
            elif eng.terrain[ny][nx] != "ICE":
                break
            cx, cy = nx, ny
    return vis


def make_state(eng, mode="BLIND"):
    hx, hy = eng.hero["x"], eng.hero["y"]
    if mode == "FULL":
        vis = [[True] * W for _ in range(H)]
    else:
        vis = vision_mask(eng, hx, hy)
    terrain = [["UNKNOWN"] * W for _ in range(H)]
    occ = [[None] * W for _ in range(H)]
    clues = [[False] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if not vis[y][x]:
                continue
            t = eng.terrain[y][x]
            if t in ("HEAL", "MIMIC"):
                t = "CHEST"
            terrain[y][x] = t
            occ[y][x] = eng.occ[y][x]
            clues[y][x] = eng.clues[y][x]
    bombs = [{"x": b["x"], "y": b["y"], "timer": b["timer"]} for b in eng.bombs if vis[b["y"]][b["x"]]]
    warnings = []
    if eng.turn % 3 == 0:
        # beams from current snapshot, restricted to vision
        for y in range(H):
            for x in range(W):
                t = eng.terrain[y][x]
                if t not in LASERS:
                    continue
                dkey = {"LASER_U": "U", "LASER_D": "D", "LASER_L": "L", "LASER_R": "R"}[t]
                dx, dy = DIRS[dkey]
                for d in range(1, 11):
                    nx, ny = x + d * dx, y + d * dy
                    if not in_bounds(nx, ny):
                        break
                    if eng.is_wall(nx, ny) or eng.occ[ny][nx] == "BOX":
                        break
                    if eng.occ[ny][nx] == "TNT":
                        break
                    if vis[ny][nx]:
                        warnings.append({"x": nx, "y": ny, "dir": dkey})
        warnings.sort(key=lambda w: (w["y"], w["x"], w["dir"]))
    k1, k2, v = eng._targets()
    return {
        "turn": eng.turn,
        "turns_left": MAX_TURNS - eng.turn + 1,
        "mode": mode,
        "hero": {
            "x": hx, "y": hy, "hp": eng.hero["hp"],
            "keys": list(eng.hero["keys"]), "jumps": eng.hero["jumps"],
            "throws": eng.hero["throws"], "bombs": eng.hero["bombs"],
        },
        "gates_flipped": eng.gates_flipped,
        "targets": {"K1": list(k1) if k1 else None, "K2": list(k2) if k2 else None,
                    "V": list(v) if v else None},
        "visible_mask": vis,
        "terrain": terrain,
        "occupant": occ,
        "bombs": bombs,
        "clues": clues,
        "laser_warnings": warnings,
    }
