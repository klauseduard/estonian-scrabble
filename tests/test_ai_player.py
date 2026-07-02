"""Tests for the AI player (issue #33).

The AI validates candidate words against the STRICT dictionary
(compounding disabled): brute-force move generation finds Hunspell
compound seams a human never would, so the permissive dictionary is
not safe for it. These tests pin the move generator's behaviour and
the strict/permissive dictionary asymmetry.
"""

import unittest

try:
    import spylls  # noqa: F401

    HAS_SPYLLS = True
except ImportError:
    HAS_SPYLLS = False

from game.ai_player import Move, find_all_moves, select_move


def _empty_board():
    return [[None] * 15 for _ in range(15)]


class FixedWordList:
    """Accepts exactly the configured words."""

    def __init__(self, words):
        self.words = {w.lower() for w in words}

    def is_valid_word(self, word):
        return word.lower() in self.words


class TestMoveGeneration(unittest.TestCase):
    def test_first_move_finds_known_word_through_center(self):
        wl = FixedWordList(["maja"])
        moves = find_all_moves(_empty_board(), ["m", "a", "j", "a", "k", "t", "s"], wl, first_move=True)
        self.assertTrue(moves)
        words = {w for m in moves for w in m.words_formed}
        self.assertIn("maja", words)
        # Every move must cover the center square
        for move in moves:
            self.assertIn((7, 7), {(r, c) for r, c, _ in move.tiles})

    def test_no_valid_words_returns_no_moves(self):
        wl = FixedWordList([])
        move = select_move(_empty_board(), ["m", "a", "j", "a"], wl, first_move=True)
        self.assertIsNone(move)

    def test_medium_difficulty_picks_highest_score(self):
        wl = FixedWordList(["maja", "aja"])
        move = select_move(
            _empty_board(), ["m", "a", "j", "a"], wl, first_move=True, difficulty="medium"
        )
        self.assertIsNotNone(move)
        # 'maja' (m=2) always outscores 'aja'
        self.assertIn("maja", move.words_formed)

    def test_only_generates_words_the_wordlist_accepts(self):
        wl = FixedWordList(["aja"])
        moves = find_all_moves(_empty_board(), ["m", "a", "j", "a"], wl, first_move=True)
        for move in moves:
            for word in move.words_formed:
                self.assertTrue(wl.is_valid_word(word), f"AI generated unvalidated word {word!r}")


class TestStrongMode(unittest.TestCase):
    """Strong mode finds what fast mode structurally cannot (issue #40)."""

    def test_strong_finds_bingo_fast_does_not(self):
        """A 7-letter word from a scrambled rack: strong-only territory."""
        wl = FixedWordList(["kalurid"])
        rack = ["d", "i", "r", "u", "l", "a", "k"]  # scrambled

        fast_moves = find_all_moves(_empty_board(), rack, wl, first_move=True, mode="fast")
        fast_words = {w for m in fast_moves for w in m.words_formed}
        self.assertNotIn("kalurid", fast_words)

        strong_moves = find_all_moves(_empty_board(), rack, wl, first_move=True, mode="strong")
        strong_words = {w for m in strong_moves for w in m.words_formed}
        self.assertIn("kalurid", strong_words)

    def test_strong_uses_blank_tiles_scored_zero(self):
        wl = FixedWordList(["kass"])
        rack = ["k", "a", "s", "_"]

        fast_moves = find_all_moves(_empty_board(), rack, wl, first_move=True, mode="fast")
        self.assertEqual(fast_moves, [])  # fast never touches blanks

        move = select_move(_empty_board(), rack, wl, first_move=True, difficulty="strong")
        self.assertIsNotNone(move)
        self.assertIn("kass", move.words_formed)
        self.assertEqual(len(move.blanks), 1)
        # kass through the center DW: (k1 + a1 + s1 + blank 0) * 2
        self.assertEqual(move.raw_score, 6)

    def test_legacy_difficulty_names_still_work(self):
        wl = FixedWordList(["maja"])
        for legacy in ("easy", "medium", "hard"):
            with self.subTest(difficulty=legacy):
                move = select_move(
                    _empty_board(), ["m", "a", "j", "a"], wl, first_move=True, difficulty=legacy
                )
                self.assertIsNotNone(move)


@unittest.skipUnless(HAS_SPYLLS, "spylls not installed")
class TestStrictDictionaryForAI(unittest.TestCase):
    """The strict/permissive asymmetry that makes the AI safe (issue #33)."""

    @classmethod
    def setUpClass(cls):
        from wordlist import WordList

        cls.wordlist = WordList()
        if cls.wordlist._dict is None:
            raise unittest.SkipTest("Hunspell dictionary not available")
        cls.strict = cls.wordlist.strict

    def test_strict_rejects_compounds_permissive_accepts(self):
        """False negatives are fine for the AI; humans keep compounds."""
        for word in ["raudtee", "ööpäev", "jalgpall"]:
            with self.subTest(word=word):
                self.assertTrue(self.wordlist.is_valid_word(word))
                self.assertFalse(self.strict.is_valid_word(word))

    def test_both_reject_garbage_and_blocklist(self):
        for word in ["tköis", "kköiserbl", "öis", "tk", "xyzzy"]:
            with self.subTest(word=word):
                self.assertFalse(self.wordlist.is_valid_word(word))
                self.assertFalse(self.strict.is_valid_word(word))

    def test_both_accept_simple_words_and_inflections(self):
        for word in ["maja", "majadest", "kassi", "matš", "tee"]:
            with self.subTest(word=word):
                self.assertTrue(self.wordlist.is_valid_word(word))
                self.assertTrue(self.strict.is_valid_word(word))

    def test_dawg_generation_fast_and_valid(self):
        """The production DAWG generates instantly and only valid words."""
        import time

        if self.strict.dawg is None:
            self.skipTest("DAWG artifact not built")
        board = _empty_board()
        for c, ch in enumerate("silmad"):
            board[7][5 + c] = ch
        t0 = time.monotonic()
        moves = find_all_moves(board, ["k", "a", "s", "t", "m", "e", "_"], self.strict)
        elapsed = time.monotonic() - t0
        self.assertTrue(moves)
        self.assertLess(elapsed, 5.0)  # measured ~0.2 s; generous CI margin
        self.assertTrue(any(m.blanks for m in moves))
        # Spot-check words from a sample of moves against the dictionary
        for move in moves[:200]:
            for word in move.words_formed:
                self.assertTrue(self.strict.is_valid_word(word), f"{word!r} invalid")

    def test_ai_generation_produces_no_garbage(self):
        """Regression for the revert reason: generated words must be clean.

        With the permissive dictionary this rack generates compound-seam
        garbage; with the strict dictionary every word must be vowelled,
        not blocklisted, and strict-valid.
        """
        rack = ["s", "i", "l", "p", "k", "a", "e"]
        moves = find_all_moves(_empty_board(), rack, self.strict, first_move=True)
        self.assertTrue(moves, "AI should find moves with this rack")
        words = {w for m in moves for w in m.words_formed}
        vowels = set("aeiouõäöü")
        for word in words:
            with self.subTest(word=word):
                self.assertTrue(set(word) & vowels, f"vowelless word {word!r}")
                self.assertTrue(self.strict.is_valid_word(word))


if __name__ == "__main__":
    unittest.main()
