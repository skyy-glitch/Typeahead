"""
typeahead.py — TypeaheadEngine: the glue between Trie and the city dataset.

Usage:
    from typeahead import TypeaheadEngine

    engine = TypeaheadEngine()
    results = engine.suggest("mum")          # → list of city dicts
    stats   = engine.stats()                 # → build/perf statistics
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Optional

from trie import Trie
from cities import get_cities


class TypeaheadEngine:
    """
    Wraps a Trie loaded with all Indian cities.

    Public API:
        suggest(prefix, limit)  → list[dict]   O(k) lookup
        add(city, state)        → None          insert a custom city
        remove(city)            → bool          delete a city
        stats()                 → dict          performance counters
    """

    def __init__(self, limit: int = 8) -> None:
        self.default_limit = limit
        self._trie = Trie()
        self._query_times: list[float] = []   # rolling window for avg

        # Click tracking setup
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if os.environ.get("VERCEL"):
            self._stats_file = "/tmp/search_stats.json"
        else:
            self._stats_file = os.path.join(script_dir, "search_stats.json")
        self._city_clicks: dict[str, int] = {}
        self._load_clicks()

        self._last_query_path: list[str] = ["Root"]
        self._last_query_failed: bool = False

        build_start = time.perf_counter()
        self._cities = get_cities()
        self._build()
        self._build_time_ms = (time.perf_counter() - build_start) * 1000

    def _load_clicks(self) -> None:
        try:
            if os.path.exists(self._stats_file):
                with open(self._stats_file, 'r', encoding='utf-8') as f:
                    self._city_clicks = json.load(f)
        except Exception as e:
            sys.stderr.write(f"Error loading clicks: {e}\n")

    def _save_clicks(self) -> None:
        try:
            with open(self._stats_file, 'w', encoding='utf-8') as f:
                json.dump(self._city_clicks, f, indent=2)
        except Exception as e:
            sys.stderr.write(f"Error saving clicks: {e}\n")

    def record_click(self, city: str, state: str) -> None:
        key = f"{city}, {state}"
        self._city_clicks[key] = self._city_clicks.get(key, 0) + 1
        self._save_clicks()

    # ------------------------------------------------------------------ #
    #  BUILD                                                               #
    # ------------------------------------------------------------------ #

    def _build(self) -> None:
        """Insert every city into the Trie. Called once at init."""
        for entry in self._cities:
            # tier-1 cities get higher frequency so they surface first
            freq = {1: 10, 2: 5, 3: 1}[entry["tier"]]
            data = {
                "city":  entry["city"],
                "state": entry["state"],
                "tier":  entry["tier"],
            }
            # Index under multiple keys to support various lookup patterns
            keys = [
                entry["city"],
                f"{entry['city']}, {entry['state']}",
                f"{entry['state']} - {entry['city']}"
            ]
            for key in keys:
                for _ in range(freq):
                    self._trie.insert(key, data)

    # ------------------------------------------------------------------ #
    #  SUGGEST                                                             #
    # ------------------------------------------------------------------ #

    def suggest(self, prefix: str, limit: Optional[int] = None) -> list[dict]:
        """
        Return up to *limit* city dicts matching *prefix*.
        Supports city prefix, city/state prefix, and state prefix lookups.
        """
        if not prefix or not prefix.strip():
            self._last_query_path = ["Root"]
            self._last_query_failed = False
            return []

        clean_prefix = prefix.strip()
        n = limit or self.default_limit
        t0 = time.perf_counter()

        # 1. Walk the Trie character by character to trace the path
        node = self._trie._root
        matched = []
        failed = False
        for ch in clean_prefix.lower():
            if ch in node.children:
                matched.append(ch)
                node = node.children[ch]
            else:
                failed = True
                break

        self._last_query_path = ["Root"] + [c.upper() for c in matched]
        if failed:
            self._last_query_path.append("❌")
        self._last_query_failed = failed

        # 2. Query prefix. We search with an expanded limit to de-duplicate results
        results = self._trie.search_prefix(clean_prefix, limit=n * 4)
        elapsed = (time.perf_counter() - t0) * 1000

        self._query_times.append(elapsed)
        if len(self._query_times) > 100:
            self._query_times.pop(0)

        # 3. De-duplicate by unique (city, state) key
        seen = set()
        unique_results = []
        for r in results:
            clean_r = {k: v for k, v in r.items() if k != "_freq"}
            key = (clean_r["city"].lower(), clean_r["state"].lower())
            if key not in seen:
                seen.add(key)
                unique_results.append(clean_r)

        return unique_results[:n]

    # ------------------------------------------------------------------ #
    #  ADD / REMOVE                                                        #
    # ------------------------------------------------------------------ #

    def add(self, city: str, state: str = "Unknown") -> None:
        """Insert a custom city into the engine at runtime."""
        data = {"city": city, "state": state, "tier": 3}
        self._trie.insert(city, data)
        self._trie.insert(f"{city}, {state}", data)
        self._trie.insert(f"{state} - {city}", data)
        
        if not any(c["city"].lower() == city.lower() for c in self._cities):
            self._cities.append(data)

    def remove(self, city: str) -> bool:
        """Remove a city. Returns True if it existed."""
        data = self._trie.exact_match(city)
        if not data:
            return False
        state = data.get("state", "Unknown")
        
        self._trie.delete(city)
        self._trie.delete(f"{city}, {state}")
        self._trie.delete(f"{state} - {city}")

        # Also remove from list of cities
        self._cities = [c for c in self._cities if c["city"].lower() != city.lower()]
        return True

    # ------------------------------------------------------------------ #
    #  STATS                                                               #
    # ------------------------------------------------------------------ #

    def stats(self) -> dict:
        """Return build and query performance statistics including popular searches and Trie path."""
        avg = (sum(self._query_times) / len(self._query_times)
               if self._query_times else 0.0)

        # Get top 5 most searched cities
        sorted_clicks = sorted(self._city_clicks.items(), key=lambda x: x[1], reverse=True)
        top_searches = []
        for key, count in sorted_clicks[:5]:
            parts = key.split(", ")
            if len(parts) == 2:
                top_searches.append({
                    "city": parts[0],
                    "state": parts[1],
                    "count": count
                })

        return {
            "total_cities":       len(self._cities),
            "trie_words":         len(self._trie),
            "trie_nodes":         self._trie.node_count,
            "build_time_ms":      round(self._build_time_ms, 3),
            "queries_run":        len(self._query_times),
            "avg_query_ms":       round(avg, 4),
            "last_query_ms":      round(self._query_times[-1], 4)
                                  if self._query_times else 0.0,
            "last_query_path":    self._last_query_path,
            "last_query_failed":  self._last_query_failed,
            "most_searched":      top_searches,
        }
