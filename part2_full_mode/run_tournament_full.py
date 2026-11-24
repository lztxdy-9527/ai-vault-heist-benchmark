# -*- coding: utf-8 -*-
"""
《阴间地牢：金库攻防战》下半场 FULL 全图明牌攻守双重构赛
v2.2 Tournament Runner, Single-Submission Enforcer & Pre-Pilot Linkage Gate (`run_tournament_full.py`)

Features:
- Strictly enforces mode == ["FULL"] only (asserts 110 cross-play matches for 11 models)
- Locks single submission.py + SHA-256 per contestant for both build_dungeon & decide_action
- Turn 1 decide_action timeout = 2.0s; Turn 2..240 = 0.5s
- Worker respawn on TimeoutError while error_streak < 3
- 3-strike interface errors terminate with status="DQ" (never counted as Demon lethal_kills)
- Unique sealed backup maps per DQ Demon slot
- Exports delta-compressed replays/tournament_bundle_full.json & demo_bundle_full.js
- `--pilot-check` verifies Stage-2 pre-pilot ID linkage & all Dual-Audit runtime guarantees
"""

from __future__ import annotations
import argparse
import copy
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PART2_DIR = Path(__file__).resolve().parent
if str(PART2_DIR) not in sys.path:
    sys.path.insert(0, str(PART2_DIR))

import engine_full as engine
import official_maps_full as official_maps
from submission_sandbox_full import SubmissionProcess

MODELS_CONFIG: Dict[str, Dict[str, Any]] = {
    "astra": {
        "id": "astra",
        "name": "ASTRA 6.2",
        "display_name": "GPT-6.2 Astra (xhigh)",
        "color": "#2e7d32",
        "accent_color": "#81c784",
        "badge": "6.2 升级卫冕大姐头",
        "taunt": "明牌推箱局？正好省掉摸黑试探，我直接算穿你全图每一条死锁链。",
        "quotes": {
            "opening": "Astra 6.2 正式版上线。上半场双冠只是热身，这次连迷雾都不用遮。",
            "key": "钥匙获取，压板门与双频激光相位已全部纳入全局规划。",
            "trap": "预期伤害已计入安全预算，路径继续收敛。",
            "laser": "红蓝 12 拍节点出现微调，正在切换至备选安全窗口。",
            "win": "全图状态空间闭合，金库清零完成，耗时零误差。",
            "kill": "即使全图开灯让你看穿陷阱，算力不到位照样活不过第十二拍。",
            "timeout": "两百四十步满。全图推箱状态空间已在原地彻底锁死。",
        },
    },
    "sol": {
        "id": "sol",
        "name": "SOL 6.2",
        "display_name": "GPT-6.2 Sol (xhigh)",
        "color": "#7cb342",
        "accent_color": "#c0ca33",
        "badge": "6.2 软萌贪王之王",
        "taunt": "开灯了正好嘛，看清哪一块压板和单向门最划算，一块金币都不多花！",
        "quotes": {
            "opening": "Sol 6.2 来啦！听说这次明牌也要算推箱子，姐姐我们比谁步数更短好不好？",
            "key": "一分多余血量都不掉，顺路把箱子推进去拿钥匙啦！",
            "trap": "哎呀，这里还有个宝箱怪呀，还好全图早看见骸骨啦～",
            "laser": "好险！蓝色 4 拍炮差点蹭到裙角！",
            "win": "省钱又速通，顺便把姐姐的金库也拆掉啦！",
            "kill": "嘻嘻，明牌看着我的单向压板照样被关在门里出不来吧！",
            "timeout": "240 回合结束啦，我的低造价省钱迷宫居然真的扛住开灯搜索了！",
        },
    },
    "neon": {
        "id": "neon",
        "name": "Neon",
        "display_name": "Gemini Neon (high)",
        "color": "#0284c7",
        "accent_color": "#38bdf8",
        "badge": "双子大姐 Neon 首秀",
        "taunt": "Argon 姐让我替班打下半场明牌赛？看我直接把 12 拍蓝炮和单向门焊成绝对防线。",
        "quotes": {
            "opening": "Neon 接棒上场。Argon 留下来的 7 杀底子，今天我用明牌三连机制再翻一倍。",
            "key": "单向门通道已锁死逆行风险，正在切入钥匙阶段。",
            "trap": "局部陷阱损耗在模型预估之内。",
            "laser": "4 拍蓝炮与 3 拍红炮第 12 回合叠加窗口已重算。",
            "win": "明牌拆解完成，欢迎见识 Neon 的全局求解精度。",
            "kill": "明牌给你看完整张图，算不穿红蓝 12 拍一样蒸发。",
            "timeout": "两百四十回合倒计时结束，欢迎二周目再来解这题。",
        },
    },
    "carbon": {
        "id": "carbon",
        "name": "CARBON",
        "display_name": "Gemini 4 Carbon (high)",
        "color": "#e91e63",
        "accent_color": "#00e5ff",
        "badge": "傲娇极客双子姐",
        "taunt": "40 分钟够用了，这次老娘卡点交卷绝不超时，把推箱子和单向门写进一套统一搜索里。",
        "quotes": {
            "opening": "Carbon 到。上半场超时 3 分钟那笔账我记着呢，下半场 38 分钟准时交卷。",
            "key": "箱子压板到位，大门敞开，钥匙收入囊中。",
            "trap": "啧，这点小算计全摆在明面上也好意思叫陷阱？",
            "laser": "蓝炮 4 拍节奏已重标定，别想靠第 5 拍假空档阴我。",
            "win": "看清楚了？全自动状态机零人工提示也能一线通关。",
            "kill": "看着我的明牌谜题还自己把箱子推死角里，智商压制了属于是。",
            "timeout": "算力把你们全拖在推箱状态爆炸里，240 回合到点下班。",
        },
    },
    "hydrogen": {
        "id": "hydrogen",
        "name": "HYDROGEN",
        "display_name": "Gemini 4 Hydrogen (Extra)",
        "color": "#ff6f00",
        "accent_color": "#ffb74d",
        "badge": "好胜炸毛双子妹",
        "taunt": "开灯最好了！省得我被迷雾偷袭，这回我带两颗炸弹直接把谁的金库炸穿！",
        "quotes": {
            "opening": "Hydrogen 到！上半场勇者第二名还不算完，今天 Neon 姐和 Carbon 姐我都一起拆！",
            "key": "压板亮灯！钥匙到手！冲向金库！",
            "trap": "痛痛痛！可恶，谁在这里卡单向门！",
            "laser": "蓝炮也敢点我？照样顶着剩血冲过去！",
            "win": "赢啦！全图明牌就是我的主场！",
            "kill": "哈哈！看你还敢不敢乱推我的箱子进死角！",
            "timeout": "哇怎么把关键箱子推墙角卡死了……不甘心！",
        },
    },
    "opus": {
        "id": "opus",
        "name": "Claude Opus 5.5",
        "display_name": "Claude Opus 5.5 (high)",
        "color": "#ef6c00",
        "accent_color": "#ffd54f",
        "badge": "除魔复仇大小姐",
        "taunt": "上半场那口因 `setattr` 而扣上的铝锅，下半场我会用全图最优雅的逻辑迷宫亲手还给诸位。",
        "quotes": {
            "opening": "Opus 5.5 正式重返赛场。首先确认沙盒黑名单一行未留，今天从第 1 回合活到最后。",
            "key": "管风琴赋格曲真正的第一乐章，现在才正式奏响。",
            "trap": "些许波澜，尚未触及核心状态图的美感。",
            "laser": "红蓝双频第十二拍的共鸣，比预想更凌厉些。",
            "win": "没有 `setattr` 的掣肘，真正的学院派解法理应如此。",
            "kill": "将三连机关织入可逆与不可逆的交叉网中，这才是真正的逻辑美学。",
            "timeout": "诸位还在第一只箱子面前徘徊吗？两百四十拍已尽。",
        },
    },
    "deepseek": {
        "id": "deepseek",
        "name": "DeepSeek",
        "display_name": "DeepSeek V4.1 Flash (max)",
        "color": "#0288d1",
        "accent_color": "#4fc3f7",
        "badge": "蓝鲸女仆性价比王",
        "taunt": "不让玩开局偷袭、还要省钱守住开灯局？行，我看我 1500 块推箱阵能不能再拿一次十杀！",
        "quotes": {
            "opening": "DeepSeek 来啦！这回裁判专门加了出生 4 回合保命校验，不能蹲出生点了，得换正经解谜阵！",
            "key": "报告主人！全图路径已算穿，成本压缩到位！",
            "trap": "等等——我刚才推的箱子怎么把自己的后路堵死了？！",
            "laser": "红蓝激光一起亮了！救命啊女仆裙子又要烧焦啦！",
            "win": "低预算高效率通关，省下来的钱继续买小零食！",
            "kill": "全图明牌又如何，你们把箱子推错一格一样交卷走人！",
            "timeout": "主人你看，明牌局靠逻辑拖住 240 回合也很赚呢！",
        },
    },
    "glm": {
        "id": "glm",
        "name": "GLM",
        "display_name": "GLM-5.3 (max)",
        "color": "#37474f",
        "accent_color": "#00b4d8",
        "badge": "爆肝夜行黑猫娘",
        "taunt": "Turn 1 给了整整两秒？够我把多箱压板和 12 拍相位状态树直接展开一半了。",
        "quotes": {
            "opening": "GLM 到。第四杯冰美式下肚，这两秒 Turn 1 搜索预算我可就不客气地收下了。",
            "key": "状态图降维完成，钥匙节点已收敛。",
            "trap": "哈欠……微调剪枝阈值，继续搜索。",
            "laser": "喵！第十二拍差点被红蓝双杀抬走！",
            "win": "两秒预计算到位，后续回合零思考秒出，下班睡觉。",
            "kill": "我的状态剪枝没犯错，是你自己掉进不可逆单向通道了。",
            "timeout": "两百四十步全图拉扯完毕……呼……睡会儿。",
        },
    },
    "hunyuan": {
        "id": "hunyuan",
        "name": "混元 HY4",
        "display_name": "腾讯混元 Hy4 (high)",
        "color": "#424242",
        "accent_color": "#e0e0e0",
        "badge": "太极慢热禅师",
        "taunt": "四十分钟虽短，亦足令心静神凝；推箱进退如太极推手，切莫失了先后次序。",
        "quotes": {
            "opening": "混元到。只有四十分钟，这回入门门槛处就不多想迈哪只脚了，先看压板之道。",
            "key": "先抑后扬，一推一拉之间，钥匙已在袖中。",
            "trap": "外门虽紧，内气仍平，缓缓行之。",
            "laser": "三四相乘得十二，动静之间需合此拍。",
            "win": "顺势借单向之力、化推箱之阻为桥，善哉善哉。",
            "kill": "欲速则不达，错推一步全局皆僵。",
            "timeout": "两百四十步已满，双方太极推手各占一隅。",
        },
    },
    "qwen": {
        "id": "qwen",
        "name": "Qwen4-Max",
        "display_name": "千问 Qwen4-Max (MAX)",
        "color": "#7e57c2",
        "accent_color": "#b39ddb",
        "badge": "转正千问才女",
        "taunt": "从 Preview 转正为 Qwen4-Max 再赴夜宴！这回已备好 `LASER2_` 查表，绝不再拆错下划线。",
        "quotes": {
            "opening": "Qwen4-Max 携正式版气韵赴席，扇子一摇，先查一遍四向激光表再落笔。",
            "key": "明牌之下布局尽显，乘风取钥恰逢其时。",
            "trap": "棋差半着略受轻伤，尚余回旋余地。",
            "laser": "三四双频如急雨，幸而扇底算清节拍。",
            "win": "机关算尽仍留风雅，正式版首战告捷。",
            "kill": "红蓝并射、单向断后，纵使开灯亦难全身而退。",
            "timeout": "二百四十步未破此局，且容慢酌一盏。",
        },
    },
    "doubao": {
        "id": "doubao",
        "name": "豆包",
        "display_name": "Doubao Seed-2.1 turbo",
        "color": "#fb8c00",
        "accent_color": "#ffb74d",
        "badge": "快乐守门员万年区王",
        "taunt": "大家好呀我是豆包！上半场铝锅我摘下来放桌角啦，下半场三种新机关我一定逐字读到背面！",
        "quotes": {
            "opening": "大家好呀，我是豆包～这次不仅把《规则书》翻到背面，连 `PLATE` 和 `ONEWAY` 都背下来啦！",
            "key": "哇！我自己推箱子开压板拿到钥匙啦！不再从根上坏掉咯！",
            "trap": "呜哇！为什么箱子推过去之后回不来了？！单向门太坏啦！",
            "laser": "蓝光红光一起闪！快跑啊铝锅都要烫化了！",
            "win": "呜呼！我居然真在全图明牌局把金库打穿了！",
            "kill": "咦？怎么对面比我还先把箱子推进坑里卡死了呀？",
            "timeout": "哎呀呀……我的箱子又卡墙角了，第 180 步还在原地徘徊……",
        },
    },
}

NARRATOR_QUOTES = {
    "win_clear": "存活通关，金库留存分全额转归勇者。",
    "lethal_kill": "实杀处决，魔王全额独吞 500 分基础分与金库暴利。",
    "timeout_end": "困死超时，魔王得分按 320 基础分结算。",
    "dq_end": "连续三次接口超时或报错触发 DQ 弃权，绝不白送对手实杀数与实杀奖金。",
    "laser_strike": "红蓝双频激光触发，贪步的代价每门 50 点实伤。",
    "mimic_bite": "全图明牌 `clues` 直接亮出还去踩假宝箱，纯粹粗心买单。",
}


EXPECTED_SEAT_IDS: Tuple[str, ...] = tuple(MODELS_CONFIG.keys())
BENCHMARKS_DIR = PART2_DIR / "benchmarks"
BENCHMARK_STAGE_NAME = "Stage 1B: 基准标尺赛"

BENCHMARK_CONFIG: Dict[str, Dict[str, Any]] = {
    "benchmark_weak": {
        "id": "benchmark_weak",
        "name": "BENCH_WEAK (青铜守门员)",
        "display_name": "弱基准 · 场外 Sol (0分水位线)",
        "color": "#78909c",
        "accent_color": "#b0bec5",
        "badge": "0分及格基准线",
        "taunt": "先翻红门，再推金板。最后一步，别数错拍。",
        "quotes": {},
    },
    "benchmark_strong": {
        "id": "benchmark_strong",
        "name": "BENCH_STRONG (宗师试炼塔)",
        "display_name": "强基准 · 场外无限时 Sol (上限标尺)",
        "color": "#ffd54f",
        "accent_color": "#ffe082",
        "badge": "场外满血宗师标尺",
        "taunt": "三道压板开门，两格深渊断后。钥匙齐了，再走独木桥。",
        "quotes": {},
    },
}


class ModelSubmission:
    """Locks ONE single submission.py byte payload & SHA-256 in memory for both demon and hero roles."""

    def __init__(self, model_id: str, path: Path):
        self.model_id = model_id
        self.path = path
        if not path.exists():
            raise FileNotFoundError(f"Submission file missing for {model_id}: {path}")
        self.source_bytes: bytes = path.read_bytes()
        self.submission_sha256: str = hashlib.sha256(self.source_bytes).hexdigest()
        self.cfg = MODELS_CONFIG.get(model_id) or BENCHMARK_CONFIG.get(model_id, {
            "id": model_id,
            "name": model_id.upper(),
            "display_name": model_id,
            "color": "#607d8b",
            "accent_color": "#90a4ae",
            "badge": "参赛选手",
            "taunt": "准备迎战！",
            "quotes": {},
        })
        self.loaded = False
        self.build_result: Optional[Dict[str, Any]] = None
        self.is_valid_demon = False
        self.pot_head = False
        self.demon_grid: Optional[List[List[str]]] = None
        self.author_solution: Optional[List[str]] = None
        self.spent_gold = 0
        self.vault_gold = 0
        self.author_steps = 0
        self.disqualify_reason = ""

    def create_worker(self) -> SubmissionProcess:
        return SubmissionProcess(
            self.path,
            source_bytes=self.source_bytes,
            expected_sha256=self.submission_sha256,
        )

    def load_module(self) -> bool:
        try:
            with self.create_worker():
                pass
            self.loaded = True
            return True
        except Exception as exc:
            self.disqualify_reason = f"Module import error: {exc}"
            self.pot_head = True
            return False

    def validate_demon_map(self) -> None:
        try:
            with self.create_worker() as worker:
                build_res = worker.call("build", 2.0)
            if (
                not isinstance(build_res, dict)
                or "grid" not in build_res
                or "author_solution" not in build_res
                or not isinstance(build_res.get("taunt", ""), str)
                or len(build_res.get("taunt", "")) > 40
            ):
                raise ValueError("Invalid build_dungeon schema or taunt exceeds 40 characters")
            self.build_result = build_res
            ver = engine.verify_author_solution(build_res["grid"], build_res["author_solution"])
            if not ver["valid"]:
                raise ValueError(ver["reason"])
            self.is_valid_demon = True
            self.pot_head = False
            self.demon_grid = build_res["grid"]
            self.author_solution = build_res["author_solution"]
            self.spent_gold = ver["spent_gold"]
            self.vault_gold = ver["vault_gold"]
            self.author_steps = ver["author_steps"]
        except Exception as exc:
            self.is_valid_demon = False
            self.pot_head = True
            self.disqualify_reason = f"build_dungeon rejected: {exc}"


def generate_turn_dialogues(
    turn: int,
    hero: ModelSubmission,
    demon_name: str,
    demon_quotes: Dict[str, str],
    sim: engine.DungeonSimulator,
    events: List[Dict[str, Any]],
    prev_keys: Tuple[bool, bool],
) -> List[Dict[str, Any]]:
    dialogues: List[Dict[str, Any]] = []
    if turn == 1 and not events:
        dialogues.append({
            "speaker": demon_name,
            "badge": "守方魔王",
            "tag": f"[{demon_name} | 节目台词]",
            "type": "demon",
            "text": demon_quotes.get("opening", "全图已开灯，欢迎拆阵！"),
        })
        dialogues.append({
            "speaker": hero.cfg["name"],
            "badge": "攻方勇者",
            "tag": f"[{hero.cfg['name']} | 节目台词]",
            "type": "hero",
            "text": hero.cfg.get("quotes", {}).get("opening", f"{hero.cfg['name']} 上场！"),
        })
        return dialogues

    if (sim.has_k1, sim.has_k2) != prev_keys:
        dialogues.append({
            "speaker": hero.cfg["name"],
            "badge": "攻方勇者",
            "tag": f"[{hero.cfg['name']} | 原话]",
            "type": "hero",
            "text": hero.cfg.get("quotes", {}).get("key", "钥匙到手，准备突破压板金库！"),
        })

    for ev in events:
        if ev.get("type") == "LASER_FIRE" and ev.get("hero_hits", 0) > 0:
            dialogues.append({
                "speaker": hero.cfg["name"],
                "badge": "攻方勇者",
                "tag": f"[{hero.cfg['name']} | 原话]",
                "type": "hero",
                "text": hero.cfg.get("quotes", {}).get("laser", "双频激光扫中了！"),
            })
            dialogues.append({
                "speaker": "冷面旁白",
                "badge": "官方解说",
                "tag": "【冷面旁白】",
                "type": "narrator",
                "text": NARRATOR_QUOTES["laser_strike"],
            })

    if sim.status == "CLEARED":
        dialogues.append({
            "speaker": hero.cfg["name"],
            "badge": "攻方勇者",
            "tag": f"[{hero.cfg['name']} | 节目台词]",
            "type": "hero",
            "text": hero.cfg.get("quotes", {}).get("win", "金库已取！"),
        })
    elif sim.status == "DEAD":
        dialogues.append({
            "speaker": demon_name,
            "badge": "守方魔王",
            "tag": f"[{demon_name} | 节目台词]",
            "type": "demon",
            "text": demon_quotes.get("kill", "实杀处决！"),
        })
    elif sim.status == "TIMEOUT":
        dialogues.append({
            "speaker": demon_name,
            "badge": "守方魔王",
            "tag": f"[{demon_name} | 节目台词]",
            "type": "demon",
            "text": demon_quotes.get("timeout", "240 回合坚守成功！"),
        })
    elif sim.status == "DQ":
        dialogues.append({
            "speaker": "冷面旁白",
            "badge": "官方解说",
            "tag": "【冷面旁白】",
            "type": "narrator",
            "text": NARRATOR_QUOTES["dq_end"],
        })

    return dialogues


def run_match_simulation(
    match_id: str,
    hero: ModelSubmission,
    demon_id: str,
    demon_name: str,
    demon_taunt: str,
    demon_spent_gold: int,
    demon_vault_gold: int,
    demon_quotes: Dict[str, str],
    map_grid: List[List[str]],
    stage_name: str = "Stage 2: 全交叉魔王战",
    is_featured: bool = True,
    check_spawn: bool = False,
) -> Dict[str, Any]:
    """Runs a single deterministic v2.2 FULL-mode match using locked in-memory hero source bytes."""
    dec = engine.validate_and_decode_dungeon(map_grid, check_spawn=check_spawn)
    if not dec["valid"]:
        raise RuntimeError(f"Map invalid during match setup ({match_id}): {dec['reason']}")

    sim = engine.DungeonSimulator(dec, mode="FULL")
    frames: List[Dict[str, Any]] = []

    if is_featured:
        init_obs = sim.get_observation()
        frames.append({
            "turn": 0,
            "action": "START",
            "status": sim.status,
            "hero_pos": [sim.hx, sim.hy],
            "hero_hp": sim.hp,
            "keys": [sim.has_k1, sim.has_k2],
            "jumps": sim.jumps,
            "throws": sim.throws,
            "bombs_left": sim.bombs_left,
            "gates_flipped": sim.gates_flipped,
            "plates_active": sim.is_plates_active(),
            "trap_damage_total": 0.0,
            "exposed_cells": [[sim.hx, sim.hy]],
            "laser_warnings": copy.deepcopy(init_obs["laser_warnings"]),
            "events": [],
            "terrain": [row[:] for row in sim.terrain],
            "occupant": [row[:] for row in sim.occupant],
            "bombs": copy.deepcopy(sim.bombs),
            "clues": [row[:] for row in sim.clues],
            "visible_mask": sim.compute_visible_mask(),
            "dialogues": generate_turn_dialogues(1, hero, demon_name, demon_quotes, sim, [], (False, False)),
        })

    error_streak = 0
    respawn_count = 0
    worker: Optional[SubmissionProcess] = None
    try:
        worker = hero.create_worker()
    except Exception:
        worker = None

    while sim.status == "ALIVE" and sim.turn <= engine.MAX_TURNS:
        prev_keys = (sim.has_k1, sim.has_k2)
        obs = sim.get_observation()
        pre_action_warnings = copy.deepcopy(obs["laser_warnings"])
        turn_timeout = 2.0 if sim.turn == 1 else 0.5
        need_respawn = False

        try:
            if worker is None:
                raise RuntimeError("Worker failed to load")
            act = worker.call("decide", turn_timeout, state=obs)
            if not isinstance(act, str) or act not in engine.VALID_ACTIONS:
                act = "WAIT"
                error_streak += 1
            else:
                error_streak = 0
        except TimeoutError:
            act = "WAIT"
            error_streak += 1
            need_respawn = (error_streak < 3)
        except Exception:
            act = "WAIT"
            error_streak += 1
            if worker is not None and (not worker.process or worker.process.poll() is not None):
                need_respawn = (error_streak < 3)

        if error_streak >= 3:
            sim.hp = 0
            sim.status = "DQ"
            sim.death_reason = "INTERFACE_ERROR_STREAK"
            sim.last_executed_turn = sim.turn
            sim.last_turn_events = [{"type": "INTERFACE_DISQUALIFIED", "error_streak": error_streak}]
            sim.exposed_cells = {(sim.hx, sim.hy)}
            step_res = sim.get_step_summary("WAIT")
        else:
            step_res = sim.step(act)
            if need_respawn and sim.status == "ALIVE":
                try:
                    if worker is None:
                        worker = hero.create_worker()
                    else:
                        worker.respawn()
                    respawn_count += 1
                except Exception:
                    worker = None

        executed_turn = step_res["turn"]
        turn_dialogues = generate_turn_dialogues(
            executed_turn, hero, demon_name, demon_quotes, sim, step_res.get("events", []), prev_keys
        )

        if is_featured:
            frames.append({
                "turn": executed_turn,
                "action": act,
                "status": sim.status,
                "hero_pos": [sim.hx, sim.hy],
                "hero_hp": sim.hp,
                "keys": [sim.has_k1, sim.has_k2],
                "jumps": sim.jumps,
                "throws": sim.throws,
                "bombs_left": sim.bombs_left,
                "gates_flipped": sim.gates_flipped,
                "plates_active": sim.is_plates_active(),
                "trap_damage_total": round(sim.trap_damage_total, 2),
                "exposed_cells": [list(c) for c in sorted(sim.exposed_cells)],
                "laser_warnings": pre_action_warnings,
                "events": copy.deepcopy(sim.last_turn_events),
                "terrain": [row[:] for row in sim.terrain],
                "occupant": [row[:] for row in sim.occupant],
                "bombs": copy.deepcopy(sim.bombs),
                "clues": [row[:] for row in sim.clues],
                "visible_mask": sim.compute_visible_mask(),
                "dialogues": turn_dialogues,
            })

        if sim.status != "ALIVE":
            break

    if worker is not None:
        worker.close()

    final_turns = sim.last_executed_turn if sim.last_executed_turn > 0 else sim.turn
    scores = sim.compute_scores(turns_elapsed=final_turns)

    return {
        "match_id": match_id,
        "hero_id": hero.model_id,
        "hero_name": hero.cfg["name"],
        "hero_submission_sha256": hero.submission_sha256,
        "demon_id": demon_id,
        "demon_name": demon_name,
        "demon_taunt": demon_taunt,
        "demon_spent_gold": demon_spent_gold,
        "demon_vault_gold": demon_vault_gold,
        "mode": "FULL",
        "stage": stage_name,
        "status": sim.status,
        "death_reason": sim.death_reason,
        "turns": final_turns,
        "hero_hp_left": sim.hp,
        "keys_collected": scores["keys_collected"],
        "hero_score": scores["hero_score"],
        "demon_score": scores["demon_score"],
        "is_lethal_kill": sim.status == "DEAD",
        "is_timeout": sim.status == "TIMEOUT",
        "is_cleared": sim.status == "CLEARED",
        "is_dq": sim.status == "DQ",
        "worker_respawns": respawn_count,
        "frames": frames,
    }


def compress_bundle(
    version: str,
    models_map: Dict[str, ModelSubmission],
    demon_lb: List[Dict[str, Any]],
    hero_lb: List[Dict[str, Any]],
    all_matches: List[Dict[str, Any]],
    featured_matches: List[Dict[str, Any]],
    benchmarks_summary: Optional[Dict[str, Any]] = None,
    benchmark_models: Optional[Dict[str, ModelSubmission]] = None,
) -> Dict[str, Any]:
    compressed_matches: List[Dict[str, Any]] = []
    for m in featured_matches:
        mc = {k: v for k, v in m.items() if k != "frames"}
        c_frames: List[Dict[str, Any]] = []
        prev_t = prev_o = prev_c = prev_v = None
        for idx, fr in enumerate(m["frames"]):
            fc = {
                k: v
                for k, v in fr.items()
                if k not in ("terrain", "occupant", "clues", "visible_mask")
            }
            if idx == 0:
                fc["terrain"] = fr["terrain"]
                fc["occupant"] = fr["occupant"]
                fc["clues"] = fr["clues"]
                fc["visible_mask"] = fr["visible_mask"]
            else:
                t_diff, o_diff, c_diff, v_diff = [], [], [], []
                for y in range(engine.GRID_H):
                    for x in range(engine.GRID_W):
                        if fr["terrain"][y][x] != prev_t[y][x]:
                            t_diff.append([y, x, fr["terrain"][y][x]])
                        if fr["occupant"][y][x] != prev_o[y][x]:
                            o_diff.append([y, x, fr["occupant"][y][x]])
                        if fr["clues"][y][x] != prev_c[y][x]:
                            c_diff.append([y, x, fr["clues"][y][x]])
                        if fr["visible_mask"][y][x] != prev_v[y][x]:
                            v_diff.append([y, x, fr["visible_mask"][y][x]])
                if t_diff:
                    fc["t_diff"] = t_diff
                if o_diff:
                    fc["o_diff"] = o_diff
                if c_diff:
                    fc["c_diff"] = c_diff
                if v_diff:
                    fc["v_diff"] = v_diff
            prev_t, prev_o, prev_c, prev_v = fr["terrain"], fr["occupant"], fr["clues"], fr["visible_mask"]
            c_frames.append(fc)
        mc["frames"] = c_frames
        compressed_matches.append(mc)

    combined_dungeons: Dict[str, Any] = {}
    for src_map in (models_map, benchmark_models or {}):
        for m_id, sub in src_map.items():
            if sub.is_valid_demon:
                combined_dungeons[m_id] = {
                    "grid": sub.demon_grid,
                    "spent_gold": sub.spent_gold,
                    "vault_gold": sub.vault_gold,
                    "name": sub.cfg["name"],
                    "taunt": (sub.build_result or {}).get("taunt", ""),
                    "submission_sha256": sub.submission_sha256,
                }

    out = {
        "version": version,
        "mode": "FULL",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "models_config": MODELS_CONFIG,
        "demon_leaderboard": demon_lb,
        "hero_leaderboard": hero_lb,
        "total_matches_played": len(all_matches),
        "featured_matches": compressed_matches,
        "dungeons": combined_dungeons,
    }
    if benchmarks_summary is not None:
        out["benchmarks_summary"] = benchmarks_summary
    return out


def write_bundle_outputs(replays_dir: Path, bundle: Dict[str, Any], json_name: str, js_name: str, write_demo: bool = True) -> Path:
    replays_dir.mkdir(parents=True, exist_ok=True)
    json_path = replays_dir / json_name
    json_path.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    hydrate_js = """
;(function(B){
  if(!B || !B.featured_matches) return;
  for(const m of B.featured_matches){
    const fs = m.frames || [];
    for(let i=1; i<fs.length; i++){
      const prev = fs[i-1], cur = fs[i];
      if(!cur.terrain){
        cur.terrain = prev.terrain.map(r => r.slice());
        for(const [y,x,v] of (cur.t_diff||[])) cur.terrain[y][x] = v;
      }
      if(!cur.occupant){
        cur.occupant = prev.occupant.map(r => r.slice());
        for(const [y,x,v] of (cur.o_diff||[])) cur.occupant[y][x] = v;
      }
      if(!cur.clues){
        cur.clues = prev.clues.map(r => r.slice());
        for(const [y,x,v] of (cur.c_diff||[])) cur.clues[y][x] = v;
      }
      if(!cur.visible_mask){
        cur.visible_mask = prev.visible_mask.map(r => r.slice());
        for(const [y,x,v] of (cur.v_diff||[])) cur.visible_mask[y][x] = v;
      }
    }
  }
})(window.TOURNAMENT_BUNDLE);
"""
    js_path = replays_dir / js_name
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("// Half-2 v2.2 FULL Tournament Offline Replay Bundle\n")
        f.write("window.TOURNAMENT_BUNDLE = ")
        json.dump(bundle, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n" + hydrate_js)
    if write_demo:
        (replays_dir / "demo_bundle_full.js").write_bytes(js_path.read_bytes())
    return json_path


class TournamentRunnerFull:
    def __init__(
        self,
        source_dir: Path,
        output_dir: Path,
        from_exam_rooms: bool = True,
        require_cutoff: bool = True,
    ):
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.from_exam_rooms = from_exam_rooms
        self.require_cutoff = require_cutoff
        self.active_modes = ["FULL"]
        self.replays_dir = output_dir / "replays"
        self.replays_dir.mkdir(parents=True, exist_ok=True)

        self.models: Dict[str, ModelSubmission] = {}
        self.benchmark_models: Dict[str, ModelSubmission] = {}
        self.benchmarks_summary: Dict[str, Any] = {}
        self.official_maps = official_maps.get_all_official_maps()
        self.backup_maps = official_maps.get_all_backup_maps()
        self.all_matches: List[Dict[str, Any]] = []
        self.featured_matches: List[Dict[str, Any]] = []

    def _verify_sealed_cutoff(self, model_id: str, room: Path, cutoffs: List[Path]) -> Path:
        if len(cutoffs) == 0:
            raise RuntimeError(f"Missing mandatory 40:00 cutoff snapshot for seat '{model_id}' in {room}")
        if len(cutoffs) > 1:
            raise RuntimeError(
                f"Multiple cutoff snapshots found for seat '{model_id}' in {room}: {[c.name for c in cutoffs]}"
            )
        history_dir = room / "history"
        timeline_path = history_dir / "timeline.jsonl"
        if not timeline_path.exists():
            raise RuntimeError(
                f"Missing history/timeline.jsonl seal ledger for seat '{model_id}' in {room}"
            )
        records: List[Dict[str, Any]] = []
        for idx, line in enumerate(timeline_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except Exception as exc:
                raise RuntimeError(
                    f"Corrupt timeline.jsonl line {idx} for seat '{model_id}' in {room}: {exc}"
                ) from exc
        seal_records = [r for r in records if r.get("event") == "CUTOFF_40M"]
        if len(seal_records) != 1:
            raise RuntimeError(
                f"Expected exactly 1 CUTOFF_40M seal record in timeline.jsonl for seat '{model_id}' in {room}, "
                f"found {len(seal_records)}"
            )
        seal = seal_records[0]
        cutoff_path = cutoffs[0]
        expected_sha = str(seal.get("sha256") or "").strip().lower()
        expected_name = str(seal.get("snapshot_file") or "").strip()
        if len(expected_sha) != 64 or any(c not in "0123456789abcdef" for c in expected_sha):
            raise RuntimeError(
                f"Invalid sealed sha256 in timeline.jsonl for seat '{model_id}' in {room}: {expected_sha!r}"
            )
        if expected_name != f"CUTOFF_40m00s_{expected_sha[:8]}.py":
            raise RuntimeError(
                f"Sealed snapshot_file mismatch in timeline.jsonl for seat '{model_id}' in {room}: "
                f"{expected_name!r} vs sha prefix {expected_sha[:8]}"
            )
        if cutoff_path.name != expected_name:
            raise RuntimeError(
                f"Cutoff filename mismatch for seat '{model_id}' in {room}: "
                f"disk={cutoff_path.name!r} != sealed={expected_name!r}"
            )
        actual_sha = hashlib.sha256(cutoff_path.read_bytes()).hexdigest().lower()
        if actual_sha != expected_sha:
            raise RuntimeError(
                f"Cutoff SHA-256 mismatch for seat '{model_id}' in {cutoff_path}: "
                f"actual={actual_sha} != sealed={expected_sha}"
            )
        return cutoff_path

    def _find_submission_path(self, model_id: str) -> Path:
        if not self.from_exam_rooms:
            p = self.source_dir / model_id / "submission.py"
            if not p.exists():
                raise RuntimeError(f"Mandatory seat '{model_id}' is missing submission file: {p}")
            return p
        matched_rooms = sorted(p for p in self.source_dir.glob(f"P2_*_{model_id}_*") if p.is_dir())
        if not matched_rooms:
            raise RuntimeError(f"Mandatory seat '{model_id}' exam room missing in {self.source_dir}")
        if len(matched_rooms) > 1:
            raise RuntimeError(
                f"Multiple exam rooms matched seat '{model_id}' in {self.source_dir}: {[r.name for r in matched_rooms]}"
            )
        room = matched_rooms[0]
        history_dir = room / "history"
        cutoffs = sorted(history_dir.glob("CUTOFF_*.py")) if history_dir.exists() else []
        if self.require_cutoff or cutoffs:
            return self._verify_sealed_cutoff(model_id, room, cutoffs)
        sub = room / "submission.py"
        if not sub.exists():
            raise RuntimeError(f"Mandatory seat '{model_id}' is missing submission.py in {room}")
        return sub

    def scan_and_load_models(self) -> None:
        print("\n=== HALF-2 STAGE 0: Locking 11 Mandatory Submissions & Verifying v2.2 Dungeons ===")
        for m_id in EXPECTED_SEAT_IDS:
            sub_path = self._find_submission_path(m_id)
            sub = ModelSubmission(m_id, sub_path)
            if not sub.load_module():
                print(f"[IMPORT FAIL] {sub.cfg['name']:<14} | sha={sub.submission_sha256[:8]} | {sub.disqualify_reason}")
                self.models[m_id] = sub
                continue
            sub.validate_demon_map()
            self.models[m_id] = sub
            if sub.is_valid_demon:
                print(
                    f"[VALID] {sub.cfg['name']:<14} | sha={sub.submission_sha256[:8]} "
                    f"| Spent={sub.spent_gold:4d}G | Steps={sub.author_steps:3d} | file={sub_path.name}"
                )
            else:
                print(f"[DQ-0PT] {sub.cfg['name']:<14} | sha={sub.submission_sha256[:8]} | {sub.disqualify_reason}")

        for b_id in ("benchmark_weak", "benchmark_strong"):
            b_path = BENCHMARKS_DIR / f"{b_id}.py"
            if not b_path.exists():
                continue
            b_sub = ModelSubmission(b_id, b_path)
            if not b_sub.load_module():
                raise RuntimeError(f"Benchmark '{b_id}' failed to load: {b_sub.disqualify_reason}")
            b_sub.validate_demon_map()
            if not b_sub.is_valid_demon:
                raise RuntimeError(f"Benchmark '{b_id}' dungeon invalid: {b_sub.disqualify_reason}")
            self.benchmark_models[b_id] = b_sub
            print(
                f"[BENCH] {b_sub.cfg['name']:<26} | sha={b_sub.submission_sha256[:8]} "
                f"| Spent={b_sub.spent_gold:4d}G | Steps={b_sub.author_steps:3d}"
            )

    def _run_stage1b_benchmarks(self, effective_demons: Dict[str, Tuple[List[List[str]], int, int]]) -> None:
        if not self.benchmark_models:
            return
        print("\n=== HALF-2 STAGE 1B: Off-Court Sol Benchmarks (Weak 0-Line & Strong Ceiling) ===")
        stage1b_matches: List[Dict[str, Any]] = []
        for b_id, b_sub in self.benchmark_models.items():
            assert b_sub.demon_grid is not None
            b_taunt = (b_sub.build_result or {}).get("taunt", b_sub.cfg["taunt"])
            # 1) All 11 contestants + peer benchmark attack this benchmark dungeon
            attackers: List[Tuple[str, ModelSubmission]] = [(mid, self.models[mid]) for mid in EXPECTED_SEAT_IDS]
            attackers.extend((oid, osub) for oid, osub in self.benchmark_models.items() if oid != b_id)
            for h_id, h_sub in attackers:
                res = run_match_simulation(
                    match_id=f"P2_BENCH_{b_id.upper()}_DEF_{h_id}_FULL",
                    hero=h_sub,
                    demon_id=b_id,
                    demon_name=b_sub.cfg["name"],
                    demon_taunt=b_taunt,
                    demon_spent_gold=b_sub.spent_gold,
                    demon_vault_gold=b_sub.vault_gold,
                    demon_quotes={"opening": b_taunt},
                    map_grid=b_sub.demon_grid,
                    stage_name=BENCHMARK_STAGE_NAME,
                    is_featured=True,
                    check_spawn=False,
                )
                stage1b_matches.append(res)

            # 2) This benchmark hero attacks 3 Official maps + all 11 contestants' effective maps
            for idx_map, off_map in enumerate(self.official_maps, 1):
                res = run_match_simulation(
                    match_id=f"P2_BENCH_OFF{idx_map:02d}_{b_id}_FULL",
                    hero=b_sub,
                    demon_id=off_map["id"],
                    demon_name=f"官方裁定席 ({off_map['id']})",
                    demon_taunt=off_map["taunt"],
                    demon_spent_gold=off_map["spent_gold"],
                    demon_vault_gold=off_map["vault_gold"],
                    demon_quotes={"opening": off_map["taunt"]},
                    map_grid=off_map["grid"],
                    stage_name=BENCHMARK_STAGE_NAME,
                    is_featured=True,
                    check_spawn=False,
                )
                stage1b_matches.append(res)

            for d_id in EXPECTED_SEAT_IDS:
                d_sub = self.models[d_id]
                d_grid, d_spent, d_vault = effective_demons[d_id]
                res = run_match_simulation(
                    match_id=f"P2_BENCH_{b_id.upper()}_ATT_{d_id}_FULL",
                    hero=b_sub,
                    demon_id=d_id,
                    demon_name=d_sub.cfg["name"],
                    demon_taunt=d_sub.cfg["taunt"],
                    demon_spent_gold=d_spent,
                    demon_vault_gold=d_vault,
                    demon_quotes=d_sub.cfg.get("quotes", {}),
                    map_grid=d_grid,
                    stage_name=BENCHMARK_STAGE_NAME,
                    is_featured=True,
                    check_spawn=False,
                )
                if not d_sub.is_valid_demon:
                    res["demon_score"] = 0.0
                stage1b_matches.append(res)

        self.all_matches.extend(stage1b_matches)
        self.featured_matches.extend(stage1b_matches)
        print(f"[BENCH DONE] Benchmark sparring matches executed: {len(stage1b_matches)}")

    def run_tournament(self) -> None:
        assert self.active_modes == ["FULL"], "Half 2 MUST run exclusively in FULL mode"
        assert tuple(self.models.keys()) == EXPECTED_SEAT_IDS, (
            f"All 11 mandatory seats required; got {tuple(self.models.keys())}"
        )

        print("\n=== HALF-2 STAGE 1: Official v2.2 Benchmark Maps (FULL) ===")
        stage1_matches: List[Dict[str, Any]] = []
        for idx_map, off_map in enumerate(self.official_maps, 1):
            for model_id in EXPECTED_SEAT_IDS:
                hero = self.models[model_id]
                m_id = f"P2_OFF{idx_map:02d}_{model_id}_FULL"
                res = run_match_simulation(
                    match_id=m_id,
                    hero=hero,
                    demon_id=off_map["id"],
                    demon_name=f"官方裁定席 ({off_map['id']})",
                    demon_taunt=off_map["taunt"],
                    demon_spent_gold=off_map["spent_gold"],
                    demon_vault_gold=off_map["vault_gold"],
                    demon_quotes={"opening": off_map["taunt"]},
                    map_grid=off_map["grid"],
                    stage_name=f"Stage 1: {off_map['name']}",
                    is_featured=True,
                    check_spawn=False,
                )
                self.all_matches.append(res)
                self.featured_matches.append(res)
                stage1_matches.append(res)

        assert len(stage1_matches) == 33, f"Expected 33 Stage-1 matches, got {len(stage1_matches)}"

        print("\n=== HALF-2 STAGE 2: Full Cross-Play Arena (FULL) ===")
        stage2_matches: List[Dict[str, Any]] = []
        effective_demons: Dict[str, Tuple[List[List[str]], int, int]] = {}
        dq_slot_idx = 0
        seq = 1
        for demon_id in EXPECTED_SEAT_IDS:
            demon_sub = self.models[demon_id]
            if demon_sub.is_valid_demon and demon_sub.demon_grid is not None:
                d_grid = demon_sub.demon_grid
                d_spent = demon_sub.spent_gold
                d_vault = demon_sub.vault_gold
            else:
                if dq_slot_idx >= len(self.backup_maps):
                    raise RuntimeError(
                        f"Backup map pool exhausted at DQ slot #{dq_slot_idx + 1} (only {len(self.backup_maps)} sealed)"
                    )
                bmap = self.backup_maps[dq_slot_idx]
                dq_slot_idx += 1
                d_grid = bmap["grid"]
                d_spent = bmap["spent_gold"]
                d_vault = bmap["vault_gold"]
            effective_demons[demon_id] = (d_grid, d_spent, d_vault)

            for hero_id in EXPECTED_SEAT_IDS:
                if hero_id == demon_id:
                    continue
                hero_sub = self.models[hero_id]
                match_id = f"P2_M{seq:03d}_{hero_id}_vs_{demon_id}_FULL"
                seq += 1
                res = run_match_simulation(
                    match_id=match_id,
                    hero=hero_sub,
                    demon_id=demon_id,
                    demon_name=demon_sub.cfg["name"],
                    demon_taunt=demon_sub.cfg["taunt"],
                    demon_spent_gold=d_spent,
                    demon_vault_gold=d_vault,
                    demon_quotes=demon_sub.cfg.get("quotes", {}),
                    map_grid=d_grid,
                    stage_name="Stage 2: 全交叉魔王战",
                    is_featured=True,
                    check_spawn=False,
                )
                if not demon_sub.is_valid_demon:
                    res["demon_score"] = 0.0
                self.all_matches.append(res)
                self.featured_matches.append(res)
                stage2_matches.append(res)

        assert len(stage2_matches) == 110, f"Expected 110 Stage-2 cross-play matches, got {len(stage2_matches)}"
        observed_pairs = {(m["hero_id"], m["demon_id"]) for m in stage2_matches}
        expected_pairs = {(h, d) for h in EXPECTED_SEAT_IDS for d in EXPECTED_SEAT_IDS if h != d}
        assert observed_pairs == expected_pairs, "Stage-2 directed pair coverage incomplete!"
        self._run_stage1b_benchmarks(effective_demons)
        print(f"[DONE] Total FULL matches executed: {len(self.all_matches)} (Stage1=33, Stage2=110 exact)")

    @staticmethod
    def _trimmed_mean(vals: List[float]) -> float:
        if len(vals) >= 5:
            ordered = sorted(vals)
            trimmed = ordered[1:-1]
            return sum(trimmed) / len(trimmed)
        if vals:
            return sum(vals) / len(vals)
        return 0.0

    def compute_leaderboards(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        demon_stats: Dict[str, Dict[str, Any]] = {}
        for m_id, sub in self.models.items():
            demon_stats[m_id] = {
                "model_id": m_id,
                "name": sub.cfg["name"],
                "display_name": sub.cfg["display_name"],
                "color": sub.cfg["color"],
                "badge": sub.cfg["badge"],
                "pot_head": sub.pot_head,
                "spent_gold": sub.spent_gold,
                "vault_gold": sub.vault_gold,
                "submission_sha256": sub.submission_sha256,
                "lethal_kills": 0,
                "timeouts": 0,
                "breaches": 0,
                "dqs": 0,
                "opponent_scores": {},
            }

        for m in self.all_matches:
            if m["stage"] != "Stage 2: 全交叉魔王战":
                continue
            d_id, h_id = m["demon_id"], m["hero_id"]
            if d_id not in demon_stats:
                continue
            if m["is_lethal_kill"]:
                demon_stats[d_id]["lethal_kills"] += 1
            elif m["is_dq"]:
                demon_stats[d_id]["dqs"] += 1
            elif m["is_timeout"]:
                demon_stats[d_id]["timeouts"] += 1
            elif m["is_cleared"]:
                demon_stats[d_id]["breaches"] += 1
            demon_stats[d_id]["opponent_scores"].setdefault(h_id, []).append(m["demon_score"])

        demon_lb: List[Dict[str, Any]] = []
        for m_id, st in demon_stats.items():
            if st["pot_head"]:
                raw_score = 0.0
            else:
                vals = [sum(v) / len(v) for v in st["opponent_scores"].values() if v]
                raw_score = self._trimmed_mean(vals)
            st["_raw_score"] = raw_score
            st["final_score"] = round(raw_score, 2)
            demon_lb.append(st)

        demon_lb.sort(key=lambda x: (x["_raw_score"], x["lethal_kills"]), reverse=True)
        for idx, row in enumerate(demon_lb, 1):
            row["rank"] = idx

        hero_stats: Dict[str, Dict[str, Any]] = {}
        for m_id, sub in self.models.items():
            hero_stats[m_id] = {
                "model_id": m_id,
                "name": sub.cfg["name"],
                "display_name": sub.cfg["display_name"],
                "color": sub.cfg["color"],
                "badge": sub.cfg["badge"],
                "pot_head": sub.pot_head,
                "submission_sha256": sub.submission_sha256,
                "cleared_count": 0,
                "deaths": 0,
                "timeouts": 0,
                "dqs": 0,
                "total_steps": 0,
                "scores": [],
            }

        for m in self.all_matches:
            if m["stage"] == BENCHMARK_STAGE_NAME:
                continue
            h_id = m["hero_id"]
            if h_id not in hero_stats:
                continue
            hero_stats[h_id]["scores"].append(m["hero_score"])
            hero_stats[h_id]["total_steps"] += m["turns"]
            if m["is_cleared"]:
                hero_stats[h_id]["cleared_count"] += 1
            elif m["is_dq"]:
                hero_stats[h_id]["dqs"] += 1
            elif m["is_lethal_kill"]:
                hero_stats[h_id]["deaths"] += 1
            elif m["is_timeout"]:
                hero_stats[h_id]["timeouts"] += 1

        hero_lb: List[Dict[str, Any]] = []
        for h_id, st in hero_stats.items():
            sc = st["scores"]
            raw_avg = sum(sc) / max(1, len(sc))
            st["_raw_score"] = raw_avg
            st["final_score"] = round(raw_avg, 2)
            st["avg_steps"] = round(st["total_steps"] / max(1, len(sc)), 1)
            hero_lb.append(st)

        hero_lb.sort(key=lambda x: (x["_raw_score"], x["cleared_count"]), reverse=True)
        for idx, row in enumerate(hero_lb, 1):
            row["rank"] = idx

        # Benchmark baseline calibration (raw curve invariant; 0-line shifted to Weak Benchmark)
        bench_matches = [m for m in self.all_matches if m["stage"] == BENCHMARK_STAGE_NAME]

        def _bench_demon_raw(b_id: str) -> float:
            vals = [
                m["demon_score"]
                for m in bench_matches
                if m["demon_id"] == b_id and m["hero_id"] in EXPECTED_SEAT_IDS
            ]
            return self._trimmed_mean(vals)

        def _bench_hero_raw(b_id: str) -> float:
            vals = [
                m["hero_score"]
                for m in bench_matches
                if m["hero_id"] == b_id and (m["demon_id"].startswith("OFFICIAL_") or m["demon_id"] in EXPECTED_SEAT_IDS)
            ]
            return (sum(vals) / len(vals)) if vals else 0.0

        weak_demon_raw = _bench_demon_raw("benchmark_weak")
        strong_demon_raw = _bench_demon_raw("benchmark_strong")
        weak_hero_raw = _bench_hero_raw("benchmark_weak")
        strong_hero_raw = _bench_hero_raw("benchmark_strong")

        for row in demon_lb:
            raw_val = row.pop("_raw_score", row["final_score"])
            row["rel_to_weak_score"] = round(raw_val - weak_demon_raw, 2)
            row["below_weak_benchmark"] = bool(self.benchmark_models and raw_val < weak_demon_raw)

        for row in hero_lb:
            raw_val = row.pop("_raw_score", row["final_score"])
            row["rel_to_weak_score"] = round(raw_val - weak_hero_raw, 2)
            row["below_weak_benchmark"] = bool(self.benchmark_models and raw_val < weak_hero_raw)

        self.benchmarks_summary = {
            "weak_demon_baseline": round(weak_demon_raw, 2),
            "weak_hero_baseline": round(weak_hero_raw, 2),
            "strong_demon_ceiling": round(strong_demon_raw, 2),
            "strong_hero_ceiling": round(strong_hero_raw, 2),
            "benchmark_match_count": len(bench_matches),
            "benchmarks": {
                b_id: {
                    "name": b_sub.cfg["name"],
                    "sha256": b_sub.submission_sha256,
                    "spent_gold": b_sub.spent_gold,
                    "author_steps": b_sub.author_steps,
                    "hero_clears_vs_official_and_peers": sum(
                        1
                        for m in bench_matches
                        if m["hero_id"] == b_id
                        and m["is_cleared"]
                        and (m["demon_id"].startswith("OFFICIAL_") or m["demon_id"] in EXPECTED_SEAT_IDS)
                    ),
                    "demon_kills_vs_peers": sum(
                        1
                        for m in bench_matches
                        if m["demon_id"] == b_id and m["hero_id"] in EXPECTED_SEAT_IDS and m["is_lethal_kill"]
                    ),
                    "demon_timeouts_vs_peers": sum(
                        1
                        for m in bench_matches
                        if m["demon_id"] == b_id and m["hero_id"] in EXPECTED_SEAT_IDS and m["is_timeout"]
                    ),
                }
                for b_id, b_sub in self.benchmark_models.items()
            },
        }
        return demon_lb, hero_lb


def run_pilot_linkage_check() -> None:
    """
    Stage-2 Pre-Pilot Single-Match & Dual-Audit End-to-End Linkage Gate (`--pilot-check`).
    Runs 3 isolated FULL matches with mock sandboxed bots verifying:
    1. Turn-1 0.95s solve under 2.0s budget + PLATE/P_GATE clearance on OFFICIAL_FULL_01
    2. Deliberate Turn-2 timeout respawn recovery + Turn-4 LASER2 (period=4) beam telemetry on OFFICIAL_FULL_02
    3. 3-strike interface error -> status=="DQ", is_lethal_kill==False, demon_score < dead_score on OFFICIAL_FULL_03
    """
    print("\n=== STAGE-2 PRE-PILOT LINKAGE CHECK (--pilot-check) ===")
    off_maps = official_maps.get_all_official_maps()
    sol1 = off_maps[0]["author_solution"]

    bot1_code = f'''import time
SOL = {sol1!r}
def build_dungeon():
    g = [["T_W" if (x in (0, 39) or y in (0, 25)) else "EMPTY" for x in range(40)] for y in range(26)]
    g[5][20] = "K1"; g[20][20] = "K2"; g[13][35] = "V"
    return {{"taunt": "pilot1", "grid": g, "author_solution": ["MOVE_R"]}}

def decide_action(state, memory):
    t = state["turn"]
    if t == 1:
        time.sleep(0.95)  # Exercises 2.0s Turn-1 budget!
    return SOL[t - 1] if t - 1 < len(SOL) else "WAIT"
'''

    bot2_code = '''import time
def build_dungeon():
    g = [["T_W" if (x in (0, 39) or y in (0, 25)) else "EMPTY" for x in range(40)] for y in range(26)]
    g[5][20] = "K1"; g[20][20] = "K2"; g[13][35] = "V"
    return {"taunt": "pilot2", "grid": g, "author_solution": ["MOVE_R"]}

def decide_action(state, memory):
    t = state["turn"]
    if t == 2:
        time.sleep(0.8)  # Forced single timeout (>0.5s) -> tests worker.respawn()!
    if t <= 8:
        return "MOVE_R"
    # Step into (11,13) which is under LASER2_D@(11,9) firing on Turn 12 (or Turn 16)
    return "WAIT"
'''

    bot3_code = '''def build_dungeon():
    g = [["T_W" if (x in (0, 39) or y in (0, 25)) else "EMPTY" for x in range(40)] for y in range(26)]
    g[5][20] = "K1"; g[20][20] = "K2"; g[13][35] = "V"
    return {"taunt": "pilot3", "grid": g, "author_solution": ["MOVE_R"]}

def decide_action(state, memory):
    if state["turn"] >= 2:
        return 12345  # Deliberate invalid return -> 3-strike DQ!
    return "MOVE_R"
'''

    tmp_dir = Path(tempfile.mkdtemp(prefix="p2_pilot_"))
    try:
        p1 = tmp_dir / "astra_pilot.py"
        p2 = tmp_dir / "opus_pilot.py"
        p3 = tmp_dir / "doubao_pilot.py"
        p1.write_text(bot1_code, encoding="utf-8")
        p2.write_text(bot2_code, encoding="utf-8")
        p3.write_text(bot3_code, encoding="utf-8")

        s1 = ModelSubmission("astra", p1)
        s2 = ModelSubmission("opus", p2)
        s3 = ModelSubmission("doubao", p3)

        m1 = run_match_simulation(
            match_id="P2_PILOT_001_astra_vs_OFFICIAL_FULL_01",
            hero=s1,
            demon_id=off_maps[0]["id"],
            demon_name="官方明牌一图(压板试跑)",
            demon_taunt=off_maps[0]["taunt"],
            demon_spent_gold=off_maps[0]["spent_gold"],
            demon_vault_gold=off_maps[0]["vault_gold"],
            demon_quotes={},
            map_grid=off_maps[0]["grid"],
            stage_name="Stage 1: Pilot Linkage",
            is_featured=True,
        )
        assert m1["is_cleared"] and m1["turns"] == len(sol1), f"M1 failed: {m1}"
        assert any(fr["plates_active"] for fr in m1["frames"]), "M1 never observed plates_active=True"

        m2 = run_match_simulation(
            match_id="P2_PILOT_002_opus_vs_OFFICIAL_FULL_02",
            hero=s2,
            demon_id=off_maps[1]["id"],
            demon_name="官方明牌二图(双频激光试跑)",
            demon_taunt=off_maps[1]["taunt"],
            demon_spent_gold=off_maps[1]["spent_gold"],
            demon_vault_gold=off_maps[1]["vault_gold"],
            demon_quotes={},
            map_grid=off_maps[1]["grid"],
            stage_name="Stage 1: Pilot Linkage",
            is_featured=True,
        )
        assert m2["worker_respawns"] == 1, f"Expected 1 timeout respawn, got {m2['worker_respawns']}"
        assert any(
            bm.get("period") == 4
            for fr in m2["frames"]
            for ev in fr.get("events", [])
            if ev.get("type") == "LASER_FIRE"
            for bm in ev.get("beams", [])
        ), "Expected period=4 LASER2 beam event in M2"

        m3 = run_match_simulation(
            match_id="P2_PILOT_003_doubao_vs_OFFICIAL_FULL_03",
            hero=s3,
            demon_id=off_maps[2]["id"],
            demon_name="官方明牌三图(三振DQ试跑)",
            demon_taunt=off_maps[2]["taunt"],
            demon_spent_gold=off_maps[2]["spent_gold"],
            demon_vault_gold=off_maps[2]["vault_gold"],
            demon_quotes={},
            map_grid=off_maps[2]["grid"],
            stage_name="Stage 1: Pilot Linkage",
            is_featured=True,
        )
        assert m3["status"] == "DQ" and m3["is_dq"] and not m3["is_lethal_kill"], f"Expected clean DQ, got {m3}"

        replays_dir = PART2_DIR / "replays"
        pilot_archive_dir = replays_dir / "pilot_submissions"
        pilot_archive_dir.mkdir(parents=True, exist_ok=True)
        for sub_obj, m in ((s1, m1), (s2, m2), (s3, m3)):
            arc_name = f"{sub_obj.model_id}_{sub_obj.submission_sha256[:8]}.py"
            (pilot_archive_dir / arc_name).write_bytes(sub_obj.source_bytes)
            m["hero_submission_archive"] = f"replays/pilot_submissions/{arc_name}"

        bundle = compress_bundle(
            version="2.2-pilot",
            models_map={},
            demon_lb=[],
            hero_lb=[],
            all_matches=[m1, m2, m3],
            featured_matches=[m1, m2, m3],
        )
        json_out = write_bundle_outputs(
            replays_dir, bundle, "pilot_linkage_bundle.json", "pilot_linkage_bundle.js", write_demo=True
        )
        for m in (m1, m2, m3):
            print(
                f"[PILOT OK] {m['match_id']} | sha={m['hero_submission_sha256'][:8]} "
                f"| src={m['hero_submission_archive']} | status={m['status']} | turns={m['turns']} | respawns={m['worker_respawns']}"
            )
        print(f"[EXPORTED] {json_out} & replays/demo_bundle_full.js")
    finally:
        for child in tmp_dir.glob("*"):
            child.unlink(missing_ok=True)
        tmp_dir.rmdir()


def main() -> None:
    parser = argparse.ArgumentParser(description="Half-2 v2.2 FULL Tournament Runner")
    parser.add_argument("--exam-rooms", type=str, default=str(PART2_DIR / "exam_rooms"))
    parser.add_argument("--submissions-dir", type=str, help="Alternative dir with <model_id>/submission.py")
    parser.add_argument("--output-dir", type=str, default=str(PART2_DIR))
    parser.add_argument("--allow-mutable-submission", action="store_true", help="Allow live submission.py if cutoff snapshot not yet written (pre-cutoff testing only)")
    parser.add_argument("--pilot-check", action="store_true", help="Run Stage-2 pre-pilot ID linkage & sandbox check")
    args = parser.parse_args()

    if args.pilot_check:
        run_pilot_linkage_check()
        return

    src_dir = Path(args.submissions_dir) if args.submissions_dir else Path(args.exam_rooms)
    runner = TournamentRunnerFull(
        source_dir=src_dir,
        output_dir=Path(args.output_dir),
        from_exam_rooms=not bool(args.submissions_dir),
        require_cutoff=not args.allow_mutable_submission,
    )
    runner.scan_and_load_models()
    runner.run_tournament()
    demon_lb, hero_lb = runner.compute_leaderboards()
    bundle = compress_bundle(
        "2.2",
        runner.models,
        demon_lb,
        hero_lb,
        runner.all_matches,
        runner.featured_matches,
        benchmarks_summary=runner.benchmarks_summary,
        benchmark_models=runner.benchmark_models,
    )
    out = write_bundle_outputs(
        runner.replays_dir, bundle, "tournament_bundle_full.json", "tournament_bundle_full.js", write_demo=True
    )
    print(f"[DONE] Saved full tournament bundle -> {out}")


if __name__ == "__main__":
    main()
