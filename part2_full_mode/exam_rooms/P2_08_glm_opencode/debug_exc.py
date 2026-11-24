# -*- coding: utf-8 -*-
import sys, json, traceback
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S
import test_full as T

with open(r"part2_full_mode/exam_rooms\P2_08_glm_opencode\v22_sparring_benchmarks.json", encoding="utf-8") as f:
    bench = json.load(f)
dd = {"taunt": "", "grid": bench["dungeons"]["BENCH_STRONG"]["grid"], "author_solution": ["WAIT"]}
st = T._mk_state(dd, turn=1)
w = S.decode_state(st)
memory = {}
# 重放到卡点附近（t75）
for i in range(1, 76):
    st["turn"] = i
    st["hero"].update({"x": w.hx, "y": w.hy, "hp": w.hp, "keys": [w.k1, w.k2],
                       "jumps": w.jumps, "bombs": w.bombs})
    st["gates_flipped"] = w.gates
    st["bombs"] = [{"x": b[0], "y": b[1], "timer": b[2]} for b in w.bl]
    st["terrain"] = [[(w.t(x, y) if w.t(x, y) not in ("HEAL", "MIMIC") else "CHEST")
                      for x in range(40)] for y in range(26)]
    st["occupant"] = [[w.occ.get((x, y)) for x in range(40)] for y in range(26)]
    a = S.decide_action(st, memory)
    w = S.step_world(w, a)

st["turn"] = 76
st["hero"].update({"x": w.hx, "y": w.hy, "hp": w.hp, "keys": [w.k1, w.k2],
                   "jumps": w.jumps, "bombs": w.bombs})
st["terrain"] = [[(w.t(x, y) if w.t(x, y) not in ("HEAL", "MIMIC") else "CHEST")
                  for x in range(40)] for y in range(26)]
st["occupant"] = [[w.occ.get((x, y)) for x in range(40)] for y in range(26)]
print("state at t76: hero:", (w.hx, w.hy), "plates:", {p: w.occ.get(p) for p in w.plates})
try:
    a = S._decide(st, memory)
    print("decision:", a)
except Exception:
    traceback.print_exc()
