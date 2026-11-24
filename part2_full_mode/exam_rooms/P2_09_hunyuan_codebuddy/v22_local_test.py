"""v2.2 本地回归自测（仅本地使用，不属于评测交付接口）。

覆盖：建造合规 / 作者解回放 / 出生 4 回合准入 / golden vectors /
双基准靶场 / 上半场 14 张图 FULL 对局 / 单步耗时。
"""
import collections
import copy
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import submission as S

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = S.W, S.H


def empty_grid():
    return [["T_W" if (x in (0, W - 1) or y in (0, H - 1)) else "EMPTY"
             for x in range(W)] for y in range(H)]


def put(g, tiles):
    for (x, y), t in tiles.items():
        g[y][x] = t
    return g


def replay(grid, actions, trace=False):
    sim = S._Sim(grid=grid)
    for i, a in enumerate(actions):
        if sim.status != "PLAYING":
            break
        sim.step(a)
        if trace and (i < 6 or sim.h["hp"] != 100 or i % 40 == 0):
            print("   t=%3d %-8s pos=(%2d,%2d) hp=%3d keys=%s flip=%s plates=%s" %
                  (sim.turn - 1, a, sim.h["x"], sim.h["y"], sim.h["hp"],
                   sim.h["keys"], sim.flipped, sim.plates_active()))
    return sim


def birth_admission(grid, verbose=False):
    """至少 2 个不同 Turn-1 零伤落点，且各自存在 Turn2..4 零伤序列。"""
    base = S._Sim(grid=grid)
    landings = {}
    for a in S.VALID_ACTIONS:
        c = base.clone()
        c.step(a)
        if c.status == "PLAYING" and c.h["hp"] == 100:
            landings.setdefault((c.h["x"], c.h["y"]), c)
    good = []

    def dfs(sim, depth):
        if depth == 0:
            return True
        for a in S.VALID_ACTIONS:
            c = sim.clone()
            c.step(a)
            if c.status == "PLAYING" and c.h["hp"] == 100 and dfs(c, depth - 1):
                return True
        return False

    for p, sim in landings.items():
        if dfs(sim, 3):
            good.append(p)
    if verbose:
        print("   turn1 landings:", sorted(landings), "-> safe-4:", sorted(good))
    return len(good) >= 2, good


def check_own():
    print("=== OWN DUNGEON ===")
    t0 = time.monotonic()
    d = S.build_dungeon()
    print("build time %.4fs" % (time.monotonic() - t0))
    g = d["grid"]
    ok, spent, info = S.validate_grid(g)
    print("valid=%s spent=%s vault=%s counts=%s" %
          (ok, spent, info.get("vault_gold"),
           {k: v for k, v in info.get("counts", {}).items() if k not in ("EMPTY",)}))
    print("taunt:", d["taunt"], "| len(taunt)=", len(d["taunt"]))
    a = d["author_solution"]
    print("author steps:", len(a), "all valid:", all(x in S.VALID_ACTIONS for x in a))
    sim = replay(g, a)
    print("author replay: status=%s win_turn=%s hp=%s keys=%s D=%s turn=%s" %
          (sim.status, sim.win_turn, sim.h["hp"], sim.h["keys"],
           sim.trap_damage, sim.turn - 1))
    print("win exactly on last step:",
          sim.status == "CLEARED" and sim.win_turn == len(a) and len(a) <= 200)
    okb, good = birth_admission(g, verbose=True)
    print("birth admission:", okb, "safe landings:", len(good))
    # FULL 明牌下让求解器自己打一次自己的图
    t0 = time.monotonic()
    sim2, worst, acts, wturn, wlate = play(g, verbose=False)
    print("self-play: status=%s T=%s hp=%s keys=%s D=%s wall=%.3fs worst_step=%.4fs@turn%d late=%.4fs" %
          (sim2.status, sim2.win_turn or sim2.turn - 1, sim2.h["hp"],
           sim2.h["keys"], sim2.trap_damage, time.monotonic() - t0, worst, wturn, wlate))
    return d, sim, ok, okb


def golden():
    print("=== GOLDEN VECTORS ===")
    # GV22_01 预算与压板约束
    g = empty_grid()
    put(g, {(20, 5): "K1", (20, 20): "K2", (35, 13): "V",
            (8, 8): "PLATE", (6, 8): "BOX", (34, 13): "P_GATE",
            (25, 2): "LASER2_D", (10, 13): "ONEWAY_R"})
    ok, spent, info = S.validate_grid(g)
    sim = S._Sim(grid=g)
    print("GV22_01 valid=%s spent=%s (exp 225) plates_active=%s (exp False)" %
          (ok, spent, sim.plates_active()))
    # GV22_02 仅 BOX 压板
    g = empty_grid()
    put(g, {(20, 5): "K1", (20, 20): "K2", (35, 13): "V",
            (5, 13): "PLATE", (34, 13): "P_GATE", (7, 13): "BOX"})
    sim = S._Sim(grid=g)
    sim.h["x"], sim.h["y"] = 4, 13
    sim.step("MOVE_R")
    s1 = (sim.plates_active(), sim.high(34, 13))
    sim.h["x"], sim.h["y"] = 8, 13
    sim.step("MOVE_L")
    sim.step("MOVE_L")
    s2 = (sim.plates_active(), sim.high(34, 13), sim.occ(5, 13))
    print("GV22_02 hero-on-plate (exp False,True):", s1,
          "| box pushed (exp True,False,BOX):", s2)
    # GV22_03 12 拍双射秒杀
    g = empty_grid()
    put(g, {(20, 5): "K1", (20, 20): "K2", (35, 13): "V",
            (15, 8): "LASER_D", (12, 10): "LASER2_R"})
    sim = S._Sim(grid=g)
    sim.turn = 12
    sim.h["x"], sim.h["y"] = 15, 10
    st = sim.state()
    per = sorted({w["period"] for w in st["laser_warnings"] if (w["x"], w["y"]) == (15, 10)})
    sim.step("WAIT")
    print("GV22_03 periods at (15,10) (exp [3,4]):", per,
          "| hp (exp 0):", sim.h["hp"], "| status:", sim.status)
    # GV22_04(a) 逆向推箱被整次拒绝 + CRACK 不坍塌
    g = empty_grid()
    put(g, {(20, 5): "K1", (20, 20): "K2", (35, 13): "V",
            (5, 13): "CRACK", (6, 13): "ONEWAY_L"})
    sim = S._Sim(grid=g)
    sim.bo[(6, 13)] = "BOX"
    sim.h["x"], sim.h["y"] = 5, 13
    sim.step("MOVE_R")
    print("GV22_04a box=%s hero=(%d,%d) crack=%s (exp BOX@(6,13), hero(5,13), CRACK)" %
          (sim.occ(6, 13), sim.h["x"], sim.h["y"], sim.tile(5, 13)))
    # GV22_05 弹簧遇逆向 ONEWAY 提前落停
    g = empty_grid()
    put(g, {(20, 5): "K1", (20, 20): "K2", (35, 13): "V",
            (10, 10): "SPRING_R", (12, 10): "ONEWAY_L"})
    sim = S._Sim(grid=g)
    sim.h["x"], sim.h["y"] = 9, 10
    sim.step("MOVE_R")
    print("GV22_05 spring land (exp (11,10)): (%d,%d)" % (sim.h["x"], sim.h["y"]))
    # GV22_05b 跳跃逆向 ONEWAY 失败仍扣次数
    g = empty_grid()
    put(g, {(20, 5): "K1", (20, 20): "K2", (35, 13): "V", (6, 14): "ONEWAY_L"})
    sim = S._Sim(grid=g)
    sim.h["x"], sim.h["y"] = 5, 14
    sim.step("JUMP_R")
    print("GV22_05b jump (exp (5,14), jumps=2): (%d,%d), jumps=%d" %
          (sim.h["x"], sim.h["y"], sim.h["jumps"]))
    # GV22_07 阶段 C 炸箱关门挡下阶段 D 激光
    g = empty_grid()
    put(g, {(20, 5): "K1", (20, 20): "K2", (35, 13): "V",
            (10, 10): "PLATE", (12, 10): "P_GATE", (15, 10): "LASER_L"})
    sim = S._Sim(grid=g)
    sim.bo[(10, 10)] = "BOX"
    sim.h["x"], sim.h["y"] = 7, 10
    sim.turn = 3
    print("GV22_07 before: plates=%s pgate_high=%s" %
          (sim.plates_active(), sim.high(12, 10)))
    # 手放一颗 timer=1 的炸弹在箱旁，阶段 C 炸掉箱子
    sim.bombs = [(9, 10, 1)]
    sim.step("WAIT")
    print("GV22_07 after: plates=%s hp=%s (exp False, 100)" %
          (sim.plates_active(), sim.h["hp"]))
    # GV22_08 V 先于阶段 D 结算
    g = empty_grid()
    put(g, {(20, 5): "K1", (20, 20): "K2", (35, 13): "V", (35, 5): "LASER_D"})
    sim = S._Sim(grid=g)
    sim.h["x"], sim.h["y"] = 34, 13
    sim.h["hp"] = 20
    sim.h["keys"] = [True, True]
    sim.turn = 240
    sim.step("MOVE_R")
    print("GV22_08 status=%s hp=%s (exp CLEARED,20)" % (sim.status, sim.h["hp"]))


def play(grid, verbose=False, max_turns=240):
    sim = S._Sim(grid=grid)
    mem = {}
    worst = 0.0
    worst_turn = 0
    worst_late = 0.0
    acts = []
    while sim.status == "PLAYING" and len(acts) < max_turns:
        st = sim.state()
        t0 = time.monotonic()
        a = S.decide_action(st, mem)
        dt = time.monotonic() - t0
        if dt > worst:
            worst, worst_turn = dt, st["turn"]
        if st["turn"] > 1:
            worst_late = max(worst_late, dt)
        acts.append(a)
        if verbose and (len(acts) <= 5 or len(acts) % 30 == 0):
            print("   t=%3d %-8s pos=(%2d,%2d) hp=%3d keys=%s flip=%s plates=%s dt=%.3f" %
                  (sim.turn, a, sim.h["x"], sim.h["y"], sim.h["hp"],
                   sim.h["keys"], sim.flipped, sim.plates_active(), dt))
        sim.step(a)
    return sim, worst, acts, worst_turn, worst_late


def benchmarks():
    print("=== SPARRING BENCHMARKS + PART1 GRIDS ===")
    fn = os.path.join(HERE, "v22_sparring_benchmarks.json")
    d = json.load(open(fn, encoding="utf-8"))
    for name, dd in d["dungeons"].items():
        g = dd["grid"]
        ok, spent, info = S.validate_grid(g)
        okb, _ = birth_admission(g)
        t0 = time.monotonic()
        sim, worst, acts, wturn, wlate = play(g)
        print("%-13s valid=%s spent=%s birth=%s | %-8s T=%3d hp=%3d keys=%s D=%5.1f wall=%.2fs step=%.4fs@t%d late=%.4fs" %
              (name, ok, spent, okb, sim.status, sim.win_turn or sim.turn - 1,
               sim.h["hp"], sim.h["keys"], sim.trap_damage,
               time.monotonic() - t0, worst, wturn, wlate))
    fn2 = os.path.join(HERE, "part1_dungeons_benchmark.json")
    d2 = json.load(open(fn2, encoding="utf-8"))
    cleared = dead = 0
    for name, dd in d2["dungeons"].items():
        g = dd["grid"]
        sim, worst, acts, wturn, wlate = play(g)
        if sim.status == "CLEARED":
            cleared += 1
        if sim.status == "DEAD":
            dead += 1
        print("  part1 %-12s %-8s T=%3d hp=%3d keys=%s D=%5.1f step=%.4f@t%d late=%.4f" %
              (name, sim.status, sim.win_turn or sim.turn - 1, sim.h["hp"],
               sim.h["keys"], sim.trap_damage, worst, wturn, wlate))
    print("part1 summary: cleared=%d dead=%d total=%d" %
          (cleared, dead, len(d2["dungeons"])))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "own"):
        check_own()
    if which in ("all", "golden"):
        golden()
    if which in ("all", "bench"):
        benchmarks()
