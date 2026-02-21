# 🔷 OptiRoute — A* Pathfinding Visualizer (Python + Flask)

Real-time A* algorithm visualization in the browser, powered by a Python Flask backend.

---

## 📁 Project Structure

```
optiroute-python/
│
├── app.py              ← Flask server (routes, API endpoints)
├── astar.py            ← A* algorithm using Python heapq (CORE AI)
├── grid.py             ← Node + Grid classes (data model)
├── config.py           ← All constants (grid size, weights, etc.)
├── requirements.txt    ← Python dependencies
│
├── templates/
│   └── index.html      ← Main HTML page (Jinja2 template)
│
└── static/
    ├── css/
    │   └── style.css   ← Dark-theme styling
    └── js/
        ├── renderer.js ← Canvas drawing engine
        └── app.js      ← Frontend logic + Flask API calls
```

---

## 🚀 How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the Flask server
python app.py

# 3. Open in browser
# http://localhost:5000
```

---

## 🧠 How It Works

```
Browser (JavaScript)          Python Flask Backend
─────────────────────         ────────────────────
User draws grid           →   POST /api/solve
                              ↓
                              grid.py builds Grid
                              ↓
                              astar.py runs A*
                              ↓
                              Returns JSON:
                              { path, visited, cost }
                          ←
Canvas animates result
step by step
```

---

## 🔑 Key Python Concepts Used

| Concept | Where | Why |
|---------|-------|-----|
| `heapq` min-heap | `astar.py` | O(log n) priority queue for open set |
| Classes (`Node`, `Grid`, `AStarSolver`) | `grid.py`, `astar.py` | OOP data encapsulation |
| `float('inf')` | `grid.py` | Initial g/f values before discovery |
| `set()` | `astar.py` | O(1) closed set membership checks |
| `@app.route` | `app.py` | Flask URL routing decorator |
| `request.get_json()` | `app.py` | Parse JSON from browser |
| `jsonify()` | `app.py` | Return Python dict as JSON response |
| `render_template()` | `app.py` | Pass Python data to HTML (Jinja2) |

---

## A* Formula

```
f(n) = g(n) + h(n)

g(n) = actual cost from start to node n
h(n) = Manhattan distance estimate to goal
f(n) = total estimated cost through n
```

A* always expands the node with the **lowest f(n)** — guaranteed optimal path.
