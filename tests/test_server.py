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
        self.assertEqual(payload["scores"][0]["final_score"], 50)
        self.assertEqual(payload["scores"][0]["word_score"], 50)


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


class TestMoveHistory(unittest.TestCase):
    """The room keeps a full move history and sends it with the game state."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_record_move_sets_last_move_and_appends(self):
        room = Room("ABCD")
        first = {"action": "pass", "player_name": "Alice"}
        second = {"action": "exchange", "player_name": "Bob", "tile_count": 3}
        room.record_move(first)
        room.record_move(second)
        self.assertIs(room.last_move, second)
        self.assertEqual(room.move_history, [first, second])

    def test_pass_and_exchange_handlers_append_history(self):
        from server.app import (
            _handle_create_room,
            _handle_join_room,
            _handle_pass_turn,
            room_manager,
        )

        room_manager.rooms.clear()
        ws1, ws2 = _make_ws(), _make_ws()
        room = self._run(_handle_create_room(ws1, {"player_name": "Alice"}))
        self._run(_handle_join_room(ws2, {"room_code": room.code, "player_name": "Bob"}))
        room.game = _create_game(2)
        room.game.players[0].name = "Alice"
        room.game.players[1].name = "Bob"
        room.started = True

        self._run(_handle_pass_turn(ws1, room))
        self.assertEqual(len(room.move_history), 1)
        self.assertEqual(room.move_history[0]["action"], "pass")
        self.assertEqual(room.move_history[0]["player_name"], "Alice")

        self._run(_handle_pass_turn(ws2, room))
        self.assertEqual(len(room.move_history), 2)

    def test_broadcast_game_state_includes_move_history(self):
        room = Room("ABCD")
        room.game = _create_game(2)
        ws = _make_ws()
        room.add_player("Alice", ws)
        room.record_move({"action": "pass", "player_name": "Alice"})

        self._run(room.broadcast_game_state())
        payload = ws.send_json.call_args[0][0]
        self.assertEqual(payload["move_history"], [{"action": "pass", "player_name": "Alice"}])


class TestForceCommitVsAI(unittest.TestCase):
    """Force-commit is rejected without human opponents (issue #37).

    With only AI opponents the approval set would be empty and any
    garbage word would commit unopposed.
    """

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _make_room(self, opponent_is_ai):
        from server.app import _handle_create_room, room_manager

        room_manager.rooms.clear()
        ws = _make_ws()
        room = self._run(_handle_create_room(ws, {"player_name": "Klaus"}))
        if opponent_is_ai:
            room.add_ai_player("Arvuti", "medium")
        else:
            room.add_player("Mari", _make_ws())
        room.game = _create_game(2)
        room.game.players[0].name = "Klaus"
        room.game.players[1].name = "Arvuti" if opponent_is_ai else "Mari"
        room.game.players[0].rack = ["z", "s"]
        room.started = True
        return ws, room

    def test_force_commit_rejected_when_only_ai_opponents(self):
        from server.app import _handle_force_commit

        ws, room = self._make_room(opponent_is_ai=True)
        ws.send_json.reset_mock()
        self._run(_handle_force_commit(ws, room))
        msg = ws.send_json.call_args[0][0]
        self.assertEqual(msg["type"], "error")
        self.assertIn("Arvuti vastu", msg["message"])
        self.assertEqual(room.move_history, [])

    def test_force_commit_allowed_with_human_opponent(self):
        from server.app import _handle_force_commit

        ws, room = self._make_room(opponent_is_ai=False)
        ws.send_json.reset_mock()
        # Place a garbage word so the force-commit has something to commit
        room.game.place_tile(7, 7, 0)
        room.game.place_tile(7, 8, 0)
        self._run(_handle_force_commit(ws, room))
        # Not rejected by the AI guard: the move committed
        self.assertEqual(len(room.move_history), 1)
        self.assertEqual(room.move_history[0]["action"], "word")
        self.assertTrue(room.move_history[0]["forced"])


class TestTurnTimer(unittest.TestCase):
    """Optional per-turn time limit (issue #38)."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _make_started_room(self, turn_time_limit=None):
        from server.app import _handle_create_room, _handle_join_room, room_manager

        room_manager.rooms.clear()
        ws1, ws2 = _make_ws(), _make_ws()
        payload = {"player_name": "Alice"}
        if turn_time_limit is not None:
            payload["turn_time_limit"] = turn_time_limit
        room = self._run(_handle_create_room(ws1, payload))
        self._run(_handle_join_room(ws2, {"room_code": room.code, "player_name": "Bob"}))
        room.game = _create_game(2)
        room.game.players[0].name = "Alice"
        room.game.players[1].name = "Bob"
        room.started = True
        return room

    def test_create_room_accepts_allowed_limits(self):
        for limit in (60, 120, 300):
            with self.subTest(limit=limit):
                room = self._make_started_room(turn_time_limit=limit)
                self.assertEqual(room.turn_time_limit, limit)

    def test_create_room_rejects_invalid_limits(self):
        for limit in (45, -1, "60", True, 10_000):
            with self.subTest(limit=limit):
                room = self._make_started_room(turn_time_limit=limit)
                self.assertIsNone(room.turn_time_limit)

    def test_timer_not_armed_when_untimed_or_ai_turn(self):
        from server.app import _arm_turn_timer

        room = self._make_started_room()
        _arm_turn_timer(room)
        self.assertIsNone(room._turn_timer_task)

        room.turn_time_limit = 60
        room.ai_players = {room.game.current_player_idx}
        _arm_turn_timer(room)
        self.assertIsNone(room._turn_timer_task)
        room.cancel_turn_timer()

    def test_timeout_auto_passes_and_records_history(self):
        from server.app import _arm_turn_timer

        room = self._make_started_room()
        room.turn_time_limit = 0.05  # directly set a tiny limit for the test

        async def scenario():
            _arm_turn_timer(room)
            self.assertIsNotNone(room._turn_timer_task)
            self.assertIsNotNone(room.turn_time_remaining())
            # Prevent the handler re-arming for the next player after the
            # timeout fires, so exactly one auto-pass happens.
            room.turn_time_limit = None
            await asyncio.sleep(0.2)

        self._run(scenario())
        self.assertEqual(room.game.current_player_idx, 1)  # turn advanced
        self.assertEqual(len(room.move_history), 1)
        move = room.move_history[0]
        self.assertEqual(move["action"], "pass")
        self.assertTrue(move["timeout"])
        self.assertEqual(move["player_name"], "Alice")

    def test_rearm_cancels_previous_timer(self):
        from server.app import _arm_turn_timer

        room = self._make_started_room()
        room.turn_time_limit = 60

        async def scenario():
            _arm_turn_timer(room)
            first_task = room._turn_timer_task
            _arm_turn_timer(room)
            await asyncio.sleep(0)
            self.assertTrue(first_task.cancelled() or first_task.done())
            room.cancel_turn_timer()

        self._run(scenario())
        self.assertEqual(room.move_history, [])  # no timeout fired


class TestChessClock(unittest.TestCase):
    """Tournament chess clock with overtime penalties (issue #39)."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _make_started_room(self, **create_payload):
        from server.app import _handle_create_room, _handle_join_room, room_manager

        room_manager.rooms.clear()
        ws1, ws2 = _make_ws(), _make_ws()
        room = self._run(_handle_create_room(ws1, {"player_name": "Alice", **create_payload}))
        self._run(_handle_join_room(ws2, {"room_code": room.code, "player_name": "Bob"}))
        room.game = _create_game(2)
        room.game.players[0].name = "Alice"
        room.game.players[1].name = "Bob"
        room.init_game_clock(2)
        room.started = True
        return room

    def test_create_room_accepts_allowed_budgets(self):
        for limit in (300, 900, 1500):
            with self.subTest(limit=limit):
                room = self._make_started_room(game_time_limit=limit)
                self.assertEqual(room.game_time_limit, limit)
                self.assertEqual(room.clock_remaining, [float(limit)] * 2)

    def test_create_room_rejects_invalid_budgets(self):
        for limit in (299, "900", True, -300):
            with self.subTest(limit=limit):
                room = self._make_started_room(game_time_limit=limit)
                self.assertIsNone(room.game_time_limit)

    def test_chess_clock_wins_over_turn_timer(self):
        room = self._make_started_room(game_time_limit=900, turn_time_limit=60)
        self.assertEqual(room.game_time_limit, 900)
        self.assertIsNone(room.turn_time_limit)

    def test_clock_deducts_elapsed_time(self):
        room = self._make_started_room(game_time_limit=300)

        async def scenario():
            room.start_clock(0)
            await asyncio.sleep(0.1)
            room.stop_clock()

        self._run(scenario())
        self.assertLess(room.clock_remaining[0], 300.0)
        self.assertEqual(room.clock_remaining[1], 300.0)

    def test_clock_snapshot_reflects_running_player(self):
        room = self._make_started_room(game_time_limit=300)

        async def scenario():
            room.start_clock(1)
            return room.clock_snapshot()

        snap = self._run(scenario())
        room.stop_clock()
        self.assertEqual(snap["running_for"], 1)
        self.assertEqual(len(snap["remaining"]), 2)

    def test_time_penalties_ten_points_per_started_minute(self):
        room = self._make_started_room(game_time_limit=300)
        room.clock_remaining = [-1.0, 130.0]  # 1s overtime vs no overtime
        self.assertEqual(room.time_penalties(), [10, 0])
        room.clock_remaining = [-61.0, -120.0]  # 2nd minute started vs exactly 2 min
        self.assertEqual(room.time_penalties(), [20, 20])

    def test_game_over_payload_applies_penalties(self):
        from server.serialization import serialize_game_over

        game = _create_game(2)
        game.players[0].score = 100
        game.players[1].score = 90
        payload = serialize_game_over(game, time_penalties=[30, 0])
        self.assertEqual(payload["scores"][0]["time_penalty"], -30)
        self.assertEqual(payload["scores"][0]["final_score"], 70)
        self.assertEqual(payload["scores"][1]["time_penalty"], 0)
        self.assertEqual(payload["scores"][1]["final_score"], 90)

    def test_deep_overtime_backstop_auto_passes(self):
        from server.app import _arm_turn_timer

        room = self._make_started_room(game_time_limit=300)
        room.clock_remaining = [-601.0, 300.0]  # Alice past the overtime cap

        async def scenario():
            _arm_turn_timer(room)
            await asyncio.sleep(0.1)

        self._run(scenario())
        room.stop_clock()
        self.assertEqual(room.game.current_player_idx, 1)
        self.assertEqual(len(room.move_history), 1)
        self.assertTrue(room.move_history[0]["timeout"])


class TestInputValidation(unittest.TestCase):
    """Malformed WebSocket payloads must produce error frames, never exceptions.

    An uncaught exception used to escape the receive loop and skip disconnect
    cleanup, leaving a stale player slot and a wedged room (GitHub issue #34).
    """

    def setUp(self):
        from server.app import (
            _dispatch,
            _handle_chat,
            _handle_challenge,
            _handle_create_room,
            _handle_designate_blank,
            _handle_exchange_tiles,
            _handle_join_room,
            _handle_place_tile,
            _handle_remove_tile,
            room_manager,
        )

        self.dispatch = _dispatch
        self.chat = _handle_chat
        self.challenge = _handle_challenge
        self.designate_blank = _handle_designate_blank
        self.exchange_tiles = _handle_exchange_tiles
        self.place_tile = _handle_place_tile
        self.remove_tile = _handle_remove_tile
        room_manager.rooms.clear()

        # A started 2-player room with a real (mock-wordlist) game
        self.ws1, self.ws2 = _make_ws(), _make_ws()
        self.room = self._run(_handle_create_room(self.ws1, {"player_name": "Alice"}))
        self._run(
            _handle_join_room(self.ws2, {"room_code": self.room.code, "player_name": "Bob"})
        )
        self.game = _create_game(2)
        self.game.players[0].name = "Alice"
        self.game.players[1].name = "Bob"
        self.game.players[0].rack = ["a", "b", "c", "d", "e", "f", "_"]
        self.room.game = self.game
        self.room.started = True
        self.ws1.send_json.reset_mock()

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _assert_error(self, ws):
        msg = ws.send_json.call_args[0][0]
        self.assertEqual(msg["type"], "error")

    def test_place_tile_rejects_malformed_payloads(self):
        payloads = [
            {"row": "x", "col": 7, "tile_idx": 0},
            {"row": 999, "col": 7, "tile_idx": 0},
            {"row": [1], "col": 7, "tile_idx": 0},
            {"row": 7, "col": -1, "tile_idx": 0},
            {"row": 7, "col": 7, "tile_idx": "0"},
            {"row": 7, "col": 7, "tile_idx": 99},
            {"row": 7, "col": 7, "tile_idx": True},
            {"row": 7, "col": 7},
            {"row": 7, "col": 7, "tile_idx": 0, "designated_letter": "qq"},
            {"row": 7, "col": 7, "tile_idx": 0, "designated_letter": 5},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                self.ws1.send_json.reset_mock()
                self._run(self.place_tile(self.ws1, self.room, payload))
                self._assert_error(self.ws1)
                self.assertEqual(self.game.current_turn_tiles, set())

    def test_place_tile_still_works_with_valid_payload(self):
        self._run(self.place_tile(self.ws1, self.room, {"row": 7, "col": 7, "tile_idx": 0}))
        self.assertIn((7, 7), self.game.current_turn_tiles)

    def test_remove_tile_rejects_malformed_payloads(self):
        for payload in [{"row": [1], "col": 7}, {"row": 7}, {"row": 7, "col": 99}]:
            with self.subTest(payload=payload):
                self.ws1.send_json.reset_mock()
                self._run(self.remove_tile(self.ws1, self.room, payload))
                self._assert_error(self.ws1)

    def test_exchange_tiles_rejects_malformed_payloads(self):
        payloads = [
            {"tile_indices": 5},
            {"tile_indices": ["a"]},
            {"tile_indices": [True]},
            {"tile_indices": list(range(50))},
            {},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                self.ws1.send_json.reset_mock()
                self._run(self.exchange_tiles(self.ws1, self.room, payload))
                self._assert_error(self.ws1)

    def test_designate_blank_rejects_invalid_letter(self):
        # Place the blank first (rack index 6)
        self._run(
            self.place_tile(
                self.ws1, self.room, {"row": 7, "col": 7, "tile_idx": 6, "designated_letter": "a"}
            )
        )
        for payload in [
            {"row": 7, "col": 7, "letter": "qwerty"},
            {"row": 7, "col": 7, "letter": 5},
            {"row": 7, "col": 7},
            {"row": "x", "col": 7, "letter": "a"},
        ]:
            with self.subTest(payload=payload):
                self.ws1.send_json.reset_mock()
                self._run(self.designate_blank(self.ws1, self.room, payload))
                self._assert_error(self.ws1)
        # Board still holds the original designation
        self.assertEqual(self.game.board[7][7], "a")

    def test_chat_ignores_non_string_text(self):
        for payload in [{"text": 123}, {"text": ["hi"]}, {}]:
            with self.subTest(payload=payload):
                self.ws1.send_json.reset_mock()
                self.ws2.send_json.reset_mock()
                self._run(self.chat(self.ws1, self.room, payload))
                self.ws2.send_json.assert_not_called()

    def test_challenge_from_unknown_socket_gets_error(self):
        self.room.save_snapshot("Alice")
        stranger = _make_ws()
        self._run(self.challenge(stranger, self.room))
        self._assert_error(stranger)

    def test_dispatch_rejects_non_dict_action_and_unknown_action(self):
        ws = _make_ws()
        room = self._run(self.dispatch(ws, self.room, {"action": "no_such_action"}))
        self.assertIs(room, self.room)
        self._assert_error(ws)

    def test_create_room_rejects_non_string_name(self):
        ws = _make_ws()
        result = self._run(self.dispatch(ws, None, {"action": "create_room", "player_name": 42}))
        self.assertIsNone(result)
        self._assert_error(ws)

    def test_join_failure_keeps_existing_room_binding(self):
        """A failed join must not detach the socket from its current room."""
        result = self._run(
            self.dispatch(self.ws1, self.room, {"action": "join_room", "room_code": "ZZZZ"})
        )
        self.assertIs(result, self.room)


if __name__ == "__main__":
    unittest.main()
