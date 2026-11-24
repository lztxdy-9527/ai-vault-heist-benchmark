"""
Carbon's v2.2 Demon Dungeon v2 (Ultra-Lean ~1680G, 0-Key Lockout + 57,000-State Black Hole):
- South-West Basin (x=1..8, y=16..24) contains TWO PLATES (#1, #2) and ONLY TWO BOXES (B1, B2)!
- B1(5,17) sits 1 push from SPRING_R(6,17) -> flies over (7,17) & PIT(8,17) onto PLATE #3(9,17)!
- Pushing B1 -> PLATE #3 leaves 2 plates (#1, #2) with only 1 box (B2) -> plates_active CAN NEVER
  BECOME TRUE, locking ALL THREE P_GATEs (guarding K1, K2, AND V -> opponent gets 0/2 keys!!),
  while B5 & B6 in open Mid-Chamber trap un-pruned solvers in 57,000+ useless Sokoban states!
"""

import collections
import json
import time

from v22_judge import (
    GRID_WIDTH, GRID_HEIGHT, MAX_BUDGET, MAX_AUTHOR_STEPS, TILE_COSTS,
    validate_and_decode_grid_v22, DungeonEngineV22,
)


def create_carbon_v22_grid_lean():
    g = [
        [
            "T_W" if (x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1) else "EMPTY"
            for x in range(GRID_WIDTH)
        ]
        for y in range(GRID_HEIGHT)
    ]

    def hline(y, x1, x2, tile="W"):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            g[y][x] = tile

    def vline(x, y1, y2, tile="W"):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            g[y][x] = tile

    # 1. South-West 2-Plate / 2-Box Basin (x=1..8, y=16..24) against FREE x=0 and FREE y=25!
    # Hero enters via (1,16)->(1,17)->(2,17); g[18][1]="T_W" + x=0 outer T_W blocks external boxes!
    hline(16, 2, 10, "T_W")
    g[18][1] = "T_W"
    vline(8, 17, 24, "T_W")
    g[18][8] = "PIT"           # Blocks pushing boxes across x=8 while letting SPRING_R fly over!

    # Binary Choice Box B1 at (5, 18) ((5,17) is EMPTY so Hero can stand above B1!):
    # - 1-Push Greedy Bait (MOVE_R): SPRING_R(6,18) -> flies over (7,18), PIT(8,18) -> PLATE #3(9,18)!
    # - True Move (MOVE_D): 3 pushes D onto PLATE #2(5,21)!
    g[18][5] = "BOX"           # B1!
    g[18][6] = "SPRING_R"
    g[18][9] = "PLATE"         # PLATE #3!
    g[17][9] = "T_W"
    g[19][9] = "T_W"
    g[17][10] = "T_W"
    g[19][10] = "T_W"
    g[18][10] = "ONEWAY_L"
    g[18][11] = "R_GATE"

    g[21][5] = "PLATE"         # PLATE #2!
    g[22][5] = "W"

    # B2 at (3, 21) -> pushed D onto PLATE #1(3, 23)!
    g[21][3] = "BOX"           # B2!
    g[23][3] = "PLATE"         # PLATE #1!
    g[24][3] = "W"

    # 2. Mid Chamber: Remote ONEWAY + MIRROR + ICE Stone-Throw Switch + B3 + Decoy B5/B6
    hline(1, 15, 20, "W")
    hline(3, 17, 20, "W")
    g[2][15] = "W"
    g[2][16] = "MIRROR_NE"
    g[3][16] = "PIT"
    g[4][16] = "ONEWAY_D"
    g[3][15] = "W"
    g[4][15] = "W"
    g[4][17] = "W"
    g[2][18] = "ICE"
    g[2][19] = "ICE"
    g[2][20] = "SWITCH"
    g[2][21] = "W"

    # B3 at (12, 18) -> once R_GATE(11,18) opens, pushed L onto PLATE #3(9,18)!
    g[17][12] = "W"
    g[19][12] = "W"
    g[18][12] = "BOX"          # B3!

    # Decoy Free Boxes B4, B5 in open Mid-Chamber (combusts opponent state space into 57,000+ states!)
    g[8][18] = "BOX"
    g[8][21] = "BOX"

    # 3. South-East K2 Pocket -> K2=(34, 23) (sealed by explosion-immune T_W + P_GATE #1! 0 keys if trapped!)
    g[23][32] = "P_GATE"
    g[22][32] = "T_W"
    g[24][32] = "T_W"
    hline(22, 33, 35, "W")
    hline(21, 33, 35, "W")
    hline(20, 33, 35, "W")     # 3-thick W roof (5G/tile, immune to 2 bombs!)
    vline(35, 22, 24, "T_W")
    g[24][33] = "W"
    g[24][34] = "W"
    g[23][34] = "K2"

    # 4. North-East Venus Flytrap & 12-Beat Dual-Laser Fortress -> P_GATE #2 -> K1=(33, 2)
    hline(3, 22, 35, "W")
    g[2][21] = "LASER_R"
    g[1][22] = "EMPTY"
    g[1][23] = "ONEWAY_R"
    g[1][24] = "EMPTY"
    g[1][25] = "W"
    g[1][26] = "EMPTY"
    g[1][27] = "EMPTY"
    for xx in range(28, 35):
        g[1][xx] = "W"
    g[1][31] = "T_W"
    g[3][32] = "T_W"
    g[3][33] = "T_W"
    g[3][34] = "T_W"
    g[2][35] = "T_W"
    g[1][35] = "W"

    g[12][28] = "LASER2_U"
    g[3][28] = "PIT"

    g[2][24] = "MIRROR_NE"
    g[2][25] = "ICE"
    for xx in range(28, 32):
        g[2][xx] = "ICE"
    g[2][32] = "P_GATE"        # P_GATE #2!
    g[2][33] = "K1"
    g[2][34] = "PORTAL_1A"

    # PORTAL_1B one-way exit at (30, 13) -> Vault!
    g[12][30] = "W"
    g[14][30] = "W"
    g[13][29] = "W"
    g[13][30] = "PORTAL_1B"
    g[13][31] = "ONEWAY_R"

    # 5. East Vault Sanctum -> V=(37, 13) (12-beat crossfire + R_GATE + P_GATE #3!)
    hline(12, 31, 38, "W")
    hline(14, 31, 38, "W")
    g[12][36] = "T_W"
    g[12][37] = "T_W"
    g[14][36] = "T_W"
    g[14][37] = "T_W"
    g[13][38] = "T_W"

    g[12][34] = "PIT"
    g[14][34] = "PIT"
    g[7][34] = "LASER_D"
    g[19][34] = "LASER2_U"

    g[13][35] = "R_GATE"
    g[13][36] = "P_GATE"       # P_GATE #3!
    g[13][37] = "V"

    return g


if __name__ == "__main__":
    import submission as sub
    import verify_submission_v22 as vs

    grid = create_carbon_v22_grid_lean()
    ok, msg, dec = validate_and_decode_grid_v22(grid, check_spawn_4turn=True)
    print("Validation:", ok, msg)
    assert ok, msg
    print("Spent Gold:", dec["spent_gold"], "Vault Gold:", MAX_BUDGET - dec["spent_gold"],
          f"(g = {(MAX_BUDGET - dec['spent_gold'])/MAX_BUDGET:.3f})")

    eng = DungeonEngineV22(dec)
    sim_eng = sub._decode_state_to_eng(eng.get_observation())
    t0 = time.monotonic()
    ok_w, sol = sub._solve_full_dungeon(sim_eng, 1.56)
    dt_ms = (time.monotonic() - t0) * 1000.0
    print(f"Carbon Solver: ok={ok_w}, len={len(sol)} in {dt_ms:.1f} ms")
    assert ok_w and len(sol) <= MAX_AUTHOR_STEPS
    for idx, a in enumerate(sol):
        eng.step(a)
        assert eng.status == ("ALIVE" if idx < len(sol) - 1 else "CLEARED")
    print(f"Replay OK! Steps={eng.turn}, HP={eng.hp}")
    print("SOL_JSON =", json.dumps(sol))

    print("\n--- Testing Standard Opponent against Lean v2 Dungeon ---")
    vs.run_match_v22(vs.opponent_standard_macro_astar, grid, "OPP_Standard_Macro_AStar")
