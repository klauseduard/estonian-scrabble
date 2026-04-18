# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Estonian Scrabble — a Python/Pygame implementation of Scrabble adapted for the Estonian language, with full support for Estonian special characters (õ, ä, ö, ü, š, ž).

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the game
python main.py

# Run all tests
python3 -m unittest discover tests

# Run a specific test file
python3 -m unittest tests/test_word_validator.py

# Run with verbose output
python3 -m unittest -v tests/test_word_validator.py
```

## Architecture

```
User Input → main.py (ScrabbleUI) → GameState (game/state.py)
                                         ↓
                       WordValidator (game/word_validator.py) → WordList (wordlist.py)
                                         ↓
                       UI Components (ui/components.py) render results
```

- **`game/state.py`** — `GameState` manages the 15×15 board, 2–4 players, tile bag, placement, scoring (with bingo bonus, end-game adjustment), blank tile designations, tile exchange, and consecutive-pass game-over detection. `Player` holds name, score, and rack.
- **`game/word_validator.py`** — `WordValidator` detects words formed by placed tiles, validates against the dictionary, enforces placement rules (center square on first move, connectivity, continuous line).
- **`wordlist.py`** — `WordList` uses the official LibreOffice Estonian Hunspell dictionary (et_EE) via the `spylls` library for full morphological word validation, supporting all inflected forms. Dictionary files are downloaded on first run.
- **`ui/components.py`** — Pygame UI components: `Board`, `Tile` (with point value subscripts), `Rack`, `Button`, `ScoreDisplay`.
- **`ui/language.py`** — `LanguageManager` singleton for Estonian/English i18n with Estonian fallback for missing keys.
- **`main.py`** — `ScrabbleUI` runs the Pygame event loop, handles drag-and-drop tile placement and rack reordering, blank tile letter selection dialog, turn transition screen, score preview, game-over screen with score breakdown, and player count selection.
- **`game/constants.py`** — Official Estonian Scrabble letter distribution (100 letters + 2 blanks = 102 tiles), premium square positions.

## Code Style

- PEP 8 with 100-char line length (Black formatter)
- Double quotes for strings
- Type hints on function signatures
- snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- Private members prefixed with underscore
- Imports grouped: stdlib → third-party → local, alphabetically sorted within groups

## Git Conventions

- Conventional Commits: `<type>(<scope>): <description>` (feat, fix, docs, style, refactor, test, chore, perf)
- Subject line ≤72 chars, imperative mood, no trailing period
- Branches: `feature/<name>`, `fix/<description>`, `release/v<version>`
