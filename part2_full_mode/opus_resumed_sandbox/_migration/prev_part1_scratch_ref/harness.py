import sys, json, time, copy, random
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\opus")
import importlib
import submission as S

COST = {"EMPTY": 0, "K1": 0, "K2": 0, "V": 0, "W": 5, "T_W": 25, "ICE": 10, "PIT": 40, "CRACK": 20,
        "SWITCH": 30, "R_GATE": 20, "B_GATE": 20, "TNT": 40, "BOX": 30, "HEAL": 30, "MIMIC": 60}
for k in ("MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW"): COST[k] = 25
for k in ("SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R"): COST[k] = 35
for k in ("LASER_U", "LASER_D", "LASER_L", "LASER_R"): COST[k] = 75
for k in ("PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B"): COST[k] = 40


def validate(grid):
    assert len(grid) == 26 and all(len(r) == 40 for r in grid)
    cost = 0
    cnt = {}
    for y in range(26):
        for x in range(40):
            c = grid[y][x]
            assert c in COST, c
            if x in (0, 39) or y in (0, 25):
                assert c == "T_W"
                continue
            cost += COST[c]
            cnt[c] = cnt.get(c, 0) + 1
            if 1 <= x <= 3 and 12 <= y <= 14:
                assert c == "EMPTY"
    assert cnt.get("T_W", 0) <= 120
    lim = lambda ks: sum(cnt.get(k, 0) for k in ks)
    assert lim([k for k in COST if k.startswith("LASER")]) <= 12
    assert lim([k for k in COST if k.startswith("MIRROR")]) <= 30
    assert lim([k for k in COST if k.startswith("SPRING")]) <= 20
    assert cnt.get("CRACK", 0) <= 40 and cnt.get("SWITCH", 0) <= 6
    assert lim(["R_GATE", "B_GATE"]) <= 16 and cnt.get("TNT", 0) <= 12
    assert cnt.get("BOX", 0) <= 4 and cnt.get("HEAL", 0) <= 4 and cnt.get("MIMIC", 0) <= 4
    for k in ("K1", "K2", "V"):
        assert cnt.get(k, 0) == 1
    pos = {grid[y][x]: (x, y) for y in range(26) for x in range(40) if grid[y][x] in ("K1", "K2", "V")}
    k1, k2, v = pos["K1"], pos["K2"], pos["V"]
    assert 12 <= k1[0] <= 34 and 2 <= k1[1] <= 10
    assert 12 <= k2[0] <= 34 and 15 <= k2[1] <= 23
    assert abs(k1[0] - k2[0]) + abs(k1[1] - k2[1]) >= 12
    assert 33 <= v[0] <= 37 and 4 <= v[1] <= 21
    assert S.bind_clues(grid) is not None
    assert cost <= 3000
    return cost, pos


def view(game, mode="BLIND"):
    hx, hy = game.hx, game.hy
    vis = [[False] * 40 for _ in range(26)]
    def isw(x, y):
        return game.wall(x, y)
    def V(dx, dy):
        x, y = hx + dx, hy + dy
        return 0 <= x < 40 and 0 <= y < 26 and vis[y][x]
    def op(dx, dy):
        return V(dx, dy) and not isw(hx + dx, hy + dy)
    sgn = lambda v: (v > 0) - (v < 0)
    cells = [(dx, dy) for dx in range(-3, 4) for dy in range(-3, 4) if dx * dx + dy * dy <= 10]
    cells.sort(key=lambda c: max(abs(c[0]), abs(c[1])))
    for dx, dy in cells:
        x, y = hx + dx, hy + dy
        if not (0 <= x < 40 and 0 <= y < 26):
            continue
        r = max(abs(dx), abs(dy))
        sx, sy = sgn(dx), sgn(dy)
        if r <= 1:
            ok = True
        elif dx == 0 or dy == 0:
            ok = op(dx - sx, dy - sy)
        elif abs(dx) == abs(dy):
            ok = op(dx - sx, dy - sy) and not (isw(hx + sx, hy) and isw(hx, hy + sy)) if abs(dx) == 2 else op(dx - sx, dy - sy)
        elif abs(dx) > abs(dy):
            ok = op(dx - sx, dy) or op(dx - sx, dy - sy)
        else:
            ok = op(dx, dy - sy) or op(dx - sx, dy - sy)
        if ok:
            vis[y][x] = True
    # ice extension
    stack = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            x, y = hx + dx, hy + dy
            if game.T[y][x] == "ICE" or game.T[y][x].startswith("MIRROR"):
                stack.append((x, y))
    seen = set(stack)
    while stack:
        x, y = stack.pop()
        vis[y][x] = True
        for ddx, ddy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = x + ddx, y + ddy
            if 0 <= nx < 40 and 0 <= ny < 26:
                vis[ny][nx] = True
                if (nx, ny) not in seen and (game.T[ny][nx] == "ICE" or game.T[ny][nx].startswith("MIRROR")):
                    seen.add((nx, ny)); stack.append((nx, ny))
    clue_cells = set(game.clue_of.values())
    terr = [[(("CHEST" if game.T[y][x] in ("HEAL", "MIMIC") else game.T[y][x]) if vis[y][x] else "UNKNOWN") for x in range(40)] for y in range(26)]
    occ = [[(game.O[y][x] if vis[y][x] else None) for x in range(40)] for y in range(26)]
    clues = [[(vis[y][x] and (x, y) in clue_cells) for x in range(40)] for y in range(26)]
    warns = []
    if game.turn % 3 == 0:
        for y in range(26):
            for x in range(40):
                t = game.T[y][x]
                if t in S.LASERS:
                    d = S.LASERS[t]; dx, dy = S.DIRV[d]
                    for k in range(1, 11):
                        px, py = x + k * dx, y + k * dy
                        if game.wall(px, py) or game.O[py][px] is not None:
                            break
                        if vis[py][px]:
                            warns.append((py, px, d))
        warns.sort()
    return vis, terr, occ, clues, [{"x": x, "y": y, "dir": d} for (y, x, d) in warns]


def make_state(game, targets):
    vis, terr, occ, clues, warns = view(game)
    return {"turn": game.turn, "turns_left": 241 - game.turn, "mode": "BLIND",
            "hero": {"x": game.hx, "y": game.hy, "hp": game.hp, "keys": [game.k1, game.k2],
                     "jumps": game.jumps, "throws": game.throws, "bombs": game.nb},
            "gates_flipped": game.gates, "targets": targets, "visible_mask": vis, "terrain": terr,
            "occupant": occ, "bombs": [{"x": b["x"], "y": b["y"], "timer": b["timer"]} for b in game.bombs],
            "clues": clues, "laser_warnings": warns}


def run_hero(grid, decide, verbose=False, maxt=240):
    pos = {grid[y][x]: (x, y) for y in range(26) for x in range(40) if grid[y][x] in ('K1', 'K2', 'V')}
    game = S.make_game(grid)
    targets = {"K1": list(pos["K1"]), "K2": list(pos["K2"]), "V": list(pos["V"])}
    memory = {}
    worst = 0
    acts = []
    for turn in range(1, maxt + 1):
        game.turn = turn
        st = make_state(game, targets)
        t0 = time.time()
        try:
            a = decide(copy.deepcopy(st), memory)
        except Exception as e:
            import traceback; traceback.print_exc(); a = "WAIT"
        dt = time.time() - t0
        worst = max(worst, dt)
        acts.append(a)
        game.act(a)
        if game.status == "ALIVE":
            game.phases()
        if verbose:
            print(turn, a, (game.hx, game.hy), game.hp, game.k1, game.k2, game.status, "%.3f" % dt)
        if game.status != "ALIVE":
            break
    return game.status, turn, game.hp, (game.k1, game.k2), worst, acts, game.trap


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

