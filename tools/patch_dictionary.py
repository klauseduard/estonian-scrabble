"""Patch the upstream et_EE Hunspell dictionary for Scrabble use.

The upstream LibreOffice dictionary assigns its compound flag (``Z``) to
~118 abbreviation entries (tk, lk, nt, TV, GB, ...). For spell-checking
prose that is fine, but for Scrabble it lets garbage compounds like
"tköis" (= tk + öis) validate. See GitHub issue #32.

No real Estonian word is vowelless, so the patch strips the compound
flag from vowelless roots. Real words that were only reachable through
such garbage parses (e.g. "maantee", accepted upstream only as
maa + nt + ee) are re-added from ``data/extra_words.txt`` by cloning
the dictionary entries of a model word they inflect like.

The et_EE dictionary stores noun paradigms as principal-part entries —
lemma, lemma+"d", lemma+"ga" — and derives all other case forms from
the -ga entry via suffix rules keyed on the "ga" ending. Cloning those
three anchors for an extra word therefore yields its full paradigm.

Usage: python -m tools.patch_dictionary
"""

import logging
import os
import shutil
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_VOWELS = set("aeiouõäöüAEIOUÕÄÖÜ")

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_DIR = os.path.join(_REPO_ROOT, "dict")
EXTRA_WORDS_FILE = os.path.join(_REPO_ROOT, "data", "extra_words.txt")
BLOCKED_STEMS_FILE = os.path.join(_REPO_ROOT, "data", "blocked_stems.txt")

SOURCE_BASE = "et_EE"
PATCHED_BASE = "et_EE_scrabble"
STRICT_BASE = "et_EE_scrabble_strict"


def _read_aff_directive(aff_path: str, directive: str, encoding: str) -> Optional[str]:
    """Return the value of a directive (e.g. COMPOUNDFLAG) from an .aff file."""
    with open(aff_path, encoding=encoding) as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2 and parts[0] == directive:
                return parts[1]
    return None


def _read_encoding(aff_path: str) -> str:
    """Read the SET directive; Hunspell .aff files declare their own encoding."""
    with open(aff_path, encoding="ascii", errors="ignore") as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2 and parts[0] == "SET":
                return parts[1]
    return "UTF-8"


def _split_entry(line: str) -> tuple:
    """Split a .dic entry into (root, flags, rest). rest is tab-separated data."""
    body, tab, rest = line.partition("\t")
    root, slash, flags = body.partition("/")
    return root, flags if slash else None, (tab + rest) if tab else ""


def _load_blocked_stems(path: str = BLOCKED_STEMS_FILE) -> set:
    """Dictionary entries to drop entirely (bogus paradigm anchors)."""
    stems = set()
    if not os.path.exists(path):
        return stems
    with open(path, encoding="utf-8") as f:
        for line in f:
            stem = line.split("#", 1)[0].strip()
            if stem:
                stems.add(stem)
    return stems


def _load_extra_words(path: str) -> List[tuple]:
    """Parse extra_words.txt: lines of "WORD" or "WORD MODEL", # comments allowed."""
    entries = []
    if not os.path.exists(path):
        return entries
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            entries.append((parts[0], parts[1] if len(parts) > 1 else None))
    return entries


def patch_dictionary(
    dict_dir: str = DICT_DIR, extra_words_file: str = EXTRA_WORDS_FILE
) -> str:
    """Build <dict_dir>/et_EE_scrabble.{dic,aff} from the upstream files.

    Returns the base path (without extension) of the patched dictionary.
    """
    src_dic = os.path.join(dict_dir, SOURCE_BASE + ".dic")
    src_aff = os.path.join(dict_dir, SOURCE_BASE + ".aff")
    out_dic = os.path.join(dict_dir, PATCHED_BASE + ".dic")
    out_aff = os.path.join(dict_dir, PATCHED_BASE + ".aff")

    encoding = _read_encoding(src_aff)
    compound_flag = _read_aff_directive(src_aff, "COMPOUNDFLAG", encoding)
    if compound_flag is None:
        raise ValueError(f"No COMPOUNDFLAG directive in {src_aff}")

    with open(src_dic, encoding=encoding) as f:
        lines = f.read().splitlines()

    blocked_stems = _load_blocked_stems()

    # First line is the entry count; patch the rest.
    entries: List[str] = []
    entry_by_root: Dict[str, tuple] = {}
    stripped = 0
    removed = 0
    for line in lines[1:]:
        if not line:
            continue
        root, flags, rest = _split_entry(line)
        if root in blocked_stems:
            removed += 1
            continue
        if flags and compound_flag in flags and not (set(root) & _VOWELS):
            flags = flags.replace(compound_flag, "")
            stripped += 1
        if root not in entry_by_root:
            entry_by_root[root] = (flags, rest)
        entries.append(root + (f"/{flags}" if flags else "") + rest)

    # Principal-part endings of a noun paradigm in the et_EE data (see
    # module docstring): the -ga entry is the anchor for all case forms.
    paradigm_endings = ("", "d", "ga")
    added = 0
    for word, model in _load_extra_words(extra_words_file):
        if model is None:
            entries.append(word)
            added += 1
            continue
        if model not in entry_by_root:
            logger.warning("extra_words: model %r for %r not found in .dic", model, word)
            entries.append(word)
            added += 1
            continue
        for ending in paradigm_endings:
            entry = entry_by_root.get(model + ending)
            if entry is None:
                continue
            flags, rest = entry
            entries.append(word + ending + (f"/{flags}" if flags else "") + rest)
            added += 1

    with open(out_dic, "w", encoding=encoding) as f:
        f.write(f"{len(entries)}\n")
        f.write("\n".join(entries) + "\n")
    shutil.copyfile(src_aff, out_aff)

    # Strict variant for AI move validation: same entries, compounding
    # disabled. Hunspell compounding over-generates (any compound-flagged
    # words may concatenate) — tolerable for human play backed by the
    # challenge system, fatal for brute-force move generation (issue #33).
    strict_dic = os.path.join(dict_dir, STRICT_BASE + ".dic")
    strict_aff = os.path.join(dict_dir, STRICT_BASE + ".aff")
    with open(src_aff, encoding=encoding) as f:
        aff_lines = [
            line for line in f.read().splitlines()
            if not line.startswith("COMPOUND")
        ]
    with open(strict_aff, "w", encoding=encoding) as f:
        f.write("\n".join(aff_lines) + "\n")
    shutil.copyfile(out_dic, strict_dic)

    logger.info(
        "Patched dictionary written to %s (compound flag stripped from %d "
        "vowelless entries, %d blocked stems removed, %d extra-word entries "
        "appended); strict no-compound variant written to %s",
        out_dic, stripped, removed, added, strict_dic,
    )
    return os.path.join(dict_dir, PATCHED_BASE)


def patched_dictionary_stale(
    dict_dir: str = DICT_DIR, extra_words_file: str = EXTRA_WORDS_FILE
) -> bool:
    """Whether the patched dictionary is missing or older than its inputs."""
    outputs = [
        os.path.join(dict_dir, base + ext)
        for base in (PATCHED_BASE, STRICT_BASE)
        for ext in (".dic", ".aff")
    ]
    if not all(os.path.exists(p) for p in outputs):
        return True
    built = min(os.path.getmtime(p) for p in outputs)
    sources = [
        os.path.join(dict_dir, SOURCE_BASE + ".dic"),
        os.path.join(dict_dir, SOURCE_BASE + ".aff"),
        extra_words_file,
        BLOCKED_STEMS_FILE,
        os.path.abspath(__file__),
    ]
    return any(os.path.exists(s) and os.path.getmtime(s) > built for s in sources)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    patch_dictionary()
