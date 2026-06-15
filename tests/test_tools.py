"""Tests for the three FitFindr tools in tools.py."""

from unittest.mock import MagicMock, patch

import pytest

from tools import create_fit_card, search_listings, suggest_outfit


# ── search_listings ──────────────────────────────────────────────────────────


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    for item in results:
        assert item["price"] <= 10


def test_search_size_filter():
    results = search_listings("jeans", size="L")
    for item in results:
        assert "l" in item["size"].lower()


def test_search_results_sorted_by_relevance():
    results = search_listings("vintage graphic tee")
    assert len(results) >= 2, "Need at least 2 results to verify sort order"
    # Recompute scores to verify ordering
    keywords = "vintage graphic tee".lower().split()
    def score(listing):
        text = " ".join([
            listing["title"],
            listing["description"],
            listing["category"],
            " ".join(listing["style_tags"]),
        ]).lower()
        return sum(1 for kw in keywords if kw in text)

    assert score(results[0]) >= score(results[-1])


# ── Helper: mock Groq client ────────────────────────────────────────────────


def _mock_groq_client(response_text="mock LLM response"):
    """Return a MagicMock that behaves like a Groq client."""
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = response_text
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


SAMPLE_ITEM = {
    "id": "test-001",
    "title": "Vintage Band Tee",
    "description": "A cool vintage tee from the 90s",
    "category": "tops",
    "style_tags": ["vintage", "streetwear"],
    "size": "M",
    "condition": "good",
    "price": 18.0,
    "colors": ["black", "white"],
    "brand": "Hanes",
    "platform": "depop",
}


# ── suggest_outfit ───────────────────────────────────────────────────────────


@patch("tools._get_groq_client")
def test_suggest_outfit_with_wardrobe(mock_get_client):
    mock_get_client.return_value = _mock_groq_client("Pair the tee with jeans")
    wardrobe = {
        "items": [
            {"name": "Blue Jeans", "category": "bottoms", "colors": ["blue"]},
            {"name": "White Sneakers", "category": "shoes", "colors": ["white"]},
        ]
    }
    result = suggest_outfit(SAMPLE_ITEM, wardrobe)
    assert isinstance(result, str)
    assert len(result) > 0
    mock_get_client.return_value.chat.completions.create.assert_called_once()


@patch("tools._get_groq_client")
def test_suggest_outfit_empty_wardrobe(mock_get_client):
    mock_get_client.return_value = _mock_groq_client("Try pairing with basics")
    wardrobe = {"items": []}
    result = suggest_outfit(SAMPLE_ITEM, wardrobe)
    assert isinstance(result, str)
    assert len(result) > 0


# ── create_fit_card ──────────────────────────────────────────────────────────


@patch("tools._get_groq_client")
def test_create_fit_card_returns_caption(mock_get_client):
    mock_get_client.return_value = _mock_groq_client("Just thrifted this gem!")
    result = create_fit_card("Rock the tee with slim jeans and boots", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert len(result) > 0
    mock_get_client.return_value.chat.completions.create.assert_called_once()


def test_create_fit_card_empty_outfit():
    # Should return fallback without calling Groq at all
    result = create_fit_card("", SAMPLE_ITEM)
    assert "no outfit suggestion" in result.lower()
