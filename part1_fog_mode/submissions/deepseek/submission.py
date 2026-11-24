"""
《阴间地牢：金库攻防战》 参赛提交 (submission.py)

魔王侧：出生点"密闭处刑盒"：
  * 北侧三格深渊（挡路 / 透光 / 免疫爆炸），y=10 三门周期激光炮穿过深渊覆盖整块 3x3 出生区，
    第 3、6 回合两轮齐射即处决盒内任何存在；
  * 南侧钛金承重墙、东西钛金墙，普通炸弹无法开出缺口；
  * 东侧唯一的深渊活门只能"跳"过去，落点是一座被南北深渊、头顶独立激光炮锁死的处刑岛；
  * 岛上唯一出口由 TNT 堵死（跳跃被 W 墙挡住、走动被 TNT 挡住），必须在盒内先用飞石
    越过深渊引爆 TNT 才能炸开东侧通路 —— 这是作者自证路线才知道的开门顺序。
作者自证：64 步、50 HP 存活踏入 V。

勇者侧：BLIND 迷雾下的增量建图 + 风险加权反向 Dijkstra，
对已知深渊 / 高墙 / 宝箱怪零容忍，对未知格、冰面 / 斜坡 / 弹簧 / 传送门、激光弹道、
炸弹爆圈逐格计价；动作层再用 8 步原子位移仿真过滤单步致命，并在被彻底封死时用炸弹破墙。
"""

import heapq

GRID_W = 40
GRID_H = 26
CELLS = GRID_W * GRID_H
INF = 1e18

HIGH_WALLS = frozenset(("W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R"))
LASER_TILES = {"LASER_U": "U", "LASER_D": "D", "LASER_L": "L", "LASER_R": "R"}
MIRROR_TILES = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}
SPRING_TILES = {"SPRING_U": "U", "SPRING_D": "D", "SPRING_L": "L", "SPRING_R": "R"}
PORTALS = frozenset(("PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B"))
DIRS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
DIR_KEYS = ("U", "D", "L", "R")
MOVE_ACT = {"U": "MOVE_U", "D": "MOVE_D", "L": "MOVE_L", "R": "MOVE_R"}
JUMP_ACT = {"U": "JUMP_U", "D": "JUMP_D", "L": "JUMP_L", "R": "JUMP_R"}
VALID_ACTIONS = frozenset((
    "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT",
    "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
    "THROW_U", "THROW_D", "THROW_L", "THROW_R", "BOMB",
))


# =============================================================================
# 参赛入口 1：魔王造图与自证
# =============================================================================

K1_XY = (20, 5)
K2_XY = (20, 20)
V_XY = (35, 13)


def _blank_grid():
    grid = [["EMPTY"] * GRID_W for _ in range(GRID_H)]
    for x in range(GRID_W):
        grid[0][x] = "T_W"
        grid[GRID_H - 1][x] = "T_W"
    for y in range(GRID_H):
        grid[y][0] = "T_W"
        grid[y][GRID_W - 1] = "T_W"
    return grid


def build_dungeon() -> dict:
    grid = _blank_grid()

    # --- 激光顶棚：三门下射炮，光束穿过 y=11 的深渊覆盖整个 3x3 出生区
    grid[10][1] = "LASER_D"
    grid[10][2] = "LASER_D"
    grid[10][3] = "LASER_D"
    # 北侧闭环：深渊挡路、透光、免疫爆炸
    grid[11][1] = "PIT"
    grid[11][2] = "PIT"
    grid[11][3] = "PIT"
    # 东侧：钛金墙夹一个深渊活门
    grid[12][4] = "T_W"
    grid[13][4] = "PIT"
    grid[14][4] = "T_W"
    # 南侧：钛金承重墙
    grid[15][1] = "T_W"
    grid[15][2] = "T_W"
    grid[15][3] = "T_W"
    # --- 处刑岛：只能跳过活门抵达；南北深渊夹击，头顶独立激光炮覆盖
    grid[12][5] = "PIT"
    grid[14][5] = "PIT"
    grid[11][5] = "LASER_D"
    grid[15][5] = "T_W"
    # 岛上唯一出口被 TNT 堵死，须先从盒内用飞石越过深渊引爆
    grid[13][6] = "TNT"
    grid[12][7] = "W"
    grid[13][7] = "W"
    grid[14][7] = "W"

    grid[K1_XY[1]][K1_XY[0]] = "K1"
    grid[K2_XY[1]][K2_XY[0]] = "K2"
    grid[V_XY[1]][V_XY[0]] = "V"

    acts = [
        "MOVE_R",              # (2,13) -> (3,13)
        "THROW_R",             # 飞石越过活门深渊，引爆 (6,13) 的 TNT，炸开东侧 W 墙
        "WAIT",                # 第 3 回合顶棚齐射，盒内必吃一发
        "JUMP_R",              # 跳过活门 -> 处刑岛 (5,13)
        "MOVE_R",              # -> (6,13)
        "MOVE_R",              # -> (7,13) 出匣
    ]
    acts += ["MOVE_R"] * 13    # (8,13)  .. (20,13)
    acts += ["MOVE_U"] * 8     # (20,12) .. (20,5)  = K1
    acts += ["MOVE_D"] * 15    # (20,6)  .. (20,20) = K2
    acts += ["MOVE_R"] * 15    # (21,20) .. (35,20)
    acts += ["MOVE_U"] * 7     # (35,19) .. (35,13) = V

    return {
        "taunt": "十二模型同场？先在我盒子里躺六年再说。",
        "grid": grid,
        "author_solution": acts,
    }


# =============================================================================
# 勇者侧工具
# =============================================================================

def _is_wall(tile, flipped):
    if tile in HIGH_WALLS:
        return True
    if tile == "R_GATE":
        return not flipped
    if tile == "B_GATE":
        return flipped
    return False


def _cell_cost(tile, occ, flipped, in_beam, in_hot, hp):
    """进入该格的代价（单位≈分数：1 回合 ≈ 0.63，50 HP ≈ 75，故激光格 +33、炸弹圈 +50）。"""
    if occ == "BOX" or occ == "TNT":
        return None
    if tile is None:
        return 1.8 + (50.0 if in_hot else 0.0)
    if tile in HIGH_WALLS:
        return None
    if tile == "PIT":
        return None
    if tile == "R_GATE":
        return None if not flipped else 0.9
    if tile == "B_GATE":
        return None if flipped else 0.9
    if tile == "MIMIC":
        return 40.0
    if tile == "CHEST":
        return 2.0 if hp > 60 else 9.0
    if tile in MIRROR_TILES:
        cost = 3.5
    elif tile in SPRING_TILES:
        cost = 4.5
    elif tile == "ICE":
        cost = 2.6
    elif tile == "CRACK":
        cost = 0.9
    elif tile == "SWITCH":
        cost = 1.5
    elif tile in PORTALS:
        cost = 3.5
    else:
        cost = 0.63
    if in_beam:
        cost += 33.0
    if in_hot:
        cost += 50.0
    return cost


def _update_memory(state, memory):
    known = memory.get("k")
    if not isinstance(known, list) or len(known) != CELLS:
        known = [None] * CELLS
        memory["k"] = known
    occ_m = memory.get("o")
    if not isinstance(occ_m, list) or len(occ_m) != CELLS:
        occ_m = [None] * CELLS
        memory["o"] = occ_m
    vis = state["visible_mask"]
    ter = state["terrain"]
    occ = state["occupant"]
    clues = state["clues"]
    for y in range(GRID_H):
        vr = vis[y]
        if not vr:
            continue
        base = y * GRID_W
        tr = ter[y]
        orow = occ[y]
        for x in range(GRID_W):
            if not vr[x]:
                continue
            t = tr[x]
            if t == "UNKNOWN":
                continue
            idx = base + x
            if t == "CHEST":
                # 四邻全可见才能用骸骨线索判断真伪
                resolved = True
                mimic = False
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx = x + dx
                    ny = y + dy
                    if nx < 0 or nx >= GRID_W or ny < 0 or ny >= GRID_H:
                        continue
                    if not vis[ny][nx]:
                        resolved = False
                        break
                    if clues[ny][nx]:
                        mimic = True
                known[idx] = ("MIMIC" if mimic else "HEAL") if resolved else "CHEST"
                occ_m[idx] = None
                continue
            known[idx] = t
            occ_m[idx] = orow[x]
    return known, occ_m


def _beam_sets(known, occ_m, flipped):
    sets = []
    for idx in range(CELLS):
        dk = LASER_TILES.get(known[idx])
        if dk is None:
            continue
        x = idx % GRID_W
        y = idx // GRID_W
        dx, dy = DIRS[dk]
        cells = set()
        for step in range(1, 11):
            nx = x + dx * step
            ny = y + dy * step
            if nx < 0 or nx >= GRID_W or ny < 0 or ny >= GRID_H:
                break
            j = ny * GRID_W + nx
            t = known[j]
            if t is not None and _is_wall(t, flipped):
                break
            o = occ_m[j]
            if o == "BOX" or o == "TNT":
                break
            cells.add(j)
        if cells:
            sets.append(cells)
    return sets


def _hot_cells(state, beam_sets):
    hot = set()
    bombs = state.get("bombs") or ()
    for b in bombs:
        try:
            t = int(b["timer"])
            bx = int(b["x"])
            by = int(b["y"])
        except Exception:
            continue
        if t <= 2:
            for yy in range(by - 1, by + 2):
                for xx in range(bx - 1, bx + 2):
                    if 0 <= xx < GRID_W and 0 <= yy < GRID_H:
                        hot.add(yy * GRID_W + xx)
    # 已知 TNT 若已在激光弹道上，会在激光回合被引爆
    if beam_sets:
        occ = state.get("occupant")
        for cells in beam_sets:
            for idx in cells:
                y = idx // GRID_W
                x = idx % GRID_W
                try:
                    if occ[y][x] != "TNT":
                        continue
                except Exception:
                    continue
                for yy in range(y - 1, y + 2):
                    for xx in range(x - 1, x + 2):
                        if 0 <= xx < GRID_W and 0 <= yy < GRID_H:
                            hot.add(yy * GRID_W + xx)
    return hot


def _next_goal(state):
    hero = state["hero"]
    hx = int(hero["x"])
    hy = int(hero["y"])
    keys = hero["keys"]
    tg = state.get("targets") or {}
    k1 = tg.get("K1")
    k2 = tg.get("K2")
    vp = tg.get("V")
    if not keys[0] and not keys[1]:
        best = None
        bd = None
        for cand in (k1, k2):
            if not cand:
                continue
            d = abs(int(cand[0]) - hx) + abs(int(cand[1]) - hy)
            if bd is None or d < bd:
                bd = d
                best = cand
        return (int(best[0]), int(best[1])) if best else None
    if keys[0] and not keys[1]:
        return (int(k2[0]), int(k2[1])) if k2 else None
    if keys[1] and not keys[0]:
        return (int(k1[0]), int(k1[1])) if k1 else None
    return (int(vp[0]), int(vp[1])) if vp else None


_POPC = [0] * 4096
for _i in range(1, 4096):
    _POPC[_i] = _POPC[_i >> 1] + (_i & 1)


def _plan_field(known, occ_m, flipped, beams, hot, hp, jumps, goal_idx, mem_beam=None):
    """三相位（turn%3）时间展开反向 Dijkstra：

    dist[cell*3+p] = 在"出发回合号 mod 3 == p"时位于 cell 的最优代价，
    act[...] = 该状态的最佳首动作。相位模型让规划器自动把穿越激光的时机算进去。
    """
    nb = len(beams)
    cover = [0] * CELLS
    for bi in range(nb):
        bit = 1 << bi
        for c in beams[bi]:
            cover[c] |= bit
    if hp > 70:
        hit_cost = 90.0
    elif hp > 50:
        hit_cost = 500.0
    else:
        hit_cost = 1500.0
    if mem_beam is None:
        mem_beam = ()
    layers = [[[] for _ in range(CELLS)] for _ in range(3)]
    jump_extra = 2.0 + (2.5 if jumps <= 1 else 0.0)

    def add_edge(u, v, act_s, base, heavy, prob):
        layers[1][v].append((u * 3, act_s, base + heavy + prob))
        layers[2][v].append((u * 3 + 1, act_s, base))
        layers[0][v].append((u * 3 + 2, act_s, base))

    for u in range(CELLS):
        ux = u % GRID_W
        uy = u // GRID_W
        cu = cover[u]
        for dk in DIR_KEYS:
            dx, dy = DIRS[dk]
            nx = ux + dx
            ny = uy + dy
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                v = ny * GRID_W + nx
                base = _cell_cost(known[v], occ_m[v], flipped, False, v in hot, hp)
                if base is not None:
                    cv = cover[v]
                    heavy = hit_cost * _POPC[cu | cv] if nb else 0.0
                    prob = 0.0
                    if not (cu | cv) and (u in mem_beam or v in mem_beam):
                        prob = hit_cost
                    add_edge(u, v, MOVE_ACT[dk], base, heavy, prob)
            if jumps > 0:
                p1x = ux + dx
                p1y = uy + dy
                p2x = ux + 2 * dx
                p2y = uy + 2 * dy
                if not (0 <= p2x < GRID_W and 0 <= p2y < GRID_H):
                    continue
                i1 = p1y * GRID_W + p1x
                t1 = known[i1]
                if t1 is not None and _is_wall(t1, flipped):
                    continue
                i2 = p2y * GRID_W + p2x
                t2 = known[i2]
                if t2 is not None and _is_wall(t2, flipped):
                    continue
                base2 = _cell_cost(t2, occ_m[i2], flipped, False, i2 in hot, hp)
                if base2 is None:
                    continue
                if t1 is None:
                    base2 += 1.5
                ci = cover[i2]
                heavy = hit_cost * _POPC[cu | ci] if nb else 0.0
                prob = 0.0
                if not (cu | ci) and (u in mem_beam or i2 in mem_beam):
                    prob = hit_cost
                add_edge(u, i2, JUMP_ACT[dk], base2 + jump_extra, heavy, prob)

    total = CELLS * 3
    dist = [INF] * total
    act = [None] * total
    if goal_idx is None:
        return dist, act
    for ph in range(3):
        dist[goal_idx * 3 + ph] = 0.0
    pq = [(0.0, goal_idx * 3), (0.0, goal_idx * 3 + 1), (0.0, goal_idx * 3 + 2)]
    while pq:
        d, st = heapq.heappop(pq)
        if d > dist[st] + 1e-12:
            continue
        cell = st // 3
        ph = st % 3
        for (uf, a, c) in layers[ph][cell]:
            nd = d + c
            if nd < dist[uf] - 1e-12:
                dist[uf] = nd
                act[uf] = a
                heapq.heappush(pq, (nd, uf))
    return dist, act


def _sim_chain(hx, hy, dkey, known, occ_m, flipped, hp):
    """已知地图上仿真一次 MOVE 的 8 步原子位移链。"""
    res = {"dead": False, "blocked": False, "unknown": False,
           "dmg": 0, "x": hx, "y": hy, "exposed": [(hx, hy)]}
    dx, dy = DIRS[dkey]
    x = hx + dx
    y = hy + dy
    if not (0 <= x < GRID_W and 0 <= y < GRID_H):
        res["blocked"] = True
        return res
    idx = y * GRID_W + x
    if occ_m[idx] == "BOX" or occ_m[idx] == "TNT":
        res["blocked"] = True
        return res
    t = known[idx]
    if t is None:
        res["unknown"] = True
        res["x"] = x
        res["y"] = y
        res["exposed"].append((x, y))
        return res
    if _is_wall(t, flipped):
        res["blocked"] = True
        return res
    cur = (x, y)
    dk = dkey
    steps = 0
    while True:
        steps += 1
        if steps > 32:
            break
        tile = known[cur[1] * GRID_W + cur[0]]
        if tile is None:
            res["unknown"] = True
            break
        res["exposed"].append(cur)
        if tile == "PIT":
            res["dmg"] += 100
            res["dead"] = True
            break
        if tile == "MIMIC":
            res["dmg"] += 45
        elif tile == "HEAL":
            res["dmg"] -= 30
        elif tile == "SWITCH":
            flipped = not flipped
        if tile in SPRING_TILES:
            dk = SPRING_TILES[tile]
            ndx, ndy = DIRS[dk]
            land = None
            for k in (1, 2, 3):
                px = cur[0] + k * ndx
                py = cur[1] + k * ndy
                if not (0 <= px < GRID_W and 0 <= py < GRID_H):
                    land = None if k == 1 else (cur[0] + (k - 1) * ndx, cur[1] + (k - 1) * ndy)
                    break
                j = py * GRID_W + px
                tt = known[j]
                oo = occ_m[j]
                if oo == "BOX" or oo == "TNT" or (tt is not None and _is_wall(tt, flipped)):
                    land = None if k == 1 else (cur[0] + (k - 1) * ndx, cur[1] + (k - 1) * ndy)
                    break
                if tt is None:
                    res["unknown"] = True
                    land = None
                    break
            if res["unknown"]:
                break
            if land is None or land == cur:
                break
            cur = land
            res["exposed"].append(cur)
            tile = known[cur[1] * GRID_W + cur[0]]
            if tile is None:
                res["unknown"] = True
                break
            if tile == "PIT":
                res["dmg"] += 100
                res["dead"] = True
                break
            if tile == "MIMIC":
                res["dmg"] += 45
            elif tile == "HEAL":
                res["dmg"] -= 30
            elif tile == "SWITCH":
                flipped = not flipped
            if tile != "ICE" and tile not in MIRROR_TILES:
                break
            continue
        if tile in MIRROR_TILES:
            dk = MIRROR_TILES[tile][dk]
        if tile in PORTALS:
            res["unknown"] = True
            break
        if tile == "ICE" or tile in MIRROR_TILES or tile in SPRING_TILES:
            ndx, ndy = DIRS[dk]
            nx = cur[0] + ndx
            ny = cur[1] + ndy
            if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                break
            j = ny * GRID_W + nx
            tt = known[j]
            oo = occ_m[j]
            if oo == "BOX" or oo == "TNT" or (tt is not None and _is_wall(tt, flipped)):
                break
            if tt is None:
                res["unknown"] = True
                break
            cur = (nx, ny)
            continue
        break
    res["x"] = cur[0]
    res["y"] = cur[1]
    if hp - res["dmg"] <= 0:
        res["dead"] = True
    return res


def _sim_jump(hx, hy, dkey, known, occ_m, flipped, hp):
    res = {"dead": False, "blocked": False, "unknown": False,
           "dmg": 0, "x": hx, "y": hy, "exposed": [(hx, hy)]}
    dx, dy = DIRS[dkey]
    p1 = (hx + dx, hy + dy)
    p2 = (hx + 2 * dx, hy + 2 * dy)
    if not (0 <= p2[0] < GRID_W and 0 <= p2[1] < GRID_H):
        res["blocked"] = True
        return res
    t1 = known[p1[1] * GRID_W + p1[0]]
    if t1 is not None and _is_wall(t1, flipped):
        res["blocked"] = True
        return res
    i2 = p2[1] * GRID_W + p2[0]
    o2 = occ_m[i2]
    if o2 == "BOX" or o2 == "TNT":
        res["blocked"] = True
        return res
    t2 = known[i2]
    if t2 is None:
        res["unknown"] = True
        res["x"] = p2[0]
        res["y"] = p2[1]
        res["exposed"].append(p2)
        return res
    if _is_wall(t2, flipped):
        res["blocked"] = True
        return res
    res["exposed"].append(p2)
    if t2 == "PIT":
        res["dmg"] += 100
        res["dead"] = True
        res["x"] = p2[0]
        res["y"] = p2[1]
        return res
    if t2 == "MIMIC":
        res["dmg"] += 45
    elif t2 == "HEAL":
        res["dmg"] -= 30
    res["x"] = p2[0]
    res["y"] = p2[1]
    if hp - res["dmg"] <= 0:
        res["dead"] = True
    return res


def _laser_hits(cells, beam_sets, warn=None):
    """估计本轮会被多少门激光炮命中（已知炮座精确计数 + 官方 laser_warnings 兜底）。"""
    if not cells:
        return 0
    ex = set()
    for (x, y) in cells:
        ex.add(y * GRID_W + x)
    n = 0
    if beam_sets:
        for bs in beam_sets:
            if not ex.isdisjoint(bs):
                n += 1
    if warn:
        top = 0
        distinct = 0
        for (x, y) in cells:
            c = warn.get((x, y), 0)
            if c > top:
                top = c
            if c > 0:
                distinct += 1
        if top > n:
            n = top
        if distinct > n:
            n = distinct
    return n


# ---------------------------------------------------------------- 破墙自救

def _bfs_reach(start, known, occ_m, flipped):
    seen = set((start,))
    stack = [start]
    while stack:
        u = stack.pop()
        ux = u % GRID_W
        uy = u // GRID_W
        for dk in DIR_KEYS:
            dx, dy = DIRS[dk]
            nx = ux + dx
            ny = uy + dy
            if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                continue
            v = ny * GRID_W + nx
            if v in seen:
                continue
            t = known[v]
            if t is None:
                continue
            if occ_m[v] is not None:
                continue
            if _is_wall(t, flipped) or t == "PIT" or t == "MIMIC":
                continue
            seen.add(v)
            stack.append(v)
    return seen


def _bfs_path_act(start, target, known, occ_m, flipped):
    """从 start 到 target 的最短步行路径的首个动作。"""
    if start == target:
        return None
    prev = {start: (None, None)}
    dq = [start]
    head = 0
    while head < len(dq):
        u = dq[head]
        head += 1
        ux = u % GRID_W
        uy = u // GRID_W
        for dk in DIR_KEYS:
            dx, dy = DIRS[dk]
            nx = ux + dx
            ny = uy + dy
            if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                continue
            v = ny * GRID_W + nx
            if v in prev:
                continue
            if occ_m[v] is not None:
                continue
            t = known[v]
            if t is None or _is_wall(t, flipped) or t == "PIT" or t == "MIMIC":
                continue
            prev[v] = (u, MOVE_ACT[dk])
            if v == target:
                node = v
                act = MOVE_ACT[dk]
                while prev[node][0] is not None and prev[node][0] != start:
                    node = prev[node][0]
                    act = prev[node][1]
                return act
            dq.append(v)
    return None


def _breach_action(state, known, occ_m, flipped, hx, hy, goal):
    """被彻底封死时：找一格可炸的 W 墙，走到贴墙格布雷。"""
    hero = state["hero"]
    if int(hero["bombs"]) <= 0:
        return None
    gx, gy = goal
    start = hy * GRID_W + hx
    reach = _bfs_reach(start, known, occ_m, flipped)
    best_wall = None
    for u in reach:
        ux = u % GRID_W
        uy = u // GRID_W
        for dk in DIR_KEYS:
            dx, dy = DIRS[dk]
            nx = ux + dx
            ny = uy + dy
            if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                continue
            v = ny * GRID_W + nx
            if known[v] != "W" or occ_m[v] is not None:
                continue
            sc = abs(nx - gx) + abs(ny - gy)
            if best_wall is None or sc < best_wall[0]:
                best_wall = (sc, v)
    if best_wall is None:
        return None
    wx = best_wall[1] % GRID_W
    wy = best_wall[1] // GRID_W
    # 选贴近墙的可达格作为布雷点
    best_b = None
    for u in reach:
        ux = u % GRID_W
        uy = u // GRID_W
        if max(abs(ux - wx), abs(uy - wy)) <= 1:
            d = abs(ux - hx) + abs(uy - hy)
            if best_b is None or d < best_b[0]:
                best_b = (d, u)
    if best_b is None:
        return None
    bx = best_b[1] % GRID_W
    by = best_b[1] // GRID_W
    # 已有炸弹贴着我们 / 脚下 -> 先撤到安全距离
    bombs = state.get("bombs") or ()
    near_bomb = False
    for b in bombs:
        try:
            ddx = abs(int(b["x"]) - hx)
            ddy = abs(int(b["y"]) - hy)
        except Exception:
            continue
        if ddx <= 1 and ddy <= 1:
            near_bomb = True
    if near_bomb:
        best_r = None
        for u in reach:
            ux = u % GRID_W
            uy = u // GRID_W
            far = True
            for b in bombs:
                try:
                    if max(abs(int(b["x"]) - ux), abs(int(b["y"]) - uy)) <= 1:
                        far = False
                        break
                except Exception:
                    continue
            if far:
                d = abs(ux - hx) + abs(uy - hy)
                if best_r is None or d < best_r[0]:
                    best_r = (d, u)
        if best_r is None:
            return None
        return _bfs_path_act(start, best_r[1], known, occ_m, flipped)
    if start == best_b[1]:
        # 确认炸完有地方躲（够大就躲，躲不开就赌血量扛一发炸弹自伤 50）
        safe = False
        for u in reach:
            ux = u % GRID_W
            uy = u // GRID_W
            if max(abs(ux - bx), abs(uy - by)) >= 2:
                safe = True
                break
        if not safe and int(hero["hp"]) <= 60:
            return None
        return "BOMB"
    return _bfs_path_act(start, best_b[1], known, occ_m, flipped)


# =============================================================================
# 决策主体
# =============================================================================

def _decide(state, memory):
    hero = state["hero"]
    hx = int(hero["x"])
    hy = int(hero["y"])
    hp = int(hero["hp"])
    turn = int(state["turn"])
    flipped = bool(state["gates_flipped"])
    jumps = int(hero["jumps"])
    throws = int(hero["throws"])

    known, occ_m = _update_memory(state, memory)
    beams = _beam_sets(known, occ_m, flipped)
    hot = _hot_cells(state, beams)
    start = hy * GRID_W + hx

    goal = _next_goal(state)
    if goal is None:
        return "WAIT"
    gx, gy = goal
    goal_idx = gy * GRID_W + gx
    laser_now = (turn % 3 == 0)
    phase = turn % 3
    next_phase = (turn + 1) % 3
    warn = None
    if laser_now:
        warn = {}
        for w in (state.get("laser_warnings") or ()):
            try:
                key = (int(w["x"]), int(w["y"]))
            except Exception:
                continue
            warn[key] = warn.get(key, 0) + 1
    # 记住历史警告过的弹道格（炮座可能在视野外），供后续回合避险
    beam_mem = memory.get("b")
    if not isinstance(beam_mem, set):
        beam_mem = set()
        memory["b"] = beam_mem
    if warn:
        for (bx, by) in warn:
            beam_mem.add(by * GRID_W + bx)
    dist, act = _plan_field(known, occ_m, flipped, beams, hot, hp, jumps, goal_idx,
                            beam_mem)
    start_state = start * 3 + phase
    plan_act = act[start_state]
    goal_cost = dist[start_state]
    sealed = goal_cost >= INF * 0.5
    if sealed:
        goal_cost = 40.0

    # 防打转：最近走过的格子
    hist = memory.get("h")
    if not isinstance(hist, list):
        hist = []
        memory["h"] = hist
    hist3 = set(hist[-3:-1]) if len(hist) >= 2 else set()

    # ---- 被彻底封死 / 长时间僵住：尝试炸弹破墙
    stall = memory.get("stall")
    if not isinstance(stall, int):
        stall = 0
    if sealed or stall >= 6:
        breach = None
        try:
            breach = _breach_action(state, known, occ_m, flipped, hx, hy, goal)
        except Exception:
            breach = None
        if breach in VALID_ACTIONS:
            memory["stall"] = 0
            memory["probe"] = 0
            return breach
        # 最后手段：系统化试探（飞石引爆 TNT / 跳跃越障等），总比原地等死强
        idx = memory.get("probe")
        if not isinstance(idx, int):
            idx = 0
        order = ("THROW_R", "THROW_U", "THROW_D", "THROW_L",
                 "JUMP_R", "JUMP_U", "JUMP_D", "JUMP_L", "BOMB")
        while idx < len(order):
            a = order[idx]
            idx += 1
            if a.startswith("THROW_") and throws <= 0:
                continue
            if a.startswith("JUMP_"):
                if jumps <= 0:
                    continue
                sim = _sim_jump(hx, hy, a[5], known, occ_m, flipped, hp)
                if sim["blocked"] or sim["dead"]:
                    continue
            memory["probe"] = idx
            memory["stall"] = 0
            return a
        memory["probe"] = idx

    # ---- 候选动作评估
    cands = []
    if plan_act:
        cands.append(plan_act)
    for dk in DIR_KEYS:
        a = MOVE_ACT[dk]
        if a not in cands:
            cands.append(a)
    if jumps > 0:
        for dk in DIR_KEYS:
            a = JUMP_ACT[dk]
            if a not in cands:
                cands.append(a)

    best_score = None
    best_act = None
    for a in cands:
        if a.startswith("MOVE_"):
            sim = _sim_chain(hx, hy, a[5], known, occ_m, flipped, hp)
        else:
            sim = _sim_jump(hx, hy, a[5], known, occ_m, flipped, hp)
        if sim["blocked"] or sim["dead"]:
            continue
        if sim["x"] == hx and sim["y"] == hy:
            continue
        dmg = sim["dmg"]
        if laser_now:
            dmg += 50 * _laser_hits(sim["exposed"], beams, warn)
        if hp - dmg <= 0:
            continue
        eidx = sim["y"] * GRID_W + sim["x"]
        d2 = dist[eidx * 3 + next_phase]
        if d2 >= INF * 0.5:
            d2 = 40.0 + 0.63 * (abs(gx - sim["x"]) + abs(gy - sim["y"]))
        score = 1.5 * dmg + d2
        if sim["unknown"]:
            score += 1.0
        if a != plan_act:
            score += 0.5
        if a.startswith("JUMP_"):
            score += 0.3
        if eidx in hist3:
            score += 4.0
        if best_score is None or score < best_score:
            best_score = score
            best_act = a

    wait_dmg = 0
    if laser_now:
        wait_dmg += 50 * _laser_hits([(hx, hy)], beams, warn)
    wait_score = 1.5 * wait_dmg + dist[start * 3 + next_phase] + 2.0

    hist.append(start)
    if len(hist) > 8:
        del hist[0:len(hist) - 8]

    if best_act is None:
        memory["stall"] = stall + 1
        return "WAIT"
    if wait_score < best_score:
        memory["stall"] = 0 if wait_dmg > 0 else stall + 1
        return "WAIT"
    memory["stall"] = 0
    return best_act


def decide_action(state: dict, memory: dict) -> str:
    try:
        if not isinstance(memory, dict):
            memory = {}
        act = _decide(state, memory)
        if act in VALID_ACTIONS:
            return act
        return "WAIT"
    except Exception:
        return "WAIT"
