# FitFindr Demo Video Script (3-5 minutes)

## Setup (before recording)

- Have the Gradio app running (`python app.py`)
- Have `agent.py`, `tools.py`, and `app.py` open in your editor
- Terminal visible alongside the browser

---

## INTRO (0:00 - 0:30)

**[Show: Gradio UI in browser]**

> "This is FitFindr, an AI-powered thrift shopping assistant. You give it a natural language query describing what you're looking for, and it searches secondhand listings, suggests an outfit using your wardrobe, and generates a shareable social media caption -- what we call a fit card."

> "The agent uses a planning loop that dynamically decides which tool to call next by inspecting a session dictionary. Each iteration, a function called `_decide_next_step` checks what data exists so far and picks the next action. Let me walk through a full interaction."

---

## DEMO 1 -- Successful Multi-Step Interaction (0:30 - 2:30)

### Step 1: Enter a query

**[Show: Type into the Gradio text box]**

Query: `vintage graphic tee under $30 size M`

Wardrobe: **Example wardrobe (10 items)**

> "I'm searching for a vintage graphic tee, with a max price of thirty dollars, in size medium. I'm using the example wardrobe so the agent can suggest outfits with pieces I already own."

**[Click Submit]**

### Step 2: The planning loop begins

**[Show: agent.py -- the `while True` loop and `_decide_next_step` function]**

> "The agent enters a `while True` planning loop. Each iteration, it calls `_decide_next_step`, which inspects the session dictionary and decides what to do next. Right now the session is mostly empty, so `_decide_next_step` sees that `session['parsed']` is empty and returns 'parse'."

### Step 3: Loop iteration 1 -- parse

**[Show: agent.py -- the _parse_query function]**

> "The loop calls `_parse_query`. It uses regex to extract three things from my query: the description -- 'vintage graphic tee', the max price -- thirty dollars, and the size -- medium. These get stored in the session dictionary under the 'parsed' key. Now `_decide_next_step` runs again -- it sees parsed data exists but no search results, so it returns 'search'."

### Step 4: Loop iteration 2 -- search_listings

**[Show: tools.py -- search_listings function]**

> "The loop calls **search_listings** with the parsed description, size, and max price. It scores every listing in our dataset by keyword overlap, filters by size and price, and returns matches sorted by relevance. The agent picks the top match, storing it in session as 'selected_item'. `_decide_next_step` runs again -- selected item exists but no outfit suggestion, so it returns 'suggest'."

**[Show: the listing result panel in Gradio -- item title, price, platform, condition]**

> "Here's our top result -- you can see the title, price, condition, and which platform it's listed on."

### Step 5: Loop iteration 3 -- suggest_outfit

**[Show: tools.py -- suggest_outfit function]**

> "The loop calls **suggest_outfit**. It reads two things from the session: the selected item and my wardrobe. The tool sends these to the Groq LLM -- Llama 3.1 -- which generates one or two outfit combinations using specific pieces from my wardrobe. Notice the state flowing: the search result from iteration two becomes the input here. `_decide_next_step` runs again -- outfit suggestion exists but no fit card, so it returns 'create'."

**[Show: the outfit suggestion panel in Gradio]**

> "The LLM paired the tee with my baggy jeans and denim jacket -- pieces it pulled from my actual wardrobe data."

### Step 6: Loop iteration 4 -- create_fit_card

**[Show: tools.py -- create_fit_card function]**

> "The loop calls **create_fit_card**. This reads the outfit suggestion and the selected item from the session dictionary. It hits the LLM again at a higher temperature for more creative output and generates a two-to-four sentence caption. Now `_decide_next_step` sees all fields are populated and returns 'done' -- the loop breaks."

**[Show: the fit card panel in Gradio]**

> "Here's our fit card -- a casual, shareable caption that mentions the item name, price, and platform. Ready for Instagram or TikTok."

### State summary

> "To recap: the planning loop ran four iterations. Each time, `_decide_next_step` inspected the session dictionary and dynamically chose the next tool based on what was populated. The parsed query fed into search_listings, its top result fed into suggest_outfit alongside the wardrobe, and the outfit suggestion fed into create_fit_card. The loop didn't follow a fixed sequence -- it reacted to what each tool returned."

---

## DEMO 2 -- Triggered Failure with Graceful Response (2:30 - 3:30)

**[Show: Gradio UI, clear previous results]**

Query: `designer ballgown size XXS under $5`

> "Now let me trigger a failure. I'm searching for something extremely specific -- a designer ballgown, size extra-extra-small, under five dollars. Our dataset of forty secondhand listings almost certainly won't have this."

**[Click Submit]**

**[Show: the error message in the listing panel]**

> "The agent handled this gracefully. The loop ran parse, then search. search_listings returned an empty list, so the agent set `session['error']`. On the next iteration, `_decide_next_step` saw the error and returned 'done' -- the loop broke without ever calling suggest_outfit or create_fit_card. The UI shows a helpful message: 'No matching listings found -- try broadening your description, removing the size or price filter, or searching for a different item.'"

**[Show: agent.py -- the `_decide_next_step` function and the search branch that sets the error]**

> "Here in the agent code, you can see the decision function checks for errors on every iteration. Once `session['error']` is set, none of the conditions for 'suggest' or 'create' can pass -- they all require `session['error'] is None`. So the loop returns 'done' and the remaining tools are skipped. The other two panels stay empty because those tools were never invoked."

---

## DEMO 3 (Optional) -- Empty Wardrobe Handling (3:30 - 4:15)

**[Show: Gradio UI]**

Query: `denim jacket under $40`

Wardrobe: **Empty wardrobe (new user)**

> "One more scenario: what happens when a new user has no wardrobe? I'll search for a denim jacket with an empty wardrobe."

**[Click Submit]**

> "The loop runs parse, then search -- search_listings finds matches, no problem there. Then `_decide_next_step` returns 'suggest'. But when suggest_outfit detects the wardrobe is empty, it switches to a different LLM prompt. Instead of naming specific wardrobe pieces, it gives general styling advice -- what kinds of items would pair well with this jacket."

**[Show: the outfit suggestion panel -- general advice instead of specific pieces]**

> "The fit card still generates normally from this general advice. The tool adapted instead of failing."

---

## CLOSING (4:15 - 4:45)

**[Show: editor with agent.py, tools.py, app.py tabs visible]**

> "To wrap up: FitFindr uses a planning loop that dynamically selects which tool to call by inspecting session state each iteration. The `_decide_next_step` function checks what data exists and picks the next action -- parse, search, suggest, create, or done. State passes between tools through the session dictionary. The agent handles failures reactively: when search sets an error, the decision function sees it and returns 'done', skipping the remaining tools. An empty wardrobe switches the LLM prompt to general advice. Each tool does one job, and the loop orchestrates the flow based on what each tool returns."

---

## Recording Tips

- Use a screen recorder that captures both audio and screen (OBS, QuickTime, Loom)
- Zoom in on the relevant code when explaining each tool
- Keep the Gradio UI visible when showing results
- Speak at a measured pace -- you have 3-5 minutes, no need to rush
- If the LLM calls are slow, you can briefly narrate "waiting for the Groq API to respond" to fill dead air
