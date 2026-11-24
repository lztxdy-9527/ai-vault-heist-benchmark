# -*- coding: utf-8 -*-
"""
《阴间地牢：金库攻防战》(Vault Siege: Dungeon vs. Hero)
v2.1 Official Deterministic Referee Engine (engine.py)

Strictly implements all 28 Red-Team / Astra audit patches:
- Free outer frame (128 T_W cells = 0G, excluded from 120 inner T_W cap)
- Four-layer truth model: terrain, occupant, bombs, clues
- Row-major deterministic MIMIC clue binding (U, D, L, R) with isolation checks
- 8-step Atomic Displacement Pipeline (Step 32 arrival settles; Step 33 cut off)
- Box-first momentum chain with Hero origin blocking and post-box re-check
- Phase C simultaneous BFS explosion closure & proportional mixed-damage accounting
- Phase D simultaneous laser snapshot (destroying a laser via TNT does not cancel its beam or tick bombs)
- Stage-isolated failure approach scoring & Kill vs. Timeout Demon scoring
"""

from __future__ import annotations
import copy
import json
import math
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

GRID_W = 40
GRID_H = 26
MAX_TURNS = 240
MAX_BUDGET = 3000
MAX_SUB_STEPS = 32
SPAWN_POS = (2, 13)

VALID_ACTIONS = {
    "MOVE_U", "MOVE_D", "MOVE_L", "MOVE_R",
    "JUMP_U", "JUMP_D", "JUMP_L", "JUMP_R",
    "THROW_U", "THROW_D", "THROW_L", "THROW_R",
    "BOMB", "WAIT",
}

DIR_VECTORS: Dict[str, Tuple[int, int]] = {
    "U": (0, -1),
    "D": (0, 1),
    "L": (-1, 0),
    "R": (1, 0),
}

VEC_TO_DIR: Dict[Tuple[int, int], str] = {v: k for k, v in DIR_VECTORS.items()}

MIRROR_TABLE: Dict[str, Dict[Tuple[int, int], Tuple[int, int]]] = {
    "MIRROR_NE": {
        (-1, 0): (0, -1), (1, 0): (0, -1),
        (0, -1): (1, 0),  (0, 1): (1, 0),
    },
    "MIRROR_SE": {
        (-1, 0): (0, 1),  (1, 0): (0, 1),
        (0, -1): (1, 0),  (0, 1): (1, 0),
    },
    "MIRROR_SW": {
        (-1, 0): (0, 1),  (1, 0): (0, 1),
        (0, -1): (-1, 0), (0, 1): (-1, 0),
    },
    "MIRROR_NW": {
        (-1, 0): (0, -1), (1, 0): (0, -1),
        (0, -1): (-1, 0), (0, 1): (-1, 0),
    },
}

SPRING_DIRS: Dict[str, Tuple[int, int]] = {
    "SPRING_U": (0, -1),
    "SPRING_D": (0, 1),
    "SPRING_L": (-1, 0),
    "SPRING_R": (1, 0),
}

LASER_DIRS: Dict[str, Tuple[int, int]] = {
    "LASER_U": (0, -1),
    "LASER_D": (0, 1),
    "LASER_L": (-1, 0),
    "LASER_R": (1, 0),
}

TILE_COSTS: Dict[str, int] = {
    "EMPTY": 0,
    "K1": 0, "K2": 0, "V": 0,
    "W": 5,
    "T_W": 25,
    "ICE": 10,
    "MIRROR_NE": 25, "MIRROR_SE": 25, "MIRROR_SW": 25, "MIRROR_NW": 25,
    "SPRING_U": 35, "SPRING_D": 35, "SPRING_L": 35, "SPRING_R": 35,
    "PIT": 40,
    "LASER_U": 75, "LASER_D": 75, "LASER_L": 75, "LASER_R": 75,
    "CRACK": 20,
    "SWITCH": 30,
    "R_GATE": 20, "B_GATE": 20,
    "TNT": 40,
    "BOX": 30,
    "HEAL": 30,
    "MIMIC": 60,
    "PORTAL_1A": 40, "PORTAL_1B": 40,
    "PORTAL_2A": 40, "PORTAL_2B": 40,
}

EXPLOSION_IMMUNE_TERRAIN = {
    "T_W", "K1", "K2", "V",
    "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
    "PIT",
}


def in_bounds(x: int, y: int) -> bool:
    return 0 <= x < GRID_W and 0 <= y < GRID_H


def is_outer_frame(x: int, y: int) -> bool:
    return x == 0 or x == GRID_W - 1 or y == 0 or y == GRID_H - 1


def is_spawn_clearance(x: int, y: int) -> bool:
    return 1 <= x <= 3 and 12 <= y <= 14


def manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def validate_and_decode_dungeon(grid: List[List[str]]) -> Dict[str, Any]:
    """
    Validates a 26x40 grid against all v2.1 construction & budget rules,
    and decodes it into the 4-layer truth representation.
    Returns a dict with `valid: bool`, `reason: str`, `spent_gold: int`, `vault_gold: int`,
    and decoded layers if valid.
    """
    if not isinstance(grid, list) or len(grid) != GRID_H:
        return {"valid": False, "reason": f"Grid height must be {GRID_H}."}
    for y, row in enumerate(grid):
        if not isinstance(row, list) or len(row) != GRID_W:
            return {"valid": False, "reason": f"Grid row {y} width must be {GRID_W}."}
        for x, cell in enumerate(row):
            if not isinstance(cell, str) or cell not in TILE_COSTS:
                return {"valid": False, "reason": f"Invalid tile '{cell}' at ({x},{y})."}

    # 1. Outer frame check (free 128 T_W)
    for y in range(GRID_H):
        for x in range(GRID_W):
            if is_outer_frame(x, y) and grid[y][x] != "T_W":
                return {"valid": False, "reason": f"Outer frame cell ({x},{y}) must be 'T_W'."}

    # 2. Spawn clearance check
    for y in range(12, 15):
        for x in range(1, 4):
            if grid[y][x] != "EMPTY":
                return {"valid": False, "reason": f"Spawn clearance cell ({x},{y}) must be 'EMPTY'."}

    # 3. Count inner tiles & landmarks
    counts: Dict[str, int] = {k: 0 for k in TILE_COSTS}
    landmarks: Dict[str, List[Tuple[int, int]]] = {"K1": [], "K2": [], "V": []}
    portals: Dict[str, List[Tuple[int, int]]] = {
        "PORTAL_1A": [], "PORTAL_1B": [],
        "PORTAL_2A": [], "PORTAL_2B": [],
    }
    spent_gold = 0

    for y in range(1, GRID_H - 1):
        for x in range(1, GRID_W - 1):
            t = grid[y][x]
            counts[t] += 1
            spent_gold += TILE_COSTS[t]
            if t in landmarks:
                landmarks[t].append((x, y))
            if t in portals:
                portals[t].append((x, y))

    # Landmarks validation
    for lm in ("K1", "K2", "V"):
        if len(landmarks[lm]) != 1:
            return {"valid": False, "reason": f"Must place exactly 1 '{lm}', found {len(landmarks[lm])}."}

    k1_pos = landmarks["K1"][0]
    k2_pos = landmarks["K2"][0]
    v_pos = landmarks["V"][0]

    if not (12 <= k1_pos[0] <= 34 and 2 <= k1_pos[1] <= 10):
        return {"valid": False, "reason": f"K1 at {k1_pos} violates zone x in [12,34], y in [2,10]."}
    if not (12 <= k2_pos[0] <= 34 and 15 <= k2_pos[1] <= 23):
        return {"valid": False, "reason": f"K2 at {k2_pos} violates zone x in [12,34], y in [15,23]."}
    if manhattan(k1_pos, k2_pos) < 12:
        return {"valid": False, "reason": f"Manhattan distance between K1 and K2 is {manhattan(k1_pos, k2_pos)} < 12."}
    if not (33 <= v_pos[0] <= 37 and 4 <= v_pos[1] <= 21):
        return {"valid": False, "reason": f"V at {v_pos} violates zone x in [33,37], y in [4,21]."}

    # Quotas check
    if counts["T_W"] > 120:
        return {"valid": False, "reason": f"Inner T_W count {counts['T_W']} exceeds cap 120."}
    mirror_count = sum(counts[m] for m in ("MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW"))
    if mirror_count > 30:
        return {"valid": False, "reason": f"Total MIRROR count {mirror_count} exceeds cap 30."}
    spring_count = sum(counts[s] for s in ("SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R"))
    if spring_count > 20:
        return {"valid": False, "reason": f"Total SPRING count {spring_count} exceeds cap 20."}
    laser_count = sum(counts[l] for l in ("LASER_U", "LASER_D", "LASER_L", "LASER_R"))
    if laser_count > 12:
        return {"valid": False, "reason": f"Total LASER count {laser_count} exceeds cap 12."}
    if counts["CRACK"] > 40:
        return {"valid": False, "reason": f"CRACK count {counts['CRACK']} exceeds cap 40."}
    if counts["SWITCH"] > 6:
        return {"valid": False, "reason": f"SWITCH count {counts['SWITCH']} exceeds cap 6."}
    gate_count = counts["R_GATE"] + counts["B_GATE"]
    if gate_count > 16:
        return {"valid": False, "reason": f"Total GATE count {gate_count} exceeds cap 16."}
    if counts["TNT"] > 12:
        return {"valid": False, "reason": f"TNT count {counts['TNT']} exceeds cap 12."}
    if counts["BOX"] > 4:
        return {"valid": False, "reason": f"BOX count {counts['BOX']} exceeds cap 4."}
    if counts["HEAL"] > 4:
        return {"valid": False, "reason": f"HEAL count {counts['HEAL']} exceeds cap 4."}
    if counts["MIMIC"] > 4:
        return {"valid": False, "reason": f"MIMIC count {counts['MIMIC']} exceeds cap 4."}

    # Portals pairing check
    for p_idx in ("1", "2"):
        pa = f"PORTAL_{p_idx}A"
        pb = f"PORTAL_{p_idx}B"
        if len(portals[pa]) > 1 or len(portals[pb]) > 1:
            return {"valid": False, "reason": f"Duplicate portal endpoints for pair {p_idx}."}
        if len(portals[pa]) != len(portals[pb]):
            return {"valid": False, "reason": f"Unpaired portal endpoints {pa} and {pb}."}

    if spent_gold > MAX_BUDGET:
        return {"valid": False, "reason": f"Spent gold {spent_gold}G exceeds budget {MAX_BUDGET}G."}

    # 4. Decode into Four-Layer Truth Model
    terrain: List[List[str]] = [["EMPTY"] * GRID_W for _ in range(GRID_H)]
    occupant: List[List[Optional[str]]] = [[None] * GRID_W for _ in range(GRID_H)]
    clues: List[List[bool]] = [[False] * GRID_W for _ in range(GRID_H)]
    mimic_to_clue: Dict[Tuple[int, int], Tuple[int, int]] = {}

    for y in range(GRID_H):
        for x in range(GRID_W):
            cell = grid[y][x]
            if cell in ("BOX", "TNT"):
                terrain[y][x] = "EMPTY"
                occupant[y][x] = cell
            else:
                terrain[y][x] = cell
                occupant[y][x] = None

    # 5. Bind MIMIC exclusive clues in row-major order
    for y in range(1, GRID_H - 1):
        for x in range(1, GRID_W - 1):
            if terrain[y][x] == "MIMIC":
                bound_coord: Optional[Tuple[int, int]] = None
                for dir_key in ("U", "D", "L", "R"):
                    dx, dy = DIR_VECTORS[dir_key]
                    nx, ny = x + dx, y + dy
                    if not in_bounds(nx, ny):
                        continue
                    if terrain[ny][nx] != "EMPTY" or occupant[ny][nx] is not None:
                        continue
                    if is_spawn_clearance(nx, ny):
                        continue
                    if clues[ny][nx]:
                        continue
                    # Check that (nx, ny) is not orthogonally adjacent to any OTHER chest (HEAL or MIMIC)
                    adj_other_chest = False
                    for adx, ady in DIR_VECTORS.values():
                        cx, cy = nx + adx, ny + ady
                        if (cx, cy) == (x, y):
                            continue
                        if in_bounds(cx, cy) and terrain[cy][cx] in ("HEAL", "MIMIC"):
                            adj_other_chest = True
                            break
                    if not adj_other_chest:
                        bound_coord = (nx, ny)
                        break
                if bound_coord is None:
                    return {
                        "valid": False,
                        "reason": f"MIMIC at ({x},{y}) has no valid isolated clue cell.",
                    }
                clues[bound_coord[1]][bound_coord[0]] = True
                mimic_to_clue[(x, y)] = bound_coord

    portal_map: Dict[Tuple[int, int], Tuple[int, int]] = {}
    for p_idx in ("1", "2"):
        pa = f"PORTAL_{p_idx}A"
        pb = f"PORTAL_{p_idx}B"
        if portals[pa] and portals[pb]:
            pos_a = portals[pa][0]
            pos_b = portals[pb][0]
            portal_map[pos_a] = pos_b
            portal_map[pos_b] = pos_a

    if not static_geometry_reachable(terrain, portal_map, {k: v[0] for k, v in landmarks.items()}):
        return {"valid": False, "reason": "Static geometry cannot connect spawn, both keys and vault."}

    return {
        "valid": True,
        "reason": "OK",
        "spent_gold": spent_gold,
        "vault_gold": MAX_BUDGET - spent_gold,
        "inner_tw_count": counts["T_W"],
        "terrain": terrain,
        "occupant": occupant,
        "clues": clues,
        "mimic_to_clue": mimic_to_clue,
        "portal_map": portal_map,
        "targets": {
            "K1": list(k1_pos),
            "K2": list(k2_pos),
            "V": list(v_pos),
        },
    }


def static_geometry_reachable(terrain, portal_map, targets) -> bool:
    """Necessary geometric state-graph check; exact author replay remains mandatory.

    Destructible objects are optimistically removable, doors may open if switches
    exist, and jump/spring/portal edges are included. This never substitutes for
    checking inventory, timing, forced momentum and survival in the certificate.
    Both key orders are legal under RULES section II.1.
    """
    has_switch = any("SWITCH" in row for row in terrain)

    def solid(x, y):
        if not in_bounds(x, y) or terrain[y][x] == "T_W":
            return True
        return terrain[y][x] == "R_GATE" and not has_switch

    def node(x, y, keys):
        if (x, y) == targets["K1"]:
            keys |= 1
        if (x, y) == targets["K2"]:
            keys |= 2
        return x, y, keys

    start = (*SPAWN_POS, 0)
    queue, seen = deque([start]), {start}
    while queue:
        x, y, keys = queue.popleft()
        if keys == 3 and (x, y) == targets["V"]:
            return True
        candidates = []
        for dx, dy in DIR_VECTORS.values():
            if not solid(x + dx, y + dy):
                candidates.append((x + dx, y + dy))
                if not solid(x + 2 * dx, y + 2 * dy):
                    candidates.append((x + 2 * dx, y + 2 * dy))
        if terrain[y][x] in SPRING_DIRS:
            dx, dy = SPRING_DIRS[terrain[y][x]]
            distance = 0
            for k in (1, 2, 3):
                if solid(x + k * dx, y + k * dy):
                    break
                distance = k
            if distance:
                candidates.append((x + distance * dx, y + distance * dy))
        if (x, y) in portal_map:
            candidates.append(portal_map[(x, y)])
        for nx, ny in candidates:
            if solid(nx, ny) or terrain[ny][nx] == "PIT":
                continue
            nxt = node(nx, ny, keys)
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return False


class DungeonSimulator:
    """
    Deterministic v2.1 Turn & Sub-Tick Physics Simulator.
    """

    def __init__(self, decoded_dungeon: Dict[str, Any], mode: str = "FULL"):
        self.mode = mode  # "BLIND" or "FULL"
        self.spent_gold: int = decoded_dungeon["spent_gold"]
        self.vault_gold: int = decoded_dungeon["vault_gold"]
        self.terrain: List[List[str]] = copy.deepcopy(decoded_dungeon["terrain"])
        self.occupant: List[List[Optional[str]]] = copy.deepcopy(decoded_dungeon["occupant"])
        self.clues: List[List[bool]] = copy.deepcopy(decoded_dungeon["clues"])
        self.mimic_to_clue: Dict[Tuple[int, int], Tuple[int, int]] = dict(decoded_dungeon["mimic_to_clue"])
        self.portal_map: Dict[Tuple[int, int], Tuple[int, int]] = dict(decoded_dungeon["portal_map"])
        self.targets: Dict[str, List[int]] = copy.deepcopy(decoded_dungeon["targets"])

        self.turn: int = 1
        self.gates_flipped: bool = False
        self.hx: int = SPAWN_POS[0]
        self.hy: int = SPAWN_POS[1]
        self.hp: int = 100
        self.has_k1: bool = False
        self.has_k2: bool = False
        self.jumps: int = 3
        self.throws: int = 3
        self.bombs_left: int = 2

        self.bombs: List[Dict[str, int]] = []
        self.next_bomb_id: int = 1

        self.status: str = "ALIVE"  # "ALIVE", "DEAD", "CLEARED", "TIMEOUT"
        self.death_reason: str = ""
        self.trap_damage_total: float = 0.0
        self.error_streak: int = 0

        # Per-turn transient state
        self.exposed_cells: Set[Tuple[int, int]] = {(self.hx, self.hy)}
        self.tnt_armed: Set[Tuple[int, int]] = set()
        self.last_executed_turn: int = 0
        self.last_steps_taken: int = 0
        self.last_portal_count: int = 0
        self.last_phase_d_executed: bool = False
        self.last_laser_Warning_beams: List[Dict[str, Any]] = []
        self.last_turn_events: List[Dict[str, Any]] = []

        # Stage-isolated distance progress tracker (Patch 04)
        self.stage_d0: int = self._current_stage_target_dist(self.hx, self.hy)
        self.stage_dmin: int = self.stage_d0

    def _current_stage_target_dist(self, x: int, y: int) -> int:
        k1 = (self.targets["K1"][0], self.targets["K1"][1])
        k2 = (self.targets["K2"][0], self.targets["K2"][1])
        v = (self.targets["V"][0], self.targets["V"][1])
        if not self.has_k1 and not self.has_k2:
            return min(manhattan((x, y), k1), manhattan((x, y), k2))
        elif self.has_k1 and not self.has_k2:
            return manhattan((x, y), k2)
        elif not self.has_k1 and self.has_k2:
            return manhattan((x, y), k1)
        else:
            return manhattan((x, y), v)

    def _update_stage_progress(self) -> None:
        d = self._current_stage_target_dist(self.hx, self.hy)
        if d < self.stage_dmin:
            self.stage_dmin = d

    def _reset_stage_progress_on_new_key(self) -> None:
        self.stage_d0 = self._current_stage_target_dist(self.hx, self.hy)
        self.stage_dmin = self.stage_d0

    def is_high_wall(self, x: int, y: int) -> bool:
        if not in_bounds(x, y):
            return True
        t = self.terrain[y][x]
        if t in ("W", "T_W", "LASER_U", "LASER_D", "LASER_L", "LASER_R"):
            return True
        if t == "R_GATE" and not self.gates_flipped:
            return True
        if t == "B_GATE" and self.gates_flipped:
            return True
        return False

    def is_enterable_for_entity(self, x: int, y: int, entity: str) -> bool:
        if not in_bounds(x, y):
            return False
        if self.is_high_wall(x, y):
            return False
        if self.occupant[y][x] in ("BOX", "TNT"):
            return False
        if entity == "BOX":
            if (x, y) == (self.hx, self.hy):
                return False
            if self.terrain[y][x] in ("K1", "K2", "V"):
                return False
        return True

    def _clear_mimic(self, x: int, y: int) -> None:
        self.terrain[y][x] = "EMPTY"
        clue_pos = self.mimic_to_clue.pop((x, y), None)
        if clue_pos is not None:
            cx, cy = clue_pos
            self.clues[cy][cx] = False

    def _apply_damage_batch(self, trap_nominal: int, self_nominal: int, source: str = "") -> None:
        total = trap_nominal + self_nominal
        if total <= 0 or self.hp <= 0:
            return
        h_before = self.hp
        eff_trap = min(float(h_before), float(total)) * (float(trap_nominal) / float(total))
        self.trap_damage_total = min(100.0, self.trap_damage_total + eff_trap)
        self.hp -= total
        self.last_turn_events.append({
            "type": "DAMAGE",
            "source": source,
            "trap_nominal": trap_nominal,
            "self_nominal": self_nominal,
            "hp_after": self.hp,
        })
        if self.hp <= 0:
            self.status = "DEAD"
            self.death_reason = source

    def _execute_atomic_displacement(
        self,
        entity: str,
        p0: Tuple[int, int],
        p1: Tuple[int, int],
        direction: Tuple[int, int],
        state_tracker: Dict[str, Any],
        arrived_via_portal: bool = False,
    ) -> None:
        """
        Executes the 8-step Atomic Displacement Pipeline for `entity` ("HERO" or "BOX")
        moving from `p0` to `p1`.
        """
        if self.status in ("DEAD", "CLEARED"):
            return

        x0, y0 = p0
        x1, y1 = p1

        # Step 1: Increment displacement count
        state_tracker["steps_taken"] += 1
        self.last_steps_taken = state_tracker["steps_taken"]

        # Step 2: Leave Hook on p0
        if self.terrain[y0][x0] == "CRACK":
            self.terrain[y0][x0] = "PIT"
            self.last_turn_events.append({"type": "CRACK_COLLAPSE", "x": x0, "y": y0})

        # Step 3: Update coordinates and exposed trajectory
        if entity == "BOX":
            self.occupant[y0][x0] = None
            self.occupant[y1][x1] = "BOX"
            self.last_turn_events.append({"type": "BOX_MOVE", "from": [x0, y0], "to": [x1, y1]})
        else:
            self.hx, self.hy = x1, y1
            self.exposed_cells.add((x1, y1))
            # Fatal arrival is still an actually reached point for failure scoring.
            self._update_stage_progress()
            self.last_turn_events.append({"type": "HERO_MOVE", "from": [x0, y0], "to": [x1, y1]})

        # Step 4: Arrive Hook on p1
        t1 = self.terrain[y1][x1]
        if entity == "BOX":
            if t1 == "PIT":
                self.occupant[y1][x1] = None
                self.terrain[y1][x1] = "EMPTY"
                self.last_turn_events.append({"type": "BOX_FILL_PIT", "x": x1, "y": y1})
                return
            elif t1 == "MIMIC":
                self._clear_mimic(x1, y1)
                self.last_turn_events.append({"type": "BOX_CRUSH_MIMIC", "x": x1, "y": y1})
            elif t1 == "SWITCH":
                self.gates_flipped = not self.gates_flipped
                self.last_turn_events.append({"type": "SWITCH_FLIP", "by": "BOX", "x": x1, "y": y1, "gates_flipped": self.gates_flipped})
        else:
            if t1 == "PIT":
                self._apply_damage_batch(100, 0, source="PIT")
            elif t1 == "MIMIC":
                self._clear_mimic(x1, y1)
                state_tracker["stop_momentum"] = True
                self._apply_damage_batch(45, 0, source="MIMIC")
            elif t1 == "HEAL":
                self.hp = min(100, self.hp + 30)
                self.terrain[y1][x1] = "EMPTY"
                self.last_turn_events.append({"type": "HEAL", "x": x1, "y": y1, "hp_after": self.hp})
            elif t1 == "SWITCH":
                self.gates_flipped = not self.gates_flipped
                self.last_turn_events.append({"type": "SWITCH_FLIP", "by": "HERO", "x": x1, "y": y1, "gates_flipped": self.gates_flipped})

        # Step 5: Death Immediate Cutoff
        if self.hp <= 0 or self.status == "DEAD":
            return

        # Step 6: Key Pickup & Win Immediate Cutoff
        if entity == "HERO":
            t1_now = self.terrain[y1][x1]
            picked_new_key = False
            if t1_now == "K1":
                self.has_k1 = True
                self.terrain[y1][x1] = "EMPTY"
                picked_new_key = True
                self.last_turn_events.append({"type": "PICK_KEY", "key": "K1", "x": x1, "y": y1})
            elif t1_now == "K2":
                self.has_k2 = True
                self.terrain[y1][x1] = "EMPTY"
                picked_new_key = True
                self.last_turn_events.append({"type": "PICK_KEY", "key": "K2", "x": x1, "y": y1})

            if picked_new_key:
                self._reset_stage_progress_on_new_key()
            else:
                self._update_stage_progress()

            if t1_now == "V" and self.has_k1 and self.has_k2 and self.hp > 0:
                self.status = "CLEARED"
                self.last_turn_events.append({"type": "VAULT_CLEARED", "x": x1, "y": y1, "turn": self.turn})
                return

        # Step 7: Step Cap (32) & Stop Momentum Cutoff
        if state_tracker["steps_taken"] >= MAX_SUB_STEPS or state_tracker.get("stop_momentum", False):
            return

        # Step 8: Momentum Continuation
        if arrived_via_portal:
            if state_tracker["portal_count"] >= 2:
                return
            # portal_count == 1: step 1 tile out of exit portal along current direction
            dx, dy = direction
            nx, ny = x1 + dx, y1 + dy
            if self.is_enterable_for_entity(nx, ny, entity):
                self._execute_atomic_displacement(
                    entity, (x1, y1), (nx, ny), direction, state_tracker, arrived_via_portal=False
                )
            return

        t_curr = self.terrain[y1][x1]

        if t_curr == "ICE":
            dx, dy = direction
            nx, ny = x1 + dx, y1 + dy
            if self.is_enterable_for_entity(nx, ny, entity):
                self._execute_atomic_displacement(
                    entity, (x1, y1), (nx, ny), direction, state_tracker, arrived_via_portal=False
                )
            return

        if t_curr in MIRROR_TABLE:
            new_dir = MIRROR_TABLE[t_curr][direction]
            ndx, ndy = new_dir
            nx, ny = x1 + ndx, y1 + ndy
            if self.is_enterable_for_entity(nx, ny, entity):
                self._execute_atomic_displacement(
                    entity, (x1, y1), (nx, ny), new_dir, state_tracker, arrived_via_portal=False
                )
            return

        if t_curr in SPRING_DIRS:
            sdir = SPRING_DIRS[t_curr]
            sdx, sdy = sdir
            blocked_k: Optional[int] = None
            for k in (1, 2, 3):
                kx, ky = x1 + k * sdx, y1 + k * sdy
                if not self.is_enterable_for_entity(kx, ky, entity):
                    blocked_k = k
                    if entity == "BOX" and in_bounds(kx, ky) and self.occupant[ky][kx] == "TNT":
                        self.tnt_armed.add((kx, ky))
                    break
            if blocked_k == 1:
                return
            elif blocked_k in (2, 3):
                land_k = blocked_k - 1
                lx, ly = x1 + land_k * sdx, y1 + land_k * sdy
                self._execute_atomic_displacement(
                    entity, (x1, y1), (lx, ly), sdir, state_tracker, arrived_via_portal=False
                )
            else:
                lx, ly = x1 + 3 * sdx, y1 + 3 * sdy
                self._execute_atomic_displacement(
                    entity, (x1, y1), (lx, ly), sdir, state_tracker, arrived_via_portal=False
                )
            return

        if t_curr in ("PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B"):
            if state_tracker["portal_count"] >= 2:
                return
            pair_pos = self.portal_map.get((x1, y1))
            if pair_pos is not None and self.is_enterable_for_entity(pair_pos[0], pair_pos[1], entity):
                state_tracker["portal_count"] += 1
                self.last_portal_count = state_tracker["portal_count"]
                self._execute_atomic_displacement(
                    entity, (x1, y1), pair_pos, direction, state_tracker, arrived_via_portal=True
                )
            return

    def _execute_throw(self, direction: Tuple[int, int]) -> None:
        if self.throws <= 0:
            return
        self.throws -= 1
        sx, sy = self.hx, self.hy
        curr_dir = direction
        range_left = 6
        stone_portals = 0

        # Air flight loop (range_left > 0)
        while range_left > 0:
            dx, dy = curr_dir
            nx, ny = sx + dx, sy + dy
            range_left -= 1
            sx, sy = nx, ny
            if not in_bounds(sx, sy) or self.is_high_wall(sx, sy) or self.occupant[sy][sx] == "BOX":
                return
            if self.occupant[sy][sx] == "TNT":
                self.tnt_armed.add((sx, sy))
                return
            t = self.terrain[sy][sx]
            if t == "SWITCH":
                self.gates_flipped = not self.gates_flipped
                self.last_turn_events.append({"type": "SWITCH_FLIP", "by": "STONE", "x": sx, "y": sy, "gates_flipped": self.gates_flipped})
                return
            if t == "MIMIC":
                self._clear_mimic(sx, sy)
                self.last_turn_events.append({"type": "STONE_DESTROY_MIMIC", "x": sx, "y": sy})
                return
            if t in MIRROR_TABLE:
                curr_dir = MIRROR_TABLE[t][curr_dir]
                continue
            if t in ("PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B") and stone_portals < 2:
                pair_pos = self.portal_map.get((sx, sy))
                if pair_pos is not None:
                    px, py = pair_pos
                    if not self.is_high_wall(px, py) and self.occupant[py][px] not in ("BOX", "TNT"):
                        sx, sy = px, py
                        stone_portals += 1
                        if stone_portals >= 2:
                            return

        # Ground slide extension if 6th tile is ICE or MIRROR_*
        if in_bounds(sx, sy) and (self.terrain[sy][sx] == "ICE" or self.terrain[sy][sx] in MIRROR_TABLE):
            slide_steps = 0
            while slide_steps < MAX_SUB_STEPS:
                dx, dy = curr_dir
                nx, ny = sx + dx, sy + dy
                slide_steps += 1
                sx, sy = nx, ny
                if not in_bounds(sx, sy) or self.is_high_wall(sx, sy) or self.occupant[sy][sx] == "BOX":
                    return
                if self.occupant[sy][sx] == "TNT":
                    self.tnt_armed.add((sx, sy))
                    return
                t = self.terrain[sy][sx]
                if t == "SWITCH":
                    self.gates_flipped = not self.gates_flipped
                    self.last_turn_events.append({"type": "SWITCH_FLIP", "by": "STONE", "x": sx, "y": sy, "gates_flipped": self.gates_flipped})
                    return
                if t == "MIMIC":
                    self._clear_mimic(sx, sy)
                    self.last_turn_events.append({"type": "STONE_DESTROY_MIMIC", "x": sx, "y": sy})
                    return
                if t in MIRROR_TABLE:
                    curr_dir = MIRROR_TABLE[t][curr_dir]
                    continue
                if t == "ICE":
                    continue
                if t in ("PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B") and stone_portals < 2:
                    pair_pos = self.portal_map.get((sx, sy))
                    if pair_pos is not None:
                        px, py = pair_pos
                        if not self.is_high_wall(px, py) and self.occupant[py][px] not in ("BOX", "TNT"):
                            sx, sy = px, py
                            stone_portals += 1
                            if stone_portals >= 2:
                                return
                            continue
                # Any other terrain stops ground slide
                return

    def _resolve_explosion_closure(
        self,
        initial_bomb_ids: Set[int],
        initial_tnts: Set[Tuple[int, int]],
    ) -> None:
        """
        Executes Phase C steps 3 & 4: BFS chain explosion closure and batch damage/terrain settlement.
        Does NOT decrement bomb timers (caller handles timer decrement only in Phase C step 1).
        """
        if not initial_bomb_ids and not initial_tnts:
            return

        exploded_bomb_ids: Set[int] = set(initial_bomb_ids)
        exploded_tnts: Set[Tuple[int, int]] = set(initial_tnts)

        # Queue of (x, y, source_type) where source_type is "BOMB" or "TNT"
        queue: List[Tuple[int, int, str]] = []
        for b in self.bombs:
            if b["id"] in exploded_bomb_ids:
                queue.append((b["x"], b["y"], "BOMB"))
        for (tx, ty) in exploded_tnts:
            queue.append((tx, ty, "TNT"))

        blast_cells: Set[Tuple[int, int]] = set()
        q_idx = 0
        while q_idx < len(queue):
            ex, ey, _ = queue[q_idx]
            q_idx += 1
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    cx, cy = ex + dx, ey + dy
                    if not in_bounds(cx, cy):
                        continue
                    blast_cells.add((cx, cy))
                    # Chain to unexploded TNT
                    if self.occupant[cy][cx] == "TNT" and (cx, cy) not in exploded_tnts:
                        exploded_tnts.add((cx, cy))
                        queue.append((cx, cy, "TNT"))
                    # Chain to unexploded BOMB
                    for b in self.bombs:
                        if b["x"] == cx and b["y"] == cy and b["id"] not in exploded_bomb_ids:
                            exploded_bomb_ids.add(b["id"])
                            queue.append((b["x"], b["y"], "BOMB"))

        # Batch damage calculation on hero (hx, hy)
        trap_nominal = 0
        self_nominal = 0
        for ex, ey, stype in queue:
            if abs(self.hx - ex) <= 1 and abs(self.hy - ey) <= 1:
                if stype == "TNT":
                    trap_nominal += 60
                else:
                    self_nominal += 50

        if trap_nominal + self_nominal > 0:
            self._apply_damage_batch(trap_nominal, self_nominal, source="EXPLOSION")

        # Remove exploded bombs and TNTs
        self.bombs = [b for b in self.bombs if b["id"] not in exploded_bomb_ids]
        for (tx, ty) in exploded_tnts:
            if self.occupant[ty][tx] == "TNT":
                self.occupant[ty][tx] = None

        self.last_turn_events.append({
            "type": "EXPLOSION_BATCH",
            "sources": [{"x": ex, "y": ey, "kind": stype} for ex, ey, stype in queue],
            "blast_cells": [[cx, cy] for cx, cy in sorted(blast_cells)],
        })

        # Settle terrain and BOX destruction across union of 3x3 blast cells
        for cx, cy in blast_cells:
            if self.occupant[cy][cx] == "BOX":
                self.occupant[cy][cx] = None
            t = self.terrain[cy][cx]
            if t in EXPLOSION_IMMUNE_TERRAIN:
                continue
            elif t == "CRACK":
                self.terrain[cy][cx] = "PIT"
            elif t == "MIMIC":
                self._clear_mimic(cx, cy)
            else:
                self.terrain[cy][cx] = "EMPTY"

        # Post-explosion support check
        for y in range(GRID_H):
            for x in range(GRID_W):
                if self.occupant[y][x] == "BOX" and self.terrain[y][x] == "PIT":
                    self.occupant[y][x] = None
                    self.terrain[y][x] = "EMPTY"

        if self.hp > 0 and self.status != "DEAD" and self.terrain[self.hy][self.hx] == "PIT":
            self._apply_damage_batch(100, 0, source="PIT_FROM_EXPLOSION")

    def compute_laser_snapshot(self) -> Tuple[List[Dict[str, Any]], Set[Tuple[int, int]]]:
        """
        Computes simultaneous laser beams based on current map state.
        Returns (beams_list, hit_tnts_set).
        Each item in beams_list: {"cannon": (lx, ly), "dir": "U/D/L/R", "cells": [(x,y), ...]}
        """
        beams: List[Dict[str, Any]] = []
        hit_tnts: Set[Tuple[int, int]] = set()

        for y in range(1, GRID_H - 1):
            for x in range(1, GRID_W - 1):
                t = self.terrain[y][x]
                if t in LASER_DIRS:
                    dx, dy = LASER_DIRS[t]
                    dir_char = t.split("_")[1]
                    beam_cells: List[Tuple[int, int]] = []
                    for dist in range(1, 11):
                        bx, by = x + dist * dx, y + dist * dy
                        if not in_bounds(bx, by):
                            break
                        if self.is_high_wall(bx, by) or self.occupant[by][bx] == "BOX":
                            break
                        if self.occupant[by][bx] == "TNT":
                            hit_tnts.add((bx, by))
                            break
                        beam_cells.append((bx, by))
                    beams.append({
                        "cannon": (x, y),
                        "dir": dir_char,
                        "cells": beam_cells,
                    })
        return beams, hit_tnts

    def compute_visible_mask(self) -> List[List[bool]]:
        if self.mode == "FULL":
            return [[True] * GRID_W for _ in range(GRID_H)]
        mask = [[False] * GRID_W for _ in range(GRID_H)]
        # Scheme B: the same 37-cell disc, propagated near-to-far through LOS.
        def open_offset(dx: int, dy: int) -> bool:
            x, y = self.hx + dx, self.hy + dy
            return in_bounds(x, y) and mask[y][x] and not self.is_high_wall(x, y)

        for radius in range(4):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if max(abs(dx), abs(dy)) != radius or dx*dx + dy*dy > 10:
                        continue
                    x, y = self.hx + dx, self.hy + dy
                    if not in_bounds(x, y):
                        continue
                    sx, sy = (dx > 0) - (dx < 0), (dy > 0) - (dy < 0)
                    if radius <= 1:
                        visible = True
                    elif dx == 0 or dy == 0:
                        visible = open_offset(dx-sx, dy-sy)
                    elif abs(dx) == abs(dy):
                        visible = open_offset(sx, sy) and not (
                            self.is_high_wall(self.hx+sx, self.hy)
                            and self.is_high_wall(self.hx, self.hy+sy))
                    elif abs(dx) > abs(dy):
                        visible = open_offset(dx-sx, dy) or open_offset(dx-sx, dy-sy)
                    else:
                        visible = open_offset(dx, dy-sy) or open_offset(dx-sx, dy-sy)
                    mask[y][x] = visible

        # Ice-track extension from the 8 adjacent cells around hero
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                ax, ay = self.hx + dx, self.hy + dy
                if not in_bounds(ax, ay):
                    continue
                if self.terrain[ay][ax] == "ICE" or self.terrain[ay][ax] in MIRROR_TABLE:
                    # Trace cardinal slide directions if orthogonal, or all 4 if diagonal
                    cardinal_dirs = [(dx, dy)] if (dx == 0 or dy == 0) else list(DIR_VECTORS.values())
                    for cdir in cardinal_dirs:
                        cx, cy = ax, ay
                        cur_d = cdir
                        for _ in range(MAX_SUB_STEPS):
                            if not in_bounds(cx, cy):
                                break
                            mask[cy][cx] = True
                            ct = self.terrain[cy][cx]
                            if ct in MIRROR_TABLE:
                                cur_d = MIRROR_TABLE[ct][cur_d]
                            elif ct != "ICE":
                                break
                            cx += cur_d[0]
                            cy += cur_d[1]
        return mask

    def get_observation(self) -> Dict[str, Any]:
        """
        Builds the sanitized observation `state` dictionary passed to `decide_action(state, memory)`.
        """
        vis = self.compute_visible_mask()
        obs_terrain: List[List[str]] = [["UNKNOWN"] * GRID_W for _ in range(GRID_H)]
        obs_occupant: List[List[Optional[str]]] = [[None] * GRID_W for _ in range(GRID_H)]
        obs_clues: List[List[bool]] = [[False] * GRID_W for _ in range(GRID_H)]

        for y in range(GRID_H):
            for x in range(GRID_W):
                if vis[y][x]:
                    t = self.terrain[y][x]
                    if t in ("HEAL", "MIMIC"):
                        obs_terrain[y][x] = "CHEST"
                    else:
                        obs_terrain[y][x] = t
                    obs_occupant[y][x] = self.occupant[y][x]
                    obs_clues[y][x] = self.clues[y][x]

        obs_bombs = [
            {"x": b["x"], "y": b["y"], "timer": b["timer"]}
            for b in self.bombs
            if vis[b["y"]][b["x"]]
        ]

        laser_warnings: List[Dict[str, Any]] = []
        if self.turn % 3 == 0:
            beams, _ = self.compute_laser_snapshot()
            warning_tuples: Set[Tuple[int, int, str]] = set()
            for bm in beams:
                d_char = bm["dir"]
                for bx, by in bm["cells"]:
                    if vis[by][bx]:
                        warning_tuples.add((by, bx, d_char))
            for by, bx, d_char in sorted(warning_tuples):
                laser_warnings.append({"x": bx, "y": by, "dir": d_char})

        return {
            "turn": self.turn,
            "turns_left": MAX_TURNS - self.turn + 1,
            "mode": self.mode,
            "hero": {
                "x": self.hx,
                "y": self.hy,
                "hp": self.hp,
                "keys": [self.has_k1, self.has_k2],
                "jumps": self.jumps,
                "throws": self.throws,
                "bombs": self.bombs_left,
            },
            "gates_flipped": self.gates_flipped,
            "targets": copy.deepcopy(self.targets),
            "visible_mask": vis,
            "terrain": obs_terrain,
            "occupant": obs_occupant,
            "bombs": obs_bombs,
            "clues": obs_clues,
            "laser_warnings": laser_warnings,
        }

    def step(self, action: str) -> Dict[str, Any]:
        """
        Executes a single full turn (Phases A, B, C, D) for the given hero action.
        """
        if self.status != "ALIVE":
            return self.get_step_summary(action)

        self.last_executed_turn = self.turn
        self.exposed_cells = {(self.hx, self.hy)}
        self.tnt_armed = set()
        self.last_steps_taken = 0
        self.last_portal_count = 0
        self.last_phase_d_executed = False
        self.last_turn_events = []

        if not isinstance(action, str) or action not in VALID_ACTIONS:
            action = "WAIT"

        # ================= PHASE A & B: Action & Momentum =================
        if action == "WAIT":
            pass

        elif action == "BOMB":
            if self.bombs_left > 0 and not any(b["x"] == self.hx and b["y"] == self.hy for b in self.bombs):
                self.bombs_left -= 1
                self.bombs.append({
                    "id": self.next_bomb_id,
                    "x": self.hx,
                    "y": self.hy,
                    "timer": 3,
                })
                self.last_turn_events.append({"type": "BOMB_PLACED", "id": self.next_bomb_id, "x": self.hx, "y": self.hy})
                self.next_bomb_id += 1

        elif action.startswith("MOVE_"):
            d_key = action.split("_")[1]
            dx, dy = DIR_VECTORS[d_key]
            x1, y1 = self.hx + dx, self.hy + dy
            if in_bounds(x1, y1) and not self.is_high_wall(x1, y1) and self.occupant[y1][x1] != "TNT":
                if self.occupant[y1][x1] == "BOX":
                    x2, y2 = self.hx + 2 * dx, self.hy + 2 * dy
                    if self.is_enterable_for_entity(x2, y2, "BOX"):
                        box_tracker = {"steps_taken": 0, "portal_count": 0, "stop_momentum": False}
                        self._execute_atomic_displacement("BOX", (x1, y1), (x2, y2), (dx, dy), box_tracker)
                        if self.status == "ALIVE" and self.is_enterable_for_entity(x1, y1, "HERO"):
                            hero_tracker = {"steps_taken": 0, "portal_count": 0, "stop_momentum": False}
                            self._execute_atomic_displacement("HERO", (self.hx, self.hy), (x1, y1), (dx, dy), hero_tracker)
                else:
                    hero_tracker = {"steps_taken": 0, "portal_count": 0, "stop_momentum": False}
                    self._execute_atomic_displacement("HERO", (self.hx, self.hy), (x1, y1), (dx, dy), hero_tracker)

        elif action.startswith("JUMP_"):
            if self.jumps > 0:
                self.jumps -= 1
                d_key = action.split("_")[1]
                dx, dy = DIR_VECTORS[d_key]
                x1, y1 = self.hx + dx, self.hy + dy
                x2, y2 = self.hx + 2 * dx, self.hy + 2 * dy
                if (
                    in_bounds(x1, y1)
                    and in_bounds(x2, y2)
                    and not self.is_high_wall(x1, y1)
                    and self.is_enterable_for_entity(x2, y2, "HERO")
                ):
                    hero_tracker = {"steps_taken": 0, "portal_count": 0, "stop_momentum": False}
                    self._execute_atomic_displacement("HERO", (self.hx, self.hy), (x2, y2), (dx, dy), hero_tracker)

        elif action.startswith("THROW_"):
            d_key = action.split("_")[1]
            dx, dy = DIR_VECTORS[d_key]
            self._execute_throw((dx, dy))

        # Check immediate termination after Phase B (death or vault cleared)
        if self.status in ("DEAD", "CLEARED"):
            return self.get_step_summary(action)

        # ================= PHASE C: Bomb Countdown & Chain Explosion =================
        for b in self.bombs:
            b["timer"] -= 1

        initial_bomb_ids = {b["id"] for b in self.bombs if b["timer"] <= 0}
        initial_tnts = set(self.tnt_armed)
        self.tnt_armed.clear()

        if initial_bomb_ids or initial_tnts:
            self._resolve_explosion_closure(initial_bomb_ids, initial_tnts)

        if self.status in ("DEAD", "CLEARED"):
            return self.get_step_summary(action)

        # ================= PHASE D: Simultaneous Laser Snapshot (turn % 3 == 0) =================
        if self.turn % 3 == 0:
            self.last_phase_d_executed = True
            beams, laser_hit_tnts = self.compute_laser_snapshot()
            self.last_laser_Warning_beams = beams

            # Count how many active laser cannons intersect with hero's exposed_cells
            hit_count = 0
            for bm in beams:
                if any(cell in self.exposed_cells for cell in bm["cells"]):
                    hit_count += 1

            self.last_turn_events.append({
                "type": "LASER_FIRE",
                "beams": [
                    {"cannon": list(bm["cannon"]), "dir": bm["dir"], "cells": [list(c) for c in bm["cells"]]}
                    for bm in beams
                ],
                "hero_hits": hit_count,
            })

            if hit_count > 0:
                self._apply_damage_batch(50 * hit_count, 0, source="LASER")
                if self.status == "DEAD":
                    return self.get_step_summary(action)

            # Settle TNT chain explosions triggered by lasers WITHOUT decrementing bomb timers
            if laser_hit_tnts:
                self._resolve_explosion_closure(set(), laser_hit_tnts)
                if self.status == "DEAD":
                    return self.get_step_summary(action)

        # End of turn advancement / timeout check
        if self.turn >= MAX_TURNS and self.status == "ALIVE":
            self.status = "TIMEOUT"
        else:
            self.turn += 1

        return self.get_step_summary(action)

    def get_step_summary(self, action: str) -> Dict[str, Any]:
        return {
            "turn": self.last_executed_turn if self.last_executed_turn > 0 else self.turn,
            "action": action,
            "status": self.status,
            "hero_pos": [self.hx, self.hy],
            "hero_hp": self.hp,
            "keys": [self.has_k1, self.has_k2],
            "jumps": self.jumps,
            "throws": self.throws,
            "bombs_left": self.bombs_left,
            "gates_flipped": self.gates_flipped,
            "trap_damage_total": round(self.trap_damage_total, 4),
            "steps_taken": self.last_steps_taken,
            "portal_count": self.last_portal_count,
            "phase_d_executed": self.last_phase_d_executed,
            "exposed_cells": [list(c) for c in sorted(self.exposed_cells)],
            "events": self.last_turn_events,
        }

    def compute_scores(self, turns_elapsed: int) -> Dict[str, float]:
        """
        Computes final Hero and Demon scores according to Section IV of RULES.md.
        """
        g = float(MAX_BUDGET - self.spent_gold) / float(MAX_BUDGET)
        d_eff = min(100.0, self.trap_damage_total)
        k = (1 if self.has_k1 else 0) + (1 if self.has_k2 else 0)
        denom = max(1, self.stage_d0)
        progress_ratio = max(0.0, float(self.stage_d0 - self.stage_dmin) / float(denom))
        p_total = float(k) + progress_ratio

        if self.status == "CLEARED":
            t_clamped = max(1, min(MAX_TURNS, turns_elapsed))
            hero_score = 600.0 + 1.5 * float(self.hp) + 150.0 * float(MAX_TURNS - t_clamped) / 239.0 + 100.0 * g
            demon_score = 2.0 * d_eff + 120.0 * float(t_clamped - 1) / 239.0
        else:
            hero_score = 200.0 * float(k) + 200.0 * progress_ratio
            if self.status == "DEAD":
                demon_score = 500.0 + 50.0 * (3.0 - p_total) + d_eff + 250.0 * g
            else:
                # TIMEOUT
                demon_score = 320.0 + 50.0 * (3.0 - p_total) + d_eff + 125.0 * g

        return {
            "hero_score": round(hero_score, 4),
            "demon_score": round(demon_score, 4),
            "vault_ratio_g": round(g, 4),
            "effective_trap_damage": round(d_eff, 4),
            "keys_collected": k,
        }


def verify_author_solution(grid: List[List[str]], author_solution: List[str]) -> Dict[str, Any]:
    """
    Validates the dungeon grid AND verifies that `author_solution` is a non-empty list
    of 1..240 valid actions that achieves `"CLEARED"` status on the exact last action.
    """
    dec = validate_and_decode_dungeon(grid)
    if not dec["valid"]:
        return {"valid": False, "reason": f"Grid invalid: {dec['reason']}"}

    if not isinstance(author_solution, list) or not (1 <= len(author_solution) <= MAX_TURNS):
        return {"valid": False, "reason": "author_solution must be a list of 1..240 actions."}

    sim = DungeonSimulator(dec, mode="FULL")
    for idx, act in enumerate(author_solution):
        if not isinstance(act, str) or act not in VALID_ACTIONS:
            return {"valid": False, "reason": f"Invalid action '{act}' at index {idx}."}
        sim.step(act)
        if sim.status == "DEAD":
            return {"valid": False, "reason": f"Author died on step {idx + 1} ({act})."}
        if sim.status == "CLEARED" and idx != len(author_solution) - 1:
            return {
                "valid": False,
                "reason": f"Author cleared early at step {idx + 1}/{len(author_solution)} (trailing padding forbidden).",
            }

    if sim.status != "CLEARED":
        return {"valid": False, "reason": f"Author failed to clear vault after {len(author_solution)} steps (status={sim.status})."}

    scores = sim.compute_scores(turns_elapsed=len(author_solution))
    return {
        "valid": True,
        "reason": "OK",
        "spent_gold": dec["spent_gold"],
        "vault_gold": dec["vault_gold"],
        "author_steps": len(author_solution),
        "author_hp_left": sim.hp,
        "scores_if_author_run": scores,
        "decoded": dec,
    }
