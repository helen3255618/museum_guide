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

# ── 样式保持不变 ──────────────────────────────
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
.label-guide { font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; color: #c4956a; text-transform: uppercase; }
.label-visitor { font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; color: #7a9a6a; text-transform: uppercase; text-align: right; }
.streaming-text { background: #ffffff; border-left: 3px solid #e8c49a; border-radius: 0 8px 8px 0; padding: 1rem 1.2rem; font-size: 1.05rem; }
audio { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── API Key ──
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    st.error("请在 Secrets 中配置 OPENAI_API_KEY")
    st.stop()

client = openai.OpenAI(api_key=api_key)

# ── Session State ──
if "history" not in st.session_state: st.session_state.history = []
if "display" not in st.session_state: st.session_state.display = []
if "specimen_name" not in st.session_state: st.session_state.specimen_name = ""

# ── 工具函数 ──
def stt(audio_bytes):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        path = f.name
    try:
        with open(path, "rb") as f:
            return client.audio.transcriptions.create(model="whisper-1", file=f).text.strip()
    finally:
        if os.path.exists(path): os.unlink(path)

def tts(text, voice_opt):
    return client.audio.speech.create(model="tts-1", voice=voice_opt, input=text).content

def autoplay_audio(audio_bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    st.components.v1.html(f"<script>new Audio('data:audio/mp3;base64,{b64}').play();</script>", height=0)

def stream_gpt(messages):
    full_text = ""
    placeholder = st.empty()
    # 修正：使用标准的 ChatCompletion API
    stream = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=messages,
        stream=True
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            full_text += content
            placeholder.markdown(f'<div class="streaming-text">{full_text}▌</div>', unsafe_allow_html=True)
    placeholder.empty() # 清除流式占位符，由统一的历史记录渲染
    return full_text

# ── Sidebar ──
with st.sidebar:
    voice = st.selectbox("Voice", ["nova", "shimmer", "alloy", "ash", "coral", "echo", "fable", "onyx", "sage"])
    if st.button("↺ New Visitor"):
        st.session_state.history = []
        st.session_state.display = []
        st.rerun()

# ── 主界面 ──
st.markdown('<div class="main-header"><h1>🏛 Museum Audio Guide</h1><p>Speak your question</p></div>', unsafe_allow_html=True)

# 渲染对话历史
for msg in st.session_state.display:
    role_class = "visitor" if msg["role"] == "visitor" else "guide"
    st.markdown(f'<div class="label-{role_class}">{role_class.title()}</div><div class="msg-{role_class}">{msg["content"]}</div>', unsafe_allow_html=True)

st.divider()
col1, col2 = st.columns([1, 2])
with col1:
    specimen_input = st.text_input("🔬 Scientific name", value=st.session_state.specimen_name, placeholder="e.g. Panthera leo")
    st.session_state.specimen_name = specimen_input
with col2:
    audio_input = st.audio_input("🎙 Record your question")

# 处理新输入
if audio_input:
    # 检查当前音频是否已经处理过，防止重刷
    audio_hash = hash(audio_input.getvalue())
    if "last_audio_hash" not in st.session_state or st.session_state.last_audio_hash != audio_hash:
        st.session_state.last_audio_hash = audio_hash
        
        with st.spinner("Thinking..."):
            user_text = stt(audio_input.getvalue())
            if user_text:
                # 拼接逻辑
                full_user_content = f"[Specimen: {st.session_state.specimen_name}] {user_text}" if st.session_state.specimen_name else user_text
                display_user_text = f"🔬 {st.session_state.specimen_name} — {user_text}" if st.session_state.specimen_name else user_text
                
                # 更新状态
                st.session_state.display.append({"role": "visitor", "content": display_user_text})
                st.session_state.history.append({"role": "user", "content": full_user_content})
                
                # 获取 AI 响应
                system_msg = {"role": "system", "content": "You are a museum companion. Respond conversationally, no bullet points. End with a specific question about a detail."}
                messages = [system_msg] + st.session_state.history[-10:] # 取最近10轮
                
                reply = stream_gpt(messages)
                
                # 语音合成与播放
                audio_reply = tts(reply, voice)
                autoplay_audio(audio_reply)
                
                # 存入历史并刷新
                st.session_state.history.append({"role": "assistant", "content": reply})
                st.session_state.display.append({"role": "guide", "content": reply})
                st.rerun()
