# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\glm_max")
import time
import test_hero as TH
import submission as S

# L7: 全高深坑墙 —— 必须用 JUMP 越过（p1=已知深坑, p2=已知空地）
P7 = {}
for y in range(1, 25):
    P7[(16, y)] = "PIT"
g7 = TH.FogGame(TH.make_map(P7, k1=(14, 13), k2=(24, 13), v=(30, 13)))
r = g7.run()
used_jump = any(a.startswith("JUMP") for a in g7.actions)
print("L7 mandatory jump:", r, "used_jump =", used_jump, "jumps left =", g7.j.jumps)

# L8: 冰道滑行 —— 安全滑入目标方向
P8 = {}
for x in range(8, 20):
    P8[(x, 13)] = "ICE"
g8 = TH.FogGame(TH.make_map(P8, k1=(6, 13), k2=(24, 13), v=(30, 13)))
print("L8 ice slide:", g8.run())

# import timing
t0 = time.time()
import importlib
importlib.reload(S)
print(f"import+reload time: {time.time()-t0:.3f}s (limit 1.5s)")

t0 = time.time()
d = S.build_dungeon()
print(f"build_dungeon time: {time.time()-t0:.3f}s (limit 2.0s)")
