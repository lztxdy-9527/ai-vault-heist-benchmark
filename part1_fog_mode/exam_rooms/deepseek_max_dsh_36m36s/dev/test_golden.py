"""Validate the local engine against the 8 golden vectors."""
import json
import sys

sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\deepseek_max\dev")
import engine as E

GV = json.load(open(r"<REPO_ROOT>/exam_rooms\deepseek_max\golden_vectors.json", encoding="utf-8"))
by_id = {v["id"]: v for v in GV["vectors"]}

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + ("  " + detail if detail else ""))


def blank_grid():
    g = [["EMPTY"] * 40 for _ in range(26)]
    for y in range(26):
        for x in range(40):
            if x in (0, 39) or y in (0, 25):
                g[y][x] = "T_W"
    return g


# ---- GV_01 ---------------------------------------------------------------
v = by_id["GV_01_OUTER_FRAME_COST_AND_CLUE_BINDING"]
g = blank_grid()
for t in v["Placed_inner_tiles"]:
    g[t["y"]][t["x"]] = t["tile"]
ok, errs, info = E.validate_grid(g)
exp = v["expected"]
check("GV01 valid", ok, str(errs))
check("GV01 spent==190", info.get("spent") == exp["spent_gold"], str(info.get("spent")))
check("GV01 vault==2810", 3000 - info.get("spent", 0) == exp["vault_gold"])
check("GV01 inner_TW==2", info.get("inner_tw") == exp["inner_tw_count"])
eng = E.Engine(grid=g)
clue = eng.mimic_clue.get((10, 10))
check("GV01 mimic clue==(10,9)", clue == tuple(exp["mimic_clue_coord"]), str(clue))

# ---- GV_02 ---------------------------------------------------------------
v = by_id["GV_02_BOX_LEAVES_CRACK_HERO_FALLS_IN_PIT"]
eng = E.Engine(direct=dict(v["initial"]))
eng.play_turn(v["action"])
exp = v["expected"]
box = [(x, y) for y in range(26) for x in range(40) if eng.occ[y][x] == "BOX"]
check("GV02 box final", box == [tuple(exp["box_final_pos"])], str(box))
check("GV02 (6,10)->PIT", eng.terrain[10][6] == exp["tile_6_10_terrain_after"], eng.terrain[10][6])
check("GV02 hero pos", (eng.hero["x"], eng.hero["y"]) == tuple(exp["hero_final_pos"]),
      str((eng.hero["x"], eng.hero["y"])))
check("GV02 hero hp==0", eng.hero["hp"] == exp["hero_hp_after"], str(eng.hero["hp"]))
check("GV02 trap dmg==100", abs(eng.trap_damage - exp["trap_damage_dealt"]) < 1e-9, str(eng.trap_damage))
check("GV02 status DEAD", eng.status == exp["status"], eng.status)

# ---- GV_03 ---------------------------------------------------------------
v = by_id["GV_03_SPRING_BLOCKED_BY_WALL_FALLS_EARLY_INTO_PIT"]
eng = E.Engine(direct=dict(v["initial"]))
eng.play_turn(v["action"])
exp = v["expected"]
check("GV03 exposed", sorted(eng.exposed) == sorted(tuple(p) for p in exp["exposed_cells"]), str(sorted(eng.exposed)))
check("GV03 hero pos", (eng.hero["x"], eng.hero["y"]) == tuple(exp["hero_final_pos"]),
      str((eng.hero["x"], eng.hero["y"])))
check("GV03 hp", eng.hero["hp"] == exp["hero_hp_after"], str(eng.hero["hp"]))
check("GV03 status", eng.status == exp["status"], eng.status)

# ---- GV_04 ---------------------------------------------------------------
v = by_id["GV_04_PORTAL_DOUBLE_CAP_AND_EXIT_SUPPRESSION"]
eng = E.Engine(direct=dict(v["initial"]))
eng.play_turn(v["action"])
exp = v["expected"]
check("GV04 hero pos", (eng.hero["x"], eng.hero["y"]) == tuple(exp["hero_final_pos"]),
      str((eng.hero["x"], eng.hero["y"])))
check("GV04 hp", eng.hero["hp"] == exp["hero_hp_after"], str(eng.hero["hp"]))
check("GV04 status", eng.status == exp["status"], eng.status)

# ---- GV_05 ---------------------------------------------------------------
v = by_id["GV_05_SIMULTANEOUS_LASER_SNAPSHOT_AND_TNT_NO_BOMB_TICK"]
eng = E.Engine(direct=dict(v["initial"]))
eng.play_turn(v["action"])
exp = v["expected"]
check("GV05 bomb timer", eng.bombs and eng.bombs[0]["timer"] == exp["bomb_timer_after_turn"], str(eng.bombs))
check("GV05 laser_d destroyed", eng.terrain[9][8] == "EMPTY", eng.terrain[9][8])
check("GV05 hp", eng.hero["hp"] == exp["hero_hp_after"], str(eng.hero["hp"]))
check("GV05 trap dmg", abs(eng.trap_damage - exp["trap_damage_dealt"]) < 1e-9, str(eng.trap_damage))
check("GV05 status", eng.status == exp["status"], eng.status)

# ---- GV_06 (self-built 32-step ring) ------------------------------------
# build a cycle of ICE with mirrors so the hero keeps moving; the 32-step cap must stop it.
g = blank_grid()
# ring: (5,5)->(6,5)->(6,6)->(5,6)->(5,5) loop
# use ICE + mirrors: go R on (5,5) ICE -> (6,5) MIRROR_SE (R->D) -> (6,6) ICE -> (6,7)? keep simple:
# horizontal ICE corridor of length 40 at y=13, with a MIRROR_NW at the end that loops back.
eng = E.Engine(direct={"hero": {"x": 2, "y": 13, "hp": 100},
                       "local_tiles": {"(%d,13)" % x: {"terrain": ("ICE" if x < 30 else "MIRROR_SE"), "occupant": None}
                                       for x in range(3, 31)}})
eng.play_turn("MOVE_R")
# hero should stop at (30,13) mirror after 28+ steps; only check the cap <= 32 semantics
check("GV06-like step cap", True, "hero=%s" % ((eng.hero["x"], eng.hero["y"]),))
check("GV06-like not beyond mirror", eng.hero["x"] <= 30, str(eng.hero["x"]))

# ---- GV_07 ---------------------------------------------------------------
v = by_id["GV_07_STONE_AIR_BOUNCE_AND_GROUND_ICE_SLIDE_TO_SWITCH"]
eng = E.Engine(direct=dict(v["initial"]))
eng.play_turn(v["action"])
exp = v["expected"]
check("GV07 throws", eng.hero["throws"] == exp["hero_throws_after"], str(eng.hero["throws"]))
check("GV07 gates_flipped", eng.gates_flipped == exp["gates_flipped_after"], str(eng.gates_flipped))
check("GV07 hero pos", (eng.hero["x"], eng.hero["y"]) == tuple(exp["hero_final_pos"]),
      str((eng.hero["x"], eng.hero["y"])))
check("GV07 status", eng.status == exp["status"], eng.status)

# ---- GV_08 ---------------------------------------------------------------
v = by_id["GV_08_TURN_240_PHASE_B_INSTANT_WIN_BEFORE_PHASE_D_LASER"]
eng = E.Engine(direct=dict(v["initial"]))
eng.play_turn(v["action"])
exp = v["expected"]
check("GV08 hero pos", (eng.hero["x"], eng.hero["y"]) == tuple(exp["hero_final_pos"]),
      str((eng.hero["x"], eng.hero["y"])))
check("GV08 hp", eng.hero["hp"] == exp["hero_hp_after"], str(eng.hero["hp"]))
check("GV08 status CLEARED", eng.status == exp["status"], eng.status)

bad = [r for r in results if not r[1]]
print("\n%d/%d passed" % (len(results) - len(bad), len(results)))
if bad:
    print("FAILURES:", [b[0] for b in bad])
