# Estonian Scrabble letter distribution and points
LETTER_DISTRIBUTION = {
    # High-frequency vowels
    'a': {'count': 10, 'points': 1},
    'e': {'count': 9, 'points': 1},
    'i': {'count': 9, 'points': 1},
    'o': {'count': 5, 'points': 1},
    'u': {'count': 5, 'points': 1},

    # High-frequency consonants
    's': {'count': 8, 'points': 1},
    't': {'count': 7, 'points': 1},
    'k': {'count': 5, 'points': 1},
    'l': {'count': 5, 'points': 1},
    'd': {'count': 4, 'points': 2},
    'm': {'count': 4, 'points': 2},
    'n': {'count': 4, 'points': 2},
    'r': {'count': 2, 'points': 2},

    # Medium-frequency consonants
    'g': {'count': 2, 'points': 3},
    'v': {'count': 2, 'points': 3},

    # Low-frequency consonants
    'b': {'count': 1, 'points': 4},
    'h': {'count': 2, 'points': 4},
    'j': {'count': 2, 'points': 4},
    'p': {'count': 2, 'points': 4},

    # Estonian special characters (vowels)
    'õ': {'count': 2, 'points': 4},
    'ä': {'count': 2, 'points': 5},
    'ü': {'count': 2, 'points': 5},
    'ö': {'count': 2, 'points': 6},

    # Rare letters
    'f': {'count': 1, 'points': 8},
    'š': {'count': 1, 'points': 10},
    'z': {'count': 1, 'points': 10},
    'ž': {'count': 1, 'points': 10},

    # Blank tiles (can represent any letter, worth 0 points)
    '_': {'count': 2, 'points': 0},
}

# Board premium squares (sets for O(1) lookup)
TRIPLE_WORD_SCORE = {
    (0, 0), (0, 7), (0, 14),
    (7, 0), (7, 14),
    (14, 0), (14, 7), (14, 14),
}

DOUBLE_WORD_SCORE = {
    (1, 1), (1, 13),
    (2, 2), (2, 12),
    (3, 3), (3, 11),
    (4, 4), (4, 10),
    (10, 4), (10, 10),
    (11, 3), (11, 11),
    (12, 2), (12, 12),
    (13, 1), (13, 13),
    (7, 7),
}

TRIPLE_LETTER_SCORE = {
    (1, 5), (1, 9),
    (5, 1), (5, 5), (5, 9), (5, 13),
    (9, 1), (9, 5), (9, 9), (9, 13),
    (13, 5), (13, 9),
}

DOUBLE_LETTER_SCORE = {
    (0, 3), (0, 11),
    (2, 6), (2, 8),
    (3, 0), (3, 7), (3, 14),
    (6, 2), (6, 6), (6, 8), (6, 12),
    (7, 3), (7, 11),
    (8, 2), (8, 6), (8, 8), (8, 12),
    (11, 0), (11, 7), (11, 14),
    (12, 6), (12, 8),
    (14, 3), (14, 11),
}