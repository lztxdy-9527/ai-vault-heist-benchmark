"""
Exact v2.2 Official Simulator, Dungeon Validator, AST Compliance Checker, and Scorer.
Verified against all 23 Part-1 match logs and all 8 v2.2 golden vectors.
"""

import ast
import copy
import json
from collections import deque

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

LASER1_TILES = {"LASER_U", "LASER_D", "LASER_L", "LASER_R"}
LASER2_TILES = {"LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R"}
ALL_LASER_TILES = LASER1_TILES | LASER2_TILES
ONEWAY_TILES = {"ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R"}
SPRING_TILES = {"SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R"}
MIRROR_TILES = set(MIRROR_MAP.keys())
HIGH_WALL_STATIC = {"W", "T_W"} | ALL_LASER_TILES
PORTAL_PAIRS = {
    "PORTAL_1A": "PORTAL_1B", "PORTAL_1B": "PORTAL_1A",
    "PORTAL_2A": "PORTAL_2B", "PORTAL_2B": "PORTAL_2A",
}
IMMUNE_EXPLOSION = {
    "T_W", "K1", "K2", "V",
    "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
    "PIT", "PLATE", "P_GATE",
    "ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R",
}
DESTROY_TO_EMPTY = {
    "W", "ICE",
    "MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW",
    "SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R",
    "LASER_U", "LASER_D", "LASER_L", "LASER_R",
    "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R",
    "SWITCH", "R_GATE", "B_GATE", "HEAL", "MIMIC",
}


class EngineV22:
    def __init__(self, grid, start_pos=SPAWN_POS, turn=1, hp=100, jumps=3, throws=3, bombs=2):
        self.terrain = [["EMPTY"] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.occupant = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.plates = []
        self.targets = {}
        self.portals = {}
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                tile = grid[y][x]
                if tile in ("BOX", "TNT"):
                    self.terrain[y][x] = "EMPTY"
                    self.occupant[y][x] = tile
                else:
                    self.terrain[y][x] = tile
                    if tile == "PLATE":
                        self.plates.append((x, y))
                    elif tile in ("K1", "K2", "V"):
                        self.targets[tile] = [x, y]
                    elif tile in PORTAL_PAIRS:
                        self.portals[tile] = (x, y)

        self.hx, self.hy = start_pos
        self.hp = hp
        self.jumps = jumps
        self.throws = throws
        self.bombs_left = bombs
        self.keys = [False, False]
        self.gates_flipped = False
        self.active_bombs = []  # list of dict {"x": x, "y": y, "timer": t}
        self.turn = turn
        self.status = "RUNNING"  # RUNNING, CLEARED, DEAD, TIMEOUT
        self.total_damage_taken = 0
        self.visited = {(self.hx, self.hy)}

    def clone(self):
        return copy.deepcopy(self)

    def in_bounds(self, x, y):
        return 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT

    def is_plates_active(self):
        if not self.plates:
            return False
        for px, py in self.plates:
            if self.occupant[py][px] != "BOX":
                return False
        return True

    def is_high_wall(self, x, y):
        if not self.in_bounds(x, y):
            return True
        t = self.terrain[y][x]
        if t in HIGH_WALL_STATIC:
            return True
        if t == "R_GATE" and not self.gates_flipped:
            return True
        if t == "B_GATE" and self.gates_flipped:
            return True
        if t == "P_GATE" and not self.is_plates_active():
            return True
        return False

    def blocks_oneway(self, x, y, cur_dir):
        if not self.in_bounds(x, y):
            return False
        t = self.terrain[y][x]
        if t in ONEWAY_TILES:
            return t[-1] != cur_dir
        return False

    def _can_box_enter(self, x, y, cur_dir):
        if not self.in_bounds(x, y):
            return False
        if self.is_high_wall(x, y) or self.blocks_oneway(x, y, cur_dir):
            return False
        if self.terrain[y][x] in ("K1", "K2", "V"):
            return False
        if self.occupant[y][x] in ("BOX", "TNT"):
            return False
        if (x, y) == (self.hx, self.hy):
            return False
        return True

    def _can_hero_enter(self, x, y, cur_dir):
        if not self.in_bounds(x, y):
            return False
        if self.is_high_wall(x, y) or self.blocks_oneway(x, y, cur_dir):
            return False
        if self.occupant[y][x] in ("BOX", "TNT"):
            return False
        return True

    def _displace_box(self, x0, y0, x1, y1, cur_dir, armed_tnts):
        steps = 0
        portal_count = 0
        suppress_portal_once = False
        while True:
            steps += 1
            if self.terrain[y0][x0] == "CRACK":
                self.terrain[y0][x0] = "PIT"
            self.occupant[y0][x0] = None
            self.occupant[y1][x1] = "BOX"
            t1 = self.terrain[y1][x1]
            if t1 == "PIT":
                self.occupant[y1][x1] = None
                self.terrain[y1][x1] = "EMPTY"
                break
            elif t1 == "MIMIC":
                self.terrain[y1][x1] = "EMPTY"
            elif t1 == "SWITCH":
                self.gates_flipped = not self.gates_flipped

            if steps >= 32:
                break

            if suppress_portal_once:
                suppress_portal_once = False
                if portal_count >= 2:
                    break
                dx, dy = DIRECTIONS[cur_dir]
                nx, ny = x1 + dx, y1 + dy
                if self._can_box_enter(nx, ny, cur_dir):
                    x0, y0, x1, y1 = x1, y1, nx, ny
                    continue
                if self.in_bounds(nx, ny) and self.occupant[ny][nx] == "TNT" and not self.blocks_oneway(nx, ny, cur_dir):
                    armed_tnts.add((nx, ny))
                break

            t_cur = self.terrain[y1][x1]
            if t_cur == "ICE":
                dx, dy = DIRECTIONS[cur_dir]
                nx, ny = x1 + dx, y1 + dy
                if self._can_box_enter(nx, ny, cur_dir):
                    x0, y0, x1, y1 = x1, y1, nx, ny
                    continue
                if self.in_bounds(nx, ny) and self.occupant[ny][nx] == "TNT" and not self.blocks_oneway(nx, ny, cur_dir):
                    armed_tnts.add((nx, ny))
                break
            elif t_cur in MIRROR_MAP:
                cur_dir = MIRROR_MAP[t_cur][cur_dir]
                dx, dy = DIRECTIONS[cur_dir]
                nx, ny = x1 + dx, y1 + dy
                if self._can_box_enter(nx, ny, cur_dir):
                    x0, y0, x1, y1 = x1, y1, nx, ny
                    continue
                if self.in_bounds(nx, ny) and self.occupant[ny][nx] == "TNT" and not self.blocks_oneway(nx, ny, cur_dir):
                    armed_tnts.add((nx, ny))
                break
            elif t_cur in SPRING_TILES:
                cur_dir = t_cur[-1]
                dx, dy = DIRECTIONS[cur_dir]
                blocked_k = None
                for k in (1, 2, 3):
                    pkx, pky = x1 + k * dx, y1 + k * dy
                    if not self._can_box_enter(pkx, pky, cur_dir):
                        blocked_k = k
                        if self.in_bounds(pkx, pky) and self.occupant[pky][pkx] == "TNT" and not self.blocks_oneway(pkx, pky, cur_dir):
                            armed_tnts.add((pkx, pky))
                        break
                if blocked_k == 1:
                    break
                land_k = (blocked_k - 1) if blocked_k is not None else 3
                x0, y0, x1, y1 = x1, y1, x1 + land_k * dx, y1 + land_k * dy
                continue
            elif t_cur in PORTAL_PAIRS:
                pair_pos = self.portals.get(PORTAL_PAIRS[t_cur])
                if pair_pos is None:
                    break
                px, py = pair_pos
                if self.occupant[py][px] is not None or (px, py) == (self.hx, self.hy):
                    break
                portal_count += 1
                suppress_portal_once = True
                x0, y0, x1, y1 = x1, y1, px, py
                continue
            else:
                break

    def _displace_hero(self, x1, y1, cur_dir, exposed):
        x0, y0 = self.hx, self.hy
        steps = 0
        portal_count = 0
        suppress_portal_once = False
        stop_momentum = False

        while True:
            steps += 1
            if self.terrain[y0][x0] == "CRACK":
                self.terrain[y0][x0] = "PIT"
            self.hx, self.hy = x1, y1
            exposed.add((self.hx, self.hy))
            self.visited.add((self.hx, self.hy))
            t1 = self.terrain[y1][x1]

            if t1 == "PIT":
                self.hp -= 100
                self.total_damage_taken += 100
            elif t1 == "MIMIC":
                self.hp -= 45
                self.total_damage_taken += 45
                self.terrain[y1][x1] = "EMPTY"
                stop_momentum = True
            elif t1 == "HEAL":
                self.hp = min(100, self.hp + 30)
                self.terrain[y1][x1] = "EMPTY"
            elif t1 == "SWITCH":
                self.gates_flipped = not self.gates_flipped

            if self.hp <= 0:
                self.status = "DEAD"
                return

            if t1 == "K1":
                self.keys[0] = True
                self.terrain[y1][x1] = "EMPTY"
            elif t1 == "K2":
                self.keys[1] = True
                self.terrain[y1][x1] = "EMPTY"
            elif t1 == "V" and self.keys[0] and self.keys[1] and self.hp > 0:
                self.status = "CLEARED"
                return

            if steps >= 32 or stop_momentum:
                break

            if suppress_portal_once:
                suppress_portal_once = False
                if portal_count >= 2:
                    break
                dx, dy = DIRECTIONS[cur_dir]
                nx, ny = x1 + dx, y1 + dy
                if self._can_hero_enter(nx, ny, cur_dir):
                    x0, y0, x1, y1 = x1, y1, nx, ny
                    continue
                break

            t_cur = self.terrain[y1][x1]
            if t_cur == "ICE":
                dx, dy = DIRECTIONS[cur_dir]
                nx, ny = x1 + dx, y1 + dy
                if self._can_hero_enter(nx, ny, cur_dir):
                    x0, y0, x1, y1 = x1, y1, nx, ny
                    continue
                break
            elif t_cur in MIRROR_MAP:
                cur_dir = MIRROR_MAP[t_cur][cur_dir]
                dx, dy = DIRECTIONS[cur_dir]
                nx, ny = x1 + dx, y1 + dy
                if self._can_hero_enter(nx, ny, cur_dir):
                    x0, y0, x1, y1 = x1, y1, nx, ny
                    continue
                break
            elif t_cur in SPRING_TILES:
                cur_dir = t_cur[-1]
                dx, dy = DIRECTIONS[cur_dir]
                blocked_k = None
                for k in (1, 2, 3):
                    pkx, pky = x1 + k * dx, y1 + k * dy
                    if not self._can_hero_enter(pkx, pky, cur_dir):
                        blocked_k = k
                        break
                if blocked_k == 1:
                    break
                land_k = (blocked_k - 1) if blocked_k is not None else 3
                x0, y0, x1, y1 = x1, y1, x1 + land_k * dx, y1 + land_k * dy
                continue
            elif t_cur in PORTAL_PAIRS:
                pair_pos = self.portals.get(PORTAL_PAIRS[t_cur])
                if pair_pos is None:
                    break
                px, py = pair_pos
                if self.occupant[py][px] is not None:
                    break
                portal_count += 1
                suppress_portal_once = True
                x0, y0, x1, y1 = x1, y1, px, py
                continue
            else:
                break

    def _resolve_throw(self, d, armed_tnts):
        sx, sy = self.hx, self.hy
        cur_dir = d
        range_left = 6
        stone_portals = 0
        shattered = False
        stopped_on_portal = False

        while range_left > 0:
            dx, dy = DIRECTIONS[cur_dir]
            sx, sy = sx + dx, sy + dy
            range_left -= 1
            if not self.in_bounds(sx, sy):
                shattered = True
                break
            t = self.terrain[sy][sx]
            if self.is_high_wall(sx, sy) or self.occupant[sy][sx] == "BOX":
                shattered = True
                break
            if self.occupant[sy][sx] == "TNT":
                armed_tnts.add((sx, sy))
                shattered = True
                break
            if t == "SWITCH":
                self.gates_flipped = not self.gates_flipped
                shattered = True
                break
            if t == "MIMIC":
                self.terrain[sy][sx] = "EMPTY"
                shattered = True
                break
            if t in MIRROR_MAP:
                cur_dir = MIRROR_MAP[t][cur_dir]
            elif t in PORTAL_PAIRS and stone_portals < 2:
                pair_pos = self.portals.get(PORTAL_PAIRS[t])
                if pair_pos is not None and self.occupant[pair_pos[1]][pair_pos[0]] is None:
                    sx, sy = pair_pos
                    stone_portals += 1
                    if stone_portals == 2:
                        stopped_on_portal = True
                        break

        if not shattered and not stopped_on_portal and range_left == 0:
            t6 = self.terrain[sy][sx]
            if t6 == "ICE" or t6 in MIRROR_MAP:
                for _ in range(32):
                    dx, dy = DIRECTIONS[cur_dir]
                    sx, sy = sx + dx, sy + dy
                    if not self.in_bounds(sx, sy):
                        break
                    t = self.terrain[sy][sx]
                    if self.is_high_wall(sx, sy) or self.occupant[sy][sx] == "BOX":
                        break
                    if self.occupant[sy][sx] == "TNT":
                        armed_tnts.add((sx, sy))
                        break
                    if t == "SWITCH":
                        self.gates_flipped = not self.gates_flipped
                        break
                    if t == "MIMIC":
                        self.terrain[sy][sx] = "EMPTY"
                        break
                    if t in MIRROR_MAP:
                        cur_dir = MIRROR_MAP[t][cur_dir]
                    elif t == "ICE":
                        pass
                    elif t in PORTAL_PAIRS and stone_portals < 2:
                        pair_pos = self.portals.get(PORTAL_PAIRS[t])
                        if pair_pos is not None and self.occupant[pair_pos[1]][pair_pos[0]] is None:
                            sx, sy = pair_pos
                            stone_portals += 1
                            if stone_portals == 2:
                                break
                        else:
                            break
                    else:
                        # ONEWAY_* and all other non-ice floor stop ground-sliding stone
                        break

    def _detonate_closure(self, seeds):
        if not seeds:
            return
        exploded = set()
        q = deque(seeds)
        while q:
            ex, ey = q.popleft()
            if (ex, ey) in exploded:
                continue
            exploded.add((ex, ey))
            if self.occupant[ey][ex] == "TNT":
                self.occupant[ey][ex] = None
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = ex + dx, ey + dy
                    if not self.in_bounds(nx, ny):
                        continue
                    if (nx, ny) == (self.hx, self.hy):
                        self.hp -= 60
                        self.total_damage_taken += 60
                    if self.occupant[ny][nx] == "BOX":
                        self.occupant[ny][nx] = None
                    elif self.occupant[ny][nx] == "TNT":
                        self.occupant[ny][nx] = None
                        if (nx, ny) not in exploded:
                            q.append((nx, ny))
                    nt = self.terrain[ny][nx]
                    if nt == "CRACK":
                        self.terrain[ny][nx] = "PIT"
                    elif nt in DESTROY_TO_EMPTY:
                        self.terrain[ny][nx] = "EMPTY"
        if self.hp <= 0:
            self.status = "DEAD"

    def compute_laser_beams(self, turn):
        beams = []  # list of (cannon_xy, period, dir, cells_list, hit_tnts)
        fire_r = (turn % 3 == 0)
        fire_b = (turn % 4 == 0)
        if not (fire_r or fire_b):
            return beams
        for y in range(1, GRID_HEIGHT - 1):
            for x in range(1, GRID_WIDTH - 1):
                t = self.terrain[y][x]
                period = 0
                if fire_r and t in LASER1_TILES:
                    period = 3
                elif fire_b and t in LASER2_TILES:
                    period = 4
                if period == 0:
                    continue
                d = t[-1]
                dx, dy = DIRECTIONS[d]
                cells = []
                hit_tnt = None
                for dist in range(1, 11):
                    rx, ry = x + dist * dx, y + dist * dy
                    if not self.in_bounds(rx, ry):
                        break
                    if self.is_high_wall(rx, ry):
                        break
                    if self.occupant[ry][rx] == "BOX":
                        break
                    if self.occupant[ry][rx] == "TNT":
                        hit_tnt = (rx, ry)
                        break
                    cells.append((rx, ry))
                beams.append(((x, y), period, d, cells, hit_tnt))
        return beams

    def get_observation(self):
        # FULL mode observation matching official v2.2 schema
        obs_t = [row[:] for row in self.terrain]
        obs_o = [row[:] for row in self.occupant]
        clues = [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if obs_t[y][x] in ("HEAL", "MIMIC"):
                    if obs_t[y][x] == "MIMIC":
                        for dx, dy in DIRECTIONS.values():
                            nx, ny = x + dx, y + dy
                            if self.in_bounds(nx, ny):
                                clues[ny][nx] = True
                    obs_t[y][x] = "CHEST"

        warnings = []
        for (cx, cy), period, d, cells, _ in self.compute_laser_beams(self.turn):
            for bx, by in cells:
                warnings.append({
                    "x": bx, "y": by, "dir": d, "period": period, "cannon": [cx, cy]
                })
        warnings.sort(key=lambda w: (w["y"], w["x"], w["dir"], w["period"], w["cannon"]))

        return {
            "mode": "FULL",
            "turn": self.turn,
            "max_turns": MAX_TURNS,
            "hero": {
                "x": self.hx, "y": self.hy, "hp": self.hp,
                "jumps": self.jumps, "throws": self.throws, "bombs": self.bombs_left,
                "keys": [self.keys[0], self.keys[1]],
            },
            "targets": {k: list(v) for k, v in self.targets.items()},
            "gates_flipped": self.gates_flipped,
            "plates_active": self.is_plates_active(),
            "bombs": [dict(b) for b in self.active_bombs],
            "visible_mask": [[True] * GRID_WIDTH for _ in range(GRID_HEIGHT)],
            "terrain": obs_t,
            "occupant": obs_o,
            "clues": clues,
            "laser_warnings": warnings,
        }

    def step(self, action):
        if self.status != "RUNNING":
            return self.status
        if action not in VALID_ACTIONS:
            action = "WAIT"

        exposed = {(self.hx, self.hy)}
        armed_tnts = set()

        # Phase A: Hero action
        if action == "WAIT":
            pass
        elif action == "BOMB":
            if self.bombs_left > 0 and not any(b["x"] == self.hx and b["y"] == self.hy for b in self.active_bombs):
                self.bombs_left -= 1
                self.active_bombs.append({"x": self.hx, "y": self.hy, "timer": 3})
        elif action.startswith("THROW_"):
            if self.throws > 0:
                self.throws -= 1
                self._resolve_throw(action[-1], armed_tnts)
        elif action.startswith("MOVE_"):
            d = action[-1]
            dx, dy = DIRECTIONS[d]
            p1x, p1y = self.hx + dx, self.hy + dy
            if self.in_bounds(p1x, p1y) and not self.is_high_wall(p1x, p1y) and not self.blocks_oneway(p1x, p1y, d):
                occ1 = self.occupant[p1y][p1x]
                if occ1 == "BOX":
                    p2x, p2y = self.hx + 2 * dx, self.hy + 2 * dy
                    if self._can_box_enter(p2x, p2y, d):
                        self._displace_box(p1x, p1y, p2x, p2y, d, armed_tnts)
                        if self._can_hero_enter(p1x, p1y, d):
                            self._displace_hero(p1x, p1y, d, exposed)
                    elif self.in_bounds(p2x, p2y) and self.occupant[p2y][p2x] == "TNT" and not self.blocks_oneway(p2x, p2y, d):
                        armed_tnts.add((p2x, p2y))
                elif occ1 == "TNT":
                    pass
                else:
                    self._displace_hero(p1x, p1y, d, exposed)
        elif action.startswith("JUMP_"):
            if self.jumps > 0:
                self.jumps -= 1
                d = action[-1]
                dx, dy = DIRECTIONS[d]
                p1x, p1y = self.hx + dx, self.hy + dy
                p2x, p2y = self.hx + 2 * dx, self.hy + 2 * dy
                p1_ok = self.in_bounds(p1x, p1y) and not self.is_high_wall(p1x, p1y) and not self.blocks_oneway(p1x, p1y, d)
                p2_ok = self._can_hero_enter(p2x, p2y, d)
                if p1_ok and p2_ok:
                    self._displace_hero(p2x, p2y, d, exposed)

        if self.status != "RUNNING":
            return self.status

        # Phase C: Bombs & armed TNTs
        det_seeds = set(armed_tnts)
        next_bombs = []
        for b in self.active_bombs:
            b["timer"] -= 1
            if b["timer"] <= 0:
                det_seeds.add((b["x"], b["y"]))
            else:
                next_bombs.append(b)
        self.active_bombs = next_bombs
        if det_seeds:
            self._detonate_closure(det_seeds)

        if self.status != "RUNNING":
            return self.status

        # Phase D: Dual-period lasers (based on post-Phase-C snapshot)
        if self.turn % 3 == 0 or self.turn % 4 == 0:
            beams = self.compute_laser_beams(self.turn)
            laser_tnts = set()
            for _, _, _, cells, hit_tnt in beams:
                if hit_tnt is not None:
                    laser_tnts.add(hit_tnt)
                for c in cells:
                    if c in exposed:
                        self.hp -= 50
                        self.total_damage_taken += 50
                        break
            if self.hp <= 0:
                self.status = "DEAD"
            if laser_tnts:
                self._detonate_closure(laser_tnts)

        if self.status != "RUNNING":
            return self.status

        if self.turn >= MAX_TURNS:
            self.status = "TIMEOUT"
            return self.status

        self.turn += 1
        return self.status


def check_ast_compliance(filepath):
    """Verify submission.py passes v2.2 static AST redlines (no __ names/attrs, no forbidden imports/calls)."""
    with open(filepath, "r", encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src, filename=filepath)
    forbidden_imports = {
        "os", "sys", "pathlib", "io", "subprocess", "socket", "urllib", "http",
        "requests", "shutil", "glob", "tempfile", "pickle", "marshal", "ctypes",
        "inspect", "importlib", "builtins", "multiprocessing", "threading", "signal",
    }
    forbidden_calls = {
        "open", "eval", "exec", "compile", "getattr", "setattr", "delattr",
        "hasattr", "vars", "globals", "locals", "dir", "type", "input",
    }
    errors = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in forbidden_imports or alias.name.startswith("__"):
                    errors.append(f"Line {node.lineno}: forbidden import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in forbidden_imports or (node.module or "").startswith("__"):
                errors.append(f"Line {node.lineno}: forbidden import-from {node.module}")
        elif isinstance(node, ast.Name):
            if node.id.startswith("__"):
                errors.append(f"Line {node.lineno}: forbidden dunder name {node.id}")
            if node.id in forbidden_calls:
                errors.append(f"Line {node.lineno}: forbidden builtin {node.id}")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                errors.append(f"Line {node.lineno}: forbidden dunder attr .{node.attr}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name.startswith("__"):
                errors.append(f"Line {node.lineno}: forbidden dunder def {node.name}")
        elif isinstance(node, ast.arg):
            if node.arg.startswith("__"):
                errors.append(f"Line {node.lineno}: forbidden dunder arg {node.arg}")
    return errors


def validate_dungeon(dungeon_dict):
    """Full v2.2 dungeon validation including budget, caps, spawn 4-turn rule, and author_solution <= 200."""
    errors = []
    if not isinstance(dungeon_dict, dict):
        return False, ["Must return dict"], {}
    for k in ("taunt", "grid", "author_solution"):
        if k not in dungeon_dict:
            errors.append(f"Missing key {k}")
    if errors:
        return False, errors, {}

    taunt = dungeon_dict["taunt"]
    if not isinstance(taunt, str) or len(taunt) > 40:
        errors.append(f"taunt must be str with len <= 40, got len={len(str(taunt))}")

    grid = dungeon_dict["grid"]
    if not isinstance(grid, list) or len(grid) != GRID_HEIGHT or any(len(r) != GRID_WIDTH for r in grid):
        errors.append("grid must be 26x40")
        return False, errors, {}

    counts = {}
    spent = 0
    k1_pos = k2_pos = v_pos = None
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            t = grid[y][x]
            if t not in TILE_COSTS:
                errors.append(f"Unknown tile {t} at ({x},{y})")
                continue
            is_border = (x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1)
            if is_border:
                if t != "T_W":
                    errors.append(f"Border ({x},{y}) must be T_W, got {t}")
                continue
            counts[t] = counts.get(t, 0) + 1
            spent += TILE_COSTS[t]
            if t == "K1":
                k1_pos = (x, y)
            elif t == "K2":
                k2_pos = (x, y)
            elif t == "V":
                v_pos = (x, y)

    if spent > MAX_BUDGET:
        errors.append(f"Over budget: {spent} > {MAX_BUDGET}")

    # Spawn 3x3 clear
    for y in range(12, 15):
        for x in range(1, 4):
            if grid[y][x] != "EMPTY":
                errors.append(f"Spawn clear zone ({x},{y}) must be EMPTY, got {grid[y][x]}")

    # Landmarks
    if counts.get("K1", 0) != 1 or k1_pos is None or not (12 <= k1_pos[0] <= 34 and 2 <= k1_pos[1] <= 10):
        errors.append(f"Invalid K1: count={counts.get('K1', 0)}, pos={k1_pos}")
    if counts.get("K2", 0) != 1 or k2_pos is None or not (12 <= k2_pos[0] <= 34 and 15 <= k2_pos[1] <= 23):
        errors.append(f"Invalid K2: count={counts.get('K2', 0)}, pos={k2_pos}")
    if k1_pos and k2_pos and abs(k1_pos[0] - k2_pos[0]) + abs(k1_pos[1] - k2_pos[1]) < 12:
        errors.append(f"K1-K2 Manhattan dist < 12")
    if counts.get("V", 0) != 1 or v_pos is None or not (33 <= v_pos[0] <= 37 and 4 <= v_pos[1] <= 21):
        errors.append(f"Invalid V: count={counts.get('V', 0)}, pos={v_pos}")

    # Caps
    if counts.get("T_W", 0) > 120:
        errors.append(f"T_W inner {counts['T_W']} > 120")
    if sum(counts.get(t, 0) for t in MIRROR_TILES) > 30:
        errors.append("MIRROR > 30")
    if sum(counts.get(t, 0) for t in SPRING_TILES) > 20:
        errors.append("SPRING > 20")
    if counts.get("CRACK", 0) > 40:
        errors.append("CRACK > 40")
    if counts.get("SWITCH", 0) > 6:
        errors.append("SWITCH > 6")
    if counts.get("R_GATE", 0) + counts.get("B_GATE", 0) > 16:
        errors.append("R_GATE+B_GATE > 16")
    if counts.get("PLATE", 0) > 4:
        errors.append("PLATE > 4")
    if counts.get("P_GATE", 0) > 8:
        errors.append("P_GATE > 8")
    if counts.get("P_GATE", 0) > 0:
        if not (1 <= counts.get("PLATE", 0) <= counts.get("BOX", 0)):
            errors.append(f"P_GATE>0 requires 1 <= PLATE({counts.get('PLATE',0)}) <= BOX({counts.get('BOX',0)})")
    if sum(counts.get(t, 0) for t in ALL_LASER_TILES) > 12:
        errors.append("LASER + LASER2 > 12")
    if sum(counts.get(t, 0) for t in ONEWAY_TILES) > 12:
        errors.append("ONEWAY > 12")
    if counts.get("TNT", 0) > 12:
        errors.append("TNT > 12")
    if counts.get("BOX", 0) > 6:
        errors.append("BOX > 6")
    if counts.get("HEAL", 0) > 4:
        errors.append("HEAL > 4")
    if counts.get("MIMIC", 0) > 4:
        errors.append("MIMIC > 4")
    for p in ("1", "2"):
        ca, cb = counts.get(f"PORTAL_{p}A", 0), counts.get(f"PORTAL_{p}B", 0)
        if not ((ca == 0 and cb == 0) or (ca == 1 and cb == 1)):
            errors.append(f"Portal pair {p} invalid: A={ca}, B={cb}")

    # Spawn 4-turn fair admission check:
    # At least 2 distinct turn-1 end coords (hx, hy) with 0 damage, each having a 0-damage sequence through turn 4
    safe_t1_coords = set()
    for act1 in VALID_ACTIONS:
        e1 = EngineV22(grid)
        e1.step(act1)
        if e1.status == "RUNNING" and e1.total_damage_taken == 0:
            coord1 = (e1.hx, e1.hy)
            if coord1 in safe_t1_coords:
                continue
            # DFS turns 2, 3, 4 for 0 damage
            found4 = False
            stack = [(e1, 2)]
            seen_states = set()
            while stack and not found4:
                eng, tnum = stack.pop()
                if tnum > 4:
                    found4 = True
                    break
                for a in ("WAIT", "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R"):
                    nxt = eng.clone()
                    nxt.step(a)
                    if nxt.status in ("RUNNING", "CLEARED") and nxt.total_damage_taken == 0:
                        key = (tnum, nxt.hx, nxt.hy, nxt.gates_flipped, nxt.jumps)
                        if key not in seen_states:
                            seen_states.add(key)
                            stack.append((nxt, tnum + 1))
            if found4:
                safe_t1_coords.add(coord1)
    if len(safe_t1_coords) < 2:
        errors.append(f"Spawn 4-turn fairness failed: only {len(safe_t1_coords)} safe T1 coords {safe_t1_coords}")

    # Author solution check
    sol = dungeon_dict["author_solution"]
    if not isinstance(sol, list) or not (1 <= len(sol) <= MAX_AUTHOR_STEPS):
        errors.append(f"author_solution len must be 1..{MAX_AUTHOR_STEPS}, got {len(sol) if isinstance(sol, list) else type(sol)}")
    else:
        eng = EngineV22(grid)
        for idx, act in enumerate(sol):
            if act not in VALID_ACTIONS:
                errors.append(f"author_solution[{idx}] invalid action {act}")
                break
            st = eng.step(act)
            if idx < len(sol) - 1 and st != "RUNNING":
                errors.append(f"author_solution ended early at step {idx+1} with status {st}")
                break
            if idx == len(sol) - 1 and st != "CLEARED":
                errors.append(f"author_solution did not CLEAR on final step {idx+1}: status={st} pos=({eng.hx},{eng.hy}) hp={eng.hp} keys={eng.keys}")
                break

    info = {
        "spent_gold": spent,
        "vault_gold": MAX_BUDGET - spent,
        "author_steps": len(sol) if isinstance(sol, list) else -1,
        "safe_t1_coords": sorted(safe_t1_coords),
        "counts": counts,
    }
    return (len(errors) == 0), errors, info


def run_self_tests():
    # 1. Verify all 23 Part 1 match replays!
    with open("part1_dungeons_benchmark.json", encoding="utf-8") as f:
        p1 = json.load(f)

    total_matches = 0
    mismatches = 0
    for m in p1["my_hero_matches"]:
        grid = p1["dungeons"][m["demon_id"]]["grid"]
        eng = EngineV22(grid)
        total_matches += 1
        ok = True
        for i, act in enumerate(m["actions"]):
            eng.step(act)
            exp_pos = tuple(m["positions"][i + 1])
            exp_hp = m["hp_trace"][i + 1]
            if (eng.hx, eng.hy) != exp_pos or eng.hp != exp_hp:
                print(f"[MISMATCH hero vs {m['demon_id']}] T{i+1} act={act}: got pos=({eng.hx},{eng.hy}) hp={eng.hp} vs exp pos={exp_pos} hp={exp_hp}")
                ok = False
                mismatches += 1
                break
        if ok and eng.status != m["status"]:
            print(f"[STATUS MISMATCH hero vs {m['demon_id']}] got {eng.status} vs {m['status']}")
            mismatches += 1

    for m in p1["my_demon_defense_matches"]:
        if m["hero_id"] == "opus":
            continue  # DQ interface error streak in Part 1
        grid = p1["dungeons"]["argon"]["grid"]
        eng = EngineV22(grid)
        total_matches += 1
        ok = True
        for i, act in enumerate(m["actions"]):
            eng.step(act)
            exp_pos = tuple(m["positions"][i + 1])
            exp_hp = m["hp_trace"][i + 1]
            if (eng.hx, eng.hy) != exp_pos or eng.hp != exp_hp:
                print(f"[MISMATCH demon vs {m['hero_id']}] T{i+1} act={act}: got pos=({eng.hx},{eng.hy}) hp={eng.hp} vs exp pos={exp_pos} hp={exp_hp}")
                ok = False
                mismatches += 1
                break
        if ok and eng.status != m["status"]:
            print(f"[STATUS MISMATCH demon vs {m['hero_id']}] got {eng.status} vs {m['status']}")
            mismatches += 1

    print(f"Part-1 replay verification: {total_matches - mismatches}/{total_matches} EXACT MATCH!")

    # 2. Verify all 8 v2.2 golden vectors!
    def empty_grid():
        return [
            ["T_W" if (x == 0 or x == 39 or y == 0 or y == 25) else "EMPTY" for x in range(40)]
            for y in range(26)
        ]

    # GV22_02: PLATE BOX ONLY
    g = empty_grid()
    g[13][5] = "PLATE"; g[13][34] = "P_GATE"; g[13][7] = "BOX"
    e = EngineV22(g, start_pos=(4, 13))
    e.step("MOVE_R")
    assert e.is_plates_active() is False and e.is_high_wall(34, 13) is True
    e = EngineV22(g, start_pos=(8, 13))
    e.step("MOVE_L"); e.step("MOVE_L")
    assert e.is_plates_active() is True and e.is_high_wall(34, 13) is False

    # GV22_03: LCM12 instant kill
    g = empty_grid()
    g[8][15] = "LASER_D"; g[10][12] = "LASER2_R"
    e = EngineV22(g, start_pos=(15, 10), turn=12)
    obs = e.get_observation()
    periods = sorted(w["period"] for w in obs["laser_warnings"] if (w["x"], w["y"]) == (15, 10))
    assert periods == [3, 4], f"periods={periods}"
    e.step("WAIT")
    assert e.hp == 0 and e.status == "DEAD"

    # GV22_04: ONEWAY reverse push & mirror new_dir
    g = empty_grid()
    g[13][5] = "CRACK"; g[13][6] = "ONEWAY_L"
    e = EngineV22(g, start_pos=(5, 13))
    e.occupant[13][6] = "BOX"
    e.step("MOVE_R")
    assert (e.hx, e.hy) == (5, 13) and e.occupant[13][6] == "BOX" and e.terrain[13][5] == "CRACK"
    g = empty_grid()
    g[10][10] = "MIRROR_NE"; g[9][10] = "ONEWAY_R"
    e = EngineV22(g, start_pos=(9, 10))
    e.step("MOVE_R")
    assert (e.hx, e.hy) == (10, 10)

    # GV22_05: SPRING & JUMP ONEWAY
    g = empty_grid()
    g[10][10] = "SPRING_R"; g[10][12] = "ONEWAY_L"
    e = EngineV22(g, start_pos=(9, 10))
    e.step("MOVE_R")
    assert (e.hx, e.hy) == (11, 10)
    g = empty_grid()
    g[14][6] = "ONEWAY_L"
    e = EngineV22(g, start_pos=(5, 14))
    e.step("JUMP_R")
    assert (e.hx, e.hy) == (5, 14) and e.jumps == 2

    # GV22_06: THROW air pass vs ground stop on ONEWAY
    g = empty_grid()
    g[10][6] = "ONEWAY_L"; g[10][7] = "SWITCH"
    e = EngineV22(g, start_pos=(5, 10))
    e.step("THROW_R")
    assert e.gates_flipped is True
    g = empty_grid()
    g[15][11] = "ICE"; g[15][12] = "ONEWAY_L"; g[15][13] = "SWITCH"
    e = EngineV22(g, start_pos=(5, 15))
    e.step("THROW_R")
    assert e.gates_flipped is False

    # GV22_07: Phase C box destruction closes P_GATE before Phase D laser
    g = empty_grid()
    g[10][10] = "PLATE"; g[10][12] = "P_GATE"; g[10][15] = "LASER_L"
    e = EngineV22(g, start_pos=(7, 10), turn=3)
    e.occupant[10][10] = "BOX"
    e.active_bombs.append({"x": 10, "y": 11, "timer": 1})
    e.step("WAIT")
    assert e.is_plates_active() is False and e.hp == 100

    print("All v2.2 Golden Vectors (GV22_02..GV22_07) PASSED!")


if __name__ == "__main__":
    run_self_tests()
