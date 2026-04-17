import os
import urllib.request
import logging
from typing import Set

# Dictionary directory for Hunspell files
_DICT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dict")
_DIC_FILE = os.path.join(_DICT_DIR, "et_EE.dic")
_AFF_FILE = os.path.join(_DICT_DIR, "et_EE.aff")

_DIC_URL = "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/et_EE/et_EE.dic"
_AFF_URL = "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/et_EE/et_EE.aff"


class WordList:
    """Estonian word validator using Hunspell dictionary with full morphological support.

    Uses the official LibreOffice et_EE Hunspell dictionary via the spylls
    library, which understands Estonian affix rules and validates all inflected
    forms (e.g. 'õõtsuma', 'majaga') — not just dictionary stems.
    """

    def __init__(self):
        self._setup_logging()
        self._ensure_dictionary()
        self._load_dictionary()

    def _setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def _ensure_dictionary(self):
        """Download Hunspell dictionary files if not present."""
        os.makedirs(_DICT_DIR, exist_ok=True)
        for path, url in [(_DIC_FILE, _DIC_URL), (_AFF_FILE, _AFF_URL)]:
            if not os.path.exists(path):
                self.logger.info(f"Downloading {os.path.basename(path)}...")
                try:
                    urllib.request.urlretrieve(url, path)
                except Exception as e:
                    self.logger.error(f"Failed to download {url}: {e}")

    def _load_dictionary(self):
        """Load the Hunspell dictionary via spylls."""
        try:
            from spylls.hunspell import Dictionary
            dict_base = os.path.join(_DICT_DIR, "et_EE")
            self._dict = Dictionary.from_files(dict_base)
            self.logger.info("Loaded Estonian Hunspell dictionary (et_EE)")
        except Exception as e:
            self.logger.error(f"Failed to load Hunspell dictionary: {e}")
            self._dict = None

    def is_valid_word(self, word: str) -> bool:
        """Check if a word is valid Estonian using Hunspell morphological rules."""
        if self._dict is None:
            return False
        return self._dict.lookup(word.lower())
