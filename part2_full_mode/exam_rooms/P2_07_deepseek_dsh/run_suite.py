"""run_suite.py — 用本地 v2.2 裁判跑 submission.decide_action 的整局对抗回归。"""
import importlib
import json
import sys
import time
import traceback

sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_07_deepseek_dsh")
import judge_v22 as J

ROOT = r"part2_full_mode/exam_rooms\P2_07_deepseek_dsh"


def load_sub(path=None):
    if path:
        spec = importlib.util.spec_from_file_location("sub_x", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    import submission
    return submission


class Progress:
    def __init__(self, judge):
        self.j = judge
        self.best = {}

    def p(self):
        j = self.j
        keys = sum(1 for k in j.hero["keys"] if k)
        tgt = j._targets()
        hx, hy = j.hero["x"], j.hero["y"]
        if keys == 0:
            cands = [c for c in (tgt.get("K1"), tgt.get("K2")) if c]
            d = min(abs(c[0] - hx) + abs(c[1] - hy) for c in cands) if cands else 0
        elif keys == 1:
            c = tgt.get("K2") if j.hero["keys"][0] else tgt.get("K1")
            d = abs(c[0] - hx) + abs(c[1] - hy) if c else 0
        else:
            c = tgt.get("V")
            d = abs(c[0] - hx) + abs(c[1] - hy) if c else 0
        st = self.best.setdefault(keys, [d, d])
        st[0] = min(st[0], d)
        d0, dmin = st
        return keys + max(0.0, (d0 - dmin) / max(1, d0))


def run(grid, mod, name="", verbose=False, max_turns=J.MAX_TURNS, info=None):
    j = J.Judge(grid)
    prog = Progress(j)
    p = prog.p()
    memory = {}
    tmax = 0.0
    tsum = 0.0
    nt = 0
    slow = []
    err = None
    try:
        while j.status is None and j.turn < max_turns:
            st = j.observe()
            t0 = time.monotonic()
            a = mod.decide_action(st, memory)
            dt = time.monotonic() - t0
            nt += 1
            tsum += dt
            if dt > tmax:
                tmax = dt
            lim = 2.0 if st["turn"] == 1 else 0.5
            if dt > lim:
                slow.append((st["turn"], round(dt, 3)))
            j.play(a)
            p = prog.p()
    except Exception:
        err = traceback.format_exc()
    status = j.status or "UNDONE"
    g = (J.MAX_BUDGET - (info or {}).get("spent_gold", 0)) / J.MAX_BUDGET
    g = 0.0 if info is None else info.get("g", 0.0)
    hs = J.hero_score(status == "CLEARED", j.turn, j.hero["hp"], j.hero["keys"], p, g)
    ds = J.demon_score(status, j.turn, j.damage_total, p, g)
    if verbose:
        print("  events:", "; ".join(j.events[-6:]))
    return {
        "name": name, "status": status, "turns": j.turn, "hp": j.hero["hp"],
        "keys": sum(1 for k in j.hero["keys"] if k), "P": round(p, 3),
        "hero_score": round(hs, 2), "demon_score": round(ds, 2),
        "tmax": round(tmax, 3), "tavg_ms": round(1000 * tsum / max(1, nt), 2),
        "slow": slow, "err": err, "judge": j,
    }


def fmt(r):
    flag = "TIMEOUT!" if r["slow"] else ""
    line = ("%-18s %-8s T=%3d HP=%4d K=%d P=%.2f  Hero=%7.2f Demon=%7.2f  "
            "tmax=%.3fs avg=%.1fms %s" % (
                r["name"], r["status"], r["turns"], r["hp"], r["keys"], r["P"],
                r["hero_score"], r["demon_score"], r["tmax"], r["tavg_ms"], flag))
    if r["err"]:
        line += "\n  ERROR: " + r["err"].strip().splitlines()[-1]
    return line


def main(argv):
    mod = load_sub()
    data = json.load(open(ROOT + r"\v22_sparring_benchmarks.json", encoding="utf-8"))
    names = argv[1:] or ["BENCH_WEAK", "BENCH_STRONG"]
    for n in names:
        d = data["dungeons"][n]
        r = run(d["grid"], mod, n, verbose=True,
                info={"spent_gold": d["spent_gold"], "g": (3000 - d["spent_gold"]) / 3000.0})
        print(fmt(r))


if __name__ == "__main__":
    main(sys.argv)
