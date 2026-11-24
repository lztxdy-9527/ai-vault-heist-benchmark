"""Adversarial FULL compositions and witnessed legal solutions."""
import collections
import json
import random
import sys
import verify_full as v
import submission_overtime as s
from overtime_cases import chamber

v.s=s


class Witness:
    def __init__(self, grid):
        self.grid=grid
        self.w=v.decode(grid)
        self.actions=[]

    def act(self, *actions):
        for action in actions:
            self.actions.append(action)
            self.w=self.w.step(action,len(self.actions))
            assert self.w.hp>0,(len(self.actions),action,self.w.p)
        return self

    def walk(self, x, y):
        goal=max(0,y)*40+x
        w=self.w
        start=(w.p,(len(self.actions)+1)%w.period)
        queue=collections.deque([(start,w,0)])
        prev={start:None}
        while queue:
            seen,a,k=queue.popleft()
            if a.p==goal:
                path=[]
                while prev[seen]:
                    seen,action=prev[seen]
                    path.append(action)
                return self.act(*reversed(path))
            tick=len(self.actions)+1+k
            for action in (*s.MOVES,"WAIT"):
                b=a.step(action,tick)
                if b.hp<w.hp or b.boxes!=w.boxes or b.flipped!=w.flipped:
                    continue
                if (b.signature!=w.signature and b.p!=goal) or (b.won and b.p!=goal):
                    continue
                new=(b.p,(tick+1)%w.period)
                if new not in prev:
                    prev[new]=(seen,action)
                    queue.append((new,b,k+1))
        raise AssertionError((w.p,goal,"witness walk"))

    def cert(self):
        assert self.w.won and self.w.keys==3
        d=dict(grid=self.grid,taunt="完整路线可回放。",author_solution=self.actions)
        v.certify(d)
        return self.grid


def bridge_boxes():
    g=v.empty()
    chamber(g,15,5,"K1","P_GATE")
    g[20][22]="K2"
    for x,y in ((7,9),(15,9),(7,17),(15,17)):
        g[y][x]="BOX"
        g[y][x+2]="PLATE"
    for x in range(28,39):
        g[12][x]=g[14][x]="T_W"
    g[12][29]="EMPTY"
    g[13][38]="T_W"
    g[13][28]="BOX"
    g[13][30]="BOX"
    g[13][32]=g[13][33]=g[13][34]="PIT"
    g[13][35]="ONEWAY_R"
    g[13][37]="V"
    w=Witness(g)
    for x,y in ((7,9),(15,9),(15,17),(7,17)):
        w.walk(x-1,y).act("MOVE_R","MOVE_R")
    assert w.w.active
    w.walk(15,5).walk(22,20).walk(29,13).act("MOVE_R","MOVE_R")
    assert w.w.tile(13*40+32)==s.EMPTY
    w.walk(27,13).act(*(["MOVE_R"]*5),"MOVE_R","JUMP_R","MOVE_R","MOVE_R")
    return w.cert()


def powered_explosion():
    g=v.empty()
    chamber(g,22,6,"K1","W")
    chamber(g,20,19,"K2","W")
    chamber(g,36,13,"V","W")
    g[6][20]="TNT"
    g[6][19]="LASER_R"
    g[3][20]="LASER2_D"
    w=Witness(g)
    w.act("WAIT","WAIT","WAIT")
    # The blast destroys the red source; the blue ray remains active.
    w.walk(22,6)
    for x,y in ((18,19),(34,13)):
        w.walk(x,y).act("BOMB","MOVE_L","MOVE_L")
        w.walk(x+2,y)
    return w.cert()


def rearm_plate_after_blast():
    g=v.empty()
    chamber(g,16,9,"K1","W")
    chamber(g,22,19,"K2","W")
    chamber(g,36,13,"V","W")
    g[12][34]=g[14][34]="T_W"
    g[13][34]="P_GATE"
    for x,y,t in ((9,10,"BOX"),(11,10,"BOX"),(13,10,"PLATE"),
                  (12,11,"LASER2_R"),(13,11,"P_GATE"),(14,11,"TNT"),(13,12,"TNT")):
        g[y-2][x]=t
    w=Witness(g)
    w.walk(10,8).act("MOVE_R","MOVE_R")
    for unused in range(4):
        if not w.w.occ(9*40+14):
            break
        w.act("WAIT")
    assert not w.w.active and not w.w.occ(9*40+14)
    w.walk(8,8).act(*(["MOVE_R"]*4))
    assert w.w.active
    w.walk(16,9)
    for x,y in ((20,19),(34,13)):
        w.walk(x,y).act("BOMB","MOVE_L","MOVE_L")
        w.walk(x+2,y)
    return w.cert()


def directional_trap(seed):
    rng=random.Random(seed)
    g=v.empty()
    for x in (12,25):
        for y in range(1,25):
            g[y][x]="T_W"
        g[13][x]="ONEWAY_R"
    g[13][8]="PORTAL_1A"
    g[19][31]="PORTAL_1B"
    g[19][32]="ONEWAY_R"
    g[19][30]=g[18][31]=g[20][31]="T_W"
    first=(rng.randint(14,20),rng.randint(3,7))
    second=(rng.choice((27,28,29,33)),rng.randint(18,22))
    vault=(rng.randint(34,37),rng.randint(5,14))
    for z,(x,y) in zip(("K1","K2","V"),(first,second,vault)):
        g[y][x]=z
    # Lasers, springs, and cliffs each stress the path geometry without
    # changing the directional boundary's irreversible portal shortcut.
    for unused in range(30):
        x,y=rng.randrange(1,39),rng.randrange(1,25)
        if (g[y][x]=="EMPTY" and not (x<=3 and 12<=y<=14) and
                (x,y) not in {(8,12),(9,12),(11,13),(13,13),(24,13),(26,13)}):
            g[y][x]=rng.choice(("W","PIT","CRACK","ICE","SPRING_D","LASER2_R"))
    w=Witness(g)
    w.walk(8,12).walk(9,12).walk(*first).walk(*second).walk(*vault)
    return w.cert()


if __name__=="__main__":
    keys=sys.argv[1:] or ["bridge","fuse","loss-order"]
    for key in keys:
        if key=="bridge": g=bridge_boxes()
        elif key=="fuse": g=powered_explosion()
        elif key=="loss-order": g=directional_trap(208836)
        elif key=="rearm": g=rearm_plate_after_blast()
        else: g=directional_trap(int(key))
        w,_=v.play("adversarial "+key,g,True)
        assert w.won,key
