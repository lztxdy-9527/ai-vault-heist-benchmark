# -*- coding: utf-8 -*-
import sys, json
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S
import test_full as T

with open(r"part2_full_mode/exam_rooms\P2_08_glm_opencode\v22_sparring_benchmarks.json", encoding="utf-8") as f:
    bench = json.load(f)
dd = {"taunt": "", "grid": bench["dungeons"]["BENCH_STRONG"]["grid"], "author_solution": ["WAIT"]}

st = T._mk_state(dd, turn=69)
st["hero"]["x"], st["hero"]["y"] = 3, 17
# 箱在 (4,17)，其余箱：(3,9),(4,21),(23,13) 原位
st["occupant"][17][4] = "BOX"
w = S.decode_state(st)
w2 = S.step_world(w, "MOVE_R")
print("hero:", (w2.hx, w2.hy), "boxes:", sorted([p for p, v in w2.occ.items() if v == "BOX"]))
print("plates:", {p: w2.occ.get(p) for p in w2.plates})

# 若箱已在 (6,17)（被推过一次后再推）
st = T._mk_state(dd, turn=70)
st["hero"]["x"], st["hero"]["y"] = 4, 17
st["occupant"][17][6] = "BOX"
w = S.decode_state(st)
w2 = S.step_world(w, "MOVE_R")
print("case B hero:", (w2.hx, w2.hy), "boxes:", sorted([p for p, v in w2.occ.items() if v == "BOX"]))
