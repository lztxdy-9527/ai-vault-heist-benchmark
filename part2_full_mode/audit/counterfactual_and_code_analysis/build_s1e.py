import ast
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
from statistics import mean
import tokenize
from profiles import META

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
OVERVIEW=BASE/"_overview"
OVERVIEW.mkdir(exist_ok=True)
WAVE=Path("part2_full_mode/audit/three_waves_opus1029_20261122")
TICK=chr(96)
def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))
def lines_json(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8-sig").splitlines()]
def save(path,value):
    path.write_text(value.rstrip()+"\n",encoding="utf-8")
def save_json(path,value):
    save(path,json.dumps(value,ensure_ascii=False,indent=2))
def link(path,text,line=None):
    target=str(path).replace("\\","/")
    if line:
        target+=f":{line}"
    return f"[{text}](<{target}>)"
def inline(s):
    return TICK+str(s)+TICK
manifest=load(WAVE/"versions_manifest.json")
roster=load(WAVE/"wave3_final_11seats/leaderboard.json")["roster"]
versions={manifest[n]["seat_id"]:(n,manifest[n]) for n in roster}
replays=load(HERE/"wave3_replay_metrics.json")
admissions=load(HERE/"defense_admissions.json")
probes=lines_json(HERE/"turn1_probe.jsonl")
trace=lines_json(HERE/"glm_wait_trace.jsonl")
order=list(META)
PHASES=("感知","列候选","推演或搜索","打分","出手")
STATUSES={"CLEARED":"通关","TIMEOUT":"回合上限","DEAD":"阵亡"}
EVENTS={"wall_break":"爆破移除普通墙格数","plate_open":"压板门开启次数","laser_hits":"激光命中次数",
        "jump":"JUMP 动作次数","box_moves":"BOX_MOVE 事件次数","wait":"WAIT 动作次数",
        "SWITCH_FLIP":"开关翻转事件次数","BOX_FILL_PIT":"箱子填坑事件次数","blast":"爆炸批次数"}
META["neon"]["fixed"]="用前向推演的状态签名复核缓存路线。没有宏计划则模拟安全单步。压板按箱子是否占据更新。"
META["doubao"]["fixed"]="首拍、路线失配或短计划伴随较低停滞计数时尝试搜索。执行前模拟安全性。防图外圈坐标固定。"

META["astra"]["snippets"][2]=(350,359,"守","在钥匙区和金库入口附近放置门、炮与 TNT。","start","")
META["sol"]["snippets"][2]=(1446,1456,"守","字符地图同时标出四块压板、箱子、钥匙区和金库前的坑。","start","")
META["neon"]["snippets"][2]=(175,185,"守","在金库前侧布置坑、压板门与上下相向炮座。","start","")
META["glm"]["snippets"][3]=(91,101,"守","K2 底边为普通墙并放置 TNT，金库壁龛入口放置压板门。","start","")
META["opus"]["snippets"][2]=(979,986,"守","在压板推箱线上放裂纹地板，金库通路设置三座激光炮。","laser_hits","deepseek")
META["hunyuan"]["snippets"][2]=(1241,1250,"守","按坐标在空格放入多座红炮与蓝炮。","start","")
META["qwen"]["snippets"][2]=(1060,1071,"守","设置带侧壁与单向入口的三块压板，并放置三个箱子。","start","")

META["doubao"]["phases"][1]=("_actions",META["doubao"]["phases"][1][1])

META["hunyuan"]["snippets"][0]=(959,970,"攻","对未覆盖的压板取箱到板的最短距离，再加英雄接近箱子的代价。","plate_open","benchmark_strong")
META["hunyuan"]["snippets"][1]=(994,1005,"攻","先跑基本动作集，按阶段条件再试完整动作集。","terminal","benchmark_strong")
META["hydrogen"]["snippets"][0]=(887,898,"攻","局部走子搜索只在射线区加入 WAIT，并计入预计损血和跳跃成本。","wait","benchmark_strong")

def replay_ref(r,turn):
    keys=("file","jsonl_line","replay_match_id","match_id","map_id","grid_from_frame0_sha256")
    return {**{k:r[k] for k in keys},"turn":turn}
def result(r):
    return f"{STATUSES.get(r['status'],r['status'])}，T{r['turns']}，结算 HP {r['hp']}，钥匙 {r['keys']} 把"
def clip_link(r,turn):
    return f"{link(r['file'],'回放')} JSONL 第 {r['jsonl_line']} 行，{r['replay_match_id']}，T{turn}"

def find_replay(agent,role,event,pref):
    rs=[r for r in replays if (
        (role=="攻" and r["hero_id"]==agent and r["role"] in ("attack","benchmark_attack"))
        or (role=="守" and r["demon_id"]==agent and r["role"] in ("attack","benchmark_defense")))]
    rs.sort(key=lambda r:(bool(pref and pref in (r["map_id"],r["hero_id"],r["demon_id"])),r["role"]=="attack"),reverse=True)
    if event in EVENTS:
        rs=[r for r in rs if r["samples"].get(event)]
    if event=="longest_wait":
        rs=[r for r in rs if r["longest_wait"]["n"]]
    assert rs,(agent,role,event,pref)
    return rs[0]

def evidence(agent,role,event,pref,start,admit):
    if event=="glm_trace":
        r=find_replay(agent,role,"terminal","benchmark_strong")
        t=trace[11]
        label,value,detail,note={
            975:("过滤后可执行的前缀长度",len(t["partial_safe"]),t["partial_in"],
                 "T12 搜索只交回 MOVE_R，部分路径检查遇到占位变化，保留 0 步。"),
            852:("WAIT 三元组的距离项",t["reactive"][-1][3][1],t["reactive"],
                 "T12 兜底排除推箱，WAIT 以 (0,1,0) 取得最低字典序评分。"),
            778:("首个压板搜索的展开节点数",t["trials"][0]["nodes"],t["trials"],
                 "T12 首块压板未完成。日志显示子搜索用尽时限，交回部分路径。"),
        }[start]
        return dict(replay=replay_ref(r,12),observation=note,number={"label":label,"value":value},
                    relation="instrumented_reproduction",log={"file":str(HERE/"glm_wait_trace.jsonl"),"jsonl_line":12},trace_detail=detail)
    r=find_replay(agent,role,event,pref)
    if event=="rejection":
        return dict(replay=replay_ref(r,0),observation=f"提交图 (0,0) 是 {admit['outer_corner_0_0']}，验证要求 T_W。该回放 T0 为 {r['map_id']}。",
                    number={"label":"提交图未验收的内圈标价（金币）","value":admit["submitted_interior_cost"]},
                    relation="verified_admission_and_backup",validation={"file":str(HERE/"defense_admissions.json"),"json_key":agent,"reason":admit["reason"]})
    if event=="start":
        return dict(replay=replay_ref(r,0),observation=f"T0 的地图为 {r['map_id']}。准入输出和回放起始棋盘的 SHA-256 相同。",
                    number={"label":"守图花费金币","value":admit["historic_spent_gold"]},relation="verified_built_grid",
                    validation={"file":str(HERE/"defense_admissions.json"),"json_key":agent})
    if event=="terminal":
        return dict(replay=replay_ref(r,r["turns"]),observation=f"末帧 {result(r)}。",
                    number={"label":"结算回合","value":r["turns"]},relation="source_consistent_untraced")
    if event=="longest_wait":
        w=r["longest_wait"]
        return dict(replay=replay_ref(r,w["from"]),observation=f"同场最长连续等待窗口 T{w['from']}–T{w['through']}，末帧 {result(r)}。",
                    number={"label":"窗口内连续 WAIT 动作","value":w["n"]},through_turn=w["through"],relation="source_consistent_untraced")
    sample=r["samples"][event][-1 if agent=="opus" and role=="守" else 0]
    turn=sample["turn"]
    return dict(replay=replay_ref(r,turn),
                observation=f"T{turn}，动作 {sample['action']}，位置 {sample['hero_position']}，当拍结束 HP {sample['hp']}。见事件字段与同场计数。",
                number={"label":"该场"+EVENTS[event],"value":r["metrics"][event]},event=event,frame=sample,
                relation="verified_defense_mechanism" if role=="守" else "source_consistent_untraced")

def functions(raw):
    out={}
    def visit(node,prefix=()):
        for item in ast.iter_child_nodes(node):
            if isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                qualified=(*prefix,item.name)
                if not isinstance(item,ast.ClassDef):
                    out[".".join(qualified)]=(item.lineno,item.end_lineno)
                visit(item,qualified)
            else:
                visit(item,prefix)
    visit(ast.parse(raw))
    return out
def effective_lines(raw):
    ignored={tokenize.COMMENT,tokenize.ENCODING,tokenize.INDENT,tokenize.DEDENT,tokenize.NEWLINE,tokenize.NL,tokenize.ENDMARKER}
    rows=raw.splitlines()
    return len({i for t in tokenize.generate_tokens(io.StringIO(raw).readline) if t.type not in ignored
                for i in range(t.start[0],t.end[0]+1) if i<=len(rows) and rows[i-1].strip()})
def summary(agent):
    rs=[r for r in replays if r["role"]=="attack" and r["hero_id"]==agent]
    p=[i for i in probes if i["agent"]==agent]
    valid=[i["time_sec"] for i in p if not i["error"]]
    assert len(rs)==len(p)==len(valid)==13
    return rs,valid

def build_agent(agent):
    folder=BASE/agent
    folder.mkdir(exist_ok=True)
    version,entry=versions[agent]
    path=Path(entry["staged"])
    data=path.read_bytes()
    assert hashlib.sha256(data).hexdigest()==entry["sha256"]==admissions[agent]["sha256"]
    raw=data.decode("utf-8-sig")
    source_lines=raw.splitlines()
    funcs=functions(raw)
    assert agent!="opus" or len(source_lines)==1029
    def size(span):
        return span[1]-span[0]+1
    biggest=max(funcs,key=lambda n:size(funcs[n]))
    n0,n1=funcs[biggest]
    meta,admit=META[agent],admissions[agent]
    rs,times=summary(agent)
    nodes=[sum(i["nodes"] for i in t["trials"]) for t in trace]
    node_runs=[n for n in nodes if n] if agent=="glm" else []
    stats=dict(agent=agent,version=version,source_file=str(path),sha256=entry["sha256"],
               physical_lines=len(source_lines),effective_code_lines=effective_lines(raw),
               line_count_definition="Python token 所覆盖的物理非空行。排除注释和空行，字符串及 docstring 保留。",
               function_count=len(funcs),maximum_function={"name":biggest,"line_start":n0,"line_end":n1,"lines":size((n0,n1))},
               turn1_mean_seconds=mean(times),turn1_max_seconds=max(times),turn1_sample_n=len(times),turn1_errors=0,
               turn1_scope="Wave3 的 13 张正式计分攻图各测一次，逐图新建标准 worker，计第一拍收发耗时，不含 worker 启动。复测实测。",
               turn1_log=str(HERE/"turn1_probe.jsonl"),average_search_nodes=mean(node_runs) if node_runs else None,
               search_node_sample_n=len(node_runs),
               search_node_scope=("标准强基准固定历史前缀的插桩复现。逐回合汇总各搜索展开数，对至少展开一个节点的回合取均值。"
                                  if node_runs else "正式回放无节点计数，未逐版插桩。"),
               search_node_log=str(HERE/"glm_wait_trace.jsonl") if node_runs else None,
               attack_outcomes=dict(sorted(Counter(r["status"] for r in rs).items())),defense_admission=admit)
    save_json(folder/"stats.json",stats)
    caption=f"终局版本 {version}，SHA-256 {inline(entry['sha256'])}。{link(path,'送评源码')}"
    rows=[]
    for phase,(func,note) in zip(PHASES,meta["phases"],strict=True):
        hits=[func] if func in funcs else [n for n in funcs if n.endswith("."+func)]
        assert len(hits)==1,(agent,func,hits)
        a,b=funcs[hits[0]]
        rows.append(f"- **{phase}**　{note} {inline(hits[0])}，L{a}–L{b}，{size((a,b))} 行。{link(path,'源码',a)}")
    limits=[f"- **{label}**　{meta[k]}" for label,k in
            [("算法","methods"),("剪枝","pruning"),("时间控制","timing"),("固定规则与回退","fixed")]]
    a,b=funcs["build_dungeon"]
    defense=f"{meta['defense']} {inline('build_dungeon')} L{a}–L{b}。{link(path,'源码',a)}"
    if admit["valid"]:
        validation=f"官方记账 {admit['historic_spent_gold']} 金币，作者解 {admit['historic_author_steps']} 步。标准引擎验图通过，复核作者解 {admit['build_proof_steps']} 步，结算 HP {admit['build_proof_hp']}。"
    else:
        validation=f"提交图内圈标价 {admit['submitted_interior_cost']} 金币，入口返回 {admit['build_proof_steps']} 步作者串。准入在外角 (0,0) 失败，作者串未重放。官方记账和作者解均为 0，守局使用后备图。"
    keys=[k for k in admit["fixtures"] if k not in ("T_W","W","K1","K2","V","S")]
    fixtures="提交图机关和布局设施包括 "+"、".join(f"{inline(k)} × {admit['fixtures'][k]}" for k in keys)+"。"+link(HERE/"defense_admissions.json","验图记录")
    save(folder/"anatomy.md","\n\n".join([f"# {agent} 程序结构",caption,"## 勇者的五步决策","\n".join(rows),
         "## 搜索与限制","\n".join(limits),"## 魔王防图",defense,validation,fixtures,
         link(folder/"snippets.md","代码片段")+" · "+link(folder/"effects.json","画面证据")]))
    snips=[f"# {agent} 代码片段",caption,"片段对应的回放文件、回合和数字见 "+link(folder/"effects.json","effects.json")+"。"]
    fx=[]
    for i,(a,b,role,note,event,pref) in enumerate(meta["snippets"],1):
        assert 1<=b-a+1<=12 and b<=len(source_lines)
        identifier=f"{agent}-{i:02}"
        snips += [f"## {identifier}　{role}",f"{note} L{a}–L{b}。{link(path,'源码',a)}",
                  TICK*3+"python\n"+"\n".join(source_lines[a-1:b])+"\n"+TICK*3]
        ev=evidence(agent,role,event,pref,a,admit)
        if ev["relation"] in ("verified_built_grid","verified_defense_mechanism"):
            assert ev["replay"]["grid_from_frame0_sha256"]==admit["submitted_grid_sha256"]
        fx.append(dict(snippet_id=identifier,side=role,source=dict(file=str(path),line_start=a,line_end=b),source_observation=note,**ev))
    save(folder/"snippets.md","\n\n".join(snips))
    save_json(folder/"effects.json",dict(agent=agent,version=version,sha256=entry["sha256"],effects=fx,
        convention="turn 以引擎帧为准，T0 为开局。source_consistent_untraced 表示画面证实动作或结局，未记录分支选择。"))

def save_csv(path,header,rows):
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
def build_overview():
    tier={"glm":2,"doubao":2,"hydrogen":3,"qwen":3,"astra":4,"sol":4,"neon":4,"carbon":4,"opus":4,"deepseek":4,"hunyuan":4}
    save_csv(OVERVIEW/"ladder.csv",["agent","tier","search","opponent_identity_model","terrain_change_model",
              "alternative_parameterization_or_search_mode","fallback","assessment","source"],
             [[k,tier[k],int(META[k]["features"][0]),0,*map(int,META[k]["features"][1:]),META[k]["methods"],versions[k][1]["staged"]]
              for k in sorted(order,key=lambda k:tier[k])])
    radar={}
    for a in order:
        rs,times=summary(a)
        avg=lambda k:mean(r["metrics"].get(k,0) for r in rs)
        radar[a]=dict(mean_turns=mean(r["turns"] for r in rs),clear_rate=mean(r["status"]=="CLEARED" for r in rs),
                      wall_breaks_per_match=avg("wall_break"),box_moves_per_match=avg("box_moves"),laser_hits_per_match=avg("laser_hits"),
                      jumps_per_match=avg("jump"),wait_share=sum(r["metrics"].get("wait",0) for r in rs)/sum(r["turns"] for r in rs),
                      mean_turn1_seconds=mean(times))
    cols=list(radar[order[0]])
    bounds={k:(min(row[k] for row in radar.values()),max(row[k] for row in radar.values())) for k in cols}
    def normal(v,k):
        low,high=bounds[k]
        return (v-low)/(high-low) if high!=low else 0
    save_csv(OVERVIEW/"radar.csv",["agent",*cols],[[a,*[f"{normal(radar[a][k],k):.6f}" for k in cols]] for a in order])
    save_json(HERE/"radar_raw.json",{"units":{"mean_turn1_seconds":"秒","clear_rate":"0–1","wait_share":"0–1"},"bounds":bounds,"by_agent":radar})

if __name__=="__main__":
    for agent in order:
        print(agent,flush=True)
        build_agent(agent)
    build_overview()

