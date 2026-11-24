"""admission.py — 出生 4 回合准入校验（v2.2 新规）与作者自证校验。

规则：必须存在至少 2 个不同的「第 1 回合末坐标」，各自满足零机关伤害存活到第 4 回合结束。
本实现用 4 层 DFS 精确枚举（14 种动作），剪掉任何产生机关伤害/死亡/通关的分支。
"""

import sys

sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_07_deepseek_dsh")
import judge_v22 as J

ACTION_ORDER = ("MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R", "WAIT",
                "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
                "THROW_U", "THROW_D", "THROW_L", "THROW_R", "BOMB")


def check_author_solution(grid, acts):
    """自证校验：1..200 步、全程合法、最后一步恰好首次存活踏上 V。"""
    errs = []
    if not isinstance(acts, list) or not (1 <= len(acts) <= J.MAX_AUTHOR_STEPS):
        return False, ["author_solution 长度须为 1..200，实为 %s" % (len(acts) if acts else 0)]
    for i, a in enumerate(acts):
        if a not in J.VALID_ACTIONS:
            errs.append("第 %d 步非法动作 %r" % (i + 1, a))
    if errs:
        return False, errs
    j = J.Judge(grid)
    for i, a in enumerate(acts):
        j.play(a)
        if j.status == "CLEARED":
            if i != len(acts) - 1:
                errs.append("第 %d 步已通关，其后仍有 %d 步冗余动作" % (i + 1, len(acts) - 1 - i))
            if j.hero["hp"] <= 0:
                errs.append("通关时 HP<=0")
            return (len(errs) == 0), errs
        if j.status is not None:
            errs.append("第 %d 步判 %s（HP=%d）" % (i + 1, j.status, j.hero["hp"]))
            return False, errs
    errs.append("动作序列跑完仍未通关（status=%s, hp=%d）" % (j.status, j.hero["hp"]))
    return False, errs


def _snapshot(j):
    return (j.hero["x"], j.hero["y"], j.hero["hp"], tuple(j.hero["keys"]),
            j.gates_flipped, j.hero["jumps"], j.hero["throws"], j.hero["bombs"],
            tuple(sorted(j.bombs.items())),
            tuple(tuple(row) for row in j.terrain),
            tuple(tuple(row) for row in j.occ))


def check_spawn_admission(grid, node_cap=400000):
    """返回 (ok, msgs, info)。info['endpoints'] = 满足条件的第 1 回合末坐标集合。"""
    j0 = J.Judge(grid)
    # 第 1 回合：枚举所有动作，保留零伤且存活的
    turn1 = []
    for a in ACTION_ORDER:
        j = J.Judge(grid)
        j.play(a)
        if j.status is not None:
            continue
        if j.damage_total > 1e-9 or j.hero["hp"] != 100:
            continue
        turn1.append(j)
    # 按第 1 回合末坐标去重
    by_pos = {}
    for j in turn1:
        by_pos.setdefault((j.hero["x"], j.hero["y"]), []).append(j)
    good = {}
    nodes = [0]

    def dfs(j, depth):
        nodes[0] += 1
        if nodes[0] > node_cap:
            return False
        if depth == 4:
            return True
        seen = set()
        for a in ACTION_ORDER:
            c = j.clone_for_probe()
            c.play(a)
            if c.status is not None:
                continue
            if c.damage_total > 1e-9 or c.hero["hp"] != 100:
                continue
            key = _snapshot(c)
            if key in seen:
                continue
            seen.add(key)
            if dfs(c, depth + 1):
                return True
        return False

    for pos, states in by_pos.items():
        if dfs(states[0], 1):
            good[pos] = True
    ok = len(good) >= 2
    msgs = [] if ok else ["出生 4 回合准入不足：仅 %d 个不同零伤第 1 回合末坐标" % len(good)]
    return ok, msgs, {"endpoints": sorted(good.keys()), "nodes": nodes[0]}


def _patch_judge_clone():
    def clone_for_probe(self):
        c = J.Judge.__new__(J.Judge)
        c.grid0 = [list(r) for r in self.grid0]
        c.terrain = [row[:] for row in self.terrain]
        c.occ = [row[:] for row in self.occ]
        c.clues = [row[:] for row in self.clues]
        c.mimic_binding = dict(self.mimic_binding)
        c.plate_cells = list(self.plate_cells)
        c.pair_pos = dict(self.pair_pos)
        c.turn = self.turn
        c.hero = dict(self.hero)
        c.hero["keys"] = list(self.hero["keys"])
        c.gates_flipped = self.gates_flipped
        c.bombs = dict(self.bombs)
        c.damage_total = self.damage_total
        c.status = self.status
        c.events = []
        c.trace = list(self.trace)
        c.exposed = set()
        c.tnt_armed = set()
        return c
    J.Judge.clone_for_probe = clone_for_probe


_patch_judge_clone()
