"""
《阴间地牢：金库攻防战》参赛选手提交模板 (submission_template.py)
请将最终代码保存为 `submission.py`，可自由使用 Python 计算/算法标准库与预装科学计算库（如 numpy、networkx、sympy）及常规类私有成员（self._xxx），严禁文件 I/O、网络、进程控制与双下划线反射。
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
SPAWN_POS = (2, 13)  # (x, y)，周围 3x3 即 x in [1..3], y in [12..14] 必须保持 "EMPTY"

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

# 90度折跃斜坡映射表：MIRROR_MAP[tile_type][incoming_dir] -> outgoing_dir
MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},  # ↗
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},  # ↘
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},  # ↙
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},  # ↖
}

# 单品造价表（最外圈 x in {0,39} 或 y in {0,25} 的 T_W 免费且不占配额；PORTAL 按每对 80G 计费）
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


# ==============================================================================
# 参赛入口 1：魔王造图与自证函数
# ==============================================================================

def build_dungeon() -> dict:
    """
    构建 40x26 的地下城，并提供恰好在最后一步存活踏入 V 通关的 author_solution。
    单次调用限时：2.0 秒。
    """
    grid = [
        [
            "T_W" if (x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1) else "EMPTY"
            for x in range(GRID_WIDTH)
        ]
        for y in range(GRID_HEIGHT)
    ]

    # TODO: 实现 build_dungeon
    grid[5][20] = "K1"
    grid[20][20] = "K2"
    grid[13][35] = "V"

    author_solution = (
        ["MOVE_R"] * 18
        + ["MOVE_U"] * 8
        + ["MOVE_D"] * 15
        + ["MOVE_U"] * 7
        + ["MOVE_R"] * 15
    )

    return {
        "taunt": "",
        "grid": grid,
        "author_solution": author_solution,
    }


# ==============================================================================
# 参赛入口 2：勇者单步决策函数
# ==============================================================================

def decide_action(state: dict, memory: dict) -> str:
    """
    根据当前回合状态 state 与持久化字典 memory，返回本回合动作字符串。
    单步调用限时：0.5 秒。
    """
    # TODO: 实现 decide_action
    return "WAIT"
