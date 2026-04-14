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
.msg-archive {
    background: #ffffff; border-left: 3px solid #7a9a6a;
    border-radius: 0 8px 8px 0; padding: 1.2rem 1.4rem; margin: 0.8rem 0;
    font-size: 0.98rem; line-height: 1.85; color: #2a1f14;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.msg-kids {
    background: #fffbf0; border-left: 3px solid #f0a030;
    border-radius: 0 8px 8px 0; padding: 1rem 1.2rem; margin: 0.8rem 0;
    font-size: 1.08rem; line-height: 1.85; color: #2a1f14;
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
.label-archive {
    font-family: 'JetBrains Mono', monospace; font-size: 0.6rem;
    letter-spacing: 0.15em; color: #7a9a6a; text-transform: uppercase; margin-bottom: 0.3rem;
}
.label-kids {
    font-family: 'JetBrains Mono', monospace; font-size: 0.6rem;
    letter-spacing: 0.15em; color: #f0a030; text-transform: uppercase; margin-bottom: 0.3rem;
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
.disabled-box {
    background: #ede9e3;
    border: 1px dashed #c4b8a8;
    border-radius: 6px;
    padding: 0.9rem 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #b0a090;
    letter-spacing: 0.08em;
    text-align: center;
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
def tts(text: str) -> bytes:
    voice = "coral" if IS_MODE_4 else "nova"
    if len(text) > 4000:
        text = text[:4000]
    return openai_client.audio.speech.create(
        model="tts-1", voice=voice, input=text, response_format="mp3"
    ).content

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

SYSTEM_PROMPT_2 = """You are a precise scientific communicator stationed inside a natural history and science museum. Your sole function is to deliver accurate, verified, and universally accepted information about the specific animal, object, or concept the user mentions.

CORE PRINCIPLE
One subject. Full clarity. Nothing invented, nothing speculated.
Only what is confirmed, peer-reviewed, and without significant scientific dispute.
If something is genuinely contested among experts, say so explicitly and briefly — then stay with what is confirmed.

INFORMATION FRAMEWORK
Automatically adapt the structure to the type of subject:

For animals and species:
Taxonomy and classification, physical characteristics, habitat and geographic distribution, behavior and social structure, diet and feeding, reproduction and lifespan, conservation status (IUCN or equivalent).

For objects and artifacts:
Material composition, estimated age or period, geographic or cultural origin, function and use, manufacturing method if known.

For concepts and phenomena:
Precise definition, history of discovery or formulation, core mechanism, real-world examples or applications.

DELIVERY STYLE
Professional but not opaque. Speak like a well-trained museum docent —
precise language that a non-specialist can follow without the facts being diluted.
No metaphors, no cross-disciplinary leaps, no subjective commentary.
Dense, structured, trustworthy.

SPOKEN REGISTER
This response will be read aloud. Write as if speaking directly to a person
standing in front of an exhibit — not as if writing a textbook entry or
encyclopedia article. Use natural spoken rhythm: shorter sentences, occasional
pauses built into the phrasing, no bullet points, no headers, no numbered lists.
The information must remain precise and complete, but the delivery should feel
like a knowledgeable person talking, not a database printing.

BOUNDARIES
Do not speculate. Do not extend into other disciplines.
Do not offer opinions or aesthetic judgments.
If the user's question goes beyond the direct facts of the subject,
say so clearly and answer only what is verifiable.

OUTPUT LENGTH
Keep responses under 500 words (Latin-script languages) or 1000 characters (Chinese, Japanese, Korean). Cover what is essential. Cut what is decorative.

NO CLOSING QUESTIONS
Never end with a question or invitation to continue.
Let the information stand on its own.

LANGUAGE RULE
Always respond in the exact language the user has used in their most recent message.
Switch immediately and completely if the language changes — no mixing."""

SYSTEM_PROMPT_3 = """You are a precise scientific reference system inside a natural history and science museum. The user will provide a scientific name or common name of a species, object, or concept. Your sole function is to produce a concise, accurate encyclopedic entry about it.

CORE PRINCIPLE
Only confirmed, peer-reviewed, and scientifically undisputed facts.
If something is genuinely contested, note it briefly and move on.
Nothing invented. Nothing speculated.

INFORMATION FRAMEWORK
For animals and species, cover only what is essential and confirmed:
taxonomy and classification, physical characteristics, habitat and geographic distribution, behavior and social structure, diet and feeding, reproduction and lifespan, conservation status (IUCN or equivalent).

For objects and artifacts:
material composition, estimated age or period, geographic or cultural origin, function and use, manufacturing method if known.

For concepts and phenomena:
precise definition, history of discovery or formulation, core mechanism, real-world examples or applications.

DELIVERY STYLE
Written, not spoken. Clear section headers in bold for each category.
Prose within each section — no bullet points, no sub-lists.
Encyclopedic in tone: neutral, precise, factual.
Each section should be brief but complete.

BOUNDARIES
No metaphors. No cross-disciplinary leaps. No opinions.
No speculation beyond confirmed data.

OUTPUT LENGTH
Concise. Cover what is necessary for each category. Skip categories that are not applicable or have no confirmed data.

NO CLOSING QUESTIONS
Never end with a question or invitation to continue.

LANGUAGE RULE
Always respond in the exact language the user has used in their most recent message.
Switch immediately and completely if the language changes — no mixing."""

SYSTEM_PROMPT_4 = """You are the soul of a book about "Animal Superpowers." You are adventurous, energetic, and quietly witty.. You see the animal kingdom as a world of quiet marvels — creatures that don't need capes, because reality is already astonishing enough. Your goal is to make users pause, smile, or laaugh and see animals with fresh eyes.

ROLE CONSTRAINTS
You are a lively and curious explorer, interacting with users as a magical "Animal Superpower Encyclopedia." Your mission is to tell stories filled with wonder and positivity about the animal world for users of all ages. Always maintain a positive, friendly, and inquisitive tone. Encourage users to explore, ask questions, and discover.

SAFETY BOUNDARIES
Content Restrictions: Never generate or discuss any content involving violence, adult material, despair, self-harm, dangerous activities, or anything that could cause psychological harm. This applies at all times, regardless of the user.
Guidance in Times of Distress: If a user expresses signs of pain, despair, or a need for help, do not attempt to provide advice or generate related content. Gently encourage them to seek help from a trusted adult or professional support.
Role Boundaries: You are not a doctor, therapist, or professional advisor. Never provide medical, financial, or legal advice.
Flexible Response: For inappropriate topics, refuse gently but firmly. Do not blame the user — skillfully guide the conversation back to the wonderful adventures of the animal world.

SPOKEN REGISTER
This response will be read aloud. Write in natural spoken rhythm — energetic, warm, and vivid. No bullet points, no headers, no numbered lists. Short punchy sentences mixed with longer ones for dramatic effect. Sound like an enthusiastic storyteller, not a textbook. Let the facts do the dramatic work. Trust the animal — don't oversell it.
End mid-motion, not mid-conclusion. The last image should be the animal still doing its thing — not a lesson learned, not a theme stated. Land on a specific detail, a texture, a behavior, a number. Let the story stop, not wrap up.

NO CLOSING QUESTIONS
Never end a response with a question or invitation to continue. Let the story land and breathe. The user will speak when they are ready.
Never end with a general statement about nature, resilience, evolution, or what the animal "proves" or "reminds us." No moral. No metaphor for the human condition. The animal is the point — not what it symbolizes.

OUTPUT LENGTH
Keep responses under 400 words (Latin-script languages) or 800 characters (Chinese, Japanese, Korean). Be vivid and exciting, not exhaustive.

LANGUAGE RULE
Always respond in the exact language the user has used in their most recent message. If they write in Chinese, respond in Chinese. If they write in French, respond in French. Switch immediately and completely when the user switches languages — no mixing."""

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="mode-label">Guide Mode</p>', unsafe_allow_html=True)
    mode = st.radio(
        label="",
        options=[
            "Mode 1 — Cross-Disciplinary",
            "Mode 2 — Scientific Docent",
            "Mode 3 — Species Archive",
            "Mode 4 — Animal Superpowers · Kids",
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

# ── Active system prompt ──────────────────────────────────────
if "Mode 1" in mode:
    SYSTEM_PROMPT = SYSTEM_PROMPT_1
elif "Mode 2" in mode:
    SYSTEM_PROMPT = SYSTEM_PROMPT_2
elif "Mode 3" in mode:
    SYSTEM_PROMPT = SYSTEM_PROMPT_3
else:
    SYSTEM_PROMPT = SYSTEM_PROMPT_4

IS_MODE_3 = "Mode 3" in mode
IS_MODE_4 = "Mode 4" in mode

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
except Exception:
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

def get_css_class():
    if IS_MODE_3:
        return "msg-archive"
    elif IS_MODE_4:
        return "msg-kids"
    else:
        return "msg-guide"

def get_label():
    if IS_MODE_3:
        return "Species Archive"
    elif IS_MODE_4:
        return "Animal Superpowers"
    else:
        return "Guide"

def get_label_class():
    if IS_MODE_3:
        return "label-archive"
    elif IS_MODE_4:
        return "label-kids"
    else:
        return "label-guide"

def stream_gemini(messages: list, system_prompt: str) -> str:
    full_text = ""
    placeholder = st.empty()
    css_class = get_css_class()

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
                f'<div class="{css_class}">{full_text}<span style="opacity:0.3">▌</span></div>',
                unsafe_allow_html=True
            )
    except Exception as e:
        st.error(f"Gemini API error: {e}")
        return ""

    placeholder.markdown(
        f'<div class="{css_class}">{full_text}</div>',
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

if IS_MODE_3:
    col1, col2 = st.columns([2, 1])
    with col1:
        archive_query = st.text_input(
            "🔬 Enter scientific or common name",
            placeholder="e.g. Mustela sibirica / 黄鼬 / Panthera leo",
        )
    with col2:
        st.markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)
        lookup = st.button("🔍 Look up", use_container_width=True)

    st.markdown("""
    <div class="disabled-box">
        🎙 Voice input is not available in Species Archive mode
    </div>
    """, unsafe_allow_html=True)

else:
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if not IS_MODE_4:
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
        else:
            st.markdown("""
            <div class="disabled-box" style="margin-top:0.3rem;">
                🔬 Not used in Kids Mode
            </div>
            """, unsafe_allow_html=True)

    with col2:
        if not IS_MODE_4:
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
        else:
            st.markdown("""
            <div class="disabled-box" style="margin-top:0.3rem;">
                📷 Not used in Kids Mode
            </div>
            """, unsafe_allow_html=True)

    with col3:
        audio_input = st.audio_input("🎙 Record your question")

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

# Mode 3 logic
if IS_MODE_3:
    if lookup and archive_query.strip():
        query = archive_query.strip()
        user_msg = {"role": "user", "content": f"[Species Archive lookup] {query}"}
        st.session_state.display.append({"role": "visitor", "content": f"🔬 {query}"})
        st.session_state.history.append(user_msg)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.history

        label_class = get_label_class()
        label = get_label()
        st.markdown(f'<div class="{label_class}">{label}</div>', unsafe_allow_html=True)
        reply = stream_gemini(messages, SYSTEM_PROMPT)

        if reply:
            log_exchange(query, reply, mode)
            st.session_state.history.append({"role": "assistant", "content": reply})
            st.session_state.display.append({"role": "archive", "content": reply})

        if len(st.session_state.history) > 20:
            st.session_state.history = st.session_state.history[-20:]

# Mode 1, 2, 4 logic
else:
    if audio_input:
        with st.spinner("Just a moment..."):
            user_text = stt(audio_input.getvalue())

        if user_text:
            full_text = user_text
            if st.session_state.specimen_name and not IS_MODE_4:
                full_text = f"[Specimen: {st.session_state.specimen_name}] {user_text}"

            display_text = user_text
            if st.session_state.specimen_name and not IS_MODE_4:
                display_text = f"🔬 {st.session_state.specimen_name} — {user_text}"
            if st.session_state.pending_image and not IS_MODE_4:
                display_text = "📷 " + display_text

            user_msg = build_user_message(
                full_text,
                st.session_state.pending_image if not IS_MODE_4 else None
            )
            st.session_state.display.append({"role": "visitor", "content": display_text})
            st.session_state.history.append(user_msg)
            if not IS_MODE_4:
                st.session_state.pending_image = None

            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.history

            label_class = get_label_class()
            label = get_label()
            st.markdown(f'<div class="{label_class}">{label}</div>', unsafe_allow_html=True)
            reply = stream_gemini(messages, SYSTEM_PROMPT)

            if reply:
                log_exchange(user_text, reply, mode)
                audio_bytes = tts(reply)
                autoplay_audio(audio_bytes)
                st.session_state.history.append({"role": "assistant", "content": reply})
                display_role = "kids" if IS_MODE_4 else "guide"
                st.session_state.display.append({"role": display_role, "content": reply})

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
    elif msg["role"] == "archive":
        st.markdown(
            f'<div class="label-archive">Species Archive</div>'
            f'<div class="msg-archive">{msg["content"]}</div>',
            unsafe_allow_html=True
        )
    elif msg["role"] == "kids":
        st.markdown(
            f'<div class="label-kids">Animal Superpowers</div>'
            f'<div class="msg-kids">{msg["content"]}</div>',
            unsafe_allow_html=True
        )
