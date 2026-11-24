"""
Local Judge Engine & Golden Vector Verifier for v2.2 FULL Mode.
Strictly implements RULES_FULL_v22.md and validates all 8 golden_vectors_v22.json cases.
"""

import collections
import copy
import json
import math
import random
import time

GRID_WIDTH = 40
GRID_HEIGHT = 26
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

DIRECTIONS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}

MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}

SPRING_DIR = {
    "SPRING_U": "U", "SPRING_D": "D", "SPRING_L": "L", "SPRING_R": "R",
}

LASER_RED_DIR = {
    "LASER_U": "U", "LASER_D": "D", "LASER_L": "L", "LASER_R": "R",
}

LASER_BLUE_DIR = {
    "LASER2_U": "U", "LASER2_D": "D", "LASER2_L": "L", "LASER2_R": "R",
}

ALL_LASER_DIR = {**LASER_RED_DIR, **LASER_BLUE_DIR}

ONEWAY_DIR = {
    "ONEWAY_U": "U", "ONEWAY_D": "D", "ONEWAY_L": "L", "ONEWAY_R": "R",
}

PORTAL_PAIR_TILE = {
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

EXPLOSION_IMMUNE = {
    "T_W", "K1", "K2", "V",
    "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
    "PIT", "EMPTY",
    "PLATE", "P_GATE",
    "ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R",
}


def in_bounds(x: int, y: int) -> bool:
    return 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT


def is_outer_frame(x: int, y: int) -> bool:
    return x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1


def is_spawn_clearance(x: int, y: int) -> bool:
    return 1 <= x <= 3 and 12 <= y <= 14


def manhattan(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def validate_and_decode_grid_v22(grid, check_spawn_4turn: bool = True):
    if not isinstance(grid, list) or len(grid) != GRID_HEIGHT:
        return False, "Invalid grid height", None
    for y, row in enumerate(grid):
        if not isinstance(row, list) or len(row) != GRID_WIDTH:
            return False, f"Invalid row width at y={y}", None
        for x, t in enumerate(row):
            if t not in TILE_COSTS:
                return False, f"Unknown tile {t} at ({x},{y})", None
            if is_outer_frame(x, y) and t != "T_W":
                return False, f"Outer frame ({x},{y}) must be T_W, got {t}", None
            if is_spawn_clearance(x, y) and t != "EMPTY":
                return False, f"Spawn clearance ({x},{y}) must be EMPTY, got {t}", None

    counts = collections.Counter()
    landmarks = {}
    spent_gold = 0
    for y in range(1, GRID_HEIGHT - 1):
        for x in range(1, GRID_WIDTH - 1):
            t = grid[y][x]
            counts[t] += 1
            spent_gold += TILE_COSTS[t]
            if t in ("K1", "K2", "V"):
                landmarks.setdefault(t, []).append((x, y))

    for lm in ("K1", "K2", "V"):
        if len(landmarks.get(lm, [])) != 1:
            return False, f"Landmark {lm} count != 1", None

    k1 = landmarks["K1"][0]
    k2 = landmarks["K2"][0]
    v = landmarks["V"][0]
    if not (12 <= k1[0] <= 34 and 2 <= k1[1] <= 10):
        return False, f"K1 out of zone: {k1}", None
    if not (12 <= k2[0] <= 34 and 15 <= k2[1] <= 23):
        return False, f"K2 out of zone: {k2}", None
    if manhattan(k1, k2) < 12:
        return False, f"K1-K2 manhattan < 12", None
    if not (33 <= v[0] <= 37 and 4 <= v[1] <= 21):
        return False, f"V out of zone: {v}", None

    if spent_gold > MAX_BUDGET:
        return False, f"Budget exceeded: {spent_gold} > {MAX_BUDGET}", None

    if counts["T_W"] > 120:
        return False, f"Inner T_W > 120: {counts['T_W']}", None
    if sum(counts[m] for m in MIRROR_MAP) > 30:
        return False, "MIRROR > 30", None
    if sum(counts[s] for s in SPRING_DIR) > 20:
        return False, "SPRING > 20", None
    if sum(counts[l] for l in ALL_LASER_DIR) > 12:
        return False, "LASER + LASER2 > 12", None
    if counts["CRACK"] > 40:
        return False, "CRACK > 40", None
    if counts["SWITCH"] > 6:
        return False, "SWITCH > 6", None
    if counts["R_GATE"] + counts["B_GATE"] > 16:
        return False, "R_GATE + B_GATE > 16", None
    if counts["PLATE"] > 4:
        return False, "PLATE > 4", None
    if counts["P_GATE"] > 8:
        return False, "P_GATE > 8", None
    if counts["P_GATE"] > 0 and not (1 <= counts["PLATE"] <= counts["BOX"]):
        return False, f"P_GATE used but not (1 <= PLATE({counts['PLATE']}) <= BOX({counts['BOX']}))", None
    if sum(counts[o] for o in ONEWAY_DIR) > 12:
        return False, "ONEWAY > 12", None
    if counts["TNT"] > 12:
        return False, "TNT > 12", None
    if counts["BOX"] > 6:
        return False, "BOX > 6", None
    if counts["HEAL"] > 4:
        return False, "HEAL > 4", None
    if counts["MIMIC"] > 4:
        return False, "MIMIC > 4", None
    if counts["PORTAL_1A"] != counts["PORTAL_1B"] or counts["PORTAL_1A"] > 1:
        return False, "Invalid PORTAL_1 pair", None
    if counts["PORTAL_2A"] != counts["PORTAL_2B"] or counts["PORTAL_2A"] > 1:
        return False, "Invalid PORTAL_2 pair", None

    terrain = [["EMPTY"] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    occupant = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    portals = {}
    plates = []
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            t = grid[y][x]
            if t in ("BOX", "TNT"):
                terrain[y][x] = "EMPTY"
                occupant[y][x] = t
            else:
                terrain[y][x] = t
                if t in PORTAL_PAIR_TILE:
                    portals[t] = (x, y)
                elif t == "PLATE":
                    plates.append((x, y))

    clues = [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    mimic_to_clue = {}
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if terrain[y][x] == "MIMIC":
                bound = None
                for dname in ("U", "D", "L", "R"):
                    dx, dy = DIRECTIONS[dname]
                    nx, ny = x + dx, y + dy
                    if not in_bounds(nx, ny):
                        continue
                    if terrain[ny][nx] != "EMPTY" or occupant[ny][nx] is not None:
                        continue
                    if is_spawn_clearance(nx, ny) or clues[ny][nx]:
                        continue
                    other_chest = False
                    for d2 in ("U", "D", "L", "R"):
                        ax, ay = nx + DIRECTIONS[d2][0], ny + DIRECTIONS[d2][1]
                        if (ax, ay) != (x, y) and in_bounds(ax, ay):
                            if terrain[ay][ax] in ("HEAL", "MIMIC"):
                                other_chest = True
                                break
                    if not other_chest:
                        bound = (nx, ny)
                        break
                if bound is None:
                    return False, f"MIMIC at ({x},{y}) has no valid clue cell", None
                clues[bound[1]][bound[0]] = True
                mimic_to_clue[(x, y)] = bound

    decoded = {
        "terrain": terrain,
        "occupant": occupant,
        "clues": clues,
        "mimic_to_clue": mimic_to_clue,
        "portals": portals,
        "plates": plates,
        "targets": {"K1": list(k1), "K2": list(k2), "V": list(v)},
        "spent_gold": spent_gold,
        "inner_tw_count": counts["T_W"],
    }

    if check_spawn_4turn:
        ok_sp, msg_sp = verify_spawn_4_turn_fairness(decoded)
        if not ok_sp:
            return False, msg_sp, None

    return True, "OK", decoded


class DungeonEngineV22:
    def __init__(self, decoded: dict):
        self.terrain = [row[:] for row in decoded["terrain"]]
        self.occupant = [row[:] for row in decoded["occupant"]]
        self.clues = [row[:] for row in decoded["clues"]]
        self.mimic_to_clue = dict(decoded["mimic_to_clue"])
        self.portals = dict(decoded["portals"])
        self.plates = list(decoded["plates"])
        self.targets = copy.deepcopy(decoded["targets"])
        self.spent_gold = decoded["spent_gold"]

        self.hx, self.hy = SPAWN_POS
        self.hp = 100
        self.has_k1 = False
        self.has_k2 = False
        self.jumps = 3
        self.throws = 3
        self.bombs_inv = 2
        self.gates_flipped = False
        self.bombs = []
        self.next_bomb_id = 1

        self.turn = 0
        self.status = "ALIVE"
        self.trap_damage = 0.0
        self.exposed_cells = set()

        self.stage = 0
        self.stage_d0 = self._dist_to_next_target((self.hx, self.hy))
        self.stage_dmin = self.stage_d0

    def clone(self):
        c = DungeonEngineV22.__new__(DungeonEngineV22)
        c.terrain = [r[:] for r in self.terrain]
        c.occupant = [r[:] for r in self.occupant]
        c.clues = [r[:] for r in self.clues]
        c.mimic_to_clue = dict(self.mimic_to_clue)
        c.portals = self.portals
        c.plates = self.plates
        c.targets = self.targets
        c.spent_gold = self.spent_gold
        c.hx, c.hy = self.hx, self.hy
        c.hp = self.hp
        c.has_k1, c.has_k2 = self.has_k1, self.has_k2
        c.jumps, c.throws, c.bombs_inv = self.jumps, self.throws, self.bombs_inv
        c.gates_flipped = self.gates_flipped
        c.bombs = [dict(b) for b in self.bombs]
        c.next_bomb_id = self.next_bomb_id
        c.turn = self.turn
        c.status = self.status
        c.trap_damage = self.trap_damage
        c.exposed_cells = set(self.exposed_cells)
        c.stage = self.stage
        c.stage_d0 = self.stage_d0
        c.stage_dmin = self.stage_dmin
        return c

    def is_plates_active(self) -> bool:
        if not self.plates:
            return False
        for px, py in self.plates:
            if self.occupant[py][px] != "BOX":
                return False
        return True

    def is_high_wall(self, x: int, y: int) -> bool:
        if not in_bounds(x, y):
            return True
        t = self.terrain[y][x]
        if t in ("W", "T_W") or t in ALL_LASER_DIR:
            return True
        if t == "R_GATE" and not self.gates_flipped:
            return True
        if t == "B_GATE" and self.gates_flipped:
            return True
        if t == "P_GATE" and not self.is_plates_active():
            return True
        return False

    def blocks_oneway(self, x: int, y: int, dname: str) -> bool:
        if not in_bounds(x, y):
            return False
        t = self.terrain[y][x]
        if t in ONEWAY_DIR:
            return ONEWAY_DIR[t] != dname
        return False

    def _dist_to_next_target(self, pos):
        k1 = tuple(self.targets["K1"])
        k2 = tuple(self.targets["K2"])
        v = tuple(self.targets["V"])
        if not self.has_k1 and not self.has_k2:
            return min(manhattan(pos, k1), manhattan(pos, k2))
        elif not self.has_k1:
            return manhattan(pos, k1)
        elif not self.has_k2:
            return manhattan(pos, k2)
        else:
            return manhattan(pos, v)

    def _on_hero_arrive_progress(self, pos, stage_changed: bool):
        if stage_changed:
            self.stage = int(self.has_k1) + int(self.has_k2)
            self.stage_d0 = self._dist_to_next_target(pos)
            self.stage_dmin = self.stage_d0
        else:
            d = self._dist_to_next_target(pos)
            if d < self.stage_dmin:
                self.stage_dmin = d

    def _clear_mimic(self, x: int, y: int):
        self.terrain[y][x] = "EMPTY"
        clue_pos = self.mimic_to_clue.pop((x, y), None)
        if clue_pos is not None:
            self.clues[clue_pos[1]][clue_pos[0]] = False

    def _can_hero_enter(self, x: int, y: int, dname: str) -> bool:
        if self.is_high_wall(x, y) or self.blocks_oneway(x, y, dname):
            return False
        if self.occupant[y][x] in ("BOX", "TNT"):
            return False
        return True

    def _can_box_enter(self, x: int, y: int, dname: str) -> bool:
        if self.is_high_wall(x, y) or self.blocks_oneway(x, y, dname):
            return False
        if self.occupant[y][x] is not None:
            return False
        if (x, y) == (self.hx, self.hy):
            return False
        if self.terrain[y][x] in ("K1", "K2", "V"):
            return False
        return True

    def _find_portal_pair(self, portal_tile: str):
        pair_tile = PORTAL_PAIR_TILE[portal_tile]
        if pair_tile in self.portals:
            return self.portals[pair_tile]
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.terrain[y][x] == pair_tile:
                    self.portals[pair_tile] = (x, y)
                    return (x, y)
        return None

    def _displace(self, entity: str, p0, p1, dname: str, state_ctx: dict, suppress_portal_once: bool = False):
        state_ctx["steps_taken"] += 1
        x0, y0 = p0
        x1, y1 = p1

        if self.terrain[y0][x0] == "CRACK":
            self.terrain[y0][x0] = "PIT"

        if entity == "BOX":
            self.occupant[y0][x0] = None
            self.occupant[y1][x1] = "BOX"
        else:
            self.hx, self.hy = x1, y1
            self.exposed_cells.add((x1, y1))

        t1 = self.terrain[y1][x1]
        stop_momentum = False
        if entity == "BOX":
            if t1 == "PIT":
                self.occupant[y1][x1] = None
                self.terrain[y1][x1] = "EMPTY"
                return
            elif t1 == "MIMIC":
                self._clear_mimic(x1, y1)
            elif t1 == "SWITCH":
                self.gates_flipped = not self.gates_flipped
        else:
            if t1 == "PIT":
                dmg = min(self.hp, 100)
                self.trap_damage += dmg
                self.hp -= 100
            elif t1 == "MIMIC":
                dmg = min(self.hp, 45)
                self.trap_damage += dmg
                self.hp -= 45
                self._clear_mimic(x1, y1)
                stop_momentum = True
            elif t1 == "HEAL":
                self.hp = min(100, self.hp + 30)
                self.terrain[y1][x1] = "EMPTY"
            elif t1 == "SWITCH":
                self.gates_flipped = not self.gates_flipped

        if entity == "HERO" and self.hp <= 0:
            self._on_hero_arrive_progress((x1, y1), False)
            self.status = "DEAD"
            return

        if entity == "HERO":
            stage_changed = False
            cur_t = self.terrain[y1][x1]
            if cur_t == "K1":
                self.has_k1 = True
                self.terrain[y1][x1] = "EMPTY"
                stage_changed = True
            elif cur_t == "K2":
                self.has_k2 = True
                self.terrain[y1][x1] = "EMPTY"
                stage_changed = True
            self._on_hero_arrive_progress((x1, y1), stage_changed)
            if cur_t == "V" and self.has_k1 and self.has_k2 and self.hp > 0:
                self.status = "CLEARED"
                return

        if state_ctx["steps_taken"] >= 32 or stop_momentum:
            return

        cur_t = self.terrain[y1][x1]
        can_enter = self._can_hero_enter if entity == "HERO" else self._can_box_enter

        if suppress_portal_once:
            if state_ctx["portal_count"] >= 2:
                return
            dx, dy = DIRECTIONS[dname]
            nx, ny = x1 + dx, y1 + dy
            if can_enter(nx, ny, dname):
                self._displace(entity, (x1, y1), (nx, ny), dname, state_ctx, False)
            return

        if cur_t == "ICE":
            dx, dy = DIRECTIONS[dname]
            nx, ny = x1 + dx, y1 + dy
            if can_enter(nx, ny, dname):
                self._displace(entity, (x1, y1), (nx, ny), dname, state_ctx, False)
        elif cur_t in MIRROR_MAP:
            ndir = MIRROR_MAP[cur_t][dname]
            dx, dy = DIRECTIONS[ndir]
            nx, ny = x1 + dx, y1 + dy
            if can_enter(nx, ny, ndir):
                self._displace(entity, (x1, y1), (nx, ny), ndir, state_ctx, False)
        elif cur_t in SPRING_DIR:
            sdir = SPRING_DIR[cur_t]
            dx, dy = DIRECTIONS[sdir]
            blocked_k = None
            for k in (1, 2, 3):
                kx, ky = x1 + k * dx, y1 + k * dy
                is_blk = False
                if not in_bounds(kx, ky) or self.is_high_wall(kx, ky) or self.blocks_oneway(kx, ky, sdir):
                    is_blk = True
                elif self.occupant[ky][kx] in ("BOX", "TNT"):
                    is_blk = True
                elif entity == "BOX" and ((kx, ky) == (self.hx, self.hy) or self.terrain[ky][kx] in ("K1", "K2", "V")):
                    is_blk = True
                if is_blk:
                    blocked_k = k
                    if entity == "BOX" and in_bounds(kx, ky) and self.occupant[ky][kx] == "TNT":
                        state_ctx["tnt_armed"].add((kx, ky))
                    break
            if blocked_k == 1:
                return
            tk = (blocked_k - 1) if blocked_k in (2, 3) else 3
            self._displace(entity, (x1, y1), (x1 + tk * dx, y1 + tk * dy), sdir, state_ctx, False)
        elif cur_t in PORTAL_PAIR_TILE:
            p_pair = self._find_portal_pair(cur_t)
            if p_pair is None:
                return
            px, py = p_pair
            if self.occupant[py][px] is not None:
                return
            if entity == "BOX" and (px, py) == (self.hx, self.hy):
                return
            state_ctx["portal_count"] += 1
            self._displace(entity, (x1, y1), (px, py), dname, state_ctx, True)

    def _resolve_explosions(self, initial_bombs, initial_tnts):
        if not initial_bombs and not initial_tnts:
            return
        exploded_bomb_ids = set()
        exploded_tnts = set()
        q = collections.deque()

        for b in initial_bombs:
            if b["id"] not in exploded_bomb_ids:
                exploded_bomb_ids.add(b["id"])
                q.append(("BOMB", b["x"], b["y"]))
        for tx, ty in initial_tnts:
            if (tx, ty) not in exploded_tnts and self.occupant[ty][tx] == "TNT":
                exploded_tnts.add((tx, ty))
                q.append(("TNT", tx, ty))

        bomb_map_by_pos = collections.defaultdict(list)
        for b in self.bombs:
            bomb_map_by_pos[(b["x"], b["y"])].append(b)

        sources = []
        affected_cells = set()
        while q:
            stype, ex, ey = q.popleft()
            sources.append((stype, ex, ey))
            for ny in range(max(0, ey - 1), min(GRID_HEIGHT, ey + 2)):
                for nx in range(max(0, ex - 1), min(GRID_WIDTH, ex + 2)):
                    affected_cells.add((nx, ny))
                    if self.occupant[ny][nx] == "TNT" and (nx, ny) not in exploded_tnts:
                        exploded_tnts.add((nx, ny))
                        q.append(("TNT", nx, ny))
                    for b in bomb_map_by_pos.get((nx, ny), ()):
                        if b["id"] not in exploded_bomb_ids:
                            exploded_bomb_ids.add(b["id"])
                            q.append(("BOMB", b["x"], b["y"]))

        a = 0
        b_dmg = 0
        for stype, ex, ey in sources:
            if abs(self.hx - ex) <= 1 and abs(self.hy - ey) <= 1:
                if stype == "TNT":
                    a += 60
                else:
                    b_dmg += 50

        if a + b_dmg > 0:
            eff = min(self.hp, a + b_dmg) * (a / (a + b_dmg))
            self.trap_damage += eff
            self.hp -= (a + b_dmg)

        self.bombs = [b for b in self.bombs if b["id"] not in exploded_bomb_ids]
        for tx, ty in exploded_tnts:
            if self.occupant[ty][tx] == "TNT":
                self.occupant[ty][tx] = None

        for cx, cy in affected_cells:
            if self.occupant[cy][cx] == "BOX":
                self.occupant[cy][cx] = None
            t = self.terrain[cy][cx]
            if t in EXPLOSION_IMMUNE:
                pass
            elif t == "CRACK":
                self.terrain[cy][cx] = "PIT"
            elif t == "MIMIC":
                self._clear_mimic(cx, cy)
            else:
                self.terrain[cy][cx] = "EMPTY"

        for cy in range(GRID_HEIGHT):
            for cx in range(GRID_WIDTH):
                if self.occupant[cy][cx] == "BOX" and self.terrain[cy][cx] == "PIT":
                    self.occupant[cy][cx] = None
                    self.terrain[cy][cx] = "EMPTY"

        if self.hp > 0 and self.terrain[self.hy][self.hx] == "PIT":
            dmg = min(self.hp, 100)
            self.trap_damage += dmg
            self.hp -= 100

        if self.hp <= 0:
            self.status = "DEAD"

    def compute_firing_lasers_for_turn(self, target_turn: int):
        """Returns list of (lx, ly, dname, period, beam_cells_list, hit_tnt_or_None)."""
        fire_red = (target_turn % 3 == 0)
        fire_blue = (target_turn % 4 == 0)
        if not fire_red and not fire_blue:
            return []
        lasers = []
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                t = self.terrain[y][x]
                period = None
                dname = None
                if fire_red and t in LASER_RED_DIR:
                    period = 3
                    dname = LASER_RED_DIR[t]
                elif fire_blue and t in LASER_BLUE_DIR:
                    period = 4
                    dname = LASER_BLUE_DIR[t]
                if period is not None:
                    dx, dy = DIRECTIONS[dname]
                    beam = []
                    hit_tnt = None
                    for dist in range(1, 11):
                        nx, ny = x + dist * dx, y + dist * dy
                        if not in_bounds(nx, ny) or self.is_high_wall(nx, ny) or self.occupant[ny][nx] == "BOX":
                            break
                        if self.occupant[ny][nx] == "TNT":
                            hit_tnt = (nx, ny)
                            break
                        beam.append((nx, ny))
                    lasers.append((x, y, dname, period, beam, hit_tnt))
        return lasers

    def step(self, action: str):
        if self.status != "ALIVE":
            return
        if action not in VALID_ACTIONS:
            action = "WAIT"

        self.turn += 1
        self.exposed_cells = {(self.hx, self.hy)}
        tnt_armed = set()

        # Phase A & B
        if action == "WAIT":
            pass
        elif action == "BOMB":
            if self.bombs_inv > 0 and not any(b["x"] == self.hx and b["y"] == self.hy for b in self.bombs):
                self.bombs_inv -= 1
                self.bombs.append({"id": self.next_bomb_id, "x": self.hx, "y": self.hy, "timer": 3})
                self.next_bomb_id += 1
        elif action.startswith("MOVE_"):
            dname = action[5:]
            dx, dy = DIRECTIONS[dname]
            p1x, p1y = self.hx + dx, self.hy + dy
            if not self.is_high_wall(p1x, p1y) and not self.blocks_oneway(p1x, p1y, dname) and self.occupant[p1y][p1x] != "TNT":
                if self.occupant[p1y][p1x] == "BOX":
                    p2x, p2y = self.hx + 2 * dx, self.hy + 2 * dy
                    if self._can_box_enter(p2x, p2y, dname):
                        box_ctx = {"steps_taken": 0, "portal_count": 0, "tnt_armed": tnt_armed}
                        self._displace("BOX", (p1x, p1y), (p2x, p2y), dname, box_ctx, False)
                        if self.status == "ALIVE" and self._can_hero_enter(p1x, p1y, dname):
                            hero_ctx = {"steps_taken": 0, "portal_count": 0, "tnt_armed": tnt_armed}
                            self._displace("HERO", (self.hx, self.hy), (p1x, p1y), dname, hero_ctx, False)
                else:
                    hero_ctx = {"steps_taken": 0, "portal_count": 0, "tnt_armed": tnt_armed}
                    self._displace("HERO", (self.hx, self.hy), (p1x, p1y), dname, hero_ctx, False)
        elif action.startswith("JUMP_"):
            if self.jumps > 0:
                self.jumps -= 1
                dname = action[5:]
                dx, dy = DIRECTIONS[dname]
                p1x, p1y = self.hx + dx, self.hy + dy
                p2x, p2y = self.hx + 2 * dx, self.hy + 2 * dy
                if (
                    not self.is_high_wall(p1x, p1y)
                    and not self.blocks_oneway(p1x, p1y, dname)
                    and in_bounds(p2x, p2y)
                    and self._can_hero_enter(p2x, p2y, dname)
                ):
                    hero_ctx = {"steps_taken": 0, "portal_count": 0, "tnt_armed": tnt_armed}
                    self._displace("HERO", (self.hx, self.hy), (p2x, p2y), dname, hero_ctx, False)
        elif action.startswith("THROW_"):
            if self.throws > 0:
                self.throws -= 1
                dname = action[6:]
                sx, sy = self.hx, self.hy
                range_left = 6
                stone_portals = 0
                shattered = False
                while range_left > 0:
                    dx, dy = DIRECTIONS[dname]
                    sx, sy = sx + dx, sy + dy
                    range_left -= 1
                    if not in_bounds(sx, sy) or self.is_high_wall(sx, sy) or self.occupant[sy][sx] == "BOX":
                        shattered = True
                        break
                    if self.occupant[sy][sx] == "TNT":
                        tnt_armed.add((sx, sy))
                        shattered = True
                        break
                    t = self.terrain[sy][sx]
                    if t == "SWITCH":
                        self.gates_flipped = not self.gates_flipped
                        shattered = True
                        break
                    if t == "MIMIC":
                        self._clear_mimic(sx, sy)
                        shattered = True
                        break
                    if t in MIRROR_MAP:
                        dname = MIRROR_MAP[t][dname]
                    elif t in PORTAL_PAIR_TILE and stone_portals < 2:
                        p_pair = self._find_portal_pair(t)
                        if p_pair is not None and self.occupant[p_pair[1]][p_pair[0]] not in ("BOX", "TNT"):
                            sx, sy = p_pair
                            stone_portals += 1
                            if stone_portals == 2:
                                shattered = True
                                break
                if not shattered and range_left == 0 and self.terrain[sy][sx] in ("ICE", *MIRROR_MAP.keys()):
                    for _ in range(32):
                        dx, dy = DIRECTIONS[dname]
                        sx, sy = sx + dx, sy + dy
                        if not in_bounds(sx, sy) or self.is_high_wall(sx, sy) or self.occupant[sy][sx] == "BOX":
                            break
                        if self.occupant[sy][sx] == "TNT":
                            tnt_armed.add((sx, sy))
                            break
                        t = self.terrain[sy][sx]
                        if t == "SWITCH":
                            self.gates_flipped = not self.gates_flipped
                            break
                        if t == "MIMIC":
                            self._clear_mimic(sx, sy)
                            break
                        if t in MIRROR_MAP:
                            dname = MIRROR_MAP[t][dname]
                        elif t == "ICE":
                            continue
                        elif t in PORTAL_PAIR_TILE and stone_portals < 2:
                            p_pair = self._find_portal_pair(t)
                            if p_pair is not None and self.occupant[p_pair[1]][p_pair[0]] not in ("BOX", "TNT"):
                                sx, sy = p_pair
                                stone_portals += 1
                                if stone_portals == 2:
                                    break
                            else:
                                break
                        else:
                            # ONEWAY_* and all other terrains immediately stop ground slide!
                            break

        if self.status in ("DEAD", "CLEARED"):
            return

        # Phase C
        for b in self.bombs:
            b["timer"] -= 1
        due_bombs = [b for b in self.bombs if b["timer"] == 0]
        if due_bombs or tnt_armed:
            self._resolve_explosions(due_bombs, tnt_armed)
            if self.status == "DEAD":
                return

        # Phase D: Dual-frequency lasers (turn % 3 == 0 or turn % 4 == 0)
        if self.turn % 3 == 0 or self.turn % 4 == 0:
            lasers = self.compute_firing_lasers_for_turn(self.turn)
            m = 0
            laser_tnt_armed = set()
            for _, _, _, _, beam, hit_tnt in lasers:
                if hit_tnt is not None:
                    laser_tnt_armed.add(hit_tnt)
                if any(cell in self.exposed_cells for cell in beam):
                    m += 1
            if m > 0:
                dmg = min(self.hp, 50 * m)
                self.trap_damage += dmg
                self.hp -= 50 * m
                if self.hp <= 0:
                    self.status = "DEAD"
                    return
            if laser_tnt_armed:
                self._resolve_explosions([], laser_tnt_armed)
                if self.status == "DEAD":
                    return

        if self.turn >= MAX_TURNS and self.status == "ALIVE":
            self.status = "TIMEOUT"

    def get_observation(self) -> dict:
        next_turn = self.turn + 1
        vis = [[True] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        obs_terrain = [
            ["CHEST" if t in ("HEAL", "MIMIC") else t for t in row]
            for row in self.terrain
        ]
        obs_occ = [row[:] for row in self.occupant]
        obs_clues = [row[:] for row in self.clues]
        obs_bombs = [{"x": b["x"], "y": b["y"], "timer": b["timer"]} for b in self.bombs]

        warnings = []
        if next_turn % 3 == 0 or next_turn % 4 == 0:
            for lx, ly, dname, period, beam, _ in self.compute_firing_lasers_for_turn(next_turn):
                for bx, by in beam:
                    warnings.append({
                        "x": bx, "y": by, "dir": dname,
                        "period": period, "cannon": [lx, ly],
                    })
            warnings.sort(key=lambda w: (w["y"], w["x"], w["dir"], w["period"], w["cannon"]))

        return {
            "turn": next_turn,
            "turns_left": MAX_TURNS - self.turn,
            "mode": "FULL",
            "hero": {
                "x": self.hx,
                "y": self.hy,
                "hp": self.hp,
                "keys": [self.has_k1, self.has_k2],
                "jumps": self.jumps,
                "throws": self.throws,
                "bombs": self.bombs_inv,
            },
            "gates_flipped": self.gates_flipped,
            "plates_active": self.is_plates_active(),
            "targets": copy.deepcopy(self.targets),
            "visible_mask": vis,
            "terrain": obs_terrain,
            "occupant": obs_occ,
            "bombs": obs_bombs,
            "clues": obs_clues,
            "laser_warnings": warnings,
        }

    def compute_scores(self):
        g = (MAX_BUDGET - self.spent_gold) / MAX_BUDGET
        D = min(100.0, self.trap_damage)
        k = int(self.has_k1) + int(self.has_k2)
        r = max(0.0, (self.stage_d0 - self.stage_dmin) / max(1, self.stage_d0))
        P = min(2.999999, k + r)
        if self.status == "CLEARED":
            hero_score = 600.0 + 1.5 * self.hp + 150.0 * (240 - self.turn) / 239.0 + 100.0 * g
            demon_score = min(320.0, 1.7 * D + 150.0 * (self.turn - 1) / 239.0)
        elif self.status == "DEAD":
            hero_score = 200.0 * P
            demon_score = 500.0 + 50.0 * (3.0 - P) + D + 250.0 * g
        else:
            hero_score = 200.0 * P
            demon_score = 320.0 + 50.0 * (3.0 - P) + D + 125.0 * g
        return hero_score, demon_score


def verify_spawn_4_turn_fairness(decoded: dict):
    """
    v2.2 Spawn 4-Turn Fairness Rule:
    At least 2 distinct Turn-1 end coordinates (hx, hy) with 0 trap damage alive/cleared,
    each having at least one Turn 2->3->4 action sequence with 0 trap damage surviving Turn 4.
    """
    base = DungeonEngineV22(decoded)
    t1_by_pos = {}
    for act1 in VALID_ACTIONS:
        e1 = base.clone()
        e1.step(act1)
        if e1.status in ("ALIVE", "CLEARED") and e1.trap_damage == 0.0 and e1.hp == 100:
            t1_by_pos.setdefault((e1.hx, e1.hy), []).append(e1)

    safe_t1_coords = 0
    for pos1, engines1 in t1_by_pos.items():
        survived = False
        q = collections.deque(engines1)
        seen = set()
        while q and not survived:
            cur = q.popleft()
            if cur.status == "CLEARED" or cur.turn >= 4:
                survived = True
                break
            for act in VALID_ACTIONS:
                nxt = cur.clone()
                nxt.step(act)
                if nxt.status in ("ALIVE", "CLEARED") and nxt.trap_damage == 0.0 and nxt.hp == 100:
                    if nxt.status == "CLEARED" or nxt.turn >= 4:
                        survived = True
                        break
                    sig = (nxt.turn, nxt.hx, nxt.hy, nxt.gates_flipped, nxt.jumps, nxt.throws, nxt.bombs_inv)
                    if sig not in seen:
                        seen.add(sig)
                        q.append(nxt)
        if survived:
            safe_t1_coords += 1
            if safe_t1_coords >= 2:
                return True, "OK"

    return False, f"Spawn 4-turn fairness failed: only {safe_t1_coords} safe Turn-1 coords (< 2)"


def make_blank_grid_v22():
    grid = [
        ["T_W" if is_outer_frame(x, y) else "EMPTY" for x in range(GRID_WIDTH)]
        for y in range(GRID_HEIGHT)
    ]
    grid[5][20] = "K1"
    grid[20][20] = "K2"
    grid[13][35] = "V"
    return grid


def run_golden_vectors_v22(gv_path: str):
    with open(gv_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for vec in data["vectors"]:
        vid = vec["id"]
        exp = vec.get("expected", {})

        if vid == "GV22_01_V22_BUDGET_AND_PLATE_PGATE_SCHEMA":
            g = [["T_W" if is_outer_frame(x, y) else "EMPTY" for x in range(GRID_WIDTH)] for y in range(GRID_HEIGHT)]
            for item in vec["placed_inner_tiles"]:
                g[item["y"]][item["x"]] = item["tile"]
            ok, msg, dec = validate_and_decode_grid_v22(g)
            assert ok == exp["valid"], f"{vid}: {msg}"
            assert dec["spent_gold"] == exp["spent_gold"]
            assert MAX_BUDGET - dec["spent_gold"] == exp["vault_gold"]
            eng = DungeonEngineV22(dec)
            assert eng.is_plates_active() == exp["initial_plates_active"]
            print(f"[PASS] {vid}")

        elif vid == "GV22_02_PLATE_BOX_ONLY_TRIGGER":
            g = make_blank_grid_v22()
            g[13][5] = "PLATE"
            g[13][34] = "P_GATE"
            g[13][7] = "BOX"
            ok, msg, dec = validate_and_decode_grid_v22(g)
            assert ok, msg
            eng = DungeonEngineV22(dec)
            eng.hx, eng.hy = 4, 13
            eng.step("MOVE_R")
            assert eng.is_plates_active() is False
            assert eng.is_high_wall(34, 13) is True
            eng.hx, eng.hy = 8, 13
            eng.step("MOVE_L")
            eng.step("MOVE_L")
            assert eng.is_plates_active() is True
            assert eng.is_high_wall(34, 13) is False
            print(f"[PASS] {vid}")

        elif vid == "GV22_03_LCM12_RED_AND_BLUE_LASER_INSTANT_KILL":
            g = make_blank_grid_v22()
            g[8][15] = "LASER_D"
            g[10][12] = "LASER2_R"
            ok, msg, dec = validate_and_decode_grid_v22(g)
            assert ok, msg
            eng = DungeonEngineV22(dec)
            eng.turn = 11
            eng.hx, eng.hy = 15, 10
            obs = eng.get_observation()
            periods = [w["period"] for w in obs["laser_warnings"] if (w["x"], w["y"]) == (15, 10)]
            assert periods == exp["warning_periods_at_15_10"], f"{vid}: {periods}"
            eng.step("WAIT")
            assert eng.hp == exp["hero_hp_after"]
            assert eng.status == exp["status"]
            print(f"[PASS] {vid}")

        elif vid == "GV22_04_ONEWAY_REVERSE_PUSH_AND_MIRROR_NEWDIR":
            g = make_blank_grid_v22()
            ok, msg, dec = validate_and_decode_grid_v22(g)
            eng = DungeonEngineV22(dec)
            eng.terrain[13][5] = "CRACK"
            eng.terrain[13][6] = "ONEWAY_L"
            eng.occupant[13][6] = "BOX"
            eng.hx, eng.hy = 5, 13
            eng.step("MOVE_R")
            assert [eng.hx, eng.hy] == exp["case_a_hero_pos"]
            assert eng.occupant[13][6] == "BOX"
            assert (eng.terrain[13][5] == "CRACK") == exp["case_a_crack_intact"]

            eng2 = DungeonEngineV22(dec)
            eng2.terrain[10][10] = "MIRROR_NE"
            eng2.terrain[9][10] = "ONEWAY_R"
            eng2.hx, eng2.hy = 9, 10
            eng2.step("MOVE_R")
            assert [eng2.hx, eng2.hy] == exp["case_b_hero_pos"]
            print(f"[PASS] {vid}")

        elif vid == "GV22_05_SPRING_AND_JUMP_ONEWAY_INTERACTION":
            g = make_blank_grid_v22()
            ok, msg, dec = validate_and_decode_grid_v22(g)
            eng = DungeonEngineV22(dec)
            eng.terrain[10][10] = "SPRING_R"
            eng.terrain[10][12] = "ONEWAY_L"
            eng.hx, eng.hy = 9, 10
            eng.step("MOVE_R")
            assert [eng.hx, eng.hy] == exp["spring_land_pos"]

            eng.terrain[14][6] = "ONEWAY_L"
            eng.hx, eng.hy = 5, 14
            eng.step("JUMP_R")
            assert [eng.hx, eng.hy] == exp["jump_failed_pos"]
            assert eng.jumps == exp["jumps_left"]
            print(f"[PASS] {vid}")

        elif vid == "GV22_06_THROW_AIR_PASS_VS_GROUND_STOP_ON_ONEWAY":
            g = make_blank_grid_v22()
            ok, msg, dec = validate_and_decode_grid_v22(g)
            eng = DungeonEngineV22(dec)
            eng.terrain[10][6] = "ONEWAY_L"
            eng.terrain[10][7] = "SWITCH"
            eng.hx, eng.hy = 5, 10
            eng.step("THROW_R")
            assert eng.gates_flipped == exp["air_throw_gates_flipped"]

            eng2 = DungeonEngineV22(dec)
            eng2.terrain[15][11] = "ICE"
            eng2.terrain[15][12] = "ONEWAY_L"
            eng2.terrain[15][13] = "SWITCH"
            eng2.hx, eng2.hy = 5, 15
            eng2.step("THROW_R")
            assert eng2.gates_flipped == exp["ground_slide_gates_flipped"]
            print(f"[PASS] {vid}")

        elif vid == "GV22_07_PHASE_C_BOX_DESTRUCTION_CLOSES_PGATE_BEFORE_PHASE_D":
            g = make_blank_grid_v22()
            g[10][10] = "PLATE"
            g[10][12] = "P_GATE"
            g[10][15] = "LASER_L"
            g[9][10] = "BOX"
            ok, msg, dec = validate_and_decode_grid_v22(g)
            assert ok, msg
            eng = DungeonEngineV22(dec)
            eng.occupant[9][10] = None
            eng.occupant[10][10] = "BOX"
            eng.bombs.append({"id": 1, "x": 10, "y": 9, "timer": 1})
            eng.turn = 2
            eng.hx, eng.hy = 7, 10
            assert eng.is_plates_active() is True
            eng.step("WAIT")
            assert eng.is_plates_active() == exp["plates_active_after"]
            assert eng.hp == exp["hero_hp_after"]
            print(f"[PASS] {vid}")

        elif vid == "GV22_08_SCORING_ZERO_SUM_AND_2WIDE_PIT_BRIDGE":
            g = make_blank_grid_v22()
            for y in range(11, 16):
                for x in range(30, 38):
                    g[y][x] = "T_W"
            g[13][29] = "BOX"
            g[13][30] = "EMPTY"
            g[13][31] = "EMPTY"
            g[13][32] = "PIT"
            g[13][33] = "PIT"
            g[13][34] = "EMPTY"
            g[13][35] = "V"
            ok, msg, dec = validate_and_decode_grid_v22(g)
            assert ok == exp["valid"], msg
            eng = DungeonEngineV22(dec)
            eng.status = "CLEARED"
            eng.turn = 240
            eng.trap_damage = 100.0
            eng.hp = 1
            eng.has_k1 = eng.has_k2 = True
            _, d_score = eng.compute_scores()
            assert abs(d_score - exp["cleared_max_demon_score"]) < 1e-6
            assert MAX_AUTHOR_STEPS == exp["max_author_steps"]
            print(f"[PASS] {vid}")


if __name__ == "__main__":
    run_golden_vectors_v22("golden_vectors_v22.json")
    print("ALL 8 v2.2 GOLDEN VECTORS PASSED PERFECTLY!")
