from pathlib import Path

from analyze import WAVE2
from run_noise import HERE, OLD, S1D, WAVE, read, write


def checkpoints():
    wave = "wave1_40m_settled"
    path = OLD / wave / "matches.json"
    manifest = read(OLD / "versions_manifest.json")
    admit_path = S1D / "admission_and_benchmarks.json"
    benchmarks = read(admit_path)["benchmarks"]
    after = read(S1D / "run_config.json")["after_sha256"]
    rows = read(path)
    seats = {}
    for bench in ("benchmark_weak", "benchmark_strong"):
        for index, row in enumerate(rows):
            sid = row["hero_id"]
            if row["match_id"] != f"{wave}_BENCH_{bench.upper()}_DEF_{sid}" or sid.startswith("benchmark"):
                continue
            assert row["hero_submission_sha256"] == manifest[row["hero_ver"]]["sha256"]
            def result(record, version, source, file, locator):
                return dict(version=version, source=source, path=str(file), json_locator=locator,
                            **{key: record[key] for key in ("match_id", "hero_submission_sha256",
                                                          "status", "turns", "hero_hp_left")})
            original = result(row, row["hero_ver"], "original", path, f"$[{index}]")
            production = original
            if sid == "opus":
                rerun = benchmarks[bench]["match"]
                assert row["hero_ver"] == "opus_40m"
                assert rerun["hero_submission_sha256"] == after
                assert row["demon_submission_sha256"] == benchmarks[bench]["defense_hash"]
                production = result(rerun, "opus_1029_lines", "rerun", admit_path,
                                    f"benchmarks.{bench}.match")
            seats.setdefault(sid, {})[bench] = {"original": original, "production": production}
    counts = {}
    for cohort in ("production", "original"):
        counts[cohort] = {bench: sum(row[bench][cohort]["status"] == "CLEARED"
                                    for row in seats.values()) for bench in benchmarks}
    assert len(seats) == 9
    assert counts == {"production": {"benchmark_weak": 5, "benchmark_strong": 3},
                      "original": {"benchmark_weak": 4, "benchmark_strong": 2}}
    return dict(
        cohort_size=len(seats), outside_cohort=["carbon", "hydrogen"], counts=counts, seats=seats,
        production_rule="制作组裁定按净用时归组，Opus 攻方使用 S1d 准入的 1029 行结果，其余沿用原归档。",
        original_rule="三波赛 Wave 1 墙钟快照归组，Opus 使用 opus_40m。",
        note="通过仅计 CLEARED。九席为到达该节点的阵容，Opus 续跑精确用时缺少监考记录。")


def kills():
    out = {}
    for wave in (WAVE2, WAVE):
        path = S1D / "hybrid" / wave / "matches.json"
        originals = read(OLD / wave / "matches.json")
        matches = read(path)
        allowed = [row for row in matches if row["demon_id"] == "opus" and row["is_lethal_kill"]]
        assert len(allowed) == (3 if wave == WAVE2 else 4)
        replay_path = Path(allowed[0]["provenance"]["replay_path"])
        replays = read(replay_path)["featured_matches"]
        items = []
        for row in sorted(allowed, key=lambda item: item["turns"]):
            p = row["provenance"]
            assert row["source"] == "original" and row["stage"].startswith("Stage 2:")
            assert row["actual_map_id"] == "opus_quota"
            assert {key: value for key, value in row.items() if key not in ("source", "provenance")} == originals[p["json_index"]]
            i = int(p["replay_json_locator"].removeprefix("featured_matches[").removesuffix("]"))
            replay = replays[i]
            frames = replay["frames"]
            last = frames[-1]
            assert replay["match_id"] == row["match_id"] and last["turn"] == row["turns"]
            assert last["status"] == "DEAD" and last["hero_hp"] == 0
            damage, = [e for e in last["events"] if e["type"] == "DAMAGE" and e["hp_after"] == 0]
            assert damage["source"] == row["death_reason"]
            cue = dict(turn=last["turn"], action=last["action"], hero_pos=last["hero_pos"],
                       hp_before=frames[-2]["hero_hp"], hp_after=last["hero_hp"], damage=damage)
            if damage["source"] == "LASER":
                shot, = [beam for e in last["events"] if e["type"] == "LASER_FIRE"
                         for beam in e["beams"] if last["hero_pos"] in beam["cells"]]
                cue.update(cannon=shot["cannon"], period=shot["period"], direction=shot["dir"])
            else:
                assert damage["source"] == "EXPLOSION" and damage["self_nominal"] == 50
                source, = [s for e in last["events"] if e["type"] == "EXPLOSION_BATCH" for s in e["sources"]]
                assert source["kind"] == "BOMB"
                placed, = [e for e in frames[-3]["events"] if e["type"] == "BOMB_PLACED"]
                assert (placed["x"], placed["y"]) == (source["x"], source["y"])
                cue.update(bomb_placed_turn=frames[-3]["turn"], bomb_source=source)
            items.append(dict(match_id=row["match_id"], source=row["source"], hero_id=row["hero_id"],
                              hero_name=row["hero_name"], replay_path=str(replay_path),
                              replay_json_locator=p["replay_json_locator"], cue=cue))
        out[wave] = items
    return out


if __name__ == "__main__":
    write(HERE / "hybrid/checkpoint_40m.json", checkpoints())
    write(HERE / "hybrid/opus_defense_kills.json", kills())
