"""Additional offline maze/bridge test generator."""
import collections
import random
import stress_submission as t
import verify_submission as v


def maze(seed):
    rng=random.Random(seed)
    grid=v.empty_grid()
    for y in range(1,25):
        for x in range(1,39):
            grid[y][x]="W"
    start=(1,13)
    stack=[start];visited={start};grid[start[1]][start[0]]="EMPTY"
    while stack:
        x,y=stack[-1]
        options=[(x+dx*2,y+dy*2,dx,dy) for dx,dy in ((0,-1),(0,1),(-1,0),(1,0))
                 if 1<=x+dx*2<=37 and 1<=y+dy*2<=23 and (x+dx*2,y+dy*2) not in visited]
        if not options:
            stack.pop();continue
        xx,yy,dx,dy=rng.choice(options)
        grid[y+dy][x+dx]=grid[yy][xx]="EMPTY"
        visited.add((xx,yy));stack.append((xx,yy))
    # Add a few genuine cycles; the solid-wall version is a particularly
    # adversarial exploration problem with limited sight and a 240-turn cap.
    for unused in range(12):
        x,y=rng.randint(2,36),rng.randint(2,22)
        grid[y][x]="EMPTY"
    return t.landmarks(grid,(31,3),(31,21),(35,13))


def ordinary_route(grid):
    def route(a,b):
        q=collections.deque([a]);dist={a:0}
        while q:
            x,y=q.popleft()
            if (x,y)==b:return dist[(x,y)]
            for dx,dy in ((0,-1),(0,1),(-1,0),(1,0)):
                p=(x+dx,y+dy)
                if 0<=p[0]<40 and 0<=p[1]<26 and grid[p[1]][p[0]] not in ("T_W","W") and p not in dist:
                    dist[p]=dist[(x,y)]+1;q.append(p)
        return 10000
    return min(route((2,13),(31,3))+route((31,3),(31,21))+route((31,21),(35,13)),
               route((2,13),(31,21))+route((31,21),(31,3))+route((31,3),(35,13)))


if __name__=="__main__":
    found=0
    for seed in range(200):
        grid=maze(seed)
        length=ordinary_route(grid)
        if length>220:continue
        print("MAZE",seed,"known walking solution",length,flush=True)
        v.play(grid,"DFS maze "+str(seed))
        found+=1
        if found==6:break
