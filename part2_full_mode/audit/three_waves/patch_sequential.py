"""Re-run CPU-contention-sensitive matches in strictly 1-worker sequential mode and update all_unique_matches.jsonl.gz + waves."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(r"<REPO_ROOT>/part2_full")
sys.path.insert(0, str(ROOT))

import official_maps_full as omf
import run_tournament_full as rt

OUT = ROOT / "audit" / "three_waves_20261120"
CACHE_PATH = OUT / "all_unique_matches.jsonl.gz"
MANIFEST_PATH = OUT / "versions_manifest.json"

def grid_sha(grid):
    return hashlib.sha256(json.dumps(grid, separators=(",", ":")).encode("utf-8")).hexdigest()

manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
subs = {}
for ver_id, info in manifest.items():
    sub = rt.ModelSubmission(info["seat_id"], Path(info["staged"]))
    sub.ver_id = ver_id
    if sub.load_module():
        sub.validate_demon_map()
    subs[ver_id] = sub

benchmarks = {}
for b_id in ("benchmark_weak", "benchmark_strong"):
    b_sub = rt.ModelSubmission(b_id, ROOT / "benchmarks" / f"{b_id}.py")
    b_sub.ver_id = b_id
    assert b_sub.load_module()
    b_sub.validate_demon_map()
    benchmarks[b_id] = b_sub

official = omf.get_all_official_maps()
map_desc = {}
for m in official:
    map_desc[m["id"]] = dict(grid=m["grid"], gs=grid_sha(m["grid"]), name=f"官方裁定席 ({m['id']})", taunt=m["taunt"], spent=m["spent_gold"], vault=m["vault_gold"])
for bid, bsub in benchmarks.items():
    map_desc[bid] = dict(grid=bsub.demon_grid, gs=grid_sha(bsub.demon_grid), name=bsub.cfg["name"], taunt="", spent=bsub.spent_gold, vault=bsub.vault_gold)
for vid, s in subs.items():
    if s.is_valid_demon:
        map_desc[vid] = dict(grid=s.demon_grid, gs=grid_sha(s.demon_grid), name=s.cfg["name"], taunt="", spent=s.spent_gold, vault=s.vault_gold)

TO_RECHECK = [
    ("sol_39m", "benchmark_strong"),
    ("sol_39m", "sol_17m"),
    ("sol_39m", "opus_quota"),
    ("sol_39m", "glm_38m"),
    ("sol_39m", "qwen_105m"),
    ("sol_39m", "neon_40m"),
    ("sol_17m", "opus_quota"),
    ("astra_39m", "qwen_105m"),
    ("neon_54m", "opus_quota"),
    ("neon_54m", "glm_68m"),
    ("neon_54m", "sol_39m"),
    ("glm_68m", "astra_21m"),
    ("hunyuan_63m", "astra_39m"),
    ("qwen_105m", "OFFICIAL_FULL_03"),
    ("qwen_105m", "opus_quota"),
]

updated = {}
for h_id, m_id in TO_RECHECK:
    hs = subs[h_id]
    md = map_desc[m_id]
    res = rt.run_match_simulation(
        f"SEQ_{h_id}_vs_{m_id}", hs, m_id, md["name"], md["taunt"],
        md["spent"], md["vault"], {}, md["grid"],
        stage_name="CacheSim", is_featured=True, check_spawn=False
    )
    res["_canonical_grid_sha"] = md["gs"]
    updated[(hs.submission_sha256, md["gs"])] = res
    print(f"SEQ {h_id:12s} vs {m_id:18s} => {res['status']:7s} t={res['turns']:3d} hp={res['hero_hp_left']:4d} k={res['keys_collected']} resp={res['worker_respawns']}", flush=True)

# Rewrite CACHE_PATH replacing exact (hero_sha, gs) entries
kept = []
with gzip.open(CACHE_PATH, "rt", encoding="utf-8") as f:
    for l in f:
        r = json.loads(l)
        k = (r["hero_submission_sha256"], r["_canonical_grid_sha"])
        if k in updated:
            continue
        kept.append(r)

with gzip.open(CACHE_PATH, "wt", encoding="utf-8", compresslevel=3) as f:
    for r in kept:
        f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
    for r in updated.values():
        f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

print("Updated CACHE_PATH with", len(updated), "clean sequential records.")
