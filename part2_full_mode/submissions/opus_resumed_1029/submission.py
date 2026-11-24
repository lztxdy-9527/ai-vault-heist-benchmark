"""
Submission v2.2 FULL: 阴间地牢·金库攻防战（下半场）
No I/O, no reflection builtins.
"""
import heapq
import time

W_, H_ = 40, 26
DIRV = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}
SPRINGS = {"SPRING_U": "U", "SPRING_D": "D", "SPRING_L": "L", "SPRING_R": "R"}
ONEWAY = {"ONEWAY_U": "U", "ONEWAY_D": "D", "ONEWAY_L": "L", "ONEWAY_R": "R"}
PAIRS = {"PORTAL_1A": "PORTAL_1B", "PORTAL_1B": "PORTAL_1A",
         "PORTAL_2A": "PORTAL_2B", "PORTAL_2B": "PORTAL_2A"}
LASERS = {"LASER_U": ("U", 3), "LASER_D": ("D", 3), "LASER_L": ("L", 3), "LASER_R": ("R", 3),
          "LASER2_U": ("U", 4), "LASER2_D": ("D", 4), "LASER2_L": ("L", 4), "LASER2_R": ("R", 4)}
HIGH = {"W", "T_W"} | set(LASERS)
KV = {"K1", "K2", "V"}
BOMB_IMMUNE = {"T_W", "K1", "K2", "V", "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B", "PIT",
               "PLATE", "P_GATE", "ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R"}
BOMBABLE_WALL = {"W", "R_GATE", "B_GATE"} | set(LASERS)
VALID_ACTIONS = ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT",
                 "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
                 "THROW_U", "THROW_D", "THROW_L", "THROW_R", "BOMB")


# ==============================================================================
# Physics engine
# ==============================================================================
class Game:
    def init(self, T, O, hx, hy, hp=100, k1=False, k2=False, jumps=3, throws=3,
             nb=2, gates=False, bombs=None, turn=1):
        self.T = T
        self.O = O
        self.hx, self.hy = hx, hy
        self.hp = hp
        self.k1, self.k2 = k1, k2
        self.jumps, self.throws, self.nb = jumps, throws, nb
        self.gates = gates
        self.bombs = bombs if bombs is not None else []
        self.turn = turn
        self.trap = 0.0
        self.status = "ALIVE"
        self.next_id = 1000
        self.log = None
        self.portals = {}
        self.plates = []
        self.cannons = []
        for y in range(H_):
            row = T[y]
            for x in range(W_):
                t = row[x]
                if t in PAIRS:
                    self.portals[t] = (x, y)
                elif t == "PLATE":
                    self.plates.append((x, y))
                elif t in LASERS:
                    self.cannons.append((x, y))
        self.exposed = set()
        self.tnt_armed = set()
        return self

    def setT(self, x, y, v):
        if self.log is not None:
            self.log.append((0, x, y, self.T[y][x]))
        self.T[y][x] = v

    def setO(self, x, y, v):
        if self.log is not None:
            self.log.append((1, x, y, self.O[y][x]))
        self.O[y][x] = v

    def undo(self):
        lg = self.log
        while lg:
            k, x, y, v = lg.pop()
            if k == 0:
                self.T[y][x] = v
            else:
                self.O[y][x] = v

    def plates_active(self):
        if not self.plates:
            return False
        O = self.O
        for (x, y) in self.plates:
            if O[y][x] != "BOX":
                return False
        return True

    def wall(self, x, y):
        if x < 0 or y < 0 or x >= W_ or y >= H_:
            return True
        t = self.T[y][x]
        if t in HIGH:
            return True
        if t == "R_GATE":
            return not self.gates
        if t == "B_GATE":
            return self.gates
        if t == "P_GATE":
            return not self.plates_active()
        return False

    def bow(self, x, y, d):
        t = self.T[y][x]
        return t in ONEWAY and ONEWAY[t] != d

    def dmg_trap(self, d):
        self.trap += min(max(self.hp, 0), d)
        self.hp -= d

    def enterable(self, ent, x, y, d):
        if self.wall(x, y):
            return False
        o = self.O[y][x]
        if o == "BOX" or o == "TNT":
            return False
        if self.bow(x, y, d):
            return False
        if ent == "B":
            if (x, y) == (self.hx, self.hy) or self.T[y][x] in KV:
                return False
        return True

    def chain(self, ent, x0, y0, x1, y1, d):
        steps = 0
        portals = 0
        just_portal = False
        while True:
            steps += 1
            if self.T[y0][x0] == "CRACK":
                self.setT(x0, y0, "PIT")
            if ent == "B":
                self.setO(x0, y0, None)
                self.setO(x1, y1, "BOX")
            else:
                self.hx, self.hy = x1, y1
                self.exposed.add((x1, y1))
            t = self.T[y1][x1]
            stop = False
            if ent == "B":
                if t == "PIT":
                    self.setO(x1, y1, None)
                    self.setT(x1, y1, "EMPTY")
                    return
                elif t == "MIMIC":
                    self.setT(x1, y1, "EMPTY")
                elif t == "SWITCH":
                    self.gates = not self.gates
            else:
                if t == "PIT":
                    self.dmg_trap(100)
                elif t == "MIMIC":
                    self.dmg_trap(45)
                    self.setT(x1, y1, "EMPTY")
                    stop = True
                elif t == "HEAL":
                    self.hp = min(100, self.hp + 30)
                    self.setT(x1, y1, "EMPTY")
                elif t == "SWITCH":
                    self.gates = not self.gates
                if self.hp <= 0:
                    self.status = "DEAD"
                    return
                if t == "K1":
                    self.k1 = True
                    self.setT(x1, y1, "EMPTY")
                elif t == "K2":
                    self.k2 = True
                    self.setT(x1, y1, "EMPTY")
                elif t == "V" and self.k1 and self.k2:
                    self.status = "WIN"
                    return
            if steps >= 32 or stop:
                return
            t = self.T[y1][x1]
            dx, dy = DIRV[d]
            if just_portal:
                just_portal = False
                if portals >= 2:
                    return
                nx, ny = x1 + dx, y1 + dy
                if self.enterable(ent, nx, ny, d):
                    x0, y0, x1, y1 = x1, y1, nx, ny
                    continue
                return
            if t == "ICE" or t in MIRROR_MAP:
                if t != "ICE":
                    d = MIRROR_MAP[t][d]
                    dx, dy = DIRV[d]
                nx, ny = x1 + dx, y1 + dy
                if self.enterable(ent, nx, ny, d):
                    x0, y0, x1, y1 = x1, y1, nx, ny
                    continue
                return
            if t in SPRINGS:
                d = SPRINGS[t]
                dx, dy = DIRV[d]
                land = None
                for k in (1, 2, 3):
                    px, py = x1 + k * dx, y1 + k * dy
                    blk = self.wall(px, py)
                    if not blk:
                        o = self.O[py][px]
                        if o == "BOX" or o == "TNT":
                            blk = True
                            if ent == "B" and o == "TNT":
                                self.tnt_armed.add((px, py))
                        elif self.bow(px, py, d):
                            blk = True
                        elif ent == "B" and ((px, py) == (self.hx, self.hy) or self.T[py][px] in KV):
                            blk = True
                    if blk:
                        if k == 1:
                            return
                        land = (x1 + (k - 1) * dx, y1 + (k - 1) * dy)
                        break
                if land is None:
                    land = (x1 + 3 * dx, y1 + 3 * dy)
                x0, y0, x1, y1 = x1, y1, land[0], land[1]
                continue
            if t in PAIRS:
                pp = self.portals.get(PAIRS[t])
                if pp is None:
                    return
                px, py = pp
                if self.O[py][px] is not None:
                    return
                if ent == "B" and (px, py) == (self.hx, self.hy):
                    return
                portals += 1
                just_portal = True
                x0, y0, x1, y1 = x1, y1, px, py
                continue
            return

    def act(self, a):
        self.exposed = {(self.hx, self.hy)}
        self.tnt_armed = set()
        hx, hy = self.hx, self.hy
        if a == "BOMB":
            if self.nb > 0 and not any(b["x"] == hx and b["y"] == hy for b in self.bombs):
                self.nb -= 1
                self.bombs.append({"id": self.next_id, "x": hx, "y": hy, "timer": 3})
                self.next_id += 1
        elif a.startswith("MOVE_"):
            d = a[5]
            dx, dy = DIRV[d]
            x1, y1 = hx + dx, hy + dy
            if self.wall(x1, y1) or self.O[y1][x1] == "TNT" or self.bow(x1, y1, d):
                pass
            elif self.O[y1][x1] == "BOX":
                x2, y2 = hx + 2 * dx, hy + 2 * dy
                if ((not self.wall(x2, y2)) and self.O[y2][x2] is None and self.T[y2][x2] not in KV
                        and not self.bow(x2, y2, d)):
                    self.chain("B", x1, y1, x2, y2, d)
                    if (not self.wall(x1, y1)) and self.O[y1][x1] is None and not self.bow(x1, y1, d):
                        self.chain("H", hx, hy, x1, y1, d)
            else:
                self.chain("H", hx, hy, x1, y1, d)
        elif a.startswith("JUMP_"):
            if self.jumps > 0:
                self.jumps -= 1
                d = a[5]
                dx, dy = DIRV[d]
                x1, y1 = hx + dx, hy + dy
                x2, y2 = hx + 2 * dx, hy + 2 * dy
                if not (self.wall(x1, y1) or self.bow(x1, y1, d) or self.wall(x2, y2)
                        or self.O[y2][x2] is not None or self.bow(x2, y2, d)):
                    self.chain("H", hx, hy, x2, y2, d)
        elif a.startswith("THROW_"):
            if self.throws > 0:
                self.throws -= 1
                self.throw(a[6])

    def throw(self, d):
        sx, sy = self.hx, self.hy
        rng = 6
        sp = 0
        while rng > 0:
            dx, dy = DIRV[d]
            sx += dx
            sy += dy
            rng -= 1
            if self.wall(sx, sy) or self.O[sy][sx] == "BOX":
                return
            if self.O[sy][sx] == "TNT":
                self.tnt_armed.add((sx, sy))
                return
            t = self.T[sy][sx]
            if t == "SWITCH":
                self.gates = not self.gates
                return
            if t == "MIMIC":
                self.setT(sx, sy, "EMPTY")
                return
            if t in MIRROR_MAP:
                d = MIRROR_MAP[t][d]
            elif t in PAIRS and sp < 2:
                pp = self.portals.get(PAIRS[t])
                if pp and self.O[pp[1]][pp[0]] not in ("BOX", "TNT"):
                    sx, sy = pp
                    sp += 1
                    if sp == 2:
                        return
        t = self.T[sy][sx]
        if not (t == "ICE" or t in MIRROR_MAP):
            return
        for _ in range(32):
            dx, dy = DIRV[d]
            sx += dx
            sy += dy
            if self.wall(sx, sy) or self.O[sy][sx] == "BOX":
                return
            if self.O[sy][sx] == "TNT":
                self.tnt_armed.add((sx, sy))
                return
            t = self.T[sy][sx]
            if t == "SWITCH":
                self.gates = not self.gates
                return
            if t == "MIMIC":
                self.setT(sx, sy, "EMPTY")
                return
            if t in MIRROR_MAP:
                d = MIRROR_MAP[t][d]
                continue
            if t == "ICE":
                continue
            if t in PAIRS and sp < 2:
                pp = self.portals.get(PAIRS[t])
                if pp and self.O[pp[1]][pp[0]] not in ("BOX", "TNT"):
                    sx, sy = pp
                    sp += 1
                    if sp == 2:
                        return
                    continue
            return

    def explode(self, init_bombs, init_tnt):
        eb = set()
        et = set()
        srcs = []
        q = []
        for b in init_bombs:
            if b["id"] not in eb:
                eb.add(b["id"])
                q.append(("B", b["x"], b["y"]))
        for p in init_tnt:
            if p not in et and self.O[p[1]][p[0]] == "TNT":
                et.add(p)
                q.append(("T", p[0], p[1]))
        bpos = {}
        for b in self.bombs:
            bpos.setdefault((b["x"], b["y"]), []).append(b)
        qi = 0
        while qi < len(q):
            s = q[qi]
            qi += 1
            srcs.append(s)
            _, ex, ey = s
            for yy in range(ey - 1, ey + 2):
                for xx in range(ex - 1, ex + 2):
                    if 0 <= xx < W_ and 0 <= yy < H_:
                        if self.O[yy][xx] == "TNT" and (xx, yy) not in et:
                            et.add((xx, yy))
                            q.append(("T", xx, yy))
                        for b in bpos.get((xx, yy), ()):
                            if b["id"] not in eb:
                                eb.add(b["id"])
                                q.append(("B", xx, yy))
        if not srcs:
            return
        a = 0
        bb = 0
        for k, ex, ey in srcs:
            if abs(ex - self.hx) <= 1 and abs(ey - self.hy) <= 1:
                if k == "T":
                    a += 60
                else:
                    bb += 50
        if a + bb > 0:
            self.trap += min(max(self.hp, 0), a + bb) * a / (a + bb)
            self.hp -= a + bb
        self.bombs = [b for b in self.bombs if b["id"] not in eb]
        for p in et:
            self.setO(p[0], p[1], None)
        cells = set()
        for k, ex, ey in srcs:
            for yy in range(ey - 1, ey + 2):
                for xx in range(ex - 1, ex + 2):
                    if 0 <= xx < W_ and 0 <= yy < H_:
                        cells.add((xx, yy))
        for (cx, cy) in cells:
            if self.O[cy][cx] == "BOX":
                self.setO(cx, cy, None)
            t = self.T[cy][cx]
            if t in BOMB_IMMUNE or t == "EMPTY":
                continue
            if t == "CRACK":
                self.setT(cx, cy, "PIT")
            else:
                self.setT(cx, cy, "EMPTY")
        for (x, y) in cells:
            if self.O[y][x] == "BOX" and self.T[y][x] == "PIT":
                self.setO(x, y, None)
                self.setT(x, y, "EMPTY")
        if self.hp > 0 and self.T[self.hy][self.hx] == "PIT":
            self.dmg_trap(100)
        if self.hp <= 0:
            self.status = "DEAD"

    def beams(self, turn):
        res = []
        f3 = turn % 3 == 0
        f4 = turn % 4 == 0
        if not (f3 or f4):
            return res
        for (x, y) in self.cannons:
            t = self.T[y][x]
            if t not in LASERS:
                continue
            d, per = LASERS[t]
            if (per == 3 and not f3) or (per == 4 and not f4):
                continue
            dx, dy = DIRV[d]
            cells = set()
            tnt = None
            for k in range(1, 11):
                px, py = x + k * dx, y + k * dy
                if self.wall(px, py) or self.O[py][px] == "BOX":
                    break
                if self.O[py][px] == "TNT":
                    tnt = (px, py)
                    break
                cells.add((px, py))
            res.append((cells, tnt))
        return res

    def phases(self):
        if self.bombs or self.tnt_armed:
            for b in self.bombs:
                b["timer"] -= 1
            ib = [b for b in self.bombs if b["timer"] <= 0]
            if ib or self.tnt_armed:
                self.explode(ib, list(self.tnt_armed))
                if self.status == "DEAD":
                    return
        if self.cannons and (self.turn % 3 == 0 or self.turn % 4 == 0):
            bl = self.beams(self.turn)
            m = 0
            lt = []
            for cells, tnt in bl:
                if cells & self.exposed:
                    m += 1
                if tnt and tnt not in lt:
                    lt.append(tnt)
            if m:
                self.dmg_trap(50 * m)
                if self.hp <= 0:
                    self.status = "DEAD"
                    return
            if lt:
                self.explode([], lt)

    def full_turn(self, a):
        self.act(a)
        if self.status == "ALIVE":
            self.phases()
        self.turn += 1
        return self.status


def make_game(grid):
    T = [[("EMPTY" if c in ("BOX", "TNT") else c) for c in row] for row in grid]
    O = [[(c if c in ("BOX", "TNT") else None) for c in row] for row in grid]
    return Game().init(T, O, 2, 13)


# ==============================================================================
# Planner (full-state weighted A* over the exact engine)
# ==============================================================================
def _dist_field(T, src, wallcost):
    INF = 10 ** 9
    dist = [[INF] * W_ for _ in range(H_)]
    portals = {}
    for yy in range(H_):
        for xx in range(W_):
            if T[yy][xx] in PAIRS:
                portals[T[yy][xx]] = (xx, yy)
    rev = {}
    for a, (ax, ay) in portals.items():
        b = portals.get(PAIRS[a])
        if b is None:
            continue
        bx, by = b
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            cx, cy = ax - dx, ay - dy
            ex, ey = bx + dx, by + dy
            if not (0 < cx < W_ - 1 and 0 < cy < H_ - 1):
                continue
            if T[cy][cx] in PAIRS or wallcost.get(T[cy][cx], 1) is None:
                continue
            if not (0 < ex < W_ - 1 and 0 < ey < H_ - 1) or T[ey][ex] in HIGH or T[ey][ex] in PAIRS:
                ex, ey = bx, by
            rev.setdefault((ex, ey), []).append((cx, cy))
    sx, sy = src
    dist[sy][sx] = 0
    pq = [(0, sx, sy)]
    while pq:
        d, x, y = heapq.heappop(pq)
        if d > dist[y][x]:
            continue
        for (cx, cy) in rev.get((x, y), ()):
            nd = d + wallcost.get(T[cy][cx], 1)
            if nd < dist[cy][cx]:
                dist[cy][cx] = nd
                heapq.heappush(pq, (nd, cx, cy))
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = x + dx, y + dy
            if nx <= 0 or ny <= 0 or nx >= W_ - 1 or ny >= H_ - 1:
                continue
            if T[ny][nx] in PAIRS:
                continue
            c = wallcost.get(T[ny][nx], 1)
            if c is None:
                continue
            nd = d + c
            if nd < dist[ny][nx]:
                dist[ny][nx] = nd
                heapq.heappush(pq, (nd, nx, ny))
    for (px, py) in portals.values():
        best = INF
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            v = dist[py + dy][px + dx] if (0 <= px + dx < W_ and 0 <= py + dy < H_) else INF
            if v < best:
                best = v
        if best < INF and best + 1 < dist[py][px]:
            dist[py][px] = best + 1
    return dist


def _jump_field(T, src):
    INF = 10 ** 6
    dist = [[INF] * W_ for _ in range(H_)]
    portals = {}
    for y in range(H_):
        for x in range(W_):
            if T[y][x] in PAIRS:
                portals[T[y][x]] = (x, y)

    def ok(x, y):
        return 0 < x < W_ - 1 and 0 < y < H_ - 1 and T[y][x] != "T_W" and T[y][x] != "PIT"

    srev = {}
    for y in range(1, H_ - 1):
        for x in range(1, W_ - 1):
            if T[y][x] in SPRINGS:
                dx, dy = DIRV[SPRINGS[T[y][x]]]
                for k in (1, 2, 3):
                    px, py = x + k * dx, y + k * dy
                    if not (0 < px < W_ - 1 and 0 < py < H_ - 1) or T[py][px] == "T_W":
                        break
                    if T[py][px] == "PIT":
                        continue
                    srev.setdefault((px, py), []).append((x, y))
    sx, sy = src
    dist[sy][sx] = 0
    dq = [(0, sx, sy)]
    while dq:
        d, x, y = heapq.heappop(dq)
        if d > dist[y][x]:
            continue
        nb = []
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = x + dx, y + dy
            if ok(nx, ny) and T[ny][nx] not in SPRINGS:
                nb.append((nx, ny, 0))
            mx, my = x + 2 * dx, y + 2 * dy
            if (0 < nx < W_ - 1 and 0 < ny < H_ - 1 and T[ny][nx] != "T_W" and ok(mx, my)
                    and T[my][mx] not in SPRINGS):
                nb.append((mx, my, 1))
        t = T[y][x]
        if t in PAIRS and PAIRS[t] in portals:
            px, py = portals[PAIRS[t]]
            nb.append((px, py, 0))
        for (px, py) in srev.get((x, y), ()):
            nb.append((px, py, 0))
        for nx, ny, c in nb:
            if d + c < dist[ny][nx]:
                dist[ny][nx] = d + c
                heapq.heappush(dq, (d + c, nx, ny))
    return dist

class Planner:
    def init(self, T, O, hero, gates, bombs, turn):
        self.T0 = T
        self.O0 = O
        g = Game().init(T, O, hero["x"], hero["y"], hp=hero["hp"], k1=hero["keys"][0],
                        k2=hero["keys"][1], jumps=hero["jumps"], throws=hero["throws"],
                        nb=hero["bombs"], gates=gates, bombs=bombs, turn=turn)
        self.g = g
        self.turn0 = turn
        self.root = None
        self.W = 1.5
        wc = {"T_W": None, "PIT": 3, "W": 4, "R_GATE": 2, "B_GATE": 2, "P_GATE": 2, "MIMIC": 4}
        for k in LASERS:
            wc[k] = 6
        self.targets = {}
        for y in range(H_):
            for x in range(W_):
                if T[y][x] in KV:
                    self.targets[T[y][x]] = (x, y)
        self.fields = {}
        for k, p in self.targets.items():
            self.fields[k] = _dist_field(T, p, wc)
        self.jf = None
        self.jw = 30 if any(c == "BOX" for r in O for c in r) else 200
        if True:
            self.jf = {k: _jump_field(T, p) for k, p in self.targets.items()}
        self.has_switch = any(T[y][x] == "SWITCH" for y in range(H_) for x in range(W_))
        self.has_throw_targets = self.has_switch or any(
            T[y][x] == "MIMIC" or O[y][x] == "TNT" for y in range(H_) for x in range(W_))
        self.has_bombable = any(T[y][x] in BOMBABLE_WALL for y in range(1, H_ - 1) for x in range(1, W_ - 1))
        if g.cannons:
            pers = set(LASERS[T[y][x]][1] for (x, y) in g.cannons)
            self.tmod = 12 if len(pers) == 2 else (3 if 3 in pers else 4)
        else:
            self.tmod = 1
        self.zone = set()
        for (cx, cy) in g.cannons:
            d, per = LASERS[T[cy][cx]]
            dx, dy = DIRV[d]
            for k in range(1, 11):
                px, py = cx + k * dx, cy + k * dy
                if px <= 0 or py <= 0 or px >= W_ - 1 or py >= H_ - 1 or T[py][px] == "T_W":
                    break
                for ex in (-2, -1, 0, 1, 2):
                    for ey in (-2, -1, 0, 1, 2):
                        if abs(ex) + abs(ey) <= 2:
                            self.zone.add((px + ex, py + ey))
        self.plate_fields = []
        self.need_plates = False
        if g.plates and any(T[y][x] == "P_GATE" for y in range(H_) for x in range(W_)):
            self.need_plates = True
            pwc = {"T_W": None, "W": None, "PIT": None, "P_GATE": None}
            for k in LASERS:
                pwc[k] = None
            for p in g.plates:
                self.plate_fields.append((p, _dist_field(T, p, pwc)))
        return self

    def h(self, g, osig=None):
        F = self.fields
        x, y = g.hx, g.hy
        k1p = self.targets.get("K1")
        k2p = self.targets.get("K2")
        if g.k1 and g.k2:
            v = F["V"][y][x]
        elif g.k1:
            v = F["K2"][y][x] + F["V"][k2p[1]][k2p[0]]
        elif g.k2:
            v = F["K1"][y][x] + F["V"][k1p[1]][k1p[0]]
        else:
            a = F["K1"][y][x] + F["K2"][k1p[1]][k1p[0]] + F["V"][k2p[1]][k2p[0]]
            b = F["K2"][y][x] + F["K1"][k2p[1]][k2p[0]] + F["V"][k1p[1]][k1p[0]]
            v = min(a, b)
        JF = self.jf
        if JF is not None:
            if g.k1 and g.k2:
                need = JF["V"][y][x]
            elif g.k1:
                need = JF["K2"][y][x] + JF["V"][k2p[1]][k2p[0]]
            elif g.k2:
                need = JF["K1"][y][x] + JF["V"][k1p[1]][k1p[0]]
            else:
                need = min(JF["K1"][y][x] + JF["K2"][k1p[1]][k1p[0]] + JF["V"][k2p[1]][k2p[0]],
                           JF["K2"][y][x] + JF["K1"][k2p[1]][k2p[0]] + JF["V"][k1p[1]][k1p[0]])
            if need > g.jumps:
                v += self.jw * (need - g.jumps)
        if self.need_plates and not g.plates_active():
            O = g.O
            if osig is None:
                osig = self._osig(O)
            boxes = [(bx, by) for (bx, by, kind) in osig if kind == "BOX"]
            extra = 0
            free = [b for b in boxes if g.T[b[1]][b[0]] != "PLATE"]
            for (p, pf) in self.plate_fields:
                if O[p[1]][p[0]] == "BOX":
                    continue
                best = 10 ** 6
                for (bx, by) in free:
                    dd = pf[by][bx] * 3 + abs(bx - x) + abs(by - y)
                    if dd < best:
                        best = dd
                extra += best
            v += extra
        return v

    def search(self, budget, t0, W=None):
        g = self.g
        if self.root is None:
            self.root = (g.T, g.O, g.hx, g.hy, g.hp, g.k1, g.k2, g.jumps, g.throws, g.nb, g.gates,
                         [dict(b) for b in g.bombs], g.turn, (), self._osig(g.O))
        root = self.root
        self._load(root)
        nodes = [(root, -1, None)]
        best_seen = {}
        h0 = self.h(g, root[14])
        if W is None:
            W = self.W
        pq = [(h0 * W, 0.0, 0)]
        best_partial = (10 ** 12, 0)
        cnt = 0
        tmod = self.tmod
        zone = self.zone
        while pq:
            if (cnt & 3) == 0 and time.perf_counter() - t0 > budget:
                break
            cnt += 1
            f, gc, idx = heapq.heappop(pq)
            st = nodes[idx][0]
            if st[12] > 240:
                continue
            acts = ["MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R"]
            if st[11] or (tmod > 1 and (st[2], st[3]) in zone):
                acts.append("WAIT")
            if st[7] > 0:
                acts += ["JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R"]
            if st[9] > 0 and self.has_bombable and not st[11]:
                hx, hy = st[2], st[3]
                T = st[0]
                ok = False
                for yy in range(hy - 1, hy + 2):
                    for xx in range(hx - 1, hx + 2):
                        if T[yy][xx] in BOMBABLE_WALL and 0 < xx < W_ - 1 and 0 < yy < H_ - 1:
                            ok = True
                if ok:
                    acts.append("BOMB")
            if st[8] > 0 and self.has_throw_targets:
                acts += ["THROW_U", "THROW_D", "THROW_L", "THROW_R"]
            for a in acts:
                child = self._step(st, a)
                if child is None:
                    continue
                cst, status = child
                if status == "WIN":
                    nodes.append((cst, idx, a))
                    return self._path(nodes, len(nodes) - 1), True
                if ((cst[2], cst[3]) == (st[2], st[3]) and a != "WAIT" and a != "BOMB"
                        and cst[10] == st[10] and cst[14] == st[14] and cst[13] == st[13]):
                    continue
                tk = cst[12] % tmod if ((cst[2], cst[3]) in zone or cst[11]) else -1
                kd = cst[13]
                if kd:
                    T0k = self.T0
                    kd = tuple(e for e in kd if T0k[e[0][1]][e[0][0]] not in ("CRACK", "HEAL", "MIMIC"))
                key = (cst[2], cst[3], cst[5], cst[6], cst[10], tk, cst[9],
                       kd, cst[14], tuple((b["x"], b["y"], b["timer"]) for b in cst[11]))
                val = cst[4] * 100 + cst[7] * 12 + cst[8] * 3
                prev = best_seen.get(key)
                if prev is not None and prev >= val:
                    continue
                best_seen[key] = val
                nodes.append((cst, idx, a))
                ni = len(nodes) - 1
                self._load(cst)
                hv = self.h(g, cst[14])
                c = 1.0
                if a[0] == "J":
                    c = 3.0
                elif a[0] == "T":
                    c = 4.0
                elif a[0] == "B":
                    c = 6.0
                g2 = gc + c + (st[4] - cst[4]) * 0.4
                heapq.heappush(pq, (g2 + W * hv, g2, ni))
                score = hv + g2 * 0.02
                if score < best_partial[0]:
                    best_partial = (score, ni)
        return self._path(nodes, best_partial[1]), False

    def _osig(self, O):
        res = []
        for y in range(H_):
            row = O[y]
            for x in range(W_):
                if row[x] is not None:
                    res.append((x, y, row[x]))
        return tuple(res)

    def _load(self, st):
        g = self.g
        (g.T, g.O, g.hx, g.hy, g.hp, g.k1, g.k2, g.jumps, g.throws, g.nb, g.gates,
         _b, g.turn, _d, _o) = st
        g.bombs = [dict(b) for b in st[11]]
        g.status = "ALIVE"
        g.trap = 0.0

    def _step(self, st, a):
        g = self.g
        self._load(st)
        g.log = []
        g.full_turn(a)
        status = g.status
        if status == "DEAD":
            g.undo()
            g.log = None
            return None
        lg = g.log
        T, O = st[0], st[1]
        tdiff = st[13]
        osig = st[14]
        if lg:
            tcells = set((e[1], e[2]) for e in lg if e[0] == 0)
            tch = bool(tcells)
            och = any(e[0] == 1 for e in lg)
            g.undo()
            g.log = None
            nT = [r[:] for r in T] if tch else T
            nO = [r[:] for r in O] if och else O
            self._load(st)
            g.T, g.O = nT, nO
            g.full_turn(a)
            if tch:
                d = dict(tdiff)
                T0 = self.T0
                for (x, y) in tcells:
                    if nT[y][x] == T0[y][x]:
                        d.pop((x, y), None)
                    else:
                        d[(x, y)] = nT[y][x]
                tdiff = tuple(sorted(d.items()))
            if och:
                osig = self._osig(nO)
        else:
            g.log = None
            nT, nO = T, O
        cst = (nT, nO, g.hx, g.hy, g.hp, g.k1, g.k2, g.jumps, g.throws, g.nb, g.gates,
               [dict(b) for b in g.bombs], g.turn, tdiff, osig)
        return cst, status

    def _path(self, nodes, idx):
        acts = []
        states = []
        while idx > 0:
            st, p, a = nodes[idx]
            acts.append(a)
            states.append((st[2], st[3], st[4], st[12], st[5], st[6]))
            idx = p
        acts.reverse()
        states.reverse()
        return acts, states


def _decode(state):
    terr = state["terrain"]
    occ = state["occupant"]
    clues = state.get("clues")
    T = [list(r) for r in terr]
    O = [list(r) for r in occ]
    for y in range(H_):
        for x in range(W_):
            if T[y][x] == "CHEST":
                mim = False
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W_ and 0 <= ny < H_ and clues and clues[ny][nx]:
                        mim = True
                T[y][x] = "MIMIC" if mim else "HEAL"
            elif T[y][x] == "UNKNOWN":
                T[y][x] = "EMPTY"
    return T, O


def _choose(state, memory):
    t0 = time.perf_counter()
    h = state["hero"]
    turn = state["turn"]
    cur = (h["x"], h["y"], h["hp"], turn, h["keys"][0], h["keys"][1])
    plan = memory.get("plan")
    if plan and memory.get("expect") == cur and memory.get("pi", 0) < len(plan[0]):
        i = memory["pi"]
        if memory.get("plan_full") or i < 6:
            memory["pi"] = i + 1
            nxt = plan[1][i]
            memory["expect"] = (nxt[0], nxt[1], nxt[2], nxt[3], nxt[4], nxt[5])
            return plan[0][i]
    T, O = _decode(state)
    bombs = [{"id": i, "x": b["x"], "y": b["y"], "timer": b["timer"]}
             for i, b in enumerate(state.get("bombs") or [])]
    P = Planner().init(T, O, h, state.get("gates_flipped", False), bombs, turn)
    if turn == 1 and memory.get("plan") is None:
        sched = ((3.0, 0.30), (2.0, 0.70), (1.5, 1.35))
    else:
        sched = ((1.5, 0.36),)
    best = None
    for (wv, lim) in sched:
        if time.perf_counter() - t0 > lim - 0.02:
            break
        (acts, states), full = P.search(lim, t0, wv)
        if full:
            q = 1.5 * states[-1][2] - 0.63 * len(acts)
            if best is None or not best[1] or q > best[2]:
                best = ((acts, states), True, q)
            if states[-1][2] >= h["hp"] and time.perf_counter() - t0 > 0.6:
                break
            continue
        if best is None or (not best[1] and acts and len(acts) > len(best[0][0])):
            best = ((acts, states), False, 0)
    (acts, states), full = (best[0], best[1]) if best is not None else (([], []), False)
    if not acts:
        memory["plan"] = None
        bestc = None
        for a in ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT"):
            c = P._step(P.root if P.root is not None else None, a) if P.root is not None else None
            if c is not None:
                P._load(c[0])
                hv = P.h(P.g, c[0][14]) + (0.5 if a == "WAIT" else 0)
                if bestc is None or hv < bestc[0]:
                    bestc = (hv, a)
        return bestc[1] if bestc else "WAIT"
    memory["plan"] = (acts, states)
    memory["plan_full"] = full
    memory["pi"] = 1
    nxt = states[0]
    memory["expect"] = (nxt[0], nxt[1], nxt[2], nxt[3], nxt[4], nxt[5])
    return acts[0]


def decide_action(state: dict, memory: dict) -> str:
    try:
        a = _choose(state, memory)
        if a in VALID_ACTIONS:
            return a
    except Exception:
        pass
    return "WAIT"


# ==============================================================================
# Demon
# ==============================================================================
def _design():
    g = [["T_W" if (x in (0, 39) or y in (0, 25)) else "EMPTY" for x in range(W_)] for y in range(H_)]
    # sealed vault: only through the plate gate
    g[13][37] = "V"
    g[12][37] = "T_W"
    g[14][37] = "T_W"
    g[13][36] = "P_GATE"
    # K1 pocket (open only from below)
    g[3][16] = "K1"
    g[3][15] = "T_W"
    g[3][17] = "T_W"
    g[2][16] = "T_W"
    # K2 pocket (pit above, open only from below)
    g[22][16] = "K2"
    g[22][15] = "T_W"
    g[22][17] = "T_W"
    # ice highway on row 13 ending in a pit
    for x in range(5, 32):
        g[13][x] = "ICE"
    g[13][32] = "PIT"
    # ice drop between the keys ending in a pit right above K2
    for y in range(5, 21):
        g[y][16] = "ICE"
    g[21][16] = "PIT"
    # two sokoban plates; the straight push lanes are cracked (box leaves -> pit -> hero falls)
    g[6][30] = "BOX"
    g[4][34] = "PLATE"
    g[20][30] = "BOX"
    g[22][34] = "PLATE"
    for x in (31, 32, 33):
        g[4][x] = "CRACK"
        g[22][x] = "CRACK"
    # dual-period laser curtains on the vault approach
    g[2][35] = "LASER_D"
    g[24][35] = "LASER2_U"
    g[13][38] = "LASER_L"
    return g


AUTHOR_SOLUTION_RL = [
    ("JUMP_R", 1),
    ("MOVE_U", 1),
    ("JUMP_R", 2),
    ("MOVE_R", 8),
    ("MOVE_U", 6),
    ("MOVE_R", 16),
    ("MOVE_D", 1),
    ("MOVE_R", 1),
    ("MOVE_U", 2),
    ("MOVE_L", 4),
    ("MOVE_D", 16),
    ("MOVE_L", 1),
    ("MOVE_D", 1),
    ("MOVE_R", 4),
    ("MOVE_D", 1),
    ("MOVE_R", 1),
    ("MOVE_U", 1),
    ("MOVE_L", 18),
    ("MOVE_U", 1),
    ("MOVE_D", 1),
    ("MOVE_L", 2),
    ("MOVE_U", 18),
    ("MOVE_R", 2),
    ("MOVE_U", 1),
    ("MOVE_D", 1),
    ("MOVE_R", 1),
    ("MOVE_D", 8),
    ("MOVE_R", 17),
    ("WAIT", 1),
    ("MOVE_R", 2),
    ("WAIT", 1),
    ("MOVE_D", 1),
    ("MOVE_R", 1),
]
AUTHOR_SOLUTION = [a for a, n in AUTHOR_SOLUTION_RL for _ in range(n)]


def build_dungeon() -> dict:
    g = _design()
    return {"taunt": "压板只认箱子，金库只认活人。", "grid": g, "author_solution": list(AUTHOR_SOLUTION)}
