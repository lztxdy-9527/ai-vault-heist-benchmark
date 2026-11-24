import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path("<REPO_ROOT>/part2_full")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import run_tournament_full as rt

SOURCE = ROOT / "scratch/opus_resumed_run/submission.py"
TARGET_HASH = "d9239b39f24227d988508182a941338d164ef580e1d9eb0ec3ca133ae53375f2"

class ObservedWorker:
    def __init__(self, worker, records):
        self.worker = worker
        self.records = records
    def __getattr__(self, name):
        return getattr(self.worker, name)
    def call(self, op, timeout, **payload):
        t0 = perf_counter()
        error = None
        try:
            result = self.worker.call(op, timeout, **payload)
            if op == "decide" and result not in rt.engine.VALID_ACTIONS:
                error = "invalid_action"
            return result
        except Exception as exc:
            error = type(exc).__name__
            raise
        finally:
            self.records.append(dict(op=op, turn=payload.get("state", {}).get("turn"), cap_sec=timeout,
                                     elapsed_sec=perf_counter()-t0, error=error))
    def __enter__(self):
        return self
    def __exit__(self,*args):
        self.worker.close()

class MeasuredSubmission(rt.ModelSubmission):
    def __init__(self, model_id, path):
        super().__init__(model_id,path)
        self.records = []
    def create_worker(self):
        return ObservedWorker(super().create_worker(),self.records)

def bench(sub, bid):
    b = rt.ModelSubmission(bid,ROOT/"benchmarks"/(bid+".py"))
    assert b.load_module(), b.disqualify_reason
    b.validate_demon_map()
    assert b.is_valid_demon, b.disqualify_reason
    sub.records.clear()
    result=rt.run_match_simulation("S1d_gate_"+bid,sub,bid,b.cfg["name"],b.cfg["taunt"],b.spent_gold,b.vault_gold,
                                    {},b.demon_grid,is_featured=False,check_spawn=False)
    result.pop("frames")
    return dict(match=result, timings=list(sub.records), defense_hash=b.submission_sha256)

def main():
    sub=MeasuredSubmission("opus",SOURCE)
    assert sub.submission_sha256 == TARGET_HASH
    start=perf_counter()
    loaded=sub.load_module()
    load_wall=perf_counter()-start
    if loaded:
        sub.validate_demon_map()
    report=dict(sha256=sub.submission_sha256, loaded=loaded, valid_demon=sub.is_valid_demon,
                reason=sub.disqualify_reason, worker_start_and_load_sec=load_wall,
                build_calls=list(sub.records), spent_gold=sub.spent_gold, vault_gold=sub.vault_gold,
                author_steps=sub.author_steps)
    print(json.dumps(report,ensure_ascii=False),flush=True)
    if loaded and sub.is_valid_demon:
        d=rt.engine.validate_and_decode_dungeon(sub.demon_grid)
        report["admission"]={k:v for k,v in d.items() if k in ("safe_t1_coords","valid","reason","safe_spawns","safe_first_steps")}
        report["benchmarks"]={}
        for bid in ("benchmark_weak","benchmark_strong"):
            rec=bench(sub,bid)
            calls=rec["timings"]
            ok=all(not r["error"] for r in calls) and rec["match"]["worker_respawns"]==0 and not rec["match"]["is_dq"]
            rec["timing_pass"]=ok
            report["benchmarks"][bid]=rec
            print(bid,rec["match"]["status"],rec["match"]["turns"],rec["match"]["hero_hp_left"],"T1", calls[0],
                   "max T2+",max((r["elapsed_sec"] for r in calls[1:]),default=0),"errors",sum(bool(r["error"]) for r in calls),flush=True)
            if not ok:
                break
    report["gate_pass"]=loaded and sub.is_valid_demon and len(report.get("benchmarks",{}))==2 and all(
        s["timing_pass"] for s in report["benchmarks"].values())
    (HERE/"gate.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("gate_pass",report["gate_pass"],flush=True)

if __name__=="__main__":
    main()

