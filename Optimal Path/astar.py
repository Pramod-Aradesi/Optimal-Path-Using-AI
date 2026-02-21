# =============================================================================
#  FILE: astar.py
#  ROLE: Implements the A* (A-Star) pathfinding algorithm in Python.
#
#  THIS IS THE CORE AI ENGINE OF THE PROJECT.
#
#  WHAT IS A*?
#  -----------
#  A* is a "best-first search" algorithm that finds the CHEAPEST path
#  between two nodes on a weighted graph.
#
#  It is smarter than:
#    - BFS     : which ignores edge weights (treats all moves equally)
#    - Dijkstra: which explores in ALL directions with no goal guidance
#
#  A* uses a HEURISTIC to guide the search toward the goal,
#  making it much faster while still guaranteeing the optimal path.
#
#  THE FORMULA: f(n) = g(n) + h(n)
#  --------------------------------
#    g(n) = EXACT cost from start to node n (we know this precisely)
#    h(n) = ESTIMATED cost from node n to goal (approximation)
#    f(n) = total estimated cost of the best path THROUGH node n
#
#  At every step, A* picks the node with the LOWEST f(n) from
#  the open set (priority queue) and explores its neighbors.
#
#  WHY heapq (MIN-HEAP)?
#  ---------------------
#  In our JavaScript version, we used array.sort() = O(n log n) per step.
#  Here in Python, we use heapq — a binary min-heap:
#    - heappush() inserts a node in O(log n)
#    - heappop()  removes the minimum-f node in O(log n)
#  This is the production-grade approach.
#
#  RECORDED DATA FOR VISUALIZATION:
#  ----------------------------------
#  We record every node evaluation so the browser can
#  animate the algorithm step by step:
#    - visited_order : nodes evaluated in sequence
#    - open_history  : nodes added to open set in sequence
#    - final path    : the optimal route
# =============================================================================

import heapq
import math
from grid import Grid, Node
from config import CONFIG


# =============================================================================
#  HEURISTIC FUNCTIONS
#  These estimate the cost from a node to the goal.
#  A good heuristic is ADMISSIBLE — never overestimates.
# =============================================================================

def manhattan_distance(node_a: Node, node_b: Node) -> float:
    """
    Manhattan Distance: |Δrow| + |Δcol|

    Best for 4-directional grids (up/down/left/right only).
    It is ADMISSIBLE for 4-dir movement because the true path
    can never be shorter than the Manhattan distance.

    Example: From (2,3) to (5,7)
      h = |2-5| + |3-7| = 3 + 4 = 7
    """
    return abs(node_a.row - node_b.row) + abs(node_a.col - node_b.col)


def euclidean_distance(node_a: Node, node_b: Node) -> float:
    """
    Euclidean Distance: sqrt(Δrow² + Δcol²)

    Good for free-movement (any direction). For strict 4-dir grids,
    it slightly underestimates diagonal paths — still admissible,
    but less tight than Manhattan.

    Example: From (2,3) to (5,7)
      h = sqrt((2-5)² + (3-7)²) = sqrt(9+16) = sqrt(25) = 5.0
    """
    return math.sqrt(
        (node_a.row - node_b.row) ** 2 +
        (node_a.col - node_b.col) ** 2
    )


def chebyshev_distance(node_a: Node, node_b: Node) -> float:
    """
    Chebyshev Distance: max(|Δrow|, |Δcol|)

    Optimal for 8-directional movement (diagonals allowed).
    It counts the minimum number of "king moves" on a chessboard.
    """
    return max(
        abs(node_a.row - node_b.row),
        abs(node_a.col - node_b.col)
    )


# Map heuristic name string → function (used by AStarSolver)
HEURISTICS = {
    'manhattan':  manhattan_distance,
    'euclidean':  euclidean_distance,
    'chebyshev':  chebyshev_distance,
}


# =============================================================================
#  CLASS: AStarSolver
#  Runs A* on a Grid and returns detailed results.
# =============================================================================
class AStarSolver:
    """
    Runs A* pathfinding on a Grid object.

    Usage:
        solver = AStarSolver(grid, start=(0,0), end=(19,24))
        result = solver.solve()
        # result['path'] contains the optimal path as [[r,c], ...]

    Args:
        grid      : Grid object from grid.py
        start     : (row, col) tuple for start position
        end       : (row, col) tuple for goal position
        heuristic : 'manhattan' | 'euclidean' | 'chebyshev'
    """

    def __init__(self, grid: Grid, start: tuple, end: tuple,
                 heuristic: str = 'manhattan'):

        self.grid      = grid
        self.start_pos = start    # (row, col) tuple
        self.end_pos   = end

        # Select heuristic function from the map above
        self.heuristic_fn = HEURISTICS.get(heuristic, manhattan_distance)
        self.heuristic_name = heuristic

        # Get the actual Node objects from the grid
        self.start_node = grid.get(start[0], start[1])
        self.end_node   = grid.get(end[0],   end[1])

        # ── Data recorded during search (for animation) ───────
        # We store the ORDER in which nodes were visited/opened
        # so the browser can replay the algorithm step by step.
        self.visited_order  = []   # [[r,c], ...] — nodes evaluated in order
        self.open_history   = []   # [[r,c], ...] — nodes added to open set

    # -------------------------------------------------------------------------
    # MAIN SOLVE METHOD
    # -------------------------------------------------------------------------
    def solve(self) -> dict:
        """
        Run the A* algorithm and return results.

        Returns:
            dict with keys:
                success         : bool — was a path found?
                path            : [[r,c], ...] — optimal path nodes
                visited         : [[r,c], ...] — all nodes A* explored
                open_history    : [[r,c], ...] — open set additions
                path_cost       : float — total cost of optimal path
                nodes_visited   : int — how many nodes were evaluated
                heuristic_used  : str — which heuristic was used
                message         : str — human-readable result
        """

        # ── GUARD: Validate start and end nodes ───────────────
        if not self.start_node:
            return self._error("Start position is out of bounds.")
        if not self.end_node:
            return self._error("End position is out of bounds.")
        if not self.start_node.passable:
            return self._error("Start node is a wall — choose a road cell.")
        if not self.end_node.passable:
            return self._error("End node is a wall — choose a road cell.")

        # ── STEP 1: Reset grid A* state ────────────────────────
        # Clear any scores from previous runs
        self.grid.reset_astar()
        self.visited_order = []
        self.open_history  = []

        # ── STEP 2: Initialize start node ─────────────────────
        start = self.start_node
        end   = self.end_node

        start.g = 0.0                                   # cost from start = 0
        start.h = self.heuristic_fn(start, end)         # estimate to goal
        start.f = start.g + start.h                     # total estimate

        # ── STEP 3: Set up the Open Set (min-heap) ────────────
        # The open set holds nodes we've DISCOVERED but not yet EVALUATED.
        #
        # We use Python's heapq module — a binary min-heap.
        # heappush / heappop maintain the heap property:
        #   the SMALLEST element is always at index 0.
        #
        # heapq compares tuples element by element:
        #   (f_value, node) — so nodes with lowest f are popped first.
        #   Node.__lt__ handles ties (by comparing h values).
        open_heap = []
        heapq.heappush(open_heap, (start.f, start))

        # ── STEP 4: Set up the Closed Set ─────────────────────
        # The closed set tracks nodes already fully evaluated.
        # Using a Python set gives O(1) membership checks.
        closed_set = set()

        # ── STEP 5: Main A* Loop ───────────────────────────────
        while open_heap:

            # ------------------------------------------------------------------
            # 5a. Pop the node with the LOWEST f(n) from the heap
            # ------------------------------------------------------------------
            _, current = heapq.heappop(open_heap)

            # Skip if already evaluated (can have stale duplicates in heap)
            # This happens because we push duplicates instead of updating in-place
            if current in closed_set:
                continue

            # ------------------------------------------------------------------
            # 5b. Mark as evaluated (add to closed set)
            # ------------------------------------------------------------------
            closed_set.add(current)

            # Record this node was visited — browser will animate it blue
            if current is not start and current is not end:
                current.state = 'visited'
                self.visited_order.append([current.row, current.col])

            # ------------------------------------------------------------------
            # 5c. GOAL CHECK — Did we reach the end node?
            # ------------------------------------------------------------------
            if current is end:
                # SUCCESS — trace the path and return results
                path       = self._trace_path()
                path_cost  = end.g

                return {
                    'success':        True,
                    'path':           path,
                    'visited':        self.visited_order,
                    'open_history':   self.open_history,
                    'path_cost':      round(path_cost, 2),
                    'nodes_visited':  len(self.visited_order),
                    'heuristic_used': self.heuristic_name,
                    'message':        f"Path found! Cost: {path_cost:.1f}, "
                                      f"Nodes visited: {len(self.visited_order)}",
                }

            # ------------------------------------------------------------------
            # 5d. Explore neighbors
            # ------------------------------------------------------------------
            for neighbor in self.grid.get_neighbors(current):

                # Skip already-evaluated nodes
                if neighbor in closed_set:
                    continue

                # --------------------------------------------------------------
                # CALCULATE TENTATIVE g SCORE
                # --------------------------------------------------------------
                # The cost to reach `neighbor` via `current` is:
                #   current's cost + neighbor's movement weight
                #
                # neighbor.weight is the KEY to traffic avoidance:
                #   normal road  (weight=1.0) → cheap
                #   traffic jam  (weight=4.0) → expensive
                # A* naturally picks cheaper routes.
                # --------------------------------------------------------------
                tentative_g = current.g + neighbor.weight

                # Is this a BETTER path to this neighbor than previously known?
                if tentative_g < neighbor.g:
                    # YES — update neighbor with better values

                    # Record where we came from (for path reconstruction later)
                    neighbor.parent = current

                    # Update scores
                    neighbor.g = tentative_g
                    neighbor.h = self.heuristic_fn(neighbor, end)
                    neighbor.f = neighbor.g + neighbor.h

                    # Mark as "open" for visualization (green on canvas)
                    if neighbor is not end:
                        neighbor.state = 'open'

                    # Add to open heap
                    # Note: We push a new entry even if neighbor is already in
                    # the heap. The stale entry will be skipped (closed_set check
                    # above). This "lazy deletion" avoids complex heap updates.
                    heapq.heappush(open_heap, (neighbor.f, neighbor))

                    # Record for animation
                    self.open_history.append([neighbor.row, neighbor.col])

        # ── STEP 6: Open set exhausted — no path found ────────
        return {
            'success':        False,
            'path':           [],
            'visited':        self.visited_order,
            'open_history':   self.open_history,
            'path_cost':      0,
            'nodes_visited':  len(self.visited_order),
            'heuristic_used': self.heuristic_name,
            'message':        "No path found — goal is unreachable.",
        }

    # -------------------------------------------------------------------------
    # PATH RECONSTRUCTION
    # -------------------------------------------------------------------------
    def _trace_path(self) -> list:
        """
        Reconstruct the optimal path by following parent pointers
        from the end node back to the start node.

        HOW IT WORKS:
        During the search, every time we found a better path to a node,
        we set: neighbor.parent = current
        This creates a chain of pointers from end → start.

        We follow this chain backwards, then reverse to get start → end.

        Returns:
            List of [row, col] pairs from start to end (inclusive).
        """
        path    = []
        current = self.end_node

        # Walk backwards through parent pointers
        while current is not None:
            path.append([current.row, current.col])
            current = current.parent   # jump to previous node

        # Path is currently end → start, so reverse it
        path.reverse()   # now it's start → end

        # Mark path nodes for visualization (orange on canvas)
        for pos in path:
            node = self.grid.get(pos[0], pos[1])
            if node and node is not self.start_node and node is not self.end_node:
                node.state = 'path'

        return path

    # -------------------------------------------------------------------------
    # ERROR HELPER
    # -------------------------------------------------------------------------
    def _error(self, message: str) -> dict:
        """Return a standard error result dict."""
        return {
            'success':        False,
            'path':           [],
            'visited':        [],
            'open_history':   [],
            'path_cost':      0,
            'nodes_visited':  0,
            'heuristic_used': self.heuristic_name,
            'message':        f"Error: {message}",
        }
