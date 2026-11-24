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
    g[6][5],g[22][6],g[9][5] = "R_GATE","B_GATE","SWITCH"
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



INF = 10000.
MOTION = {ICE,NE,SE,SW,NW,SU,SD,SL,SR,PA,PB,PC,PD}


def static_land(w, board, q, d, flip, active, box=False, ignore_boxes=False):
    wall = WALLS[flip][active]
    portals, paired = 0, False
    def barrier(p,d):
        c = board[p]
        t = c & MASK
        return (wall[t] or wrong(t,d) or c >= TNT or (c >= BOX and not ignore_boxes)
                or (box and t in (K1,K2,V)))
    for _ in range(31):
        t = board[q] & MASK
        if paired:
            paired = False
            if portals == 2:
                break
        elif PA <= t <= PD:
            pair = w.ports[(t-PA)^1]
            if pair < 0 or (board[pair]>=BOX and not ignore_boxes):
                break
            q = pair
            paired = True
            portals += 1
            continue
        elif SU <= t <= SR:
            d = t-SU
            last = q
            for _ in range(3):
                if barrier(q+D[d],d):
                    break
                q += D[d]
            if q == last:
                break
            continue
        elif NE <= t <= NW:
            d = MIRROR[t-NE][d]
        elif t != ICE:
            break
        if barrier(q+D[d],d):
            break
        q += D[d]
    return q


def reverse_dist(rev,seeds):
    values = [INF]*len(rev)
    heap = []
    for q,c in seeds:
        if values[q] > c:
            values[q] = c
            heappush(heap,(c,q))
    while heap:
        c,q = heappop(heap)
        if c != values[q]:
            continue
        for p,price in rev[q]:
            val = c+price
            if val < values[p]:
                values[p] = val
                heappush(heap,(val,p))
    return values



def limited_field(rev,seeds,jmax):
    """A reverse edge that jumps consumes one charge in the forward direction."""
    n=len(rev)
    values=[INF]*(n*(jmax+1))
    heap=[]
    for p,c in seeds:
        if c<values[p]:
            values[p]=c
            heappush(heap,(c,p))
    while heap:
        cost,idx=heappop(heap)
        if cost!=values[idx]:
            continue
        lev,p=divmod(idx,n)
        base=idx-p
        for src,length,jump in rev[p]:
            if lev+jump>jmax:
                continue
            prev=base+src+jump*n
            nc=cost+length
            if nc<values[prev]:
                values[prev]=nc
                heappush(heap,(nc,prev))
    return values


class Guide:
    def prepare(self,w,root,opened,extra=None):
        board = w.base
        switches = [p for p in INNER if board[p]&MASK == SWITCH]
        self.dual = bool(switches and (RED in board or BLUE in board))
        flips = (0,1) if self.dual else (root.flip,)
        rev = [[] for _ in range(1040*len(flips))]
        boxes = [p for p in INNER if BOX <= board[p] < TNT]
        for flip in flips:
            layer = 1040*flip if self.dual else 0
            wall = WALLS[flip][opened]
            for q in INNER:
                c = board[q]
                t = c & MASK
                if t == TW or (t == PG and not opened):
                    continue
                cost = 1.
                if t == PIT:
                    # Only a spare box can turn a pit into a walkable landing.
                    if len(boxes) <= len(w.plates) or not any(dist(q,b)<=12 for b in boxes):
                        continue
                    cost += 13.
                elif wall[t]:
                    if not root.bombs and not root.fuses and not any(board[q+k]>=TNT for k in AREA):
                        continue
                    cost += 8.
                elif c >= TNT:
                    if not root.stones and not root.bombs:
                        continue
                    cost += 4.
                elif c >= BOX:
                    cost += 1.75
                elif t == MIMIC:
                    cost += 2.3 if root.stones else 13.
                elif t == CRACK:
                    cost += 0.5
                for d,step_ in enumerate(D):
                    p = q-step_
                    mid = board[p] & MASK
                    if mid == TW or wrong(t,d):
                        continue
                    dest = static_land(w,board,q,d,flip,opened) if t in MOTION else q
                    end = board[dest] & MASK
                    if end == PIT and t != PIT:
                        continue
                    level = 1040-layer if self.dual and end == SWITCH else layer
                    back = rev[level+dest]
                    back.append((p+layer,cost,0))
                    if root.jumps and not wall[mid] and not wrong(mid,d):
                        far = p-step_
                        if board[far] & MASK != TW:
                            back.append((far+layer,cost+1.25,1))
            if self.dual and root.stones:
                # Enumerate real stone impacts, including approaches around a
                # corner via a mirror or through the paired end of a portal.
                shooter=Turn().start(w,root)
                for p in INNER:
                    if wall[board[p]&MASK] or board[p]>=BOX or board[p]&MASK==PIT:
                        continue
                    shooter.p=p
                    for d in range(4):
                        shooter.flip=flip
                        shooter.cells.clear()
                        shooter.armed.clear()
                        shooter.stone(d)
                        if shooter.flip!=flip:
                            rev[p+1040-layer].append((p+layer,2.0,0))
                            break
        self.targets=w.targets
        self.size=len(rev)
        self.jmax=root.jumps
        self.extra=None
        n=self.size
        def seeds_at(q,after=None):
            keys=(q+i*1040+j*n for i in range(len(flips)) for j in range(root.jumps+1))
            return [(i,after[i] if after is not None else 0.) for i in keys]
        if extra is not None:
            self.extra=limited_field(rev,seeds_at(extra),root.jumps)
            return self
        a,b,v=w.targets
        last=limited_field(rev,seeds_at(v),root.jumps)
        one=limited_field(rev,seeds_at(b,last),root.jumps)
        two=limited_field(rev,seeds_at(a,last),root.jumps)
        first=limited_field(rev,seeds_at(a,one)+seeds_at(b,two),root.jumps)
        self.stages=(first,one,two,last)
        self.partial=None
        if self.value(root)>=INF:
            # The static relaxation may miss a future terrain alteration.
            # Aim at an attainable key while still retaining its full-world state.
            goals=[q for i,q in enumerate((a,b)) if not root.keys & (1<<i)] or [v]
            self.partial=limited_field(rev,[seed for q in goals for seed in seeds_at(q)],root.jumps)
        return self

    def value(self,s):
        p=s.p+(1040*s.flip if self.dual else 0)+min(self.jmax,s.jumps)*self.size
        if self.extra is not None:
            return self.extra[p]
        h=self.stages[s.keys][p]
        if h>=INF and self.partial is not None:
            nearest=min((dist(s.p,self.targets[i]) for i in range(2) if not s.keys&(1<<i)),
                        default=dist(s.p,self.targets[2]))
            return INF+min(self.partial[p],350+nearest)+.1*nearest
        return h


def material(w,s):
    board = w.base[:]
    for p,c in s.edits:
        board[p] = c
    return board


def sign(s,board_hash,t):
    return (s.p,s.hp,s.keys,s.flip,s.jumps,s.stones,s.bombs,s.fuses,board_hash,t%12)


def action_options(w,s,t,model):
    wall = WALLS[s.flip][model.active]
    rays = None
    for d,off in enumerate(D):
        q = s.p+off
        c = model.at(q)
        tile = c&MASK
        if wall[tile] or wrong(tile,d):
            continue
        if c<TNT:
            yield d
        if not s.jumps:
            continue
        if c>=BOX or tile in MOTION or tile in (PIT,CRACK,SWITCH,MIMIC) or s.fuses:
            yield d+4
        elif s.keys==3 and dist(s.p,w.targets[2])<=2*s.jumps+1:
            yield d+4
        elif w.guns:
            if rays is None:
                rays = w.rays(s.edits,s.flip,model.active,12)[0]
            if s.p in rays or q in rays or q+off in rays:
                yield d+4
    if s.stones:
        yield from (8,9,10,11)
    if w.guns or s.fuses:
        yield WAIT
    if s.bombs and any(model.at(s.p+o)>=BOX or model.at(s.p+o)&MASK not in IMMUNE and
                       model.at(s.p+o)&MASK not in (FLOOR,HEAL) for o in AREA):
        yield BOMB


def reconstruct(nodes,i):
    path = []
    while i:
        parent,a = nodes[i]
        path.append(a)
        i = parent
    path.reverse()
    return path


def search(w,root,turn,guide,deadline,visits,goal=None,weight=1.65):
    origin = guide.value(root)
    heap=[(weight*origin,0.,0,root,0)]
    nodes=[(-1,-1)]
    seen={(root,turn%w.period):0.}
    best_rank = (0, -1e9)
    best_id, expanded = 0,0
    while heap:
        _,g,idx,s,depth=heappop(heap)
        if (goal is None and s.keys==3 and s.p==w.targets[2] and idx) or (goal is not None and s.p==goal):
            return reconstruct(nodes,idx),True
        tick=turn+depth
        if tick>240 or g>seen.get((s,tick%w.period),1e8)+0.00001:
            continue
        if expanded%12==0 and monotonic()>=deadline:
            break
        expanded+=1
        model=Turn().start(w,s)
        for a in action_options(w,s,tick,model):
            obj=Turn().start(w,s)
            res=obj.play(a,tick)
            if res is None or res.state.hp<=0:
                continue
            n=res.state
            cost=1.
            if 4<=a<8:
                cost += (0.05 if s.keys==3 and dist(s.p,w.targets[2])<=2*s.jumps+1 else 2.15)
            elif 8<=a<12:
                cost += 0.6
            elif a==BOMB:
                cost += 3.2
            if model.active and not obj.active:
                cost+=16.
            if s.hp>n.hp:
                cost+=(s.hp-n.hp)*0.12
            if s.p!=n.p and visits:
                cost+=0.17*min(10,visits.get(n.p,0))
            elif depth==0 and a==WAIT and visits.get(n.p,0)>2:
                cost+=1.
            ng=g+cost
            tag=(n,(tick+1)%w.period)
            if ng>=seen.get(tag,1e8)-0.00001:
                continue
            seen[tag]=ng
            h=guide.value(n)
            healthcost=0.72*(root.hp-n.hp)
            priority=ng+healthcost+weight*h
            ni=len(nodes)
            nodes.append((idx,a))
            if res.won:
                return reconstruct(nodes,ni),True
            heappush(heap,(priority,ng,ni,n,depth+1))
            # Keep a verified, useful prefix if the time-slice ends mid-search.
            milestone = (n.keys.bit_count()-root.keys.bit_count()) if goal is None else 0
            progress=(milestone,origin-h-.18*ng-.50*max(0,root.hp-n.hp))
            if progress>best_rank:
                best_rank,best_id=progress,ni
    return reconstruct(nodes,best_id),False

class Crates:
    """Search pushes as macro actions. Flood-fill supplies the intervening walks."""
    def prepare(self,w,s,goals,sacrifice=False):
        self.w=w
        self.root=s
        self.goals=tuple(goals)
        self.sacrifice=sacrifice
        self.initial_boxes=tuple(p for p in INNER if BOX<=w.base[p]<TNT)
        self.initial_pits=frozenset(p for p in INNER if w.base[p]&MASK==PIT)
        self.field_cache={}
        self.match_cache={}
        self.walk_cache={}
        self.switches=[p for p in INNER if w.base[p]&MASK==SWITCH] if RED in w.base or BLUE in w.base else []
        return self

    def box_set(self,s):
        get=dict(s.edits).get
        candidates=set(self.initial_boxes)
        candidates.update(p for p,c in s.edits if BOX<=c<TNT)
        return tuple(sorted(p for p in candidates if BOX<=get(p,self.w.base[p])<TNT))

    def distances(self,s,filled):
        signature=(filled,s.flip)
        if signature in self.field_cache:
            return self.field_cache[signature]
        board=[c&MASK if BOX<=c<TNT else c for c in self.w.base]
        for p in filled:
            board[p]=FLOOR
        if self.switches:
            board=[FLOOR if c in (RED,BLUE) else c for c in board]
        wall=WALLS[s.flip][False]
        rev=[[] for _ in range(1040)]
        for p in INNER:
            t=board[p]&MASK
            if wall[t] or t in (K1,K2,V) or board[p]>=TNT:
                continue
            for d,off in enumerate(D):
                behind=p-off
                q=p+off
                c=board[q];land=c&MASK
                if (wall[board[behind]&MASK] or wall[land] or wrong(t,d) or wrong(land,d)
                        or c>=TNT or land in (K1,K2,V)):
                    continue
                dest=static_land(self.w,board,q,d,s.flip,False,box=True) if land in MOTION else q
                if dest==p:
                    continue
                penalty=1.
                if board[dest]&MASK==PIT:
                    penalty+=8.
                if board[behind]&MASK==PIT:
                    penalty+=5.
                rev[dest].append((p,penalty))
        fields=tuple(reverse_dist(rev,[(g,0.)]) for g in self.goals)
        if len(self.field_cache)<24:
            self.field_cache[signature]=fields
        return fields

    def estimate(self,s,boxes,filled):
        if self.sacrifice and self.goals[0] in filled:
            return 0.
        signature=(boxes,filled,s.flip)
        if signature in self.match_cache:
            return self.match_cache[signature]
        if len(boxes)<len(self.goals):
            return INF
        fields=self.distances(s,filled)
        assignments={0:0.}
        for field in fields:
            other={}
            for used,v in assignments.items():
                for i,b in enumerate(boxes):
                    mask=1<<i
                    if used&mask:
                        continue
                    cost=v+field[b]
                    tag=used|mask
                    if cost<other.get(tag,INF):
                        other[tag]=cost
            assignments=other
        val=min(assignments.values(),default=INF)
        if not self.sacrifice:
            val+=2.0*sum(g not in boxes for g in self.goals)
        self.match_cache[signature]=val
        return val

    def walking(self,board,p,flip,active):
        # Ordinary edges can be reused for every arrangement of crates.
        key=(flip,active)
        graph=self.walk_cache.get(key)
        if graph is None:
            graph=[[] for _ in range(1040)]
            wall=WALLS[flip][active]
            for q in INNER:
                if wall[self.w.base[q]&MASK]:
                    continue
                edges=graph[q]
                for d,off in enumerate(D):
                    u=q+off
                    t=self.w.base[u]&MASK
                    if not wall[t] and not wrong(t,d):
                        edges.append((u,d,t in MOTION))
            self.walk_cache[key]=graph
        prev={p:(p,-1,0)}
        wave=[p]
        for q in wave:
            length=prev[q][2]+1
            for u,d,motion in graph[q]:
                c=board[u]
                if c>=BOX or c&MASK in (PIT,SWITCH):
                    continue
                dest=static_land(self.w,board,u,d,flip,active) if motion else u
                if dest not in prev and board[dest]&MASK not in (PIT,SWITCH):
                    prev[dest]=(q,d,length)
                    wave.append(dest)
        return prev

    def plan(self,deadline):
        root=self.root
        bs=self.initial_boxes
        empty=frozenset()
        h0=self.estimate(root,bs,empty)
        if h0>=INF:
            return []
        heap=[(3.5*h0,0.,0,root,bs,empty)]
        records=[(-1,())]
        closed={}
        best_id,best_score=0,h0
        while heap and monotonic()<deadline:
            _,g,i,s,boxes,filled=heappop(heap)
            board=material(self.w,s)
            completed=(self.goals[0] in filled if self.sacrifice else all(p in boxes for p in self.goals))
            if completed:
                best_id=i
                break
            active=bool(self.w.plates) and all(p in boxes for p in self.w.plates)
            paths=self.walking(board,s.p,s.flip,active)
            sig=(boxes,filled,s.flip,min(paths))
            if g>=closed.get(sig,1e9):
                continue
            closed[sig]=g
            wall=WALLS[s.flip][active]
            if self.switches:
                # Toggle parity with the shortest controllable approach. The
                # macro is replayed with real phases before it is ever issued.
                toggle_choices=[]
                for q in self.switches:
                    for d,off in enumerate(D):
                        behind=q-off
                        if behind in paths:
                            toggle_choices.append((paths[behind][2],behind,d))
                        if not s.stones:
                            continue
                        u=q
                        for _ in range(6):
                            u-=off
                            c=board[u]
                            if wall[c&MASK] or c>=BOX or c&MASK in MOTION-{ICE} or c&MASK==MIMIC:
                                break
                            if u in paths:
                                toggle_choices.append((paths[u][2]+2,u,8+d))
                for length,behind,a in sorted(toggle_choices)[:3]:
                    pose=State(behind,s.hp,s.keys,s.flip,s.jumps,s.stones,s.bombs,s.edits,())
                    edge=step(self.w,pose,a,1)
                    if edge is None or edge.state.flip==s.flip or edge.state.hp<=0:
                        continue
                    walked=[a];at=behind
                    while at!=s.p:
                        at,walk_action,_=paths[at]
                        walked.append(walk_action)
                    ng=g+1+.15*length
                    n=edge.state
                    ni=len(records)
                    records.append((i,tuple(reversed(walked))))
                    nh=self.estimate(n,boxes,filled)
                    heappush(heap,(ng+3.5*nh,ng,ni,n,boxes,filled))
            for b in boxes:
                if wall[board[b]&MASK]:
                    continue
                for d,off in enumerate(D):
                    behind,q=b-off,b+off
                    if behind not in paths or wrong(board[b]&MASK,d) or board[q]>=BOX:
                        continue
                    target=board[q]&MASK
                    if wall[target] or wrong(target,d) or target in (K1,K2,V):
                        continue
                    pose=State(behind,s.hp,s.keys,s.flip,s.jumps,s.stones,s.bombs,s.edits,())
                    out=step(self.w,pose,d,1)
                    if not out or out.state.hp<=0:
                        continue
                    n=out.state
                    moved=self.box_set(n)
                    if moved==boxes:
                        continue
                    new_filled=filled
                    if len(moved)<len(boxes):
                        new_filled=frozenset(p for p,c in n.edits if p in self.initial_pits and c&MASK!=PIT)
                    if self.sacrifice and active and not all(p in moved for p in self.w.plates):
                        continue
                    nh=self.estimate(n,moved,new_filled)
                    if nh>=INF:
                        continue
                    length=paths[behind][2]
                    ng=g+1+.15*length
                    if b in self.goals:
                        ng+=1.1
                    walk=[d]
                    a=behind
                    while a!=s.p:
                        a,action,_=paths[a]
                        walk.append(action)
                    idx=len(records)
                    records.append((i,tuple(reversed(walk))))
                    score=nh+.045*ng
                    if score<best_score:
                        best_id,best_score=idx,score
                    if nh==0:
                        best_id=idx
                        heap.clear()
                        break
                    heappush(heap,(ng+3.5*nh,ng,idx,n,moved,new_filled))
                else:
                    continue
                break
            if best_id and best_score<=0.045*g+0.5 and not heap:
                break
        chunks=[]
        while best_id:
            best_id,chunk=records[best_id]
            chunks.append(chunk)
        return [a for chunk in reversed(chunks) for a in chunk]


def extinguish_route(w,root,turn,guns,deadline):
    """Plan the approach, detonation and escape for a cannon on a needed route."""
    if not (root.bombs or root.stones) or not guns:
        return []
    board=w.base
    guards=set(guns)
    protected={p for p in w.plates if BOX<=board[p]<TNT}
    box_count=sum(BOX<=board[p]<TNT for p in INNER)
    if box_count<=len(w.plates)+2:
        protected.update(p for p in INNER if BOX<=board[p]<TNT)
    bad_sites={b+k for b in protected for k in AREA}
    target_zone={q+k for q in guards for k in AREA}
    sites={p for p in target_zone if p not in bad_sites} if root.bombs else set()
    # Shooting an explosive chain can disable a gun from the other side of a wall.
    barrels={p for p in INNER if board[p]>=TNT}
    hot=barrels & target_zone
    wave=list(hot)
    for p in wave:
        for k in AREA:
            q=p+k
            if q in barrels and q not in hot:
                hot.add(q);wave.append(q)
    if root.bombs:
        sites.update(p+k for p in hot for k in AREA if p+k not in bad_sites)
    shoot={}
    active=bool(w.plates) and all(BOX<=board[p]<TNT for p in w.plates)
    wall=WALLS[root.flip][active]
    if hot and root.stones:
        shooter=Turn().start(w,root)
        for p in INNER:
            if wall[board[p]&MASK] or board[p]>=BOX:continue
            shooter.p=p
            for d in range(4):
                shooter.armed.clear();shooter.cells.clear();shooter.flip=root.flip
                shooter.stone(d)
                if shooter.armed & hot:
                    shoot.setdefault(p,[]).append(8+d)
    seeds=sites | set(shoot)
    if not seeds:
        return []
    rev=[[] for _ in range(1040)]
    for p in INNER:
        if wall[board[p]&MASK] or board[p]>=BOX:
            continue
        for d,off in enumerate(D):
            q=p+off;c=board[q];t=c&MASK
            if wall[t] or wrong(t,d):
                continue
            ends=[]
            if c<BOX and t!=PIT:
                ends.append((q,1.))
            if root.jumps and (t in MOTION or t==PIT or c>=BOX):
                u=q+off;b=board[u];land=b&MASK
                if b<BOX and not wall[land] and not wrong(land,d) and land!=PIT:
                    ends.append((u,3.))
            for u,price in ends:
                dest=static_land(w,board,u,d,root.flip,active) if board[u]&MASK in MOTION else u
                if board[dest]&MASK!=PIT:
                    rev[dest].append((p,price))
    distances=reverse_dist(rev,[(p,0.) for p in seeds if 0<=p<1040])
    if distances[root.p]>=INF:
        return []
    heap=[(0.,0.,0,root,0)]
    parents=[(-1,-1)]
    seen={(root,turn%w.period):0.}
    while heap and monotonic()<deadline:
        _,cost,idx,s,depth=heappop(heap)
        if depth>=min(65,241-turn):
            continue
        model=Turn().start(w,s)
        choices=[a for a in action_options(w,s,turn+depth,model) if a<8 or a==WAIT]
        if s.p in sites and s.bombs and not s.fuses:
            choices.append(BOMB)
        if s.stones:
            choices.extend(shoot.get(s.p,()))
        for a in choices:
            if a<4 and model.at(s.p+D[a])>=BOX:continue
            edge=step(w,s,a,turn+depth)
            if not edge or edge.state.hp<root.hp:continue
            n=edge.state;edits=dict(n.edits)
            if any(edits.get(p,board[p])<BOX for p in protected if board[p]>=BOX):
                continue
            ncost=cost+1+(2 if 4<=a<8 else 0)
            tag=(n,(turn+depth+1)%w.period)
            if ncost>=seen.get(tag,1e8):continue
            seen[tag]=ncost
            ni=len(parents);parents.append((idx,a))
            if any(edits.get(p,board[p])==FLOOR for p in guards):
                return reconstruct(parents,ni)
            h=distances[n.p] if not n.fuses else 0.
            heappush(heap,(ncost+1.6*h,ncost,ni,n,depth+1))
    return []


def cache_route(w,root,turn,actions,memory,retime=False):
    """Replay against exact physics. A cached step is used only on its predicted state."""
    plan=[]
    guns_hit=set()
    s=root
    def append(n,a):
        nonlocal s
        if n.hp<s.hp and w.guns:
            tracer=Turn().start(w,s)
            tracer.play(a,turn+len(plan),False)
            rays,_=w.rays(s.edits,n.flip,tracer.active,turn+len(plan))
            bits=0
            for p in tracer.path:bits|=rays.get(p,0)
            guns_hit.update(p for i,(p,d,rate) in enumerate(w.guns) if bits&(1<<i))
        before=hash(tuple(material(w,s)))
        plan.append((sign(s,before,turn+len(plan)),a))
        s=n
    for i,a in enumerate(actions):
        tick=turn+len(plan)
        if tick>240:
            break
        res=step(w,s,a,tick)
        if retime and w.guns:
            def outlook(start,now):
                trial=start
                for j in range(i,min(i+4,len(actions))):
                    edge=step(w,trial,actions[j],now+j-i)
                    if not edge or edge.state.hp<=0:
                        return -200
                    trial=edge.state
                    if edge.won:
                        break
                return trial.hp
            rating=outlook(s,tick)
            if rating < s.hp:
                waitstate=s
                best=rating
                count=0
                for delay in range(1,12):
                    idle=step(w,waitstate,WAIT,tick+delay-1)
                    if not idle or idle.state.hp<=0:
                        break
                    waitstate=idle.state
                    hp=outlook(waitstate,tick+delay)
                    if hp>best:
                        count,best=delay,hp
                        if hp>=s.hp:
                            break
                for _ in range(count):
                    if turn+len(plan)>240:
                        break
                    idle=step(w,s,WAIT,turn+len(plan))
                    append(idle.state,WAIT)
                tick=turn+len(plan)
                res=step(w,s,a,tick)
        if tick>240 or res is None or res.state.hp<=0:
            break
        append(res.state,a)
        if res.won:
            break
    memory["hazard_guns"]=sorted(guns_hit)
    if plan:
        memory["route"]=list(reversed(plan[1:]))
        return ACTIONS[plan[0][1]]
    return None


def decide_action(state,memory):
    start=monotonic()
    turn=state["turn"]
    deadline=start+(1.54 if turn==1 else .325)
    board,root=encode(state)
    stamp=sign(root,hash(tuple(board)),turn)
    route=memory.get("route")
    if route:
        expected,a=route.pop()
        # Workers may transport memory through JSON, converting tuples to lists.
        if (expected[0:7]==stamp[0:7] or tuple(expected[:7])==stamp[:7]) and tuple(map(tuple,expected[7]))==stamp[7] and tuple(expected[8:])==stamp[8:]:
            return ACTIONS[a]
        route.clear()
    w=Arena().prepare(board,tuple(pos(state["targets"][k]) for k in ("K1","K2","V")))
    visits=memory.setdefault("visits",{})
    visits[root.p]=visits.get(root.p,0)+1
    active=bool(w.plates) and all(BOX<=board[p]<TNT for p in w.plates)
    closed=Guide().prepare(w,root,active)
    if w.plates and PG in board and not active:
        opened=Guide().prepare(w,root,True)
        if closed.value(root)>opened.value(root)+10:
            crate_end=min(deadline-.065,start+(1.23 if turn==1 else .205))
            if monotonic()<crate_end:
                planner=Crates().prepare(w,root,w.plates)
                pushes=planner.plan(crate_end)
                if pushes:
                    action=cache_route(w,root,turn,pushes,memory,retime=True)
                    if action is not None:
                        threats=memory["hazard_guns"]
                        if threats and monotonic()+.03<deadline:
                            disarm=extinguish_route(w,root,turn,threats,deadline-.012)
                            if disarm:
                                return cache_route(w,root,turn,disarm,memory)
                        return action
    path,done=search(w,root,turn,closed,deadline,visits,weight=1.65+min(.7,.12*(visits[root.p]-1)))
    if path:
        action=cache_route(w,root,turn,path if done else path[:14],memory)
        if action is not None:
            return action
    # No surviving route was found in this slice. Secure the greatest reachable
    # stage progress, including any key or vault crossed by a momentum chain.
    best=(-1e12,WAIT)
    for a in range(14):
        model=Turn().start(w,root)
        edge=model.play(a,turn,False)
        n=edge.state
        goals=[w.targets[i] for i in range(2) if not n.keys&(1<<i)] or [w.targets[2]]
        distance=min(dist(p,q) for p in model.path for q in goals)
        score=10000*edge.won+500*(n.hp>0)+200*n.keys.bit_count()-distance+.005*n.hp
        if n.p!=root.p:
            score+=.1
        if score>best[0]:
            best=score,a
    return ACTIONS[best[1]]

CERTIFICATE = 'uuuuuuuuurrrrrrrrrdzuuddddddllllllluulurruuldldrrrluuuuldddldrrrrrrdddddllllluuuulurrrrrlllddddddddddlldrrrlddddldruuuuuruuuurrrrrrrRURuuuuuuurrrrrrrrddddddddddddddrdrddrkllludrruuuuuuuurrrrrrr'

