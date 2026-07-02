import logging
import os
import urllib.request
from typing import Set

from tools.patch_dictionary import (
    DICT_DIR as _DICT_DIR,
    patch_dictionary,
    patched_dictionary_stale,
)

_DIC_FILE = os.path.join(_DICT_DIR, "et_EE.dic")
_AFF_FILE = os.path.join(_DICT_DIR, "et_EE.aff")

_DIC_URL = "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/et_EE/et_EE.dic"
_AFF_URL = "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/et_EE/et_EE.aff"

_BLOCKED_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "blocked_words.txt"
)

_VOWELS = set("aeiouõäöü")


class WordList:
    """Estonian word validator using Hunspell dictionary with full morphological support.

    Uses the official LibreOffice et_EE Hunspell dictionary via the spylls
    library, which understands Estonian affix rules and validates all inflected
    forms (e.g. 'õõtsuma', 'majaga') — not just dictionary stems.

    The dictionary is patched for Scrabble use (see tools/patch_dictionary.py):
    the upstream data lets abbreviations act as compound parts, which accepts
    garbage like 'tköis' (= tk + öis). On top of that, words listed in
    data/blocked_words.txt and vowelless words are always rejected.
    """

    def __init__(self):
        self._setup_logging()
        self._ensure_dictionary()
        self._load_dictionary()
        self._blocked = self._load_blocked_words()
        self._strict = None

    def _setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def _ensure_dictionary(self):
        """Download Hunspell dictionary files if not present, then patch them."""
        os.makedirs(_DICT_DIR, exist_ok=True)
        for path, url in [(_DIC_FILE, _DIC_URL), (_AFF_FILE, _AFF_URL)]:
            if not os.path.exists(path):
                self.logger.info(f"Downloading {os.path.basename(path)}...")
                try:
                    urllib.request.urlretrieve(url, path)
                except Exception as e:
                    self.logger.error(f"Failed to download {url}: {e}")
        try:
            if patched_dictionary_stale():
                self.logger.info("Building Scrabble-patched dictionary...")
                patch_dictionary()
        except Exception as e:
            self.logger.error(f"Failed to patch dictionary: {e}")

    def _load_dictionary(self):
        """Load the patched Hunspell dictionary via spylls."""
        try:
            from spylls.hunspell import Dictionary

            dict_base = os.path.join(_DICT_DIR, "et_EE_scrabble")
            if not os.path.exists(dict_base + ".dic"):
                # Patching failed — fall back to the unpatched dictionary
                dict_base = os.path.join(_DICT_DIR, "et_EE")
                self.logger.warning("Patched dictionary missing, using upstream et_EE")
            self._dict = Dictionary.from_files(dict_base)
            self.logger.info(f"Loaded Estonian Hunspell dictionary ({os.path.basename(dict_base)})")
        except Exception as e:
            self.logger.error(f"Failed to load Hunspell dictionary: {e}")
            self._dict = None

    def _load_blocked_words(self) -> Set[str]:
        """Load the Scrabble blocklist (words Hunspell wrongly accepts)."""
        blocked: Set[str] = set()
        try:
            with open(_BLOCKED_FILE, encoding="utf-8") as f:
                for line in f:
                    word = line.split("#", 1)[0].strip()
                    if word:
                        blocked.add(word.lower())
        except OSError as e:
            self.logger.warning(f"Could not read blocklist {_BLOCKED_FILE}: {e}")
        return blocked

    def is_valid_word(self, word: str) -> bool:
        """Check if a word is valid Estonian using Hunspell morphological rules."""
        if self._dict is None:
            return False
        word = word.lower()
        if word in self._blocked:
            return False
        # No real Estonian word is vowelless; Hunspell would accept
        # abbreviations like 'tk' or 'lk' here.
        if not set(word) & _VOWELS:
            return False
        return self._dict.lookup(word)

    @property
    def strict(self) -> "StrictWordList":
        """Strict validator for AI move generation (compounding disabled).

        Hunspell compounding lets any compound-flagged words concatenate,
        which brute-force move search exploits to find garbage a human
        never would (issue #33). The strict dictionary rejects all
        compounds: false negatives are harmless for the AI, false
        positives are fatal.
        """
        if self._strict is None:
            self._strict = StrictWordList(self._blocked, self.logger)
        return self._strict


class StrictWordList:
    """Word validator over the no-compound dictionary variant.

    Shares the blocklist and vowelless guard with :class:`WordList`.
    Used for AI candidate validation only — humans are validated with
    the permissive dictionary plus the challenge system.
    """

    def __init__(self, blocked: Set[str], logger: logging.Logger):
        self._blocked = blocked
        self.logger = logger
        try:
            from spylls.hunspell import Dictionary

            self._dict = Dictionary.from_files(
                os.path.join(_DICT_DIR, "et_EE_scrabble_strict")
            )
            self.logger.info("Loaded strict Estonian dictionary (et_EE_scrabble_strict)")
        except Exception as e:
            self.logger.error(f"Failed to load strict dictionary: {e}")
            self._dict = None

    def is_valid_word(self, word: str) -> bool:
        """Check a word against the strict (no-compound) dictionary."""
        if self._dict is None:
            return False
        word = word.lower()
        if word in self._blocked:
            return False
        if not set(word) & _VOWELS:
            return False
        return self._dict.lookup(word)
