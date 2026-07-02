"""Tests for DAWG construction and DAWG-based move generation (issue #40).

Uses small hand-built DAWGs so the tests are fast and deterministic;
the full-dictionary DAWG is exercised by an integration test in
test_ai_player.py when the built artifact is available.
"""

import unittest

from game.ai_player import find_all_moves, select_move
from game.dawg import Dawg


def _empty_board():
    return [[None] * 15 for _ in range(15)]


class DawgWordList:
    """Minimal wordlist exposing a DAWG, as WordList().strict does."""

    def __init__(self, words):
        self.words = sorted(set(words))
        self.dawg = Dawg.build(iter(self.words))

    def is_valid_word(self, word):
        return self.dawg.is_word(word.lower())


class TestDawgStructure(unittest.TestCase):
    def test_membership(self):
        dawg = Dawg.build(iter(sorted(["maja", "majad", "oja", "ojad"])))
        for word in ["maja", "majad", "oja", "ojad"]:
            self.assertTrue(dawg.is_word(word))
        for word in ["ma", "majade", "oj", "kass", ""]:
            self.assertFalse(dawg.is_word(word))

    def test_suffix_sharing_compresses(self):
        # Shared "…jad" suffixes must merge into common nodes
        words = sorted(["majad", "ojad", "rajad", "kajad"])
        dawg = Dawg.build(iter(words))
        trie_upper_bound = sum(len(w) for w in words) + 1
        self.assertLess(len(dawg), trie_upper_bound)

    def test_build_rejects_unsorted_input(self):
        with self.assertRaises(ValueError):
            Dawg.build(iter(["oja", "maja"]))

    def test_save_load_roundtrip(self):
        import tempfile

        dawg = Dawg.build(iter(sorted(["maja", "oja"])))
        with tempfile.NamedTemporaryFile(suffix=".marshal") as f:
            dawg.save(f.name)
            loaded = Dawg.load(f.name)
        self.assertTrue(loaded.is_word("maja"))
        self.assertFalse(loaded.is_word("majad"))


class TestDawgMoveGeneration(unittest.TestCase):
    def test_first_move_through_center(self):
        wl = DawgWordList(["maja", "aja"])
        moves = find_all_moves(_empty_board(), ["m", "a", "j", "a", "k"], wl, first_move=True)
        self.assertTrue(moves)
        words = {w for m in moves for w in m.words_formed}
        self.assertEqual(words, {"maja", "aja"})
        for move in moves:
            self.assertIn((7, 7), move.positions)

    def test_finds_bingo_instantly(self):
        wl = DawgWordList(["kalurid"])
        rack = ["d", "i", "r", "u", "l", "a", "k"]  # scrambled
        moves = find_all_moves(_empty_board(), rack, wl, first_move=True)
        self.assertTrue(any(len(m.tiles) == 7 for m in moves))

    def test_cross_checks_respected(self):
        # Board has "maja" horizontally; extending vertically through its
        # letters must form valid cross-words only.
        wl = DawgWordList(["maja", "aja", "ma"])
        board = _empty_board()
        for c, ch in enumerate("maja"):
            board[7][6 + c] = ch
        moves = find_all_moves(board, ["m", "a", "j", "a"], wl, first_move=False)
        for move in moves:
            for word in move.words_formed:
                self.assertTrue(wl.is_valid_word(word), f"invalid cross-word {word!r}")

    def test_blank_plays_generated_and_marked(self):
        wl = DawgWordList(["kass"])
        moves = find_all_moves(_empty_board(), ["k", "a", "s", "_"], wl, first_move=True)
        blank_moves = [m for m in moves if m.blanks]
        self.assertTrue(blank_moves)
        move = select_move(_empty_board(), ["k", "a", "s", "_"], wl, first_move=True,
                           difficulty="strong")
        self.assertIn("kass", move.words_formed)
        self.assertEqual(len(move.blanks), 1)
        # (k1 + a1 + s1 + blank 0) * 2 for the center DW
        self.assertEqual(move.raw_score, 6)

    def test_easy_mode_picks_weaker_move(self):
        """Easy never returns the top-scoring move (given enough options)."""
        wl = DawgWordList(["maja", "aja", "ma", "aa"])
        rack = ["m", "a", "j", "a"]
        strong = select_move(_empty_board(), rack, wl, first_move=True, difficulty="strong")
        best_score = strong.raw_score
        for _ in range(10):
            easy = select_move(_empty_board(), rack, wl, first_move=True, difficulty="easy")
            self.assertLess(easy.raw_score, best_score)

    def test_dawg_and_brute_force_agree_on_small_case(self):
        """Both generators must find the identical move set."""

        class PlainWordList:
            def __init__(self, words):
                self.words = set(words)

            def is_valid_word(self, word):
                return word.lower() in self.words

        words = ["maja", "aja", "ma", "kaja"]
        rack = ["m", "a", "j", "a", "k"]
        dawg_moves = find_all_moves(_empty_board(), rack, DawgWordList(words), first_move=True)
        brute_moves = find_all_moves(
            _empty_board(), rack, PlainWordList(words), first_move=True, mode="strong"
        )

        def keys(moves):
            return {
                frozenset((r, c, l, (r, c) in m.blanks) for r, c, l in m.tiles)
                for m in moves
            }

        self.assertEqual(keys(dawg_moves), keys(brute_moves))


if __name__ == "__main__":
    unittest.main()
