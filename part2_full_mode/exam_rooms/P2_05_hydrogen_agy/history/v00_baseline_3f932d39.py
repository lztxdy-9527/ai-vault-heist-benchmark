import heapq
from collections import deque

GRID_WIDTH = 40
GRID_HEIGHT = 26
MAX_BUDGET = 3000
MAX_TURNS = 240
SPAWN_POS = (2, 13)

VALID_ACTIONS = (
    "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R",
    "WAIT",
    "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
    "THROW_U", "THROW_D", "THROW_L", "THROW_R",
    "BOMB",
)

DIRECTIONS = {
    "U": (0, -1),
    "D": (0, 1),
    "L": (-1, 0),
    "R": (1, 0),
}

MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}

TILE_COSTS = {
    "EMPTY": 0,
    "K1": 0, "K2": 0, "V": 0,
    "W": 5,
    "T_W": 25,
    "ICE": 10,
    "MIRROR_NE": 25, "MIRROR_SE": 25, "MIRROR_SW": 25, "MIRROR_NW": 25,
    "SPRING_U": 35, "SPRING_D": 35, "SPRING_L": 35, "SPRING_R": 35,
    "PIT": 40,
    "LASER_U": 75, "LASER_D": 75, "LASER_L": 75, "LASER_R": 75,
    "CRACK": 20,
    "SWITCH": 30,
    "R_GATE": 20, "B_GATE": 20,
    "TNT": 40,
    "BOX": 30,
    "HEAL": 30,
    "MIMIC": 60,
    "PORTAL_1A": 40, "PORTAL_1B": 40,
    "PORTAL_2A": 40, "PORTAL_2B": 40,
}

LASER_TILES = {"LASER_U", "LASER_D", "LASER_L", "LASER_R"}
MIRROR_TILES = {"MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW"}
SPRING_TILES = {"SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R"}
PORTAL_TILES = {"PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B"}
PORTAL_PAIR_MAP = {
    "PORTAL_1A": "PORTAL_1B",
    "PORTAL_1B": "PORTAL_1A",
    "PORTAL_2A": "PORTAL_2B",
    "PORTAL_2B": "PORTAL_2A",
}


def _in_bounds(x, y):
    return 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT


def _is_high_wall_terrain(t, gates_flipped):
    if t in ("W", "T_W", "UNKNOWN") or t in LASER_TILES:
        return True
    if t == "R_GATE" and not gates_flipped:
        return True
    if t == "B_GATE" and gates_flipped:
        return True
    return False


def _chest_kind(x, y, terrain, seen, clues):
    if terrain[y][x] != "CHEST":
        return terrain[y][x]
    all_neighbors_seen = True
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nx, ny = x + dx, y + dy
        if not _in_bounds(nx, ny):
            continue
        if not seen[ny][nx]:
            all_neighbors_seen = False
        elif clues[ny][nx]:
            return "MIMIC"
    return "HEAL" if all_neighbors_seen else "CHEST_UNKNOWN"


def _compute_laser_hazards(memory, gates_flipped):
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    danger = set()
    uncertain = set()

    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            t = terrain[y][x]
            if t in LASER_TILES:
                dchar = t.split("_")[1]
                dx, dy = DIRECTIONS[dchar]
                hit_unknown = False
                for step in range(1, 11):
                    nx, ny = x + step * dx, y + step * dy
                    if not _in_bounds(nx, ny):
                        break
                    nt = terrain[ny][nx]
                    if nt == "UNKNOWN":
                        hit_unknown = True
                    if not hit_unknown:
                        if _is_high_wall_terrain(nt, gates_flipped) or occupant[ny][nx] in ("BOX", "TNT"):
                            break
                        danger.add((nx, ny))
                    else:
                        uncertain.add((nx, ny))

    active_warnings = []
    for (wx, wy, dchar) in memory["warning_rays"]:
        dx, dy = DIRECTIONS[dchar]
        explained_or_dead = False
        for step in range(1, 11):
            bx, by = wx - step * dx, wy - step * dy
            if not _in_bounds(bx, by):
                break
            bt = terrain[by][bx]
            if bt == f"LASER_{dchar}":
                explained_or_dead = True
                break
            if bt == "UNKNOWN":
                break
            if _is_high_wall_terrain(bt, gates_flipped) or occupant[by][bx] in ("BOX", "TNT"):
                explained_or_dead = True
                break
        if not explained_or_dead:
            active_warnings.append((wx, wy, dchar))
            danger.add((wx, wy))
            min_dist_from_turret = 10
            for step in range(1, 10):
                bx, by = wx - step * dx, wy - step * dy
                if not _in_bounds(bx, by):
                    break
                if terrain[by][bx] == "UNKNOWN":
                    min_dist_from_turret = step
                    break
            max_fwd = max(0, 10 - min_dist_from_turret)
            clear_set = memory.get("clear_laser_dir", set())
            for step in range(1, max_fwd + 1):
                fx, fy = wx + step * dx, wy + step * dy
                if not _in_bounds(fx, fy):
                    break
                if (fx, fy, dchar) in clear_set:
                    break
                ft = terrain[fy][fx]
                if ft != "UNKNOWN" and (_is_high_wall_terrain(ft, gates_flipped) or occupant[fy][fx] in ("BOX", "TNT")):
                    break
                if ft == "UNKNOWN":
                    uncertain.add((fx, fy))
                else:
                    danger.add((fx, fy))
    memory["warning_rays"] = active_warnings
    return danger, uncertain


def _compute_bomb_hazards(state, memory):
    bombs = state["bombs"]
    if not bombs:
        return {}
    occupant = memory["occupant"]
    hazards = {}
    for b in bombs:
        dt = b["timer"]
        if dt <= 0:
            continue
        q = deque([(b["x"], b["y"])])
        seen_src = {(b["x"], b["y"])}
        blast = set()
        while q:
            ex, ey = q.popleft()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    cx, cy = ex + dx, ey + dy
                    if _in_bounds(cx, cy):
                        blast.add((cx, cy))
                        if occupant[cy][cx] == "TNT" and (cx, cy) not in seen_src:
                            seen_src.add((cx, cy))
                            q.append((cx, cy))
        hazards.setdefault(dt, set()).update(blast)
    return hazards


def _sim_move_from(x, y, dchar, memory, gates_flipped, allow_unknown=False):
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    seen = memory["seen"]
    clues = memory["clues"]
    portals = memory["portals"]

    dx, dy = DIRECTIONS[dchar]
    p1 = (x + dx, y + dy)
    if not _in_bounds(*p1):
        return None
    t1 = terrain[p1[1]][p1[0]]
    if t1 == "UNKNOWN" and not allow_unknown:
        return None
    if _is_high_wall_terrain(t1, gates_flipped) or occupant[p1[1]][p1[0]] in ("BOX", "TNT"):
        return None

    cur_dir = dchar
    x0, y0 = x, y
    x1, y1 = p1
    steps = 0
    portal_count = 0
    stop_mom = False
    suppress_portal = False
    exposed = {(x, y)}
    cracks_broken = set()
    flipped = False
    hp_delta = 0
    entered_unknown = False
    touched_unknown_portal = False
    touched_unknown_chest = False

    def is_ent_ok(nx, ny, cur_gf, cur_cracks):
        if not _in_bounds(nx, ny):
            return False
        nt = terrain[ny][nx]
        if nt == "UNKNOWN":
            return allow_unknown
        if (nx, ny) in cur_cracks:
            return True
        if _is_high_wall_terrain(nt, cur_gf) or occupant[ny][nx] in ("BOX", "TNT"):
            return False
        return True

    while True:
        steps += 1
        if terrain[y0][x0] == "CRACK" and (x0, y0) not in cracks_broken:
            cracks_broken.add((x0, y0))

        exposed.add((x1, y1))
        t1 = terrain[y1][x1]
        if t1 == "UNKNOWN":
            entered_unknown = True
            break
        if (x1, y1) in cracks_broken:
            t1 = "PIT"

        if t1 == "PIT":
            hp_delta -= 100
            break
        elif t1 == "CHEST":
            ck = _chest_kind(x1, y1, terrain, seen, clues)
            if ck == "MIMIC":
                hp_delta -= 45
                stop_mom = True
            elif ck == "HEAL":
                hp_delta += 30
            else:
                touched_unknown_chest = True
                hp_delta -= 45
                stop_mom = True
        elif t1 == "SWITCH":
            flipped = not flipped

        if steps >= 32 or stop_mom:
            break

        cur_gf = gates_flipped ^ flipped
        sup = suppress_portal
        suppress_portal = False

        if t1 == "ICE":
            vx, vy = DIRECTIONS[cur_dir]
            nx, ny = x1 + vx, y1 + vy
            if not _in_bounds(nx, ny):
                break
            if terrain[ny][nx] == "UNKNOWN":
                entered_unknown = True
                break
            if is_ent_ok(nx, ny, cur_gf, cracks_broken):
                x0, y0 = x1, y1
                x1, y1 = nx, ny
                continue
            break

        elif t1 in MIRROR_TILES:
            cur_dir = MIRROR_MAP[t1][cur_dir]
            vx, vy = DIRECTIONS[cur_dir]
            nx, ny = x1 + vx, y1 + vy
            if not _in_bounds(nx, ny):
                break
            if terrain[ny][nx] == "UNKNOWN":
                entered_unknown = True
                break
            if is_ent_ok(nx, ny, cur_gf, cracks_broken):
                x0, y0 = x1, y1
                x1, y1 = nx, ny
                continue
            break

        elif t1 in SPRING_TILES:
            cur_dir = t1.split("_")[1]
            vx, vy = DIRECTIONS[cur_dir]
            blocked_k = None
            unk = False
            for k in (1, 2, 3):
                kx, ky = x1 + k * vx, y1 + k * vy
                if not _in_bounds(kx, ky):
                    blocked_k = k
                    break
                kt = terrain[ky][kx]
                if kt == "UNKNOWN":
                    unk = True
                    break
                if _is_high_wall_terrain(kt, cur_gf) or occupant[ky][kx] in ("BOX", "TNT"):
                    blocked_k = k
                    break
            if unk:
                entered_unknown = True
                break
            if blocked_k == 1:
                break
            land_k = (blocked_k - 1) if blocked_k in (2, 3) else 3
            x0, y0 = x1, y1
            x1, y1 = x1 + land_k * vx, y1 + land_k * vy
            continue

        elif t1 in PORTAL_TILES and not sup:
            pair_name = PORTAL_PAIR_MAP[t1]
            if pair_name not in portals:
                touched_unknown_portal = True
                break
            px, py = portals[pair_name]
            if occupant[py][px] is not None:
                break
            portal_count += 1
            steps += 1
            x1, y1 = px, py
            exposed.add((px, py))
            if steps >= 32 or portal_count >= 2:
                break
            vx, vy = DIRECTIONS[cur_dir]
            nx, ny = px + vx, py + vy
            if not _in_bounds(nx, ny):
                break
            if terrain[ny][nx] == "UNKNOWN":
                entered_unknown = True
                break
            if is_ent_ok(nx, ny, cur_gf, cracks_broken):
                x0, y0 = px, py
                x1, y1 = nx, ny
                continue
            break

        else:
            break

    return {
        "land": (x1, y1),
        "exposed": frozenset(exposed),
        "entered_unknown": entered_unknown,
        "cracks_broken": frozenset(cracks_broken),
        "flipped_switch": flipped,
        "hp_delta": hp_delta,
        "died": hp_delta <= -100,
        "touched_unknown_portal": touched_unknown_portal,
        "touched_unknown_chest": touched_unknown_chest,
    }


def _sim_jump_from(x, y, dchar, memory, gates_flipped, allow_unknown=False):
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    dx, dy = DIRECTIONS[dchar]
    p1 = (x + dx, y + dy)
    p2 = (x + 2 * dx, y + 2 * dy)
    if not _in_bounds(*p1) or not _in_bounds(*p2):
        return None
    t1 = terrain[p1[1]][p1[0]]
    t2 = terrain[p2[1]][p2[0]]
    if t1 == "UNKNOWN" or t2 == "UNKNOWN":
        return None
    if _is_high_wall_terrain(t1, gates_flipped) or _is_high_wall_terrain(t2, gates_flipped):
        return None
    if occupant[p2[1]][p2[0]] in ("BOX", "TNT"):
        return None
    # No point jumping over safe normal ground unless it's hazardous or laser-exposed
    res = _sim_move_from(p1[0], p1[1], dchar, memory, gates_flipped, allow_unknown=allow_unknown)
    if res is None:
        return None
    exposed = (res["exposed"] - {p1}) | {(x, y)}
    cracks_broken = set(res["cracks_broken"])
    if terrain[p1[1]][p1[0]] == "CRACK":
        cracks_broken.discard(p1)
    if terrain[y][x] == "CRACK":
        cracks_broken.add((x, y))
    return {
        "land": res["land"],
        "exposed": frozenset(exposed),
        "entered_unknown": res["entered_unknown"],
        "cracks_broken": frozenset(cracks_broken),
        "flipped_switch": res["flipped_switch"],
        "hp_delta": res["hp_delta"],
        "died": res["died"],
        "touched_unknown_portal": res["touched_unknown_portal"],
        "touched_unknown_chest": res["touched_unknown_chest"],
    }


def _sim_throw_from(x, y, dchar, memory, gates_flipped):
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    seen = memory["seen"]
    clues = memory["clues"]
    portals = memory["portals"]

    cur_dir = dchar
    sx, sy = x, y
    range_left = 6
    stone_portals = 0
    hit_switch = None
    hit_tnt = None
    hit_mimic = None
    shattered = False

    while range_left > 0:
        dx, dy = DIRECTIONS[cur_dir]
        nx, ny = sx + dx, sy + dy
        range_left -= 1
        sx, sy = nx, ny
        if not _in_bounds(sx, sy):
            shattered = True
            break
        t = terrain[sy][sx]
        if t == "UNKNOWN" or _is_high_wall_terrain(t, gates_flipped) or occupant[sy][sx] == "BOX":
            shattered = True
            break
        if occupant[sy][sx] == "TNT":
            hit_tnt = (sx, sy)
            shattered = True
            break
        if t == "SWITCH":
            hit_switch = (sx, sy)
            shattered = True
            break
        if t == "CHEST" and _chest_kind(sx, sy, terrain, seen, clues) == "MIMIC":
            hit_mimic = (sx, sy)
            shattered = True
            break
        if t in MIRROR_TILES:
            cur_dir = MIRROR_MAP[t][cur_dir]
        elif t in PORTAL_TILES and stone_portals < 2:
            pair_name = PORTAL_PAIR_MAP[t]
            if pair_name not in portals:
                shattered = True
                break
            px, py = portals[pair_name]
            if occupant[py][px] not in ("BOX", "TNT"):
                sx, sy = px, py
                stone_portals += 1
                if stone_portals == 2:
                    shattered = True
                    break

    if not shattered and range_left == 0 and _in_bounds(sx, sy):
        t = terrain[sy][sx]
        if t == "ICE" or t in MIRROR_TILES:
            for _ in range(32):
                dx, dy = DIRECTIONS[cur_dir]
                nx, ny = sx + dx, sy + dy
                if not _in_bounds(nx, ny):
                    break
                nt = terrain[ny][nx]
                if nt == "UNKNOWN" or _is_high_wall_terrain(nt, gates_flipped) or occupant[ny][nx] == "BOX":
                    break
                if occupant[ny][nx] == "TNT":
                    hit_tnt = (nx, ny)
                    break
                if nt == "SWITCH":
                    hit_switch = (nx, ny)
                    break
                if nt == "CHEST" and _chest_kind(nx, ny, terrain, seen, clues) == "MIMIC":
                    hit_mimic = (nx, ny)
                    break
                if nt in MIRROR_TILES:
                    sx, sy = nx, ny
                    cur_dir = MIRROR_MAP[nt][cur_dir]
                elif nt == "ICE":
                    sx, sy = nx, ny
                else:
                    break

    return {"hit_switch": hit_switch, "hit_tnt": hit_tnt, "hit_mimic": hit_mimic}


def _build_transition_graph(memory, gates_flipped, hero_hp, laser_danger):
    """Precompute safe 1-step MOVE and JUMP edges once per turn for fast Dijkstra."""
    terrain = memory["terrain"]
    move_edges = {}
    jump_edges = {}

    for y in range(1, GRID_HEIGHT - 1):
        for x in range(1, GRID_WIDTH - 1):
            t = terrain[y][x]
            if t == "UNKNOWN" or t == "PIT" or _is_high_wall_terrain(t, gates_flipped):
                continue
            if memory["occupant"][y][x] in ("BOX", "TNT"):
                continue

            m_list = []
            j_list = []
            for dchar in ("U", "D", "L", "R"):
                res = _sim_move_from(x, y, dchar, memory, gates_flipped, allow_unknown=False)
                if res and not res["entered_unknown"] and not res["touched_unknown_portal"] and not res["touched_unknown_chest"]:
                    if not res["died"] and res["hp_delta"] >= 0:
                        nx, ny = res["land"]
                        flip_bit = 1 if res["flipped_switch"] else 0
                        sc = 1.0 + (3.0 if flip_bit else 0.0)
                        if terrain[ny][nx] == "CRACK":
                            sc += 4.0
                        if res["hp_delta"] > 0 and hero_hp < 100:
                            sc = max(0.1, sc - 0.5 * min(100 - hero_hp, res["hp_delta"]))
                        m_list.append((f"MOVE_{dchar}", nx, ny, res["exposed"], res["cracks_broken"], sc, flip_bit))

                dx, dy = DIRECTIONS[dchar]
                p1x, p1y = x + dx, y + dy
                if _in_bounds(p1x, p1y):
                    p1t = terrain[p1y][p1x]
                    if p1t in ("PIT", "CRACK", "CHEST") or p1t in SPRING_TILES or (p1x, p1y) in laser_danger or memory["occupant"][p1y][p1x] in ("BOX", "TNT"):
                        jres = _sim_jump_from(x, y, dchar, memory, gates_flipped, allow_unknown=False)
                        if jres and not jres["entered_unknown"] and not jres["touched_unknown_portal"] and not jres["touched_unknown_chest"]:
                            if not jres["died"] and jres["hp_delta"] >= 0:
                                nx, ny = jres["land"]
                                flip_bit = 1 if jres["flipped_switch"] else 0
                                jsc = 28.0 + (3.0 if flip_bit else 0.0)
                                j_list.append((f"JUMP_{dchar}", nx, ny, jres["exposed"], jres["cracks_broken"], jsc, flip_bit))
            if m_list:
                move_edges[(x, y)] = m_list
            if j_list:
                jump_edges[(x, y)] = j_list
    return move_edges, jump_edges


def _dijkstra(start_x, start_y, start_t3, init_gf, hero_hp, jumps_avail, graphs, laser_danger, laser_uncertain, bomb_hazards):
    start_state = (start_x, start_y, start_t3, 0, init_gf)
    dist = {start_state: 0.0}
    first_act = {}
    parent = {start_state: None}
    broken_map = {start_state: frozenset()}
    pq = [(0.0, start_state)]

    while pq:
        cost, st = heapq.heappop(pq)
        if cost > dist.get(st, 1e18):
            continue
        x, y, t3, ju, gf = st
        nt3 = (t3 + 1) % 3
        is_first = (st == start_state)
        is_second = (parent[st] == start_state)
        broken_here = broken_map[st]
        move_edges, jump_edges = graphs[gf]

        # WAIT
        wait_ok = True
        if is_first and 1 in bomb_hazards and (x, y) in bomb_hazards[1]:
            wait_ok = False
        if is_second and 2 in bomb_hazards and (x, y) in bomb_hazards[2]:
            wait_ok = False
        if wait_ok:
            wcost = 1.05
            if (t3 == 0 or nt3 == 0) and (x, y) in laser_danger:
                if hero_hp <= 50:
                    wait_ok = False
                else:
                    wcost += 400.0
            elif (t3 == 0 or nt3 == 0) and (x, y) in laser_uncertain:
                wcost += 12.0
            if wait_ok:
                nst = (x, y, nt3, ju, gf)
                ncost = cost + wcost
                if ncost < dist.get(nst, 1e18):
                    dist[nst] = ncost
                    parent[nst] = st
                    first_act[nst] = "WAIT" if is_first else first_act[st]
                    broken_map[nst] = broken_here
                    heapq.heappush(pq, (ncost, nst))

        # MOVE edges
        for act, nx, ny, exposed, cbroken, sc, flip_bit in move_edges.get((x, y), ()):
            if cbroken and (cbroken & broken_here):
                continue
            if (nx, ny) in broken_here:
                continue
            if is_first and 1 in bomb_hazards and (nx, ny) in bomb_hazards[1]:
                continue
            if is_second and 2 in bomb_hazards and (nx, ny) in bomb_hazards[2]:
                continue
            lcost = sc
            if (t3 == 0 and (exposed & laser_danger)) or (nt3 == 0 and (nx, ny) in laser_danger):
                if hero_hp <= 50:
                    continue
                lcost += 400.0
            elif (t3 == 0 and (exposed & laser_uncertain)) or (nt3 == 0 and (nx, ny) in laser_uncertain):
                lcost += 12.0
            nst = (nx, ny, nt3, ju, gf ^ flip_bit)
            ncost = cost + lcost
            if ncost < dist.get(nst, 1e18):
                dist[nst] = ncost
                parent[nst] = st
                first_act[nst] = act if is_first else first_act[st]
                broken_map[nst] = (broken_here | cbroken) if cbroken else broken_here
                heapq.heappush(pq, (ncost, nst))

        # JUMP edges
        if ju < jumps_avail:
            for act, nx, ny, exposed, cbroken, sc, flip_bit in jump_edges.get((x, y), ()):
                if cbroken and (cbroken & broken_here):
                    continue
                if (nx, ny) in broken_here:
                    continue
                if is_first and 1 in bomb_hazards and (nx, ny) in bomb_hazards[1]:
                    continue
                if is_second and 2 in bomb_hazards and (nx, ny) in bomb_hazards[2]:
                    continue
                lcost = sc
                if (t3 == 0 and (exposed & laser_danger)) or (nt3 == 0 and (nx, ny) in laser_danger):
                    if hero_hp <= 50:
                        continue
                    lcost += 400.0
                elif (t3 == 0 and (exposed & laser_uncertain)) or (nt3 == 0 and (nx, ny) in laser_uncertain):
                    lcost += 12.0
                nst = (nx, ny, nt3, ju + 1, gf ^ flip_bit)
                ncost = cost + lcost
                if ncost < dist.get(nst, 1e18):
                    dist[nst] = ncost
                    parent[nst] = st
                    first_act[nst] = act if is_first else first_act[st]
                    broken_map[nst] = (broken_here | cbroken) if cbroken else broken_here
                    heapq.heappush(pq, (ncost, nst))

    return dist, first_act


def decide_action(state: dict, memory: dict) -> str:
    hx = state["hero"]["x"]
    hy = state["hero"]["y"]
    hp = state["hero"]["hp"]
    has_k1, has_k2 = state["hero"]["keys"]
    jumps = state["hero"]["jumps"]
    throws = state["hero"]["throws"]
    bombs_left = state["hero"]["bombs"]
    gates_flipped = state["gates_flipped"]
    turn = state["turn"]
    t3 = turn % 3
    targets = state["targets"]

    if "init" not in memory:
        memory["init"] = True
        memory["terrain"] = [["UNKNOWN"] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        memory["occupant"] = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        memory["clues"] = [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        memory["seen"] = [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        memory["portals"] = {}
        memory["warning_rays"] = []
        memory["clear_laser_dir"] = set()
        memory["prev_gf"] = gates_flipped
        memory["switched_coords"] = set()
        memory["visit_counts"] = {}
        memory["phase_min_goal_dist"] = {}

    vis = state["visible_mask"]
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    clues = memory["clues"]
    seen = memory["seen"]
    portals = memory["portals"]

    if gates_flipped != memory.get("prev_gf"):
        memory["clear_laser_dir"].clear()
        memory["prev_gf"] = gates_flipped

    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if vis[y][x]:
                old_t = terrain[y][x]
                old_o = occupant[y][x]
                seen[y][x] = True
                t = state["terrain"][y][x]
                o = state["occupant"][y][x]
                if old_t != "UNKNOWN" and (old_t != t or old_o != o):
                    memory["clear_laser_dir"].clear()
                terrain[y][x] = t
                occupant[y][x] = o
                clues[y][x] = state["clues"][y][x]
                if t in PORTAL_TILES:
                    portals[t] = (x, y)

    if has_k1:
        k1x, k1y = targets["K1"]
        if terrain[k1y][k1x] == "K1":
            terrain[k1y][k1x] = "EMPTY"
    if has_k2:
        k2x, k2y = targets["K2"]
        if terrain[k2y][k2x] == "K2":
            terrain[k2y][k2x] = "EMPTY"

    cur_warn_set = set()
    for w in state.get("laser_warnings", []):
        item = (w["x"], w["y"], w["dir"])
        cur_warn_set.add(item)
        if item not in memory["warning_rays"]:
            memory["warning_rays"].append(item)
    if t3 == 0:
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if vis[y][x]:
                    for dchar in ("U", "D", "L", "R"):
                        if (x, y, dchar) not in cur_warn_set:
                            memory["clear_laser_dir"].add((x, y, dchar))

    v_key = (hx, hy, has_k1, has_k2, gates_flipped)
    memory["visit_counts"][v_key] = memory["visit_counts"].get(v_key, 0) + 1

    laser_danger, laser_uncertain = _compute_laser_hazards(memory, gates_flipped)
    bomb_hazards = _compute_bomb_hazards(state, memory)

    if has_k1 and has_k2:
        goal_coords = [tuple(targets["V"])]
    elif has_k1:
        goal_coords = [tuple(targets["K2"])]
    elif has_k2:
        goal_coords = [tuple(targets["K1"])]
    else:
        goal_coords = [tuple(targets["K1"]), tuple(targets["K2"])]

    def dist_to_goals(x, y):
        return min(abs(x - gx) + abs(y - gy) for gx, gy in goal_coords)

    phase_key = (has_k1, has_k2, gates_flipped)
    cur_gdist = dist_to_goals(hx, hy)
    if phase_key not in memory["phase_min_goal_dist"] or cur_gdist < memory["phase_min_goal_dist"][phase_key]:
        memory["phase_min_goal_dist"][phase_key] = cur_gdist
    min_gdist = memory["phase_min_goal_dist"][phase_key]

    init_gf = 1 if gates_flipped else 0
    has_switch_seen = any(terrain[y][x] == "SWITCH" for y in range(GRID_HEIGHT) for x in range(GRID_WIDTH))
    graphs = {init_gf: _build_transition_graph(memory, bool(init_gf), hp, laser_danger)}
    if has_switch_seen:
        graphs[init_gf ^ 1] = _build_transition_graph(memory, bool(init_gf ^ 1), hp, laser_danger)

    dist, first_act = _dijkstra(
        hx, hy, t3, init_gf, hp, jumps, graphs,
        laser_danger, laser_uncertain, bomb_hazards
    )

    def best_state_for_coords(coords, max_cost=1e15):
        best_c = max_cost
        best_st = None
        for st, c in dist.items():
            if (st[0], st[1]) in coords and c < best_c:
                best_c = c
                best_st = st
        return best_st, best_c

    # 1. HEAL detour if injured
    if hp <= 75:
        heal_coords = set()
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if terrain[y][x] == "CHEST" and _chest_kind(x, y, terrain, seen, clues) == "HEAL":
                    heal_coords.add((x, y))
        if heal_coords:
            hst, _ = best_state_for_coords(heal_coords, max_cost=22.0 if hp > 50 else 45.0)
            if hst is not None and hst in first_act:
                return first_act[hst]

    reach_cutoff = 700.0 if (t3 == 0 and (hx, hy) in laser_danger and hp > 50) else 300.0

    # 2. Direct goal path (works across open OR switch-toggled gates & portals!)
    gst, gc = best_state_for_coords(set(goal_coords), max_cost=reach_cutoff)
    if gst is not None and gst in first_act:
        return first_act[gst]

    # Collect safe reachable cells: same-gf vs any-gf (possibly via SWITCH)
    reachable_cells = {}
    reachable_any = {}
    for st, c in dist.items():
        if c < reach_cutoff:
            xy = (st[0], st[1])
            if xy not in reachable_any or c < reachable_any[xy][0]:
                reachable_any[xy] = (c, st)
            if st[4] == init_gf:
                if xy not in reachable_cells or c < reachable_cells[xy][0]:
                    reachable_cells[xy] = (c, st)

    closed_gate_seen = False
    for (rx, ry) in reachable_cells:
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = rx + dx, ry + dy
            if _in_bounds(nx, ny):
                nt = terrain[ny][nx]
                if (nt == "R_GATE" and not gates_flipped) or (nt == "B_GATE" and gates_flipped):
                    closed_gate_seen = True

    def _collect_frontiers(cell_map, gf_val):
        flist = []
        gf_bool = bool(gf_val)
        for (fx, fy), (fc, fst) in cell_map.items():
            if (fx, fy) in laser_danger:
                has_safe_adj = any(
                    _in_bounds(fx + dx, fy + dy)
                    and (fx + dx, fy + dy) not in laser_danger
                    and not _is_high_wall_terrain(terrain[fy + dy][fx + dx], gf_bool)
                    and terrain[fy + dy][fx + dx] != "PIT"
                    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
                )
                if not has_safe_adj:
                    continue
            unk_adj = 0
            near_hazard = False
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = fx + dx, fy + dy
                if _in_bounds(nx, ny):
                    if terrain[ny][nx] == "UNKNOWN":
                        unk_adj += 1
                    elif (nx, ny) in laser_danger or terrain[ny][nx] in ("PIT", "CRACK"):
                        near_hazard = True
            unk_across = 0
            if unk_adj == 0 and near_hazard:
                for ddx, ddy in ((0, -2), (0, 2), (-2, 0), (2, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                    ux, uy = fx + ddx, fy + ddy
                    if _in_bounds(ux, uy) and terrain[uy][ux] == "UNKNOWN":
                        mx, my = fx + (0 if ddx == 0 else (1 if ddx > 0 else -1)), fy + (0 if ddy == 0 else (1 if ddy > 0 else -1))
                        if not _is_high_wall_terrain(terrain[my][mx], gf_bool):
                            unk_across += 1
            if unk_adj > 0 or unk_across > 0:
                vc = memory["visit_counts"].get((fx, fy, has_k1, has_k2, gates_flipped), 0)
                fd = dist_to_goals(fx, fy)
                score = fc + 1.1 * fd - 1.5 * unk_adj - 0.8 * unk_across + 4.0 * vc + (6.0 if (fx, fy) in laser_danger else 0.0)
                flist.append((score, fd, fc, fst))
        flist.sort(key=lambda z: z[0])
        return flist

    # 3. Exploration frontiers (same gf) & flipped-gf frontiers (behind closed gates via SWITCH)
    frontiers = _collect_frontiers(reachable_cells, init_gf)
    flipped_only_cells = {xy: val for xy, val in reachable_any.items() if xy not in reachable_cells}
    frontiers_flipped = _collect_frontiers(flipped_only_cells, init_gf ^ 1) if flipped_only_cells else []

    # 4. SWITCH candidates (walk or throw, deduped per switch coord & key phase)
    walkable_switches = set()
    switch_candidates = []
    for (rx, ry), (rc, rst) in reachable_cells.items():
        for dchar, (dx, dy) in DIRECTIONS.items():
            nx, ny = rx + dx, ry + dy
            if _in_bounds(nx, ny) and terrain[ny][nx] == "SWITCH":
                walkable_switches.add((nx, ny))
                sw_key = ((nx, ny), has_k1, has_k2)
                if sw_key not in memory["switched_coords"]:
                    act = f"MOVE_{dchar}" if (rx, ry) == (hx, hy) else first_act[rst]
                    switch_candidates.append((rc + 1.0, act, sw_key, (nx, ny)))
    if throws > 0:
        for (rx, ry), (rc, rst) in reachable_cells.items():
            for dchar in ("U", "D", "L", "R"):
                tres = _sim_throw_from(rx, ry, dchar, memory, gates_flipped)
                sw_pos = tres["hit_switch"]
                if sw_pos is not None and sw_pos not in walkable_switches:
                    sw_key = (sw_pos, has_k1, has_k2)
                    if sw_key not in memory["switched_coords"]:
                        act = f"THROW_{dchar}" if (rx, ry) == (hx, hy) else first_act[rst]
                        switch_candidates.append((rc + 4.0, act, sw_key, sw_pos))

    # 5. Unknown PORTAL candidates (allow walking across SWITCH if needed via reachable_any!)
    unknown_portal_cands = []
    for pname, (px, py) in portals.items():
        pair = PORTAL_PAIR_MAP[pname]
        if pair not in portals:
            for dchar, (dx, dy) in DIRECTIONS.items():
                ax, ay = px - dx, py - dy
                if (ax, ay) in reachable_any:
                    rc, rst = reachable_any[(ax, ay)]
                    act = f"MOVE_{dchar}" if (ax, ay) == (hx, hy) else first_act[rst]
                    unknown_portal_cands.append((rc, act))

    best_frontier_drifting = bool(frontiers) and frontiers[0][1] > min_gdist + 8
    flipped_closer_to_goal = bool(frontiers_flipped) and (not frontiers or frontiers_flipped[0][0] + 10.0 < frontiers[0][0])
    # Check if a closed gate lies directly toward goal with reasonable switch-flip cost (position-invariant, no rc cutoff)
    best_blocked_gate_dist = None
    if closed_gate_seen and frontiers:
        cur_best_fd = frontiers[0][1]
        for (rx, ry) in reachable_cells:
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = rx + dx, ry + dy
                if _in_bounds(nx, ny):
                    nt = terrain[ny][nx]
                    if (nt == "R_GATE" and not gates_flipped) or (nt == "B_GATE" and gates_flipped):
                        gd = dist_to_goals(nx, ny)
                        if gd < cur_best_fd:
                            if best_blocked_gate_dist is None or gd < best_blocked_gate_dist:
                                best_blocked_gate_dist = gd

    # Helper: find best THROW-open candidate (TNT or MIMIC opening unreachable space)
    def _find_throw_open():
        if throws <= 0:
            return None
        best = None
        for (rx, ry), (rc, rst) in sorted(reachable_cells.items(), key=lambda z: z[1][0]):
            for dchar in ("U", "D", "L", "R"):
                tres = _sim_throw_from(rx, ry, dchar, memory, gates_flipped)
                target_cell = tres["hit_tnt"] or tres["hit_mimic"]
                if target_cell:
                    tx, ty = target_cell
                    if tres["hit_tnt"] and abs(rx - tx) <= 1 and abs(ry - ty) <= 1:
                        continue
                    best_near = 1e9
                    opens = False
                    rad = (-1, 0, 1) if tres["hit_tnt"] else (0,)
                    for dy in rad:
                        for dx in rad:
                            cx, cy = tx + dx, ty + dy
                            if not _in_bounds(cx, cy):
                                continue
                            for ndx, ndy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                                nx, ny = cx + ndx, cy + ndy
                                if _in_bounds(nx, ny) and (nx, ny) not in reachable_cells:
                                    nt = terrain[ny][nx]
                                    if nt == "UNKNOWN" or (not _is_high_wall_terrain(nt, gates_flipped) and nt != "PIT"):
                                        opens = True
                                        best_near = min(best_near, dist_to_goals(nx, ny))
                    if opens:
                        act = f"THROW_{dchar}" if (rx, ry) == (hx, hy) else first_act[rst]
                        cand = (rc + best_near, best_near, act)
                        if best is None or cand[0] < best[0]:
                            best = cand
        return best

    # Helper: find best BOX push toward PIT/SWITCH using short BFS of box positions
    def _find_box_push():
        best = None
        for by in range(1, GRID_HEIGHT - 1):
            for bx in range(1, GRID_WIDTH - 1):
                if occupant[by][bx] != "BOX" or terrain[by][bx] == "CRACK":
                    continue
                # BFS of box coordinates from (bx, by) up to depth 5
                bq = deque([(bx, by, None, 0)])  # x, y, first_push_req=(hero_pos, dchar, dx, dy), pushes
                bvis = {(bx, by)}
                while bq:
                    cx, cy, f_req, pcnt = bq.popleft()
                    if pcnt >= 5:
                        continue
                    for dchar, (dx, dy) in DIRECTIONS.items():
                        hx_req, hy_req = cx - dx, cy - dy
                        nx, ny = cx + dx, cy + dy
                        if not (_in_bounds(hx_req, hy_req) and _in_bounds(nx, ny)):
                            continue
                        ht_req = terrain[hy_req][hx_req]
                        if _is_high_wall_terrain(ht_req, gates_flipped) or ht_req in ("UNKNOWN", "PIT", "CRACK"):
                            continue
                        nt = terrain[ny][nx]
                        if nt == "UNKNOWN" or _is_high_wall_terrain(nt, gates_flipped) or nt in ("K1", "K2", "V", "CRACK"):
                            continue
                        if occupant[ny][nx] is not None and (nx, ny) != (bx, by):
                            continue
                        if pcnt == 0 and (hx_req, hy_req) not in reachable_cells:
                            continue
                        req = f_req if f_req is not None else (hx_req, hy_req, dchar)
                        if nt in ("PIT", "SWITCH"):
                            # Target PIT/SWITCH reached! Score by hero travel + pushes + target goal dist
                            rc, rst = reachable_cells[(req[0], req[1])]
                            gd = dist_to_goals(nx, ny)
                            # Prefer PIT if it bridges toward unreachable cells
                            bridges_unreach = any(
                                _in_bounds(nx + ox, ny + oy)
                                and (nx + ox, ny + oy) not in reachable_cells
                                and not _is_high_wall_terrain(terrain[ny + oy][nx + ox], gates_flipped)
                                and terrain[ny + oy][nx + ox] != "PIT"
                                for ox, oy in ((0, -1), (0, 1), (-1, 0), (1, 0))
                            )
                            act = f"MOVE_{req[2]}" if (req[0], req[1]) == (hx, hy) else first_act[rst]
                            sc = rc + (pcnt + 1) * 2.0 + gd - (6.0 if bridges_unreach else 0.0)
                            cand = (sc, gd, act)
                            if best is None or cand[0] < best[0]:
                                best = cand
                        elif nt == "EMPTY" and (nx, ny) not in bvis:
                            bvis.add((nx, ny))
                            bq.append((nx, ny, req, pcnt + 1))
        return best

    # Helper: find best BOMB placement with verified 2-step safe escape
    def _find_bomb_breach():
        if bombs_left <= 0 or state["bombs"]:
            return None
        cur_edges = graphs[init_gf][0]
        best = None
        for (rx, ry), (rc, rst) in reachable_cells.items():
            blast = set()
            bq = deque([(rx, ry)])
            bseen = {(rx, ry)}
            while bq:
                ex, ey = bq.popleft()
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        cx, cy = ex + dx, ey + dy
                        if _in_bounds(cx, cy):
                            blast.add((cx, cy))
                            if occupant[cy][cx] == "TNT" and (cx, cy) not in bseen:
                                bseen.add((cx, cy))
                                bq.append((cx, cy))
            destroyed_any = False
            opens_new = False
            best_near = 1e9
            for (cx, cy) in blast:
                ct = terrain[cy][cx]
                is_destr = (
                    ct in ("W", "R_GATE", "B_GATE")
                    or ct in LASER_TILES
                    or (ct == "CHEST" and _chest_kind(cx, cy, terrain, seen, clues) == "MIMIC")
                    or occupant[cy][cx] == "TNT"
                )
                if not is_destr:
                    continue
                destroyed_any = True
                for ndx, ndy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = cx + ndx, cy + ndy
                    if not _in_bounds(nx, ny) or (nx, ny) in blast or (nx, ny) in reachable_cells:
                        continue
                    nt = terrain[ny][nx]
                    if nt == "UNKNOWN" or (not _is_high_wall_terrain(nt, gates_flipped) and nt != "PIT"):
                        opens_new = True
                        best_near = min(best_near, dist_to_goals(nx, ny))
            if not (destroyed_any and opens_new):
                continue
            # Check 1..2 step safe escape in cur_edges outside blast
            has_escape = False
            for _, n1x, n1y, exp1, _, _, f1 in cur_edges.get((rx, ry), ()):
                if f1:
                    continue
                if (n1x, n1y) not in blast and (n1x, n1y) not in laser_danger:
                    has_escape = True
                    break
                for _, n2x, n2y, exp2, _, _, f2 in cur_edges.get((n1x, n1y), ()):
                    if not f2 and (n2x, n2y) not in blast:
                        has_escape = True
                        break
                if has_escape:
                    break
            if has_escape:
                act = "BOMB" if (rx, ry) == (hx, hy) else first_act[rst]
                cand = (rc + best_near, best_near, act)
                if best is None or cand[0] < best[0]:
                    best = cand
        return best

    # Active bomb immediate blast escape if standing inside ticking blast zone
    if state["bombs"]:
        in_blast = ((hx, hy) in bomb_hazards.get(1, ())) or ((hx, hy) in bomb_hazards.get(2, ()))
        if in_blast:
            all_blast = bomb_hazards.get(1, set()) | bomb_hazards.get(2, set())
            esc_cands = []
            for (ex, ey), (ec, est) in reachable_cells.items():
                if (ex, ey) not in all_blast and est in first_act:
                    esc_cands.append((ec, first_act[est]))
            if esc_cands:
                esc_cands.sort(key=lambda z: z[0])
                return esc_cands[0][1]

    if unknown_portal_cands:
        unknown_portal_cands.sort(key=lambda z: z[0])
        if (
            not frontiers
            or (unknown_portal_cands[0][0] <= 4.0 and frontiers[0][2] > 5.0)
            or (best_frontier_drifting and unknown_portal_cands[0][0] < 35.0)
        ):
            return unknown_portal_cands[0][1]

    if frontiers_flipped and (not frontiers or flipped_closer_to_goal or (best_frontier_drifting and frontiers_flipped[0][1] <= frontiers[0][1])):
        bfst = frontiers_flipped[0][3]
        if bfst in first_act:
            return first_act[bfst]

    if switch_candidates:
        switch_candidates.sort(key=lambda z: z[0])
        if (
            not frontiers
            or (best_blocked_gate_dist is not None and switch_candidates[0][0] + best_blocked_gate_dist < frontiers[0][0] + 6.0)
            or (best_frontier_drifting and switch_candidates[0][0] < 25.0)
        ):
            _, act, sw_key, sw_pos = switch_candidates[0]
            if (abs(hx - sw_pos[0]) + abs(hy - sw_pos[1]) == 1 and act.startswith("MOVE_")) or act.startswith("THROW_"):
                memory["switched_coords"].add(sw_key)
            return act

    # Goal-directed breakthrough (BOX->PIT, BOMB->W, THROW->TNT/MIMIC) using monotonic full-score comparison
    box_cand = _find_box_push()
    bomb_cand = _find_bomb_breach()
    throw_cand = _find_throw_open()
    if frontiers:
        best_fscore = frontiers[0][0]
        if box_cand and (box_cand[0] + 2.0 < best_fscore or best_frontier_drifting):
            return box_cand[2]
        if bomb_cand and (bomb_cand[0] + 6.0 < best_fscore or (best_frontier_drifting and bomb_cand[1] <= min_gdist + 4)):
            return bomb_cand[2]
        if throw_cand and (throw_cand[0] + 4.0 < best_fscore or (best_frontier_drifting and throw_cand[1] <= min_gdist + 4)):
            return throw_cand[2]

    if frontiers:
        best_fst = frontiers[0][3]
        if best_fst in first_act:
            return first_act[best_fst]

    if frontiers_flipped:
        bfst = frontiers_flipped[0][3]
        if bfst in first_act:
            return first_act[bfst]

    if switch_candidates:
        switch_candidates.sort(key=lambda z: z[0])
        _, act, sw_key, sw_pos = switch_candidates[0]
        if (abs(hx - sw_pos[0]) + abs(hy - sw_pos[1]) == 1 and act.startswith("MOVE_")) or act.startswith("THROW_"):
            memory["switched_coords"].add(sw_key)
        return act

    if unknown_portal_cands:
        unknown_portal_cands.sort(key=lambda z: z[0])
        return unknown_portal_cands[0][1]

    if box_cand:
        return box_cand[2]
    if bomb_cand:
        return bomb_cand[2]
    if throw_cand:
        return throw_cand[2]

    # 9. Fallback: goal with laser hit or safe move
    if gst is not None and gst in first_act:
        return first_act[gst]

    if 1 in bomb_hazards and (hx, hy) in bomb_hazards[1]:
        for dchar in ("U", "D", "L", "R"):
            res = _sim_move_from(hx, hy, dchar, memory, gates_flipped, allow_unknown=True)
            if res and not res["died"] and res["land"] not in bomb_hazards[1]:
                return f"MOVE_{dchar}"

    for dchar in ("R", "D", "U", "L"):
        res = _sim_move_from(hx, hy, dchar, memory, gates_flipped, allow_unknown=True)
        if res and not res["died"]:
            if not (t3 == 0 and (res["exposed"] & laser_danger)) and not (t3 == 2 and res["land"] in laser_danger):
                return f"MOVE_{dchar}"

    return "WAIT"


def build_dungeon() -> dict:
    """Build the 40x26 Demon fortress with a verified 78-turn 100-HP author_solution."""
    grid = [
        [
            "T_W" if (x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1) else "EMPTY"
            for x in range(GRID_WIDTH)
        ]
        for y in range(GRID_HEIGHT)
    ]

    # 1. Bomb-proof spawn containment forcing exit through (4, 13) -> (5, 13) Turn-3 sniper tunnel
    for x in range(1, 5):
        grid[11][x] = "T_W"
        grid[15][x] = "W"
    grid[15][4] = "T_W"
    grid[12][4] = "T_W"
    grid[14][4] = "T_W"

    # Turn-3 sniper tunnel along y=13: LASER_L(15, 13) fires x=14..5
    for x in range(6, 16):
        grid[12][x] = "W"
        grid[14][x] = "W"
    grid[13][6] = "CRACK"
    grid[13][7] = "SPRING_R"
    grid[13][10] = "PIT"
    grid[13][15] = "LASER_L"
    grid[13][16] = "W"

    # 2. South wing entry with Turn-6 double-tap LASER_L(13, 16) + cross LASER_D(14, 16)
    for x in range(6, 21):
        grid[15][x] = "W"
    for y in range(16, 23):
        grid[y][5] = "W"
    grid[16][5] = "EMPTY"
    grid[16][13] = "LASER_L"
    grid[16][14] = "LASER_D"

    # 3. South laser hall along y=23
    for x in range(6, 20):
        grid[21][x] = "W"
        grid[22][x] = "W"
    for x in (8, 10, 15, 16, 17, 18, 19, 20):
        grid[22][x] = "EMPTY"
    grid[23][20] = "LASER_L"
    grid[21][20] = "W"

    # 4. K2 Titanium vault (B_GATE open initially; SWITCH opens R_GATE for K1; PORTAL_1A exits North)
    for y in range(22, 25):
        grid[y][21] = "T_W"
        grid[y][28] = "T_W"
    for x in range(22, 28):
        grid[21][x] = "T_W"
    grid[22][21] = "B_GATE"
    grid[23][24] = "K2"
    grid[23][27] = "SWITCH"
    grid[22][27] = "PORTAL_1A"
    grid[22][26] = "T_W"
    grid[22][24] = "W"

    # 5. Double-thick W horizontal divider at y=9 and y=10 (resists single-bomb breach)
    for x in range(5, 39):
        grid[9][x] = "W"
        grid[10][x] = "W"

    # 6. Upper wing (x=5..21, y=1..8) & PORTAL_1B(9, 8)
    grid[8][9] = "PORTAL_1B"
    grid[6][15] = "LASER_L"
    grid[7][16] = "SPRING_R"
    grid[7][19] = "PIT"
    grid[1][20] = "LASER_D"

    # 7. K1 Titanium vault gated by R_GATE
    for y in range(1, 4):
        grid[y][22] = "T_W"
        grid[y][28] = "T_W"
    for x in range(23, 28):
        grid[4][x] = "T_W"
    grid[2][22] = "R_GATE"
    grid[2][28] = "R_GATE"
    grid[2][25] = "K1"

    # 8. East laser gauntlet leading to PORTAL_2A(36, 7)
    grid[1][34] = "LASER_D"
    grid[6][38] = "LASER_L"
    for x in (31, 32, 33, 35, 36, 37):
        grid[5][x] = "W"
    grid[8][32] = "W"
    grid[8][35] = "W"
    grid[7][33] = "CRACK"
    grid[7][36] = "PORTAL_2A"

    # 9. Sealed V Titanium vault (reachable only via PORTAL_2A -> PORTAL_2B)
    for y in range(12, 15):
        grid[y][35] = "T_W"
    for x in range(36, 39):
        grid[11][x] = "T_W"
        grid[15][x] = "T_W"
    grid[13][36] = "PORTAL_2B"
    grid[13][37] = "V"

    author_solution = [
        "MOVE_R", "MOVE_R", "WAIT", "MOVE_R", "MOVE_U", "MOVE_U", "MOVE_R", "MOVE_R",
        "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
        "MOVE_R", "MOVE_D", "MOVE_R", "MOVE_D", "MOVE_D", "MOVE_R", "MOVE_R", "MOVE_R",
        "MOVE_R", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_D",
        "MOVE_D", "MOVE_R", "MOVE_D", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
        "MOVE_U", "MOVE_R", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_R", "MOVE_R", "MOVE_R",
        "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
        "MOVE_U", "MOVE_U", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
        "MOVE_R", "MOVE_R", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_R",
        "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
    ]

    return {
        "taunt": "Hydrogen trap: count mod 3 or perish!",
        "grid": grid,
        "author_solution": author_solution,
    }
