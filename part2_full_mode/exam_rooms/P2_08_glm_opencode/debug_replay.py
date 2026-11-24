# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S
import test_full as T

d = S.build_dungeon()
w = S.decode_state(T._mk_state(d, turn=1))
marks = {10: "推箱A?", 43: "推箱B?", 85: "进湾", 86: "跳K1", 87: "弹簧",
         107: "放弹", 113: "取K2", 137: "推箱D", 139: "跳桥", 145: "三板齐",
         151: "突进", 155: "通关"}
for i, a in enumerate(d["author_solution"], 1):
    w = S.step_world(w, a)
    note = marks.get(i, "")
    if i <= 12 or note or i % 15 == 0 or w.status != "ALIVE":
        print(f"t={i:3d} {a:8s} pos=({w.hx},{w.hy}) hp={w.hp} k=({w.k1},{w.k2}) "
              f"j={w.jumps} b={w.bombs} st={w.status} {note}")
    if w.status != "ALIVE":
        break
