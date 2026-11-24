"""Offline development checks.  Not part of the submitted contestant module."""
import ast
import collections
import importlib.util
import json
import random
import time

import submission as s


COSTS = {
    "EMPTY": 0, "K1": 0, "K2": 0, "V": 0, "W": 5, "T_W": 25,
    "ICE": 10, "PIT": 40, "CRACK": 20, "SWITCH": 30, "R_GATE": 20,
    "B_GATE": 20, "TNT": 40, "BOX": 30, "HEAL": 30, "MIMIC": 60,
}
for tile in ("NE", "SE", "SW", "NW"):
    COSTS["MIRROR_" + tile] = 25
for d in "UDLR":
    COSTS["SPRING_" + d] = 35
    COSTS["LASER_" + d] = 75
for p in ("1A", "1B", "2A", "2B"):
    COSTS["PORTAL_" + p] = 40


def empty_grid():
    return [["T_W" if x in (0, 39) or y in (0, 25) else "EMPTY"
             for x in range(40)] for y in range(26)]


def validate(result):
    grid = result["grid"]
    assert len(grid) == 26 and all(len(row) == 40 for row in grid)
    count = collections.Counter()
    positions = {}
    spent = 0
    for y, row in enumerate(grid):
        for x, tile in enumerate(row):
            assert tile in COSTS, (x, y, tile)
            if x in (0, 39) or y in (0, 25):
                assert tile == "T_W"
                continue
            count[tile] += 1
            spent += COSTS[tile]
            positions.setdefault(tile, []).append((x, y))
    assert spent <= 3000, spent
    assert all(grid[y][x] == "EMPTY" for y in range(12, 15) for x in range(1, 4))
    for key in ("K1", "K2", "V"):
        assert count[key] == 1
    x1, y1 = positions["K1"][0]
    x2, y2 = positions["K2"][0]
    xv, yv = positions["V"][0]
    assert 12 <= x1 <= 34 and 2 <= y1 <= 10
    assert 12 <= x2 <= 34 and 15 <= y2 <= 23
    assert abs(x1-x2)+abs(y1-y2) >= 12
    assert 33 <= xv <= 37 and 4 <= yv <= 21
    for prefix, limit in (("MIRROR_", 30), ("SPRING_", 20), ("LASER_", 12)):
        assert sum(n for t, n in count.items() if t.startswith(prefix)) <= limit
    assert count["T_W"] <= 120 and count["CRACK"] <= 40
    assert count["SWITCH"] <= 6 and count["R_GATE"] + count["B_GATE"] <= 16
    for tile, limit in (("TNT", 12), ("BOX", 4), ("HEAL", 4), ("MIMIC", 4)):
        assert count[tile] <= limit
    for n in (1, 2):
        assert count[f"PORTAL_{n}A"] == count[f"PORTAL_{n}B"]
        assert count[f"PORTAL_{n}A"] <= 1
    assert len(result["taunt"]) <= 40
    assert 1 <= len(result["author_solution"]) <= 240
    assert all(a in s.ALL_ACTIONS for a in result["author_solution"])
    bind_clues(grid)
    return spent


def bind_clues(grid):
    clues = {}
    for y in range(26):
        for x in range(40):
            if grid[y][x] != "MIMIC":
                continue
            for dx, dy in s.DIRS:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < 40 and 0 <= ny < 26):
                    continue
                if grid[ny][nx] != "EMPTY" or (1 <= nx <= 3 and 12 <= ny <= 14):
                    continue
                if (nx, ny) in clues.values():
                    continue
                others = [(nx+ddx, ny+ddy) for ddx, ddy in s.DIRS
                          if (nx+ddx, ny+ddy) != (x, y)
                          and 0 <= nx+ddx < 40 and 0 <= ny+ddy < 26
                          and grid[ny+ddy][nx+ddx] in ("HEAL", "MIMIC")]
                if not others:
                    clues[(x, y)] = (nx, ny)
                    break
            else:
                raise AssertionError(("invalid mimic clue", x, y))
    return clues


def decode(grid, hero=None, turn=1):
    terrain = [s.CODE[tile] if tile not in ("BOX", "TNT") else s.EMPTY
               for row in grid for tile in row]
    occupant = [s.BOX if tile == "BOX" else s.TNT if tile == "TNT" else 0
                for row in grid for tile in row]
    if hero is None:
        hero = dict(x=2, y=13, hp=100, keys=[False, False], jumps=3, throws=3, bombs=2)
    return s._World(terrain, occupant, hero)


def independent_author_replay(result):
    """Independent minimal interpreter for this map's portal/wall/laser route."""
    grid = [row[:] for row in result["grid"]]
    p, hp, keys, jumps = (2, 13), 100, set(), 3
    bombs=[];stock=2
    portals = {grid[y][x]: (x, y) for y in range(26) for x in range(40)
               if grid[y][x].startswith("PORTAL_")}
    for turn, action in enumerate(result["author_solution"], 1):
        exposed = {p}
        if action == "WAIT":
            pass
        elif action == "BOMB":
            assert stock>0
            stock-=1
            bombs.append((p,3))
        else:
            mode, direction = action.split("_")
            dx, dy = s.DIRS["UDLR".index(direction)]
            distance = 2 if mode == "JUMP" else 1
            if mode == "JUMP":
                assert jumps > 0
                jumps -= 1
                assert grid[p[1]+dy][p[0]+dx] not in ("T_W", "W")
            q = p[0] + distance*dx, p[1] + distance*dy
            assert grid[q[1]][q[0]] not in ("W", "T_W")
            p = q
            exposed.add(p)
            if grid[p[1]][p[0]].startswith("PORTAL_"):
                t = grid[p[1]][p[0]]
                pair = t[:-1] + ("B" if t[-1] == "A" else "A")
                p = portals[pair]
                exposed.add(p)
                q = p[0] + dx, p[1] + dy
                if grid[q[1]][q[0]] not in ("W", "T_W"):
                    p = q
                    exposed.add(p)
            tile = grid[p[1]][p[0]]
            if tile == "PIT":
                hp -= 100
            if tile in ("K1", "K2"):
                keys.add(tile)
                grid[p[1]][p[0]] = "EMPTY"
            if tile == "V" and len(keys) == 2:
                assert hp > 0 and turn == len(result["author_solution"])
                return turn, hp
        bombs=[(bp,timer-1) for bp,timer in bombs]
        exploding=[bp for bp,timer in bombs if timer<=0]
        bombs=[(bp,timer) for bp,timer in bombs if timer>0]
        for bx,by in exploding:
            if max(abs(p[0]-bx),abs(p[1]-by))<=1:
                hp-=50
            for yy in range(max(0,by-1),min(26,by+2)):
                for xx in range(max(0,bx-1),min(40,bx+2)):
                    if grid[yy][xx] == "W":
                        grid[yy][xx]="EMPTY"
        if turn % 3 == 0:
            for y in range(26):
                for x in range(40):
                    t = grid[y][x]
                    if not t.startswith("LASER_"):
                        continue
                    dx, dy = s.DIRS["UDLR".index(t[-1])]
                    ray = set()
                    for distance in range(1, 11):
                        q = x + dx*distance, y + dy*distance
                        if not (0 <= q[0] < 40 and 0 <= q[1] < 26):
                            break
                        if grid[q[1]][q[0]] in ("W", "T_W") or grid[q[1]][q[0]].startswith("LASER_"):
                            break
                        ray.add(q)
                    if ray & exposed:
                        hp -= 50
        assert hp > 0, (turn, p, hp)
    raise AssertionError("author did not clear")


def golden_checks():
    with open("golden_vectors.json", encoding="utf-8") as f:
        vectors = json.load(f)["vectors"]
    for v in vectors:
        if "initial" not in v or "local_tiles" not in v.get("initial", {}):
            continue
        initial = v["initial"]
        grid = empty_grid()
        w = decode(grid, initial["hero"])
        w.flipped = initial.get("gates_flipped", False)
        for coord, content in initial["local_tiles"].items():
            x, y = (int(n) for n in coord.strip("()").split(","))
            p = y*40+x
            w.base_t[p] = s.CODE[content["terrain"]]
            w.base_o[p] = s.BOX if content["occupant"] == "BOX" else s.TNT if content["occupant"] == "TNT" else 0
        w = s._World(w.base_t, w.base_o, initial["hero"], w.flipped)
        after = w.step(v["action"], initial["turn"])
        e = v["expected"]
        if "hero_final_pos" in e:
            assert [after.p % 40, after.p // 40] == e["hero_final_pos"], v["id"]
        if "hero_hp_after" in e:
            assert after.hp == e["hero_hp_after"], (v["id"], after.hp)
        if "trap_damage_dealt" in e:
            assert after.trap_damage == e["trap_damage_dealt"], v["id"]
        if "gates_flipped_after" in e:
            assert after.flipped == e["gates_flipped_after"], v["id"]
        if "exposed_cells" in e:
            assert after.exposed == {y*40+x for x, y in e["exposed_cells"]}, v["id"]
        if "bomb_timer_after_turn" in e:
            assert after.bombs[0][1] == e["bomb_timer_after_turn"], v["id"]
        if e["status"] == "CLEARED":
            assert after.won, v["id"]
        print("PASS", v["id"])
    # GV01 independent economics and clue binding.
    v = vectors[0]
    grid = empty_grid()
    for item in v["Placed_inner_tiles"]:
        grid[item["y"]][item["x"]] = item["tile"]
    total = sum(COSTS[grid[y][x]] for y in range(1, 25) for x in range(1, 39))
    assert total == 190 and bind_clues(grid)[(10, 10)] == (10, 9)
    print("PASS", v["id"])
    # GV06: 32nd landing executes; 33rd displacement must not begin.
    grid = empty_grid()
    for x in range(3, 35):
        grid[13][x] = "ICE"
    grid[13][35] = "PIT"
    w = decode(grid).step("MOVE_R", 1)
    assert w.p == 13*40+34 and w.hp == 100 and len(w.exposed) == 33
    grid[13][34] = "PIT"
    w = decode(grid).step("MOVE_R", 1)
    assert w.p == 13*40+34 and w.hp == 0
    print("PASS", vectors[5]["id"])


def visible(world):
    hx, hy = world.p % 40, world.p // 40
    vis = [[False]*40 for unused in range(26)]
    def high(x, y):
        return not (0 <= x < 40 and 0 <= y < 26) or s._high(world.tile(y*40+x), world.flipped)
    def clear(dx, dy):
        x, y = hx+dx, hy+dy
        return 0 <= x < 40 and 0 <= y < 26 and vis[y][x] and not high(x, y)
    for radius in range(4):
        for dy in range(-radius, radius+1):
            for dx in range(-radius, radius+1):
                if max(abs(dx),abs(dy)) != radius or dx*dx+dy*dy > 10:
                    continue
                x, y = hx+dx, hy+dy
                if not (0 <= x < 40 and 0 <= y < 26):
                    continue
                sx, sy = (dx > 0)-(dx < 0), (dy > 0)-(dy < 0)
                if radius <= 1:
                    ok = True
                elif dx == 0 or dy == 0:
                    ok = clear(dx-sx,dy-sy)
                elif abs(dx) == abs(dy):
                    ok = clear(sx,sy) and not (high(hx+sx,hy) and high(hx,hy+sy))
                elif abs(dx) > abs(dy):
                    ok = clear(dx-sx,dy) or clear(dx-sx,dy-sy)
                else:
                    ok = clear(dx,dy-sy) or clear(dx-sx,dy-sy)
                vis[y][x] = ok
    # The extension only increases the official base mask.  Trace nearby
    # ice/mirror lanes for stress tests; all base LOS rules above are exact.
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            if not (dx or dy):
                continue
            x,y = hx+dx,hy+dy
            if not (0 <= x < 40 and 0 <= y < 26):
                continue
            p=y*40+x
            if world.tile(p) != s.ICE and not s.MNE <= world.tile(p) <= s.MNW:
                continue
            for d0 in range(4):
                q,d = p,d0
                for unused in range(32):
                    t=world.tile(q)
                    if s.MNE <= t <= s.MNW:
                        d=s.MIRRORS[t-s.MNE][d]
                    elif t != s.ICE:
                        break
                    q=s.NEIGHBORS[q][d]
                    if q < 0:
                        break
                    vis[q//40][q%40]=True
                    if s._high(world.tile(q), world.flipped) or world.occ(q):
                        break
    return vis


def observation(world, turn, targets, clues):
    mask = visible(world)
    terrain, occupants, clue_mask = [], [], []
    for y in range(26):
        tr, oc, cl = [], [], []
        for x in range(40):
            p=y*40+x
            t=world.tile(p)
            tr.append("UNKNOWN" if not mask[y][x] else
                      "CHEST" if t in (s.HEAL,s.MIMIC) else s.NAMES[t])
            o=world.occ(p)
            oc.append(("BOX" if o == s.BOX else "TNT" if o == s.TNT else None) if mask[y][x] else None)
            exists = any(pos == (x,y) and world.tile(my*40+mx) == s.MIMIC
                         for (mx,my),pos in clues.items())
            cl.append(mask[y][x] and exists)
        terrain.append(tr);occupants.append(oc);clue_mask.append(cl)
    warnings=[]
    if turn % 3 == 0:
        for laser in world.lasers:
            t=world.tile(laser)
            if not s.LU <= t <= s.LR:
                continue
            d=t-s.LU;p=laser
            for unused in range(10):
                p=s.NEIGHBORS[p][d]
                if p<0 or s._high(world.tile(p),world.flipped) or world.occ(p):
                    break
                if mask[p//40][p%40]:
                    warnings.append(dict(x=p%40,y=p//40,dir=s.LETTERS[d]))
    return dict(turn=turn,turns_left=241-turn,mode="BLIND",
                hero=dict(x=world.p%40,y=world.p//40,hp=world.hp,
                          keys=[bool(world.keys&1),bool(world.keys&2)],
                          jumps=world.jumps,throws=world.throws,bombs=world.stock),
                gates_flipped=world.flipped,targets=targets,visible_mask=mask,
                terrain=terrain,occupant=occupants,clues=clue_mask,
                bombs=[dict(x=p%40,y=p//40,timer=t) for p,t in world.bombs],
                laser_warnings=warnings)


def play(grid, name, verbose=False):
    world=decode(grid)
    targets={tile:[x,y] for y in range(26) for x in range(40)
             if (tile:=grid[y][x]) in ("K1","K2","V")}
    clues=bind_clues(grid)
    memory={}; times=[]
    for turn in range(1,241):
        state=observation(world,turn,targets,clues)
        start=time.perf_counter()
        action=s.decide_action(state,memory)
        elapsed=time.perf_counter()-start
        times.append(elapsed)
        assert action in s.ALL_ACTIONS
        if elapsed > .5:
            raise AssertionError(("decision timeout", name, turn, elapsed))
        after=world.step(action,turn)
        if verbose:
            print(turn,(world.p%40,world.p//40),action,"->",
                  (after.p%40,after.p//40),after.hp,after.keys,
                  "jumps",after.jumps,"bombs",after.stock,
                  memory.get("search_reason"),memory.get("search_nodes"),round(elapsed,4),flush=True)
        world=after
        if world.hp<=0 or world.won:
            break
    result=dict(name=name,turn=turn,hp=world.hp,keys=world.keys,
                won=world.won,max_ms=round(max(times)*1000,2),
                mean_ms=round(sum(times)/len(times)*1000,2),
                position=[world.p%40,world.p//40],jumps=world.jumps,bombs=world.stock)
    print(result,flush=True)
    return result


def compliance():
    source=open("submission.py",encoding="utf-8").read()
    tree=ast.parse(source)
    allowed={"collections","heapq","math","time"}
    forbidden={"open","eval","exec","compile","globals","locals","getattr","setattr","delattr","vars","input","breakpoint"}
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            assert all(a.name in allowed for a in node.names)
        if isinstance(node,ast.ImportFrom):
            assert node.module in allowed
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
            assert node.func.id not in forbidden,node.func.id
        if isinstance(node,ast.Attribute):
            assert not node.attr.startswith("__"),node.attr
    print("PASS pure-computation AST check")


if __name__ == "__main__":
    golden_checks()
    compliance()
    start=time.perf_counter(); dungeon=s.build_dungeon(); build_time=time.perf_counter()-start
    print("BUILD",validate(dungeon),"gold",build_time,"seconds")
    print("AUTHOR INDEPENDENT",independent_author_replay(dungeon))
    world=decode(dungeon["grid"])
    for i,a in enumerate(dungeon["author_solution"],1):
        world=world.step(a,i)
        assert world.hp>0
        assert not world.won or i==len(dungeon["author_solution"])
    assert world.won
    print("AUTHOR FULL",i,world.hp)
    grid=empty_grid()
    grid[5][20]="K1";grid[20][20]="K2";grid[13][35]="V"
    play(grid,"open",False)
    play(dungeon["grid"],"own directional portals",True)
