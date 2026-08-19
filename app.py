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

# ==================== HEALTH CHECK WEB SUNUCUSU ====================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status":"online","service":"BIST Smart Money Bot"}')
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
IZLEME_HAVUZU = ["OZATD", "ODINE", "PASEU", "KARCL", "KTLEV", "GUNDG", "TEHOL", "BETAE", "TRALT", "TRMET", "BIGEN", "ALKLC"]

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
        params = {"timeout": 2, "offset": offset}
        r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params=params, timeout=5)
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
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print("KAP Hatası:", e)
    return []

def calculate_pre_pump_readiness(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 15:
        return {"score": 0, "phase": "YETERSIZ_VERI", "reasons": []}

    high_20d = float(df['High'].tail(min(len(df), 20)).max())
    low_20d = float(df['Low'].tail(min(len(df), 20)).min())
    current_price = float(df['Close'].iloc[-1])
    range_pct = ((high_20d - low_20d) / low_20d) * 100 if low_20d > 0 else 0

    sma_20 = df['Close'].rolling(min(len(df), 20)).mean()
    std_20 = df['Close'].rolling(min(len(df), 20)).std().fillna(0)
    bb_width = ((sma_20 + std_20*2) - (sma_20 - std_20*2)) / sma_20 * 100
    is_squeezing = float(bb_width.iloc[-1]) <= float(bb_width.tail(min(len(df), 60)).min()) * 1.35 if len(df) >= 20 else False

    mf_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'])
    mf_multiplier = mf_multiplier.fillna(0)
    vol_sum = df['Volume'].rolling(min(len(df), 20)).sum()
    cmf_20 = (mf_multiplier * df['Volume']).rolling(min(len(df), 20)).sum() / vol_sum
    current_cmf = float(cmf_20.iloc[-1]) if not cmf_20.empty and not np.isnan(cmf_20.iloc[-1]) else 0

    ema_20 = float(df['Close'].ewm(span=min(len(df), 20), adjust=False).mean().iloc[-1])
    low_52w = float(df['Low'].min())
    prim_52w = current_price / low_52w if low_52w > 0 else 1.0

    score = 0
    reasons = []

    if prim_52w <= 1.60:
        score += 25
        reasons.append(f"Tabanda (52H: {prim_52w:.2f}x)")
    elif prim_52w <= 2.2:
        score += 15
        reasons.append(f"Makul prim ({prim_52w:.2f}x)")

    if range_pct <= 14.0:
        score += 25
        reasons.append(f"Kuvvetli sıkışma (20G: %{range_pct:.1f})")
    elif range_pct <= 22.0:
        score += 15
        reasons.append(f"Konsolidasyon (20G: %{range_pct:.1f})")

    if current_cmf > 0.05:
        score += 25
        reasons.append(f"Güçlü para girişi (CMF: +{current_cmf:.2f})")
    elif current_cmf >= -0.05:
        score += 15
        reasons.append(f"Pozitif para akışı (CMF: {current_cmf:+.2f})")

    if current_price >= ema_20:
        score += 25
        reasons.append("20 EMA üzerinde tutunuyor")
    else:
        score += 10
        reasons.append("Destek arayışında")

    if score >= 70:
        phase = "🔥 PATLAMA / HAREKET EŞİĞİNDE"
        action = "GİRİŞ / İLK KADEME ALIM"
    elif score >= 45:
        phase = "⏳ AKÜMÜLASYON DEVAM EDİYOR"
        action = "TAKİPTE KAL / DÜŞÜŞTE TOPLA"
    else:
        phase = "⚪ HENÜZ OLGUNLAŞMADI"
        action = "İZLEMEDE BEKLET"

    return {
        "score": score,
        "phase": phase,
        "action": action,
        "price": current_price,
        "stop_loss": round(current_price * 0.93, 2),
        "target_1": round(current_price * 1.50, 2),
        "reasons": reasons
    }

def run_watchlist_scan():
    send_tg("⏳ *CANLI BIST & 15-30 GÜNLÜK AKÜMÜLASYON TARAMASI BAŞLADI...*\nLütfen 3-5 saniye bekleyin.")
    results = []
    
    # 1. Hızlı Paralel Toplu İndirme (Tüm hisseler aynı anda 1.5 saniyede iner)
    try:
        import yfinance as yf
        symbols = [f"{t}.IS" for t in IZLEME_HAVUZU]
        batch_data = yf.download(symbols, period="6mo", interval="1d", group_by='ticker', threads=True, progress=False, timeout=8)
        
        for ticker in IZLEME_HAVUZU:
            sym = f"{ticker}.IS"
            try:
                if sym in batch_data:
                    df_t = batch_data[sym].dropna()
                    if not df_t.empty and len(df_t) >= 15:
                        res = calculate_pre_pump_readiness(df_t)
                        if res.get("score", 0) > 0:
                            results.append({"ticker": ticker, **res})
            except Exception:
                pass
    except Exception as e:
        print("Toplu indirme hatası:", e)

    # 2. Yedek İş Yatırım Hattı
    if len(results) < 3:
        for ticker in IZLEME_HAVUZU:
            if any(r["ticker"] == ticker for r in results): continue
            try:
                url = f"https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/ChartData.aspx/Index2?period=1440&code={ticker}.E.BIST"
                headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.isyatirim.com.tr/"}
                r = requests.get(url, headers=headers, timeout=3)
                if r.status_code == 200 and r.text:
                    data = r.json()
                    if isinstance(data, list) and len(data) >= 15:
                        df = pd.DataFrame(data, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                        res = calculate_pre_pump_readiness(df.dropna())
                        if res.get("score", 0) > 0:
                            results.append({"ticker": ticker, **res})
            except Exception:
                pass

    if not results:
        send_tg("⚠️ Veri hattı anlık meşgul, lütfen 30 saniye sonra tekrar /tara yazın.")
        return

    results.sort(key=lambda x: x["score"], reverse=True)

    msg_lines = [
        "📊 *CANLI BIST HAREKET HAZIRLIK RAPORU* 📊",
        "────────────────────"
    ]
    for item in results[:5]:
        badge = "🔥" if item["score"] >= 70 else ("⏳" if item["score"] >= 45 else "⚪")
        msg_lines.extend([
            f"{badge} *{item['ticker']}* — Hazırlık Skoru: `%{item['score']}`",
            f"• Durum: {item['phase']}",
            f"• Aksiyon: `{item['action']}`",
            f"• Güncel Fiyat: `{item['price']:.2f} TL`",
            f"• Stop-Loss (%7): `{item['stop_loss']:.2f} TL` | Hedef (%50): `{item['target_1']:.2f} TL`",
            f"• Sinyal Teyidi: {', '.join(item['reasons'][:2])}",
            "────────────────────"
        ])
    
    msg_lines.append("💡 İstediğin zaman Telegram'dan `/tara` yazarak güncel taramayı çalıştırabilirsin.")
    send_tg("\n".join(msg_lines))

def parse_disclosure_data(d):
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
    
    ratio_match = re.search(r"%\s*([0-9]+[,\.][0-9]+)", full_text)
    ratio = float(ratio_match.group(1).replace(",", ".")) if ratio_match else None

    lot_match = re.search(r"([0-9\.,]+)\s*ADET", full_text)
    lot_str = lot_match.group(1).replace(".", "").replace(",", ".") if lot_match else None
    lot = float(lot_str) if lot_str else None

    price_match = re.search(r"([0-9]+[,\.][0-9]+)\s*-\s*([0-9]+[,\.][0-9]+)\s*TL", full_text)
    if not price_match:
        price_match = re.search(r"([0-9]+[,\.][0-9]+)\s*TL\s*(FİYATTAN|FİYATLA)", full_text)
    price_info = price_match.group(0) if price_match else "Bildirim detayında"

    action = "ALIM" if any(w in full_text for w in ["ALDI", "ALINDI", "EDİNİLDİ", "ALIM"]) else ("SATIM" if "SAT" in full_text else "EŞİK BİLDİRİMİ")

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
    print("🚀 Render BIST Smart Money Bot Başlatıldı.")
    send_tg("🟢 *BIST SMART MONEY BOTU AKTİF (RENDER HIZLI MOD)*\n\n• Paralel çoklu veri hattı devrede.\n• Telegram'dan `/tara` yazarak anında tarama yapabilirsin!")
    
    seen = set()
    last_update_id = None
    last_kap_check = 0

    while True:
        try:
            updates = get_tg_updates(offset=last_update_id)
            for u in updates:
                last_update_id = u["update_id"] + 1
                msg = u.get("message", {})
                text = msg.get("text", "").strip().lower()
                
                if text in ["/tara", "tara", "/hazirlik", "hazirlik", "/analiz"]:
                    run_watchlist_scan()
                elif text in ["/start", "start", "/yardim"]:
                    send_tg("📌 *KOMUTLAR:*\n• `/tara` : Canlı BIST ve KAP akışında akümülasyonu biten hisseleri listeler.\n• 7/24 Canlı KAP bildirimleri anında telefonuna düşer.")

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
                        f"🚨 *CANLI KURUMSAL PAY ALIM ALARMI* 🚨\n"
                        f"────────────────────\n"
                        f"📌 *Hisse:* `{sig['ticker']}`\n"
                        f"🏛 *Kurum:* {sig['inst']}\n"
                        f"📊 *Yeni Sermaye Payı:* `{ratio_txt}`\n"
                        f"📦 *İşlem Lotu:* `{lot_txt}`\n"
                        f"💰 *İşlem Fiyatı:* `{sig['price_info']}`\n"
                        f"🕒 *Tarih:* {sig['date']}\n"
                        f"────────────────────\n"
                        f"🔗 [KAP Bildirimi](https://www.kap.org.tr/tr/Bildirim/{sig['id']})"
                    )
                    send_tg(msg)
                    print(f"KAP Gönderildi: {sig['ticker']}")

                if len(seen) > 1000: seen = set(list(seen)[-500:])

        except Exception as e:
            print("Worker Hatası:", e)

        time.sleep(2)

t = threading.Thread(target=bot_worker, daemon=True)
t.start()

if __name__ == "__main__":
    run_web_server()
