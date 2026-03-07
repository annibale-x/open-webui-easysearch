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