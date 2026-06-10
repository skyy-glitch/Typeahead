# Typeahead Suggester — Indian Cities
## Data Structures Mini Project

A **prefix-search engine** over 10,000+ Indian cities, built on a hand-rolled
**Trie** (prefix tree) data structure. Lookups are O(k) — independent of
dataset size.

---

## Project Structure

```
typeahead_trie/
├── trie.py        ← Trie data structure (core DS implementation)
├── cities.py      ← Dataset: 10 000+ Indian cities
├── typeahead.py   ← Engine that glues Trie + dataset together
├── main.py        ← Interactive CLI demo
└── test_trie.py   ← Unit tests (30 tests, no dependencies)
```

---

## How to Run

```bash
# Interactive demo
python main.py

# Tests
python test_trie.py
```

No external libraries required — pure Python 3.8+.

---

## Data Structure: Trie (Prefix Tree)

```
root
 └── m
      ├── u
      │    ├── m → "Mumbai" ✓  (Maharashtra, tier 1)
      │    └── n → "Munger" ✓  (Bihar, tier 3)
      └── y
           └── s → "Mysuru" ✓  (Karnataka, tier 2)
```

### Node structure

```python
@dataclass
class TrieNode:
    children : dict[str, TrieNode]  # char → child
    is_end   : bool                 # marks a complete city name
    data     : dict | None          # payload: city, state, tier
    frequency: int                  # for ranking (tier-1 cities rank higher)
```

### Complexity

| Operation      | Time      | Notes                              |
|--------------- |-----------|------------------------------------|
| `insert(word)` | O(k)      | k = characters in word             |
| `search_prefix`| O(k + r)  | r = results collected              |
| `exact_match`  | O(k)      | —                                  |
| `delete(word)` | O(k)      | prunes empty nodes                 |
| Space          | O(n · k)  | n = words, k = avg length          |

### Why Trie over alternatives?

| Approach          | Search time | Notes                            |
|-------------------|-------------|----------------------------------|
| Linear scan       | O(n · k)    | Slows down with more cities      |
| Sorted list + bisect | O(log n + r) | Only works for pure prefixes  |
| Hash map          | O(1) exact  | Can't do prefix lookup           |
| **Trie**          | **O(k)**    | Pure prefix, fast, memory-efficient|

---

## Sample Session

```
  ──────────────────────────────────────────────────────
    Indian Cities Typeahead  •  Trie-powered
  ──────────────────────────────────────────────────────
  ✓ Indexed 10,000 cities in 42.3 ms  (58,241 nodes)

  » mum

  2 results for 'mum'  [0.0041 ms]

   1. Mumbai                       Maharashtra            ● metro
   2. Mumbra                       Maharashtra              other

  » ban

  8 results for 'ban'  [0.0038 ms]

   1. Bengaluru                    Karnataka              ● metro
   ...

  » :stats

  ── Stats ──────────────────────────────
  Cities indexed   : 10,000
  Trie nodes       : 58,241
  Build time       : 42.3 ms
  Queries run      : 6
  Avg query time   : 0.0039 ms
  Last query time  : 0.0038 ms
  ───────────────────────────────────────
```

---

## Key Design Decisions

1. **Frequency-based ranking** — Tier-1 metro cities (Mumbai, Delhi…) are
   inserted with higher frequency so they surface at the top of results.

2. **DFS collection** — After walking to the prefix node, a depth-first search
   collects all matching cities. Sorting by frequency then gives ranked output.

3. **Node pruning on delete** — The `delete` operation walks back up the path
   and removes nodes that are no longer needed, keeping memory lean.

4. **Case-insensitive** — All keys are lowercased at insert and search time,
   so `"MUM"`, `"mum"`, and `"Mum"` all return the same results.
