"""
《阴间地牢：金库攻防战》正式参赛答卷 (submission.py)
Model: CARBON
"""

import collections
import heapq
import math
import time

# ==============================================================================
# 官方规则常量定义
# ==============================================================================

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

OPP_DIR = {"U": "D", "D": "U", "L": "R", "R": "L"}

MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}

SPRING_DIR = {
    "SPRING_U": "U",
    "SPRING_D": "D",
    "SPRING_L": "L",
    "SPRING_R": "R",
}

LASER_DIR = {
    "LASER_U": "U",
    "LASER_D": "D",
    "LASER_L": "L",
    "LASER_R": "R",
}

PORTAL_PAIR_TILE = {
    "PORTAL_1A": "PORTAL_1B",
    "PORTAL_1B": "PORTAL_1A",
    "PORTAL_2A": "PORTAL_2B",
    "PORTAL_2B": "PORTAL_2A",
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

EXPLOSION_IMMUNE = {
    "T_W", "K1", "K2", "V",
    "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
    "PIT", "EMPTY",
}

DESTRUCTIBLE_TILES = {
    "W", "R_GATE", "B_GATE", "LASER_U", "LASER_D", "LASER_L", "LASER_R",
}

AUTHOR_SOLUTION = [
    "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_L", "MOVE_D", "MOVE_D", "MOVE_D",
    "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_R", "MOVE_R", "WAIT", "MOVE_R", "MOVE_D", "MOVE_R", "MOVE_U", "MOVE_R",
    "MOVE_R", "MOVE_L", "MOVE_R", "MOVE_R", "MOVE_U", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_R", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_D", "MOVE_L", "MOVE_L",
    "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_U", "MOVE_L", "MOVE_L", "MOVE_U", "MOVE_U",
    "MOVE_U", "MOVE_U", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_R", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U",
    "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_L", "MOVE_L", "MOVE_U", "MOVE_U", "MOVE_U",
    "MOVE_U", "MOVE_U", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_U",
    "MOVE_U", "MOVE_R", "MOVE_R", "MOVE_U", "MOVE_R", "MOVE_D", "MOVE_R", "MOVE_R",
    "MOVE_L", "MOVE_R", "MOVE_R", "MOVE_D", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_U", "MOVE_L", "MOVE_L", "MOVE_D",
    "MOVE_U", "MOVE_L", "MOVE_D", "MOVE_L", "MOVE_L", "MOVE_D", "MOVE_D", "MOVE_D",
    "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_R",
    "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_U", "MOVE_U", "MOVE_R",
    "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_R", "MOVE_D", "MOVE_D", "MOVE_L",
]


def _in_bounds(x: int, y: int) -> bool:
    return 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT


def _is_outer(x: int, y: int) -> bool:
    return x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1


def _is_spawn_zone(x: int, y: int) -> bool:
    return 1 <= x <= 3 and 12 <= y <= 14


def _manhattan(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ==============================================================================
# 参赛入口 1：魔王造图与自证函数
# ==============================================================================

def build_dungeon() -> dict:
    """
    构建 40x26 的地下城，并提供恰好在最后一步存活踏入 V 通关的 author_solution。
    单次调用限时：2.0 秒。
    """
    g = [
        [
            "T_W" if _is_outer(x, y) else "EMPTY"
            for x in range(GRID_WIDTH)
        ]
        for y in range(GRID_HEIGHT)
    ]

    def hline(y, x1, x2, tile="W"):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            g[y][x] = tile

    def vline(x, y1, y2, tile="W"):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            g[y][x] = tile

    def rect(x1, y1, x2, y2, tile="W"):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for x in range(min(x1, x2), max(x1, x2) + 1):
                g[y][x] = tile

    # 1. 出生诱捕盒 (x=1..5, y=9..17)，真实出口藏于左下 (1, 18) 并接中场 S 形折流墙
    hline(8, 1, 7, "W")
    vline(6, 9, 17, "W")
    vline(7, 9, 17, "W")
    hline(18, 2, 20, "W")

    # 正东盲传瞬杀陷阱: PORTAL_1A(5,13) -> PORTAL_1B(8,13) -> R -> PIT(9,13)
    g[12][5] = "W"
    g[13][5] = "PORTAL_1A"
    g[14][5] = "W"
    g[12][8] = "W"
    g[12][9] = "W"
    g[13][8] = "PORTAL_1B"
    g[13][9] = "PIT"
    g[13][10] = "W"
    g[14][8] = "W"
    g[14][9] = "W"

    # 东北 & 东南对称盲区弹簧陷阱 (第 3 格砖墙位于 dx=4 迷雾外，触发提前落坑)
    g[9][8] = "W"
    g[10][6] = "SPRING_R"
    g[10][7] = "EMPTY"
    g[10][8] = "PIT"
    g[10][9] = "W"
    g[11][8] = "W"

    g[15][8] = "W"
    g[16][6] = "SPRING_R"
    g[16][7] = "EMPTY"
    g[16][8] = "PIT"
    g[16][9] = "W"
    g[17][8] = "W"

    # 出生区反相诱饵开关
    g[9][4] = "SWITCH"

    # 2. 南翼超视距十字交叉激光要塞 -> K2(32, 23) (3 层砖墙全面免疫双炸弹偷渡)
    hline(22, 16, 32, "W")
    rect(29, 20, 34, 22, "W")
    rect(33, 23, 35, 24, "W")

    g[23][27] = "LASER_L"
    g[13][21] = "LASER_D"
    g[22][21] = "PIT"

    for x in range(16, 33):
        if x not in (20, 21, 26, 27, 28):
            g[24][x] = "W"

    g[23][17] = "ICE"
    g[23][18] = "ICE"
    g[23][19] = "ICE"
    for x in range(22, 26):
        g[23][x] = "ICE"
    g[23][26] = "MIRROR_SW"

    g[23][29] = "B_GATE"
    g[23][31] = "B_GATE"
    g[23][32] = "K2"

    # 3. 北翼超视距十字交叉激光要塞 -> K1(32, 2)
    hline(3, 16, 32, "W")
    rect(29, 3, 34, 5, "W")
    rect(33, 1, 35, 2, "W")

    g[2][27] = "LASER_L"
    g[12][21] = "LASER_U"
    g[3][21] = "PIT"

    for x in range(16, 33):
        if x not in (20, 21, 26, 27, 28):
            g[1][x] = "W"

    g[2][17] = "ICE"
    g[2][18] = "ICE"
    g[2][19] = "ICE"
    for x in range(22, 26):
        g[2][x] = "ICE"
    g[2][26] = "MIRROR_NW"

    g[2][30] = "B_GATE"
    g[2][32] = "K1"

    # 中场东翼折流挡墙，迫使路线横穿 x=21 纵贯激光束并诱导迷雾探索深入死胡同
    hline(7, 22, 38, "W")

    # 4. 中路盲区冰道宝箱怪 + 真开关 + 精炼钛金三红门金库 -> V(37, 13)
    hline(12, 14, 17, "W")
    g[11][18] = "W"
    g[12][19] = "W"
    for x in range(14, 18):
        g[13][x] = "ICE"
    g[13][18] = "MIMIC"
    g[13][19] = "W"
    hline(14, 14, 19, "W")

    g[13][28] = "SWITCH"

    rect(33, 9, 38, 10, "W")
    hline(12, 33, 36, "W")
    g[11][33] = "R_GATE"
    g[11][36] = "R_GATE"
    g[12][37] = "T_W"
    g[13][36] = "T_W"
    g[14][37] = "T_W"
    g[14][38] = "T_W"
    g[13][38] = "R_GATE"
    g[13][37] = "V"

    return {
        "taunt": "迷雾深处皆幻象，步步惊心金库藏！",
        "grid": g,
        "author_solution": list(AUTHOR_SOLUTION),
    }


# ==============================================================================
# 勇者端核心模块：信念地图维护、精确物理推演与四维时空规划
# ==============================================================================

def _is_high_wall_tile(t: str, gates_flipped: bool) -> bool:
    if t in ("W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R"):
        return True
    if t == "R_GATE" and not gates_flipped:
        return True
    if t == "B_GATE" and gates_flipped:
        return True
    return False


def _compute_frontier_gain_from_cell(terrain, ever_seen, gf: bool, hx: int, hy: int) -> int:
    gain = 0
    has_any_unseen = False
    for dy in range(-3, 4):
        ny = hy + dy
        if ny < 0 or ny >= GRID_HEIGHT:
            continue
        es_row = ever_seen[ny]
        for dx in range(-3, 4):
            if dx * dx + dy * dy <= 10:
                nx = hx + dx
                if 0 <= nx < GRID_WIDTH and not es_row[nx]:
                    has_any_unseen = True
                    if abs(dx) <= 1 and abs(dy) <= 1:
                        gain += 1
    if not has_any_unseen:
        for dx, dy in DIRECTIONS.values():
            nx, ny = hx + dx, hy + dy
            if _in_bounds(nx, ny) and terrain[ny][nx] in ("ICE", *MIRROR_MAP.keys()):
                return 1
        return 0
    if gain > 0:
        return gain

    def is_hw(x, y):
        if not _in_bounds(x, y):
            return True
        t = terrain[y][x]
        return False if t == "UNKNOWN" else _is_high_wall_tile(t, gf)

    def sgn(v):
        return 1 if v > 0 else (-1 if v < 0 else 0)

    vis_local = {(0, 0): True}
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if _in_bounds(hx + dx, hy + dy):
                vis_local[(dx, dy)] = True

    for ring in (2, 3):
        for rdy in range(-ring, ring + 1):
            for rdx in range(-ring, ring + 1):
                if max(abs(rdx), abs(rdy)) != ring or rdx * rdx + rdy * rdy > 10:
                    continue
                nx, ny = hx + rdx, hy + rdy
                if not _in_bounds(nx, ny):
                    continue
                sx, sy = sgn(rdx), sgn(rdy)
                if rdx == 0 or rdy == 0:
                    v = vis_local.get((rdx - sx, rdy - sy), False) and not is_hw(hx + rdx - sx, hy + rdy - sy)
                elif abs(rdx) == 2 and abs(rdy) == 2:
                    v = (
                        vis_local.get((sx, sy), False)
                        and not is_hw(hx + sx, hy + sy)
                        and not (is_hw(hx + sx, hy) and is_hw(hx, hy + sy))
                    )
                elif abs(rdx) > abs(rdy) > 0:
                    o1 = vis_local.get((rdx - sx, rdy), False) and not is_hw(hx + rdx - sx, hy + rdy)
                    o2 = vis_local.get((rdx - sx, rdy - sy), False) and not is_hw(hx + rdx - sx, hy + rdy - sy)
                    v = o1 or o2
                else:
                    o1 = vis_local.get((rdx, rdy - sy), False) and not is_hw(hx + rdx, hy + rdy - sy)
                    o2 = vis_local.get((rdx - sx, rdy - sy), False) and not is_hw(hx + rdx - sx, hy + rdy - sy)
                    v = o1 or o2
                if v:
                    vis_local[(rdx, rdy)] = True
                    if not ever_seen[ny][nx]:
                        gain += 1
    return gain


def _build_frontier_gains(memory: dict) -> dict:
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    ever_seen = memory["ever_seen"]
    stood = memory["stood"]
    fg_all = {False: {}, True: {}}
    for g_flag in (False, True):
        st_grid = stood[g_flag]
        fg = fg_all[g_flag]
        for y in range(1, GRID_HEIGHT - 1):
            es_row = ever_seen[y]
            st_row = st_grid[y]
            t_row = terrain[y]
            o_row = occupant[y]
            for x in range(1, GRID_WIDTH - 1):
                if not es_row[x] or st_row[x]:
                    continue
                t = t_row[x]
                if _is_high_wall_tile(t, g_flag) or t == "PIT" or o_row[x] in ("BOX", "TNT"):
                    continue
                g_val = _compute_frontier_gain_from_cell(terrain, ever_seen, g_flag, x, y)
                if g_val > 0:
                    fg[(x, y)] = g_val
    return fg_all


def _init_memory(state: dict, memory: dict) -> None:
    terrain = [
        ["T_W" if _is_outer(x, y) else ("EMPTY" if _is_spawn_zone(x, y) else "UNKNOWN")
         for x in range(GRID_WIDTH)]
        for y in range(GRID_HEIGHT)
    ]
    ever_seen = [
        [True if _is_outer(x, y) or _is_spawn_zone(x, y) else False for x in range(GRID_WIDTH)]
        for y in range(GRID_HEIGHT)
    ]
    targets = state["targets"]
    for name in ("K1", "K2", "V"):
        tx, ty = targets[name]
        terrain[ty][tx] = name

    memory["ready"] = True
    memory["terrain"] = terrain
    memory["occupant"] = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    memory["ever_seen"] = ever_seen
    memory["stood"] = {
        False: [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)],
        True: [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)],
    }
    memory["clues_now"] = [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    memory["portals"] = {}
    memory["lasers"] = {}
    memory["warn_beams"] = set()
    memory["laser_checked"] = {
        False: [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)],
        True: [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)],
    }
    memory["tracked_bombs"] = []
    memory["visit_counts"] = {}
    memory["probed_chests"] = set()
    memory["tried_portals"] = set()
    memory["tried_mirrors"] = set()
    memory["last_pos"] = None
    memory["last_action"] = None
    memory["last_bombs_inv"] = state["hero"]["bombs"]


def _apply_unseen_explosion_belief(memory: dict, ex: int, ey: int, vis) -> None:
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    for ny in range(max(0, ey - 1), min(GRID_HEIGHT, ey + 2)):
        for nx in range(max(0, ex - 1), min(GRID_WIDTH, ex + 2)):
            if vis[ny][nx]:
                continue
            if occupant[ny][nx] in ("BOX", "TNT"):
                occupant[ny][nx] = None
            t = terrain[ny][nx]
            if t == "UNKNOWN" or t in EXPLOSION_IMMUNE:
                pass
            elif t == "CRACK":
                terrain[ny][nx] = "PIT"
            else:
                terrain[ny][nx] = "EMPTY"
                if (nx, ny) in memory["lasers"]:
                    del memory["lasers"][(nx, ny)]
            memory["laser_checked"][False][ny][nx] = False
            memory["laser_checked"][True][ny][nx] = False


def _update_memory(state: dict, memory: dict) -> None:
    if "ready" not in memory:
        _init_memory(state, memory)

    hero = state["hero"]
    hx, hy = hero["x"], hero["y"]
    gf = state["gates_flipped"]
    vis = state["visible_mask"]
    obs_t = state["terrain"]
    obs_o = state["occupant"]
    obs_c = state["clues"]
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    ever_seen = memory["ever_seen"]

    last_pos = memory["last_pos"]
    if last_pos is not None and last_pos != (hx, hy):
        lx, ly = last_pos
        if terrain[ly][lx] == "CRACK":
            terrain[ly][lx] = "PIT"

    prev_bombs = list(memory["tracked_bombs"])
    if memory["last_action"] == "BOMB" and hero["bombs"] < memory["last_bombs_inv"] and last_pos is not None:
        prev_bombs.append({"x": last_pos[0], "y": last_pos[1], "timer": 3})

    new_tracked = []
    for b in prev_bombs:
        nt = b["timer"] - 1
        if nt <= 0:
            _apply_unseen_explosion_belief(memory, b["x"], b["y"], vis)
        elif not vis[b["y"]][b["x"]]:
            new_tracked.append({"x": b["x"], "y": b["y"], "timer": nt})
    for b in state["bombs"]:
        new_tracked.append({"x": b["x"], "y": b["y"], "timer": b["timer"]})
    memory["tracked_bombs"] = new_tracked

    k1x, k1y = state["targets"]["K1"]
    k2x, k2y = state["targets"]["K2"]
    if hero["keys"][0] and terrain[k1y][k1x] == "K1":
        terrain[k1y][k1x] = "EMPTY"
    if hero["keys"][1] and terrain[k2y][k2x] == "K2":
        terrain[k2y][k2x] = "EMPTY"

    for y in range(GRID_HEIGHT):
        vrow = vis[y]
        trow = obs_t[y]
        orow = obs_o[y]
        crow = obs_c[y]
        for x in range(GRID_WIDTH):
            if vrow[x]:
                ever_seen[y][x] = True
                t = trow[x]
                o = orow[x]
                terrain[y][x] = t
                occupant[y][x] = o
                memory["clues_now"][y][x] = crow[x]
                if t in PORTAL_PAIR_TILE:
                    memory["portals"][t] = (x, y)
                if t in LASER_DIR:
                    memory["lasers"][(x, y)] = LASER_DIR[t]
                elif (x, y) in memory["lasers"]:
                    del memory["lasers"][(x, y)]

    memory["stood"][gf][hy][hx] = True

    if state["turn"] % 3 == 0:
        lc = memory["laser_checked"][gf]
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if vis[y][x]:
                    lc[y][x] = True
        memory["warn_beams"] = {
            item for item in memory["warn_beams"] if not vis[item[1]][item[0]]
        }
        for w in state["laser_warnings"]:
            memory["warn_beams"].add((w["x"], w["y"], w["dir"]))

    st_key = (hx, hy, gf, hero["keys"][0], hero["keys"][1])
    memory["visit_counts"][st_key] = memory["visit_counts"].get(st_key, 0) + 1


def _classify_chests(memory: dict) -> dict:
    terrain = memory["terrain"]
    ever_seen = memory["ever_seen"]
    clues_now = memory["clues_now"]
    probed = memory["probed_chests"]
    res = {}

    for y in range(1, GRID_HEIGHT - 1):
        for x in range(1, GRID_WIDTH - 1):
            if terrain[y][x] != "CHEST":
                continue
            if (x, y) in probed:
                res[(x, y)] = "HEAL"
                continue
            is_mimic = False
            has_unseen_cand = False
            for dx, dy in DIRECTIONS.values():
                nx, ny = x + dx, y + dy
                if not _in_bounds(nx, ny):
                    continue
                if clues_now[ny][nx]:
                    is_mimic = True
                    break
                if not ever_seen[ny][nx] and not _is_outer(nx, ny) and not _is_spawn_zone(nx, ny):
                    has_unseen_cand = True
            if is_mimic:
                res[(x, y)] = "MIMIC"
            elif not has_unseen_cand:
                res[(x, y)] = "HEAL"
            else:
                res[(x, y)] = "UNVERIFIED"
    return res


def _compute_laser_hit_counts(memory: dict, gf: bool, occ_override=None) -> dict:
    terrain = memory["terrain"]
    occupant = occ_override if occ_override is not None else memory["occupant"]
    hit_counts = collections.Counter()
    covered_by_known = set()

    for (lx, ly), dname in memory["lasers"].items():
        if terrain[ly][lx] not in LASER_DIR:
            continue
        dx, dy = DIRECTIONS[dname]
        for dist in range(1, 11):
            nx, ny = lx + dist * dx, ly + dist * dy
            if not _in_bounds(nx, ny):
                break
            t = terrain[ny][nx]
            if t != "UNKNOWN" and _is_high_wall_tile(t, gf):
                break
            if occupant[ny][nx] in ("BOX", "TNT"):
                break
            hit_counts[(nx, ny)] += 1
            covered_by_known.add((nx, ny, dname))

    grouped_warns = collections.defaultdict(list)
    for wx, wy, dname in memory["warn_beams"]:
        if (wx, wy, dname) in covered_by_known:
            continue
        grouped_warns[(dname, wy if dname in ("L", "R") else wx)].append((wx, wy))

    for (dname, _), cells in grouped_warns.items():
        dx, dy = DIRECTIONS[dname]
        ax, ay = max(cells, key=lambda p: p[0] * dx + p[1] * dy)
        added_line = set()
        for back in range(0, 10):
            bx, by = ax - back * dx, ay - back * dy
            if not _in_bounds(bx, by):
                break
            t = terrain[by][bx]
            if t in LASER_DIR and LASER_DIR[t] == dname:
                break
            if t != "UNKNOWN" and (_is_high_wall_tile(t, gf) or occupant[by][bx] in ("BOX", "TNT")):
                break
            added_line.add((bx, by))
        for cell in added_line:
            hit_counts[cell] += 1

    return hit_counts


def _has_unchecked_sniper_line(memory: dict, x: int, y: int, gf: bool) -> bool:
    if memory["laser_checked"][gf][y][x]:
        return False
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    for dname, (dx, dy) in DIRECTIONS.items():
        opp_laser = "LASER_" + OPP_DIR[dname]
        for dist in range(1, 11):
            nx, ny = x + dist * dx, y + dist * dy
            if not _in_bounds(nx, ny):
                break
            t = terrain[ny][nx]
            if t == "UNKNOWN" and not memory["ever_seen"][ny][nx]:
                return True
            if t == opp_laser:
                return True
            if t != "UNKNOWN" and (_is_high_wall_tile(t, gf) or occupant[ny][nx] in ("BOX", "TNT")):
                break
    return False


# ==============================================================================
# 轻量级单步物理推演内核
# ==============================================================================

def _sim_single_turn(
    hx: int, hy: int, hp: int, k1: bool, k2: bool,
    jumps: int, throws: int, bombs_inv: int, gf: bool,
    turn: int, action: str,
    base_terrain, base_occ, chest_types: dict, portals: dict,
    tracked_bombs: list, memory: dict,
    treat_unknown_as_empty: bool = False,
) -> dict:
    t_mod = {}
    o_mod = {}

    def get_t(x, y):
        return t_mod.get((x, y), base_terrain[y][x])

    def set_t(x, y, val):
        t_mod[(x, y)] = val

    def get_o(x, y):
        return o_mod.get((x, y), base_occ[y][x])

    def set_o(x, y, val):
        o_mod[(x, y)] = val

    cur_hx, cur_hy = hx, hy
    cur_hp = hp
    cur_k1, cur_k2 = k1, k2
    cur_jumps, cur_throws, cur_bombs_inv = jumps, throws, bombs_inv
    cur_gf = gf
    status = "ALIVE"
    dmg_taken = 0
    entered_unknown = False
    cracks_collapsed = []
    exposed = {(cur_hx, cur_hy)}
    tnt_armed = set()
    bombs = [dict(b) for b in tracked_bombs]

    def is_hw(x, y):
        if not _in_bounds(x, y):
            return True
        t = get_t(x, y)
        if t == "UNKNOWN":
            return not treat_unknown_as_empty
        return _is_high_wall_tile(t, cur_gf)

    def can_hero(x, y):
        if is_hw(x, y):
            return False
        if get_o(x, y) in ("BOX", "TNT"):
            return False
        return True

    def can_box(x, y):
        if is_hw(x, y):
            return False
        if get_o(x, y) is not None:
            return False
        if (x, y) == (cur_hx, cur_hy):
            return False
        if get_t(x, y) in ("K1", "K2", "V", "UNKNOWN"):
            return False
        return True

    def displace(entity: str, p0, p1, dname: str, ctx: dict, suppress_portal: bool = False):
        nonlocal cur_hx, cur_hy, cur_hp, cur_k1, cur_k2, cur_gf, status, dmg_taken, entered_unknown
        ctx["steps"] += 1
        x0, y0 = p0
        x1, y1 = p1

        if get_t(x0, y0) == "CRACK":
            set_t(x0, y0, "PIT")
            cracks_collapsed.append((x0, y0))

        if entity == "BOX":
            set_o(x0, y0, None)
            set_o(x1, y1, "BOX")
        else:
            cur_hx, cur_hy = x1, y1
            exposed.add((x1, y1))

        t1 = get_t(x1, y1)
        if entity == "HERO" and not memory["ever_seen"][y1][x1] and t1 not in ("K1", "K2", "V"):
            entered_unknown = True

        stop_mom = False
        if entity == "BOX":
            if t1 == "PIT":
                set_o(x1, y1, None)
                set_t(x1, y1, "EMPTY")
                return
            elif t1 == "CHEST" and chest_types.get((x1, y1)) != "HEAL":
                set_t(x1, y1, "EMPTY")
            elif t1 == "SWITCH":
                cur_gf = not cur_gf
        else:
            if t1 == "PIT":
                dmg_taken += 100
                cur_hp -= 100
            elif t1 == "CHEST":
                ctype = chest_types.get((x1, y1), "UNVERIFIED")
                if ctype == "HEAL":
                    cur_hp = min(100, cur_hp + 30)
                    set_t(x1, y1, "EMPTY")
                else:
                    dmg_taken += 45
                    cur_hp -= 45
                    set_t(x1, y1, "EMPTY")
                    stop_mom = True
            elif t1 == "SWITCH":
                cur_gf = not cur_gf

        if entity == "HERO" and cur_hp <= 0:
            status = "DEAD"
            return

        if entity == "HERO":
            ct = get_t(x1, y1)
            if ct == "K1":
                cur_k1 = True
                set_t(x1, y1, "EMPTY")
            elif ct == "K2":
                cur_k2 = True
                set_t(x1, y1, "EMPTY")
            elif ct == "V" and cur_k1 and cur_k2 and cur_hp > 0:
                status = "CLEARED"
                return

        if ctx["steps"] >= 32 or stop_mom:
            return

        ct = get_t(x1, y1)
        ce = can_hero if entity == "HERO" else can_box

        if suppress_portal:
            if ctx["portals"] >= 2:
                return
            dx, dy = DIRECTIONS[dname]
            nx, ny = x1 + dx, y1 + dy
            if _in_bounds(nx, ny) and get_t(nx, ny) == "UNKNOWN" and entity == "HERO":
                entered_unknown = True
            if ce(nx, ny):
                displace(entity, (x1, y1), (nx, ny), dname, ctx, False)
            return

        if ct == "ICE":
            dx, dy = DIRECTIONS[dname]
            nx, ny = x1 + dx, y1 + dy
            if _in_bounds(nx, ny) and get_t(nx, ny) == "UNKNOWN" and entity == "HERO":
                entered_unknown = True
            if ce(nx, ny):
                displace(entity, (x1, y1), (nx, ny), dname, ctx, False)
        elif ct in MIRROR_MAP:
            ndir = MIRROR_MAP[ct][dname]
            dx, dy = DIRECTIONS[ndir]
            nx, ny = x1 + dx, y1 + dy
            if _in_bounds(nx, ny) and get_t(nx, ny) == "UNKNOWN" and entity == "HERO":
                entered_unknown = True
            if ce(nx, ny):
                displace(entity, (x1, y1), (nx, ny), ndir, ctx, False)
        elif ct in SPRING_DIR:
            sdir = SPRING_DIR[ct]
            dx, dy = DIRECTIONS[sdir]
            blocked_k = None
            for k in (1, 2, 3):
                kx, ky = x1 + k * dx, y1 + k * dy
                if _in_bounds(kx, ky) and get_t(kx, ky) == "UNKNOWN" and entity == "HERO":
                    entered_unknown = True
                is_blk = False
                if not _in_bounds(kx, ky) or is_hw(kx, ky):
                    is_blk = True
                elif get_o(kx, ky) in ("BOX", "TNT"):
                    is_blk = True
                elif entity == "BOX" and ((kx, ky) == (cur_hx, cur_hy) or get_t(kx, ky) in ("K1", "K2", "V")):
                    is_blk = True
                if is_blk:
                    blocked_k = k
                    if entity == "BOX" and _in_bounds(kx, ky) and get_o(kx, ky) == "TNT":
                        tnt_armed.add((kx, ky))
                    break
            if blocked_k == 1:
                return
            tk = (blocked_k - 1) if blocked_k in (2, 3) else 3
            displace(entity, (x1, y1), (x1 + tk * dx, y1 + tk * dy), sdir, ctx, False)
        elif ct in PORTAL_PAIR_TILE:
            pair_tile = PORTAL_PAIR_TILE[ct]
            if pair_tile not in portals:
                if entity == "HERO":
                    entered_unknown = True
                return
            px, py = portals[pair_tile]
            if get_o(px, py) is not None:
                return
            if entity == "BOX" and (px, py) == (cur_hx, cur_hy):
                return
            ctx["portals"] += 1
            displace(entity, (x1, y1), (px, py), dname, ctx, True)

    if action == "WAIT":
        pass
    elif action == "BOMB":
        if cur_bombs_inv > 0 and not any(b["x"] == cur_hx and b["y"] == cur_hy for b in bombs):
            cur_bombs_inv -= 1
            bombs.append({"x": cur_hx, "y": cur_hy, "timer": 3})
    elif action.startswith("MOVE_"):
        dname = action[5:]
        dx, dy = DIRECTIONS[dname]
        p1x, p1y = cur_hx + dx, cur_hy + dy
        if not is_hw(p1x, p1y) and get_o(p1x, p1y) != "TNT":
            if get_o(p1x, p1y) == "BOX":
                p2x, p2y = cur_hx + 2 * dx, cur_hy + 2 * dy
                if can_box(p2x, p2y):
                    displace("BOX", (p1x, p1y), (p2x, p2y), dname, {"steps": 0, "portals": 0}, False)
                    if status == "ALIVE" and can_hero(p1x, p1y):
                        displace("HERO", (cur_hx, cur_hy), (p1x, p1y), dname, {"steps": 0, "portals": 0}, False)
            else:
                displace("HERO", (cur_hx, cur_hy), (p1x, p1y), dname, {"steps": 0, "portals": 0}, False)
    elif action.startswith("JUMP_"):
        if cur_jumps > 0:
            cur_jumps -= 1
            dname = action[5:]
            dx, dy = DIRECTIONS[dname]
            p1x, p1y = cur_hx + dx, cur_hy + dy
            p2x, p2y = cur_hx + 2 * dx, cur_hy + 2 * dy
            if not is_hw(p1x, p1y) and _in_bounds(p2x, p2y) and can_hero(p2x, p2y):
                displace("HERO", (cur_hx, cur_hy), (p2x, p2y), dname, {"steps": 0, "portals": 0}, False)
    elif action.startswith("THROW_"):
        if cur_throws > 0:
            cur_throws -= 1
            dname = action[6:]
            sx, sy = cur_hx, cur_hy
            rleft = 6
            sp = 0
            shattered = False
            while rleft > 0:
                dx, dy = DIRECTIONS[dname]
                sx, sy = sx + dx, sy + dy
                rleft -= 1
                if not _in_bounds(sx, sy) or is_hw(sx, sy) or get_o(sx, sy) == "BOX":
                    shattered = True
                    break
                if get_o(sx, sy) == "TNT":
                    tnt_armed.add((sx, sy))
                    shattered = True
                    break
                ct = get_t(sx, sy)
                if ct == "SWITCH":
                    cur_gf = not cur_gf
                    shattered = True
                    break
                if ct == "CHEST" and chest_types.get((sx, sy)) == "MIMIC":
                    set_t(sx, sy, "EMPTY")
                    shattered = True
                    break
                if ct in MIRROR_MAP:
                    dname = MIRROR_MAP[ct][dname]
                elif ct in PORTAL_PAIR_TILE and sp < 2:
                    pt = PORTAL_PAIR_TILE[ct]
                    if pt in portals and get_o(portals[pt][0], portals[pt][1]) not in ("BOX", "TNT"):
                        sx, sy = portals[pt]
                        sp += 1
                        if sp == 2:
                            shattered = True
                            break
            if not shattered and rleft == 0 and get_t(sx, sy) in ("ICE", *MIRROR_MAP.keys()):
                for _ in range(32):
                    dx, dy = DIRECTIONS[dname]
                    sx, sy = sx + dx, sy + dy
                    if not _in_bounds(sx, sy) or is_hw(sx, sy) or get_o(sx, sy) == "BOX":
                        break
                    if get_o(sx, sy) == "TNT":
                        tnt_armed.add((sx, sy))
                        break
                    ct = get_t(sx, sy)
                    if ct == "SWITCH":
                        cur_gf = not cur_gf
                        break
                    if ct == "CHEST" and chest_types.get((sx, sy)) == "MIMIC":
                        set_t(sx, sy, "EMPTY")
                        break
                    if ct in MIRROR_MAP:
                        dname = MIRROR_MAP[ct][dname]
                    elif ct == "ICE":
                        continue
                    elif ct in PORTAL_PAIR_TILE and sp < 2:
                        pt = PORTAL_PAIR_TILE[ct]
                        if pt in portals and get_o(portals[pt][0], portals[pt][1]) not in ("BOX", "TNT"):
                            sx, sy = portals[pt]
                            sp += 1
                            if sp == 2:
                                break
                        else:
                            break
                    else:
                        break

    if status in ("DEAD", "CLEARED"):
        return {
            "hx": cur_hx, "hy": cur_hy, "hp": cur_hp, "k1": cur_k1, "k2": cur_k2,
            "jumps": cur_jumps, "throws": cur_throws, "bombs_inv": cur_bombs_inv,
            "gf": cur_gf, "status": status, "dmg": dmg_taken,
            "entered_unknown": entered_unknown, "bombs": bombs,
            "t_mod": t_mod, "o_mod": o_mod, "cracks": cracks_collapsed,
        }

    def resolve_blast(init_b, init_tnt):
        nonlocal cur_hp, status, dmg_taken, bombs
        if not init_b and not init_tnt:
            return
        q = collections.deque()
        exp_b_idx = set()
        exp_tnt = set()
        for idx in init_b:
            exp_b_idx.add(idx)
            q.append(("BOMB", bombs[idx]["x"], bombs[idx]["y"]))
        for tx, ty in init_tnt:
            if (tx, ty) not in exp_tnt and get_o(tx, ty) == "TNT":
                exp_tnt.add((tx, ty))
                q.append(("TNT", tx, ty))
        affected = set()
        sources = []
        while q:
            st, ex, ey = q.popleft()
            sources.append((st, ex, ey))
            for ny in range(max(0, ey - 1), min(GRID_HEIGHT, ey + 2)):
                for nx in range(max(0, ex - 1), min(GRID_WIDTH, ex + 2)):
                    affected.add((nx, ny))
                    if get_o(nx, ny) == "TNT" and (nx, ny) not in exp_tnt:
                        exp_tnt.add((nx, ny))
                        q.append(("TNT", nx, ny))
                    for bi, bobj in enumerate(bombs):
                        if bi not in exp_b_idx and bobj["x"] == nx and bobj["y"] == ny:
                            exp_b_idx.add(bi)
                            q.append(("BOMB", bobj["x"], bobj["y"]))
        bdmg = 0
        for st, ex, ey in sources:
            if abs(cur_hx - ex) <= 1 and abs(cur_hy - ey) <= 1:
                bdmg += (60 if st == "TNT" else 50)
        if bdmg > 0:
            dmg_taken += bdmg
            cur_hp -= bdmg
        bombs = [bobj for bi, bobj in enumerate(bombs) if bi not in exp_b_idx]
        for tx, ty in exp_tnt:
            set_o(tx, ty, None)
        for cx, cy in affected:
            if get_o(cx, cy) == "BOX":
                set_o(cx, cy, None)
            ct = get_t(cx, cy)
            if ct in EXPLOSION_IMMUNE or ct == "UNKNOWN":
                pass
            elif ct == "CRACK":
                set_t(cx, cy, "PIT")
            else:
                set_t(cx, cy, "EMPTY")
            if get_o(cx, cy) == "BOX" and get_t(cx, cy) == "PIT":
                set_o(cx, cy, None)
                set_t(cx, cy, "EMPTY")
        if cur_hp > 0 and get_t(cur_hx, cur_hy) == "PIT":
            dmg_taken += 100
            cur_hp -= 100
        if cur_hp <= 0:
            status = "DEAD"

    for b in bombs:
        b["timer"] -= 1
    due_idx = [i for i, b in enumerate(bombs) if b["timer"] <= 0]
    if due_idx or tnt_armed:
        resolve_blast(due_idx, tnt_armed)
        if status == "DEAD":
            return {
                "hx": cur_hx, "hy": cur_hy, "hp": cur_hp, "k1": cur_k1, "k2": cur_k2,
                "jumps": cur_jumps, "throws": cur_throws, "bombs_inv": cur_bombs_inv,
                "gf": cur_gf, "status": status, "dmg": dmg_taken,
                "entered_unknown": entered_unknown, "bombs": bombs,
                "t_mod": t_mod, "o_mod": o_mod, "cracks": cracks_collapsed,
            }

    if turn % 3 == 0:
        hits = 0
        covered = set()
        laser_tnts = set()
        for (lx, ly), dname in memory["lasers"].items():
            if get_t(lx, ly) not in LASER_DIR:
                continue
            dx, dy = DIRECTIONS[dname]
            beam_hit = False
            for dist in range(1, 11):
                nx, ny = lx + dist * dx, ly + dist * dy
                if not _in_bounds(nx, ny):
                    break
                ct = get_t(nx, ny)
                co = get_o(nx, ny)
                if ct != "UNKNOWN" and _is_high_wall_tile(ct, cur_gf):
                    break
                if co == "BOX":
                    break
                if co == "TNT":
                    laser_tnts.add((nx, ny))
                    break
                covered.add((nx, ny, dname))
                if (nx, ny) in exposed:
                    beam_hit = True
            if beam_hit:
                hits += 1

        grouped_warns = collections.defaultdict(list)
        for wx, wy, dname in memory["warn_beams"]:
            if (wx, wy, dname) not in covered:
                grouped_warns[(dname, wy if dname in ("L", "R") else wx)].append((wx, wy))
        for (dname, _), cells in grouped_warns.items():
            dx, dy = DIRECTIONS[dname]
            ax, ay = max(cells, key=lambda p: p[0] * dx + p[1] * dy)
            beam_cells = set()
            for back in range(0, 10):
                bx, by = ax - back * dx, ay - back * dy
                if not _in_bounds(bx, by):
                    break
                ct = get_t(bx, by)
                if ct != "UNKNOWN" and (_is_high_wall_tile(ct, cur_gf) or get_o(bx, by) in ("BOX", "TNT")):
                    break
                beam_cells.add((bx, by))
            if beam_cells & exposed:
                hits += 1

        if hits > 0:
            dmg_taken += 50 * hits
            cur_hp -= 50 * hits
            if cur_hp <= 0:
                status = "DEAD"
        if status == "ALIVE" and laser_tnts:
            resolve_blast([], laser_tnts)

    return {
        "hx": cur_hx, "hy": cur_hy, "hp": cur_hp, "k1": cur_k1, "k2": cur_k2,
        "jumps": cur_jumps, "throws": cur_throws, "bombs_inv": cur_bombs_inv,
        "gf": cur_gf, "status": status, "dmg": dmg_taken,
        "entered_unknown": entered_unknown, "bombs": bombs,
        "t_mod": t_mod, "o_mod": o_mod, "cracks": cracks_collapsed,
    }


def _has_safe_followup(sim_res: dict, next_turn: int, base_terrain, base_occ,
                       chest_types: dict, portals: dict, memory: dict, max_dmg: int = 0) -> bool:
    if sim_res["status"] == "CLEARED":
        return True
    if sim_res["status"] == "DEAD":
        return False

    has_mods = bool(sim_res["t_mod"] or sim_res["o_mod"])
    if has_mods:
        t_grid = [row[:] for row in base_terrain]
        o_grid = [row[:] for row in base_occ]
        for (x, y), v in sim_res["t_mod"].items():
            t_grid[y][x] = v
        for (x, y), v in sim_res["o_mod"].items():
            o_grid[y][x] = v
    else:
        t_grid = base_terrain
        o_grid = base_occ

    check_acts = ("WAIT", "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R")
    if sim_res["jumps"] > 0:
        check_acts = check_acts + ("JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R")

    for act2 in check_acts:
        r2 = _sim_single_turn(
            sim_res["hx"], sim_res["hy"], sim_res["hp"], sim_res["k1"], sim_res["k2"],
            sim_res["jumps"], sim_res["throws"], sim_res["bombs_inv"], sim_res["gf"],
            next_turn, act2, t_grid, o_grid, chest_types, portals,
            sim_res["bombs"], memory, treat_unknown_as_empty=False,
        )
        if r2["status"] == "CLEARED":
            return True
        if r2["status"] == "ALIVE" and r2["dmg"] <= max_dmg and not r2["entered_unknown"]:
            return True
    return False


# ==============================================================================
# 四维时空 Dijkstra 规划器: (x, y, turn % 3, gates_flipped)
# ==============================================================================

def _run_temporal_dijkstra(
    start_state: dict,
    memory: dict,
    chest_types: dict,
    goals: set,
    allow_unknown_walk: bool = True,
    allow_blind_hazard: bool = False,
    max_step_dmg: int = 0,
    terrain_override=None,
    occ_override=None,
    frontier_gain=None,
    deadline: float = 0.0,
):
    terrain = terrain_override if terrain_override is not None else memory["terrain"]
    occupant = occ_override if occ_override is not None else memory["occupant"]
    ever_seen = memory["ever_seen"]
    portals = memory["portals"]
    tracked_bombs = memory["tracked_bombs"]
    visit_counts = memory["visit_counts"]

    hero = start_state["hero"]
    hx0, hy0 = hero["x"], hero["y"]
    hp0 = hero["hp"]
    k1_0, k2_0 = hero["keys"][0], hero["keys"][1]
    jumps0 = hero["jumps"]
    throws0 = hero["throws"]
    bombs_inv0 = hero["bombs"]
    gf0 = start_state["gates_flipped"]
    turn0 = start_state["turn"]

    laser_map = {
        False: _compute_laser_hit_counts(memory, False, occupant),
        True: _compute_laser_hit_counts(memory, True, occupant),
    }

    if frontier_gain is None:
        frontier_gain = {False: {}, True: {}}

    start_node = (hx0, hy0, (turn0 - 1) % 3, gf0)
    dist = {start_node: 0.0}
    used_cracks = {start_node: frozenset()}
    pq = [(0.0, turn0 - 1, hx0, hy0, gf0, jumps0, None)]

    best_goal_act = None
    best_goal_cost = float("inf")
    best_front_act = None
    best_front_score = float("inf")

    goal_list = list(goals)

    def min_goal_dist(x, y):
        if not goal_list:
            return 0
        return min(abs(x - gx) + abs(y - gy) for gx, gy in goal_list)

    expansions = 0
    while pq:
        if deadline > 0.0 and (expansions & 63) == 0 and time.perf_counter() > deadline:
            break
        expansions += 1

        cost, prev_t, x, y, gf, jleft, fa = heapq.heappop(pq)
        cur_node = (x, y, prev_t % 3, gf)
        if cost > dist.get(cur_node, float("inf")) + 1e-6:
            continue

        if fa is not None:
            if (x, y) in goals and (ever_seen[y][x] or allow_unknown_walk):
                best_goal_act = fa
                best_goal_cost = cost
                break
            gain = frontier_gain[gf].get((x, y), 0)
            if gain > 0 and (x, y) != (hx0, hy0):
                f_score = cost + 0.40 * min_goal_dist(x, y) - 0.18 * gain
                if f_score < best_front_score:
                    best_front_score = f_score
                    best_front_act = fa

        cur_turn = prev_t + 1
        if cur_turn > MAX_TURNS:
            continue

        if prev_t == turn0 - 1:
            root_acts = ["MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT"]
            if jleft > 0:
                root_acts.extend(["JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R"])
            if throws0 > 0:
                root_acts.extend(["THROW_U", "THROW_D", "THROW_L", "THROW_R"])

            for act in root_acts:
                sr = _sim_single_turn(
                    hx0, hy0, hp0, k1_0, k2_0, jleft, throws0, bombs_inv0, gf0,
                    cur_turn, act, terrain, occupant, chest_types, portals,
                    tracked_bombs, memory, treat_unknown_as_empty=False,
                )
                if sr["status"] == "DEAD" or sr["dmg"] > max_step_dmg:
                    continue
                if sr["entered_unknown"] and not allow_blind_hazard:
                    continue
                if sr["status"] == "CLEARED":
                    return act, cost + 1.0, act, cost + 1.0
                if not _has_safe_followup(sr, cur_turn + 1, terrain, occupant, chest_types, portals, memory, max_step_dmg):
                    continue

                nx, ny, ngf = sr["hx"], sr["hy"], sr["gf"]
                if act.startswith("THROW_") and ngf == gf0 and not sr["t_mod"] and not sr["o_mod"]:
                    continue
                if act.startswith("MOVE_") and (nx, ny) == (hx0, hy0) and ngf == gf0 and not sr["o_mod"]:
                    continue
                if act.startswith("JUMP_") and (nx, ny) == (hx0, hy0):
                    continue

                if (sr["k1"] != k1_0 or sr["k2"] != k2_0) and (nx, ny) in goals:
                    return act, 1.0, act, 1.0

                vc = min(6, visit_counts.get((nx, ny, ngf, sr["k1"], sr["k2"]), 0))
                step_c = (1.28 if act == "WAIT" else 1.0) + 0.15 * vc + 0.4 * sr["dmg"]
                if act.startswith("JUMP_"):
                    step_c += 13.0
                elif act.startswith("THROW_"):
                    step_c += 4.0
                if sr["cracks"]:
                    step_c += 3.5 * len(sr["cracks"])

                nnode = (nx, ny, cur_turn % 3, ngf)
                ncost = cost + step_c
                if ncost < dist.get(nnode, float("inf")):
                    dist[nnode] = ncost
                    used_cracks[nnode] = frozenset(sr["cracks"])
                    heapq.heappush(pq, (ncost, cur_turn, nx, ny, ngf, sr["jumps"], act))
            continue

        c_set = used_cracks.get(cur_node, frozenset())

        if not ever_seen[y][x]:
            if not allow_unknown_walk:
                continue
            for dname, (dx, dy) in DIRECTIONS.items():
                nx, ny = x + dx, y + dy
                if not _in_bounds(nx, ny):
                    continue
                if ever_seen[ny][nx]:
                    nt = terrain[ny][nx]
                    if _is_high_wall_tile(nt, gf) or occupant[ny][nx] in ("BOX", "TNT") or nt == "PIT" or (nx, ny) in c_set:
                        continue
                nnode = (nx, ny, cur_turn % 3, gf)
                ncost = cost + 2.2
                if ncost < dist.get(nnode, float("inf")):
                    dist[nnode] = ncost
                    used_cracks[nnode] = c_set
                    heapq.heappush(pq, (ncost, cur_turn, nx, ny, gf, jleft, fa))
            continue

        cand_inner = ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT")
        if jleft > 0:
            cand_inner = cand_inner + ("JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R")

        for act in cand_inner:
            nj = jleft
            step_c = 1.28 if act == "WAIT" else 1.0
            if act == "WAIT":
                nx, ny, ngf = x, y, gf
                exp_cells = {(x, y)}
                new_cracks = c_set
                dmg = 0
            else:
                is_jump = act.startswith("JUMP_")
                dname = act[5:]
                dx, dy = DIRECTIONS[dname]
                if is_jump:
                    p1x, p1y = x + dx, y + dy
                    tx, ty = x + 2 * dx, y + 2 * dy
                    if not _in_bounds(tx, ty) or not ever_seen[p1y][p1x]:
                        continue
                    if _is_high_wall_tile(terrain[p1y][p1x], gf):
                        continue
                    if not ever_seen[ty][tx]:
                        continue
                    nj -= 1
                    step_c += 13.0
                else:
                    tx, ty = x + dx, y + dy
                    if not _in_bounds(tx, ty):
                        continue

                if not ever_seen[ty][tx]:
                    if not allow_unknown_walk or is_jump:
                        continue
                    ncr = c_set | ({(x, y)} if terrain[y][x] == "CRACK" else set())
                    nnode = (tx, ty, cur_turn % 3, gf)
                    ncost = cost + 2.2 + (3.5 if terrain[y][x] == "CRACK" else 0.0)
                    if ncost < dist.get(nnode, float("inf")):
                        dist[nnode] = ncost
                        used_cracks[nnode] = ncr
                        heapq.heappush(pq, (ncost, cur_turn, tx, ty, gf, nj, fa))
                    continue

                tt = terrain[ty][tx]
                if _is_high_wall_tile(tt, gf) or occupant[ty][tx] in ("BOX", "TNT") or (tx, ty) in c_set:
                    continue

                cx0, cy0 = x, y
                cx1, cy1 = tx, ty
                cd = dname
                ngf = gf
                exp_cells = {(x, y)}
                ncr_mut = set(c_set)
                dmg = 0
                unk_hit = False
                p_cnt = 0
                sup_p = False
                aborted = False

                for _step_i in range(32):
                    if ever_seen[cy0][cx0] and terrain[cy0][cx0] == "CRACK" and (cx0, cy0) not in ncr_mut:
                        ncr_mut.add((cx0, cy0))
                        step_c += 3.5
                    exp_cells.add((cx1, cy1))
                    if not ever_seen[cy1][cx1]:
                        unk_hit = True
                        break
                    ct = "PIT" if ((cx1, cy1) in ncr_mut and (cx1, cy1) != (cx0, cy0) and terrain[cy1][cx1] == "CRACK") else terrain[cy1][cx1]
                    stop_m = False
                    if ct == "PIT":
                        dmg += 100
                        aborted = True
                        break
                    elif ct == "CHEST":
                        ctp = chest_types.get((cx1, cy1), "UNVERIFIED")
                        if ctp == "HEAL":
                            step_c = max(0.2, step_c - 0.5)
                        else:
                            dmg += 45
                            stop_m = True
                    elif ct == "SWITCH":
                        ngf = not ngf

                    if (cx1, cy1) in goals and ct == "V" and k1_0 and k2_0:
                        exp_cells = set()
                        break

                    if _step_i == 31 or stop_m:
                        break

                    if sup_p:
                        sup_p = False
                        if p_cnt >= 2:
                            break
                        ddx, ddy = DIRECTIONS[cd]
                        nnx, nny = cx1 + ddx, cy1 + ddy
                        if not _in_bounds(nnx, nny):
                            break
                        if not ever_seen[nny][nnx]:
                            unk_hit = True
                            break
                        if _is_high_wall_tile(terrain[nny][nnx], ngf) or occupant[nny][nnx] in ("BOX", "TNT"):
                            break
                        cx0, cy0, cx1, cy1 = cx1, cy1, nnx, nny
                        continue

                    if ct == "ICE":
                        ddx, ddy = DIRECTIONS[cd]
                        nnx, nny = cx1 + ddx, cy1 + ddy
                        if not _in_bounds(nnx, nny):
                            break
                        if not ever_seen[nny][nnx]:
                            if allow_unknown_walk:
                                cx0, cy0, cx1, cy1 = cx1, cy1, nnx, nny
                                step_c += 2.5
                            else:
                                unk_hit = True
                            break
                        if _is_high_wall_tile(terrain[nny][nnx], ngf) or occupant[nny][nnx] in ("BOX", "TNT"):
                            break
                        cx0, cy0, cx1, cy1 = cx1, cy1, nnx, nny
                    elif ct in MIRROR_MAP:
                        cd = MIRROR_MAP[ct][cd]
                        ddx, ddy = DIRECTIONS[cd]
                        nnx, nny = cx1 + ddx, cy1 + ddy
                        if not _in_bounds(nnx, nny):
                            break
                        if not ever_seen[nny][nnx]:
                            if allow_unknown_walk:
                                cx0, cy0, cx1, cy1 = cx1, cy1, nnx, nny
                                step_c += 2.5
                            else:
                                unk_hit = True
                            break
                        if _is_high_wall_tile(terrain[nny][nnx], ngf) or occupant[nny][nnx] in ("BOX", "TNT"):
                            break
                        cx0, cy0, cx1, cy1 = cx1, cy1, nnx, nny
                    elif ct in SPRING_DIR:
                        cd = SPRING_DIR[ct]
                        ddx, ddy = DIRECTIONS[cd]
                        blk_k = None
                        for kk in (1, 2, 3):
                            kx, ky = cx1 + kk * ddx, cy1 + kk * ddy
                            if not _in_bounds(kx, ky):
                                blk_k = kk
                                break
                            if not ever_seen[ky][kx]:
                                unk_hit = True
                                break
                            if _is_high_wall_tile(terrain[ky][kx], ngf) or occupant[ky][kx] in ("BOX", "TNT"):
                                blk_k = kk
                                break
                        if unk_hit or blk_k == 1:
                            break
                        tk = (blk_k - 1) if blk_k in (2, 3) else 3
                        cx0, cy0, cx1, cy1 = cx1, cy1, cx1 + tk * ddx, cy1 + tk * ddy
                    elif ct in PORTAL_PAIR_TILE:
                        pt = PORTAL_PAIR_TILE[ct]
                        if pt not in portals:
                            unk_hit = True
                            break
                        px, py = portals[pt]
                        if occupant[py][px] is not None:
                            break
                        p_cnt += 1
                        sup_p = True
                        cx0, cy0, cx1, cy1 = cx1, cy1, px, py
                    else:
                        break

                if aborted:
                    continue
                if unk_hit and not allow_blind_hazard:
                    continue
                nx, ny = cx1, cy1
                new_cracks = frozenset(ncr_mut)

            if tracked_bombs and cur_turn - (turn0 - 1) <= 3:
                dt_b = cur_turn - (turn0 - 1)
                if any(b["timer"] == dt_b and abs(nx - b["x"]) <= 1 and abs(ny - b["y"]) <= 1 for b in tracked_bombs):
                    continue

            if cur_turn % 3 == 0 and exp_cells:
                lmap = laser_map[ngf]
                l_hits = max((lmap.get(ec, 0) for ec in exp_cells), default=0)
                if l_hits > 0:
                    dmg += 50 * l_hits

            if dmg > max_step_dmg or dmg >= hp0:
                continue

            vc = min(6, visit_counts.get((nx, ny, ngf, k1_0, k2_0), 0))
            step_c += 0.15 * vc + 0.4 * dmg
            nnode = (nx, ny, cur_turn % 3, ngf)
            ncost = cost + step_c
            if ncost < dist.get(nnode, float("inf")):
                dist[nnode] = ncost
                used_cracks[nnode] = new_cracks
                heapq.heappush(pq, (ncost, cur_turn, nx, ny, ngf, nj, fa))

    return best_goal_act, best_goal_cost, best_front_act, best_front_score


# ==============================================================================
# 专项战术求解器: 全物理飞石打靶(含镜面/冰滑) / 推箱解谜(填坑+开关+让路) / 双层炸弹破墙
# ==============================================================================

def _trace_stone_hit(vx: int, vy: int, dname: str, gf: bool, terrain, occupant, ever_seen, chest_types: dict, portals: dict):
    """前向模拟从 (vx, vy) 向 dname 投掷飞石(支持斜坡折转、传送门、第6格冰面滑行)，返回命中的有效目标 (kind, tx, ty) 或 None。"""
    sx, sy = vx, vy
    rleft = 6
    sp = 0
    while rleft > 0:
        dx, dy = DIRECTIONS[dname]
        sx, sy = sx + dx, sy + dy
        rleft -= 1
        if not _in_bounds(sx, sy) or not ever_seen[sy][sx]:
            return None
        co = occupant[sy][sx]
        ct = terrain[sy][sx]
        if _is_high_wall_tile(ct, gf) or co == "BOX":
            return None
        if co == "TNT":
            return ("TNT", sx, sy)
        if ct == "SWITCH":
            return ("SWITCH", sx, sy)
        if ct == "CHEST" and chest_types.get((sx, sy)) in ("MIMIC", "UNVERIFIED"):
            return ("CHEST", sx, sy)
        if ct in MIRROR_MAP:
            dname = MIRROR_MAP[ct][dname]
        elif ct in PORTAL_PAIR_TILE and sp < 2:
            pt = PORTAL_PAIR_TILE[ct]
            if pt not in portals:
                return None
            px, py = portals[pt]
            if occupant[py][px] in ("BOX", "TNT"):
                pass
            else:
                sx, sy = px, py
                sp += 1
                if sp == 2:
                    return None

    if ever_seen[sy][sx] and terrain[sy][sx] in ("ICE", *MIRROR_MAP.keys()):
        for _ in range(32):
            dx, dy = DIRECTIONS[dname]
            sx, sy = sx + dx, sy + dy
            if not _in_bounds(sx, sy) or not ever_seen[sy][sx]:
                return None
            co = occupant[sy][sx]
            ct = terrain[sy][sx]
            if _is_high_wall_tile(ct, gf) or co == "BOX":
                return None
            if co == "TNT":
                return ("TNT", sx, sy)
            if ct == "SWITCH":
                return ("SWITCH", sx, sy)
            if ct == "CHEST" and chest_types.get((sx, sy)) in ("MIMIC", "UNVERIFIED"):
                return ("CHEST", sx, sy)
            if ct in MIRROR_MAP:
                dname = MIRROR_MAP[ct][dname]
            elif ct == "ICE":
                continue
            elif ct in PORTAL_PAIR_TILE and sp < 2:
                pt = PORTAL_PAIR_TILE[ct]
                if pt in portals and occupant[portals[pt][1]][portals[pt][0]] not in ("BOX", "TNT"):
                    sx, sy = portals[pt]
                    sp += 1
                    if sp == 2:
                        return None
                else:
                    return None
            else:
                return None
    return None


def _find_remote_throw_action(state: dict, memory: dict, chest_types: dict, goals: set, fg_cache: dict, deadline: float):
    hero = state["hero"]
    if hero["throws"] <= 0:
        return None
    hx, hy = hero["x"], hero["y"]
    gf = state["gates_flipped"]
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    ever_seen = memory["ever_seen"]
    portals = memory["portals"]

    # 先验证哪些目标在被击中后能真正打通通往 goals 的道路
    useful_targets = set()
    # 1. 检查翻转门态是否有益
    fake_state = dict(state)
    fake_state["gates_flipped"] = not gf
    ga_sw, _, _, _ = _run_temporal_dijkstra(
        fake_state, memory, chest_types, goals,
        allow_unknown_walk=True, allow_blind_hazard=False, max_step_dmg=0,
        deadline=deadline,
    )
    if ga_sw is not None:
        useful_targets.add(("SWITCH", -1, -1))

    # 2. 检查已知 TNT 爆破是否有益
    for y in range(1, GRID_HEIGHT - 1):
        for x in range(1, GRID_WIDTH - 1):
            if not ever_seen[y][x]:
                continue
            if occupant[y][x] == "TNT":
                sim_t = [r[:] for r in terrain]
                sim_o = [r[:] for r in occupant]
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if _in_bounds(nx, ny) and ever_seen[ny][nx]:
                            if sim_o[ny][nx] in ("BOX", "TNT"):
                                sim_o[ny][nx] = None
                            ct = sim_t[ny][nx]
                            if ct not in EXPLOSION_IMMUNE:
                                sim_t[ny][nx] = "PIT" if ct == "CRACK" else "EMPTY"
                ga_tnt, _, fa_tnt, _ = _run_temporal_dijkstra(
                    state, memory, chest_types, goals,
                    allow_unknown_walk=True, allow_blind_hazard=False, max_step_dmg=0,
                    terrain_override=sim_t, occ_override=sim_o, frontier_gain=fg_cache,
                    deadline=deadline,
                )
                if ga_tnt is not None or fa_tnt is not None:
                    useful_targets.add(("TNT", x, y))
            elif terrain[y][x] == "CHEST" and chest_types.get((x, y)) in ("MIMIC", "UNVERIFIED") and (x, y) not in memory["probed_chests"]:
                sim_t = [r[:] for r in terrain]
                sim_t[y][x] = "EMPTY"
                ga_ch, _, _, _ = _run_temporal_dijkstra(
                    state, memory, chest_types, goals,
                    allow_unknown_walk=True, allow_blind_hazard=False, max_step_dmg=0,
                    terrain_override=sim_t, deadline=deadline,
                )
                if ga_ch is not None:
                    useful_targets.add(("CHEST", x, y))

    if not useful_targets:
        return None

    # 扫描所有已知安全站立格上的四向投掷结果（< 1ms，完整支持斜坡反弹与冰面滑行！）
    vantage_map = {}
    non_standable = {"PIT", "ICE", *MIRROR_MAP.keys(), *SPRING_DIR.keys(), *PORTAL_PAIR_TILE.keys()}
    for y in range(1, GRID_HEIGHT - 1):
        for x in range(1, GRID_WIDTH - 1):
            if not ever_seen[y][x]:
                continue
            vt = terrain[y][x]
            if _is_high_wall_tile(vt, gf) or vt in non_standable or occupant[y][x] is not None:
                continue
            for dname in ("U", "D", "L", "R"):
                hit = _trace_stone_hit(x, y, dname, gf, terrain, occupant, ever_seen, chest_types, portals)
                if hit is None:
                    continue
                hkind, tx, ty = hit
                if hkind == "TNT" and abs(x - tx) <= 1 and abs(y - ty) <= 1:
                    continue
                if (hkind == "SWITCH" and ("SWITCH", -1, -1) in useful_targets) or (hkind, tx, ty) in useful_targets:
                    vantage_map[(x, y)] = ("THROW_" + dname, hkind, tx, ty)
                    break

    if not vantage_map:
        return None

    if (hx, hy) in vantage_map:
        tact, hkind, tx, ty = vantage_map[(hx, hy)]
        sr = _sim_single_turn(
            hx, hy, hero["hp"], hero["keys"][0], hero["keys"][1],
            hero["jumps"], hero["throws"], hero["bombs"], gf, state["turn"],
            tact, terrain, occupant, chest_types, portals,
            memory["tracked_bombs"], memory, False,
        )
        if sr["status"] == "ALIVE" and sr["dmg"] == 0 and _has_safe_followup(
            sr, state["turn"] + 1, terrain, occupant, chest_types, portals, memory, 0
        ):
            if hkind == "CHEST":
                memory["probed_chests"].add((tx, ty))
            return tact

    nav_act, _, _, _ = _run_temporal_dijkstra(
        state, memory, chest_types, set(vantage_map.keys()),
        allow_unknown_walk=False, allow_blind_hazard=False, max_step_dmg=0,
        deadline=deadline,
    )
    return nav_act


def _find_box_puzzle_action(state: dict, memory: dict, chest_types: dict, goals: set, fg_cache: dict, deadline: float):
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    ever_seen = memory["ever_seen"]
    hero = state["hero"]
    hx0, hy0 = hero["x"], hero["y"]
    gf0 = state["gates_flipped"]

    boxes = [
        (x, y)
        for y in range(1, GRID_HEIGHT - 1)
        for x in range(1, GRID_WIDTH - 1)
        if ever_seen[y][x] and occupant[y][x] == "BOX"
    ]
    if not boxes:
        return None

    for bx0, by0 in boxes:
        if time.perf_counter() > deadline:
            break
        sim_o_base = [r[:] for r in occupant]
        sim_o_base[by0][bx0] = None

        tested_configs = set()
        q = collections.deque([(hx0, hy0, bx0, by0, gf0, None, 0)])
        seen = {(hx0, hy0, bx0, by0, gf0)}
        while q:
            if time.perf_counter() > deadline:
                break
            ux, uy, cbx, cby, cgf, fa, depth = q.popleft()
            if depth > 36:
                continue

            # 若箱子填平了 PIT、翻转了开关、或移开了原位，检验是否打通了目标道路
            if fa is not None and (cbx == -1 or cgf != gf0 or (cbx, cby) != (bx0, by0)):
                cfg_key = (cbx, cby, cgf)
                if cfg_key not in tested_configs:
                    tested_configs.add(cfg_key)
                    sim_t = terrain
                    sim_o = sim_o_base
                    if cbx == -1:
                        pit_x, pit_y = cby // 100, cby % 100
                        sim_t = [r[:] for r in terrain]
                        sim_t[pit_y][pit_x] = "EMPTY"
                    else:
                        sim_o = [r[:] for r in sim_o_base]
                        sim_o[cby][cbx] = "BOX"
                    fake_st = dict(state)
                    fake_st["gates_flipped"] = cgf
                    fake_hero = dict(hero)
                    fake_hero["x"], fake_hero["y"] = ux, uy
                    fake_st["hero"] = fake_hero
                    ga, _, _, _ = _run_temporal_dijkstra(
                        fake_st, memory, chest_types, goals,
                        allow_unknown_walk=True, allow_blind_hazard=False, max_step_dmg=0,
                        terrain_override=sim_t, occ_override=sim_o, frontier_gain=fg_cache,
                        deadline=deadline,
                    )
                    if ga is not None:
                        return fa
                if cbx == -1:
                    continue

            for dname in ("U", "D", "L", "R"):
                act = "MOVE_" + dname
                dx, dy = DIRECTIONS[dname]
                nx, ny = ux + dx, uy + dy
                if not _in_bounds(nx, ny) or not ever_seen[ny][nx]:
                    continue
                nt = terrain[ny][nx]
                if _is_high_wall_tile(nt, cgf) or sim_o_base[ny][nx] in ("BOX", "TNT"):
                    continue

                if (nx, ny) == (cbx, cby):
                    sim_o_base[cby][cbx] = "BOX"
                    sr = _sim_single_turn(
                        ux, uy, hero["hp"], hero["keys"][0], hero["keys"][1],
                        0, 0, 0, cgf, state["turn"] + depth, act,
                        terrain, sim_o_base, chest_types, memory["portals"],
                        memory["tracked_bombs"] if depth == 0 else [], memory, False,
                    )
                    sim_o_base[cby][cbx] = None
                    if sr["status"] == "DEAD" or sr["dmg"] > 0 or sr["entered_unknown"]:
                        continue
                    if depth == 0 and not _has_safe_followup(
                        sr, state["turn"] + 1, terrain, occupant, chest_types, memory["portals"], memory, 0
                    ):
                        continue
                    nbx, nby = -1, -1
                    filled_pit = None
                    for (mx, my), mv in sr["t_mod"].items():
                        if terrain[my][mx] == "PIT" and mv == "EMPTY":
                            filled_pit = (mx, my)
                    for (mx, my), ov in sr["o_mod"].items():
                        if ov == "BOX":
                            nbx, nby = mx, my
                    if nbx == -1 and (cbx, cby) not in sr["o_mod"]:
                        nbx, nby = cbx, cby
                    if filled_pit is not None:
                        nbx, nby = -1, filled_pit[0] * 100 + filled_pit[1]
                    elif nbx == -1:
                        continue
                    st_next = (sr["hx"], sr["hy"], nbx, nby, sr["gf"])
                    if st_next not in seen:
                        seen.add(st_next)
                        q.append((sr["hx"], sr["hy"], nbx, nby, sr["gf"], act if fa is None else fa, depth + 1))
                else:
                    if nt in ("PIT", "CHEST", "CRACK", "ICE", *MIRROR_MAP.keys(), *SPRING_DIR.keys(), *PORTAL_PAIR_TILE.keys()):
                        continue
                    if depth == 0:
                        sr0 = _sim_single_turn(
                            ux, uy, hero["hp"], hero["keys"][0], hero["keys"][1],
                            hero["jumps"], hero["throws"], hero["bombs"], cgf, state["turn"], act,
                            terrain, occupant, chest_types, memory["portals"],
                            memory["tracked_bombs"], memory, False,
                        )
                        if sr0["status"] == "DEAD" or sr0["dmg"] > 0 or not _has_safe_followup(
                            sr0, state["turn"] + 1, terrain, occupant, chest_types, memory["portals"], memory, 0
                        ):
                            continue
                    ngf = (not cgf) if nt == "SWITCH" else cgf
                    st_next = (nx, ny, cbx, cby, ngf)
                    if st_next not in seen:
                        seen.add(st_next)
                        q.append((nx, ny, cbx, cby, ngf, act if fa is None else fa, depth + 1))
    return None


def _can_escape_bomb_now(state: dict, memory: dict, chest_types: dict) -> bool:
    hero = state["hero"]
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    portals = memory["portals"]

    r0 = _sim_single_turn(
        hero["x"], hero["y"], hero["hp"], hero["keys"][0], hero["keys"][1],
        hero["jumps"], hero["throws"], hero["bombs"], state["gates_flipped"],
        state["turn"], "BOMB", terrain, occupant, chest_types, portals,
        memory["tracked_bombs"], memory, treat_unknown_as_empty=False,
    )
    if r0["status"] != "ALIVE" or r0["dmg"] > 0:
        return False

    layer = [r0]
    move_acts = ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT", "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R")
    for offset in (1, 2):
        nxt_layer = []
        seen = set()
        for st in layer:
            t_grid = [row[:] for row in terrain]
            o_grid = [row[:] for row in occupant]
            for (cx, cy), v in st["t_mod"].items():
                t_grid[cy][cx] = v
            for (cx, cy), v in st["o_mod"].items():
                o_grid[cy][cx] = v
            for act in move_acts:
                if act.startswith("JUMP_") and st["jumps"] <= 0:
                    continue
                rn = _sim_single_turn(
                    st["hx"], st["hy"], st["hp"], st["k1"], st["k2"],
                    st["jumps"], st["throws"], st["bombs_inv"], st["gf"],
                    state["turn"] + offset, act, t_grid, o_grid, chest_types, portals,
                    st["bombs"], memory, treat_unknown_as_empty=False,
                )
                if rn["status"] == "CLEARED":
                    return True
                if rn["status"] == "ALIVE" and rn["dmg"] == 0 and not rn["entered_unknown"]:
                    merged_t = dict(st["t_mod"])
                    merged_t.update(rn["t_mod"])
                    merged_o = dict(st["o_mod"])
                    merged_o.update(rn["o_mod"])
                    rn["t_mod"] = merged_t
                    rn["o_mod"] = merged_o
                    sig = (rn["hx"], rn["hy"], rn["gf"], rn["jumps"])
                    if sig not in seen:
                        seen.add(sig)
                        nxt_layer.append(rn)
        layer = nxt_layer
        if not layer:
            return False
    return True


def _find_bomb_breach_action(state: dict, memory: dict, chest_types: dict, goals: set, deadline: float):
    """
    穿墙层数 Dijkstra 爆破规划器 (< 1ms)：支持 1 层及 2 层可炸毁墙体 (W/GATE/LASER/TNT) 连续破障！
    """
    hero = state["hero"]
    bombs_avail = hero["bombs"]
    if bombs_avail <= 0 or any(b["x"] == hero["x"] and b["y"] == hero["y"] for b in memory["tracked_bombs"]):
        return None

    terrain = memory["terrain"]
    occupant = memory["occupant"]
    ever_seen = memory["ever_seen"]
    gf = state["gates_flipped"]
    hx0, hy0 = hero["x"], hero["y"]

    # 从 goals 反向做 0-1/加权 Dijkstra，计算每格到达 goals 所需炸穿的最少墙体层数与步数
    INF = (99, 999999)
    best_w = [[INF] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    pq = []
    for gx, gy in goals:
        best_w[gy][gx] = (0, 0)
        heapq.heappush(pq, (0, 0, gx, gy))

    while pq:
        layers, steps, cx, cy = heapq.heappop(pq)
        if (layers, steps) > best_w[cy][cx]:
            continue
        for dx, dy in DIRECTIONS.values():
            nx, ny = cx + dx, cy + dy
            if not _in_bounds(nx, ny) or _is_outer(nx, ny):
                continue
            if not ever_seen[ny][nx]:
                add_l = 0
                add_s = 2
            else:
                nt = terrain[ny][nx]
                no = occupant[ny][nx]
                if nt in ("T_W", "PIT") or no == "BOX":
                    continue
                if nt in DESTRUCTIBLE_TILES or no == "TNT":
                    if nt == "R_GATE" and gf:
                        add_l, add_s = 0, 1
                    elif nt == "B_GATE" and not gf:
                        add_l, add_s = 0, 1
                    else:
                        add_l, add_s = 1, 4
                else:
                    add_l, add_s = 0, 1
            nl = layers + add_l
            ns = steps + add_s
            if nl <= bombs_avail and (nl, ns) < best_w[ny][nx]:
                best_w[ny][nx] = (nl, ns)
                heapq.heappush(pq, (nl, ns, nx, ny))

    # 在当前可达的已知安全格中，找到紧贴某块“炸开后可使 layers 严格下降且 <= bombs_avail”的爆破站位
    cand_spots = []
    for y in range(1, GRID_HEIGHT - 1):
        for x in range(1, GRID_WIDTH - 1):
            if not ever_seen[y][x]:
                continue
            t = terrain[y][x]
            if _is_high_wall_tile(t, gf) or t in ("PIT", "ICE", *MIRROR_MAP.keys(), *SPRING_DIR.keys()) or occupant[y][x] is not None:
                continue
            best_after = INF
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    wx, wy = x + dx, y + dy
                    if not _in_bounds(wx, wy) or not ever_seen[wy][wx]:
                        continue
                    wt = terrain[wy][wx]
                    wo = occupant[wy][wx]
                    is_closed_wall = (
                        wt in ("W", "LASER_U", "LASER_D", "LASER_L", "LASER_R")
                        or (wt == "R_GATE" and not gf)
                        or (wt == "B_GATE" and gf)
                        or wo == "TNT"
                    )
                    if is_closed_wall:
                        # 炸毁 (wx, wy) 后，剩余层数为 (wx, wy) 邻格中的最优层数 (自身层数已被本次炸弹抵消!)
                        wl, ws = best_w[wy][wx]
                        rem_l = max(0, wl - 1)
                        if rem_l < bombs_avail:
                            cand = (rem_l, ws + _manhattan((hx0, hy0), (x, y)))
                            if cand < best_after:
                                best_after = cand
            if best_after < INF:
                cand_spots.append((best_after, x, y))

    cand_spots.sort()
    for _, bx, by in cand_spots[:6]:
        if time.perf_counter() > deadline:
            break
        if (hx0, hy0) == (bx, by):
            if _can_escape_bomb_now(state, memory, chest_types):
                return "BOMB"
        else:
            nav_act, _, _, _ = _run_temporal_dijkstra(
                state, memory, chest_types, {(bx, by)},
                allow_unknown_walk=False, allow_blind_hazard=False, max_step_dmg=0,
                deadline=deadline,
            )
            if nav_act is not None:
                return nav_act
    return None


def _goal_enclosure_status(memory: dict, gf: bool, goals: set) -> tuple:
    terrain = memory["terrain"]
    ever_seen = memory["ever_seen"]
    occupant = memory["occupant"]
    q = collections.deque(goals)
    visited = set(goals)
    has_gate = False
    has_unk = False
    has_destructible = False

    while q:
        cx, cy = q.popleft()
        if not ever_seen[cy][cx] and (cx, cy) not in goals:
            has_unk = True
        for dx, dy in DIRECTIONS.values():
            nx, ny = cx + dx, cy + dy
            if not _in_bounds(nx, ny) or (nx, ny) in visited:
                continue
            if not ever_seen[ny][nx]:
                visited.add((nx, ny))
                has_unk = True
                q.append((nx, ny))
                continue
            nt = terrain[ny][nx]
            if nt in DESTRUCTIBLE_TILES or occupant[ny][nx] == "TNT":
                has_destructible = True
            if nt in ("R_GATE", "B_GATE"):
                has_gate = True
                if not _is_high_wall_tile(nt, gf):
                    visited.add((nx, ny))
                    q.append((nx, ny))
                continue
            if _is_high_wall_tile(nt, gf) or nt == "PIT" or occupant[ny][nx] in ("BOX", "TNT"):
                continue
            visited.add((nx, ny))
            q.append((nx, ny))

    sealed_small = len(visited) <= 25
    return has_gate, has_unk, has_destructible, sealed_small


def _find_blind_mirror_throw_action(state: dict, memory: dict, chest_types: dict, deadline: float):
    """当门锁阻断且全场可见区域无开关时，尝试向通往未知区域的 MIRROR_* 投石盲狙隐藏开关。"""
    hero = state["hero"]
    if hero["throws"] <= 0:
        return None
    hx, hy = hero["x"], hero["y"]
    gf = state["gates_flipped"]
    terrain = memory["terrain"]
    occupant = memory["occupant"]
    ever_seen = memory["ever_seen"]
    non_standable = {"PIT", "ICE", *MIRROR_MAP.keys(), *SPRING_DIR.keys(), *PORTAL_PAIR_TILE.keys()}

    vantage = {}
    for y in range(1, GRID_HEIGHT - 1):
        for x in range(1, GRID_WIDTH - 1):
            if not ever_seen[y][x] or terrain[y][x] not in MIRROR_MAP:
                continue
            m_tile = terrain[y][x]
            for in_d in ("U", "D", "L", "R"):
                if (x, y, in_d) in memory["tried_mirrors"]:
                    continue
                out_d = MIRROR_MAP[m_tile][in_d]
                odx, ody = DIRECTIONS[out_d]
                # 检查折转方向 1..6 格内是否通向未见区域
                leads_unseen = False
                for k in range(1, 8):
                    kx, ky = x + k * odx, y + k * ody
                    if not _in_bounds(kx, ky):
                        break
                    if not ever_seen[ky][kx]:
                        leads_unseen = True
                        break
                    if _is_high_wall_tile(terrain[ky][kx], gf) or occupant[ky][kx] in ("BOX", "TNT"):
                        break
                if not leads_unseen:
                    continue
                idx, idy = DIRECTIONS[in_d]
                for dist_s in range(1, 6):
                    vx, vy = x - dist_s * idx, y - dist_s * idy
                    if not _in_bounds(vx, vy) or not ever_seen[vy][vx]:
                        break
                    vt = terrain[vy][vx]
                    if _is_high_wall_tile(vt, gf) or occupant[vy][vx] in ("BOX", "TNT"):
                        break
                    if vt not in non_standable:
                        vantage[(vx, vy)] = ("THROW_" + in_d, (x, y, in_d))
    if not vantage:
        return None
    if (hx, hy) in vantage:
        tact, mkey = vantage[(hx, hy)]
        memory["tried_mirrors"].add(mkey)
        return tact
    nav_act, _, _, _ = _run_temporal_dijkstra(
        state, memory, chest_types, set(vantage.keys()),
        allow_unknown_walk=False, allow_blind_hazard=False, max_step_dmg=0,
        deadline=deadline,
    )
    return nav_act


def _find_unseen_portal_action(state: dict, memory: dict, chest_types: dict, deadline: float):
    terrain = memory["terrain"]
    ever_seen = memory["ever_seen"]
    portals = memory["portals"]
    hero = state["hero"]
    hx, hy = hero["x"], hero["y"]

    cand_portals = []
    for p_name, (px, py) in portals.items():
        pair_name = PORTAL_PAIR_TILE[p_name]
        if pair_name not in portals and (px, py) not in memory["tried_portals"]:
            cand_portals.append((px, py))

    for px, py in cand_portals:
        if _manhattan((hx, hy), (px, py)) == 1:
            for dname, (dx, dy) in DIRECTIONS.items():
                if (hx + dx, hy + dy) == (px, py):
                    memory["tried_portals"].add((px, py))
                    return "MOVE_" + dname
        adj = set()
        for dx, dy in DIRECTIONS.values():
            nx, ny = px + dx, py + dy
            if _in_bounds(nx, ny) and ever_seen[ny][nx] and not _is_high_wall_tile(terrain[ny][nx], state["gates_flipped"]) and terrain[ny][nx] != "PIT":
                adj.add((nx, ny))
        if adj:
            nav_act, _, _, _ = _run_temporal_dijkstra(
                state, memory, chest_types, adj,
                allow_unknown_walk=False, allow_blind_hazard=False, max_step_dmg=0,
                deadline=deadline,
            )
            if nav_act is not None:
                return nav_act
    return None


# ==============================================================================
# 参赛入口 2：勇者单步决策函数
# ==============================================================================

def decide_action(state: dict, memory: dict) -> str:
    """
    根据当前回合状态 state 与持久化字典 memory，返回本回合动作字符串。
    单步调用限时：0.5 秒。
    """
    t_start = time.perf_counter()
    deadline = t_start + 0.25

    _update_memory(state, memory)
    chest_types = _classify_chests(memory)
    fg_cache = _build_frontier_gains(memory)

    hero = state["hero"]
    hx, hy = hero["x"], hero["y"]
    hp = hero["hp"]
    has_k1, has_k2 = hero["keys"][0], hero["keys"][1]
    gf = state["gates_flipped"]
    turn = state["turn"]
    turns_left = state["turns_left"]
    targets = state["targets"]

    if has_k1 and has_k2:
        goals = {tuple(targets["V"])}
    elif has_k1:
        goals = {tuple(targets["K2"])}
    elif has_k2:
        goals = {tuple(targets["K1"])}
    else:
        goals = {tuple(targets["K1"]), tuple(targets["K2"])}

    if hp <= 70:
        for pos, ctype in chest_types.items():
            if ctype == "HEAL" and _manhattan((hx, hy), pos) <= 8:
                goals = {pos} | goals

    chosen = None

    # 层级 1: 仅当目标格本身已被观测过时，尝试纯已知安全直达路径
    if not memory["tracked_bombs"] and any(memory["ever_seen"][gy][gx] for gx, gy in goals):
        known_act, _, _, _ = _run_temporal_dijkstra(
            state, memory, chest_types, goals,
            allow_unknown_walk=False, allow_blind_hazard=False, max_step_dmg=0,
            deadline=min(deadline, t_start + 0.08),
        )
        if known_act is not None:
            chosen = known_act

    # 层级 2: 乐观迷雾路径 + 封闭性分析与专项解谜协同
    if chosen is None and time.perf_counter() < deadline:
        g_act, _, f_act, _ = _run_temporal_dijkstra(
            state, memory, chest_types, goals,
            allow_unknown_walk=True, allow_blind_hazard=False, max_step_dmg=0,
            frontier_gain=fg_cache,
            deadline=min(deadline, t_start + 0.16),
        )
        if g_act is not None:
            chosen = g_act
        else:
            if hero["throws"] > 0 and time.perf_counter() < deadline:
                chosen = _find_remote_throw_action(state, memory, chest_types, goals, fg_cache, deadline)
            if chosen is None and time.perf_counter() < deadline:
                chosen = _find_box_puzzle_action(state, memory, chest_types, goals, fg_cache, deadline)

            if chosen is None:
                has_gate, has_unk, has_destr, sealed_small = _goal_enclosure_status(memory, gf, goals)
                if not has_gate and not has_destr and time.perf_counter() < deadline:
                    chosen = _find_unseen_portal_action(state, memory, chest_types, deadline)
                if chosen is None and not has_gate and (not has_unk or (sealed_small and has_destr)) and hero["bombs"] > 0 and time.perf_counter() < deadline:
                    chosen = _find_bomb_breach_action(state, memory, chest_types, goals, deadline)
                if chosen is None and f_act is not None:
                    chosen = f_act

    # 层级 3: 前沿耗尽后的盲狙反射镜、双层炸弹破墙、盲传密室探测与盲弹兜底
    if chosen is None and hero["throws"] > 0 and time.perf_counter() < deadline:
        chosen = _find_blind_mirror_throw_action(state, memory, chest_types, deadline)
    if chosen is None and hero["bombs"] > 0 and time.perf_counter() < deadline:
        chosen = _find_bomb_breach_action(state, memory, chest_types, goals, deadline)
    if chosen is None and time.perf_counter() < deadline:
        chosen = _find_unseen_portal_action(state, memory, chest_types, deadline)
    if chosen is None and time.perf_counter() < deadline:
        b_act, _, bf_act, _ = _run_temporal_dijkstra(
            state, memory, chest_types, goals,
            allow_unknown_walk=True, allow_blind_hazard=True, max_step_dmg=0,
            frontier_gain=fg_cache,
            deadline=deadline,
        )
        chosen = b_act if b_act is not None else bf_act

    # 层级 4: 受控抗伤推进兜底 (血量充裕且无零伤路径时，抗非致命伤通关拿 600+ 高分)
    if chosen is None and hp > 45 and time.perf_counter() < deadline:
        d_act, _, df_act, _ = _run_temporal_dijkstra(
            state, memory, chest_types, goals,
            allow_unknown_walk=True, allow_blind_hazard=True, max_step_dmg=hp - 1,
            frontier_gain=fg_cache,
            deadline=deadline,
        )
        chosen = d_act if d_act is not None else df_act

    # 超视距狙击激光预扫描保护
    if (
        chosen is not None
        and chosen.startswith("MOVE_")
        and turn % 3 == 2
        and turns_left > 45
        and not memory["tracked_bombs"]
    ):
        sr_chk = _sim_single_turn(
            hx, hy, hp, has_k1, has_k2, hero["jumps"], hero["throws"], hero["bombs"],
            gf, turn, chosen, memory["terrain"], memory["occupant"], chest_types,
            memory["portals"], memory["tracked_bombs"], memory, False,
        )
        if sr_chk["status"] == "ALIVE" and not sr_chk["entered_unknown"]:
            nx, ny, ngf = sr_chk["hx"], sr_chk["hy"], sr_chk["gf"]
            if (
                (nx, ny) != (hx, hy)
                and state["visible_mask"][ny][nx]
                and _has_unchecked_sniper_line(memory, nx, ny, ngf)
                and not _has_unchecked_sniper_line(memory, hx, hy, gf)
            ):
                sr_wait = _sim_single_turn(
                    hx, hy, hp, has_k1, has_k2, hero["jumps"], hero["throws"], hero["bombs"],
                    gf, turn, "WAIT", memory["terrain"], memory["occupant"], chest_types,
                    memory["portals"], memory["tracked_bombs"], memory, False,
                )
                if sr_wait["status"] == "ALIVE" and sr_wait["dmg"] == 0 and _has_safe_followup(
                    sr_wait, turn + 1, memory["terrain"], memory["occupant"], chest_types, memory["portals"], memory, 0
                ):
                    chosen = "WAIT"

    # 终极紧急逃生兜底
    if chosen not in VALID_ACTIONS:
        best_emg = "WAIT"
        best_emg_score = (-1, -9999)
        for act in ("WAIT", "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R"):
            if act.startswith("JUMP_") and hero["jumps"] <= 0:
                continue
            sr = _sim_single_turn(
                hx, hy, hp, has_k1, has_k2, hero["jumps"], hero["throws"], hero["bombs"],
                gf, turn, act, memory["terrain"], memory["occupant"], chest_types,
                memory["portals"], memory["tracked_bombs"], memory, False,
            )
            if sr["status"] == "CLEARED":
                best_emg = act
                break
            if sr["status"] == "ALIVE":
                sc = (1 if not sr["entered_unknown"] else 0, -sr["dmg"])
                if sc > best_emg_score:
                    best_emg_score = sc
                    best_emg = act
        chosen = best_emg

    memory["last_pos"] = (hx, hy)
    memory["last_action"] = chosen
    memory["last_bombs_inv"] = hero["bombs"]
    return chosen
