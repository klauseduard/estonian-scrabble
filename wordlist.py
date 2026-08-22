import logging
import os
import urllib.request
from typing import Set

from tools.patch_dictionary import (
    DICT_DIR as _DICT_DIR,
)
from tools.patch_dictionary import (
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


def _is_valid(dictionary, blocked: Set[str], word: str) -> bool:
    """The shared validation rule: blocklist, vowelless guard, Hunspell lookup.

    Both word lists apply exactly this. Stated once so the two cannot drift.
    """
    word = word.lower()
    if word in blocked:
        return False
    # No real Estonian word is vowelless; Hunspell would accept
    # abbreviations like 'tk' or 'lk' here.
    if not set(word) & _VOWELS:
        return False
    return dictionary.lookup(word)


class DictionaryUnavailableError(RuntimeError):
    """Raised when a word list cannot load the dictionary it validates against.

    Deliberately fatal. The alternative — carrying on with no dictionary — makes
    every word invalid, which a player cannot tell apart from a correctly
    rejected word.
    """


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
        try:
            from tools.build_dawg import build_dawg, dawg_stale

            if dawg_stale():
                self.logger.info("Building AI move-generation DAWG (~30 s, cached)...")
                build_dawg()
        except Exception as e:
            # The AI falls back to brute-force generation without a DAWG
            self.logger.error(f"Failed to build DAWG: {e}")

    def _load_dictionary(self):
        """Load the patched Hunspell dictionary via spylls.

        Raises DictionaryUnavailableError if it cannot be loaded: a validator
        with no dictionary would call every word invalid, which is worse than
        not starting at all.
        """
        dict_base = os.path.join(_DICT_DIR, "et_EE_scrabble")
        if not os.path.exists(dict_base + ".dic"):
            # Patching failed — fall back to the unpatched dictionary. This one
            # is a real fallback: upstream still validates Estonian correctly,
            # it is just more permissive about compounds.
            dict_base = os.path.join(_DICT_DIR, "et_EE")
            self.logger.warning("Patched dictionary missing, using upstream et_EE")
        try:
            from spylls.hunspell import Dictionary

            self._dict = Dictionary.from_files(dict_base)
        except Exception as e:
            raise DictionaryUnavailableError(
                f"Could not load the Estonian dictionary from {dict_base!r}: {e}"
            ) from e
        self.logger.info(f"Loaded Estonian Hunspell dictionary ({os.path.basename(dict_base)})")

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
        return _is_valid(self._dict, self._blocked, word)

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
        self._dawg = None
        self._dawg_loaded = False
        strict_base = os.path.join(_DICT_DIR, "et_EE_scrabble_strict")
        try:
            from spylls.hunspell import Dictionary

            self._dict = Dictionary.from_files(strict_base)
        except Exception as e:
            raise DictionaryUnavailableError(
                f"Could not load the strict Estonian dictionary from {strict_base!r}: {e}"
            ) from e
        self.logger.info("Loaded strict Estonian dictionary (et_EE_scrabble_strict)")

    @property
    def dawg(self):
        """DAWG over all strict-dictionary forms, for AI move generation.

        Lazy-loaded (~1 MB marshal). None if unavailable — the AI then
        falls back to brute-force generation.
        """
        if not self._dawg_loaded:
            self._dawg_loaded = True
            try:
                from game.dawg import Dawg
                from tools.build_dawg import DAWG_FILE

                self._dawg = Dawg.load(DAWG_FILE)
                self.logger.info(f"Loaded move-generation DAWG ({len(self._dawg)} nodes)")
            except Exception as e:
                self.logger.error(f"Failed to load DAWG: {e}")
                self._dawg = None
        return self._dawg

    def is_valid_word(self, word: str) -> bool:
        """Check a word against the strict (no-compound) dictionary."""
        return _is_valid(self._dict, self._blocked, word)
