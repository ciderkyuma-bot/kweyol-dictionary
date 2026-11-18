import streamlit as st
import requests
import html
import qrcode
import socket
import pandas as pd
import altair as alt
import os
import base64
import random
import datetime
import numpy as np
from pathlib import Path
from io import BytesIO
from st_copy_to_clipboard import st_copy_to_clipboard

# 引入核心功能
from main import load_databases, fast_query, search_examples, analyze_database_stats, run_lego_translation

# 頁面設定
st.set_page_config(
    page_title="Kwéyòl Dictionary (Beta)",
    page_icon="🥥", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS 樣式 ---
st.markdown('''
<style>
/* 1. 全域背景與字體 */
.stApp { background-color: #fcfbf9; font-family: "Segoe UI", "Helvetica Neue", sans-serif; }
h1, h2, h3 { color: #2c2c2c !important; font-weight: 700; }
p, div, label, span { color: #333333; }

/* 2. Tabs 優化 */
.stTabs [data-baseweb="tab-list"] { gap: 20px; border-bottom: 2px solid #e8e0d5; padding-bottom: 0px; }
.stTabs [data-baseweb="tab"] { height: 45px; background-color: transparent; border: none; color: #888888; font-weight: 600; font-size: 1rem; }
.stTabs [aria-selected="true"] { color: #5d4037 !important; border-bottom: 3px solid #8d6e63; }
.stTabs [data-baseweb="tab"]:hover { color: #8d6e63; }

/* 3. 按鈕樣式 */
.stButton > button {
    background-color: #ffffff; color: #4a4a4a !important; border: 1px solid #bcaaa4;
    border-radius: 6px; padding: 0.5rem 1.2rem; font-weight: 600; transition: all 0.2s;
}
.stButton > button:hover {
    background-color: #efebe9; border-color: #8d6e63; color: #2c2c2c !important; transform: translateY(-1px);
}

/* 4. 複製按鈕特別樣式 */
div.stButton > button:contains("Copy") {
    font-size: 0.85rem !important; padding: 0.3rem 0.8rem !important;
    background-color: #f4f0ea !important; color: #8c7b75 !important;
    border: 1px solid #e0dcd0 !important; height: auto !important; margin-top: -10px; 
}

/* 5. 輸入框優化 */
.stTextInput > div > div > input, .stTextArea > div > div > textarea {
    border-radius: 6px; border: 1.5px solid #d7ccc8; background-color: #ffffff; color: #222; font-size: 1.1rem;
}
.stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
    border-color: #8d6e63; box-shadow: 0 0 0 1px #8d6e63;
}

/* 6. 卡片樣式 */
.translation-card-rbmt {
    background-color: #ffffff; padding: 25px; border-radius: 10px; 
    border-left: 6px solid #8d6e63;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08); 
    margin-bottom: 20px;
}
.result-card {
    background-color: #ffffff; padding: 1.5rem; margin-bottom: 0.5rem; 
    border-radius: 8px; border: 1px solid #eee; border-left: 4px solid #8d6e63;
    box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    position: relative;
    padding-bottom: 2.5rem;
}
.stats-card {
    background-color: #ffffff; border: 1px solid #eee; 
    padding: 20px; border-radius: 10px; text-align: center;
    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    height: 100%;
}
.stats-number { font-size: 2rem; font-weight: bold; color: #8d6e63; }
.stats-label { font-size: 0.9rem; color: #666; text-transform: uppercase; letter-spacing: 1px; }

/* 7. 來源標籤 */
.source-badge {
    position: absolute; bottom: 10px; right: 10px;
    padding: 3px 10px; border-radius: 10px;
    font-size: 0.75rem; font-weight: 600; opacity: 0.9;
}
.badge-frc { background-color: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }
.badge-book { background-color: #e3f2fd; color: #1565c0; border: 1px solid #bbdefb; }
.badge-default { background-color: #f5f5f5; color: #616161; border: 1px solid #e0e0e0; }

/* 8. 開發者頁面與致謝 */
.dev-header {
    background-color: #fff; padding: 2rem; border-radius: 15px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #eee;
    margin-bottom: 2rem;
}
.tech-badge {
    display: inline-block; padding: 6px 14px; margin: 4px;
    background-color: #eefeef; color: #2e7d32; border-radius: 20px;
    font-size: 0.9rem; font-weight: 600; border: 1px solid #c8e6c9;
}
.section-title {
    font-size: 1.4rem; font-weight: 700; color: #2c3e50; 
    border-bottom: 3px solid #8d6e63; padding-bottom: 8px; margin-bottom: 15px;
    display: inline-block;
}
/* 9. 國旗小圖示 */
.flag-icon {
    height: 1em; width: auto; vertical-align: text-bottom;
    margin-right: 5px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); border-radius: 2px;
}
</style>
''', unsafe_allow_html=True)

# --- 輔助函數 ---
@st.cache_data(ttl=60)
def check_connection_status(timeout=3):
    try:
        requests.get("https://www.google.com", timeout=timeout)
        return "good"
    except: return "unstable"

def _make_qr(data: str):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(data); qr.make(fit=True)
    img = qr.make_image(fill_color="#222", back_color="#fff")
    buf = BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return buf

def img_to_bytes(img_path):
    img_bytes = Path(img_path).read_bytes()
    return base64.b64encode(img_bytes).decode()

def get_badge_html(source_text):
    src = str(source_text).lower()
    if "frc" in src:
        text = "FRC Data"
        css_class = "badge-frc"
    elif "phrasebook" in src or "jason" in src:
        text = "Phrasebook"
        css_class = "badge-book"
    else:
        text = "Database"
        css_class = "badge-default"
    return f'<span class="source-badge {css_class}">{text}</span>'

# --- 克里奧語發音 TTS ---
@st.cache_resource(show_spinner=False)
def load_tts_model():
    """載入 facebook/mms-tts-acf 克里奧語 TTS 模型（只載入一次）"""
    try:
        from transformers import VitsModel, AutoTokenizer
        import torch
        _model = VitsModel.from_pretrained("facebook/mms-tts-acf")
        _tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-acf")
        return _model, _tokenizer
    except Exception:
        return None, None

def generate_kweyol_audio(text: str):
    """將克里奧語文字轉為 WAV bytes；失敗回傳 None"""
    if not text or not text.strip():
        return None
    tts_model, tts_tokenizer = load_tts_model()
    if tts_model is None:
        return None
    try:
        import torch
        import scipy.io.wavfile as wav_writer
        inputs = tts_tokenizer(text.strip(), return_tensors="pt")
        with torch.no_grad():
            waveform = tts_model(**inputs).waveform
        waveform_np = waveform.squeeze().numpy()
        waveform_int16 = (waveform_np * 32767).clip(-32768, 32767).astype(np.int16)
        buf = BytesIO()
        wav_writer.write(buf, tts_model.config.sampling_rate, waveform_int16)
        buf.seek(0)
        return buf.read()
    except Exception:
        return None

def tts_button(text: str, btn_key: str):
    """顯示 🔊 發音按鈕，點擊後自動直接播放發音"""
    if st.button("🔊 Kwéyòl", key=btn_key, help=f"播放克里奧語發音：{text}"):
        with st.spinner("產生發音中..."):
            audio_bytes = generate_kweyol_audio(text)
        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav", autoplay=True)
        else:
            st.warning("⚠️ 發音模型尚未就緒，請確認 torch 與 transformers 已安裝")

def english_tts_button(text: str, btn_key: str):
    """英文發音按鈕，使用瀏覽器內建 Web Speech API（即時無需模型）"""
    import streamlit.components.v1 as components
    safe = text.replace("'", "\\'").replace('"', '\\"').replace('\n', ' ')
    if st.button("🔊 English", key=btn_key, help=f"Pronounce in English: {text}"):
        components.html(f"""
        <script>
            var u = new SpeechSynthesisUtterance("{safe}");
            u.lang = 'en-US';
            window.speechSynthesis.speak(u);
        </script>
        """, height=0)

# [核心] 載入資料庫
if 'databases' not in st.session_state:
    st.session_state.databases = load_databases()
databases = st.session_state.databases

TEXTS = {
    'title': "Kwéyòl Dictionary (Beta)",
    'subtitle': "Dictionary + Smart Rule-Based Translation",
    'warning_header': "Note:",
    'warning_body': "Beta Translation: Optimized for local context using Symbolic AI rules."
}

# --- 側邊欄 ---
with st.sidebar:
    st.header("Project Info")
    
    query_params = st.query_params
    if query_params.get("admin") == "true":
        if st.button("🔄 Reload Database (Dev)", use_container_width=True):
            st.cache_data.clear()
            st.session_state.databases = load_databases()
            databases = st.session_state.databases
            st.success("Reloaded!")
            st.rerun()

    with st.expander("📖 User Guide", expanded=False):
        st.markdown("""
        1. **Dictionary**: Lookup.
        2. **Phrase Finder**: Examples.
        3. **Beta Translation**: Sentence Builder.
        4. **Dashboard**: Stats.
        """)

    with st.expander("🛠️ Update Log", expanded=False):
        st.markdown("**v6.10 Stable**\n- POS Stats Simplified.\n- Layout Refined.")

    with st.expander("💬 Feedback", expanded=False):
        st.markdown("[Feedback Form](https://forms.gle/2YiiAwyKkhGLYqTY7)")
    
    st.markdown("---")
    st.subheader("Mobile Access")
    public_url = "https://stlucia-kweyol.streamlit.app/"
    st.image(_make_qr(public_url), width=200)
    st.markdown(f"<div style='text-align:left'><a href='{public_url}' target='_blank' style='color:#8c7b75; text-decoration:none;'>Open in Browser ↗</a></div>", unsafe_allow_html=True)

# =================================================
# 主畫面
# =================================================

col_header_L, col_header_R = st.columns([3, 1])

with col_header_L:
    st.title(TEXTS['title'])
    st.caption(TEXTS['subtitle'])

with col_header_R:
    status = check_connection_status()
    st_color = "green" if status == 'good' else "red"
    st.markdown(f"""
    <div style="text-align: right; padding-top: 20px; font-size: 0.85rem; color: #888;">
        System Status: <span style="color: {st_color}; font-weight: bold;">● {status.upper()}</span>
    </div>
    """, unsafe_allow_html=True)

# 6 個分頁
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Dictionary", "Phrase Finder", "Beta Translation", "Dashboard", "About Kwéyòl", "About Developer"])

# === Tab 1: Dictionary ===
with tab1:
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    
    if 'wotd' not in st.session_state:
        try:
            df_k2e = databases['k2e_data']
            if not df_k2e.empty:
                candidates = df_k2e[df_k2e['Kweyol_Example'].astype(str).str.strip() != ''].to_dict('records')
                st.session_state['wotd'] = random.choice(candidates) if candidates else None
            else:
                st.session_state['wotd'] = None
        except:
            st.session_state['wotd'] = None

    wotd = st.session_state.get('wotd')
    if wotd:
        w_word = wotd.get('Kweyol word', 'Bonjou')
        w_pos  = wotd.get('pos', '').strip()
        w_def  = wotd.get('Definition', '')
        w_ex_k = wotd.get('Kweyol_Example', '')
        w_ex_e = wotd.get('English_Example', '')

        st.markdown(f"""
        <div style="background:#fff; border:1px solid #e8e0d5; border-radius:12px;
                    padding:24px 28px; margin-bottom:24px; border-left:5px solid #aebf9e;
                    box-shadow:0 2px 8px rgba(0,0,0,0.05);">
            <div style="font-size:0.72rem; font-weight:700; letter-spacing:2px;
                        color:#999; text-transform:uppercase; margin-bottom:10px;">
                WORD OF THE DAY
            </div>
            <div style="display:flex; align-items:baseline; gap:10px; margin-bottom:6px;">
                <span style="font-size:1.9rem; font-weight:800; color:#2e7d32;">{html.escape(w_word)}</span>
                <span style="font-size:0.95rem; color:#999; font-style:italic;">{html.escape(w_pos)}</span>
            </div>
            <div style="font-size:1.05rem; color:#333; margin-bottom:14px;">{html.escape(w_def)}</div>
            <div style="border-left:4px solid #aebf9e; padding:10px 16px; background:#f8faf8; border-radius:0 8px 8px 0;">
                <div style="color:#2e7d32; font-weight:700; margin-bottom:4px;">{html.escape(w_ex_k)}</div>
                <div style="color:#777; font-size:0.95rem;">{html.escape(w_ex_e)}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns([3,1])
    with col1:
        search_direction = st.radio("Direction", ["English → Kwéyòl", "Kwéyòl → English"], horizontal=True, key='s_dir')
    with col2:
        search_mode = st.radio("Mode", ["Exact", "Fuzzy"], horizontal=True, key='s_mode')

    input_label = "Enter English word" if search_direction == "English → Kwéyòl" else "Enter Kwéyòl word"
    search_word = st.text_input(input_label, key='search_input', placeholder="Type word here...")
    
    if st.button("Search", key='btn_dict') or search_word:
        if search_word.strip():
            results = fast_query(search_word, 'exact' if search_mode == "Exact" else 'fuzzy', search_direction, databases)
            st.markdown("<br>", unsafe_allow_html=True)
            if results:
                st.success(f"Found {len(results)} result(s)")
                for i, res in enumerate(results):
                    source_badge = get_badge_html(res.get('source', 'Database'))
                    
                    if search_direction == "English → Kwéyòl":
                        word = res.get('english', '')
                        pos = res.get('pos', '').strip()
                        kweyol = res.get('Kweyol', '')
                        header_text = f"{word} ({pos}.)" if pos else word
                        
                        st.markdown(f'''
                        <div class="result-card">
                            <div style="font-size:1.6rem; font-weight:700; color:#2c2c2c; margin-bottom:5px;">{html.escape(header_text)}</div>
                            <div style="font-size:1.6rem; font-weight:700; color:#5d4037;">{html.escape(kweyol)}</div>
                            {source_badge}
                        </div>''', unsafe_allow_html=True)
                        st_copy_to_clipboard(kweyol, before_copy_label="📋 Copy", after_copy_label="✅ Copied!", key=f"copy_e2k_{i}")
                        tts_button(kweyol, btn_key=f"tts_e2k_{i}")
                    else:
                        kw_word = res.get('Kweyol word', '')
                        pos = res.get('pos', '').strip()
                        definition = res.get('Definition', '')
                        eng_ex = res.get('English_Example', '')
                        kwe_ex = res.get('Kweyol_Example', '')
                        header_text = f"{kw_word} ({pos}.)" if pos else kw_word
                        
                        st.markdown(f'''
                        <div class="result-card">
                            <div style="font-size:1.6rem; font-weight:700; color:#2c2c2c; margin-bottom:5px;">{html.escape(header_text)}</div>
                            <div class="def-block"><b>Definition:</b> {html.escape(definition)}</div>
                            <div class="ex-block">
                                <div style="color:#5d4037; font-weight:600; font-style:italic; margin-bottom:4px;">{html.escape(kwe_ex)}</div>
                                <div style="color:#666; font-style:italic;">{html.escape(eng_ex)}</div>
                            </div>
                            {source_badge}
                        </div>''', unsafe_allow_html=True)
                        st_copy_to_clipboard(definition, before_copy_label="📋 Copy", after_copy_label="✅ Copied!", key=f"copy_k2e_{i}")
                        col_tts_kw, col_tts_en = st.columns([1, 1])
                        with col_tts_kw:
                            tts_button(kw_word, btn_key=f"tts_k2e_{i}")
                        with col_tts_en:
                            english_tts_button(definition, btn_key=f"tts_en_{i}")
            else:
                st.info("No results found. Try Fuzzy mode.")

# === Tab 2: Phrase Finder ===
with tab2:
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    phrase_query = st.text_input("Keyword", key="phrase_search", placeholder="e.g. eat, manje")
    
    if phrase_query:
        examples = search_examples(phrase_query, databases)
        st.markdown("<br>", unsafe_allow_html=True)
        if examples:
            st.success(f"Found {len(examples)} sentences")
            for i, ex in enumerate(examples):
                pos_val = ex.get('pos', '')
                pos_text = f" ({pos_val}.)" if pos_val else ""
                source_badge = get_badge_html(ex.get('source_word', 'Phrasebook')) 
                
                st.markdown(f"""
                <div class="result-card" style="border-left:4px solid #aebf9e">
                    <div style="margin-bottom: 5px;">
                        <span style="color: #556b2f; font-size: 1.3rem; font-weight: 700;">{html.escape(ex['kweyol'])}{html.escape(pos_text)}</span>
                    </div>
                    <p style="font-size: 1.1rem; color: #6d5e58;">{html.escape(ex['english'])}</p>
                    {source_badge}
                </div>""", unsafe_allow_html=True)
                st_copy_to_clipboard(ex['kweyol'], before_copy_label="📋 Copy", after_copy_label="✅ Copied!", key=f"copy_phr_{i}")
                tts_button(ex['kweyol'], btn_key=f"tts_phr_{i}")
        else:
            st.info("No examples found.")

# === Tab 3: Beta Translation ===
with tab3:
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.markdown("##### Smart Rule-Based Translation")
    txt = st.text_area("Input (English)", height=100, placeholder="e.g., Let's go to the waterfall")
    
    if 'translation_result' not in st.session_state: st.session_state['translation_result'] = ""
    
    if st.button("Translate", type="primary", use_container_width=True):
        if txt.strip():
            res = run_lego_translation(txt.strip(), databases)
            st.session_state['translation_result'] = res
    
    if st.session_state['translation_result']:
        final = st.session_state['translation_result']
        st.markdown(f'''
        <div class="translation-card-rbmt">
            <div style="font-size:0.8rem;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:5px">Result</div>
            <div style="font-size:1.6rem;color:#2c2c2c;font-weight:700;">{final}</div>
            <div style="margin-top:15px; font-size:0.8rem; color:#888;">*Context-Aware Logic & Verified Dictionary.</div>
        </div>
        ''', unsafe_allow_html=True)
        st_copy_to_clipboard(final, before_copy_label="📋 Copy", after_copy_label="✅ Copied!")
        tts_button(final, btn_key="tts_translation")

# === Tab 4: Dashboard ===
with tab4:
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    stats = analyze_database_stats(databases)
    
    st.markdown("##### 📊 Database Overview")
    
    # 2x2 佈局
    r1_c1, r1_c2 = st.columns(2)
    e2k_count = len(databases['e2k_data'])
    k2e_count = len(databases['k2e_data'])
    total_count = e2k_count + k2e_count
    
    with r1_c1:
        st.markdown(f'''<div class="stats-card"><div class="stats-number">{e2k_count}</div><div class="stats-label">English Entries</div></div>''', unsafe_allow_html=True)
    with r1_c2:
        st.markdown(f'''<div class="stats-card"><div class="stats-number">{k2e_count}</div><div class="stats-label">Kwéyòl Entries</div></div>''', unsafe_allow_html=True)
    
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    
    r2_c1, r2_c2 = st.columns(2)
    per = round((stats['example_coverage']['With Examples']/stats['k2e_count'])*100, 1) if stats['k2e_count'] else 0
    
    with r2_c1:
        st.markdown(f'''<div class="stats-card"><div class="stats-number">{total_count}</div><div class="stats-label">Total Words</div></div>''', unsafe_allow_html=True)
    with r2_c2:
        st.markdown(f'''<div class="stats-card"><div class="stats-number">{per}%</div><div class="stats-label">Example Coverage</div></div>''', unsafe_allow_html=True)
    
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Part of Speech")
        
        # [修正] 詞性分類邏輯：只顯示主要詞性，其他歸類為 Others
        if stats['pos_distribution']:
            # 1. 建立對照表
            def map_pos_category(pos_tag):
                p = str(pos_tag).lower().strip().replace('.', '')
                if p in ['n', 'noun', 'nouns']: return 'Noun'
                if p in ['v', 'verb', 'vi', 'vt', 'verbs']: return 'Verb'
                if p in ['adj', 'adjective', 'adjectives']: return 'Adjective'
                if p in ['adv', 'adverb', 'adverbs']: return 'Adverb'
                return 'Others'

            # 2. 轉換資料
            raw_data = list(stats['pos_distribution'].items())
            df_raw = pd.DataFrame(raw_data, columns=['RawType', 'Count'])
            df_raw['Type'] = df_raw['RawType'].apply(map_pos_category)
            
            # 3. 加總
            df_pos = df_raw.groupby('Type', as_index=False)['Count'].sum()
            
            # 4. 排序：讓主要詞性排前面 (Noun, Verb, Adj, Adv, Others)
            sort_order = ['Noun', 'Verb', 'Adjective', 'Adverb', 'Others']
            
            chart = alt.Chart(df_pos).mark_arc(innerRadius=60).encode(
                theta=alt.Theta(field="Count", type="quantitative"),
                color=alt.Color(field="Type", type="nominal", sort=sort_order),
                order=alt.Order("Count", sort="descending"),
                tooltip=["Type", "Count"]
            ).properties(height=350)
            
            st.altair_chart(chart, use_container_width=True)
            
    with c2:
        st.markdown("##### Alphabet Frequency")
        if stats['alpha_eng']:
            df_alpha = pd.DataFrame({'English': stats['alpha_eng'], 'Kwéyòl': stats['alpha_kwe']})
            st.line_chart(df_alpha, color=["#888888", "#aebf9e"])

# === Tab 5: About Kwéyòl ===
with tab5:
    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <h3>
        <img src="https://upload.wikimedia.org/wikipedia/commons/9/9f/Flag_of_Saint_Lucia.svg" class="flag-icon"> 
        The Soul of the Nation
    </h3>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    **Saint Lucian Kwéyòl** (also known as *Patwa*) is a French-lexicon Creole language. 
    It emerged in the 17th century from the contact between enslaved West Africans and French colonists. 
    Linguistically, it combines a vocabulary derived largely from 17th-century French (lexifier) with syntactic structures from West African languages (substrate).
    """)
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.info("""
        **🗣️ Not "Broken French"**
        It is a fully developed language with its own systematic grammar, syntax, and orthography. 
        It is mutually intelligible with the Creoles of **Martinique, Dominica, Guadeloupe**, and to a lesser extent, Haiti.
        """)
        
    with c2:
        st.success("""
        **🎉 Jounen Kwéyòl**
        Celebrated on the **last weekend of October (specifically the last Sunday)**, this is the largest cultural festival in Saint Lucia. 
        It honors the language, traditional food (Green Fig & Saltfish), dress (*Wob Dwiyet*), and music.
        """)
    
    st.markdown("---")
    st.markdown("##### 📜 Writing & Standardization")
    st.markdown("""
    For a long time, Kwéyòl was only an oral language. However, due to the efforts of the **Folk Research Centre (FRC)** and linguists, a standard writing system was developed. 
    Today, it is used in radio news, cultural documentation, and increasingly in education.
    
    *Reference: Folk Research Centre (FRC) & Saint Lucia National Language Policy.*
    """)

# === Tab 6: About Developer ===
with tab6:
    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    
    # 照片讀取邏輯
    img_src = "https://ui-avatars.com/api/?name=Jimmy+Chiu&size=300&background=eee"
    possible_files = ["IMG_1304.JPEG", "IMG_1304.jpg", "IMG_1304.png", "profile.jpg"]
    for f in possible_files:
        if os.path.exists(f):
            try: img_src = f"data:image/jpeg;base64,{img_to_bytes(f)}"; break
            except: pass

    # 開發者卡片 (已移除個人聯絡按鈕)
    st.markdown(f"""
    <div class="dev-header">
        <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 40px;">
            <img src="{img_src}" 
                 style="width: 180px; height: 180px; border-radius: 50%; object-fit: cover; border: 5px solid #fff; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
            <div style="flex: 1;">
                <h1 style="margin-bottom: 5px; color: #2c2c2c;"> Jimmy (Tzu Ming Chiu)</h1>
                <h3 style="margin-top: 0; color: #8d6e63; font-weight: 500;">ICT Intern, Taiwan Technical Mission in Saint Lucia, 
                <br> 2025.08-2026.01</h3>
                <p style="font-size: 1.1rem; color: #555; line-height: 1.6;">
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.markdown('<div class="section-title">👨‍💻 About this Project</div>', unsafe_allow_html=True)
        st.info("""
        **Project Name:** Kwéyòl Intelligent Translation System
        
        This system was developed to assist in the preservation and learning of the Saint Lucian Kwéyòl language. 
        Unlike traditional black-box AI models, this tool uses a **transparent, rule-based architecture** that mimics how native speakers construct sentences.
        """)
        
        st.markdown('<br><div class="section-title">🚀 Project Highlights</div>', unsafe_allow_html=True)
        st.markdown("""
        * **Symbolic AI Engine:** Designed a custom Python engine that parses English grammar and maps it to Kwéyòl syntax rules (e.g., tense markers *té, ka, kay*).
        * **Context-Aware Algorithms:** Implemented Regex-based logic to resolve polysemy (e.g., distinguishing *"Run a business"* from *"Run fast"*).
        * **Lightweight Architecture:** Optimized the system to run on CPU-only cloud environments, reducing deployment size by **90%** compared to Neural Network approaches.
        * **Fuzzy Search:** Integrated Levenshtein Distance algorithms to handle user typos and improve dictionary accessibility.
        """)

    with c2:
        st.markdown('<div class="section-title">🛠️ Tech Stack</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="line-height: 2.2;">
            <span class="tech-badge">Python 3.13</span>
            <span class="tech-badge">Streamlit</span>
            <span class="tech-badge">Pandas</span>
            <span class="tech-badge">Regex (NLP)</span>
            <span class="tech-badge">Git / GitHub Actions</span>
            <span class="tech-badge">Levenshtein Algo</span>
            <span class="tech-badge">Data Structures</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.subheader("🤝 Acknowledgments")
    st.markdown("This project was made possible with the support of:")
    
    ack_col1, ack_col2 = st.columns(2)
    
    with ack_col1:
        st.markdown("""
        **<img src="https://upload.wikimedia.org/wikipedia/commons/7/72/Flag_of_the_Republic_of_China.svg" class="flag-icon"> Taiwan Partners**
        """, unsafe_allow_html=True)
        st.markdown("""
        - **Embassy of the Republic of China (Taiwan) in Saint Lucia**
        - **Taiwan Technical Mission in Saint Lucia**
        """)
        
    with ack_col2:
        st.markdown("""
        **<img src="https://upload.wikimedia.org/wikipedia/commons/9/9f/Flag_of_Saint_Lucia.svg" class="flag-icon"> Saint Lucia Partners**
        """, unsafe_allow_html=True)
        st.markdown("""
        - **OECS (Organisation of Eastern Caribbean States)**
        - **Folk Research Centre (FRC)**
        - **Jason C. Joseph (Author, A Phrasebook for Busy Folks)**
        """)

# 頁尾 (只保留這一個)
st.markdown(f"""
<div style="margin-top:3rem; font-size:0.8rem; color:#aaa; text-align:center;">
{TEXTS['warning_header']} {TEXTS['warning_body']}
</div>
""", unsafe_allow_html=True)