"""dungeon_dev.py — 下半场魔王图构建 + 作者自证 + 准入校验（开发期用）。"""
import sys

sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_07_deepseek_dsh")
import judge_v22 as J
import admission as AD

W, H = 40, 26


def blank():
    g = [["EMPTY"] * W for _ in range(H)]
    for x in range(W):
        g[0][x] = "T_W"
        g[H - 1][x] = "T_W"
    for y in range(H):
        g[y][0] = "T_W"
        g[y][W - 1] = "T_W"
    return g


def rect(g, x0, y0, x1, y1, t):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            g[y][x] = t


def build_grid():
    g = blank()
    # ---- 中央分隔墙 x=21（T_W 防爆，唯一两个缺口：y=1 隧道口 / y=20 压板门）
    for y in range(1, 25):
        g[y][21] = "T_W"
    g[1][21] = "EMPTY"
    g[20][21] = "P_GATE"

    # ---- 顶部死亡隧道：y=1 x=10..21，南侧承重墙 y=2，唯一入口 (12,2)
    for x in range(10, 21):
        g[2][x] = "T_W"
    g[2][10] = "EMPTY"
    g[1][9] = "LASER_R"

    # ---- K2 壁龛（西区）
    for (x, y) in ((12, 21), (12, 22), (12, 23), (14, 21), (14, 22), (14, 23), (13, 23)):
        g[y][x] = "T_W"
    g[22][13] = "K2"

    # ---- K1 壁龛（东区）
    for (x, y) in ((29, 4), (30, 4), (31, 4), (29, 5), (31, 5)):
        g[y][x] = "T_W"
    g[5][30] = "K1"
    g[13][36] = "V"

    # ---- 压板 + 箱子 + 深渊陷阱
    g[8][3] = "PLATE"
    g[18][3] = "PLATE"
    g[8][8] = "BOX"
    g[18][8] = "BOX"
    g[8][10] = "PIT"
    g[18][10] = "PIT"
    g[6][8] = "PIT"
    g[16][8] = "PIT"
    return g


def bfs_path(g, start, goal, pgate_open=False):
    """在静态地图上求一条步行路径（不穿高墙/深渊/箱子），返回动作列表。"""
    from collections import deque
    W, H = 40, 26
    prev = {start: (None, None)}
    dq = deque([start])
    while dq:
        x, y = dq.popleft()
        if (x, y) == goal:
            break
        for dk, (dx, dy) in (("U", (0, -1)), ("D", (0, 1)), ("L", (-1, 0)), ("R", (1, 0))):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            if (nx, ny) in prev:
                continue
            t = g[ny][nx]
            if t == "P_GATE":
                if not pgate_open:
                    continue
            elif t in ("T_W", "W", "PIT", "BOX", "R_GATE", "B_GATE") or \
                    t.startswith("LASER") or t.startswith("ONEWAY"):
                continue
            prev[(nx, ny)] = ((x, y), "MOVE_" + dk)
            dq.append((nx, ny))
    if goal not in prev:
        return None
    acts = []
    cur = goal
    while prev[cur][0] is not None:
        p, a = prev[cur]
        acts.append(a)
        cur = p
    acts.reverse()
    return acts


def author_solution(g):
    """手工设计的自证路线：K2 -> 压板A -> 压板B -> P_GATE -> K1 -> V。"""
    acts = []
    cur = (2, 13)
    wps = [(13, 21), (13, 22), (9, 8)]
    for wp in wps:
        seg = bfs_path(g, cur, wp)
        if seg is None:
            raise RuntimeError("路径不通 %s -> %s" % (cur, wp))
        acts += seg
        cur = wp
    acts += ["MOVE_L"] * 5       # 箱 A 推上 PLATE(3,8)
    cur = (4, 8)
    for wp in [(9, 18)]:
        seg = bfs_path(g, cur, wp)
        if seg is None:
            raise RuntimeError("路径不通 %s -> %s" % (cur, wp))
        acts += seg
        cur = wp
    acts += ["MOVE_L"] * 5       # 箱 B 推上 PLATE(3,18)
    cur = (4, 18)
    for wp in [(20, 20), (22, 20), (30, 6), (30, 5), (36, 13)]:
        seg = bfs_path(g, cur, wp, pgate_open=True)
        if seg is None:
            raise RuntimeError("路径不通 %s -> %s" % (cur, wp))
        acts += seg
        cur = wp
    return acts


LEG = {"T_W": "#", "EMPTY": ".", "W": "+", "ICE": "=", "PIT": "O", "CRACK": "~",
       "SWITCH": "!", "R_GATE": "r", "B_GATE": "b", "PLATE": "_", "P_GATE": "g",
       "TNT": "T", "BOX": "B", "HEAL": "H", "MIMIC": "M", "K1": "1", "K2": "2", "V": "V",
       "SPRING_U": "A", "SPRING_D": "V", "SPRING_L": "<", "SPRING_R": ">",
       "MIRROR_NE": "/", "MIRROR_SE": "\\", "MIRROR_SW": "/", "MIRROR_NW": "\\",
       "LASER_U": "U", "LASER_D": "D", "LASER_L": "L", "LASER_R": "R",
       "LASER2_U": "u", "LASER2_D": "d", "LASER2_L": "l", "LASER2_R": "j",
       "ONEWAY_U": "n", "ONEWAY_D": "s", "ONEWAY_L": "w", "ONEWAY_R": "e",
       "PORTAL_1A": "P", "PORTAL_1B": "Q", "PORTAL_2A": "p", "PORTAL_2B": "q"}


def show(g):
    print("     " + "".join(str(x % 10) for x in range(W)))
    for y in range(H):
        print("%2d | " % y + "".join(LEG.get(t, "?") for t in g[y]))


def main():
    g = build_grid()
    ok, errs, info = J.validate_dungeon(g)
    print("validate:", ok, errs)
    print("spent=%d vault=%d g=%.3f" % (info.get("spent_gold", -1), info.get("vault_gold", -1),
                                        info.get("g", 0)))
    show(g)
    acts = author_solution(g)
    print("author steps:", len(acts))
    ok2, errs2 = AD.check_author_solution(g, acts)
    print("author_solution:", ok2, errs2)
    ok3, errs3, inf3 = AD.check_spawn_admission(g)
    print("spawn admission:", ok3, errs3, inf3)


if __name__ == "__main__":
    main()
