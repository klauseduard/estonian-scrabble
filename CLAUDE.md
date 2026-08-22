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
- **`wordlist.py`** — `WordList` uses the official LibreOffice Estonian Hunspell dictionary (et_EE) via the `spylls` library for full morphological word validation, supporting all inflected forms. Dictionary files are downloaded on first run, then patched for Scrabble by `tools/patch_dictionary.py` (strips the compound flag from vowelless abbreviation entries that let garbage compounds like "tköis" validate — issue #32). `data/extra_words.txt` (allowlist with inflection model words) and `data/blocked_words.txt` (blocklist) tune validation without touching code. `WordList().strict` (no compounds) validates AI moves and exposes a `dawg` for move generation, built by `tools/build_dawg.py` (~30 s, cached in dict/).
- **`game/ai_player.py` + `game/dawg.py`** — AI move generation: Appel & Jacobson-style traversal of a DAWG built from all ~10.7M strict-dictionary forms (issue #40); exhaustive and instant, includes bingos and blank plays. Falls back to budgeted brute force when no DAWG is available (mock wordlists in tests). Modes: "easy" picks a mid-percentile move, "strong" the heuristic best.
- **`ui/components.py`** — Pygame UI components: `Board`, `Tile` (with point value subscripts), `Rack`, `Button`, `ScoreDisplay`.
- **`ui/language.py`** — `LanguageManager` singleton for Estonian/English i18n with Estonian fallback for missing keys.
- **`main.py`** — `ScrabbleUI` runs the Pygame event loop, handles drag-and-drop tile placement and rack reordering, blank tile letter selection dialog, turn transition screen, score preview, game-over screen with score breakdown, and player count selection.
- **`game/constants.py`** — Official Estonian Scrabble letter distribution (100 letters + 2 blanks = 102 tiles), premium square positions.

## Code Style

Enforced by ruff and Black — `pyproject.toml` is the source of truth, not this
list. Before committing:

```bash
.venv/bin/ruff check --fix .
.venv/bin/black .
```

The pre-commit hook in `tools/hooks/` blocks commits that fail either. Run
ruff first and Black second — Black owns the final layout.

Line length, quote style, naming and import order are all enforced, so they are
not restated here — `ruff check` and `black --check` are the authority. Black is
pinned to 26.5.1 in `requirements-dev.txt`; an unpinned Black formats differently
across versions.

Not enforced, so worth stating:

- Type hints on function signatures. `ruff --select ANN` reports 146 gaps today,
  so this is not a gate — annotate new code, do not retrofit opportunistically.
- Private members prefixed with underscore.

### Design rules no linter can check

Each of these was earned from a real defect in this repo. They are specific on
purpose: a general appeal to the Zen of Python does not tell you what to do at
the branch point.

- **A failed dependency must not degrade into a plausible wrong answer.**
  `WordList` used to log a load failure and continue with `_dict = None`, after
  which `is_valid_word` returned False for every word — indistinguishable to the
  player from "not a word". It now raises `DictionaryUnavailableError`, so a
  broken install fails at startup instead of playing badly. Do not reintroduce
  this shape: a dependency that is required should raise, not return a default
  that looks like a real answer. Genuine fallbacks (a missing DAWG dropping to
  brute force, a missing patched dictionary dropping to upstream) stay silent
  because they still produce correct results.
- **Event and message handling dispatches to named handlers.** `server/app.py`
  `_dispatch` is the pattern to copy (16 arms, 2 levels deep). `main.py` `run()`
  is the one to stop growing: 152 lines, 10 levels of nesting below the `def`.
- **Catch the specific exception.** `except WebSocketDisconnect: pass` is correct
  — a disconnect is normal control flow, explicitly named, with cleanup in
  `finally`. `except OSError: pass` in `tools/build_dawg.py` is not: it cannot
  distinguish an absent file from an unreadable one.

## Git Conventions

- Conventional Commits: `<type>(<scope>): <description>` (feat, fix, docs, style, refactor, test, chore, perf)
- Subject line ≤72 chars, imperative mood, no trailing period
- Branches: `feature/<name>`, `fix/<description>`, `release/v<version>`
