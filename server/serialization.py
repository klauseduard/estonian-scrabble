"""Serialize GameState to JSON-safe dictionaries for WebSocket transport."""

from typing import Any, Dict, List, Optional, Tuple

from game.state import GameState


def serialize_board(game: GameState) -> List[List[Optional[str]]]:
    """Return the full 15x15 board as a 2D list of letters (None for empty)."""
    return [
        [cell for cell in row]
        for row in game.board
    ]


def serialize_current_turn_tiles(game: GameState) -> List[Dict[str, int]]:
    """Return the positions of tiles placed during the current turn."""
    return [
        {"row": row, "col": col}
        for row, col in game.current_turn_tiles
    ]


def serialize_score_preview(game: GameState) -> List[Dict[str, Any]]:
    """Return the score breakdown for the current placement."""
    breakdown = game.calculate_turn_score()
    return [
        {"word": word, "score": score}
        for word, score in breakdown
    ]


def serialize_players(game: GameState) -> List[Dict[str, Any]]:
    """Return public player info (name, score) for all players."""
    return [
        {"name": player.name, "score": player.score}
        for player in game.players
    ]


def serialize_game_state(game: GameState, player_index: int) -> Dict[str, Any]:
    """Build the full game-state payload for a specific player.

    Only the requesting player's rack is included (hidden information).
    """
    data: Dict[str, Any] = {
        "type": "game_state",
        "board": serialize_board(game),
        "players": serialize_players(game),
        "current_player_index": game.current_player_idx,
        "tiles_remaining": len(game.tile_bag),
        "game_over": game.game_over,
    }

    # Only send the player's own rack
    if 0 <= player_index < len(game.players):
        data["rack"] = list(game.players[player_index].rack)
    else:
        data["rack"] = []

    # Active player sees their placed tiles and score preview
    if player_index == game.current_player_idx:
        data["current_turn_tiles"] = serialize_current_turn_tiles(game)
        data["score_preview"] = serialize_score_preview(game)
    else:
        data["current_turn_tiles"] = []
        data["score_preview"] = []

    return data


def serialize_game_over(game: GameState) -> Dict[str, Any]:
    """Build the game-over payload with final scores."""
    scores = [
        {"name": player.name, "score": player.score}
        for player in game.players
    ]
    return {
        "type": "game_over",
        "scores": scores,
    }
