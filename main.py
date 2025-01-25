import pygame
import sys
from game import GameState
from ui import (
    Tile, Board, Rack, Button, ScoreDisplay, TurnIndicator,
    WHITE, BLACK, BOARD_COLOR,
    PREMIUM_TRIPLE_WORD, PREMIUM_DOUBLE_WORD,
    PREMIUM_TRIPLE_LETTER, PREMIUM_DOUBLE_LETTER,
    CURRENT_TURN_COLOR, VALID_WORD_COLOR, INVALID_WORD_COLOR
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
        
        # Initialize game components
        self.game = GameState(BOARD_SIZE)
        # Set player names based on current language
        self.game.players[0].name = self.lang_manager.get_string("player_1")
        self.game.players[1].name = self.lang_manager.get_string("player_2")
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
        
        # Initialize score displays
        score_y = PADDING
        self.score_displays = [
            ScoreDisplay(PADDING, score_y, self.font),
            ScoreDisplay(WINDOW_SIZE - 200, score_y, self.font)
        ]
        
        # Initialize turn indicator
        self.turn_indicator = TurnIndicator(WINDOW_SIZE // 2, score_y + 10, self.font)
        
        # UI state
        self.selected_tile = None
        self.dragging = False
        self.drag_pos = (0, 0)
        self._update_submit_button()

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
        self.game.players[0].name = self.lang_manager.get_string("player_1")
        self.game.players[1].name = self.lang_manager.get_string("player_2")
        self.submit_button.text = self.lang_manager.get_string("submit_turn")
        self.pass_button.text = self.lang_manager.get_string("pass_turn")
        self.lang_button.text = self.lang_manager.get_string("lang_button")  # Update language button text

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
                    Tile(tile, TILE_SIZE, self.font).draw(self.screen, x, y)

    def draw_rack(self):
        rack_x = self.rack.get_rack_position(len(self.game.current_player.rack))
        for i, letter in enumerate(self.game.current_player.rack):
            if self.selected_tile != i or self.dragging:
                x = rack_x + i * TILE_SIZE
                Tile(letter, TILE_SIZE, self.font).draw(self.screen, x, self.rack.y)

    def draw_dragged_tile(self):
        if self.dragging and self.selected_tile is not None:
            letter = self.game.current_player.rack[self.selected_tile]
            x, y = self.drag_pos
            x -= TILE_SIZE // 2
            y -= TILE_SIZE // 2
            Tile(letter, TILE_SIZE, self.font).draw(self.screen, x, y)

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
            
        # Draw turn indicator
        self.turn_indicator.draw(self.screen, self.game.current_player_idx == 0)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                # Handle language toggle button
                if self.lang_button.handle_event(event):
                    self.lang_manager.toggle_language()
                    self._update_ui_text()
                
                # Handle submit button
                elif self.submit_button.handle_event(event):
                    if self.game.commit_turn():
                        self._update_submit_button()
                
                # Handle pass button
                elif self.pass_button.handle_event(event):
                    self.game.next_player()
                    self._update_submit_button()
                
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
            pygame.display.flip()

if __name__ == "__main__":
    game = ScrabbleUI()
    game.run() 
