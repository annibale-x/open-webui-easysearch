"""
title: 🌐 EasySearch
version: 0.2.7
author: Hannibal
repository: https://github.com/annibale-x/open-webui-easysearch
author_email: annibale.x@gmail.com
author_url: https://openwebui.com/u/h4nn1b4l
description: High-performance Web Search filter. Triggers: '?? <query>' or '??' (context-aware).
"""

import os
import json
import re
import time
import sys
import datetime
import random
import asyncio
from typing import Optional, Any, List, Dict, Tuple, Union
from pydantic import BaseModel, Field

# Open WebUI Imports
from open_webui.main import app  # type: ignore
from open_webui.models.users import Users, UserModel  # type: ignore
from open_webui.utils.chat import generate_chat_completion  # type: ignore
from open_webui.routers.retrieval import SearchForm, process_web_search  # type: ignore

# Optional Dependencies for Turbo Loader
try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    from lxml import html as lxml_html

    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False


# --- CONSTANTS ---

APP_ICON = "🌐"
APP_NAME = "EasySearch"
TRACE = False


# --- PROMPT TEMPLATES ---

# Query Generation Template for LLM (Used for expansion)
QUERY_GENERATION_TEMPLATE = """### Task:
Analyze the user request to determine the necessity of generating search queries.
The aim is to retrieve comprehensive, updated, and valuable information.
{LANG_RULE}
### Guidelines:
- Respond **EXCLUSIVELY** with a JSON object. Any form of extra commentary is strictly prohibited.
- Format: {{ "queries": ["query1", "query2"] }}
- Generate up to {COUNT} distinct, concise, and relevant queries.
- Today's date is: {DATE}.
### User Request:
{REQUEST}
### Output:
Strictly return in JSON format:
{{
  "queries": ["query1", "query2"]
}}
"""

# Context Extraction Template (Used for '??' empty trigger)
CONTEXT_EXTRACTION_TEMPLATE = """
[SYSTEM]
You are a Search Query Extractor.
Task: Extract a single, highly effective web search query based on the provided text.
Constraint: Output ONLY the query string. Do not explain.
Text: {TEXT}
"""

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/122.0.6261.89 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.105 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S921B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.105 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SAMSUNG SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 Chrome/117.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Vivaldi/6.6.3271.45",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

# --- CORE CLASSES ---


class Store(dict):
    """
    A dictionary subclass that allows attribute-style access.
    Used for managing internal model state.
    """

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            return None

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class ConfigService:
    """
    Service for handling configuration, valves, and internal state.
    Centralizes 'splatting' of Admin Valves and User Valves into a single model.
    """

    def __init__(self, ctx):
        self.ctx = ctx
        self.valves, self.user_valves = ctx.valves, ctx.user_valves
        self.start_time = time.time()

        # Resolve Search Prefix from User Preference ONLY
        prefix = self.user_valves.search_prefix

        # Resolve Gap-Filler / Result Count Assurance (User Override > Admin Global)
        gap_filler_state = self.valves.auto_recovery_fetch

        if self.user_valves.auto_recovery_fetch is not None:
            gap_filler_state = self.user_valves.auto_recovery_fetch

        # Build Unified Configuration Model
        self.model = Store(
            {
                # --- Configuration (Merged) ---
                "search_prefix": prefix,
                "max_search_queries": self.valves.max_search_queries,
                "search_results_per_query": self.valves.search_results_per_query,
                "max_total_results": self.valves.max_total_results,
                "max_download_bytes": self.valves.max_download_mb * 1024 * 1024,
                "max_result_length": self.valves.max_result_length,
                "search_timeout": self.valves.search_timeout,
                "debug": self.valves.debug or self.user_valves.debug,
                "oversampling_factor": self.valves.oversampling_factor,
                # --- Renamed for clarity in the model ---
                "auto_recovery_fetch": gap_filler_state,
                # --- Runtime State ---
                "user_query": "",
                "search_language": None,  # Tracked for debug
                "executed": False,
                "web_search_original": False,
                "retrieval_original": False,
            }
        )


class ShadowRequest:
    """
    A thread-safe proxy for the Request object.
    Allows overriding specific app.state.config attributes dynamically.
    """

    def __init__(self, original_request, overrides: Dict[str, Any]):
        self._req = original_request
        self._overrides = overrides

        class ConfigProxy:
            def __init__(self, real_config, overrides):
                self._real = real_config
                self._overrides = overrides

            def __getattr__(self, name):
                if name in self._overrides:
                    return self._overrides[name]
                return getattr(self._real, name)

        class StateProxy:
            def __init__(self, real_state, config_proxy):
                self._real = real_state
                self.config = config_proxy

            def __getattr__(self, name):
                if name == "config":
                    return self.config
                return getattr(self._real, name)

        class AppProxy:
            def __init__(self, real_app, state_proxy):
                self._real = real_app
                self.state = state_proxy

            def __getattr__(self, name):
                if name == "state":
                    return self.state
                return getattr(self._real, name)

        real_app = original_request.app
        real_state = real_app.state
        real_config = real_state.config

        self.app = AppProxy(
            real_app, StateProxy(real_state, ConfigProxy(real_config, overrides))
        )

    def __getattr__(self, name):
        if name == "app":
            return self.app
        return getattr(self._req, name)


class WebSearchHandler:
    """
    A portable handler for Web Search operations.
    Encapsulates query generation, execution, citation emission, and result formatting.
    """

    def __init__(
        self,
        request,
        user_id: str,
        emitter: Any,
        config: Any,  # Receives the unified ConfigService model
        debug_service: Any = None,
    ):
        self.request = request
        self.user_id = user_id
        self.em = emitter
        self.cfg = config  # Store unified config
        self.debug = debug_service
        self.user_obj = Users.get_user_by_id(user_id)

    def log(self, msg: str, is_error: bool = False):
        if self.debug:
            self.debug.log(f"[WebSearchHandler] {msg}", is_error)

    async def search(
        self, query: str, model: str, result_count: int, lang: Optional[str] = None
    ) -> Optional[str]:
        """
        Main entry point.
        :param result_count: Number of actual web pages to fetch and read (N).
        """
        try:
            # Clamp result_count to max_total_results (Safety Cap)
            max_cap = self.cfg.max_total_results
            final_count = min(result_count, max_cap)

            self.log(
                f"Starting search cycle. Requested: {result_count}, Max Cap: {max_cap}, Final Target: {final_count}, Lang: {lang}"
            )

            # 1. Generate Queries (Limit from Config)
            gen_count = self.cfg.max_search_queries
            await self.em.emit_status("Generating Search Queries", False)
            queries = await self._generate_queries(query, model, gen_count, lang)

            if not queries:
                queries = [query]

            self.log(f"Generated Queries ({len(queries)}): {queries}")
            await self.em.emit_search_queries(queries)

            # 2. Execute Search (Bypassing OWUI Loader safely)
            # Pass final_count to calculate dynamic results per query
            results = await self._execute_search(queries, final_count)

            if self.debug and TRACE:
                self.debug.dump(results, "RAW SEARCH RESULTS")

            if not results:
                await self.em.emit_status("⚠️ No results found", True)
                return None

            # 3. Process Results (Fetch N pages)
            formatted_context = await self._process_results(results, final_count)

            if TRACE:
                self.debug.log(f"Formatted results: {formatted_context}")

            return formatted_context

        except Exception as e:
            self.log(f"Search Cycle Failed: {e}", True)
            await self.em.emit_status(f"❌ Search Error: {str(e)}", True)
            return None

    async def _generate_queries(
        self, text: str, model: str, count: int, lang: Optional[str] = None
    ) -> List[str]:
        """Uses LLM to expand the user request into multiple search queries."""

        try:
            lang_rule = (
                f"- Search results and queries MUST be in the following language/locale: {lang}."
                if lang
                else ""
            )

            prompt = QUERY_GENERATION_TEMPLATE.format(
                COUNT=count,
                DATE=datetime.date.today(),
                REQUEST=text,
                LANG_RULE=lang_rule,
            )

            messages = [{"role": "user", "content": prompt}]
            form_data = {"model": model, "messages": messages, "stream": False}

            response = await generate_chat_completion(
                self.request, form_data, user=self.user_obj
            )

            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"].strip()
                content = re.sub(r"```json|```", "", content).strip()
                try:
                    data = json.loads(content)
                    queries = data.get("queries", [])
                    if isinstance(queries, list):
                        return queries[:count]
                except json.JSONDecodeError:
                    self.log("JSON Decode Error in Query Gen", True)
                    return [
                        line.strip('- *"')
                        for line in content.split("\n")
                        if line.strip()
                    ][:count]
            return [text]

        except Exception as e:
            self.log(f"Query Gen Error: {e}", True)
            return [text]

    async def _execute_search(self, queries: List[str], target_count: int) -> Any:
        """
        Calls Open WebUI search with oversampling to ensure enough candidates after deduplication.
        """

        try:
            # ⚠️ FIX: Using self.cfg (unified model) instead of self.valves
            # The oversampling_factor is passed from Filter.Valves into the unified config model
            factor = getattr(self.cfg, "oversampling_factor", 2)

            # Request more results than target to compensate for duplicates/dead links
            count_per_query = (
                max(self.cfg.search_results_per_query, target_count) * factor
            )

            self.log(
                f"Executing Shadow Request. Oversampling: {factor}x. Target Per Query: {count_per_query}"
            )

            overrides = {
                "BYPASS_WEB_SEARCH_WEB_LOADER": True,
                "WEB_SEARCH_RESULT_COUNT": count_per_query,
            }

            shadow_req = ShadowRequest(self.request, overrides=overrides)
            form_data = SearchForm(queries=queries, collection_name="")

            return await process_web_search(shadow_req, form_data, self.user_obj)

        except Exception as e:
            self.log(f"Process Web Search Error: {e}", True)
            raise e

    def _sanitize_url(self, url: str) -> str:
        """
        Removes common tracking parameters and fragments from the URL to improve deduplication
        without breaking dynamic routing.
        """

        from urllib.parse import urlparse, parse_qsl, urlunparse, urlencode

        try:
            parsed = urlparse(url)

            # List of parameters that usually do not change the page content
            tracking_params = {
                "utm_source",
                "utm_medium",
                "utm_campaign",
                "utm_term",
                "utm_content",
                "gclid",
                "fbclid",
                "msclkid",
                "mc_cid",
                "mc_eid",
            }

            query_dict = dict(parse_qsl(parsed.query))

            filtered_query = {
                k: v for k, v in query_dict.items() if k.lower() not in tracking_params
            }

            # Return URL without fragment and with filtered query string
            return urlunparse(
                parsed._replace(query=urlencode(filtered_query), fragment="")
            )

        except Exception:
            return url

    async def _fetch_concurrently(self, urls: List[str]) -> Dict[str, str]:
        """
        Fetches multiple URLs in parallel using HTTPX with streaming, size limit and UA rotation.
        """

        if not HTTPX_AVAILABLE or not urls:
            return {}

        results = {}
        verify_ssl = os.environ.get("REQUESTS_CA_BUNDLE", True)

        if verify_ssl == "":
            verify_ssl = True

        # Use configured limits from unified model
        max_bytes = self.cfg.max_download_bytes
        req_timeout = float(self.cfg.search_timeout)

        self.log(
            f"Fetching {len(urls)} URLs. Limit: {max_bytes} bytes, Timeout: {req_timeout}s"
        )

        timeout = httpx.Timeout(req_timeout, connect=5.0)
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

        async def fetch_single(client, url):
            try:
                # Rotate User-Agent for each request to minimize blocking
                headers = {"User-Agent": random.choice(USER_AGENTS)}

                req = client.build_request("GET", url, headers=headers)
                response = await client.send(req, stream=True)

                if response.status_code != 200:
                    await response.aclose()
                    return None

                body = b""

                async for chunk in response.aiter_bytes():
                    body += chunk

                    if len(body) > max_bytes:
                        # Cut connection immediately to save bandwidth/RAM
                        await response.aclose()
                        break

                await response.aclose()

                # Decode safely
                encoding = response.encoding or "utf-8"
                return body.decode(encoding, errors="replace")

            except Exception as e:

                if self.debug:
                    self.debug.log(f"Fetch failed for {url}: {e}")
                return None

        try:

            async with httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                follow_redirects=True,
                verify=verify_ssl,
                trust_env=True,
            ) as client:
                tasks = [fetch_single(client, url) for url in urls]
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                for url, content in zip(urls, responses):

                    if isinstance(content, str):
                        results[url] = content

        except Exception as e:
            self.log(f"HTTPX Batch Error: {e}", True)

        return results

    async def _clean_with_lxml(self, raw_html: str) -> str:
        """
        Uses lxml to strip HTML tags and noise. Requires lxml to be installed.
        """

        if not raw_html:
            return ""

        if not LXML_AVAILABLE:
            self.log(
                "Critical Error: lxml library is missing in this environment.", True
            )

            await self.em.emit_status(
                "❌ Error: lxml library missing (Required for EasySearch)", True
            )
            return ""

        try:
            tree = lxml_html.fromstring(raw_html)

            cleaner_xpath = "//script | //style | //nav | //footer | //header | //aside | //form | //iframe | //noscript"

            for element in tree.xpath(cleaner_xpath):
                element.drop_tree()

            text = tree.text_content()

            return text.strip()

        except Exception as e:
            self.log(f"lxml parsing failed: {e}", True)

            return ""

    async def _process_results(self, results: Any, target_count: int) -> Optional[str]:
        """
        Parses results, fetches raw HTML in parallel with a fallback mechanism (Gap-Filler).
        """

        if not isinstance(results, dict) or "items" not in results:
            return None

        raw_items = results["items"]

        if not raw_items:
            return None

        # --- DEDUPLICATION & SANITIZATION START ---
        seen_urls = set()
        unique_items = []

        for item in raw_items:
            original_url = item.get("link", "")

            if not original_url:
                continue

            sanitized_url = self._sanitize_url(original_url)

            if sanitized_url not in seen_urls:
                seen_urls.add(sanitized_url)
                # Store the sanitized URL in the item for consistency during fetching
                item["sanitized_link"] = sanitized_url
                unique_items.append(item)

        self.log(
            f"Deduplication: {len(raw_items)} raw -> {len(unique_items)} unique. Target: {target_count}"
        )

        # --- ROUND 1: INITIAL FETCH ---
        candidates = unique_items[:target_count]
        remaining_pool = unique_items[target_count:]

        urls_to_fetch = [item.get("link") for item in candidates]
        fetched_html_map = {}

        if HTTPX_AVAILABLE and LXML_AVAILABLE and urls_to_fetch:
            await self.em.emit_status(f"Reading {len(urls_to_fetch)} pages", False)
            fetched_html_map = await self._fetch_concurrently(urls_to_fetch)

        # --- ROUND 2: GAP FILLER (Controlled by auto_recovery_fetch) ---
        success_count = len([v for v in fetched_html_map.values() if v])

        # Use the unified and renamed config key
        enable_gap = getattr(self.cfg, "auto_recovery_fetch", True)

        if enable_gap and success_count < target_count and remaining_pool:

            gap_size = target_count - success_count

            if self.debug:
                self.debug.log(
                    f"Gap detected: {gap_size} missing. Triggering thorough search."
                )

            msg = f"Recovering {gap_size} failed {'page' if gap_size == 1 else 'pages'}"
            await self.em.emit_status(msg, False)

            backup_candidates = remaining_pool[:gap_size]
            backup_urls = [item.get("link") for item in backup_candidates]

            backup_html_map = await self._fetch_concurrently(backup_urls)
            fetched_html_map.update(backup_html_map)

            # Combine candidates for final processing
            candidates.extend(backup_candidates)

        # --- FINAL CONTEXT CONSTRUCTION ---
        context_parts = []
        max_len = self.cfg.max_result_length

        noise_pattern = re.compile(
            r"^(?:menu|home|search|sign in|log in|sign up|register|subscribe|newsletter|account|profile|cart|checkout|buy now|shop|close|cancel|skip to content|next|previous|back to top|privacy policy|terms|cookie|copyright|all rights reserved|legal|contact us|help|support|faq|social|follow us|share|facebook|twitter|instagram|linkedin|youtube|advertisement|sponsored|promoted|related posts|read more|loading|posted by|written by|author|category|tags)$",
            re.IGNORECASE,
        )

        source_id = 1

        for item in candidates:
            url = item.get("link", "")

            if url not in fetched_html_map or not fetched_html_map[url]:
                continue

            text = await self._clean_with_lxml(fetched_html_map[url])

            if not text:
                continue

            # Cleaning Pipeline
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            text = re.sub(r"[ \t\u00A0]+", " ", text)

            lines = text.split("\n")
            cleaned_lines = []
            prev_line = ""

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if noise_pattern.match(line):
                    continue
                if len(line) < 5 and not any(c.isalnum() for c in line):
                    continue
                if len(line) < 20 and re.match(
                    r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w{3} \d{1,2},? \d{4}", line
                ):
                    continue
                if line == prev_line:
                    continue

                cleaned_lines.append(line)
                prev_line = line

            text = "\n".join(cleaned_lines)
            text = re.sub(r"\n{3,}", "\n\n", text)

            # Dynamic Truncation
            if len(text) > max_len:
                text = text[:max_len] + "... [TRUNCATED]"

            context_parts.append(
                f"--- Source {source_id}: {item.get('title', 'Source')} ---\nURL: {url}\nContent:\n{text[:max_len]}\n"
            )

            await self.em.emit_citation(
                item.get("title", "Source"), item.get("snippet", ""), url
            )

            source_id += 1

        return "\n".join(context_parts)


class EmitterService:
    """
    Service for emitting events and status updates to the UI.
    """

    def __init__(self, event_emitter, ctx):
        self.emitter, self.ctx = event_emitter, ctx

    async def emit_status(self, description: str, done: bool = False):
        if self.emitter:
            await self.emitter(
                {"type": "status", "data": {"description": description, "done": done}}
            )

    async def emit_citation(self, name: str, document: str, source: str):
        if self.emitter:
            await self.emitter(
                {
                    "type": "citation",
                    "data": {
                        "source": {"name": name},
                        "document": [document],
                        "metadata": [{"source": source}],
                    },
                }
            )

    async def emit_search_queries(self, queries: List[str]):
        if self.emitter:
            await self.emitter(
                {
                    "type": "status",
                    "data": {
                        "action": "web_search_queries_generated",
                        "description": "🔍 Searching",
                        "queries": queries,
                        "done": False,
                    },
                }
            )


class DebugService:
    """
    Service for logging and dumping debug information.
    """

    def __init__(self, ctx):
        self.ctx = ctx

    def log(self, msg: str, is_error: bool = False):
        is_debug = (
            self.ctx.ctx.model.debug if self.ctx.ctx else self.ctx.user_valves.debug
        )
        if is_debug or is_error:
            delta = time.time() - self.ctx.ctx.start_time if self.ctx.ctx else 0
            print(
                f"{'❌' if is_error else '⚡'} [{delta:+.2f}s] {APP_NAME} DEBUG: {msg}",
                file=sys.stderr,
                flush=True,
            )

    async def error(self, e: Any):
        self.log(str(e), is_error=True)
        if self.ctx:
            if self.ctx.em.emitter:
                await self.ctx.em.emitter(
                    {"type": "message", "data": {"content": f"\n\n❌ ERROR: {str(e)}"}}
                )

    def dump(self, data: Any = None, label: str = "DUMP"):
        is_debug = (
            self.ctx.ctx.model.debug if self.ctx.ctx else self.ctx.user_valves.debug
        )
        if not is_debug:
            return
        print(
            f"{'—'*60}\n📦 {APP_NAME} {label}:\n{json.dumps(data, indent=2, default=lambda o: str(o))}\n{'—'*60}",
            file=sys.stderr,
            flush=True,
        )

    def emit(self):
        if not self.ctx.user_valves.debug:
            return ""

        def _s(d):
            return {
                k: (
                    _s(v)
                    if isinstance(v, dict)
                    else (
                        f"{v[:4]}...{v[-4:]}"
                        if isinstance(v, str)
                        and ("key" in k.lower() or "auth" in k.lower())
                        else v
                    )
                )
                for k, v in d.items()
            }

        return (
            f"\n\n<details>\n\n"
            f"<summary>🔍 {APP_NAME} Debug</summary>\n\n"
            f"```json\n{json.dumps(_s(self.ctx.ctx.model), indent=2)}\n```\n\n"
            f"</details>"
        )


class Filter:
    # Set high priority to ensure this filter runs LAST in the pipeline.
    priority = 999

    class Valves(BaseModel):
        # Admin / Infrastructure Settings
        max_search_queries: int = Field(
            default=3,
            ge=1,
            le=5,
            description="Max distinct search queries generated by LLM.",
        )
        search_results_per_query: int = Field(
            default=5,
            ge=1,
            le=20,
            description="Minimum results to fetch per query (Default).",
        )
        max_total_results: int = Field(
            default=20,
            ge=1,
            le=50,
            description="Hard limit on total pages to read (Safety Cap).",
        )
        max_download_mb: int = Field(
            default=1,
            ge=1,
            description="Max download size per page in MB (Anti-Flood).",
        )
        max_result_length: int = Field(
            default=4000,
            ge=500,
            description="Max characters per search result context.",
        )
        search_timeout: int = Field(
            default=8,
            ge=1,
            le=30,
            description="Timeout in seconds for web requests.",
        )
        oversampling_factor: int = Field(
            default=2,
            ge=1,
            le=4,
            description="Multiplier for search results to provide a buffer for deduplication/dead links.",
        )
        auto_recovery_fetch: bool = Field(
            default=False,
            description="If enabled, performs a second search round to replace failed or empty pages.",
        )
        debug: bool = Field(default=False)

    class UserValves(BaseModel):
        # User Preferences
        search_prefix: Optional[str] = Field(
            default="??",
            description="Custom Trigger prefix. Leave empty to use Admin default.",
            min_length=1,
            max_length=3,
        )
        auto_recovery_fetch: bool = Field(
            default=False,
            description="If enabled, performs a second search round to replace failed or empty pages.",
        )
        default_context_count: int = Field(
            default=1,
            ge=1,
            le=10,
            description="Default number of previous messages to use as context for '??' trigger.",
        )
        debug: bool = Field(default=False)

    def __init__(self):
        self.valves, self.user_valves = self.Valves(), self.UserValves()
        self.request = self.debug = self.net = self.em = self.ctx = None

    def _parse_trigger(self, txt: str) -> Optional[dict]:
        """
        Parse input for trigger using ONLY user-defined prefix and colon-separated modifiers.
        Syntax: '??', '??:7', '??:en', '??:c3', '??:en:10:c2'.
        """

        prefix = self.user_valves.search_prefix

        if not txt.startswith(prefix):
            return None

        parts = txt.split(" ", 1)
        trigger_part = parts[0]
        content = parts[1].strip() if len(parts) > 1 else ""

        tokens = trigger_part[len(prefix) :].split(":")
        tokens = [t for t in tokens if t]

        # Default values
        target_count = (
            self.valves.max_search_queries * self.valves.search_results_per_query
        )
        lang = None
        context_count = self.user_valves.default_context_count

        for token in tokens:
            if token.isdigit():
                target_count = int(token)
            elif token.startswith("c") and token[1:].isdigit():
                context_count = int(token[1:])
            elif len(token) == 2 and token.isalpha():
                lang = token.lower()

        return {
            "is_search": True,
            "content": content,
            "target_count": target_count,
            "lang": lang,
            "context_count": context_count,
        }

    async def _extract_query_from_context(
        self, context_text: str, model: str, user_id: str
    ) -> str:
        """
        Generates a search query based on the provided context (last message).
        """
        try:
            user = Users.get_user_by_id(user_id)
            prompt = CONTEXT_EXTRACTION_TEMPLATE.format(TEXT=context_text[:2000])

            messages = [{"role": "user", "content": prompt}]
            form_data = {"model": model, "messages": messages, "stream": False}

            response = await generate_chat_completion(
                self.request, form_data, user=user
            )

            if isinstance(response, dict) and "choices" in response:
                return response["choices"][0]["message"]["content"].strip().strip('"')
            return context_text[:100]

        except Exception as e:
            if self.debug:
                self.debug.log(f"Context Query Gen Failed: {e}", True)
            return context_text[:100]

    async def inlet(
        self,
        body: dict,
        __user__: dict = None,  # type: ignore
        __event_emitter__: callable = None,  # type: ignore
        __request__=None,
    ) -> dict:
        """Process the incoming request and trigger search logic."""
        self.ctx = None
        self.request = __request__

        # Load User Valves
        uv_data = __user__.get("valves", {}) if __user__ else {}
        self.user_valves = (
            self.UserValves(**uv_data) if isinstance(uv_data, dict) else uv_data
        )

        msg_list = body.get("messages", [])
        if not msg_list:
            return body

        # Extract text from last message
        last_msg = msg_list[-1].get("content", "")
        if isinstance(last_msg, list):
            txt = "\n".join(
                [
                    str(part.get("text", ""))
                    for part in last_msg
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
            )
        else:
            txt = str(last_msg)
        txt = txt.strip()

        # Phase 1: Parsing
        parsed = self._parse_trigger(txt)

        if not parsed:
            return body

        # Phase 2: Initialization
        self.ctx = ConfigService(self)
        self.debug, self.em = DebugService(self), EmitterService(
            __event_emitter__, self
        )

        # Update model with parsed triggers
        self.ctx.model.user_query = parsed["content"]
        self.ctx.model.search_language = parsed["lang"]

        self.debug.log(
            f"Trigger recognized: lang={parsed['lang']}, count={parsed['target_count']}, query='{parsed['content']}'"
        )

        if TRACE:
            self.debug.dump(body, "Body")

        await self.em.emit_status("EasySearch initialized", False)

        # Phase 3: State Management
        # ConfigService is initialized here, merging Valves and UserValves
        self.ctx.model.web_search_original = body.get("features", {}).get(
            "web_search", False
        )
        self.ctx.model.retrieval_original = body.get("features", {}).get(
            "retrieval", False
        )
        content = parsed["content"]

        # Override default count if specified in trigger
        target_count = parsed["target_count"]

        # Phase 4: Context Resolution (Empty Trigger '??')
        if not content and len(msg_list) > 1:
            # Get the previous messages based on context_count modifier or default
            c_count = parsed.get("context_count", 1)
            context_window = (
                msg_list[-(c_count + 1) : -1]
                if len(msg_list) > c_count
                else msg_list[:-1]
            )

            context_text = ""

            for m in context_window:
                role = m.get("role", "user")
                c = m.get("content", "")
                text = c[0].get("text", "") if isinstance(c, list) else str(c)
                context_text += f"{role.upper()}: {text}\n"

            self.debug.log(
                f"Empty trigger detected. Analyzing context window ({len(context_window)} msgs)"
            )

            # ⚠️ SURGICAL FIX: Improved status message with context depth
            status_msg = f"Extracting query from last {len(context_window)} {'msg' if len(context_window) == 1 else 'msgs'}"
            await self.em.emit_status(status_msg, False)

            # Generate query from context
            content = await self._extract_query_from_context(
                context_text, body.get("model"), __user__["id"]
            )

            self.debug.log(f"Extracted Query: {content}")

            # Update status to show the search is starting
            await self.em.emit_status(f"Searching {target_count} pages", False)

        self.ctx.model.user_query = content

        try:
            # Phase 5: Search Execution
            search_handler = WebSearchHandler(
                self.request, __user__["id"], self.em, self.ctx.model, self.debug
            )

            # Execute Search Cycle with language support
            search_context = await search_handler.search(
                self.ctx.model.user_query,
                body.get("model"),
                parsed["target_count"],
                parsed["lang"],
            )

            if search_context:
                # Disable Native Web Search
                if "features" not in body:
                    body["features"] = {}

                body["features"]["web_search"] = False
                body["features"]["retrieval"] = False

                # Construct System Instruction
                instr = (
                    f"Search Query: {self.ctx.model.user_query}\n\n"
                    f"INSTRUCTION: Answer the query above using ONLY the provided search results.\n"
                    f"CRITICAL: You MUST write your response in the EXACT SAME LANGUAGE used in the 'Search Query' above. Do not use the language of the search results or system prompts.\n"
                    f"Always cite sources using [1], [2] format.\n\n"
                    f"--- SEARCH RESULTS ---\n{search_context}"
                )

                # PRESERVE SYSTEM PROMPTS
                preserved_messages = [
                    msg for msg in msg_list if msg.get("role") == "system"
                ]

                # Reconstruct history
                body["messages"] = preserved_messages + [
                    {"role": "user", "content": instr}
                ]

                self.ctx.model.executed = True
                self.debug.log(
                    f"Search executed. Preserved {len(preserved_messages)} system messages."
                )

                await self.em.emit_status("Thinking...", False)

        except Exception as e:
            await self.debug.error(e)

        return body

    async def outlet(
        self, body: dict, __user__: dict = None, __event_emitter__=None  # type: ignore
    ) -> dict:
        """Process the outgoing response and restore web search state."""
        try:
            if self.ctx and self.ctx.model.executed:
                # Restore original web search feature state
                if "features" in body:
                    body["features"]["web_search"] = self.ctx.model.web_search_original
                    body["features"]["retrieval"] = self.ctx.model.retrieval_original

                # Handle Output & Debug
                if "messages" in body and len(body["messages"]) > 0:
                    last_msg = body["messages"][-1]
                    content = last_msg.get("content", "")
                    debug_out = self.debug.emit()

                    if isinstance(content, str):
                        last_msg["content"] += debug_out
                    elif isinstance(content, list) and debug_out:
                        content.append({"type": "text", "text": debug_out})
                        last_msg["content"] = content

                self.debug.log("--- OUTLET COMPLETE ---")
                await self.em.emit_status("EasySearch completed", True)

        except Exception as e:
            print(f"EasySearch Outlet Error: {e}")

        finally:
            self.ctx = None

        return body
