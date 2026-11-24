# -*- coding: utf-8 -*-
"""
Generates & verifies `golden_vectors_v22.json` directly from `engine_full.py`
for Half-2 v2.2 contestants.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PART2_DIR = HERE.parent
if str(PART2_DIR) not in sys.path:
    sys.path.insert(0, str(PART2_DIR))

import engine_full as engine


def _base_grid():
    g = [["EMPTY"] * engine.GRID_W for _ in range(engine.GRID_H)]
    for y in range(engine.GRID_H):
        for x in range(engine.GRID_W):
            if x in (0, engine.GRID_W - 1) or y in (0, engine.GRID_H - 1):
                g[y][x] = "T_W"
    g[5][20] = "K1"
    g[20][20] = "K2"
    g[13][35] = "V"
    return g


def build_and_verify_vectors():
    vectors = []

    # GV22_01: Budget + BOX-only PLATE + P_GATE validation
    g1 = _base_grid()
    g1[8][8] = "PLATE"
    g1[8][6] = "BOX"
    g1[13][34] = "P_GATE"
    g1[2][25] = "LASER2_D"
    g1[13][10] = "ONEWAY_R"
    dec1 = engine.validate_and_decode_dungeon(g1)
    assert dec1["valid"] and dec1["spent_gold"] == 45 + 30 + 30 + 90 + 30
    vectors.append({
        "id": "GV22_01_V22_BUDGET_AND_PLATE_PGATE_SCHEMA",
        "category": "budget_and_validation",
        "description": "验证 v2.2 单价总计 (PLATE 45G + BOX 30G + P_GATE 30G + LASER2_D 90G + ONEWAY_R 30G = 225G)，且 P_GATE>0 时满足 1<=PLATE<=BOX。",
        "placed_inner_tiles": [
            {"x": 20, "y": 5, "tile": "K1"},
            {"x": 20, "y": 20, "tile": "K2"},
            {"x": 35, "y": 13, "tile": "V"},
            {"x": 8, "y": 8, "tile": "PLATE"},
            {"x": 6, "y": 8, "tile": "BOX"},
            {"x": 34, "y": 13, "tile": "P_GATE"},
            {"x": 25, "y": 2, "tile": "LASER2_D"},
            {"x": 10, "y": 13, "tile": "ONEWAY_R"},
        ],
        "expected": {
            "valid": True,
            "spent_gold": dec1["spent_gold"],
            "vault_gold": dec1["vault_gold"],
            "initial_plates_active": False,
        },
    })

    # GV22_02: PLATE BOX-only vs Hero non-trigger
    g2 = _base_grid()
    g2[13][5] = "PLATE"
    g2[13][7] = "BOX"
    g2[13][34] = "P_GATE"
    sim2 = engine.DungeonSimulator(engine.validate_and_decode_dungeon(g2), mode="FULL")
    sim2.hx, sim2.hy = 4, 13
    s_hero = sim2.step("MOVE_R")  # Hero steps onto PLATE(5,13)
    assert s_hero["hero_pos"] == [5, 13] and s_hero["plates_active"] is False
    sim2.hx, sim2.hy = 8, 13
    s_box = sim2.step("MOVE_L")  # Wait (8,13) MOVE_L pushes BOX(7,13)->(6,13); another MOVE_L -> (5,13)!
    s_box2 = sim2.step("MOVE_L")
    assert s_box2["plates_active"] is True and not sim2.is_high_wall(34, 13)
    vectors.append({
        "id": "GV22_02_PLATE_BOX_ONLY_TRIGGER",
        "category": "plate_and_pgate",
        "description": "勇者踏上 PLATE(5,13) 时 plates_active 仍为 False；唯有将 BOX 推上 PLATE(5,13) 后 plates_active 变为 True，P_GATE(34,13) 立即打开。",
        "initial": {"plate": [5, 13], "p_gate": [34, 13], "box": [7, 13]},
        "steps": [
            {"from": [4, 13], "action": "MOVE_R", "expected_plates_active": False, "expected_pgate_closed": True},
            {"from": [8, 13], "actions": ["MOVE_L", "MOVE_L"], "expected_plates_active": True, "expected_pgate_closed": False},
        ],
    })

    # GV22_03: Dual-frequency LASER2 (period 4) & LASER (period 3) LCM 12 collision
    g3 = _base_grid()
    g3[8][15] = "LASER_D"    # period 3
    g3[10][12] = "LASER2_R"  # period 4
    dec3 = engine.validate_and_decode_dungeon(g3)
    sim3 = engine.DungeonSimulator(dec3, mode="FULL")
    sim3.turn = 12
    sim3.hx, sim3.hy = 15, 10
    obs3 = sim3.get_observation()
    s3 = sim3.step("WAIT")
    assert s3["hero_hp"] == 0 and s3["status"] == "DEAD"
    vectors.append({
        "id": "GV22_03_LCM12_RED_AND_BLUE_LASER_INSTANT_KILL",
        "category": "dual_period_lasers",
        "description": "LASER_D(15,8)[period=3] 与 LASER2_R(12,10)[period=4] 的射线在 (15,10) 交汇。于 turn=12 时 get_observation() 返回双周期预警，WAIT 结算后红蓝齐射造成 50+50=100 伤秒杀。",
        "initial": {"turn": 12, "hero": [15, 10], "laser_d": [15, 8], "laser2_r": [12, 10]},
        "action": "WAIT",
        "expected": {
            "warning_periods_at_15_10": sorted(list({w["period"] for w in obs3["laser_warnings"] if w["x"] == 15 and w["y"] == 10})),
            "hero_hp_after": s3["hero_hp"],
            "status": s3["status"],
        },
    })

    # GV22_04: ONEWAY reverse push with CRACK preservation & MIRROR new_dir check
    g4 = _base_grid()
    g4[13][5] = "CRACK"
    g4[13][6] = "ONEWAY_L"
    g4[10][10] = "MIRROR_NE"
    g4[9][10] = "ONEWAY_R"  # opposed to MIRROR_NE's new_dir=U
    dec4 = engine.validate_and_decode_dungeon(g4)
    sim4a = engine.DungeonSimulator(dec4, mode="FULL")
    sim4a.occupant[13][6] = "BOX"
    sim4a.hx, sim4a.hy = 5, 13
    sim4a.step("MOVE_R")
    assert sim4a.occupant[13][6] == "BOX" and [sim4a.hx, sim4a.hy] == [5, 13] and sim4a.terrain[13][5] == "CRACK"

    sim4b = engine.DungeonSimulator(dec4, mode="FULL")
    sim4b.hx, sim4b.hy = 9, 10
    sim4b.step("MOVE_R")
    assert [sim4b.hx, sim4b.hy] == [10, 10]
    vectors.append({
        "id": "GV22_04_ONEWAY_REVERSE_PUSH_AND_MIRROR_NEWDIR",
        "category": "oneway_physics",
        "description": "(a) BOX 停在 ONEWAY_L(6,13) 上时，勇者站 CRACK(5,13) 执行逆向 MOVE_R 推箱整次被拒：BOX 未动且 CRACK 不坍塌；(b) MOVE_R 滑上 MIRROR_NE(10,10) 折转为 U 后检查 (10,9) ONEWAY_R 被阻，停在斜坡 (10,10)。",
        "expected": {
            "case_a_box_pos": [6, 13],
            "case_a_hero_pos": [5, 13],
            "case_a_crack_intact": True,
            "case_b_hero_pos": [10, 10],
        },
    })

    # GV22_05: JUMP across/onto ONEWAY + SPRING blocked by ONEWAY
    g5 = _base_grid()
    g5[10][10] = "SPRING_R"
    g5[10][12] = "ONEWAY_L"
    g5[14][6] = "ONEWAY_L"
    sim5 = engine.DungeonSimulator(engine.validate_and_decode_dungeon(g5), mode="FULL")
    sim5.hx, sim5.hy = 9, 10
    s5_spr = sim5.step("MOVE_R")
    sim5.hx, sim5.hy = 5, 14
    s5_jmp = sim5.step("JUMP_R")
    assert s5_spr["hero_pos"] == [11, 10]
    assert s5_jmp["hero_pos"] == [5, 14] and s5_jmp["jumps"] == 2
    vectors.append({
        "id": "GV22_05_SPRING_AND_JUMP_ONEWAY_INTERACTION",
        "category": "oneway_physics",
        "description": "SPRING_R(10,10) 向前第 2 格 (12,10) 为逆向 ONEWAY_L，勇者提前落停于 (11,10)；从 (5,14) 试图 JUMP_R 飞越逆向 ONEWAY_L(6,14) 失败停回 (5,14) 且消耗 1 次跳跃。",
        "expected": {
            "spring_land_pos": s5_spr["hero_pos"],
            "jump_failed_pos": s5_jmp["hero_pos"],
            "jumps_left": s5_jmp["jumps"],
        },
    })

    # GV22_06: THROW air pass vs ground slide stop on ONEWAY + LASER bypass
    g6 = _base_grid()
    g6[10][6] = "ONEWAY_L"
    g6[10][7] = "SWITCH"
    g6[15][11] = "ICE"
    g6[15][12] = "ONEWAY_L"
    g6[15][13] = "SWITCH"
    dec6 = engine.validate_and_decode_dungeon(g6)
    s6_air = engine.DungeonSimulator(dec6, mode="FULL")
    s6_air.hx, s6_air.hy = 5, 10
    r6_air = s6_air.step("THROW_R")
    s6_gnd = engine.DungeonSimulator(dec6, mode="FULL")
    s6_gnd.hx, s6_gnd.hy = 5, 15
    r6_gnd = s6_gnd.step("THROW_R")
    assert r6_air["gates_flipped"] is True and r6_gnd["gates_flipped"] is False
    vectors.append({
        "id": "GV22_06_THROW_AIR_PASS_VS_GROUND_STOP_ON_ONEWAY",
        "category": "oneway_throw",
        "description": "THROW_R 空中飞行自由穿透逆向 ONEWAY_L(6,10) 击中 SWITCH(7,10) 翻门；若飞石第 6 格落到 ICE(11,15) 转地面滑行，滑到 ONEWAY_L(12,15) 立即停下无法触发后方 SWITCH(13,15)。",
        "expected": {
            "air_throw_gates_flipped": r6_air["gates_flipped"],
            "ground_slide_gates_flipped": r6_gnd["gates_flipped"],
        },
    })

    # GV22_07: Phase C bomb destroys BOX on PLATE before Phase D LASER fires
    g7 = _base_grid()
    g7[10][10] = "PLATE"
    g7[10][12] = "P_GATE"
    g7[10][15] = "LASER_L"
    g7[10][8] = "BOX"
    sim7 = engine.DungeonSimulator(engine.validate_and_decode_dungeon(g7), mode="FULL")
    sim7.occupant[10][8] = None
    sim7.occupant[10][10] = "BOX"
    sim7.hx, sim7.hy = 7, 10
    sim7.bombs = [{"id": 1, "x": 10, "y": 10, "timer": 1}]
    sim7.turn = 3
    r7 = sim7.step("WAIT")
    assert r7["plates_active"] is False and r7["hero_hp"] == 100
    vectors.append({
        "id": "GV22_07_PHASE_C_BOX_DESTRUCTION_CLOSES_PGATE_BEFORE_PHASE_D",
        "category": "phase_c_d_plate",
        "description": "第 3 回合开始时 BOX 压在 PLATE(10,10) 上使 P_GATE(12,10) 开启；阶段 C 炸弹炸毁箱子后 P_GATE 在同回合阶段 D 激光快照前立即关闭，挡住 LASER_L(15,10) 救下勇者 (7,10)。",
        "expected": {
            "plates_active_after": r7["plates_active"],
            "hero_hp_after": r7["hero_hp"],
        },
    })

    # GV22_08: Scoring formula invariant & 200-step author cap
    g8 = _base_grid()
    g8[13][10] = "PIT"
    g8[13][11] = "PIT"
    g8[13][8] = "BOX"
    dec8 = engine.validate_and_decode_dungeon(g8)
    sim8 = engine.DungeonSimulator(dec8, mode="FULL")
    sim8.status = "CLEARED"
    sim8.trap_damage_total = 100.0
    sc8 = sim8.compute_scores(turns_elapsed=240)
    assert dec8["valid"] and sc8["demon_score"] == 320.0
    vectors.append({
        "id": "GV22_08_SCORING_ZERO_SUM_AND_2WIDE_PIT_BRIDGE",
        "category": "scoring_and_reachability",
        "description": "验证两格深渊+箱子搭桥地图合法通过；且失守局满 100 伤拖满 240 回合时魔王得分精确封顶 320.0000（与 TIMEOUT 底线零和衔接）。",
        "expected": {
            "valid": True,
            "cleared_max_demon_score": sc8["demon_score"],
            "max_author_steps": engine.MAX_AUTHOR_STEPS,
        },
    })

    out = {"schema_version": "2.2", "mode": "FULL", "vectors": vectors}
    out_path = HERE / "golden_vectors_v22.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path, len(vectors)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    p, n = build_and_verify_vectors()
    print(f"[OK] Generated & verified {n} v2.2 golden vectors -> {p}")
