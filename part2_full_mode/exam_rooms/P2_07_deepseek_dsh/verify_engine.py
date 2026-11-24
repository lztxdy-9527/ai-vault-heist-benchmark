"""verify_engine.py — 用上半场 23 局真实轨迹回归校验本地 v2.2 裁判内核。"""
import json
import sys

sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_07_deepseek_dsh")
import judge_v22 as J

BENCH = r"part2_full_mode/exam_rooms\P2_07_deepseek_dsh\part1_dungeons_benchmark.json"


def normalize_positions(raw):
    out = []
    for p in raw:
        if isinstance(p, dict):
            out.append(tuple(p["value"]))
        else:
            out.append(tuple(p))
    return out


def key_trace(raw):
    out = []
    for k in raw:
        if isinstance(k, dict):
            out.append(tuple(k["value"]))
        else:
            out.append(tuple(k))
    return out


def compare(tag, grid, rec, extra_solution_len=None):
    actions = rec["actions"]
    j = J.Judge(grid)
    for a in actions:
        if j.status is not None:
            break
        j.play(a)
    if j.status is None:
        j.status = "TIMEOUT" if j.turn >= 240 else "UNDONE"
    pos = normalize_positions(rec["positions"])
    hp = list(rec["hp_trace"])
    kt = key_trace(rec["keys_trace"])
    ok = True
    msgs = []
    if j.status != rec["status"]:
        ok = False
        msgs.append("status %s != %s" % (j.status, rec["status"]))
    if j.turn != rec["turns"]:
        ok = False
        msgs.append("turns %d != %d" % (j.turn, rec["turns"]))
    if j.hero["hp"] != rec["hero_hp_left"]:
        ok = False
        msgs.append("hp %d != %d" % (j.hero["hp"], rec["hero_hp_left"]))
    if min(len(pos), len(j.trace)) != len(j.trace):
        msgs.append("pos_len %d vs trace %d" % (len(pos), len(j.trace)))
    mism = 0
    first = None
    for i, tr in enumerate(j.trace):
        if i >= len(pos):
            break
        if (tr[0], tr[1]) != pos[i]:
            mism += 1
            if first is None:
                first = (i, "pos", (tr[0], tr[1]), pos[i], actions[i - 1] if i > 0 else None)
        if i < len(hp) and tr[2] != hp[i]:
            mism += 1
            if first is None:
                first = (i, "hp", tr[2], hp[i], actions[i - 1] if i > 0 else None)
        if i < len(kt) and tuple(tr[3]) != tuple(kt[i]):
            mism += 1
            if first is None:
                first = (i, "keys", tr[3], kt[i], actions[i - 1] if i > 0 else None)
    if mism:
        ok = False
        msgs.append("trace mismatch x%d first=%s" % (mism, first))
    print(("PASS " if ok else "FAIL ") + tag + ("  " + "; ".join(msgs) if msgs else ""))
    return ok


def main():
    data = json.load(open(BENCH, encoding="utf-8"))
    dungeons = data["dungeons"]
    total = 0
    passed = 0
    for rec in data["my_hero_matches"]:
        did = rec["demon_id"]
        g = dungeons[did]["grid"]
        total += 1
        passed += 1 if compare("hero vs %-14s %s t=%d" % (did, rec["status"], rec["turns"]), g, rec) else 0
    mine = data["dungeons"]["deepseek"]["grid"]
    for rec in data["my_demon_defense_matches"]:
        total += 1
        passed += 1 if compare("def  vs %-14s %s t=%d" % (rec["hero_id"], rec["status"], rec["turns"]), mine, rec) else 0
    print("\n=== %d/%d PASS" % (passed, total))


if __name__ == "__main__":
    main()
