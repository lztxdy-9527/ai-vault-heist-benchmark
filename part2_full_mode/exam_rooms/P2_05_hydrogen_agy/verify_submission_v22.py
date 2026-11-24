"""End-to-end final verification suite directly testing submission.py against ALL v2.2 FULL rules."""

import collections
import json
import subprocess
import sys
import time

import local_judge_v22 as judge
import stress_v22
import submission


def run_match(grid: list[list[str]], hero_fn, restart_turn: int | None = None):
    dec = judge.decode_grid_only(grid)
    eng = judge.GameEngineV22(dec)
    mem = {}
    t1_ms = 0.0
    max_t2_ms = 0.0
    for turn in range(1, judge.MAX_TURNS + 1):
        if restart_turn is not None and turn == restart_turn:
            mem = {}
        state = eng.get_state(turn, mode="FULL")
        ts = time.perf_counter()
        act = hero_fn(state, mem)
        el = (time.perf_counter() - ts) * 1000.0
        assert act in judge.VALID_ACTIONS, f"Illegal action {act!r} on turn {turn}"
        if turn == 1:
            t1_ms = el
        else:
            max_t2_ms = max(max_t2_ms, el)
        eng.step(act)
        if eng.status != "ALIVE":
            break
    hs, ds = eng.compute_scores()
    return eng.status, eng.turn, eng.hp, (eng.has_k1, eng.has_k2), hs, ds, t1_ms, max_t2_ms


def greedy_baseline(state: dict, _mem: dict) -> str:
    hx, hy = state["hero"]["x"], state["hero"]["y"]
    k1, k2 = state["hero"]["keys"]
    tx, ty = state["targets"]["V"] if (k1 and k2) else (state["targets"]["K1"] if not k1 else state["targets"]["K2"])
    best = None
    tr = state["terrain"]
    occ = state["occupant"]
    gf = state["gates_flipped"]
    pa = state["plates_active"]
    for d, (dx, dy) in judge.DIRECTIONS.items():
        nx, ny = hx + dx, hy + dy
        if 0 <= nx < 40 and 0 <= ny < 26:
            t = tr[ny][nx]
            if t in ("W", "T_W", "PIT", "CHEST") or t in judge.ALL_LASER_DIRS:
                continue
            if (t == "R_GATE" and not gf) or (t == "B_GATE" and gf) or (t == "P_GATE" and not pa):
                continue
            if t in judge.ONEWAY_DIRS and d != judge.ONEWAY_DIRS[t]:
                continue
            if occ[ny][nx] == "TNT":
                continue
            sc = abs(nx - tx) + abs(ny - ty)
            if best is None or sc < best[0]:
                best = (sc, f"MOVE_{d}")
    return best[1] if best else "WAIT"


def bfs_baseline(state: dict, mem: dict) -> str:
    tr = state["terrain"]
    occ = state["occupant"]
    hx, hy = state["hero"]["x"], state["hero"]["y"]
    k1, k2 = state["hero"]["keys"]
    gf = state["gates_flipped"]
    pa = state["plates_active"]
    goal = tuple(state["targets"]["V"] if (k1 and k2) else (state["targets"]["K1"] if not k1 else state["targets"]["K2"]))
    q = collections.deque([(hx, hy, [])])
    seen = {(hx, hy)}
    while q:
        ux, uy, path = q.popleft()
        if (ux, uy) == goal and path:
            return path[0]
        for d, (dx, dy) in judge.DIRECTIONS.items():
            nx, ny = ux + dx, uy + dy
            if 0 <= nx < 40 and 0 <= ny < 26 and (nx, ny) not in seen:
                t = tr[ny][nx]
                if t in ("W", "T_W", "PIT", "CHEST", "SWITCH") or t in judge.ALL_LASER_DIRS:
                    continue
                if (t == "R_GATE" and not gf) or (t == "B_GATE" and gf) or (t == "P_GATE" and not pa):
                    continue
                if t in judge.ONEWAY_DIRS and d != judge.ONEWAY_DIRS[t]:
                    continue
                if occ[ny][nx] in ("BOX", "TNT"):
                    continue
                seen.add((nx, ny))
                q.append((nx, ny, path + [f"MOVE_{d}"]))
    return greedy_baseline(state, mem)


def main():
    print("=== 1. AST Safety, Subprocess Import & build_dungeon() Check ===")
    with open("submission.py", "r", encoding="utf-8") as f:
        src = f.read()
    issues = judge.check_ast_safety(src)
    assert not issues, f"AST safety issues: {issues}"
    print(f"  AST safety: PASS (0 issues, {len(src.splitlines())} lines)")

    sub_cmd = [
        sys.executable, "-c",
        "import time; t0=time.perf_counter(); import submission; t1=time.perf_counter(); d=submission.build_dungeon(); t2=time.perf_counter(); print(f'{(t1-t0)*1000:.2f} {(t2-t1)*1000:.2f}')"
    ]
    out = subprocess.check_output(sub_cmd, text=True).strip()
    imp_ms, bld_ms = map(float, out.split())
    assert imp_ms <= 1500.0 and bld_ms <= 2000.0
    print(f"  Fresh import: {imp_ms:.2f}ms (<=1500ms) | build_dungeon(): {bld_ms:.2f}ms (<=2000ms)")

    dung = submission.build_dungeon()
    dec = judge.validate_dungeon(dung, check_spawn_4turn=True, check_author=True)
    print(f"  validate_dungeon: PASS | gold={dec['spent_gold']}G/3000G | inner_T_W={dec['counts']['T_W']}/120 | author_steps={len(dung['author_solution'])}/200")

    print("\n=== 2. Golden Vectors v2.2 ===")
    judge.verify_golden_vectors("golden_vectors_v22.json")

    print("\n=== 3. Mid-Bomb Restart Safety Test ===")
    sp = json.load(open("v22_sparring_benchmarks.json", "r", encoding="utf-8"))["dungeons"]
    eng_b = judge.GameEngineV22(judge.decode_grid_only(sp["BENCH_WEAK"]["grid"]))
    eng_b.step("MOVE_R")
    eng_b.step("BOMB")
    st_b = eng_b.get_state(3)
    act_b = submission.decide_action(st_b, {})
    eng_b.step(act_b)
    act_b2 = submission.decide_action(eng_b.get_state(4), {})
    eng_b.step(act_b2)
    assert eng_b.status == "ALIVE" and eng_b.hp == 100
    print(f"  Mid-bomb restart escape: PASS (pos=({eng_b.hx},{eng_b.hy}), hp={eng_b.hp})")

    print("\n=== 4. submission.decide_action Full Hero Suite (25 Maps) ===")
    for name in ("BENCH_WEAK", "BENCH_STRONG"):
        st, t, hp, k, hs, ds, t1, mt2 = run_match(sp[name]["grid"], submission.decide_action)
        assert st == "CLEARED" and t1 <= 2000.0 and mt2 <= 500.0, f"{name} failed/slow"
        print(f"  [{name:30s}] {st:8s} t={t:3d} hp={hp:3d} k={int(k[0])+int(k[1])}/2 hero={hs:5.1f} t1={t1:6.1f}ms max_t2={mt2:6.2f}ms")

    stress_scores = []
    for name, grid in stress_v22.build_stress_maps():
        st, t, hp, k, hs, ds, t1, mt2 = run_match(grid, submission.decide_action)
        assert t1 <= 2000.0 and mt2 <= 500.0, f"{name} latency exceeded"
        stress_scores.append(hs)
        print(f"  [{name:30s}] {st:8s} t={t:3d} hp={hp:3d} k={int(k[0])+int(k[1])}/2 hero={hs:5.1f} t1={t1:6.1f}ms max_t2={mt2:6.2f}ms")

    st, t, hp, k, hs, ds, t1, mt2 = run_match(sp["BENCH_STRONG"]["grid"], submission.decide_action, restart_turn=8)
    assert t1 <= 2000.0 and mt2 <= 500.0
    print(f"  [{'S09_RESTART_AT_T8_BENCH_STRONG':30s}] {st:8s} t={t:3d} hp={hp:3d} k={int(k[0])+int(k[1])}/2 hero={hs:5.1f} t1={t1:6.1f}ms max_t2={mt2:6.2f}ms")

    p1 = json.load(open("part1_dungeons_benchmark.json", "r", encoding="utf-8"))["dungeons"]
    p1_scores = []
    for name in sorted(p1.keys()):
        grid = p1[name]["grid"] if isinstance(p1[name], dict) else p1[name]
        st, t, hp, k, hs, ds, t1, mt2 = run_match(grid, submission.decide_action)
        assert t1 <= 2000.0 and mt2 <= 500.0, f"{name} latency exceeded"
        p1_scores.append(hs)
        print(f"  [{name:30s}] {st:8s} t={t:3d} hp={hp:3d} k={int(k[0])+int(k[1])}/2 hero={hs:5.1f} t1={t1:6.1f}ms max_t2={mt2:6.2f}ms")

    print(f"\n  HERO TOTALS -> Part1 Avg={sum(p1_scores)/len(p1_scores):.2f} | Stress Avg={sum(stress_scores)/len(stress_scores):.2f}")

    print("\n=== 5. submission.build_dungeon() Defense Audit ===")
    for label, fn in (
        ("Greedy_Manhattan_Bot", greedy_baseline),
        ("Static_BFS_Baseline", bfs_baseline),
        ("Submission_Hero_Live_1.45s", submission.decide_action),
    ):
        st, t, hp, k, hs, ds, t1, mt2 = run_match(dung["grid"], fn)
        print(f"  [{label:30s}] {st:8s} t={t:3d} hp={hp:3d} k={int(k[0])+int(k[1])}/2 hero={hs:5.1f} demon={ds:5.1f} t1={t1:6.1f}ms max_t2={mt2:6.2f}ms")


if __name__ == "__main__":
    main()
