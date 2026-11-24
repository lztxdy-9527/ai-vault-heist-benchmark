"""Synthetic offline navigation regression suite (development only)."""
import collections
import random
import verify_submission as v


def landmarks(grid, k1=(20,5), k2=(20,20), vault=(35,13)):
    for tile,(x,y) in zip(("K1","K2","V"),(k1,k2,vault)):
        grid[y][x]=tile
    for y in range(12,15):
        for x in range(1,4):
            grid[y][x]="EMPTY"
    return grid


def maps():
    grid=landmarks(v.empty_grid(),(15,5),(25,20))
    for x in (10,20,30):
        for y in range(1,25):
            grid[y][x]="PIT"
    yield "three mandatory jumps",grid

    grid=landmarks(v.empty_grid(),(18,5),(26,20))
    for x in (10,11):
        for y in range(1,25):
            grid[y][x]="PIT"
    grid[13][9]="SPRING_R"
    yield "two-wide abyss spring crossing",grid

    grid=landmarks(v.empty_grid(),(15,5),(25,20))
    for y in (4,6):
        for x in range(14,17):
            grid[y][x]="W"
    grid[5][14]=grid[5][16]="W"
    yield "bomb opens key chamber",grid

    grid=landmarks(v.empty_grid(),(15,5),(25,20))
    for y in (4,6):
        for x in range(14,17):
            grid[y][x]="T_W"
    grid[5][14]="R_GATE";grid[5][16]="T_W"
    grid[8][12]="SWITCH"
    yield "switch opens key chamber",grid

    grid=landmarks(v.empty_grid(),(15,5),(25,20))
    for y in (4,6):
        for x in range(14,17):
            grid[y][x]="T_W"
    grid[5][14]="R_GATE";grid[5][16]="T_W"
    grid[8][12]="SWITCH"
    for x,y in ((11,8),(13,8),(12,7),(12,9)):
        grid[y][x]="PIT"
    yield "throw to remote switch",grid

    grid=landmarks(v.empty_grid(),(25,5),(30,20))
    for x in range(4,22):
        grid[13][x]="ICE"
    grid[13][22]="MIRROR_NE"
    for y in range(6,13):
        grid[y][22]="ICE"
    grid[5][22]="SPRING_R"
    yield "ice mirror and spring shortcut",grid

    grid=landmarks(v.empty_grid(),(18,5),(26,20))
    for x in (10,16,22,28):
        grid[2][x]="LASER_D"
        grid[23][x+1]="LASER_U"
    for x,y in ((9,13),(15,13),(21,13),(27,13)):
        grid[y][x]="TNT"
    yield "crossing lasers and TNT",grid

    grid=landmarks(v.empty_grid(),(25,5),(25,20))
    for x,y,t in ((6,13,"MIMIC"),(9,10,"MIMIC"),(18,5,"MIMIC"),
                  (25,16,"MIMIC"),(7,11,"HEAL"),(12,9,"HEAL")):
        grid[y][x]=t
    yield "chest clues",grid

    for seed in range(10):
        rng=random.Random(seed+888)
        grid=v.empty_grid()
        for y in range(1,25):
            for x in range(1,39):
                r=rng.random()
                grid[y][x]="W" if r<.27 else "PIT" if r<.285 else "EMPTY"
        landmarks(grid,(rng.randint(16,30),rng.randint(2,9)),
                   (rng.randint(16,30),rng.randint(17,23)))
        yield "random obstacles "+str(seed),grid


if __name__=="__main__":
    results=[]
    for name,grid in maps():
        results.append(v.play(grid,name))
    print("CLEARS",sum(r["won"] for r in results),"/",len(results),flush=True)
