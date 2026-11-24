"""S1e-2 experiment harness. Read official source/replay bytes and write only local evidence."""
from collections import defaultdict
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from build_s1e import BASE, HERE, WAVE, find_replay, load, versions
from trace_glm_wait import ROOT, rt, SubmissionProcess

LAB=HERE/"s1e2"
LAB.mkdir(exist_ok=True)
AGENTS=("neon","carbon","opus","astra","glm")
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
def save(path,o):
    path.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
def source(a):
    entry=versions[a][1]
    raw=Path(entry["staged"]).read_bytes()
    assert digest(raw)==entry["sha256"]
    return raw

def get_refs():
    wanted=defaultdict(dict)
    for a in AGENTS:
        r=find_replay(a,"攻","terminal","benchmark_strong")
        wanted[r["file"]][r["jsonl_line"]]=(a,r)
    refs={}
    for name,w in wanted.items():
        with gzip.open(name,"rt",encoding="utf8") as f:
            for n,line in enumerate(f,1):
                if n not in w:
                    continue
                a,r=w.pop(n)
                obj=json.loads(line)
                assert obj["match_id"]==r["replay_match_id"]
                assert obj["hero_submission_sha256"]==digest(source(a))
                refs[a]=obj
                if not w:
                    break
    return refs

def verify_glm(ref):
    version,entry=versions["glm"]
    archived=ref["hero_submission_sha256"]
    final=load(WAVE/"wave3_final_11seats/matches.json")
    row=next(r for r in final if r["match_id"]==find_replay("glm","攻","terminal","benchmark_strong")["match_id"])
    ref_grid=[[o or t for o,t in zip(orow,trow)] for orow,trow in zip(ref["frames"][0]["occupant"],ref["frames"][0]["terrain"])]
    assert row["demon_submission_sha256"]==ref["demon_submission_sha256"]
    assert row["status"]==ref["status"] and row["turns"]==ref["turns"]
    out=dict(version=version,staged_file=entry["staged"],historical_file=entry["orig"],
             staged_sha256=digest(source("glm")),historical_sha256=digest(Path(entry["orig"]).read_bytes()),
             replay_hero_sha256=archived,wave3_hero_sha256=row["hero_submission_sha256"],
             wave3_match=row["match_id"],replay_match=ref["match_id"],grid_sha256=digest(json.dumps(ref_grid,separators=(",",":")).encode()),
             wait_start=12,wait_end=240,
             continuous_wait=sum(fr["action"]=="WAIT" for fr in ref["frames"][12:]),
             turn11_position=ref["frames"][11]["hero_pos"],turn240_position=ref["frames"][-1]["hero_pos"])
    save(LAB/"glm_archive_check.json",out)
    assert len({out[k] for k in ("staged_sha256","historical_sha256","replay_hero_sha256","wave3_hero_sha256")})==1
    assert [fr["turn"] for fr in ref["frames"][12:]]==list(range(12,241)) and out["continuous_wait"]==229
    assert ref["frames"][11]["action"]!="WAIT"
    assert ref["match_id"]=="P2_RETEST_025_glm_vs_benchmark_strong_FULL"
    return out

def strong():
    bench=rt.ModelSubmission("benchmark_strong",ROOT/"benchmarks/benchmark_strong.py")
    bench.validate_demon_map()
    assert bench.is_valid_demon
    return bench

def case_worker():
    raw=(ROOT/"submission_worker_full.py").read_text(encoding="utf-8-sig")
    raw=raw.replace("import json","import json\nimport time as wall_clock\nfrom types import SimpleNamespace",1)
    old="                namespace = load_source(request['source'])"
    assert raw.count(old)==1
    new=old+"""
                if request.get('clock_rate', 1) == 0.5:
                    clock_start = wall_clock.monotonic()
                    namespace['time'] = SimpleNamespace(monotonic=lambda: clock_start + (wall_clock.monotonic() - clock_start) * 0.5)
"""
    path=LAB/"case_worker.py"
    path.write_text(raw.replace(old,new),encoding="utf8")
    return path

class LocalWorker(SubmissionProcess):
    def __init__(self,path,worker,clock_rate=1):
        self.worker_path=worker
        self.clock_rate=clock_rate
        super().__init__(path)
    def respawn(self):
        self.close()
        self.replies=queue.Queue()
        self.process=subprocess.Popen([sys.executable,"-I","-u",str(self.worker_path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,text=True,encoding="utf-8",creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        threading.Thread(target=self._read,daemon=True).start()
        try:
            self._receive(5)
            self.call("load",1.5,source=self.locked_source,clock_rate=self.clock_rate)
        except BaseException:
            self.close()
            raise

def first_push(raw):
    target=b"            if ww2.occ != ww.occ:\n                break\n"
    text=raw.replace(b"\r\n",b"\n")
    assert text.count(target)==1
    # Only admit the first step of an otherwise-truncated prefix, and only when it actually pushes an adjacent box.
    changed=b"""            if ww2.occ != ww.occ:
                if not safe_prefix and (ww2.hx, ww2.hy) != (ww.hx, ww.hy) and ww.occ.get((ww2.hx, ww2.hy)) == "BOX" and ww2.status != "DEAD" and ww2.hp >= ww.hp:
                    safe_prefix.append(act)
                break
"""
    return text.replace(target,changed)

class CaseHero(rt.ModelSubmission):
    def create_worker(self):
        return LocalWorker(self.path_for_case,self.worker_for_case,self.clock_for_case)

def experiment():
    from trace_glm_wait import get_reference
    ref=get_reference()
    print("verified",verify_glm(ref),flush=True)
    bench=strong()
    assert bench.submission_sha256==ref["demon_submission_sha256"]
    worker=case_worker()
    raw=source("glm")
    cfg={"A":(raw,.5),"B":(first_push(raw),1),"C":(first_push(raw),.5)}
    for v,(code,rate) in cfg.items():
        (LAB/f"glm_{v}_submission.py").write_bytes(code)
    assert digest((LAB/"glm_A_submission.py").read_bytes())==digest(raw)
    dest=LAB/"glm_counterfactual_runs.jsonl"
    done={}
    if dest.exists():
        done={(o["variant"],o["replicate"]):o for o in (json.loads(line) for line in dest.read_text(encoding="utf8").splitlines())}
    for rep,v in itertools.product(range(1,4),cfg):
        if (v,rep) in done:
            continue
        _,rate=cfg[v]
        src=LAB/f"glm_{v}_submission.py"
        h=CaseHero(f"glm_{v}",src)
        h.path_for_case=src
        h.worker_for_case=worker
        h.clock_for_case=rate
        start=time.perf_counter()
        match=rt.run_match_simulation(f"S1e2_GLM_{v}_{rep}",h,"benchmark_strong","benchmark_strong","",
                                      bench.spent_gold,bench.vault_gold,{},bench.demon_grid)
        frames=match["frames"]
        details=dict(variant=v,replicate=rep,status=match["status"],turns=match["turns"],hp=match["hero_hp_left"],
                     keys=match["keys_collected"],death_reason=match["death_reason"],elapsed_seconds=time.perf_counter()-start,
                     first12=[f["action"] for f in frames[1:13]],wait_count=sum(f["action"]=="WAIT" for f in frames[1:]),
                     source_sha256=digest(src.read_bytes()),search_clock_rate=rate,judge_timeout_s=[2.0,0.5],
                     replay_file=str(LAB/f"glm_case_{v}_{rep}.json"))
        save(Path(details["replay_file"]),match)
        with dest.open("a",encoding="utf8") as f:
            f.write(json.dumps(details,ensure_ascii=False)+"\n")
        print(v,rep,details["status"],details["turns"],details["hp"],details["death_reason"],flush=True)

if __name__=="__main__":
    experiment()

