"""AI player for Estonian Scrabble.

Generates valid moves by scanning the board for anchor points, trying
rack tile combinations, and scoring candidates.  The module is pure
game-logic — no UI or server dependencies — so it works with both the
Pygame desktop client and the FastAPI web server.

Difficulty levels control move selection:
  - easy:   random valid move
  - medium: highest-scoring move (greedy)
  - hard:   highest score + rack-balance and positional heuristics
"""

import itertools
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .constants import (
    DOUBLE_LETTER_SCORE,
    DOUBLE_WORD_SCORE,
    LETTER_DISTRIBUTION,
    TRIPLE_LETTER_SCORE,
    TRIPLE_WORD_SCORE,
)


@dataclass
class Move:
    """A candidate move the AI might play."""

    tiles: List[Tuple[int, int, str]]  # (row, col, letter) placements
    words_formed: List[str]
    raw_score: int = 0
    heuristic_score: float = 0.0

    @property
    def positions(self) -> Set[Tuple[int, int]]:
        return {(r, c) for r, c, _ in self.tiles}


# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

def _get_anchors(board: List[List[Optional[str]]], first_move: bool) -> Set[Tuple[int, int]]:
    """Return empty cells adjacent to existing tiles (or center on first move)."""
    size = len(board)
    if first_move:
        center = size // 2
        return {(center, center)}

    anchors: Set[Tuple[int, int]] = set()
    for r in range(size):
        for c in range(size):
            if board[r][c] is not None:
                continue
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < size and 0 <= nc < size and board[nr][nc] is not None:
                    anchors.add((r, c))
                    break
    return anchors


def _read_word(board, row, col, dr, dc):
    """Read the contiguous word through (row, col) in direction (dr, dc).

    Returns (word_str, [(r,c), ...]) or None if single letter.
    """
    size = len(board)
    # Find start of the word
    sr, sc = row, col
    while sr - dr >= 0 and sc - dc >= 0 and sr - dr < size and sc - dc < size:
        if board[sr - dr][sc - dc] is None:
            break
        sr -= dr
        sc -= dc

    word = ""
    positions = []
    cr, cc = sr, sc
    while 0 <= cr < size and 0 <= cc < size and board[cr][cc] is not None:
        word += board[cr][cc]
        positions.append((cr, cc))
        cr += dr
        cc += dc

    if len(word) > 1:
        return word, positions
    return None


def _cross_word(board, row, col, direction):
    """Get the cross-word formed at (row, col) perpendicular to *direction*.

    direction: (dr, dc) of the main word.
    Returns the cross-word string or None if no cross-word.
    """
    # Perpendicular direction
    if direction == (0, 1):  # horizontal main → check vertical cross
        cdr, cdc = 1, 0
    else:  # vertical main → check horizontal cross
        cdr, cdc = 0, 1

    return _read_word(board, row, col, cdr, cdc)


# ---------------------------------------------------------------------------
# Move generation
# ---------------------------------------------------------------------------

def _generate_line_moves(
    board: List[List[Optional[str]]],
    rack: List[str],
    anchor_row: int,
    anchor_col: int,
    dr: int,
    dc: int,
    wordlist,
    validation_cache: Dict[str, bool],
    first_move: bool,
) -> List[Move]:
    """Generate valid moves through *anchor* in direction (dr, dc)."""
    size = len(board)
    moves: List[Move] = []

    # Determine how far we can extend before and after the anchor
    # "Before" = opposite of (dr, dc)
    max_before = 0
    r, c = anchor_row - dr, anchor_col - dc
    while 0 <= r < size and 0 <= c < size and board[r][c] is None:
        max_before += 1
        r -= dr
        c -= dc
    # Cap at rack size
    max_before = min(max_before, len(rack))

    # Try different starting offsets (how many cells before the anchor)
    for before in range(max_before + 1):
        start_r = anchor_row - before * dr
        start_c = anchor_col - before * dc

        # Try placing 1..len(rack) tiles
        usable = list(range(len(rack)))
        for length in range(1, len(rack) + 1):
            if length > 7:
                break
            for combo in itertools.combinations(usable, length):
                for perm in itertools.permutations(combo):
                    tiles_placed = []
                    temp_board = [row[:] for row in board]
                    valid = True
                    pr, pc = start_r, start_c
                    tile_idx = 0

                    # Walk along the line, placing tiles in empty cells
                    tiles_used = 0
                    while tiles_used < len(perm) and 0 <= pr < size and 0 <= pc < size:
                        if temp_board[pr][pc] is None:
                            letter = rack[perm[tile_idx]]
                            if letter == "_":
                                # Skip blanks for now (simplification)
                                valid = False
                                break
                            temp_board[pr][pc] = letter
                            tiles_placed.append((pr, pc, letter))
                            tile_idx += 1
                            tiles_used += 1
                        # else: existing tile, skip over it
                        pr += dr
                        pc += dc

                    if not valid or not tiles_placed:
                        continue

                    # Must include the anchor
                    placed_positions = {(r, c) for r, c, _ in tiles_placed}
                    if (anchor_row, anchor_col) not in placed_positions:
                        # Check if anchor is covered by an existing tile in the line
                        if board[anchor_row][anchor_col] is not None:
                            pass  # anchor is an existing tile we're extending from
                        else:
                            continue

                    # First move must cover center
                    if first_move:
                        center = size // 2
                        main_word_info = _read_word(temp_board, tiles_placed[0][0], tiles_placed[0][1], dr, dc)
                        if main_word_info:
                            word_positions = main_word_info[1]
                            if (center, center) not in [(r, c) for r, c in word_positions]:
                                continue

                    # Check the main word formed
                    main_word_info = _read_word(
                        temp_board, tiles_placed[0][0], tiles_placed[0][1], dr, dc
                    )
                    if main_word_info is None:
                        continue

                    main_word, main_positions = main_word_info
                    words_formed = []

                    # Validate main word
                    if main_word not in validation_cache:
                        validation_cache[main_word] = wordlist.is_valid_word(main_word)
                    if not validation_cache[main_word]:
                        continue
                    words_formed.append(main_word)

                    # Validate all cross-words
                    cross_valid = True
                    for tr, tc, _ in tiles_placed:
                        cw = _cross_word(temp_board, tr, tc, (dr, dc))
                        if cw is not None:
                            cw_str = cw[0]
                            if cw_str not in validation_cache:
                                validation_cache[cw_str] = wordlist.is_valid_word(cw_str)
                            if not validation_cache[cw_str]:
                                cross_valid = False
                                break
                            words_formed.append(cw_str)

                    if not cross_valid:
                        continue

                    # Valid move found!
                    moves.append(Move(
                        tiles=tiles_placed,
                        words_formed=words_formed,
                    ))

                    # Limit permutations per combination for performance
                    if len(perm) > 4:
                        break  # only try one permutation for long words

            # Limit combinations for long words
            if length > 4:
                break

    return moves


def find_all_moves(
    board: List[List[Optional[str]]],
    rack: List[str],
    wordlist,
    first_move: bool = False,
) -> List[Move]:
    """Find all valid moves for the given rack on the current board.

    This is the CPU-intensive function that should be run via
    ``asyncio.run_in_executor`` on the server.
    """
    anchors = _get_anchors(board, first_move)
    validation_cache: Dict[str, bool] = {}
    all_moves: List[Move] = []
    seen_placements: Set[frozenset] = set()

    for anchor_r, anchor_c in anchors:
        for dr, dc in [(0, 1), (1, 0)]:  # horizontal, vertical
            moves = _generate_line_moves(
                board, rack, anchor_r, anchor_c, dr, dc,
                wordlist, validation_cache, first_move,
            )
            for move in moves:
                key = frozenset((r, c, l) for r, c, l in move.tiles)
                if key not in seen_placements:
                    seen_placements.add(key)
                    all_moves.append(move)

    return all_moves


# ---------------------------------------------------------------------------
# Scoring with heuristics
# ---------------------------------------------------------------------------

def _calculate_move_score(
    board: List[List[Optional[str]]],
    move: Move,
) -> int:
    """Calculate the raw score for a move (premium squares included)."""
    total = 0
    placed_set = move.positions

    # Temporarily place tiles
    temp_board = [row[:] for row in board]
    for r, c, letter in move.tiles:
        temp_board[r][c] = letter

    # Score each word formed
    for r, c, _ in move.tiles:
        # Check horizontal word
        hw = _read_word(temp_board, r, c, 0, 1)
        if hw:
            word_str, positions = hw
            word_score = 0
            word_mult = 1
            for letter, (wr, wc) in zip(word_str, positions):
                base = LETTER_DISTRIBUTION.get(letter.lower(), {}).get("points", 0)
                if (wr, wc) in placed_set:
                    if (wr, wc) in TRIPLE_LETTER_SCORE:
                        base *= 3
                    elif (wr, wc) in DOUBLE_LETTER_SCORE:
                        base *= 2
                    if (wr, wc) in TRIPLE_WORD_SCORE:
                        word_mult *= 3
                    elif (wr, wc) in DOUBLE_WORD_SCORE:
                        word_mult *= 2
                word_score += base
            total += word_score * word_mult

        # Check vertical word
        vw = _read_word(temp_board, r, c, 1, 0)
        if vw:
            word_str, positions = vw
            word_score = 0
            word_mult = 1
            for letter, (wr, wc) in zip(word_str, positions):
                base = LETTER_DISTRIBUTION.get(letter.lower(), {}).get("points", 0)
                if (wr, wc) in placed_set:
                    if (wr, wc) in TRIPLE_LETTER_SCORE:
                        base *= 3
                    elif (wr, wc) in DOUBLE_LETTER_SCORE:
                        base *= 2
                    if (wr, wc) in TRIPLE_WORD_SCORE:
                        word_mult *= 3
                    elif (wr, wc) in DOUBLE_WORD_SCORE:
                        word_mult *= 2
                word_score += base
            total += word_score * word_mult

    # Avoid double-counting: the scoring above counts each word once per
    # placed tile that's part of it.  We need to deduplicate.
    # Simpler: recalculate using unique words.
    total = 0
    seen_words: Set[Tuple[Tuple[int, int], ...]] = set()
    for r, c, _ in move.tiles:
        for dr, dc in [(0, 1), (1, 0)]:
            winfo = _read_word(temp_board, r, c, dr, dc)
            if winfo is None:
                continue
            _, positions = winfo
            key = tuple(positions)
            if key in seen_words:
                continue
            seen_words.add(key)

            word_str = winfo[0]
            word_score = 0
            word_mult = 1
            for letter, (wr, wc) in zip(word_str, positions):
                base = LETTER_DISTRIBUTION.get(letter.lower(), {}).get("points", 0)
                if (wr, wc) in placed_set:
                    if (wr, wc) in TRIPLE_LETTER_SCORE:
                        base *= 3
                    elif (wr, wc) in DOUBLE_LETTER_SCORE:
                        base *= 2
                    if (wr, wc) in TRIPLE_WORD_SCORE:
                        word_mult *= 3
                    elif (wr, wc) in DOUBLE_WORD_SCORE:
                        word_mult *= 2
                word_score += base
            total += word_score * word_mult

    # Bingo bonus
    if len(move.tiles) == 7:
        total += 50

    move.raw_score = total
    return total


def _rack_balance_bonus(remaining_rack: List[str]) -> float:
    """Heuristic: prefer moves that leave a balanced rack."""
    if not remaining_rack:
        return 10.0  # Used all tiles — great

    vowels = set("aeioõäöü")
    v_count = sum(1 for t in remaining_rack if t.lower() in vowels)
    c_count = len(remaining_rack) - v_count

    # Ideal ratio ~40% vowels
    if len(remaining_rack) >= 2:
        ratio = v_count / len(remaining_rack)
        if 0.3 <= ratio <= 0.5:
            balance = 5.0
        elif 0.2 <= ratio <= 0.6:
            balance = 2.0
        else:
            balance = -3.0
    else:
        balance = 0.0

    # Penalize duplicate letters
    from collections import Counter
    counts = Counter(t.lower() for t in remaining_rack)
    dupes = sum(c - 1 for c in counts.values() if c > 1)
    balance -= dupes * 2.0

    return balance


def _positional_bonus(board: List[List[Optional[str]]], move: Move) -> float:
    """Heuristic: penalize moves that open premium squares for the opponent."""
    bonus = 0.0
    size = len(board)
    placed = move.positions

    # Check if this move opens a TW or DW square for the opponent
    for r, c, _ in move.tiles:
        for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc < size and board[nr][nc] is None and (nr, nc) not in placed:
                if (nr, nc) in TRIPLE_WORD_SCORE:
                    bonus -= 8.0
                elif (nr, nc) in DOUBLE_WORD_SCORE:
                    bonus -= 3.0

    # Bonus for using premium squares ourselves
    for r, c, _ in move.tiles:
        if (r, c) in TRIPLE_WORD_SCORE:
            bonus += 5.0
        elif (r, c) in DOUBLE_WORD_SCORE:
            bonus += 2.0
        elif (r, c) in TRIPLE_LETTER_SCORE:
            bonus += 1.5

    return bonus


# ---------------------------------------------------------------------------
# Move selection
# ---------------------------------------------------------------------------

def select_move(
    board: List[List[Optional[str]]],
    rack: List[str],
    wordlist,
    first_move: bool = False,
    difficulty: str = "medium",
) -> Optional[Move]:
    """Find and select a move based on difficulty level.

    Returns None if no valid move exists (AI should pass or exchange).
    """
    moves = find_all_moves(board, rack, wordlist, first_move)

    if not moves:
        return None

    # Score all moves
    for move in moves:
        _calculate_move_score(board, move)

    if difficulty == "easy":
        # Random move from all valid moves
        return random.choice(moves)

    if difficulty == "medium":
        # Highest raw score
        return max(moves, key=lambda m: m.raw_score)

    # Hard: raw score + heuristics
    for move in moves:
        used_letters = [l for _, _, l in move.tiles]
        remaining = rack[:]
        for l in used_letters:
            if l in remaining:
                remaining.remove(l)
        move.heuristic_score = (
            move.raw_score
            + _rack_balance_bonus(remaining)
            + _positional_bonus(board, move)
        )

    return max(moves, key=lambda m: m.heuristic_score)
