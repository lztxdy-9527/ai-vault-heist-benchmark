"""Publish verified S1e-2 evidence and append it to the production ledger."""
from verify_s1e2 import *
from build_s1e import save as save_text

names={"neon":"Neon","carbon":"Carbon","opus":"Opus 1029 行","astra":"Astra","glm":"GLM"}
results=load(LAB/"trace_validation.json")
check=load(LAB/"glm_archive_check.json")
runs=jsonl_read(LAB/"glm_counterfactual_runs.jsonl")
evidence=BASE.parent
ledger=evidence/"evidence_ledger_v2.jsonl"
task="S1e-2"
items=[]
def fact(agent,type_,statement,path,locator,**extra):
    items.append(dict(agent=agent,t_contest_sec=None,t_wall=None,type=type_,
        fact="赛后实验 / 插桩，非正式赛。"+statement,verbatim=None,claim=None,source_path=str(path),
        source_kind="rerun",grade="C",post_hoc=True,confidence="high",task=task,json_locator=locator,**extra))

fact("glm","stat","GLM 复测与第三波终局强基准存档的勇者源码 SHA-256 相同，逐拍动作、坐标和血量一致，T12–T240 均执行 WAIT。",
    LAB/"glm_archive_check.json","$",match_id=check["wave3_match"],
    replay_path=check["wave3_original_replay"],replay_json_locator=check["wave3_original_locator"],sha256=check["staged_sha256"])
for a in AGENTS:
    r=results[a]
    turn=12 if a=="glm" else 1
    fact(a,"stat",f"强基准 T{turn} 记录 {r['expanded']} 次节点展开、{r['discarded']} 次已埋点的舍弃，导出 {r['frontier_frames']} 帧动画数据。与终局参照逐拍比较 {r['comparison_turns']} 个动作，差异 {len(r['difference_turns'])} 个。",
         r["frontier_file"],f"T{turn} chronological events",match_id=r["wave3_match"],expanded_by_stage=r["expanded_by_stage"],
         replay_path=r["reference_path"],replay_json_locator=r["reference_locator"],decision_csv=str(BASE/a/"search_trace/per_turn.csv"))
for i,r in enumerate(runs,1):
    status="通关" if r["status"]=="CLEARED" else "接口弃权"
    fact("glm","match_result",f"GLM {r['variant']} 第 {r['replicate']} 次在强基准{status}，T{r['turns']}，结算 HP {r['hp']}，钥匙 {r['keys']} 把。",
         LAB/"glm_counterfactual_runs.jsonl",f"JSONL:{i}",experiment_variant=r["variant"],replicate=r["replicate"],
         status=r["status"],replay_path=r["replay_file"],sha256=r["source_sha256"])
fact("glm","stat","A 与 C 的独立单步核验均在 T7 触发 0.5 秒裁判调用超时。",
     LAB/"glm_case_deadline_probe.json","A/C")
raw=ledger.read_bytes()
old=[json.loads(line) for line in raw.splitlines()]
seen=[x for x in old if x.get("task")==task]
if seen:
    begin=int(seen[0]["id"].split("-")[1])
else:
    begin=max(int(x["id"].split("-")[1]) for x in old if re.fullmatch(r"E-\d+",x["id"]))+1
rows=[dict(id=f"E-{k:04d}",**record) for k,record in enumerate(items,begin)]
if seen:
    assert rows==seen
else:
    content="".join(json.dumps(r,ensure_ascii=False,separators=(",",":"))+"\n" for r in rows).encode("utf8")
    with ledger.open("ab") as f:
        if not raw.endswith(b"\n"):
            f.write(b"\n")
        f.write(content)
    assert ledger.read_bytes()==raw+(b"" if raw.endswith(b"\n") else b"\n")+content

def trace_links(a):
    folder=BASE/a/"search_trace"
    front=folder/("t12_frontier.jsonl" if a=="glm" else "turn1_frontier.jsonl")
    return link(folder/"per_turn.csv","逐回合 CSV")+" · "+link(front,"动画 JSONL")+" · "+link(folder/"metadata.json","挂点与归档定位")

summary=[
    "# S1e-2 搜索插桩与 GLM 反事实",
    "以下搜索轨迹和改法结果均为**赛后实验 / 插桩，非正式赛**。",
    "## GLM 的终局回放",
    f"第三波强基准原始回放为 {check['wave3_original_locator']}。它与 P2_RETEST_025 的源码哈希、逐拍动作、坐标和血量一致。T11 勇者到 (3,21)，T12–T240 共 229 拍 WAIT。冷开场可直接取第三波原始回放。{link(check['wave3_original_replay'],'第三波原始回放')} · {link(LAB/'glm_archive_check.json','四份哈希核验')}。",
    "## 搜索动画",
]
lines=[]
for a in AGENTS:
    v=results[a]
    stage="、".join(f"{k} {n}" for k,n in v["expanded_by_stage"].items())
    turn=12 if a=="glm" else 1
    lines.append(f"- **{names[a]}**　T{turn} 展开 {v['expanded']} 节点（{stage}），记录 {v['discarded']} 次舍弃，导出 {v['frontier_frames']} 帧。插桩推荐动作与 {v['comparison_turns']} 拍归档回放一致。{trace_links(a)}。")
summary.append("\n".join(lines))
glm=results["glm"]
summary.append(f"GLM 的 512 次 T12 展开全部发生在首个目标 (8,22)。本次插桩最后展开的勇者格为 {tuple(glm['last_expanded_cell'])}，随后出现 deadline；其余三个子目标在同一截止后直接停止。最终动作 WAIT。S1e 的 448 与这次的 512 分属两次不同负载的插桩，镜头计数应与所用轨迹配套。{trace_links('glm')}。")
summary.extend([
    "动画按展开节点数分帧。每条 events 记录含全序 seq、阶段 stage、坐标 cell 和原因 reason。expand 点亮，discard 可置灰；同一格可因资源、相位或棋盘不同多次出现。GLM 的 trial 标子目标，stop 标预算截止。计数只覆盖各席埋点队列，含各自列出的局部搜索，预处理未纳入，勿用节点数排序能力。",
    "CSV 的 found_full_path 表示该回合新找到整图通关路线，缓存续走为 False；found_subgoal 仅用于 GLM 的子目标搜索记录。search_seconds 在被埋点的搜索调用外层计时，嵌套调用只记一次；decision_seconds 计副本决策函数，worker_roundtrip_seconds 含往返。时间为插桩实测。",
    "## GLM 反事实",
    "\n".join([
        "- **A　仅加倍内部预算**　原提交源码完全同字节。副本 worker 将程序内部单调钟走速减半，使 1.30 / 0.25 秒对应实际 2.60 / 0.50 秒。三次均 T9 接口弃权，结算 HP 0，钥匙 0。",
        "- **B　仅保留无伤首步推箱**　部分路径第一步若确为推箱且存活无损血，则保留这一拍，后续过滤及兜底沿用原逻辑。三次均在 T12 执行 MOVE_R 推箱，T120 通关，HP 100、两把钥匙，全程 WAIT 0 次。",
        "- **C　A 与 B 同时启用**　三次均 T9 接口弃权，结算 HP 0，钥匙 0。",
    ]),
    f"裁判调用上限保持 T1 为 2.0 秒、后续为 0.5 秒。A、C 各自的单步核验在 T7 重现调用超时。整局回放在 T7–T9 记录 WAIT，并在 T9 记为接口错误三连弃权。HP 0 为弃权结算值。该实验没有测放宽裁判时限后的通关情况。{link(LAB/'glm_case_deadline_probe.json','T7 错误类型')} · {link(LAB/'glm_counterfactual_runs.jsonl','九次结果和独立回放路径')}。",
    f"事实编号 {rows[0]['id']} 至 {rows[-1]['id']}，共 {len(rows)} 条。{link(ledger,'v2 台账')}。"
])
save_text(HERE/"S1e2_summary.md","\n\n".join(summary))
total=sum(results[a]["comparison_turns"] for a in AGENTS if a!="glm")
handoff=[
    "# S1e-2 搜索插桩与 GLM 反事实交接",
    f"四席强基准逐回合动作与终局引用回放共核对 {total} 拍，差异 0。GLM 的补充轨迹核对前 12 拍，差异 0。五份动画轨迹均在 60–200 帧内。",
    "\n".join([
        "- **冷开场**　取第三波 GLM 强基准原始回放 featured_matches[176]，切 T11 → T12 与 T240。源码 SHA-256 与历史复测一致。"+link(check["wave3_original_replay"],"原回放")+" · "+link(LAB/"glm_archive_check.json","定位与核验")+"。",
        "- **搜索镜头**　各席按 CSV 找回合、按 JSONL 的 seq 点亮，再同步每帧 expanded_total。"+link(HERE/"S1e2_summary.md","数据入口")+"。",
        "- **GLM 伏笔回收**　B 版三次均在 T12 推箱，T120 满血通关，标「赛后实验」。A、C 保持裁判时限，六次均 T9 接口弃权。"+link(LAB/"glm_counterfactual_runs.jsonl","九次实验")+"。",
    ]),
    f"节点按本次插桩定义计数。固定历史状态的轨迹只用于同输入比较，反事实整局由副本实际出手推进。参赛源码、原始回放及比赛结果保存在原位置。新增事实 {rows[0]['id']}–{rows[-1]['id']} 全部标记 post_hoc=true、source_kind=rerun。{link(ledger,'v2 事实台账')} · {link(LAB/'trace_validation.json','校验记录')}。"
]
save_text(evidence/"HANDOFF_S1e2.md","\n\n".join(handoff))
print(f"{len(rows)} facts {rows[0]['id']}–{rows[-1]['id']}")

