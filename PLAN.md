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

### M13 — BM25 Reranking + Adaptive Budget (v0.4.0, HELD)
**Spec:** `docs/BM25_RERANK.md` (revised — adaptive budget now in scope)
**Prompts:** `tasks/todo/feat-bm25-reranking.md` (Phase 1, complete) + `tasks/todo/feat-bm25-adaptive-budget.md` (Phase 2, pending)
**Reference implementation:** `mcp-webgate/src/mcp_webgate/utils/reranker.py` + `tools/query.py` (`_redistribute_budget`)

**Status:** v0.4.0 is **held** until the adaptive budget phase lands. BM25 ordering alone provides weak value — the real leverage is proportional char allocation. Shipping v0.4.0 with ordering-only would waste the feature. CHANGELOG v0.4.0 entry must be rewritten when Phase 2 ships.

#### Phase 1 — BM25 ordering (code complete, release held)
- [x] Add module-level BM25 reranker helpers (`_tokenize`, `_bm25_scores`, `rerank_by_bm25`) ported from mcp-webgate
- [x] Admin valve `enable_bm25_rerank: bool = True` wired through `ConfigService`
- [x] Persist `cfg.generated_queries` in the unified model so the reranker can consume them
- [x] Extract text-sanitization pipeline from `_process_results` into `WebSearchHandler._sanitize_text`
- [x] Integrate rerank phase between fetch-clean and context construction in `_process_results`
- [x] Debug emission `BM25 RERANKED ORDER` when `valves.debug: true`
- [x] Version bump to `0.4.0` in `easysearch.py` frontmatter and `README.md` heading
- [x] Update `CHANGELOG.md` with `v0.4.0` entry
- [x] Update README "What's New" and add a bullet under Main Features

#### Phase 2 — Adaptive budget (required before v0.4.0 ships)
- [x] Strip truncation from `_sanitize_text` — pure cleaning only; truncation moves to the adaptive phase
- [x] Add `rerank_with_scores(query, sources)` helper (ports mcp-webgate signature; returns `(scores, reordered_sources)`)
- [x] Add `redistribute_budget(sources, allocs, scores)` helper (ports mcp-webgate `_redistribute_budget`)
- [x] Add module constant `BM25_FLOOR_CHARS = 200`
- [x] Replace Phase B in `_process_results` with: `rerank_with_scores` → proportional allocation → surplus redistribution → in-place truncation
- [x] Per-source allocation ceiling as module constant `BM25_CEILING_FACTOR = 3` (initially scoped as a valve; demoted to constant — exposing it would bloat config for a knob 99% of admins never touch)
- [x] Replace debug key `BM25 RERANKED ORDER` with `BM25 ADAPTIVE BUDGET` carrying per-source `score`, `init_alloc`, `final_alloc`, `actual_len`
- [x] Amend the existing v0.4.0 `CHANGELOG.md` entry (do NOT add a new version) to reflect adaptive budget + new valve
- [x] Amend the existing v0.4.0 "What's New" section in README accordingly
- [x] Retire or deprecate the old `rerank_by_bm25` helper (callers migrate to `rerank_with_scores`)
- [ ] Manual verification per `docs/BM25_RERANK.md` §9 — happy path + skewed scores + failed fetches + valve off + edge cases

---

## Next Milestone

### M14 — Engine-Aware Result Cap (target 2026-MM)
**Prompt:** `tasks/todo/enh-widen-results-cap.md`

Context: `max_results_per_query` ships with `le=50` and a Brave-only description. Research across OWUI backends confirms 20 is a safe floor, but SerpAPI/Exa/Serper allow 100. Admin users on those engines are unnecessarily capped. Default stays 20 (backend-agnostic safe choice); only the upper bound and description change.

- [x] Raise `max_results_per_query` upper bound from `le=50` to `le=100`
- [x] Rewrite valve description to be engine-agnostic with per-engine cap hints
- [x] CHANGELOG entry
- [x] README admin-valves table reflects new wording

---

### M15 — Tier 2 LLM-Assisted Reranking (opt-in, target post-v0.4.0)
**Prompt:** _to be drafted — `tasks/todo/feat-bm25-llm-rerank.md`_
**Reference implementation:** `mcp-webgate/src/mcp_webgate/utils/reranker.py` `rerank_llm`

Context: BM25 is keyword-only and structurally blind to semantic matches (synonyms, paraphrase, intent). For complex natural-language queries (especially cross-language `??:en>it` scenarios), this caps relevance quality. A Tier 2 LLM pass takes the Tier 1-ranked list and reorders by semantic relevance. Mandatory guard rails below prevent it from degrading EasySearch's "fast and cheap" default.

- [ ] New admin valve `enable_llm_rerank: bool = False` — **opt-in, default off**
- [ ] New admin valve `llm_rerank_model: Optional[str] = None` — when set, rerank runs on this model (cheap/fast small model); when `None`, falls back to the user's current chat model
- [ ] Strict timeout (hardcoded ≈5s) with silent fallback to Tier 1 order on timeout, malformed JSON, or any exception
- [ ] Lean prompt: `title + first 200 chars of snippet/content` per source — no conversation history, no system bloat (minimizes rerank-model context pressure, critical for self-hosted small-context backends)
- [ ] Phase ordering in `_process_results`: BM25 adaptive budget runs *before* Tier 2; Tier 2 only reorders, does not reallocate budget (allocations already computed from BM25 scores)
- [ ] Debug emission `LLM RERANKED ORDER` with per-source id/url when `valves.debug: true`
- [ ] README documentation under "Advanced Pro-Tips" with explicit latency/cost warning
- [ ] Manual verification: semantic-match query (e.g. query in language A, sources in language B) shows Tier 2 improving order vs Tier 1 alone

---

## Backlog (not scheduled)

Candidate follow-ups evaluated but explicitly deferred:

- **Round-robin sub-query interleaving** — replicate `mcp-webgate/tools/query.py:110-128` to avoid one sub-query dominating the candidate pool. Requires N separate `process_web_search` calls (one per sub-query) instead of OWUI's batch call — significant refactor for moderate ROI.

---

## Resolved Out-of-Plan Work

Items that were not scheduled milestones but landed during a fix cycle.

- **Snippet-pool BM25 reranking** (shipped v0.4.3) — originally listed as low-ROI backlog, but the v0.4.3 citation-coherence work made it necessary: unfiltered pool entries were leaking off-topic citations into the UI and confusing models into citing slugs (`[REF]…[/REF]`). The pool now passes through the same BM25 + zero-score filter as the fetched sources before injection, with `emit_citation` per surviving entry. Admin valve `inject_snippet_pool` controls whether the pool reaches the LLM context at all.
