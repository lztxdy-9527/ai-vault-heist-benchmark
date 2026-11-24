import sys, json, time, copy
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_06_opus_agy")
import importlib
import submission as S
importlib.reload(S)

COST = {"EMPTY": 0, "K1": 0, "K2": 0, "V": 0, "W": 5, "T_W": 25, "ICE": 10, "PIT": 40, "CRACK": 20,
        "SWITCH": 30, "R_GATE": 20, "B_GATE": 20, "TNT": 40, "BOX": 30, "HEAL": 30, "MIMIC": 60,
        "PLATE": 45, "P_GATE": 30}
for k in ("MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW"): COST[k] = 25
for k in ("SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R"): COST[k] = 35
for k in ("LASER_U", "LASER_D", "LASER_L", "LASER_R"): COST[k] = 75
for k in ("LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R"): COST[k] = 90
for k in ("ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R"): COST[k] = 30
for k in ("PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B"): COST[k] = 40


def bind_clues(grid):
    clue_of = {}
    used = set()
    for my in range(26):
        for mx in range(40):
            if grid[my][mx] != "MIMIC":
                continue
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = mx + dx, my + dy
                if grid[ny][nx] != "EMPTY" or (1 <= nx <= 3 and 12 <= ny <= 14) or (nx, ny) in used:
                    continue
                bad = any(grid[ny + ey][nx + ex] in ("HEAL", "MIMIC") and (nx + ex, ny + ey) != (mx, my)
                          for ex, ey in ((0, -1), (0, 1), (-1, 0), (1, 0)) if 0 <= nx + ex < 40 and 0 <= ny + ey < 26)
                if bad:
                    continue
                used.add((nx, ny)); clue_of[(mx, my)] = (nx, ny); break
            else:
                return None
    return clue_of


def validate(grid):
    assert len(grid) == 26 and all(len(r) == 40 for r in grid)
    cost = 0; cnt = {}
    for y in range(26):
        for x in range(40):
            c = grid[y][x]
            assert c in COST, c
            if x in (0, 39) or y in (0, 25):
                assert c == "T_W"; continue
            cost += COST[c]; cnt[c] = cnt.get(c, 0) + 1
            if 1 <= x <= 3 and 12 <= y <= 14:
                assert c == "EMPTY"
    lim = lambda ks: sum(cnt.get(k, 0) for k in ks)
    assert cnt.get("T_W", 0) <= 120, "tw"
    assert lim([k for k in COST if k.startswith("LASER")]) <= 12
    assert lim([k for k in COST if k.startswith("MIRROR")]) <= 30
    assert lim([k for k in COST if k.startswith("SPRING")]) <= 20
    assert lim([k for k in COST if k.startswith("ONEWAY")]) <= 12
    assert cnt.get("CRACK", 0) <= 40 and cnt.get("SWITCH", 0) <= 6
    assert lim(["R_GATE", "B_GATE"]) <= 16 and cnt.get("TNT", 0) <= 12
    assert cnt.get("BOX", 0) <= 6 and cnt.get("HEAL", 0) <= 4 and cnt.get("MIMIC", 0) <= 4
    assert cnt.get("PLATE", 0) <= 4 and cnt.get("P_GATE", 0) <= 8
    if cnt.get("P_GATE", 0):
        assert 1 <= cnt.get("PLATE", 0) <= cnt.get("BOX", 0), "plate/box"
    for k in ("K1", "K2", "V"):
        assert cnt.get(k, 0) == 1
    pos = {grid[y][x]: (x, y) for y in range(26) for x in range(40) if grid[y][x] in ("K1", "K2", "V")}
    k1, k2, v = pos["K1"], pos["K2"], pos["V"]
    assert 12 <= k1[0] <= 34 and 2 <= k1[1] <= 10
    assert 12 <= k2[0] <= 34 and 15 <= k2[1] <= 23
    assert abs(k1[0] - k2[0]) + abs(k1[1] - k2[1]) >= 12
    assert 33 <= v[0] <= 37 and 4 <= v[1] <= 21
    assert bind_clues(grid) is not None, "clue"
    assert cost <= 3000, cost
    return cost, pos


def admission(grid):
    acts = list(S.VALID_ACTIONS)
    good = set()
    def rec(game, depth):
        if depth == 4:
            return True
        for a in acts:
            gg = clone(game)
            gg.turn = depth + 1
            gg.act(a)
            if gg.status == "ALIVE":
                gg.phases()
            if gg.status == "DEAD" or gg.trap > 0:
                continue
            if gg.status == "WIN" or rec(gg, depth + 1):
                return True
        return False
    for a in acts:
        g = S.make_game(grid); g.turn = 1
        g.act(a)
        if g.status == "ALIVE": g.phases()
        if g.status == "DEAD" or g.trap > 0: continue
        if (g.hx, g.hy) in good: continue
        if rec(g, 1):
            good.add((g.hx, g.hy))
    return good


def clone(g):
    n = S.Game().init([r[:] for r in g.T], [r[:] for r in g.O], g.hx, g.hy, hp=g.hp, k1=g.k1, k2=g.k2,
                      jumps=g.jumps, throws=g.throws, nb=g.nb, gates=g.gates, bombs=[dict(b) for b in g.bombs], turn=g.turn)
    n.trap = g.trap
    return n


def make_state(game, targets, clue_cells):
    T = game.T
    terr = [[("CHEST" if T[y][x] in ("HEAL", "MIMIC") else T[y][x]) for x in range(40)] for y in range(26)]
    clues = [[((x, y) in clue_cells) for x in range(40)] for y in range(26)]
    warns = []
    for cells_dir in []:
        pass
    return {"turn": game.turn, "turns_left": 241 - game.turn, "mode": "FULL",
            "hero": {"x": game.hx, "y": game.hy, "hp": game.hp, "keys": [game.k1, game.k2],
                     "jumps": game.jumps, "throws": game.throws, "bombs": game.nb},
            "gates_flipped": game.gates, "plates_active": game.plates_active(), "targets": targets,
            "visible_mask": [[True] * 40 for _ in range(26)], "terrain": terr,
            "occupant": [r[:] for r in game.O], "bombs": [{"x": b["x"], "y": b["y"], "timer": b["timer"]} for b in game.bombs],
            "clues": clues, "laser_warnings": warns}


def run_hero(grid, decide, maxt=240, verbose=False):
    pos = {grid[y][x]: (x, y) for y in range(26) for x in range(40) if grid[y][x] in ("K1", "K2", "V")}
    game = S.make_game(grid)
    co = bind_clues(grid) or {}
    targets = {"K1": list(pos["K1"]), "K2": list(pos["K2"]), "V": list(pos["V"])}
    memory = {}
    worst1 = 0; worst = 0
    acts = []
    for turn in range(1, maxt + 1):
        game.turn = turn
        alive_clues = set(c for m, c in co.items() if game.T[m[1]][m[0]] == "MIMIC")
        st = make_state(game, targets, alive_clues)
        t0 = time.perf_counter()
        a = decide(copy.deepcopy(st), memory)
        dt = time.perf_counter() - t0
        if turn == 1: worst1 = dt
        else: worst = max(worst, dt)
        if dt > (2.0 if turn == 1 else 0.5):
            a = "WAIT"; memory = {}
        acts.append(a)
        game.act(a)
        if game.status == "ALIVE":
            game.phases()
        if verbose:
            print(turn, a, (game.hx, game.hy), game.hp, game.k1, game.k2, game.status, "%.3f" % dt)
        if game.status != "ALIVE":
            break
    return dict(status=game.status, turn=turn, hp=game.hp, keys=(game.k1, game.k2), w1=round(worst1, 3),
                w=round(worst, 3), trap=game.trap, acts=acts)


def replay(grid, actions):
    game = S.make_game(grid)
    for i, a in enumerate(actions):
        game.turn = i + 1
        game.act(a)
        if game.status == "ALIVE":
            game.phases()
        if game.status != "ALIVE":
            return game.status, i + 1, game.hp, game.trap
    return game.status, len(actions), game.hp, game.trap


def hero_score(r, g=0.5):
    if r["status"] == "WIN":
        return 600 + 1.5 * r["hp"] + 150 * (240 - r["turn"]) / 239 + 100 * g
    return 200 * sum(r["keys"])


def load_maps():
    d1 = json.load(open(r"part2_full_mode/exam_rooms\P2_06_opus_agy\part1_dungeons_benchmark.json", encoding="utf-8"))
    d2 = json.load(open(r"part2_full_mode/exam_rooms\P2_06_opus_agy\v22_sparring_benchmarks.json", encoding="utf-8"))
    maps = {}
    for k, v in d2["dungeons"].items():
        maps[k] = (v["grid"], v["vault_gold"] / 3000)
    for k, v in d1["dungeons"].items():
        maps[k] = (v["grid"], v["vault_gold"] / 3000)
    return maps
