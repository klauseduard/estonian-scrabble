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
- `Tile`: Individual letter tile rendering
- `Board`: Game board rendering and interaction
- `Rack`: Player rack rendering and interaction
- Color constants and visual settings

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

## Testing (Future)

When tests are added:
1. Write unit tests for new features
2. Ensure all tests pass before submitting PR
3. Add integration tests for UI components
4. Test edge cases and error conditions

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

1. **PEP 8**
   - 4 spaces for indentation
   - Maximum line length of 88 characters
   - Use meaningful variable names

2. **Documentation**
   - Docstrings for all public classes and functions
   - Inline comments for complex logic
   - Type hints for all functions

3. **Organization**
   - Keep files focused and single-purpose
   - Group related functionality
   - Use clear, descriptive names

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