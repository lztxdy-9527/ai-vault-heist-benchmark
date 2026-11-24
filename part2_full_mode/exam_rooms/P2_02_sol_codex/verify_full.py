import ast
import collections
import json
import sys
import time
from pathlib import Path
import submission as s
from submission_template_v22 import TILE_COSTS


def empty():
    return [["T_W" if x in (0,39) or y in (0,25) else "EMPTY" for x in range(40)] for y in range(26)]


def decode(grid, x=2, y=13, hp=100):
    t=[s.EMPTY if z in ("BOX","TNT") else s.CODE[z] for row in grid for z in row]
    o=[s.BOX if z=="BOX" else s.TNT if z=="TNT" else 0 for row in grid for z in row]
    return s._World(t,o,dict(x=x,y=y,hp=hp))


def targets(grid):
    return {v:[x,y] for y,row in enumerate(grid) for x,v in enumerate(row) if v in ("K1","K2","V")}


def clue_bind(grid):
    occupied=set()
    bindings={}
    for y,row in enumerate(grid):
        for x,t in enumerate(row):
            if t!="MIMIC": continue
            p=y*40+x
            for q in s.NEIGHBORS[p]:
                if q<0 or q in occupied or grid[q//40][q%40]!="EMPTY":
                    continue
                if 1<=q%40<=3 and 12<=q//40<=14:continue
                if any(r>=0 and r!=p and grid[r//40][r%40] in ("HEAL","MIMIC") for r in s.NEIGHBORS[q]):
                    continue
                occupied.add(q);bindings[p]=q
                break
            else:raise AssertionError(("mimic clue",x,y))
    return bindings


def observe(w,t,marks,bindings):
    clues={q for p,q in bindings.items() if w.tile(p)==s.MIMIC}
    warnings=[]
    for origin in w.lasers:
        tile=w.tile(origin)
        if not s._laser(tile):continue
        period=4 if tile>=s.L2U else 3
        if t%period:continue
        d=tile-(s.L2U if period==4 else s.LU)
        p=origin
        for i in range(10):
            p=s.NEIGHBORS[p][d]
            if w.high(p) or w.occ(p):break
            warnings.append(dict(x=p%40,y=p//40,dir=s.LETTERS[d],period=period,cannon=[origin%40,origin//40]))
    warnings.sort(key=lambda z:(z["y"],z["x"],z["dir"],z["period"],z["cannon"]))
    def terrain(p):
        t=w.tile(p)
        return "CHEST" if t in (s.HEAL,s.MIMIC) else s.NAMES[t]
    return dict(turn=t,turns_left=241-t,mode="FULL",
                hero=dict(x=w.p%40,y=w.p//40,hp=w.hp,keys=[bool(w.keys&1),bool(w.keys&2)],
                          jumps=w.jumps,throws=w.throws,bombs=w.stock),
                targets=marks,gates_flipped=w.flipped,plates_active=w.active,
                terrain=[[terrain(y*40+x) for x in range(40)] for y in range(26)],
                occupant=[[(None,"BOX","TNT")[w.occ(y*40+x)] for x in range(40)] for y in range(26)],
                clues=[[y*40+x in clues for x in range(40)] for y in range(26)],
                visible_mask=[[True]*40 for _ in range(26)],laser_warnings=warnings,
                bombs=[dict(x=p%40,y=p//40,timer=timer) for p,timer in w.bombs])


def valid(grid):
    assert len(grid)==26 and all(len(row)==40 for row in grid)
    assert all(grid[y][x]=="T_W" for y in range(26) for x in range(40) if y in (0,25) or x in (0,39))
    assert all(grid[y][x]=="EMPTY" for y in range(12,15) for x in range(1,4))
    c=collections.Counter(grid[y][x] for y in range(1,25) for x in range(1,39))
    for tile in ("K1","K2","V"):assert c[tile]==1
    m=targets(grid)
    assert 12<=m["K1"][0]<=34 and 2<=m["K1"][1]<=10
    assert 12<=m["K2"][0]<=34 and 15<=m["K2"][1]<=23
    assert 33<=m["V"][0]<=37 and 4<=m["V"][1]<=21
    assert sum(abs(a-b) for a,b in zip(m["K1"],m["K2"]))>=12
    for tile,cap in dict(T_W=120,CRACK=40,SWITCH=6,PLATE=4,P_GATE=8,BOX=6,TNT=12,HEAL=4,MIMIC=4).items():
        assert c[tile]<=cap,(tile,c[tile])
    for prefixes,cap in ((("MIRROR_",),30),(("SPRING_",),20),(("LASER_","LASER2_"),12),(("ONEWAY_",),12),(("R_GATE","B_GATE"),16)):
        assert sum(n for tile,n in c.items() if tile.startswith(prefixes))<=cap
    if c["P_GATE"]:assert 1<=c["PLATE"]<=c["BOX"]
    for i in (1,2):assert c[f"PORTAL_{i}A"]==c[f"PORTAL_{i}B"]<=1
    cost=sum(TILE_COSTS[k]*n for k,n in c.items())
    assert cost<=3000,cost
    clue_bind(grid)
    return cost


def spawn_check(w):
    by_spot={}
    def survive(v,n):
        if v.hp<=0 or v.trap_damage:return None
        if n==5:return []
        for a in ("WAIT",*s.MOVES,*s.JUMPS,*s.THROWS,"BOMB"):
            v2=v.step(a,n)
            path=survive(v2,n+1)
            if path is not None:return [a]+path
        return None
    for a in s.ALL_ACTIONS:
        n=w.step(a,1)
        if n.p in by_spot:continue
        rest=survive(n,2)
        if rest is not None:by_spot[n.p]=[a]+rest
    assert len(by_spot)>=2,by_spot
    return by_spot


def certify(d):
    g=d["grid"];cost=valid(g)
    acts=d["author_solution"]
    assert 1<=len(acts)<=200 and len(d["taunt"])<=40
    w=decode(g)
    witnesses=spawn_check(w)
    for turn,a in enumerate(acts,1):
        assert a in s.ALL_ACTIONS
        before=w
        w=w.step(a,turn)
        assert w.hp>0,(turn,a,(w.p%40,w.p//40),w.hp,sorted(w.boxes))
        assert w.won==(turn==len(acts)),(turn,a,(w.p%40,w.p//40),w.keys,w.won)
    print("CERTIFIED",cost,len(acts),w.hp,"spawn endpoints",len(witnesses),flush=True)
    return w


def fixtures():
    g=empty()
    d=json.loads(Path("golden_vectors_v22.json").read_text(encoding="utf-8"))
    for row in d["vectors"][0]["placed_inner_tiles"]:
        g[row["y"]][row["x"]]=row["tile"]
    assert valid(g)==225 and not decode(g).active
    g=empty();g[13][5]="PLATE";g[13][34]="P_GATE";g[13][7]="BOX"
    assert not decode(g,4,13).step("MOVE_R",1).active
    w=decode(g,8,13).step("MOVE_L",1).step("MOVE_L",2)
    assert w.active and not w.high(13*40+34)
    g=empty();g[8][15]="LASER_D";g[10][12]="LASER2_R"
    w=decode(g,15,10)
    assert {p["period"] for p in observe(w,12,{}, {})["laser_warnings"] if (p["x"],p["y"])==(15,10)}=={3,4}
    assert w.step("WAIT",12).hp==0 and w.step("WAIT",3).hp==50 and w.step("WAIT",4).hp==50
    g=empty();g[13][5]="CRACK";g[13][6]="ONEWAY_L";w=decode(g,5,13);w.set_occ(13*40+6,s.BOX)
    a=w.step("MOVE_R",1);assert a.p==w.p and a.boxes==w.boxes and a.tile(w.p)==s.CRACK
    g=empty();g[10][10]="MIRROR_NE";g[9][10]="ONEWAY_R"
    assert decode(g,9,10).step("MOVE_R",1).p==10*40+10
    g=empty();g[10][10]="SPRING_R";g[10][12]="ONEWAY_L";g[14][6]="ONEWAY_L"
    assert decode(g,9,10).step("MOVE_R",1).p==10*40+11
    w=decode(g,5,14);a=w.step("JUMP_R",1);assert a.p==w.p and a.jumps==2
    g=empty();g[10][6]="ONEWAY_L";g[10][7]="SWITCH";g[15][11]="ICE";g[15][12]="ONEWAY_L";g[15][13]="SWITCH"
    assert decode(g,5,10).step("THROW_R",1).flipped
    assert not decode(g,5,15).step("THROW_R",1).flipped
    g=empty();g[10][10]="PLATE";g[10][12]="P_GATE";g[10][15]="LASER_L"
    w=decode(g,7,10);w.set_occ(410,s.BOX);w.bombs=((410,1),)
    assert w.active
    a=w.step("WAIT",3);assert not a.active and a.hp==100 and a.tile(410)==s.PLATE
    g=empty();g[13][8]="BOX";g[13][10]=g[13][11]="PIT"
    w=decode(g,7,13).step("MOVE_R",1).step("MOVE_R",2).step("MOVE_R",3)
    assert w.tile(13*40+10)==s.EMPTY
    w=w.step("JUMP_R",4)
    assert w.p==13*40+12 and w.hp==100
    assert 1.7*100+150*(240-1)/239==320.0
    # Portal exit applies pre-teleport direction to a one-way tile.
    g=empty();g[13][5]="PORTAL_1A";g[8][10]="PORTAL_1B";g[8][11]="ONEWAY_L"
    assert decode(g,4,13).step("MOVE_R",1).p==8*40+10
    print("8 golden vectors and additional one-way/phase checks pass",flush=True)


def regress_old():
    pack=json.loads(Path("part1_dungeons_benchmark.json").read_text(encoding="utf-8"))
    for m in pack["my_hero_matches"]+pack["my_demon_defense_matches"]:
        k=m.get("demon_id","sol");w=decode(pack["dungeons"][k]["grid"])
        for turn,a in enumerate(m["actions"],1):
            w=w.step(a,turn)
            if [w.p%40,w.p//40]!=m["positions"][turn] or w.hp!=m["hp_trace"][turn]:
                if "接口" not in str(m.get("milestone_events",[])):
                    print("TRACE DIFFERENCE",k,m.get("hero_id"),turn,a,[w.p%40,w.p//40],w.hp,m["positions"][turn],m["hp_trace"][turn],flush=True)
                break
        else:print("TRACE MATCH",k,m.get("hero_id","sol"),len(m["actions"]),flush=True)


def play(name,grid,verbose=False,limit=240,reset=0):
    w=decode(grid);m={};marks=targets(grid);bindings=clue_bind(grid)
    times=[];last=(w.keys,len(w.boxes),w.active)
    for t in range(1,limit+1):
        if t==reset:m={}
        obs=observe(w,t,marks,bindings)
        now=time.monotonic();a=s.decide_action(obs,m);dt=time.monotonic()-now
        times.append(dt)
        assert a in s.ALL_ACTIONS and dt<(2 if t==1 else .5),(t,dt)
        w=w.step(a,t)
        if verbose and (verbose==2 or t%10==0 or (w.keys,len(w.boxes),w.active)!=last):
            print(t,a,(w.p%40,w.p//40),w.hp,w.keys,w.jumps,w.stock,sorted(w.boxes),m.get("kind"),m.get("complete"),len(m.get("plan",[])),m.get("nodes"),flush=True)
        last=(w.keys,len(w.boxes),w.active)
        if w.won or w.hp<=0:break
    print(name,"CLEAR" if w.won else "DEAD" if w.hp<=0 else "TIMEOUT",t,"HP",w.hp,"keys",w.keys,
          "first_ms",round(times[0]*1000),"later_max_ms",round(max(times[1:],default=0)*1000),flush=True)
    return w,t


if __name__=="__main__":
    fixtures()
    a=json.loads(Path("part1_dungeons_benchmark.json").read_text(encoding="utf-8"))
    b=json.loads(Path("v22_sparring_benchmarks.json").read_text(encoding="utf-8"))
    maps=a["dungeons"]|b["dungeons"]
    for key in sys.argv[1:] or maps:
        if key=="traces":regress_old()
        elif key=="self":
            d=s.build_dungeon();certify(d);play(key,d["grid"],True)
        else:play(key,maps[key]["grid"],key=="BENCH_STRONG")


