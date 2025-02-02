from typing import List, Tuple, Set, Dict, Optional
from wordlist import WordList
import logging

class WordValidator:
    def __init__(self, wordlist: WordList):
        self.wordlist = wordlist
        self.word_validity: Dict[Tuple[int, int], bool] = {}
        self.logger = logging.getLogger(__name__)

    def get_word_at_position(self, board: List[List[Optional[str]]], row: int, col: int) -> List[Tuple[str, List[Tuple[int, int]]]]:
        """Get horizontal and vertical words at the given position."""
        words = []
        directions = [(0, 1), (1, 0)]  # Horizontal and vertical

        for dy, dx in directions:
            # Find word start
            start_row, start_col = row, col
            while (start_row - dy >= 0 and start_col - dx >= 0 and 
                   board[start_row - dy][start_col - dx] is not None):
                start_row -= dy
                start_col -= dx

            # Build word
            word = ""
            positions = []
            curr_row, curr_col = start_row, start_col
            while (curr_row < len(board) and curr_col < len(board[0]) and 
                   board[curr_row][curr_col] is not None):
                word += board[curr_row][curr_col]
                positions.append((curr_row, curr_col))
                curr_row += dy
                curr_col += dx

            if len(word) > 1:
                self.logger.info(f"Found word: '{word}' at positions {positions}")
                words.append((word, positions))

        return words

    def _is_connected_to_existing(self, board: List[List[Optional[str]]], current_turn_tiles: Set[Tuple[int, int]]) -> bool:
        """Check if new tiles are connected to existing tiles on the board."""
        # If this is the first move (board is empty), tiles must be placed through center
        center = len(board) // 2
        is_first_move = all(board[i][j] is None or (i, j) in current_turn_tiles 
                           for i in range(len(board)) for j in range(len(board[0])))
        
        if is_first_move:
            # For first move, check if any tile is on center
            return (center, center) in current_turn_tiles
        
        # For subsequent moves, check if any new tile is adjacent to an existing tile
        for row, col in current_turn_tiles:
            # Check all adjacent positions
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                new_row, new_col = row + dr, col + dc
                if (0 <= new_row < len(board) and 
                    0 <= new_col < len(board[0]) and 
                    board[new_row][new_col] is not None and 
                    (new_row, new_col) not in current_turn_tiles):
                    return True
        return False

    def _are_turn_tiles_connected(self, board: List[List[Optional[str]]], current_turn_tiles: Set[Tuple[int, int]]) -> bool:
        """Check if all tiles placed in current turn form a continuous line."""
        if not current_turn_tiles:
            return True
        if len(current_turn_tiles) == 1:
            return True
            
        # Find if tiles form a line (horizontal or vertical)
        tiles = list(current_turn_tiles)
        rows = [r for r, _ in tiles]
        cols = [c for _, c in tiles]
        
        # Check if tiles are in same row
        if len(set(rows)) == 1:
            # All tiles in same row - check if continuous
            cols = sorted(cols)
            # Check each position between min and max col has either a current turn tile or existing tile
            return all((rows[0], col) in current_turn_tiles or 
                      (board[rows[0]][col] is not None and (rows[0], col) not in current_turn_tiles)
                      for col in range(cols[0], cols[-1] + 1))
            
        # Check if tiles are in same column
        if len(set(cols)) == 1:
            # All tiles in same column - check if continuous
            rows = sorted(rows)
            # Check each position between min and max row has either a current turn tile or existing tile
            return all((row, cols[0]) in current_turn_tiles or
                      (board[row][cols[0]] is not None and (row, cols[0]) not in current_turn_tiles)
                      for row in range(rows[0], rows[-1] + 1))
            
        # Tiles neither in same row nor column
        return False

    def validate_placement(self, board: List[List[Optional[str]]], current_turn_tiles: Set[Tuple[int, int]]) -> Dict[Tuple[int, int], bool]:
        """Validate all words formed by the current turn's tiles."""
        self.word_validity.clear()
        
        # First check if tiles are connected to existing tiles
        if not self._is_connected_to_existing(board, current_turn_tiles):
            self.logger.warning("Tiles are not connected to existing tiles")
            # Mark all tiles as invalid
            for pos in current_turn_tiles:
                self.word_validity[pos] = False
            return self.word_validity

        # Check if current turn tiles form a continuous line
        if not self._are_turn_tiles_connected(board, current_turn_tiles):
            self.logger.warning("Tiles placed this turn do not form a continuous line")
            # Mark all tiles as invalid
            for pos in current_turn_tiles:
                self.word_validity[pos] = False
            return self.word_validity
        
        # Check each placed tile
        all_words = set()  # Keep track of all words to avoid duplicates
        for row, col in current_turn_tiles:
            words = self.get_word_at_position(board, row, col)
            
            for word, positions in words:
                if word not in all_words:
                    all_words.add(word)
                    is_valid = self.wordlist.is_valid_word(word)
                    self.logger.info(f"Validating word '{word}': {'valid' if is_valid else 'invalid'}")
                    # Update validity for all positions in the word
                    for pos in positions:
                        self.word_validity[pos] = is_valid

        # If no words were formed (single letter), mark as invalid
        if not all_words:
            self.logger.warning("No valid words formed")
            for pos in current_turn_tiles:
                self.word_validity[pos] = False

        return self.word_validity

    def is_placement_valid(self) -> bool:
        """Check if all words in current placement are valid."""
        return all(self.word_validity.values()) 