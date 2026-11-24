# -*- coding: utf-8 -*-
import sys, time, json
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S
import test_full as T

with open(r"part2_full_mode/exam_rooms\P2_08_glm_opencode\v22_sparring_benchmarks.json", encoding="utf-8") as f:
    bench = json.load(f)
dd = {"taunt": "", "grid": bench["dungeons"]["BENCH_STRONG"]["grid"], "author_solution": ["WAIT"]}
w = S.decode_state(T._mk_state(dd, turn=1))

for pp in [(8, 18), (8, 22), (7, 6)]:
    field_p = S._relaxed_dist(w, pp[0], pp[1])
    box_field = {}
    for (bx, by) in [p for p, v in w.occ.items() if v == "BOX"]:
        d2 = S._relaxed_dist(w, bx, by)
        for kk, vv2 in d2.items():
            if vv2 < box_field.get(kk, 999):
                box_field[kk] = vv2
    h_fn = (lambda node: min([field_p.get(b, 999) for b, v in node.occ.items() if v == "BOX"] or [999])
            + box_field.get((node.hx, node.hy), 999))
    test = (lambda c, pp=pp: c.occ.get(pp) == "BOX")
    t0 = time.monotonic()
    res, complete, nodes = S._astar(w, test, h_fn, t0 + 3.0, 60000, push_guard=field_p)
    print(f"plate {pp}: complete={complete} path_len={len(res) if res else None} nodes={nodes} "
          f"用时{time.monotonic()-t0:.2f}s")
    if res:
        print("   path:", res[:25])
