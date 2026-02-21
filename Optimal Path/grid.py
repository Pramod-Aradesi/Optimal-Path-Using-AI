# =============================================================================
#  FILE: grid.py
#  ROLE: Defines the city grid data structure.
#
#  Contains two classes:
#    1. Node  — represents a single cell in the grid
#    2. Grid  — the full 2D city map (collection of Nodes)
#
#  WHY CLASSES?
#  ------------
#  A Node isn't just a position — it carries A* algorithm state
#  (f, g, h scores and parent pointer). Bundling data + behaviour
#  into a class is clean OOP design and makes astar.py much simpler.
#
#  HOW THE GRID LOOKS:
#  -------------------
#  Grid is a 2D list: self.cells[row][col] = Node object
#
#       col→  0     1     2     3
#  row↓  0  [Node][Node][Node][Node]
#         1  [Node][WALL][Node][Node]
#         2  [Node][Node][TRAF][Node]
#
#  Node types:
#    - Normal road  : weight = 1.0  (cheap, fast)
#    - Traffic road : weight = 2–4  (expensive, A* avoids)
#    - Wall         : passable = False (never entered)
#    - Start        : is_start = True
#    - End          : is_end   = True
# =============================================================================

import random
import math
from config import CONFIG


# =============================================================================
#  CLASS: Node
#  Represents one cell in the grid.
# =============================================================================
class Node:
    """
    A single cell in the city grid.

    Attributes:
        row (int)         : Row position in the grid
        col (int)         : Column position in the grid
        passable (bool)   : False = wall (impassable building)
        weight (float)    : Movement cost to ENTER this cell (used by A*)
        is_start (bool)   : True if this is the start node
        is_end   (bool)   : True if this is the goal node

        --- A* Algorithm State (reset before each search) ---
        g (float)         : Actual cost from start to this node
        h (float)         : Heuristic estimate from this node to goal
        f (float)         : f = g + h (total estimated cost)
        parent (Node)     : Previous node on the best known path
        state (str)       : Visualization state:
                            'none'    = untouched
                            'open'    = in open set (being considered)
                            'visited' = in closed set (already evaluated)
                            'path'    = on the final optimal path
    """

    def __init__(self, row: int, col: int):
        # ── Position ─────────────────────────────────────────
        self.row = row
        self.col = col

        # ── Cell type ────────────────────────────────────────
        self.passable  = True              # True = road, False = wall
        self.weight    = CONFIG['WEIGHT_NORMAL']  # default: normal road
        self.is_start  = False
        self.is_end    = False

        # ── A* scores (reset before every search run) ────────
        self.g      = float('inf')   # infinity means "not yet reached"
        self.h      = 0.0
        self.f      = float('inf')   # f = g + h
        self.parent = None           # Node reference (for path tracing)

        # ── Visualization state ───────────────────────────────
        self.state = 'none'

    def reset_astar_state(self):
        """
        Clears A* scores and visualization state.
        Called before every new A* search run so previous
        results don't interfere with the new one.
        """
        self.g      = float('inf')
        self.h      = 0.0
        self.f      = float('inf')
        self.parent = None
        self.state  = 'none'

    def to_dict(self) -> dict:
        """
        Converts this node to a JSON-serializable dictionary.
        Used by Flask to send node data to the browser.
        """
        return {
            'row':      self.row,
            'col':      self.col,
            'passable': self.passable,
            'weight':   self.weight,
            'is_start': self.is_start,
            'is_end':   self.is_end,
            'state':    self.state,
        }

    def __repr__(self):
        return f"Node({self.row},{self.col} w={self.weight})"

    # -------------------------------------------------------------------------
    # Comparison operators — needed so Python's heapq (min-heap) can
    # sort Nodes by f value. heapq uses < to compare items.
    # -------------------------------------------------------------------------
    def __lt__(self, other):
        # Primary sort: lower f(n) comes first
        # Tie-break: lower h(n) (prefer nodes closer to goal)
        if self.f == other.f:
            return self.h < other.h
        return self.f < other.f

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.row == other.row and self.col == other.col

    def __hash__(self):
        # Needed so Node can be used in Python sets (closed set in A*)
        return hash((self.row, self.col))


# =============================================================================
#  CLASS: Grid
#  The full city map — a 2D array of Node objects.
# =============================================================================
class Grid:
    """
    The city grid. Manages creation, wall placement,
    weight assignment, and maze generation.

    Usage:
        g = Grid(rows=20, cols=25)
        g.set_walls([(3,4), (3,5)])
        g.set_weights({(7,8): 4.0})
        node = g.get(5, 10)
    """

    def __init__(self, rows: int, cols: int):
        """
        Create a blank grid filled with normal-weight road nodes.

        Args:
            rows: Number of rows
            cols: Number of columns
        """
        self.rows = rows
        self.cols = cols

        # ── Build the 2D cell array ───────────────────────────
        # List comprehension creates a ROWS x COLS 2D list of Nodes.
        # self.cells[row][col] gives us any node by position.
        self.cells = [
            [Node(row, col) for col in range(cols)]
            for row in range(rows)
        ]

    # -------------------------------------------------------------------------
    # NODE ACCESS
    # -------------------------------------------------------------------------
    def get(self, row: int, col: int) -> Node:
        """
        Get the node at (row, col).
        Returns None if position is out of bounds.
        """
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.cells[row][col]
        return None

    def is_valid(self, row: int, col: int) -> bool:
        """Check if (row, col) is within the grid boundaries."""
        return 0 <= row < self.rows and 0 <= col < self.cols

    # -------------------------------------------------------------------------
    # GRID SETUP
    # -------------------------------------------------------------------------
    def set_walls(self, positions: list):
        """
        Mark a list of positions as walls (impassable).

        Args:
            positions: List of (row, col) tuples to make into walls
        """
        for (row, col) in positions:
            node = self.get(row, col)
            if node and not node.is_start and not node.is_end:
                node.passable = False
                node.weight   = CONFIG['WEIGHT_WALL']

    def set_weights(self, weight_map: dict):
        """
        Assign movement costs to specific cells (traffic jams).

        Args:
            weight_map: dict of {(row, col): weight_value}
            Example:    {(5, 8): 4.0, (9, 3): 2.0}
        """
        for (row, col), weight in weight_map.items():
            node = self.get(row, col)
            if node and node.passable:
                node.weight = weight

    def set_start(self, row: int, col: int) -> Node:
        """Place the start marker on the grid."""
        node = self.get(row, col)
        if node:
            node.is_start  = True
            node.passable  = True  # start is always passable
            node.weight    = CONFIG['WEIGHT_NORMAL']
        return node

    def set_end(self, row: int, col: int) -> Node:
        """Place the end (goal) marker on the grid."""
        node = self.get(row, col)
        if node:
            node.is_end   = True
            node.passable = True  # end is always passable
            node.weight   = CONFIG['WEIGHT_NORMAL']
        return node

    # -------------------------------------------------------------------------
    # NEIGHBOR DISCOVERY
    # Used by astar.py to find which nodes to explore next.
    # -------------------------------------------------------------------------
    def get_neighbors(self, node: Node) -> list:
        """
        Return all passable adjacent cells (4-directional).

        This is called by A* to discover candidate next nodes.
        Only returns passable (non-wall) neighbors within bounds.

        Args:
            node: The current node

        Returns:
            List of neighboring Node objects
        """
        neighbors = []

        # Check all 4 directions: up, down, left, right
        for (dr, dc) in CONFIG['DIRECTIONS_4']:
            new_row = node.row + dr
            new_col = node.col + dc

            # Skip if out of bounds
            if not self.is_valid(new_row, new_col):
                continue

            neighbor = self.cells[new_row][new_col]

            # Skip walls (impassable buildings)
            if not neighbor.passable:
                continue

            neighbors.append(neighbor)

        return neighbors

    # -------------------------------------------------------------------------
    # RESET
    # -------------------------------------------------------------------------
    def reset_astar(self):
        """
        Reset A* scores on all nodes before a new search.
        Preserves walls and weights — only clears algorithm state.
        """
        for row in self.cells:
            for node in row:
                node.reset_astar_state()

    # -------------------------------------------------------------------------
    # MAZE GENERATION
    # Creates interesting grid configurations for demo purposes.
    # -------------------------------------------------------------------------
    def generate_maze(self, maze_type: str = 'random') -> dict:
        """
        Generate a maze and return wall/weight positions.

        Args:
            maze_type: 'random' | 'recursive' | 'sparse'

        Returns:
            dict with 'walls', 'weights', 'start', 'end'
        """

        if maze_type == 'random':
            return self._random_maze()
        elif maze_type == 'recursive':
            return self._recursive_maze()
        else:
            return self._sparse_maze()

    def _random_maze(self) -> dict:
        """
        Randomly place walls with MAZE_WALL_DENSITY probability.
        Also randomly add traffic-weight cells.
        """
        walls   = []
        weights = {}

        # Fixed start and end positions (corners)
        start = CONFIG['DEFAULT_START']
        end   = CONFIG['DEFAULT_END']
        start_tuple = tuple(start)
        end_tuple   = tuple(end)

        for r in range(self.rows):
            for c in range(self.cols):
                pos = (r, c)

                # Never wall out the start or end
                if pos == start_tuple or pos == end_tuple:
                    continue

                # Randomly decide: wall?
                if random.random() < CONFIG['MAZE_WALL_DENSITY']:
                    walls.append([r, c])
                # Or: traffic weight?
                elif random.random() < CONFIG['MAZE_TRAFFIC_DENSITY']:
                    weight = random.choice([
                        CONFIG['WEIGHT_MEDIUM'],
                        CONFIG['WEIGHT_HEAVY']
                    ])
                    weights[f"{r},{c}"] = weight

        return {
            'walls':   walls,
            'weights': weights,
            'start':   start,
            'end':     end,
        }

    def _recursive_maze(self) -> dict:
        """
        Generate a proper maze using Recursive Division algorithm.
        Creates corridors and rooms — harder for A* to navigate.
        """
        # Start with all walls
        wall_set = set()
        for r in range(self.rows):
            for c in range(self.cols):
                wall_set.add((r, c))

        # Carve passages starting from (1,1)
        def carve(r, c):
            # Mark current cell as open (remove from walls)
            wall_set.discard((r, c))

            # Shuffle directions for random maze shape
            dirs = list(CONFIG['DIRECTIONS_4'])
            random.shuffle(dirs)

            for (dr, dc) in dirs:
                # Move 2 steps in this direction
                nr, nc = r + dr * 2, c + dc * 2

                # Only carve if destination is still a wall and in bounds
                if (nr, nc) in wall_set and self.is_valid(nr, nc):
                    # Remove the wall between current and destination
                    wall_set.discard((r + dr, c + dc))
                    carve(nr, nc)

        # Start carving from top-left area
        carve(1, 1)

        # Convert wall set to list format for JSON
        walls = [[r, c] for (r, c) in wall_set]

        start = CONFIG['DEFAULT_START']
        end   = CONFIG['DEFAULT_END']

        # Ensure start and end are not walls
        start_tuple = tuple(start)
        end_tuple   = tuple(end)
        walls = [w for w in walls
                 if tuple(w) != start_tuple and tuple(w) != end_tuple]

        return {'walls': walls, 'weights': {}, 'start': start, 'end': end}

    def _sparse_maze(self) -> dict:
        """
        Light maze: fewer walls, more traffic weights.
        Good for demonstrating traffic avoidance.
        """
        walls   = []
        weights = {}
        start   = CONFIG['DEFAULT_START']
        end     = CONFIG['DEFAULT_END']

        for r in range(self.rows):
            for c in range(self.cols):
                if [r, c] == start or [r, c] == end:
                    continue
                roll = random.random()
                if roll < 0.12:
                    walls.append([r, c])
                elif roll < 0.30:
                    weights[f"{r},{c}"] = CONFIG['WEIGHT_HEAVY']
                elif roll < 0.45:
                    weights[f"{r},{c}"] = CONFIG['WEIGHT_MEDIUM']

        return {'walls': walls, 'weights': weights, 'start': start, 'end': end}
