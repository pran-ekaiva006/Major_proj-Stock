"""
Tests for Sentiment Analysis Module
=====================================
"""

import pytest
from backend.sentiment import analyze_sentiment, get_stock_sentiment


class TestAnalyzeSentiment:
    def test_positive_text(self):
        result = analyze_sentiment("Stock surges to record high, great earnings!")
        assert result["compound"] > 0
        assert result["category"] == "bullish"

    def test_negative_text(self):
        result = analyze_sentiment("Market crashes, massive losses reported")
        assert result["compound"] < 0
        assert result["category"] == "bearish"

    def test_neutral_text(self):
        result = analyze_sentiment("The stock market closed today")
        assert result["category"] in ["neutral", "bullish", "bearish"]

    def test_result_keys(self):
        result = analyze_sentiment("test")
        assert "compound" in result
        assert "positive" in result
        assert "negative" in result
        assert "neutral" in result
        assert "category" in result

    def test_score_range(self):
        result = analyze_sentiment("Amazing growth!")
        assert -1 <= result["compound"] <= 1
        assert 0 <= result["positive"] <= 1
        assert 0 <= result["negative"] <= 1


class TestGetStockSentiment:
    def test_returns_structure(self):
        result = get_stock_sentiment("AAPL", max_headlines=3)
        assert "symbol" in result
        assert "overall_score" in result
        assert "overall_category" in result
        assert "headline_count" in result
        assert "headlines" in result
        assert result["symbol"] == "AAPL"

    def test_overall_score_range(self):
        result = get_stock_sentiment("MSFT", max_headlines=3)
        assert -1 <= result["overall_score"] <= 1
