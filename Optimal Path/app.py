# =============================================================================
#  FILE: app.py
#  ROLE: Flask application entry point.
#
#  This is the MAIN file you run to start the web server.
#  It creates the Flask app, registers all URL routes, and
#  connects the frontend (browser) to the Python A* backend.
#
#  HOW FLASK WORKS:
#  ----------------
#  Flask is a lightweight Python web framework.
#  - You define "routes" using @app.route('/some-url')
#  - When a browser visits that URL, Flask calls your Python function
#  - Your function returns HTML (for pages) or JSON (for API calls)
#
#  FLOW IN THIS PROJECT:
#  ---------------------
#  Browser                    Flask (app.py)              Python Modules
#    |                             |                            |
#    |-- GET /          ---------> index()          ---------> renders index.html
#    |                             |                            |
#    |-- POST /api/solve --------> solve()          ---------> astar.py → grid.py
#    |                             |                            |
#    |<-- JSON {path, visited} ----|                            |
#    |                             |                            |
#  Canvas animates the result
#
#  TO RUN:
#  -------
#    pip install flask
#    python app.py
#    Open http://localhost:5000 in your browser
# =============================================================================

from flask import Flask, render_template, request, jsonify

# Import our custom modules
from grid import Grid          # builds the city grid
from astar import AStarSolver  # runs the A* algorithm
from config import CONFIG      # all constants


# -----------------------------------------------------------------------------
# CREATE THE FLASK APPLICATION
# -----------------------------------------------------------------------------
# Flask(__name__) creates the app.
# __name__ tells Flask where to find templates/ and static/ folders.
app = Flask(__name__)


# =============================================================================
#  ROUTE 1: GET /
#  Serves the main HTML page (index.html inside templates/).
#  This is the first thing the browser loads.
# =============================================================================
@app.route('/')
def index():
    """
    Render and return the main page.

    Flask looks for 'index.html' inside the /templates folder.
    We pass CONFIG so the HTML can read grid dimensions etc.
    """
    return render_template('index.html', config=CONFIG)


# =============================================================================
#  ROUTE 2: POST /api/solve
#  The A* API endpoint.
#
#  The browser sends a JSON request describing the grid:
#    {
#      "rows": 20,
#      "cols": 25,
#      "start": [2, 3],         <- [row, col] of start node
#      "end":   [17, 22],       <- [row, col] of end node
#      "walls": [[r,c], ...],   <- list of wall positions
#      "weights": {             <- weighted cells (traffic)
#          "5,8": 4,
#          "9,3": 3
#      }
#    }
#
#  This function:
#    1. Parses the request
#    2. Builds the grid in Python
#    3. Runs A* algorithm
#    4. Returns the result as JSON back to the browser
# =============================================================================
@app.route('/api/solve', methods=['POST'])
def solve():
    """
    Receive grid config from browser, run A*, return path + visited nodes.

    Returns JSON:
    {
      "success": true,
      "path": [[r,c], [r,c], ...],         <- optimal path nodes
      "visited": [[r,c], [r,c], ...],      <- all nodes A* explored
      "open_set_history": [[r,c], ...],    <- nodes added to open set
      "path_cost": 12.5,                   <- total cost of optimal path
      "nodes_visited": 143,                <- how many nodes A* checked
      "message": "Path found!"
    }
    """
    # -------------------------------------------------------------------------
    # STEP 1: Parse the JSON body sent by the browser
    # -------------------------------------------------------------------------
    data = request.get_json()

    # Extract values with safe defaults
    rows        = data.get('rows',    CONFIG['ROWS'])
    cols        = data.get('cols',    CONFIG['COLS'])
    start       = tuple(data.get('start',   [0, 0]))        # (row, col)
    end         = tuple(data.get('end',     [rows-1, cols-1]))
    walls       = [tuple(w) for w in data.get('walls',   [])]
    weights_raw = data.get('weights', {})                    # {"r,c": weight}

    # Convert weights from {"5,8": 4} format to {(5,8): 4} tuple keys
    weights = {}
    for key, val in weights_raw.items():
        r, c = key.split(',')
        weights[(int(r), int(c))] = float(val)

    # -------------------------------------------------------------------------
    # STEP 2: Build the Grid
    # grid.py creates the 2D array of Node objects
    # -------------------------------------------------------------------------
    city_grid = Grid(rows=rows, cols=cols)
    city_grid.set_walls(walls)
    city_grid.set_weights(weights)

    # -------------------------------------------------------------------------
    # STEP 3: Run A* Algorithm
    # astar.py does the pathfinding and returns detailed results
    # -------------------------------------------------------------------------
    solver = AStarSolver(grid=city_grid, start=start, end=end)
    result = solver.solve()

    # -------------------------------------------------------------------------
    # STEP 4: Return results as JSON to the browser
    # jsonify() converts a Python dict → JSON response
    # -------------------------------------------------------------------------
    return jsonify(result)


# =============================================================================
#  ROUTE 3: POST /api/generate-maze
#  Generates a random maze configuration and sends it to the browser.
#  The browser then renders it and lets the user run A* on it.
# =============================================================================
@app.route('/api/generate-maze', methods=['POST'])
def generate_maze():
    """
    Generate a maze and return wall positions + suggested start/end.

    Request JSON: { "type": "random" | "recursive" | "sparse" }
    Response JSON: { "walls": [[r,c],...], "start": [r,c], "end": [r,c] }
    """
    data      = request.get_json()
    maze_type = data.get('type', 'random')

    # Import maze generator (defined in grid.py)
    city_grid = Grid(rows=CONFIG['ROWS'], cols=CONFIG['COLS'])
    maze_data = city_grid.generate_maze(maze_type)

    return jsonify(maze_data)


# =============================================================================
#  MAIN ENTRY POINT
#  When you run `python app.py`, this block executes.
#  debug=True means Flask auto-reloads when you edit files — great for dev.
# =============================================================================
if __name__ == '__main__':
    print("=" * 55)
    print("  OptiRoute — A* Pathfinding Visualizer")
    print("  Open http://localhost:5000 in your browser")
    print("=" * 55)
    app.run(debug=True, port=5000)
