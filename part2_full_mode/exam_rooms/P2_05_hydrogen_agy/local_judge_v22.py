"""Local v2.2 FULL-mode reference engine, validator, and golden-vector verifier."""

import ast
import collections
import copy
import json
import os

GRID_WIDTH = 40
GRID_HEIGHT = 26
MAX_BUDGET = 3000
MAX_TURNS = 240
MAX_AUTHOR_STEPS = 200
SPAWN_POS = (2, 13)

VALID_ACTIONS = (
    "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R",
    "WAIT",
    "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
    "THROW_U", "THROW_D", "THROW_L", "THROW_R",
    "BOMB",
)

DIRECTIONS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}

MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}

LASER1_DIRS = {"LASER_U": "U", "LASER_D": "D", "LASER_L": "L", "LASER_R": "R"}
LASER2_DIRS = {"LASER2_U": "U", "LASER2_D": "D", "LASER2_L": "L", "LASER2_R": "R"}
ALL_LASER_DIRS = {**LASER1_DIRS, **LASER2_DIRS}
SPRING_DIRS = {"SPRING_U": "U", "SPRING_D": "D", "SPRING_L": "L", "SPRING_R": "R"}
ONEWAY_DIRS = {"ONEWAY_U": "U", "ONEWAY_D": "D", "ONEWAY_L": "L", "ONEWAY_R": "R"}
PORTAL_PAIRS = {
    "PORTAL_1A": "PORTAL_1B", "PORTAL_1B": "PORTAL_1A",
    "PORTAL_2A": "PORTAL_2B", "PORTAL_2B": "PORTAL_2A",
}

TILE_COSTS = {
    "EMPTY": 0, "K1": 0, "K2": 0, "V": 0,
    "W": 5, "T_W": 25, "ICE": 10,
    "MIRROR_NE": 25, "MIRROR_SE": 25, "MIRROR_SW": 25, "MIRROR_NW": 25,
    "SPRING_U": 35, "SPRING_D": 35, "SPRING_L": 35, "SPRING_R": 35,
    "PIT": 40,
    "LASER_U": 75, "LASER_D": 75, "LASER_L": 75, "LASER_R": 75,
    "LASER2_U": 90, "LASER2_D": 90, "LASER2_L": 90, "LASER2_R": 90,
    "CRACK": 20, "SWITCH": 30, "R_GATE": 20, "B_GATE": 20,
    "PLATE": 45, "P_GATE": 30,
    "ONEWAY_U": 30, "ONEWAY_D": 30, "ONEWAY_L": 30, "ONEWAY_R": 30,
    "TNT": 40, "BOX": 30, "HEAL": 30, "MIMIC": 60,
    "PORTAL_1A": 40, "PORTAL_1B": 40, "PORTAL_2A": 40, "PORTAL_2B": 40,
}

BANNED_MODULES = {
    "os", "sys", "io", "pathlib", "shutil", "subprocess", "multiprocessing",
    "threading", "socket", "urllib", "requests", "http", "ftplib", "smtplib",
    "pickle", "marshal", "ctypes", "inspect", "importlib", "pkgutil",
    "tempfile", "glob", "sqlite3", "asyncio", "concurrent",
}
BANNED_NAMES = {"open", "eval", "exec", "compile", "__import__", "getattr", "setattr", "delattr", "globals", "locals", "vars", "dir", "input", "breakpoint"}
BANNED_ATTRS = {"__class__", "__bases__", "__subclasses__", "__mro__", "__globals__", "__code__", "__builtins__", "__dict__", "__getattribute__"}


def check_ast_safety(source: str) -> list[str]:
    issues = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in BANNED_MODULES:
                    issues.append(f"Banned import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            root = mod.split(".")[0]
            if root in BANNED_MODULES:
                issues.append(f"Banned import from: {mod}")
            if mod.startswith("numpy.") and any(s in mod for s in ("ctypeslib", "f2py", "testing", "load", "save")):
                issues.append(f"Banned numpy IO: {mod}")
            if mod.startswith("networkx") and any((a.name.startswith("read_") or a.name.startswith("write_")) for a in node.names):
                issues.append(f"Banned nx IO: {mod}")
        elif isinstance(node, ast.Name):
            if node.id in BANNED_NAMES:
                issues.append(f"Banned name: {node.id}")
        elif isinstance(node, ast.Attribute):
            if node.attr in BANNED_ATTRS or (node.attr.startswith("__") and node.attr.endswith("__") and node.attr not in ("__init__", "__name__", "__main__", "__doc__")):
                issues.append(f"Banned attr: {node.attr}")
    return issues


def in_bounds(x: int, y: int) -> bool:
    return 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT


def make_empty_grid() -> list[list[str]]:
    return [
        ["T_W" if (x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1) else "EMPTY" for x in range(GRID_WIDTH)]
        for y in range(GRID_HEIGHT)
    ]


def decode_grid_only(raw_grid: list[list[str]]) -> dict:
    """Decode a 26x40 grid without running author_solution or spawn checks (for benchmarks)."""
    if not isinstance(raw_grid, list) or len(raw_grid) != GRID_HEIGHT:
        raise ValueError("grid must have 26 rows")
    terrain = [["EMPTY"] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    occupant = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    clues = [[False] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    mimic_to_clue = {}
    portals = {}
    targets = {}
    plate_coords = []
    counts = collections.Counter()
    spent_gold = 0

    for y in range(GRID_HEIGHT):
        row = raw_grid[y]
        if not isinstance(row, list) or len(row) != GRID_WIDTH:
            raise ValueError(f"row {y} invalid len")
        for x in range(GRID_WIDTH):
            tile = row[x]
            if tile not in TILE_COSTS:
                raise ValueError(f"Unknown tile {tile} at ({x},{y})")
            is_border = (x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1)
            if is_border:
                if tile != "T_W":
                    raise ValueError(f"Border ({x},{y}) must be T_W, got {tile}")
                terrain[y][x] = "T_W"
                continue
            if 1 <= x <= 3 and 12 <= y <= 14 and tile != "EMPTY":
                raise ValueError(f"Spawn zone ({x},{y}) must be EMPTY, got {tile}")
            counts[tile] += 1
            spent_gold += TILE_COSTS[tile]
            if tile in ("BOX", "TNT"):
                terrain[y][x] = "EMPTY"
                occupant[y][x] = tile
            else:
                terrain[y][x] = tile
            if tile == "PLATE":
                plate_coords.append((x, y))
            elif tile in ("K1", "K2", "V"):
                if tile in targets:
                    raise ValueError(f"Duplicate target {tile}")
                targets[tile] = (x, y)
            elif tile in PORTAL_PAIRS:
                if tile in portals:
                    raise ValueError(f"Duplicate portal {tile}")
                portals[tile] = (x, y)

    if spent_gold > MAX_BUDGET:
        raise ValueError(f"Budget exceeded: {spent_gold} > {MAX_BUDGET}")
    if set(targets.keys()) != {"K1", "K2", "V"}:
        raise ValueError(f"Missing targets: {targets.keys()}")
    k1, k2, v = targets["K1"], targets["K2"], targets["V"]
    if not (12 <= k1[0] <= 34 and 2 <= k1[1] <= 10):
        raise ValueError(f"K1 out of range: {k1}")
    if not (12 <= k2[0] <= 34 and 15 <= k2[1] <= 23):
        raise ValueError(f"K2 out of range: {k2}")
    if abs(k1[0] - k2[0]) + abs(k1[1] - k2[1]) < 12:
        raise ValueError(f"K1-K2 Manhattan dist < 12: {k1}, {k2}")
    if not (33 <= v[0] <= 37 and 4 <= v[1] <= 21):
        raise ValueError(f"V out of range: {v}")

    # Quotas
    if counts["T_W"] > 120: raise ValueError("T_W > 120")
    if sum(counts[k] for k in MIRROR_MAP) > 30: raise ValueError("MIRROR > 30")
    if sum(counts[k] for k in SPRING_DIRS) > 20: raise ValueError("SPRING > 20")
    if sum(counts[k] for k in ALL_LASER_DIRS) > 12: raise ValueError("LASER+LASER2 > 12")
    if counts["CRACK"] > 40: raise ValueError("CRACK > 40")
    if counts["SWITCH"] > 6: raise ValueError("SWITCH > 6")
    if counts["R_GATE"] + counts["B_GATE"] > 16: raise ValueError("R_GATE+B_GATE > 16")
    if counts["PLATE"] > 4: raise ValueError("PLATE > 4")
    if counts["P_GATE"] > 8: raise ValueError("P_GATE > 8")
    if counts["P_GATE"] > 0 and not (1 <= counts["PLATE"] <= counts["BOX"]):
        raise ValueError("P_GATE requires 1 <= PLATE <= BOX")
    if sum(counts[k] for k in ONEWAY_DIRS) > 12: raise ValueError("ONEWAY > 12")
    if counts["TNT"] > 12: raise ValueError("TNT > 12")
    if counts["BOX"] > 6: raise ValueError("BOX > 6")
    if counts["HEAL"] > 4: raise ValueError("HEAL > 4")
    if counts["MIMIC"] > 4: raise ValueError("MIMIC > 4")
    for p_num in ("1", "2"):
        ca, cb = f"PORTAL_{p_num}A" in portals, f"PORTAL_{p_num}B" in portals
        if ca != cb:
            raise ValueError(f"Unpaired portal {p_num}")

    # Deterministic MIMIC clues (if MIMIC has valid neighbor; choose first empty/walkable or deterministic neighbor)
    for y in range(1, GRID_HEIGHT - 1):
        for x in range(1, GRID_WIDTH - 1):
            if terrain[y][x] == "MIMIC":
                cands = []
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = x + dx, y + dy
                    if in_bounds(nx, ny):
                        cands.append((nx, ny))
                if cands:
                    cx, cy = cands[0]
                    clues[cy][cx] = True
                    mimic_to_clue[(x, y)] = (cx, cy)

    return {
        "terrain": terrain,
        "occupant": occupant,
        "clues": clues,
        "mimic_to_clue": mimic_to_clue,
        "portals": portals,
        "targets": targets,
        "plate_coords": plate_coords,
        "spent_gold": spent_gold,
        "counts": counts,
    }


def validate_dungeon(dungeon: dict, check_spawn_4turn: bool = True, check_author: bool = True) -> dict:
    if not isinstance(dungeon, dict):
        raise ValueError("build_dungeon must return dict")
    taunt = dungeon.get("taunt", "")
    if not isinstance(taunt, str) or len(taunt) > 80:
        raise ValueError("taunt invalid")
    decoded = decode_grid_only(dungeon["grid"])

    if check_spawn_4turn:
        ok_t1 = set()
        acts = ("WAIT", "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R")
        for a1 in acts:
            e1 = GameEngineV22(decoded)
            e1.step(a1)
            if e1.status in ("ALIVE", "CLEARED") and e1.trap_damage == 0.0 and (e1.hx, e1.hy) not in ok_t1:
                pos1 = (e1.hx, e1.hy)
                # Verify at least one 0-damage sequence through Turn 4
                survived_t4 = False
                for a2 in acts:
                    e2 = copy.deepcopy(e1)
                    e2.step(a2)
                    if e2.status not in ("ALIVE", "CLEARED") or e2.trap_damage > 0: continue
                    for a3 in acts:
                        e3 = copy.deepcopy(e2)
                        e3.step(a3)
                        if e3.status not in ("ALIVE", "CLEARED") or e3.trap_damage > 0: continue
                        for a4 in acts:
                            e4 = copy.deepcopy(e3)
                            e4.step(a4)
                            if e4.status in ("ALIVE", "CLEARED") and e4.trap_damage == 0:
                                survived_t4 = True
                                break
                        if survived_t4: break
                    if survived_t4: break
                if survived_t4:
                    ok_t1.add(pos1)
        if len(ok_t1) < 2:
            raise ValueError(f"Spawn 4-turn check failed: only {len(ok_t1)} safe T1 positions: {ok_t1}")

    if check_author:
        sol = dungeon.get("author_solution")
        if not isinstance(sol, list) or not (1 <= len(sol) <= MAX_AUTHOR_STEPS):
            raise ValueError(f"author_solution len invalid: {len(sol) if isinstance(sol, list) else type(sol)}")
        eng = GameEngineV22(decoded)
        for i, act in enumerate(sol):
            if act not in VALID_ACTIONS:
                raise ValueError(f"Invalid author action {act} at {i}")
            eng.step(act)
            if i < len(sol) - 1 and eng.status != "ALIVE":
                raise ValueError(f"Author ended early at step {i}: {eng.status}")
        if eng.status != "CLEARED" or eng.hp <= 0:
            raise ValueError(f"Author did not clear alive: {eng.status}, hp={eng.hp}")

    return decoded


class GameEngineV22:
    def __init__(self, decoded: dict):
        self.spent_gold = decoded["spent_gold"]
        self.terrain = copy.deepcopy(decoded["terrain"])
        self.occupant = copy.deepcopy(decoded["occupant"])
        self.clues = copy.deepcopy(decoded["clues"])
        self.mimic_to_clue = dict(decoded["mimic_to_clue"])
        self.portals = dict(decoded["portals"])
        self.targets = dict(decoded["targets"])
        self.plate_coords = list(decoded["plate_coords"])

        self.hx, self.hy = SPAWN_POS
        self.hp = 100
        self.has_k1 = False
        self.has_k2 = False
        self.jumps = 3
        self.throws = 3
        self.bombs_left = 2
        self.gates_flipped = False
        self.bombs = []
        self.next_bomb_id = 1
        self.turn = 0
        self.status = "ALIVE"
        self.trap_damage = 0.0

        self.stage_k = 0
        self.d0 = self._dist_to_next(self.hx, self.hy)
        self.dmin = self.d0

    def is_plates_active(self) -> bool:
        return bool(self.plate_coords) and all(self.occupant[y][x] == "BOX" for x, y in self.plate_coords)

    def _dist_to_next(self, x: int, y: int) -> int:
        cands = []
        if not self.has_k1:
            cands.append(abs(x - self.targets["K1"][0]) + abs(y - self.targets["K1"][1]))
        if not self.has_k2:
            cands.append(abs(x - self.targets["K2"][0]) + abs(y - self.targets["K2"][1]))
        if not cands:
            cands.append(abs(x - self.targets["V"][0]) + abs(y - self.targets["V"][1]))
        return min(cands)

    def _update_progress(self):
        new_k = (1 if self.has_k1 else 0) + (1 if self.has_k2 else 0)
        if new_k > self.stage_k:
            self.stage_k = new_k
            self.d0 = self._dist_to_next(self.hx, self.hy)
            self.dmin = self.d0
        else:
            d = self._dist_to_next(self.hx, self.hy)
            if d < self.dmin:
                self.dmin = d

    def is_high_wall(self, x: int, y: int) -> bool:
        if not in_bounds(x, y):
            return True
        t = self.terrain[y][x]
        if t in ("W", "T_W") or t in ALL_LASER_DIRS:
            return True
        if t == "R_GATE" and not self.gates_flipped:
            return True
        if t == "B_GATE" and self.gates_flipped:
            return True
        if t == "P_GATE" and not self.is_plates_active():
            return True
        return False

    def blocks_oneway(self, x: int, y: int, d: str) -> bool:
        if not in_bounds(x, y):
            return False
        t = self.terrain[y][x]
        return t in ONEWAY_DIRS and d != ONEWAY_DIRS[t]

    def _hero_enterable(self, x: int, y: int, d: str) -> bool:
        if self.is_high_wall(x, y) or self.blocks_oneway(x, y, d):
            return False
        if self.occupant[y][x] in ("BOX", "TNT"):
            return False
        return True

    def _box_enterable(self, x: int, y: int, d: str) -> bool:
        if self.is_high_wall(x, y) or self.blocks_oneway(x, y, d):
            return False
        if self.occupant[y][x] is not None:
            return False
        if self.terrain[y][x] in ("K1", "K2", "V"):
            return False
        return True

    def _clear_mimic(self, x: int, y: int):
        self.terrain[y][x] = "EMPTY"
        clue_pos = self.mimic_to_clue.pop((x, y), None)
        if clue_pos is not None:
            cx, cy = clue_pos
            if not any(pos == (cx, cy) for pos in self.mimic_to_clue.values()):
                self.clues[cy][cx] = False

    def _displace_entity(self, kind: str, start: tuple[int, int], first_pos: tuple[int, int], d: str,
                         exposed_cells: set, tnt_armed: set):
        cur_x, cur_y = start
        nx, ny = first_pos
        cur_d = d
        step_count = 0
        portal_count = 0
        suppress_portal = False

        while step_count < 32:
            step_count += 1
            if self.terrain[cur_y][cur_x] == "CRACK":
                self.terrain[cur_y][cur_x] = "PIT"

            if kind == "BOX":
                self.occupant[cur_y][cur_x] = None
                self.occupant[ny][nx] = "BOX"
            else:
                self.hx, self.hy = nx, ny
                exposed_cells.add((nx, ny))
                self._update_progress()

            cur_x, cur_y = nx, ny
            t = self.terrain[cur_y][cur_x]
            stop_momentum = False

            if t == "PIT":
                if kind == "BOX":
                    self.occupant[cur_y][cur_x] = None
                    self.terrain[cur_y][cur_x] = "EMPTY"
                    break
                else:
                    self.trap_damage += min(self.hp, 100)
                    self.hp -= 100
                    self.status = "DEAD"
                    return
            elif t == "SWITCH":
                self.gates_flipped = not self.gates_flipped
            elif kind == "HERO":
                if t == "K1":
                    self.has_k1 = True
                    self.terrain[cur_y][cur_x] = "EMPTY"
                    self._update_progress()
                elif t == "K2":
                    self.has_k2 = True
                    self.terrain[cur_y][cur_x] = "EMPTY"
                    self._update_progress()
                elif t == "V":
                    if self.has_k1 and self.has_k2:
                        self.status = "CLEARED"
                        return
                elif t == "HEAL":
                    self.hp = min(100, self.hp + 30)
                    self.terrain[cur_y][cur_x] = "EMPTY"
                elif t == "MIMIC":
                    self.trap_damage += min(self.hp, 45)
                    self.hp -= 45
                    self._clear_mimic(cur_x, cur_y)
                    stop_momentum = True
                    if self.hp <= 0:
                        self.status = "DEAD"
                        return

            if stop_momentum or step_count >= 32:
                break

            sup = suppress_portal
            suppress_portal = False

            if t == "ICE":
                vx, vy = DIRECTIONS[cur_d]
                tx, ty = cur_x + vx, cur_y + vy
                ok = self._hero_enterable(tx, ty, cur_d) if kind == "HERO" else self._box_enterable(tx, ty, cur_d)
                if not ok:
                    if kind == "BOX" and in_bounds(tx, ty) and self.occupant[ty][tx] == "TNT":
                        tnt_armed.add((tx, ty))
                    break
                nx, ny = tx, ty
                continue

            if t in MIRROR_MAP:
                cur_d = MIRROR_MAP[t][cur_d]
                vx, vy = DIRECTIONS[cur_d]
                tx, ty = cur_x + vx, cur_y + vy
                ok = self._hero_enterable(tx, ty, cur_d) if kind == "HERO" else self._box_enterable(tx, ty, cur_d)
                if not ok:
                    if kind == "BOX" and in_bounds(tx, ty) and self.occupant[ty][tx] == "TNT":
                        tnt_armed.add((tx, ty))
                    break
                nx, ny = tx, ty
                continue

            if t in SPRING_DIRS:
                cur_d = SPRING_DIRS[t]
                vx, vy = DIRECTIONS[cur_d]
                blocked_k = None
                for k in (1, 2, 3):
                    px, py = cur_x + k * vx, cur_y + k * vy
                    if not in_bounds(px, py) or self.is_high_wall(px, py) or self.blocks_oneway(px, py, cur_d):
                        blocked_k = k
                        break
                    if self.occupant[py][px] in ("BOX", "TNT"):
                        if kind == "BOX" and self.occupant[py][px] == "TNT":
                            tnt_armed.add((px, py))
                        blocked_k = k
                        break
                    if kind == "BOX" and self.terrain[py][px] in ("K1", "K2", "V"):
                        blocked_k = k
                        break
                if blocked_k == 1:
                    break
                land_k = 3 if blocked_k is None else blocked_k - 1
                nx, ny = cur_x + land_k * vx, cur_y + land_k * vy
                continue

            if t in PORTAL_PAIRS and not sup:
                pair = PORTAL_PAIRS[t]
                if pair not in self.portals:
                    break
                px, py = self.portals[pair]
                if self.occupant[py][px] is not None or (kind == "BOX" and self.terrain[py][px] in ("K1", "K2", "V")):
                    break
                portal_count += 1
                step_count += 1
                if kind == "BOX":
                    self.occupant[cur_y][cur_x] = None
                    self.occupant[py][px] = "BOX"
                else:
                    self.hx, self.hy = px, py
                    exposed_cells.add((px, py))
                    self._update_progress()
                cur_x, cur_y = px, py
                if portal_count >= 2 or step_count >= 32:
                    break
                vx, vy = DIRECTIONS[cur_d]
                tx, ty = cur_x + vx, cur_y + vy
                ok = self._hero_enterable(tx, ty, cur_d) if kind == "HERO" else self._box_enterable(tx, ty, cur_d)
                if not ok:
                    if kind == "BOX" and in_bounds(tx, ty) and self.occupant[ty][tx] == "TNT":
                        tnt_armed.add((tx, ty))
                    break
                nx, ny = tx, ty
                suppress_portal = True
                continue

            break

    def _run_explosions(self, initial_tnts: set, due_bombs: list[dict]):
        queue = []
        seen_src = set()
        for b in due_bombs:
            pos = (b["x"], b["y"])
            if pos not in seen_src:
                seen_src.add(pos)
                queue.append(("BOMB", pos[0], pos[1]))
        for tx, ty in sorted(initial_tnts):
            if (tx, ty) not in seen_src:
                seen_src.add((tx, ty))
                queue.append(("TNT", tx, ty))
        self.bombs = [b for b in self.bombs if b["timer"] > 0]

        if not queue:
            return
        idx = 0
        while idx < len(queue):
            _, ex, ey = queue[idx]
            idx += 1
            for cy in range(max(0, ey - 1), min(GRID_HEIGHT, ey + 2)):
                for cx in range(max(0, ex - 1), min(GRID_WIDTH, ex + 2)):
                    if (cx, cy) not in seen_src:
                        if self.occupant[cy][cx] == "TNT":
                            seen_src.add((cx, cy))
                            queue.append(("TNT", cx, cy))
                        for b in list(self.bombs):
                            if (b["x"], b["y"]) == (cx, cy):
                                seen_src.add((cx, cy))
                                queue.append(("BOMB", cx, cy))
                                self.bombs.remove(b)

        affected = set()
        for _, ex, ey in queue:
            for cy in range(max(0, ey - 1), min(GRID_HEIGHT, ey + 2)):
                for cx in range(max(0, ex - 1), min(GRID_WIDTH, ex + 2)):
                    affected.add((cx, cy))

        immune = {
            "T_W", "K1", "K2", "V", "PIT", "PLATE", "P_GATE",
            "ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R",
            "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
        }
        for cx, cy in affected:
            if self.occupant[cy][cx] in ("BOX", "TNT"):
                self.occupant[cy][cx] = None
            t = self.terrain[cy][cx]
            if t in immune:
                continue
            elif t == "CRACK":
                self.terrain[cy][cx] = "PIT"
            elif t == "MIMIC":
                self._clear_mimic(cx, cy)
            elif t != "EMPTY":
                self.terrain[cy][cx] = "EMPTY"

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.occupant[y][x] == "BOX" and self.terrain[y][x] == "PIT":
                    self.occupant[y][x] = None
                    self.terrain[y][x] = "EMPTY"

        if (self.hx, self.hy) in affected:
            dmg = 60
            self.trap_damage += min(self.hp, dmg)
            self.hp -= dmg
            if self.hp <= 0:
                self.status = "DEAD"
                return

        if self.hp > 0 and self.terrain[self.hy][self.hx] == "PIT":
            self.trap_damage += min(self.hp, 100)
            self.hp -= 100
        if self.hp <= 0:
            self.status = "DEAD"

    def _compute_laser_rays(self, turn_num: int):
        rays = []
        tnt_armed = set()
        fire1 = (turn_num % 3 == 0)
        fire2 = (turn_num % 4 == 0)
        if not (fire1 or fire2):
            return rays, tnt_armed
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                t = self.terrain[y][x]
                period = 3 if (t in LASER1_DIRS and fire1) else (4 if (t in LASER2_DIRS and fire2) else None)
                if period is None:
                    continue
                d = ALL_LASER_DIRS[t]
                dx, dy = DIRECTIONS[d]
                cells = set()
                for k in range(1, 11):
                    nx, ny = x + k * dx, y + k * dy
                    if self.is_high_wall(nx, ny) or self.occupant[ny][nx] == "BOX":
                        break
                    if self.occupant[ny][nx] == "TNT":
                        tnt_armed.add((nx, ny))
                        break
                    cells.add((nx, ny))
                rays.append((x, y, d, period, cells))
        return rays, tnt_armed

    def step(self, action: str):
        if self.status != "ALIVE":
            return
        self.turn += 1
        exposed_cells = {(self.hx, self.hy)}
        tnt_armed = set()

        if action == "WAIT":
            pass
        elif action == "BOMB":
            if self.bombs_left > 0 and not any(b["x"] == self.hx and b["y"] == self.hy for b in self.bombs):
                self.bombs_left -= 1
                self.bombs.append({"id": self.next_bomb_id, "x": self.hx, "y": self.hy, "timer": 3})
                self.next_bomb_id += 1
        elif action.startswith("MOVE_"):
            d = action.split("_")[1]
            dx, dy = DIRECTIONS[d]
            x1, y1 = self.hx + dx, self.hy + dy
            if not self.is_high_wall(x1, y1) and not self.blocks_oneway(x1, y1, d) and self.occupant[y1][x1] != "TNT":
                if self.occupant[y1][x1] == "BOX":
                    x2, y2 = x1 + dx, y1 + dy
                    if self._box_enterable(x2, y2, d):
                        self._displace_entity("BOX", (x1, y1), (x2, y2), d, exposed_cells, tnt_armed)
                        if self._hero_enterable(x1, y1, d):
                            self._displace_entity("HERO", (self.hx, self.hy), (x1, y1), d, exposed_cells, tnt_armed)
                    elif in_bounds(x2, y2) and self.occupant[y2][x2] == "TNT":
                        tnt_armed.add((x2, y2))
                else:
                    self._displace_entity("HERO", (self.hx, self.hy), (x1, y1), d, exposed_cells, tnt_armed)
        elif action.startswith("JUMP_"):
            if self.jumps > 0:
                self.jumps -= 1
                d = action.split("_")[1]
                dx, dy = DIRECTIONS[d]
                x1, y1 = self.hx + dx, self.hy + dy
                x2, y2 = self.hx + 2 * dx, self.hy + 2 * dy
                if (
                    not self.is_high_wall(x1, y1) and not self.blocks_oneway(x1, y1, d)
                    and self._hero_enterable(x2, y2, d)
                ):
                    self._displace_entity("HERO", (self.hx, self.hy), (x2, y2), d, exposed_cells, tnt_armed)
        elif action.startswith("THROW_"):
            if self.throws > 0:
                self.throws -= 1
                d = action.split("_")[1]
                sx, sy = self.hx, self.hy
                range_left = 6
                stone_portals = 0
                shattered = False
                while range_left > 0:
                    dx, dy = DIRECTIONS[d]
                    sx, sy = sx + dx, sy + dy
                    range_left -= 1
                    if self.is_high_wall(sx, sy) or self.occupant[sy][sx] == "BOX":
                        shattered = True
                        break
                    if self.occupant[sy][sx] == "TNT":
                        tnt_armed.add((sx, sy))
                        shattered = True
                        break
                    t = self.terrain[sy][sx]
                    if t == "SWITCH":
                        self.gates_flipped = not self.gates_flipped
                        shattered = True
                        break
                    if t == "MIMIC":
                        self._clear_mimic(sx, sy)
                        shattered = True
                        break
                    if t in MIRROR_MAP:
                        d = MIRROR_MAP[t][d]
                    elif t in PORTAL_PAIRS and stone_portals < 2:
                        pair = PORTAL_PAIRS[t]
                        if pair in self.portals:
                            px, py = self.portals[pair]
                            if self.occupant[py][px] not in ("BOX", "TNT"):
                                sx, sy = px, py
                                stone_portals += 1
                                if stone_portals == 2:
                                    shattered = True
                                    break
                if not shattered and range_left == 0 and in_bounds(sx, sy):
                    t = self.terrain[sy][sx]
                    if t == "ICE" or t in MIRROR_MAP:
                        for _ in range(32):
                            dx, dy = DIRECTIONS[d]
                            sx, sy = sx + dx, sy + dy
                            if self.is_high_wall(sx, sy) or self.blocks_oneway(sx, sy, d) or self.occupant[sy][sx] == "BOX":
                                break
                            if self.occupant[sy][sx] == "TNT":
                                tnt_armed.add((sx, sy))
                                break
                            t = self.terrain[sy][sx]
                            if t == "SWITCH":
                                self.gates_flipped = not self.gates_flipped
                                break
                            if t == "MIMIC":
                                self._clear_mimic(sx, sy)
                                break
                            if t in MIRROR_MAP:
                                d = MIRROR_MAP[t][d]
                            elif t == "ICE":
                                continue
                            elif t in PORTAL_PAIRS and stone_portals < 2:
                                pair = PORTAL_PAIRS[t]
                                if pair in self.portals:
                                    px, py = self.portals[pair]
                                    if self.occupant[py][px] not in ("BOX", "TNT"):
                                        sx, sy = px, py
                                        stone_portals += 1
                                        if stone_portals == 2:
                                            break
                                        continue
                                break
                            else:
                                break

        if self.status != "ALIVE":
            return

        # Phase C
        for b in self.bombs:
            b["timer"] -= 1
        due_bombs = [b for b in self.bombs if b["timer"] == 0]
        self._run_explosions(tnt_armed, due_bombs)
        if self.status != "ALIVE":
            return

        # Phase D
        if self.turn % 3 == 0 or self.turn % 4 == 0:
            rays, laser_tnt_armed = self._compute_laser_rays(self.turn)
            hits = sum(1 for _, _, _, _, cells in rays if cells & exposed_cells)
            if hits > 0:
                dmg = 50 * hits
                self.trap_damage += min(self.hp, dmg)
                self.hp -= dmg
                if self.hp <= 0:
                    self.status = "DEAD"
                    return
            if laser_tnt_armed:
                self._run_explosions(laser_tnt_armed, [])
                if self.status != "ALIVE":
                    return

        if self.turn >= MAX_TURNS and self.status == "ALIVE":
            self.status = "TIMEOUT"

    def get_state(self, next_turn: int, mode: str = "FULL") -> dict:
        assert mode == "FULL"
        vis = [[True] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        terrain_view = [["EMPTY"] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                t = self.terrain[y][x]
                terrain_view[y][x] = "CHEST" if t in ("HEAL", "MIMIC") else t

        laser_warnings = []
        if next_turn % 3 == 0 or next_turn % 4 == 0:
            rays, _ = self._compute_laser_rays(next_turn)
            warn_items = []
            for lx, ly, d, period, cells in rays:
                for cx, cy in cells:
                    warn_items.append((cy, cx, d, period, lx, ly))
            for cy, cx, d, period, lx, ly in sorted(set(warn_items)):
                laser_warnings.append({"x": cx, "y": cy, "dir": d, "period": period, "cannon": [lx, ly]})

        return {
            "turn": next_turn,
            "turns_left": MAX_TURNS - next_turn + 1,
            "mode": "FULL",
            "hero": {
                "x": self.hx, "y": self.hy, "hp": self.hp,
                "keys": [self.has_k1, self.has_k2],
                "jumps": self.jumps, "throws": self.throws, "bombs": self.bombs_left,
            },
            "gates_flipped": self.gates_flipped,
            "plates_active": self.is_plates_active(),
            "targets": {"K1": list(self.targets["K1"]), "K2": list(self.targets["K2"]), "V": list(self.targets["V"])},
            "visible_mask": vis,
            "terrain": terrain_view,
            "occupant": copy.deepcopy(self.occupant),
            "bombs": [{"x": b["x"], "y": b["y"], "timer": b["timer"]} for b in self.bombs],
            "clues": copy.deepcopy(self.clues),
            "laser_warnings": laser_warnings,
        }

    def compute_scores(self) -> tuple[float, float]:
        g = (MAX_BUDGET - self.spent_gold) / MAX_BUDGET
        d_total = min(100.0, self.trap_damage)
        k = self.stage_k
        r = max(0.0, (self.d0 - self.dmin) / max(1, self.d0))
        p = k + r
        if self.status == "CLEARED":
            hero_score = 600.0 + 1.5 * self.hp + 150.0 * (240 - self.turn) / 239.0 + 100.0 * g
            demon_score = 1.7 * d_total + 150.0 * (self.turn - 1) / 239.0
        elif self.status == "DEAD":
            hero_score = 200.0 * p
            demon_score = 500.0 + 50.0 * (3.0 - p) + d_total + 250.0 * g
        else:
            hero_score = 200.0 * p
            demon_score = 320.0 + 50.0 * (3.0 - p) + d_total + 125.0 * g
        return hero_score, demon_score


def verify_golden_vectors(gv_path: str):
    with open(gv_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    vecs = {v["id"]: v for v in data["vectors"]}

    # GV22_01
    v1 = vecs["GV22_01_V22_BUDGET_AND_PLATE_PGATE_SCHEMA"]
    g1 = make_empty_grid()
    for item in v1["placed_inner_tiles"]:
        g1[item["y"]][item["x"]] = item["tile"]
    dec1 = decode_grid_only(g1)
    assert dec1["spent_gold"] == v1["expected"]["spent_gold"]
    assert GameEngineV22(dec1).is_plates_active() == v1["expected"]["initial_plates_active"]
    print("[PASS] GV22_01")

    # GV22_02
    v2 = vecs["GV22_02_PLATE_BOX_ONLY_TRIGGER"]
    g2 = make_empty_grid()
    g2[5][20], g2[20][20], g2[13][35] = "K1", "K2", "V"
    px, py = v2["initial"]["plate"]
    pgx, pgy = v2["initial"]["p_gate"]
    bx, by = v2["initial"]["box"]
    g2[py][px], g2[pgy][pgx], g2[by][bx] = "PLATE", "P_GATE", "BOX"
    dec2 = decode_grid_only(g2)
    e2 = GameEngineV22(dec2)
    e2.hx, e2.hy = v2["steps"][0]["from"]
    e2.step(v2["steps"][0]["action"])
    assert e2.is_plates_active() is False and e2.is_high_wall(pgx, pgy) is True
    e2 = GameEngineV22(dec2)
    e2.hx, e2.hy = v2["steps"][1]["from"]
    for a in v2["steps"][1]["actions"]:
        e2.step(a)
    assert e2.is_plates_active() is True and e2.is_high_wall(pgx, pgy) is False
    print("[PASS] GV22_02")

    # GV22_03
    v3 = vecs["GV22_03_LCM12_RED_AND_BLUE_LASER_INSTANT_KILL"]
    g3 = make_empty_grid()
    g3[5][20], g3[20][20], g3[13][35] = "K1", "K2", "V"
    g3[8][15], g3[10][12] = "LASER_D", "LASER2_R"
    e3 = GameEngineV22(decode_grid_only(g3))
    e3.turn = 11
    e3.hx, e3.hy = 15, 10
    st3 = e3.get_state(12, mode="FULL")
    periods = sorted({w["period"] for w in st3["laser_warnings"] if (w["x"], w["y"]) == (15, 10)})
    assert periods == [3, 4], periods
    e3.step("WAIT")
    assert e3.hp == 0 and e3.status == "DEAD"
    print("[PASS] GV22_03")

    # GV22_04
    g4 = make_empty_grid()
    g4[5][20], g4[20][20], g4[13][35] = "K1", "K2", "V"
    g4[13][5], g4[13][6] = "CRACK", "ONEWAY_L"
    g4[10][10], g4[9][10] = "MIRROR_NE", "ONEWAY_R"
    dec4 = decode_grid_only(g4)
    dec4["occupant"][13][6] = "BOX"
    e4 = GameEngineV22(dec4)
    e4.hx, e4.hy = 5, 13
    e4.step("MOVE_R")
    assert e4.occupant[13][6] == "BOX" and (e4.hx, e4.hy) == (5, 13) and e4.terrain[13][5] == "CRACK"
    e4b = GameEngineV22(decode_grid_only(g4))
    e4b.hx, e4b.hy = 9, 10
    e4b.step("MOVE_R")
    assert (e4b.hx, e4b.hy) == (10, 10)
    print("[PASS] GV22_04")

    # GV22_05
    g5 = make_empty_grid()
    g5[5][20], g5[20][20], g5[13][35] = "K1", "K2", "V"
    g5[10][10], g5[10][12] = "SPRING_R", "ONEWAY_L"
    g5[14][6] = "ONEWAY_L"
    dec5 = decode_grid_only(g5)
    e5a = GameEngineV22(dec5)
    e5a.hx, e5a.hy = 9, 10
    e5a.step("MOVE_R")
    assert (e5a.hx, e5a.hy) == (11, 10)
    e5b = GameEngineV22(dec5)
    e5b.hx, e5b.hy = 5, 14
    e5b.step("JUMP_R")
    assert (e5b.hx, e5b.hy) == (5, 14) and e5b.jumps == 2
    print("[PASS] GV22_05")

    # GV22_06
    g6 = make_empty_grid()
    g6[5][20], g6[20][20], g6[13][35] = "K1", "K2", "V"
    g6[10][6], g6[10][7] = "ONEWAY_L", "SWITCH"
    g6[15][11], g6[15][12], g6[15][13] = "ICE", "ONEWAY_L", "SWITCH"
    dec6 = decode_grid_only(g6)
    e6a = GameEngineV22(dec6)
    e6a.hx, e6a.hy = 4, 10
    e6a.step("THROW_R")
    assert e6a.gates_flipped is True
    e6b = GameEngineV22(dec6)
    e6b.hx, e6b.hy = 5, 15
    e6b.step("THROW_R")
    assert e6b.gates_flipped is False
    print("[PASS] GV22_06")

    # GV22_07
    v7 = vecs["GV22_07_PHASE_C_BOX_DESTRUCTION_CLOSES_PGATE_BEFORE_PHASE_D"]
    g7 = make_empty_grid()
    g7[5][20], g7[20][20], g7[13][35] = "K1", "K2", "V"
    g7[10][10], g7[10][12], g7[10][15] = "PLATE", "P_GATE", "LASER_L"
    g7[1][1] = "BOX"
    dec7 = decode_grid_only(g7)
    dec7["occupant"][1][1] = None
    dec7["occupant"][10][10] = "BOX"
    e7 = GameEngineV22(dec7)
    e7.turn = 2
    e7.hx, e7.hy = 7, 10
    e7.bombs = [{"id": 1, "x": 9, "y": 10, "timer": 1}]
    e7.step("WAIT")
    assert e7.is_plates_active() is False and e7.hp == 100
    print("[PASS] GV22_07")

    # GV22_08
    g8 = make_empty_grid()
    g8[5][20], g8[20][20], g8[13][35] = "K1", "K2", "V"
    g8[13][34], g8[13][33] = "PIT", "PIT"
    g8[13][31], g8[13][32] = "BOX", "BOX"
    dec8 = decode_grid_only(g8)
    e8 = GameEngineV22(dec8)
    e8.status = "CLEARED"
    e8.turn = 240
    e8.trap_damage = 100.0
    _, ds8 = e8.compute_scores()
    assert abs(ds8 - 320.0) < 1e-6
    print("[PASS] GV22_08")


if __name__ == "__main__":
    gv_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_vectors_v22.json")
    verify_golden_vectors(gv_file)
    print("ALL 8 GOLDEN VECTORS PASSED!")
