# -*- coding: utf-8 -*-
import sys, time
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S
import test_full as T

d = S.build_dungeon()
w = S.decode_state(T._mk_state(d, turn=1))

t0 = time.perf_counter()
N = 20000
for i in range(N):
    ww = S.step_world(w, "MOVE_R")
dt = time.perf_counter() - t0
print(f"step_world: {dt/N*1e6:.0f} us/call -> {N/dt:.0f} calls/s")

# A* 节点吞吐
t0 = time.perf_counter()
res, nodes = S._astar(w, 17, 5, time.monotonic() + 1.0, 30000)
dt = time.perf_counter() - t0
print(f"astar to K1: nodes={nodes} path={len(res) if res else None} 用时{dt:.2f}s -> {nodes/max(dt,1e-9):.0f} nodes/s")
