# Estonian Scrabble Game Rules

## Overview

Estonian Scrabble follows the standard Scrabble rules with adaptations for the Estonian language and alphabet. Supports 2–4 players.

## Game Components

### Board
- 15x15 grid
- Center square (7,7) is a Double Word Score
- Premium squares for bonus scoring:
  - Triple Word Score (3×S, red squares)
  - Double Word Score (2×S, pink squares)
  - Triple Letter Score (3×T, dark blue squares)
  - Double Letter Score (2×T, light blue squares)

### Tiles (102 total)
Estonian Scrabble uses the following letter distribution:

| Letter | Count | Points |
|--------|-------|--------|
| _ (blank) | 2 | 0 |
| a | 10 | 1 |
| e | 9 | 1 |
| i | 9 | 1 |
| o | 5 | 1 |
| u | 5 | 1 |
| s | 8 | 1 |
| t | 7 | 1 |
| k | 5 | 1 |
| l | 5 | 1 |
| d | 4 | 2 |
| m | 4 | 2 |
| n | 4 | 2 |
| r | 2 | 2 |
| g | 2 | 3 |
| v | 2 | 3 |
| b | 1 | 4 |
| h | 2 | 4 |
| j | 2 | 4 |
| p | 2 | 4 |
| õ | 2 | 4 |
| ä | 2 | 5 |
| ü | 2 | 5 |
| ö | 2 | 6 |
| f | 1 | 8 |
| š | 1 | 10 |
| z | 1 | 10 |
| ž | 1 | 10 |

## Game Play

### Setup
1. Select number of players (2–4)
2. Each player draws 7 tiles
3. First player places a word through the center square
4. Play continues clockwise

### Turn Actions
Players can:
1. Place new tiles to form words
2. Remove incorrectly placed tiles (before committing turn)
3. Reorder tiles in the rack by dragging
4. Pass their turn
5. Exchange tiles with the bag (only when bag has ≥ 7 tiles)

### Blank Tiles
- Can represent any letter — player chooses when placing
- Score 0 points regardless of the letter they represent
- Do not activate letter premium squares (DLS/TLS)
- Word premium squares (DWS/TWS) still apply to words containing blanks

### Word Formation
1. Words must:
   - Connect to existing tiles
   - Form valid Estonian words (validated using Hunspell dictionary)
   - Read left-to-right or top-to-bottom

2. All connected tiles must form valid words

### Scoring
1. Letter Points:
   - Each letter has a point value shown as a subscript on the tile
   - Premium squares multiply points for newly placed tiles only
   - Premiums are "used up" — they do not apply to tiles from previous turns

2. Premium Squares:
   - Triple Word Score (red squares)
   - Double Word Score (pink squares, including center)
   - Triple Letter Score (dark blue squares)
   - Double Letter Score (light blue squares)

3. Word Multipliers:
   - Apply after letter premiums
   - Multiple word multipliers stack multiplicatively

4. Bingo Bonus:
   - Using all 7 tiles in one turn awards a 50-point bonus

5. A live score preview is shown above the rack while tiles are placed

### Game End
The game ends when:
1. The bag is empty and one player uses all their tiles
2. All players pass consecutively (one full round of passes)

Final score adjustments:
- Subtract the point value of remaining tiles from each player's score
- If a player emptied their rack, add the total value of all opponents' remaining tiles to their score

A game-over screen shows the final score breakdown (word score, tile adjustment, total) for each player.

## User Interface

### Tile Placement
1. Drag tiles from rack to board
2. Right-click to remove placed tiles
3. Drag tiles within the rack to reorder
4. Visual feedback: green for valid words, red for invalid

### Turn Management
1. Commit turn when all words are valid (button enables automatically)
2. Pass turn if no moves possible
3. A transition screen hides tiles between players

### Display
- Point values shown on each tile
- Remaining tile count displayed below the rack
- Player scores and turn indicator at the top
- Language toggle (Estonian/English) in the bottom-right corner
