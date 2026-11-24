import json
from pathlib import Path

from run_noise import HERE, OLD, S1D, WAVE, digest, read
from analyze import WAVE2

EVIDENCE = HERE.parent.parent
HYBRID = S1D / "hybrid"
LABELS = dict(astra="Astra", neon="Neon", hydrogen="Hydrogen", carbon="Carbon", opus="Opus",
              sol="Sol", qwen="Qwen4-Max", glm="GLM", deepseek="DeepSeek", hunyuan="混元 HY4",
              doubao="豆包")
STATUS = dict(CLEARED="通关", DEAD="阵亡", TIMEOUT="超时", DQ="接口判罚")
FOCUS = [("opus", "sol"), ("neon", "hydrogen")]


def link(label, path):
    return f"[{label}](<{path.as_posix()}>)"


def number_range(low_high):
    return f"{low_high[0]:.2f} 至 {low_high[1]:.2f}"


def pair_label(pair):
    return f"{LABELS[pair['upper']]} 对 {LABELS[pair['lower']]}"


def study_report(study, fixtures, board):
    boot = study["bootstrap"]
    sensitivity = {(p["upper"], p["lower"]): p for p in study["five_match_sensitivity"]["adjacent"]}
    pairs = {(p["upper"], p["lower"]): p for p in boot["adjacent"]}
    overlap = [pair for pair in pairs.values() if pair["interval_overlap"] is not None]
    baselines = {f["baseline"]["match_id"]: f["baseline"] for f in fixtures.values()}
    out = [
        "# S1d-2 · 同输入复跑与终局名次波动",
        "",
        "以第三波混合榜为基线，5 场原版攻 Opus 和 2 场 Opus 1029 行版攻 Sol、Hydrogen 各复跑 10 次，共 70 局。"
        "每局启动新的 FULL v2.2 worker，种子固定为原值 20261115。复跑逐场比对勇者、守方和地图的 SHA-256，"
        "引擎与 worker 文件指纹也和 S1d 记录一致。",
        "",
        "本批次按轮交错、单 worker 串行执行。原赛运行器支持 6 并发，并对受影响结果作过串行修补。"
        "壁钟搜索的执行路径可能随机器和调度改变，本批分布对应这次串行观测。",
        "",
        "## 逐对局分布",
        "",
        "每行按「最小 / 中位 / 最大」给出回合数和双方单局原始分。基线栏来自混合榜所采信的赛果。",
        "",
        "| 对局 | 基线结果 / 回合 | 通关 / 阵亡 / 超时 / 判罚 | 回合 | 攻方得分 | 守方得分 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for mid, stats in study["distributions"].items():
        row = baselines[mid]
        label = f"{LABELS[row['hero_id']]} → {LABELS[row['demon_id']]}"
        counts = " / ".join(str(stats["counts"][key]) for key in STATUS)
        steps = " / ".join(f"{x:g}" for x in stats["turns"])
        attack, defense = [" / ".join(f"{x:.2f}" for x in stats[key])
                           for key in ("hero_score", "demon_score")]
        match_number = mid.removeprefix(WAVE + "_").split("_", 1)[0]
        out.append(f"| {label}（{match_number}） | {STATUS[row['status']]} / {row['turns']} | "
                   f"{counts} | {steps} | {attack} | {defense} |")
    respawns = sum(x["worker_respawns"] for x in study["distributions"].values())
    neon_id = next(mid for mid, row in baselines.items() if row["hero_id"] == "neon")
    sol_id = next(mid for mid, row in baselines.items() if row["hero_id"] == "sol")
    neon_clears = study["distributions"][neon_id]["counts"]["CLEARED"]
    sol_respawns = study["distributions"][sol_id]["worker_respawns"]
    out.extend([
        "",
        f"原赛 Neon 在第 {baselines[neon_id]['turns']} 回合阵亡，本批 {neon_clears}/10 局通关。"
        "总分区间采用新测样本的结果频数，混合榜保留原赛这一局，因此两者的分数位置可能不同。",
        "",
        f"全批 worker 重启 {respawns} 次，其中 Sol 攻 Opus 的十局合计 {sol_respawns} 次，"
        f"该场原赛记录为 {baselines[sol_id]['worker_respawns']} 次。引擎按正式决策请求限时处理这些重启，"
        "统计保留其实际结算。逐局记录链接到压缩逐帧回放，保留血量、钥匙、结算和结束原因。"
        f"{link('样本 JSONL', HERE / 'noise_samples.jsonl')} · "
        f"{link('输入与基线', HERE / 'noise_config.json')}。",
        "",
        "## 混合榜总分 90% 区间",
        "",
        f"以 {boot['draws']:,} 次经验 bootstrap 重算终局，抽样种子为 {boot['seed']}。"
        "每轮对每个实测对局有放回抽取一条新样本，取同一条记录的攻守分，场间独立抽样。"
        "未测场次固定为混合榜结果。每轮重新计算攻方均值、守方截尾均值和总分，取第 5、95 百分位。"
        "这些是给定本机复跑样本与固定赛程的总分波动区间。单场仅 10 个样本，区间宽度和换位频率受样本覆盖限制。"
        "零宽区间表示该席在这些代入样本中得分固定。",
        "",
        "| 混合榜名次 | 选手 | 混合总分 | 复跑总分中位数 | 总分 90% 区间 | 模拟名次 |",
        "|---:|---|---:|---:|---:|---|",
    ])
    for row in board["overall_leaderboard"]:
        sid = row["model_id"]
        stats = boot["seats"][sid]
        rank_text = " / ".join(f"#{rank} {count / boot['draws']:.1%}"
                               for rank, count in stats["rank_counts"].items())
        out.append(f"| {row['rank']} | {LABELS[sid]} | {row['total']:.2f} | {stats['median']:.2f} | "
                   f"{number_range(stats['total_p05_p95'])} | {rank_text} |")
    out.extend(["", "## 相邻席位", ""])
    if overlap:
        out.append("90% 总分区间重叠的相邻席位为 " + "、".join(
            f"{pair_label(pair)}（{number_range(pair['interval_overlap'])} 分）" for pair in overlap) + "。")
    else:
        out.append("本批 bootstrap 的相邻席位总分 90% 区间均分离。")
    out.append("")
    scores = {row["model_id"]: row["total"] for row in board["overall_leaderboard"]}
    for upper, lower in FOCUS:
        pair = pairs[(upper, lower)]
        rate = pair["lower_ahead_fraction"]
        reduced_rate = sensitivity[(upper, lower)]["lower_ahead_fraction"]
        lower_name = LABELS[lower]
        tie_rate = pair["equal_score_fraction"]
        out.append(f"- **{pair_label(pair)}**在混合榜差 {scores[upper] - scores[lower]:.2f} 分。"
                   f"同轮分差的 90% 区间为 {number_range(pair['gap_p05_p95'])} 分。"
                   f"{lower_name} 严格反超频率 {rate:.1%}，平分频率 {tie_rate:.1%}。"
                   f"只重抽指定五场时，{lower_name} 严格反超频率为 {reduced_rate:.1%}。")
    out.extend([
        "",
        "分差按混合榜靠前席减靠后席计算，两席的各自区间重叠与否和同轮反超频率是不同指标。"
        f"所有相邻席位和五场敏感性结果见 {link('统计 JSON', HERE / 'noise_analysis.json')}。",
        "",
    ])
    (HERE.parent / "noise_study.md").write_text("\n".join(out), encoding="utf-8")


def append_ledger(study, boards, chart):
    ledger = EVIDENCE / "evidence_ledger_v2.jsonl"
    previous = ledger.read_bytes()
    records = list(map(json.loads, previous.decode("utf-8-sig").splitlines()))
    existing = [row for row in records if row.get("task") == "S1d-2"]
    if existing:
        raise RuntimeError("S1d-2 ledger rows already exist")
    assert previous.endswith(b"\n")
    assert len({r["id"] for r in records}) == len(records)
    index = max(int(r["id"].split("-")[1]) for r in records)
    rows = []

    def add(kind, fact, path, locator, **data):
        rows.append(dict(id=f"E-{index + len(rows) + 1}", agent="opus", t_contest_sec=None,
                         t_wall=None, type=kind, fact=fact, verbatim=None, claim=None,
                         source_path=str(path), source_kind="rerun", grade="C", post_hoc=True,
                         confidence="high", task="S1d-2", json_locator=locator, **data))

    for wave in (WAVE2, WAVE):
        board = boards[wave]
        row = next(r for r in board["overall_leaderboard"] if r["model_id"] == "opus")
        swaps = board["source_counts"]["rerun"]
        add("stat", f"{wave} 仅替换 Opus 攻方 {swaps} 局。"
                    f"Opus 攻 {row['hero']:.2f}、守 {row['demon']:.2f}、总 {row['total']:.2f}，总榜第 {row['rank']}。",
            HYBRID / "leaderboard.json", f"waves.{wave}.overall_leaderboard",
            source_counts=board["source_counts"], opus=row)
    noise = HERE / "noise_analysis.json"
    for mid, dist in study["distributions"].items():
        counts = dist["counts"]
        add("test_batch", f"{mid} 同输入复跑 10 次。"
                          f"{counts['CLEARED']} 通关、{counts['DEAD']} 阵亡、"
                          f"{counts['TIMEOUT']} 超时、{counts['DQ']} 判罚。",
            noise, f"distributions.{mid}", match_id=mid, distribution=dist,
            notes="同引擎、版本、地图及种子。串行执行。")
    boot = study["bootstrap"]
    add("stat", f"第三波按七场实测分布执行 {boot['draws']:,} 次 bootstrap，记录 11 席总分 90% 区间和相邻席位。",
        noise, "bootstrap", notes="其余赛果固定，区间和反超比例仅适用于本批样本。",
        interval_overlap=[p for p in boot["adjacent"] if p["interval_overlap"] is not None],
        adjacent_focus=[p for p in boot["adjacent"] if (p["upper"], p["lower"]) in FOCUS])
    chart_path = HYBRID / "p6_chart_data.json"
    add("stat", "P6 行数与综合均分 Spearman 为 +0.3909，行数与守方分为 +0.0818。",
        chart_path, "spearman", result=chart["spearman"])
    add("stat", "P6 四阶段攻守名次使用第二、第三波混合榜，Part 1 与 40 分钟准点门沿用粗剪数据。",
        chart_path, "revenge_curves", stage_order=chart["stage_order"])
    append = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows)
    data = append.encode("utf-8")
    (EVIDENCE / "s1d2_ledger_append.jsonl").write_bytes(data)
    with ledger.open("ab") as handle:
        handle.write(data)
    assert ledger.read_bytes() == previous + data
    return rows[0]["id"], rows[-1]["id"], len(rows)


def handoff(study, ids):
    boot = study["bootstrap"]
    pair_map = {(p["upper"], p["lower"]): p for p in boot["adjacent"]}
    focus = "、".join(f"{LABELS[lower]} 反超 {LABELS[upper]} {pair_map[(upper, lower)]['lower_ahead_fraction']:.1%}"
                     for upper, lower in FOCUS)
    reversed_pairs = [pair_label(p) for p in pair_map.values()
                      if (p["upper"], p["lower"]) in FOCUS and p["lower_ahead_fraction"] > 0]
    cue = ("「复跑可能换位」有实测样本支持的重点配对为 " + "、".join(reversed_pairs) + "。"
           if reversed_pairs else "本批重点配对均未出现同轮反超。")
    rows = (
        "# S1d-2 · 混合榜单与噪声测量交接\n\n"
        "- **P6 榜单**按 D-09。Opus 终局攻 533.31（第 6）、守 468.34（第 2）、总 1001.65（第 5）、"
        "双榜均分 500.83、四杀。第二波总分 1126.48（第 4）。第三波与总指挥指定值全部吻合。"
        f"{link('混合榜单报告', HERE.parent / 'hybrid_leaderboard.md')} · "
        f"{link('榜单 JSON', HYBRID / 'leaderboard.json')}。\n"
        "- **P5 回放**使用原赛守图四杀，DeepSeek T88、Neon T123、Sol T165、混元 T189。"
        "Opus 攻双基准分别 71 和 117 回合满血通关。逐场赛果和回放来源按各波 matches.json 查找。"
        f"{link('第三波逐场索引', HYBRID / WAVE / 'matches.json')}。\n"
        "- **P6 图表**两项 Spearman ρ 为 +0.3909、+0.0818。四阶段沿用 Part 1 与 P6 准点门，"
        "后两列由混合榜聚合。"
        f"{link('P6 数据 JSON', HYBRID / 'p6_chart_data.json')} · "
        f"{link('四阶段 CSV', HYBRID / 'p6_rank_progression.csv')}。\n"
        f"- **P13 波动**七场各复跑十次，{boot['draws']:,} 次条件 bootstrap。"
        f"在本批样本模型中，{focus}。{cue}"
        f"{link('噪声报告', HERE.parent / 'noise_study.md')}。\n"
        f"- **台账**在 v2 追加 {ids[2]} 条，{ids[0]} 至 {ids[1]}，标记 `post_hoc=true`、`source_kind=rerun`。"
        f"{link('台账追加副本', EVIDENCE / 's1d2_ledger_append.jsonl')}。\n\n"
        "复现时在工作区运行 `python -B 02_evidence/stats/S1d2/run_noise.py`，"
        "完成后运行 `python -B 02_evidence/stats/S1d2/analyze.py --noise`。"
        "脚本读取历史档案，输出到脚本旁。已有样本按 run_id 跳过。"
        "如需开启一批独立复跑，将这两个脚本复制到工作区内的空目录后在那里运行。"
        f"{link('本批运行配置', HERE / 'noise_config.json')}。\n"
    )
    (EVIDENCE / "HANDOFF_S1d2.md").write_text(rows, encoding="utf-8")


def main():
    safe_files = read(S1D / "original_inputs_sha256.json")
    assert all(digest(Path(path)) == sha for path, sha in safe_files.items())
    for local in (HERE / "hybrid").rglob("*"):
        if local.is_file():
            assert digest(local) == digest(HYBRID / local.relative_to(HERE / "hybrid"))
    boards = read(HYBRID / "leaderboard.json")["waves"]
    chart = read(HYBRID / "p6_chart_data.json")
    study = read(HERE / "noise_analysis.json")
    study_report(study, read(HERE / "noise_config.json")["fixtures"], boards[WAVE])
    ids = append_ledger(study, boards, chart)
    handoff(study, ids)
    print(ids)


if __name__ == "__main__":
    main()
