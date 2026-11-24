import sys, random
sys.path.insert(0, r"<LOCAL_USER_HOME>\.gemini\antigravity\brain\b070b56c-8bd8-4bca-a493-7b8dd9087240\scratch")
from harness import *

def blank():
    g = [["T_W" if (x in (0, 39) or y in (0, 25)) else "EMPTY" for x in range(40)] for y in range(26)]
    g[5][20] = "K1"; g[20][20] = "K2"; g[13][35] = "V"
    return g

maps = {}
maps["blank"] = blank()
# maze-ish: vertical walls with gaps
g = blank()
for x in (8, 16, 24, 30):
    gap = random.Random(x).randint(2, 23)
    for y in range(1, 25):
        if abs(y - gap) > 0 and g[y][x] == "EMPTY":
            g[y][x] = "W"
maps["walls"] = g
# ice and pits
g = blank()
for x in range(6, 30):
    g[13][x] = "ICE"
g[13][30] = "PIT"
for y in range(3, 9):
    g[y][18] = "PIT"
g[6][22] = "MIMIC"; g[6][19] = "HEAL"
maps["icepit"] = g
# lasers crossing corridor
g = blank()
for y in range(1, 25):
    if y not in (12, 13, 14):
        g[y][10] = "T_W" if y < 8 or y > 18 else "W"
g[11][12] = "LASER_D"
g[15][14] = "LASER_U"
g[16][28] = "LASER_L"
maps["lasers"] = g
# sealed key needing bomb
g = blank()
for dx in (-1, 0, 1):
    for dy in (-1, 0, 1):
        if dx or dy:
            g[5 + dy][20 + dx] = "W"
maps["sealed"] = g
# pit moat needing jump
g = blank()
for y in range(1, 25):
    g[y][10] = "PIT"
maps["moat"] = g
# spring + portal
g = blank()
for y in range(1, 25):
    g[y][10] = "T_W" if y % 2 else "W"
g[13][9] = "PORTAL_1A"; g[13][12] = "PORTAL_1B"
for y in range(1, 25):
    if y != 13: g[y][10] = "T_W" if y < 13 else "W"
g[13][10] = "W"
maps["portal"] = g
maps["mine"] = S._design()
# gates + switch: K1 behind red gate, switch nearby
g = blank()
for dx in (-1, 0, 1):
    for dy in (-1, 0, 1):
        if dx or dy:
            g[5 + dy][20 + dx] = "T_W"
g[6][20] = "R_GATE"
g[9][15] = "SWITCH"
maps["gate"] = g
# mimic corridor & cracks & springs
g = blank()
for y in range(1, 25):
    if y != 13:
        g[y][12] = "T_W" if abs(y - 13) < 10 else "W"
g[13][12] = "CRACK"
g[13][14] = "MIMIC"
g[12][14] = "W"; g[14][14] = "W"
g[13][16] = "SPRING_R"
g[13][20] = "PIT"
maps["mixed"] = g
# random clutter maps
rnd = random.Random(7)
for k in range(6):
    g = blank()
    tiles = ["W"] * 30 + ["PIT"] * 10 + ["ICE"] * 10 + ["CRACK"] * 3 + ["MIRROR_NE", "MIRROR_SW", "SPRING_U", "SPRING_R", "TNT", "BOX", "MIMIC", "HEAL"]
    for _ in range(330):
        x, y = rnd.randint(1, 38), rnd.randint(1, 24)
        if 1 <= x <= 3 and 12 <= y <= 14: continue
        if g[y][x] != "EMPTY": continue
        g[y][x] = rnd.choice(tiles)
    lz = 0
    for _ in range(8):
        x, y = rnd.randint(5, 37), rnd.randint(1, 24)
        if g[y][x] == "EMPTY":
            g[y][x] = rnd.choice(["LASER_U", "LASER_D", "LASER_L", "LASER_R"])
    # fix counts
    cnt = {}
    for y in range(26):
        for x in range(40):
            c = g[y][x]
            cnt[c] = cnt.get(c, 0) + 1
            lim = {"TNT": 12, "BOX": 4, "MIMIC": 4, "HEAL": 4, "CRACK": 40}.get(c)
            if lim and cnt[c] > lim: g[y][x] = "EMPTY"
    if S.bind_clues(g) is None:
        for y in range(26):
            for x in range(40):
                if g[y][x] == "MIMIC": g[y][x] = "EMPTY"
    maps["rand%d" % k] = g

names = sys.argv[1:] or list(maps)
for n in names:
    try:
        validate(maps[n])
    except AssertionError as e:
        print(n, "invalid", e)
    res = run_hero(maps[n], S.decide_action, verbose=("-v" in n))
    print(n, res[0], "turn", res[1], "hp", res[2], "keys", res[3], "worst %.3f" % res[4], "trap", res[6])
