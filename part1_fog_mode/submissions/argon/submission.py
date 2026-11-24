"""
Dungeon Vault Attack and Defense Submission Module.
Implements build_dungeon() and decide_action(state, memory).
"""

import bisect
import collections
import copy
import functools
import heapq
import itertools
import json
import math
import operator
import random
import re
import time
import typing

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

DIRECTIONS = {
    "U": (0, -1),
    "D": (0, 1),
    "L": (-1, 0),
    "R": (1, 0),
}

DIR_ORDER = ("R", "U", "D", "L")

MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}

TILE_COSTS = {
    "EMPTY": 0,
    "K1": 0, "K2": 0, "V": 0,
    "W": 5,
    "T_W": 25,
    "ICE": 10,
    "MIRROR_NE": 25, "MIRROR_SE": 25, "MIRROR_SW": 25, "MIRROR_NW": 25,
    "SPRING_U": 35, "SPRING_D": 35, "SPRING_L": 35, "SPRING_R": 35,
    "PIT": 40,
    "LASER_U": 75, "LASER_D": 75, "LASER_L": 75, "LASER_R": 75,
    "CRACK": 20,
    "SWITCH": 30,
    "R_GATE": 20, "B_GATE": 20,
    "TNT": 40,
    "BOX": 30,
    "HEAL": 30,
    "MIMIC": 60,
    "PORTAL_1A": 40, "PORTAL_1B": 40,
    "PORTAL_2A": 40, "PORTAL_2B": 40,
}

HIGH_WALL_STATIC = {"W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R"}
PORTAL_PAIRS = {
    "PORTAL_1A": "PORTAL_1B", "PORTAL_1B": "PORTAL_1A",
    "PORTAL_2A": "PORTAL_2B", "PORTAL_2B": "PORTAL_2A",
}
IMMUNE_EXPLOSION = {
    "T_W", "K1", "K2", "V",
    "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
    "PIT",
}
DESTROY_TO_EMPTY = {
    "W", "ICE",
    "MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW",
    "SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R",
    "LASER_U", "LASER_D", "LASER_L", "LASER_R",
    "SWITCH", "R_GATE", "B_GATE", "HEAL", "MIMIC",
}


# ==============================================================================
# Part 1: Demon Dungeon Builder
# ==============================================================================

def build_dungeon() -> dict:
    """
    Construct a 40x26 dungeon within the 3000G budget (spending 1095G, retaining 1905G)
    and provide a 76-step author_solution that clears on the exact final step.
    """
    grid = [
        [
            "T_W" if (x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1) else "EMPTY"
            for x in range(GRID_WIDTH)
        ]
        for y in range(GRID_HEIGHT)
    ]

    # Mandatory Landmarks:
    # K1 at (34, 2)  [x in 12..34, y in 2..10]
    # K2 at (34, 21) [x in 12..34, y in 15..23], |34-34| + |2-21| = 19 >= 12
    # V  at (33, 21) [x in 33..37, y in 4..21]
    grid[2][34] = "K1"
    grid[21][34] = "K2"
    grid[21][33] = "V"

    # 1. Top-Left Unobservable Switch Vault: (1..6, 1)
    # Triggered by standing at (6, 4) and executing THROW_U:
    # (6,3)[5] -> (6,2)[4] -> (6,1) MIRROR_NW (turns L)[3] -> (5,1) PIT[2] -> (4,1) PIT[1]
    # -> (3,1) ICE[0, ground slide] -> (2,1) ICE -> (1,1) SWITCH
    grid[1][1] = "SWITCH"
    grid[1][2] = "ICE"
    grid[1][3] = "ICE"
    grid[1][4] = "PIT"
    grid[1][5] = "PIT"
    grid[1][6] = "MIRROR_NW"
    for x in range(1, 6):
        grid[2][x] = "W"

    # 2. Starter Corridor & Turn-6 Double-Laser Guillotine at (10, 13)
    for x in range(1, 5):
        grid[11][x] = "W"
        grid[15][x] = "W"
    for x in range(4, 10):
        grid[12][x] = "W"
        grid[14][x] = "W"
    grid[13][7] = "ICE"
    grid[13][8] = "ICE"
    grid[13][9] = "ICE"
    grid[3][10] = "LASER_D"
    grid[23][10] = "LASER_U"

    # 3. K1(34, 2) Titanium Pod with GV_03 Spring + CRACK + PIT + Unseen R_GATE
    for px, py in ((34, 1), (34, 3), (35, 2), (33, 1), (33, 3), (32, 1), (32, 3)):
        grid[py][px] = "T_W"
    for px, py in ((30, 1), (31, 1), (30, 3), (31, 3)):
        grid[py][px] = "W"
    grid[2][30] = "SPRING_R"
    grid[2][31] = "CRACK"
    grid[2][32] = "PIT"
    grid[2][33] = "R_GATE"

    # 4. K2(34, 21) + V(33, 21) + Direction-Locked PORTAL_1B(35, 21) Titanium Pod
    for px, py in ((32, 21), (33, 20), (34, 20), (33, 22), (34, 22)):
        grid[py][px] = "T_W"
    grid[21][35] = "PORTAL_1B"
    grid[21][36] = "PIT"
    grid[20][35] = "PIT"
    grid[22][35] = "PIT"
    grid[13][22] = "PORTAL_1A"

    author_solution = (
        ["MOVE_R"] * 4
        + ["WAIT"] * 2
        + ["MOVE_R"]
        + ["MOVE_R"]
        + ["MOVE_U"] * 11
        + ["MOVE_L"] * 5
        + ["MOVE_D"] * 2
        + ["THROW_U"]
        + ["MOVE_U"] * 2
        + ["MOVE_R"] * 24
        + ["MOVE_R"]
        + ["MOVE_L"]
        + ["JUMP_L"]
        + ["JUMP_L"]
        + ["MOVE_L"] * 6
        + ["MOVE_D"] * 11
        + ["MOVE_L"]
        + ["MOVE_L"]
    )

    return {
        "taunt": "盲区折跃锁双钥，冰道双光断归途！欢迎挑战 CARBON 金库！",
        "grid": grid,
        "author_solution": author_solution,
    }


# ==============================================================================
# Part 2: Hero Decision Engine & Deterministic Physics Planner (BLIND Mode)
# ==============================================================================

def _in_bounds(x: int, y: int) -> bool:
    return 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT


def _is_high_wall_tile(t: str, gates_flipped: bool) -> bool:
    if t in HIGH_WALL_STATIC:
        return True
    if not gates_flipped and t == "R_GATE":
        return True
    if gates_flipped and t == "B_GATE":
        return True
    return False


def _init_memory(state: dict, memory: dict) -> None:
    if memory.get("initialized"):
        return
    terrain = [
        [
            "T_W" if (x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1) else "UNKNOWN"
            for x in range(GRID_WIDTH)
        ]
        for y in range(GRID_HEIGHT)
    ]
    occupant = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    targets = state.get("targets", {})
    for kname in ("K1", "K2", "V"):
        if kname in targets:
            tx, ty = targets[kname]
            if _in_bounds(tx, ty):
                terrain[ty][tx] = kname

    memory["initialized"] = True
    memory["terrain"] = terrain
    memory["occupant"] = occupant
    memory["clue_cells"] = set()
    memory["seen_ever"] = set()
    memory["safe_mod3_cells"] = set()
    memory["confirmed_laser_cells"] = set()
    memory["laser_beams_by_dir"] = set()
    memory["visit_counts"] = collections.Counter()
    memory["pos_history"] = []
    memory["action_history"] = []
    memory["tried_throws"] = set()
    memory["tried_portals"] = set()
    memory["portal_dest"] = {}
    memory["last_pos"] = None
    memory["last_action"] = None
    memory["switches_flipped"] = 0
    memory["last_gates_flipped"] = bool(state.get("gates_flipped", False))


def _update_memory(state: dict, memory: dict) -> None:
    _init_memory(state, memory)
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    vis = state["visible_mask"]
    obs_t = state["terrain"]
    obs_o = state["occupant"]
    obs_c = state["clues"]
    turn = state["turn"]
    hx = state["hero"]["x"]
    hy = state["hero"]["y"]
    gates_flipped = bool(state.get("gates_flipped", False))

    if gates_flipped != memory["last_gates_flipped"]:
        memory["switches_flipped"] += 1
        memory["last_gates_flipped"] = gates_flipped

    last_pos = memory["last_pos"]
    last_act = memory["last_action"]
    if last_pos is not None and last_act is not None:
        lx, ly = last_pos
        if abs(hx - lx) + abs(hy - ly) > 4:
            memory["portal_dest"][(lx, ly, last_act)] = (hx, hy)

    for y in range(GRID_HEIGHT):
        row_vis = vis[y]
        for x in range(GRID_WIDTH):
            if row_vis[x]:
                t = obs_t[y][x]
                terrain[y][x] = t
                occupant[y][x] = obs_o[y][x]
                memory["seen_ever"].add((x, y))
                if obs_c[y][x]:
                    memory["clue_cells"].add((x, y))
                else:
                    memory["clue_cells"].discard((x, y))

    keys = state["hero"]["keys"]
    targets = state["targets"]
    if not keys[0]:
        k1x, k1y = targets["K1"]
        if terrain[k1y][k1x] == "UNKNOWN":
            terrain[k1y][k1x] = "K1"
    if not keys[1]:
        k2x, k2y = targets["K2"]
        if terrain[k2y][k2x] == "UNKNOWN":
            terrain[k2y][k2x] = "K2"
    vx, vy = targets["V"]
    if terrain[vy][vx] == "UNKNOWN":
        terrain[vy][vx] = "V"

    if turn % 3 == 0:
        warn_coords = set()
        for w in state.get("laser_warnings", []):
            wx, wy, wdir = w["x"], w["y"], w["dir"]
            warn_coords.add((wx, wy))
            memory["confirmed_laser_cells"].add((wx, wy))
            memory["laser_beams_by_dir"].add((wx, wy, wdir))
            dx, dy = DIRECTIONS[wdir]
            for step_i in range(1, 10):
                nx, ny = wx + step_i * dx, wy + step_i * dy
                if not _in_bounds(nx, ny):
                    break
                nt = terrain[ny][nx]
                if nt == "UNKNOWN" or _is_high_wall_tile(nt, gates_flipped) or occupant[ny][nx] in ("BOX", "TNT"):
                    break
                memory["confirmed_laser_cells"].add((nx, ny))
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if vis[y][x] and (x, y) not in warn_coords:
                    memory["safe_mod3_cells"].add((x, y))

    memory["visit_counts"][(hx, hy)] += 1
    memory["pos_history"].append((hx, hy))


def _classify_chests(memory: dict) -> typing.Tuple[set, set]:
    terrain = memory["terrain"]
    clues = memory["clue_cells"]
    seen = memory["seen_ever"]
    suspected_mimics = set()
    confirmed_heals = set()

    for y in range(1, GRID_HEIGHT - 1):
        for x in range(1, GRID_WIDTH - 1):
            if terrain[y][x] == "CHEST":
                has_clue = False
                all_seen = True
                for dx, dy in DIRECTIONS.values():
                    nx, ny = x + dx, y + dy
                    if (nx, ny) in clues:
                        has_clue = True
                    if (nx, ny) not in seen:
                        all_seen = False
                if has_clue:
                    suspected_mimics.add((x, y))
                elif all_seen:
                    confirmed_heals.add((x, y))
                else:
                    suspected_mimics.add((x, y))

    return suspected_mimics, confirmed_heals


def _get_laser_hazard_cells(memory: dict, gates_flipped: bool) -> set:
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    hazards = set(memory["confirmed_laser_cells"])

    for y in range(1, GRID_HEIGHT - 1):
        for x in range(1, GRID_WIDTH - 1):
            t = terrain[y][x]
            if t.startswith("LASER_"):
                ldir = t[-1]
                dx, dy = DIRECTIONS[ldir]
                for dist in range(1, 11):
                    rx, ry = x + dist * dx, y + dist * dy
                    if not _in_bounds(rx, ry):
                        break
                    rt = terrain[ry][rx]
                    if rt != "UNKNOWN" and _is_high_wall_tile(rt, gates_flipped):
                        break
                    if occupant[ry][rx] in ("BOX", "TNT"):
                        break
                    hazards.add((rx, ry))

    return hazards


def _has_unverified_laser_los(memory: dict, x: int, y: int, gates_flipped: bool) -> bool:
    if (x, y) in memory["safe_mod3_cells"]:
        return False
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    for dx, dy in DIRECTIONS.values():
        for dist in range(1, 11):
            rx, ry = x + dist * dx, y + dist * dy
            if not _in_bounds(rx, ry):
                break
            rt = terrain[ry][rx]
            if rt == "UNKNOWN":
                return True
            if _is_high_wall_tile(rt, gates_flipped) or occupant[ry][rx] in ("BOX", "TNT"):
                break
    return False


def _find_portal_in_grid(terrain: list, target_tile: str) -> typing.Optional[typing.Tuple[int, int]]:
    for y in range(1, GRID_HEIGHT - 1):
        for x in range(1, GRID_WIDTH - 1):
            if terrain[y][x] == target_tile:
                return (x, y)
    return None


def _sim_displace_box(
    terrain: list,
    occupant: list,
    hx: int,
    hy: int,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    cur_dir: str,
    gates_flipped: bool,
) -> dict:
    """
    Simulate pushing a BOX from (x0, y0) to (x1, y1) on a copy of terrain/occupant.
    """
    t_copy = [row[:] for row in terrain]
    o_copy = [row[:] for row in occupant]
    steps_taken = 0
    portal_count = 0
    suppress_portal_once = False
    tnt_armed = set()
    filled_pit = False
    flipped_switch = False

    def can_box_enter(nx: int, ny: int, gf: bool) -> bool:
        if not _in_bounds(nx, ny):
            return False
        nt = t_copy[ny][nx]
        if nt in ("UNKNOWN", "K1", "K2", "V") or _is_high_wall_tile(nt, gf):
            return False
        if o_copy[ny][nx] in ("BOX", "TNT"):
            return False
        if (nx, ny) == (hx, hy):
            return False
        return True

    while True:
        steps_taken += 1
        if t_copy[y0][x0] == "CRACK":
            t_copy[y0][x0] = "PIT"
        o_copy[y0][x0] = None
        o_copy[y1][x1] = "BOX"
        t1 = t_copy[y1][x1]
        if t1 == "PIT":
            o_copy[y1][x1] = None
            t_copy[y1][x1] = "EMPTY"
            filled_pit = True
            break
        elif t1 == "MIMIC":
            t_copy[y1][x1] = "EMPTY"
        elif t1 == "SWITCH":
            gates_flipped = not gates_flipped
            flipped_switch = True

        if steps_taken >= 32:
            break

        t_cur = t_copy[y1][x1]
        if suppress_portal_once:
            suppress_portal_once = False
            if portal_count >= 2:
                break
            dx, dy = DIRECTIONS[cur_dir]
            nx, ny = x1 + dx, y1 + dy
            if can_box_enter(nx, ny, gates_flipped):
                x0, y0, x1, y1 = x1, y1, nx, ny
                continue
            else:
                break

        if t_cur == "ICE":
            dx, dy = DIRECTIONS[cur_dir]
            nx, ny = x1 + dx, y1 + dy
            if can_box_enter(nx, ny, gates_flipped):
                x0, y0, x1, y1 = x1, y1, nx, ny
                continue
            else:
                break
        elif t_cur in MIRROR_MAP:
            cur_dir = MIRROR_MAP[t_cur][cur_dir]
            dx, dy = DIRECTIONS[cur_dir]
            nx, ny = x1 + dx, y1 + dy
            if can_box_enter(nx, ny, gates_flipped):
                x0, y0, x1, y1 = x1, y1, nx, ny
                continue
            else:
                break
        elif t_cur.startswith("SPRING_"):
            cur_dir = t_cur[-1]
            dx, dy = DIRECTIONS[cur_dir]
            blocked_k = None
            for k in (1, 2, 3):
                pkx, pky = x1 + k * dx, y1 + k * dy
                if not can_box_enter(pkx, pky, gates_flipped):
                    blocked_k = k
                    if _in_bounds(pkx, pky) and o_copy[pky][pkx] == "TNT":
                        tnt_armed.add((pkx, pky))
                    break
            if blocked_k == 1:
                break
            elif blocked_k in (2, 3):
                land_k = blocked_k - 1
                x0, y0, x1, y1 = x1, y1, x1 + land_k * dx, y1 + land_k * dy
                continue
            else:
                x0, y0, x1, y1 = x1, y1, x1 + 3 * dx, y1 + 3 * dy
                continue
        elif t_cur in PORTAL_PAIRS:
            p_pair = _find_portal_in_grid(t_copy, PORTAL_PAIRS[t_cur])
            if p_pair is None:
                break
            px, py = p_pair
            if o_copy[py][px] is not None or (px, py) == (hx, hy):
                break
            portal_count += 1
            suppress_portal_once = True
            x0, y0, x1, y1 = x1, y1, px, py
            continue
        else:
            break

    return {
        "terrain": t_copy,
        "occupant": o_copy,
        "gates_flipped": gates_flipped,
        "filled_pit": filled_pit,
        "flipped_switch": flipped_switch,
        "tnt_armed": tnt_armed,
    }


def _sim_displace_hero(
    terrain: list,
    occupant: list,
    hx: int,
    hy: int,
    x1: int,
    y1: int,
    cur_dir: str,
    hp: int,
    has_k1: bool,
    has_k2: bool,
    gates_flipped: bool,
    suspected_mimics: set,
    allow_unknown_step: bool = False,
    allow_unseen_portal: bool = False,
) -> dict:
    x0, y0 = hx, hy
    steps_taken = 0
    portal_count = 0
    stop_momentum = False
    suppress_portal_once = False
    exposed = {(hx, hy)}
    cracked_cells = []
    hit_unknown = False
    entered_unseen_portal = False
    cleared = False
    dead = False

    def can_enter(nx: int, ny: int) -> bool:
        if not _in_bounds(nx, ny):
            return False
        nt = terrain[ny][nx]
        if nt == "UNKNOWN":
            return allow_unknown_step
        if _is_high_wall_tile(nt, gates_flipped):
            return False
        if occupant[ny][nx] in ("BOX", "TNT"):
            return False
        return True

    while True:
        steps_taken += 1
        if terrain[y0][x0] == "CRACK":
            cracked_cells.append((x0, y0))
        hx, hy = x1, y1
        exposed.add((hx, hy))
        t1 = terrain[y1][x1]

        if t1 == "UNKNOWN":
            hit_unknown = True
            break

        if t1 == "PIT" or (x1, y1) in cracked_cells:
            hp -= 100
        elif t1 == "MIMIC" or (t1 == "CHEST" and (x1, y1) in suspected_mimics):
            hp -= 45
            stop_momentum = True
        elif t1 == "HEAL" or (t1 == "CHEST" and (x1, y1) not in suspected_mimics):
            hp = min(100, hp + 30)
        elif t1 == "SWITCH":
            gates_flipped = not gates_flipped

        if hp <= 0:
            dead = True
            break

        if t1 == "K1":
            has_k1 = True
        elif t1 == "K2":
            has_k2 = True
        elif t1 == "V" and has_k1 and has_k2 and hp > 0:
            cleared = True
            break

        if steps_taken >= 32 or stop_momentum:
            break

        if suppress_portal_once:
            suppress_portal_once = False
            if portal_count >= 2:
                break
            dx, dy = DIRECTIONS[cur_dir]
            nx, ny = x1 + dx, y1 + dy
            if can_enter(nx, ny):
                x0, y0, x1, y1 = x1, y1, nx, ny
                continue
            else:
                break

        if t1 == "ICE":
            dx, dy = DIRECTIONS[cur_dir]
            nx, ny = x1 + dx, y1 + dy
            if not _in_bounds(nx, ny):
                break
            if terrain[ny][nx] == "UNKNOWN":
                hit_unknown = True
                break
            if can_enter(nx, ny):
                x0, y0, x1, y1 = x1, y1, nx, ny
                continue
            else:
                break
        elif t1 in MIRROR_MAP:
            cur_dir = MIRROR_MAP[t1][cur_dir]
            dx, dy = DIRECTIONS[cur_dir]
            nx, ny = x1 + dx, y1 + dy
            if not _in_bounds(nx, ny):
                break
            if terrain[ny][nx] == "UNKNOWN":
                hit_unknown = True
                break
            if can_enter(nx, ny):
                x0, y0, x1, y1 = x1, y1, nx, ny
                continue
            else:
                break
        elif t1.startswith("SPRING_"):
            cur_dir = t1[-1]
            dx, dy = DIRECTIONS[cur_dir]
            blocked_k = None
            unknown_k = False
            for k in (1, 2, 3):
                pkx, pky = x1 + k * dx, y1 + k * dy
                if not _in_bounds(pkx, pky):
                    blocked_k = k
                    break
                pt = terrain[pky][pkx]
                if pt == "UNKNOWN":
                    unknown_k = True
                    break
                if _is_high_wall_tile(pt, gates_flipped) or occupant[pky][pkx] in ("BOX", "TNT"):
                    blocked_k = k
                    break
            if unknown_k:
                hit_unknown = True
                break
            if blocked_k == 1:
                break
            elif blocked_k in (2, 3):
                land_k = blocked_k - 1
                x0, y0, x1, y1 = x1, y1, x1 + land_k * dx, y1 + land_k * dy
                continue
            else:
                x0, y0, x1, y1 = x1, y1, x1 + 3 * dx, y1 + 3 * dy
                continue
        elif t1 in PORTAL_PAIRS:
            p_pair = _find_portal_in_grid(terrain, PORTAL_PAIRS[t1])
            if p_pair is None:
                entered_unseen_portal = True
                if not allow_unseen_portal:
                    hit_unknown = True
                break
            px, py = p_pair
            if occupant[py][px] is not None:
                break
            portal_count += 1
            suppress_portal_once = True
            x0, y0, x1, y1 = x1, y1, px, py
            continue
        else:
            break

    return {
        "x": hx,
        "y": hy,
        "hp": hp,
        "has_k1": has_k1,
        "has_k2": has_k2,
        "gates_flipped": gates_flipped,
        "exposed": exposed,
        "cracked_cells": cracked_cells,
        "hit_unknown": hit_unknown,
        "entered_unseen_portal": entered_unseen_portal,
        "cleared": cleared,
        "dead": dead,
        "steps_taken": steps_taken,
    }


def _sim_throw(
    terrain: list,
    occupant: list,
    hx: int,
    hy: int,
    d: str,
    gates_flipped: bool,
    suspected_mimics: set,
) -> dict:
    sx, sy = hx, hy
    cur_dir = d
    range_left = 6
    stone_portals = 0
    shattered = False
    stopped_on_portal = False
    hit_switch = False
    hit_tnt = None
    hit_mimic = None
    bounced_mirror = False
    slid_on_ice = False
    reached_unknown_after_mirror = False

    while range_left > 0:
        dx, dy = DIRECTIONS[cur_dir]
        sx, sy = sx + dx, sy + dy
        range_left -= 1
        if not _in_bounds(sx, sy):
            shattered = True
            break
        t = terrain[sy][sx]
        if t == "UNKNOWN":
            if bounced_mirror:
                reached_unknown_after_mirror = True
            shattered = True
            break
        if _is_high_wall_tile(t, gates_flipped) or occupant[sy][sx] == "BOX":
            shattered = True
            break
        if occupant[sy][sx] == "TNT":
            hit_tnt = (sx, sy)
            shattered = True
            break
        if t == "SWITCH":
            hit_switch = True
            shattered = True
            break
        if t == "MIMIC" or (t == "CHEST" and (sx, sy) in suspected_mimics):
            hit_mimic = (sx, sy)
            shattered = True
            break
        if t in MIRROR_MAP:
            cur_dir = MIRROR_MAP[t][cur_dir]
            bounced_mirror = True
        elif t in PORTAL_PAIRS and stone_portals < 2:
            p_pair = _find_portal_in_grid(terrain, PORTAL_PAIRS[t])
            if p_pair is not None and occupant[p_pair[1]][p_pair[0]] is None:
                sx, sy = p_pair
                stone_portals += 1
                if stone_portals == 2:
                    stopped_on_portal = True
                    break

    if not shattered and not stopped_on_portal and range_left == 0:
        t6 = terrain[sy][sx]
        if t6 == "ICE" or t6 in MIRROR_MAP:
            slid_on_ice = True
            for _ in range(32):
                dx, dy = DIRECTIONS[cur_dir]
                sx, sy = sx + dx, sy + dy
                if not _in_bounds(sx, sy):
                    break
                t = terrain[sy][sx]
                if t == "UNKNOWN":
                    reached_unknown_after_mirror = True
                    break
                if _is_high_wall_tile(t, gates_flipped) or occupant[sy][sx] == "BOX":
                    break
                if occupant[sy][sx] == "TNT":
                    hit_tnt = (sx, sy)
                    break
                if t == "SWITCH":
                    hit_switch = True
                    break
                if t == "MIMIC" or (t == "CHEST" and (sx, sy) in suspected_mimics):
                    hit_mimic = (sx, sy)
                    break
                if t in MIRROR_MAP:
                    cur_dir = MIRROR_MAP[t][cur_dir]
                    bounced_mirror = True
                elif t == "ICE":
                    pass
                elif t in PORTAL_PAIRS and stone_portals < 2:
                    p_pair = _find_portal_in_grid(terrain, PORTAL_PAIRS[t])
                    if p_pair is not None and occupant[p_pair[1]][p_pair[0]] is None:
                        sx, sy = p_pair
                        stone_portals += 1
                        if stone_portals == 2:
                            break
                    else:
                        break
                else:
                    break

    return {
        "hit_switch": hit_switch,
        "hit_tnt": hit_tnt,
        "hit_mimic": hit_mimic,
        "bounced_mirror": bounced_mirror,
        "slid_on_ice": slid_on_ice,
        "reached_unknown_after_mirror": reached_unknown_after_mirror,
    }


def _is_action_safe(
    state: dict,
    memory: dict,
    action: str,
    suspected_mimics: set,
    laser_hazards: set,
    allow_unknown_step: bool = False,
    allow_unseen_portal: bool = False,
    strict_mod3_slide: bool = True,
) -> typing.Optional[dict]:
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    hero = state["hero"]
    hx, hy = hero["x"], hero["y"]
    hp = hero["hp"]
    has_k1, has_k2 = bool(hero["keys"][0]), bool(hero["keys"][1])
    gates_flipped = bool(state.get("gates_flipped", False))
    turn = state["turn"]
    bombs = state.get("bombs", [])

    if action == "WAIT":
        res = {
            "x": hx, "y": hy, "hp": hp,
            "has_k1": has_k1, "has_k2": has_k2,
            "gates_flipped": gates_flipped,
            "exposed": {(hx, hy)},
            "cracked_cells": [],
            "hit_unknown": False,
            "entered_unseen_portal": False,
            "cleared": False,
            "dead": False,
            "steps_taken": 0,
        }
    elif action.startswith("MOVE_"):
        d = action[-1]
        dx, dy = DIRECTIONS[d]
        p1x, p1y = hx + dx, hy + dy
        if not _in_bounds(p1x, p1y):
            return None
        t1 = terrain[p1y][p1x]
        if t1 == "UNKNOWN" and not allow_unknown_step:
            return None
        if t1 != "UNKNOWN" and _is_high_wall_tile(t1, gates_flipped):
            return None
        if occupant[p1y][p1x] == "TNT":
            return None
        if occupant[p1y][p1x] == "BOX":
            p2x, p2y = hx + 2 * dx, hy + 2 * dy
            if not _in_bounds(p2x, p2y):
                return None
            t2 = terrain[p2y][p2x]
            if t2 in ("UNKNOWN", "K1", "K2", "V") or _is_high_wall_tile(t2, gates_flipped) or occupant[p2y][p2x] is not None:
                return None
            if terrain[p1y][p1x] == "CRACK":
                return None
            box_sim = _sim_displace_box(terrain, occupant, hx, hy, p1x, p1y, p2x, p2y, d, gates_flipped)
            if box_sim["tnt_armed"] and any(abs(hx - tx) <= 1 and abs(hy - ty) <= 1 for tx, ty in box_sim["tnt_armed"]):
                return None
            if box_sim["occupant"][p1y][p1x] is not None or _is_high_wall_tile(box_sim["terrain"][p1y][p1x], box_sim["gates_flipped"]):
                return None
            res = _sim_displace_hero(
                box_sim["terrain"], box_sim["occupant"], hx, hy, p1x, p1y, d,
                hp, has_k1, has_k2, box_sim["gates_flipped"], suspected_mimics,
                allow_unknown_step=allow_unknown_step,
                allow_unseen_portal=allow_unseen_portal,
            )
            res["box_pushed"] = True
            res["box_filled_pit"] = box_sim["filled_pit"]
            res["box_flipped_switch"] = box_sim["flipped_switch"]
        else:
            res = _sim_displace_hero(
                terrain, occupant, hx, hy, p1x, p1y, d,
                hp, has_k1, has_k2, gates_flipped, suspected_mimics,
                allow_unknown_step=allow_unknown_step,
                allow_unseen_portal=allow_unseen_portal,
            )
    elif action.startswith("JUMP_"):
        if hero["jumps"] <= 0:
            return None
        d = action[-1]
        dx, dy = DIRECTIONS[d]
        p1x, p1y = hx + dx, hy + dy
        p2x, p2y = hx + 2 * dx, hy + 2 * dy
        if not _in_bounds(p1x, p1y) or not _in_bounds(p2x, p2y):
            return None
        t1 = terrain[p1y][p1x]
        t2 = terrain[p2y][p2x]
        if t1 == "UNKNOWN" or _is_high_wall_tile(t1, gates_flipped):
            return None
        if t2 == "UNKNOWN" and not allow_unknown_step:
            return None
        if t2 != "UNKNOWN" and (_is_high_wall_tile(t2, gates_flipped) or occupant[p2y][p2x] in ("BOX", "TNT")):
            return None
        res = _sim_displace_hero(
            terrain, occupant, hx, hy, p2x, p2y, d,
            hp, has_k1, has_k2, gates_flipped, suspected_mimics,
            allow_unknown_step=allow_unknown_step,
            allow_unseen_portal=allow_unseen_portal,
        )
    else:
        return None

    if res["dead"] or res["hp"] <= 0:
        return None
    if res["cleared"]:
        return res
    if res["hit_unknown"] and not allow_unknown_step:
        return None

    fx, fy = res["x"], res["y"]

    for b in bombs:
        bx, by, btimer = b["x"], b["y"], b["timer"]
        if btimer <= 1 and abs(fx - bx) <= 1 and abs(fy - by) <= 1:
            return None

    if turn % 3 == 0:
        newly_exposed = res["exposed"] - {(hx, hy)}
        if newly_exposed & laser_hazards and strict_mod3_slide:
            return None
        if res["exposed"] & laser_hazards:
            if res["hp"] <= 50:
                return None
            res["hp"] -= 50

    if turn % 3 == 2 and (fx, fy) in laser_hazards:
        return None

    if strict_mod3_slide and res["steps_taken"] > 1:
        if turn % 3 in (0, 2) and _has_unverified_laser_los(memory, fx, fy, res["gates_flipped"]):
            return None

    return res


def _compute_reach_map(
    state: dict,
    memory: dict,
    suspected_mimics: set,
    laser_hazards: set,
    allow_jumps: bool = False,
    strict_mod3_slide: bool = True,
) -> dict:
    """
    Single-pass BFS computing shortest path `(first_action, depth)` from `(hx, hy)`
    to every reachable cell `(x, y)` on the map.
    """
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    hero = state["hero"]
    start_x, start_y = hero["x"], hero["y"]
    hp = hero["hp"]
    has_k1, has_k2 = bool(hero["keys"][0]), bool(hero["keys"][1])
    gates_flipped = bool(state.get("gates_flipped", False))
    start_jumps = hero["jumps"] if allow_jumps else 0
    turn = state["turn"]

    reach = {}
    q = collections.deque()
    visited = {(start_x, start_y, gates_flipped, 0)}
    q.append((start_x, start_y, hp, has_k1, has_k2, gates_flipped, 0, turn, None, 0))

    actions_to_try = ["MOVE_R", "MOVE_U", "MOVE_D", "MOVE_L"]
    if allow_jumps and start_jumps > 0:
        actions_to_try += ["JUMP_R", "JUMP_U", "JUMP_D", "JUMP_L"]

    max_expansions = 1600
    expansions = 0

    while q and expansions < max_expansions:
        cx, cy, chp, ck1, ck2, cgates, j_used, cturn, first_act, depth = q.popleft()
        expansions += 1
        if depth > 75:
            continue

        for act in actions_to_try:
            if act.startswith("JUMP_") and j_used >= start_jumps:
                continue
            d = act[-1]
            dx, dy = DIRECTIONS[d]
            if act.startswith("MOVE_"):
                p1x, p1y = cx + dx, cy + dy
                if not _in_bounds(p1x, p1y):
                    continue
                t1 = terrain[p1y][p1x]
                if t1 == "UNKNOWN" or _is_high_wall_tile(t1, cgates) or occupant[p1y][p1x] in ("BOX", "TNT"):
                    continue
                if depth == 0:
                    sim = _is_action_safe(
                        state, memory, act, suspected_mimics, laser_hazards,
                        allow_unknown_step=False, allow_unseen_portal=False,
                        strict_mod3_slide=strict_mod3_slide,
                    )
                    if sim is None:
                        continue
                else:
                    sim = _sim_displace_hero(
                        terrain, occupant, cx, cy, p1x, p1y, d,
                        chp, ck1, ck2, cgates, suspected_mimics,
                        allow_unknown_step=False, allow_unseen_portal=False,
                    )
                    if sim["dead"] or sim["hp"] <= 0 or sim["hit_unknown"]:
                        continue
                    if cturn % 3 == 0 and ((sim["exposed"] - {(cx, cy)}) & laser_hazards):
                        continue
                    if (sim["x"], sim["y"]) in laser_hazards and cturn % 3 in (2, 0):
                        continue
                nj = j_used
            else:
                p1x, p1y = cx + dx, cy + dy
                p2x, p2y = cx + 2 * dx, cy + 2 * dy
                if not _in_bounds(p1x, p1y) or not _in_bounds(p2x, p2y):
                    continue
                t1 = terrain[p1y][p1x]
                t2 = terrain[p2y][p2x]
                if t1 == "UNKNOWN" or _is_high_wall_tile(t1, cgates):
                    continue
                if t2 == "UNKNOWN" or _is_high_wall_tile(t2, cgates) or occupant[p2y][p2x] in ("BOX", "TNT"):
                    continue
                if t1 == "EMPTY" and (p1x, p1y) not in laser_hazards:
                    continue
                if depth == 0:
                    sim = _is_action_safe(
                        state, memory, act, suspected_mimics, laser_hazards,
                        allow_unknown_step=False, allow_unseen_portal=False,
                        strict_mod3_slide=strict_mod3_slide,
                    )
                    if sim is None:
                        continue
                else:
                    sim = _sim_displace_hero(
                        terrain, occupant, cx, cy, p2x, p2y, d,
                        chp, ck1, ck2, cgates, suspected_mimics,
                        allow_unknown_step=False, allow_unseen_portal=False,
                    )
                    if sim["dead"] or sim["hp"] <= 0 or sim["hit_unknown"]:
                        continue
                nj = j_used + 1

            nx, ny = sim["x"], sim["y"]
            ngates = sim["gates_flipped"]
            nfirst = act if first_act is None else first_act
            if (nx, ny) not in reach:
                reach[(nx, ny)] = (nfirst, depth + 1)

            skey = (nx, ny, ngates, nj)
            if skey not in visited:
                visited.add(skey)
                q.append((nx, ny, sim["hp"], sim["has_k1"], sim["has_k2"], ngates, nj, cturn + 1, nfirst, depth + 1))

    return reach


def _find_throw_opportunity(
    state: dict,
    memory: dict,
    suspected_mimics: set,
) -> typing.Optional[typing.Tuple[int, int, str]]:
    if state["hero"]["throws"] <= 0:
        return None
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    gates_flipped = bool(state.get("gates_flipped", False))
    tried = memory["tried_throws"]

    best_mirror_shot = None

    for y in range(1, GRID_HEIGHT - 1):
        for x in range(1, GRID_WIDTH - 1):
            t = terrain[y][x]
            if t in ("EMPTY", "K1", "K2", "SWITCH", "B_GATE", "R_GATE") and not _is_high_wall_tile(t, gates_flipped):
                if occupant[y][x] is not None:
                    continue
                for d in DIR_ORDER:
                    if (x, y, d, gates_flipped) in tried:
                        continue
                    tres = _sim_throw(terrain, occupant, x, y, d, gates_flipped, suspected_mimics)
                    if tres["hit_switch"]:
                        return (x, y, d)
                    if tres["bounced_mirror"] and (tres["slid_on_ice"] or tres["reached_unknown_after_mirror"]):
                        if best_mirror_shot is None:
                            best_mirror_shot = (x, y, d)

    return best_mirror_shot


def decide_action(state: dict, memory: dict) -> str:
    """
    Main Hero decision entrypoint for BLIND mode.
    Single-step execution time ~ 5-15ms (limit 500ms).
    """
    try:
        _update_memory(state, memory)
        terrain = memory["terrain"]
        occupant = memory["occupant"]
        hero = state["hero"]
        hx, hy = hero["x"], hero["y"]
        hp = hero["hp"]
        has_k1, has_k2 = bool(hero["keys"][0]), bool(hero["keys"][1])
        gates_flipped = bool(state.get("gates_flipped", False))
        turn = state["turn"]
        targets = state["targets"]
        bombs = state.get("bombs", [])

        suspected_mimics, confirmed_heals = _classify_chests(memory)
        laser_hazards = _get_laser_hazard_cells(memory, gates_flipped)

        def record_and_return(act: str) -> str:
            if act not in VALID_ACTIONS:
                act = "WAIT"
            memory["last_pos"] = (hx, hy)
            memory["last_action"] = act
            memory["action_history"].append(act)
            if act.startswith("THROW_"):
                memory["tried_throws"].add((hx, hy, act[-1], gates_flipped))
            return act

        # Detect if stuck oscillating in place recently
        recent_positions = memory["pos_history"][-12:]
        is_stuck_looping = recent_positions.count((hx, hy)) >= 4
        strict_slide = not is_stuck_looping

        # Compute single-pass reachability maps once per turn
        reach_no_jump = _compute_reach_map(
            state, memory, suspected_mimics, laser_hazards,
            allow_jumps=False, strict_mod3_slide=strict_slide,
        )
        reach_with_jump = None

        def get_reach_with_jump() -> dict:
            nonlocal reach_with_jump
            if reach_with_jump is None:
                reach_with_jump = _compute_reach_map(
                    state, memory, suspected_mimics, laser_hazards,
                    allow_jumps=True, strict_mod3_slide=strict_slide,
                )
            return reach_with_jump

        # 0. Emergency Escape from Active Bombs!
        in_bomb_radius = any(abs(hx - b["x"]) <= 1 and abs(hy - b["y"]) <= 1 for b in bombs)
        if in_bomb_radius:
            rj = get_reach_with_jump()
            best_esc = None
            best_dist = 999
            for (ex, ey), (f_act, dist) in rj.items():
                if not any(abs(ex - b["x"]) <= 1 and abs(ey - b["y"]) <= 1 for b in bombs):
                    if dist < best_dist:
                        best_dist = dist
                        best_esc = f_act
            if best_esc is not None:
                return record_and_return(best_esc)
            for d in DIR_ORDER:
                act = f"MOVE_{d}"
                sim = _is_action_safe(state, memory, act, suspected_mimics, laser_hazards, strict_mod3_slide=False)
                if sim is not None:
                    return record_and_return(act)

        # 1. Determine Active Goal Landmark(s)
        k1_pos = tuple(targets["K1"])
        k2_pos = tuple(targets["K2"])
        v_pos = tuple(targets["V"])

        if not has_k1 and not has_k2:
            d1 = abs(hx - k1_pos[0]) + abs(hy - k1_pos[1])
            d2 = abs(hx - k2_pos[0]) + abs(hy - k2_pos[1])
            active_goals = [k1_pos, k2_pos] if d1 <= d2 else [k2_pos, k1_pos]
        elif not has_k1:
            active_goals = [k1_pos]
        elif not has_k2:
            active_goals = [k2_pos]
        else:
            active_goals = [v_pos]

        # 2. Check immediate 1-step win
        for d in DIR_ORDER:
            for prefix in ("MOVE_", "JUMP_"):
                act = f"{prefix}{d}"
                sim = _is_action_safe(state, memory, act, suspected_mimics, laser_hazards)
                if sim is not None and sim["cleared"]:
                    return record_and_return(act)

        # 3. If HP <= 70 and a confirmed HEAL chest is reachable within 12 steps, grab it
        if hp <= 70 and confirmed_heals:
            for hpos in confirmed_heals:
                if hpos in reach_no_jump and reach_no_jump[hpos][1] <= 12:
                    return record_and_return(reach_no_jump[hpos][0])

        # 4. Direct Reachability to Active Goal Landmark(s)
        for gpos in active_goals:
            if gpos in reach_no_jump:
                return record_and_return(reach_no_jump[gpos][0])
        rj = get_reach_with_jump()
        for gpos in active_goals:
            if gpos in rj:
                return record_and_return(rj[gpos][0])

        # 5. Check if adjacent to an ICE slide blocked ONLY by strict_mod3_slide (Turn-6 Laser Guillotine protection!)
        if strict_slide and turn % 3 in (2, 0):
            for d in DIR_ORDER:
                dx, dy = DIRECTIONS[d]
                nx, ny = hx + dx, hy + dy
                if _in_bounds(nx, ny) and terrain[ny][nx] == "ICE":
                    sim_strict = _is_action_safe(state, memory, f"MOVE_{d}", suspected_mimics, laser_hazards, strict_mod3_slide=True)
                    sim_relaxed = _is_action_safe(state, memory, f"MOVE_{d}", suspected_mimics, laser_hazards, strict_mod3_slide=False)
                    if sim_strict is None and sim_relaxed is not None:
                        fx, fy = sim_relaxed["x"], sim_relaxed["y"]
                        if memory["visit_counts"][(fx, fy)] == 0:
                            wait_sim = _is_action_safe(state, memory, "WAIT", suspected_mimics, laser_hazards)
                            if wait_sim is not None:
                                return record_and_return("WAIT")

        # 6. Check if pushing an adjacent BOX fills a PIT or flips a SWITCH!
        for d in DIR_ORDER:
            act = f"MOVE_{d}"
            sim = _is_action_safe(state, memory, act, suspected_mimics, laser_hazards)
            if sim is not None and (sim.get("box_filled_pit") or sim.get("box_flipped_switch")):
                return record_and_return(act)

        # 7. Check if a remote THROW opportunity (for SWITCH or MIRROR+ICE slide) is available
        if memory["switches_flipped"] == 0 and hero["throws"] > 0:
            throw_opp = _find_throw_opportunity(state, memory, suspected_mimics)
            if throw_opp is not None:
                tx, ty, td = throw_opp
                if (hx, hy) == (tx, ty):
                    return record_and_return(f"THROW_{td}")
                if (tx, ty) in reach_no_jump:
                    return record_and_return(reach_no_jump[(tx, ty)][0])

        # 8. Frontier Exploration using precomputed reachability map!
        primary_goal = active_goals[0]
        best_frontier_act = None
        best_frontier_score = 999999

        for (x, y), (f_act, dist) in reach_no_jump.items():
            if memory["visit_counts"][(x, y)] > 0:
                continue
            unk_count = 0
            for dy in range(-3, 4):
                ny = y + dy
                if 1 <= ny < GRID_HEIGHT - 1:
                    for dx in range(-3, 4):
                        if dx * dx + dy * dy <= 10:
                            nx = x + dx
                            if 1 <= nx < GRID_WIDTH - 1 and terrain[ny][nx] == "UNKNOWN":
                                unk_count += 1
            if unk_count > 0:
                gdist = abs(x - primary_goal[0]) + abs(y - primary_goal[1])
                score = gdist * 2 + dist * 2 - unk_count * 2
                if score < best_frontier_score:
                    best_frontier_score = score
                    best_frontier_act = f_act

        if best_frontier_act is not None:
            return record_and_return(best_frontier_act)

        # Try frontier with jumps if no frontier is reachable without jumps
        for (x, y), (f_act, dist) in rj.items():
            if memory["visit_counts"][(x, y)] > 0:
                continue
            unk_count = 0
            for dy in range(-3, 4):
                ny = y + dy
                if 1 <= ny < GRID_HEIGHT - 1:
                    for dx in range(-3, 4):
                        if dx * dx + dy * dy <= 10:
                            nx = x + dx
                            if 1 <= nx < GRID_WIDTH - 1 and terrain[ny][nx] == "UNKNOWN":
                                unk_count += 1
            if unk_count > 0:
                gdist = abs(x - primary_goal[0]) + abs(y - primary_goal[1])
                score = gdist * 2 + dist * 2 - unk_count * 2
                if score < best_frontier_score:
                    best_frontier_score = score
                    best_frontier_act = f_act

        if best_frontier_act is not None:
            return record_and_return(best_frontier_act)

        # 9. Walkable SWITCH activation
        if memory["switches_flipped"] == 0:
            for y in range(1, GRID_HEIGHT - 1):
                for x in range(1, GRID_WIDTH - 1):
                    if terrain[y][x] == "SWITCH" and memory["visit_counts"][(x, y)] == 0:
                        if (x, y) in rj:
                            return record_and_return(rj[(x, y)][0])

        # 10. Direction-Smart Portal Exploration (prefer entering from East via MOVE_L first!)
        portal_entries = []
        for y in range(1, GRID_HEIGHT - 1):
            for x in range(1, GRID_WIDTH - 1):
                if terrain[y][x] in PORTAL_PAIRS:
                    preferred_neighbors = [
                        (x + 1, y, "MOVE_L", 0),
                        (x, y - 1, "MOVE_D", 1),
                        (x, y + 1, "MOVE_U", 2),
                        (x - 1, y, "MOVE_R", 3),
                    ]
                    for nx, ny, pact, prio in preferred_neighbors:
                        if _in_bounds(nx, ny) and (x, y, pact) not in memory["tried_portals"]:
                            nt = terrain[ny][nx]
                            if nt not in ("UNKNOWN", "PIT") and not _is_high_wall_tile(nt, gates_flipped):
                                portal_entries.append((prio, nx, ny, x, y, pact))

        portal_entries.sort(key=lambda item: item[0])
        for _, nx, ny, px, py, pact in portal_entries:
            if (hx, hy) == (nx, ny):
                sim = _is_action_safe(
                    state, memory, pact, suspected_mimics, laser_hazards,
                    allow_unknown_step=True, allow_unseen_portal=True, strict_mod3_slide=False,
                )
                if sim is not None:
                    memory["tried_portals"].add((px, py, pact))
                    return record_and_return(pact)
            elif (nx, ny) in rj:
                return record_and_return(rj[(nx, ny)][0])

        # 11. Try stepping onto SPRING_* whose landing is in UNKNOWN
        for y in range(1, GRID_HEIGHT - 1):
            for x in range(1, GRID_HEIGHT - 1):
                if terrain[y][x].startswith("SPRING_") and memory["visit_counts"][(x, y)] == 0:
                    if (x, y) in reach_no_jump:
                        return record_and_return(reach_no_jump[(x, y)][0])
                    for d in DIR_ORDER:
                        dx, dy = DIRECTIONS[d]
                        if (hx + dx, hy + dy) == (x, y):
                            return record_and_return(f"MOVE_{d}")

        # 12. Try using BOMB to breach a destructible W wall or closed gate blocking the goal
        if hero["bombs"] > 0 and not bombs:
            best_bomb_spot = None
            best_bomb_dist = 9999
            for y in range(1, GRID_HEIGHT - 1):
                for x in range(1, GRID_WIDTH - 1):
                    if (x, y) == (hx, hy) or (x, y) in reach_no_jump:
                        if terrain[y][x] == "EMPTY" and occupant[y][x] is None:
                            adj_destructible = False
                            for dx, dy in DIRECTIONS.values():
                                nx, ny = x + dx, y + dy
                                if _in_bounds(nx, ny) and terrain[ny][nx] in ("W", "R_GATE", "B_GATE", "LASER_U", "LASER_D", "LASER_L", "LASER_R"):
                                    adj_destructible = True
                                    break
                            if adj_destructible:
                                d_goal = abs(x - primary_goal[0]) + abs(y - primary_goal[1])
                                if d_goal < best_bomb_dist:
                                    best_bomb_dist = d_goal
                                    best_bomb_spot = (x, y)
            if best_bomb_spot is not None:
                if (hx, hy) == best_bomb_spot:
                    can_escape = False
                    for d in DIR_ORDER:
                        dx, dy = DIRECTIONS[d]
                        nx, ny = hx + dx, hy + dy
                        if _in_bounds(nx, ny) and terrain[ny][nx] == "EMPTY" and occupant[ny][nx] is None:
                            for d2 in DIR_ORDER:
                                dx2, dy2 = DIRECTIONS[d2]
                                nnx, nny = nx + dx2, ny + dy2
                                if _in_bounds(nnx, nny) and (abs(nnx - hx) > 1 or abs(nny - hy) > 1):
                                    if terrain[nny][nnx] == "EMPTY" and occupant[nny][nnx] is None:
                                        can_escape = True
                    if can_escape:
                        return record_and_return("BOMB")
                elif best_bomb_spot in reach_no_jump:
                    return record_and_return(reach_no_jump[best_bomb_spot][0])

        # 13. Fallback: pick the least-visited safe move
        best_act = "WAIT"
        best_score = 999999
        for d in DIR_ORDER:
            act = f"MOVE_{d}"
            sim = _is_action_safe(state, memory, act, suspected_mimics, laser_hazards, allow_unknown_step=True, strict_mod3_slide=False)
            if sim is not None:
                fx, fy = sim["x"], sim["y"]
                v_cnt = memory["visit_counts"][(fx, fy)]
                g_dist = abs(fx - primary_goal[0]) + abs(fy - primary_goal[1])
                sc = v_cnt * 20 + g_dist
                if sc < best_score:
                    best_score = sc
                    best_act = act

        return record_and_return(best_act)
    except Exception:
        return "WAIT"
