# -*- coding: utf-8 -*-
"""本地验证：魔王图合法性 + author_solution 物理回放 + 勇者迷雾仿真。"""
import sys
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\glm_max")
import submission as S

W, H = 40, 26
DIRS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
HW = {"W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R"}


def validate(d):
    grid = d["grid"]
    errs = []
    assert len(grid) == 26, "rows != 26"
    for y, row in enumerate(grid):
        assert len(row) == 40, f"row {y} len != 40"
    # border
    for y in range(H):
        for x in range(W):
            if x in (0, 39) or y in (0, 25):
                if grid[y][x] != "T_W":
                    errs.append(f"border ({x},{y}) not T_W")
    # spawn zone
    for y in range(12, 15):
        for x in range(1, 4):
            if grid[y][x] != "EMPTY":
                errs.append(f"spawn zone ({x},{y}) = {grid[y][x]}")
    # landmarks
    k1 = [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "K1"]
    k2 = [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "K2"]
    v = [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "V"]
    assert len(k1) == 1 and len(k2) == 1 and len(v) == 1, "landmark count"
    (k1x, k1y), (k2x, k2y), (vx, vy) = k1[0], k2[0], v[0]
    assert 12 <= k1x <= 34 and 2 <= k1y <= 10, "K1 bounds"
    assert 12 <= k2x <= 34 and 15 <= k2y <= 23, "K2 bounds"
    assert abs(k1x - k2x) + abs(k1y - k2y) >= 12, "K dist"
    assert 33 <= vx <= 37 and 4 <= vy <= 21, "V bounds"
    # budget & quotas
    cost = 0
    inner_tw = 0
    counts = {}
    for y in range(1, 25):
        for x in range(1, 39):
            t = grid[y][x]
            cost += S.TILE_COSTS[t]
            counts[t] = counts.get(t, 0) + 1
            if t == "T_W":
                inner_tw += 1
    assert cost <= 3000, f"budget {cost} > 3000"
    assert inner_tw <= 120
    assert counts.get("MIRROR_NE", 0) + counts.get("MIRROR_SE", 0) + counts.get("MIRROR_SW", 0) + counts.get("MIRROR_NW", 0) <= 30
    assert sum(counts.get(k, 0) for k in ("SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R")) <= 20
    assert sum(counts.get(k, 0) for k in ("LASER_U", "LASER_D", "LASER_L", "LASER_R")) <= 12
    assert counts.get("CRACK", 0) <= 40 and counts.get("SWITCH", 0) <= 6
    assert counts.get("R_GATE", 0) + counts.get("B_GATE", 0) <= 16
    assert counts.get("TNT", 0) <= 12 and counts.get("BOX", 0) <= 4
    assert counts.get("HEAL", 0) <= 4 and counts.get("MIMIC", 0) <= 4
    # mimic clue binding (rules §3.4)
    terr = [[grid[y][x] if grid[y][x] not in ("BOX", "TNT") else "EMPTY" for x in range(W)] for y in range(H)]
    occ = [["BOX" if grid[y][x] == "BOX" else ("TNT" if grid[y][x] == "TNT" else None) for x in range(W)] for y in range(H)]
    chests = [(x, y) for y in range(H) for x in range(W) if grid[y][x] in ("HEAL", "MIMIC")]
    clues = [[False] * W for _ in range(H)]
    for (mx, my) in [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "MIMIC"]:
        ok = False
        for ch in "UDLR":
            dx, dy = DIRS[ch]
            nx, ny = mx + dx, my + dy
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            if terr[ny][nx] != "EMPTY" or occ[ny][nx] is not None:
                continue
            if 1 <= nx <= 3 and 12 <= ny <= 14:
                continue
            other_chest = any((nx + ddx, ny + ddy) in chests and (nx + ddx, ny + ddy) != (mx, my)
                              for ddx, ddy in DIRS.values() if 0 <= nx + ddx < W and 0 <= ny + ddy < H)
            if other_chest or clues[ny][nx]:
                continue
            clues[ny][nx] = True
            ok = True
            break
        if not ok:
            errs.append(f"MIMIC ({mx},{my}) no legal clue cell")
    print(f"[validate] cost={cost}G inner_tw={inner_tw} k1={k1[0]} k2={k2[0]} v={v[0]} errs={errs}")
    return not errs


# ---------------------------------------------------------------- mini judge
class Judge:
    def __init__(self, d):
        self.grid = [list(r) for r in d["grid"]]
        self.terr = [[self.grid[y][x] if self.grid[y][x] not in ("BOX", "TNT") else "EMPTY" for x in range(W)] for y in range(H)]
        self.occ = [["BOX" if self.grid[y][x] == "BOX" else ("TNT" if self.grid[y][x] == "TNT" else None) for x in range(W)] for y in range(H)]
        self.hx, self.hy = 2, 13
        self.hp = 100
        self.k1 = self.k2 = False
        self.jumps = 3; self.throws = 3; self.bombs = 2
        self.gates = False
        self.bombs_list = []
        self.status = "ALIVE"
        self.trace = []

    def is_wall(self, x, y):
        t = self.terr[y][x]
        if t in HW:
            return True
        if t == "R_GATE":
            return not self.gates
        if t == "B_GATE":
            return self.gates
        return False

    def atomic(self, x0, y0, x1, y1, ent, exposed, st, dx, dy):
        """8 步原子位移；ent='hero'；(dx,dy) 为本次位移的动量方向。返回 (stopped, dead, won)。"""
        steps, dead, won = st
        px, py = x0, y0
        cx, cy = x1, y1
        while True:
            steps += 1
            # leave hook
            if self.terr[py][px] == "CRACK":
                self.terr[py][px] = "PIT"
            self.hx, self.hy = cx, cy
            if ent == "hero":
                exposed.add((cx, cy))
            # arrive hook
            t = self.terr[cy][cx]
            if ent == "hero":
                if t == "PIT":
                    self.hp -= 100
                elif t == "MIMIC":
                    self.hp -= 45; self.terr[cy][cx] = "EMPTY"; return (True, True, False)
                elif t == "HEAL":
                    self.hp = min(100, self.hp + 30); self.terr[cy][cx] = "EMPTY"
                elif t == "SWITCH":
                    self.gates = not self.gates
                if self.hp <= 0:
                    return (True, True, False)
                if t == "K1":
                    self.k1 = True; self.terr[cy][cx] = "EMPTY"
                if t == "K2":
                    self.k2 = True; self.terr[cy][cx] = "EMPTY"
                if t == "V" and self.k1 and self.k2 and self.hp > 0:
                    return (True, False, True)
            # momentum continuation
            if steps >= 32:
                return (True, dead, won)
            t = self.terr[cy][cx]
            if t == "ICE":
                nx, ny = cx + dx, cy + dy
                if self.is_wall(nx, ny) or self.occ[ny][nx] in ("BOX", "TNT"):
                    return (True, dead, won)
                px, py = cx, cy
                cx, cy = nx, ny
                continue
            if t and t.startswith("SPRING_"):
                d = DIRS[t[-1]]
                blocked_k = None
                for k in (1, 2, 3):
                    pk = (cx + k * d[0], cy + k * d[1])
                    if self.is_wall(*pk) or self.occ[pk[1]][pk[0]] in ("BOX", "TNT"):
                        blocked_k = k
                        break
                if blocked_k is None:
                    px, py = cx, cy
                    cx, cy = cx + 3 * d[0], cy + 3 * d[1]
                    continue
                if blocked_k == 1:
                    return (True, dead, won)
                px, py = cx, cy
                cx, cy = cx + (blocked_k - 1) * d[0], cy + (blocked_k - 1) * d[1]
                continue
            if t and t.startswith("PORTAL_"):
                return (True, dead, won)  # 本图无传送门
            return (True, dead, won)

    def explode(self, sources, exposed):
        """阶段 C/D 爆炸闭包；返回 hero 受伤。"""
        Q = list(sources)
        done = set(sources)
        while Q:
            ex, ey = Q.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    cx, cy = ex + dx, ey + dy
                    if not (0 <= cx < W and 0 <= cy < H):
                        continue
                    if self.occ[cy][cx] == "TNT" and (cx, cy) not in done:
                        done.add((cx, cy)); Q.append((cx, cy))
            for b in list(self.bombs_list):
                if (b["x"], b["y"]) not in done:
                    done.add((b["x"], b["y"])); Q.append((b["x"], b["y"]))
        dmg = 0
        for (ex, ey) in done:
            if abs(self.hx - ex) <= 1 and abs(self.hy - ey) <= 1:
                dmg += 50  # 自伤（本图作者路径从不波及自身）
        for (ex, ey) in done:
            for b in self.bombs_list:
                if (b["x"], b["y"]) == (ex, ey):
                    self.bombs_list.remove(b)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    cx, cy = ex + dx, ey + dy
                    if not (0 <= cx < W and 0 <= cy < H):
                        continue
                    if self.occ[cy][cx] == "BOX":
                        self.occ[cy][cx] = None
                    t = self.terr[cy][cx]
                    if t in ("T_W", "K1", "K2", "V", "PIT") or (t and t.startswith("PORTAL_")):
                        continue
                    if t == "CRACK":
                        self.terr[cy][cx] = "PIT"
                    elif t in ("W", "ICE", "SWITCH", "R_GATE", "B_GATE", "HEAL", "MIMIC") or \
                            (t and (t.startswith("MIRROR_") or t.startswith("SPRING_") or t.startswith("LASER_"))):
                        self.terr[cy][cx] = "EMPTY"
        return dmg

    def step(self, turn, action):
        exposed = {(self.hx, self.hy)}
        won = dead = False
        ch = action[-1] if action not in ("WAIT", "BOMB") else None
        if action == "WAIT":
            pass
        elif action == "BOMB":
            if self.bombs > 0 and not any(b["x"] == self.hx and b["y"] == self.hy for b in self.bombs_list):
                self.bombs -= 1
                self.bombs_list.append({"x": self.hx, "y": self.hy, "timer": 3})
        elif action.startswith("MOVE_"):
            d = DIRS[ch]
            nx, ny = self.hx + d[0], self.hy + d[1]
            if self.is_wall(nx, ny) or self.occ[ny][nx] == "TNT":
                pass
            elif self.occ[ny][nx] == "BOX":
                pass
            else:
                _, dead, won = self.atomic(self.hx, self.hy, nx, ny, "hero", exposed, (0, False, False), d[0], d[1])
        elif action.startswith("JUMP_"):
            if self.jumps > 0:
                self.jumps -= 1
                d = DIRS[ch]
                p1 = (self.hx + d[0], self.hy + d[1])
                p2 = (self.hx + 2 * d[0], self.hy + 2 * d[1])
                if not self.is_wall(*p1) and not (self.is_wall(*p2) or self.occ[p2[1]][p2[0]] in ("BOX", "TNT")):
                    _, dead, won = self.atomic(self.hx, self.hy, p2[0], p2[1], "hero", exposed, (0, False, False), d[0], d[1])
        if dead:
            self.status = "DEAD"; return exposed
        if won:
            self.status = "CLEARED"; return exposed
        # phase C: bombs
        armed_tnt = []
        for b in self.bombs_list:
            b["timer"] -= 1
        src = [(b["x"], b["y"]) for b in self.bombs_list if b["timer"] == 0] + armed_tnt
        if src:
            dmg = self.explode(src, exposed)
            self.hp -= dmg
            if self.hp <= 0:
                self.status = "DEAD"; return exposed
        # phase D: lasers
        if turn % 3 == 0:
            for (ly, lx) in [(y, x) for y in range(H) for x in range(W) if self.terr[y][x].startswith("LASER_")]:
                t = self.terr[ly][lx]
                d = DIRS[t[-1]]
                ray = set()
                cx, cy = lx, ly
                for _ in range(10):
                    cx += d[0]; cy += d[1]
                    if not (0 <= cx < W and 0 <= cy < H):
                        break
                    if self.is_wall(cx, cy) or self.occ[cy][cx] == "BOX":
                        break
                    ray.add((cx, cy))
                if ray & exposed:
                    self.hp -= 50
                    if self.hp <= 0:
                        self.status = "DEAD"; return exposed
        return exposed


def replay(d):
    j = Judge(d)
    sol = d["author_solution"]
    assert 1 <= len(sol) <= 240
    for a in sol:
        assert a in S.VALID_ACTIONS, f"illegal action {a}"
    for i, a in enumerate(sol, 1):
        j.step(i, a)
        if j.status != "ALIVE":
            break
    print(f"[replay] turns_run={i}/{len(sol)} status={j.status} hp={j.hp} pos=({j.hx},{j.hy}) "
          f"keys=({j.k1},{j.k2}) jumps={j.jumps} bombs={j.bombs}")
    ok = (j.status == "CLEARED" and i == len(sol) and j.hp > 0)
    print(f"[replay] {'PASS: 最后一步恰好首达通关' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    d = S.build_dungeon()
    v = validate(d)
    r = replay(d)
    print("ALL:", "PASS" if (v and r) else "FAIL")
