"""Build full demo_bundle_full.js from audit/three_waves/all_unique_matches.jsonl.gz for arena_stage_full.html."""
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
P2 = HERE.parent
src = P2 / "audit" / "three_waves" / "all_unique_matches.jsonl.gz"
summary = json.loads((P2 / "audit" / "three_waves" / "wave3_final_11seats" / "summary.json").read_text(encoding="utf-8"))
matches = []
with gzip.open(src, "rt", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            matches.append(json.loads(line))
bundle = {"summary": summary, "featured_matches": matches}
out_js = HERE / "demo_bundle_full.js"
out_js.write_text("window.TOURNAMENT_BUNDLE = " + json.dumps(bundle, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
print(f"Wrote {len(matches)} unique matches into {out_js}")
