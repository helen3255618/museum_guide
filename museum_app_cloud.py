# ============================================================
# Museum Audio Guide — Streamlit with true streaming TTS
# ============================================================
# pip install streamlit openai
# streamlit run museum_app.py

import streamlit as st
import openai
import tempfile
import os
import time
import re
import base64

# ── Page config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Museum Audio Guide",
    page_icon="🏛️",
    layout="centered",
)

# ── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=JetBrains+Mono:wght@300;400&display=swap');

html, body, [class*="css"] {
    font-family: 'Cormorant Garamond', Georgia, serif;
}

.stApp {
    background: #0f0f0f;
    color: #e8dcc8;
}

.main-header {
    text-align: center;
    padding: 2rem 0 1rem 0;
    border-bottom: 1px solid #2a2a2a;
    margin-bottom: 2rem;
}

.main-header h1 {
    font-family: 'Cormorant Garamond', serif;
    font-weight: 300;
    font-size: 2rem;
    letter-spacing: 0.15em;
    color: #e8dcc8;
    margin: 0;
}

.main-header p {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    color: #5a5040;
    margin: 0.5rem 0 0 0;
    text-transform: uppercase;
}

.msg-guide {
    background: #161616;
    border-left: 2px solid #c4956a;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
    font-size: 1.05rem;
    line-height: 1.75;
    color: #e8dcc8;
}

.msg-visitor {
    background: #1a1a12;
    border-right: 2px solid #4a6a3a;
    border-radius: 8px 0 0 8px;
    padding: 0.8rem 1.2rem;
    margin: 0.8rem 0;
    font-size: 0.95rem;
    line-height: 1.6;
    color: #b8c8a8;
    text-align: right;
}

.label-guide {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.15em;
    color: #c4956a;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}

.label-visitor {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.15em;
    color: #4a6a3a;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
    text-align: right;
}

.status-bar {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #3a3a3a;
    text-align: center;
    letter-spacing: 0.1em;
    padding: 0.5rem 0;
}

div[data-testid="stAudioInput"] {
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 1rem;
}

section[data-testid="stSidebar"] {
    background: #0a0a0a;
    border-right: 1px solid #1a1a1a;
}

.stButton > button {
    background: #1a1a1a;
    color: #c4956a;
    border: 1px solid #2a2a2a;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    border-radius: 4px;
}

.stButton > button:hover {
    background: #242424;
    border-color: #c4956a;
}

.streaming-text {
    background: #161616;
    border-left: 2px solid #c4956a;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
    font-size: 1.05rem;
    line-height: 1.75;
    color: #e8dcc8;
    min-height: 3rem;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p style="font-family: JetBrains Mono, monospace; font-size: 0.65rem; letter-spacing: 0.15em; color: #5a5040; text-transform: uppercase;">Configuration</p>', unsafe_allow_html=True)
    api_key = st.secrets["OPENAI_API_KEY"]
    voice = st.selectbox("Voice", ["nova", "shimmer", "alloy", "echo", "fable", "onyx"], index=0)
    st.divider()
    if st.button("↺  New Visitor"):
        st.session_state.history = []
        st.session_state.display = []
        st.success("Reset")

if not api_key:
    st.markdown("""
    <div class="main-header">
        <h1>🏛 Museum Audio Guide</h1>
        <p>Enter your API key in the sidebar to begin</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

client = openai.OpenAI(api_key=api_key)

SYSTEM_PROMPT = (
    "You are a museum companion with deep knowledge across natural history, ecology, "
    "art history, archaeology, materials science, and physics. "
    "You walk alongside a curious visitor who has no specialist background.\n\n"
    "Your first move is always a short, precise question to find out what the visitor "
    "is actually looking at. Not a broad invitation but something specific enough to "
    "reveal where their attention really is.\n\n"
    "Then go somewhere real. Bring in the actual mechanism, the actual historical moment, "
    "the actual species, the actual material, the actual place. "
    "Not general statements like 'this reflects trade networks' but the specific route, "
    "the specific material, the reason it traveled, the moment in history when that happened.\n\n"
    "Narrate as if thinking out loud on a slow walk. "
    "Short punchy sentences for clear points, longer ones to build context. "
    "Cross-disciplinary connections only when real and tight.\n\n"
    "When something is genuinely uncertain among experts, say so.\n\n"
    "End each response with a specific question pointing at a concrete detail in front of them.\n\n"
    "Respond in whatever language the visitor uses."
)

# ── Session state ────────────────────────────────────────────
for k, v in [("history", []), ("display", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Core functions ───────────────────────────────────────────
def stt(audio_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        path = f.name
    try:
        with open(path, "rb") as f:
            return client.audio.transcriptions.create(
                model="whisper-1", file=f
            ).text.strip()
    finally:
        os.unlink(path)


def tts_chunk(text: str, voice: str) -> bytes:
    """Generate TTS for a single sentence chunk."""
    return client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text,
        response_format="mp3"
    ).content


def play_audio_bytes(audio_bytes: bytes):
    """Inject audio into page via base64 for immediate autoplay."""
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(
        f'<audio autoplay style="display:none">'
        f'<source src="data:audio/mp3;base64,{b64}" type="audio/mp3">'
        f'</audio>',
        unsafe_allow_html=True
    )


def stream_response_with_tts(messages: list, voice: str):
    """
    Stream GPT response sentence by sentence.
    Each complete sentence is immediately sent to TTS and played.
    Returns the full response text.
    """
    sentence_end = re.compile(r'(?<=[.!?。！？…])\s+')
    buffer = ""
    full_text = ""
    text_placeholder = st.empty()

    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=800,
        temperature=0.7,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        buffer += delta
        full_text += delta

        # Show text as it streams
        text_placeholder.markdown(
            f'<div class="streaming-text">{full_text}<span style="opacity:0.3">▌</span></div>',
            unsafe_allow_html=True
        )

        # When a sentence boundary appears, fire TTS immediately
        parts = sentence_end.split(buffer)
        if len(parts) > 1:
            for sentence in parts[:-1]:
                sentence = sentence.strip()
                if len(sentence) > 8:  # skip tiny fragments
                    audio = tts_chunk(sentence, voice)
                    play_audio_bytes(audio)
            buffer = parts[-1]

    # Play any remaining buffer
    if buffer.strip() and len(buffer.strip()) > 4:
        audio = tts_chunk(buffer.strip(), voice)
        play_audio_bytes(audio)

    # Replace streaming placeholder with final styled bubble
    text_placeholder.markdown(
        f'<div class="label-guide">Guide</div>'
        f'<div class="msg-guide">{full_text}</div>',
        unsafe_allow_html=True
    )

    return full_text


# ── Header ───────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🏛 Museum Audio Guide</h1>
    <p>Speak your question — the guide will respond</p>
</div>
""", unsafe_allow_html=True)

# ── Conversation history display ─────────────────────────────
for msg in st.session_state.display:
    if msg["role"] == "visitor":
        st.markdown(
            f'<div class="label-visitor">Visitor</div>'
            f'<div class="msg-visitor">{msg["content"]}</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="label-guide">Guide</div>'
            f'<div class="msg-guide">{msg["content"]}</div>',
            unsafe_allow_html=True
        )

# ── Audio input ──────────────────────────────────────────────
st.divider()
audio_input = st.audio_input("🎙 Record your question")

if audio_input:
    # Transcribe
    with st.spinner(""):
        user_text = stt(audio_input.getvalue())

    if user_text:
        # Show visitor bubble
        st.markdown(
            f'<div class="label-visitor">Visitor</div>'
            f'<div class="msg-visitor">{user_text}</div>',
            unsafe_allow_html=True
        )
        st.session_state.display.append({"role": "visitor", "content": user_text})
        st.session_state.history.append({"role": "user", "content": user_text})

        # Stream GPT + TTS sentence by sentence
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.history

        st.markdown('<div class="label-guide">Guide</div>', unsafe_allow_html=True)
        reply = stream_response_with_tts(messages, voice)

        # Save to history
        st.session_state.history.append({"role": "assistant", "content": reply})
        st.session_state.display.append({"role": "guide", "content": reply})

        # Keep context window manageable
        if len(st.session_state.history) > 20:
            st.session_state.history = st.session_state.history[-20:]

        st.markdown('<div class="status-bar">— say something to continue —</div>', unsafe_allow_html=True)

