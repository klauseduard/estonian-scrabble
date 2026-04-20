# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial game implementation
- Estonian alphabet support
- Basic game board with drag-and-drop tile placement
- Word validation with visual feedback
- Two-player turn system
- Premium square layout
- Right-click to remove tiles
- Real-time word validation
- Estonian Hunspell dictionary via spylls library for full morphological word validation
- Full scoring system with premium squares, bingo bonus, and end-game score adjustment
- Unit tests for game state, scoring, and word validation
- 2-4 player support with player count selection screen
- Player name entry screen
- Blank tile support with letter selection dialog
- Tile exchange (swap tiles with the bag when bag has 7+ tiles)
- Turn transition screen to hide tiles between players
- Score preview above rack during tile placement
- Game-over screen with score breakdown (word score, tile adjustment, total)
- Estonian/English language toggle (LanguageManager singleton)
- Rack reordering via drag-and-drop
- Logging system

### Changed
- Refactored code into modular structure
- Separated UI and game logic
- Improved documentation

### Todo
- Add game save/load functionality
- Add network multiplayer
- Add AI opponent

## [0.1.0] - 2024-03-19
### Added
- Initial project structure
- Basic game mechanics
- UI components
- Documentation 