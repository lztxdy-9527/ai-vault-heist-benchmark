import sys, random
sys.path.insert(0, r"<LOCAL_USER_HOME>\.gemini\antigravity\brain\b070b56c-8bd8-4bca-a493-7b8dd9087240\scratch")
from harness import *

def blank():
    g = [["T_W" if (x in (0, 39) or y in (0, 25)) else "EMPTY" for x in range(40)] for y in range(26)]
    g[5][20] = "K1"; g[20][20] = "K2"; g[13][35] = "V"
    return g

rnd = random.Random(11)
res = []
for k in range(8):
    g = blank()
    pool = ["ICE"] * 40 + ["MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW"] * 4 + ["PIT"] * 12 + ["W"] * 15 + ["SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R"] * 2 + ["R_GATE", "B_GATE", "CRACK"] * 2
    dens = 0.25 + 0.06 * k
    for y in range(1, 25):
        for x in range(1, 39):
            if 1 <= x <= 3 and 12 <= y <= 14: continue
            if g[y][x] != "EMPTY": continue
            if rnd.random() < dens:
                g[y][x] = rnd.choice(pool)
    g[16][8] = "SWITCH"; g[8][28] = "SWITCH"
    for i in range(6):
        x, y = rnd.randint(6, 37), rnd.randint(1, 24)
        if g[y][x] == "EMPTY": g[y][x] = rnd.choice(["LASER_U", "LASER_D", "LASER_L", "LASER_R"])
    st, t, hp, keys, worst, acts, trap = run_hero(g, S.decide_action)
    res.append((k, st, t, hp, keys, round(worst, 3)))
    print(k, st, t, hp, keys, "worst %.3f" % worst, flush=True)
