# -*- coding: utf-8 -*-
import sys, json
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S
import test_full as T

with open(r"part2_full_mode/exam_rooms\P2_08_glm_opencode\v22_sparring_benchmarks.json", encoding="utf-8") as f:
    bench = json.load(f)
dd = {"taunt": "", "grid": bench["dungeons"]["BENCH_STRONG"]["grid"], "author_solution": ["WAIT"]}

st = T._mk_state(dd, turn=1)
st["hero"]["x"], st["hero"]["y"] = 3, 17
w = S.decode_state(st)
print("before: box@:", [p for p, v in w.occ.items() if v == "BOX"][:6])
w2 = S.step_world(w, "MOVE_R")
print("after MOVE_R: hero=({}, {}) box@:".format(w2.hx, w2.hy),
      [p for p, v in w2.occ.items() if v == "BOX"][:6])
print("plates_active:", w2.plates_active())
print("terr (8,17):", w2.t(8, 17), " (8,18):", w2.t(8, 18))

# 也试试从 (2,17) 走两步
st2 = T._mk_state(dd, turn=1)
w3 = S.decode_state(st2)
w3 = S.step_world(w3, "MOVE_R")   # (3,13)
w3 = S.step_world(w3, "MOVE_D")   # (3,14)
w3 = S.step_world(w3, "MOVE_D")   # (3,15)
w3 = S.step_world(w3, "MOVE_D")   # (3,16)
w3 = S.step_world(w3, "MOVE_D")   # (3,17)
print("\nwalk to (3,17): hero=({}, {})".format(w3.hx, w3.hy))
w4 = S.step_world(w3, "MOVE_R")
print("push: hero=({}, {}) boxes:".format(w4.hx, w4.hy),
      [p for p, v in w4.occ.items() if v == "BOX"])
print("plates_active:", w4.plates_active())
