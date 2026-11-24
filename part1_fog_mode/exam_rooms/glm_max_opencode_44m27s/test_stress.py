# -*- coding: utf-8 -*-
"""随机压力测试：多张随机陷阱图上跑勇者，统计结果与耗时。"""
import sys
import time
import random
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\glm_max")
import test_hero as TH
import submission as S

random.seed(20261115)
TILES = ["PIT", "W", "CRACK", "ICE", "MIMIC", "HEAL", "T_W", "SPRING_R", "SWITCH", "R_GATE"]

results = {"CLEARED": 0, "ALIVE": 0, "DEAD": 0}
max_ms = 0.0
N = 12
for i in range(N):
    P = {}
    for _ in range(random.randint(20, 60)):
        x = random.randint(2, 37)
        y = random.randint(2, 23)
        if 1 <= x <= 3 and 12 <= y <= 14:
            continue  # 出生净空区
        P[(x, y)] = random.choice(TILES)
    K1, K2, V = (14, 5), (22, 20), (35, 13)
    P.pop(K1, None); P.pop(K2, None); P.pop(V, None)
    g = TH.FogGame(TH.make_map(P, k1=K1, k2=K2, v=V))
    t0 = time.time()
    st = g.run()
    dt = (time.time() - t0) / max(1, g.turn) * 1000
    max_ms = max(max_ms, dt)
    results[st] = results.get(st, 0) + 1

print("results:", results, f"max avg step: {max_ms:.1f}ms (limit 500ms)")
