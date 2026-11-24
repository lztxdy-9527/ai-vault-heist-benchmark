# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\glm_max")
import test_hero as TH
import submission as S

P7 = {}
for y in range(1, 25):
    P7[(16, y)] = "PIT"
g7 = TH.FogGame(TH.make_map(P7, k1=(14, 13), k2=(24, 13), v=(30, 13)))

# 跑到拿到 K1 为止
while g7.turn < 100 and not g7.j.k1:
    g7.turn += 1
    st = g7.build_state()
    act = S.decide_action(st, g7.memory)
    g7.j.step(g7.turn, act)
    g7.actions.append(act)
print("after K1: pos =", (g7.j.hx, g7.j.hy), "turn =", g7.turn)

# 手动构造下一回合 state 检查决策
st = g7.build_state()
act = S.decide_action(st, g7.memory)
print("next action:", act)

# 检查 memory 状态
mt = g7.memory["terr"]
print("mt[13][14..18] =", [mt[13][x] for x in range(14, 19)])
print("hero keys:", st["hero"]["keys"], "jumps:", st["hero"]["jumps"])
print("targets:", st["targets"])
