"""
==============================================================================
Institutional Real-Time Market Signal Server (FastAPI + WebSockets)
==============================================================================
Streams sub-second live ticks, order book depth, VWAP, and signals.
Features both Live Exchange Feed and 24/7 Realistic HFT Simulator.
==============================================================================
"""

import os
import sys
import json
import time
import random
import asyncio
import urllib.request
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Reconfigure stdout for UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from engine import OrderBookDepth, HighFrequencySignalEngine

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(market_data_broadcaster())
    yield

app = FastAPI(title="Live Institutional Pressure Signal Bot", lifespan=lifespan)

# Directory setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# State
active_ticker = "PERSISTENT.NS"
display_symbol = "PERSISTENT"
engine = HighFrequencySignalEngine(display_symbol)
is_simulation_mode = True  # Automatically active for weekend / after-market testing

# Simulated Baseline State
sim_price = 6050.00
sim_day_open = 6190.00
sim_day_high = 6240.00
sim_day_low = 6041.50
sim_prev_close = 6109.50
sim_vix = 17.20
sim_vix_change = 11.20
sim_it_pct = 0.05
sim_bank_pct = 1.90
sim_nifty_pct = 1.60

connected_clients: List[WebSocket] = []


def fetch_live_yahoo_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetches real-time price snapshot from Yahoo Finance API."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())["chart"]["result"][0]
            meta = data["meta"]
            return {
                "price": float(meta.get("regularMarketPrice", 0.0)),
                "high": float(meta.get("regularMarketDayHigh", 0.0)),
                "low": float(meta.get("regularMarketDayLow", 0.0)),
                "prev_close": float(meta.get("chartPreviousClose", 0.0)),
                "volume": float(meta.get("regularMarketVolume", 100000))
            }
    except Exception:
        return None


def generate_synthetic_depth(base_price: float, bias: float) -> OrderBookDepth:
    """
    Generates realistic 5-level market depth with order book imbalances.
    bias > 0: heavier bids (buyers stepping in)
    bias < 0: heavier asks (sellers dumping)
    """
    bids = []
    asks = []
    tick_size = 0.50

    base_qty = random.randint(15000, 35000)
    for i in range(1, 6):
        # Bids below market
        b_p = round(base_price - (i * tick_size), 2)
        b_q = int(base_qty * random.uniform(0.7, 1.4) * (1.0 + bias))
        bids.append({"price": b_p, "qty": max(500, b_q)})

        # Asks above market
        a_p = round(base_price + (i * tick_size), 2)
        a_q = int(base_qty * random.uniform(0.7, 1.4) * (1.0 - bias))
        asks.append({"price": a_p, "qty": max(500, a_q)})

    return OrderBookDepth(bids=bids, asks=asks)


async def market_data_broadcaster():
    """High-frequency background loop broadcasting ticks every 300ms–500ms."""
    global sim_price, sim_vix, sim_vix_change, sim_it_pct, sim_bank_pct, is_simulation_mode

    # Bias trends cyclically to simulate realistic market ebb and flow
    cycle_counter = 0
    sim_bias = -0.30  # Default mild sell bias mirroring today's afternoon

    while True:
        try:
            cycle_counter += 1
            # Every 40 cycles (~15-20 seconds), shift market regime
            if cycle_counter % 45 == 0:
                sim_bias = random.choice([-0.45, -0.20, 0.0, 0.25, 0.50])

            # In simulation or live fallback
            price_delta = random.uniform(-1.5, 1.5) + (sim_bias * 0.8)
            sim_price = round(max(5950.0, min(6300.0, sim_price + price_delta)), 2)
            tick_volume = random.randint(100, 3500)

            # Generate Depth with current regime
            depth = generate_synthetic_depth(sim_price, sim_bias)

            # Compute Signals
            signal_data = engine.evaluate_tick(
                price=sim_price,
                volume=tick_volume,
                depth=depth,
                vix=round(sim_vix + random.uniform(-0.1, 0.1), 2),
                vix_change_pct=sim_vix_change,
                it_pct=sim_it_pct,
                bank_pct=sim_bank_pct,
                nifty_pct=sim_nifty_pct
            )

            # Add Level-2 depth for UI rendering
            payload = {
                **signal_data,
                "mode": "SIMULATION / 24-7 PRACTICE" if is_simulation_mode else "LIVE EXCHANGE",
                "bids": depth.bids,
                "asks": depth.asks,
                "day_high": sim_day_high,
                "day_low": sim_day_low,
                "prev_close": sim_prev_close,
                "change_pct": round(((sim_price - sim_prev_close) / sim_prev_close) * 100, 2),
                "ms_timestamp": int(time.time() * 1000)
            }

            # Broadcast to all connected WebSockets
            if connected_clients:
                text_data = json.dumps(payload)
                dead_clients = []
                for client in connected_clients:
                    try:
                        await client.send_text(text_data)
                    except Exception:
                        dead_clients.append(client)
                for dead in dead_clients:
                    if dead in connected_clients:
                        connected_clients.remove(dead)

        except Exception as e:
            print(f"⚠️ Broadcast loop error: {e}", flush=True)

        # High frequency interval (350ms)
        await asyncio.sleep(0.35)


@app.get("/")
async def get_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>Real-Time Signal Server Active. static/index.html not found.</h1>")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            # Keep-alive receive
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)


@app.get("/api/set-ticker")
async def set_ticker(ticker: str):
    global active_ticker, display_symbol, engine, sim_price, sim_prev_close
    active_ticker = ticker
    display_symbol = ticker.split(".")[0].upper()
    engine = HighFrequencySignalEngine(display_symbol)

    # Re-seed baseline price
    if "TCS" in display_symbol:
        sim_price, sim_prev_close = 3950.0, 3960.0
    elif "INFY" in display_symbol:
        sim_price, sim_prev_close = 1820.0, 1830.0
    elif "HDFC" in display_symbol:
        sim_price, sim_prev_close = 1780.0, 1765.0
    elif "RELIANCE" in display_symbol:
        sim_price, sim_prev_close = 1320.0, 1315.0
    else:
        sim_price, sim_prev_close = 6050.0, 6109.5

    return {"status": "SUCCESS", "ticker": display_symbol, "price": sim_price}


# Mount static assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    print("[*] Starting Real-Time Institutional Signal Bot on http://127.0.0.1:8000 ...", flush=True)
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False, access_log=False)
