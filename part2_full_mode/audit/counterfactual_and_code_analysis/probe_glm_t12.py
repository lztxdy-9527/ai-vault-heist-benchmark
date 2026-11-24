"""Apply two separate actions from the archived GLM T12 state in the standard engine."""
import json
from trace_glm_wait import HERE, ROOT, get_reference, rt

def main():
    ref=get_reference()
    bench=rt.ModelSubmission("benchmark_strong",ROOT/"benchmarks/benchmark_strong.py")
    bench.validate_demon_map()
    assert bench.is_valid_demon and ref["demon_submission_sha256"]==bench.submission_sha256
    result={}
    for action in ("WAIT","MOVE_R"):
        grid=rt.engine.validate_and_decode_dungeon(bench.demon_grid,check_spawn=False)
        engine=rt.engine.DungeonSimulator(grid,mode="FULL")
        for frame in ref["frames"][1:12]:
            engine.step(frame["action"])
        assert (engine.hx,engine.hy,engine.hp)==(3,21,100)
        step=engine.step(action)
        result[action]={"position":[engine.hx,engine.hy],"hp":engine.hp,"result":step}
    path=HERE/"glm_t12_engine_probe.json"
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()

