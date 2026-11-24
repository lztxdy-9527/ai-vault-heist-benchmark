import sys
sys.path.insert(0, r"<LOCAL_USER_HOME>\.gemini\antigravity\brain\b070b56c-8bd8-4bca-a493-7b8dd9087240\scratch")
from harness import *

def blank():
    return [["T_W" if (x in (0, 39) or y in (0, 25)) else "EMPTY" for x in range(40)] for y in range(26)]

def G(tiles, hx, hy, turn=1, hp=100, keys=(False, False)):
    g = blank()
    for (x, y), t in tiles.items():
        g[y][x] = t
    game = S.make_game(g)
    game.hx, game.hy, game.turn, game.hp = hx, hy, turn, hp
    game.k1, game.k2 = keys
    return game

# GV2
g = G({(6, 10): "CRACK"}, 5, 10); g.O[10][6] = "BOX"
g.full_turn("MOVE_R"); print("GV2", g.O[10][7], g.T[10][6], (g.hx, g.hy), g.hp, g.trap, g.status)
# GV3
g = G({(5, 10): "SPRING_R", (7, 10): "PIT", (8, 10): "W"}, 4, 10)
g.act("MOVE_R"); print("GV3", sorted(g.exposed), (g.hx, g.hy), g.hp, g.status)
# GV4
g = G({(5, 10): "PORTAL_1A", (10, 10): "PORTAL_1B", (11, 10): "PORTAL_2A", (20, 10): "PORTAL_2B", (21, 10): "ICE"}, 4, 10)
g.full_turn("MOVE_R"); print("GV4", (g.hx, g.hy), g.hp, g.status)
# GV5
g = G({(5, 8): "LASER_R", (8, 9): "LASER_D"}, 8, 12, turn=3); g.O[8][8] = "TNT"
g.full_turn("BOMB"); print("GV5", g.bombs, g.T[9][8], g.hp, g.trap, g.status)
# GV7
g = G({(6, 10): "PIT", (8, 10): "MIRROR_SE", (8, 11): "PIT", (8, 13): "ICE", (8, 14): "ICE", (8, 15): "SWITCH"}, 5, 10)
g.full_turn("THROW_R"); print("GV7", g.throws, g.gates, (g.hx, g.hy), g.status)
# GV8
g = G({(35, 5): "LASER_D", (35, 13): "V"}, 34, 13, turn=240, hp=20, keys=(True, True))
g.full_turn("MOVE_R"); print("GV8", (g.hx, g.hy), g.hp, g.status)
# GV1
gg = blank()
for (x, y, t) in [(20, 5, "K1"), (20, 20, "K2"), (35, 13, "V"), (6, 6, "T_W"), (7, 6, "T_W"), (8, 8, "PORTAL_1A"), (25, 8, "PORTAL_1B"), (10, 10, "MIMIC")]:
    gg[y][x] = t
print("GV1", validate(gg)[0], S.bind_clues(gg))
