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
        _font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        _bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        self.font = pygame.font.Font(_font_path, 22)
        self.score_font = pygame.font.Font(_bold_path, 20)
        self.button_font = pygame.font.Font(_font_path, 16)
        self.lang_button_font = pygame.font.Font(_font_path, 13)
        self.title_font = pygame.font.Font(_bold_path, 30)
        self.turn_font = pygame.font.Font(_font_path, 18)

        # Show player selection and name entry screens
        num_players = self._show_player_selection()
        player_names = self._get_player_names(num_players)

        # Initialize game components
        self.game = GameState(BOARD_SIZE, num_players=num_players)
        for i, name in enumerate(player_names):
            self.game.players[i].name = name
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
        self.show_game_over = False
        self._cached_breakdown = []
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

    def _get_player_names(self, num_players: int) -> list:
        """Show a name entry screen. Returns list of player names."""
        name_keys = ["player_1", "player_2", "player_3", "player_4"]
        defaults = [self.lang_manager.get_string(name_keys[i]) for i in range(num_players)]
        names = [""] * num_players
        active_idx = 0

        # Layout: center the whole block (title + fields + button) vertically
        field_h = 40
        field_gap = 50
        total_h = WINDOW_SIZE + RACK_HEIGHT
        block_h = 50 + num_players * field_gap + 70  # title + fields + gap + button
        block_top = (total_h - block_h) // 2
        title_y = block_top
        first_field_y = block_top + 60
        btn_y = first_field_y + num_players * field_gap + 20
        field_x = WINDOW_SIZE // 2 - 120
        field_w = 240

        start_label = self.lang_manager.get_string("start_game")
        start_btn = Button(
            (WINDOW_SIZE - 200) // 2, btn_y,
            200, 50, start_label, self.button_font,
        )

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if start_btn.handle_event(event):
                    return [n if n else defaults[i] for i, n in enumerate(names)]

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i in range(num_players):
                        fy = first_field_y + i * field_gap
                        if field_x <= event.pos[0] <= field_x + field_w and fy <= event.pos[1] <= fy + field_h:
                            active_idx = i

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_TAB or event.key == pygame.K_RETURN:
                        active_idx = (active_idx + 1) % num_players
                    elif event.key == pygame.K_BACKSPACE:
                        names[active_idx] = names[active_idx][:-1]
                    elif event.unicode and len(names[active_idx]) < 15:
                        names[active_idx] += event.unicode

            self.screen.fill(WHITE)

            # Title
            title = self.lang_manager.get_string("enter_names")
            title_surface = self.title_font.render(title, True, BLACK)
            self.screen.blit(title_surface, title_surface.get_rect(
                center=(WINDOW_SIZE // 2, title_y + 20)
            ))

            # Name fields
            for i in range(num_players):
                fy = first_field_y + i * field_gap
                border_color = TURN_INDICATOR_COLOR if i == active_idx else (180, 180, 180)
                pygame.draw.rect(self.screen, border_color, (field_x, fy, field_w, field_h), 2)

                display_text = names[i] if names[i] else defaults[i]
                text_color = BLACK if names[i] else (180, 180, 180)
                text_surface = self.font.render(display_text, True, text_color)
                self.screen.blit(text_surface, (field_x + 8, fy + 8))

            start_btn.draw(self.screen)
            pygame.display.flip()

    def _set_player_names(self):
        """Set player names based on the current language."""
        name_keys = ["player_1", "player_2", "player_3", "player_4"]
        for i, player in enumerate(self.game.players):
            player.name = self.lang_manager.get_string(name_keys[i])

    def _init_score_displays(self):
        """Create score displays arranged evenly across the top."""
        num = len(self.game.players)
        score_y = 8
        spacing = WINDOW_SIZE // num
        self.score_displays = [
            ScoreDisplay(spacing * i + PADDING, score_y, self.score_font)
            for i in range(num)
        ]

    def _update_submit_button(self):
        """Update submit button state and cached score breakdown."""
        if len(self.game.current_turn_tiles) == 0:
            self.submit_button.enabled = False
            self._cached_breakdown = []
        else:
            self.submit_button.enabled = self.game.word_validator.is_placement_valid()
            self._cached_breakdown = self.game.calculate_turn_score()

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

    def _draw_game_over(self):
        """Draw the game-over screen with a score breakdown table."""
        overlay = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE + RACK_HEIGHT))
        overlay.fill((30, 30, 30))
        self.screen.blit(overlay, (0, 0))

        center_x = WINDOW_SIZE // 2
        total_h = WINDOW_SIZE + RACK_HEIGHT

        # Title
        title = self.lang_manager.get_string("game_over")
        title_surface = self.title_font.render(title, True, WHITE)
        self.screen.blit(title_surface, title_surface.get_rect(center=(center_x, total_h // 4)))

        details = getattr(self.game, "end_game_details", [])
        if not details:
            return

        # Sort by final score descending
        ranked = sorted(details, key=lambda d: d["final_score"], reverse=True)

        # Table header
        header_y = total_h // 4 + 50
        col_name = center_x - 250
        col_words = center_x - 50
        col_tiles = center_x + 70
        col_final = center_x + 200
        gray = (160, 160, 160)

        for col_x, label in [
            (col_name, self.lang_manager.get_string("player_1").split()[0]),
            (col_words, self.lang_manager.get_string("score_words")),
            (col_tiles, self.lang_manager.get_string("score_tiles")),
            (col_final, self.lang_manager.get_string("score_final")),
        ]:
            hdr = self.button_font.render(label, True, gray)
            self.screen.blit(hdr, (col_x, header_y))

        # Table rows
        for i, detail in enumerate(ranked):
            y = header_y + 35 + i * 35
            is_winner = i == 0
            color = (255, 215, 0) if is_winner else WHITE

            name_s = self.font.render(detail["name"], True, color)
            self.screen.blit(name_s, (col_name, y))

            words_s = self.font.render(str(detail["word_score"]), True, color)
            self.screen.blit(words_s, (col_words, y))

            adj = detail["tile_deduction"] + detail["tile_bonus"]
            adj_str = f"{adj:+d}" if adj != 0 else "0"
            tiles_s = self.font.render(adj_str, True, color)
            self.screen.blit(tiles_s, (col_tiles, y))

            final_s = self.font.render(str(detail["final_score"]), True, color)
            self.screen.blit(final_s, (col_final, y))

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

        # Draw turn indicator below the score row
        turn_text = f"{self.lang_manager.get_string('turn')}: {self.game.current_player.name}"
        turn_surface = self.turn_font.render(turn_text, True, TURN_INDICATOR_COLOR)
        turn_rect = turn_surface.get_rect(center=(WINDOW_SIZE // 2, 38))
        self.screen.blit(turn_surface, turn_rect)

        # Draw remaining tile count near the rack
        bag_count = len(self.game.tile_bag)
        bag_text = self.lang_button_font.render(
            f"{self.lang_manager.get_string('tiles_left')}: {bag_count}",
            True, SCORE_COLOR
        )
        self.screen.blit(bag_text, (PADDING, self.rack.y + TILE_SIZE + 5))

        # Draw move score preview when tiles are placed
        if self._cached_breakdown:
            breakdown = self._cached_breakdown
            if breakdown:
                parts = [f"{word}: {score}" for word, score in breakdown]
                total = sum(s for _, s in breakdown)
                if len(parts) == 1:
                    preview = parts[0]
                else:
                    preview = " + ".join(parts) + f" = {total}"
                preview_surface = self.button_font.render(preview, True, TURN_INDICATOR_COLOR)
                preview_rect = preview_surface.get_rect(
                    center=(WINDOW_SIZE // 2, self.rack.y - 12)
                )
                self.screen.blit(preview_surface, preview_rect)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # --- Game over screen is modal (only quit exits) ---
                if self.show_game_over:
                    continue

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
                        if self.game.game_over:
                            self.show_game_over = True
                        else:
                            self._start_transition()

                # Handle pass button
                elif self.pass_button.handle_event(event):
                    self.game.next_player()
                    self._update_submit_button()
                    if self.game.game_over:
                        self.show_game_over = True
                    else:
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
                        dropped = False
                        if self.selected_tile is not None:
                            # Check if dropped on the rack — reorder tiles
                            rack = self.game.current_player.rack
                            drop_idx = self.rack.get_tile_index(event.pos, len(rack))
                            if drop_idx is not None and drop_idx != self.selected_tile:
                                tile = rack.pop(self.selected_tile)
                                rack.insert(drop_idx, tile)
                                dropped = True

                            # Check if dropped on the board — place tile
                            if not dropped:
                                board_pos = self.board.get_board_position(event.pos)
                                if board_pos:
                                    row, col = board_pos
                                    letter = rack[self.selected_tile]
                                    if letter == "_":
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
            if self.show_game_over:
                self._draw_game_over()
            pygame.display.flip()

if __name__ == "__main__":
    game = ScrabbleUI()
    game.run() 
