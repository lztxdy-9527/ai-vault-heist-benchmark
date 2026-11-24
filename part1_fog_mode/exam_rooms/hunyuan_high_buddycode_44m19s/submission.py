"""
《阴间地牢：金库攻防战》 submission.py

build_dungeon()   : 魔王造图 + 自证通关解
decide_action()   : BLIND 迷雾增量建图 / 物理预判 / 避险寻路
"""
import heapq
import collections

W = 40
H = 26
INF = 1e18

DIRS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
VEC2DIR = {(0, -1): "U", (0, 1): "D", (-1, 0): "L", (1, 0): "R"}
HIGH = {"W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R"}
MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}
VALID_ACTIONS = (
    "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT",
    "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
    "THROW_U", "THROW_D", "THROW_L", "THROW_R", "BOMB",
)
NEI4 = ((0, -1), (0, 1), (-1, 0), (1, 0))


# ==============================================================================
# 魔王：建图与自证
# ==============================================================================

def _wall_blocks(t, flipped=False):
    if t in HIGH:
        return True
    if t == "R_GATE" and not flipped:
        return True
    if t == "B_GATE" and flipped:
        return True
    return False


def _laser_beams(grid):
    """All cells lit by laser cannons in the initial (static) snapshot."""
    beams = set()
    for y in range(H):
        for x in range(W):
            t = grid[y][x]
            if t not in ("LASER_U", "LASER_D", "LASER_L", "LASER_R"):
                continue
            dx, dy = DIRS[t[-1]]
            for k in range(1, 11):
                cx, cy = x + k * dx, y + k * dy
                if not (0 <= cx < W and 0 <= cy < H):
                    break
                if _wall_blocks(grid[cy][cx]):
                    break
                beams.add((cx, cy))
    return beams


def _safe_bfs(grid, start, goal, forbidden):
    q = collections.deque([start])
    prev = {start: None}
    allowed = {"EMPTY", "K1", "K2", "V"}
    while q:
        p = q.popleft()
        if p == goal:
            out = []
            while p is not None:
                out.append(p)
                p = prev[p]
            return out[::-1]
        x, y = p
        for dx, dy in NEI4:
            n = (x + dx, y + dy)
            if not (0 <= n[0] < W and 0 <= n[1] < H) or n in prev or n in forbidden:
                continue
            if grid[n[1]][n[0]] not in allowed:
                continue
            prev[n] = p
            q.append(n)
    return None


def _hash_key(p):
    x, y = p
    h = (x * 374761393 + y * 668265263 + x * y * 1274126177
         + x * x * 69069 + y * y * 12345) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return h


def build_dungeon() -> dict:
    grid = [
        ["T_W" if (x == 0 or x == W - 1 or y == 0 or y == H - 1) else "EMPTY"
         for x in range(W)]
        for y in range(H)
    ]

    # 四道横向隔离墙，缺口左右交替，强制长蛇形绕行。
    barriers = [(4, 38), (8, 1), (17, 38), (21, 1)]
    for by, gap in barriers:
        for x in range(1, W - 1):
            grid[by][x] = "W"
        grid[by][gap] = "EMPTY"

    k1 = (14, 2)
    k2 = (20, 18)
    vault = (37, 13)

    # 激光炮沿各条开阔带横扫，射线格在自证路径中一律视为禁区。
    lasers = [
        (4, 5, "LASER_R"), (34, 7, "LASER_L"),
        (4, 11, "LASER_R"), (34, 11, "LASER_L"),
        (4, 19, "LASER_R"), (34, 19, "LASER_L"),
        (4, 23, "LASER_R"),
    ]
    for lx, ly, lt in lasers:
        if grid[ly][lx] == "EMPTY":
            grid[ly][lx] = lt

    grid[k1[1]][k1[0]] = "K1"
    grid[k2[1]][k2[0]] = "K2"
    grid[vault[1]][vault[0]] = "V"

    beams = _laser_beams(grid)

    # 先求出一条完全避开射线与所有非平地格的黄金安全走廊。
    forbidden = set(beams)
    for t_pos in (k2, vault):
        forbidden.add(t_pos)
    seg1 = _safe_bfs(grid, (2, 13), k1, forbidden)
    forbidden2 = set(beams)
    forbidden2.add(vault)
    seg2 = _safe_bfs(grid, k1, k2, forbidden2)
    forbidden3 = set(beams)
    seg3 = _safe_bfs(grid, k2, vault, forbidden3)
    if not seg1 or not seg2 or not seg3:
        # 极端情况下退化为最短 BFS（不避开射线），保证结构合法。
        seg1 = _safe_bfs(grid, (2, 13), k1, {k2, vault})
        seg2 = _safe_bfs(grid, k1, k2, {vault})
        seg3 = _safe_bfs(grid, k2, vault, set())
    golden = set(seg1) | set(seg2) | set(seg3)

    # 只在不影响自证走廊的区域铺设陷阱。
    cands = []
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            if (x, y) in golden or grid[y][x] != "EMPTY":
                continue
            if 1 <= x <= 3 and 12 <= y <= 14:
                continue
            cands.append((x, y))
    cands.sort(key=_hash_key)

    reserved = set()
    mimics = []
    # 宝箱怪：上方必须预留合法专属骸骨线索格。
    for p in cands:
        if len(mimics) >= 3:
            break
        x, y = p
        clue = (x, y - 1)
        if not (0 <= clue[0] < W and 0 <= clue[1] < H):
            continue
        if grid[clue[1]][clue[0]] != "EMPTY" or clue in golden:
            continue
        if 1 <= clue[0] <= 3 and 12 <= clue[1] <= 14:
            continue
        bad = False
        for dx, dy in NEI4:
            c = (clue[0] + dx, clue[1] + dy)
            if c == p:
                continue
            if grid[c[1]][c[0]] in ("HEAL", "MIMIC") or c in reserved:
                bad = True
                break
        if bad:
            continue
        # 线索格的四邻不得存在其它宝箱
        other = False
        for dx, dy in NEI4:
            c = (clue[0] + dx, clue[1] + dy)
            if c != p and grid[c[1]][c[0]] in ("HEAL", "MIMIC"):
                other = True
        if other:
            continue
        mimics.append(p)
        reserved.add(p)
        reserved.add(clue)

    for p in mimics:
        grid[p[1]][p[0]] = "MIMIC"

    pit_positions = []
    ice_positions = []
    crack_positions = []
    for p in cands:
        if p in reserved or grid[p[1]][p[0]] != "EMPTY":
            continue
        if len(pit_positions) < 8:
            pit_positions.append(p)
            reserved.add(p)
    for p in pit_positions:
        grid[p[1]][p[0]] = "PIT"
        # 冰道 -> 深渊 诱杀链：从左侧滑入深渊
        for k in (1, 2, 3):
            c = (p[0] - k, p[1])
            if (0 < c[0] < W - 1 and 0 < c[1] < H - 1 and c not in golden
                    and c not in reserved and grid[c[1]][c[0]] == "EMPTY"
                    and len(ice_positions) < 24):
                ice_positions.append(c)
                reserved.add(c)
    for p in ice_positions:
        grid[p[1]][p[0]] = "ICE"

    for p in cands:
        if len(crack_positions) >= 38:
            break
        if p in reserved or grid[p[1]][p[0]] != "EMPTY":
            continue
        crack_positions.append(p)
        reserved.add(p)
        grid[p[1]][p[0]] = "CRACK"

    # 用最终地形重新求路（所有陷阱格都不可走），生成自证动作序列。
    forbidden = set(beams)
    forbidden.add(k2)
    forbidden.add(vault)
    s1 = _safe_bfs(grid, (2, 13), k1, forbidden)
    forbidden = set(beams)
    forbidden.add(vault)
    s2 = _safe_bfs(grid, k1, k2, forbidden)
    s3 = _safe_bfs(grid, k2, vault, set(beams))
    if not s1 or not s2 or not s3:
        s1, s2, s3 = seg1, seg2, seg3

    path = s1 + s2[1:] + s3[1:]
    actions = []
    for i in range(1, len(path)):
        dx = path[i][0] - path[i - 1][0]
        dy = path[i][1] - path[i - 1][1]
        actions.append("MOVE_" + VEC2DIR[(dx, dy)])
    if len(actions) > 240:
        actions = actions[:240]

    return {
        "taunt": "迷雾里的捷径都是我挖的坑",
        "grid": grid,
        "author_solution": actions,
    }


# ==============================================================================
# 勇者：BLIND 迷雾决策
# ==============================================================================

def _init_memory(mem):
    # 最外圈恒为免费钛金墙，属于已知先验，避免把越界格当成可通行 UNKNOWN
    mem["known"] = [
        ["T_W" if (x == 0 or x == W - 1 or y == 0 or y == H - 1) else "UNKNOWN"
         for x in range(W)]
        for y in range(H)
    ]
    mem["beam"] = {}
    mem["beam_lines"] = set()
    mem["cannons"] = {}
    mem["clue_cells"] = set()
    mem["visited"] = {}
    mem["stuck"] = 0
    mem["turn"] = 0
    mem["last_goal"] = None
    mem["plan_goal"] = None
    mem["recent"] = []
    mem["best_metric"] = None
    mem["stagnation"] = 0
    mem["metric_goal"] = None
    mem["wander_until"] = 0
    mem["unreachable_streak"] = 0


def _known_high(known, x, y, flipped):
    if not (0 <= x < W and 0 <= y < H):
        return True
    t = known[y][x]
    if t in HIGH:
        return True
    if t == "R_GATE" and not flipped:
        return True
    if t == "B_GATE" and flipped:
        return True
    return False


def _enter_cost(known, occ, clue_cells, tnt_danger, beam, x, y, flipped):
    t = known[y][x]
    if t == "PIT":
        return INF
    if t in ("W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R"):
        return INF
    if occ[y][x] == "TNT":
        return INF
    if t == "UNKNOWN":
        c = 1.15
    elif t == "CHEST":
        c = 24.0
        for dx, dy in NEI4:
            if (x + dx, y + dy) in clue_cells:
                c = INF
                break
    elif t == "ICE" or t.startswith("MIRROR_"):
        c = 7.0
    elif t.startswith("SPRING_") or t.startswith("PORTAL_"):
        c = 6.0
    elif t == "CRACK":
        c = 2.2
    elif t == "SWITCH":
        c = 1.6
    elif t == "R_GATE" or t == "B_GATE":
        c = 13.0
    else:
        c = 1.0
    if c >= INF:
        return INF
    if occ[y][x] == "BOX":
        c += 7.0
    if (x, y) in tnt_danger:
        c += 9.0
    if (x, y) in beam:
        c += 2.5
    return c


def _dijkstra(known, occ, clue_cells, tnt_danger, beam, start, flipped):
    dist = [[INF] * W for _ in range(H)]
    sx, sy = start
    if not (0 <= sx < W and 0 <= sy < H):
        return dist
    dist[sy][sx] = 0.0
    pq = [(0.0, sx, sy)]
    while pq:
        d, x, y = heapq.heappop(pq)
        if d > dist[y][x] + 1e-9:
            continue
        for dx, dy in NEI4:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            c = _enter_cost(known, occ, clue_cells, tnt_danger, beam, nx, ny, flipped)
            if c >= INF:
                continue
            nd = d + c
            if nd + 1e-9 < dist[ny][nx]:
                dist[ny][nx] = nd
                heapq.heappush(pq, (nd, nx, ny))
    return dist


def _recompute_beams(mem, known, occ, state):
    """Accumulate remembered laser beams from warnings and from known cannon tiles."""
    flipped = state.get("gates_flipped", False)
    beam = mem["beam"]
    for (cx, cy), dr in list(mem["cannons"].items()):
        if known[cy][cx] not in ("LASER_U", "LASER_D", "LASER_L", "LASER_R"):
            continue
        dx, dy = DIRS[dr]
        for k in range(1, 11):
            x, y = cx + k * dx, cy + k * dy
            if not (0 <= x < W and 0 <= y < H):
                break
            t = known[y][x]
            # 门可能被开关临时打开，按最坏情况把整条射线都记下来
            if t in ("W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R"):
                break
            if occ[y][x] == "BOX":
                break
            beam.setdefault((x, y), set()).add((cx, cy))
            if occ[y][x] == "TNT":
                break


def _simulate(act, ctx):
    """Predict the hero's own phase-A/B chain plus immediate phase-C/D hazards."""
    known = ctx["known"]
    occ = ctx["occ"]
    hx, hy = ctx["pos"]
    hp = ctx["hp"]
    keys = list(ctx["keys"])
    flipped = ctx["flipped"]
    beam = ctx["beam"]
    turn = ctx["turn"]
    tnt_cells = ctx["tnt_cells"]
    portal_map = ctx["portals"]
    start = (hx, hy)
    exposed = {start}
    pos = start
    damage = 0
    dead = False
    win = False
    keys_gain = 0
    flip = flipped
    moved = False
    used_jump = act.startswith("JUMP_")
    used_throw = act.startswith("THROW_")
    used_bomb = act == "BOMB"
    cleared_override = None   # occupant temporarily freed (pushed BOX)

    def khigh(x, y):
        return _known_high(known, x, y, flip)

    def occ_at(p):
        if p == cleared_override:
            return None
        return occ[p[1]][p[0]] if 0 <= p[0] < W and 0 <= p[1] < H else None

    def passable(p):
        x, y = p
        if not (0 <= x < W and 0 <= y < H) or khigh(x, y):
            return False
        return occ_at(p) not in ("BOX", "TNT")

    def terrain_at(p):
        t = known[p[1]][p[0]]
        return "EMPTY" if t == "UNKNOWN" else t

    def chain(p0, p1, d):
        nonlocal pos, damage, dead, win, keys_gain, flip, moved
        steps = 0
        portals = 0
        suppress = False
        cur = p1
        prev = p0
        while True:
            steps += 1
            pos = cur
            exposed.add(cur)
            moved = pos != start
            t = terrain_at(cur)
            stop = False
            if t == "PIT":
                damage += 100
                dead = True
                return
            if t == "CHEST":
                damage += 45
                stop = True
            elif t == "SWITCH":
                flip = not flip
            elif t == "K1":
                if not keys[0]:
                    keys[0] = True
                    keys_gain += 1
            elif t == "K2":
                if not keys[1]:
                    keys[1] = True
                    keys_gain += 1
            elif t == "V":
                if keys[0] and keys[1] and hp - damage > 0:
                    win = True
                    return
            if steps >= 32 or stop:
                return
            dx, dy = d
            if suppress:
                if portals >= 2:
                    return
                nxt = (cur[0] + dx, cur[1] + dy)
                if passable(nxt):
                    prev, cur = cur, nxt
                    suppress = False
                    continue
                return
            if t == "ICE" or t.startswith("MIRROR_"):
                if t.startswith("MIRROR_"):
                    d = DIRS[MIRROR_MAP[t][VEC2DIR[d]]]
                    dx, dy = d
                nxt = (cur[0] + dx, cur[1] + dy)
                if passable(nxt):
                    prev, cur = cur, nxt
                    continue
                return
            if t.startswith("SPRING_"):
                d = DIRS[t[-1]]
                dx, dy = d
                land = None
                for k in (1, 2, 3):
                    pk = (cur[0] + k * dx, cur[1] + k * dy)
                    blocked = khigh(*pk) or occ_at(pk) in ("BOX", "TNT")
                    if blocked:
                        if k == 1:
                            return
                        land = (cur[0] + (k - 1) * dx, cur[1] + (k - 1) * dy)
                        break
                if land is None:
                    land = (cur[0] + 3 * dx, cur[1] + 3 * dy)
                prev, cur = cur, land
                continue
            if t.startswith("PORTAL_") and cur in portal_map:
                pair = portal_map[cur]
                if occ_at(pair) in ("BOX", "TNT"):
                    return
                portals += 1
                prev, cur = cur, pair
                suppress = True
                continue
            return

    if act.startswith("MOVE_"):
        d = DIRS[act[-1]]
        p1 = (hx + d[0], hy + d[1])
        if not khigh(*p1) and occ_at(p1) != "TNT":
            if occ_at(p1) == "BOX":
                p2 = (hx + 2 * d[0], hy + 2 * d[1])
                if passable(p2):
                    cleared_override = p1
                    chain(start, p1, d)
            else:
                chain(start, p1, d)
    elif act.startswith("JUMP_"):
        if ctx["jumps"] > 0:
            d = DIRS[act[-1]]
            p1 = (hx + d[0], hy + d[1])
            p2 = (hx + 2 * d[0], hy + 2 * d[1])
            if (not khigh(*p1) and not khigh(*p2)
                    and occ_at(p2) not in ("BOX", "TNT")):
                chain(start, p2, d)
    elif act.startswith("THROW_"):
        if ctx["throws"] > 0:
            d = DIRS[act[-1]]
            dx, dy = d
            sx, sy = hx, hy
            left = 6
            sp = 0
            while left > 0:
                sx += dx
                sy += dy
                left -= 1
                if not (0 <= sx < W and 0 <= sy < H):
                    break
                if khigh(sx, sy) or occ[sy][sx] == "BOX":
                    break
                if occ[sy][sx] == "TNT":
                    break
                t = terrain_at((sx, sy))
                if t == "SWITCH":
                    flip = not flip
                    break
                if t == "MIMIC":
                    break
                if t.startswith("MIRROR_"):
                    d = DIRS[MIRROR_MAP[t][VEC2DIR[(dx, dy)]]]
                    dx, dy = d
                elif t.startswith("PORTAL_") and (sx, sy) in portal_map and sp < 2:
                    sx, sy = portal_map[(sx, sy)]
                    sp += 1
                    if sp == 2:
                        break

    if not win:
        # 激光（阶段 D）：暴露轨迹与已记录射线格相交即可能受 50 点/门伤害
        if turn % 3 == 0:
            hit_sources = set()
            for c in exposed:
                if c in beam:
                    hit_sources |= beam[c]
            if hit_sources:
                damage += 50 * len(hit_sources)
        # 炸弹（阶段 C）：timer==1 的炸弹本回合末爆炸
        for b in state_bombs(ctx):
            tx, ty, tm = b
            if abs(pos[0] - tx) <= 1 and abs(pos[1] - ty) <= 1:
                if tm == 1:
                    damage += 50
                elif tm == 2:
                    damage += 30
        # 激光点燃 TNT 的爆炸波及
        if turn % 3 == 0:
            for (tx, ty) in tnt_cells:
                if (tx, ty) in beam and abs(pos[0] - tx) <= 1 and abs(pos[1] - ty) <= 1:
                    damage += 60
    if hp - damage <= 0:
        dead = True

    return {
        "pos": pos, "damage": damage, "dead": dead, "win": win,
        "keys_gain": keys_gain, "moved": moved, "flip": flip,
        "exposed": exposed, "used_jump": used_jump,
        "used_throw": used_throw, "used_bomb": used_bomb,
    }


def state_bombs(ctx):
    return ctx["bomb_list"]


def _unknown_around(known, pos, radius=3):
    x0, y0 = pos
    n = 0
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy > radius * radius + 1:
                continue
            x, y = x0 + dx, y0 + dy
            if 0 <= x < W and 0 <= y < H and known[y][x] == "UNKNOWN":
                n += 1
    return n


def _decide(state, memory):
    mem = memory
    if "known" not in mem:
        _init_memory(mem)

    hero = state["hero"]
    hx, hy = int(hero["x"]), int(hero["y"])
    hp = int(hero["hp"])
    keys = [bool(hero["keys"][0]), bool(hero["keys"][1])]
    turn = int(state["turn"])
    flipped = bool(state.get("gates_flipped", False))
    known = mem["known"]
    terr = state["terrain"]
    occ_grid = state["occupant"]
    mask = state["visible_mask"]
    clues = state["clues"]
    warnings = state.get("laser_warnings") or []

    # ---- 增量建图 ----
    tnt_cells = set()
    portals = {}
    pcoord = {}
    for y in range(H):
        row = terr[y]
        crow = clues[y] if y < len(clues) else [False] * W
        mrow = mask[y]
        orow = occ_grid[y] if y < len(occ_grid) else [None] * W
        krow = known[y]
        for x in range(W):
            if mrow[x]:
                t = row[x]
                krow[x] = t
                if t in ("LASER_U", "LASER_D", "LASER_L", "LASER_R"):
                    mem["cannons"][(x, y)] = t[-1]
                elif (x, y) in mem["cannons"] and t != "UNKNOWN":
                    mem["cannons"].pop((x, y), None)
                if orow[x] == "TNT":
                    tnt_cells.add((x, y))
                if crow[x]:
                    mem["clue_cells"].add((x, y))
                if t.startswith("PORTAL_"):
                    pcoord[t] = (x, y)
    for n in ("1", "2"):
        a, b = "PORTAL_%sA" % n, "PORTAL_%sB" % n
        if a in pcoord and b in pcoord:
            portals[pcoord[a]] = pcoord[b]
            portals[pcoord[b]] = pcoord[a]
    # 记住全部见过的传送门端点
    if "portal_seen" not in mem:
        mem["portal_seen"] = {}
    for t, p in pcoord.items():
        mem["portal_seen"][t] = p
    for n in ("1", "2"):
        a, b = "PORTAL_%sA" % n, "PORTAL_%sB" % n
        if a in mem["portal_seen"] and b in mem["portal_seen"]:
            portals[mem["portal_seen"][a]] = mem["portal_seen"][b]
            portals[mem["portal_seen"][b]] = mem["portal_seen"][a]

    _recompute_beams(mem, known, occ_grid, state)
    for w in warnings:
        wx, wy, wd = int(w["x"]), int(w["y"]), w["dir"]
        c = (wx, wy)
        if c not in mem["beam"]:
            mem["beam"].setdefault(c, set()).add(("w", wd))
        # 由射线格反推整条炮线，提前把可能致命的行/列纳入风险集
        lines = mem["beam_lines"]
        if wd in ("L", "R"):
            for xx in range(max(1, wx - 10), min(W - 2, wx + 10) + 1):
                lines.add((xx, wy))
        else:
            for yy in range(max(1, wy - 10), min(H - 2, wy + 10) + 1):
                lines.add((wx, yy))

    key = (hx, hy)
    mem["visited"][key] = mem["visited"].get(key, 0) + 1
    mem["turn"] = turn

    # ---- 目标选择 ----
    targets = state["targets"]
    t1 = (int(targets["K1"][0]), int(targets["K1"][1]))
    t2 = (int(targets["K2"][0]), int(targets["K2"][1]))
    tv = (int(targets["V"][0]), int(targets["V"][1]))

    tnt_danger = set()
    for (tx, ty) in tnt_cells:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                tnt_danger.add((tx + dx, ty + dy))
    beam_cells = mem["beam"]
    occ = occ_grid

    from_hero = _dijkstra(known, occ, mem["clue_cells"], tnt_danger,
                          beam_cells, (hx, hy), flipped)
    if keys[0] and keys[1]:
        goal = tv
        mem["plan_goal"] = None
    elif keys[0]:
        goal = t2
        mem["plan_goal"] = None
    elif keys[1]:
        goal = t1
        mem["plan_goal"] = None
    else:
        # 锁定第一个目标，避免在两把钥匙之间来回摇摆
        pg = mem.get("plan_goal")
        if pg not in (t1, t2):
            d1 = from_hero[t1[1]][t1[0]]
            d2 = from_hero[t2[1]][t2[0]]
            pg = t1 if d1 <= d2 else t2
            mem["plan_goal"] = pg
            mem["unreachable_streak"] = 0
        elif mem.get("unreachable_streak", 0) >= 25:
            other = t2 if pg == t1 else t1
            if from_hero[other[1]][other[0]] < INF:
                pg = other
                mem["plan_goal"] = pg
                mem["unreachable_streak"] = 0
        goal = pg
    mem["last_goal"] = goal

    # 停滞检测：距目标代价长期不下降时切换到「前沿探索」模式
    raw_goal_dist = from_hero[goal[1]][goal[0]]
    goal_unreachable = raw_goal_dist >= INF
    if goal_unreachable:
        mem["unreachable_streak"] = mem.get("unreachable_streak", 0) + 1
    else:
        mem["unreachable_streak"] = 0
    metric = raw_goal_dist
    if goal_unreachable:
        metric = 500.0 + abs(hx - goal[0]) + abs(hy - goal[1])
    if mem.get("metric_goal") != goal:
        mem["metric_goal"] = goal
        mem["best_metric"] = metric
        mem["stagnation"] = 0
        mem["wander_until"] = 0
    elif metric < mem["best_metric"] - 0.6:
        mem["best_metric"] = metric
        mem["stagnation"] = 0
    else:
        mem["stagnation"] += 1
    far_from_goal = abs(hx - goal[0]) + abs(hy - goal[1]) > 5
    if mem["stagnation"] >= 7 and far_from_goal:
        mem["wander_until"] = turn + 6
        mem["stagnation"] = 0
    wander = mem.get("wander_until", 0) > turn and far_from_goal

    dg = _dijkstra(known, occ, mem["clue_cells"], tnt_danger,
                   beam_cells, goal, flipped)

    ctx = {
        "known": known, "occ": occ, "pos": (hx, hy), "hp": hp, "keys": keys,
        "flipped": flipped, "beam": beam_cells, "turn": turn,
        "tnt_cells": tnt_cells, "portals": portals,
        "jumps": int(hero["jumps"]), "throws": int(hero["throws"]),
        "bombs": int(hero["bombs"]),
        "state": state,
    }
    ctx["bomb_list"] = [(int(b["x"]), int(b["y"]), int(b["timer"]))
                        for b in (state.get("bombs") or [])]

    candidates = ["MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT"]
    if ctx["jumps"] > 1:
        candidates += ["JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R"]
    if ctx["throws"] > 0:
        candidates += ["THROW_U", "THROW_D", "THROW_L", "THROW_R"]
    if ctx["bombs"] > 0:
        candidates.append("BOMB")

    results = {}
    for act in candidates:
        results[act] = _simulate(act, ctx)

    stuck = mem["stuck"]
    recent = mem["recent"]
    recent_all = set(recent)
    cycle = len(recent) >= 4 and len(set(recent[-4:])) <= 2
    recent_penalty = 60.0 if cycle else 8.0
    start_unknown = _unknown_around(known, (hx, hy))
    best_act = "WAIT"
    best_score = -1e30
    for act in candidates:
        r = results[act]
        p = r["pos"]
        if 0 <= p[0] < W and 0 <= p[1] < H:
            d = dg[p[1]][p[0]]
        else:
            d = INF
        blocked_goal = d >= INF
        if blocked_goal:
            d = abs(p[0] - goal[0]) + abs(p[1] - goal[1]) + 30
        if wander:
            # 短期游走：优先踏进没去过、能揭开迷雾的格子，打破势能局部极小
            score = (6.0 * (_unknown_around(known, p) - start_unknown)
                     - 9.0 * min(mem["visited"].get(p, 0), 8))
        else:
            score = -12.0 * d
            score -= 1.0 * min(mem["visited"].get(p, 0), 6)
        if blocked_goal:
            score -= 400.0
        score -= 3.0 * r["damage"]
        if r["dead"]:
            score -= 1000000.0
        if not r["moved"] and act != "BOMB" and not r["used_throw"]:
            score -= 3.0
        if p in recent_all:
            score -= recent_penalty
        score += 400.0 * r["keys_gain"]
        if r["win"]:
            score += 100000.0
        if r["used_jump"]:
            score -= 2.5
        if r["used_throw"]:
            score -= 2.0
        if r["used_bomb"]:
            score -= 6.0
        # 下回合是激光回合时，停在射线格上必然吃到下一轮的伤害
        exact_beam = p in beam_cells
        line_beam = p in mem["beam_lines"]
        if exact_beam:
            score -= 12.0
        elif line_beam:
            score -= 5.0
        future = 0.0
        if (turn + 1) % 3 == 0 and not r["win"]:
            if exact_beam:
                future = 50.0 * max(1, len(beam_cells[p]))
                score -= 60.0
            elif line_beam:
                future = 25.0
                score -= 25.0
        if future:
            score -= 3.0 * future
            if hp - r["damage"] - future <= 0:
                score -= 100000.0
        #  flip 有收益时鼓励飞石击打开关
        if r["used_throw"] and r["flip"] != flipped:
            for dx in range(-8, 9):
                for dy in range(-8, 9):
                    gx, gy = hx + dx, hy + dy
                    if 0 <= gx < W and 0 <= gy < H:
                        gt = known[gy][gx]
                        if (gt == "R_GATE" and not flipped) or (gt == "B_GATE" and flipped):
                            score += 20.0
                            break
                else:
                    continue
                break
        if score > best_score:
            best_score = score
            best_act = act

    # 卡死时尝试炸开普通砖墙
    if (not results[best_act]["moved"] and stuck >= 3 and ctx["bombs"] > 0
            and hp > 55 and any(
                known[hy + dy][hx + dx] == "W"
                for dx, dy in NEI4 if 0 <= hx + dx < W and 0 <= hy + dy < H)):
        if not any(b[2] <= 2 and abs(b[0] - hx) <= 1 and abs(b[1] - hy) <= 1
                   for b in ctx["bomb_list"]):
            best_act = "BOMB"

    if results[best_act]["moved"]:
        mem["stuck"] = 0
    else:
        mem["stuck"] = stuck + 1
    recent.append((hx, hy))
    if len(recent) > 12:
        del recent[:len(recent) - 12]
    return best_act if best_act in VALID_ACTIONS else "WAIT"


def decide_action(state: dict, memory: dict) -> str:
    try:
        return _decide(state, memory)
    except Exception:
        return "WAIT"
