"""Additional rule-derived edge cases beyond the eight supplied vectors."""
import copy
import json
import math
import submission as s
import verify_submission as v
import stress_submission as t


def run():
    checks=0
    def check(ok,label):
        nonlocal checks
        assert ok,label
        checks+=1

    # A closed door under an entity does not prevent it from leaving.
    g=v.empty_grid();g[13][2]="B_GATE"
    w=v.decode(g);w.flipped=True
    a=w.step("MOVE_R",1)
    check(a.p==13*40+3,"leave closed door")
    g[13][3]="R_GATE";w=v.decode(g)
    a=w.step("JUMP_R",1)
    check(a.p==w.p and a.jumps==2,"blocked jump still consumes inventory")

    # A jumping hero is not exposed at an intermediate airborne cell.
    g=v.empty_grid();g[5][6]="LASER_D"
    h=dict(x=5,y=10,hp=100,keys=[False,False],jumps=3,throws=3,bombs=2)
    w=v.decode(g,h)
    check(w.step("JUMP_R",3).hp==100,"airborne laser bypass")
    check(w.step("MOVE_R",3).hp==50,"ordinary laser crossing")
    for x in (6,7):g[10][x]="ICE"
    w=v.decode(g,h);a=w.step("MOVE_R",3)
    check(a.p==10*40+8 and a.hp==50,"earlier exposed landing remains vulnerable")

    # A planted bomb ticks once, and a win on its detonation turn preempts it.
    g=v.empty_grid();w=v.decode(g)
    a=w.step("BOMB",1)
    check(a.bombs==((w.p,2),),"new bomb timer 2 after planting")
    a=a.step("WAIT",2)
    check(a.bombs==((w.p,1),),"bomb timer 1 next turn")
    a=a.step("WAIT",3)
    check(a.hp==50 and not a.bombs,"bomb third-turn self damage")
    g[13][3]="V";h=dict(x=2,y=13,hp=20,keys=[True,True],jumps=0,throws=0,bombs=0)
    w=v.decode(g,h);w.bombs=((w.p,1),)
    a=w.step("MOVE_R",240)
    check(a.won and a.hp==20 and a.bombs[0][1]==1,"instant win preempts explosion")

    # Effective trap damage is apportioned between TNT and self bombs.
    g=v.empty_grid();g[10][6]="TNT";g[11][6]="TNT"
    h=dict(x=5,y=10,hp=100,keys=[False,False],jumps=3,throws=3,bombs=0)
    w=v.decode(g,h);w.bombs=((w.p,2),)
    a=w.step("THROW_R",1)
    check(a.hp==-70 and math.isclose(a.trap_damage,12000/170),"mixed chain damage attribution")
    g=v.empty_grid();g[10][5]="CRACK";g[10][6]="TNT"
    w=v.decode(g,h);a=w.step("THROW_R",1)
    check(a.hp==-60 and a.trap_damage==100 and a.tile(w.p)==s.PIT,"exploded bridge support check")

    # Titanium is itself immune but does not shield blast diagonals.
    g=v.empty_grid();g[10][6]="T_W";g[11][6]="TNT"
    w=v.decode(g,h);w.armed.add(11*40+6)
    w.explode({(11*40+6,-1)})
    check(w.hp==40 and w.tile(10*40+6)==s.TITANIUM,"titanium diagonal blast")

    # All sixteen documented mirror entries.
    table={"MIRROR_NE":"RRUU","MIRROR_SE":"RRDD",
           "MIRROR_SW":"LLDD","MIRROR_NW":"LLUU"}
    for mirror,outgoing in table.items():
        for incoming in range(4):
            g=v.empty_grid();g[10][10]=mirror
            dx,dy=s.DIRS[incoming]
            hh=dict(x=10-dx,y=10-dy,hp=100,keys=[False,False],jumps=3,throws=3,bombs=2)
            a=v.decode(g,hh).step("MOVE_"+s.LETTERS[incoming],1)
            od=s.LETTERS.index(outgoing[incoming]);ox,oy=s.DIRS[od]
            check(a.p==(10+oy)*40+10+ox,"mirror "+mirror+str(incoming))

    # Caller state is immutable, and persistent memory survives a JSON round trip.
    g=t.landmarks(v.empty_grid());w=v.decode(g)
    targets={z:[x,y] for y in range(26) for x in range(40)
             if (z:=g[y][x]) in ("K1","K2","V")}
    state=v.observation(w,1,targets,{})
    saved=copy.deepcopy(state);memory={}
    action=s.decide_action(state,memory)
    check(state==saved,"input state is not mutated")
    memory=json.loads(json.dumps(memory))
    w=w.step(action,1)
    action=s.decide_action(v.observation(w,2,targets,{}),memory)
    check(action in s.ALL_ACTIONS,"JSON memory round trip")

    # An uncertain chest is not declared safe until all its clue neighbors are known.
    g=t.landmarks(v.empty_grid());g[13][5]="MIMIC"
    clues=v.bind_clues(g);w=v.decode(g)
    st=v.observation(w,1,targets,clues);m={}
    root,unused=s._observe(st,m)
    check(root.tile(13*40+5)==s.MIMIC,"visible skeleton identifies mimic")
    g[13][5]="HEAL";w=v.decode(g)
    st=v.observation(w,1,targets,{});m={}
    root,unused=s._observe(st,m)
    check(root.tile(13*40+5) in (s.CHEST,s.HEAL),"no invented mimic clue")

    # One known collinear cannon must not suppress an unseen second cannon.
    g=t.landmarks(v.empty_grid(),(12,3),(30,20))
    g[13][10]=g[13][20]="LASER_L"
    hh=dict(x=12,y=14,hp=50,keys=[False,False],jumps=0,throws=0,bombs=0)
    w=v.decode(g,hh)
    tt={"K1":[12,3],"K2":[30,20],"V":[35,13]}
    state=v.observation(w,3,tt,{})
    root,unused=s._observe(state,{})
    check(13*40+10 in root.lasers and 13*40+20 not in root.lasers,"collinear test visibility")
    check(bool(root.extra_emitters),"unseen collinear cannon retained")
    check(root.step("MOVE_U",3).hp<=0,"unseen collinear ray damages hero")
    m={};action=s.decide_action(state,m)
    check(w.step(action,3).hp>0,"avoid unseen collinear ray")

    # Gates are evaluated after the action, including inferred remote beams.
    g[13][12]="SWITCH";g[13][15]="B_GATE"
    w=v.decode(g,hh);state=v.observation(w,3,tt,{})
    root,unused=s._observe(state,{})
    a=root.step("MOVE_U",3)
    check(a.hp==50 and a.flipped,"closing gate cuts inferred beam immediately")

    # A movable box can separate a remembered cannon from a new hidden one.
    g=t.landmarks(v.empty_grid(),(12,3),(30,20))
    g[13][14]=g[13][20]="LASER_L";g[13][17]="BOX"
    hh=dict(x=20,y=14,hp=50,keys=[False,False],jumps=0,throws=0,bombs=0)
    memory={};w=v.decode(g,hh)
    s._observe(v.observation(w,1,tt,{}),memory)
    hh["x"]=10;w=v.decode(g,hh)
    root,unused=s._observe(v.observation(w,3,tt,{}),memory)
    check(root.step("MOVE_U",3).hp<=0,"box-separated unknown cannon retained")

    # Possible remote TNT damage never creates a fictional cleared corridor.
    g=t.landmarks(v.empty_grid());g[13][11]="TNT";g[12][11]="W"
    hh=dict(x=10,y=13,hp=100,keys=[False,False],jumps=0,throws=0,bombs=0)
    w=v.decode(g,hh);w.extra_emitters=((2,(13*40+18,)),)
    a=w.step("WAIT",3)
    check(a.hp==40 and a.occ(13*40+11)==s.TNT and a.tile(12*40+11)==s.WALL,
          "uncertain TNT uses damage bound without invented destruction")

    # The final action prioritizes immediate completion before laser settlement.
    g=t.landmarks(v.empty_grid());g[5][35]="LASER_D"
    hh=dict(x=34,y=13,hp=20,keys=[True,True],jumps=0,throws=0,bombs=0)
    w=v.decode(g,hh);state=v.observation(w,240,targets,{})
    action=s.decide_action(state,{})
    check(w.step(action,240).won,"last-turn immediate clear")

    # A fully explored map has no frontier; long backtracking must not create
    # an artificial goal at the current square and force a two-step loop.
    g=t.landmarks(v.empty_grid());g[5][20]=g[20][20]="EMPTY"
    hh=dict(x=2,y=13,hp=100,keys=[True,True],jumps=3,throws=3,bombs=2)
    w=v.decode(g,hh);state=v.observation(w,1,targets,{})
    state["visible_mask"]=[[True]*40 for unused in range(26)]
    state["terrain"]=g
    memory={};s._observe(state,memory)
    memory["stale"]=25;memory["visits"][w.p]=5
    action=s.decide_action(v.observation(w,100,targets,{}),memory)
    check(action=="MOVE_R","known-map backtracking retains real objective")

    # A plain-ground jump can be essential to escape a bomb's final tick.
    g=t.landmarks(v.empty_grid());hh=dict(x=5,y=5,hp=50,keys=[False,False],jumps=3,throws=0,bombs=0)
    w=v.decode(g,hh);w.bombs=((w.p,1),)
    state=v.observation(w,10,targets,{})
    action=s.decide_action(state,{})
    check(action.startswith("JUMP_") and w.step(action,10).hp>0,"jump out of imminent bomb")

    # Leave a firing lane before its next firing turn: walking one square is
    # too slow, even though the middle and landing are ordinary empty ground.
    g=t.landmarks(v.empty_grid());g[5][5]="LASER_D"
    for yy in range(10,16):
        g[yy][4]=g[yy][6]="T_W"
    hh=dict(x=5,y=14,hp=50,keys=[True,True],jumps=3,throws=0,bombs=0)
    w=v.decode(g,hh);state=v.observation(w,2,targets,{})
    state["visible_mask"]=[[True]*40 for unused in range(26)];state["terrain"]=g
    action=s.decide_action(state,{})
    check(action=="JUMP_D","escape beam before firing turn")

    # build_dungeon returns independent fresh structures.
    a=s.build_dungeon();b=s.build_dungeon()
    a["grid"][13][4]="EMPTY"
    check(b["grid"][13][4]=="PORTAL_1A","fresh dungeon structure")
    print("PASS",checks,"additional physics/interface checks",flush=True)


if __name__=="__main__":
    run()
