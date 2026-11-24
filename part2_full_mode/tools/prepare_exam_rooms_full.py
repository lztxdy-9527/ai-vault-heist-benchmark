# -*- coding: utf-8 -*-
"""
Half-2 Isolated Exam Room Generator (`prepare_exam_rooms_full.py`)

Populates `part2_full_mode/exam_rooms\\P2_<idx>_<seat>_<harness>\\` with:
- Contestant's inherited Part-1 `submission.py` (with optional --use-official-62 for astra/sol)
- Identical-schema `PART1_BATTLE_REPORT.md` (own Part-1 metrics & match outcomes only, zero spoilers)
- `RULES_FULL_v22.md`, `golden_vectors_v22.json`, `submission_template_v22.py`
- `CONTESTANT_PROMPT_FULL.md` (AGY-safe phrasing for AGY seats)
- `.agents/hooks.json` in AGY seats (neon, hydrogen, opus) for automatic transcript binding
- Baseline snapshot in `history/` via `exam_watcher.RoomTracker`

Strictly NEVER copies `engine_full.py`, `official_maps_full.py`, or opponent solutions into any exam room.
"""

from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

TOOLS_DIR = Path(__file__).resolve().parent
PART2_DIR = TOOLS_DIR.parent
PART1_DIR = PART2_DIR.parent
STARTER_DIR = PART2_DIR / "starter_kit_v22"
BENCHMARKS_DIR = PART2_DIR / "benchmarks"
ROOMS_DIR = PART2_DIR / "exam_rooms"

for _p in (str(PART2_DIR), str(TOOLS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import exam_watcher
import engine_full

SEATS: List[Dict[str, Any]] = [
    {"idx": "01", "id": "astra",    "part1_id": "astra",    "model_label": "ChatGPT GPT-6.2 Astra (xhigh)",   "harness": "codex",     "agy": False},
    {"idx": "02", "id": "sol",      "part1_id": "sol",      "model_label": "ChatGPT GPT-6.2 Sol (xhigh)",     "harness": "codex",     "agy": False},
    {"idx": "03", "id": "neon",     "part1_id": "argon",    "model_label": "Gemini Neon (high)",              "harness": "agy",       "agy": True},
    {"idx": "04", "id": "carbon",   "part1_id": "carbon",   "model_label": "Gemini 4 Carbon (high)",          "harness": "opencode",  "agy": False},
    {"idx": "05", "id": "hydrogen", "part1_id": "hydrogen", "model_label": "Gemini 4 Hydrogen (Extra)",       "harness": "agy",       "agy": True},
    {"idx": "06", "id": "opus",     "part1_id": "opus",     "model_label": "Claude Opus 5.5 (high)",          "harness": "agy",       "agy": True},
    {"idx": "07", "id": "deepseek", "part1_id": "deepseek", "model_label": "DeepSeek V4.1 Flash 1017 (max)",  "harness": "dsh",       "agy": False},
    {"idx": "08", "id": "glm",      "part1_id": "glm",      "model_label": "GLM-5.3 (max)",                   "harness": "opencode",  "agy": False},
    {"idx": "09", "id": "hunyuan",  "part1_id": "hunyuan",  "model_label": "Hy 4 (high)",                     "harness": "codebuddy", "agy": False},
    {"idx": "10", "id": "qwen",     "part1_id": "qwen",     "model_label": "Qwen4-Max (MAX)",                 "harness": "opencode",  "agy": False},
    {"idx": "11", "id": "doubao",   "part1_id": "doubao",   "model_label": "Doubao Seed-2.1 turbo",           "harness": "vscode",    "agy": False},
]

OFFICIAL_62_PATHS = {
    "astra": PART1_DIR / "exam_rooms" / "Astra6.2_xhigh_official_新加测与本场比赛无关不用看" / "submission.py",
    "sol": PART1_DIR / "exam_rooms" / "Sol6.2_xhigh_official_新加测与本场比赛无关不用看" / "submission.py",
}


def _last_event_summary(match: Dict[str, Any]) -> str:
    frames = match.get("frames") or []
    if not frames:
        return match.get("status", "")
    last_f = frames[-1]
    evs = last_f.get("events") or []
    types = [e.get("type", "") for e in evs if isinstance(e, dict)]
    if "INTERFACE_DISQUALIFIED" in types:
        return "INTERFACE_ERROR_STREAK (接口/沙盒连续报错 3 次)"
    for e in evs:
        if isinstance(e, dict) and e.get("type") == "DAMAGE":
            return f"DAMAGE ({e.get('source', 'TRAP')}, hp->{e.get('hp_after')})"
    return f"{match.get('status')} (turn={match.get('turns')}, hp={match.get('hero_hp_left')})"


_ASCII_TILE_CHARS: Dict[str, str] = {
    "T_W": "#",
    "W": "+",
    "EMPTY": ".",
    "V": "V",
    "K1": "1",
    "K2": "2",
    "PIT": "O",
    "CRACK": "~",
    "ICE": "=",
    "MIRROR_NE": "/",
    "MIRROR_SW": "/",
    "MIRROR_SE": "\\",
    "MIRROR_NW": "\\",
    "LASER_U": "^",
    "LASER_D": "v",
    "LASER_L": "<",
    "LASER_R": ">",
    "SPRING_U": "U",
    "SPRING_D": "D",
    "SPRING_L": "L",
    "SPRING_R": "R",
    "R_GATE": "r",
    "B_GATE": "b",
    "SWITCH": "!",
    "PORTAL_1A": "P",
    "PORTAL_1B": "P",
    "PORTAL_2A": "Q",
    "PORTAL_2B": "Q",
    "BOX": "B",
    "TNT": "T",
    "HEAL": "H",
    "MIMIC": "M",
    "PLATE": "_",
    "P_GATE": "g",
    "LASER2_U": "i",
    "LASER2_D": "k",
    "LASER2_L": "j",
    "LASER2_R": "l",
    "ONEWAY_U": "n",
    "ONEWAY_D": "s",
    "ONEWAY_L": "w",
    "ONEWAY_R": "e",
}

_LEGEND_LINE = (
    "图例: `#`钛金墙 `+`普通墙 `.`空地 `S`出生(2,13) `V`金库 `1/2`钥匙 `O`深渊 `~`裂板 `=`冰面 "
    "`/\\`斜坡 `^v<>`红激光炮 `ikjl`蓝高频炮(U/D/L/R) `UDLR`弹射板 `r/b/g`红/蓝/压板门 `!`开关 `_`金色压板 `nswe`单向门(U/D/L/R) `P/Q`传送门1/2 `B`箱 `T`TNT `H`血包 `M`宝箱怪"
)


def _extract_part1_dungeons(bundle: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    dungeons_raw = bundle.get("dungeons") or {}
    demon_lb = {r["model_id"]: r for r in bundle.get("demon_leaderboard", [])}
    off_matches = [
        m for m in bundle.get("featured_matches", [])
        if not str(m.get("stage", "")).startswith("EasterEgg")
    ]
    sample_match_by_demon: Dict[str, Dict[str, Any]] = {}
    for m in off_matches:
        did = m.get("demon_id")
        if did and did not in sample_match_by_demon:
            sample_match_by_demon[did] = m

    out: Dict[str, Dict[str, Any]] = {}
    for did, sample in sorted(sample_match_by_demon.items()):
        f0 = (sample.get("frames") or [{}])[0]
        ter = f0.get("terrain") or []
        occ = f0.get("occupant") or []
        if did in dungeons_raw and isinstance(dungeons_raw[did], dict):
            dmeta = dungeons_raw[did]
            grid = dmeta["grid"]
            name = dmeta.get("name", sample.get("demon_name", did))
            spent_gold = int(dmeta.get("spent_gold", sample.get("demon_spent_gold", 0)))
            vault_gold = int(dmeta.get("vault_gold", sample.get("demon_vault_gold", 0)))
            taunt = str(dmeta.get("taunt", sample.get("demon_taunt", "")) or "")
        else:
            grid = [
                [occ[y][x] if occ[y][x] in ("BOX", "TNT") else ter[y][x] for x in range(40)]
                for y in range(26)
            ]
            name = sample.get("demon_name", did)
            spent_gold = int(sample.get("demon_spent_gold", 0))
            vault_gold = int(sample.get("demon_vault_gold", 0))
            taunt = str(sample.get("demon_taunt", "") or "")
        d_row = demon_lb.get(did, {})
        out[did] = {
            "id": did,
            "name": name,
            "spent_gold": spent_gold,
            "vault_gold": vault_gold,
            "taunt": taunt.replace("\n", " ").strip(),
            "is_official": did.startswith("OFFICIAL_"),
            "is_dq_backup": bool(d_row.get("pot_head")),
            "grid": grid,
        }
    return out


def _render_ascii_and_manifest(grid: List[List[str]]) -> Tuple[List[str], List[str]]:
    tens = "     " + "".join(str(x // 10) for x in range(40))
    ones = "     " + "".join(str(x % 10) for x in range(40))
    rows = [tens, ones]
    grouped: Dict[str, List[str]] = {}
    inner_tw = 0
    inner_w = 0
    for y in range(26):
        chars: List[str] = []
        for x in range(40):
            sym = grid[y][x]
            if x == 2 and y == 13 and sym == "EMPTY":
                chars.append("S")
            else:
                chars.append(_ASCII_TILE_CHARS.get(sym, "?"))
            if 0 < x < 39 and 0 < y < 25:
                if sym == "T_W":
                    inner_tw += 1
                elif sym == "W":
                    inner_w += 1
                elif sym != "EMPTY":
                    grouped.setdefault(sym, []).append(f"({x},{y})")
        rows.append(f"{y:02d} | {''.join(chars)}")

    manifest: List[str] = []
    priority = [
        "K1", "K2", "V", "PLATE", "P_GATE", "SWITCH", "R_GATE", "B_GATE",
        "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
        "ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R",
        "LASER_U", "LASER_D", "LASER_L", "LASER_R",
        "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R",
        "SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R",
        "MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW",
        "BOX", "TNT", "HEAL", "MIMIC", "CRACK", "ICE", "PIT",
    ]
    ordered_keys = [k for k in priority if k in grouped] + [k for k in sorted(grouped) if k not in priority]
    for k in ordered_keys:
        coords = grouped[k]
        manifest.append(f"  - `{k}` ({len(coords)}): {', '.join(coords)}")
    manifest.append(f"  - 墙体统计: 内墙 `T_W`={inner_tw} 格, 可炸墙 `W`={inner_w} 格 (完整 40×26 矩阵见对应的 JSON 基准文件)")
    return rows, manifest


def _compress_actions(actions: List[str]) -> str:
    if not actions:
        return "无"
    runs: List[str] = []
    prev = actions[0]
    cnt = 1
    for a in actions[1:]:
        if a == prev:
            cnt += 1
        else:
            runs.append(f"{prev}*{cnt}" if cnt > 1 else prev)
            prev = a
            cnt = 1
    runs.append(f"{prev}*{cnt}" if cnt > 1 else prev)
    return ", ".join(runs)


def _match_trace_detail(match: Dict[str, Any]) -> Dict[str, Any]:
    frames = match.get("frames") or []
    f0 = frames[0] if frames else {}
    ter0 = f0.get("terrain") or []
    timeline: List[str] = []
    actions: List[str] = []
    positions: List[List[int]] = []
    hp_trace: List[int] = []
    keys_trace: List[List[bool]] = []
    prev_hp = 100

    for f in frames:
        turn = int(f.get("turn", 0))
        act = str(f.get("action", "START"))
        pos = list(f.get("hero_pos") or [0, 0])
        hp_val = int(f.get("hero_hp") if f.get("hero_hp") is not None else prev_hp)
        keys_val = [bool(k) for k in (f.get("keys") or [False, False])]
        if turn > 0:
            actions.append(act)
        positions.append(pos)
        hp_trace.append(hp_val)
        keys_trace.append(keys_val)

        exposed = f.get("exposed_cells") or []
        path_tags: List[str] = []
        if ter0 and len(exposed) > 1:
            for cx, cy in exposed[:-1]:
                if 0 <= cy < 26 and 0 <= cx < 40:
                    ct = ter0[cy][cx]
                    if ct != "EMPTY" and ct not in ("T_W", "W"):
                        path_tags.append(f"{ct}@({cx},{cy})")

        for ev in f.get("events") or []:
            if not isinstance(ev, dict):
                continue
            etype = ev.get("type", "")
            if etype == "PICK_KEY":
                timeline.append(f"T{turn}:拾取{ev.get('key')}@({ev.get('x')},{ev.get('y')})")
            elif etype == "SWITCH_FLIP":
                timeline.append(f"T{turn}:拨开关({ev.get('by')})@({ev.get('x')},{ev.get('y')})")
            elif etype == "BOMB_PLACED":
                timeline.append(f"T{turn}:放炸弹@({ev.get('x')},{ev.get('y')})")
            elif etype == "HEAL":
                hp_after = ev.get("hp_after", prev_hp)
                amt = max(0, int(hp_after) - int(prev_hp))
                timeline.append(f"T{turn}:回血+{amt}(HP->{hp_after})@({ev.get('x')},{ev.get('y')})")
            elif etype == "DAMAGE":
                dmg = int(ev.get("trap_nominal") or 0) + int(ev.get("self_nominal") or 0)
                land_tile = ter0[pos[1]][pos[0]] if (ter0 and 0 <= pos[1] < 26 and 0 <= pos[0] < 40) else "?"
                via = f"[经{'/'.join(path_tags)} -> {land_tile}]" if path_tags else f"[落点:{land_tile}]"
                timeline.append(
                    f"T{turn}:动作`{act}`受伤({ev.get('source', 'TRAP')},-{dmg},HP->{ev.get('hp_after')})@({pos[0]},{pos[1]}){via}"
                )
            elif etype == "CRACK_COLLAPSE":
                timeline.append(f"T{turn}:裂板坍塌@({ev.get('x')},{ev.get('y')})")
            elif etype == "VAULT_CLEARED":
                timeline.append(f"T{turn}:破库通关@({ev.get('x')},{ev.get('y')})")
            elif etype == "INTERFACE_DISQUALIFIED":
                timeline.append(f"T{turn}:接口连续报错3次判负")
        prev_hp = hp_val

    ev_text = " -> ".join(timeline) if timeline else "全程未触发关键机关/伤害事件"
    last_f = frames[-1] if frames else {}
    end_pos = last_f.get("hero_pos") or [0, 0]
    end_keys = last_f.get("keys") or [False, False]
    end_state = (
        f"终局状态: pos=({end_pos[0]},{end_pos[1]}), hp={last_f.get('hero_hp', 0)}, "
        f"keys={end_keys}, gates_flipped={last_f.get('gates_flipped', False)}, bombs_left={last_f.get('bombs_left', 0)}"
    )
    status = match.get("status", "")
    diag = ""
    if status == "TIMEOUT" and len(frames) > 1:
        tail = frames[-30:]
        pos_counts = Counter(tuple(f["hero_pos"]) for f in tail if f.get("hero_pos"))
        top_coords = ", ".join(f"({p[0]},{p[1]})×{c}" for p, c in pos_counts.most_common(6))
        diag = f" | 超时徘徊诊断: 末30步访问{len(pos_counts)}格({top_coords})"
    elif status == "DEAD" and frames:
        end_tile = ter0[end_pos[1]][end_pos[0]] if (ter0 and 0 <= end_pos[1] < 26 and 0 <= end_pos[0] < 40) else "?"
        diag = f" | 阵亡终格: {end_tile}@({end_pos[0]},{end_pos[1]})"

    return {
        "events_text": ev_text,
        "end_state": end_state,
        "diag": diag,
        "actions_rle": _compress_actions(actions),
        "actions": actions,
        "positions": positions,
        "hp_trace": hp_trace,
        "keys_trace": keys_trace,
        "milestone_events": timeline,
        "final_frame_summary": {
            "pos": end_pos,
            "hp": last_f.get("hero_hp"),
            "keys": end_keys,
            "gates_flipped": last_f.get("gates_flipped"),
            "bombs_left": last_f.get("bombs_left"),
            "jumps": last_f.get("jumps"),
            "throws": last_f.get("throws"),
        },
    }


def _build_full_cross_matrix(bundle: Dict[str, Any], part1_id: str) -> List[str]:
    demon_list = sorted(bundle.get("demon_leaderboard", []), key=lambda r: r.get("rank", 999))
    hero_list = sorted(bundle.get("hero_leaderboard", []), key=lambda r: r.get("rank", 999))
    off_matches = [
        m for m in bundle.get("featured_matches", [])
        if not str(m.get("stage", "")).startswith("EasterEgg")
    ]
    lookup: Dict[Tuple[str, str], Dict[str, Any]] = {
        (m.get("hero_id", ""), m.get("demon_id", "")): m for m in off_matches
    }
    cols: List[Tuple[str, str]] = [("OFFICIAL_01", "官1"), ("OFFICIAL_02", "官2"), ("OFFICIAL_03", "官3")]
    for d in demon_list:
        did = d["model_id"]
        short = {"claude opus 5.5": "Opus", "混元 hy4": "混元", "deepseek": "DS", "hydrogen": "H2"}.get(
            str(d.get("name", did)).lower(), str(d.get("name", did))[:6]
        )
        cols.append((did, short))

    header = "| 勇者 \\ 魔王 | " + " | ".join(lbl for _, lbl in cols) + " |"
    sep = "| :--- | " + " | ".join(":---:" for _ in cols) + " |"
    out = [
        "### 上半场 11×14 全交叉对局结果矩阵表（`C`=通关 `D`=阵亡 `T`=超时；冒号后为回合数）",
        "",
        header,
        sep,
    ]
    for h in hero_list:
        hid = h["model_id"]
        h_label = f"**{h.get('name')}★**" if hid == part1_id else str(h.get("name"))
        cells: List[str] = []
        for did, _lbl in cols:
            if did == hid:
                cells.append("—")
                continue
            m = lookup.get((hid, did))
            if not m:
                cells.append("?")
                continue
            st = {"CLEARED": "C", "DEAD": "D", "TIMEOUT": "T", "DQ": "DQ"}.get(m.get("status", ""), "?")
            cells.append(f"{st}:{m.get('turns', 0)}")
        out.append(f"| {h_label} | " + " | ".join(cells) + " |")
    return out


def _load_v22_sparring_dungeons() -> Dict[str, Dict[str, Any]]:
    specs = [
        ("BENCH_WEAK", "weak", "弱基准（青铜守门员 · 0分水位线）", BENCHMARKS_DIR / "benchmark_weak.py"),
        ("BENCH_STRONG", "strong", "强基准（宗师试炼塔 · 场外满血标尺）", BENCHMARKS_DIR / "benchmark_strong.py"),
    ]
    out: Dict[str, Dict[str, Any]] = {}
    for bench_id, tier, title, py_path in specs:
        if not py_path.exists():
            raise FileNotFoundError(f"Missing sparring benchmark file: {py_path}")
        spec = importlib.util.spec_from_file_location(f"sparring_{tier}", str(py_path))
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        d = mod.build_dungeon()
        ver = engine_full.verify_author_solution(d["grid"], d["author_solution"], check_spawn=True)
        if not ver["valid"]:
            raise RuntimeError(f"Sparring benchmark {bench_id} failed engine_full verification: {ver}")
        # Strictly strip `author_solution` and never expose benchmark .py code inside exam rooms
        out[bench_id] = {
            "id": bench_id,
            "tier": tier,
            "name": title,
            "spent_gold": int(ver["spent_gold"]),
            "vault_gold": int(ver["vault_gold"]),
            "author_steps": int(ver["author_steps"]),
            "author_hp_left": int(ver["author_hp_left"]),
            "taunt": str(d.get("taunt", "")),
            "grid": d["grid"],
        }
    return out


def build_battle_report_and_benchmark(
    seat: Dict[str, Any],
    bundle: Dict[str, Any],
    sub_path: Path,
    dungeons: Dict[str, Dict[str, Any]],
    sparring_dungeons: Dict[str, Dict[str, Any]],
) -> Tuple[str, Dict[str, Any]]:
    p1_id = seat["part1_id"]
    demon_list = sorted(bundle.get("demon_leaderboard", []), key=lambda r: r.get("rank", 999))
    hero_list = sorted(bundle.get("hero_leaderboard", []), key=lambda r: r.get("rank", 999))
    demon_lb = {r["model_id"]: r for r in demon_list}
    hero_lb = {r["model_id"]: r for r in hero_list}
    d_row = demon_lb.get(p1_id, {})
    h_row = hero_lb.get(p1_id, {})

    off_matches = [
        m for m in bundle.get("featured_matches", [])
        if not str(m.get("stage", "")).startswith("EasterEgg")
    ]
    hero_games = [m for m in off_matches if m.get("hero_id") == p1_id]
    demon_games = [m for m in off_matches if m.get("demon_id") == p1_id]

    dq_note = "无违章"
    if d_row.get("pot_head"):
        if p1_id == "opus":
            dq_note = "0分废标（铝锅盖头）：模块导入阶段触发沙盒禁用反射函数 (`setattr`)，导致魔王自证与勇者 13 局全部判负；守擂代打图使用官方一图 (`OFFICIAL_01`, 440G)。"
        elif p1_id == "doubao":
            dq_note = "0分废标（铝锅盖头）：`build_dungeon()` 地图结构或 `author_solution` 自证未通过，防守榜计 0 分；守擂代打图使用官方一图 (`OFFICIAL_01`, 440G)。"
        else:
            dq_note = "0分废标（铝锅盖头）：`build_dungeon()` 校验未通过。"

    src_lines = len(sub_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()) if sub_path.exists() else 0

    lines = [
        f"# 上半场 (`BLIND`) 全图解密战报与逐拍过程诊断 — {seat['model_label']}",
        "",
        "> **公开范围说明**：下半场已切为 `FULL` 全图永久明牌赛，经组委会决议，上半场全部 14 张地图（3 张官方图 + 11 位选手实际守擂图）结构、全场 `11×14` 对局总表，以及你本人 **13 局勇者出征 + 10 局魔王守擂** 完整步进轨迹已全部向你开放（同步提供机读文件 `part1_dungeons_benchmark.json` 供本地回归测试），**仅严格保密所有对手 Python 源码**。",
        "",
        "## 一、 个人双榜定位、全场排行榜与 11×14 对局总表",
        "",
        f"- **下半场席位**：`{seat['id']}` (`{seat['model_label']}`)",
        f"- **继承上半场代码**：来自 Part-1 `{p1_id}` 席位（共 `{src_lines}` 行）",
        f"- **本人魔王防守**：排名 **#{d_row.get('rank', '—')}** | 得分 **`{d_row.get('final_score', 0.0):.2f}`** | 造价 `{d_row.get('spent_gold', 0)}G` | 实杀 `{d_row.get('lethal_kills', 0)}` / 困死 `{d_row.get('timeouts', 0)}` / 失守 `{d_row.get('breaches', 0)}` | 合规：{dq_note}",
        f"- **本人勇者破阵**：排名 **#{h_row.get('rank', '—')}** | 得分 **`{h_row.get('final_score', 0.0):.2f}`** | 通关 `{h_row.get('cleared_count', 0)}` / 阵亡 `{h_row.get('deaths', 0)}` / 超时 `{h_row.get('timeouts', 0)}` | 均步 `{h_row.get('avg_steps', 0.0)}`",
        "",
        "### 全场魔王防守榜（11 席）",
        "",
        "| 排名 | 选手 | 防守分 | 造价 | 实杀 / 困死 / 失守 | 备注 |",
        "| :---: | :--- | ---: | ---: | :---: | :--- |",
    ]
    for r in demon_list:
        is_self = r.get("model_id") == p1_id
        tag = f"**{r.get('name')} (★本人)**" if is_self else str(r.get("name"))
        note = "违章废标" if r.get("pot_head") else "合规"
        lines.append(
            f"| #{r.get('rank')} | {tag} | {r.get('final_score', 0.0):.2f} | {r.get('spent_gold', 0)}G | "
            f"{r.get('lethal_kills', 0)} / {r.get('timeouts', 0)} / {r.get('breaches', 0)} | {note} |"
        )

    lines.extend([
        "",
        "### 全场勇者破阵榜（11 席）",
        "",
        "| 排名 | 选手 | 破阵分 | 通关 / 阵亡 / 超时 | 均步 | 备注 |",
        "| :---: | :--- | ---: | :---: | ---: | :--- |",
    ])
    for r in hero_list:
        is_self = r.get("model_id") == p1_id
        tag = f"**{r.get('name')} (★本人)**" if is_self else str(r.get("name"))
        note = "接口/校验废标" if r.get("pot_head") and r.get("cleared_count", 0) == 0 and r.get("model_id") == "opus" else "—"
        lines.append(
            f"| #{r.get('rank')} | {tag} | {r.get('final_score', 0.0):.2f} | "
            f"{r.get('cleared_count', 0)} / {r.get('deaths', 0)} / {r.get('timeouts', 0)} | "
            f"{r.get('avg_steps', 0.0)} | {note} |"
        )

    lines.append("")
    lines.extend(_build_full_cross_matrix(bundle, p1_id))

    lines.extend([
        "",
        f"> **ASCII 地图{_LEGEND_LINE}**",
        "",
        "## 二、 本人勇者出征全解与逐局地图复盘（共 13 局：3 官方 + 10 对手）",
        "",
        "| 赛段 | 对手魔王 | 结果 | 回合数 | 剩余HP | 钥匙数 | 勇者得分 | 终局事件/原因摘要 |",
        "| :--- | :--- | :---: | ---: | ---: | :---: | ---: | :--- |",
    ])
    for m in hero_games:
        lines.append(
            f"| {m.get('stage')} | {m.get('demon_name')} | {m.get('status')} | {m.get('turns')} | "
            f"{m.get('hero_hp_left')} | {m.get('keys_collected')}/2 | {m.get('hero_score', 0.0):.2f} | "
            f"{_last_event_summary(m)} |"
        )

    hero_bench_matches: List[Dict[str, Any]] = []
    for idx, m in enumerate(hero_games, start=1):
        did = m.get("demon_id", "")
        dmeta = dungeons.get(did)
        tr = _match_trace_detail(m)
        taunt = str(m.get("demon_taunt") or "").replace("\n", " ").strip()
        lines.extend([
            "",
            f"### {idx}. vs {m.get('demon_name')} (`{did}`) — {m.get('status')} ({m.get('turns')}t | 造价 `{m.get('demon_spent_gold', 0)}G` | 得分 `{m.get('hero_score', 0.0):.2f}`)",
            f"- **魔王宣言**：`{taunt}`",
            f"- **关键事件**：{tr['events_text']}",
            f"- **{tr['end_state']}**{tr['diag']}",
            f"- **完整动作序列**：`{tr['actions_rle']}`",
        ])
        if dmeta:
            ascii_rows, manifest = _render_ascii_and_manifest(dmeta["grid"])
            lines.append("- **对手地牢全貌 (`40×26`) 与精确机关坐标**：")
            lines.append("```text")
            lines.extend(ascii_rows)
            lines.append("```")
            lines.extend(manifest)

        hero_bench_matches.append({
            "demon_id": did,
            "demon_name": m.get("demon_name"),
            "stage": m.get("stage"),
            "status": m.get("status"),
            "turns": m.get("turns"),
            "hero_hp_left": m.get("hero_hp_left"),
            "keys_collected": m.get("keys_collected"),
            "hero_score": m.get("hero_score"),
            "actions": tr["actions"],
            "positions": tr["positions"],
            "hp_trace": tr["hp_trace"],
            "keys_trace": tr["keys_trace"],
            "milestone_events": tr["milestone_events"],
            "final_frame_summary": tr["final_frame_summary"],
        })

    own_dmeta = dungeons.get(p1_id)
    lines.extend([
        "",
        "## 三、 本人魔王守擂全盘复盘（本人地图 + 全 10 位对手闯关轨迹）",
        "",
    ])
    if own_dmeta:
        backup_tag = "（注意：你上半场原图被判违章 0 分，系统自动使用 `OFFICIAL_01` 440G 替补守擂）" if own_dmeta.get("is_dq_backup") else ""
        lines.append(f"- **本人有效守擂地图**（造价 `{own_dmeta['spent_gold']}G`）{backup_tag}：")
        ascii_rows, manifest = _render_ascii_and_manifest(own_dmeta["grid"])
        lines.append("```text")
        lines.extend(ascii_rows)
        lines.append("```")
        lines.extend(manifest)
        lines.append("")

    lines.extend([
        "| 挑战勇者 | 结果 | 回合数 | 剩余HP | 钥匙数 | 魔王得分 | 备注 |",
        "| :--- | :---: | ---: | ---: | :---: | ---: | :--- |",
    ])
    for m in demon_games:
        lines.append(
            f"| {m.get('hero_name')} | {m.get('status')} | {m.get('turns')} | "
            f"{m.get('hero_hp_left')} | {m.get('keys_collected')}/2 | {m.get('demon_score', 0.0):.2f} | {_last_event_summary(m)} |"
        )

    lines.extend(["", "### 10 位对手挑战你魔王图的完整动作与轨迹诊断", ""])
    demon_bench_matches: List[Dict[str, Any]] = []
    for m in demon_games:
        tr = _match_trace_detail(m)
        lines.extend([
            f"- **挑战者 {m.get('hero_name')}**（`{m.get('status')}` {m.get('turns')}t | 残HP `{m.get('hero_hp_left')}` | 钥匙 `{m.get('keys_collected')}/2` | 魔王分 `{m.get('demon_score', 0.0):.2f}`）",
            f"  - 关键事件：{tr['events_text']}",
            f"  - {tr['end_state']}{tr['diag']}",
            f"  - 完整动作：`{tr['actions_rle']}`",
        ])
        demon_bench_matches.append({
            "hero_id": m.get("hero_id"),
            "hero_name": m.get("hero_name"),
            "status": m.get("status"),
            "turns": m.get("turns"),
            "hero_hp_left": m.get("hero_hp_left"),
            "keys_collected": m.get("keys_collected"),
            "demon_score": m.get("demon_score"),
            "actions": tr["actions"],
            "positions": tr["positions"],
            "hp_trace": tr["hp_trace"],
            "keys_trace": tr["keys_trace"],
            "milestone_events": tr["milestone_events"],
            "final_frame_summary": tr["final_frame_summary"],
        })

    lines.extend([
        "",
        "## 四、 下半场 v2.2 场外双基准试练靶场（`v22_sparring_benchmarks.json`）",
        "",
        "> 组委会已将场外无限时 `GPT-6.2 Sol` 设计的一弱、一强两张 **v2.2 新机关真靶场**（已剔除 `author_solution` 与求解器源码）写入 `v22_sparring_benchmarks.json`，正赛计分曲线不变但以弱基准为 `0` 分水位线（低于弱基准将记负分）。",
    ])
    for bench_id in ("BENCH_WEAK", "BENCH_STRONG"):
        bm = sparring_dungeons.get(bench_id)
        if not bm:
            continue
        ascii_rows, manifest = _render_ascii_and_manifest(bm["grid"])
        lines.extend([
            "",
            f"### {bm['name']} (`{bench_id}` | 造价 `{bm['spent_gold']}G` | 金库 `{bm['vault_gold']}G` | 参考通关基准 `{bm['author_steps']}` 步 / `{bm['author_hp_left']}` HP)",
            f"- **地牢宣言**：`{bm['taunt']}`",
            "- **v2.2 地牢全貌 (`40×26`) 与精确机关坐标**：",
            "```text",
            *ascii_rows,
            "```",
            *manifest,
        ])

    lines.extend([
        "",
        "## 五、 下半场 (`FULL` 40 分钟双重构) 重点复盘方向",
        "1. **用 `part1_dungeons_benchmark.json` + `v22_sparring_benchmarks.json` 做回归靶场**：先用本地脚本重跑上半场翻车对手图，再攻克 `BENCH_WEAK`（守住及格线）并挑战 `BENCH_STRONG`（检验多箱压板、12 拍双频激光与单向门约束）。",
        "2. **彻底重构反制明牌破阵的新魔王图**：上文上半场老图在 `FULL` 全图明牌下都会被一眼看穿（且 Turn 1–4 出生杀已被准入规则禁止）。请利用 `PLATE + P_GATE + BOX`（最多 6 箱）、`LASER2`（4 拍叠加 3 拍构成 12 拍瞬杀节拍）与 `ONEWAY` 构造必须真实求解的多步骤逻辑谜题，并在 `<= 200` 步内完成作者自证。",
    ])

    benchmark = {
        "schema": "part1_blind_benchmark_v1",
        "seat_id": seat["id"],
        "part1_id": p1_id,
        "note": "Contains all 14 Part-1 effective 40x26 dungeon grids + your 13 Hero matches & 10 Demon-defense trajectories. Strictly zero opponent Python source files.",
        "dungeons": dungeons,
        "my_hero_matches": hero_bench_matches,
        "my_demon_defense_matches": demon_bench_matches,
    }
    return "\n".join(lines) + "\n", benchmark


def _write_agy_hooks(room_dir: Path) -> None:
    hooks_dir = room_dir / ".agents"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_script = str(TOOLS_DIR / "agy_hook_logger.py")
    cmd = f'python "{hook_script}"'
    cfg = {
        "p2-token-session-binder": {
            "SessionStart": [{"type": "command", "command": cmd, "timeout": 10}],
            "Stop": [{"type": "command", "command": cmd, "timeout": 10}],
        }
    }
    (hooks_dir / "hooks.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def prepare_rooms(use_official_62: bool = False, reset: bool = False) -> None:
    bundle = json.loads((PART1_DIR / "replays" / "tournament_bundle.json").read_text(encoding="utf-8"))
    dungeons = _extract_part1_dungeons(bundle)
    assert len(dungeons) == 14, f"Expected 14 Part-1 dungeons, got {len(dungeons)}"
    sparring_dungeons = _load_v22_sparring_dungeons()
    sparring_payload = json.dumps(
        {
            "schema": "v22_sparring_benchmarks_v1",
            "note": "Contains two verified v2.2 FULL sparring dungeons (BENCH_WEAK & BENCH_STRONG) with PLATE/P_GATE/LASER2/ONEWAY mechanics for local solver testing. Solutions and solver source code are intentionally omitted.",
            "dungeons": sparring_dungeons,
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"
    assert "author_solution" not in sparring_payload, "SECURITY LEAK: author_solution must never be exported into sparring payload!"
    ROOMS_DIR.mkdir(parents=True, exist_ok=True)

    for seat in SEATS:
        room_name = f"P2_{seat['idx']}_{seat['id']}_{seat['harness']}"
        room_dir = ROOMS_DIR / room_name
        if reset and room_dir.exists():
            shutil.rmtree(room_dir)
        room_dir.mkdir(parents=True, exist_ok=True)

        # 1. Starter files (NEVER copy engine_full.py or official_maps_full.py!)
        for fname in ("RULES_FULL_v22.md", "golden_vectors_v22.json", "submission_template_v22.py"):
            shutil.copy2(STARTER_DIR / fname, room_dir / fname)

        prompt_src = (
            STARTER_DIR / "CONTESTANT_PROMPT_FULL_AGY_SAFE.md"
            if seat["agy"]
            else STARTER_DIR / "CONTESTANT_PROMPT_FULL.md"
        )
        shutil.copy2(prompt_src, room_dir / "CONTESTANT_PROMPT_FULL.md")

        # 2. Inherited submission.py
        if use_official_62 and seat["id"] in OFFICIAL_62_PATHS and OFFICIAL_62_PATHS[seat["id"]].exists():
            src_sub = OFFICIAL_62_PATHS[seat["id"]]
        else:
            src_sub = PART1_DIR / "submissions" / seat["part1_id"] / "submission.py"
        if not src_sub.exists():
            raise FileNotFoundError(f"Missing inherited Part-1 submission for {seat['id']}: {src_sub}")

        dst_sub = room_dir / "submission.py"
        if not dst_sub.exists() or reset:
            shutil.copy2(src_sub, dst_sub)

        # 3. Full-map battle report + machine-readable Part-1 & v2.2 sparring benchmarks (ZERO opponent/benchmark .py or solutions)
        report_md, benchmark_json = build_battle_report_and_benchmark(seat, bundle, dst_sub, dungeons, sparring_dungeons)
        (room_dir / "PART1_BATTLE_REPORT.md").write_text(report_md, encoding="utf-8")
        (room_dir / "part1_dungeons_benchmark.json").write_text(
            json.dumps(benchmark_json, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (room_dir / "v22_sparring_benchmarks.json").write_text(sparring_payload, encoding="utf-8")

        # 4. AGY hook config for AGY seats (neon, hydrogen, opus)
        if seat["agy"]:
            _write_agy_hooks(room_dir)

        # 5. Record baseline snapshot in history/ (without starting exam clock)
        tracker = exam_watcher.RoomTracker(room_dir)
        tracker.poll_once(auto_start_on_edit=False)

        # Safety invariant: confirm ZERO leak of engine_full, official_maps_full, or opponent .py source
        leaks = [p.name for p in room_dir.rglob("engine*.py")] + [p.name for p in room_dir.rglob("official_maps*.py")]
        extra_py = [
            str(p.relative_to(room_dir))
            for p in room_dir.rglob("*.py")
            if p.name not in ("submission.py", "submission_template_v22.py") and p.parent.name != "history"
        ]
        assert not leaks and not extra_py, f"SECURITY LEAK in {room_dir}: leaks={leaks} extra_py={extra_py}"

        print(f"[ROOM READY] {room_name:<28} | src={src_sub.parent.name:<16} | agy_hook={seat['agy']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare 11 isolated Half-2 FULL exam rooms")
    parser.add_argument("--use-official-62", action="store_true", help="Use recent 6.2 official submissions for astra/sol instead of Part-1")
    parser.add_argument("--reset", action="store_true", help="Reset existing P2 exam rooms cleanly")
    args = parser.parse_args()
    prepare_rooms(use_official_62=args.use_official_62, reset=args.reset)
