"""run_part1.py — 用本地 v2.2 裁判把 submission 的勇者跑一遍上半场 14 张真实魔王图。"""
import json
import sys

sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_07_deepseek_dsh")
import judge_v22 as J
import run_suite as RS

ROOT = r"part2_full_mode/exam_rooms\P2_07_deepseek_dsh"


def main(argv):
    mod = RS.load_sub()
    data = json.load(open(ROOT + r"\part1_dungeons_benchmark.json", encoding="utf-8"))
    only = argv[1:] or None
    tot = 0.0
    n = 0
    rows = []
    for did, d in data["dungeons"].items():
        if only and did not in only:
            continue
        if d.get("is_dq_backup"):
            continue
        g = d["grid"]
        info = {"spent_gold": d["spent_gold"], "g": (3000 - d["spent_gold"]) / 3000.0}
        r = RS.run(g, mod, did, info=info)
        rows.append(r)
        tot += r["hero_score"]
        n += 1
        print(RS.fmt(r))
        sys.stdout.flush()
    print("\n=== 勇者均分 %.2f over %d maps" % (tot / max(1, n), n))


if __name__ == "__main__":
    main(sys.argv)
