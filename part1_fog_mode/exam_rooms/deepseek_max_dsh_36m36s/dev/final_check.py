"""Final acceptance checks for submission.py"""
import re
import sys
import time

sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\deepseek_max\dev")
sys.path.insert(0, r"<REPO_ROOT>/exam_rooms\deepseek_max")

t0 = time.perf_counter()
import submission as S
imp = time.perf_counter() - t0
print("import time: %.3fs" % imp)

t0 = time.perf_counter()
d = S.build_dungeon()
bt = time.perf_counter() - t0
print("build_dungeon time: %.4fs" % bt)
print("taunt len:", len(d["taunt"]), "|", d["taunt"])
print("grid rows:", len(d["grid"]), "cols:", len(d["grid"][0]))
print("author actions:", len(d["author_solution"]))

import engine as E
ok, errs, info = E.validate_grid(d["grid"])
print("dungeon legal:", ok, errs)
print("spent:", info["spent"], "g=%.4f" % ((3000 - info["spent"]) / 3000.0),
      "inner T_W:", info["inner_tw"])
good, msg = E.check_author_solution(d["grid"], d["author_solution"])
print("author replay:", good, msg)
eng, _ = E.run_actions(d["grid"], d["author_solution"])
print("author final:", eng.status, "hp", eng.hero["hp"], "turns", eng.turn - 1)

# forbidden token scan
src = open(r"<REPO_ROOT>/exam_rooms\deepseek_max\submission.py", encoding="utf-8").read()
bad = ["open(", "os.", "pathlib", "shutil", "socket", "urllib", "requests", "subprocess",
       "multiprocessing", "threading", "sys.", "eval(", "exec(", "inspect", "ctypes",
       "pickle", "builtins", "__class__", "__globals__", "np.load", "importlib", "getattr",
       "setattr", "globals(", "locals(", "compile(", "__import__", "input(", "print("]
hits = [b for b in bad if b in src]
print("forbidden-token hits:", hits)

# decide_action timing & robustness on the real dungeon
import test_hero as T
eng, info = T.run(d["grid"])
print("our hero vs our dungeon:", info["scores"]["status"], "turns", info["scores"]["turns"],
      "max_ms=%.1f avg_ms=%.2f err=%d" % (info["max_ms"], info["avg_ms"], info["errors"]))

# degenerate state robustness
weird = {
    "turn": 1, "turns_left": 240, "mode": "BLIND",
    "hero": {"x": 2, "y": 13, "hp": 100, "keys": [False, False], "jumps": 3, "throws": 3, "bombs": 2},
    "gates_flipped": False,
    "targets": {"K1": [20, 5], "K2": [20, 20], "V": [35, 13]},
    "visible_mask": [[False] * 40 for _ in range(26)],
    "terrain": [["UNKNOWN"] * 40 for _ in range(26)],
    "occupant": [[None] * 40 for _ in range(26)],
    "bombs": [], "clues": [[False] * 40 for _ in range(26)], "laser_warnings": [],
}
print("all-unknown state ->", S.decide_action(weird, {}))
print("empty-ish state ->", S.decide_action({"turn": 5, "hero": {"x": 0, "y": 0, "hp": 10, "keys": [True, True],
                                                              "jumps": 0, "throws": 0, "bombs": 0},
                                            "gates_flipped": True, "targets": {}, "visible_mask": [],
                                            "terrain": [], "occupant": [], "clues": [],
                                            "bombs": [], "laser_warnings": []}, {}))
