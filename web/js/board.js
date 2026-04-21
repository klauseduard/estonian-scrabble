/**
 * Board rendering and interaction for the 15x15 Scrabble grid.
 */

import { getPremiumType, getLetterPoints, ESTONIAN_LETTERS } from "./constants.js";

/**
 * @typedef {object} BoardState
 * @property {(string|null)[][]} board - 15x15 array of letters
 * @property {{row: number, col: number}[]} currentTurnTiles - tiles placed this turn
 * @property {boolean} isMyTurn
 */

/** @type {HTMLElement|null} */
let boardEl = null;

/** @type {((row: number, col: number) => void)|null} */
let onCellClick = null;

/** @type {((row: number, col: number) => void)|null} */
let onCellRightClick = null;

/** @type {((letter: string) => void)|null} */
let pendingBlankCallback = null;

/**
 * Initialize the board grid inside the given container.
 * @param {HTMLElement} container
 * @param {object} callbacks
 * @param {(row: number, col: number) => void} callbacks.onCellClick
 * @param {(row: number, col: number) => void} callbacks.onCellRightClick
 */
export function initBoard(container, callbacks) {
  onCellClick = callbacks.onCellClick;
  onCellRightClick = callbacks.onCellRightClick;

  boardEl = document.createElement("div");
  boardEl.className = "board";
  boardEl.setAttribute("role", "grid");
  boardEl.setAttribute("aria-label", "Scrabble board, 15 by 15");

  for (let row = 0; row < 15; row++) {
    for (let col = 0; col < 15; col++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.dataset.row = String(row);
      cell.dataset.col = String(col);
      cell.setAttribute("role", "gridcell");

      const premium = getPremiumType(row, col);
      if (premium) {
        cell.classList.add(`cell--${premium.toLowerCase()}`);
        const label = document.createElement("span");
        label.className = "cell__label";
        label.textContent = premium;
        cell.appendChild(label);
      }

      if (row === 7 && col === 7) {
        cell.classList.add("cell--center");
        if (!premium || cell.querySelector(".cell__label")) {
          /* Center star — add star overlay */
          const star = document.createElement("span");
          star.className = "cell__star";
          star.textContent = "\u2605";
          cell.appendChild(star);
        }
      }

      cell.addEventListener("click", () => _handleCellClick(row, col));
      cell.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        _handleCellRightClick(row, col);
      });

      /* Drop target for drag-and-drop */
      cell.addEventListener("dragover", (e) => {
        e.preventDefault();
        cell.classList.add("cell--drop-target");
      });
      cell.addEventListener("dragleave", () => {
        cell.classList.remove("cell--drop-target");
      });
      cell.addEventListener("drop", (e) => {
        e.preventDefault();
        cell.classList.remove("cell--drop-target");
        _handleCellClick(row, col);
      });

      boardEl.appendChild(cell);
    }
  }

  container.appendChild(boardEl);
}

/**
 * Update the board display from game state.
 * @param {BoardState} state
 */
export function updateBoard(state) {
  if (!boardEl) return;

  const turnTileSet = new Set(
    state.currentTurnTiles.map((t) => `${t.row},${t.col}`)
  );

  const cells = boardEl.querySelectorAll(".cell");
  cells.forEach((cell) => {
    const row = parseInt(cell.dataset.row, 10);
    const col = parseInt(cell.dataset.col, 10);
    const letter = state.board[row][col];
    const key = `${row},${col}`;

    /* Remove any existing tile from the cell */
    const existingTile = cell.querySelector(".board-tile");
    if (existingTile) existingTile.remove();

    /* Show/hide premium label and star */
    const label = cell.querySelector(".cell__label");
    const star = cell.querySelector(".cell__star");

    if (letter) {
      if (label) label.style.display = "none";
      if (star) star.style.display = "none";

      const tile = document.createElement("div");
      tile.className = "board-tile";
      if (turnTileSet.has(key)) {
        tile.classList.add("board-tile--current-turn");
      }

      const letterSpan = document.createElement("span");
      letterSpan.className = "board-tile__letter";
      letterSpan.textContent = letter.toUpperCase();
      tile.appendChild(letterSpan);

      const points = getLetterPoints(letter);
      const pointsSpan = document.createElement("span");
      pointsSpan.className = "board-tile__points";
      pointsSpan.textContent = String(points);
      tile.appendChild(pointsSpan);

      cell.appendChild(tile);

      cell.setAttribute(
        "aria-label",
        `Row ${row + 1}, Column ${col + 1}, letter ${letter.toUpperCase()}, ${points} points`
      );
    } else {
      if (label) label.style.display = "";
      if (star) star.style.display = "";

      const premium = getPremiumType(row, col);
      const premiumLabel = premium ? `, ${premium} premium square` : "";
      cell.setAttribute(
        "aria-label",
        `Row ${row + 1}, Column ${col + 1}${premiumLabel}, empty`
      );
    }
  });
}

/**
 * Show the blank tile letter picker modal.
 * @param {(letter: string) => void} callback - called with the chosen letter
 */
export function showBlankPicker(callback) {
  pendingBlankCallback = callback;

  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "blank-picker-overlay";

  const modal = document.createElement("div");
  modal.className = "modal blank-picker";

  const title = document.createElement("h2");
  title.textContent = "Choose a letter for the blank tile";
  modal.appendChild(title);

  const grid = document.createElement("div");
  grid.className = "blank-picker__grid";

  for (const letter of ESTONIAN_LETTERS) {
    const btn = document.createElement("button");
    btn.className = "blank-picker__letter";
    btn.textContent = letter;
    btn.setAttribute("aria-label", `Select letter ${letter}`);
    btn.addEventListener("click", () => {
      _closeBlankPicker();
      if (pendingBlankCallback) {
        pendingBlankCallback(letter.toLowerCase());
        pendingBlankCallback = null;
      }
    });
    grid.appendChild(btn);
  }

  modal.appendChild(grid);
  overlay.appendChild(modal);

  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) {
      _closeBlankPicker();
      pendingBlankCallback = null;
    }
  });

  document.body.appendChild(overlay);
}

function _closeBlankPicker() {
  const overlay = document.getElementById("blank-picker-overlay");
  if (overlay) overlay.remove();
}

function _handleCellClick(row, col) {
  if (onCellClick) onCellClick(row, col);
}

function _handleCellRightClick(row, col) {
  if (onCellRightClick) onCellRightClick(row, col);
}
