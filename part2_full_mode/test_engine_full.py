# -*- coding: utf-8 -*-
"""
Comprehensive Dual-Audit Regression Suite for Half-2 v2.2 (`test_engine_full.py`).
Tests all Scheme-C mechanics (PLATE/P_GATE, LASER2 mod 4 + LCM 12, ONEWAY 9 callsites),
GPT & Red-Team audit counterexamples, spawn admissibility, scoring invariants, and sandbox respawn.
"""

from __future__ import annotations
import hashlib
import json
import sys
import tempfile
from pathlib import Path

PART2_DIR = Path(__file__).resolve().parent
if str(PART2_DIR) not in sys.path:
    sys.path.insert(0, str(PART2_DIR))

import engine_full as engine
import official_maps_full as official_maps
from submission_sandbox_full import SubmissionProcess


def empty_grid():
    g = [["EMPTY"] * engine.GRID_W for _ in range(engine.GRID_H)]
    for y in range(engine.GRID_H):
        for x in range(engine.GRID_W):
            if x in (0, engine.GRID_W - 1) or y in (0, engine.GRID_H - 1):
                g[y][x] = "T_W"
    g[5][20] = "K1"
    g[20][20] = "K2"
    g[13][35] = "V"
    return g


def test_plate_and_pgate_rules():
    # 1. Validation: P_GATE without PLATE or PLATE > BOX must fail
    g = empty_grid()
    g[13][34] = "P_GATE"
    assert not engine.validate_and_decode_dungeon(g)["valid"], "P_GATE without PLATE must fail"

    g[8][8] = "PLATE"
    assert not engine.validate_and_decode_dungeon(g)["valid"], "P_GATE with PLATE > BOX must fail"

    g[8][6] = "BOX"
    dec = engine.validate_and_decode_dungeon(g)
    assert dec["valid"], f"Valid 1 PLATE + 1 BOX + 1 P_GATE failed: {dec}"
    assert dec["spent_gold"] == 30 + 45 + 30

    # Caps check: BOX cap=6, PLATE cap=4, P_GATE cap=8
    g_caps = empty_grid()
    for i in range(6):
        g_caps[2][5 + i] = "BOX"
    for i in range(4):
        g_caps[3][5 + i] = "PLATE"
    for i in range(8):
        g_caps[4][5 + i] = "P_GATE"
    assert engine.validate_and_decode_dungeon(g_caps)["valid"]

    g_over_box = [r[:] for r in g_caps]
    g_over_box[2][12] = "BOX"
    assert not engine.validate_and_decode_dungeon(g_over_box)["valid"]

    g_over_plate = [r[:] for r in g_caps]
    g_over_plate[3][9] = "PLATE"
    assert not engine.validate_and_decode_dungeon(g_over_plate)["valid"]

    g_over_pgate = [r[:] for r in g_caps]
    g_over_pgate[4][13] = "P_GATE"
    assert not engine.validate_and_decode_dungeon(g_over_pgate)["valid"]

    # 2. BOX-only trigger: Hero standing on PLATE does NOT activate; BOMB on PLATE does NOT activate
    g2 = empty_grid()
    g2[13][5] = "PLATE"
    g2[13][34] = "P_GATE"
    g2[10][10] = "BOX"
    sim = engine.DungeonSimulator(engine.validate_and_decode_dungeon(g2))
    for _ in range(3):
        sim.step("MOVE_R")  # -> (5,13) PLATE
    assert (sim.hx, sim.hy) == (5, 13)
    assert not sim.is_plates_active(), "Hero must NOT trigger PLATE"
    sim.step("BOMB")
    sim.step("MOVE_L")
    assert not sim.is_plates_active(), "BOMB must NOT trigger PLATE"

    # 3. Trapped BOX inside P_GATE & Phase C/D box destruction closing P_GATE immediately
    g3 = empty_grid()
    g3[13][7] = "BOX"
    g3[13][8] = "PLATE"
    g3[13][9] = "P_GATE"
    g3[13][10] = "LASER_D"  # no, use LASER_L at (12,13) to test beam blocking by closed P_GATE
    g3[13][12] = "LASER_L"
    g3[13][4] = "BOX"
    g3[13][15] = "EMPTY"
    sim3 = engine.DungeonSimulator(engine.validate_and_decode_dungeon(g3))
    # Setup: put hero at (6,13), push BOX(7,13) R onto PLATE(8,13)
    sim3.hx, sim3.hy = 6, 13
    sim3.step("MOVE_R")  # Hero@(7,13), BOX@(8,13=PLATE) -> plates_active=True!
    assert sim3.is_plates_active()
    assert not sim3.is_high_wall(9, 13)
    # Now push BOX from PLATE(8,13) ONTO P_GATE(9,13)!
    # Step 3 places BOX inside P_GATE(9,13), PLATE(8,13) empty -> plates_active flips False immediately!
    # Hero follow-up onto P_GATE(9,13) is blocked (is_high_wall True) -> Hero stays at (7,13)?
    # Wait: Hero was at (7,13), pushing BOX at (8,13) R -> x1=(8,13) IS EMPTY PLATE, NOT P_GATE!
    # So Hero steps onto (8,13) and BOX stays trapped inside P_GATE(9,13)!
    sim3.step("MOVE_R")
    assert sim3.occupant[13][9] == "BOX"
    assert (sim3.hx, sim3.hy) == (8, 13)
    assert not sim3.is_plates_active()
    # Trapped BOX inside closed P_GATE(9,13) cannot be pushed further R from (8,13) because is_high_wall(9,13)==True
    # Actually Wait: P_GATE(9,13) is closed high wall, so Hero at (8,13) cannot enter (9,13)!
    sim3.step("MOVE_R")
    assert sim3.occupant[13][9] == "BOX" and (sim3.hx, sim3.hy) == (8, 13)

    # 4. Phase C bomb destroys BOX on PLATE BEFORE Phase D laser on same turn (turn 3)
    g4 = empty_grid()
    g4[10][10] = "PLATE"
    g4[10][10] = "PLATE"
    g4[10][11] = "EMPTY"
    g4[10][9] = "EMPTY"
    g4[10][12] = "P_GATE"
    g4[10][15] = "LASER_L"  # shoots L up to 10 cells (14..5) on Turn 3
    # Move hero to (10,11), put BOX on (10,10), place bomb at (10,11) at Turn 1?
    # Better: use manual sim state at turn=3 with bomb timer=1 at (10,10) under BOX!
    g4[10][8] = "BOX"
    dec4 = engine.validate_and_decode_dungeon(g4)
    sim4 = engine.DungeonSimulator(dec4)
    sim4.occupant[10][8] = None
    sim4.occupant[10][10] = "BOX"  # Box on PLATE(10,10) -> P_GATE(12,10) open!
    assert sim4.is_plates_active()
    sim4.hx, sim4.hy = 7, 10  # Hero on row y=10 in range of LASER_L@(15,10)
    sim4.bombs = [{"id": 1, "x": 10, "y": 10, "timer": 1}]
    sim4.turn = 3
    res4 = sim4.step("WAIT")
    # Phase C blows up bomb & BOX@(10,10) -> P_GATE(12,10) closes BEFORE Phase D LASER_L fires!
    # Therefore Hero at (7,10) MUST NOT be hit by LASER_L@(15,10)!
    assert not sim4.is_plates_active()
    assert res4["plates_active"] is False
    assert sim4.hp == 100, f"Closed P_GATE in Phase C should block Turn-3 laser, got hp={sim4.hp}"

    # 5. Phase D laser triggers TNT that destroys BOX on PLATE -> updates plates_active without retracting fired beam
    g5 = empty_grid()
    g5[10][10] = "PLATE"
    g5[10][11] = "TNT"
    g5[10][14] = "LASER2_L"  # period=4 fires at turn=4, hits TNT@(11,10), blast 3x3 destroys BOX@(10,10)
    g5[13][34] = "P_GATE"
    g5[10][8] = "BOX"
    dec5 = engine.validate_and_decode_dungeon(g5)
    sim5 = engine.DungeonSimulator(dec5)
    sim5.occupant[10][8] = None
    sim5.occupant[10][10] = "BOX"
    sim5.hx, sim5.hy = 5, 13  # safe
    sim5.turn = 4
    res5 = sim5.step("WAIT")
    assert sim5.occupant[10][10] is None, "Phase D TNT explosion should destroy BOX on PLATE"
    assert res5["plates_active"] is False
    assert sim5.is_high_wall(34, 13), "P_GATE must close after Phase D TNT destroys BOX"
    print("[PASS] test_plate_and_pgate_rules")


def test_dual_period_lasers_and_lcm12():
    g = empty_grid()
    g[8][15] = "LASER_D"   # period=3 -> sweeps x=15, y=9..18
    g[8][16] = "LASER2_D"  # period=4 -> sweeps x=16, y=9..18
    g[10][12] = "LASER2_R" # period=4 -> sweeps y=10, x=13..22 (crosses (15,10)!)
    dec = engine.validate_and_decode_dungeon(g)
    assert dec["valid"]
    assert dec["spent_gold"] == 75 + 90 + 90

    # Turn 3: only LASER_D fires (period 3)
    sim = engine.DungeonSimulator(dec)
    sim.turn = 3
    obs3 = sim.get_observation()
    assert all(w["period"] == 3 for w in obs3["laser_warnings"])
    sim.hx, sim.hy = 15, 10
    sim.step("WAIT")
    assert sim.hp == 50  # hit by red LASER_D only

    # Turn 4: only LASER2 fires (period 4)
    sim = engine.DungeonSimulator(dec)
    sim.turn = 4
    obs4 = sim.get_observation()
    assert all(w["period"] == 4 for w in obs4["laser_warnings"])
    assert any(w["x"] == 15 and w["y"] == 10 and w["period"] == 4 for w in obs4["laser_warnings"])
    sim.hx, sim.hy = 15, 10
    sim.step("WAIT")
    assert sim.hp == 50  # hit by blue LASER2_R only

    # Turn 12 (LCM(3,4)): BOTH Red LASER_D and Blue LASER2_R hit (15,10) -> 100 damage instant kill!
    sim = engine.DungeonSimulator(dec)
    sim.turn = 12
    obs12 = sim.get_observation()
    periods_at_15_10 = {w["period"] for w in obs12["laser_warnings"] if w["x"] == 15 and w["y"] == 10}
    assert periods_at_15_10 == {3, 4}, f"Expected both periods at (15,10), got {periods_at_15_10}"
    sim.hx, sim.hy = 15, 10
    sim.step("WAIT")
    assert sim.hp == 0 and sim.status == "DEAD" and sim.death_reason == "LASER"

    # Destructibility check: LASER2_* is destroyed by BOMB explosion
    sim_b = engine.DungeonSimulator(dec)
    sim_b.hx, sim_b.hy = 16, 9
    sim_b.step("BOMB")
    sim_b.step("MOVE_R")
    sim_b.step("MOVE_R")
    assert sim_b.terrain[8][16] == "EMPTY", "LASER2_D should be destroyed by BOMB"

    # Quota check: 12 max shared between LASER and LASER2
    g_q = empty_grid()
    for i in range(6):
        g_q[2][10 + i] = "LASER_D"
        g_q[22][10 + i] = "LASER2_U"
    assert engine.validate_and_decode_dungeon(g_q)["valid"]
    g_q[2][17] = "LASER2_D"
    assert not engine.validate_and_decode_dungeon(g_q)["valid"]
    print("[PASS] test_dual_period_lasers_and_lcm12")


def test_oneway_9_callsites_matrix():
    # 1. Hero MOVE blocked vs allowed & CRACK not collapsed on failed move/push/jump
    g = empty_grid()
    g[13][5] = "CRACK"
    g[13][6] = "ONEWAY_L"  # Can only enter from R going L!
    dec = engine.validate_and_decode_dungeon(g)
    sim = engine.DungeonSimulator(dec)
    sim.hx, sim.hy = 5, 13
    sim.step("MOVE_R")  # Blocked by ONEWAY_L!
    assert (sim.hx, sim.hy) == (5, 13)
    assert sim.terrain[13][5] == "CRACK", "Failed MOVE against ONEWAY must NOT collapse CRACK"

    # 2. JUMP blocked when landing on OR passing over opposing ONEWAY_L
    sim.step("JUMP_R")  # p1=(6,13) is ONEWAY_L! Jump fails, consumes 1 jump, CRACK still intact!
    assert (sim.hx, sim.hy) == (5, 13) and sim.jumps == 2
    assert sim.terrain[13][5] == "CRACK"

    g_land = empty_grid()
    g_land[13][7] = "ONEWAY_L"
    sim_l = engine.DungeonSimulator(engine.validate_and_decode_dungeon(g_land))
    sim_l.hx, sim_l.hy = 5, 13
    sim_l.step("JUMP_R")  # p2=(7,13) is ONEWAY_L! Blocked!
    assert (sim_l.hx, sim_l.hy) == (5, 13) and sim_l.jumps == 2

    # Aligned JUMP succeeds across or onto ONEWAY_R
    g_ok = empty_grid()
    g_ok[13][6] = "ONEWAY_R"
    g_ok[13][7] = "ONEWAY_R"
    sim_ok = engine.DungeonSimulator(engine.validate_and_decode_dungeon(g_ok))
    sim_ok.hx, sim_ok.hy = 5, 13
    sim_ok.step("JUMP_R")
    assert (sim_ok.hx, sim_ok.hy) == (7, 13)

    # 3. BOX standing ON ONEWAY_L cannot be pushed R (pre-check rejects whole push)
    g_box = empty_grid()
    g_box[13][6] = "ONEWAY_L"
    g_box[13][5] = "CRACK"
    sim_box = engine.DungeonSimulator(engine.validate_and_decode_dungeon(g_box))
    sim_box.occupant[13][6] = "BOX"
    sim_box.hx, sim_box.hy = 5, 13
    sim_box.step("MOVE_R")
    assert sim_box.occupant[13][6] == "BOX" and (sim_box.hx, sim_box.hy) == (5, 13)
    assert sim_box.terrain[13][5] == "CRACK"

    # 4. MIRROR_* deflects to new_dir -> MUST check new_dir against ONEWAY_*
    # MIRROR_NE turns moving R into moving U! Put ONEWAY_R above MIRROR_NE (aligned with old R, opposed to new U!)
    g_mir = empty_grid()
    g_mir[10][10] = "MIRROR_NE"
    g_mir[9][10] = "ONEWAY_R"  # Requires dir=R; MIRROR_NE outputs dir=U -> MUST BLOCK!
    sim_m = engine.DungeonSimulator(engine.validate_and_decode_dungeon(g_mir))
    sim_m.hx, sim_m.hy = 9, 10
    sim_m.step("MOVE_R")
    assert (sim_m.hx, sim_m.hy) == (10, 10), "MIRROR_NE must check new_dir=U (blocked by ONEWAY_R)"

    # Now ONEWAY_U above MIRROR_NE (new_dir=U matches!) -> MUST ENTER (10,9) and STOP cleanly
    g_mir2 = empty_grid()
    g_mir2[10][10] = "MIRROR_NE"
    g_mir2[9][10] = "ONEWAY_U"
    sim_m2 = engine.DungeonSimulator(engine.validate_and_decode_dungeon(g_mir2))
    sim_m2.hx, sim_m2.hy = 9, 10
    sim_m2.step("MOVE_R")
    assert (sim_m2.hx, sim_m2.hy) == (10, 9), "MIRROR_NE should enter ONEWAY_U along new_dir=U"
    # Exit from ONEWAY_U is unrestricted in any direction (D onto MIRROR_NE slides R to (11,10)):
    sim_m2.step("MOVE_D")
    assert (sim_m2.hx, sim_m2.hy) == (11, 10), "Exiting ONEWAY must not be restricted (MIRROR_NE deflects D->R to (11,10))"

    # 5. SPRING_* respects ONEWAY per tile & ICE stops before opposing ONEWAY
    g_spr = empty_grid()
    g_spr[10][10] = "SPRING_R"
    g_spr[10][12] = "ONEWAY_L"  # at k=2! Hero should land at k=1 (11,10)!
    g_spr[14][10] = "ICE"
    g_spr[14][11] = "ICE"
    g_spr[14][12] = "ONEWAY_L"
    sim_s = engine.DungeonSimulator(engine.validate_and_decode_dungeon(g_spr))
    sim_s.hx, sim_s.hy = 9, 10
    sim_s.step("MOVE_R")
    assert (sim_s.hx, sim_s.hy) == (11, 10), "SPRING_R blocked at k=2 should land at k=1"
    sim_s.hx, sim_s.hy = 9, 14
    sim_s.step("MOVE_R")
    assert (sim_s.hx, sim_s.hy) == (11, 14), "ICE slide should stop before opposing ONEWAY_L"

    # 6. PORTAL exit step respects ONEWAY_* (teleport itself ignores portal vector, exit step enforces dir)
    g_por = empty_grid()
    g_por[10][10] = "PORTAL_1A"
    g_por[8][25] = "PORTAL_1B"
    g_por[8][26] = "ONEWAY_L"  # Opposes R exit from PORTAL_1B -> Hero stops on PORTAL_1B (25,8)!
    sim_p = engine.DungeonSimulator(engine.validate_and_decode_dungeon(g_por))
    sim_p.hx, sim_p.hy = 9, 10
    sim_p.step("MOVE_R")
    assert (sim_p.hx, sim_p.hy) == (25, 8)

    # 7. THROW passes ONEWAY in air, stops on ground slide; LASER passes ONEWAY; ONEWAY immune to BOMB
    g_tl = empty_grid()
    g_tl[10][6] = "ONEWAY_L"
    g_tl[10][7] = "SWITCH"
    g_tl[10][8] = "ONEWAY_R"
    g_tl[10][12] = "LASER_L"
    g_tl[15][6] = "ICE"
    g_tl[15][11] = "ICE"  # 6th tile from (5,15) R! -> enters ground slide
    g_tl[15][12] = "ONEWAY_L"
    g_tl[15][13] = "SWITCH"
    sim_t = engine.DungeonSimulator(engine.validate_and_decode_dungeon(g_tl))
    sim_t.hx, sim_t.hy = 5, 10
    sim_t.step("THROW_R")  # Air throw through opposing ONEWAY_L(6,10) hits SWITCH(7,10)!
    assert sim_t.gates_flipped is True
    # Laser passes freely through ONEWAY_R(8,10) unless blocked by BOX
    sim_t.turn = 3
    sim_t.step("WAIT")
    assert sim_t.hp == 50, "Laser must pass freely through ONEWAY"
    # Explosion immunity
    sim_t.hx, sim_t.hy = 6, 10
    sim_t.step("BOMB")
    sim_t.step("MOVE_L"); sim_t.step("MOVE_L"); sim_t.step("MOVE_L")
    assert sim_t.terrain[10][6] == "ONEWAY_L", "ONEWAY must be explosion immune"
    # Ground slide stops on ONEWAY_*
    sim_t2 = engine.DungeonSimulator(engine.validate_and_decode_dungeon(g_tl))
    sim_t2.hx, sim_t2.hy = 5, 15
    sim_t2.step("THROW_R")  # Lands 6th air tile on ICE(11,15) -> slides onto ONEWAY_L(12,15) and stops!
    assert sim_t2.gates_flipped is False, "Ground slide stone must stop on ONEWAY_* without hitting SWITCH"
    print("[PASS] test_oneway_9_callsites_matrix")


def test_gpt_counterexamples_admissibility_and_scoring():
    # 1. GPT P0-03 Counterexample A: Full vertical T_W column at x=10 with ONLY 1 no-switch R_GATE (bombable!)
    g_a = empty_grid()
    for y in range(1, engine.GRID_H - 1):
        g_a[y][10] = "T_W"
    g_a[13][10] = "R_GATE"  # No SWITCH anywhere! Hero bombs R_GATE!
    dec_a = engine.validate_and_decode_dungeon(g_a)
    assert dec_a["valid"], f"Bombable no-switch R_GATE must NOT be falsely rejected: {dec_a}"
    sol_a = (
        ["MOVE_R"] * 7 + ["BOMB"] + ["MOVE_L"] * 2 + ["WAIT"] + ["MOVE_R"] * 2  # blows up (10,13)
        + ["MOVE_R"] * 9 + ["MOVE_U"] * 8  # (18,5) -> WAIT: (9+9=18, U*8->(18,5))
        + ["MOVE_R"] * 2  # (20,5 K1)
        + ["MOVE_D"] * 15 # (20,20 K2)
        + ["MOVE_U"] * 7 + ["MOVE_R"] * 15
    )
    ver_a = engine.verify_author_solution(g_a, sol_a)
    assert ver_a["valid"], f"Counterexample A certificate failed: {ver_a}"

    # 2. GPT P0-03 Counterexample B: 2-wide PIT moat at x=10, 11 with BOX at (8,13)
    g_b = empty_grid()
    for y in range(1, engine.GRID_H - 1):
        g_b[y][10] = "PIT"
        g_b[y][11] = "PIT"
    g_b[13][8] = "BOX"
    dec_b = engine.validate_and_decode_dungeon(g_b)
    assert dec_b["valid"], f"2-wide PIT + BOX moat must NOT be rejected: {dec_b}"
    sol_b = (
        ["MOVE_R"] * 7  # push BOX from (8,13)->(10,13 fills PIT!), Hero@(9,13)
        + ["MOVE_R"]    # Hero@(10,13)
        + ["JUMP_R"]    # jumps (11,13 PIT) -> (12,13)!
        + ["MOVE_R"] * 8 + ["MOVE_U"] * 8  # (20,5 K1)
        + ["MOVE_D"] * 15 # (20,20 K2)
        + ["MOVE_U"] * 7 + ["MOVE_R"] * 15
    )
    ver_b = engine.verify_author_solution(g_b, sol_b)
    assert ver_b["valid"], f"Counterexample B certificate failed: {ver_b}"

    # 3. Anti-spawn-camp admissibility check blocks Turn 1..4 spawn trap cages
    g_cage = empty_grid()
    # Wall in spawn zone tightly at x=4 and y=11,15 so only (1..3, 12..14) reachable, then fire LASER_D/L on Turn 3 & LASER2 on Turn 4!
    for x in range(1, 5):
        g_cage[11][x] = "T_W"
        g_cage[15][x] = "T_W"
    for y in range(11, 16):
        g_cage[y][4] = "T_W"
    #Wait: spawn is locked in 3x3 box! Put LASER2_L at (5, 12..14) won't pierce T_W(4,12..14).
    # Put cannons INSIDE perimeter at (6,12..14) shooting L with NO wall at x=4 -> wall at x=5 behind cannons doesn't block cannons!
    g_trap = empty_grid()
    g_trap[10][1] = "LASER_D"; g_trap[10][2] = "LASER_D"; g_trap[10][3] = "LASER_D"
    g_trap[12][5] = "T_W"; g_trap[13][5] = "T_W"; g_trap[14][5] = "T_W"
    g_trap[16][1] = "T_W"; g_trap[16][2] = "T_W"; g_trap[16][3] = "T_W"
    g_trap[11][1] = "T_W"; g_trap[11][2] = "T_W"; g_trap[11][3] = "T_W"  # blocks above, leaving x=4 open unless... wait:
    # Make Turn 3 red cannons at (7,12), (7,13), (7,14) + wall at (1..3,15) + wall at (1..3,11), and LASER_L at (6,12..14) shoots through x=1..4!
    g_trap = empty_grid()
    g_trap[12][5] = "LASER_L"; g_trap[13][5] = "LASER_L"; g_trap[14][5] = "LASER_L"
    g_trap[11][1] = "T_W"; g_trap[11][2] = "T_W"; g_trap[11][3] = "T_W"; g_trap[11][4] = "T_W"
    g_trap[15][1] = "T_W"; g_trap[15][2] = "T_W"; g_trap[15][3] = "T_W"; g_trap[15][4] = "T_W"
    g_trap[12][4] = "EMPTY"; g_trap[13][4] = "EMPTY"; g_trap[14][4] = "EMPTY"
    # Add Turn 3 LASER_D at (4,10) with (4,11)=EMPTY -> only 1 exit? If (4,11)=T_W, (1..4, 12..14) is swept by LASER_L@(5,12..14) on Turn 3 AND Wait (5,12..14) blocks x=5 -> Hero can NEVER escape x<=4 by Turn 3!
    res_trap = engine.validate_and_decode_dungeon(g_trap)
    assert not res_trap["valid"], "Unavoidable Turn-3 spawn laser trap must be rejected!"

    # 4. Scoring invariants
    sim_sc = engine.DungeonSimulator(dec_a)
    sim_sc.status = "CLEARED"
    sim_sc.trap_damage_total = 100.0
    sc_max = sim_sc.compute_scores(turns_elapsed=240)
    assert sc_max["demon_score"] == 320.0, f"Expected CLEARED cap 320.0, got {sc_max}"
    sim_sc.status = "DQ"
    sc_dq = sim_sc.compute_scores(turns_elapsed=3)
    sim_sc.status = "TIMEOUT"
    sc_to = sim_sc.compute_scores(turns_elapsed=3)
    sim_sc.status = "DEAD"
    sc_dead = sim_sc.compute_scores(turns_elapsed=3)
    # DQ must equal TIMEOUT formula (strictly below DEAD kill bonus!)
    assert sc_dq["demon_score"] == sc_to["demon_score"] and sc_dq["demon_score"] < sc_dead["demon_score"]
    # Zero-sum wait at Vault check: delta(Hero) + delta(Demon) == 0 across any two clear turns T1, T2
    sim_sc.status = "CLEARED"; sim_sc.hp = 100
    c1 = sim_sc.compute_scores(turns_elapsed=80)
    c2 = sim_sc.compute_scores(turns_elapsed=160)
    assert round((c1["hero_score"] + c1["demon_score"]) - (c2["hero_score"] + c2["demon_score"]), 3) == 0.0

    # Author length cap = 200
    assert not engine.verify_author_solution(g_a, ["WAIT"] * 201)["valid"]

    # Official + backup maps check
    maps = official_maps.get_all_official_maps() + official_maps.get_all_backup_maps()
    assert len(maps) == 14
    print("[PASS] test_gpt_counterexamples_admissibility_and_scoring")


def test_sandbox_respawn_and_turn1_budget():
    bot_code = """
import time
def build_dungeon():
    g = [["T_W" if (x in (0, 39) or y in (0, 25)) else "EMPTY" for x in range(40)] for y in range(26)]
    g[5][20] = "K1"; g[20][20] = "K2"; g[13][35] = "V"
    return {"taunt": "test", "grid": g, "author_solution": ["MOVE_R"]}

def decide_action(state, memory):
    if state["turn"] == 1 and not memory.get("did_sleep"):
        memory["did_sleep"] = True
        time.sleep(0.9)
    elif state["turn"] == 2:
        time.sleep(0.8)  # Force deliberate Turn-2 0.5s timeout!
    return "WAIT"
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
        tf.write(bot_code)
        bot_path = Path(tf.name)
    try:
        dec = engine.validate_and_decode_dungeon(empty_grid())
        sim = engine.DungeonSimulator(dec, mode="FULL")
        with SubmissionProcess(bot_path) as worker:
            # Turn 1: 0.9s MUST succeed under 2.0s budget!
            act1 = worker.call("decide", 2.0, state=sim.get_observation())
            assert act1 == "WAIT"
            sim.step(act1)
            # Turn 2: 0.8s exceeds 0.5s -> TimeoutError -> respawn -> Turn 3 succeeds cleanly!
            try:
                worker.call("decide", 0.5, state=sim.get_observation())
                assert False, "Expected Turn-2 TimeoutError"
            except TimeoutError:
                worker.respawn()
            sim.step("WAIT")
            act3 = worker.call("decide", 0.5, state=sim.get_observation())
            assert act3 == "WAIT"
    finally:
        bot_path.unlink(missing_ok=True)
    print("[PASS] test_sandbox_respawn_and_turn1_budget")


def test_gpt_p0_1_bomb_spawn_admissibility():
    g = empty_grid()
    g[5][20] = "EMPTY"; g[20][20] = "EMPTY"; g[13][35] = "EMPTY"
    g[5][12] = "K1"; g[19][12] = "K2"; g[19][33] = "V"
    g[10][1] = "T_W"; g[11][1] = "LASER2_D"; g[15][1] = "T_W"
    g[10][2] = "T_W"; g[11][2] = "LASER2_D"; g[15][2] = "T_W"
    g[11][3] = "T_W"; g[15][3] = "LASER2_U"
    g[12][4] = "T_W"; g[13][4] = "T_W"; g[14][4] = "T_W"

    dec = engine.validate_and_decode_dungeon(g, check_spawn=True)
    assert dec["valid"], f"2-route BOMB map must pass spawn admissibility: {dec}"

    route_a = ["MOVE_U", "BOMB", "MOVE_D", "MOVE_D"]
    route_b = ["MOVE_D", "BOMB", "MOVE_R", "JUMP_U"]
    for label, seq in (("RouteA", route_a), ("RouteB", route_b)):
        sim = engine.DungeonSimulator(dec, mode="FULL")
        for act in seq:
            sim.step(act)
        assert sim.status == "ALIVE" and sim.hp == 100 and sim.trap_damage_total == 0.0, (
            f"{label} failed 4-turn survival: status={sim.status} hp={sim.hp} dmg={sim.trap_damage_total}"
        )

    sol = (
        route_b
        + ["MOVE_D"] * 4
        + ["MOVE_R"] * 9
        + ["MOVE_U"] * 11
        + ["MOVE_D"] * 14
        + ["MOVE_R"] * 21
    )
    ver = engine.verify_author_solution(g, sol, check_spawn=True)
    assert ver["valid"] and ver["author_steps"] == 63 and ver["author_hp_left"] == 100, ver
    print("[PASS] test_gpt_p0_1_bomb_spawn_admissibility")


def test_gpt_p0_2_in_memory_hash_lock():
    import run_tournament_full as rt

    bot_template = """
def build_dungeon():
    g = [["T_W" if (x in (0, 39) or y in (0, 25)) else "EMPTY" for x in range(40)] for y in range(26)]
    g[5][20] = "K1"; g[20][20] = "K2"; g[13][35] = "V"
    sol = ["MOVE_R"] * 18 + ["MOVE_U"] * 8 + ["MOVE_D"] * 15 + ["MOVE_U"] * 7 + ["MOVE_R"] * 15
    return {"taunt": "lock", "grid": g, "author_solution": sol}

def decide_action(state, memory):
    return %r
"""
    with tempfile.TemporaryDirectory() as td:
        bot_path = Path(td) / "submission.py"
        bot_path.write_text(bot_template % "WAIT", encoding="utf-8")
        sub = rt.ModelSubmission("lock_model", bot_path)
        locked_sha = sub.submission_sha256

        # Overwrite on disk AFTER ModelSubmission read/locked bytes in memory
        bot_path.write_text(bot_template % "MOVE_R", encoding="utf-8")

        match = rt.run_match_simulation(
            match_id="LOCK_VERIFY",
            hero=sub,
            demon_id="official",
            demon_name="Official",
            demon_taunt="lock",
            demon_spent_gold=0,
            demon_vault_gold=3000,
            demon_quotes={},
            map_grid=empty_grid(),
            is_featured=True,
            check_spawn=False,
        )
        assert match["hero_submission_sha256"] == locked_sha
        assert match["frames"][1]["action"] == "WAIT"
        assert all(f["action"] == "WAIT" for f in match["frames"][1:])

        dec = engine.validate_and_decode_dungeon(empty_grid(), check_spawn=False)
        sim = engine.DungeonSimulator(dec, mode="FULL")
        with sub.create_worker() as worker:
            assert worker.call("decide", 1.0, state=sim.get_observation()) == "WAIT"
            worker.respawn()
            assert worker.call("decide", 1.0, state=sim.get_observation()) == "WAIT"

        bad_raised = False
        try:
            with SubmissionProcess(bot_path, expected_sha256="0" * 64):
                pass
        except ValueError:
            bad_raised = True
        assert bad_raised, "Expected SubmissionProcess expected_sha256 mismatch to raise ValueError"
    print("[PASS] test_gpt_p0_2_in_memory_hash_lock")


def test_gpt_p0_4_schedule_and_11_unique_backups():
    import run_tournament_full as rt
    from tools.exam_watcher import RoomTracker

    backups = official_maps.get_all_backup_maps()
    assert len(backups) == 11
    backup_hashes = {b["grid_sha256"] for b in backups}
    assert len(backup_hashes) == 11
    officials = official_maps.get_all_official_maps()
    assert len({m["grid_sha256"] for m in (officials + backups)}) == 14

    minimal_bot = """
def build_dungeon():
    g = [["T_W" if (x in (0, 39) or y in (0, 25)) else "EMPTY" for x in range(40)] for y in range(26)]
    g[5][20] = "K1"; g[20][20] = "K2"; g[13][35] = "V"
    sol = ["MOVE_R"] * 18 + ["MOVE_U"] * 8 + ["MOVE_D"] * 15 + ["MOVE_U"] * 7 + ["MOVE_R"] * 15
    return {"taunt": "m", "grid": g, "author_solution": sol}

def decide_action(state, memory):
    return "WAIT"
"""
    t0 = 1_700_000_000.0

    def _seal_room(rdir: Path) -> None:
        rdir.mkdir(parents=True, exist_ok=True)
        (rdir / "submission.py").write_text(minimal_bot, encoding="utf-8")
        tr = RoomTracker(rdir, cutoff_seconds=2400.0)
        tr.poll_once(now=t0)
        tr.start_exam(now=t0)
        tr.poll_once(now=t0 + 2401.0)

    with tempfile.TemporaryDirectory() as td:
        rooms_dir = Path(td) / "exam_rooms"
        out_dir = Path(td) / "replays"
        seats = list(rt.EXPECTED_SEAT_IDS)
        assert len(seats) == 11

        # Authentic RoomTracker sealed snapshots for the first 10 seats
        for idx, sid in enumerate(seats[:-1]):
            _seal_room(rooms_dir / f"P2_{idx + 1:02d}_{sid}_test")

        # 1. Missing 11th seat -> must pass seats 1..10 and fail specifically on missing seat 11
        missing_seat_msg = ""
        try:
            r1 = rt.TournamentRunnerFull(rooms_dir, out_dir, from_exam_rooms=True, require_cutoff=True)
            r1.scan_and_load_models()
        except RuntimeError as exc:
            missing_seat_msg = str(exc)
        assert seats[-1] in missing_seat_msg and "exam room missing" in missing_seat_msg, missing_seat_msg

        # 2. Add 11th seat with submission.py ONLY (no cutoff) -> must fail specifically on missing cutoff for seat 11
        last_dir = rooms_dir / f"P2_11_{seats[-1]}_test"
        last_dir.mkdir(parents=True, exist_ok=True)
        (last_dir / "submission.py").write_text(minimal_bot, encoding="utf-8")
        missing_cutoff_msg = ""
        try:
            r2 = rt.TournamentRunnerFull(rooms_dir, out_dir, from_exam_rooms=True, require_cutoff=True)
            r2.scan_and_load_models()
        except RuntimeError as exc:
            missing_cutoff_msg = str(exc)
        assert seats[-1] in missing_cutoff_msg and "Missing mandatory 40:00 cutoff snapshot" in missing_cutoff_msg, (
            missing_cutoff_msg
        )

        # 3. Seal 11th seat genuinely, then test tamper + duplicate cutoff rejection
        _seal_room(last_dir)
        cut_files = list((last_dir / "history").glob("CUTOFF_*.py"))
        assert len(cut_files) == 1
        orig_bytes = cut_files[0].read_bytes()

        cut_files[0].write_bytes(orig_bytes + b"\n# tampered post-cutoff\n")
        tamper_msg = ""
        try:
            r3 = rt.TournamentRunnerFull(rooms_dir, out_dir, from_exam_rooms=True, require_cutoff=True)
            r3.scan_and_load_models()
        except RuntimeError as exc:
            tamper_msg = str(exc)
        finally:
            cut_files[0].write_bytes(orig_bytes)
        assert seats[-1] in tamper_msg and "Cutoff SHA-256 mismatch" in tamper_msg, tamper_msg

        extra_cut = last_dir / "history" / "CUTOFF_40m00s_ffffffff.py"
        extra_cut.write_bytes(orig_bytes)
        dup_msg = ""
        try:
            r4 = rt.TournamentRunnerFull(rooms_dir, out_dir, from_exam_rooms=True, require_cutoff=True)
            r4.scan_and_load_models()
        except RuntimeError as exc:
            dup_msg = str(exc)
        finally:
            extra_cut.unlink(missing_ok=True)
        assert seats[-1] in dup_msg and "Multiple cutoff snapshots" in dup_msg, dup_msg

        # 4. Clean 11-seat sealed exam rooms -> require_cutoff=True must succeed for all 11 seats
        runner = rt.TournamentRunnerFull(rooms_dir, out_dir, from_exam_rooms=True, require_cutoff=True)
        runner.scan_and_load_models()
        assert len(runner.models) == 11
        assert len(runner.backup_maps) == 11
    print("[PASS] test_gpt_p0_4_schedule_and_11_unique_backups")


def test_part1_freeze_manifest_integrity():
    manifest_path = PART2_DIR / "docs" / "part1_freeze_manifest.json"
    assert manifest_path.exists(), f"Missing freeze manifest: {manifest_path}"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files", [])
    assert manifest.get("count") == len(files) and len(files) >= 15
    part1_root = PART2_DIR.parent / "part1_fog_mode"
    verified_exact = 0
    for entry in files:
        raw_path = entry["path"].replace("\\", "/")
        rel = raw_path.split("<REPO_ROOT>/", 1)[-1] if "<REPO_ROOT>/" in raw_path else raw_path
        p = part1_root / rel
        if rel == "replays/tournament_bundle.json" and not p.exists():
            gz = part1_root / "replays" / "tournament_bundle.json.gz"
            assert gz.exists(), f"Missing frozen Part-1 replay archive: {gz}"
            continue
        assert p.exists(), f"Missing frozen Part-1 file: {p}"
        # Strict byte-exact SHA-256 verification on core engine & all 11 official submissions
        if rel == "engine.py" or rel.startswith("submissions/"):
            actual = hashlib.sha256(p.read_bytes()).hexdigest()
            assert actual == entry["sha256"], f"Part-1 freeze hash mismatch for {p}: {actual} != {entry['sha256']}"
            verified_exact += 1
    assert verified_exact == 12, f"Expected 12 byte-exact Part-1 files (engine + 11 submissions), got {verified_exact}"
    print(f"[PASS] test_part1_freeze_manifest_integrity ({verified_exact} core files SHA-256 exact, {len(files)} entries verified)")


if __name__ == "__main__":
    test_plate_and_pgate_rules()
    test_dual_period_lasers_and_lcm12()
    test_oneway_9_callsites_matrix()
    test_gpt_counterexamples_admissibility_and_scoring()
    test_sandbox_respawn_and_turn1_budget()
    test_gpt_p0_1_bomb_spawn_admissibility()
    test_gpt_p0_2_in_memory_hash_lock()
    test_gpt_p0_4_schedule_and_11_unique_backups()
    test_part1_freeze_manifest_integrity()
    print("\nALL HALF-2 v2.2 ENGINE & SANDBOX TESTS PASSED!")
