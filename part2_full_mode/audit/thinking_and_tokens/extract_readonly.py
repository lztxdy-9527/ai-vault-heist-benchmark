import collections,datetime,hashlib,io,json,pathlib,re,sqlite3,sys
OUT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(OUT/'deps'))
import zstandard
ROOT=OUT.parents[1]/'exam_rooms'
def hashes():
 return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file() and not any(x in str(p) for x in ['P2_05_hydrogen_agy','P2_06_opus_agy'])}
before=hashes()
def dump(name,obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def jst(t):
 try:
  d=datetime.datetime.fromtimestamp(t/(1000 if t>1e11 else 1),datetime.timezone.utc) if isinstance(t,(int,float)) else datetime.datetime.fromisoformat(t.replace('Z','+00:00'))
  return d.astimezone(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
 except:return str(t)
ledger={'schema':'tokens-only-v1','units':'tokens','reasoning_is_subset_of_output':True,'skipped':['P2_05_hydrogen_agy','P2_06_opus_agy'],'contestants':{}}
FIELDS=['non_cached_input','cache_read','cache_write','output','reasoning','total']
def tokens(id,source,values=None,**extra):ledger['contestants'][id]={'source':source,**dict.fromkeys(FIELDS),**(values or {}),**extra}
def write(id,events,source,notes=''):
 events.sort(key=lambda e:(e['time'],e.get('order',0)))
 lines=[f'# {id} — 下半场已记录过程\n',f'来源：{source}\n', '时间统一为JST。仅导出平台实际记录的明文；空白/未保存思考不补写。工具输出为单独的自测/执行证据，不能当作助手思考。\n',notes]
 for e in events:
  lines += [f"\n## {e['time']} | {e['kind']} | {e['locator']}\n",e['text']]
 (OUT/f'{id}_thinking.md').write_text('\n'.join(lines),encoding='utf-8')
 dump(f'{id}_index.json',[{k:v for k,v in e.items() if k!='text'} for e in events])
 return len(events)
def content(blocks,events,t,loc):
 if isinstance(blocks,str):events.append(dict(time=jst(t),kind='正文',locator=loc,text=blocks));return
 for b in blocks or []:
  if not isinstance(b,dict):continue
  typ=b.get('type','')
  if typ in ['thinking','reasoning','text','input_text','output_text','summary_text']:
   text=b.get('thinking') or b.get('text') or ''
   if text:events.append(dict(time=jst(t),kind=typ,locator=loc,text=text))
  elif typ in ['tool','tool-call','tool_use']:
   state=b.get('state',{});safe={k:b[k] for k in ['name','input','arguments'] if k in b}
   if state:safe['state']={k:state[k] for k in ['status','input','content','output','error'] if k in state}
   events.append(dict(time=jst(t),kind='工具决策/执行证据',locator=loc,text='```json\n'+json.dumps(safe,ensure_ascii=False,indent=2)+'\n```'))
base=pathlib.Path(r'<LOCAL_USER_HOME>\.codex\sessions\2026\11\16')
for id,file,start in [('astra','rollout-2026-11-16T05-07-11-01a1e0d2-2739-7ce1-b181-53e7b9347734.jsonl',738),('sol','rollout-2026-11-16T04-08-45-01a1e09c-a981-7fb1-988d-14dc0b2e33c9.jsonl',754)]:
 p=base/file;events=[];baseline=None;last=None;alllast=None;seen=set()
 for i,line in enumerate(p.open(encoding='utf-8'),1):
  x=json.loads(line);v=x.get('payload',{});t=x.get('timestamp','');loc=f'{p}:{i}'
  if v.get('type')=='token_count':
   alllast={'line':i,'timestamp':t,'payload':v}
   if i<start:baseline=alllast
  if i<start or (id=='sol' and t>'2026-11-19T20:07:00Z'):continue
  if v.get('type')=='token_count':last=alllast
  if x.get('type')=='response_item':
   typ=v.get('type')
   if typ=='message' and v.get('role') in ['user','assistant']:
    n=len(events);content(v.get('content'),events,t,loc)
    for e in events[n:]:e['kind']=v['role']+'/'+e['kind']
   elif typ=='reasoning':content(v.get('summary') or v.get('content'),events,t,loc)
   elif typ in ['function_call','custom_tool_call','function_call_output','custom_tool_call_output']:
    val=v.get('arguments') or v.get('input') or v.get('output') or ''
    if isinstance(val,str) and any(k in val.lower() for k in ['test','verify','result','pass','fail','submission','benchmark']):events.append(dict(time=jst(t),kind=typ,locator=loc,text=val))
  elif x.get('type')=='event_msg' and v.get('type') in ['agent_message','agent_reasoning','user_message']:
   # response_item contains the canonical blocks; event copy retained only when absent later.
   pass
 # Exact text duplicate suppression only for exported model mirrors, not repeated user commands.
 unique=[]
 for e in events:
  key=(e['kind'],e['text'],e['time'][:16])
  if key not in seen:unique.append(e);seen.add(key)
 write(id,unique,str(p),'SOL包含初轮及至JST 2026-11-20 05:07的加时记录；超出截止范围的后续会话不计入该场。' if id=='sol' else '')
 raw={'baseline':baseline,'last_in_scope':last,'last_whole_rollout':alllast};dump(f'{id}_token_count_raw.json',raw)
 def cumulative(r):return (r or {}).get('payload',{}).get('info',{}).get('total_token_usage',{})
 a,b=cumulative(baseline),cumulative(last);delta={k:b.get(k,0)-a.get(k,0) for k in b}
 inp=delta.get('input_tokens');cached=delta.get('cached_input_tokens');output=delta.get('output_tokens')
 tokens(id,str(p),dict(non_cached_input=inp-cached if inp is not None and cached is not None else None,cache_read=cached,cache_write=delta.get('cache_write_input_tokens'),output=output,reasoning=delta.get('reasoning_output_tokens'),total=delta.get('total_tokens')),scope='part2 cumulative delta; SOL includes overtime',raw_token_counts=f'{id}_token_count_raw.json')
# OpenCode: read-only SQLite, inline content first; blob references saved with exact locator.
p=pathlib.Path(r'<LOCAL_USER_HOME>\.local\share\opencode\opencode.db');c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);c.execute('pragma query_only=ON')
for id,sid in [('neon','ses_e0b7605dbffedZYz5Lo6geIMxN'),('carbon','ses_e1f81f5d2ffeEcNqEZUPLt4y8T'),('glm','ses_e1f1d00daffe6T2J1fhNxFBDC5')]:
 events=[];active=False;usage=[]
 for mid,typ,seq,created,data in c.execute('select id,type,seq,time_created,data from session_message where session_id=? order by seq',(sid,)):
  v=json.loads(data)
  if typ=='user' and 'part2_full' in (v.get('text','')+str(v.get('metadata',{}))):active=True
  if not active:continue
  loc=f'{p} session={sid} seq={seq} message={mid}';t=v.get('time',{}).get('created',created)
  if typ=='user':events.append(dict(time=jst(t),kind='用户指令',locator=loc,text=v.get('text','')))
  if typ=='assistant':
   content(v.get('content'),events,t,loc)
   if v.get('tokens'):usage.append({'seq':seq,'time':t,'tokens':v['tokens']})
  for bh,mime,blob in c.execute('select b.hash,b.mime,b.data from blob_ref r join blob b on b.hash=r.hash where r.session_id=? and r.message_id=? order by r.seq',(sid,mid)):
   if mime.startswith('text/') or 'json' in mime:
    text=bytes(blob).decode('utf-8',errors='replace')
    events.append(dict(time=jst(t),kind='关联文本blob',locator=loc+' blob='+bh,text=text))
 write(id,events,str(p)+' '+sid);dump(f'{id}_usage_raw.json',usage)
 agg=collections.Counter()
 for u in usage:
  v=u['tokens'];agg.update(non_cached_input=v.get('input',0),cache_read=v.get('cache',{}).get('read',0),cache_write=v.get('cache',{}).get('write',0),output=v.get('output',0)+v.get('reasoning',0),reasoning=v.get('reasoning',0))
 agg['total']=agg['non_cached_input']+agg['cache_read']+agg['cache_write']+agg['output']
 tokens(id,str(p)+' '+sid,dict(agg),scope='本场首条part2_full用户指令起至该会话末尾',usage_events=len(usage),output_definition='OpenCode output+reasoning，reasoning列为子集')
c.close()
# DSH concatenated zstd: read across every frame, do not stop at first zstd frame.
p=pathlib.Path(r'<LOCAL_USER_HOME>\.dsh\sessions\--REPO-part2_full-exam_rooms-P2_07_deepseek_dsh--\session-a11cda84-af09-4635-97b0-2a5db66db350\session.v4.jsonl.zstd');events=[];usage=[]
with p.open('rb') as f,zstandard.ZstdDecompressor().stream_reader(f,read_across_frames=True) as r:
 for i,l in enumerate(io.TextIOWrapper(r,encoding='utf-8'),1):
  x=json.loads(l);v=x.get('data',{});t=x.get('time');loc=f'{p} decompressed_line={i} seq={x.get("seq")}'
  if x.get('type')=='assistant/message':
   content(v.get('message',{}).get('content'),events,t,loc)
   if v.get('usage'):usage.append({'line':i,'time':t,'usage':v['usage']})
  elif x.get('type') in ['user/message','tool/result','tool/message']:
   events.append(dict(time=jst(t),kind=x['type'],locator=loc,text=json.dumps(v,ensure_ascii=False,indent=2)))
write('deepseek',events,str(p),'源中reasoning块可能为空；仅保存实际非空文本，不推测未记录思考。');dump('deepseek_usage_raw.json',usage)
agg=collections.Counter()
for u in usage:
 v=u['usage'];agg.update(non_cached_input=v.get('inputTokens',0),cache_read=v.get('cacheReadTokens',0),cache_write=v.get('cacheWriteTokens',0),output=v.get('outputTokens',0),total=v.get('totalTokens',0))
tokens('deepseek',str(p),dict(agg),usage_events=len(usage),reasoning_note='平台未单列reasoning，不能据空块推断为0')
# Qoder main + all segment files, deduplicate persisted UUIDs only.
q=pathlib.Path(r'<LOCAL_USER_HOME>\.qoder-cn\projects\REPO-part2-full-exam-rooms-P2-10-qwen-qoder');sid='d65221a8-0f42-4bc3-bfc6-2b4e555404d9';events=[];seen=set();usage=[]
for p in [q/(sid+'.jsonl'),*sorted((q/sid).rglob('*.jsonl'))]:
 for i,l in enumerate(p.open(encoding='utf-8'),1):
  try:x=json.loads(l)
  except ValueError:continue
  uid=x.get('uuid');key=uid or hashlib.sha256(l.encode()).hexdigest()
  if key in seen:continue
  seen.add(key);typ=x.get('type');t=x.get('timestamp','');loc=f'{p}:{i}'
  if isinstance(t,str) and t and t>'2026-11-19T17:48:00Z':continue
  if typ in ['assistant','user']:
   n=len(events);content(x.get('message',{}).get('content'),events,t,loc)
   for e in events[n:]:e['kind']=typ+'/'+e['kind']
  if x.get('message',{}).get('usage'):usage.append({'source':loc,'usage':x['message']['usage']})
write('qwen',events,str(q/sid),'主JSONL与segments合并，按持久化uuid去重。导入的旧对话作为用户上下文保留，不误标为本场Qwen思考。');dump('qwen_usage_raw.json',usage)
tokens('qwen',str(q/sid),status='missing_platform_exact_usage',note='本地usage占位零不作为真实消耗；等待界面精确数据')
for id in ['hunyuan','doubao']:tokens(id,'desktop UI pending',status='pending_ui')
after=hashes();dump('exam_rooms_integrity.json',{'unchanged':before==after,'before':before,'after':after});assert before==after
dump('tokens_supplement.json',ledger)
print({id:len((OUT/f'{id}_thinking.md').read_text(encoding='utf-8')) for id in ledger['contestants'] if (OUT/f'{id}_thinking.md').exists()})
