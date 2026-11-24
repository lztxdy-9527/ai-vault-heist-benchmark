"""
Synthetic Nightmare v2.2 Stress-Test Suite — HARDER than BENCH_STRONG!
Tests:
1. NIGHTMARE_ICE_STOPPER: Box B must be parked as a stopper on ICE so Box A stops on PLATE_1 instead of sliding into PIT, then Box B goes to PLATE_2!
2. NIGHTMARE_4PLATE_5BOX: 4 PLATEs, 5 BOXes (4 for plates, 1 for 2-wide PIT bridge), 12-beat crossfire, ONEWAYs, SWITCH, TNT!
3. NIGHTMARE_BOX_SHIELD: Corridor with 3-beat + 4-beat lasers where pushing a BOX into the beam is the ONLY 0-damage way through!
4. NIGHTMARE_DOUBLE_SWITCH_BANKSHOT: Bomb W -> Mirror+Portal bank-shot THROW -> TNT -> K1 -> flip SWITCH ON for R_GATE -> flip SWITCH OFF for B_GATE -> V!
5. NIGHTMARE_MANDATORY_MIMIC_HEAL: Unavoidable Spring->Mimic (-45 HP), 1 real HEAL among 3 MIMICs (+30 HP), plus tight 12-beat crossfire!
"""

import time
from sim_v22 import EngineV22
from solver_v22 import FastWorld


def empty_grid():
    return [
        ["T_W" if (x == 0 or x == 39 or y == 0 or y == 25) else "EMPTY" for x in range(40)]
        for y in range(26)
    ]


def build_nightmare_ice_stopper():
    """
    Box A at (6, 8) must slide right across ICE(7..11, 8) and stop on PLATE(10, 8),
    otherwise it slides into PIT(12, 8)!
    To stop Box A on PLATE(10, 8), Box B at (11, 12) must FIRST be pushed up to (11, 8) (acting as stopper!),
    then Box A is pushed right -> stops on PLATE(10, 8),
    then Box B is pushed up from (11, 8) to PLATE(11, 5)!
    """
    g = empty_grid()
    g[4][20] = "K1"
    g[20][20] = "K2"
    g[13][36] = "V"
    # Seal V behind P_GATE
    for px, py in ((35, 12), (36, 12), (37, 12), (37, 13), (35, 14), (36, 14), (37, 14)):
        g[py][px] = "T_W"
    g[13][35] = "P_GATE"
    # Ice stopper puzzle!
    g[8][6] = "BOX"      # Box A
    g[8][7] = "ICE"
    g[8][8] = "ICE"
    g[8][9] = "ICE"
    g[8][10] = "PLATE"   # Wait: if (10,8) is PLATE (not ICE), Box A stops on PLATE automatically!
    # So make (10,8) PLATE ONLY reachable by sliding on ICE(7..9) AND wait: PLATE stops slide!
    # For true stopper: put ICE on (7..9, 8), MIRROR_NE? No, put PLATE at (10, 8) is non-ice so it stops!
    # Wait: how do you make Box A overshoot a PLATE?
    # Put SPRING_R at (8, 8) launching k=1(9,8), k=2(10,8 PLATE), k=3(11,8 PIT)!!
    # YES!! SPRING_R(8,8) launches 3 tiles to (11,8 PIT) UNLESS Box B stands at (11,8) -> blocked_k=3 -> lands on k=2 (10,8 PLATE)!!
    g[8][7] = "EMPTY"
    g[8][8] = "SPRING_R"
    g[8][9] = "PIT"      # jumped over by spring!
    g[8][10] = "PLATE"   # k=2!
    g[8][11] = "EMPTY"   # k=3! (if Box B is at (11,8), Box A stops at k=2 = PLATE(10,8)!! Wait: if (11,8) is EMPTY and (12,8) is PIT, without Box B Box A lands on (11,8) and stops, still not on PLATE; if (11,8) is ICE -> PIT(12,8), without Box B Box A lands on ICE(11,8) and dies in PIT(12,8)!!)
    g[8][11] = "ICE"
    g[8][12] = "PIT"
    # Surround row 8 with T_W above/below at x=9,10 so Box A CANNOT be walked directly onto PLATE(10,8)!
    for x in (8, 9, 10):
        g[7][x] = "T_W"
        g[9][x] = "T_W"
    # Box B starts at (11, 12), can be pushed up to (11, 8) [Wait: (11,8) is ICE! If pushed UP onto (11,8) ICE, it slides UP to (11,7)! So put T_W at (11,7) so Box B stops ON (11,8), then after Box A lands on PLATE(10,8), push Box B DOWN to PLATE(11,14)? No, if T_W is at (11,7), hero can't get above (11,8) to push down!
    # Put (11, 7) = EMPTY, (11, 8) = EMPTY, (12, 8) = PIT, wait: if (11,8) is EMPTY and hero puts Box B at (11,8), Box A from SPRING_R(8,8) is blocked at k=3 (11,8) and lands on k=2 PLATE(10,8)!! Then hero walks to (11,7) and pushes Box B DOWN to (11,10) -> PLATE(11,10)!!
    # AND without Box B at (11,8), Box A lands on (11,8) which is NOT on PLATE, and since (10,7)/(10,9) are T_W and (11,8) is right of (10,8) wait hero could push Box A left onto (10,8) unless (11,8) is ONEWAY_R or PIT!
    # YES!! Make (10,8) PLATE, (9,8) PIT, (11,8) ONEWAY_U? No, if (11,8) is ONEWAY_R, Box B can enter (11,8) from (10,8)? No!
    # Make (11,8) EMPTY, (12,8) T_W! Then if Box A lands on (11,8), hero CANNOT get to (12,8) to push Box A left -> DEADLOCKED!
    # Whereas if Box B is pushed UP from (11,10) to (11,8): hero pushes Box A onto SPRING_R(8,8) -> blocked by Box B at (11,8) -> lands on PLATE(10,8)! Then hero walks to (11,7) and pushes Box B DOWN to PLATE(11,11)!!
    g[8][11] = "EMPTY"
    g[8][12] = "T_W"
    g[10][11] = "BOX"    # Box B
    g[12][11] = "PLATE"  # Plate 2!
    return g


def build_nightmare_4plate_5box():
    """4 plates, 5 boxes (4 for plates + 1 to fill 2-wide PIT bridge), 12-beat crossfire, switch, TNT."""
    g = empty_grid()
    g[4][24] = "K1"
    g[22][24] = "K2"
    g[13][36] = "V"
    # Vertical titanium divider at x=14 with P_GATE at (14,13)
    for y in range(1, 25):
        g[y][14] = "T_W"
    g[13][14] = "P_GATE"
    # 4 plates in left half (x=1..13) with 4 boxes (2 normal, 1 via ICE+MIRROR, 1 via SPRING over PIT)
    g[4][10] = "PLATE"; g[4][6] = "BOX"
    g[8][10] = "PLATE"; g[8][6] = "BOX"
    g[18][10] = "PLATE"; g[17][5] = "BOX"; g[17][6] = "ICE"; g[17][7] = "ICE"; g[17][8] = "ICE"; g[17][9] = "ICE"; g[17][10] = "MIRROR_SE"
    g[22][10] = "PLATE"; g[22][5] = "BOX"; g[22][6] = "SPRING_R"; g[22][7] = "PIT"
    # Right half divider at x=28 with 2-wide PIT bridge + ONEWAY_R
    for y in range(1, 25):
        g[y][28] = "T_W"
    g[13][26] = "BOX"  # 5th box!
    g[13][28] = "PIT"
    g[13][29] = "PIT"
    g[13][30] = "ONEWAY_R"
    # K1 sealed by R_GATE + T_W
    for px, py in ((23, 3), (24, 3), (25, 3), (23, 4), (25, 4)):
        g[py][px] = "T_W"
    g[5][24] = "R_GATE"
    g[13][18] = "SWITCH"
    # K2 sealed by W + TNT
    g[21][24] = "W"; g[23][24] = "W"; g[22][25] = "W"; g[22][23] = "TNT"
    # V guarded by P_GATE + 12-beat crossfire
    for px, py in ((35, 12), (36, 12), (37, 12), (37, 13), (35, 14), (36, 14), (37, 14)):
        g[py][px] = "T_W"
    g[13][35] = "P_GATE"
    g[7][34] = "LASER_D"
    g[19][34] = "LASER2_U"
    g[13][38] = "LASER_L"
    return g


def build_nightmare_box_shield():
    """
    Corridor at y=13 (x=17..21) has deadly 12-beat crossfire from LASER_D(18,8) [mod 3],
    LASER2_U(18,18) [mod 4], and LASER_L(23,13) [mod 3].
    Pushing BOX(14,10) to (18,10) shields LASER_D(18,8) for a clean 100 HP crossing!
    """
    g = empty_grid()
    g[5][28] = "K1"
    g[20][28] = "K2"
    g[13][35] = "V"
    for y in range(1, 25):
        if y != 13:
            g[y][21] = "T_W"
    # Corridor walls with PIT gaps so vertical lasers shine onto y=13
    for x in range(17, 21):
        g[12][x] = "PIT"
        g[14][x] = "PIT"
    g[8][18] = "LASER_D"
    g[18][18] = "LASER2_U"
    g[8][19] = "LASER2_D"
    g[18][19] = "LASER_U"
    g[8][20] = "LASER_D"
    g[18][20] = "LASER2_U"
    # Box on upper ledge to block LASER_D(18,8) or LASER2_D(19,8)
    g[10][14] = "BOX"
    return g


def build_nightmare_double_switch_bankshot():
    """
    Requires:
    1) Bomb W(8,10) to open throw line
    2) Stand at (8,12) and THROW_U -> MIRROR_NW(8,6) -> PORTAL_1A(6,6) -> PORTAL_1B(22,6) -> TNT(20,6) blows up W(19,6) around K1(19,5)!
    3) Step on SWITCH(10,13) -> opens R_GATE(24,20) for K2(25,20)!
    4) Step on SWITCH(10,13) AGAIN -> re-opens B_GATE(34,13) for V(35,13)!
    """
    g = empty_grid()
    g[5][19] = "K1"
    g[20][25] = "K2"
    g[13][35] = "V"
    # K1 sealed by T_W except W(19,6) next to TNT(20,6)
    for px, py in ((18, 4), (19, 4), (20, 4), (18, 5), (20, 5), (18, 6), (21, 5), (21, 6), (22, 5), (22, 7), (23, 6)):
        g[py][px] = "T_W"
    g[6][19] = "W"
    g[6][20] = "TNT"
    g[6][22] = "PORTAL_1B"
    # Throw setup: (8,10) has W blocking line from (8,11) to MIRROR_NW(8,6) -> PORTAL_1A(6,6)
    # Wait: (8,10) is W, hero bombs (8,10) then stands at (8,11) -> THROW_U dist 5 to (8,6) MIRROR_NW -> turns L, dist 6 to (7,6) ICE -> slides L to PORTAL_1A(6,6) -> teleports to PORTAL_1B(22,6) -> slides L to (21,6)? Wait (21,6) was T_W! Make (21,6) ICE!
    g[6][21] = "ICE"
    g[6][8] = "MIRROR_NW"
    g[6][7] = "ICE"
    g[6][6] = "PORTAL_1A"
    g[5][6] = "T_W"; g[7][6] = "T_W"; g[6][5] = "T_W"; g[5][7] = "T_W"; g[7][7] = "T_W"
    g[10][8] = "W"; g[10][7] = "T_W"; g[10][9] = "T_W"
    # K2 behind R_GATE
    for px, py in ((24, 19), (25, 19), (26, 19), (26, 20), (24, 21), (25, 21), (26, 21)):
        g[py][px] = "T_W"
    g[20][24] = "R_GATE"
    g[13][10] = "SWITCH"
    # V behind B_GATE (open when gf=False, closed when gf=True!)
    for px, py in ((34, 12), (35, 12), (36, 12), (36, 13), (34, 14), (35, 14), (36, 14)):
        g[py][px] = "T_W"
    g[13][34] = "B_GATE"
    return g


def build_nightmare_mandatory_mimic_heal():
    """
    Unavoidable Spring->Mimic (-45 HP) to enter right half!
    4 chests (3 MIMIC, 1 HEAL +30 HP) in left half!
    Plus 12-beat laser corridor!
    """
    g = empty_grid()
    g[5][25] = "K1"
    g[20][25] = "K2"
    g[13][35] = "V"
    for y in range(1, 25):
        g[y][15] = "T_W"
        g[y][16] = "T_W"
        g[y][17] = "T_W"
    # Unavoidable Spring->Mimic bridge at y=13: enter (14,13) SPRING_R from (14,12), T_W at (13,13)!
    g[13][13] = "T_W"
    g[13][14] = "SPRING_R"
    g[13][15] = "PIT"
    g[13][16] = "PIT"
    g[13][17] = "MIMIC"
    g[13][18] = "ONEWAY_R"
    # 3 MIMICs + 1 HEAL in left room
    g[8][6] = "MIMIC"
    g[8][9] = "HEAL"
    g[18][6] = "MIMIC"
    g[18][9] = "MIMIC"
    # Second unavoidable Mimic before V (drops HP 55 -> 10 without HEAL, or 85 -> 40 with HEAL)
    for y in range(1, 25):
        g[y][30] = "T_W"
        g[y][31] = "T_W"
        g[y][32] = "T_W"
    g[13][28] = "T_W"
    g[13][29] = "SPRING_R"
    g[13][30] = "PIT"
    g[13][31] = "PIT"
    g[13][32] = "MIMIC"
    g[13][33] = "ONEWAY_R"
    g[8][34] = "LASER_D"
    g[18][34] = "LASER2_U"
    return g


def main():
    tests = [
        ("NIGHTMARE_1_ICE_STOPPER", build_nightmare_ice_stopper()),
        ("NIGHTMARE_2_4PLATE_5BOX", build_nightmare_4plate_5box()),
        ("NIGHTMARE_3_BOX_SHIELD", build_nightmare_box_shield()),
        ("NIGHTMARE_4_DBL_SW_BANK", build_nightmare_double_switch_bankshot()),
        ("NIGHTMARE_5_MIMIC_HEAL", build_nightmare_mandatory_mimic_heal()),
    ]
    passed = 0
    for name, grid in tests:
        eng = EngineV22(grid)
        obs = eng.get_observation()
        fw = FastWorld()
        t0 = time.perf_counter()
        st0 = fw.build_from_state(obs)
        plan, partial, stats = fw.solve(st0, budget_sec=1.45)
        dt = (time.perf_counter() - t0) * 1000
        if plan is not None:
            e2 = EngineV22(grid)
            for a in plan:
                e2.step(a)
                if e2.status != "RUNNING":
                    break
            ok = (e2.status == "CLEARED")
            if ok:
                passed += 1
            print(f"{name:26s} | {'PASS' if ok else 'FAIL'} | steps={len(plan):3d} | hp={e2.hp:3d} | nodes={stats['nodes']:4d} | time={dt:6.1f}ms")
        else:
            print(f"{name:26s} | UNSOLVED | partial={len(partial):3d} | nodes={stats['nodes']:4d} | time={dt:6.1f}ms")
    print(f"\nNIGHTMARE SUITE: {passed}/{len(tests)}")


if __name__ == "__main__":
    main()
