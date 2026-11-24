# -*- coding: utf-8 -*-
"""最终全量回归：基准双图（含记忆清空）+ 本人图 + 计时红线。"""
import sys, time, json
sys.path.insert(0, r"part2_full_mode/exam_rooms\P2_08_glm_opencode")
import submission as S
import test_full as T
import test_extra as E

W, H = 40, 26

with open(r"part2_full_mode/exam_rooms\P2_08_glm_opencode\v22_sparring_benchmarks.json", encoding="utf-8") as f:
    bench = json.load(f)

print("=== BENCH_WEAK（0 分水位线，必须通关）===")
E.run({"taunt": "", "grid": bench["dungeons"]["BENCH_WEAK"]["grid"], "author_solution": ["WAIT"]},
      label="weak")
E.run({"taunt": "", "grid": bench["dungeons"]["BENCH_WEAK"]["grid"], "author_solution": ["WAIT"]},
      wipe_every=10, label="weak+wipe10")

print("=== BENCH_STRONG（强标尺）===")
E.run({"taunt": "", "grid": bench["dungeons"]["BENCH_STRONG"]["grid"], "author_solution": ["WAIT"]},
      label="strong")
E.run({"taunt": "", "grid": bench["dungeons"]["BENCH_STRONG"]["grid"], "author_solution": ["WAIT"]},
      wipe_every=13, label="strong+wipe13")

print("=== 畸形 state 容错 ===")
bad = [{}, {"turn": 5}, {"turn": 5, "hero": {}}, {"turn": "x", "hero": {"x": None}},
       {"turn": 3, "hero": {"x": 2, "y": 13, "hp": 50, "keys": [], "jumps": 0},
        "terrain": [], "visible_mask": [], "targets": None, "clues": []}]
ok = all(S.decide_action(b, {}) in S.VALID_ACTIONS for b in bad)
print("  malformed robustness:", "PASS" if ok else "FAIL")
