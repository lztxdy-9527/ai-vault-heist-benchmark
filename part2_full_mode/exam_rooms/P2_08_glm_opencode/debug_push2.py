# -*- coding: utf-8 -*-
import sys, json
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S
import test_full as T

with open(r"part2_full_mode/exam_rooms\P2_08_glm_opencode\v22_sparring_benchmarks.json", encoding="utf-8") as f:
    bench = json.load(f)
dd = {"taunt": "", "grid": bench["dungeons"]["BENCH_STRONG"]["grid"], "author_solution": ["WAIT"]}

st = T._mk_state(dd, turn=1)
st["hero"]["x"], st["hero"]["y"] = 3, 21
w = S.decode_state(st)
w = S.step_world(w, "MOVE_R")
print("after push R: hero=({},{}), boxes={}".format(w.hx, w.hy,
      [p for p, v in w.occ.items() if v == "BOX"]))
# 走到 (8,20) 再推 D
for a in ["MOVE_U", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R"]:
    w = S.step_world(w, a)
print("walk to:", (w.hx, w.hy))
w = S.step_world(w, "MOVE_D")
print("after push D: hero=({},{}), box on (8,22)? {}".format(w.hx, w.hy, w.occ.get((8, 22))))
print("plates_active:", w.plates_active())
