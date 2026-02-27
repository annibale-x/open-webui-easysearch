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