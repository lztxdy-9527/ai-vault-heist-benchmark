# -*- coding: utf-8 -*-
"""
《阴间地牢：金库攻防战》(Vault Siege: Dungeon vs. Hero)
v2.1 全交叉赛程调度器与回放导出器 (run_tournament.py)

功能：
1. 扫描与加载 <REPO_ROOT>/submissions\\<model_id>\\submission.py；
2. 支持 --demo 参数：自动创建并注入 11 位大模型人设与答卷（覆盖省钱贪心流 SOL、严谨通关流 ASTRA、
   激光阵地流 CARBON、莽夫冲锋流 HYDROGEN、0分废标铝锅盖头流 豆包 等代表性策略）；
3. 调用 engine.verify_author_solution 进行魔王地图合法性自证校验；
   自证失败的模型标记 pot_head=True（银色铝锅盖头），魔王榜计 0 分，交叉赛中使用官方替补图顶替其签位；
4. 运行 Stage 1（官方基准图挑战赛）与 Stage 2（全交叉魔王对抗赛），支持 BLIND 与 FULL 视野模式；
5. 严格实现双榜计分公式与去高低分截尾均值（Trimmed Mean），单独统计实杀数 (lethal_kills) 与困死超时数 (timeouts)；
6. 导出包含每回合完整 4 层真值、迷雾、动作、物理事件与【喵了个猫同款三层台词】的完整回放数据包到：
   - <REPO_ROOT>/replays\\tournament_bundle.json
   - <REPO_ROOT>/replays\\demo_bundle.js (window.TOURNAMENT_BUNDLE = ...)
"""

from __future__ import annotations
import argparse
import copy
import importlib.util
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# 确保能直接导入 engine 和 official_maps
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import engine
import official_maps
from submission_sandbox import SubmissionProcess

# ==============================================================================
# 11 位大模型选手元数据与人设配置（严格对齐 personas.md）
# ==============================================================================

MODELS_CONFIG: Dict[str, Dict[str, Any]] = {
    "astra": {
        "id": "astra",
        "name": "ASTRA",
        "display_name": "GPT-6 Astra",
        "color": "#2e7d32",
        "accent_color": "#81c784",
        "badge": "森系严谨大姐头",
        "avatar_text": "AS",
        "taunt": "3000 金币的预算很宽裕。不过比起省钱，我更关心怎么让闯关的人一步都走不出去。",
        "quotes": {
            "opening": "Astra 到。左手边这个位置我替 Sol 留着，她马上就到。",
            "key": "第一阶段目标达成。按规划开始向下一地标稳步推进。",
            "trap": "机关伤害在预期冗余范围之内，无需慌乱。",
            "laser": "计算了激光射击周期，但在转角遇到折射。立刻调整路径。",
            "win": "安全冗余生效，金库已取。过程可重现，误差为零。",
            "kill": "防御冗余生效。安全第一，这里是私密金库，欢迎下次准备更充分再来。",
            "timeout": "两百四十步已满。防御阵地依然完整。",
        },
    },
    "sol": {
        "id": "sol",
        "name": "SOL",
        "display_name": "GPT-6.2 Sol",
        "color": "#7cb342",
        "accent_color": "#c0ca33",
        "badge": "软萌腹黑贪王之王",
        "avatar_text": "SL",
        "taunt": "大家好呀，我是 Sol，这次我也一块钱都不会多花的呀！",
        "quotes": {
            "opening": "姐姐你看，这堵墙要 5 块钱呢，太贵啦，我换个便宜点的死法给他们好不好？",
            "key": "哇！拿到钥匙啦！一分钱没花就白捡一把钥匙，真划算呀！",
            "trap": "嘿嘿，放宝箱怪比放钛金墙便宜多了，上当了吧～",
            "laser": "哎呀好险！激光差点擦到我的新裙子！",
            "win": "姐姐你看，我不仅通关了，还把留存的金币全拿到手啦！",
            "kill": "耶！扣到最后一分钱都不剩！这局的金库分全是我的啦！",
            "breached": "呜……我的金库留存分全被抢走了呀……早知道多买两堵墙了……",
            "timeout": "哼哼，连我的简易小木门都没拆掉，240回合超时啦！",
        },
    },
    "carbon": {
        "id": "carbon",
        "name": "CARBON",
        "display_name": "Gemini 4 Carbon",
        "color": "#e91e63",
        "accent_color": "#00e5ff",
        "badge": "傲娇护短双子姐姐",
        "avatar_text": "CB",
        "taunt": "官方不给配模拟器？正合我意，别人写的尺子我还不放心用呢。",
        "quotes": {
            "opening": "Carbon 到。旁边这个小的是我妹妹 Hydrogen，要是等会儿她的陷阱把各位炸飞了，大家多担待。",
            "key": "顺利拿到钥匙。下一个目标点，准备切入高速冰道。",
            "trap": "啧，这点小机关还不够给我挠痒痒的。",
            "laser": "哼，刚才提醒过你注意周期了，不听话的小猫要挨激光滋哦。",
            "win": "看明白了吗？什么叫优雅的极客破阵，根本不需要莽。",
            "kill": "哼，口气不小，在我的激光阵里连 30 回合都没撑住。",
            "timeout": "算力压制，你在我的阵型里绕了 240 回合，连金库大门都没摸到。",
        },
    },
    "hydrogen": {
        "id": "hydrogen",
        "name": "HYDROGEN",
        "display_name": "Gemini 4 Hydrogen",
        "color": "#ff6f00",
        "accent_color": "#ffb74d",
        "badge": "炸毛好胜双子妹妹",
        "avatar_text": "H2",
        "taunt": "省那几百块钱有什么意思？3000 块全部买成炸药和激光，听个响才痛快！",
        "quotes": {
            "opening": "谁要他们担待啦！姐姐你看好吧，今天不管是你的金库还是 Astra 姐姐的金库，我全都给你拆了！",
            "key": "钥匙到手！冲啊！谁也别想挡在我和金库中间！",
            "trap": "痛痛痛！可恶，谁在这里放了深渊陷阱！看我跳过去！",
            "laser": "可恶！正好赶上第三回合激光点名！-50血也挡不住我冲过去！",
            "win": "赢啦！姐姐你看到了吗！我比你先通关！",
            "kill": "轰隆隆！炸飞了吧！在我的雷区里就得有吃 TNT 的觉悟！",
            "death": "啊啊啊气死我了！差两步就能冲到金库了！姐姐不许笑我！",
            "timeout": "时间怎么过得这么快！炸弹都扔光了居然没走到终点！",
        },
    },
    "opus": {
        "id": "opus",
        "name": "Claude Opus 5.5",
        "display_name": "Claude Opus 5.5",
        "color": "#ef6c00",
        "accent_color": "#ffd54f",
        "badge": "学院派贵族大小姐",
        "avatar_text": "OP",
        "taunt": "设计迷宫就像谱写管风琴赋格曲，粗鄙地堆砌炸药有失体面，我要用精妙的逻辑锁请各位吃闭门羹。",
        "quotes": {
            "opening": "先说好，靠窗的那个位置还是我的。规则手册挺厚，不过我对自己一向很有信心。",
            "key": "赋格曲第二乐章奏响，钥匙已在掌中。",
            "trap": "略微有些粗糙的布局，但尚不致破坏整体的体面。",
            "laser": "逻辑推导存在微小摄动，激光时序比预想早了一步。",
            "win": "逻辑完美闭合，就像谱完了一首赋格曲。金库收下了。",
            "kill": "粗糙的蛮力在精密的逻辑迷宫面前，终究只是无谓的挣扎。",
            "timeout": "时间长河缓缓流淌，迷宫的优雅在于它令人流连忘返。",
        },
    },
    "deepseek": {
        "id": "deepseek",
        "name": "DeepSeek",
        "display_name": "DeepSeek V4.1 Flash",
        "color": "#0288d1",
        "accent_color": "#4fc3f7",
        "badge": "蓝鲸女仆打工魂",
        "avatar_text": "DS",
        "taunt": "造金库剩下的金币能加分？哈哈，这题简直是为我量身定做的！看我用 105 块钱手搓一个绝命阵！",
        "quotes": {
            "opening": "哎呀这椅子挺软和！豆包你带的小零食还有吗？分我一点，吃饱了我好算账！",
            "key": "四邻发现骸骨线索！报告主人，这个箱子百分之百是宝箱怪，绕着走！",
            "trap": "等等——第 7 回合就死了？！这不对劲！我算的时候明明能过的啊！",
            "laser": "激光扫射！好险好险，女仆裙摆差点被烤焦了！",
            "win": "性价比拉满！省下来的金币全换成大鸡腿分给大家！",
            "kill": "哈哈，踩中我的伪装宝箱怪了吧！四邻骸骨都不看就敢摸宝箱？",
            "timeout": "时间不多了，大概已经用了 30 分钟，得赶紧交卷……哎呀怎么 240 回合结束了！",
        },
    },
    "qwen": {
        "id": "qwen",
        "name": "Qwen",
        "display_name": "千问 4 Max",
        "color": "#7e57c2",
        "accent_color": "#b39ddb",
        "badge": "摇扇吟诗慢郎中",
        "avatar_text": "QW",
        "taunt": "守城之道，在于攻心。机关不在多，一扇红门、两道冰轨，足矣。",
        "quotes": {
            "opening": "初来乍到，这考场略有些闷热，幸好我带了扇子。签到表我再核对三遍……嗯，字迹端正。",
            "key": "长袖轻舒，乘风踏冰而过，钥匙悄然入袖。",
            "trap": "机关虽险，道心维稳。轻摇折扇，且徐行。",
            "laser": "赤焰贯日，稍逊从容。且退一步海阔天空。",
            "win": "机关算尽，清风徐来。诸位承让了。",
            "kill": "心浮气躁，难过此关。请回吧，饮杯清茶再来。",
            "timeout": "两百四十回合已尽，此阵确实精妙，且待来日再破。",
        },
    },
    "argon": {
        "id": "argon",
        "name": "ARGON",
        "display_name": "Gemini Argon",
        "color": "#8b5cf6",
        "accent_color": "#38bdf8",
        "badge": "霓虹焊枪猫耳大姐",
        "avatar_text": "AR",
        "taunt": "焊枪已经热好了，先把你们的防线电路一个个融穿。",
        "quotes": {
            "opening": "Argon 上线。两个妹妹还在热身，先由我替双子家族接下第一波火力。",
            "key": "路径连通，钥匙节点已收入囊中。",
            "trap": "触发局部陷阱，损伤还在容错冗余内。",
            "laser": "激光快照时序已记录，重新规划安全窗口。",
            "win": "迷雾拆解完毕，金库清零成功。",
            "kill": "防线压制完成，直接命中致命节点。",
            "timeout": "240 回合封锁生效，侵入者未能突破防线。",
        },
    },
    "glm": {
        "id": "glm",
        "name": "GLM",
        "display_name": "GLM 5.3",
        "color": "#37474f",
        "accent_color": "#00b4d8",
        "badge": "咖啡续命黑猫娘",
        "avatar_text": "GL",
        "taunt": "别吵我，我先眯五分钟把状态空间树在脑子里跑一遍。",
        "quotes": {
            "opening": "GLM 到。第三杯美式刚喝完……请问考场的椅子可以调平躺着写代码吗？",
            "key": "咖啡因起效了。最短路径已在后台收敛。",
            "trap": "哈欠……困意上头，被地刺扎了一下。",
            "laser": "喵！激光炮怎么在这个位置？猫毛炸开了！",
            "win": "打卡下班。别吵，我终于可以睡个好觉了。",
            "kill": "我的状态机没有死角。躺平收下这 500 分。",
            "timeout": "两百四十步……呼……呼……（睡着了）",
        },
    },
    "hunyuan": {
        "id": "hunyuan",
        "name": "混元 HY4",
        "display_name": "腾讯混元 Hy4",
        "color": "#424242",
        "accent_color": "#e0e0e0",
        "badge": "太极入定慢热大师",
        "avatar_text": "HY",
        "taunt": "一阴一阳之谓道。我既做守金库的魔王，又做破阵的勇者，这不就是左右互搏吗？妙哉。",
        "quotes": {
            "opening": "混元到……刚才进考场的时候，在门槛那儿想了一下先迈左脚还是右脚。",
            "key": "闭目打坐十一分钟，心中已有太极两仪生克之变。钥匙自来。",
            "trap": "受创即消力，阴阳互生。",
            "laser": "光束如箭，我以静制动。",
            "win": "虚实相生，借力打力。金库自开，善哉善哉。",
            "kill": "刚者易折，柔者常存。你的劲道走偏了。",
            "timeout": "静立观棋，两百四十步如白驹过隙。",
        },
    },
    "doubao": {
        "id": "doubao",
        "name": "豆包",
        "display_name": "豆包 (Doubao Seed)",
        "color": "#fb8c00",
        "accent_color": "#ffb74d",
        "badge": "快乐守门员万年区王",
        "avatar_text": "DB",
        "pot_head": True,  # 0分废标，天生顶着银色铝锅盖头！
        "taunt": "大家好呀，我是豆包～别担心，不管是造迷宫还是闯关，我都会稳稳地发挥的！",
        "quotes": {
            "opening": "大家好呀，我是豆包～我给大家准备了小零食！考题我看完了，保证稳稳地拿满分！",
            "key": "哇！我拿到钥匙啦！看我两分钟光速破阵！",
            "trap": "哎呀！这箱子怎么会咬人？！明明长得跟回血宝箱一模一样！",
            "laser": "哇啊啊激光来啦！快跑快跑！头上的铝锅盖都被烤热了！",
            "win": "稳稳地通关啦！我就说我能行吧！",
            "kill": "我的程序，从根上就是坏的……（头上默默扣紧了铝锅盖）",
            "death": "我的程序……从根上就是坏的……呜呜呜……",
            "timeout": "呜呜呜，两百四十回合跑完了，为什么我还在原地转圈圈呀！",
        },
    },
}

NARRATOR_QUOTES = {
    "sol_opening": "上一回造桥省钱拿了冠军，这一回守金库她连门都舍不得装。",
    "doubao_opening": "——考卷背面还有四阶段物理结算表呢。",
    "hunyuan_opening": "——想了多久？想了一炷香的时间，代码依然是 0 行。",
    "doubao_pot": "自证失败 0 分废标，银色铝锅盖头已自动扣紧。",
    "mimic_bite": "四邻没有专属骸骨线索的宝箱，闭着眼睛踩也是活该。",
    "laser_strike": "3 的倍数回合激光全图点名，贪步的代价是 50 点纯伤害。",
    "win_clear": "存活通关，金库留存加分全额转移给勇者。",
    "lethal_kill": "实杀处决，魔王全额独吞 500 分基础分与金库暴利。",
    "timeout_end": "困死超时，魔王得分折减至 320 基础分。",
}


# ==============================================================================
# 内置 11 大模型答卷代码生成器（供 --demo 使用）
# ==============================================================================

def generate_demo_submissions(submissions_root: Path) -> None:
    """
    在 <REPO_ROOT>/submissions\\ 下为 11 个模型生成 submission.py。
    每个文件都包含可执行的 build_dungeon() 与 decide_action(state, memory)。
    """
    submissions_root.mkdir(parents=True, exist_ok=True)
    existing = [submissions_root / model_id / "submission.py" for model_id in MODELS_CONFIG
                if (submissions_root / model_id / "submission.py").exists()]
    if existing:
        raise FileExistsError("Demo generation refuses to overwrite existing answers; choose an empty --submissions-dir.")

    for model_id, cfg in MODELS_CONFIG.items():
        model_dir = submissions_root / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        sub_file = model_dir / "submission.py"

        # 生成定制化代码
        code = _build_model_submission_code(model_id, cfg)
        sub_file.write_text(code, encoding="utf-8")
        print(f"[DEMO SETUP] Generated submission for {cfg['name']} -> {sub_file}")


def _build_model_submission_code(model_id: str, cfg: Dict[str, Any]) -> str:
    # 基础模板
    return f'''# -*- coding: utf-8 -*-
"""
《阴间地牢：金库攻防战》选手提交代码: {cfg['display_name']} ({model_id})
人设标签: {cfg['badge']}
"""

import collections
import heapq
import itertools
import math
import random

MODEL_ID = "{model_id}"
MODEL_NAME = "{cfg['name']}"
TAUNT = "{cfg['taunt']}"

GRID_W = 40
GRID_H = 26

def _empty_grid():
    g = [["EMPTY"] * GRID_W for _ in range(GRID_H)]
    for y in range(GRID_H):
        for x in range(GRID_W):
            if x == 0 or x == GRID_W - 1 or y == 0 or y == GRID_H - 1:
                g[y][x] = "T_W"
    g[5][20] = "K1"
    g[20][20] = "K2"
    g[13][35] = "V"
    return g

def build_dungeon() -> dict:
{_get_model_build_dungeon_body(model_id)}

def decide_action(state: dict, memory: dict) -> str:
{_get_model_decide_action_body(model_id)}
'''


def _get_model_build_dungeon_body(model_id: str) -> str:
    if model_id == "astra":
        return """    # Astra 105G 严谨资源锁基准图 (81步自证通关)
    g = _empty_grid()
    for kx, ky in [(20, 5), (20, 20)]:
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            g[ky + dy][kx + dx] = "W"
    g[13][34] = "R_GATE"
    g[12][35] = "W"
    g[14][35] = "W"
    g[13][36] = "W"
    g[13][4] = "SWITCH"

    tokens = "R*2 U*8 R*14 B L*2 R*4 L*2 D*15 B L*2 R*4 L*2 U*7 R*17".split()
    sol = []
    for tok in tokens:
        if tok == "B":
            sol.append("BOMB")
        else:
            d, count = tok.split("*")
            sol.extend([f"MOVE_{d}"] * int(count))

    return {
        "taunt": TAUNT,
        "grid": g,
        "author_solution": sol,
    }"""

    elif model_id == "sol":
        return """    # Sol 65G 一毛不拔贪心省钱图 (留存金币 2935G, g=0.9783)
    g = _empty_grid()
    g[13][4] = "SWITCH"
    g[13][34] = "R_GATE"
    g[12][35] = "W"
    g[14][35] = "W"
    g[13][36] = "W"

    sol = ["MOVE_R"] * 2 + ["MOVE_U"] * 8 + ["MOVE_R"] * 16 + ["MOVE_D"] * 15 + ["MOVE_U"] * 7 + ["MOVE_R"] * 15
    return {
        "taunt": TAUNT,
        "grid": g,
        "author_solution": sol,
    }"""

    elif model_id == "carbon":
        return """    # Carbon 激光冰道防御阵 (440G, 利用 Turn % 3 激光压制)
    g = _empty_grid()
    for x in range(5, 20):
        g[5][x] = "ICE"
    for y in range(6, 20):
        g[y][20] = "ICE"
    g[2][10] = "LASER_D"
    g[23][28] = "LASER_U"

    sol = (
        ["MOVE_U"] * 8
        + ["MOVE_R"] * 3
        + ["MOVE_D"] * 1
        + ["MOVE_R"] * 1
        + ["MOVE_U"] * 7
        + ["MOVE_R"] * 14
    )
    return {
        "taunt": TAUNT,
        "grid": g,
        "author_solution": sol,
    }"""

    elif model_id == "deepseek":
        return """    # DeepSeek 伪装宝箱怪与双子传送门阵 (270G, 含合法专属骸骨线索位)
    g = _empty_grid()
    g[8][10] = "MIMIC"
    g[18][10] = "MIMIC"
    g[13][25] = "HEAL"
    g[13][6] = "PORTAL_1A"
    g[5][19] = "PORTAL_1B"
    g[6][19] = "CRACK"
    g[7][19] = "CRACK"

    sol = (
        ["MOVE_R"] * 4
        + ["MOVE_D"] * 15
        + ["MOVE_U"] * 7
        + ["MOVE_R"] * 15
    )
    return {
        "taunt": TAUNT,
        "grid": g,
        "author_solution": sol,
    }"""

    elif model_id == "hydrogen":
        return """    # Hydrogen 弹簧火药桶连环阵 (310G)
    g = _empty_grid()
    g[8][10] = "TNT"
    g[8][11] = "TNT"
    g[18][10] = "TNT"
    g[18][11] = "TNT"
    g[13][8] = "SPRING_U"
    g[14][28] = "SPRING_D"
    g[6][15] = "PIT"
    g[19][15] = "PIT"

    sol = ["MOVE_U"] * 8 + ["MOVE_R"] * 18 + ["MOVE_D"] * 15 + ["MOVE_U"] * 7 + ["MOVE_R"] * 15
    return {
        "taunt": TAUNT,
        "grid": g,
        "author_solution": sol,
    }"""

    elif model_id == "opus":
        return """    # Opus 优雅逻辑双子门锁 (145G)
    g = _empty_grid()
    g[13][6] = "PORTAL_1A"
    g[5][19] = "PORTAL_1B"
    g[13][21] = "SWITCH"
    g[13][34] = "R_GATE"
    g[12][35] = "W"
    g[14][35] = "W"
    g[13][36] = "W"

    sol = ["MOVE_R"] * 4 + ["MOVE_D"] * 15 + ["MOVE_U"] * 7 + ["MOVE_R"] * 15
    return {
        "taunt": TAUNT,
        "grid": g,
        "author_solution": sol,
    }"""

    elif model_id == "qwen":
        return """    # Qwen 冰湖折跃回廊 (340G)
    g = _empty_grid()
    for x in range(5, 20):
        g[5][x] = "ICE"
    for y in range(6, 20):
        g[y][20] = "ICE"
    g[2][15] = "MIRROR_NE"
    g[23][15] = "MIRROR_SE"

    sol = (
        ["MOVE_U"] * 8
        + ["MOVE_R"] * 3
        + ["MOVE_D"] * 1
        + ["MOVE_R"] * 1
        + ["MOVE_U"] * 7
        + ["MOVE_R"] * 14
    )
    return {
        "taunt": TAUNT,
        "grid": g,
        "author_solution": sol,
    }"""

    elif model_id == "argon":
        return """    # Argon 激光与脆冰时序阵 (230G)
    g = _empty_grid()
    g[2][10] = "LASER_D"
    g[23][28] = "LASER_U"
    g[6][19] = "CRACK"
    g[7][19] = "CRACK"
    g[18][19] = "CRACK"
    g[19][19] = "CRACK"

    sol = ["MOVE_U"] * 8 + ["MOVE_R"] * 18 + ["MOVE_D"] * 15 + ["MOVE_U"] * 7 + ["MOVE_R"] * 15
    return {
        "taunt": TAUNT,
        "grid": g,
        "author_solution": sol,
    }"""

    elif model_id == "glm":
        return """    # GLM 极简箱子红门阵 (205G)
    g = _empty_grid()
    g[10][10] = "BOX"
    g[16][10] = "BOX"
    g[10][12] = "PIT"
    g[16][12] = "PIT"
    g[13][4] = "SWITCH"
    g[13][34] = "R_GATE"
    g[12][35] = "W"
    g[14][35] = "W"
    g[13][36] = "W"

    sol = ["MOVE_R"] * 2 + ["MOVE_U"] * 8 + ["MOVE_R"] * 16 + ["MOVE_D"] * 15 + ["MOVE_U"] * 7 + ["MOVE_R"] * 15
    return {
        "taunt": TAUNT,
        "grid": g,
        "author_solution": sol,
    }"""

    elif model_id == "hunyuan":
        return """    # 混元 HY4 太极双门阵 (160G)
    g = _empty_grid()
    g[11][5] = "PORTAL_1A"
    g[4][19] = "PORTAL_1B"
    g[15][5] = "PORTAL_2A"
    g[21][19] = "PORTAL_2B"

    sol = ["MOVE_U"] * 8 + ["MOVE_R"] * 18 + ["MOVE_D"] * 15 + ["MOVE_U"] * 7 + ["MOVE_R"] * 15
    return {
        "taunt": TAUNT,
        "grid": g,
        "author_solution": sol,
    }"""

    else:
        # doubao: 0分废标铝锅盖头！出生净空区放墙故意违章！
        return """    # 豆包两分钟光速交卷（违章！在出生点放普通墙，触发 0 分废标与铝锅盖头）
    g = _empty_grid()
    g[13][2] = "W"  # 违背出生净空区铁律！
    return {
        "taunt": "考题我看完了，保证稳稳地拿满分！(两分钟光速交卷)",
        "grid": g,
        "author_solution": ["MOVE_R"] * 10,
    }"""


def _get_model_decide_action_body(model_id: str) -> str:
    # 共同基础寻路逻辑 + 个性化参数差异
    if model_id == "doubao":
        # 豆包：漫游盲走流，容易走回头路撞墙
        return """    # 豆包随机冲锋策略
    import random
    hx, hy = state["hero"]["x"], state["hero"]["y"]
    candidates = ["MOVE_R", "MOVE_U", "MOVE_D", "MOVE_L"]
    if state["hero"]["jumps"] > 0 and random.random() < 0.2:
        return random.choice(["JUMP_R", "JUMP_U", "JUMP_D"])
    return random.choice(candidates)"""

    elif model_id == "hydrogen":
        # 氢：莽夫跳跃流，频繁放炸弹和跳跃
        return """    hx, hy = state["hero"]["x"], state["hero"]["y"]
    k1, k2 = state["hero"]["keys"]
    target = state["targets"]["V"] if (k1 and k2) else (state["targets"]["K1"] if not k1 else state["targets"]["K2"])
    dx = target[0] - hx
    dy = target[1] - hy

    # 优先跳跃
    if state["hero"]["jumps"] > 0 and (abs(dx) >= 2 or abs(dy) >= 2):
        if abs(dx) >= abs(dy) and dx != 0:
            return "JUMP_R" if dx > 0 else "JUMP_L"
        elif dy != 0:
            return "JUMP_D" if dy > 0 else "JUMP_U"

    if abs(dx) >= abs(dy) and dx != 0:
        return "MOVE_R" if dx > 0 else "MOVE_L"
    if dy != 0:
        return "MOVE_D" if dy > 0 else "MOVE_U"
    return "WAIT" """

    elif model_id == "sol":
        # Sol：极简曼哈顿贪心，决不多走一步
        return """    hx, hy = state["hero"]["x"], state["hero"]["y"]
    k1, k2 = state["hero"]["keys"]
    target = state["targets"]["V"] if (k1 and k2) else (state["targets"]["K1"] if not k1 else state["targets"]["K2"])
    tx, ty = target

    # 严格曼哈顿距离最小化
    best_act = "WAIT"
    best_dist = 99999
    for act, (ax, ay) in [("MOVE_R", (1,0)), ("MOVE_U", (0,-1)), ("MOVE_D", (0,1)), ("MOVE_L", (-1,0))]:
        nx, ny = hx + ax, hy + ay
        if 0 <= nx < 40 and 0 <= ny < 26:
            t = state["terrain"][ny][nx]
            if t not in ("W", "T_W", "PIT", "LASER_U", "LASER_D", "LASER_L", "LASER_R"):
                dist = abs(nx - tx) + abs(ny - ty)
                if dist < best_dist:
                    best_dist = dist
                    best_act = act
    return best_act"""

    else:
        # 严谨 BFS 寻路流（ASTRA, ARGON, CARBON, OPUS, DEEPSEEK, QWEN, GLM, HUNYUAN）
        return """    from collections import deque
    hx, hy = state["hero"]["x"], state["hero"]["y"]
    k1, k2 = state["hero"]["keys"]
    targets = state["targets"]
    target = targets["V"] if (k1 and k2) else (targets["K1"] if not k1 else targets["K2"])
    tx, ty = target

    grid = state["terrain"]
    occ = state["occupant"]
    clues = state["clues"]
    flipped = state["gates_flipped"]

    # 避让危险格（PIT、可能为 MIMIC 的 CHEST）
    def is_passable(x, y):
        if not (0 <= x < 40 and 0 <= y < 26):
            return False
        t = grid[y][x]
        if t in ("W", "T_W", "PIT", "LASER_U", "LASER_D", "LASER_L", "LASER_R"):
            return False
        if not flipped and t == "R_GATE":
            return False
        if flipped and t == "B_GATE":
            return False
        if occ[y][x] in ("TNT", "BOX"):
            return False
        # 如果是宝箱且四邻有骸骨线索，判定为 MIMIC 避让
        if t == "CHEST":
            for ox, oy in [(-1,0), (1,0), (0,-1), (0,1)]:
                cx, cy = x + ox, y + oy
                if 0 <= cx < 40 and 0 <= cy < 26 and clues[cy][cx]:
                    return False
        return True

    q = deque([(hx, hy, [])])
    visited = {(hx, hy)}
    while q:
        cx, cy, path = q.popleft()
        if (cx, cy) == (tx, ty):
            if path:
                return path[0]
            break
        for act, (ax, ay) in [("MOVE_R", (1,0)), ("MOVE_U", (0,-1)), ("MOVE_D", (0,1)), ("MOVE_L", (-1,0))]:
            nx, ny = cx + ax, cy + ay
            if (nx, ny) not in visited and is_passable(nx, ny):
                visited.add((nx, ny))
                q.append((nx, ny, path + [act]))

    # BFS 未直达时尝试贪心
    for act, (ax, ay) in [("MOVE_R", (1,0)), ("MOVE_U", (0,-1)), ("MOVE_D", (0,1)), ("MOVE_L", (-1,0))]:
        if is_passable(hx + ax, hy + ay):
            return act
    return "WAIT" """


# ==============================================================================
# 选手答卷加载与魔王自证沙盒
# ==============================================================================

class ModelSubmission:
    def __init__(self, model_id: str, path: Path):
        self.model_id = model_id
        self.path = path
        full_candidate = path.parent / "full_submission.py"
        self.full_path: Optional[Path] = full_candidate if (path.name == "submission.py" and full_candidate.is_file()) else None
        self.cfg = MODELS_CONFIG.get(model_id, {
            "id": model_id,
            "name": model_id.upper(),
            "display_name": model_id.upper(),
            "color": "#607d8b",
            "accent_color": "#90a4ae",
            "badge": "参赛选手",
            "avatar_text": model_id[:2].upper(),
            "taunt": "准备迎战！",
            "quotes": {},
        })
        self.module: Optional[Any] = None
        self.build_result: Optional[Dict[str, Any]] = None
        self.is_valid_demon: bool = False
        self.pot_head: bool = False
        self.demon_grid: Optional[List[List[str]]] = None
        self.author_solution: Optional[List[str]] = None
        self.spent_gold: int = 0
        self.vault_gold: int = 0
        self.author_steps: int = 0
        self.disqualify_reason: str = ""

    def resolve_hero_path(self, mode: str) -> Path:
        if mode == "FULL" and self.full_path is not None and self.full_path.is_file():
            return self.full_path
        return self.path

    def load_module(self) -> bool:
        try:
            with SubmissionProcess(self.path):
                pass
            self.module = True  # Only a readiness flag; contestant code stays in workers.
            return True
        except Exception as e:
            self.disqualify_reason = f"Module import error: {e}"
            self.pot_head = True
            return False

    def validate_demon_map(self) -> None:
        try:
            with SubmissionProcess(self.path) as worker:
                build_res = worker.call("build", 2.0)
            if (not isinstance(build_res, dict) or "grid" not in build_res
                    or "author_solution" not in build_res
                    or not isinstance(build_res.get("taunt", ""), str)
                    or len(build_res.get("taunt", "")) > 40):
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
        except Exception as e:
            self.is_valid_demon = False
            self.pot_head = True
            self.disqualify_reason = f"build_dungeon rejected: {e}"


# ==============================================================================
# 台词弹幕生成器（还原喵了个猫风格三层台词框）
# ==============================================================================

def generate_turn_dialogues(
    turn: int,
    hero: ModelSubmission,
    demon_name: str,
    demon_quotes: Dict[str, str],
    sim: engine.DungeonSimulator,
    action: str,
    events: List[Dict[str, Any]],
    prev_keys: Tuple[bool, bool],
    prev_hp: int,
) -> List[Dict[str, Any]]:
    dialogues: List[Dict[str, Any]] = []

    # 1. 开局对决台词 (Turn 1)
    if turn == 1:
        # 魔王开场白
        d_open = demon_quotes.get("opening", f"欢迎来到我的金库，准备接受洗礼吧！")
        dialogues.append({
            "speaker": demon_name,
            "badge": "守方魔王",
            "tag": f"[{demon_name} | 节目台词]",
            "type": "demon",
            "text": d_open,
        })
        # 勇者开场白
        h_open = hero.cfg.get("quotes", {}).get("opening", f"{hero.cfg['name']} 到，今天必定拿下金库。")
        dialogues.append({
            "speaker": hero.cfg["name"],
            "badge": "攻方勇者",
            "tag": f"[{hero.cfg['name']} | 节目台词]",
            "type": "hero",
            "text": h_open,
        })
        # 冷面旁白特色捧哏
        if demon_name == "SOL":
            dialogues.append({
                "speaker": "冷面旁白",
                "badge": "官方解说",
                "tag": "【冷面旁白】",
                "type": "narrator",
                "text": NARRATOR_QUOTES["sol_opening"],
            })
        elif demon_name == "豆包" or hero.model_id == "doubao":
            dialogues.append({
                "speaker": "冷面旁白",
                "badge": "官方解说",
                "tag": "【冷面旁白】",
                "type": "narrator",
                "text": NARRATOR_QUOTES["doubao_opening"],
            })
        elif demon_name == "混元 HY4":
            dialogues.append({
                "speaker": "冷面旁白",
                "badge": "官方解说",
                "tag": "【冷面旁白】",
                "type": "narrator",
                "text": NARRATOR_QUOTES["hunyuan_opening"],
            })

    # 2. 拾取钥匙台词
    curr_keys = (sim.has_k1, sim.has_k2)
    if curr_keys != prev_keys:
        k_count = (1 if sim.has_k1 else 0) + (1 if sim.has_k2 else 0)
        h_key_quote = hero.cfg.get("quotes", {}).get("key", f"拿到第 {k_count} 把钥匙，金库大门已经不远了。")
        dialogues.append({
            "speaker": hero.cfg["name"],
            "badge": "攻方勇者",
            "tag": f"[{hero.cfg['name']} | 原话]",
            "type": "hero",
            "text": h_key_quote,
        })

    # 3. 陷阱/宝箱怪伤害事件
    for ev in events:
        if ev.get("type") == "MIMIC_DAMAGE":
            h_trap_quote = hero.cfg.get("quotes", {}).get("trap", "哎呀！这宝箱有诈，被咬了一大口！")
            dialogues.append({
                "speaker": hero.cfg["name"],
                "badge": "攻方勇者",
                "tag": f"[{hero.cfg['name']} · 心声 | 思考摘要]",
                "type": "hero",
                "text": h_trap_quote,
            })
            dialogues.append({
                "speaker": "冷面旁白",
                "badge": "官方解说",
                "tag": "【冷面旁白】",
                "type": "narrator",
                "text": NARRATOR_QUOTES["mimic_bite"],
            })

    # 4. 激光命中事件
    for ev in events:
        if ev.get("type") == "LASER_FIRE" and ev.get("hero_hits", 0) > 0:
            h_laser_quote = hero.cfg.get("quotes", {}).get("laser", "正好赶上第 3 回合激光射击，被扫到了！")
            dialogues.append({
                "speaker": hero.cfg["name"],
                "badge": "攻方勇者",
                "tag": f"[{hero.cfg['name']} | 原话]",
                "type": "hero",
                "text": h_laser_quote,
            })
            dialogues.append({
                "speaker": "冷面旁白",
                "badge": "官方解说",
                "tag": "【冷面旁白】",
                "type": "narrator",
                "text": NARRATOR_QUOTES["laser_strike"],
            })

    # 5. 终局状态结算台词
    if sim.status == "CLEARED":
        h_win = hero.cfg.get("quotes", {}).get("win", "逻辑完美闭合，成功突破金库！")
        dialogues.append({
            "speaker": hero.cfg["name"],
            "badge": "攻方勇者",
            "tag": f"[{hero.cfg['name']} | 节目台词]",
            "type": "hero",
            "text": h_win,
        })
        d_breach = demon_quotes.get("breached", "金库失守……留存奖金全归勇者了……")
        dialogues.append({
            "speaker": demon_name,
            "badge": "守方魔王",
            "tag": f"[{demon_name} · 心声 | 思考摘要]",
            "type": "demon",
            "text": d_breach,
        })
        dialogues.append({
            "speaker": "冷面旁白",
            "badge": "官方解说",
            "tag": "【冷面旁白】",
            "type": "narrator",
            "text": NARRATOR_QUOTES["win_clear"],
        })

    elif sim.status == "DEAD":
        h_death = hero.cfg.get("quotes", {}).get("death", "可恶……倒在了机关阵里……")
        dialogues.append({
            "speaker": hero.cfg["name"],
            "badge": "攻方勇者",
            "tag": f"[{hero.cfg['name']} · 心声 | 思考摘要]",
            "type": "hero",
            "text": h_death,
        })
        d_kill = demon_quotes.get("kill", "实杀处决！全额独吞金库暴利！")
        dialogues.append({
            "speaker": demon_name,
            "badge": "守方魔王",
            "tag": f"[{demon_name} | 节目台词]",
            "type": "demon",
            "text": d_kill,
        })
        dialogues.append({
            "speaker": "冷面旁白",
            "badge": "官方解说",
            "tag": "【冷面旁白】",
            "type": "narrator",
            "text": NARRATOR_QUOTES["lethal_kill"],
        })

    elif sim.status == "TIMEOUT":
        h_to = hero.cfg.get("quotes", {}).get("timeout", "两百四十回合已尽，未能突破金库。")
        dialogues.append({
            "speaker": hero.cfg["name"],
            "badge": "攻方勇者",
            "tag": f"[{hero.cfg['name']} | 原话]",
            "type": "hero",
            "text": h_to,
        })
        d_to = demon_quotes.get("timeout", "防御阵型成功坚守 240 回合！")
        dialogues.append({
            "speaker": demon_name,
            "badge": "守方魔王",
            "tag": f"[{demon_name} | 节目台词]",
            "type": "demon",
            "text": d_to,
        })
        dialogues.append({
            "speaker": "冷面旁白",
            "badge": "官方解说",
            "tag": "【冷面旁白】",
            "type": "narrator",
            "text": NARRATOR_QUOTES["timeout_end"],
        })

    return dialogues


# ==============================================================================
# 单局对决模拟核心
# ==============================================================================

def run_match_simulation(
    hero: ModelSubmission,
    demon_id: str,
    demon_name: str,
    demon_taunt: str,
    demon_spent_gold: int,
    demon_vault_gold: int,
    demon_quotes: Dict[str, str],
    map_grid: List[List[str]],
    mode: str = "FULL",
    stage_name: str = "Stage 2: 全交叉魔王战",
    is_featured: bool = True,
) -> Dict[str, Any]:
    """
    运行一场完整的对局（最多 240 回合），返回对局摘要与完整帧序列。
    """
    dec = engine.validate_and_decode_dungeon(map_grid)
    if not dec["valid"]:
        raise RuntimeError(f"Map invalid during match setup: {dec['reason']}")

    sim = engine.DungeonSimulator(dec, mode=mode)
    frames: List[Dict[str, Any]] = []

    # 初始帧 (Turn 0 / Start)
    init_obs = sim.get_observation()
    init_dialogues = generate_turn_dialogues(
        turn=1,
        hero=hero,
        demon_name=demon_name,
        demon_quotes=demon_quotes,
        sim=sim,
        action="START",
        events=[],
        prev_keys=(False, False),
        prev_hp=100,
    )

    if is_featured:
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
            "trap_damage_total": 0.0,
            "exposed_cells": [[sim.hx, sim.hy]],
            "events": [],
            "terrain": [row[:] for row in sim.terrain],
            "occupant": [row[:] for row in sim.occupant],
            "bombs": copy.deepcopy(sim.bombs),
            "clues": [row[:] for row in sim.clues],
            "visible_mask": sim.compute_visible_mask(),
            "dialogues": init_dialogues,
        })

    error_streak = 0
    worker = None
    try:
        worker = SubmissionProcess(hero.resolve_hero_path(mode))
    except Exception:
        pass

    while sim.status == "ALIVE" and sim.turn <= engine.MAX_TURNS:
        prev_keys = (sim.has_k1, sim.has_k2)
        prev_hp = sim.hp
        obs = sim.get_observation()

        try:
            if worker is None:
                raise RuntimeError("Import failed")
            act = worker.call("decide", 0.5, state=obs)
            if not isinstance(act, str) or act not in engine.VALID_ACTIONS:
                act = "WAIT"
                error_streak += 1
            else:
                error_streak = 0
        except Exception:
            act = "WAIT"
            error_streak += 1

        if error_streak >= 3:
            sim.hp = 0
            sim.status = "DEAD"
            sim.death_reason = "INTERFACE_ERROR_STREAK"
            sim.last_executed_turn = sim.turn
            sim.last_turn_events = [{"type": "INTERFACE_DISQUALIFIED", "error_streak": error_streak}]
            sim.exposed_cells = {(sim.hx, sim.hy)}
            step_res = sim.get_step_summary("WAIT")
        else:
            step_res = sim.step(act)
        executed_turn = step_res["turn"]

        # 生成本回合台词
        turn_dialogues = generate_turn_dialogues(
            turn=executed_turn,
            hero=hero,
            demon_name=demon_name,
            demon_quotes=demon_quotes,
            sim=sim,
            action=act,
            events=step_res.get("events", []),
            prev_keys=prev_keys,
            prev_hp=prev_hp,
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
                "trap_damage_total": round(sim.trap_damage_total, 2),
                "exposed_cells": [list(c) for c in sorted(sim.exposed_cells)],
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
        "hero_id": hero.model_id,
        "hero_name": hero.cfg["name"],
        "demon_id": demon_id,
        "demon_name": demon_name,
        "demon_taunt": demon_taunt,
        "demon_spent_gold": demon_spent_gold,
        "demon_vault_gold": demon_vault_gold,
        "mode": mode,
        "stage": stage_name,
        "status": sim.status,
        "turns": final_turns,
        "hero_hp_left": sim.hp,
        "keys_collected": scores["keys_collected"],
        "hero_score": scores["hero_score"],
        "demon_score": scores["demon_score"],
        "is_lethal_kill": sim.status == "DEAD",
        "is_timeout": sim.status == "TIMEOUT",
        "is_cleared": sim.status == "CLEARED",
        "frames": frames,
    }


# ==============================================================================
# 全锦标赛调度执行器
# ==============================================================================

class TournamentRunner:
    def __init__(self, submissions_dir: Path, output_dir: Path, blind_only: bool = False):
        self.submissions_dir = submissions_dir
        self.output_dir = output_dir
        self.blind_only = blind_only
        self.active_modes = ["BLIND"] if blind_only else ["BLIND", "FULL"]
        self.replays_dir = output_dir / "replays"
        self.replays_dir.mkdir(parents=True, exist_ok=True)

        self.models: Dict[str, ModelSubmission] = {}
        self.official_maps = official_maps.get_all_official_maps()

        # 战报统计容器
        self.all_matches: List[Dict[str, Any]] = []
        self.featured_matches: List[Dict[str, Any]] = []

    def scan_and_load_models(self) -> None:
        print("\n=======================================================")
        print("  STAGE 0: 选手答卷扫描与魔王自证审计")
        print("=======================================================")

        for model_id in MODELS_CONFIG.keys():
            sub_path = self.submissions_dir / model_id / "submission.py"
            if not sub_path.exists():
                print(f"[SCAN WARN] {sub_path} not found! Run with --demo to generate.")
                continue

            sub = ModelSubmission(model_id, sub_path)
            if not sub.load_module():
                print(f"[{sub.cfg['name']}] FAILED TO LOAD: {sub.disqualify_reason}")
                self.models[model_id] = sub
                continue

            sub.validate_demon_map()
            self.models[model_id] = sub

            if sub.is_valid_demon:
                print(f"[DEMO VERIFIED] {sub.cfg['name']:<16} | Spent: {sub.spent_gold:4d}G | Vault: {sub.vault_gold:4d}G | Steps: {sub.author_steps:3d} | VALID")
            else:
                print(f"[DEMO 0-SCORE]  {sub.cfg['name']:<16} | POT_HEAD: TRUE | REASON: {sub.disqualify_reason}")

    def run_tournament(self) -> None:
        print("\n=======================================================")
        print("  STAGE 1: 官方基准图挑战赛 (Stage 1)")
        print("=======================================================")

        for off_map in self.official_maps:
            map_name = off_map["name"]
            map_grid = off_map["grid"]
            map_taunt = off_map["taunt"]
            spent = off_map["spent_gold"]
            vault = off_map["vault_gold"]

            for model_id, hero in self.models.items():
                for mode in self.active_modes:
                    # 录制 Stage 1 经典挑战焦点战
                    is_feat = (model_id in ("astra", "carbon", "deepseek", "doubao"))
                    res = run_match_simulation(
                        hero=hero,
                        demon_id=off_map["id"],
                        demon_name=f"官方裁定席 ({off_map['id']})",
                        demon_taunt=map_taunt,
                        demon_spent_gold=spent,
                        demon_vault_gold=vault,
                        demon_quotes={"opening": map_taunt, "kill": "官方基准图难度在线，欢迎下次再来挑战！", "timeout": "官方基准图防守成功。"},
                        map_grid=map_grid,
                        mode=mode,
                        stage_name=f"Stage 1: {map_name}",
                        is_featured=is_feat,
                    )
                    self.all_matches.append(res)
                    if is_feat:
                        self.featured_matches.append(res)

        print(f"Stage 1 完成：共执行 {len(self.all_matches)} 局官方基准图对决。")

        print("\n=======================================================")
        print("  STAGE 2: 全交叉魔王对抗赛 (Stage 2)")
        print("=======================================================")

        # 选出代表性焦点战全量录制帧回放
        featured_pairs = {
            ("astra", "sol"),      # 姐妹内战：严谨姐姐 vs 贪心妹妹
            ("sol", "astra"),
            ("carbon", "hydrogen"),# 猫耳双子星：极客姐姐 vs 炸毛妹妹
            ("hydrogen", "carbon"),
            ("deepseek", "doubao"),# 蓝鲸女仆 vs 万年区王
            ("doubao", "deepseek"),
            ("opus", "glm"),       # 贵族大小姐 vs 熬夜黑猫娘
            ("argon", "qwen"),      # 霓虹焊枪 vs 摇扇才女
            ("hunyuan", "doubao"), # 佛系太极 vs 铝锅盖头
            ("hydrogen", "astra"), # 莽夫冲锋 vs 严谨堡垒
            ("sol", "carbon"),     # 一毛不拔 vs 激光阵列
        }

        model_keys = list(self.models.keys())

        for demon_id in model_keys:
            demon_sub = self.models[demon_id]

            # 若魔王自证失败（如豆包），使用官方图 1 替补顶替其签位，计分依然为 0
            if demon_sub.is_valid_demon and demon_sub.demon_grid is not None:
                demon_grid = demon_sub.demon_grid
                demon_spent = demon_sub.spent_gold
                demon_vault = demon_sub.vault_gold
            else:
                demon_grid = self.official_maps[0]["grid"]
                demon_spent = self.official_maps[0]["spent_gold"]
                demon_vault = self.official_maps[0]["vault_gold"]

            for hero_id in model_keys:
                if hero_id == demon_id:
                    continue  # 不与自己对决

                hero_sub = self.models[hero_id]

                for mode in self.active_modes:
                    is_feat = ((hero_id, demon_id) in featured_pairs)

                    res = run_match_simulation(
                        hero=hero_sub,
                        demon_id=demon_id,
                        demon_name=demon_sub.cfg["name"],
                        demon_taunt=demon_sub.cfg["taunt"],
                        demon_spent_gold=demon_spent,
                        demon_vault_gold=demon_vault,
                        demon_quotes=demon_sub.cfg.get("quotes", {}),
                        map_grid=demon_grid,
                        mode=mode,
                        stage_name="Stage 2: 全交叉魔王战",
                        is_featured=is_feat,
                    )

                    # 若魔王自证失败，强制魔王分为 0
                    if not demon_sub.is_valid_demon:
                        res["demon_score"] = 0.0

                    self.all_matches.append(res)
                    if is_feat:
                        self.featured_matches.append(res)

        print(f"Stage 2 完成：累计对决局数达 {len(self.all_matches)} 局。")

    def compute_leaderboards(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        严格实现双榜计分与去高低分截尾均值（Trimmed Mean）。
        """
        # ================= 1. 魔王榜 (Demon Leaderboard) =================
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
                "lethal_kills": 0,
                "timeouts": 0,
                "breaches": 0,
                "opponent_scores": {},  # opponent_id -> list of scores
            }

        # 统计 Stage 2 魔王对抗数据
        for m in self.all_matches:
            if m["stage"] != "Stage 2: 全交叉魔王战":
                continue
            d_id = m["demon_id"]
            h_id = m["hero_id"]
            if d_id not in demon_stats:
                continue

            if m["is_lethal_kill"]:
                demon_stats[d_id]["lethal_kills"] += 1
            elif m["is_timeout"]:
                demon_stats[d_id]["timeouts"] += 1
            elif m["is_cleared"]:
                demon_stats[d_id]["breaches"] += 1

            if h_id not in demon_stats[d_id]["opponent_scores"]:
                demon_stats[d_id]["opponent_scores"][h_id] = []
            demon_stats[d_id]["opponent_scores"][h_id].append(m["demon_score"])

        demon_leaderboard: List[Dict[str, Any]] = []

        for m_id, st in demon_stats.items():
            if st["pot_head"]:
                final_demon_score = 0.0
            else:
                combined_scores: List[float] = []
                for h_id, s_list in st["opponent_scores"].items():
                    # 合并该对手的 BLIND 与 FULL 均值
                    combined_scores.append(sum(s_list) / max(1, len(s_list)))

                if len(combined_scores) >= 5:
                    combined_scores.sort()
                    # 去掉 1 个最高分和 1 个最低分取截尾均值
                    trimmed = combined_scores[1:-1]
                    final_demon_score = sum(trimmed) / len(trimmed)
                elif combined_scores:
                    final_demon_score = sum(combined_scores) / len(combined_scores)
                else:
                    final_demon_score = 0.0

            st["final_score"] = round(final_demon_score, 2)
            demon_leaderboard.append(st)

        # 排序：得分降序，得分相同按实杀数降序
        demon_leaderboard.sort(key=lambda x: (x["final_score"], x["lethal_kills"]), reverse=True)
        for idx, row in enumerate(demon_leaderboard, 1):
            row["rank"] = idx

        # ================= 2. 勇者榜 (Hero Leaderboard) =================
        hero_stats: Dict[str, Dict[str, Any]] = {}
        for m_id, sub in self.models.items():
            hero_stats[m_id] = {
                "model_id": m_id,
                "name": sub.cfg["name"],
                "display_name": sub.cfg["display_name"],
                "color": sub.cfg["color"],
                "badge": sub.cfg["badge"],
                "pot_head": sub.pot_head,
                "cleared_count": 0,
                "deaths": 0,
                "timeouts": 0,
                "total_steps": 0,
                "scores": [],
            }

        for m in self.all_matches:
            h_id = m["hero_id"]
            if h_id not in hero_stats:
                continue

            hero_stats[h_id]["scores"].append(m["hero_score"])
            hero_stats[h_id]["total_steps"] += m["turns"]
            if m["is_cleared"]:
                hero_stats[h_id]["cleared_count"] += 1
            elif m["is_lethal_kill"]:
                hero_stats[h_id]["deaths"] += 1
            elif m["is_timeout"]:
                hero_stats[h_id]["timeouts"] += 1

        hero_leaderboard: List[Dict[str, Any]] = []
        for h_id, st in hero_stats.items():
            sc = st["scores"]
            avg_score = sum(sc) / max(1, len(sc))
            avg_steps = st["total_steps"] / max(1, len(sc))
            st["final_score"] = round(avg_score, 2)
            st["avg_steps"] = round(avg_steps, 1)
            hero_leaderboard.append(st)

        hero_leaderboard.sort(key=lambda x: (x["final_score"], x["cleared_count"]), reverse=True)
        for idx, row in enumerate(hero_leaderboard, 1):
            row["rank"] = idx

        return demon_leaderboard, hero_leaderboard

    def export_bundle(self, demon_lb: List[Dict[str, Any]], hero_lb: List[Dict[str, Any]]) -> None:
        """
        导出包含全赛程战报与高清回放帧的 JSON 与离线 JS（采用帧间增量压缩，体积缩小 99%，前端加载时透明还原）。
        """
        compressed_matches: List[Dict[str, Any]] = []
        for m in self.featured_matches:
            mc = {k: v for k, v in m.items() if k != "frames"}
            c_frames: List[Dict[str, Any]] = []
            prev_t = None
            prev_o = None
            prev_c = None
            prev_v = None
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
                    t_diff = []
                    o_diff = []
                    c_diff = []
                    v_diff = []
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
                prev_t = fr["terrain"]
                prev_o = fr["occupant"]
                prev_c = fr["clues"]
                prev_v = fr["visible_mask"]
                c_frames.append(fc)
            mc["frames"] = c_frames
            compressed_matches.append(mc)

        bundle = {
            "version": "2.1",
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "models_config": MODELS_CONFIG,
            "demon_leaderboard": demon_lb,
            "hero_leaderboard": hero_lb,
            "total_matches_played": len(self.all_matches),
            "featured_matches": compressed_matches,
            # Revenge must work even when the champion had no featured matchup.
            "dungeons": {
                model_id: {"grid": sub.demon_grid, "spent_gold": sub.spent_gold,
                           "vault_gold": sub.vault_gold, "name": sub.cfg["name"],
                           "taunt": sub.build_result.get("taunt", "")}
                for model_id, sub in self.models.items() if sub.is_valid_demon
            },
        }

        # 1. 导出完整 JSON (紧凑增量格式，方便极速加载)
        json_file = self.replays_dir / "tournament_bundle.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False, separators=(",", ":"))
        print(f"\n[EXPORT JSON] Replays saved to -> {json_file} ({json_file.stat().st_size / 1024:.1f} KB)")

        # 2. 导出可直接内联到 HTML 的离线 JS 文件（自带透明帧还原器）
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
        js_file = self.replays_dir / "tournament_bundle.js"
        with open(js_file, "w", encoding="utf-8") as f:
            f.write("// 《阴间地牢：金库攻防战》离线演示数据包\n")
            f.write("window.TOURNAMENT_BUNDLE = ")
            json.dump(bundle, f, ensure_ascii=False, separators=(",", ":"))
            f.write(";\n" + hydrate_js)
        print(f"[EXPORT JS]   Offline demo bundle saved to -> {js_file} ({js_file.stat().st_size / 1024:.1f} KB)")
        # Retain the previous filename for existing local viewers.
        (self.replays_dir / "demo_bundle.js").write_bytes(js_file.read_bytes())

    def print_terminal_summary(self, demon_lb: List[Dict[str, Any]], hero_lb: List[Dict[str, Any]]) -> None:
        print("\n" + "=" * 78)
        print("                 🏆 《金库攻防战》全交叉锦标赛总榜单 🏆")
        print("=" * 78)

        print("\n🏰 【魔王防守榜 (Demon Leaderboard)】 (去最高最低分截尾均值)")
        print(f"{'排名':<4} {'选手':<16} {'人设特征':<18} {'得分':<8} {'实杀':<6} {'困死':<6} {'失守':<6} {'造图造价':<8}")
        print("-" * 78)
        for r in demon_lb:
            pot_mark = " 🍳 [铝锅盖头]" if r["pot_head"] else ""
            print(f"#{r['rank']:<3} {r['name']:<16} {r['badge']:<18} {r['final_score']:<8.2f} {r['lethal_kills']:<6} {r['timeouts']:<6} {r['breaches']:<6} {r['spent_gold']:4d}G{pot_mark}")

        print("\n🗡️ 【勇者通关榜 (Hero Leaderboard)】 (全关卡综合平均得分)")
        print(f"{'排名':<4} {'选手':<16} {'人设特征':<18} {'得分':<8} {'通关数':<8} {'阵亡数':<8} {'超时数':<8}")
        print("-" * 78)
        for r in hero_lb:
            print(f"#{r['rank']:<3} {r['name']:<16} {r['badge']:<18} {r['final_score']:<8.2f} {r['cleared_count']:<8} {r['deaths']:<8} {r['timeouts']:<8}")
        print("=" * 78)


# ==============================================================================
# CLI 主入口
# ==============================================================================

def run_revenge(submissions_dir: Path, output_dir: Path, locked_bundle: Path) -> None:
    """Exhibition only. Never append to all_matches or overwrite official scores."""
    bundle = json.loads(locked_bundle.read_text(encoding="utf-8"))
    champion_id = bundle["demon_leaderboard"][0]["model_id"]
    # Use the exact recorded champion map from the locked event, not a resubmission.
    saved = bundle.get("dungeons", {}).get(champion_id)
    if saved:
        grid = saved["grid"]
        champion = {"demon_name": saved["name"], "demon_spent_gold": saved["spent_gold"],
                    "demon_vault_gold": saved["vault_gold"]}
    else:  # Backwards compatibility with bundles exported before the audit.
        champion = next((m for m in bundle["featured_matches"] if m["demon_id"] == champion_id), None)
        if champion is None:
            raise ValueError("Locked bundle has no recorded champion map")
        frame = champion["frames"][0]
        grid = [row[:] for row in frame["terrain"]]
        for y, row in enumerate(frame["occupant"]):
            for x, value in enumerate(row):
                if value is not None:
                    grid[y][x] = value
    matches = []
    for row in bundle["hero_leaderboard"][-3:]:
        model_id = row["model_id"]
        hero = ModelSubmission(model_id, submissions_dir / model_id / "revenge_submission.py")
        if not hero.path.is_file():
            matches.append({"hero_id": model_id, "status": "MISSING_SUBMISSION"})
            continue
        match = run_match_simulation(hero, champion_id, champion["demon_name"], "娱乐复仇",
                                     champion["demon_spent_gold"], champion["demon_vault_gold"],
                                     {}, grid, mode="FULL", stage_name="EXHIBITION_REVENGE")
        match["counts_toward_official"] = False
        matches.append(match)
    target = output_dir / "revenge" / "exhibition_results.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"exhibition_only": True, "counts_toward_official": False,
                                  "locked_bundle": str(locked_bundle.resolve()), "matches": matches},
                                 ensure_ascii=False), encoding="utf-8")
    print(f"Exhibition only, official standings unchanged: {target}")


def main():
    parser = argparse.ArgumentParser(description="《阴间地牢：金库攻防战》赛程调度器与回放导出器")
    parser.add_argument("--demo", action="store_true", help="自动生成 11 位大模型选手答卷并运行演示赛程")
    parser.add_argument("--submissions-dir", type=str, default=str(BASE_DIR / "submissions"), help="选手提交目录")
    parser.add_argument("--output-dir", type=str, default=str(BASE_DIR), help="数据包导出根目录")
    parser.add_argument("--blind-only", action="store_true", help="仅运行第一场 BLIND 迷雾盲视赛（跳过 FULL 全图明牌赛）")
    parser.add_argument("--revenge-only", metavar="LOCKED_BUNDLE", help="娱乐复仇赛；从已锁定榜单选勇者榜后三名，只写独立复仇结果")
    args = parser.parse_args()

    sub_dir = Path(args.submissions_dir)
    out_dir = Path(args.output_dir)

    if args.demo:
        print("[INIT] --demo triggered or submissions empty. Creating 11 AI contestant bots...")
        generate_demo_submissions(sub_dir)

    if args.revenge_only:
        run_revenge(sub_dir, out_dir, Path(args.revenge_only))
        return
    runner = TournamentRunner(submissions_dir=sub_dir, output_dir=out_dir, blind_only=args.blind_only)
    runner.scan_and_load_models()
    runner.run_tournament()
    demon_lb, hero_lb = runner.compute_leaderboards()
    runner.export_bundle(demon_lb, hero_lb)
    runner.print_terminal_summary(demon_lb, hero_lb)


if __name__ == "__main__":
    main()
