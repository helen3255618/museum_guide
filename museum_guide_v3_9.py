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

# ── Iframe microphone permission fix ─────────────────────────
st.components.v1.html("""
    <script>
        const iframe = window.frameElement;
        if (iframe) {
            iframe.allow = "microphone";
        }
    </script>
""", height=0)

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
audio { display: none !important; }



</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p style="font-family:JetBrains Mono,monospace;font-size:0.65rem;letter-spacing:0.15em;color:#9a8878;text-transform:uppercase;">Configuration</p>', unsafe_allow_html=True)
    voice = st.selectbox(
        "Voice",
        ["nova", "shimmer", "alloy", "ash", "coral", "echo", "fable", "onyx", "sage"],
        index=0
    )
    st.divider()
    if st.button("↺  New Visitor"):
        st.session_state.history = []
        st.session_state.display = []
        st.rerun()

    st.divider()
    st.markdown('<p style="font-family:JetBrains Mono,monospace;font-size:0.65rem;letter-spacing:0.15em;color:#9a8878;text-transform:uppercase;">Version log</p>', unsafe_allow_html=True)

    VERSIONS = [
        {
            "version": "v3.9",
            "date": "2026-03-24",
            "changes": [
                "✨ Streamlined UX: single spinner, text stays in place, audio plays silently",
                "⏸ Stop/resume audio — pure JS toggle, no rerun, no re-generation",
                "📷 Camera on-demand — activates only when needed",
                "🔄 gpt-4o / gpt-4o-mini routing (stable chat completions, image supported)",
                "🔬 Scientific name input — stays locked across conversation",
                "🎙 Iframe microphone permission fix for Streamlit Cloud",
                "🔊 Voice list expanded: added ash, coral, sage",
            ],
        },
        {
            "version": "v2.0",
            "date": "2026-03-20",
            "changes": [
                "🏛 Initial museum audio guide",
                "🎙 Voice recording via st.audio_input",
                "🔊 Text-to-speech auto-playback",
                "💬 Multi-turn conversation with context memory",
            ],
        },
    ]

    for v in VERSIONS:
        is_latest = v == VERSIONS[0]
        label = f"{'● ' if is_latest else '○ '}{v['version']}  ·  {v['date']}"
        st.markdown(
            f'<p style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
            f'color:{"#c4956a" if is_latest else "#9a8878"};margin:0.6rem 0 0.2rem 0;">'
            f'{label}</p>',
            unsafe_allow_html=True
        )
        for change in v["changes"]:
            st.markdown(
                f'<p style="font-size:0.78rem;color:#6a5a4a;margin:0.1rem 0 0 0.5rem;line-height:1.5;">'
                f'{change}</p>',
                unsafe_allow_html=True
            )

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
for k, v in [("history", []), ("display", []), ("pending_image", None), ("specimen_name", "")]:
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

def stream_gpt(messages: list) -> str:
    full_text = ""
    placeholder = st.empty()

    has_image = any(
        isinstance(m.get("content"), list)
        for m in messages
        if m["role"] == "user"
    )
    model = "gpt-4o" if has_image else "gpt-4o-mini"

    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=800,
        temperature=0.7,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        full_text += delta
        placeholder.markdown(
            f'<div class="msg-guide">{full_text}<span style="opacity:0.3">▌</span></div>',
            unsafe_allow_html=True
        )

    # Finalize — remove cursor
    placeholder.markdown(
        f'<div class="msg-guide">{full_text}</div>',
        unsafe_allow_html=True
    )
    return full_text


def build_user_message(text: str, image_b64: str | None) -> dict:
    if image_b64:
        return {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                },
                {"type": "text", "text": text},
            ],
        }
    return {"role": "user", "content": text}

# ── Header ───────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🏛 Museum Audio Guide</h1>
    <p>Speak your question — the guide will respond</p>
</div>
""", unsafe_allow_html=True)

# ── Input area (top, always visible) ─────────────────────────
st.divider()
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    specimen_input = st.text_input(
        "🔬 Scientific name",
        value=st.session_state.specimen_name,
        placeholder="e.g. Panthera leo",
    )
    if specimen_input != st.session_state.specimen_name:
        st.session_state.specimen_name = specimen_input
    if st.session_state.specimen_name:
        st.caption(f"Locked: _{st.session_state.specimen_name}_")
        if st.button("✕ Clear name"):
            st.session_state.specimen_name = ""
            st.rerun()

with col2:
    if st.session_state.pending_image:
        st.success("Photo ready")
        if st.button("✕ Clear photo"):
            st.session_state.pending_image = None
            st.rerun()
    else:
        if "camera_open" not in st.session_state:
            st.session_state.camera_open = False
        if not st.session_state.camera_open:
            if st.button("📷 Take photo"):
                st.session_state.camera_open = True
                st.rerun()
        else:
            camera_shot = st.camera_input("📷 Take photo")
            if camera_shot:
                st.session_state.pending_image = base64.b64encode(camera_shot.getvalue()).decode()
                st.session_state.camera_open = False
                st.rerun()
            if st.button("✕ Cancel"):
                st.session_state.camera_open = False
                st.rerun()

with col3:
    audio_input = st.audio_input("🎙 Record your question")

# ── Pause / Resume button — pure HTML, no Streamlit rerun ────
st.components.v1.html("""
<button
    id="audioToggleBtn"
    onclick="
        var a = window.top._guideAudio;
        if (!a) return;
        if (a.paused) {
            a.play();
            this.innerText = '⏸ Pause';
        } else {
            a.pause();
            this.innerText = '▶ Resume';
        }
    "
    style="
        background: #f7f4ef;
        color: #c4956a;
        border: 1px solid #d4c8b8;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        letter-spacing: 0.1em;
        border-radius: 4px;
        padding: 0.35rem 0.75rem;
        cursor: pointer;
        margin-top: 0.5rem;
    "
>⏸ Pause</button>
""", height=40)

if audio_input:
    # Single spinner covers transcription + generation
    with st.spinner("思考中..."):
        user_text = stt(audio_input.getvalue())

    if user_text:
        full_text = user_text
        if st.session_state.specimen_name:
            full_text = f"[Specimen: {st.session_state.specimen_name}] {user_text}"

        display_text = user_text
        if st.session_state.specimen_name:
            display_text = f"🔬 {st.session_state.specimen_name} — {user_text}"
        if st.session_state.pending_image:
            display_text = "📷 " + display_text

        user_msg = build_user_message(full_text, st.session_state.pending_image)
        st.session_state.display.append({"role": "visitor", "content": display_text})
        st.session_state.history.append(user_msg)

        st.session_state.pending_image = None

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.history

        # Stream text — stays visible in place
        st.markdown('<div class="label-guide">Guide</div>', unsafe_allow_html=True)
        reply = stream_gpt(messages)

        # Generate and play audio silently in background
        audio_bytes = tts(reply)
        autoplay_audio(audio_bytes)

        st.session_state.history.append({"role": "assistant", "content": reply})
        st.session_state.display.append({"role": "guide", "content": reply})

        if len(st.session_state.history) > 20:
            st.session_state.history = st.session_state.history[-20:]

# ── Conversation history — guide only, newest first ──────────
st.divider()
for msg in reversed(st.session_state.display):
    if msg["role"] == "guide":
        st.markdown(
            f'<div class="label-guide">Guide</div>'
            f'<div class="msg-guide">{msg["content"]}</div>',
            unsafe_allow_html=True
        )
