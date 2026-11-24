import ast, difflib, hashlib, json, re, sys
from pathlib import Path

ROOT = Path(r'<REPO_ROOT>/part2_full')
sys.path.insert(0, str(ROOT))
import run_tournament_full as rt

OUT = ROOT / 'audit' / 'three_waves_20261120'
SUBS_DIR = OUT / 'submissions'
SUBS_DIR.mkdir(parents=True, exist_ok=True)
PR = ROOT / 'audit' / 'process_recovery_20261119'
RT = ROOT / 'audit' / 'retest_20261119' / 'submissions'
ER = ROOT / 'exam_rooms'

def strip_slots_and_object(text: str, class_names: list[str]) -> str:
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    to_del = []
    for cname in class_names:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == cname:
                for b in node.body:
                    if (isinstance(b, ast.Assign) and len(b.targets) == 1
                        and isinstance(b.targets[0], ast.Name) and b.targets[0].id == '__slots__'):
                        to_del.append((b.lineno - 1, b.end_lineno))
    for a, b in sorted(to_del, reverse=True):
        del lines[a:b]
    out = ''.join(lines)
    for cname in class_names:
        out = out.replace(f'class {cname}(object):', f'class {cname}:')
    return out

def compat_patch(ver_id: str, text: str) -> str:
    if ver_id == 'glm_38m':
        text = strip_slots_and_object(text, ['_World'])
    elif ver_id == 'hunyuan_39m':
        assert text.count('def __init__(self, grid=None, state=None):\n') == 1
        text = text.replace(
            'def __init__(self, grid=None, state=None):\n',
            'def __init__(self, grid=None, state=None):\n        if grid is None and state is None:\n            return\n',
            1,
        )
        text = text.replace('s = _Sim.__new__(_Sim)', 's = _Sim()')
    elif ver_id == 'doubao_35m':
        assert text.count('def __init__(self, grid):\n') == 1
        text = text.replace(
            'def __init__(self, grid):\n',
            'def __init__(self, grid=None):\n        if grid is None:\n            return\n',
            1,
        )
        text = text.replace('w = cls.__new__(cls)', 'w = cls()')
        text = text.replace('w = World.__new__(World)', 'w = World()')
    elif ver_id in ('deepseek_14m', 'deepseek_79m'):
        text = strip_slots_and_object(text, ['_Sim', '_Plan'])
        if 'def __init__(self, ter, occ, hero, gates, turn=1):\n' in text:
            text = text.replace(
                'def __init__(self, ter, occ, hero, gates, turn=1):\n',
                'def __init__(self, ter=None, occ=None, hero=None, gates=None, turn=1):\n        if ter is None:\n            return\n',
                1,
            )
        elif 'def __init__(self, ter, occ, gates, hero, turn=1):\n' in text:
            text = text.replace(
                'def __init__(self, ter, occ, gates, hero, turn=1):\n',
                'def __init__(self, ter=None, occ=None, gates=None, hero=None, turn=1):\n        if ter is None:\n            return\n',
                1,
            )
        text = text.replace('s = _Sim.__new__(_Sim)', 's = _Sim()')
    return text

CANDIDATES = {
    'astra_21m': ('astra', ER / 'P2_01_astra_codex/history/CUTOFF_40m00s_04845fa1.py'),
    'astra_39m': ('astra', ER / 'P2_01_astra_codex/postmatch_candidate.py'),
    'sol_17m': ('sol', ER / 'P2_02_sol_codex/submission.py'),
    'sol_39m': ('sol', ER / 'P2_02_sol_codex/submission_overtime.py'),
    'neon_40m': ('neon', ER / 'P2_03_neon_agy/history/CUTOFF_40m00s_dcddc96e.py'),
    'neon_54m': ('neon', ER / 'P2_03_neon_agy/submission.py'),
    'carbon_108m': ('carbon', RT / 'carbon/submission.py'),
    'hydrogen_64m': ('hydrogen', RT / 'hydrogen/submission.py'),
    'opus_40m': ('opus', ER / 'P2_06_opus_agy/history/CUTOFF_40m00s_47b78c89.py'),
    'opus_quota': ('opus', ER / 'P2_06_opus_agy/submission.py'),
    'deepseek_14m': ('deepseek', PR / 'deepseek_tools/05_seq520_submission.py'),
    'deepseek_79m': ('deepseek', PR / 'deepseek_history/02_v01_v01_full_v22_09148101.py'),
    'deepseek_95m': ('deepseek', RT / 'deepseek/submission.py'),
    'glm_38m': ('glm', PR / 'glm/30_seq1339_0_submission.py'),
    'glm_68m': ('glm', RT / 'glm/submission.py'),
    'hunyuan_39m': ('hunyuan', PR / 'hy4/13_xYy9_submission.py'),
    'hunyuan_63m': ('hunyuan', RT / 'hunyuan/submission.py'),
    'qwen_39m': ('qwen', ER / 'P2_10_qwen_qoder/history/CUTOFF_40m00s_60c319ea.py'),
    'qwen_105m': ('qwen', ER / 'P2_10_qwen_qoder/submission.py'),
    'doubao_35m': ('doubao', PR / 'doubao/01_line1385_submission.py'),
    'doubao_117m': ('doubao', RT / 'doubao/submission.py'),
}

meta = {}
for ver_id, (seat_id, src) in CANDIDATES.items():
    raw_text = src.read_text(encoding='utf-8-sig')
    patched = compat_patch(ver_id, raw_text)
    dst_dir = SUBS_DIR / ver_id
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / 'submission.py'
    if patched != raw_text:
        dst.write_text(patched, encoding='utf-8')
    else:
        dst.write_bytes(src.read_bytes())
    sub = rt.ModelSubmission(seat_id, dst)
    ok = sub.load_module()
    if ok:
        sub.validate_demon_map()
    meta[ver_id] = {
        'seat_id': seat_id,
        'orig': str(src),
        'staged': str(dst),
        'sha256': sub.submission_sha256,
        'loaded': ok,
        'valid_demon': sub.is_valid_demon,
        'spent_gold': sub.spent_gold,
        'author_steps': sub.author_steps,
        'reason': sub.disqualify_reason,
    }
    print(f'{ver_id:14s} seat={seat_id:8s} loaded={ok!s:5s} valid={sub.is_valid_demon!s:5s} gold={sub.spent_gold:4d} auth={sub.author_steps:3d} err={sub.disqualify_reason[:65]}')

(OUT / 'versions_manifest.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
