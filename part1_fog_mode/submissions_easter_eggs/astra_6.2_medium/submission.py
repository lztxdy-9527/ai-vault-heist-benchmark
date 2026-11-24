"""ASTRA / blind vault tournament."""
from heapq import heappop, heappush
from time import perf_counter

DIR = {"U": -40, "D": 40, "L": -1, "R": 1}
NAMES = tuple(DIR)
DELTA = tuple(DIR.values())
NEXT = tuple(tuple(y*40+x+d if 0 <= x+(d if abs(d)==1 else 0)<40 and
                   0 <= y+(d//40 if abs(d)==40 else 0)<26 else -1
                   for d in DELTA) for y in range(26) for x in range(40))
WALL = {"W","T_W","LASER_U","LASER_D","LASER_L","LASER_R"}
IMMUNE = {"T_W","K1","K2","V","PIT","PORTAL_1A","PORTAL_1B","PORTAL_2A","PORTAL_2B"}
ACTIONS = ("MOVE_U","MOVE_D","MOVE_L","MOVE_R","JUMP_U","JUMP_D","JUMP_L","JUMP_R",
           "WAIT","BOMB","THROW_U","THROW_D","THROW_L","THROW_R")


def build_dungeon():
    g = [["T_W" if x in (0,39) or y in (0,25) else "EMPTY"
          for x in range(40)] for y in range(26)]
    for y in (12,13,14):
        g[y][4] = "LASER_L"
    for x in (1,2,3):
        g[15][x] = "LASER_U"
        g[11][x] = "W"
    g[11][1], g[6][12] = "PORTAL_1A","PORTAL_1B"
    for x,y,name in ((22,5,"K1"),(27,21,"K2")):
        g[y][x] = name
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            g[y+dy][x+dx] = "W"
    for x in range(32,39):
        for y in range(10,16):
            if x in (32,38) or y in (10,15):
                g[y][x] = "W"
    g[13][35],g[14][35] = "PORTAL_2B","V"
    g[11][3] = "PORTAL_2A"
    for x,y in ((34,13),(35,12),(36,13)):
        g[y][x] = "PIT"
    moves = ["MOVE_L","JUMP_U"]  # portal exit (12,5)
    def walk(direction,n):
        moves.extend(["MOVE_"+direction]*n)
    walk("R",8)  # (20,5)
    moves.append("BOMB")
    walk("L",2)
    walk("R",4)  # K1
    walk("L",2)
    walk("D",16)
    walk("R",5)  # (25,21)
    moves.append("BOMB")
    walk("L",2)
    walk("R",4)  # K2
    walk("L",2)
    walk("U",11)
    walk("L",22)  # approach the other entrance from above
    walk("D",1)
    return {"grid":g,"taunt":"第三拍灯亮之前，记得回头。","author_solution":moves}


def dist(a,b):
    return abs(a%40-b%40)+abs(a//40-b//40)


def high(tile, flip):
    return tile in WALL or tile == ("B_GATE" if flip else "R_GATE")


def reflect(tile,di):
    if di >= 2:
        return 0 if tile[-2]=="N" else 1
    return 3 if tile[-1]=="E" else 2


class Board:
    def __init__(self,s,m):
        h=s["hero"]
        self.pos=h["y"]*40+h["x"]
        self.turn=s["turn"]
        self.flip=s["gates_flipped"]
        if "terrain" not in m:
            m["terrain"]=["T_W" if p%40 in (0,39) or p//40 in (0,25) else "?" for p in range(1040)]
            m["occ"]={}
            m["clues"]=[None]*1040
            m["visits"]={}
            m["warn"]={}
        self.t=m["terrain"]
        self.occ=m["occ"]
        self.clues=m["clues"]
        self.visits=m["visits"]
        self.visits[self.pos]=1+self.visits.get(self.pos,0)
        self.targets=[v[1]*40+v[0] for v in (s["targets"][k] for k in ("K1","K2","V"))]
        self.goals=[p for i,p in enumerate(self.targets[:2]) if not h["keys"][i]] or self.targets[2:]
        for y,row in enumerate(s["visible_mask"]):
            for x,visible in enumerate(row):
                if visible:
                    p=y*40+x
                    self.t[p]=s["terrain"][y][x]
                    self.clues[p]=s["clues"][y][x]
                    o=s["occupant"][y][x]
                    if o:
                        self.occ[p]=o
                    else:
                        self.occ.pop(p,None)
        self.portals={t:p for p,t in enumerate(self.t) if t.startswith("PORTAL")}
        self.lasers=[(p,NAMES.index(t[-1])) for p,t in enumerate(self.t) if t.startswith("LASER")]
        # Remember lines from unseen cannons; replace information on the next firing sample.
        self.warn=m["warn"]
        if self.turn%3==0:
            for p in list(self.warn):
                if s["visible_mask"][p//40][p%40]:
                    del self.warn[p]
            for w in s["laser_warnings"]:
                p=w["y"]*40+w["x"]
                self.warn.setdefault(p,[]).append(w["dir"])
        self.bombs=tuple((v["y"]*40+v["x"],v["timer"]) for v in s["bombs"])
        self.initial=(self.pos,h["hp"],h["jumps"],h["throws"],h["bombs"],self.flip,{},self.occ,self.bombs)
        self.bans=m.setdefault("bans",{})
        prior=m.get("last")
        if prior and prior[0]==self.pos and prior[1]<8:
            self.bans[self.pos*8+prior[1]]=self.turn+5

    def pair(self,t):
        return self.portals.get(t[:-1]+("A" if t[-1]=="B" else "B"))

    def heuristic(self):
        # Reverse relaxed shortest paths: pass unknown ground, price breaches,
        # include all known non-local movement so the search can head away from a key.
        t=self.t
        rev={}
        for p,v in enumerate(t):
            if v.startswith("PORTAL"):
                q=self.pair(v)
                if q is not None:
                    rev.setdefault(q,[]).append((p,0.12))
            elif v.startswith("SPRING"):
                di=NAMES.index(v[-1])
                q=p
                for k in range(3):
                    n=NEXT[q][di]
                    if n<0 or high(t[n],self.flip) or n in self.occ: break
                    q=n
                if q!=p: rev.setdefault(q,[]).append((p,0.15))
        ds=[2000.0]*1040
        pq=[]
        for p in self.goals:
            ds[p]=0
            heappush(pq,(0,p))
        while pq:
            cost,p=heappop(pq)
            if ds[p]!=cost: continue
            v=t[p]
            if v=="T_W": continue
            w=1.
            if high(v,self.flip) or self.occ.get(p)=="TNT": w=12
            elif v=="PIT": w=9
            elif v=="?": w=1.48
            elif v=="ICE" or v.startswith("MIRROR"): w=.48
            for n in NEXT[p]:
                if n>=0 and cost+w<ds[n] and t[n]!="T_W":
                    ds[n]=cost+w
                    heappush(pq,(cost+w,n))
            for n,w2 in rev.get(p,()):
                if cost+w2<ds[n]:
                    ds[n]=cost+w2
                    heappush(pq,(ds[n],n))
        return ds

    def simulate(self,node,act,turn):
        start,hp,jumps,throws,bombs,flip,patch,occ,timers=node
        pos=start
        trail={start}
        armed=set()
        speculative=False
        unknown_port=False
        gain=0
        oldpatch,oldocc=patch,occ
        def tile(p):
            return patch.get(p,self.t[p])
        def put(p,t):
            nonlocal patch
            if patch is oldpatch: patch=dict(patch)
            patch[p]=t
        def mutable_occ():
            nonlocal occ
            if occ is oldocc: occ=dict(occ)
        def blocked(p,box=False):
            return (p<0 or high(tile(p),flip) or p in occ or
                    (box and (p==start or tile(p) in ("K1","K2","V"))))
        def move(src,q,di,box):
            nonlocal hp,flip,speculative,unknown_port,gain
            passed=0
            paired=False
            for tick in range(32):
                if tile(src)=="CRACK": put(src,"PIT")
                if box:
                    mutable_occ()
                    occ.pop(src,None)
                    occ[q]="BOX"
                else:
                    trail.add(q)
                v=tile(q)
                if v=="?": speculative=True
                if v=="PIT":
                    if box:
                        occ.pop(q)
                        put(q,"EMPTY")
                    else: hp=0
                    break
                if v=="SWITCH": flip=not flip
                if v=="CHEST":
                    bad=any(n>=0 and self.clues[n] for n in NEXT[q])
                    if bad or not box:
                        if not box:
                            if bad: hp-=45
                            elif all(n<0 or self.clues[n] is not None for n in NEXT[q]):
                                hp=min(100,hp+30)
                            else: gain+=2
                        put(q,"EMPTY")
                if not box and q in self.goals: break
                if tick==31: break
                if v.startswith("PORTAL") and not paired:
                    n=self.pair(v)
                    if n is None:
                        unknown_port=True
                        break
                    if blocked(n,box): break
                    passed+=1
                    paired=True
                else:
                    if paired:
                        paired=False
                        if passed>=2: break
                    elif v.startswith("SPRING"):
                        di=NAMES.index(v[-1])
                        n=q
                        for k in range(3):
                            nxt=NEXT[n][di]
                            if blocked(nxt,box):
                                if box and occ.get(nxt)=="TNT": armed.add(nxt)
                                break
                            n=nxt
                        if n==q: break
                        src,q=q,n
                        continue
                    elif v.startswith("MIRROR"):
                        di=reflect(v,di)
                    elif v!="ICE": break
                    n=NEXT[q][di]
                    if blocked(n,box): break
                src,q=q,n
            return q
        di=act%4
        if act<8:
            q=NEXT[pos][di]
            if act>=4:
                if not jumps or q<0 or high(tile(q),flip): return None
                jumps-=1
                q=NEXT[q][di]
            elif occ.get(q)=="BOX":
                n=NEXT[q][di]
                if blocked(n,True): return None
                move(q,n,di,True)
            if blocked(q):
                if occ is oldocc: return None
            else: pos=move(pos,q,di,False)
        elif act==9:
            if not bombs or any(p==pos for p,_ in timers): return None
            bombs-=1
            timers=timers+((pos,3),)
        elif act>=10:
            if not throws: return None
            di=act-10
            q=pos
            passed=0
            hit=False
            for step in range(38):
                q=NEXT[q][di]
                if q<0: break
                v=tile(q)
                if high(v,flip) or occ.get(q)=="BOX": break
                if occ.get(q)=="TNT":
                    armed.add(q); hit=True; break
                if v=="SWITCH":
                    flip=not flip; hit=True; break
                if v=="CHEST" and any(n>=0 and self.clues[n] for n in NEXT[q]):
                    put(q,"EMPTY"); hit=True; break
                if v.startswith("MIRROR"): di=reflect(v,di)
                elif v.startswith("PORTAL"):
                    n=self.pair(v)
                    if n is None or n in occ: break
                    q=n; passed+=1
                    if passed>=2 or step==5: break
                elif step>=5 and v!="ICE": break
            if not hit: return None
            throws-=1
        win=pos in self.goals and self.goals==self.targets[2:]
        def explode(seeds):
            nonlocal timers,hp
            allbomb=dict(timers)
            sources=set(seeds)
            todo=list(seeds)
            cells=set()
            while todo:
                p=todo.pop()
                for y in range(max(0,p//40-1),min(26,p//40+2)):
                    for x in range(max(0,p%40-1),min(40,p%40+2)):
                        n=y*40+x
                        cells.add(n)
                        if (n in allbomb or occ.get(n)=="TNT") and n not in sources:
                            sources.add(n); todo.append(n)
            for p in sources:
                if abs(p%40-pos%40)<=1 and abs(p//40-pos//40)<=1:
                    hp-=50 if p in allbomb else 60
            timers=tuple((p,k) for p,k in timers if p not in sources)
            for n in cells:
                if n in occ: mutable_occ(); occ.pop(n)
                v=tile(n)
                if v=="CRACK": put(n,"PIT")
                elif v not in IMMUNE and v not in ("EMPTY","?"): put(n,"EMPTY")
            if tile(pos)=="PIT": hp=0
        if not win and hp>0:
            timers=tuple((p,k-1) for p,k in timers)
            armed.update(p for p,k in timers if k<=0)
            if armed: explode(armed)
            if turn%3==0 and hp>0:
                hits=set()
                covered=set()
                lit=set()
                for p,ld in self.lasers:
                    if not tile(p).startswith("LASER"): continue
                    q=p
                    for k in range(10):
                        q=NEXT[q][ld]
                        if q<0 or high(tile(q),flip) or occ.get(q)=="BOX": break
                        if occ.get(q)=="TNT":
                            lit.add(q); break
                        if q in trail:
                            hits.add(p)
                            covered.add((ld,q))
                # Forecast out-of-sight cannons from the last observed firing pattern.
                if flip==self.flip and patch is oldpatch and not patch and occ is self.occ:
                    for q in trail:
                        for name in self.warn.get(q,()):
                            ld=NAMES.index(name)
                            if (ld,q) not in covered:
                                hits.add((ld,q%40 if ld<2 else q//40))
                hp-=50*len(hits)
                if lit and hp>0: explode(lit)
        if hp<=0: return None
        return (pos,hp,jumps,throws,bombs,flip,patch,occ,timers),speculative,unknown_port,gain

def detour_guide(b, memory, normal):
    stage=tuple(b.goals)
    closest=min(dist(b.pos,p) for p in stage)
    if memory.get("stage")!=stage:
        memory.update(stage=stage,closest=closest,advanced=b.turn,detour=None)
    if closest<memory["closest"]:
        memory.update(closest=closest,advanced=b.turn,detour=None)
    dest=memory.get("detour")
    if dest is not None and (dest==b.pos or b.turn>=memory["detour_until"]
                             or (memory["seek_unknown"] and b.t[dest]!="?")):
        memory.update(advanced=b.turn,detour=None)
        dest=None
    if dest is None and b.turn-memory["advanced"]>=15:
        original=b.goals
        b.goals=[b.pos]
        away=b.heuristic()
        b.goals=original
        tried=memory.setdefault("explored_dest",{})
        options=[]
        closed="B_GATE" if b.flip else "R_GATE"
        needs_switch=closed in b.t
        for q,v in enumerate(b.t):
            if away[q]>=1900 or q==b.pos: continue
            priority=0
            if v=="?" and any(n>=0 and b.t[n]!="?" and not high(b.t[n],b.flip)
                              and b.t[n]!="PIT" for n in NEXT[q]):
                priority=3
            elif v=="SWITCH" and needs_switch: priority=-7
            elif v.startswith("PORTAL") and b.pair(v) is None: priority=-10
            else: continue
            penalty=30 if b.turn-tried.get(q,-100)<50 else 0
            options.append((away[q]+priority+penalty+.22*min(dist(q,p) for p in stage),q))
        if options:
            dest=min(options)[1]
            tried[dest]=b.turn
            memory.update(detour=dest,detour_until=b.turn+26,seek_unknown=b.t[dest]=="?")
    if dest is None: return normal
    original=b.goals
    b.goals=[dest]
    ds=b.heuristic()
    b.goals=original
    return ds


def decide_action(state,memory):
    deadline=perf_counter()+0.25
    b=Board(state,memory)
    guide=b.heuristic()
    turns_left=state["turns_left"]
    # If the objective is sealed behind unknown topology, route to the nearest
    # uncharted ground or unpaired portal, even when it lies behind the hero.
    if guide[b.pos]>=1900:
        goals=b.goals
        frontier=[p for p,v in enumerate(b.t) if v=="?" or
                  (v.startswith("PORTAL") and b.pair(v) is None)]
        if frontier:
            b.goals=frontier
            guide=b.heuristic()
            b.goals=goals
    guide=detour_guide(b,memory,guide)
    original=b.initial
    root_h=guide[b.pos]
    pq=[(0.,0,0.,0,-1,original)]
    best={}
    rank=float("inf")
    answer=8
    seq=0
    expanded=0
    portal_choice=None
    completed=None
    has_shot=any(v in ("TNT",) for v in b.occ.values()) or any(
        v in ("SWITCH","CHEST") for v in b.t)
    while pq and expanded<650 and perf_counter()<deadline:
        estimate,_,g,depth,first,node=heappop(pq)
        p,hp,j,th,bo,flip,patch,occ,timers=node
        turn=b.turn+depth
        sig=(p,turn%3,j,th,bo,flip,tuple(sorted(patch.items())),
             tuple(sorted(occ.items())),timers,hp)
        if g>=best.get(sig,1e9): continue
        best[sig]=g
        if depth:
            reached=p in b.goals or p==memory.get("detour")
            if reached:
                completed=first
                break
            # Compare executable prefixes by progress, including the cost of
            # turning back out of cul-de-sacs; avoid rewarding a bare WAIT.
            merit=guide[p]+0.39*g+2.3*min(8,b.visits.get(p,0))
            if timers: merit+=4
            if depth==1 and first==8: merit+=6
            if p==b.pos: merit+=5
            if b.t[p]=="?": merit-=1.5
            if merit<rank:
                rank,answer=merit,first
        if depth>=min(55,turns_left): continue
        expanded+=1
        local=[n for n in NEXT[p] if n>=0]
        actions=list(range(4))
        if j: actions.extend((4,5,6,7))
        if b.lasers or timers or b.warn: actions.append(8)
        if bo and not timers and any(patch.get(n,b.t[n]) in
                ("W","R_GATE","B_GATE","LASER_U","LASER_D","LASER_R","LASER_L")
                or occ.get(n) in ("BOX","TNT") for n in local):
            actions.append(9)
        if th and has_shot: actions.extend((10,11,12,13))
        for act in actions:
            result=b.simulate(node,act,turn)
            if result is None: continue
            new,unknown,portal,caution=result
            q=new[0]
            na=act if first<0 else first
            fee=1.0+max(0,hp-new[1])*.46+caution
            if act in range(4,8):
                fee+=1.55 if j>=2 else 2.45
            if act==9: fee+=4.8
            if act>=10: fee+=1.8
            if unknown: fee+=1.1
            if depth<8 and q!=p:
                fee+=min(5,b.visits.get(q,0))*.75
            if depth==0 and act<8 and b.bans.get(p*8+act,0)>=turn: fee+=12
            if portal:
                # A one-way trip into fog can bypass a sealed region. Commit
                # only when its approach beats the best currently known route.
                val=g+fee+max(2.,min(root_h*.40,20.))
                if portal_choice is None or val<portal_choice[0]:
                    portal_choice=(val,na)
                continue
            ng=g+fee
            seq+=1
            heappush(pq,(ng+1.45*guide[q],seq,ng,depth+1,na,new))
    if completed is not None:
        answer=completed
    if portal_choice and (completed is None or portal_choice[0]<g-2):
        answer=portal_choice[1]
    memory["last"]=(b.pos,answer)
    return ACTIONS[answer]

