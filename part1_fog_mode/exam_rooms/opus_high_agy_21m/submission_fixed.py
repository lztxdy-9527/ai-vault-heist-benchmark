"""
Submission: 阴间地牢·金库攻防战
"""
import heapq
import collections

W_, H_ = 40, 26
HIGH = {"W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R"}
DIRV = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
MIRROR_MAP = {
    "MIRROR_NE": {"L": "U", "R": "U", "U": "R", "D": "R"},
    "MIRROR_SE": {"L": "D", "R": "D", "U": "R", "D": "R"},
    "MIRROR_SW": {"L": "D", "R": "D", "U": "L", "D": "L"},
    "MIRROR_NW": {"L": "U", "R": "U", "U": "L", "D": "L"},
}
SPRINGS = {"SPRING_U": "U", "SPRING_D": "D", "SPRING_L": "L", "SPRING_R": "R"}
PAIRS = {"PORTAL_1A": "PORTAL_1B", "PORTAL_1B": "PORTAL_1A",
         "PORTAL_2A": "PORTAL_2B", "PORTAL_2B": "PORTAL_2A"}
LASERS = {"LASER_U": "U", "LASER_D": "D", "LASER_L": "L", "LASER_R": "R"}
KV = {"K1", "K2", "V"}
BOMB_IMMUNE = {"T_W", "K1", "K2", "V", "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B", "PIT"}
VALID_ACTIONS = ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT",
                 "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
                 "THROW_U", "THROW_D", "THROW_L", "THROW_R", "BOMB")


# ==============================================================================
# Physics engine (also used by the hero for look-ahead on its belief map)
# ==============================================================================
class Game:
    def init(self, T, O, hx, hy, hp=100, k1=False, k2=False, jumps=3, throws=3,
                 nb=2, gates=False, bombs=None, turn=1, clue_of=None, extra_beams=None):
        self.T = T
        self.O = O
        self.hx, self.hy = hx, hy
        self.hp = hp
        self.k1, self.k2 = k1, k2
        self.jumps, self.throws, self.nb = jumps, throws, nb
        self.gates = gates
        self.bombs = bombs if bombs is not None else []
        self.turn = turn
        self.clue_of = clue_of if clue_of is not None else {}
        self.trap = 0.0
        self.status = "ALIVE"
        self.next_id = 1000
        self.log = None  # undo log
        self.unknown = False
        self.extra_beams = extra_beams  # list of sets of cells (unattributed beams)
        self.portals = {}
        for y in range(H_):
            row = T[y]
            for x in range(W_):
                if row[x] in PAIRS:
                    self.portals[row[x]] = (x, y)
        return self

    # --- mutation helpers with undo log
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
        return False

    def clear_clue(self, x, y):
        self.clue_of.pop((x, y), None)

    def dmg_trap(self, d):
        self.trap += min(max(self.hp, 0), d)
        self.hp -= d

    def enterable(self, ent, x, y):
        if self.wall(x, y):
            return False
        o = self.O[y][x]
        if o == "BOX" or o == "TNT":
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
                elif t == "MIMIC" or t == "CHEST":
                    self.setT(x1, y1, "EMPTY")
                    self.clear_clue(x1, y1)
                elif t == "SWITCH":
                    self.gates = not self.gates
            else:
                if t == "PIT":
                    self.dmg_trap(100)
                elif t == "MIMIC":
                    self.dmg_trap(45)
                    self.setT(x1, y1, "EMPTY")
                    self.clear_clue(x1, y1)
                    stop = True
                elif t == "HEAL":
                    self.hp = min(100, self.hp + 30)
                    self.setT(x1, y1, "EMPTY")
                elif t == "SWITCH":
                    self.gates = not self.gates
                elif t == "UNKNOWN":
                    self.unknown = True
                    stop = True
                elif t == "CHEST":  # belief: unknown chest -> pessimistic
                    self.unknown = True
                    self.dmg_trap(45)
                    self.setT(x1, y1, "EMPTY")
                    stop = True
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
                if self.enterable(ent, nx, ny):
                    x0, y0, x1, y1 = x1, y1, nx, ny
                    continue
                return
            if t == "ICE" or t in MIRROR_MAP:
                if t != "ICE":
                    d = MIRROR_MAP[t][d]
                    dx, dy = DIRV[d]
                nx, ny = x1 + dx, y1 + dy
                if self.enterable(ent, nx, ny):
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
                    self.unknown = True
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
            if self.wall(x1, y1) or self.O[y1][x1] == "TNT":
                pass
            elif self.O[y1][x1] == "BOX":
                x2, y2 = hx + 2 * dx, hy + 2 * dy
                if (not self.wall(x2, y2)) and self.O[y2][x2] is None and self.T[y2][x2] not in KV:
                    self.chain("B", x1, y1, x2, y2, d)
                    if not self.wall(x1, y1) and self.O[y1][x1] is None:
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
                if not (self.wall(x1, y1) or self.wall(x2, y2) or self.O[y2][x2] is not None):
                    self.chain("H", hx, hy, x2, y2, d)
        elif a.startswith("THROW_"):
            if self.throws > 0:
                self.throws -= 1
                self.throw(a[6])

    def throw(self, d):
        sx, sy = self.hx, self.hy
        rng = 6
        sp = 0
        done = False
        while rng > 0:
            dx, dy = DIRV[d]
            sx += dx
            sy += dy
            rng -= 1
            if self.wall(sx, sy) or self.O[sy][sx] == "BOX":
                done = True
                break
            if self.O[sy][sx] == "TNT":
                self.tnt_armed.add((sx, sy))
                done = True
                break
            t = self.T[sy][sx]
            if t == "SWITCH":
                self.gates = not self.gates
                done = True
                break
            if t == "MIMIC":
                self.setT(sx, sy, "EMPTY")
                self.clear_clue(sx, sy)
                done = True
                break
            if t in MIRROR_MAP:
                d = MIRROR_MAP[t][d]
            elif t in PAIRS and sp < 2:
                pp = self.portals.get(PAIRS[t])
                if pp and self.O[pp[1]][pp[0]] is None:
                    sx, sy = pp
                    sp += 1
                    if sp == 2:
                        done = True
                        break
        if done:
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
                self.clear_clue(sx, sy)
                return
            if t in MIRROR_MAP:
                d = MIRROR_MAP[t][d]
                continue
            if t == "ICE":
                continue
            if t in PAIRS and sp < 2:
                pp = self.portals.get(PAIRS[t])
                if pp and self.O[pp[1]][pp[0]] is None:
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
        q = collections.deque()
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
        while q:
            s = q.popleft()
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
            if t in BOMB_IMMUNE or t == "UNKNOWN":
                continue
            if t == "CRACK":
                self.setT(cx, cy, "PIT")
            elif t == "EMPTY":
                continue
            else:
                if t == "MIMIC" or t == "CHEST":
                    self.clear_clue(cx, cy)
                self.setT(cx, cy, "EMPTY")
        for y in range(H_):
            for x in range(W_):
                if self.O[y][x] == "BOX" and self.T[y][x] == "PIT":
                    self.setO(x, y, None)
                    self.setT(x, y, "EMPTY")
        if self.hp > 0 and self.T[self.hy][self.hx] == "PIT":
            self.dmg_trap(100)
        if self.hp <= 0:
            self.status = "DEAD"

    def beams(self):
        res = []
        for y in range(H_):
            row = self.T[y]
            for x in range(W_):
                if row[x] in LASERS:
                    dx, dy = DIRV[LASERS[row[x]]]
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

    def phases(self, beam_cache=None):
        # phase C
        for b in self.bombs:
            b["timer"] -= 1
        ib = [b for b in self.bombs if b["timer"] <= 0]
        if ib or self.tnt_armed:
            self.explode(ib, list(self.tnt_armed))
            if self.status == "DEAD":
                return
        if self.turn % 3 == 0:
            bl = beam_cache if beam_cache is not None else self.beams()
            m = 0
            lt = []
            for cells, tnt in bl:
                if cells & self.exposed:
                    m += 1
                if tnt:
                    lt.append(tnt)
            if self.extra_beams:
                for cells in self.extra_beams:
                    if cells & self.exposed:
                        m += 1
            if m:
                self.dmg_trap(50 * m)
                if self.hp <= 0:
                    self.status = "DEAD"
                    return
            if lt:
                self.explode([], lt)

    def full_turn(self, a, beam_cache=None):
        self.act(a)
        if self.status == "ALIVE":
            self.phases(beam_cache)
        self.turn += 1
        return self.status


def bind_clues(grid):
    clue_of = {}
    used = set()
    chests = {"HEAL", "MIMIC"}
    for my in range(H_):
        for mx in range(W_):
            if grid[my][mx] != "MIMIC":
                continue
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = mx + dx, my + dy
                if not (0 <= nx < W_ and 0 <= ny < H_):
                    continue
                if grid[ny][nx] != "EMPTY":
                    continue
                if 1 <= nx <= 3 and 12 <= ny <= 14:
                    continue
                if (nx, ny) in used:
                    continue
                bad = False
                for ex, ey in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    qx, qy = nx + ex, ny + ey
                    if (qx, qy) == (mx, my):
                        continue
                    if 0 <= qx < W_ and 0 <= qy < H_ and grid[qy][qx] in chests:
                        bad = True
                if bad:
                    continue
                used.add((nx, ny))
                clue_of[(mx, my)] = (nx, ny)
                break
            else:
                return None
    return clue_of


def make_game(grid):
    T = [[("EMPTY" if c in ("BOX", "TNT") else c) for c in row] for row in grid]
    O = [[(c if c in ("BOX", "TNT") else None) for c in row] for row in grid]
    return Game().init(T, O, 2, 13, clue_of=bind_clues(grid) or {})


# ==============================================================================
# Demon
# ==============================================================================
MAP_ROWS = None  # filled in build


def _design():
    g = [["T_W" if (x in (0, 39) or y in (0, 25)) else "EMPTY" for x in range(W_)] for y in range(H_)]
    # Spawn kill-chamber: 12 vertical lasers cover columns 1..6, rows 5..22
    for x in range(1, 7):
        g[4][x] = "LASER_D"
        g[23][x] = "LASER_U"
    # chamber east wall, single exit at row 10 through an ice lane
    for y in range(5, 23):
        if y != 10:
            g[y][7] = "W"
    for x in range(3, 8):
        g[10][x] = "ICE"
    # landmarks far away
    g[2][33] = "K1"
    g[23][33] = "K2"
    g[13][36] = "V"
    return g


def build_dungeon() -> dict:
    g = _design()
    sol = list(AUTHOR_SOLUTION)
    return {"taunt": "第3回合，激光点名。能出门的再聊。", "grid": g, "author_solution": sol}


AUTHOR_SOLUTION = (["MOVE_U"] * 3 + ["MOVE_R"]
                   + ["MOVE_U"] * 8 + ["MOVE_R"] * 25
                   + ["MOVE_D"] * 21
                   + ["MOVE_U"] * 10 + ["MOVE_R"] * 3)


# ==============================================================================
# Hero
# ==============================================================================
PLAIN = {"EMPTY", "K1", "K2", "V", "UNKNOWN"}


def _update_memory(state, memory):
    if "T" not in memory:
        memory["T"] = [["UNKNOWN"] * W_ for _ in range(H_)]
        memory["O"] = [[None] * W_ for _ in range(H_)]
        memory["clue"] = set()
        memory["warn"] = {}
        memory["seen"] = [[False] * W_ for _ in range(H_)]
        memory["visits"] = collections.Counter()
        memory["last"] = []
    T = memory["T"]
    O = memory["O"]
    vm = state["visible_mask"]
    st = state["terrain"]
    so = state["occupant"]
    sc = state["clues"]
    seen = memory["seen"]
    for y in range(H_):
        vr = vm[y]
        for x in range(W_):
            if vr[x]:
                t = st[y][x]
                if t != "UNKNOWN":
                    T[y][x] = t
                    seen[y][x] = True
                O[y][x] = so[y][x]
                if sc[y][x]:
                    memory["clue"].add((x, y))
                else:
                    memory["clue"].discard((x, y))
    for w in state.get("laser_warnings", []) or []:
        memory["warn"][(w["x"], w["y"])] = w["dir"]
    h = state["hero"]
    memory["visits"][(h["x"], h["y"])] += 1


def _belief(state, memory):
    T = [row[:] for row in memory["T"]]
    O = [row[:] for row in memory["O"]]
    seen = memory["seen"]
    clue = memory["clue"]
    keys = state["hero"]["keys"]
    tg = state["targets"]
    for name, idx in (("K1", 0), ("K2", 1)):
        x, y = tg[name]
        if not keys[idx] and T[y][x] == "UNKNOWN":
            T[y][x] = name
    vx, vy = tg["V"]
    if T[vy][vx] == "UNKNOWN":
        T[vy][vx] = "V"
    for y in range(H_):
        for x in range(W_):
            if T[y][x] == "CHEST":
                mim = False
                allseen = True
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W_ and 0 <= ny < H_:
                        if (nx, ny) in clue:
                            mim = True
                        if not seen[ny][nx]:
                            allseen = False
                if mim:
                    T[y][x] = "MIMIC"
                elif allseen:
                    T[y][x] = "HEAL"
    return T, O


def _extra_beams(memory, T):
    # warned cells not explained by a known emitter -> group per (dir, line)
    groups = {}
    for (x, y), d in memory["warn"].items():
        dx, dy = DIRV[d]
        # walk back toward emitter
        explained = False
        for k in range(1, 11):
            px, py = x - k * dx, y - k * dy
            if not (0 <= px < W_ and 0 <= py < H_):
                break
            t = T[py][px]
            if t in LASERS and LASERS[t] == d:
                explained = True
                break
            if t in HIGH or t == "UNKNOWN":
                break
        if explained:
            continue
        key = (d, x if d in "UD" else y)
        groups.setdefault(key, set()).add((x, y))
    return list(groups.values())


class Planner:
    def init(self, state, memory, deadline):
        self.state = state
        self.memory = memory
        h = state["hero"]
        self.h = h
        T, O = _belief(state, memory)
        self.T, self.O = T, O
        self.extra = _extra_beams(memory, T)
        gates = state["gates_flipped"]
        bombs = [{"id": i, "x": b["x"], "y": b["y"], "timer": b["timer"]} for i, b in enumerate(state.get("bombs", []) or [])]
        self.g = Game().init(T, O, h["x"], h["y"], hp=h["hp"], k1=h["keys"][0], k2=h["keys"][1],
                      jumps=h["jumps"], throws=h["throws"], nb=h["bombs"], gates=gates,
                      bombs=bombs, turn=state["turn"], clue_of={}, extra_beams=self.extra)
        self.has_switch = any(T[y][x] == "SWITCH" for y in range(H_) for x in range(W_))
        self.deadline = deadline
        # static beam cells for cost
        self.beam_cells = set()
        for cells, _ in self.g.beams():
            self.beam_cells |= cells
        for cells in self.extra:
            self.beam_cells |= cells
        for p in memory["warn"]:
            self.beam_cells.add(p)
        return self

    def sim_edge(self, x, y, gates, a, jumps):
        g = self.g
        g.log = []
        g.hx, g.hy, g.hp, g.gates = x, y, 100, gates
        g.jumps = jumps
        g.status = "ALIVE"
        g.unknown = False
        g.trap = 0.0
        saved_b = g.bombs
        g.bombs = []
        g.act(a)
        res = (g.hx, g.hy, g.gates, g.status, 100 - g.hp, g.unknown, frozenset(g.exposed), len(g.log))
        crack_used = any(e[0] == 0 and e[3] == "CRACK" for e in g.log)
        g.undo()
        g.bombs = saved_b
        g.log = None
        return res, crack_used

    def build_graph(self):
        T, O = self.T, self.O
        g = self.g
        jumps = self.h["jumps"]
        nbombs = self.h["bombs"]
        layers = (False, True) if self.has_switch else (self.state["gates_flipped"],)
        edges = {}
        hp = self.h["hp"]
        active = [(b["x"], b["y"]) for b in (self.state.get("bombs") or [])]
        BOMBABLE = ("W", "LASER_U", "LASER_D", "LASER_L", "LASER_R", "R_GATE", "B_GATE")
        for gates in layers:
            g.gates = gates
            for y in range(1, H_ - 1):
                for x in range(1, W_ - 1):
                    if g.wall(x, y):
                        if T[y][x] in BOMBABLE and (nbombs > 0 or active):
                            el = []
                            for d, (dx, dy) in DIRV.items():
                                nx, ny = x + dx, y + dy
                                if not g.wall(nx, ny) and T[ny][nx] != "PIT" and O[ny][nx] is None:
                                    el.append(((nx, ny, gates), 1.0, None))
                            edges[(x, y, gates)] = el
                        continue
                    t = T[y][x]
                    if t == "PIT":
                        continue
                    node = (x, y, gates)
                    el = []
                    for d, (dx, dy) in DIRV.items():
                        nx, ny = x + dx, y + dy
                        nt = T[ny][nx]
                        if g.wall(nx, ny):
                            if nt in BOMBABLE and 0 < nx < W_ - 1 and 0 < ny < H_ - 1:
                                near = any(max(abs(bx - nx), abs(by - ny)) <= 1 for bx, by in active)
                                if near:
                                    el.append(((nx, ny, gates), 3.0, ("WAITBOMB", d)))
                                elif nbombs > 0:
                                    el.append(((nx, ny, gates), 12.0, ("BOMB", d)))
                            continue
                        if t not in PAIRS and O[ny][nx] is None and (nt in PLAIN or nt == "CRACK" and t != "CRACK"):
                            c = 1.0
                            if nt == "UNKNOWN":
                                c += 0.3
                            if t == "CRACK":
                                c += 1.5
                            if (nx, ny) in self.beam_cells or (x, y) in self.beam_cells:
                                c += 6
                            el.append(((nx, ny, gates), c, None))
                            continue
                        if O[ny][nx] == "TNT":
                            continue
                        res, cu = self.sim_edge(x, y, gates, "MOVE_" + d, jumps)
                        self._add(el, res, cu, hp, 0)
                    if jumps > 0 and t != "UNKNOWN":
                        for d, (dx, dy) in DIRV.items():
                            px, py = x + dx, y + dy
                            pt = T[py][px]
                            if (pt == "EMPTY" or pt == "UNKNOWN") and O[py][px] is None and (px, py) not in self.beam_cells:
                                continue
                            if g.wall(px, py):
                                continue
                            qx, qy = x + 2 * dx, y + 2 * dy
                            if g.wall(qx, qy) or O[qy][qx] is not None:
                                continue
                            res, cu = self.sim_edge(x, y, gates, "JUMP_" + d, jumps)
                            self._add(el, res, cu, hp, 4.0)
                    edges[node] = el
        self.edges = edges
        self.layers = layers
        h = self.h
        g.hx, g.hy, g.hp, g.jumps = h["x"], h["y"], h["hp"], h["jumps"]
        g.gates = self.state["gates_flipped"]
        g.status = "ALIVE"
        g.unknown = False
        g.trap = 0.0

    def _add(self, el, res, cu, hp, extra):
        fx, fy, fg, status, dmg, unk, exp, _ = res
        if status == "DEAD" or dmg >= hp:
            return
        c = 1.0 + extra + dmg * 0.6
        if unk:
            c += 3
        if cu:
            c += 1.5
        if exp & self.beam_cells:
            c += 6
        el.append(((fx, fy, fg), c, None))

    def field(self, goal_xy):
        rev = collections.defaultdict(list)
        for u, el in self.edges.items():
            for v, c, _ in el:
                rev[v].append((u, c))
        dist = {}
        pq = []
        goals = goal_xy if isinstance(goal_xy, list) else [goal_xy]
        for gx, gy in goals:
            for gt in self.layers:
                n = (gx, gy, gt)
                dist[n] = 0.0
                pq.append((0.0, n))
        heapq.heapify(pq)
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist.get(u, 1e18):
                continue
            for v, c in rev.get(u, ()):
                nd = d + c
                if nd < dist.get(v, 1e18):
                    dist[v] = nd
                    heapq.heappush(pq, (nd, v))
        return dist


def _fd(field, x, y, g):
    return field.get((x, y, g), 1e9)


def _choose(state, memory):
    import time as _t
    t0 = _t.time()
    _update_memory(state, memory)
    P = Planner().init(state, memory, t0 + 0.35)
    P.build_graph()
    h = state["hero"]
    keys = h["keys"]
    tg = state["targets"]
    K1 = tuple(tg["K1"])
    K2 = tuple(tg["K2"])
    V = tuple(tg["V"])
    gf = state["gates_flipped"]
    hx, hy = h["x"], h["y"]
    fV = None
    if keys[0] and keys[1]:
        goal = V
        F = P.field(V)
    elif keys[0] or keys[1]:
        goal = K2 if keys[0] else K1
        F = P.field(goal)
    else:
        f1 = P.field(K1)
        f2 = P.field(K2)
        fV = P.field(V)
        ca = _fd(f1, hx, hy, gf) + min(_fd(f2, K1[0], K1[1], g) for g in P.layers) + min(_fd(fV, K2[0], K2[1], g) for g in P.layers)
        cb = _fd(f2, hx, hy, gf) + min(_fd(f1, K2[0], K2[1], g) for g in P.layers) + min(_fd(fV, K1[0], K1[1], g) for g in P.layers)
        pref = memory.get("pref")
        if pref == "A" and ca <= cb * 1.25 + 3:
            ch = "A"
        elif pref == "B" and cb <= ca * 1.25 + 3:
            ch = "B"
        else:
            ch = "A" if ca <= cb else "B"
        memory["pref"] = ch
        goal = K1 if ch == "A" else K2
        F = f1 if ch == "A" else f2
    # unreachable goal: try stepping through portals whose pair is unknown
    if _fd(F, hx, hy, gf) >= 1e8:
        T = P.T
        known = {T[y][x] for y in range(H_) for x in range(W_) if T[y][x] in PAIRS}
        best_f, best_v = None, 1e18
        for y in range(H_):
            for x in range(W_):
                if T[y][x] in PAIRS and PAIRS[T[y][x]] not in known:
                    f = P.field((x, y))
                    v = _fd(f, hx, hy, gf)
                    if v < best_v:
                        best_v, best_f = v, f
        if best_f is not None and best_v < 1e8:
            F = best_f
        else:
            unk = [(x, y) for y in range(1, H_ - 1) for x in range(1, W_ - 1) if T[y][x] == "UNKNOWN"]
            if unk:
                f = P.field(unk)
                if _fd(f, hx, hy, gf) < 1e8:
                    F = f
    return _local(P, F, memory, state, goal, t0)


def _local(P, F, memory, state, goal, t0):
    import time as _t
    h = state["hero"]
    g = P.g
    base = dict(hx=g.hx, hy=g.hy, hp=g.hp, k1=g.k1, k2=g.k2, jumps=g.jumps, throws=g.throws,
                nb=g.nb, gates=g.gates, turn=g.turn)
    base_bombs = [dict(b) for b in g.bombs]
    beam_cache = g.beams()
    keys_before = (g.k1, g.k2)
    acts1 = ["MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT"]
    if h["jumps"] > 0:
        acts1 += ["JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R"]
    acts2 = ["MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT"]
    visits = memory["visits"]

    def restore(snap, bombs):
        g.hx = snap["hx"]; g.hy = snap["hy"]; g.hp = snap["hp"]
        g.k1 = snap["k1"]; g.k2 = snap["k2"]
        g.jumps = snap["jumps"]; g.throws = snap["throws"]; g.nb = snap["nb"]
        g.gates = snap["gates"]; g.turn = snap["turn"]
        g.bombs = [dict(b) for b in bombs]
        g.status = "ALIVE"
        g.unknown = False
        g.trap = 0.0

    def snapshot():
        return dict(hx=g.hx, hy=g.hy, hp=g.hp, k1=g.k1, k2=g.k2, jumps=g.jumps, throws=g.throws,
                    nb=g.nb, gates=g.gates, turn=g.turn), [dict(b) for b in g.bombs]

    def score_state():
        if g.status == "WIN":
            return -1000.0
        if g.status == "DEAD":
            return 1e7
        val = 0.0
        got_new = (g.k1 and not keys_before[0]) or (g.k2 and not keys_before[1])
        if got_new:
            val -= 500
        else:
            val += _fd(F, g.hx, g.hy, g.gates)
        val += (base["hp"] - g.hp) * 0.6
        val += (base["jumps"] - g.jumps) * 4.0
        if g.unknown:
            val += 25
        val += 0.15 * min(visits.get((g.hx, g.hy), 0), 12)
        return val

    best = None
    best_a = "WAIT"
    g.log = []
    for a1 in acts1:
        restore(base, base_bombs)
        st = g.full_turn(a1, beam_cache)
        v1 = score_state()
        unk1 = g.unknown
        if st != "ALIVE" or (g.k1, g.k2) != keys_before:
            score = v1 + 1
        else:
            s1, b1 = snapshot()
            hp1 = g.hp
            score2 = 1e18
            for a2 in acts2:
                mark = len(g.log)
                restore(s1, b1)
                g.full_turn(a2, beam_cache)
                v2 = score_state()
                if unk1:
                    v2 += 25
                v2 += (hp1 - g.hp) * 0.0
                if v2 < score2:
                    score2 = v2
                # undo second step mutations
                while len(g.log) > mark:
                    k, x, y, v = g.log.pop()
                    if k == 0:
                        g.T[y][x] = v
                    else:
                        g.O[y][x] = v
            score = score2 + 2 + 0.1 * v1
            # also consider being better after first step
        # loop / revisit penalty
        restore(base, base_bombs)
        g.undo() if False else None
        # tie-breaks
        if a1 == "WAIT":
            score += 0.05
        if score < (best if best is not None else 1e18):
            best = score
            best_a = a1
        # undo all mutations from this branch
        g.undo()
        g.log = []
        if _t.time() - t0 > 0.42:
            break
    g.log = None
    restore(base, base_bombs)
    # bomb macro if stuck and plan suggests bomb edge
    cur = _fd(F, base["hx"], base["hy"], base["gates"])
    if cur >= 1e8 or best is None or best >= 1e6:
        return _fallback(P, state, memory, goal)
    bomb_a = _maybe_bomb(P, F, state, memory)
    if bomb_a:
        return bomb_a
    return best_a


def _maybe_bomb(P, F, state, memory):
    h = state["hero"]
    if h["bombs"] <= 0 or state.get("bombs"):
        return None
    x, y = h["x"], h["y"]
    gf = state["gates_flipped"]
    cur = _fd(F, x, y, gf)
    for (v, c, tag) in P.edges.get((x, y, gf), ()):
        if tag and tag[0] == "BOMB":
            if abs(_fd(F, v[0], v[1], v[2]) + c - cur) < 1e-6:
                # is bomb edge at least as good as any move edge?
                best_move = min((_fd(F, vv[0], vv[1], vv[2]) + cc for vv, cc, tt in P.edges[(x, y, gf)] if not tt), default=1e18)
                if best_move < cur - 1e-6:
                    return None
                # escape exists: a cell at chebyshev>=2 within 2 plain moves
                if _escape_exists(P, x, y):
                    return "BOMB"
    return None


def _escape_exists(P, x, y):
    g = P.g
    q = collections.deque([(x, y, 0)])
    seen = {(x, y)}
    while q:
        cx, cy, d = q.popleft()
        if max(abs(cx - x), abs(cy - y)) >= 2:
            return True
        if d == 2:
            continue
        for dx, dy in DIRV.values():
            nx, ny = cx + dx, cy + dy
            if (nx, ny) in seen or g.wall(nx, ny) or P.O[ny][nx] is not None:
                continue
            if P.T[ny][nx] not in ("EMPTY", "K1", "K2", "V") and not (P.T[ny][nx] == "R_GATE" or P.T[ny][nx] == "B_GATE"):
                continue
            seen.add((nx, ny))
            q.append((nx, ny, d + 1))
    return False


def _fallback(P, state, memory, goal):
    # safest action that reduces manhattan distance to goal / explores
    h = state["hero"]
    g = P.g
    best, ba = 1e18, "WAIT"
    for a in ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT"):
        g.log = []
        sv = (g.hx, g.hy, g.hp, g.gates, g.turn, g.k1, g.k2, g.jumps, g.throws, g.nb)
        bb = [dict(b) for b in g.bombs]
        g.status = "ALIVE"
        g.unknown = False
        g.full_turn(a)
        if g.status == "DEAD":
            sc = 1e9
        else:
            sc = abs(g.hx - goal[0]) + abs(g.hy - goal[1]) + (sv[2] - g.hp) + memory["visits"][(g.hx, g.hy)] * 2 + (20 if g.unknown else 0)
        g.undo()
        g.log = None
        (g.hx, g.hy, g.hp, g.gates, g.turn, g.k1, g.k2, g.jumps, g.throws, g.nb) = sv
        g.bombs = bb
        if sc < best:
            best, ba = sc, a
    return ba


def decide_action(state: dict, memory: dict) -> str:
    try:
        a = _choose(state, memory)
        if a in VALID_ACTIONS:
            return a
    except Exception:
        pass
    return "WAIT"
