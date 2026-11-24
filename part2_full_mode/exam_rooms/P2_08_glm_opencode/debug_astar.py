# -*- coding: utf-8 -*-
import sys, json, time, heapq
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S
import test_full as T

with open(r"part2_full_mode/exam_rooms\P2_08_glm_opencode\v22_sparring_benchmarks.json", encoding="utf-8") as f:
    bench = json.load(f)
dd = {"taunt": "", "grid": bench["dungeons"]["BENCH_WEAK"]["grid"], "author_solution": ["WAIT"]}
st = T._mk_state(dd, turn=20)
st["hero"]["x"], st["hero"]["y"] = 7, 17
st["terrain"][17][9] = "EMPTY"; st["terrain"][17][10] = "EMPTY"
w = S.decode_state(st)

field_p = S._relaxed_dist(w, 11, 17)
bf = S._relaxed_dist(w, 8, 17)
h_fn = (lambda node: min([field_p.get(b, 999) for b, v in node.occ.items()
                          if v == "BOX" and b not in node.plates] or [999])
        + bf.get((node.hx, node.hy), 999))

# 手工复刻 A* 前 30 次弹出
rays0 = S._ray_cells(w)
zone = S._ray_zone(w, rays0)
open_heap = [(3.0 * h_fn(w), 0, 0, w)]
best_g = {S._node_key(w, zone): 0}
counter = 1
pops = 0
while open_heap and pops < 30:
    f, g, _, cur = heapq.heappop(open_heap)
    k = S._node_key(cur, zone)
    if g > best_g.get(k, 1 << 30):
        continue
    pops += 1
    print(f"pop#{pops}: f={f:.1f} g={g} hero=({cur.hx},{cur.hy}) "
          f"box@{[p for p, v in cur.occ.items() if v == 'BOX']} "
          f"h={h_fn(cur)} goal={cur.occ.get((11, 17)) == 'BOX'}")
    if pops == 3:
        rays = S._ray_cells(cur) if cur.cannons else []
        print("  >>> pop#3 children detail:")
        for act in S._actions(cur, rays):
            nw = S.step_world(cur, act)
            print(f"      {act}: hero->({nw.hx},{nw.hy}) box@{[p for p, v in nw.occ.items() if v == 'BOX']}"
                  f" st={nw.status} hp={nw.hp}")
    rays = S._ray_cells(cur) if cur.cannons else []
    for act in S._actions(cur, rays):
        nw = S.step_world(cur, act)
        if nw.status == "DEAD" or nw.hp < cur.hp:
            continue
        gone = [p for p in cur.occ if cur.occ[p] == "BOX" and p not in nw.occ]
        new = [p for p in nw.occ if nw.occ[p] == "BOX" and p not in cur.occ]
        if gone:
            if any(gp in cur.plates for gp in gone):
                print(f"   {act}: GUARD-plate-reject (gone={gone})")
                continue
            if not new:
                print(f"   {act}: GUARD-vanish-reject")
                continue
            old_best = min(field_p.get(p, 999) for p in gone)
            new_best = min(field_p.get(p, 999) for p in new)
            if new_best > old_best:
                print(f"   {act}: GUARD-monotone-reject {gone}->{new}")
                continue
        k2 = S._node_key(nw, zone)
        ng = g + 1
        if best_g.get(k2, 1 << 30) <= ng:
            continue
        best_g[k2] = ng
        heapq.heappush(open_heap, (ng + 3.0 * h_fn(nw), ng, counter, nw))
        counter += 1
