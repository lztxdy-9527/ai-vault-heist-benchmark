"""
End-to-End Verification Suite for submission.py (v2.2 FULL Mode).
Checks AST redlines, import/build timing, dungeon validation, worker-restart recovery,
and full turn-by-turn matches on all 14 Part-1 + 2 v2.2 Sparring + 5 Nightmare maps!
"""

import json
import time
from sim_v22 import EngineV22, check_ast_compliance, validate_dungeon
import stress_tests as st


def run_match(decide_fn, grid, wipe_turn=None):
    eng = EngineV22(grid)
    memory = {}
    t1_time = 0.0
    max_t2_time = 0.0
    while eng.status == "RUNNING":
        if wipe_turn is not None and eng.turn == wipe_turn:
            memory = {}
        obs = eng.get_observation()
        t0 = time.perf_counter()
        act = decide_fn(obs, memory)
        dt = time.perf_counter() - t0
        if eng.turn == 1:
            t1_time = dt
        else:
            if dt > max_t2_time:
                max_t2_time = dt
        eng.step(act)
    return eng.status, eng.turn, eng.hp, eng.keys, t1_time, max_t2_time


def main():
    print("=== 1. STATIC AST COMPLIANCE CHECK ===")
    ast_errs = check_ast_compliance("submission.py")
    print(f"AST errors: {len(ast_errs)}")
    for e in ast_errs:
        print("  ERROR:", e)
    assert not ast_errs, "AST compliance FAILED!"

    print("\n=== 2. IMPORT & BUILD_DUNGEON TIMING & VALIDATION ===")
    t0 = time.perf_counter()
    import submission
    t_imp = time.perf_counter() - t0
    t0 = time.perf_counter()
    dungeon = submission.build_dungeon()
    t_bld = time.perf_counter() - t0
    ok, errs, info = validate_dungeon(dungeon)
    print(f"import time: {t_imp*1000:.1f}ms (limit 1500ms)")
    print(f"build_dungeon time: {t_bld*1000:.1f}ms (limit 2000ms)")
    print(f"taunt: {dungeon['taunt']!r} (len={len(dungeon['taunt'])}/40)")
    print(f"spent_gold: {info['spent_gold']}G / 3000G (vault={info['vault_gold']}G)")
    print(f"author_steps: {info['author_steps']}/200 | safe_t1_coords: {len(info['safe_t1_coords'])}")
    print(f"validate_dungeon: ok={ok} errs={errs}")
    assert t_imp < 1.5 and t_bld < 2.0 and ok, "build_dungeon validation FAILED!"

    # Verify Turn-9 Instant Kill on straight-East naive hero
    eng_naive = EngineV22(dungeon["grid"])
    for _ in range(15):
        eng_naive.step("MOVE_R")
        if eng_naive.status != "RUNNING":
            break
    print(f"Naive straight-East walker vs our dungeon: status={eng_naive.status} turn={eng_naive.turn} hp={eng_naive.hp}")
    assert eng_naive.status == "DEAD" and eng_naive.turn == 9

    print("\n=== 3. END-TO-END HERO MATCHES (14 Part-1 + 2 v2.2 Sparring + 5 Nightmares) ===")
    with open("part1_dungeons_benchmark.json", encoding="utf-8") as f:
        p1 = json.load(f)["dungeons"]
    with open("v22_sparring_benchmarks.json", encoding="utf-8") as f:
        v22 = json.load(f)["dungeons"]

    maps = [(f"P1:{k}", v["grid"]) for k, v in p1.items()]
    maps += [(f"V22:{k}", v["grid"]) for k, v in v22.items()]
    maps += [
        ("NM1:ICE_STOPPER", st.build_nightmare_ice_stopper()),
        ("NM2:4PLATE_5BOX", st.build_nightmare_4plate_5box()),
        ("NM3:BOX_SHIELD", st.build_nightmare_box_shield()),
        ("NM4:DBL_SW_BANK", st.build_nightmare_double_switch_bankshot()),
        ("NM5:MIMIC_HEAL", st.build_nightmare_mandatory_mimic_heal()),
    ]

    cleared = 0
    max_t1_all = 0.0
    max_t2_all = 0.0
    for name, grid in maps:
        status, turns, hp, keys, t1, t2 = run_match(submission.decide_action, grid)
        max_t1_all = max(max_t1_all, t1)
        max_t2_all = max(max_t2_all, t2)
        if status == "CLEARED":
            cleared += 1
        t_flag = "OK" if (t1 < 1.9 and t2 < 0.48) else "TIMING_WARN!"
        print(f"{name:18s} | {status:7s} | T={turns:3d} | HP={hp:3d} | T1={t1*1000:6.1f}ms | maxT2={t2*1000:5.2f}ms | {t_flag}")

    print(f"\nHERO SCOREBOARD: {cleared}/{len(maps)} CLEARED | max T1={max_t1_all*1000:.1f}ms (<2000ms) | max T2+={max_t2_all*1000:.2f}ms (<500ms)")

    print("\n=== 4. WORKER-RESTART (EMPTY MEMORY MID-MATCH) RECOVERY TEST ===")
    status, turns, hp, keys, t1, t2 = run_match(submission.decide_action, v22["BENCH_STRONG"]["grid"], wipe_turn=45)
    print(f"BENCH_STRONG (memory wiped at T45): {status} | T={turns} | HP={hp} | T1={t1*1000:.1f}ms | maxT2={t2*1000:.1f}ms")
    assert status == "CLEARED" and t2 < 0.48, "Worker-restart recovery FAILED!"

    print("\n=== 5. SELF-DEFENSE CHECK (OUR OWN SOLVER vs OUR OWN DUNGEON) ===")
    status, turns, hp, keys, t1, t2 = run_match(submission.decide_action, dungeon["grid"])
    print(f"Our Hero vs Our Demon: {status} | T={turns} | HP={hp} | keys={keys} | T1={t1*1000:.1f}ms | maxT2={t2*1000:.1f}ms")
    assert t1 < 1.9 and t2 < 0.48, "Timing exceeded on ultra-hard map!"

    print("\nALL VERIFICATION CHECKS PASSED!")


if __name__ == "__main__":
    main()
