import random
import html
import datetime
import pandas as pd
import streamlit as st

# 聖露西亞熱帶島嶼風 SVG 橫幅（Pitons 雙子峰 + 太陽 + 棕櫚剪影）
ARCADE_BANNER_SVG = """
<div style="background: linear-gradient(135deg, #1f5c6b 0%, #2f6f7e 55%, #488b99 100%);
            border-radius: 14px; padding: 20px 26px; margin-bottom: 18px;
            box-shadow: 0 6px 18px rgba(31, 92, 107, 0.18);
            display: flex; align-items: center; justify-content: space-between;
            position: relative; overflow: hidden;">
    <div style="z-index: 2; max-width: 72%;">
        <div style="display: inline-block; background: rgba(244, 180, 0, 0.22);
                    border: 1px solid rgba(244, 180, 0, 0.55); color: #ffe082;
                    font-size: 0.72rem; font-weight: 700; letter-spacing: 1.5px;
                    padding: 3px 10px; border-radius: 999px; text-transform: uppercase;
                    margin-bottom: 8px;">
            Interactive Practice
        </div>
        <div style="margin: 0 0 6px 0; color: #ffffff; font-size: 1.75rem; font-weight: 800; line-height: 1.2;">
            Kwéyòl Island Arcade
        </div>
        <div style="margin: 0; color: #e0f2f1; font-size: 0.96rem; line-height: 1.45;">
            Train your vocabulary, listening ear, and sentence structure with bite-sized Saint Lucian Kwéyòl challenges.
        </div>
    </div>
    <div style="z-index: 2; flex-shrink: 0;">
        <svg width="130" height="96" viewBox="0 0 130 96" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="96" cy="24" r="14" fill="#FCD116" opacity="0.95"/>
            <circle cx="96" cy="24" r="20" fill="#FCD116" opacity="0.22"/>
            <!-- Pitons Peaks -->
            <path d="M12 86 L42 28 L66 86 Z" fill="#16424d"/>
            <path d="M42 28 L52 48 L43 44 L36 52 Z" fill="#235b69"/>
            <path d="M48 86 L76 38 L106 86 Z" fill="#1d525f"/>
            <path d="M76 38 L86 55 L77 51 L70 57 Z" fill="#2c7080"/>
            <!-- Sea wave -->
            <path d="M6 86 Q 35 80, 65 86 T 124 86" stroke="#80cbc4" stroke-width="3" stroke-linecap="round" fill="none"/>
            <path d="M18 92 Q 45 87, 72 92 T 118 92" stroke="#b2dfdb" stroke-width="2" stroke-linecap="round" fill="none" opacity="0.7"/>
        </svg>
    </div>
</div>
"""

TOPIC_LABELS = {
    "All Topics": "🌴 All Topics",
    "Food": "🍍 Food & Fruits",
    "Body": "👋 Body Parts",
    "Home": "🏠 Around the Home",
    "Family": "👨‍👩‍👧‍👦 Family",
    "Time": "⏰ Days & Time",
    "Occupation": "👷 Occupations",
}


def _clean_kweyol_choice(raw: str) -> str:
    """Take the primary Kwéyòl term and strip trailing punctuation."""
    text = str(raw).split(",")[0].strip().rstrip(".")
    return text


def _init_game_state():
    defaults = {
        "game_score": 0,
        "game_streak": 0,
        "game_best_streak": 0,
        "game_answered": 0,
        "game_correct": 0,
        "game_mode": "🥥 Island Quiz",
        "quiz_topic": "All Topics",
        "quiz_direction": "English → Kwéyòl",
        "quiz_q": None,
        "quiz_feedback": None,
        "audio_q": None,
        "audio_bytes": None,
        "audio_feedback": None,
        "audio_play_ts": None,
        "sb_q": None,
        "sb_picked": [],
        "sb_feedback": None,
        "sb_play_bytes": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _build_quiz_question(databases, topic: str, direction: str):
    df = databases.get("e2k_data", pd.DataFrame())
    if df.empty:
        return None

    pool = df[(df["english"].astype(str).str.strip() != "") & (df["Kweyol"].astype(str).str.strip() != "")].copy()
    if topic != "All Topics":
        themed = pool[pool["pos"] == topic]
        if len(themed) >= 4:
            pool = themed

    if len(pool) < 4:
        return None

    target_row = pool.sample(n=1).iloc[0]
    eng = str(target_row["english"]).strip()
    kwe = _clean_kweyol_choice(target_row["Kweyol"])
    pos = str(target_row.get("pos", "")).strip() or "General"

    distractor_pool = pool[pool["english"].astype(str).str.strip() != eng]
    if len(distractor_pool) < 3:
        distractor_pool = df[df["english"].astype(str).str.strip() != eng]

    distractors = distractor_pool.sample(n=min(10, len(distractor_pool)))

    if direction == "English → Kwéyòl":
        prompt_word = eng
        answer = kwe
        options = [answer]
        for _, r in distractors.iterrows():
            cand = _clean_kweyol_choice(r["Kweyol"])
            if cand and cand.lower() not in [o.lower() for o in options]:
                options.append(cand)
            if len(options) == 4:
                break
    else:
        prompt_word = kwe
        answer = eng
        options = [answer]
        for _, r in distractors.iterrows():
            cand = str(r["english"]).strip()
            if cand and cand.lower() not in [o.lower() for o in options]:
                options.append(cand)
            if len(options) == 4:
                break

    if len(options) < 4:
        return None

    random.shuffle(options)
    return {
        "prompt": prompt_word,
        "answer": answer,
        "kweyol": kwe,
        "english": eng,
        "pos": pos,
        "options": options,
        "direction": direction,
    }


def _build_audio_question(databases, topic: str):
    q = _build_quiz_question(databases, topic, "English → Kwéyòl")
    if not q:
        return None
    # Audio Match tests listening to Kwéyòl and picking the English meaning
    df = databases.get("e2k_data", pd.DataFrame())
    pool = df[(df["english"].astype(str).str.strip() != "") & (df["Kweyol"].astype(str).str.strip() != "")]
    if topic != "All Topics" and len(pool[pool["pos"] == topic]) >= 4:
        pool = pool[pool["pos"] == topic]

    distractors = pool[pool["english"].astype(str).str.strip() != q["english"]].sample(n=min(10, len(pool) - 1))
    eng_options = [q["english"]]
    for _, r in distractors.iterrows():
        cand = str(r["english"]).strip()
        if cand and cand.lower() not in [o.lower() for o in eng_options]:
            eng_options.append(cand)
        if len(eng_options) == 4:
            break
    if len(eng_options) < 4:
        return None
    random.shuffle(eng_options)
    q["eng_options"] = eng_options
    return q


def _build_sentence_question(databases):
    df = databases.get("k2e_data", pd.DataFrame())
    if df.empty:
        return None
    candidates = df[
        (df["Kweyol_Example"].astype(str).str.strip() != "")
        & (df["English_Example"].astype(str).str.strip() != "")
    ].copy()
    if candidates.empty:
        return None

    # Filter sentences with 3 to 6 words for fun, manageable puzzles
    candidates["word_count"] = candidates["Kweyol_Example"].astype(str).apply(lambda s: len(s.strip().split()))
    short_sents = candidates[(candidates["word_count"] >= 3) & (candidates["word_count"] <= 6)]
    if short_sents.empty:
        short_sents = candidates

    row = short_sents.sample(n=1).iloc[0]
    kwe_sent = str(row["Kweyol_Example"]).strip()
    eng_sent = str(row["English_Example"]).strip()
    tokens = kwe_sent.split()
    shuffled = [(idx, tok) for idx, tok in enumerate(tokens)]
    random.shuffle(shuffled)
    # Ensure it's actually shuffled when possible
    if len(tokens) > 1 and [t for _, t in shuffled] == tokens:
        shuffled.reverse()

    return {
        "kweyol_sentence": kwe_sent,
        "english_sentence": eng_sent,
        "tokens": tokens,
        "shuffled": shuffled,
    }


def _record_result(is_correct: bool, points: int = 10):
    st.session_state["game_answered"] += 1
    if is_correct:
        st.session_state["game_correct"] += 1
        st.session_state["game_streak"] += 1
        bonus = min(st.session_state["game_streak"] - 1, 5) * 2
        st.session_state["game_score"] += points + bonus
        if st.session_state["game_streak"] > st.session_state["game_best_streak"]:
            st.session_state["game_best_streak"] = st.session_state["game_streak"]
    else:
        st.session_state["game_streak"] = 0


def _play_hidden_wav(audio_bytes: bytes):
    """Trigger native hidden autoplay audio (player bar hidden by global CSS)."""
    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav", autoplay=True)


def _render_hud():
    score = st.session_state["game_score"]
    streak = st.session_state["game_streak"]
    best = st.session_state["game_best_streak"]
    answered = st.session_state["game_answered"]
    correct = st.session_state["game_correct"]
    acc = f"{round((correct / answered) * 100)}%" if answered > 0 else "—"

    st.markdown(
        f"""
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 18px;">
            <div style="background:#fff; border:1px solid #e8e0d5; border-radius:10px; padding:12px; text-align:center; box-shadow:0 2px 6px rgba(0,0,0,0.03);">
                <div style="font-size:0.75rem; color:#888; font-weight:700; letter-spacing:1px; text-transform:uppercase;">Score</div>
                <div style="font-size:1.55rem; font-weight:800; color:#2f6f7e;">{score}</div>
            </div>
            <div style="background:#fff; border:1px solid #e8e0d5; border-radius:10px; padding:12px; text-align:center; box-shadow:0 2px 6px rgba(0,0,0,0.03);">
                <div style="font-size:0.75rem; color:#888; font-weight:700; letter-spacing:1px; text-transform:uppercase;">Streak</div>
                <div style="font-size:1.55rem; font-weight:800; color:#e67e22;">🔥 {streak}</div>
            </div>
            <div style="background:#fff; border:1px solid #e8e0d5; border-radius:10px; padding:12px; text-align:center; box-shadow:0 2px 6px rgba(0,0,0,0.03);">
                <div style="font-size:0.75rem; color:#888; font-weight:700; letter-spacing:1px; text-transform:uppercase;">Accuracy</div>
                <div style="font-size:1.55rem; font-weight:800; color:#2e7d32;">{acc}</div>
            </div>
            <div style="background:#fff; border:1px solid #e8e0d5; border-radius:10px; padding:12px; text-align:center; box-shadow:0 2px 6px rgba(0,0,0,0.03);">
                <div style="font-size:0.75rem; color:#888; font-weight:700; letter-spacing:1px; text-transform:uppercase;">Best Streak</div>
                <div style="font-size:1.55rem; font-weight:800; color:#8d6e63;">🏆 {best}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_island_quiz(databases, generate_kweyol_audio):
    c_topic, c_dir = st.columns([1.2, 1])
    with c_topic:
        selected_topic = st.selectbox(
            "Topic Pack",
            options=list(TOPIC_LABELS.keys()),
            format_func=lambda k: TOPIC_LABELS[k],
            key="quiz_topic_select",
        )
    with c_dir:
        selected_dir = st.radio(
            "Challenge Direction",
            ["English → Kwéyòl", "Kwéyòl → English"],
            horizontal=True,
            key="quiz_dir_radio",
        )

    if (
        st.session_state["quiz_q"] is None
        or selected_topic != st.session_state["quiz_topic"]
        or selected_dir != st.session_state["quiz_direction"]
    ):
        st.session_state["quiz_topic"] = selected_topic
        st.session_state["quiz_direction"] = selected_dir
        st.session_state["quiz_q"] = _build_quiz_question(databases, selected_topic, selected_dir)
        st.session_state["quiz_feedback"] = None

    q = st.session_state["quiz_q"]
    if not q:
        st.info("Not enough entries in this topic to build a question.")
        return

    badge_text = TOPIC_LABELS.get(q["pos"], q["pos"])
    prompt_label = "Translate to Kwéyòl" if q["direction"] == "English → Kwéyòl" else "What does this Kwéyòl word mean?"

    st.markdown(
        f"""
        <div style="background:#fff; border:1px solid #e8e0d5; border-left:6px solid #2f6f7e;
                    border-radius:12px; padding:24px 28px; margin:14px 0 18px 0;
                    box-shadow:0 4px 12px rgba(0,0,0,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span style="font-size:0.78rem; font-weight:700; color:#607080; text-transform:uppercase; letter-spacing:1.2px;">
                    {prompt_label}
                </span>
                <span style="background:#e7f3f5; color:#2f6f7e; font-size:0.78rem; font-weight:700;
                             padding:3px 10px; border-radius:999px; border:1px solid #c7e1e6;">
                    {html.escape(badge_text)}
                </span>
            </div>
            <div style="font-size:2.1rem; font-weight:800; color:#5d4037; line-height:1.2;">
                {html.escape(q["prompt"])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    fb = st.session_state["quiz_feedback"]
    is_locked = fb is not None

    col_a, col_b = st.columns(2)
    for idx, opt in enumerate(q["options"]):
        target_col = col_a if idx % 2 == 0 else col_b
        with target_col:
            if st.button(opt, key=f"quiz_opt_{idx}_{q['prompt']}", disabled=is_locked, use_container_width=True):
                correct = opt == q["answer"]
                _record_result(correct, points=10)
                st.session_state["quiz_feedback"] = {
                    "correct": correct,
                    "picked": opt,
                    "answer": q["answer"],
                    "kweyol": q["kweyol"],
                }
                st.rerun()

    if fb:
        if fb["correct"]:
            st.success(f"🎉 Correct! **{q['english']}** = **{q['kweyol']}**")
        else:
            st.error(f"Not quite! You picked **{fb['picked']}**, but the answer is **{fb['answer']}**.")

        act_col1, act_col2 = st.columns([1, 1])
        with act_col1:
            if st.button("🔊 Hear Kwéyòl", key="quiz_hear_btn", use_container_width=True):
                with st.spinner("Generating Kwéyòl audio..."):
                    audio_bytes = generate_kweyol_audio(q["kweyol"])
                if audio_bytes:
                    st.session_state["_quiz_last_audio"] = (audio_bytes, datetime.datetime.now().timestamp())
        with act_col2:
            if st.button("Next Question ➡️", type="primary", key="quiz_next_btn", use_container_width=True):
                st.session_state["quiz_q"] = _build_quiz_question(databases, selected_topic, selected_dir)
                st.session_state["quiz_feedback"] = None
                st.session_state.pop("_quiz_last_audio", None)
                st.rerun()

        if "_quiz_last_audio" in st.session_state:
            _play_hidden_wav(st.session_state["_quiz_last_audio"][0])


def _render_audio_match(databases, generate_kweyol_audio):
    selected_topic = st.selectbox(
        "Topic Pack",
        options=list(TOPIC_LABELS.keys()),
        format_func=lambda k: TOPIC_LABELS[k],
        key="audio_topic_select",
    )

    if st.session_state["audio_q"] is None or st.session_state.get("_audio_topic_prev") != selected_topic:
        st.session_state["_audio_topic_prev"] = selected_topic
        st.session_state["audio_q"] = _build_audio_question(databases, selected_topic)
        st.session_state["audio_bytes"] = None
        st.session_state["audio_feedback"] = None
        st.session_state["audio_play_ts"] = None

    q = st.session_state["audio_q"]
    if not q:
        st.info("Not enough entries to start Audio Match.")
        return

    st.markdown(
        """
        <div style="background:#fff; border:1px solid #e8e0d5; border-left:6px solid #f4b400;
                    border-radius:12px; padding:22px 26px; margin:14px 0 16px 0;
                    box-shadow:0 4px 12px rgba(0,0,0,0.05); text-align:center;">
            <div style="font-size:0.8rem; font-weight:700; color:#888; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px;">
                Listening Comprehension
            </div>
            <div style="font-size:1.25rem; font-weight:700; color:#2c2c2c;">
                Tap the button below to hear a Kwéyòl word, then pick its English meaning!
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🔊 Play Kwéyòl Sound", type="primary", key="audio_match_play", use_container_width=True):
        if st.session_state["audio_bytes"] is None:
            with st.spinner("Synthesizing Kwéyòl voice..."):
                st.session_state["audio_bytes"] = generate_kweyol_audio(q["kweyol"])
        if st.session_state["audio_bytes"]:
            st.session_state["audio_play_ts"] = datetime.datetime.now().timestamp()
        else:
            st.warning("⚠️ Audio synthesis is currently unavailable.")

    if st.session_state.get("audio_bytes") and st.session_state.get("audio_play_ts"):
        _play_hidden_wav(st.session_state["audio_bytes"])

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    fb = st.session_state["audio_feedback"]
    is_locked = fb is not None

    col_a, col_b = st.columns(2)
    for idx, opt in enumerate(q["eng_options"]):
        target_col = col_a if idx % 2 == 0 else col_b
        with target_col:
            if st.button(opt, key=f"aud_opt_{idx}_{q['kweyol']}", disabled=is_locked, use_container_width=True):
                correct = opt == q["english"]
                _record_result(correct, points=15)
                st.session_state["audio_feedback"] = {
                    "correct": correct,
                    "picked": opt,
                }
                st.rerun()

    if fb:
        if fb["correct"]:
            st.success(f"🎧 Spot on! You heard **{q['kweyol']}** — meaning **{q['english']}**.")
        else:
            st.error(f"Good try! The word was **{q['kweyol']}**, which means **{q['english']}**.")

        if st.button("Next Sound ➡️", type="primary", key="audio_next_btn", use_container_width=True):
            st.session_state["audio_q"] = _build_audio_question(databases, selected_topic)
            st.session_state["audio_bytes"] = None
            st.session_state["audio_feedback"] = None
            st.session_state["audio_play_ts"] = None
            st.rerun()


def _render_sentence_builder(databases, generate_kweyol_audio):
    if st.session_state["sb_q"] is None:
        st.session_state["sb_q"] = _build_sentence_question(databases)
        st.session_state["sb_picked"] = []
        st.session_state["sb_feedback"] = None
        st.session_state["sb_play_bytes"] = None

    q = st.session_state["sb_q"]
    if not q:
        st.info("No example sentences available for Sentence Builder.")
        return

    st.markdown(
        f"""
        <div style="background:#fff; border:1px solid #e8e0d5; border-left:6px solid #2e7d32;
                    border-radius:12px; padding:22px 26px; margin:14px 0 16px 0;
                    box-shadow:0 4px 12px rgba(0,0,0,0.05);">
            <div style="font-size:0.78rem; font-weight:700; color:#2e7d32; text-transform:uppercase; letter-spacing:1.2px; margin-bottom:8px;">
                Build this sentence in Kwéyòl
            </div>
            <div style="font-size:1.35rem; font-weight:700; color:#2c2c2c;">
                “{html.escape(q['english_sentence'])}”
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    picked_indices = st.session_state["sb_picked"]
    token_map = dict(q["shuffled"])
    built_words = [token_map[i] for i in picked_indices]
    built_preview = " ".join(built_words) if built_words else "Tap word tiles below in the right order..."
    preview_color = "#5d4037" if built_words else "#aaa"

    st.markdown(
        f"""
        <div style="background:#fcfbf9; border:2px dashed #bcaaa4; border-radius:10px;
                    padding:16px 20px; min-height:60px; margin-bottom:14px;
                    font-size:1.25rem; font-weight:700; color:{preview_color};">
            {html.escape(built_preview)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    fb = st.session_state["sb_feedback"]
    is_locked = fb is not None

    # Word tiles
    cols = st.columns(min(len(q["shuffled"]), 6))
    for i, (orig_idx, tok) in enumerate(q["shuffled"]):
        with cols[i % len(cols)]:
            already_used = orig_idx in picked_indices
            if st.button(
                tok,
                key=f"sb_tile_{orig_idx}_{q['kweyol_sentence']}",
                disabled=already_used or is_locked,
                use_container_width=True,
            ):
                st.session_state["sb_picked"].append(orig_idx)
                st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 1.4])
    with c1:
        if st.button("↩️ Undo", key="sb_undo", disabled=is_locked or not picked_indices, use_container_width=True):
            st.session_state["sb_picked"].pop()
            st.rerun()
    with c2:
        if st.button("🗑️ Clear", key="sb_clear", disabled=is_locked or not picked_indices, use_container_width=True):
            st.session_state["sb_picked"] = []
            st.rerun()
    with c3:
        ready = len(built_words) == len(q["tokens"]) and not is_locked
        if st.button("✅ Check Answer", type="primary", key="sb_check", disabled=not ready, use_container_width=True):
            user_str = " ".join(built_words)
            correct = user_str == q["kweyol_sentence"]
            _record_result(correct, points=20)
            st.session_state["sb_feedback"] = {
                "correct": correct,
                "user": user_str,
            }
            st.rerun()

    if fb:
        if fb["correct"]:
            st.success(f"🧩 Nailed it! **{q['kweyol_sentence']}**")
        else:
            st.error(f"Almost! Correct order: **{q['kweyol_sentence']}**")

        b1, b2 = st.columns(2)
        with b1:
            if st.button("🔊 Hear Sentence", key="sb_hear", use_container_width=True):
                with st.spinner("Generating sentence audio..."):
                    audio_bytes = generate_kweyol_audio(q["kweyol_sentence"])
                if audio_bytes:
                    st.session_state["sb_play_bytes"] = (audio_bytes, datetime.datetime.now().timestamp())
        with b2:
            if st.button("Next Sentence ➡️", type="primary", key="sb_next", use_container_width=True):
                st.session_state["sb_q"] = _build_sentence_question(databases)
                st.session_state["sb_picked"] = []
                st.session_state["sb_feedback"] = None
                st.session_state["sb_play_bytes"] = None
                st.rerun()

        if st.session_state.get("sb_play_bytes"):
            _play_hidden_wav(st.session_state["sb_play_bytes"][0])


def render_game_tab(databases, generate_kweyol_audio):
    """Render the Kwéyòl Island Arcade tab."""
    _init_game_state()
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown(ARCADE_BANNER_SVG, unsafe_allow_html=True)
    _render_hud()

    mode = st.radio(
        "Choose Game Mode",
        ["🥥 Island Quiz", "🎧 Audio Match", "🧩 Sentence Builder"],
        horizontal=True,
        key="arcade_mode_radio",
    )

    st.markdown("<hr style='margin: 10px 0 16px 0; border-color: #e8e0d5;'>", unsafe_allow_html=True)

    if mode == "🥥 Island Quiz":
        _render_island_quiz(databases, generate_kweyol_audio)
    elif mode == "🎧 Audio Match":
        _render_audio_match(databases, generate_kweyol_audio)
    else:
        _render_sentence_builder(databases, generate_kweyol_audio)
