# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S
import test_full as T

d = S.build_dungeon()
w = S.decode_state(T._mk_state(d, turn=1))
for i, a in enumerate(d["author_solution"], 1):
    w = S.step_world(w, a)
    if 26 <= i <= 46 or 59 <= i <= 62:
        occ_str = {k: v for k, v in w.occ.items() if k[1] == 21}
        print(f"t={i:3d} {a:8s} pos=({w.hx},{w.hy}) occ@21={occ_str}")
    if w.status != "ALIVE":
        break
