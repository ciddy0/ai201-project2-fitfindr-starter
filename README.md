# FitFindr

FitFindr is an AI-powered thrift shopping assistant that searches secondhand clothing listings, suggests outfits using your existing wardrobe, and generates shareable social media captions. It runs as a Gradio web app backed by three chained tools orchestrated through a planning loop. To run it: `pip install -r requirements.txt`, add your `GROQ_API_KEY` to a `.env` file, then `python app.py`.

---

## Tool Inventory

### Tool 1: `search_listings`

**What it does:** Searches a dataset of 40 mock secondhand clothing listings for items matching a keyword description, with optional size and price filters. Results are ranked by keyword relevance.

**Inputs:**

| Parameter     | Type             | Description                                                                 |
|---------------|------------------|-----------------------------------------------------------------------------|
| `description` | `str`            | Keywords describing what the user wants (e.g., `"vintage graphic tee"`)     |
| `size`        | `str \| None`    | Size to filter by (case-insensitive substring match), or `None` to skip     |
| `max_price`   | `float \| None`  | Maximum price in dollars (inclusive), or `None` to skip                      |

**Output:** A `list[dict]` of matching listings sorted by relevance score (highest first). Each dict contains: `id`, `title`, `description`, `category`, `style_tags` (list of strings), `size`, `condition`, `price` (float), `colors` (list of strings), `brand`, and `platform`. Returns an empty list if nothing matches.

**Purpose in agent workflow:** This is the first tool called. Its output populates `session["search_results"]`. If the list is empty, the agent exits early without calling the remaining tools.

---

### Tool 2: `suggest_outfit`

**What it does:** Uses the Groq LLM (Llama 3.1 8B) to suggest 1-2 complete outfit combinations incorporating a thrifted item with pieces from the user's wardrobe. If the wardrobe is empty, it provides general styling advice instead.

**Inputs:**

| Parameter  | Type   | Description                                                                                     |
|------------|--------|-------------------------------------------------------------------------------------------------|
| `new_item` | `dict` | A listing dict (the item the user is considering) with fields like `title`, `description`, `category`, `colors`, `style_tags`, etc. |
| `wardrobe` | `dict` | A wardrobe dict with an `"items"` key containing a list of wardrobe item dicts. May be empty.    |

**Output:** A `str` containing LLM-generated outfit suggestions. When the wardrobe has items, the string names specific wardrobe pieces to pair with the new item. When the wardrobe is empty, it returns general styling advice describing what kinds of pieces and aesthetics pair well.

**Purpose in agent workflow:** Called after an item is selected from search results. Its string output is stored in `session["outfit_suggestion"]` and passed as input to `create_fit_card`.

---

### Tool 3: `create_fit_card`

**What it does:** Uses the Groq LLM (Llama 3.1 8B, temperature 0.9) to generate a 2-4 sentence social media caption for an outfit-of-the-day post featuring the thrifted item.

**Inputs:**

| Parameter  | Type   | Description                                                        |
|------------|--------|--------------------------------------------------------------------|
| `outfit`   | `str`  | The outfit suggestion string returned by `suggest_outfit()`        |
| `new_item` | `dict` | The listing dict for the thrifted item (used for title, price, platform) |

**Output:** A `str` containing a 2-4 sentence Instagram/TikTok caption that mentions the item name, price, and platform naturally. The caption is casual and authentic in tone. If the `outfit` string is empty or whitespace-only, returns the fallback string: `"Could not generate a caption - no outfit suggestion was provided."`

**Purpose in agent workflow:** The final tool in the pipeline. Its output is stored in `session["fit_card"]` and displayed in the Gradio UI's third panel.

---

## Planning Loop

The agent uses a **`while` loop with a `_decide_next_step(session)` function** that inspects the session dict each iteration and dynamically selects which tool to call next. Rather than executing tools in a hardcoded sequence, the decision function checks what data has been populated so far and returns the appropriate next action (`"parse"`, `"search"`, `"suggest"`, `"create"`, or `"done"`). If any step sets `session["error"]`, the decision function returns `"done"` on the next iteration and the remaining tools are never called.

### How `_decide_next_step` works

```python
def _decide_next_step(session: dict) -> str:
    if not session["parsed"]:
        return "parse"
    if not session["search_results"] and session["error"] is None:
        return "search"
    if session["selected_item"] and session["outfit_suggestion"] is None and session["error"] is None:
        return "suggest"
    if session["outfit_suggestion"] and session["fit_card"] is None and session["error"] is None:
        return "create"
    return "done"
```

### Loop execution

1. **Initialize session**: `_new_session(query, wardrobe)` creates the session dict with all fields set to defaults.

2. **Enter `while True` loop**: Each iteration calls `_decide_next_step(session)`.

3. **`"parse"`** — `session["parsed"]` is empty → call `_parse_query(session)`. Regex extracts `description`, `size`, and `max_price` from the raw query.

4. **`"search"`** — Parsed data exists, no search results yet, no error → call `search_listings()`.
   - If results are empty: sets `session["error"]`. Next iteration, `_decide_next_step` sees the error and returns `"done"` — `suggest_outfit` and `create_fit_card` are never called.
   - If results exist: sets `session["selected_item"]` to the top result.

5. **`"suggest"`** — Selected item exists, no outfit suggestion yet → call `suggest_outfit()` with the selected item and wardrobe. Internally, this tool branches based on whether the wardrobe is empty (general advice) or populated (specific outfit combinations).

6. **`"create"`** — Outfit suggestion exists, no fit card yet → call `create_fit_card()` with the outfit suggestion and selected item.

7. **`"done"`** — All fields populated or error set → loop breaks, session is returned. The Gradio app checks `session["error"]` first; if `None`, it displays the listing, outfit suggestion, and fit card in three panels.

---

## State Management

All inter-tool communication flows through a single **session dict**, created by `_new_session()` at the start of each interaction. There is no global state and no persistence between interactions.

### Session dict fields

| Field               | Type                | Set in step | Description                                      |
|---------------------|---------------------|-------------|--------------------------------------------------|
| `query`             | `str`               | Init        | Original user query                              |
| `parsed`            | `dict`              | Step 2      | Extracted `description`, `size`, `max_price`     |
| `search_results`    | `list[dict]`        | Step 3      | Matching listing dicts from `search_listings`    |
| `selected_item`     | `dict \| None`      | Step 4      | The top-ranked listing dict                      |
| `wardrobe`          | `dict`              | Init        | User's wardrobe with `"items"` key               |
| `outfit_suggestion` | `str \| None`       | Step 5      | String returned by `suggest_outfit`              |
| `fit_card`          | `str \| None`       | Step 6      | String returned by `create_fit_card`             |
| `error`             | `str \| None`       | Step 3      | Set if the interaction ended early; otherwise `None` |

### Data flow between tools

```
search_listings reads session["parsed"]
        |
        v
session["search_results"] -> session["selected_item"] (top result)
        |
        v
suggest_outfit reads session["selected_item"] + session["wardrobe"]
        |
        v
session["outfit_suggestion"]
        |
        v
create_fit_card reads session["outfit_suggestion"] + session["selected_item"]
        |
        v
session["fit_card"]
```

Each tool reads only the fields it needs and writes to its own designated field. The session dict is the single source of truth and is returned as the final output.

---

## Error Handling

### 1. `search_listings` - no results found

**Failure mode:** The user's query is too specific and no listings match (e.g., filtering by an extreme size, very low price, or niche description).

**Agent response:** Sets `session["error"]` to: *"No matching listings found for your search. Try broadening your description, removing the size or price filter, or searching for a different item."* Returns the session immediately. `suggest_outfit` and `create_fit_card` are never called. The Gradio UI shows this message in the listing panel with the other two panels empty.

**How to trigger:** Enter `designer ballgown size XXS under $5` in the search box and click "Find it". No listing in the dataset matches all three constraints (niche description + extreme size + very low price), so `search_listings` returns an empty list. The agent exits early and the UI displays:

```
Top listing found:  "No matching listings found for your search. Try broadening
                     your description, removing the size or price filter, or
                     searching for a different item."
Outfit idea:        (empty)
Your fit card:      (empty)
```

### 2. `suggest_outfit` - empty wardrobe

**Failure mode:** The user has no wardrobe items (`wardrobe["items"]` is an empty list), so the tool cannot reference specific pieces for outfit combinations.

**Agent response:** The tool detects the empty wardrobe and switches to an alternative LLM prompt that asks for general styling advice: what kinds of pieces pair well, what vibe the item fits, and what occasions it suits. The agent stores this general advice in `session["outfit_suggestion"]` and continues normally to `create_fit_card`. No exception is raised.

**How to trigger:** Select **"Empty wardrobe (new user)"** from the Wardrobe radio button, enter any valid query like `vintage graphic tee under $30`, and click "Find it". The listing panel shows a result normally, but the Outfit idea panel contains general styling advice (e.g., "this boxy tee pairs well with wide-leg pants and chunky shoes") instead of naming specific wardrobe pieces.

### 3. `create_fit_card` - empty outfit string

**Failure mode:** The `outfit` parameter is an empty string or contains only whitespace (e.g., if `suggest_outfit` somehow returned no content).

**Agent response:** The tool returns the fallback string: *"Could not generate a caption - no outfit suggestion was provided."* This is stored in `session["fit_card"]` and the session is returned normally. No exception is raised.

**How to trigger:** Call `create_fit_card` directly in a Python shell:

```python
from tools import create_fit_card
result = create_fit_card("", {"title": "Test", "price": 10, "platform": "depop"})
print(result)
# Output: "Could not generate a caption - no outfit suggestion was provided."
```

This cannot be triggered through the Gradio UI under normal conditions because `suggest_outfit` always returns a non-empty string. The guard exists as a defensive check.

---

## Spec Reflection

**How the spec helped:** The architecture diagram in `planning.md` made the session dict data flow explicit before any code was written. Mapping out the `_decide_next_step` decision function and which session fields each tool reads/writes made the `while` loop implementation straightforward — each branch in the loop body corresponds directly to a step in the spec.

**How the implementation diverged:** The planning.md spec originally described a "hybrid regex + LLM fallback" approach for query parsing, where the agent would call the Groq LLM if regex failed to extract all parameters. The actual implementation uses regex-only parsing since the regex patterns handle all expected query formats (price with "under/below/less than", size with "size X", and description as the remaining text). The LLM fallback was unnecessary complexity for the input patterns the app encounters.

---

## AI Usage

### Instance 1: Implementing `run_agent()`

**What I provided to AI:** The complete Planning Loop section from `planning.md` (the `while` loop with `_decide_next_step` decision function), the State Management section (session dict structure and data flow), the architecture diagram, the `_new_session()` function from `agent.py`, and the function signatures of all three tools from `tools.py`.

**What AI generated:** The full `run_agent()` implementation with the `while True` planning loop, the `_decide_next_step(session)` function that inspects session state to dynamically select the next tool, the `_parse_query(session)` helper for regex-based query parsing, and the loop body with branches for each step (`"parse"`, `"search"`, `"suggest"`, `"create"`, `"done"`).

**What I reviewed and revised:** Verified the regex parsing handles edge cases. Checked that `"under $30"` correctly extracts `30.0`, that `"size M"` extracts `"M"` (uppercased), and that filler phrases like "I'm looking for a" are stripped from the description. Confirmed that when `search_listings` returns empty, `session["error"]` is set and `_decide_next_step` returns `"done"` on the next iteration, preventing downstream tools from being called.

### Instance 2: Implementing `handle_query()`

**What I provided to AI:** The `app.py` stub file with the `handle_query()` docstring (which specified the empty-query guard, wardrobe selection, `run_agent()` call, error check, and listing formatting), plus the session dict structure from `planning.md`.

**What AI generated:** The complete `handle_query()` function including the empty-query guard, wardrobe selection based on the radio button choice, the `run_agent()` call, the error-path return, and the listing formatting string that displays title, price, size, condition, platform, brand, tags, and description.

**What I reviewed and revised:** Checked the listing format output to ensure all relevant fields from the listing dict are included (title, price, size, condition, platform, brand, style_tags, description). Verified the error path returns the error message in the first panel with empty strings for the other two panels, matching the Gradio UI's three-output structure.

---

## Demo Video

A separate demo video walkthrough is required as part of the project submission and is not included in this README.
