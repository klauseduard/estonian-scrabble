import os
import urllib.request
import logging
from typing import Set
import unicodedata

class WordList:
    # Raw content URL from GitHub (change 'blob' to 'raw')
    WORDLIST_URL = "https://raw.githubusercontent.com/titoBouzout/Dictionaries/master/Estonian.dic"
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
        # Convert to lowercase and apply NFKC normalization
        return unicodedata.normalize('NFKC', word.lower())

    def _download_wordlist(self) -> bool:
        """Download the Estonian wordlist from GitHub."""
        self.logger.info("Downloading Estonian wordlist from GitHub...")
        try:
            with urllib.request.urlopen(self.WORDLIST_URL) as response:
                content = response.read().decode('utf-8', errors='ignore')
                
            # Process and clean the wordlist
            valid_words = set()
            for line in content.splitlines():
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                    
                # Words in the file are in format "word/flags"
                word = line.split('/')[0].strip().lower()
                
                # Skip single letters
                if len(word) > 1:
                    valid_words.add(word)

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
            "tere", "maja", "kool", "raamat", "õpik",
            "päike", "öö", "ülikool", "šokolaad", "žetoon",
            "auto", "puu", "laud", "tool", "arvuti",
            "telefon", "raamatukogu", "õpilane", "õpetaja",
            "täna", "homme", "eile", "sõber", "pere",
            "kodu", "töö", "aed", "tänav", "linn"
        ]
        with open(self.LOCAL_FILENAME, 'w', encoding='utf-8') as f:
            f.write('\n'.join(test_words))
        self.logger.info("Created test wordlist with common Estonian words")

    def _load_wordlist(self):
        """Load the Estonian wordlist from file or download it."""
        if not os.path.exists(self.LOCAL_FILENAME):
            if not self._download_wordlist():
                self._create_test_wordlist()
        
        try:
            with open(self.LOCAL_FILENAME, 'r', encoding='utf-8') as f:
                self.words = {word.strip().lower() for word in f}  # Removed normalization here
            self.logger.info(f"Loaded {len(self.words)} words from wordlist")
            # Debug log some sample words
            sample_words = {'loov', 'voli', 'mört', 'õpik', 'tere'}
            for word in sample_words:
                self.logger.info(f"Word '{word}' {'is' if word in self.words else 'is not'} in wordlist")
        except Exception as e:
            self.logger.error(f"Error loading wordlist: {e}")
            self.words = set()

    def is_valid_word(self, word: str) -> bool:
        """Check if a word exists in the Estonian wordlist."""
        word_lower = word.lower()
        is_valid = word_lower in self.words
        self.logger.info(f"Checking word '{word}' (lowercased: '{word_lower}'): {is_valid}")
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