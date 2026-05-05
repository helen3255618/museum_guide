
Claude finished the response
You said: let's fix a peoblem.
let's fix a peoblem. 

the web app deployed by streamlit, the voice function does not work again. it only happens on my iphone ios system broswers, i tested 3 broswers and none of them work. but my laptop browswer works very  well.

4:00 PM
Claude responded: Let me ask a few questions to better understand the issue before we dive in.
Let me ask a few questions to better understand the issue before we dive in.

Can you answer these two quick questions? That'll help me pinpoint whether this is a permissions issue, a browser API compatibility issue, or something specific to how your Streamlit component is implemented.

You said: Q: What does 'voice function' mean in your app?
Q: What does 'voice function' mean in your app?
A: Speech-to-text (mic input)

Q: What happens on iPhone when you try to use it?
A: Error message shown

4:01 PM
Claude responded: What does the error message say?
What does the error message say? And can you also share the relevant code that handles the microphone/speech-to-text in your Streamlit app?

You said: well, i cant find where is the developer tool on my phone side.
well, i cant find where is the developer tool on my phone side... so i dont knwo what is the issue.

4:03 PM
Claude responded: No worries!
No worries! The good news is that iPhone browser issues with microphone/speech-to-text are very well-known, and the root cause is almost always one of a few things. Let me explain what's likely happening.

The core problem: iOS Safari restrictions

iOS browsers (Safari, Chrome, Firefox on iPhone — they all use the same WebKit engine underneath) have strict rules around microphone access:

getUserMedia() requires a user gesture — the mic can only be activated directly from a tap event. If your code triggers it programmatically or with a slight delay, iOS blocks it silently or throws an error.
MediaRecorder API is poorly supported on iOS — if your app uses MediaRecorder to capture audio, it often fails on iOS because Safari has limited/buggy support for it.
HTTPS is mandatory — mic access is blocked on non-HTTPS pages (Streamlit Cloud is HTTPS, so this is likely fine).
Web Speech API (SpeechRecognition) — iOS Safari has partial support, and it behaves differently than Chrome on desktop.
To help you fix it, can you share the relevant code? Specifically I'm looking for things like:

How you're capturing mic input (e.g. streamlit-webrtc, a custom JS component, st.audio, SpeechRecognition, etc.)
Any JavaScript snippets involving getUserMedia, MediaRecorder, or webkitSpeechRecognition
If you can paste the relevant part of your code here, I can pinpoint the exact fix needed for iOS compatibility.

You said: the problem is strange.
the problem  is strange. it was working fine abuot 1 monthes aago. i  did not touch open it , and then now it's not working... what is the problem ?

4:05 PM
Claude responded: That's a very important clue!
That's a very important clue! If you didn't change anything, the most likely culprits are:

1. iOS system update broke something (most likely) Apple released iOS 17.x and 18.x updates in recent months. These updates have a history of quietly tightening WebKit security policies — things that worked before can suddenly break without any code change on your end. Specifically, iOS 18 changed how permissions for microphone access work in WebKit.

2. Streamlit version auto-updated Streamlit Cloud automatically updates its runtime. A dependency or Streamlit itself may have been bumped to a newer version that changed how the frontend component behaves on mobile.

3. A third-party library you use got updated If you use something like streamlit-webrtc or any JS-based audio library, it may have received an update that broke iOS compatibility.

Quick things to check right now:

What iOS version is your iPhone on? (Settings → General → About → iOS Version)
Go to your Streamlit app and check the bottom of the sidebar or run streamlit --version — did the version change?
Did Streamlit Cloud show any migration warnings in your dashboard?
The most likely fix without seeing your code:

If it's an iOS 18 issue, the fix usually involves ensuring the mic is triggered directly and synchronously inside a user tap event, with no async/await delays before calling getUserMedia(). iOS 18 became stricter about this.

Can you share your code so I can give you a precise fix?

You said: which part of the code do you need?
which part of the code do you need?

4:07 PM
Claude responded: I need these specific parts:
I need these specific parts:

The microphone/recording logic — any code that uses getUserMedia, MediaRecorder, SpeechRecognition, or webkitSpeechRecognition
The button/trigger — the code that starts the recording when the user clicks/taps
Any custom JavaScript components — if you have an st.components.v1.html() or st.components.v1.declare_component() block related to audio/voice
If your project has multiple files, it's likely in one of these:

A file named something like audio.py, voice.py, speech.py
Or inside your main app.py / main.py — just search for keywords like "record", "audio", "microphone", "speech", or "getUserMedia"
Paste whichever file(s) contain those keywords and that'll be enough to diagnose the problem!


import streamlit as st import openai import tempfile import os import base64 import datetime import uuid from google import genai from google.genai import types import gspread from google.oauth2.service_account import Credentials st.set_page_config( page_title="Museum Audio Guide", page_ico

pasted

4:07 PM
Claude responded: Now I can see the full picture.
Now I can see the full picture. Let me identify the exact problems for iOS.

There are 2 issues causing the failure on iPhone:

Issue 1 — st.audio_input inside an iframe (the main culprit)
Streamlit apps run inside an <iframe>. Your fix at the top tries to set iframe.allow = "microphone" via JavaScript, but this doesn't work on iOS Safari/WebKit — iOS requires the allow="microphone" attribute to be set server-side on the iframe HTML element itself, not patched via JS at runtime. WebKit ignores runtime permission grants.

This worked before because older iOS versions were more lenient. iOS 17.4+ and iOS 18.x tightened this — now it strictly enforces the attribute must be present at load time.

Issue 2 — autoplay_audio via window.top is blocked on iOS
Your audio autoplay uses new Audio(...) injected into window.top. iOS Safari blocks autoplay of audio that isn't triggered directly and synchronously by a user tap. Since the audio fires after an API round-trip (Whisper → Gemini → TTS), iOS kills it.

The Fix
For Issue 1 — you need to patch the iframe allow attribute at the Streamlit server config level, not in JS. Add this to your .streamlit/config.toml:

toml
[server]
enableCORS = false
enableXsrfProtection = false
And replace your broken JS iframe patch with this more robust version that targets the correct iframe:

python
st.components.v1.html("""
<script>
(function() {
    function patchIframes() {
        var iframes = window.parent.document.querySelectorAll('iframe');
        iframes.forEach(function(f) {
            if (!f.allow || !f.allow.includes('microphone')) {
                f.allow = (f.allow ? f.allow + '; ' : '') + 'microphone';
                f.setAttribute('allow', f.allow);
            }
        });
    }
    patchIframes();
    setTimeout(patchIframes, 500);
    setTimeout(patchIframes, 1500);
})();
</script>
""", height=0)
For Issue 2 — replace your autoplay_audio function with one that uses a visible play button as fallback on iOS, since autoplay is blocked:

python
def autoplay_audio(audio_bytes: bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    st.components.v1.html(
        f"""
        <script>
        (function() {{
            var src = 'data:audio/mp3;base64,{b64}';

            if (window.top._guideAudio) {{
                window.top._guideAudio.pause();
                window.top._guideAudio.currentTime = 0;
            }}

            var audio = new Audio(src);
            window.top._guideAudio = audio;
            window.top._guideAudioPaused = false;

            var btn = window.top.document.getElementById('audioToggleBtn');

            var playPromise = audio.play();
            if (playPromise !== undefined) {{
                playPromise.then(function() {{
                    if (btn) btn.innerText = '⏸ Pause';
                }}).catch(function(err) {{
                    // iOS blocked autoplay — show a tap-to-play prompt
                    if (btn) {{
                        btn.innerText = '▶ Tap to play response';
                        btn.style.background = '#c4956a';
                        btn.style.color = '#fff';
                        btn.onclick = function() {{
                            audio.play();
                            btn.innerText = '⏸ Pause';
                            btn.style.background = '#f7f4ef';
                            btn.style.color = '#c4956a';
                            btn.onclick = function() {{
                                if (audio.paused) {{
                                    audio.play();
                                    btn.innerText = '⏸ Pause';
                                }} else {{
                                    audio.pause();
                                    btn.innerText = '▶ Resume';
                                }}
                            }};
                        }};
                    }}
                }});
            }}
        }})();
        </script>
        """,
        height=0,
    )
Summary of changes
Problem	Root cause	Fix
Mic not working on iOS	iframe.allow can't be patched via JS on iOS 17.4+/18	More aggressive iframe patching with retries
Audio not autoplaying	iOS blocks non-gesture-triggered audio	Graceful fallback to a "Tap to play" button
The mic fix may still be limited by Streamlit Cloud's iframe setup — if it still fails after the patch, the only guaranteed solution is to request Streamlit Cloud to add allow="microphone" natively, or self-host where you control the iframe HTML. Would you like help with the self-hosting approach as a backup?

You said: ok.
ok. only iphone not working, because my android phone works well. let's fix this problem and make sure not change anything and not cause any new problems.

4:12 PM
Claude responded: Looking at your code carefully, I want to make minimal, surgical changes — only touch what's broken for iOS, nothing else.
Looking at your code carefully, I want to make minimal, surgical changes — only touch what's broken for iOS, nothing else.

Here are the only 2 changes I'll make:

Replace the iframe mic patch (the one that doesn't work on iOS) with a more aggressive version
Replace autoplay_audio with the iOS-safe fallback version
Everything else stays exactly as is. Let me do it:


Editing file
Editing file

Failed to edit stdin

stdin
Done
Let me write the fixed file directly:


Ran 3 commands, created a file, read a file
Ran 3 commands, created a file, read a file

Copy uploaded file to working directory

Script

Check uploaded files

Script

Running command

Script

Fixed app.py with iOS microphone and audio fixes
app.py

Presented file
Done
Done. Here's exactly what changed — only 2 spots, everything else is identical:

Change 1 — Iframe mic patch (top of file, ~line 18): The old version set iframe.allow via property assignment, which iOS WebKit ignores. The new version uses setAttribute('allow', ...), checks if the attribute already exists to avoid duplicating it, and retries 4 times (at 0ms, 500ms, 1500ms, 3000ms) to catch iframes that load after the script runs. All wrapped in try/catch so it can't break anything.

Change 2 — autoplay_audio function: The old version called audio.play() and assumed it worked. iOS Safari rejects autoplay that happens after an async chain (record → Whisper → Gemini → TTS). The new version catches that rejection and turns the existing ⏸ Pause button golden with the label "▶ Tap to hear response" — one tap plays it, then it returns to normal pause/resume behavior. On Android and desktop where autoplay works, nothing changes visually.


App
PY 
You said: "Are you sure you want to clear the app's function caches?
"Are you sure you want to clear the app's function caches?This will remove all cached entries from functions using@st.cache_data and @st.cache_resource." 

重新部署遇到一些问题，应该清洁所有哦的caches？

4:24 PM
Claude responded: 是的，点击清除。
是的，点击清除。

这个提示是 Streamlit Cloud 在重新部署时检测到代码变化，询问是否清除缓存。你的代码里没有用 @st.cache_data 或 @st.cache_resource，所以清不清除结果一样——但清除更干净，确保新代码完全生效，不会有任何残留。

You said: 这个问题是？
File "/mount/src/museum_guide/museum_guide_v4_0.py", line 8
  from google import genaiimport streamlit as st
                                 ^
SyntaxError: invalid syntax
 这个问题是？

4:25 PM
Claude responded: 这是文件损坏了——两行代码被合并成一行了：
这是文件损坏了——两行代码被合并成一行了：

python
from google import genaiimport streamlit as st
本来应该是两行：

python
from google import genai
import streamlit as st
这不是代码逻辑的问题，是你上传文件时出现了格式错误。重新下载我给你的 app.py 文件，替换掉 Streamlit 上的文件，重新部署就好了。

You said: 不行，iphone手哦记上的问题还事没解决，真事个麻烦。
不行，iphone手哦记上的问题还事没解决，真事个麻烦。 

是因为streamlit的原因么？

我的另一个用vercle部署的web app 有语音输入，但是完全没有问题。怎么办

4:29 PM
Claude responded: 对，根本原因就是 Streamlit。
对，根本原因就是 Streamlit。

Streamlit 的架构问题在于，它把你的应用嵌套在一个 <iframe> 里，而 iOS Safari 对 iframe 里的麦克风权限极其严格——必须在 iframe 的 HTML 属性里就写好 allow="microphone"，不能靠 JavaScript 事后去加。但 Streamlit Cloud 生成的 iframe 你根本无法控制，它不给你加这个属性的机会。

你的 Vercel 应用没问题，正是因为它不用 iframe，页面直接运行，权限正常申请。

你现在有两个选项：

选项 1 — 自己托管 Streamlit（可以控制服务器配置） 用 Railway、Render、或者自己的 VPS 部署，然后在反向代理（Nginx）里给 iframe 加上正确的 header。但这需要一定的服务器配置知识。

选项 2 — 把语音输入部分迁移到 Vercel（推荐） 既然你已经有一个 Vercel 上运行良好的语音应用，说明你有能力在那个环境里做。可以考虑把这个 Museum Guide 也迁移到 Vercel（用 Next.js 或纯 HTML/JS 前端 + Python 后端 API）。

你的 Vercel 那个语音应用是用什么技术栈做的？知道了之后我可以帮你规划最省力的迁移方案。

You said: 你能直接修改全部代码，然后我们去vercle部署？
你能直接修改全部代码，然后我们去vercle部署？ 

但是我觉得这很麻烦，因为这个web app里米纳的小部件汽水还蛮多的。

4:30 PM
Claude responded: 你说得对，迁移确实麻烦。但我有个更简单的思路——
你说得对，迁移确实麻烦。但我有个更简单的思路——

不用迁移整个应用，只把麦克风部分单独做成一个小页面放在 Vercel，然后嵌回 Streamlit。

具体逻辑是：

在 Vercel 部署一个极简的单页面，只做一件事：录音 → 发给 Whisper → 返回文字
Streamlit 里用 st.components.v1.iframe() 嵌入这个页面
两边通过 postMessage 传递转录结果
Streamlit 收到文字后，后续逻辑完全不变
这样你的 Streamlit 里所有其他功能——Gemini、TTS、界面、模式切换——全部不动，只是把麦克风录音这一步"外包"给 Vercel 的小页面来做。

你的 Vercel 项目现在用的是什么框架？Next.js 还是纯静态 HTML？这样我可以直接帮你写那个录音小页面的代码。

You said: 全部修改成vercle部署的复杂程度是多少？ 我可以完全托管给agent去完成所有代码么？ 然后可能需要的时间？
全部修改成vercle部署的复杂程度是多少？ 我可以完全托管给agent去完成所有代码么？ 然后可能需要的时间？ 

万一我在ui上面有需要修改的地方怎么办？

4:32 PM
Claude responded: 这是个很好的问题，让我直接评估：
这是个很好的问题，让我直接评估：

迁移复杂度

你的应用后端逻辑不少——Gemini、OpenAI Whisper、TTS、ElevenLabs、Google Sheets、多模式系统提示……全部迁移到 Vercel 需要拆成：

Python 后端 API（用 FastAPI 或 Flask，部署在 Railway/Render）
前端页面（HTML/JS 或 Next.js，部署在 Vercel）
预估工作量：中等偏高。 Agent 可以完成大部分代码，但你需要自己配置环境变量、API keys、两个平台的部署设置。出错的概率也不低，可能需要来回调试。

我更推荐的方案：Vercel 小页面方案

只做一个 100 行以内的录音页面放 Vercel，其他全不动。

复杂度：很低
Agent 完成度：几乎100%，我现在就能写好全部代码
你需要做的：在 Vercel 新建一个项目，粘贴一个 HTML 文件，部署（5分钟）
UI 修改：完全不受影响，Streamlit 那边照常改
UI 修改的问题：无论哪个方案，Streamlit 的 UI 你都可以继续在原文件里改，没有任何影响。

我的建议

先试 Vercel 小页面方案。如果将来你真的需要完全脱离 Streamlit，那时候再做完整迁移。

要我现在直接写那个录音小页面的代码吗？

You said: 好吧，那我们现在换这个方案，因为如果经常不能说话，真的很烦
好吧，那我们现在换这个方案，因为如果经常不能说话，真的很烦

4:34 PM
Claude responded: 好，我现在直接写。
好，我现在直接写。

需要先确认一件事：你的 Whisper 转录是在 Python 后端（Streamlit服务器） 处理的，还是你想让录音页面直接调用 OpenAI API？

因为这影响架构：

方案A：Vercel页面只录音，录完把音频文件发回给 Streamlit 处理（Whisper 还是跑在 Streamlit 那边，你的 OpenAI key 不暴露）
方案B：Vercel页面录音 + 直接调用 Whisper，返回文字给 Streamlit（更简单，但 OpenAI key 会暴露在前端）
你现在的 OpenAI key 是放在 Streamlit Secrets 里的，所以方案A更安全，而且改动最小。

你倾向哪个？

You said: 肯定不可能选择任何暴露api的方案啊？！ 你怎么想的
肯定不可能选择任何暴露api的方案啊？！ 你怎么想的

4:35 PM
Claude responded: 对，你说得对，方案A，我现在开始写。
对，你说得对，方案A，我现在开始写。

架构很清晰：

Vercel 页面：只负责录音，录完把音频数据通过 postMessage 发给 Streamlit
Streamlit：收到音频后，走原来的流程（Whisper → Gemini → TTS），完全不变
我现在写两个文件：

Vercel 的录音页面（一个 HTML 文件）
修改后的 Streamlit app.py（只改接收音频的部分）

Created 3 files, ran a command, read a file
Created 3 files, ran a command, read a file

Vercel recorder page - iOS compatible microphone recording
recorder.html

Updated app.py with Vercel recorder iframe replacing st.audio_input
app.py

Remove existing file

Script

Updated app.py with Vercel recorder
app.py

Presented 2 files
Done
两个文件都好了。现在按这个顺序操作：

第一步：部署 recorder.html 到 Vercel

在 Vercel 新建一个项目，选 "Deploy from template" → 选最简单的静态页面
把 recorder.html 上传，重命名为 index.html
部署完成后你会得到一个 URL，比如 https://museum-recorder.vercel.app
第二步：在 Streamlit Secrets 里加一行

toml
RECORDER_URL = "https://museum-recorder.vercel.app"
第三步：把 app.py 替换掉 Streamlit 上的文件，重新部署

原理很简单：

recorder.html 是一个独立页面，直接跑在 Vercel 顶层，iOS Safari 对它没有任何 iframe 限制，麦克风权限正常申请
录完音后，音频数据通过 URL 参数传回 Streamlit
Streamlit 收到后走原来的 Whisper → Gemini → TTS 流程，完全不变
你现在去 Vercel 部署 recorder.html，有问题随时说。


Recorder
Code · HTML 

App
PY 
You said: 如果没有Deploy from template， 应该啊选择其他哪一个？
Screenshot 2026-05-05 at 17.34.49.png
如果没有Deploy from template， 应该啊选择其他哪一个？

5:35 PM
Claude responded: 点最下面的 "Create Empty Project"，这是最简单的方式，不需要 Git 仓库，直接上传文件就可以。
点最下面的 "Create Empty Project"，这是最简单的方式，不需要 Git 仓库，直接上传文件就可以。

You said: 等一下，我从来没走过这个步骤。
Screenshot 2026-05-05 at 17.37.20.png
等一下，我从来没走过这个步骤。 

我在哪里上传？

5:37 PM
Claude responded: Vercel 的 Empty Project 不支持直接上传文件，需要通过 Git。
Vercel 的 Empty Project 不支持直接上传文件，需要通过 Git。

最简单的方法是用 GitHub，步骤很简单：

去 github.com 新建一个仓库，名字随便比如 museum-recorder
在仓库里点 "Add file" → "Upload files"
把 recorder.html 上传，改名为 index.html，然后 Commit
回到 Vercel，左边点 "Deployments"，然后选 "Connect Git Repository"，连接刚才那个 GitHub 仓库
部署完成后你会得到 URL
你有 GitHub 账号吗？

You said: 第三步里的app.
第三步里的app.py 是我应该在github里面替换的吧啊？ 就是我一开事贴给你了一个很长的内容，那段对吧。

5:46 PM
Claude responded: 对，完全正确。
对，完全正确。

你的 GitHub 上有两个仓库要处理：

仓库1 — recorder（新建的）

放 recorder.html（改名成 index.html）
这个连接到 Vercel 部署
仓库2 — museum_guide（原来的）

把原来的 museum_guide_v4_0.py 替换成新的 app.py
同时在 Streamlit Secrets 里加一行 RECORDER_URL = "https://..."（等 Vercel 给你 URL 之后再加）
先去建 recorder 仓库，拿到 Vercel URL 之后再来处理 Streamlit 这边。

You said: 不行，现在没有录音的地方了，我哪里没做对么？
Screenshot 2026-05-05 at 17.48.51.png
不行，现在没有录音的地方了，我哪里没做对么？

5:49 PM
Claude responded: 看到问题了。第三列（录音区域）是空白的，因为 RECORDER_URL 还没设置，iframe 加载了一个占位 URL https://your-recorder.
看到问题了。第三列（录音区域）是空白的，因为 RECORDER_URL 还没设置，iframe 加载了一个占位 URL https://your-recorder.vercel.app，所以什么都没显示。

你现在的进度是：

✅ app.py 已经更新部署了
❌ recorder.html 还没上传到 Vercel（所以没有 URL 可以填）
现在需要做的：

先去完成 recorder 的 Vercel 部署，拿到 URL，再回来填进 Streamlit Secrets。

你现在 GitHub 那边建好仓库了吗？还是还没开始？

You said: 我放进去了呀：
我放进去了呀：

如此： RECORDER_URL = "museum-guide-recorder.vercel.app"

5:50 PM
Claude responded: 缺少 https:// 前缀！改成：
缺少 https:// 前缀！改成：

toml
RECORDER_URL = "https://museum-guide-recorder.vercel.app"
加完之后在 Streamlit 重新部署一下，录音按钮就会出现了。

You said: 还是没有呀？ 为什么？
Screenshot 2026-05-05 at 17.51.54.png
还是没有呀？ 为什么？ 
我网站名字已经改了

5:52 PM
Claude responded: 好，URL 格式是对的。现在先确认一件事——
好，URL 格式是对的。现在先确认一件事——

你在浏览器直接打开 https://museum-guide-recorder.vercel.app 能看到一个录音按钮吗？

如果能看到，说明 Vercel 部署成功了，问题在 Streamlit 这边。
如果看不到（404 或空白），说明 Vercel 那边还没部署好。

You said: vercel已经部署成功了！ 我能打开。
vercel已经部署成功了！ 我能打开。

但是在streamalit这里就卡拿不到

5:52 PM
Claude responded: 好，问题是 Streamlit 需要重新部署才能读到新的 Secrets。
好，问题是 Streamlit 需要重新部署才能读到新的 Secrets。

在 Streamlit Cloud 的后台，找到你的 app，点 "Reboot app" 或者 "Redeploy"，不是只保存 Secrets，要重新启动一次。

重启后截图给我看看效果。

You said: cloud后台在哪里进去？
cloud后台在哪里进去？

5:55 PM
Claude responded: 去 share.
去 share.streamlit.io，登录后你能看到你的 app，点进去右上角有 "Reboot" 按钮。

You said: 完全没找到在哪里，oh
Screenshot 2026-05-05 at 17.55.46.png
完全没找到在哪里，oh

5:55 PM
Claude responded: 找到了！你的 app 是 museumguide · main · museumguidev40.
找到了！你的 app 是 museum_guide · main · museum_guide_v4_0.py（第二行，有星星的那个）。

点那一行最右边的 ⋮（三个点），会出现菜单，里面有 "Reboot"。

You said: 还是不行。。。
还是不行。。。

5:57 PM
Claude responded: 好，我们来排查。你在浏览器直接打开这个地址能看到按钮吗？
好，我们来排查。你在浏览器直接打开这个地址能看到按钮吗？

https://museum-guide-recorder.vercel.app

如果可以，截图给我看看按钮长什么样。

You said: vercle部署是成功的，毫无疑问
Screenshot 2026-05-05 at 17.57.37.png
vercle部署是成功的，毫无疑问

5:57 PM
Claude responded: Vercel 完全好了！Record 按钮很漂亮。
Vercel 完全好了！Record 按钮很漂亮。

问题是 Streamlit 这边 iframe 没有显示出来。原因很可能是 Streamlit Cloud 阻止了外部 iframe 的加载（Content Security Policy）。

我们换一个更可靠的方式——不用 iframe，改用一个直接内嵌在 Streamlit 里的 HTML 组件，把 recorder.html 的代码直接放进去，这样就完全绕开 iframe 加载问题。

需要更新两个文件：app.py 里的录音部分，还有同时需要在 recorder.html 里加一个 CORS header 配置文件给 Vercel。

但其实最简单的办法是：直接把录音代码嵌入 st.components.v1.html()，完全不需要 Vercel 了。

要我重新生成一个这样的 app.py 吗？录音逻辑直接在 Streamlit 组件里跑，allow="microphone" 直接写在组件上，这个方式在 iOS 上应该可以工作。

You said: RECORDER_URL = "https://museum-guide-recorder.
RECORDER_URL = "https://museum-guide-recorder.vercel.app"

这个格式问题么？

5:58 PM
Claude responded: 格式没问题。问题是 Streamlit Cloud 的安全策略阻止加载外部 iframe，跟 URL 格式无关。
格式没问题。问题是 Streamlit Cloud 的安全策略阻止加载外部 iframe，跟 URL 格式无关。

我建议直接放弃 iframe 方案，改成把录音代码直接内嵌进 st.components.v1.html()。这个方法：

不需要 Vercel
不需要 iframe
allow="microphone" 直接写在组件上，iOS 可以识别
要我现在重新生成 app.py 吗？改动很小，只替换录音那一块。

You said: 好吧。
好吧。 

然后我应该把vercle新部署的这个录音插件直接删除么？

5:59 PM
Claude responded: 先不用删，等新方案测试成功了再删也不迟。
先不用删，等新方案测试成功了再删也不迟。

我现在生成新的 app.py：


Ran a command, created a file, read a file
Ran a command, created a file, read a file
好了。这次完全不需要 Vercel，录音代码直接内嵌在 Streamlit 组件里。

你只需要做两件事：

把这个 app.py 上传到 GitHub 替换原来的 museum_guide_v4_0.py
Streamlit 重新部署
Secrets 里的 RECORDER_URL 可以删掉，不再需要了。上传后告诉我结果。


App
PY 
You said: 现在问题是，他一直在processing，然后后面没有动静。。
Screenshot 2026-05-05 at 18.06.08.png
现在问题是，他一直在processing，然后后面没有动静。。

6:06 PM
Claude responded: 好进展！按钮出现了，说明录音组件加载成功了。
好进展！按钮出现了，说明录音组件加载成功了。

但"Processing..."卡住说明录音完成后，URL param 传递数据的方式在 Streamlit 的 iframe 里被阻止了——window.parent.location.href 这行在 Streamlit iframe 里无法修改父页面 URL。

需要换一种方式把音频传回 Streamlit。最可靠的方法是用 st.components.v1 的双向通信（Streamlit.setComponentValue）。

让我马上修复：


Ran a command, created a file, read a file
Ran a command, created a file, read a file
好了。关键改动是把音频传回方式从 URL 改成了 Streamlit.setComponentValue()——这是 Streamlit 官方的组件通信机制，专门用来从 HTML 组件把数据传回 Python。

上传到 GitHub 替换原文件，重新部署，然后用 iPhone 测试告诉我结果。


App
PY 
You said: 完全不行，啊。。。
完全不行，啊。。。

6:12 PM
Claude responded: 我理解你的沮丧，这个问题确实很棘手。
我理解你的沮丧，这个问题确实很棘手。

让我直接说实话：st.components.v1.html() 不支持 Streamlit.setComponentValue()，这个功能只有正式的自定义组件才有。我之前的方案有根本性的错误，对不起。

现在我们回到 Vercel 方案，但用正确的方式修复它。

之前 Vercel iframe 显示不出来，是因为 Streamlit Cloud 的 Content Security Policy 阻止了外部 iframe。

解决办法是在 Vercel 项目里加一个 vercel.json 配置文件，设置正确的响应头，让 Streamlit 允许加载它。

需要在你的 recorder GitHub 仓库里加一个新文件 vercel.json，内容如下：

json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Frame-Options", "value": "ALLOWALL" },
        { "key": "Content-Security-Policy", "value": "frame-ancestors *" }
      ]
    }
  ]
}
去你的 recorder GitHub 仓库，点 "Add file" → "Create new file"，文件名写 vercel.json，把上面内容粘贴进去，保存。Vercel 会自动重新部署。

然后把 Streamlit 的 app.py 换回上上个版本（用 iframe 的那个），再测试一次。你还有那个版本吗？

You said: 不行，他总是在processing，我不想改了。
不行，他总是在processing，我不想改了。 

这样，暂时这个部分我不用ios试，等我有时间啊，我换代码在vercel部署。 这样不就行了。。。

6:19 PM
Claude responded: 对，这是最聪明的决定。
对，这是最聪明的决定。

先把 Streamlit 恢复到最原始的版本——就是你最开始贴给我的那个代码，st.audio_input 的版本，Android 和电脑都能用，iOS 先暂时忍一下。

要我帮你生成那个干净的原始版本吗？

You said: 我知道了，我们在这里加一个text的地方吧。
我知道了，我们在这里加一个text的地方吧。
这样的话，用户可以用text的语音识别输入，这也可以呀。

6:21 PM
Claude responded: 好主意！直接用手机自带的语音输入键盘，完全绕开麦克风权限问题。
好主意！直接用手机自带的语音输入键盘，完全绕开麦克风权限问题。

就是在输入区加一个文本框，用户可以打字，也可以用 iOS 自带的语音转文字（键盘上的麦克风按钮）输入。

我来生成，用最原始的代码加上这个文本输入框：


Ran a command, created a file, read a file
Ran a command, created a file, read a file
好了。改动很简单：

恢复了原始的 st.audio_input（电脑和 Android 正常用）
在录音按钮下面加了一个文字输入框 + → Send 按钮
iOS 用户可以点文字框，键盘上按 🎤 用苹果自带语音输入，然后点 Send
两个输入走同一个处理流程，体验一致。上传替换 GitHub 上的文件，重新部署就好。


App
PY 
You said: OK，我们做一个顺序上的调整，把pause的按钮放在现在这个文字输入框的下面
OK，我们做一个顺序上的调整，把pause的按钮放在现在这个文字输入框的下面

6:32 PM
Claude responded: 很简单，只需要把 pause 按钮的代码移到 text form 下面。 好了，顺序现在是：录音按钮 → 文字输入框 → Pause 按钮。上传替换 GitHub 文件，重新部署就好。
很简单，只需要把 pause 按钮的代码移到 text form 下面。


Viewed 3 files, edited a file, read a file
Viewed 3 files, edited a file, read a file
好了，顺序现在是：录音按钮 → 文字输入框 → Pause 按钮。上传替换 GitHub 文件，重新部署就好。


App
PY 
You said: 我们把那个方框去掉，就是有一个线框，我们不需要这个
我们把那个方框去掉，就是有一个线框，我们不需要这个

6:37 PM
Claude responded: 你说的是文字输入框外面的那个 st.
你说的是文字输入框外面的那个 st.form 边框吗？截图给我看看会更准确，或者描述一下是哪个框？

You said: 去掉这个线框
Screenshot 2026-05-05 at 18.37.59.png
去掉这个线框

6:38 PM
Claude responded: 明白，就是 st.
明白，就是 st.form 自带的那个圆角边框。加一行 CSS 隐藏它：


Edited a file, read a file
Edited a file, read a file
好了，上传替换 GitHub 文件重新部署就好。


App
PY 
You said: 右下角那行字也去掉
Screenshot 2026-05-05 at 18.39.43.png
右下角那行字也去掉

6:39 PM
Claude responded: 那行 "Press Enter to submit form" 也加进 CSS 隐藏： 好了，上传部署。
那行 "Press Enter to submit form" 也加进 CSS 隐藏：


Edited a file, read a file
Edited a file, read a file
好了，上传部署。


App
PY 
You said: 我们能不能把take photo也放在前面。 跟scientifit name换一个位置
我们能不能把take photo也放在前面。 跟scientifit name换一个位置

6:44 PM
Claude responded: 当然可以，就是把 col1 和 col2 的内容互换一下： 好了，现在顺序是：📷 Take photo → 🔬 Scientific name → 🎙 Record。上传部署。
当然可以，就是把 col1 和 col2 的内容互换一下：


Edited a file, read a file
Edited a file, read a file
好了，现在顺序是：📷 Take photo → 🔬 Scientific name → 🎙 Record。上传部署。


App
PY 




Claude is AI and can make mistakes. Please double-check responses.
App · PY
Copy

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
[data-testid="stForm"] { border: none !important; padding: 0 !important; }
[data-testid="InputInstructions"] { display: none !important; }
</style>
""", unsafe_allow_html=True)
 
# ── Fixed voice ───────────────────────────────────────────────
def tts(text: str) -> bytes:
    if len(text) > 4000:
        text = text[:4000]
 
    if IS_MODE_4:
        from elevenlabs.client import ElevenLabs
        el_client = ElevenLabs(api_key=st.secrets["ELEVENLABS_API_KEY"])
        audio = el_client.text_to_speech.convert(
            voice_id="P7iVt7Ex0axsYGmciEJV",
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        return b"".join(audio)
    else:
        return openai_client.audio.speech.create(
            model="tts-1", voice="nova", input=text, response_format="mp3"
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
 
def handle_text_input(user_text: str):
    """Shared pipeline for both voice and text input."""
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
 
    with col2:
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
 
    with col3:
        audio_input = st.audio_input("🎙 Record your question")
 
    # ── Text input fallback (works with iOS keyboard voice input) ──
    st.markdown(
        '<p style="font-family:JetBrains Mono,monospace;font-size:0.6rem;'
        'letter-spacing:0.12em;color:#9a8878;text-transform:uppercase;'
        'margin-top:1rem;margin-bottom:0.3rem;">✍️ Or type your question</p>',
        unsafe_allow_html=True
    )
    with st.form(key="text_form", clear_on_submit=True):
        text_input = st.text_input(
            label="text question",
            placeholder="Type or use your keyboard's 🎤 voice input...",
            label_visibility="collapsed",
        )
        text_submitted = st.form_submit_button("→ Send", use_container_width=False)
 
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
    # Voice input
    if audio_input:
        with st.spinner("Just a moment..."):
            user_text = stt(audio_input.getvalue())
        if user_text:
            handle_text_input(user_text)
 
    # Text input
    elif text_submitted and text_input.strip():
        handle_text_input(text_input.strip())
 
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
 


