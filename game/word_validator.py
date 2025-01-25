from typing import List, Tuple, Set, Dict, Optional
from wordlist import WordList

class WordValidator:
    def __init__(self, wordlist: WordList):
        self.wordlist = wordlist
        self.word_validity: Dict[Tuple[int, int], bool] = {}

    def get_word_at_position(self, board: List[List[Optional[str]]], row: int, col: int) -> List[Tuple[str, List[Tuple[int, int]]]]:
        """Get horizontal and vertical words at the given position."""
        words = []
        directions = [(0, 1), (1, 0)]  # Horizontal and vertical

        for dy, dx in directions:
            # Find word start
            start_row, start_col = row, col
            while start_row > 0 and start_col > 0 and board[start_row - dy][start_col - dx] is not None:
                start_row -= dy
                start_col -= dx

            # Build word
            word = ""
            curr_row, curr_col = start_row, start_col
            while (curr_row < len(board) and curr_col < len(board[0]) and 
                   board[curr_row][curr_col] is not None):
                word += board[curr_row][curr_col]
                curr_row += dy
                curr_col += dx

            if len(word) > 1:
                positions = []
                r, c = start_row, start_col
                while r < curr_row or c < curr_col:
                    positions.append((r, c))
                    r += dy
                    c += dx
                words.append((word, positions))

        return words

    def validate_placement(self, board: List[List[Optional[str]]], current_turn_tiles: Set[Tuple[int, int]]) -> Dict[Tuple[int, int], bool]:
        """Validate all words formed by the current turn's tiles."""
        self.word_validity.clear()
        
        # Check each placed tile
        for row, col in current_turn_tiles:
            words = self.get_word_at_position(board, row, col)
            
            for word, positions in words:
                is_valid = self.wordlist.is_valid_word(word)
                # Update validity for all positions in the word
                for pos in positions:
                    self.word_validity[pos] = is_valid

        return self.word_validity

    def is_placement_valid(self) -> bool:
        """Check if all words in current placement are valid."""
        return all(self.word_validity.values()) 