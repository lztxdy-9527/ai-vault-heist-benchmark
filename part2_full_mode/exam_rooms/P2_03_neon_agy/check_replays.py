import json

with open("part1_dungeons_benchmark.json", encoding="utf-8") as f:
    d = json.load(f)

for m in d["my_demon_defense_matches"]:
    if m["hero_id"] in ("glm", "deepseek", "doubao", "sol", "astra"):
        print("=== demon vs", m["hero_id"], m["status"], m["turns"], "===")
        n = len(m["actions"])
        start = max(0, n - 8)
        for i in range(start, n):
            print(f"  T{i+1}: act={m['actions'][i]} pos={m['positions'][i]}->{m['positions'][i+1]} hp={m['hp_trace'][i]}->{m['hp_trace'][i+1]}")

print("=== hero vs qwen around bombs ===")
for m in d["my_hero_matches"]:
    if m["demon_id"] == "qwen":
        for rng in (range(65, 74), range(100, 108)):
            print("  --")
            for i in rng:
                print(f"  T{i+1}: act={m['actions'][i]} pos={m['positions'][i]}->{m['positions'][i+1]} hp={m['hp_trace'][i]}->{m['hp_trace'][i+1]}")
    if m["demon_id"] == "sol":
        print("=== hero vs sol around bombs ===")
        for rng in (range(39, 46), range(51, 58)):
            print("  --")
            for i in rng:
                print(f"  T{i+1}: act={m['actions'][i]} pos={m['positions'][i]}->{m['positions'][i+1]} hp={m['hp_trace'][i]}->{m['hp_trace'][i+1]}")
