/**
 * Tile rack rendering, drag-and-drop, and tap-to-select interaction.
 */

import { getLetterPoints } from "./constants.js";

/** @type {HTMLElement|null} */
let rackEl = null;

/** @type {string[]} */
let currentRack = [];

/** @type {number|null} Selected tile index for tap-to-place. */
let selectedTileIdx = null;

/** @type {Set<number>} Tile indices selected for exchange. */
let exchangeSelection = new Set();

/** @type {boolean} */
let exchangeMode = false;

/** @type {((tileIdx: number) => void)|null} */
let onTileSelect = null;

/** @type {((tileIndices: number[]) => void)|null} */
let onExchangeConfirm = null;

/**
 * Initialize the rack inside the given container.
 * @param {HTMLElement} container
 * @param {object} callbacks
 * @param {(tileIdx: number) => void} callbacks.onTileSelect
 * @param {(tileIndices: number[]) => void} callbacks.onExchangeConfirm
 */
export function initRack(container, callbacks) {
  onTileSelect = callbacks.onTileSelect;
  onExchangeConfirm = callbacks.onExchangeConfirm;

  rackEl = document.createElement("div");
  rackEl.className = "rack";
  rackEl.setAttribute("role", "list");
  rackEl.setAttribute("aria-label", "Your tile rack");
  container.appendChild(rackEl);
}

/**
 * Update the rack display.
 * @param {string[]} rack - array of letters (or "_" for blank)
 */
export function updateRack(rack) {
  if (!rackEl) return;
  currentRack = rack;

  /* Clear existing children safely */
  while (rackEl.firstChild) {
    rackEl.removeChild(rackEl.firstChild);
  }

  rack.forEach((letter, idx) => {
    const tile = document.createElement("div");
    tile.className = "rack-tile";
    tile.dataset.idx = String(idx);
    tile.setAttribute("role", "listitem");
    tile.setAttribute("draggable", "true");
    tile.setAttribute("tabindex", "0");

    if (letter === "_") {
      tile.classList.add("rack-tile--blank");
    }

    if (exchangeMode && exchangeSelection.has(idx)) {
      tile.classList.add("rack-tile--exchange-selected");
    } else if (!exchangeMode && selectedTileIdx === idx) {
      tile.classList.add("rack-tile--selected");
    }

    const letterSpan = document.createElement("span");
    letterSpan.className = "rack-tile__letter";
    letterSpan.textContent = letter === "_" ? " " : letter.toUpperCase();
    tile.appendChild(letterSpan);

    const points = getLetterPoints(letter);
    const pointsSpan = document.createElement("span");
    pointsSpan.className = "rack-tile__points";
    pointsSpan.textContent = String(points);
    tile.appendChild(pointsSpan);

    tile.addEventListener("click", () => _handleTileClick(idx));

    /* Drag-and-drop for desktop */
    tile.addEventListener("dragstart", (e) => {
      if (exchangeMode) {
        e.preventDefault();
        return;
      }
      selectedTileIdx = idx;
      e.dataTransfer.setData("text/plain", String(idx));
      e.dataTransfer.effectAllowed = "move";
      tile.classList.add("rack-tile--dragging");
      _refreshSelection();
    });

    tile.addEventListener("dragend", () => {
      tile.classList.remove("rack-tile--dragging");
    });

    tile.setAttribute(
      "aria-label",
      letter === "_"
        ? "Blank tile, 0 points"
        : `Letter ${letter.toUpperCase()}, ${points} points`
    );

    rackEl.appendChild(tile);
  });

  /* Exchange confirm button (shown only in exchange mode) */
  if (exchangeMode) {
    const confirmBtn = document.createElement("button");
    confirmBtn.className = "btn btn--exchange-confirm";
    confirmBtn.textContent = `Exchange ${exchangeSelection.size} tile${exchangeSelection.size !== 1 ? "s" : ""}`;
    confirmBtn.disabled = exchangeSelection.size === 0;
    confirmBtn.addEventListener("click", () => {
      if (onExchangeConfirm && exchangeSelection.size > 0) {
        onExchangeConfirm([...exchangeSelection]);
      }
    });
    rackEl.appendChild(confirmBtn);

    const cancelBtn = document.createElement("button");
    cancelBtn.className = "btn btn--exchange-cancel";
    cancelBtn.textContent = "Cancel";
    cancelBtn.addEventListener("click", () => {
      setExchangeMode(false);
    });
    rackEl.appendChild(cancelBtn);
  }
}

/**
 * Get the currently selected tile index.
 * @returns {number|null}
 */
export function getSelectedTileIdx() {
  return selectedTileIdx;
}

/** Get the letter at the selected tile index. */
export function getSelectedTileLetter() {
  if (selectedTileIdx === null || selectedTileIdx >= currentRack.length) return null;
  return currentRack[selectedTileIdx];
}

/** Clear tile selection. */
export function clearSelection() {
  selectedTileIdx = null;
  _refreshSelection();
}

/**
 * Toggle exchange mode on/off.
 * @param {boolean} enabled
 */
export function setExchangeMode(enabled) {
  exchangeMode = enabled;
  exchangeSelection.clear();
  selectedTileIdx = null;
  if (rackEl) {
    rackEl.classList.toggle("rack--exchange-mode", enabled);
  }
  updateRack(currentRack);
}

/** @returns {boolean} */
export function isExchangeMode() {
  return exchangeMode;
}

/**
 * Handle a tile click -- either select for placement or toggle exchange selection.
 * @param {number} idx
 */
function _handleTileClick(idx) {
  if (exchangeMode) {
    if (exchangeSelection.has(idx)) {
      exchangeSelection.delete(idx);
    } else {
      exchangeSelection.add(idx);
    }
    updateRack(currentRack);
    return;
  }

  if (selectedTileIdx === idx) {
    selectedTileIdx = null;
  } else {
    selectedTileIdx = idx;
  }
  _refreshSelection();

  if (onTileSelect && selectedTileIdx !== null) {
    onTileSelect(selectedTileIdx);
  }
}

/** Refresh the visual selection state without rebuilding DOM. */
function _refreshSelection() {
  if (!rackEl) return;
  rackEl.querySelectorAll(".rack-tile").forEach((tile) => {
    const idx = parseInt(tile.dataset.idx, 10);
    tile.classList.toggle("rack-tile--selected", !exchangeMode && selectedTileIdx === idx);
    tile.classList.toggle(
      "rack-tile--exchange-selected",
      exchangeMode && exchangeSelection.has(idx)
    );
  });
}
