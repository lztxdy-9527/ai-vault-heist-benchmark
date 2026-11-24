"""Replay the seven reviewed current submissions under the official FULL match limits."""

import ast
import difflib
import gzip
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from itertools import permutations
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT))

from official_maps_full import get_all_backup_maps, get_all_official_maps
from run_tournament_full import ModelSubmission, run_match_simulation


ROOMS = {
    "sol": "P2_02_sol_codex",
    "carbon": "P2_04_carbon_opencode",
    "hydrogen": "P2_05_hydrogen_agy",
    "deepseek": "P2_07_deepseek_dsh",
    "glm": "P2_08_glm_opencode",
    "hunyuan": "P2_09_hunyuan_codebuddy",
    "doubao": "P2_11_doubao_vscode",
}


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Expected exactly one reviewed occurrence of {old!r}")
    return text.replace(old, new, 1)


def convert_reviewed_source(seat, text):
    if seat in {"deepseek", "glm"}:
        class_name = "_Sim" if seat == "deepseek" else "_World"
        cls = next(node for node in ast.parse(text).body
                   if isinstance(node, ast.ClassDef) and node.name == class_name)
        slots = next(node for node in cls.body if isinstance(node, ast.Assign)
                     and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                     and node.targets[0].id == "__slots__")
        entries = ast.literal_eval(slots.value)
        if not isinstance(entries, tuple) or not all(isinstance(e, str) and e.isidentifier() for e in entries):
            raise ValueError(f"Unexpected slots declaration in {seat}")
        lines = text.splitlines(keepends=True)
        del lines[slots.lineno - 1:slots.end_lineno]
        text = "".join(lines)
        # Python 3 provides the same base implicitly. The worker's restricted
        # builtins do not supply a name for the redundant explicit base.
        text = replace_once(text, f"class {class_name}(object):", f"class {class_name}:")
    if seat == "deepseek":
        text = replace_once(text, "class _Plan(object):", "class _Plan:")

    # A normal constructor returns immediately on the three reviewed empty-object
    # paths. The original clone/from_state logic still initializes all fields.
    if seat == "deepseek":
        text = replace_once(text, "def __init__(self, ter, occ, hero, gates, turn=1):\n",
                            "def __init__(self, ter=None, occ=None, hero=None, gates=None, turn=1):\n"
                            "        if ter is None:\n            return\n")
        text = replace_once(text, "s = _Sim.__new__(_Sim)", "s = _Sim()")
    elif seat == "hunyuan":
        text = replace_once(text, "def __init__(self, grid=None, state=None):\n",
                            "def __init__(self, grid=None, state=None):\n"
                            "        if grid is None and state is None:\n            return\n")
        text = replace_once(text, "s = _Sim.__new__(_Sim)", "s = _Sim()")
    elif seat == "doubao":
        text = replace_once(text, "def __init__(self, grid):\n",
                            "def __init__(self, grid=None):\n"
                            "        if grid is None:\n            return\n")
        text = replace_once(text, "w = cls.__new__(cls)", "w = cls()")
        text = replace_once(text, "w = World.__new__(World)", "w = World()")
    elif seat == "hydrogen":
        text = replace_once(text, '"Plates feed pits, switches flip twice, mod-12 waits for none."',
                            '"Plates feed pits. Mod-12 waits for none."')
    compile(text, f"{seat}/submission.py", "exec")
    return text


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare():
    reviewed = json.loads((OUT.parent / "process_recovery_20261119/load_checks.json").read_text(encoding="utf-8"))
    models = {}
    admissions = {}
    for seat, room in ROOMS.items():
        original = ROOT / "exam_rooms" / room / "submission.py"
        raw = original.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        key = {"deepseek": "deepseek_tools", "hunyuan": "hy4"}.get(seat, seat)
        if digest != reviewed[key]["current"]["sha256"]:
            raise ValueError(f"{seat}: current submission changed since review")
        original_text = original.read_text(encoding="utf-8-sig")
        converted = convert_reviewed_source(seat, original_text)
        directory = OUT / "submissions" / seat
        directory.mkdir(parents=True, exist_ok=True)
        source = directory / "submission.py"
        source.write_bytes(converted.encode("utf-8") if converted != original_text else raw)
        if converted != original_text:
            diff = difflib.unified_diff(original_text.splitlines(keepends=True),
                                        converted.splitlines(keepends=True),
                                        fromfile=str(original), tofile=str(source))
            (directory / "review.diff").write_bytes("".join(diff).encode("utf-8"))

        sub = ModelSubmission(seat, source)
        if sub.load_module():
            sub.validate_demon_map()
        else:
            raise RuntimeError(f"{seat}: {sub.disqualify_reason}")
        models[seat] = sub
        admissions[seat] = dict(
            original=str(original), original_sha256=digest, replay_source=str(source),
            replay_sha256=sub.submission_sha256, loaded=sub.loaded,
            valid_demon=sub.is_valid_demon, detail=sub.disqualify_reason,
            spent_gold=sub.spent_gold, author_steps=sub.author_steps,
        )
        print(seat, "LOAD_OK", "MAP_OK" if sub.is_valid_demon else sub.disqualify_reason,
              sub.spent_gold, sub.author_steps, flush=True)
    write_json(OUT / "admissions.json", admissions)
    return models


def own_map(sub):
    return dict(id=sub.model_id, name=sub.cfg["name"], grid=sub.demon_grid,
                spent_gold=sub.spent_gold, vault_gold=sub.vault_gold,
                taunt=sub.build_result.get("taunt", sub.cfg["taunt"]),
                submission_sha256=sub.submission_sha256)


def run_one(i, item, models):
    section, hero, seat, dungeon = item
    result = run_match_simulation(
        match_id=f"P2_RETEST_{i:03d}_{hero.model_id}_vs_{seat}_FULL",
        hero=hero, demon_id=seat, demon_name=dungeon["name"],
        demon_taunt=dungeon["taunt"], demon_spent_gold=dungeon["spent_gold"],
        demon_vault_gold=dungeon["vault_gold"], demon_quotes={},
        map_grid=dungeon["grid"], stage_name=section, is_featured=True,
    )
    result["actual_map_id"] = dungeon["id"]
    result["demon_submission_sha256"] = dungeon.get("submission_sha256")
    if seat in models and not models[seat].is_valid_demon:
        result["demon_score"] = 0.0
    print(f"{i:02d}/91", hero.model_id, "vs", seat, result["status"],
          result["turns"], "respawns", result["worker_respawns"], flush=True)
    return result


def write_result(replays, records, result):
    replays.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    replays.flush()
    records.append({k: v for k, v in result.items() if k != "frames"})


def recover_results(path, plan, replays, records):
    try:
        with gzip.open(path, "rt", encoding="utf-8") as previous:
            for line in previous:
                result = json.loads(line)
                section, hero, seat, dungeon = plan[len(records)]
                assert result["hero_id"] == hero.model_id and result["hero_submission_sha256"] == hero.submission_sha256
                assert result["demon_id"] == seat and result["stage"] == section
                assert result["actual_map_id"] == dungeon["id"]
                assert result["demon_submission_sha256"] == dungeon.get("submission_sha256")
                write_result(replays, records, result)
    except EOFError:
        pass  # A stopped stream can still contain complete, flushed replay entries.


def main():
    resume = "--resume" in sys.argv[1:]
    models = prepare()
    benchmarks = {}
    for tier in ("weak", "strong"):
        seat = f"benchmark_{tier}"
        sub = ModelSubmission(seat, ROOT / "benchmarks" / f"{seat}.py")
        if not sub.load_module():
            raise RuntimeError(sub.disqualify_reason)
        sub.validate_demon_map()
        if not sub.is_valid_demon:
            raise RuntimeError(sub.disqualify_reason)
        benchmarks[seat] = sub

    official = get_all_official_maps()
    backups = iter(get_all_backup_maps()) if any(not sub.is_valid_demon for sub in models.values()) else iter(())
    effective = {seat: own_map(sub) if sub.is_valid_demon else next(backups)
                 for seat, sub in models.items()}
    plan = []
    for hero in models.values():
        for dungeon in official:
            plan.append(("official", hero, dungeon["id"], dungeon))
        for seat, bench in benchmarks.items():
            plan.append(("benchmark_attack", hero, seat, own_map(bench)))
    for hero_seat, demon_seat in permutations(models, 2):
        plan.append(("cross", models[hero_seat], demon_seat, effective[demon_seat]))
    for hero in benchmarks.values():
        for seat, dungeon in effective.items():
            plan.append(("benchmark_defense", hero, seat, dungeon))
    assert len(plan) == 91

    records = []
    final_replay = OUT / "replays.jsonl.gz"
    output_replay = OUT / "replays_resumed.jsonl.gz" if resume else final_replay
    with gzip.open(output_replay, "wt", encoding="utf-8", compresslevel=3) as replays:
        if resume:
            recover_results(final_replay, plan, replays, records)
            print(f"Recovered {len(records)} completed matches", flush=True)
            for start in range(len(records), len(plan), 6):
                batch = list(enumerate(plan[start:start + 6], start + 1))
                with ThreadPoolExecutor(max_workers=6) as pool:
                    futures = [pool.submit(run_one, i, item, models) for i, item in batch]
                    results = [future.result() for future in futures]
                for (i, item), result in zip(batch, results):
                    if result["worker_respawns"] or result["is_dq"]:
                        print(f"Confirming match {i} in isolation", flush=True)
                        result = run_one(i, item, models)
                    write_result(replays, records, result)
        else:
            for i, item in enumerate(plan, 1):
                write_result(replays, records, run_one(i, item, models))
    if resume:
        output_replay.replace(final_replay)
    write_json(OUT / "matches.json", records)


if __name__ == "__main__":
    main()
