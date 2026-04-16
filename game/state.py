import random
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
        """Calculate score for a single letter considering premium squares.

        Only applies letter premium multipliers to tiles placed this turn.
        Tiles already on the board use their base point value.
        """
        base_score = LETTER_DISTRIBUTION[letter.lower()]['points']
        pos = (row, col)

        # Only apply letter premium squares for newly placed tiles
        if pos in self.current_turn_tiles:
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

        # Calculate score for all unique words formed this turn.
        # Deduplicate by positions tuple so the same word is not scored
        # multiple times when several turn tiles belong to it.
        unique_words = {}
        for row, col in self.current_turn_tiles:
            words = self.word_validator.get_word_at_position(self.board, row, col)
            for word_info in words:
                _, positions = word_info
                key = tuple(positions)
                if key not in unique_words:
                    unique_words[key] = word_info

        turn_score = 0
        for word_info in unique_words.values():
            turn_score += self._calculate_word_score(word_info)

        # 50-point bingo bonus for using all 7 tiles in one turn
        if len(self.current_turn_tiles) == 7:
            turn_score += 50

        # Update player's score
        self.current_player.score += turn_score

        # Draw new tiles
        self._draw_tiles(self.current_player, len(self.current_turn_tiles))

        # Clear current turn tiles
        self.current_turn_tiles.clear()

        # Check for game over and apply end-game adjustment
        if self.is_game_over():
            self.apply_end_game_adjustment()

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

    def apply_end_game_adjustment(self):
        """Apply end-game score adjustment for remaining tiles.

        The player who emptied their rack receives the sum of all opponents'
        remaining tile values. Each player with tiles remaining has the total
        point value of those tiles subtracted from their score. If no player
        has an empty rack, each player simply loses their remaining tile values.
        """
        # Find the player(s) with empty racks
        empty_rack_players = [p for p in self.players if len(p.rack) == 0]

        # Calculate remaining tile values for each player
        remaining_values: Dict[str, int] = {}
        total_remaining = 0
        for player in self.players:
            value = sum(
                LETTER_DISTRIBUTION[tile.lower()]["points"] for tile in player.rack
            )
            remaining_values[player.name] = value
            total_remaining += value

        # Subtract remaining tile values from each player who still has tiles
        for player in self.players:
            if len(player.rack) > 0:
                player.score -= remaining_values[player.name]

        # Add total remaining to the player who went out
        if len(empty_rack_players) == 1:
            empty_rack_players[0].score += total_remaining

    def exchange_tiles(self, tile_indices: List[int]) -> bool:
        """Exchange tiles from the current player's rack with the tile bag.

        The player forfeits their turn. Exchange is only allowed when the bag
        has at least 7 tiles and no tiles have been placed on the board this turn.

        Args:
            tile_indices: Indices into the current player's rack to exchange.

        Returns:
            True if the exchange succeeded, False otherwise.
        """
        if len(self.tile_bag) < 7:
            return False

        if self.current_turn_tiles:
            return False

        if not tile_indices:
            return False

        rack = self.current_player.rack
        # Validate all indices
        for idx in tile_indices:
            if not (0 <= idx < len(rack)):
                return False

        # Check for duplicate indices
        if len(set(tile_indices)) != len(tile_indices):
            return False

        # Remove tiles from rack in reverse order to preserve indices
        old_tiles = []
        for idx in sorted(tile_indices, reverse=True):
            old_tiles.append(rack.pop(idx))

        # Draw the same number of new tiles
        self._draw_tiles(self.current_player, len(old_tiles))

        # Return old tiles to the bag and shuffle
        self.tile_bag.extend(old_tiles)
        random.shuffle(self.tile_bag)

        # Switch to next player
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        return True

    def is_game_over(self) -> bool:
        """Check if the game is over."""
        return (len(self.tile_bag) == 0 and
                any(len(player.rack) == 0 for player in self.players))
