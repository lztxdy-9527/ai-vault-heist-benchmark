# -*- coding: utf-8 -*-
import sys, json, time
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S
import test_full as T

with open(r"part2_full_mode/exam_rooms\P2_08_glm_opencode\v22_sparring_benchmarks.json", encoding="utf-8") as f:
    bench = json.load(f)
dd = {"taunt": "", "grid": bench["dungeons"]["BENCH_STRONG"]["grid"], "author_solution": ["WAIT"]}
st = T._mk_state(dd, turn=1)
w = S.decode_state(st)
memory = {}
acts = []
for i in range(1, 80):
    st["turn"] = i
    st["hero"].update({"x": w.hx, "y": w.hy, "hp": w.hp, "keys": [w.k1, w.k2],
                       "jumps": w.jumps, "bombs": w.bombs})
    st["gates_flipped"] = w.gates
    st["bombs"] = [{"x": b[0], "y": b[1], "timer": b[2]} for b in w.bl]
    st["terrain"] = [[(w.t(x, y) if w.t(x, y) not in ("HEAL", "MIMIC") else "CHEST")
                      for x in range(40)] for y in range(26)]
    st["occupant"] = [[w.occ.get((x, y)) for x in range(40)] for y in range(26)]
    a = S.decide_action(st, memory)
    acts.append((i, a, (w.hx, w.hy)))
    w = S.step_world(w, a)

print("last 15:", acts[-15:])
print("plates:", {p: w.occ.get(p) for p in w.plates}, "active:", w.plates_active())

# 卡点诊断：从 (8,17) 逐动作模拟
st["hero"].update({"x": w.hx, "y": w.hy, "hp": w.hp, "keys": [w.k1, w.k2],
                   "jumps": w.jumps, "bombs": w.bombs})
st["turn"] = 80
w2 = S.decode_state(st)
rays = S._ray_cells(w2) if w2.cannons else []
print("hero:", (w2.hx, w2.hy), "t=", w2.t(w2.hx, w2.hy))
print("actions:", S._actions(w2, rays))
for a in S._actions(w2, rays):
    nw = S.step_world(w2, a)
    print(f"  {a}: -> ({nw.hx},{nw.hy}) hp={nw.hp} st={nw.status}")
print("memory plan:", memory.get("plan"))
