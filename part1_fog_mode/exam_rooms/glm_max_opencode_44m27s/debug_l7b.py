# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\glm_max")
import test_hero as TH
import submission as S

P7 = {}
for y in range(1, 25):
    P7[(16, y)] = "PIT"
g7 = TH.FogGame(TH.make_map(P7, k1=(14, 13), k2=(24, 13), v=(30, 13)))
while g7.turn < 100 and not g7.j.k1:
    g7.turn += 1
    st = g7.build_state()
    act = S.decide_action(st, g7.memory)
    g7.j.step(g7.turn, act)
    g7.actions.append(act)

st = g7.build_state()
print("hero pos:", (g7.j.hx, g7.j.hy))
print("vis row13 x=13..19:", [st["visible_mask"][13][x] for x in range(13, 20)])
print("terr row13 x=13..19:", [st["terrain"][13][x] for x in range(13, 20)])
act = S.decide_action(st, g7.memory)
print("action:", act)
print("mem row13 x=13..19:", [g7.memory["terr"][13][x] for x in range(13, 20)])
