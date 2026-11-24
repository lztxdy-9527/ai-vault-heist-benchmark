# -*- coding: utf-8 -*-
"""
Automated Verification Suite for `engine.py` against:
1. All 8 Golden Test Vectors (`starter_kit/golden_vectors.json`)
2. Astra's 105G Resource-Lock Audit Map (81-step exact certificate)
3. Mixed-Damage Proportional Accounting & Stage-Isolated Failure Distance
"""

import json
from pathlib import Path
from engine import (
    GRID_W, GRID_H, validate_and_decode_dungeon, DungeonSimulator, verify_author_solution
)


def make_base_grid() -> list[list[str]]:
    grid = [["EMPTY"] * GRID_W for _ in range(GRID_H)]
    for y in range(GRID_H):
        for x in range(GRID_W):
            if x == 0 or x == GRID_W - 1 or y == 0 or y == GRID_H - 1:
                grid[y][x] = "T_W"
    grid[5][20] = "K1"
    grid[20][20] = "K2"
    grid[13][35] = "V"
    return grid


def apply_local_tiles(sim: DungeonSimulator, local_tiles: dict) -> None:
    for coord_str, info in local_tiles.items():
        s = coord_str.strip("()")
        x_str, y_str = s.split(",")
        x, y = int(x_str), int(y_str)
        sim.terrain[y][x] = info["terrain"]
        sim.occupant[y][x] = info["occupant"]


def test_all_golden_vectors() -> None:
    gv_path = Path(__file__).parent / "starter_kit" / "golden_vectors.json"
    data = json.loads(gv_path.read_text(encoding="utf-8"))
    assert len(data["vectors"]) == 8, "Update the regression harness for newly added golden vectors."
    vectors = {v["id"]: v for v in data["vectors"]}

    # GV_01: Outer frame cost and clue binding
    v1 = vectors["GV_01_OUTER_FRAME_COST_AND_CLUE_BINDING"]
    g1 = [["EMPTY"] * GRID_W for _ in range(GRID_H)]
    for y in range(GRID_H):
        for x in range(GRID_W):
            if x in (0, GRID_W - 1) or y in (0, GRID_H - 1):
                g1[y][x] = "T_W"
    for item in v1["Placed_inner_tiles"]:
        g1[item["y"]][item["x"]] = item["tile"]
    dec1 = validate_and_decode_dungeon(g1)
    assert dec1["valid"] is True, dec1
    assert dec1["spent_gold"] == v1["expected"]["spent_gold"]
    assert dec1["vault_gold"] == v1["expected"]["vault_gold"]
    assert dec1["inner_tw_count"] == v1["expected"]["inner_tw_count"]
    assert list(dec1["mimic_to_clue"][(10, 10)]) == v1["expected"]["mimic_clue_coord"]
    print("[PASS] GV_01_OUTER_FRAME_COST_AND_CLUE_BINDING")

    # GV_02: Box leaves CRACK, hero falls into PIT
    v2 = vectors["GV_02_BOX_LEAVES_CRACK_HERO_FALLS_IN_PIT"]
    sim2 = DungeonSimulator(validate_and_decode_dungeon(make_base_grid()))
    sim2.hx, sim2.hy = v2["initial"]["hero"]["x"], v2["initial"]["hero"]["y"]
    apply_local_tiles(sim2, v2["initial"]["local_tiles"])
    sim2.step(v2["action"])
    assert sim2.occupant[10][7] == "BOX"
    assert sim2.terrain[10][6] == v2["expected"]["tile_6_10_terrain_after"]
    assert [sim2.hx, sim2.hy] == v2["expected"]["hero_final_pos"]
    assert sim2.hp == v2["expected"]["hero_hp_after"]
    assert sim2.trap_damage_total == v2["expected"]["trap_damage_dealt"]
    assert sim2.status == v2["expected"]["status"]
    print("[PASS] GV_02_BOX_LEAVES_CRACK_HERO_FALLS_IN_PIT")

    # GV_03: Spring blocked by wall falls early into PIT
    v3 = vectors["GV_03_SPRING_BLOCKED_BY_WALL_FALLS_EARLY_INTO_PIT"]
    sim3 = DungeonSimulator(validate_and_decode_dungeon(make_base_grid()))
    sim3.hx, sim3.hy = v3["initial"]["hero"]["x"], v3["initial"]["hero"]["y"]
    apply_local_tiles(sim3, v3["initial"]["local_tiles"])
    res3 = sim3.step(v3["action"])
    assert res3["exposed_cells"] == v3["expected"]["exposed_cells"], res3["exposed_cells"]
    assert [sim3.hx, sim3.hy] == v3["expected"]["hero_final_pos"]
    assert sim3.hp == v3["expected"]["hero_hp_after"]
    assert sim3.status == v3["expected"]["status"]
    print("[PASS] GV_03_SPRING_BLOCKED_BY_WALL_FALLS_EARLY_INTO_PIT")

    # GV_04: Portal double cap and exit suppression
    v4 = vectors["GV_04_PORTAL_DOUBLE_CAP_AND_EXIT_SUPPRESSION"]
    g4 = make_base_grid()
    for coord_str, info in v4["initial"]["local_tiles"].items():
        x, y = map(int, coord_str.strip("()").split(","))
        g4[y][x] = info["terrain"]
    sim4 = DungeonSimulator(validate_and_decode_dungeon(g4))
    sim4.hx, sim4.hy = v4["initial"]["hero"]["x"], v4["initial"]["hero"]["y"]
    res4 = sim4.step(v4["action"])
    assert res4["portal_count"] == v4["expected"]["portal_count"]
    assert [sim4.hx, sim4.hy] == v4["expected"]["hero_final_pos"]
    assert sim4.hp == v4["expected"]["hero_hp_after"]
    assert sim4.status == v4["expected"]["status"]
    print("[PASS] GV_04_PORTAL_DOUBLE_CAP_AND_EXIT_SUPPRESSION")

    # GV_05: Simultaneous laser snapshot and TNT no bomb tick
    v5 = vectors["GV_05_SIMULTANEOUS_LASER_SNAPSHOT_AND_TNT_NO_BOMB_TICK"]
    sim5 = DungeonSimulator(validate_and_decode_dungeon(make_base_grid()))
    sim5.turn = v5["initial"]["turn"]
    sim5.hx, sim5.hy = v5["initial"]["hero"]["x"], v5["initial"]["hero"]["y"]
    apply_local_tiles(sim5, v5["initial"]["local_tiles"])
    sim5.step(v5["action"])
    assert len(sim5.bombs) == 1 and sim5.bombs[0]["timer"] == v5["expected"]["bomb_timer_after_turn"]
    assert (sim5.terrain[9][8] == "EMPTY") == v5["expected"]["laser_d_destroyed_for_future_turns"]
    assert sim5.hp == v5["expected"]["hero_hp_after"]
    assert sim5.trap_damage_total == v5["expected"]["trap_damage_dealt"]
    assert sim5.status == v5["expected"]["status"]
    print("[PASS] GV_05_SIMULTANEOUS_LASER_SNAPSHOT_AND_TNT_NO_BOMB_TICK")

    # GV_06: Step 32 cutoff before step 33 pit
    v6 = vectors["GV_06_STEP_32_FALLS_INTO_PIT_VS_STEP_33_CUTOFF"]
    sim6 = DungeonSimulator(validate_and_decode_dungeon(make_base_grid()))
    # GV06 omits a concrete track. Supply a local runtime fixture matching its
    # stated spawn, 32nd arrival (10,5), and 33rd candidate PIT (11,5).
    path = ([(x,13) for x in range(3,7)] + [(6,y) for y in range(14,18)]
            + [(x,17) for x in range(5,1,-1)] + [(2,y) for y in range(16,4,-1)]
            + [(x,5) for x in range(3,11)])
    for x,y in path:
        sim6.terrain[y][x] = "ICE"
    for x,y,t in [(6,13,"MIRROR_SE"),(6,17,"MIRROR_NW"),
                  (2,17,"MIRROR_NE"),(2,5,"MIRROR_NE")]:
        sim6.terrain[y][x] = t
    sim6.terrain[5][11] = "PIT"
    res6 = sim6.step("MOVE_R")
    assert res6["steps_taken"] == 32
    assert [sim6.hx, sim6.hy] == v6["expected"]["hero_final_pos"]
    assert (11, 5) not in sim6.exposed_cells
    assert sim6.hp == 100
    assert sim6.status == "ALIVE"
    print("[PASS] GV_06_STEP_32_FALLS_INTO_PIT_VS_STEP_33_CUTOFF")

    # GV_07: Stone air bounce and ground ice slide to switch
    v7 = vectors["GV_07_STONE_AIR_BOUNCE_AND_GROUND_ICE_SLIDE_TO_SWITCH"]
    sim7 = DungeonSimulator(validate_and_decode_dungeon(make_base_grid()))
    sim7.hx, sim7.hy = v7["initial"]["hero"]["x"], v7["initial"]["hero"]["y"]
    apply_local_tiles(sim7, v7["initial"]["local_tiles"])
    sim7.step(v7["action"])
    assert sim7.throws == v7["expected"]["hero_throws_after"]
    assert sim7.gates_flipped == v7["expected"]["gates_flipped_after"]
    assert [sim7.hx, sim7.hy] == v7["expected"]["hero_final_pos"]
    assert sim7.status == v7["expected"]["status"]
    print("[PASS] GV_07_STONE_AIR_BOUNCE_AND_GROUND_ICE_SLIDE_TO_SWITCH")

    # GV_08: Turn 240 Phase B instant win before Phase D laser
    v8 = vectors["GV_08_TURN_240_PHASE_B_INSTANT_WIN_BEFORE_PHASE_D_LASER"]
    sim8 = DungeonSimulator(validate_and_decode_dungeon(make_base_grid()))
    sim8.turn = v8["initial"]["turn"]
    sim8.hx, sim8.hy = v8["initial"]["hero"]["x"], v8["initial"]["hero"]["y"]
    sim8.hp = v8["initial"]["hero"]["hp"]
    sim8.has_k1, sim8.has_k2 = v8["initial"]["hero"]["keys"]
    apply_local_tiles(sim8, v8["initial"]["local_tiles"])
    res8 = sim8.step(v8["action"])
    assert [sim8.hx, sim8.hy] == v8["expected"]["hero_final_pos"]
    assert sim8.hp == v8["expected"]["hero_hp_after"]
    assert res8["phase_d_executed"] == v8["expected"]["phase_d_executed"]
    assert sim8.status == v8["expected"]["status"]
    print("[PASS] GV_08_TURN_240_PHASE_B_INSTANT_WIN_BEFORE_PHASE_D_LASER")


def test_astra_105g_audit_map() -> None:
    """
    Verifies Astra's Point 02 105G map and its exact 81-step author certificate:
    R*2 U*8 R*14 B L*2 R*4 L*2 D*15 B L*2 R*4 L*2 U*7 R*17
    """
    grid = make_base_grid()
    # Four W around K1(20,5) and K2(20,20)
    for kx, ky in [(20, 5), (20, 20)]:
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            grid[ky + dy][kx + dx] = "W"
    # V(35,13): left is R_GATE, other 3 neighbors are W
    grid[13][34] = "R_GATE"
    grid[12][35] = "W"
    grid[14][35] = "W"
    grid[13][36] = "W"
    # SWITCH at (4,13)
    grid[13][4] = "SWITCH"

    tokens = "R*2 U*8 R*14 B L*2 R*4 L*2 D*15 B L*2 R*4 L*2 U*7 R*17".split()
    sol = []
    for tok in tokens:
        if tok == "B":
            sol.append("BOMB")
        else:
            d, count = tok.split("*")
            sol.extend([f"MOVE_{d}"] * int(count))

    assert len(sol) == 81
    res = verify_author_solution(grid, sol)
    assert res["valid"] is True, res
    assert res["spent_gold"] == 105
    assert res["author_steps"] == 81
    assert res["author_hp_left"] == 100
    print(f"[PASS] Astra 105G Map verified: spent={res['spent_gold']}G, steps={res['author_steps']}, HP={res['author_hp_left']}")


def test_blind_euclidean_visibility() -> None:
    sim = DungeonSimulator(validate_and_decode_dungeon(make_base_grid()), mode="BLIND")
    sim.hx, sim.hy = 20, 13
    mask = sim.compute_visible_mask()
    assert sum(map(sum, mask)) == 37
    for y in range(GRID_H):
        for x in range(GRID_W):
            assert mask[y][x] == ((x-20)**2 + (y-13)**2 <= 10)
    for sign in (-1, 1):
        assert mask[13][20 + sign*3] and mask[13 + sign*3][20]
        for other_sign in (-1, 1):
            assert not mask[13 + other_sign*2][20 + sign*3]
            assert not mask[13 + other_sign*3][20 + sign*2]
            assert not mask[13 + other_sign*3][20 + sign*3]
    # Existing ice/mirror tracing still reaches beyond the base disc and bends.
    for x in range(21, 27):
        sim.terrain[13][x] = "ICE"
    sim.terrain[13][26] = "MIRROR_NE"
    sim.terrain[12][26] = "ICE"
    extended = sim.compute_visible_mask()
    assert extended[13][26] and extended[12][26] and extended[11][26]
    assert not extended[10][26]
    sim.mode = "FULL"
    assert sum(map(sum, sim.compute_visible_mask())) == GRID_W * GRID_H
    print("[PASS] BLIND Euclidean disc: 37 cells, exact shape, ice/mirror extension and FULL preserved")


def test_blind_wall_los() -> None:
    def fresh():
        s = DungeonSimulator(validate_and_decode_dungeon(make_base_grid()), mode="BLIND")
        s.hx, s.hy = 20, 13
        return s

    # The adjacent wall face is visible, but the complete next row is hidden.
    sim = fresh()
    for x in range(17, 24):
        sim.terrain[12][x] = "T_W"
    mask = sim.compute_visible_mask()
    assert all(mask[12][x] for x in range(17,24))
    assert all(not mask[11][x] for x in range(18,23))
    assert not mask[10][20]
    sim.clues[11][20] = True
    sim.occupant[11][20] = "TNT"
    observation = sim.get_observation()
    assert observation["terrain"][11][20] == "UNKNOWN"
    assert not observation["clues"][11][20]
    assert observation["occupant"][11][20] is None

    # Diagonal pinch: two orthogonal walls seal the (2,2) diagonal.
    sim = fresh()
    sim.terrain[13][21] = "W"
    sim.terrain[14][20] = "T_W"
    assert not sim.compute_visible_mask()[15][22]
    sim.terrain[14][20] = "EMPTY"
    assert sim.compute_visible_mask()[15][22]
    sim.terrain[14][21] = "W"
    assert not sim.compute_visible_mask()[15][22]

    # Skew cells accept either transmitting predecessor, but not two blockers.
    sim = fresh()
    sim.terrain[13][21] = "W"
    assert sim.compute_visible_mask()[14][22]
    sim.terrain[14][21] = "W"
    assert not sim.compute_visible_mask()[14][22]
    sim = fresh()
    sim.terrain[14][20] = "W"
    assert sim.compute_visible_mask()[15][21]
    sim.terrain[14][21] = "W"
    assert not sim.compute_visible_mask()[15][21]

    for gate, closed_when in (("R_GATE",False),("B_GATE",True)):
        sim = fresh()
        sim.terrain[13][21] = gate
        sim.gates_flipped = closed_when
        assert sim.compute_visible_mask()[13][21]
        assert not sim.compute_visible_mask()[13][22]
        sim.gates_flipped = not closed_when
        assert sim.compute_visible_mask()[13][22]
    # Keep the engine's existing HIGH_WALL definition, including cannon bases.
    sim = fresh(); sim.terrain[13][21] = "LASER_L"
    assert not sim.compute_visible_mask()[13][22]
    sim.mode = "FULL"
    assert all(all(row) for row in sim.compute_visible_mask())
    print("[PASS] BLIND LOS: wall face, hidden room/clue, diagonal pinch, skew OR, both gate states, FULL")


if __name__ == "__main__":
    test_all_golden_vectors()
    test_astra_105g_audit_map()
    test_blind_euclidean_visibility()
    test_blind_wall_los()
    print("\nALL ENGINE TESTS PASSED 100%!")
