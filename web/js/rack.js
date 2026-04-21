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

/** @type {number|null} Index of tile being dragged within the rack for reordering. */
let reorderDragIdx = null;

/** @type {string[]} Locally ordered rack — survives server state updates. */
let localRackOrder = [];

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
 * Reconcile server rack with local order.
 *
 * When the server sends a new rack (e.g. after drawing tiles), we want to
 * preserve the player's manual ordering for tiles that are still present,
 * and append any newly drawn tiles at the end.
 *
 * @param {string[]} serverRack
 * @returns {string[]} merged rack in local order
 */
function _reconcileRackOrder(serverRack) {
  /* Build a frequency map of the server rack */
  const serverCounts = new Map();
  for (const letter of serverRack) {
    serverCounts.set(letter, (serverCounts.get(letter) || 0) + 1);
  }

  /* Keep tiles from local order that still exist in server rack */
  const result = [];
  const usedCounts = new Map();
  for (const letter of localRackOrder) {
    const available = (serverCounts.get(letter) || 0) - (usedCounts.get(letter) || 0);
    if (available > 0) {
      result.push(letter);
      usedCounts.set(letter, (usedCounts.get(letter) || 0) + 1);
    }
  }

  /* Append any new tiles from server that weren't in local order */
  for (const letter of serverRack) {
    const used = usedCounts.get(letter) || 0;
    const needed = (serverCounts.get(letter) || 0);
    if (used < needed) {
      result.push(letter);
      usedCounts.set(letter, used + 1);
    }
  }

  return result;
}

/**
 * Update the rack display.
 * @param {string[]} rack - array of letters (or "_" for blank)
 */
export function updateRack(rack) {
  if (!rackEl) return;

  /* Reconcile with local ordering */
  if (localRackOrder.length === 0) {
    localRackOrder = [...rack];
  } else {
    localRackOrder = _reconcileRackOrder(rack);
  }
  currentRack = localRackOrder;

  /* Clear existing children safely */
  while (rackEl.firstChild) {
    rackEl.removeChild(rackEl.firstChild);
  }

  currentRack.forEach((letter, idx) => {
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

    /* Drag-and-drop: reorder within rack or place on board */
    tile.addEventListener("dragstart", (e) => {
      if (exchangeMode) {
        e.preventDefault();
        return;
      }
      reorderDragIdx = idx;
      selectedTileIdx = idx;
      e.dataTransfer.setData("text/plain", String(idx));
      e.dataTransfer.effectAllowed = "move";
      tile.classList.add("rack-tile--dragging");
      _refreshSelection();
    });

    tile.addEventListener("dragend", () => {
      tile.classList.remove("rack-tile--dragging");
      reorderDragIdx = null;
    });

    tile.addEventListener("dragover", (e) => {
      if (reorderDragIdx === null || reorderDragIdx === idx) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      tile.classList.add("rack-tile--drop-target");
    });

    tile.addEventListener("dragleave", () => {
      tile.classList.remove("rack-tile--drop-target");
    });

    tile.addEventListener("drop", (e) => {
      e.preventDefault();
      e.stopPropagation();
      tile.classList.remove("rack-tile--drop-target");
      if (reorderDragIdx === null || reorderDragIdx === idx) return;
      _reorderTile(reorderDragIdx, idx);
      reorderDragIdx = null;
    });

    /* Touch reorder: long-press to drag within rack */
    let touchTimer = null;
    let touchReordering = false;

    tile.addEventListener("touchstart", (e) => {
      if (exchangeMode) return;
      touchTimer = setTimeout(() => {
        touchReordering = true;
        reorderDragIdx = idx;
        tile.classList.add("rack-tile--dragging");
      }, 400);
    }, { passive: true });

    tile.addEventListener("touchmove", (e) => {
      if (touchTimer) {
        clearTimeout(touchTimer);
        touchTimer = null;
      }
      if (!touchReordering) return;
      e.preventDefault();
      const touch = e.touches[0];
      const target = document.elementFromPoint(touch.clientX, touch.clientY);
      const targetTile = target?.closest?.(".rack-tile");
      /* Highlight drop target */
      rackEl.querySelectorAll(".rack-tile--drop-target").forEach(
        (el) => el.classList.remove("rack-tile--drop-target")
      );
      if (targetTile && targetTile.dataset.idx !== String(idx)) {
        targetTile.classList.add("rack-tile--drop-target");
      }
    });

    tile.addEventListener("touchend", (e) => {
      if (touchTimer) {
        clearTimeout(touchTimer);
        touchTimer = null;
      }
      if (!touchReordering) return;
      touchReordering = false;
      tile.classList.remove("rack-tile--dragging");
      const touch = e.changedTouches[0];
      const target = document.elementFromPoint(touch.clientX, touch.clientY);
      const targetTile = target?.closest?.(".rack-tile");
      if (targetTile) {
        const targetIdx = parseInt(targetTile.dataset.idx, 10);
        if (targetIdx !== idx) {
          _reorderTile(idx, targetIdx);
        }
      }
      rackEl.querySelectorAll(".rack-tile--drop-target").forEach(
        (el) => el.classList.remove("rack-tile--drop-target")
      );
      reorderDragIdx = null;
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
 * Move a tile from one rack position to another (insert before target).
 * @param {number} fromIdx
 * @param {number} toIdx
 */
function _reorderTile(fromIdx, toIdx) {
  const tile = localRackOrder.splice(fromIdx, 1)[0];
  localRackOrder.splice(toIdx, 0, tile);
  selectedTileIdx = null;
  currentRack = localRackOrder;
  updateRack(currentRack);
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

/** Reset local rack ordering (call when starting a new game). */
export function resetRackOrder() {
  localRackOrder = [];
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
