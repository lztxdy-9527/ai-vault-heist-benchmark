"""Capture search queue expansions and selected real reject branches from exact Wave3 sources."""
import csv
import math
from collections import Counter
from experiment_s1e2 import *

# Original line, insertion indent, event kind, stage, coordinate expression, optional reason.
# Expansions count nodes that reach the expansion body, with separate macro and local stages.
HOOKS={
    "neon":[
        (1591,12,"expand","local","cidx"),
        (1563,16,"discard","local","nidx","dedup"),
        (1568,24,"discard","local","nidx","resource_dominance"),
        (1589,16,"discard","local","cidx","stale"),
        (2065,12,"expand","plates","st[0],st[1]"),
        (2076,20,"discard","plates","ns[0],ns[1]","key_pickup"),
        (2078,20,"discard","plates","ns[0],ns[1]","no_effect"),
        (2082,20,"discard","plates","ns[0],ns[1]","dedup"),
        (2136,16,"discard","macro","st[0],st[1]","stale"),
        (2138,16,"discard","macro","st[0],st[1]","plan_length"),
        (2140,12,"expand","macro","st[0],st[1]"),
        (2161,24,"discard","macro","ns[0],ns[1]","pit_resources"),
        (2168,20,"discard","macro","ns[0],ns[1]","dedup"),
    ],
    "carbon":[
        (923,12,"discard","local","x,y","stale"),
        (929,8,"expand","local","x,y"),
        (1126,12,"else_discard","local","nx,ny","dedup"),
        (1718,16,"discard","macro","eng['hx'],eng['hy']","stale"),
        (1720,12,"expand","macro","eng['hx'],eng['hy']"),
        (1752,20,"discard","macro","c_eng['hx'],c_eng['hy']","dead"),
        (1754,20,"discard","macro","c_eng['hx'],c_eng['hy']","damage_forbidden"),
        (1775,24,"discard","macro","c_eng['hx'],c_eng['hy']","relaxed_unreachable"),
        (1784,24,"discard","macro","c_eng['hx'],c_eng['hy']","box_count"),
        (1793,16,"dedup_if_not_queued","macro","c_eng['hx'],c_eng['hy']","dedup"),
    ],
    "opus":[
        (730,16,"discard","weighted","st[2],st[3]","turn_limit"),
        (731,12,"expand","weighted","st[2],st[3]"),
        (758,20,"discard","weighted","cst[2],cst[3]","no_effect"),
        (769,20,"discard","weighted","cst[2],cst[3]","dedup"),
    ],
    "astra":[
        (782,12,"expand","crate_walk","q"),
        (791,16,"else_discard","crate_walk","dest","visited_or_unsafe"),
        (631,12,"discard","main","s.p","stale_or_turn_limit"),
        (634,8,"expand","main","s.p"),
        (660,16,"discard","main","n.p","dedup"),
        (815,16,"discard","crates","s.p","dedup"),
        (816,12,"expand","crates","s.p"),
        (877,24,"discard","crates","n.p","unreachable_assignment"),
        (1035,12,"discard","demolition","s.p","depth_limit"),
        (1036,8,"expand","demolition","s.p"),
        (1051,12,"split_discard","demolition","n.p","dedup"),
    ],
    "glm":[
        (781,12,"stop","astar","-1,-1","deadline"),
        (784,12,"discard","astar","cur.hx,cur.hy","stale"),
        (788,8,"expand","astar","cur.hx,cur.hy"),
        (806,16,"discard","astar","nw.hx,nw.hy","damage_or_dead"),
        (813,24,"discard","astar","nw.hx,nw.hy","pressed_box"),
        (815,24,"discard","astar","nw.hx,nw.hy","lost_box"),
        (819,24,"discard","astar","nw.hx,nw.hy","regressive_box"),
        (823,16,"discard","astar","nw.hx,nw.hy","dedup"),
        (952,8,"trial","astar","cell[0],cell[1]","target"),
    ],
}
WRAPS={
    "neon":[("FastWorld.solve","pair_first"),("FastWorld._run_macro_astar","pair_first")],
    "carbon":[("_solve_full_dungeon","first_bool")],
    "opus":[("Planner.search","last_bool")],
    "astra":[("search","last_bool"),("Crates.plan","none"),("clear_crate_lane","none"),("clear_obstacle","none")],
    "glm":[("_astar","stage_bool")],
}
# The nested macro routine is measured inside solve and counted once in elapsed time.
TRACE_WORKER=LAB/"frontier_worker.py"
def prepare_worker():
    original=(ROOT/"submission_worker_full.py").read_text(encoding="utf-8-sig")
    needle="def main():"
    helper="""
from time import perf_counter
def bind_trace(namespace, spec):
    record = {'capture':False, 'events':[], 'counts':{}, 'search_s':0., 'depth':0, 'full':False, 'subgoal':False, 'calls':0}
    def emit(kind, stage, x, y=None, reason=''):
        if kind == 'expand':
            record['counts'][stage] = record['counts'].get(stage, 0) + 1
        if record['capture']:
            if y is None:
                x, y = x % 40, x // 40
            record['events'].append((kind, stage, x, y, reason))
    def wrap(old, outcome):
        def traced(*args, **kwargs):
            outer = record['depth'] == 0
            begin = perf_counter() if outer else 0.
            record['depth'] += 1
            record['calls'] += 1
            try:
                result = old(*args, **kwargs)
                if outcome == 'pair_first' and result[0] or outcome == 'first_bool' and result[0] or outcome == 'last_bool' and result[-1]:
                    record['full'] = True
                if outcome == 'stage_bool' and result[1]:
                    record['subgoal'] = True
                return result
            finally:
                record['depth'] -= 1
                if outer:
                    record['search_s'] += perf_counter() - begin
        return traced
    namespace['trace_evt'] = emit
    for name, outcome in spec:
        if '.' in name:
            owner, sub = name.split('.')
            cls = namespace[owner]
            setattr(cls, sub, wrap(getattr(cls, sub), outcome))
        else:
            namespace[name] = wrap(namespace[name], outcome)
    return record

"""
    assert original.count(needle)==1
    raw=original.replace(needle,helper+needle)
    a="                namespace = load_source(request['source'])"
    assert raw.count(a)==1
    raw=raw.replace(a,a+"\n                trace_record = bind_trace(namespace, request['wraps'])")
    a="                result = namespace['decide_action'](request['state'], memory)"
    assert raw.count(a)==1
    raw=raw.replace(a,"""                trace_record.update(capture=request.get('capture',False),events=[],counts={},search_s=0.,depth=0,full=False,subgoal=False,calls=0)
                start = perf_counter()
"""+a+"""
                trace_record['decision_s'] = perf_counter()-start
""")
    a="            else:\n                raise ValueError('Unknown operation')"
    assert raw.count(a)==1
    raw=raw.replace(a,"""            elif request['op'] == 'trace_meta':
                result = {k:v for k,v in trace_record.items() if k!='events'}
                result['event_count'] = len(trace_record['events'])
            elif request['op'] == 'trace_page':
                offset = request['offset']
                result = trace_record['events'][offset:offset+4000]
"""+a)
    TRACE_WORKER.write_text(raw,encoding="utf8")

class FrontierWorker(LocalWorker):
    def __init__(self,path,wraps):
        self.wraps=wraps
        super().__init__(path,TRACE_WORKER)
    def call(self,op,timeout,**data):
        if op=="load":
            data["wraps"]=self.wraps
        return super().call(op,timeout,**data)

def patch(a):
    raw=source(a).decode("utf-8-sig")
    lines=raw.splitlines()
    for n,indent,kind,stage,coord,*why in sorted(HOOKS[a],key=lambda row:row[0],reverse=True):
        old=lines[n-1]
        reason=why[0] if why else ""
        emit=f"trace_evt({kind!r}, {stage!r}, {coord}, reason={reason!r})"
        if kind=="else_discard":
            assert len(lines[n-2])-len(lines[n-2].lstrip())==indent+4
            lines[n-1:n-1]=[" "*indent+"else:"," "*(indent+4)+emit.replace("'else_discard'","'discard'")]
        elif kind=="dedup_if_not_queued":
            # Same branch as the failed comparison immediately preceding the original return.
            assert old.strip()=="return None" and "heappush" in lines[n-2]
            lines[n-1:n-1]=[" "*indent+"else:"," "*(indent+4)+emit.replace("'dedup_if_not_queued'","'discard'")]
        elif kind=="split_discard":
            assert old.endswith(":continue")
            lines[n-1:n]=[old[:-8]," "*(indent+4)+emit.replace("'split_discard'","'discard'")," "*(indent+4)+"continue"]
        else:
            assert len(old)-len(old.lstrip())==indent,(a,n,repr(old),indent)
            lines.insert(n-1," "*indent+emit)
    out=LAB/f"frontier_{a}_submission.py"
    out.write_text("\n".join(lines)+"\n",encoding="utf8")
    return out

def save_frontier(events,path,turn,meta):
    # Chunk about 100 visual frames using expansion count. Rejects between expanded nodes stay in event order.
    n=sum(i[0]=="expand" for i in events)
    stride=max(1,math.ceil(n/120))
    groups=[]
    part=[]
    count=0
    for seq,(kind,stage,x,y,reason) in enumerate(events,1):
        if kind=="expand" and part and count and count%stride==0:
            groups.append((count,part))
            part=[]
        if kind=="expand":
            count+=1
        part.append(dict(seq=seq,kind=kind,stage=stage,cell=[x,y] if x>=0 and y>=0 else None,reason=reason or None))
    if part:
        groups.append((count,part))
    assert 60<=len(groups)<=200,(path,n,len(groups))
    with path.open("w",encoding="utf8") as f:
        for i,(c,batch) in enumerate(groups,1):
            obj=dict(turn=turn,frame=i,expanded_total=c,events=batch)
            if i==len(groups):
                obj["last_expanded_cell"]=next((e[2:4] for e in reversed(events) if e[0]=="expand"),None)
                obj["selected_action"]=meta["selected_action"]
            f.write(json.dumps(obj,ensure_ascii=False,separators=(",",":"))+"\n")
    return dict(frames=len(groups),stride=stride,expanded=n,rejected=sum(e[0]=="discard" for e in events),
                last_expanded_cell=next((e[2:4] for e in reversed(events) if e[0]=="expand"),None))

def run(a,ref,bench):
    limit=12 if a=="glm" else ref["turns"]
    capture=12 if a=="glm" else 1
    original=find_replay(a,"攻","terminal","benchmark_strong")
    if ref.get("demon_submission_sha256"):
        assert bench.submission_sha256==ref["demon_submission_sha256"]
    assert digest(json.dumps(bench.demon_grid,separators=(",",":")).encode())==original["grid_from_frame0_sha256"]
    assert len(ref["frames"])==ref["turns"]+1
    dec=rt.engine.validate_and_decode_dungeon(bench.demon_grid,check_spawn=False)
    sim=rt.engine.DungeonSimulator(dec,mode="FULL")
    folder=BASE/a/"search_trace"
    folder.mkdir(exist_ok=True)
    src=patch(a)
    rows=[]
    with FrontierWorker(src,WRAPS[a]) as work:
        for frame in ref["frames"][1:limit+1]:
            turn=frame["turn"]
            t0=time.perf_counter()
            try:
                act=work.call("decide",2.0 if turn==1 else .5,state=sim.get_observation(),capture=turn==capture)
                wall=time.perf_counter()-t0
                trace=work.call("trace_meta",.5)
                err=None
            except Exception as exc:
                act,trace,err=None,{},type(exc).__name__
                wall=time.perf_counter()-t0
                work.respawn()
            assert act in rt.engine.VALID_ACTIONS or err is not None
            row=dict(turn=turn,selected_action=act,archived_action=frame["action"],action_match=act==frame["action"],
                     expanded_nodes=sum(trace["counts"].values()) if trace else None,
                     expanded_by_stage=trace.get("counts"),search_seconds=trace.get("search_s"),
                     decision_seconds=trace.get("decision_s"),worker_roundtrip_seconds=wall,
                     found_full_path=trace.get("full"),found_subgoal=trace.get("subgoal"),search_calls=trace.get("calls"),error=err)
            rows.append(row)
            if turn==capture:
                assert trace
                events=[event for offset in range(0,trace["event_count"],4000)
                        for event in work.call("trace_page",1.5,offset=offset)]
                assert len(events)==trace["event_count"]
                save(LAB/f"raw_frontier_{a}.json",events)
                frontier=save_frontier(events,folder/("t12_frontier.jsonl" if a=="glm" else "turn1_frontier.jsonl"),turn,row)
                assert frontier["expanded"]==row["expanded_nodes"]
            # Hold the official engine states constant so even divergent recommendations see identical input.
            sim.step(frame["action"])
            assert ([sim.hx,sim.hy],sim.hp)==(frame["hero_pos"],frame["hero_hp"])
    with (folder/"per_turn.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        for row in rows:
            w.writerow({**row,"expanded_by_stage":json.dumps(row["expanded_by_stage"],separators=(",",":"))})
    delta=[r for r in rows if not r["action_match"]]
    out=dict(agent=a,source_sha256=digest(source(a)),trace_source_sha256=digest(src.read_bytes()),
             replay={k:original[k] for k in ("file","jsonl_line","replay_match_id","match_id","grid_from_frame0_sha256")},
             compared_turns=len(rows),mismatches=delta,capture_turn=capture,frontier=frontier,
             hooks=HOOKS[a],search_time_wrappers=WRAPS[a],
             methodology="标准引擎按历史动作推进，逐帧复核位置与血量。副本策略独立延续 memory，出现动作差异后的记录仍使用该历史棋盘。",
             coverage="节点为列出的队列扩展点；剪枝仅包括显式埋点分支。未计反向距离预处理。完整路线为本拍新发现可通关的路线，不计缓存续走。")
    save(folder/"metadata.json",out)
    print(a,len(rows),len(delta),frontier,flush=True)

if __name__=="__main__":
    prepare_worker()
    refs=get_refs()
    verify_glm(refs["glm"])
    bench=strong()
    for a in sys.argv[1:] or AGENTS:
        run(a,refs[a],bench)

