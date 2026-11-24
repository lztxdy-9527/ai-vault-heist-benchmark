"""Part 2 FULL-mode dual-role submission: Chrono-Bastion v2.2 & FullWorldEnv Hero Solver."""

import collections
import heapq
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
DIR_NAMES = ("U", "D", "L", "R")

MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}

LASER1_DIRS = {"LASER_U": "U", "LASER_D": "D", "LASER_L": "L", "LASER_R": "R"}
LASER2_DIRS = {"LASER2_U": "U", "LASER2_D": "D", "LASER2_L": "L", "LASER2_R": "R"}
ALL_LASER_DIRS = {**LASER1_DIRS, **LASER2_DIRS}
SPRING_DIRS = {"SPRING_U": "U", "SPRING_D": "D", "SPRING_L": "L", "SPRING_R": "R"}
ONEWAY_DIRS = {"ONEWAY_U": "U", "ONEWAY_D": "D", "ONEWAY_L": "L", "ONEWAY_R": "R"}
PORTAL_PAIRS = {
    "PORTAL_1A": "PORTAL_1B", "PORTAL_1B": "PORTAL_1A",
    "PORTAL_2A": "PORTAL_2B", "PORTAL_2B": "PORTAL_2A",
}

BOMB_IMMUNE = {
    "T_W", "K1", "K2", "V", "PIT", "PLATE", "P_GATE",
    "ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R",
    "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
}

_AUTHOR_SOLUTION = ['MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_D', 'MOVE_R', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_L', 'MOVE_U', 'MOVE_R', 'MOVE_R', 'MOVE_D', 'MOVE_D', 'MOVE_L', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_L', 'MOVE_L', 'MOVE_L', 'MOVE_L', 'MOVE_L', 'MOVE_D', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'WAIT', 'WAIT', 'MOVE_R', 'MOVE_R', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'THROW_R', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'JUMP_R', 'MOVE_R', 'WAIT', 'MOVE_U', 'MOVE_L', 'MOVE_L', 'WAIT', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_R', 'MOVE_U', 'MOVE_U', 'MOVE_U', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'THROW_R', 'MOVE_D', 'MOVE_L', 'MOVE_L', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_D', 'MOVE_L', 'MOVE_D', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'MOVE_R', 'JUMP_R', 'MOVE_D', 'MOVE_D', 'MOVE_R', 'MOVE_R', 'JUMP_R']


def build_dungeon() -> dict:
    """Build Chrono-Bastion v2.2 FULL-mode dungeon with coupled Sokoban, repurpose, mod-12 lasers, and double switch."""
    grid = [
        ["T_W" if (x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1) else "EMPTY" for x in range(GRID_WIDTH)]
        for y in range(GRID_HEIGHT)
    ]

    def put(x: int, y: int, t: str) -> None:
        grid[y][x] = t

    # K1 Vault [32..38, 1..6]
    for x in range(32, 39):
        put(x, 7, "T_W")
    for y in range(1, 7):
        if y != 4:
            put(32, y, "T_W")
    put(32, 4, "P_GATE")
    put(33, 4, "PIT")
    put(34, 4, "R_GATE")
    put(35, 4, "ICE")

    put(35, 1, "LASER_D")
    put(35, 2, "PIT")
    put(34, 1, "T_W")
    put(34, 2, "T_W")
    put(36, 1, "T_W")
    put(36, 2, "T_W")

    put(38, 5, "LASER2_L")
    put(37, 5, "PIT")
    put(37, 4, "T_W")
    put(38, 4, "T_W")
    put(37, 6, "T_W")
    put(38, 6, "T_W")

    put(34, 6, "K1")
    put(35, 6, "PORTAL_1A")
    put(36, 6, "T_W")

    # V Vault: 1-row sealed corridor [34..38, 8]
    put(33, 8, "T_W")
    for x in range(33, 39):
        put(x, 9, "T_W")
    put(34, 8, "PORTAL_2B")
    put(36, 8, "PIT")
    put(37, 8, "V")

    # K2 Vault [32..38, 16..24]
    for x in range(32, 39):
        put(x, 16, "T_W")
    for y in range(17, 25):
        if y != 20:
            put(32, y, "T_W")
    put(31, 20, "ONEWAY_R")
    put(32, 20, "PIT")
    put(33, 20, "PIT")
    put(34, 20, "B_GATE")

    put(34, 22, "K2")
    put(35, 22, "CRACK")
    put(36, 22, "PORTAL_2A")
    put(37, 22, "T_W")
    put(36, 23, "T_W")

    # Sniper SWITCH Bunker (16, 13)
    put(15, 13, "ONEWAY_L")
    put(16, 13, "SWITCH")
    put(17, 13, "ONEWAY_R")
    for px in (15, 16, 17):
        put(px, 12, "T_W")
        put(px, 14, "T_W")

    # Box 1 -> Plate 1 in NW Sokoban
    put(7, 6, "BOX")
    put(13, 3, "PLATE")
    for wx, wy in ((6, 4), (7, 4), (8, 4), (12, 2), (14, 2), (14, 3), (12, 6), (13, 6)):
        put(wx, wy, "W")

    # Box 2 -> Plate 2 at (12,20), later repurposed East into (32,20) PIT
    put(7, 20, "BOX")
    put(12, 20, "PLATE")
    put(14, 15, "LASER_D")
    put(14, 16, "PIT")
    put(13, 15, "T_W")
    put(13, 16, "T_W")
    put(15, 15, "T_W")
    put(15, 16, "T_W")

    put(10, 24, "LASER2_U")
    put(10, 23, "PIT")
    put(9, 23, "T_W")
    put(9, 24, "T_W")
    put(11, 23, "T_W")
    put(11, 24, "T_W")

    # PORTAL_1B one-way exit vestibule
    put(6, 16, "PORTAL_1B")
    put(7, 16, "ONEWAY_R")
    put(5, 16, "T_W")
    put(6, 15, "T_W")
    put(6, 17, "T_W")

    return {
        "taunt": "Plates feed pits. Mod-12 waits for none.",
        "grid": grid,
        "author_solution": list(_AUTHOR_SOLUTION),
    }


def _in_bounds(x: int, y: int) -> bool:
    return 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT


def _classify_chests_csp(terrain: list[list[str]], clues: list[list[bool]]) -> tuple[set, set, set]:
    """Classify CHEST coordinates in FULL mode into (confirmed_heals, confirmed_mimics, suspect_mimics)."""
    chests = []
    clue_cells = set()
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if terrain[y][x] == "CHEST":
                chests.append((x, y))
            if clues[y][x]:
                clue_cells.add((x, y))

    heals = set()
    mimics = set()
    suspects = set()

    # Check orthogonal neighbors of each chest
    ambiguous = []
    for cx, cy in chests:
        adj_clues = []
        for dx, dy in DIRECTIONS.values():
            nx, ny = cx + dx, cy + dy
            if _in_bounds(nx, ny) and (nx, ny) in clue_cells:
                adj_clues.append((nx, ny))
        if not adj_clues:
            heals.add((cx, cy))
        else:
            ambiguous.append((cx, cy))

    # Every clue cell must be adjacent to at least one MIMIC in ambiguous
    amb_set = set(ambiguous)
    for clx, cly in clue_cells:
        adj_chests = []
        for dx, dy in DIRECTIONS.values():
            nx, ny = clx + dx, cly + dy
            if (nx, ny) in amb_set:
                adj_chests.append((nx, ny))
        if len(adj_chests) == 1:
            mimics.add(adj_chests[0])

    for c in ambiguous:
        if c not in mimics:
            suspects.add(c)
    return heals, mimics, suspects


class FullWorldEnv:
    """Fast static-base + sparse-delta exact v2.2 FULL world model & simulator."""

    def __init__(self, state: dict):
        tr = state["terrain"]
        occ = state["occupant"]
        clues = state["clues"]
        self.base_terrain = [row[:] for row in tr]
        self.portals = {}
        self.plates = []
        self.switches = set()
        self.k1 = tuple(state["targets"]["K1"])
        self.k2 = tuple(state["targets"]["K2"])
        self.v = tuple(state["targets"]["V"])

        init_boxes = set()
        init_tnts = set()
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                t = tr[y][x]
                o = occ[y][x]
                if t in PORTAL_PAIRS:
                    self.portals[t] = (x, y)
                elif t == "PLATE":
                    self.plates.append((x, y))
                elif t == "SWITCH":
                    self.switches.add((x, y))
                if o == "BOX":
                    init_boxes.add((x, y))
                elif o == "TNT":
                    init_tnts.add((x, y))
        self.plates = tuple(sorted(self.plates))
        self.heals, self.mimics, self.suspects = _classify_chests_csp(tr, clues)
        self.init_boxes = frozenset(init_boxes)
        self.init_tnts = frozenset(init_tnts)
        self.geom_cache = {}

    def tile_at(self, ov: dict, x: int, y: int) -> str:
        return ov.get((x, y), self.base_terrain[y][x])

    def is_plates_active(self, boxes: frozenset) -> bool:
        return bool(self.plates) and all(p in boxes for p in self.plates)

    def is_high_wall(self, ov: dict, gf: bool, p_act: bool, x: int, y: int) -> bool:
        if not _in_bounds(x, y):
            return True
        t = ov.get((x, y), self.base_terrain[y][x])
        if t in ("W", "T_W") or t in ALL_LASER_DIRS:
            return True
        if t == "R_GATE" and not gf:
            return True
        if t == "B_GATE" and gf:
            return True
        if t == "P_GATE" and not p_act:
            return True
        return False

    def blocks_oneway(self, ov: dict, x: int, y: int, d: str) -> bool:
        if not _in_bounds(x, y):
            return False
        t = ov.get((x, y), self.base_terrain[y][x])
        return t in ONEWAY_DIRS and d != ONEWAY_DIRS[t]

    def get_geom(self, boxes: frozenset, tnts: frozenset, ov_items: tuple, gf: bool):
        key = (boxes, tnts, ov_items, gf)
        g = self.geom_cache.get(key)
        if g is not None:
            return g
        ov = dict(ov_items)
        p_act = self.is_plates_active(boxes)

        red_rays = []
        blue_rays = []
        all_laser_cells = set()
        for y in range(1, GRID_HEIGHT - 1):
            for x in range(1, GRID_WIDTH - 1):
                t = ov.get((x, y), self.base_terrain[y][x])
                if t in LASER1_DIRS:
                    per = 3
                elif t in LASER2_DIRS:
                    per = 4
                else:
                    continue
                d = ALL_LASER_DIRS[t]
                dx, dy = DIRECTIONS[d]
                cells = set()
                for k in range(1, 11):
                    nx, ny = x + k * dx, y + k * dy
                    if self.is_high_wall(ov, gf, p_act, nx, ny) or (nx, ny) in boxes or (nx, ny) in tnts:
                        break
                    cells.add((nx, ny))
                    all_laser_cells.add((nx, ny))
                if cells:
                    fcells = frozenset(cells)
                    if per == 3:
                        red_rays.append(fcells)
                    else:
                        blue_rays.append(fcells)

        all_laser_cells_f = frozenset(all_laser_cells)
        laser_zone = set(all_laser_cells)
        for lx, ly in all_laser_cells:
            for ddx, ddy in DIRECTIONS.values():
                nx, ny = lx + ddx, ly + ddy
                if _in_bounds(nx, ny):
                    laser_zone.add((nx, ny))
        # Also keep phase on ICE/MIRROR/SPRING/PORTAL tiles AND their entry neighbors so slide/portal laser waits work cleanly
        if all_laser_cells:
            for y in range(1, GRID_HEIGHT - 1):
                for x in range(1, GRID_WIDTH - 1):
                    t = ov.get((x, y), self.base_terrain[y][x])
                    if t == "ICE" or t in MIRROR_MAP or t in SPRING_DIRS or t in PORTAL_PAIRS:
                        laser_zone.add((x, y))
                        for ddx, ddy in DIRECTIONS.values():
                            nx, ny = x + ddx, y + ddy
                            if _in_bounds(nx, ny):
                                laser_zone.add((nx, ny))

        # Build flat 26x40 terrain, high_wall & oneway lookup grids for O(1) BFS/sim access!
        base_t = self.base_terrain
        hw = [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        ow = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        terr = [row[:] for row in base_t]
        for (ox, oy), ot in ov.items():
            terr[oy][ox] = ot
        for y in range(GRID_HEIGHT):
            row_hw = hw[y]
            row_ow = ow[y]
            row_t = terr[y]
            for x in range(GRID_WIDTH):
                t = row_t[x]
                if t in ("W", "T_W") or t in ALL_LASER_DIRS or (t == "R_GATE" and not gf) or (t == "B_GATE" and gf) or (t == "P_GATE" and not p_act):
                    row_hw[x] = True
                elif t in ONEWAY_DIRS:
                    row_ow[x] = ONEWAY_DIRS[t]

        lmod = 12 if (red_rays and blue_rays) else (4 if blue_rays else (3 if red_rays else 1))
        g = {
            "ov": ov,
            "p_act": p_act,
            "terr": terr,
            "hw": hw,
            "ow": ow,
            "red_rays": red_rays,
            "blue_rays": blue_rays,
            "all_laser_cells": all_laser_cells_f,
            "laser_zone": frozenset(laser_zone),
            "lmod": lmod,
            "sim_cache": {},
        }
        self.geom_cache[key] = g
        return g

    def exposed_damage(self, geom: dict, turn_num: int, exposed: frozenset) -> int:
        if not (exposed & geom["all_laser_cells"]):
            return 0
        hits = 0
        if turn_num % 3 == 0:
            for cs in geom["red_rays"]:
                if exposed & cs:
                    hits += 1
        if turn_num % 4 == 0:
            for cs in geom["blue_rays"]:
                if exposed & cs:
                    hits += 1
        return 50 * hits

    def sim_step(self, geom: dict, boxes: frozenset, tnts: frozenset, gf: bool, keys: int,
                 x: int, y: int, action: str) -> dict | None:
        """Exact static-world transition for MOVE_d / JUMP_d / WAIT; caches per (x,y,action,keys)."""
        if action == "WAIT":
            return {
                "end": (x, y),
                "exposed": frozenset(((x, y),)),
                "cracks": (),
                "flips": False,
                "heal": False,
                "mimic": False,
                "got_k1": False,
                "got_k2": False,
                "won": False,
            }
        cache_key = (x, y, action, keys)
        sc = geom["sim_cache"]
        if cache_key in sc:
            return sc[cache_key]

        terr = geom["terr"]
        hw = geom["hw"]
        ow = geom["ow"]

        is_jump = action[0] == "J"
        d = action[-1]
        dx, dy = DIRECTIONS[d]

        if is_jump:
            x1, y1 = x + dx, y + dy
            x2, y2 = x + 2 * dx, y + 2 * dy
            if not (0 <= x1 < 40 and 0 <= y1 < 26) or hw[y1][x1] or (ow[y1][x1] is not None and d != ow[y1][x1]):
                sc[cache_key] = None
                return None
            if not (0 <= x2 < 40 and 0 <= y2 < 26) or hw[y2][x2] or (ow[y2][x2] is not None and d != ow[y2][x2]) or (x2, y2) in boxes or (x2, y2) in tnts:
                sc[cache_key] = None
                return None
            cur_x, cur_y = x, y
            nx, ny = x2, y2
        else:
            x1, y1 = x + dx, y + dy
            if not (0 <= x1 < 40 and 0 <= y1 < 26) or hw[y1][x1] or (ow[y1][x1] is not None and d != ow[y1][x1]) or (x1, y1) in boxes or (x1, y1) in tnts:
                sc[cache_key] = None
                return None
            cur_x, cur_y = x, y
            nx, ny = x1, y1

        cur_d = d
        step_cnt = 0
        portal_cnt = 0
        sup_portal = False
        exposed = {(x, y)}
        cracks = set()
        flips = False
        heal_pos = None
        mimic = False
        got_k1 = bool(keys & 1)
        got_k2 = bool(keys & 2)
        new_k1 = False
        new_k2 = False
        won = False

        while step_cnt < 32:
            step_cnt += 1
            if not is_jump or step_cnt > 1:
                if terr[cur_y][cur_x] == "CRACK":
                    cracks.add((cur_x, cur_y))
            else:
                if terr[y][x] == "CRACK":
                    cracks.add((x, y))

            cur_x, cur_y = nx, ny
            exposed.add((cur_x, cur_y))
            t = "PIT" if (cur_x, cur_y) in cracks else terr[cur_y][cur_x]

            if t == "PIT":
                sc[cache_key] = None
                return None
            if t == "SWITCH":
                flips = not flips
                break  # treat switch as macro boundary cleanly
            if t == "K1" and not got_k1:
                got_k1 = True
                new_k1 = True
            elif t == "K2" and not got_k2:
                got_k2 = True
                new_k2 = True
            elif t == "V" and got_k1 and got_k2:
                won = True
                break
            elif t == "CHEST":
                if (cur_x, cur_y) in self.heals:
                    heal_pos = (cur_x, cur_y)
                    break
                else:
                    mimic = True
                    break

            if step_cnt >= 32:
                break

            sup = sup_portal
            sup_portal = False
            cur_gf = gf ^ flips

            if t == "ICE":
                vx, vy = DIRECTIONS[cur_d]
                tx, ty = cur_x + vx, cur_y + vy
                if not (0 <= tx < 40 and 0 <= ty < 26) or self.is_high_wall(geom["ov"], cur_gf, geom["p_act"], tx, ty) or (ow[ty][tx] is not None and cur_d != ow[ty][tx]):
                    break
                if (tx, ty) in boxes or (tx, ty) in tnts:
                    break
                nx, ny = tx, ty
                continue

            if t in MIRROR_MAP:
                cur_d = MIRROR_MAP[t][cur_d]
                vx, vy = DIRECTIONS[cur_d]
                tx, ty = cur_x + vx, cur_y + vy
                if not (0 <= tx < 40 and 0 <= ty < 26) or self.is_high_wall(geom["ov"], cur_gf, geom["p_act"], tx, ty) or (ow[ty][tx] is not None and cur_d != ow[ty][tx]):
                    break
                if (tx, ty) in boxes or (tx, ty) in tnts:
                    break
                nx, ny = tx, ty
                continue

            if t in SPRING_DIRS:
                cur_d = SPRING_DIRS[t]
                vx, vy = DIRECTIONS[cur_d]
                blk = None
                for k in (1, 2, 3):
                    px, py = cur_x + k * vx, cur_y + k * vy
                    if (not (0 <= px < 40 and 0 <= py < 26) or self.is_high_wall(geom["ov"], cur_gf, geom["p_act"], px, py)
                            or (ow[py][px] is not None and cur_d != ow[py][px]) or (px, py) in boxes or (px, py) in tnts):
                        blk = k
                        break
                if blk == 1:
                    break
                land_k = 3 if blk is None else blk - 1
                nx, ny = cur_x + land_k * vx, cur_y + land_k * vy
                continue

            if t in PORTAL_PAIRS and not sup:
                pair = PORTAL_PAIRS[t]
                if pair not in self.portals:
                    break
                px, py = self.portals[pair]
                if (px, py) in boxes or (px, py) in tnts:
                    break
                portal_cnt += 1
                step_cnt += 1
                cur_x, cur_y = px, py
                exposed.add((px, py))
                # Check portal target effects
                pt = "PIT" if (px, py) in cracks else terr[py][px]
                if pt == "PIT":
                    sc[cache_key] = None
                    return None
                if pt == "K1" and not got_k1:
                    got_k1 = True
                    new_k1 = True
                elif pt == "K2" and not got_k2:
                    got_k2 = True
                    new_k2 = True
                elif pt == "V" and got_k1 and got_k2:
                    won = True
                    break
                elif pt == "SWITCH":
                    flips = not flips
                    break
                elif pt == "CHEST":
                    if (px, py) in self.heals:
                        heal_pos = (px, py)
                        break
                    else:
                        mimic = True
                        break
                if portal_cnt >= 2 or step_cnt >= 32:
                    break
                vx, vy = DIRECTIONS[cur_d]
                tx, ty = px + vx, py + vy
                if not (0 <= tx < 40 and 0 <= ty < 26) or self.is_high_wall(geom["ov"], gf ^ flips, geom["p_act"], tx, ty) or (ow[ty][tx] is not None and cur_d != ow[ty][tx]):
                    break
                if (tx, ty) in boxes or (tx, ty) in tnts:
                    break
                nx, ny = tx, ty
                sup_portal = True
                continue

            break

        if mimic:
            sc[cache_key] = None
            return None

        res = {
            "end": (cur_x, cur_y),
            "exposed": frozenset(exposed),
            "cracks": tuple(sorted(cracks)) if cracks else (),
            "flips": flips,
            "heal": heal_pos,
            "got_k1": new_k1,
            "got_k2": new_k2,
            "won": won,
        }
        sc[cache_key] = res
        return res

    def sim_box_push(self, geom: dict, boxes: frozenset, tnts: frozenset, gf: bool,
                     bx: int, by: int, d: str) -> dict | None:
        """Simulate pushing BOX at (bx,by) in direction d (+ chains). Assumes (bx-dx,by-dy) has hero."""
        ov = geom["ov"]
        p_act = geom["p_act"]
        dx, dy = DIRECTIONS[d]
        x1, y1 = bx + dx, by + dy

        def box_ok(tx: int, ty: int, td: str, cur_ov: dict, cur_gf: bool, cur_p_act: bool) -> bool:
            if self.is_high_wall(cur_ov, cur_gf, cur_p_act, tx, ty) or self.blocks_oneway(cur_ov, tx, ty, td):
                return False
            if (tx, ty) in boxes and (tx, ty) != (bx, by):
                return False
            if (tx, ty) in tnts:
                return False
            if cur_ov.get((tx, ty), self.base_terrain[ty][tx]) in ("K1", "K2", "V"):
                return False
            return True

        # Check HERO entering (bx,by) along d won't be blocked by ONEWAY or CRACK rules!
        if self.blocks_oneway(ov, bx, by, d):
            return None
        if not box_ok(x1, y1, d, ov, gf, p_act):
            if _in_bounds(x1, y1) and (x1, y1) in tnts:
                return {"tnt_armed": (x1, y1), "land": (bx, by), "pit_filled": None, "cracks": (), "flips": False}
            return None

        cur_x, cur_y = bx, by
        nx, ny = x1, y1
        cur_d = d
        step_cnt = 0
        portal_cnt = 0
        sup_portal = False
        cracks = set()
        flips = False
        pit_filled = None
        tnt_armed = None
        # Compute live p_act with box vacated from (bx,by) during box flight
        temp_boxes = (boxes - {(bx, by)})

        while step_cnt < 32:
            step_cnt += 1
            if self.tile_at(ov, cur_x, cur_y) == "CRACK":
                cracks.add((cur_x, cur_y))
            cur_x, cur_y = nx, ny
            t = "PIT" if (cur_x, cur_y) in cracks else self.tile_at(ov, cur_x, cur_y)
            if t == "PIT":
                pit_filled = (cur_x, cur_y)
                break
            if t == "SWITCH":
                flips = not flips

            if step_cnt >= 32:
                break
            sup = sup_portal
            sup_portal = False
            cur_gf = gf ^ flips
            cur_p_act = self.is_plates_active(temp_boxes | {(cur_x, cur_y)})

            if t == "ICE":
                vx, vy = DIRECTIONS[cur_d]
                tx, ty = cur_x + vx, cur_y + vy
                if not box_ok(tx, ty, cur_d, ov, cur_gf, cur_p_act):
                    if _in_bounds(tx, ty) and (tx, ty) in tnts:
                        tnt_armed = (tx, ty)
                    break
                nx, ny = tx, ty
                continue

            if t in MIRROR_MAP:
                cur_d = MIRROR_MAP[t][cur_d]
                vx, vy = DIRECTIONS[cur_d]
                tx, ty = cur_x + vx, cur_y + vy
                if not box_ok(tx, ty, cur_d, ov, cur_gf, cur_p_act):
                    if _in_bounds(tx, ty) and (tx, ty) in tnts:
                        tnt_armed = (tx, ty)
                    break
                nx, ny = tx, ty
                continue

            if t in SPRING_DIRS:
                cur_d = SPRING_DIRS[t]
                vx, vy = DIRECTIONS[cur_d]
                blk = None
                for k in (1, 2, 3):
                    px, py = cur_x + k * vx, cur_y + k * vy
                    if not box_ok(px, py, cur_d, ov, cur_gf, cur_p_act):
                        if _in_bounds(px, py) and (px, py) in tnts:
                            tnt_armed = (px, py)
                        blk = k
                        break
                if blk == 1:
                    break
                land_k = 3 if blk is None else blk - 1
                nx, ny = cur_x + land_k * vx, cur_y + land_k * vy
                continue

            if t in PORTAL_PAIRS and not sup:
                pair = PORTAL_PAIRS[t]
                if pair not in self.portals:
                    break
                px, py = self.portals[pair]
                if ((px, py) in temp_boxes) or (px, py) in tnts or self.tile_at(ov, px, py) in ("K1", "K2", "V"):
                    break
                portal_cnt += 1
                step_cnt += 1
                cur_x, cur_y = px, py
                if portal_cnt >= 2 or step_cnt >= 32:
                    break
                vx, vy = DIRECTIONS[cur_d]
                tx, ty = px + vx, py + vy
                if not box_ok(tx, ty, cur_d, ov, cur_gf, self.is_plates_active(temp_boxes | {(cur_x, cur_y)})):
                    if _in_bounds(tx, ty) and (tx, ty) in tnts:
                        tnt_armed = (tx, ty)
                    break
                nx, ny = tx, ty
                sup_portal = True
                continue

            break

        return {
            "land": None if pit_filled else (cur_x, cur_y),
            "pit_filled": pit_filled,
            "tnt_armed": tnt_armed,
            "cracks": tuple(sorted(cracks)),
            "flips": flips,
        }

    def sim_throw(self, geom: dict, boxes: frozenset, tnts: frozenset, gf: bool, sx: int, sy: int, d: str) -> dict:
        terr = geom["terr"]
        hw = geom["hw"]
        ow = geom["ow"]
        cur_dir = d
        cx, cy = sx, sy
        range_left = 6
        portal_cnt = 0
        hit_switch = None
        hit_tnt = None
        hit_mimic = None
        shattered = False

        while range_left > 0:
            dx, dy = DIRECTIONS[cur_dir]
            cx, cy = cx + dx, cy + dy
            range_left -= 1
            if not (0 <= cx < 40 and 0 <= cy < 26) or hw[cy][cx] or (cx, cy) in boxes:
                shattered = True
                break
            if (cx, cy) in tnts:
                hit_tnt = (cx, cy)
                shattered = True
                break
            t = terr[cy][cx]
            if t == "SWITCH":
                hit_switch = (cx, cy)
                shattered = True
                break
            if t == "CHEST" and ((cx, cy) in self.mimics or (cx, cy) in self.suspects):
                hit_mimic = (cx, cy)
                shattered = True
                break
            if t in MIRROR_MAP:
                cur_dir = MIRROR_MAP[t][cur_dir]
            elif t in PORTAL_PAIRS and portal_cnt < 2:
                pair = PORTAL_PAIRS[t]
                if pair not in self.portals:
                    shattered = True
                    break
                px, py = self.portals[pair]
                if (px, py) not in boxes and (px, py) not in tnts:
                    cx, cy = px, py
                    portal_cnt += 1
                    if portal_cnt == 2:
                        shattered = True
                        break

        if not shattered and range_left == 0 and (0 <= cx < 40 and 0 <= cy < 26):
            t = terr[cy][cx]
            if t == "ICE" or t in MIRROR_MAP:
                for _ in range(32):
                    dx, dy = DIRECTIONS[cur_dir]
                    cx, cy = cx + dx, cy + dy
                    if not (0 <= cx < 40 and 0 <= cy < 26) or hw[cy][cx] or (ow[cy][cx] is not None and cur_dir != ow[cy][cx]) or (cx, cy) in boxes:
                        break
                    if (cx, cy) in tnts:
                        hit_tnt = (cx, cy)
                        break
                    t = terr[cy][cx]
                    if t == "SWITCH":
                        hit_switch = (cx, cy)
                        break
                    if t == "CHEST" and ((cx, cy) in self.mimics or (cx, cy) in self.suspects):
                        hit_mimic = (cx, cy)
                        break
                    if t in MIRROR_MAP:
                        cur_dir = MIRROR_MAP[t][cur_dir]
                    elif t == "ICE":
                        continue
                    elif t in PORTAL_PAIRS and portal_cnt < 2:
                        pair = PORTAL_PAIRS[t]
                        if pair in self.portals:
                            px, py = self.portals[pair]
                            if (px, py) not in boxes and (px, py) not in tnts:
                                cx, cy = px, py
                                portal_cnt += 1
                                if portal_cnt == 2:
                                    break
                                continue
                        break
                    else:
                        break
        return {"switch": hit_switch, "tnt": hit_tnt, "mimic": hit_mimic}

    def run_explosion_delta(self, initial_srcs: list[tuple[int, int]], boxes: frozenset, tnts: frozenset, ov_items: tuple):
        ov = dict(ov_items)
        new_tnts = set(tnts)
        new_boxes = set(boxes)
        q = collections.deque(initial_srcs)
        seen_src = set(initial_srcs)
        while q:
            ex, ey = q.popleft()
            for cy in range(max(0, ey - 1), min(GRID_HEIGHT, ey + 2)):
                for cx in range(max(0, ex - 1), min(GRID_WIDTH, ex + 2)):
                    if (cx, cy) not in seen_src and (cx, cy) in new_tnts:
                        seen_src.add((cx, cy))
                        q.append((cx, cy))
        affected = set()
        for ex, ey in seen_src:
            for cy in range(max(0, ey - 1), min(GRID_HEIGHT, ey + 2)):
                for cx in range(max(0, ex - 1), min(GRID_WIDTH, ex + 2)):
                    affected.add((cx, cy))
        for cx, cy in affected:
            new_tnts.discard((cx, cy))
            new_boxes.discard((cx, cy))
            t = ov.get((cx, cy), self.base_terrain[cy][cx])
            if t in BOMB_IMMUNE:
                continue
            elif t == "CRACK":
                ov[(cx, cy)] = "PIT"
            elif t != "EMPTY":
                ov[(cx, cy)] = "EMPTY"
        for bx, by in list(new_boxes):
            if ov.get((bx, by), self.base_terrain[by][bx]) == "PIT":
                new_boxes.remove((bx, by))
                ov[(bx, by)] = "EMPTY"
        new_ov = tuple(sorted((k, v) for k, v in ov.items() if v != self.base_terrain[k[1]][k[0]]))
        return frozenset(new_boxes), frozenset(new_tnts), new_ov, frozenset(affected)

    def hero_bfs(self, geom: dict, boxes: frozenset, tnts: frozenset, gf: bool, keys: int,
                 hx: int, hy: int, cur_turn: int, hp: int, jumps: int,
                 allow_damage: bool = False, stop_on_goal: bool = False) -> dict:
        """
        Compute exact time-aware safe reachability inside fixed world geom.
        Compresses phase mod 12 outside laser_zone for 30x+ speedup without losing optimality.
        """
        lzone = geom["laser_zone"]
        lmod = geom["lmod"]
        init_m = (cur_turn % lmod) if (hx, hy) in lzone else 0
        dist = {(hx, hy, init_m, 0): (0, 0)}  # (turns_elapsed, dmg_taken)
        parent = {}
        pq = [(0.0, 0, 0, hx, hy, cur_turn % lmod, 0)]  # (score, dt, dmg, x, y, true_m, ju)
        settled_dom = {}  # (x, y, true_m) -> list of (pj, pdt, pdmg)

        reached_xy = {}  # (x, y) -> (dt, dmg, st)
        milestones = {
            "win": None,
            "k1": None,
            "k2": None,
            "heals": {},
            "switches": {},
            "cracks": {},
        }

        def best_key(dmg_v: int, dt_v: int, ju_v: int):
            return (dmg_v, dt_v + 28 * ju_v)

        while pq:
            sc, dt, dmg, cx, cy, true_m, ju = heapq.heappop(pq)
            st = (cx, cy, true_m if (cx, cy) in lzone else 0, ju)
            prev = dist.get(st)
            if prev is not None and (dt, dmg) > prev:
                continue
            dkey = (cx, cy, true_m)
            dlist = settled_dom.get(dkey)
            if dlist is not None:
                dominated = False
                for pj, pdt, pdmg in dlist:
                    if pj <= ju and pdmg <= dmg and pdt <= dt + 12 * (ju - pj):
                        dominated = True
                        break
                if dominated:
                    continue
                dlist.append((ju, dt, dmg))
            else:
                settled_dom[dkey] = [(ju, dt, dmg)]

            if (cx, cy) not in reached_xy or best_key(dmg, dt, ju) < best_key(reached_xy[(cx, cy)][1], reached_xy[(cx, cy)][0], reached_xy[(cx, cy)][2][3]):
                reached_xy[(cx, cy)] = (dt, dmg, st)

            next_turn = cur_turn + dt + 1
            nm = next_turn % lmod

            # WAIT only inside laser_zone!
            if (cx, cy) in lzone:
                wdmg = self.exposed_damage(geom, next_turn, frozenset(((cx, cy),)))
                if wdmg == 0 or (allow_damage and hp - dmg - wdmg > 0):
                    ndmg = dmg + wdmg
                    ndt = dt + 1
                    nst = (cx, cy, nm, ju)
                    nval = (ndt, ndmg)
                    if nst not in dist or nval < dist[nst]:
                        dist[nst] = nval
                        parent[nst] = (st, "WAIT")
                        heapq.heappush(pq, (ndt + 2.5 * ndmg + 28.0 * ju, ndt, ndmg, cx, cy, nm, ju))

            # MOVE & hazard-filtered JUMP (never burn jumps over open doors!)
            acts = ["MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R"]
            if ju < jumps:
                terr = geom["terr"]
                lcells = geom["all_laser_cells"]
                for d in DIR_NAMES:
                    ddx, ddy = DIRECTIONS[d]
                    mx, my = cx + ddx, cy + ddy
                    if 0 <= mx < 40 and 0 <= my < 26:
                        mt = terr[my][mx]
                        if mt in ("PIT", "CRACK", "CHEST") or mt in SPRING_DIRS or (mx, my) in boxes or (mx, my) in tnts or (mx, my) in lcells:
                            acts.append(f"JUMP_{d}")
            for act in acts:
                is_j = act.startswith("JUMP_")
                nju = ju + (1 if is_j else 0)
                sim = self.sim_step(geom, boxes, tnts, gf, keys, cx, cy, act)
                if sim is None:
                    continue
                ex, ey = sim["end"]
                if sim["won"]:
                    cand = (dt + 1, dmg, st, act, nju)
                    if milestones["win"] is None or best_key(dmg, dt + 1, nju) < best_key(milestones["win"][1], milestones["win"][0], milestones["win"][4]):
                        milestones["win"] = cand
                    if stop_on_goal:
                        return {"dist": dist, "parent": parent, "reached": reached_xy, "milestones": milestones}
                    continue

                ldmg = self.exposed_damage(geom, next_turn, sim["exposed"])
                if ldmg > 0 and (not allow_damage or hp - dmg - ldmg <= 0):
                    continue
                ndmg = dmg + ldmg
                ndt = dt + 1

                if sim["flips"]:
                    cand = (ndt, ndmg, st, act, (ex, ey), nju)
                    ksw = (ex, ey)
                    if ksw not in milestones["switches"] or best_key(ndmg, ndt, nju) < best_key(milestones["switches"][ksw][1], milestones["switches"][ksw][0], milestones["switches"][ksw][5]):
                        milestones["switches"][ksw] = cand
                    continue

                if sim["heal"]:
                    hxy = sim["heal"]
                    cand = (ndt, ndmg, st, act, hxy, nju)
                    if hxy not in milestones["heals"] or best_key(ndmg, ndt, nju) < best_key(milestones["heals"][hxy][1], milestones["heals"][hxy][0], milestones["heals"][hxy][5]):
                        milestones["heals"][hxy] = cand
                    continue

                if sim["got_k1"]:
                    cand = (ndt, ndmg, st, act, (ex, ey), sim["cracks"], nju)
                    if milestones["k1"] is None or best_key(ndmg, ndt, nju) < best_key(milestones["k1"][1], milestones["k1"][0], milestones["k1"][6]):
                        milestones["k1"] = cand
                    continue

                if sim["got_k2"]:
                    cand = (ndt, ndmg, st, act, (ex, ey), sim["cracks"], nju)
                    if milestones["k2"] is None or best_key(ndmg, ndt, nju) < best_key(milestones["k2"][1], milestones["k2"][0], milestones["k2"][6]):
                        milestones["k2"] = cand
                    continue

                if sim["cracks"]:
                    ckey = (sim["cracks"], ex, ey)
                    cand = (ndt, ndmg, st, act, (ex, ey), nju)
                    if ckey not in milestones["cracks"] or best_key(ndmg, ndt, nju) < best_key(milestones["cracks"][ckey][1], milestones["cracks"][ckey][0], milestones["cracks"][ckey][5]):
                        milestones["cracks"][ckey] = cand
                    continue

                key_m = nm if (ex, ey) in lzone else 0
                nst = (ex, ey, key_m, nju)
                nval = (ndt, ndmg)
                if nst not in dist or nval < dist[nst]:
                    dist[nst] = nval
                    parent[nst] = (st, act)
                    heapq.heappush(pq, (ndt + 2.5 * ndmg + 28.0 * nju, ndt, ndmg, ex, ey, nm, nju))

        return {"dist": dist, "parent": parent, "reached": reached_xy, "milestones": milestones}

    def point_to_point_astar(self, geom: dict, boxes: frozenset, tnts: frozenset, gf: bool, keys: int,
                             hx: int, hy: int, cur_turn: int, hp: int, jumps: int,
                             goal_xy: tuple[int, int], allow_damage: bool = False):
        """Fast A* to single target (gx, gy), stopping immediately upon pop."""
        gx, gy = goal_xy
        if (hx, hy) == (gx, gy):
            return 0, 0, []
        lzone = geom["laser_zone"]
        lmod = geom["lmod"]
        init_m = (cur_turn % lmod) if (hx, hy) in lzone else 0
        dist = {(hx, hy, init_m, 0): (0, 0)}
        parent = {}
        pq = [(abs(hx - gx) + abs(hy - gy), 0, 0, hx, hy, cur_turn % lmod, 0)]
        ov = geom["ov"]
        lcells = geom["all_laser_cells"]
        while pq:
            _, dt, dmg, cx, cy, true_m, ju = heapq.heappop(pq)
            st = (cx, cy, true_m if (cx, cy) in lzone else 0, ju)
            if (cx, cy) == (gx, gy):
                return dt, dmg, self.reconstruct(parent, st)
            prev = dist.get(st)
            if prev is not None and (dt, dmg) > prev:
                continue
            nturn = cur_turn + dt + 1
            nm = nturn % lmod
            if (cx, cy) in lzone:
                wdmg = self.exposed_damage(geom, nturn, frozenset(((cx, cy),)))
                if wdmg == 0 or (allow_damage and hp - dmg - wdmg > 0):
                    nst = (cx, cy, nm, ju)
                    nval = (dt + 1, dmg + wdmg)
                    if nst not in dist or nval < dist[nst]:
                        dist[nst] = nval
                        parent[nst] = (st, "WAIT")
                        heapq.heappush(pq, (dt + 1 + abs(cx - gx) + abs(cy - gy) + 2.5 * nval[1] + 28.0 * ju, dt + 1, nval[1], cx, cy, nm, ju))
            acts = ["MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R"]
            if ju < jumps:
                for d in DIR_NAMES:
                    ddx, ddy = DIRECTIONS[d]
                    mx, my = cx + ddx, cy + ddy
                    if _in_bounds(mx, my):
                        mt = ov.get((mx, my), self.base_terrain[my][mx])
                        if mt != "EMPTY" or (mx, my) in boxes or (mx, my) in tnts or (mx, my) in lcells:
                            acts.append(f"JUMP_{d}")
            for act in acts:
                nju = ju + (1 if act.startswith("JUMP_") else 0)
                sim = self.sim_step(geom, boxes, tnts, gf, keys, cx, cy, act)
                if sim is None or sim["flips"] or sim["cracks"] or sim["heal"]:
                    continue
                ldmg = self.exposed_damage(geom, nturn, sim["exposed"])
                if ldmg > 0 and (not allow_damage or hp - dmg - ldmg <= 0):
                    continue
                ex, ey = sim["end"]
                ndmg = dmg + ldmg
                ndt = dt + 1
                key_m = nm if (ex, ey) in lzone else 0
                nst = (ex, ey, key_m, nju)
                nval = (ndt, ndmg)
                if nst not in dist or nval < dist[nst]:
                    dist[nst] = nval
                    parent[nst] = (st, act)
                    heapq.heappush(pq, (ndt + abs(ex - gx) + abs(ey - gy) + 2.5 * ndmg + 28.0 * nju, ndt, ndmg, ex, ey, nm, nju))
        return None

    def reconstruct(self, parent: dict, st, last_act: str | None = None) -> list[str]:
        path = []
        if last_act is not None:
            path.append(last_act)
        cur = st
        while cur in parent:
            pst, act = parent[cur]
            path.append(act)
            cur = pst
        path.reverse()
        return path


def solve_full_plan(state: dict, time_budget: float = 1.45) -> list[str]:
    """Synthesize complete or best-anytime optimal FULL action plan within time_budget."""
    t_start = time.perf_counter()
    deadline = t_start + time_budget
    env = FullWorldEnv(state)

    hx0, hy0 = state["hero"]["x"], state["hero"]["y"]
    hp0 = state["hero"]["hp"]
    j0 = state["hero"]["jumps"]
    b0 = state["hero"]["bombs"]
    th0 = state["hero"]["throws"]
    gf0 = bool(state["gates_flipped"])
    k10 = 1 if state["hero"]["keys"][0] else 0
    k20 = 2 if state["hero"]["keys"][1] else 0
    keys0 = k10 | k20
    turn0 = state["turn"] - 1  # turns already completed before action `state["turn"]`

    # Precompute optimistic static portal-aware heuristic to V, K1, K2
    def optimistic_goal_dist(x: int, y: int, keys: int) -> int:
        c = []
        if not (keys & 1):
            c.append(abs(x - env.k1[0]) + abs(y - env.k1[1]))
        if not (keys & 2):
            c.append(abs(x - env.k2[0]) + abs(y - env.k2[1]))
        if not c:
            return abs(x - env.v[0]) + abs(y - env.v[1])
        return min(c) + (15 if keys == 0 else 0) + abs((env.k1[0] if not (keys & 1) else env.k2[0]) - env.v[0]) // 2

    # Note active ticking bombs if restarted mid-bomb! Wait: normally bombs is empty at turn=1
    if state.get("bombs"):
        soon = sorted(state["bombs"], key=lambda b: b["timer"])
        mt = soon[0]["timer"]
        bxy = [(b["x"], b["y"]) for b in soon if b["timer"] == mt]
        _, _, _, aff_b = env.run_explosion_delta(bxy, env.init_boxes, env.init_tnts, ())
        if (hx0, hy0) in aff_b or mt == 1:
            g0 = env.get_geom(env.init_boxes, env.init_tnts, (), gf0)
            eq = collections.deque([(hx0, hy0, turn0, [])])
            eseen = {(hx0, hy0, 0)}
            while eq:
                ux, uy, ut, ep = eq.popleft()
                if len(ep) == mt:
                    if (ux, uy) not in aff_b:
                        return ep
                    continue
                nt = ut + 1
                for a in ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT"):
                    sim = env.sim_step(g0, env.init_boxes, env.init_tnts, gf0, keys0, ux, uy, a)
                    if sim is None:
                        continue
                    if env.exposed_damage(g0, nt, sim["exposed"]) > 0:
                        continue
                    ex, ey = sim["end"]
                    st_e = (ex, ey, len(ep) + 1)
                    if st_e not in eseen:
                        eseen.add(st_e)
                        eq.append((ex, ey, nt, ep + [a]))

    init_node = (hx0, hy0, env.init_boxes, env.init_tnts, (), gf0, keys0, hp0, j0, b0, th0)
    # Track best g=(turns + 2.0*(100-hp)) at deduped macro signature including jumps remaining
    best_g = {(hx0, hy0, env.init_boxes, env.init_tnts, (), gf0, keys0, j0): (turn0, -hp0)}

    # Priority queue items: (f_score, cur_t, -hp, step_id, node_tuple, action_list)
    step_uid = 0
    pq = [(float(turn0 + optimistic_goal_dist(hx0, hy0, keys0)), turn0, -hp0, 0, init_node, [])]
    best_partial = (0, 0, 10**9, 0, [])  # (keys, plates, min_h, turns, actions)

    # Also track second pass allowing controlled -50 HP laser crossing only when 0-dmg nodes exhaust
    deferred_damage_nodes = []

    while pq or deferred_damage_nodes:
        if time.perf_counter() > deadline:
            break
        if not pq:
            # Unlock damage-allowed exploration from deferred bottleneck nodes!
            for item in deferred_damage_nodes:
                heapq.heappush(pq, item)
            deferred_damage_nodes.clear()
            allow_dmg_mode = True
        else:
            allow_dmg_mode = False

        _, cur_t, neg_hp, _, node, acts_so_far = heapq.heappop(pq)
        hp = -neg_hp
        hx, hy, boxes, tnts, ov, gf, keys, nhp, jmp, bmb, thr = node
        if cur_t >= 240:
            continue

        # Update partial fallback on pop
        h_rem = optimistic_goal_dist(hx, hy, keys)
        k_cnt = (1 if (keys & 1) else 0) + (1 if (keys & 2) else 0)
        p_cov = sum(1 for p in env.plates if p in boxes)
        if acts_so_far and (k_cnt, p_cov, -h_rem, -cur_t) > (best_partial[0], best_partial[1], -best_partial[2], -best_partial[3]):
            best_partial = (k_cnt, p_cov, h_rem, cur_t, acts_so_far)

        geom = env.get_geom(boxes, tnts, ov, gf)
        bfs = env.hero_bfs(geom, boxes, tnts, gf, keys, hx, hy, cur_t, hp, jmp, allow_damage=allow_dmg_mode)
        ms = bfs["milestones"]
        reached = bfs["reached"]

        # 1. Instant Win!
        if ms["win"] is not None:
            dt, dmg, pst, pact, _ = ms["win"]
            if cur_t + dt <= 240:
                return acts_so_far + env.reconstruct(bfs["parent"], pst, pact)

        if not allow_dmg_mode and hp > 50:
            deferred_damage_nodes.append((cur_t + 80.0 + h_rem, cur_t, neg_hp, step_uid + 1, node, acts_so_far))

        def push_macro(new_node, add_acts, add_dt, new_hp_val, bonus=0.0):
            nonlocal step_uid, best_partial
            nt = cur_t + add_dt
            if nt >= 240 or new_hp_val <= 0:
                return
            nx, ny, nbx, ntn, nov, ngf, nkeys, _, njmp, nbmb, nthr = new_node
            sig = (nx, ny, nbx, ntn, nov, ngf, nkeys, njmp)
            prev = best_g.get(sig)
            if prev is not None and (nt, -new_hp_val) >= prev:
                return
            best_g[sig] = (nt, -new_hp_val)
            nk_cnt = (1 if (nkeys & 1) else 0) + (1 if (nkeys & 2) else 0)
            np_cov = sum(1 for p in env.plates if p in nbx)
            nh_rem = optimistic_goal_dist(nx, ny, nkeys)
            cand_part = (nk_cnt, np_cov, -nh_rem, -nt)
            cur_best_part = (best_partial[0], best_partial[1], -best_partial[2], -best_partial[3])
            full_acts = acts_so_far + add_acts
            if full_acts and cand_part > cur_best_part:
                best_partial = (nk_cnt, np_cov, nh_rem, nt, full_acts)
            step_uid += 1
            f = (nt + 2.0 * (100 - new_hp_val) + 0.9 * nh_rem - 55.0 * nk_cnt - 45.0 * np_cov
                 + 8.0 * (j0 - njmp) + 5.0 * (b0 - nbmb) + 3.0 * (th0 - nthr) + bonus)
            heapq.heappush(pq, (f, nt, -new_hp_val, step_uid, new_node, full_acts))

        # 2. Pick K1 / K2
        for kbit, mkey in ((1, "k1"), (2, "k2")):
            if ms[mkey] is not None:
                dt, dmg, pst, pact, (ex, ey), crk, _ = ms[mkey]
                ov_d = dict(ov)
                for cx, cy in crk:
                    ov_d[(cx, cy)] = "PIT"
                ov_d[env.k1 if kbit == 1 else env.k2] = "EMPTY"
                nov = tuple(sorted((k, v) for k, v in ov_d.items() if v != env.base_terrain[k[1]][k[0]]))
                add_a = env.reconstruct(bfs["parent"], pst, pact)
                nju = jmp - sum(1 for a in add_a if a.startswith("JUMP_"))
                push_macro((ex, ey, boxes, tnts, nov, gf, keys | kbit, hp - dmg, nju, bmb, thr), add_a, dt, hp - dmg, bonus=-20.0)

        # 3. Pick verified HEAL if injured
        if hp < 100:
            for hxy, (dt, dmg, pst, pact, _, _) in ms["heals"].items():
                ov_d = dict(ov)
                ov_d[hxy] = "EMPTY"
                nov = tuple(sorted((k, v) for k, v in ov_d.items() if v != env.base_terrain[k[1]][k[0]]))
                nh = min(100, (hp - dmg) + 30)
                add_a = env.reconstruct(bfs["parent"], pst, pact)
                nju = jmp - sum(1 for a in add_a if a.startswith("JUMP_"))
                push_macro((hxy[0], hxy[1], boxes, tnts, nov, gf, keys, nh, nju, bmb, thr), add_a, dt, nh, bonus=-10.0)

        # 4. Walk SWITCH
        for sw_xy, (dt, dmg, pst, pact, (ex, ey), _) in ms["switches"].items():
            add_a = env.reconstruct(bfs["parent"], pst, pact)
            nju = jmp - sum(1 for a in add_a if a.startswith("JUMP_"))
            push_macro((ex, ey, boxes, tnts, ov, not gf, keys, hp - dmg, nju, bmb, thr), add_a, dt, hp - dmg, bonus=-5.0)

        # 5. THROW onto SWITCH / TNT / MIMIC (pre-filter to tiles aligned with / within 7 tiles of targets or portals/mirrors)
        if thr > 0:
            throw_targets = set(env.switches) | tnts | env.mimics | env.suspects
            if throw_targets:
                hot_throw = []
                for (rx, ry), val in reached.items():
                    near_t = False
                    for tx, ty in throw_targets:
                        if abs(rx - tx) + abs(ry - ty) <= 7 and (rx == tx or ry == ty or env.portals):
                            near_t = True
                            break
                    if not near_t:
                        for px, py in env.portals.values():
                            if (rx == px or ry == py) and abs(rx - px) + abs(ry - py) <= 6:
                                near_t = True
                                break
                    if near_t:
                        hot_throw.append(((rx, ry), val))
                hot_throw.sort(key=lambda z: z[1][0])
                seen_throw = set()
                for (rx, ry), (dt, dmg, pst) in hot_throw:
                    for d in DIR_NAMES:
                        tres = env.sim_throw(geom, boxes, tnts, gf, rx, ry, d)
                        if tres["switch"]:
                            tag = ("sw", tres["switch"])
                            if tag not in seen_throw:
                                seen_throw.add(tag)
                                add_a = env.reconstruct(bfs["parent"], pst, f"THROW_{d}")
                                nju = jmp - sum(1 for a in add_a if a.startswith("JUMP_"))
                                push_macro((rx, ry, boxes, tnts, ov, not gf, keys, hp - dmg, nju, bmb, thr - 1), add_a, dt + 1, hp - dmg, bonus=-6.0)
                        if tres["tnt"]:
                            tx, ty = tres["tnt"]
                            if abs(rx - tx) <= 1 and abs(ry - ty) <= 1:
                                continue
                            tag = ("tnt", tx, ty)
                            if tag not in seen_throw:
                                seen_throw.add(tag)
                                nb, ntnt, nov, _ = env.run_explosion_delta([(tx, ty)], boxes, tnts, ov)
                                if len(env.plates) <= len(nb):
                                    add_a = env.reconstruct(bfs["parent"], pst, f"THROW_{d}")
                                    nju = jmp - sum(1 for a in add_a if a.startswith("JUMP_"))
                                    push_macro((rx, ry, nb, ntnt, nov, gf, keys, hp - dmg, nju, bmb, thr - 1), add_a, dt + 1, hp - dmg, bonus=-5.0)
                        if tres["mimic"]:
                            mx, my = tres["mimic"]
                            opens_adj = False
                            for ndx, ndy in DIRECTIONS.values():
                                ax_m, ay_m = mx + ndx, my + ndy
                                if _in_bounds(ax_m, ay_m) and (ax_m, ay_m) not in reached and env.tile_at(geom["ov"], ax_m, ay_m) != "T_W":
                                    opens_adj = True
                                    break
                            if opens_adj:
                                tag = ("mim", mx, my)
                                if tag not in seen_throw:
                                    seen_throw.add(tag)
                                    ov_d = dict(ov)
                                    ov_d[(mx, my)] = "EMPTY"
                                    nov = tuple(sorted((k, v) for k, v in ov_d.items() if v != env.base_terrain[k[1]][k[0]]))
                                    add_a = env.reconstruct(bfs["parent"], pst, f"THROW_{d}")
                                    nju = jmp - sum(1 for a in add_a if a.startswith("JUMP_"))
                                    push_macro((rx, ry, boxes, tnts, nov, gf, keys, hp - dmg, nju, bmb, thr - 1), add_a, dt + 1, hp - dmg, bonus=2.0)

        # 6. Walk across CRACK (only if not trivially reached by JUMP; e.g. opens new area or dead-end entry)
        for (crk, ex, ey), (dt, dmg, pst, pact, _, nju_rel) in ms["cracks"].items():
            ov_d = dict(ov)
            for cx, cy in crk:
                ov_d[(cx, cy)] = "PIT"
            nov = tuple(sorted((k, v) for k, v in ov_d.items() if v != env.base_terrain[k[1]][k[0]]))
            add_a = env.reconstruct(bfs["parent"], pst, pact)
            push_macro((ex, ey, boxes, tnts, nov, gf, keys, hp - dmg, jmp - nju_rel, bmb, thr), add_a, dt, hp - dmg, bonus=3.0)

        # 7. BOX Push Macros (PLATE, PIT, SWITCH, TNT, LASER_SHIELD, or Unblock 1-2 steps!)
        uncovered_plates = set(env.plates) - boxes
        plates_set = set(env.plates)
        for bx0, by0 in sorted(boxes):
            if time.perf_counter() > deadline:
                break
            on_plate_now = (bx0, by0) in plates_set
            # Do not needlessly pull boxes off active plates while uncovered plates still exist
            if on_plate_now and uncovered_plates:
                continue

            # Precompute flat walkable passability once for this box!
            ov_dict = dict(ov)
            lcells = geom["all_laser_cells"]
            static_blk = [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
            base_t = env.base_terrain
            for py_i in range(GRID_HEIGHT):
                sb_row = static_blk[py_i]
                bt_row = base_t[py_i]
                for px_i in range(GRID_WIDTH):
                    wt = ov_dict.get((px_i, py_i), bt_row[px_i])
                    if wt in ("W", "T_W", "PIT", "CRACK", "SWITCH", "CHEST") or wt in ALL_LASER_DIRS or wt in SPRING_DIRS or wt in PORTAL_PAIRS:
                        sb_row[px_i] = True
                    elif (wt == "R_GATE" and not gf) or (wt == "B_GATE" and gf):
                        sb_row[px_i] = True

            def can_hero_walk_to_set(hstart, targets_xy, bx_block, cur_boxes):
                cp_act = env.is_plates_active(cur_boxes)
                seen_h = {hstart}
                hq = collections.deque([hstart])
                found = {}
                while hq:
                    ux, uy = hq.popleft()
                    if (ux, uy) in targets_xy:
                        found[(ux, uy)] = True
                        if len(found) == len(targets_xy):
                            return found
                    for d in DIR_NAMES:
                        vx, vy = DIRECTIONS[d]
                        wx, wy = ux + vx, uy + vy
                        if not (0 <= wx < GRID_WIDTH and 0 <= wy < GRID_HEIGHT) or (wx, wy) in seen_h:
                            continue
                        if static_blk[wy][wx]:
                            continue
                        if (wx, wy) == bx_block or (wx, wy) in cur_boxes or (wx, wy) in tnts:
                            continue
                        wt = ov_dict.get((wx, wy), base_t[wy][wx])
                        if (wt == "P_GATE" and not cp_act) or (wt in ONEWAY_DIRS and d != ONEWAY_DIRS[wt]):
                            continue
                        seen_h.add((wx, wy))
                        hq.append((wx, wy))
                return found

            # Heuristic A* over single-box positions toward PLATE / open PIT / SWITCH / TNT / Laser shield!
            all_pits = []
            open_pits = []
            for py_i in range(1, GRID_HEIGHT - 1):
                for px_i in range(1, GRID_WIDTH - 1):
                    if ov_dict.get((px_i, py_i), base_t[py_i][px_i]) == "PIT":
                        all_pits.append((px_i, py_i))
                        adj_non_bunk = 0
                        for nd in DIR_NAMES:
                            ddx, ddy = DIRECTIONS[nd]
                            ax, ay = px_i + ddx, py_i + ddy
                            if 0 <= ax < GRID_WIDTH and 0 <= ay < GRID_HEIGHT:
                                at = ov_dict.get((ax, ay), base_t[ay][ax])
                                if at not in ("T_W", "W") and at not in ALL_LASER_DIRS:
                                    adj_non_bunk += 1
                        if adj_non_bunk >= 2:
                            open_pits.append((px_i, py_i))
            pit_targets = open_pits if open_pits else all_pits
            box_goal_pts = list(uncovered_plates) + list(env.switches) + list(tnts) + pit_targets

            def run_box_astar(targets_pts, max_pops: int, stop_on_pit=None):
                def _bh(x: int, y: int) -> int:
                    if not targets_pts:
                        return 0
                    return min(abs(x - gx) + abs(y - gy) for gx, gy in targets_pts)

                bpq = []
                bseen = set()
                uid = 0
                for d in DIR_NAMES:
                    dx, dy = DIRECTIONS[d]
                    rx, ry = bx0 - dx, by0 - dy
                    if (rx, ry) in reached:
                        uid += 1
                        heapq.heappush(bpq, (_bh(bx0, by0), 0, uid, bx0, by0, [(rx, ry, d)]))
                bvisited = {(bx0, by0)}
                bpops = 0
                found_plates = set()
                nonlocal shield_cnt
                while bpq and bpops < max_pops:
                    if time.perf_counter() > deadline:
                        break
                    _, p_depth, _, cbx, cby, pseq = heapq.heappop(bpq)
                    bpops += 1
                    d = pseq[-1][2]
                    cur_b = (boxes - {(bx0, by0)}) | {(cbx, cby)}
                    lite_geom = {"ov": ov_dict, "p_act": env.is_plates_active(cur_b)}
                    pres = env.sim_box_push(lite_geom, cur_b, tnts, gf, cbx, cby, d)
                    if pres is None:
                        continue
                    if pres.get("tnt_armed"):
                        strategic_targets.append((-20, pseq, pres))
                        continue
                    if pres["pit_filled"]:
                        strategic_targets.append((-25, pseq, pres))
                        found_pits.add(pres["pit_filled"])
                        if stop_on_pit is not None and pres["pit_filled"] == stop_on_pit:
                            return
                        continue
                    nbx, nby = pres["land"]
                    if pres["flips"]:
                        strategic_targets.append((-15, pseq, pres))
                        continue
                    if (nbx, nby) in uncovered_plates:
                        strategic_targets.append((-35, pseq, pres))
                        found_plates.add((nbx, nby))
                        if len(found_plates) == len(uncovered_plates):
                            break
                        continue
                    if stop_on_pit is None and (nbx, nby) in lcells and shield_cnt < 2:
                        shield_cnt += 1
                        strategic_targets.append((-12, pseq, pres))
                    if stop_on_pit is None and p_depth == 0:
                        strategic_targets.append((5, pseq, pres))
                    if p_depth >= 38 or pres["cracks"] or (nbx, nby) in bvisited:
                        continue
                    bvisited.add((nbx, nby))

                    nhx, nhy = cbx, cby
                    cur_bset = (boxes - {(bx0, by0)}) | {(nbx, nby)}
                    need_reqs = {}
                    for nd in DIR_NAMES:
                        ndx, ndy = DIRECTIONS[nd]
                        rx, ry = nbx - ndx, nby - ndy
                        if 0 <= rx < GRID_WIDTH and 0 <= ry < GRID_HEIGHT:
                            need_reqs[(rx, ry)] = nd
                    reach_ok = can_hero_walk_to_set((nhx, nhy), set(need_reqs.keys()), (nbx, nby), cur_bset)
                    for rx, ry in reach_ok:
                        nd = need_reqs[(rx, ry)]
                        if (nbx, nby, nd) not in bseen:
                            bseen.add((nbx, nby, nd))
                            uid += 1
                            nx_p, ny_p = nbx + DIRECTIONS[nd][0], nby + DIRECTIONS[nd][1]
                            heapq.heappush(bpq, (p_depth + 1 + _bh(nx_p, ny_p), p_depth + 1, uid, nbx, nby, pseq + [(rx, ry, nd)]))

            strategic_targets = []
            shield_cnt = 0
            found_pits = set()
            run_box_astar(box_goal_pts, 55 if on_plate_now else 85)
            # Targeted follow-up for open corridor PITs if not reached (e.g. 20-step plate->pit bridges!)
            for op in sorted(open_pits, key=lambda p: abs(p[0] - bx0) + abs(p[1] - by0))[:3]:
                if time.perf_counter() > deadline:
                    break
                if op not in found_pits:
                    run_box_astar([op], 50, stop_on_pit=op)

            # Deduplicate final targets by end state and execute exact time-aware hero+box replay!
            seen_final_box = set()
            seen_role_dst = set()
            filtered_targets = []
            strategic_targets.sort(key=lambda z: (z[0], len(z[1])))
            for prio, pseq, pres in strategic_targets:
                rkey = (prio, pres.get("pit_filled") or pres.get("tnt_armed") or pres.get("land"))
                if rkey not in seen_role_dst:
                    seen_role_dst.add(rkey)
                    filtered_targets.append((prio, pseq, pres))
            for prio, pseq, _ in filtered_targets[:8]:
                if time.perf_counter() > deadline:
                    break
                # Exact leg-by-leg replay from (hx, hy, cur_t, hp, jmp, boxes, tnts, ov, gf)
                rhx, rhy, rt, rhp, rjmp = hx, hy, cur_t, hp, jmp
                rboxes, rtnts, rov, rgf, rkeys = boxes, tnts, ov, gf, keys
                r_acts = []
                valid_replay = True
                for idx_p, (req_x, req_y, pd) in enumerate(pseq):
                    # Walk hero to (req_x, req_y) if not already there
                    if (rhx, rhy) != (req_x, req_y):
                        if idx_p == 0 and (req_x, req_y) in reached:
                            wdt, wdmg, wst = reached[(req_x, req_y)]
                            wacts = env.reconstruct(bfs["parent"], wst)
                        else:
                            r_geom = env.get_geom(rboxes, rtnts, rov, rgf)
                            p2p = env.point_to_point_astar(r_geom, rboxes, rtnts, rgf, rkeys, rhx, rhy, rt, rhp, rjmp, (req_x, req_y), allow_damage=allow_dmg_mode)
                            if p2p is None:
                                valid_replay = False
                                break
                            wdt, wdmg, wacts = p2p
                        r_acts.extend(wacts)
                        rjmp -= sum(1 for a in wacts if a.startswith("JUMP_"))
                        rt += wdt
                        rhp -= wdmg
                        rhx, rhy = req_x, req_y
                    # Find which box is adjacent at (req_x + dx, req_y + dy)
                    pdx, pdy = DIRECTIONS[pd]
                    tbx, tby = req_x + pdx, req_y + pdy
                    if (tbx, tby) not in rboxes:
                        valid_replay = False
                        break
                    # Check laser damage on hero entering (tbx, tby) during this push!
                    # Wait until laser-safe if waiting 1-4 turns helps (fixes wait_i turn offset + 2-turn beam lookahead)
                    pushed_ok = False
                    wait_acts = []
                    cur_rt = rt
                    cur_rhp = rhp
                    for wait_i in range(5):
                        r_geom = env.get_geom(rboxes, rtnts, rov, rgf)
                        pres = env.sim_box_push(r_geom, rboxes, rtnts, rgf, tbx, tby, pd)
                        if pres is None:
                            break
                        # Compute next state boxes/tnts/ov/gf after box moves first (step 3)
                        nbx_set = set(rboxes)
                        nbx_set.discard((tbx, tby))
                        ov_d = dict(rov)
                        for cx, cy in pres["cracks"]:
                            ov_d[(cx, cy)] = "PIT"
                        if pres.get("tnt_armed"):
                            tx, ty = pres["tnt_armed"]
                            nb_e, nt_e, nov_e, aff_e = env.run_explosion_delta([(tx, ty)], frozenset(nbx_set | {(tbx, tby)}), rtnts, rov)
                            if (rhx, rhy) in aff_e:
                                break
                            rboxes, rtnts, rov = nb_e, nt_e, nov_e
                            r_acts.extend(wait_acts)
                            r_acts.append(f"MOVE_{pd}")
                            rt = cur_rt + 1
                            rhp = cur_rhp
                            pushed_ok = True
                            break
                        if pres["pit_filled"]:
                            ov_d[pres["pit_filled"]] = "EMPTY"
                        else:
                            nbx_set.add(pres["land"])
                        ngf = rgf ^ pres["flips"]
                        nov = tuple(sorted((k, v) for k, v in ov_d.items() if v != env.base_terrain[k[1]][k[0]]))
                        nbx_f = frozenset(nbx_set)
                        # Now hero steps onto (tbx, tby) along pd!
                        h_geom = env.get_geom(nbx_f, rtnts, nov, ngf)
                        hsim = env.sim_step(h_geom, nbx_f, rtnts, ngf, rkeys, rhx, rhy, f"MOVE_{pd}")
                        if hsim is None:
                            break
                        push_turn = cur_rt + 1
                        hdmg = env.exposed_damage(h_geom, push_turn, hsim["exposed"])
                        # Also verify landing tile doesn't trap hero on turn push_turn+1 when standing in a beam
                        stay_unsafe = False
                        if hdmg == 0 and idx_p + 1 < len(pseq) and hsim["end"] in h_geom["all_laser_cells"]:
                            if env.exposed_damage(h_geom, push_turn + 1, frozenset((hsim["end"],))) > 0:
                                stay_unsafe = True
                        if (hdmg == 0 and (not stay_unsafe or wait_i == 4)) or (wait_i == 4 and allow_dmg_mode and cur_rhp - hdmg > 0):
                            r_acts.extend(wait_acts)
                            r_acts.append(f"MOVE_{pd}")
                            rt = push_turn
                            rhp = cur_rhp - hdmg
                            rhx, rhy = hsim["end"]
                            rboxes = nbx_f
                            ov_d2 = dict(nov)
                            for cx, cy in hsim["cracks"]:
                                ov_d2[(cx, cy)] = "PIT"
                            if hsim["got_k1"]:
                                rkeys |= 1
                                ov_d2[env.k1] = "EMPTY"
                            if hsim["got_k2"]:
                                rkeys |= 2
                                ov_d2[env.k2] = "EMPTY"
                            rgf = ngf ^ hsim["flips"]
                            rov = tuple(sorted((k, v) for k, v in ov_d2.items() if v != env.base_terrain[k[1]][k[0]]))
                            pushed_ok = True
                            break
                        # Otherwise wait 1 turn at (rhx, rhy) if standing tile safe
                        wd = env.exposed_damage(r_geom, push_turn, frozenset(((rhx, rhy),)))
                        if wd > 0 and not allow_dmg_mode:
                            break
                        if wait_i == 4:
                            break
                        wait_acts.append("WAIT")
                        cur_rt += 1
                        cur_rhp -= wd
                    if not pushed_ok:
                        valid_replay = False
                        break
                if valid_replay and r_acts:
                    end_sig = (rhx, rhy, rboxes, rtnts, rov, rgf, rkeys)
                    if end_sig not in seen_final_box:
                        seen_final_box.add(end_sig)
                        push_macro((rhx, rhy, rboxes, rtnts, rov, rgf, rkeys, rhp, rjmp, bmb, thr),
                                   r_acts, rt - cur_t, rhp, bonus=prio * 0.5)

        # 8. BOMB Breach Macros (verified 3-turn safe escape!)
        if bmb > 0 and time.perf_counter() <= deadline:
            geom_ov = geom["ov"]
            agoals = []
            if not (keys & 1):
                agoals.append(env.k1)
            if not (keys & 2):
                agoals.append(env.k2)
            if not agoals:
                agoals.append(env.v)
            agoals.extend(uncovered_plates)
            agoals.extend(env.switches)

            bomb_spots = set()
            for (rx, ry) in reached:
                rdt, rdmg, _ = reached[(rx, ry)]
                if rdmg > 0 and not allow_dmg_mode:
                    continue
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        cx, cy = rx + dx, ry + dy
                        if _in_bounds(cx, cy):
                            ct = env.tile_at(geom_ov, cx, cy)
                            if ct in ("W", "R_GATE", "B_GATE") or ct in ALL_LASER_DIRS or (cx, cy) in tnts or ct == "CHEST":
                                bomb_spots.add((rx, ry))
                                break
                    if (rx, ry) in bomb_spots:
                        break
            best_blast = {}
            for (rx, ry) in bomb_spots:
                if time.perf_counter() > deadline:
                    break
                dt, dmg, pst = reached[(rx, ry)]
                tb = cur_t + dt + 1
                if env.exposed_damage(geom, tb, frozenset(((rx, ry),))) > 0:
                    continue
                nb, ntnt, nov, aff = env.run_explosion_delta([(rx, ry)], boxes, tnts, ov)
                if len(nb) < len(env.plates):
                    continue
                if nov == ov and nb == boxes and ntnt == tnts:
                    continue
                breaks_major = False
                breaks_spring = False
                opened_pts = []
                for (ax, ay) in aff:
                    bt = env.tile_at(geom_ov, ax, ay)
                    if bt in SPRING_DIRS:
                        breaks_spring = True
                    if bt in ALL_LASER_DIRS or (ax, ay) in tnts or bt in ("R_GATE", "B_GATE"):
                        breaks_major = True
                        opened_pts.append((ax, ay))
                    elif bt in ("W", "MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW"):
                        for ndx, ndy in DIRECTIONS.values():
                            nx, ny = ax + ndx, ay + ndy
                            if _in_bounds(nx, ny):
                                nt_t = env.tile_at(geom_ov, nx, ny)
                                if nt_t not in ("T_W", "W"):
                                    rv = reached.get((nx, ny))
                                    if rv is None or rv[2][3] > 0:
                                        opened_pts.append((nx, ny))
                if breaks_spring and not breaks_major:
                    continue
                if not breaks_major and not opened_pts:
                    continue
                sig_blast = (nb, ntnt, nov)
                gd = min((abs(ox - gx) + abs(oy - gy) for ox, oy in opened_pts for gx, gy in agoals), default=20)
                pre_score = dt + (0 if breaks_major else 6) + 1.5 * gd
                if sig_blast not in best_blast or pre_score < best_blast[sig_blast][0]:
                    best_blast[sig_blast] = (pre_score, rx, ry, dt, dmg, pst, tb, nb, ntnt, nov, aff)

            pre_cands = sorted(best_blast.values(), key=lambda z: z[0])
            cands_b = []
            for pre_score, rx, ry, dt, dmg, pst, tb, nb, ntnt, nov, aff in pre_cands[:12]:
                if time.perf_counter() > deadline:
                    break
                evade_q = collections.deque([(rx, ry, tb, [])])
                evade_seen = {(rx, ry, 0)}
                evade_res = None
                while evade_q:
                    ux, uy, ut, ep = evade_q.popleft()
                    step_b = len(ep)
                    if step_b == 2:
                        if (ux, uy) not in aff:
                            evade_res = (ux, uy, ep)
                            break
                        continue
                    nt_b = ut + 1
                    for a in ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT"):
                        sim = env.sim_step(geom, boxes, tnts, gf, keys, ux, uy, a)
                        if sim is None or sim["flips"] or sim["cracks"] or sim["heal"]:
                            continue
                        if env.exposed_damage(geom, nt_b, sim["exposed"]) > 0:
                            continue
                        ex, ey = sim["end"]
                        if (ex, ey, step_b + 1) not in evade_seen:
                            evade_seen.add((ex, ey, step_b + 1))
                            evade_q.append((ex, ey, nt_b, ep + [a]))
                if evade_res is not None:
                    ex, ey, ep = evade_res
                    add_a = env.reconstruct(bfs["parent"], pst) + ["BOMB"] + ep
                    cands_b.append((pre_score,
                                    (ex, ey, nb, ntnt, nov, gf, keys, hp - dmg, jmp - sum(1 for a in add_a if a.startswith("JUMP_")), bmb - 1, thr),
                                    add_a, dt + 3, hp - dmg))
            cands_b.sort(key=lambda z: z[0])
            for _, b_node, b_acts, b_dt, b_hp in cands_b[:2]:
                push_macro(b_node, b_acts, b_dt, b_hp, bonus=-1.0)

    return best_partial[-1]


def decide_action(state: dict, memory: dict) -> str:
    turn = state["turn"]
    if "plan" not in memory:
        memory["plan"] = []
        memory["plan_idx"] = 0

    plan = memory["plan"]
    idx = memory["plan_idx"]

    if idx >= len(plan):
        budget = 1.45 if turn == 1 else 0.32
        plan = solve_full_plan(state, time_budget=budget)
        memory["plan"] = plan
        memory["plan_idx"] = 0
        idx = 0

    if idx < len(plan):
        act = plan[idx]
        memory["plan_idx"] = idx + 1
        return act

    # Lightweight safe fallback if completely trapped/stalled
    env = FullWorldEnv(state)
    hx, hy = state["hero"]["x"], state["hero"]["y"]
    hp = state["hero"]["hp"]
    gf = bool(state["gates_flipped"])
    geom = env.get_geom(env.init_boxes, env.init_tnts, (), gf)
    if env.exposed_damage(geom, turn, frozenset(((hx, hy),))) == 0:
        return "WAIT"
    for d in DIR_NAMES:
        a = f"MOVE_{d}"
        sim = env.sim_step(geom, env.init_boxes, env.init_tnts, gf, 0, hx, hy, a)
        if sim is not None and env.exposed_damage(geom, turn, sim["exposed"]) < hp:
            return a
    return "WAIT"
