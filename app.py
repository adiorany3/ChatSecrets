import base64
import hashlib
import html
import io
import math
import sqlite3
import struct
import wave
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from cryptography.fernet import Fernet, InvalidToken
from attachments import FILE_TYPES, validate_attachment
from storage import AuthError, Store, provision_key

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

# ==============================
# CONFIG
# ==============================
APP_TITLE = "Cit Chat"
APP_ICON = "💻"
BASE_DIR = Path(__file__).resolve().parent
SECRETS_FILE = BASE_DIR / ".streamlit" / "secrets.toml"
ROOM_INPUT_KEY = "room_name_input"
USERNAME_INPUT_KEY = "username_input"
LOCKED_ROOM_KEY = "locked_room_name"
LOCKED_USERNAME_KEY = "locked_username"

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="centered")

# ==============================
# CSS
# ==============================
APP_CSS = """
<style>
.stApp {
    background: #0f172a;
    color: #e2e8f0;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    line-height: 1.6;
}
.block-container {
    max-width: 960px;
    padding: 4rem 2rem 2rem;
}
[data-testid="stSidebar"] {
    background: #162033;
    color: #e2e8f0;
    border-right: 1px solid #334155;
}
h1, h2, h3 {
    color: #f8fafc;
    line-height: 1.3;
    letter-spacing: normal;
    overflow-wrap: anywhere;
}
h1 { font-size: clamp(1.8rem, 5vw, 2.6rem); }
[data-testid="stMarkdownContainer"] p,
[data-testid="stCaptionContainer"],
[data-testid="stWidgetLabel"] p {
    line-height: 1.6;
    overflow-wrap: anywhere;
}
[data-testid="stCaptionContainer"] { color: #b8c5d6; }
[data-testid="stWidgetLabel"] { color: #e2e8f0; }
input, textarea {
    font-family: inherit;
    font-size: 16px !important;
    line-height: 1.5;
    color: #f8fafc !important;
    caret-color: #5eead4;
}
input::placeholder, textarea::placeholder { color: #a8b7cc; opacity: 1; }
[data-baseweb="input"], [data-baseweb="textarea"] {
    background: #162033;
    border: 1px solid #64748b;
    border-radius: 10px;
}
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within {
    border-color: #5eead4;
    outline: 2px solid #5eead4;
    outline-offset: 2px;
}
.stButton > button, [data-testid="stFormSubmitButton"] button {
    min-height: 44px;
    background: #1e293b;
    color: #f8fafc;
    border: 1px solid #64748b;
    border-radius: 10px;
    padding: .6rem 1rem;
    white-space: normal;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
    background: #134e4a;
    color: #f0fdfa;
    border-color: #5eead4;
}
button:focus-visible { outline: 2px solid #5eead4; outline-offset: 3px; }
[data-testid="stExpander"], [data-testid="stForm"] {
    border: 1px solid #334155;
    border-radius: 12px;
}
hr { border-color: #334155; }
[data-testid="stFormSubmitButton"] button[kind="primary"] {
 background: #134e4a;
 border-color: #5eead4;
 color: #f0fdfa;
}
input:disabled { -webkit-text-fill-color: #b8c5d6; opacity: 1; }
@media (max-width: 480px) {
 [data-testid="stForm"] { padding: .75rem; }
}
@media (max-width: 640px) {
    .block-container { padding: 3.5rem 1rem 1.5rem; }
    h2, h3 { font-size: 1.25rem; }
    [data-testid="stForm"] [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
        gap: .75rem;
    }
    [data-testid="stForm"] [data-testid="stColumn"] {
        min-width: 120px;
        flex: 1 1 120px;
    }
}
</style>
"""

CHAT_COMPONENT_CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
html, body {
    margin: 0;
    padding: 0;
    background: #0f172a;
    color: #e2e8f0;
    font: 16px/1.6 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.chat-box {
    height: 440px;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: 16px;
    border: 1px solid #334155;
    border-radius: 12px;
    background: #162033;
    overflow-wrap: anywhere;
}
.sound-panel {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding-bottom: 14px;
    margin-bottom: 16px;
    border-bottom: 1px solid #334155;
    color: #b8c5d6;
    font-size: 14px;
}
.sound-panel span { flex: 1 1 180px; min-width: 0; }
.sound-panel button {
    min-height: 44px;
    padding: 8px 14px;
    border: 1px solid #5eead4;
    border-radius: 8px;
    background: #134e4a;
    color: #f0fdfa;
    font: inherit;
    cursor: pointer;
}
.sound-panel button:hover { background: #115e59; }
.sound-panel button:focus-visible { outline: 2px solid #5eead4; outline-offset: 3px; }
.chat-bubble {
    width: fit-content;
    max-width: 90%;
    margin: 12px 0;
    padding: 12px 16px;
    border: 1px solid #475569;
    border-radius: 12px;
    background: #1e293b;
    overflow-wrap: anywhere;
}
.chat-bubble.me {
    margin-left: auto;
    background: #134e4a;
    border-color: #28766e;
    color: #f0fdfa;
}
.chat-box:focus-visible { outline: 2px solid #5eead4; outline-offset: -3px; }
.chat-message-text { white-space: pre-wrap; }
.chat-meta { margin-top: 8px; font-size: 13px; color: #cbd5e1; }
.empty-line { padding: 32px 8px; color: #b8c5d6; text-align: center; }
@media (max-width: 480px) {
    .chat-box { padding: 12px; }
    .chat-bubble { max-width: 100%; padding: 10px 12px; }
}
"""

# ==============================
# STORAGE + CRYPTO HELPERS
# ==============================
@st.cache_resource
def get_store() -> Store:
    configured = None
    try:
        configured = st.secrets.get("secrets", {}).get("fernet_key") or st.secrets.get("fernet_key")
    except FileNotFoundError:
        pass
    key = provision_key(SECRETS_FILE, configured)
    return Store(BASE_DIR / "chatsecrets.sqlite3", key, legacy_dir=BASE_DIR)














def get_fernet() -> Fernet:
    return get_store().fernet




def decrypt_message(text: str) -> str:
    try:
        return get_fernet().decrypt(text.encode()).decode()
    except Exception:
        return "[Pesan tidak dapat didekripsi]"




# ==============================
# ROOM DESTROY HELPERS
# ==============================
def sanitize_room_name(room: str) -> str:
    return room.strip()
















def clear_current_room_session(room: str | None = None) -> None:
    if ROOM_INPUT_KEY in st.session_state:
        st.session_state[ROOM_INPUT_KEY] = ""

    if USERNAME_INPUT_KEY in st.session_state:
        st.session_state[USERNAME_INPUT_KEY] = ""

    st.session_state.pop(LOCKED_ROOM_KEY, None)
    st.session_state.pop(LOCKED_USERNAME_KEY, None)
    st.session_state.pop("room_token", None)
    st.session_state.pop("last_message_signature", None)
    st.session_state["composer_id"] = st.session_state.get("composer_id", 0) + 1

    if room:
        st.session_state["destroyed_room_notice"] = sanitize_room_name(room)


def panic_destroy_current_room(room: str, username: str) -> None:
    try:
        get_store().destroy(st.session_state.get("room_token", ""))
    except AuthError as exc:
        st.session_state["auth_notice"] = str(exc)
        clear_current_room_session()
    except (OSError, sqlite3.Error) as exc:
        st.session_state["auth_notice"] = f"Destroy failed: {exc}"
    else:
        clear_current_room_session(room)








def get_locked_room() -> str:
    return sanitize_room_name(str(st.session_state.get(LOCKED_ROOM_KEY, "")))


def get_locked_username() -> str:
    return str(st.session_state.get(LOCKED_USERNAME_KEY, "")).strip()


def sync_locked_room_before_widget() -> None:
    locked_room = get_locked_room()

    if locked_room and st.session_state.get(ROOM_INPUT_KEY) != locked_room:
        st.session_state[ROOM_INPUT_KEY] = locked_room


def sync_locked_username_before_widget() -> None:
    locked_username = get_locked_username()

    if locked_username and st.session_state.get(USERNAME_INPUT_KEY) != locked_username:
        st.session_state[USERNAME_INPUT_KEY] = locked_username




# ==============================
# CHAT HELPERS
# ==============================


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


def should_play_incoming_sound(messages: list[dict[str, Any]], current_username: str, sound_enabled: bool) -> bool:
    current_signature = get_message_signature(messages)
    previous_signature = st.session_state.get("last_message_signature")
    st.session_state.last_message_signature = current_signature

    if not sound_enabled or not messages or previous_signature is None:
        return False
    latest_sender = str(messages[-1].get("username", ""))
    return current_signature != previous_signature and latest_sender != current_username


def render_chat_messages(messages: list[dict[str, Any]], current_username: str) -> str:
    if not messages:
        return '<div class="empty-line">Belum ada pesan. Mulai percakapan dengan mengirim pesan pertama.</div>'

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


def render_chat_box(messages: list[dict[str, Any]], current_username: str, play_incoming_sound: bool, sound_enabled: bool, sound_data_uri: str) -> str:
    body = render_chat_messages(messages, current_username)
    play_flag = "true" if play_incoming_sound else "false"
    escaped_sound_src = html.escape(sound_data_uri, quote=True)

    sound_panel = """
    <div class="sound-panel"><span>[AUDIO] Klik unlock untuk mengaktifkan suara pesan masuk.</span><button onclick="window.chatSound.play()">Unlock Sound</button></div>
    """ if sound_enabled else """
    <div class="sound-panel">[AUDIO] Suara pesan masuk dimatikan dari sidebar.</div>
    """

    return f"""
    <style>{CHAT_COMPONENT_CSS}</style>
    <div id="chatBox" class="chat-box" tabindex="0" role="region" aria-label="Pesan chat">{sound_panel}{body}</div>
    <audio id="chatSound" src="{escaped_sound_src}"></audio>
    <script>
      window.chatSound = document.getElementById('chatSound');

      function scrollChatToBottom() {{
        const chatBox = document.getElementById('chatBox');
        if (!chatBox) return;

        // Scroll hanya area pesan, bukan halaman utama Streamlit.
        chatBox.scrollTop = chatBox.scrollHeight;
      }}

      window.addEventListener('load', scrollChatToBottom);
      requestAnimationFrame(scrollChatToBottom);
      setTimeout(scrollChatToBottom, 80);
      setTimeout(scrollChatToBottom, 250);

      if ({play_flag}) {{
        window.chatSound.currentTime = 0;
        window.chatSound.play().catch(() => {{}});
      }}
    </script>
    """


def append_message(room: str, username: str, message_text: str, attachment: dict[str, str] | None = None) -> None:
    get_store().send(st.session_state.get("room_token", ""), message_text, attachment)

# ==============================
# AUDIO HELPERS
# ==============================
def build_hacker_wav_data_uri() -> str:
    sample_rate = 44100
    notes = [740, 990, 520, 1180]
    note_duration = 0.085
    gap_duration = 0.025
    volume = 0.28
    samples: list[int] = []

    for frequency in notes:
        total_note_samples = int(sample_rate * note_duration)
        for i in range(total_note_samples):
            t = i / sample_rate
            attack = min(1.0, i / max(1, int(sample_rate * 0.012)))
            release = min(1.0, (total_note_samples - i) / max(1, int(sample_rate * 0.025)))
            envelope = max(0.0, min(attack, release))
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


def render_page_sound_trigger(sound_data_uri: str) -> str:
    escaped_src = html.escape(sound_data_uri, quote=True)
    return f"""
    <audio id="pageSound" src="{escaped_src}"></audio>
    <script>
      const sound = document.getElementById('pageSound');
      sound.play().catch(() => {{}});
    </script>
    """

HACKER_SOUND_DATA_URI = build_hacker_wav_data_uri()

# ==============================
# UI HELPERS
# ==============================
def render_header() -> None:
    st.title("Cit Chat")
    st.write("Ruang percakapan pribadi, dengan tampilan yang nyaman dibaca.")
    st.caption("Join explicitly with a room name, username, and shared password.")


def render_sidebar() -> tuple[bool, int, bool, bool]:
    with st.sidebar:
        st.markdown("### Pengaturan")
        auto_refresh_enabled = st.toggle("Aktifkan auto refresh", value=True)
        refresh_seconds = st.slider("Interval refresh", min_value=2, max_value=15, value=3, step=1)
        sound_enabled = st.toggle("Suara pesan masuk", value=True)
        test_sound_requested = st.button("Tes suara", use_container_width=True)
        st.caption("Klik Tes suara sekali. Setelah browser mengizinkan audio, pesan masuk dari user lain akan berbunyi otomatis.")
        st.caption("Matikan auto-refresh sementara kalau sedang mengetik pesan panjang.")
        return auto_refresh_enabled, refresh_seconds, sound_enabled, test_sound_requested


def update_online_status(room: str, username: str) -> list[str]:
    return get_store().presence(st.session_state.get("room_token", ""))


def render_destroy_room(room: str, username: str) -> None:
    clean_room = sanitize_room_name(room)
    with st.expander("Destroy / Panic Room", expanded=False):
        st.markdown(
            """
            [PANIC ROOM]

            Tekan tombol ini untuk menghapus data room, menghapus status online room, mengunci nama room, lalu mengeluarkan user dari room.
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "PANIC ROOM // DESTROY NOW",
            use_container_width=True,
            key=f"panic_room_{clean_room}",
            on_click=panic_destroy_current_room,
            args=(clean_room, username),
        )

# ==============================
# APP FLOW
# ==============================
st.markdown(APP_CSS, unsafe_allow_html=True)

render_header()
try:
    store = get_store()
except (ValueError, OSError, sqlite3.Error) as exc:
    st.error(f"Storage unavailable: {exc}")
    st.stop()

if st.session_state.get("room_token"):
    try:
        store.presence(st.session_state["room_token"])
    except AuthError as exc:
        clear_current_room_session()
        st.session_state["auth_notice"] = str(exc)
    except sqlite3.Error as exc:
        st.error(f"Storage unavailable: {exc}")
        st.stop()

if notice := st.session_state.pop("auth_notice", None):
    st.error(notice)
auto_refresh_enabled, refresh_seconds, sound_enabled, test_sound_requested = render_sidebar()

if auto_refresh_enabled:
    if st_autorefresh is not None:
        st_autorefresh(interval=refresh_seconds * 1000, key="chat_auto_refresh")
    else:
        st.warning("Auto-refresh belum aktif. Jalankan: pip install streamlit-autorefresh")

notice_room = st.session_state.pop("destroyed_room_notice", None)
if notice_room:
    st.success(
        f"Room `{notice_room}` sedang dibersihkan, agar Anda nyaman menggunakan room ini. "
        f"Nama room dapat digunakan kembali setelah 30 detik, silahkan datang kembali nanti"
    )


sync_locked_room_before_widget()
sync_locked_username_before_widget()
locked_room = get_locked_room()
locked_username = get_locked_username()

if not st.session_state.get("room_token"):
    with st.form("join_room", clear_on_submit=True):
        room = st.text_input("Room name", max_chars=128)
        username = st.text_input("Username", max_chars=80)
        password = st.text_input("Shared room password (8–1024 characters)", type="password", max_chars=1024)
        join = st.form_submit_button("Create / join room", type="primary")
    st.caption("New room: sets its password. Existing room: requires the same password. Every authenticated member can destroy the room.")
    if join:
        try:
            token = store.join(room, username, password)
        except (ValueError, OSError, sqlite3.Error) as exc:
            st.error(str(exc))
        else:
            st.session_state["room_token"] = token
            st.session_state[LOCKED_ROOM_KEY] = room.strip()
            st.session_state[LOCKED_USERNAME_KEY] = username.strip()
            st.rerun()
    st.stop()

room, username = locked_room, locked_username
try:
    online_users = update_online_status(room, username)
    messages = store.read(st.session_state["room_token"])
except AuthError as exc:
    clear_current_room_session()
    st.session_state["auth_notice"] = str(exc)
    st.rerun()
except (sqlite3.Error, InvalidToken, ValueError) as exc:
    st.error(f"Messages unavailable: {exc}")
    st.stop()
st.markdown("---")
st.subheader(f"Room: {room}")
st.write(f"Login sebagai: `{username}`")
st.info(
    f"Session aktif 30 menit. Auto-refresh: {'ON' if auto_refresh_enabled else 'OFF'} setiap {refresh_seconds} detik. "
    f"Suara: {'ON' if sound_enabled else 'OFF'}."
)

render_destroy_room(room, username)

if not st.session_state.get("room_token"):
    st.stop()

play_incoming_sound = should_play_incoming_sound(messages, username, sound_enabled)

components.html(
    render_chat_box(messages, username, play_incoming_sound, sound_enabled, HACKER_SOUND_DATA_URI),
    height=455,
    scrolling=False,
)

if sound_enabled and (play_incoming_sound or test_sound_requested):
    components.html(render_page_sound_trigger(HACKER_SOUND_DATA_URI), height=0, scrolling=False)

if test_sound_requested:
    st.success("Test sound dipicu. Kalau belum terdengar, cek izin audio browser/tab dan volume perangkat.")

# ponytail: bounded attachments stay encrypted in SQLite; use encrypted blob storage for larger uploads.
for index, msg in enumerate(messages):
    if not msg.get("attachment"):
        continue
    with st.expander(f"Lampiran — {msg.get('username', '')} · {msg.get('time', '')}"):
        try:
            attachment = msg["attachment"]
            data = get_fernet().decrypt(attachment["data"].encode())
            info = validate_attachment(attachment["name"], data)
        except (InvalidToken, ValueError, KeyError, TypeError, AttributeError):
            st.error("Lampiran tidak dapat dibaca atau tidak valid.")
            continue
        if info["mime"].startswith("image/"):
            encoded = base64.b64encode(data).decode("ascii")
            st.markdown(
                f'<img src="data:{info["mime"]};base64,{encoded}" '
                f'alt="{html.escape(info["name"], quote=True)}" '
                'style="max-width:100%;max-height:360px;object-fit:contain">',
                unsafe_allow_html=True,
            )
        st.download_button(
            "Unduh " + info["name"], data=data, file_name=info["name"],
            mime="application/octet-stream", key=f"attachment_{index}",
        )
        st.caption("Buka hanya file dari pengirim tepercaya. File tidak dipindai antivirus.")

composer_id = st.session_state.get("composer_id", 0)
with st.form(f"send_message_form_{composer_id}", clear_on_submit=False):
    message = st.text_input("Pesan", placeholder="Tulis pesan...", key=f"message_{composer_id}")
    uploaded_file = st.file_uploader(
        "Gambar atau dokumen (maksimal 5 MiB)", type=list(FILE_TYPES),
        key=f"upload_{composer_id}",
    )
    col1, col2 = st.columns([3, 2])
    send = col1.form_submit_button("Kirim", type="primary", use_container_width=True)
    ping = col2.form_submit_button("Ping", use_container_width=True)

components.html(
    "<script>" + (Path(__file__).parent / "static" / "composer-focus.js").read_text(encoding="utf-8") + "</script>",
    height=0,
    scrolling=False,
)

if online_users:
    st.success(f"Online: {', '.join(online_users)}")
else:
    st.info("Belum ada lawan bicara online di room ini.")

if send and (message.strip() or uploaded_file is not None):
    try:
        attachment = None
        if uploaded_file is not None:
            data = uploaded_file.getvalue()
            attachment = validate_attachment(uploaded_file.name, data)
            attachment["data"] = get_fernet().encrypt(data).decode("ascii")
        text = message.strip() or ("Lampiran: " + attachment["name"])
        append_message(room, username, text, attachment)
    except (ValueError, OSError, sqlite3.Error, InvalidToken) as exc:
        st.error(f"Pesan belum terkirim: {exc}")
    else:
        st.session_state["composer_id"] = composer_id + 1
        st.rerun()

if ping:
    try:
        append_message(room, username, "PING!")
    except (ValueError, OSError, sqlite3.Error) as exc:
        st.error(f"Ping not sent: {exc}")
    else:
        st.rerun()

st.caption("Pesan terenkripsi di file lokal. Untuk keamanan, gunakan Panic Room / Destroy Room setelah selesai digunakan.")
