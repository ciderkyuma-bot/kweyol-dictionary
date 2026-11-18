import streamlit as st
import pandas as pd
import os
import re
import unicodedata
import string
import difflib

# --- 0. 核心工具 ---
def normalize_text(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = "".join([c for c in text if unicodedata.category(c) != 'Mn'])
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()

# --- 1. 資料庫載入 ---
@st.cache_data
def load_databases():
    databases = {
        "e2k_data": pd.DataFrame(),
        "k2e_data": pd.DataFrame(),
        "grammar_rules": pd.DataFrame(),
        "patterns": pd.DataFrame()
    }

    current_dir = os.path.dirname(os.path.abspath(__file__))
    e2k_path = os.path.join(current_dir, "e2k.csv")
    k2e_path = os.path.join(current_dir, "k2e.csv")
    grammar_path = os.path.join(current_dir, "grammar.csv")
    patterns_path = os.path.join(current_dir, "patterns.csv")

    default_rules = [
        {"english": "will not", "kweyol": "pa kay", "priority": 1},
        {"english": "do not", "kweyol": "pa", "priority": 1},
        {"english": "did not", "kweyol": "pa té", "priority": 1},
        {"english": "will", "kweyol": "kay", "priority": 3},
        {"english": "is", "kweyol": "ka", "priority": 3}, 
        {"english": "am", "kweyol": "ka", "priority": 3},
        {"english": "are", "kweyol": "ka", "priority": 3},
        {"english": "is", "kweyol": "sé", "priority": 4}, 
        {"english": "i", "kweyol": "mwen", "priority": 1},
        {"english": "my", "kweyol": "mwen", "priority": 2},
    ]

    try:
        if os.path.exists(e2k_path): 
            databases["e2k_data"] = pd.read_csv(e2k_path).fillna("")
        
        if os.path.exists(k2e_path): 
            databases["k2e_data"] = pd.read_csv(k2e_path).fillna("")
        
        if os.path.exists(grammar_path):
            rules = pd.read_csv(grammar_path).fillna("")
            if 'priority' in rules.columns:
                rules['priority'] = pd.to_numeric(rules['priority'], errors='coerce').fillna(99)
                rules = rules.sort_values(by='priority')
            databases["grammar_rules"] = rules
        else:
            databases["grammar_rules"] = pd.DataFrame(default_rules)
            
        if os.path.exists(patterns_path):
            pats = pd.read_csv(patterns_path).fillna("")
            databases["patterns"] = pats
            
        return databases
    except Exception as e:
        databases["grammar_rules"] = pd.DataFrame(default_rules)
        return databases

# --- 2. 詞性清理 ---
def get_clean_pos(raw_text):
    if not isinstance(raw_text, str): return "Unknown"
    text = raw_text.strip()
    if not text: return "Unknown"
    text_lower = text.lower().replace(".", "")
    
    if text_lower.startswith('noun') or text_lower == 'n': return 'Noun'
    if text_lower.startswith('verb') or text_lower == 'v': return 'Verb'
    if text_lower.startswith('adj'): return 'Adjective'
    if text_lower.startswith('adv'): return 'Adverb'
    if text_lower.startswith('prep'): return 'Preposition'
    if text_lower.startswith('conj'): return 'Conjunction'
    if text_lower.startswith('pron') or text_lower.startswith('pro'): return 'Pronoun'
    if text_lower.startswith('inter') or text_lower.startswith('exclam'): return 'Interjection'
    if text_lower.startswith('art') or text_lower == 'det': return 'Article/Det'
    
    if 'phr' in text_lower: return 'Phrase'
    if 'id' in text_lower: return 'Idiom'
    
    return text.capitalize()

# --- 3. 搜尋功能 ---
def fast_query(word, mode, direction, databases):
    if not word: return []
    clean_search = normalize_text(word)
    if direction == "English → Kwéyòl": 
        df = databases['e2k_data']
        col = 'english'
    else: 
        df = databases['k2e_data']
        col = 'Kweyol word'
    if df.empty: return []

    search_col = df[col].astype(str).apply(normalize_text)
    
    if mode == 'exact':
        matches = df[search_col == clean_search].copy()
        if not matches.empty:
            matches['match_score'] = 1.0
            matches['match_pct'] = "100%"
            matches['match_type'] = "Exact match"
    else:
        # Fuzzy / Contains mode
        cond = search_col.str.contains(clean_search, regex=False)
        matches = df[cond].copy()
        if matches.empty:
            # If substring not found, try fuzzy match across top candidates
            import difflib
            ratios = search_col.apply(lambda x: difflib.SequenceMatcher(None, clean_search, x).ratio())
            matches = df[ratios >= 0.65].copy()
            if not matches.empty:
                matches['match_score'] = ratios[ratios >= 0.65]
            else:
                matches['match_score'] = 0.0
        else:
            def calculate_relevance(val):
                v = str(val).lower().strip()
                v_clean = normalize_text(v)
                if v_clean == clean_search:
                    return 1.0, "Exact match", "100%"
                words = v_clean.split()
                if clean_search in words:
                    # Whole word match, slightly penalized by total length
                    score = 0.95 - min(0.08, (len(v_clean) - len(clean_search)) * 0.005)
                    return score, "Contains your input", f"{int(score * 100)}%"
                if clean_search in v_clean:
                    score = 0.86 - min(0.15, (len(v_clean) - len(clean_search)) * 0.008)
                    return score, "Contains your input", f"{int(score * 100)}%"
                import difflib
                sim = difflib.SequenceMatcher(None, clean_search, v_clean).ratio()
                score = sim * 0.8
                return score, "Similar match", f"{int(score * 100)}%"

            metrics = [calculate_relevance(val) for val in matches[col]]
            matches['match_score'] = [m[0] for m in metrics]
            matches['match_type'] = [m[1] for m in metrics]
            matches['match_pct'] = [m[2] for m in metrics]

    if not matches.empty and 'match_score' in matches.columns:
        # Sort descending so 100% / highest matches are always at the top
        matches = matches.sort_values(by='match_score', ascending=False)
        
    return matches.to_dict('records')

def search_examples(query, databases):
    if not query: return []
    clean_query = normalize_text(query)
    df = databases['k2e_data']
    if df.empty: return []
    mask = (df['Kweyol_Example'].astype(str).apply(normalize_text).str.contains(clean_query, regex=False) |
            df['English_Example'].astype(str).apply(normalize_text).str.contains(clean_query, regex=False))
    matches = df[mask]
    results = []
    for _, row in matches.iterrows():
        results.append({'kweyol': row['Kweyol_Example'], 'english': row['English_Example'], 'pos': row.get('pos',''), 'source_word': row['Kweyol word']})
    return results

# --- 4. 文法與句型引擎 ---

def apply_construction_patterns(text, databases):
    text = " " + text.lower() + " "
    patterns_df = databases.get('patterns', pd.DataFrame())
    if not patterns_df.empty:
        for _, row in patterns_df.iterrows():
            try:
                text = re.sub(str(row['english_regex']), str(row['kweyol_replacement']), text, flags=re.IGNORECASE)
            except: pass
    return text.strip()

def apply_grammar_logic(text, databases):
    text = " " + text.lower() + " "
    rules_df = databases.get('grammar_rules', pd.DataFrame())
    
    if not rules_df.empty:
        for _, row in rules_df.iterrows():
            trigger = str(row['english']).lower().strip()
            marker = str(row['kweyol']).strip()
            if not trigger or not marker: continue

            if trigger in ['have done', 'has done']:
                text = re.sub(r"\b(have|has)\b", " ja ", text)
            elif trigger in ['is', 'am', 'are'] and marker == 'ka':
                def progressive_repl(match):
                    return f" {marker} {match.group(1)} " 
                text = re.sub(r"\b" + trigger + r"\s+(\w+)ing\b", progressive_repl, text)
            elif trigger in ['was', 'were'] and marker == 'té':
                def past_prog_repl(match):
                    return f" té ka {match.group(1)} "
                if re.search(r"\b" + trigger + r"\s+\w+ing\b", text):
                    text = re.sub(r"\b" + trigger + r"\s+(\w+)ing\b", past_prog_repl, text)
                text = re.sub(r"\b" + trigger + r"\b", " té ", text)
            else:
                pattern = r"\b" + re.escape(trigger) + r"\b"
                if re.search(pattern, text):
                    text = re.sub(pattern, f" {marker} ", text)
    return text.strip()

def apply_context_logic(text):
    context_rules = [
        # --- 0. 關鍵短語修復 (最高優先級) ---
        
        # [新增] My name is -> Non mwen sé
        (r"\bmy\s+name\s+is\b", "non mwen sé"),
        
        # [修正] is from -> sòti (不是 dépi!)
        (r"\b(is|am|are)\s+from\b", "sòti"),
        
        # [修正] He/She -> i (純正聖露西亞用法，不改成 Li)
        (r"\b(he|she)\b", "i"),
        (r"\b(it)\b", "i"), # It 通常也是 i

        # 1. RUN: Business vs Movement
        (r"\brun\b(?=\s*(?:a\s+)?(?:business|shop|store|company))", "jéré"),
        
        # 2. RIGHT: Direction vs Correct
        (r"\bright\b(?=\s*(?:hand|turn|side))", "dwèt"),
        
        # 3. FLY: Insect vs Action
        (r"(?<=a\s)fly\b", "mouch"),
        (r"(?<=the\s)fly\b", "mouch-la"),
        (r"\bfly\b(?=.*(?:sky|plane|bird))", "volé"),
        
        # 4. PLAY: Instrument vs Game
        (r"\bplay\b(?=\s*(?:the\s+)?(?:guitar|piano|drum|music))", "joué"),

        # 5. TO: Direction (去) vs Purpose (為了)
        (r"(?<=\bgo\s)to\b", "aprep"),
        (r"(?<=\bgoes\s)to\b", "aprep"),
        (r"(?<=\bwent\s)to\b", "aprep"),
        (r"(?<=\bcome\s)to\b", "aprep"),
        (r"(?<=\bwalk\s)to\b", "aprep"),
        (r"(?<=\brun\s)to\b", "aprep"),
        (r"(?<=\bfly\s)to\b", "aprep"),
        
        # Let's go to -> Annou alé aprep
        (r"\blet\s+us\s+go\s+to\b", "annou alé aprep"),
    ]
    
    for pattern, replacement in context_rules:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
    return text

# 模糊搜尋小工具
def find_closest_match(word, vocab_keys):
    matches = difflib.get_close_matches(word, vocab_keys, n=1, cutoff=0.85)
    return matches[0] if matches else None

def run_lego_translation(text, databases):
    if not text: return ""

    # [關鍵] 保存原始文字 (含大小寫)，用來偵測人名
    original_text = text.strip()
    ending_punct = ""
    if original_text and original_text[-1] in ".?!":
        ending_punct = original_text[-1]
        text = text.rstrip(".?!")

    # 人名偵測：抓取所有大寫開頭的字 (排除句首的第一個字，除非它本來就是大寫)
    # 這裡我們簡單抓所有大寫字，稍後用字典過濾
    potential_names = set(re.findall(r"\b[A-Z][a-z]*\b", original_text))

    text = text.replace("’", "'")
    
    # 縮寫還原 (Contractions)
    contractions = {
        "I'll": "I will", "i'll": "i will",
        "You'll": "You will", "you'll": "you will",
        "He'll": "He will", "he'll": "he will",
        "She'll": "She will", "she'll": "she will",
        "We'll": "We will", "we'll": "we will",
        "They'll": "They will", "they'll": "they will",
        "I'm": "I am", "i'm": "i am",
        "It's": "It is", "it's": "it is",
        "Don't": "Do not", "don't": "do not",
        "Didn't": "Did not", "didn't": "did not",
        "Can't": "Can not", "can't": "can not",
        "Won't": "Will not", "won't": "will not",
        "I've": "I have", "i've": "i have",
        "You've": "You have", "you've": "you have",
        "He've": "He has", "he've": "he has",
        "She've": "She has", "she've": "she has",
        "We've": "We have", "we've": "we have",
        "They've": "They have", "they've": "they have",
        "Isn't": "Is not", "isn't": "is not",
        "Ain't": "Am not", "ain't": "am not",
        "That's": "That is", "that's": "that is",
        "What's": "What is", "what's": "what is",
        "There's": "There is", "there's": "there is",
        "Where's": "Where is", "where's": "where is",
        "When's": "When is", "when's": "when is",
        "Then's": "Then is", "then's": "then is",
        "Who's": "Who is", "who's": "who is",
        "How's": "How is", "how's": "how is",
        "This's": "This is", "this's": "this is",
        "I'd": "I would", "i'd": "i would",
        "You'd": "You would", "you'd": "you would",
        "He'd": "He would", "he'd": "he would",
        "She'd": "She would", "she'd": "she would",
        "We'd": "We would", "we'd": "we would",
        "They'd": "They would", "they'd": "they would",
        "Let's": "Let us", "let's": "let us"
    }
    
    for contraction, expansion in contractions.items():
        text = text.replace(contraction, expansion)

    # 執行順序：1.語境(優先) -> 2.句型 -> 3.文法
    text = apply_context_logic(text)
    text = apply_construction_patterns(text, databases)
    text = apply_grammar_logic(text, databases)
    
    irregular_verbs = {
        "eaten": "eat", "ate": "eat",
        "gone": "go", "went": "go",
        "seen": "see", "saw": "see",
        "taken": "take", "took": "take",
        "done": "do", "did": "do",
        "known": "know", "knew": "know",
        "said": "say", "told": "tell"
    }

    dictionary = {}
    
    def add_to_dict(k, v):
        if k and v:
            clean_k = normalize_text(str(k))
            clean_v = str(v).split(',')[0].strip().replace('"', '').rstrip(".") 
            dictionary[clean_k] = clean_v

    df_k2e = databases['k2e_data']
    if not df_k2e.empty:
        for _, row in df_k2e.iterrows():
            add_to_dict(row['English_Example'], row['Kweyol_Example'])
            add_to_dict(row['Definition'], row['Kweyol word'])

    df_e2k = databases['e2k_data']
    if not df_e2k.empty:
        for _, row in df_e2k.iterrows(): add_to_dict(row['english'], row['Kweyol'])

    grammar_df = databases.get('grammar_rules', pd.DataFrame())
    if not grammar_df.empty:
        for _, row in grammar_df.iterrows():
            clean_k = normalize_text(str(row['kweyol']).split(',')[0])
            if clean_k not in dictionary: dictionary[clean_k] = row['kweyol']

    patterns_df = databases.get('patterns', pd.DataFrame())
    if not patterns_df.empty:
        for _, row in patterns_df.iterrows():
            parts = str(row['kweyol_replacement']).split()
            for part in parts:
                if not part.startswith('\\'):
                    dictionary[normalize_text(part)] = part
    
    # [關鍵] 定義語境代號與白名單
    context_words = {
        "jéré": "jéré", "dwèt": "dwèt", "korèk": "korèk", 
        "mouch": "mouch", "volé": "volé", "joué": "joué",
        "annou": "annou", "aprep": "a", "sòti": "sòti",
        # 加入基本代名詞，避免被當成未知字
        "non": "non", "mwen": "mwen", "sé": "sé", "i": "i"
    }
    for k, v in context_words.items():
        if k not in dictionary: dictionary[k] = v

    fallback_vocab = {
        "kay": "kay", "ka": "ka", "te": "té", "pa": "pa", "ja": "ja", 
        "mwen": "mwen", "ou": "ou", "li": "li", "nou": "nou", "yo": "yo", 
        "ek": "èk", "la": "la", "an": "an", "se": "sé", "sa": "sa"
    }
    for k, v in fallback_vocab.items():
        if k not in dictionary: dictionary[k] = v

    search_buffer = normalize_text(text)
    translated_chunks = []
    all_vocab_keys = list(dictionary.keys())
    
    while search_buffer:
        search_buffer = search_buffer.strip()
        if not search_buffer: break
        
        first_word = search_buffer.split(' ')[0]
        if first_word in irregular_verbs:
            restored_word = irregular_verbs[first_word]
            search_buffer = restored_word + search_buffer[len(first_word):]
            continue 

        best_match = None
        best_match_len = 0
        
        for clean_key in dictionary:
            if search_buffer.startswith(clean_key):
                key_len = len(clean_key)
                if (key_len == len(search_buffer)) or (search_buffer[key_len] == ' '):
                    if key_len > best_match_len:
                        best_match = clean_key
                        best_match_len = key_len
        
        if best_match:
            translated_chunks.append(dictionary[best_match])
            search_buffer = search_buffer[best_match_len:]
        else:
            split_text = search_buffer.split(' ', 1)
            unknown_word = split_text[0]
            if unknown_word:
                # [人名還原邏輯]
                # 如果字典裡沒有，但原始輸入是大寫 -> 強制還原為大寫人名 (例如 Jimmy, Taiwan)
                if unknown_word.title() in potential_names:
                    translated_chunks.append(unknown_word.title())
                elif unknown_word in fallback_vocab:
                    translated_chunks.append(fallback_vocab[unknown_word])
                else:
                    guess = None
                    if len(unknown_word) > 3:
                        guess = find_closest_match(unknown_word, all_vocab_keys)
                    
                    if guess:
                        translated_chunks.append(dictionary[guess])
                    else:
                        # 真的找不到字：再檢查一次是否為人名
                        if unknown_word.title() in potential_names:
                            translated_chunks.append(unknown_word.title())
                        else:
                            translated_chunks.append(unknown_word)
                            
            search_buffer = split_text[1] if len(split_text) > 1 else ""

    result = " ".join(translated_chunks)
    result = re.sub(r"\s+la\b", "-la", result)
    
    if len(result) > 0:
        result = result[0].upper() + result[1:]
    
    if ending_punct and not result.endswith(ending_punct):
        result += ending_punct
    
    return result

# --- 5. 統計 ---
def analyze_database_stats(databases):
    e2k = databases['e2k_data']
    k2e = databases['k2e_data']
    
    stats = {
        'total_words': 0, 'k2e_count': 0, 'e2k_count': 0, 
        'pos_distribution': {}, 'alpha_eng': {}, 'alpha_kwe': {}, 
        'example_coverage': {'With Examples': 0, 'Without Examples': 0}
    }
    
    if e2k.empty and k2e.empty: return stats
    
    stats['total_words'] = len(e2k) + len(k2e)
    stats['e2k_count'] = len(e2k); stats['k2e_count'] = len(k2e)
    
    if not k2e.empty and 'pos' in k2e.columns:
        stats['pos_distribution'] = k2e['pos'].apply(get_clean_pos).value_counts().to_dict()
    
    def get_alpha_clean(series):
        s = series.astype(str).str.strip()
        s = s[s != ""]
        s = s.str[0].str.upper()
        s = s.dropna()
        def safe_normalize(x):
            if not isinstance(x, str): return ""
            return unicodedata.normalize('NFD', x).encode('ascii', 'ignore').decode('utf-8')
        s = s.apply(safe_normalize)
        s = s[s.str.match(r'[A-Z]')]
        counts = s.value_counts()
        for char in string.ascii_uppercase:
            if char not in counts: counts[char] = 0
        return counts.sort_index().to_dict()

    if not e2k.empty and 'english' in e2k.columns:
        stats['alpha_eng'] = get_alpha_clean(e2k['english'])
        
    if not k2e.empty and 'Kweyol word' in k2e.columns:
        stats['alpha_kwe'] = get_alpha_clean(k2e['Kweyol word'])
        
    if not k2e.empty and 'Kweyol_Example' in k2e.columns:
        has_ex = k2e['Kweyol_Example'].astype(str).str.strip().astype(bool).sum()
        stats['example_coverage'] = {'With Examples': int(has_ex), 'Without Examples': int(len(k2e) - has_ex)}
        
    return stats

# --- 6. AI 模型 ---
@st.cache_resource
def load_translation_model():
    return None

def run_translation(translator, text, action):
    return "(AI Disabled)"