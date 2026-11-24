"""FULL v2.2 dungeon and deterministic solver."""

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
    "PLATE", "P_GATE", "ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R",
    "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R",
)
CODE = {name: i for i, name in enumerate(NAMES)}
UNK, EMPTY, WALL, TITANIUM, ICE, PIT, CRACK = range(7)
K1, K2, VAULT, SWITCH, RED, BLUE = range(7, 13)
MNE, MSE, MSW, MNW = range(13, 17)
SU, SD, SL, SR = range(17, 21)
LU, LD, LL, LR = range(21, 25)
HEAL, MIMIC, CHEST = range(25, 28)
P1A, P1B, P2A, P2B = range(28, 32)
PLATE, PGATE, OU, OD, OL, OR, L2U, L2D, L2L, L2R = range(32, 42)
BOX, TNT = 1, 2
MIRRORS = ((3, 3, 0, 0), (3, 3, 1, 1),
           (2, 2, 1, 1), (2, 2, 0, 0))
MOVES = tuple("MOVE_" + d for d in LETTERS)
JUMPS = tuple("JUMP_" + d for d in LETTERS)
THROWS = tuple("THROW_" + d for d in LETTERS)
ALL_ACTIONS = MOVES + JUMPS + THROWS + ("WAIT", "BOMB")
IMMUNE = {TITANIUM, K1, K2, VAULT, PIT, P1A, P1B, P2A, P2B,
          PLATE, PGATE, OU, OD, OL, OR}


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


def _laser(t):
    return LU <= t <= LR or L2U <= t <= L2R


def _high(t, flipped, active=False):
    return (t == WALL or t == TITANIUM or _laser(t)
            or t == (BLUE if flipped else RED) or (t == PGATE and not active))


def _against(t, direction):
    return OU <= t <= OR and t - OU != direction


def _manhattan(a, b):
    return abs(a % 40 - b % 40) + abs(a // 40 - b // 40)


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
        self.plates = []
        self.boxes = frozenset(i for i, o in enumerate(occupant) if o == BOX)
        for p, tile in enumerate(terrain):
            if P1A <= tile <= P2B:
                self.portals[tile] = p
            elif _laser(tile):
                self.lasers.append(p)
            elif tile == PLATE:
                self.plates.append(p)
        self.active = bool(self.plates) and all(p in self.boxes for p in self.plates)
        self.period = 12 if any(terrain[p] >= L2U for p in self.lasers) and any(terrain[p] <= LR for p in self.lasers) else (4 if any(terrain[p] >= L2U for p in self.lasers) else (3 if self.lasers else 1))
        self.signature = 0
        self.won = False
        self.trap_damage = 0.0
        self.exposed = {self.p}
        self.armed = set()
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
        w.trap_damage = self.trap_damage
        w.exposed = {self.p}
        w.armed = set()
        w.plates, w.active, w.boxes = self.plates, self.active, self.boxes
        w.period = self.period
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
            if old == BOX:
                self.boxes = self.boxes - {p}
            if value == BOX:
                self.boxes = self.boxes | {p}
            if self.tile(p) == PLATE:
                self.active = bool(self.plates) and all(q in self.boxes for q in self.plates)

    def high(self, p):
        return _high(self.tile(p), self.flipped, self.active)

    def blocked(self, p, direction, box=False):
        t = self.tile(p)
        return (_high(t, self.flipped, self.active) or _against(t, direction)
                or self.occ(p) != 0
                or (box and (p == self.p or t in (K1, K2, VAULT))))

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
                if self.blocked(nxt, d, box):
                    return
            elif t == ICE or MNE <= t <= MNW:
                if t != ICE:
                    d = MIRRORS[t - MNE][d]
                nxt = NEIGHBORS[p][d]
                if self.blocked(nxt, d, box):
                    return
            elif SU <= t <= SR:
                d = t - SU
                landing = p
                for k in (1, 2, 3):
                    q = _neighbor(p, d, k)
                    if self.blocked(q, d, box):
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
            if self.high(p) or o == BOX:
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
                if pair is not None and not self.occ(pair):
                    p = pair
                    teleports += 1
                    if teleports == 2:
                        return
                elif not airborne:
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

    def laser_rays(self, turn):
        phase = (turn % 3 == 0, turn % 4 == 0)
        key = self.signature, self.flipped, self.active, phase
        cached = self.ray_cache.get(key)
        if cached is not None:
            return cached
        rays, armed = [], set()
        for origin in self.lasers:
            t = self.tile(origin)
            if not _laser(t):
                continue
            blue = t >= L2U
            if not phase[blue]:
                continue
            d = t - (L2U if blue else LU)
            p, ray = origin, set()
            for unused in range(10):
                p = NEIGHBORS[p][d]
                if self.high(p) or self.occ(p) == BOX:
                    break
                if self.occ(p) == TNT:
                    armed.add(p)
                    break
                ray.add(p)
            if ray:
                rays.append(ray)
        result = tuple(rays), frozenset(armed)
        if len(self.ray_cache) < 18000:
            self.ray_cache[key] = result
        return result

    def step(self, action, turn):
        w = self.clone()
        p = w.p
        if action in MOVES:
            d = MOVES.index(action)
            q = NEIGHBORS[p][d]
            if not w.high(q) and not _against(w.tile(q), d) and w.occ(q) != TNT:
                if w.occ(q) == BOX:
                    r = NEIGHBORS[q][d]
                    if not w.blocked(r, d, True):
                        w.displace(q, r, d, True)
                        if not w.blocked(q, d):
                            w.displace(p, q, d)
                else:
                    w.displace(p, q, d)
        elif action in JUMPS and w.jumps:
            w.jumps -= 1
            d = JUMPS.index(action)
            q, r = NEIGHBORS[p][d], _neighbor(p, d, 2)
            if not w.high(q) and not _against(w.tile(q), d) and not w.blocked(r, d):
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
        if w.hp > 0 and w.lasers and (turn % 3 == 0 or turn % 4 == 0):
            rays, armed = w.laser_rays(turn)
            hits = sum(bool(ray & w.exposed) for ray in rays)
            if hits:
                w.damage(50 * hits)
            if w.hp > 0:
                w.explode({(bp, -1) for bp in armed})
        return w

    def key(self, turn):
        return (self.p, self.keys, self.flipped, self.jumps, self.throws,
                self.stock, self.hp, self.signature, self.bombs, turn % self.period)


INF = 1_000_000
DOUBLE = tuple(tuple(_neighbor(p,d,2) for d in range(4)) for p in range(SIZE))
MOMENTUM = {ICE, *range(MNE, SR + 1), *range(P1A, P2B + 1)}


def _from_state(state):
    terrain = [CODE[t] for row in state["terrain"] for t in row]
    clues = [c for row in state["clues"] for c in row]
    for p, t in enumerate(terrain):
        if t == CHEST:
            terrain[p] = MIMIC if any(q >= 0 and clues[q] for q in NEIGHBORS[p]) else HEAL
    occ = [BOX if o == "BOX" else TNT if o == "TNT" else 0
           for row in state["occupant"] for o in row]
    return _World(terrain, occ, state["hero"], state["gates_flipped"], state["bombs"])


def _snapshot(w):
    # Compare the actual observation with the exact predicted next state.
    return hash((tuple(w.tile(p) for p in range(SIZE)), tuple(w.occ(p) for p in range(SIZE)),
                 w.p, w.hp, w.keys, w.flipped, w.jumps, w.throws, w.stock,
                 tuple(sorted(w.bombs))))


def _relaxed_world(root, open_plate, demolition, fill):
    tiles = [root.tile(p) for p in range(SIZE)]
    costs = [0] * SIZE
    for p, t in enumerate(tiles):
        if t in (RED, BLUE) or (t == PGATE and open_plate):
            tiles[p] = EMPTY
            costs[p] = 0 if not root.high(p) else 2
        elif demolition and (t == WALL or _laser(t)):
            tiles[p] = EMPTY
            costs[p] = 8 if t == WALL else 10
        elif t == PIT and fill:
            tiles[p] = EMPTY
            costs[p] = 16
        elif t == MIMIC:
            costs[p] = 3 if root.throws else 18
        if root.occ(p) == TNT:
            costs[p] += 5
    fake = _World(tiles, [0] * SIZE, dict(x=0,y=0))
    return fake, costs


class _Graph:
    """Reverse navigation graph with exact static momentum and priced relaxations."""

    def __init__(self, root, open_plate=True, demolition=True, fill=False):
        model, costs = _relaxed_world(root, open_plate, demolition, fill)
        self.reverse = [[] for _ in range(SIZE)]
        self.fields = {}
        self.jump_edges = [[] for _ in range(SIZE)]
        for p in range(41, 999):
            if model.high(p) or model.tile(p) == PIT:
                continue
            for d, q in enumerate(NEIGHBORS[p]):
                if model.high(q) or _against(model.tile(q), d):
                    continue
                for dest, jump in ((q, 0), (DOUBLE[p][d], 1)):
                    t = model.tile(dest)
                    if (model.high(dest) or t == PIT or _against(t, d)
                            or (jump and (not root.jumps or costs[q] >= 8 and root.tile(q) != PIT))):
                        continue
                    land = dest
                    if t in MOMENTUM:
                        w = model.clone()
                        w.p, w.exposed = p, {p}
                        w.displace(p, dest, d)
                        if w.hp <= 0:
                            continue
                        land = w.p
                    if land != p:
                        weight = 1 + costs[dest] + (0.9 if jump else 0)
                        self.reverse[land].append((p, weight))
                        self.jump_edges[land].append((p,jump))
        # Being on a gate when it closes allows departure under the exact model.

    def distances(self, target):
        if target in self.fields:
            return self.fields[target]
        dist = [INF] * SIZE
        dist[target] = 0
        queue = [(0, target)]
        while queue:
            n, p = heapq.heappop(queue)
            if n != dist[p]:
                continue
            for q, c in self.reverse[p]:
                v = n + c
                if v < dist[q]:
                    dist[q] = v
                    heapq.heappush(queue, (v, q))
        self.fields[target] = dist
        return dist


    def minimum_jumps(self, target):
        needs=[INF]*SIZE
        needs[target]=0
        todo=collections.deque([target])
        while todo:
            p=todo.popleft()
            for q,use in self.jump_edges[p]:
                cost=needs[p]+use
                if cost<needs[q]:
                    needs[q]=cost
                    if use:
                        todo.append(q)
                    else:
                        todo.appendleft(q)
        return needs


class _PushGuide:
    """Reverse box-push distances. Exact search resolves hero access and other boxes."""

    def __init__(self, root, graph):
        self.root, self.graph = root, graph
        model, ignored = _relaxed_world(root, root.active, False, False)
        self.reverse = [[] for _ in range(SIZE)]
        self.out = [[] for _ in range(SIZE)]
        for p in range(41, 999):
            if model.high(p) or model.tile(p) in (PIT, K1, K2, VAULT):
                continue
            for d, q in enumerate(NEIGHBORS[p]):
                stand = NEIGHBORS[p][d ^ 1]
                if (model.high(stand) or model.tile(stand) == PIT or
                        _against(model.tile(p), d) or model.high(q) or
                        _against(model.tile(q), d) or model.tile(q) in (K1, K2, VAULT)):
                    continue
                land = q
                if model.tile(q) in MOMENTUM:
                    w = model.clone()
                    w.p = stand
                    w.set_occ(p, BOX)
                    w.displace(p, q, d, True)
                    if w.boxes:
                        land = next(iter(w.boxes))
                    else:
                        land = next((r for r, val in w.t.items() if
                                     val == EMPTY and model.tile(r) == PIT), q)
                if land != p:
                    self.reverse[land].append(p)
                    self.out[p].append((land, stand))
        self.fields = {}

    def distances(self, target):
        if target not in self.fields:
            dist = [INF] * SIZE
            dist[target] = 0
            queue = collections.deque([target])
            while queue:
                p = queue.popleft()
                for q in self.reverse[p]:
                    if dist[q] == INF:
                        dist[q] = dist[p] + 1
                        queue.append(q)
            self.fields[target] = dist
        return self.fields[target]

    def estimate(self, w, target):
        dist = self.distances(target)
        best = INF
        pinned = set(w.plates) & w.boxes
        for b in w.boxes:
            if b in pinned or dist[b] == INF:
                continue
            for land, stand in self.out[b]:
                if dist[land] >= dist[b]:
                    continue
                walk = self.graph.distances(stand)[w.p] if stand in self.graph.fields else _manhattan(w.p, stand)
                best = min(best, 2.8 * dist[b] + min(walk, _manhattan(w.p,stand) + 24))
        return best


def _task(root, targets, memory, graph, guide, kind):
    positions = targets
    def make(goal, fn, progress):
        return goal, fn, progress

    if kind == "plates":
        choices = [p for p in root.plates if p not in root.boxes]
        if choices:
            # Prefer an assignment that leaves a distinct viable box for each other plate.
            def assignment(p, remaining, used):
                if not p:
                    return 0
                ds = guide.distances(p[0])
                return min((ds[b] + assignment(p[1:], remaining, used | {b})
                            for b in remaining if b not in used and ds[b] < INF),
                           default=INF)
            candidates = []
            available = root.boxes - set(root.plates)
            for p in choices:
                ds = guide.distances(p)
                reserve = min((ds[b] + assignment([q for q in choices if q != p], available, {b})
                               for b in available if ds[b] < INF), default=INF)
                candidates.append((guide.estimate(root,p) + min(reserve,1000) * .7, p))
            candidates.sort()
            options = [p for score,p in candidates if score < INF]
            if options:
                p = options[memory.get("preference", 0) % len(options)]
                # Path costs to the initial push fronts prevent wall-side oscillations.
                for b in root.boxes:
                    for dest, stand in guide.out[b]:
                        if guide.distances(p)[dest] < guide.distances(p)[b]:
                            graph.distances(stand)
                return make(lambda w: p in w.boxes,
                            lambda w: 0 if p in w.boxes else guide.estimate(w,p),
                            lambda w: sum(q in w.boxes for q in w.plates))
    if kind == "bridge":
        pits = [p for p in range(SIZE) if root.tile(p) == PIT and any(
            guide.distances(p)[b] < INF for b in root.boxes - set(root.plates))]
        if pits:
            # Rank by route savings after filling, favor bridge points directly
            # paired with another pit or a one-way barrier.
            reachable = _Graph(root, open_plate=True, demolition=bool(root.stock), fill=False)
            fields = [reachable.distances(p) for p in positions]
            desired = [i for i in range(2) if not root.keys & (1 << i)] or [2]
            def priority(p):
                neighbors = [q for q in NEIGHBORS[p] if q >= 0 and not root.high(q)]
                separation = any(min(fields[i][q] for q in neighbors) < INF and
                                 max(fields[i][q] for q in neighbors) == INF for i in desired) if neighbors else False
                obstacle = any(root.tile(q) == PIT or OU <= root.tile(q) <= OR for q in neighbors)
                return guide.estimate(root,p) + min(_manhattan(p,positions[i]) for i in desired) * .8 - 11*separation - 5*obstacle
            pits.sort(key=priority)
            p = pits[memory.get("preference", 0) % len(pits)]
            return make(lambda w: w.tile(p) != PIT,
                        lambda w: 0 if w.tile(p) != PIT else guide.estimate(w,p),
                        lambda w: 0)

    f1, f2, fv = [graph.distances(p) for p in positions]
    def all_keys(w):
        p=w.p
        if w.keys == 3:
            return fv[p]
        if w.keys == 1:
            return f2[p] + fv[positions[1]]
        if w.keys == 2:
            return f1[p] + fv[positions[0]]
        return min(f1[p] + f2[positions[0]] + fv[positions[1]],
                   f2[p] + f1[positions[1]] + fv[positions[0]])
    def estimate(w):
        n=all_keys(w)
        if n < INF:
            return n
        pending = [positions[i] for i in range(2) if not w.keys & (1 << i)] or [positions[2]]
        return 135 + min(_manhattan(w.p,p) for p in pending) + 35*(2-w.keys.bit_count())
    return make(lambda w: w.won, estimate, lambda w: w.keys.bit_count())


def _actions(w, expanded, jumps_free):
    danger = set().union(*w.laser_rays(12)[0]) if w.jumps and w.lasers else ()
    for d,q in enumerate(NEIGHBORS[w.p]):
        t = w.tile(q)
        if w.high(q) or _against(t,d):
            continue
        if t != PIT and w.occ(q) != TNT:
            yield MOVES[d]
        if w.jumps:
            r = DOUBLE[w.p][d]
            if (jumps_free or t in (PIT, MIMIC, CRACK, SWITCH) or t in MOMENTUM
                    or w.tile(r) in MOMENTUM or w.occ(q) or w.bombs or q in danger or w.p in danger
                    or (w.tile(r)==VAULT and w.keys==3)):
                if w.tile(r) != PIT and not w.blocked(r,d):
                    yield JUMPS[d]
    if w.throws and w.interactive:
        yield from THROWS
    if w.stock and not any(p == w.p for p,t in w.bombs):
        if any(w.tile(q) in (WALL,RED,BLUE) or _laser(w.tile(q)) or w.occ(q) for q in BLAST[w.p]):
            yield "BOMB"
    if w.bombs or w.lasers:
        yield "WAIT"


def _plan(root, turn, objective, estimate, progress, deadline, memory, width, kind, reserve):
    remaining = 241-turn
    queue = [(estimate(root), 0.0, 0, root, 0)]
    seen = {root.key(turn): 0.0}
    links = [(-1,"")]
    best_id, best, best_depth = 0, INF, 0
    best_progress = progress(root)
    solved = False
    expanded=0
    weights = (2.35, 3.8, 1.3, 5.2)
    weight = weights[memory.get("attempt",0) % len(weights)]
    visits = memory.get("visits", {})
    pinned = set(root.plates) & root.boxes
    root_h = estimate(root)
    polls=0
    while queue and expanded < width:
        polls+=1
        if polls % 16 == 1 and time.monotonic() >= deadline:
            break
        _, cost, node, w, depth = heapq.heappop(queue)
        if cost != seen.get(w.key(turn+depth)):
            continue
        if objective(w):
            best_id=node
            solved=True
            break
        if node:
            made = progress(w)
            h = estimate(w)
            value = h + cost * .31 + (0.0 if not w.bombs else 4.0)
            if made > best_progress or (made == best_progress and
                                        (value < best or value == best and depth > best_depth)):
                best,best_id,best_depth,best_progress=value,node,depth,made
        if depth >= remaining:
            continue
        expanded += 1
        for action in _actions(w,expanded,memory.get("attempt",0)>10 and turn>195 and kind=="main"):
            child=w.step(action,turn+depth)
            if child.hp <= 0:
                continue
            uses_jump = child.jumps < w.jumps
            if uses_jump and not child.won:
                if kind=="plates" and memory.get("stalled",0)<3:
                    continue
                if reserve is not None and turn<226 and not child.boxes-root.boxes:
                    need=reserve[child.p]
                    if need<INF and child.jumps<need:
                        continue
            same = (child.p == w.p and child.signature == w.signature and
                    child.flipped == w.flipped and child.bombs == w.bombs)
            if same and action != "WAIT":
                continue
            if action in THROWS and child.signature == w.signature and child.flipped == w.flipped:
                continue
            # Once a complete route is available, all inventory use on it is safe.
            # While searching, favor health and scarce resources over cosmetic shortcuts.
            step = 1 + max(0, w.hp-child.hp) * 1.95
            if child.hp > w.hp:
                step -= .70
            if child.stock < w.stock:
                step += 5.0
            if child.jumps < w.jumps:
                step += (0.2 if child.won else 12 if kind != "main" else 7.0)
            if child.throws < w.throws:
                step += 1.1
            if pinned and child.boxes != w.boxes:
                step += 12 * len((pinned & w.boxes) - child.boxes)
            if depth < 3:
                step += .52 * min(8, visits.get(str(child.p),0))
            new_cost = cost + step
            nd=depth+1
            key=child.key(turn+nd)
            if new_cost >= seen.get(key,INF):
                continue
            seen[key]=new_cost
            node2=len(links);links.append((node,action))
            h=0 if objective(child) else estimate(child)
            heapq.heappush(queue,(new_cost + weight*h,new_cost,node2,child,nd))
    path=[]
    while best_id:
        best_id,action=links[best_id]
        path.append(action)
    path.reverse()
    # A deadline break can also land on an already simulated terminal state;
    # replay of the returned route decides whether it is ready to commit.
    return path, expanded, best, root_h, solved


def _safe_action(root, turn, targets, memory):
    best, selected = -INF, "WAIT"
    goals = [p for i,p in enumerate(targets[:2]) if not root.keys & (1<<i)] or targets[2:]
    for action in ALL_ACTIONS:
        w = root.step(action,turn)
        if w.hp <= 0:
            continue
        score = (100000 if w.won else 0) + 260 * w.keys.bit_count() + 3 * w.hp
        score -= min(_manhattan(p,q) for p in w.exposed for q in goals)
        score -= 2.5 * memory.get("visits",{}).get(str(w.p),0)
        score -= 9*(root.stock-w.stock) + 4*(root.jumps-w.jumps) + 4*(root.throws-w.throws)
        if w.p == root.p and action != "WAIT":
            score -= 8
        if not w.won and turn < 240 and not any(
                w.step(a,turn+1).hp > 0 for a in (*MOVES,*JUMPS,"WAIT")):
            score -= 700
        if score > best:
            best, selected = score, action
    return selected



def _plate_macro(root, guide, turn, deadline):
    """Search joint layouts for ordinary push rooms. Walking paths are compressed."""
    if not root.boxes or len(root.boxes) < len(root.plates):
        return []
    area = root.boxes | set(root.plates)
    x0,y0=max(1,min(p%40 for p in area)-3),max(1,min(p//40 for p in area)-3)
    x1,y1=min(38,max(p%40 for p in area)+3),min(24,max(p//40 for p in area)+3)
    if (x1-x0+1)*(y1-y0+1) > 330 or not (x0<=root.p%40<=x1 and y0<=root.p//40<=y1):
        return []
    floor=set()
    for y in range(y0,y1+1):
        for x in range(x0,x1+1):
            p=y*40+x
            t=root.tile(p)
            if root.high(p) or t in (PIT,CRACK,SWITCH,HEAL,MIMIC,K1,K2,VAULT) or t in MOMENTUM or root.occ(p)==TNT:
                continue
            floor.add(p)
    if not (area | {root.p}) <= floor:
        return []
    walks={}
    pushes={}
    for pos in floor:
        walks[pos]=tuple((q,d) for d,q in enumerate(NEIGHBORS[pos])
                         if q in floor and not _against(root.tile(q),d))
        pushes[pos]=tuple((q,NEIGHBORS[q][d],d) for q,d in walks[pos]
                          if NEIGHBORS[q][d] in floor and not _against(root.tile(NEIGHBORS[q][d]),d))
    fields=[guide.distances(p) for p in root.plates]
    match_cache={}
    def match(boxes):
        prior=match_cache.get(boxes)
        if prior is not None:
            return prior
        def rec(i,left):
            if i==len(fields):
                return 0
            f=fields[i]
            return min((f[b]+rec(i+1,left-{b}) for b in left if f[b]<INF),default=INF)
        h=rec(0,boxes)
        match_cache[boxes]=h
        return h
    def component(pos,boxes):
        prev={pos:None}
        todo=[pos]
        for a in todo:
            for b,d in walks[a]:
                if b not in prev and b not in boxes:
                    prev[b]=(a,d)
                    todo.append(b)
        return prev
    h=match(root.boxes)
    if h>=INF:
        return []
    heap=[(h,0,0,root.p,root.boxes)]
    history=[(-1,())]
    settled={}
    count=0
    polls=0
    while heap and count<7500:
        polls+=1
        if polls%8==1 and time.monotonic()>=deadline:
            break
        _,cost,node,p,boxes=heapq.heappop(heap)
        if all(q in boxes for q in root.plates):
            chunks=[]
            while node:
                node,part=history[node];chunks.append(part)
            path=[a for chunk in reversed(chunks) for a in chunk]
            w=root
            for i,a in enumerate(path):
                w=w.step(a,turn+i)
                if w.hp<root.hp:
                    return []
            if w.active and turn+len(path)<=240:
                return path
            return []
        reach=component(p,boxes)
        # Directed gates can make two positions in the same reachable set
        # inequivalent. Use the whole set as the component identifier.
        frozen=frozenset(reach)
        key=(boxes,frozen)
        if cost>=settled.get(key,INF):
            continue
        settled[key]=cost
        count+=1
        for stand in reach:
            for b,q,d in pushes[stand]:
                if b not in boxes or q in boxes:
                    continue
                shifted=(boxes-{b})|{q}
                v=match(shifted)
                if v>=INF:
                    continue
                segment=[MOVES[d]]
                i=stand
                while i!=p:
                    i,d0=reach[i]
                    segment.append(MOVES[d0])
                segment.reverse()
                g=cost+len(segment)
                if turn+g>240:
                    continue
                node2=len(history);history.append((node,segment))
                heapq.heappush(heap,(g+4.7*v,g,node2,b,shifted))
    return []


def _choose_plan(root, turn, targets, memory, deadline):
    graph = _Graph(root, demolition=bool(root.stock or root.throws))
    guided = bool(root.boxes)
    guide = _PushGuide(root,graph) if guided else None
    kind = "main"
    required_plate = False
    pending = [p for i,p in enumerate(targets[:2]) if not root.keys & (1<<i)] + [targets[2]]
    if guided and root.plates and not root.active and PGATE in root.base_t:
        closed = _Graph(root, open_plate=False, demolition=bool(root.stock or root.throws), fill=True)
        required_plate = any(closed.distances(p)[root.p] == INF for p in pending)
        if required_plate:
            kind = "plates"
            if len(root.plates) >= 3 and not root.bombs:
                now=time.monotonic()
                macro=_plate_macro(root,guide,turn,min(deadline-.06,now+(.72 if turn==1 else .095)))
                if macro:
                    memory.update(stalled=0,kind="joint plates",complete=True)
                    return macro
    if guided and kind == "main" and any(graph.distances(p)[root.p] == INF for p in pending):
        kind = "bridge"
    if guided and memory.get("stalled",0) >= 9:
        memory["preference"] = memory.get("preference",0) + 1
        if root.plates and not root.active:
            kind="plates"
        elif memory["preference"] % 2:
            kind="bridge"
    goal, h, progress = _task(root,targets,memory,graph,guide,kind)
    reserve = None
    if root.jumps and kind!="bridge":
        needs = (_Graph(root,demolition=False).minimum_jumps(targets[2])
                 if root.stock or root.throws else graph.minimum_jumps(targets[2]))
        vault=targets[2]
        outside=min(needs[q] for q in range(41,999) if _manhattan(q,vault)>=7)
        if outside<=root.jumps:
            reserve=[need if need<=root.jumps else
                     (outside if _manhattan(q,vault)>=7 else 0)
                     for q,need in enumerate(needs)]
        if memory.get("stalled",0)>28 and memory.get("attempt",0)%5==4:
            reserve=None
    path,n,best,h0,solved=_plan(root,turn,goal,h,progress,deadline,memory,24000 if turn==1 else 8000,kind,reserve)
    w=root
    for i,action in enumerate(path):
        w=w.step(action,turn+i)
    complete=solved and bool(path) and goal(w) and (kind!="main" or w.won)
    if complete:
        memory["stalled"]=0
    else:
        memory["stalled"]=memory.get("stalled",0)+1
        memory["attempt"]=memory.get("attempt",0)+1
    memory["nodes"],memory["kind"],memory["complete"] = n,kind,complete
    # Commit proven stage plans. Partial searches are receding-horizon and
    # preserve enough of a promising path to cross flat heuristic plateaus.
    return path if complete or w.won else path[:(2 if best < h0+1 else 1)]


def decide_action(state, memory):
    started=time.monotonic()
    turn=state["turn"]
    root=_from_state(state)
    targets=tuple(state["targets"][name][1]*40+state["targets"][name][0] for name in ("K1","K2","V"))
    if turn==1:
        memory.clear()
    visits=memory.setdefault("visits",{})
    p=str(root.p)
    visits[p]=visits.get(p,0)+1
    cached=memory.get("plan",[])
    if cached and memory.get("expected")==_snapshot(root):
        route=cached
    elif turn==240:
        route=[]
    else:
        route=_choose_plan(root,turn,targets,memory,started+(1.54 if turn==1 else .36))
    action=route[0] if route else _safe_action(root,turn,targets,memory)
    after=root.step(action,turn)
    if after.hp <= 0:
        action=_safe_action(root,turn,targets,memory)
        after=root.step(action,turn)
        route=[]
    memory["plan"]=route[1:]
    memory["expected"]=_snapshot(after)
    return action


def build_dungeon():
    """Four interacting pressure plates, two demolition locks, then a three-jump gauntlet."""
    terrain = {   '#': 'T_W',
        '+': 'W',
        '.': 'EMPTY',
        '1': 'K1',
        '2': 'K2',
        '>': 'LASER_R',
        'B': 'BOX',
        'O': 'PIT',
        'V': 'V',
        '_': 'PLATE',
        'g': 'P_GATE',
        'k': 'LASER2_D',
        's': 'ONEWAY_D'}
    rows = (   '########################################',
        '#......................................#',
        '#......................................#',
        '#......................................#',
        '#....##########.....###................#',
        '#....#.._.B...#.....+g1#...............#',
        '#....#..##....#.....###................#',
        '#....#...B.#_.#........................#',
        '#....#_B#.....#........................#',
        '#....#..#..#..#........................#',
        '#....#.B.._...#........................#',
        '#....####.#####........................#',
        '#.........................###g#####k####',
        '#.........................#>.s..O.O.OV##',
        '#.........................##############',
        '#......................................#',
        '#...................###................#',
        '#...................+.2#...............#',
        '#...................###................#',
        '#......................................#',
        '#......................................#',
        '#......................................#',
        '#......................................#',
        '#......................................#',
        '#......................................#',
        '########################################')
    script = 'RRRRRRRUUUUURULLLDLDDRRRLLUDRRUUULLULDUURRRRDDDDLDLLUUDDRRUUURUULLLDLDRRRDRRRUULLDLDRRLUURRDRDDLURUUULLLLRDDDDLDDDRRRRRRRRRRUUUUUUUbLLRRRRRLLLDDDDDDDDDDDDbLLRRRRRLLLUUUUUURRRRRRRRRRD....DRRjjj'
    actions = dict(zip("UDLRjb.", (*MOVES, "JUMP_R", "BOMB", "WAIT")))
    return dict(taunt='四只箱子都要归位。最后三跳，数准你还剩几拍。', grid=[[terrain[c] for c in row] for row in rows],
                author_solution=[actions[a] for a in script])
