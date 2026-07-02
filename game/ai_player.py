"""AI player for Estonian Scrabble.

Generates valid moves by scanning the board for anchor points, trying
rack tile combinations, and scoring candidates.  The module is pure
game-logic — no UI or server dependencies — so it works with both the
Pygame desktop client and the FastAPI web server.

Two modes (issue #40 tracks a fundamentally better generator):
  - fast:   bounded search, answers in ~a second; short words only,
            no blank tiles. Optimizes response time.
  - strong: spends a ~12 s time budget hunting longer words (up to
            bingos) and playing blank tiles; selects with rack-balance
            and positional heuristics. Optimizes playing strength.

Legacy difficulty names map onto these: easy = fast with a random
move, medium = fast, hard = strong.
"""

import itertools
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .constants import (
    DOUBLE_LETTER_SCORE,
    DOUBLE_WORD_SCORE,
    LETTER_DISTRIBUTION,
    TRIPLE_LETTER_SCORE,
    TRIPLE_WORD_SCORE,
)

# Wall-clock budgets per move (seconds)
FAST_TIME_BUDGET = 1.5
STRONG_TIME_BUDGET = 12.0

# Blank substitutions are tried in this order (common letters first)
# so the time budget is spent on the most promising designations.
BLANK_LETTERS = "aeistulkomnrdgvhjpbõäöüfšzž"


@dataclass
class Move:
    """A candidate move the AI might play."""

    tiles: List[Tuple[int, int, str]]  # (row, col, letter) placements
    words_formed: List[str]
    blanks: Set[Tuple[int, int]] = field(default_factory=set)  # blank-tile positions
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
    lengths: range,
    full_perm_max_length: int,
    deadline: Optional[float] = None,
    blank_indices: Optional[Set[int]] = None,
) -> List[Move]:
    """Generate valid moves through *anchor* in direction (dr, dc).

    *lengths* selects how many rack tiles to try placing. Combinations up
    to *full_perm_max_length* tiles get every permutation; longer ones
    get a single permutation (full enumeration of 6!–7! orderings would
    blow any budget). *deadline* (time.monotonic) aborts the search.
    *blank_indices* marks rack positions that are really blank tiles
    substituted with a letter — their placements score 0.
    """
    size = len(board)
    moves: List[Move] = []
    blank_indices = blank_indices or set()

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

        usable = list(range(len(rack)))
        for length in lengths:
            if length > len(rack) or length > 7:
                continue
            for combo in itertools.combinations(usable, length):
                if deadline is not None and time.monotonic() > deadline:
                    return moves
                if length > full_perm_max_length:
                    perms = [combo]  # one ordering only for long placements
                else:
                    perms = itertools.permutations(combo)
                for perm in perms:
                    if deadline is not None and time.monotonic() > deadline:
                        return moves
                    tiles_placed = []
                    blank_positions: Set[Tuple[int, int]] = set()
                    temp_board = [row[:] for row in board]
                    pr, pc = start_r, start_c
                    tile_idx = 0

                    # Walk along the line, placing tiles in empty cells
                    tiles_used = 0
                    while tiles_used < len(perm) and 0 <= pr < size and 0 <= pc < size:
                        if temp_board[pr][pc] is None:
                            rack_idx = perm[tile_idx]
                            letter = rack[rack_idx]
                            temp_board[pr][pc] = letter
                            tiles_placed.append((pr, pc, letter))
                            if rack_idx in blank_indices:
                                blank_positions.add((pr, pc))
                            tile_idx += 1
                            tiles_used += 1
                        # else: existing tile, skip over it
                        pr += dr
                        pc += dc

                    if not tiles_placed:
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
                        blanks=blank_positions,
                    ))

    return moves


def _collect_moves(
    board, rack, anchors, wordlist, validation_cache, first_move,
    lengths, full_perm_max_length, deadline,
    all_moves, seen_placements, blank_indices=None,
):
    """Run the line generator over all anchors, deduplicating placements."""
    for anchor_r, anchor_c in anchors:
        if deadline is not None and time.monotonic() > deadline:
            return
        for dr, dc in [(0, 1), (1, 0)]:  # horizontal, vertical
            moves = _generate_line_moves(
                board, rack, anchor_r, anchor_c, dr, dc,
                wordlist, validation_cache, first_move,
                lengths=lengths,
                full_perm_max_length=full_perm_max_length,
                deadline=deadline,
                blank_indices=blank_indices,
            )
            for move in moves:
                key = frozenset(
                    (r, c, l, (r, c) in move.blanks) for r, c, l in move.tiles
                )
                if key not in seen_placements:
                    seen_placements.add(key)
                    all_moves.append(move)


def find_all_moves(
    board: List[List[Optional[str]]],
    rack: List[str],
    wordlist,
    first_move: bool = False,
    mode: str = "fast",
) -> List[Move]:
    """Find valid moves for the given rack on the current board.

    fast:   short placements (1–4 tiles, full permutations), blanks
            unused, ~FAST_TIME_BUDGET wall clock.
    strong: everything fast finds, then spends the rest of
            STRONG_TIME_BUDGET on longer placements (5–7 tiles,
            permutations capped) and blank-tile substitutions.

    This is the CPU-intensive function that should be run via
    ``asyncio.run_in_executor`` on the server.
    """
    anchors = _get_anchors(board, first_move)
    validation_cache: Dict[str, bool] = {}
    all_moves: List[Move] = []
    seen_placements: Set[frozenset] = set()

    budget = STRONG_TIME_BUDGET if mode == "strong" else FAST_TIME_BUDGET
    deadline = time.monotonic() + budget

    plain_rack = [t for t in rack if t != "_"]
    blank_count = len(rack) - len(plain_rack)

    # Pass 1 (both modes): short placements, full permutations, no blanks.
    _collect_moves(
        board, plain_rack, anchors, wordlist, validation_cache, first_move,
        lengths=range(1, 5), full_perm_max_length=4, deadline=deadline,
        all_moves=all_moves, seen_placements=seen_placements,
    )

    if mode != "strong":
        return all_moves

    # Pass 2: longer placements — bingo hunting. Longest first so the
    # budget is spent on the highest-value words; full permutations,
    # cut off by the deadline (issue #40 tracks the real fix).
    _collect_moves(
        board, plain_rack, anchors, wordlist, validation_cache, first_move,
        lengths=range(7, 4, -1), full_perm_max_length=7, deadline=deadline,
        all_moves=all_moves, seen_placements=seen_placements,
    )

    # Pass 3: blank substitutions, common letters first, until the budget
    # runs out. Each variant rack replaces the blank(s) with a concrete
    # letter; those placements are marked and score 0.
    if blank_count > 0:
        blank_letter_sets = (
            [(a,) for a in BLANK_LETTERS]
            if blank_count == 1
            else [(a, b) for a in BLANK_LETTERS[:12] for b in BLANK_LETTERS[:12]]
        )
        for letters in blank_letter_sets:
            if time.monotonic() > deadline:
                break
            variant = plain_rack + list(letters)
            blank_indices = set(range(len(plain_rack), len(variant)))
            _collect_moves(
                board, variant, anchors, wordlist, validation_cache, first_move,
                lengths=range(1, 6), full_perm_max_length=4, deadline=deadline,
                all_moves=all_moves, seen_placements=seen_placements,
                blank_indices=blank_indices,
            )

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

    # Score each unique word formed
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
                if (wr, wc) in move.blanks:
                    base = 0  # blank tiles always score 0
                else:
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
    difficulty: str = "fast",
) -> Optional[Move]:
    """Find and select a move for the given mode.

    Modes: "fast" (bounded search, greedy pick) and "strong" (deep
    search, heuristic pick). Legacy difficulty names are mapped:
    easy = fast + random move, medium = fast, hard = strong.

    Returns None if no valid move exists (AI should pass or exchange).
    """
    mode = {"easy": "fast", "medium": "fast", "hard": "strong"}.get(difficulty, difficulty)
    if mode not in ("fast", "strong"):
        mode = "fast"

    moves = find_all_moves(board, rack, wordlist, first_move, mode=mode)

    if not moves:
        return None

    # Score all moves
    for move in moves:
        _calculate_move_score(board, move)

    if difficulty == "easy":
        # Random move from all valid moves
        return random.choice(moves)

    if mode == "fast":
        # Highest raw score
        return max(moves, key=lambda m: m.raw_score)

    # Strong: raw score + heuristics
    for move in moves:
        remaining = rack[:]
        for r, c, letter in move.tiles:
            used = "_" if (r, c) in move.blanks else letter
            if used in remaining:
                remaining.remove(used)
        move.heuristic_score = (
            move.raw_score
            + _rack_balance_bonus(remaining)
            + _positional_bonus(board, move)
        )

    return max(moves, key=lambda m: m.heuristic_score)
