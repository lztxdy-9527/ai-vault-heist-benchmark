"""Verify staged sources, per-clip excerpts and pointers against the underlying archives."""
from collections import defaultdict
import gzip
import re
from build_s1e import *

def validate():
    snippets=0
    by_file=defaultdict(lambda:defaultdict(list))
    for a in order:
        folder=BASE/a
        stats=load(folder/"stats.json")
        effects=load(folder/"effects.json")
        assert all((folder/file).is_file() for file in ("stats.json","effects.json","snippets.md","anatomy.md"))
        source=Path(stats["source_file"]).read_bytes()
        assert hashlib.sha256(source).hexdigest()==stats["sha256"]==effects["sha256"]
        source_lines=source.decode("utf-8-sig").splitlines()
        excerpts=re.findall(re.escape(TICK*3)+"python\n(.*?)\n"+re.escape(TICK*3),
                            (folder/"snippets.md").read_text(encoding="utf-8"),flags=re.S)
        assert len(excerpts)==len(effects["effects"]) and 3<=len(excerpts)<=6
        for actual,e in zip(excerpts,effects["effects"],strict=True):
            lo,hi=e["source"]["line_start"],e["source"]["line_end"]
            assert 1<=hi-lo+1<=12 and actual=="\n".join(source_lines[lo-1:hi]),(a,lo)
            ref=e["replay"]
            by_file[ref["file"]][ref["jsonl_line"]].append((a,e))
            snippets+=1
    for path,wanted in by_file.items():
        with gzip.open(path,"rt",encoding="utf-8-sig") as file:
            for line,raw in enumerate(file,1):
                if line not in wanted:
                    continue
                row=json.loads(raw)
                for a,e in wanted.pop(line):
                    ref=e["replay"]
                    assert row["match_id"]==ref["replay_match_id"]
                    frame=row["frames"][ref["turn"]]
                    assert frame["turn"]==ref["turn"]
                    assert isinstance(e["number"]["value"],(int,float))
                    if "frame" in e:
                        sample=e["frame"]
                        assert (sample["action"],sample["hero_position"],sample["hp"])==(frame["action"],frame["hero_pos"],frame["hero_hp"])
                    if a=="opus" and e["side"]=="守":
                        hits=[beam for event in frame["events"] if event["type"]=="LASER_FIRE"
                              for beam in event["beams"] if [35,14] in beam["cells"]]
                        assert any(b["cannon"]==[35,24] for b in hits),hits
                    if e["relation"]=="instrumented_reproduction":
                        assert frame["action"]=="WAIT"
                if not wanted:
                    break
        assert not wanted,wanted
    assert len(replays)==187 and len(probes)==143
    with (OVERVIEW/"radar.csv").open(encoding="utf-8-sig",newline="") as f:
        radar=list(csv.reader(f))
        assert len(radar)==12 and all(len(row)==9 for row in radar)
        assert all(0<=float(s)<=1 for row in radar[1:] for s in row[1:])
    facts=[i for i in lines_json(BASE.parent/"evidence_ledger_v2.jsonl") if i.get("task")=="S1e"]
    assert len(facts)==71 and len({i["id"] for i in facts})==71
    print(f"{len(order)} exact source hashes, {snippets} byte-for-line excerpts, {snippets} archived frames, 187 indexed replays, 143 probes, 71 facts")

if __name__=="__main__":
    validate()

