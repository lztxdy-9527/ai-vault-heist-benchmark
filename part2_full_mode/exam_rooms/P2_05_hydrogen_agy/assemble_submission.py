"""Assemble self-contained v2.2 FULL-mode submission.py from tested hero_v22 + Chrono-Bastion."""

import build_demon_v22

d = build_demon_v22.build_chrono_bastion()
author_sol = d["author_solution"]

hero_src = open("hero_v22.py", "r", encoding="utf-8").read()

# Strip hero_v22 docstring & initial constants that we supply in clean header
marker = "def _in_bounds(x: int, y: int) -> bool:"
idx = hero_src.index(marker)
hero_body = hero_src[idx:]

# Upgrade the state["bombs"] mid-bomb restart guard cleanly inside solve_full_plan
old_bomb_guard = """    if state["bombs"]:
        # Escape ticking bomb cleanly first
        pass"""

new_bomb_guard = """    if state.get("bombs"):
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
                        eq.append((ex, ey, nt, ep + [a]))"""

assert old_bomb_guard in hero_body, "old_bomb_guard not found"
hero_body = hero_body.replace(old_bomb_guard, new_bomb_guard, 1)

header = f'''"""Part 2 FULL-mode dual-role submission: Chrono-Bastion v2.2 & FullWorldEnv Hero Solver."""

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

DIRECTIONS = {{"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}}
DIR_NAMES = ("U", "D", "L", "R")

MIRROR_MAP = {{
    "MIRROR_NE": {{"L": "U", "R": "U", "U": "R", "D": "R"}},
    "MIRROR_SE": {{"L": "D", "R": "D", "U": "R", "D": "R"}},
    "MIRROR_SW": {{"L": "D", "R": "D", "U": "L", "D": "L"}},
    "MIRROR_NW": {{"L": "U", "R": "U", "U": "L", "D": "L"}},
}}

LASER1_DIRS = {{"LASER_U": "U", "LASER_D": "D", "LASER_L": "L", "LASER_R": "R"}}
LASER2_DIRS = {{"LASER2_U": "U", "LASER2_D": "D", "LASER2_L": "L", "LASER2_R": "R"}}
ALL_LASER_DIRS = {{**LASER1_DIRS, **LASER2_DIRS}}
SPRING_DIRS = {{"SPRING_U": "U", "SPRING_D": "D", "SPRING_L": "L", "SPRING_R": "R"}}
ONEWAY_DIRS = {{"ONEWAY_U": "U", "ONEWAY_D": "D", "ONEWAY_L": "L", "ONEWAY_R": "R"}}
PORTAL_PAIRS = {{
    "PORTAL_1A": "PORTAL_1B", "PORTAL_1B": "PORTAL_1A",
    "PORTAL_2A": "PORTAL_2B", "PORTAL_2B": "PORTAL_2A",
}}

BOMB_IMMUNE = {{
    "T_W", "K1", "K2", "V", "PIT", "PLATE", "P_GATE",
    "ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R",
    "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
}}

_AUTHOR_SOLUTION = {repr(author_sol)}


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

    return {{
        "taunt": "Plates feed pits, switches flip twice, mod-12 waits for none.",
        "grid": grid,
        "author_solution": list(_AUTHOR_SOLUTION),
    }}


'''

full_src = header + hero_body
with open("submission.py", "w", encoding="utf-8") as f:
    f.write(full_src)
print("Wrote submission.py, lines:", len(full_src.splitlines()), "bytes:", len(full_src))
