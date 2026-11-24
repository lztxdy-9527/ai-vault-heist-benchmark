exec(open(str(__import__("pathlib").Path(__file__).resolve().parent / "dev_harness.py"), encoding="utf-8").read())
maps = load_maps()
maps["MINE"] = (S._design(), 0.7)
names = args.get("names") if isinstance(globals().get("args"), dict) and args.get("names") else list(maps)
tot = 0
for name in names:
    grid, g = maps[name]
    r = run_hero(grid, S.decide_action)
    sc = hero_score(r, g)
    tot += sc
    print(name, r["status"], r["turn"], r["hp"], r["keys"], "w1", r["w1"], "w", r["w"], "score %.1f" % sc, flush=True)
print("TOTAL", round(tot, 1))
