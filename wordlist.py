import os
import urllib.request
import logging
from typing import Set
import unicodedata

class WordList:
    # Estonian Institute's wordlist
    WORDLIST_URL = "https://raw.githubusercontent.com/EKI-PIK/ekilex/master/ekilex-app/fileresources/sql/classifier_data.sql"
    LOCAL_FILENAME = "estonian_words.txt"
    
    def __init__(self):
        self.words: Set[str] = set()
        self._setup_logging()
        self._load_wordlist()

    def _setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def _normalize_word(self, word: str) -> str:
        """Normalize word to ensure consistent character handling."""
        # Replace common problematic character combinations
        replacements = {
            'š': 'š',  # Different forms of š
            'ş': 'š',
            'sh': 'š',
            'ž': 'ž',  # Different forms of ž
            'ż': 'ž',
            'zh': 'ž',
            'õ': 'õ',  # Different forms of õ
            'ő': 'õ',
            'ø': 'õ',
            'ä': 'ä',  # Different forms of ä
            'æ': 'ä',
            'ö': 'ö',  # Different forms of ö
            'ő': 'ö',
            'ü': 'ü',  # Different forms of ü
            'ű': 'ü',
            # Add more replacements if needed
        }
        
        # Apply replacements
        result = word.lower()
        for old, new in replacements.items():
            result = result.replace(old, new)

        # First decompose to handle combined characters
        decomposed = unicodedata.normalize('NFKD', result)
        # Then recompose to get standard form
        normalized = unicodedata.normalize('NFKC', decomposed)
        self.logger.debug(f"Normalized '{word}' to '{normalized}'")
        return normalized

    def _download_wordlist(self) -> bool:
        """Download the Estonian wordlist from GitHub."""
        self.logger.info("Downloading Estonian wordlist from GitHub...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}  # Some servers require a user agent
            request = urllib.request.Request(self.WORDLIST_URL, headers=headers)
            with urllib.request.urlopen(request) as response:
                # Use UTF-8 decoding with replace error handler to handle unknown chars
                content = response.read().decode('utf-8', errors='replace')
                
            # Process and clean the wordlist
            valid_words = set()
            for line in content.splitlines():
                # Skip empty lines, comments, and flags
                if not line or line.startswith('#') or '/' in line:
                    continue
                
                # Normalize the word
                if len(line.strip()) > 1:
                    normalized_word = self._normalize_word(line.strip())
                    # Only add words that contain valid Estonian characters
                    if not any(c == '?' for c in normalized_word):  # Skip words with replacement chars
                        valid_words.add(normalized_word)
                        # Log some example words with special characters for debugging
                        if any(c in normalized_word for c in 'šžõäöü'):
                            self.logger.debug(f"Added word with special chars: {normalized_word}")

            # Save processed wordlist
            with open(self.LOCAL_FILENAME, 'w', encoding='utf-8') as f:
                f.write('\n'.join(sorted(valid_words)))
            
            self.logger.info(f"Successfully downloaded and processed {len(valid_words)} words")
            return True
            
        except Exception as e:
            self.logger.error(f"Error downloading wordlist: {e}")
            return False

    def _create_test_wordlist(self):
        """Create a small test wordlist with common Estonian words."""
        self.logger.warning("Creating test wordlist as fallback")
        test_words = [
            # Basic words
            "tere", "maja", "kool", "raamat", "õpik",
            "päike", "öö", "ülikool", "šokolaad", "žetoon",
            "auto", "puu", "laud", "tool", "arvuti",
            "telefon", "raamatukogu", "õpilane", "õpetaja",
            "täna", "homme", "eile", "sõber", "pere",
            "kodu", "töö", "aed", "tänav", "linn",
            
            # Words with special characters
            "garaaž", "šampoon", "želee", "šokolaad",
            "mõõk", "jäätis", "köök", "süüa", "õun",
            "päev", "öökull", "ära", "üles", "šeff",
            
            # Common Estonian words
            "tänav", "mägi", "järv", "meri", "saar",
            "küla", "põld", "mets", "jõgi", "org",
            "käsi", "jalg", "pea", "silm", "nina",
            "suu", "kõrv", "süda", "veri", "luu",
            
            # More words with special characters
            "žürii", "šašlõkk", "džungel", "võõras",
            "mälu", "täht", "õhk", "öine", "ümbrik",
            "šokk", "žanr", "õnn", "ääres", "öö",
            
            # Compound words
            "raudtee", "käsipuu", "õunapuu", "jõulupuu",
            "täiskuu", "põhjamaa", "lõunamaa", "idamaa",
            "läänekülg", "põhjakaar", "lõunasöök"
        ]
        with open(self.LOCAL_FILENAME, 'w', encoding='utf-8') as f:
            normalized_words = sorted(set(self._normalize_word(word) for word in test_words))
            f.write('\n'.join(normalized_words))
        self.logger.info(f"Created test wordlist with {len(normalized_words)} common Estonian words")

    def _load_wordlist(self):
        """Load the Estonian wordlist from file or download it."""
        if not os.path.exists(self.LOCAL_FILENAME):
            if not self._download_wordlist():
                self._create_test_wordlist()
        
        try:
            with open(self.LOCAL_FILENAME, 'r', encoding='utf-8') as f:
                # Use normalization when loading words
                self.words = {self._normalize_word(word.strip()) for word in f}
            self.logger.info(f"Loaded {len(self.words)} words from wordlist")
            # Debug log some sample words with special characters
            sample_words = {'šokolaad', 'garaaž', 'želee', 'mõõk', 'jäätis'}
            for word in sample_words:
                normalized = self._normalize_word(word)
                self.logger.info(f"Word '{word}' (normalized: '{normalized}') {'is' if normalized in self.words else 'is not'} in wordlist")
        except Exception as e:
            self.logger.error(f"Error loading wordlist: {e}")
            self.words = set()

    def is_valid_word(self, word: str) -> bool:
        """Check if a word exists in the Estonian wordlist."""
        normalized = self._normalize_word(word)
        is_valid = normalized in self.words
        self.logger.info(f"Checking word '{word}' (normalized: '{normalized}'): {is_valid}")
        return is_valid

    def get_possible_words(self, letters: str) -> list:
        """Find all possible words that can be made from given letters."""
        possible_words = []
        letters_lower = letters.lower()
        
        for word in self.words:
            # Check if word can be made from available letters
            word_chars = list(word)
            letters_available = list(letters_lower)
            can_make_word = True
            
            for char in word_chars:
                if char in letters_available:
                    letters_available.remove(char)
                else:
                    can_make_word = False
                    break
            
            if can_make_word:
                possible_words.append(word)
        
        return possible_words 