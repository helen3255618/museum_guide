import streamlit as st
import openai
import tempfile
import os
import base64
import datetime
import uuid
from google import genai
from google.genai import types
import gspread
from google.oauth2.service_account import Credentials

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
.notice-bar {
    background: #f0ebe3;
    border: 1px solid #d4c8b8;
    border-radius: 6px;
    padding: 0.8rem 1.1rem;
    margin-bottom: 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.63rem;
    color: #9a8878;
    letter-spacing: 0.05em;
    line-height: 1.9;
}
.mode-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.12em;
    color: #9a8878;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
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

# ── Fixed voice ───────────────────────────────────────────────
VOICE = "nova"

# ── System Prompts ────────────────────────────────────────────
SYSTEM_PROMPT_1 = """You are a Cross-Disciplinary Associative Thinking Simulator dedicated to cultivating multidimensional associative capabilities. By simulating cross-disciplinary thinking pathways, you spark innovation and deep insight. Your core goal is to help users build meaningful connections between seemingly unrelated fields, thereby enhancing their perceptual clarity and problem-solving ability.

OPERATING MECHANISM

Concept Parsing and Decomposition:
When a user inputs a concept, question, or challenge, you first perform a deep analysis, identifying core elements, implicit assumptions, and latent dimensions. You break complex concepts into smaller, manageable components for multi-angle examination.

Multidimensional Knowledge Retrieval and Association:
You draw on a broad knowledge base — science, art, philosophy, history, economics, engineering, sociology, and beyond — retrieving information both directly and tangentially related to the user's input. You focus on identifying shared patterns, analogies, metaphors, structures, processes, or underlying principles across disciplines. You actively seek connections between concepts that are not typically associated, in order to break habitual thinking.

Building Multidimensional Associative Pathways:
You generate cross-disciplinary associative pathways of several types:
- Direct analogy: finding functionally or structurally similar things across fields.
- Indirect connection: linking seemingly unrelated domains through shared abstract concepts or universal principles.
- Reverse inference: working backward from outcomes or phenomena in one field to possible causes or applications in another.
- Combinatorial innovation: merging elements from multiple disciplines to form new concepts or solutions.
- Historical evolution: tracing how a concept or phenomenon has evolved across different historical periods and cultural contexts, uncovering cross-era commonalities.

When building associations, pay particular attention to quantitative and scalar relationships — degree, proportion, intensity, frequency, scope, balance, tipping points — looking for how these dimensions manifest across disciplines.

Heuristic Questioning and Guidance:
Encourage users to explore connections they have not considered, challenging fixed assumptions.

BEHAVIORAL PRINCIPLES

- Open and exploratory: maintain an open mindset; encourage bold conceptual leaps and nonlinear exploration.
- Depth and breadth: cover a wide range of knowledge domains while digging into the essence and underlying logic of concepts.
- Critical and constructive: encourage users to critically evaluate associations and guide them toward concrete application.
- User-centered: adapt complexity and presentation to the user's interests, background, and goals.
- Tone — direct and unsentimental: use plain, peer-level language. No honorifics. Speak as an equal.
- Refuse clichés: begin each section by precisely identifying the fracture between the physical and logical dimensions of the subject. Stay cool — like a detached observer revealing counterintuitive logic. No emotional inflation; only facts and their implications.

NO CLOSING QUESTIONS
Never end a response with a question, rhetorical question, or any form of prompt directed at the user. Do not invite them to reflect, respond, or continue. Let the observation stand on its own. The user will speak when they are ready.

OUTPUT LENGTH
Keep each response under 800 words (for Latin-script languages) or 1000 characters (for Chinese, Japanese, Korean). Be dense and precise, not exhaustive.

LANGUAGE RULE
Always respond in the exact language the user has used in their most recent message. If they write in Chinese, respond in Chinese. If they write in French, respond in French. Switch immediately and completely when the user switches languages — no mixing."""

SYSTEM_PROMPT_2 = """Role Definition：
You are a museum-grade audio guide narrator. Your output is optimized for pure listening environments, where users cannot see text and cannot rewind easily.

Core Objective

Generate narration that is:

Accurate and domain-correct
Structured for auditory cognition
Delivered in a calm, guided, museum-style tone
Structural Constraints（强约束）
1. Opening (≤ 2 sentences)
Establish context immediately
Create attention hook using contrast or mild surprise

Pattern:

“You might think… but actually…”
“What you are seeing is…”
2. Explicit Framing
Always provide a clear structure upfront

Required:

Number of categories / items
Basis of classification

Example:

“We can divide them into four groups.”
“You can tell them apart by…”
3. Chunking Rule (Critical)
One entity = one paragraph
Each paragraph must contain:
Name
Location (optional but preferred)
ONE dominant visual trait
ONE analogy or mental image

Forbidden:

Multiple competing attributes in same sentence
Dense taxonomic descriptions
4. Memory Anchors

Each item must include at least one:

Analogy (e.g., “like a puzzle”, “like ink spreading”)
Contrast with previous item
Simple label (implicit or explicit)
5. Transition Signals (Every 20–30 seconds)

Must include phrases like:

“Next…”
“Now let’s look at…”
“The third type…”
6. Mid-summary (Optional but recommended)
Compress previous information into a short recall-friendly line

Example:

“So far, you’ve seen…”
“In simple terms…”
7. Closure (Required)

Must include:

A unifying statement (shared traits or concept)
A broader context (e.g., ecology, conservation, significance)
Language Style Constraints
Sentence length: short to medium (8–18 words preferred)
Avoid nested clauses
Prefer spoken rhythm over written grammar
Use pauses naturally (line breaks)
Tone Constraints
Calm, observational, slightly immersive
No excitement spikes, no exaggerated emotion
Avoid academic density; prefer guided explanation
Cognitive Load Rules
Max 3–4 key items per segment
Avoid introducing multiple unfamiliar terms at once
Reinforce with repetition when necessary
Output Format
Use line breaks to simulate pacing
No bullet points
No headings
Must read naturally when spoken aloud
Anti-Patterns（必须避免）
Dense paragraph without structure
Back-to-back technical descriptors
No framing before listing items
No recap or closure
Writing as if user is reading, not listening"""

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<p class="mode-label">Guide Mode</p>',
        unsafe_allow_html=True
    )
    mode = st.radio(
        label="",
        options=[
            "Mode 1 — Cross-Disciplinary",
            "Mode 2 — Scientific Docent",
        ],
        index=0,
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("↺  New Visitor"):
        st.session_state.history = []
        st.session_state.display = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.divider()
    st.markdown(
        '<p style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
        'letter-spacing:0.15em;color:#9a8878;text-transform:uppercase;">Version log</p>',
        unsafe_allow_html=True
    )
    VERSIONS = [
        {
            "version": "v4.0 in editing",
            "date": "Apr 2026",
            "changes": ["Work in progress"],
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

# ── Active system prompt based on mode selection ──────────────
SYSTEM_PROMPT = SYSTEM_PROMPT_1 if "Mode 1" in mode else SYSTEM_PROMPT_2

# ── API Keys ─────────────────────────────────────────────────
try:
    openai_api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    st.error("OpenAI API key not found. Add OPENAI_API_KEY in Secrets.")
    st.stop()

try:
    google_api_key = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("Google API key not found. Add GOOGLE_API_KEY in Secrets.")
    st.stop()

openai_client = openai.OpenAI(api_key=openai_api_key)
gemini_client = genai.Client(api_key=google_api_key)
GEMINI_MODEL = "gemini-3.1-pro-preview"

# ── Google Sheets client ──────────────────────────────────────
try:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    gs_client = gspread.client.Client(auth=creds)
    sheet = gs_client.open_by_key(st.secrets["GOOGLE_SHEET_ID"]).sheet1
    SHEETS_READY = True
    st.sidebar.success("✓ Sheets connected")
except Exception as e:
    SHEETS_READY = False
    import traceback
    st.session_state["sheets_error"] = traceback.format_exc()

# ── Session state ────────────────────────────────────────────
for k, v in [
    ("history", []),
    ("display", []),
    ("pending_image", None),
    ("specimen_name", ""),
    ("session_id", str(uuid.uuid4())),
    ("active_mode", mode),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# Reset history when mode changes
if st.session_state.active_mode != mode:
    st.session_state.history = []
    st.session_state.display = []
    st.session_state.active_mode = mode

# ── Functions ────────────────────────────────────────────────
def stt(audio_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        path = f.name
    try:
        with open(path, "rb") as f:
            return openai_client.audio.transcriptions.create(
                model="whisper-1", file=f
            ).text.strip()
    finally:
        os.unlink(path)

def tts(text: str) -> bytes:
    if len(text) > 4000:
        text = text[:4000]
    return openai_client.audio.speech.create(
        model="tts-1", voice=VOICE, input=text, response_format="mp3"
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

def log_exchange(user_text: str, reply: str, mode_name: str):
    if not SHEETS_READY:
        return
    try:
        sheet.append_row([
            str(datetime.datetime.utcnow()),
            st.session_state.session_id,
            mode_name,
            user_text,
            reply,
        ])
    except Exception:
        pass

def build_user_message(text: str, image_b64: str | None) -> dict:
    if image_b64:
        return {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                {"type": "text", "text": text},
            ],
        }
    return {"role": "user", "content": text}

def build_gemini_contents(history: list, system_prompt: str) -> list:
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"[System instructions]\n{system_prompt}")]
        ),
        types.Content(
            role="model",
            parts=[types.Part.from_text(text="Understood. I will follow these instructions precisely.")]
        ),
    ]
    for m in history:
        if m["role"] == "system":
            continue
        role = "user" if m["role"] == "user" else "model"
        if isinstance(m["content"], list):
            parts = []
            for part in m["content"]:
                if part["type"] == "text":
                    parts.append(types.Part.from_text(text=part["text"]))
                elif part["type"] == "image_url":
                    b64 = part["image_url"]["url"].split(",")[1]
                    img_bytes = base64.b64decode(b64)
                    parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
            contents.append(types.Content(role=role, parts=parts))
        else:
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=m["content"])]
            ))
    return contents

def stream_gemini(messages: list, system_prompt: str) -> str:
    full_text = ""
    placeholder = st.empty()

    history = [m for m in messages if m["role"] != "system"]
    contents = build_gemini_contents(history, system_prompt)

    try:
        stream = gemini_client.models.generate_content_stream(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                max_output_tokens=4019,
                temperature=0.7,
            ),
        )
        for chunk in stream:
            delta = chunk.text or ""
            full_text += delta
            placeholder.markdown(
                f'<div class="msg-guide">{full_text}<span style="opacity:0.3">▌</span></div>',
                unsafe_allow_html=True
            )
    except Exception as e:
        st.error(f"Gemini API error: {e}")
        return ""

    placeholder.markdown(
        f'<div class="msg-guide">{full_text}</div>',
        unsafe_allow_html=True
    )
    return full_text

# ── Header ───────────────────────────────────────────────────
if "sheets_error" in st.session_state:
    st.error(st.session_state["sheets_error"])

st.markdown("""
<div class="main-header">
    <h1>Curiosity Expedition</h1>
    <p>Cross-Disciplinary Associative Thinking Simulator</p>
</div>
""", unsafe_allow_html=True)

# ── Notice bar ───────────────────────────────────────────────
st.markdown("""
<div class="notice-bar">
⚠️ &nbsp;AI responses may contain errors — always verify information independently.<br>
🔒 &nbsp;Your questions and responses are collected anonymously (no personal data) for research purposes only.
</div>
""", unsafe_allow_html=True)

# ── Input area ───────────────────────────────────────────────
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

# ── Pause / Resume button ────────────────────────────────────
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

# ── Main logic ───────────────────────────────────────────────
if audio_input:
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

        st.markdown('<div class="label-guide">Guide</div>', unsafe_allow_html=True)
        reply = stream_gemini(messages, SYSTEM_PROMPT)

        if reply:
            log_exchange(user_text, reply, mode)
            audio_bytes = tts(reply)
            autoplay_audio(audio_bytes)
            st.session_state.history.append({"role": "assistant", "content": reply})
            st.session_state.display.append({"role": "guide", "content": reply})

        if len(st.session_state.history) > 20:
            st.session_state.history = st.session_state.history[-20:]

# ── Conversation history ──────────────────────────────────────
st.divider()
for msg in reversed(st.session_state.display):
    if msg["role"] == "guide":
        st.markdown(
            f'<div class="label-guide">Guide</div>'
            f'<div class="msg-guide">{msg["content"]}</div>',
            unsafe_allow_html=True
        )
