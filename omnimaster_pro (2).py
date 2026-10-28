import os
import json
import asyncio
import sqlite3
import requests
import streamlit as st
from bs4 import BeautifulSoup
import aiohttp
from duckduckgo_search import DDGS

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="OmniMaster Pro - Ücretsiz Bulut Ajanı",
    page_icon="⚡",
    layout="wide"
)

# --- TASARIM VE ARAYÜZ STİLLERİ ---
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; color: #00FF7F; font-weight: bold; margin-bottom: 0px; }
    .sub-title { font-size: 1.0rem; color: #A9A9A9; margin-bottom: 20px; }
    .stButton>button { background-color: #00FF7F; color: #000; font-weight: bold; border-radius: 8px; }
    .stButton>button:hover { background-color: #32CD32; color: #fff; }
</style>
""", unsafe_allow_html=True)

# --- YÜKSEK HIZLI ASENKRON TARAYICI ---
class LightningScraper:
    @staticmethod
    async def fetch(session, url):
        try:
            async with session.get(url, timeout=3) as res:
                if res.status == 200:
                    html = await res.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    for s in soup(["script", "style"]): s.decompose()
                    return {"url": url, "text": soup.get_text(separator=' ', strip=True)[:1500]}
        except:
            return None

    @classmethod
    def run_fast_search(cls, query):
        urls = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=4):
                urls.append(r['href'])
        
        if not urls: return "Sonuç bulunamadı."
        
        async def main():
            async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
                tasks = [cls.fetch(session, u) for u in urls]
                return await asyncio.gather(*tasks)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(main())
        return [r for r in results if r]

# --- AKILLI HAFIZA VE MOTOR ---
class OmniEngine:
    def __init__(self, api_key):
        self.api_key = api_key
        self.db = "omnimaster_pro.db"
        self.init_db()

    def init_db(self):
        try:
            conn = sqlite3.connect(self.db)
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS knowledge (id INTEGER PRIMARY KEY, tag TEXT, content TEXT)")
            conn.commit()
            conn.close()
        except Exception:
            pass

    def remember(self, tag, content):
        try:
            conn = sqlite3.connect(self.db)
            c = conn.cursor()
            c.execute("INSERT INTO knowledge (tag, content) VALUES (?, ?)", (tag, content))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def fast_respond(self, prompt):
        if not self.api_key:
            return "❌ Lütfen sol menüden API anahtarınızı girin!"

        if prompt.lower().startswith("ara:"):
            q = prompt.split(":", 1)[1].strip()
            scraped = LightningScraper.run_fast_search(q)
            combined_text = ""
            for item in scraped:
                self.remember(q, item['text'])
                combined_text += f"\n👉 [{item['url']}]\n{item['text'][:400]}...\n"
            return f"⚡ **Milisaniyeler içinde tarandı ve hafızaya işlendi:**\n{combined_text}"

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "anthropic/claude-3.5-sonnet",
            "messages": [
                {"role": "system", "content": "Sen en zor kodlama problemlerini (C++, Python, Algoritma) çözen, asla kod kısaltmayan, tam ve kusursuz çalışan kodlar üreten kıdemli bir otonom mühendissin."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        try:
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
            data = res.json()
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
            else:
                return f"API Yanıt Hatası: {data}"
        except Exception as e:
            return f"Bağlantı Hatası: {str(e)}"

# --- ARAYÜZ (UI) ---
st.markdown('<div class="main-title">⚡ OmniMaster Pro Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Bulut Tabanlı Ücretsiz Otonom Mühendislik Paneli</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Konfigürasyon")
    api_key_input = st.text_input("API Key (OpenRouter vb.)", value="", type="password")
    st.divider()
    st.success("Durum: Bulut Modu Aktif ☁️")
    st.info("Hafıza: SQLite Kalıcı Depo")

engine = OmniEngine(api_key_input)

tab1, tab2 = st.tabs(["💬 Otonom Çalışma Ekranı", "🧠 Kalıcı Hafıza"])

with tab1:
    user_q = st.text_area("Talimatınızı veya Kodlama Sorununuzu Yazın:", placeholder="Örn: 'ara: C++26 yenilikleri' veya 'Yüksek performanslı C++ Thread Pool kodu yaz'", height=120)
    
    if st.button("🚀 Hemen Çalıştır ve Çöz"):
        if user_q:
            with st.spinner("⚡ OmniMaster işliyor..."):
                answer = engine.fast_respond(user_q)
                st.markdown("### 📋 Sonuç")
                st.markdown(answer)
        else:
            st.warning("Lütfen bir komut veya soru girin.")

with tab2:
    st.subheader("📚 Hafızaya Kaydedilen Veriler")
    if os.path.exists("omnimaster_pro.db"):
        conn = sqlite3.connect("omnimaster_pro.db")
        c = conn.cursor()
        c.execute("SELECT id, tag, content FROM knowledge ORDER BY id DESC LIMIT 15")
        rows = c.fetchall()
        conn.close()
        
        if rows:
            for r in rows:
                st.write(f"**ID:** {r[0]} | **Konu:** {r[1]}")
                st.caption(r[2][:300] + "...")
                st.divider()
        else:
            st.info("Henüz hafızaya kaydedilmiş veri yok.")
    else:
        st.info("Henüz veritabanı oluşturulmadı.")
