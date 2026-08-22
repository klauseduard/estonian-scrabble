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
     handled by the tools. There is no separate list to memorise — if it passes
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
     When `WordList` cannot load its dictionary it logs the error and continues
     with `_dict = None`. From then on `is_valid_word` returns False for every
     word, so a broken install looks exactly like a working game that rejects
     your vocabulary. Prefer raising, or expose an availability flag the caller
     checks once at startup.
   - **Event and message handling dispatches to named handlers.** Compare
     `_dispatch` in `server/app.py` — sixteen branches, each one line, calling a
     named handler — with `run()` in `main.py`, where the pygame event loop has
     grown to 152 lines and ten levels of indentation. Same codebase, same
     problem, two very different outcomes. Copy the first one.
   - **Catch the specific exception.** `except WebSocketDisconnect: pass` is
     correct: a client disconnecting is ordinary control flow, the exception is
     named explicitly, and cleanup happens in `finally`. `except OSError: pass`
     in `tools/build_dawg.py` is not, because it cannot tell a file that is
     absent from one it lacks permission to read, and treats both as empty.

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