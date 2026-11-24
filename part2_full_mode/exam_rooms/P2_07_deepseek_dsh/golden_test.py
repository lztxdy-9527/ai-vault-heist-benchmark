"""golden_test.py — 对 golden_vectors_v22.json 的 8 条 v2.2 边界样例逐条构造场景回归。"""
import json
import sys

sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_07_deepseek_dsh")
import judge_v22 as J

W, H = 40, 26
results = []


def mk(placements, k1=(20, 5), k2=(20, 20), v=(35, 13)):
    g = [["EMPTY"] * W for _ in range(H)]
    for x in range(W):
        g[0][x] = "T_W"
        g[H - 1][x] = "T_W"
    for y in range(H):
        g[y][0] = "T_W"
        g[y][W - 1] = "T_W"
    for (x, y, t) in placements:
        g[y][x] = t
    if k1:
        g[k1[1]][k1[0]] = "K1"
    if k2:
        g[k2[1]][k2[0]] = "K2"
    if v:
        g[v[1]][v[0]] = "V"
    return g


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + ("   " + detail if detail else ""))


# ---------------- GV22_01 预算与 P_GATE/PLATE 约束 ----------------
g = mk([(8, 8, "PLATE"), (6, 8, "BOX"), (34, 13, "P_GATE"),
        (25, 2, "LASER2_D"), (10, 13, "ONEWAY_R")])
ok, errs, info = J.validate_dungeon(g)
check("GV22_01 预算=225/金库=2775", ok and info["spent_gold"] == 225 and info["vault_gold"] == 2775,
      "spent=%d vault=%d errs=%s" % (info.get("spent_gold", -1), info.get("vault_gold", -1), errs))
j = J.Judge(g)
check("GV22_01 initial_plates_active=False", j.plates_active() is False)

# P_GATE 但有 PLATE 无 BOX -> 违章
g_bad = mk([(8, 8, "PLATE"), (34, 13, "P_GATE")])
ok2, errs2, _ = J.validate_dungeon(g_bad)
check("GV22_01b P_GATE 且 BOX=0 应违章", (not ok2) and any("P_GATE" in e for e in errs2), str(errs2))

# ---------------- GV22_02 仅 BOX 可压 PLATE ----------------
g = mk([(5, 13, "PLATE"), (34, 13, "P_GATE"), (7, 13, "BOX")])
j = J.Judge(g)
j.hero["x"], j.hero["y"] = 4, 13
j.play("MOVE_R")
check("GV22_02a 勇者踩板不激活", j.hero["x"] == 5 and j.plates_active() is False and j.is_high_wall(34, 13))
j.hero["x"], j.hero["y"], j.hero["hp"] = 8, 13, 100
j.play("MOVE_L")
j.play("MOVE_L")
box_at = [(x, y) for y in range(H) for x in range(W) if j.occ[y][x] == "BOX"]
check("GV22_02b 推箱上板 -> plates_active 且 P_GATE 开",
      j.plates_active() is True and (5, 13) in box_at and not j.is_high_wall(34, 13),
      "box=%s active=%s" % (box_at, j.plates_active()))

# ---------------- GV22_03 12 拍红蓝同帧 100 伤 ----------------
g = mk([(15, 8, "LASER_D"), (12, 10, "LASER2_R")])
j = J.Judge(g)
j.turn = 11
j.hero["x"], j.hero["y"] = 15, 10
st = j.observe()
per = sorted({w["period"] for w in st["laser_warnings"] if (w["x"], w["y"]) == (15, 10)})
check("GV22_03a 双周期预警 (15,10)", per == [3, 4], str(per))
j.play("WAIT")
check("GV22_03b 双频齐射 100 伤秒杀", j.status == "DEAD" and j.hero["hp"] <= 0,
      "hp=%d status=%s" % (j.hero["hp"], j.status))

# ---------------- GV22_04a 逆向推箱整次拒绝 ----------------
g = mk([(6, 13, "ONEWAY_L"), (6, 13, "ONEWAY_L"), (5, 13, "CRACK")])
g[13][6] = "ONEWAY_L"
g[13][5] = "CRACK"
j = J.Judge(g)
j.occ[13][6] = "BOX"
j.hero["x"], j.hero["y"] = 5, 13
j.play("MOVE_R")
box_at = [(x, y) for y in range(H) for x in range(W) if j.occ[y][x] == "BOX"]
check("GV22_04a 逆向推箱被拒/箱不动/CRACK 不塌",
      box_at == [(6, 13)] and (j.hero["x"], j.hero["y"]) == (5, 13) and j.terrain[13][5] == "CRACK",
      "box=%s hero=(%d,%d) crack=%s" % (box_at, j.hero["x"], j.hero["y"], j.terrain[13][5]))

# ---------------- GV22_04b MIRROR 先折转再用新方向验 ONEWAY ----------------
g = mk([(10, 10, "MIRROR_NE"), (10, 9, "ONEWAY_R")])
j = J.Judge(g)
j.hero["x"], j.hero["y"] = 9, 10
j.play("MOVE_R")
check("GV22_04b 斜坡折转后撞逆向单向门停稳",
      (j.hero["x"], j.hero["y"]) == (10, 10), "(%d,%d)" % (j.hero["x"], j.hero["y"]))

# ---------------- GV22_05 弹簧与跳跃的单向门交互 ----------------
g = mk([(10, 10, "SPRING_R"), (12, 10, "ONEWAY_L"), (6, 14, "ONEWAY_L")])
j = J.Judge(g)
j.hero["x"], j.hero["y"] = 9, 10
j.play("MOVE_R")
check("GV22_05a 弹簧第 2 格遇逆向门提前落停", (j.hero["x"], j.hero["y"]) == (11, 10),
      "(%d,%d)" % (j.hero["x"], j.hero["y"]))
j.hero["x"], j.hero["y"] = 5, 14
j.play("JUMP_R")
check("GV22_05b 跳越逆向门失败且消耗跳跃",
      (j.hero["x"], j.hero["y"]) == (5, 14) and j.hero["jumps"] == 2,
      "(%d,%d) jumps=%d" % (j.hero["x"], j.hero["y"], j.hero["jumps"]))

# ---------------- GV22_06 飞石空中穿透 / 落地滑行被门挡 ----------------
g = mk([(6, 10, "ONEWAY_L"), (7, 10, "SWITCH")])
j = J.Judge(g)
j.hero["x"], j.hero["y"] = 5, 10
j.play("THROW_R")
check("GV22_06a 空中穿透单向门击中开关", j.gates_flipped is True)
g = mk([(11, 15, "ICE"), (12, 15, "ONEWAY_L"), (13, 15, "SWITCH")])
j = J.Judge(g)
j.hero["x"], j.hero["y"] = 5, 15
j.play("THROW_R")
check("GV22_06b 第6格转地面滑行被单向门挡停", j.gates_flipped is False,
      "gates=%s" % j.gates_flipped)

# ---------------- GV22_07 阶段C炸箱 -> P_GATE 关门挡住激光 ----------------
g = mk([(10, 10, "PLATE"), (12, 10, "P_GATE"), (15, 10, "LASER_L")])
j = J.Judge(g)
j.occ[10][10] = "BOX"
j.turn = 2
j.hero["x"], j.hero["y"] = 7, 10
j.bombs[(9, 10)] = 1
check("GV22_07a 开局板激活", j.plates_active() is True)
j.play("WAIT")
check("GV22_07b 炸箱后板失活且激光被关门挡下",
      j.plates_active() is False and j.status is None and j.hero["hp"] == 100,
      "active=%s hp=%d events=%s" % (j.plates_active(), j.hero["hp"], j.events[-3:]))

# ---------------- GV22_08 两格深渊 + 箱子搭桥 & 计分封顶 ----------------
g = mk([(20, 13, "PIT"), (21, 13, "PIT"), (19, 13, "BOX"), (22, 13, "BOX")])
ok, errs, info = J.validate_dungeon(g)
check("GV22_08a 两格深渊+箱桥地图合法", ok, str(errs))
j = J.Judge(g)
j.hero["x"], j.hero["y"] = 18, 13
j.play("MOVE_R")            # 箱子填 (20,13)
j.hero["x"], j.hero["y"] = 23, 13
j.play("MOVE_L")            # 箱子填 (21,13)
for _ in range(3):
    j.play("MOVE_L")
check("GV22_08b 推两箱填坑后跨越",
      (j.hero["x"], j.hero["y"]) == (19, 13) and j.status in (None,) and j.hero["hp"] == 100,
      "(%d,%d) status=%s hp=%d" % (j.hero["x"], j.hero["y"], j.status, j.hero["hp"]))
s = J.demon_score("CLEARED", 240, 100.0, 2.0, 0.0)
check("GV22_08c 失守满伤拖满 240 回合魔王分=320.0", abs(s - 320.0) < 1e-9, "%.4f" % s)
check("GV22_08d author 上限 200", J.MAX_AUTHOR_STEPS == 200)

bad = [r for r in results if not r[1]]
print("\n=== %d/%d PASS" % (len(results) - len(bad), len(results)))
sys.exit(1 if bad else 0)
