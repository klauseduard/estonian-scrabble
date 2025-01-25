import pygame
from typing import Tuple, Optional
from game.constants import (
    TRIPLE_WORD_SCORE, DOUBLE_WORD_SCORE,
    TRIPLE_LETTER_SCORE, DOUBLE_LETTER_SCORE
)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BOARD_COLOR = (240, 230, 220)
PREMIUM_TRIPLE_WORD = (255, 102, 102)    # Red for triple word
PREMIUM_DOUBLE_WORD = (255, 182, 193)    # Pink for double word
PREMIUM_TRIPLE_LETTER = (0, 153, 204)    # Blue for triple letter
PREMIUM_DOUBLE_LETTER = (173, 216, 230)  # Light blue for double letter
SELECTED_COLOR = (255, 255, 0, 128)      # Semi-transparent yellow
CURRENT_TURN_COLOR = (200, 255, 200)     # Light green for current turn tiles
VALID_WORD_COLOR = (144, 238, 144)       # Light green for valid words
INVALID_WORD_COLOR = (255, 182, 193)     # Light red for invalid words
TILE_COLOR = (255, 235, 205)             # Beige for tiles
BUTTON_COLOR = (70, 130, 180)            # Steel blue for buttons
BUTTON_HOVER_COLOR = (100, 149, 237)     # Cornflower blue for button hover
BUTTON_DISABLED_COLOR = (169, 169, 169)  # Dark gray for disabled buttons
SCORE_COLOR = (47, 79, 79)               # Dark slate gray for score display
TURN_INDICATOR_COLOR = (34, 139, 34)    # Forest green for turn indicator

class Button:
    def __init__(self, x: int, y: int, width: int, height: int, text: str, font: pygame.font.Font):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.enabled = True
        self.hovered = False
        self.pressed = False
        # Shadow and border radius
        self.shadow_height = 4
        self.border_radius = 10

    def draw(self, screen: pygame.Surface):
        """Draw the button with appropriate colors based on state."""
        # Determine colors
        if not self.enabled:
            main_color = BUTTON_DISABLED_COLOR
            shadow_color = (main_color[0] * 0.8, main_color[1] * 0.8, main_color[2] * 0.8)
        else:
            if self.pressed:
                main_color = BUTTON_COLOR
                shadow_color = (main_color[0] * 0.7, main_color[1] * 0.7, main_color[2] * 0.7)
            elif self.hovered:
                main_color = BUTTON_HOVER_COLOR
                shadow_color = (main_color[0] * 0.8, main_color[1] * 0.8, main_color[2] * 0.8)
            else:
                main_color = BUTTON_COLOR
                shadow_color = (main_color[0] * 0.8, main_color[1] * 0.8, main_color[2] * 0.8)

        # Draw shadow
        shadow_rect = pygame.Rect(
            self.rect.x,
            self.rect.y + self.shadow_height,
            self.rect.width,
            self.rect.height
        )
        pygame.draw.rect(screen, shadow_color, shadow_rect, border_radius=self.border_radius)

        # Draw main button
        button_rect = pygame.Rect(
            self.rect.x,
            self.rect.y if self.pressed else self.rect.y - self.shadow_height,
            self.rect.width,
            self.rect.height
        )
        pygame.draw.rect(screen, main_color, button_rect, border_radius=self.border_radius)

        # Draw text with shadow
        text_surface = self.font.render(self.text, True, WHITE)
        text_rect = text_surface.get_rect(center=button_rect.center)
        
        if not self.enabled:
            # Draw disabled text slightly transparent
            text_surface.set_alpha(128)
        
        screen.blit(text_surface, text_rect)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle mouse events and return True if clicked."""
        if not self.enabled:
            return False

        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
            return False
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                self.pressed = True
                return False
        
        elif event.type == pygame.MOUSEBUTTONUP:
            was_pressed = self.pressed
            self.pressed = False
            if event.button == 1 and self.rect.collidepoint(event.pos) and was_pressed:
                return True
        
        return False

class ScoreDisplay:
    def __init__(self, x: int, y: int, font: pygame.font.Font):
        self.x = x
        self.y = y
        self.font = font

    def draw(self, screen: pygame.Surface, player_name: str, score: int, is_current: bool):
        """Draw the player's score with appropriate highlighting."""
        text = f"{player_name}: {score}"
        color = SCORE_COLOR if not is_current else BUTTON_COLOR
        text_surface = self.font.render(text, True, color)
        screen.blit(text_surface, (self.x, self.y))

class TurnIndicator:
    def __init__(self, x: int, y: int, font: pygame.font.Font):
        self.x = x
        self.y = y
        self.font = font
        self.arrow_size = 20
        self.padding = 10

    def draw(self, screen: pygame.Surface, is_player_one: bool):
        """Draw a turn indicator showing which player's turn it is."""
        # Draw arrow
        points = self._get_arrow_points(is_player_one)
        pygame.draw.polygon(screen, TURN_INDICATOR_COLOR, points)
        
        # Draw "Turn" text
        text = self.font.render("Turn", True, TURN_INDICATOR_COLOR)
        text_rect = text.get_rect(center=(self.x, self.y + self.arrow_size + self.padding))
        screen.blit(text, text_rect)
    
    def _get_arrow_points(self, is_player_one: bool) -> list:
        """Get the points for drawing the arrow polygon."""
        if is_player_one:
            # Arrow pointing left (from Player 1 to their score)
            return [
                (self.x + self.arrow_size, self.y - self.arrow_size//2),
                (self.x - self.arrow_size, self.y),
                (self.x + self.arrow_size, self.y + self.arrow_size//2)
            ]
        else:
            # Arrow pointing right (from Player 2 to their score)
            return [
                (self.x - self.arrow_size, self.y - self.arrow_size//2),
                (self.x + self.arrow_size, self.y),
                (self.x - self.arrow_size, self.y + self.arrow_size//2)
            ]

class Tile:
    def __init__(self, letter: str, size: int, font: pygame.font.Font):
        self.letter = letter
        self.size = size
        self.font = font

    def draw(self, screen: pygame.Surface, x: int, y: int):
        """Draw a single tile with letter."""
        # Draw tile background
        pygame.draw.rect(screen, TILE_COLOR, 
                        (x + 2, y + 2, self.size - 4, self.size - 4))
        
        # Draw letter
        text = self.font.render(self.letter.upper(), True, BLACK)
        text_rect = text.get_rect(center=(x + self.size // 2, y + self.size // 2))
        screen.blit(text, text_rect)

class Board:
    def __init__(self, size: int, tile_size: int, board_start: int, font: pygame.font.Font):
        self.size = size
        self.tile_size = tile_size
        self.board_start = board_start
        self.font = font
        self.small_font = pygame.font.Font(None, 20)  # Smaller font for premium labels

    def get_square_position(self, row: int, col: int) -> Tuple[int, int]:
        """Convert board coordinates to screen coordinates."""
        x = self.board_start + col * self.tile_size
        y = self.board_start + row * self.tile_size
        return x, y

    def get_board_position(self, screen_pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Convert screen coordinates to board coordinates."""
        x, y = screen_pos
        col = (x - self.board_start) // self.tile_size
        row = (y - self.board_start) // self.tile_size
        
        if 0 <= row < self.size and 0 <= col < self.size:
            return row, col
        return None

    def get_premium_type(self, row: int, col: int) -> Tuple[str, Tuple[int, int, int]]:
        """Get the premium type and color for a square."""
        pos = (row, col)
        if pos in TRIPLE_WORD_SCORE:
            return "TWS", PREMIUM_TRIPLE_WORD
        elif pos in DOUBLE_WORD_SCORE:
            return "DWS", PREMIUM_DOUBLE_WORD
        elif pos in TRIPLE_LETTER_SCORE:
            return "TLS", PREMIUM_TRIPLE_LETTER
        elif pos in DOUBLE_LETTER_SCORE:
            return "DLS", PREMIUM_DOUBLE_LETTER
        return "", BOARD_COLOR

    def draw_square(self, screen: pygame.Surface, row: int, col: int, override_color: Optional[Tuple[int, int, int]] = None):
        """Draw a single board square with premium indicators."""
        x, y = self.get_square_position(row, col)
        
        # Determine square color
        if override_color:
            color = override_color
        else:
            premium_text, color = self.get_premium_type(row, col)
        
        # Draw square background
        pygame.draw.rect(screen, color, (x, y, self.tile_size, self.tile_size))
        pygame.draw.rect(screen, BLACK, (x, y, self.tile_size, self.tile_size), 1)

        # Draw premium text if no override color
        if not override_color and premium_text:
            text = self.small_font.render(premium_text, True, BLACK)
            text_rect = text.get_rect(center=(x + self.tile_size // 2, y + self.tile_size // 2))
            screen.blit(text, text_rect)

class Rack:
    def __init__(self, window_size: int, tile_size: int, font: pygame.font.Font):
        self.window_size = window_size
        self.tile_size = tile_size
        self.font = font
        self.y = window_size + 10

    def get_rack_position(self, tiles_count: int) -> int:
        """Get the x coordinate where the rack should start."""
        return (self.window_size - (tiles_count * self.tile_size)) // 2

    def get_tile_index(self, mouse_pos: Tuple[int, int], tiles_count: int) -> Optional[int]:
        """Get the index of a tile in the rack based on mouse position."""
        x, y = mouse_pos
        rack_x = self.get_rack_position(tiles_count)
        
        if self.y <= y <= self.y + self.tile_size:
            idx = (x - rack_x) // self.tile_size
            if 0 <= idx < tiles_count:
                return idx
        return None 