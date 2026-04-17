import unittest
from unittest.mock import patch, MagicMock
from typing import List, Optional
from game.state import GameState, Player
from game.constants import LETTER_DISTRIBUTION, DOUBLE_LETTER_SCORE, TRIPLE_LETTER_SCORE


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
        """Total letter tiles should be 100 (official is 102 minus 2 blanks)."""
        total = sum(info["count"] for info in LETTER_DISTRIBUTION.values())
        self.assertEqual(total, 100)

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


if __name__ == "__main__":
    unittest.main()
