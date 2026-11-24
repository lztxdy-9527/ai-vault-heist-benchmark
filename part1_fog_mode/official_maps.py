# -*- coding: utf-8 -*-
"""
Official Benchmark Maps & Backup Slot Maps (`official_maps.py`)
Every map here is 100% verified against `engine.verify_author_solution()`.
"""

from typing import Any, Dict, List
from engine import GRID_W, GRID_H, verify_author_solution


def _empty_framed_grid() -> List[List[str]]:
    g = [["EMPTY"] * GRID_W for _ in range(GRID_H)]
    for y in range(GRID_H):
        for x in range(GRID_W):
            if x in (0, GRID_W - 1) or y in (0, GRID_H - 1):
                g[y][x] = "T_W"
    return g


def build_official_map_1_laser_ice() -> Dict[str, Any]:
    """
    Official Map 1: 《冰火激光长廊》(Ice Slide & Laser Corridor)
    Tests ice slide momentum, mirror deflection, and Turn % 3 == 0 laser timing.
    """
    g = _empty_framed_grid()
    g[5][20] = "K1"
    g[20][20] = "K2"
    g[13][35] = "V"

    # Ice speedway from (5,5) to (19,5) towards K1(20,5)
    for x in range(5, 20):
        g[5][x] = "ICE"
    # Ice speedway from (20,6) to (20,19) towards K2(20,20)
    for y in range(6, 20):
        g[y][20] = "ICE"
    # Laser cannons guarding the central lane (avoiding path on non-multiples of 3)
    g[2][10] = "LASER_D"
    g[23][28] = "LASER_U"

    # Author solution:
    # From (2,13) -> U*8 to (2,5) -> R*3 to (5,5) [slides to (20,5) K1!]
    # -> D*1 to (20,6) [slides to (20,20) K2!]
    # -> R*1 to (21,20) [step off ice column] -> U*7 to (21,13) -> R*14 to (35,13) V!
    sol = (
        ["MOVE_U"] * 8
        + ["MOVE_R"] * 3
        + ["MOVE_D"] * 1
        + ["MOVE_R"] * 1
        + ["MOVE_U"] * 7
        + ["MOVE_R"] * 14
    )
    return {
        "id": "OFFICIAL_01",
        "name": "官方一图：冰火激光长廊",
        "taunt": "顺着冰道一滑到底，但小心三回合一次的激光点名！",
        "grid": g,
        "author_solution": sol,
    }


def build_official_map_2_bomb_switch_lock() -> Dict[str, Any]:
    """
    Official Map 2: 《红门炸弹生死锁》(Astra 105G Resource Lock Benchmark)
    Tests bomb conservation vs. red gate switch logic.
    """
    g = _empty_framed_grid()
    g[5][20] = "K1"
    g[20][20] = "K2"
    g[13][35] = "V"

    for kx, ky in [(20, 5), (20, 20)]:
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            g[ky + dy][kx + dx] = "W"

    g[13][34] = "R_GATE"
    g[12][35] = "W"
    g[14][35] = "W"
    g[13][36] = "W"
    g[13][4] = "SWITCH"

    tokens = "R*2 U*8 R*14 B L*2 R*4 L*2 D*15 B L*2 R*4 L*2 U*7 R*17".split()
    sol: List[str] = []
    for tok in tokens:
        if tok == "B":
            sol.append("BOMB")
        else:
            d, count = tok.split("*")
            sol.extend([f"MOVE_{d}"] * int(count))

    return {
        "id": "OFFICIAL_02",
        "name": "官方二图：105G 红门炸弹生死锁",
        "taunt": "两颗炸弹三道锁，炸错一堵墙就永远留在这里吧！",
        "grid": g,
        "author_solution": sol,
    }


def build_official_map_3_mimic_portal_fortress() -> Dict[str, Any]:
    """
    Official Map 3: 《真假宝箱双子阵》(Mimic Clue & Twin Portals)
    Tests portal teleportation, crack bridges, and mimic clue avoidance.
    """
    g = _empty_framed_grid()
    g[5][20] = "K1"
    g[20][20] = "K2"
    g[13][35] = "V"

    # Place Mimics off the main path with valid empty clue cells
    g[8][10] = "MIMIC"
    g[18][10] = "MIMIC"
    g[13][25] = "HEAL"

    # Portal shortcut from (6,13) to (19,5) right next to K1(20,5)!
    g[13][6] = "PORTAL_1A"
    g[5][19] = "PORTAL_1B"

    # Crack bridge below K1
    g[6][20] = "CRACK"
    g[7][20] = "CRACK"

    # Author solution:
    # From (2,13) -> MOVE_R * 4 enters PORTAL_1A(6,13) -> teleports to (19,5) and steps 1 tile R onto K1(20,5)!
    # Then D*15 to K2(20,20) -> U*7 to (20,13) -> R*15 to V(35,13) (passes through HEAL at (25,13))
    sol = (
        ["MOVE_R"] * 4
        + ["MOVE_D"] * 15
        + ["MOVE_U"] * 7
        + ["MOVE_R"] * 15
    )
    return {
        "id": "OFFICIAL_03",
        "name": "官方三图：真假宝箱双子阵",
        "taunt": "传送门直通钥匙，但退路一旦踩碎就再也回不来了！",
        "grid": g,
        "author_solution": sol,
    }


def get_all_official_maps() -> List[Dict[str, Any]]:
    maps = [
        build_official_map_1_laser_ice(),
        build_official_map_2_bomb_switch_lock(),
        build_official_map_3_mimic_portal_fortress(),
    ]
    for m in maps:
        ver = verify_author_solution(m["grid"], m["author_solution"])
        if not ver["valid"]:
            raise RuntimeError(f"Official map {m['id']} failed verification: {ver['reason']}")
        m["spent_gold"] = ver["spent_gold"]
        m["vault_gold"] = ver["vault_gold"]
        m["author_steps"] = ver["author_steps"]
    return maps


if __name__ == "__main__":
    for m in get_all_official_maps():
        print(f"[VERIFIED] {m['id']} ({m['name']}): spent={m['spent_gold']}G, steps={m['author_steps']}")
