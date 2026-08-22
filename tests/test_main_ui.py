"""Characterisation tests for the pygame event loop in main.ScrabbleUI.run().

`run()` is 152 lines and ten levels deep, and until now had no tests at all —
main.py sat at 0% coverage. These pin its current behaviour so it can be
extracted into named handlers without guessing at what it did.

They are characterisation tests: they describe what the loop does today, not
what it ought to do. If one of them starts failing during a refactor, the
refactor changed behaviour.

The loop is driven by scripting ``pygame.event.get`` frame by frame. One call
per ``while True`` iteration, so one list per frame, terminated by QUIT — which
the loop turns into ``sys.exit()``.

Note the mock in ``_make_ui``: ScrabbleUI.__init__ calls two blocking modal
loops (_show_player_selection, _get_player_names), so the object cannot be
built without driving a UI. That mock is load-bearing here and is the next
thing worth fixing.
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

from tests.test_server import MockWordList  # noqa: E402


class ScrabbleUITestCase(unittest.TestCase):
    """Builds a headless ScrabbleUI and drives its event loop."""

    @staticmethod
    def _quit_event():
        return pygame.event.Event(pygame.QUIT, {})

    @staticmethod
    def click(pos, button=1):
        return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": button})

    @staticmethod
    def release(pos, button=1):
        return pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": button})

    @classmethod
    def button_click(cls, rect):
        """A Button only fires on release, and only if it saw the press.

        See ui.components.Button.handle_event — MOUSEBUTTONDOWN just sets
        `pressed`. Sending only a down event silently does nothing, which is
        what the first draft of these tests got wrong.
        """
        return (cls.click(rect.center), cls.release(rect.center))

    @staticmethod
    def key(keycode):
        return pygame.event.Event(pygame.KEYDOWN, {"key": keycode, "unicode": ""})

    def _make_ui(self, names=("Alice", "Bob"), valid_words=()):
        import main

        with (
            mock.patch("game.state.WordList") as mock_wordlist_cls,
            mock.patch.object(main.ScrabbleUI, "_show_player_selection", return_value=len(names)),
            mock.patch.object(main.ScrabbleUI, "_get_player_names", return_value=list(names)),
        ):
            wordlist = MockWordList()
            wordlist.words = {w.lower() for w in valid_words}
            mock_wordlist_cls.return_value = wordlist
            ui = main.ScrabbleUI()
        return ui

    def drive(self, ui, *events):
        """Feed one event per frame, then QUIT.

        The frame list is padded with extra QUITs so a test that under-scripts
        gets a clean exit rather than a confusing StopIteration from the mock.
        """
        frames = [[event] for event in events]
        frames.extend([[self._quit_event()]] * 8)
        with (
            mock.patch("pygame.event.get", side_effect=frames),
            mock.patch("pygame.display.flip"),
            mock.patch("pygame.quit"),
        ):
            with self.assertRaises(SystemExit):
                ui.run()


class TestLoopExit(ScrabbleUITestCase):
    def test_quit_event_exits_the_process(self):
        """The one behaviour an extraction into handlers could silently drop."""
        ui = self._make_ui()
        with (
            mock.patch("pygame.event.get", side_effect=[[self._quit_event()]]),
            mock.patch("pygame.display.flip"),
            mock.patch("pygame.quit") as mock_quit,
        ):
            with self.assertRaises(SystemExit):
                ui.run()
        mock_quit.assert_called_once()


class TestNormalInteraction(ScrabbleUITestCase):
    """The non-modal path, so the modal tests below mean something."""

    def test_clicking_the_rack_selects_a_tile_and_starts_a_drag(self):
        ui = self._make_ui()
        self.assertIsNone(ui.selected_tile)

        self.drive(ui, self.click((400, ui.rack.y + 5)))

        self.assertIsNotNone(ui.selected_tile)
        self.assertTrue(ui.dragging)

    def test_language_button_toggles_language(self):
        ui = self._make_ui()
        before = ui.lang_manager.get_current_language()

        self.drive(ui, *self.button_click(ui.lang_button.rect))

        self.assertNotEqual(ui.lang_manager.get_current_language(), before)


class TestModalPrecedence(ScrabbleUITestCase):
    """Four overlays gate the loop, each with a bare `continue`.

    The order is game over -> turn transition -> blank dialog -> normal input.
    Extracting the loop into named handlers is exactly the change that gets
    this ordering wrong, so each layer is pinned separately.
    """

    def _rack_click(self, ui):
        return self.click((400, ui.rack.y + 5))

    def test_game_over_screen_swallows_input(self):
        ui = self._make_ui()
        ui.show_game_over = True

        self.drive(ui, self._rack_click(ui))

        self.assertIsNone(ui.selected_tile)
        self.assertFalse(ui.dragging)

    def test_transition_overlay_swallows_input(self):
        ui = self._make_ui()
        ui.show_transition = True

        self.drive(ui, self._rack_click(ui))

        self.assertTrue(ui.show_transition, "overlay should still be up")
        self.assertIsNone(ui.selected_tile)

    def test_transition_overlay_is_dismissed_by_the_ready_button(self):
        ui = self._make_ui()
        ui.show_transition = True

        self.drive(ui, *self.button_click(ui.ready_button.rect))

        self.assertFalse(ui.show_transition)

    def test_blank_dialog_swallows_rack_clicks(self):
        ui = self._make_ui()
        ui._pending_blank = (7, 7, 0)

        self.drive(ui, self._rack_click(ui))

        self.assertIsNone(ui.selected_tile)
        self.assertFalse(ui.dragging)

    def test_escape_cancels_the_blank_dialog(self):
        ui = self._make_ui()
        ui._pending_blank = (7, 7, 0)

        self.drive(ui, self.key(pygame.K_ESCAPE))

        self.assertIsNone(ui._pending_blank)

    def test_game_over_outranks_the_transition_overlay(self):
        """Both up at once: the game-over `continue` must win, so the ready
        button does not secretly dismiss the transition underneath."""
        ui = self._make_ui()
        ui.show_game_over = True
        ui.show_transition = True

        self.drive(ui, *self.button_click(ui.ready_button.rect))

        self.assertTrue(ui.show_transition)

    def test_transition_outranks_the_blank_dialog(self):
        ui = self._make_ui()
        ui.show_transition = True
        ui._pending_blank = (7, 7, 0)

        self.drive(ui, self.key(pygame.K_ESCAPE))

        self.assertIsNotNone(ui._pending_blank, "blank dialog must not see the key")


if __name__ == "__main__":
    unittest.main()
