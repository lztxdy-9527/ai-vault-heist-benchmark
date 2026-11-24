"""Collect Wave 3 replay features and measure cold first moves with contest workers."""
import ast
from collections import Counter,defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=Path("<REPO_ROOT>/part2_full")
ORIG=ROOT/"audit/three_waves_20261120"
RERUN=ROOT/"audit/three_waves_opus1029_20261122"
WAVE="wave3_final_11seats"
sys.path.insert(0,str(ROOT))
import official_maps_full as omf
import run_tournament_full as rt

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def write(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def verified_inputs():
    manifest=read(RERUN/"versions_manifest.json")
    summary=read(RERUN/WAVE/"leaderboard.json")
    matches=read(RERUN/WAVE/"matches.json")
    for version in summary["roster"]:
        entry=manifest[version]
        assert hashlib.sha256(Path(entry["staged"]).read_bytes()).hexdigest()==entry["sha256"]
    return manifest,summary,matches

def sha_grid(grid):
    return hashlib.sha256(json.dumps(grid,separators=(",",":")).encode()).hexdigest()

def collect_replays(manifest,summary,matches):
    newfile=RERUN/"changed_unique_replays.jsonl.gz"
    oldfile=ORIG/"all_unique_matches.jsonl.gz"
    retest=ROOT/"audit/retest_20261119/replays.jsonl.gz"
    aliases={r["match_id"]:r["replay_match_id"] for r in read(RERUN/"changed_replay_index.json") if r["wave"]==WAVE}
    hero_ids={manifest[v]["seat_id"] for v in summary["roster"]}
    roles={"attack":[],"benchmark_attack":[],"benchmark_defense":[]}
    for m in matches:
        if m["hero_id"] in hero_ids:
            roles["benchmark_attack" if m["stage"]==rt.BENCHMARK_STAGE_NAME else "attack"].append(m)
        elif m["demon_id"] in hero_ids and m["stage"]==rt.BENCHMARK_STAGE_NAME:
            roles["benchmark_defense"].append(m)
    wanted=defaultdict(list)
    def key_of(row):
        mid=row["match_id"]
        if mid in aliases:return (str(newfile),aliases[mid])
        if "_canonical_grid_sha" in row:return (str(oldfile),row["hero_submission_sha256"],row["_canonical_grid_sha"])
        map_id=row["actual_map_id"]
        if map_id in manifest:map_id=manifest[map_id]["seat_id"]
        return (str(retest),row["hero_submission_sha256"],map_id)
    for role,data in roles.items():
        for m in data:wanted[key_of(m)].append((role,m))
    got={}
    for path in (oldfile,newfile,retest):
        with gzip.open(path,"rt",encoding="utf-8") as file:
            for n,line in enumerate(file,1):
                # Metadata precedes the portion that contains the frame arrays. The old hash may follow the arrays.
                r=json.loads(line)
                if path==newfile:key=(str(path),r["match_id"])
                elif path==oldfile:key=(str(path),r["hero_submission_sha256"],r["_canonical_grid_sha"])
                else:key=(str(path),r["hero_submission_sha256"],r["actual_map_id"])
                if key not in wanted:continue
                fs=r["frames"]
                assert fs[0]["turn"]==0 and fs[-1]["turn"]==r["turns"]
                counts=Counter()
                samples=defaultdict(list)
                def add(tag,f,details=None,n=1):
                    counts[tag]+=n
                    if len(samples[tag])<8:
                        samples[tag].append(dict(turn=f["turn"],action=f["action"],hero_position=f["hero_pos"],hp=f["hero_hp"],details=details))
                flagged={}
                longest=run=0
                wait_start=None
                for prev,f in zip(fs,fs[1:]):
                    if f["action"]=="WAIT":
                        add("wait",f)
                        run+=1
                        if run>longest:
                            longest=run
                            wait_start=f["turn"]-run+1
                    else:run=0
                    if f["action"].startswith("JUMP_"):add("jump",f)
                    if f["action"].startswith("THROW_"):add("throw",f)
                    if f["plates_active"] and not prev["plates_active"]:
                        add("plate_open",f)
                    if prev["plates_active"] and not f["plates_active"]:
                        add("plate_close",f)
                    types=set()
                    for event in f["events"]:
                        name=event["type"]
                        if name=="LASER_FIRE" and event["hero_hits"]:
                            add("laser_hits",f,{"hero_hits":event["hero_hits"]},event["hero_hits"])
                        if name=="BOX_MOVE":
                            add("box_moves",f,{k:event[k] for k in ("from","to")})
                            if f["terrain"][event["to"][1]][event["to"][0]]=="PLATE":add("box_on_plate",f,event)
                        if name in ("PICK_KEY","BOX_FILL_PIT","BOMB_PLACED","SWITCH_FLIP","CRACK_COLLAPSE","DAMAGE","VAULT_CLEARED"):
                            add(name,f,event)
                        if name=="EXPLOSION_BATCH":
                            add("blast",f,{"sources":event["sources"],"cells":len(event["blast_cells"])})
                            walls=[(x,y) for x,y in event["blast_cells"] if prev["terrain"][y][x]=="W" and f["terrain"][y][x]=="EMPTY"]
                            if walls:add("wall_break",f,{"opened":walls},len(walls))
                        types.add(name)
                for role,m in wanted[key]:
                    assert (m["turns"],m["status"],m["hero_hp_left"],m["hero_submission_sha256"]) == (r["turns"],r["status"],r["hero_hp_left"],r["hero_submission_sha256"]),m["match_id"]
                    g0=[[o or t for o,t in zip(orow,trow)] for orow,trow in zip(fs[0]["occupant"],fs[0]["terrain"])]
                    ctx=dict(role=role,file=str(path),jsonl_line=n,replay_match_id=r["match_id"],grid_from_frame0_sha256=sha_grid(g0),
                             match_id=m["match_id"],map_id=m["actual_map_id"],hero_id=m["hero_id"],demon_id=m["demon_id"],
                             hero_sha256=m["hero_submission_sha256"],demon_sha256=m["demon_submission_sha256"],
                             status=m["status"],turns=m["turns"],hp=m["hero_hp_left"],keys=m["keys_collected"],
                             death_reason=m["death_reason"],metrics=dict(counts),samples=dict(samples),
                             longest_wait={"from":wait_start,"through":wait_start+longest-1 if longest else None,"n":longest},
                             last_events=fs[-1]["events"])
                    got[m["match_id"]]=ctx
    assert len(got)==sum(map(len,roles.values())) and len(roles["attack"])==143, [m["match_id"] for data in roles.values() for m in data if m["match_id"] not in got]
    write(HERE/"wave3_replay_metrics.json",list(got.values()))
    print("replays",len(got),flush=True)

def measure(manifest,summary,matches):
    grids={m["id"]:m["grid"] for m in (*omf.get_all_official_maps(),*omf.get_all_backup_maps())}
    by_id={}
    defense={}
    canonical_ids=set(m["actual_map_id"] for m in matches)
    for v in dict.fromkeys(summary["roster"]+list(sorted(canonical_ids&manifest.keys()))):
        entry=manifest[v]
        sub=rt.ModelSubmission(entry["seat_id"],Path(entry["staged"]))
        assert sub.submission_sha256==entry["sha256"]
        sub.validate_demon_map()
        assert sub.is_valid_demon==entry["valid_demon"],(v,sub.disqualify_reason)
        if sub.is_valid_demon:grids[v]=sub.demon_grid
        if v in summary["roster"]:
            by_id[sub.model_id]=sub
            own=sub.build_result
            assert isinstance(own,dict) and len(own["grid"])==26
            grid=own["grid"]
            design=Counter(t for row in grid[1:-1] for t in row[1:-1] if t!="EMPTY")
            interior_cost=sum(rt.engine.TILE_COSTS.get(k,0)*n for k,n in design.items())
            proof=rt.engine.verify_author_solution(grid,own["author_solution"]) if sub.is_valid_demon else None
            defense[sub.model_id]=dict(sha256=sub.submission_sha256,valid=sub.is_valid_demon,
                 reason=sub.disqualify_reason,fixtures=dict(sorted(design.items())),submitted_interior_cost=interior_cost,
                 build_proof_steps=len(own["author_solution"]),build_proof_hp=proof["author_hp_left"] if proof else None,
                 historic_spent_gold=entry["spent_gold"],historic_author_steps=entry["author_steps"],
                 submitted_grid_sha256=sha_grid(grid),outer_corner_0_0=grid[0][0])
    replay_checks={r["match_id"]:r["grid_from_frame0_sha256"] for r in read(HERE/"wave3_replay_metrics.json")}
    for m in matches:
        if m["stage"]==rt.BENCHMARK_STAGE_NAME or m["hero_id"] not in by_id:continue
        assert sha_grid(grids[m["actual_map_id"]])==m.get("_canonical_grid_sha",replay_checks[m["match_id"]]),m["match_id"]
    write(HERE/"defense_admissions.json",defense)
    with (HERE/"turn1_probe.jsonl").open("w",encoding="utf-8") as f:
        for v in summary["roster"]:
            a=manifest[v]["seat_id"]
            sub=by_id[a]
            for m in matches:
                if m["stage"]==rt.BENCHMARK_STAGE_NAME or m["hero_id"]!=a:continue
                dec=rt.engine.validate_and_decode_dungeon(grids[m["actual_map_id"]],check_spawn=False)
                obs=rt.engine.DungeonSimulator(dec,mode="FULL").get_observation()
                assert obs["turn"]==1
                with sub.create_worker() as worker:
                    start=time.perf_counter()
                    error=None
                    try:
                        act=worker.call("decide",2,state=obs)
                        if act not in rt.engine.VALID_ACTIONS:error="illegal_action"
                    except Exception as exc:
                        act=None
                        error=type(exc).__name__
                    elapsed=time.perf_counter()-start
                f.write(json.dumps(dict(agent=a,sha256=sub.submission_sha256,match_id=m["match_id"],map_id=m["actual_map_id"],
                    first_action=act,time_sec=elapsed,error=error),ensure_ascii=False,separators=(",",":"))+"\n")
            f.flush()
            print("turn1",a,flush=True)

if __name__=="__main__":
    inp=verified_inputs()
    if sys.argv[-1]!="measure":collect_replays(*inp)
    if sys.argv[-1]!="replays":measure(*inp)

