import json, time
from sim_v22 import EngineV22
from solver_v22 import FastWorld

with open("part1_dungeons_benchmark.json", encoding="utf-8") as f:
    p1 = json.load(f)["dungeons"]
with open("v22_sparring_benchmarks.json", encoding="utf-8") as f:
    v22 = json.load(f)["dungeons"]

# 1. Inspect P1:sol
eng = EngineV22(p1["sol"]["grid"])
fw = FastWorld()
st0 = fw.build_from_state(eng.get_observation())
_, macros = fw.expand_macros(st0, time.perf_counter() + 2.0)
print("=== SOL macros from start ===")
for ns, acts, dmg in macros:
    print(f"  acts={acts} -> pos=({ns[0]},{ns[1]}) km={ns[3]} j={ns[5]} b={ns[7]} dm={ns[12]}")

# 2. Inspect P1:carbon
eng = EngineV22(p1["carbon"]["grid"])
fw = FastWorld()
st0 = fw.build_from_state(eng.get_observation())
t0 = time.perf_counter()
plan, partial, stats = fw.solve(st0, budget_sec=1.0)
print(f"=== CARBON partial len={len(partial)} ===")
e2 = EngineV22(p1["carbon"]["grid"])
for a in partial:
    e2.step(a)
print(f"  end pos=({e2.hx},{e2.hy}) hp={e2.hp} keys={e2.keys} gf={e2.gates_flipped} j={e2.jumps} b={e2.bombs_left}")

# 3. Inspect BENCH_STRONG partial
eng = EngineV22(v22["BENCH_STRONG"]["grid"])
fw = FastWorld()
st0 = fw.build_from_state(eng.get_observation())
plan, partial, stats = fw.solve(st0, budget_sec=1.0)
print(f"=== BENCH_STRONG partial len={len(partial)} nodes={stats['nodes']} ===")
e2 = EngineV22(v22["BENCH_STRONG"]["grid"])
for a in partial:
    e2.step(a)
boxes = [(x,y) for y in range(26) for x in range(40) if e2.occupant[y][x] == "BOX"]
print(f"  end pos=({e2.hx},{e2.hy}) hp={e2.hp} keys={e2.keys} gf={e2.gates_flipped} plates_act={e2.is_plates_active()} boxes={boxes} j={e2.jumps} th={e2.throws} b={e2.bombs_left}")
