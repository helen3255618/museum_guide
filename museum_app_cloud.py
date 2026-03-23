st.components.v1.html("""
    <script>
        const iframe = window.frameElement;
        if (iframe) {
            iframe.allow = "microphone";
        }
    </script>
""", height=0)

import streamlit as st
import openai
import tempfile
import os
import base64

st.set_page_config(
    page_title="Museum Audio Guide",
    page_icon="🏛️",
    layout="centered",
)

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
.status-bar {
    font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
    color: #b0a090; text-align: center; letter-spacing: 0.1em; padding: 0.5rem 0;
}
.streaming-text {
    background: #ffffff; border-left: 3px solid #e8c49a;
    border-radius: 0 8px 8px 0; padding: 1rem 1.2rem; margin: 0.8rem 0;
    font-size: 1.05rem; line-height: 1.75; color: #2a1f14;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
section[data-testid="stSidebar"] { background: #f0ebe3; border-right: 1px solid #d4c8b8; }
.stButton > button {
    background: #f7f4ef; color: #c4956a; border: 1px solid #d4c8b8;
    font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
    letter-spacing: 0.1em; border-radius: 4px;
}
.stButton > button:hover { background: #fff; border-color: #c4956a; }
/* Hide the default st.audio player bar */
audio { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p style="font-family:JetBrains Mono,monospace;font-size:0.65rem;letter-spacing:0.15em;color:#9a8878;text-transform:uppercase;">Configuration</p>', unsafe_allow_html=True)
    voice = st.selectbox("Voice", ["nova", "shimmer", "alloy", "echo", "fable", "onyx"], index=0)
    st.divider()
    if st.button("↺  New Visitor"):
        st.session_state.history = []
        st.session_state.display = []
        st.rerun()

# ── API Key ──────────────────────────────────────────────────
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    st.error("API key not found. Go to Manage app → Settings → Secrets and add OPENAI_API_KEY.")
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

# ── Functions ────────────────────────────────────────────────
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

def tts(text: str) -> bytes:
    return client.audio.speech.create(
        model="tts-1", voice=voice, input=text, response_format="mp3"
    ).content

def autoplay_audio(audio_bytes: bytes):
    """
    Use st.components to guarantee script execution in Streamlit Cloud.
    This is an iframe — scripts inside always run.
    """
    b64 = base64.b64encode(audio_bytes).decode()
    st.components.v1.html(
        f"""
        <script>
        var audio = new Audio('data:audio/mp3;base64,{b64}');
        audio.play();
        </script>
        """,
        height=0,
    )

def stream_gpt(messages: list) -> str:
    """Stream GPT text only — show as it arrives."""
    full_text = ""
    placeholder = st.empty()

    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=800,
        temperature=0.7,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        full_text += delta
        placeholder.markdown(
            f'<div class="streaming-text">{full_text}<span style="opacity:0.3">▌</span></div>',
            unsafe_allow_html=True
        )

    placeholder.markdown(
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

# ── Conversation history ─────────────────────────────────────
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
    # Step 1: Transcribe
    with st.spinner("Transcribing..."):
        user_text = stt(audio_input.getvalue())

    if user_text:
        st.markdown(
            f'<div class="label-visitor">Visitor</div>'
            f'<div class="msg-visitor">{user_text}</div>',
            unsafe_allow_html=True
        )
        st.session_state.display.append({"role": "visitor", "content": user_text})
        st.session_state.history.append({"role": "user", "content": user_text})

        # Step 2: Stream GPT text
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.history
        st.markdown('<div class="label-guide">Guide</div>', unsafe_allow_html=True)
        reply = stream_gpt(messages)

        # Step 3: TTS once on full reply → autoplay via iframe
        with st.spinner("Generating audio..."):
            audio_bytes = tts(reply)
        autoplay_audio(audio_bytes)

        st.session_state.history.append({"role": "assistant", "content": reply})
        st.session_state.display.append({"role": "guide", "content": reply})

        if len(st.session_state.history) > 20:
            st.session_state.history = st.session_state.history[-20:]

        st.markdown('<div class="status-bar">— say something to continue —</div>', unsafe_allow_html=True)
