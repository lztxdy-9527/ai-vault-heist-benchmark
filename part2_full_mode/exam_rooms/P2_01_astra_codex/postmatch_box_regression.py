"""Post-cutoff regression on certified warehouse puzzles, using the frozen entry."""
import hashlib
import random
from pathlib import Path
from referee_checks import DIR, Referee, adj, blank, match
from submission_template_v22 import TILE_COSTS


def certified_boxes(seed):
    rng = random.Random(seed)
    opposite = {"U": "D", "D": "U", "L": "R", "R": "L"}
    for attempt in range(300):
        grid = blank()
        for x, y in ((20, 5), (20, 20), (35, 13)):
            grid[y][x] = "EMPTY"
        for y in range(1, 25):
            grid[y][11] = "T_W"
        grid[13][11] = "P_GATE"
        for x, y, tile in ((18, 6, "K1"), (26, 21, "K2"), (35, 13, "V"),
                           (15, 13, "ONEWAY_R"), (26, 16, "ONEWAY_D"), (35, 16, "ONEWAY_U"),
                           (21, 2, "LASER_D"), (19, 10, "LASER2_R")):
            grid[y][x] = tile
        for x, y in rng.sample([(x, y) for x in range(4, 10) for y in range(7, 20)], 10):
            grid[y][x] = "T_W"
        floor = {(x, y) for x in range(1, 11) for y in range(1, 25) if grid[y][x] == "EMPTY"}
        candidates = sorted(p for p in floor if 4 <= p[0] <= 9 and 7 <= p[1] <= 19)
        goals = set(rng.sample(candidates, 3 + seed % 2))
        boxes = goals.copy()
        hero = (10, 13)
        reverse = []

        def walks(start):
            paths = {start: ""}
            queue = [start]
            for point in queue:
                for direction in DIR:
                    neighbor = adj(point, direction)
                    if neighbor in floor and neighbor not in boxes and neighbor not in paths:
                        paths[neighbor] = paths[point] + direction
                        queue.append(neighbor)
            return paths

        for _ in range(14 + seed % 6):
            paths = walks(hero)
            choices = []
            for box in sorted(boxes):
                for direction in DIR:
                    stand = adj(box, direction)
                    end = adj(stand, direction)
                    if stand not in paths or end not in floor or end in boxes:
                        continue
                    if not (3 <= stand[0] <= 9 and 5 <= stand[1] <= 21):
                        continue
                    score = rng.uniform(0, 6) + 2.5 * (box in goals)
                    score -= 0.18 * len(paths[stand]) + 5 * (stand in goals)
                    choices.append((score, box, direction, stand, end))
            if not choices:
                break
            _, box, direction, stand, end = max(choices)
            reverse.extend(paths[stand] + direction)
            boxes.remove(box)
            boxes.add(stand)
            hero = end
        if boxes & goals or any(x <= 3 and 12 <= y <= 14 for x, y in boxes):
            continue
        paths = walks(hero)
        if (2, 13) not in paths:
            continue
        reverse.extend(paths[2, 13])
        proof = ["MOVE_" + opposite[d] for d in reversed(reverse)]
        if len(proof) > 141:
            continue
        for x, y in boxes:
            grid[y][x] = "BOX"
        for x, y in goals:
            grid[y][x] = "PLATE"
        judge = Referee(grid)
        for a in proof:
            judge.act(a)
        if not judge.active() or judge.p != (10, 13):
            continue
        suffix = "R"*8 + "U"*7 + "R"*8 + "D"*15 + "R"*9 + "U"*8
        ok = True
        for direction in suffix:
            p = judge.p
            q = adj(p, direction)
            for _ in range(12):
                tick = judge.turn
                rays, _ = judge.rays()
                judge.turn += 1
                following, _ = judge.rays()
                judge.turn = tick
                if (not any({p, q} & beam for beam in rays.values())
                        and not any(q in beam for beam in following.values())):
                    break
                if any(p in beam for beam in rays.values()):
                    ok = False
                    break
                judge.act("WAIT")
                proof.append("WAIT")
            if not ok:
                break
            judge.act("MOVE_" + direction)
            proof.append("MOVE_" + direction)
        if ok and judge.won and judge.hp > 0 and len(proof) <= 200:
            assert sum(TILE_COSTS[t] for row in grid[1:-1] for t in row[1:-1]) <= 3000
            assert len(boxes) == len(goals) <= 4 and len(goals) >= 1
            for first in ("MOVE_L", "MOVE_R"):
                spawn = Referee(grid)
                for action in (first, "WAIT", "WAIT", "WAIT"):
                    spawn.act(action)
                assert spawn.damage == 0 and spawn.hp == 100
            return grid, proof
    raise AssertionError(("no certificate generated", seed))


def main():
    cutoff = Path("history/CUTOFF_40m00s_04845fa1.py").read_bytes()
    assert hashlib.sha256(cutoff).hexdigest() == "04845fa112cac8115a8c5897c0a64b50caa13489841ebac9c838eedf694fdd62"
    assert Path("submission.py").read_bytes() == cutoff
    successes = 0
    for seed in range(1, 13):
        grid, proof = certified_boxes(seed)
        status, _, _ = match(grid, "seed " + str(seed) + ", certificate " + str(len(proof)))
        successes += status == "CLEARED"
    print("certified box regressions", successes, "/ 12")


if __name__ == "__main__":
    main()

