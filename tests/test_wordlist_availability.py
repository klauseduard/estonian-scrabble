"""Tests for how WordList behaves when its dictionary cannot be loaded.

A Scrabble validator that cannot load its dictionary used to log the error and
carry on with ``_dict = None``, after which ``is_valid_word`` returned False for
every word. To a player that is indistinguishable from "your word is not in the
dictionary", so a broken install looked exactly like a working game with a very
small vocabulary. These tests pin the loud-failure behaviour that replaced it.

They also pin the degradations that are legitimate and must NOT start raising:
a missing DAWG falls back to brute-force move generation, and a missing patched
dictionary falls back to the upstream one.
"""

import unittest
from unittest import mock

try:
    import spylls  # noqa: F401

    HAS_SPYLLS = True
except ImportError:
    HAS_SPYLLS = False

from wordlist import DictionaryUnavailableError, WordList


@unittest.skipUnless(HAS_SPYLLS, "spylls not installed")
class TestDictionaryLoadFailure(unittest.TestCase):
    """A dictionary that will not load must fail loudly, not silently."""

    def test_load_failure_raises_rather_than_rejecting_every_word(self):
        with (
            mock.patch.object(WordList, "_ensure_dictionary"),
            mock.patch(
                "spylls.hunspell.Dictionary.from_files", side_effect=OSError("disk on fire")
            ),
        ):
            with self.assertRaises(DictionaryUnavailableError):
                WordList()

    def test_error_reports_the_underlying_cause(self):
        """The message must be actionable — the original error is the useful part."""
        with (
            mock.patch.object(WordList, "_ensure_dictionary"),
            mock.patch(
                "spylls.hunspell.Dictionary.from_files", side_effect=OSError("disk on fire")
            ),
        ):
            with self.assertRaises(DictionaryUnavailableError) as ctx:
                WordList()
        self.assertIn("disk on fire", str(ctx.exception))

    def test_strict_dictionary_failure_raises(self):
        """The AI's strict validator has the same failure shape as the main one."""
        wordlist = WordList()
        with mock.patch(
            "spylls.hunspell.Dictionary.from_files", side_effect=OSError("no strict dict")
        ):
            with self.assertRaises(DictionaryUnavailableError):
                _ = wordlist.strict


@unittest.skipUnless(HAS_SPYLLS, "spylls not installed")
class TestLegitimateDegradation(unittest.TestCase):
    """Not every missing file is fatal. These fallbacks must keep working."""

    def test_missing_dawg_falls_back_without_raising(self):
        """No DAWG means brute-force move generation, not a dead game."""
        strict = WordList().strict
        strict._dawg = None
        strict._dawg_loaded = False
        with mock.patch("game.dawg.Dawg.load", side_effect=OSError("no dawg")):
            self.assertIsNone(strict.dawg)

    def test_missing_blocklist_falls_back_to_empty(self):
        """The blocklist is a refinement, not a prerequisite."""
        with mock.patch("builtins.open", side_effect=OSError("no blocklist")):
            self.assertEqual(WordList._load_blocked_words(mock.Mock()), set())


if __name__ == "__main__":
    unittest.main()
