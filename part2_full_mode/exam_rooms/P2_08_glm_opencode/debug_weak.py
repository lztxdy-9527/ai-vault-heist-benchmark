# -*- coding: utf-8 -*-
import sys, json, traceback
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S
import test_full as T

with open(r"part2_full_mode/exam_rooms\P2_08_glm_opencode\v22_sparring_benchmarks.json", encoding="utf-8") as f:
    bench = json.load(f)
dd = {"taunt": "", "grid": bench["dungeons"]["BENCH_WEAK"]["grid"], "author_solution": ["WAIT"]}
st = T._mk_state(dd, turn=1)
w = S.decode_state(st)
memory = {}
for i in range(1, 20):
    st["turn"] = i
    st["hero"].update({"x": w.hx, "y": w.hy, "hp": w.hp, "keys": [w.k1, w.k2],
                       "jumps": w.jumps, "bombs": w.bombs})
    st["gates_flipped"] = w.gates
    st["bombs"] = [{"x": b[0], "y": b[1], "timer": b[2]} for b in w.bl]
    st["terrain"] = [[(w.t(x, y) if w.t(x, y) not in ("HEAL", "MIMIC") else "CHEST")
                      for x in range(40)] for y in range(26)]
    st["occupant"] = [[w.occ.get((x, y)) for x in range(40)] for y in range(26)]
    a = S.decide_action(st, memory)
    print(f"t={i} {a} hero=({w.hx},{w.hy})")
    w = S.step_world(w, a)
print("memory plan:", memory.get("plan"))
st["turn"] = 20
st["hero"].update({"x": w.hx, "y": w.hy, "hp": w.hp, "keys": [w.k1, w.k2],
                   "jumps": w.jumps, "bombs": w.bombs})
st["terrain"] = [[(w.t(x, y) if w.t(x, y) not in ("HEAL", "MIMIC") else "CHEST")
                  for x in range(40)] for y in range(26)]
st["occupant"] = [[w.occ.get((x, y)) for x in range(40)] for y in range(26)]
print("t20 decision:", S._decide(st, memory))
import time
field_p = S._relaxed_dist(w, 11, 17)
bf = S._relaxed_dist(w, 8, 17)
h_fn = (lambda node: min([field_p.get(b, 999) for b, v in node.occ.items() if v == "BOX"] or [999])
        + bf.get((node.hx, node.hy), 999))
res, complete, nodes = S._astar(w, (lambda c: c.occ.get((11, 17)) == "BOX"), h_fn,
                                time.monotonic() + 2.0, 10000, push_guard=field_p)
print("direct real-h search: complete=", complete, "nodes=", nodes, "path=", res[:12] if res else None)
print("hero:", (w.hx, w.hy), "boxes:", sorted([p for p, v in w.occ.items() if v == "BOX"]),
      "plates:", w.plates)
