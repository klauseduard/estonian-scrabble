from typing import List, Dict, Optional
import random

# Estonian Scrabble letter distribution and points
LETTER_DISTRIBUTION = {
    'a': {'count': 10, 'points': 1},
    'e': {'count': 9, 'points': 1},
    'i': {'count': 8, 'points': 1},
    's': {'count': 8, 'points': 1},
    't': {'count': 7, 'points': 1},
    'l': {'count': 6, 'points': 1},
    'n': {'count': 6, 'points': 1},
    'o': {'count': 5, 'points': 1},
    'u': {'count': 5, 'points': 1},
    'd': {'count': 4, 'points': 2},
    'k': {'count': 4, 'points': 2},
    'm': {'count': 4, 'points': 2},
    'r': {'count': 4, 'points': 2},
    'v': {'count': 3, 'points': 3},
    'õ': {'count': 2, 'points': 3},
    'ä': {'count': 2, 'points': 3},
    'ö': {'count': 2, 'points': 3},
    'ü': {'count': 2, 'points': 3},
    'b': {'count': 1, 'points': 4},
    'f': {'count': 1, 'points': 4},
    'g': {'count': 1, 'points': 4},
    'h': {'count': 2, 'points': 3},
    'j': {'count': 1, 'points': 4},
    'p': {'count': 2, 'points': 3},
    'š': {'count': 1, 'points': 4},
    'z': {'count': 1, 'points': 4},
    'ž': {'count': 1, 'points': 4},
}

class Player:
    def __init__(self, name: str):
        self.name = name
        self.score = 0
        self.rack: List[str] = []

    def add_tiles(self, tiles: List[str]):
        self.rack.extend(tiles)

    def remove_tiles(self, tiles: List[str]):
        for tile in tiles:
            self.rack.remove(tile)

class ScrabbleGame:
    def __init__(self):
        self.board = [[None for _ in range(15)] for _ in range(15)]
        self.players = [Player("Player 1"), Player("Player 2")]
        self.current_player_idx = 0
        self.tile_bag = self._create_tile_bag()
        self._initialize_game()

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_idx]

    def _create_tile_bag(self) -> List[str]:
        tiles = []
        for letter, info in LETTER_DISTRIBUTION.items():
            tiles.extend([letter] * info['count'])
        random.shuffle(tiles)
        return tiles

    def _initialize_game(self):
        # Deal initial tiles to players
        for player in self.players:
            self._draw_tiles(player, 7)

    def _draw_tiles(self, player: Player, count: int) -> List[str]:
        tiles_to_draw = min(count, len(self.tile_bag))
        if tiles_to_draw == 0:
            return []
        
        new_tiles = self.tile_bag[:tiles_to_draw]
        self.tile_bag = self.tile_bag[tiles_to_draw:]
        player.add_tiles(new_tiles)
        return new_tiles

    def place_word(self, word: str, row: int, col: int, direction: str) -> bool:
        # Validate word placement and update board
        # This is a placeholder - needs to be implemented with full game rules
        pass

    def calculate_word_score(self, word: str, row: int, col: int, direction: str) -> int:
        # Calculate score for a word placement
        # This is a placeholder - needs to be implemented with premium squares
        score = 0
        for letter in word:
            score += LETTER_DISTRIBUTION[letter.lower()]['points']
        return score

    def next_turn(self):
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)

    def is_game_over(self) -> bool:
        # Game is over if tile bag is empty and any player has no tiles
        return (len(self.tile_bag) == 0 and 
                any(len(player.rack) == 0 for player in self.players)) 