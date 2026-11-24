# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\glm_max")
import test_hero as TH
import submission as S

S._DEBUG = True

P7 = {}
for y in range(1, 25):
    P7[(16, y)] = "PIT"
g7 = TH.FogGame(TH.make_map(P7, k1=(14, 13), k2=(24, 13), v=(30, 13)))
while g7.turn < 30 and g7.j.status == "ALIVE":
    g7.turn += 1
    st = g7.build_state()
    act = S.decide_action(st, g7.memory)
    g7.j.step(g7.turn, act)
    g7.actions.append(act)
    print(f"t={g7.turn} {act} pos=({g7.j.hx},{g7.j.hy}) k=({g7.j.k1},{g7.j.k2})")
