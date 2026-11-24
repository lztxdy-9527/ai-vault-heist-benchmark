"""Benchmark hero_v22 across v2.2 sparring (2), adversarial stress (8 + restart), and Part 1 (14) = 25 FULL tests."""

import json
import os
import sys
import time

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)

import local_judge_v22 as lj
import stress_v22 as sv
import hero_v22


def run_hero_match(name: str, dec: dict, fn, restart_at: int | None = None):
    eng = lj.GameEngineV22(dec)
    mem = {}
    t1_dt = 0.0
    max_t2_dt = 0.0
    for t in range(1, lj.MAX_TURNS + 1):
        if restart_at is not None and t == restart_at:
            mem = {}  # simulate worker process restart cleanly!
        st = eng.get_state(t, mode="FULL")
        t0 = time.perf_counter()
        act = fn(st, mem)
        dt = time.perf_counter() - t0
        if t == 1:
            t1_dt = dt
        elif dt > max_t2_dt:
            max_t2_dt = dt
        assert act in lj.VALID_ACTIONS, f"Invalid action {act} on {name}"
        eng.step(act)
        if eng.status != "ALIVE":
            break
    hs, ds = eng.compute_scores()
    print(f"  [{name:32s}] {eng.status:8s} t={eng.turn:3d} hp={eng.hp:3d} k={eng.stage_k}/2 hero={hs:6.1f} t1={t1_dt*1000:6.1f}ms max_t2={max_t2_dt*1000:6.2f}ms")
    return hs, ds, eng


def main():
    with open(os.path.join(DIR, "v22_sparring_benchmarks.json"), "r", encoding="utf-8") as f:
        v22 = json.load(f)["dungeons"]
    with open(os.path.join(DIR, "part1_dungeons_benchmark.json"), "r", encoding="utf-8") as f:
        p1 = json.load(f)["dungeons"]

    print("=== 1. v2.2 Sparring Benchmarks (FULL mode) ===")
    v22_res = []
    for k in ("BENCH_WEAK", "BENCH_STRONG"):
        dec = lj.decode_grid_only(v22[k]["grid"])
        hs, _, e = run_hero_match(k, dec, hero_v22.decide_action)
        v22_res.append((k, e.status, e.turn, e.hp, hs))

    print("\n=== 2. Adversarial Stress Suite v2.2 (S01..S08 + S09 restart) ===")
    stress_maps = sv.build_stress_maps()
    st_scores = []
    for name, g in stress_maps:
        dec = lj.decode_grid_only(g)
        hs, _, _ = run_hero_match(name, dec, hero_v22.decide_action)
        st_scores.append(hs)
    # Test mid-game process restart (memory={} at turn 8!) on BENCH_STRONG
    dec_bs = lj.decode_grid_only(v22["BENCH_STRONG"]["grid"])
    run_hero_match("S09_RESTART_AT_T8_BENCH_STRONG", dec_bs, hero_v22.decide_action, restart_at=8)

    print("\n=== 3. Part 1 Full Benchmark (14 maps) ===")
    p1_scores = []
    for mid, m in sorted(p1.items()):
        dec = lj.decode_grid_only(m["grid"])
        hs, _, _ = run_hero_match(str(mid), dec, hero_v22.decide_action)
        p1_scores.append(hs)
    print(f"\nSUMMARY: Part1 Avg={sum(p1_scores)/len(p1_scores):.2f} | Stress Avg={sum(st_scores)/len(st_scores):.2f} | BENCH_WEAK={v22_res[0][4]:.1f} ({v22_res[0][2]}t) | BENCH_STRONG={v22_res[1][4]:.1f} ({v22_res[1][2]}t)")


if __name__ == "__main__":
    main()
