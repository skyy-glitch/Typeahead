"""
main.py — Interactive CLI typeahead demo.

Run:
    python main.py

Commands while running:
    <any text>   → search cities with that prefix
    :stats       → show performance stats
    :add <city> <state>  → add a custom city
    :remove <city>       → remove a city
    :quit / :q   → exit
"""

from __future__ import annotations

import sys
import time


def print_banner() -> None:
    print("\n" + "─" * 52)
    print("  🏙  Indian Cities Typeahead  •  Trie-powered")
    print("─" * 52)


def print_help() -> None:
    print("  Type a city prefix to search.")
    print("  :stats          — performance report")
    print("  :add <city> <state>  — insert a city")
    print("  :remove <city>  — delete a city")
    print("  :q              — quit")
    print("─" * 52)


def format_result(i: int, entry: dict) -> str:
    tier_label = {1: "● metro", 2: "○ major", 3: "  other"}
    t = tier_label.get(entry.get("tier", 3), "")
    return f"  {i:>2}. {entry['city']:<28} {entry['state']:<22} {t}"


def print_stats(engine) -> None:
    s = engine.stats()
    print("\n  ── Stats ──────────────────────────────")
    print(f"  Cities indexed   : {s['total_cities']:,}")
    print(f"  Trie nodes       : {s['trie_nodes']:,}")
    print(f"  Build time       : {s['build_time_ms']:.1f} ms")
    print(f"  Queries run      : {s['queries_run']}")
    print(f"  Avg query time   : {s['avg_query_ms']:.4f} ms")
    print(f"  Last query time  : {s['last_query_ms']:.4f} ms")
    print("  ───────────────────────────────────────\n")


def main() -> None:
    print_banner()
    print("\n  Building Trie index…", end="", flush=True)

    from typeahead import TypeaheadEngine
    engine = TypeaheadEngine(limit=8)

    s = engine.stats()
    print(f"\r  ✓ Indexed {s['total_cities']:,} cities in "
          f"{s['build_time_ms']:.1f} ms  "
          f"({s['trie_nodes']:,} nodes)\n")
    print_help()

    while True:
        try:
            query = input("\n  » ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Bye!\n")
            break

        if not query:
            continue

        # ── Commands ────────────────────────────────────────────────────
        if query.lower() in (":q", ":quit", ":exit"):
            print("\n  Bye!\n")
            break

        if query == ":stats":
            print_stats(engine)
            continue

        if query.startswith(":add "):
            parts = query[5:].strip().split(maxsplit=1)
            if len(parts) < 2:
                print("  Usage: :add <city> <state>")
                continue
            engine.add(parts[0], parts[1])
            print(f"  ✓ Added '{parts[0]}' ({parts[1]})")
            continue

        if query.startswith(":remove "):
            city = query[8:].strip()
            ok = engine.remove(city)
            print(f"  {'✓ Removed' if ok else '✗ Not found:'} '{city}'")
            continue

        # ── Typeahead search ────────────────────────────────────────────
        t0 = time.perf_counter()
        results = engine.suggest(query)
        elapsed = (time.perf_counter() - t0) * 1000

        if not results:
            print(f"  No cities found for '{query}'.")
        else:
            count = len(results)
            print(f"\n  {count} result{'s' if count > 1 else ''} "
                  f"for '{query}'  [{elapsed:.4f} ms]\n")
            for i, entry in enumerate(results, 1):
                print(format_result(i, entry))


if __name__ == "__main__":
    main()
