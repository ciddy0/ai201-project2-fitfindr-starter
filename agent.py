"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def _parse_query(session: dict) -> None:
    """Parse the user's natural language query into structured fields.

    Uses regex to extract description, size, and max_price from the raw query
    string. Stores the result in session["parsed"].
    """
    text = session["query"].lower()

    # Extract max_price
    max_price = None
    price_match = re.search(r'(?:under|below|less than|max|<)\s*\$?\s*(\d+(?:\.\d{1,2})?)', text)
    if price_match:
        max_price = float(price_match.group(1))

    # Extract size
    size = None
    size_match = re.search(r'(?:in\s+)?size\s+(\w+)', text)
    if size_match:
        size = size_match.group(1).upper()

    # Extract description — remove price/size phrases, strip filler
    description = session["query"]
    if price_match:
        description = re.sub(r'(?:under|below|less than|max|<)\s*\$?\s*\d+(?:\.\d{1,2})?', '', description, flags=re.IGNORECASE)
    if size_match:
        description = re.sub(r'(?:in\s+)?size\s+\w+', '', description, flags=re.IGNORECASE)
    description = re.sub(r'[,.\-]+$', '', description).strip()
    description = re.sub(r"(?i)^(i'm |i am )?(looking for|searching for|find me|i want|i need)\s+(a |an )?", '', description).strip()

    session["parsed"] = {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


def _decide_next_step(session: dict) -> str:
    """Inspect the session state and decide which tool to call next.

    Returns one of: "parse", "search", "suggest", "create", or "done".
    The planning loop calls this each iteration to dynamically select the
    next action based on what prior tools have returned so far.
    """
    if not session["parsed"]:
        return "parse"
    if not session["search_results"] and session["error"] is None:
        return "search"
    if session["selected_item"] and session["outfit_suggestion"] is None and session["error"] is None:
        return "suggest"
    if session["outfit_suggestion"] and session["fit_card"] is None and session["error"] is None:
        return "create"
    return "done"


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    The agent uses a planning loop that inspects session state each iteration
    and dynamically selects which tool to call next via _decide_next_step().
    If any step produces a result that makes downstream tools inappropriate
    (e.g., empty search results), the loop terminates early without calling
    the remaining tools.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.
    """
    session = _new_session(query, wardrobe)

    while True:
        step = _decide_next_step(session)

        if step == "parse":
            _parse_query(session)

        elif step == "search":
            session["search_results"] = search_listings(
                description=session["parsed"]["description"],
                size=session["parsed"]["size"],
                max_price=session["parsed"]["max_price"],
            )
            if not session["search_results"]:
                session["error"] = (
                    "No matching listings found for your search. "
                    "Try broadening your description, removing the size or "
                    "price filter, or searching for a different item."
                )
            else:
                session["selected_item"] = session["search_results"][0]

        elif step == "suggest":
            session["outfit_suggestion"] = suggest_outfit(
                new_item=session["selected_item"],
                wardrobe=session["wardrobe"],
            )

        elif step == "create":
            session["fit_card"] = create_fit_card(
                outfit=session["outfit_suggestion"],
                new_item=session["selected_item"],
            )

        else:  # "done"
            break

    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
