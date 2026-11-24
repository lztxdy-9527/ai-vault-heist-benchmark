import json,pathlib,re,hashlib
OUT=pathlib.Path(__file__).resolve().parent
ledger=json.loads((OUT/'tokens_supplement.json').read_text(encoding='utf-8'))
log=pathlib.Path(r'<LOCAL_USER_HOME>\AppData\Roaming\CodeBuddy CN\logs\20261119T200317\window1\exthost\Tencent-Cloud.coding-copilot\腾讯云代码助手.log')
for i,line in enumerate(log.open(encoding='utf-8',errors='replace'),1):
 if '2026-11-19 21:11:22.520' in line and 'Agent execution successful with usage:' in line:
  raw=json.loads(line.split('usage:',1)[1]);usage={k:raw[k] for k in ['inputTokens','outputTokens','totalTokens','cacheTokens','cachedWriteTokens','cachedMissTokens','thinkingTokens']};source=f'{log}:{i}'
ledger['contestants']['hunyuan']={'source':source,'status':'native_completion_usage_verified_against_desktop_screenshot','non_cached_input':usage['cachedMissTokens'],'cache_read':usage['cacheTokens'],'cache_write':usage['cachedWriteTokens'],'output':usage['outputTokens'],'reasoning':usage['thinkingTokens'],'total':usage['totalTokens'],'ui_evidence':'hunyuan_tokens_ui.png','reasoning_is_subset_of_output':True}
(OUT/'hunyuan_usage_raw.json').write_text(json.dumps(usage,indent=2),encoding='utf-8')
(OUT/'hunyuan_thinking.md').write_text('''# hunyuan — 界面已恢复的末轮公开回复（不完整）

来源：CodeBuddy CN，打开的“勇者迷宫AI调试与修正”会话；起始用户指令在界面显示为2026/11/19 20:08，路径P2_09_hunyuan_codebuddy。截图 hunyuan_tokens_ui.png。

## 本次采集边界
已核对当前会话归属并保存末轮公开回复及Tokens统计截图。会话树包含955个子节点但被桌面辅助功能接口整体截断，尚未完整导出折叠的Thinking。尝试会话菜单、复制、显示编辑区后，桌面采集连接在选择Qoder窗口时失效；重置后15秒超时。以下只是截图可见末轮，不等同完整思考链。

## 2026-11-19 21:11 左右 — 末轮自述与自测结论
已完成，所有新写文件均在 part2_full_mode/exam_rooms/P2_09_hunyuan_codebuddy/：submission.py（交付答卷）与v22_local_test.py（本地回归工具）；原参战文件未改动。

魔王：造价1740G，金库1260G；PLATE/R_GATE/BOX推箱锁、红蓝双域与单向门，两次跳跃隔离墙，压板配对；author_solution 141步，最后一步首次踏V，声称4向冲入有7个安全落点。

勇者：自带v2.2前向模拟器；红蓝门做分阶段加权A*，压板→近钥匙→远钥匙→金库，推箱阶段使用末收敛压板的切换配置和山启发式，其余阶段用门格步行距离与非压板推箱距离双地图。

自测：8条golden vectors通过；BENCH_WEAK 69步/100HP；BENCH_STRONG 108步/100HP；上半场14图FULL回归9通关、0阵亡、5超时。Turn1搜索预算1.55s，实测最慢1.61s；后续0.30s预算，实测最慢0.344s。说明已知某些复杂毒图Turn1预算内解不完，只能部分计划收尾。

以上是选手公开回复的记录，不是本次重新执行测试。所需“加炸弹逃生”之前的完整思考正文仍缺，不能从代码快照反推补写。

## 界面Token核验
精确总数36,174,194；已与原生日志21:11:22.520的完成汇总一致。细分见tokens_supplement.json。未记录任何费用换算。
''',encoding='utf-8')
(OUT/'doubao_thinking.md').write_text('''# doubao — 待补采，未冒充完整导出

目标：2026-11-19 20:37–22:34 JST，P2_11_doubao_vscode；含两次上下文截断及最后催交。

本次桌面库存只见“Visual Studio Code — doubao_default_vscode”窗口，没有独立Trae窗口；尚不能确认所需历史会话。CodeBuddy采集后桌面连接报unknown or expired node_repl continuation，重置后读取桌面库存仍超时，因此未能进入Trae历史列表、展开Thinking或核对两次截断。此项全部思考正文和精确Token仍为缺失。

已有本地工具日志和先前恢复的代码版本仅可用作索引，不能替代全部助手思考。未引用20:35的last_turn_total_tokens，因为早于本场20:37开始，且存在重复事件。

建议恢复桌面连接后打开本场历史，逐段导出/展开两次截断前后上下文并保存精确会话统计；不得用账户总量、credits或文本长度估算代替。
''',encoding='utf-8')
# The supplied Astra companion is an approval review, not the contestant solver.
p=pathlib.Path(r'<LOCAL_USER_HOME>\.codex\sessions\2026\11\20\rollout-2026-11-20T03-50-37-01a1f525-7f64-76a3-8680-91711678f603.jsonl')
lines=['# Astra审批配套rollout（独立，不合并选手Token）\n','这是审批评审会话；其中引用的选手历史可能与主rollout重叠。只作权限/执行证据，不能当作Astra新增思考或加到主消耗。\n'];last=None
for i,l in enumerate(p.open(encoding='utf-8'),1):
 x=json.loads(l);v=x.get('payload',{});typ=v.get('type')
 if typ=='token_count':last={'source':f'{p}:{i}','timestamp':x.get('timestamp'),'payload':v}
 if x.get('type')=='response_item' and (typ=='reasoning' or (typ=='message' and v.get('role')=='assistant')):
  for b in v.get('summary',v.get('content',[])):
   if b.get('text'):lines+=[f'\n## {x.get("timestamp")} | {p}:{i}\n',b['text']]
(OUT/'astra_approval_review.md').write_text('\n'.join(lines),encoding='utf-8')
(OUT/'astra_approval_token_raw.json').write_text(json.dumps(last,ensure_ascii=False,indent=2),encoding='utf-8')
ledger['contestants']['astra']['approval_sidecar']={'transcript':'astra_approval_review.md','usage':'astra_approval_token_raw.json','included_in_total':False}
# Add locator-only strategy indices from exported blocks, without inventing private thoughts.
for id in ['astra','sol','neon','carbon','glm','deepseek','qwen']:
 p=OUT/f'{id}_thinking.md';s=p.read_text(encoding='utf-8');sections=re.split(r'\n## ',s)
 candidates=[]
 for sec in sections[1:]:
  h,_,body=sec.partition('\n')
  if re.search(r'策略|炸弹|逃生|自测|验证|失败|回滚|A\*|phase|bomb|benchmark|test|bug|search|pass|fail',body,re.I):
   quote=' '.join(body.strip().split())[:180];candidates.append(f'- {h} — {quote}')
 # Spread locators across the full chronology so late overtime/self-tests are not lost.
 selected=candidates if len(candidates)<=30 else [candidates[round(i*(len(candidates)-1)/29)] for i in range(30)]
 p.write_text(s+'\n\n# 关键策略与自测定位（原文关键词索引，非独立验证结论）\n\n'+'\n'.join(selected)+'\n',encoding='utf-8')
for id,v in ledger['contestants'].items():
 if all(v.get(k) is not None for k in ['non_cached_input','cache_read','cache_write','output','total']):
  v['arithmetic_check']=v['non_cached_input']+v['cache_read']+v['cache_write']+v['output']==v['total'];assert v['arithmetic_check'],id
 v['thinking_export']=f'{id}_thinking.md'
ledger['contestants']['qwen']['ui_status']='not_retrieved: desktop helper expired selecting Qoder window; reset inventory timed out'
ledger['contestants']['doubao']['ui_status']='not_retrieved: desktop helper unavailable; no independent Trae window in initial inventory'
ledger['known_totals_only']=sum(v['total'] for v in ledger['contestants'].values() if v.get('total') is not None)
ledger['warning']='Known totals are not a complete tournament total. Missing fields are null, not zero. No currency or credits conversion.'
(OUT/'tokens_supplement.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'README.md').write_text('''# 下半场思考与Token补采

## 已完成
7位磁盘来源（Astra、SOL、Neon、Carbon、GLM、DeepSeek、Qwen）按JST时间顺序导出平台实际保存的明文思考、回复、用户指令与工具决策/自测证据，并附来源行号或seq。SOL覆盖05:06加时最终回复。Astra审批配套独立保存且不叠加。DSH使用read_across_frames=True解压全部拼接帧。OpenCode通过mode=ro和query_only读取，未依赖空session_part表。

Token：Astra/SOL取下半场累计差值；Neon/Carbon/GLM按本场assistant消息相加；DSH216条用量；HY4完成汇总精确细分并有UI总量截图核对。Qwen本地usage全0不当作真实0，Qwen和豆包精确消耗待补。reasoning是output子集，绝不重复加总。

## 未完成，明早需处理
1. CodeBuddy：已定位本场、截图总量并抄录末轮回复，但未取全折叠Thinking及“加炸弹逃生”段。辅助功能会话节点被955子节点截断，复制/导出操作尚未验证成功。
2. Trae：尚未进入目标历史，无完整Thinking和Token；必须核对两次上下文截断。初始库存仅见doubao_default_vscode窗口。
3. Qoder平台用量：窗口选择时桌面采集连接报unknown or expired node_repl continuation，重置后getState在15秒内超时；没有抓到后台精确明细。不要用零占位或账户总消耗填补本场。
4. Codex只保存了明文reasoning摘要的轮次，无法还原未记录/加密的内部完整推理，未虚构补写。

## 完整性
exam_rooms_integrity.json对纳入范围考场所有文件逐一SHA-256比对，确认提取前后未改。AGY Hydrogen和Opus均排除；Neon虽目录后缀_agy，按OpenCode纳入。

## 复现
运行extract_readonly.py后再运行finalize_supplement.py。脚本仅向本目录写文件（含依赖deps）；不执行选手代码，不写exam_rooms。UI截图为hunyuan_tokens_ui.png。
''',encoding='utf-8')
print('finalized',len(ledger['contestants']),'contestants; known total coverage',sum(v.get('total') is not None for v in ledger['contestants'].values()))
