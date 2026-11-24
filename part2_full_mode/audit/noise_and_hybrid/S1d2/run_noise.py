import gzip
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path("<REPO_ROOT>/part2_full")
OLD = ROOT / "audit/three_waves_20261120"
S1D = ROOT / "audit/three_waves_opus1029_20261122"
WAVE = "wave3_final_11seats"
TARGETS = {"M053": "original", "M058": "original", "M052": "original",
           "M054": "original", "M055": "original", "M015": "rerun", "M045": "rerun"}

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main():
    sys.path.insert(0, str(S1D / "reproduce"))
    from rerun_affected import grid_hash, model_from, rt

    config = read(S1D / "run_config.json")
    assert config["worker_seed"] == 20261115
    engine_hashes = {name: digest(ROOT / name) for name in config["engine_inputs"]}
    assert engine_hashes == config["engine_inputs"]
    sources = {"original": OLD, "rerun": S1D}
    manifests = {kind: read(path / "versions_manifest.json") for kind, path in sources.items()}
    rows = {kind: read(path / WAVE / "matches.json") for kind, path in sources.items()}
    models = {}
    fixtures = {}
    for match_number, kind in TARGETS.items():
        row, = [row for row in rows[kind] if row["match_id"].startswith(f"{WAVE}_{match_number}_")]
        for role in ("hero", "demon", "map"):
            version = row["hero_ver"] if role == "hero" else row["actual_map_id"]
            if role == "demon":
                version, = [key for key, info in manifests[kind].items()
                            if info["sha256"] == row["demon_submission_sha256"]]
            manifest = manifests[kind][version]
            if role != "map":
                assert manifest["sha256"] == row[f"{role}_submission_sha256"]
            if manifest["sha256"] not in models:
                models[manifest["sha256"]] = model_from(manifest, version)
        hero = models[row["hero_submission_sha256"]]
        demon = models[row["demon_submission_sha256"]]
        assert hero.loaded and demon.is_valid_demon
        map_grid = models[manifests[kind][row["actual_map_id"]]["sha256"]].demon_grid
        assert grid_hash(map_grid) == row["_canonical_grid_sha"] and demon.demon_grid == map_grid
        assert (demon.spent_gold, demon.vault_gold) == (row["demon_spent_gold"], row["demon_vault_gold"])
        fixtures[match_number] = (kind, row, hero, map_grid)

    write(HERE / "noise_config.json", dict(engine_hashes=engine_hashes, worker_seed=20261115,
          limits=config["limits"], worker_count=1, repetitions=10, python=sys.version,
          platform=platform.platform(), fixtures={number: dict(source=kind, baseline=row)
          for number, (kind, row, _, _) in fixtures.items()}))
    replay_dir = HERE / "noise_replays"
    replay_dir.mkdir(exist_ok=True)
    log_path = HERE / "noise_samples.jsonl"
    done = set()
    if log_path.exists():
        done = {row["run_id"] for row in map(json.loads, log_path.read_text(encoding="utf-8").splitlines())}
    with log_path.open("a", encoding="utf-8") as log:
        for repetition in range(1, 11):
            for kind, row, hero, grid in fixtures.values():
                run_id = f"{row['match_id']}_S1d2_r{repetition:02}"
                if run_id in done:
                    continue
                start = time.perf_counter()
                sim = rt.run_match_simulation(row["match_id"], hero, row["demon_id"], row["demon_name"],
                    row["demon_taunt"], row["demon_spent_gold"], row["demon_vault_gold"], {}, grid,
                    stage_name="CacheSim", is_featured=True, check_spawn=False)
                assert sim["hero_submission_sha256"] == row["hero_submission_sha256"]
                record = dict(sim, run_id=run_id, repetition=repetition, baseline_source=kind,
                              grid_sha256=row["_canonical_grid_sha"], worker_seed=20261115,
                              demon_submission_sha256=row["demon_submission_sha256"],
                              duration_sec=round(time.perf_counter() - start, 3))
                replay_path = replay_dir / f"{run_id}.json.gz"
                with gzip.open(replay_path, "wt", encoding="utf-8", compresslevel=3) as handle:
                    json.dump(record, handle, ensure_ascii=False, separators=(",", ":"))
                record.pop("frames")
                record["replay"] = str(replay_path.relative_to(HERE)).replace("\\", "/")
                log.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                log.flush()
                print(run_id, sim["status"], sim["turns"], sim["hero_score"],
                      sim["demon_score"], record["duration_sec"], flush=True)

if __name__ == "__main__":
    main()
