"""FastAPI application with WebSocket endpoint for multiplayer Estonian Scrabble."""

from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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
