import base64
import hashlib
import html
import io
import json
import math
import os
import struct
import time
import uuid
import wave
from datetime import datetime, timedelta, timezone
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from cryptography.fernet import Fernet

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None


# ==============================
# CONFIG
# ==============================
APP_TITLE = "ChatSecrets Terminal"
APP_ICON = "🟢"
FERNET_KEY_FILE = "fernet.key"
CHAT_FILE = "chat_rooms.json"
ONLINE_FILE = "online_status.json"
WIB = timezone(timedelta(hours=7))

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="centered")


# ==============================
# CSS: MAIN STREAMLIT PAGE
# ==============================
APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

:root {
    --terminal-green: #00ff66;
    --terminal-cyan: #00ddff;
    --terminal-dark: #020403;
    --terminal-panel: rgba(0, 20, 8, 0.92);
    --terminal-dim: #6dff9a;
    --danger: #ff275f;
}

.stApp {
    background:
        radial-gradient(circle at top, rgba(0,255,102,0.14), transparent 35%),
        linear-gradient(180deg, #020403 0%, #000000 100%);
    color: var(--terminal-green);
    font-family: 'Share Tech Mono', monospace;
}

.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background: repeating-linear-gradient(
        to bottom,
        rgba(255,255,255,0.025) 0px,
        rgba(255,255,255,0.025) 1px,
        transparent 2px,
        transparent 4px
    );
    z-index: 9999;
    mix-blend-mode: overlay;
}

.stApp::after {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    box-shadow: inset 0 0 130px rgba(0, 255, 102, 0.14);
    z-index: 9998;
}

.block-container {
    max-width: 980px;
    padding-top: 2rem;
    padding-bottom: 2rem;
}

h1, h2, h3, p, label, span, div, button, input, textarea {
    font-family: 'Share Tech Mono', monospace !important;
}

h1 {
    color: var(--terminal-green);
    text-shadow: 0 0 8px var(--terminal-green), 0 0 20px rgba(0,255,102,.7);
    letter-spacing: 2px;
    border-bottom: 1px solid rgba(0,255,102,.75);
    padding-bottom: 12px;
    margin-bottom: 18px;
}

h1::before {
    content: "root@AntiTrust:~$ ";
    color: var(--terminal-dim);
    font-size: 0.52em;
}

h2, h3 {
    color: var(--terminal-green);
    text-shadow: 0 0 8px rgba(0,255,102,.65);
}

.stTextInput input {
    background: #000 !important;
    color: var(--terminal-green) !important;
    border: 1px solid var(--terminal-green) !important;
    border-radius: 0 !important;
    box-shadow: 0 0 12px rgba(0,255,102,.24);
}

.stTextInput input:focus {
    box-shadow: 0 0 20px rgba(0,255,102,.72) !important;
    border-color: #9cffb8 !important;
}

.stButton button,
.stFormSubmitButton button {
    background: #001a08 !important;
    color: var(--terminal-green) !important;
    border: 1px solid var(--terminal-green) !important;
    border-radius: 0 !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    box-shadow: 0 0 12px rgba(0,255,102,.25);
    transition: all .15s ease-in-out;
}

.stButton button:hover,
.stFormSubmitButton button:hover {
    background: var(--terminal-green) !important;
    color: #000 !important;
    box-shadow: 0 0 24px rgba(0,255,102,.85);
}

.stAlert {
    background: rgba(0, 25, 8, 0.88) !important;
    color: var(--terminal-green) !important;
    border: 1px solid rgba(0,255,102,.55) !important;
    border-radius: 0 !important;
    box-shadow: 0 0 14px rgba(0,255,102,.18);
}

.terminal-panel {
    background: var(--terminal-panel);
    border: 1px solid var(--terminal-green);
    box-shadow: 0 0 24px rgba(0,255,102,.24);
    padding: 18px;
    margin: 18px 0 24px 0;
    position: relative;
}

.terminal-panel::before {
    content: "ACCESS TERMINAL // ENCRYPTED SESSION";
    position: absolute;
    top: -12px;
    left: 14px;
    background: #020403;
    color: var(--terminal-green);
    padding: 0 8px;
    font-size: 12px;
    letter-spacing: 1px;
}

.status-line {
    color: var(--terminal-dim);
    margin: 4px 0;
}

hr {
    border: none;
    border-top: 1px dashed rgba(0,255,102,.5);
}

::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: var(--terminal-green); }

.cursor-blink {
    display: inline-block;
    width: 9px;
    height: 18px;
    background: var(--terminal-green);
    margin-left: 4px;
    animation: blink 0.9s infinite;
}

@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}
</style>
"""


# ==============================
# CSS: CHAT COMPONENT IFRAME
# ==============================
CHAT_COMPONENT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

html, body {
    margin: 0;
    padding: 0;
    background: transparent;
    font-family: 'Share Tech Mono', monospace;
}

.chat-box {
    height: 430px;
    overflow-y: auto;
    box-sizing: border-box;
    background: rgba(0, 0, 0, 0.94);
    border: 1px solid #00ff66;
    padding: 16px;
    box-shadow: inset 0 0 24px rgba(0,255,102,.14), 0 0 18px rgba(0,255,102,.2);
    color: #00ff66;
}

.chat-box::before {
    content: "CHAT LOG // LIVE FEED";
    display: block;
    color: #6dff9a;
    border-bottom: 1px dashed rgba(0,255,102,.45);
    padding-bottom: 8px;
    margin-bottom: 10px;
    letter-spacing: 1px;
}

.sound-panel {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 9px 10px;
    margin-bottom: 10px;
    border: 1px dashed rgba(0,255,102,.45);
    background: rgba(0, 255, 102, 0.04);
    color: rgba(120,255,165,.88);
    font-size: 12px;
}

.sound-panel button {
    background: #001a08;
    color: #00ff66;
    border: 1px solid #00ff66;
    padding: 6px 9px;
    cursor: pointer;
    font-family: 'Share Tech Mono', monospace;
    text-transform: uppercase;
}

.sound-panel button:hover {
    background: #00ff66;
    color: #000;
}

.chat-bubble {
    background: transparent;
    border-left: 3px solid #00ff66;
    padding: 10px 12px;
    margin: 10px 0;
    color: #00ff66;
    text-shadow: 0 0 6px rgba(0,255,102,.65);
    word-wrap: break-word;
    overflow-wrap: anywhere;
}

.chat-bubble::before {
    content: "> ";
    color: #9cffb8;
}

.chat-bubble.me {
    border-left-color: #00ddff;
    color: #8ff3ff;
    text-shadow: 0 0 6px rgba(0,204,255,.65);
}

.chat-bubble.me::before {
    content: "$ ";
    color: #8ff3ff;
}

.chat-message-text {
    display: inline;
    white-space: normal;
}

.chat-meta {
    font-size: 12px;
    color: rgba(120,255,165,.75);
    margin-top: 6px;
}

.empty-line {
    color: rgba(120,255,165,.75);
    margin-top: 14px;
}

::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: #00ff66; }
"""


# ==============================
# STORAGE + CRYPTO HELPERS
# ==============================
def load_json(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return {}


def save_json(path: str, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def get_fernet() -> Fernet:
    if not os.path.exists(FERNET_KEY_FILE):
        key = Fernet.generate_key()
        with open(FERNET_KEY_FILE, "wb") as file:
            file.write(key)
    else:
        with open(FERNET_KEY_FILE, "rb") as file:
            key = file.read()

    return Fernet(key)


def encrypt_message(text: str) -> str:
    return get_fernet().encrypt(text.encode()).decode()


def decrypt_message(text: str) -> str:
    try:
        return get_fernet().decrypt(text.encode()).decode()
    except Exception:
        return "[Pesan tidak dapat didekripsi]"


def wib_now() -> str:
    return datetime.now(WIB).strftime("%H:%M")


# ==============================
# CHAT HELPERS
# ==============================
def make_message(username: str, text: str) -> dict[str, str]:
    return {
        "id": str(uuid.uuid4()),
        "username": username,
        "text": encrypt_message(text),
        "time": wib_now(),
    }


def get_message_signature(messages: list[dict[str, Any]]) -> str:
    if not messages:
        return "empty"

    latest = messages[-1]
    raw = "|".join([
        str(len(messages)),
        str(latest.get("id", "")),
        str(latest.get("username", "")),
        str(latest.get("time", "")),
        str(latest.get("text", "")),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def should_play_incoming_sound(
    messages: list[dict[str, Any]],
    current_username: str,
    sound_enabled: bool,
) -> bool:
    current_signature = get_message_signature(messages)
    previous_signature = st.session_state.get("last_message_signature")
    st.session_state.last_message_signature = current_signature

    if not sound_enabled or not messages or previous_signature is None:
        return False

    latest_sender = str(messages[-1].get("username", ""))
    return current_signature != previous_signature and latest_sender != current_username


def render_chat_messages(messages: list[dict[str, Any]], current_username: str) -> str:
    if not messages:
        return '<div class="empty-line">[LOG] Belum ada pesan. Kirim command pertama...</div>'

    chat_parts: list[str] = []
    for msg in messages:
        is_me = msg.get("username") == current_username
        bubble_class = "chat-bubble me" if is_me else "chat-bubble"
        owner = " (Anda)" if is_me else ""

        safe_text = html.escape(decrypt_message(str(msg.get("text", ""))), quote=True).replace("\n", "<br>")
        safe_user = html.escape(str(msg.get("username", "unknown")), quote=True)
        safe_time = html.escape(str(msg.get("time", "")), quote=True)

        chat_parts.append(
            f'<div class="{bubble_class}">'
            f'<div class="chat-message-text">{safe_text}</div>'
            f'<div class="chat-meta">{safe_user}{owner} // {safe_time}</div>'
            f'</div>'
        )

    return "".join(chat_parts)


def render_chat_box(
    messages: list[dict[str, Any]],
    current_username: str,
    play_incoming_sound: bool,
    sound_enabled: bool,
    sound_data_uri: str,
) -> str:
    body = render_chat_messages(messages, current_username)
    play_flag = "true" if play_incoming_sound else "false"
    escaped_sound_src = html.escape(sound_data_uri, quote=True)
    sound_panel = """
        <div class="sound-panel" id="soundPanel">
            <span id="soundStatus">[AUDIO] Klik unlock untuk mengaktifkan suara pesan masuk.</span>
            <button id="unlockSound" type="button">Unlock Sound</button>
        </div>
    """ if sound_enabled else """
        <div class="sound-panel">
            <span>[AUDIO] Suara pesan masuk dimatikan dari sidebar.</span>
        </div>
    """

    return f"""
    <!doctype html>
    <html>
    <head>
        <style>{CHAT_COMPONENT_CSS}</style>
    </head>
    <body>
        <div class="chat-box" id="chatBox">
            {sound_panel}
            {body}
        </div>
        <script>
            const shouldPlay = {play_flag};
            const beepSrc = "{escaped_sound_src}";
            const chatBox = document.getElementById('chatBox');
            const unlockButton = document.getElementById('unlockSound');
            const soundStatus = document.getElementById('soundStatus');

            function setSoundStatus() {{
                if (!soundStatus) return;
                const unlocked = localStorage.getItem('chatsecrets_sound_unlocked') === 'yes';
                soundStatus.textContent = unlocked
                    ? '[AUDIO] Suara aktif. Incoming packet akan berbunyi.'
                    : '[AUDIO] Klik unlock untuk mengaktifkan suara pesan masuk.';
            }}

            function playHackerTone() {{
                try {{
                    const audio = new Audio(beepSrc);
                    audio.volume = 0.75;
                    const promise = audio.play();
                    if (promise !== undefined) {{
                        promise.catch(() => playOscillatorFallback());
                    }}
                }} catch (error) {{
                    playOscillatorFallback();
                }}
            }}

            function playOscillatorFallback() {{
                try {{
                    const AudioContext = window.AudioContext || window.webkitAudioContext;
                    if (!AudioContext) return;

                    const ctx = new AudioContext();
                    const master = ctx.createGain();
                    master.gain.setValueAtTime(0.0001, ctx.currentTime);
                    master.gain.exponentialRampToValueAtTime(0.11, ctx.currentTime + 0.025);
                    master.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.42);
                    master.connect(ctx.destination);

                    const notes = [740, 990, 520, 1180];
                    notes.forEach((frequency, index) => {{
                        const osc = ctx.createOscillator();
                        const gain = ctx.createGain();
                        const start = ctx.currentTime + index * 0.09;
                        const end = start + 0.075;

                        osc.type = index % 2 ? 'square' : 'sawtooth';
                        osc.frequency.setValueAtTime(frequency, start);
                        gain.gain.setValueAtTime(0.0001, start);
                        gain.gain.exponentialRampToValueAtTime(0.32, start + 0.012);
                        gain.gain.exponentialRampToValueAtTime(0.0001, end);

                        osc.connect(gain);
                        gain.connect(master);
                        osc.start(start);
                        osc.stop(end + 0.02);
                    }});

                    setTimeout(() => ctx.close(), 700);
                }} catch (error) {{}}
            }}

            if (unlockButton) {{
                unlockButton.addEventListener('click', () => {{
                    localStorage.setItem('chatsecrets_sound_unlocked', 'yes');
                    setSoundStatus();
                    playHackerTone();
                }});
            }}

            setSoundStatus();
            chatBox.scrollTop = chatBox.scrollHeight;

            if (shouldPlay && localStorage.getItem('chatsecrets_sound_unlocked') === 'yes') {{
                setTimeout(playHackerTone, 120);
            }}
        </script>
    </body>
    </html>
    """


def append_message(room: str, username: str, message_text: str) -> None:
    rooms = load_json(CHAT_FILE)
    rooms.setdefault(room, [])
    rooms[room].append(make_message(username, message_text))
    save_json(CHAT_FILE, rooms)



# ==============================
# AUDIO HELPERS
# ==============================
def build_hacker_wav_data_uri() -> str:
    """Generate a short hacker-style beep as an inline WAV data URI.

    This avoids relying on external audio files and works offline.
    """
    sample_rate = 44100
    notes = [740, 990, 520, 1180]
    note_duration = 0.085
    gap_duration = 0.025
    volume = 0.28

    samples: list[int] = []
    for note_index, frequency in enumerate(notes):
        total_note_samples = int(sample_rate * note_duration)
        for i in range(total_note_samples):
            t = i / sample_rate
            # quick attack and release, so the sound feels like a terminal alert
            attack = min(1.0, i / max(1, int(sample_rate * 0.012)))
            release = min(1.0, (total_note_samples - i) / max(1, int(sample_rate * 0.025)))
            envelope = max(0.0, min(attack, release))

            # mix sine + slight square-ish harmonic for a digital tone
            sine = math.sin(2 * math.pi * frequency * t)
            harmonic = 0.35 * math.sin(2 * math.pi * frequency * 2 * t)
            value = int(32767 * volume * envelope * (sine + harmonic) / 1.35)
            samples.append(value)

        samples.extend([0] * int(sample_rate * gap_duration))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:audio/wav;base64,{encoded}"


HACKER_SOUND_DATA_URI = build_hacker_wav_data_uri()


def render_page_sound_trigger(sound_data_uri: str) -> str:
    """Play sound from a tiny page-level component as a fallback.

    Streamlit re-creates the chat iframe on rerun, so this trigger helps the
    audio play even when the chat component's previous AudioContext was lost.
    """
    escaped_src = html.escape(sound_data_uri, quote=True)
    return f"""
    <!doctype html>
    <html>
    <body style="margin:0;padding:0;background:transparent;">
        <audio id="incomingSound" src="{escaped_src}" preload="auto" autoplay></audio>
        <script>
            const audio = document.getElementById('incomingSound');
            audio.volume = 0.75;

            function webAudioFallback() {{
                try {{
                    const AudioContext = window.AudioContext || window.webkitAudioContext;
                    if (!AudioContext) return;
                    const ctx = new AudioContext();
                    const master = ctx.createGain();
                    master.gain.setValueAtTime(0.0001, ctx.currentTime);
                    master.gain.exponentialRampToValueAtTime(0.12, ctx.currentTime + 0.025);
                    master.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.42);
                    master.connect(ctx.destination);

                    [740, 990, 520, 1180].forEach((frequency, index) => {{
                        const osc = ctx.createOscillator();
                        const gain = ctx.createGain();
                        const start = ctx.currentTime + index * 0.09;
                        const end = start + 0.075;
                        osc.type = index % 2 ? 'square' : 'sawtooth';
                        osc.frequency.setValueAtTime(frequency, start);
                        gain.gain.setValueAtTime(0.0001, start);
                        gain.gain.exponentialRampToValueAtTime(0.3, start + 0.012);
                        gain.gain.exponentialRampToValueAtTime(0.0001, end);
                        osc.connect(gain);
                        gain.connect(master);
                        osc.start(start);
                        osc.stop(end + 0.02);
                    }});
                    setTimeout(() => ctx.close(), 700);
                }} catch (error) {{}}
            }}

            const playPromise = audio.play();
            if (playPromise !== undefined) {{
                playPromise.catch(() => webAudioFallback());
            }} else {{
                webAudioFallback();
            }}
        </script>
    </body>
    </html>
    """

# ==============================
# UI HELPERS
# ==============================
def render_header() -> None:
    st.markdown(
        """
        <h1>~/.Ch4t53cr3T <span class="cursor-blink"></span></h1>
        <div class="terminal-panel">
            <p class="status-line">[BOOT] Secure channel initialized... Dark Mode are recommended.. Screen must be on.. <span class="cursor-blink"></span></h1></p>
            <p class="status-line">[CRYPTO] Fernet encryption active..<span class="cursor-blink"></span></h1></p>
            <p class="status-line">[MODE] Private multi-room communication..<span class="cursor-blink"></span></h1></p>
            <p class="status-line">[WARNING] Destroy room after use for maximum privacy..<span class="cursor-blink"></span></h1></p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> tuple[bool, int, bool, bool]:
    with st.sidebar:
        st.markdown("### SYSTEM CONTROL")
        auto_refresh_enabled = st.toggle("Aktifkan auto refresh", value=True)
        refresh_seconds = st.slider("Interval refresh", min_value=2, max_value=15, value=3, step=1)
        sound_enabled = st.toggle("Suara pesan masuk", value=True)
        test_sound_requested = st.button("Test Hacker Sound", use_container_width=True)
        st.caption("Klik Test Hacker Sound sekali. Setelah browser mengizinkan audio, pesan masuk dari user lain akan berbunyi otomatis.")
        st.caption("Matikan auto-refresh sementara kalau sedang mengetik pesan panjang.")

    return auto_refresh_enabled, refresh_seconds, sound_enabled, test_sound_requested


def update_online_status(room: str, username: str) -> list[str]:
    online = load_json(ONLINE_FILE)
    now_epoch = int(time.time())

    online.setdefault(room, {})
    online[room][username] = now_epoch
    save_json(ONLINE_FILE, online)

    return [
        user for user, last_seen in online.get(room, {}).items()
        if user != username and now_epoch - int(last_seen) <= 10
    ]


def render_destroy_room(room: str) -> None:
    with st.expander("Destroy Chat Room", expanded=False):
        secret_key = f"destroy_secret_{room}"
        if secret_key not in st.session_state:
            st.session_state[secret_key] = ""

        new_secret = st.text_input("Set kode destroy minimal 6 karakter:", type="password")
        if st.button("Set Destroy Code"):
            if len(new_secret) >= 6:
                st.session_state[secret_key] = new_secret
                st.success("Kode destroy berhasil disimpan untuk room ini.")
            else:
                st.error("Kode destroy minimal 6 karakter.")

        destroy_key = st.text_input("Masukkan kode destroy:", type="password", key="destroy_key_input")
        if st.button("Destroy Chat Room"):
            if destroy_key and destroy_key == st.session_state.get(secret_key):
                rooms = load_json(CHAT_FILE)
                rooms.pop(room, None)
                save_json(CHAT_FILE, rooms)

                online = load_json(ONLINE_FILE)
                online.pop(room, None)
                save_json(ONLINE_FILE, online)

                st.success("Chat room berhasil dihancurkan. Refresh halaman untuk mulai ulang.")
                st.stop()
            else:
                st.error("Kode destroy salah.")


# ==============================
# APP FLOW
# ==============================
st.markdown(APP_CSS, unsafe_allow_html=True)

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

render_header()
auto_refresh_enabled, refresh_seconds, sound_enabled, test_sound_requested = render_sidebar()

if auto_refresh_enabled:
    if st_autorefresh is not None:
        st_autorefresh(interval=refresh_seconds * 1000, key="chat_auto_refresh")
    else:
        st.warning("Auto-refresh belum aktif. Jalankan: pip install streamlit-autorefresh")

room = st.text_input("room_name:", placeholder="contoh: black-room-01, atau buat unik, dan bagikan ke lawan bicara")
username = st.text_input("username:", placeholder="contoh: zero_cool")

if not room or not username:
    st.info("Masukkan nama room dan username untuk mulai chat terenkripsi.")
    st.caption("Software dibuat dengan Python + Streamlit + Fernet encryption.")
    st.stop()

online_users = update_online_status(room, username)

st.markdown("---")
st.subheader(f"Room: {room}")
st.write(f"Login sebagai: `{username}`")
st.info(
    f"Session aktif 30 menit. Auto-refresh: {'ON' if auto_refresh_enabled else 'OFF'} "
    f"setiap {refresh_seconds} detik. Suara: {'ON' if sound_enabled else 'OFF'}."
)

if online_users:
    st.success(f"Online: {', '.join(online_users)}")
else:
    st.info("Belum ada lawan bicara online di room ini.")

render_destroy_room(room)

messages = load_json(CHAT_FILE).get(room, [])
play_incoming_sound = should_play_incoming_sound(messages, username, sound_enabled)

components.html(
    render_chat_box(messages, username, play_incoming_sound, sound_enabled, HACKER_SOUND_DATA_URI),
    height=455,
    scrolling=False,
)

if sound_enabled and (play_incoming_sound or test_sound_requested):
    components.html(
        render_page_sound_trigger(HACKER_SOUND_DATA_URI),
        height=0,
        scrolling=False,
    )
    if test_sound_requested:
        st.success("Test sound dipicu. Kalau belum terdengar, cek izin audio browser/tab dan volume perangkat.")

with st.form("send_message_form", clear_on_submit=True):
    message = st.text_input("command_message:", placeholder="ketik pesan rahasia...")
    col1, col2 = st.columns([3, 1])
    send = col1.form_submit_button("Send")
    ping = col2.form_submit_button("Ping")

if send and message.strip():
    append_message(room, username, message.strip())
    st.rerun()

if ping:
    append_message(room, username, "PING!")
    st.rerun()

if st.button("Refresh Chat"):
    st.rerun()

st.caption("Pesan terenkripsi di file lokal. Untuk keamanan, destroy room setelah selesai digunakan.")
