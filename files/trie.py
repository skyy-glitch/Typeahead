"""
trie.py — Core Trie data structure for O(k) prefix search.

A Trie (prefix tree) stores strings character-by-character.
Each node represents one character; walking k characters finds
all words sharing that prefix in O(k) time, regardless of
how many total entries exist.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TrieNode:
    """
    One node in the Trie — one character in the alphabet.

    Attributes:
        children  : map of char -> child TrieNode
        is_end    : True if this node completes a valid word
        data      : arbitrary payload stored at word-end nodes
                    (e.g. {"city": "Mumbai", "state": "Maharashtra"})
        frequency : how often this entry was inserted (for ranking)
    """
    children: dict[str, "TrieNode"] = field(default_factory=dict)
    is_end: bool = False
    data: Optional[dict] = None
    frequency: int = 0


class Trie:
    """
    Trie with:
      • insert(word, data)          — O(k)
      • search_prefix(prefix, n)    — O(k + results)
      • exact_match(word)           — O(k)
      • delete(word)                — O(k)
      • autocomplete(prefix, n)     — alias for search_prefix
      • __len__                     — total words inserted
      • node_count property         — total nodes in the trie
    """

    def __init__(self) -> None:
        self._root = TrieNode()
        self._word_count = 0
        self._node_count = 1          # root counts as one node

    # ------------------------------------------------------------------ #
    #  INSERT                                                              #
    # ------------------------------------------------------------------ #

    def insert(self, word: str, data: Optional[dict] = None) -> None:
        """
        Insert *word* into the trie, storing optional *data* at the leaf.
        Case-insensitive: words are stored lowercased.

        Time  : O(k)   where k = len(word)
        Space : O(k)   in the worst case (no shared prefix)
        """
        node = self._root
        for ch in word.lower():
            if ch not in node.children:
                node.children[ch] = TrieNode()
                self._node_count += 1
            node = node.children[ch]

        if not node.is_end:
            self._word_count += 1
        node.is_end = True
        node.frequency += 1
        node.data = data or {"word": word}

    # ------------------------------------------------------------------ #
    #  EXACT MATCH                                                         #
    # ------------------------------------------------------------------ #

    def exact_match(self, word: str) -> Optional[dict]:
        """
        Return the stored data for *word* if it exists, else None.

        Time: O(k)
        """
        node = self._find_node(word)
        if node and node.is_end:
            return node.data
        return None

    # ------------------------------------------------------------------ #
    #  PREFIX SEARCH  (the typeahead core)                                 #
    # ------------------------------------------------------------------ #

    def search_prefix(self, prefix: str, limit: int = 10) -> list[dict]:
        """
        Return up to *limit* entries whose key starts with *prefix*.

        Algorithm:
          1. Walk the trie character-by-character along *prefix*  → O(k)
          2. DFS from that node collecting all is_end descendants → O(results)

        Total: O(k + results)  — completely independent of dataset size.

        Returns list of data dicts, sorted by frequency descending.
        """
        node = self._find_node(prefix)
        if node is None:
            return []

        results: list[dict] = []
        self._dfs_collect(node, results)

        # sort by frequency so popular cities surface first
        results.sort(key=lambda d: d.get("_freq", 0), reverse=True)
        return results[:limit]

    # Alias used in the demo
    autocomplete = search_prefix

    # ------------------------------------------------------------------ #
    #  DELETE                                                              #
    # ------------------------------------------------------------------ #

    def delete(self, word: str) -> bool:
        """
        Remove *word* from the trie.
        Prunes now-empty nodes to reclaim memory.

        Returns True if the word existed and was removed.
        Time: O(k)
        """
        path: list[tuple[TrieNode, str]] = []   # (parent, char) pairs
        node = self._root

        for ch in word.lower():
            if ch not in node.children:
                return False
            path.append((node, ch))
            node = node.children[ch]

        if not node.is_end:
            return False

        node.is_end = False
        node.data = None
        self._word_count -= 1

        # prune leaf nodes that are no longer needed
        for parent, ch in reversed(path):
            child = parent.children[ch]
            if not child.children and not child.is_end:
                del parent.children[ch]
                self._node_count -= 1
            else:
                break

        return True

    # ------------------------------------------------------------------ #
    #  PROPERTIES                                                          #
    # ------------------------------------------------------------------ #

    @property
    def node_count(self) -> int:
        return self._node_count

    def __len__(self) -> int:
        return self._word_count

    def __repr__(self) -> str:
        return (f"Trie(words={self._word_count}, "
                f"nodes={self._node_count})")

    # ------------------------------------------------------------------ #
    #  PRIVATE HELPERS                                                     #
    # ------------------------------------------------------------------ #

    def _find_node(self, prefix: str) -> Optional[TrieNode]:
        """Walk the trie along *prefix*, return the last node or None."""
        node = self._root
        for ch in prefix.lower():
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node

    def _dfs_collect(self, node: TrieNode, results: list[dict]) -> None:
        """DFS from *node*, appending data of every is_end node found."""
        if node.is_end and node.data:
            entry = dict(node.data)
            entry["_freq"] = node.frequency
            results.append(entry)
        for child in node.children.values():
            self._dfs_collect(child, results)
