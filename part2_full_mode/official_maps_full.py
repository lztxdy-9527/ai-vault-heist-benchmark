# -*- coding: utf-8 -*-
"""
Official v2.2 FULL Benchmark Maps & Sealed Backup Maps (`official_maps_full.py`)
Half 2 (FULL 全图明牌攻守双重构赛)

Contains:
- 3 Official Benchmark Stage-1 Maps (covering all 3 new Scheme-C mechanics)
- 2 Distinct Pre-Sealed Backup Maps for any Demon DQ slots
Every map is verified 100% against `engine_full.verify_author_solution()`.
"""

from __future__ import annotations
import hashlib
import json
from typing import Any, Dict, List
import engine_full as engine


def _empty_framed_grid() -> List[List[str]]:
    g = [["EMPTY"] * engine.GRID_W for _ in range(engine.GRID_H)]
    for y in range(engine.GRID_H):
        for x in range(engine.GRID_W):
            if x in (0, engine.GRID_W - 1) or y in (0, engine.GRID_H - 1):
                g[y][x] = "T_W"
    return g


def build_official_full_1_sokoban_plates() -> Dict[str, Any]:
    """
    OFFICIAL_FULL_01: 《黄金压板推箱库》
    Tests BOX-only PLATE + P_GATE, BOX sliding on ICE onto PLATE,
    and 2-wide PIT + BOX bridge right before the P_GATE-sealed Vault.
    """
    g = _empty_framed_grid()
    g[5][20] = "K1"
    g[20][20] = "K2"
    g[13][35] = "V"

    # Seal K1(20,5) on 3 sides + P_GATE at (20,6) so K1 only opens after plates active
    g[4][20] = "T_W"
    g[5][19] = "T_W"
    g[5][21] = "T_W"
    g[4][19] = "T_W"
    g[4][21] = "T_W"
    g[6][20] = "P_GATE"

    # Seal V(35,13) inside T_W vault behind P_GATE(34,13) and 2-wide PIT moat at (32..33, 13)
    for y in (12, 14):
        for x in range(32, 37):
            g[y][x] = "T_W"
    g[13][36] = "T_W"
    g[13][34] = "P_GATE"
    g[13][33] = "PIT"
    g[13][32] = "PIT"
    g[13][30] = "BOX"  # Bridge box to fill (32,13), then jump over (33,13) onto P_GATE(34,13)

    # Plate 1 puzzle: push BOX(13,7) R twice onto PLATE(15,7)
    g[7][13] = "BOX"
    g[7][15] = "PLATE"
    g[6][15] = "W"

    # Plate 2 puzzle: push BOX(21,18) R once onto ICE(22..24,18), slides to PLATE(25,18) against W(26,18)
    g[18][21] = "BOX"
    for ix in (22, 23, 24):
        g[18][ix] = "ICE"
    g[18][25] = "PLATE"
    g[18][26] = "W"

    # Decoy 4th BOX off-path to test Sokoban planner pruning
    g[10][10] = "BOX"

    # Author solution trace from S=(2,13):
    # U*6 -> (2,7); R*10 -> (12,7);
    # R*2 -> Hero(14,7), BOX#1@(15,7)=PLATE;
    # D*11 -> (14,18); R*6 -> (20,18);
    # R*1 -> Hero(21,18), BOX#2 slides across ICE to (25,18)=PLATE => plates_active=True!
    # D*2 -> (21,20); L*1 -> (20,20) K2 picked!
    # U*15 -> (20,5) [walks straight through open P_GATE(20,6) -> K1 picked!]
    # D*8 -> (20,13); R*9 -> (29,13);
    # R*2 -> pushes BOX#3 from (30,13)->(31,13)->(32,13 PIT filled!), Hero at (31,13);
    # R*1 -> (32,13 EMPTY); JUMP_R -> lands on open P_GATE(34,13); R*1 -> (35,13) V CLEARED!
    sol = (
        ["MOVE_U"] * 6
        + ["MOVE_R"] * 12
        + ["MOVE_D"] * 11
        + ["MOVE_R"] * 7
        + ["MOVE_D"] * 2
        + ["MOVE_L"] * 1
        + ["MOVE_U"] * 15
        + ["MOVE_D"] * 8
        + ["MOVE_R"] * 12
        + ["JUMP_R"]
        + ["MOVE_R"]
    )
    return {
        "id": "OFFICIAL_FULL_01",
        "name": "官方明牌一图：黄金压板推箱库",
        "taunt": "两块压板四只箱，外加两格深渊桥，推错一步永远别想开金库！",
        "grid": g,
        "author_solution": sol,
    }


def build_official_full_2_lcm12_lasers() -> Dict[str, Any]:
    """
    OFFICIAL_FULL_02: 《红蓝12拍双频激光阵》
    Tests LASER_* (period=3) + LASER2_* (period=4) LCM(3,4)=12 corridor timing,
    plus ONEWAY directional turnstile near K2 and Vault entry.
    """
    g = _empty_framed_grid()
    g[5][20] = "K1"
    g[20][20] = "K2"
    g[13][35] = "V"

    # Build horizontal T_W corridor walls framing central rhythm lane at y=13, x in 10..17
    for x in range(10, 18):
        g[11][x] = "T_W"
        g[15][x] = "T_W"
    # Red (mod 3) cannons at x=12, 16; Blue (mod 4) cannons at x=11, 14
    g[9][11] = "LASER2_D"
    g[9][12] = "LASER_D"
    g[9][14] = "LASER2_D"
    g[9][16] = "LASER_D"
    g[11][11] = "EMPTY"
    g[11][12] = "EMPTY"
    g[11][14] = "EMPTY"
    g[11][16] = "EMPTY"

    # Overlapping corner guard near V(35,13): Red LASER_L + Blue LASER2_D shoot (34,13)
    g[8][34] = "LASER2_D"
    g[13][38] = "LASER_L"  # shoots x=37..28 along y=13 on turn % 3 == 0 (Wait: T_W at x=36? No!)
    # Protect K2 with ONEWAY_D entrance & ONEWAY_U exit channel
    g[19][19] = "T_W"
    g[19][21] = "T_W"
    g[19][20] = "ONEWAY_D"
    g[21][20] = "ONEWAY_D"  # Can enter K2 from top, cannot go up back through (19,20), must exit down -> (21,20)

    # Trace safe timing:
    # From S(2,13): R*8 -> (10,13) at end of T=8 (next turn is T=9, red fires!).
    # T=9: WAIT at (10,13) [red fires at x=12,16; (10,13) safe!]; T=10..11: R*2 -> (12,13);
    # T=12: JUMP_R across (13,13) to (14,13)? Wait T=12 BOTH fire, (14,13) is hit by LASER2_D(14,9)!
    # Better: T=10: R -> (11,13); T=11: R -> (12,13); T=12: JUMP_R -> (14,13)? Still in (14,9) beam on T=12!
    # Wait: just step carefully on non-laser turns or jump over! Let's trace exact turns:
    # T=1..8: MOVE_R*8 -> at T=8 end, Hero at (10,13) (safe from x=11..16).
    # T=9 (red fires on 12,16): MOVE_R -> (11,13) safe! (Notice LASER2@11 fires on T=8,12, NOT T=9!)
    # T=10 (safe): MOVE_R -> (12,13)
    # T=11 (safe): JUMP_R -> leaps (13,13), lands (14,13)! Hero exposed at (12,13),(14,13) - BOTH SAFE ON T=11!
    # T=12 (Red+Blue fire on 11,12,14,16): Wait! At start of T=12 Hero is ON (14,13)! JUMP_R -> (16,13) leaves (14,13) still exposed on T=12!
    # Instead at T=11: MOVE_R -> (13,13)! (safe on 11,12!)
    # T=12 (both fire on 11,12,14,16!): WAIT on (13,13)!! Neither Red nor Blue hits (13,13)! So T=12 double-beam passes harmlessly in front & behind!
    # T=13 (safe): JUMP_R -> leaps (14,13), lands (15,13) (safe!)
    # T=14 (safe): JUMP_R -> leaps (16,13), lands (17,13) (safe!)
    # Wait: at T=14 end Hero at (17,13), T=15 LASER_L@(38,13) fires along y=13 x=28..37! Hero is at x=17 (out of range 28..37)!
    # Now go get K1(20,5): from (17,13) T=15..22: U*8 -> (17,5) [end T=22], R*3 -> (20,5) [end T=25] K1 picked!
    # Go get K2(20,20): T=26..39: D*14 -> (20,19=ONEWAY_D), T=40: D -> (20,20 K2), T=41: D -> (20,21=ONEWAY_D), T=42: D -> (20,22);
    # Move toward V corridor on y=12 (above LASER_L at y=13!):
    # R*14 -> (34,22) [T=43..56]; U*10 -> (34,12)? Careful: LASER2_D@(34,8) shoots y=9..18 x=34 on T % 4 == 0!
    # Check turn numbers at (34,12):
    # From (20,22) end T=42: R*13 -> (33,22) [T=43..55]. U*10 -> (33,12) [T=56..65] (completely off x=34!).
    # Wait one tick if needed: T=65 ends at (33,12). Next turns: T=66 (Red only, (34,12) NOT hit by Red!),
    # T=66: R -> (34,12) [safe from Blue@34(mod4) and Red@(38,13)].
    # T=67 (ALL CLEAR: 67%3!=0, 67%4!=0): D -> (34,13) -> next T=68 (Blue fires on x=34): WAIT? No, move R!
    # Even better: T=67: R? From (34,12) -> T=67: D -> (34,13) [safe], T=68: R -> (35,13) V CLEARED in Step 6 BEFORE Phase D!
    # Route: S(2,13) -> R*11 -> (13,13) [T=11] -> WAIT [T=12 Red+Blue miss (13,13)]
    # -> JUMP_R -> (15,13) [T=13] -> JUMP_R -> (17,13) [T=14] -> MOVE_R -> (18,13) [T=15 clear of T_W]
    # -> MOVE_U*8 -> (18,5) [T=23] -> MOVE_R*2 -> (20,5 K1) [T=25]
    # -> MOVE_D*17 -> (20,22 via ONEWAY_D(20,19), K2(20,20), ONEWAY_D(20,21)) [T=42]
    # -> MOVE_R*13 -> (33,22) [T=55] -> MOVE_U*10 -> (33,12) [T=65]
    # -> MOVE_R -> (34,12) [T=66] -> MOVE_D -> (34,13) [T=67] -> MOVE_R -> (35,13 V) [T=68 clears before Phase D]!
    sol = (
        ["MOVE_R"] * 11        # T=1..11 -> (13,13)
        + ["WAIT"]             # T=12 -> dodge Red+Blue at (13,13)
        + ["JUMP_R", "JUMP_R"] # T=13->(15,13), T=14->(17,13)
        + ["MOVE_R"]           # T=15 -> (18,13) outside T_W corridor
        + ["MOVE_U"] * 8       # T=16..23 -> (18,5)
        + ["MOVE_R"] * 2       # T=24..25 -> (20,5) K1
        + ["MOVE_D"] * 17      # T=26..42 -> (20,22) via ONEWAY_D & K2
        + ["MOVE_R"] * 13      # T=43..55 -> (33,22)
        + ["MOVE_U"] * 10      # T=56..65 -> (33,12)
        + ["MOVE_R"]           # T=66 -> (34,12) [Red fires y=13, safe]
        + ["MOVE_D"]           # T=67 -> (34,13) [all clear]
        + ["MOVE_R"]           # T=68 -> (35,13) V! [clears before Phase D]
    )
    return {
        "id": "OFFICIAL_FULL_02",
        "name": "官方明牌二图：红蓝12拍双频激光阵",
        "taunt": "红炮3拍、蓝炮4拍、第12拍齐射满百爆头，踩错半拍直接蒸发！",
        "grid": g,
        "author_solution": sol,
    }


def build_official_full_3_grand_master() -> Dict[str, Any]:
    """
    OFFICIAL_FULL_03: 《三连宗师综合试炼殿》
    Combines ONEWAY turnstiles, PORTAL shortcut, BOX+PLATE+P_GATE, and LASER2_D.
    """
    g = _empty_framed_grid()
    g[5][20] = "K1"
    g[20][20] = "K2"
    g[13][35] = "V"

    # Portal 1 from (6,13) -> (18,5) near K1(20,5); ONEWAY_R at (19,5) forces rightward approach
    g[13][6] = "PORTAL_1A"
    g[5][18] = "PORTAL_1B"
    g[5][19] = "ONEWAY_R"
    g[4][20] = "T_W"
    g[5][21] = "T_W"
    g[6][20] = "ONEWAY_D"  # Must leave K1 downward after picking it!

    # Blue LASER2_D sweeping x=20 at y=7..17? Keep y=6..15 open, put LASER2_D at (25,10)
    g[10][25] = "LASER2_D"  # Sweeps (25,11..20) on turn % 4 == 0

    # Lock V behind P_GATE(34,13), activated by pushing BOX(28,15) L->No, R onto PLATE(30,15) through ONEWAY_R(29,15)
    for y in (12, 14):
        for x in range(34, 37):
            g[y][x] = "T_W"
    g[13][36] = "T_W"
    g[13][34] = "P_GATE"

    g[15][28] = "BOX"
    g[15][29] = "ONEWAY_R"  # Hero must push BOX R from (27,15), pushing BOX into (29,15), then R again onto PLATE(30,15)!
    g[15][30] = "PLATE"
    g[15][31] = "T_W"

    # Author trace from S=(2,13):
    # R*4 -> T=4? Careful: PORTAL_1A at (6,13) teleports on T=4 to (18,5) and steps out R*1 onto ONEWAY_R(19,5)!
    # So T=1..4 MOVE_R*4 -> Hero ends T=4 at (19,5)!
    # T=5 MOVE_R -> (20,5) K1!
    # T=6..20 MOVE_D*15 -> passes ONEWAY_D(20,6) -> (20,20) K2!
    # T=21..25 U*5 -> (20,15); T=26..32 R*7 -> (27,15) (Notice (25,15) crossed at T=30, NOT mod 4!)
    # T=33: R -> pushes BOX(28,15)->(29,15 ONEWAY_R), Hero@(28,15);
    # T=34: R -> pushes BOX(29,15)->(30,15 PLATE), Hero@(29,15) -> plates_active=True!
    # T=35..36: U*2 -> (29,13); T=37..42: R*6 -> (35,13) V CLEARED!
    sol = (
        ["MOVE_R"] * 5
        + ["MOVE_D"] * 15
        + ["MOVE_U"] * 5
        + ["MOVE_R"] * 9
        + ["MOVE_U"] * 2
        + ["MOVE_R"] * 6
    )
    return {
        "id": "OFFICIAL_FULL_03",
        "name": "官方明牌三图：三连宗师综合试炼殿",
        "taunt": "传送门落单向道、再推箱过单行桥压板——欢迎来到明牌地狱考场！",
        "grid": g,
        "author_solution": sol,
    }


def build_backup_full_1() -> Dict[str, Any]:
    """Sealed backup dungeon #1 for first DQ Demon slot."""
    g = _empty_framed_grid()
    g[5][20] = "K1"
    g[20][20] = "K2"
    g[13][35] = "V"

    # Compact vault P_GATE lock + LASER2 guard + ONEWAY wing
    g[12][35] = "T_W"
    g[14][35] = "T_W"
    g[13][36] = "T_W"
    g[13][34] = "P_GATE"
    g[16][24] = "BOX"
    g[16][26] = "PLATE"
    g[4][19] = "T_W"
    g[5][19] = "ONEWAY_R"
    g[2][25] = "LASER2_D"

    # Route: S(2,13) -> U*8 (2,5) -> R*18 (20,5 K1) -> D*15 (20,20 K2) -> U*4 (20,16) -> R*3 (23,16)
    # -> R*2 pushes BOX(24->26 PLATE), Hero@(25,16) -> U*3 (25,13)? Careful LASER2_D(25,2) only shoots y=3..12!
    # So (25,16) & (25,13) are outside range 10 (y=12)!
    # R*10 -> (35,13 V)!
    sol = (
        ["MOVE_U"] * 8
        + ["MOVE_R"] * 18
        + ["MOVE_D"] * 15
        + ["MOVE_U"] * 4
        + ["MOVE_R"] * 5
        + ["MOVE_U"] * 3
        + ["MOVE_R"] * 10
    )
    return {
        "id": "BACKUP_FULL_01",
        "name": "官方封存备用图一：单向压板守备阵",
        "taunt": "官方封存替补阵：不许抄作业，请凭真本事过单向压板锁。",
        "grid": g,
        "author_solution": sol,
    }


def build_backup_full_2() -> Dict[str, Any]:
    """Sealed backup dungeon #2 for second DQ Demon slot (distinct from #1)."""
    g = _empty_framed_grid()
    g[7][22] = "K1"
    g[19][22] = "K2"
    g[13][36] = "V"

    g[12][36] = "T_W"
    g[14][36] = "T_W"
    g[13][37] = "T_W"
    g[13][35] = "R_GATE"
    g[10][12] = "SWITCH"
    g[3][18] = "LASER_D"
    g[3][28] = "LASER2_D"
    g[7][21] = "ONEWAY_R"

    # Route: S(2,13) -> R*10 (12,13) -> U*3 (12,10 SWITCH flipped!) -> U*3 (12,7)
    # -> R*10 (22,7 K1 via ONEWAY_R(21,7)) -> D*12 (22,19 K2) -> U*6 (22,13) -> R*14 (36,13 V)
    # Check LASER_D(18,3) hits y=4..13 on mod 3; LASER2_D(28,3) hits y=4..13 on mod 4.
    # Let's check exact turns:
    # R*10: T=1..10 -> (12,13)
    # U*6: T=11..16 -> (12,7)
    # R*10: T=17..26 -> crosses (18,7) at T=22! (22 % 3 = 1, safe!) -> reaches (22,7 K1) at T=26
    # D*12: T=27..38 -> (22,19 K2)
    # U*6: T=39..44 -> (22,13)
    # R*14: T=45..58 -> crosses (28,13) at T=50! (50 % 4 = 2, safe!) -> reaches (36,13 V) at T=58!
    sol = (
        ["MOVE_R"] * 10
        + ["MOVE_U"] * 6
        + ["MOVE_R"] * 10
        + ["MOVE_D"] * 12
        + ["MOVE_U"] * 6
        + ["MOVE_R"] * 14
    )
    return {
        "id": "BACKUP_FULL_02",
        "name": "官方封存备用图二：红蓝双炮反相闸阵",
        "taunt": "官方封存替补阵二号：先翻红门再避双炮，绝不和一号图重样。",
        "grid": g,
        "author_solution": sol,
    }


def build_backup_full_3() -> Dict[str, Any]:
    """Sealed backup dungeon #3: Ice+PLATE vault + ONEWAY_D chute."""
    g = _empty_framed_grid()
    g[4][24] = "K1"
    g[21][24] = "K2"
    g[10][36] = "V"
    g[9][36] = "T_W"; g[11][36] = "T_W"; g[10][37] = "T_W"; g[10][35] = "P_GATE"
    g[13][14] = "BOX"
    g[13][15] = "ICE"; g[13][16] = "ICE"; g[13][17] = "PLATE"; g[13][18] = "T_W"
    g[20][24] = "ONEWAY_D"
    g[2][20] = "LASER2_D"
    # S(2,13) -> R*11 (13,13) -> R (pushes BOX@(14->17 PLATE), Hero@(14,13))
    # -> U*9 (14,4) -> R*10 (24,4 K1) -> D*17 (24,21 K2 via ONEWAY_D(24,20))
    # -> R*11 (35,21)? Wait V at (36,10) behind P_GATE(35,10): R*10 -> (34,21) -> U*11 -> (34,10) -> R*2 -> (36,10)
    sol = (
        ["MOVE_R"] * 12
        + ["MOVE_U"] * 9
        + ["MOVE_R"] * 10
        + ["MOVE_D"] * 17
        + ["MOVE_R"] * 10
        + ["MOVE_U"] * 11
        + ["MOVE_R"] * 2
    )
    return {
        "id": "BACKUP_FULL_03",
        "name": "官方封存备用图三：冰轨压板通道",
        "taunt": "封存替补三号：一记推箱溜冰亮全板。",
        "grid": g,
        "author_solution": sol,
    }


def build_backup_full_4() -> Dict[str, Any]:
    """Sealed backup dungeon #4: Portal shortcut + ONEWAY_R + LASER2 guard."""
    g = _empty_framed_grid()
    g[6][18] = "K1"
    g[18][26] = "K2"
    g[15][34] = "V"
    g[13][7] = "PORTAL_1A"; g[6][16] = "PORTAL_1B"; g[6][17] = "ONEWAY_R"
    g[14][34] = "T_W"; g[16][34] = "T_W"; g[15][35] = "T_W"; g[15][33] = "P_GATE"
    g[18][22] = "BOX"; g[18][24] = "PLATE"; g[17][24] = "W"
    g[22][30] = "LASER2_U"
    # S(2,13) -> R*5 (enters PORTAL_1A(7,13) -> exits PORTAL_1B(16,6) +1R onto ONEWAY_R(17,6))
    # -> R*1 (18,6 K1) -> R*2 (20,6) -> D*12 (20,18) -> R*3 (pushes BOX(22->24 PLATE), Hero@(23,18))
    # -> D*1 (23,19) -> R*3 (26,19) -> U*1 (26,18 K2) -> R*6 (32,18) -> U*3 (32,15) -> R*2 (34,15 V)
    sol = (
        ["MOVE_R"] * 6
        + ["MOVE_R"] * 2
        + ["MOVE_D"] * 12
        + ["MOVE_R"] * 3
        + ["MOVE_D"] * 1
        + ["MOVE_R"] * 3
        + ["MOVE_U"] * 1
        + ["MOVE_R"] * 6
        + ["MOVE_U"] * 3
        + ["MOVE_R"] * 2
    )
    return {
        "id": "BACKUP_FULL_04",
        "name": "官方封存备用图四：跃迁单行枢纽",
        "taunt": "封存替补四号：传送落脚即是单向关口。",
        "grid": g,
        "author_solution": sol,
    }


def build_backup_full_5() -> Dict[str, Any]:
    """Sealed backup dungeon #5: SPRING_U launch + 2-PIT BOX bridge."""
    g = _empty_framed_grid()
    g[3][19] = "K1"
    g[22][19] = "K2"
    g[14][35] = "V"
    g[9][19] = "SPRING_U"  # from (19,10) U -> hits (19,9) SPRING_U -> lands (19,6)
    g[14][32] = "PIT"; g[14][33] = "PIT"; g[13][33] = "T_W"; g[15][33] = "T_W"
    g[14][30] = "BOX"
    g[2][25] = "LASER_D"; g[14][28] = "ONEWAY_R"
    # Note T=1..8 R*17 reaches (19,13) [avoiding x=25]. Let's trace exact turns avoiding LASER_D@(25,2) (sweeps y=3..12 on %3):
    # S(2,13) -> R*17 (19,13) -> U*4 (hits (19,9) SPRING_U -> lands (19,6)) -> U*3 (19,3 K1)
    # -> D*7 (19,10)? Wait (19,9) is SPRING_U! Moving D from (19,8) hits (19,9 SPRING_U) -> springs back UP!
    # So go R*1 to (20,3), D*19 to (20,22), L*1 to (19,22 K2)!
    # Then U*8 to (19,14) -> R*12 (passes ONEWAY_R(28,14), pushes BOX(30,14)->(31,14)->(32,14 PIT), Hero@(31,14)) -> Wait check exact count!
    # From (19,14): BOX at (30,14). R*10 -> Hero@(29,14). R*1 -> BOX@(31,14) Hero@(30,14). R*1 -> BOX fills (32,14) Hero@(31,14). Total R*12.
    # Then R*1 -> Hero@(32,14) -> JUMP_R -> lands (34,14) -> R*1 -> (35,14 V)!
    sol = (
        ["MOVE_R"] * 17
        + ["MOVE_U"] * 7
        + ["MOVE_R"] * 1
        + ["MOVE_D"] * 19
        + ["MOVE_L"] * 1
        + ["MOVE_U"] * 8
        + ["MOVE_R"] * 13
        + ["JUMP_R"]
        + ["MOVE_R"]
    )
    return {
        "id": "BACKUP_FULL_05",
        "name": "官方封存备用图五：弹射填坑桥梁",
        "taunt": "封存替补五号：弹簧抢道再填双坑。",
        "grid": g,
        "author_solution": sol,
    }


def build_backup_full_6() -> Dict[str, Any]:
    """Sealed backup dungeon #6: Switch + R_GATE + LASER2 + ONEWAY."""
    g = _empty_framed_grid()
    g[5][15] = "K1"
    g[19][15] = "K2"
    g[12][34] = "V"
    g[11][34] = "T_W"; g[13][34] = "T_W"; g[12][35] = "T_W"; g[12][33] = "R_GATE"
    g[13][9] = "SWITCH"
    g[18][15] = "ONEWAY_D"
    g[20][22] = "LASER2_U"
    g[4][28] = "LASER_D"
    sol = (
        ["MOVE_R"] * 13
        + ["MOVE_U"] * 8
        + ["MOVE_D"] * 14
        + ["MOVE_R"] * 1
        + ["MOVE_U"] * 7
        + ["MOVE_R"] * 18
    )
    return {
        "id": "BACKUP_FULL_06",
        "name": "官方封存备用图六：单门斜控金库",
        "taunt": "封存替补六号：单向开关与红门守望。",
        "grid": g,
        "author_solution": sol,
    }


def build_backup_full_7() -> Dict[str, Any]:
    """Sealed backup dungeon #7: Dual PLATE + 2 BOX + LASER2."""
    g = _empty_framed_grid()
    g[5][25] = "K1"
    g[20][25] = "K2"
    g[13][37] = "V"
    g[12][37] = "T_W"; g[14][37] = "T_W"; g[13][38] = "T_W"; g[13][36] = "P_GATE"
    g[8][14] = "BOX"; g[8][16] = "PLATE"; g[8][17] = "W"
    g[18][14] = "BOX"; g[18][16] = "PLATE"; g[18][17] = "W"
    g[2][30] = "LASER2_D"  # shoots y=3..12 x=30 (safe at y=13!)
    sol = (
        ["MOVE_U"] * 5
        + ["MOVE_R"] * 13
        + ["MOVE_L"] * 3
        + ["MOVE_D"] * 10
        + ["MOVE_R"] * 3
        + ["MOVE_U"] * 13
        + ["MOVE_R"] * 10
        + ["MOVE_D"] * 15
        + ["MOVE_U"] * 7
        + ["MOVE_R"] * 12
    )
    return {
        "id": "BACKUP_FULL_07",
        "name": "官方封存备用图七：双箱压板锁阵",
        "taunt": "封存替补七号：两枚压板缺一不开。",
        "grid": g,
        "author_solution": sol,
    }


def build_backup_full_8() -> Dict[str, Any]:
    """Sealed backup dungeon #8: MIRROR_NE + ONEWAY_U + CRACK lane."""
    g = _empty_framed_grid()
    g[3][28] = "K1"
    g[22][28] = "K2"
    g[11][35] = "V"
    g[13][14] = "MIRROR_NE"  # Moving R onto (14,13) deflects U to (14,12)!
    g[12][14] = "ONEWAY_U"
    g[11][14] = "CRACK"
    g[16][22] = "HEAL"
    g[16][30] = "MIMIC"
    # S(2,13) -> R*12 (steps on MIRROR_NE(14,13) -> deflects U onto ONEWAY_U(14,12))
    # -> U*9 (14,3 via CRACK(14,11)) -> R*14 (28,3 K1) -> D*19 (28,22 K2) -> U*11 (28,11) -> R*7 (35,11 V)
    sol = (
        ["MOVE_R"] * 12
        + ["MOVE_U"] * 9
        + ["MOVE_R"] * 14
        + ["MOVE_D"] * 19
        + ["MOVE_U"] * 11
        + ["MOVE_R"] * 7
    )
    return {
        "id": "BACKUP_FULL_08",
        "name": "官方封存备用图八：折跃单行试炼",
        "taunt": "封存替补八号：斜坡折射直入单向道。",
        "grid": g,
        "author_solution": sol,
    }


def build_backup_full_9() -> Dict[str, Any]:
    """Sealed backup dungeon #9: Dual-frequency guard + Portal pair 2."""
    g = _empty_framed_grid()
    g[6][30] = "K1"
    g[19][30] = "K2"
    g[9][33] = "V"
    g[13][8] = "PORTAL_2A"
    g[6][26] = "PORTAL_2B"
    g[2][20] = "LASER2_D"
    g[23][24] = "LASER_U"
    g[5][30] = "W"; g[6][31] = "ONEWAY_R"
    sol = (
        ["MOVE_R"] * 9
        + ["MOVE_D"] * 13
        + ["MOVE_U"] * 10
        + ["MOVE_R"] * 3
    )
    return {
        "id": "BACKUP_FULL_09",
        "name": "官方封存备用图九：双子远传快线",
        "taunt": "封存替补九号：直传后区迎战红蓝双炮。",
        "grid": g,
        "author_solution": sol,
    }


def build_backup_full_10() -> Dict[str, Any]:
    """Sealed backup dungeon #10: TNT chain + PLATE + ONEWAY_L exit."""
    g = _empty_framed_grid()
    g[5][16] = "K1"
    g[18][16] = "K2"
    g[6][36] = "V"
    g[5][36] = "T_W"; g[7][36] = "T_W"; g[6][37] = "T_W"; g[6][35] = "P_GATE"
    g[13][10] = "BOX"; g[13][12] = "PLATE"; g[13][13] = "W"
    g[17][17] = "ONEWAY_L"
    g[10][26] = "TNT"
    g[1][22] = "LASER2_D"
    sol = (
        ["MOVE_R"] * 9
        + ["MOVE_U"] * 8
        + ["MOVE_R"] * 5
        + ["MOVE_D"] * 13
        + ["MOVE_U"] * 12
        + ["MOVE_R"] * 20
    )
    return {
        "id": "BACKUP_FULL_10",
        "name": "官方封存备用图十：上区金库压板战",
        "taunt": "封存替补十号：上区高位金库加单向拦截。",
        "grid": g,
        "author_solution": sol,
    }


def build_backup_full_11() -> Dict[str, Any]:
    """Sealed backup dungeon #11: Lower-wing Vault + 4-corner ONEWAY ring + LASER2."""
    g = _empty_framed_grid()
    g[8][12] = "K1"
    g[22][32] = "K2"
    g[20][37] = "V"
    g[19][37] = "T_W"; g[21][37] = "T_W"; g[20][38] = "T_W"; g[20][36] = "P_GATE"
    g[13][6] = "BOX"; g[13][8] = "PLATE"; g[13][9] = "T_W"
    g[22][31] = "ONEWAY_R"; g[21][32] = "ONEWAY_U"
    g[15][20] = "LASER2_R"; g[10][12] = "ONEWAY_U"
    # S(2,13) -> R*5 (Hero@(7,13), BOX@(8,13 PLATE) -> plates_active=True!)
    # -> U*5 (7,8) -> R*5 (12,8 K1) -> R*18 (30,8) -> D*14 (30,22)
    # -> R*2 (passes ONEWAY_R(31,22) -> (32,22 K2)) -> U*2 (passes ONEWAY_U(32,21) -> (32,20)) -> R*5 (37,20 V)
    sol = (
        ["MOVE_R"] * 5
        + ["MOVE_U"] * 5
        + ["MOVE_R"] * 23
        + ["MOVE_D"] * 14
        + ["MOVE_R"] * 2
        + ["MOVE_U"] * 2
        + ["MOVE_R"] * 5
    )
    return {
        "id": "BACKUP_FULL_11",
        "name": "官方封存备用图十一：下翼双折压板宫",
        "taunt": "封存替补十一号：全程绝不重样的下翼迷宫。",
        "grid": g,
        "author_solution": sol,
    }


def get_all_official_maps() -> List[Dict[str, Any]]:
    raw_maps = [
        build_official_full_1_sokoban_plates(),
        build_official_full_2_lcm12_lasers(),
        build_official_full_3_grand_master(),
    ]
    return _verify_map_list(raw_maps)


def get_all_backup_maps() -> List[Dict[str, Any]]:
    raw_maps = [
        build_backup_full_1(),
        build_backup_full_2(),
        build_backup_full_3(),
        build_backup_full_4(),
        build_backup_full_5(),
        build_backup_full_6(),
        build_backup_full_7(),
        build_backup_full_8(),
        build_backup_full_9(),
        build_backup_full_10(),
        build_backup_full_11(),
    ]
    return _verify_map_list(raw_maps)


def _verify_map_list(raw_maps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    verified: List[Dict[str, Any]] = []
    seen_ids = set()
    seen_hashes = set()
    for m in raw_maps:
        if m["id"] in seen_ids:
            raise RuntimeError(f"Duplicate map ID '{m['id']}'")
        seen_ids.add(m["id"])
        grid_hash = hashlib.sha256(json.dumps(m["grid"]).encode("utf-8")).hexdigest()
        if grid_hash in seen_hashes:
            raise RuntimeError(f"Duplicate grid layout detected in '{m['id']}'")
        seen_hashes.add(grid_hash)

        ver = engine.verify_author_solution(m["grid"], m["author_solution"])
        if not ver["valid"]:
            raise RuntimeError(f"Official/Backup v2.2 map '{m['id']}' invalid: {ver['reason']}")
        verified.append({
            **m,
            "grid_sha256": grid_hash,
            "spent_gold": ver["spent_gold"],
            "vault_gold": ver["vault_gold"],
            "author_steps": ver["author_steps"],
            "author_hp_left": ver["author_hp_left"],
        })
    return verified


if __name__ == "__main__":
    print("=== Verifying Half-2 v2.2 Official (3) & Backup (11) Maps ===")
    for item in get_all_official_maps() + get_all_backup_maps():
        print(
            f"[OK] {item['id']:<18} | sha={item['grid_sha256'][:8]} | Spent={item['spent_gold']:4d}G "
            f"| Vault={item['vault_gold']:4d}G | Steps={item['author_steps']:3d} | HP={item['author_hp_left']:3d}"
        )
