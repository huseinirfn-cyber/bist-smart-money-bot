import os
import sys
import time
import re
import threading
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==================== HEALTH CHECK SUNUCUSU ====================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status":"online","service":"BIST Smart Money Bot","time":"ok"}')
    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# ==================== BOT KONFİGÜRASYONU ====================
TOKEN = "8671096782:AAHGsXCuSVxk3ugzhFyyN4ZaTy0_WuPfz1Y"
CHAT_ID = "8874953570"

HEDEF_KURUMLAR = [
    "TERA", "PUSULA", "HEDEF", "DENİZ", "RE-PIE", "AURA", "ATLAS", 
    "ALBATROS", "KUVEYT TÜRK", "AHLATCI", "AZİMUT", "İSTANBUL PORTFÖY", "TACİRLER"
]
HEDEF_FONLAR = ["TLY", "THF", "DUH", "PHE", "DHV", "DOH", "PCS", "PUK", "KPC", "LTL", "MAC", "TI2", "IIH"]

DYNAMIC_WATCHLIST = {
    "TRMET", "BETAE", "TRALT", "BIGEN", "SDTTR", "PATEK", "ARDYZ", "ONCSM", 
    "NETCD", "MOBTL", "LOGO", "VBTYZ", "PAPIL", "ALVES", "AGROT", "BINHO", 
    "HOROZ", "LIDER", "MANAS", "ORZAX", "ANELE", "BARMA", "CVKMD", "KARYE", 
    "TEZOL", "KOPOL", "CWENE", "ALFAS", "EUPWR", "GESAN", "ASTOR", "SAYAS", 
    "TRHOL", "DAPGM", "TEHOL", "PEKGY", "SELEC", "MPARK", "TABGD", "GOKNR", 
    "KRVGD", "MEYSU", "EBEBK", "PASEU", "KTLEV", "GUNDG", "KARCL"
}

is_scanning = False

def send_tg(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True},
            timeout=10
        )
    except Exception as e:
        print("Telegram Gönderim Hatası:", e)

def get_tg_updates(offset=None):
    try:
        params = {"timeout": 1, "offset": offset}
        r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params=params, timeout=4)
        if r.status_code == 200:
            return r.json().get("result", [])
    except Exception:
        pass
    return []

def get_kap_disclosures():
    url = "https://www.kap.org.tr/tr/api/disclosures"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.kap.org.tr/"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print("KAP Hatası:", e)
    return []

def calculate_pre_pump_readiness(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 15:
        return {"score": 0, "phase": "YETERSIZ_VERI"}

    current_price = float(df['Close'].iloc[-1])
    low_52w = float(df['Low'].min())
    high_52w = float(df['High'].max())
    prim_52w = current_price / low_52w if low_52w > 0 else 1.0

    # Katı taban filtresi: 1.45x üstü (primli) elenir
    if prim_52w > 1.45:
        return {"score": 0, "phase": "AŞIRI PRİMLİ / TEPE RİSKİ"}

    high_20d = float(df['High'].tail(min(len(df), 20)).max())
    low_20d = float(df['Low'].tail(min(len(df), 20)).min())
    range_pct = ((high_20d - low_20d) / low_20d) * 100 if low_20d > 0 else 0

    if range_pct > 16.0:
        return {"score": 0, "phase": "VOLATİLİTE YÜKSEK"}

    # RSI (14G)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    current_rsi = float(rsi.iloc[-1]) if not rsi.empty and not np.isnan(rsi.iloc[-1]) else 50.0

    # CMF (Para Girişi)
    mf_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'])
    mf_multiplier = mf_multiplier.fillna(0)
    vol_sum = df['Volume'].rolling(min(len(df), 20)).sum()
    cmf_20 = (mf_multiplier * df['Volume']).rolling(min(len(df), 20)).sum() / vol_sum
    current_cmf = float(cmf_20.iloc[-1]) if not cmf_20.empty and not np.isnan(cmf_20.iloc[-1]) else 0

    ema_20 = float(df['Close'].ewm(span=min(len(df), 20), adjust=False).mean().iloc[-1])
    ema_50 = float(df['Close'].ewm(span=min(len(df), 50), adjust=False).mean().iloc[-1])
    above_ema20 = current_price >= ema_20

    score = 60
    reasons = []

    if prim_52w <= 1.25:
        score += 20
        reasons.append(f"Tam dipte (52H: {prim_52w:.2f}x)")
    else:
        score += 10
        reasons.append(f"Taban seviyesinde ({prim_52w:.2f}x)")

    if range_pct <= 9.0:
        score += 20
        reasons.append(f"Kuvvetli dar bant sıkışması (%{range_pct:.1f})")
    else:
        score += 10
        reasons.append(f"Yatay konsolidasyon (%{range_pct:.1f})")

    if current_cmf > 0.05:
        score += 10
        cmf_status = f"+{current_cmf:.2f} (Güçlü Para Girişi)"
    elif current_cmf >= -0.05:
        score += 5
        cmf_status = f"{current_cmf:+.2f} (Dengeli Para Akışı)"
    else:
        cmf_status = f"{current_cmf:.2f} (Nötr)"

    phase = "🔥 YATAYDAN DİKEYE GEÇİŞ (HAZIRLIK TAMAM)" if score >= 80 else "⏳ TABANDA SESSİZ MAL TOPLAMA"
    action = "GİRİŞ / İLK KADEME ALIM" if score >= 80 else "DÜŞÜŞTE DESTEKTEN TOPLA"

    stop_loss = round(current_price * 0.93, 2)
    target_1 = round(current_price * 1.25, 2)
    target_2 = round(current_price * 1.50, 2)
    target_3 = round(current_price * 2.00, 2)
    entry_low = round(current_price * 0.985, 2)
    entry_high = round(current_price * 1.01, 2)

    return {
        "score": score,
        "phase": phase,
        "action": action,
        "price": current_price,
        "low_52w": low_52w,
        "high_52w": high_52w,
        "prim_52w": prim_52w,
        "low_20d": low_20d,
        "high_20d": high_20d,
        "range_pct": range_pct,
        "ema_20": ema_20,
        "ema_50": ema_50,
        "rsi": current_rsi,
        "cmf_str": cmf_status,
        "entry_range": f"{entry_low:.2f} - {entry_high:.2f} TL",
        "stop_loss": stop_loss,
        "target_1": target_1,
        "target_2": target_2,
        "target_3": target_3,
        "reasons": reasons
    }

def format_rich_stock_card(ticker: str, data: dict) -> str:
    score = data["score"]
    badge = "🔥" if score >= 80 else ("⏳" if score >= 65 else "⚪")
    
    lines = [
        f"{badge} *{ticker}* ── *HAZIRLIK SKORU: %{score}*",
        f"────────────────────────────",
        f"📊 *1. AKÜMÜLASYON & PARA AKIŞI:*",
        f"• Para Girişi (CMF): `{data.get('cmf_str', 'Nötr')}`",
        f"• RSI (14G): `{data.get('rsi', 50):.1f} (Soğumuş/Taban)`",
        f"• 52H Dip Durumu: `{data.get('low_52w', 0):.2f} TL ({data.get('prim_52w', 1.0):.2f}x - Dipte)`",
        f"────────────────────────────",
        f"🎯 *2. WYCKOFF SIKIŞMA VE TEKNİK YAPI:*",
        f"• Güncel Fiyat: `{data.get('price', 0):.2f} TL`",
        f"• 20G Sıkışma Bandı: `{data.get('low_20d', 0):.2f} - {data.get('high_20d', 0):.2f} TL (%{data.get('range_pct', 0):.1f})`",
        f"• Hareketli Ortalamalar: `20 EMA: {data.get('ema_20', 0):.2f} TL | 50 EMA: {data.get('ema_50', 0):.2f} TL`",
        f"• Evre Kararı: *{data.get('phase')}*",
        f"────────────────────────────",
        f"💡 *3. ASİMETRİK OPERASYONEL TRADE PLANI:*",
        f"• 🎯 Önerilen Giriş Aralığı: `{data.get('entry_range')}`",
        f"• 🛑 Stop-Loss (%7): `{data.get('stop_loss', 0):.2f} TL` *(Kapanış şartı)*",
        f"• 🥇 Hedef 1 (Kısa Vade / +%25): `{data.get('target_1', 0):.2f} TL`",
        f"• 🚀 Hedef 2 (Ana Trend / +%50): `{data.get('target_2', 0):.2f} TL`",
        f"• 💎 Hedef 3 (Patlama / +%100): `{data.get('target_3', 0):.2f} TL`",
        f"• Risk / Ödül Oranı (R:R): `1 : 7.1`",
        f"────────────────────────────",
        f"📝 *Strateji Notu:* Fiyat 20 EMA üzerinde konsolide oldu, satıcılar kurudu. İlk hacim teyidinde yataydan dikeye geçiş potansiyeli yüksek.",
        f"🔗 [TradingView Grafiği](https://tr.tradingview.com/symbols/BIST-{ticker}/) | [KAP Şirket Bilgisi](https://www.kap.org.tr/tr/sirket-bilgileri/genel/{ticker})"
    ]
    return "\n".join(lines)

def run_watchlist_scan_async():
    global is_scanning
    if is_scanning:
        send_tg("⏳ Zaten devam eden bir tarama var, lütfen birkaç saniye bekleyin.")
        return

    is_scanning = True
    active_pool = list(DYNAMIC_WATCHLIST)
    send_tg(f"⏳ *BIST DETAYLI TABAN SIKIŞMASI TARANIYOR...*\n📊 Taranan Hisse Sayısı: `{len(active_pool)}`\nLütfen 5-8 saniye bekleyin.")
    results = []
    
    try:
        import yfinance as yf
        symbols = [f"{t}.IS" for t in active_pool]
        batch_data = yf.download(symbols, period="6mo", interval="1d", group_by='ticker', threads=True, progress=False, timeout=10)
        
        for ticker in active_pool:
            sym = f"{ticker}.IS"
            try:
                if sym in batch_data:
                    df_t = batch_data[sym].dropna()
                    if not df_t.empty and len(df_t) >= 15:
                        res = calculate_pre_pump_readiness(df_t)
                        if res.get("score", 0) >= 60:
                            results.append({"ticker": ticker, **res})
            except Exception:
                pass
    except Exception as e:
        print("Tarama Hatası:", e)

    if not results:
        send_tg("ℹ️ *TARAMA TAMAMLANDI*\n\nTaranan hisseler arasında şu an katı taban sıkışmasında olan uygun hisse bulunamadı (Diğer hisseler primli veya dalgalı).")
        is_scanning = False
        return

    results.sort(key=lambda x: x["score"], reverse=True)

    send_tg(f"📊 *BIST YATAYDAN DİKEYE GEÇİŞ (TABAN AKÜMÜLASYON) RAPORU* 📊\n🛡 *Filtre:* 52H Dip (≤ 1.45x) & Dar Sıkışma\n──────────────")

    for item in results[:3]:
        card_text = format_rich_stock_card(item["ticker"], item)
        send_tg(card_text)
        time.sleep(0.5)

    is_scanning = False
