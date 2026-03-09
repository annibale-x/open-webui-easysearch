## 🌐 EasySearch v0.3.4: High-Performance Web Search Filter

An intelligent, context-aware web search filter for Open WebUI. EasySearch bypasses noisy standard web scrapers, utilizing parallel fetching, structural HTML cleaning, and dynamic context-awareness to feed your LLM only the highest quality data.

[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-181717?logo=github&logoColor=white)](https://github.com/annibale-x/open-webui-easysearch)
![Open WebUI Plugin](https://img.shields.io/badge/Open%20WebUI-Plugin-blue?style=flat&logo=openai)
![License](https://img.shields.io/github/license/annibale-x/open-webui-easysearch?color=green)

---

### 🆕 What's New in v0.3.4
- **Documentation Update**: Added **Troubleshooting & FAQ** section.
- **Fail-Fast Global Check**: Added immediate validation of Open WebUI's global Web Search toggle at startup to prevent unnecessary LLM processing if disabled.
- **Fixed Dual-Language Syntax (`??:src>dest`):** to decouple the search language from the response language.
- **Linguistic Precision:** Improved "Smart Default" logic with a dedicated Language Anchor. Separating the search intent from the conversational language is now more accurate.
- **Binary Scrubber:** Upgraded text cleaning engine that automatically detects and skips binary files (.pdf, .docx, .zip) and annihilates Unicode junk characters from dirty web sources.
- **Oversampling Pool Injection:** All retrieved search snippets from unread pages are now fed directly to the LLM providing massive signal density.

---

### ✨ Main Features

- **Independent Execution (No Setup Required):** EasySearch works entirely out of the box. You **do not** need to enable Open WebUI's native web search toggle or attach any tools to your model. The filter operates independently and seamlessly hijacks the prompt when triggered.
- **Deep Contextual Awareness:** Automatically analyzes your recent conversation history to infer exactly what you want to search for, allowing for zero-prompt searches using just the `??` trigger.
- **Multi-Modifier Syntax:** Chain modifiers effortlessly to dictate search behavior. Force specific languages, context depth, and result limits on the fly (e.g., `??:en:10:c3`).
- **Pure Text Extraction:** Utilizes `lxml` for surgical HTML cleaning. It strips away useless navigation menus, cookie banners, and footers, feeding the LLM only the pure, relevant article text to save tokens and improve accuracy.
- **Anti-Scraping Stealth & Resilience:** Concurrently fetches pages while rotating through 20 unique browser User-Agents. If a website blocks the request (403 Forbidden), the "Gap-Filler" mechanism automatically fetches backup links in the background.
- **RAG & Context Lockdown:** Temporarily disables native document retrieval (RAG) and standard searches during its execution round to prevent Open WebUI from polluting the prompt with conflicting background data.

---

### 🚀 At a Glance: Killer Features & Use Cases

Standard LLM web searches often just read brief "snippets" from Google or get confused by navigation menus on websites. EasySearch is built differently. Here is what it can do for you:

#### 1. The "Zero-Friction" Fact Check
You are discussing a complex topic and need real-world data without leaving the flow of the conversation.
* **You type:** `?? latest AI models released by Google in 2026`
* **What happens:** EasySearch hijacks the prompt, generates multiple optimal search queries, downloads the actual content of the top pages, strips away the junk (menus, cookie banners), and feeds the pure text to the LLM. You get a perfectly cited answer.

#### 2. The "I'm Too Lazy to Type" Search (Contextual Mode)
You and the Assistant just had a long debate about renewable energy. You want sources to back up the Assistant's last claim.
* **You type:** `??` (Just the trigger prefix, nothing else).
* **What happens:** EasySearch reads the recent conversation history, understands the context, automatically formulates the perfect query (e.g., "solar panel efficiency statistics 2026"), and fetches the sources. 

#### 3. The "Polyglot Researcher" (Dual-Language)
You are chatting in Italian, but you need reliable technical documentation that is mostly written in English.
* **You type:** `??:en>it pianificazione prossime missioni lunari`
* **What happens:** The `:en>it` modifier tells EasySearch to generate English queries and fetch English websites, while strictly forcing the LLM to synthesize the final answer back into Italian.

#### 4. The "Deep Dive Report"
You need a comprehensive analysis, not just a quick answer.
* **You type:** `??:20 global warming ocean temperature impact`
* **What happens:** The `:20` modifier tells EasySearch to concurrently fetch and read **20 different websites**, deduplicate them, and build a massive, clean context window for the LLM to write a highly detailed report.

---

### 💡 Usage & Command Schema

The default trigger is `??`. You can type the trigger alone or follow it with a query. You can also append **modifiers** using a colon (`:`). Modifiers can be chained in **any order**.

| Command Syntax | Description | Example |
| :--- | :--- | :--- |
| `?? <query>` | **Standard Search**: Searches the web for your specific query. Response matches the prompt language. | `?? best pizza in Rome` |
| `??` | **Context Search**: Auto-generates a query based on the chat history. Response matches the chat language. | `??` |
| `??:<count>` | **Result Modifier**: Forces the system to read exactly `N` pages. | `??:10 quantum computing` |
| `??:<lang>` | **Full Language Lock**: Forces the search, the results, AND the model response to be in the specified language. | `??:de` (Search DE, Answer DE) |
| `??:<src>><dest>`| **Dual-Language Modifier**: Decouples the search language from the response language. | `??:en>it quantum computing`  (Search EN, Answer IT)|
| `??:c<count>` | **Context Modifier**: Tells the system how many previous messages to read when generating an automatic query. | `??:c3` (reads last 3 messages) |
| **Combined** | Modifiers can be stacked effortlessly. | `??:15:fr:c2 latest news` |

> ℹ️ **Note on Context Modifier (`:cN`)**
> If you use the empty trigger `??`, EasySearch looks at the last message to figure out what to search. By adding `:c3`, you tell it to look at the last 3 messages to get a broader understanding of the topic before searching.

---

### 🔧 Configuration Parameters (Valves)

EasySearch is highly customizable. Administrators can set global safety limits, while users can tweak their personal experience.

> ℹ️ **Note on Global Configuration**
> Even though EasySearch handles scraping independently, it still requires the global **Web Search** engine to be enabled in the **Admin Panel** to fetch the initial list of results.

**User Valves (Personal Preferences)**

| Valve | Default | Description |
| :--- | :---: | :--- |
| **Search Prefix** | `??` | Your personal trigger. You can change this to `search:` or `/w` if you prefer. |
| **Default Context Count** | `1` | The default number of previous chat messages to analyze when you use the empty `??` trigger without a `:cN` modifier. |
| **Auto Recovery Fetch** | `False` | Enables the "Gap-Filler". If a site blocks the scraper, the filter will automatically try to fetch backup links to ensure you get the requested number of pages. |

**Admin Valves (System Limits & Tuning)**

| Valve | Default | Description |
| :--- | :---: | :--- |
| **Max Search Queries** | `3` | How many different search variations the LLM should generate from the user's prompt to ensure broad coverage. |
| **Results Per Query** | `5` | Minimum number of search engine results to fetch per generated query. |
| **Max Total Results** | `20` | A hard safety cap. Even if a user requests `??:50`, the system will not exceed this number to prevent server overload. |
| **Search Timeout** | `8` | Time (in seconds) to wait for a website to respond before giving up. |
| **Max Download MB** | `1` | Anti-flood protection. Maximum Megabytes to download per single web page. |
| **Max Result Length** | `4000` | Maximum number of characters to keep per scraped article. Prevents blowing up the LLM's context window. |
| **Oversampling Factor** | `2` | Multiplier for search requests. If set to 2, and the target is 10 pages, EasySearch fetches 20 links from the search engine, deduplicates them, and only downloads the top 10 valid ones. |

---

### 🛠️ Under the Hood: For Sysadmins & Power Users

EasySearch isn't just a basic web scraper; it operates as a sophisticated pipeline interceptor designed to fix the common pitfalls of native LLM web searches.

#### 1. LXML Structural Cleaning
Most native web search tools (including Open WebUI's default) use basic HTML parsing (like `BeautifulSoup`'s default parser) which leaves behind navigation menus, footer links, and cookie banners. This wastes tokens and confuses the LLM. 
EasySearch enforces the use of `lxml` to evaluate the DOM structurally via XPath, surgically amputating `<nav>`, `<aside>`, `<footer>`, and `<script>` tags before the text is even processed.

#### 2. RAG & Native Search Lockdown (Shadow Bypass)
When EasySearch triggers, it doesn't just add text to the prompt. It actively intercepts the Open WebUI pipeline and injects a `ShadowRequest`. 
Once the search context is built, EasySearch dynamically forces `body["features"]["web_search"] = False` and `body["features"]["retrieval"] = False` for the current round. 
**Why?** This prevents Open WebUI's native Web Search or Document RAG (Vector DB) from firing simultaneously and polluting the context window with overlapping or conflicting data. The original states are safely restored in the `outlet` pipeline.

#### 3. Advanced Anti-Scraping & Concurrency
Websites increasingly block bots with `403 Forbidden` errors. EasySearch combats this by:
* Stripping tracking parameters (`utm_source`, `gclid`) from URLs to improve deduplication.
* Utilizing `httpx` to fetch URLs concurrently, drastically reducing wait times.
* Rotating through a carefully curated list of 20 unique, modern browser User-Agents (Windows, macOS, Linux, iOS, Android) per request.

#### 4. The Gap-Filler (Auto-Recovery)
If the user requests 10 pages, but 3 of them result in timeouts or 403s, traditional scrapers return only 7 results. If `Auto Recovery Fetch` is enabled, EasySearch detects the gap and dynamically executes a secondary parallel fetch utilizing the "leftovers" from the Oversampling pool, guaranteeing the requested payload size.

---

### 💡 Advanced Pro-Tips for Power Users

Master the advanced logic of EasySearch to get high-quality data even from difficult sources.

#### 🌐 Dynamic Language Routing (The `src>dest` Pattern)
EasySearch 0.3.1 supports sophisticated language handling:
* **Trigger:** `??` -> Infers intent from history. The response language is automatically anchored to the conversation.
* **Trigger:** `??:de` -> Forces both the **Search** and the **Response** into German.
* **Trigger:** `??:en>de` -> Separates the concerns: *"Search in English (EN) for better sources, but respond in German (DE)"*.
* **Smart Language Anchor:** When using context-aware triggers (`??`), EasySearch uses a specialized "Reference Anchor" to ensure the model doesn't get confused by foreign search results and sticks to your conversational language.

#### 🚀 Overcoming "Scraping Imbalance"
If a model claims "no relevant results found" even when citations are visible:
* **The Cause:** High-authority sites often block scrapers. If Source 1 is blocked and Source 3 is open but irrelevant, the LLM might get distracted by the "noise".
* **The Solution:** Use the `:count` modifier to increase the sample size (e.g., `??:15`). EasySearch automatically injects the **Search Snippets** of the unread pages into the context, guaranteeing a massive signal density even if the main pages fail to load.

#### 🧠 Contextual "Lazy" Searching with Depth
You can control how much history EasySearch analyzes to build its automatic query.
* **Command:** `??:c5`
* **Why it works:** By default, ES looks at the last message. With `:c5`, it analyzes the last 5 exchanges to build a sophisticated query that understands the nuance of a long conversation.

#### 🧹 Token Optimization via Structural Cleaning
EasySearch isn't just a scraper; it's a "cleaner." 
* **Technical Detail:** It uses `lxml` to evaluate the DOM via XPath, surgically removing `<nav>`, `<footer>`, and `<script>` tags. 
* **The Result:** You can fit more sources into a single prompt without hitting the model's context limit, as only the **pure article text** is preserved.

---

### ‼️ Requirements

EasySearch relies on high-performance C-bindings for its structural HTML cleaning.
* **Requirement:** The `lxml` Python library must be installed in your environment.
* **Docker Users:** If you are running the official Open WebUI Docker image, `lxml` is already included. You are good to go.
* **Manual/Bare-Metal Users:** If you installed Open WebUI manually via `pip`, ensure `lxml` is present in your virtual environment (`pip install lxml`). If it is missing, EasySearch will explicitly halt and emit an error in the UI to prevent feeding dirty HTML to your models.

---

### ❓ Troubleshooting & FAQ

If EasySearch is not behaving as expected, please follow this guide based on the internal filter logic.

#### 1. The `??` command produces no status messages
If the LLM responds normally without showing "EasySearch" status updates (e.g., *Searching...* or *Reading pages...*), the filter was not triggered.
* **Filter Activation:** Make sure the "EasySearch" filter is globally enabled or at least enabled for the model currently in use.
* **Syntax Check:** The trigger must be at the very beginning of the message and must be followed by a space if a query is provided.
    * ✅ **Correct:** `?? weather in Rome`
    * ❌ **Incorrect:** `Hey, ?? weather...` or `??weather...` (missing space).

#### 2. Error: "Global Web Search is OFF"
EasySearch performs a deterministic check at startup to ensure the environment is ready. If you see this error:
* `❌ The global Web Search "Master Switch" in the Open WebUI Admin settings is disabled.`
* **Solution:** Navigate to `Admin Panel -> Settings -> Web Search`, turn the main **Web Search** toggle **ON**, and click **Save**. EasySearch requires the base engine (SearXNG, Google PSE, etc.) to fetch the initial list of results before it can perform its deep-cleaning and fetching.

#### 3. The model responds in the wrong language
EasySearch implements a **Language Anchor** system to prevent "language drifting" caused by foreign search results.
* **Behavior:** When using an empty trigger (`??`), the filter automatically anchors the response to the language used in your last message (`msg_list[-2]`).
* **Solution:** If the model still gets confused by foreign content, use the explicit dual-modifier (e.g., `??:en>it`) to strictly separate the search engine language from the final synthesis language.

#### 4. Message: "No results found"
* **Cause:** Your configured search engine in OWUI returned no valid links, or all discovered links were binary files (PDF, DOCX, ZIP) which are automatically discarded by the Binary Scrubber for security and token efficiency.
* **Tip:** Verify that your search engine (e.g., SearXNG or Firecrawl) is functional outside of EasySearch. If sites are blocking the scraper, increase the result count (e.g., `??:15`) to force the injection of **Search Snippets** as a fallback.

#### 5. How to provide logs for bug reports
If you encounter a persistent issue, please enable the **Debug** valve in the EasySearch function settings.
* Run the search again to capture the error details.
* **Admins:** Check your Docker container logs for lines starting with `⚡ EasySearch DEBUG:`.
* **Users:** Expand the **🔍 EasySearch Debug** dropdown at the bottom of the LLM's response and copy the JSON payload.
* [Open an issue on GitHub](https://github.com/annibale-x/open-webui-easysearch/issues) and attach these logs along with your Open WebUI version.

---

### 🐞 Bug Reports & Feedback

If you experience anomalies, unexpected crashes, or have ideas for new modifiers and features, community feedback is highly appreciated. 

**Found a bug or want to suggest an improvement?** Please [open an issue on GitHub](https://github.com/annibale-x/open-webui-easysearch/issues).
