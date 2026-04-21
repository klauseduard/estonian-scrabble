/**
 * WebSocket client for Estonian Scrabble multiplayer.
 */

/** @typedef {(msg: object) => void} MessageHandler */

class ScrabbleWebSocket {
  /** @type {WebSocket|null} */
  #ws = null;
  /** @type {MessageHandler[]} */
  #handlers = [];
  /** @type {string} */
  #url;
  /** @type {boolean} */
  #intentionalClose = false;

  /**
   * @param {string} [url] - WebSocket URL. Defaults to ws(s)://currentHost/ws.
   */
  constructor(url) {
    if (url) {
      this.#url = url;
    } else {
      const protocol = location.protocol === "https:" ? "wss:" : "ws:";
      this.#url = `${protocol}//${location.host}/ws`;
    }
  }

  /**
   * Register a handler for incoming messages.
   * @param {MessageHandler} handler
   */
  onMessage(handler) {
    this.#handlers.push(handler);
  }

  /** Connect to the server. Returns a promise that resolves on open. */
  connect() {
    return new Promise((resolve, reject) => {
      this.#intentionalClose = false;
      this.#ws = new WebSocket(this.#url);

      this.#ws.onopen = () => resolve();

      this.#ws.onerror = (event) => {
        console.error("WebSocket error:", event);
        reject(new Error("WebSocket connection failed"));
      };

      this.#ws.onclose = () => {
        if (!this.#intentionalClose) {
          this.#dispatch({ type: "connection_lost" });
        }
      };

      this.#ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.#dispatch(data);
        } catch (e) {
          console.error("Failed to parse message:", e);
        }
      };
    });
  }

  /**
   * Send a JSON action to the server.
   * @param {object} data
   */
  send(data) {
    if (this.#ws && this.#ws.readyState === WebSocket.OPEN) {
      this.#ws.send(JSON.stringify(data));
    }
  }

  /** Close the connection intentionally. */
  close() {
    this.#intentionalClose = true;
    if (this.#ws) {
      this.#ws.close();
    }
  }

  /** @param {object} msg */
  #dispatch(msg) {
    for (const handler of this.#handlers) {
      handler(msg);
    }
  }

  /* Convenience methods for each action */

  /**
   * @param {string} playerName
   */
  createRoom(playerName) {
    this.send({ action: "create_room", player_name: playerName });
  }

  /**
   * @param {string} roomCode
   * @param {string} playerName
   */
  joinRoom(roomCode, playerName) {
    this.send({ action: "join_room", room_code: roomCode, player_name: playerName });
  }

  startGame() {
    this.send({ action: "start_game" });
  }

  /**
   * @param {number} row
   * @param {number} col
   * @param {number} tileIdx
   * @param {string} [designatedLetter]
   */
  placeTile(row, col, tileIdx, designatedLetter) {
    const msg = { action: "place_tile", row, col, tile_idx: tileIdx };
    if (designatedLetter) {
      msg.designated_letter = designatedLetter;
    }
    this.send(msg);
  }

  /**
   * @param {number} row
   * @param {number} col
   */
  removeTile(row, col) {
    this.send({ action: "remove_tile", row, col });
  }

  commitTurn() {
    this.send({ action: "commit_turn" });
  }

  /** Force-commit bypassing word validation. */
  forceCommit() {
    this.send({ action: "force_commit" });
  }

  passTurn() {
    this.send({ action: "pass_turn" });
  }

  /**
   * @param {number[]} tileIndices
   */
  exchangeTiles(tileIndices) {
    this.send({ action: "exchange_tiles", tile_indices: tileIndices });
  }

  /**
   * @param {number} row
   * @param {number} col
   * @param {string} letter
   */
  designateBlank(row, col, letter) {
    this.send({ action: "designate_blank", row, col, letter });
  }

  /**
   * Send a chat message.
   * @param {string} text
   */
  sendChat(text) {
    this.send({ action: "chat", text });
  }

  /** Challenge the last committed word. */
  challenge() {
    this.send({ action: "challenge" });
  }

  /** Accept a challenge (undo your last move). */
  challengeAccept() {
    this.send({ action: "challenge_accept" });
  }

  /** Refuse a challenge (keep your move). */
  challengeRefuse() {
    this.send({ action: "challenge_refuse" });
  }
}

export default ScrabbleWebSocket;
