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

# ⛔ TOKSİK VE RİSKLİ ŞİRKETLER KARA LİSTESİ (Konkordato, Gözaltı/YİP vb. Doğrudan Yasaklı)
KARA_LISTE = {"BARMA", "MEGAP", "YESIL", "AVOD", "DERAS", "KENT", "KUVVA", "ISBIR", "ROYAL"}

# GÜVENLİ BIST TABAN & YATAYDAN DİKEYE GEÇİŞ TARAMA HAVUZU
DYNAMIC_WATCHLIST = {
    "TRMET", "BETAE", "TRALT", "BIGEN", "SDTTR", "PATEK", "ARDYZ", "ONCSM", 
    "NETCD", "MOBTL", "LOGO", "VBTYZ", "PAPIL", "ALVES", "AGROT", "BINHO", 
    "HOROZ", "LIDER", "MANAS", "ORZAX", "ANELE", "CVKMD", "KARYE", "TEZOL", 
    "KOPOL", "CWENE", "ALFAS", "EUPWR", "GESAN", "ASTOR", "SAYAS", "TRHOL", 
    "DAPGM", "TEHOL", "PEKGY", "SELEC", "MPARK", "TABGD", "GOKNR", "KRVGD", 
    "MEYSU", "EBEBK", "PASEU", "KTLEV", "GUNDG", "KARCL"
}

SEKTOR_KATALIZORLERI = {
    "TRMET": {"sektor": "Metal & Emtia / Sanayi", "katalizor": "İhracat talebi, yeni fabrika kapasite artışı ve emtia desteği."},
    "BETAE": {"sektor": "Enerji & Elektrik Ekipman", "katalizor": "Yenilenebilir enerji trafo ihaleleri ve yeni iş sözleşmeleri."},
    "TRALT": {"sektor": "Maden & Kıymetli Metal", "katalizor": "Altın/maden arama ruhsatları ve emtia rallisi desteği."},
    "SDTTR": {"sektor": "Savunma Sanayii & Aviyonik", "katalizor": "Savunma Sanayii Başkanlığı radar ve haberleşme sözleşmeleri."},
    "PAPIL": {"sektor": "Güvenlik & Biyometrik Teknoloji", "katalizor": "Uluslararası sınır güvenlik yazılımı ihracat anlaşmaları."},
    "ARDYZ": {"sektor": "Yazılım & Bulut Bilişim", "katalizor": "Kamuda dijital dönüşüm ve kurumsal bulut altyapı projeleri."},
    "ONCSM": {"sektor": "Sağlık & Medikal Robotik", "katalizor": "Kemoterapi hazırlama robotları yurt dışı distribütörlükleri."},
    "ORZAX": {"sektor": "İlaç & Takviye Gıda", "katalizor": "Orta Asya/Özbekistan yeni iştirak ve ihracat genişlemesi."},
    "ALVES": {"sektor": "Kablo & Enerji Altyapı", "katalizor": "Avrupa ve Ortadoğu enerji nakil kablo tedarik sözleşmeleri."},
    "CVKMD": {"sektor": "Madencilik & Metal", "katalizor": "Krom ve altın işletme tesisleri kapasite genişletmesi."},
    "KOPOL": {"sektor": "Petrokimya & Polimer", "katalizor": "Geri dönüşüm polimer tesisi teşvikleri ve devreye alma."},
    "SELEC": {"sektor": "Sağlık & Ecza Dağıtım", "katalizor": "İlaç fiyat güncellemesi ve pazar payı genişlemesi."},
    "BIGEN": {"sektor": "Biyoteknoloji & Tarım", "katalizor": "Tohum ve tarımsal Ar-Ge ürünlerinin ticarileşmesi."},
    "PATEK": {"sektor": "Bilişim & Lojistik Yazılım", "katalizor": "Akıllı liman ve demiryolu lojistik yazılım entegrasyonları."},
    "MANAS": {"sektor": "Sayaç & Ölçüm Teknolojileri", "katalizor": "Doğalgaz ve su sayaçları kamu ve belediye ihaleleri."},
    "TEHOL": {"sektor": "Finans & Teknoloji Holding", "katalizor": "Girişim sermayesi iştirak satışı ve sermaye artırımı."},
    "LOGO": {"sektor": "Kurumsal ERP & Yazılım", "katalizor": "e-Dönüşüm ve SaaS abonelik gelirlerindeki güçlü büyüme."}
}

is_scanning = False

def send_tg(msg):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10
        )
        if r.status_code != 200:
            clean_text = msg.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "")
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

def calculate_pre_pump_readiness(df: pd.DataFrame, ticker: str = "") -> dict:
    if df.empty or len(df) < 15:
        return {"allow": False, "phase": "YETERSIZ_VERI"}

    if ticker in KARA_LISTE:
        return {"allow": False, "phase": "KARA LİSTE / KONKORDATO RİSKİ"}

    current_price = float(df['Close'].iloc[-1])
    low_52w = float(df['Low'].min())
    high_52w = float(df['High'].max())
    prim_52w = current_price / low_52w if low_52w > 0 else 1.0

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

    kat_info = SEKTOR_KATALIZORLERI.get(ticker, {
        "sektor": "Büyüme & Sanayi / Teknoloji",
        "katalizor": "KAP yeni iş ilişkileri, ihracat ve operasyonel kârlılık büyümesi takibinde."
    })

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
        "sektor": kat_info["sektor"],
        "katalizor": kat_info["katalizor"],
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
        f"🏭 <b>Sektör & Tema:</b> <code>{data.get('sektor')}</code>",
        f"📰 <b>KAP & Büyüme Hikayesi:</b> {data.get('katalizor')}",
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
    send_tg(f"⏳ <b>BIST SEKTÖREL TABAN SIKIŞMASI TARANIYOR...</b>\n🛡 Kara Liste & Konkordato Koruması Devrede\n📊 Taranan Güvenli Hisse: <code>{len(active_pool)}</code>\nLütfen 5-8 saniye bekleyin.")
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

    send_tg(f"📊 <b>BIST GÜVENLİ TABAN SIKIŞMASI RAPORU</b> 📊\n🛡 <i>Filtre: Konkordato Korumalı, 52H Dip (≤ 1.45x) & Dar Sıkışma</i>\n──────────────")

    # En az 4 Güçlü Adayı Gönder
    for item in results[:4]:
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
    
    if ticker != "BELİRTİLMEDİ" and ticker not in KARA_LISTE and ticker not in DYNAMIC_WATCHLIST:
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
    send_tg("🟢 <b>BIST SMART MONEY BOTU AKTİF</b>\n\n• Sektörel Büyüme & Taban Sıkışması Taraması devrede.\n• 7/24 Canlı KAP dinleniyor.\n• <code>/tara</code> yazarak taramayı başlatabilirsiniz!")
    
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
                
                if text_lower in ["/tara", "tara", "/hazirlik", "hazirlik", "/analiz"]:
                    threading.Thread(target=run_watchlist_scan_async, daemon=True).start()
                elif text_lower in ["/start", "start", "/yardim"]:
                    send_tg("📌 <b>KOMUTLAR:</b>\n• <code>/tara</code> : Taban sıkışması ve büyüme katalizörü olan en az 4 hisseyi listeler.\n• 7/24 Canlı KAP alımları otomatik gelir.")

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

t = threading.Thread(target=bot_worker, daemon=True)
t.start()

if __name__ == "__main__":
    run_web_server()
EOF
