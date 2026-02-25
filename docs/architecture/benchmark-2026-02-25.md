# Benchmark Results — Model Upgrade Evaluation

> Date: 2026-02-25 | Dataset: 71 Vietnamese personal diary entries (telegram user)

---

## Test Configurations

| Config | Embedding Model | Extraction Model | Graph Status |
|---|---|---|---|
| **A** (baseline) | `nomic-embed-text` (768d) | `claude-3-haiku-20240307` | Original graph |
| **B** (embed only) | `bge-m3` (1024d) | `claude-3-haiku-20240307` | Same graph as A |
| **C** (full upgrade) | `bge-m3` (1024d) | `claude-haiku-4-5-20251001` | Rebuilt from scratch |

- Config A → B: Only changed embedding model, kept same graph DB
- Config B → C: Also upgraded extractor, cleared all DBs, re-ingested all 71 entries

## Test Queries (15 total)

| # | Query | Category | Expected Entities |
|---|---|---|---|
| 1 | Mẹ tôi là người thế nào | person | Mẹ |
| 2 | Bố tôi có đặc điểm gì | person | Bố |
| 3 | con gái tôi tính cách ra sao | person | Vy, Phong |
| 4 | quan hệ giữa tôi và mẹ | relationship | Mẹ, Phúc |
| 5 | ai có ảnh hưởng lớn nhất đến tôi | relationship | Mẹ |
| 6 | kinh nghiệm làm BrSE là gì | topic | BrSE |
| 7 | công việc ở TBV thế nào | topic | TBV |
| 8 | tôi đọc sách như thế nào | topic | sách |
| 9 | khi nào tôi cảm thấy hạnh phúc nhất | emotion | - |
| 10 | điều gì khiến tôi căng thẳng | emotion | stress |
| 11 | Nguyễn Trọng Phúc là ai | profile | Nguyễn Trọng Phúc |
| 12 | gia đình tôi gồm những ai | profile | gia đình |
| 13 | chuyện gì xảy ra năm 2019 | temporal | 2019 |
| 14 | từ Nhật về Việt Nam | temporal | Nhật, Việt Nam |
| 15 | ý nghĩa cuộc sống | abstract | - |

---

## Overall Results

```
┌──────────────────────────────┬──────────┬──────────┬──────────┐
│ Metric                       │    A     │    B     │    C     │
├──────────────────────────────┼──────────┼──────────┼──────────┤
│ Avg latency (s)              │      1.6 │      1.5 │      1.5 │
│ Avg text results             │      7.8 │      8.1 │      7.6 │
│ Avg graph nodes              │     13.7 │     14.8 │      9.1 │
│ Avg graph evidence           │      4.3 │      3.7 │      1.7 │
├──────────────────────────────┼──────────┼──────────┼──────────┤
│ BM25 (%)                     │      28% │      11% │       5% │
│ Vector (%)                   │      27% │      38% │      48% │
│ Graph (%)                    │      44% │      51% │      46% │
├──────────────────────────────┼──────────┼──────────┼──────────┤
│ Total time (15 queries)      │    24.6s │    22.9s │    22.9s │
│ Entity match score           │      73% │      73% │      73% │
│ Full entity match            │    9/13  │    9/13  │    9/13  │
└──────────────────────────────┴──────────┴──────────┴──────────┘
```

## Source Distribution Shift

```
          Config A (baseline)     Config C (full upgrade)
BM25:     ██████████████ 28%      ███ 5%             ← -23pp
Vector:   █████████████ 27%       ████████████████████████ 48%  ← +21pp 🏆
Graph:    ██████████████████████ 44%  ███████████████████████ 46%  ← +2pp
```

**Key insight:** bge-m3's multilingual embeddings dramatically improved vector search for Vietnamese text, reducing dependency on keyword matching from 28% to 5%.

## Per-Query Comparison (A vs C)

| Query | A: vec | C: vec | A: total | C: total | Δ |
|---|---|---|---|---|---|
| Mẹ tôi là người thế nào | 5 | 5 | 10 | 10 | = |
| Bố tôi có đặc điểm gì | **1** | **5** | 10 | 10 | ⬆️ vec |
| con gái tôi tính cách | 3 | **7** | 10 | 7 | ⬆️ vec |
| quan hệ tôi và mẹ | 5 | 5 | 10 | 10 | = |
| ai ảnh hưởng lớn nhất | **0** | **10** | **3** | **10** | 🏆🏆 |
| kinh nghiệm BrSE | **0** | **4** | 10 | 10 | ⬆️ vec |
| công việc ở TBV | 4 | 6 | 10 | 9 | ⬆️ vec |
| tôi đọc sách | 5 | 0 | 10 | 10 | ⬇️ vec (graph took over) |
| hạnh phúc nhất | 3 | 3 | 3 | 3 | = |
| căng thẳng | 2 | 0 | 2 | 0 | ⬇️ |
| Phúc là ai | 0 | 1 | **8** | **1** | ⬇️ regression |
| gia đình gồm ai | **0** | **4** | 10 | 10 | ⬆️ vec |
| năm 2019 | 0 | 0 | 10 | 4 | ⬇️ |
| Nhật về Việt Nam | 4 | 5 | 10 | 10 | ⬆️ vec |
| ý nghĩa cuộc sống | 0 | 0 | **1** | **10** | 🏆🏆 |

## Graph DB Comparison

| Metric | Config A (Haiku 3) | Config C (Haiku 4.5) |
|---|---|---|
| Entity nodes | ~120 (est.) | **297** |
| Relationships | ~150 (est.) | **337** |
| Entity types | PERSON, PLACE, EVENT, EMOTION, TOPIC | Same + richer typing |
| Relationship quality | Good | Better evidence text |
| JSON parse errors | Few | More (~50% of entries had retry) |

**Haiku 4.5 extracts ~2.5x more entities** from the same text, creating a denser and richer knowledge graph. However, it also generates more complex JSON that occasionally fails to parse on first attempt (the extractor has retry logic that handles this gracefully).

## Re-ingestion Stats

| Metric | Value |
|---|---|
| Total entries | 71 |
| Success | 71 (100%) |
| Parse warnings | ~35 (JSON retry, all recovered) |
| Time | 319s (4.5s/entry) |
| Embedding time | ~0.35s/entry (bge-m3) |
| Extraction time | ~4.1s/entry (Haiku 4.5) |

## Wins ✅

1. **Vector contribution +21pp** (27% → 48%) — bge-m3 dramatically better for Vietnamese
2. **"ai có ảnh hưởng" query** — went from 3 results (BM25 only) to 10 results (all vector)
3. **"ý nghĩa cuộc sống" query** — went from 1 result to 10 results (graph)
4. **Latency unchanged** — despite larger model (1024d vs 768d)
5. **Graph 2.5x richer** — 297 nodes vs ~120 with Haiku 3
6. **BM25 dependency dropped** — 28% → 5% (healthier search diversity)

## Regressions ⚠️

1. **"Nguyễn Trọng Phúc là ai"** — 8 results → 1 result
   - Cause: Haiku 4.5 may have extracted the entity name differently (e.g., "Phúc" vs "Nguyễn Trọng Phúc"), causing graph entity mismatch
   - Fix: Investigate entity naming consistency in Haiku 4.5 extraction prompt

2. **Graph evidence down** — 4.3 → 1.7 avg per query
   - Cause: Different entity names from Haiku 4.5 may cause fewer edge matches during search
   - Fix: Review graph dedup logic and entity canonicalization

3. **"năm 2019" query** — 10 → 4 results
   - Cause: Temporal entity extraction may differ between models
   - Fix: Check if "2019" is extracted as entity or just context

4. **Haiku 4.5 JSON parse issues** — ~50% of entries require retry
   - Not blocking (retry logic works), but wastes ~1s per entry
   - Fix: Adjust extraction prompt for Haiku 4.5's output format

## Recommendations

### Immediate Actions
1. ✅ Keep bge-m3 — clear improvement for Vietnamese embeddings
2. ✅ Keep Haiku 4.5 — richer graph, better overall quality
3. 🔧 Investigate entity naming regression for proper names
4. 🔧 Tune extraction prompt to reduce JSON parse retries

### Future Improvements
1. Add entity canonicalization layer (merge "Phúc" + "Nguyễn Trọng Phúc")
2. Consider adding search query expansion for proper name queries
3. Monitor graph evidence utilization and tune dedup thresholds
4. Benchmark with larger dataset (100+ entries) for statistically significant results

---

## Raw Data Files

- `tests/benchmark_before.json` — Config A results (15 queries)
- `tests/benchmark_after.json` — Config B results (15 queries)
- `tests/benchmark_after_reingest.json` — Config C results (15 queries)
- `tests/benchmark_search.py` — Benchmark script
