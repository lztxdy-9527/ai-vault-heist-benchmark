# -*- coding: utf-8 -*-
"""
《阴间地牢：金库攻防战》 submission.py —— 参赛者：GLM

build_dungeon() : "GAUNTLET FORTRESS"（回廊堡垒）
  - 公共区域布满雷区/激光十字火/伪装宝箱怪；
  - K1/K2/V 三座宝室以 T_W 密封 + 北面 1 格深坑入口（需 JUMP 跃入）+
    南面弹簧单向阀（只出不进，阀前深坑防止从南面跃入）；
  - 通关全程需 4 次 JUMP（勇者只有 3 次）—— 除非精准复刻作者的双炸弹暗道。
decide_action() : BLIND 迷雾模式勇者 —— 增量建图记忆 + Dijkstra 寻路 +
  激光回合节拍规避 + 冰面滑行模拟 + 宝箱怪线索识别。
"""

import heapq

GRID_W = 40
GRID_H = 26
MAX_TURNS = 240

VALID_ACTIONS = frozenset([
    "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT",
    "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
    "THROW_U", "THROW_D", "THROW_L", "THROW_R", "BOMB",
])

DIRS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}

TILE_COSTS = {
    "EMPTY": 0, "K1": 0, "K2": 0, "V": 0,
    "W": 5, "T_W": 25,
    "ICE": 10,
    "MIRROR_NE": 25, "MIRROR_SE": 25, "MIRROR_SW": 25, "MIRROR_NW": 25,
    "SPRING_U": 35, "SPRING_D": 35, "SPRING_L": 35, "SPRING_R": 35,
    "PIT": 40,
    "LASER_U": 75, "LASER_D": 75, "LASER_L": 75, "LASER_R": 75,
    "CRACK": 20, "SWITCH": 30,
    "R_GATE": 20, "B_GATE": 20,
    "TNT": 40, "BOX": 30, "HEAL": 30, "MIMIC": 60,
    "PORTAL_1A": 40, "PORTAL_1B": 40, "PORTAL_2A": 40, "PORTAL_2B": 40,
}

HIGH_WALL_TILES = frozenset(["W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R"])
MOMENTUM_TILES = frozenset([
    "MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW",
    "SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R",
])
PORTAL_TILES = frozenset(["PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B"])


# ==============================================================================
# 参赛入口 1：魔王造图与自证函数
# ==============================================================================

def build_dungeon() -> dict:
    grid = [["EMPTY" for _ in range(GRID_W)] for _ in range(GRID_H)]
    for y in range(GRID_H):
        for x in range(GRID_W):
            if x == 0 or x == GRID_W - 1 or y == 0 or y == GRID_H - 1:
                grid[y][x] = "T_W"

    P = {}
    # ---- 地标 ----
    P[(18, 5)] = "K1"     # 上半区 (x in 12..34, y in 2..10) 合法
    P[(18, 20)] = "K2"    # 下半区 (y in 15..23) 合法; |18-18|+|5-20|=15 >= 12
    P[(35, 13)] = "V"     # x in 33..37, y in 4..21 合法

    # ---- K1 宝室：T_W 密封 + 北面深坑跳跃入口 + 南面弹簧单向阀 ----
    P[(17, 4)] = "T_W"; P[(19, 4)] = "T_W"; P[(18, 4)] = "PIT"
    P[(17, 5)] = "T_W"; P[(19, 5)] = "T_W"
    P[(17, 6)] = "T_W"; P[(18, 6)] = "SPRING_D"; P[(19, 6)] = "T_W"
    P[(18, 7)] = "PIT"    # 阀前深坑：南面跃入者坠亡 / 跃上弹簧者被弹回

    # ---- K1 口袋跳板区 (17..19, 3) 的双激光十字火 ----
    P[(16, 3)] = "LASER_R"
    P[(20, 3)] = "LASER_L"

    # ---- 北走廊：y=1 与 y=3 砖墙行（东段唯一入口是深坑门 (14,2)）----
    for x in range(12, 20):
        P[(x, 1)] = "W"            # 12..19
    for x in range(13, 16):
        P[(x, 3)] = "W"            # 13..15；(12,3) 为竖井下探缺口；(16,3)(20,3) 是激光；(17..19,3) 是口袋
    P[(20, 2)] = "W"               # 走廊东侧封口（与北广场隔绝）

    # ---- K2 宝室 ----
    P[(17, 19)] = "T_W"; P[(19, 19)] = "T_W"; P[(18, 19)] = "PIT"
    P[(17, 20)] = "T_W"; P[(19, 20)] = "T_W"
    P[(17, 21)] = "T_W"; P[(18, 21)] = "SPRING_D"; P[(19, 21)] = "T_W"
    P[(18, 22)] = "PIT"
    P[(16, 18)] = "LASER_R"        # 口袋 (17..19,18) 双激光
    P[(20, 18)] = "LASER_L"
    # 冰滑走廊（从公路南缺口滑向 K2 跳板，到达回合不受控 → 2/3 撞激光）
    P[(18, 15)] = "ICE"; P[(18, 16)] = "ICE"; P[(18, 17)] = "ICE"
    for y in (15, 16, 17):
        P[(17, y)] = "W"; P[(19, y)] = "W"

    # ---- V 宝室 ----
    P[(34, 12)] = "T_W"; P[(36, 12)] = "T_W"; P[(35, 12)] = "PIT"
    P[(34, 13)] = "T_W"; P[(36, 13)] = "T_W"
    P[(34, 14)] = "T_W"; P[(35, 14)] = "T_W"; P[(36, 14)] = "T_W"
    P[(33, 11)] = "LASER_R"        # (34..36,11) 双激光覆盖 V 跳板
    P[(37, 11)] = "LASER_L"

    # ---- 公路 (y=13) 两侧砖墙，缺口： (12,12) (18,12) (18,14) ----
    for x in range(6, 34):
        if x not in (12, 18):
            P[(x, 12)] = "W"
        if x != 18:
            P[(x, 14)] = "W"

    # ---- 诱杀撒布 ----
    for (x, y) in [(14, 7), (14, 8), (22, 7), (26, 8), (24, 20), (26, 21)]:
        P[(x, y)] = "PIT"
    for (x, y) in [(16, 8), (17, 9), (19, 9), (20, 8), (16, 10), (20, 10),
                   (16, 19), (20, 19), (17, 23), (19, 23)]:
        P[(x, y)] = "CRACK"
    P[(25, 8)] = "MIMIC"; P[(30, 18)] = "MIMIC"   # 线索位 (25,7)/(30,17) 均合法

    for (x, y), t in P.items():
        grid[y][x] = t

    # 出生净空区强制清空
    for y in range(12, 15):
        for x in range(1, 4):
            grid[y][x] = "EMPTY"

    # ---- 作者自证路径（92 回合逐拍验证，最后一步 JUMP_D 恰好首达 V 通关）----
    a = ["MOVE_R"] * 10              # t1-10 : (2,13)->(12,13)
    a += ["MOVE_U"] * 11             # t11-21: ->(12,2)
    a += ["MOVE_R"]                  # t22   : ->(13,2)
    a += ["BOMB", "MOVE_L", "MOVE_L",      # t23-25: 炸开 y=1 暗道西段
          "MOVE_R", "MOVE_R", "MOVE_U", "MOVE_R",  # t26-29
          "BOMB", "MOVE_L", "MOVE_L",      # t30-32: 炸开 (15,1)
          "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_D"]  # t33-36: 穿越至 (15,2)
    a += ["MOVE_R"] * 3              # t37-39: ->(18,2)
    a += ["MOVE_D", "JUMP_D"]        # t40-41: ≡1 进口袋、≡2 跃入 K1
    a += ["MOVE_D"]                  # t42   : 弹簧阀 -> (18,9)
    a += ["MOVE_D"] * 5              # t43-47: ->(18,14)
    a += ["WAIT", "MOVE_D", "JUMP_D"]  # t48-50: ≡1 滑冰、≡2 跃入 K2
    a += ["MOVE_D"]                  # t51   : 弹簧阀 -> (18,24)
    a += ["MOVE_R"] * 19             # t52-70: ->(37,24)
    a += ["MOVE_U"] * 12             # t71-82: ->(37,12)
    a += ["MOVE_R", "MOVE_U", "MOVE_U"]   # t83-85: ->(38,10)
    a += ["MOVE_L"] * 3              # t86-88: ->(35,10)
    a += ["WAIT", "WAIT", "MOVE_D", "JUMP_D"]  # t89-92: ≡1 登跳板、≡2 跃上 V 通关!

    return {
        "taunt": "沙盘已布，静候葬礼：钥匙在墙后，金库在雾里，而你们在坟里。",
        "grid": grid,
        "author_solution": a,
    }


# ==============================================================================
# 参赛入口 2：勇者单步决策函数（BLIND 迷雾模式专用）
# ==============================================================================

def decide_action(state: dict, memory: dict) -> str:
    try:
        act = _decide(state, memory)
        if act in VALID_ACTIONS:
            return act
        return "WAIT"
    except Exception:
        return "WAIT"


def _hw(t, flipped):
    """地形是否为当前状态下的高墙。"""
    if t is None:
        return False
    if t in HIGH_WALL_TILES:
        return True
    if t == "R_GATE":
        return not flipped
    if t == "B_GATE":
        return flipped
    return False


def _init_memory(memory):
    memory["terr"] = [[None] * GRID_W for _ in range(GRID_H)]
    memory["occ"] = [[None] * GRID_W for _ in range(GRID_H)]
    memory["clue"] = set()
    memory["rays"] = set()
    memory["crushed"] = set()      # 离开过的 CRACK -> 视为 PIT
    memory["laser_bases"] = set()  # 已知激光炮座
    memory["prev"] = None
    memory["extra_blocked"] = set()
    memory["visits"] = {}
    memory["last_pos"] = None
    memory["last_move_turn"] = None


def _decide(state, memory):
    if "terr" not in memory:
        _init_memory(memory)

    turn = int(state.get("turn", 1))
    hero = state.get("hero", {}) or {}
    hx, hy = int(hero.get("x", 2)), int(hero.get("y", 13))
    keys = hero.get("keys", [False, False]) or [False, False]
    jumps_left = int(hero.get("jumps", 0))
    flipped = bool(state.get("gates_flipped", False))
    terr = state.get("terrain") or []
    occ = state.get("occupant") or []
    vis = state.get("visible_mask") or []
    clues = state.get("clues") or []
    targets = state.get("targets", {}) or {}

    mt = memory["terr"]; mo = memory["occ"]
    # ---- 融合本回合可见信息 ----
    for y in range(GRID_H):
        if y >= len(vis):
            break
        for x in range(GRID_W):
            if vis[y] and x < len(vis[y]) and vis[y][x]:
                t = terr[y][x] if y < len(terr) and x < len(terr[y]) else None
                if t and t != "UNKNOWN":
                    mt[y][x] = t
                    if t.startswith("LASER_"):
                        memory["laser_bases"].add((x, y))
                    if t in ("EMPTY",):
                        memory["crushed"].discard((x, y))
                o = occ[y][x] if y < len(occ) and x < len(occ[y]) else None
                mo[y][x] = o
                if clues and y < len(clues) and x < len(clues[y]) and clues[y][x]:
                    memory["clue"].add((x, y))

    # ---- 激光射线记忆：本回合警告 + 由炮座推算 ----
    for w in (state.get("laser_warnings") or []):
        try:
            memory["rays"].add((int(w["x"]), int(w["y"])))
        except Exception:
            pass
    for (lx, ly) in list(memory["laser_bases"]):
        t = mt[ly][lx]
        d = DIRS.get(t[-1]) if t and t.startswith("LASER_") else None
        if not d:
            continue
        cx, cy = lx, ly
        for _ in range(10):
            cx += d[0]; cy += d[1]
            if not (0 <= cx < GRID_W and 0 <= cy < GRID_H):
                break
            tt = mt[cy][cx]
            if tt is None:
                break
            if _hw(tt, flipped) or mo[cy][cx] in ("BOX", "TNT"):
                break
            memory["rays"].add((cx, cy))

    # ---- 离开 CRACK -> 坍塌 ----
    prev = memory["prev"]
    if prev is not None and prev != (hx, hy):
        px, py = prev
        if mt[py][px] == "CRACK":
            memory["crushed"].add((px, py))
    memory["prev"] = (hx, hy)

    # ---- 规划格 ----
    blocked_extra = memory["extra_blocked"]

    def tile_at(x, y):
        if (x, y) in memory["crushed"]:
            return "PIT"
        return mt[y][x]

    def walkable(x, y):
        if not (0 <= x < GRID_W and 0 <= y < GRID_H):
            return False
        if (x, y) in blocked_extra:
            return False
        if mo[y][x] in ("BOX", "TNT"):
            return False
        t = tile_at(x, y)
        if t is None:
            return False
        if _hw(t, flipped):
            return False
        if t in ("PIT", "MIMIC"):
            return False
        if t in MOMENTUM_TILES or t in PORTAL_TILES:
            return False
        if t == "CHEST":
            return _chest_safe(x, y)
        return True

    def _chest_safe(x, y):
        """四邻全部已知且无骸骨线索 => 真补给箱。"""
        for d in DIRS.values():
            nx, ny = x + d[0], y + d[1]
            if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                continue
            if (nx, ny) in memory["clue"]:
                return False
            if mt[ny][nx] is None:
                return False
        return True

    def step_cost(x, y):
        t = tile_at(x, y)
        c = 1
        if (x, y) in memory["rays"]:
            c += 7          # 激光线上：节拍等待的代价
        if t == "CRACK":
            c += 1
        if t == "SWITCH":
            c += 3
        if t == "ICE":
            c += 1
        if t == "CHEST":
            c += 1
        return c

    # ---- 目标选择 ----
    goal = None
    tx = ty = None
    k1 = targets.get("K1"); k2 = targets.get("K2"); vv = targets.get("V")
    need = []
    if k1 and not keys[0]:
        need.append((int(k1[0]), int(k1[1])))
    if k2 and not keys[1]:
        need.append((int(k2[0]), int(k2[1])))
    if need:
        need.sort(key=lambda p: abs(p[0] - hx) + abs(p[1] - hy))
        tx, ty = need[0]
    elif vv:
        tx, ty = int(vv[0]), int(vv[1])

    if tx is None:
        return "WAIT"

    rays = memory["rays"]
    visits = memory["visits"]
    visits[(hx, hy)] = visits.get((hx, hy), 0) + 1

    def dijkstra_full(sx, sy, allow_jump, jump_budget):
        """全图 Dijkstra：返回 (dist, prev, jump_used)。允许跳跃时含 JUMP 边。"""
        INF = float("inf")
        dist = {(sx, sy): 0}
        jump_used = {(sx, sy): 0}
        prev = {}
        pq = [(0, sx, sy)]
        while pq:
            d0, cx, cy = heapq.heappop(pq)
            if d0 > dist.get((cx, cy), INF):
                continue
            ju = jump_used.get((cx, cy), 0)
            for ch, (dx, dy) in DIRS.items():
                nx, ny = cx + dx, cy + dy
                if not walkable(nx, ny):
                    continue
                nd = d0 + step_cost(nx, ny)
                if nd < dist.get((nx, ny), INF):
                    dist[(nx, ny)] = nd
                    jump_used[(nx, ny)] = ju
                    prev[(nx, ny)] = (cx, cy, "MOVE_" + ch)
                    heapq.heappush(pq, (nd, nx, ny))
            if allow_jump and ju < jump_budget:
                for ch, (dx, dy) in DIRS.items():
                    p1x, p1y = cx + dx, cy + dy
                    p2x, p2y = cx + 2 * dx, cy + 2 * dy
                    if not (0 <= p1x < GRID_W and 0 <= p1y < GRID_H):
                        continue
                    if not (0 <= p2x < GRID_W and 0 <= p2y < GRID_H):
                        continue
                    t1 = tile_at(p1x, p1y)
                    if t1 is None or _hw(t1, flipped) or mo[p1y][p1x] in ("BOX", "TNT"):
                        continue
                    if not walkable(p2x, p2y):
                        continue
                    t2 = tile_at(p2x, p2y)
                    if t2 == "CHEST" and not _chest_safe(p2x, p2y):
                        continue
                    nd = d0 + 1 + step_cost(p2x, p2y) + 5   # JUMP 强烈抑制
                    if nd < dist.get((p2x, p2y), INF):
                        dist[(p2x, p2y)] = nd
                        jump_used[(p2x, p2y)] = ju + 1
                        prev[(p2x, p2y)] = (cx, cy, "JUMP_" + ch)
                        heapq.heappush(pq, (nd, p2x, p2y))
        return dist, prev, jump_used

    def build_path(sx, sy, gx, gy, prev):
        path = []
        cur = (gx, gy)
        while cur != (sx, sy):
            info = prev.get(cur)
            if info is None:
                return None
            pc, pr, act = info
            path.append((cur, act))
            cur = (pc, pr)
        path.reverse()
        return path

    dist_w, prev_w, _ = dijkstra_full(hx, hy, False, 0)
    path = None
    if (tx, ty) in dist_w:
        path = build_path(hx, hy, tx, ty, prev_w)

    dist_j = prev_j = ju_j = None
    if path is None and jumps_left > 0:
        dist_j, prev_j, ju_j = dijkstra_full(hx, hy, True, jumps_left)
        if (tx, ty) in dist_j and ju_j.get((tx, ty), 0) <= jumps_left:
            path = build_path(hx, hy, tx, ty, prev_j)

    # ---- 不可直达：向目标的迷雾边界推进（含跳跃可达的边界格） ----
    if path is None:
        if dist_j is None:
            dist_j, prev_j, ju_j = dist_w, prev_w, {}
        best = None
        best_score = float("inf")
        for y in range(GRID_H):
            for x in range(GRID_W):
                if not walkable(x, y):
                    continue
                d0 = dist_j.get((x, y))
                if d0 is None:
                    continue
                adj_unknown = False
                for d in DIRS.values():
                    nx, ny = x + d[0], y + d[1]
                    if 0 <= nx < GRID_W and 0 <= ny < GRID_H and mt[ny][nx] is None:
                        adj_unknown = True
                        break
                if not adj_unknown:
                    continue
                if ju_j.get((x, y), 0) > jumps_left:
                    continue
                score = d0 + 2.0 * (abs(x - tx) + abs(y - ty))
                if score < best_score - 1e-9:
                    best_score = score
                    best = (x, y)
        if best is not None:
            path = build_path(hx, hy, best[0], best[1], prev_j)
            if path is not None and sum(1 for _, a in path if a.startswith("JUMP")) > jumps_left:
                path = None

    # ---- 防卡死：长时间原地 -> 随便走走 ----
    if memory["last_pos"] == (hx, hy):
        memory["streak"] = memory.get("streak", 0) + 1
    else:
        memory["streak"] = 0
    memory["last_pos"] = (hx, hy)
    if path is None or not path:
        if memory.get("streak", 0) >= 6:
            cand = []
            for ch, (dx, dy) in DIRS.items():
                nx, ny = hx + dx, hy + dy
                if walkable(nx, ny) and (nx, ny) not in memory["rays"]:
                    cand.append((visits.get((nx, ny), 0), ch, nx, ny))
            if cand:
                cand.sort()
                ch = cand[0][1]
                return "MOVE_" + ch
        return "WAIT"

    (nx, ny), act = path[0]

    if not walkable(nx, ny):
        return "WAIT"

    # ---- 执行安全校验 ----
    t_next = tile_at(nx, ny)
    fire_now = (turn % 3 == 0)
    end_danger = (turn % 3 == 2)

    if act.startswith("JUMP"):
        if t_next == "ICE":
            slid = _slide_end(nx, ny, act[-1], mt, mo, flipped, memory)
            if slid is None:
                blocked_extra.add((nx, ny))
                return "WAIT"
            if (fire_now and (slid in rays or (nx, ny) in rays)) or \
               (end_danger and slid in rays):
                return "WAIT"
        if fire_now and (nx, ny) in rays:
            return "WAIT"
        if end_danger and (nx, ny) in rays:
            return "WAIT"
        return act

    # MOVE
    if t_next == "ICE":
        slid = _slide_end(nx, ny, act[-1], mt, mo, flipped, memory)
        if slid is None:
            blocked_extra.add((nx, ny))
            return "WAIT"
        # 滑行整程都已知且安全；节拍校验
        if fire_now and ((slid in rays) or (nx, ny) in rays):
            return "WAIT"
        if end_danger and slid in rays:
            return "WAIT"
        # 停不下来滑过头且远离目标则放弃
        manh_now = abs(hx - tx) + abs(hy - ty)
        manh_end = abs(slid[0] - tx) + abs(slid[1] - ty)
        if slid != (nx, ny) and manh_end > manh_now + 3:
            blocked_extra.add((nx, ny))
            return "WAIT"
        return act

    if (fire_now or end_danger) and (nx, ny) in rays:
        return "WAIT"
    return act


def _slide_end(x0, y0, ch, mt, mo, flipped, memory):
    """从 (x0,y0) 沿方向 ch 的冰面滑行模拟；返回最终落点，不安全返回 None。"""
    d = DIRS[ch]
    cx, cy = x0, y0
    seen = {(cx, cy)}
    while True:
        nx, ny = cx + d[0], cy + d[1]
        if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
            return (cx, cy)
        t = mt[ny][nx]
        if t is None:
            return None
        if _hw(t, flipped) or mo[ny][nx] in ("BOX", "TNT"):
            return (cx, cy)
        if t in ("PIT", "MIMIC") or (nx, ny) in memory["crushed"]:
            return None
        if t in MOMENTUM_TILES or t in PORTAL_TILES or t == "CHEST":
            return None
        if t == "ICE":
            if (nx, ny) in seen:
                return None
            seen.add((nx, ny))
            cx, cy = nx, ny
            continue
        # EMPTY / CRACK / SWITCH / K / V / 开门 -> 摩擦停稳
        return (nx, ny)
