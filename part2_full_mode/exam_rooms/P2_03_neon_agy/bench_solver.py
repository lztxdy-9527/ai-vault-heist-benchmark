import json
import time
from sim_v22 import EngineV22
from solver_v22 import FastWorld

def run_bench():
    with open("part1_dungeons_benchmark.json", encoding="utf-8") as f:
        p1 = json.load(f)["dungeons"]
    with open("v22_sparring_benchmarks.json", encoding="utf-8") as f:
        v22 = json.load(f)["dungeons"]

    all_maps = []
    for k, v in p1.items():
        all_maps.append((f"P1:{k}", v["grid"]))
    for k, v in v22.items():
        all_maps.append((f"V22:{k}", v["grid"]))

    solved_cnt = 0
    for name, grid in all_maps:
        eng = EngineV22(grid)
        obs = eng.get_observation()
        fw = FastWorld()
        t0 = time.perf_counter()
        st0 = fw.build_from_state(obs)
        plan, partial, stats = fw.solve(st0, budget_sec=1.45)
        dt = time.perf_counter() - t0
        if plan is not None:
            # Verify plan on exact EngineV22!
            e2 = EngineV22(grid)
            for act in plan:
                e2.step(act)
                if e2.status != "RUNNING":
                    break
            ok = (e2.status == "CLEARED")
            if ok:
                solved_cnt += 1
            print(f"{name:18s} | {'PASS' if ok else 'FAIL(' + e2.status + ')'} | steps={len(plan):3d} | hp={e2.hp:3d} | nodes={stats['nodes']:4d} | time={dt*1000:6.1f}ms")
        else:
            print(f"{name:18s} | UNSOLVED | partial={len(partial):3d} | nodes={stats['nodes']:4d} | time={dt*1000:6.1f}ms")

    print(f"\nTOTAL SOLVED: {solved_cnt}/{len(all_maps)}")

if __name__ == "__main__":
    run_bench()
