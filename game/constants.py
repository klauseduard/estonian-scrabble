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

# Board premium squares
TRIPLE_WORD_SCORE = [
    (0, 0), (0, 7), (0, 14),
    (7, 0), (7, 14),
    (14, 0), (14, 7), (14, 14)
]

DOUBLE_WORD_SCORE = [
    (1, 1), (1, 13),
    (2, 2), (2, 12),
    (3, 3), (3, 11),
    (4, 4), (4, 10),
    (10, 4), (10, 10),
    (11, 3), (11, 11),
    (12, 2), (12, 12),
    (13, 1), (13, 13)
]

TRIPLE_LETTER_SCORE = [
    (1, 5), (1, 9),
    (5, 1), (5, 5), (5, 9), (5, 13),
    (9, 1), (9, 5), (9, 9), (9, 13),
    (13, 5), (13, 9)
]

DOUBLE_LETTER_SCORE = [
    (0, 3), (0, 11),
    (2, 6), (2, 8),
    (3, 0), (3, 7), (3, 14),
    (6, 2), (6, 6), (6, 8), (6, 12),
    (7, 3), (7, 11),
    (8, 2), (8, 6), (8, 8), (8, 12),
    (11, 0), (11, 7), (11, 14),
    (12, 6), (12, 8),
    (14, 3), (14, 11)
] 