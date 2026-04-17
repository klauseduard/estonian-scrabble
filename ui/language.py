from typing import Dict, Any

class Language:
    ESTONIAN = "et"
    ENGLISH = "en"

# UI strings for both languages
STRINGS: Dict[str, Dict[str, str]] = {
    "et": {
        "window_title": "Eesti Scrabble",
        "submit_turn": "Kinnita käik",
        "pass_turn": "Jäta vahele",
        "turn": "Käik",
        "player_1": "Mängija 1",
        "player_2": "Mängija 2",
        "player_3": "Mängija 3",
        "player_4": "Mängija 4",
        "select_players": "Vali mängijate arv",
        "lang_button": "EN",  # Show what language you'll get when clicking
        # Premium square labels
        "tws": "3×S",  # Kolmekordne sõna
        "dws": "2×S",  # Kahekordne sõna
        "tls": "3×T",  # Kolmekordne täht
        "dls": "2×T",  # Kahekordne täht
        # Blank tile dialog
        "choose_letter": "Vali täht",
    },
    "en": {
        "window_title": "Estonian Scrabble",
        "submit_turn": "Submit Turn",
        "pass_turn": "Pass Turn",
        "turn": "Turn",
        "player_1": "Player 1",
        "player_2": "Player 2",
        "player_3": "Player 3",
        "player_4": "Player 4",
        "select_players": "Select number of players",
        "lang_button": "ET",  # Show what language you'll get when clicking
        # Premium square labels
        "tws": "TWS",  # Triple Word Score
        "dws": "DWS",  # Double Word Score
        "tls": "TLS",  # Triple Letter Score
        "dls": "DLS",  # Double Letter Score
        # Blank tile dialog
        "choose_letter": "Choose letter",
    }
}

class LanguageManager:
    _instance = None
    _current_language = Language.ESTONIAN  # Default to Estonian

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LanguageManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_string(cls, key: str) -> str:
        return STRINGS[cls._current_language].get(key, key)

    @classmethod
    def set_language(cls, language: str):
        if language in [Language.ESTONIAN, Language.ENGLISH]:
            cls._current_language = language

    @classmethod
    def toggle_language(cls):
        cls._current_language = (
            Language.ENGLISH if cls._current_language == Language.ESTONIAN 
            else Language.ESTONIAN
        )

    @classmethod
    def get_current_language(cls) -> str:
        return cls._current_language 