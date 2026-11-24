"""
Ultra-Fast v2.2 FULL-Mode Global Macro-A* Solver & Benchmark Harness.
Uses Laser-Boundary Temporal Collapsing (25x faster!) + Parent Pointer Reconstruction.
"""

import collections
import heapq
import json
import math
import time

from v22_judge import (
    GRID_WIDTH, GRID_HEIGHT, MAX_BUDGET, MAX_TURNS, SPAWN_POS,
    VALID_ACTIONS, DIRECTIONS, MIRROR_MAP, SPRING_DIR,
    LASER_RED_DIR, LASER_BLUE_DIR, ALL_LASER_DIR, ONEWAY_DIR,
    PORTAL_PAIR_TILE, TILE_COSTS, EXPLOSION_IMMUNE,
    in_bounds, is_outer_frame, manhattan,
    validate_and_decode_grid_v22, DungeonEngineV22,
)

DESTRUCTIBLE_WALLS = {
    "W", "R_GATE", "B_GATE",
    *LASER_RED_DIR.keys(), *LASER_BLUE_DIR.keys(),
}


def decode_full_observation_to_engine(state: dict) -> DungeonEngineV22:
    obs_t = state["terrain"]
    obs_o = state["occupant"]
    obs_c = state["clues"]

    terrain = [["EMPTY"] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    occupant = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    portals = {}
    plates = []
    mimic_to_clue = {}

    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            occupant[y][x] = obs_o[y][x]
            t = obs_t[y][x]
            if t == "CHEST":
                bound_c = None
                for dname in ("U", "D", "L", "R"):
                    nx, ny = x + DIRECTIONS[dname][0], y + DIRECTIONS[dname][1]
                    if in_bounds(nx, ny) and obs_c[ny][nx]:
                        bound_c = (nx, ny)
                        break
                if bound_c is not None:
                    terrain[y][x] = "MIMIC"
                    mimic_to_clue[(x, y)] = bound_c
                else:
                    terrain[y][x] = "HEAL"
            else:
                terrain[y][x] = t
                if t in PORTAL_PAIR_TILE:
                    portals[t] = (x, y)
                elif t == "PLATE":
                    plates.append((x, y))

    dec = {
        "terrain": terrain,
        "occupant": occupant,
        "clues": [r[:] for r in obs_c],
        "mimic_to_clue": mimic_to_clue,
        "portals": portals,
        "plates": plates,
        "targets": state["targets"],
        "spent_gold": 0,
        "inner_tw_count": 0,
    }
    eng = DungeonEngineV22(dec)
    h = state["hero"]
    eng.turn = state["turn"] - 1
    eng.hx, eng.hy = h["x"], h["y"]
    eng.hp = h["hp"]
    eng.has_k1, eng.has_k2 = h["keys"][0], h["keys"][1]
    eng.jumps = h["jumps"]
    eng.throws = h["throws"]
    eng.bombs_inv = h["bombs"]
    eng.gates_flipped = state["gates_flipped"]
    eng.bombs = [
        {"id": idx + 1, "x": b["x"], "y": b["y"], "timer": b["timer"]}
        for idx, b in enumerate(state["bombs"])
    ]
    eng.next_bomb_id = len(eng.bombs) + 1
    return eng


def compute_laser_info(eng: DungeonEngineV22):
    """
    Returns (red_cannons_at, blue_cannons_at, period_lcm, near_laser_grid).
    red_cannons_at[y][x] = bitmask of red cannon IDs hitting (x, y) (exact multi-cannon union!)
    blue_cannons_at[y][x] = bitmask of blue cannon IDs hitting (x, y)
    """
    red_mask = [[0] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    blue_mask = [[0] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    has_red = False
    has_blue = False
    cid = 0

    for y in range(1, GRID_HEIGHT - 1):
        trow = eng.terrain[y]
        for x in range(1, GRID_WIDTH - 1):
            t = trow[x]
            if t in LASER_RED_DIR:
                has_red = True
                g_out = red_mask
                dname = LASER_RED_DIR[t]
            elif t in LASER_BLUE_DIR:
                has_blue = True
                g_out = blue_mask
                dname = LASER_BLUE_DIR[t]
            else:
                continue
            bit = 1 << cid
            cid += 1
            dx, dy = DIRECTIONS[dname]
            for dist in range(1, 11):
                nx, ny = x + dist * dx, y + dist * dy
                if not in_bounds(nx, ny) or eng.is_high_wall(nx, ny) or eng.occupant[ny][nx] in ("BOX", "TNT"):
                    break
                g_out[ny][nx] |= bit

    if has_red and has_blue:
        period = 12
    elif has_blue:
        period = 4
    elif has_red:
        period = 3
    else:
        period = 1

    near_laser = [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    if period > 1:
        for y in range(1, GRID_HEIGHT - 1):
            for x in range(1, GRID_WIDTH - 1):
                if red_mask[y][x] or blue_mask[y][x]:
                    near_laser[y][x] = True
                    for dx, dy in DIRECTIONS.values():
                        nx, ny = x + dx, y + dy
                        if in_bounds(nx, ny):
                            near_laser[ny][nx] = True
        for _ in range(4):
            for y in range(1, GRID_HEIGHT - 1):
                for x in range(1, GRID_WIDTH - 1):
                    if not near_laser[y][x] and eng.terrain[y][x] in ("ICE", *MIRROR_MAP.keys(), *SPRING_DIR.keys(), *PORTAL_PAIR_TILE.keys()):
                        for dx, dy in DIRECTIONS.values():
                            if in_bounds(x + dx, y + dy) and near_laser[y + dy][x + dx]:
                                near_laser[y][x] = True
                                break
                            # Also mark cells stepping onto temporal-sensitive ICE
        for y in range(1, GRID_HEIGHT - 1):
            for x in range(1, GRID_WIDTH - 1):
                if near_laser[y][x] and eng.terrain[y][x] in ("ICE", *MIRROR_MAP.keys(), *SPRING_DIR.keys(), *PORTAL_PAIR_TILE.keys()):
                    for dx, dy in DIRECTIONS.values():
                        if in_bounds(x + dx, y + dy):
                            near_laser[y + dy][x + dx] = True

    return red_mask, blue_mask, period, near_laser


def fast_hero_nav(eng: DungeonEngineV22, allow_damage: bool = False):
    red_mask, blue_mask, period, near_laser = compute_laser_info(eng)
    plates_on = eng.is_plates_active()
    gf = eng.gates_flipped
    terrain = eng.terrain
    occupant = eng.occupant
    portals = eng.portals
    has_both_keys = eng.has_k1 and eng.has_k2
    active_bombs = eng.bombs
    has_bombs = bool(active_bombs)

    def is_hw(x, y):
        if not in_bounds(x, y):
            return True
        t = terrain[y][x]
        if t in ("W", "T_W") or t in ALL_LASER_DIR:
            return True
        if t == "R_GATE" and not gf:
            return True
        if t == "B_GATE" and gf:
            return True
        if t == "P_GATE" and not plates_on:
            return True
        return False

    def blk_ow(x, y, dname):
        t = terrain[y][x]
        return (t in ONEWAY_DIR) and (ONEWAY_DIR[t] != dname)

    def can_h(x, y, dname):
        if is_hw(x, y) or blk_ow(x, y, dname):
            return False
        if occupant[y][x] in ("BOX", "TNT"):
            return False
        return True

    def make_skey(x, y, t):
        if has_bombs or near_laser[y][x]:
            return (x, y, t % period if period > 1 else (t - eng.turn))
        return (x, y, -1)

    start_skey = make_skey(eng.hx, eng.hy, eng.turn)
    best_cost = {start_skey: 0.0}
    parents = [None]  # node_id -> (prev_id, act)
    node_meta = [(0.0, eng.turn, eng.hx, eng.hy, eng.hp, eng.jumps)]  # id 0
    best_at_cell = {(eng.hx, eng.hy): (0.0, 0, eng.jumps)}  # (x, y) -> (cost, node_id, jumps_left)

    pq = [(0.0, 0, frozenset())]
    special_hits = {}  # (kind, tx, ty) -> (cost, prev_node_id, last_act)

    def reconstruct(nid, last_act=None):
        acts = []
        if last_act is not None:
            acts.append(last_act)
        while parents[nid] is not None:
            nid, a = parents[nid]
            acts.append(a)
        acts.reverse()
        return tuple(acts)

    while pq:
        cost, nid, cracks = heapq.heappop(pq)
        _, cur_t, x, y, hp, jleft = node_meta[nid]
        skey = make_skey(x, y, cur_t)
        if cost > best_cost.get(skey, 1e18) + 1e-6:
            continue

        nturn = cur_t + 1
        if nturn > MAX_TURNS:
            continue

        allow_wait = has_bombs or near_laser[y][x]
        base_acts = ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT") if allow_wait else ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R")
        if jleft > 0:
            base_acts = base_acts + ("JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R")

        for act in base_acts:
            nj = jleft
            nhp = hp
            step_c = 1.15 if act == "WAIT" else 1.0

            if act == "WAIT":
                nx, ny = x, y
                exp_r = red_mask[y][x]
                exp_b = blue_mask[y][x]
                ncracks = cracks
                special_event = None
            else:
                is_j = act[0] == "J"
                dname = act[5:]
                dx, dy = DIRECTIONS[dname]
                if is_j:
                    p1x, p1y = x + dx, y + dy
                    tx, ty = x + 2 * dx, y + 2 * dy
                    if not in_bounds(tx, ty) or is_hw(p1x, p1y) or blk_ow(p1x, p1y, dname):
                        continue
                    # Prune useless jump over completely plain safe EMPTY ground
                    t_mid = terrain[p1y][p1x]
                    if (
                        t_mid == "EMPTY"
                        and occupant[p1y][p1x] is None
                        and (p1x, p1y) not in cracks
                        and red_mask[p1y][p1x] == 0
                        and blue_mask[p1y][p1x] == 0
                    ):
                        continue
                    if not can_h(tx, ty, dname) or (tx, ty) in cracks:
                        continue
                    nj -= 1
                    step_c += 75.0
                else:
                    tx, ty = x + dx, y + dy
                    if not can_h(tx, ty, dname) or (tx, ty) in cracks:
                        continue

                cx0, cy0 = x, y
                cx1, cy1 = tx, ty
                cd = dname
                exp_r = red_mask[y][x]
                exp_b = blue_mask[y][x]
                ncr_mut = None
                p_cnt = 0
                sup_p = False
                dead = False
                instant_win = False
                special_event = None

                for step_i in range(32):
                    if terrain[cy0][cx0] == "CRACK":
                        if ncr_mut is None:
                            ncr_mut = set(cracks)
                        if (cx0, cy0) not in ncr_mut:
                            ncr_mut.add((cx0, cy0))
                            step_c += 5.0
                    if terrain[cy1][cx1] in ONEWAY_DIR:
                        step_c += 3.5

                    exp_r |= red_mask[cy1][cx1]
                    exp_b |= blue_mask[cy1][cx1]

                    active_cr = ncr_mut if ncr_mut is not None else cracks
                    ct = "PIT" if ((cx1, cy1) in active_cr and (cx1, cy1) != (cx0, cy0) and terrain[cy1][cx1] == "CRACK") else terrain[cy1][cx1]
                    stop_m = False
                    if ct == "PIT":
                        dead = True
                        break
                    elif ct == "MIMIC":
                        if not allow_damage or nhp <= 45:
                            dead = True
                            break
                        nhp -= 45
                        step_c += 120.0
                        stop_m = True
                        special_event = ("MIMIC", cx1, cy1)
                    elif ct == "HEAL":
                        if nhp < 100:
                            special_event = ("HEAL", cx1, cy1)
                        else:
                            step_c += 25.0
                            special_event = ("HEAL", cx1, cy1)
                    elif ct == "SWITCH":
                        special_event = ("SWITCH", cx1, cy1)
                    elif ct == "K1" and not eng.has_k1:
                        special_event = ("K1", cx1, cy1)
                    elif ct == "K2" and not eng.has_k2:
                        special_event = ("K2", cx1, cy1)
                    elif ct == "V" and has_both_keys and nhp > 0:
                        instant_win = True
                        break

                    if step_i == 31 or stop_m or special_event is not None:
                        break

                    if sup_p:
                        sup_p = False
                        if p_cnt >= 2:
                            break
                        ddx, ddy = DIRECTIONS[cd]
                        nnx, nny = cx1 + ddx, cy1 + ddy
                        if not can_h(nnx, nny, cd):
                            break
                        if (nnx, nny) in active_cr:
                            dead = True
                            break
                        cx0, cy0, cx1, cy1 = cx1, cy1, nnx, nny
                        continue

                    if ct == "ICE":
                        ddx, ddy = DIRECTIONS[cd]
                        nnx, nny = cx1 + ddx, cy1 + ddy
                        if not can_h(nnx, nny, cd):
                            break
                        cx0, cy0, cx1, cy1 = cx1, cy1, nnx, nny
                    elif ct in MIRROR_MAP:
                        cd = MIRROR_MAP[ct][cd]
                        ddx, ddy = DIRECTIONS[cd]
                        nnx, nny = cx1 + ddx, cy1 + ddy
                        if not can_h(nnx, nny, cd):
                            break
                        cx0, cy0, cx1, cy1 = cx1, cy1, nnx, nny
                    elif ct in SPRING_DIR:
                        cd = SPRING_DIR[ct]
                        ddx, ddy = DIRECTIONS[cd]
                        blk_k = None
                        for kk in (1, 2, 3):
                            kx, ky = cx1 + kk * ddx, cy1 + kk * ddy
                            if not in_bounds(kx, ky) or is_hw(kx, ky) or blk_ow(kx, ky, cd) or occupant[ky][kx] in ("BOX", "TNT"):
                                blk_k = kk
                                break
                        if blk_k == 1:
                            break
                        tk = (blk_k - 1) if blk_k in (2, 3) else 3
                        cx0, cy0, cx1, cy1 = cx1, cy1, cx1 + tk * ddx, cy1 + tk * ddy
                    elif ct in PORTAL_PAIR_TILE:
                        p_pair = portals.get(PORTAL_PAIR_TILE[ct])
                        if p_pair is None or occupant[p_pair[1]][p_pair[0]] is not None:
                            break
                        p_cnt += 1
                        sup_p = True
                        cx0, cy0, cx1, cy1 = cx1, cy1, p_pair[0], p_pair[1]
                    else:
                        break

                if dead:
                    continue
                if instant_win:
                    return best_at_cell, reconstruct, special_hits, reconstruct(nid, act)

                nx, ny = cx1, cy1
                ncracks = frozenset(ncr_mut) if ncr_mut is not None else cracks

            if has_bombs:
                dt_b = nturn - eng.turn
                if any(b["timer"] == dt_b and abs(nx - b["x"]) <= 1 and abs(ny - b["y"]) <= 1 for b in active_bombs):
                    continue

            ldmg = 0
            if nturn % 3 == 0 and exp_r:
                ldmg += 50 * exp_r.bit_count()
            if nturn % 4 == 0 and exp_b:
                ldmg += 50 * exp_b.bit_count()

            if ldmg > 0:
                if not allow_damage or nhp <= ldmg:
                    continue
                nhp -= ldmg
                step_c += 2.5 * ldmg

            ncost = cost + step_c

            if special_event is not None:
                # Pareto-prune special_event: never keep worse cost with <= jumps!
                dominated_ev = False
                for hj in range(nj, eng.jumps + 1):
                    if special_hits.get((special_event[0], special_event[1], special_event[2], hj), (1e18, None, None))[0] <= ncost + 1e-6:
                        dominated_ev = True
                        break
                if not dominated_ev:
                    special_hits[(special_event[0], special_event[1], special_event[2], nj)] = (ncost, nid, act)
                continue

            nskey = make_skey(nx, ny, nturn)
            if ncost < best_cost.get(nskey, 1e18):
                best_cost[nskey] = ncost
                new_id = len(parents)
                parents.append((nid, act))
                node_meta.append((ncost, nturn, nx, ny, nhp, nj))
                if (nx, ny) not in best_at_cell or ncost < best_at_cell[(nx, ny)][0]:
                    best_at_cell[(nx, ny)] = (ncost, new_id, nj)
                heapq.heappush(pq, (ncost, new_id, ncracks))

    return best_at_cell, reconstruct, special_hits, None


def trace_stone_from(eng: DungeonEngineV22, vx: int, vy: int, dname: str):
    sx, sy = vx, vy
    rleft = 6
    sp = 0
    while rleft > 0:
        dx, dy = DIRECTIONS[dname]
        sx, sy = sx + dx, sy + dy
        rleft -= 1
        if not in_bounds(sx, sy) or eng.is_high_wall(sx, sy) or eng.occupant[sy][sx] == "BOX":
            return None
        if eng.occupant[sy][sx] == "TNT":
            return ("TNT", sx, sy)
        t = eng.terrain[sy][sx]
        if t == "SWITCH":
            return ("SWITCH", sx, sy)
        if t == "MIMIC":
            return ("MIMIC", sx, sy)
        if t in MIRROR_MAP:
            dname = MIRROR_MAP[t][dname]
        elif t in PORTAL_PAIR_TILE and sp < 2:
            p_pair = eng.portals.get(PORTAL_PAIR_TILE[t])
            if p_pair is not None and eng.occupant[p_pair[1]][p_pair[0]] not in ("BOX", "TNT"):
                sx, sy = p_pair
                sp += 1
                if sp == 2:
                    return None
    if eng.terrain[sy][sx] in ("ICE", *MIRROR_MAP.keys()):
        for _ in range(32):
            dx, dy = DIRECTIONS[dname]
            sx, sy = sx + dx, sy + dy
            if not in_bounds(sx, sy) or eng.is_high_wall(sx, sy) or eng.occupant[sy][sx] == "BOX":
                return None
            if eng.occupant[sy][sx] == "TNT":
                return ("TNT", sx, sy)
            t = eng.terrain[sy][sx]
            if t == "SWITCH":
                return ("SWITCH", sx, sy)
            if t == "MIMIC":
                return ("MIMIC", sx, sy)
            if t in MIRROR_MAP:
                dname = MIRROR_MAP[t][dname]
            elif t == "ICE":
                continue
            elif t in PORTAL_PAIR_TILE and sp < 2:
                p_pair = eng.portals.get(PORTAL_PAIR_TILE[t])
                if p_pair is not None and eng.occupant[p_pair[1]][p_pair[0]] not in ("BOX", "TNT"):
                    sx, sy = p_pair
                    sp += 1
                    if sp == 2:
                        return None
                else:
                    return None
            else:
                return None
    return None


def canonical_hero_anchor(eng: DungeonEngineV22):
    """Canonical representative (min cell) of hero's zero-cost reversible walking component."""
    plates_on = eng.is_plates_active()
    gf = eng.gates_flipped
    terrain = eng.terrain
    occupant = eng.occupant
    sx, sy = eng.hx, eng.hy
    best = (sx, sy)
    vis = {(sx, sy)}
    q = collections.deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        if (x, y) < best:
            best = (x, y)
        for dname, (dx, dy) in DIRECTIONS.items():
            nx, ny = x + dx, y + dy
            if (nx, ny) in vis or not in_bounds(nx, ny):
                continue
            t = terrain[ny][nx]
            if t not in ("EMPTY", "PLATE") and not (t == "R_GATE" and gf) and not (t == "B_GATE" and not gf) and not (t == "P_GATE" and plates_on):
                continue
            if occupant[ny][nx] is not None:
                continue
            # Also require reverse step to be reversible (already true since t is not ONEWAY/ICE/CRACK/SPRING/PORTAL)
            vis.add((nx, ny))
            q.append((nx, ny))
    return best


def world_signature(eng: DungeonEngineV22, period: int):
    boxes = []
    tnts = []
    cracks_cnt = 0
    walls_hash = 0
    for y in range(1, GRID_HEIGHT - 1):
        trow = eng.terrain[y]
        orow = eng.occupant[y]
        for x in range(1, GRID_WIDTH - 1):
            o = orow[x]
            if o == "BOX":
                boxes.append((x, y))
            elif o == "TNT":
                tnts.append((x, y))
            t = trow[x]
            if t == "CRACK":
                cracks_cnt += 1
            elif t in ("W", *ALL_LASER_DIR.keys(), "MIMIC", "HEAL", "PIT"):
                walls_hash ^= hash((x, y, t))
    anchor = canonical_hero_anchor(eng)
    return (
        anchor[0], anchor[1],
        eng.has_k1, eng.has_k2, eng.gates_flipped,
        eng.jumps, eng.throws, eng.bombs_inv,
        tuple(boxes), tuple(tnts), cracks_cnt, walls_hash,
    )


def is_cell_permanently_box_locked(eng: DungeonEngineV22, bx: int, by: int) -> bool:
    """True if a BOX at (bx, by) can NEVER be pushed out of (bx, by) (even if all W/gates open)."""
    def perm_blk(tx, ty, push_dir, stand_x, stand_y):
        if not in_bounds(tx, ty) or not in_bounds(stand_x, stand_y):
            return True
        if eng.terrain[ty][tx] in ("T_W", "K1", "K2", "V") or eng.blocks_oneway(tx, ty, push_dir):
            return True
        if eng.terrain[stand_y][stand_x] == "T_W" or eng.blocks_oneway(bx, by, push_dir):
            return True
        return False

    h_blk = perm_blk(bx + 1, by, "R", bx - 1, by) and perm_blk(bx - 1, by, "L", bx + 1, by)
    v_blk = perm_blk(bx, by + 1, "D", bx, by - 1) and perm_blk(bx, by - 1, "U", bx, by + 1)
    return h_blk and v_blk


def compute_box_push_reach(eng: DungeonEngineV22, bx0: int, by0: int) -> set:
    """Relaxed set of cells a single BOX starting at (bx0, by0) could ever reach or fill."""
    terrain = eng.terrain
    portals = eng.portals
    vis = {(bx0, by0)}
    q = collections.deque([(bx0, by0)])

    while q:
        x, y = q.popleft()
        if terrain[y][x] == "PIT":
            continue  # Box vanishes after filling PIT!
        for dname, (dx, dy) in DIRECTIONS.items():
            sx, sy = x - dx, y - dy
            nx, ny = x + dx, y + dy
            if not in_bounds(sx, sy) or not in_bounds(nx, ny):
                continue
            if terrain[sy][sx] == "T_W":
                continue
            if terrain[ny][nx] in ("T_W", "K1", "K2", "V") or eng.blocks_oneway(nx, ny, dname):
                continue

            # Trace relaxed momentum (ICE / MIRROR / SPRING / PORTAL)
            cx, cy, cd = nx, ny, dname
            for _ in range(32):
                if (cx, cy) not in vis:
                    vis.add((cx, cy))
                    q.append((cx, cy))
                ct = terrain[cy][cx]
                if ct == "PIT":
                    break
                if ct == "ICE":
                    ddx, ddy = DIRECTIONS[cd]
                    nnx, nny = cx + ddx, cy + ddy
                    if not in_bounds(nnx, nny) or terrain[nny][nnx] in ("T_W", "K1", "K2", "V") or eng.blocks_oneway(nnx, nny, cd):
                        break
                    # Note: another box or closed gate could also stop it earlier, so intermediate cells already added to vis!
                    cx, cy = nnx, nny
                elif ct in MIRROR_MAP:
                    cd = MIRROR_MAP[ct][cd]
                    ddx, ddy = DIRECTIONS[cd]
                    nnx, nny = cx + ddx, cy + ddy
                    if not in_bounds(nnx, nny) or terrain[nny][nnx] in ("T_W", "K1", "K2", "V") or eng.blocks_oneway(nnx, nny, cd):
                        break
                    cx, cy = nnx, nny
                elif ct in SPRING_DIR:
                    cd = SPRING_DIR[ct]
                    ddx, ddy = DIRECTIONS[cd]
                    for kk in (1, 2, 3):
                        kx, ky = cx + kk * ddx, cy + kk * ddy
                        if not in_bounds(kx, ky) or terrain[ky][kx] in ("T_W", "K1", "K2", "V") or eng.blocks_oneway(kx, ky, cd):
                            break
                        if (kx, ky) not in vis:
                            vis.add((kx, ky))
                            q.append((kx, ky))
                    break
                elif ct in PORTAL_PAIR_TILE and PORTAL_PAIR_TILE[ct] in portals:
                    pp = portals[PORTAL_PAIR_TILE[ct]]
                    if pp not in vis:
                        vis.add(pp)
                        q.append(pp)
                    cx, cy = pp
                else:
                    break
    return vis


def can_ever_win_relaxed(eng: DungeonEngineV22, box_reach_cache: dict = None) -> bool:
    """
    Exact Topological Jump + Bipartite Box-to-(Plates + Mandatory Pits) Deadlock Pruner!
    """
    terrain = eng.terrain
    portals = eng.portals
    has_pgate = any(terrain[y][x] == "P_GATE" for y in range(GRID_HEIGHT) for x in range(GRID_WIDTH))

    boxes = [
        (x, y)
        for y in range(1, GRID_HEIGHT - 1)
        for x in range(1, GRID_WIDTH - 1)
        if eng.occupant[y][x] == "BOX"
    ]
    mobile_boxes = 0
    locked_plate_boxes = 0
    for x, y in boxes:
        if is_cell_permanently_box_locked(eng, x, y):
            if terrain[y][x] == "PLATE":
                locked_plate_boxes += 1
        else:
            mobile_boxes += 1

    def reachable_without_pgate_and_pits(sx, sy, goal_pt):
        vis = {(sx, sy)}
        q = collections.deque([(sx, sy)])
        while q:
            cx, cy = q.popleft()
            if (cx, cy) == goal_pt:
                return True
            for dn, (dx, dy) in DIRECTIONS.items():
                nx, ny = cx + dx, cy + dy
                if not in_bounds(nx, ny) or (nx, ny) in vis:
                    continue
                nt = terrain[ny][nx]
                if nt in ("T_W", "P_GATE") or (nt in ONEWAY_DIR and ONEWAY_DIR[nt] != dn):
                    continue
                vis.add((nx, ny))
                q.append((nx, ny))
                if nt in PORTAL_PAIR_TILE and PORTAL_PAIR_TILE[nt] in portals:
                    pp = portals[PORTAL_PAIR_TILE[nt]]
                    if pp not in vis:
                        vis.add(pp)
                        q.append(pp)
        return False

    v = tuple(eng.targets["V"])
    needs_plates = has_pgate and not reachable_without_pgate_and_pits(eng.hx, eng.hy, v)
    if needs_plates:
        plates_still_needing_mobile = max(0, len(eng.plates) - locked_plate_boxes)
        if mobile_boxes < plates_still_needing_mobile:
            return False
        num_boxes = mobile_boxes - plates_still_needing_mobile
    else:
        num_boxes = mobile_boxes

    max_total = eng.jumps + num_boxes

    def min_res_from(sx, sy, targets_set):
        # Track (total_res_used, boxes_used)
        best_r = {(sx, sy): (0, 0)}
        dq = collections.deque([(0, 0, sx, sy)])
        while dq:
            tot_u, box_u, x, y = dq.popleft()
            if (tot_u, box_u) > best_r.get((x, y), (999, 999)):
                continue
            if (x, y) in targets_set:
                return tot_u, box_u
            for dname, (dx, dy) in DIRECTIONS.items():
                nx, ny = x + dx, y + dy
                if not in_bounds(nx, ny):
                    continue
                t = terrain[ny][nx]
                if t == "T_W" or (t in ONEWAY_DIR and ONEWAY_DIR[t] != dname):
                    continue
                if t == "PIT":
                    # Option A: fill PIT with a BOX (if box_u < num_boxes)
                    if box_u + 1 <= num_boxes and tot_u + 1 <= max_total:
                        cand = (tot_u + 1, box_u + 1)
                        if cand < best_r.get((nx, ny), (999, 999)):
                            best_r[(nx, ny)] = cand
                            dq.append((cand[0], cand[1], nx, ny))
                    # Option B: straight JUMP over (nx, ny) to (x+2dx, y+2dy)!
                    jx, jy = x + 2 * dx, y + 2 * dy
                    if in_bounds(jx, jy):
                        jt = terrain[jy][jx]
                        if jt not in ("T_W", "PIT") and not (jt in ONEWAY_DIR and ONEWAY_DIR[jt] != dname):
                            if (tot_u - box_u) + 1 <= eng.jumps and tot_u + 1 <= max_total:
                                cand = (tot_u + 1, box_u)
                                if cand < best_r.get((jx, jy), (999, 999)):
                                    best_r[(jx, jy)] = cand
                                    dq.append((cand[0], cand[1], jx, jy))
                    continue

                cand = (tot_u, box_u)
                if cand < best_r.get((nx, ny), (999, 999)):
                    best_r[(nx, ny)] = cand
                    dq.appendleft((tot_u, box_u, nx, ny))
                    if t in PORTAL_PAIR_TILE:
                        pp = portals.get(PORTAL_PAIR_TILE[t])
                        if pp is not None and cand < best_r.get(pp, (999, 999)):
                            best_r[pp] = cand
                            dq.appendleft((tot_u, box_u, pp[0], pp[1]))
                    elif t in SPRING_DIR:
                        sdx, sdy = DIRECTIONS[SPRING_DIR[t]]
                        for kk in (1, 2, 3):
                            kx, ky = nx + kk * sdx, ny + kk * sdy
                            if not in_bounds(kx, ky) or terrain[ky][kx] == "T_W":
                                break
                            if terrain[ky][kx] != "PIT" and cand < best_r.get((kx, ky), (999, 999)):
                                best_r[(kx, ky)] = cand
                                dq.appendleft((tot_u, box_u, kx, ky))
        return 999, 999

    req = []
    if not eng.has_k1:
        req.append(tuple(eng.targets["K1"]))
    if not eng.has_k2:
        req.append(tuple(eng.targets["K2"]))

    # Also verify Bipartite Box Matching: all required PLATEs + each goal requiring >=1 box-filled PIT
    # must be simultaneously satisfiable by DISTINCT boxes!
    if box_reach_cache is None:
        box_reaches = [compute_box_push_reach(eng, bx, by) for bx, by in boxes]
    else:
        box_reaches = []
        for bx, by in boxes:
            if (bx, by) not in box_reach_cache:
                box_reach_cache[(bx, by)] = compute_box_push_reach(eng, bx, by)
            box_reaches.append(box_reach_cache[(bx, by)])
    sink_groups = []
    if needs_plates:
        for p in eng.plates:
            sink_groups.append({p})

    saved_nb = num_boxes
    num_boxes = 0
    max_total = eng.jumps
    # Compute all cells reachable from Hero using 0 boxes and <= eng.jumps
    _, zero_box_vis = min_res_from(eng.hx, eng.hy, {(-1, -1)}) if False else (0, None)
    for g_pt in req + [v]:
        tr0, _ = min_res_from(eng.hx, eng.hy, {g_pt})
        if tr0 > eng.jumps:
            # Reverse BFS from g_pt stopping as soon as we cross PITs into Hero's 0-box side (only step out of PIT if still PIT!)
            rev_pits = set()
            rq = collections.deque([g_pt])
            rvis = {g_pt}
            while rq:
                rcx, rcy = rq.popleft()
                cur_is_pit = (terrain[rcy][rcx] == "PIT")
                for dn, (dx, dy) in DIRECTIONS.items():
                    px, py = rcx - dx, rcy - dy
                    if not in_bounds(px, py) or (px, py) in rvis:
                        continue
                    if terrain[rcy][rcx] in ONEWAY_DIR and ONEWAY_DIR[terrain[rcy][rcx]] != dn:
                        continue
                    pt_t = terrain[py][px]
                    if pt_t == "T_W":
                        continue
                    # Note: also treat W around sealed K2 corridor? No, K2 roof is 3-thick W, Wait: in God-mode W is open!
                    # Wait: if K2 roof is W (not T_W!), can a 2-bomb hero breach 3-thick W? NO!
                    if pt_t == "PIT":
                        rvis.add((px, py))
                        rev_pits.add((px, py))
                        rq.append((px, py))
                    elif not cur_is_pit and pt_t != "W":
                        rvis.add((px, py))
                        rq.append((px, py))
            if rev_pits:
                sink_groups.append(rev_pits)

    num_boxes = saved_nb
    max_total = eng.jumps + num_boxes

    if sink_groups:
        if len(sink_groups) > len(boxes):
            return False
        cand_lists = [
            [bi for bi, br in enumerate(box_reaches) if br & sset]
            for sset in sink_groups
        ]
        if any(not cl for cl in cand_lists):
            return False
        used_b = [False] * len(boxes)

        def match_dfs(idx):
            if idx == len(cand_lists):
                return True
            for bi in cand_lists[idx]:
                if not used_b[bi]:
                    used_b[bi] = True
                    if match_dfs(idx + 1):
                        return True
                    used_b[bi] = False
            return False

        cand_lists.sort(key=len)
        if not match_dfs(0):
            return False

    if len(req) == 0:
        t1, b1 = min_res_from(eng.hx, eng.hy, {v})
        return b1 <= num_boxes and (t1 - b1) <= eng.jumps
    elif len(req) == 1:
        t1, b1 = min_res_from(eng.hx, eng.hy, {req[0]})
        if b1 > num_boxes or (t1 - b1) > eng.jumps:
            return False
        t2, b2 = min_res_from(req[0][0], req[0][1], {v})
        return max(b1, b2) <= num_boxes and ((t1 - b1) + (t2 - b2)) <= eng.jumps
    else:
        k1, k2 = req[0], req[1]
        for first_k, second_k in ((k1, k2), (k2, k1)):
            t1, b1 = min_res_from(eng.hx, eng.hy, {first_k})
            t2, b2 = min_res_from(first_k[0], first_k[1], {second_k})
            t3, b3 = min_res_from(second_k[0], second_k[1], {v})
            jtot = (t1 - b1) + (t2 - b2) + (t3 - b3)
            if max(b1, b2, b3) <= num_boxes and jtot <= eng.jumps:
                return True
        return False


def is_box_static_corner_deadlock(eng: DungeonEngineV22, bx: int, by: int) -> bool:
    if eng.terrain[by][bx] == "PLATE":
        return False
    for dname, (dx, dy) in DIRECTIONS.items():
        for dist in range(1, 11):
            nx, ny = bx - dist * dx, by - dist * dy
            if not in_bounds(nx, ny):
                break
            t = eng.terrain[ny][nx]
            if t in ALL_LASER_DIR and ALL_LASER_DIR[t] == dname:
                return False
            if t == "T_W":
                break

    def perm_blocked(tx, ty, push_dir, stand_x, stand_y):
        if not in_bounds(tx, ty) or not in_bounds(stand_x, stand_y):
            return True
        if eng.terrain[ty][tx] in ("T_W", "K1", "K2", "V") or eng.blocks_oneway(tx, ty, push_dir):
            return True
        if eng.terrain[stand_y][stand_x] == "T_W" or eng.blocks_oneway(bx, by, push_dir):
            return True
        return False

    h_blk = perm_blocked(bx + 1, by, "R", bx - 1, by) and perm_blocked(bx - 1, by, "L", bx + 1, by)
    v_blk = perm_blocked(bx, by + 1, "D", bx, by - 1) and perm_blocked(bx, by - 1, "U", bx, by + 1)
    return h_blk and v_blk


def heuristic_v22(eng: DungeonEngineV22, has_pgates: bool, goal_pits: list) -> float:
    h = 0.0
    k1 = tuple(eng.targets["K1"])
    k2 = tuple(eng.targets["K2"])
    v = tuple(eng.targets["V"])
    pos = (eng.hx, eng.hy)

    if not eng.has_k1 and not eng.has_k2:
        d_keys = min(
            manhattan(pos, k1) + manhattan(k1, k2) + manhattan(k2, v),
            manhattan(pos, k2) + manhattan(k2, k1) + manhattan(k1, v),
        )
        h += 75.0 * 2 + 0.9 * d_keys
    elif not eng.has_k1:
        h += 75.0 + 0.9 * (manhattan(pos, k1) + manhattan(k1, v))
    elif not eng.has_k2:
        h += 75.0 + 0.9 * (manhattan(pos, k2) + manhattan(k2, v))
    else:
        h += 0.9 * manhattan(pos, v)

    boxes = [
        (x, y)
        for y in range(1, GRID_HEIGHT - 1)
        for x in range(1, GRID_WIDTH - 1)
        if eng.occupant[y][x] == "BOX"
    ]

    if has_pgates and eng.plates:
        uncovered = [p for p in eng.plates if eng.occupant[p[1]][p[0]] != "BOX"]
        free_boxes = [b for b in boxes if eng.terrain[b[1]][b[0]] != "PLATE"]
        h += 45.0 * len(uncovered)
        if uncovered and free_boxes:
            for up in uncovered:
                h += 2.5 * min(manhattan(b, up) for b in free_boxes)

    h += 6.0 * (3 - eng.jumps) + 3.0 * (3 - eng.throws) + 8.0 * (2 - eng.bombs_inv)
    h += 2.5 * (100 - eng.hp)
    return h


def solve_full_dungeon(initial_eng: DungeonEngineV22, time_budget: float = 1.55):
    t0 = time.monotonic()
    deadline = t0 + time_budget

    has_pgates = any(
        initial_eng.terrain[y][x] == "P_GATE"
        for y in range(GRID_HEIGHT)
        for x in range(GRID_WIDTH)
    )
    num_plates = len(initial_eng.plates)
    _, _, init_period, _ = compute_laser_info(initial_eng)
    box_reach_cache = {}
    relax_memo = {}

    goal_pits = []
    for y in range(1, GRID_HEIGHT - 1):
        for x in range(1, GRID_WIDTH - 1):
            if initial_eng.terrain[y][x] == "PIT":
                walls_adj = sum(
                    1 for dx, dy in DIRECTIONS.values()
                    if initial_eng.terrain[y + dy][x + dx] in ("T_W", "W")
                )
                if walls_adj >= 2:
                    goal_pits.append((x, y))

    for allow_dmg in (False, True):
        if time.monotonic() >= deadline:
            break
        sub_deadline = deadline if allow_dmg else (t0 + time_budget * 0.78)

        uid = 0
        h0 = heuristic_v22(initial_eng, has_pgates, goal_pits)
        pq = [(h0, 0.0, uid, initial_eng, ())]
        best_g = {world_signature(initial_eng, init_period): 0.0}

        while pq and time.monotonic() < sub_deadline:
            f_val, g_val, _, eng, macro_path = heapq.heappop(pq)
            sig = world_signature(eng, init_period)
            if g_val > best_g.get(sig, 1e18) + 1e-6:
                continue

            best_at_cell, reconstruct, special_hits, win_nav = fast_hero_nav(eng, allow_damage=allow_dmg)
            if win_nav is not None:
                full_sol = list(macro_path + win_nav)
                v_eng = initial_eng.clone()
                for a in full_sol:
                    v_eng.step(a)
                if v_eng.status == "CLEARED":
                    return full_sol

            def push_child(nav_acts, extra_acts, extra_penalty=0.0):
                nonlocal uid
                tot_acts = macro_path + nav_acts + extra_acts
                if len(tot_acts) > MAX_TURNS:
                    return None
                c_eng = eng.clone()
                hp_before = c_eng.hp
                for a in nav_acts + extra_acts:
                    c_eng.step(a)
                    if c_eng.status in ("DEAD", "CLEARED"):
                        break
                if c_eng.status == "DEAD":
                    return None
                if not allow_dmg and c_eng.hp < hp_before:
                    return None
                if c_eng.status == "CLEARED":
                    return list(tot_acts)

                # Only invoke topological deadlock check when scarce resources or topology changed!
                if (
                    c_eng.jumps < eng.jumps
                    or c_eng.has_k1 != eng.has_k1
                    or c_eng.has_k2 != eng.has_k2
                    or c_eng.terrain[c_eng.hy][c_eng.hx] in ONEWAY_DIR
                    or any(a.startswith("MOVE_") for a in extra_acts)
                ):
                    if c_eng.jumps < eng.jumps or c_eng.has_k1 != eng.has_k1 or c_eng.has_k2 != eng.has_k2 or any(a.startswith("MOVE_") for a in extra_acts) or not has_pgates:
                        rm_key = (
                            canonical_hero_anchor(c_eng), c_eng.has_k1, c_eng.has_k2, c_eng.jumps,
                            tuple((x, y) for y in range(1, GRID_HEIGHT - 1) for x in range(1, GRID_WIDTH - 1) if c_eng.occupant[y][x] == "BOX"),
                            sum(1 for y in range(1, GRID_HEIGHT - 1) for x in range(1, GRID_WIDTH - 1) if c_eng.terrain[y][x] == "PIT"),
                        )
                        ok_rel = relax_memo.get(rm_key)
                        if ok_rel is None:
                            ok_rel = can_ever_win_relaxed(c_eng, box_reach_cache)
                            relax_memo[rm_key] = ok_rel
                        if not ok_rel:
                            return None

                if has_pgates and not c_eng.is_plates_active():
                    usable_boxes = 0
                    for by in range(1, GRID_HEIGHT - 1):
                        for bx in range(1, GRID_WIDTH - 1):
                            if c_eng.occupant[by][bx] == "BOX" and not is_box_static_corner_deadlock(c_eng, bx, by):
                                usable_boxes += 1
                    if usable_boxes < num_plates:
                        return None

                new_g = float(c_eng.turn) + 2.5 * (100 - c_eng.hp) + extra_penalty
                nsig = world_signature(c_eng, init_period)
                if new_g < best_g.get(nsig, 1e18):
                    best_g[nsig] = new_g
                    uid += 1
                    nh = heuristic_v22(c_eng, has_pgates, goal_pits)
                    # Weighted A* factor 1.35 speeds up deep multi-box Sokoban convergence dramatically!
                    heapq.heappush(pq, (new_g + 1.35 * nh, new_g, uid, c_eng, tot_acts))
                return None

            # 1. Special walk events: K1, K2, SWITCH, HEAL, MIMIC
            for (ekind, ex, ey, _ej), (ecost, pnid, lact) in special_hits.items():
                if ekind == "HEAL" and eng.hp == 100:
                    continue
                epath = reconstruct(pnid, lact)
                win_sol = push_child(epath, ())
                if win_sol is not None:
                    return win_sol

            # 2. Push reachable BOXes!
            for by in range(1, GRID_HEIGHT - 1):
                for bx in range(1, GRID_WIDTH - 1):
                    if eng.occupant[by][bx] != "BOX":
                        continue
                    for dname, (dx, dy) in DIRECTIONS.items():
                        sx, sy = bx - dx, by - dy
                        p2x, p2y = bx + dx, by + dy
                        if (sx, sy) not in best_at_cell:
                            continue
                        if eng.is_high_wall(bx, by) or eng.blocks_oneway(bx, by, dname):
                            continue
                        if not in_bounds(p2x, p2y) or eng.is_high_wall(p2x, p2y) or eng.blocks_oneway(p2x, p2y, dname):
                            continue
                        if eng.occupant[p2y][p2x] is not None or eng.terrain[p2y][p2x] in ("K1", "K2", "V"):
                            continue
                        _, nid, _ = best_at_cell[(sx, sy)]
                        win_sol = push_child(reconstruct(nid), ("MOVE_" + dname,))
                        if win_sol is not None:
                            return win_sol

            # 3. Remote THROW at SWITCH / TNT / MIMIC (pre-filter aligned rows/cols for 15x speed)!
            walkable_switches = {(ex, ey) for (ekind, ex, ey, _ej) in special_hits if ekind == "SWITCH"}
            if eng.throws > 0:
                interest_rows = set()
                interest_cols = set()
                for ty_i in range(1, GRID_HEIGHT - 1):
                    trow = eng.terrain[ty_i]
                    orow = eng.occupant[ty_i]
                    for tx_i in range(1, GRID_WIDTH - 1):
                        tt = trow[tx_i]
                        if orow[tx_i] == "TNT" or tt in ("MIMIC", *MIRROR_MAP.keys(), *PORTAL_PAIR_TILE.keys()) or (tt == "SWITCH" and (tx_i, ty_i) not in walkable_switches):
                            interest_rows.add(ty_i)
                            interest_cols.add(tx_i)
                best_throws = {}
                if interest_rows:
                    for (vx, vy), (rcost, nid, _rj) in best_at_cell.items():
                        if vy not in interest_rows and vx not in interest_cols:
                            continue
                        if eng.terrain[vy][vx] in ("ICE", *MIRROR_MAP.keys(), *SPRING_DIR.keys(), *PORTAL_PAIR_TILE.keys()):
                            continue
                        for dname in ("U", "D", "L", "R"):
                            if dname in ("L", "R") and vy not in interest_rows:
                                continue
                            if dname in ("U", "D") and vx not in interest_cols:
                                continue
                            hit = trace_stone_from(eng, vx, vy, dname)
                            if hit is None:
                                continue
                            hkind, tx, ty = hit
                            if hkind == "SWITCH" and (tx, ty) in walkable_switches:
                                continue
                            if hkind == "TNT" and abs(vx - tx) <= 1 and abs(vy - ty) <= 1:
                                continue
                            tkey = (hkind, tx, ty)
                            if rcost < best_throws.get(tkey, (1e18, None, None))[0]:
                                best_throws[tkey] = (rcost, nid, "THROW_" + dname)
                    for _, (_, nid, tact) in best_throws.items():
                        win_sol = push_child(reconstruct(nid), (tact,), extra_penalty=18.0)
                        if win_sol is not None:
                            return win_sol

            # 4. Strategic BOMB breach (topological cut-wall filter + diverse target buckets)!
            if eng.bombs_inv > 0 and not eng.bombs:
                no_jump_cells = {pos for pos, (_, _, rj) in best_at_cell.items() if rj == eng.jumps}
                bomb_cands = []
                for (bx, by), (rcost, nid, _rj) in best_at_cell.items():
                    if _rj < eng.jumps:
                        continue
                    if eng.terrain[by][bx] in ("ICE", *MIRROR_MAP.keys(), *SPRING_DIR.keys(), *PORTAL_PAIR_TILE.keys()):
                        continue
                    opens_new_space = False
                    crater_breaches_room = False
                    destroys_laser = False
                    near_active_target = 999
                    active_lms = []
                    if not eng.has_k1:
                        active_lms.append(eng.targets["K1"])
                    if not eng.has_k2:
                        active_lms.append(eng.targets["K2"])
                    if eng.has_k1 and eng.has_k2:
                        active_lms.append(eng.targets["V"])

                    blast_set = {
                        (bx + dx, by + dy)
                        for dy in (-1, 0, 1)
                        for dx in (-1, 0, 1)
                        if in_bounds(bx + dx, by + dy) and eng.terrain[by + dy][bx + dx] != "T_W"
                    }
                    for wx, wy in blast_set:
                        wt = eng.terrain[wy][wx]
                        wo = eng.occupant[wy][wx]
                        if wt in ALL_LASER_DIR:
                            destroys_laser = True
                        if wt in DESTRUCTIBLE_WALLS or wo == "TNT":
                            for tlm in active_lms:
                                near_active_target = min(near_active_target, manhattan((wx, wy), tlm))
                            for adx, ady in DIRECTIONS.values():
                                ux, uy = wx + adx, wy + ady
                                if in_bounds(ux, uy) and (ux, uy) not in no_jump_cells:
                                    ut = eng.terrain[uy][ux]
                                    if not eng.is_high_wall(ux, uy) and ut != "PIT" and eng.occupant[uy][ux] != "TNT":
                                        opens_new_space = True
                                        if (ux, uy) not in blast_set:
                                            crater_breaches_room = True
                                    elif eng.bombs_inv >= 2 and ut in DESTRUCTIBLE_WALLS:
                                        for bdx, bdy in DIRECTIONS.values():
                                            u2x, u2y = ux + bdx, uy + bdy
                                            if in_bounds(u2x, u2y) and (u2x, u2y) not in no_jump_cells and not eng.is_high_wall(u2x, u2y) and eng.terrain[u2y][u2x] != "PIT":
                                                opens_new_space = True
                                                break
                    if opens_new_space or (allow_dmg and destroys_laser):
                        bomb_cands.append((0 if crater_breaches_room else 1, near_active_target, rcost, bx, by, nid))

                by_target = sorted(bomb_cands, key=lambda it: (it[0], it[1], it[2]))
                by_local = sorted(bomb_cands, key=lambda it: (it[0], it[2], it[1]))
                dedup_bombs = []
                for pool, cap in ((by_target, 4), (by_local, 7)):
                    for item in pool:
                        _, _, _, bx, by, _ = item
                        if all(manhattan((bx, by), (ox, oy)) >= 2 for _, _, _, ox, oy, _ in dedup_bombs):
                            dedup_bombs.append(item)
                            if len(dedup_bombs) >= cap:
                                break
                for cb_flag, _, _, bx, by, nid in dedup_bombs:
                    npath = reconstruct(nid)
                    b_eng = eng.clone()
                    ok_nav = True
                    for a in npath:
                        b_eng.step(a)
                        if b_eng.status != "ALIVE" or (not allow_dmg and b_eng.hp < eng.hp):
                            ok_nav = False
                            break
                    if not ok_nav or (b_eng.hx, b_eng.hy) != (bx, by):
                        continue
                    b_eng.step("BOMB")
                    if b_eng.status != "ALIVE" or (not allow_dmg and b_eng.hp < eng.hp):
                        continue
                    found_dodge = None
                    dodge_moves = ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT", "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R")
                    for d1 in dodge_moves:
                        if d1.startswith("JUMP_") and b_eng.jumps <= 0:
                            continue
                        e1 = b_eng.clone()
                        e1.step(d1)
                        if e1.status == "CLEARED":
                            return list(macro_path + npath + ("BOMB", d1))
                        if e1.status != "ALIVE" or (not allow_dmg and e1.hp < eng.hp):
                            continue
                        for d2 in dodge_moves:
                            if d2.startswith("JUMP_") and e1.jumps <= 0:
                                continue
                            e2 = e1.clone()
                            e2.step(d2)
                            if e2.status == "CLEARED":
                                return list(macro_path + npath + ("BOMB", d1, d2))
                            if e2.status == "ALIVE" and (allow_dmg or e2.hp == eng.hp):
                                found_dodge = ("BOMB", d1, d2)
                                break
                        if found_dodge is not None:
                            break
                    if found_dodge is not None:
                        win_sol = push_child(npath, found_dodge, extra_penalty=(32.0 if cb_flag == 0 else 65.0))
                        if win_sol is not None:
                            return win_sol

    return None


def run_benchmark_all():
    with open("v22_sparring_benchmarks.json", "r", encoding="utf-8") as f:
        sparring = json.load(f)["dungeons"]
    with open("part1_dungeons_benchmark.json", "r", encoding="utf-8") as f:
        part1 = json.load(f)["dungeons"]

    all_tests = [
        ("V22_BENCH_WEAK", sparring["BENCH_WEAK"]["grid"]),
        ("V22_BENCH_STRONG", sparring["BENCH_STRONG"]["grid"]),
    ] + [(f"P1_{k}", v["grid"]) for k, v in part1.items()]

    cleared_cnt = 0
    for name, grid in all_tests:
        ok, msg, dec = validate_and_decode_grid_v22(grid, check_spawn_4turn=False)
        assert ok, f"{name}: {msg}"
        eng = DungeonEngineV22(dec)
        obs = eng.get_observation()
        sim_eng = decode_full_observation_to_engine(obs)
        sim_eng.spent_gold = dec["spent_gold"]

        t0 = time.monotonic()
        sol = solve_full_dungeon(sim_eng, time_budget=1.55)
        dt_ms = (time.monotonic() - t0) * 1000.0

        if sol is not None:
            for a in sol:
                eng.step(a)
        h_score, d_score = eng.compute_scores()
        if eng.status == "CLEARED":
            cleared_cnt += 1
        print(
            f"[{name:20s}] Status={eng.status:7s} | Steps={eng.turn:3d} | HP={eng.hp:3d} | "
            f"HeroScore={h_score:6.1f} | SolveTime={dt_ms:6.1f}ms"
        )
    print(f"\nSUMMARY: CLEARED {cleared_cnt} / {len(all_tests)} MAPS!")


if __name__ == "__main__":
    run_benchmark_all()
