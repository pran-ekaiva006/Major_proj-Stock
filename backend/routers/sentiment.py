"""
Sentiment Router
=================
News sentiment analysis endpoints.
"""

import logging
from fastapi import APIRouter

from backend.sentiment import get_stock_sentiment

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Sentiment"])


@router.get("/sentiment/{symbol}")
def sentiment(symbol: str):
    """Get sentiment analysis for a stock symbol based on recent news."""
    result = get_stock_sentiment(symbol.upper(), max_headlines=10)
    return result
