# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\glm_max")
import test_hero as TH
import submission as S

# L1: 激光射线横穿 1 宽走廊 —— 勇者须按节拍(≡1进≡2出)穿越
P2 = {(20, 9): "LASER_D"}
for x in range(8, 26):
    if x != 20:
        P2[(x, 12)] = "W"
        P2[(x, 14)] = "W"
g = TH.FogGame(TH.make_map(P2, k1=(24, 13), k2=(25, 13), v=(28, 13)))
print("L1 laser corridor:", g.run(), "hp =", g.j.hp)

# L2: 真补给箱（无线索）—— 勇者应识别为安全可踩
P3 = {(10, 12): "HEAL"}
g2 = TH.FogGame(TH.make_map(P3, k1=(14, 13), k2=(22, 13), v=(30, 13)))
print("L2 heal chest:", g2.run(), "hp =", g2.j.hp)

# L3: 伪装宝箱怪（带骸骨线索）—— 勇者应绕开，HP 不掉 45
P4 = {(12, 13): "MIMIC"}
g3 = TH.FogGame(TH.make_map(P4, k1=(14, 13), k2=(22, 13), v=(30, 13)))
print("L3 mimic+clue:", g3.run(), "hp =", g3.j.hp)

# L4: 畸形 state 容错 —— 永不抛错，永远返回合法动作
bad_states = [
    {},
    {"turn": 5},
    {"turn": 5, "hero": {}},
    {"turn": "x", "hero": {"x": None}},
    {"turn": 3, "hero": {"x": 2, "y": 13, "hp": 50, "keys": [], "jumps": 0},
     "terrain": [], "visible_mask": [], "targets": None},
]
ok = all(S.decide_action(b, {}) in S.VALID_ACTIONS for b in bad_states)
print("L4 malformed robustness:", "PASS" if ok else "FAIL")

# L5: 跳跃寻路 —— 钥匙被 1 格深坑隔离，应使用 JUMP
P5 = {}
for y in range(9, 18):
    P5[(16, y)] = "PIT"
g5 = TH.FogGame(TH.make_map(P5, k1=(14, 13), k2=(24, 13), v=(30, 13)))
print("L5 jump over pit:", g5.run(), "jumps left =", g5.j.jumps)

# L6: 裂缝单行道 —— 走过后记忆坍塌，不得回头踩
P6 = {}
for x in range(6, 30):
    P6[(x, 12)] = "W"
    P6[(x, 14)] = "W"
for x in range(10, 24):
    if 12 < 0:
        pass
P6[(18, 13)] = "CRACK"
g6 = TH.FogGame(TH.make_map(P6, k1=(14, 13), k2=(22, 13), v=(30, 13)))
print("L6 crack one-way:", g6.run(), "hp =", g6.j.hp)
