import copy
import gzip
import hashlib
import json
from pathlib import Path
from admission import HERE, ROOT, SOURCE, TARGET_HASH, MeasuredSubmission, rt
import official_maps_full as omf

OLD = ROOT/"audit/three_waves_20261120"
OUTPUT = HERE/"three_waves_opus1029_20261122"
KEY = "opus_quota"
OLD_HASH = "48bc1e613acadabaac0a0e48d0ceb6ea444715ad32539298dc4b83ae55e914ba"

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def grid_hash(grid):
    return hashlib.sha256(json.dumps(grid,separators=(",",":")).encode()).hexdigest()

def affected(row):
    return OLD_HASH in {row.get("hero_submission_sha256"),row.get("demon_submission_sha256")}

def model_from(info, id, measured=False):
    cls = MeasuredSubmission if measured else rt.ModelSubmission
    model = cls(info["seat_id"],Path(info["staged"]))
    assert model.submission_sha256==info["sha256"],id
    model.ver_id=id
    assert model.load_module()==info["loaded"],(id,model.disqualify_reason)
    if model.loaded:
        model.validate_demon_map()
    assert model.is_valid_demon==info["valid_demon"],(id,model.disqualify_reason)
    return model

def main():
    gate=read(HERE/"gate.json")
    assert gate["gate_pass"]
    old_manifest=read(OLD/"versions_manifest.json")
    assert old_manifest[KEY]["sha256"]==OLD_HASH
    old_summaries=read(OLD/"all_waves_summary.json")
    all_rows={name:read(OLD/name/"matches.json") for name in old_summaries}
    assert [sum(map(affected,ms)) for ms in all_rows.values()]==[0,0,25,27]
    contestants={}
    maps={m["id"]:m["grid"] for m in (*omf.get_all_official_maps(),*omf.get_all_backup_maps())}
    for key in old_manifest:
        contestants[key]=sub=model_from(old_manifest[key],key)
        if sub.is_valid_demon:
            maps[key]=sub.demon_grid
    for b in ("benchmark_weak","benchmark_strong"):
        sub=rt.ModelSubmission(b,ROOT/"benchmarks"/(b+".py"))
        sub.ver_id=b
        assert sub.load_module()
        sub.validate_demon_map()
        assert sub.is_valid_demon
        maps[b]=sub.demon_grid
        contestants[b]=sub
    base=contestants[KEY]
    new=MeasuredSubmission("opus",SOURCE)
    assert new.submission_sha256==TARGET_HASH and new.load_module()
    new.validate_demon_map()
    assert new.is_valid_demon
    assert new.demon_grid==base.demon_grid
    assert new.author_solution==base.author_solution
    assert new.spent_gold==base.spent_gold and new.vault_gold==base.vault_gold and new.author_steps==base.author_steps
    new.ver_id=KEY
    contestants[KEY]=new
    new_manifest=copy.deepcopy(old_manifest)
    new_manifest[KEY].update(orig=str(SOURCE),staged=str(SOURCE),sha256=TARGET_HASH,loaded=True,valid_demon=True,
                             spent_gold=new.spent_gold,author_steps=new.author_steps,reason="")
    write(OUTPUT/"versions_manifest.json",new_manifest)
    write(OUTPUT/"admission_and_benchmarks.json",gate)
    hashes={k:hashlib.sha256((ROOT/k).read_bytes()).hexdigest() for k in (
        "run_tournament_full.py","engine_full.py","official_maps_full.py","submission_worker_full.py","submission_sandbox_full.py")}
    write(OUTPUT/"run_config.json",dict(original_directory=str(OLD),worker_seed=20261115,worker_count=1,
          engine_inputs=hashes,waves={k:w["roster"] for k,w in old_summaries.items()},
          identical_opus_defense_grid_sha256=grid_hash(new.demon_grid),identical_author_solution=True,
          limits=dict(import_sec=1.5,build_sec=2.0,first_turn_sec=2.0,later_turn_sec=0.5),
          after_sha256=TARGET_HASH,before_sha256=OLD_HASH))
    # Keep immutable order and metadata. Recompute only source-dependent outcome fields.
    changed_scripts={}
    link_index=[]
    replay=OUTPUT/"changed_unique_replays.jsonl.gz"
    output_summaries={}
    index=0
    with gzip.open(replay,"wt",encoding="utf-8",compresslevel=3) as gz:
        for wave,matches in all_rows.items():
            output=[]
            for old in matches:
                if not affected(old):
                    output.append(old)
                    continue
                sub=contestants[old["hero_ver"]]
                assert sub.submission_sha256==(TARGET_HASH if old["hero_id"]=="opus" else old["hero_submission_sha256"]),old["match_id"]
                grid=maps[old["actual_map_id"]]
                gs=grid_hash(grid)
                assert gs==old["_canonical_grid_sha"],old["match_id"]
                key=(sub.submission_sha256,gs)
                if key not in changed_scripts:
                    index+=1
                    print(f"[{index}] {wave} {old['hero_ver']} vs {old['actual_map_id']}",flush=True)
                    if sub is new:
                        new.records.clear()
                    sim=rt.run_match_simulation(old["match_id"],sub,old["demon_id"],old["demon_name"],old["demon_taunt"],
                          old["demon_spent_gold"],old["demon_vault_gold"],{},grid,
                          stage_name="CacheSim",is_featured=True,check_spawn=False)
                    timings=list(new.records) if sub is new else []
                    if timings:
                        assert not any(r["error"] for r in timings),(old["match_id"],sim["worker_respawns"])
                        assert not sim["worker_respawns"] and not sim["is_dq"],old["match_id"]
                    sim["_canonical_grid_sha"]=gs
                    sim["actual_map_id"]=old["actual_map_id"]
                    sim["demon_submission_sha256"]=TARGET_HASH if old["demon_id"]=="opus" else old["demon_submission_sha256"]
                    sim["hero_ver"]=old["hero_ver"]
                    if timings:
                        sim["worker_call_timings"]=timings
                    gz.write(json.dumps(sim,ensure_ascii=False,separators=(",",":"))+"\n")
                    gz.flush()
                    changed_scripts[key]=(old["match_id"],{
                        field:sim[field] for field in (
                            "status","death_reason","turns","hero_hp_left","keys_collected",
                            "hero_score","demon_score","is_lethal_kill","is_timeout","is_cleared","is_dq","worker_respawns")})
                    print(f"  {sim['status']} T={sim['turns']} HP={sim['hero_hp_left']} H={sim['hero_score']} D={sim['demon_score']}",flush=True)
                replay_id,changes=changed_scripts[key]
                record={**old,**changes,"hero_submission_sha256":sub.submission_sha256,
                        "demon_submission_sha256":TARGET_HASH if old["demon_id"]=="opus" else old["demon_submission_sha256"]}
                defender_invalid=old["actual_map_id"].startswith("BACKUP") and old["demon_id"] in {v["seat_id"] for v in old_manifest.values()}
                if defender_invalid:
                    assert old["demon_score"]==0
                    record["demon_score"]=0.0
                output.append(record)
                link_index.append(dict(wave=wave,match_id=old["match_id"],replay_match_id=replay_id,
                                       hero_sha256=key[0],map_grid_sha256=gs))
            assert [m["match_id"] for m in matches]==[m["match_id"] for m in output]
            write(OUTPUT/wave/"matches.json",output)
    write(OUTPUT/"changed_replay_index.json",link_index)
    print(len(changed_scripts),"unique runs;",len(link_index),"affected wave rows",flush=True)

if __name__=="__main__":
    main()


