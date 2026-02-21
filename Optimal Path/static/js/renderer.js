/**
 * FILE: static/js/renderer.js
 * ROLE: Draws the grid on the HTML5 Canvas.
 *
 * This file handles ALL canvas drawing:
 *   - The grid lines
 *   - Cell colors (wall, road, visited, open, path, traffic)
 *   - Start and end markers
 *
 * It reads grid state from the `gridState` 2D array
 * maintained by app.js.
 *
 * CELL STATE VALUES:
 *   'empty'   → normal road (dark grey)
 *   'wall'    → building (near black)
 *   'start'   → start node (green circle)
 *   'end'     → end node (orange circle)
 *   'visited' → A* evaluated (dark blue)
 *   'open'    → A* open set (dark green)
 *   'path'    → optimal path (bright blue)
 *   'traffic' → weighted road (dark amber)
 */

const canvas = document.getElementById('grid-canvas');
const ctx    = canvas.getContext('2d');

// Cell pixel size — calculated in initRenderer()
let CELL = 28;

// Colors matching CSS variables
const COLORS = {
  empty:   '#1C2128',
  wall:    '#090D11',
  start:   '#3FB950',
  end:     '#F78166',
  visited: '#1a3a5c',
  open:    '#1a3a2a',
  path:    '#1F6FEB',
  traffic: '#3d2a00',
  grid:    'rgba(48, 54, 61, 0.6)',
  startGlow: '#3FB950',
  endGlow:   '#F78166',
  pathGlow:  '#1F6FEB',
};


/**
 * initRenderer()
 * ──────────────
 * Size the canvas to fit the map container and compute CELL size.
 * Called on page load and window resize.
 */
function initRenderer() {
  const wrap = document.querySelector('.map-wrap');
  const rect = wrap.getBoundingClientRect();

  // Calculate cell size to fit grid within container
  // Subtract some padding so the grid doesn't touch the edges
  CELL = Math.floor(Math.min(
    (rect.width  - 40) / COLS,
    (rect.height - 60) / ROWS
  ));

  // Set canvas pixel size to exact grid dimensions
  canvas.width  = COLS * CELL;
  canvas.height = ROWS * CELL;
}


/**
 * drawGrid()
 * ──────────
 * Full repaint of the entire grid canvas.
 * Iterates over every cell and draws it based on its current state.
 */
function drawGrid() {
  // 1. Clear canvas
  ctx.fillStyle = COLORS.empty;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // 2. Draw every cell
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      drawCell(r, c);
    }
  }
}


/**
 * drawCell(row, col)
 * ──────────────────
 * Draw a single cell based on its state in gridState[row][col].
 */
function drawCell(row, col) {
  const x     = col * CELL;   // pixel x position
  const y     = row * CELL;   // pixel y position
  const state = gridState[row][col];
  const pad   = 1;            // 1px gap between cells (grid line effect)

  // ── Determine fill color ──────────────────────────────────
  switch (state) {
    case 'wall':
      drawWall(x, y); return;

    case 'start':
      ctx.fillStyle = '#0D1117';
      ctx.fillRect(x + pad, y + pad, CELL - pad*2, CELL - pad*2);
      drawMarker(x, y, COLORS.start, 'S'); return;

    case 'end':
      ctx.fillStyle = '#0D1117';
      ctx.fillRect(x + pad, y + pad, CELL - pad*2, CELL - pad*2);
      drawMarker(x, y, COLORS.end, 'E'); return;

    case 'path':
      // Bright blue fill + subtle glow dot
      ctx.fillStyle = 'rgba(31, 111, 235, 0.25)';
      ctx.fillRect(x + pad, y + pad, CELL - pad*2, CELL - pad*2);
      ctx.shadowColor = COLORS.pathGlow;
      ctx.shadowBlur  = 8;
      ctx.fillStyle   = COLORS.path;
      const ps = Math.max(4, CELL * 0.35);
      ctx.fillRect(x + (CELL-ps)/2, y + (CELL-ps)/2, ps, ps);
      ctx.shadowBlur = 0;
      return;

    case 'visited':
      ctx.fillStyle = COLORS.visited;
      ctx.fillRect(x + pad, y + pad, CELL - pad*2, CELL - pad*2);
      // Tiny center dot
      ctx.fillStyle = 'rgba(30, 100, 180, 0.5)';
      ctx.fillRect(x + CELL/2 - 2, y + CELL/2 - 2, 4, 4);
      return;

    case 'open':
      ctx.fillStyle = COLORS.open;
      ctx.fillRect(x + pad, y + pad, CELL - pad*2, CELL - pad*2);
      ctx.fillStyle = 'rgba(30, 150, 70, 0.4)';
      ctx.fillRect(x + CELL/2 - 2, y + CELL/2 - 2, 4, 4);
      return;

    case 'traffic':
      ctx.fillStyle = COLORS.traffic;
      ctx.fillRect(x + pad, y + pad, CELL - pad*2, CELL - pad*2);
      ctx.fillStyle = 'rgba(180, 100, 0, 0.5)';
      ctx.font = `${Math.max(8, CELL * 0.45)}px sans-serif`;
      ctx.textAlign    = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('⚡', x + CELL/2, y + CELL/2);
      return;

    default: // 'empty' — normal road
      ctx.fillStyle = COLORS.empty;
      ctx.fillRect(x + pad, y + pad, CELL - pad*2, CELL - pad*2);
      return;
  }
}


/**
 * drawWall(x, y)
 * ──────────────
 * Draw a building cell — solid near-black fill.
 */
function drawWall(x, y) {
  ctx.fillStyle = '#111827';
  ctx.fillRect(x, y, CELL, CELL);
  ctx.fillStyle = '#0D1117';
  ctx.fillRect(x + 1, y + 1, CELL - 2, CELL - 2);
  // Subtle cross-hatch texture
  ctx.strokeStyle = 'rgba(255,255,255,0.03)';
  ctx.lineWidth = 0.5;
  ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x+CELL, y+CELL); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(x+CELL, y); ctx.lineTo(x, y+CELL); ctx.stroke();
}


/**
 * drawMarker(x, y, color, label)
 * ────────────────────────────────
 * Draw a glowing circular marker (used for Start and End).
 */
function drawMarker(x, y, color, label) {
  const cx = x + CELL / 2;
  const cy = y + CELL / 2;
  const r  = CELL * 0.4;

  ctx.shadowColor = color;
  ctx.shadowBlur  = 14;
  ctx.fillStyle   = color;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;

  ctx.fillStyle    = '#0D1117';
  ctx.font         = `bold ${Math.max(9, CELL * 0.45)}px Nunito, sans-serif`;
  ctx.textAlign    = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(label, cx, cy);
}


/**
 * setCellState(row, col, state)
 * ──────────────────────────────
 * Update a single cell's state and immediately redraw just that cell.
 * Much faster than calling drawGrid() for every small update.
 */
function setCellState(row, col, state) {
  if (row < 0 || row >= ROWS || col < 0 || col >= COLS) return;
  gridState[row][col] = state;
  drawCell(row, col);
}
