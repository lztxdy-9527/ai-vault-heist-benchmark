import json
import time
from sim_v22 import EngineV22
from solver_v22 import FastWorld

with open("part1_dungeons_benchmark.json", encoding="utf-8") as f:
    p1 = json.load(f)["dungeons"]
with open("v22_sparring_benchmarks.json", encoding="utf-8") as f:
    v22 = json.load(f)["dungeons"]

for name, grid in [
    ("argon", p1["argon"]["grid"]),
    ("sol", p1["sol"]["grid"]),
    ("glm", p1["glm"]["grid"]),
    ("hunyuan", p1["hunyuan"]["grid"]),
    ("carbon", p1["carbon"]["grid"]),
    ("BENCH_STRONG", v22["BENCH_STRONG"]["grid"]),
]:
    eng = EngineV22(grid)
    obs = eng.get_observation()
    fw = FastWorld()
    st0 = fw.build_from_state(obs)
    t0 = time.perf_counter()
    c, macros = fw.expand_macros(st0, t0 + 1.0)
    dt = (time.perf_counter() - t0) * 1000
    print(f"=== {name} | 1st expand: {dt:.1f}ms | cleared={c is not None} | n_macros={len(macros)} ===")
    for ns, acts, dmg in macros[:12]:
        print(f"  act_tail={acts[-3:]} len={len(acts)} -> pos=({ns[0]},{ns[1]}) hp={ns[2]} km={ns[3]} gf={ns[4]} j={ns[5]} b={ns[7]} boxes={ns[8]} h={fw.heuristic(ns)}")
