import os
import urllib.request
import logging
from typing import Set
import unicodedata

class WordList:
    # Estonian dictionary from titoBouzout's collection
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
        # Just convert to lowercase as the special characters are already handled
        return word.lower()

    def _download_wordlist(self) -> bool:
        """Download the Estonian wordlist."""
        self.logger.info("Downloading Estonian wordlist...")
        try:
            with urllib.request.urlopen(self.WORDLIST_URL) as response:
                # Read raw bytes first
                content_bytes = response.read()
                
                # Replace the specific UTF-8 sequences before decoding
                content_bytes = content_bytes.replace(b'\xc2\xa8', 'š'.encode('utf-8'))
                content_bytes = content_bytes.replace(b'\xc2\xb8', 'ž'.encode('utf-8'))
                
                # Now decode with the replacements
                content = content_bytes.decode('utf-8')
                
            # Process and clean the wordlist
            valid_words = set()
            for line in content.splitlines():
                # Skip empty lines
                if not line:
                    continue
                
                # Extract the word (before any flags)
                word = line.split('/')[0].strip()
                
                # Only process words of reasonable length
                if 1 < len(word) < 30:
                    normalized_word = self._normalize_word(word)
                    # Skip words with replacement characters
                    if not any(c == '?' for c in normalized_word):
                        valid_words.add(normalized_word)

            # Save processed wordlist
            with open(self.LOCAL_FILENAME, 'w', encoding='utf-8') as f:
                f.write('\n'.join(sorted(valid_words)))
            
            self.logger.info(f"Successfully downloaded and processed {len(valid_words)} words")
            return True
            
        except Exception as e:
            self.logger.error(f"Error downloading wordlist: {e}")
            return False

    def _create_test_wordlist(self):
        """Create a test wordlist as fallback."""
        self.logger.warning("Creating test wordlist as fallback")
        test_words = [
            "tere", "maja", "kool", "garaaž", "šokolaad",
            "žürii", "mõõk", "jäätis", "köök", "süüa",
            "õun", "päev", "öökull", "ära", "üles"
        ]
        with open(self.LOCAL_FILENAME, 'w', encoding='utf-8') as f:
            normalized_words = sorted(set(self._normalize_word(word) for word in test_words))
            f.write('\n'.join(normalized_words))
        self.logger.info(f"Created test wordlist with {len(normalized_words)} words")

    def _load_wordlist(self):
        """Load the Estonian wordlist from file or download it."""
        if not os.path.exists(self.LOCAL_FILENAME):
            if not self._download_wordlist():
                self._create_test_wordlist()
        
        try:
            with open(self.LOCAL_FILENAME, 'r', encoding='utf-8') as f:
                self.words = {self._normalize_word(word.strip()) for word in f}
            self.logger.info(f"Loaded {len(self.words)} words from wordlist")
            
            # Log some sample words for verification
            sample_words = {'šokolaad', 'garaaž', 'žürii', 'mõõk', 'jäätis'}
            for word in sample_words:
                normalized = self._normalize_word(word)
                if normalized in self.words:
                    self.logger.debug(f"Found word: {word} (normalized: {normalized})")
        except Exception as e:
            self.logger.error(f"Error loading wordlist: {e}")
            self.words = set()

    def is_valid_word(self, word: str) -> bool:
        """Check if a word exists in the Estonian wordlist."""
        normalized = self._normalize_word(word)
        return normalized in self.words

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