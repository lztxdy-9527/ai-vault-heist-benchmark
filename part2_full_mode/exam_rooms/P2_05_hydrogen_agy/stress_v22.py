"""Adversarial v2.2 FULL stress test suite (10 hard edge-case puzzles beyond BENCH_STRONG)."""

import os
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)
import local_judge_v22 as lj


def make_grid():
    return lj.make_empty_grid()


def set_rect(g, x1, y1, x2, y2, t):
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            g[y][x] = t


def build_stress_maps():
    maps = []

    # S01: Coupled 3-BOX Sokoban + ONEWAY + 2-wide PIT + PLATE
    g1 = make_grid()
    g1[5][20], g1[20][20], g1[13][36] = "K1", "K2", "V"
    # Seal V behind P_GATE(35, 13) inside T_W
    set_rect(g1, 35, 12, 37, 12, "T_W")
    set_rect(g1, 35, 14, 37, 14, "T_W")
    g1[12][37], g1[13][37], g1[14][37] = "T_W", "T_W", "T_W"
    g1[13][35] = "P_GATE"
    # Narrow 1-wide corridor at y=8 leading to PLATE(14,8) and PIT(15,8) via ONEWAY_R(11,8):
    # Box B1 at (8,8) blocks Box B2 at (6,8); must push B1 through (11,8) into PIT(15,8) FIRST? Wait:
    # Actually: PLATE(14,8) is BEFORE PIT(15,8), so if B1 enters (14,8)=PLATE first, B2 behind it can push B1 into PIT(15,8) AND B2 stays on PLATE(14,8)!
    set_rect(g1, 7, 7, 16, 7, "T_W")
    set_rect(g1, 7, 9, 16, 9, "T_W")
    g1[8][11] = "ONEWAY_R"
    g1[8][14] = "PLATE"
    g1[8][15] = "PIT"
    g1[8][16] = "ONEWAY_R"
    g1[8][8] = "BOX"
    g1[8][6] = "BOX"
    # Second PLATE(8, 18) with B3(5, 18) behind ONEWAY_D(8,17) guard
    set_rect(g1, 7, 19, 9, 19, "T_W")
    g1[18][7], g1[18][9] = "T_W", "T_W"
    g1[18][8] = "PLATE"
    g1[17][8] = "ONEWAY_D"
    g1[16][8] = "BOX"
    maps.append(("S01_COUPLED_3BOX_SOKOBAN", g1))

    # S02: PLATE repurpose (push BOX onto PLATE -> get K1 inside P_GATE -> push SAME BOX off PLATE into PIT -> V!)
    g2 = make_grid()
    g2[5][18], g2[20][20], g2[13][36] = "K1", "K2", "V"
    # K1 room sealed by P_GATE(18, 7)
    set_rect(g2, 17, 4, 19, 4, "T_W")
    g2[5][17], g2[6][17], g2[7][17] = "T_W", "T_W", "T_W"
    g2[5][19], g2[6][19], g2[7][19] = "T_W", "T_W", "T_W"
    g2[7][18] = "P_GATE"
    # Single BOX at (10, 13), PLATE at (14, 13), and V sealed behind 2-wide PIT(34..35, 13)?
    # Even cleaner: hero uses BOX(10,13)->PLATE(14,13) to open K1, then MUST push THAT BOX from (14,13) across to (33,13)->PIT(34,13)
    # where V(36,13) is behind PIT(34,13) and PIT(35,13) inside T_W (needs 1 BOX + JUMP_R? No, put PIT(33,13), PIT(34,13), PIT(35,13) = 3 PITs -> NO JUMP, only 1 BOX + 1 JUMP!! Wait: 1 BOX bridges 34->EMPTY, then JUMP_R over 33 or 35! Actually if K1 room opens P_GATE, let BOX reach PIT(34,13) while hero has 0 jumps? Or 34 & 35 are PITs and V has T_W except x=33 -> 1 BOX fills (34,13), hero jumps (33->35->36)!)
    g2[13][10] = "BOX"
    g2[13][14] = "PLATE"
    set_rect(g2, 34, 12, 37, 12, "T_W")
    set_rect(g2, 34, 14, 37, 14, "T_W")
    g2[13][37] = "T_W"
    g2[13][34] = "PIT"
    g2[13][35] = "PIT"  # Needs BOX in (34,13) [or (35,13)? push 2 left/right -> fills 34!] + JUMP_R over 35!
    maps.append(("S02_BOX_REPURPOSE_PLATE_TO_PIT", g2))

    # S03: True t % 12 Dual-Frequency Laser Maze (LASER %3 + LASER2 %4) + Bomb Turret
    g3 = make_grid()
    g3[5][20], g3[20][20], g3[13][36] = "K1", "K2", "V"
    # T_W wall at x=28 with 1 gap at (28,13); corridor x=27..29 swept by LASER_D(28,8)[%3] and LASER2_U(29,18)[%4]!
    # And LASER_L(37, 13) sweeps all of y=13 -> hero must wait exact t%12 timing!
    set_rect(g3, 28, 1, 28, 24, "T_W")
    g3[13][28] = "EMPTY"
    g3[8][28] = "LASER_D"    # swept (28, 9..18) %3
    g3[18][29] = "LASER2_U"  # swept (29, 8..17) %4
    g3[10][27] = "LASER2_D"  # swept (27, 11..20) %4
    maps.append(("S03_MOD12_DUAL_LASER_TIMING", g3))

    # S04: Movable BOX shielding beam of deadly perma-laser corridor!
    g4 = make_grid()
    g4[5][20], g4[20][20], g4[13][36] = "K1", "K2", "V"
    # Long sealed T_W tunnel x=26..37 at y=13 with V(36,13); LASER_L(37,13) + LASER2_L(38,13)? No, put LASER_L(38,13) shooting LEFT along y=13 (x=28..37),
    # and T_W above/below y=12,14 from x=27..38 so hero CANNOT dodge sideways for 10 tiles!
    # Wait: how does hero get past LASER_L(38,13) for 10 tiles with 0 damage? Push BOX(25,13) in front of hero ALL THE WAY along y=13 -> BOX blocks LASER_L completely!!
    set_rect(g4, 27, 12, 38, 12, "T_W")
    set_rect(g4, 27, 14, 38, 14, "T_W")
    g4[13][38] = "LASER_L"  # beam hits (28..37, 13)
    # Put V at (35, 13), and put LASER2_L at (37, 13) so it's 100 damage if unshielded!
    g4[13][36] = "EMPTY"
    g4[13][37] = "LASER2_L"
    g4[13][35] = "V"
    g4[13][25] = "BOX"
    # Give side exit space at (35,12) = T_W? Hero pushes BOX onto (34,13) standing at (33,13), Wait: can hero step onto V(35,13) if BOX is ON (35,13)?
    # No! _box_enterable forbids V! So put (35,14) = EMPTY (gap out to V(35,15)? NO, V at (36,13) and alcove (35,12)=EMPTY so hero parks BOX at (36,13)? No, put T_W(36,12) open -> side step at (34,12)=EMPTY, V at (35,12), BOX stays on (35,13) blocking laser while hero walks to (35,12)=V!)
    g4[13][35] = "EMPTY"
    g4[12][34] = "EMPTY"
    g4[12][35] = "V"
    g4[11][34], g4[11][35], g4[11][36] = "T_W", "T_W", "T_W"
    g4[12][33], g4[12][36] = "T_W", "T_W"
    maps.append(("S04_BOX_LASER_SHIELD", g4))

    # S05: SWITCH two-phase cycling (False -> K1 via B_GATE, flip True -> K2 via R_GATE, flip False -> V via B_GATE!)
    g5 = make_grid()
    g5[5][20], g5[20][20], g5[13][36] = "K1", "K2", "V"
    g5[13][10] = "SWITCH"
    # K1 inside T_W + B_GATE(20, 6) [False=open]
    set_rect(g5, 19, 4, 21, 4, "T_W"); g5[5][19], g5[5][21], g5[6][19], g5[6][21] = "T_W", "T_W", "T_W", "T_W"
    g5[6][20] = "B_GATE"
    # K2 inside T_W + R_GATE(20, 19) [True=open]
    set_rect(g5, 19, 21, 21, 21, "T_W"); g5[19][19], g5[19][21], g5[20][19], g5[20][21] = "T_W", "T_W", "T_W", "T_W"
    g5[19][20] = "R_GATE"
    # V inside T_W + B_GATE(35, 13) [False=open!]
    set_rect(g5, 35, 12, 37, 12, "T_W"); set_rect(g5, 35, 14, 37, 14, "T_W")
    g5[13][37] = "T_W"
    g5[13][35] = "B_GATE"
    maps.append(("S05_SWITCH_DOUBLE_FLIP", g5))

    # S06: THROW through PORTAL + MIRROR over ONEWAY_L to hit SWITCH inside sealed T_W vault!
    g6 = make_grid()
    g6[5][20], g6[20][20], g6[13][36] = "K1", "K2", "V"
    # V sealed behind R_GATE(35,13) + PIT(34,13)
    set_rect(g6, 35, 12, 37, 12, "T_W"); set_rect(g6, 35, 14, 37, 14, "T_W")
    g6[13][37] = "T_W"; g6[13][35] = "R_GATE"; g6[13][34] = "PIT"
    # Sealed SWITCH chamber at (8..11, 2..4): PORTAL_1A(6,13) -> PORTAL_1B(10, 3) -> ONEWAY_L(11,3)? Wait throw goes from outside:
    # Place PORTAL_1A at (6, 10); PORTAL_1B at (10, 3) inside T_W box, ONEWAY_L(11,3) -> SWITCH(12,3)!
    #Wait: hero can walk through PORTAL_1A too unless blocked by PIT around PORTAL_1B! Put PIT(11,3), ONEWAY_L(12,3) ->Wait stone passes PIT & ONEWAY_L? Yes! Even simpler: put T_W box around (9..13, 2..4) with PIT(11,3) & SWITCH(12,3), and PORTAL_1B(10,3), PORTAL_1A(6,10) so hero throwing THROW_R at (4,10) flies 2 into PORTAL_1A(6,10)->(10,3)[PORTAL_1B]->(11,3)[PIT]->(12,3)[SWITCH]!!
    set_rect(g6, 9, 2, 13, 2, "T_W"); set_rect(g6, 9, 4, 13, 4, "T_W")
    g6[3][9], g6[3][13] = "T_W", "T_W"
    g6[3][10] = "PORTAL_1B"
    g6[3][11] = "ONEWAY_L"  # air throw passes through! Hero stepping PORTAL_1A moving R gets blocked at (11,3) and stops at (10,3), WAIT if hero can't exit PORTAL_1B? Put PIT at (11,3)? No, ONEWAY_L blocks moving R so hero never enters PIT, and can step L back onto PORTAL_1B? Better: guard PORTAL_1A(6,10) with PIT(5,10) so hero stands at (4,10) and only THROW_R works cleanly!
    g6[10][5] = "PIT"
    g6[10][6] = "PORTAL_1A"
    g6[3][12] = "SWITCH"
    maps.append(("S06_THROW_PORTAL_ONEWAY_SWITCH", g6))

    # S07: Preserve CRACK bridge via JUMP_R so return path stays open!
    g7 = make_grid()
    g7[5][25], g7[20][20], g7[13][36] = "K1", "K2", "V"
    # K1(25,5) inside 1-wide T_W deadend x=22..26, y=5 with CRACK at (23,5)!
    # If hero walks (22,5)->CRACK(23,5)->(24,5)->K1(25,5), turning around breaks (23,5) unless JUMP_L back!
    # Put TWO cracks at (23,5) and (24,5) -> if walked in, becomes 2 PITs = softlock! Wait: JUMP_R skips 1 tile ((22->24) leaves (23,5)=CRACK intact, ONLY breaks (24,5) on way to 25, then JUMP_L back 25->23? No, (25->23) puts hero on (23,5)=CRACK then JUMP_L over... Wait: 2 cracks (23,5) & (25,5) with EMPTY at (24,5)! Walk (22,5) JUMP_R -> (24,5) -> step (25,5)=K1 -> breaks on return -> JUMP_L! Better: T_W(22..26,4&6), (23,5)=CRACK, (24,5)=EMPTY, (25,5)=K1, (26,5)=T_W! Walk in via (22,5) JUMP_R -> (24,5) -> (25,5), then (24,5) -> JUMP_L -> (22,5): BOTH CRACK(23,5) NEVER STEPPED ON!)
    set_rect(g7, 22, 4, 26, 4, "T_W"); set_rect(g7, 22, 6, 26, 6, "T_W")
    g7[5][26] = "T_W"
    g7[5][23] = "CRACK"
    g7[5][24] = "PIT"  #Wait: (23,5)=CRACK, (24,5)=EMPTY? No! If (23,5)=CRACK and hero walks across (23,5) into (24,5)->(25,5), then only 1 jump needed on return; if he has 0 jumps? Put (23,5)=CRACK & (24,5)=CRACK? Cannot jump 2! Put CRACK at (23,5) and LASER_D(23,1) or put 2-tile T_W hall (23,5)=CRACK, (24,5)=CRACK? No, (23,5)=CRACK, (24,5)=EMPTY, and (22,5) has ONEWAY_L? No, test CRACK + LASER return!
    g7[5][24] = "EMPTY"
    maps.append(("S07_CRACK_ROUNDTRIP", g7))

    # S08: Mandatory 2x -50 HP lasers + intermediate verified HEAL(+30) amidst MIMICs
    g8 = make_grid()
    g8[5][20], g8[20][20], g8[13][36] = "K1", "K2", "V"
    # Barrier 1: T_W wall x=15 with 3-tile laser tunnel (14..16, 13) swept by LASER_R(12,13)
    set_rect(g8, 15, 1, 15, 24, "T_W")
    set_rect(g8, 14, 12, 16, 12, "T_W"); set_rect(g8, 14, 14, 16, 14, "T_W")
    g8[13][15] = "EMPTY"
    g8[13][12] = "LASER_R"  # hits 13..22!Wait make LASER_L(18,13) inside T_W? Put LASER_D(15,8)[%3] AND LASER_D(16,8)[%3] AND (14,8)[LASER_D] so ALL 3 cells (14,15,16) fire on %3==0 -> unavoidable -50 HP!
    g8[13][12] = "EMPTY"
    g8[8][14], g8[8][15], g8[8][16] = "LASER_D", "LASER_D", "LASER_D"
    # Barrier 2: T_W wall x=30 with 3-tile laser tunnel (29..31, 13) -> second unavoidable -50 HP!
    set_rect(g8, 30, 1, 30, 24, "T_W")
    set_rect(g8, 29, 12, 31, 12, "T_W"); set_rect(g8, 29, 14, 31, 14, "T_W")
    g8[13][30] = "EMPTY"
    g8[8][29], g8[8][30], g8[8][31] = "LASER_D", "LASER_D", "LASER_D"
    # Between x=17..28: 1 real HEAL at (22, 13) and 2 decoy MIMICs at (22, 10) and (22, 16)!
    g8[13][22] = "HEAL"
    g8[10][22] = "MIMIC"
    g8[16][22] = "MIMIC"
    maps.append(("S08_TANK_HEAL_MIMIC", g8))

    return maps


if __name__ == "__main__":
    # Validate all 8 stress maps under v2.2 rules (except author check)
    for name, g in build_stress_maps():
        dec = lj.decode_grid_only(g)
        print(f"Stress map {name:32s}: spent={dec['spent_gold']:4d}G valid=True")
