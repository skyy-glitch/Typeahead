"""
test_trie.py — Unit tests for Trie and TypeaheadEngine.

Run:
    python -m pytest test_trie.py -v
  or just:
    python test_trie.py
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from trie import Trie, TrieNode
from typeahead import TypeaheadEngine


# ══════════════════════════════════════════════════════════════════════ #
#  Trie unit tests                                                       #
# ══════════════════════════════════════════════════════════════════════ #

class TestTrieNode:
    def test_default_state(self):
        node = TrieNode()
        assert node.children == {}
        assert node.is_end is False
        assert node.data is None
        assert node.frequency == 0


class TestTrieInsertAndExact:
    def setup_method(self):
        self.t = Trie()

    def test_insert_single_word(self):
        self.t.insert("mumbai", {"city": "Mumbai"})
        assert len(self.t) == 1

    def test_exact_match_found(self):
        self.t.insert("delhi", {"city": "Delhi"})
        result = self.t.exact_match("delhi")
        assert result is not None
        assert result["city"] == "Delhi"

    def test_exact_match_case_insensitive(self):
        self.t.insert("Pune", {"city": "Pune"})
        assert self.t.exact_match("PUNE") is not None
        assert self.t.exact_match("pune") is not None

    def test_exact_match_not_found(self):
        self.t.insert("agra", {"city": "Agra"})
        assert self.t.exact_match("agr") is None   # prefix, not full word

    def test_word_count_after_duplicates(self):
        self.t.insert("surat")
        self.t.insert("surat")     # duplicate — count stays 1
        assert len(self.t) == 1

    def test_frequency_increments(self):
        self.t.insert("kochi")
        self.t.insert("kochi")
        node = self.t._find_node("kochi")
        assert node.frequency == 2


class TestTrieSearch:
    def setup_method(self):
        self.t = Trie()
        cities = [
            ("Mumbai", {"city": "Mumbai", "state": "Maharashtra"}),
            ("Munger", {"city": "Munger", "state": "Bihar"}),
            ("Mysuru", {"city": "Mysuru", "state": "Karnataka"}),
            ("Madurai", {"city": "Madurai", "state": "Tamil Nadu"}),
            ("Meerut", {"city": "Meerut", "state": "Uttar Pradesh"}),
        ]
        for word, data in cities:
            self.t.insert(word, data)

    def test_prefix_m_returns_all(self):
        results = self.t.search_prefix("m", limit=10)
        assert len(results) == 5

    def test_prefix_mu_returns_two(self):
        results = self.t.search_prefix("mu")
        cities = {r["city"] for r in results}
        assert "Mumbai" in cities
        assert "Munger" in cities

    def test_prefix_my_returns_one(self):
        results = self.t.search_prefix("my")
        assert len(results) == 1
        assert results[0]["city"] == "Mysuru"

    def test_nonexistent_prefix(self):
        assert self.t.search_prefix("xyz") == []

    def test_limit_respected(self):
        results = self.t.search_prefix("m", limit=2)
        assert len(results) <= 2

    def test_empty_prefix(self):
        # empty prefix walks to root; collecting from root returns all words
        # we just ensure it doesn't crash
        results = self.t.search_prefix("")
        assert isinstance(results, list)


class TestTrieDelete:
    def setup_method(self):
        self.t = Trie()
        self.t.insert("jaipur", {"city": "Jaipur"})
        self.t.insert("jalandhar", {"city": "Jalandhar"})

    def test_delete_existing_word(self):
        assert self.t.delete("jaipur") is True
        assert self.t.exact_match("jaipur") is None
        assert len(self.t) == 1

    def test_delete_nonexistent_word(self):
        assert self.t.delete("jodhpur") is False

    def test_sibling_intact_after_delete(self):
        self.t.delete("jaipur")
        result = self.t.search_prefix("jal")
        assert any(r["city"] == "Jalandhar" for r in result)

    def test_double_delete(self):
        self.t.delete("jaipur")
        assert self.t.delete("jaipur") is False   # already gone


class TestTrieNodeCount:
    def test_shared_prefix_reuses_nodes(self):
        t = Trie()
        t.insert("abc")
        nodes_after_first = t.node_count
        t.insert("abd")   # shares 'a','b' — only 1 new node for 'd'
        assert t.node_count == nodes_after_first + 1


# ══════════════════════════════════════════════════════════════════════ #
#  TypeaheadEngine integration tests                                     #
# ══════════════════════════════════════════════════════════════════════ #

class TestTypeaheadEngine:
    @classmethod
    def setup_class(cls):
        cls.engine = TypeaheadEngine(limit=8)

    def test_dataset_size(self):
        s = self.engine.stats()
        assert s["total_cities"] >= 10_000

    def test_known_city_found(self):
        results = self.engine.suggest("Mumbai")
        cities = [r["city"] for r in results]
        assert "Mumbai" in cities

    def test_prefix_mum(self):
        results = self.engine.suggest("mum")
        assert len(results) > 0
        for r in results:
            assert r["city"].lower().startswith("mum")

    def test_metro_cities_rank_first(self):
        results = self.engine.suggest("mum", limit=5)
        if results:
            assert results[0]["tier"] == 1   # Mumbai should come first

    def test_empty_query_returns_nothing(self):
        assert self.engine.suggest("") == []
        assert self.engine.suggest("   ") == []

    def test_nonexistent_prefix(self):
        assert self.engine.suggest("zzzzz") == []

    def test_add_custom_city(self):
        self.engine.add("Venom City", "Valorant Pradesh")
        results = self.engine.suggest("Venom")
        assert any(r["city"] == "Venom City" for r in results)

    def test_remove_city(self):
        self.engine.add("TempCity", "TestState")
        assert self.engine.remove("TempCity") is True
        results = self.engine.suggest("TempCity")
        assert not any(r["city"] == "TempCity" for r in results)

    def test_query_is_fast(self):
        """Lookup must complete in under 5 ms on any hardware."""
        t0 = time.perf_counter()
        self.engine.suggest("ban")
        elapsed = (time.perf_counter() - t0) * 1000
        assert elapsed < 5.0, f"Query too slow: {elapsed:.2f} ms"

    def test_stats_populated(self):
        s = self.engine.stats()
        assert s["queries_run"] > 0
        assert s["avg_query_ms"] >= 0
        assert s["trie_nodes"] > 0


# ══════════════════════════════════════════════════════════════════════ #
#  Run without pytest                                                    #
# ══════════════════════════════════════════════════════════════════════ #

def run_manual():
    """Simple runner when pytest is not installed."""
    import traceback

    classes = [
        TestTrieNode, TestTrieInsertAndExact, TestTrieSearch,
        TestTrieDelete, TestTrieNodeCount, TestTypeaheadEngine,
    ]

    passed = failed = 0
    for cls in classes:
        instance = cls()
        if hasattr(cls, "setup_class"):
            cls.setup_class()
        for name in dir(cls):
            if not name.startswith("test_"):
                continue
            if hasattr(instance, "setup_method"):
                instance.setup_method()
            try:
                getattr(instance, name)()
                print(f"  ✓  {cls.__name__}.{name}")
                passed += 1
            except Exception:
                print(f"  ✗  {cls.__name__}.{name}")
                traceback.print_exc()
                failed += 1

    print(f"\n  {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    print("\n─── Typeahead Trie — Test Suite ───\n")
    ok = run_manual()
    sys.exit(0 if ok else 1)
