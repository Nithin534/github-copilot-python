// Client-side rendering and interaction for the Flask-backed Sudoku

const SIZE = 9;

const state = {
  puzzle: null,       // last puzzle grid returned by /new (0 = empty)
  prefilledMask: null, // 9x9 bool grid: true = cell was given, locked
  hintedMask: null,    // 9x9 bool grid: true = filled in by a hint, locked
  difficulty: 'medium',
  hintsUsed: 0,
  timerSeconds: 0,
  timerHandle: null,
  gameActive: false,
};

// ---------------------------------------------------------------------------
// DOM references
// ---------------------------------------------------------------------------

const boardEl = document.getElementById('sudoku-board');
const difficultySelect = document.getElementById('difficulty-select');
const newGameBtn = document.getElementById('new-game');
const checkBtn = document.getElementById('check-solution');
const hintBtn = document.getElementById('hint-button');
const themeToggleBtn = document.getElementById('theme-toggle');
const timerEl = document.getElementById('timer');
const messageEl = document.getElementById('message');
const hintsUsedEl = document.getElementById('hints-used');

const modalEl = document.getElementById('completion-modal');
const completionSummaryEl = document.getElementById('completion-summary');
const playerNameInput = document.getElementById('player-name-input');
const saveScoreBtn = document.getElementById('save-score');
const closeModalBtn = document.getElementById('close-modal');

// ---------------------------------------------------------------------------
// Board rendering
// ---------------------------------------------------------------------------

function buildBoardDom() {
  boardEl.innerHTML = '';
  for (let row = 0; row < SIZE; row++) {
    for (let col = 0; col < SIZE; col++) {
      const input = document.createElement('input');
      input.type = 'text';
      input.inputMode = 'numeric';
      input.maxLength = 1;
      input.className = 'sudoku-cell';
      input.dataset.row = row;
      input.dataset.col = col;

      // Alternating 3x3 box shading: boxes at (0,0),(0,2),(1,1),(2,0),(2,2)
      const boxRow = Math.floor(row / 3);
      const boxCol = Math.floor(col / 3);
      if ((boxRow + boxCol) % 2 === 0) {
        input.classList.add('box-alt');
      }

      boardEl.appendChild(input);
    }
  }
}

function cellAt(row, col) {
  return boardEl.querySelector(
    `.sudoku-cell[data-row="${row}"][data-col="${col}"]`
  );
}

function renderPuzzle(puzzle) {
  state.puzzle = puzzle;
  state.prefilledMask = puzzle.map((r) => r.map((v) => v !== 0));
  state.hintedMask = puzzle.map((r) => r.map(() => false));

  for (let row = 0; row < SIZE; row++) {
    for (let col = 0; col < SIZE; col++) {
      const cell = cellAt(row, col);
      const value = puzzle[row][col];

      cell.classList.remove('prefilled', 'hinted', 'incorrect', 'conflict');
      cell.value = value !== 0 ? value : '';
      cell.disabled = value !== 0;
      if (value !== 0) {
        cell.classList.add('prefilled');
      }
    }
  }
}

function readBoardFromDom() {
  const board = [];
  for (let row = 0; row < SIZE; row++) {
    board[row] = [];
    for (let col = 0; col < SIZE; col++) {
      const raw = cellAt(row, col).value;
      board[row][col] = raw ? parseInt(raw, 10) : 0;
    }
  }
  return board;
}

function clearFeedbackStyling() {
  boardEl.querySelectorAll('.sudoku-cell').forEach((cell) => {
    cell.classList.remove('incorrect', 'conflict');
  });
}

// ---------------------------------------------------------------------------
// Timer
// ---------------------------------------------------------------------------

function startTimer() {
  stopTimer();
  state.timerSeconds = 0;
  updateTimerDisplay();
  state.timerHandle = setInterval(() => {
    state.timerSeconds += 1;
    updateTimerDisplay();
  }, 1000);
}

function stopTimer() {
  if (state.timerHandle) {
    clearInterval(state.timerHandle);
    state.timerHandle = null;
  }
}

function updateTimerDisplay() {
  const minutes = Math.floor(state.timerSeconds / 60);
  const seconds = state.timerSeconds % 60;
  timerEl.textContent = `Time: ${minutes}:${String(seconds).padStart(2, '0')}`;
}

function formatTime(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

function showMessage(text, kind) {
  messageEl.textContent = text;
  messageEl.classList.remove('success', 'error');
  if (kind) {
    messageEl.classList.add(kind);
  }
}

function updateHintsUsedDisplay() {
  hintsUsedEl.textContent = state.hintsUsed > 0
    ? `Hints used: ${state.hintsUsed}`
    : '';
}

// ---------------------------------------------------------------------------
// Game actions
// ---------------------------------------------------------------------------

async function newGame() {
  state.difficulty = difficultySelect.value;
  state.hintsUsed = 0;
  updateHintsUsedDisplay();
  showMessage('', null);
  clearFeedbackStyling();

  const res = await fetch(`/new?difficulty=${encodeURIComponent(state.difficulty)}`);
  const data = await res.json();

  if (data.error) {
    showMessage(data.error, 'error');
    return;
  }

  buildBoardDom();
  renderPuzzle(data.puzzle);
  state.gameActive = true;
  startTimer();
}

async function checkSolution() {
  if (!state.gameActive) return;

  const board = readBoardFromDom();
  const res = await fetch('/check', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ board }),
  });
  const data = await res.json();

  if (data.error) {
    showMessage(data.error, 'error');
    return;
  }

  clearFeedbackStyling();

  const incorrectSet = new Set((data.incorrect || []).map(([r, c]) => `${r}-${c}`));
  const conflictSet = new Set((data.conflicts || []).map(([r, c]) => `${r}-${c}`));

  for (let row = 0; row < SIZE; row++) {
    for (let col = 0; col < SIZE; col++) {
      const key = `${row}-${col}`;
      const cell = cellAt(row, col);
      if (incorrectSet.has(key)) {
        cell.classList.add('incorrect');
      } else if (conflictSet.has(key)) {
        cell.classList.add('conflict');
      }
    }
  }

  if (data.solved) {
    handlePuzzleSolved();
  } else if (incorrectSet.size === 0 && conflictSet.size === 0) {
    showMessage('Looks good so far — keep going!', 'success');
  } else {
    showMessage('Some cells need another look.', 'error');
  }
}

async function requestHint() {
  if (!state.gameActive) return;

  const board = readBoardFromDom();
  const res = await fetch('/hint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ board }),
  });
  const data = await res.json();

  if (data.error) {
    showMessage(data.error, 'error');
    return;
  }

  const { row, col, value, hints_used: hintsUsed } = data;
  const cell = cellAt(row, col);
  cell.value = value;
  cell.disabled = true;
  cell.classList.remove('incorrect', 'conflict');
  cell.classList.add('hinted');
  state.hintedMask[row][col] = true;

  if (typeof hintsUsed === 'number') {
    state.hintsUsed = hintsUsed;
  } else {
    state.hintsUsed += 1;
  }
  updateHintsUsedDisplay();
}

function handlePuzzleSolved() {
  state.gameActive = false;
  stopTimer();
  showMessage('Solved! 🎉', 'success');

  completionSummaryEl.textContent =
    `You solved the ${state.difficulty} puzzle in ${formatTime(state.timerSeconds)} ` +
    `using ${state.hintsUsed} hint${state.hintsUsed === 1 ? '' : 's'}.`;
  playerNameInput.value = '';
  modalEl.classList.remove('hidden');
}

// ---------------------------------------------------------------------------
// Dark mode
// ---------------------------------------------------------------------------

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  themeToggleBtn.textContent = theme === 'dark' ? '☀️' : '🌙';
  localStorage.setItem('sudoku-theme', theme);
}

function initTheme() {
  const saved = localStorage.getItem('sudoku-theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  applyTheme(saved || (prefersDark ? 'dark' : 'light'));
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  applyTheme(current === 'dark' ? 'light' : 'dark');
}

// ---------------------------------------------------------------------------
// Event wiring (event delegation on the board, one listener)
// ---------------------------------------------------------------------------

boardEl.addEventListener('input', (event) => {
  const target = event.target;
  if (!target.classList.contains('sudoku-cell')) return;

  const cleaned = target.value.replace(/[^1-9]/g, '');
  target.value = cleaned;
  target.classList.remove('incorrect', 'conflict');
});

newGameBtn.addEventListener('click', newGame);
checkBtn.addEventListener('click', checkSolution);
hintBtn.addEventListener('click', requestHint);
themeToggleBtn.addEventListener('click', toggleTheme);

closeModalBtn.addEventListener('click', () => {
  modalEl.classList.add('hidden');
});

saveScoreBtn.addEventListener('click', () => {
  const name = playerNameInput.value.trim() || 'Anonymous';
  // Leaderboard persistence (localStorage) is wired up in a later step.
  console.log('Score to save:', {
    name,
    time: state.timerSeconds,
    difficulty: state.difficulty,
    hints: state.hintsUsed,
  });
  modalEl.classList.add('hidden');
});

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

window.addEventListener('load', () => {
  initTheme();
  newGame();
});
