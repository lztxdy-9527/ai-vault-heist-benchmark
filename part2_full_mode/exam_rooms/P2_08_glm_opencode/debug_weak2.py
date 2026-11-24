# -*- coding: utf-8 -*-
import sys, json, time
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
    w = S.step_world(w, a)

st["turn"] = 20
st["hero"].update({"x": w.hx, "y": w.hy, "hp": w.hp, "keys": [w.k1, w.k2],
                   "jumps": w.jumps, "bombs": w.bombs})
st["terrain"] = [[(w.t(x, y) if w.t(x, y) not in ("HEAL", "MIMIC") else "CHEST")
                  for x in range(40)] for y in range(26)]
st["occupant"] = [[w.occ.get((x, y)) for x in range(40)] for y in range(26)]
w = S.decode_state(st)
print("hero:", (w.hx, w.hy), "bombs:", w.bombs, "bl:", w.bl)
print("row 17:", [w.t(x, 17) for x in range(7, 13)])
field_p = S._relaxed_dist(w, 11, 17)
print("field_p[(8,17)] =", field_p.get((8, 17)), " field_p[(9,17)] =", field_p.get((9, 17)))

def h_fn(node):
    return (min([field_p.get(b, 999) for b, v in node.occ.items()
                 if v == "BOX" and b not in node.plates] or [999])
            + 999)  # 简化：不含 hero 项

res, complete, nodes = S._astar(w, (lambda c: c.occ.get((11, 17)) == "BOX"),
                                h_fn, time.monotonic() + 2.0, 10000,
                                push_guard=field_p)
print("plate search: complete=", complete, "nodes=", nodes, "path=", res)
