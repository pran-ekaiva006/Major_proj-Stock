"""
News Sentiment Analysis Module
================================
Fetches news headlines and scores sentiment using VADER.
Uses Google News RSS (free, no API key needed).
"""

import logging
import re
from datetime import datetime
from typing import List, Dict, Optional

log = logging.getLogger(__name__)

# Lazy imports
_vader = None


def _get_vader():
    """Lazy-load VADER sentiment analyzer."""
    global _vader
    if _vader is None:
        import nltk
        try:
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
        except LookupError:
            nltk.download('vader_lexicon', quiet=True)
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
        _vader = SentimentIntensityAnalyzer()
    return _vader


def fetch_news_headlines(symbol: str, max_results: int = 10) -> List[Dict]:
    """
    Fetch recent news headlines for a stock symbol.
    Uses Google News RSS feed (free, no API key).
    """
    import feedparser

    # Clean symbol for search
    clean_symbol = symbol.replace(".NS", "").replace("^", "")

    # Try Google News RSS
    url = f"https://news.google.com/rss/search?q={clean_symbol}+stock&hl=en-US&gl=US&ceid=US:en"

    try:
        feed = feedparser.parse(url)
        headlines = []
        for entry in feed.entries[:max_results]:
            # Clean HTML from title
            title = re.sub(r'<[^>]+>', '', entry.get('title', ''))
            source = entry.get('source', {}).get('title', 'Unknown')
            published = entry.get('published', '')

            headlines.append({
                "title": title,
                "source": source,
                "url": entry.get('link', ''),
                "published": published,
            })
        return headlines
    except Exception as e:
        log.warning(f"Failed to fetch news for {symbol}: {e}")
        return []


def analyze_sentiment(text: str) -> Dict:
    """
    Analyze sentiment of a single text using VADER.
    Returns compound score (-1 to +1) and category.
    """
    vader = _get_vader()
    scores = vader.polarity_scores(text)

    compound = scores['compound']
    if compound >= 0.05:
        category = "bullish"
    elif compound <= -0.05:
        category = "bearish"
    else:
        category = "neutral"

    return {
        "compound": round(compound, 4),
        "positive": round(scores['pos'], 4),
        "negative": round(scores['neg'], 4),
        "neutral": round(scores['neu'], 4),
        "category": category,
    }


def get_stock_sentiment(symbol: str, max_headlines: int = 10) -> Dict:
    """
    Full sentiment analysis for a stock: fetch news + score each headline.
    Returns overall sentiment and individual headline scores.
    """
    headlines = fetch_news_headlines(symbol, max_headlines)

    if not headlines:
        return {
            "symbol": symbol,
            "overall_score": 0.0,
            "overall_category": "neutral",
            "headline_count": 0,
            "headlines": [],
            "message": "No recent news found",
        }

    scored_headlines = []
    total_compound = 0.0

    for h in headlines:
        sentiment = analyze_sentiment(h["title"])
        total_compound += sentiment["compound"]
        scored_headlines.append({
            **h,
            "sentiment": sentiment,
        })

    overall_score = round(total_compound / len(headlines), 4)

    if overall_score >= 0.05:
        overall_category = "bullish"
    elif overall_score <= -0.05:
        overall_category = "bearish"
    else:
        overall_category = "neutral"

    return {
        "symbol": symbol,
        "overall_score": overall_score,
        "overall_category": overall_category,
        "headline_count": len(scored_headlines),
        "headlines": scored_headlines,
    }
