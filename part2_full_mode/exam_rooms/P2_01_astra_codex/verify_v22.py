"""Room-local replay and fixtures. Run with python -B."""
import json
from collections import deque, Counter
from pathlib import Path
import sys
from time import monotonic
import submission as game
from submission import D, ACTIONS, State, Arena, Turn, FLOOR, BOX, TNT, MASK, ID, K1, K2, V, PG, PLATE, PIT

def initial(g):
    board=[]
    for row in g:
        for t in row:
            board.append(BOX if t=="BOX" else TNT if t=="TNT" else ID[t])
    targets=tuple(board.index(t) for t in (K1,K2,V))
    return Arena().prepare(board,targets),State(522,100,0,0,3,3,2,(),())

def fields(w,s):
    b=w.base[:]
    for p,c in s.edits:b[p]=c
    return b

def obs(w,s,t):
    b=fields(w,s)
    marks=set()
    chests={p for p,c in enumerate(w.base) if c in (game.HEAL,game.MIMIC)}
    for p,c in enumerate(w.base):
        if c!=game.MIMIC:continue
        clue=next(q for q in (p+d for d in D) if w.base[q]==FLOOR and not(1<=q%40<=3 and 12<=q//40<=14) and all(q+d==p or q+d not in chests for d in D) and q not in marks)
        if b[p]&MASK==game.MIMIC:marks.add(clue)
    terrain=[["CHEST" if c&MASK in (game.MIMIC,game.HEAL) else game.NAMES[c&MASK] for c in b[i:i+40]] for i in range(0,1040,40)]
    occ=[[None if c<BOX else "BOX" if c<TNT else "TNT" for c in b[i:i+40]] for i in range(0,1040,40)]
    active=bool(w.plates) and all(BOX<=b[p]<TNT for p in w.plates)
    rays,_=w.rays(s.edits,s.flip,active,t)
    warns=[dict(x=p%40,y=p//40,dir=game.LETTERS[d],period=period,cannon=[gun%40,gun//40]) for p,mask in rays.items() for i,(gun,d,period) in enumerate(w.guns) if mask&(1<<i)]
    return dict(mode="FULL",turn=t,turns_left=241-t,hero=dict(x=s.p%40,y=s.p//40,hp=s.hp,keys=[bool(s.keys&1),bool(s.keys&2)],jumps=s.jumps,bombs=s.bombs,throws=s.stones),
                gates_flipped=bool(s.flip),plates_active=active,terrain=terrain,occupant=occ,visible_mask=[[True]*40 for _ in range(26)],
                clues=[[i+j in marks for j in range(40)] for i in range(0,1040,40)],bombs=[dict(x=p%40,y=p//40,timer=t) for p,t in s.fuses],laser_warnings=warns,
                targets={k:[p%40,p//40] for k,p in zip(("K1","K2","V"),w.targets)})

def make_proof():
    w,s=initial(game.dungeon_grid())
    actions=[]
    def act(a):
        nonlocal s
        out=game.step(w,s,a,len(actions)+1,False)
        assert out.state.hp>0,(s,a,len(actions))
        s=out.state;actions.append(a)
    def walk(x,y,*,safe=True,jump=False):
        target=y*40+x;t=len(actions)+1
        Q=deque([(s,())]);seen={(s.p,t%12,s.jumps)}
        while Q:
            cur,path=Q.popleft()
            if cur.p==target:
                for a in path:act(a)
                return
            for a in ((0,1,2,3,4,5,6,7,12) if jump else (0,1,2,3,12)):
                q=cur.p+D[a%4]
                b=dict(cur.edits)
                if a<4 and b.get(q,w.base[q])>=BOX:continue
                res=game.step(w,cur,a,t+len(path))
                if not res or res.state.hp<=0 or (safe and res.state.hp<cur.hp):continue
                n=res.state
                key=(n.p,(t+len(path)+1)%12,n.jumps,n.fuses,n.hp)
                if key in seen:continue
                seen.add(key);Q.append((n,path+(a,)))
        raise ValueError(('walk',x,y,s,len(actions)))
    # Take the rail cannon off line without disturbing the six crates.
    walk(11,5);act(13);walk(11,3)
    for y in (8,5,3,10):
        dy=1 if y<6 else -1
        walk(4,y-dy)
        for _ in range(abs(6-y)):act(1 if dy==1 else 0)
        walk(3,6)
        length={8:2,5:3,3:6,10:5}[y]
        for _ in range(length):act(3)
    walk(3,17);act(3);walk(6,17);act(3)
    walk(3,22);act(3)
    assert Turn().start(w,s).active
    walk(11,13);walk(18,11,safe=False,jump=True)
    walk(26,4,safe=False)
    walk(29,21,safe=False)
    act(10)
    walk(26,20,safe=False)
    walk(35,13,safe=False)
    print('proof',len(actions),s.hp,''.join("udlrUDLRhjkn.z"[a] for a in actions))
    return actions


def run(g,label):
    w,s=initial(g)
    mem={};times=[];trace=[]
    for t in range(1,241):
        st=obs(w,s,t);s0=monotonic()
        a=game.decide_action(st,mem)
        times.append(monotonic()-s0)
        assert a in ACTIONS and times[-1]<(2 if t==1 else .5),(label,t,a,times[-1])
        out=game.step(w,s,ACTIONS.index(a),t,False)
        trace.append((t,s.p%40,s.p//40,a,s.hp,s.keys,s.bombs,s.jumps,len(mem.get("route",()))))
        s=out.state
        if s.hp<=0 or out.won:break
    status="CLEARED" if out.won else "DEAD" if s.hp<=0 else "TIMEOUT"
    print(label,status,t,s.hp,s.keys,"first",round(times[0],3),"later",round(max(times[1:],default=0),3),flush=True)
    return status,trace

def replay_author():
    doc=game.build_dungeon();g=doc["grid"];route=doc["author_solution"]
    assert len(g)==26 and all(len(r)==40 for r in g) and len(doc["taunt"])<=40 and 1<=len(route)<=200
    for y in range(26):
        for x in range(40):
            if x in (0,39) or y in (0,25):assert g[y][x]=="T_W"
            if 1<=x<=3 and 12<=y<=14:assert g[y][x]=="EMPTY"
    costmod=__import__("submission_template_v22")
    ct=Counter(cell for row in g[1:-1] for cell in row[1:-1])
    cost=sum(costmod.TILE_COSTS[t]*n for t,n in ct.items())
    assert cost<=3000 and 1<=ct["PLATE"]<=ct["BOX"]<=6 and ct["P_GATE"]<=8 and ct["PLATE"]<=4 and ct["T_W"]<=120
    for t,n in [("LASER",12),("ONEWAY",12),("MIRROR",30),("SPRING",20)]:assert sum(c for k,c in ct.items() if k.startswith(t))<=n
    for k,(xmin,xmax,ymin,ymax) in zip(("K1","K2","V"),((12,34,2,10),(12,34,15,23),(33,37,4,21))):
        assert ct[k]==1 and any(g[y][x]==k for x in range(xmin,xmax+1) for y in range(ymin,ymax+1))
    w,s=initial(g)
    assert game.dist(w.targets[0],w.targets[1])>=12
    for a in (0,1,2,3,12):
        witness=s
        for t,ac in enumerate((a,12,12,12),1):
            witness=game.step(w,witness,ac,t,False).state
            assert witness.hp==100
    for t,a in enumerate(route,1):
        out=game.step(w,s,ACTIONS.index(a),t,False)
        s=out.state
        assert s.hp>0 and out.won==(t==len(route)),(t,a,s)
    print("author",cost,len(route),s.hp,"five distinct safe starts",flush=True)
def main():
    maps={}
    for file in ("part1_dungeons_benchmark.json","v22_sparring_benchmarks.json"):
        maps.update({k:v["grid"] for k,v in json.loads(Path(file).read_text(encoding="utf-8-sig"))["dungeons"].items()})
    maps["new"]=game.build_dungeon()["grid"]
    for k in sys.argv[1:]:
        if k=="author":replay_author();continue
        if k=="proof":make_proof();continue
        if k=="all":
            for name,g in maps.items():run(g,name)
        elif k.startswith("trace="):
            name=k[6:];res,trace=run(maps[name],name);print(trace)
        else:run(maps[k],k)
if __name__=="__main__":main()

