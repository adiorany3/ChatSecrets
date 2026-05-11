import base64
import hashlib
import html
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from cryptography.fernet import Fernet

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # package optional, app still works with manual refresh
    st_autorefresh = None

# ==============================
# CONFIG
# ==============================
APP_TITLE = "ChatSecrets Terminal"
APP_ICON = "💀"
FERNET_KEY_FILE = "fernet.key"
CHAT_FILE = "chat_rooms.json"
ONLINE_FILE = "online_status.json"
ROOM_SETTINGS_FILE = "room_settings.json"
WIB = timezone(timedelta(hours=7))

ONLINE_ACTIVE_SECONDS = 20
DEFAULT_AUTO_DESTROY_MINUTES = 30
AUTO_DESTROY_CHOICES = ["Never", "10 menit", "20 menit", "30 menit", "40 menit", "50 menit", "60 menit"]

MAX_MEDIA_BYTES = 8 * 1024 * 1024  # 8 MB per media message
ALLOWED_IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]
ALLOWED_AUDIO_TYPES = ["wav", "mp3", "ogg", "m4a", "aac", "flac", "webm"]

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="centered")

# ==============================
# CSS: HACKER TERMINAL THEME
# ==============================
APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

:root {
  --terminal-green: #00ff66;
  --terminal-cyan: #00ddff;
  --terminal-bg: #020403;
  --terminal-panel: rgba(0, 20, 8, .92);
  --terminal-dim: #79ff9e;
  --terminal-danger: #ff275f;
}

.stApp {
  background:
    radial-gradient(circle at top, rgba(0,255,102,.16), transparent 38%),
    linear-gradient(180deg, #020403 0%, #000 100%);
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
    rgba(255,255,255,.026) 0,
    rgba(255,255,255,.026) 1px,
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
  box-shadow: inset 0 0 130px rgba(0,255,102,.14);
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
}

h1::before {
  content: "root@AntiTrust:~$ ";
  color: var(--terminal-dim);
  font-size: .52em;
}

.stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
  background: #000 !important;
  color: var(--terminal-green) !important;
  border: 1px solid var(--terminal-green) !important;
  border-radius: 0 !important;
  box-shadow: 0 0 12px rgba(0,255,102,.24);
}

.stFileUploader, .stAudioInput {
  background: rgba(0, 20, 8, .36);
  border: 1px dashed rgba(0,255,102,.5);
  padding: 10px;
}

.stButton button, .stFormSubmitButton button {
  background: #001a08 !important;
  color: var(--terminal-green) !important;
  border: 1px solid var(--terminal-green) !important;
  border-radius: 0 !important;
  text-transform: uppercase;
  letter-spacing: 1px;
  box-shadow: 0 0 12px rgba(0,255,102,.25);
}

.stButton button:hover, .stFormSubmitButton button:hover {
  background: var(--terminal-green) !important;
  color: #000 !important;
  box-shadow: 0 0 24px rgba(0,255,102,.85);
}

.stAlert {
  background: rgba(0,25,8,.88) !important;
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

.status-line { color: var(--terminal-dim); margin: 4px 0; }
hr { border: none; border-top: 1px dashed rgba(0,255,102,.5); }
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: var(--terminal-green); }

.cursor-blink {
  display: inline-block;
  width: 9px;
  height: 18px;
  background: var(--terminal-green);
  margin-left: 4px;
  animation: blink .9s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>
"""

CHAT_COMPONENT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
html, body {
  margin: 0;
  padding: 0;
  background: transparent;
  font-family: 'Share Tech Mono', monospace;
}
.chat-box {
  height: 470px;
  overflow-y: auto;
  box-sizing: border-box;
  background: rgba(0,0,0,.94);
  border: 1px solid #00ff66;
  padding: 16px;
  box-shadow: inset 0 0 24px rgba(0,255,102,.18), 0 0 18px rgba(0,255,102,.22);
}
.chat-line { margin: 0 0 14px 0; }
.chat-bubble {
  border-left: 3px solid #00ff66;
  padding: 8px 10px;
  color: #00ff66;
  background: rgba(0,255,102,.055);
  text-shadow: 0 0 6px rgba(0,255,102,.65);
  overflow-wrap: anywhere;
}
.chat-bubble::before { content: "> "; color: #9cffb8; }
.chat-bubble.me {
  border-left-color: #00ddff;
  color: #8ff3ff;
  text-shadow: 0 0 6px rgba(0,204,255,.65);
}
.chat-bubble.me::before { content: "$ "; color: #8ff3ff; }
.chat-meta {
  font-size: 12px;
  color: rgba(120,255,165,.75);
  margin-top: 6px;
}
.media-label {
  display: block;
  color: rgba(156,255,184,.9);
  font-size: 12px;
  margin: 0 0 8px 0;
  letter-spacing: .6px;
}
.chat-image {
  display: block;
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
  border: 1px solid rgba(0,255,102,.65);
  box-shadow: 0 0 16px rgba(0,255,102,.18);
  background: #000;
}
.chat-audio {
  display: block;
  width: min(100%, 520px);
  filter: sepia(1) saturate(3) hue-rotate(70deg);
}
.empty-line { color: rgba(120,255,165,.75); margin-top: 14px; }
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
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
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


def epoch_now() -> int:
    return int(time.time())

# ==============================
# ROOM SETTINGS + AUTO DESTROY
# ==============================
def parse_destroy_choice(choice: str) -> int | None:
    if choice == "Never":
        return None
    return int(choice.split()[0])


def choice_from_minutes(minutes: int | None) -> str:
    if minutes is None:
        return "Never"
    return f"{minutes} menit"


def get_room_config(room: str) -> dict[str, Any]:
    settings = load_json(ROOM_SETTINGS_FILE)
    config = settings.get(room, {})
    mode = config.get("destroy_mode", "auto")
    minutes = config.get("auto_destroy_minutes", DEFAULT_AUTO_DESTROY_MINUTES)

    if mode == "never":
        minutes = None
    elif minutes not in {10, 20, 30, 40, 50, 60}:
        minutes = DEFAULT_AUTO_DESTROY_MINUTES

    return {
        "destroy_mode": "never" if minutes is None else "auto",
        "auto_destroy_minutes": minutes,
        "last_active_at": int(config.get("last_active_at", epoch_now())),
        "destroy_code_hash": config.get("destroy_code_hash", ""),
    }


def save_room_config(room: str, config: dict[str, Any]) -> None:
    settings = load_json(ROOM_SETTINGS_FILE)
    settings[room] = config
    save_json(ROOM_SETTINGS_FILE, settings)


def set_room_destroy_choice(room: str, choice: str) -> None:
    config = get_room_config(room)
    minutes = parse_destroy_choice(choice)
    config["destroy_mode"] = "never" if minutes is None else "auto"
    config["auto_destroy_minutes"] = minutes
    config.setdefault("last_active_at", epoch_now())
    save_room_config(room, config)


def mark_room_active(room: str) -> None:
    config = get_room_config(room)
    config["last_active_at"] = epoch_now()
    save_room_config(room, config)


def hash_destroy_code(room: str, code: str) -> str:
    raw = f"{room}:{code}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def destroy_room(room: str) -> None:
    rooms = load_json(CHAT_FILE)
    rooms.pop(room, None)
    save_json(CHAT_FILE, rooms)

    online = load_json(ONLINE_FILE)
    online.pop(room, None)
    save_json(ONLINE_FILE, online)

    settings = load_json(ROOM_SETTINGS_FILE)
    settings.pop(room, None)
    save_json(ROOM_SETTINGS_FILE, settings)


def destroy_room_messages(room: str) -> int:
    """Immediately remove every text/image/voice message from the active room."""
    rooms = load_json(CHAT_FILE)
    message_count = len(rooms.get(room, [])) if isinstance(rooms.get(room, []), list) else 0
    rooms[room] = []
    save_json(CHAT_FILE, rooms)
    mark_room_active(room)
    return message_count


def get_active_users_from_online(online: dict[str, Any], room: str, now: int) -> dict[str, int]:
    active: dict[str, int] = {}
    for user, last_seen in online.get(room, {}).items():
        try:
            last_seen_int = int(last_seen)
        except (TypeError, ValueError):
            continue
        if now - last_seen_int <= ONLINE_ACTIVE_SECONDS:
            active[str(user)] = last_seen_int
    return active


def purge_inactive_rooms() -> list[str]:
    """Destroy rooms whose auto-destroy timer expired after all users became inactive.

    Catatan: pada deployment Streamlit biasa, pengecekan ini berjalan saat aplikasi rerun
    atau ada browser session yang masih melakukan auto-refresh.
    """
    now = epoch_now()
    rooms = load_json(CHAT_FILE)
    online = load_json(ONLINE_FILE)
    settings = load_json(ROOM_SETTINGS_FILE)
    all_rooms = set(rooms.keys()) | set(online.keys()) | set(settings.keys())
    destroyed: list[str] = []
    changed = False

    for room in list(all_rooms):
        config = get_room_config(room)
        minutes = config.get("auto_destroy_minutes")

        active_users = get_active_users_from_online(online, room, now)
        if online.get(room) != active_users:
            online[room] = active_users
            changed = True

        if active_users:
            config["last_active_at"] = now
            settings[room] = config
            changed = True
            continue

        # Never = hanya bisa dihapus manual via Destroy Room.
        if minutes is None:
            settings[room] = config
            continue

        raw_last_seen_values = online.get(room, {}).values()
        valid_last_seen = []
        for value in raw_last_seen_values:
            try:
                valid_last_seen.append(int(value))
            except (TypeError, ValueError):
                pass

        last_active_at = int(config.get("last_active_at") or (max(valid_last_seen) if valid_last_seen else now))
        config["last_active_at"] = last_active_at

        if now - last_active_at >= int(minutes) * 60:
            rooms.pop(room, None)
            online.pop(room, None)
            settings.pop(room, None)
            destroyed.append(room)
            changed = True
        else:
            settings[room] = config

    if changed:
        save_json(CHAT_FILE, rooms)
        save_json(ONLINE_FILE, online)
        save_json(ROOM_SETTINGS_FILE, settings)

    return destroyed

# ==============================
# CHAT HELPERS
# ==============================
def make_text_message(username: str, text: str) -> dict[str, str]:
    return {
        "id": str(uuid.uuid4()),
        "type": "text",
        "username": username,
        "text": encrypt_message(text),
        "time": wib_now(),
        "created_at": str(epoch_now()),
    }


def make_media_message(
    username: str,
    media_type: str,
    data: bytes,
    mime_type: str,
    filename: str,
) -> dict[str, str]:
    encoded_payload = base64.b64encode(data).decode("ascii")
    return {
        "id": str(uuid.uuid4()),
        "type": media_type,
        "username": username,
        "payload": encrypt_message(encoded_payload),
        "mime_type": mime_type,
        "filename": filename,
        "size_bytes": str(len(data)),
        "time": wib_now(),
        "created_at": str(epoch_now()),
    }


def append_text_message(room: str, username: str, message_text: str) -> None:
    rooms = load_json(CHAT_FILE)
    rooms.setdefault(room, [])
    rooms[room].append(make_text_message(username, message_text))
    save_json(CHAT_FILE, rooms)


def append_media_message(
    room: str,
    username: str,
    media_type: str,
    data: bytes,
    mime_type: str,
    filename: str,
) -> None:
    rooms = load_json(CHAT_FILE)
    rooms.setdefault(room, [])
    rooms[room].append(make_media_message(username, media_type, data, mime_type, filename))
    save_json(CHAT_FILE, rooms)


def update_online_status(room: str, username: str) -> list[str]:
    online = load_json(ONLINE_FILE)
    now = epoch_now()
    online.setdefault(room, {})
    online[room][username] = now
    save_json(ONLINE_FILE, online)
    mark_room_active(room)

    active_users = get_active_users_from_online(online, room, now)
    return [user for user in active_users.keys() if user != username]


def validate_media_file(uploaded_file: Any, expected_prefix: str) -> tuple[bytes, str, str] | None:
    if uploaded_file is None:
        st.error("File belum dipilih.")
        return None

    data = uploaded_file.getvalue()
    if not data:
        st.error("File kosong atau gagal dibaca.")
        return None

    if len(data) > MAX_MEDIA_BYTES:
        st.error(f"Ukuran file terlalu besar. Maksimal {MAX_MEDIA_BYTES // (1024 * 1024)} MB per media.")
        return None

    mime_type = getattr(uploaded_file, "type", "") or "application/octet-stream"
    filename = getattr(uploaded_file, "name", "media_payload") or "media_payload"

    if expected_prefix == "image" and not mime_type.startswith("image/"):
        st.error("File yang dikirim bukan gambar valid.")
        return None
    if expected_prefix == "audio" and not mime_type.startswith("audio/"):
        # Sebagian browser merekam audio sebagai video/webm, tetap izinkan untuk voice note.
        if mime_type not in {"video/webm", "application/octet-stream"}:
            st.error("File yang dikirim bukan audio valid.")
            return None

    return data, mime_type, filename


def render_media_payload(msg: dict[str, Any]) -> str:
    msg_type = str(msg.get("type", "text"))
    payload_encrypted = str(msg.get("payload", ""))
    payload = decrypt_message(payload_encrypted)

    if payload.startswith("[Pesan tidak dapat didekripsi]"):
        return '<span class="media-label">[ERROR] Media tidak dapat didekripsi.</span>'

    mime_type = html.escape(str(msg.get("mime_type", "application/octet-stream")), quote=True)
    filename = html.escape(str(msg.get("filename", "media_payload")), quote=True)
    safe_payload = html.escape(payload, quote=True)

    if msg_type == "image":
        return f"""
        <span class="media-label">[IMAGE_PACKET] {filename}</span>
        <img class="chat-image" src="data:{mime_type};base64,{safe_payload}" alt="{filename}" />
        """

    if msg_type == "audio":
        return f"""
        <span class="media-label">[VOICE_PACKET] {filename}</span>
        <audio class="chat-audio" controls preload="metadata" src="data:{mime_type};base64,{safe_payload}"></audio>
        """

    return '<span class="media-label">[UNKNOWN_PACKET] Format pesan tidak dikenal.</span>'


def render_chat_box(messages: list[dict[str, Any]], username: str) -> str:
    if not messages:
        rows = '<div class="empty-line">[EMPTY] Belum ada pesan terenkripsi di room ini.</div>'
    else:
        rows = ""
        for msg in messages:
            msg_user = str(msg.get("username", "unknown"))
            msg_type = str(msg.get("type", "text"))
            is_me = msg_user == username
            css_class = "chat-bubble me" if is_me else "chat-bubble"
            safe_user = html.escape(msg_user)
            safe_time = html.escape(str(msg.get("time", "")))

            # Backward compatible untuk pesan lama yang belum punya field type.
            if msg_type == "text" or "payload" not in msg:
                safe_text = html.escape(decrypt_message(str(msg.get("text", ""))))
                content = safe_text
            else:
                content = render_media_payload(msg)

            rows += f"""
            <div class="chat-line">
              <div class="{css_class}">{content}</div>
              <div class="chat-meta">{safe_user}{' / you' if is_me else ''} :: {safe_time}</div>
            </div>
            """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><style>{CHAT_COMPONENT_CSS}</style></head>
    <body>
      <div id="chatBox" class="chat-box">{rows}</div>
      <script>
        const chatBox = document.getElementById('chatBox');
        chatBox.scrollTop = chatBox.scrollHeight;
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
          <p class="status-line">[BOOT] Secure channel initialized... terminal skin active...</p>
          <p class="status-line">[CRYPTO] Fernet encryption active...</p>
          <p class="status-line">[MODE] Private multi-room communication...</p>
          <p class="status-line">[MEDIA] Image packet + voice packet enabled...</p>
          <p class="status-line">[PURGE] Auto-destroy tersedia: Never / 10 / 20 / 30 / 40 / 50 / 60 menit...</p>
          <p class="status-line">[PANIC] Panic destroy pesan room aktif siap digunakan...</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> tuple[bool, int]:
    with st.sidebar:
        st.markdown("### SYSTEM CONTROL")
        auto_refresh_enabled = st.toggle("Aktifkan auto refresh", value=True)
        refresh_seconds = st.slider("Interval refresh", min_value=2, max_value=15, value=5, step=1)
        st.caption("Auto-refresh menjaga status online tetap aktif dan membantu pengecekan auto-destroy.")
        st.markdown("---")
        st.caption(f"Batas media: {MAX_MEDIA_BYTES // (1024 * 1024)} MB per pesan.")
    return auto_refresh_enabled, refresh_seconds


def render_auto_destroy_control(room: str) -> str:
    config = get_room_config(room)
    current_choice = choice_from_minutes(config.get("auto_destroy_minutes"))
    if current_choice not in AUTO_DESTROY_CHOICES:
        current_choice = "30 menit"

    choice = st.selectbox(
        "Auto Destroy jika tidak ada user aktif di room:",
        options=AUTO_DESTROY_CHOICES,
        index=AUTO_DESTROY_CHOICES.index(current_choice),
        help="Default 30 menit. Pilih Never jika room hanya ingin dihancurkan manual lewat Destroy Room.",
    )

    if choice != current_choice:
        set_room_destroy_choice(room, choice)
        st.success(f"Auto Destroy untuk room `{room}` diubah menjadi: {choice}")

    return choice


def render_destroy_room(room: str) -> None:
    with st.expander("Destroy Chat Room", expanded=False):
        config = get_room_config(room)
        stored_hash = str(config.get("destroy_code_hash", ""))

        st.caption("Kode destroy disimpan sebagai hash, bukan teks asli.")
        new_secret = st.text_input("Set kode destroy minimal 6 karakter:", type="password", key="new_destroy_code")
        if st.button("Set Destroy Code"):
            if len(new_secret) >= 6:
                config["destroy_code_hash"] = hash_destroy_code(room, new_secret)
                save_room_config(room, config)
                st.success("Kode destroy berhasil disimpan untuk room ini.")
            else:
                st.error("Kode destroy minimal 6 karakter.")

        destroy_key = st.text_input("Masukkan kode destroy:", type="password", key="destroy_key_input")
        if st.button("Destroy Chat Room", type="primary"):
            if not stored_hash and not config.get("destroy_code_hash"):
                st.error("Kode destroy belum diset untuk room ini.")
                return
            latest_hash = str(get_room_config(room).get("destroy_code_hash", ""))
            if destroy_key and hash_destroy_code(room, destroy_key) == latest_hash:
                destroy_room(room)
                st.success("Chat room berhasil dihancurkan. Refresh halaman untuk mulai ulang.")
                st.stop()
            else:
                st.error("Kode destroy salah.")


def render_panic_destroy(room: str) -> None:
    st.markdown("### PANIC CONTROL")
    st.caption("Tombol ini langsung menghapus semua pesan teks, gambar, dan voice di room aktif. Room, username, status online, dan setting auto-destroy tetap ada.")
    col_panic, col_status = st.columns([1, 2])
    with col_panic:
        panic_pressed = st.button("☢ PANIC DESTROY PESAN", type="primary", key="panic_destroy_messages")
    with col_status:
        st.warning("Gunakan saat darurat. Aksi ini tidak bisa di-undo.")

    if panic_pressed:
        deleted_count = destroy_room_messages(room)
        reset_media_packet("image_packet")
        reset_media_packet("voice_record_packet")
        reset_media_packet("voice_upload_packet")
        st.success(f"Panic destroy aktif. {deleted_count} pesan di room `{room}` sudah dihapus.")
        st.rerun()


def reset_media_packet(packet_name: str) -> None:
    """Reset file/audio widgets by rotating their Streamlit keys."""
    nonce_key = f"{packet_name}_nonce"
    st.session_state[nonce_key] = int(st.session_state.get(nonce_key, 0)) + 1


def render_message_composer(room: str, username: str) -> None:
    st.markdown("### SEND PACKET")

    # Streamlit file/audio widgets cannot reliably be cleared by assigning None.
    # Rotating the widget key after a successful send forces a fresh empty packet slot.
    image_nonce = int(st.session_state.get("image_packet_nonce", 0))
    voice_record_nonce = int(st.session_state.get("voice_record_packet_nonce", 0))
    voice_upload_nonce = int(st.session_state.get("voice_upload_packet_nonce", 0))

    with st.form("send_message_form", clear_on_submit=True):
        message = st.text_input("command_message:", placeholder="ketik pesan rahasia...")
        col1, col2 = st.columns([3, 1])
        send = col1.form_submit_button("Send Text")
        ping = col2.form_submit_button("Ping")

    if send and message.strip():
        append_text_message(room, username, message.strip())
        st.rerun()

    if ping:
        append_text_message(room, username, "PING!")
        st.rerun()

    image_tab, voice_tab = st.tabs(["Image Packet", "Voice Packet"])

    with image_tab:
        image_file = st.file_uploader(
            "upload_image:",
            type=ALLOWED_IMAGE_TYPES,
            accept_multiple_files=False,
            key=f"image_payload_{image_nonce}",
            help="Format: PNG, JPG/JPEG, WEBP.",
        )
        if image_file is not None:
            st.image(image_file, caption="Preview image packet", use_container_width=True)
        if st.button("Send Image", key="send_image_packet"):
            validated = validate_media_file(image_file, "image")
            if validated is not None:
                data, mime_type, filename = validated
                append_media_message(room, username, "image", data, mime_type, filename)
                reset_media_packet("image_packet")
                st.rerun()

    with voice_tab:
        recorder_supported = hasattr(st, "audio_input")
        recorded_audio = None
        if recorder_supported:
            recorded_audio = st.audio_input("record_voice:", key=f"voice_payload_record_{voice_record_nonce}")
            if recorded_audio is not None:
                st.audio(recorded_audio)
        else:
            st.caption("Recorder langsung belum tersedia di versi Streamlit ini. Gunakan upload file audio.")

        if recorder_supported and st.button("Send Recorded Voice", key="send_recorded_voice_packet"):
            validated = validate_media_file(recorded_audio, "audio")
            if validated is not None:
                data, mime_type, filename = validated
                append_media_message(room, username, "audio", data, mime_type, filename or "voice-note.wav")
                reset_media_packet("voice_record_packet")
                st.rerun()

        audio_file = st.file_uploader(
            "atau upload_audio:",
            type=ALLOWED_AUDIO_TYPES,
            accept_multiple_files=False,
            key=f"voice_payload_upload_{voice_upload_nonce}",
            help="Format: WAV, MP3, OGG, M4A, AAC, FLAC, WEBM.",
        )
        if audio_file is not None:
            st.audio(audio_file)
        if st.button("Send Uploaded Voice", key="send_uploaded_voice_packet"):
            validated = validate_media_file(audio_file, "audio")
            if validated is not None:
                data, mime_type, filename = validated
                append_media_message(room, username, "audio", data, mime_type, filename)
                reset_media_packet("voice_upload_packet")
                st.rerun()

# ==============================
# APP FLOW
# ==============================
st.markdown(APP_CSS, unsafe_allow_html=True)

destroyed_rooms = purge_inactive_rooms()

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

render_header()

if destroyed_rooms:
    st.warning("Auto-destroy menjalankan purge untuk room: " + ", ".join(destroyed_rooms))

auto_refresh_enabled, refresh_seconds = render_sidebar()
if auto_refresh_enabled:
    if st_autorefresh is not None:
        st_autorefresh(interval=refresh_seconds * 1000, key="chat_auto_refresh")
    else:
        st.warning("Auto-refresh belum aktif. Jalankan: pip install streamlit-autorefresh")

room = st.text_input("room_name:", placeholder="contoh: black-room-01")
username = st.text_input("username:", placeholder="contoh: zero_cool")

if not room or not username:
    st.info("Masukkan nama room dan username untuk mulai chat terenkripsi.")
    st.caption("Software dibuat dengan Python + Streamlit + Fernet encryption.")
    st.stop()

st.markdown("---")
st.subheader(f"Room: {room}")
st.write(f"Login sebagai: `{username}`")

auto_destroy_choice = render_auto_destroy_control(room)
online_users = update_online_status(room, username)

if auto_destroy_choice == "Never":
    st.info("Auto-destroy: NEVER. Room hanya akan hancur jika Destroy Chat Room dilakukan manual.")
else:
    st.info(
        f"Auto-destroy: {auto_destroy_choice}. Jika semua user tidak aktif/keluar dari room, "
        f"pesan akan dihancurkan otomatis setelah batas waktu tersebut."
    )

render_destroy_room(room)
render_panic_destroy(room)

messages = load_json(CHAT_FILE).get(room, [])
components.html(render_chat_box(messages, username), height=495, scrolling=False)

if online_users:
    st.success(f"Online: {', '.join(online_users)}")
else:
    st.info("Belum ada lawan bicara online di room ini.")

render_message_composer(room, username)

st.caption(
    "Pesan teks, gambar, dan suara terenkripsi di file lokal. Untuk keamanan, pilih auto-destroy atau gunakan Destroy Chat Room setelah selesai."
)
