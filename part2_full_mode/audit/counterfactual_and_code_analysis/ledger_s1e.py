import re
from build_s1e import *

EVIDENCE=BASE.parent
LEDGER=EVIDENCE/"evidence_ledger_v2.jsonl"
START=7333
rows=[]
def add(agent,type_,fact,path,kind,locator,notes="",post_hoc=False,**kw):
    identifier=f"E-{START+len(rows):04d}"
    rows.append({"id":identifier,"agent":agent,"t_contest_sec":None,"t_wall":None,"type":type_,"fact":fact,
                 "verbatim":None,"claim":None,"source_path":str(path),"source_kind":kind,"grade":"C",
                 "post_hoc":post_hoc,"confidence":"high","notes":notes,"json_locator":locator,"task":"S1e",**kw})
    return identifier

for a in order:
    folder=BASE/a
    stats=load(folder/"stats.json")
    fx=load(folder/"effects.json")
    for effect in fx["effects"]:
        source=effect["source"]
        effect["code_fact_id"]=add(a,"code_fact",effect["source_observation"],source["file"],"code",
            f"L{source['line_start']}–L{source['line_end']}",
            f"Wave3 {fx['version']}。回放匹配以开局棋盘和勇者哈希作定位。",
            source_sha256=fx["sha256"],snippet_id=effect["snippet_id"],effect_relation=effect["relation"],
            effect_file=str(folder/"effects.json"),replay=effect["replay"],clip_number=effect["number"],
            clip_observation=effect["observation"])
    save_json(folder/"effects.json",fx)
    add(a,"stat",f"{stats['version']} 有 {stats['effective_code_lines']} 个有效代码行、{stats['function_count']} 个具名函数或方法。",
        folder/"stats.json","code","effective_code_lines/function_count/maximum_function",source_sha256=stats["sha256"])
    n=stats["turn1_sample_n"]
    add(a,"stat",f"同图复测首回合 {n} 次，平均 {stats['turn1_mean_seconds']:.3f} 秒，最大 {stats['turn1_max_seconds']:.3f} 秒。",
        HERE/"turn1_probe.jsonl","rerun",f"agent == {a}",stats["turn1_scope"],post_hoc=True,source_sha256=stats["sha256"])
    admit=stats["defense_admission"]
    if admit["valid"]:
        fact=f"标准引擎复核提交防图通过。历史记账 {admit['historic_spent_gold']} 金币，作者解 {admit['build_proof_steps']} 步。"
    else:
        fact="提交防图在 (0,0) 因 W 外圈被拒，终局守局使用 BACKUP_FULL_01。"
    add(a,"code_fact",fact,HERE/"defense_admissions.json","rerun",a,"作者解步数取返回动作串长度。有效图的作者解都通过引擎验收。",post_hoc=True,source_sha256=stats["sha256"])

strong=find_replay("glm","攻","terminal","benchmark_strong")
add("glm","match_result","强基准历史回放 T12–T240 共 229 拍连续 WAIT，勇者留在 (3,21)。",strong["file"],"replay",
    f"JSONL:{strong['jsonl_line']}.frames[12:241]","引擎历史回放。",post_hoc=True,replay=replay_ref(strong,12))
add("glm","code_fact","同哈希插桩复现 T12 先裁掉唯一的推箱前缀 MOVE_R，兜底再排除该动作，WAIT 的评分最低。",
    HERE/"glm_wait_trace.jsonl","rerun","JSONL:12–240","T12–T240 推荐动作和历史一致，无调用错误或捕获异常。",post_hoc=True,
    source_sha256=versions["glm"][1]["sha256"],replay=replay_ref(strong,12))
add("glm","stat","标准引擎从历史 T12 初态执行 MOVE_R，勇者无伤移至 (4,21)，同一拍产生 2 条 BOX_MOVE。",
    HERE/"glm_t12_engine_probe.json","rerun","MOVE_R.result.events","一拍对照，未用于赛果。",post_hoc=True)
add("全场","stat","11 席共 143 场 Wave3 计分攻局，按 8 个行为指标作席间 min–max 归一化。",
    OVERVIEW/"radar.csv","replay","数据行 2–12","首拍耗时来自同图复测，单位见统计口径。",post_hoc=True)
last=rows[-1]["id"]
payload="".join(json.dumps(i,ensure_ascii=False,separators=(",",":"))+"\n" for i in rows).encode("utf-8")
ledger=LEDGER.read_bytes()
existing=[json.loads(line) for line in ledger.splitlines()]
prior=[i for i in existing if i.get("task")=="S1e"]
if prior:
    assert prior==rows
else:
    used={i["id"] for i in existing}
    assert all(i["id"] not in used for i in rows)
    with LEDGER.open("ab") as file:
        if not ledger.endswith(b"\n"):
            file.write(b"\n")
        file.write(payload)
assert LEDGER.read_bytes().endswith(payload)
inventory=EVIDENCE/"inventory.md"
text=inventory.read_text(encoding="utf-8-sig")
heading="## S1e 终局程序资料补录"
if heading not in text:
    inv=[heading,"以下均按 Wave3 版本清单锁定。原有会话盘点与等级沿用，各席的片段回放定位可从结构页进入。"]
    for a in order:
        ver,entry=versions[a]
        gap="历史对局没有节点计数。" if a!="glm" else "节点计数来自标准强基准插桩，覆盖范围见统计文件。"
        if a=="doubao":
            gap+=" 提交防图未通过外圈准入。"
        inv.append(f"- **{a}**　{ver}，哈希前 12 位 {inline(entry['sha256'][:12])}。{gap}{link(BASE/a/'anatomy.md','结构及片段')} · {link(BASE/a/'stats.json','统计与防图验收')}。")
    updated=text.rstrip()+"\n\n"+"\n\n".join(inv[:2]+["\n".join(inv[2:])])+"\n"
    inventory.write_bytes(updated.replace("\n","\r\n").encode("utf-8") if b"\r\n" in inventory.read_bytes() else updated.encode("utf-8"))
handoff=EVIDENCE/"HANDOFF_S1e.md"
hand=handoff.read_text(encoding="utf-8")
label="S1e 事实已追加"
if label not in hand:
    with handoff.open("a",encoding="utf-8") as f:
        f.write(f"\n{label}至 v2 台账，编号 E-{START:04d} 至 {last}，共 {len(rows)} 条。{link(LEDGER,'v2 事实台账')} · {link(inventory,'资料盘点')}。\n")
print(f"{len(rows)} facts, E-{START:04d} to {last}")

