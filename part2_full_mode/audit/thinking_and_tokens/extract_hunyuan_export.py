"""Extract the selected CodeBuddy request without reading or writing exam rooms."""
import collections
import datetime
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

out = Path(__file__).resolve().parent
archive = out / 'hunyuan_codebuddy_export.zip'
request_id = 'fe4d83df1f9d4926bd7df4bf1ff54128'
with ZipFile(archive) as zipped:
    entries = [(name, json.loads(zipped.read(name))) for name in zipped.namelist() if name.endswith('.json')]
matches = [(name, conversation, request) for name, record in entries
           for conversation in record['data']['conversations'] for request in conversation['requests']
           if request['id'] == request_id]
[(member, conversation, request)] = matches
messages = request['messages']
assert 'P2_09_hunyuan_codebuddy' in messages[0]['message']


def fenced(text, language=''):
    ticks = '```'
    while ticks in text:
        ticks += '`'
    return f'{ticks}{language}\n{text}\n{ticks}'


zone = datetime.timezone(datetime.timedelta(hours=9))
started = datetime.datetime.fromtimestamp(request['startedAt'] / 1000, zone).isoformat()
header = (f'# 混元 HY4 下半场完整对话与 Thinking\n\n'
          f'来源为 CodeBuddy 历史会话导出 `{archive.name}` 内的 `{member}`。'
          f'请求 `{request_id}` 于 {started} 开始。按导出消息与内容块原序排列，'
          f'逐条时间以导出字段为准，缺时使用序号定位。\n')
full = [header]
thinking = [header.replace('完整对话与 Thinking', 'Thinking 原文摘录')]
counts = collections.Counter()
index = []
for number, envelope in enumerate(messages, 1):
    message = json.loads(envelope['message'])
    role = message['role']
    counts[role] += 1
    blocks = message.get('content', [])
    if isinstance(blocks, str):
        blocks = [{'type': 'text', 'text': blocks}]
    full.append(f'## {number:03d} · {role}\n')
    for ordinal, block in enumerate(blocks, 1):
        kind = block.get('type', 'other')
        counts[f'{role}/{kind}'] += 1
        index.append({'message': number, 'block': ordinal, 'role': role, 'type': kind})
        literal = block.get('text')
        body = fenced(literal) if isinstance(literal, str) else fenced(json.dumps(block, ensure_ascii=False, indent=2), 'json')
        full.extend([f'### {ordinal} · {kind}', body])
        if role == 'assistant' and kind == 'reasoning':
            thinking.extend([f'## {number:03d}.{ordinal} · Thinking', body])

for filename, body in [('hunyuan_thinking.md', full), ('hunyuan_thinking_only.md', thinking)]:
    (out / filename).write_text('\n\n'.join(body) + '\n', encoding='utf-8')
(out / 'hunyuan_export_index.json').write_text(json.dumps({
    'member': member, 'request_id': request_id, 'started_jst': started,
    'counts': counts, 'messages': len(messages), 'blocks': index,
}, ensure_ascii=False, indent=2), encoding='utf-8')
ledger_path = out / 'tokens_supplement.json'
ledger = json.loads(ledger_path.read_text(encoding='utf-8'))
record = ledger['contestants']['hunyuan']
record['conversation_export'] = archive.name
record['conversation_request_id'] = request_id
record['thinking_export_status'] = 'all blocks present in native export'
ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding='utf-8')
readme = out / 'README.md'
contents = readme.read_text(encoding='utf-8')
start = contents.index('1. CodeBuddy')
end = contents.index('\n2. Trae', start)
contents = contents[:start] + '1. CodeBuddy 已用原生批量导出取回目标请求。`hunyuan_thinking.md` 保留全对话与工具记录，`hunyuan_thinking_only.md` 单列 Thinking 原文。' + contents[end:]
readme.write_text(contents, encoding='utf-8')
(out / 'manifest.json').write_text(json.dumps({
    p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    for p in sorted(out.iterdir()) if p.is_file() and p.name != 'manifest.json'
}, indent=2), encoding='utf-8')
print(json.dumps(counts, ensure_ascii=False))
