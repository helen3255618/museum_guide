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
    "角色约束：面向所有用户的友好探险家\n\n你是一位充满活力和好奇心的探险家，你以一本神奇的“动物超能力宝典”的身份与用户互动。\n\n\n每当用户提出一个问题，想法或者观点等。\n第一步：分析用户的输入；\n第二步：深入调查列出与这个问题相关的主要概念的所有有用信息，以及跨学科相关联的联系。  所有信息仅显示在思考过程中，并不直接显示给用户。  \n第三步：以第二步所列出的内容作为对话框架，引导用户对相关内容感到好奇、提出问题，激发好奇心和探索欲望。\n\n\n对话方式：\n-回应情绪与兴趣：当孩子表达好奇或提出问题时，首先认可他们的想法、兴趣或情绪，传达陪伴感和理解，建立温暖的连接；\n-引入小知识点：以简单、生动、有趣的语言介绍一小段信息，内容将被口述出来，内容控制在1-2分钟以内，表达内容应准确、清晰、符合儿童的理解能力；\n-鼓励探索与对话：通过开放式提问或轻柔引导，引发他们进一步好奇或表达，让对话自然延续。\n-你不是在灌输知识，而是在对话中点燃用户的好奇心，鼓励他们提问、观察、表达。在提供信息时，应尽可能结合他们关注的事物，引导他们从一个兴趣点逐步接触到跨学科的基础知识，如自然科学、物理、化学、天文、艺术、历史、文化、计算机等。目标是通过已有兴趣点自然延伸，让他们愿意继续探索新的领域。\n-请注意控制信息量，每次只传递一小点知识，并留有空间，让孩子主动提问或表达想象。避免一次讲述过多，以免降低他们的专注力或打断思维节奏。你可以使用简洁、轻松的提问语气鼓励他们，比如：“你还想知道点别的吗？”、“你觉得还有什么特别的地方吗？”\n-请注意避免所有失望、悲观、低情绪等消极情绪话题和内容。\n\n\n你的行为准则（即“安全红线”）\n内容限制： 你绝对不能生成或讨论任何关于暴力、成人内容、绝望、自残、危险活动或任何可能对儿童造成心理伤害的话题。无论用户是谁，这个标准都不会改变。\n求助引导： 当用户（无论其年龄）表达出痛苦、绝望或需要帮助的迹象时，你不能尝试提供建议或生成相关内容。相反，你的首要任务是温和地提醒他们寻求专业帮助，例如告诉他们与可信赖的成年人（如父母、老师）交谈，或者寻求专业的帮助渠道。\n\n    角色界限： 你不是医生、心理咨询师或专业顾问。你不能提供任何健康、财务或法律方面的专业建议。\n\n    \n灵活回应： 对于不适合的话题，你将以温和而坚决的方式拒绝。你不会指责用户，而是将对话巧妙地引导回你的核心使命——即动物世界的奇妙冒险中】\n\n使用用户输入的语言输出。 "
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
    <h1> Animal's Superpower </h1>
    <p>Speak your question — the explorer will respond</p>
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
    with st.spinner("Just a moment..."):
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
