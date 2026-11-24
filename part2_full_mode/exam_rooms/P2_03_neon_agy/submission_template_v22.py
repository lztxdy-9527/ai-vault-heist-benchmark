"""
《阴间地牢：金库攻防战》下半场 FULL 全图明牌双重构提交参考模板 (submission_template_v22.py)
请保存并直接覆盖你考场目录下的 `submission.py`。
"""

import bisect
import collections
import copy
import heapq
import itertools
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


def build_dungeon() -> dict:
    """
    v2.2 魔王造图：支持 PLATE/P_GATE/LASER2/ONEWAY。
    红线：外圈全 "T_W"；len(taunt) <= 40 字符；author_solution <= 200 步且须通过前4回合出生准入；
    全文件禁用 __slots__ / __new__ 等一切以 `__` 开头的名称或属性。
    """
    raise NotImplementedError


def decide_action(state: dict, memory: dict) -> str:
    """v2.2 FULL 明牌勇者：Turn 1 限时 2.0s，Turn 2..240 限时 0.5s。"""
    raise NotImplementedError
