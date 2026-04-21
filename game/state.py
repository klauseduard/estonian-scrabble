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
    def __init__(self, board_size: int = 15, num_players: int = 2):
        if not 2 <= num_players <= 4:
            raise ValueError("num_players must be between 2 and 4")
        self.board_size = board_size
        self.board: List[List[Optional[str]]] = [[None for _ in range(board_size)] for _ in range(board_size)]
        self.players = [Player(f"Player {i + 1}") for i in range(num_players)]
        self.current_player_idx = 0
        self.current_turn_tiles: Set[Tuple[int, int]] = set()
        self.blank_designations: Dict[Tuple[int, int], str] = {}
        self.consecutive_passes = 0
        self.game_over = False
        self.first_move = True
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
        Blank tiles always score 0 points regardless of premium squares.
        """
        pos = (row, col)

        # Blank tiles always score 0, even on premium squares
        if pos in self.blank_designations:
            return 0

        base_score = LETTER_DISTRIBUTION[letter.lower()]['points']

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

    def place_tile(
        self, row: int, col: int, tile_idx: int, designated_letter: Optional[str] = None
    ) -> bool:
        """Place a tile from the current player's rack onto the board.

        For blank tiles, *designated_letter* must be provided so the board
        stores the chosen letter (for word validation) and the position is
        recorded in ``blank_designations`` (for scoring at 0 points).
        """
        if self.board[row][col] is not None:
            return False

        letter = self.current_player.rack[tile_idx]

        if letter == "_":
            if designated_letter is None:
                return False
            self.board[row][col] = designated_letter.lower()
            self.blank_designations[(row, col)] = designated_letter.lower()
        else:
            self.board[row][col] = letter

        self.current_player.rack.pop(tile_idx)
        self.current_turn_tiles.add((row, col))
        return True

    def remove_tile(self, row: int, col: int) -> bool:
        """Remove a tile from the board and return it to the current player's rack.

        If the tile is a blank, the original ``'_'`` token is returned to the
        rack and the designation is cleaned up.
        """
        if (row, col) not in self.current_turn_tiles:
            return False

        if (row, col) in self.blank_designations:
            # Return blank as '_' to the rack
            self.current_player.rack.append("_")
            del self.blank_designations[(row, col)]
        else:
            letter = self.board[row][col]
            self.current_player.rack.append(letter)

        self.board[row][col] = None
        self.current_turn_tiles.remove((row, col))
        return True

    def validate_current_placement(self) -> dict:
        """Validate the current turn's word placements."""
        return self.word_validator.validate_placement(self.board, self.current_turn_tiles, self.first_move)

    def calculate_turn_score(self) -> List[Tuple[str, int]]:
        """Calculate score breakdown for current placement without committing.

        Returns a list of (word, score) pairs, plus a bingo bonus entry if
        applicable. Returns an empty list if placement is invalid.
        """
        if not self.word_validator.is_placement_valid():
            return []

        unique_words = {}
        for row, col in self.current_turn_tiles:
            words = self.word_validator.get_word_at_position(self.board, row, col)
            for word_info in words:
                _, positions = word_info
                key = tuple(positions)
                if key not in unique_words:
                    unique_words[key] = word_info

        breakdown = []
        for word_info in unique_words.values():
            word, _ = word_info
            score = self._calculate_word_score(word_info)
            breakdown.append((word.upper(), score))

        if len(self.current_turn_tiles) == 7:
            breakdown.append(("BINGO", 50))

        return breakdown

    def force_calculate_turn_score(self) -> List[Tuple[str, int]]:
        """Calculate score breakdown ignoring word validity.

        Same as ``calculate_turn_score`` but skips the validity check.
        Used for forced commits when players agree to override the dictionary.
        Returns an empty list only if placement rules are structurally broken
        (no tiles placed, not connected, etc.).
        """
        validation = self.word_validator.validate_placement(
            self.board, self.current_turn_tiles, self.first_move
        )
        # Check structural rules but not word validity
        if not validation.get("center_square", True) and self.first_move:
            return []
        if not validation.get("connected", True) and not self.first_move:
            return []
        if not validation.get("continuous_line", True):
            return []
        if not self.current_turn_tiles:
            return []

        unique_words = {}
        for row, col in self.current_turn_tiles:
            words = self.word_validator.get_word_at_position(self.board, row, col)
            for word_info in words:
                _, positions = word_info
                key = tuple(positions)
                if key not in unique_words:
                    unique_words[key] = word_info

        breakdown = []
        for word_info in unique_words.values():
            word, _ = word_info
            score = self._calculate_word_score(word_info)
            breakdown.append((word.upper(), score))

        if len(self.current_turn_tiles) == 7:
            breakdown.append(("BINGO", 50))

        return breakdown

    def commit_turn(self, force: bool = False) -> bool:
        """Commit the current turn.

        Args:
            force: If True, bypass word validity checks (players agreed
                   to override the dictionary). Structural placement rules
                   (connectivity, center square) are still enforced.
        """
        if force:
            breakdown = self.force_calculate_turn_score()
        else:
            breakdown = self.calculate_turn_score()
        if not breakdown and self.current_turn_tiles:
            return False
        if not self.current_turn_tiles:
            return False

        turn_score = sum(score for _, score in breakdown)

        # Update player's score
        self.current_player.score += turn_score

        # Draw new tiles
        self._draw_tiles(self.current_player, len(self.current_turn_tiles))

        # Clear current turn tiles (blank designations persist on the board)
        self.current_turn_tiles.clear()

        # A successful placement resets the consecutive pass counter
        self.consecutive_passes = 0
        self.first_move = False

        # Check for game over and apply end-game adjustment
        if self.is_game_over():
            self.game_over = True
            self.apply_end_game_adjustment()

        # Switch to next player
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        return True

    def next_player(self):
        """Skip to the next player's turn (pass)."""
        # Return any placed tiles to the rack
        for row, col in self.current_turn_tiles:
            if (row, col) in self.blank_designations:
                self.current_player.rack.append("_")
                del self.blank_designations[(row, col)]
            else:
                letter = self.board[row][col]
                self.current_player.rack.append(letter)
            self.board[row][col] = None

        # Clear current turn tiles
        self.current_turn_tiles.clear()

        # Track consecutive passes — game ends if all players pass in a row
        self.consecutive_passes += 1
        if self.consecutive_passes >= len(self.players):
            self.game_over = True
            self.apply_end_game_adjustment()

        # Switch to next player
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)

    def apply_end_game_adjustment(self):
        """Apply end-game score adjustment for remaining tiles.

        The player who emptied their rack receives the sum of all opponents'
        remaining tile values. Each player with tiles remaining has the total
        point value of those tiles subtracted from their score. If no player
        has an empty rack, each player simply loses their remaining tile values.

        Safe to call only once — guarded by ``_end_game_applied``.
        """
        if getattr(self, "_end_game_applied", False):
            return
        self._end_game_applied = True

        # Store pre-adjustment scores for the game-over breakdown
        self.end_game_details: List[Dict] = []

        # Find the player(s) with empty racks
        empty_rack_players = [p for p in self.players if len(p.rack) == 0]

        # Calculate remaining tile values for each player
        remaining_values: Dict[str, int] = {}
        total_remaining = 0
        for player in self.players:
            value = sum(
                LETTER_DISTRIBUTION[tile.lower()]["points"]
                for tile in player.rack
            )
            remaining_values[player.name] = value
            total_remaining += value

        for player in self.players:
            detail = {
                "name": player.name,
                "word_score": player.score,
                "tile_deduction": 0,
                "tile_bonus": 0,
            }
            if len(player.rack) > 0:
                detail["tile_deduction"] = -remaining_values[player.name]
                player.score -= remaining_values[player.name]
            if len(empty_rack_players) == 1 and player in empty_rack_players:
                detail["tile_bonus"] = total_remaining
                player.score += total_remaining
            detail["final_score"] = player.score
            self.end_game_details.append(detail)

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
