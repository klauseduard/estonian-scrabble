"""Build the AI's DAWG from the strict Scrabble dictionary (issue #40).

Two steps, both fast enough to run automatically when the dictionary
changes (~30 s total, done once and cached in dict/):

1. Unmunch: expand every .dic stem by its suffix rules into the full
   set of playable surface forms. The strict .aff is suffix-only (no
   prefixes, no continuation flags, no compounding), so single-level
   suffix application is the complete expansion — ~10.7M words.
2. Build a DAWG (game/dawg.py) from the sorted words and marshal it
   to dict/dawg_strict.marshal (~1 MB — Estonian inflection paradigms
   share suffixes almost perfectly).

Filters mirror WordList.strict.is_valid_word: playable alphabet only,
length 2–15, no blocked words, no vowelless words.

Usage: python -m tools.build_dawg
"""

import logging
import os
import re
import time
from typing import Set

from game.dawg import Dawg
from tools.patch_dictionary import DICT_DIR, STRICT_BASE

logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCKED_FILE = os.path.join(_REPO_ROOT, "data", "blocked_words.txt")
DAWG_FILE = os.path.join(DICT_DIR, "dawg_strict.marshal")

PLAYABLE = "abdefghijklmnoprstuvzõäöüšž"
VOWELS = set("aeiouõäöü")
_WORD_RE = re.compile(f"[{PLAYABLE}]{{2,15}}$")


def _load_blocked() -> Set[str]:
    blocked = set()
    try:
        with open(BLOCKED_FILE, encoding="utf-8") as f:
            for line in f:
                word = line.split("#", 1)[0].strip()
                if word:
                    blocked.add(word.lower())
    except OSError:
        pass
    return blocked


def unmunch_strict_dictionary(dict_dir: str = DICT_DIR) -> Set[str]:
    """Expand the strict dictionary's stems × suffix rules into all forms."""
    from spylls.hunspell import Dictionary

    d = Dictionary.from_files(os.path.join(dict_dir, STRICT_BASE))

    # Group each flag's suffix rules by condition so each distinct
    # condition regex is tested once per stem, not once per subrule.
    cond_groups = {}
    for flag, suffixes in d.aff.SFX.items():
        by_cond = {}
        for sfx in suffixes:
            by_cond.setdefault(sfx.condition, []).append((sfx.strip, sfx.add))
        groups = []
        for cond, pairs in by_cond.items():
            rx = None if cond == "." else re.compile(cond.replace("-", "\\-") + "$")
            groups.append((rx, pairs))
        cond_groups[flag] = groups

    playable_set = set(PLAYABLE)
    blocked = _load_blocked()
    words: Set[str] = set()
    fullmatch = _WORD_RE.fullmatch

    for entry in d.dic.words:
        stem = entry.stem
        # The stem itself is a valid standalone word (the strict aff has
        # no NEEDAFFIX flag).
        if fullmatch(stem):
            words.add(stem)
        if not entry.flags:
            continue
        stem_clean = set(stem) <= playable_set
        for flag in entry.flags:
            groups = cond_groups.get(flag)
            if groups is None:
                continue  # inert flag (e.g. the old compound flag Z)
            for rx, pairs in groups:
                if rx is not None and rx.search(stem) is None:
                    continue
                for strip, add in pairs:
                    if strip:
                        if not stem.endswith(strip) or len(stem) <= len(strip):
                            continue  # FULLSTRIP not set: no full strip
                        form = stem[: -len(strip)] + add
                    else:
                        form = stem + add
                    if stem_clean:
                        if 2 <= len(form) <= 15:
                            words.add(form)
                    elif fullmatch(form):
                        words.add(form)

    return {w for w in words if w not in blocked and set(w) & VOWELS}


def build_dawg(dict_dir: str = DICT_DIR) -> str:
    """Unmunch + build + save the DAWG. Returns the output path."""
    t0 = time.monotonic()
    words = unmunch_strict_dictionary(dict_dir)
    t1 = time.monotonic()
    dawg = Dawg.build(iter(sorted(words)))
    out = os.path.join(dict_dir, "dawg_strict.marshal")
    dawg.save(out)
    logger.info(
        "DAWG built: %d words -> %d nodes, %.1f MB, unmunch %.0fs + build %.0fs",
        len(words), len(dawg), os.path.getsize(out) / 1e6,
        t1 - t0, time.monotonic() - t1,
    )
    return out


def dawg_stale(dict_dir: str = DICT_DIR) -> bool:
    """Whether the DAWG is missing or older than its inputs."""
    out = os.path.join(dict_dir, "dawg_strict.marshal")
    if not os.path.exists(out):
        return True
    built = os.path.getmtime(out)
    sources = [
        os.path.join(dict_dir, STRICT_BASE + ".dic"),
        os.path.join(dict_dir, STRICT_BASE + ".aff"),
        BLOCKED_FILE,
        os.path.abspath(__file__),
    ]
    return any(os.path.exists(s) and os.path.getmtime(s) > built for s in sources)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    build_dawg()
