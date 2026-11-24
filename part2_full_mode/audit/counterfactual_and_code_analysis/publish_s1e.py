from build_s1e import *

def src(a,n):
    return link(versions[a][1]["staged"],f"{a} 源码 L{n}",n)

def attack(a,d):
    rows=[r for r in replays if r["hero_id"]==a and d in (r["map_id"],r["demon_id"])]
    assert len(rows)==1,(a,d)
    return rows[0]

def event_turn(row,key):
    return row["samples"][key][0]["turn"]

def match(a,b,d,case,descs,notes,clips):
    ra,rb=attack(a,d),attack(b,d)
    assert ra["grid_from_frame0_sha256"]==rb["grid_from_frame0_sha256"]
    title=f"## {case}　{a} / {b}"
    head=f"双方回放的开局地图 SHA-256 为 {inline(ra['grid_from_frame0_sha256'])}。"
    sides=[]
    for agent,r,(note,line),tag in zip((a,b),(ra,rb),descs,clips,strict=True):
        t=event_turn(r,tag) if tag else r["turns"]
        sides.append(f"- **{agent}**　{note} 结算 {result(r)}。{src(agent,line)} · {clip_link(r,t)}。")
    return "\n\n".join((title,head,"\n".join(sides),notes))

contrast=[
    match("neon","carbon","benchmark_strong","强基准的推箱候选",
          [("对候选先推演一拍，要求占位、机关态或地形实际变化，再排除箱组死锁。",1725),
           ("先为每个未完成压板或坑反查可推达的箱，按距离留至多两个。",1816)],
          "两场均发生 17 次 BOX_MOVE，通关相差 12 回合。Carbon 该版本实现的是可达性与距离筛选，另有角落死锁判断。回放可见推箱和用时，候选淘汰过程需要额外日志。",["box_moves","box_moves"]),
    match("astra","sol","glm","同一张 GLM 防图上的障碍处理",
          [("为受阻箱路试移除一个或两个阻挡格，这场实际爆炸移除 2 格 W。",949),
           ("有完整阶段片段时才追加整局尝试，这场 2 次裂纹塌陷，钥匙仍为零。",1349)],
          "两场都出现 7 次 BOX_MOVE，通关和回合上限是可见分歧。档案没有记录 Sol 剩余候选的剪枝原因。",["wall_break","CRACK_COLLAPSE"]),
    match("opus","glm","benchmark_strong","强基准开局如何处理部分路径",
          [("首拍对三档权重与截止运行前向搜索，以终点血量和步数比较完整路径。",899),
           ("加权搜索部分路径在首次占位变化处截断；T12 同哈希插桩确认被截掉的是 MOVE_R。",975)],
          "Opus 在 T117 通关。GLM 在 T12–T240 连续 WAIT，取钥匙 0。Opus 的历史回放不包含首拍权重选择。",["wall_break","wait"]),
    match("deepseek","qwen","benchmark_strong","开门取钥匙后的路线推进",
          [("用模拟器重放候选，直接识别终点和阵亡。在这场取齐两钥匙，推箱事件 15 次。",1294),
           ("在前向验证中保留阵亡动作之前的路径前缀。这场取齐两钥匙，随后可见箱子填坑。",1983)],
          "双方均炸掉 2 格普通墙。同图中 Qwen 有 1 次箱子填坑并通关，DeepSeek 该场没有箱子填坑事件，最终达到回合上限。",["PICK_KEY","BOX_FILL_PIT"]),
    match("hydrogen","hunyuan","benchmark_strong","中段压板与填坑",
          [("推箱小搜索把 TNT 和填坑识别为不同宏并给到候选列表。",1380),
           ("先对阶段用基本动作集搜索，按目标和剩余时间增试完整动作集。",994)],
          "双方均 100 HP、17 次 BOX_MOVE、1 次箱子填坑。Hydrogen 没有炸掉普通墙，Hunyuan 炸掉 2 格，结算相差 7 回合。",["BOX_FILL_PIT","wall_break"]),
    match("sol","doubao","benchmark_strong","跨回合规划与跳跃资源",
          [("反向 0–1 距离为目标路径计算跳跃下界。此场共执行 2 次 JUMP。",535),
           ("由路径签名决定沿用或重建搜索会话，余步短且停滞计数低时续搜。此场共执行 1 次 JUMP。",950)],
          "Sol 推箱 17 次并通关，Doubao 没有 BOX_MOVE、钥匙为零。两场保留相同的结算血量。",["jump","jump"]),
]
local_report=Path("part2_full_mode/audit/thinking_and_tokens_20261120/glm_thinking.md")
glm=attack("glm","benchmark_strong")
save(OVERVIEW/"key_contrasts.md","\n\n".join([
    "# 相同地图上的程序对照",
    "六组对照都核验了双方回放的 T0 棋盘哈希。代码说明定位实现，回放定位动作与结果。",
    *contrast,
    "## 附录　GLM 本地模拟器与标准引擎",
    f"选手本地日志记录 BENCH_STRONG 在 120 回合通关，HP 100。历史标准引擎回放的 GLM 在 T240 达到回合上限，T12 起保持 WAIT。本地记录的程序和棋盘字节未与终局样本成对核验，复现仅能确定标准引擎产生的状态如何触发正式程序的 WAIT。{link(local_report,'选手本地测试输出',5621)} · {clip_link(glm,12)} · {link(BASE/'glm/wait_mystery.md','插桩诊断')}。"
]))

save(OVERVIEW/"README.md","\n\n".join([
    "# 全场程序对照口径",
    "## 复杂度阶梯",
    "第 1 级是静态规则，本场无样本。第 2 级逐拍搜索。第 3 级使用阶段目标或宏动作。第 4 级还会切换搜索策略、子阶段顺序或参数。标志为 0 或 1，层级描述实现结构。认对手的标志仅指显式读取对手身份或预测对手策略。棋盘和机关模型由地形变化列记录。",
    "## 行为指标",
    "每席 13 场 Wave3 计分攻局，共 143 场。强弱基准的 44 个附加回放用于选镜和对照。跨席的 10 张对手图各自不同，三张官方图相同。归一化按指标在 11 席内做 min–max，保留六位小数。某列全相同时统一记 0。较大数值表示原始观测量较大。首拍来源为同图新起标准 worker 的单次复测。",
    "\n".join([
        "- mean_turns 为平均结算回合，含通关、阵亡和达到回合上限。",
        "- clear_rate 为通关局数除以 13。",
        "- wall_breaks_per_match 为每局因爆炸从 W 变为空地的格数均值。",
        "- box_moves_per_match 为每局 BOX_MOVE 事件数均值。一拍滑行可能发出多条事件。",
        "- laser_hits_per_match 为每局 LASER_FIRE.hero_hits 的总数均值。",
        "- jumps_per_match 为每局 JUMP 动作数均值。",
        "- wait_share 为累计执行 WAIT 的回合数除以累计结算回合数，含可能由裁判代执行的 WAIT。",
        "- mean_turn1_seconds 为每席在 13 张计分攻图上的首拍耗时均值，单位为秒。",
    ]),
    link(HERE/"radar_raw.json","原值和归一化上下界")+" · "+link(HERE/"wave3_replay_metrics.json","逐场指标和回放索引")+" · "+link(HERE/"turn1_probe.jsonl","首拍测量")
]))

late=trace[11:]
t=trace[11]
first=t["trials"][0]
assert all(i["trace_action"]==i["archived_action"] for i in trace)
assert len(late)==229 and all(i["branch"]=="reactive" and i["partial_cut_at"]=="MOVE_R" and i["trace_action"]=="WAIT"
                             and i["worker_error"] is None and i.get("exception") is None and i["start"]==[3,21] for i in late)
p=load(HERE/"glm_t12_engine_probe.json")
box=[e for e in p["MOVE_R"]["result"]["events"] if e["type"]=="BOX_MOVE"]
assert len(box)==2 and box[-1]["to"]==[8,21] and p["MOVE_R"]["hp"]==100
wait_md=[
    "# GLM 在强基准图上从 T12 起等待",
    f"GLM T12 的搜索只返回一拍推箱。部分路线过滤删掉这一步，兜底又排除会移动箱子的动作。在余下动作中，WAIT 的评分最低。T12–T240 共 229 回合复现相同分支。{clip_link(glm,12)} · {link(HERE/'glm_wait_trace.jsonl','插桩日志第 12 行',12)}。",
    "## T12 如何走到 WAIT",
    "\n".join([
        f"1. T11 缓存的最后一步 MOVE_D 执行后，勇者到 (3,21)，HP 100。T12 进决策时缓存为空。搜索先试压板 (8,22)。插桩记录首个子搜索展开 {first['nodes']} 个节点并交回不完整路径 [MOVE_R]，后面三个目标均未展开节点。{src('glm',893)} · {src('glm',921)} · {src('glm',950)}。",
        f"2. 部分路线执行前，逐步比较占位层。MOVE_R 会推动 (4,21) 的箱子，首步就被截断，安全前缀长度为 0。{src('glm',973)}。",
        f"3. 兜底再次检查占位变化，排除 MOVE_R。MOVE_U、MOVE_D、MOVE_L 都得到 (0,2,1)，WAIT 得到 (0,1,0)。分数按（是否损血、静态距离、等待优先项）取最小，所以 T12 在距离项就已选出 WAIT。{src('glm',844)} · {src('glm',988)}。",
    ]),
    f"从标准引擎的同一个 T12 初态分别执行一拍。WAIT 留在 (3,21)。MOVE_R 无伤到 (4,21)，箱子经 (5,21) 滑到 (8,21)，记录 2 条 BOX_MOVE。本次单步对照确认引擎允许该推箱。{link(HERE/'glm_t12_engine_probe.json','标准引擎单步对照')}。",
    "## 复现边界",
    f"勇者源码 SHA-256 为 {inline(versions['glm'][1]['sha256'])}。强基准提交与历史回放的防方 SHA-256 一致。标准引擎按历史动作推进，并逐帧核对勇者位置和血量。每回合的插桩建议均与历史动作一致。T12–T240 的 229 次调用没有 worker 错误或被外层捕获的异常。T12 往返耗时 {t['seconds']:.3f} 秒，这段最长 {max(i['seconds'] for i in late):.3f} 秒，均低于裁判的 0.5 秒后续回合上限。",
    f"内部搜索时限限制了 T12 得到的路线。插桩第 12 行记录首个子搜索耗时 {first['elapsed_sec']:.3f} 秒，出搜索时距共享截止约 {first['remaining_sec']*1000:.0f} ms。日志里的节点数和耗时来自这次测量。改变时间预算或解除一拍过滤后能否通关，尚未重跑整局。{src('glm',778)} · {src('glm',866)} · {link(HERE/'trace_glm_wait.py','复现脚本')}。",
    f"选手本地工具另记录 BENCH_STRONG 在 120 回合通关。本地模拟与标准引擎使用的程序、状态生成及地图字节未逐项对齐。现有复现只确认正式程序在标准引擎中的 WAIT 决策链。{link(local_report,'选手本地输出',5621)}。"
]
save(BASE/"glm/wait_mystery.md","\n\n".join(wait_md))

def evidence_link(file,label):
    return link(BASE/file,label)
total_snips=sum(len(p["snippets"]) for p in META.values())
opus=load(BASE/"opus/stats.json")
save(BASE.parent/"HANDOFF_S1e.md","\n\n".join([
    "# S1e 程序拆解资料交接",
    f"按终局清单复核了 11 份送评源码的 SHA-256。Opus 为 {opus['version']}，送评文件 {opus['physical_lines']} 行。每席有五步结构、防图验收、代码统计和逐段选镜。共 {total_snips} 个片段，每段至多 12 行。",
    "## 制作入口",
    "\n".join([
        "- 结构与画面按选手并排查阅。"+ " · ".join(evidence_link(Path(a)/"anatomy.md", a) for a in order),
        "- 用 effects.json 的 source、replay、number 定位 D-07 同屏三件套。turn 压到引擎帧，JSONL 行号指解压后的原始档案行。",
        "- 复杂度阶梯、八轴行为数据和六组同图对照。"+evidence_link("_overview/ladder.csv","阶梯")+" · "+evidence_link("_overview/radar.csv","八轴数据")+" · "+evidence_link("_overview/key_contrasts.md","同图对照")+" · "+evidence_link("_overview/README.md","统计口径"),
        "- GLM 等待段可用 T11 → T12 与 T240 切点。标准引擎确认 MOVE_R 当拍可推箱，程序过滤该步后改选 WAIT。"+evidence_link("glm/wait_mystery.md","T12 诊断与日志"),
    ]),
    "## 验证与覆盖",
    "统计覆盖 143 场计分攻局及额外 44 场强弱基准攻守回放。首拍耗时来自同图新建 worker 的复测，143 个调用均成功。搜索节点均值仅有 GLM 的强基准插桩样本。其余选手的正式档案不包含节点计数。",
    "直接观察以历史帧为准。未插桩的攻方片段仅能联结实际场面和相符的代码逻辑。Doubao 提交图未通过外圈准入，守方回放对应后备图。原始源码、结果和回放保留在原位置。",
    link(WAVE/"versions_manifest.json","终局版本清单")+" · "+link(HERE/"defense_admissions.json","防图验收复核")+" · "+link(HERE/"wave3_replay_metrics.json","回放事件索引")
]))

