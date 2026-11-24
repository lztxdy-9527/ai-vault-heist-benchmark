import sys
sys.path.insert(0, r"<LOCAL_USER_HOME>\.gemini\antigravity\brain\b070b56c-8bd8-4bca-a493-7b8dd9087240\scratch")
from harness import *

grid = S._design()
cost, pos = validate(grid)
print("cost", cost, pos)
# author path
sol = ["MOVE_U"] * 3 + ["MOVE_R"]          # -> (8,10) turn 4
sol += ["MOVE_U"] * 8 + ["MOVE_R"] * 25    # (8,2) -> (33,2) K1
sol += ["MOVE_D"] * 21                     # (33,23) K2
sol += ["MOVE_U"] * 10 + ["MOVE_R"] * 3    # (36,13) V
print(replay(grid, sol), len(sol))
print(sol)
for seq in (["MOVE_R", "MOVE_R", "MOVE_R"], ["MOVE_U", "MOVE_U", "MOVE_R"], ["MOVE_U", "MOVE_U", "WAIT", "WAIT", "WAIT", "WAIT"], ["MOVE_D", "MOVE_D", "MOVE_R"]):
    print(seq, replay(grid, seq + ["WAIT"] * 10))
