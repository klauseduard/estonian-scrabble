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

``_make_ui`` now only fakes the word list. ScrabbleUI.__init__ used to run two
blocking modal loops (player count, then names), so the object could not be
built without driving a UI; those moved to module-level functions behind
``ScrabbleUI.from_setup_screens()``.
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

        with mock.patch("game.state.WordList") as mock_wordlist_cls:
            wordlist = MockWordList()
            wordlist.words = {w.lower() for w in valid_words}
            mock_wordlist_cls.return_value = wordlist
            ui = main.ScrabbleUI(num_players=len(names), player_names=list(names))
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


class TestConstruction(unittest.TestCase):
    """ScrabbleUI must be constructible from plain data.

    It used to gather the player count and names itself, by running two
    blocking modal loops from inside __init__ — so you could not build the
    object without driving a UI, and every test had to mock past them.
    """

    def test_constructs_from_plain_data_without_driving_any_ui(self):
        import main

        with mock.patch("game.state.WordList") as mock_wordlist_cls:
            mock_wordlist_cls.return_value = MockWordList()
            ui = main.ScrabbleUI(num_players=2, player_names=["Alice", "Bob"])

        self.assertEqual([p.name for p in ui.game.players], ["Alice", "Bob"])

    def test_player_names_are_optional(self):
        import main

        with mock.patch("game.state.WordList") as mock_wordlist_cls:
            mock_wordlist_cls.return_value = MockWordList()
            ui = main.ScrabbleUI(num_players=3)

        self.assertEqual(len(ui.game.players), 3)


class TestSetupScreenWiring(unittest.TestCase):
    """from_setup_screens() is the interactive entry point __main__ uses.

    Patchable at all only because the two screens are now module-level
    functions; as methods on a half-built object they were unreachable.
    """

    def test_answers_from_the_screens_reach_the_game(self):
        import main

        with (
            mock.patch("main.ask_player_count", return_value=3) as ask_count,
            mock.patch("main.ask_player_names", return_value=["X", "Y", "Z"]) as ask_names,
            mock.patch("game.state.WordList") as mock_wordlist_cls,
        ):
            mock_wordlist_cls.return_value = MockWordList()
            ui = main.ScrabbleUI.from_setup_screens()

        ask_count.assert_called_once()
        self.assertEqual(ask_names.call_args[0][1], 3, "name screen gets the chosen count")
        self.assertEqual([p.name for p in ui.game.players], ["X", "Y", "Z"])

    def test_the_window_is_opened_once_not_twice(self):
        """The presentation is built once and passed in, not rebuilt by __init__."""
        import main

        with (
            mock.patch("main.ask_player_count", return_value=2),
            mock.patch("main.ask_player_names", return_value=["A", "B"]),
            mock.patch("game.state.WordList") as mock_wordlist_cls,
            mock.patch("main._make_presentation", wraps=main._make_presentation) as make_pres,
        ):
            mock_wordlist_cls.return_value = MockWordList()
            main.ScrabbleUI.from_setup_screens()

        make_pres.assert_called_once()


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


class TestHandlersDirectly(ScrabbleUITestCase):
    """The payoff of splitting run() up.

    These paths — drag to place, right click to take back, rack reorder — were
    the deepest part of the old loop and the least covered, because reaching
    them meant driving the whole while/for/if stack. Now each handler can be
    called on its own.
    """

    def _ui_with_rack(self, letters="majakts"):
        ui = self._make_ui()
        ui.game.players[0].rack = list(letters)
        return ui

    def _rack_pos(self, ui, index=0):
        return (ui.rack.get_rack_position(len(ui.game.current_player.rack)), ui.rack.y + 5)

    def _square_pos(self, ui, row=7, col=7):
        x, y = ui.board.get_square_position(row, col)
        return (x + 5, y + 5)

    def test_dragging_a_tile_onto_the_board_plays_it(self):
        ui = self._ui_with_rack()
        target = self._square_pos(ui)

        ui._handle_event(self.click(self._rack_pos(ui)))
        ui._handle_event(self.release(target))

        self.assertEqual(ui.game.board[7][7], "m")
        self.assertNotIn("m", ui.game.players[0].rack[:1])
        self.assertFalse(ui.dragging)
        self.assertIsNone(ui.selected_tile)

    def test_right_click_takes_a_placed_tile_back(self):
        ui = self._ui_with_rack()
        target = self._square_pos(ui)
        ui._handle_event(self.click(self._rack_pos(ui)))
        ui._handle_event(self.release(target))

        ui._handle_event(self.click(target, button=3))

        self.assertIsNone(ui.game.board[7][7])
        self.assertIn("m", ui.game.players[0].rack)

    def test_dropping_back_on_the_rack_reorders_instead_of_placing(self):
        ui = self._ui_with_rack("majakts")
        before = list(ui.game.players[0].rack)
        rack = ui.rack

        ui.selected_tile = 0
        ui.dragging = True
        # Aim at the last rack slot.
        last_x = rack.get_rack_position(len(before)) + (len(before) - 1) * 40
        ui._handle_event(self.release((last_x + 5, rack.y + 5)))

        self.assertEqual(sorted(ui.game.players[0].rack), sorted(before))
        self.assertIsNone(ui.game.board[7][7], "must not have touched the board")

    def test_exchange_button_arms_mode_then_rack_clicks_toggle_selection(self):
        ui = self._ui_with_rack()

        ui._press_exchange_button()
        self.assertTrue(ui.exchange_mode)

        ui._handle_event(self.click(self._rack_pos(ui)))
        self.assertEqual(ui.exchange_selected, {0}, "click selects for exchange, not drag")
        self.assertFalse(ui.dragging)

        ui._handle_event(self.click(self._rack_pos(ui)))
        self.assertEqual(ui.exchange_selected, set(), "clicking again deselects")

    def test_finishing_a_turn_starts_a_transition(self):
        ui = self._ui_with_rack()
        ui.exchange_mode = True

        ui._finish_turn()

        self.assertFalse(ui.exchange_mode, "exchange mode is always cleared")
        self.assertTrue(ui.show_transition)
        self.assertFalse(ui.show_game_over)

    def test_finishing_a_turn_shows_game_over_when_the_game_ended(self):
        ui = self._ui_with_rack()
        ui.game.game_over = True

        ui._finish_turn()

        self.assertTrue(ui.show_game_over)
        self.assertFalse(ui.show_transition, "no transition once the game is over")


if __name__ == "__main__":
    unittest.main()
