"""Run Wave 1 (~40m), Wave 2 (~60-70m), Wave 3 (90m+ 11-seat Final), and full Old-vs-New version matrix."""
import copy
import gzip
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(r"<REPO_ROOT>/part2_full")
sys.path.insert(0, str(ROOT))

import engine_full as engine
import official_maps_full as omf
import run_tournament_full as rt

OUT = ROOT / "audit" / "three_waves_20261120"
MANIFEST_PATH = OUT / "versions_manifest.json"
CACHE_PATH = OUT / "all_unique_matches.jsonl.gz"

WAVES = {
    "wave1_40m_settled": [
        "astra_39m", "sol_39m", "neon_40m", "opus_40m",
        "deepseek_14m", "glm_38m", "hunyuan_39m", "qwen_39m", "doubao_35m",
    ],
    "wave1_early_21m17m": [
        "astra_21m", "sol_17m", "neon_40m", "opus_40m",
        "deepseek_14m", "glm_38m", "hunyuan_39m", "qwen_39m", "doubao_35m",
    ],
    "wave2_60m_reinforcements": [
        "astra_39m", "sol_39m", "neon_54m", "hunyuan_63m", "hydrogen_64m", "glm_68m",
        "opus_quota", "deepseek_14m", "qwen_39m", "doubao_35m",
    ],
    "wave3_final_11seats": [
        "astra_39m", "sol_39m", "neon_54m", "carbon_108m", "hydrogen_64m",
        "opus_quota", "deepseek_95m", "glm_68m", "hunyuan_63m", "qwen_105m", "doubao_117m",
    ],
}


def grid_sha(grid: List[List[str]]) -> str:
    return hashlib.sha256(json.dumps(grid, separators=(",", ":")).encode("utf-8")).hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    official = omf.get_all_official_maps()
    backups = omf.get_all_backup_maps()

    subs: Dict[str, rt.ModelSubmission] = {}
    for ver_id, info in manifest.items():
        sub = rt.ModelSubmission(info["seat_id"], Path(info["staged"]))
        sub.ver_id = ver_id
        if sub.load_module():
            sub.validate_demon_map()
        subs[ver_id] = sub

    benchmarks: Dict[str, rt.ModelSubmission] = {}
    for b_id in ("benchmark_weak", "benchmark_strong"):
        b_sub = rt.ModelSubmission(b_id, ROOT / "benchmarks" / f"{b_id}.py")
        b_sub.ver_id = b_id
        assert b_sub.load_module()
        b_sub.validate_demon_map()
        assert b_sub.is_valid_demon
        benchmarks[b_id] = b_sub

    # Build canonical map catalog keyed by grid_sha
    # Every map descriptor holds canonical_sha, ref_name, grid, spent_gold, vault_gold, taunt
    map_catalog: Dict[str, Dict[str, Any]] = {}
    for m in official:
        gs = grid_sha(m["grid"])
        map_catalog[gs] = dict(
            grid_sha=gs, map_id=m["id"], name=f"官方裁定席 ({m['id']})",
            taunt=m["taunt"], spent_gold=m["spent_gold"], vault_gold=m["vault_gold"], grid=m["grid"],
        )
    for b_id, b_sub in benchmarks.items():
        gs = grid_sha(b_sub.demon_grid)
        map_catalog[gs] = dict(
            grid_sha=gs, map_id=b_id, name=b_sub.cfg["name"],
            taunt=(b_sub.build_result or {}).get("taunt", b_sub.cfg["taunt"]),
            spent_gold=b_sub.spent_gold, vault_gold=b_sub.vault_gold, grid=b_sub.demon_grid,
        )
    for idx, bm in enumerate(backups[:4]):
        gs = grid_sha(bm["grid"])
        map_catalog[gs] = dict(
            grid_sha=gs, map_id=bm["id"], name=bm["name"],
            taunt=bm.get("taunt", ""), spent_gold=bm["spent_gold"], vault_gold=bm["vault_gold"], grid=bm["grid"],
        )
    ver_demon_sha: Dict[str, str] = {}
    for ver_id, sub in subs.items():
        if sub.is_valid_demon and sub.demon_grid is not None:
            gs = grid_sha(sub.demon_grid)
            ver_demon_sha[ver_id] = gs
            if gs not in map_catalog:
                map_catalog[gs] = dict(
                    grid_sha=gs, map_id=ver_id, name=sub.cfg["name"],
                    taunt=(sub.build_result or {}).get("taunt", sub.cfg["taunt"]),
                    spent_gold=sub.spent_gold, vault_gold=sub.vault_gold, grid=sub.demon_grid,
                )

    print(f"Loaded {len(subs)} version submissions, {len(benchmarks)} benchmarks, {len(map_catalog)} unique map grids.", flush=True)

    # Seed cache from retest_20261119/replays.jsonl.gz using exact (hero_sha, grid_sha)
    cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
    retest_replays = ROOT / "audit" / "retest_20261119" / "replays.jsonl.gz"
    retest_sub_to_grid_sha: Dict[str, str] = {}
    for v_id in ("sol_17m", "carbon_108m", "hydrogen_64m", "deepseek_95m", "glm_68m", "hunyuan_63m"):
        if v_id in ver_demon_sha:
            retest_sub_to_grid_sha[subs[v_id].submission_sha256] = ver_demon_sha[v_id]
    off_by_id = {m["id"]: grid_sha(m["grid"]) for m in official}
    bk_by_id = {m["id"]: grid_sha(m["grid"]) for m in backups}
    bm_by_id = {b_id: grid_sha(b_sub.demon_grid) for b_id, b_sub in benchmarks.items()}

    if retest_replays.exists():
        with gzip.open(retest_replays, "rt", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                hsha = rec.get("hero_submission_sha256")
                amid = rec.get("actual_map_id")
                dsha = rec.get("demon_submission_sha256")
                gs = None
                if amid in off_by_id:
                    gs = off_by_id[amid]
                elif amid in bk_by_id:
                    gs = bk_by_id[amid]
                elif amid in bm_by_id:
                    gs = bm_by_id[amid]
                elif dsha and dsha in retest_sub_to_grid_sha:
                    gs = retest_sub_to_grid_sha[dsha]
                if hsha and gs and gs in map_catalog:
                    # keep clean physics/frames payload
                    cache[(hsha, gs)] = rec
        print(f"Pre-seeded cache from retest_20261119: {len(cache)} exact pairs.", flush=True)

    if CACHE_PATH.exists():
        try:
            with gzip.open(CACHE_PATH, "rt", encoding="utf-8") as f:
                for line in f:
                    rec = json.loads(line)
                    k = (rec["hero_submission_sha256"], rec["_canonical_grid_sha"])
                    cache[k] = rec
        except EOFError:
            pass
        print(f"Total pre-loaded cache after CACHE_PATH: {len(cache)} pairs.", flush=True)

    # Deduplicate hero executables by submission_sha256
    hero_by_sha: Dict[str, rt.ModelSubmission] = {}
    for ver_id, sub in subs.items():
        hero_by_sha.setdefault(sub.submission_sha256, sub)
    for b_id, b_sub in benchmarks.items():
        hero_by_sha.setdefault(b_sub.submission_sha256, b_sub)

    jobs: List[Tuple[str, rt.ModelSubmission, str, Dict[str, Any]]] = []
    for hsha, hsub in hero_by_sha.items():
        for gs, minfo in map_catalog.items():
            if (hsha, gs) not in cache:
                jobs.append((hsha, hsub, gs, minfo))

    print(f"Unique new matches to simulate: {len(jobs)} (total hero payloads={len(hero_by_sha)})", flush=True)

    def run_job(idx: int, item: Tuple[str, rt.ModelSubmission, str, Dict[str, Any]]) -> Dict[str, Any]:
        hsha, hsub, gs, minfo = item
        res = rt.run_match_simulation(
            match_id=f"U_{idx:04d}_{getattr(hsub, 'ver_id', hsub.model_id)}_vs_{minfo['map_id']}",
            hero=hsub,
            demon_id=minfo["map_id"],
            demon_name=minfo["name"],
            demon_taunt=minfo["taunt"],
            demon_spent_gold=minfo["spent_gold"],
            demon_vault_gold=minfo["vault_gold"],
            demon_quotes={},
            map_grid=minfo["grid"],
            stage_name="CacheSim",
            is_featured=True,
            check_spawn=False,
        )
        res["_canonical_grid_sha"] = gs
        print(
            f"[{idx:03d}/{len(jobs)}] {getattr(hsub,'ver_id',hsub.model_id):14s} vs {minfo['map_id']:18s} "
            f"=> {res['status']:7s} t={res['turns']:3d} hp={res['hero_hp_left']:4d} k={res['keys_collected']} resp={res['worker_respawns']}",
            flush=True,
        )
        return res

    if jobs:
        with gzip.open(CACHE_PATH, "at", encoding="utf-8", compresslevel=3) as cf:
            for start in range(0, len(jobs), 6):
                batch = list(enumerate(jobs[start:start + 6], start + 1))
                with ThreadPoolExecutor(max_workers=6) as pool:
                    futs = [pool.submit(run_job, idx, item) for idx, item in batch]
                    results = [f.result() for f in futs]
                for (idx, item), res in zip(batch, results):
                    if res["worker_respawns"] or res["is_dq"]:
                        print(f"  [Confirming isolated #{idx}]", flush=True)
                        res = run_job(idx, item)
                    cache[(item[0], item[2])] = res
                    cf.write(json.dumps(res, ensure_ascii=False, separators=(",", ":")) + "\n")
                cf.flush()

    # Helper to synthesize wave match record from cache
    def build_match(
        wave_name: str,
        match_id: str,
        stage_label: str,
        hero_sub: rt.ModelSubmission,
        demon_id: str,
        demon_name: str,
        demon_taunt: str,
        demon_cfg_quotes: Dict[str, str],
        map_desc: Dict[str, Any],
        demon_valid: bool = True,
        demon_sha: Optional[str] = None,
    ) -> Dict[str, Any]:
        gs = map_desc["grid_sha"]
        base = cache[(hero_sub.submission_sha256, gs)]
        m = copy.deepcopy(base)
        m["match_id"] = match_id
        m["stage"] = stage_label
        m["hero_id"] = hero_sub.model_id
        m["hero_name"] = hero_sub.cfg["name"]
        m["hero_ver"] = getattr(hero_sub, "ver_id", hero_sub.model_id)
        m["hero_submission_sha256"] = hero_sub.submission_sha256
        m["demon_id"] = demon_id
        m["demon_name"] = demon_name
        m["demon_taunt"] = demon_taunt
        m["demon_spent_gold"] = map_desc["spent_gold"]
        m["demon_vault_gold"] = map_desc["vault_gold"]
        m["actual_map_id"] = map_desc["map_id"]
        m["demon_submission_sha256"] = demon_sha
        if not demon_valid:
            m["demon_score"] = 0.0
        return m

    def evaluate_wave(wave_name: str, roster_vers: List[str], write_bundle: bool = True) -> Dict[str, Any]:
        wave_dir = OUT / wave_name
        wave_dir.mkdir(parents=True, exist_ok=True)
        models_map = {subs[v].model_id: subs[v] for v in roster_vers}
        seat_ids = tuple(models_map.keys())
        bk_iter = iter(backups)
        effective_desc: Dict[str, Dict[str, Any]] = {}
        for sid, sub in models_map.items():
            if sub.is_valid_demon:
                effective_desc[sid] = map_catalog[ver_demon_sha[getattr(sub, "ver_id")]]
            else:
                bm = next(bk_iter)
                effective_desc[sid] = map_catalog[grid_sha(bm["grid"])]

        all_matches: List[Dict[str, Any]] = []
        # Stage 1: Official
        for idx_m, om in enumerate(official, 1):
            mdesc = map_catalog[grid_sha(om["grid"])]
            for sid in seat_ids:
                all_matches.append(build_match(
                    wave_name, f"{wave_name}_OFF{idx_m:02d}_{sid}", f"Stage 1: {om['name']}",
                    models_map[sid], om["id"], f"官方裁定席 ({om['id']})", om["taunt"], {}, mdesc, True, None
                ))
        # Stage 2: Cross
        seq = 1
        for d_id in seat_ids:
            dsub = models_map[d_id]
            mdesc = effective_desc[d_id]
            for h_id in seat_ids:
                if h_id == d_id:
                    continue
                all_matches.append(build_match(
                    wave_name, f"{wave_name}_M{seq:03d}_{h_id}_vs_{d_id}", "Stage 2: 全交叉魔王战",
                    models_map[h_id], d_id, dsub.cfg["name"], dsub.cfg["taunt"], {}, mdesc,
                    dsub.is_valid_demon, dsub.submission_sha256
                ))
                seq += 1
        # Stage 1B: Benchmarks
        for b_id, b_sub in benchmarks.items():
            bdesc = map_catalog[grid_sha(b_sub.demon_grid)]
            b_taunt = (b_sub.build_result or {}).get("taunt", b_sub.cfg["taunt"])
            for h_id in seat_ids:
                all_matches.append(build_match(
                    wave_name, f"{wave_name}_BENCH_{b_id.upper()}_DEF_{h_id}", rt.BENCHMARK_STAGE_NAME,
                    models_map[h_id], b_id, b_sub.cfg["name"], b_taunt, {}, bdesc, True, b_sub.submission_sha256
                ))
            for ob_id, ob_sub in benchmarks.items():
                if ob_id != b_id:
                    all_matches.append(build_match(
                        wave_name, f"{wave_name}_BENCH_{b_id.upper()}_DEF_{ob_id}", rt.BENCHMARK_STAGE_NAME,
                        ob_sub, b_id, b_sub.cfg["name"], b_taunt, {}, bdesc, True, b_sub.submission_sha256
                    ))
            for idx_m, om in enumerate(official, 1):
                mdesc = map_catalog[grid_sha(om["grid"])]
                all_matches.append(build_match(
                    wave_name, f"{wave_name}_BENCH_OFF{idx_m:02d}_{b_id}", rt.BENCHMARK_STAGE_NAME,
                    b_sub, om["id"], f"官方裁定席 ({om['id']})", om["taunt"], {}, mdesc, True, None
                ))
            for d_id in seat_ids:
                dsub = models_map[d_id]
                mdesc = effective_desc[d_id]
                all_matches.append(build_match(
                    wave_name, f"{wave_name}_BENCH_{b_id.upper()}_ATT_{d_id}", rt.BENCHMARK_STAGE_NAME,
                    b_sub, d_id, dsub.cfg["name"], dsub.cfg["taunt"], {}, mdesc, dsub.is_valid_demon, dsub.submission_sha256
                ))

        # Compute exact leaderboards matching TournamentRunnerFull
        def trimmed_mean(vals: List[float]) -> float:
            if len(vals) >= 5:
                ordered = sorted(vals)
                t = ordered[1:-1]
                return sum(t) / len(t)
            return (sum(vals) / len(vals)) if vals else 0.0

        bench_matches = [m for m in all_matches if m["stage"] == rt.BENCHMARK_STAGE_NAME]
        weak_d = trimmed_mean([m["demon_score"] for m in bench_matches if m["demon_id"] == "benchmark_weak" and m["hero_id"] in seat_ids])
        weak_h_vals = [m["hero_score"] for m in bench_matches if m["hero_id"] == "benchmark_weak" and (m["demon_id"].startswith("OFFICIAL_") or m["demon_id"] in seat_ids)]
        weak_h = sum(weak_h_vals) / max(1, len(weak_h_vals))

        demon_lb = []
        for sid, sub in models_map.items():
            ms = [m for m in all_matches if m["stage"] == "Stage 2: 全交叉魔王战" and m["demon_id"] == sid]
            kills = sum(1 for m in ms if m["is_lethal_kill"])
            dqs = sum(1 for m in ms if m["is_dq"])
            tos = sum(1 for m in ms if m["is_timeout"])
            breaches = sum(1 for m in ms if m["is_cleared"])
            raw = 0.0 if sub.pot_head else trimmed_mean([m["demon_score"] for m in ms])
            demon_lb.append({
                "model_id": sid, "ver_id": getattr(sub, "ver_id"), "name": sub.cfg["name"],
                "pot_head": sub.pot_head, "spent_gold": sub.spent_gold, "author_steps": sub.author_steps,
                "lethal_kills": kills, "timeouts": tos, "breaches": breaches, "dqs": dqs,
                "final_score": round(raw, 2), "rel_to_weak_score": round(raw - weak_d, 2),
                "below_weak_benchmark": raw < weak_d, "_raw": raw,
                "submission_sha256": sub.submission_sha256,
            })
        demon_lb.sort(key=lambda x: (x["_raw"], x["lethal_kills"]), reverse=True)
        for idx, r in enumerate(demon_lb, 1):
            r.pop("_raw")
            r["rank"] = idx

        hero_lb = []
        for sid, sub in models_map.items():
            ms = [m for m in all_matches if m["stage"] != rt.BENCHMARK_STAGE_NAME and m["hero_id"] == sid]
            sc = [m["hero_score"] for m in ms]
            avg = sum(sc) / max(1, len(sc))
            hero_lb.append({
                "model_id": sid, "ver_id": getattr(sub, "ver_id"), "name": sub.cfg["name"],
                "pot_head": sub.pot_head,
                "cleared_count": sum(1 for m in ms if m["is_cleared"]),
                "total_matches": len(ms),
                "deaths": sum(1 for m in ms if m["is_lethal_kill"]),
                "timeouts": sum(1 for m in ms if m["is_timeout"]),
                "dqs": sum(1 for m in ms if m["is_dq"]),
                "avg_steps": round(sum(m["turns"] for m in ms) / max(1, len(sc)), 1),
                "final_score": round(avg, 2), "rel_to_weak_score": round(avg - weak_h, 2),
                "below_weak_benchmark": avg < weak_h, "_raw": avg,
                "submission_sha256": sub.submission_sha256,
            })
        hero_lb.sort(key=lambda x: (x["_raw"], x["cleared_count"]), reverse=True)
        for idx, r in enumerate(hero_lb, 1):
            r.pop("_raw")
            r["rank"] = idx

        summary = {
            "wave": wave_name,
            "roster": roster_vers,
            "weak_hero_baseline": round(weak_h, 2),
            "weak_demon_baseline": round(weak_d, 2),
            "hero_leaderboard": hero_lb,
            "demon_leaderboard": demon_lb,
        }
        write_json(wave_dir / "leaderboard.json", summary)
        write_json(wave_dir / "matches.json", [{k: v for k, v in m.items() if k != "frames"} for m in all_matches])
        if write_bundle:
            bundle = rt.compress_bundle(
                f"v2.2-FULL-{wave_name}", models_map, demon_lb, hero_lb,
                all_matches, all_matches,
                {"weak_hero_baseline": round(weak_h, 2), "weak_demon_baseline": round(weak_d, 2)},
                benchmarks,
            )
            rt.write_bundle_outputs(wave_dir / "replays", bundle, "tournament_results_full.json", "demo_bundle_full.js", write_demo=True)
        return summary

    all_wave_summaries = {}
    for wname, wroster in WAVES.items():
        print(f"\n=== EVALUATING {wname} ({len(wroster)} seats) ===", flush=True)
        ws = evaluate_wave(wname, wroster, write_bundle=True)
        all_wave_summaries[wname] = ws
        print("  HERO TOP:")
        for r in ws["hero_leaderboard"]:
            print(f"    #{r['rank']:2d} {r['ver_id']:14s} score={r['final_score']:6.2f} (rel={r['rel_to_weak_score']:+7.2f}) C={r['cleared_count']}/{r['total_matches']} D={r['deaths']} TO={r['timeouts']} DQ={r['dqs']}")
        print("  DEMON TOP:")
        for r in ws["demon_leaderboard"]:
            print(f"    #{r['rank']:2d} {r['ver_id']:14s} score={r['final_score']:6.2f} gold={r['spent_gold']:4d} K={r['lethal_kills']} TO={r['timeouts']} B={r['breaches']} pot={r['pot_head']}")

    # Old-vs-New comprehensive comparison across ALL valid unique maps (3 official + 2 bench + 11 valid demon maps)
    eval_maps = []
    seen_gs = set()
    for m in official:
        gs = grid_sha(m["grid"])
        if gs not in seen_gs:
            seen_gs.add(gs); eval_maps.append(("official", m["id"], map_catalog[gs]))
    for b_id, b_sub in benchmarks.items():
        gs = grid_sha(b_sub.demon_grid)
        if gs not in seen_gs:
            seen_gs.add(gs); eval_maps.append(("bench", b_id, map_catalog[gs]))
    for v_id in ["astra_21m","astra_39m","sol_39m","neon_40m","neon_54m","carbon_108m","hydrogen_64m","opus_quota","deepseek_95m","glm_68m","hunyuan_63m","qwen_39m","qwen_105m"]:
        gs = ver_demon_sha[v_id]
        if gs not in seen_gs:
            seen_gs.add(gs); eval_maps.append(("contestant", v_id, map_catalog[gs]))

    version_groups = {
        "astra": ["astra_21m", "astra_39m"],
        "sol": ["sol_17m", "sol_39m"],
        "neon": ["neon_40m", "neon_54m"],
        "opus": ["opus_40m", "opus_quota"],
        "deepseek": ["deepseek_14m", "deepseek_79m", "deepseek_95m"],
        "glm": ["glm_38m", "glm_68m"],
        "hunyuan": ["hunyuan_39m", "hunyuan_63m"],
        "qwen": ["qwen_39m", "qwen_105m"],
        "doubao": ["doubao_35m", "doubao_117m"],
    }
    diffs_report = {}
    for seat, vlist in version_groups.items():
        seat_data = {"versions": {}}
        for v_id in vlist:
            hsha = subs[v_id].submission_sha256
            atk = {}
            for kind, mname, mdesc in eval_maps:
                r = cache[(hsha, mdesc["grid_sha"])]
                atk[mname] = {
                    "status": r["status"], "turns": r["turns"], "hp": r["hero_hp_left"],
                    "keys": r["keys_collected"], "score": round(r["hero_score"], 2), "resp": r["worker_respawns"],
                }
            # Defense summary if valid demon
            defense = {}
            if subs[v_id].is_valid_demon:
                dgs = ver_demon_sha[v_id]
                for att_id in subs:
                    r = cache[(subs[att_id].submission_sha256, dgs)]
                    defense[att_id] = {
                        "status": r["status"], "turns": r["turns"], "keys": r["keys_collected"],
                        "demon_score": round(r["demon_score"], 2),
                    }
            seat_data["versions"][v_id] = {
                "valid_demon": subs[v_id].is_valid_demon,
                "spent_gold": subs[v_id].spent_gold,
                "author_steps": subs[v_id].author_steps,
                "hero_clears": sum(1 for x in atk.values() if x["status"] == "CLEARED"),
                "hero_total": len(atk),
                "hero_avg_score": round(sum(x["score"] for x in atk.values()) / len(atk), 2),
                "attack_details": atk,
                "defense_details": defense,
            }
        # Compute per-opponent changes between first and last version
        if len(vlist) >= 2:
            v_old, v_new = vlist[0], vlist[-1]
            changes = []
            for kind, mname, _ in eval_maps:
                a0 = seat_data["versions"][v_old]["attack_details"][mname]
                a1 = seat_data["versions"][v_new]["attack_details"][mname]
                if a0["status"] != a1["status"] or abs(a0["score"] - a1["score"]) >= 1.0 or a0["turns"] != a1["turns"]:
                    changes.append({"map": mname, "old": a0, "new": a1, "score_delta": round(a1["score"] - a0["score"], 2)})
            seat_data["attack_deltas_first_to_last"] = changes
        diffs_report[seat] = seat_data

    write_json(OUT / "version_diffs_summary.json", diffs_report)
    write_json(OUT / "all_waves_summary.json", all_wave_summaries)
    print("\nALL DONE! Summaries saved under", OUT, flush=True)


if __name__ == "__main__":
    main()
