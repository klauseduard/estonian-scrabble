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
        test_words = {"ema", "maa", "kes", "sees", "ses", "emas", "ems", "ms"}
        self.wordlist = MockWordList(test_words)
        self.validator = WordValidator(self.wordlist)
        
    def create_empty_board(self) -> List[List[Optional[str]]]:
        return [[None for _ in range(15)] for _ in range(15)]
        
    def test_disconnected_tile_placement(self):
        """Test that disconnected tile placements are marked as invalid."""
        board = [[None] * 15 for _ in range(15)]
        tiles = {(7, 7), (10, 10)}  # Disconnected tiles
        self.assertFalse(self.validator._are_turn_tiles_connected(board, tiles))
        
    def test_continuous_line_validation(self):
        """Test that tiles must form a continuous line."""
        board = [[None] * 15 for _ in range(15)]
        
        # Test horizontal placement
        tiles = {(7, 7), (7, 8), (7, 9)}  # Continuous line
        self.assertTrue(self.validator._are_turn_tiles_connected(board, tiles))
        
        tiles = {(7, 7), (7, 9)}  # Gap in line
        self.assertFalse(self.validator._are_turn_tiles_connected(board, tiles))
        
        # Test vertical placement
        tiles = {(7, 7), (8, 7), (9, 7)}  # Continuous line
        self.assertTrue(self.validator._are_turn_tiles_connected(board, tiles))
        
        tiles = {(7, 7), (9, 7)}  # Gap in line
        self.assertFalse(self.validator._are_turn_tiles_connected(board, tiles))

    def test_tiles_must_be_adjacent(self):
        """Test that tiles must be adjacent to each other in a continuous line."""
        board = [[None] * 15 for _ in range(15)]
        
        # Test with gaps
        tiles = {(7, 7), (7, 9)}  # Horizontal gap
        self.assertFalse(self.validator._are_turn_tiles_connected(board, tiles))
        
        tiles = {(7, 7), (9, 7)}  # Vertical gap
        self.assertFalse(self.validator._are_turn_tiles_connected(board, tiles))

    def test_placement_through_existing_tiles(self):
        """Test that placement through existing tiles is valid."""
        board = [[None] * 15 for _ in range(15)]
        # Place an existing tile
        board[8][7] = 'U'
        
        # Test vertical placement through existing tile
        tiles = {(7, 7), (9, 7)}  # K and S around existing U
        self.assertTrue(self.validator._are_turn_tiles_connected(board, tiles))
        
        # Test horizontal placement through existing tile
        board = [[None] * 15 for _ in range(15)]
        board[7][8] = 'U'
        tiles = {(7, 7), (7, 9)}  # K and S around existing U
        self.assertTrue(self.validator._are_turn_tiles_connected(board, tiles))

if __name__ == '__main__':
    unittest.main() 