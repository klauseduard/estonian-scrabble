"""Room management for multiplayer Scrabble over WebSockets."""

import asyncio
import random
import string
from typing import Any, Dict, List, Optional, Set

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
        # Each entry: {"name": str, "ws": WebSocket | None, "difficulty": str | None}
        self.players: List[Dict[str, Any]] = []
        self.game: Optional[GameState] = None
        self.started: bool = False
        self.last_move: Optional[Dict[str, Any]] = None
        self.move_history: List[Dict[str, Any]] = []
        self.public: bool = False  # visible in lobby for strangers to join
        # Optional per-turn time limit in seconds (issue #38); None = untimed
        self.turn_time_limit: Optional[float] = None
        self._turn_timer_task: Optional[Any] = None  # asyncio.Task
        self._turn_deadline: Optional[float] = None  # event-loop time
        # Optional chess clock (issue #39): total seconds per player.
        # clock_remaining may go negative — overtime is penalized 10 points
        # per started minute at game end, per tournament rules.
        self.game_time_limit: Optional[int] = None
        self.clock_remaining: List[float] = []
        self._clock_running_for: Optional[int] = None
        self._clock_started_at: Optional[float] = None
        # AI player tracking — indices of players controlled by the AI engine
        self.ai_players: Set[int] = set()
        # Challenge support: snapshot of game state before last commit
        self._pre_commit_snapshot: Optional[GameState] = None
        self._challengeable_player: Optional[str] = None  # name of player whose move can be challenged
        self._challenge_pending: Optional[Dict[str, Any]] = None  # active challenge info
        # Track which players have acknowledged a forced word
        self._force_acks: set = set()  # player indices who clicked OK
        self._force_required_acks: set = set()  # player indices who must acknowledge

    @property
    def player_count(self) -> int:
        """Total player slots (including disconnected)."""
        return len(self.players)

    @property
    def connected_count(self) -> int:
        """Number of human players currently connected (excludes AI)."""
        return sum(
            1 for i, p in enumerate(self.players)
            if p["ws"] is not None and i not in self.ai_players
        )

    def add_player(self, name: str, ws: WebSocket) -> int:
        """Add a player and return their index."""
        index = len(self.players)
        self.players.append({"name": name, "ws": ws})
        return index

    def add_ai_player(self, name: str, difficulty: str = "medium") -> int:
        """Add an AI player (no WebSocket connection) and return their index."""
        index = len(self.players)
        self.players.append({"name": name, "ws": None, "difficulty": difficulty})
        self.ai_players.add(index)
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
        """Check if a human player with this name is disconnected and can reconnect."""
        return any(
            p["name"] == name and p["ws"] is None and i not in self.ai_players
            for i, p in enumerate(self.players)
        )

    def record_move(self, move: Dict[str, Any]):
        """Set the last move and append it to the game's move history."""
        self.last_move = move
        self.move_history.append(move)

    def turn_time_remaining(self) -> Optional[int]:
        """Seconds left on the current turn's timer, or None if untimed."""
        if self._turn_deadline is None:
            return None
        loop = asyncio.get_event_loop()
        return max(0, int(round(self._turn_deadline - loop.time())))

    def cancel_turn_timer(self):
        """Cancel any running turn timer."""
        if self._turn_timer_task is not None:
            self._turn_timer_task.cancel()
            self._turn_timer_task = None
        self._turn_deadline = None

    # ---- Chess clock (issue #39) ----

    def init_game_clock(self, num_players: int):
        """Give every player their full time budget at game start."""
        if self.game_time_limit:
            self.clock_remaining = [float(self.game_time_limit)] * num_players

    def start_clock(self, player_idx: int):
        """Start the given player's clock (stopping whichever was running)."""
        self.stop_clock()
        self._clock_running_for = player_idx
        self._clock_started_at = asyncio.get_event_loop().time()

    def stop_clock(self):
        """Stop the running clock and deduct the elapsed time."""
        if self._clock_running_for is None:
            return
        elapsed = asyncio.get_event_loop().time() - self._clock_started_at
        self.clock_remaining[self._clock_running_for] -= elapsed
        self._clock_running_for = None
        self._clock_started_at = None

    def clock_snapshot(self) -> Optional[Dict[str, Any]]:
        """Live per-player clock state for the game_state payload."""
        if not self.game_time_limit or not self.clock_remaining:
            return None
        remaining = list(self.clock_remaining)
        if self._clock_running_for is not None:
            elapsed = asyncio.get_event_loop().time() - self._clock_started_at
            remaining[self._clock_running_for] -= elapsed
        return {
            "remaining": [int(round(r)) for r in remaining],
            "running_for": self._clock_running_for,
        }

    def time_penalties(self) -> Optional[List[int]]:
        """Overtime penalties at game end: 10 points per started minute."""
        if not self.game_time_limit or not self.clock_remaining:
            return None
        self.stop_clock()
        return [
            int(-(-max(0.0, -r) // 60)) * 10  # ceil(overtime / 60) * 10
            for r in self.clock_remaining
        ]

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
            "end_game_applied": getattr(game, "_end_game_applied", False),
            "end_game_details": [
                dict(d) for d in getattr(game, "end_game_details", [])
            ],
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
        # Undo any end-game adjustment applied by the retracted move —
        # otherwise the guard flag stays set and the real game end would
        # silently skip the tile adjustment (issue #36).
        game._end_game_applied = snap["end_game_applied"]
        game.end_game_details = [dict(d) for d in snap["end_game_details"]]
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
        """Mark that all human players except the committer must acknowledge a forced word.

        Tracked by player index, not name — names are not guaranteed
        unique across the room's lifetime (issue #36).
        """
        self._force_acks.clear()
        self._force_required_acks = {
            i for i, p in enumerate(self.players)
            if p["name"] != committer_name and i not in self.ai_players
        }

    def add_force_ack(self, player_index: int) -> bool:
        """Record a required player's acknowledgement.

        Acks from players outside the required set are ignored.
        Returns True once every required player has acknowledged.
        """
        if player_index in self._force_required_acks:
            self._force_acks.add(player_index)
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
            state["move_history"] = self.move_history
            state["ai_players"] = sorted(self.ai_players)
            state["turn_time_limit"] = self.turn_time_limit
            state["turn_time_remaining"] = self.turn_time_remaining()
            state["game_clock"] = self.clock_snapshot()
            await ws.send_json(state)

    async def broadcast_game_over(self):
        """Send the game-over payload to all players."""
        if self.game is None:
            return
        self.cancel_turn_timer()
        payload = serialize_game_over(self.game, time_penalties=self.time_penalties())
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
