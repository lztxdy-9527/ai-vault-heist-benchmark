"""Hero policy test harness: drives our decide_action through the local engine."""
import sys
import time
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\deepseek_max\dev")
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\deepseek_max")
import engine as E
import submission as S


def run(grid, mode="BLIND", verbose=False, max_turns=240):
    eng = E.Engine(grid=grid)
    memory = {}
    times = []
    n_err = 0
    acts = []
    for _ in range(max_turns):
        if eng.status != "ALIVE":
            break
        state = E.make_state(eng, mode)
        t0 = time.perf_counter()
        try:
            act = S._decide(state, memory)
        except Exception as exc:
            n_err += 1
            act = "WAIT"
            if verbose:
                print("  !! exception:", repr(exc))
        times.append(time.perf_counter() - t0)
        if act not in S.VALID_ACTIONS:
            act = "WAIT"
        acts.append(act)
        if verbose:
            print("  t%-3d %-8s pos=%s hp=%-4d keys=%s" % (
                eng.turn, act, (eng.hero["x"], eng.hero["y"]), eng.hero["hp"], eng.hero["keys"]))
        eng.play_turn(act)
    return eng, {
        "acts": acts,
        "max_ms": max(times) * 1000 if times else 0,
        "avg_ms": (sum(times) / len(times) * 1000) if times else 0,
        "errors": n_err,
        "scores": eng.scores(),
    }


def show(name, grid, verbose=False):
    eng, info = run(grid, verbose=verbose)
    sc = info["scores"]
    print("%-26s status=%-8s turns=%-3d hp=%-4d keys=%s P=%.2f D=%.0f hero=%.1f demon=%s  max=%.1fms avg=%.2fms err=%d" % (
        name, sc["status"], sc["turns"], sc["hp"], sc["keys"], sc["P"], sc["D"],
        sc["hero_score"], sc["demon_score"], info["max_ms"], info["avg_ms"], info["errors"]))
    return eng, info


def blank():
    g = [["EMPTY"] * 40 for _ in range(26)]
    for y in range(26):
        for x in range(40):
            if x in (0, 39) or y in (0, 25):
                g[y][x] = "T_W"
    return g


def map_open():
    g = blank()
    g[5][20] = "K1"
    g[20][20] = "K2"
    g[13][35] = "V"
    return g


def map_pit_maze():
    g = blank()
    # dense pits with a snaking safe corridor
    for y in range(1, 25):
        for x in range(1, 39):
            if (x * 7 + y * 3) % 11 == 0:
                g[y][x] = "PIT"
    g[5][20] = "K1"
    g[20][20] = "K2"
    g[13][35] = "V"
    return g


def map_lasers_ice():
    g = blank()
    for x in (8, 14, 22, 28):
        g[6][x] = "LASER_D"
        g[19][x] = "LASER_U"
    for x in range(9, 14):
        g[10][x] = "ICE"
    g[8][17] = "MIRROR_SE"
    g[5][20] = "K1"
    g[20][20] = "K2"
    g[13][35] = "V"
    return g


def map_typical_llm():
    """imitation of a strong-LLM style dungeon: walls, pits, lasers, chests, tnt"""
    g = blank()
    g[5][20] = "K1"
    g[20][20] = "K2"
    g[13][35] = "V"
    for x in range(8, 33):
        g[8][x] = "W"
        g[18][x] = "W"
    for x in range(8, 33, 2):
        g[8][x] = "PIT"
        g[18][x] = "PIT"
    for y in range(9, 18):
        g[y][8] = "W"
        g[y][32] = "W"
    g[11][12] = "LASER_R"
    g[15][26] = "LASER_L"
    g[12][16] = "HEAL"
    g[12][17] = "MIMIC"
    g[14][24] = "MIMIC"
    g[11][21] = "TNT"
    g[13][13] = "CRACK"
    g[13][14] = "CRACK"
    g[10][3] = "BOX"
    g[9][30] = "SWITCH"
    g[10][30] = "R_GATE"
    g[11][30] = "B_GATE"
    return g


def map_sealed_box():
    """our own dungeon (hero is expected to die here - the box is lethal)"""
    return S.build_dungeon()["grid"]


def map_ring_box():
    """simpler sealed box: spawn ringed by walls, keys outside"""
    g = blank()
    for x in (1, 2, 3):
        g[11][x] = "W"
        g[15][x] = "W"
    g[12][1] = "W"
    g[12][2] = "W"
    g[12][3] = "W"
    g[14][1] = "W"
    g[14][2] = "W"
    g[14][3] = "W"
    g[13][4] = "W"
    g[5][20] = "K1"
    g[20][20] = "K2"
    g[13][35] = "V"
    return g


if __name__ == "__main__":
    show("open field", map_open())
    show("pit maze", map_pit_maze())
    show("lasers+ice", map_lasers_ice())
    show("typical llm", map_typical_llm())
    show("our dungeon", map_sealed_box())
    show("walled box", map_ring_box())
