import base64
import hashlib
import html
import io
import json
import math
import os
import struct
import tempfile
import time
import uuid
import wave
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from cryptography.fernet import Fernet, InvalidToken
from attachments import FILE_TYPES, validate_attachment

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

# ==============================
# CONFIG
# ==============================
APP_TITLE = "ChatSecrets"
APP_ICON = "💻"
SECRETS_FILE = Path(".streamlit") / "secrets.toml"
CHAT_FILE = "chat_rooms.json"
ONLINE_FILE = "online_status.json"
DESTROYED_ROOMS_FILE = "destroyed_rooms.json"
ROOM_INPUT_KEY = "room_name_input"
USERNAME_INPUT_KEY = "username_input"
LOCKED_ROOM_KEY = "locked_room_name"
LOCKED_USERNAME_KEY = "locked_username"
ROOM_REUSE_WAIT_SECONDS = 30
WIB = timezone(timedelta(hours=7))

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
def load_json(path: str) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Format penyimpanan tidak valid: {path}")
    return data


def save_json(path: str, data: dict[str, Any]) -> None:
    # ponytail: atomic writes only; use SQLite transactions for concurrent updates.
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=Path(path).parent,
            prefix=f".{Path(path).name}.", suffix=".tmp", delete=False,
        ) as file:
            tmp_path = file.name
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path is not None:
            Path(tmp_path).unlink(missing_ok=True)


def _read_fernet_key_from_toml() -> str | None:
    """Read Fernet key from .streamlit/secrets.toml without adding a toml dependency."""
    if not SECRETS_FILE.exists():
        return None

    in_secrets_section = False
    for raw_line in SECRETS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            in_secrets_section = line == "[secrets]"
            continue
        if in_secrets_section and line.startswith("fernet_key") and "=" in line:
            _, value = line.split("=", 1)
            return value.strip().strip('"').strip("'")
    return None


def _write_fernet_key_to_toml(key: bytes) -> None:
    """Store generated Fernet key inside the hidden Streamlit TOML file."""
    SECRETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    key_text = key.decode("utf-8")
    content = (
        "# File ini menyimpan secret lokal untuk ChatSecrets.\n"
        "# Jangan commit / upload file ini ke repository publik.\n\n"
        "[secrets]\n"
        f'fernet_key = "{key_text}"\n'
    )
    SECRETS_FILE.write_text(content, encoding="utf-8")


def get_fernet_key() -> bytes:
    """
    Fernet key sekarang disembunyikan di file TOML:
    .streamlit/secrets.toml pada bagian [secrets].fernet_key
    """
    key_text = None

    try:
        if "secrets" in st.secrets and "fernet_key" in st.secrets["secrets"]:
            key_text = str(st.secrets["secrets"]["fernet_key"])
        elif "fernet_key" in st.secrets:
            key_text = str(st.secrets["fernet_key"])
    except Exception:
        key_text = None

    if not key_text:
        key_text = _read_fernet_key_from_toml()

    if not key_text:
        generated_key = Fernet.generate_key()
        _write_fernet_key_to_toml(generated_key)
        return generated_key

    key = key_text.encode("utf-8")
    try:
        Fernet(key)
    except Exception as exc:
        st.error("Fernet key di `.streamlit/secrets.toml` tidak valid. Gunakan key dari `Fernet.generate_key()`. ")
        raise exc
    return key


def get_fernet() -> Fernet:
    return Fernet(get_fernet_key())


def encrypt_message(text: str) -> str:
    return get_fernet().encrypt(text.encode()).decode()


def decrypt_message(text: str) -> str:
    try:
        return get_fernet().decrypt(text.encode()).decode()
    except Exception:
        return "[Pesan tidak dapat didekripsi]"


def wib_now() -> str:
    return datetime.now(WIB).strftime("%H:%M")


def wib_timestamp() -> str:
    return datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")

# ==============================
# ROOM DESTROY HELPERS
# ==============================
def sanitize_room_name(room: str) -> str:
    return room.strip()


def _parse_wib_timestamp(timestamp_text: str) -> datetime | None:
    try:
        clean_text = timestamp_text.replace(" WIB", "")
        return datetime.strptime(clean_text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=WIB)
    except Exception:
        return None


def get_destroyed_rooms() -> dict[str, Any]:
    """
    Membaca daftar room yang dihancurkan.
    Room yang sudah lewat 30 detik otomatis dihapus dari destroyed_rooms.json,
    sehingga nama room bisa digunakan kembali dan tidak meninggalkan jejak.
    """
    destroyed_rooms = load_json(DESTROYED_ROOMS_FILE)
    now = datetime.now(WIB)
    changed = False

    for room_name, data in list(destroyed_rooms.items()):
        destroyed_at_text = str(data.get("destroyed_at", ""))
        destroyed_at = _parse_wib_timestamp(destroyed_at_text)

        if destroyed_at is None:
            destroyed_rooms.pop(room_name, None)
            changed = True
            continue

        elapsed_seconds = (now - destroyed_at).total_seconds()

        if elapsed_seconds >= ROOM_REUSE_WAIT_SECONDS:
            destroyed_rooms.pop(room_name, None)
            changed = True

    if changed:
        save_json(DESTROYED_ROOMS_FILE, destroyed_rooms)

    return destroyed_rooms


def get_room_remaining_lock_seconds(room: str) -> int:
    clean_room = sanitize_room_name(room)
    destroyed_rooms = get_destroyed_rooms()

    if clean_room not in destroyed_rooms:
        return 0

    destroyed_at_text = str(destroyed_rooms[clean_room].get("destroyed_at", ""))
    destroyed_at = _parse_wib_timestamp(destroyed_at_text)

    if destroyed_at is None:
        destroyed_rooms.pop(clean_room, None)
        save_json(DESTROYED_ROOMS_FILE, destroyed_rooms)
        return 0

    elapsed_seconds = int((datetime.now(WIB) - destroyed_at).total_seconds())
    remaining_seconds = ROOM_REUSE_WAIT_SECONDS - elapsed_seconds

    if remaining_seconds <= 0:
        destroyed_rooms.pop(clean_room, None)
        save_json(DESTROYED_ROOMS_FILE, destroyed_rooms)
        return 0

    return remaining_seconds


def is_room_destroyed(room: str) -> bool:
    clean_room = sanitize_room_name(room)

    if not clean_room:
        return False

    return get_room_remaining_lock_seconds(clean_room) > 0


def destroy_room_completely(room: str, username: str = "system", reason: str = "panic") -> None:
    clean_room = sanitize_room_name(room)

    if not clean_room:
        return

    rooms = load_json(CHAT_FILE)
    rooms.pop(clean_room, None)
    save_json(CHAT_FILE, rooms)

    online = load_json(ONLINE_FILE)
    online.pop(clean_room, None)
    save_json(ONLINE_FILE, online)

    destroyed_rooms = get_destroyed_rooms()
    destroyed_rooms[clean_room] = {
        "destroyed_at": wib_timestamp(),
        "destroyed_by": username,
        "reason": reason,
    }
    save_json(DESTROYED_ROOMS_FILE, destroyed_rooms)


def clear_current_room_session(room: str | None = None) -> None:
    if ROOM_INPUT_KEY in st.session_state:
        st.session_state[ROOM_INPUT_KEY] = ""

    if USERNAME_INPUT_KEY in st.session_state:
        st.session_state[USERNAME_INPUT_KEY] = ""

    st.session_state.pop(LOCKED_ROOM_KEY, None)
    st.session_state.pop(LOCKED_USERNAME_KEY, None)
    st.session_state.pop("last_message_signature", None)

    if room:
        st.session_state["destroyed_room_notice"] = sanitize_room_name(room)


def panic_destroy_current_room(room: str, username: str) -> None:
    clean_room = sanitize_room_name(room)
    destroy_room_completely(clean_room, username=username, reason="panic_button")
    clear_current_room_session(clean_room)


def destroy_current_room_with_code(room: str, username: str) -> None:
    clean_room = sanitize_room_name(room)
    secret_key = f"destroy_secret_{clean_room}"
    provided_key = st.session_state.get("destroy_key_input", "")
    expected_key = st.session_state.get(secret_key, "")

    if provided_key and expected_key and provided_key == expected_key:
        destroy_room_completely(clean_room, username=username, reason="destroy_code")
        st.session_state.pop(secret_key, None)
        st.session_state["destroy_code_ok"] = True
        clear_current_room_session(clean_room)
    else:
        st.session_state["destroy_code_error"] = True


def auto_clear_destroyed_room_before_widgets() -> None:
    room_in_session = sanitize_room_name(str(st.session_state.get(ROOM_INPUT_KEY, "")))

    if room_in_session and is_room_destroyed(room_in_session):
        clear_current_room_session(room_in_session)


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


def lock_room_and_username_after_entering_room(room: str, username: str) -> None:
    clean_room = sanitize_room_name(room)
    clean_username = username.strip()

    if not clean_room or not clean_username or get_locked_room() or get_locked_username():
        return

    st.session_state[LOCKED_ROOM_KEY] = clean_room
    st.session_state[LOCKED_USERNAME_KEY] = clean_username
    st.rerun()

# ==============================
# CHAT HELPERS
# ==============================
def make_message(username: str, text: str) -> dict[str, Any]:
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
    clean_room = sanitize_room_name(room)
    if is_room_destroyed(clean_room):
        st.session_state["blocked_destroyed_room"] = clean_room
        clear_current_room_session(clean_room)
        return

    rooms = load_json(CHAT_FILE)
    rooms.setdefault(clean_room, [])
    message = make_message(username, message_text)
    if attachment is not None:
        message["attachment"] = attachment
    rooms[clean_room].append(message)
    save_json(CHAT_FILE, rooms)

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
    st.title("ChatSecrets")
    st.write("Ruang percakapan pribadi, dengan tampilan yang nyaman dibaca.")
    st.caption("Masukkan nama room dan username untuk mulai. Gunakan nama room yang sama untuk bergabung.")


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
    clean_room = sanitize_room_name(room)
    if is_room_destroyed(clean_room):
        clear_current_room_session(clean_room)
        return []

    online = load_json(ONLINE_FILE)
    now_epoch = int(time.time())
    online.setdefault(clean_room, {})
    online[clean_room][username] = now_epoch
    save_json(ONLINE_FILE, online)

    return [
        user
        for user, last_seen in online.get(clean_room, {}).items()
        if user != username and now_epoch - int(last_seen) <= 10
    ]


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

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

auto_clear_destroyed_room_before_widgets()
render_header()
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

if st.session_state.pop("destroy_code_error", False):
    st.error("Kode destroy salah atau belum diset.")

sync_locked_room_before_widget()
sync_locked_username_before_widget()
locked_room = get_locked_room()
locked_username = get_locked_username()
room_is_locked = bool(locked_room)
username_is_locked = bool(locked_username)

room = st.text_input(
    "room_name >",
    placeholder="contoh: black-room-01, atau buat unik, dan bagikan ke lawan bicara",
    key=ROOM_INPUT_KEY,
    disabled=room_is_locked,
)
username = st.text_input(
    "username >",
    placeholder="contoh: SubZero1",
    key=USERNAME_INPUT_KEY,
    disabled=username_is_locked,
)

room = locked_room if room_is_locked else sanitize_room_name(room)
username = locked_username if username_is_locked else username.strip()

if room_is_locked and username_is_locked:
    st.caption("Room dan username sudah terkunci setelah masuk room pada session ini.")
elif room_is_locked:
    st.caption("Room sudah terkunci setelah masuk room dan tidak bisa diganti pada session ini.")
elif username_is_locked:
    st.caption("Username sudah terkunci setelah masuk room dan tidak bisa diganti pada session ini.")

if room and is_room_destroyed(room):
    remaining_seconds = get_room_remaining_lock_seconds(room)
    remaining_minutes = remaining_seconds // 60
    remaining_second_only = remaining_seconds % 60

    st.error(
        f"Room ini baru saja dihancurkan. Nama room dapat digunakan kembali dalam "
        f"{remaining_minutes} menit {remaining_second_only} detik."
    )
    st.stop()

if not room or not username:
    st.info("Masukkan nama room dan username untuk mulai chat terenkripsi.")
    st.caption("Software dibuat dengan Python + Streamlit + Fernet encryption.")
    st.stop()

lock_room_and_username_after_entering_room(room, username)

online_users = update_online_status(room, username)
st.markdown("---")
st.subheader(f"Room: {room}")
st.write(f"Login sebagai: `{username}`")
st.info(
    f"Session aktif 30 menit. Auto-refresh: {'ON' if auto_refresh_enabled else 'OFF'} setiap {refresh_seconds} detik. "
    f"Suara: {'ON' if sound_enabled else 'OFF'}."
)

render_destroy_room(room, username)

if not st.session_state.get(ROOM_INPUT_KEY):
    st.stop()

messages = load_json(CHAT_FILE).get(room, [])
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

# ponytail: small files remain in room JSON; use encrypted blob storage for larger uploads.
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
    except (ValueError, OSError) as exc:
        st.error(f"Pesan belum terkirim: {exc}")
    else:
        st.session_state["composer_id"] = composer_id + 1
        st.rerun()

if ping:
    append_message(room, username, "PING!")
    st.rerun()

st.caption("Pesan terenkripsi di file lokal. Untuk keamanan, gunakan Panic Room / Destroy Room setelah selesai digunakan.")
