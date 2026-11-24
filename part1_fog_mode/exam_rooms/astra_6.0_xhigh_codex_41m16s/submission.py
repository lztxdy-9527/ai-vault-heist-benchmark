"""ASTRA's blind vault tournament entry."""

from collections import namedtuple
from heapq import heappop, heappush
from time import perf_counter


def build_dungeon():
    grid = [["T_W" if x in (0, 39) or y in (0, 25) else "EMPTY"
             for x in range(40)] for y in range(26)]
    for x in (1, 2, 3):
        grid[7][x] = "LASER_D"
        grid[19][x] = "LASER_U"
    for y in range(11, 16):
        grid[y][4] = "W"
    grid[15][1] = grid[16][1] = "ICE"
    grid[17][1], grid[20][8] = "PORTAL_1A", "PORTAL_1B"
    grid[2][33], grid[23][34], grid[4][37] = "K1", "K2", "V"
    route = (["MOVE_L", "JUMP_D"] + ["MOVE_R"] * 26 + ["MOVE_D"] * 2
             + ["MOVE_U"] * 21 + ["MOVE_L"] + ["MOVE_R"] * 4 + ["MOVE_D"] * 2)
    return {"taunt": "冰面上那串脚印，为什么只有去程？",
            "grid": grid, "author_solution": route}


WIDTH, SIZE = 40, 1040
DIR = (-40, 40, -1, 1)
LETTERS = "UDLR"
MOVES = tuple("MOVE_" + d for d in LETTERS)
JUMPS = tuple("JUMP_" + d for d in LETTERS)
THROWS = tuple("THROW_" + d for d in LETTERS)
ACTIONS = MOVES + JUMPS + THROWS + ("WAIT", "BOMB")
WAIT, DROP = 12, 13
AREA = (-41, -40, -39, -1, 0, 1, 39, 40, 41)
INNER = tuple(y * 40 + x for y in range(1, 25) for x in range(1, 39))
NAMES = ("UNKNOWN EMPTY W T_W PIT ICE CRACK SWITCH R_GATE B_GATE K1 K2 V "
         "CHEST HEAL MIMIC MIRROR_NE MIRROR_SE MIRROR_SW MIRROR_NW "
         "SPRING_U SPRING_D SPRING_L SPRING_R PORTAL_1A PORTAL_1B "
         "PORTAL_2A PORTAL_2B LASER_U LASER_D LASER_L LASER_R").split()
ID = {name: i for i, name in enumerate(NAMES)}
(FOG, FLOOR, WALL, STEEL, PIT, ICE, CRACK, SWITCH, RED, BLUE, K1, K2, VAULT,
 CHEST, HEAL, MIMIC, NE, SE, SW, NW, SU, SD, SL, SR, P1A, P1B, P2A, P2B,
 LU, LD, LL, LR) = range(32)
MASK, BOX, TNT = 31, 32, 64
OBJECT = {None: 0, "BOX": BOX, "TNT": TNT}
MIRROR = ((3, 3, 0, 0), (3, 3, 1, 1), (2, 2, 1, 1), (2, 2, 0, 0))
IMMUNE = {STEEL, K1, K2, VAULT, PIT, P1A, P1B, P2A, P2B}
BLOCK = tuple(tuple(t in (WALL, STEEL, BLUE if flip else RED) or t >= LU
                    for t in range(32)) for flip in (0, 1))
State = namedtuple("State", "p hp keys flip jumps bombs stones edits fuses")
Transition = namedtuple("Transition", "state cost scout won")


def index(xy):
    return xy[1] * WIDTH + xy[0]


def distance(p, q):
    return abs(p % WIDTH - q % WIDTH) + abs(p // WIDTH - q // WIDTH)


def remember(s, mem):
    h = s["hero"]
    p = h["y"] * WIDTH + h["x"]
    keys = int(h["keys"][0]) + 2 * int(h["keys"][1])
    targets = tuple(index(s["targets"][k]) for k in ("K1", "K2", "V"))
    if "map" not in mem:
        board = [STEEL] * SIZE
        for i in INNER:
            board[i] = FOG
        for i, t in zip(targets, (K1, K2, VAULT)):
            board[i] = t
        mem.update(map=board, clue=[False] * SIZE, beams=[0] * SIZE,
                   visits=[0] * SIZE, stage=-1, trail=[], trips={}, rubble=[])
    board, clues, beams = mem["map"], mem["clue"], mem["beams"]
    if keys != mem["stage"]:
        mem.update(stage=keys, visits=[0] * SIZE, trail=[], trips={})
    predicted = mem.pop("predicted", None)
    if predicted and predicted[0] == p and predicted[1] == int(s["gates_flipped"]):
        for pos, code in predicted[2]:
            if (board[pos] & MASK == WALL or board[pos] & MASK >= LU) and code == FLOOR:
                mem["rubble"].append(pos)
            board[pos] = code
    if keys & 1:
        board[targets[0]] = FLOOR
    if keys & 2:
        board[targets[1]] = FLOOR
    firing = s["turn"] % 3 == 0
    visible = set()
    discovered = 0
    for y, mask in enumerate(s["visible_mask"]):
        terrains, occupants, marks = s["terrain"][y], s["occupant"][y], s["clues"][y]
        for x, seen in enumerate(mask):
            if seen:
                i = y * WIDTH + x
                if board[i] & MASK == FOG:
                    discovered += 1
                code = ID[terrains[x]]
                if code == CHEST and board[i] & MASK == HEAL:
                    code = HEAL
                board[i] = code + OBJECT[occupants[x]]
                clues[i] = marks[x]
                visible.add(i)
                if firing:
                    beams[i] = 0
    for ray in s["laser_warnings"]:
        i = ray["y"] * WIDTH + ray["x"]
        beams[i] |= 1 << LETTERS.index(ray["dir"])
    probe = mem.pop("probe", -1)
    if probe in visible and board[probe] & MASK == CHEST:
        board[probe] = HEAL + (board[probe] & ~MASK)
    trail = mem["trail"]
    trail.append(p)
    if len(trail) > 18:
        trail.pop(0)
    mem["visits"][p] += 1
    if discovered >= 2 or len(trail) == 1:
        mem["dry"] = 0
    else:
        mem["dry"] = mem.get("dry", 0) + 1
    return p, keys, targets, visible


class World:
    def __init__(self, s, mem, targets, visible):
        self.mem = mem
        self.board = mem["map"][:]
        self.targets = targets
        self.visible = visible
        self.turn = s["turn"]
        self.lasers = []
        self.portals = [-1] * 4
        self.switches = []
        self.gates = False
        colors = set()
        for p in INNER:
            c = self.board[p]
            t = c & MASK
            if t == CHEST:
                if any(mem["clue"][p + d] for d in DIR):
                    self.board[p] = c - CHEST + MIMIC
                elif all(self.board[p + d] & MASK != FOG for d in DIR):
                    self.board[p] = c - CHEST + HEAL
            elif t >= LU:
                self.lasers.append((p, t - LU))
            elif P1A <= t <= P2B:
                self.portals[t - P1A] = p
            elif t == SWITCH:
                self.switches.append(p)
            elif t in (RED, BLUE):
                self.gates = True
                colors.add(t)
        self.preferred_flip = (1 if colors == {RED} else 0 if colors == {BLUE} else None)
        self.unexplained = {}
        self.laser_cache = {}
        for p, dirs in enumerate(mem["beams"]):
            if not dirs:
                continue
            for d, step in enumerate(DIR):
                if not dirs & (1 << d):
                    continue
                if any(k == d and 1 <= (p - q) // step <= 10
                       and (p - q) % step == 0 and distance(p, q) <= 10
                       and (d < 2 or p // WIDTH == q // WIDTH)
                       for q, k in self.lasers):
                    continue
                line = p % WIDTH if d < 2 else p // WIDTH
                bit = 1 << (len(self.lasers) + d * 40 + line)
                self.unexplained[p] = self.unexplained.get(p, 0) | bit
        # A visible beam with a hidden source also certifies the unobstructed
        # segment back to the first cell which could contain that source.
        for p, dirs in enumerate(mem["beams"]):
            if not dirs or p not in self.unexplained:
                continue
            for d, step in enumerate(DIR):
                line = p % WIDTH if d < 2 else p // WIDTH
                bit = 1 << (len(self.lasers) + d * 40 + line)
                if not self.unexplained[p] & bit:
                    continue
                q = p
                segment = []
                for _ in range(10):
                    q -= step
                    c = self.board[q]
                    if c & MASK == FOG:
                        for a in segment:
                            self.unexplained[a] = self.unexplained.get(a, 0) | bit
                        break
                    if c >= BOX or BLOCK[int(s["gates_flipped"])][c & MASK]:
                        break
                    segment.append(q)
        self.has_beams = bool(self.lasers or self.unexplained)
        self.seen_shot = s["turn"] % 3 == 0
        self.root_flip = int(s["gates_flipped"])
        self.visits = mem["visits"]
        self.stale = len(mem["trail"]) - len(set(mem["trail"]))
        self.ray_signatures = {}
        self.opening_risks = {}
        self.rubble = set(mem["rubble"])
        self.fog_cost = [0.] * SIZE
        for q in INNER:
            if self.board[q] & MASK not in (WALL, STEEL):
                continue
            for step in DIR:
                # A straight observed wall commonly continues behind the fog.
                # It only changes path cost. New observations always settle it.
                if self.board[q - step] & MASK not in (WALL, STEEL):
                    continue
                a = q
                for surcharge in (8.0, 5.5, 3.0, 1.5):
                    a += step
                    if self.board[a] & MASK != FOG:
                        break
                    self.fog_cost[a] = max(self.fog_cost[a], surcharge)

    def opening_risk(self, p):
        # Before the first warning, long unseen firing lanes through the spawn
        # are more dangerous than lanes screened by a known wall or obstacle.
        if p in self.opening_risks:
            return self.opening_risks[p]
        x, y = p % WIDTH, p // WIDTH
        axes = [0., 0.]
        for d, step in enumerate(DIR):
            offset = abs(x - 2) if d < 2 else abs(y - 13)
            if offset > 3:
                continue
            q = p
            for k in range(1, 11):
                q += step
                c = self.board[q]
                if c >= BOX or BLOCK[self.root_flip][c & MASK]:
                    break
                if c & MASK == FOG:
                    alignment = ((5., 3.2, 1.6, 0.3) if d < 2 else (7., 3.8, 0.7, 0.15))[offset]
                    longitudinal = abs(y - 13) if d < 2 else abs(x - 2)
                    axes[d // 2] += alignment * max(0.15, 1. - longitudinal * 0.12)
                    break
        risk = sum(axes) + 0.25 * axes[0] * axes[1]
        self.opening_risks[p] = risk
        return risk

    def rays(self, edits, flip, actual=False):
        geom = self.ray_signatures.get(edits)
        if geom is None:
            geom = tuple((p, c) for p, c in edits
                         if self.board[p] >= BOX or c >= BOX
                         or BLOCK[0][self.board[p] & MASK] or BLOCK[1][self.board[p] & MASK])
            self.ray_signatures[edits] = geom
        actual = actual and not geom and flip == self.root_flip and self.seen_shot
        key = (geom, flip, actual)
        if key in self.laser_cache:
            return self.laser_cache[key]
        get = dict(geom).get
        rays = dict(self.unexplained)
        if actual:
            for p in self.visible:
                if p in rays:
                    value = 0
                    for d in range(4):
                        if self.mem["beams"][p] & (1 << d):
                            line = p % WIDTH if d < 2 else p // WIDTH
                            value |= rays[p] & (1 << (len(self.lasers) + d * 40 + line))
                    rays[p] = value
        armed = []
        wall = BLOCK[flip]
        for number, (src, d) in enumerate(self.lasers):
            if get(src, self.board[src]) & MASK != LU + d:
                continue
            p, step, bit = src, DIR[d], 1 << number
            for _ in range(10):
                p += step
                c = get(p, self.board[p])
                if c >= TNT:
                    armed.append(p)
                    break
                if c >= BOX or wall[c & MASK]:
                    break
                if not actual or p not in self.visible or self.mem["beams"][p] & (1 << d):
                    rays[p] = rays.get(p, 0) | bit
        result = rays, tuple(armed)
        self.laser_cache[key] = result
        return result


class Turn:
    """One speculative turn. Only altered cells are copied between search nodes."""

    def __init__(self, world, state):
        self.w = world
        self.base = world.board
        self.cells = dict(state.edits)
        self.p = state.p
        self.hp = state.hp
        self.keys = state.keys
        self.flip = state.flip
        self.fuses = state.fuses
        self.armed = []
        self.path = [state.p]
        self.uncertainty = 0.0
        self.scout = -1
        self.won = False
        self.probe = -1

    def at(self, p):
        return self.cells.get(p, self.base[p])

    def put(self, p, c):
        if c == self.base[p]:
            self.cells.pop(p, None)
        else:
            self.cells[p] = c

    def blocked(self, p, box=False):
        c = self.at(p)
        t = c & MASK
        return (c >= BOX or BLOCK[self.flip][t]
                or (box and (p == self.p or t in (K1, K2, VAULT))))

    def advance(self, src, dest, d, box=False):
        teleports = 0
        exit_portal = False
        for n in range(1, 33):
            old = self.at(src) & MASK
            t = self.at(dest) & MASK
            if box or old == CRACK:
                self.put(src, PIT if old == CRACK else old)
            if box:
                self.put(dest, BOX + t)
                if t == PIT:
                    self.put(dest, FLOOR)
                    return
                if t == MIMIC:
                    self.put(dest, BOX + FLOOR)
            else:
                self.p = dest
                self.path.append(dest)
                if t == PIT:
                    self.hp -= 100
                    return
                if t in (MIMIC, CHEST):
                    self.hp -= 45
                    self.put(dest, FLOOR)
                    return
                if t == HEAL:
                    self.hp = min(100, self.hp + 30)
                    self.put(dest, FLOOR)
                elif t in (K1, K2):
                    self.keys |= 1 if t == K1 else 2
                    self.put(dest, FLOOR)
                elif t == VAULT and self.keys == 3:
                    self.won = True
                    return
            if t == SWITCH:
                self.flip ^= 1
            if t == FOG:
                self.uncertainty += (0.45 if n == 1 else 9.0) + self.w.fog_cost[dest]
            if n == 32:
                return
            src = dest
            if exit_portal:
                exit_portal = False
                if teleports == 2:
                    return
            elif P1A <= t <= P2B:
                pair = self.w.portals[(t - P1A) ^ 1]
                if pair < 0:
                    if not box:
                        self.scout = src
                    return
                if self.blocked(pair, box):
                    return
                dest = pair
                teleports += 1
                exit_portal = True
                continue
            elif SU <= t <= SR:
                d = t - SU
                step = DIR[d]
                for _ in range(3):
                    ahead = dest + step
                    if self.blocked(ahead, box):
                        if box and self.at(ahead) >= TNT:
                            self.armed.append(ahead)
                        break
                    dest = ahead
                if src == dest:
                    return
                continue
            elif NE <= t <= NW:
                d = MIRROR[t - NE][d]
            elif t != ICE:
                return
            dest = src + DIR[d]
            if self.blocked(dest, box):
                return

    def useful_jump(self, s, d, turn):
        step = DIR[d]
        mid = s.p + step
        c = self.at(mid)
        if BLOCK[s.flip][c & MASK]:
            return False
        end = mid + step
        if c >= BOX or c & MASK not in (FOG, FLOOR, K1, K2, VAULT, HEAL, RED, BLUE):
            return True
        if s.fuses or turn >= 233:
            return True
        if s.keys == 3 and distance(s.p, self.w.targets[2]) <= 2 * s.jumps:
            return True
        if turn <= 2 and s.jumps == 3:
            return True
        if self.w.has_beams:
            rays, _ = self.w.rays(s.edits, s.flip)
            if rays.get(s.p) or rays.get(mid) or rays.get(end):
                return True
        return False

    def useful_charge(self):
        for offset in AREA:
            c = self.at(self.p + offset)
            t = c & MASK
            if c >= BOX or t in (WALL, RED, BLUE, MIMIC, ICE) or t >= LU or NE <= t <= SR:
                return True
        return False

    def stone(self, d):
        p, portals = self.p, 0
        certain = True
        for n in range(1, 39):
            p += DIR[d]
            c = self.at(p)
            t = c & MASK
            if BLOCK[self.flip][t] or BOX <= c < TNT:
                return False
            if c >= TNT:
                self.armed.append(p)
                return True
            if t == SWITCH:
                self.flip ^= 1
                return True
            if t in (CHEST, MIMIC):
                self.put(p, FLOOR)
                if certain and t == CHEST:
                    self.probe = p
                return True
            if t == FOG:
                certain = False
            if NE <= t <= NW:
                d = MIRROR[t - NE][d]
            if P1A <= t <= P2B and portals < 2:
                pair = self.w.portals[(t - P1A) ^ 1]
                if pair < 0:
                    return False
                if self.at(pair) < BOX:
                    p = pair
                    portals += 1
                    if portals == 2:
                        return False
            if n >= 6 and t != ICE and not NE <= t <= NW:
                if n == 6 or not P1A <= t <= P2B:
                    return False
        return False

    def explode(self, tnts, due):
        sources = [(p, TNT) for p in tnts if self.at(p) >= TNT]
        sources.extend((p, 0) for p in due)
        if not sources:
            return
        bombs = dict(self.fuses)
        seen = set(sources)
        damaged = set()
        damage = 0
        for center, kind in sources:
            for off in AREA:
                p = center + off
                if p == self.p:
                    damage += 60 if kind == TNT else 50
                if p in damaged:
                    continue
                damaged.add(p)
                if p in bombs and (p, 0) not in seen:
                    seen.add((p, 0))
                    sources.append((p, 0))
                if self.at(p) >= TNT and (p, TNT) not in seen:
                    seen.add((p, TNT))
                    sources.append((p, TNT))
        self.hp -= damage
        self.fuses = tuple((p, t) for p, t in self.fuses if p not in damaged)
        for p in damaged:
            t = self.at(p) & MASK
            self.put(p, t if t in IMMUNE or t == FOG else PIT if t == CRACK else FLOOR)
        if self.at(self.p) & MASK == PIT and self.hp > 0:
            self.hp -= 100

    def play(self, s, action, phase, actual=False, opening=False):
        p = s.p
        j, b, stones = s.jumps, s.bombs, s.stones
        price = 1.0
        if action < 8:
            d = action % 4
            step = DIR[d]
            q = p + step
            c = self.at(q)
            if BLOCK[self.flip][c & MASK]:
                return None
            if action >= 4:
                if not j or self.blocked(q + step):
                    return None
                j -= 1
                # Spend surplus jumps on the final approach after saving enough
                # to cross obstacles which may still be hidden beyond sight.
                final_sprint = s.keys == 3 and distance(p, self.w.targets[2]) <= 2 * s.jumps
                price += 0.25 if final_sprint else (2.75, 3.65, 5.25)[2 - j]
                if c & MASK in (PIT, CHEST, MIMIC) or c >= BOX:
                    price -= 0.8
                if self.at(q + step) & MASK == FOG:
                    price += 2.8
                q += step
            elif c >= TNT:
                return None
            elif c >= BOX:
                if self.blocked(q + step, True):
                    return None
                self.advance(q, q + step, d, True)
                price += 2.1
                if self.blocked(q):
                    # A push can change the world even if the hero stays put.
                    q = p
            if q != p:
                self.advance(p, q, d)
        elif action == DROP:
            if not b or any(q == p for q, timer in self.fuses):
                return None
            b -= 1
            self.fuses = tuple(sorted(self.fuses + ((p, 3),)))
            price += 4.5 if b else 7.5
            if p in self.w.rubble:
                price -= 2.0
            elif any(p + k in self.w.rubble for k in AREA):
                price += 4.0
            cleared = sum(self.at(p + k) & MASK == WALL or self.at(p + k) & MASK >= LU for k in AREA)
            if cleared:
                price += 1.5 - 0.65 * min(6, cleared)
        elif action < WAIT:
            if not stones or not self.stone(action - 8):
                return None
            stones -= 1
            price += 1.0 if stones else 1.8

        if self.hp <= 0:
            return None
        if not self.won:
            if self.fuses:
                self.fuses = tuple((q, timer - 1) for q, timer in self.fuses)
            if self.armed or any(timer == 0 for _, timer in self.fuses):
                self.explode(set(self.armed), [q for q, timer in self.fuses if timer == 0])
            if self.hp <= 0:
                return None
        edits = tuple(sorted(self.cells.items()))
        if not self.won and self.w.has_beams and phase != 1:
            rays, hit_tnts = self.w.rays(edits, self.flip, actual)
            if phase == 0:
                struck = 0
                for q in self.path:
                    struck |= rays.get(q, 0)
                self.hp -= 50 * struck.bit_count()
                if self.hp > 0 and hit_tnts:
                    self.explode(set(hit_tnts), ())
                    edits = tuple(sorted(self.cells.items()))
                if self.hp <= 0:
                    return None
            else:
                # The origin of the following move is already exposed.
                pending = 50 * rays.get(self.p, 0).bit_count()
                if pending:
                    price += 2.0 + (35 if pending >= self.hp else 0)
        if s.flip != self.flip and self.w.preferred_flip is not None:
            if self.flip == self.w.preferred_flip:
                price = max(0.4, price - 1.5)
            else:
                price += 5.0
        if opening and not self.won:
            price += self.w.opening_risk(self.p)
        delta_hp = s.hp - self.hp
        if delta_hp > 0:
            price += delta_hp * 0.58
        elif delta_hp < 0:
            price = max(0.35, price - 1.8)
        price += self.uncertainty
        if self.p != p:
            price += 0.06 * min(12, self.w.visits[self.p])
            if self.at(self.p) & MASK == CRACK:
                price += 0.5
        next_state = State(self.p, self.hp, self.keys, self.flip, j, b, stones,
                           edits, self.fuses)
        return Transition(next_state, price, self.scout, self.won)


def relaxed_landing(w, q, d, flip):
    board = w.board
    portals, arriving = 0, False
    for _ in range(32):
        t = board[q] & MASK
        if arriving:
            arriving = False
            if portals == 2:
                break
        elif P1A <= t <= P2B:
            pair = w.portals[(t - P1A) ^ 1]
            if pair < 0 or board[pair] >= BOX:
                break
            q = pair
            arriving = True
            portals += 1
            continue
        elif SU <= t <= SR:
            d = t - SU
            step = DIR[d]
            landing = q
            for _ in range(3):
                c = board[landing + step]
                if c >= BOX or BLOCK[flip][c & MASK]:
                    break
                landing += step
            if q == landing:
                break
            q = landing
            continue
        elif NE <= t <= NW:
            d = MIRROR[t - NE][d]
        elif t != ICE:
            break
        nxt = q + DIR[d]
        c = board[nxt]
        if c >= BOX or BLOCK[flip][c & MASK]:
            break
        q = nxt
    return q


def flood(rev, seeds):
    values = [10000.] * len(rev)
    queue = []
    for p, cost in seeds:
        if cost < values[p]:
            values[p] = cost
            heappush(queue, (cost, p))
    while queue:
        cost, at = heappop(queue)
        if cost != values[at]:
            continue
        for prev, length in rev[at]:
            new = cost + length
            if new < values[prev]:
                values[prev] = new
                heappush(queue, (new, prev))
    return values


class Guide:
    """Reverse shortest paths through fog, including forced motion and gate parity."""

    def __init__(self, w, root):
        self.dual = bool(w.gates and w.switches)
        flips = (0, 1) if self.dual else (root.flip,)
        rev = [[] for _ in range(SIZE * len(flips))]
        board = w.board
        if root.fuses:
            forecast = Turn(w, root)
            forecast.explode((), [p for p, _ in root.fuses])
            board = board[:]
            for p, c in forecast.cells.items():
                board[p] = c
        goals = [(q, 0.) for i, q in enumerate(w.targets[:2]) if not root.keys & (1 << i)]
        if len(goals) == 2:
            a, b, v = w.targets
            da, db = distance(a, v), distance(b, v)
            goals = [(a, 0.8 * max(0, db - da)), (b, 0.8 * max(0, da - db))]
        elif not goals:
            goals = [(w.targets[2], 0.)]
        self.goal_cells = tuple(p for p, _ in goals)
        self.goals = dict(goals)
        self.scouts = {}
        for portal in range(4):
            p = w.portals[portal]
            if p >= 0 and w.portals[portal ^ 1] < 0:
                estimate = min(distance(p, g) + v for g, v in goals)
                penalty = min(30, 7 * w.mem.get("scouted", {}).get(str(p), 0))
                self.scouts[p] = 8.0 + 1.38 * estimate + penalty
        for flip in flips:
            level = SIZE * flip if self.dual else 0
            wall = BLOCK[flip]
            for q in INNER:
                c = board[q]
                t = c & MASK
                if t in (PIT, STEEL):
                    continue
                price = 1.
                if wall[t]:
                    if not root.bombs:
                        continue
                    price += 8.5 if root.bombs == 2 else 12.
                    if t in (RED, BLUE) and w.switches:
                        price += 7.
                elif c >= TNT:
                    if not (root.stones or root.bombs):
                        continue
                    price += 4.
                elif c >= BOX:
                    price += 1.8
                elif t == FOG:
                    price += 0.48 + w.fog_cost[q]
                elif t == CRACK:
                    price += 0.6
                elif t in (MIMIC, CHEST):
                    price += 2.7 if root.stones else 14.0
                motion = t == ICE or NE <= t <= P2B
                for d, step in enumerate(DIR):
                    p = q - step
                    mid = board[p] & MASK
                    if mid == STEEL:
                        continue
                    dest = relaxed_landing(w, q, d, flip) if motion else q
                    land = board[dest] & MASK
                    if land == PIT:
                        continue
                    if land == SWITCH and self.dual:
                        dest += SIZE - level
                    else:
                        dest += level
                    extra = 1.0 if motion and land == FOG else 0.0
                    if wall[t] and p in w.rubble:
                        # A charge inside an existing breach can cut its next
                        # layer. Avoid spending the last charge widening its lip.
                        extra -= 7.0 if root.bombs == 1 else 3.0
                    elif wall[t] and board[q + step] & MASK == FOG:
                        extra += 7.0 if root.bombs == 1 else 3.5
                    rev[dest].append((p + level, price + extra))
                    if root.jumps and not wall[mid]:
                        far = p - step
                        if board[far] & MASK != STEEL:
                            rev[dest].append((far + level, price + extra + 1.4))
            # A box pushed straight into a pit becomes a permanent bridge.
            # Include its approach square so the search can line up a long push.
            for box in INNER:
                if not BOX <= board[box] < TNT:
                    continue
                for step in DIR:
                    behind = box - step
                    if wall[board[behind] & MASK] or board[behind] >= BOX:
                        continue
                    lane = [behind, box]
                    q = box
                    for _ in range(12):
                        q += step
                        c = board[q]
                        if c == PIT:
                            for i, src in enumerate(lane):
                                rev[q + level].append((src + level, (len(lane) - i) * 1.6))
                            break
                        if c not in (FLOOR, FOG):
                            break
                        lane.append(q)
            if self.dual and root.stones:
                for q in w.switches:
                    for step in DIR:
                        p = q
                        for _ in range(6):
                            p += step
                            c = board[p]
                            t = c & MASK
                            if c >= BOX or wall[t] or t in (SWITCH, MIMIC) or NE <= t <= NW or P1A <= t <= P2B:
                                break
                            rev[p + SIZE - level].append((p + level, 2.4))
        if len(goals) == 2:
            a, b, v = w.targets
            def distances_to(q):
                return flood(rev, [(q + i * SIZE, 0.) for i in range(len(flips))])
            va, vb, vv = distances_to(a), distances_to(b), distances_to(v)
            def remaining(field, p):
                return min(field[p + i * SIZE] for i in range(len(flips)))
            after_a = remaining(vb, a) + remaining(vv, b)
            after_b = remaining(va, b) + remaining(vv, a)
            if min(after_a, after_b) < 9900:
                geometric = goals[0][1] - goals[1][1]
                observed = 1. - board.count(FOG) / len(INNER)
                trust = 0.2 + 0.65 * observed
                estimated = max(-24., min(24., after_a - after_b))
                bias = (1. - trust) * geometric + trust * estimated
                goals = [(a, max(0., bias)), (b, max(0., -bias))]
                self.goals = dict(goals)
        seeds = [(q + i * SIZE, price) for q, price in goals + list(self.scouts.items())
                 for i in range(len(flips))]
        self.values = flood(rev, seeds)
        self.heals = {}
        health_gain = min(30, 100 - root.hp)
        if health_gain >= 10 and (241 - w.turn > 12 or root.hp <= 50):
            for p in INNER:
                if board[p] != HEAL:
                    continue
                onward = min(self.at(p, f) for f in flips)
                # The heal is consumed exactly once. Compare its detour against
                # the health gained and how many turns remain in the game.
                benefit = health_gain * (0.95 if root.hp <= 50 else 0.68)
                if w.turn + self.at(root.p, root.flip) > 218:
                    benefit *= 0.4
                self.heals[p] = max(0., onward - benefit)
            if self.heals:
                seeds += [(p + i * SIZE, v) for p, v in self.heals.items()
                          for i in range(len(flips))]
                self.values = flood(rev, seeds)
        self.exploring = self.at(root.p, root.flip) >= 9900
        self.frontiers = {}
        stuck = w.stale >= 7 and w.mem["dry"] >= 6
        if self.exploring or stuck:
            fringe = [(p, 4. + 0.75 * min(distance(p, g) + v for g, v in goals))
                      for p in INNER if board[p] & MASK == FOG
                      and any(board[p + d] & MASK not in (FOG, STEEL) for d in DIR)]
            if fringe:
                if not self.exploring:
                    fringe = [(p, v + 10.) for p, v in fringe]
                self.frontiers = dict(fringe)
                self.values = flood(rev, seeds + [(p + i * SIZE, v) for p, v in fringe
                                                  for i in range(len(flips))])
        # States made newly reachable by demolition/pushes still get a gradient.
        for i, value in enumerate(self.values):
            if value >= 9900:
                self.values[i] = 28. + min(distance(i % SIZE, g) + v for g, v in goals)

    def at(self, p, flip):
        return self.values[p + SIZE * flip if self.dual else p]


def choose(w, s, root, guide, deadline):
    phase = w.turn % 3
    left = s["turns_left"]
    trip_key = (str(root.p) + "/" + str(phase) + "/" + str(root.flip) + "/"
                + str(root.keys) + "/" + str(root.jumps) + "/" + str(root.bombs))
    counts = w.mem["trips"].get(trip_key, {})
    wait_useful = w.has_beams or root.fuses
    root_options = {}
    fallback = (float("-inf"), WAIT)
    serial = 0
    heap = []
    best = {}
    goal_cost = float("inf")
    goal_action = None
    weight = 1.42
    # The search closes one key stage at a time; the guide prices the later order.
    def enqueue(result, action, depth, first, cost):
        nonlocal serial, goal_cost, goal_action
        ns = result.state
        if depth == 1:
            first = action
            root_options[action] = result
            cost += min(19, 2.8 * counts.get(str(action), 0))
        cost += result.cost
        frontier = ns.p in guide.frontiers and ns.p != root.p
        healed = ns.hp > root.hp and ns.p in guide.heals
        if ns.keys != root.keys or result.won or result.scout >= 0 or frontier or healed:
            value = 0.
            if result.scout >= 0 and not result.won and ns.keys == root.keys:
                value = guide.scouts.get(result.scout, guide.at(ns.p, ns.flip) + 4)
            elif healed and not result.won and ns.keys == root.keys:
                value = guide.heals[ns.p]
            elif frontier and not result.won and ns.keys == root.keys:
                value = guide.frontiers[ns.p]
            elif not result.won and root.keys == 0:
                key_at = w.targets[0] if ns.keys & 1 else w.targets[1]
                value = guide.goals.get(key_at, 0.)
            rank = cost + weight * value
            if rank < goal_cost:
                goal_cost, goal_action = rank, first
            return
        if depth >= left:
            return
        tick = (phase + depth) % 3 if w.has_beams else 0
        tag = (ns, tick)
        if cost >= best.get(tag, 1e9) - 0.0001:
            return
        best[tag] = cost
        h = guide.at(ns.p, ns.flip)
        rank = cost + weight * h
        serial += 1
        heappush(heap, (rank, h, serial, cost, ns, depth, first, tag))

    for action in range(14):
        if action == WAIT and not wait_useful:
            continue
        model = Turn(w, root)
        if action == DROP and not model.useful_charge():
            continue
        if 4 <= action < 8 and not model.useful_jump(root, action - 4, w.turn):
            continue
        result = model.play(root, action, phase, True, opening=w.turn == 2)
        if result is not None:
            enqueue(result, action, 1, action, 0.)
        # If all moves die on this tick, optimize actual key/distance progress.
        if model.p != root.p or action == WAIT:
            path = model.path
            remaining = guide.goal_cells
            if model.keys != root.keys:
                acquired = [w.targets[i] for i in range(2) if (model.keys ^ root.keys) & (1 << i)]
                last_pickup = max(path.index(q) for q in acquired)
                path = path[last_pickup:]
                remaining = tuple(w.targets[i] for i in range(2) if not model.keys & (1 << i)) or (w.targets[2],)
            proximity = min(distance(q, g) for q in path for g in remaining)
            rank = 10000 * model.won + 200 * model.keys.bit_count() - proximity + 0.001 * model.hp
            if rank > fallback[0]:
                fallback = (rank, action)

    if left == 1:
        return fallback[1], root_options
    # Take a nearby switch opportunity before leaving its range. If both
    # colors have been seen, the regular two-layer search decides the parity.
    prefer = w.preferred_flip
    if not w.gates and w.switches and sum(w.board.count(t) for t in (WALL, STEEL)) > 134:
        prefer = 1
    if prefer is not None and root.flip != prefer and left > 15 and root_options:
        def route_value(entry):
            ns = entry.state
            return entry.cost + guide.at(ns.p, ns.flip)
        available = [(route_value(result), action) for action, result in root_options.items()
                     if result.state.flip == prefer and result.state.hp >= root.hp
                     and result.scout < 0 and result.cost < 6.]
        if available:
            price, action = min(available)
            ordinary = min(route_value(result) for result in root_options.values())
            if price <= ordinary + (4.0 if w.gates else 2.5):
                return action, root_options
    expansions = 0
    while heap:
        rank, h, _, cost, node, depth, first, tag = heappop(heap)
        if cost != best.get(tag):
            continue
        if goal_cost <= rank:
            break
        if expansions >= 850 or (expansions % 8 == 0 and perf_counter() >= deadline):
            return first, root_options
        expansions += 1
        tick = (phase + depth) % 3
        for action in range(14):
            if 4 <= action < 8 and not node.jumps:
                continue
            if 8 <= action < WAIT and not node.stones:
                continue
            if action == WAIT and not (w.has_beams or node.fuses):
                continue
            if action == DROP and not node.bombs:
                continue
            model = Turn(w, node)
            if action == DROP and not model.useful_charge():
                continue
            if 4 <= action < 8 and not model.useful_jump(node, action - 4, w.turn + depth):
                continue
            result = model.play(node, action, tick, opening=w.turn + depth == 2)
            if result is not None:
                enqueue(result, action, depth + 1, first, cost)
    if goal_action is not None:
        return goal_action, root_options
    if root_options:
        def priority(item):
            action, result = item
            ns = result.state
            return (guide.at(ns.p, ns.flip) + result.cost + 3 * counts.get(str(action), 0)
                    + 0.4 * w.visits[ns.p])
        return min(root_options.items(), key=priority)[0], root_options
    return fallback[1], root_options


def decide_action(state, memory):
    deadline = perf_counter() + 0.155
    p, keys, targets, visible = remember(state, memory)
    w = World(state, memory, targets, visible)
    h = state["hero"]
    root = State(p, h["hp"], keys, int(state["gates_flipped"]), h["jumps"],
                 h["bombs"], h["throws"], (),
                 tuple(sorted((a["y"] * WIDTH + a["x"], a["timer"]) for a in state["bombs"])))
    guide = Guide(w, root)
    action, options = choose(w, state, root, guide, deadline)
    trip_key = (str(p) + "/" + str(w.turn % 3) + "/" + str(root.flip) + "/"
                + str(keys) + "/" + str(root.jumps) + "/" + str(root.bombs))
    trips = memory["trips"].setdefault(trip_key, {})
    trips[str(action)] = trips.get(str(action), 0) + 1
    if action in options:
        result = options[action]
        ns = result.state
        memory["predicted"] = [ns.p, ns.flip, list(ns.edits)]
        if result.scout >= 0:
            scouts = memory.setdefault("scouted", {})
            scouts[str(result.scout)] = scouts.get(str(result.scout), 0) + 1
        if 8 <= action < WAIT:
            stone = Turn(w, root)
            stone.stone(action - 8)
            if stone.probe >= 0:
                memory["probe"] = stone.probe
    return ACTIONS[action]

