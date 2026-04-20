# Estonian Scrabble Architecture

This document describes the technical architecture of the Estonian Scrabble game.

## Overview

The application is built using Python and Pygame, following a modular architecture that separates game logic from user interface components.

## Core Components

### 1. Game Logic (`game/`)

#### GameState (`state.py`)
The central controller for game mechanics:
- Manages the game board state
- Handles player turns
- Controls tile placement and removal
- Manages the tile bag and distribution

```python
class GameState:
    def __init__(self, board_size: int = 15, num_players: int = 2):
        self.board: List[List[Optional[str]]]  # Game board
        self.players: List[Player]             # Player list
        self.current_player_idx: int           # Current player
        self.current_turn_tiles: Set[Tuple]    # Tiles placed this turn
        self.blank_designations: Dict[Tuple, str]  # Blank tile letter assignments
        self.consecutive_passes: int           # Tracks consecutive passes for game-over
        self.game_over: bool                   # Whether the game has ended
        self.first_move: bool                  # Whether no tiles have been committed yet
```

#### Word Validator (`word_validator.py`)
Handles word validation and scoring:
- Detects words formed on the board
- Validates words against dictionary
- Provides real-time feedback
- Handles scoring calculations (premium squares, bingo bonus, end-game adjustment)

```python
class WordValidator:
    def __init__(self, wordlist: WordList):
        self.wordlist: WordList                # Dictionary reference
        self.word_validity: Dict[Tuple, bool]  # Word validity cache
```

#### Constants (`constants.py`)
Game configuration and constants:
- Letter distribution and points
- Premium square locations
- Board configuration

### 2. User Interface (`ui/`)

#### Components (`components.py`)
Reusable UI elements:
- `Tile`: Letter tile visualization (with point value subscripts)
- `Board`: Game board rendering
- `Rack`: Player rack display
- `Button`: Clickable UI button
- `ScoreDisplay`: Player scores display
- `TurnIndicator`: Current player turn indicator

#### Language (`language.py`)
- `LanguageManager`: Singleton for Estonian/English i18n with Estonian fallback for missing keys

### 4. Word List (`wordlist.py`)
Dictionary integration:
- `WordList`: Uses the official LibreOffice Estonian Hunspell dictionary (et_EE) via the `spylls` library
- Supports full morphological word validation including all inflected forms
- Dictionary files are downloaded on first run

```python
class Board:
    def __init__(self, size: int, tile_size: int, ...):
        self.size: int           # Board dimensions
        self.tile_size: int      # Tile pixel size
        self.board_start: int    # Board starting position
```

### 3. Main Game Loop (`main.py`)
Coordinates between UI and game logic:
- Handles event processing
- Updates game state
- Manages rendering
- Controls game flow

## Data Flow

1. **User Input**
   ```
   Mouse Event -> Main Loop -> UI Component -> Game State Update
   ```

2. **Word Validation**
   ```
   Tile Placement -> Word Detection -> Dictionary Check -> Visual Feedback
   ```

3. **Turn Management**
   ```
   Turn End -> Score Calculation -> State Update -> Player Switch
   ```

## State Management

### Game State
- Board state (15x15 grid)
- Player information
- Current turn state
- Tile bag contents

### UI State
- Selected tile
- Dragging state
- Visual feedback
- Animation states
- Blank tile dialog state (letter selection for blank tiles)
- Turn transition state (screen between player turns)
- Game over state (final score breakdown display)
- Cached score breakdown (avoids recalculating every frame)

## Future Considerations

### Planned Features
1. **Network Multiplayer**
   - Client-server architecture
   - State synchronization
   - Move validation

2. **AI Opponent**
   - Word finding algorithm
   - Strategy implementation
   - Difficulty levels

3. **Save/Load System**
   - Game state serialization
   - Progress persistence
   - Replay functionality

### Scalability Considerations
1. **Performance**
   - Word validation optimization
   - Rendering efficiency
   - Memory management

2. **Modularity**
   - Plugin system for extensions
   - AI opponent integration
   - Network layer abstraction

## Development Guidelines

### Adding Features
1. Identify the appropriate module
2. Maintain separation of concerns
3. Update documentation
4. Add tests

### Code Organization
1. Keep modules focused
2. Use clear naming
3. Document public interfaces
4. Follow type hints 