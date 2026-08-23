"""Regenerate every measured figure quoted in docs/algorithms.md.

Run with `python -m tools.algorithm_figures`. The document is meant to stay
true to the artifacts in dict/, so when the dictionary or the DAWG changes,
run this and update the numbers rather than trusting the prose.
"""

import logging
import os
import sys
import time

from game.dawg import Dawg


def main() -> None:
    logging.disable(logging.CRITICAL)
    from tools.build_dawg import DAWG_FILE, unmunch_strict_dictionary

    print("== DAWG ==")
    dawg = Dawg.load(DAWG_FILE)
    edges = sum(len(e) for e in dawg.edges)
    size = os.path.getsize(DAWG_FILE)
    print(f"  nodes             {len(dawg):,}")
    print(f"  edges             {edges:,}")
    print(f"  word-ending nodes {sum(dawg.finals):,}")
    print(f"  serialized        {size / 1024:.0f} KB")

    start = time.perf_counter()
    for _ in range(200_000):
        dawg.is_word("majale")
    elapsed = time.perf_counter() - start
    print(f"  is_word           {elapsed / 200_000 * 1e6:.2f} us")

    print("\n== toy example ==")
    words = sorted(["maja", "majad", "majale", "oja", "ojad", "ojale"])
    toy = Dawg.build(words)
    prefixes = {w[:i] for w in words for i in range(1, len(w) + 1)}
    print(f"  trie nodes        {len(prefixes) + 1}")
    print(f"  DAWG nodes        {len(toy)}")
    for i, (final, edge) in enumerate(zip(toy.finals, toy.edges)):
        print(f"    {i}  {'*' if final else ' '}  {dict(edge)}")

    print("\n== Hunspell source dictionary ==")
    from tools.patch_dictionary import DICT_DIR

    dic = os.path.join(DICT_DIR, "et_EE.dic")
    aff = os.path.join(DICT_DIR, "et_EE.aff")
    if os.path.exists(dic) and os.path.exists(aff):
        with open(dic, encoding="iso-8859-15") as handle:
            stems = sum(1 for _ in handle) - 1  # first line is the entry count
        with open(aff, encoding="iso-8859-15") as handle:
            sfx = [line.split() for line in handle if line.startswith("SFX")]
        groups = sum(1 for parts in sfx if len(parts) == 4)
        print(f"  stem entries      {stems:,}")
        print(f"  suffix groups     {groups}")
        print(f"  suffix rules      {len(sfx) - groups:,}")
    else:
        print("  (dictionary not downloaded yet)")

    if "--full" in sys.argv:
        print("\n== unmunch (slow) ==")
        forms = unmunch_strict_dictionary()
        raw = sum(len(w.encode()) + 1 for w in forms)
        print(f"  surface forms     {len(forms):,}")
        print(f"  as plain text     {raw / 1024 / 1024:.1f} MB")
        print(f"  compression       {raw / size:.0f}x")


if __name__ == "__main__":
    main()
