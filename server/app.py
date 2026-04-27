"""FastAPI application with WebSocket endpoint for multiplayer Estonian Scrabble."""

import asyncio
import random
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from game.ai_player import select_move
from game.state import GameState

from .room import Room, RoomManager
from .serialization import serialize_game_state

app = FastAPI(title="Estonian Scrabble Server")
room_manager = RoomManager()


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment platforms."""
    return {"status": "ok"}

_WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@app.get("/lobby")
async def public_lobby():
    """List public rooms waiting for players."""
    rooms = []
    for room in room_manager.rooms.values():
        if room.public and not room.started and room.player_count < 4:
            rooms.append({
                "code": room.code,
                "host": room.players[0]["name"] if room.players else "?",
                "players": room.player_count,
            })
    return {"rooms": rooms}


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
    <thead><tr><th>M&auml;ngijaid</th><th>Staatus</th></tr></thead>
    <tbody id="room-rows"><tr><td colspan="3">Laen...</td></tr></tbody>
  </table>
  <div id="updated"></div>
<script>
function esc(s) { const d = document.createElement("span"); d.textContent = s; return d.innerHTML; }
async function refresh() {
  try {
    const r = await fetch("stats");
    const d = await r.json();
    document.getElementById("v-players").textContent = d.players_connected;
    document.getElementById("v-playing").textContent = d.rooms_playing;
    document.getElementById("v-waiting").textContent = d.rooms_waiting;
    const tbody = document.getElementById("room-rows");
    while (tbody.firstChild) tbody.removeChild(tbody.firstChild);
    if (d.rooms.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 2; td.style.color = "#667"; td.textContent = "Tube pole";
      tr.appendChild(td); tbody.appendChild(tr);
    } else {
      d.rooms.forEach(function(rm) {
        const tr = document.createElement("tr");
        const tdPlayers = document.createElement("td");
        tdPlayers.textContent = rm.players;
        const tdStatus = document.createElement("td");
        tdStatus.className = "status-" + rm.status;
        tdStatus.textContent = rm.status === "playing" ? "M\\u00e4ngib" : "Ootab";
        tr.appendChild(tdPlayers); tr.appendChild(tdStatus);
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


def _is_force_pending(room: Room) -> bool:
    """Check if a forced word is waiting for all players to acknowledge."""
    return bool(room._force_required_acks and not room._force_required_acks.issubset(room._force_acks))


async def _maybe_run_ai_turn(room: Room):
    """If the current player is an AI, schedule their turn execution."""
    game = room.game
    if game is None or game.game_over:
        return
    player_idx = game.current_player_idx
    if player_idx not in room.ai_players:
        return
    # Fire-and-forget so we don't block the caller
    asyncio.ensure_future(_execute_ai_turn(room))


async def _execute_ai_turn(room: Room):
    """Execute the AI player's turn in a thread pool."""
    game = room.game
    if game is None or game.game_over:
        return

    player_idx = game.current_player_idx
    if player_idx not in room.ai_players:
        return

    # Small delay for natural feel
    await asyncio.sleep(1.5)

    # Re-check after delay (game state may have changed)
    if game.game_over or game.current_player_idx != player_idx:
        return

    # Run AI computation in executor (don't block event loop)
    loop = asyncio.get_event_loop()
    rack = list(game.players[player_idx].rack)
    board = [row[:] for row in game.board]
    difficulty = room.players[player_idx].get("difficulty", "medium")

    move = await loop.run_in_executor(
        None,
        select_move, board, rack, game.wordlist, game.first_move, difficulty,
    )

    # Re-check again after executor completes
    if game.game_over or game.current_player_idx != player_idx:
        return

    player_name = game.players[player_idx].name

    if move is None:
        # No valid move — pass
        room.clear_challenge()
        game.next_player()
        room.last_move = {
            "action": "pass",
            "player_name": player_name,
        }
        await room.broadcast({
            "type": "chat",
            "player_name": "Süsteem",
            "text": f"{player_name} jättis käigu vahele.",
        })
        if game.game_over:
            await room.broadcast_game_over()
        else:
            await room.broadcast_game_state()
            await _maybe_run_ai_turn(room)
    else:
        # Place tiles and commit
        room.clear_challenge()
        for row, col, letter in move.tiles:
            tile_idx = game.current_player.rack.index(letter)
            game.place_tile(row, col, tile_idx)
        game.validate_current_placement()

        # Capture score info before commit
        score_breakdown = game.calculate_turn_score()
        words = [{"word": w, "score": s} for w, s in score_breakdown]
        total_score = sum(s for _, s in score_breakdown)
        placed_positions = [{"row": r, "col": c} for r, c in game.current_turn_tiles]

        room.save_snapshot(player_name)
        success = game.commit_turn(force=False, defer_draw=True)
        if not success:
            # Shouldn't happen with AI-generated moves, but handle gracefully
            room.clear_challenge()
            game.next_player()
            room.last_move = {"action": "pass", "player_name": player_name}
            await room.broadcast_game_state()
            await _maybe_run_ai_turn(room)
            return

        room.last_move = {
            "action": "word",
            "player_name": player_name,
            "words": words,
            "total_score": total_score,
            "tiles": placed_positions,
            "challengeable": True,
            "forced": False,
        }

        # Post move to chat
        word_parts = [f"{w['word'].upper()}: {w['score']}" for w in words]
        chat_text = " + ".join(word_parts) + f" = {total_score} p."
        await room.broadcast({
            "type": "chat",
            "player_name": "Süsteem",
            "text": f"{player_name}: {chat_text}",
        })

        if game.game_over:
            await room.broadcast_game_over()
        else:
            await room.broadcast_game_state()
            await _maybe_run_ai_turn(room)


async def _handle_create_room(ws: WebSocket, data: Dict[str, Any]) -> Room:
    """Handle the ``create_room`` action and return the new Room."""
    player_name = data.get("player_name", "Player 1")
    room = room_manager.create_room()
    room.public = bool(data.get("public", False))
    player_index = room.add_player(player_name, ws)
    await ws.send_json({
        "type": "room_created",
        "room_code": room.code,
        "player_index": player_index,
        "players": [p["name"] for p in room.players],
    })
    return room


async def _handle_join_room(ws: WebSocket, data: Dict[str, Any]) -> Room | None:
    """Handle the ``join_room`` action and return the Room if successful.

    If the game has started and a disconnected player with the same name exists,
    reconnect them to their existing slot instead of rejecting.
    """
    room_code = data.get("room_code", "")
    player_name = data.get("player_name", "Player")
    room = room_manager.get_room(room_code)

    if room is None:
        await _send_error(ws, f"Room '{room_code}' not found")
        return None

    # Reconnection: game in progress, player with same name is disconnected
    if room.started and room.has_disconnected_player(player_name):
        player_index = room.reconnect_player(player_name, ws)
        await ws.send_json({
            "type": "reconnected",
            "room_code": room.code,
            "player_index": player_index,
            "players": [p["name"] for p in room.players],
        })
        await room.broadcast(
            {
                "type": "player_reconnected",
                "player_name": player_name,
            },
            exclude=ws,
        )
        # Send current game state to the reconnected player
        if room.game is not None:
            state = serialize_game_state(room.game, player_index, last_move=room.last_move)
            state["your_player_index"] = player_index
            await ws.send_json(state)
        return room

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
        "players": [p["name"] for p in room.players],
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

    # Randomize player order
    random.shuffle(room.players)

    # Rebuild AI player index set after shuffle
    room.ai_players = {
        i for i, p in enumerate(room.players) if p.get("difficulty") is not None
    }

    room.game = GameState(num_players=room.player_count)
    # Overwrite default player names with the ones chosen in the lobby
    for i, player_info in enumerate(room.players):
        room.game.players[i].name = player_info["name"]

    room.started = True
    first_player_name = room.game.players[0].name
    await room.broadcast({
        "type": "game_started",
        "first_player": first_player_name,
    })
    await room.broadcast_game_state()
    await _maybe_run_ai_turn(room)


async def _handle_add_ai(ws: WebSocket, room: Room, data: Dict[str, Any]):
    """Add an AI player to the room (host only, before game starts)."""
    if room.started:
        await _send_error(ws, "Game already started")
        return

    # Only the host (first player) can add AI players
    host_idx = room.get_player_index(ws)
    if host_idx != 0:
        await _send_error(ws, "Only the host can add AI players")
        return

    if room.player_count >= 4:
        await _send_error(ws, "Room is full")
        return

    difficulty = data.get("difficulty", "medium")
    if difficulty not in ("easy", "medium", "hard"):
        difficulty = "medium"

    # Generate AI name
    existing_ai_count = len(room.ai_players)
    if existing_ai_count == 0:
        ai_name = "Arvuti"
    else:
        ai_name = f"Arvuti {existing_ai_count + 1}"

    room.add_ai_player(ai_name, difficulty)

    await room.broadcast({
        "type": "player_joined",
        "player_name": ai_name,
        "player_count": room.player_count,
        "is_ai": True,
    })


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

    if _is_force_pending(room):
        await _send_error(ws, "Oota, kuni kõik mängijad on programmi arvates lubamatu sõna heaks kiitnud")
        return

    room.clear_challenge()  # Next player is acting, challenge window closed

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


async def _do_commit(ws: WebSocket, room: Room, force: bool = False):
    """Shared commit logic for normal and forced commits."""
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
    if force:
        score_breakdown = game.force_calculate_turn_score()
    else:
        score_breakdown = game.calculate_turn_score()
    words = [{"word": w, "score": s} for w, s in score_breakdown]
    total_score = sum(s for _, s in score_breakdown)

    # Save snapshot for potential challenge undo
    room.save_snapshot(player_name)

    success = game.commit_turn(force=force, defer_draw=True)
    if not success:
        room.clear_challenge()
        await _send_error(ws, "Invalid placement — cannot commit")
        return

    room.last_move = {
        "action": "word",
        "player_name": player_name,
        "words": words,
        "total_score": total_score,
        "tiles": placed_positions,
        "challengeable": True,
        "forced": force,
    }

    # Post move to chat with score breakdown
    word_parts = [f"{w['word'].upper()}: {w['score']}" for w in words]
    chat_text = " + ".join(word_parts) + f" = {total_score} p."
    await room.broadcast({
        "type": "chat",
        "player_name": "Süsteem",
        "text": f"{player_name}: {chat_text}",
    })
    if force:
        forced_words = ", ".join(w["word"].upper() for w in words)
        await room.broadcast({
            "type": "chat",
            "player_name": "Süsteem",
            "text": f"Sõna {forced_words} ei ole sõnastikus — vajab teiste mängijate heakskiitu.",
        })
        room.set_force_ack_required(player_name)

    if game.game_over:
        await room.broadcast_game_over()
    else:
        await room.broadcast_game_state()
        await _maybe_run_ai_turn(room)


async def _handle_commit_turn(ws: WebSocket, room: Room):
    """Commit the current turn if all words are valid."""
    await _do_commit(ws, room, force=False)


async def _handle_force_commit(ws: WebSocket, room: Room):
    """Force-commit the current turn, bypassing word validation."""
    await _do_commit(ws, room, force=True)


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

    if _is_force_pending(room):
        await _send_error(ws, "Oota, kuni kõik mängijad on programmi arvates lubamatu sõna heaks kiitnud")
        return

    player_name = game.players[player_index].name
    room.clear_challenge()
    game.next_player()

    room.last_move = {
        "action": "pass",
        "player_name": player_name,
    }

    await room.broadcast({
        "type": "chat",
        "player_name": "Süsteem",
        "text": f"{player_name} jättis käigu vahele.",
    })

    if game.game_over:
        await room.broadcast_game_over()
    else:
        await room.broadcast_game_state()
        await _maybe_run_ai_turn(room)


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

    if _is_force_pending(room):
        await _send_error(ws, "Oota, kuni kõik mängijad on programmi arvates lubamatu sõna heaks kiitnud")
        return

    player_name = game.players[player_index].name
    count = len(tile_indices)
    room.clear_challenge()

    success = game.exchange_tiles(tile_indices)
    if not success:
        await _send_error(ws, "Cannot exchange tiles")
        return

    room.last_move = {
        "action": "exchange",
        "player_name": player_name,
        "tile_count": count,
    }

    await room.broadcast({
        "type": "chat",
        "player_name": "Süsteem",
        "text": f"{player_name} vahetas {count} tähe{'d' if count != 1 else 't'}.",
    })

    await room.broadcast_game_state()
    await _maybe_run_ai_turn(room)


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


async def _handle_force_ack(ws: WebSocket, room: Room):
    """Acknowledge a forced word — player approves it."""
    player_index = room.get_player_index(ws)
    if player_index is None:
        return
    player_name = room.players[player_index]["name"]

    all_acked = room.add_force_ack(player_name)

    await room.broadcast({
        "type": "chat",
        "player_name": "Süsteem",
        "text": f"{player_name} kiitis sõna heaks.",
    })

    if all_acked:
        # All players approved — clear challenge window and draw tiles
        room.clear_challenge(force_check=False)
        await room.broadcast({"type": "force_approved"})
        await room.broadcast_game_state()
        await _maybe_run_ai_turn(room)


async def _handle_challenge(ws: WebSocket, room: Room):
    """A player challenges the last committed word. Asks the challenged player to undo."""
    game = room.game
    if game is None or game.game_over:
        await _send_error(ws, "Game not active")
        return

    if room._challengeable_player is None or room._pre_commit_snapshot is None:
        await _send_error(ws, "Nothing to challenge")
        return

    challenger_index = room.get_player_index(ws)
    challenger_name = room.players[challenger_index]["name"]

    # Can't challenge your own move
    if challenger_name == room._challengeable_player:
        await _send_error(ws, "You cannot challenge your own move")
        return

    # Already a pending challenge
    if room._challenge_pending is not None:
        await _send_error(ws, "A challenge is already pending")
        return

    room._challenge_pending = {
        "challenger": challenger_name,
        "challenged": room._challengeable_player,
    }

    await room.broadcast({
        "type": "challenge",
        "challenger": challenger_name,
        "challenged": room._challengeable_player,
    })
    await room.broadcast({
        "type": "chat",
        "player_name": "Süsteem",
        "text": f"{challenger_name} vaidlustab mängija {room._challengeable_player} käigu.",
    })


async def _handle_challenge_accept(ws: WebSocket, room: Room):
    """The challenged player accepts — undo their last move."""
    if room._challenge_pending is None:
        await _send_error(ws, "No pending challenge")
        return

    player_index = room.get_player_index(ws)
    player_name = room.players[player_index]["name"]

    if player_name != room._challenge_pending["challenged"]:
        await _send_error(ws, "Only the challenged player can accept")
        return

    challenger = room._challenge_pending["challenger"]
    challenged = room._challenge_pending["challenged"]

    if not room.restore_snapshot():
        await _send_error(ws, "Cannot undo — no snapshot available")
        return

    room.last_move = {
        "action": "challenge_accepted",
        "challenger": challenger,
        "challenged": challenged,
    }

    await room.broadcast({
        "type": "challenge_resolved",
        "result": "accepted",
        "challenger": challenger,
        "challenged": challenged,
    })
    await room.broadcast({
        "type": "chat",
        "player_name": "Süsteem",
        "text": f"{challenged} võttis käigu tagasi.",
    })
    await room.broadcast_game_state()
    await _maybe_run_ai_turn(room)


async def _handle_challenge_refuse(ws: WebSocket, room: Room):
    """The challenged player refuses — game continues as-is."""
    if room._challenge_pending is None:
        await _send_error(ws, "No pending challenge")
        return

    player_index = room.get_player_index(ws)
    player_name = room.players[player_index]["name"]

    if player_name != room._challenge_pending["challenged"]:
        await _send_error(ws, "Only the challenged player can refuse")
        return

    challenger = room._challenge_pending["challenger"]
    challenged = room._challenge_pending["challenged"]

    # Clear the pending challenge but keep the snapshot — others can still challenge
    room._challenge_pending = None

    await room.broadcast({
        "type": "challenge_resolved",
        "result": "refused",
        "challenger": challenger,
        "challenged": challenged,
    })
    await room.broadcast({
        "type": "chat",
        "player_name": "Süsteem",
        "text": f"{challenged} keeldus käiku tagasi võtmast.",
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

            elif action == "add_ai":
                await _handle_add_ai(ws, room, data)

            elif action == "place_tile":
                await _handle_place_tile(ws, room, data)

            elif action == "remove_tile":
                await _handle_remove_tile(ws, room, data)

            elif action == "commit_turn":
                await _handle_commit_turn(ws, room)

            elif action == "force_commit":
                await _handle_force_commit(ws, room)

            elif action == "pass_turn":
                await _handle_pass_turn(ws, room)

            elif action == "exchange_tiles":
                await _handle_exchange_tiles(ws, room, data)

            elif action == "designate_blank":
                await _handle_designate_blank(ws, room, data)

            elif action == "chat":
                await _handle_chat(ws, room, data)

            elif action == "force_ack":
                await _handle_force_ack(ws, room)

            elif action == "challenge":
                await _handle_challenge(ws, room)

            elif action == "challenge_accept":
                await _handle_challenge_accept(ws, room)

            elif action == "challenge_refuse":
                await _handle_challenge_refuse(ws, room)

            else:
                await _send_error(ws, f"Unknown action: {action}")

    except WebSocketDisconnect:
        if room is not None:
            if room.started:
                # Game in progress: preserve slot for reconnection
                idx = room.disconnect_player(ws)
                if idx is not None:
                    player_name = room.players[idx]["name"]
                    await room.broadcast({
                        "type": "player_disconnected",
                        "player_name": player_name,
                    })
                # Clean up room only if ALL players disconnected
                if room.connected_count == 0:
                    room_manager.remove_room(room.code)
            else:
                # Waiting room: remove player entirely
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
