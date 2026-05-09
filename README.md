# MCP Server — Market Data Tools

MCP server providing real-time stock market data via Alpha Vantage API. Deploy to Railway for remote access from claude.ai scheduled tasks.

## Tools

| Tool | Description | Rate |
|------|-------------|------|
| `get_full(ticker)` | All data in one call (price, PE, EPS, RSI, SMA, MACD, analyst ratings) | 6 API calls, ~75s |
| `get_quote(ticker)` | Current price, volume, change | 1 call |
| `get_overview(ticker)` | Fundamentals (PE, EPS, margins, market cap, analyst ratings) | 1 call |
| `get_rsi(ticker, period)` | RSI indicator (default 14-day) | 1 call |
| `get_sma(ticker, period)` | Simple Moving Average (50 or 200) | 1 call |
| `get_macd(ticker)` | MACD indicator | 1 call |
| `get_news(ticker)` | News sentiment for a ticker | 1 call |
| `get_news_general()` | General market news | 1 call |

## Run locally

```bash
pip install -r requirements.txt
python server.py              # stdio (for Claude Code)
python server.py --remote     # HTTP (for remote access)
```

## Deploy to Railway

1. Push this repo to GitHub
2. Go to [railway.com](https://railway.com) → New Project → Deploy from GitHub
3. Set environment variable: `ALPHA_VANTAGE_API_KEY` (or use the default)
4. Railway gives you an HTTPS URL like `https://mcp-server-xyz.railway.app`

## Connect to claude.ai

1. Go to claude.ai → Settings → Connectors → Add custom connector
2. Paste: `https://your-railway-url.railway.app/mcp`
3. Done — scheduled tasks can now call the tools

## Connect to Claude Code (local)

```bash
claude mcp add market-data -- python /path/to/server.py
```

## Rate limits

Alpha Vantage free tier: 5 API calls/minute, 25/day. `get_full()` uses 6 calls per ticker, so max ~4 tickers per day on free tier. Upgrade at alphavantage.co/premium for higher limits.
