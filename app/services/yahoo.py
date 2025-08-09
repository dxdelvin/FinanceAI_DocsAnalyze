# app/services/yahoo.py
from __future__ import annotations

import re
import datetime as dt
from typing import Any, Dict, List, Optional, Set

import yfinance as yf
import pandas as pd
import pytz

EU_TZ = pytz.timezone("Europe/Berlin")

# --------------------------------------------------------------------------------------
# US-only controls
# --------------------------------------------------------------------------------------

# Yahoo fast_info.exchange codes commonly used for US listings
_US_EXCHANGES: Set[str] = {
    "NMS",  # NASDAQ Global Select
    "NGM",  # NASDAQ Global Market
    "NCM",  # NASDAQ Capital Market
    "NYQ",  # NYSE
    "NYS",  # NYSE (alt)
    "ASE",  # NYSE American (AMEX)
    "PCX",  # NYSE Arca (ETFs)
    "BATS", # Cboe BZX
    "CBOE", # Cboe
}

# Reject obvious non-US tickers via suffix
_NON_US_SUFFIXES = (
    ".NS", ".BO", ".L", ".TO", ".HK", ".SS", ".SZ", ".T", ".AX", ".NZ",
    ".PA", ".DE", ".VI", ".SW", ".SA", ".MX", ".CO", ".MI", ".BR", ".OL",
)

# --------------------------------------------------------------------------------------
# Aliases: common names & variants -> US tickers
# (Feel free to extend — these are the most frequently asked)
# --------------------------------------------------------------------------------------
_ALIASES: Dict[str, str] = {
    # Mega-cap tech
    "APPLE": "AAPL", "APPLE INC": "AAPL", "AAPL": "AAPL",
    "MICROSOFT": "MSFT", "MICROSOFT CORP": "MSFT", "MSFT": "MSFT",
    "GOOGLE": "GOOGL", "ALPHABET": "GOOGL", "ALPHABET A": "GOOGL", "ALPHABET CLASS A": "GOOGL",
    "ALPHABET C": "GOOG", "ALPHABET CLASS C": "GOOG", "GOOG": "GOOG", "GOOGL": "GOOGL",
    "META": "META", "FACEBOOK": "META", "FB": "META",
    "AMAZON": "AMZN", "AMZN": "AMZN",
    "TESLA": "TSLA", "TSLA": "TSLA",
    "NVIDIA": "NVDA", "NVDA": "NVDA",
    "NETFLIX": "NFLX", "NFLX": "NFLX",
    "ADOBE": "ADBE", "ADBE": "ADBE",
    "SALESFORCE": "CRM", "CRM": "CRM",
    "SERVICENOW": "NOW", "NOW": "NOW",
    "ORACLE": "ORCL", "ORCL": "ORCL",
    "IBM": "IBM",
    "INTEL": "INTC", "INTC": "INTC",
    "AMD": "AMD",
    "QUALCOMM": "QCOM", "QCOM": "QCOM",
    "BROADCOM": "AVGO", "AVGO": "AVGO",
    "CISCO": "CSCO", "CSCO": "CSCO",
    "MICRON": "MU", "MU": "MU",
    "TEXAS INSTRUMENTS": "TXN", "TXN": "TXN",
    "ASML": "ASML",
    "TAIWAN SEMI": "TSM", "TSMC": "TSM", "TSM": "TSM",
    "ARM": "ARM",

    # Fin/Payments
    "JPMORGAN": "JPM", "JPM": "JPM",
    "BANK OF AMERICA": "BAC", "BAC": "BAC",
    "CITI": "C", "CITIGROUP": "C", "C": "C",
    "WELLS FARGO": "WFC", "WFC": "WFC",
    "GOLDMAN": "GS", "GOLDMAN SACHS": "GS", "GS": "GS",
    "MORGAN STANLEY": "MS", "MS": "MS",
    "VISA": "V", "V": "V",
    "MASTERCARD": "MA", "MA": "MA",
    "PAYPAL": "PYPL", "PYPL": "PYPL",
    "AMERICAN EXPRESS": "AXP", "AMEX": "AXP", "AXP": "AXP",

    # Berkshire & class shares
    "BERKSHIRE": "BRK-B", "BERKSHIRE HATHAWAY": "BRK-B",
    "BRK.B": "BRK-B", "BRKB": "BRK-B", "BRK-B": "BRK-B",
    "BRK.A": "BRK-A", "BRKA": "BRK-A", "BRK-A": "BRK-A",
    "BFB": "BF-B", "BF.B": "BF-B", "BF-B": "BF-B", "BROWN FORMAN": "BF-B",

    # Commerce / Consumer / Travel
    "WALMART": "WMT", "WMT": "WMT",
    "COSTCO": "COST", "COST": "COST",
    "TARGET": "TGT", "TGT": "TGT",
    "HOME DEPOT": "HD", "HD": "HD",
    "LOWES": "LOW", "LOWE'S": "LOW", "LOW": "LOW",
    "DISNEY": "DIS", "DIS": "DIS",
    "NIKE": "NKE", "NKE": "NKE",
    "MACYS": "M", "MACY'S": "M", "M": "M",
    "STARBUCKS": "SBUX", "SBUX": "SBUX",
    "MCDONALDS": "MCD", "MCDONALD'S": "MCD", "MCD": "MCD",
    "CHIPOTLE": "CMG", "CMG": "CMG",
    "COCA COLA": "KO", "COKE": "KO", "KO": "KO",
    "PEPSI": "PEP", "PEPSICO": "PEP", "PEP": "PEP",
    "UBER": "UBER", "LYFT": "LYFT",
    "AIRBNB": "ABNB", "ABNB": "ABNB",
    "DOORDASH": "DASH", "DASH": "DASH",
    "SHOPIFY": "SHOP", "SHOP": "SHOP",
    "ETSY": "ETSY", "ROKU": "ROKU", "PINS": "PINS", "SNAP": "SNAP",

    # Energy / Industrials / Defense
    "EXXON": "XOM", "XOM": "XOM",
    "CHEVRON": "CVX", "CVX": "CVX",
    "CONOCOPHILLIPS": "COP", "COP": "COP",
    "OCCIDENTAL": "OXY", "OXY": "OXY",
    "SHELL": "SHEL", "BP": "BP",
    "CATERPILLAR": "CAT", "CAT": "CAT",
    "DEERE": "DE", "JOHN DEERE": "DE", "DE": "DE",
    "BOEING": "BA", "BA": "BA",
    "LOCKHEED": "LMT", "LOCKHEED MARTIN": "LMT", "LMT": "LMT",
    "NORTHROP": "NOC", "NORTHROP GRUMMAN": "NOC", "NOC": "NOC",
    "RTX": "RTX", "RAYTHEON": "RTX",
    "GE": "GE",

    # Autos / EVs
    "FORD": "F", "F": "F",
    "GM": "GM",
    "RIVIAN": "RIVN", "RIVN": "RIVN",
    "LUCID": "LCID", "LCID": "LCID",

    # Telecom
    "AT&T": "T", "ATT": "T", "T": "T",
    "VERIZON": "VZ", "VZ": "VZ",
    "T MOBILE": "TMUS", "T-MOBILE": "TMUS", "TMUS": "TMUS",

    # Health / Pharma / MedTech
    "UNITEDHEALTH": "UNH", "UNH": "UNH",
    "JOHNSON & JOHNSON": "JNJ", "JOHNSON AND JOHNSON": "JNJ", "JNJ": "JNJ",
    "PFIZER": "PFE", "PFE": "PFE",
    "MERCK": "MRK", "MRK": "MRK",
    "ABBVIE": "ABBV", "ABBV": "ABBV",
    "ELI LILLY": "LLY", "LILLY": "LLY", "LLY": "LLY",
    "BRISTOL MYERS": "BMY", "BRISTOL-MYERS": "BMY", "BMY": "BMY",
    "GILEAD": "GILD", "GILD": "GILD",
    "MODERNA": "MRNA", "MRNA": "MRNA",
    "THERMO FISHER": "TMO", "TMO": "TMO",
    "DANAHER": "DHR", "DHR": "DHR",
    "ASTRAZENECA": "AZN", "AZN": "AZN",
    "NOVO NORDISK": "NVO", "NVO": "NVO",

    # Cyber / Cloud / Dev
    "CROWDSTRIKE": "CRWD", "CRWD": "CRWD",
    "PALO ALTO": "PANW", "PANW": "PANW",
    "ZSCALER": "ZS", "ZS": "ZS",
    "FORTINET": "FTNT", "FTNT": "FTNT",
    "DATADOG": "DDOG", "DDOG": "DDOG",
    "OKTA": "OKTA",
    "ATLASSIAN": "TEAM", "TEAM": "TEAM",
    "GITLAB": "GTLB", "GTLB": "GTLB",
    "MONGODB": "MDB", "MDB": "MDB",
    "ELASTIC": "ESTC", "ESTC": "ESTC",
    "SNOWFLAKE": "SNOW", "SNOW": "SNOW",
    "SERVICENOW": "NOW",

    # Crypto proxies
    "COINBASE": "COIN", "COIN": "COIN",
    "MICROSTRATEGY": "MSTR", "MSTR": "MSTR",

    # Media
    "WARNER BROS": "WBD", "WBD": "WBD",
    "PARAMOUNT": "PARA", "PARA": "PARA",
    "NETFLIX": "NFLX",

    # ETFs (popular)
    "SPY": "SPY", "S&P500": "SPY", "S&P 500": "SPY", "SP500": "SPY", "SPX": "SPY",
    "VOO": "VOO", "IVV": "IVV", "VTI": "VTI",
    "QQQ": "QQQ", "DIA": "DIA", "IWM": "IWM",
    "SOXX": "SOXX", "SMH": "SMH",
    "ARKK": "ARKK",
    "XLK": "XLK", "XLF": "XLF", "XLE": "XLE", "XLV": "XLV", "XLY": "XLY",
    "XLP": "XLP", "XLU": "XLU", "XLI": "XLI", "XLB": "XLB", "XLRE": "XLRE", "XLC": "XLC",
}

# Words we should ignore when trying to guess a ticker from plain English
_STOPWORDS: Set[str] = {
    "PRICE", "TODAY", "NEWS", "TREND", "TRENDS", "AND", "OR", "THE", "A", "AN",
    "SHOW", "GIVE", "WHAT", "IS", "ARE", "FOR", "WITH", "OF", "ON", "TO", "IN",
    "PLEASE", "LATEST", "CURRENT", "UPDATE", "STOCK", "INFO",
}

# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------

def _is_us_exchange(code: Optional[str]) -> bool:
    return bool(code and code in _US_EXCHANGES)

def _safe_pct(a: Optional[float], b: Optional[float]) -> Optional[float]:
    try:
        if a is None or b is None or b == 0:
            return None
        return (a / b - 1.0) * 100.0
    except Exception:
        return None

# --------------------------------------------------------------------------------------
# Parsing & normalization
# --------------------------------------------------------------------------------------

def normalize_ticker(text: str) -> str:
    """
    Clean user input to a Yahoo-style US ticker:
    - strip $, spaces, weird chars
    - dot->dash for class shares (BRK.B -> BRK-B)
    - apply aliases (APPLE -> AAPL)
    - reject known non-US suffixes
    """
    s = (text or "").strip().upper()
    s = s.replace("$", "")
    s = re.sub(r"[^A-Z0-9\.\-\s]+", "", s).strip()
    s = re.sub(r"\s+", "", s)

    for suf in _NON_US_SUFFIXES:
        if s.endswith(suf):
            raise ValueError("Only US-listed symbols are supported.")

    # Map common names/variants
    if s in _ALIASES:
        s = _ALIASES[s]

    # Normalize class shares (if still dot form)
    if "." in s:
        s = s.replace(".", "-")

    # Basic validation (1–5 core chars, optional -CLASS)
    if not re.fullmatch(r"[A-Z0-9]{1,5}(?:-[A-Z]{1,2})?", s):
        raise ValueError("Unsupported ticker format (US symbols only).")

    return s

def extract_first_ticker(message: str) -> Optional[str]:
    """
    Try to pull a US ticker or known alias from free text.
    Precedence:
      1) $TICKER (e.g., $AAPL)
      2) Ticker with class (BRK.B / BRK-B)
      3) Known alias word (APPLE, TESLA, etc.)
      4) Uppercase token that looks like a ticker and not a stopword
    """
    msg = (message or "").strip()

    # 1) $TICKER
    m = re.search(r"\$([A-Za-z0-9]{1,10}(?:[.\-][A-Za-z]{1,2})?)\b", msg)
    if m:
        return m.group(1).upper()

    # 2) TICKER with dot/dash class
    m = re.search(r"\b([A-Za-z0-9]{1,10}(?:[.\-][A-Za-z]{1,2}))\b", msg)
    if m:
        return m.group(1).upper()

    # 3) Known aliases (scan words)
    for token in re.findall(r"[A-Za-z0-9\-\.\&']{2,20}", msg):
        up = token.upper()
        if up in _ALIASES:
            return up

    # 4) Uppercase-ish token that looks like a ticker (avoid stopwords)
    for token in re.findall(r"[A-Za-z0-9]{1,6}", msg):
        up = token.upper()
        if up in _STOPWORDS:
            continue
        if re.fullmatch(r"[A-Z0-9]{1,5}(?:-[A-Z]{1,2})?", up):
            return up

    return None

# --------------------------------------------------------------------------------------
# Core fetchers
# --------------------------------------------------------------------------------------

def get_quote(ticker: str) -> Dict[str, Any]:
    t = yf.Ticker(ticker)
    info = t.fast_info
    exchange = getattr(info, "exchange", None)

    try:
        price = float(info.last_price)
    except Exception:
        price = None

    # Fail early for non-US or unknown exchange
    if not _is_us_exchange(exchange):
        raise ValueError("Unknown or non-US symbol. Try a US ticker like AAPL, MSFT, BRK-B.")

    out = {
        "symbol": ticker,
        "currency": getattr(info, "currency", None),
        "exchange": exchange,
        "market_state": getattr(info, "market_state", None),
        "price": price,
        "previous_close": getattr(info, "previous_close", None),
        "day_high": getattr(info, "day_high", None),
        "day_low": getattr(info, "day_low", None),
        "year_high": getattr(info, "year_high", None),
        "year_low": getattr(info, "year_low", None),
        "market_cap": getattr(info, "market_cap", None),
        "trailing_pe": getattr(info, "trailing_pe", None),
        "volume": getattr(info, "last_volume", None) or getattr(info, "volume", None),
        "avg_volume": getattr(info, "ten_day_average_volume", None) or getattr(info, "three_month_average_volume", None),
    }
    out["change_pct"] = _safe_pct(out["price"], out["previous_close"]) if (out["price"] and out["previous_close"]) else None

    # If no price and no previous close, likely invalid/delisted
    if out["price"] is None and out["previous_close"] is None:
        raise ValueError("No real-time data found. The symbol may be inactive or delisted.")

    return out

def get_history_and_trends(ticker: str) -> Dict[str, Any]:
    t = yf.Ticker(ticker)
    try:
        hist = t.history(period="1y", interval="1d", auto_adjust=False)
    except Exception:
        return {"trend": {}, "samples": []}

    if hist is None or hist.empty:
        return {"trend": {}, "samples": []}

    hist = hist.reset_index()
    # Normalize timezone safely
    try:
        hist["Date"] = pd.to_datetime(hist["Date"]).dt.tz_localize("UTC").dt.tz_convert(EU_TZ)
    except Exception:
        hist["Date"] = pd.to_datetime(hist["Date"]).dt.tz_convert(EU_TZ)

    def pct_change(days: int) -> Optional[float]:
        if len(hist) < days + 1:
            return None
        recent = float(hist.iloc[-1]["Close"])
        past = float(hist.iloc[-1 - days]["Close"])
        return _safe_pct(recent, past)

    trend = {
        "1d": pct_change(1),
        "5d": pct_change(5),
        "1mo": pct_change(21),
        "3mo": pct_change(63),
        "6mo": pct_change(126),
        "1y": pct_change(252) if len(hist) >= 253 else None,
    }

    tail = hist.tail(60)[["Date", "Close"]]
    samples = [{"t": int(row["Date"].timestamp()), "close": float(row["Close"])} for _, row in tail.iterrows()]
    return {"trend": trend, "samples": samples}

def get_news(ticker: str, limit: int = 6) -> List[Dict[str, Any]]:
    t = yf.Ticker(ticker)
    try:
        raw = t.news or []
    except Exception:
        raw = []
    items: List[Dict[str, Any]] = []
    for item in raw[:limit]:
        ts = item.get("providerPublishTime")
        published = dt.datetime.fromtimestamp(ts, tz=EU_TZ).isoformat() if ts else None
        items.append({
            "title": item.get("title"),
            "link": item.get("link"),
            "publisher": item.get("publisher"),
            "published": published,
        })
    return items

def summarize_basic(ticker: str) -> Dict[str, Any]:
    q = get_quote(ticker)          # enforces US-only and validity
    h = get_history_and_trends(ticker)
    n = get_news(ticker)
    return {"quote": q, "history": h, "news": n}
