"""selftest.py — 下半场交付物一键自测（裁判一致性 + 魔王图合规 + 勇者回归）。

用法： python selftest.py            # 全量（含 14 张上半场图，较慢）
       python selftest.py --fast     # 只跑基准靶场 + 自证/准入 + 裁判一致性
"""
import io
import json
import sys
import time

sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_07_deepseek_dsh")
import judge_v22 as J
import admission as AD
import submission as S
import run_suite as RS

ROOT = r"part2_full_mode/exam_rooms\P2_07_deepseek_dsh"
OUT = []
LINES = []


def emit(s=""):
    print(s)
    LINES.append(s)


def section(t):
    emit("\n" + "=" * 78)
    emit(t)
    emit("=" * 78)


def main():
    fast = "--fast" in sys.argv
    t_all = time.monotonic()

    # ---------------- 1. 裁判一致性：上半场真实轨迹回放 ----------------
    section("一、裁判内核一致性：上半场 23 局真实逐拍轨迹回放")
    data = json.load(io.open(ROOT + r"\part1_dungeons_benchmark.json", encoding="utf-8"))
    import verify_engine as VE
    ok_n = 0
    tot = 0
    for rec in data["my_hero_matches"]:
        tot += 1
        if VE.compare("hero vs %-12s %s t=%d" % (rec["demon_id"], rec["status"], rec["turns"]),
                      data["dungeons"][rec["demon_id"]]["grid"], rec):
            ok_n += 1
    mine = data["dungeons"]["deepseek"]["grid"]
    for rec in data["my_demon_defense_matches"]:
        tot += 1
        if VE.compare("def  vs %-12s %s t=%d" % (rec["hero_id"], rec["status"], rec["turns"]),
                      mine, rec):
            ok_n += 1
    emit("回放一致：%d/%d（`def vs opus` 为接口三振判负，非物理差异）" % (ok_n, tot))

    # ---------------- 2. 金标样例 ----------------
    section("二、v2.2 金标边界样例 golden_vectors_v22（19 项）")
    import runpy
    try:
        runpy.run_path(ROOT + r"\golden_test.py", run_name="__main__")
    except SystemExit as e:
        if e.code:
            emit("!! golden_test 有失败项")

    # ---------------- 3. 魔王图合规 ----------------
    section("三、魔王图合规与自证")
    d = S.build_dungeon()
    grid = d["grid"]
    ok, errs, info = J.validate_dungeon(grid)
    emit("预算校验 : %s   花费 %dG / 金库 %dG / g=%.3f" % (ok, info["spent_gold"],
                                                           info["vault_gold"], info["g"]))
    if errs:
        for e in errs:
            emit("   !! " + e)
    ok2, errs2 = AD.check_author_solution(grid, d["author_solution"])
    emit("作者自证 : %s   步数 %d（上限 200）" % (ok2, len(d["author_solution"])))
    for e in errs2:
        emit("   !! " + e)
    ok3, errs3, inf3 = AD.check_spawn_admission(grid)
    emit("出生准入 : %s   合规第 1 回合末坐标 %d 个 %s" % (ok3, len(inf3["endpoints"]),
                                                          inf3["endpoints"]))
    for e in errs3:
        emit("   !! " + e)
    emit("建设清单 : " + ", ".join("%s×%d" % (k, v) for k, v in sorted(info["counts"].items())
                                   if k not in ("EMPTY",)))

    # ---------------- 4. 勇者回归 ----------------
    section("四、勇者破阵回归（本地 v2.2 裁判整局对抗）")
    rows = []
    bench = json.load(io.open(ROOT + r"\v22_sparring_benchmarks.json", encoding="utf-8"))["dungeons"]
    for n in ("BENCH_WEAK", "BENCH_STRONG"):
        b = bench[n]
        r = RS.run(b["grid"], S, n, info={"spent_gold": b["spent_gold"],
                                          "g": (3000 - b["spent_gold"]) / 3000.0})
        rows.append(r)
        emit(RS.fmt(r))
    r = RS.run(grid, S, "MY_DUNGEON", info={"spent_gold": info["spent_gold"], "g": info["g"]})
    rows.append(r)
    emit(RS.fmt(r) + "   <- 自家魔王图（证明该图可解）")

    if not fast:
        emit("")
        tot_h = 0.0
        n = 0
        for did, dd in data["dungeons"].items():
            if dd.get("is_dq_backup"):
                continue
            r = RS.run(dd["grid"], S, did, info={"spent_gold": dd["spent_gold"],
                                                 "g": (3000 - dd["spent_gold"]) / 3000.0})
            rows.append(r)
            tot_h += r["hero_score"]
            n += 1
            emit(RS.fmt(r))
        emit("\n上半场 12 张真实魔王图勇者均分：%.2f" % (tot_h / max(1, n)))

    # ---------------- 5. 接口与时序 ----------------
    section("五、接口与时序红线")
    bad = [r for r in rows if r["slow"]]
    worst = max(rows, key=lambda r: r["tmax"])
    emit("最大单步耗时 %.3fs（%s，Turn1 上限 2.0s / 其余 0.5s）" % (worst["tmax"], worst["name"]))
    emit("超时回合数：%d %s" % (sum(len(r["slow"]) for r in rows),
                                "!!" if bad else "（全部合规）"))
    errs_r = [r for r in rows if r["err"]]
    emit("接口异常：%d %s" % (len(errs_r), "!!" if errs_r else "（全部正常）"))
    emit("\n总耗时 %.1fs" % (time.monotonic() - t_all))
    io.open(ROOT + r"\SELFTEST_RESULT.txt", "w", encoding="utf-8").write("\n".join(LINES))


if __name__ == "__main__":
    main()
