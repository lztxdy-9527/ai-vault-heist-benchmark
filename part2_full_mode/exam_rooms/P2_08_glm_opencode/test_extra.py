# -*- coding: utf-8 -*-
"""综合回归：本人图求解 + GV22 规则保真 + 记忆清空恢复 + 计时红线。"""
import sys, time
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S
import test_full as T

W, H = 40, 26


def mk_clues(grid):
    terr = [[grid[y][x] if grid[y][x] not in ("BOX", "TNT") else "EMPTY" for x in range(W)] for y in range(H)]
    chests = [(x, y) for y in range(H) for x in range(W) if grid[y][x] in ("HEAL", "MIMIC")]
    clues = [[False] * W for _ in range(H)]
    for (mx, my) in [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "MIMIC"]:
        for ch in "UDLR":
            dx, dy = S.DIRS[ch]
            nx, ny = mx + dx, my + dy
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            if terr[ny][nx] != "EMPTY":
                continue
            if 1 <= nx <= 3 and 12 <= ny <= 14:
                continue
            if any((nx + ddx, ny + ddy) in chests and (nx + ddx, ny + ddy) != (mx, my)
                   for ddx, ddy in S.DIRS.values() if 0 <= nx + ddx < W and 0 <= ny + ddy < H):
                continue
            if clues[ny][nx]:
                continue
            clues[ny][nx] = True
            break
    return clues


def run(d, wipe_every=0, label=""):
    st = T._mk_state(d, turn=1)
    st["clues"] = mk_clues(d["grid"])
    w = S.decode_state(st)
    memory = {}
    max_ms = 0.0
    n = 0
    for i in range(1, 241):
        if wipe_every and i % wipe_every == 0:
            memory = {}
        st["turn"] = i
        st["hero"].update({"x": w.hx, "y": w.hy, "hp": w.hp, "keys": [w.k1, w.k2],
                           "jumps": w.jumps, "bombs": w.bombs})
        st["gates_flipped"] = w.gates
        st["bombs"] = [{"x": b[0], "y": b[1], "timer": b[2]} for b in w.bl]
        st["terrain"] = [[(w.t(x, y) if w.t(x, y) not in ("HEAL", "MIMIC") else "CHEST")
                          for x in range(W)] for y in range(H)]
        st["occupant"] = [[w.occ.get((x, y)) for x in range(W)] for y in range(H)]
        ta = time.time()
        act = S.decide_action(st, memory)
        max_ms = max(max_ms, (time.time() - ta) * 1000)
        w = S.step_world(w, act)
        n = i
        if w.status != "ALIVE":
            break
    print(f"[{label}] status={w.status} turns={n} hp={w.hp} keys=({w.k1},{w.k2}) "
          f"pos=({w.hx},{w.hy}) 单步最大 {max_ms:.0f}ms")


# ---- 1. 求解器跑本人魔王图 + 记忆清空恢复 ----
d = S.build_dungeon()
run(d, label="own-map")
run(d, wipe_every=17, label="own-map+wipe17")

# ---- 2. GV22 规则保真 ----
def gv(name, cond):
    print(f"  {name}: {'PASS' if cond else 'FAIL'}")
    return cond


def mk_grid(extra):
    grid = [["T_W" if (x in (0, 39) or y in (0, 25)) else "EMPTY" for x in range(W)] for y in range(H)]
    grid[5][20] = "K1"; grid[20][20] = "K2"; grid[13][35] = "V"
    for (x, y), t in extra.items():
        grid[y][x] = t
    return grid


ok = True
grid = mk_grid({(5, 13): "PLATE", (7, 13): "BOX", (34, 13): "P_GATE"})
dd = {"taunt": "", "grid": grid, "author_solution": ["WAIT"]}
st = T._mk_state(dd, turn=1)
st["hero"]["x"], st["hero"]["y"] = 4, 13
w = S.decode_state(st)
w = S.step_world(w, "MOVE_R")
ok &= gv("GV22_02a hero-on-plate not active", w.plates_active() is False)
st = T._mk_state(dd, turn=1)
st["hero"]["x"], st["hero"]["y"] = 8, 13
w = S.decode_state(st)
w = S.step_world(w, "MOVE_L")
w = S.step_world(w, "MOVE_L")
ok &= gv("GV22_02b box-on-plate active", w.plates_active() is True)

grid = mk_grid({(15, 8): "LASER_D", (12, 10): "LASER2_R"})
dd = {"taunt": "", "grid": grid, "author_solution": ["WAIT"]}
st = T._mk_state(dd, turn=12)
st["hero"]["x"], st["hero"]["y"] = 15, 10
w = S.decode_state(st)
w = S.step_world(w, "WAIT")
ok &= gv("GV22_03 LCM12 dual-kill", w.hp == 0 and w.status == "DEAD")

grid = mk_grid({(5, 13): "CRACK", (6, 13): "ONEWAY_L"})
dd = {"taunt": "", "grid": grid, "author_solution": ["WAIT"]}
st = T._mk_state(dd, turn=1)
st["hero"]["x"], st["hero"]["y"] = 5, 13
st["occupant"][13][6] = "BOX"
w = S.decode_state(st)
w = S.step_world(w, "MOVE_R")
ok &= gv("GV22_04a reverse-push rejected", (w.hx, w.hy) == (5, 13)
         and w.occ.get((6, 13)) == "BOX" and w.t(5, 13) == "CRACK")

grid = mk_grid({(10, 10): "SPRING_R", (12, 10): "ONEWAY_L"})
dd = {"taunt": "", "grid": grid, "author_solution": ["WAIT"]}
st = T._mk_state(dd, turn=1)
st["hero"]["x"], st["hero"]["y"] = 9, 10
w = S.decode_state(st)
w = S.step_world(w, "MOVE_R")
ok &= gv("GV22_05 spring early-land oneway", (w.hx, w.hy) == (11, 10))

grid = mk_grid({(6, 14): "ONEWAY_L"})
dd = {"taunt": "", "grid": grid, "author_solution": ["WAIT"]}
st = T._mk_state(dd, turn=1)
st["hero"]["x"], st["hero"]["y"] = 5, 14
w = S.decode_state(st)
w = S.step_world(w, "JUMP_R")
ok &= gv("GV22_05b jump over reverse-oneway fails", (w.hx, w.hy) == (5, 14) and w.jumps == 2)

# ---- 3. 计时红线 ----
t0 = time.time()
import importlib
importlib.reload(S)
print(f"[import] {time.time()-t0:.3f}s (limit 1.5s)")
t0 = time.time()
d = S.build_dungeon()
print(f"[build_dungeon] {time.time()-t0:.3f}s (limit 2.0s)")
print("GV22 overall:", "PASS" if ok else "FAIL")
