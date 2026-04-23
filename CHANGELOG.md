* 2026-04-23: v0.4.2 - OWUI Compatibility & Citation Fixes (Hannibal)
  * **fix:** `Users.get_user_by_id()` is synchronous in OWUI ≤0.8.12 and asynchronous in OWUI ≥0.9.x. Using a bare `await` on the sync version raises `object UserModel can't be used in 'await' expression`. Replaced all three call sites with a `_get_user()` helper that uses `inspect.isawaitable()` to branch at runtime — no minimum OWUI version requirement.
  * **fix:** Snippet-only `remaining_pool` entries were assigned `[N]` IDs in the search context but had no corresponding `emit_citation` call. OWUI silently drops inline `[N]` markers with no registered citation, so any fact the model cited from a snippet-only source would produce a dangling marker. All pool entries now emit a citation event.

* 2026-04-23: v0.4.1 - Engine-Aware Result Cap (Hannibal)
  * **enh:** Raised `max_results_per_query` upper bound from 50 to 100 so admins on SerpAPI, Exa, and Serper (which allow up to 100 per request) can make full use of their engine.
  * **docs:** Valve description is now engine-agnostic and lists the actual per-engine API caps for quick reference.

* 2026-04-23: v0.4.0 - BM25 Reranking + Dynamic Budget + Reasoning-Model Support (Hannibal)
  * **fix:** Strip `<think>...</think>` and `<thinking>...</thinking>` blocks from LLM responses before parsing. Reasoning models (phi-reasoning, deepseek-r1, qwen3 thinking mode) emit these blocks inline; without stripping them, JSON parsing in query generation fails and the fallback line-splitter turns reasoning text into search queries. Also handles truncated/unclosed `<think>` openers defensively. Fix applied to both `_generate_queries` and `_extract_query_from_context`.
  * **fix:** Inline citations were silently dropped by most models. Source blocks were labelled `--- Source N: Title ---` while the model was asked to cite as `[N]` — requiring a cognitive mapping step that recent models increasingly skip, especially in the presence of the `SECURITY:` instruction that tells them to ignore content inside `<search_results>`. Switched source labelling to `[N] Title` (matching the citation format 1:1) and rewrote the `CITATIONS:` and `SECURITY:` instructions to be explicit and non-conflicting. Pattern aligned with mcp-webgate's summarizer, which has been verified to produce inline citations reliably across models.
  * **feat:** BM25 relevance reranking. Fetched pages are ranked by keyword-overlap relevance against your query, so the most relevant sources appear first in the model's context — where LLM attention is strongest.
  * **feat:** Dynamic budget allocation. The per-source character budget is now proportional to BM25 score — highly relevant pages get up to `3 × max_result_length` chars; marginal pages shrink to a 200-char floor. Total context size is unchanged vs. the previous flat allocation — the same budget is just distributed more intelligently.
  * **feat:** Surplus redistribution. Characters unused by failed fetches or thin pages are reclaimed and handed to high-scoring pages that would otherwise be truncated. No wasted budget.
  * **feat:** New admin valve `enable_bm25_rerank` (default: `True`) — single toggle for the entire block (ranking + allocation). Disable to restore the v0.3.x flat-allocation behavior.
  * **enh:** `WebSearchHandler._sanitize_text` now does cleaning only; truncation moved to the dynamic allocation phase. The noise-filter regex is compiled once at module load (`NOISE_LINE_RE`).

* 2026-04-23: v0.3.5 - Bug Fixes & Security (Hannibal)
  * **fix:** Clamp `WEB_SEARCH_RESULT_COUNT` to a configurable `max_results_per_query` valve (default: 20). Brave Search API hard-rejects `count > 20` with 422 for all plans. Closes #3.
  * **fix:** Guard race condition on shared Filter singleton — concurrent requests could reset `self.ctx = None` mid-execution, causing `'NoneType' has no attribute 'model'` in `DebugService.emit()` and `outlet()`. Closes #1.
  * **fix:** Added missing `await` on `Users.get_user_by_id` calls — was returning coroutines instead of user objects, causing `'coroutine' has no attribute 'role'`. (PR #4 by @jaybill). Closes #5.
  * **security:** Wrapped raw web content in `<search_results>` XML tags with explicit untrusted-data instruction to mitigate indirect prompt injection from malicious pages. Addresses #2.

* 2026-03-09: v0.3.4 - Documentation & Logic Improvements (Hannibal)  
  * Added **Troubleshooting & FAQ** section to README.md.
  * Added immediate validation of Open WebUI's global Web Search toggle at startup.
  * Improved "Smart Default" logic with a dedicated Language Anchor.
  * Upgraded text cleaning engine to automatically skip binary files (.pdf, .docx, .zip) and remove Unicode junk characters.
  * All retrieved search snippets from unread pages are now fed directly to the LLM for better signal density.

* 2026-03-07: v0.3.3 - Documentation & Clarity (Hannibal)  

  * Added explicit clarification in README.md regarding the requirement of the global Web Search engine in the Admin Panel for initial result fetching.

* 2026-03-07: v0.3.2 - Early Exit & Syntax Fix (Hannibal)  

  * Moved the Global Web Search check from `_execute_search` to `inlet` (Phase 2) to fail early and save processing time if the feature is disabled.

  * Fixed an `unterminated string literal` syntax error in `DebugService.dump` caused by unsupported multiline f-strings in older Python versions.

* 2026-02-28: v0.3.1 - Linguistic Precision & Binary Scrubber (Hannibal)  
  * Fixed an issue where context-aware queries (`??`) would lose the original conversation language by implementing a strict `Language Anchor` using `msg_list[-2]`.
  * Fixed a bug in `_parse_trigger` that caused single-language modifiers (e.g., `??:de`) to ignore the `response_lang` constraint.
  * Introduced a Pre-Fetch Blacklist in `_process_results` to safely skip `.pdf`, `.docx`, `.zip` and other non-HTML binaries before establishing an HTTP connection.
  * Upgraded the text cleaner with an Aggressive Scrubber regex to annihilate C0/C1 control codes, `\ufffd` replacements, and Zero-Width/Bi-Directional characters from dirty DOM elements.
  * Fixed a bug in the Gap-Filler logic that caused the total source count to exceed the requested target.

* 2026-02-28: v0.3.0 - Resilient Double-Layer Context (Hannibal)
  * Implemented "Snippet-First" fallback logic in `_process_results` to prevent signal loss.
  * Added oversampling pool injection: all retrieved snippets are now fed to the LLM for massive signal density.
  * Enhanced System Prompt to enforce prioritization of Snippets over noisy/empty Scraped Content.
  * Refactored result formatting to distinguish between 'Summary' and 'Full Content'.

* 2026-02-28: v0.2.9 - Multi-Language Synthesis & Smart Defaults (Hannibal)
  * Implemented dual-language syntax `??:src>dest` for decoupled search/response.
  * Added Smart Default logic: responses follow user prompt language unless overridden.
  * Refactored `_parse_trigger` to handle complex language tokens.

* 2026-02-28: v0.2.8 - Anti-Bleed Injection (Hannibal)
  * Implementation of the "Anti-Bleed" system. The model now strictly adheres to the language of your query or the explicit `:lang` modifier
  * The LLM is now strictly forbidden from generating bibliographies, source lists, or URL repetitions at the end of the response

* 2026-02-28: v0.2.7 - Anti-Bleed Injection (Hannibal)
  * Implemented "Anti-Bleed" system instruction: Added a critical directive to the final prompt that forces the LLM to respond in the exact same language as the user's search query, preventing linguistic drift caused by foreign-language search results.

* 2026-02-28: v0.2.6 - Deep Context & RAG Lockdown (Hannibal)
  * Implemented colon-separated modifiers for context window depth (e.g., `??:c3`).
  * Added `default_context_count` User Valve to define default lookback for empty triggers.
  * Enhanced UI status messages to show the exact number of messages analyzed during context extraction.
  * Implemented safe RAG/Retrieval lockdown in `inlet` with mandatory restoration in `outlet`.
  * Optimized User-Agent list (20 unique strings) by removing duplicates and diversifying browser fingerprints.
  * Refined structural HTML cleaning using `lxml` with explicit error reporting for missing dependencies.

* 2026-02-28: v0.2.5 - Full Logic Consolidation (Hannibal)
  * Consolidated multi-modifier parsing logic (e.g., ??:en:10).
  * Expanded User-Agent rotation to 20 unique strings for better stealth.
  * Fixed pluralization in status messages (singular/plural 'page').
  * Implemented strict lxml requirement with explicit UI error reporting.
  * Verified and secured system prompt preservation during search cycles.
  * Mapped search language and query data into the unified model for enhanced debugging.

* 2026-02-28: v0.2.4 - Multi-Modifier Syntax & Context Preservation (Hannibal)  
  * Added support for colon-separated modifiers in triggers (e.g., `??:en:10`, `??:10:it`).
  * Implemented System Prompt preservation to maintain model personality during search.
  * Added regex-based fallback for HTML cleaning when lxml is unavailable or fails.
  * Fixed a regression causing double search execution in the inlet phase.
  * Implemented dynamic singular/plural logic for status recovery messages.
  * Integrated search language tracking in the unified configuration model for better debugging.

* 2026-02-28: v0.2.2 - Network Resilience & UA Rotation (Hannibal)
  * Added configurable search timeout via Admin Valves.
  * Implemented User-Agent rotation to prevent anti-scraping blocks.
  * Improved concurrent fetching logic with dynamic headers.

* 2026-02-27: v0.2.1 - Search Resilience & UX Milestone (Hannibal)
  * Implemented URL Sanitization to filter tracking parameters (UTM, etc.) and fragments.
  * Added Oversampling logic in search execution to ensure a healthy candidate pool.
  * Implemented Auto-Recovery Fetch (Gap-Filler) to maintain the requested source count.
  * Moved search_prefix to UserValves for full user customization.
  * Added "Thinking..." UI status emission at the end of the inlet phase.
  * Integrated unified configuration mapping in ConfigService for all new valves.

* 2026-02-27: v0.1.5 - Dynamic Fetching & Safety Caps (Hannibal)
  * Implemented dynamic calculation for `WEB_SEARCH_RESULT_COUNT` override: now uses `max(default, user_target)` to prevent underfetching when few queries are generated.
  * Added `max_total_results` Valve (default: 20) as a hard safety cap to prevent user abuse (e.g., `??1000`).
  * Refined `search_results_per_query` to act as a minimum guaranteed fetch count per query.
  * Updated logging to clearly show requested vs. capped vs. final target counts.
  
* 2026-02-27: v0.1.3 - Configuration Refactor & Anti-Flood (Hannibal)
  * Refactored configuration management into ConfigService for centralized Valve merging.
  * Implemented robust trigger parsing logic to handle `??N` modifiers.
  * Added HTTPX streaming with `max_download_mb` limit to prevent memory flooding.
  * Centralized Admin Valves and User Valves logic.
  * Enhanced debug logging across all critical paths.

* 2026-02-27: v0.1.1 - Core Refactor & Deduplication (Hannibal)
  * Added URL deduplication logic in `_process_results` to prevent redundant scraping.
  * Optimized token usage by filtering out duplicate search results before LLM processing.

* 2026-02-27: v0.1.0 - Core Refactor (Hannibal)
  * Forked from EasyBrief: removed all formatting, visual generation, and brief logic.
  * Implemented "Search Only" focus with `??` trigger.
  * Added Context Extraction for empty `??` trigger based on last assistant message.
  * Set Filter Priority to 999 to prevent pipeline breakage during history wiping.