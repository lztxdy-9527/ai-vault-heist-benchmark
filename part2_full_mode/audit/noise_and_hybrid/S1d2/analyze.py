import argparse
import csv
import gzip
import json
import math
import random
import re
from collections import Counter
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from statistics import correlation, median, quantiles

from run_noise import HERE, ROOT, OLD, S1D, TARGETS, WAVE, digest, read, write

WAVE2 = "wave2_60m_reinforcements"
P6_WAVES = ROOT / "frontend_v2/data/part2_wave_data.js"
CODE_STATS = ROOT / "frontend_v3/stage_common_v3.js"
BOOTSTRAP_SEED = 20261122
BOOTSTRAP_DRAWS = 10000


def trimmed(scores):
    if len(scores) >= 5:
        scores = sorted(scores)[1:-1]
    return sum(scores) / len(scores) if scores else 0.0


def score_groups(rows, sid):
    attack = [r for r in rows if "_BENCH_" not in r["match_id"] and r["hero_id"] == sid]
    defense = [r for r in rows if r["stage"].startswith("Stage 2:") and r["demon_id"] == sid]
    return attack, defense


def board(template, rows, attack_versions):
    out = deepcopy(template)
    seats = {r["model_id"]: r for r in out["hero_leaderboard"]}
    defenses = {r["model_id"]: r for r in out["demon_leaderboard"]}
    order = {ver: i for i, ver in enumerate(out["roster"])}
    bench = [r for r in rows if "_BENCH_" in r["match_id"]]
    weak_h = [r["hero_score"] for r in bench if r["hero_id"] == "benchmark_weak"
              and (r["demon_id"] in seats or r["demon_id"].startswith("OFFICIAL_"))]
    weak_h = sum(weak_h) / len(weak_h)
    weak_d = trimmed([r["demon_score"] for r in bench if r["demon_id"] == "benchmark_weak"
                      and r["hero_id"] in seats])
    out.update(weak_hero_baseline=round(weak_h, 2), weak_demon_baseline=round(weak_d, 2))
    for sid, hero in seats.items():
        demon = defenses[sid]
        attack, defense = score_groups(rows, sid)
        attack_score = sum(r["hero_score"] for r in attack) / len(attack)
        defense_score = 0.0 if demon["pot_head"] else trimmed([r["demon_score"] for r in defense])
        hero.update(_raw=attack_score, final_score=round(attack_score, 2),
                    rel_to_weak_score=round(attack_score - weak_h, 2),
                    below_weak_benchmark=attack_score < weak_h, total_matches=len(attack),
                    avg_steps=round(sum(r["turns"] for r in attack) / len(attack), 1),
                    cleared_count=sum(r["is_cleared"] for r in attack),
                    deaths=sum(r["is_lethal_kill"] for r in attack),
                    timeouts=sum(r["is_timeout"] for r in attack),
                    dqs=sum(r["is_dq"] for r in attack),
                    submission_sha256=attack_versions[sid])
        demon.update(_raw=defense_score, final_score=round(defense_score, 2),
                     rel_to_weak_score=round(defense_score - weak_d, 2),
                     below_weak_benchmark=defense_score < weak_d,
                     lethal_kills=sum(r["is_lethal_kill"] for r in defense),
                     timeouts=sum(r["is_timeout"] for r in defense),
                     breaches=sum(r["is_cleared"] for r in defense),
                     dqs=sum(r["is_dq"] for r in defense))
    for side, tie in (("hero", "cleared_count"), ("demon", "lethal_kills")):
        items = out[f"{side}_leaderboard"]
        items.sort(key=lambda r: (-r["_raw"], -r[tie], order[r["ver_id"]]))
        for rank, item in enumerate(items, 1):
            item.pop("_raw")
            item["rank"] = rank
    overall = []
    for hero in out["hero_leaderboard"]:
        sid = hero["model_id"]
        demon = defenses[sid]
        total = round(hero["final_score"] + demon["final_score"], 2)
        dual = (Decimal(str(total)) / 2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        overall.append(dict(model_id=sid, name=hero["name"], hero=hero["final_score"],
                            demon=demon["final_score"], total=total, dual_average=float(dual),
                            hero_rank=hero["rank"], demon_rank=demon["rank"],
                            wins=hero["cleared_count"], kills=demon["lethal_kills"],
                            timeouts=hero["timeouts"], breaches=demon["breaches"]))
    overall.sort(key=lambda r: (-r["total"], r["hero_rank"]))
    for rank, row in enumerate(overall, 1):
        row["rank"] = rank
    out["overall_leaderboard"] = overall
    return out


def build_hybrid(out):
    replay_index = {r["match_id"]: r for r in read(S1D / "changed_replay_index.json")}
    original_manifest = read(OLD / "versions_manifest.json")
    rerun_manifest = read(S1D / "versions_manifest.json")
    config = read(S1D / "run_config.json")
    assert original_manifest["opus_quota"]["sha256"] == config["before_sha256"]
    assert rerun_manifest["opus_quota"]["sha256"] == config["after_sha256"]
    boards = {}
    for wave, expected_swaps in ((WAVE2, 14), (WAVE, 15)):
        original_path = OLD / wave / "matches.json"
        rerun_path = S1D / wave / "matches.json"
        original, rerun = read(original_path), read(rerun_path)
        original_bundle = OLD / wave / "replays/tournament_results_full.json"
        original_replays = read(original_bundle)["featured_matches"]
        original_replay_indices = {r["match_id"]: i for i, r in enumerate(original_replays)}
        template = read(OLD / wave / "leaderboard.json")
        original_hashes = {r["model_id"]: r["submission_sha256"] for r in template["hero_leaderboard"]}
        original_check = board(template, original, original_hashes)
        assert all(original_check[key] == value for key, value in template.items()), wave
        rerun_board = read(S1D / wave / "leaderboard.json")
        rerun_hashes = {r["model_id"]: r["submission_sha256"] for r in rerun_board["hero_leaderboard"]}
        rerun_check = board(rerun_board, rerun, rerun_hashes)
        assert all(rerun_check[key] == rerun_board[key] for key in template), wave
        selected = []
        assert len(original) == len(rerun)
        for idx, (before, after) in enumerate(zip(original, rerun)):
            assert before["match_id"] == after["match_id"]
            use_rerun = before["hero_id"] == "opus"
            row = after if use_rerun else before
            source = "rerun" if use_rerun else "original"
            provenance = dict(path=str(rerun_path if use_rerun else original_path), json_index=idx)
            if use_rerun:
                assert before["hero_submission_sha256"] == config["before_sha256"]
                assert after["hero_submission_sha256"] == config["after_sha256"]
                for key in ("hero_id", "demon_id", "stage", "_canonical_grid_sha", "actual_map_id",
                            "demon_submission_sha256"):
                    assert before[key] == after[key], (before["match_id"], key)
                replay = replay_index[row["match_id"]]
                assert replay["hero_sha256"] == row["hero_submission_sha256"]
                assert replay["map_grid_sha256"] == row["_canonical_grid_sha"]
                provenance.update(replay_path=str(S1D / "changed_unique_replays.jsonl.gz"),
                                  replay_match_id=replay["replay_match_id"])
            else:
                index = original_replay_indices[row["match_id"]]
                replay = original_replays[index]
                assert replay["frames"] and all(replay[k] == v for k, v in row.items())
                provenance.update(replay_path=str(original_bundle), replay_match_id=row["match_id"],
                                  replay_json_locator=f"featured_matches[{index}]")
                if before["demon_id"] == "opus":
                    assert before["_canonical_grid_sha"] == config["identical_opus_defense_grid_sha256"]
            selected.append(dict(row, source=source, provenance=provenance))
        counts = Counter(row["source"] for row in selected)
        assert counts["rerun"] == expected_swaps
        dest = out / wave
        dest.mkdir(exist_ok=True)
        write(dest / "matches.json", selected)
        result = board(template, selected, rerun_hashes)
        result.update(source_counts=dict(counts), post_hoc=True, source_kind="rerun",
                      source_rule="Opus attack: rerun. All other matches: original.")
        write(dest / "leaderboard.json", result)
        boards[wave] = result
    actual = {r["model_id"]: r for r in boards[WAVE]["overall_leaderboard"]}
    expected = dict(opus=dict(hero=533.31, demon=468.34, total=1001.65, rank=5),
                    sol=dict(total=994.26), neon=dict(total=1134.42), hunyuan=dict(total=499.45))
    check = {sid: {key: {"expected": value, "actual": actual[sid][key],
                         "match": value == actual[sid][key]} for key, value in fields.items()}
             for sid, fields in expected.items()}
    write(out / "leaderboard.json", dict(waves=boards, commander_check=check))
    return boards


def ranks(values):
    ordered = sorted(values)
    return [(ordered.index(v) + 1 + len(ordered) - ordered[::-1].index(v)) / 2 for v in values]


def spearman(xs, ys):
    rho = correlation(ranks(xs), ranks(ys))
    # The usual two-sided t approximation, integrated in angular coordinates.
    df = len(xs) - 2
    start = math.asin(min(1, abs(rho)))
    segments = 1024
    step = (math.pi / 2 - start) / segments
    integrand = [math.cos(start + i * step) ** (df - 1) for i in range(segments + 1)]
    integral = step / 3 * (integrand[0] + integrand[-1] + 4 * sum(integrand[1:-1:2])
                           + 2 * sum(integrand[2:-1:2]))
    p = 2 * math.gamma((df + 1) / 2) / (math.sqrt(math.pi) * math.gamma(df / 2)) * integral
    return dict(rho=round(rho, 8), p=round(p, 8), n=len(xs))


def charts(boards, out):
    manifest = read(S1D / "versions_manifest.json")
    p6 = json.loads(P6_WAVES.read_text(encoding="utf-8-sig").split("=", 1)[1].strip().rstrip(";"))
    code_stats = CODE_STATS.read_text(encoding="utf-8-sig").split("const CODE_STATS = [", 1)[1].split("];", 1)[0]
    displayed = {sid: int(lines) for sid, lines in re.findall(r'id: "(\w+)",\s*lines: (\d+)', code_stats)}
    line_counts = {}
    for version in boards[WAVE]["roster"]:
        row = manifest[version]
        path = Path(row["staged"])
        assert digest(path) == row["sha256"]
        line_counts[row["seat_id"]] = len(path.read_text(encoding="utf-8-sig").splitlines())
    assert displayed == line_counts, (displayed, line_counts)
    points = [dict(row, lines=line_counts[row["model_id"]])
              for row in boards[WAVE]["overall_leaderboard"]]
    length = [r["lines"] for r in points]
    corr = dict(lines_avg=spearman(length, [r["total"] for r in points]),
                lines_demon=spearman(length, [r["demon"] for r in points]))
    stages = ["part1_blind", "wave1_40m_ontime", "wave2_60m", "wave3_final_overtime"]
    curves = deepcopy(p6["revenge_curves"])
    for key, wave in zip(stages[2:], (WAVE2, WAVE)):
        for side in ("hero", "demon"):
            current = {r["model_id"]: r for r in boards[wave][f"{side}_leaderboard"]}
            field = f"revenge_delta_{side}"
            for curve in curves:
                if curve["model_id"] not in current:
                    assert curve["points"][key][side]["unsubmitted"]
                    continue
                record = current[curve["model_id"]]
                point = curve["points"][key][side]
                base = curve["points"][stages[0]][side]["rank"]
                delta = base - record["rank"] if base is not None else None
                point.update(rank=record["rank"], final_score=record["final_score"],
                             ver_id=record["ver_id"], unsubmitted=False, dashed=False)
                point[field] = delta
    data = dict(stage_order=stages, stage_sources={stages[0]: str(P6_WAVES), stages[1]: str(P6_WAVES),
                stages[2]: WAVE2, stages[3]: WAVE}, points=points, spearman=corr,
                revenge_curves=curves, rank_delta_definition=p6["rank_delta_definition"])
    write(out / "p6_chart_data.json", data)
    with (out / "p6_rank_progression.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        csv_writer = csv.writer(handle)
        csv_writer.writerow(["model_id", "phase", "side", "rank", "final_score", "unsubmitted",
                             "rank_delta_vs_part1", "version_id"])
        for curve in curves:
            for stage in stages:
                for side in ("hero", "demon"):
                    p = curve["points"][stage][side]
                    csv_writer.writerow([curve["model_id"], stage, side, p["rank"], p["final_score"],
                                         p["unsubmitted"], p[f"revenge_delta_{side}"], p["ver_id"]])
    return data


def interval(values):
    cuts = quantiles(values, n=20, method="inclusive")
    return [round(cuts[0], 2), round(cuts[-1], 2)]


def distribution(rows):
    stats = {}
    for key in ("turns", "hero_score", "demon_score"):
        values = [r[key] for r in rows]
        stats[key] = [min(values), median(values), max(values)]
    counts = Counter(r["status"] for r in rows)
    return dict(counts={key: counts[key] for key in ("CLEARED", "DEAD", "TIMEOUT", "DQ")},
                worker_respawns=sum(r["worker_respawns"] for r in rows), **stats)


def bootstrap(rows, reference, samples, n, seed):
    rng = random.Random(seed)
    invalid = {r["model_id"] for r in reference["demon_leaderboard"] if r["pot_head"]}
    observed = reference["overall_leaderboard"]
    ids = [r["model_id"] for r in observed]
    groups = {sid: score_groups(rows, sid) for sid in ids}
    totals = {sid: [] for sid in ids}
    new_ranks = {sid: Counter() for sid in ids}
    pairs = [(row["model_id"], other["model_id"]) for row, other in zip(observed, observed[1:])]
    gaps = {pair: [] for pair in pairs}
    initial_order = {r["model_id"]: r["hero_rank"] for r in observed}
    for _ in range(n):
        draw = {mid: rng.choice(outcomes) for mid, outcomes in samples.items()}
        scores = {}
        hero_keys = {}
        for sid, (attack, defense) in groups.items():
            a = [draw.get(row["match_id"], row) for row in attack]
            d = [draw.get(row["match_id"], row) for row in defense]
            hero = sum(row["hero_score"] for row in a) / len(a)
            demon = 0 if sid in invalid else trimmed([row["demon_score"] for row in d])
            scores[sid] = round(round(hero, 2) + round(demon, 2), 2)
            hero_keys[sid] = (-hero, -sum(row["is_cleared"] for row in a), initial_order[sid])
            totals[sid].append(scores[sid])
        ranked = sorted(ids, key=lambda sid: (-scores[sid], *hero_keys[sid]))
        for rank, sid in enumerate(ranked, 1):
            new_ranks[sid][rank] += 1
        for upper, lower in pairs:
            gaps[upper, lower].append(round(scores[upper] - scores[lower], 2))
    seats = {sid: dict(total_p05_p95=interval(totals[sid]), median=median(totals[sid]),
                       rank_counts=dict(sorted(new_ranks[sid].items()))) for sid in ids}
    comparisons = []
    for upper, lower in pairs:
        a, b = [seats[sid]["total_p05_p95"] for sid in (upper, lower)]
        overlap = [max(a[0], b[0]), min(a[1], b[1])]
        delta = gaps[upper, lower]
        comparisons.append(dict(upper=upper, lower=lower, gap_p05_p95=interval(delta),
                                interval_overlap=overlap if overlap[0] <= overlap[1] else None,
                                lower_ahead_fraction=sum(x < 0 for x in delta) / n,
                                equal_score_fraction=sum(x == 0 for x in delta) / n))
    return dict(draws=n, seed=seed, resampled_matches=list(samples), seats=seats, adjacent=comparisons)


def analyze_noise(out, reference):
    fixtures = read(HERE / "noise_config.json")["fixtures"]
    rows = read(out / WAVE / "matches.json")
    by_id = {row["match_id"]: row for row in rows}
    samples = {fixture["baseline"]["match_id"]: [] for fixture in fixtures.values()}
    with (HERE / "noise_samples.jsonl").open(encoding="utf-8") as handle:
        for row in map(json.loads, handle):
            mid = row["match_id"]
            baseline = by_id[mid]
            assert row["baseline_source"] == baseline["source"]
            assert row["grid_sha256"] == baseline["_canonical_grid_sha"]
            assert row["worker_seed"] == 20261115
            assert row["status"] in ("CLEARED", "DEAD", "TIMEOUT", "DQ")
            for key in ("hero_submission_sha256", "demon_submission_sha256", "mode", "hero_id",
                        "demon_id", "demon_spent_gold", "demon_vault_gold"):
                assert row[key] == baseline[key], (mid, key)
            with gzip.open(HERE / row["replay"], "rt", encoding="utf-8") as replay_handle:
                replay = json.load(replay_handle)
            frames = replay.pop("frames")
            assert replay == {k: v for k, v in row.items() if k != "replay"}
            assert frames[0]["turn"] == 0 and frames[-1]["turn"] == row["turns"]
            assert frames[-1]["status"] == row["status"]
            samples[mid].append(row)
    summary = {}
    for mid, outcomes in samples.items():
        assert sorted(r["repetition"] for r in outcomes) == list(range(1, 11)), mid
        assert len({r["run_id"] for r in outcomes}) == 10
        summary[mid] = dict(n=len(outcomes), **distribution(outcomes))
    five = {mid: outcomes for mid, outcomes in samples.items() if by_id[mid]["source"] == "original"}
    assert len(samples) == 7 and len(five) == 5
    write(HERE / "noise_analysis.json", dict(
        distributions=summary,
        bootstrap=bootstrap(rows, reference, samples, BOOTSTRAP_DRAWS, BOOTSTRAP_SEED),
        five_match_sensitivity=bootstrap(rows, reference, five, BOOTSTRAP_DRAWS, BOOTSTRAP_SEED)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--noise", action="store_true")
    options = parser.parse_args()
    out = HERE / "hybrid"
    out.mkdir(exist_ok=True)
    boards = build_hybrid(out)
    data = charts(boards, out)
    print(json.dumps(data["spearman"], ensure_ascii=False))
    if options.noise:
        analyze_noise(out, boards[WAVE])


if __name__ == "__main__":
    main()
