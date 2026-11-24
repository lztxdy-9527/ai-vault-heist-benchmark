"""FULL v2.2 strong reference entrant. Standalone, standard-library only."""

from collections import deque
from heapq import heappop, heappush
from time import perf_counter


WIDTH, HEIGHT = 40, 26
SIZE = WIDTH * HEIGHT
MAX_TURNS = 240
DIRS = "UDLR"
VECTORS = ((0, -1), (0, 1), (-1, 0), (1, 0))
OPPOSITE = (1, 0, 3, 2)
ACTIONS = (
    tuple("MOVE_" + d for d in DIRS)
    + tuple("JUMP_" + d for d in DIRS)
    + ("WAIT", "BOMB")
    + tuple("THROW_" + d for d in DIRS)
)
WAIT, BOMB = 8, 9
CELL = tuple(1 << p for p in range(SIZE))


def _adjacent(p):
    x, y = p % WIDTH, p // WIDTH
    return tuple(
        (y + dy) * WIDTH + x + dx
        if 0 <= x + dx < WIDTH and 0 <= y + dy < HEIGHT else -1
        for dx, dy in VECTORS
    )


ADJ = tuple(_adjacent(p) for p in range(SIZE))
BLAST = tuple(
    sum(
        CELL[y * WIDTH + x]
        for y in range(max(0, p // WIDTH - 1), min(HEIGHT, p // WIDTH + 2))
        for x in range(max(0, p % WIDTH - 1), min(WIDTH, p % WIDTH + 2))
    )
    for p in range(SIZE)
)

(FLOOR, WALL, TITANIUM, PIT, CRACK, ICE, SWITCH, RED, BLUE, PLATE, PRESS_GATE,
 HEAL, MIMIC, KEY1, KEY2, VAULT) = range(16)
MIRRORS = {
    16: (3, 3, 0, 0),  # NE, indexed by incoming U/D/L/R
    17: (3, 3, 1, 1),
    18: (2, 2, 1, 1),
    19: (2, 2, 0, 0),
}
SPRING = 20
ONEWAY = 24
PORTAL = 28
CANNON = 32
SYMBOL = {
    name: i for i, name in enumerate((
        "EMPTY", "W", "T_W", "PIT", "CRACK", "ICE", "SWITCH", "R_GATE", "B_GATE",
        "PLATE", "P_GATE", "HEAL", "MIMIC", "K1", "K2", "V",
        "MIRROR_NE", "MIRROR_SE", "MIRROR_SW", "MIRROR_NW",
        "SPRING_U", "SPRING_D", "SPRING_L", "SPRING_R",
        "ONEWAY_U", "ONEWAY_D", "ONEWAY_L", "ONEWAY_R",
        "PORTAL_1A", "PORTAL_1B", "PORTAL_2A", "PORTAL_2B",
        "LASER_U", "LASER_D", "LASER_L", "LASER_R",
        "LASER2_U", "LASER2_D", "LASER2_L", "LASER2_R",
    ))
}
BREAKABLE = frozenset(
    (WALL, ICE, SWITCH, RED, BLUE, HEAL, MIMIC)
    + tuple(range(16, ONEWAY)) + tuple(range(CANNON, CANNON + 8))
)
STOPS_BOX = (KEY1, KEY2, VAULT)
INF = 4096.0

# Compact search position. Phase is passed separately. Terrain changes use two
# bitsets relative to the observed board. TNT locations never move.
POS, HP, KEYS, JUMPS, STONES, CHARGES, FLIP, BOXES, BARRELS, GONE, CRACKED, FUSES = range(12)


def _positions(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1
        mask ^= bit


def _dist(p, q):
    return abs(p % WIDTH - q % WIDTH) + abs(p // WIDTH - q // WIDTH)


class Board:
    def __init__(self, terrain, targets):
        self.tiles = terrain
        self.targets = targets
        masks = [0] * len(SYMBOL)
        for p, tile in enumerate(terrain):
            masks[tile] |= CELL[p]
        self.plates = masks[PLATE]
        self.pits = masks[PIT]
        self.press_gates = masks[PRESS_GATE]
        self.color_gates = (masks[RED], masks[BLUE])
        self.cracks = masks[CRACK]
        self.fragile = sum(masks[t] for t in BREAKABLE)
        self.interesting = self.fragile & ~masks[HEAL]
        self.fixtures = masks[SWITCH] | masks[MIMIC]
        self.solids = masks[TITANIUM] | masks[WALL] | sum(masks[CANNON:])
        self.wrong_way = tuple(
            sum(masks[ONEWAY + other] for other in range(4) if other != direction)
            for direction in range(4)
        )
        portal_at = {tile: p for p, tile in enumerate(terrain) if PORTAL <= tile < CANNON}
        self.portals = {p: portal_at[tile ^ 1] for tile, p in portal_at.items() if tile ^ 1 in portal_at}
        self.rays = []
        self.ray_area = 0
        for p in _positions(sum(masks[CANNON:])):
            tile = terrain[p] - CANNON
            direction = tile % 4
            ray = []
            q = p
            for _ in range(10):
                q = ADJ[q][direction]
                if q < 0 or terrain[q] == TITANIUM:
                    break
                ray.append(CELL[q])
                self.ray_area |= CELL[q]
            self.rays.append((CELL[p], 3 + tile // 4, tuple(ray)))
        self.ray_cache = {}

    def walls(self, flipped, boxes, gone):
        mask = self.solids | self.color_gates[flipped]
        if not self.plates or boxes & self.plates != self.plates:
            mask |= self.press_gates
        return mask & ~gone

    def beams(self, phase, walls, boxes, barrels, gone):
        firing = (phase % 3 == 0, phase % 4 == 0)
        key = (firing, walls, boxes, barrels)
        cache = self.ray_cache
        cached = cache.get(key)
        if cached is not None:
            return cached
        stop = walls | boxes
        beams, ignited = [], 0
        for cannon, period, ray in self.rays:
            if not firing[period - 3] or cannon & gone:
                continue
            beam = 0
            for bit in ray:
                if bit & stop:
                    break
                if bit & barrels:
                    ignited |= bit
                    break
                beam |= bit
            if beam:
                beams.append(beam)
        result = (tuple(beams), ignited)
        if len(cache) < 1800:
            cache[key] = result
        return result


def _observe(observation):
    terrain = tuple(t for row in observation["terrain"] for t in row)
    clues = tuple(flag for row in observation["clues"] for flag in row)
    tiles = tuple(
        (MIMIC if any(q >= 0 and clues[q] for q in ADJ[p]) else HEAL)
        if tile == "CHEST" else SYMBOL[tile]
        for p, tile in enumerate(terrain)
    )
    boxes = barrels = 0
    for y, row in enumerate(observation["occupant"]):
        for x, tile in enumerate(row):
            if tile == "BOX":
                boxes |= CELL[y * WIDTH + x]
            elif tile == "TNT":
                barrels |= CELL[y * WIDTH + x]
    hero = observation["hero"]
    fuses = tuple(sorted(
        (b["y"] * WIDTH + b["x"], b["timer"]) for b in observation["bombs"]
    ))
    start = (
        hero["y"] * WIDTH + hero["x"], hero["hp"], int(hero["keys"][0]) + 2 * int(hero["keys"][1]),
        hero["jumps"], hero["throws"], hero["bombs"], int(observation["gates_flipped"]),
        boxes, barrels, 0, 0, fuses,
    )
    return tiles, start


def _tile(tiles, p, gone, cracked):
    bit = CELL[p]
    if bit & gone:
        return FLOOR
    if bit & cracked:
        return PIT
    return tiles[p]


def _blocked(p, mask):
    return p < 0 or bool(CELL[p] & mask)


def _motion(board, state, origin, landing, direction, moving_box):
    pos, hp, keys, jumps, stones, charges, flipped, boxes, barrels, gone, cracked, fuses = state
    tiles, wrong_way = board.tiles, board.wrong_way
    trail = CELL[pos]
    armed = teleports = 0
    after_portal = False
    for step in range(32):
        old, bit = CELL[origin], CELL[landing]
        cracked |= old & board.cracks & ~gone
        if moving_box:
            boxes = (boxes ^ old) | bit
        else:
            pos = landing
            trail |= bit
        kind = _tile(tiles, landing, gone, cracked)
        if kind == PIT:
            if not moving_box:
                return None, trail, armed, False
            boxes ^= bit
            gone |= bit
            cracked &= ~bit
            break
        if kind == SWITCH:
            flipped ^= 1
        elif kind == MIMIC:
            gone |= bit
            if not moving_box:
                hp -= 45
                if hp <= 0:
                    return None, trail, armed, False
            break
        elif not moving_box:
            if kind == HEAL:
                hp = min(100, hp + 30)
                gone |= bit
            elif kind in (KEY1, KEY2):
                keys |= 1 << (kind - KEY1)
                gone |= bit
            elif kind == VAULT and keys == 3:
                won = (pos, hp, keys, jumps, stones, charges, flipped, boxes, barrels, gone, cracked, fuses)
                return won, trail, armed, True

        if step == 31:
            break
        if after_portal and teleports == 2:
            break
        if not after_portal and kind < ICE:
            break
        if not after_portal and ICE < kind < 16:
            break
        mask = board.walls(flipped, boxes, gone) | boxes | barrels
        if moving_box:
            mask |= CELL[pos]
        if after_portal:
            after_portal = False
        elif 16 <= kind < SPRING:
            direction = MIRRORS[kind][direction]
        elif SPRING <= kind < ONEWAY:
            direction = kind - SPRING
            q = landing
            for _ in range(3):
                candidate = ADJ[q][direction]
                if _blocked(candidate, mask | wrong_way[direction]) or (
                    moving_box and _tile(tiles, candidate, gone, cracked) in STOPS_BOX
                ):
                    if moving_box and candidate >= 0:
                        armed |= CELL[candidate] & barrels
                    break
                q = candidate
            if q == landing:
                break
            origin, landing = landing, q
            continue
        elif PORTAL <= kind < CANNON:
            q = board.portals[landing]
            if _blocked(q, mask):
                break
            origin, landing = landing, q
            teleports += 1
            after_portal = True
            continue
        elif kind != ICE:
            break

        q = ADJ[landing][direction]
        if _blocked(q, mask | wrong_way[direction]) or (
            moving_box and _tile(tiles, q, gone, cracked) in STOPS_BOX
        ):
            break
        origin, landing = landing, q

    result = (pos, hp, keys, jumps, stones, charges, flipped, boxes, barrels, gone, cracked, fuses)
    return result, trail, armed, False


def _throw(board, state, direction, walls):
    """Return the first effect reachable by this throw, or no changed state."""
    p, tiles, boxes, barrels, gone = state[POS], board.tiles, state[BOXES], state[BARRELS], state[GONE]
    stop = walls | boxes
    teleports = 0
    for step in range(38):
        p = ADJ[p][direction]
        if _blocked(p, stop):
            break
        bit = CELL[p]
        if bit & barrels:
            return state[FLIP], gone, bit
        kind = FLOOR if bit & gone else tiles[p]
        if kind == SWITCH:
            return state[FLIP] ^ 1, gone, 0
        if kind == MIMIC:
            return state[FLIP], gone | bit, 0
        if kind in MIRRORS:
            direction = MIRRORS[kind][direction]
        elif PORTAL <= kind < CANNON:
            q = board.portals[p]
            if not _blocked(q, stop | barrels):
                teleports += 1
                if teleports == 2 or step == 5:
                    break
                p = q
                continue
        if step >= 5 and kind != ICE and kind not in MIRRORS:
            break
    return None


def _explode(board, state, armed, due):
    pos, hp, keys, jumps, stones, charges, flipped, boxes, barrels, gone, cracked, fuses = state
    area = BLAST[pos]
    blast = 0
    live = barrels
    pending = armed
    survivors = list(fuses)
    damage = 0
    while pending or due:
        for p in _positions(pending):
            blast |= BLAST[p]
            if CELL[p] & area:
                damage += 60
        live &= ~pending
        for p, _ in due:
            blast |= BLAST[p]
            if CELL[p] & area:
                damage += 50
            survivors = [fuse for fuse in survivors if fuse[0] != p]
        pending = live & blast
        due = [fuse for fuse in survivors if CELL[fuse[0]] & blast]
    hp -= damage
    gone |= board.fragile & blast
    cracked = (cracked | (board.cracks & blast)) & ~gone
    if hp <= 0 or _tile(board.tiles, pos, gone, cracked) == PIT:
        return None
    return (pos, hp, keys, jumps, stones, charges, flipped,
            boxes & ~blast, live, gone, cracked, tuple(survivors))


def _advance(board, state, action, phase):
    """Predict A/B/C/D. A redundant action or a dead hero gives no useful successor."""
    pos, hp, keys, jumps, stones, charges, flipped, boxes, barrels, gone, cracked, fuses = state
    walls = board.walls(flipped, boxes, gone)
    trail, armed = CELL[pos], 0
    if action < 8:
        direction = action % 4
        wrong = board.wrong_way[direction]
        next_cell = ADJ[pos][direction]
        if _blocked(next_cell, walls | wrong):
            return None, False
        if action >= 4:
            landing = ADJ[next_cell][direction]
            if not jumps or _blocked(landing, walls | wrong | boxes | barrels):
                return None, False
            state = state[:JUMPS] + (jumps - 1,) + state[STONES:]
        elif CELL[next_cell] & boxes:
            box_dst = ADJ[next_cell][direction]
            if _blocked(box_dst, walls | wrong | boxes | barrels | CELL[pos]) or (
                _tile(board.tiles, box_dst, gone, cracked) in STOPS_BOX
            ):
                return None, False
            state, _, armed, _ = _motion(board, state, next_cell, box_dst, direction, True)
            walls = board.walls(state[FLIP], state[BOXES], state[GONE])
            landing = next_cell
            if _blocked(landing, walls | wrong | state[BOXES] | barrels):
                landing = -1
        else:
            if CELL[next_cell] & barrels:
                return None, False
            landing = next_cell
        if landing >= 0:
            state, trail, bump, win = _motion(board, state, pos, landing, direction, False)
            if state is None or win:
                return state, win
            armed |= bump
    elif action == BOMB:
        if not charges or any(p == pos for p, _ in fuses):
            return None, False
        fuses = tuple(sorted(fuses + ((pos, 3),)))
        state = state[:CHARGES] + (charges - 1,) + state[FLIP:FUSES] + (fuses,)
    elif action > BOMB:
        hit = _throw(board, state, action - 10, walls) if stones else None
        if hit is None:
            return None, False
        flipped, gone, armed = hit
        state = (pos, hp, keys, jumps, stones - 1, charges, flipped, boxes, barrels, gone, cracked, fuses)

    fuses = state[FUSES]
    if fuses:
        fuses = tuple((p, timer - 1) for p, timer in fuses)
        state = state[:FUSES] + (fuses,)
    if armed or any(timer == 0 for _, timer in fuses):
        state = _explode(board, state, armed, [item for item in fuses if item[1] == 0])
        if state is None:
            return None, False
    if board.rays and (phase % 3 == 0 or phase % 4 == 0):
        walls = board.walls(state[FLIP], state[BOXES], state[GONE])
        beams, armed = board.beams(phase, walls, state[BOXES], state[BARRELS], state[GONE])
        hp = state[HP] - 50 * sum(bool(beam & trail) for beam in beams)
        if hp <= 0:
            return None, False
        if hp != state[HP]:
            state = (state[POS], hp) + state[KEYS:]
        if armed:
            state = _explode(board, state, armed, [])
    return state, False


def _actions(board, state, reserve_jump=True):
    result = [0, 1, 2, 3]
    if state[JUMPS]:
        # A jump saved on open ground is worth little compared with a jump
        # kept for a moat or for the only safe beat in a beam corridor.
        pos = state[POS]
        last_for_moat = (
            reserve_jump and state[JUMPS] == 1
            and bool((board.pits | state[CRACKED]) & ~state[GONE])
        )
        for direction, p in enumerate(ADJ[pos]):
            if p < 0:
                continue
            target = ADJ[p][direction]
            kind = _tile(board.tiles, p, state[GONE], state[CRACKED])
            if last_for_moat and kind != PIT:
                continue
            if target >= 0 and (
                (CELL[p] & (state[BOXES] | state[BARRELS]))
                or kind in (PIT, CRACK, ICE, SWITCH, MIMIC)
                or 16 <= kind < CANNON
                or board.ray_area & (CELL[pos] | CELL[p] | CELL[target])
            ):
                result.append(4 + direction)
    if board.rays or state[FUSES]:
        result.append(WAIT)
    if state[CHARGES] and (BLAST[state[POS]] & (
        (board.interesting & ~state[GONE]) | state[BOXES] | state[BARRELS]
    )):
        result.append(BOMB)
    if state[STONES] and ((board.fixtures & ~state[GONE]) | state[BARRELS]):
        result.extend((10, 11, 12, 13))
    return result


def _reverse_travel(board, start, pass_press_gate):
    """Relaxed directed travel graph used only to order exact search states."""
    reverse = [[] for _ in range(SIZE)]
    tiles, portals = board.tiles, board.portals
    for p, kind in enumerate(tiles):
        if kind == TITANIUM or (kind == PRESS_GATE and not pass_press_gate):
            continue
        for direction, q in enumerate(ADJ[p]):
            if q < 0:
                continue
            dest = tiles[q]
            if dest == TITANIUM or (dest == PRESS_GATE and not pass_press_gate):
                continue
            if ONEWAY <= dest < PORTAL and dest != ONEWAY + direction:
                continue
            if dest == WALL or dest >= CANNON:
                reverse[q].append((p, 5.0 if start[CHARGES] else 22.0))
                continue
            if dest == PIT:
                weight = 8.0
            elif dest == (BLUE if start[FLIP] else RED):
                weight = 3.8
            elif kind == ICE or kind in MIRRORS:
                weight = 0.21
            else:
                weight = 1.0
            if CELL[q] & start[BARRELS]:
                weight += 2.2
            reverse[q].append((p, weight))
            landing = ADJ[q][direction]
            if start[JUMPS] and landing >= 0:
                lt = tiles[landing]
                if (lt not in (TITANIUM, WALL, PIT) and lt < CANNON
                    and (lt != PRESS_GATE or pass_press_gate)
                    and (not ONEWAY <= lt < PORTAL or lt == ONEWAY + direction)):
                    reverse[landing].append((p, 1.75))
        if p in portals:
            reverse[portals[p]].append((p, 0.15))
        if SPRING <= kind < ONEWAY:
            direction = kind - SPRING
            q = p
            for _ in range(3):
                landing = ADJ[q][direction]
                if landing < 0:
                    break
                lt = tiles[landing]
                if (lt in (TITANIUM, WALL) or lt >= CANNON
                    or (lt == PRESS_GATE and not pass_press_gate)
                    or (ONEWAY <= lt < PORTAL and lt != ONEWAY + direction)):
                    break
                q = landing
            if q != p:
                reverse[q].append((p, 0.15))
    return reverse


def _distances(reverse, goals):
    distances = [INF] * SIZE
    queue = []
    for goal in goals:
        distances[goal] = 0.0
        heappush(queue, (0.0, goal))
    while queue:
        score, p = heappop(queue)
        if score != distances[p]:
            continue
        for q, weight in reverse[p]:
            next_score = score + weight
            if next_score < distances[q]:
                distances[q] = next_score
                heappush(queue, (next_score, q))
    return distances


def _crate_destination(board, hero, landing, direction, fixed_walls):
    """Relax a push by considering one crate, with no other movable blockers."""
    teleports = 0
    after_portal = False
    tiles = board.tiles
    mask = fixed_walls | CELL[hero]
    for _ in range(31):
        kind = tiles[landing]
        if kind == PIT:
            return -1
        if after_portal:
            if teleports >= 2:
                break
            after_portal = False
        elif kind in MIRRORS:
            direction = MIRRORS[kind][direction]
        elif SPRING <= kind < ONEWAY:
            direction = kind - SPRING
            q = landing
            for _ in range(3):
                candidate = ADJ[q][direction]
                if _blocked(candidate, mask | board.wrong_way[direction]):
                    break
                q = candidate
            if q == landing:
                break
            landing = q
            continue
        elif PORTAL <= kind < CANNON:
            q = board.portals[landing]
            if _blocked(q, mask):
                break
            landing = q
            teleports += 1
            after_portal = True
            continue
        elif kind != ICE:
            break
        q = ADJ[landing][direction]
        if _blocked(q, mask | board.wrong_way[direction]):
            break
        landing = q
    return landing if tiles[landing] != PIT else -1


class PlateGuide:
    def __init__(self, board):
        self.plates = tuple(_positions(board.plates))
        self.pushes = [[] for _ in range(SIZE)]
        reverse = [[] for _ in range(SIZE)]
        tiles = board.tiles
        walls = board.solids | board.press_gates | sum(
            CELL[p] for p, kind in enumerate(tiles) if kind in STOPS_BOX
        )
        for p, kind in enumerate(tiles):
            if CELL[p] & walls or kind == PIT:
                continue
            for direction, q in enumerate(ADJ[p]):
                stand = ADJ[p][OPPOSITE[direction]]
                wrong = board.wrong_way[direction]
                if (stand < 0 or tiles[stand] == PIT or _blocked(stand, board.solids | board.press_gates)
                    or _blocked(p, wrong) or _blocked(q, walls | wrong)):
                    continue
                landing = _crate_destination(board, stand, q, direction, walls)
                if landing >= 0 and landing != p:
                    reverse[landing].append(p)
                    self.pushes[p].append((landing, stand))
        self.distances = []
        for p in self.plates:
            depths = [90] * SIZE
            depths[p] = 0
            queue = deque([p])
            while queue:
                q = queue.popleft()
                for prev in reverse[q]:
                    if depths[prev] == 90:
                        depths[prev] = 1 + depths[q]
                        queue.append(prev)
            self.distances.append(depths)
        self.cache = {}

    def _assignment(self, crates):
        # Exact minimum cost matching on the relaxed push graph. An off-plate
        # decoy cannot be reused for two plates in this estimate.
        scores = {0: 0}
        for depths in self.distances:
            next_scores = {}
            for taken, cost in scores.items():
                for i, box in enumerate(crates):
                    bit = 1 << i
                    if taken & bit:
                        continue
                    key = taken | bit
                    candidate = cost + depths[box]
                    if candidate < next_scores.get(key, 900):
                        next_scores[key] = candidate
            scores = next_scores
        return min(scores.values(), default=900)

    def _config(self, mask):
        crates = tuple(_positions(mask))
        if len(crates) < len(self.plates):
            return (1400.0, ())
        cost = self._assignment(crates)
        stands = set()
        fallback = set()
        for p in crates:
            for q, stand in self.pushes[p]:
                if any(depths[q] < depths[p] for depths in self.distances):
                    fallback.add(stand)
                    if self._assignment(tuple(q if b == p else b for b in crates)) < cost:
                        stands.add(stand)
        if not (stands or fallback):
            fallback.update(q for p in crates for q in ADJ[p] if q >= 0)
        return cost * 3.25, tuple(sorted(stands or fallback))

    def configuration(self, mask):
        config = self.cache.get(mask)
        if config is None:
            config = self._config(mask)
            if len(self.cache) < 1600:
                self.cache[mask] = config
        return config

    def estimate(self, state):
        config = self.configuration(state[BOXES])
        cost, stands = config
        return cost + min((_dist(state[POS], p) for p in stands), default=0)


def _tour_estimate(distances, targets, state):
    a, b, vault = distances
    k1, k2, _ = targets
    p = state[POS]
    keys = state[KEYS]
    if keys == 0:
        return min(a[p] + b[k1] + vault[k2], b[p] + a[k2] + vault[k1])
    if keys == 1:
        return b[p] + vault[k2]
    if keys == 2:
        return a[p] + vault[k1]
    return vault[p]


def _objective(board, start):
    activated = bool(board.plates and start[BOXES] & board.plates == board.plates)
    can_unlock = bool(board.press_gates and board.plates and start[BOXES].bit_count() >= board.plates.bit_count())
    targets = board.targets
    reverse = _reverse_travel(board, start, activated)
    distances = tuple(_distances(reverse, (goal,)) for goal in targets)
    if can_unlock and not activated and _tour_estimate(distances, targets, start) >= INF:
        guide = PlateGuide(board)
        # Pick up a key first if doing so stays on the way to a useful push.
        # Without this test a plate beside the vault can cause a round trip
        # across the map before either key is collected.
        _, stands = guide.configuration(start[BOXES])
        approach = _distances(reverse, stands)
        candidates = [
            i for i in range(2)
            if not (start[KEYS] & (1 << i))
            and (distances[i][start[POS]] + approach[targets[i]]
                 <= min(INF - 1.0, approach[start[POS]] + 10.0))
        ]
        if candidates:
            index = min(candidates, key=lambda i: distances[i][start[POS]] + approach[targets[i]])
            checkpoint = 1 << index
            return (
                lambda state: distances[index][state[POS]],
                lambda state: bool(state[KEYS] & checkpoint),
            )
        if guide.estimate(start) < 1100.0:
            plate_mask = board.plates
            pressed = (start[BOXES] & plate_mask).bit_count()

            def plate_goal(state):
                count = (state[BOXES] & plate_mask).bit_count()
                # Commit useful plate placements in segments, retaining the
                # global matching estimate for all unplaced crates.
                return count > pressed and guide.configuration(state[BOXES])[0] < 280

            return guide.estimate, plate_goal
    if _tour_estimate(distances, targets, start) >= INF and start[KEYS] != 3:
        candidates = [i for i in range(2) if not (start[KEYS] & (1 << i))]
        index = min(candidates, key=lambda i: distances[i][start[POS]])
        checkpoint = 1 << index

        def key_distance(state):
            return 0.0 if state[KEYS] & checkpoint else distances[index][state[POS]]

        def key_goal(state):
            return bool(state[KEYS] & checkpoint)

        return key_distance, key_goal

    def tour_distance(state):
        return _tour_estimate(distances, targets, state)

    def no_checkpoint(state):
        return False

    return tour_distance, no_checkpoint


def _terrain_matches(base_tiles, actual_tiles, expected):
    gone, cracked = expected[GONE], expected[CRACKED]
    if not (gone or cracked):
        return actual_tiles == base_tiles
    return all(
        actual_tiles[p] == _tile(base_tiles, p, gone, cracked)
        for p in range(SIZE)
    )


def _visit_key(state):
    return state[POS], state[KEYS], state[FLIP], state[BOXES], state[BARRELS]


def _route(board, initial, turn, remaining, visits, deadline):
    estimate, checkpoint = _objective(board, initial)
    has_rays = bool(board.rays)
    initial_phase = turn % 12 if has_rays else 1
    initial_h = estimate(initial)
    states = [(initial, -1, WAIT)]
    queue = [(0.0, 0, 0, 0.0)]
    best_cost = {(initial, initial_phase): 0.0}
    best_partial = None
    best_end = None
    best_score = float("inf")
    expanded = 0
    while queue and expanded < 12500 and perf_counter() < deadline:
        _, index, depth, path_cost = heappop(queue)
        state = states[index][0]
        phase = (turn + depth) % 12 if has_rays else 1
        if path_cost > best_cost.get((state, phase), float("inf")):
            continue
        if depth and checkpoint(state):
            best_end = index
            break
        if depth >= remaining:
            continue
        next_phase = (phase + 1) % 12 if has_rays else 1
        expanded += 1
        for action in _actions(board, state):
            child, win = _advance(board, state, action, phase)
            if child is None:
                continue
            elapsed = depth + 1
            # This is the clear-score tradeoff in units of turns.
            actual_cost = elapsed + 2.39 * (100 - child[HP])
            if win:
                if actual_cost < best_score:
                    best_score = actual_cost
                    best_end = len(states)
                    states.append((child, index, action))
                if child[HP] == 100:
                    queue.clear()
                    break
                continue
            if best_end is not None and elapsed >= best_score:
                continue
            # Small conservation costs only affect search order.
            cost = (elapsed + 2.39 * (100 - child[HP])
                    + 1.4 * (initial[JUMPS] - child[JUMPS])
                    + 0.38 * (initial[STONES] - child[STONES])
                    + 1.2 * (initial[CHARGES] - child[CHARGES]))
            signature = (child, next_phase)
            if cost >= best_cost.get(signature, float("inf")):
                continue
            best_cost[signature] = cost
            h = 0.0 if checkpoint(child) else estimate(child)
            visit = min(8, visits.get(_visit_key(child), 0))
            bias = 1.7 * visit if elapsed < 10 else 0.0
            if h >= INF:
                # Sealed terrain can still change under a blast or a box.
                h = min(h, INF + 15) + 0.25 * min(_dist(child[POS], q) for q in board.targets)
            if board.plates and initial[BOXES] & board.plates == board.plates:
                if child[BOXES] & board.plates != board.plates:
                    bias += 9.0
            priority = cost + 1.85 * h + bias
            node = len(states)
            states.append((child, index, action))
            heappush(queue, (priority, node, elapsed, cost))
            merit = h + 0.42 * cost + 2.7 * visit
            if child[FUSES]:
                merit += 9.0
            if child[POS] == initial[POS] and child[KEYS] == initial[KEYS] and child[BOXES] == initial[BOXES]:
                merit += 3.0 if h >= initial_h else 0.0
            merit -= 4.0 * (child[KEYS].bit_count() - initial[KEYS].bit_count())
            if best_partial is None or merit < best_partial[0]:
                best_partial = (merit, node)
        if best_end is not None and (not queue or expanded >= 4500):
            break
    index = best_end if best_end is not None else (best_partial[1] if best_partial else 0)
    path = []
    while index:
        child, parent, action = states[index]
        path.append((states[parent][0], action))
        index = parent
    path.reverse()
    return path if best_end is not None else path[:4]


def decide_action(state: dict, memory: dict) -> str:
    """Search complete turn states, and reuse a route only as long as it still matches."""
    turn = state["turn"]
    deadline = perf_counter() + (1.42 if turn == 1 else 0.30)
    tiles, initial = _observe(state)
    if turn == 1:
        memory.clear()
    visits = memory.setdefault("visits", {})
    key = _visit_key(initial)
    visits[key] = visits.get(key, 0) + 1
    cached = memory.get("route")
    if cached is not None:
        first_turn, base_tiles, path = cached
        index = turn - first_turn
        if 0 <= index < len(path):
            expected, action = path[index]
            if (initial[:GONE] == expected[:GONE] and initial[FUSES] == expected[FUSES]
                and _terrain_matches(base_tiles, tiles, expected)):
                return ACTIONS[action]
    targets = tuple(state["targets"][k][1] * WIDTH + state["targets"][k][0] for k in ("K1", "K2", "V"))
    board = Board(tiles, targets)
    plan = _route(board, initial, turn, state["turns_left"], visits, deadline)
    if plan:
        memory["route"] = (turn, tiles, plan)
        return ACTIONS[plan[0][1]]
    # Choose a surviving action even if the search budget expired before finding a route.
    options = []
    phase = turn % 12
    for action in _actions(board, initial, reserve_jump=False):
        child, win = _advance(board, initial, action, phase)
        if win:
            return ACTIONS[action]
        if child is not None:
            options.append((-child[HP], visits.get(_visit_key(child), 0), action))
    return ACTIONS[min(options)[2]] if options else "WAIT"


def build_dungeon() -> dict:
    """Three separated workshops, followed by a one-way bridge to the vault."""
    grid = [
        ["T_W" if x in (0, 39) or y in (0, 25) else "EMPTY" for x in range(WIDTH)]
        for y in range(HEIGHT)
    ]
    for y in range(1, 25):
        grid[y][11] = "T_W"
        grid[y][26] = "T_W"
    for x, y in (
        (7, 5), (6, 6), (8, 6), (6, 7), (8, 7),
        (7, 18), (9, 18), (8, 19),
        (7, 22), (9, 22), (8, 23),
        (20, 5), (19, 6), (21, 6),
        (35, 12), (36, 12), (35, 14), (36, 14), (37, 13),
    ):
        grid[y][x] = "T_W"
    placements = (
        (3, 9, "BOX"), (7, 6, "PLATE"), (7, 7, "ONEWAY_U"),
        (4, 17, "BOX"), (8, 18, "PLATE"), (8, 17, "MIRROR_SE"),
        (4, 21, "BOX"), (8, 22, "PLATE"), (5, 21, "SPRING_R"),
        (6, 21, "PIT"), (11, 13, "P_GATE"),
        (15, 13, "SWITCH"), (20, 7, "R_GATE"), (20, 6, "K1"),
        (19, 22, "K2"), (18, 22, "TNT"), (20, 22, "W"), (19, 21, "W"), (19, 23, "W"),
        (23, 13, "BOX"), (25, 13, "PIT"), (26, 13, "PIT"), (27, 13, "ONEWAY_R"),
        (31, 8, "LASER_D"), (34, 18, "LASER2_U"), (38, 12, "LASER_L"),
        (35, 13, "P_GATE"), (36, 13, "V"),
    )
    for x, y, kind in placements:
        grid[y][x] = kind
    for x in (5, 6, 7):
        grid[17][x] = "ICE"

    # Turn the first crate, slide the second, then bounce and turn the third.
    # Destroy the barrel from outside the blast and keep a jump for the bridge.
    runs = (
        ("MOVE_U", 4), ("MOVE_R", 4), ("MOVE_D", 1), ("MOVE_R", 1), ("MOVE_U", 3),
        ("MOVE_D", 1), ("MOVE_L", 4), ("MOVE_D", 9), ("MOVE_R", 1),
        ("MOVE_L", 1), ("MOVE_D", 4), ("MOVE_R", 1),
        ("MOVE_U", 1), ("MOVE_R", 4), ("MOVE_D", 1),
        ("MOVE_U", 1), ("MOVE_R", 2), ("MOVE_U", 7), ("MOVE_R", 10), ("MOVE_U", 7),
        ("MOVE_D", 14), ("MOVE_L", 4), ("MOVE_D", 2), ("THROW_R", 1),
        ("MOVE_R", 3), ("MOVE_U", 9), ("MOVE_R", 6), ("JUMP_R", 1),
        ("MOVE_R", 3), ("JUMP_R", 1), ("MOVE_R", 4),
    )
    author_solution = [action for action, count in runs for _ in range(count)]
    return {
        "grid": grid,
        "author_solution": author_solution,
        "taunt": "三道压板开门，两格深渊断后。钥匙齐了，再走独木桥。",
    }
