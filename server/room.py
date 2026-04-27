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
    """A single game room holding a WebSocket connection per player.

    During a game, disconnected players have ``ws`` set to ``None`` so their
    slot (and rack) is preserved for reconnection.
    """

    def __init__(self, room_code: str):
        self.code: str = room_code
        # Each entry: {"name": str, "ws": WebSocket | None}
        self.players: List[Dict[str, Any]] = []
        self.game: Optional[GameState] = None
        self.started: bool = False
        self.last_move: Optional[Dict[str, Any]] = None
        self.public: bool = False  # visible in lobby for strangers to join
        # Challenge support: snapshot of game state before last commit
        self._pre_commit_snapshot: Optional[GameState] = None
        self._challengeable_player: Optional[str] = None  # name of player whose move can be challenged
        self._challenge_pending: Optional[Dict[str, Any]] = None  # active challenge info
        # Track which players have acknowledged a forced word
        self._force_acks: set = set()  # player names who clicked OK
        self._force_required_acks: set = set()  # player names who need to acknowledge

    @property
    def player_count(self) -> int:
        """Total player slots (including disconnected)."""
        return len(self.players)

    @property
    def connected_count(self) -> int:
        """Number of players currently connected."""
        return sum(1 for p in self.players if p["ws"] is not None)

    def add_player(self, name: str, ws: WebSocket) -> int:
        """Add a player and return their index."""
        index = len(self.players)
        self.players.append({"name": name, "ws": ws})
        return index

    def disconnect_player(self, ws: WebSocket) -> Optional[int]:
        """Mark a player as disconnected (preserve slot). Return index or None."""
        for i, player in enumerate(self.players):
            if player["ws"] is ws:
                player["ws"] = None
                return i
        return None

    def remove_player(self, ws: WebSocket) -> Optional[int]:
        """Remove a player entirely (pre-game only). Return index or None."""
        for i, player in enumerate(self.players):
            if player["ws"] is ws:
                self.players.pop(i)
                return i
        return None

    def reconnect_player(self, name: str, ws: WebSocket) -> Optional[int]:
        """Reconnect a disconnected player by name. Return index or None."""
        for i, player in enumerate(self.players):
            if player["name"] == name and player["ws"] is None:
                player["ws"] = ws
                return i
        return None

    def get_player_index(self, ws: WebSocket) -> Optional[int]:
        """Return the index of the player associated with the given WebSocket."""
        for i, player in enumerate(self.players):
            if player["ws"] is ws:
                return i
        return None

    def has_disconnected_player(self, name: str) -> bool:
        """Check if a player with this name is disconnected and can reconnect."""
        return any(p["name"] == name and p["ws"] is None for p in self.players)

    async def broadcast(self, message: Dict[str, Any], exclude: Optional[WebSocket] = None):
        """Send a JSON message to all connected players, optionally excluding one."""
        for player in self.players:
            ws = player["ws"]
            if ws is not None and ws is not exclude:
                await ws.send_json(message)

    def save_snapshot(self, player_name: str):
        """Save a lightweight snapshot of mutable game state before a commit.

        Only copies the data that changes during a commit (board, racks,
        scores, tile bag, etc.) — NOT the heavy WordList/Hunspell dictionary.
        """
        game = self.game
        if game is None:
            return
        self._pre_commit_snapshot = {
            "board": [row[:] for row in game.board],
            "players": [
                {"name": p.name, "score": p.score, "rack": p.rack[:]}
                for p in game.players
            ],
            "tile_bag": game.tile_bag[:],
            "current_player_idx": game.current_player_idx,
            "current_turn_tiles": set(game.current_turn_tiles),
            "blank_designations": dict(game.blank_designations),
            "consecutive_passes": game.consecutive_passes,
            "game_over": game.game_over,
            "first_move": game.first_move,
        }
        self._challengeable_player = player_name
        self._challenge_pending = None

    def restore_snapshot(self) -> bool:
        """Restore game state from the saved snapshot. Returns True on success."""
        snap = self._pre_commit_snapshot
        if snap is None or self.game is None:
            return False
        game = self.game
        game.board = [row[:] for row in snap["board"]]
        for i, pdata in enumerate(snap["players"]):
            game.players[i].name = pdata["name"]
            game.players[i].score = pdata["score"]
            game.players[i].rack = pdata["rack"][:]
        game.tile_bag = snap["tile_bag"][:]
        game.current_player_idx = snap["current_player_idx"]
        game.current_turn_tiles = set(snap["current_turn_tiles"])
        game.blank_designations = dict(snap["blank_designations"])
        game.consecutive_passes = snap["consecutive_passes"]
        game.game_over = snap["game_over"]
        game.first_move = snap["first_move"]
        # Clear deferred draw — move is being undone, no tiles should be drawn
        game._deferred_draw_count = 0
        game._deferred_draw_player_idx = None
        # Re-validate so word_validator state is consistent
        game.validate_current_placement()
        self._pre_commit_snapshot = None
        self._challengeable_player = None
        self._challenge_pending = None
        self._force_acks.clear()
        self._force_required_acks.clear()
        return True

    def clear_challenge(self, force_check: bool = True):
        """Clear challenge state and draw any deferred tiles.

        Called when the next player acts (place/pass/exchange), signalling
        that the previous move is accepted and the challenge window is closed.

        For forced words, the challenge window stays open until all other
        players have acknowledged. Set force_check=False to skip this guard.
        """
        if force_check and self._force_required_acks:
            # Forced word still waiting for acknowledgement — don't clear yet
            return
        if self.game is not None and self.game.has_deferred_draw:
            self.game.draw_deferred_tiles()
        self._pre_commit_snapshot = None
        self._challengeable_player = None
        self._challenge_pending = None
        self._force_acks.clear()
        self._force_required_acks.clear()

    def set_force_ack_required(self, committer_name: str):
        """Mark that all players except the committer must acknowledge a forced word."""
        self._force_acks.clear()
        self._force_required_acks = {
            p["name"] for p in self.players if p["name"] != committer_name
        }

    def add_force_ack(self, player_name: str) -> bool:
        """Record a player's acknowledgement. Returns True if all have acknowledged."""
        self._force_acks.add(player_name)
        return self._force_required_acks.issubset(self._force_acks)

    async def broadcast_game_state(self):
        """Send each player a personalised game-state snapshot (own rack only)."""
        if self.game is None:
            return
        for i, player in enumerate(self.players):
            ws = player["ws"]
            if ws is None:
                continue
            state = serialize_game_state(self.game, i, last_move=self.last_move)
            state["your_player_index"] = i
            await ws.send_json(state)

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
