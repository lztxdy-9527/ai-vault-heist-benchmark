"""
《阴间地牢：金库攻防战》下半场 FULL 全图明牌攻守双重构正式答卷 (submission.py)
Model: CARBON (v2.2 Official Specification)
"""

import collections
import heapq
import math
import time

# ==============================================================================
# v2.2 官方常量定义
# ==============================================================================

GRID_WIDTH = 40
GRID_HEIGHT = 26
MAX_BUDGET = 3000
MAX_TURNS = 240
MAX_AUTHOR_STEPS = 200
SPAWN_POS = (2, 13)

VALID_ACTIONS = (
    "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R",
    "WAIT",
    "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
    "THROW_U", "THROW_D", "THROW_L", "THROW_R",
    "BOMB",
)

DIRECTIONS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}

MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}

SPRING_DIR = {
    "SPRING_U": "U", "SPRING_D": "D", "SPRING_L": "L", "SPRING_R": "R",
}

LASER_RED_DIR = {
    "LASER_U": "U", "LASER_D": "D", "LASER_L": "L", "LASER_R": "R",
}

LASER_BLUE_DIR = {
    "LASER2_U": "U", "LASER2_D": "D", "LASER2_L": "L", "LASER2_R": "R",
}

ALL_LASER_DIR = {
    "LASER_U": "U", "LASER_D": "D", "LASER_L": "L", "LASER_R": "R",
    "LASER2_U": "U", "LASER2_D": "D", "LASER2_L": "L", "LASER2_R": "R",
}

ONEWAY_DIR = {
    "ONEWAY_U": "U", "ONEWAY_D": "D", "ONEWAY_L": "L", "ONEWAY_R": "R",
}

PORTAL_PAIR_TILE = {
    "PORTAL_1A": "PORTAL_1B", "PORTAL_1B": "PORTAL_1A",
    "PORTAL_2A": "PORTAL_2B", "PORTAL_2B": "PORTAL_2A",
}

TILE_COSTS = {
    "EMPTY": 0, "K1": 0, "K2": 0, "V": 0,
    "W": 5, "T_W": 25, "ICE": 10,
    "MIRROR_NE": 25, "MIRROR_SE": 25, "MIRROR_SW": 25, "MIRROR_NW": 25,
    "SPRING_U": 35, "SPRING_D": 35, "SPRING_L": 35, "SPRING_R": 35,
    "PIT": 40,
    "LASER_U": 75, "LASER_D": 75, "LASER_L": 75, "LASER_R": 75,
    "LASER2_U": 90, "LASER2_D": 90, "LASER2_L": 90, "LASER2_R": 90,
    "CRACK": 20, "SWITCH": 30, "R_GATE": 20, "B_GATE": 20,
    "PLATE": 45, "P_GATE": 30,
    "ONEWAY_U": 30, "ONEWAY_D": 30, "ONEWAY_L": 30, "ONEWAY_R": 30,
    "TNT": 40, "BOX": 30, "HEAL": 30, "MIMIC": 60,
    "PORTAL_1A": 40, "PORTAL_1B": 40, "PORTAL_2A": 40, "PORTAL_2B": 40,
}

EXPLOSION_IMMUNE = {
    "T_W", "K1", "K2", "V",
    "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
    "PIT", "EMPTY",
    "PLATE", "P_GATE",
    "ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R",
}

DESTRUCTIBLE_WALLS = {
    "W", "R_GATE", "B_GATE",
    "LASER_U", "LASER_D", "LASER_L", "LASER_R",
    "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R",
}

AUTHOR_SOLUTION_V22 = [
    "MOVE_D", "MOVE_L", "MOVE_D", "MOVE_D", "MOVE_R", "MOVE_R", "MOVE_D", "MOVE_U",
    "MOVE_L", "MOVE_L", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U",
    "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_R", "MOVE_R", "MOVE_D", "MOVE_U", "MOVE_L", "MOVE_L", "MOVE_D", "MOVE_D",
    "MOVE_D", "MOVE_D", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L",
    "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L",
    "MOVE_L", "MOVE_L", "MOVE_D", "MOVE_D", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_D", "MOVE_D", "JUMP_D", "MOVE_D", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L",
    "MOVE_L", "MOVE_L", "MOVE_U", "JUMP_U", "MOVE_U", "MOVE_U", "MOVE_L", "MOVE_L",
    "MOVE_L", "MOVE_L", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U",
    "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_R", "MOVE_R", "MOVE_R", "THROW_U", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_D",
    "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_D", "MOVE_L",
    "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_L", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U",
    "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_U", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_R", "MOVE_U", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
    "MOVE_R", "MOVE_R", "MOVE_R", "WAIT", "MOVE_R", "JUMP_U", "MOVE_R", "MOVE_R",
    "MOVE_R", "MOVE_R", "MOVE_R", "WAIT", "WAIT", "WAIT", "WAIT", "WAIT", "WAIT",
    "MOVE_R", "MOVE_R", "MOVE_R", "MOVE_R",
]


def _in_bounds(x: int, y: int) -> bool:
    return 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT


def _is_outer(x: int, y: int) -> bool:
    return x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1


def _manhattan(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ==============================================================================
# 参赛入口 1：v2.2 魔王造图与自证函数
# ==============================================================================

def build_dungeon() -> dict:
    """
    v2.2 明牌反制逻辑迷宫：
    1) 伪压板死锁悖论 (False-Plate Paradox): B1(5,17) 向右 1 步弹上 PLATE #1(9,17) 即锁死西南双深渊钥匙井 K2；
       唯有让 B1 南下冰槽填平深渊 (5,20)，再以飞石隔单向门+折跃镜+冰轨远程打开关释放 B3 压住 PLATE #1 方可破局。
    2) 东北捕蝇草单向门 + 12 拍红蓝双频激光走廊 (ONEWAY_R + LASER_R + LASER2_U + ICE->P_GATE)。
    3) 东翼双频交叉激光 + 红门 + 金色压板门终极金库。
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

    # 1. 西南双箱封锁盆地 (勇者经 (1,15)->(1,16)->(2,16) 自由出入，外箱受 x=0 外墙阻挡无法内推)
    hline(15, 2, 11, "T_W")
    vline(11, 16, 21, "T_W")

    g[17][5] = "BOX"
    g[17][6] = "SPRING_R"
    g[17][8] = "ONEWAY_R"
    g[16][8] = "T_W"
    g[18][8] = "T_W"
    g[16][9] = "T_W"
    g[18][9] = "T_W"
    g[16][10] = "T_W"
    g[18][10] = "T_W"
    g[17][9] = "PLATE"
    g[17][10] = "ONEWAY_L"
    g[17][11] = "R_GATE"

    g[18][5] = "ICE"
    g[19][5] = "ICE"
    vline(4, 20, 24, "T_W")
    vline(6, 20, 22, "T_W")
    hline(22, 6, 13, "T_W")
    vline(13, 22, 24, "T_W")
    g[20][5] = "PIT"
    g[21][5] = "PIT"
    g[23][12] = "K2"

    g[17][1] = "T_W"
    g[17][2] = "W"
    g[17][4] = "W"
    g[18][2] = "W"
    g[18][4] = "W"
    g[19][3] = "W"
    g[17][3] = "BOX"
    g[18][3] = "PLATE"

    # 2. 中场隔单向门+折跃镜+冰滑远程飞石开关靶室 + B3 & B4/PLATE #3
    hline(1, 15, 20, "W")
    hline(3, 17, 20, "W")
    g[2][15] = "W"
    g[2][16] = "MIRROR_NE"
    g[3][16] = "PIT"
    g[4][16] = "ONEWAY_D"
    g[3][15] = "W"
    g[4][15] = "W"
    g[4][17] = "W"
    g[2][18] = "ICE"
    g[2][19] = "ICE"
    g[2][20] = "SWITCH"
    g[2][21] = "W"

    g[16][12] = "W"
    g[18][12] = "W"
    g[17][12] = "BOX"

    g[11][18] = "W"
    g[11][20] = "W"
    g[12][18] = "W"
    g[12][20] = "W"
    g[13][19] = "W"
    g[11][19] = "BOX"
    g[12][19] = "PLATE"
    # 诱饵游离双箱 B5, B6 (使未做二分图死锁剪枝的对手在误触 PLATE #1 后陷入数万状态的推箱泥潭)
    g[7][22] = "BOX"
    g[7][24] = "BOX"

    # 3. 东北单向捕蝇草与 12 拍双频激光要塞 -> K1(33, 2) -> PORTAL_1A(34, 2)
    hline(3, 22, 35, "W")
    g[2][21] = "LASER_R"
    g[1][22] = "EMPTY"
    g[1][23] = "ONEWAY_R"
    g[1][24] = "EMPTY"
    g[1][25] = "W"
    g[1][26] = "EMPTY"
    g[1][27] = "EMPTY"
    for xx in range(28, 35):
        g[1][xx] = "W"
    g[1][31] = "T_W"
    g[3][32] = "T_W"
    g[3][33] = "T_W"
    g[3][34] = "T_W"
    g[2][35] = "T_W"
    g[1][35] = "W"

    g[12][28] = "LASER2_U"
    g[3][28] = "PIT"

    g[2][24] = "MIRROR_NE"
    g[2][25] = "ICE"
    for xx in range(28, 32):
        g[2][xx] = "ICE"
    g[2][32] = "P_GATE"
    g[2][33] = "K1"
    g[2][34] = "PORTAL_1A"

    g[12][30] = "W"
    g[14][30] = "W"
    g[13][29] = "W"
    g[13][30] = "PORTAL_1B"
    g[13][31] = "ONEWAY_R"

    # 4. 东翼 12 拍双频交叉金库圣殿 -> V(37, 13)
    hline(12, 31, 38, "W")
    hline(14, 31, 38, "W")
    g[12][36] = "T_W"
    g[12][37] = "T_W"
    g[14][36] = "T_W"
    g[14][37] = "T_W"
    g[13][38] = "T_W"

    g[12][34] = "PIT"
    g[14][34] = "PIT"
    g[7][34] = "LASER_D"
    g[19][34] = "LASER2_U"

    g[13][35] = "R_GATE"
    g[13][36] = "P_GATE"
    g[13][37] = "V"

    return {
        "taunt": "假板一步锁死局，十二拍里辨真章！",
        "grid": g,
        "author_solution": list(AUTHOR_SOLUTION_V22),
    }


# ==============================================================================
# 纯字典无反射确定性物理引擎 (100% 对齐 RULES_FULL_v22.md，零双下划线调用)
# ==============================================================================

def _eng_plates_active(eng: dict) -> bool:
    plates = eng["plates"]
    if not plates:
        return False
    occ = eng["occupant"]
    for px, py in plates:
        if occ[py][px] != "BOX":
            return False
    return True


def _eng_is_high_wall(eng: dict, x: int, y: int) -> bool:
    if not _in_bounds(x, y):
        return True
    t = eng["terrain"][y][x]
    if t in ("W", "T_W") or t in ALL_LASER_DIR:
        return True
    if t == "R_GATE" and not eng["gates_flipped"]:
        return True
    if t == "B_GATE" and eng["gates_flipped"]:
        return True
    if t == "P_GATE" and not _eng_plates_active(eng):
        return True
    return False


def _eng_blocks_oneway(eng: dict, x: int, y: int, dname: str) -> bool:
    if not _in_bounds(x, y):
        return False
    t = eng["terrain"][y][x]
    if t in ONEWAY_DIR:
        return ONEWAY_DIR[t] != dname
    return False


def _eng_can_hero_enter(eng: dict, x: int, y: int, dname: str) -> bool:
    if _eng_is_high_wall(eng, x, y) or _eng_blocks_oneway(eng, x, y, dname):
        return False
    if eng["occupant"][y][x] in ("BOX", "TNT"):
        return False
    return True


def _eng_can_box_enter(eng: dict, x: int, y: int, dname: str) -> bool:
    if _eng_is_high_wall(eng, x, y) or _eng_blocks_oneway(eng, x, y, dname):
        return False
    if eng["occupant"][y][x] is not None:
        return False
    if (x, y) == (eng["hx"], eng["hy"]):
        return False
    if eng["terrain"][y][x] in ("K1", "K2", "V"):
        return False
    return True


def _clone_eng(eng: dict) -> dict:
    return {
        "terrain": [r[:] for r in eng["terrain"]],
        "occupant": [r[:] for r in eng["occupant"]],
        "portals": eng["portals"],
        "plates": eng["plates"],
        "targets": eng["targets"],
        "hx": eng["hx"],
        "hy": eng["hy"],
        "hp": eng["hp"],
        "has_k1": eng["has_k1"],
        "has_k2": eng["has_k2"],
        "jumps": eng["jumps"],
        "throws": eng["throws"],
        "bombs_inv": eng["bombs_inv"],
        "gates_flipped": eng["gates_flipped"],
        "bombs": [dict(b) for b in eng["bombs"]],
        "next_bomb_id": eng["next_bomb_id"],
        "turn": eng["turn"],
        "status": eng["status"],
    }


def _decode_state_to_eng(state: dict) -> dict:
    obs_t = state["terrain"]
    obs_o = state["occupant"]
    obs_c = state["clues"]

    terrain = [["EMPTY"] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    occupant = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    portals = {}
    plates = []

    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            occupant[y][x] = obs_o[y][x]
            t = obs_t[y][x]
            if t == "CHEST":
                is_m = False
                for dname in ("U", "D", "L", "R"):
                    nx, ny = x + DIRECTIONS[dname][0], y + DIRECTIONS[dname][1]
                    if _in_bounds(nx, ny) and obs_c[ny][nx]:
                        is_m = True
                        break
                terrain[y][x] = "MIMIC" if is_m else "HEAL"
            else:
                terrain[y][x] = t
                if t in PORTAL_PAIR_TILE:
                    portals[t] = (x, y)
                elif t == "PLATE":
                    plates.append((x, y))

    h = state["hero"]
    bombs = [
        {"id": idx + 1, "x": b["x"], "y": b["y"], "timer": b["timer"]}
        for idx, b in enumerate(state["bombs"])
    ]
    return {
        "terrain": terrain,
        "occupant": occupant,
        "portals": portals,
        "plates": tuple(plates),
        "targets": state["targets"],
        "hx": h["x"],
        "hy": h["y"],
        "hp": h["hp"],
        "has_k1": h["keys"][0],
        "has_k2": h["keys"][1],
        "jumps": h["jumps"],
        "throws": h["throws"],
        "bombs_inv": h["bombs"],
        "gates_flipped": state["gates_flipped"],
        "bombs": bombs,
        "next_bomb_id": len(bombs) + 1,
        "turn": state["turn"] - 1,
        "status": "ALIVE",
    }


def _eng_displace(eng: dict, entity: str, p0, p1, dname: str, ctx: dict, suppress_portal_once: bool = False) -> None:
    ctx["steps_taken"] += 1
    x0, y0 = p0
    x1, y1 = p1
    terrain = eng["terrain"]
    occupant = eng["occupant"]

    if terrain[y0][x0] == "CRACK":
        terrain[y0][x0] = "PIT"

    if entity == "BOX":
        occupant[y0][x0] = None
        occupant[y1][x1] = "BOX"
    else:
        eng["hx"], eng["hy"] = x1, y1
        ctx["exposed"].add((x1, y1))

    t1 = terrain[y1][x1]
    stop_momentum = False
    if entity == "BOX":
        if t1 == "PIT":
            occupant[y1][x1] = None
            terrain[y1][x1] = "EMPTY"
            return
        elif t1 == "MIMIC":
            terrain[y1][x1] = "EMPTY"
        elif t1 == "SWITCH":
            eng["gates_flipped"] = not eng["gates_flipped"]
    else:
        if t1 == "PIT":
            eng["hp"] -= 100
        elif t1 == "MIMIC":
            eng["hp"] -= 45
            terrain[y1][x1] = "EMPTY"
            stop_momentum = True
        elif t1 == "HEAL":
            eng["hp"] = min(100, eng["hp"] + 30)
            terrain[y1][x1] = "EMPTY"
        elif t1 == "SWITCH":
            eng["gates_flipped"] = not eng["gates_flipped"]

    if entity == "HERO" and eng["hp"] <= 0:
        eng["status"] = "DEAD"
        return

    if entity == "HERO":
        ct = terrain[y1][x1]
        if ct == "K1":
            eng["has_k1"] = True
            terrain[y1][x1] = "EMPTY"
        elif ct == "K2":
            eng["has_k2"] = True
            terrain[y1][x1] = "EMPTY"
        elif ct == "V" and eng["has_k1"] and eng["has_k2"] and eng["hp"] > 0:
            eng["status"] = "CLEARED"
            return

    if ctx["steps_taken"] >= 32 or stop_momentum:
        return

    ct = terrain[y1][x1]
    can_enter = _eng_can_hero_enter if entity == "HERO" else _eng_can_box_enter

    if suppress_portal_once:
        if ctx["portal_count"] >= 2:
            return
        dx, dy = DIRECTIONS[dname]
        nx, ny = x1 + dx, y1 + dy
        if can_enter(eng, nx, ny, dname):
            _eng_displace(eng, entity, (x1, y1), (nx, ny), dname, ctx, False)
        return

    if ct == "ICE":
        dx, dy = DIRECTIONS[dname]
        nx, ny = x1 + dx, y1 + dy
        if can_enter(eng, nx, ny, dname):
            _eng_displace(eng, entity, (x1, y1), (nx, ny), dname, ctx, False)
    elif ct in MIRROR_MAP:
        ndir = MIRROR_MAP[ct][dname]
        dx, dy = DIRECTIONS[ndir]
        nx, ny = x1 + dx, y1 + dy
        if can_enter(eng, nx, ny, ndir):
            _eng_displace(eng, entity, (x1, y1), (nx, ny), ndir, ctx, False)
    elif ct in SPRING_DIR:
        sdir = SPRING_DIR[ct]
        dx, dy = DIRECTIONS[sdir]
        blocked_k = None
        for k in (1, 2, 3):
            kx, ky = x1 + k * dx, y1 + k * dy
            is_blk = False
            if not _in_bounds(kx, ky) or _eng_is_high_wall(eng, kx, ky) or _eng_blocks_oneway(eng, kx, ky, sdir):
                is_blk = True
            elif occupant[ky][kx] in ("BOX", "TNT"):
                is_blk = True
            elif entity == "BOX" and ((kx, ky) == (eng["hx"], eng["hy"]) or terrain[ky][kx] in ("K1", "K2", "V")):
                is_blk = True
            if is_blk:
                blocked_k = k
                if entity == "BOX" and _in_bounds(kx, ky) and occupant[ky][kx] == "TNT":
                    ctx["tnt_armed"].add((kx, ky))
                break
        if blocked_k == 1:
            return
        tk = (blocked_k - 1) if blocked_k in (2, 3) else 3
        _eng_displace(eng, entity, (x1, y1), (x1 + tk * dx, y1 + tk * dy), sdir, ctx, False)
    elif ct in PORTAL_PAIR_TILE:
        p_pair = eng["portals"].get(PORTAL_PAIR_TILE[ct])
        if p_pair is None:
            return
        px, py = p_pair
        if occupant[py][px] is not None:
            return
        if entity == "BOX" and (px, py) == (eng["hx"], eng["hy"]):
            return
        ctx["portal_count"] += 1
        _eng_displace(eng, entity, (x1, y1), (px, py), dname, ctx, True)


def _eng_resolve_explosions(eng: dict, initial_bombs: list, initial_tnts: set) -> None:
    if not initial_bombs and not initial_tnts:
        return
    terrain = eng["terrain"]
    occupant = eng["occupant"]
    exploded_bomb_ids = set()
    exploded_tnts = set()
    q = collections.deque()

    for b in initial_bombs:
        if b["id"] not in exploded_bomb_ids:
            exploded_bomb_ids.add(b["id"])
            q.append(("BOMB", b["x"], b["y"]))
    for tx, ty in initial_tnts:
        if (tx, ty) not in exploded_tnts and occupant[ty][tx] == "TNT":
            exploded_tnts.add((tx, ty))
            q.append(("TNT", tx, ty))

    bomb_by_pos = collections.defaultdict(list)
    for b in eng["bombs"]:
        bomb_by_pos[(b["x"], b["y"])].append(b)

    sources = []
    affected = set()
    while q:
        st, ex, ey = q.popleft()
        sources.append((st, ex, ey))
        for ny in range(max(0, ey - 1), min(GRID_HEIGHT, ey + 2)):
            for nx in range(max(0, ex - 1), min(GRID_WIDTH, ex + 2)):
                affected.add((nx, ny))
                if occupant[ny][nx] == "TNT" and (nx, ny) not in exploded_tnts:
                    exploded_tnts.add((nx, ny))
                    q.append(("TNT", nx, ny))
                for b in bomb_by_pos.get((nx, ny), ()):
                    if b["id"] not in exploded_bomb_ids:
                        exploded_bomb_ids.add(b["id"])
                        q.append(("BOMB", b["x"], b["y"]))

    tot_dmg = 0
    hx, hy = eng["hx"], eng["hy"]
    for st, ex, ey in sources:
        if abs(hx - ex) <= 1 and abs(hy - ey) <= 1:
            tot_dmg += (60 if st == "TNT" else 50)
    if tot_dmg > 0:
        eng["hp"] -= tot_dmg

    eng["bombs"] = [b for b in eng["bombs"] if b["id"] not in exploded_bomb_ids]
    for tx, ty in exploded_tnts:
        if occupant[ty][tx] == "TNT":
            occupant[ty][tx] = None

    for cx, cy in affected:
        if occupant[cy][cx] == "BOX":
            occupant[cy][cx] = None
        t = terrain[cy][cx]
        if t in EXPLOSION_IMMUNE:
            pass
        elif t == "CRACK":
            terrain[cy][cx] = "PIT"
        else:
            terrain[cy][cx] = "EMPTY"

    for cy in range(1, GRID_HEIGHT - 1):
        for cx in range(1, GRID_WIDTH - 1):
            if occupant[cy][cx] == "BOX" and terrain[cy][cx] == "PIT":
                occupant[cy][cx] = None
                terrain[cy][cx] = "EMPTY"

    if eng["hp"] > 0 and terrain[eng["hy"]][eng["hx"]] == "PIT":
        eng["hp"] -= 100

    if eng["hp"] <= 0:
        eng["status"] = "DEAD"


def _eng_step(eng: dict, action: str) -> None:
    if eng["status"] != "ALIVE":
        return
    if action not in VALID_ACTIONS:
        action = "WAIT"

    eng["turn"] += 1
    turn = eng["turn"]
    terrain = eng["terrain"]
    occupant = eng["occupant"]
    exposed = {(eng["hx"], eng["hy"])}
    tnt_armed = set()

    if action == "WAIT":
        pass
    elif action == "BOMB":
        if eng["bombs_inv"] > 0 and not any(b["x"] == eng["hx"] and b["y"] == eng["hy"] for b in eng["bombs"]):
            eng["bombs_inv"] -= 1
            eng["bombs"].append({"id": eng["next_bomb_id"], "x": eng["hx"], "y": eng["hy"], "timer": 3})
            eng["next_bomb_id"] += 1
    elif action.startswith("MOVE_"):
        dname = action[5:]
        dx, dy = DIRECTIONS[dname]
        p1x, p1y = eng["hx"] + dx, eng["hy"] + dy
        if not _eng_is_high_wall(eng, p1x, p1y) and not _eng_blocks_oneway(eng, p1x, p1y, dname) and occupant[p1y][p1x] != "TNT":
            if occupant[p1y][p1x] == "BOX":
                p2x, p2y = eng["hx"] + 2 * dx, eng["hy"] + 2 * dy
                if _eng_can_box_enter(eng, p2x, p2y, dname):
                    bctx = {"steps_taken": 0, "portal_count": 0, "tnt_armed": tnt_armed, "exposed": exposed}
                    _eng_displace(eng, "BOX", (p1x, p1y), (p2x, p2y), dname, bctx, False)
                    if eng["status"] == "ALIVE" and _eng_can_hero_enter(eng, p1x, p1y, dname):
                        hctx = {"steps_taken": 0, "portal_count": 0, "tnt_armed": tnt_armed, "exposed": exposed}
                        _eng_displace(eng, "HERO", (eng["hx"], eng["hy"]), (p1x, p1y), dname, hctx, False)
            else:
                hctx = {"steps_taken": 0, "portal_count": 0, "tnt_armed": tnt_armed, "exposed": exposed}
                _eng_displace(eng, "HERO", (eng["hx"], eng["hy"]), (p1x, p1y), dname, hctx, False)
    elif action.startswith("JUMP_"):
        if eng["jumps"] > 0:
            eng["jumps"] -= 1
            dname = action[5:]
            dx, dy = DIRECTIONS[dname]
            p1x, p1y = eng["hx"] + dx, eng["hy"] + dy
            p2x, p2y = eng["hx"] + 2 * dx, eng["hy"] + 2 * dy
            if (
                not _eng_is_high_wall(eng, p1x, p1y)
                and not _eng_blocks_oneway(eng, p1x, p1y, dname)
                and _in_bounds(p2x, p2y)
                and _eng_can_hero_enter(eng, p2x, p2y, dname)
            ):
                hctx = {"steps_taken": 0, "portal_count": 0, "tnt_armed": tnt_armed, "exposed": exposed}
                _eng_displace(eng, "HERO", (eng["hx"], eng["hy"]), (p2x, p2y), dname, hctx, False)
    elif action.startswith("THROW_"):
        if eng["throws"] > 0:
            eng["throws"] -= 1
            dname = action[6:]
            sx, sy = eng["hx"], eng["hy"]
            rleft = 6
            sp = 0
            shattered = False
            while rleft > 0:
                dx, dy = DIRECTIONS[dname]
                sx, sy = sx + dx, sy + dy
                rleft -= 1
                if not _in_bounds(sx, sy) or _eng_is_high_wall(eng, sx, sy) or occupant[sy][sx] == "BOX":
                    shattered = True
                    break
                if occupant[sy][sx] == "TNT":
                    tnt_armed.add((sx, sy))
                    shattered = True
                    break
                t = terrain[sy][sx]
                if t == "SWITCH":
                    eng["gates_flipped"] = not eng["gates_flipped"]
                    shattered = True
                    break
                if t == "MIMIC":
                    terrain[sy][sx] = "EMPTY"
                    shattered = True
                    break
                if t in MIRROR_MAP:
                    dname = MIRROR_MAP[t][dname]
                elif t in PORTAL_PAIR_TILE and sp < 2:
                    pp = eng["portals"].get(PORTAL_PAIR_TILE[t])
                    if pp is not None and occupant[pp[1]][pp[0]] not in ("BOX", "TNT"):
                        sx, sy = pp
                        sp += 1
                        if sp == 2:
                            shattered = True
                            break
            if not shattered and rleft == 0 and terrain[sy][sx] in ("ICE", *MIRROR_MAP.keys()):
                for _ in range(32):
                    dx, dy = DIRECTIONS[dname]
                    sx, sy = sx + dx, sy + dy
                    if not _in_bounds(sx, sy) or _eng_is_high_wall(eng, sx, sy) or occupant[sy][sx] == "BOX":
                        break
                    if occupant[sy][sx] == "TNT":
                        tnt_armed.add((sx, sy))
                        break
                    t = terrain[sy][sx]
                    if t == "SWITCH":
                        eng["gates_flipped"] = not eng["gates_flipped"]
                        break
                    if t == "MIMIC":
                        terrain[sy][sx] = "EMPTY"
                        break
                    if t in MIRROR_MAP:
                        dname = MIRROR_MAP[t][dname]
                    elif t == "ICE":
                        continue
                    elif t in PORTAL_PAIR_TILE and sp < 2:
                        pp = eng["portals"].get(PORTAL_PAIR_TILE[t])
                        if pp is not None and occupant[pp[1]][pp[0]] not in ("BOX", "TNT"):
                            sx, sy = pp
                            sp += 1
                            if sp == 2:
                                break
                        else:
                            break
                    else:
                        break

    if eng["status"] in ("DEAD", "CLEARED"):
        return

    for b in eng["bombs"]:
        b["timer"] -= 1
    due_bombs = [b for b in eng["bombs"] if b["timer"] == 0]
    if due_bombs or tnt_armed:
        _eng_resolve_explosions(eng, due_bombs, tnt_armed)
        if eng["status"] == "DEAD":
            return

    if turn % 3 == 0 or turn % 4 == 0:
        fire_red = (turn % 3 == 0)
        fire_blue = (turn % 4 == 0)
        m = 0
        laser_tnt_armed = set()
        for y in range(1, GRID_HEIGHT - 1):
            trow = terrain[y]
            for x in range(1, GRID_WIDTH - 1):
                t = trow[x]
                dname = None
                if fire_red and t in LASER_RED_DIR:
                    dname = LASER_RED_DIR[t]
                elif fire_blue and t in LASER_BLUE_DIR:
                    dname = LASER_BLUE_DIR[t]
                if dname is not None:
                    dx, dy = DIRECTIONS[dname]
                    hit_hero = False
                    for dist in range(1, 11):
                        nx, ny = x + dist * dx, y + dist * dy
                        if not _in_bounds(nx, ny) or _eng_is_high_wall(eng, nx, ny) or occupant[ny][nx] == "BOX":
                            break
                        if occupant[ny][nx] == "TNT":
                            laser_tnt_armed.add((nx, ny))
                            break
                        if (nx, ny) in exposed:
                            hit_hero = True
                    if hit_hero:
                        m += 1
        if m > 0:
            eng["hp"] -= 50 * m
            if eng["hp"] <= 0:
                eng["status"] = "DEAD"
                return
        if laser_tnt_armed:
            _eng_resolve_explosions(eng, [], laser_tnt_armed)
            if eng["status"] == "DEAD":
                return

    if turn >= MAX_TURNS and eng["status"] == "ALIVE":
        eng["status"] = "TIMEOUT"


# ==============================================================================
# 参赛入口 2：v2.2 FULL 明牌全局宏动作搜索引擎 + 二分图死锁剪枝 + 在线续算
# ==============================================================================

def _compute_laser_info(eng: dict):
    red_mask = [[0] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    blue_mask = [[0] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    has_red = False
    has_blue = False
    cid = 0
    terrain = eng["terrain"]
    occupant = eng["occupant"]

    for y in range(1, GRID_HEIGHT - 1):
        trow = terrain[y]
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
                if not _in_bounds(nx, ny) or _eng_is_high_wall(eng, nx, ny) or occupant[ny][nx] in ("BOX", "TNT"):
                    break
                g_out[ny][nx] |= bit

    period = 12 if (has_red and has_blue) else (4 if has_blue else (3 if has_red else 1))
    near_laser = [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    if period > 1:
        for y in range(1, GRID_HEIGHT - 1):
            for x in range(1, GRID_WIDTH - 1):
                if red_mask[y][x] or blue_mask[y][x]:
                    near_laser[y][x] = True
                    for dx, dy in DIRECTIONS.values():
                        nx, ny = x + dx, y + dy
                        if _in_bounds(nx, ny):
                            near_laser[ny][nx] = True
        for _ in range(4):
            for y in range(1, GRID_HEIGHT - 1):
                for x in range(1, GRID_WIDTH - 1):
                    if not near_laser[y][x] and terrain[y][x] in ("ICE", *MIRROR_MAP.keys(), *SPRING_DIR.keys(), *PORTAL_PAIR_TILE.keys()):
                        for dx, dy in DIRECTIONS.values():
                            if _in_bounds(x + dx, y + dy) and near_laser[y + dy][x + dx]:
                                near_laser[y][x] = True
                                break
        for y in range(1, GRID_HEIGHT - 1):
            for x in range(1, GRID_WIDTH - 1):
                if near_laser[y][x] and terrain[y][x] in ("ICE", *MIRROR_MAP.keys(), *SPRING_DIR.keys(), *PORTAL_PAIR_TILE.keys()):
                    for dx, dy in DIRECTIONS.values():
                        if _in_bounds(x + dx, y + dy):
                            near_laser[y + dy][x + dx] = True

    return red_mask, blue_mask, period, near_laser


def _fast_hero_nav(eng: dict, allow_damage: bool = False):
    red_mask, blue_mask, period, near_laser = _compute_laser_info(eng)
    plates_on = _eng_plates_active(eng)
    gf = eng["gates_flipped"]
    terrain = eng["terrain"]
    occupant = eng["occupant"]
    portals = eng["portals"]
    has_both_keys = eng["has_k1"] and eng["has_k2"]
    active_bombs = eng["bombs"]
    has_bombs = bool(active_bombs)
    t0_eng = eng["turn"]

    def is_hw(x, y):
        if not _in_bounds(x, y):
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
            return (x, y, t % period if period > 1 else (t - t0_eng))
        return (x, y, -1)

    start_skey = make_skey(eng["hx"], eng["hy"], t0_eng)
    best_cost = {start_skey: 0.0}
    parents = [None]
    node_meta = [(0.0, t0_eng, eng["hx"], eng["hy"], eng["hp"], eng["jumps"])]
    best_at_cell = {(eng["hx"], eng["hy"]): (0.0, 0, eng["jumps"])}

    pq = [(0.0, 0, frozenset())]
    special_hits = {}

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
                    if not _in_bounds(tx, ty) or is_hw(p1x, p1y) or blk_ow(p1x, p1y, dname):
                        continue
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
                    elif ct == "K1" and not eng["has_k1"]:
                        special_event = ("K1", cx1, cy1)
                    elif ct == "K2" and not eng["has_k2"]:
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
                            if not _in_bounds(kx, ky) or is_hw(kx, ky) or blk_ow(kx, ky, cd) or occupant[ky][kx] in ("BOX", "TNT"):
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
                dt_b = nturn - t0_eng
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
                dominated_ev = False
                for hj in range(nj, eng["jumps"] + 1):
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


def _trace_stone_from(eng: dict, vx: int, vy: int, dname: str):
    sx, sy = vx, vy
    rleft = 6
    sp = 0
    terrain = eng["terrain"]
    occupant = eng["occupant"]
    portals = eng["portals"]

    while rleft > 0:
        dx, dy = DIRECTIONS[dname]
        sx, sy = sx + dx, sy + dy
        rleft -= 1
        if not _in_bounds(sx, sy) or _eng_is_high_wall(eng, sx, sy) or occupant[sy][sx] == "BOX":
            return None
        if occupant[sy][sx] == "TNT":
            return ("TNT", sx, sy)
        t = terrain[sy][sx]
        if t == "SWITCH":
            return ("SWITCH", sx, sy)
        if t == "MIMIC":
            return ("MIMIC", sx, sy)
        if t in MIRROR_MAP:
            dname = MIRROR_MAP[t][dname]
        elif t in PORTAL_PAIR_TILE and sp < 2:
            pp = portals.get(PORTAL_PAIR_TILE[t])
            if pp is not None and occupant[pp[1]][pp[0]] not in ("BOX", "TNT"):
                sx, sy = pp
                sp += 1
                if sp == 2:
                    return None
    if terrain[sy][sx] in ("ICE", *MIRROR_MAP.keys()):
        for _ in range(32):
            dx, dy = DIRECTIONS[dname]
            sx, sy = sx + dx, sy + dy
            if not _in_bounds(sx, sy) or _eng_is_high_wall(eng, sx, sy) or occupant[sy][sx] == "BOX":
                return None
            if occupant[sy][sx] == "TNT":
                return ("TNT", sx, sy)
            t = terrain[sy][sx]
            if t == "SWITCH":
                return ("SWITCH", sx, sy)
            if t == "MIMIC":
                return ("MIMIC", sx, sy)
            if t in MIRROR_MAP:
                dname = MIRROR_MAP[t][dname]
            elif t == "ICE":
                continue
            elif t in PORTAL_PAIR_TILE and sp < 2:
                pp = portals.get(PORTAL_PAIR_TILE[t])
                if pp is not None and occupant[pp[1]][pp[0]] not in ("BOX", "TNT"):
                    sx, sy = pp
                    sp += 1
                    if sp == 2:
                        return None
                else:
                    return None
            else:
                return None
    return None


def _canonical_hero_anchor(eng: dict):
    plates_on = _eng_plates_active(eng)
    gf = eng["gates_flipped"]
    terrain = eng["terrain"]
    occupant = eng["occupant"]
    sx, sy = eng["hx"], eng["hy"]
    best = (sx, sy)
    vis = {(sx, sy)}
    q = collections.deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        if (x, y) < best:
            best = (x, y)
        for dx, dy in DIRECTIONS.values():
            nx, ny = x + dx, y + dy
            if (nx, ny) in vis or not _in_bounds(nx, ny):
                continue
            t = terrain[ny][nx]
            if t not in ("EMPTY", "PLATE") and not (t == "R_GATE" and gf) and not (t == "B_GATE" and not gf) and not (t == "P_GATE" and plates_on):
                continue
            if occupant[ny][nx] is not None:
                continue
            vis.add((nx, ny))
            q.append((nx, ny))
    return best


def _world_signature(eng: dict):
    boxes = []
    tnts = []
    cracks_cnt = 0
    walls_hash = 0
    terrain = eng["terrain"]
    occupant = eng["occupant"]
    for y in range(1, GRID_HEIGHT - 1):
        trow = terrain[y]
        orow = occupant[y]
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
    anchor = _canonical_hero_anchor(eng)
    return (
        anchor[0], anchor[1],
        eng["has_k1"], eng["has_k2"], eng["gates_flipped"],
        eng["jumps"], eng["throws"], eng["bombs_inv"],
        tuple(boxes), tuple(tnts), cracks_cnt, walls_hash,
    )


def _is_cell_permanently_box_locked(eng: dict, bx: int, by: int) -> bool:
    terrain = eng["terrain"]

    def perm_blk(tx, ty, push_dir, stand_x, stand_y):
        if not _in_bounds(tx, ty) or not _in_bounds(stand_x, stand_y):
            return True
        if terrain[ty][tx] in ("T_W", "K1", "K2", "V") or _eng_blocks_oneway(eng, tx, ty, push_dir):
            return True
        if terrain[stand_y][stand_x] == "T_W" or _eng_blocks_oneway(eng, bx, by, push_dir):
            return True
        return False

    h_blk = perm_blk(bx + 1, by, "R", bx - 1, by) and perm_blk(bx - 1, by, "L", bx + 1, by)
    v_blk = perm_blk(bx, by + 1, "D", bx, by - 1) and perm_blk(bx, by - 1, "U", bx, by + 1)
    return h_blk and v_blk


def _is_box_static_corner_deadlock(eng: dict, bx: int, by: int) -> bool:
    terrain = eng["terrain"]
    if terrain[by][bx] == "PLATE":
        return False
    for dname, (dx, dy) in DIRECTIONS.items():
        for dist in range(1, 11):
            nx, ny = bx - dist * dx, by - dist * dy
            if not _in_bounds(nx, ny):
                break
            t = terrain[ny][nx]
            if t in ALL_LASER_DIR and ALL_LASER_DIR[t] == dname:
                return False
            if t == "T_W":
                break
    return _is_cell_permanently_box_locked(eng, bx, by)


def _compute_box_push_reach(eng: dict, bx0: int, by0: int) -> set:
    terrain = eng["terrain"]
    portals = eng["portals"]
    vis = {(bx0, by0)}
    q = collections.deque([(bx0, by0)])

    while q:
        x, y = q.popleft()
        if terrain[y][x] == "PIT":
            continue
        for dname, (dx, dy) in DIRECTIONS.items():
            sx, sy = x - dx, y - dy
            nx, ny = x + dx, y + dy
            if not _in_bounds(sx, sy) or not _in_bounds(nx, ny):
                continue
            if terrain[sy][sx] == "T_W":
                continue
            if terrain[ny][nx] in ("T_W", "K1", "K2", "V") or _eng_blocks_oneway(eng, nx, ny, dname):
                continue

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
                    if not _in_bounds(nnx, nny) or terrain[nny][nnx] in ("T_W", "K1", "K2", "V") or _eng_blocks_oneway(eng, nnx, nny, cd):
                        break
                    cx, cy = nnx, nny
                elif ct in MIRROR_MAP:
                    cd = MIRROR_MAP[ct][cd]
                    ddx, ddy = DIRECTIONS[cd]
                    nnx, nny = cx + ddx, cy + ddy
                    if not _in_bounds(nnx, nny) or terrain[nny][nnx] in ("T_W", "K1", "K2", "V") or _eng_blocks_oneway(eng, nnx, nny, cd):
                        break
                    cx, cy = nnx, nny
                elif ct in SPRING_DIR:
                    cd = SPRING_DIR[ct]
                    ddx, ddy = DIRECTIONS[cd]
                    for kk in (1, 2, 3):
                        kx, ky = cx + kk * ddx, cy + kk * ddy
                        if not _in_bounds(kx, ky) or terrain[ky][kx] in ("T_W", "K1", "K2", "V") or _eng_blocks_oneway(eng, kx, ky, cd):
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


def _can_ever_win_relaxed(eng: dict, box_reach_cache: dict) -> bool:
    terrain = eng["terrain"]
    portals = eng["portals"]
    has_pgate = any(terrain[y][x] == "P_GATE" for y in range(GRID_HEIGHT) for x in range(GRID_WIDTH))

    boxes = [
        (x, y)
        for y in range(1, GRID_HEIGHT - 1)
        for x in range(1, GRID_WIDTH - 1)
        if eng["occupant"][y][x] == "BOX"
    ]
    mobile_boxes = 0
    locked_plate_boxes = 0
    for x, y in boxes:
        if _is_cell_permanently_box_locked(eng, x, y):
            if terrain[y][x] == "PLATE":
                locked_plate_boxes += 1
        else:
            mobile_boxes += 1

    def reachable_without_pgate(sx, sy, goal_pt):
        vis = {(sx, sy)}
        q = collections.deque([(sx, sy)])
        while q:
            cx, cy = q.popleft()
            if (cx, cy) == goal_pt:
                return True
            for dn, (dx, dy) in DIRECTIONS.items():
                nx, ny = cx + dx, cy + dy
                if not _in_bounds(nx, ny) or (nx, ny) in vis:
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

    v = tuple(eng["targets"]["V"])
    needs_plates = has_pgate and not reachable_without_pgate(eng["hx"], eng["hy"], v)
    if needs_plates:
        plates_still_needing_mobile = max(0, len(eng["plates"]) - locked_plate_boxes)
        if mobile_boxes < plates_still_needing_mobile:
            return False
        num_boxes = mobile_boxes - plates_still_needing_mobile
    else:
        num_boxes = mobile_boxes

    max_total = eng["jumps"] + num_boxes

    def min_res_from(sx, sy, targets_set):
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
                if not _in_bounds(nx, ny):
                    continue
                t = terrain[ny][nx]
                if t == "T_W" or (t in ONEWAY_DIR and ONEWAY_DIR[t] != dname):
                    continue
                if t == "PIT":
                    if box_u + 1 <= num_boxes and tot_u + 1 <= max_total:
                        cand = (tot_u + 1, box_u + 1)
                        if cand < best_r.get((nx, ny), (999, 999)):
                            best_r[(nx, ny)] = cand
                            dq.append((cand[0], cand[1], nx, ny))
                    jx, jy = x + 2 * dx, y + 2 * dy
                    if _in_bounds(jx, jy):
                        jt = terrain[jy][jx]
                        if jt not in ("T_W", "PIT") and not (jt in ONEWAY_DIR and ONEWAY_DIR[jt] != dname):
                            if (tot_u - box_u) + 1 <= eng["jumps"] and tot_u + 1 <= max_total:
                                cand = (tot_u + 1, box_u)
                                if cand < best_r.get((jx, jy), (999, 999)):
                                    best_r[(jx, jy)] = cand
                                    dq.append((cand[0], cand[1], jx, jy))
                    continue

                cand = (tot_u, box_u)
                if cand < best_r.get((nx, ny), (999, 999)):
                    best_r[(nx, ny)] = cand
                    dq.appendleft((tot_u, box_u, nx, ny))
                    if t in PORTAL_PAIR_TILE and PORTAL_PAIR_TILE[t] in portals:
                        pp = portals[PORTAL_PAIR_TILE[t]]
                        if cand < best_r.get(pp, (999, 999)):
                            best_r[pp] = cand
                            dq.appendleft((tot_u, box_u, pp[0], pp[1]))
                    elif t in SPRING_DIR:
                        sdx, sdy = DIRECTIONS[SPRING_DIR[t]]
                        for kk in (1, 2, 3):
                            kx, ky = nx + kk * sdx, ny + kk * ddy if False else ny + kk * sdy
                            if not _in_bounds(kx, ky) or terrain[ky][kx] == "T_W":
                                break
                            if terrain[ky][kx] != "PIT" and cand < best_r.get((kx, ky), (999, 999)):
                                best_r[(kx, ky)] = cand
                                dq.appendleft((tot_u, box_u, kx, ky))
        return 999, 999

    req = []
    if not eng["has_k1"]:
        req.append(tuple(eng["targets"]["K1"]))
    if not eng["has_k2"]:
        req.append(tuple(eng["targets"]["K2"]))

    box_reaches = []
    for bx, by in boxes:
        if (bx, by) not in box_reach_cache:
            box_reach_cache[(bx, by)] = _compute_box_push_reach(eng, bx, by)
        box_reaches.append(box_reach_cache[(bx, by)])

    sink_groups = [{p} for p in eng["plates"]] if needs_plates else []
    saved_nb = num_boxes
    num_boxes = 0
    max_total = eng["jumps"]
    for g_pt in req + [v]:
        tr0, _ = min_res_from(eng["hx"], eng["hy"], {g_pt})
        if tr0 > eng["jumps"]:
            rev_pits = set()
            rq = collections.deque([g_pt])
            rvis = {g_pt}
            while rq:
                rcx, rcy = rq.popleft()
                cur_is_pit = (terrain[rcy][rcx] == "PIT")
                for dn, (dx, dy) in DIRECTIONS.items():
                    px, py = rcx - dx, rcy - dy
                    if not _in_bounds(px, py) or (px, py) in rvis:
                        continue
                    if terrain[rcy][rcx] in ONEWAY_DIR and ONEWAY_DIR[terrain[rcy][rcx]] != dn:
                        continue
                    pt_t = terrain[py][px]
                    if pt_t == "T_W":
                        continue
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
    max_total = eng["jumps"] + num_boxes

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
        t1, b1 = min_res_from(eng["hx"], eng["hy"], {v})
        return b1 <= num_boxes and (t1 - b1) <= eng["jumps"]
    elif len(req) == 1:
        t1, b1 = min_res_from(eng["hx"], eng["hy"], {req[0]})
        if b1 > num_boxes or (t1 - b1) > eng["jumps"]:
            return False
        t2, b2 = min_res_from(req[0][0], req[0][1], {v})
        return max(b1, b2) <= num_boxes and ((t1 - b1) + (t2 - b2)) <= eng["jumps"]
    else:
        k1, k2 = req[0], req[1]
        for first_k, second_k in ((k1, k2), (k2, k1)):
            t1, b1 = min_res_from(eng["hx"], eng["hy"], {first_k})
            t2, b2 = min_res_from(first_k[0], first_k[1], {second_k})
            t3, b3 = min_res_from(second_k[0], second_k[1], {v})
            jtot = (t1 - b1) + (t2 - b2) + (t3 - b3)
            if max(b1, b2, b3) <= num_boxes and jtot <= eng["jumps"]:
                return True
        return False


def _extract_mandatory_pits(eng: dict) -> list:
    """精确提取仅靠跳跃无法跨越、必须用箱子填平的真实咽喉 PIT 集合（排除墙壁激光射击孔）。"""
    terrain = eng["terrain"]
    portals = eng["portals"]
    max_j = eng["jumps"]

    def zero_box_min_j(sx, sy, g_pt):
        best_j = {(sx, sy): 0}
        dq = collections.deque([(0, sx, sy)])
        while dq:
            ju, x, y = dq.popleft()
            if ju > best_j.get((x, y), 999):
                continue
            if (x, y) == g_pt:
                return ju
            for dname, (dx, dy) in DIRECTIONS.items():
                nx, ny = x + dx, y + dy
                if not _in_bounds(nx, ny):
                    continue
                t = terrain[ny][nx]
                if t == "T_W" or (t in ONEWAY_DIR and ONEWAY_DIR[t] != dname):
                    continue
                if t == "PIT":
                    jx, jy = x + 2 * dx, y + 2 * dy
                    if _in_bounds(jx, jy):
                        jt = terrain[jy][jx]
                        if jt not in ("T_W", "PIT") and not (jt in ONEWAY_DIR and ONEWAY_DIR[jt] != dname):
                            if ju + 1 <= max_j and ju + 1 < best_j.get((jx, jy), 999):
                                best_j[(jx, jy)] = ju + 1
                                dq.append((ju + 1, jx, jy))
                    continue
                if ju < best_j.get((nx, ny), 999):
                    best_j[(nx, ny)] = ju
                    dq.appendleft((ju, nx, ny))
                    if t in PORTAL_PAIR_TILE and PORTAL_PAIR_TILE[t] in portals:
                        pp = portals[PORTAL_PAIR_TILE[t]]
                        if ju < best_j.get(pp, 999):
                            best_j[pp] = ju
                            dq.appendleft((ju, pp[0], pp[1]))
                    elif t in SPRING_DIR:
                        sdx, sdy = DIRECTIONS[SPRING_DIR[t]]
                        for kk in (1, 2, 3):
                            kx, ky = nx + kk * sdx, ny + kk * sdy
                            if not _in_bounds(kx, ky) or terrain[ky][kx] == "T_W":
                                break
                            if terrain[ky][kx] != "PIT" and ju < best_j.get((kx, ky), 999):
                                best_j[(kx, ky)] = ju
                                dq.appendleft((ju, kx, ky))
        return 999

    goals = []
    if not eng["has_k1"]:
        goals.append(tuple(eng["targets"]["K1"]))
    if not eng["has_k2"]:
        goals.append(tuple(eng["targets"]["K2"]))
    goals.append(tuple(eng["targets"]["V"]))

    mand_pits = set()
    for g_pt in goals:
        if zero_box_min_j(eng["hx"], eng["hy"], g_pt) > max_j:
            rq = collections.deque([g_pt])
            rvis = {g_pt}
            while rq:
                rcx, rcy = rq.popleft()
                cur_is_pit = (terrain[rcy][rcx] == "PIT")
                for dn, (dx, dy) in DIRECTIONS.items():
                    px, py = rcx - dx, rcy - dy
                    if not _in_bounds(px, py) or (px, py) in rvis:
                        continue
                    if terrain[rcy][rcx] in ONEWAY_DIR and ONEWAY_DIR[terrain[rcy][rcx]] != dn:
                        continue
                    pt_t = terrain[py][px]
                    if pt_t == "T_W":
                        continue
                    if pt_t == "PIT":
                        rvis.add((px, py))
                        mand_pits.add((px, py))
                        rq.append((px, py))
                    elif not cur_is_pit and pt_t != "W":
                        rvis.add((px, py))
                        rq.append((px, py))
    return sorted(mand_pits)


def _heuristic_v22(eng: dict, has_pgates: bool, true_pits: list = ()) -> float:
    h = 0.0
    k1 = tuple(eng["targets"]["K1"])
    k2 = tuple(eng["targets"]["K2"])
    v = tuple(eng["targets"]["V"])
    pos = (eng["hx"], eng["hy"])

    if not eng["has_k1"] and not eng["has_k2"]:
        d_keys = min(
            _manhattan(pos, k1) + _manhattan(k1, k2) + _manhattan(k2, v),
            _manhattan(pos, k2) + _manhattan(k2, k1) + _manhattan(k1, v),
        )
        h += 75.0 * 2 + 0.9 * d_keys
    elif not eng["has_k1"]:
        h += 75.0 + 0.9 * (_manhattan(pos, k1) + _manhattan(k1, v))
    elif not eng["has_k2"]:
        h += 75.0 + 0.9 * (_manhattan(pos, k2) + _manhattan(k2, v))
    else:
        h += 0.9 * _manhattan(pos, v)

    boxes = None
    if (has_pgates and eng["plates"]) or true_pits:
        boxes = [
            (x, y)
            for y in range(1, GRID_HEIGHT - 1)
            for x in range(1, GRID_WIDTH - 1)
            if eng["occupant"][y][x] == "BOX"
        ]
        free_boxes = [b for b in boxes if eng["terrain"][b[1]][b[0]] != "PLATE"]
        if has_pgates and eng["plates"]:
            uncovered = [p for p in eng["plates"] if eng["occupant"][p[1]][p[0]] != "BOX"]
            h += 45.0 * len(uncovered)
            if uncovered and free_boxes:
                for up in uncovered:
                    h += 2.5 * min(_manhattan(b, up) for b in free_boxes)
        if true_pits:
            rem_pits = [p for p in true_pits if eng["terrain"][p[1]][p[0]] == "PIT"]
            h += 35.0 * len(rem_pits)
            if rem_pits and free_boxes:
                h += 2.2 * min(_manhattan(b, p) for b in free_boxes for p in rem_pits)

    h += 6.0 * (3 - eng["jumps"]) + 3.0 * (3 - eng["throws"]) + 8.0 * (2 - eng["bombs_inv"])
    h += 2.5 * (100 - eng["hp"])
    return h


def _solve_full_dungeon(initial_eng: dict, time_budget: float, visited_sigs=None):
    """
    Returns (is_complete_win: bool, action_list: list).
    """
    t0 = time.monotonic()
    deadline = t0 + time_budget
    if visited_sigs is None:
        visited_sigs = set()

    has_pgates = any(
        initial_eng["terrain"][y][x] == "P_GATE"
        for y in range(GRID_HEIGHT)
        for x in range(GRID_WIDTH)
    )
    num_plates = len(initial_eng["plates"])
    true_pits = _extract_mandatory_pits(initial_eng)
    box_reach_cache = {}
    relax_memo = {}

    best_partial = []
    best_partial_rank = (
        int(initial_eng["has_k1"]) + int(initial_eng["has_k2"]),
        sum(1 for px, py in initial_eng["plates"] if initial_eng["occupant"][py][px] == "BOX"),
        -sum(1 for px, py in true_pits if initial_eng["terrain"][py][px] == "PIT"),
        -_heuristic_v22(initial_eng, has_pgates, true_pits),
    )

    for allow_dmg in (False, True):
        if time.monotonic() >= deadline:
            break
        sub_deadline = deadline if allow_dmg else (t0 + time_budget * 0.82)

        uid = 0
        h0 = _heuristic_v22(initial_eng, has_pgates, true_pits)
        pq = [(h0, 0.0, uid, initial_eng, ())]
        best_g = {_world_signature(initial_eng): 0.0}

        while pq and time.monotonic() < sub_deadline:
            _, g_val, _, eng, macro_path = heapq.heappop(pq)
            sig = _world_signature(eng)
            if g_val > best_g.get(sig, 1e18) + 1e-6:
                continue

            if macro_path and sig not in visited_sigs:
                prank = (
                    int(eng["has_k1"]) + int(eng["has_k2"]),
                    sum(1 for px, py in eng["plates"] if eng["occupant"][py][px] == "BOX"),
                    -sum(1 for px, py in true_pits if eng["terrain"][py][px] == "PIT"),
                    -_heuristic_v22(eng, has_pgates, true_pits),
                )
                if prank > best_partial_rank:
                    best_partial_rank = prank
                    best_partial = list(macro_path)

            best_at_cell, reconstruct, special_hits, win_nav = _fast_hero_nav(eng, allow_damage=allow_dmg)
            if win_nav is not None:
                full_sol = list(macro_path + win_nav)
                v_eng = _clone_eng(initial_eng)
                for a in full_sol:
                    _eng_step(v_eng, a)
                if v_eng["status"] == "CLEARED":
                    return True, full_sol

            def push_child(nav_acts, extra_acts, extra_penalty=0.0):
                nonlocal uid
                tot_acts = macro_path + nav_acts + extra_acts
                if len(tot_acts) > MAX_TURNS:
                    return None
                c_eng = _clone_eng(eng)
                hp_before = c_eng["hp"]
                for a in nav_acts + extra_acts:
                    _eng_step(c_eng, a)
                    if c_eng["status"] in ("DEAD", "CLEARED"):
                        break
                if c_eng["status"] == "DEAD":
                    return None
                if not allow_dmg and c_eng["hp"] < hp_before:
                    return None
                if c_eng["status"] == "CLEARED":
                    return list(tot_acts)

                if (
                    c_eng["jumps"] < eng["jumps"]
                    or c_eng["has_k1"] != eng["has_k1"]
                    or c_eng["has_k2"] != eng["has_k2"]
                    or any(a.startswith("MOVE_") for a in extra_acts)
                    or not has_pgates
                ):
                    rm_key = (
                        _canonical_hero_anchor(c_eng), c_eng["has_k1"], c_eng["has_k2"], c_eng["jumps"],
                        tuple((x, y) for y in range(1, GRID_HEIGHT - 1) for x in range(1, GRID_WIDTH - 1) if c_eng["occupant"][y][x] == "BOX"),
                        sum(1 for y in range(1, GRID_HEIGHT - 1) for x in range(1, GRID_WIDTH - 1) if c_eng["terrain"][y][x] == "PIT"),
                    )
                    ok_rel = relax_memo.get(rm_key)
                    if ok_rel is None:
                        ok_rel = _can_ever_win_relaxed(c_eng, box_reach_cache)
                        relax_memo[rm_key] = ok_rel
                    if not ok_rel:
                        return None

                if has_pgates and not _eng_plates_active(c_eng):
                    usable_boxes = 0
                    for by in range(1, GRID_HEIGHT - 1):
                        for bx in range(1, GRID_WIDTH - 1):
                            if c_eng["occupant"][by][bx] == "BOX" and not _is_box_static_corner_deadlock(c_eng, bx, by):
                                usable_boxes += 1
                    if usable_boxes < num_plates:
                        return None

                new_g = float(c_eng["turn"]) + 2.5 * (100 - c_eng["hp"]) + extra_penalty
                nsig = _world_signature(c_eng)
                if new_g < best_g.get(nsig, 1e18):
                    best_g[nsig] = new_g
                    uid += 1
                    nh = _heuristic_v22(c_eng, has_pgates, true_pits)
                    heapq.heappush(pq, (new_g + 1.35 * nh, new_g, uid, c_eng, tot_acts))
                return None

            # 1. 拾取钥匙 / 踩开关 / 吃血包 / 受控踩怪
            for (ekind, ex, ey, _ej), (_, pnid, lact) in special_hits.items():
                if time.monotonic() >= sub_deadline:
                    break
                if ekind == "HEAL" and eng["hp"] == 100:
                    continue
                win_sol = push_child(reconstruct(pnid, lact), ())
                if win_sol is not None:
                    return True, win_sol

            # 2. 推箱子宏动作 (仅为每个未完成压板/深渊匹配最近可达箱子，彻底免疫空场游离诱饵箱！)
            sinks_now = [p for p in eng["plates"] if eng["occupant"][p[1]][p[0]] != "BOX"] + [
                p for p in true_pits if eng["terrain"][p[1]][p[0]] == "PIT"
            ]
            all_free_boxes = [
                (bx, by)
                for by in range(1, GRID_HEIGHT - 1)
                for bx in range(1, GRID_WIDTH - 1)
                if eng["occupant"][by][bx] == "BOX" and eng["terrain"][by][bx] != "PLATE"
            ]
            box_target_sinks = collections.defaultdict(list)
            for sk in sinks_now:
                ranked_b = []
                for bx, by in all_free_boxes:
                    if (bx, by) not in box_reach_cache:
                        box_reach_cache[(bx, by)] = _compute_box_push_reach(eng, bx, by)
                    if sk in box_reach_cache[(bx, by)]:
                        ranked_b.append((_manhattan((bx, by), sk), bx, by))
                ranked_b.sort()
                for idx_r, (d_b, bx, by) in enumerate(ranked_b[:2]):
                    if idx_r == 0 or d_b <= ranked_b[0][0] + 5:
                        box_target_sinks[(bx, by)].append(sk)

            box_push_cands = []
            for by in range(1, GRID_HEIGHT - 1):
                for bx in range(1, GRID_WIDTH - 1):
                    if eng["occupant"][by][bx] != "BOX":
                        continue
                    my_sinks = box_target_sinks.get((bx, by), ())
                    if not my_sinks and eng["terrain"][by][bx] != "PLATE":
                        open_adj = sum(
                            1 for adx, ady in DIRECTIONS.values()
                            if _in_bounds(bx + adx, by + ady) and not _eng_is_high_wall(eng, bx + adx, by + ady)
                        )
                        if open_adj > 2:
                            continue
                    d_prev = min((_manhattan((bx, by), sk) for sk in my_sinks), default=0)
                    for dname, (dx, dy) in DIRECTIONS.items():
                        sx, sy = bx - dx, by - dy
                        p2x, p2y = bx + dx, by + dy
                        if (sx, sy) not in best_at_cell:
                            continue
                        if _eng_is_high_wall(eng, bx, by) or _eng_blocks_oneway(eng, bx, by, dname):
                            continue
                        if not _in_bounds(p2x, p2y) or _eng_is_high_wall(eng, p2x, p2y) or _eng_blocks_oneway(eng, p2x, p2y, dname):
                            continue
                        if eng["occupant"][p2y][p2x] is not None or eng["terrain"][p2y][p2x] in ("K1", "K2", "V"):
                            continue
                        d_cur = min((_manhattan((p2x, p2y), sk) for sk in my_sinks), default=0)
                        improves = 0 if (my_sinks and d_cur < d_prev) else 1
                        rcost_s, nid, _ = best_at_cell[(sx, sy)]
                        box_push_cands.append((improves, d_cur, rcost_s, bx, by, p2x, p2y, dname, dx, dy, nid, my_sinks))

            box_push_cands.sort(key=lambda it: it[:5])
            non_imp_cnt = 0
            for improves, d_cur, _, bx, by, p2x, p2y, dname, dx, dy, nid, my_sinks in box_push_cands:
                if time.monotonic() >= sub_deadline:
                    break
                if improves == 1:
                    non_imp_cnt += 1
                    if non_imp_cnt > 3:
                        continue
                nav_p = reconstruct(nid)
                push_act = "MOVE_" + dname
                extra_p = 0.0 if improves == 0 else 8.0
                win_sol = push_child(nav_p, (push_act,), extra_penalty=extra_p)
                if win_sol is not None:
                    return True, win_sol

                if improves == 0 and my_sinks and eng["terrain"][p2y][p2x] == "EMPTY":
                    chain = [push_act]
                    nbx, nby = p2x, p2y
                    for _ in range(8):
                        nx2, ny2 = nbx + dx, nby + dy
                        if not _in_bounds(nx2, ny2) or _eng_is_high_wall(eng, nx2, ny2) or _eng_blocks_oneway(eng, nx2, ny2, dname):
                            break
                        if eng["occupant"][ny2][nx2] is not None or eng["terrain"][ny2][nx2] in ("K1", "K2", "V"):
                            break
                        if min(_manhattan((nx2, ny2), sk) for sk in my_sinks) >= min(_manhattan((nbx, nby), sk) for sk in my_sinks):
                            break
                        chain.append(push_act)
                        nbx, nby = nx2, ny2
                        if eng["terrain"][nby][nbx] in ("PLATE", "PIT", "ICE", *SPRING_DIR.keys(), *MIRROR_MAP.keys()):
                            break
                    if len(chain) >= 2:
                        win_sol2 = push_child(nav_p, tuple(chain))
                        if win_sol2 is not None:
                            return True, win_sol2

            # 3. 远程飞石打靶 (支持单向门穿透、折跃镜反弹与第6格冰滑)
            walkable_switches = {(ex, ey) for (ekind, ex, ey, _ej) in special_hits if ekind == "SWITCH"}
            if eng["throws"] > 0:
                interest_rows = set()
                interest_cols = set()
                for ty_i in range(1, GRID_HEIGHT - 1):
                    trow = eng["terrain"][ty_i]
                    orow = eng["occupant"][ty_i]
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
                        if eng["terrain"][vy][vx] in ("ICE", *MIRROR_MAP.keys(), *SPRING_DIR.keys(), *PORTAL_PAIR_TILE.keys()):
                            continue
                        for dname in ("U", "D", "L", "R"):
                            if dname in ("L", "R") and vy not in interest_rows:
                                continue
                            if dname in ("U", "D") and vx not in interest_cols:
                                continue
                            hit = _trace_stone_from(eng, vx, vy, dname)
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
                        return True, win_sol

            # 4. 拓扑割墙炸弹破障宏动作 (含 3 回合安全闪避捆绑验证)
            if eng["bombs_inv"] > 0 and not eng["bombs"]:
                no_jump_cells = {pos for pos, (_, _, rj) in best_at_cell.items() if rj == eng["jumps"]}
                bomb_cands = []
                active_lms = []
                if not eng["has_k1"]:
                    active_lms.append(eng["targets"]["K1"])
                if not eng["has_k2"]:
                    active_lms.append(eng["targets"]["K2"])
                if eng["has_k1"] and eng["has_k2"]:
                    active_lms.append(eng["targets"]["V"])

                for (bx, by), (rcost, nid, _rj) in best_at_cell.items():
                    if _rj < eng["jumps"]:
                        continue
                    if eng["terrain"][by][bx] in ("ICE", *MIRROR_MAP.keys(), *SPRING_DIR.keys(), *PORTAL_PAIR_TILE.keys()):
                        continue
                    opens_new_space = False
                    crater_breaches_room = False
                    destroys_laser = False
                    near_active_target = 999

                    blast_set = {
                        (bx + dx, by + dy)
                        for dy in (-1, 0, 1)
                        for dx in (-1, 0, 1)
                        if _in_bounds(bx + dx, by + dy) and eng["terrain"][by + dy][bx + dx] != "T_W"
                    }
                    for wx, wy in blast_set:
                        wt = eng["terrain"][wy][wx]
                        wo = eng["occupant"][wy][wx]
                        if wt in ALL_LASER_DIR:
                            destroys_laser = True
                        if wt in DESTRUCTIBLE_WALLS or wo == "TNT":
                            for tlm in active_lms:
                                near_active_target = min(near_active_target, _manhattan((wx, wy), tlm))
                            for adx, ady in DIRECTIONS.values():
                                ux, uy = wx + adx, wy + ady
                                if _in_bounds(ux, uy) and (ux, uy) not in no_jump_cells:
                                    ut = eng["terrain"][uy][ux]
                                    if not _eng_is_high_wall(eng, ux, uy) and ut != "PIT" and eng["occupant"][uy][ux] != "TNT":
                                        opens_new_space = True
                                        if (ux, uy) not in blast_set:
                                            crater_breaches_room = True
                                    elif eng["bombs_inv"] >= 2 and ut in DESTRUCTIBLE_WALLS:
                                        for bdx, bdy in DIRECTIONS.values():
                                            u2x, u2y = ux + bdx, uy + bdy
                                            if _in_bounds(u2x, u2y) and (u2x, u2y) not in no_jump_cells and not _eng_is_high_wall(eng, u2x, u2y) and eng["terrain"][u2y][u2x] != "PIT":
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
                        if all(_manhattan((bx, by), (ox, oy)) >= 2 for _, _, _, ox, oy, _ in dedup_bombs):
                            dedup_bombs.append(item)
                            if len(dedup_bombs) >= cap:
                                break
                for cb_flag, _, _, bx, by, nid in dedup_bombs:
                    if time.monotonic() >= sub_deadline:
                        break
                    npath = reconstruct(nid)
                    b_eng = _clone_eng(eng)
                    ok_nav = True
                    for a in npath:
                        _eng_step(b_eng, a)
                        if b_eng["status"] != "ALIVE" or (not allow_dmg and b_eng["hp"] < eng["hp"]):
                            ok_nav = False
                            break
                    if not ok_nav or (b_eng["hx"], b_eng["hy"]) != (bx, by):
                        continue
                    _eng_step(b_eng, "BOMB")
                    if b_eng["status"] != "ALIVE" or (not allow_dmg and b_eng["hp"] < eng["hp"]):
                        continue
                    found_dodge = None
                    dodge_moves = ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT", "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R")
                    for d1 in dodge_moves:
                        if d1.startswith("JUMP_") and b_eng["jumps"] <= 0:
                            continue
                        e1 = _clone_eng(b_eng)
                        _eng_step(e1, d1)
                        if e1["status"] == "CLEARED":
                            return True, list(macro_path + npath + ("BOMB", d1))
                        if e1["status"] != "ALIVE" or (not allow_dmg and e1["hp"] < eng["hp"]):
                            continue
                        for d2 in dodge_moves:
                            if d2.startswith("JUMP_") and e1["jumps"] <= 0:
                                continue
                            e2 = _clone_eng(e1)
                            _eng_step(e2, d2)
                            if e2["status"] == "CLEARED":
                                return True, list(macro_path + npath + ("BOMB", d1, d2))
                            if e2["status"] == "ALIVE" and (allow_dmg or e2["hp"] == eng["hp"]):
                                found_dodge = ("BOMB", d1, d2)
                                break
                        if found_dodge is not None:
                            break
                    if found_dodge is not None:
                        win_sol = push_child(npath, found_dodge, extra_penalty=(32.0 if cb_flag == 0 else 65.0))
                        if win_sol is not None:
                            return True, win_sol

    return False, best_partial


def _emergency_safe_step(eng: dict) -> str:
    """当全局搜索未产出序列时的毫秒级 2-ply 安全贪心兜底，保证绝不接口报错或原地受死。"""
    k1 = tuple(eng["targets"]["K1"])
    k2 = tuple(eng["targets"]["K2"])
    v = tuple(eng["targets"]["V"])
    goal = v if (eng["has_k1"] and eng["has_k2"]) else (k2 if eng["has_k1"] else k1)

    best_act = "WAIT"
    best_sc = (-1, -9999, -9999)
    cand = ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT", "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R")
    for act in cand:
        if act.startswith("JUMP_") and eng["jumps"] <= 0:
            continue
        e1 = _clone_eng(eng)
        _eng_step(e1, act)
        if e1["status"] == "CLEARED":
            return act
        if e1["status"] != "ALIVE":
            continue
        survives_2 = 0
        for act2 in ("WAIT", "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R"):
            e2 = _clone_eng(e1)
            _eng_step(e2, act2)
            if e2["status"] in ("ALIVE", "CLEARED") and e2["hp"] == e1["hp"]:
                survives_2 = 1
                break
        sc = (survives_2, e1["hp"], -_manhattan((e1["hx"], e1["hy"]), goal))
        if sc > best_sc:
            best_sc = sc
            best_act = act
    return best_act


def _state_quick_sig(state: dict) -> tuple:
    h = state["hero"]
    return (
        h["x"], h["y"], h["hp"],
        h["keys"][0], h["keys"][1],
        state["gates_flipped"], state.get("plates_active", False),
    )


def _store_plan_in_memory(sim_eng: dict, plan: list, is_complete: bool, memory: dict) -> None:
    expected_sigs = []
    probe = _clone_eng(sim_eng)
    for act in plan:
        expected_sigs.append((
            probe["hx"], probe["hy"], probe["hp"],
            probe["has_k1"], probe["has_k2"],
            probe["gates_flipped"], _eng_plates_active(probe),
        ))
        _eng_step(probe, act)
    memory["plan"] = plan
    memory["sigs"] = expected_sigs
    memory["idx"] = 0
    memory["complete"] = is_complete


def decide_action(state: dict, memory: dict) -> str:
    """
    v2.2 FULL 明牌全局规划决策器：
    - Turn 1 利用 1.56s 安全窗口执行完整宏动作搜索并缓存精确校验轨迹，Turn 2..240 0.02ms 极速出招；
    - 若遇超深地图分段求解或子进程重启导致 memory 清空，自动按 0.24s 安全预算在线续算无缝衔接。
    """
    turn = state["turn"]
    budget = 1.56 if turn == 1 else 0.24
    visited_sigs = memory.setdefault("visited_sigs", set())

    if "plan" in memory and memory["idx"] < len(memory["plan"]):
        idx = memory["idx"]
        if memory["sigs"][idx] == _state_quick_sig(state):
            if not memory.get("complete", False) and (len(memory["plan"]) - idx) <= 1:
                sim_eng = _decode_state_to_eng(state)
                visited_sigs.add(_world_signature(sim_eng))
                ok_win, new_plan = _solve_full_dungeon(sim_eng, budget, visited_sigs)
                if new_plan:
                    _store_plan_in_memory(sim_eng, new_plan, ok_win, memory)
                    memory["idx"] = 1
                    return new_plan[0]
            act = memory["plan"][idx]
            memory["idx"] = idx + 1
            return act
        else:
            saved_vs = set(visited_sigs)
            memory.clear()
            memory["visited_sigs"] = saved_vs
            visited_sigs = memory["visited_sigs"]

    sim_eng = _decode_state_to_eng(state)
    visited_sigs.add(_world_signature(sim_eng))
    ok_win, plan = _solve_full_dungeon(sim_eng, budget, visited_sigs)
    if plan:
        _store_plan_in_memory(sim_eng, plan, ok_win, memory)
        memory["idx"] = 1
        return plan[0]

    return _emergency_safe_step(sim_eng)
