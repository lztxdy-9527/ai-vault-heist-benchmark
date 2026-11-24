"""Simulated opponent hero policies, run against our dungeon to estimate the demon score."""
import random
import sys
from collections import deque
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\deepseek_max\dev")
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\deepseek_max")
import engine as E
import submission as S

DIRS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
BAD = {"W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R", "PIT", "MIMIC", "BOX", "TNT"}


def danger(t):
    return t in BAD


def pol_random(eng, rng, mem):
    return rng.choice(["MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT",
                       "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R", "BOMB"])


def pol_greedy(eng, rng, mem):
    """move toward the nearest key/vault, refusing visible pits & walls"""
    st = E.make_state(eng, "BLIND")
    hx, hy = eng.hero["x"], eng.hero["y"]
    k1, k2, v = eng._targets()
    keys = eng.hero["keys"]
    tgt = v if (keys[0] and keys[1]) else (k2 if keys[0] else (k1 if not keys[1] else k2))
    if tgt is None:
        return "WAIT"
    best = None
    for dk, (dx, dy) in DIRS.items():
        nx, ny = hx + dx, hy + dy
        if not (0 <= nx < 40 and 0 <= ny < 26):
            continue
        t = st["terrain"][ny][nx]
        if t != "UNKNOWN" and danger(t):
            continue
        if st["occupant"][ny][nx] in ("BOX", "TNT"):
            continue
        d = abs(nx - tgt[0]) + abs(ny - tgt[1])
        if best is None or d < best[0]:
            best = (d, "MOVE_" + dk)
    if best is None:
        return "WAIT"
    return best[1]


def pol_explorer(eng, rng, mem):
    """BFS over known-passable cells (unknown treated as passable with a penalty)."""
    st = E.make_state(eng, "BLIND")
    hx, hy = eng.hero["x"], eng.hero["y"]
    k1, k2, v = eng._targets()
    keys = eng.hero["keys"]
    tgt = v if (keys[0] and keys[1]) else (k2 if keys[0] else (k1 if not keys[1] else k2))
    if tgt is None:
        return "WAIT"
    ter = st["terrain"]
    occ = st["occupant"]
    start = (hx, hy)
    prev = {start: None}
    q = deque([start])
    goal = None
    while q:
        cur = q.popleft()
        if cur == tgt:
            goal = cur
            break
        cx, cy = cur
        for dk, (dx, dy) in DIRS.items():
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < 40 and 0 <= ny < 26):
                continue
            if (nx, ny) in prev:
                continue
            t = ter[ny][nx]
            if occ[ny][nx] in ("BOX", "TNT"):
                continue
            if t != "UNKNOWN" and danger(t):
                continue
            prev[(nx, ny)] = (cur, "MOVE_" + dk)
            q.append((nx, ny))
    if goal is None:
        # walk greedily toward target through unknown
        best = None
        for dk, (dx, dy) in DIRS.items():
            nx, ny = hx + dx, hy + dy
            if not (0 <= nx < 40 and 0 <= ny < 26):
                continue
            t = ter[ny][nx]
            if t != "UNKNOWN" and danger(t):
                continue
            d = abs(nx - tgt[0]) + abs(ny - tgt[1])
            if best is None or d < best[0]:
                best = (d, "MOVE_" + dk)
        return best[1] if best else "WAIT"
    node = goal
    first = None
    while prev[node] is not None:
        node, act = prev[node]
        first = act
    return first or "WAIT"


def pol_jumper(eng, rng, mem):
    """explorer + jump edges over known hazards"""
    st = E.make_state(eng, "BLIND")
    hx, hy = eng.hero["x"], eng.hero["y"]
    k1, k2, v = eng._targets()
    keys = eng.hero["keys"]
    tgt = v if (keys[0] and keys[1]) else (k2 if keys[0] else (k1 if not keys[1] else k2))
    if tgt is None:
        return "WAIT"
    ter = st["terrain"]
    occ = st["occupant"]
    start = (hx, hy)

    def cell_ok(nx, ny, allow_unknown=True):
        if not (0 <= nx < 40 and 0 <= ny < 26):
            return False
        t = ter[ny][nx]
        if occ[ny][nx] in ("BOX", "TNT"):
            return False
        if t == "UNKNOWN":
            return allow_unknown
        return not danger(t)

    prev = {start: None}
    q = deque([start])
    goal = None
    while q:
        cur = q.popleft()
        if cur == tgt:
            goal = cur
            break
        cx, cy = cur
        for dk, (dx, dy) in DIRS.items():
            nx, ny = cx + dx, cy + dy
            if (nx, ny) not in prev and cell_ok(nx, ny):
                prev[(nx, ny)] = (cur, "MOVE_" + dk)
                q.append((nx, ny))
        if eng.hero["jumps"] > 0:
            for dk, (dx, dy) in DIRS.items():
                mx, my = cx + dx, cy + dy
                nx, ny = cx + 2 * dx, cy + 2 * dy
                if (nx, ny) in prev:
                    continue
                t1 = ter[my][mx] if (0 <= mx < 40 and 0 <= my < 26) else None
                if t1 is not None and t1 in ("W", "T_W"):
                    continue
                if cell_ok(nx, ny):
                    prev[(nx, ny)] = (cur, "JUMP_" + dk)
                    q.append((nx, ny))
    if goal is None:
        return pol_explorer(eng, rng, mem)
    node = goal
    first = None
    while prev[node] is not None:
        node, act = prev[node]
        first = act
    return first or "WAIT"


def run(policy, grid, seed=7):
    rng = random.Random(seed)
    eng = E.Engine(grid=grid)
    mem = {}
    for _ in range(240):
        if eng.status != "ALIVE":
            break
        a = policy(eng, rng, mem)
        if a not in ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT", "JUMP_U", "JUMP_D",
                     "JUMP_L", "JUMP_R", "THROW_U", "THROW_D", "THROW_L", "THROW_R", "BOMB"):
            a = "WAIT"
        eng.play_turn(a)
    return eng


if __name__ == "__main__":
    grid = S.build_dungeon()["grid"]
    for name, pol in (("random", pol_random), ("greedy", pol_greedy),
                      ("explorer", pol_explorer), ("jumper", pol_jumper),
                      ("our-hero", None)):
        if pol is None:
            import test_hero as T
            eng2, info = T.run(grid)
            sc = info["scores"]
        else:
            eng2 = run(pol, grid)
            sc = eng2.scores()
        print("%-9s status=%-8s turns=%-3d hp=%-4d keys=%s  demon_score=%s" % (
            name, sc["status"], sc["turns"], sc["hp"], sc["keys"], sc["demon_score"]))
