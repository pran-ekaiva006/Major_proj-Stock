"""
News Sentiment Analysis Module
================================
Fetches news headlines and scores sentiment using a keyword-based approach.
Uses Google News RSS (free, no API key needed).
"""

import logging
import re
from typing import List, Dict

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Keyword-Based Sentiment (no external deps needed)
# ──────────────────────────────────────────────────────────────────────

POSITIVE_WORDS = {
    'surge', 'soar', 'rally', 'gain', 'rise', 'jump', 'climb', 'boost',
    'profit', 'growth', 'bullish', 'upgrade', 'outperform', 'buy', 'strong',
    'positive', 'record', 'high', 'beat', 'exceed', 'optimistic', 'recovery',
    'boom', 'breakout', 'momentum', 'upside', 'earnings', 'revenue', 'success',
    'win', 'deal', 'partnership', 'innovation', 'launch', 'expand', 'dividend',
    'opportunity', 'milestone', 'approve', 'backed', 'top', 'best',
}

NEGATIVE_WORDS = {
    'crash', 'plunge', 'drop', 'fall', 'decline', 'loss', 'bearish', 'sell',
    'downgrade', 'underperform', 'weak', 'negative', 'low', 'miss', 'fail',
    'risk', 'concern', 'warning', 'threat', 'crisis', 'recession', 'layoff',
    'cut', 'slash', 'debt', 'lawsuit', 'investigation', 'fraud', 'scandal',
    'bankruptcy', 'default', 'volatile', 'uncertainty', 'fear', 'panic',
    'worst', 'slump', 'tumble', 'sink', 'collapse', 'trouble',
}


def analyze_sentiment(text: str) -> Dict:
    """
    Analyze sentiment of text using keyword matching.
    Returns a score (-1 to +1) and category.
    """
    words = set(re.findall(r'\b[a-z]+\b', text.lower()))

    pos_count = len(words & POSITIVE_WORDS)
    neg_count = len(words & NEGATIVE_WORDS)
    total = pos_count + neg_count

    if total == 0:
        compound = 0.0
    else:
        compound = round((pos_count - neg_count) / total, 4)

    positive = round(pos_count / max(len(words), 1), 4)
    negative = round(neg_count / max(len(words), 1), 4)
    neutral = round(1.0 - positive - negative, 4)

    if compound >= 0.05:
        category = "bullish"
    elif compound <= -0.05:
        category = "bearish"
    else:
        category = "neutral"

    return {
        "compound": compound,
        "positive": positive,
        "negative": negative,
        "neutral": max(0, neutral),
        "category": category,
    }


def fetch_news_headlines(symbol: str, max_results: int = 10) -> List[Dict]:
    """
    Fetch recent news headlines for a stock symbol.
    Uses Google News RSS feed (free, no API key).
    """
    try:
        import feedparser
    except ImportError:
        log.warning("feedparser not installed — returning empty headlines")
        return []

    clean_symbol = symbol.replace(".NS", "").replace("^", "")
    url = f"https://news.google.com/rss/search?q={clean_symbol}+stock&hl=en-US&gl=US&ceid=US:en"

    try:
        feed = feedparser.parse(url)
        headlines = []
        for entry in feed.entries[:max_results]:
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
