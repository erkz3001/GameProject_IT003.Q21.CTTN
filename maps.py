import random

# Tile codes: 0=floor 1=player 2=slime 3=wall 4=torch 5=item 6=door 9=key 10=spike
# All maps: 20 rows x 36 cols, single-tile walls
# Key (9) and Door (6) are NOT hardcoded — placed randomly by place_door_and_key().

W = [3]*36

def _r(vals={}):
    """36-col row: walls at col 0 & 35, floor inside, with optional overrides."""
    row = [3]+[0]*34+[3]
    for c,v in vals.items(): row[c]=v
    return row

def _w(vals={}):
    """Full wall row with optional overrides."""
    row = [3]*36
    for c,v in vals.items(): row[c]=v
    return row

def _split(divs, vals={}):
    row = [3] + [0]*34 + [3]

    for d in divs:
        row[d] = 3

    for c, v in vals.items():
        row[c] = v

    return row

def add_traps(tile_map, spike_count=9):
    """Randomly place spike traps (10) on open floor tiles (0)."""
    candidates = [(r, c) for r, row in enumerate(tile_map)
                  for c, t in enumerate(row) if t == 0]
    random.shuffle(candidates)
    result = [list(row) for row in tile_map]
    for r, c in candidates[:spike_count]:
        result[r][c] = 10
    return result


def create_nav_grid(tile_map):
    """Return a boolean grid: True=walkable."""
    return [[t != 3 for t in row] for row in tile_map]

def _q(vals={}):
    """Quadrant row: walls at col 0, 17, 35."""
    row=[3]+[0]*16+[3]+[0]*17+[3]
    for c,v in vals.items(): row[c]=v
    return row

def _qc(vals={}):
    """Quadrant row with full open corridor."""
    row=[3]+[0]*34+[3]
    for c,v in vals.items(): row[c]=v
    return row

# ── MAP 1: Left/Right two-room layout ──────────────────────────────────────
MAP_1 = [
    W,                                                     # r0
    _split([17, 24]),                                # r1  torches
    _split([17, 24]),                                            # r2
    _split([17, 24],{3:4,13:4}),                                            # r3
    _split([17, 24],{8:2, 26:2}),                                # r4  slimes
    _split([17]),                                            # r5
    _split([17],{5:4,14:4,29:4}),                                # r6  torches
    _split([17]),                                            # r7
    _r({}),                                               # r8  corridor
    _r({4:1, 15:4}),                                            # r9  player
    _r({}),                                               # r10
    _r({4:4, 12:4, 23:4}),                                               # r11
    _split([17]),                                            # r12
    _split([17],{8:2,26:2}),                                # r13 slimes
    _split([17]),                                            # r14
    _split([17],{12:4, 17:4, 20:5}),                                    # r15 item
    _split([17, 22]),                                            # r16
    _split([17, 22],{1:4,32:4}),                                # r17 torches
    _split([17, 22]),                                            # r18
    W,                                                     # r19
]

# ── MAP 2: Top/Bottom two-room layout ──────────────────────────────────────
MAP_2 = [
    W,                                                     # r0
    _r(),                                       # r1  torches
    _r({8:2,26:2}),                                       # r2  slimes
    _r({}),                                               # r3
    _r({4:1, 6:4, 15:4, 23:4}),                                            # r4  player
    _r({}),                                               # r5
    _r({20:5}),                                           # r6  item
    _r({7:4,31:4}),                                       # r7  torches
    _r({}),                                               # r8
    _w({1:3,2:3,3:3,4:3,5:3,6:3,7:3,8:3,9:3,
        10:0,11:0,12:0,13:0,
        14:3,15:3,16:3,17:3,18:3,19:3,20:3,21:3,22:3,
        23:0,24:0,25:0,26:0,
        27:3,28:3,29:3,30:3,31:3,32:3,33:3,34:3,35:3}), # r9  wall + gaps
    _w({1:3,2:3,3:3,4:3,5:3,6:3,7:3,8:3,9:3,
        10:0,11:0,12:0,13:0,
        14:3,15:3,16:3,17:3,18:3,19:3,20:3,21:3,22:3,
        23:0,24:0,25:0,26:0,
        27:3,28:3,29:3,30:3,31:3,32:3,33:3,34:3,35:3}), # r10 wall + gaps
    _r({}),                                               # r11
    _r({8:2,26:2}),                                       # r12 slimes
    _r({}),                                               # r13
    _r({}),                                               # r14
    _r({6:4,17:4}),                                       # r15 torches
    _r({}),                                               # r16
    _r({}),                                               # r17
    _r({}),                                               # r18
    W,                                                     # r19
]

# ── MAP 3: Four-room quadrant ───────────────────────────────────────────────


MAP_3 = [
    W,                                                     # r0
    _q(),                                       # r1
    _q({8:2,26:2}),                                       # r2
    _q({}),                                               # r3
    _q({4:1, 9:4, 26:4}),                                            # r4  player
    _q({}),                                               # r5
    _q({5:4,17:4}),                                       # r6
    _q({8:2,26:2}),                                       # r7
    _q({}),                                               # r8
    _qc({}),                                              # r9  corridor
    _qc({13:4}),                                              # r10 corridor
    _q({}),                                               # r11
    _q({5:5,28:5}),                                       # r12 items
    _q({8:2,26:2}),                                       # r13 slimes
    _q({}),                                               # r14
    _q({}),                                               # r15
    _q({3:4,19:4}),                                       # r16
    _q({}),                                               # r17
    _q({}),                                               # r18
    W,                                                     # r19
]

# ── MAP 4: Open arena with internal pillars ─────────────────────────────────
MAP_4 = [
    W,                                                     # r0
    _r(),                                       # r1
    _r({10:3,11:3,23:3,24:3}),                           # r2  pillars
    _r({10:3,11:3,23:3,24:3, 5:4}),                           # r3
    _r({6:2,28:2}),                                       # r4  slimes
    _r({}),                                               # r5
    _r({3:4,17:5,25:4}),                                  # r6
    _r({}),                                               # r7
    _r({10:3,11:3,23:3,24:3}),                           # r8  pillars
    _r({10:3,11:3,23:3,24:3}),                           # r9
    _r({4:1, 9:4}),                                            # r10 player
    _r({10:3,11:3,23:3,24:3}),                           # r11 pillars
    _r({10:3,11:3,23:3,24:3}),                           # r12
    _r({}),                                               # r13
    _r({3:4,17:10,26:4}),                                 # r14 spike
    _r({6:2,28:2}),                                       # r15 slimes
    _r({}),                                               # r16
    _r({10:3,11:3,23:3,24:3}),                           # r17 pillars
    _r({10:3,11:3,23:3,24:3}),                           # r18
    W,                                                     # r19
]

# ── MAP 5: S-path / shifted split ──────────────────────────────────────────
MAP_5 = [
    W,                                                     # r0
    _split([17]),                                     # r1  left room torch
    _split([17],{8:2}),                                     # r2  slime
    _split([17],{5:4}),                                        # r3
    _split([17],{4:1}),                                     # r4  player
    _split([17],{8:5}),                                     # r5  item
    _split([17],{12:4, 18:4}),                                        # r6
    _split([17],{8:2}),                                     # r7  slime
    _r({}),                                               # r8  corridor
    _r({}),                                               # r9  corridor
    _split([18],{}),                                        # r10 right room starts
    _split([18],{26:2}),                                    # r11 slime
    _split([18],{7:4, 24:4}),                                        # r12
    _split([18],{26:5}),                                    # r13 item
    _split([18],{}),                                        # r14
    _split([18],{26:2}),                                    # r15 slime
    _split([18],{27:4}),                                    # r16 torch
    _split([18],{}),                                        # r17
    _split([18],{}),                                        # r18
    W,                                                     # r19
]

ALL_MAPS = [MAP_1, MAP_2, MAP_3, MAP_4, MAP_5]

def get_random_map():
    return random.choice(ALL_MAPS)

def place_door_and_key(tile_map):
    """Return a fresh copy of tile_map with door (tile 6×2) and key (tile 9) placed randomly.

    Door: placed on the top (r=0) or bottom (r=last) wall row, centred randomly.
    Key:  placed on a random open floor tile far from the player spawn.
    """
    result = [list(row) for row in tile_map]
    rows, cols = len(result), len(result[0])

    # ── Door ────────────────────────────────────────────────────────────────
    side = random.choice([0, rows - 1])
    wall_row = result[side]
    # Both col c and c+1 must be solid walls; avoid the outermost two cols
    cands = [c for c in range(2, cols - 3)
             if wall_row[c] == 3 and wall_row[c + 1] == 3]
    # Prefer the centre third to keep the door visible and reachable
    if cands:
        lo = max(0, len(cands) // 3)
        hi = min(len(cands), 2 * len(cands) // 3) or len(cands)
        dc = random.choice(cands[lo:hi] or cands)
        result[side][dc]     = 6
        result[side][dc + 1] = 6

    # ── Key ─────────────────────────────────────────────────────────────────
    # Find player spawn for distance check
    player_rc = next(
        ((r, c) for r, row in enumerate(result) for c, t in enumerate(row) if t == 1),
        (rows // 2, cols // 2),
    )
    # Must be an open floor tile at least 8 tiles away (Manhattan) from player
    eligible = [
        (r, c) for r, row in enumerate(result)
        for c, t in enumerate(row)
        if t == 0 and abs(r - player_rc[0]) + abs(c - player_rc[1]) > 8
    ]
    if eligible:
        kr, kc = random.choice(eligible)
        result[kr][kc] = 9

    return result


