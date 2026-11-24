# -*- coding: utf-8 -*-
import sys, json
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S
import test_full as T

orig_atomic = S._atomic

def logged_atomic(w, x0, y0, x1, y1, dch, is_hero, steps, exposure):
    r = orig_atomic(w, x0, y0, x1, y1, dch, is_hero, steps, exposure)
    if not is_hero:
        print(f"    [box-atomic] ({x0},{y0})->({x1},{y1}) d={dch} stop@({w.hx if False else x1},{y1})"
              f" chain-end; boxes now:", sorted([p for p, v in w.occ.items() if v == "BOX"]))
    return r

S._atomic = logged_atomic

with open(r"part2_full_mode/exam_rooms\P2_08_glm_opencode\v22_sparring_benchmarks.json", encoding="utf-8") as f:
    bench = json.load(f)
dd = {"taunt": "", "grid": bench["dungeons"]["BENCH_STRONG"]["grid"], "author_solution": ["WAIT"]}
st = T._mk_state(dd, turn=1)
w = S.decode_state(st)
memory = {}
for i in range(1, 73):
    st["turn"] = i
    st["hero"].update({"x": w.hx, "y": w.hy, "hp": w.hp, "keys": [w.k1, w.k2],
                       "jumps": w.jumps, "bombs": w.bombs})
    st["gates_flipped"] = w.gates
    st["bombs"] = [{"x": b[0], "y": b[1], "timer": b[2]} for b in w.bl]
    st["terrain"] = [[(w.t(x, y) if w.t(x, y) not in ("HEAL", "MIMIC") else "CHEST")
                      for x in range(40)] for y in range(26)]
    st["occupant"] = [[w.occ.get((x, y)) for x in range(40)] for y in range(26)]
    if 66 <= i <= 72:
        print(f"t={i}: hero=({w.hx},{w.hy}) act:")
    a = S.decide_action(st, memory)
    w = S.step_world(w, a)
