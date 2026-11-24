"""Bind traces to the final reel and verify the counterfactual outcomes."""
import re
from statistics import mean

from frontier_s1e2 import *
from trace_glm_wait import get_reference
from build_s1e import link

def csv_read(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def timeline(row):
    return [(f["turn"],f["action"],f["hero_pos"],f["hero_hp"]) for f in row["frames"]]

def jsonl_read(path):
    return [json.loads(s) for s in path.read_text(encoding="utf8").splitlines()]

def confirm_deadline(ref):
    """Replay only through the first deadline under A/C and log the real error type."""
    worker=case_worker()
    bench=strong()
    results={}
    for a in ("A","C"):
        assert (LAB/f"glm_{a}_submission.py").is_file()
        dec=rt.engine.validate_and_decode_dungeon(bench.demon_grid,check_spawn=False)
        sim=rt.engine.DungeonSimulator(dec,mode="FULL")
        with LocalWorker(LAB/f"glm_{a}_submission.py",worker,.5) as work:
            for f in ref["frames"][1:8]:
                now=time.perf_counter()
                action=None
                try:
                    action=work.call("decide",2. if f["turn"]==1 else .5,state=sim.get_observation())
                except TimeoutError:
                    results[a]=dict(turn=f["turn"],error="TimeoutError",roundtrip_seconds=time.perf_counter()-now,
                                    timed_out_before_action=True,external_limit_s=.5)
                    break
                assert action==f["action"],(a,f["turn"],action,f["action"])
                sim.step(action)
        assert results[a]["turn"]==7
    save(LAB/"glm_case_deadline_probe.json",results)

def verify():
    original=WAVE.parent/"three_waves_20261120/wave3_final_11seats/replays/tournament_results_full.json"
    hybrid=WAVE/"hybrid/wave3_final_11seats/matches.json"
    original_matches=load(original)["featured_matches"]
    hybrid_rows={x["match_id"]:x for x in load(hybrid)}
    refs=get_refs()
    validation={}
    for a in AGENTS:
        r=refs[a]
        id_=find_replay(a,"攻","terminal","benchmark_strong")["match_id"]
        row=hybrid_rows[id_]
        prov=row["provenance"]
        assert row["hero_submission_sha256"]==r["hero_submission_sha256"]==digest(source(a))
        if a!="opus":
            index=prov["json_index"]
            direct=original_matches[index]
            assert direct["match_id"]==id_ and direct["hero_submission_sha256"]==r["hero_submission_sha256"]
            assert timeline(direct)==timeline(r),(a,"wave3 original differs")
            path,locator=str(original),f"featured_matches[{index}]"
        else:
            assert row["source"]=="rerun" and r["match_id"]==prov["replay_match_id"]
            assert len(source(a).splitlines())==1029
            path,locator=prov["replay_path"],f"JSONL:{find_replay(a,'攻','terminal','benchmark_strong')['jsonl_line']}"
        folder=BASE/a/"search_trace"
        meta=load(folder/"metadata.json")
        turns=csv_read(folder/"per_turn.csv")
        assert len(turns)==meta["compared_turns"]
        differences=[int(t["turn"]) for t in turns if t["selected_action"]!=r["frames"][int(t["turn"])]["action"]]
        assert differences==[i["turn"] for i in meta["mismatches"]]
        assert all(not t["error"] for t in turns)
        frontier_path=folder/("t12_frontier.jsonl" if a=="glm" else "turn1_frontier.jsonl")
        frames=jsonl_read(frontier_path)
        events=[e for f in frames for e in f["events"]]
        assert 60<=len(frames)==meta["frontier"]["frames"]<=200
        expanded=0
        for f in frames:
            expanded+=sum(e["kind"]=="expand" for e in f["events"])
            assert expanded==f["expanded_total"]
        assert [e["seq"] for e in events]==list(range(1,len(events)+1))
        assert all(0<=e["cell"][0]<40 and 0<=e["cell"][1]<26 for e in events if e["cell"] is not None)
        raw=load(LAB/f"raw_frontier_{a}.json")
        assert len(raw)==len(events)
        assert all((e["kind"],e["stage"],e["cell"],e["reason"])==(kind,stage,[x,y] if x>=0 else None,why or None)
                   for e,(kind,stage,x,y,why) in zip(events,raw,strict=True))
        cap=turns[meta["capture_turn"]-1]
        validation[a]=dict(reference_path=path,reference_locator=locator,wave3_match=id_,
                           comparison_turns=len(turns),difference_turns=differences,
                           frontier_file=str(frontier_path),frontier_frames=len(frames),
                           expanded=expanded,discarded=meta["frontier"]["rejected"],
                           expanded_by_stage=json.loads(cap["expanded_by_stage"]),
                           last_expanded_cell=meta["frontier"]["last_expanded_cell"],
                           action=cap["selected_action"],found_full_path=cap["found_full_path"]=="True")
        meta["final_wave3_replay"]=dict(file=path,locator=locator,match_id=id_)
        save(folder/"metadata.json",meta)
    g=verify_glm(refs["glm"])
    g["wave3_original_replay"]=validation["glm"]["reference_path"]
    g["wave3_original_locator"]=validation["glm"]["reference_locator"]
    g["historical_vs_wave3_actions_positions_hp_match"]=True
    save(LAB/"glm_archive_check.json",g)
    trials=jsonl_read(LAB/"glm_counterfactual_runs.jsonl")
    assert {(r["variant"],r["replicate"]) for r in trials}==set(itertools.product("ABC",range(1,4))) and len(trials)==9
    for r in trials:
        case=r["variant"]
        match=load(Path(r["replay_file"]))
        assert (r["status"],r["turns"],r["hp"])==(match["status"],match["turns"],match["hero_hp_left"])
        assert match["hero_submission_sha256"]==r["source_sha256"]==digest((LAB/f"glm_{case}_submission.py").read_bytes())
        if case=="B":
            assert (r["status"],r["turns"],r["hp"],r["keys"])==("CLEARED",120,100,2)
            assert timeline(match)[:12]==timeline(refs["glm"])[:12] and match["frames"][12]["action"]=="MOVE_R"
            assert any(e["type"]=="BOX_MOVE" for e in match["frames"][12]["events"])
        else:
            assert (r["status"],r["turns"],r["hp"],r["death_reason"])==("DQ",9,0,"INTERFACE_ERROR_STREAK")
            assert [f["action"] for f in match["frames"][7:10]]==["WAIT"]*3
    assert source("glm")== (LAB/"glm_A_submission.py").read_bytes()
    assert first_push(source("glm"))==(LAB/"glm_B_submission.py").read_bytes()==(LAB/"glm_C_submission.py").read_bytes()
    save(LAB/"trace_validation.json",validation)
    confirm_deadline(refs["glm"])
    print("Five indexed traces verified, nine outcomes verified, A/C T7 deadline verified.")

if __name__=="__main__":
    verify()

