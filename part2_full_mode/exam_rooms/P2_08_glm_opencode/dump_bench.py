# -*- coding: utf-8 -*-
"""Dump v22 sparring benchmark maps as ASCII for design inspection."""
import json

CH = {
    "T_W": "#", "EMPTY": ".", "K1": "1", "K2": "2", "V": "V",
    "W": "+", "ICE": "=", "PIT": "O", "CRACK": "~",
    "MIRROR_NE": "/", "MIRROR_SE": "\\", "MIRROR_SW": "]", "MIRROR_NW": "[",
    "SPRING_U": "U", "SPRING_D": "D", "SPRING_L": "L", "SPRING_R": "R",
    "LASER_U": "^", "LASER_D": "v", "LASER_L": "<", "LASER_R": ">",
    "LASER2_U": "i", "LASER2_D": "k", "LASER2_L": "j", "LASER2_R": "l",
    "SWITCH": "!", "R_GATE": "r", "B_GATE": "b", "PLATE": "_",
    "P_GATE": "g", "ONEWAY_U": "n", "ONEWAY_D": "s", "ONEWAY_L": "w", "ONEWAY_R": "e",
    "TNT": "T", "BOX": "B", "HEAL": "H", "MIMIC": "M",
    "PORTAL_1A": "P", "PORTAL_1B": "Q", "PORTAL_2A": "A", "PORTAL_2B": "Z",
}

with open(r"part2_full_mode/exam_rooms\P2_08_glm_opencode\v22_sparring_benchmarks.json", encoding="utf-8") as f:
    data = json.load(f)

for name, d in data["dungeons"].items():
    print("=" * 60)
    print(f"{name}  spent={d['spent_gold']}G  author_steps={d['author_steps']}  taunt={d['taunt']}")
    print("    0000000000111111111122222222223333333333")
    print("    0123456789012345678901234567890123456789")
    for y, row in enumerate(d["grid"]):
        print(f"{y:2d} | " + "".join(CH.get(t, "?") for t in row) + "|")
    # itemized coordinates
    from collections import defaultdict
    items = defaultdict(list)
    for y, row in enumerate(d["grid"]):
        for x, t in enumerate(row):
            if t not in ("T_W", "EMPTY"):
                items[t].append((x, y))
    for t in sorted(items):
        print(f"  {t:10s} x{len(items[t]):2d}: {items[t]}")
