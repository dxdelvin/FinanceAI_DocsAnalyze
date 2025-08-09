# app/routers/ai_chat.py
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, Request, HTTPException, Query, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..services.yahoo import summarize_basic, extract_first_ticker, normalize_ticker

# ---- Router + templates ----------------------------------------------------
router = APIRouter(tags=["ai"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))

# ---- Page ------------------------------------------------------------------
@router.get("/ai", response_class=HTMLResponse)
def ai_page(request: Request):
    # Render the UI only; backend wired via endpoints below.
    return templates.TemplateResponse(
        "ai.html",
        {"request": request, "is_authed": False, "my_sub": ""}  # adjust later for auth
    )

# ---- Structured stock endpoint (US-only) -----------------------------------
@router.get("/api/ai/stock")
def ai_stock(sym: str = Query(..., description="US ticker like AAPL, MSFT, BRK-B")):
    try:
        sym = normalize_ticker(sym)               # validates US-only and normalizes
        data = summarize_basic(sym)               # {quote, history, news}
        if not data or not data.get("quote", {}).get("price"):
            raise HTTPException(status_code=404, detail=f"No data for {sym}")
        return data
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Yahoo fetch failed: {e}")

# ---- Chat endpoint returning {answer, report} as your UI expects -----------
@router.post("/api/ai/chat")
async def ai_chat(payload: Dict[str, Any] = Body(...)):
    """
    Accepts: { "message": "aapl price today + news" }
    Returns: { "answer": "...", "report": { "summary": "...", "charts": [ ... ] } }
    """
    msg = (payload.get("message") or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="message is required")

    raw = extract_first_ticker(msg)
    if not raw:
        raise HTTPException(status_code=400, detail="US symbols only. Try like: 'AAPL price today' or 'BRK-B news'")

    try:
        ticker = normalize_ticker(raw)            # enforces US-only & BRK.B -> BRK-B
        data = summarize_basic(ticker)            # {quote, history, news}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Yahoo fetch failed: {e}")

    q   = data.get("quote", {})
    h   = data.get("history", {})
    tr  = h.get("trend", {}) or {}
    smp = h.get("samples", []) or []
    nws = data.get("news", [])[:5]

    # ---- Build human answer -------------------------------------------------
    price = q.get("price")
    chg   = q.get("change_pct")
    cur   = q.get("currency") or "USD"
    yr_lo = q.get("year_low")
    yr_hi = q.get("year_high")

    def fmt_num(x, nd=2):
        return f"{x:.{nd}f}" if isinstance(x, (int, float)) else "—"

    chg_txt   = (f"{chg:+.2f}%" if isinstance(chg, (int, float)) else "—")
    price_txt = (f"{fmt_num(price)} {cur}" if isinstance(price, (int, float)) else "—")
    range_txt = (f"{fmt_num(yr_lo)}–{fmt_num(yr_hi)} {cur}"
                 if isinstance(yr_lo, (int, float)) and isinstance(yr_hi, (int, float))
                 else "—")

    trend_bits: List[str] = []
    for k in ["1d", "5d", "1mo", "3mo", "6mo", "1y"]:
        v = tr.get(k)
        if isinstance(v, (int, float)):
            trend_bits.append(f"{k}: {v:+.1f}%")
    trend_line = ", ".join(trend_bits) if trend_bits else "No trend data"

    answer = f"{ticker}: {price_txt} ({chg_txt} today). Trend — {trend_line}. 52w range: {range_txt}."

    # ---- Build simple chart config for ai.html ------------------------------
    pts_map = {}
    for s in smp:
        try:
            ts = int(s["t"])
            pts_map[ts] = float(s["close"])   # last value wins if duplicate ts
        except Exception:
            continue

    pts = sorted(pts_map.items(), key=lambda x: x[0])  # [(ts, close), ...]
    MAX_POINTS = 30
    if len(pts) > MAX_POINTS:
        step = max(1, len(pts) // MAX_POINTS)
        pts = pts[::step][:MAX_POINTS]

    labels = [dt.datetime.fromtimestamp(ts).strftime("%b %d") for ts, _ in pts]
    values = [v for _, v in pts]

    charts = []
    if labels and values:
        # compute padded y-range so the frontend can fix the axis (prevents jitter)
        y_min = min(values); y_max = max(values)
        pad = max(0.01, (y_max - y_min) * 0.05)
        y_min -= pad; y_max += pad

        charts.append({
            "type": "line",
            "labels": labels,
            "series": [
                {"name": f"{ticker} Close", "data": values}
            ],
            # optional hints your UI can use to turn off animation & lock axis
            "options": {
                "animate": False,
                "yMin": y_min,
                "yMax": y_max
            }
        })

    # ---- News digest in report.summary -------------------------------------
    news_lines = []
    for n in nws:
        t = n.get("title"); pub = n.get("publisher"); when = n.get("published")
        if t:
            news_lines.append(f"• {t} — {pub or ''} ({when or ''})")
    news_txt = ("\n".join(news_lines)) if news_lines else "No recent Yahoo news."

    report = {
        "summary": f"{ticker} quick view:\n{answer}\n\nLatest news:\n{news_txt}",
        "charts": charts,
    }

    return {"answer": answer, "report": report}

# ---- Placeholder: not implemented yet --------------------------------------
@router.post("/api/ai/upload")
async def ai_upload():
    raise HTTPException(status_code=501, detail="Upload endpoint not implemented yet.")
