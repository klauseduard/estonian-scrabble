"""Tests for the FastAPI WebSocket server."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from game.state import GameState

from server.room import Room, RoomManager, _generate_room_code
from server.serialization import serialize_game_state, serialize_game_over


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MockWordList:
    """A mock wordlist that treats configured words as valid."""

    def __init__(self):
        self.words: set = set()

    def is_valid_word(self, word: str) -> bool:
        return word.lower() in self.words


def _create_game(num_players: int = 2, valid_words=None) -> GameState:
    """Create a GameState with a mock wordlist and empty racks."""
    with patch("game.state.WordList") as MockWL:
        mock_wl = MockWordList()
        if valid_words:
            mock_wl.words = {w.lower() for w in valid_words}
        MockWL.return_value = mock_wl
        game = GameState(num_players=num_players)
    for player in game.players:
        game.tile_bag.extend(player.rack)
        player.rack.clear()
    return game


def _make_ws() -> AsyncMock:
    """Return a mock WebSocket with send_json."""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# Room / RoomManager tests
# ---------------------------------------------------------------------------

class TestRoomCode(unittest.TestCase):
    """Room code generation."""

    def test_code_length_and_format(self):
        code = _generate_room_code()
        self.assertEqual(len(code), 4)
        self.assertTrue(code.isalpha())
        self.assertTrue(code.isupper())


class TestRoomManager(unittest.TestCase):
    """Room creation and lookup."""

    def test_create_and_get_room(self):
        mgr = RoomManager()
        room = mgr.create_room()
        self.assertIsInstance(room, Room)
        self.assertIs(mgr.get_room(room.code), room)

    def test_get_nonexistent_room(self):
        mgr = RoomManager()
        self.assertIsNone(mgr.get_room("ZZZZ"))

    def test_remove_room(self):
        mgr = RoomManager()
        room = mgr.create_room()
        code = room.code
        mgr.remove_room(code)
        self.assertIsNone(mgr.get_room(code))


class TestRoom(unittest.TestCase):
    """Room player management."""

    def test_add_and_count_players(self):
        room = Room("TEST")
        ws1 = _make_ws()
        ws2 = _make_ws()
        idx0 = room.add_player("Alice", ws1)
        idx1 = room.add_player("Bob", ws2)
        self.assertEqual(idx0, 0)
        self.assertEqual(idx1, 1)
        self.assertEqual(room.player_count, 2)

    def test_remove_player(self):
        room = Room("TEST")
        ws = _make_ws()
        room.add_player("Alice", ws)
        removed = room.remove_player(ws)
        self.assertEqual(removed, 0)
        self.assertEqual(room.player_count, 0)

    def test_remove_unknown_ws(self):
        room = Room("TEST")
        ws = _make_ws()
        self.assertIsNone(room.remove_player(ws))

    def test_get_player_index(self):
        room = Room("TEST")
        ws1, ws2 = _make_ws(), _make_ws()
        room.add_player("Alice", ws1)
        room.add_player("Bob", ws2)
        self.assertEqual(room.get_player_index(ws1), 0)
        self.assertEqual(room.get_player_index(ws2), 1)
        self.assertIsNone(room.get_player_index(_make_ws()))


# ---------------------------------------------------------------------------
# Serialization tests
# ---------------------------------------------------------------------------

class TestSerialization(unittest.TestCase):
    """GameState serialization with hidden-information enforcement."""

    def test_rack_only_visible_to_owner(self):
        """Player 0's rack must appear in their payload, not player 1's."""
        game = _create_game(num_players=2)
        game.players[0].rack = ["a", "b", "c"]
        game.players[1].rack = ["x", "y", "z"]

        state_p0 = serialize_game_state(game, player_index=0)
        state_p1 = serialize_game_state(game, player_index=1)

        self.assertEqual(state_p0["rack"], ["a", "b", "c"])
        self.assertEqual(state_p1["rack"], ["x", "y", "z"])
        # Ensure racks are not cross-leaked
        self.assertNotIn("x", state_p0["rack"])
        self.assertNotIn("a", state_p1["rack"])

    def test_board_serialized_fully(self):
        game = _create_game()
        game.board[7][7] = "e"
        state = serialize_game_state(game, player_index=0)
        self.assertEqual(state["board"][7][7], "e")
        self.assertIsNone(state["board"][0][0])

    def test_tiles_remaining_is_count(self):
        game = _create_game()
        state = serialize_game_state(game, player_index=0)
        self.assertEqual(state["tiles_remaining"], len(game.tile_bag))

    def test_current_turn_tiles_only_for_active_player(self):
        """Only the active player should receive current_turn_tiles."""
        game = _create_game()
        game.players[0].rack = ["a"]
        game.place_tile(7, 7, 0)

        state_p0 = serialize_game_state(game, player_index=0)
        state_p1 = serialize_game_state(game, player_index=1)

        self.assertEqual(len(state_p0["current_turn_tiles"]), 1)
        self.assertEqual(state_p1["current_turn_tiles"], [])

    def test_game_over_payload(self):
        game = _create_game()
        game.players[0].score = 50
        game.players[1].score = 30
        payload = serialize_game_over(game)
        self.assertEqual(payload["type"], "game_over")
        self.assertEqual(len(payload["scores"]), 2)
        self.assertEqual(payload["scores"][0]["score"], 50)


# ---------------------------------------------------------------------------
# WebSocket integration tests (async)
# ---------------------------------------------------------------------------

class TestWebSocketFlow(unittest.TestCase):
    """End-to-end game flow via the WebSocket handler functions."""

    def setUp(self):
        """Import handler functions and reset the global room manager."""
        from server.app import (
            _handle_create_room,
            _handle_join_room,
            _handle_start_game,
            _handle_place_tile,
            _handle_commit_turn,
            _handle_pass_turn,
            _handle_exchange_tiles,
            room_manager,
        )
        self.create_room = _handle_create_room
        self.join_room = _handle_join_room
        self.start_game = _handle_start_game
        self.place_tile = _handle_place_tile
        self.commit_turn = _handle_commit_turn
        self.pass_turn = _handle_pass_turn
        self.exchange_tiles = _handle_exchange_tiles
        self.room_manager = room_manager
        # Clear any leftover rooms
        self.room_manager.rooms.clear()

    def _run(self, coro):
        """Run an async coroutine synchronously."""
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_create_and_join_room(self):
        ws1 = _make_ws()
        ws2 = _make_ws()

        room = self._run(self.create_room(ws1, {"player_name": "Alice"}))
        self.assertIsNotNone(room)
        # Check room_created response
        ws1.send_json.assert_called_once()
        msg = ws1.send_json.call_args[0][0]
        self.assertEqual(msg["type"], "room_created")
        self.assertEqual(msg["player_index"], 0)

        room2 = self._run(
            self.join_room(ws2, {"room_code": room.code, "player_name": "Bob"})
        )
        self.assertIs(room2, room)
        self.assertEqual(room.player_count, 2)

    def test_join_nonexistent_room_returns_error(self):
        ws = _make_ws()
        result = self._run(
            self.join_room(ws, {"room_code": "ZZZZ", "player_name": "Bob"})
        )
        self.assertIsNone(result)
        msg = ws.send_json.call_args[0][0]
        self.assertEqual(msg["type"], "error")

    @patch("server.app.random.shuffle")
    @patch("server.app.GameState")
    def test_start_game_creates_game_state(self, MockGS, _mock_shuffle):
        """Starting a game with 2 players should create a GameState."""
        mock_game = MagicMock()
        mock_game.game_over = False
        mock_game.current_player_idx = 0
        mock_game.board = [[None] * 15 for _ in range(15)]
        mock_game.tile_bag = ["a"] * 80
        mock_game.current_turn_tiles = set()
        mock_game.players = [
            MagicMock(name="Alice", score=0, rack=["a", "b"]),
            MagicMock(name="Bob", score=0, rack=["c", "d"]),
        ]
        mock_game.calculate_turn_score.return_value = []
        MockGS.return_value = mock_game

        ws1, ws2 = _make_ws(), _make_ws()
        room = self._run(self.create_room(ws1, {"player_name": "Alice"}))
        self._run(self.join_room(ws2, {"room_code": room.code, "player_name": "Bob"}))
        self._run(self.start_game(ws1, room))

        self.assertTrue(room.started)
        MockGS.assert_called_once_with(num_players=2)

    def test_start_game_requires_two_players(self):
        ws = _make_ws()
        room = self._run(self.create_room(ws, {"player_name": "Alice"}))
        ws.send_json.reset_mock()

        self._run(self.start_game(ws, room))
        msg = ws.send_json.call_args[0][0]
        self.assertEqual(msg["type"], "error")
        self.assertFalse(room.started)

    def test_pass_turn_flow(self):
        """Passing turn should advance to next player."""
        ws1, ws2 = _make_ws(), _make_ws()
        room = self._run(self.create_room(ws1, {"player_name": "Alice"}))
        self._run(self.join_room(ws2, {"room_code": room.code, "player_name": "Bob"}))

        with patch("server.app.GameState") as MockGS, \
             patch("server.app.random.shuffle"):
            mock_game = MagicMock()
            mock_game.game_over = False
            mock_game.current_player_idx = 0
            mock_game.board = [[None] * 15 for _ in range(15)]
            mock_game.tile_bag = ["a"] * 80
            mock_game.current_turn_tiles = set()
            mock_game.players = [
                MagicMock(name="Alice", score=0, rack=["a"]),
                MagicMock(name="Bob", score=0, rack=["b"]),
            ]
            mock_game.calculate_turn_score.return_value = []
            MockGS.return_value = mock_game
            self._run(self.start_game(ws1, room))

        # Pass turn as player 0
        self._run(self.pass_turn(ws1, room))
        room.game.next_player.assert_called_once()

    def test_wrong_player_gets_error(self):
        """A non-active player attempting an action should receive an error."""
        ws1, ws2 = _make_ws(), _make_ws()
        room = self._run(self.create_room(ws1, {"player_name": "Alice"}))
        self._run(self.join_room(ws2, {"room_code": room.code, "player_name": "Bob"}))

        with patch("server.app.GameState") as MockGS, \
             patch("server.app.random.shuffle"):
            mock_game = MagicMock()
            mock_game.game_over = False
            mock_game.current_player_idx = 0
            mock_game.board = [[None] * 15 for _ in range(15)]
            mock_game.tile_bag = ["a"] * 80
            mock_game.current_turn_tiles = set()
            mock_game.players = [
                MagicMock(name="Alice", score=0, rack=["a"]),
                MagicMock(name="Bob", score=0, rack=["b"]),
            ]
            mock_game.calculate_turn_score.return_value = []
            MockGS.return_value = mock_game
            self._run(self.start_game(ws1, room))

        ws2.send_json.reset_mock()
        # Player 1 (Bob) tries to pass but it's player 0's turn
        self._run(self.pass_turn(ws2, room))
        msg = ws2.send_json.call_args[0][0]
        self.assertEqual(msg["type"], "error")
        self.assertIn("Not your turn", msg["message"])


if __name__ == "__main__":
    unittest.main()
