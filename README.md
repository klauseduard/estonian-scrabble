# Estonian Scrabble

A Scrabble game implementation that supports Estonian alphabet and uses Estonian wordlist.

## Features

- Full Estonian alphabet support including õ, ä, ö, ü, š, ž
- Visual feedback for valid/invalid word placements
- Drag-and-drop tile placement
- Real-time word validation
- Premium square scoring system
- Support for two players

## Project Structure

```
scrabble/
├── game/                   # Game logic and state management
│   ├── __init__.py        # Package exports
│   ├── constants.py       # Game constants (letter distribution, premium squares)
│   ├── state.py          # Core game state management
│   └── word_validator.py  # Word validation logic
├── ui/                    # User interface components
│   ├── __init__.py       # Package exports
│   └── components.py     # UI components (Board, Tile, Rack)
├── main.py               # Main game entry point
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Run the game:
```bash
python main.py
```

## Game Rules

- The game follows standard Scrabble rules with adaptations for Estonian alphabet
- Supports Estonian special characters (õ, ä, ö, ü, š, ž)
- Uses Estonian wordlist for word validation
- Premium squares follow standard Scrabble board layout

## Development

### Architecture

The project follows a modular architecture with clear separation of concerns:

1. **Game Logic (`game/`):**
   - `state.py`: Manages game state, player turns, and tile placement
   - `word_validator.py`: Handles word validation and scoring
   - `constants.py`: Contains game constants and configuration

2. **User Interface (`ui/`):**
   - `components.py`: Reusable UI components
   - Handles user input and visual feedback

### Adding New Features

When adding new features:

1. Determine which module should contain the new code
2. Update relevant tests (when we add them)
3. Follow the existing code style
4. Update documentation

### Code Style

- Use type hints for function parameters and return values
- Follow PEP 8 guidelines
- Write docstrings for classes and functions
- Keep functions focused and single-purpose

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Future Improvements

- [ ] Add proper Estonian wordlist source
- [ ] Implement scoring system
- [ ] Add game save/load functionality
- [ ] Add network multiplayer support
- [ ] Add unit tests
- [ ] Add AI opponent

## License

This project is open source and available under the MIT License. 