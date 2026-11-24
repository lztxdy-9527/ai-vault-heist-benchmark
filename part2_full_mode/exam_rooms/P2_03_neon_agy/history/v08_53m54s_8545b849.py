"""
Dungeon Vault Attack and Defense — Part 2 (v2.2 FULL Mode) Submission.
Implements build_dungeon() and decide_action(state, memory).
Zero dunder identifiers, pure Python stdlib (collections, heapq, time).
"""

import collections
import heapq
import time

GRID_WIDTH = 40
GRID_HEIGHT = 26
GRID_SIZE = GRID_WIDTH * GRID_HEIGHT
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
DIR_DELTAS = (("R", 1, 0, 1), ("D", 0, 1, 40), ("U", 0, -1, -40), ("L", -1, 0, -1))
DIR_LIST = ("R", "D", "U", "L")

MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}

LASER1_TILES = frozenset({"LASER_U", "LASER_D", "LASER_L", "LASER_R"})
LASER2_TILES = frozenset({"LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R"})
ALL_LASER_TILES = LASER1_TILES | LASER2_TILES
ONEWAY_TILES = frozenset({"ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R"})
SPRING_TILES = frozenset({"SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R"})
HIGH_WALL_STATIC = frozenset({"W", "T_W"}) | ALL_LASER_TILES
PORTAL_PAIRS = {
    "PORTAL_1A": "PORTAL_1B", "PORTAL_1B": "PORTAL_1A",
    "PORTAL_2A": "PORTAL_2B", "PORTAL_2B": "PORTAL_2A",
}
DESTROY_TO_EMPTY = frozenset({
    "W", "ICE",
    "MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW",
    "SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R",
    "LASER_U", "LASER_D", "LASER_L", "LASER_R",
    "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R",
    "SWITCH", "R_GATE", "B_GATE", "HEAL", "MIMIC",
})
SIMPLE_WALK_TILES = frozenset({
    "EMPTY", "PLATE", "ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R",
    "R_GATE", "B_GATE", "P_GATE",
})
MECH_TILES = frozenset({
    "ICE", "MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW",
    "SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R",
    "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
})


# ==============================================================================
# Part 1: v2.2 Demon Dungeon Builder ("Neon Sovereign Vault")
# ==============================================================================

def build_dungeon() -> dict:
    """
    Construct a 2890G anti-FULL 5-act interlocking v2.2 dungeon:
    1) Dual coupled Spring-Stopper Sokoban puzzles with 3-sided titanium greedy-trap pockets (4 PLATE, 4 BOX).
    2) Hidden bank-shot THROW_U SWITCH vault behind ONEWAY_D + MIRROR_NW + ICE.
    3) K1 & K2 vaults gated by P_GATE + R_GATE/B_GATE + unavoidable SPRING->MIMIC (-90 HP total -> 10 HP)
       + 2 mandatory BOMBs + ONEWAY exits.
    4) Final 10-HP V gauntlet requiring BOX_5 pit-bridge + all 3 JUMPs + 12-beat dual-period crossfire.
    5) Mid-field Turn-8 Blue + Turn-9 Red inescapable ICE guillotine (Spawn 4-turn fairness 8/8 safe).
    """
    grid = [
        [
            "T_W" if (x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1) else "EMPTY"
            for x in range(GRID_WIDTH)
        ]
        for y in range(GRID_HEIGHT)
    ]

    # Act 1A: Upper Coupled Spring-Stopper (PLATE_1(6,5), stopper(7,5), pocket PLATE_2(7,1))
    grid[4][6] = "T_W"
    grid[6][6] = "T_W"
    grid[5][8] = "T_W"
    grid[5][4] = "SPRING_R"
    grid[5][5] = "PIT"
    grid[5][6] = "PLATE"
    grid[5][2] = "BOX"
    grid[3][7] = "BOX"
    grid[1][6] = "T_W"
    grid[1][7] = "PLATE"
    grid[1][8] = "T_W"

    # Act 1B: Lower Coupled Spring-Stopper (PLATE_3(6,20), stopper(7,20), pocket PLATE_4(7,24))
    grid[19][6] = "T_W"
    grid[21][6] = "T_W"
    grid[20][8] = "T_W"
    grid[20][4] = "SPRING_R"
    grid[20][5] = "PIT"
    grid[20][6] = "PLATE"
    grid[20][2] = "BOX"
    grid[22][7] = "BOX"
    grid[24][6] = "T_W"
    grid[24][7] = "PLATE"
    grid[24][8] = "T_W"

    # Act 2: Hidden Bank-Shot THROW_U SWITCH Vault (y=1..2, x=9..16)
    grid[1][9] = "T_W"
    grid[1][10] = "SWITCH"
    grid[1][11] = "ICE"
    grid[1][12] = "ICE"
    grid[1][13] = "EMPTY"
    grid[1][14] = "EMPTY"
    grid[1][15] = "MIRROR_NW"
    for x in range(10, 15):
        grid[2][x] = "T_W"
    grid[2][15] = "ONEWAY_D"

    # Act 3: K1 Vault (y=1..3, x=16..25) — P_GATE + R_GATE + Unavoidable SPRING->MIMIC #1 + BOMB #2
    grid[1][16] = "T_W"
    grid[1][17] = "SPRING_R"
    grid[1][18] = "PIT"
    grid[1][19] = "EMPTY"
    grid[1][20] = "MIMIC"
    grid[1][21] = "EMPTY"
    grid[1][22] = "EMPTY"
    grid[1][23] = "W"
    grid[1][24] = "EMPTY"
    grid[1][25] = "T_W"
    grid[2][16] = "T_W"
    grid[2][17] = "R_GATE"
    for x in range(18, 24):
        grid[2][x] = "T_W"
    grid[2][24] = "K1"
    grid[2][25] = "T_W"
    grid[3][17] = "P_GATE"
    grid[3][24] = "ONEWAY_D"

    # Act 4: K2 Vault (y=22..24, x=16..25) — P_GATE + B_GATE + Unavoidable SPRING->MIMIC #2 + BOMB #1
    grid[24][16] = "T_W"
    grid[24][17] = "SPRING_R"
    grid[24][18] = "PIT"
    grid[24][19] = "EMPTY"
    grid[24][20] = "MIMIC"
    grid[24][21] = "EMPTY"
    grid[24][22] = "EMPTY"
    grid[24][23] = "W"
    grid[24][24] = "EMPTY"
    grid[24][25] = "T_W"
    grid[23][16] = "T_W"
    grid[23][17] = "B_GATE"
    for x in range(18, 24):
        grid[23][x] = "T_W"
    grid[23][24] = "K2"
    grid[23][25] = "T_W"
    grid[22][17] = "P_GATE"
    grid[22][24] = "ONEWAY_U"

    # Act 5: Final 10-HP Gauntlet to V(35,13) — BOX_5 pit bridge + 3 JUMPs + 12-beat crossfire
    grid[13][25] = "BOX"
    for x in (29, 30, 32, 33, 34, 35):
        grid[12][x] = "T_W"
        grid[14][x] = "T_W"
    grid[13][36] = "T_W"
    grid[12][31] = "ONEWAY_U"
    grid[14][31] = "ONEWAY_D"
    grid[13][27] = "PIT"
    grid[13][28] = "PIT"
    grid[13][29] = "ONEWAY_R"
    grid[13][30] = "P_GATE"
    grid[13][31] = "EMPTY"
    grid[13][32] = "PIT"
    grid[13][33] = "EMPTY"
    grid[13][34] = "PIT"
    grid[13][35] = "V"
    grid[7][31] = "LASER_D"
    grid[19][31] = "LASER2_U"

    # Act 6: Mid-Field Turn-8 Blue + Turn-9 Red Inescapable ICE Guillotine
    grid[13][10] = "ICE"
    grid[13][11] = "ICE"
    grid[13][12] = "ICE"
    grid[6][13] = "LASER_D"
    grid[20][13] = "LASER2_U"

    # Exact 183-step verified author_solution (clears on step 183 with 10 HP)
    author_solution = (
        # 1. Upper Coupled Spring-Stopper (PLATE_1 + PLATE_2)
        ["MOVE_L"]
        + ["MOVE_U"] * 11
        + ["MOVE_R"] * 6
        + ["MOVE_D"] * 2
        + ["MOVE_U"] * 2
        + ["MOVE_L"] * 6
        + ["MOVE_D"] * 3
        + ["MOVE_R"] * 2
        + ["MOVE_D"] * 2
        + ["MOVE_R"] * 4
        + ["MOVE_U"] * 5
        # 2. Lower Coupled Spring-Stopper (PLATE_3 + PLATE_4)
        + ["MOVE_R"] * 2
        + ["MOVE_D"] * 21
        + ["MOVE_L"] * 2
        + ["MOVE_U"] * 2
        + ["MOVE_D"] * 2
        + ["MOVE_L"] * 6
        + ["MOVE_U"] * 3
        + ["MOVE_R"] * 2
        + ["MOVE_U"] * 2
        + ["MOVE_R"] * 4
        + ["MOVE_D"] * 5
        # 3. K2 Vault (B_GATE open, MIMIC #1 -> 55 HP, BOMB #1)
        + ["MOVE_U"] * 2
        + ["MOVE_R"] * 10
        + ["MOVE_D"] * 3
        + ["MOVE_R"] * 2
        + ["BOMB"]
        + ["MOVE_L"] * 2
        + ["MOVE_R"] * 4
        + ["MOVE_U"] * 3
        # 4. Bank-Shot THROW_U at (15,4) -> flips SWITCH(10,1)
        + ["MOVE_L"] * 9
        + ["MOVE_U"] * 17
        + ["THROW_U"]
        # 5. K1 Vault (R_GATE open, MIMIC #2 -> 10 HP, BOMB #2)
        + ["MOVE_R"] * 2
        + ["MOVE_U"] * 3
        + ["MOVE_R"] * 2
        + ["BOMB"]
        + ["MOVE_L"] * 2
        + ["MOVE_R"] * 4
        + ["MOVE_D"] * 3
        # 6. Final 10-HP Gauntlet (BOX_5 pit bridge + 3 JUMPs + 12-beat crossfire -> V)
        + ["MOVE_D"] * 9
        + ["MOVE_R"] * 3
        + ["JUMP_R"]
        + ["MOVE_R"]
        + ["MOVE_R"]
        + ["JUMP_R"]
        + ["JUMP_R"]
    )

    return {
        "taunt": "双挡板锁金门，残血斩双频！",
        "grid": grid,
        "author_solution": author_solution,
    }


# ==============================================================================
# Part 2: v2.2 FULL-Mode Championship Hero Solver
# ==============================================================================

def _in_bounds(x: int, y: int) -> bool:
    return 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT


def _classify_chests_exact(obs_terrain, clues):
    """Exact CSP solver over FULL-mode clues to classify CHESTs into MIMIC vs HEAL."""
    chests = []
    for y in range(1, GRID_HEIGHT - 1):
        for x in range(1, GRID_WIDTH - 1):
            if obs_terrain[y][x] == "CHEST":
                chests.append((x, y))
    if not chests:
        return set(), set()

    possible_mimics = []
    confirmed_heals = set()
    for cx, cy in chests:
        can_be_mimic = True
        for dx, dy in DIRECTIONS.values():
            nx, ny = cx + dx, cy + dy
            if _in_bounds(nx, ny) and not clues[ny][nx]:
                can_be_mimic = False
                break
        if can_be_mimic:
            possible_mimics.append((cx, cy))
        else:
            confirmed_heals.add((cx, cy))

    clue_cells = set()
    for cx, cy in possible_mimics:
        for dx, dy in DIRECTIONS.values():
            nx, ny = cx + dx, cy + dy
            if _in_bounds(nx, ny) and clues[ny][nx]:
                clue_cells.add((nx, ny))

    n = len(possible_mimics)
    cov = []
    for cx, cy in possible_mimics:
        s = set()
        for dx, dy in DIRECTIONS.values():
            nx, ny = cx + dx, cy + dy
            if (nx, ny) in clue_cells:
                s.add((nx, ny))
        cov.append(s)

    valid_masks = []
    if n <= 12:
        for mask in range(1 << n):
            if mask.bit_count() > 4:
                continue
            covered = set()
            for i in range(n):
                if mask & (1 << i):
                    covered |= cov[i]
            if covered == clue_cells:
                valid_masks.append(mask)

    mimics = set()
    heals = set(confirmed_heals)
    if valid_masks:
        always_on = valid_masks[0]
        always_off = (~valid_masks[0]) & ((1 << n) - 1)
        for m in valid_masks[1:]:
            always_on &= m
            always_off &= (~m) & ((1 << n) - 1)
        for i, pos in enumerate(possible_mimics):
            if always_on & (1 << i):
                mimics.add(pos)
            elif always_off & (1 << i):
                heals.add(pos)
            else:
                mimics.add(pos)
    else:
        for pos in possible_mimics:
            mimics.add(pos)
    return mimics, heals


class FastWorld:
    """Compact bitmask exact v2.2 physics engine + Macro-Action A* solver (no dunders)."""

    def build_from_state(self, state):
        obs_t = state["terrain"]
        obs_o = state["occupant"]
        clues = state["clues"]
        mimics, heals = _classify_chests_exact(obs_t, clues)

        self.base = [row[:] for row in obs_t]
        for mx, my in mimics:
            self.base[my][mx] = "MIMIC"
        for hx, hy in heals:
            self.base[hy][hx] = "HEAL"

        self.base_flat = [self.base[y][x] for y in range(GRID_HEIGHT) for x in range(GRID_WIDTH)]
        self.plates = []
        self.pgates = []
        self.switches = []
        self.portals = {}
        self.lasers = []
        self.crack_bit = {}
        self.crack_cells = []
        self.pit_bit = {}
        self.pit_cells = []
        self.destr_bit = {}
        self.destr_cells = []
        self.heals = []
        self.mimics = []
        self.init_tnt_set = set()

        c_cnt = p_cnt = d_cnt = 0
        init_boxes = []
        init_tnts = []

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                t = self.base[y][x]
                occ = obs_o[y][x]
                if occ == "BOX":
                    init_boxes.append((x, y))
                elif occ == "TNT":
                    init_tnts.append((x, y))
                    self.init_tnt_set.add((x, y))

                if t == "PLATE":
                    self.plates.append((x, y))
                elif t == "P_GATE":
                    self.pgates.append((x, y))
                elif t == "SWITCH":
                    self.switches.append((x, y))
                elif t in PORTAL_PAIRS:
                    self.portals[t] = (x, y)
                elif t == "CRACK":
                    bit = 1 << c_cnt
                    self.crack_bit[(x, y)] = bit
                    self.crack_cells.append((x, y, y * 40 + x, bit))
                    c_cnt += 1
                    dbit = 1 << d_cnt
                    self.destr_bit[(x, y)] = dbit
                    self.destr_cells.append((x, y, y * 40 + x, dbit))
                    d_cnt += 1
                elif t == "PIT":
                    bit = 1 << p_cnt
                    self.pit_bit[(x, y)] = bit
                    self.pit_cells.append((x, y, y * 40 + x, bit))
                    p_cnt += 1
                elif t == "HEAL":
                    self.heals.append((x, y))
                elif t == "MIMIC":
                    self.mimics.append((x, y))

                if t in DESTROY_TO_EMPTY or t in ("K1", "K2"):
                    if (x, y) not in self.destr_bit:
                        dbit = 1 << d_cnt
                        self.destr_bit[(x, y)] = dbit
                        self.destr_cells.append((x, y, y * 40 + x, dbit))
                        d_cnt += 1

                if t in LASER1_TILES:
                    self.lasers.append((x, y, 3, t[-1], self.destr_bit[(x, y)]))
                elif t in LASER2_TILES:
                    self.lasers.append((x, y, 4, t[-1], self.destr_bit[(x, y)]))

        self.plates_tuple = tuple(self.plates)
        self.plates_set = frozenset(self.plates)
        self.has_lasers = len(self.lasers) > 0
        self.targets = state["targets"]
        self.k1_pos = tuple(self.targets["K1"])
        self.k2_pos = tuple(self.targets["K2"])
        self.v_pos = tuple(self.targets["V"])

        self.laser_cache = {}
        self._precompute_static()
        return self.state_from_obs(state)

    def state_from_obs(self, state):
        hero = state["hero"]
        obs_t = state["terrain"]
        obs_o = state["occupant"]
        kmask = (1 if hero["keys"][0] else 0) | (2 if hero["keys"][1] else 0)

        boxes = []
        tnts = []
        crack_m = 0
        pit_m = 0
        destr_m = 0
        for y in range(1, GRID_HEIGHT - 1):
            for x in range(1, GRID_WIDTH - 1):
                occ = obs_o[y][x]
                if occ == "BOX":
                    boxes.append((x, y))
                elif occ == "TNT":
                    tnts.append((x, y))
                bt = self.base[y][x]
                ct = obs_t[y][x]
                if bt == "CRACK":
                    if ct == "PIT":
                        crack_m |= self.crack_bit[(x, y)]
                    elif ct == "EMPTY":
                        destr_m |= self.destr_bit[(x, y)]
                elif bt == "PIT":
                    if ct == "EMPTY":
                        pit_m |= self.pit_bit[(x, y)]
                elif bt in DESTROY_TO_EMPTY or bt in ("K1", "K2"):
                    if ct == "EMPTY":
                        destr_m |= self.destr_bit[(x, y)]

        if hero["keys"][0] and self.k1_pos in self.destr_bit:
            destr_m |= self.destr_bit[self.k1_pos]
        if hero["keys"][1] and self.k2_pos in self.destr_bit:
            destr_m |= self.destr_bit[self.k2_pos]
        active_bombs = tuple((b["x"], b["y"], b["timer"]) for b in state.get("bombs", []))

        return (
            hero["x"], hero["y"], hero["hp"], kmask,
            bool(state.get("gates_flipped", False)),
            hero["jumps"], hero["throws"], hero["bombs"],
            tuple(sorted(boxes)),
            tuple(sorted(tnts)),
            crack_m, pit_m, destr_m,
            active_bombs,
            state["turn"],
        )

    def _precompute_static(self):
        def bfs_dist(target_xy):
            dist = [[999] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
            tx, ty = target_xy
            dist[ty][tx] = 0
            q = collections.deque([(tx, ty)])
            while q:
                x, y = q.popleft()
                nd = dist[y][x] + 1
                cur_t = self.base[y][x]
                for d, (dx, dy) in DIRECTIONS.items():
                    if cur_t in ONEWAY_TILES and cur_t[-1] != d:
                        continue
                    px, py = x - dx, y - dy
                    if _in_bounds(px, py) and dist[py][px] > nd:
                        if self.base[py][px] == "T_W":
                            continue
                        dist[py][px] = nd
                        q.append((px, py))
                if cur_t in PORTAL_PAIRS:
                    pp = self.portals.get(PORTAL_PAIRS[cur_t])
                    if pp and dist[pp[1]][pp[0]] > nd:
                        dist[pp[1]][pp[0]] = nd
                        q.append(pp)
            return dist

        self.dist_k1 = bfs_dist(self.k1_pos)
        self.dist_k2 = bfs_dist(self.k2_pos)
        self.dist_v = bfs_dist(self.v_pos)

        def box_rev_dist(plate_xy):
            dist = [[999] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
            px0, py0 = plate_xy
            dist[py0][px0] = 0
            q = collections.deque([(px0, py0)])
            while q:
                x, y = q.popleft()
                nd = dist[y][x] + 1
                cur_t = self.base[y][x]
                for d, (dx, dy) in DIRECTIONS.items():
                    if cur_t in ONEWAY_TILES and cur_t[-1] != d:
                        continue
                    bx, by = x - dx, y - dy
                    hx, hy = x - 2 * dx, y - 2 * dy
                    if _in_bounds(bx, by) and _in_bounds(hx, hy):
                        bt = self.base[by][bx]
                        ht = self.base[hy][hx]
                        if bt not in ("T_W", "PIT", "K1", "K2", "V") and ht not in ("T_W", "PIT"):
                            if not (bt in ONEWAY_TILES and bt[-1] != d):
                                if dist[by][bx] > nd:
                                    dist[by][bx] = nd
                                    q.append((bx, by))
                for d, (dx, dy) in DIRECTIONS.items():
                    if cur_t in ONEWAY_TILES and cur_t[-1] != d:
                        continue
                    ix, iy = x - dx, y - dy
                    while _in_bounds(ix, iy) and self.base[iy][ix] == "ICE":
                        if dist[iy][ix] > nd:
                            dist[iy][ix] = nd
                            q.append((ix, iy))
                        px, py = ix - dx, iy - dy
                        hx, hy = ix - 2 * dx, iy - 2 * dy
                        if _in_bounds(px, py) and _in_bounds(hx, hy):
                            if self.base[py][px] not in ("T_W", "PIT", "K1", "K2", "V") and self.base[hy][hx] not in ("T_W", "PIT"):
                                if dist[py][px] > nd:
                                    dist[py][px] = nd
                                    q.append((px, py))
                        ix -= dx
                        iy -= dy
                for d, (dx, dy) in DIRECTIONS.items():
                    mx, my = x - dx, y - dy
                    if _in_bounds(mx, my) and self.base[my][mx] in MIRROR_MAP:
                        if d in MIRROR_MAP[self.base[my][mx]].values():
                            if dist[my][mx] > nd:
                                dist[my][mx] = nd
                                q.append((mx, my))
                for d, (dx, dy) in DIRECTIONS.items():
                    sname = f"SPRING_{d}"
                    for k in (1, 2, 3):
                        sx, sy = x - k * dx, y - k * dy
                        if _in_bounds(sx, sy) and self.base[sy][sx] == sname:
                            if dist[sy][sx] > nd:
                                dist[sy][sx] = nd
                                q.append((sx, sy))
                if cur_t in PORTAL_PAIRS:
                    pp = self.portals.get(PORTAL_PAIRS[cur_t])
                    if pp and dist[pp[1]][pp[0]] > nd:
                        dist[pp[1]][pp[0]] = nd
                        q.append(pp)
            return dist

        self.dist_plates = [box_rev_dist(p) for p in self.plates]

        self.stopper_for_plate = {}
        self.stopper_required_plates = set()
        self.pocket_plates = set()
        for pi, (px, py) in enumerate(self.plates):
            open_dirs = 0
            for d, (dx, dy) in DIRECTIONS.items():
                nx, ny = px + dx, py + dy
                if _in_bounds(nx, ny) and self.base[ny][nx] not in ("T_W", "PIT"):
                    open_dirs += 1
            if open_dirs == 1:
                self.pocket_plates.add(pi)

            can_normal_push = False
            for d, (dx, dy) in DIRECTIONS.items():
                bx, by = px - dx, py - dy
                hx, hy = px - 2 * dx, py - 2 * dy
                if _in_bounds(bx, by) and _in_bounds(hx, hy):
                    if self.base[by][bx] not in ("T_W", "PIT") and self.base[hy][hx] not in ("T_W", "PIT"):
                        can_normal_push = True
                        break
            for d, (dx, dy) in DIRECTIONS.items():
                sname = f"SPRING_{d}"
                is_traj = False
                for k in (1, 2):
                    bx, by = px - k * dx, py - k * dy
                    if _in_bounds(bx, by) and self.base[by][bx] == sname:
                        is_traj = True
                        break
                if not is_traj:
                    bx, by = px - dx, py - dy
                    if _in_bounds(bx, by) and self.base[by][bx] == "ICE":
                        is_traj = True
                if is_traj:
                    sx, sy = px + dx, py + dy
                    if _in_bounds(sx, sy) and self.base[sy][sx] not in ("T_W", "PIT"):
                        self.stopper_for_plate[(sx, sy)] = pi
                        if not can_normal_push:
                            self.stopper_required_plates.add(pi)

        # Admissible 0-1 BFS lower bound on PITs/JUMPs to reach V
        self.min_pits_to_v = [[99] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        vx, vy = self.v_pos
        self.min_pits_to_v[vy][vx] = 0
        dq = collections.deque([(vx, vy)])
        while dq:
            x, y = dq.popleft()
            cd = self.min_pits_to_v[y][x]
            cur_t = self.base[y][x]
            for d, (dx, dy) in DIRECTIONS.items():
                if cur_t in ONEWAY_TILES and cur_t[-1] != d:
                    continue
                px, py = x - dx, y - dy
                if _in_bounds(px, py) and self.base[py][px] not in ("T_W", "PIT"):
                    if self.min_pits_to_v[py][px] > cd:
                        self.min_pits_to_v[py][px] = cd
                        dq.appendleft((px, py))
                px2, py2 = x - 2 * dx, y - 2 * dy
                if _in_bounds(px2, py2) and _in_bounds(px, py):
                    if self.base[py2][px2] not in ("T_W", "PIT") and self.base[py][px] == "PIT":
                        sc = 0 if self.base[py2][px2] in SPRING_TILES else 1
                        if self.min_pits_to_v[py2][px2] > cd + sc:
                            self.min_pits_to_v[py2][px2] = cd + sc
                            if sc == 0:
                                dq.appendleft((px2, py2))
                            else:
                                dq.append((px2, py2))
                px3, py3 = x - 3 * dx, y - 3 * dy
                if _in_bounds(px3, py3) and self.base[py3][px3] in SPRING_TILES:
                    if self.min_pits_to_v[py3][px3] > cd:
                        self.min_pits_to_v[py3][px3] = cd
                        dq.appendleft((px3, py3))
            if cur_t in PORTAL_PAIRS:
                pp = self.portals.get(PORTAL_PAIRS[cur_t])
                if pp is not None and self.min_pits_to_v[pp[1]][pp[0]] > cd:
                    self.min_pits_to_v[pp[1]][pp[0]] = cd
                    dq.appendleft(pp)

        # Static dead box cells
        self.dead_box_cells = set()
        if self.plates:
            safe_special = set(self.plates_set)
            for lx, ly, _, d, _ in self.lasers:
                dx, dy = DIRECTIONS[d]
                for dist in range(1, 11):
                    rx, ry = lx + dist * dx, ly + dist * dy
                    if not _in_bounds(rx, ry) or self.base[ry][rx] == "T_W":
                        break
                    safe_special.add((rx, ry))
            for y in range(1, GRID_HEIGHT - 1):
                for x in range(1, GRID_WIDTH - 1):
                    t = self.base[y][x]
                    if t in MECH_TILES or t in ("PLATE", "SWITCH"):
                        for dy in (-1, 0, 1):
                            for dx in (-1, 0, 1):
                                safe_special.add((x + dx, y + dy))
            for y in range(1, GRID_HEIGHT - 1):
                for x in range(1, GRID_WIDTH - 1):
                    if (x, y) in safe_special:
                        continue
                    if self.base[y][x] in ("T_W", "PIT", "PLATE", "SWITCH"):
                        continue
                    def hb(nx, ny, pd):
                        if not _in_bounds(nx, ny):
                            return True
                        nt = self.base[ny][nx]
                        if nt in ("T_W", "K1", "K2", "V"):
                            return True
                        if nt in ONEWAY_TILES and nt[-1] != pd:
                            return True
                        return False
                    if (hb(x, y - 1, "U") or hb(x, y + 1, "D")) and (hb(x - 1, y, "L") or hb(x + 1, y, "R")):
                        self.dead_box_cells.add((x, y))

        # Blocking MIMICs (corridor/chokepoint)
        self.blocking_mimics = set()
        for mx, my in self.mimics:
            blk = 0
            for dx, dy in DIRECTIONS.values():
                nx, ny = mx + dx, my + dy
                if not _in_bounds(nx, ny):
                    blk += 1
                else:
                    nt = self.base[ny][nx]
                    if nt in ("T_W", "W", "PIT") or nt in ALL_LASER_TILES or nt in ONEWAY_TILES or nt in SPRING_TILES or nt in PORTAL_PAIRS:
                        blk += 1
            if blk >= 2:
                self.blocking_mimics.add((mx, my))

        self.throw_candidates = collections.defaultdict(list)
        if self.switches or self.blocking_mimics or self.init_tnt_set:
            for y in range(1, GRID_HEIGHT - 1):
                for x in range(1, GRID_WIDTH - 1):
                    t = self.base[y][x]
                    if t in ("T_W", "PIT"):
                        continue
                    for d in DIR_LIST:
                        if self._static_throw_hits(x, y, d):
                            self.throw_candidates[(x, y)].append(d)

        self.bomb_candidates = set()
        for y in range(1, GRID_HEIGHT - 1):
            for x in range(1, GRID_WIDTH - 1):
                t = self.base[y][x]
                if t in ("T_W", "PIT") or t in ALL_LASER_TILES:
                    continue
                for dy in (-1, 0, 1):
                    found = False
                    for dx in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if _in_bounds(nx, ny):
                            nt = self.base[ny][nx]
                            if nt in DESTROY_TO_EMPTY or (nx, ny) in self.init_tnt_set or nt == "PLATE":
                                found = True
                                break
                    if found:
                        self.bomb_candidates.add((x, y))
                        break

    def _static_throw_hits(self, sx, sy, d):
        cd = d
        x, y = sx, sy
        rng = 6
        sp = 0
        while rng > 0:
            dx, dy = DIRECTIONS[cd]
            x, y = x + dx, y + dy
            rng -= 1
            if not _in_bounds(x, y):
                return False
            t = self.base[y][x]
            if t == "T_W":
                return False
            if t == "SWITCH" or (x, y) in self.blocking_mimics or (x, y) in self.init_tnt_set:
                return True
            if t in MIRROR_MAP:
                cd = MIRROR_MAP[t][cd]
            elif t in PORTAL_PAIRS and sp < 2:
                pp = self.portals.get(PORTAL_PAIRS[t])
                if pp:
                    x, y = pp
                    sp += 1
                    if sp == 2:
                        return False
        t6 = self.base[y][x]
        if t6 == "ICE" or t6 in MIRROR_MAP:
            for _ in range(32):
                dx, dy = DIRECTIONS[cd]
                x, y = x + dx, y + dy
                if not _in_bounds(x, y):
                    return False
                t = self.base[y][x]
                if t == "T_W":
                    return False
                if t == "SWITCH" or (x, y) in self.blocking_mimics or (x, y) in self.init_tnt_set:
                    return True
                if t in MIRROR_MAP:
                    cd = MIRROR_MAP[t][cd]
                elif t == "ICE":
                    continue
                elif t in PORTAL_PAIRS and sp < 2:
                    pp = self.portals.get(PORTAL_PAIRS[t])
                    if pp:
                        x, y = pp
                        sp += 1
                        if sp == 2:
                            return False
                    else:
                        return False
                else:
                    return False
        return False

    def tile_at(self, x, y, crack_m, pit_m, destr_m):
        t = self.base[y][x]
        if t == "CRACK":
            if destr_m & self.destr_bit[(x, y)]:
                return "EMPTY"
            if crack_m & self.crack_bit[(x, y)]:
                return "PIT"
            return "CRACK"
        if t == "PIT":
            if pit_m & self.pit_bit[(x, y)]:
                return "EMPTY"
            return "PIT"
        bit = self.destr_bit.get((x, y))
        if bit and (destr_m & bit):
            return "EMPTY"
        return t

    def plates_active(self, boxes):
        if not self.plates_tuple:
            return False
        for p in self.plates_tuple:
            if p not in boxes:
                return False
        return True

    def is_high_wall(self, x, y, gf, p_act, crack_m, pit_m, destr_m):
        if not _in_bounds(x, y):
            return True
        t = self.tile_at(x, y, crack_m, pit_m, destr_m)
        if t in HIGH_WALL_STATIC:
            return True
        if t == "R_GATE" and not gf:
            return True
        if t == "B_GATE" and gf:
            return True
        if t == "P_GATE" and not p_act:
            return True
        return False

    def blocks_oneway(self, x, y, cur_dir):
        t = self.base[y][x]
        if t in ONEWAY_TILES:
            return t[-1] != cur_dir
        return False

    def get_laser_info(self, gf, boxes, tnts, destr_m):
        if not self.has_lasers:
            return None
        p_act = self.plates_active(boxes)
        key = (gf, p_act, boxes, tnts, destr_m)
        cached = self.laser_cache.get(key)
        if cached is not None:
            return cached

        red_arr = [0] * GRID_SIZE
        blue_arr = [0] * GRID_SIZE
        red_tnts = set()
        blue_tnts = set()
        box_set = set(boxes)
        tnt_set = set(tnts)
        haz_indices = set()

        for idx, (lx, ly, period, d, lbit) in enumerate(self.lasers):
            if destr_m & lbit:
                continue
            dx, dy = DIRECTIONS[d]
            cbit = 1 << idx
            arr = red_arr if period == 3 else blue_arr
            tset = red_tnts if period == 3 else blue_tnts
            for dist in range(1, 11):
                rx, ry = lx + dist * dx, ly + dist * dy
                if not _in_bounds(rx, ry):
                    break
                if self.is_high_wall(rx, ry, gf, p_act, 0, 0, destr_m):
                    break
                if (rx, ry) in box_set:
                    break
                if (rx, ry) in tnt_set:
                    tset.add((rx, ry))
                    break
                ridx = ry * 40 + rx
                arr[ridx] |= cbit
                haz_indices.add(ridx)

        res = (red_arr, blue_arr, red_tnts, blue_tnts, haz_indices)
        if len(self.laser_cache) < 25000:
            self.laser_cache[key] = res
        return res

    def step(self, st, action):
        (hx, hy, hp, kmask, gf, jumps, throws, bombs_left,
         boxes, tnts, crack_m, pit_m, destr_m, active_bombs, turn) = st

        if turn > MAX_TURNS:
            return None, "DEAD", 0

        box_set = set(boxes)
        tnt_set = set(tnts)
        exposed = {(hx, hy)}
        armed_tnts = set()
        bombs_list = list(active_bombs)
        dmg_taken = 0
        status = "RUNNING"

        def cur_p_act():
            if not self.plates_tuple:
                return False
            for p in self.plates_tuple:
                if p not in box_set:
                    return False
            return True

        def cur_hw(x, y):
            if not _in_bounds(x, y):
                return True
            t = self.tile_at(x, y, crack_m, pit_m, destr_m)
            if t in HIGH_WALL_STATIC:
                return True
            if t == "R_GATE" and not gf:
                return True
            if t == "B_GATE" and gf:
                return True
            if t == "P_GATE" and not cur_p_act():
                return True
            return False

        def can_box(x, y, d):
            if not _in_bounds(x, y) or cur_hw(x, y) or self.blocks_oneway(x, y, d):
                return False
            t = self.tile_at(x, y, crack_m, pit_m, destr_m)
            if t in ("K1", "K2", "V"):
                return False
            if (x, y) in box_set or (x, y) in tnt_set or (x, y) == (hx, hy):
                return False
            return True

        def can_hero(x, y, d):
            if not _in_bounds(x, y) or cur_hw(x, y) or self.blocks_oneway(x, y, d):
                return False
            if (x, y) in box_set or (x, y) in tnt_set:
                return False
            return True

        def displace_box(x0, y0, x1, y1, cur_dir):
            nonlocal gf, crack_m, pit_m, destr_m
            steps = 0
            p_cnt = 0
            sup = False
            while True:
                steps += 1
                if self.tile_at(x0, y0, crack_m, pit_m, destr_m) == "CRACK":
                    crack_m |= self.crack_bit[(x0, y0)]
                box_set.discard((x0, y0))
                box_set.add((x1, y1))
                t1 = self.tile_at(x1, y1, crack_m, pit_m, destr_m)
                if t1 == "PIT":
                    box_set.discard((x1, y1))
                    if self.base[y1][x1] == "PIT":
                        pit_m |= self.pit_bit[(x1, y1)]
                    else:
                        destr_m |= self.destr_bit[(x1, y1)]
                    break
                elif t1 == "MIMIC":
                    destr_m |= self.destr_bit[(x1, y1)]
                elif t1 == "SWITCH":
                    gf = not gf

                if steps >= 32:
                    break
                if sup:
                    sup = False
                    if p_cnt >= 2:
                        break
                    dx, dy = DIRECTIONS[cur_dir]
                    nx, ny = x1 + dx, y1 + dy
                    if can_box(nx, ny, cur_dir):
                        x0, y0, x1, y1 = x1, y1, nx, ny
                        continue
                    if _in_bounds(nx, ny) and (nx, ny) in tnt_set and not self.blocks_oneway(nx, ny, cur_dir):
                        armed_tnts.add((nx, ny))
                    break

                tc = self.tile_at(x1, y1, crack_m, pit_m, destr_m)
                if tc == "ICE":
                    dx, dy = DIRECTIONS[cur_dir]
                    nx, ny = x1 + dx, y1 + dy
                    if can_box(nx, ny, cur_dir):
                        x0, y0, x1, y1 = x1, y1, nx, ny
                        continue
                    if _in_bounds(nx, ny) and (nx, ny) in tnt_set and not self.blocks_oneway(nx, ny, cur_dir):
                        armed_tnts.add((nx, ny))
                    break
                elif tc in MIRROR_MAP:
                    cur_dir = MIRROR_MAP[tc][cur_dir]
                    dx, dy = DIRECTIONS[cur_dir]
                    nx, ny = x1 + dx, y1 + dy
                    if can_box(nx, ny, cur_dir):
                        x0, y0, x1, y1 = x1, y1, nx, ny
                        continue
                    if _in_bounds(nx, ny) and (nx, ny) in tnt_set and not self.blocks_oneway(nx, ny, cur_dir):
                        armed_tnts.add((nx, ny))
                    break
                elif tc in SPRING_TILES:
                    cur_dir = tc[-1]
                    dx, dy = DIRECTIONS[cur_dir]
                    blk = None
                    for k in (1, 2, 3):
                        pkx, pky = x1 + k * dx, y1 + k * dy
                        if not can_box(pkx, pky, cur_dir):
                            blk = k
                            if _in_bounds(pkx, pky) and (pkx, pky) in tnt_set and not self.blocks_oneway(pkx, pky, cur_dir):
                                armed_tnts.add((pkx, pky))
                            break
                    if blk == 1:
                        break
                    lk = (blk - 1) if blk is not None else 3
                    x0, y0, x1, y1 = x1, y1, x1 + lk * dx, y1 + lk * dy
                    continue
                elif tc in PORTAL_PAIRS:
                    pp = self.portals.get(PORTAL_PAIRS[tc])
                    if pp is None or pp in box_set or pp in tnt_set or pp == (hx, hy):
                        break
                    p_cnt += 1
                    sup = True
                    x0, y0, x1, y1 = x1, y1, pp[0], pp[1]
                    continue
                else:
                    break

        def displace_hero(x1, y1, cur_dir):
            nonlocal hx, hy, hp, kmask, gf, crack_m, destr_m, dmg_taken, status
            x0, y0 = hx, hy
            steps = 0
            p_cnt = 0
            sup = False
            stop_m = False
            while True:
                steps += 1
                if self.tile_at(x0, y0, crack_m, pit_m, destr_m) == "CRACK":
                    crack_m |= self.crack_bit[(x0, y0)]
                hx, hy = x1, y1
                exposed.add((hx, hy))
                t1 = self.tile_at(x1, y1, crack_m, pit_m, destr_m)
                if t1 == "PIT":
                    hp -= 100
                    dmg_taken += 100
                elif t1 == "MIMIC":
                    hp -= 45
                    dmg_taken += 45
                    destr_m |= self.destr_bit[(x1, y1)]
                    stop_m = True
                elif t1 == "HEAL":
                    hp = min(100, hp + 30)
                    destr_m |= self.destr_bit[(x1, y1)]
                elif t1 == "SWITCH":
                    gf = not gf

                if hp <= 0:
                    status = "DEAD"
                    return

                if t1 == "K1":
                    kmask |= 1
                    destr_m |= self.destr_bit[(x1, y1)]
                elif t1 == "K2":
                    kmask |= 2
                    destr_m |= self.destr_bit[(x1, y1)]
                elif t1 == "V" and kmask == 3 and hp > 0:
                    status = "CLEARED"
                    return

                if steps >= 32 or stop_m:
                    break
                if sup:
                    sup = False
                    if p_cnt >= 2:
                        break
                    dx, dy = DIRECTIONS[cur_dir]
                    nx, ny = x1 + dx, y1 + dy
                    if can_hero(nx, ny, cur_dir):
                        x0, y0, x1, y1 = x1, y1, nx, ny
                        continue
                    break

                tc = self.tile_at(x1, y1, crack_m, pit_m, destr_m)
                if tc == "ICE":
                    dx, dy = DIRECTIONS[cur_dir]
                    nx, ny = x1 + dx, y1 + dy
                    if can_hero(nx, ny, cur_dir):
                        x0, y0, x1, y1 = x1, y1, nx, ny
                        continue
                    break
                elif tc in MIRROR_MAP:
                    cur_dir = MIRROR_MAP[tc][cur_dir]
                    dx, dy = DIRECTIONS[cur_dir]
                    nx, ny = x1 + dx, y1 + dy
                    if can_hero(nx, ny, cur_dir):
                        x0, y0, x1, y1 = x1, y1, nx, ny
                        continue
                    break
                elif tc in SPRING_TILES:
                    cur_dir = tc[-1]
                    dx, dy = DIRECTIONS[cur_dir]
                    blk = None
                    for k in (1, 2, 3):
                        pkx, pky = x1 + k * dx, y1 + k * dy
                        if not can_hero(pkx, pky, cur_dir):
                            blk = k
                            break
                    if blk == 1:
                        break
                    lk = (blk - 1) if blk is not None else 3
                    x0, y0, x1, y1 = x1, y1, x1 + lk * dx, y1 + lk * dy
                    continue
                elif tc in PORTAL_PAIRS:
                    pp = self.portals.get(PORTAL_PAIRS[tc])
                    if pp is None or pp in box_set or pp in tnt_set:
                        break
                    p_cnt += 1
                    sup = True
                    x0, y0, x1, y1 = x1, y1, pp[0], pp[1]
                    continue
                else:
                    break

        if action == "WAIT":
            pass
        elif action == "BOMB":
            if bombs_left > 0 and not any(b[0] == hx and b[1] == hy for b in bombs_list):
                bombs_left -= 1
                bombs_list.append((hx, hy, 3))
        elif action.startswith("THROW_"):
            if throws > 0:
                throws -= 1
                sx, sy = hx, hy
                cd = action[-1]
                rng = 6
                sp = 0
                shat = False
                stop_p = False
                while rng > 0:
                    dx, dy = DIRECTIONS[cd]
                    sx, sy = sx + dx, sy + dy
                    rng -= 1
                    if not _in_bounds(sx, sy) or cur_hw(sx, sy) or (sx, sy) in box_set:
                        shat = True
                        break
                    if (sx, sy) in tnt_set:
                        armed_tnts.add((sx, sy))
                        shat = True
                        break
                    t = self.tile_at(sx, sy, crack_m, pit_m, destr_m)
                    if t == "SWITCH":
                        gf = not gf
                        shat = True
                        break
                    if t == "MIMIC":
                        destr_m |= self.destr_bit[(sx, sy)]
                        shat = True
                        break
                    if t in MIRROR_MAP:
                        cd = MIRROR_MAP[t][cd]
                    elif t in PORTAL_PAIRS and sp < 2:
                        pp = self.portals.get(PORTAL_PAIRS[t])
                        if pp is not None and pp not in box_set and pp not in tnt_set:
                            sx, sy = pp
                            sp += 1
                            if sp == 2:
                                stop_p = True
                                break
                if not shat and not stop_p and rng == 0:
                    t6 = self.tile_at(sx, sy, crack_m, pit_m, destr_m)
                    if t6 == "ICE" or t6 in MIRROR_MAP:
                        for _ in range(32):
                            dx, dy = DIRECTIONS[cd]
                            sx, sy = sx + dx, sy + dy
                            if not _in_bounds(sx, sy) or cur_hw(sx, sy) or (sx, sy) in box_set:
                                break
                            if (sx, sy) in tnt_set:
                                armed_tnts.add((sx, sy))
                                break
                            t = self.tile_at(sx, sy, crack_m, pit_m, destr_m)
                            if t == "SWITCH":
                                gf = not gf
                                break
                            if t == "MIMIC":
                                destr_m |= self.destr_bit[(sx, sy)]
                                break
                            if t in MIRROR_MAP:
                                cd = MIRROR_MAP[t][cd]
                            elif t == "ICE":
                                continue
                            elif t in PORTAL_PAIRS and sp < 2:
                                pp = self.portals.get(PORTAL_PAIRS[t])
                                if pp is not None and pp not in box_set and pp not in tnt_set:
                                    sx, sy = pp
                                    sp += 1
                                    if sp == 2:
                                        break
                                else:
                                    break
                            else:
                                break
        elif action.startswith("MOVE_"):
            d = action[-1]
            dx, dy = DIRECTIONS[d]
            p1x, p1y = hx + dx, hy + dy
            if _in_bounds(p1x, p1y) and not cur_hw(p1x, p1y) and not self.blocks_oneway(p1x, p1y, d):
                if (p1x, p1y) in box_set:
                    p2x, p2y = hx + 2 * dx, hy + 2 * dy
                    if can_box(p2x, p2y, d):
                        displace_box(p1x, p1y, p2x, p2y, d)
                        if can_hero(p1x, p1y, d):
                            displace_hero(p1x, p1y, d)
                    elif _in_bounds(p2x, p2y) and (p2x, p2y) in tnt_set and not self.blocks_oneway(p2x, p2y, d):
                        armed_tnts.add((p2x, p2y))
                elif (p1x, p1y) in tnt_set:
                    pass
                else:
                    displace_hero(p1x, p1y, d)
        elif action.startswith("JUMP_"):
            if jumps > 0:
                jumps -= 1
                d = action[-1]
                dx, dy = DIRECTIONS[d]
                p1x, p1y = hx + dx, hy + dy
                p2x, p2y = hx + 2 * dx, hy + 2 * dy
                p1_ok = _in_bounds(p1x, p1y) and not cur_hw(p1x, p1y) and not self.blocks_oneway(p1x, p1y, d)
                if p1_ok and can_hero(p2x, p2y, d):
                    displace_hero(p2x, p2y, d)

        if status != "RUNNING":
            ns = (hx, hy, hp, kmask, gf, jumps, throws, bombs_left,
                  tuple(sorted(box_set)), tuple(sorted(tnt_set)),
                  crack_m, pit_m, destr_m, tuple(bombs_list), turn + 1)
            return ns, status, dmg_taken

        def detonate(seeds):
            nonlocal hp, dmg_taken, crack_m, destr_m, status
            exploded = set()
            q = collections.deque(seeds)
            while q:
                ex, ey = q.popleft()
                if (ex, ey) in exploded:
                    continue
                exploded.add((ex, ey))
                tnt_set.discard((ex, ey))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = ex + dx, ey + dy
                        if not _in_bounds(nx, ny):
                            continue
                        if (nx, ny) == (hx, hy):
                            hp -= 60
                            dmg_taken += 60
                        box_set.discard((nx, ny))
                        if (nx, ny) in tnt_set:
                            tnt_set.discard((nx, ny))
                            if (nx, ny) not in exploded:
                                q.append((nx, ny))
                        nt = self.tile_at(nx, ny, crack_m, pit_m, destr_m)
                        if nt == "CRACK":
                            crack_m |= self.crack_bit[(nx, ny)]
                        elif nt in DESTROY_TO_EMPTY:
                            destr_m |= self.destr_bit[(nx, ny)]
            if hp <= 0:
                status = "DEAD"

        det_seeds = set(armed_tnts)
        next_bombs = []
        for bx, by, bt in bombs_list:
            bt -= 1
            if bt <= 0:
                det_seeds.add((bx, by))
            else:
                next_bombs.append((bx, by, bt))
        if det_seeds:
            detonate(det_seeds)
        if status != "RUNNING":
            return None, "DEAD", dmg_taken

        new_boxes = tuple(sorted(box_set))
        new_tnts = tuple(sorted(tnt_set))

        if self.has_lasers and (turn % 3 == 0 or turn % 4 == 0):
            red_arr, blue_arr, red_tnts, blue_tnts, _ = self.get_laser_info(gf, new_boxes, new_tnts, destr_m)
            hit_mask = 0
            ltnts = set()
            if turn % 3 == 0:
                ltnts |= red_tnts
                for ex, ey in exposed:
                    m = red_arr[ey * 40 + ex]
                    if m:
                        hit_mask |= m
            if turn % 4 == 0:
                ltnts |= blue_tnts
                for ex, ey in exposed:
                    m = blue_arr[ey * 40 + ex]
                    if m:
                        hit_mask |= m
            if hit_mask:
                hits = hit_mask.bit_count()
                hp -= 50 * hits
                dmg_taken += 50 * hits
                if hp <= 0:
                    return None, "DEAD", dmg_taken
            if ltnts:
                detonate(ltnts)
                if status != "RUNNING":
                    return None, "DEAD", dmg_taken
                new_boxes = tuple(sorted(box_set))
                new_tnts = tuple(sorted(tnt_set))

        ns = (hx, hy, hp, kmask, gf, jumps, throws, bombs_left,
              new_boxes, new_tnts, crack_m, pit_m, destr_m, tuple(next_bombs), turn + 1)
        return ns, "RUNNING", dmg_taken

    def _is_box_deadlocked(self, boxes):
        if not self.plates_tuple:
            return False
        alive = 0
        for b in boxes:
            if b in self.plates_set or b not in self.dead_box_cells:
                alive += 1
        return alive < len(self.plates_tuple)

    def _min_plate_matching(self, unfilled_idxs, free_boxes):
        nu = len(unfilled_idxs)
        nb = len(free_boxes)
        if nu == 0:
            return 0, 0
        if nb < nu:
            return 99999, 0
        costs = []
        for pi in unfilled_idxs:
            px, py = self.plates_tuple[pi]
            dp = self.dist_plates[pi]
            row = []
            for bx, by in free_boxes:
                d = dp[by][bx]
                if d >= 999:
                    d = 500 + abs(bx - px) + abs(by - py)
                row.append(d)
            costs.append(row)

        dp_m = {0: 0}
        for i in range(nu):
            ndp = {}
            crow = costs[i]
            for mask, val in dp_m.items():
                for bi in range(nb):
                    bit = 1 << bi
                    if not (mask & bit):
                        nmask = mask | bit
                        nv = val + crow[bi]
                        prev = ndp.get(nmask)
                        if prev is None or nv < prev:
                            ndp[nmask] = nv
            dp_m = ndp
        best_val = 999999
        best_mask = 0
        for mask, val in dp_m.items():
            if val < best_val:
                best_val = val
                best_mask = mask
        return best_val, best_mask

    def heuristic(self, st, plates_only=False):
        (hx, hy, hp, kmask, gf, jumps, throws, bombs_left,
         boxes, tnts, crack_m, pit_m, destr_m, active_bombs, turn) = st

        h = 0
        unfilled = [i for i, p in enumerate(self.plates_tuple) if p not in boxes]
        if unfilled:
            free_boxes = [b for b in boxes if b not in self.plates_set]
            mval, mmask = self._min_plate_matching(unfilled, free_boxes)
            if mval >= 99999:
                return 99999
            h += mval * 4 + len(unfilled) * 18
            if self.stopper_for_plate:
                unfilled_set = set(unfilled)
                for (sx, sy), pi in self.stopper_for_plate.items():
                    if pi in unfilled_set:
                        best_sd = 99
                        for b in free_boxes:
                            sd = abs(b[0] - sx) + abs(b[1] - sy)
                            if sd < best_sd:
                                best_sd = sd
                        if best_sd == 0:
                            h = max(0, h - 28)
                        elif best_sd <= 6:
                            h = max(0, h - (7 - best_sd) * 3)
                if self.stopper_required_plates and (unfilled_set & self.stopper_required_plates):
                    for ppi in self.pocket_plates:
                        if self.plates_tuple[ppi] in boxes:
                            h += 65
            nearest = 999
            for bi, (bx, by) in enumerate(free_boxes):
                if mmask & (1 << bi):
                    hd = abs(hx - bx) + abs(hy - by)
                    if hd < nearest:
                        nearest = hd
            if nearest < 999:
                h += nearest
        if plates_only:
            return h

        k1x, k1y = self.k1_pos
        k2x, k2y = self.k2_pos
        vx, vy = self.v_pos
        d_k1 = self.dist_k1[hy][hx]
        if d_k1 >= 999:
            d_k1 = abs(hx - k1x) + abs(hy - k1y)
        d_k2 = self.dist_k2[hy][hx]
        if d_k2 >= 999:
            d_k2 = abs(hx - k2x) + abs(hy - k2y)
        d_v = self.dist_v[hy][hx]
        if d_v >= 999:
            d_v = abs(hx - vx) + abs(hy - vy)
        d12 = abs(k1x - k2x) + abs(k1y - k2y)
        d1v = abs(k1x - vx) + abs(k1y - vy)
        d2v = abs(k2x - vx) + abs(k2y - vy)

        if kmask == 0:
            h += min(d_k1 + d12 + d2v, d_k2 + d12 + d1v) + 25
        elif kmask == 1:
            h += d_k2 + d2v + 12
        elif kmask == 2:
            h += d_k1 + d1v + 12
        else:
            h += d_v
        return h

    def _build_flat_grid(self, gf, p_act, boxes, tnts, crack_m, pit_m, destr_m):
        grid = self.base_flat[:]
        for _, _, idx, bit in self.destr_cells:
            if destr_m & bit:
                grid[idx] = "EMPTY"
        for _, _, idx, bit in self.crack_cells:
            if (crack_m & bit) and grid[idx] == "CRACK":
                grid[idx] = "PIT"
        for _, _, idx, bit in self.pit_cells:
            if pit_m & bit:
                grid[idx] = "EMPTY"

        hw = bytearray(GRID_SIZE)
        occ = bytearray(GRID_SIZE)
        for idx, t in enumerate(grid):
            if t in HIGH_WALL_STATIC:
                hw[idx] = 1
            elif t == "R_GATE" and not gf:
                hw[idx] = 1
            elif t == "B_GATE" and gf:
                hw[idx] = 1
            elif t == "P_GATE" and not p_act:
                hw[idx] = 1
        for bx, by in boxes:
            occ[by * 40 + bx] = 1
        for tx, ty in tnts:
            occ[ty * 40 + tx] = 2
        return grid, hw, occ

    def expand_macros(self, st, deadline):
        (sx, sy, shp, skmask, sgf, sjumps, sthrows, sbombs,
         sboxes, stnts, scrack_m, spit_m, sdestr_m, sactive_bombs, sturn) = st

        if sactive_bombs:
            out = []
            for act in ("MOVE_R", "MOVE_D", "MOVE_U", "MOVE_L", "WAIT", "JUMP_R", "JUMP_D", "JUMP_U", "JUMP_L"):
                ns, status, dmg = self.step(st, act)
                if status == "CLEARED":
                    return [act], []
                if status == "RUNNING":
                    out.append((ns, [act], dmg))
            return None, out

        p_act = self.plates_active(sboxes)
        grid, hw, occ = self._build_flat_grid(sgf, p_act, sboxes, stnts, scrack_m, spit_m, sdestr_m)

        if self.has_lasers:
            red_arr, blue_arr, red_tnts, blue_tnts, haz_indices = self.get_laser_info(sgf, sboxes, stnts, sdestr_m)
            has_live_lasers = len(haz_indices) > 0
            if has_live_lasers:
                has_r = any(red_arr[i] for i in haz_indices)
                has_b = any(blue_arr[i] for i in haz_indices)
                lperiod = 12 if (has_r and has_b) else (3 if has_r else 4)
            else:
                lperiod = 1
        else:
            red_arr = blue_arr = None
            haz_indices = ()
            has_live_lasers = False
            lperiod = 1

        phase_sens = bytearray(GRID_SIZE)
        if has_live_lasers:
            for hidx in haz_indices:
                phase_sens[hidx] = 1
                hx0 = hidx % 40
                hy0 = hidx // 40
                for _, dx, dy, _ in DIR_DELTAS:
                    nx, ny = hx0 + dx, hy0 + dy
                    if 1 <= nx < GRID_WIDTH - 1 and 1 <= ny < GRID_HEIGHT - 1:
                        phase_sens[ny * 40 + nx] = 1
            for idx, t in enumerate(grid):
                if t in MECH_TILES:
                    phase_sens[idx] = 1
                    mx, my = idx % 40, idx // 40
                    for _, dx, dy, _ in DIR_DELTAS:
                        nx, ny = mx + dx, my + dy
                        if 1 <= nx < GRID_WIDTH - 1 and 1 <= ny < GRID_HEIGHT - 1:
                            phase_sens[ny * 40 + nx] = 1
            phase_sens[sy * 40 + sx] = 1

        push_spots = {}
        for (bx, by) in sboxes:
            for d, dx, dy, _ in DIR_DELTAS:
                px, py = bx - dx, by - dy
                if 1 <= px < GRID_WIDTH - 1 and 1 <= py < GRID_HEIGHT - 1:
                    pidx = py * 40 + px
                    if pidx not in push_spots:
                        push_spots[pidx] = []
                    push_spots[pidx].append((bx, by, d))

        tnt_throw_spots = {}
        if sthrows > 0 and stnts:
            opp_map = {"U": "D", "D": "U", "L": "R", "R": "L"}
            for (tx, ty) in stnts:
                for d, dx, dy, _ in DIR_DELTAS:
                    od = opp_map[d]
                    for dist in range(1, 7):
                        rx, ry = tx + dist * dx, ty + dist * dy
                        if not _in_bounds(rx, ry):
                            break
                        ridx = ry * 40 + rx
                        if hw[ridx] or occ[ridx] == 1:
                            break
                        if ridx not in tnt_throw_spots:
                            tnt_throw_spots[ridx] = []
                        tnt_throw_spots[ridx].append(od)

        sidx = sy * 40 + sx
        m_nodes = [(None, None)]
        best_m = {}
        tkey0 = (sturn % lperiod) if (has_live_lasers and phase_sens[sidx]) else 0
        best_m[(sidx, tkey0, sjumps)] = (0, 0)

        pq = [(0, 0, 0, sidx, shp, sjumps, scrack_m, sturn, 0)]
        best_cell_arrival = {}
        reached_no_jump = set()
        best_push_arrival = {}
        best_bomb_arrival = {}
        emitted_events = {}

        def trace_path(nid, extra=None):
            acts = []
            cur = nid
            while cur != 0:
                p, a = m_nodes[cur]
                acts.append(a)
                cur = p
            acts.reverse()
            if extra is not None:
                acts.append(extra)
            return acts

        def try_push_micro(ndmg, nsteps, nidx, nhp, nj, ncm, nturn, parent_nid, act_str):
            if nturn > MAX_TURNS + 1:
                return
            tk = (nturn % lperiod) if (has_live_lasers and phase_sens[nidx]) else 0
            mk = (nidx, tk, nj)
            prev = best_m.get(mk)
            if prev is not None and (ndmg, nsteps) >= prev:
                return
            if nj < sjumps:
                for hj in range(nj + 1, sjumps + 1):
                    hpv = best_m.get((nidx, tk, hj))
                    if hpv is not None and hpv[0] <= ndmg and hpv[1] <= nsteps:
                        return
            best_m[mk] = (ndmg, nsteps)
            cnid = len(m_nodes)
            m_nodes.append((parent_nid, act_str))
            nprio = ndmg * 600 + nsteps * 10 + (sjumps - nj) * 55 + (1 if ncm != scrack_m else 0) * 3
            heapq.heappush(pq, (nprio, ndmg, nsteps, nidx, nhp, nj, ncm, nturn, cnid))

        pops = 0
        max_pops = 4200 if lperiod == 12 else (2800 if has_live_lasers else 2000)

        while pq and pops < max_pops:
            prio, cdmg, csteps, cidx, chp, cjumps, ccm, cturn, cnid = heapq.heappop(pq)
            pops += 1
            if (pops & 255) == 0 and time.perf_counter() > deadline:
                break
            if cturn > MAX_TURNS:
                continue

            tk = (cturn % lperiod) if (has_live_lasers and phase_sens[cidx]) else 0
            pv = best_m.get((cidx, tk, cjumps))
            if pv is not None and (cdmg, csteps) > pv:
                continue

            cx = cidx % 40
            cy = cidx // 40

            if cjumps == sjumps and cdmg == 0:
                reached_no_jump.add(cidx)

            pca = best_cell_arrival.get(cidx)
            if pca is None or (cdmg, sjumps - cjumps, csteps) < (pca[0], sjumps - pca[3], pca[1]):
                best_cell_arrival[cidx] = (cdmg, csteps, chp, cjumps, ccm, cturn, cnid)

            ps_list = push_spots.get(cidx)
            if ps_list is not None:
                for (bx, by, d) in ps_list:
                    bidx = by * 40 + bx
                    ptk = (cturn % lperiod) if (has_live_lasers and (cidx in haz_indices or bidx in haz_indices)) else 0
                    pk = (bx, by, d, ptk)
                    pp = best_push_arrival.get(pk)
                    p_rank = (cdmg, sjumps - cjumps, csteps)
                    if pp is None or p_rank < pp[0]:
                        best_push_arrival[pk] = (p_rank, chp, cjumps, ccm, cturn, cnid, cidx, d)

            if sbombs > 0 and (cx, cy) in self.bomb_candidates:
                pb = best_bomb_arrival.get(cidx)
                if pb is None or (cdmg, sjumps - cjumps, csteps) < (pb[0], sjumps - pb[3], pb[1]):
                    best_bomb_arrival[cidx] = (cdmg, csteps, chp, cjumps, ccm, cturn, cnid)

            t3 = has_live_lasers and (cturn % 3 == 0)
            t4 = has_live_lasers and (cturn % 4 == 0)
            c_lmask = 0
            if t3:
                c_lmask |= red_arr[cidx]
            if t4:
                c_lmask |= blue_arr[cidx]

            if has_live_lasers and phase_sens[cidx]:
                wdmg = 50 * c_lmask.bit_count() if c_lmask else 0
                if chp > wdmg:
                    try_push_micro(cdmg + wdmg, csteps + 1, cidx, chp - wdmg, cjumps, ccm, cturn + 1, cnid, "WAIT")

            cur_tile = grid[cidx]
            cur_is_crack = (cur_tile == "CRACK") and not (ccm & self.crack_bit[(cx, cy)])

            for d, dx, dy, didx in DIR_DELTAS:
                nidx = cidx + didx
                if not hw[nidx] and not occ[nidx]:
                    nt = grid[nidx]
                    if not (nt in ONEWAY_TILES and nt[-1] != d):
                        if (not cur_is_crack) and (nt in SIMPLE_WALK_TILES) and (not (t3 and red_tnts)) and (not (t4 and blue_tnts)):
                            lmask = c_lmask
                            if t3:
                                lmask |= red_arr[nidx]
                            if t4:
                                lmask |= blue_arr[nidx]
                            sdmg = 50 * lmask.bit_count() if lmask else 0
                            if chp > sdmg:
                                try_push_micro(cdmg + sdmg, csteps + 1, nidx, chp - sdmg, cjumps, ccm, cturn + 1, cnid, f"MOVE_{d}")
                        else:
                            if nt != "PIT" and not (nt == "CRACK" and (ccm & self.crack_bit[(cx + dx, cy + dy)])):
                                act = f"MOVE_{d}"
                                cur_st = (cx, cy, chp, skmask, sgf, cjumps, sthrows, sbombs,
                                          sboxes, stnts, ccm, spit_m, sdestr_m, (), cturn)
                                ns, nstatus, sdmg = self.step(cur_st, act)
                                if nstatus == "CLEARED":
                                    return trace_path(cnid, act), []
                                if nstatus == "RUNNING":
                                    (nx, ny, nhp, nkm, ngf, nj, _, _, _, _, ncm, _, ndm, _, nturn) = ns
                                    ndmg = cdmg + sdmg
                                    nsteps = csteps + 1
                                    if nkm != skmask or ngf != sgf or ndm != sdestr_m:
                                        etk = (nturn % lperiod) if (has_live_lasers and (ny * 40 + nx) in haz_indices) else 0
                                        ek = (nx, ny, nkm, ngf, nj, ncm, ndm, etk)
                                        pe = emitted_events.get(ek)
                                        if pe is None or (ndmg, nsteps) < (pe[0], pe[1]):
                                            emitted_events[ek] = (ndmg, nsteps, ns, cnid, act)
                                    else:
                                        try_push_micro(ndmg, nsteps, ny * 40 + nx, nhp, nj, ncm, nturn, cnid, act)

                if cjumps > 0:
                    nx2 = cx + 2 * dx
                    ny2 = cy + 2 * dy
                    if 1 <= nx2 < GRID_WIDTH - 1 and 1 <= ny2 < GRID_HEIGHT - 1:
                        nidx2 = nidx + didx
                        if not hw[nidx] and not hw[nidx2] and not occ[nidx2]:
                            nt1 = grid[nidx]
                            nt2 = grid[nidx2]
                            if (nt1 != "EMPTY" or occ[nidx] or (has_live_lasers and (red_arr[nidx] or blue_arr[nidx]))):
                                if not (nt1 in ONEWAY_TILES and nt1[-1] != d) and not (nt2 in ONEWAY_TILES and nt2[-1] != d):
                                    if nt2 != "PIT" and not (nt2 == "CRACK" and (ccm & self.crack_bit[(nx2, ny2)])):
                                        if (not cur_is_crack) and (nt2 in SIMPLE_WALK_TILES) and (not (t3 and red_tnts)) and (not (t4 and blue_tnts)):
                                            lmask = c_lmask
                                            if t3:
                                                lmask |= red_arr[nidx2]
                                            if t4:
                                                lmask |= blue_arr[nidx2]
                                            sdmg = 50 * lmask.bit_count() if lmask else 0
                                            if chp > sdmg:
                                                try_push_micro(cdmg + sdmg, csteps + 1, nidx2, chp - sdmg, cjumps - 1, ccm, cturn + 1, cnid, f"JUMP_{d}")
                                        else:
                                            act = f"JUMP_{d}"
                                            cur_st = (cx, cy, chp, skmask, sgf, cjumps, sthrows, sbombs,
                                                      sboxes, stnts, ccm, spit_m, sdestr_m, (), cturn)
                                            ns, nstatus, sdmg = self.step(cur_st, act)
                                            if nstatus == "CLEARED":
                                                return trace_path(cnid, act), []
                                            if nstatus == "RUNNING":
                                                (nx, ny, nhp, nkm, ngf, nj, _, _, _, _, ncm, _, ndm, _, nturn) = ns
                                                ndmg = cdmg + sdmg
                                                nsteps = csteps + 1
                                                if nkm != skmask or ngf != sgf or ndm != sdestr_m:
                                                    etk = (nturn % lperiod) if (has_live_lasers and (ny * 40 + nx) in haz_indices) else 0
                                                    ek = (nx, ny, nkm, ngf, nj, ncm, ndm, etk)
                                                    pe = emitted_events.get(ek)
                                                    if pe is None or (ndmg, nsteps) < (pe[0], pe[1]):
                                                        emitted_events[ek] = (ndmg, nsteps, ns, cnid, act)
                                                else:
                                                    try_push_micro(ndmg, nsteps, ny * 40 + nx, nhp, nj, ncm, nturn, cnid, act)

        macros = []
        ev_by_base = collections.defaultdict(list)
        for (nx, ny, nkm, ngf, nj, ncm, ndm, etk), val in emitted_events.items():
            ev_by_base[(nx, ny, nkm, ngf, ndm, etk)].append((val[0], -nj, val[1], val[2], val[3], val[4]))
        for group in ev_by_base.values():
            group.sort()
            kept = []
            for dmg, neg_j, steps, ns, cnid, last_act in group:
                dom = False
                for kdmg, kneg_j, ksteps in kept:
                    if kdmg <= dmg and kneg_j <= neg_j and ksteps <= steps + 10:
                        dom = True
                        break
                if not dom:
                    kept.append((dmg, neg_j, steps))
                    macros.append((ns, trace_path(cnid, last_act), dmg))

        for (_, chp, cjumps, ccm, cturn, cnid, cidx, d) in best_push_arrival.values():
            cx, cy = cidx % 40, cidx // 40
            cur_st = (cx, cy, chp, skmask, sgf, cjumps, sthrows, sbombs,
                      sboxes, stnts, ccm, spit_m, sdestr_m, (), cturn)
            act = f"MOVE_{d}"
            ns, nstatus, _ = self.step(cur_st, act)
            if nstatus == "CLEARED":
                return trace_path(cnid, act), []
            if nstatus == "RUNNING":
                if ns[8] != sboxes or ns[9] != stnts or ns[4] != sgf or ns[11] != spit_m or ns[12] != sdestr_m:
                    if not self._is_box_deadlocked(ns[8]):
                        macros.append((ns, trace_path(cnid, act), max(0, shp - ns[2])))

        if sthrows > 0:
            seen_throw = set()
            for cidx, (cdmg, csteps, chp, cjumps, ccm, cturn, cnid) in best_cell_arrival.items():
                cx, cy = cidx % 40, cidx // 40
                cdirs = self.throw_candidates.get((cx, cy))
                tdirs = tnt_throw_spots.get(cidx)
                if not cdirs and not tdirs:
                    continue
                dirs = set(cdirs) if cdirs else set()
                if tdirs:
                    dirs.update(tdirs)
                cur_st = (cx, cy, chp, skmask, sgf, cjumps, sthrows, sbombs,
                          sboxes, stnts, ccm, spit_m, sdestr_m, (), cturn)
                for d in dirs:
                    act = f"THROW_{d}"
                    ns, nstatus, _ = self.step(cur_st, act)
                    if nstatus == "RUNNING":
                        if ns[4] != sgf or ns[9] != stnts or ns[12] != sdestr_m:
                            ek = (ns[4], ns[9], ns[12])
                            if ek not in seen_throw:
                                seen_throw.add(ek)
                                macros.append((ns, trace_path(cnid, act), max(0, shp - ns[2])))

        if sbombs > 0 and best_bomb_arrival:
            by_effect = {}
            for cidx, info in best_bomb_arrival.items():
                bx, by = cidx % 40, cidx // 40
                cdmg, csteps, chp, cjumps, ccm, cturn, cnid = info
                val = 0
                hits = []
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = bx + dx, by + dy
                        if not _in_bounds(nx, ny):
                            continue
                        nidx = ny * 40 + nx
                        if occ[nidx] == 2:
                            val += 60
                            hits.append(nidx)
                        elif occ[nidx] == 1 and (nx, ny) in self.plates_set:
                            val += 25
                            hits.append(nidx)
                        nt = grid[nidx]
                        if nt in ALL_LASER_TILES:
                            val += 50
                            hits.append(nidx)
                        elif nt in ("R_GATE", "B_GATE"):
                            val += 45
                            hits.append(nidx)
                        elif nt == "MIMIC":
                            if (nx, ny) in self.blocking_mimics:
                                val += 30
                                hits.append(nidx)
                        elif nt in SPRING_TILES or nt in MIRROR_MAP:
                            val += 15
                            hits.append(nidx)
                        elif nt == "W":
                            adj_unreach = False
                            for _, adx, ady, _ in DIR_DELTAS:
                                ax, ay = nx + adx, ny + ady
                                if 1 <= ax < GRID_WIDTH - 1 and 1 <= ay < GRID_HEIGHT - 1:
                                    aidx = ay * 40 + ax
                                    if aidx not in reached_no_jump and grid[aidx] != "T_W" and grid[aidx] != "W":
                                        adj_unreach = True
                                        break
                            if adj_unreach:
                                val += 35
                                hits.append(nidx)
                            elif (abs(nx - self.k1_pos[0]) + abs(ny - self.k1_pos[1]) <= 2
                                  or abs(nx - self.k2_pos[0]) + abs(ny - self.k2_pos[1]) <= 2
                                  or abs(nx - self.v_pos[0]) + abs(ny - self.v_pos[1]) <= 2):
                                val += 40
                                hits.append(nidx)
                if val > 0 and hits:
                    hk = tuple(hits)
                    prev = by_effect.get(hk)
                    rank_b = (-val, sjumps - cjumps, csteps)
                    if prev is None or rank_b < prev[0]:
                        by_effect[hk] = (rank_b, cidx, info)

            cands = sorted(by_effect.values(), key=lambda z: z[0])[:10]
            fallback_used = 0
            for rank_b, bidx, (cdmg, csteps, chp, cjumps, ccm, cturn, cnid) in cands:
                if time.perf_counter() > deadline:
                    break
                bx, by = bidx % 40, bidx // 40
                cur_st = (bx, by, chp, skmask, sgf, cjumps, sthrows, sbombs,
                          sboxes, stnts, ccm, spit_m, sdestr_m, (), cturn)
                esc_pair = self._find_fast_bomb_escape(bx, by, chp, cjumps, cturn, grid, hw, occ,
                                                       has_live_lasers, red_arr, blue_arr)
                if esc_pair is not None:
                    st1, s1, _ = self.step(cur_st, "BOMB")
                    if s1 != "RUNNING":
                        continue
                    st2, s2, _ = self.step(st1, esc_pair[0])
                    if s2 == "CLEARED":
                        return trace_path(cnid) + ["BOMB", esc_pair[0]], []
                    if s2 != "RUNNING":
                        continue
                    st3, s3, _ = self.step(st2, esc_pair[1])
                    if s3 == "CLEARED":
                        return trace_path(cnid) + ["BOMB", esc_pair[0], esc_pair[1]], []
                    if s3 == "RUNNING" and not st3[13] and st3[2] >= chp - 50:
                        if st3[12] != sdestr_m or st3[8] != sboxes or st3[9] != stnts:
                            macros.append((st3, trace_path(cnid) + ["BOMB", esc_pair[0], esc_pair[1]], max(0, shp - st3[2])))
                elif fallback_used < 3 and (-rank_b[0]) >= 35:
                    fallback_used += 1
                    res_fb = self._find_exact_bomb_escape(cur_st)
                    if res_fb is not None:
                        if res_fb[0] == "CLEARED":
                            return trace_path(cnid) + res_fb[1], []
                        st3, acts3 = res_fb[1], res_fb[2]
                        if st3[12] != sdestr_m or st3[8] != sboxes or st3[9] != stnts:
                            macros.append((st3, trace_path(cnid) + acts3, max(0, shp - st3[2])))

        return None, macros

    def _find_fast_bomb_escape(self, bx, by, hp, jumps, turn, grid, hw, occ, has_lasers, red_arr, blue_arr):
        bidx = by * 40 + bx
        if has_lasers:
            m0 = (red_arr[bidx] if turn % 3 == 0 else 0) | (blue_arr[bidx] if turn % 4 == 0 else 0)
            if m0 and hp <= 50 * m0.bit_count():
                return None

        t1 = turn + 1
        t2 = turn + 2
        step1_opts = []
        for d, dx, dy, didx in DIR_DELTAS:
            n1 = bidx + didx
            if not hw[n1] and not occ[n1]:
                nt1 = grid[n1]
                if nt1 in SIMPLE_WALK_TILES and not (nt1 in ONEWAY_TILES and nt1[-1] != d):
                    l1 = 0
                    if has_lasers:
                        if t1 % 3 == 0:
                            l1 |= red_arr[bidx] | red_arr[n1]
                        if t1 % 4 == 0:
                            l1 |= blue_arr[bidx] | blue_arr[n1]
                    if not l1:
                        step1_opts.append((n1, bx + dx, by + dy, f"MOVE_{d}", 0))
            if jumps > 0:
                nx2, ny2 = bx + 2 * dx, by + 2 * dy
                if 1 <= nx2 < GRID_WIDTH - 1 and 1 <= ny2 < GRID_HEIGHT - 1:
                    n2 = n1 + didx
                    if not hw[n1] and not hw[n2] and not occ[n2]:
                        nt1, nt2 = grid[n1], grid[n2]
                        if nt2 in SIMPLE_WALK_TILES and not (nt1 in ONEWAY_TILES and nt1[-1] != d) and not (nt2 in ONEWAY_TILES and nt2[-1] != d):
                            l1 = 0
                            if has_lasers:
                                if t1 % 3 == 0:
                                    l1 |= red_arr[bidx] | red_arr[n2]
                                if t1 % 4 == 0:
                                    l1 |= blue_arr[bidx] | blue_arr[n2]
                            if not l1:
                                step1_opts.append((n2, nx2, ny2, f"JUMP_{d}", 1))

        best = None
        for n1, x1, y1, a1, ju in step1_opts:
            if abs(x1 - bx) > 1 or abs(y1 - by) > 1:
                l2 = 0
                if has_lasers:
                    if t2 % 3 == 0:
                        l2 |= red_arr[n1]
                    if t2 % 4 == 0:
                        l2 |= blue_arr[n1]
                if not l2:
                    if ju == 0:
                        return (a1, "WAIT")
                    best = (a1, "WAIT")
            for d2, dx2, dy2, didx2 in DIR_DELTAS:
                x2, y2 = x1 + dx2, y1 + dy2
                if abs(x2 - bx) <= 1 and abs(y2 - by) <= 1:
                    continue
                if not (1 <= x2 < GRID_WIDTH - 1 and 1 <= y2 < GRID_HEIGHT - 1):
                    continue
                n2 = n1 + didx2
                if not hw[n2] and not occ[n2]:
                    nt2 = grid[n2]
                    if nt2 in SIMPLE_WALK_TILES and not (nt2 in ONEWAY_TILES and nt2[-1] != d2):
                        l2 = 0
                        if has_lasers:
                            if t2 % 3 == 0:
                                l2 |= red_arr[n1] | red_arr[n2]
                            if t2 % 4 == 0:
                                l2 |= blue_arr[n1] | blue_arr[n2]
                        if not l2:
                            if ju == 0:
                                return (a1, f"MOVE_{d2}")
                            if best is None:
                                best = (a1, f"MOVE_{d2}")
        return best

    def _find_exact_bomb_escape(self, cur_st):
        st1, s1, _ = self.step(cur_st, "BOMB")
        if s1 != "RUNNING":
            return None
        acts = ("MOVE_R", "MOVE_L", "MOVE_U", "MOVE_D", "JUMP_R", "JUMP_L", "JUMP_U", "JUMP_D", "WAIT")
        best = None
        for a1 in acts:
            if a1.startswith("JUMP_") and st1[5] <= 0:
                continue
            st2, s2, _ = self.step(st1, a1)
            if s2 == "CLEARED":
                return ("CLEARED", ["BOMB", a1])
            if s2 != "RUNNING":
                continue
            for a2 in acts:
                if a2.startswith("JUMP_") and st2[5] <= 0:
                    continue
                st3, s3, _ = self.step(st2, a2)
                if s3 == "CLEARED":
                    return ("CLEARED", ["BOMB", a1, a2])
                if s3 == "RUNNING" and not st3[13] and st3[2] >= cur_st[2] - 50:
                    sc = (cur_st[2] - st3[2]) * 100 + (cur_st[5] - st3[5]) * 15
                    if best is None or sc < best[0]:
                        best = (sc, st3, ["BOMB", a1, a2])
                        if sc == 0:
                            return ("OK", st3, ["BOMB", a1, a2])
        if best is not None:
            return ("OK", best[1], best[2])
        return None

    def _eval_plan_score(self, init_state, plan):
        st = init_state
        for act in plan:
            st, status, _ = self.step(st, act)
            if status == "CLEARED":
                hp_left = st[2]
                t_len = len(plan)
                return 600.0 + 1.5 * hp_left + 150.0 * (240 - t_len) / 239.0
            if status != "RUNNING":
                return -1.0
        return -1.0

    def solve(self, init_state, budget_sec=1.50):
        t0 = time.perf_counter()
        deadline = t0 + budget_sec
        rem_turns = MAX_TURNS - init_state[14] + 1

        # If map has stopper-required plates, run dedicated Plate-First Subgoal Search FIRST!
        if self.stopper_required_plates and not self.plates_active(init_state[8]):
            dl_sp = t0 + min(budget_sec * 0.68, 1.02)
            p_acts, p_st, _ = self._run_plate_subgoal(init_state, dl_sp)
            if p_st is not None and time.perf_counter() < deadline - 0.05:
                plan_rest, part_rest, _ = self._run_macro_astar(p_st, deadline, weight=2.2, b_pen=20, j_pen=18)
                if plan_rest is not None:
                    comb = p_acts + plan_rest
                    if len(comb) <= rem_turns:
                        return comb, comb
                if p_acts:
                    return None, p_acts + part_rest

        dl1 = t0 + min(budget_sec * 0.48, 0.72)
        plan, partial, nodes = self._run_macro_astar(init_state, dl1, weight=2.2, b_pen=24, j_pen=18)

        best_plan = None
        best_score = -1.0
        if plan is not None and len(plan) <= rem_turns:
            sc = self._eval_plan_score(init_state, plan)
            if sc > best_score:
                best_score = sc
                best_plan = plan

        if best_plan is not None:
            if (best_score < 840.0 or len(best_plan) > 95) and time.perf_counter() < deadline - 0.15:
                dl_opt = min(deadline, time.perf_counter() + 0.45)
                plan_opt, _, n_opt = self._run_macro_astar(
                    init_state, dl_opt, weight=1.15, b_pen=4, j_pen=6, max_plan_len=len(best_plan)
                )
                nodes += n_opt
                if plan_opt is not None and len(plan_opt) <= rem_turns:
                    sc2 = self._eval_plan_score(init_state, plan_opt)
                    if sc2 > best_score:
                        best_score = sc2
                        best_plan = plan_opt
            return best_plan, best_plan

        if self.plates_tuple and not self.plates_active(init_state[8]) and time.perf_counter() < deadline - 0.16:
            dl_p = min(deadline - 0.08, time.perf_counter() + 0.65)
            p_acts, p_st, _ = self._run_plate_subgoal(init_state, dl_p)
            if p_st is not None and time.perf_counter() < deadline - 0.03:
                plan_rest, part_rest, _ = self._run_macro_astar(p_st, deadline, weight=2.2, b_pen=20, j_pen=18)
                if plan_rest is not None:
                    comb = p_acts + plan_rest
                    if len(comb) <= rem_turns:
                        return comb, comb
                if len(p_acts) + len(part_rest) > len(partial):
                    partial = p_acts + part_rest

        if time.perf_counter() < deadline - 0.05:
            plan3, partial3, _ = self._run_macro_astar(init_state, deadline, weight=5.0, b_pen=18, j_pen=16)
            if plan3 is not None and len(plan3) <= rem_turns:
                return plan3, plan3
            if len(partial3) > len(partial):
                partial = partial3

        return None, partial

    def _run_plate_subgoal(self, init_state, deadline):
        def skey(st):
            return (st[0], st[1], st[4], st[5], st[7], st[8], st[9], st[10], st[11], st[12])

        h0 = self.heuristic(init_state, plates_only=True)
        pq = [(1.25 * h0, 0, 0, init_state)]
        parents = {0: (None, [])}
        best_g = {skey(init_state): 0}
        next_id = 1
        expanded = 0

        def reconstruct(nid):
            ch = []
            cur = nid
            while cur is not None:
                p, a = parents[cur]
                if a:
                    ch.append(a)
                cur = p
            ch.reverse()
            out = []
            for x in ch:
                out.extend(x)
            return out

        while pq and time.perf_counter() < deadline:
            f, g, nid, st = heapq.heappop(pq)
            if self.plates_active(st[8]):
                return reconstruct(nid), st, expanded
            expanded += 1
            cleared, macros = self.expand_macros(st, deadline)
            if cleared is not None:
                return reconstruct(nid) + cleared, None, expanded
            for ns, act_seq, _ in macros:
                if ns[14] > MAX_TURNS + 1:
                    continue
                if self.plates_active(ns[8]):
                    return reconstruct(nid) + act_seq, ns, expanded
                # Skip key pickups or no-op macros during dedicated plate subgoal search
                if ns[3] != st[3]:
                    continue
                if ns[8] == st[8] and ns[4] == st[4] and ns[11] == st[11] and ns[12] == st[12]:
                    continue
                ng = g + len(act_seq) + max(0, st[2] - ns[2]) * 2.5 + max(0, st[5] - ns[5]) * 18 + max(0, st[7] - ns[7]) * 20
                k = skey(ns)
                if k in best_g and ng >= best_g[k]:
                    continue
                best_g[k] = ng
                cid = next_id
                next_id += 1
                parents[cid] = (nid, act_seq)
                nh = self.heuristic(ns, plates_only=True)
                heapq.heappush(pq, (ng + 1.25 * nh, ng, cid, ns))
        return [], None, expanded

    def _run_macro_astar(self, init_state, deadline, weight=2.2, b_pen=24, j_pen=18, max_plan_len=None):
        def state_key(st):
            tmod = 0
            if self.has_lasers:
                linfo = self.get_laser_info(st[4], st[8], st[9], st[12])
                if (st[1] * 40 + st[0]) in linfo[4]:
                    tmod = st[14] % 12
            return (st[0], st[1], st[3], st[4], st[5], st[6], st[7],
                    st[8], st[9], st[10], st[11], st[12], st[13], tmod)

        def progress_rank(st):
            km = st[3]
            keys_cnt = (1 if km & 1 else 0) + (1 if km & 2 else 0)
            p_filled = sum(1 for p in self.plates_tuple if p in st[8])
            return (keys_cnt, p_filled, 1 if self.plates_active(st[8]) else 0, -self.heuristic(st), st[2])

        h0 = self.heuristic(init_state)
        pq = [(weight * h0, 0, 0, init_state)]
        parents = {0: (None, [])}
        best_g = {state_key(init_state): (0, init_state[2])}
        best_partial_rank = progress_rank(init_state)
        best_partial_id = 0
        next_id = 1
        expanded = 0
        start_turn = init_state[14]

        def reconstruct(nid):
            chunks = []
            cur = nid
            while cur is not None:
                pid, acts = parents[cur]
                if acts:
                    chunks.append(acts)
                cur = pid
            chunks.reverse()
            out = []
            for ch in chunks:
                out.extend(ch)
            return out

        while pq and time.perf_counter() < deadline:
            f, g, nid, st = heapq.heappop(pq)
            sk = state_key(st)
            bg = best_g.get(sk)
            if bg is not None and g > bg[0] and st[2] <= bg[1]:
                continue
            if max_plan_len is not None and (st[14] - start_turn) >= max_plan_len:
                continue

            expanded += 1
            pr = progress_rank(st)
            if pr > best_partial_rank:
                best_partial_rank = pr
                best_partial_id = nid

            cleared_acts, macros = self.expand_macros(st, deadline)
            if cleared_acts is not None:
                full_plan = reconstruct(nid) + cleared_acts
                return full_plan, full_plan, expanded

            for ns, act_seq, _ in macros:
                if ns[14] > MAX_TURNS + 1:
                    continue
                if max_plan_len is not None and (ns[14] - start_turn) >= max_plan_len:
                    continue
                need_p = self.min_pits_to_v[ns[1]][ns[0]]
                if need_p < 99:
                    spare_boxes = max(0, len(ns[8]) - len(self.plates_tuple))
                    filled_pits = ns[11].bit_count()
                    if ns[5] + spare_boxes + filled_pits < need_p:
                        continue
                j_spent = max(0, st[5] - ns[5])
                b_spent = max(0, st[7] - ns[7])
                ng = g + len(act_seq) + max(0, st[2] - ns[2]) * 2.5 + j_spent * j_pen + b_spent * b_pen
                nsk = state_key(ns)
                nbg = best_g.get(nsk)
                if nbg is not None and ng >= nbg[0] and ns[2] <= nbg[1]:
                    continue
                best_g[nsk] = (ng, ns[2])
                cid = next_id
                next_id += 1
                parents[cid] = (nid, act_seq)
                nh = self.heuristic(ns)
                heapq.heappush(pq, (ng + weight * nh, ng, cid, ns))

        return None, reconstruct(best_partial_id), expanded

    def pick_safe_fallback(self, st, visits):
        best_act = "WAIT"
        best_sc = (999, 999999)
        for act in ("MOVE_R", "MOVE_D", "MOVE_U", "MOVE_L", "WAIT", "JUMP_R", "JUMP_D", "JUMP_U", "JUMP_L"):
            if act.startswith("JUMP_") and st[5] <= 0:
                continue
            ns, status, dmg = self.step(st, act)
            if status == "CLEARED":
                return act
            if status != "RUNNING":
                continue
            sc = (dmg, visits.get((ns[0], ns[1]), 0) * 15 + self.heuristic(ns) + (20 if act.startswith("JUMP_") else 0))
            if sc < best_sc:
                best_sc = sc
                best_act = act
        return best_act


def decide_action(state: dict, memory: dict) -> str:
    """
    v2.2 FULL-Mode Hero Entrypoint.
    Turn 1 budget: 1.50s (official limit 2.0s).
    Turn 2..240: < 0.5ms on cached plan, <= 0.30s on replan/recovery (official limit 0.5s).
    """
    try:
        turn = state.get("turn", 1)
        hero = state["hero"]
        pos = (hero["x"], hero["y"])
        visits = memory.get("visits")
        if visits is None:
            visits = {}
            memory["visits"] = visits
        visits[pos] = visits.get(pos, 0) + 1

        fw = memory.get("world")
        if fw is None:
            fw = FastWorld()
            cur_st = fw.build_from_state(state)
            memory["world"] = fw
        else:
            cur_st = fw.state_from_obs(state)

        # Fast-path execution of verified plan
        plan = memory.get("plan")
        plan_idx = memory.get("plan_idx", 0)
        exp_sig = memory.get("expected_sig")
        cur_sig = (cur_st[0], cur_st[1], cur_st[2], cur_st[3], cur_st[4], cur_st[8])

        if plan and plan_idx < len(plan):
            if exp_sig is None or exp_sig == cur_sig:
                act = plan[plan_idx]
                ns, status, _ = fw.step(cur_st, act)
                if status in ("RUNNING", "CLEARED"):
                    memory["plan_idx"] = plan_idx + 1
                    if ns is not None:
                        memory["expected_sig"] = (ns[0], ns[1], ns[2], ns[3], ns[4], ns[8])
                    else:
                        memory["expected_sig"] = None
                    return act if act in VALID_ACTIONS else "WAIT"

        # Plan missing, finished, or diverged -> solve within strict time budget!
        budget = 1.50 if turn == 1 else 0.30
        full_plan, partial = fw.solve(cur_st, budget_sec=budget)
        chosen_plan = full_plan if full_plan else partial

        if chosen_plan:
            memory["plan"] = chosen_plan
            memory["plan_idx"] = 1
            act = chosen_plan[0]
            ns, status, _ = fw.step(cur_st, act)
            if status in ("RUNNING", "CLEARED"):
                memory["expected_sig"] = (ns[0], ns[1], ns[2], ns[3], ns[4], ns[8]) if ns is not None else None
                return act if act in VALID_ACTIONS else "WAIT"

        # Safe fallback if no macro plan available
        memory["plan"] = None
        memory["expected_sig"] = None
        act = fw.pick_safe_fallback(cur_st, visits)
        return act if act in VALID_ACTIONS else "WAIT"
    except Exception:
        return "WAIT"
