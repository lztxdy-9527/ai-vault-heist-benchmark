"""Independent coordinate-based referee for local v2.2 verification only."""
from collections import deque
from pathlib import Path
from time import monotonic
import json
import random
import sys
import ast
import submission as entry
from submission_template_v22 import TILE_COSTS, VALID_ACTIONS

DIR={"U":(0,-1),"D":(0,1),"L":(-1,0),"R":(1,0)}
def adj(p,d):
    dx,dy=DIR[d]
    return p[0]+dx,p[1]+dy
def area(p):
    return [(p[0]+x,p[1]+y) for y in (-1,0,1) for x in (-1,0,1)]
def reflect(t,d):
    if d in "UD":return "R" if "E" in t[-2:] else "L"
    return "U" if "N" in t[-2:] else "D"
def blank():
    g=[["T_W" if x in (0,39) or y in (0,25) else "EMPTY" for x in range(40)] for y in range(26)]
    g[5][20],g[20][20],g[13][35]="K1","K2","V"
    return g

class Referee:
    def __init__(self,g):
        self.t={(x,y):v for y,row in enumerate(g) for x,v in enumerate(row)}
        self.o={p:v for p,v in self.t.items() if v in ("TNT","BOX")}
        for p in self.o:self.t[p]="EMPTY"
        self.plates={p for p,v in self.t.items() if v=="PLATE"}
        self.ports={v:p for p,v in self.t.items() if v.startswith("PORTAL")}
        self.guns={p:(v[-1],4 if v.startswith("LASER2") else 3) for p,v in self.t.items() if v.startswith("LASER")}
        self.targets={v:p for p,v in self.t.items() if v in ("K1","K2","V")}
        chests={p for p,t in self.t.items() if t in ("MIMIC","HEAL")}
        self.clue={}
        for p,t in self.t.items():
            if t=="MIMIC":
                for d in DIR:
                    c=adj(p,d)
                    if (self.t[c]=="EMPTY" and c not in self.o and c not in self.clue.values()
                        and not(1<=c[0]<=3 and 12<=c[1]<=14)
                        and not((chests-{p}) & {adj(c,j) for j in DIR})):
                        self.clue[p]=c;break
                assert p in self.clue
        self.p=(2,13);self.hp=100;self.keys=[False,False];self.flip=False
        self.jumps=3;self.stones=3;self.charges=2;self.fuses={};self.turn=1
        self.path=set();self.armed=set();self.won=False;self.damage=0.

    def active(self):
        return bool(self.plates) and all(self.o.get(p)=="BOX" for p in self.plates)

    def wall(self,p):
        t=self.t.get(p,"T_W")
        return t in ("T_W","W","B_GATE" if self.flip else "R_GATE") or t.startswith("LASER") or (t=="P_GATE" and not self.active())

    def wrong(self,p,d):
        t=self.t[p]
        return t.startswith("ONEWAY_") and t[-1]!=d

    def block(self,p,d,box):
        return self.wall(p) or self.wrong(p,d) or p in self.o or (box and (p==self.p or self.t[p] in ("K1","K2","V")))

    def hurt(self,a,b=0):
        h=max(0,self.hp)
        self.damage+=min(h,a+b)*a/(a+b) if a+b else 0
        self.hp-=a+b

    def slide(self,p,q,d,box):
        arrived=False;count=0
        for i in range(32):
            if self.t[p]=="CRACK":self.t[p]="PIT"
            if box:
                del self.o[p];self.o[q]="BOX"
            else:self.p=q;self.path.add(q)
            t=self.t[q]
            if box and t=="PIT":
                self.t[q]="EMPTY";del self.o[q];return
            if t=="MIMIC":
                self.clue.pop(q,None);self.t[q]="EMPTY"
                if not box:self.hurt(45);return
            elif t=="HEAL" and not box:self.hp=min(100,self.hp+30);self.t[q]="EMPTY"
            elif t=="PIT" and not box:self.hurt(100);return
            elif t=="SWITCH":self.flip=not self.flip
            elif not box and t in ("K1","K2"):self.keys[int(t[-1])-1]=True;self.t[q]="EMPTY"
            elif not box and t=="V" and all(self.keys):self.won=True;return
            if i==31:return
            p=q
            if arrived:
                arrived=False
                if count==2:return
            elif t.startswith("PORTAL"):
                q=self.ports[t[:-1]+("B" if t[-1]=="A" else "A")]
                if q in self.o or (box and q==self.p):return
                arrived=True;count+=1;continue
            elif t.startswith("SPRING"):
                d=t[-1]
                for _ in range(3):
                    n=adj(q,d)
                    if self.block(n,d,box):
                        if box and self.o.get(n)=="TNT":self.armed.add(n)
                        break
                    q=n
                if q==p:return
                continue
            elif t.startswith("MIRROR"):d=reflect(t,d)
            elif t!="ICE":return
            q=adj(p,d)
            if self.block(q,d,box):return

    def throw(self,d):
        p=self.p;n=0
        for step in range(1,39):
            p=adj(p,d)
            if self.wall(p) or self.o.get(p)=="BOX":return
            if self.o.get(p)=="TNT":self.armed.add(p);return
            t=self.t[p]
            if t=="SWITCH":self.flip=not self.flip;return
            if t=="MIMIC":self.t[p]="EMPTY";self.clue.pop(p,None);return
            if t.startswith("MIRROR"):d=reflect(t,d)
            if t.startswith("PORTAL") and n<2:
                q=self.ports[t[:-1]+("B" if t[-1]=="A" else "A")]
                if q not in self.o:
                    n+=1;p=q
                    if n==2:return
            if step>=6 and t!="ICE" and not t.startswith("MIRROR"):
                if step==6 or not t.startswith("PORTAL"):return

    def rays(self):
        beams={};lit=set()
        for gun,(d,rate) in self.guns.items():
            if not self.t[gun].startswith("LASER") or self.turn%rate:continue
            p=gun;cells=set()
            for _ in range(10):
                p=adj(p,d)
                if self.wall(p) or self.o.get(p)=="BOX":break
                if self.o.get(p)=="TNT":lit.add(p);break
                cells.add(p)
            beams[gun]=cells
        return beams,lit

    def blast(self,barrels,due):
        q=[(p,"TNT") for p in barrels]+[(p,"B") for p in due]
        seen=set(q);hit=set();a=b=0
        for center,kind in q:
            cells=area(center)
            if self.p in cells:
                if kind=="B":b+=50
                else:a+=60
            for p in cells:
                if p in hit:continue
                hit.add(p)
                for tag,present in (("TNT",self.o.get(p)=="TNT"),("B",p in self.fuses)):
                    if present and (p,tag) not in seen:
                        seen.add((p,tag));q.append((p,tag))
        self.hurt(a,b)
        for p in hit:
            self.o.pop(p,None);self.fuses.pop(p,None);self.clue.pop(p,None)
            t=self.t[p]
            if t not in ("T_W","PIT","K1","K2","V","P_GATE","PLATE") and not t.startswith(("ONEWAY","PORTAL")):
                self.t[p]="PIT" if t=="CRACK" else "EMPTY"
        if self.hp>0 and self.t[self.p]=="PIT":self.hurt(100)

    def act(self,a):
        assert self.hp>0 and not self.won and a in VALID_ACTIONS
        self.armed=set();self.path={self.p}
        p=self.p;d=a[-1]
        if a.startswith("MOVE"):
            q=adj(p,d)
            if not self.wall(q) and not self.wrong(q,d):
                if self.o.get(q)=="BOX" and not self.block(adj(q,d),d,True):
                    self.slide(q,adj(q,d),d,True)
                if not self.block(q,d,False):self.slide(p,q,d,False)
        elif a.startswith("JUMP") and self.jumps:
            self.jumps-=1;q=adj(p,d);n=adj(q,d)
            if not self.wall(q) and not self.wrong(q,d) and not self.block(n,d,False):self.slide(p,n,d,False)
        elif a.startswith("THROW") and self.stones:self.stones-=1;self.throw(d)
        elif a=="BOMB" and self.charges and p not in self.fuses:self.charges-=1;self.fuses[p]=3
        if self.hp<=0 or self.won:return
        self.fuses={p:v-1 for p,v in self.fuses.items()}
        due=[p for p,v in self.fuses.items() if v==0]
        if due or self.armed:self.blast(self.armed,due)
        if self.hp>0:
            rays,lit=self.rays()
            self.hurt(50*sum(bool(c&self.path) for c in rays.values()))
            if self.hp>0 and lit:self.blast(lit,[])
        self.turn+=1

    def observation(self):
        beams,_=self.rays()
        hints=[dict(x=p[0],y=p[1],dir=self.guns[gun][0],period=self.guns[gun][1],cannon=list(gun)) for gun,cells in beams.items() for p in cells]
        bones=set(self.clue.values())
        return dict(turn=self.turn,turns_left=241-self.turn,mode="FULL",hero=dict(x=self.p[0],y=self.p[1],hp=self.hp,keys=self.keys[:],jumps=self.jumps,bombs=self.charges,throws=self.stones),
                    terrain=[["CHEST" if self.t[x,y] in ("HEAL","MIMIC") else self.t[x,y] for x in range(40)] for y in range(26)],
                    occupant=[[self.o.get((x,y)) for x in range(40)] for y in range(26)],visible_mask=[[True]*40 for _ in range(26)],
                    clues=[[(x,y) in bones for x in range(40)] for y in range(26)],targets=self.targets,
                    gates_flipped=self.flip,plates_active=self.active(),bombs=[dict(x=x,y=y,timer=v) for (x,y),v in self.fuses.items()],
                    laser_warnings=sorted(hints,key=lambda h:(h["y"],h["x"],h["dir"],h["period"],h["cannon"])))

def compare(ref,action):
    st=ref.observation()
    board,root=entry.encode(st)
    w=entry.Arena().prepare(board,tuple(entry.pos(st["targets"][k]) for k in ("K1","K2","V")))
    model=entry.Turn().start(w,root)
    out=model.play(entry.ACTIONS.index(action),ref.turn,False)
    ref.act(action)
    newboard,newroot=entry.encode(ref.observation())
    res=out.state
    assert (res[:7],res.fuses,out.won)==(newroot[:7],newroot.fuses,ref.won),(action,res,newroot)
    assert entry.material(w,res)==newboard,(action,ref.p)
    assert model.active==ref.active() and set(model.path)=={entry.pos(p) for p in ref.path}

def fixture(tiles,p=(2,13),t=1):
    g=blank()
    for (x,y),v in tiles.items():g[y][x]=v
    ref=Referee(g);ref.p=p;ref.turn=t
    return ref

def test_vectors():
    vec=json.loads(Path("golden_vectors_v22.json").read_text(encoding="utf-8-sig"))["vectors"]
    e=[v.get("expected",{}) for v in vec]
    g=blank()
    for v in vec[0]["placed_inner_tiles"]:g[v["y"]][v["x"]]=v["tile"]
    r=Referee(g);spent=sum(TILE_COSTS[t] for row in g[1:-1] for t in row[1:-1])
    assert (spent,3000-spent,r.active())==(e[0]["spent_gold"],e[0]["vault_gold"],e[0]["initial_plates_active"])
    r=fixture({(5,13):"PLATE",(34,13):"P_GATE",(7,13):"BOX"},(4,13))
    compare(r,"MOVE_R");assert not r.active() and r.wall((34,13))
    r.p=(8,13);compare(r,"MOVE_L");compare(r,"MOVE_L");assert r.active() and not r.wall((34,13))
    r=fixture({(15,8):"LASER_D",(12,10):"LASER2_R"},(15,10),12)
    assert sorted(h["period"] for h in r.observation()["laser_warnings"] if (h["x"],h["y"])==r.p)==e[2]["warning_periods_at_15_10"]
    compare(r,"WAIT");assert r.hp==e[2]["hero_hp_after"]
    r=fixture({(5,13):"CRACK",(6,13):"ONEWAY_L"},(5,13));r.o[6,13]="BOX"
    compare(r,"MOVE_R");assert r.p==(5,13) and r.o[6,13]=="BOX" and r.t[5,13]=="CRACK"
    r=fixture({(10,10):"MIRROR_NE",(10,9):"ONEWAY_R"},(9,10));compare(r,"MOVE_R");assert list(r.p)==e[3]["case_b_hero_pos"]
    r=fixture({(10,10):"SPRING_R",(12,10):"ONEWAY_L"},(9,10));compare(r,"MOVE_R");assert list(r.p)==e[4]["spring_land_pos"]
    r=fixture({(6,14):"ONEWAY_L"},(5,14));compare(r,"JUMP_R");assert list(r.p)==e[4]["jump_failed_pos"] and r.jumps==2
    r=fixture({(6,10):"ONEWAY_L",(7,10):"SWITCH"},(5,10));compare(r,"THROW_R");assert r.flip
    r=fixture({(11,15):"ICE",(12,15):"ONEWAY_L",(13,15):"SWITCH"},(5,15));compare(r,"THROW_R");assert not r.flip
    r=fixture({(10,10):"PLATE",(12,10):"P_GATE",(15,10):"LASER_L"},(7,10),3);r.o[10,10]="BOX";r.fuses[10,9]=1
    compare(r,"WAIT");assert not r.active() and r.hp==100
    g=blank()
    for y in range(1,25):g[y][10]=g[y][11]="PIT"
    g[13][8]="BOX";r=Referee(g)
    proof=["MOVE_R"]*7+["MOVE_R","JUMP_R"]+["MOVE_R"]*8+["MOVE_U"]*8+["MOVE_D"]*15+["MOVE_R"]*15+["MOVE_U"]*7
    for t,a in enumerate(proof,1):
        compare(r,a)
        assert r.won==(t==len(proof))
    assert len(proof)<=e[7]["max_author_steps"] and 1.7*100+150*(240-1)/239==e[7]["cleared_max_demon_score"]
    print("8/8 published v2.2 vector groups and differential transitions passed",flush=True)

def author_check():
    import verify_v22
    verify_v22.replay_author()
    d=entry.build_dungeon();r=Referee(d["grid"])
    for i,a in enumerate(d["author_solution"],1):
        compare(r,a);assert r.hp>0 and r.won==(i==len(d["author_solution"]))
    starts=set()
    for a in ("WAIT","MOVE_L","MOVE_R","MOVE_U","MOVE_D"):
        test=Referee(d["grid"]);test.act(a);starts.add(test.p)
        for _ in range(3):test.act("WAIT")
        assert test.hp==100 and test.damage==0
    assert len(starts)==5
    print("independent author",i,r.hp,r.damage,"spawn",sorted(starts),flush=True)

def match(g,name,reset=None):
    r=Referee(g);mem={};times=[];moves=[]
    while r.hp>0 and not r.won and r.turn<=240:
        st=r.observation()
        if reset and r.turn in reset:mem={}
        t=monotonic();a=entry.decide_action(st,mem);elapsed=monotonic()-t
        assert a in VALID_ACTIONS and elapsed<(2 if r.turn==1 else .5),(name,r.turn,elapsed)
        times.append(elapsed);moves.append(a);r.act(a)
    status="CLEARED" if r.won else "DEAD" if r.hp<=0 else "TIMEOUT"
    print(name,status,len(moves),r.hp,r.keys,"ms",round(times[0]*1000),round(max(times[1:],default=0)*1000),flush=True)
    return status,moves,times

def static_check():
    src=Path("submission.py").read_text(encoding="utf-8-sig");tree=ast.parse(src)
    for n in ast.walk(tree):
        for prop in ("id","attr","name"):
            name=getattr(n,prop,"")
            assert not name.startswith("__") and name not in ("eval","exec","getattr","setattr","open","compile","globals","locals")
        if isinstance(n,ast.ImportFrom):assert n.module in ("collections","heapq","time","itertools","functools","math")
    print("submission AST passed")

if __name__=="__main__":
    maps={}
    for file in ("part1_dungeons_benchmark.json","v22_sparring_benchmarks.json"):
        maps.update({k:v["grid"] for k,v in json.loads(Path(file).read_text(encoding="utf-8-sig"))["dungeons"].items()})
    maps["new"]=entry.build_dungeon()["grid"]
    for arg in sys.argv[1:]:
        if arg=="golden":test_vectors()
        elif arg=="author":author_check()
        elif arg=="static":static_check()
        elif arg=="all":
            for name,g in maps.items():match(g,name)
        elif arg=="recover":
            for name in ("BENCH_STRONG","sol","glm"):
                match(maps[name],name+" restart",{2,9,24,73})
        else:match(maps[arg],arg)

