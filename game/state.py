from typing import List, Set, Tuple, Optional, Dict
from dataclasses import dataclass
from .word_validator import WordValidator
from .constants import (
    LETTER_DISTRIBUTION,
    TRIPLE_WORD_SCORE,
    DOUBLE_WORD_SCORE,
    TRIPLE_LETTER_SCORE,
    DOUBLE_LETTER_SCORE
)
from wordlist import WordList

@dataclass
class Player:
    name: str
    score: int = 0
    rack: List[str] = None

    def __post_init__(self):
        if self.rack is None:
            self.rack = []

    def add_tiles(self, tiles: List[str]):
        self.rack.extend(tiles)

    def remove_tiles(self, tiles: List[str]):
        for tile in tiles:
            self.rack.remove(tile)

class GameState:
    def __init__(self, board_size: int = 15):
        self.board_size = board_size
        self.board: List[List[Optional[str]]] = [[None for _ in range(board_size)] for _ in range(board_size)]
        self.players = [Player("Player 1"), Player("Player 2")]
        self.current_player_idx = 0
        self.current_turn_tiles: Set[Tuple[int, int]] = set()
        self.wordlist = WordList()
        self.word_validator = WordValidator(self.wordlist)
        self.tile_bag = self._create_tile_bag()
        self._initialize_game()

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_idx]

    def _create_tile_bag(self) -> List[str]:
        """Create and shuffle the initial tile bag."""
        tiles = []
        for letter, info in LETTER_DISTRIBUTION.items():
            tiles.extend([letter] * info['count'])
        import random
        random.shuffle(tiles)
        return tiles

    def _initialize_game(self):
        """Set up the initial game state."""
        for player in self.players:
            self._draw_tiles(player, 7)

    def _draw_tiles(self, player: Player, count: int) -> List[str]:
        """Draw tiles from the bag for a player."""
        tiles_to_draw = min(count, len(self.tile_bag))
        if tiles_to_draw == 0:
            return []
        
        new_tiles = self.tile_bag[:tiles_to_draw]
        self.tile_bag = self.tile_bag[tiles_to_draw:]
        player.add_tiles(new_tiles)
        return new_tiles

    def _get_letter_score(self, letter: str, row: int, col: int) -> int:
        """Calculate score for a single letter considering premium squares."""
        base_score = LETTER_DISTRIBUTION[letter.lower()]['points']
        pos = (row, col)
        
        if pos in TRIPLE_LETTER_SCORE:
            return base_score * 3
        elif pos in DOUBLE_LETTER_SCORE:
            return base_score * 2
        return base_score

    def _calculate_word_score(self, word_info: Tuple[str, List[Tuple[int, int]]]) -> int:
        """Calculate score for a word including premium squares."""
        word, positions = word_info
        word_multiplier = 1
        word_score = 0

        # Calculate letter scores and collect word multipliers
        for letter, (row, col) in zip(word, positions):
            word_score += self._get_letter_score(letter, row, col)
            pos = (row, col)
            
            # Only apply premium squares for newly placed tiles
            if pos in self.current_turn_tiles:
                if pos in TRIPLE_WORD_SCORE:
                    word_multiplier *= 3
                elif pos in DOUBLE_WORD_SCORE:
                    word_multiplier *= 2

        return word_score * word_multiplier

    def place_tile(self, row: int, col: int, tile_idx: int) -> bool:
        """Place a tile from the current player's rack onto the board."""
        if self.board[row][col] is not None:
            return False

        letter = self.current_player.rack[tile_idx]
        self.board[row][col] = letter
        self.current_player.rack.pop(tile_idx)
        self.current_turn_tiles.add((row, col))
        return True

    def remove_tile(self, row: int, col: int) -> bool:
        """Remove a tile from the board and return it to the current player's rack."""
        if (row, col) not in self.current_turn_tiles:
            return False

        letter = self.board[row][col]
        self.board[row][col] = None
        self.current_player.rack.append(letter)
        self.current_turn_tiles.remove((row, col))
        return True

    def validate_current_placement(self) -> dict:
        """Validate the current turn's word placements."""
        return self.word_validator.validate_placement(self.board, self.current_turn_tiles)

    def commit_turn(self) -> bool:
        """Commit the current turn if all words are valid."""
        if not self.word_validator.is_placement_valid():
            return False

        # Calculate score for all words formed this turn
        turn_score = 0
        for row, col in self.current_turn_tiles:
            words = self.word_validator.get_word_at_position(self.board, row, col)
            for word_info in words:
                turn_score += self._calculate_word_score(word_info)

        # Update player's score
        self.current_player.score += turn_score

        # Draw new tiles
        self._draw_tiles(self.current_player, len(self.current_turn_tiles))
        
        # Clear current turn tiles
        self.current_turn_tiles.clear()
        
        # Switch to next player
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        return True

    def next_player(self):
        """Skip to the next player's turn."""
        # Return any placed tiles to the rack
        for row, col in self.current_turn_tiles:
            letter = self.board[row][col]
            self.board[row][col] = None
            self.current_player.rack.append(letter)
        
        # Clear current turn tiles
        self.current_turn_tiles.clear()
        
        # Switch to next player
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)

    def is_game_over(self) -> bool:
        """Check if the game is over."""
        return (len(self.tile_bag) == 0 and 
                any(len(player.rack) == 0 for player in self.players)) 