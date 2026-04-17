import pygame
import sys
from typing import Optional
from game import GameState
from game.constants import LETTER_DISTRIBUTION
from ui import (
    Tile, Board, Rack, Button, ScoreDisplay,
    WHITE, BLACK, BOARD_COLOR, BLANK_TILE_COLOR,
    PREMIUM_TRIPLE_WORD, PREMIUM_DOUBLE_WORD,
    PREMIUM_TRIPLE_LETTER, PREMIUM_DOUBLE_LETTER,
    CURRENT_TURN_COLOR, VALID_WORD_COLOR, INVALID_WORD_COLOR,
    TURN_INDICATOR_COLOR, SCORE_COLOR,
)
from ui.language import LanguageManager

# Initialize Pygame
pygame.init()

# Constants
WINDOW_SIZE = 800
BOARD_SIZE = 15
TILE_SIZE = 40
RACK_HEIGHT = 120  # Increased to accommodate buttons below rack
BUTTON_WIDTH = 120  # Slightly smaller width
BUTTON_HEIGHT = 40  # Slightly smaller height
PADDING = 20
BUTTON_TEXT_SIZE = 24  # Smaller text size for buttons
LANG_BUTTON_SIZE = 30  # Smaller language button
LANG_BUTTON_PADDING = 5  # Smaller padding for language button

class ScrabbleUI:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE + RACK_HEIGHT))
        self.lang_manager = LanguageManager()
        pygame.display.set_caption(self.lang_manager.get_string("window_title"))
        self.font = pygame.font.Font(None, 36)  # Main font
        self.button_font = pygame.font.Font(None, BUTTON_TEXT_SIZE)  # Smaller font for buttons
        self.lang_button_font = pygame.font.Font(None, 20)  # Even smaller font for language button
        self.title_font = pygame.font.Font(None, 48)  # Title font for selection screen

        # Show player selection screen first
        num_players = self._show_player_selection()

        # Initialize game components
        self.game = GameState(BOARD_SIZE, num_players=num_players)
        # Set player names based on current language
        self._set_player_names()
        board_start = (WINDOW_SIZE - (BOARD_SIZE * TILE_SIZE)) // 2
        self.board = Board(BOARD_SIZE, TILE_SIZE, board_start, self.font)
        self.rack = Rack(WINDOW_SIZE - PADDING, TILE_SIZE, self.font)

        # Calculate rack width and position
        max_rack_tiles = 7
        rack_width = max_rack_tiles * TILE_SIZE
        rack_x = (WINDOW_SIZE - rack_width) // 2

        # Initialize UI controls
        button_y = WINDOW_SIZE + RACK_HEIGHT - BUTTON_HEIGHT - PADDING
        total_width = (BUTTON_WIDTH * 2) + PADDING
        start_x = (WINDOW_SIZE - total_width) // 2

        # Position Pass button on the left
        self.pass_button = Button(
            start_x,
            button_y,
            BUTTON_WIDTH,
            BUTTON_HEIGHT,
            self.lang_manager.get_string("pass_turn"),
            self.button_font
        )

        # Position Submit button on the right
        self.submit_button = Button(
            start_x + BUTTON_WIDTH + PADDING,
            button_y,
            BUTTON_WIDTH,
            BUTTON_HEIGHT,
            self.lang_manager.get_string("submit_turn"),
            self.button_font
        )

        # Add language toggle button in bottom-right corner, above the buttons
        self.lang_button = Button(
            WINDOW_SIZE - LANG_BUTTON_SIZE - LANG_BUTTON_PADDING,
            button_y + (BUTTON_HEIGHT - LANG_BUTTON_SIZE) // 2,  # Vertically center with other buttons
            LANG_BUTTON_SIZE,
            LANG_BUTTON_SIZE,
            self.lang_manager.get_string("lang_button"),
            self.lang_button_font
        )

        # Initialize score displays arranged across the top
        self._init_score_displays()

        # Turn transition state
        self.show_transition = False
        self.transition_player_name = ""
        self.transition_font = pygame.font.Font(None, 56)
        ready_w, ready_h = 200, 60
        ready_x = (WINDOW_SIZE - ready_w) // 2
        ready_y = (WINDOW_SIZE + RACK_HEIGHT) // 2 + 20
        self.ready_button = Button(
            ready_x, ready_y, ready_w, ready_h,
            self.lang_manager.get_string("ready"),
            self.button_font,
        )

        # UI state
        self.selected_tile = None
        self.dragging = False
        self.drag_pos = (0, 0)
        self._update_submit_button()

        # Letter choices for blank tile dialog (all real letters, no '_')
        self._blank_letters = sorted(
            [k for k in LETTER_DISTRIBUTION.keys() if k != "_"]
        )
        # Pending blank placement (row, col, tile_idx) while dialog is open
        self._pending_blank: tuple = None

    def _show_player_selection(self) -> int:
        """Show a simple player count selection screen. Returns chosen count."""
        selection_buttons = []
        btn_width = 180
        btn_height = 50
        total_width = btn_width * 3 + PADDING * 2
        start_x = (WINDOW_SIZE - total_width) // 2
        btn_y = (WINDOW_SIZE + RACK_HEIGHT) // 2

        for i, count in enumerate((2, 3, 4)):
            label = f"{count} {'Players' if self.lang_manager.get_current_language() == 'en' else 'Mängijat'}"
            btn = Button(
                start_x + i * (btn_width + PADDING),
                btn_y,
                btn_width,
                btn_height,
                label,
                self.button_font,
            )
            selection_buttons.append((btn, count))

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                for btn, count in selection_buttons:
                    if btn.handle_event(event):
                        return count

            self.screen.fill(WHITE)
            # Draw title
            title_text = self.lang_manager.get_string("select_players")
            title_surface = self.title_font.render(title_text, True, BLACK)
            title_rect = title_surface.get_rect(
                center=(WINDOW_SIZE // 2, btn_y - 60)
            )
            self.screen.blit(title_surface, title_rect)

            for btn, _ in selection_buttons:
                btn.draw(self.screen)

            pygame.display.flip()

    def _set_player_names(self):
        """Set player names based on the current language."""
        name_keys = ["player_1", "player_2", "player_3", "player_4"]
        for i, player in enumerate(self.game.players):
            player.name = self.lang_manager.get_string(name_keys[i])

    def _init_score_displays(self):
        """Create score displays arranged evenly across the top."""
        num = len(self.game.players)
        score_y = PADDING
        if num == 2:
            self.score_displays = [
                ScoreDisplay(PADDING, score_y, self.font),
                ScoreDisplay(WINDOW_SIZE - 200, score_y, self.font),
            ]
        else:
            # Evenly space across the top
            spacing = WINDOW_SIZE // num
            self.score_displays = [
                ScoreDisplay(spacing * i + PADDING, score_y, self.font)
                for i in range(num)
            ]

    def _update_submit_button(self):
        """Update submit button state based on word validity."""
        if len(self.game.current_turn_tiles) == 0:
            self.submit_button.enabled = False
        else:
            # Enable only if all words are valid
            self.submit_button.enabled = self.game.word_validator.is_placement_valid()

    def _update_ui_text(self):
        """Update all UI text elements after language change."""
        pygame.display.set_caption(self.lang_manager.get_string("window_title"))
        self._set_player_names()
        self.submit_button.text = self.lang_manager.get_string("submit_turn")
        self.pass_button.text = self.lang_manager.get_string("pass_turn")
        self.lang_button.text = self.lang_manager.get_string("lang_button")
        self.ready_button.text = self.lang_manager.get_string("ready")

    def _start_transition(self):
        """Activate the turn transition overlay for the current (already-switched) player."""
        self.show_transition = True
        self.transition_player_name = self.game.current_player.name

    def _draw_transition(self):
        """Draw an opaque overlay with 'Pass to: Player' text and a Ready button."""
        overlay = pygame.Surface(
            (WINDOW_SIZE, WINDOW_SIZE + RACK_HEIGHT)
        )
        overlay.fill((30, 30, 30))
        self.screen.blit(overlay, (0, 0))

        text = self.lang_manager.get_string("pass_to_player").format(
            player=self.transition_player_name
        )
        text_surface = self.transition_font.render(text, True, WHITE)
        text_rect = text_surface.get_rect(
            center=(WINDOW_SIZE // 2, (WINDOW_SIZE + RACK_HEIGHT) // 2 - 40)
        )
        self.screen.blit(text_surface, text_rect)

        self.ready_button.draw(self.screen)

    def _draw_blank_dialog(self):
        """Draw a modal overlay with a grid of letters for blank tile designation."""
        # Semi-transparent overlay
        overlay = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE + RACK_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        letters = self._blank_letters
        cols = 7
        rows = (len(letters) + cols - 1) // cols
        cell_size = 50
        grid_w = cols * cell_size
        grid_h = rows * cell_size
        title_h = 50
        dialog_w = grid_w + 40
        dialog_h = grid_h + title_h + 40
        dx = (WINDOW_SIZE - dialog_w) // 2
        dy = (WINDOW_SIZE + RACK_HEIGHT - dialog_h) // 2

        # Dialog background
        pygame.draw.rect(self.screen, WHITE, (dx, dy, dialog_w, dialog_h), border_radius=12)
        pygame.draw.rect(self.screen, BLACK, (dx, dy, dialog_w, dialog_h), 2, border_radius=12)

        # Title
        title_text = self.lang_manager.get_string("choose_letter")
        title_surf = self.font.render(title_text, True, BLACK)
        title_rect = title_surf.get_rect(center=(dx + dialog_w // 2, dy + title_h // 2))
        self.screen.blit(title_surf, title_rect)

        # Letter grid
        grid_x = dx + 20
        grid_y = dy + title_h + 10
        for idx, letter in enumerate(letters):
            r = idx // cols
            c = idx % cols
            cx = grid_x + c * cell_size
            cy = grid_y + r * cell_size
            rect = pygame.Rect(cx, cy, cell_size, cell_size)
            pygame.draw.rect(self.screen, (245, 235, 220), rect)
            pygame.draw.rect(self.screen, BLACK, rect, 1)
            ltr_surf = self.font.render(letter.upper(), True, BLACK)
            ltr_rect = ltr_surf.get_rect(center=rect.center)
            self.screen.blit(ltr_surf, ltr_rect)

    def _handle_blank_dialog_click(self, pos) -> Optional[str]:
        """Return the chosen letter if the click lands on one, else None."""
        letters = self._blank_letters
        cols = 7
        rows = (len(letters) + cols - 1) // cols
        cell_size = 50
        grid_w = cols * cell_size
        grid_h = rows * cell_size
        title_h = 50
        dialog_w = grid_w + 40
        dialog_h = grid_h + title_h + 40
        dx = (WINDOW_SIZE - dialog_w) // 2
        dy = (WINDOW_SIZE + RACK_HEIGHT - dialog_h) // 2
        grid_x = dx + 20
        grid_y = dy + title_h + 10

        mx, my = pos
        if mx < grid_x or my < grid_y:
            return None
        c = (mx - grid_x) // cell_size
        r = (my - grid_y) // cell_size
        if 0 <= c < cols and 0 <= r < rows:
            idx = r * cols + c
            if idx < len(letters):
                return letters[idx]
        return None

    def draw_board(self):
        # Fill background
        self.screen.fill(WHITE)
        
        # Draw board squares
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                # Determine square color based on state
                if (row, col) in self.game.word_validator.word_validity:
                    color = VALID_WORD_COLOR if self.game.word_validator.word_validity[(row, col)] else INVALID_WORD_COLOR
                elif (row, col) in self.game.current_turn_tiles:
                    color = CURRENT_TURN_COLOR
                else:
                    color = None  # Let the board handle premium square colors
                
                # Draw square and tile
                self.board.draw_square(self.screen, row, col, color)
                tile = self.game.board[row][col]
                if tile:
                    x, y = self.board.get_square_position(row, col)
                    is_blank = (row, col) in self.game.blank_designations
                    pts = 0 if is_blank else LETTER_DISTRIBUTION.get(tile.lower(), {}).get("points")
                    Tile(tile, TILE_SIZE, self.font, is_blank=is_blank, points=pts).draw(
                        self.screen, x, y
                    )

    def draw_rack(self):
        rack_x = self.rack.get_rack_position(len(self.game.current_player.rack))
        for i, letter in enumerate(self.game.current_player.rack):
            if self.selected_tile != i or self.dragging:
                x = rack_x + i * TILE_SIZE
                is_blank = letter == "_"
                pts = LETTER_DISTRIBUTION.get(letter.lower(), {}).get("points")
                Tile(letter, TILE_SIZE, self.font, is_blank=is_blank, points=pts).draw(
                    self.screen, x, self.rack.y
                )

    def draw_dragged_tile(self):
        if self.dragging and self.selected_tile is not None:
            letter = self.game.current_player.rack[self.selected_tile]
            x, y = self.drag_pos
            x -= TILE_SIZE // 2
            y -= TILE_SIZE // 2
            is_blank = letter == "_"
            pts = LETTER_DISTRIBUTION.get(letter.lower(), {}).get("points")
            Tile(letter, TILE_SIZE, self.font, is_blank=is_blank, points=pts).draw(
                self.screen, x, y
            )

    def draw_ui(self):
        # Draw submit button
        self.submit_button.draw(self.screen)
        # Draw pass button
        self.pass_button.draw(self.screen)
        # Draw language toggle button
        self.lang_button.draw(self.screen)

        # Draw player scores
        for i, player in enumerate(self.game.players):
            self.score_displays[i].draw(
                self.screen,
                player.name,
                player.score,
                i == self.game.current_player_idx
            )

        # Draw turn indicator (simple text showing current player name)
        turn_text = f"{self.lang_manager.get_string('turn')}: {self.game.current_player.name}"
        turn_surface = self.font.render(turn_text, True, TURN_INDICATOR_COLOR)
        turn_rect = turn_surface.get_rect(center=(WINDOW_SIZE // 2, PADDING + 30))
        self.screen.blit(turn_surface, turn_rect)

        # Draw remaining tile count near the rack
        bag_count = len(self.game.tile_bag)
        bag_text = self.lang_button_font.render(
            f"{self.lang_manager.get_string('tiles_left')}: {bag_count}",
            True, SCORE_COLOR
        )
        self.screen.blit(bag_text, (PADDING, self.rack.y + TILE_SIZE + 5))

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # --- Turn transition overlay is modal ---
                if self.show_transition:
                    if self.ready_button.handle_event(event):
                        self.show_transition = False
                    continue

                # --- Blank tile dialog is modal ---
                if self._pending_blank is not None:
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        chosen = self._handle_blank_dialog_click(event.pos)
                        if chosen is not None:
                            row, col, tile_idx = self._pending_blank
                            self._pending_blank = None
                            if self.game.place_tile(row, col, tile_idx, designated_letter=chosen):
                                self.game.validate_current_placement()
                                self._update_submit_button()
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self._pending_blank = None
                    continue

                # Handle language toggle button
                if self.lang_button.handle_event(event):
                    self.lang_manager.toggle_language()
                    self._update_ui_text()

                # Handle submit button
                elif self.submit_button.handle_event(event):
                    if self.game.commit_turn():
                        self._update_submit_button()
                        self._start_transition()

                # Handle pass button
                elif self.pass_button.handle_event(event):
                    self.game.next_player()
                    self._update_submit_button()
                    self._start_transition()

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        rack_idx = self.rack.get_tile_index(event.pos, len(self.game.current_player.rack))
                        if rack_idx is not None:
                            self.selected_tile = rack_idx
                            self.dragging = True
                            self.drag_pos = event.pos

                    elif event.button == 3:  # Right click
                        board_pos = self.board.get_board_position(event.pos)
                        if board_pos:
                            row, col = board_pos
                            if self.game.remove_tile(row, col):
                                self.game.validate_current_placement()
                                self._update_submit_button()

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and self.dragging:
                        board_pos = self.board.get_board_position(event.pos)
                        if board_pos and self.selected_tile is not None:
                            row, col = board_pos
                            letter = self.game.current_player.rack[self.selected_tile]
                            if letter == "_":
                                # Open blank tile dialog instead of placing immediately
                                if self.game.board[row][col] is None:
                                    self._pending_blank = (row, col, self.selected_tile)
                            else:
                                if self.game.place_tile(row, col, self.selected_tile):
                                    self.game.validate_current_placement()
                                    self._update_submit_button()
                        self.dragging = False
                        self.selected_tile = None

                elif event.type == pygame.MOUSEMOTION:
                    if self.dragging:
                        self.drag_pos = event.pos
                    # Update button hover states
                    self.submit_button.handle_event(event)
                    self.pass_button.handle_event(event)
                    self.lang_button.handle_event(event)

            self.draw_board()
            self.draw_rack()
            self.draw_ui()
            if self.dragging:
                self.draw_dragged_tile()
            if self._pending_blank is not None:
                self._draw_blank_dialog()
            if self.show_transition:
                self._draw_transition()
            pygame.display.flip()

if __name__ == "__main__":
    game = ScrabbleUI()
    game.run() 
