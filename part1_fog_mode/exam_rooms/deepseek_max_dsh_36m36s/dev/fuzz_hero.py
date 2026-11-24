"""Fuzz: run the hero policy over many random LEGAL dungeons."""
import random
import sys
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\deepseek_max\dev")
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\deepseek_max")
import engine as E
import submission as S
import test_hero as T

QUOTA = {
    "T_W": 120, "MIRROR_NE": 30, "MIRROR_SE": 30, "MIRROR_SW": 30, "MIRROR_NW": 30,
    "SPRING_U": 20, "SPRING_D": 20, "SPRING_L": 20, "SPRING_R": 20,
    "LASER_U": 12, "LASER_D": 12, "LASER_L": 12, "LASER_R": 12,
    "CRACK": 40, "SWITCH": 6, "R_GATE": 16, "B_GATE": 16, "TNT": 12,
    "BOX": 4, "HEAL": 4, "MIMIC": 4,
}
GROUP = {
    "MIRROR": 30, "SPRING": 20, "LASER": 12, "GATE": 16,
}
COST = {
    "EMPTY": 0, "K1": 0, "K2": 0, "V": 0, "W": 5, "T_W": 25, "ICE": 10,
    "MIRROR_NE": 25, "MIRROR_SE": 25, "MIRROR_SW": 25, "MIRROR_NW": 25,
    "SPRING_U": 35, "SPRING_D": 35, "SPRING_L": 35, "SPRING_R": 35,
    "PIT": 40, "LASER_U": 75, "LASER_D": 75, "LASER_L": 75, "LASER_R": 75,
    "CRACK": 20, "SWITCH": 30, "R_GATE": 20, "B_GATE": 20, "TNT": 40,
    "BOX": 30, "HEAL": 30, "MIMIC": 60,
}
POOL = (["W"] * 6 + ["T_W"] * 2 + ["PIT"] * 6 + ["ICE"] * 4 + ["MIRROR_SE"] * 2 +
        ["MIRROR_NW"] * 2 + ["SPRING_R"] * 1 + ["SPRING_D"] * 1 + ["LASER_D"] * 2 +
        ["LASER_R"] * 2 + ["CRACK"] * 4 + ["TNT"] * 1 + ["SWITCH"] * 1 + ["HEAL"] * 1 +
        ["EMPTY"] * 10)


def rand_map(rng, density=0.22, want_mimic=2):
    g = T.blank()
    budget = 3000
    used = {}
    grp = {}
    for y in range(1, 25):
        for x in range(1, 39):
            if 1 <= x <= 3 and 12 <= y <= 14:
                continue
            if rng.random() > density:
                continue
            tile = rng.choice(POOL)
            c = COST[tile]
            if c > budget:
                continue
            if tile in QUOTA and used.get(tile, 0) >= QUOTA[tile]:
                continue
            gk = None
            if tile.startswith("MIRROR"):
                gk = "MIRROR"
            elif tile.startswith("SPRING"):
                gk = "SPRING"
            elif tile.startswith("LASER"):
                gk = "LASER"
            elif tile.endswith("_GATE"):
                gk = "GATE"
            if gk is not None and grp.get(gk, 0) >= GROUP[gk]:
                continue
            g[y][x] = tile
            budget -= c
            used[tile] = used.get(tile, 0) + 1
            if gk:
                grp[gk] = grp.get(gk, 0) + 1
    k1 = (rng.randint(12, 34), rng.randint(2, 10))
    k2 = (rng.randint(12, 34), rng.randint(15, 23))
    for _ in range(80):
        if abs(k1[0] - k2[0]) + abs(k1[1] - k2[1]) >= 12:
            break
        k2 = (rng.randint(12, 34), rng.randint(15, 23))
    v = (rng.randint(33, 37), rng.randint(4, 21))
    for (x, y) in (k1, k2, v):
        g[y][x] = "EMPTY"
    g[k1[1]][k1[0]] = "K1"
    g[k2[1]][k2[0]] = "K2"
    g[v[1]][v[0]] = "V"
    placed = 0
    for _ in range(60):
        if placed >= want_mimic:
            break
        x = rng.randint(4, 36)
        y = rng.randint(3, 22)
        if g[y][x] != "EMPTY":
            continue
        ok = False
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < 40 and 0 <= ny < 26 and g[ny][nx] == "EMPTY":
                ok = True
                break
        if ok and budget >= 60:
            g[y][x] = "MIMIC"
            placed += 1
            budget -= 60
    try:
        E.Engine(grid=g)
    except Exception:
        return None
    return g


def main(n=40, seed=1, verbose=False):
    rng = random.Random(seed)
    rows = []
    skipped = 0
    for i in range(n):
        g = rand_map(rng, density=rng.choice((0.14, 0.20, 0.26)))
        if g is None:
            skipped += 1
            continue
        eng, info2 = T.run(g)
        sc = info2["scores"]
        rows.append(sc)
        if verbose:
            print("%2d %-8s turns=%-3d hp=%-4d keys=%s hero=%6.1f D=%3.0f g=%.2f err=%d" % (
                i, sc["status"], sc["turns"], sc["hp"], sc["keys"], sc["hero_score"],
                sc["D"], sc["g"] or 0, info2["errors"]))
    n2 = len(rows)
    cleared = [r for r in rows if r["status"] == "CLEARED"]
    print("\n--- %d maps (skipped %d) ---" % (n2, skipped))
    print("clear rate: %d/%d = %.0f%%" % (len(cleared), n2, 100.0 * len(cleared) / max(1, n2)))
    print("avg hero score: %.1f" % (sum(r["hero_score"] for r in rows) / max(1, n2)))
    if cleared:
        print("avg clear turns: %.1f  avg hp: %.1f" % (
            sum(r["turns"] for r in cleared) / len(cleared), sum(r["hp"] for r in cleared) / len(cleared)))
    fails = [r for r in rows if r["status"] != "CLEARED"]
    if fails:
        print("failures:", [(r["status"], r["turns"], r["hp"], r["keys"]) for r in fails][:14])


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    main(n, verbose=True)
