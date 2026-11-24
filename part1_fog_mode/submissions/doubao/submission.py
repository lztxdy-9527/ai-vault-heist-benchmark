"""
《阴间地牢：金库攻防战》参赛提交 (submission.py)
- build_dungeon(): 魔王造图 + 自证通关
- decide_action(state, memory): BLIND 迷雾模式勇者单步决策
"""

import bisect
import collections
import copy
import dataclasses
import enum
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

# ==============================================================================
# 官方规则常量定义
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

DIR_VEC = {
    "U": (0, -1),
    "D": (0, 1),
    "L": (-1, 0),
    "R": (1, 0),
}

DIR_NAME = {(0, -1): "U", (0, 1): "D", (-1, 0): "L", (1, 0): "R"}

MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}


# ==============================================================================
# 工具函数
# ==============================================================================

def in_bounds(x, y):
    return 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT


def is_high_wall(terrain_cell, gates_flipped):
    if terrain_cell in ("W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R"):
        return True
    if terrain_cell == "R_GATE":
        return not gates_flipped
    if terrain_cell == "B_GATE":
        return gates_flipped
    return False


def laser_blocked_cells(terrain, occupant, gates_flipped, turn):
    """根据已知地形估算激光束危险格（turn % 3 == 0 时）。"""
    cells = set()
    if turn % 3 != 0:
        return cells
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            t = terrain[y][x]
            if t in ("LASER_U", "LASER_D", "LASER_L", "LASER_R"):
                if t == "LASER_U":
                    dx, dy = 0, -1
                elif t == "LASER_D":
                    dx, dy = 0, 1
                elif t == "LASER_L":
                    dx, dy = -1, 0
                else:
                    dx, dy = 1, 0
                for d in range(1, 11):
                    nx, ny = x + dx * d, y + dy * d
                    if not in_bounds(nx, ny):
                        break
                    nt = terrain[ny][nx]
                    no = occupant[ny][nx]
                    if is_high_wall(nt, gates_flipped) or no == "BOX":
                        break
                    cells.add((nx, ny))
    return cells


# ==============================================================================
# 参赛入口 1：魔王造图与自证函数
# ==============================================================================

def build_dungeon() -> dict:
    grid = [
        [
            "T_W" if (x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1) else "EMPTY"
            for x in range(GRID_WIDTH)
        ]
        for y in range(GRID_HEIGHT)
    ]

    grid[5][20] = "K1"
    grid[20][20] = "K2"
    grid[13][35] = "V"

    pits = [
        (5, 3), (8, 3), (11, 3), (14, 3),
        (5, 22), (8, 22), (11, 22), (14, 22),
        (30, 3), (30, 22),
        (33, 7), (33, 8), (33, 17), (33, 18),
        (16, 7), (16, 18),
    ]
    for x, y in pits:
        grid[y][x] = "PIT"

    mimics = [(10, 3), (10, 22), (28, 3), (28, 22)]
    for x, y in mimics:
        grid[y][x] = "MIMIC"

    grid[3][35] = "LASER_D"

    walls = [
        (6, 6), (7, 6), (8, 6),
        (6, 19), (7, 19), (8, 19),
        (24, 6), (25, 6), (26, 6),
        (24, 19), (25, 19), (26, 19),
        (30, 10), (30, 11), (30, 15), (30, 16),
        (12, 10), (12, 11), (12, 15), (12, 16),
    ]
    for x, y in walls:
        grid[y][x] = "W"

    author_solution = (
        ["MOVE_R"] * 18
        + ["MOVE_U"] * 8
        + ["MOVE_D"] * 15
        + ["MOVE_U"] * 7
        + ["MOVE_R"] * 15
    )

    return {
        "taunt": "ASTRA、SOL、CARBON、HYDROGEN、Claude、DeepSeek、Qwen、Kimi、GLM、混元，金库归我！",
        "grid": grid,
        "author_solution": author_solution,
    }


# ==============================================================================
# 参赛入口 2：勇者单步决策函数
# ==============================================================================

def _init_memory(memory):
    if "terrain" not in memory:
        memory["terrain"] = [["UNKNOWN" for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        memory["occupant"] = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        memory["clues"] = [[False for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        memory["turn_visited"] = {}


def _update_memory(state, memory):
    terrain_view = state["terrain"]
    occupant_view = state["occupant"]
    clues_view = state["clues"]
    visible = state["visible_mask"]
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if visible[y][x]:
                memory["terrain"][y][x] = terrain_view[y][x]
                memory["occupant"][y][x] = occupant_view[y][x]
                memory["clues"][y][x] = clues_view[y][x]


def _is_mimic(memory, x, y):
    """若 CHEST 四邻中有骸骨线索，则判定为 MIMIC。"""
    if memory["terrain"][y][x] != "CHEST":
        return False
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nx, ny = x + dx, y + dy
        if in_bounds(nx, ny) and memory["clues"][ny][nx]:
            return True
    return False


def _walkable_cost(memory, x, y, gates_flipped):
    if not in_bounds(x, y):
        return float("inf")
    t = memory["terrain"][y][x]
    o = memory["occupant"][y][x]
    if is_high_wall(t, gates_flipped):
        return float("inf")
    if o == "TNT":
        return float("inf")
    if o == "BOX":
        return float("inf")
    if t == "PIT":
        return float("inf")
    if t == "MIMIC":
        return float("inf")
    if t == "CHEST":
        if _is_mimic(memory, x, y):
            return float("inf")
        return 6
    if t == "CRACK":
        return 40
    if t == "UNKNOWN":
        return 3
    if t == "ICE":
        return 4
    if t.startswith("MIRROR_"):
        return 6
    if t.startswith("SPRING_"):
        return 10
    if t.startswith("PORTAL_"):
        return 10
    return 1


def _find_path(memory, start, target, gates_flipped, laser_cells, jumps_left):
    terrain = memory["terrain"]
    occupant = memory["occupant"]

    pq = [(0, start[0], start[1], jumps_left)]
    best = {(start[0], start[1], jumps_left): 0}
    parent = {}

    dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    while pq:
        cost, x, y, j = heapq.heappop(pq)
        if (x, y) == target:
            path = []
            cur = (x, y, j)
            while cur in parent:
                px, py, pj, act = parent[cur]
                path.append((act, (cur[0], cur[1])))
                cur = (px, py, pj)
            path.reverse()
            return path
        if cost > best.get((x, y, j), float("inf")):
            continue

        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if (nx, ny) in laser_cells:
                continue
            c = _walkable_cost(memory, nx, ny, gates_flipped)
            if c == float("inf"):
                continue
            nc = cost + c
            state = (nx, ny, j)
            if nc < best.get(state, float("inf")):
                best[state] = nc
                parent[state] = (x, y, j, "MOVE")
                heapq.heappush(pq, (nc, nx, ny, j))

        if j > 0:
            for dx, dy in dirs:
                p1x, p1y = x + dx, y + dy
                p2x, p2y = x + 2 * dx, y + 2 * dy
                if not in_bounds(p1x, p1y) or not in_bounds(p2x, p2y):
                    continue
                t1 = terrain[p1y][p1x]
                t2 = terrain[p2y][p2x]
                if is_high_wall(t1, gates_flipped):
                    continue
                if is_high_wall(t2, gates_flipped):
                    continue
                if occupant[p2y][p2x] in ("BOX", "TNT"):
                    continue
                if (p2x, p2y) in laser_cells:
                    continue
                c2 = _walkable_cost(memory, p2x, p2y, gates_flipped)
                if c2 == float("inf"):
                    continue
                nc = cost + c2 + 1
                state = (p2x, p2y, j - 1)
                if nc < best.get(state, float("inf")):
                    best[state] = nc
                    parent[state] = (x, y, j, "JUMP")
                    heapq.heappush(pq, (nc, p2x, p2y, j - 1))

    return None


def _find_explore_target(memory, start, gates_flipped):
    """找到最近的 UNKNOWN 格子，用于探索。"""
    terrain = memory["terrain"]
    visited = set()
    q = collections.deque([(start[0], start[1], 0)])
    visited.add((start[0], start[1]))
    dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    while q:
        x, y, d = q.popleft()
        if terrain[y][x] == "UNKNOWN" and d > 0:
            return (x, y)
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if not in_bounds(nx, ny) or (nx, ny) in visited:
                continue
            t = terrain[ny][nx]
            if is_high_wall(t, gates_flipped):
                continue
            if t == "PIT" or t == "MIMIC":
                continue
            if memory["occupant"][ny][nx] in ("BOX", "TNT"):
                continue
            visited.add((nx, ny))
            q.append((nx, ny, d + 1))
    return None


def _action_from_delta(dx, dy, action_type="MOVE"):
    sx = 1 if dx > 0 else (-1 if dx < 0 else 0)
    sy = 1 if dy > 0 else (-1 if dy < 0 else 0)
    dname = DIR_NAME.get((sx, sy))
    if dname is None:
        return "WAIT"
    return f"{action_type}_{dname}"


def decide_action(state: dict, memory: dict) -> str:
    _init_memory(memory)
    _update_memory(state, memory)

    hero = state["hero"]
    hx, hy = hero["x"], hero["y"]
    turn = state["turn"]
    gates_flipped = state["gates_flipped"]
    targets = state["targets"]
    jumps_left = hero["jumps"]

    has_k1, has_k2 = hero["keys"]
    if not has_k1 and not has_k2:
        k1 = tuple(targets["K1"])
        k2 = tuple(targets["K2"])
        d1 = abs(hx - k1[0]) + abs(hy - k1[1])
        d2 = abs(hx - k2[0]) + abs(hy - k2[1])
        target = k1 if d1 <= d2 else k2
    elif has_k1 and not has_k2:
        target = tuple(targets["K2"])
    elif not has_k1 and has_k2:
        target = tuple(targets["K1"])
    else:
        target = tuple(targets["V"])

    laser_cells = laser_blocked_cells(memory["terrain"], memory["occupant"], gates_flipped, turn)
    for lw in state.get("laser_warnings", []):
        laser_cells.add((lw["x"], lw["y"]))

    path = _find_path(memory, (hx, hy), target, gates_flipped, laser_cells, jumps_left)

    if path:
        act, _ = path[0]
        dx = 0
        dy = 0
        if act == "MOVE":
            nxt = path[0][1]
            dx = nxt[0] - hx
            dy = nxt[1] - hy
            return _action_from_delta(dx, dy, "MOVE")
        elif act == "JUMP":
            nxt = path[0][1]
            dx = nxt[0] - hx
            dy = nxt[1] - hy
            return _action_from_delta(dx, dy, "JUMP")

    explore_target = _find_explore_target(memory, (hx, hy), gates_flipped)
    if explore_target:
        path2 = _find_path(memory, (hx, hy), explore_target, gates_flipped, laser_cells, jumps_left)
        if path2:
            act, nxt = path2[0]
            dx = nxt[0] - hx
            dy = nxt[1] - hy
            return _action_from_delta(dx, dy, act)

    has_bomb_here = any(b["x"] == hx and b["y"] == hy for b in state.get("bombs", []))

    for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
        nx, ny = hx + dx, hy + dy
        if in_bounds(nx, ny):
            t = memory["terrain"][ny][nx]
            if t == "W" and hero["bombs"] > 0 and not has_bomb_here:
                return "BOMB"

    if has_bomb_here:
        return "WAIT"

    for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
        nx, ny = hx + dx, hy + dy
        c = _walkable_cost(memory, nx, ny, gates_flipped)
        if c != float("inf") and (nx, ny) not in laser_cells:
            return _action_from_delta(dx, dy, "MOVE")

    return "WAIT"