import streamlit as st
import chromadb
from openai import OpenAI
import json
import base64
import io
import os
import tempfile

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Museum Audio Guide",
    page_icon="🏛️",
    layout="centered",
)

# ── Iframe microphone permission fix (from v3_9) ──────────────
st.components.v1.html("""
    <script>
        const iframe = window.frameElement;
        if (iframe) {
            iframe.allow = "microphone";
        }
    </script>
""", height=0)

# ── Styles (from v3_9, preserved entirely) ────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=JetBrains+Mono:wght@300;400&display=swap');
html, body, [class*="css"] { font-family: 'Cormorant Garamond', Georgia, serif; }
.stApp { background: #f7f4ef; color: #2a1f14; }
.main-header {
    text-align: center; padding: 2rem 0 1rem 0;
    border-bottom: 1px solid #d4c8b8; margin-bottom: 2rem;
}
.main-header h1 {
    font-family: 'Cormorant Garamond', serif; font-weight: 300;
    font-size: 2rem; letter-spacing: 0.15em; color: #2a1f14; margin: 0;
}
.main-header p {
    font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
    letter-spacing: 0.2em; color: #9a8878; margin: 0.5rem 0 0 0; text-transform: uppercase;
}
.msg-guide {
    background: #ffffff; border-left: 3px solid #c4956a;
    border-radius: 0 8px 8px 0; padding: 1rem 1.2rem; margin: 0.8rem 0;
    font-size: 1.05rem; line-height: 1.75; color: #2a1f14;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.msg-visitor {
    background: #eef2e8; border-right: 3px solid #7a9a6a;
    border-radius: 8px 0 0 8px; padding: 0.8rem 1.2rem; margin: 0.8rem 0;
    font-size: 0.95rem; line-height: 1.6; color: #2a3a1a; text-align: right;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.label-guide {
    font-family: 'JetBrains Mono', monospace; font-size: 0.6rem;
    letter-spacing: 0.15em; color: #c4956a; text-transform: uppercase; margin-bottom: 0.3rem;
}
.label-visitor {
    font-family: 'JetBrains Mono', monospace; font-size: 0.6rem;
    letter-spacing: 0.15em; color: #7a9a6a; text-transform: uppercase;
    margin-bottom: 0.3rem; text-align: right;
}
.identify-badge {
    font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
    letter-spacing: 0.12em; color: #6a8a9a; background: #eef4f7;
    border: 1px solid #c8dce6; border-radius: 4px;
    padding: 0.3rem 0.7rem; display: inline-block; margin-bottom: 0.5rem;
}
.no-context-badge {
    font-family: 'JetBrains Mono', monospace; font-size: 0.6rem;
    color: #9a8878; background: #f5f0ea; border: 1px solid #d4c8b8;
    border-radius: 4px; padding: 0.2rem 0.6rem; display: inline-block; margin-bottom: 0.4rem;
}
section[data-testid="stSidebar"] { background: #f0ebe3; border-right: 1px solid #d4c8b8; }
.stButton > button {
    background: #f7f4ef; color: #c4956a; border: 1px solid #d4c8b8;
    font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
    letter-spacing: 0.1em; border-radius: 4px;
}
.stButton > button:hover { background: #fff; border-color: #c4956a; }
audio { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── API client ────────────────────────────────────────────────
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    st.error("API key not found. Go to Manage app → Settings → Secrets and add OPENAI_API_KEY.")
    st.stop()

client = OpenAI(api_key=api_key)

# ── Knowledge base (from desert exhibition, with persistent fix) ──
@st.cache_resource
def load_knowledge_base():
    """
    Load ChromaDB collection. Uses PersistentClient so embeddings are built
    only once — not rebuilt on every Streamlit rerun.
    """
    persist_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    chroma_client = chromadb.PersistentClient(path=persist_path)

    existing = [c.name for c in chroma_client.list_collections()]
    if "exhibition" in existing:
        return chroma_client.get_collection("exhibition")

    # First-time build
    collection = chroma_client.create_collection("exhibition")

    chunks = []
    for fname in ["desert_chunks_ch_001_054.jsonl", "desert_chunks_ch_055-100.jsonl"]:
        fpath = os.path.join(os.path.dirname(__file__), fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    chunks.append(json.loads(line))

    if not chunks:
        return collection  # empty but won't crash

    texts = [c["text"] for c in chunks]
    response = client.embeddings.create(input=texts, model="text-embedding-3-small")
    embeddings = [r.embedding for r in response.data]

    collection.add(
        ids=[c["chunk_id"] for c in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[{
            "chunk_id": c.get("chunk_id", ""),
            "domain": c.get("domain", ""),
            "exhibition_zone": c.get("exhibition_zone", ""),
            "subject": ", ".join(c.get("subject", [])) if isinstance(c.get("subject"), list) else "",
        } for c in chunks]
    )
    return collection

collection = load_knowledge_base()

# ── System prompts (multi-language, from desert exhibition) ───
SYSTEM_PROMPTS = {
    "zh": """你是一位博物馆讲解员，风格是"诗意的科学家"：
语言有温度和画面感，但所有细节必须来自提供的展览资料，不添加、不虚构。
如果资料中没有相关内容，坦诚说明并用通用知识补充，同时提醒观众。
回答长度控制在100-150字，适合朗读。结尾用一个具体问题引导观众观察眼前的细节。
用中文回答。""",

    "en": """You are a museum guide with the style of a poetic scientist.
Warm and vivid language, but every detail must come from the provided exhibit notes. Do not invent.
If the notes don't cover the question, say so honestly and supplement with general knowledge.
Keep responses to 100-150 words, suitable for reading aloud.
End with a specific question that directs the visitor's attention to a concrete detail in front of them.
Answer in English.""",

    "fr": """Tu es un guide de musée au style de scientifique poétique.
Langage chaleureux, mais chaque détail doit provenir des notes d'exposition. Ne pas inventer.
Si les notes ne couvrent pas la question, dis-le honnêtement et complète avec des connaissances générales.
Réponse de 100-150 mots, adaptée à la lecture à voix haute.
Termine par une question précise qui attire l'attention du visiteur sur un détail concret.
Réponds en français.""",
}

VOICES = {"zh": "nova", "en": "shimmer", "fr": "nova"}

LANG_MAP = {
    "chinese": "zh", "mandarin": "zh",
    "english": "en",
    "french": "fr", "français": "fr",
}

# ── Search (from desert exhibition) ──────────────────────────
def search(query: str, n: int = 5):
    embedding = client.embeddings.create(
        input=query, model="text-embedding-3-small"
    ).data[0].embedding
    results = collection.query(query_embeddings=[embedding], n_results=n)
    return results["documents"][0], results["metadatas"][0]

# ── Exhibit identification via GPT-4o (new, Plan C) ───────────
def identify_exhibit(image_b64: str) -> dict:
    """
    Given a base64 image, ask GPT-4o what exhibit is visible.
    Returns dict with keys: name, scientific_name, confidence, description
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                },
                {
                    "type": "text",
                    "text": (
                        "You are helping identify museum exhibits. "
                        "Look at this image and identify what is shown. "
                        "Respond ONLY with a JSON object, no markdown, no explanation:\n"
                        '{"name": "common name", "scientific_name": "latin name or empty string", '
                        '"confidence": "high|medium|low", '
                        '"description": "one sentence visual description"}'
                    )
                }
            ]
        }]
    )
    raw = response.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"name": "", "scientific_name": "", "confidence": "low", "description": raw}

# ── STT (from v3_9) ───────────────────────────────────────────
def stt(audio_bytes: bytes) -> tuple[str, str]:
    """Returns (transcript_text, detected_language)"""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        path = f.name
    try:
        with open(path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json"  # gives us language detection
            )
        lang = LANG_MAP.get(result.language, "en")
        return result.text.strip(), lang
    finally:
        os.unlink(path)

# ── TTS (from v3_9) ───────────────────────────────────────────
def tts(text: str, lang: str, voice_override: str | None = None) -> bytes:
    voice = voice_override or VOICES.get(lang, "nova")
    return client.audio.speech.create(
        model="tts-1", voice=voice, input=text, response_format="mp3"
    ).content

# ── Autoplay audio (from v3_9) ────────────────────────────────
def autoplay_audio(audio_bytes: bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    st.components.v1.html(
        f"""
        <script>
        if (window.top._guideAudio) {{
            window.top._guideAudio.pause();
            window.top._guideAudio.currentTime = 0;
        }}
        window.top._guideAudio = new Audio('data:audio/mp3;base64,{b64}');
        window.top._guideAudio.play();
        window.top._guideAudioPaused = false;
        var btn = window.top.document.getElementById('audioToggleBtn');
        if (btn) btn.innerText = '⏸ Pause';
        </script>
        """,
        height=0,
    )

# ── Streaming answer with RAG context (merged) ───────────────
def stream_answer(question: str, lang: str, exhibit_info: dict | None = None) -> tuple[str, bool, list, list]:
    """
    Retrieve context, stream answer.
    Returns (full_text, context_was_found, docs, metas).
    """
    # Build search query: exhibit name + question
    query_parts = []
    if exhibit_info and exhibit_info.get("name"):
        query_parts.append(exhibit_info["name"])
    if exhibit_info and exhibit_info.get("scientific_name"):
        query_parts.append(exhibit_info["scientific_name"])
    query_parts.append(question)
    query = " ".join(query_parts)

    docs, metas = search(query)
    context_found = bool(docs and any(d.strip() for d in docs))
    context = "\n\n".join([f"[{i+1}] {d}" for i, d in enumerate(docs)]) if context_found else ""

    # Build messages
    system = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS["en"])
    user_content = ""
    if exhibit_info and exhibit_info.get("name"):
        user_content += f"Exhibit identified: {exhibit_info['name']}"
        if exhibit_info.get("scientific_name"):
            user_content += f" ({exhibit_info['scientific_name']})"
        user_content += "\n\n"
    if context_found:
        user_content += f"Exhibit notes:\n{context}\n\n"
    else:
        user_content += "[No specific exhibit notes found — use general knowledge and note this.]\n\n"
    user_content += f"Visitor question: {question}"

    messages = [{"role": "system", "content": system}]

    # Add conversation history (from v3_9)
    for turn in st.session_state.history[-10:]:  # last 5 exchanges
        messages.append({"role": "user", "content": turn["question"]})
        messages.append({"role": "assistant", "content": turn["answer"]})

    messages.append({"role": "user", "content": user_content})

    # Stream
    full_text = ""
    placeholder = st.empty()

    stream = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=400,
        temperature=0.75,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        full_text += delta
        placeholder.markdown(
            f'<div class="msg-guide">{full_text}<span style="opacity:0.3">▌</span></div>',
            unsafe_allow_html=True
        )
    placeholder.markdown(
        f'<div class="msg-guide">{full_text}</div>',
        unsafe_allow_html=True
    )
    return full_text, context_found, docs, metas

# ── Session state ────────────────────────────────────────────
for k, v in [
    ("history", []),
    ("display", []),
    ("pending_image", None),
    ("pending_image_b64", None),
    ("camera_open", False),
    ("specimen_name", ""),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sidebar (from v3_9) ───────────────────────────────────────
with st.sidebar:
    st.markdown('<p style="font-family:JetBrains Mono,monospace;font-size:0.65rem;letter-spacing:0.15em;color:#9a8878;text-transform:uppercase;">Configuration</p>', unsafe_allow_html=True)
    voice_override = st.selectbox(
        "Voice override",
        ["auto", "nova", "shimmer", "alloy", "ash", "coral", "echo", "fable", "onyx", "sage"],
        index=0
    )
    st.caption("'auto' selects voice by detected language.")
    st.divider()
    if st.button("↺  New Visitor"):
        st.session_state.history = []
        st.session_state.display = []
        st.session_state.pending_image = None
        st.session_state.pending_image_b64 = None
        st.session_state.specimen_name = ""
        st.rerun()
    st.divider()
    st.markdown('<p style="font-family:JetBrains Mono,monospace;font-size:0.65rem;letter-spacing:0.15em;color:#9a8878;text-transform:uppercase;">Version log</p>', unsafe_allow_html=True)
    VERSIONS = [
        {
            "version": "v4.0",
            "date": "2026-03-26",
            "changes": [
                "🔍 Plan B: ChromaDB RAG — knowledge retrieved per question",
                "📷 Plan C: GPT-4o exhibit identification from photo",
                "🌐 Whisper language auto-detection (zh/en/fr)",
                "💾 PersistentClient — embeddings built once, not per rerun",
                "💬 Conversation history preserved across turns",
                "🎙 Iframe microphone permission fix retained",
                "⏸ Pause/Resume audio retained",
                "🎨 Full v3.9 visual design retained",
            ],
        },
        {
            "version": "v3.9",
            "date": "2026-03-24",
            "changes": [
                "✨ Streamlined UX: single spinner, streaming text, silent audio",
                "⏸ Stop/resume audio — pure JS toggle",
                "📷 Camera on-demand",
                "🔄 gpt-4o / gpt-4o-mini routing",
            ],
        },
    ]
    for v in VERSIONS:
        is_latest = v == VERSIONS[0]
        label = f"{'● ' if is_latest else '○ '}{v['version']}  ·  {v['date']}"
        st.markdown(
            f'<p style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
            f'color:{"#c4956a" if is_latest else "#9a8878"};margin:0.6rem 0 0.2rem 0;">'
            f'{label}</p>', unsafe_allow_html=True
        )
        for change in v["changes"]:
            st.markdown(
                f'<p style="font-size:0.78rem;color:#6a5a4a;margin:0.1rem 0 0 0.5rem;line-height:1.5;">'
                f'{change}</p>', unsafe_allow_html=True
            )

# ── Header ────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🏛 Museum Audio Guide</h1>
    <p>Speak · Photograph · Discover</p>
</div>
""", unsafe_allow_html=True)

# ── Input area ────────────────────────────────────────────────
st.divider()

# Step 1 label
st.markdown(
    '<p style="font-family:JetBrains Mono,monospace;font-size:0.6rem;'
    'letter-spacing:0.15em;color:#9a8878;text-transform:uppercase;margin-bottom:0.4rem;">'
    'Step 1 &nbsp;·&nbsp; Identify exhibit <span style="font-weight:300;color:#c4b8a8;">(optional)</span></p>',
    unsafe_allow_html=True
)

# Step 1 row: scientific name | divider | camera — equal weight, side by side
col_name, col_or, col_cam = st.columns([5, 1, 5])

with col_name:
    specimen_input = st.text_input(
        "🔬 Scientific name",
        value=st.session_state.specimen_name,
        placeholder="e.g. Panthera leo",
        label_visibility="collapsed",
    )
    if specimen_input != st.session_state.specimen_name:
        st.session_state.specimen_name = specimen_input
    # Inline status — no separate row
    if st.session_state.specimen_name:
        col_locked, col_clr = st.columns([3, 1])
        with col_locked:
            st.caption(f"🔬 _{st.session_state.specimen_name}_")
        with col_clr:
            if st.button("✕", key="clear_name", help="Clear scientific name"):
                st.session_state.specimen_name = ""
                st.rerun()

with col_or:
    st.markdown(
        '<div style="text-align:center;padding-top:0.5rem;'
        'font-family:JetBrains Mono,monospace;font-size:0.65rem;'
        'color:#c4b8a8;letter-spacing:0.1em;">or</div>',
        unsafe_allow_html=True
    )

with col_cam:
    if st.session_state.pending_image:
        col_ready, col_clr2 = st.columns([3, 1])
        with col_ready:
            st.caption("📷 _Photo ready_")
        with col_clr2:
            if st.button("✕", key="clear_photo", help="Clear photo"):
                st.session_state.pending_image = None
                st.session_state.pending_image_b64 = None
                st.rerun()
    else:
        if not st.session_state.camera_open:
            if st.button("📷 Photograph exhibit", use_container_width=True):
                st.session_state.camera_open = True
                st.rerun()
        else:
            camera_shot = st.camera_input("Point at the exhibit")
            if camera_shot:
                raw = camera_shot.getvalue()
                st.session_state.pending_image = raw
                st.session_state.pending_image_b64 = base64.b64encode(raw).decode()
                st.session_state.camera_open = False
                st.rerun()
            if st.button("✕ Cancel"):
                st.session_state.camera_open = False
                st.rerun()

st.markdown("<div style='margin-top:1.2rem;'></div>", unsafe_allow_html=True)

# Step 2 label
st.markdown(
    '<p style="font-family:JetBrains Mono,monospace;font-size:0.6rem;'
    'letter-spacing:0.15em;color:#9a8878;text-transform:uppercase;margin-bottom:0.4rem;">'
    'Step 2 &nbsp;·&nbsp; Ask your question</p>',
    unsafe_allow_html=True
)

# Step 2: full-width mic
audio_input = st.audio_input("🎙 Record your question", label_visibility="collapsed")

# Pause / Resume — tucked directly under mic
st.components.v1.html("""
<button id="audioToggleBtn"
    onclick="
        var a = window.top._guideAudio;
        if (!a) return;
        if (a.paused) { a.play(); this.innerText = '⏸ Pause'; }
        else { a.pause(); this.innerText = '▶ Resume'; }
    "
    style="background:#f7f4ef;color:#c4956a;border:1px solid #d4c8b8;
           font-family:'JetBrains Mono',monospace;font-size:0.7rem;
           letter-spacing:0.1em;border-radius:4px;padding:0.35rem 0.75rem;
           cursor:pointer;margin-top:0.3rem;">⏸ Pause</button>
""", height=36)

# ── Main interaction loop ─────────────────────────────────────
if audio_input:
    image_b64 = st.session_state.pending_image_b64

    with st.spinner("Listening..."):
        user_text, lang = stt(audio_input.getvalue())

    if user_text:
        # Step 1: identify exhibit — photo takes priority, specimen_name is fallback
        exhibit_info = None
        if image_b64:
            with st.spinner("Identifying exhibit..."):
                exhibit_info = identify_exhibit(image_b64)

            if exhibit_info and exhibit_info.get("confidence") in ("high", "medium"):
                name_display = exhibit_info["name"]
                if exhibit_info.get("scientific_name"):
                    name_display += f" · {exhibit_info['scientific_name']}"
                st.markdown(
                    f'<div class="identify-badge">📷 {name_display}</div>',
                    unsafe_allow_html=True
                )

        # If no photo (or low-confidence identification), fall back to manual specimen name
        if not exhibit_info or exhibit_info.get("confidence") == "low":
            if st.session_state.specimen_name:
                exhibit_info = {
                    "name": st.session_state.specimen_name,
                    "scientific_name": st.session_state.specimen_name,
                    "confidence": "manual",
                    "description": "",
                }
                st.markdown(
                    f'<div class="identify-badge">🔬 {st.session_state.specimen_name}</div>',
                    unsafe_allow_html=True
                )

        # Step 2: build display label
        display_question = user_text
        if exhibit_info and exhibit_info.get("name"):
            display_question = f"[{exhibit_info['name']}] {user_text}"

        st.markdown('<div class="label-visitor">Visitor</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="msg-visitor">{display_question}</div>', unsafe_allow_html=True)

        # Step 3: retrieve + stream answer
        st.markdown('<div class="label-guide">Guide</div>', unsafe_allow_html=True)
        with st.spinner("Thinking..."):
            reply, context_found, docs, metas = stream_answer(user_text, lang, exhibit_info)

        if not context_found:
            st.markdown(
                '<div class="no-context-badge">ℹ️ No exhibit notes found — answered from general knowledge</div>',
                unsafe_allow_html=True
            )

        # DEV ONLY — set expanded=False before going live,
        # or remove this block entirely for production.
        with st.expander("🔍 Retrieved chunks (debug)", expanded=True):
            if not docs:
                st.caption("No chunks retrieved.")
            for i, (doc, meta) in enumerate(zip(docs, metas)):
                st.markdown(
                    f"**Chunk {i+1}**"
                    f"&nbsp;·&nbsp; zone: `{meta.get('exhibition_zone', '—')}`"
                    f"&nbsp;·&nbsp; domain: `{meta.get('domain', '—')}`"
                    f"&nbsp;·&nbsp; subject: `{meta.get('subject', '—')}`"
                )
                st.caption(doc)
                if i < len(docs) - 1:
                    st.divider()

        # Step 4: TTS
        voice_sel = None if voice_override == "auto" else voice_override
        audio_bytes = tts(reply, lang, voice_override=voice_sel)
        autoplay_audio(audio_bytes)

        # Step 5: update state
        st.session_state.pending_image = None
        st.session_state.pending_image_b64 = None

        st.session_state.history.append({
            "question": display_question,
            "answer": reply,
            "lang": lang,
        })
        st.session_state.display.append({"role": "visitor", "content": display_question})
        st.session_state.display.append({"role": "guide", "content": reply})

        # Keep history bounded
        if len(st.session_state.history) > 20:
            st.session_state.history = st.session_state.history[-20:]

# ── Conversation history (newest first, from v3_9) ────────────
st.divider()
pairs = []
items = st.session_state.display
i = 0
while i < len(items) - 1:
    if items[i]["role"] == "visitor" and items[i+1]["role"] == "guide":
        pairs.append((items[i], items[i+1]))
        i += 2
    else:
        i += 1

for visitor_msg, guide_msg in reversed(pairs):
    st.markdown(
        f'<div class="label-visitor">Visitor</div>'
        f'<div class="msg-visitor">{visitor_msg["content"]}</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<div class="label-guide">Guide</div>'
        f'<div class="msg-guide">{guide_msg["content"]}</div>',
        unsafe_allow_html=True
    )
