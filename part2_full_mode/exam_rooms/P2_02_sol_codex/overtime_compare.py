"""A/B replay and deterministic holdouts for the overtime submission."""
import hashlib
import json
import sys
import time
from pathlib import Path

import verify_full as v
import submission as original
import submission_overtime as overtime
import overtime_adversarial as tests


def outcome(s,g,cost,reset=None):
    v.s=s
    w=v.decode(g)
    marks=v.targets(g);clues=v.clue_bind(g)
    targets=[y*40+x for x,y in (marks[k] for k in ("K1","K2","V"))]
    memory={};times=[]
    def distance(p,keys):
        pending=[q for i,q in enumerate(targets[:2]) if not keys&(1<<i)] or targets[2:]
        return min(s._manhattan(p,q) for q in pending)
    start=best=distance(w.p,w.keys)
    for turn in range(1,241):
        if turn==reset:
            memory={}
        state=v.observe(w,turn,marks,clues)
        before=time.perf_counter()
        action=s.decide_action(state,memory)
        duration=time.perf_counter()-before
        times.append(duration)
        assert action in s.ALL_ACTIONS and duration<=(2 if turn==1 else .5),(turn,action,duration)
        after=w.step(action,turn)
        if after.keys!=w.keys:
            start=best=distance(after.p,after.keys)
        else:
            best=min(best,*(distance(p,after.keys) for p in after.exposed))
        w=after
        if w.won or w.hp<=0:
            break
    score=(600+1.5*w.hp+150*(240-turn)/239+100*(3000-cost)/3000
           if w.won else 200*(w.keys.bit_count()+max(0,(start-best)/max(1,start))))
    return dict(status="CLEARED" if w.won else "DEAD" if w.hp<=0 else "TIMEOUT",
                turn=turn,hp=w.hp,keys=w.keys.bit_count(),score=round(score,3),
                first_ms=round(1000*times[0],2),later_max_ms=round(max(times[1:],default=0)*1000,2))


def run(which):
    s=original if which=="original" else overtime
    if which=="holdout":
        for seed in (51719,60941,81523,103841,137029,210361):
            v.s=overtime
            g=tests.directional_trap(seed)
            data=outcome(s,g,v.valid(g),reset=29)
            print(seed,data,flush=True)
        return
    v.s=s
    v.fixtures()
    a=json.loads(Path("part1_dungeons_benchmark.json").read_text(encoding="utf-8"))
    b=json.loads(Path("v22_sparring_benchmarks.json").read_text(encoding="utf-8"))
    results={}
    for key,m in (a["dungeons"]|b["dungeons"]).items():
        data=outcome(s,m["grid"],m["spent_gold"])
        results[key]=data
        print(which,key,data,flush=True)
    attempts=[results[k] for k in a["dungeons"]]
    print(which,"legacy",sum(q["status"]=="CLEARED" for q in attempts),
          "average",round(sum(q["score"] for q in attempts)/len(attempts),3),flush=True)
    p=Path("submission.py" if which=="original" else "submission_overtime.py")
    Path("overtime_results_"+which+".json").write_text(
        json.dumps({"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"results":results},
                   ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    run(sys.argv[1])
