"""DAWG — Directed Acyclic Word Graph — for instant dictionary traversal.

A DAWG is a trie with all shared suffixes merged: "majale" and "ojale"
share their "…jale" tail as one path. Estonian's regular inflection
paradigms compress spectacularly — the ~10.7 million surface forms of
the strict dictionary collapse to ~27k nodes (≈1 MB serialized).

Built with the incremental algorithm of Daciuk et al. (2000), which
requires lexicographically sorted input. The finished automaton is
flattened to parallel lists (``finals``: is-a-word flag per node,
``edges``: char -> node-index dict per node) for fast traversal and
compact marshal serialization.

Used by the AI move generator (game/ai_player.py, issue #40): walking
the DAWG *is* the dictionary check, so only letter sequences that can
still become words are ever explored.
"""

import marshal
from typing import Dict, Iterable, List, Tuple


class _BuildNode:
    __slots__ = ("edges", "final")

    def __init__(self):
        self.edges: Dict[str, "_BuildNode"] = {}
        self.final = False

    def key(self):
        # Children are already minimized (registered), so identity works.
        return (self.final, tuple((ch, id(n)) for ch, n in self.edges.items()))


class Dawg:
    """Flattened DAWG: finals[i] is terminality, edges[i] maps char -> node index."""

    def __init__(self, finals: List[bool], edges: List[Dict[str, int]]):
        self.finals = finals
        self.edges = edges
        self.root = 0

    # -- membership ---------------------------------------------------------

    def is_word(self, word: str) -> bool:
        node = 0
        edges = self.edges
        for ch in word:
            node = edges[node].get(ch)
            if node is None:
                return False
        return self.finals[node]

    # -- construction -------------------------------------------------------

    @classmethod
    def build(cls, sorted_words: Iterable[str]) -> "Dawg":
        """Build from lexicographically sorted words (Daciuk et al.)."""
        root = _BuildNode()
        register: Dict[tuple, _BuildNode] = {}
        # unchecked: (parent, char, child) path of the previous word not yet minimized
        unchecked: List[Tuple[_BuildNode, str, _BuildNode]] = []
        previous = ""

        def minimize(down_to: int):
            for _ in range(len(unchecked) - down_to):
                parent, ch, child = unchecked.pop()
                key = child.key()
                existing = register.get(key)
                if existing is not None:
                    parent.edges[ch] = existing
                else:
                    register[key] = child

        for word in sorted_words:
            word = word.rstrip("\n")
            if not word:
                continue
            if word <= previous and previous:
                raise ValueError(f"input not sorted: {previous!r} >= {word!r}")
            # common prefix with previous word
            cp = 0
            maxcp = min(len(word), len(previous))
            while cp < maxcp and word[cp] == previous[cp]:
                cp += 1
            minimize(cp)
            node = unchecked[-1][2] if unchecked else root
            for ch in word[cp:]:
                nxt = _BuildNode()
                node.edges[ch] = nxt
                unchecked.append((node, ch, nxt))
                node = nxt
            node.final = True
            previous = word

        minimize(0)

        # Flatten to parallel lists (BFS numbering, root = 0)
        index: Dict[int, int] = {id(root): 0}
        order = [root]
        for node in order:  # grows while iterating
            for child in node.edges.values():
                if id(child) not in index:
                    index[id(child)] = len(order)
                    order.append(child)
        finals = [n.final for n in order]
        edges = [{ch: index[id(c)] for ch, c in n.edges.items()} for n in order]
        return cls(finals, edges)

    # -- serialization ------------------------------------------------------

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            marshal.dump((self.finals, self.edges), f)

    @classmethod
    def load(cls, path: str) -> "Dawg":
        with open(path, "rb") as f:
            finals, edges = marshal.load(f)
        return cls(finals, edges)

    def __len__(self):
        return len(self.finals)
