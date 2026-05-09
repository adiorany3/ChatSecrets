import json
import os
import time
import uuid
import html
from datetime import datetime, timezone, timedelta

import streamlit as st
import streamlit.components.v1 as components
from cryptography.fernet import Fernet

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None


FERNET_KEY_FILE = "fernet.key"
CHAT_FILE = "chat_rooms.json"
ONLINE_FILE = "online_status.json"


st.set_page_config(
    page_title="ChatSecrets Terminal",
    page_icon="🟢",
    layout="centered",
)


HACKER_TERMINAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

:root {
    --terminal-green: #00ff66;
    --terminal-cyan: #00ddff;
    --terminal-dark: #020403;
    --terminal-panel: rgba(0, 20, 8, 0.92);
    --terminal-border: #00ff66;
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
    content: "root@chatsecrets:~$ ";
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
    border: 1px solid var(--terminal-border) !important;
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

.chat-box {
    height: 430px;
    overflow-y: auto;
    background: rgba(0, 0, 0, 0.94);
    border: 1px solid var(--terminal-green);
    padding: 16px;
    margin: 16px 0;
    box-shadow: inset 0 0 24px rgba(0,255,102,.14), 0 0 18px rgba(0,255,102,.2);
}

.chat-bubble {
    background: transparent;
    border-left: 3px solid var(--terminal-green);
    padding: 10px 12px;
    margin: 10px 0;
    color: var(--terminal-green);
    text-shadow: 0 0 6px rgba(0,255,102,.65);
    word-wrap: break-word;
}

.chat-bubble::before {
    content: "> ";
    color: #9cffb8;
}

.chat-bubble.me {
    border-left-color: var(--terminal-cyan);
    color: #8ff3ff;
    text-shadow: 0 0 6px rgba(0,204,255,.65);
}

.chat-bubble.me::before {
    content: "$ ";
    color: #8ff3ff;
}

.chat-meta {
    font-size: 12px;
    color: rgba(120,255,165,.75);
    margin-top: 6px;
}

.status-line {
    color: var(--terminal-dim);
    margin: 4px 0;
}

hr {
    border: none;
    border-top: 1px dashed rgba(0,255,102,.5);
}

::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: #000;
}

::-webkit-scrollbar-thumb {
    background: var(--terminal-green);
}

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

st.markdown(HACKER_TERMINAL_CSS, unsafe_allow_html=True)


def get_fernet() -> Fernet:
    if not os.path.exists(FERNET_KEY_FILE):
        key = Fernet.generate_key()
        with open(FERNET_KEY_FILE, "wb") as file:
            file.write(key)
    else:
        with open(FERNET_KEY_FILE, "rb") as file:
            key = file.read()
    return Fernet(key)


def load_json(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            return {}
    return {}


def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def wib_now() -> str:
    wib = timezone(timedelta(hours=7))
    return datetime.now(wib).strftime("%H:%M")


def encrypt_message(text: str) -> str:
    return get_fernet().encrypt(text.encode()).decode()


def decrypt_message(text: str) -> str:
    try:
        return get_fernet().decrypt(text.encode()).decode()
    except Exception:
        return "[Pesan tidak dapat didekripsi]"


if "input_counter" not in st.session_state:
    st.session_state.input_counter = 0

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())


with st.sidebar:
    st.markdown("### AUTO REFRESH")
    auto_refresh_enabled = st.toggle("Aktifkan auto refresh", value=True)
    refresh_seconds = st.slider("Interval refresh", min_value=2, max_value=15, value=3, step=1)
    st.caption("Matikan sementara kalau sedang mengetik pesan panjang.")

if auto_refresh_enabled:
    if st_autorefresh is not None:
        st_autorefresh(interval=refresh_seconds * 1000, key="chat_auto_refresh")
    else:
        st.warning("Auto-refresh belum aktif. Jalankan: pip install streamlit-autorefresh")


st.markdown(
    """
    <h1>CHATSECRETS <span class="cursor-blink"></span></h1>
    <div class="terminal-panel">
        <p class="status-line">[BOOT] Secure channel initialized...</p>
        <p class="status-line">[CRYPTO] Fernet encryption active</p>
        <p class="status-line">[MODE] Private multi-room communication</p>
        <p class="status-line">[WARNING] Destroy room after use for maximum privacy</p>
    </div>
    """,
    unsafe_allow_html=True,
)

room = st.text_input("room_name:", placeholder="contoh: black-room-01")
username = st.text_input("username:", placeholder="contoh: zero_cool")

if not room or not username:
    st.info("Masukkan nama room dan username untuk mulai chat terenkripsi.")
    st.caption("Software dibuat dengan Python + Streamlit + Fernet encryption.")
    st.stop()

rooms = load_json(CHAT_FILE)
online = load_json(ONLINE_FILE)
now_epoch = int(time.time())

online.setdefault(room, {})
online[room][username] = now_epoch
save_json(ONLINE_FILE, online)

st.markdown("---")
st.subheader(f"Room: {room}")
st.write(f"Login sebagai: `{username}`")
st.info(f"Session aktif 30 menit. Auto-refresh: {'ON' if auto_refresh_enabled else 'OFF'} setiap {refresh_seconds} detik.")

online_users = [
    user for user, last_seen in online.get(room, {}).items()
    if user != username and now_epoch - int(last_seen) <= 10
]

if online_users:
    st.success(f"Online: {', '.join(online_users)}")
else:
    st.info("Belum ada lawan bicara online di room ini.")

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

messages = load_json(CHAT_FILE).get(room, [])

# Render chat memakai components.html, bukan st.markdown.
# Ini mencegah tag <div> bocor sebagai teks pada pesan kedua dan seterusnya.
def render_chat_box(chat_messages: list, current_username: str) -> str:
    chat_parts = []
    for msg in chat_messages:
        is_me = msg.get("username") == current_username
        bubble_class = "chat-bubble me" if is_me else "chat-bubble"

        decrypted_text = decrypt_message(msg.get("text", ""))
        safe_text = html.escape(decrypted_text, quote=True).replace("\n", "<br>")
        safe_user = html.escape(str(msg.get("username", "unknown")), quote=True)
        safe_time = html.escape(str(msg.get("time", "")), quote=True)
        owner = " (Anda)" if is_me else ""

        chat_parts.append(
            f'<div class="{bubble_class}">'
            f'<div class="chat-message-text">{safe_text}</div>'
            f'<div class="chat-meta">{safe_user}{owner} // {safe_time}</div>'
            f'</div>'
        )

    body = "".join(chat_parts) or '<div class="empty-line">[LOG] Belum ada pesan. Kirim command pertama...</div>'

    return f"""
    <!doctype html>
    <html>
    <head>
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
    html, body {{
        margin: 0;
        padding: 0;
        background: transparent;
        font-family: 'Share Tech Mono', monospace;
    }}
    .chat-box {{
        height: 430px;
        overflow-y: auto;
        box-sizing: border-box;
        background: rgba(0, 0, 0, 0.94);
        border: 1px solid #00ff66;
        padding: 16px;
        box-shadow: inset 0 0 24px rgba(0,255,102,.14), 0 0 18px rgba(0,255,102,.2);
        color: #00ff66;
    }}
    .chat-box::before {{
        content: "CHAT LOG // LIVE FEED";
        display: block;
        color: #6dff9a;
        border-bottom: 1px dashed rgba(0,255,102,.45);
        padding-bottom: 8px;
        margin-bottom: 10px;
        letter-spacing: 1px;
    }}
    .chat-bubble {{
        background: transparent;
        border-left: 3px solid #00ff66;
        padding: 10px 12px;
        margin: 10px 0;
        color: #00ff66;
        text-shadow: 0 0 6px rgba(0,255,102,.65);
        word-wrap: break-word;
        overflow-wrap: anywhere;
    }}
    .chat-bubble::before {{
        content: "> ";
        color: #9cffb8;
    }}
    .chat-bubble.me {{
        border-left-color: #00ddff;
        color: #8ff3ff;
        text-shadow: 0 0 6px rgba(0,204,255,.65);
    }}
    .chat-bubble.me::before {{
        content: "$ ";
        color: #8ff3ff;
    }}
    .chat-message-text {{
        display: inline;
        white-space: normal;
    }}
    .chat-meta {{
        font-size: 12px;
        color: rgba(120,255,165,.75);
        margin-top: 6px;
    }}
    .empty-line {{
        color: rgba(120,255,165,.75);
        margin-top: 14px;
    }}
    ::-webkit-scrollbar {{ width: 8px; }}
    ::-webkit-scrollbar-track {{ background: #000; }}
    ::-webkit-scrollbar-thumb {{ background: #00ff66; }}
    </style>
    </head>
    <body>
        <div class="chat-box" id="chatBox">{body}</div>
        <script>
            const chatBox = document.getElementById('chatBox');
            chatBox.scrollTop = chatBox.scrollHeight;
        </script>
    </body>
    </html>
    """

components.html(render_chat_box(messages, username), height=455, scrolling=False)

with st.form("send_message_form", clear_on_submit=True):
    message = st.text_input("command_message:", placeholder="ketik pesan rahasia...")
    col1, col2 = st.columns([3, 1])
    send = col1.form_submit_button("Send")
    ping = col2.form_submit_button("Ping")

if send and message.strip():
    rooms = load_json(CHAT_FILE)
    rooms.setdefault(room, [])
    rooms[room].append({
        "username": username,
        "text": encrypt_message(message.strip()),
        "time": wib_now(),
    })
    save_json(CHAT_FILE, rooms)
    st.rerun()

if ping:
    rooms = load_json(CHAT_FILE)
    rooms.setdefault(room, [])
    rooms[room].append({
        "username": username,
        "text": encrypt_message("PING!"),
        "time": wib_now(),
    })
    save_json(CHAT_FILE, rooms)
    st.rerun()

if st.button("Refresh Chat"):
    st.rerun()

st.caption("Pesan terenkripsi di file lokal. Untuk keamanan, destroy room setelah selesai digunakan.")
