/**
 * FILE: static/js/app.js
 * ROLE: Frontend brain — manages grid state, user interaction,
 *       API calls to Python Flask, and animation of A* results.
 *
 * FLOW:
 *   1. Page loads → initApp() sets up canvas + event listeners
 *   2. User draws on grid → updates gridState[][] + redraws cells
 *   3. User clicks "Run A*" → runVisualization()
 *      a. Collects grid state → sends POST to /api/solve (Python)
 *      b. Python runs A* → returns JSON {path, visited, ...}
 *      c. animateResult() plays back visited + path step by step
 *
 * KEY DATA STRUCTURES:
 *   gridState[row][col]  → string: 'empty'|'wall'|'start'|'end'|'traffic'|...
 *   wallSet              → Set of "r,c" strings for fast lookup
 *   weightMap            → {"r,c": weight} for traffic cells
 */

// ── Shared State ───────────────────────────────────────────────
// gridState is a 2D array of cell state strings.
// It is initialized in initApp() and read by renderer.js.
let gridState = [];

// Tracks where start and end are placed
let startPos = null;   // [row, col]
let endPos   = null;   // [row, col]

// Tracks walls and traffic cells
let wallSet   = new Set();    // "r,c" strings
let weightMap = {};           // {"r,c": weight_number}

// Current draw mode (what the mouse places)
let currentMode = 'start';

// Is the algorithm currently running? (prevents double-click)
let isRunning = false;

// Is the mouse held down? (for click-drag drawing)
let isMouseDown = false;

// Animation delay in ms (controlled by speed slider)
let animDelay = ANIM_DELAY;  // ANIM_DELAY comes from index.html <script>


// =============================================================================
//  INITIALIZATION
// =============================================================================

/**
 * initApp()
 * ─────────
 * Called on page load. Sets up:
 *   1. The gridState 2D array (all empty)
 *   2. Canvas size via renderer.js
 *   3. Default start + end positions
 *   4. Mouse event listeners on the canvas
 *   5. Speed slider listener
 */
function initApp() {
  // ── Step 1: Create blank gridState ─────────────────────────
  // Two nested loops build a ROWS x COLS 2D array of 'empty' strings.
  gridState = [];
  for (let r = 0; r < ROWS; r++) {
    gridState[r] = [];
    for (let c = 0; c < COLS; c++) {
      gridState[r][c] = 'empty';
    }
  }

  // ── Step 2: Size the canvas ─────────────────────────────────
  // initRenderer() is in renderer.js — sets canvas.width/height
  initRenderer();

  // ── Step 3: Place default start and end ─────────────────────
  // DEF_START and DEF_END come from index.html (passed by Flask/Python)
  placeStart(DEF_START[0], DEF_START[1]);
  placeEnd(DEF_END[0],     DEF_END[1]);

  // ── Step 4: Draw the initial empty grid ─────────────────────
  drawGrid();  // renderer.js

  // ── Step 5: Attach mouse events to canvas ───────────────────
  const canvas = document.getElementById('grid-canvas');
  canvas.addEventListener('mousedown', onMouseDown);
  canvas.addEventListener('mousemove', onMouseMove);
  canvas.addEventListener('mouseup',   () => isMouseDown = false);
  canvas.addEventListener('mouseleave',() => isMouseDown = false);

  // ── Step 6: Speed slider ─────────────────────────────────────
  const slider = document.getElementById('speed-slider');
  slider.addEventListener('input', (e) => {
    // Invert: high slider = fast = low delay
    animDelay = Math.round((100 - e.target.value) * 0.4);
    document.getElementById('speed-label').textContent = `${animDelay}ms delay`;
  });

  appendLog('Canvas initialized', 'info');
  appendLog(`Grid: ${ROWS} rows × ${COLS} cols`, 'info');
}


// =============================================================================
//  MOUSE INTERACTION
// =============================================================================

/**
 * getGridPos(event)
 * ──────────────────
 * Convert a mouse event's pixel position to a [row, col] grid position.
 * Uses canvas.getBoundingClientRect() to handle any CSS scaling.
 */
function getGridPos(e) {
  const canvas = document.getElementById('grid-canvas');
  const rect   = canvas.getBoundingClientRect();

  // Scale factor (in case CSS resizes the canvas element)
  const scaleX = canvas.width  / rect.width;
  const scaleY = canvas.height / rect.height;

  const col = Math.floor((e.clientX - rect.left) * scaleX / CELL);
  const row = Math.floor((e.clientY - rect.top)  * scaleY / CELL);

  return [row, col];
}

function onMouseDown(e) {
  if (isRunning) return;
  isMouseDown = true;
  const [row, col] = getGridPos(e);
  handleCellAction(row, col);
}

function onMouseMove(e) {
  if (!isMouseDown || isRunning) return;
  const [row, col] = getGridPos(e);
  // Only drag-draw walls, traffic, and erase (not start/end)
  if (['wall', 'traffic', 'erase'].includes(currentMode)) {
    handleCellAction(row, col);
  }
}

/**
 * handleCellAction(row, col)
 * ───────────────────────────
 * Apply the current draw mode to the cell at (row, col).
 */
function handleCellAction(row, col) {
  if (row < 0 || row >= ROWS || col < 0 || col >= COLS) return;

  switch (currentMode) {
    case 'start':
      placeStart(row, col); break;

    case 'end':
      placeEnd(row, col); break;

    case 'wall':
      // Don't overwrite start or end
      if (gridState[row][col] === 'start' || gridState[row][col] === 'end') return;
      wallSet.add(`${row},${col}`);
      delete weightMap[`${row},${col}`];
      setCellState(row, col, 'wall');
      break;

    case 'traffic':
      if (gridState[row][col] === 'start' || gridState[row][col] === 'end') return;
      weightMap[`${row},${col}`] = 4.0;   // heavy traffic cost
      wallSet.delete(`${row},${col}`);
      setCellState(row, col, 'traffic');
      break;

    case 'erase':
      if (gridState[row][col] === 'start' || gridState[row][col] === 'end') return;
      wallSet.delete(`${row},${col}`);
      delete weightMap[`${row},${col}`];
      setCellState(row, col, 'empty');
      break;
  }
}

/**
 * placeStart(row, col) / placeEnd(row, col)
 * ──────────────────────────────────────────
 * Move the start/end marker to a new position.
 * Clears the old position first.
 */
function placeStart(row, col) {
  if (startPos) {
    // Clear previous start (restore to empty or wall)
    const key = `${startPos[0]},${startPos[1]}`;
    setCellState(startPos[0], startPos[1],
      wallSet.has(key) ? 'wall' : 'empty');
  }
  startPos = [row, col];
  wallSet.delete(`${row},${col}`);
  setCellState(row, col, 'start');
}

function placeEnd(row, col) {
  if (endPos) {
    const key = `${endPos[0]},${endPos[1]}`;
    setCellState(endPos[0], endPos[1],
      wallSet.has(key) ? 'wall' : 'empty');
  }
  endPos = [row, col];
  wallSet.delete(`${row},${col}`);
  setCellState(row, col, 'end');
}


// =============================================================================
//  MODE + SPEED CONTROLS (called by HTML button onclick)
// =============================================================================

function setMode(mode) {
  currentMode = mode;
  // Remove 'active' from all mode buttons
  document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
  // Add 'active' to the clicked button
  document.getElementById(`mode-${mode}`).classList.add('active');
}


// =============================================================================
//  MAIN: RUN A* VISUALIZATION
// =============================================================================

/**
 * runVisualization()
 * ──────────────────
 * Called when user clicks "Run A*" button.
 *
 * Steps:
 *   1. Validate start + end are placed
 *   2. Build the request payload (grid config as JSON)
 *   3. POST to Flask /api/solve (Python runs A*)
 *   4. Receive JSON result
 *   5. Animate visited nodes → then path nodes
 */
async function runVisualization() {
  // ── Guard ──────────────────────────────────────────────────
  if (isRunning) return;
  if (!startPos || !endPos) {
    setStatus('Please place both START and END nodes first!');
    return;
  }

  isRunning = true;
  document.getElementById('btn-run').disabled = true;
  setStatus('Sending grid to Python... Running A*...');
  appendLog('Sending request to Flask /api/solve', 'info');

  clearPathCells();  // remove previous path visualization

  const t0 = Date.now();

  // ── Step 2: Build request payload ─────────────────────────
  // Collect all walls as [[r,c], ...] list
  const walls = Array.from(wallSet).map(key => {
    const [r, c] = key.split(',').map(Number);
    return [r, c];
  });

  const payload = {
    rows:    ROWS,
    cols:    COLS,
    start:   startPos,
    end:     endPos,
    walls:   walls,
    weights: weightMap,
    heuristic: document.getElementById('heuristic-select').value,
  };

  // ── Step 3: POST to Python Flask ───────────────────────────
  // fetch() sends an HTTP request to the Flask server.
  // The Python backend receives this, runs A*, and returns JSON.
  let result;
  try {
    const response = await fetch('/api/solve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),   // Python's request.get_json() reads this
    });
    result = await response.json();    // parse the JSON response

  } catch (err) {
    appendLog(`Network error: ${err.message}`, 'error');
    isRunning = false;
    document.getElementById('btn-run').disabled = false;
    return;
  }

  const serverTime = Date.now() - t0;
  appendLog(`Python response in ${serverTime}ms`, 'ok');
  appendLog(result.message, result.success ? 'ok' : 'error');

  // ── Step 4: Update header stats ───────────────────────────
  document.getElementById('h-time').textContent  = serverTime;
  document.getElementById('h-nodes').textContent = result.nodes_visited || '—';
  document.getElementById('h-cost').textContent  = result.path_cost     || '—';
  document.getElementById('h-path').textContent  = result.path?.length  || '—';

  // ── Step 5: Animate the result ────────────────────────────
  if (result.success) {
    setStatus('Animating A* search...');
    await animateResult(result);
    setStatus(`✓ Path found! ${result.path.length} steps, cost ${result.path_cost}`);
  } else {
    setStatus('✗ ' + result.message);
  }

  isRunning = false;
  document.getElementById('btn-run').disabled = false;
}


// =============================================================================
//  ANIMATION
// =============================================================================

/**
 * animateResult(result)
 * ──────────────────────
 * Plays back the A* search step by step:
 *   Phase 1: Animate "visited" nodes (blue) — shows algorithm exploring
 *   Phase 2: Animate "path" nodes (bright blue) — shows optimal route
 *
 * Uses async/await + sleep() to pause between each cell,
 * giving the browser time to repaint the canvas.
 *
 * The data comes from Python's AStarSolver:
 *   result.visited  = [[r,c], ...] in the order A* evaluated them
 *   result.path     = [[r,c], ...] the optimal route
 */
async function animateResult(result) {
  const visited = result.visited || [];
  const path    = result.path    || [];
  let   openIdx = 0;  // tracks position in open_history for live updates
  const openHist = result.open_history || [];

  // ── Phase 1: Animate visited nodes ─────────────────────────
  // Show each node A* evaluated, in the order it evaluated them.
  for (let i = 0; i < visited.length; i++) {
    const [r, c] = visited[i];

    // Don't overwrite start/end markers
    if (gridState[r][c] !== 'start' && gridState[r][c] !== 'end') {
      setCellState(r, c, 'visited');
    }

    // Update live node data panel every 5 steps (avoids DOM thrash)
    if (i % 5 === 0) {
      updateNodePanel(r, c, i, openHist.length - openIdx);
    }

    // Pause between steps — this is what makes the animation visible
    // animDelay = 0 means instant (no pause)
    if (animDelay > 0) await sleep(animDelay);
  }

  // ── Phase 2: Animate the optimal path ──────────────────────
  // Draw the final path on top of the visited overlay.
  setStatus('Drawing optimal path...');
  for (const [r, c] of path) {
    if (gridState[r][c] !== 'start' && gridState[r][c] !== 'end') {
      setCellState(r, c, 'path');
    }
    if (animDelay > 0) await sleep(animDelay * 0.5);  // path animates faster
  }

  appendLog(`Animation complete. Path: ${path.length} nodes`, 'ok');
}


/**
 * sleep(ms)
 * ─────────
 * Pause execution for `ms` milliseconds.
 * Returns a Promise — used with await to yield to the browser.
 *
 * Without this, the browser would compute all steps instantly
 * and only show the final result (no animation).
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}


// =============================================================================
//  MAZE GENERATION
// =============================================================================

/**
 * generateMaze(type)
 * ───────────────────
 * Calls Python's /api/generate-maze endpoint.
 * Python generates walls + weights and returns them.
 * We apply them to the frontend grid.
 */
async function generateMaze(type) {
  if (isRunning) return;

  appendLog(`Generating ${type} maze via Python...`, 'info');

  const response = await fetch('/api/generate-maze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type }),
  });
  const data = await response.json();

  // ── Apply maze to frontend ─────────────────────────────────
  resetGrid(true);  // clear without resetting start/end

  // Apply walls
  wallSet = new Set();
  for (const [r, c] of data.walls) {
    wallSet.add(`${r},${c}`);
    if (gridState[r][c] !== 'start' && gridState[r][c] !== 'end') {
      gridState[r][c] = 'wall';
    }
  }

  // Apply weights (traffic)
  weightMap = {};
  for (const [key, val] of Object.entries(data.weights || {})) {
    weightMap[key] = val;
    const [r, c] = key.split(',').map(Number);
    if (gridState[r][c] !== 'start' && gridState[r][c] !== 'end'
        && gridState[r][c] !== 'wall') {
      gridState[r][c] = 'traffic';
    }
  }

  // Place start and end from maze data
  placeStart(data.start[0], data.start[1]);
  placeEnd(data.end[0],     data.end[1]);

  drawGrid();
  appendLog(`Maze applied: ${data.walls.length} walls, ${Object.keys(data.weights||{}).length} traffic cells`, 'ok');
}


// =============================================================================
//  GRID RESET / CLEAR
// =============================================================================

/**
 * clearPath()
 * ────────────
 * Remove only the A* visualization (visited + path cells).
 * Keeps walls and traffic in place so user can re-run.
 */
function clearPath() {
  if (isRunning) return;

  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      if (gridState[r][c] === 'visited' || gridState[r][c] === 'path') {
        gridState[r][c] = 'empty';
      }
    }
  }

  drawGrid();
  resetHeaderStats();
  setStatus('Path cleared — ready to run again');
  appendLog('Path cleared', 'info');
}

/** Clear only path/visited cells (called before new animation) */
function clearPathCells() {
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      const s = gridState[r][c];
      if (s === 'visited' || s === 'path') {
        gridState[r][c] = 'empty';
      }
    }
  }
}

/**
 * resetGrid(keepStartEnd = false)
 * ─────────────────────────────────
 * Full reset — clears everything and rebuilds a blank grid.
 */
function resetGrid(keepStartEnd = false) {
  if (isRunning) return;

  wallSet   = new Set();
  weightMap = {};

  const prevStart = startPos;
  const prevEnd   = endPos;

  // Reset all cells to empty
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      gridState[r][c] = 'empty';
    }
  }

  startPos = null;
  endPos   = null;

  if (keepStartEnd && prevStart && prevEnd) {
    placeStart(prevStart[0], prevStart[1]);
    placeEnd(prevEnd[0],     prevEnd[1]);
  } else {
    placeStart(DEF_START[0], DEF_START[1]);
    placeEnd(DEF_END[0],     DEF_END[1]);
  }

  drawGrid();
  resetHeaderStats();
  setStatus('Grid reset — ready');
  appendLog('Grid reset', 'info');
}


// =============================================================================
//  UI HELPERS
// =============================================================================

function setStatus(msg) {
  document.getElementById('status-bar').textContent = msg;
}

function resetHeaderStats() {
  ['h-nodes', 'h-path', 'h-cost', 'h-time'].forEach(id => {
    document.getElementById(id).textContent = '—';
  });
}

/** Update the live node data panel in the right sidebar */
function updateNodePanel(r, c, visitedCount, openSize) {
  document.getElementById('n-pos').textContent  = `(${r}, ${c})`;
  document.getElementById('n-open').textContent = openSize;
  document.getElementById('n-g').textContent    = visitedCount;
}

/** Append a line to the response log terminal */
function appendLog(msg, cls = '') {
  const box  = document.getElementById('log-box');
  const line = document.createElement('div');
  line.className   = `log-line ${cls}`;
  const tag = cls === 'ok' ? 'OK  ' : cls === 'error' ? 'ERR ' : 'INFO';
  line.textContent = `[${tag}] ${msg}`;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
  // Keep max 60 lines
  while (box.children.length > 60) box.firstChild.remove();
}


// =============================================================================
//  BOOT
// =============================================================================
// Wait for DOM to be ready, then initialize everything.
document.addEventListener('DOMContentLoaded', initApp);
