"""
End-to-End Judge Verification & Grandmaster Torture Suite for Carbon's v2.2 submission.py
"""

import ast
import collections
import heapq
import json
import random
import time

from v22_judge import (
    GRID_WIDTH, GRID_HEIGHT, MAX_BUDGET, MAX_TURNS, MAX_AUTHOR_STEPS,
    VALID_ACTIONS, DIRECTIONS, ONEWAY_DIR,
    validate_and_decode_grid_v22, DungeonEngineV22, make_blank_grid_v22,
)

FORBIDDEN_MODULES = {
    "os", "sys", "io", "pathlib", "shutil", "socket", "urllib", "http", "requests",
    "subprocess", "multiprocessing", "threading", "inspect", "ctypes", "gc", "types",
    "pickle", "builtins",
}
FORBIDDEN_NAMES = {
    "open", "eval", "exec", "compile", "getattr", "setattr", "delattr", "__import__",
}


def audit_ast(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in FORBIDDEN_MODULES, f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                assert node.module.split(".")[0] not in FORBIDDEN_MODULES, f"Forbidden import: {node.module}"
        elif isinstance(node, ast.Name):
            assert node.id not in FORBIDDEN_NAMES, f"Forbidden name: {node.id}"
            assert not (node.id.startswith("__") and node.id.endswith("__")), f"Dunder name: {node.id}"
        elif isinstance(node, ast.Attribute):
            assert not (node.attr.startswith("__") and node.attr.endswith("__")), f"Dunder attr: {node.attr}"
    print("[PASS] AST Security Audit: 0 forbidden imports, 0 getattr/setattr/eval, 0 dunder attributes!")


def build_extra_v22_torture_maps():
    maps = []

    # TORTURE 1: 6 Boxes + 4 Plates + Coupled Switch-Opens-Box-Path + Oneway + 12-Beat Laser!
    g1 = make_blank_grid_v22()
    for y in range(11, 16):
        for x in range(32, 38):
            g1[y][x] = "T_W"
    g1[13][32] = "ONEWAY_R"
    g1[13][33] = "EMPTY"
    g1[13][34] = "P_GATE"
    g1[13][35] = "V"
    g1[8][33] = "LASER_D"
    g1[18][33] = "LASER2_U"
    g1[11][33] = "PIT"
    g1[15][33] = "PIT"
    # 4 Plates, 1 gated behind R_GATE requiring SWITCH first!
    g1[8][8] = "PLATE"
    g1[8][6] = "BOX"
    g1[10][8] = "PLATE"
    g1[10][6] = "BOX"
    g1[16][8] = "PLATE"
    g1[16][6] = "BOX"
    # 4th plate behind R_GATE(9, 20)
    g1[19][9] = "T_W"
    g1[21][9] = "T_W"
    g1[19][10] = "T_W"
    g1[21][10] = "T_W"
    g1[20][11] = "T_W"
    g1[20][9] = "R_GATE"
    g1[20][10] = "PLATE"
    g1[20][7] = "BOX"
    g1[22][5] = "BOX"
    g1[22][7] = "BOX"
    g1[3][10] = "SWITCH"
    maps.append(("V22_TORTURE_6BOX_4PLATE", g1))

    # TORTURE 2: 2-Wide Pit Bridge (2 consecutive boxes into 2 pits, GV22_08!) + P_GATE!
    g2 = make_blank_grid_v22()
    for y in range(11, 16):
        for x in range(28, 38):
            g2[y][x] = "T_W"
    g2[13][25] = "BOX"
    g2[13][27] = "BOX"
    g2[13][28] = "EMPTY"
    g2[13][29] = "EMPTY"
    g2[13][30] = "PIT"
    g2[13][31] = "PIT"
    g2[13][32] = "PIT"   # 3-wide PIT! 2 boxes fill 2 pits + 1 JUMP crosses the 3rd!
    g2[13][33] = "EMPTY"
    g2[13][34] = "P_GATE"
    g2[13][35] = "V"
    g2[8][8] = "PLATE"
    g2[8][6] = "BOX"
    maps.append(("V22_TORTURE_3WIDE_PIT", g2))

    # TORTURE 3: Mimic vs Heal Full-Clue Discrimination + Mandatory Chip Damage + Heal Recovery!
    g3 = make_blank_grid_v22()
    for y in range(11, 16):
        for x in range(24, 38):
            g3[y][x] = "T_W"
    for x in range(24, 36):
        g3[13][x] = "EMPTY"
    # 4 MIMICs + 2 HEALs inside 1-wide corridor (3 throws clear 3 mimics, 4th tanked + healed back to 85 HP!)
    for mx in (25, 27, 29, 31):
        g3[13][mx] = "MIMIC"
        g3[12][mx] = "EMPTY"
    g3[13][33] = "HEAL"
    g3[13][35] = "V"
    maps.append(("V22_TORTURE_MIMIC_HEAL", g3))

    return maps


def run_match_v22(decide_fn, grid, name: str, wipe_memory_at_turn: int = -1):
    ok, msg, dec = validate_and_decode_grid_v22(grid, check_spawn_4turn=False)
    assert ok, f"{name}: {msg}"
    eng = DungeonEngineV22(dec)
    memory = {}
    random.seed(20261115)

    t1_ms = 0.0
    max_later_ms = 0.0
    error_streak = 0

    while eng.status == "ALIVE":
        obs = eng.get_observation()
        turn = obs["turn"]
        if turn == wipe_memory_at_turn:
            memory.clear()

        t0 = time.monotonic()
        act = decide_fn(obs, memory)
        dt_ms = (time.monotonic() - t0) * 1000.0

        limit_ms = 2000.0 if turn == 1 else 500.0
        if turn == 1:
            t1_ms = dt_ms
        else:
            max_later_ms = max(max_later_ms, dt_ms)

        if dt_ms > limit_ms or act not in VALID_ACTIONS:
            print(f"  [WARN] {name} turn {turn} interface error: act={act}, dt={dt_ms:.1f}ms")
            act = "WAIT"
            error_streak += 1
            memory.clear()
            if error_streak >= 3:
                eng.status = "DQ"
                break
        else:
            error_streak = 0

        eng.step(act)

    h_sc, d_sc = eng.compute_scores()
    print(
        f"[{name:24s}] {eng.status:7s} | T={eng.turn:3d} | HP={eng.hp:3d} | "
        f"Hero={h_sc:6.1f} | Demon={d_sc:6.1f} | T1={t1_ms:6.1f}ms | MaxT2+={max_later_ms:5.1f}ms"
    )
    return eng, h_sc, d_sc


def opponent_standard_macro_astar(state, memory):
    """
    Simulated Strong Opponent in FULL mode:
    Standard Macro-A* with box-to-plate distance heuristic (WITHOUT Carbon's Bipartite Box-Sink Hall's Marriage Pruner!).
    """
    import submission as sub
    if "plan" not in memory:
        eng = sub._decode_state_to_eng(state)
        # Temporarily disable bipartite pruner to simulate standard heuristic A* opponent!
        orig_fn = sub._can_ever_win_relaxed
        sub._can_ever_win_relaxed = lambda e, c: True
        try:
            _, plan = sub._solve_full_dungeon(eng, 1.60)
        finally:
            sub._can_ever_win_relaxed = orig_fn
        memory["plan"] = plan if plan else ["WAIT"] * 240
        memory["i"] = 0
    idx = memory["i"]
    memory["i"] = idx + 1
    return memory["plan"][idx] if idx < len(memory["plan"]) else "WAIT"


if __name__ == "__main__":
    audit_ast("submission.py")

    t_imp = time.monotonic()
    import submission
    print(f"[PASS] import submission in {(time.monotonic() - t_imp)*1000:.1f} ms")

    tb = time.monotonic()
    d_out = submission.build_dungeon()
    tb_ms = (time.monotonic() - tb) * 1000.0
    assert len(d_out["taunt"]) <= 40
    assert 1 <= len(d_out["author_solution"]) <= MAX_AUTHOR_STEPS

    ok, msg, dec = validate_and_decode_grid_v22(d_out["grid"], check_spawn_4turn=True)
    assert ok, f"build_dungeon validation failed: {msg}"

    eng_auth = DungeonEngineV22(dec)
    for idx, act in enumerate(d_out["author_solution"]):
        eng_auth.step(act)
        if idx < len(d_out["author_solution"]) - 1:
            assert eng_auth.status == "ALIVE", f"Early end at step {idx+1}: {eng_auth.status}"
        else:
            assert eng_auth.status == "CLEARED", f"Final step status: {eng_auth.status}"
    print(
        f"[PASS] build_dungeon() verified in {tb_ms:.2f} ms | Spent={dec['spent_gold']}G | "
        f"AuthorSteps={eng_auth.turn}/{MAX_AUTHOR_STEPS} | FinalHP={eng_auth.hp} | 4-Turn Spawn OK!"
    )

    print("\n=== OPPONENT STANDARD MACRO-A* VS CARBON v2.2 DEMON DUNGEON ===")
    run_match_v22(opponent_standard_macro_astar, d_out["grid"], "OPP_Standard_Macro_AStar")

    print("\n=== CARBON v2.2 HERO FULL SUITE (21 MAPS + MEMORY-WIPE TEST) ===")
    with open("v22_sparring_benchmarks.json", "r", encoding="utf-8") as f:
        sp = json.load(f)["dungeons"]
    with open("part1_dungeons_benchmark.json", "r", encoding="utf-8") as f:
        p1 = json.load(f)["dungeons"]

    suite = [
        ("V22_BENCH_WEAK", sp["BENCH_WEAK"]["grid"]),
        ("V22_BENCH_STRONG", sp["BENCH_STRONG"]["grid"]),
        ("V22_CARBON_OWN_DEMON", d_out["grid"]),
    ] + build_extra_v22_torture_maps() + [(f"P1_{k}", v["grid"]) for k, v in p1.items()]

    cleared = 0
    scores = []
    for mname, mgrid in suite:
        eng_r, hs, _ = run_match_v22(submission.decide_action, mgrid, mname)
        scores.append(hs)
        if eng_r.status == "CLEARED":
            cleared += 1

    print("\n=== MID-GAME MEMORY RESET RECOVERY TEST (Turn 25 wipe on BENCH_STRONG) ===")
    eng_w, hs_w, _ = run_match_v22(submission.decide_action, sp["BENCH_STRONG"]["grid"], "RECOVERY_BENCH_STRONG", wipe_memory_at_turn=25)
    assert eng_w.status == "CLEARED", "Mid-game recovery failed!"

    print(f"\nFINAL VERDICT: CLEARED {cleared} / {len(suite)} MAPS! Mean Hero Score = {sum(scores)/len(scores):.2f}")
