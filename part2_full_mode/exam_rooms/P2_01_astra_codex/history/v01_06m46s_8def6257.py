"""FULL-information vault solver and dungeon, version 2.2."""
from collections import deque, namedtuple
from heapq import heappush, heappop
from time import monotonic

D = (-40, 40, -1, 1)
LETTERS = "UDLR"
ACTIONS = tuple(prefix + d for prefix in ("MOVE_", "JUMP_", "THROW_") for d in LETTERS) + ("WAIT", "BOMB")
WAIT, BOMB = 12, 13
INNER = tuple(40 * y + x for y in range(1, 25) for x in range(1, 39))
AREA = (-41, -40, -39, -1, 0, 1, 39, 40, 41)
NAMES = ("EMPTY W T_W PIT ICE CRACK SWITCH R_GATE B_GATE K1 K2 V HEAL MIMIC "
         "MIRROR_NE MIRROR_SE MIRROR_SW MIRROR_NW SPRING_U SPRING_D SPRING_L SPRING_R "
         "PORTAL_1A PORTAL_1B PORTAL_2A PORTAL_2B LASER_U LASER_D LASER_L LASER_R "
         "LASER2_U LASER2_D LASER2_L LASER2_R PLATE P_GATE ONEWAY_U ONEWAY_D ONEWAY_L ONEWAY_R").split()
ID = {s: i for i, s in enumerate(NAMES)}
(FLOOR, W, TW, PIT, ICE, CRACK, SWITCH, RED, BLUE, K1, K2, V, HEAL, MIMIC,
 NE, SE, SW, NW, SU, SD, SL, SR, PA, PB, PC, PD, LU, LD, LL, LR, BU, BD, BL, BR,
 PLATE, PG, OU, OD, OL, OR) = range(len(NAMES))
MASK, BOX, TNT = 63, 64, 128
OBJECT = {None: 0, "BOX": BOX, "TNT": TNT}
MIRROR = ((3,3,0,0), (3,3,1,1), (2,2,1,1), (2,2,0,0))
IMMUNE = {TW, PIT, K1, K2, V, PA, PB, PC, PD, PLATE, PG, OU, OD, OL, OR}
WALLS = tuple(tuple(tuple(t in (W,TW,BLUE if flip else RED) or LU <= t <= BR or (t == PG and not active)
                          for t in range(len(NAMES))) for active in (0,1)) for flip in (0,1))
State = namedtuple("State", "p hp keys flip jumps stones bombs edits fuses")
Outcome = namedtuple("Outcome", "state won")


def dist(a, b):
    return abs(a % 40 - b % 40) + abs(a // 40 - b // 40)


def pos(pair):
    return pair[0] + 40 * pair[1]


def wrong(t, d):
    return OU <= t <= OR and t != OU + d


def encode(obs):
    board = []
    chests = []
    for y, row in enumerate(obs["terrain"]):
        occ = obs["occupant"][y]
        for x, tile in enumerate(row):
            if tile == "CHEST":
                chests.append(40*y+x)
                tile = "HEAL"
            board.append(ID[tile] + OBJECT[occ[x]])
    for p in chests:
        if any(obs["clues"][(p+d)//40][(p+d)%40] for d in D):
            board[p] += MIMIC - HEAL
    h = obs["hero"]
    root = State(40*h["y"]+h["x"], h["hp"], int(h["keys"][0])+2*int(h["keys"][1]),
                 int(obs["gates_flipped"]), h["jumps"], h["throws"], h["bombs"], (),
                 tuple(sorted((40*b["y"]+b["x"], b["timer"]) for b in obs["bombs"])))
    return board, root


class Arena:
    def prepare(self, board, targets):
        self.base = board
        self.targets = targets
        self.plates = [p for p in INNER if board[p] & MASK == PLATE]
        self.guns = [(p, (board[p]-LU) % 4, 3 if board[p] < BU else 4)
                     for p in INNER if LU <= board[p] <= BR]
        self.ports = [-1]*4
        for p in INNER:
            t = board[p] & MASK
            if PA <= t <= PD:
                self.ports[t-PA] = p
        self.beam_cache = {}
        self.period = 12 if self.guns else 1
        if self.guns and all(g[2] == self.guns[0][2] for g in self.guns):
            self.period = self.guns[0][2]
        return self

    def rays(self, edits, flip, active, turn):
        red, blue = turn % 3 == 0, turn % 4 == 0
        if not self.guns or not (red or blue):
            return {}, ()
        key = (edits,flip,active,red,blue)
        data = self.beam_cache.get(key)
        if data is not None:
            return data
        get = dict(edits).get
        wall = WALLS[flip][active]
        rays, barrels = {}, set()
        for i,(gun,d,period) in enumerate(self.guns):
            if turn % period or get(gun,self.base[gun]) != self.base[gun]:
                continue
            p = gun
            for _ in range(10):
                p += D[d]
                c = get(p,self.base[p])
                if wall[c & MASK] or BOX <= c < TNT:
                    break
                if c >= TNT:
                    barrels.add(p)
                    break
                rays[p] = rays.get(p,0) | (1 << i)
        data = rays, tuple(barrels)
        if len(self.beam_cache) > 2500:
            self.beam_cache.clear()
        self.beam_cache[key] = data
        return data


class Turn:
    def start(self, arena, state):
        self.arena = arena
        self.base = arena.base
        self.cells = dict(state.edits)
        self.p, self.hp, self.keys, self.flip = state[:4]
        self.jumps, self.stones, self.bombs = state[4:7]
        self.fuses = state.fuses
        self.path = [self.p]
        self.armed = set()
        self.won = False
        self.active = self.plates_down()
        return self

    def at(self, p):
        return self.cells.get(p,self.base[p])

    def put(self, p, c):
        if c == self.base[p]:
            self.cells.pop(p,None)
        else:
            self.cells[p] = c

    def plates_down(self):
        return bool(self.arena.plates) and all(BOX <= self.at(p) < TNT for p in self.arena.plates)

    def blocked(self, p, d, box=False):
        c = self.at(p)
        t = c & MASK
        return (c >= BOX or WALLS[self.flip][self.active][t] or wrong(t,d)
                or (box and (p == self.p or t in (K1,K2,V))))

    def advance(self, src, dest, d, box=False):
        portals = 0
        paired = False
        for n in range(1,33):
            old = self.at(src) & MASK
            t = self.at(dest) & MASK
            if box or old == CRACK:
                self.put(src,PIT if old == CRACK else old)
            if box:
                self.put(dest, BOX + t)
                if old == PLATE or t == PLATE:
                    self.active = self.plates_down()
                if t == PIT:
                    self.put(dest,FLOOR)
                    return
                if t == MIMIC:
                    self.put(dest,BOX+FLOOR)
            else:
                self.p = dest
                self.path.append(dest)
                if t == PIT:
                    self.hp -= 100
                    return
                if t == MIMIC:
                    self.hp -= 45
                    self.put(dest,FLOOR)
                    return
                if t == HEAL:
                    self.hp = min(100,self.hp+30)
                    self.put(dest,FLOOR)
                elif t in (K1,K2):
                    self.keys |= 1 if t == K1 else 2
                    self.put(dest,FLOOR)
                elif t == V and self.keys == 3:
                    self.won = True
                    return
            if t == SWITCH:
                self.flip ^= 1
            if n == 32:
                return
            src = dest
            if paired:
                paired = False
                if portals >= 2:
                    return
            elif PA <= t <= PD:
                other = self.arena.ports[(t-PA)^1]
                if other < 0 or self.at(other) >= BOX or (box and other == self.p):
                    return
                portals += 1
                dest = other
                paired = True
                continue
            elif SU <= t <= SR:
                d = t-SU
                for _ in range(3):
                    ahead = dest + D[d]
                    if self.blocked(ahead,d,box):
                        if box and self.at(ahead) >= TNT:
                            self.armed.add(ahead)
                        break
                    dest = ahead
                if dest == src:
                    return
                continue
            elif NE <= t <= NW:
                d = MIRROR[t-NE][d]
            elif t != ICE:
                return
            dest = src + D[d]
            if self.blocked(dest,d,box):
                return

    def stone(self, d):
        p, portals = self.p, 0
        for n in range(1,39):
            p += D[d]
            c = self.at(p)
            t = c & MASK
            if WALLS[self.flip][self.active][t] or BOX <= c < TNT:
                return False
            if c >= TNT:
                self.armed.add(p)
                return True
            if t == SWITCH:
                self.flip ^= 1
                return True
            if t == MIMIC:
                self.put(p,FLOOR)
                return True
            if NE <= t <= NW:
                d = MIRROR[t-NE][d]
            if PA <= t <= PD and portals < 2:
                other = self.arena.ports[(t-PA)^1]
                if other >= 0 and self.at(other) < BOX:
                    p = other
                    portals += 1
                    if portals == 2:
                        return False
            if n >= 6 and t != ICE and not NE <= t <= NW:
                if n == 6 or not PA <= t <= PD:
                    return False
        return False

    def blast(self, barrels, due):
        sources = [(p,TNT) for p in set(barrels) if self.at(p) >= TNT] + [(p,BOMB) for p in due]
        used = set(sources)
        hit = set()
        bombs = dict(self.fuses)
        for center,kind in sources:
            for offset in AREA:
                p = center + offset
                if p == self.p:
                    self.hp -= 60 if kind == TNT else 50
                if p in hit:
                    continue
                hit.add(p)
                if p in bombs and (p,BOMB) not in used:
                    used.add((p,BOMB))
                    sources.append((p,BOMB))
                if self.at(p) >= TNT and (p,TNT) not in used:
                    used.add((p,TNT))
                    sources.append((p,TNT))
        for p in hit:
            t = self.at(p) & MASK
            self.put(p,t if t in IMMUNE else PIT if t == CRACK else FLOOR)
        self.fuses = tuple((p,t) for p,t in self.fuses if p not in hit)
        self.active = self.plates_down()
        if self.hp > 0 and self.at(self.p) & MASK == PIT:
            self.hp -= 100

    def play(self, act, turn, prune=True):
        p = self.p
        if act < 8:
            d = act % 4
            q = p + D[d]
            c = self.at(q)
            t = c & MASK
            can = not WALLS[self.flip][self.active][t] and not wrong(t,d)
            if act >= 4:
                can = can and self.jumps > 0 and not self.blocked(q+D[d],d)
                self.jumps = max(0,self.jumps-1)
                q += D[d]
            elif c >= TNT:
                can = False
            elif can and c >= BOX:
                can = not self.blocked(q+D[d],d,True)
                if can:
                    self.advance(q,q+D[d],d,True)
                    if self.blocked(q,d):
                        q = p
            if can and q != p:
                self.advance(p,q,d)
            if not can and prune:
                return None
        elif act < WAIT:
            fired = self.stones > 0
            self.stones = max(0,self.stones-1)
            if not (fired and self.stone(act-8)) and prune:
                return None
        elif act == BOMB:
            if self.bombs and not any(q == p for q,_ in self.fuses):
                if prune and not any(self.at(p+z) >= BOX or self.at(p+z) & MASK not in IMMUNE | {FLOOR}
                                     for z in AREA):
                    return None
                self.fuses = tuple(sorted(self.fuses+((p,3),)))
                self.bombs -= 1
            elif prune:
                return None
        if self.hp > 0 and not self.won:
            if self.fuses:
                self.fuses = tuple((q,t-1) for q,t in self.fuses)
            if self.armed or any(t==0 for _,t in self.fuses):
                self.blast(self.armed,[q for q,t in self.fuses if t==0])
            if self.hp > 0 and self.arena.guns and (turn%3==0 or turn%4==0):
                rays, lit = self.arena.rays(tuple(sorted(self.cells.items())),self.flip,self.active,turn)
                hit = 0
                for q in self.path:
                    hit |= rays.get(q,0)
                self.hp -= 50 * hit.bit_count()
                if self.hp > 0 and lit:
                    self.blast(lit,())
        s = State(self.p,self.hp,self.keys,self.flip,self.jumps,self.stones,self.bombs,
                  tuple(sorted(self.cells.items())),self.fuses)
        return Outcome(s,self.won)


def step(w,s,a,t,prune=True):
    return Turn().start(w,s).play(a,t,prune)

def dungeon_grid():
    g = [["T_W" if x in (0,39) or y in (0,25) else "EMPTY" for x in range(40)] for y in range(26)]
    for y in range(1,25):
        g[y][12] = "T_W"
    g[13][12] = "P_GATE"
    for x in range(6,11):
        g[5][x] = g[7][x] = "T_W"
    g[7][9] = "ONEWAY_D"
    g[6][6:12] = ["PIT","PIT","ONEWAY_R","PLATE","PLATE","LASER_L"]
    for y in (3,5,8,10):
        g[y][4] = "BOX"
    for y in (17,22):
        for x,yy in ((8,y-1),(8,y+1),(9,y)):
            g[yy][x] = "T_W"
        g[y][4] = "BOX"
        g[y][8] = "PLATE"
    g[17][5:8] = ["ICE","ICE","ONEWAY_R"]
    g[22][5] = "SPRING_R"
    for x in range(13,16):
        g[12][x] = g[14][x] = "T_W"
    g[13][22], g[8][16] = "LASER_L","LASER2_D"
    g[4][26], g[20][26], g[13][35] = "K1","K2","V"
    for x,y in ((26,19),(25,20),(27,20),(35,12),(35,14),(36,13)):
        g[y][x] = "T_W"
    g[21][26], g[21][27] = "W","TNT"
    g[13][34] = "ONEWAY_R"
    return g


def build_dungeon():
    return {"grid": dungeon_grid(), "taunt":"六只箱子，四块压板。少的两只该停在哪儿？",
            "author_solution": [ACTIONS["udlrUDLRhjkn.z".index(a)] for a in CERTIFICATE]}

CERTIFICATE = ''

