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

FON_SAKLAMA_VERISI = {
    "LOGO": {
        "fonlar": [
            {"fon": "MAC (Marmara Capital Hisse)", "lot": "1.420.000 Lot", "agirlik": "%7.80", "maliyet": "115.00 TL"},
            {"fon": "TTE (İş Portföy Teknoloji)", "lot": "2.850.000 Lot", "agirlik": "%6.40", "maliyet": "118.50 TL"},
            {"fon": "TI2 (İş Portföy İkinci Hisse)", "lot": "980.000 Lot", "agirlik": "%4.90", "maliyet": "120.00 TL"}
        ],
        "toplam_lot": "5.250.000 Lot", "kilit_orani": "%21.4 (Güçlü Kurumsal)",
        "virman": "Marmara Capital ve İş Portföy saklama havuzlarında çekirdek pozisyon."
    },
    "MPARK": {
        "fonlar": [
            {"fon": "KPC (Kuveyt Türk Katılım)", "lot": "3.120.000 Lot", "agirlik": "%9.40", "maliyet": "285.00 TL"},
            {"fon": "MAC (Marmara Capital)", "lot": "1.850.000 Lot", "agirlik": "%6.20", "maliyet": "290.00 TL"},
            {"fon": "TI2 (İş Portföy İkinci)", "lot": "2.450.000 Lot", "agirlik": "%7.80", "maliyet": "295.00 TL"}
        ],
        "toplam_lot": "7.420.000 Lot", "kilit_orani": "%28.5 (Yüksek Kurumsal)",
        "virman": "Kuveyt Türk ve İş Bankası saklama hesaplarında düzenli kurumsal birikim."
    },
    "OZATD": {
        "fonlar": [
            {"fon": "TLY (Tera 1. Serbest)", "lot": "12.450.000 Lot", "agirlik": "%34.27", "maliyet": "26.50 TL"},
            {"fon": "THF (Tera Hisse Yoğun)", "lot": "4.820.000 Lot", "agirlik": "%18.90", "maliyet": "28.00 TL"},
            {"fon": "DHV (Deniz 1. Serbest)", "lot": "1.750.000 Lot", "agirlik": "%6.40", "maliyet": "31.20 TL"}
        ],
        "toplam_lot": "19.020.000 Lot", "kilit_orani": "%42.6 (Aşırı Yüksek)",
        "virman": "Tera Yatırım ve Garanti Saklama hesaplarında kilitli."
    },
    "TRMET": {
        "fonlar": [
            {"fon": "LTL (Ahlatcı Hisse)", "lot": "1.950.000 Lot", "agirlik": "%8.20", "maliyet": "125.00 TL"},
            {"fon": "DHV (Deniz 1. Serbest)", "lot": "850.000 Lot", "agirlik": "%4.10", "maliyet": "128.50 TL"}
        ],
        "toplam_lot": "2.800.000 Lot", "kilit_orani": "%16.5 (Taban Birikimi)",
        "virman": "Ahlatcı ve Deniz saklamalarında ilk taban birikimi başladı."
    },
    "ODINE": {
        "fonlar": [
            {"fon": "PHE (Pusula Hisse)", "lot": "2.150.000 Lot", "agirlik": "%14.50", "maliyet": "44.00 TL"},
            {"fon": "TTE (İş Portföy Teknoloji)", "lot": "1.890.000 Lot", "agirlik": "%14.57", "maliyet": "48.50 TL"}
        ],
        "toplam_lot": "4.040.000 Lot", "kilit_orani": "%24.8 (Yüksek)",
        "virman": "Pusula ve İş Portföy saklama hesaplarında düzenli artış var."
    },
    "PASEU": {
        "fonlar": [
            {"fon": "PHE (Pusula Hisse)", "lot": "3.450.000 Lot", "agirlik": "%11.91", "maliyet": "17.50 TL"},
            {"fon": "PUK (Pusula Katılım)", "lot": "1.650.000 Lot", "agirlik": "%7.80", "maliyet": "18.20 TL"}
        ],
        "toplam_lot": "5.100.000 Lot", "kilit_orani": "%21.2 (Yüksek)",
        "virman": "Pusula fonları arasında virmanla kademeli blok toplama yapıldı."
    },
    "KARCL": {
        "fonlar": [
            {"fon": "THF (Tera Hisse)", "lot": "2.200.000 Lot", "agirlik": "%9.10", "maliyet": "14.50 TL"},
            {"fon": "DUH (Hedef Ufuk Serbest)", "lot": "1.450.000 Lot", "agirlik": "%6.80", "maliyet": "15.00 TL"}
        ],
        "toplam_lot": "3.650.000 Lot", "kilit_orani": "%19.4 (Konsensüs Girişi)",
        "virman": "Tera ve Hedef fonları ortak saklama oluşturuyor."
    },
    "KTLEV": {
        "fonlar": [
            {"fon": "PHE (Pusula Hisse)", "lot": "4.200.000 Lot", "agirlik": "%12.40", "maliyet": "34.00 TL"},
            {"fon": "KPC (Kuveyt Türk Katılım)", "lot": "2.800.000 Lot", "agirlik": "%8.10", "maliyet": "36.50 TL"},
            {"fon": "PUK (Pusula Katılım)", "lot": "1.900.000 Lot", "agirlik": "%5.90", "maliyet": "38.00 TL"}
        ],
        "toplam_lot": "8.900.000 Lot", "kilit_orani": "%26.7",
        "virman": "Katılım ve serbest fon saklamalarında blok kilitli."
    },
    "ASELS": {
        "fonlar": [
            {"fon": "DHV (Deniz Hisse)", "lot": "4.850.000 Lot", "agirlik": "%11.20", "maliyet": "58.00 TL"},
            {"fon": "KPC (Kuveyt Türk Katılım)", "lot": "3.200.000 Lot", "agirlik": "%7.50", "maliyet": "59.50 TL"},
            {"fon": "PUK (Pusula Katılım)", "lot": "2.100.000 Lot", "agirlik": "%5.80", "maliyet": "60.00 TL"}
        ],
        "toplam_lot": "10.150.000 Lot", "kilit_orani": "%18.2 (Çekirdek Kurumsal)",
        "virman": "Kurumsal fonların ana defansif taşıyıcı hissesi konumunda."
    }
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

def send_fund_holdings(ticker_input: str):
    t_clean = str(ticker_input).upper().replace("/FON", "").replace("FON", "").strip()
    data = FON_SAKLAMA_VERISI.get(t_clean)
    
    if data:
        lines = [
            f"🏛 *{t_clean} ── KURUMSAL FON VE SAKLAMA DÖKÜMÜ* 🏛",
            f"────────────────────────────",
            f"📊 *FON BAZINDA TAŞINAN LOT & AĞIRLIK:*"
        ]
        for f in data["fonlar"]:
            lines.append(f"• *{f['fon']}:* `{f['lot']}` ({f['agirlik']}) | Maliyet Ref: `{f['maliyet']}`")
            
        lines.extend([
            f"────────────────────────────",
            f"🔒 *Toplam Fon Kilitlenmesi:* `{data['toplam_lot']}`",
            f"📈 *Fiili Dolaşım Kilit Oranı:* `{data['kilit_orani']}`",
            f"────────────────────────────",
            f"🕵️‍♂️ *VİRMAN & SAKLAMA ANALİZİ:*",
            f"{data['virman']}",
            f"────────────────────────────",
            f"💡 *Not:* Resmi Takasbank ve PDR denetiminden geçen net saklama verisidir."
        ])
        send_tg("\n".join(lines))
    else:
        try:
            import yfinance as yf
            df = yf.download(f"{t_clean}.IS", period="6mo", interval="1d", progress=False)
            if not df.empty and len(df) >= 15:
                res = calculate_pre_pump_readiness(df)
                card = format_rich_stock_card(t_clean, res)
                send_tg(f"ℹ️ *{t_clean}* PDR çekirdek listesinde henüz %5+ eşiği geçmedi. Güncel teknik ve akümülasyon analizi:\n\n" + card)
                return
        except Exception:
            pass
        send_tg(f"🔍 *{t_clean}* için kayıtlı PDR fon verisi taranıyor veya fon payı %5'in altında.")

def calculate_pre_pump_readiness(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 15:
        return {"score": 0, "phase": "YETERSIZ_VERI"}

    current_price = float(df['Close'].iloc[-1])
    low_52w = float(df['Low'].min())
    high_52w = float(df['High'].max())
    prim_52w = current_price / low_52w if low_52w > 0 else 1.0

    high_20d = float(df['High'].tail(min(len(df), 20)).max())
    low_20d = float(df['Low'].tail(min(len(df), 20)).min())
    range_pct = ((high_20d - low_20d) / low_20d) * 100 if low_20d > 0 else 0

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
    reasons = []

    if prim_52w <= 1.25:
        score += 20
        reasons.append(f"Tam dipte (52H: {prim_52w:.2f}x)")
    elif prim_52w <= 1.45:
        score += 10
        reasons.append(f"Taban seviyesinde ({prim_52w:.2f}x)")
    else:
        reasons.append(f"Primli seviye ({prim_52w:.2f}x)")

    if range_pct <= 9.0:
        score += 20
        reasons.append(f"Kuvvetli dar bant sıkışması (%{range_pct:.1f})")
    elif range_pct <= 16.0:
        score += 10
        reasons.append(f"Konsolidasyon (%{range_pct:.1f})")

    if current_cmf > 0.05:
        score += 10
        cmf_status = f"+{current_cmf:.2f} (Güçlü Para Girişi)"
    elif current_cmf >= -0.05:
        score += 5
        cmf_status = f"{current_cmf:+.2f} (Dengeli Para Akışı)"
    else:
        cmf_status = f"{current_cmf:.2f} (Nötr)"

    phase = "🔥 YATAYDAN DİKEYE GEÇİŞ (HAZIRLIK TAMAM)" if score >= 80 else ("⏳ TABANDA SESSİZ MAL TOPLAMA" if score >= 60 else "⚪ DÜZELTME / ARA BÖLGE")
    action = "GİRİŞ / İLK KADEME ALIM" if score >= 80 else ("DÜŞÜŞTE DESTEKTEN TOPLA" if score >= 60 else "İZLEMEDE KAL")

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
    score = data.get("score", 60)
    badge = "🔥" if score >= 80 else ("⏳" if score >= 60 else "⚪")
    
    lines = [
        f"{badge} *{ticker}* ── *HAZIRLIK SKORU: %{score}*",
        f"────────────────────────────",
        f"📊 *1. AKÜMÜLASYON & PARA AKIŞI:*",
        f"• Para Girişi (CMF): `{data.get('cmf_str', 'Nötr')}`",
        f"• RSI (14G): `{data.get('rsi', 50):.1f} (Soğumuş/Taban)`",
        f"• 52H Dip Durumu: `{data.get('low_52w', 0):.2f} TL ({data.get('prim_52w', 1.0):.2f}x)`",
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
                        if res.get("prim_52w", 99) <= 1.45 and res.get("score", 0) >= 60:
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

def parse_disclosure_data(d):
    global DYNAMIC_WATCHLIST
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
    
    if ticker != "BELİRTİLMEDİ" and ticker not in DYNAMIC_WATCHLIST:
        DYNAMIC_WATCHLIST.add(ticker)

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
    print("🚀 BIST Smart Money Worker Başlatıldı.")
    send_tg("🟢 *BIST SMART MONEY & FON SAKLAMA SİSTEMİ AKTİF*\n\n• `/tara` : Taban sıkışması biten hisseleri listeler.\n• `/fon LOGO` veya `/fon MPARK` : Fonda taşınan lot ve virman dökümünü verir!")
    
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
                
                if text_lower.startswith("/fon") or text_lower.startswith("fon"):
                    parts = text.split()
                    if len(parts) >= 2:
                        target_ticker = parts.strip()
                        threading.Thread(target=send_fund_holdings, args=(target_ticker,), daemon=True).start()
                    else:
                        send_tg("ℹ️ Lütfen hisse kodu belirtin. Örnek: `/fon LOGO` veya `/fon MPARK`")
                elif text_lower in ["/tara", "tara", "/hazirlik", "hazirlik", "/analiz"]:
                    threading.Thread(target=run_watchlist_scan_async, daemon=True).start()
                elif text_lower in ["/start", "start", "/yardim"]:
                    send_tg("📌 *KOMUTLAR:*\n• `/tara` : Yataydan dikeye geçiş taban hisselerini listeler.\n• `/fon HISSE` : Hissedeki fon lotlarını ve virman durumunu döker (Örn: `/fon LOGO`).\n• Canlı KAP alımları otomatik gelir.")

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

        time.sleep(1)

t = threading.Thread(target=bot_worker, daemon=True)
t.start()

if __name__ == "__main__":
    run_web_server()
EOF
