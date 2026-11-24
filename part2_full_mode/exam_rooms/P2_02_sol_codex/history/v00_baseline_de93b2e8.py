"""SOL: deterministic dungeon construction and an incremental BLIND explorer.

The submitted module performs pure computation only.  All observations and
predicted changes are kept in the supplied per-game memory dictionary.
"""

import collections
import heapq
import math
import time


WIDTH = 40
HEIGHT = 26
SIZE = WIDTH * HEIGHT
DIRS = ((0, -1), (0, 1), (-1, 0), (1, 0))
LETTERS = "UDLR"
DELTA = (-40, 40, -1, 1)
NAMES = (
    "UNKNOWN", "EMPTY", "W", "T_W", "ICE", "PIT", "CRACK",
    "K1", "K2", "V", "SWITCH", "R_GATE", "B_GATE",
    "MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW",
    "SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R",
    "LASER_U", "LASER_D", "LASER_L", "LASER_R",
    "HEAL", "MIMIC", "CHEST",
    "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
)
CODE = {name: i for i, name in enumerate(NAMES)}
UNK, EMPTY, WALL, TITANIUM, ICE, PIT, CRACK = range(7)
K1, K2, VAULT, SWITCH, RED, BLUE = range(7, 13)
MNE, MSE, MSW, MNW = range(13, 17)
SU, SD, SL, SR = range(17, 21)
LU, LD, LL, LR = range(21, 25)
HEAL, MIMIC, CHEST = range(25, 28)
P1A, P1B, P2A, P2B = range(28, 32)
BOX, TNT = 1, 2
MIRRORS = ((3, 3, 0, 0), (3, 3, 1, 1),
           (2, 2, 1, 1), (2, 2, 0, 0))
MOVES = tuple("MOVE_" + d for d in LETTERS)
JUMPS = tuple("JUMP_" + d for d in LETTERS)
THROWS = tuple("THROW_" + d for d in LETTERS)
ALL_ACTIONS = MOVES + JUMPS + THROWS + ("WAIT", "BOMB")
IMMUNE = {TITANIUM, K1, K2, VAULT, PIT, P1A, P1B, P2A, P2B}


def _neighbor(p, d, n=1):
    x, y = p % 40, p // 40
    dx, dy = DIRS[d]
    x, y = x + dx * n, y + dy * n
    return y * 40 + x if 0 <= x < 40 and 0 <= y < 26 else -1


NEIGHBORS = tuple(tuple(_neighbor(p, d) for d in range(4))
                  for p in range(SIZE))
BLAST = tuple(tuple(yy * 40 + xx
                    for yy in range(max(0, p // 40 - 1), min(26, p // 40 + 2))
                    for xx in range(max(0, p % 40 - 1), min(40, p % 40 + 2)))
              for p in range(SIZE))


def _high(t, flipped):
    return (t == WALL or t == TITANIUM or LU <= t <= LR
            or t == (BLUE if flipped else RED))


def _manhattan(a, b):
    return abs(a % 40 - b % 40) + abs(a // 40 - b // 40)


def build_dungeon():
    """Directional portal locks followed by an exact three-jump inventory lock."""
    grid = [["T_W" if x in (0, 39) or y in (0, 25) else "EMPTY"
             for x in range(40)] for y in range(26)]
    # Only portals can enter the key chambers.  Corners need no paid walls:
    # neither walking nor jumping can cross an orthogonal titanium side.
    for y, key, portal in ((2, "K1", "PORTAL_1B"),
                           (23, "K2", "PORTAL_2B")):
        key_x = 32 if key == "K1" else 34
        pit_x = 34 if key == "K1" else 32
        grid[y][key_x] = key
        grid[y][33] = portal
        grid[y][pit_x] = "PIT"
        for x in (32, 33, 34):
            grid[y - 1][x] = "T_W"
            grid[y + 1][x] = "T_W"
        grid[y][31] = grid[y][35] = "T_W"
        # Extend the chamber to the free outer frame: three paid ceiling/floor
        # walls can be replaced by two side walls, saving 25G per chamber.
        edge_y = 1 if y == 2 else 24
        for x in (32, 33, 34):
            grid[edge_y][x] = "EMPTY"
        grid[edge_y][31] = grid[edge_y][35] = "T_W"
    grid[13][4] = "PORTAL_1A"
    grid[13][8] = "PORTAL_2A"
    # The two exits have opposite safe directions.  Blindly repeating the same
    # entry direction at the second lock is therefore unsafe as well.
    for x in (4, 8):
        grid[12][x] = grid[14][x] = "T_W"
    for x in range(1, 9):
        grid[11][x] = grid[15][x] = "W"
    for x in (5, 6, 7):
        grid[12][x] = grid[14][x] = "W"
    grid[13][18] = "LASER_L"
    grid[13][37] = "V"
    # All three jumps are needed at the vault.  Spending one on an early
    # portal bypass is irreversible.  Bombs, however, can open a safe escape
    # from the spawn corridor, without consuming any jump inventory.
    for x in (32, 34, 36):
        grid[13][x] = "PIT"
    for x in (33, 35, 37):
        grid[12][x] = grid[14][x] = "T_W"
    grid[13][38] = "T_W"
    route = ["MOVE_R", "MOVE_U", "BOMB", "MOVE_L", "MOVE_L",
             "MOVE_R", "MOVE_R", "MOVE_U", "MOVE_R", "BOMB",
             "MOVE_U", "MOVE_U", "MOVE_R", "MOVE_D", "MOVE_D",
             "MOVE_D", "MOVE_D", "MOVE_L", "MOVE_R", "MOVE_R",
             "MOVE_R", "MOVE_R", "MOVE_L", "MOVE_L", "MOVE_L",
             "MOVE_U", "MOVE_U", "MOVE_U"]
    route += ["MOVE_R"] * 26 + ["MOVE_D"] * 3 + ["JUMP_R"] * 3
    return {"taunt": "向前很容易，活着回来才算本事。", "grid": grid,
            "author_solution": route}


class _World:
    """Small copy-on-write game state for exact one-turn forecasts."""

    def __init__(self, terrain=None, occupant=None, hero=None, flipped=False, bombs=()):
        if terrain is None:
            return
        self.base_t = terrain
        self.base_o = occupant
        self.t = {}
        self.o = {}
        self.p = hero["y"] * 40 + hero["x"]
        self.hp = hero.get("hp", 100)
        self.keys = sum((1 << i) for i, v in enumerate(hero.get("keys", (False, False))) if v)
        self.jumps = hero.get("jumps", 3)
        self.throws = hero.get("throws", 3)
        self.stock = hero.get("bombs", 2)
        self.flipped = bool(flipped)
        self.bombs = tuple((b["y"] * 40 + b["x"], b["timer"]) for b in bombs)
        self.portals = {}
        self.lasers = []
        for p, tile in enumerate(terrain):
            if P1A <= tile <= P2B:
                self.portals[tile] = p
            elif LU <= tile <= LR:
                self.lasers.append(p)
        self.signature = 0
        self.won = False
        self.unknown = 0
        self.tele_unknown = False
        self.trap_damage = 0.0
        self.exposed = {self.p}
        self.armed = set()
        self.extra_rays = ()
        self.extra_emitters = ()
        self.possible_tnt = frozenset()
        self.ray_cache = {}
        self.interactive = any(t in (SWITCH, MIMIC, CHEST) for t in terrain) or TNT in occupant

    def clone(self):
        w = _World()
        w.base_t = self.base_t
        w.base_o = self.base_o
        w.t = self.t.copy()
        w.o = self.o.copy()
        w.p, w.hp, w.keys = self.p, self.hp, self.keys
        w.jumps, w.throws, w.stock = self.jumps, self.throws, self.stock
        w.flipped, w.bombs = self.flipped, self.bombs
        w.portals, w.lasers = self.portals, self.lasers
        w.signature = self.signature
        w.won = self.won
        w.unknown = 0
        w.tele_unknown = False
        w.trap_damage = self.trap_damage
        w.exposed = {self.p}
        w.armed = set()
        w.extra_rays = self.extra_rays
        w.extra_emitters = self.extra_emitters
        w.possible_tnt = frozenset()
        w.ray_cache = self.ray_cache
        w.interactive = self.interactive
        return w

    def tile(self, p):
        return TITANIUM if p < 0 else self.t.get(p, self.base_t[p])

    def occ(self, p):
        return 0 if p < 0 else self.o.get(p, self.base_o[p])

    def set_tile(self, p, value):
        old = self.tile(p)
        if old != value:
            self.signature ^= hash((p, old, 0)) ^ hash((p, value, 0))
            self.t[p] = value

    def set_occ(self, p, value):
        old = self.occ(p)
        if old != value:
            self.signature ^= hash((p, old, 1)) ^ hash((p, value, 1))
            self.o[p] = value

    def blocked(self, p, box=False):
        return (p < 0 or _high(self.tile(p), self.flipped) or self.occ(p) != 0
                or (box and (p == self.p or self.tile(p) in (K1, K2, VAULT))))

    def damage(self, amount, trap=True):
        if trap:
            self.trap_damage += max(0, min(self.hp, amount))
        self.hp -= amount

    def displace(self, origin, target, direction, box=False):
        p, nxt, d = origin, target, direction
        steps, portals = 0, 0
        arriving_portal = False
        while nxt >= 0:
            steps += 1
            if self.tile(p) == CRACK:
                self.set_tile(p, PIT)
            if box:
                self.set_occ(p, 0)
                self.set_occ(nxt, BOX)
            else:
                self.p = nxt
                self.exposed.add(nxt)
            p = nxt
            t = self.tile(p)
            stop = False
            if t == UNK:
                self.unknown += 1
            if box:
                if t == PIT:
                    self.set_occ(p, 0)
                    self.set_tile(p, EMPTY)
                    return
                if t == MIMIC:
                    self.set_tile(p, EMPTY)
                elif t == SWITCH:
                    self.flipped = not self.flipped
            else:
                if t == PIT:
                    self.damage(100)
                elif t == MIMIC:
                    self.damage(45)
                    self.set_tile(p, EMPTY)
                    stop = True
                elif t == HEAL:
                    self.hp = min(100, self.hp + 30)
                    self.set_tile(p, EMPTY)
                elif t == CHEST:
                    # Unidentified supplies are pessimistically treated as a mimic.
                    self.damage(45)
                    self.set_tile(p, EMPTY)
                    stop = True
                elif t == SWITCH:
                    self.flipped = not self.flipped
                if self.hp <= 0:
                    return
                if t == K1 or t == K2:
                    self.keys |= 1 << (t - K1)
                    self.set_tile(p, EMPTY)
                elif t == VAULT and self.keys == 3:
                    self.won = True
                    return
            if steps >= 32 or stop:
                return
            t = self.tile(p)
            if arriving_portal:
                arriving_portal = False
                if portals >= 2:
                    return
                nxt = NEIGHBORS[p][d]
                if self.blocked(nxt, box):
                    return
            elif t == ICE or MNE <= t <= MNW:
                if t != ICE:
                    d = MIRRORS[t - MNE][d]
                nxt = NEIGHBORS[p][d]
                if self.blocked(nxt, box):
                    return
            elif SU <= t <= SR:
                d = t - SU
                landing = p
                for k in (1, 2, 3):
                    q = _neighbor(p, d, k)
                    if self.blocked(q, box):
                        if box and q >= 0 and self.occ(q) == TNT:
                            self.armed.add(q)
                        break
                    landing = q
                if landing == p:
                    return
                nxt = landing
            elif P1A <= t <= P2B:
                pair = self.portals.get(t ^ 1)
                if pair is None:
                    self.tele_unknown = True
                    return
                if self.occ(pair) or (box and pair == self.p):
                    return
                portals += 1
                nxt = pair
                arriving_portal = True
            else:
                return

    def stone(self, d):
        p, left, teleports = self.p, 6, 0
        for step in range(38):
            q = NEIGHBORS[p][d]
            if q < 0:
                return
            p = q
            airborne = left > 0
            if airborne:
                left -= 1
            t, o = self.tile(p), self.occ(p)
            if _high(t, self.flipped) or o == BOX:
                return
            if o == TNT:
                self.armed.add(p)
                return
            if t == SWITCH:
                self.flipped = not self.flipped
                return
            if t == MIMIC or t == CHEST:
                # CHEST is only removed if it is actually a mimic; known-safe
                # chests are HEAL, and uncertain results are observed next turn.
                self.set_tile(p, EMPTY)
                return
            if MNE <= t <= MNW:
                d = MIRRORS[t - MNE][d]
            elif P1A <= t <= P2B and teleports < 2:
                pair = self.portals.get(t ^ 1)
                if pair is None or self.occ(pair):
                    return
                p = pair
                teleports += 1
                if teleports == 2:
                    return
            if left == 0:
                landing = self.tile(p)
                if not (landing == ICE or MNE <= landing <= MNW or
                        (not airborne and P1A <= landing <= P2B)):
                    return

    def explode(self, initial):
        if not initial:
            return
        # Source identity includes kind, so a planted bomb and TNT can coexist.
        sources = set(initial)
        queue = list(initial)
        bomb_map = {}
        for i, (p, timer) in enumerate(self.bombs):
            bomb_map.setdefault(p, []).append(i)
        for p, kind in queue:
            for q in BLAST[p]:
                if self.occ(q) == TNT and (q, -1) not in sources:
                    sources.add((q, -1))
                    queue.append((q, -1))
                for i in bomb_map.get(q, ()):
                    if (q, i) not in sources:
                        sources.add((q, i))
                        queue.append((q, i))
        a = b = 0
        affected = set()
        removed = set()
        for p, kind in sources:
            affected.update(BLAST[p])
            if self.p in BLAST[p]:
                if kind == -1:
                    a += 60
                else:
                    b += 50
            if kind == -1:
                self.set_occ(p, 0)
            else:
                removed.add(kind)
        if a + b:
            self.trap_damage += max(0, min(self.hp, a + b)) * a / (a + b)
            self.hp -= a + b
        self.bombs = tuple(v for i, v in enumerate(self.bombs) if i not in removed)
        for p in affected:
            if self.occ(p) == BOX:
                self.set_occ(p, 0)
            t = self.tile(p)
            if t == CRACK:
                self.set_tile(p, PIT)
            elif t not in IMMUNE and t != UNK:
                self.set_tile(p, EMPTY)
        if self.hp > 0 and self.tile(self.p) == PIT:
            self.damage(100)

    def laser_rays(self):
        cache_key = (self.signature, self.flipped)
        cached = self.ray_cache.get(cache_key)
        if cached is not None:
            rays, armed, self.possible_tnt = cached
            return rays, armed
        rays, armed = [], set()
        for p in self.lasers:
            t = self.tile(p)
            if not LU <= t <= LR:
                continue
            d, ray = t - LU, set()
            for unused in range(10):
                p = NEIGHBORS[p][d]
                if p < 0 or _high(self.tile(p), self.flipped) or self.occ(p) == BOX:
                    break
                if self.occ(p) == TNT:
                    armed.add(p)
                    break
                ray.add(p)
            rays.append(ray)
        rays.extend(self.extra_rays)
        possible_tnt = set()
        for d, candidates in self.extra_emitters:
            ray = set()
            for origin in candidates:
                p = origin
                for unused in range(10):
                    p = NEIGHBORS[p][d]
                    if p < 0 or _high(self.tile(p), self.flipped) or self.occ(p) == BOX:
                        break
                    if self.occ(p) == TNT:
                        possible_tnt.add(p)
                        break
                    ray.add(p)
            if ray:
                rays.append(frozenset(ray))
        result = (tuple(frozenset(r) for r in rays), frozenset(armed), frozenset(possible_tnt))
        self.possible_tnt = result[2]
        self.ray_cache[cache_key] = result
        return result[0], result[1]

    def possible_blast(self):
        """Conservative damage, without inventing uncertain map destruction."""
        todo = [(p, -1) for p in self.possible_tnt if self.occ(p) == TNT]
        visited = set(todo)
        for p, kind in todo:
            for q in BLAST[p]:
                if self.occ(q) == TNT and (q, -1) not in visited:
                    visited.add((q, -1))
                    todo.append((q, -1))
                for i, (bp, timer) in enumerate(self.bombs):
                    if bp == q and (q, i) not in visited:
                        visited.add((q, i))
                        todo.append((q, i))
        hit = [(p, k) for p, k in visited if self.p in BLAST[p]]
        if hit:
            self.damage(sum(60 if kind == -1 else 50 for p, kind in hit))
            if self.hp > 0 and self.tile(self.p) == CRACK:
                self.damage(100)

    def step(self, action, turn):
        w = self.clone()
        p = w.p
        if action in MOVES:
            d = MOVES.index(action)
            q = NEIGHBORS[p][d]
            if q >= 0 and not _high(w.tile(q), w.flipped) and w.occ(q) != TNT:
                if w.occ(q) == BOX:
                    r = NEIGHBORS[q][d]
                    if not w.blocked(r, True):
                        w.displace(q, r, d, True)
                        if not w.blocked(q):
                            w.displace(p, q, d)
                else:
                    w.displace(p, q, d)
        elif action in JUMPS and w.jumps:
            w.jumps -= 1
            d = JUMPS.index(action)
            q, r = NEIGHBORS[p][d], _neighbor(p, d, 2)
            if (q >= 0 and not _high(w.tile(q), w.flipped)
                    and not w.blocked(r)):
                w.displace(p, r, d)
        elif action in THROWS and w.throws:
            w.throws -= 1
            w.stone(THROWS.index(action))
        elif action == "BOMB" and w.stock and not any(bp == p for bp, bt in w.bombs):
            w.stock -= 1
            w.bombs += ((p, 3),)
        if w.hp <= 0 or w.won:
            return w
        w.bombs = tuple((bp, bt - 1) for bp, bt in w.bombs)
        initial = {(bp, i) for i, (bp, bt) in enumerate(w.bombs) if bt <= 0}
        initial.update((bp, -1) for bp in w.armed)
        w.explode(initial)
        if w.hp > 0 and turn % 3 == 0:
            rays, armed = w.laser_rays()
            hits = sum(bool(ray & w.exposed) for ray in rays)
            if hits:
                w.damage(50 * hits)
            if w.hp > 0:
                w.explode({(bp, -1) for bp in armed})
                if w.hp > 0 and w.possible_tnt:
                    w.possible_blast()
        return w

    def key(self, phase):
        return (self.p, self.keys, self.flipped, self.jumps, self.throws,
                self.stock, self.hp, self.signature, self.bombs, phase)


def _observe(state, memory):
    if memory.get("version") != 3 or state.get("turn", 1) == 1:
        memory.clear()
        memory.update(version=3, tiles=[UNK] * SIZE, occupants=[0] * SIZE,
                      seen=[False] * SIZE, clues=[False] * SIZE,
                      visits=[0] * SIZE, beam_history={}, stale=0)
    terrain, occupants = memory["tiles"], memory["occupants"]
    seen, clues = memory["seen"], memory["clues"]
    mask = state["visible_mask"]
    newly_seen = 0
    topology_changed = False
    for y in range(26):
        for x in range(40):
            p = y * 40 + x
            if mask[y][x]:
                nt = CODE.get(state["terrain"][y][x], UNK)
                no = state["occupant"][y][x]
                no = BOX if no == "BOX" else TNT if no == "TNT" else 0
                if seen[p] and (occupants[p] != no or
                                _high(terrain[p], state.get("gates_flipped", False)) !=
                                _high(nt, state.get("gates_flipped", False))):
                    topology_changed = True
                if not seen[p]:
                    newly_seen += 1
                seen[p] = True
                terrain[p] = nt
                occupants[p] = no
                clues[p] = bool(state["clues"][y][x])
    # The frame and public landmark coordinates are exact public information.
    for x in range(40):
        terrain[x] = terrain[1000 + x] = TITANIUM
    for y in range(26):
        terrain[y * 40] = terrain[y * 40 + 39] = TITANIUM
    targets = {}
    keys = state["hero"]["keys"]
    for i, name in enumerate(("K1", "K2", "V")):
        x, y = state["targets"][name]
        p = y * 40 + x
        targets[name] = p
        if i < 2 and keys[i]:
            terrain[p] = EMPTY
        else:
            terrain[p] = (K1, K2, VAULT)[i]
    for p, t in enumerate(terrain):
        if t != CHEST:
            continue
        adj = tuple(q for q in NEIGHBORS[p] if q >= 0)
        if any(clues[q] for q in adj):
            terrain[p] = MIMIC
        elif all(seen[q] for q in adj):
            terrain[p] = HEAL
    world = _World(terrain, occupants, state["hero"],
                   state.get("gates_flipped", False), state.get("bombs", ()))
    memory["visits"][world.p] += 1
    if newly_seen or memory.get("last_keys") != world.keys:
        memory["stale"] = 0
    else:
        memory["stale"] += 1
    memory["last_keys"] = world.keys
    # Remember visible fragments of rays whose cannon has not been seen yet.
    # Remember beams by line and direction.  Known blockers partition collinear
    # cannons into separate ray intervals; one known cannon must not hide another.
    turn = state.get("turn", 1)
    history = memory["beam_history"]
    if topology_changed:
        for record in history.values():
            record["clear"] = []
    if turn % 3 == 0:
        groups = {}
        for item in state.get("laser_warnings", ()):
            d = LETTERS.find(item["dir"])
            if d < 0:
                continue
            p = item["y"] * 40 + item["x"]
            group = str(d) + ":" + str(p % 40 if d < 2 else p // 40)
            groups.setdefault(group, set()).add(p)
        for group, record in list(history.items()):
            if record["f"] != world.flipped:
                continue
            current = groups.get(group, set())
            cells = {p for p in record["cells"] if not mask[p // 40][p % 40]}
            cells.update(current)
            record["cells"] = sorted(cells)
            d_text, line_text = group.split(":")
            d, line = int(d_text), int(line_text)
            clear = set(record.get("clear", ()))
            for coordinate in range(40 if d >= 2 else 26):
                p = line * 40 + coordinate if d >= 2 else coordinate * 40 + line
                if mask[p // 40][p % 40]:
                    if p in current:
                        clear.discard(p)
                    else:
                        clear.add(p)
            record["clear"] = sorted(clear)
        for group, cells in groups.items():
            old = history.get(group)
            clear = set()
            if old is not None and old["f"] == world.flipped:
                cells.update(old["cells"])
                clear.update(old.get("clear", ()))
            d_text, line_text = group.split(":")
            d, line = int(d_text), int(line_text)
            for coordinate in range(40 if d >= 2 else 26):
                p = line * 40 + coordinate if d >= 2 else coordinate * 40 + line
                if mask[p // 40][p % 40] and p not in cells:
                    clear.add(p)
            history[group] = {"cells": sorted(cells), "clear": sorted(clear),
                              "f": world.flipped, "turn": turn}
    known_coverage = ({}, {})
    for flip in (False, True):
        for origin in world.lasers:
            d = world.tile(origin) - LU
            group = str(d) + ":" + str(origin % 40 if d < 2 else origin // 40)
            coverage = known_coverage[int(flip)].setdefault(group, set())
            p = origin
            for unused in range(10):
                p = NEIGHBORS[p][d]
                if p < 0 or _high(world.tile(p), flip) or world.occ(p):
                    break
                coverage.add(p)
    inferred, emitters = [], []
    for group, record in history.items():
        if not record["cells"]:
            continue
        d_text, line_text = group.split(":")
        d, line = int(d_text), int(line_text)
        flip = record["f"]
        required = set(record["cells"]) - known_coverage[int(flip)].get(group, set())
        excluded = set(record.get("clear", ()))
        pieces = {}
        back = 2 if d >= 2 else 0
        for p in required:
            q = p
            for unused in range(40):
                before = NEIGHBORS[q][back]
                if before < 0 or _high(world.tile(before), flip) or world.occ(before) == TNT:
                    break
                q = before
            pieces.setdefault(q, set()).add(p)
        for needed in pieces.values():
            candidates, covered = [], set()
            for coordinate in range(1, 39 if d >= 2 else 25):
                origin = line * 40 + coordinate if d >= 2 else coordinate * 40 + line
                tile = world.tile(origin)
                if tile != UNK:
                    continue
                ray = set()
                p = origin
                for unused in range(10):
                    p = NEIGHBORS[p][d]
                    if p < 0 or _high(world.tile(p), flip) or world.occ(p) == TNT:
                        break
                    ray.add(p)
                if (needed & ray) and not (excluded & ray):
                    candidates.append(origin)
                    covered.update(needed & ray)
            if candidates:
                emitters.append((d, tuple(candidates)))
            if needed - covered:
                inferred.append(frozenset(needed - covered))
    world.extra_rays = tuple(inferred)
    world.extra_emitters = tuple(emitters)
    world.ray_cache.clear()
    return world, targets


def _momentum_links(world):
    """Reverse shortcuts for known forced-motion chains, used only as a bound."""
    links = {}
    for p in range(SIZE):
        t = world.tile(p)
        if not (t == ICE or MNE <= t <= SR or P1A <= t <= P2B):
            continue
        if P1A <= t <= P2B and (t ^ 1) not in world.portals:
            continue
        for d in range(4):
            origin = NEIGHBORS[p][d ^ 1]
            if origin < 0 or _high(world.tile(origin), world.flipped) or world.tile(origin) == PIT:
                continue
            if world.occ(p):
                continue
            w = world.clone()
            w.p = origin
            w.exposed = {origin}
            w.displace(origin, p, d)
            if w.hp > 0 and not w.tele_unknown and w.p != origin:
                links.setdefault(w.p, []).append((origin, 1.0))
            if world.jumps:
                origin2 = NEIGHBORS[origin][d ^ 1]
                if (origin2 >= 0 and not _high(world.tile(origin2), world.flipped)
                        and world.tile(origin2) != PIT):
                    w = world.clone()
                    w.p = origin2
                    w.exposed = {origin2}
                    w.displace(origin2, p, d)
                    if w.hp > 0 and not w.tele_unknown and w.p != origin2:
                        links.setdefault(w.p, []).append((origin2, 1.65))
    return links


def _distances(world, target, allow_demolition=True, momentum=None):
    """Optimistic reverse distance field; exact physics is used by the search."""
    dist = [1.0e6] * SIZE
    dist[target] = 0.0
    queue = [(0.0, target)]
    terrain = [world.tile(p) for p in range(SIZE)]
    costs = [1.0] * SIZE
    for p, t in enumerate(terrain):
        if t == TITANIUM or t == PIT:
            costs[p] = 1.0e6
        elif t == WALL or LU <= t <= LR:
            costs[p] = 5.0 if world.stock and allow_demolition else 1.0e6
        elif t == UNK:
            costs[p] = 1.12
        elif t in (RED, BLUE):
            costs[p] = 2.2
        elif t in (MIMIC, CHEST):
            costs[p] = 5.0 if world.throws else 25.0
        if world.occ(p) == TNT:
            costs[p] = 6.0 if world.throws or world.stock else 1.0e6
        elif world.occ(p) == BOX:
            costs[p] += 1.0
    while queue:
        value, p = heapq.heappop(queue)
        if value != dist[p]:
            continue
        entering = costs[p]
        if entering < 1.0e6:
            for q in NEIGHBORS[p]:
                if q >= 0 and costs[q] < 1.0e6:
                    nv = value + entering
                    if nv < dist[q]:
                        dist[q] = nv
                        heapq.heappush(queue, (nv, q))
        if world.jumps and entering < 1.0e6:
            for d in range(4):
                mid = NEIGHBORS[p][d]
                q = _neighbor(p, d, 2)
                if (q >= 0 and costs[q] < 1.0e6 and mid >= 0
                        and not _high(terrain[mid], world.flipped)):
                    nv = value + 1.65
                    if nv < dist[q]:
                        dist[q] = nv
                        heapq.heappush(queue, (nv, q))
        t = terrain[p]
        if P1A <= t <= P2B:
            pair = world.portals.get(t ^ 1)
            if pair is not None and value + 1 < dist[pair]:
                dist[pair] = value + 1
                heapq.heappush(queue, (value + 1, pair))
        if momentum:
            for q, cost in momentum.get(p, ()):
                nv = value + cost
                if nv < dist[q]:
                    dist[q] = nv
                    heapq.heappush(queue, (nv, q))
    return dist


def _frontier(world, memory, target):
    seen, visits = memory["seen"], memory["visits"]
    best, best_score = world.p, 1.0e9
    reachable = _distances(world, world.p, False)
    for p in range(41, 999):
        t = world.tile(p)
        if (p == world.p or not seen[p] or _high(t, world.flipped) or t in (PIT, MIMIC, CHEST)
                or world.occ(p) or reachable[p] > 1000):
            continue
        unknown = 0
        x, y = p % 40, p // 40
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                xx, yy = x + dx, y + dy
                if 0 <= xx < 40 and 0 <= yy < 26 and not seen[yy * 40 + xx]:
                    unknown += 1
        if unknown == 0:
            continue
        score = (reachable[p] * .80 + _manhattan(p, target) * .30
                 - min(unknown, 12) * 1.2 + min(visits[p], 10) * 4)
        if score < best_score:
            best, best_score = p, score
    return best if best_score < 1.0e8 else None


def _interaction_actions(w):
    actions = []
    if w.throws and w.interactive:
        # Tracing four harmless stones is cheap; unchanged results are discarded.
        actions.extend(THROWS)
    if w.stock and not w.bombs:
        useful = False
        for q in BLAST[w.p]:
            t = w.tile(q)
            if (t == WALL or LU <= t <= LR or t in (RED, BLUE)
                    or w.occ(q) == TNT):
                useful = True
                break
        if useful:
            actions.append("BOMB")
    if w.bombs or w.lasers or w.extra_rays or w.extra_emitters:
        actions.append("WAIT")
    return actions


def _search(root, state, memory, targets, deadline):
    turn = state.get("turn", 1)
    remaining = state.get("turns_left", 241 - turn)
    pending_names = [name for i, name in enumerate(("K1", "K2"))
                     if not root.keys & (1 << i)] or ["V"]
    pending = [targets[name] for name in pending_names]
    momentum = _momentum_links(root)
    fields = [_distances(root, p, momentum=momentum) for p in pending]
    selected = 0
    if len(pending) == 2:
        to_vault = _distances(root, targets["V"], momentum=momentum)
        scores = [min(1000, fields[i][root.p])
                  + min(1000, fields[1-i][pending[i]])
                  + min(1000, to_vault[pending[1-i]]) for i in range(2)]
        selected = 1 if scores[1] < scores[0] - 1.0 else 0
        previous = memory.get("goal")
        if previous in pending_names:
            old = pending_names.index(previous)
            if scores[old] <= scores[selected] + 8:
                selected = old
        if fields[selected][root.p] > 10000 and fields[1-selected][root.p] < 10000:
            selected = 1-selected
    hgoal = fields[selected]
    memory["goal"] = pending_names[selected]
    goal = pending[selected]
    explore = False
    if (hgoal[root.p] > 10000 or
            (memory["stale"] > 18 and memory["visits"][root.p] >= 3)):
        frontier = _frontier(root, memory, goal)
        if frontier is not None:
            goal = frontier
            hgoal = _distances(root, goal, momentum=momentum)
            explore = True
    unpaired = []
    for t, p in root.portals.items():
        if (t ^ 1) not in root.portals:
            # A blind teleport is an information-gathering action, rather than
            # an imaginary walk through the portal square to the other side.
            base = 10 + min(13, min(_manhattan(p, q) for q in pending) * .19)
            unpaired.append((p, base))
    visits = memory["visits"]
    start_keys = root.keys

    def heuristic(w):
        if w.won or w.keys != start_keys or (explore and w.p == goal):
            return 0.0
        value = hgoal[w.p]
        if value > 10000:
            value = 40 + 1.4 * _manhattan(w.p, goal)
        for p, base in unpaired:
            value = min(value, .85 * _manhattan(w.p, p) + base)
        return value

    queue = [(heuristic(root), 0.0, 0, 0, root, "")]
    known = {root.key(turn % 3): 0.0}
    serial = 0
    expanded = 0
    best_action = "WAIT"
    best_value = 1.0e9
    best_depth = 0
    while queue and expanded < 2800:
        if expanded % 16 == 0 and time.perf_counter() >= deadline:
            break
        priority, cost, unused, depth, w, first = heapq.heappop(queue)
        if cost > known.get(w.key((turn + depth) % 3), 1.0e9) + 1.e-8:
            continue
        if w.won or w.keys != start_keys or (explore and w.p == goal):
            if first:
                return first, expanded, "goal"
        if w.tele_unknown:
            if first:
                return first, expanded, "portal"
            continue
        value = heuristic(w) + cost * .24
        if first and depth >= 1 and (value < best_value - .001 or
                                    (abs(value - best_value) < .001 and depth > best_depth)):
            best_value, best_action, best_depth = value, first, depth
        if depth >= min(remaining, 110):
            continue
        expanded += 1
        actions = []
        jump_hazards = set()
        if w.jumps and (w.lasers or w.extra_rays or w.extra_emitters):
            rays, armed = w.laser_rays()
            for ray in rays:
                jump_hazards.update(ray)
            for p in armed | w.possible_tnt:
                jump_hazards.update(BLAST[p])
        for d in range(4):
            q = NEIGHBORS[w.p][d]
            if q < 0:
                continue
            if not _high(w.tile(q), w.flipped) and w.occ(q) != TNT:
                actions.append(MOVES[d])
            if w.jumps and not _high(w.tile(q), w.flipped):
                r = _neighbor(w.p, d, 2)
                tq, tr = w.tile(q), w.tile(r)
                useful = (tq in (PIT, CRACK, CHEST, MIMIC, SWITCH, ICE) or
                          MNE <= tq <= SR or P1A <= tq <= P2B or w.occ(q) or
                          tr == ICE or MNE <= tr <= SR or P1A <= tr <= P2B or
                          tr in (SWITCH, HEAL, CHEST) or bool(w.bombs) or
                          w.p in jump_hazards or q in jump_hazards or
                          (tr == VAULT and w.keys == 3) or
                          remaining - depth < 10)
                if useful and not w.blocked(r):
                    actions.append(JUMPS[d])
        actions.extend(_interaction_actions(w))
        for action in actions:
            child = w.step(action, turn + depth)
            if child.hp <= 0:
                continue
            changed = (child.p != w.p or child.keys != w.keys or child.signature != w.signature
                       or child.flipped != w.flipped or child.bombs != w.bombs)
            if not changed and action != "WAIT":
                continue
            if action in THROWS and not changed:
                continue
            extra = 1.0
            if child.hp < w.hp:
                extra += 2.45 * (w.hp - child.hp)
            elif child.hp > w.hp:
                extra = .3
            if child.jumps < w.jumps:
                extra += (.12 if child.won or remaining < 15 else
                          (1.15 if w.jumps >= 3 else 1.7 if w.jumps == 2 else 2.8))
                d = LETTERS.find(action[-1])
                mid = NEIGHBORS[w.p][d] if d >= 0 else -1
                mt = w.tile(mid)
                if (P1A <= mt <= P2B and not memory["seen"][targets["V"]]
                        and remaining >= 35):
                    # A portal can usually be approached from a different side.
                    # Keep irreplaceable jumps for as-yet-unseen pit locks;
                    # destructible walls provide an alternative use for bombs.
                    extra += 24 if (mt ^ 1) not in w.portals else 12
            if child.throws < w.throws:
                extra += .75
            if child.stock < w.stock:
                extra += 2.2
            extra += .45 * child.unknown
            if depth == 0 and child.unknown:
                extra += 12 * child.unknown
            if child.tele_unknown:
                d = LETTERS.find(action[-1])
                # Favor perpendicular or reverse approaches to an unseen exit.
                # This is a risk preference, never an assertion of hidden tiles.
                preferred = 2
                portal_tile = child.tile(child.p)
                if P1A <= portal_tile <= P2B:
                    likely_key = targets["K1" if portal_tile < P2A else "K2"]
                    if likely_key % 40 >= 34:
                        preferred = 3
                extra += (0 if d < 2 else 1 if d == preferred else 35) if d >= 0 else 35
            if child.p != w.p:
                extra += min(visits[child.p], 8) * .16
            if child.p == root.p and depth > 0:
                extra += 1.2
            nc = cost + extra
            nd = depth + 1
            key = child.key((turn + nd) % 3)
            if nc >= known.get(key, 1.0e9) - 1.e-8:
                continue
            known[key] = nc
            serial += 1
            h = heuristic(child)
            if child.tele_unknown:
                source = w.p
                # Entry might have been a two-square jump or a momentum chain.
                # Use the associated source's information cost where possible.
                bases = [base for p, base in unpaired if p == child.p]
                h = min(bases) if bases else 14.0
            heapq.heappush(queue, (nc + h * 1.03, nc, serial, nd, child,
                                  first or action))
    return best_action, expanded, "partial"


def _fallback(root, state, memory, targets):
    goals = [targets[name] for i, name in enumerate(("K1", "K2"))
             if not root.keys & (1 << i)] or [targets["V"]]
    best_action, best = "WAIT", -1.0e9
    for action in ALL_ACTIONS:
        w = root.step(action, state.get("turn", 1))
        if w.hp <= 0:
            continue
        score = 10000 if w.won else 0
        score += 500 * ((w.keys & 1) + ((w.keys >> 1) & 1))
        score += 3 * w.hp - min(_manhattan(w.p, p) for p in goals)
        score -= min(memory["visits"][w.p], 15) * 3 + w.unknown * 15
        score -= (root.jumps - w.jumps) * 3 + (root.throws - w.throws) * 3
        score -= (root.stock - w.stock) * 8
        if w.p == root.p and action != "WAIT":
            score -= 10
        if w.tele_unknown:
            score -= 20 if action.endswith("R") else 8
        if score > best:
            best_action, best = action, score
    return best_action


def _last_turn(root, state, targets):
    best_action, best = "WAIT", -1.0e12
    for action in ALL_ACTIONS:
        w = root.step(action, state.get("turn", 240))
        if w.hp <= 0:
            continue
        count = bool(w.keys & 1) + bool(w.keys & 2)
        pending = [targets[name] for i, name in enumerate(("K1", "K2"))
                   if not w.keys & (1 << i)] or [targets["V"]]
        distance = min(_manhattan(p, q) for p in w.exposed for q in pending)
        score = (1000000 if w.won else 0) + count * 10000 - distance * 100 + w.hp * .01
        if score > best:
            best_action, best = action, score
    return best_action


def decide_action(state, memory):
    started = time.perf_counter()
    root, targets = _observe(state, memory)
    if state.get("turns_left", 241 - state.get("turn", 1)) == 1:
        action, expanded, reason = _last_turn(root, state, targets), 0, "last_turn"
    else:
        action, expanded, reason = _search(root, state, memory, targets, started + .335)
    if action not in ALL_ACTIONS or (action == "WAIT" and expanded == 0 and reason == "partial"):
        action = _fallback(root, state, memory, targets)
    predicted = root.step(action, state.get("turn", 1))
    if predicted.hp <= 0:
        action = _fallback(root, state, memory, targets)
        predicted = root.step(action, state.get("turn", 1))
    # Preserve changes outside the next visible area, e.g. a collapsed bridge,
    # a pushed box, or a wall removed by a distant chain reaction.
    topology_changed = (bool(predicted.o) or predicted.flipped != root.flipped or
                        any(_high(root.tile(p), root.flipped) != _high(value, predicted.flipped)
                            for p, value in predicted.t.items()))
    for p, value in predicted.t.items():
        memory["tiles"][p] = value
    for p, value in predicted.o.items():
        memory["occupants"][p] = value
    if topology_changed:
        for record in memory["beam_history"].values():
            record["clear"] = []
    memory["last_action"] = action
    memory["search_nodes"] = expanded
    memory["search_reason"] = reason
    return action

