# Contributing to Estonian Scrabble

Thank you for your interest in contributing to Estonian Scrabble! This document provides guidelines and information for contributors.

## Development Environment Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd scrabble
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

   For development, install the linter and formatter too, and enable the git
   hooks:
```bash
pip install -r requirements-dev.txt
tools/hooks/install.sh
```

   Prose in Markdown is linted by [Vale](https://vale.sh), which is a single Go
   binary rather than a Python package. Install it to `~/.local/bin` or anywhere
   on your `PATH`. The hook skips the prose check when Vale is absent, so this
   step is optional:
```bash
curl -sfL https://github.com/errata-ai/vale/releases/download/v3.18.0/vale_3.18.0_Linux_64-bit.tar.gz \
  | tar xz -C ~/.local/bin vale
```

   Claude Code users additionally get `tools/hooks/ruff-fix-hook.sh` wired up
   automatically via `.claude/settings.json`, which formats Python files as
   they are written. Personal overrides belong in `.claude/settings.local.json`,
   which stays out of the repo.

3. Run the game to verify setup:
```bash
python main.py
```

## Project Architecture

### Game Module (`game/`)

The game module handles all game logic and state management:

#### `state.py`
- `GameState`: Main game state controller
- `Player`: Player data and actions
- Handles:
  - Board state
  - Player management
  - Turn management
  - Tile placement validation

#### `word_validator.py`
- `WordValidator`: Word validation logic
- Handles:
  - Word formation detection
  - Dictionary validation
  - Word placement validation

#### `constants.py`
- Letter distribution
- Point values
- Premium square locations
- Other game constants

### UI Module (`ui/`)

The UI module handles all visual elements and user interaction:

#### `components.py`
- `Tile`: Individual letter tile rendering (with point value subscripts)
- `Board`: Game board rendering and interaction
- `Rack`: Player rack rendering and interaction
- `Button`: Clickable UI button
- `ScoreDisplay`: Player scores display
- `TurnIndicator`: Current player turn indicator
- Color constants and visual settings

#### `language.py`
- `LanguageManager`: Singleton for Estonian/English i18n with Estonian fallback for missing keys

## Adding New Features

1. **Choose the Right Module**
   - Game logic goes in `game/`
   - Visual elements go in `ui/`
   - New features might require changes in both

2. **Follow the Pattern**
   - Use existing patterns and conventions
   - Keep components modular and single-purpose
   - Add appropriate documentation

3. **Type Hints**
   - Use Python type hints for all functions
   - Example:
   ```python
   def place_tile(self, row: int, col: int, tile_idx: int) -> bool:
       """Place a tile from the current player's rack onto the board.
       
       Args:
           row: The row to place the tile
           col: The column to place the tile
           tile_idx: The index of the tile in the player's rack
           
       Returns:
           bool: True if placement was successful, False otherwise
       """
   ```

4. **Documentation**
   - Add docstrings to all new classes and functions
   - Update README.md if adding major features
   - Comment complex logic

## Testing

Tests use Python's `unittest` framework with mock wordlists for isolated testing.

1. Run all tests:
   ```bash
   python3 -m unittest discover tests
   ```
2. Test files:
   - `tests/test_game_state.py` — Game state, scoring, and turn management tests
   - `tests/test_word_validator.py` — Word validation and placement rule tests
3. Write unit tests for new features
4. Ensure all tests pass before submitting PR
5. Test edge cases and error conditions

## Common Tasks

### Adding a New UI Component

1. Add the component class to `ui/components.py`
2. Follow the existing pattern (initialization, drawing, interaction)
3. Add any new color constants needed
4. Update the main game loop if needed

### Modifying Game Logic

1. Identify the appropriate module (`state.py` or `word_validator.py`)
2. Add new methods or modify existing ones
3. Update type hints and documentation
4. Consider impact on other components

### Adding Game Features

1. Plan the feature implementation
2. Update game state management if needed
3. Add UI components for interaction
4. Update documentation

## Code Style

Follow these style guidelines:

1. **PEP 8** — enforced by ruff and Black, configured in `pyproject.toml`
   - Run `ruff check --fix .` then `black .` before committing; the pre-commit
     hook rejects anything that fails either
   - Indentation, line length, quote style, naming and import order are all
     handled by the tools. There is no separate list to memorise: if it passes
     both commands, it matches the house style
   - Black will not split long string literals — if one pushes a line past 100,
     hoist it to a local rather than wrapping it (Black collapses implicit
     concatenation into the adjacent-string form)
   - Use meaningful variable names; no tool can check this one

2. **Documentation**
   - Docstrings for all public classes and functions
   - Inline comments for complex logic
   - Type hints on function signatures. Coverage is incomplete (~146 gaps), so
     this is not a gate — annotate new code rather than retrofitting old

3. **Organization**
   - Keep files focused and single-purpose
   - Group related functionality
   - Use clear, descriptive names

4. **Design rules no linter can check**

   These are not general advice. Each one describes a mistake already present in
   this codebase, named so it does not spread:

   - **A failed dependency must not degrade into a plausible wrong answer.**
     `WordList` used to log a dictionary load failure and continue with
     `_dict = None`. From then on `is_valid_word` returned False for every word,
     so a broken install looked exactly like a working game that rejected your
     vocabulary. It now raises `DictionaryUnavailableError` at construction.
     Apply the same rule to new code: if a dependency is required, raise when it
     is missing rather than returning a default that reads as a real answer.
     Fallbacks that still give correct results — a missing DAWG dropping to
     brute-force move generation, a missing patched dictionary dropping to the
     upstream one — are fine and should stay quiet.
   - **Event and message handling dispatches to named handlers.** `_dispatch` in
     `server/app.py` is sixteen branches, each one line, each calling a named
     handler. `main.py` now matches: `run()` is six lines, `_handle_event` is a
     precedence ladder (quit, then each modal overlay, then buttons, then the
     board), and every case is its own method. It was a single 152-line function
     nested ten deep until 2026-08-22. Add new cases as new handlers, not as new
     branches inside an existing one.
   - **Catch the specific exception, and check what it actually means.**
     `except WebSocketDisconnect: pass` in `server/app.py` is correct: a client
     disconnecting is ordinary control flow, the exception is named explicitly,
     and cleanup happens in `finally`. `tools/build_dawg.py` used to say
     `except OSError: pass` when reading the blocklist. That could not tell an
     absent file, which is fine because the DAWG is then unfiltered, from a file
     it lacks permission to read, which is a real problem. It now checks for
     absence first and warns on anything else.

## Submitting Changes

1. Create a new branch for your feature
2. Make your changes
3. Update documentation
4. Submit a pull request with:
   - Clear description of changes
   - Any new dependencies
   - Screenshots if UI changes
   - Testing instructions

## Getting Help

- Open an issue for bugs or feature requests
- Ask questions in discussions
- Review existing code for patterns and conventions 