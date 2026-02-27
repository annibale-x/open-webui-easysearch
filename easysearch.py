"""
title: 🌐 EasySearch
version: 0.1.5
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

        # Resolve Search Prefix (User Preference > Admin Default)
        prefix = self.user_valves.search_prefix
        if not prefix:
            prefix = self.valves.search_prefix

        # Build Unified Configuration Model
        self.model = Store(
            {
                # --- Configuration (Merged) ---
                "search_prefix": prefix,
                "max_search_queries": self.valves.max_search_queries,
                "search_results_per_query": self.valves.search_results_per_query,
                "max_total_results": self.valves.max_total_results,  # New Valve
                "max_download_bytes": self.valves.max_download_mb
                * 1024
                * 1024,  # Convert MB to Bytes
                "max_result_length": self.valves.max_result_length,
                "debug": self.valves.debug or self.user_valves.debug,
                # --- Runtime State ---
                "user_query": "",
                "executed": False,
                "web_search_original": False,
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

    async def search(self, query: str, model: str, result_count: int) -> Optional[str]:
        """
        Main entry point.
        :param result_count: Number of actual web pages to fetch and read (N).
        """
        try:
            # Clamp result_count to max_total_results (Safety Cap)
            max_cap = self.cfg.max_total_results
            final_count = min(result_count, max_cap)

            self.log(
                f"Starting search cycle. Requested: {result_count}, Max Cap: {max_cap}, Final Target: {final_count}"
            )

            # 1. Generate Queries (Limit from Config)
            gen_count = self.cfg.max_search_queries
            await self.em.emit_status("Generating Search Queries", False)
            queries = await self._generate_queries(query, model, gen_count)

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

    async def _generate_queries(self, text: str, model: str, count: int) -> List[str]:
        """Uses LLM to expand the user request into multiple search queries."""
        try:
            prompt = QUERY_GENERATION_TEMPLATE.format(
                COUNT=count, DATE=datetime.date.today(), REQUEST=text
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
        Calls Open WebUI search using a Shadow Request.
        Overrides:
        - BYPASS_WEB_SEARCH_WEB_LOADER: True (to use our internal fetcher)
        - WEB_SEARCH_RESULT_COUNT: Dynamic (max of config default or user target)
        """
        try:
            # Dynamic Calculation:
            # If user wants 10 pages (target_count), we must ask for AT LEAST 10 results per query
            # to ensure we have enough candidates even if only 1 query is generated.
            # We use the maximum of (Configured Default, User Target).
            count_per_query = max(self.cfg.search_results_per_query, target_count)

            self.log(
                f"Executing Shadow Request. Overriding Result Count (Per Query) to: {count_per_query}"
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

    async def _fetch_concurrently(self, urls: List[str]) -> Dict[str, str]:
        """
        Fetches multiple URLs in parallel using HTTPX with streaming and size limit.
        """
        if not HTTPX_AVAILABLE or not urls:
            return {}

        results = {}
        verify_ssl = os.environ.get("REQUESTS_CA_BUNDLE", True)
        if verify_ssl == "":
            verify_ssl = True

        # Use configured limit from unified model
        max_bytes = self.cfg.max_download_bytes
        self.log(f"Fetching {len(urls)} URLs with limit {max_bytes} bytes/page")

        timeout = httpx.Timeout(8.0, connect=5.0)
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        async def fetch_single(client, url):
            try:
                req = client.build_request("GET", url)
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
                headers=headers,
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

    def _clean_with_lxml(self, raw_html: str) -> str:
        """
        Uses lxml to strip HTML tags, scripts, styles, and structural noise.
        """
        if not raw_html or not LXML_AVAILABLE:
            return ""

        try:
            tree = lxml_html.fromstring(raw_html)
            cleaner_xpath = "//script | //style | //nav | //footer | //header | //aside | //form | //iframe | //noscript | //div[contains(@class, 'menu')] | //div[contains(@class, 'footer')]"
            for element in tree.xpath(cleaner_xpath):
                element.drop_tree()
            text = tree.text_content()
            return text.strip()
        except Exception:
            return ""

    async def _process_results(self, results: Any, target_count: int) -> Optional[str]:
        """
        Parses results, fetches raw HTML in parallel, and builds context.
        Limits fetching to 'target_count' unique URLs.
        """
        if not isinstance(results, dict) or "items" not in results:
            return None

        raw_items = results["items"]
        if not raw_items:
            return None

        # --- DEDUPLICATION LOGIC START ---
        seen_urls = set()
        items = []
        dup = 0
        for item in raw_items:
            url = item.get("link", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                items.append(item)
            else:
                dup += 1
        # --- DEDUPLICATION LOGIC END ---

        self.log(
            f"Deduplication: {len(raw_items)} raw -> {len(items)} unique. Target: {target_count}"
        )

        # Slice items to target count BEFORE fetching
        items = items[:target_count]

        urls_to_fetch = []
        for item in items:
            url = item.get("link", "")
            if url:
                urls_to_fetch.append(url)
            await self.em.emit_citation(
                item.get("title", "Source"), item.get("snippet", ""), url
            )

        fetched_html_map = {}
        if HTTPX_AVAILABLE and LXML_AVAILABLE and urls_to_fetch:
            await self.em.emit_status(f"Deep reading {len(urls_to_fetch)} pages", False)
            fetched_html_map = await self._fetch_concurrently(urls_to_fetch)

        context_parts = []
        max_len = self.cfg.max_result_length  # Use unified config

        noise_pattern = re.compile(
            r"^(?:menu|home|search|sign in|log in|sign up|register|subscribe|newsletter|account|profile|cart|checkout|buy now|shop|close|cancel|skip to content|next|previous|back to top|privacy policy|terms|cookie|copyright|all rights reserved|legal|contact us|help|support|faq|social|follow us|share|facebook|twitter|instagram|linkedin|youtube|advertisement|sponsored|promoted|related posts|read more|loading|posted by|written by|author|category|tags)$",
            re.IGNORECASE,
        )

        for i, item in enumerate(items):
            url = item.get("link", "")
            title = item.get("title", "Source")
            text = ""

            if url in fetched_html_map:
                text = self._clean_with_lxml(fetched_html_map[url])

            if not text:
                text = item.get("snippet", "")

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
                f"--- Source {i+1}: {title} ---\nURL: {url}\nContent:\n{text}\n"
            )

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
        search_prefix: str = Field(
            default="??",
            description="Default Trigger prefix (Admin).",
            min_length=1,
            max_length=3,
        )
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
        debug: bool = Field(default=False)

    class UserValves(BaseModel):
        # User Preferences
        search_prefix: Optional[str] = Field(
            default=None,
            description="Custom Trigger prefix. Leave empty to use Admin default.",
            min_length=1,
            max_length=3,
        )
        debug: bool = Field(default=False)

    def __init__(self):
        self.valves, self.user_valves = self.Valves(), self.UserValves()
        self.request = self.debug = self.net = self.em = self.ctx = None

    def _parse_trigger(self, txt: str) -> Optional[dict]:
        """
        Parse input for trigger with optional numeric modifier.
        Syntax: '??' or '??N' (where N is int).
        Strict check: Must be followed by space or end of string.
        """
        # Resolve prefix (User > Admin)
        prefix = self.user_valves.search_prefix
        if not prefix:
            prefix = self.valves.search_prefix

        if not txt.startswith(prefix):
            return None

        # Remove prefix to get the "payload"
        payload = txt[len(prefix) :]

        # Default values
        # If no N is specified, default to Max Possible (Query Count * Results Per Query)
        # This ensures we fetch ALL candidates found by the search engine
        target_count = (
            self.valves.max_search_queries * self.valves.search_results_per_query
        )
        content = ""

        # Case 1: Empty payload (Just "??")
        if not payload:
            return {"is_search": True, "content": "", "target_count": target_count}

        # Case 2: Payload starts with space (Standard "?? query")
        if payload[0] == " ":
            content = payload.strip()
            return {"is_search": True, "content": content, "target_count": target_count}

        # Case 3: Payload starts with number (Modifier "??10 query")
        # Split by first space to isolate potential number
        parts = payload.split(" ", 1)
        potential_number = parts[0]

        if potential_number.isdigit():
            target_count = int(potential_number)
            if len(parts) > 1:
                content = parts[1].strip()
            else:
                content = ""  # "??10" (Context search with N pages)

            return {"is_search": True, "content": content, "target_count": target_count}

        # Case 4: Payload starts with text (Invalid "??query")
        # We want to ignore this to avoid false positives
        return None

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
        self.debug, self.em = (
            DebugService(self),
            EmitterService(__event_emitter__, self),
        )

        if TRACE:
            self.debug.dump(body, "Body")

        await self.em.emit_status("EasySearch initialized", False)

        # Phase 3: State Management
        # ConfigService is initialized here, merging Valves and UserValves
        self.ctx.model.web_search_original = body.get("features", {}).get(
            "web_search", False
        )
        content = parsed["content"]

        # Override default count if specified in trigger
        target_count = parsed["target_count"]

        # Phase 4: Context Resolution (Empty Trigger '??')
        if not content and len(msg_list) > 1:
            # Get the previous message (usually Assistant's output)
            prev_content = msg_list[-2].get("content", "")
            context_text = (
                prev_content[0].get("text", "")
                if isinstance(prev_content, list)
                else str(prev_content)
            )

            self.debug.log(
                f"Empty trigger detected. Using context: {context_text[:50]}..."
            )
            await self.em.emit_status("Extracting query from context", False)

            # Generate query from context
            content = await self._extract_query_from_context(
                context_text, body.get("model"), __user__["id"]
            )
            self.debug.log(f"Extracted Query: {content}")
            await self.em.emit_status(f"Searching {target_count} pages", False)

        self.ctx.model.user_query = content

        try:
            # Phase 5: Search Execution
            # Pass the unified ConfigService model (self.ctx.model) to handler
            search_handler = WebSearchHandler(
                self.request, __user__["id"], self.em, self.ctx.model, self.debug
            )

            # Execute Search Cycle (Generate -> Search -> Process)
            search_context = await search_handler.search(
                content, body.get("model"), target_count
            )

            if search_context:
                # Disable Native Web Search to prevent double-search
                if "features" not in body:
                    body["features"] = {}
                body["features"]["web_search"] = False

                # Construct System Instruction with Search Results
                instr = (
                    f"Search Query: {content}\n\n"
                    f"INSTRUCTION: Answer the query above using ONLY the provided search results/context below. "
                    f"Do not hallucinate or use prior conversation memory if unrelated.\n"
                    f"Always cite sources using [1], [2] format corresponding to the Source ID.\n\n"
                    f"--- SEARCH RESULTS ---\n{search_context}"
                )

                # WIPE HISTORY: Replace messages with the single search context message.
                # This prevents RAG pollution and ensures focus on the new data.
                body["messages"] = [{"role": "user", "content": instr}]

                self.ctx.model.executed = True
                self.debug.log("Search executed & History wiped.")

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
