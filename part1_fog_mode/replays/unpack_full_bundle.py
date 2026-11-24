"""Expand tournament_bundle.json.gz into full demo_bundle.js for arena_stage.html."""
import gzip
from pathlib import Path

HERE = Path(__file__).resolve().parent
with gzip.open(HERE / "tournament_bundle.json.gz", "rt", encoding="utf-8") as f:
    raw = f.read()
(HERE / "tournament_bundle.json").write_text(raw, encoding="utf-8")
(HERE / "demo_bundle.js").write_text(f"window.TOURNAMENT_BUNDLE = {raw};\n", encoding="utf-8")
print("Expanded full Part-1 tournament_bundle.json and demo_bundle.js successfully.")
