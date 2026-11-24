"""本地 v2.2 裁判式回归靶场（仅本地测试用，非提交文件）。
用法: python local_test_v22.py [gv|bench|demon|scan|all]
"""
import ast
import copy
import importlib.util
import json
import sys
import time

spec = importlib.util.spec_from_file_location("submission", "submission.py")
sub = importlib.util.module_from_spec(spec)
t0 = time.monotonic()
spec.loader.exec_module(sub)
IMPORT_S = time.monotonic() - t0

Eng = sub.Eng
W, H = 40, 26


def blank():
    return [["T_W" if (x == 0 or x == 39 or y == 0 or y == 25) else "EMPTY"
             for x in range(W)] for y in range(H)]


def put(g, x, y, t):
    g[y][x] = t


def hero_at(x, y, **kw):
    h = {"x": x, "y": y, "hp": 100, "keys": [False, False],
         "jumps": 3, "throws": 3, "bombs": 2}
    h.update(kw)
    return h


# ---------------------------------------------------------------- golden vectors
def gv_all():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(("  OK  " if cond else "  FAIL") + " " + name + (" " + detail if detail else ""))
        if not cond:
            ok = False

    print("== GV22_01 budget & plate/pgate schema ==")
    g = blank()
    for (x, y, t) in [(20, 5, "K1"), (20, 20, "K2"), (35, 13, "V"),
                      (8, 8, "PLATE"), (6, 8, "BOX"), (34, 13, "P_GATE"),
                      (25, 2, "LASER2_D"), (10, 13, "ONEWAY_R")]:
        put(g, x, y, t)
    spent = sub._spend(g)
    e = Eng().setup(g)
    check("spent_gold==225", spent == 225, str(spent))
    check("vault_gold==2775", 3000 - spent == 2775)
    check("initial_plates_active==False", e.plates is False)
    check("layout_ok", sub._layout_ok(g))

    print("== GV22_02 plate box-only trigger ==")
    g = blank()
    put(g, 5, 13, "PLATE"); put(g, 34, 13, "P_GATE"); put(g, 7, 13, "BOX")
    put(g, 20, 5, "K1"); put(g, 20, 20, "K2"); put(g, 35, 13, "V")
    e = Eng().setup(g, hero=hero_at(4, 13))
    e.step("MOVE_R")
    check("hero on plate -> plates False", e.plates is False and (e.hx, e.hy) == (5, 13))
    check("pgate closed", e.high(13 * W + 34))
    e2 = Eng().setup(g, hero=hero_at(8, 13))
    e2.step("MOVE_L"); e2.step("MOVE_L")
    check("box on plate -> plates True", e2.plates is True)
    check("pgate open", not e2.high(13 * W + 34))

    print("== GV22_03 LCM12 instant kill ==")
    g = blank()
    put(g, 15, 8, "LASER_D"); put(g, 12, 10, "LASER2_R")
    put(g, 20, 5, "K1"); put(g, 20, 20, "K2"); put(g, 35, 13, "V")
    e = Eng().setup(g, hero=hero_at(15, 10), turn=11)
    warns = e.warnings(12)
    periods = sorted({w["period"] for w in warns if w["x"] == 15 and w["y"] == 10})
    check("warning periods [3,4]", periods == [3, 4], str(periods))
    e.step("WAIT")
    check("hp==0 DEAD", e.hp == 0 and e.status == "DEAD", "hp=%d" % e.hp)

    print("== GV22_04 oneway reverse push & mirror newdir ==")
    g = blank()
    put(g, 6, 13, "ONEWAY_L"); put(g, 6, 13, "ONEWAY_L")
    g[13][6] = "ONEWAY_L"
    g[13][5] = "CRACK"
    put(g, 7, 13, "BOX")  # box will be moved onto oneway below
    # case a: box ON ONEWAY_L(6,13)
    g2 = blank()
    put(g2, 20, 5, "K1"); put(g2, 20, 20, "K2"); put(g2, 35, 13, "V")
    g2[13][6] = "ONEWAY_L"; g2[13][5] = "CRACK"
    e = Eng().setup(g2, hero=hero_at(5, 13))
    e.occ[13 * W + 6] = "BOX"; e.box_set.add(13 * W + 6)
    e.base_occ[13 * W + 6] = "BOX"
    e.step("MOVE_R")
    check("a box stays (6,13)", e.occ[13 * W + 6] == "BOX")
    check("a hero stays (5,13)", (e.hx, e.hy) == (5, 13))
    check("a crack intact", e.ter[13 * W + 5] == "CRACK")
    # case b: mirror NE then oneway R above
    g3 = blank()
    put(g3, 20, 5, "K1"); put(g3, 20, 20, "K2"); put(g3, 35, 13, "V")
    put(g3, 10, 10, "MIRROR_NE"); put(g3, 10, 9, "ONEWAY_R")
    e = Eng().setup(g3, hero=hero_at(9, 10))
    e.step("MOVE_R")
    check("b hero rests on mirror (10,10)", (e.hx, e.hy) == (10, 10), str((e.hx, e.hy)))

    print("== GV22_05 spring & jump oneway ==")
    g = blank()
    put(g, 20, 5, "K1"); put(g, 20, 20, "K2"); put(g, 35, 13, "V")
    put(g, 10, 10, "SPRING_R"); put(g, 12, 10, "ONEWAY_L")
    e = Eng().setup(g, hero=hero_at(9, 10))
    e.step("MOVE_R")
    check("spring lands (11,10)", (e.hx, e.hy) == (11, 10), str((e.hx, e.hy)))
    g = blank()
    put(g, 20, 5, "K1"); put(g, 20, 20, "K2"); put(g, 35, 13, "V")
    put(g, 6, 14, "ONEWAY_L")
    e = Eng().setup(g, hero=hero_at(5, 14))
    e.step("JUMP_R")
    check("jump failed stays (5,14)", (e.hx, e.hy) == (5, 14))
    check("jumps_left==2", e.jumps == 2)

    print("== GV22_06 throw air pass vs ground stop ==")
    g = blank()
    put(g, 20, 5, "K1"); put(g, 20, 20, "K2"); put(g, 35, 13, "V")
    put(g, 6, 10, "ONEWAY_L"); put(g, 7, 10, "SWITCH")
    e = Eng().setup(g, hero=hero_at(5, 10))
    e.step("THROW_R")
    check("air throw flips gates", e.gates is True)
    g = blank()
    put(g, 20, 5, "K1"); put(g, 20, 20, "K2"); put(g, 35, 13, "V")
    put(g, 11, 15, "ICE"); put(g, 12, 15, "ONEWAY_L"); put(g, 13, 15, "SWITCH")
    e = Eng().setup(g, hero=hero_at(5, 15))
    e.step("THROW_R")
    check("ground slide stops, gates False", e.gates is False)

    print("== GV22_07 phase C box destruction closes P_GATE before D ==")
    g = blank()
    put(g, 20, 5, "K1"); put(g, 20, 20, "K2"); put(g, 35, 13, "V")
    put(g, 10, 10, "PLATE"); put(g, 12, 10, "P_GATE"); put(g, 15, 10, "LASER_L")
    e = Eng().setup(g, hero=hero_at(7, 10), turn=2)
    e.occ[10 * W + 10] = "BOX"; e.box_set.add(10 * W + 10)
    e.base_occ[10 * W + 10] = "BOX"
    e._plates()
    check("plates initially True", e.plates is True)
    e.bombs = [[11 * W + 10, 1]]  # explodes this turn phase C, hits box (10,10)
    e.step("WAIT")  # turn 3: red fires
    check("plates_after False", e.plates is False)
    check("hero hp 100 saved", e.hp == 100 and e.status == "ALIVE", "hp=%d" % e.hp)

    print("== GV22_08 scoring cap & 2-wide pit bridge ==")
    g = blank()
    put(g, 20, 5, "K1"); put(g, 20, 20, "K2"); put(g, 35, 13, "V")
    put(g, 20, 13, "PIT"); put(g, 21, 13, "PIT")
    put(g, 19, 13, "BOX"); put(g, 16, 13, "BOX")
    check("bridge map layout_ok", sub._layout_ok(g))
    e = Eng().setup(g, hero=hero_at(18, 13))
    e.step("MOVE_R")  # push box1 into pit1
    check("pit1 filled", e.ter[13 * W + 20] == "EMPTY" and e.occ[13 * W + 20] is None)
    e.hx, e.hy = 15, 13
    for _ in range(5):
        e.step("MOVE_R")  # push box2 across filled pit1 into pit2
    check("pit2 filled", e.ter[13 * W + 21] == "EMPTY")
    score = min(320.0, 1.7 * 100 + 150 * (240 - 1) / 239)
    check("cleared demon score cap 320", abs(score - 320.0) < 1e-9, str(score))
    check("max_author_steps==200", sub.MAX_AUTHOR_STEPS == 200)
    return ok


# ---------------------------------------------------------------- referee runner
def make_state(e, targets):
    terr = [[None] * W for _ in range(H)]
    occ = [[None] * W for _ in range(H)]
    clues = [[False] * W for _ in range(H)]
    vis = [[True] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            i = y * W + x
            t = e.ter[i]
            terr[y][x] = "CHEST" if t in ("HEAL", "MIMIC") else t
            occ[y][x] = e.occ[i]
            clues[y][x] = e.clues[i]
    return {
        "mode": "FULL", "turn": e.turn + 1,
        "hero": {"x": e.hx, "y": e.hy, "hp": e.hp,
                 "keys": [bool(e.kmask & 1), bool(e.kmask & 2)],
                 "jumps": e.jumps, "throws": e.throws, "bombs": e.bombs_left},
        "terrain": terr, "occupant": occ, "clues": clues, "visible_mask": vis,
        "targets": targets, "gates_flipped": e.gates, "plates_active": e.plates,
        "laser_warnings": e.warnings(e.turn + 1),
    }


def run_hero(grid, label, max_turns=240, verbose=False):
    targets = {}
    for y in range(H):
        for x in range(W):
            if grid[y][x] in ("K1", "K2", "V"):
                targets[grid[y][x]] = [x, y]
    e = Eng().setup(grid)
    memory = {}
    max_dt = 0.0
    total_dt = 0.0
    errors = 0
    status = "TIMEOUT"
    for t in range(1, max_turns + 1):
        st = make_state(e, targets)
        t0 = time.monotonic()
        try:
            a = sub.decide_action(st, memory)
        except Exception as ex:
            errors += 1
            a = "WAIT"
            if verbose:
                print("   exception turn", t, ex)
        dt = time.monotonic() - t0
        max_dt = max(max_dt, dt)
        total_dt += dt
        limit = 2.0 if t == 1 else 0.5
        if dt > limit:
            errors += 1
            if verbose:
                print("   TIMEOUT turn", t, "%.3fs" % dt)
            a = "WAIT"
        if a not in sub.VALID_ACTIONS:
            errors += 1
            a = "WAIT"
        e.step(a)
        if verbose and t % 40 == 0:
            print("   t%d pos=(%d,%d) hp%d keys%d" % (t, e.hx, e.hy, e.hp, e.kmask))
        if e.status != "ALIVE":
            status = e.status
            break
    g = (3000 - sub._spend(grid)) / 3000.0
    if status == "CLEARED":
        score = 600 + 1.5 * e.hp + 150 * (240 - e.turn) / 239 + 100 * g
    else:
        score = 200 * bin(e.kmask).count("1") + 200 * (e.hp / 100.0)
    print("%-14s %-8s T=%3d HP=%3d keys=%d err=%d max_dt=%.3fs avg=%.4fs score~%.1f"
          % (label, status, e.turn, e.hp, bin(e.kmask).count("1"), errors, max_dt,
             total_dt / max(1, e.turn), score))
    return status, e.turn, e.hp, errors, max_dt


def bench_all():
    sp = json.load(open("v22_sparring_benchmarks.json", encoding="utf-8"))
    p1 = json.load(open("part1_dungeons_benchmark.json", encoding="utf-8"))
    print("== v2.2 sparring benchmarks ==")
    for name in ("BENCH_WEAK", "BENCH_STRONG"):
        run_hero(sp["dungeons"][name]["grid"], name, verbose=False)
    print("== part1 regression (14 maps, FULL mode) ==")
    for name, dg in p1["dungeons"].items():
        run_hero(dg["grid"], name)


def demon_check():
    print("== demon build compliance ==")
    t0 = time.monotonic()
    d = sub.build_dungeon()
    bt = time.monotonic() - t0
    print("build time %.3fs" % bt)
    grid = d["grid"]
    sol = d["author_solution"]
    print("taunt(%d): %s" % (len(d["taunt"]), d["taunt"]))
    print("spent=%d vault_g=%.3f author_steps=%d" % (sub._spend(grid),
          (3000 - sub._spend(grid)) / 3000.0, len(sol)))
    assert len(d["taunt"]) <= 40
    assert sub._layout_ok(grid), "layout invalid"
    assert sub._spawn_admission(grid), "spawn admission failed"
    assert 1 <= len(sol) <= 200
    e = Eng().setup(grid)
    st = e.run(sol)
    assert st == "CLEARED" and e.turn == len(sol) and e.hp > 0, (st, e.turn, e.hp)
    print("author replay: CLEARED turn=%d hp=%d trap_damage=%d" % (e.turn, e.hp, e.trap_damage))
    d2 = sub.build_dungeon()
    assert d2["grid"] == grid and d2["author_solution"] == sol, "non-deterministic build"
    print("determinism OK")
    print("== self-play (own hero vs own demon) ==")
    run_hero(grid, "SELF", verbose=False)
    # ascii dump
    sym = {"EMPTY": ".", "T_W": "#", "W": "+", "K1": "1", "K2": "2", "V": "V",
           "PIT": "O", "CRACK": "~", "ICE": "=", "BOX": "B", "TNT": "T",
           "HEAL": "H", "MIMIC": "M", "SWITCH": "!", "R_GATE": "r", "B_GATE": "b",
           "PLATE": "_", "P_GATE": "g", "LASER_U": "^", "LASER_D": "v",
           "LASER_L": "<", "LASER_R": ">", "LASER2_U": "i", "LASER2_D": "k",
           "LASER2_L": "j", "LASER2_R": "l", "ONEWAY_U": "n", "ONEWAY_D": "s",
           "ONEWAY_L": "w", "ONEWAY_R": "e", "SPRING_U": "U", "SPRING_D": "D",
           "SPRING_L": "L", "SPRING_R": "R", "MIRROR_NE": "/", "MIRROR_SE": "\\",
           "MIRROR_SW": "/", "MIRROR_NW": "\\", "PORTAL_1A": "P", "PORTAL_1B": "P",
           "PORTAL_2A": "Q", "PORTAL_2B": "Q"}
    for y in range(H):
        print("".join(sym.get(grid[y][x], "?") for x in range(W)))
    return True


def scan():
    print("== AST compliance scan ==")
    src = open("submission.py", encoding="utf-8").read()
    tree = ast.parse(src)
    bad = []
    allowed = {"heapq", "math", "time", "collections", "queue", "array", "itertools",
               "copy", "random", "json", "bisect", "numpy", "networkx", "sympy", "mpmath"}
    banned_calls = {"eval", "exec", "getattr", "setattr", "delattr", "open", "compile",
                    "input", "vars", "globals", "locals", "breakpoint"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name.startswith("__"):
                bad.append("dunder def " + node.name)
        elif isinstance(node, ast.Name):
            if node.id.startswith("__"):
                bad.append("dunder name " + node.id)
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                bad.append("dunder attr " + node.attr)
        elif isinstance(node, ast.arg):
            if node.arg.startswith("__"):
                bad.append("dunder arg " + node.arg)
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in allowed:
                    bad.append("import " + a.name)
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in allowed:
                bad.append("from " + str(node.module))
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id in banned_calls:
                bad.append("call " + f.id)
            if isinstance(f, ast.Attribute) and f.attr in {"system", "popen"}:
                bad.append("call ." + f.attr)
    if bad:
        print("  FAIL:", bad[:20])
        return False
    print("  OK: no dunder names/attrs, no banned imports/calls")
    print("import time %.3fs (limit 1.5s)" % IMPORT_S)
    return True


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    results = []
    if mode in ("gv", "all"):
        results.append(("golden_vectors", gv_all()))
    if mode in ("scan", "all"):
        results.append(("ast_scan", scan()))
    if mode in ("demon", "all"):
        results.append(("demon", demon_check()))
    if mode in ("bench", "all"):
        bench_all()
    print("== summary ==")
    for name, ok in results:
        print(("PASS " if ok else "FAIL ") + name)