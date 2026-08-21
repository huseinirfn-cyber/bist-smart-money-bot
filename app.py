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

# ==================== HEALTH CHECK & AUTO-HEALING SUNUCUSU ====================
worker_thread = None

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global worker_thread
        if worker_thread is None or not worker_thread.is_alive():
            print("⚠️ Watchdog: Bot iş parçacığı yeniden başlatılıyor...")
            start_bot_thread()

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status":"online","service":"BIST Smart Money Fund Ledger","thread_alive":true}')
    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# ==================== BOT VE FON DEFTERİ YAPILANDIRMASI ====================
TOKEN = "8671096782:AAHGsXCuSVxk3ugzhFyyN4ZaTy0_WuPfz1Y"
CHAT_ID = "8874953570"

HEDEF_KURUMLAR = [
    "TERA", "PUSULA", "HEDEF", "DENİZ", "RE-PIE", "AURA", "ATLAS", 
    "ALBATROS", "KUVEYT TÜRK", "AHLATCI", "AZİMUT", "İSTANBUL PORTFÖY", "TACİRLER"
]
HEDEF_FONLAR = ["TLY", "THF", "DUH", "PHE", "DHV", "DOH", "PCS", "PUK", "KPC", "LTL", "MAC", "TI2", "IIH"]

# ⛔ TOKSİK VE RİSKLİ ŞİRKETLER KARA LİSTESİ
KARA_LISTE = {"BARMA", "MEGAP", "YESIL", "AVOD", "DERAS", "KENT", "KUVVA", "ISBIR", "ROYAL"}

DYNAMIC_WATCHLIST = {
    "TRMET", "BETAE", "TRALT", "BIGEN", "SDTTR", "PATEK", "ARDYZ", "ONCSM", 
    "NETCD", "MOBTL", "LOGO", "VBTYZ", "PAPIL", "ALVES", "AGROT", "BINHO", 
    "HOROZ", "LIDER", "MANAS", "ORZAX", "ANELE", "CVKMD", "KARYE", "TEZOL", 
    "KOPOL", "CWENE", "ALFAS", "EUPWR", "GESAN", "ASTOR", "SAYAS", "TRHOL", 
    "DAPGM", "TEHOL", "PEKGY", "SELEC", "MPARK", "TABGD", "GOKNR", "KRVGD", 
    "MEYSU", "EBEBK", "PASEU", "KTLEV", "GUNDG", "KARCL", "OZATD", "ODINE"
}

# 🏛 FONLARIN HİSSEDARLIK VE PAY ALIM/SATIM İŞLEM DEFTERİ
FUND_TRANSACTION_HISTORY = [
    {"date": "19.08.2026", "inst": "TERA PORTFÖY", "ticker": "OZATD", "action": "ALIM", "lot": 1780560, "ratio": 20.20, "price": "26.50 TL"},
    {"date": "12.08.2026", "inst": "TERA PORTFÖY", "ticker": "OZATD", "action": "ALIM", "lot": 2890000, "ratio": 18.50, "price": "25.00 TL"},
    {"date": "05.08.2026", "inst": "DENİZ PORTFÖY", "ticker": "OZATD", "action": "ALIM", "lot": 850000, "ratio": 6.40, "price": "24.20 TL"},
    
    {"date": "18.08.2026", "inst": "PUSULA PORTFÖY", "ticker": "ODINE", "action": "ALIM", "lot": 950000, "ratio": 14.50, "price": "44.00 TL"},
    {"date": "10.08.2026", "inst": "İŞ PORTFÖY (TTE)", "ticker": "ODINE", "action": "ALIM", "lot": 1200000, "ratio": 14.57, "price": "46.50 TL"},
    
    {"date": "17.08.2026", "inst": "AHLATCI PORTFÖY", "ticker": "TRMET", "action": "ALIM", "lot": 1950000, "ratio": 8.20, "price": "125.00 TL"},
    {"date": "14.08.2026", "inst": "DENİZ PORTFÖY", "ticker": "TRMET", "action": "ALIM", "lot": 850000, "ratio": 4.10, "price": "128.50 TL"},
    
    {"date": "16.08.2026", "inst": "PUSULA PORTFÖY", "ticker": "PASEU", "action": "ALIM", "lot": 1311694, "ratio": 11.91, "price": "17.50 TL"},
    {"date": "11.08.2026", "inst": "PUSULA PORTFÖY", "ticker": "PASEU", "action": "ALIM", "lot": 850000, "ratio": 9.50, "price": "16.80 TL"},
    
    {"date": "15.08.2026", "inst": "TERA PORTFÖY", "ticker": "KARCL", "action": "ALIM", "lot": 2200000, "ratio": 9.10, "price": "14.50 TL"},
    {"date": "10.08.2026", "inst": "HEDEF PORTFÖY", "ticker": "KARCL", "action": "ALIM", "lot": 1450000, "ratio": 6.80, "price": "15.00 TL"},

    {"date": "15.08.2026", "inst": "KUVEYT TÜRK (KPC)", "ticker": "MPARK", "action": "ALIM", "lot": 3120000, "ratio": 9.40, "price": "285.00 TL"},
    {"date": "08.08.2026", "inst": "MARMARA CAPITAL (MAC)", "ticker": "MPARK", "action": "ALIM", "lot": 1850000, "ratio": 6.20, "price": "290.00 TL"},

    {"date": "14.08.2026", "inst": "MARMARA CAPITAL (MAC)", "ticker": "LOGO", "action": "ALIM", "lot": 1420000, "ratio": 7.80, "price": "115.00 TL"},
    {"date": "07.08.2026", "inst": "İŞ PORTFÖY (TTE)", "ticker": "LOGO", "action": "ALIM", "lot": 2850000, "ratio": 6.40, "price": "118.50 TL"}
]

is_scanning = False

def send_tg(msg):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10
        )
        if r.status_code != 200:
            clean_text = msg.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "").replace("<i>", "").replace("</i>", "")
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": clean_text, "disable_web_page_preview": True},
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

def calculate_stock_fund_summary(ticker_input: str) -> str:
    """
    Belirli bir hissede fonların net alışlarını, güncel sermaye paylarını (%5, %10 vb.)
    ve toplam kilitlenen lot miktarını hesaplar.
    """
    ticker_clean = str(ticker_input).upper().replace("/HISSE", "").replace("HISSE", "").replace("/FON", "").replace("FON", "").strip()
    txs = [t for t in FUND_TRANSACTION_HISTORY if t["ticker"] == ticker_clean]
    
    if not txs:
        return (
            f"🔍 <b>{ticker_clean}</b> için hedef kurumsal fonlardan (Tera, Pusula, Hedef vb.) henüz KAP'a %5+ pay alım/eşik bildirimi düşmedi.\n\n"
            f"💡 <i>Fon alımları gerçekleşip KAP bildirimi geldiğinde sistem otomatik olarak deftere kaydedecektir.</i>"
        )

    inst_summary = {}
    total_lot = 0
    
    for t in txs:
        inst = t["inst"]
        if inst not in inst_summary:
            inst_summary[inst] = {
                "latest_ratio": t.get("ratio", 0),
                "total_lot": 0,
                "tx_count": 0,
                "latest_date": t.get("date", "-"),
                "avg_price_ref": t.get("price", "-")
            }
        inst_summary[inst]["total_lot"] += t.get("lot", 0)
        inst_summary[inst]["tx_count"] += 1
        total_lot += t.get("lot", 0)

    total_fund_ratio = sum(v["latest_ratio"] for v in inst_summary.values() if v["latest_ratio"])

    lines = [
        f"🏛 <b>{ticker_clean} ── KURUMSAL FON PAYI VE ALIM DEFTERİ</b> 🏛",
        f"────────────────────────────",
        f"📊 <b>FON BAZINDA GÜNCEL PAY ORANLARI:</b>"
    ]
    
    for inst, data in inst_summary.items():
        lines.append(
            f"• <b>{inst}:</b> Güncel Pay: <code>%{data['latest_ratio']}</code>\n"
            f"  └ <i>Son İşlem:</i> {data['latest_date']} | <i>Lot:</i> {data['total_lot']:,.0f} | <i>Fiyat Ref:</i> {data['avg_price_ref']}"
        )
        
    lines.extend([
        f"────────────────────────────",
        f"🔒 <b>Hissedeki Toplam Fon Kilitlenmesi:</b> <code>%{total_fund_ratio:.2f}</code>",
        f"📦 <b>Fonların Toplam Aldığı Lot:</b> <code>{total_lot:,.0f} Lot</code>",
        f"────────────────────────────",
        f"📋 <b>KAP Pay Alım/Satım Bildirim Geçmişi:</b>"
    ])
    
    for i, t in enumerate(txs[:5], 1):
        lines.append(f"{i}. <b>{t['date']}</b> | {t['inst']}: <code>{t['action']}</code> ({t['lot']:,.0f} Lot, Pay: %{t['ratio']})")

    lines.extend([
        f"────────────────────────────",
        f"🔗 <a href='https://tr.tradingview.com/symbols/BIST-{ticker_clean}/'>TradingView Grafiği</a> | <a href='https://www.kap.org.tr/tr/sirket-bilgileri/genel/{ticker_clean}'>KAP Sayfası</a>"
    ])
    
    return "\n".join(lines)

def calculate_pre_pump_readiness(df: pd.DataFrame, ticker: str = "") -> dict:
    if df.empty or len(df) < 15:
        return {"allow": False, "phase": "YETERSIZ_VERI"}

    if ticker in KARA_LISTE:
        return {"allow": False, "phase": "KARA LİSTE / KONKORDATO RİSKİ"}

    current_price = float(df['Close'].iloc[-1])
    low_52w = float(df['Low'].min())
    high_52w = float(df['High'].max())
    prim_52w = current_price / low_52w if low_52w > 0 else 1.0

    # ⛔ KATI TABAN KURALI: 52H Dibe göre 1.45x'ten fazla primliyse DİREKT ELE
    if prim_52w > 1.45:
        return {"allow": False, "phase": "AŞIRI PRİMLİ / TEPE RİSKİ"}

    high_20d = float(df['High'].tail(min(len(df), 20)).max())
    low_20d = float(df['Low'].tail(min(len(df), 20)).min())
    range_pct = ((high_20d - low_20d) / low_20d) * 100 if low_20d > 0 else 0

    if range_pct > 16.0:
        return {"allow": False, "phase": "VOLATİLİTE YÜKSEK"}

    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    current_rsi = float(rsi.iloc[-1]) if not rsi.empty and not np.isnan(rsi.iloc[-1]) else 50.0

    mf_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'])
    mf_multiplier = mf_multiplier.fillna(0)
    vol_sum = df['Volume'].rolling(min(len(df), 20)).sum()
    cmf_20 = (mf_multiplier * df['Volume']).rolling(min(len(df), 20)).sum() / vol_sum
    current_cmf = float(cmf_20.iloc[-1]) if not cmf_20.empty and not np.isnan(cmf_20.iloc[-1]) else 0

    ema_20 = float(df['Close'].ewm(span=min(len(df), 20), adjust=False).mean().iloc[-1])
    ema_50 = float(df['Close'].ewm(span=min(len(df), 50), adjust=False).mean().iloc[-1])

    score = 60
    if prim_52w <= 1.25: score += 20
    if range_pct <= 9.0: score += 20
    if current_cmf > 0.05: score += 10

    cmf_status = f"+{current_cmf:.2f} (Güçlü Para Girişi)" if current_cmf > 0.05 else (f"{current_cmf:+.2f} (Dengeli Para Akışı)" if current_cmf >= -0.05 else f"{current_cmf:.2f} (Nötr)")

    # Fon Sahipliği Durumu
    txs = [t for t in FUND_TRANSACTION_HISTORY if t["ticker"] == ticker]
    fund_lock_ratio = sum(t.get("ratio", 0) for t in txs) if txs else 0
    fund_info_str = f"%{fund_lock_ratio:.1f} (Kurumsal Toplanıyor)" if fund_lock_ratio > 0 else "İzleme Havuzunda"

    phase = "🔥 YATAYDAN DİKEYE GEÇİŞ (TABAN KIRILIMI)" if score >= 80 else "⏳ TABANDA SESSİZ MAL TOPLAMA"
    action = "GİRİŞ / İLK KADEME ALIM" if score >= 80 else "DÜŞÜŞTE DESTEKTEN TOPLA"

    stop_loss = round(current_price * 0.93, 2)
    target_1 = round(current_price * 1.25, 2)
    target_2 = round(current_price * 1.50, 2)
    target_3 = round(current_price * 2.00, 2)
    entry_low = round(current_price * 0.985, 2)
    entry_high = round(current_price * 1.01, 2)

    return {
        "allow": True,
        "score": score,
        "phase": phase,
        "action": action,
        "price": current_price,
        "fund_info_str": fund_info_str,
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
        "target_3": target_3
    }

def format_rich_stock_card(ticker: str, data: dict) -> str:
    score = data.get("score", 75)
    badge = "🔥" if score >= 80 else "⏳"
    
    lines = [
        f"{badge} <b>{ticker}</b> ── <b>HAZIRLIK SKORU: %{score}</b>",
        f"────────────────────────────",
        f"🎯 <b>Evre Durumu:</b> <b>{data.get('phase')}</b>",
        f"🏛 <b>Fon Saklama Durumu:</b> <code>{data.get('fund_info_str')}</code>",
        f"────────────────────────────",
        f"📊 <b>AKÜMÜLASYON & PARA AKIŞI:</b>",
        f"• Para Girişi (CMF): <code>{data.get('cmf_str')}</code>",
        f"• RSI (14G): <code>{data.get('rsi', 50):.1f} (Aşırı Alımdan Uzak / Taban)</code>",
        f"• 52H Dip Durumu: <code>{data.get('low_52w', 0):.2f} TL ({data.get('prim_52w', 1.0):.2f}x - Dipte)</code>",
        f"────────────────────────────",
        f"🎯 <b>WYCKOFF SIKIŞMA VE TEKNİK YAPI:</b>",
        f"• Güncel Fiyat: <code>{data.get('price', 0):.2f} TL</code>",
        f"• 20G Sıkışma Bandı: <code>{data.get('low_20d', 0):.2f} - {data.get('high_20d', 0):.2f} TL (%{data.get('range_pct', 0):.1f})</code>",
        f"• Hareketli Ortalamalar: <code>20 EMA: {data.get('ema_20', 0):.2f} TL | 50 EMA: {data.get('ema_50', 0):.2f} TL</code>",
        f"────────────────────────────",
        f"💡 <b>ASİMETRİK OPERASYONEL TRADE PLANI:</b>",
        f"• 🎯 Önerilen Giriş Aralığı: <code>{data.get('entry_range')}</code>",
        f"• 🛑 Stop-Loss (%7): <code>{data.get('stop_loss', 0):.2f} TL</code> (Kapanış şartı)",
        f"• 🥇 Hedef 1 (+%25): <code>{data.get('target_1', 0):.2f} TL</code>",
        f"• 🚀 Hedef 2 (+%50): <code>{data.get('target_2', 0):.2f} TL</code>",
        f"• 💎 Hedef 3 (+%100): <code>{data.get('target_3', 0):.2f} TL</code>",
        f"• Risk / Ödül Oranı: <b>1 : 7.1</b>",
        f"────────────────────────────",
        f"🔗 <a href=\"https://tr.tradingview.com/symbols/BIST-{ticker}/\">TradingView Grafiği</a> | <a href=\"https://www.kap.org.tr/tr/sirket-bilgileri/genel/{ticker}\">KAP Şirket Bilgisi</a>"
    ]
    return "\n".join(lines)

def run_watchlist_scan_async():
    global is_scanning
    if is_scanning:
        send_tg("⏳ Zaten devam eden bir tarama var, lütfen birkaç saniye bekleyin.")
        return

    is_scanning = True
    active_pool = [t for t in DYNAMIC_WATCHLIST if t not in KARA_LISTE]
    send_tg(f"⏳ <b>BIST KURUMSAL FON VE TABAN SIKIŞMASI TARANIYOR...</b>\n🛡 52H Dip (≤ 1.45x) & Konkordato Koruması Devrede\n📊 Taranan Hisse: <code>{len(active_pool)}</code>\nLütfen 5-8 saniye bekleyin.")
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
                        res = calculate_pre_pump_readiness(df_t, ticker)
                        if res.get("allow", False):
                            results.append({"ticker": ticker, **res})
            except Exception:
                pass
    except Exception as e:
        print("Tarama Hatası:", e)

    if not results:
        send_tg("ℹ️ <b>TARAMA TAMAMLANDI</b>\nTaranan hisseler arasında şu an güvenli taban sıkışmasında olan hisse bulunamadı.")
        is_scanning = False
        return

    results.sort(key=lambda x: x["score"], reverse=True)

    send_tg(f"📊 <b>BIST GÜVENLİ TABAN SIKIŞMASI RAPORU</b> 📊\n🛡 <i>Filtre: Fon Toplama, 52H Dip (≤ 1.45x) & Dar Sıkışma</i>\n──────────────")

    for item in results[:4]:
        card_text = format_rich_stock_card(item["ticker"], item)
        send_tg(card_text)
        time.sleep(0.5)

    is_scanning = False

def parse_disclosure_data(d):
    global DYNAMIC_WATCHLIST, FUND_TRANSACTION_HISTORY
    c_name = d.get("companyName", "").upper()
    title = d.get("title", "")
    summary = d.get("summary", "")
    full_text = f"{title} {summary}".upper()
    
    is_target_inst = any(k in c_name for k in HEDEF_KURUMLAR)
    is_target_fund = any(f"[{f}]" in full_text or f" {f} " in full_text for f in HEDEF_FONLAR)
    is_share_action = any(k in full_text for k in [
        "PAY ALIM", "PAY SATIM", "SERMAYE PİYASASI ARACI ALIM", "SINIRINA ULAŞTI", "ORANINA ULAŞTI", "PORTFÖY DAĞILIM", "ÖZEL DURUM"
    ])

    if not ((is_target_inst or is_target_fund) and is_share_action):
        return None

    ticker_match = re.search(r"\b([A-Z]{4,5})\b\s*(PAY|HİSSE|ORTAKLIK|A\.Ş)", full_text)
    ticker = ticker_match.group(1) if ticker_match else "BELİRTİLMEDİ"
    
    if ticker != "BELİRTİLMEDİ" and ticker not in KARA_LISTE and ticker not in DYNAMIC_WATCHLIST:
        DYNAMIC_WATCHLIST.add(ticker)

    ratio_match = re.search(r"%\s*([0-9]+[,\.][0-9]+)", full_text)
    ratio = float(ratio_match.group(1).replace(",", ".")) if ratio_match else None

    lot_match = re.search(r"([0-9\.,]+)\s*ADET", full_text)
    lot_str = lot_match.group(1).replace(".", "").replace(",", ".") if lot_match else None
    lot = float(lot_str) if lot_str else 0

    price_match = re.search(r"([0-9]+[,\.][0-9]+)\s*-\s*([0-9]+[,\.][0-9]+)\s*TL", full_text)
    if not price_match:
        price_match = re.search(r"([0-9]+[,\.][0-9]+)\s*TL\s*(FİYATTAN|FİYATLA)", full_text)
    price_info = price_match.group(0) if price_match else "Bildirim detayında"

    action = "ALIM" if any(w in full_text for w in ["ALDI", "ALINDI", "EDİNİLDİ", "ALIM"]) else ("SATIM" if "SAT" in full_text else "EŞİK BİLDİRİMİ")

    if ticker != "BELİRTİLMEDİ" and ratio:
        FUND_TRANSACTION_HISTORY.insert(0, {
            "date": datetime.now().strftime("%d.%m.%Y"),
            "inst": c_name,
            "ticker": ticker,
            "action": action,
            "lot": lot,
            "ratio": ratio,
            "price": price_info
        })

    return {
        "ticker": ticker,
        "inst": c_name,
        "action": action,
        "ratio": ratio,
        "lot": lot,
        "price_info": price_info,
        "title": title,
        "id": str(d.get("disclosureIndex", "")),
        "date": d.get("publishDate", "")
    }

def bot_worker():
    print("🚀 BIST Smart Money Worker Başlatıldı.")
    send_tg("🟢 <b>BIST SMART MONEY FON DEFTERİ AKTİF (7/24 KESİNTİSİZ)</b>\n\n• Hissedeki Fon Payı & Net Alış Hesabı: <code>/hisse TRMET</code> veya <code>/hisse OZATD</code>\n• Taban Sıkışması Taraması: <code>/tara</code>\n• Canlı fon pay bildirimleri anında telefonunuza düşer!")
    
    seen = set()
    last_update_id = None
    last_kap_check = 0

    while True:
        try:
            updates = get_tg_updates(offset=last_update_id)
            for u in updates:
                last_update_id = u["update_id"] + 1
                msg = u.get("message", {})
                text = msg.get("text", "").strip()
                text_lower = text.lower()
                
                # /hisse HISSE_KODU veya /fon HISSE_KODU Sorgusu
                if text_lower.startswith("/hisse") or text_lower.startswith("hisse") or text_lower.startswith("/fon") or text_lower.startswith("fon"):
                    parts = text.split()
                    if len(parts) >= 2:
                        target_ticker = str(parts).strip().upper()
                        summary_msg = calculate_stock_fund_summary(target_ticker)
                        send_tg(summary_msg)
                    else:
                        send_tg("ℹ️ Lütfen hisse kodu belirtin. Örnek: <code>/hisse OZATD</code> veya <code>/hisse TRMET</code>")
                elif text_lower in ["/tara", "tara", "/hazirlik", "hazirlik", "/analiz"]:
                    threading.Thread(target=run_watchlist_scan_async, daemon=True).start()
                elif text_lower in ["/start", "start", "/yardim"]:
                    send_tg("📌 <b>KOMUTLAR:</b>\n• <code>/hisse HISSE</code> : Fonların o hissedeki net pay oranını (%5, %10 vb.), son alımlarını ve toplam kilitlenen lotu döker (Örn: <code>/hisse OZATD</code>).\n• <code>/tara</code> : Fonların mal topladığı ve tabanda sıkışmış en güçlü 4 hisseyi listeler.\n• 7/24 Canlı KAP alımları otomatik gelir.")

            now = time.time()
            if now - last_kap_check >= 60:
                last_kap_check = now
                items = get_kap_disclosures()
                for d in items:
                    did = str(d.get("disclosureIndex", ""))
                    if not did or did in seen: continue
                    seen.add(did)
                    
                    sig = parse_disclosure_data(d)
                    if not sig: continue

                    lot_txt = f"{sig['lot']:,.0f} Lot" if sig['lot'] else "Detayda"
                    ratio_txt = f"%{sig['ratio']}" if sig['ratio'] else "Sınır Bildirimi"

                    msg = (
                        f"🚨 <b>CANLI KURUMSAL PAY ALIM ALARMI</b> 🚨\n"
                        f"────────────────────\n"
                        f"📌 <b>Hisse:</b> <code>{sig['ticker']}</code>\n"
                        f"🏛 <b>Kurum:</b> {sig['inst']}\n"
                        f"📊 <b>Yeni Sermaye Payı:</b> <code>{ratio_txt}</code>\n"
                        f"📦 <b>İşlem Lotu:</b> <code>{lot_txt}</code>\n"
                        f"💰 <b>İşlem Fiyatı:</b> <code>{sig['price_info']}</code>\n"
                        f"🕒 <b>Tarih:</b> {sig['date']}\n"
                        f"────────────────────\n"
                        f"🔗 <a href=\"https://www.kap.org.tr/tr/Bildirim/{sig['id']}\">KAP Bildirimi</a>"
                    )
                    send_tg(msg)
                    print(f"KAP Gönderildi: {sig['ticker']}")

                if len(seen) > 1000: seen = set(list(seen)[-500:])

        except Exception as e:
            print("Worker Hatası:", e)

        time.sleep(1)

def start_bot_thread():
    global worker_thread
    worker_thread = threading.Thread(target=bot_worker, daemon=True)
    worker_thread.start()

start_bot_thread()

if __name__ == "__main__":
    run_web_server()
EOF
