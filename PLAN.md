# EasySearch — Project Plan

> **Intelligent, context-aware web search filter for Open WebUI.**
> Single-file Python filter (`easysearch.py`). Bypasses OWUI's native scraper, performs parallel fetching with `httpx`, structural HTML cleaning with `lxml`, and feeds only high-quality content to the LLM.

---

## Legend

- `[x]` — shipped (verified against `CHANGELOG.md` and git history)
- `[ ]` — planned / in progress
- Pure bugfixes (`fix-` prompts) are tracked in `CHANGELOG.md`, **not** here (per `CLAUDE.md` §PLAN.md rules).

---

## Shipped Milestones

### M1 — Foundational Fork (v0.1.0, 2026-02-27)
- [x] Fork from EasyBrief: strip formatting, visual generation, and brief logic
- [x] "Search Only" mode triggered by `??`
- [x] Context Extraction from the last assistant message for empty `??` trigger
- [x] Filter priority set to `999` to prevent pipeline breakage during history wiping

### M2 — Deduplication & Configuration Core (v0.1.1 → v0.1.3, 2026-02-27)
- [x] URL deduplication in `_process_results`
- [x] Centralized `ConfigService` merging Admin and User valves into a unified model
- [x] Trigger parser handling `??N` count modifier
- [x] HTTPX streaming with `max_download_mb` cap (anti-flood)

### M3 — Dynamic Fetching & Safety Caps (v0.1.5, 2026-02-27)
- [x] Dynamic `WEB_SEARCH_RESULT_COUNT` calculation (`max(default, user_target)`) to prevent under-fetching
- [x] `max_total_results` hard safety cap valve (prevents `??1000` abuse)
- [x] `search_results_per_query` interpreted as minimum per-query fetch
- [x] Verbose logging of requested vs. capped vs. final counts

### M4 — Search Resilience & UX (v0.2.1, 2026-02-27)
- [x] URL sanitization (strip UTM / tracking params, fragments)
- [x] Oversampling in search execution for a healthy candidate pool
- [x] Auto-Recovery Fetch (Gap-Filler) — second parallel fetch from leftovers when primary fetch fails
- [x] `search_prefix` moved to `UserValves` for per-user customization
- [x] "Thinking..." UI status emitted at end of `inlet`
- [x] Unified configuration mapping extended to cover all new valves

### M5 — Network Resilience & Stealth (v0.2.2, 2026-02-28)
- [x] Configurable `search_timeout` admin valve
- [x] User-Agent rotation to evade anti-scraping blocks
- [x] Concurrent fetching with dynamic headers

### M6 — Multi-Modifier Syntax (v0.2.4 → v0.2.5, 2026-02-28)
- [x] Colon-separated modifiers in triggers (`??:en:10`, `??:10:it`)
- [x] System Prompt preservation during search (maintain model personality)
- [x] Regex-based HTML cleaning fallback when `lxml` unavailable
- [x] Dynamic singular/plural wording in status messages
- [x] Search language tracked in the unified model for debugging
- [x] User-Agent list expanded to 20 unique strings

### M7 — Deep Context & RAG Lockdown (v0.2.6, 2026-02-28)
- [x] `??:cN` context-depth modifier
- [x] `default_context_count` UserValve for empty-trigger lookback
- [x] Safe RAG / Retrieval lockdown in `inlet` with mandatory restoration in `outlet`
- [x] Status messages show exact number of messages analyzed
- [x] `lxml`-strict structural cleaning with explicit UI error on missing dependency

### M8 — Anti-Bleed Linguistic Control (v0.2.7 → v0.2.8, 2026-02-28)
- [x] "Anti-Bleed" system instruction: forces LLM to respond in the query language
- [x] Forbid LLM from generating bibliographies, source lists, URL repetitions at end of response

### M9 — Multi-Language Synthesis (v0.2.9, 2026-02-28)
- [x] `??:src>dest` dual-language syntax (decouple search language from response language)
- [x] "Smart Default" logic: response follows prompt language unless overridden
- [x] `_parse_trigger` refactored for complex language tokens

### M10 — Resilient Double-Layer Context (v0.3.0, 2026-02-28)
- [x] Snippet-First fallback logic in `_process_results` — recover signal when scraping yields low-quality content
- [x] Oversampling pool injection — all retrieved snippets passed to LLM for signal density
- [x] System prompt enforces snippet prioritization over noisy/empty scraped content
- [x] Result formatting distinguishes "Summary" (snippet) from "Full Content" (scraped)

### M11 — Linguistic Precision & Binary Scrubber (v0.3.1, 2026-02-28)
- [x] Language Anchor via `msg_list[-2]` for context-aware queries
- [x] `_parse_trigger` fix for single-language modifiers (`??:de`)
- [x] Pre-Fetch Blacklist for `.pdf`, `.docx`, `.zip` and other binaries
- [x] Aggressive text scrubber (C0/C1 control codes, `\ufffd`, Zero-Width, BiDi)
- [x] Gap-Filler total-count fix (no more overshoot beyond requested target)

### M12 — Polish & Documentation (v0.3.4, 2026-03-09)
- [x] Troubleshooting & FAQ section in README
- [x] Startup validation of OWUI global Web Search toggle
- [x] Improved "Smart Default" logic with dedicated Language Anchor
- [x] Binary skip + unicode junk removal in text cleaner
- [x] Unread-page snippets injected directly for signal density

---

## Current Milestone

### M13 — BM25 Deterministic Reranking (v0.4.0, target 2026-04)
**Spec:** `docs/BM25_RERANK.md`
**Prompt:** `tasks/todo/feat-bm25-reranking.md`
**Reference implementation:** `mcp-webgate/src/mcp_webgate/utils/reranker.py`

- [x] Add module-level BM25 reranker helpers (`_tokenize`, `_bm25_scores`, `rerank_by_bm25`) ported from mcp-webgate
- [x] Admin valve `enable_bm25_rerank: bool = True` wired through `ConfigService`
- [x] Persist `cfg.generated_queries` in the unified model so the reranker can consume them
- [x] Extract text-sanitization pipeline from `_process_results` into `WebSearchHandler._sanitize_text`
- [x] Integrate rerank phase between fetch-clean and context construction in `_process_results`
- [x] Debug emission `BM25 RERANKED ORDER` when `valves.debug: true`
- [x] Version bump to `0.4.0` in `easysearch.py` frontmatter and `README.md` heading
- [x] Update `CHANGELOG.md` with `v0.4.0` entry
- [x] Update README "What's New" and add a bullet under Main Features
- [ ] Manual verification checklist executed in a real OWUI instance (see `docs/BM25_RERANK.md` §9)

---

## Backlog (not scheduled)

Candidate follow-ups evaluated but explicitly deferred:

- **Tier 2 LLM-assisted reranking** — opt-in LLM relevance pass, as in mcp-webgate (`rerank_llm`). Value: semantic reordering where keyword overlap misses synonyms. Cost: one extra LLM call per query. Decision at a later sprint.
- **Adaptive budget** — proportional char allocation per source based on BM25 scores. EXPERIMENTAL in mcp-webgate. Requires budget redistribution machinery and surplus reclamation logic. Defer until there is a concrete case where flat allocation hurts output quality.
- **Snippet-pool reranking** — rerank `remaining_pool` (snippet-only) entries. Low ROI because the pool is secondary signal already; revisit if users report snippet-pool order complaints.
