#!/usr/bin/env python3
"""
MCP Server: Market Data Tools

Provides real-time stock market data via Alpha Vantage API as MCP tools.
Deploy to Railway/Render for remote access, or run locally via stdio.

Tools:
  - get_quote(ticker)        → Current price, volume, change
  - get_overview(ticker)     → PE, EPS, margins, market cap, analyst ratings, 52w range
  - get_rsi(ticker)          → RSI (14-day)
  - get_sma(ticker, period)  → Simple Moving Average (50, 200)
  - get_macd(ticker)         → MACD indicator
  - get_full(ticker)         → All of the above in one call (~75s due to rate limiting)
  - get_news(ticker)         → News sentiment for a specific ticker
  - get_news_general()       → General market news sentiment

Usage:
  Local (stdio):   python server.py
  Remote (HTTP):   python server.py --remote
  Or set env:      MCP_TRANSPORT=streamable-http python server.py
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
AV_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "FNHBGVF3O7VKOGJ2")
AV_BASE = "https://www.alphavantage.co/query"
RATE_LIMIT_SECONDS = 12.5  # 5 calls/min → 12s between calls + buffer

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
_last_call = 0.0


def _rate_limit():
    global _last_call
    now = time.time()
    elapsed = now - _last_call
    if elapsed < RATE_LIMIT_SECONDS:
        time.sleep(RATE_LIMIT_SECONDS - elapsed)
    _last_call = time.time()


def _fetch(params: dict) -> dict:
    _rate_limit()
    params["apikey"] = AV_KEY
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{AV_BASE}?{query}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            if "Information" in data and "rate limit" in data.get("Information", "").lower():
                time.sleep(15)
                with urllib.request.urlopen(req, timeout=15) as resp2:
                    data = json.loads(resp2.read().decode())
            return data
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "market-data",
    streamable_http_path="/api/mcp",
    transport_security={"enable_dns_rebinding_protection": False},
    instructions="""Market data tools powered by Alpha Vantage API.

Use `get_full(ticker)` to get all data for a ticker in one call (price, PE, EPS,
margins, RSI, SMA 50/200, MACD, analyst ratings). Takes ~75 seconds due to API
rate limiting (5 calls/min).

Use `get_news(ticker)` for ticker-specific news or `get_news_general()` for
broad market news with sentiment scores.

Individual tools (get_quote, get_overview, get_rsi, get_sma, get_macd) are
available if you only need specific data points.

Rate limit: 5 API calls per minute. The tools handle rate limiting automatically —
they will wait between calls as needed. Do not call multiple tools in parallel.""",
)


@mcp.tool()
def get_quote(ticker: str) -> str:
    """Get current stock price, volume, and daily change.

    Returns: price, open, high, low, volume, previous close, change, change percent, latest trading day.

    Example: get_quote("AAPL") → {"price": "287.44", "change": "-1.83", "change_percent": "-0.6325%", ...}
    """
    data = _fetch({"function": "GLOBAL_QUOTE", "symbol": ticker.upper()})
    q = data.get("Global Quote", {})
    if q:
        return json.dumps({
            "ticker": q.get("01. symbol", ticker),
            "price": q.get("05. price"),
            "open": q.get("02. open"),
            "high": q.get("03. high"),
            "low": q.get("04. low"),
            "volume": q.get("06. volume"),
            "previous_close": q.get("08. previous close"),
            "change": q.get("09. change"),
            "change_percent": q.get("10. change percent"),
            "latest_trading_day": q.get("07. latest trading day"),
        }, indent=2)
    return json.dumps(data, indent=2)


@mcp.tool()
def get_overview(ticker: str) -> str:
    """Get company fundamentals: PE, EPS, margins, market cap, analyst ratings, 52-week range, and more.

    Returns 30+ fields including: market_cap, pe_trailing, pe_forward, peg_ratio, eps_ttm,
    revenue_ttm, profit_margin, operating_margin, roe, roa, beta, 52w_high, 52w_low,
    50d_sma, 200d_sma, analyst_target_price, analyst ratings breakdown, dividend_yield, ev_ebitda.

    Example: get_overview("NVDA") → {"pe_trailing": "42.5", "market_cap": "5051308311000", ...}
    """
    data = _fetch({"function": "OVERVIEW", "symbol": ticker.upper()})
    if "Symbol" in data:
        return json.dumps({
            "ticker": data.get("Symbol"),
            "name": data.get("Name"),
            "sector": data.get("Sector"),
            "industry": data.get("Industry"),
            "market_cap": data.get("MarketCapitalization"),
            "pe_trailing": data.get("TrailingPE"),
            "pe_forward": data.get("ForwardPE"),
            "peg_ratio": data.get("PEGRatio"),
            "eps_ttm": data.get("DilutedEPSTTM"),
            "revenue_ttm": data.get("RevenueTTM"),
            "revenue_growth_yoy": data.get("QuarterlyRevenueGrowthYOY"),
            "earnings_growth_yoy": data.get("QuarterlyEarningsGrowthYOY"),
            "profit_margin": data.get("ProfitMargin"),
            "operating_margin": data.get("OperatingMarginTTM"),
            "gross_profit_ttm": data.get("GrossProfitTTM"),
            "roe": data.get("ReturnOnEquityTTM"),
            "roa": data.get("ReturnOnAssetsTTM"),
            "dividend_yield": data.get("DividendYield"),
            "payout_ratio": data.get("PayoutRatio"),
            "book_value": data.get("BookValue"),
            "price_to_book": data.get("PriceToBookRatio"),
            "price_to_sales": data.get("PriceToSalesRatioTTM"),
            "ev_ebitda": data.get("EVToEBITDA"),
            "beta": data.get("Beta"),
            "52w_high": data.get("52WeekHigh"),
            "52w_low": data.get("52WeekLow"),
            "50d_sma": data.get("50DayMovingAverage"),
            "200d_sma": data.get("200DayMovingAverage"),
            "shares_outstanding": data.get("SharesOutstanding"),
            "analyst_target_price": data.get("AnalystTargetPrice"),
            "analyst_strong_buy": data.get("AnalystRatingStrongBuy"),
            "analyst_buy": data.get("AnalystRatingBuy"),
            "analyst_hold": data.get("AnalystRatingHold"),
            "analyst_sell": data.get("AnalystRatingSell"),
            "analyst_strong_sell": data.get("AnalystRatingStrongSell"),
        }, indent=2)
    return json.dumps(data, indent=2)


@mcp.tool()
def get_rsi(ticker: str, period: int = 14) -> str:
    """Get RSI (Relative Strength Index). Default 14-day period.

    RSI > 70 = overbought, RSI < 30 = oversold.

    Example: get_rsi("NVDA") → {"rsi": "63.4032", "date": "2026-05-07"}
    """
    data = _fetch({
        "function": "RSI", "symbol": ticker.upper(),
        "interval": "daily", "time_period": str(period), "series_type": "close",
    })
    ta = data.get("Technical Analysis: RSI", {})
    if ta:
        d = next(iter(ta))
        return json.dumps({"ticker": ticker.upper(), "rsi": ta[d]["RSI"], "date": d, "period": period}, indent=2)
    return json.dumps(data, indent=2)


@mcp.tool()
def get_sma(ticker: str, period: int = 50) -> str:
    """Get Simple Moving Average. Common periods: 50 (medium-term trend), 200 (long-term trend).

    Price above SMA = bullish. Golden cross = 50 SMA crosses above 200 SMA.

    Example: get_sma("AAPL", 50) → {"sma": "262.40", "date": "2026-05-07"}
    """
    data = _fetch({
        "function": "SMA", "symbol": ticker.upper(),
        "interval": "daily", "time_period": str(period), "series_type": "close",
    })
    ta = data.get("Technical Analysis: SMA", {})
    if ta:
        d = next(iter(ta))
        return json.dumps({"ticker": ticker.upper(), "sma": ta[d]["SMA"], "period": period, "date": d}, indent=2)
    return json.dumps(data, indent=2)


@mcp.tool()
def get_macd(ticker: str) -> str:
    """Get MACD indicator (12/26/9). Shows momentum direction and strength.

    MACD crossing above signal = bullish. Histogram expanding = strengthening trend.

    Example: get_macd("NVDA") → {"macd": "5.23", "signal": "3.81", "histogram": "1.42"}
    """
    data = _fetch({
        "function": "MACD", "symbol": ticker.upper(),
        "interval": "daily", "series_type": "close",
    })
    ta = data.get("Technical Analysis: MACD", {})
    if ta:
        d = next(iter(ta))
        e = ta[d]
        return json.dumps({
            "ticker": ticker.upper(), "macd": e.get("MACD"),
            "signal": e.get("MACD_Signal"), "histogram": e.get("MACD_Hist"), "date": d,
        }, indent=2)
    return json.dumps(data, indent=2)


@mcp.tool()
def get_full(ticker: str) -> str:
    """Get ALL data for a ticker: quote + overview + RSI + SMA 50 + SMA 200 + MACD.

    Makes 6 API calls with rate limiting (~75 seconds total). Use this to build a
    complete data sheet for analysis. Returns structured JSON with all fields.

    Example: get_full("NVDA") → {"ticker": "NVDA", "data": {"quote": {...}, "overview": {...}, "rsi": {...}, ...}}
    """
    results = {}

    # Quote
    qd = _fetch({"function": "GLOBAL_QUOTE", "symbol": ticker.upper()})
    q = qd.get("Global Quote", {})
    results["quote"] = {
        "price": q.get("05. price"), "open": q.get("02. open"),
        "high": q.get("03. high"), "low": q.get("04. low"),
        "volume": q.get("06. volume"), "previous_close": q.get("08. previous close"),
        "change": q.get("09. change"), "change_percent": q.get("10. change percent"),
        "latest_trading_day": q.get("07. latest trading day"),
    }

    # Overview
    od = _fetch({"function": "OVERVIEW", "symbol": ticker.upper()})
    if "Symbol" in od:
        results["overview"] = {
            "name": od.get("Name"), "sector": od.get("Sector"), "industry": od.get("Industry"),
            "market_cap": od.get("MarketCapitalization"),
            "pe_trailing": od.get("TrailingPE"), "pe_forward": od.get("ForwardPE"),
            "peg_ratio": od.get("PEGRatio"), "eps_ttm": od.get("DilutedEPSTTM"),
            "revenue_ttm": od.get("RevenueTTM"),
            "revenue_growth_yoy": od.get("QuarterlyRevenueGrowthYOY"),
            "earnings_growth_yoy": od.get("QuarterlyEarningsGrowthYOY"),
            "profit_margin": od.get("ProfitMargin"),
            "operating_margin": od.get("OperatingMarginTTM"),
            "roe": od.get("ReturnOnEquityTTM"), "roa": od.get("ReturnOnAssetsTTM"),
            "beta": od.get("Beta"),
            "52w_high": od.get("52WeekHigh"), "52w_low": od.get("52WeekLow"),
            "50d_sma": od.get("50DayMovingAverage"), "200d_sma": od.get("200DayMovingAverage"),
            "dividend_yield": od.get("DividendYield"), "ev_ebitda": od.get("EVToEBITDA"),
            "analyst_target": od.get("AnalystTargetPrice"),
            "analyst_buy": od.get("AnalystRatingBuy"), "analyst_hold": od.get("AnalystRatingHold"),
            "analyst_sell": od.get("AnalystRatingSell"),
        }

    # RSI
    rd = _fetch({"function": "RSI", "symbol": ticker.upper(), "interval": "daily", "time_period": "14", "series_type": "close"})
    ta = rd.get("Technical Analysis: RSI", {})
    if ta:
        d = next(iter(ta))
        results["rsi"] = {"value": ta[d]["RSI"], "date": d}

    # SMA 50
    sd = _fetch({"function": "SMA", "symbol": ticker.upper(), "interval": "daily", "time_period": "50", "series_type": "close"})
    ta = sd.get("Technical Analysis: SMA", {})
    if ta:
        d = next(iter(ta))
        results["sma_50"] = {"value": ta[d]["SMA"], "date": d}

    # SMA 200
    sd2 = _fetch({"function": "SMA", "symbol": ticker.upper(), "interval": "daily", "time_period": "200", "series_type": "close"})
    ta = sd2.get("Technical Analysis: SMA", {})
    if ta:
        d = next(iter(ta))
        results["sma_200"] = {"value": ta[d]["SMA"], "date": d}

    # MACD
    md = _fetch({"function": "MACD", "symbol": ticker.upper(), "interval": "daily", "series_type": "close"})
    ta = md.get("Technical Analysis: MACD", {})
    if ta:
        d = next(iter(ta))
        e = ta[d]
        results["macd"] = {"macd": e.get("MACD"), "signal": e.get("MACD_Signal"), "histogram": e.get("MACD_Hist"), "date": d}

    return json.dumps({"ticker": ticker.upper(), "data": results}, indent=2)


@mcp.tool()
def get_news(ticker: str) -> str:
    """Get news articles with sentiment scores for a specific ticker.

    Returns up to 15 articles with: title, summary, source, url, published date,
    sentiment label (Bullish/Bearish/Neutral), and sentiment score (-1 to 1).

    Example: get_news("AAPL") → {"articles": [{"title": "...", "sentiment": "Bullish", ...}]}
    """
    data = _fetch({"function": "NEWS_SENTIMENT", "tickers": ticker.upper(), "limit": "15"})
    if "feed" in data:
        articles = []
        for item in data["feed"][:15]:
            articles.append({
                "title": item.get("title"),
                "summary": item.get("summary", "")[:300],
                "source": item.get("source"),
                "url": item.get("url"),
                "published": item.get("time_published"),
                "sentiment": item.get("overall_sentiment_label"),
                "sentiment_score": item.get("overall_sentiment_score"),
            })
        return json.dumps({"ticker": ticker.upper(), "articles": articles}, indent=2)
    return json.dumps(data, indent=2)


@mcp.tool()
def get_news_general() -> str:
    """Get general market news with sentiment analysis (not ticker-specific).

    Returns up to 30 articles covering broad market, macro, and sector news.
    Each article includes mentioned tickers so you can identify which stocks are in the news.

    Example: get_news_general() → {"articles": [{"title": "Fed holds rates...", "tickers_mentioned": ["SPY", "QQQ"], ...}]}
    """
    data = _fetch({"function": "NEWS_SENTIMENT", "limit": "30"})
    if "feed" in data:
        articles = []
        for item in data["feed"][:30]:
            tickers = [t.get("ticker", "") for t in item.get("ticker_sentiment", [])]
            articles.append({
                "title": item.get("title"),
                "summary": item.get("summary", "")[:300],
                "source": item.get("source"),
                "url": item.get("url"),
                "published": item.get("time_published"),
                "sentiment": item.get("overall_sentiment_label"),
                "tickers_mentioned": tickers[:5],
            })
        return json.dumps({"articles": articles}, indent=2)
    return json.dumps(data, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if "--remote" in sys.argv:
        transport = "streamable-http"

    if transport == "streamable-http":
        import uvicorn
        from starlette.responses import JSONResponse, Response
        from starlette.routing import Route

        async def health(request):
            return JSONResponse({"status": "ok", "server": "market-data"})

        # Get the MCP ASGI app (has /mcp route built in)
        app = mcp.streamable_http_app()

        # Add health route
        app.routes.insert(0, Route("/health", health))

        port = int(os.environ.get("PORT", 8000))
        uvicorn.run(app, host="0.0.0.0", port=port, forwarded_allow_ips="*", proxy_headers=True, server_header=False)
    else:
        mcp.run()
