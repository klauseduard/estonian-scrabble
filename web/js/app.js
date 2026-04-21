/**
 * Entry point for Estonian Scrabble web frontend.
 * Handles view routing (lobby <-> game) and orchestrates all modules.
 */

import ScrabbleWebSocket from "./websocket.js";
import { initBoard, updateBoard, showBlankPicker } from "./board.js";
import {
  initRack,
  updateRack,
  getSelectedTileIdx,
  getSelectedTileLetter,
  clearSelection,
  setExchangeMode,
  isExchangeMode,
  resetRackOrder,
} from "./rack.js";

/* ------------------------------------------------------------------ */
/*  State                                                              */
/* ------------------------------------------------------------------ */

/** @type {ScrabbleWebSocket} */
let ws;

/** @type {number|null} Our player index in the room. */
let myPlayerIndex = null;

/** @type {string|null} Current room code. */
let roomCode = null;

/** @type {boolean} Whether we are the host (first player). */
let isHost = false;

/** @type {object|null} Latest game state from the server. */
let gameState = null;

/** @type {string[]} Player names in the waiting room. */
let waitingPlayers = [];

/** @type {number|null} Previous current_player_index — used to detect turn changes. */
let prevCurrentPlayerIdx = null;

/** @type {boolean} Whether the game has started (to suppress initial notification). */
let gameHasStarted = false;

const DEFAULT_TITLE = "Eesti Scrabble";

/* ------------------------------------------------------------------ */
/*  DOM references                                                     */
/* ------------------------------------------------------------------ */

const lobbyView = document.getElementById("lobby-view");
const waitingView = document.getElementById("waiting-view");
const gameView = document.getElementById("game-view");
const gameOverOverlay = document.getElementById("game-over-overlay");

/* Lobby elements */
const nameInput = document.getElementById("player-name");
const createBtn = document.getElementById("create-btn");
const roomCodeInput = document.getElementById("room-code-input");
const joinBtn = document.getElementById("join-btn");
const lobbyError = document.getElementById("lobby-error");

/* Waiting room elements */
const waitingRoomCode = document.getElementById("waiting-room-code");
const waitingPlayerList = document.getElementById("waiting-player-list");
const startGameBtn = document.getElementById("start-game-btn");
const copyCodeBtn = document.getElementById("copy-code-btn");

/* Game elements */
const boardContainer = document.getElementById("board-container");
const rackContainer = document.getElementById("rack-container");
const submitBtn = document.getElementById("submit-btn");
const passBtn = document.getElementById("pass-btn");
const exchangeBtn = document.getElementById("exchange-btn");
const scorePanel = document.getElementById("score-panel");
const gameInfoPanel = document.getElementById("game-info-panel");
const turnIndicator = document.getElementById("turn-indicator");
const tilesRemaining = document.getElementById("tiles-remaining");
const scorePreview = document.getElementById("score-preview");
const errorToast = document.getElementById("error-toast");

/* Game over elements */
const gameOverScores = document.getElementById("game-over-scores");
const playAgainBtn = document.getElementById("play-again-btn");
const leaveBtn = document.getElementById("leave-btn");

/* Chat elements */
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const chatSendBtn = document.getElementById("chat-send");

/* ------------------------------------------------------------------ */
/*  View routing                                                       */
/* ------------------------------------------------------------------ */

/** Show only the specified view. */
function showView(view) {
  lobbyView.classList.add("hidden");
  waitingView.classList.add("hidden");
  gameView.classList.add("hidden");
  gameOverOverlay.classList.add("hidden");
  view.classList.remove("hidden");
}

/* ------------------------------------------------------------------ */
/*  WebSocket setup                                                    */
/* ------------------------------------------------------------------ */

async function connectWebSocket() {
  ws = new ScrabbleWebSocket();
  ws.onMessage(handleServerMessage);
  try {
    await ws.connect();
  } catch {
    showError("Could not connect to server. Please try again.");
  }
}

/**
 * Dispatch incoming server messages to the appropriate handler.
 * @param {object} msg
 */
function handleServerMessage(msg) {
  switch (msg.type) {
    case "room_created":
      _onRoomCreated(msg);
      break;
    case "room_joined":
      _onRoomJoined(msg);
      break;
    case "player_joined":
      _onPlayerJoined(msg);
      break;
    case "player_left":
      _onPlayerLeft(msg);
      break;
    case "game_started":
      _onGameStarted(msg);
      break;
    case "game_state":
      _onGameState(msg);
      break;
    case "game_over":
      _onGameOver(msg);
      break;
    case "chat":
      _onChat(msg);
      break;
    case "error":
      showError(msg.message);
      break;
    case "connection_lost":
      showError("Ühendus katkes. Palun värskenda lehte.");
      break;
    default:
      console.warn("Unknown message type:", msg.type);
  }
}

/* ------------------------------------------------------------------ */
/*  Message handlers                                                   */
/* ------------------------------------------------------------------ */

function _onRoomCreated(msg) {
  roomCode = msg.room_code;
  myPlayerIndex = msg.player_index;
  isHost = true;
  waitingPlayers = msg.players || [nameInput.value.trim() || "Mängija 1"];
  _showWaitingRoom();
}

function _onRoomJoined(msg) {
  roomCode = msg.room_code;
  myPlayerIndex = msg.player_index;
  isHost = false;
  waitingPlayers = msg.players || [nameInput.value.trim() || "Mängija"];
  _showWaitingRoom();
}

function _onPlayerJoined(msg) {
  waitingPlayers.push(msg.player_name);
  _renderWaitingPlayers();
  _playTurnSound();
  _showLastMoveBanner({
    action: "joined",
    player_name: msg.player_name,
  });
}

function _onPlayerLeft(msg) {
  /* We don't know which player left; update count */
  while (waitingPlayers.length > msg.player_count) {
    waitingPlayers.pop();
  }
  _renderWaitingPlayers();
}

function _onGameStarted(msg) {
  const name = msg.first_player || "?";
  _showLastMoveBanner({
    action: "started",
    player_name: name,
  });
  _playTurnSound();
}

function _onGameState(msg) {
  gameState = msg;
  /* Update player index — may change after shuffle at game start */
  if (msg.your_player_index !== undefined) {
    myPlayerIndex = msg.your_player_index;
  }
  if (gameView.classList.contains("hidden")) {
    showView(gameView);
  }
  _renderGame();
}

function _onGameOver(msg) {
  _renderGameOver(msg.scores);
}

function _onChat(msg) {
  const div = document.createElement("div");
  div.className = "chat-message";

  const nameSpan = document.createElement("span");
  nameSpan.className = "chat-message__name";
  nameSpan.textContent = msg.player_name;

  const textSpan = document.createElement("span");
  textSpan.className = "chat-message__text";
  textSpan.textContent = msg.text;

  div.appendChild(nameSpan);
  div.appendChild(textSpan);
  chatMessages.appendChild(div);

  /* Auto-scroll to bottom */
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

/* ------------------------------------------------------------------ */
/*  Waiting room                                                       */
/* ------------------------------------------------------------------ */

function _showWaitingRoom() {
  lobbyError.textContent = "";
  showView(waitingView);
  waitingRoomCode.textContent = roomCode;
  startGameBtn.classList.toggle("hidden", !isHost);
  _renderWaitingPlayers();
}

function _renderWaitingPlayers() {
  /* Clear existing children safely */
  while (waitingPlayerList.firstChild) {
    waitingPlayerList.removeChild(waitingPlayerList.firstChild);
  }
  waitingPlayers.forEach((name, i) => {
    const li = document.createElement("li");
    li.textContent = name;
    if (i === 0) {
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = "looja";
      li.appendChild(badge);
    }
    if (i === myPlayerIndex) {
      const badge = document.createElement("span");
      badge.className = "badge badge--you";
      badge.textContent = "sina";
      li.appendChild(badge);
    }
    waitingPlayerList.appendChild(li);
  });

  /* Enable start if host and 2+ players */
  if (isHost) {
    startGameBtn.disabled = waitingPlayers.length < 2;
  }
}

/* ------------------------------------------------------------------ */
/*  Game rendering                                                     */
/* ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ */
/*  Turn notifications                                                 */
/* ------------------------------------------------------------------ */

/**
 * Play a short notification tone using the Web Audio API.
 * No external audio files needed.
 */
function _playTurnSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = "sine";
    osc.frequency.setValueAtTime(587, ctx.currentTime);       // D5
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.4);
    // Second tone for a pleasant chime
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.connect(gain2);
    gain2.connect(ctx.destination);
    osc2.type = "sine";
    osc2.frequency.setValueAtTime(880, ctx.currentTime + 0.15); // A5
    gain2.gain.setValueAtTime(0.12, ctx.currentTime + 0.15);
    gain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.55);
    osc2.start(ctx.currentTime + 0.15);
    osc2.stop(ctx.currentTime + 0.55);
  } catch {
    /* Audio not available — ignore silently */
  }
}

/** Update browser tab title based on turn state. */
function _updateTabTitle(isMyTurn) {
  document.title = isMyTurn
    ? `Sinu käik! - ${DEFAULT_TITLE}`
    : DEFAULT_TITLE;
}

/**
 * Show a last-move banner above the board.
 * @param {object} lastMove - from server
 */
function _showLastMoveBanner(lastMove) {
  if (!lastMove) return;
  let text = "";
  if (lastMove.action === "word") {
    const words = (lastMove.words || []).map((w) => w.word.toUpperCase()).join(", ");
    text = `${lastMove.player_name} mängis ${words} — ${lastMove.total_score} punkti`;
  } else if (lastMove.action === "pass") {
    text = `${lastMove.player_name} jättis käigu vahele`;
  } else if (lastMove.action === "exchange") {
    const n = lastMove.tile_count || 0;
    text = `${lastMove.player_name} vahetas ${n} tähe${n !== 1 ? "d" : ""}`;
  } else if (lastMove.action === "started") {
    text = `Mäng algas! ${lastMove.player_name} alustab.`;
  } else if (lastMove.action === "joined") {
    text = `${lastMove.player_name} liitus mänguga`;
  }

  if (!text) return;

  /* Reuse the error-toast element for general notifications */
  const toast = document.getElementById("error-toast");
  toast.textContent = text;
  toast.className = "error-toast last-move-toast";
  toast.classList.remove("hidden");

  setTimeout(() => {
    toast.classList.add("hidden");
  }, 4000);
}

/**
 * Check for turn changes and fire notifications.
 * @param {boolean} isMyTurn
 */
function _handleTurnChange(isMyTurn) {
  const currentIdx = gameState.current_player_index;

  if (!gameHasStarted) {
    /* First state after game start — don't notify */
    gameHasStarted = true;
    prevCurrentPlayerIdx = currentIdx;
    _updateTabTitle(isMyTurn);
    return;
  }

  const turnChanged = prevCurrentPlayerIdx !== null && prevCurrentPlayerIdx !== currentIdx;
  prevCurrentPlayerIdx = currentIdx;

  if (turnChanged) {
    /* Show what the last player did */
    if (gameState.last_move) {
      _showLastMoveBanner(gameState.last_move);
    }

    /* Notify if it's now our turn */
    if (isMyTurn) {
      _playTurnSound();
    }
  }

  _updateTabTitle(isMyTurn);
}

/* ------------------------------------------------------------------ */

let boardInitialized = false;
let rackInitialized = false;

function _renderGame() {
  if (!gameState) return;

  /* Initialize board and rack once */
  if (!boardInitialized) {
    initBoard(boardContainer, {
      onCellClick: _handleBoardCellClick,
      onCellRightClick: _handleBoardCellRightClick,
    });
    boardInitialized = true;
  }
  if (!rackInitialized) {
    initRack(rackContainer, {
      onTileSelect: () => {},
      onExchangeConfirm: _handleExchangeConfirm,
    });
    rackInitialized = true;
  }

  const isMyTurn = gameState.current_player_index === myPlayerIndex;

  /* Detect turn changes and fire notifications */
  _handleTurnChange(isMyTurn);

  /* Extract last move tile positions for board highlighting */
  const lastMoveTiles =
    gameState.last_move && gameState.last_move.tiles
      ? gameState.last_move.tiles
      : [];

  updateBoard({
    board: gameState.board,
    currentTurnTiles: gameState.current_turn_tiles || [],
    lastMoveTiles,
    isMyTurn,
  });

  updateRack(gameState.rack || []);

  _renderScorePanel();
  _renderGameInfo(isMyTurn);
  _renderControls(isMyTurn);
  _renderScorePreview();
}

function _renderScorePanel() {
  /* Clear safely */
  while (scorePanel.firstChild) {
    scorePanel.removeChild(scorePanel.firstChild);
  }

  const heading = document.createElement("h2");
  heading.textContent = "Skoor";
  scorePanel.appendChild(heading);

  (gameState.players || []).forEach((player, i) => {
    const row = document.createElement("div");
    row.className = "score-row";
    if (i === gameState.current_player_index) {
      row.classList.add("score-row--active");
    }
    if (i === myPlayerIndex) {
      row.classList.add("score-row--me");
    }

    const nameSpan = document.createElement("span");
    nameSpan.className = "score-row__name";
    nameSpan.textContent = player.name;
    row.appendChild(nameSpan);

    const scoreSpan = document.createElement("span");
    scoreSpan.className = "score-row__score";
    scoreSpan.textContent = String(player.score);
    row.appendChild(scoreSpan);

    scorePanel.appendChild(row);
  });
}

function _renderGameInfo(isMyTurn) {
  const currentPlayer = gameState.players[gameState.current_player_index];
  if (isMyTurn) {
    turnIndicator.textContent = "Sinu käik";
    turnIndicator.className = "turn-indicator turn-indicator--your-turn";
  } else {
    turnIndicator.textContent = `Ootab: ${currentPlayer ? currentPlayer.name : "..."}`;
    turnIndicator.className = "turn-indicator turn-indicator--waiting";
  }
  tilesRemaining.textContent = `Tähti kotis: ${gameState.tiles_remaining}`;
}

function _renderControls(isMyTurn) {
  const hasTilesPlaced = (gameState.current_turn_tiles || []).length > 0;
  const hasValidWords =
    (gameState.score_preview || []).length > 0 &&
    gameState.score_preview.some((w) => w.score >= 0);

  submitBtn.disabled = !isMyTurn || !hasTilesPlaced || !hasValidWords;
  passBtn.disabled = !isMyTurn;
  exchangeBtn.disabled =
    !isMyTurn || gameState.tiles_remaining < 7 || hasTilesPlaced;

  /* Disable board interaction when not our turn */
  const board = document.querySelector(".board");
  if (board) {
    board.classList.toggle("board--disabled", !isMyTurn);
  }
}

function _renderScorePreview() {
  /* Clear safely */
  while (scorePreview.firstChild) {
    scorePreview.removeChild(scorePreview.firstChild);
  }

  const preview = gameState.score_preview || [];
  if (preview.length === 0) {
    scorePreview.textContent = "";
    return;
  }

  let total = 0;
  const parts = [];
  for (const entry of preview) {
    parts.push(`${entry.word.toUpperCase()}: ${entry.score}`);
    total += entry.score;
  }

  const text = document.createElement("span");
  text.className = "score-preview__text";
  text.textContent = parts.join(" + ") + ` = ${total} punkti`;
  scorePreview.appendChild(text);
}

/* ------------------------------------------------------------------ */
/*  Game over                                                          */
/* ------------------------------------------------------------------ */

function _renderGameOver(scores) {
  gameOverOverlay.classList.remove("hidden");

  /* Clear safely */
  while (gameOverScores.firstChild) {
    gameOverScores.removeChild(gameOverScores.firstChild);
  }

  const heading = document.createElement("h2");
  heading.textContent = "Mäng läbi";
  gameOverScores.appendChild(heading);

  /* Find winner */
  let maxScore = -1;
  for (const s of scores) {
    if (s.score > maxScore) maxScore = s.score;
  }

  const table = document.createElement("table");
  table.className = "game-over-table";

  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  const thName = document.createElement("th");
  thName.textContent = "Mängija";
  const thScore = document.createElement("th");
  thScore.textContent = "Skoor";
  headerRow.appendChild(thName);
  headerRow.appendChild(thScore);
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  for (const s of scores) {
    const tr = document.createElement("tr");
    if (s.score === maxScore) {
      tr.classList.add("game-over-table__winner");
    }

    const tdName = document.createElement("td");
    tdName.textContent = s.name;
    tr.appendChild(tdName);

    const tdScore = document.createElement("td");
    tdScore.textContent = String(s.score);
    tr.appendChild(tdScore);

    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  gameOverScores.appendChild(table);
}

/* ------------------------------------------------------------------ */
/*  User interactions                                                  */
/* ------------------------------------------------------------------ */

/**
 * Handle click on a board cell.
 * @param {number} row
 * @param {number} col
 */
function _handleBoardCellClick(row, col) {
  if (!gameState || gameState.current_player_index !== myPlayerIndex) return;
  if (isExchangeMode()) return;

  /* If the cell has a tile placed this turn, remove it */
  const turnTiles = gameState.current_turn_tiles || [];
  const isCurrentTurnTile = turnTiles.some((t) => t.row === row && t.col === col);
  if (isCurrentTurnTile) {
    ws.removeTile(row, col);
    return;
  }

  /* If a tile is selected in the rack, place it */
  const tileIdx = getSelectedTileIdx();
  if (tileIdx === null) return;

  /* If the board cell is already occupied, ignore */
  if (gameState.board[row][col] !== null) return;

  const letter = getSelectedTileLetter();
  if (letter === "_") {
    /* Blank tile — show picker */
    showBlankPicker((chosenLetter) => {
      ws.placeTile(row, col, tileIdx, chosenLetter);
      clearSelection();
    });
  } else {
    ws.placeTile(row, col, tileIdx);
    clearSelection();
  }
}

/**
 * Handle right-click on a board cell (remove tile placed this turn).
 * @param {number} row
 * @param {number} col
 */
function _handleBoardCellRightClick(row, col) {
  if (!gameState || gameState.current_player_index !== myPlayerIndex) return;

  const turnTiles = gameState.current_turn_tiles || [];
  const isCurrentTurnTile = turnTiles.some((t) => t.row === row && t.col === col);
  if (isCurrentTurnTile) {
    ws.removeTile(row, col);
  }
}

function _handleExchangeConfirm(tileIndices) {
  ws.exchangeTiles(tileIndices);
  setExchangeMode(false);
}

/* ------------------------------------------------------------------ */
/*  Error display                                                      */
/* ------------------------------------------------------------------ */

/** @type {number|null} */
let errorTimeout = null;

/**
 * Show a transient error toast.
 * @param {string} message
 */
function showError(message) {
  /* Show in lobby error area if on lobby view */
  if (!lobbyView.classList.contains("hidden")) {
    lobbyError.textContent = message;
    return;
  }

  errorToast.textContent = message;
  errorToast.classList.remove("hidden");
  if (errorTimeout) clearTimeout(errorTimeout);
  errorTimeout = setTimeout(() => {
    errorToast.classList.add("hidden");
  }, 4000);
}

/* ------------------------------------------------------------------ */
/*  Event listeners                                                    */
/* ------------------------------------------------------------------ */

createBtn.addEventListener("click", async () => {
  const name = nameInput.value.trim();
  if (!name) {
    lobbyError.textContent = "Palun sisesta oma nimi.";
    return;
  }
  lobbyError.textContent = "";
  if (!ws) await connectWebSocket();
  ws.createRoom(name);
});

joinBtn.addEventListener("click", async () => {
  const name = nameInput.value.trim();
  const code = roomCodeInput.value.trim().toUpperCase();
  if (!name) {
    lobbyError.textContent = "Palun sisesta oma nimi.";
    return;
  }
  if (!code || code.length !== 4) {
    lobbyError.textContent = "Palun sisesta 4-täheline toa kood.";
    return;
  }
  lobbyError.textContent = "";
  if (!ws) await connectWebSocket();
  ws.joinRoom(code, name);
});

startGameBtn.addEventListener("click", () => {
  ws.startGame();
});

copyCodeBtn.addEventListener("click", () => {
  if (roomCode) {
    navigator.clipboard.writeText(roomCode).then(() => {
      copyCodeBtn.textContent = "Kopeeritud!";
      setTimeout(() => {
        copyCodeBtn.textContent = "Kopeeri";
      }, 2000);
    });
  }
});

submitBtn.addEventListener("click", () => {
  ws.commitTurn();
});

passBtn.addEventListener("click", () => {
  ws.passTurn();
});

exchangeBtn.addEventListener("click", () => {
  if (isExchangeMode()) {
    setExchangeMode(false);
  } else {
    setExchangeMode(true);
  }
});

playAgainBtn.addEventListener("click", () => {
  /* Return to lobby to create a new game */
  gameOverOverlay.classList.add("hidden");
  showView(lobbyView);
  _resetClientState();
});

leaveBtn.addEventListener("click", () => {
  gameOverOverlay.classList.add("hidden");
  showView(lobbyView);
  if (ws) ws.close();
  _resetClientState();
});

/* Force uppercase on room code input */
roomCodeInput.addEventListener("input", () => {
  roomCodeInput.value = roomCodeInput.value.toUpperCase().replace(/[^A-Z]/g, "");
});

/* ---- Chat controls ---- */

function _sendChatMessage() {
  const text = chatInput.value.trim();
  if (!text || !ws) return;
  ws.sendChat(text);
  chatInput.value = "";
}

chatSendBtn.addEventListener("click", _sendChatMessage);

chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    _sendChatMessage();
  }
});

function _resetClientState() {
  myPlayerIndex = null;
  roomCode = null;
  isHost = false;
  gameState = null;
  waitingPlayers = [];
  boardInitialized = false;
  rackInitialized = false;
  resetRackOrder();
  prevCurrentPlayerIdx = null;
  gameHasStarted = false;
  document.title = DEFAULT_TITLE;
  ws = null;

  /* Clear board and rack containers */
  while (boardContainer.firstChild) {
    boardContainer.removeChild(boardContainer.firstChild);
  }
  while (rackContainer.firstChild) {
    rackContainer.removeChild(rackContainer.firstChild);
  }

  /* Reset chat */
  while (chatMessages.firstChild) {
    chatMessages.removeChild(chatMessages.firstChild);
  }
}

/* ------------------------------------------------------------------ */
/*  Initialize                                                         */
/* ------------------------------------------------------------------ */

showView(lobbyView);
