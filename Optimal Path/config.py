# =============================================================================
#  FILE: config.py
#  ROLE: Central configuration — ALL constants live here.
#
#  WHY A SEPARATE CONFIG FILE?
#  ----------------------------
#  Instead of hardcoding numbers like 20, 25, or 4.0 across many files,
#  we define them ONCE here. If you want to change the grid to 30x40,
#  you change one line — not hunt across every file.
#
#  This is called the "Single Source of Truth" principle.
#  Every other Python file imports from here:
#      from config import CONFIG
#
#  Python dict is used (instead of a class) so it can be directly
#  passed to Flask's render_template() for use in HTML templates.
# =============================================================================

CONFIG = {

    # -------------------------------------------------------------------------
    # GRID DIMENSIONS
    # The city is a 2D grid of ROWS x COLS cells.
    # Each cell is either a road (passable) or a wall (impassable).
    # -------------------------------------------------------------------------
    'ROWS': 20,      # Number of rows (vertical size of the map)
    'COLS': 25,      # Number of columns (horizontal size of the map)

    # -------------------------------------------------------------------------
    # MOVEMENT COSTS (Node Weights)
    # When A* moves from one node to its neighbor, it adds the neighbor's
    # weight to g(n). Higher weight = more expensive = A* avoids it.
    #
    # This is how traffic avoidance works — no special logic needed.
    # A* naturally picks the cheaper route.
    # -------------------------------------------------------------------------
    'WEIGHT_NORMAL': 1.0,    # Plain road — cheap, fast to traverse
    'WEIGHT_MEDIUM': 2.0,    # Moderate traffic — A* uses if no better option
    'WEIGHT_HEAVY':  4.0,    # Heavy traffic jam — A* avoids unless necessary
    'WEIGHT_WALL':   0,      # Wall / building — impassable (never entered)

    # -------------------------------------------------------------------------
    # MOVEMENT DIRECTIONS
    # We support 4-directional movement (up, down, left, right).
    # Diagonal movement is excluded because city roads are axis-aligned.
    #
    # Each tuple is (delta_row, delta_col):
    #   (-1, 0) = move UP    one row
    #   ( 1, 0) = move DOWN  one row
    #   ( 0,-1) = move LEFT  one col
    #   ( 0, 1) = move RIGHT one col
    # -------------------------------------------------------------------------
    'DIRECTIONS_4': [(-1, 0), (1, 0), (0, -1), (0, 1)],

    # 8-directional movement (includes diagonals) — diagonal cost = sqrt(2)
    # Switch to this in astar.py if you want diagonal movement
    'DIRECTIONS_8': [
        (-1, 0), (1, 0), (0, -1), (0, 1),   # cardinal
        (-1,-1), (-1, 1), (1,-1), (1, 1),    # diagonals
    ],

    # -------------------------------------------------------------------------
    # HEURISTIC OPTIONS
    # The heuristic h(n) estimates cost from node n to the goal.
    # The browser lets the user switch between these at runtime.
    # -------------------------------------------------------------------------
    'HEURISTIC_MANHATTAN':  'manhattan',   # |Δrow| + |Δcol| — best for 4-dir
    'HEURISTIC_EUCLIDEAN':  'euclidean',   # sqrt(Δrow² + Δcol²)
    'HEURISTIC_CHEBYSHEV':  'chebyshev',  # max(|Δrow|, |Δcol|) — for 8-dir

    # -------------------------------------------------------------------------
    # DEFAULT POSITIONS
    # Where start and end nodes are placed when the page first loads.
    # -------------------------------------------------------------------------
    'DEFAULT_START': [1, 1],
    'DEFAULT_END':   [18, 23],

    # -------------------------------------------------------------------------
    # MAZE GENERATION
    # Controls random wall density when generating a maze.
    # 0.0 = no walls, 1.0 = all walls (use 0.25–0.35 for interesting mazes)
    # -------------------------------------------------------------------------
    'MAZE_WALL_DENSITY': 0.28,    # 28% of cells become walls in random mode
    'MAZE_TRAFFIC_DENSITY': 0.10, # 10% of open cells get traffic weight

    # -------------------------------------------------------------------------
    # ANIMATION (used by frontend JavaScript, passed via render_template)
    # -------------------------------------------------------------------------
    'ANIM_DELAY_MS': 18,     # Default ms between each A* step animation
}
