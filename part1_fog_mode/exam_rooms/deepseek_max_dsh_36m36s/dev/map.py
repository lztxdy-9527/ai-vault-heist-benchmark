"""Dungeon design + validation harness."""
import sys
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\deepseek_max\dev")
import engine as E
from engine import W, H

K1 = (20, 5)
K2 = (20, 20)
V = (35, 13)


def blank():
    g = [["EMPTY"] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if x in (0, W - 1) or y in (0, H - 1):
                g[y][x] = "T_W"
    return g


def build_grid():
    g = blank()
    # laser roof: three down-firing turrets one row above the pit ring
    for x in (1, 2, 3):
        g[10][x] = "LASER_D"
    # north ring: pits -> block movement, transparent to laser beams, bomb proof
    for x in (1, 2, 3):
        g[11][x] = "PIT"
    # east ring: titanium walls + one pit hatch (jumpable only)
    g[12][4] = "T_W"
    g[13][4] = "PIT"
    g[14][4] = "T_W"
    # south ring: titanium walls
    for x in (1, 2, 3):
        g[15][x] = "T_W"
    # escape island: reachable only by the pit-jump, sealed N/S, roofed by its
    # own turret (pit ring is laser transparent), a TNT blocks the east walk and
    # the jump; detonating it from the box opens the way.
    g[12][5] = "PIT"
    g[14][5] = "PIT"
    g[11][5] = "LASER_D"
    g[15][5] = "T_W"
    g[13][6] = "TNT"
    g[12][7] = "W"
    g[13][7] = "W"
    g[14][7] = "W"
    g[K1[1]][K1[0]] = "K1"
    g[K2[1]][K2[0]] = "K2"
    g[V[1]][V[0]] = "V"
    return g


def author_solution():
    acts = ["MOVE_R",              # (2,13) -> (3,13)
            "THROW_R",             # stone crosses the pit, detonates TNT(6,13)
            "WAIT",                # eat the turn-3 roof volley inside the box
            "JUMP_R",              # over pit hatch -> island (5,13)
            "MOVE_R", "MOVE_R"]    # -> (6,13) -> (7,13)
    acts += ["MOVE_R"] * 13        # (8,13) .. (20,13)
    acts += ["MOVE_U"] * 8         # (20,12) .. (20,5) = K1
    acts += ["MOVE_D"] * 15        # (20,6) .. (20,20) = K2
    acts += ["MOVE_R"] * 15        # (21,20) .. (35,20)
    acts += ["MOVE_U"] * 7         # (35,19) .. (35,13) = V
    return acts


TAUNT = "十二模型同场？先在我盒子里躺六年再说。"


def dungeon():
    return {"taunt": TAUNT, "grid": build_grid(), "author_solution": author_solution()}


if __name__ == "__main__":
    g = build_grid()
    ok, errs, info = E.validate_grid(g)
    print("valid:", ok, errs)
    print("spent:", info["spent"], "g:", round((3000 - info["spent"]) / 3000.0, 4),
          "inner T_W:", info["inner_tw"])
    acts = author_solution()
    print("author actions:", len(acts))
    good, msg = E.check_author_solution(g, acts)
    print("author solution:", good, msg)
    eng, cleared_at = E.run_actions(g, acts)
    print("replay:", eng.scores())
