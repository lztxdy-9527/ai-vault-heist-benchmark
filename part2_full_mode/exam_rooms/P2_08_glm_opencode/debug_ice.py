# -*- coding: utf-8 -*-
import sys, json
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S
import test_full as T

with open(r"part2_full_mode/exam_rooms\P2_08_glm_opencode\v22_sparring_benchmarks.json", encoding="utf-8") as f:
    bench = json.load(f)
dd = {"taunt": "", "grid": bench["dungeons"]["BENCH_STRONG"]["grid"], "author_solution": ["WAIT"]}

st = T._mk_state(dd, turn=70)
st["hero"]["x"], st["hero"]["y"] = 4, 17
st["occupant"][17][8] = "BOX" if False else None
st["occupant"][18][8] = "BOX"
st["occupant"][17][4] = None
w = S.decode_state(st)
print("terrain row 17:", [w.t(x, 17) for x in range(3, 10)])
print("occ:", {k: v for k, v in w.occ.items() if k[1] in (17, 18)})
w2 = S.step_world(w, "MOVE_R")
print("after MOVE_R from (4,17): hero =", (w2.hx, w2.hy))
print("plates:", {p: w2.occ.get(p) for p in w2.plates}, "active:", w2.plates_active())
