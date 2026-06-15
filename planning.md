# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset (40 secondhand clothing items loaded from `data/listings.json` via `load_listings()`) and returns matching items filtered by keyword relevance, optional size, and optional price ceiling. Returns an empty list if nothing matches — does not raise an exception.

**Input parameters:**

- `description` (str): Keywords describing what the user is looking for. Used to score each listing by keyword overlap against the listing's `title`, `description`, `style_tags`, and `category` fields.
- `size` (str | None): Size string to filter by (e.g., "M", "L", "W30"), or `None` to skip size filtering. Matching is case-insensitive and uses substring matching (so "M" matches "S/M").
- `max_price` (float | None): Maximum price in dollars (inclusive), or `None` to skip price filtering.

**What it returns:**

Returns a list of matching listing dicts, sorted by relevance score (highest first). Each listing dict contains these fields:

```json
{
  "id": "lst_006",
  "title": "Graphic Tee — 2003 Tour Bootleg Style",
  "description": "Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.",
  "category": "tops",
  "style_tags": ["graphic tee", "vintage", "grunge", "streetwear", "band tee"],
  "size": "L",
  "condition": "good",
  "price": 24.00,
  "colors": ["black"],
  "brand": null,
  "platform": "depop"
}
```

**What happens if it fails or returns nothing:**

The agent sets `session["error"]` to a user-friendly message: "No matching listings found for your search. Try broadening your description, removing the size or price filter, or searching for a different item." The agent returns the session immediately and does NOT proceed to `suggest_outfit` or `create_fit_card` with empty input.

---

### Tool 2: suggest_outfit

**What it does:**
Given a specific thrifted listing item and the user's current wardrobe, uses the Groq LLM to suggest 1–2 complete outfit combinations that incorporate the new item with existing wardrobe pieces. If the wardrobe is empty, it provides general styling advice instead of referencing specific wardrobe items.

**Input parameters:**

- `new_item` (dict): A listing dict (the top search result the user is considering buying) — contains fields like `title`, `description`, `category`, `style_tags`, `colors`, `size`, `price`, and `platform`.
- `wardrobe` (dict): The user's wardrobe dict with an `"items"` key containing a list of wardrobe item dicts. Each wardrobe item has `id`, `name`, `category`, `colors`, `style_tags`, and `notes`. The `items` list may be empty.

**What it returns:**

Returns a **string** containing the LLM-generated outfit suggestions. If the wardrobe has items, the string names specific wardrobe pieces to pair with the new item (e.g., "Pair this with your baggy straight-leg jeans and chunky white sneakers"). If the wardrobe is empty, it returns general styling advice for the item (e.g., "This boxy graphic tee pairs well with wide-leg pants and chunky shoes for a 90s grunge vibe").

**What happens if it fails or returns nothing:**

If `wardrobe["items"]` is empty, the tool switches to an alternative LLM prompt that asks for general styling ideas (what kinds of pieces pair well, what aesthetic the item fits) rather than raising an exception or returning an empty string. The agent stores whatever string is returned in `session["outfit_suggestion"]` and continues normally to `create_fit_card`.

---

### Tool 3: create_fit_card

**What it does:**
Generates a short, shareable 2–4 sentence outfit caption suitable for social media (Instagram/TikTok OOTD post). Uses the Groq LLM at a higher temperature (~0.9) to produce varied, authentic-sounding output that differs each time for different inputs.

**Input parameters:**

- `outfit` (str): The outfit suggestion string returned by `suggest_outfit()` — describes how the item fits into a complete look.
- `new_item` (dict): The listing dict for the thrifted item — used to pull in the item's title, price, and platform for the caption.

**What it returns:**

Returns a 2–4 sentence string usable as a social media caption. The caption:
- Feels casual and authentic (like a real OOTD post, not a product description)
- Mentions the item name, price, and platform naturally (once each)
- Captures the outfit vibe in specific terms
- Sounds different each time for different inputs (high LLM temperature)

**What happens if it fails or returns nothing:**

If the `outfit` string is empty or whitespace-only, the tool returns a descriptive error message string: "Could not generate a fit card, no outfit suggestion was provided." It does NOT raise an exception. The agent stores this fallback string in `session["fit_card"]` and returns the session.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**

The agent uses a **sequential pipeline with early-exit branching**. The three tools have a strict dependency chain: `search_listings` produces data needed by `suggest_outfit`, which produces data needed by `create_fit_card`, so the order is fixed. The only branching is an early-exit check after `search_listings` returns empty results.

**Step-by-step logic:**

1. **Initialize session** — Call `_new_session(query, wardrobe)` to create the session dict with all fields set to defaults (empty lists, None values).

2. **Parse the user query** — Use a hybrid approach: first try regex patterns to extract structured parameters, then fall back to an LLM call via Groq if regex doesn't find all parameters.

3. **Call `search_listings()`**, Pass `session["parsed"]["description"]`, `session["parsed"]["size"]`, and `session["parsed"]["max_price"]`.
   - Store results in `session["search_results"]`.
   - **BRANCH — If `session["search_results"]` is empty:** Set `session["error"]` to "No matching listings found for your search. Try broadening your description, removing the size or price filter, or searching for a different item." **Return the session immediately.** Do not proceed to steps 4–6.

4. **Select top result** — Set `session["selected_item"] = session["search_results"][0]` (the highest-relevance listing).

5. **Call `suggest_outfit()`** — Pass `session["selected_item"]` and `session["wardrobe"]`. Store the returned string in `session["outfit_suggestion"]`.

6. **Call `create_fit_card()`** — Pass `session["outfit_suggestion"]` and `session["selected_item"]`. Store the returned string in `session["fit_card"]`.

7. **Return the session** — The completed session dict now contains all results. The caller (Gradio app's `handle_query()`) checks `session["error"]` first; if it is `None`, it displays the selected item, outfit suggestion, and fit card in three panels.

**How the agent knows it's done:** The pipeline always terminates at step 7 (success) or at the early-exit branch in step 3 (no results).

---

## State Management

**How does information from one tool get passed to the next?**

All state lives in a single Python dictionary called the **session dict**, created at the start of each interaction by `_new_session()`. Every tool reads its inputs from this dict and writes its outputs back to it. There is no global state and no persistence between interactions.

**Session dict structure:**

```python
{
    "query": str,              # Original user query, set at initialization
    "parsed": {                # Set in step 2 (query parsing)
        "description": str,    #   Keywords for search (e.g., "vintage graphic tee")
        "size": str | None,    #   Size filter or None
        "max_price": float | None  # Price ceiling or None
    },
    "search_results": list[dict],     # Set in step 3 — list of matching listing dicts
    "selected_item": dict | None,     # Set in step 4 — the top listing dict
    "wardrobe": dict,                 # Set at initialization — user's wardrobe with "items" key
    "outfit_suggestion": str | None,  # Set in step 5 — string from suggest_outfit
    "fit_card": str | None,           # Set in step 6 — string from create_fit_card
    "error": str | None,              # Set if interaction ended early (e.g., no search results)
}
```

**Data flow between tools:**

- `search_listings` reads from `session["parsed"]` → writes to `session["search_results"]`
- Planning loop reads `session["search_results"][0]` → writes to `session["selected_item"]`
- `suggest_outfit` reads from `session["selected_item"]` + `session["wardrobe"]` → writes to `session["outfit_suggestion"]`
- `create_fit_card` reads from `session["outfit_suggestion"]` + `session["selected_item"]` → writes to `session["fit_card"]`

Each tool only accesses what it needs and writes to its own designated field. The session dict is the single source of truth and is returned as the final output.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool            | Failure mode                          | Agent response |
| --------------- | ------------------------------------- | -------------- |
| search_listings | No results match the query            | Set `session["error"]` to "No matching listings found for your search. Try broadening your description, removing the size or price filter, or searching for a different item." Return the session immediately without calling `suggest_outfit` or `create_fit_card`. The Gradio UI displays this message in the listing panel with empty outfit and fit card panels. |
| suggest_outfit  | Wardrobe is empty                     | The tool detects `wardrobe["items"]` is empty and switches to an alternative LLM prompt asking for general styling advice (e.g., "What kinds of pieces pair well with this item? What aesthetic does it fit?") instead of referencing specific wardrobe items. The agent stores the general advice string in `session["outfit_suggestion"]` and continues normally to `create_fit_card`. |
| create_fit_card | Outfit input is missing or incomplete | The tool checks if the `outfit` string is empty or whitespace-only. If so, it returns a fallback string: "Could not generate a fit card — no outfit suggestion was provided." The agent stores this in `session["fit_card"]` and returns the session. No exception is raised. |

---

## Architecture

```
                  FitFindr Agent Architecture
                  ===========================

User Query ──► [ run_agent(query, wardrobe) ]
                        │
                        ▼
               ┌─────────────────┐
               │  1. INIT SESSION │  _new_session(query, wardrobe)
               │     session = {} │  Sets defaults for all fields
               └────────┬────────┘
                        │
                        ▼
               ┌──────────────────────┐
               │  2. PARSE QUERY       │  Hybrid: regex first, LLM fallback
               │  "vintage tee <$30"  │  ──► {"description": "vintage graphic tee",
               │                      │       "size": null, "max_price": 30.0}
               │  session["parsed"]   │
               └────────┬─────────────┘
                        │
                        ▼
               ┌──────────────────────┐
               │  3. SEARCH LISTINGS   │  search_listings(desc, size, max_price)
               │  Filter + score from │  ──► list[dict] sorted by relevance
               │  listings.json (40)  │
               │  session["search_    │
               │       results"]      │
               └────────┬─────────────┘
                        │
                   ┌────┴────┐
                   │ Empty?  │
                   └─┬─────┬─┘
                 YES │     │ NO
                     ▼     ▼
          ┌──────────────┐  ┌──────────────────┐
          │ SET ERROR     │  │ 4. SELECT TOP    │  session["selected_item"]
          │ "No matching  │  │    RESULT        │     = search_results[0]
          │  listings..." │  └────────┬─────────┘
          └──────┬───────┘           │
                 │                   ▼
                 │          ┌────────────────────────┐
                 │          │ 5. SUGGEST OUTFIT       │  suggest_outfit(
                 │          │    LLM via Groq         │    selected_item, wardrobe)
                 │          │    session["outfit_     │  ──► string
                 │          │         suggestion"]    │
                 │          └────────┬───────────────┘
                 │                   │
                 │          ┌────────┴─────────┐
                 │          │ wardrobe empty?  │
                 │          └─┬──────────────┬─┘
                 │        YES │              │ NO
                 │            ▼              ▼
                 │   General styling    Specific outfits
                 │   advice (LLM)       from wardrobe (LLM)
                 │            \            /
                 │             ▼          ▼
                 │          ┌──────────────────────────┐
                 │          │ 6. CREATE FIT CARD       │  create_fit_card(
                 │          │   LLM via Groq (temp=0.9)│    outfit_suggestion,                    
                 │          │    session["fit_card"]   │    selected_item)
                 │          └────────┬─────────────────┘  ──► string (2-4 sentences)
                 │                   │
                 ▼                   ▼
          ┌──────────────────────────────┐
          │ 7. RETURN SESSION             │
          │    error path: error is set,  │
          │      outfit/fit_card are None │
          │    happy path: all fields set │
          └──────────────┬───────────────┘
                         │
                         ▼
               [ Gradio handle_query() ]
               Displays 3 panels:
               - Listing details
               - Outfit suggestion
               - Fit card caption
```

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

**Tool 1 (search_listings):**
- **Input to AI:** The Tool 1 spec from this planning.md (parameters with types, return format with all 11 listing fields, failure behavior), plus the `load_listings()` function signature from `utils/data_loader.py`, plus 2–3 sample listings from `data/listings.json` so the AI sees the data shape.

**Tool 2 (suggest_outfit):**
- **Input to AI:** The Tool 2 spec (parameters, string return type, empty wardrobe handling), the wardrobe schema from `data/wardrobe_schema.json`, one example listing dict, and the `_get_groq_client()` helper from `tools.py`..

**Tool 3 (create_fit_card):**
- **Input to AI:** The Tool 3 spec (parameters, caption style guidelines, error guard for empty outfit), the `_get_groq_client()` helper, and an example outfit suggestion string + listing dict.

**Milestone 4 — Planning loop and state management:**

- **Input to AI:** The complete Planning Loop section, State Management section, Architecture diagram, and Error Handling table from this planning.md. Also provide the `_new_session()` function from `agent.py` and the function signatures of all three tools from `tools.py`.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1: Initialize session and parse query**

The agent calls `_new_session(query, wardrobe)` where wardrobe is the example wardrobe (10 items including baggy straight-leg jeans, chunky white sneakers, black combat boots, etc.).

Then it parses the query using the hybrid approach. Regex finds `under $30` → `max_price = 30.0`. No explicit size like "size M" is found, so `size = None`. The remaining description keywords are extracted as `"vintage graphic tee"`.

Parsed result stored in `session["parsed"]`:
```json
{
  "description": "vintage graphic tee",
  "size": null,
  "max_price": 30.0
}
```

**Step 2: Call `search_listings("vintage graphic tee", None, 30.0)`**

The tool loads all 40 listings, filters out any with `price > 30.0`, then scores remaining listings by keyword overlap with "vintage graphic tee" against each listing's title, description, style_tags, and category.

Top results returned (sorted by relevance):
1. **lst_006** — "Graphic Tee — 2003 Tour Bootleg Style" — $24.00 on depop, size L, condition good. style_tags: graphic tee, vintage, grunge, streetwear, band tee. (High score: matches "graphic", "tee", "vintage")
2. **lst_033** — "Vintage Band Tee — Faded Grey" — $19.00 on depop, size L, condition fair. style_tags: vintage, grunge, band tee, graphic tee. (High score: matches "vintage", "graphic", "tee")

The list is not empty → no error is set. The agent stores results in `session["search_results"]` and selects the top result:

`session["selected_item"]` = lst_006:
```json
{
  "id": "lst_006",
  "title": "Graphic Tee — 2003 Tour Bootleg Style",
  "description": "Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.",
  "category": "tops",
  "style_tags": ["graphic tee", "vintage", "grunge", "streetwear", "band tee"],
  "size": "L",
  "condition": "good",
  "price": 24.00,
  "colors": ["black"],
  "brand": null,
  "platform": "depop"
}
```

**Step 3: Call `suggest_outfit(selected_item, wardrobe)`**

The tool checks `wardrobe["items"]` — it has 10 items (not empty), so it builds a prompt listing the new graphic tee's details alongside the user's wardrobe pieces (baggy straight-leg jeans, wide-leg khaki trousers, white ribbed tank top, grey crewneck sweatshirt, black cropped zip hoodie, vintage black denim jacket, chunky white sneakers, black combat boots, brown leather belt, black crossbody bag).

The Groq LLM returns a string like:

> "Here are two outfit ideas with your new Graphic Tee 2003 Tour Bootleg Style:
>
> **Outfit 1 — Casual Streetwear:** Wear the graphic tee slightly tucked into your baggy straight-leg jeans (dark wash). Layer your vintage black denim jacket over it, leave it unbuttoned. Finish with your chunky white sneakers and the black crossbody bag.
>
> **Outfit 2 — Grunge Edge:** Pair the graphic tee with your wide-leg khaki trousers for contrast. Add your black combat boots and the brown leather belt. Skip the jacket — let the tee be the statement piece."

Stored in `session["outfit_suggestion"]`.

**Step 4: Call `create_fit_card(outfit_suggestion, selected_item)`**

The tool takes the outfit suggestion string and the listing dict, builds a prompt asking the LLM (at temperature ~0.9) for a 2–4 sentence Instagram/TikTok caption that mentions the item name, $24.00 price, and depop platform naturally.

The Groq LLM returns:

> "just copped this 2003 bootleg graphic tee off depop for $24 and it might be the hardest thing in my closet rn. tucked into my baggiest jeans with the denim jacket and chunky sneakers — full streetwear mode activated. thrifted fits hit different when the tee already looks perfectly worn in."

Stored in `session["fit_card"]`.

**Final output to user:**

The Gradio app displays three panels:

**Panel 1 — Top Listing Found:**
```
Graphic Tee — 2003 Tour Bootleg Style
Price: $24.00
Platform: depop
Size: L
Condition: good
Colors: black
Style: graphic tee, vintage, grunge, streetwear, band tee

Vintage-style bootleg tee with faded graphic. Slightly boxy fit.
100% cotton, soft and worn-in.
```

**Panel 2 — Outfit Idea:**
> Here are two outfit ideas with your new Graphic Tee — 2003 Tour Bootleg Style:
>
> Outfit 1 — Casual Streetwear: Wear the graphic tee slightly tucked into your baggy straight-leg jeans (dark wash). Layer your vintage black denim jacket over it, leave it unbuttoned. Finish with your chunky white sneakers and the black crossbody bag.
>
> Outfit 2 — Grunge Edge: Pair the graphic tee with your wide-leg khaki trousers for contrast. Add your black combat boots and the brown leather belt. Skip the jacket — let the tee be the statement piece.

**Panel 3 — Your Fit Card:**
> just copped this 2003 bootleg graphic tee off depop for $24 and it might be the hardest thing in my closet rn. tucked into my baggiest jeans with the denim jacket and chunky sneakers — full streetwear mode activated. thrifted fits hit different when the tee already looks perfectly worn in.

**Error path example:** If the user searched for "designer ballgown size XXS under $5", `search_listings` would return an empty list. The agent would set `session["error"]` to "No matching listings found for your search. Try broadening your description, removing the size or price filter, or searching for a different item." and return immediately. The Gradio UI would show this error in Panel 1, with Panels 2 and 3 empty.
