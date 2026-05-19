import heapq
from settings import MAP_ROWS, MAP_COLS

def _oct_dist(a, b):
    """Calculate the octile distance between two coordinate positions.

    Input:
        a: (row, col) coordinate tuple
        b: (row, col) coordinate tuple
    Output:
        The octile distance as a float
    """
    dr, dc = abs(a[0] - b[0]), abs(a[1] - b[1])
    return max(dr, dc) + 0.414 * min(dr, dc)

def astar(start, goal, nav_grid):
    """Find the shortest path from a start position to a goal position using the A* algorithm.

    Input:
        start: (row, col) coordinate tuple representing the starting position
        goal: (row, col) coordinate tuple representing the final position
        nav_grid: A 2D list of booleans representing walkable/blocked tiles
    Output:
        A list of (row, col) coordinate tuples representing the path from start to goal,
        or an empty list if no path is found.
    """
    if not (0 <= goal[0] < MAP_ROWS and 0 <= goal[1] < MAP_COLS):
        return []
    if not nav_grid[goal[0]][goal[1]]:
        return []
    heap = [(0.0, start)]
    prev = {}
    g    = {start: 0.0}
    while heap:
        _, cur = heapq.heappop(heap)
        if cur == goal:
            path = []
            while cur in prev:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        r, c = cur
        for dr, dc in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < MAP_ROWS and 0 <= nc < MAP_COLS):
                continue
            if not nav_grid[nr][nc]:
                continue
            if dr and dc and not (nav_grid[r][nc] and nav_grid[nr][c]):
                continue
            cost = 1.414 if (dr and dc) else 1.0
            ng   = g[cur] + cost
            nb   = (nr, nc)
            if ng < g.get(nb, 1e9):
                prev[nb] = cur
                g[nb]    = ng
                heapq.heappush(heap, (ng + _oct_dist(nb, goal), nb))
    return []

def px_to_tile(px, py, tile_size):
    """Convert screen pixel coordinates to grid tile coordinates.

    Input:
        px: pixel x-coordinate
        py: pixel y-coordinate
        tile_size: the size of a single tile in pixels
    Output:
        A (row, col) coordinate tuple corresponding to the tile containing the pixel
    """
    return (max(0, min(MAP_ROWS - 1, py // tile_size)),
            max(0, min(MAP_COLS - 1, px // tile_size)))

def tile_center(r, c, tile_size):
    """Calculate the screen pixel coordinates of the center of a given tile.

    Input:
        r: tile row index
        c: tile column index
        tile_size: the size of a single tile in pixels
    Output:
        An (x, y) coordinate tuple representing the pixel center of the tile
    """
    return (c * tile_size + tile_size // 2, r * tile_size + tile_size // 2)
