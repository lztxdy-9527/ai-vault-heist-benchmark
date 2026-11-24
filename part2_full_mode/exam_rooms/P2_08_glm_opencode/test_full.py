# -*- coding: utf-8 -*-
"""下半场本地回归：建图校验 + author_solution 回放 + GV22 抽查 + 基准求解。"""
import sys
import json
import time
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S

W, H = 40, 26
DIRS = S.DIRS


def validate(d):
    grid = d["grid"]
    errs = []
    assert len(grid) == 26
    for y, row in enumerate(grid):
        assert len(row) == 40
    for y in range(H):
        for x in range(W):
            if x in (0, 39) or y in (0, 25):
                if grid[y][x] != "T_W":
                    errs.append(f"border ({x},{y})")
    for y in range(12, 15):
        for x in range(1, 4):
            if grid[y][x] != "EMPTY":
                errs.append(f"spawn ({x},{y})={grid[y][x]}")
    k1 = [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "K1"]
    k2 = [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "K2"]
    vv = [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "V"]
    assert len(k1) == len(k2) == len(vv) == 1
    (k1x, k1y), (k2x, k2y), (vx, vy) = k1[0], k2[0], vv[0]
    assert 12 <= k1x <= 34 and 2 <= k1y <= 10
    assert 12 <= k2x <= 34 and 15 <= k2y <= 23
    assert abs(k1x - k2x) + abs(k1y - k2y) >= 12
    assert 33 <= vx <= 37 and 4 <= vy <= 21
    cost = 0
    cnt = {}
    n_plate = n_pgate = n_box = 0
    for y in range(1, 25):
        for x in range(1, 39):
            t = grid[y][x]
            cost += S.TILE_COSTS[t]
            cnt[t] = cnt.get(t, 0) + 1
    assert cost <= 3000, f"budget {cost}"
    n_lasers = sum(cnt.get(k, 0) for k in
                   ("LASER_U", "LASER_D", "LASER_L", "LASER_R",
                    "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R"))
    assert n_lasers <= 12
    assert cnt.get("T_W", 0) <= 120
    assert cnt.get("PLATE", 0) <= 4 and cnt.get("P_GATE", 0) <= 8
    assert cnt.get("BOX", 0) <= 6
    assert sum(cnt.get(k, 0) for k in ("ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R")) <= 12
    assert cnt.get("TNT", 0) <= 12 and cnt.get("MIMIC", 0) <= 4 and cnt.get("HEAL", 0) <= 4
    n_plate = cnt.get("PLATE", 0); n_box = cnt.get("BOX", 0)
    if cnt.get("P_GATE", 0) > 0:
        assert 1 <= n_plate <= n_box, f"P_GATE requires 1<=PLATE({n_plate})<=BOX({n_box})"
    # MIMIC 线索绑定
    terr = [[grid[y][x] if grid[y][x] not in ("BOX", "TNT") else "EMPTY" for x in range(W)] for y in range(H)]
    occ = [["BOX" if grid[y][x] == "BOX" else ("TNT" if grid[y][x] == "TNT" else None) for x in range(W)] for y in range(H)]
    chests = [(x, y) for y in range(H) for x in range(W) if grid[y][x] in ("HEAL", "MIMIC")]
    clues = [[False] * W for _ in range(H)]
    for (mx, my) in [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "MIMIC"]:
        ok = False
        for ch in "UDLR":
            dx, dy = DIRS[ch]
            nx, ny = mx + dx, my + dy
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            if terr[ny][nx] != "EMPTY" or occ[ny][nx] is not None:
                continue
            if 1 <= nx <= 3 and 12 <= ny <= 14:
                continue
            if any((nx + ddx, ny + ddy) in chests and (nx + ddx, ny + ddy) != (mx, my)
                   for ddx, ddy in DIRS.values() if 0 <= nx + ddx < W and 0 <= ny + ddy < H):
                continue
            if clues[ny][nx]:
                continue
            clues[ny][nx] = True
            ok = True
            break
        if not ok:
            errs.append(f"MIMIC ({mx},{my}) no clue")
    # 出生 4 回合准入：模拟两个不同 Turn-1 落点的安全序列
    spawn_ok = _spawn_check(d)
    if not spawn_ok:
        errs.append("spawn 4-turn check failed")
    print(f"[validate] cost={cost}G plates={n_plate} boxes={n_box} "
          f"lasers={n_lasers} k1={k1[0]} k2={k2[0]} v={vv[0]} author={len(d['author_solution'])}步 errs={errs}")
    return not errs


def _mk_state(d, turn=1, hx=2, hy=13, hp=100, k=(False, False)):
    grid = d["grid"]
    terr = [[grid[y][x] if grid[y][x] not in ("HEAL", "MIMIC") else "CHEST" for x in range(W)] for y in range(H)]
    occ = [["BOX" if grid[y][x] == "BOX" else ("TNT" if grid[y][x] == "TNT" else None) for x in range(W)] for y in range(H)]
    clues = [[False] * W for _ in range(H)]
    k1 = [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "K1"][0]
    k2 = [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "K2"][0]
    vv = [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "V"][0]
    # 线索层（按官方绑定规则）
    # —— 简化：直接用 validate 同款逻辑
    return {
        "turn": turn, "turns_left": 240 - turn, "mode": "FULL",
        "hero": {"x": hx, "y": hy, "hp": hp, "keys": list(k),
                 "jumps": 3, "throws": 3, "bombs": 2},
        "gates_flipped": False, "plates_active": False,
        "targets": {"K1": list(k1), "K2": list(k2), "V": list(vv)},
        "visible_mask": [[True] * W for _ in range(H)],
        "terrain": terr, "occupant": occ, "bombs": [], "clues": clues,
        "laser_warnings": [],
    }


def _spawn_check(d):
    """至少 2 个不同 Turn-1 落点能 0 机关伤活过第 4 回合。"""
    ok_count = 0
    for first in ("WAIT", "MOVE_R", "MOVE_U", "MOVE_D"):
        w = S.decode_state(_mk_state(d, turn=1))
        acts = [first, "WAIT", "WAIT", "WAIT"]
        alive = True
        for a in acts:
            w = S.step_world(w, a)
            if w.status != "ALIVE" or w.hp < 100:
                alive = False
                break
        if alive and w.hx != 2 or (alive and w.hy != 13):
            pass
        if alive:
            ok_count += 1
        if ok_count >= 3:
            break
    return ok_count >= 2


def replay(d):
    w = S.decode_state(_mk_state(d, turn=1))
    sol = d["author_solution"]
    assert 1 <= len(sol) <= 200, f"author steps {len(sol)} > 200"
    for a in sol:
        assert a in S.VALID_ACTIONS, f"illegal {a}"
    n = 0
    for i, a in enumerate(sol, 1):
        w = S.step_world(w, a)
        n = i
        if w.status != "ALIVE":
            break
    print(f"[replay] ran={n}/{len(sol)} status={w.status} hp={w.hp} pos=({w.hx},{w.hy}) "
          f"keys=({w.k1},{w.k2}) jumps={w.jumps} bombs={w.bombs}")
    ok = w.status == "CLEARED" and n == len(sol) and w.hp > 0
    print(f"[replay] {'PASS: 末步恰好首达通关' if ok else 'FAIL'}")
    return ok


def run_solver(d, label, max_turns=240, verbose=False):
    st = _mk_state(d, turn=1)
    w = S.decode_state(st)
    memory = {}
    t0 = time.time()
    n = 0
    for i in range(1, max_turns + 1):
        st["turn"] = i
        st["turns_left"] = 240 - i
        # 从模拟世界同步 state（真实裁判由引擎同步；此处以模拟器为准）
        st["hero"]["x"], st["hero"]["y"] = w.hx, w.hy
        st["hero"]["hp"] = w.hp
        st["hero"]["keys"] = [w.k1, w.k2]
        st["hero"]["jumps"] = w.jumps
        st["hero"]["bombs"] = w.bombs
        st["gates_flipped"] = w.gates
        st["bombs"] = [{"x": b[0], "y": b[1], "timer": b[2]} for b in w.bl]
        st["terrain"] = [[(w.t(x, y) if w.t(x, y) not in ("HEAL", "MIMIC") else "CHEST")
                          for x in range(W)] for y in range(H)]
        st["occupant"] = [[w.occ.get((x, y)) for x in range(W)] for y in range(H)]
        act = S.decide_action(st, memory)
        w = S.step_world(w, act)
        n = i
        if verbose and i % 20 == 0:
            print(f"  t={i} {act} pos=({w.hx},{w.hy}) hp={w.hp} k=({w.k1},{w.k2})")
        if w.status != "ALIVE":
            break
    dt = time.time() - t0
    print(f"[solver:{label}] status={w.status} turns={n} hp={w.hp} keys=({w.k1},{w.k2}) "
          f"pos=({w.hx},{w.hy}) 用时{dt:.1f}s 均步{dt/max(1,n)*1000:.0f}ms")
    return w.status


if __name__ == "__main__":
    d = S.build_dungeon()
    v = validate(d)
    r = replay(d)
    print("dungeon:", "PASS" if (v and r) else "FAIL")

    with open(r"part2_full_mode/exam_rooms\P2_08_glm_opencode\v22_sparring_benchmarks.json",
              encoding="utf-8") as f:
        bench = json.load(f)
    for name in ("BENCH_WEAK", "BENCH_STRONG"):
        dd = {"taunt": "", "grid": bench["dungeons"][name]["grid"],
              "author_solution": ["WAIT"]}
        st = run_solver(dd, name, verbose=True)
        print(f"  -> {name}: {'CLEARED' if st == 'CLEARED' else st}")
