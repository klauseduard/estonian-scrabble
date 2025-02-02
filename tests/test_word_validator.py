import unittest
from typing import List, Optional
from game.word_validator import WordValidator
from wordlist import WordList

class MockWordList:
    """A simple mock wordlist for testing."""
    def __init__(self, words):
        self.words = set(words)
        
    def is_valid_word(self, word: str) -> bool:
        return word.lower() in self.words

class TestWordValidator(unittest.TestCase):
    def setUp(self):
        # Create a mock wordlist for testing
        test_words = {"ema", "maa", "kes", "sees", "ses", "emas", "ems"}
        self.wordlist = MockWordList(test_words)
        self.validator = WordValidator(self.wordlist)
        
    def create_empty_board(self) -> List[List[Optional[str]]]:
        return [[None for _ in range(15)] for _ in range(15)]
        
    def test_disconnected_tile_placement(self):
        """Test that disconnected tile placements are marked as invalid."""
        board = self.create_empty_board()
        
        # Place "EMA" in the center
        center = 7
        board[center][center] = 'E'
        board[center][center + 1] = 'M'
        board[center][center + 2] = 'A'
        
        # Try placing disconnected tiles: 'K' away from "EMA" and 'ES' connected to "EMA"
        current_turn_tiles = {(5, 5), (7, 9), (7, 10)}  # K at (5,5), ES at (7,9-10)
        board[5][5] = 'K'
        board[7][9] = 'E'
        board[7][10] = 'S'
        
        # Validate the placement
        validity = self.validator.validate_placement(board, current_turn_tiles)
        
        # All positions should be marked as invalid due to disconnected placement
        self.assertFalse(validity[(5, 5)])  # K should be invalid
        self.assertFalse(validity[(7, 9)])  # E should be invalid
        self.assertFalse(validity[(7, 10)])  # S should be invalid
        
        # The overall placement should be invalid
        self.assertFalse(self.validator.is_placement_valid())
        
    def test_continuous_line_validation(self):
        """Test that tiles must form a continuous line."""
        board = self.create_empty_board()
        
        # Place "EMA" in the center
        center = 7
        board[center][center] = 'E'
        board[center][center + 1] = 'M'
        board[center][center + 2] = 'A'
        
        # Test cases for current turn tile placements
        test_cases = [
            # Valid horizontal line forming "EMAS"
            ({(7, 3)}, True, [('S', (7, 3))]),  # Forms "EMAS" with existing "EMA"
            # Valid vertical line
            ({(8, 7)}, True, [('S', (8, 7))]),  # Forms "EMS" vertically
            # Invalid diagonal
            ({(8, 8), (9, 9)}, False, [('S', (8, 8)), ('S', (9, 9))]),
            # Invalid scattered
            ({(8, 7), (8, 9)}, False, [('S', (8, 7)), ('S', (8, 9))]),
            # Empty set is valid
            (set(), True, []),
        ]
        
        for tiles, expected_valid, letters in test_cases:
            # Place the tiles on board
            for (row, col), (letter, _) in zip(tiles, letters):
                board[row][col] = letter
                
            # Validate the placement
            validity = self.validator.validate_placement(board, tiles)
            
            # For valid placements, check if they're connected and form valid words
            if expected_valid:
                self.assertTrue(self.validator._are_turn_tiles_connected(tiles),
                              f"Tiles {tiles} should form a continuous line")
                self.assertTrue(all(validity.get((r, c), False) for r, c in tiles),
                              f"All tiles in {tiles} should be valid")
            else:
                self.assertFalse(all(validity.get((r, c), False) for r, c in tiles),
                               f"Tiles {tiles} should be invalid")
            
            # Clean up the board for next test
            for row, col in tiles:
                board[row][col] = None

if __name__ == '__main__':
    unittest.main() 