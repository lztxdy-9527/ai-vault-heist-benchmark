import json
from pathlib import Path

out = Path(r'part2_full_mode/audit\three_waves_20261120')
diffs = json.loads((out / 'version_diffs_summary.json').read_text(encoding='utf-8'))

print('=== OLD vs NEW VERSION DIFFS ===')
for seat, info in diffs.items():
    print('---', seat, '---')
    for vid, vd in info['versions'].items():
        print(f"  {vid:14s}: valid_demon={vd['valid_demon']} gold={vd['spent_gold']} auth={vd['author_steps']} hero={vd['hero_clears']}/{vd['hero_total']} avg={vd['hero_avg_score']}")
    for ch in info.get('attack_deltas_first_to_last', []):
        o, n = ch['old'], ch['new']
        if o['status'] != n['status'] or abs(ch['score_delta']) >= 5 or abs(o['turns'] - n['turns']) >= 10:
            print(f"    ATK DIFF {ch['map']:18s}: {o['status']}(t={o['turns']},hp={o['hp']},k={o['keys']},s={o['score']}) -> {n['status']}(t={n['turns']},hp={n['hp']},k={n['keys']},s={n['score']}) [{ch['score_delta']:+.2f}]")

print('\n=== DEFENSE DIFFS (VALID MULTI-MAP SEATS) ===')
for seat in ('astra', 'neon', 'glm', 'hunyuan', 'qwen', 'sol'):
    vlist = list(diffs[seat]['versions'].keys())
    v0, v1 = vlist[0], vlist[-1]
    d0 = diffs[seat]['versions'][v0]['defense_details']
    d1 = diffs[seat]['versions'][v1]['defense_details']
    if d0 and d1:
        print(f'  {seat}: {v0} vs {v1}')
        for att in d0:
            if d0[att]['status'] != d1[att]['status'] or abs(d0[att]['demon_score'] - d1[att]['demon_score']) >= 15:
                print(f"    vs {att:14s}: {d0[att]['status']}(t={d0[att]['turns']},ds={d0[att]['demon_score']}) -> {d1[att]['status']}(t={d1[att]['turns']},ds={d1[att]['demon_score']})")

print('\n=== KEY CROSS & LETHAL KILLS BY WAVE ===')
for w in ('wave1_40m_settled', 'wave1_early_21m17m', 'wave2_60m_reinforcements', 'wave3_final_11seats'):
    ms = json.loads((out / w / 'matches.json').read_text(encoding='utf-8'))
    print('***', w, '***')
    for m in ms:
        if m['stage'] == 'Stage 2: 全交叉魔王战':
            if m['is_lethal_kill'] or (m['demon_id'] in ('astra','hydrogen','neon','carbon','sol','opus') and (m['is_cleared'] or m['demon_id'] == 'opus')):
                print(f"  {m['hero_id']:10s} vs {m['demon_id']:10s} => {m['status']:7s} t={m['turns']:3d} hp={m['hero_hp_left']:4d} k={m['keys_collected']} reason={m['death_reason']} hs={m['hero_score']:.1f} ds={m['demon_score']:.1f}")
        elif m['stage'].startswith('Stage 1:') and not m['is_cleared']:
            print(f"  [OFF FAIL] {m['hero_id']:10s} vs {m['demon_id']:18s} => {m['status']} t={m['turns']} k={m['keys_collected']} reason={m['death_reason']}")
