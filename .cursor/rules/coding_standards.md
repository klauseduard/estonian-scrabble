# Coding Standards

## Python Style Guide
- Follow PEP 8 guidelines
- Maximum line length: 100 characters
- Use 4 spaces for indentation (no tabs)
- Use double quotes for strings unless single quotes are needed
- Add type hints for function parameters and return values
- Include docstrings for all modules, classes, and functions

## Naming Conventions
- Classes: PascalCase (e.g., `GameBoard`, `TileRack`)
- Functions/Methods: snake_case (e.g., `validate_word`, `place_tile`)
- Variables: snake_case (e.g., `player_score`, `current_turn`)
- Constants: UPPER_CASE (e.g., `BOARD_SIZE`, `LETTER_POINTS`)
- Private members: prefix with underscore (e.g., `_calculate_score`)

## Code Organization
- Group imports in the following order:
  1. Standard library imports
  2. Third-party imports
  3. Local application imports
- Separate import groups with a blank line
- Within each group, sort imports alphabetically

## Documentation
- Module-level docstrings should describe the module's purpose
- Function docstrings should include:
  - Brief description
  - Parameters and their types
  - Return value and type
  - Any exceptions that may be raised
- Include examples in docstrings when helpful

## Testing
- Write unit tests for all new functionality
- Test both success and failure cases
- Use descriptive test names that explain the scenario
- Keep test files organized parallel to source files

## Comments
- Write comments in English
- Explain why, not what (the code shows what)
- Keep comments current with code changes
- Use TODO comments for planned improvements 