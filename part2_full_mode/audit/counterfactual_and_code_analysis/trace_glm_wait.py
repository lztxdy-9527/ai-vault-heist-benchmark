"""Trace the GLM compatibility submission in the official FULL engine with a copied worker."""
import gzip
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path("<REPO_ROOT>/part2_full")
OLD = ROOT / "audit/three_waves_20261120"
sys.path.insert(0, str(ROOT))
import run_tournament_full as rt
from submission_sandbox_full import SubmissionProcess

MANIFEST = json.loads((OLD / "versions_manifest.json").read_text(encoding="utf-8"))
ORIGINAL = Path(MANIFEST["glm_68m"]["staged"])
COPY = HERE / "glm_submission_instrumented.py"
WORKER = HERE / "glm_trace_worker.py"
HISTORICAL = ROOT / "audit/retest_20261119/replays.jsonl.gz"
REFERENCE_ID = "P2_RETEST_025_glm_vs_benchmark_strong_FULL"

def prepare_copy():
    expected = MANIFEST["glm_68m"]["sha256"]
    assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() == expected
    src = ORIGINAL.read_text(encoding="utf-8-sig")
    replacements = [
        ('def _reactive(w, dist):', '''_s1e_trace = {}
def _reactive(w, dist):'''),
        ('    for act in _actions(w, rays) + ["WAIT"]:', '''    _s1e_trace["reactive"] = []
    for act in _actions(w, rays) + ["WAIT"]:'''),
        ('''        if nw.status == "DEAD":
            continue
        if nw.occ != w.occ:
            continue          # 兜底模式绝不推箱''', '''        if nw.status == "DEAD":
            _s1e_trace["reactive"].append([act, "dead", [nw.hx, nw.hy]])
            continue
        if nw.occ != w.occ:
            _s1e_trace["reactive"].append([act, "occupant_change", [nw.hx, nw.hy]])
            continue          # 兜底模式绝不推箱'''),
        ('        sc = (pen, d, 0 if act == "WAIT" else 1)',
         '''        sc = (pen, d, 0 if act == "WAIT" else 1)
        _s1e_trace["reactive"].append([act, "scored", [nw.hx, nw.hy], sc])'''),
        ('''    try:
        act = _decide(state, memory)
        if act in VALID_ACTIONS:
            return act
        return "WAIT"
    except Exception:
        return "WAIT"''', '''    _s1e_trace.clear()
    _s1e_trace["cached_plan_before"] = len(memory.get("plan") or [])
    _s1e_trace["trials"] = []
    try:
        act = _decide(state, memory)
        if act in VALID_ACTIONS:
            return act
        _s1e_trace["invalid"] = str(act)
        return "WAIT"
    except Exception as exc:
        _s1e_trace["exception"] = str(exc)
        return "WAIT"'''),
        ('''    if a is not None:
        return a

    tg =''', '''    if a is not None:
        _s1e_trace["branch"] = "cached_plan"
        return a

    tg ='''),
        ('    best_partial = None\n    for (kind, cell) in trials:',
         '''    _s1e_trace["queued_trials"] = trials
    best_partial = None
    for (kind, cell) in trials:
        trial_t0 = time.monotonic()'''),
        ('''        if complete and res:
            memory["plan"] = res''', '''        _s1e_trace["trials"].append({"kind": kind, "cell": cell, "complete": complete, "nodes": _,
                                      "prefix": res, "elapsed_sec": time.monotonic()-trial_t0,
                                      "remaining_sec": deadline-time.monotonic()})
        if complete and res:
            memory["plan"] = res'''),
        ('''            if a is not None:
                return a
            continue
        if res and best_partial''', '''            if a is not None:
                _s1e_trace["branch"] = "new_complete_plan"
                return a
            continue
        if res and best_partial'''),
        ('''            if ww2.occ != ww.occ:
                break''', '''            if ww2.occ != ww.occ:
                _s1e_trace["partial_cut_at"] = act
                break'''),
        ('''    if best_partial:
        safe_prefix = []''', '''    if best_partial:
        _s1e_trace["partial_in"] = best_partial
        safe_prefix = []'''),
        ('''        if safe_prefix:
            memory["plan"] = safe_prefix''', '''        _s1e_trace["partial_safe"] = safe_prefix
        if safe_prefix:
            memory["plan"] = safe_prefix'''),
        ('''            if a is not None:
                return a
    # 反应式兜底''', '''            if a is not None:
                _s1e_trace["branch"] = "partial_plan"
                return a
    # 反应式兜底'''),
        ('''        return _reactive(w, dist)
    return "WAIT"''', '''        _s1e_trace["branch"] = "reactive"
        return _reactive(w, dist)
    _s1e_trace["branch"] = "no_trials"
    return "WAIT"'''),
    ]
    for a,b in replacements:
        assert src.count(a) == 1, a
        src = src.replace(a,b)
    COPY.write_text(src,encoding="utf-8")
    src = (ROOT/"submission_worker_full.py").read_text(encoding="utf-8-sig")
    needle = "            else:\n                raise ValueError('Unknown operation')"
    assert src.count(needle) == 1
    WORKER.write_text(src.replace(needle,"            elif request['op'] == 's1e_trace':\n                result = namespace.get('_s1e_trace', {})\n"+needle),encoding="utf-8")

class TraceProcess(SubmissionProcess):
    def respawn(self):
        self.close()
        import queue
        import threading
        self.replies = queue.Queue()
        self.process = subprocess.Popen([sys.executable,"-I","-u",str(WORKER)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,text=True,encoding="utf-8",creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        threading.Thread(target=self._read, daemon=True).start()
        try:
            self._receive(5.0)
            self.call("load",1.5,source=self.locked_source)
        except BaseException:
            self.close()
            raise

def get_reference():
    with gzip.open(HISTORICAL,"rt",encoding="utf-8") as f:
        return next(r for line in f if (r:=json.loads(line))["match_id"] == REFERENCE_ID)

def trace():
    prepare_copy()
    orig = rt.ModelSubmission("glm",ORIGINAL)
    bench = rt.ModelSubmission("benchmark_strong",ROOT/"benchmarks/benchmark_strong.py")
    bench.validate_demon_map()
    assert bench.is_valid_demon
    reference = get_reference()
    assert reference["hero_submission_sha256"] == orig.submission_sha256
    assert reference["demon_submission_sha256"] == bench.submission_sha256
    assert reference["frames"][11]["hero_pos"] == [3,21]
    assert all(f["action"] == "WAIT" for f in reference["frames"][12:])
    dec = rt.engine.validate_and_decode_dungeon(bench.demon_grid,check_spawn=False)
    engine = rt.engine.DungeonSimulator(dec, mode="FULL")
    with TraceProcess(COPY) as worker, (HERE/"glm_wait_trace.jsonl").open("w",encoding="utf-8") as file:
        for old in reference["frames"][1:]:
            state=engine.get_observation()
            now=time.perf_counter()
            act,error=None,None
            try:
                act=worker.call("decide",2.0 if state["turn"]==1 else 0.5,state=state)
                wall=time.perf_counter()-now
                log=worker.call("s1e_trace",0.5)
            except Exception as exc:
                wall=time.perf_counter()-now
                error=str(exc)
                log={}
                worker.respawn()
            # Compare recommendation on each archived state. Apply the archived action even when the proposal diverges.
            step=engine.step(old["action"])
            assert [engine.hx,engine.hy]==old["hero_pos"] and engine.hp==old["hero_hp"],old["turn"]
            row=dict(turn=old["turn"],start=[state["hero"]["x"],state["hero"]["y"]],hp=state["hero"]["hp"],
                     archived_action=old["action"],trace_action=act,seconds=wall,worker_error=error,**log)
            file.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
            file.flush()
            if old["turn"]<=13 or old["turn"]%40==0:print(row["turn"],act,log.get("branch"),log.get("exception"),flush=True)
if __name__=="__main__":
    trace()

