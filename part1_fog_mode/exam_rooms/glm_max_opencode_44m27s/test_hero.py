# -*- coding: utf-8 -*-
"""BLIND 迷雾仿真：用 decide_action 在测试地图上完整跑局。"""
import sys
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\glm_max")
import submission as S
import test_dungeon as T

W, H = 40, 26
HW = T.HW


class FogGame:
    def __init__(self, d, max_turns=240):
        self.j = T.Judge(d)
        self.d = d
        self.clues = self._bind_clues(d["grid"])
        self.turn = 0
        self.max_turns = max_turns
        self.memory = {}
        self.actions = []

    def _bind_clues(self, grid):
        terr = [[grid[y][x] if grid[y][x] not in ("BOX", "TNT") else "EMPTY" for x in range(W)] for y in range(H)]
        chests = [(x, y) for y in range(H) for x in range(W) if grid[y][x] in ("HEAL", "MIMIC")]
        clues = [[False] * W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                if grid[y][x] != "MIMIC":
                    continue
                for ch in "UDLR":
                    dx, dy = T.DIRS[ch]
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < W and 0 <= ny < H):
                        continue
                    if terr[ny][nx] != "EMPTY":
                        continue
                    if 1 <= nx <= 3 and 12 <= ny <= 14:
                        continue
                    if any((nx + ddx, ny + ddy) in chests and (nx + ddx, ny + ddy) != (x, y)
                           for ddx, ddy in T.DIRS.values() if 0 <= nx + ddx < W and 0 <= ny + ddy < H):
                        continue
                    if clues[ny][nx]:
                        continue
                    clues[ny][nx] = True
                    break
        return clues

    def _is_wall_now(self, x, y):
        if not (0 <= x < W and 0 <= y < H):
            return True
        return self.j.is_wall(x, y)

    def visible(self):
        j = self.j
        hx, hy = j.hx, j.hy
        vis = [[False] * W for _ in range(H)]

        def is_wall_cell(x, y):
            return self._is_wall_now(x, y)

        # 基础候选 dx^2+dy^2<=10, 按 max(|dx|,|dy|) 由近及远
        cand = {}
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                if dx * dx + dy * dy <= 10:
                    cand.setdefault(max(abs(dx), abs(dy)), []).append((dx, dy))
        for ring in sorted(cand):
            for (dx, dy) in cand[ring]:
                x, y = hx + dx, hy + dy
                if not (0 <= x < W and 0 <= y < H):
                    continue
                sx = (dx > 0) - (dx < 0)
                sy = (dy > 0) - (dy < 0)

                def open_(odx, ody):
                    ox, oy = hx + odx, hy + ody
                    if not (0 <= ox < W and 0 <= oy < H):
                        return False
                    return vis[oy][ox] and not is_wall_cell(ox, oy)

                ok = False
                if ring <= 1:
                    ok = True
                elif dx == 0 or dy == 0:
                    ok = open_(dx - sx, dy - sy)
                elif abs(dx) == 2 and abs(dy) == 2:
                    ok = open_(sx, sy) and not (is_wall_cell(hx + sx, hy) and is_wall_cell(hx, hy + sy))
                elif abs(dx) > abs(dy):
                    ok = open_(dx - sx, dy) or open_(dx - sx, dy - sy)
                else:
                    ok = open_(dx, dy - sy) or open_(dx - sx, dy - sy)
                if ok:
                    vis[y][x] = True
        # 相邻 8 格冰道延伸
        extra = set()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                ix, iy = hx + dx, hy + dy
                if not (0 <= ix < W and 0 <= iy < H) or not vis[iy][ix]:
                    continue
                if self.j.terr[iy][ix] == "ICE":
                    cx, cy = ix, iy
                    while True:
                        nx, ny = cx + (1 if dx > 0 else (-1 if dx < 0 else 0)), cy + (1 if dy > 0 else (-1 if dy < 0 else 0))
                        if not (0 <= nx < W and 0 <= ny < H):
                            break
                        if self._is_wall_now(nx, ny):
                            break
                        extra.add((nx, ny))
                        if self.j.terr[ny][nx] != "ICE":
                            break
                        cx, cy = nx, ny
        for (x, y) in extra:
            vis[y][x] = True
        vis[hy][hx] = True
        return vis

    def build_state(self):
        j = self.j
        vis = self.visible()
        terr = [[("UNKNOWN") for _ in range(W)] for _ in range(H)]
        occ = [[None] * W for _ in range(H)]
        clues = [[False] * W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                if vis[y][x]:
                    t = j.terr[y][x]
                    if t in ("HEAL", "MIMIC"):
                        t = "CHEST"
                    terr[y][x] = t
                    occ[y][x] = j.occ[y][x]
                    clues[y][x] = self.clues[y][x]
        lw = []
        if self.turn % 3 == 0:
            for y in range(H):
                for x in range(W):
                    t = j.terr[y][x]
                    if t and t.startswith("LASER_"):
                        d = T.DIRS[t[-1]]
                        cx, cy = x, y
                        for _ in range(10):
                            cx += d[0]; cy += d[1]
                            if not (0 <= cx < W and 0 <= cy < H):
                                break
                            if j.is_wall(cx, cy) or j.occ[cy][cx] == "BOX":
                                break
                            if vis[cy][cx]:
                                lw.append({"x": cx, "y": cy, "dir": t[-1]})
                            if j.occ[cy][cx] == "TNT":
                                break
            lw.sort(key=lambda w: (w["y"], w["x"], w["dir"]))
        d = self.d["grid"]
        k1 = [(x, y) for y in range(H) for x in range(W) if d[y][x] == "K1"][0]
        k2 = [(x, y) for y in range(H) for x in range(W) if d[y][x] == "K2"][0]
        vv = [(x, y) for y in range(H) for x in range(W) if d[y][x] == "V"][0]
        return {
            "turn": self.turn,
            "turns_left": self.max_turns - self.turn,
            "mode": "BLIND",
            "hero": {"x": j.hx, "y": j.hy, "hp": j.hp, "keys": [j.k1, j.k2],
                     "jumps": j.jumps, "throws": j.throws, "bombs": j.bombs},
            "gates_flipped": j.gates,
            "targets": {"K1": list(k1), "K2": list(k2), "V": list(vv)},
            "visible_mask": vis,
            "terrain": terr,
            "occupant": occ,
            "bombs": [dict(b) for b in j.bombs_list],
            "clues": clues,
            "laser_warnings": lw,
        }

    def run(self, verbose=False):
        while self.turn < self.max_turns and self.j.status == "ALIVE":
            self.turn += 1
            st = self.build_state()
            act = S.decide_action(st, self.memory)
            self.actions.append(act)
            self.j.step(self.turn, act)
            if verbose and self.turn % 20 == 0:
                print(f"  t={self.turn} {act} pos=({self.j.hx},{self.j.hy}) hp={self.j.hp} k=({self.j.k1},{self.j.k2}) {self.j.status}")
        j = self.j
        print(f"  -> outcome={j.status} turns={self.turn} hp={j.hp} keys=({j.k1},{j.k2}) pos=({j.hx},{j.hy})")
        return j.status


def make_map(place, k1=(20, 5), k2=(20, 20), v=(35, 13)):
    grid = [["T_W" if (x in (0, 39) or y in (0, 25)) else "EMPTY" for x in range(W)] for y in range(H)]
    grid[k1[1]][k1[0]] = "K1"
    grid[k2[1]][k2[0]] = "K2"
    grid[v[1]][v[0]] = "V"
    for (x, y), t in place.items():
        grid[y][x] = t
    return {"taunt": "t", "grid": grid, "author_solution": ["WAIT"]}


if __name__ == "__main__":
    import time

    print("[T1] 空旷图：应当通关")
    g = FogGame(make_map({}))
    t0 = time.time()
    g.run(verbose=True)
    print(f"  用时 {time.time()-t0:.2f}s, 平均每步 {(time.time()-t0)/g.turn*1000:.1f}ms")

    print("[T2] 陷阱图：深坑阵+激光+冰道+宝箱怪+裂缝 —— 应存活并推进")
    P = {}
    for y in range(4, 24):
        P[(12, y)] = "PIT" if y % 3 else "EMPTY"
    P[(14, 8)] = "MIMIC"
    P[(30, 9)] = "LASER_D"
    P[(24, 10)] = "ICE"; P[(25, 10)] = "ICE"; P[(26, 10)] = "PIT"
    P[(28, 20)] = "CRACK"; P[(29, 20)] = "CRACK"
    P[(33, 5)] = "HEAL"
    g2 = FogGame(make_map(P))
    t0 = time.time()
    g2.run(verbose=True)
    print(f"  用时 {time.time()-t0:.2f}s")

    print("[T3] 本人魔王图：不崩溃即可（勇者无 4 跳无法通关，属预期）")
    g3 = FogGame(S.build_dungeon())
    t0 = time.time()
    g3.run(verbose=True)
    print(f"  用时 {time.time()-t0:.2f}s, 平均每步 {(time.time()-t0)/g3.turn*1000:.1f}ms")
