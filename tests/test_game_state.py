import unittest
from unittest.mock import patch, MagicMock
from typing import List, Optional
from game.state import GameState, Player
from game.constants import (
    LETTER_DISTRIBUTION,
    DOUBLE_LETTER_SCORE,
    TRIPLE_LETTER_SCORE,
    DOUBLE_WORD_SCORE,
    TRIPLE_WORD_SCORE,
)


class MockWordList:
    """A mock wordlist that treats all words as valid."""

    def __init__(self):
        self.words = set()

    def is_valid_word(self, word: str) -> bool:
        return word.lower() in self.words


def create_game_with_mock_wordlist(valid_words=None) -> GameState:
    """Create a GameState with a mock wordlist and empty racks (no random draws)."""
    with patch("game.state.WordList") as MockWL:
        mock_wl = MockWordList()
        if valid_words:
            mock_wl.words = {w.lower() for w in valid_words}
        MockWL.return_value = mock_wl
        game = GameState()
    # Clear racks so tests control tile placement exactly
    for player in game.players:
        game.tile_bag.extend(player.rack)
        player.rack.clear()
    return game


class TestLetterDistribution(unittest.TestCase):
    """Regression tests for the official Estonian Scrabble letter distribution."""

    def test_total_tile_count(self):
        """Total tiles should be 102 (100 letters + 2 blanks)."""
        total = sum(info["count"] for info in LETTER_DISTRIBUTION.values())
        self.assertEqual(total, 102)

    def test_high_frequency_letters(self):
        """Spot-check counts and points for common letters."""
        cases = [
            ("a", 10, 1),
            ("e", 9, 1),
            ("i", 9, 1),
            ("s", 8, 1),
            ("t", 7, 1),
        ]
        for letter, expected_count, expected_points in cases:
            with self.subTest(letter=letter):
                self.assertEqual(LETTER_DISTRIBUTION[letter]["count"], expected_count)
                self.assertEqual(LETTER_DISTRIBUTION[letter]["points"], expected_points)

    def test_estonian_special_characters(self):
        """Spot-check Estonian-specific letters."""
        cases = [
            ("õ", 2, 4),
            ("ä", 2, 5),
            ("ö", 2, 6),
            ("ü", 2, 5),
            ("š", 1, 10),
            ("ž", 1, 10),
        ]
        for letter, expected_count, expected_points in cases:
            with self.subTest(letter=letter):
                self.assertEqual(LETTER_DISTRIBUTION[letter]["count"], expected_count)
                self.assertEqual(LETTER_DISTRIBUTION[letter]["points"], expected_points)


class TestScoring(unittest.TestCase):
    """Regression tests for scoring logic."""

    def test_word_scored_once_for_multi_tile_placement(self):
        """Placing 3 tiles forming one word should score the word exactly once."""
        # "ema" = e(1) + m(2) + a(1) = 4, center DWS = 8
        game = create_game_with_mock_wordlist(valid_words={"ema"})
        player = game.current_player
        player.rack = ["e", "m", "a"]

        # Place "ema" horizontally through center
        game.place_tile(7, 6, 0)  # e
        game.place_tile(7, 7, 0)  # m (center = DWS)
        game.place_tile(7, 8, 0)  # a
        game.validate_current_placement()

        self.assertTrue(game.commit_turn())
        # e(1) + m(2) + a(1) = 4, ×2 for center DWS = 8
        self.assertEqual(game.players[0].score, 8)

    def test_letter_premium_not_reapplied_on_subsequent_turn(self):
        """A tile on a DLS should not get the premium again in later turns."""
        # (7,3) is a DLS. Place a 5-letter word spanning (7,3)-(7,7) so 'd'
        # lands on the DLS and the word crosses center.
        # Turn 2: extend the word so 'd' at (7,3) is part of the new word.
        # Assert 'd' contributes only base 2, not DLS-doubled 4.
        game = create_game_with_mock_wordlist(valid_words={"deima", "adeima"})

        # Turn 1: place "deima" at (7,3)-(7,7)
        # d at (7,3)=DLS, e at (7,4), i at (7,5), m at (7,6), a at (7,7)=DWS
        player1 = game.players[0]
        player1.rack = ["d", "e", "i", "m", "a"]
        game.place_tile(7, 3, 0)  # d on DLS
        game.place_tile(7, 4, 0)  # e
        game.place_tile(7, 5, 0)  # i
        game.place_tile(7, 6, 0)  # m
        game.place_tile(7, 7, 0)  # a on center (DWS)
        game.validate_current_placement()
        self.assertTrue(game.commit_turn())
        # d(2)×2(DLS) + e(1) + i(1) + m(2) + a(1) = 9, ×2 center DWS = 18
        self.assertEqual(game.players[0].score, 18)

        # Turn 2: player 2 places 'a' at (7,2) extending to "adeima"
        player2 = game.players[1]
        player2.rack = ["a"]
        game.place_tile(7, 2, 0)  # a at (7,2), no premium
        game.validate_current_placement()
        self.assertTrue(game.commit_turn())
        # "adeima": a(1) + d(2, base only — DLS used up) + e(1) + i(1) + m(2) + a(1) = 8
        # No premiums reapplied
        self.assertEqual(game.players[1].score, 8)

    def test_cross_words_scored_separately(self):
        """Placing a tile that forms both a horizontal and vertical word scores both."""
        # Use positions away from premium squares.
        # (4,6) and (6,6) have no premiums. Place existing tiles there.
        # Place 'm' at (5,6) — no premium — forming two "am" words.
        game = create_game_with_mock_wordlist(valid_words={"am"})
        game.board[7][7] = "x"  # not first move

        game.board[4][6] = "a"  # above (5,6)
        game.board[5][5] = "a"  # left of (5,6)

        player = game.current_player
        player.rack = ["m"]

        game.place_tile(5, 6, 0)  # m at (5,6) — no premium
        game.validate_current_placement()
        self.assertTrue(game.commit_turn())
        # "am" vertical (4,6)-(5,6): a(1)+m(2) = 3
        # "am" horizontal (5,5)-(5,6): a(1)+m(2) = 3
        # total = 6
        self.assertEqual(game.players[0].score, 6)


    def test_bingo_bonus_for_seven_tiles(self):
        """Using all 7 tiles in one turn awards a 50-point bonus."""
        game = create_game_with_mock_wordlist(valid_words={"seitset"})
        player = game.current_player
        player.rack = ["s", "e", "i", "t", "s", "e", "t"]

        # Place "seitset" horizontally through center (7,4)-(7,10)
        for i in range(7):
            game.place_tile(7, 4 + i, 0)

        game.validate_current_placement()
        self.assertTrue(game.commit_turn())

        # s(1)+e(1)+i(1)+t(1)+s(1)+e(1)+t(1) = 7
        # (7,7) is center DWS => 7 * 2 = 14
        # + 50 bingo bonus = 64
        self.assertEqual(game.players[0].score, 64)


class TestEndGameAdjustment(unittest.TestCase):
    """Tests for end-game score adjustment."""

    def test_player_who_empties_rack_gets_bonus(self):
        """When bag is empty and a player goes out, they get opponents' tile values."""
        game = create_game_with_mock_wordlist(valid_words={"ema"})
        game.tile_bag.clear()

        # Set up scores
        game.players[0].score = 50
        game.players[1].score = 40

        # Player 2 has remaining tiles: d(2) + ö(6) = 8
        game.players[1].rack = ["d", "ö"]

        # Player 1 places "ema" through center to empty rack
        game.players[0].rack = ["e", "m", "a"]
        game.place_tile(7, 6, 0)  # e
        game.place_tile(7, 7, 0)  # m (center = DWS)
        game.place_tile(7, 8, 0)  # a
        game.validate_current_placement()
        self.assertTrue(game.commit_turn())

        # Word score: e(1) + m(2) + a(1) = 4, x2 DWS = 8
        # End-game: player 1 gets +8 (opponents' tiles), player 2 gets -8
        self.assertEqual(game.players[0].score, 50 + 8 + 8)  # 66
        self.assertEqual(game.players[1].score, 40 - 8)  # 32

    def test_no_empty_rack_both_lose_tiles(self):
        """When no player empties rack, both lose remaining tile values."""
        game = create_game_with_mock_wordlist(valid_words=set())
        game.tile_bag.clear()

        game.players[0].score = 30
        game.players[1].score = 25

        # Player 1 has: s(1) + d(2) = 3
        game.players[0].rack = ["s", "d"]
        # Player 2 has: ä(5) + f(8) = 13
        game.players[1].rack = ["ä", "f"]

        game.apply_end_game_adjustment()

        self.assertEqual(game.players[0].score, 27)  # 30 - 3
        self.assertEqual(game.players[1].score, 12)   # 25 - 13


class TestTileExchange(unittest.TestCase):
    """Tests for tile exchange logic."""

    def test_exchange_tiles_success(self):
        """Exchange works when the bag has enough tiles."""
        game = create_game_with_mock_wordlist()
        player = game.current_player
        player.rack = ["a", "b", "c", "d", "e"]
        original_bag_size = len(game.tile_bag)

        result = game.exchange_tiles([0, 2])  # exchange 'a' and 'c'

        self.assertTrue(result)
        # Rack should still have 5 tiles (3 kept + 2 drawn)
        self.assertEqual(len(player.rack), 5)
        # Bag size should stay the same (drew 2, returned 2)
        self.assertEqual(len(game.tile_bag), original_bag_size)

    def test_exchange_fails_when_bag_too_small(self):
        """Exchange fails when the bag has fewer than 7 tiles."""
        game = create_game_with_mock_wordlist()
        player = game.current_player
        player.rack = ["a", "b", "c"]
        game.tile_bag = ["x", "y", "z"]  # only 3 tiles in bag

        result = game.exchange_tiles([0])

        self.assertFalse(result)
        # Rack should be unchanged
        self.assertEqual(player.rack, ["a", "b", "c"])

    def test_exchange_switches_player(self):
        """After a successful exchange, it becomes the next player's turn."""
        game = create_game_with_mock_wordlist()
        game.players[0].rack = ["a", "b", "c"]
        self.assertEqual(game.current_player_idx, 0)

        game.exchange_tiles([0])

        self.assertEqual(game.current_player_idx, 1)

    def test_exchange_fails_with_tiles_on_board(self):
        """Exchange is not allowed if tiles have been placed this turn."""
        game = create_game_with_mock_wordlist()
        player = game.current_player
        player.rack = ["a", "b", "c"]
        game.place_tile(7, 7, 0)  # place 'a' on the board

        result = game.exchange_tiles([0])

        self.assertFalse(result)

    def test_exchange_fails_with_invalid_indices(self):
        """Exchange fails when tile indices are out of range."""
        game = create_game_with_mock_wordlist()
        game.current_player.rack = ["a", "b"]

        self.assertFalse(game.exchange_tiles([5]))
        self.assertFalse(game.exchange_tiles([-1]))

    def test_exchange_fails_with_empty_indices(self):
        """Exchange fails when no tile indices are provided."""
        game = create_game_with_mock_wordlist()
        game.current_player.rack = ["a", "b"]

        self.assertFalse(game.exchange_tiles([]))


class TestBlankTiles(unittest.TestCase):
    """Tests for blank tile scoring behaviour."""

    def test_blank_tile_scores_zero_on_plain_square(self):
        """A blank tile should score 0 points regardless of its designated letter."""
        game = create_game_with_mock_wordlist(valid_words={"em"})
        game.board[7][7] = "x"  # ensure not first move

        game.board[5][5] = "e"  # existing tile to the left
        player = game.current_player
        player.rack = ["_"]

        # Place blank designated as 'm' at (5,6) — no premium
        game.place_tile(5, 6, 0, designated_letter="m")
        game.validate_current_placement()
        self.assertTrue(game.commit_turn())

        # "em": e(1) + blank-m(0) = 1
        self.assertEqual(game.players[0].score, 1)

    def test_blank_tile_no_letter_premium(self):
        """A blank on a DLS/TLS should still score 0 (0 * multiplier = 0)."""
        # (1, 5) is a TLS position
        self.assertIn((1, 5), TRIPLE_LETTER_SCORE)
        game = create_game_with_mock_wordlist(valid_words={"ea"})
        game.board[7][7] = "x"  # not first move
        game.board[1][4] = "e"  # existing tile adjacent

        player = game.current_player
        player.rack = ["_"]

        # Place blank designated as 'a' on TLS at (1,5)
        game.place_tile(1, 5, 0, designated_letter="a")
        game.validate_current_placement()
        self.assertTrue(game.commit_turn())

        # "ea": e(1) + blank-a(0, TLS ignored) = 1
        self.assertEqual(game.players[0].score, 1)

    def test_word_with_blank_still_gets_word_premium(self):
        """DWS/TWS should still apply to the whole word even if a blank is in it."""
        # (7,7) is DWS (center)
        self.assertIn((7, 7), DOUBLE_WORD_SCORE)
        game = create_game_with_mock_wordlist(valid_words={"ema"})

        player = game.current_player
        player.rack = ["e", "_", "a"]

        # Place "ema" through center: e at (7,6), blank-m at (7,7) (DWS), a at (7,8)
        game.place_tile(7, 6, 0)  # e
        game.place_tile(7, 7, 0, designated_letter="m")  # blank as 'm' on DWS
        game.place_tile(7, 8, 0)  # a

        game.validate_current_placement()
        self.assertTrue(game.commit_turn())

        # e(1) + blank-m(0) + a(1) = 2, x2 DWS = 4
        self.assertEqual(game.players[0].score, 4)

    def test_blank_tile_returns_as_underscore_on_remove(self):
        """Removing a placed blank should return '_' to the rack."""
        game = create_game_with_mock_wordlist()
        game.board[7][7] = "x"  # not first move

        player = game.current_player
        player.rack = ["_"]

        game.place_tile(5, 5, 0, designated_letter="a")
        self.assertEqual(player.rack, [])
        self.assertEqual(game.board[5][5], "a")

        game.remove_tile(5, 5)
        self.assertEqual(player.rack, ["_"])
        self.assertIsNone(game.board[5][5])
        self.assertNotIn((5, 5), game.blank_designations)

    def test_blank_tile_in_letter_distribution(self):
        """The blank tile should exist in LETTER_DISTRIBUTION with count 2 and 0 points."""
        self.assertIn("_", LETTER_DISTRIBUTION)
        self.assertEqual(LETTER_DISTRIBUTION["_"]["count"], 2)
        self.assertEqual(LETTER_DISTRIBUTION["_"]["points"], 0)


def create_multiplayer_game(num_players, valid_words=None) -> GameState:
    """Create a GameState with a given number of players and a mock wordlist."""
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


class TestMultiPlayer(unittest.TestCase):
    """Tests for 2-4 player support."""

    def test_invalid_player_count(self):
        """Creating a game with fewer than 2 or more than 4 players raises ValueError."""
        for count in (0, 1, 5, 10):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    create_multiplayer_game(count)

    def test_three_player_turn_cycling(self):
        """In a 3-player game, turns cycle through all three players."""
        game = create_multiplayer_game(3)
        self.assertEqual(len(game.players), 3)
        self.assertEqual(game.current_player_idx, 0)

        game.next_player()
        self.assertEqual(game.current_player_idx, 1)

        game.next_player()
        self.assertEqual(game.current_player_idx, 2)

        game.next_player()
        self.assertEqual(game.current_player_idx, 0)

    def test_four_player_turn_cycling(self):
        """In a 4-player game, turns cycle through all four players."""
        game = create_multiplayer_game(4)
        self.assertEqual(len(game.players), 4)

        for expected in [1, 2, 3, 0, 1]:
            game.next_player()
            self.assertEqual(game.current_player_idx, expected)

    def test_three_player_end_game_adjustment(self):
        """End-game adjustment works correctly with 3 players."""
        game = create_multiplayer_game(3, valid_words={"ema"})
        game.tile_bag.clear()

        game.players[0].score = 50
        game.players[1].score = 40
        game.players[2].score = 30

        # Player 2 and 3 have remaining tiles
        game.players[1].rack = ["d", "ö"]  # d(2) + ö(6) = 8
        game.players[2].rack = ["š"]  # š(10) = 10

        # Player 1 empties rack by placing "ema"
        game.players[0].rack = ["e", "m", "a"]
        game.place_tile(7, 6, 0)  # e
        game.place_tile(7, 7, 0)  # m (center = DWS)
        game.place_tile(7, 8, 0)  # a
        game.validate_current_placement()
        self.assertTrue(game.commit_turn())

        # Word score: e(1) + m(2) + a(1) = 4, x2 DWS = 8
        # End-game: player 1 gets +18 (8+10), player 2 gets -8, player 3 gets -10
        self.assertEqual(game.players[0].score, 50 + 8 + 18)  # 76
        self.assertEqual(game.players[1].score, 40 - 8)  # 32
        self.assertEqual(game.players[2].score, 30 - 10)  # 20

    def test_four_player_end_game_no_empty_rack(self):
        """When no player empties rack with 4 players, all lose remaining tile values."""
        game = create_multiplayer_game(4)
        game.tile_bag.clear()

        game.players[0].score = 40
        game.players[1].score = 35
        game.players[2].score = 30
        game.players[3].score = 25

        game.players[0].rack = ["a"]  # a(1) = 1
        game.players[1].rack = ["d"]  # d(2) = 2
        game.players[2].rack = ["õ"]  # õ(4) = 4
        game.players[3].rack = ["ž"]  # ž(10) = 10

        game.apply_end_game_adjustment()

        self.assertEqual(game.players[0].score, 39)  # 40 - 1
        self.assertEqual(game.players[1].score, 33)  # 35 - 2
        self.assertEqual(game.players[2].score, 26)  # 30 - 4
        self.assertEqual(game.players[3].score, 15)  # 25 - 10


if __name__ == "__main__":
    unittest.main()
