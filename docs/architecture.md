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
    def __init__(self, board_size: int = 15):
        self.board: List[List[Optional[str]]]  # Game board
        self.players: List[Player]             # Player list
        self.current_player_idx: int           # Current player
        self.current_turn_tiles: Set[Tuple]    # Tiles placed this turn
```

#### Word Validator (`word_validator.py`)
Handles word validation and scoring:
- Detects words formed on the board
- Validates words against dictionary
- Provides real-time feedback
- Will handle scoring calculations

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
- `Tile`: Letter tile visualization
- `Board`: Game board rendering
- `Rack`: Player rack display

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
4. Add tests (when implemented)

### Code Organization
1. Keep modules focused
2. Use clear naming
3. Document public interfaces
4. Follow type hints 