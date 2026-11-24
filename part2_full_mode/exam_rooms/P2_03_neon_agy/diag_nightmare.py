from sim_v22 import EngineV22
from solver_v22 import FastWorld
import stress_tests as st

for name, fn in [
    ("N1_STOPPER", st.build_nightmare_ice_stopper),
    ("N2_4P5B", st.build_nightmare_4plate_5box),
    ("N3_SHIELD", st.build_nightmare_box_shield),
    ("N5_MIMIC", st.build_nightmare_mandatory_mimic_heal),
]:
    g = fn()
    e = EngineV22(g)
    fw = FastWorld()
    s0 = fw.build_from_state(e.get_observation())
    p, part, stats = fw.solve(s0, budget_sec=0.6)
    e2 = EngineV22(g)
    for a in part:
        e2.step(a)
    boxes = [(x, y) for y in range(26) for x in range(40) if e2.occupant[y][x] == "BOX"]
    print(f"{name:10s} | solved={p is not None} | nodes={stats['nodes']:3d} | part_len={len(part):3d} | end=({e2.hx},{e2.hy}) hp={e2.hp} keys={e2.keys} pact={e2.is_plates_active()} boxes={boxes}")
