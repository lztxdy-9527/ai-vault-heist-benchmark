"""Chrono-Bastion v2.2 FULL-mode Demon Dungeon builder & adversarial tester."""

import copy
import time
import local_judge_v22 as judge
import hero_v22


def build_chrono_bastion() -> dict:
    g = judge.make_empty_grid()

    def put(x: int, y: int, t: str):
        assert 1 <= x <= 38 and 1 <= y <= 24, f"Out of inner bounds {(x, y)}"
        g[y][x] = t

    # =========================================================
    # 1. COMPACT STACKED EAST VAULTS (against free borders y=0, x=39, y=25)
    # =========================================================
    # K1 Vault: [32..38, 1..6], bottom wall y=7
    for x in range(32, 39):
        put(x, 7, "T_W")
    for y in range(1, 7):
        if y != 4:
            put(32, y, "T_W")
    put(32, 4, "P_GATE")
    put(33, 4, "PIT")
    put(34, 4, "R_GATE")

    # K1 mod-12 ICE gauntlet -> K1(34,6) -> PORTAL_1A(35,6)
    put(35, 4, "ICE")
    put(35, 1, "LASER_D")
    put(35, 2, "PIT")
    put(34, 1, "T_W")
    put(34, 2, "T_W")
    put(36, 1, "T_W")
    put(36, 2, "T_W")

    put(38, 5, "LASER2_L")
    put(37, 5, "PIT")
    put(37, 4, "T_W")
    put(38, 4, "T_W")
    put(37, 6, "T_W")
    put(38, 6, "T_W")

    put(34, 6, "K1")
    put(35, 6, "PORTAL_1A")
    put(36, 6, "T_W")  # ensures entering PORTAL_1A from left (K1 -> PORTAL_1A) moving R

    # V Vault: 1-tile-high sealed tunnel [34..38, 8] (shares top y=7, border x=39; west x=33, bottom y=9)
    put(33, 8, "T_W")
    for x in range(33, 39):
        put(x, 9, "T_W")
    put(34, 8, "PORTAL_2B")
    put(36, 8, "PIT")
    put(37, 8, "V")

    # K2 Vault: [32..38, 16..24] (top y=16, border y=25, x=39; west x=32 except y=20)
    for x in range(32, 39):
        put(x, 16, "T_W")
    for y in range(17, 25):
        if y != 20:
            put(32, y, "T_W")
    put(31, 20, "ONEWAY_R")
    put(32, 20, "PIT")
    put(33, 20, "PIT")
    put(34, 20, "B_GATE")

    # K2 guarded by ONEWAY_R + PORTAL_2A(36,22)
    put(34, 22, "K2")
    put(35, 22, "CRACK")
    put(36, 22, "PORTAL_2A")
    put(37, 22, "T_W")
    put(36, 23, "T_W")

    # =========================================================
    # 2. SNIPER SWITCH BUNKER AT (16, 13) (THROW-only double-flip!)
    # =========================================================
    put(15, 13, "ONEWAY_L")
    put(16, 13, "SWITCH")
    put(17, 13, "ONEWAY_R")
    for px in (15, 16, 17):
        put(px, 12, "T_W")
        put(px, 14, "T_W")

    # =========================================================
    # 3. WEST ARENA: Coupled 2-Box Sokoban + Dual-Laser Crossfire + PORTAL_1B Exit
    # =========================================================
    # Box 1 -> Plate 1 at (13, 3) with Sokoban obstacles
    put(7, 6, "BOX")
    put(13, 3, "PLATE")
    for wx, wy in ((6, 4), (7, 4), (8, 4), (12, 2), (14, 2), (14, 3), (12, 6), (13, 6)):
        put(wx, wy, "W")

    # Box 2 -> Plate 2 at (12, 20), later repurposed East through ONEWAY_R(31,20) into PIT(32,20)!
    put(7, 20, "BOX")
    put(12, 20, "PLATE")
    # Unbombable perpendicular LASER_D(14,15) (%3) + LASER2_U(10,24) (%4) across y=20!
    put(14, 15, "LASER_D")
    put(14, 16, "PIT")
    put(13, 15, "T_W")
    put(13, 16, "T_W")
    put(15, 15, "T_W")
    put(15, 16, "T_W")

    put(10, 24, "LASER2_U")
    put(10, 23, "PIT")
    put(9, 23, "T_W")
    put(9, 24, "T_W")
    put(11, 23, "T_W")
    put(11, 24, "T_W")

    # PORTAL_1B Exit Box at (6, 16) -> ONEWAY_R(7, 16)
    put(6, 16, "PORTAL_1B")
    put(7, 16, "ONEWAY_R")
    put(5, 16, "T_W")
    put(6, 15, "T_W")
    put(6, 17, "T_W")

    # Tempting decoy CRACK (free path risk) -> skipped by clean path
    # Keep budget crisp with high g reserve

    dec = judge.decode_grid_only(g)
    print(f"Budget: {dec['spent_gold']}G / {judge.MAX_BUDGET}G | T_W inner: {dec['counts']['T_W']} / 120")

    eng = judge.GameEngineV22(dec)
    acts = []

    def next_turn_safe(eng_obj, x, y, t):
        rays, _ = eng_obj._compute_laser_rays(t)
        return not any((x, y) in cs for _, _, _, _, cs in rays)

    def walk_to(tx: int, ty: int, allow_wait: bool = True):
        q = [(eng.hx, eng.hy, eng.turn, [])]
        seen = {(eng.hx, eng.hy, eng.turn % 12)}
        while q:
            cx, cy, ct, path = q.pop(0)
            if (cx, cy) == (tx, ty):
                for a in path:
                    acts.append(a)
                    eng.step(a)
                    assert eng.status == "ALIVE", f"walk_to dead after {a} at t={eng.turn} pos={(eng.hx, eng.hy)}"
                return
            nt = ct + 1
            if allow_wait and next_turn_safe(eng, cx, cy, nt):
                sk = (cx, cy, nt % 12)
                if sk not in seen and len(path) < 70:
                    seen.add(sk)
                    q.append((cx, cy, nt, path + ["WAIT"]))
            for d, (dx, dy) in judge.DIRECTIONS.items():
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < 40 and 0 <= ny < 26):
                    continue
                tt = eng.terrain[ny][nx]
                if tt in ("W", "T_W", "PIT", "SWITCH", "CRACK", "HEAL", "MIMIC", "ICE") or tt in judge.ALL_LASER_DIRS or tt in judge.PORTAL_PAIRS:
                    continue
                if tt == "R_GATE" and not eng.gates_flipped:
                    continue
                if tt == "B_GATE" and eng.gates_flipped:
                    continue
                if tt == "P_GATE" and not eng.is_plates_active():
                    continue
                if tt in judge.ONEWAY_DIRS and d != judge.ONEWAY_DIRS[tt]:
                    continue
                if eng.occupant[ny][nx] in ("BOX", "TNT"):
                    continue
                if not next_turn_safe(eng, cx, cy, nt) or not next_turn_safe(eng, nx, ny, nt):
                    continue
                sk = (nx, ny, nt % 12)
                if sk not in seen and len(path) < 70:
                    seen.add(sk)
                    q.append((nx, ny, nt, path + [f"MOVE_{d}"]))
        raise RuntimeError(f"walk_to failed from {(eng.hx, eng.hy)} to {(tx, ty)}")

    def safe_step(act: str, wait_laser_xy=None):
        if wait_laser_xy is not None:
            for _ in range(12):
                probe = copy.deepcopy(eng)
                hp0 = probe.hp
                probe.step(act)
                if probe.status in ("ALIVE", "CLEARED") and probe.hp == hp0:
                    # Also ensure landing tile stays safe on t+2 before exiting if inside a beam
                    if probe.status == "CLEARED" or next_turn_safe(probe, probe.hx, probe.hy, eng.turn + 2):
                        break
                if not next_turn_safe(eng, eng.hx, eng.hy, eng.turn + 1):
                    raise RuntimeError(f"Unsafe to wait on {(eng.hx, eng.hy)} before {act} t={eng.turn+1}")
                acts.append("WAIT")
                eng.step("WAIT")
                assert eng.status == "ALIVE", f"Dead while waiting at t={eng.turn} pos={(eng.hx, eng.hy)}"
        acts.append(act)
        eng.step(act)
        assert eng.status in ("ALIVE", "CLEARED"), f"Dead after {act} at t={eng.turn} pos={(eng.hx, eng.hy)}"

    # 1. Push Box 1 (7,6) -> (11,6) -> (11,3) -> (13,3) PLATE_1
    walk_to(6, 6)
    for _ in range(4):
        safe_step("MOVE_R", wait_laser_xy=(eng.hx + 1, eng.hy))
    walk_to(11, 7)
    for _ in range(3):
        safe_step("MOVE_U", wait_laser_xy=(eng.hx, eng.hy - 1))
    walk_to(10, 3)
    for _ in range(2):
        safe_step("MOVE_R", wait_laser_xy=(eng.hx + 1, eng.hy))

    # 2. Push Box 2 (7,20) -> (12,20) PLATE_2
    walk_to(6, 20)
    for _ in range(5):
        safe_step("MOVE_R", wait_laser_xy=(eng.hx + 1, eng.hy))

    # 3. Flip SWITCH(16,13) False->True via THROW_R at (14,13)
    walk_to(14, 13)
    safe_step("THROW_R")

    # 4. Enter K1 Vault via (32,4)=P_GATE -> JUMP_R over (33,4)=PIT -> (34,4)=R_GATE
    walk_to(32, 4)
    safe_step("JUMP_R")  # lands (34,4)=R_GATE
    safe_step("MOVE_R", wait_laser_xy=(35, 4))  # slides ICE(35,4)->(36,4)
    walk_to(34, 6)       # picks up K1!
    safe_step("MOVE_R", wait_laser_xy=(35, 6))  # (35,6)=PORTAL_1A -> (6,16)=PORTAL_1B -> (7,16)=ONEWAY_R

    # 5. Flip SWITCH(16,13) True->False via THROW_R at (14,13)
    walk_to(14, 13)
    safe_step("THROW_R")

    # 6. Repurpose Box 2 from PLATE_2 (12,20) -> (32,20)=PIT
    walk_to(11, 20)
    for _ in range(20):
        safe_step("MOVE_R", wait_laser_xy=(eng.hx + 1, eng.hy))

    # 7. Cross PIT_BRIDGE (32,20) -> JUMP_R over (33,20)=PIT -> B_GATE(34,20)
    walk_to(32, 20)
    safe_step("JUMP_R")  # lands (34,20)=B_GATE

    # 8. Grab K2(34,22) -> (35,22)=CRACK -> (36,22)=PORTAL_2A -> PORTAL_2B(34,8) -> (35,8) -> JUMP_R -> V(37,8)!
    walk_to(34, 22)
    safe_step("MOVE_R")  # (35,22)=CRACK
    safe_step("MOVE_R")  # (36,22)=PORTAL_2A -> (34,8)=PORTAL_2B -> (35,8)=EMPTY!
    safe_step("JUMP_R")  # jumps (36,8)=PIT -> (37,8)=V!

    print(f"Author status={eng.status} turns={eng.turn} hp={eng.hp} k={(eng.has_k1, eng.has_k2)}")
    return {
        "taunt": "Plates feed pits, switches flip twice, mod-12 waits for none.",
        "grid": g,
        "author_solution": acts,
    }


if __name__ == "__main__":
    d = build_chrono_bastion()
    vres = judge.validate_dungeon(d, check_spawn_4turn=True, check_author=True)
    print("validate_dungeon PASS:", vres)

    def test_hero(label: str, fn, budget_override=None):
        eng = judge.GameEngineV22(judge.decode_grid_only(d["grid"]))
        mem = {}
        t1 = None
        max_t2 = 0.0
        for turn in range(1, judge.MAX_TURNS + 1):
            st = eng.get_state(turn)
            ts = time.perf_counter()
            if budget_override is not None:
                act = fn(st, mem, budget_override if turn == 1 else 0.35)
            else:
                act = fn(st, mem)
            el = (time.perf_counter() - ts) * 1000.0
            if turn == 1:
                t1 = el
            else:
                max_t2 = max(max_t2, el)
            eng.step(act)
            if eng.status != "ALIVE":
                break
        hs, ds = eng.compute_scores()
        print(f"  [{label:26s}] {eng.status:8s} t={eng.turn:3d} hp={eng.hp:3d} k={(eng.has_k1, eng.has_k2)} hero={hs:5.1f} demon={ds:5.1f} t1={t1:6.1f}ms max_t2={max_t2:5.2f}ms")

    def hero_v22_5s(st, mem, b):
        if "plan" not in mem or mem.get("plan_idx", 0) >= len(mem["plan"]):
            mem["plan"] = hero_v22.solve_full_plan(st, time_budget=b)
            mem["plan_idx"] = 0
        return hero_v22.decide_action(st, mem)

    print("=== Adversarial Matrix vs Chrono-Bastion v2.2 ===")
    test_hero("HeroV22_Live_1.45s", hero_v22.decide_action)
    test_hero("HeroV22_Long_8.0s", hero_v22_5s, budget_override=8.0)
