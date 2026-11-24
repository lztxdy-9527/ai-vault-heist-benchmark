"""Local supplements to the provided FULL reference boards."""
import json
import sys
import verify_full as v
import submission_overtime as s

v.s=s


def chamber(g,x,y,name,entrance):
    g[y][x]=name
    g[y][x-1]=entrance
    g[y][x+1]="T_W"
    for j in (y-1,y+1):
        g[j][x-1]=g[j][x]="T_W"


def opposite_locks():
    g=v.empty()
    chamber(g,29,5,"K1","B_GATE")
    chamber(g,28,20,"K2","R_GATE")
    chamber(g,36,12,"V","B_GATE")
    g[8][7]=g[13][25]="SWITCH"
    return g


def indirect_switch():
    g=v.empty()
    chamber(g,23,5,"K1","R_GATE")
    chamber(g,31,20,"K2","B_GATE")
    chamber(g,35,14,"V","R_GATE")
    # Entering the switch pocket from the west is forbidden. A stone or a
    # compatible reflected flight can reach it.
    g[10][12]="SWITCH"
    g[10][11]="ONEWAY_L"
    for x,y in ((12,9),(13,10),(12,11),(11,9),(11,11)):
        g[y][x]="T_W"
    return g


def box_stopper():
    g=v.empty()
    g[6][21]="K1";g[19][24]="K2"
    chamber(g,34,13,"V","P_GATE")
    for x in (9,10,11):
        g[10][x]="ICE"
    for x,y,t in ((8,10,"BOX"),(12,10,"BOX"),(11,9,"PLATE"),(12,11,"PLATE"),
                  (8,9,"T_W"),(8,11,"T_W"),(12,12,"T_W"),(12,9,"ONEWAY_D"),
                  (13,10,"PIT"),(13,11,"T_W")):
        g[y][x]=t
    return g


def put_route(w, acts, first=1):
    for turn,action in enumerate(acts,first):
        w=w.step(action,turn)
        assert w.hp>0,(turn,action,w.p)
    return w


if __name__=="__main__":
    boards={"opposite":opposite_locks(),"throw":indirect_switch(),"stopper":box_stopper()}
    for key in sys.argv[1:] or boards:
        grid=boards[key]
        v.valid(grid)
        if key=="stopper":
            start=v.decode(grid,7,10)
            path=["MOVE_R","MOVE_L","MOVE_D","MOVE_D"]+["MOVE_R"]*4+["MOVE_U","MOVE_U"]
            here=put_route(start,path)
            assert (11+9*40) in here.boxes
        w,t=v.play(key,grid,True)
