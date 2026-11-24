"""Brute-force search: shortest hero action sequence that leaves the box."""
import sys
from collections import deque
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\deepseek_max\dev")
import engine as E
import map as M

ACTIONS = ["MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT",
           "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R", "BOMB",
           "THROW_U", "THROW_D", "THROW_L", "THROW_R"]
ZONE = {(x, y) for x in (1, 2, 3) for y in (12, 13, 14)}
ISLAND = {(5, 13)}
SAFE = ZONE | ISLAND


def clone(eng):
    n = E.Engine(direct={"hero": {"x": 2, "y": 13, "hp": 100}})
    n.terrain = [row[:] for row in eng.terrain]
    n.occ = [row[:] for row in eng.occ]
    n.clues = [row[:] for row in eng.clues]
    n.mimic_clue = dict(eng.mimic_clue)
    n.bombs = [dict(b) for b in eng.bombs]
    n.next_id = eng.next_id
    n.gates_flipped = eng.gates_flipped
    n.turn = eng.turn
    n.exposed = set(eng.exposed)
    n.trap_damage = eng.trap_damage
    n.status = eng.status
    n.tnt_armed = set(eng.tnt_armed)
    n.hero = dict(eng.hero)
    n.hero["keys"] = list(eng.hero["keys"])
    n.trace = []
    n.stage = dict(eng.stage)
    n._grid = eng._grid
    return n


def key(eng):
    return (eng.hero["x"], eng.hero["y"], eng.hero["jumps"], eng.hero["throws"],
            eng.hero["bombs"], eng.hero["hp"], eng.turn % 3,
            tuple(sorted((b["x"], b["y"], b["timer"]) for b in eng.bombs)),
            tuple(sorted((x, y) for y in range(10, 17) for x in range(0, 10)
                         if eng.terrain[y][x] in ("W", "TNT", "PIT"))))


def search(max_depth=7):
    grid = M.build_grid()
    start = E.Engine(grid=grid)
    escapes = []
    q = deque([(start, [])])
    seen = {key(start)}
    while q:
        eng, path = q.popleft()
        if len(path) >= max_depth:
            continue
        for a in ACTIONS:
            n = clone(eng)
            n.play_turn(a)
            if n.status in ("DEAD", "CLEARED"):
                continue
            pos = (n.hero["x"], n.hero["y"])
            if pos not in SAFE:
                escapes.append((path + [a], pos, n.hero["hp"], n.turn - 1))
                continue
            k = key(n)
            if k in seen:
                continue
            seen.add(k)
            q.append((n, path + [a]))
    return escapes, len(seen)


if __name__ == "__main__":
    esc, n = search(max_depth=7)
    print("states explored:", n)
    print("escapes found:", len(esc))
    shortest = min((len(p) for p, *_ in esc), default=None)
    print("shortest escape length:", shortest)
    for p, pos, hp, turn in esc:
        if len(p) == shortest:
            print("   ", p, pos, "hp", hp, "turn", turn)
