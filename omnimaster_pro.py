import streamlit as st
import sqlite3
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import urllib.parse
import json
from datetime import datetime

# --- VERİTABANI YÖNETİMİ ---
def init_db():
    conn = sqlite3.connect("omnimaster_pro.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            query_type TEXT,
            input_data TEXT,
            result_data TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_to_db(query_type, input_data, result_data):
    try:
        conn = sqlite3.connect("omnimaster_pro.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO history (timestamp, query_type, input_data, result_data) VALUES (?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), query_type, input_data, result_data)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(e)

init_db()

# --- ASENKRON WEB ARAŞTIRMA MOTORU ---
async def fetch_url(session, url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        async with session.get(url, headers=headers, timeout=5) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                for script in soup(["script", "style"]):
                    script.extract()
                text = soup.get_text(separator=" ", strip=True)
                return text[:1500]
    except:
        pass
    return None

async def search_duckduckgo(query):
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    links = []
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(search_url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    for a in soup.find_all("a", class_="result__url", limit=3):
                        href = a.get("href")
                        if href:
                            links.append(href)
        except:
            pass
            
        if not links:
            links = [
                f"https://en.wikipedia.org/wiki/Special:Search?search={encoded_query}",
                f"https://github.com/search?q={encoded_query}"
            ]
            
        tasks = [fetch_url(session, link) for link in links[:3]]
        results = await asyncio.gather(*tasks)
        
        compiled_text = ""
        for i, res in enumerate(results):
            if res:
                compiled_text += f"\n--- Kaynak {i+1} ---\n{res}\n"
                
        return compiled_text if compiled_text else "Arama sonucu bulunamadı veya ağ bağlantısı zaman aşımına uğradı."

# --- ARAYÜZ (UI) ---
st.set_page_config(page_title="OmniMaster Pro - Sınırsız Mod", page_icon="⚡", layout="wide")

st.title("⚡ OmniMaster Pro (Sınırsız & Anahtarsız)")
st.markdown("Tamamen yerel ve bulut tabanlı, API anahtarı gerektirmeyen otonom asistan paneli.")

menu = st.sidebar.selectbox("Seçenekler", ["Otonom Araştırma & İşlem", "Yerel Veritabanı Geçmişi"])

if menu == "Otonom Araştırma & İşlem":
    st.subheader("Web Taraması ve Otonom Analiz")
    
    user_query = st.text_area("Aratılacak konuyu veya yapılacak görevi yazın:", placeholder="Örn: Python ile asenkron programlama en iyi pratikleri")
    
    if st.button("Sınırsız Çalıştır"):
        if user_query.strip():
            with st.spinner("Otonom motorlar çalışıyor, veriler derleniyor..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                research_result = loop.run_until_complete(search_duckduckgo(user_query))
                
                st.success("İşlem Tamamlandı!")
                st.markdown("### 📊 Elde Edilen Bulgular ve Analiz:")
                st.write(research_result)
                
                save_to_db("Otonom Araştırma", user_query, research_result)
        else:
            st.warning("Lütfen geçerli bir görev veya arama terimi girin.")

elif menu == "Yerel Veritabanı Geçmişi":
    st.subheader("💾 Kaydedilen İşlem Geçmişi")
    
    try:
        conn = sqlite3.connect("omnimaster_pro.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, query_type, input_data, result_data FROM history ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        
        if rows:
            for row in rows:
                with st.expander(f"[{row[0]}] {row[1]} - {row[2][:30]}..."):
                    st.write(f"**Girdi:** {row[2]}")
                    st.write(f"**Sonuç:** {row[3]}")
        else:
            st.info("Henüz veritabanında kayıtlı işlem bulunmuyor.")
    except Exception as e:
        st.error(f"Veritabanı okunurken bir hata oluştu: {e}")
