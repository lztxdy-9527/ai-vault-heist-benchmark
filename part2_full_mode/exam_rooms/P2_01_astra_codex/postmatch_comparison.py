"""Replay the postmatch comparison offline from this directory with python -B postmatch_comparison.py."""
import ast
import hashlib
import json
import sys
from pathlib import Path
from time import monotonic

import postmatch_candidate as candidate
import referee_checks as checks
import submission as frozen
import verify_v22
from postmatch_box_regression import certified_boxes
from submission_template_v22 import TILE_COSTS


class NearestPlate(frozen.Crates):
    """Baseline that optimizes one unfilled plate at a time using the frozen push physics."""
    def plan(self, deadline):
        boxes = self.initial_boxes
        fields = self.distances(self.root, frozenset())
        choices = sorted((min((f[b] for b in boxes), default=frozen.INF), g)
                         for f, g in zip(fields, self.goals) if g not in boxes)
        for index, (distance, goal) in enumerate(choices):
            if distance >= frozen.INF or monotonic() >= deadline:
                break
            one = joint_planner().prepare(self.w, self.root, (goal,))
            remaining = len(choices) - index
            now = monotonic()
            actions = one.plan(now + (deadline - now) / remaining)
            if actions:
                return actions
        return []


joint_planner = frozen.Crates
opposite = dict(U="D", D="U", R="L", L="R")


def offset(point, direction, steps=1):
    dx, dy = checks.DIR[direction]
    return point[0] + dx * steps, point[1] + dy * steps


def certified_lanes(lanes):
    """Build an oriented box alcove and certify the entire route using only referee moves."""
    grid = checks.blank()
    for y in range(1, 25):
        grid[y][13] = "T_W"
    grid[13][13] = "P_GATE"

    def place(p, tile):
        x, y = p
        assert grid[y][x] == "EMPTY", (p, grid[y][x])
        grid[y][x] = tile

    for box, direction, side, obstacle in lanes:
        goal = offset(box, direction, 4)
        place(box, "BOX")
        place(goal, "PLATE")
        for wall in (direction, side, opposite[side]):
            place(offset(goal, wall), "T_W")
        place(offset(box, direction, 3), obstacle)

    r = checks.Referee(grid)
    proof = []

    def act(a):
        proof.append(a)
        r.act(a)
        assert r.hp == 100

    def walk(destination):
        paths = {r.p: ()}
        wave = [r.p]
        for p in wave:
            if p == destination:
                for step in paths[p]:
                    act("MOVE_" + step)
                return
            for d in checks.DIR:
                q = offset(p, d)
                if q not in paths and not r.wall(q) and q not in r.o:
                    wave.append(q)
                    paths[q] = paths[p] + (d,)
        raise AssertionError(destination)

    for box, direction, side, obstacle in lanes:
        block = offset(box, direction, 3)
        if obstacle == "TNT":
            walk(offset(block, side, 3))
            act("THROW_" + opposite[side])
        else:
            walk(offset(block, side))
            act("BOMB")
            act("MOVE_" + side)
            act("MOVE_" + side)
        assert r.t[block] == "EMPTY" and block not in r.o
        walk(offset(box, opposite[direction]))
        for _ in range(4):
            act("MOVE_" + direction)
    assert r.active()
    for tile in ("K1", "K2", "V"):
        walk(r.targets[tile])
    assert r.won and len(proof) <= 200
    return grid, proof


def certified_tunnel():
    """A single necessary crate must pass two walls inside a one-cell tunnel."""
    grid = checks.blank()
    for y in range(1, 25):
        grid[y][13] = "T_W"
    grid[13][13] = "P_GATE"
    for x in range(8, 12):
        grid[7][x] = grid[9][x] = "T_W"
    grid[8][4] = "BOX"
    grid[8][9:13] = ["W", "W", "PLATE", "T_W"]
    route = ("U"*4 + "R"*5 + "UR" + "BLL" + "RRR" + "BLL" + "D" + "L"*4 + "U" +
             "R"*7 + "L"*3 + "D"*5 + "R"*13 + "U"*8 + "D"*15 + "R"*15 + "U"*7)
    proof = ["BOMB" if d == "B" else "MOVE_" + d for d in route]
    judge = checks.Referee(grid)
    for i, action in enumerate(proof, 1):
        judge.act(action)
        assert judge.hp == 100 and judge.won == (i == len(proof))
    assert len(proof) <= 200
    return grid, proof


def holdouts():
    east = ((4, 5), "R", "D", "TNT")
    west = ((9, 20), "L", "U", "W")
    north = ((7, 16), "U", "R", "W")
    return {"north wall": [north], "west wall": [west], "east barrel": [east],
            "two separated obstructions": [west, east]}


def validate():
    source = Path("postmatch_candidate.py").read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    for n in ast.walk(tree):
        for prop in ("id", "attr", "name"):
            name = getattr(n, prop, "") or ""
            assert not name.startswith("__") and name not in (
                "eval", "exec", "getattr", "setattr", "open", "compile", "globals", "locals")
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            assert isinstance(n, ast.ImportFrom) and n.module in ("collections", "heapq", "time")
    cutoff = Path("history/CUTOFF_40m00s_04845fa1.py").read_bytes()
    assert Path("submission.py").read_bytes() == cutoff
    assert hashlib.sha256(cutoff).hexdigest() == "04845fa112cac8115a8c5897c0a64b50caa13489841ebac9c838eedf694fdd62"
    print("Candidate AST and frozen hash passed", flush=True)
    checks.entry = verify_v22.game = candidate
    checks.test_vectors()
    checks.author_check()


def play(hero, grid, name, resets=None):
    checks.entry = hero
    return checks.match(grid, name, resets)[0]


def compare_maps():
    for name, grid in (("old", frozen.dungeon_grid()), ("new", candidate.dungeon_grid())):
        for label, hero in (("joint", frozen), ("joint + demolition", candidate), ("nearest plate", frozen)):
            if label == "nearest plate":
                frozen.Crates = NearestPlate
            try:
                play(hero, grid, label + " / " + name)
            finally:
                frozen.Crates = joint_planner
    assert play(candidate, candidate.dungeon_grid(), "new map / memory reset", {2, 9, 24, 73}) == "CLEARED"


def regression():
    published = {}
    for file in ("part1_dungeons_benchmark.json", "v22_sparring_benchmarks.json"):
        published.update(json.loads(Path(file).read_text(encoding="utf-8-sig"))["dungeons"])
    for k, m in published.items():
        assert play(candidate, m["grid"], k) == "CLEARED"
    for seed in range(1, 45):
        grid, _ = certified_boxes(seed)
        assert play(candidate, grid, "warehouse " + str(seed)) == "CLEARED"
    for k in ("BENCH_STRONG", "sol", "glm"):
        assert play(candidate, published[k]["grid"], "memory reset " + k, {2, 9, 24, 73}) == "CLEARED"


def lanes(heroes):
    cases = {name: certified_lanes(spec) for name, spec in holdouts().items()}
    cases["two walls in one tunnel"] = certified_tunnel()
    for name, (grid, proof) in cases.items():
        cost = sum(TILE_COSTS[c] for row in grid[1:-1] for c in row[1:-1])
        assert cost <= 3000
        for hero, label in heroes:
            result = play(hero, grid, f"{name} / {label} (proof {len(proof)})")
            if hero is candidate:
                assert result == "CLEARED"


if __name__ == "__main__":
    requested = set(sys.argv[1:]) or {"validate", "compare", "regression", "lanes"}
    if "validate" in requested:
        validate()
    if "regression" in requested:
        regression()
    if "compare" in requested:
        compare_maps()
    if "lanes" in requested:
        lanes([(candidate, "candidate"), (frozen, "frozen")])
    if "candidate-lanes" in requested:
        lanes([(candidate, "candidate")])

