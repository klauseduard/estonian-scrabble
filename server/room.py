"""Room management for multiplayer Scrabble over WebSockets."""

import random
import string
from typing import Any, Dict, List, Optional

from fastapi import WebSocket

from game.state import GameState

from .serialization import serialize_game_over, serialize_game_state


def _generate_room_code(length: int = 4) -> str:
    """Generate a random uppercase room code."""
    return "".join(random.choices(string.ascii_uppercase, k=length))


class Room:
    """A single game room holding a WebSocket connection per player."""

    def __init__(self, room_code: str):
        self.code: str = room_code
        self.players: List[Dict[str, Any]] = []  # {"name": str, "ws": WebSocket}
        self.game: Optional[GameState] = None
        self.started: bool = False
        self.last_move: Optional[Dict[str, Any]] = None

    @property
    def player_count(self) -> int:
        return len(self.players)

    def add_player(self, name: str, ws: WebSocket) -> int:
        """Add a player and return their index."""
        index = len(self.players)
        self.players.append({"name": name, "ws": ws})
        return index

    def remove_player(self, ws: WebSocket) -> Optional[int]:
        """Remove a player by WebSocket reference. Return their former index or None."""
        for i, player in enumerate(self.players):
            if player["ws"] is ws:
                self.players.pop(i)
                return i
        return None

    def get_player_index(self, ws: WebSocket) -> Optional[int]:
        """Return the index of the player associated with the given WebSocket."""
        for i, player in enumerate(self.players):
            if player["ws"] is ws:
                return i
        return None

    async def broadcast(self, message: Dict[str, Any], exclude: Optional[WebSocket] = None):
        """Send a JSON message to all connected players, optionally excluding one."""
        for player in self.players:
            if player["ws"] is not exclude:
                await player["ws"].send_json(message)

    async def broadcast_game_state(self):
        """Send each player a personalised game-state snapshot (own rack only)."""
        if self.game is None:
            return
        for i, player in enumerate(self.players):
            state = serialize_game_state(self.game, i, last_move=self.last_move)
            await player["ws"].send_json(state)

    async def broadcast_game_over(self):
        """Send the game-over payload to all players."""
        if self.game is None:
            return
        payload = serialize_game_over(self.game)
        await self.broadcast(payload)


class RoomManager:
    """Central registry of active rooms."""

    def __init__(self):
        self.rooms: Dict[str, Room] = {}

    def create_room(self) -> Room:
        """Create a new room with a unique code."""
        for _ in range(100):
            code = _generate_room_code()
            if code not in self.rooms:
                room = Room(code)
                self.rooms[code] = room
                return room
        raise RuntimeError("Failed to generate unique room code")

    def get_room(self, code: str) -> Optional[Room]:
        """Look up a room by its code."""
        return self.rooms.get(code.upper())

    def remove_room(self, code: str):
        """Delete a room from the registry."""
        self.rooms.pop(code.upper(), None)
