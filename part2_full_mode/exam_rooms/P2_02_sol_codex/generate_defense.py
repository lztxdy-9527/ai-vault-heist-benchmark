"""Generate the original exam dungeon locally, then materialize its fixed layout."""
import collections
import random
import submission as s
import verify_full as v


ROOM = [
    "##########",
    "#..p.....#",
    "#..##....#",
    "#.....#p.#",
    "#p.#.....#",
    "#..#..#..#",
    "#....p...#",
    "####.#####",
]
X, Y = 5, 4
delta=(-40,40,-1,1)
entry=(Y+7)*40+X+4
outside=entry+40
floor={((Y+y)*40+X+x) for y,row in enumerate(ROOM) for x,c in enumerate(row) if c!="#"}
plates=frozenset(((Y+y)*40+X+x) for y,row in enumerate(ROOM) for x,c in enumerate(row) if c=="p")


def paths(start,boxes):
    trail={start:None}
    queue=[start]
    for p in queue:
        for i,dx in enumerate(delta):
            q=p+dx
            if q in floor and q not in trail and q not in boxes:
                trail[q]=(p,"MOVE_"+s.LETTERS[i])
                queue.append(q)
    return trail


def generate():
    initial=(plates,min(paths(entry,plates)))
    tree={initial:None}; queue=[initial];level={initial:0}
    best=initial; best_score=-1
    for current in queue:
        boxes,p=current
        reach=paths(p,boxes)
        depth=level[current]
        if entry in reach:
            # Prefer mixed boxes away from their final plates.
            score=depth*10+3*len(boxes-plates)
            if score>best_score:
                best,best_score=current,score
        if len(queue)>38000:break
        for b in sorted(boxes):
            for i,d in enumerate(delta):
                q=b-d; earlier=q-d
                if q not in reach or earlier not in floor or earlier in boxes:continue
                previous=(boxes-{b})|{q}
                event=(previous,min(paths(earlier,previous)))
                if event not in tree:
                    tree[event]=(current,earlier,"MOVE_"+s.LETTERS[i],q)
                    level[event]=depth+1;queue.append(event)
    print("room nodes",len(queue),"pushes",level[best], "box positions",sorted(best[0]))
    route=[]
    p=entry;cur=best
    while tree[cur]:
        after,stand,act,q=tree[cur]
        trail=paths(p,cur[0]);seg=[]
        while stand!=p:
            stand,a=trail[stand];seg.append(a)
        route+=seg[::-1]+[act]
        cur=after;p=q
    trail=paths(p,cur[0]);seg=[];q=entry
    while q!=p:
        q,a=trail[q];seg.append(a)
    return best[0],route+seg[::-1]


def build():
    boxes,room_route=generate()
    g=v.empty()
    for y,row in enumerate(ROOM):
        for x,c in enumerate(row):
            g[Y+y][X+x]=dict(p="PLATE",**{"#":"T_W",".":"EMPTY"})[c]
    for p in boxes:g[p//40][p%40]="BOX"
    assert not boxes&plates
    # Two isolated key chambers, each requiring its own demolition charge.
    for y,key in ((5,"K1"),(17,"K2")):
        for x in (20,21,22):g[y-1][x]=g[y+1][x]="T_W"
        g[y][20]="W";g[y][22]=key;g[y][23]="T_W"
    g[5][21]="P_GATE"
    # Three successive jumps through a six-tile irradiated vault corridor.
    for x in range(26,39):
        g[12][x]=g[14][x]="T_W"
    g[13][26]="T_W";g[13][27]="LASER_R"
    g[12][29]="P_GATE";g[13][29]="ONEWAY_D"
    g[12][35]="LASER2_D"
    g[13][38]="T_W";g[13][37]="V"
    for x in (32,34,36):g[13][x]="PIT"
    route=["MOVE_R"]*7+["MOVE_U"]*2+room_route+["MOVE_D"]
    # Leave the room below its frame, then approach the two key pockets from the west.
    route+=["MOVE_R"]*10+["MOVE_U"]*7
    for i in range(2):
        route+=["BOMB"]+["MOVE_L"]*2+["MOVE_R"]*5+["MOVE_L"]*3
        if i==0:route+=["MOVE_D"]*12
    route+=["MOVE_U"]*6+["MOVE_R"]*10+["MOVE_D"]
    w=v.decode(g)
    for t,a in enumerate(route,1):
        w=w.step(a,t)
        assert w.hp>0,(t,a,w.p,w.hp)
    assert w.p==12*40+29 and w.keys==3 and w.active and w.stock==0,(w.p,w.keys,w.active,w.stock)
    tail=["MOVE_D","MOVE_R","MOVE_R","JUMP_R","JUMP_R","JUMP_R"]
    for wait in range(12):
        z=w
        suffix=["WAIT"]*wait+tail
        for turn,act in enumerate(suffix,len(route)+1):
            z=z.step(act,turn)
            if z.hp<=0:break
        if z.won:
            route+=suffix
            break
    d=dict(taunt="四只箱子都要归位。最后三跳，数准你还剩几拍。",grid=g,author_solution=route)
    print("length",len(route),"room",len(room_route),"finish",z.won,flush=True)
    v.certify(d)
    return d


if __name__=="__main__":
    from pathlib import Path
    import pprint
    d=build()
    codes={"T_W":"#","EMPTY":".","W":"+","PLATE":"_","BOX":"B","P_GATE":"g","ONEWAY_D":"s",
           "LASER_R":">","LASER2_D":"k","PIT":"O","K1":"1","K2":"2","V":"V"}
    rows=tuple(''.join(codes[t] for t in row) for row in d["grid"])
    out='\n\ndef build_dungeon():\n    """Four interacting pressure plates, two demolition locks, then a three-jump gauntlet."""\n'
    out+="    terrain = "+pprint.pformat({c:t for t,c in codes.items()},indent=4).replace("\n","\n    ")+"\n"
    out+="    rows = "+pprint.pformat(rows,indent=4).replace("\n","\n    ")+"\n"
    script=''.join({'MOVE_U':'U','MOVE_D':'D','MOVE_R':'R','MOVE_L':'L','JUMP_R':'j','BOMB':'b','WAIT':'.'}[a] for a in d['author_solution'])
    out+=f"    script = {script!r}\n"
    out+='    actions = dict(zip("UDLRjb.", (*MOVES, "JUMP_R", "BOMB", "WAIT")))\n'
    out+=f"    return dict(taunt={d['taunt']!r}, grid=[[terrain[c] for c in row] for row in rows],\n                author_solution=[actions[a] for a in script])\n"
    Path("defense_work.txt").write_text(out,encoding="utf-8")




