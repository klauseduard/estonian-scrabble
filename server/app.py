"""FastAPI application with WebSocket endpoint for multiplayer Estonian Scrabble."""

from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from game.state import GameState

from .room import Room, RoomManager

app = FastAPI(title="Estonian Scrabble Server")
room_manager = RoomManager()


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment platforms."""
    return {"status": "ok"}

_WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@app.get("/stats")
async def server_stats():
    """Live server metrics derived from active rooms."""
    rooms_list = []
    players_total = 0
    rooms_waiting = 0
    rooms_playing = 0

    for room in room_manager.rooms.values():
        status = "playing" if room.started else "waiting"
        if room.started:
            rooms_playing += 1
        else:
            rooms_waiting += 1
        players_total += room.player_count
        rooms_list.append({
            "code": room.code,
            "players": room.player_count,
            "status": status,
        })

    return {
        "rooms_total": len(rooms_list),
        "rooms_waiting": rooms_waiting,
        "rooms_playing": rooms_playing,
        "players_connected": players_total,
        "rooms": rooms_list,
    }


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    """Minimal self-refreshing admin dashboard."""
    return """<!DOCTYPE html>
<html lang="et">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Eesti Scrabble — Admin</title>
<style>
  body {
    font-family: "Noto Sans", system-ui, sans-serif;
    background: #2C3E50; color: #E8E8E8;
    margin: 0; padding: 24px;
  }
  h1 { font-size: 22px; margin-bottom: 4px; }
  .subtitle { color: #889; font-size: 13px; margin-bottom: 24px; }
  .cards { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 28px; }
  .card {
    background: #3D5266; border: 1px solid #4A6378;
    border-radius: 10px; padding: 20px 28px; min-width: 140px;
    text-align: center;
  }
  .card__value { font-size: 36px; font-weight: 700; }
  .card__label { font-size: 12px; color: #AAB; margin-top: 4px; }
  .card--gold .card__value { color: #FFD700; }
  .card--green .card__value { color: #66BB6A; }
  .card--blue .card__value { color: #4A90D9; }
  table {
    width: 100%; max-width: 600px; border-collapse: collapse;
    background: #3D5266; border-radius: 8px; overflow: hidden;
  }
  th { background: #4A6378; text-align: left; padding: 10px 14px; font-size: 13px; }
  td { padding: 10px 14px; border-top: 1px solid #4A6378; font-size: 14px; }
  .status-playing { color: #66BB6A; }
  .status-waiting { color: #FFD700; }
  .code { font-family: monospace; font-weight: 700; letter-spacing: 3px; }
  #updated { color: #667; font-size: 11px; margin-top: 16px; }
</style>
</head>
<body>
  <h1>Eesti Scrabble</h1>
  <p class="subtitle">Serveri seis &mdash; uuendab iga 10 sekundi tagant</p>
  <div class="cards">
    <div class="card card--gold">
      <div class="card__value" id="v-players">-</div>
      <div class="card__label">M&auml;ngijaid</div>
    </div>
    <div class="card card--green">
      <div class="card__value" id="v-playing">-</div>
      <div class="card__label">M&auml;nge k&auml;imas</div>
    </div>
    <div class="card card--blue">
      <div class="card__value" id="v-waiting">-</div>
      <div class="card__label">Ootavad tube</div>
    </div>
  </div>
  <table>
    <thead><tr><th>Toa kood</th><th>M&auml;ngijaid</th><th>Staatus</th></tr></thead>
    <tbody id="room-rows"><tr><td colspan="3">Laen...</td></tr></tbody>
  </table>
  <div id="updated"></div>
<script>
function esc(s) { const d = document.createElement("span"); d.textContent = s; return d.innerHTML; }
async function refresh() {
  try {
    const r = await fetch("/stats");
    const d = await r.json();
    document.getElementById("v-players").textContent = d.players_connected;
    document.getElementById("v-playing").textContent = d.rooms_playing;
    document.getElementById("v-waiting").textContent = d.rooms_waiting;
    const tbody = document.getElementById("room-rows");
    while (tbody.firstChild) tbody.removeChild(tbody.firstChild);
    if (d.rooms.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 3; td.style.color = "#667"; td.textContent = "Tube pole";
      tr.appendChild(td); tbody.appendChild(tr);
    } else {
      d.rooms.forEach(function(rm) {
        const tr = document.createElement("tr");
        const tdCode = document.createElement("td");
        tdCode.className = "code"; tdCode.textContent = rm.code;
        const tdPlayers = document.createElement("td");
        tdPlayers.textContent = rm.players;
        const tdStatus = document.createElement("td");
        tdStatus.className = "status-" + rm.status;
        tdStatus.textContent = rm.status === "playing" ? "M\\u00e4ngib" : "Ootab";
        tr.appendChild(tdCode); tr.appendChild(tdPlayers); tr.appendChild(tdStatus);
        tbody.appendChild(tr);
      });
    }
    document.getElementById("updated").textContent =
      "Uuendatud: " + new Date().toLocaleTimeString("et-EE");
  } catch(e) { /* ignore transient errors */ }
}
refresh();
setInterval(refresh, 10000);
</script>
</body>
</html>"""


async def _send_error(ws: WebSocket, message: str):
    """Send an error message to a single client."""
    await ws.send_json({"type": "error", "message": message})


async def _handle_create_room(ws: WebSocket, data: Dict[str, Any]) -> Room:
    """Handle the ``create_room`` action and return the new Room."""
    player_name = data.get("player_name", "Player 1")
    room = room_manager.create_room()
    player_index = room.add_player(player_name, ws)
    await ws.send_json({
        "type": "room_created",
        "room_code": room.code,
        "player_index": player_index,
    })
    return room


async def _handle_join_room(ws: WebSocket, data: Dict[str, Any]) -> Room | None:
    """Handle the ``join_room`` action and return the Room if successful."""
    room_code = data.get("room_code", "")
    player_name = data.get("player_name", "Player")
    room = room_manager.get_room(room_code)

    if room is None:
        await _send_error(ws, f"Room '{room_code}' not found")
        return None

    if room.started:
        await _send_error(ws, "Game already started")
        return None

    if room.player_count >= 4:
        await _send_error(ws, "Room is full")
        return None

    player_index = room.add_player(player_name, ws)
    await ws.send_json({
        "type": "room_joined",
        "room_code": room.code,
        "player_index": player_index,
    })
    await room.broadcast(
        {
            "type": "player_joined",
            "player_name": player_name,
            "player_count": room.player_count,
        },
        exclude=ws,
    )
    return room


async def _handle_start_game(ws: WebSocket, room: Room):
    """Start the game in the room (only if enough players)."""
    if room.started:
        await _send_error(ws, "Game already started")
        return

    if room.player_count < 2:
        await _send_error(ws, "Need at least 2 players to start")
        return

    room.game = GameState(num_players=room.player_count)
    # Overwrite default player names with the ones chosen in the lobby
    for i, player_info in enumerate(room.players):
        room.game.players[i].name = player_info["name"]

    room.started = True
    await room.broadcast_game_state()


async def _handle_place_tile(ws: WebSocket, room: Room, data: Dict[str, Any]):
    """Place a tile on the board."""
    game = room.game
    if game is None or game.game_over:
        await _send_error(ws, "Game not active")
        return

    player_index = room.get_player_index(ws)
    if player_index != game.current_player_idx:
        await _send_error(ws, "Not your turn")
        return

    row = data.get("row")
    col = data.get("col")
    tile_idx = data.get("tile_idx")

    if row is None or col is None or tile_idx is None:
        await _send_error(ws, "Missing row, col, or tile_idx")
        return

    designated_letter = data.get("designated_letter")
    success = game.place_tile(row, col, tile_idx, designated_letter=designated_letter)
    if not success:
        await _send_error(ws, "Invalid tile placement")
        return

    game.validate_current_placement()
    await room.broadcast_game_state()


async def _handle_remove_tile(ws: WebSocket, room: Room, data: Dict[str, Any]):
    """Remove a previously placed tile from the board."""
    game = room.game
    if game is None or game.game_over:
        await _send_error(ws, "Game not active")
        return

    player_index = room.get_player_index(ws)
    if player_index != game.current_player_idx:
        await _send_error(ws, "Not your turn")
        return

    row = data.get("row")
    col = data.get("col")
    if row is None or col is None:
        await _send_error(ws, "Missing row or col")
        return

    success = game.remove_tile(row, col)
    if not success:
        await _send_error(ws, "Cannot remove tile")
        return

    game.validate_current_placement()
    await room.broadcast_game_state()


async def _handle_commit_turn(ws: WebSocket, room: Room):
    """Commit the current turn (submit words)."""
    game = room.game
    if game is None or game.game_over:
        await _send_error(ws, "Game not active")
        return

    player_index = room.get_player_index(ws)
    if player_index != game.current_player_idx:
        await _send_error(ws, "Not your turn")
        return

    # Capture move details before commit (commit clears current_turn_tiles)
    player_name = game.players[player_index].name
    placed_positions = [{"row": r, "col": c} for r, c in game.current_turn_tiles]
    score_breakdown = game.calculate_turn_score()
    words = [{"word": w, "score": s} for w, s in score_breakdown]
    total_score = sum(s for _, s in score_breakdown)

    success = game.commit_turn()
    if not success:
        await _send_error(ws, "Invalid placement — cannot commit")
        return

    room.last_move = {
        "action": "word",
        "player_name": player_name,
        "words": words,
        "total_score": total_score,
        "tiles": placed_positions,
    }

    if game.game_over:
        await room.broadcast_game_over()
    else:
        await room.broadcast_game_state()


async def _handle_pass_turn(ws: WebSocket, room: Room):
    """Pass (forfeit) the current turn."""
    game = room.game
    if game is None or game.game_over:
        await _send_error(ws, "Game not active")
        return

    player_index = room.get_player_index(ws)
    if player_index != game.current_player_idx:
        await _send_error(ws, "Not your turn")
        return

    player_name = game.players[player_index].name
    game.next_player()

    room.last_move = {
        "action": "pass",
        "player_name": player_name,
    }

    if game.game_over:
        await room.broadcast_game_over()
    else:
        await room.broadcast_game_state()


async def _handle_exchange_tiles(ws: WebSocket, room: Room, data: Dict[str, Any]):
    """Exchange selected tiles with the bag."""
    game = room.game
    if game is None or game.game_over:
        await _send_error(ws, "Game not active")
        return

    player_index = room.get_player_index(ws)
    if player_index != game.current_player_idx:
        await _send_error(ws, "Not your turn")
        return

    tile_indices = data.get("tile_indices")
    if tile_indices is None:
        await _send_error(ws, "Missing tile_indices")
        return

    player_name = game.players[player_index].name
    count = len(tile_indices)

    success = game.exchange_tiles(tile_indices)
    if not success:
        await _send_error(ws, "Cannot exchange tiles")
        return

    room.last_move = {
        "action": "exchange",
        "player_name": player_name,
        "tile_count": count,
    }

    await room.broadcast_game_state()


async def _handle_designate_blank(ws: WebSocket, room: Room, data: Dict[str, Any]):
    """Designate a letter for a blank tile already placed on the board.

    This is handled during ``place_tile`` via the ``designated_letter`` field,
    but this action allows retroactive designation if needed by a client.
    """
    game = room.game
    if game is None or game.game_over:
        await _send_error(ws, "Game not active")
        return

    player_index = room.get_player_index(ws)
    if player_index != game.current_player_idx:
        await _send_error(ws, "Not your turn")
        return

    row = data.get("row")
    col = data.get("col")
    letter = data.get("letter")

    if row is None or col is None or letter is None:
        await _send_error(ws, "Missing row, col, or letter")
        return

    pos = (row, col)
    if pos not in game.current_turn_tiles or pos not in game.blank_designations:
        await _send_error(ws, "No blank tile at that position")
        return

    game.board[row][col] = letter.lower()
    game.blank_designations[pos] = letter.lower()
    game.validate_current_placement()
    await room.broadcast_game_state()


async def _handle_chat(ws: WebSocket, room: Room, data: Dict[str, Any]):
    """Broadcast a chat message from a player to everyone in the room."""
    player_index = room.get_player_index(ws)
    if player_index is None:
        return

    if room.game is not None:
        player_name = room.game.players[player_index].name
    else:
        player_name = room.players[player_index]["name"]

    text = data.get("text", "")[:200]
    if not text.strip():
        return

    await room.broadcast({
        "type": "chat",
        "player_name": player_name,
        "text": text,
    })


# ---- WebSocket endpoint ----

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Main WebSocket endpoint. Clients send JSON actions, receive JSON events."""
    await ws.accept()
    room: Room | None = None

    try:
        while True:
            data = await ws.receive_json()
            action = data.get("action")

            if action == "create_room":
                room = await _handle_create_room(ws, data)

            elif action == "join_room":
                room = await _handle_join_room(ws, data)

            elif room is None:
                await _send_error(ws, "Join or create a room first")

            elif action == "start_game":
                await _handle_start_game(ws, room)

            elif action == "place_tile":
                await _handle_place_tile(ws, room, data)

            elif action == "remove_tile":
                await _handle_remove_tile(ws, room, data)

            elif action == "commit_turn":
                await _handle_commit_turn(ws, room)

            elif action == "pass_turn":
                await _handle_pass_turn(ws, room)

            elif action == "exchange_tiles":
                await _handle_exchange_tiles(ws, room, data)

            elif action == "designate_blank":
                await _handle_designate_blank(ws, room, data)

            elif action == "chat":
                await _handle_chat(ws, room, data)

            else:
                await _send_error(ws, f"Unknown action: {action}")

    except WebSocketDisconnect:
        if room is not None:
            room.remove_player(ws)
            if room.player_count == 0:
                room_manager.remove_room(room.code)
            else:
                await room.broadcast({
                    "type": "player_left",
                    "player_count": room.player_count,
                })


# ---- Static file serving (must come AFTER the /ws route) ----

if _WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_WEB_DIR), html=True), name="static")
