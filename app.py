import base64
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
SHELL_SIGNATURES = [
    b"#!/bin/sh",
    b"#!/bin/bash",
    b"#!/usr/bin/env sh",
    b"#!/usr/bin/env bash",
    b"<?php",
    b"<script",
]
SHELL_KEYWORDS = [
    b"/bin/bash",
    b"/bin/sh",
    b"bash -c",
    b"sh -c",
    b"curl ",
    b"wget ",
    b"chmod ",
    b"rm -rf",
    b"nc -e",
    b"netcat",
    b"powershell",
    b"cmd.exe",
    b"eval(",
    b"system(",
    b"exec(",
]

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="centered")

# ==============================
# CSS: HACKER TERMINAL THEME
# ==============================
APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

:root {
  --green: #00ff66;
  --green-soft: #8cffae;
  --green-muted: rgba(0,255,102,.58);
  --bg: #000;
  --panel: #020b04;
  --panel2: #001604;
  --line: rgba(0,255,102,.55);
  --danger: #ff335c;
  --cyan: #00ddff;
}

#MainMenu, footer, header { visibility: hidden; }

.stApp {
  background: #000;
  color: var(--green);
  font-family: 'Share Tech Mono', monospace;
}

.stApp::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background: repeating-linear-gradient(
    to bottom,
    rgba(0,255,102,.035) 0,
    rgba(0,255,102,.035) 1px,
    transparent 2px,
    transparent 5px
  );
  opacity: .42;
  z-index: 9999;
}

.stApp::after {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  box-shadow: inset 0 0 90px rgba(0,255,102,.13);
  z-index: 9998;
}

.block-container {
  max-width: 860px;
  padding: 1.2rem 1rem 2rem 1rem;
}

h1, h2, h3, p, label, span, div, button, input, textarea {
  font-family: 'Share Tech Mono', monospace !important;
}

h1, h2, h3 {
  color: var(--green) !important;
  text-shadow: 0 0 8px rgba(0,255,102,.55);
  letter-spacing: 1px;
}

h1 {
  font-size: 1.55rem !important;
  margin-bottom: .35rem !important;
  border-bottom: 1px solid var(--line);
  padding-bottom: .45rem;
}

h1::before { content: "root@chatsecrets:~$ "; color: var(--green-soft); }

.terminal-bar {
  border: 1px solid var(--line);
  background: var(--panel);
  padding: 10px 12px;
  margin: 8px 0 14px 0;
  box-shadow: 0 0 18px rgba(0,255,102,.14);
}

.terminal-line {
  margin: 0;
  color: var(--green-soft);
  font-size: .9rem;
}

.terminal-line::before { content: "> "; color: var(--green); }

.compact-panel {
  border: 1px solid var(--line);
  background: var(--panel);
  padding: 12px;
  margin: 12px 0;
}

.stTextInput input,
.stSelectbox div[data-baseweb="select"] > div,
.stSlider,
.stTextArea textarea {
  background: #000 !important;
  color: var(--green) !important;
  border: 1px solid var(--line) !important;
  border-radius: 0 !important;
  box-shadow: none !important;
}

.stTextInput input::placeholder { color: rgba(140,255,174,.5) !important; }

.stFileUploader, .stAudioInput {
  background: var(--panel);
  border: 1px dashed var(--line);
  border-radius: 0;
  padding: 8px;
}

.stFileUploader label, .stAudioInput label { color: var(--green-soft) !important; }

.stButton button, .stFormSubmitButton button {
  background: #000 !important;
  color: var(--green) !important;
  border: 1px solid var(--green) !important;
  border-radius: 0 !important;
  text-transform: uppercase;
  letter-spacing: .8px;
  box-shadow: none !important;
}

.stButton button:hover, .stFormSubmitButton button:hover {
  background: var(--green) !important;
  color: #000 !important;
}

button[kind="primary"] {
  border-color: var(--danger) !important;
  color: var(--danger) !important;
}

button[kind="primary"]:hover {
  background: var(--danger) !important;
  color: #000 !important;
}

.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] {
  background: #000;
  border: 1px solid var(--line);
  border-bottom: none;
  border-radius: 0;
  color: var(--green-soft);
}
.stTabs [aria-selected="true"] { background: var(--panel2) !important; color: var(--green) !important; }

.stAlert {
  background: var(--panel) !important;
  color: var(--green-soft) !important;
  border: 1px solid var(--line) !important;
  border-radius: 0 !important;
}

[data-testid="stSidebar"] {
  background: #000;
  border-right: 1px solid var(--line);
}

[data-testid="stSidebar"] * { color: var(--green-soft) !important; }

hr { border: none; border-top: 1px dashed var(--line); margin: .9rem 0; }

.panic-panel {
  border: 1px solid var(--danger);
  background: rgba(255, 51, 92, .06);
  padding: 10px 12px;
  margin: 10px 0;
}

.panic-title { color: var(--danger); letter-spacing: 1px; }
.panic-copy { color: #ff9db1; margin: 2px 0 0 0; font-size: .88rem; }

.cursor-blink {
  display: inline-block;
  width: 9px;
  height: 17px;
  background: var(--green);
  margin-left: 4px;
  animation: blink .85s infinite;
}

@keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }

::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: var(--green); }
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
  height: 455px;
  overflow-y: auto;
  box-sizing: border-box;
  background: #000;
  border: 1px solid #00ff66;
  padding: 12px;
  box-shadow: inset 0 0 18px rgba(0,255,102,.12);
}
.chat-line { margin: 0 0 11px 0; }
.chat-bubble {
  border-left: 2px solid #00ff66;
  padding: 7px 9px;
  color: #00ff66;
  background: rgba(0,255,102,.045);
  overflow-wrap: anywhere;
}
.chat-bubble::before { content: "> "; color: #8cffae; }
.chat-bubble.me {
  border-left-color: #00ddff;
  color: #8ff3ff;
  background: rgba(0,221,255,.045);
}
.chat-bubble.me::before { content: "$ "; color: #8ff3ff; }
.chat-meta {
  font-size: 11px;
  color: rgba(140,255,174,.65);
  margin-top: 4px;
}
.media-label {
  display: block;
  color: rgba(140,255,174,.88);
  font-size: 11px;
  margin: 0 0 7px 0;
  letter-spacing: .6px;
}
.chat-image {
  display: block;
  max-width: min(260px, 100%);
  max-height: 220px;
  object-fit: contain;
  border: 1px solid rgba(0,255,102,.6);
  background: #000;
}
.chat-audio {
  display: block;
  width: min(100%, 420px);
  filter: sepia(1) saturate(3) hue-rotate(70deg);
}
.empty-line { color: rgba(140,255,174,.75); margin-top: 10px; }
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


def panic_clear_messages(room: str) -> int:
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

        # Never = pesan tidak dihapus otomatis; gunakan Panic Destroy bila diperlukan.
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


def detect_image_format(data: bytes) -> str | None:
    """Return the real image format from magic bytes, or None if it is not a supported image."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def is_probably_text_payload(data: bytes) -> bool:
    sample = data[:4096]
    if not sample:
        return False
    printable = sum(1 for byte in sample if byte in b"\t\n\r" or 32 <= byte <= 126)
    return printable / max(len(sample), 1) > 0.85


def looks_like_shell_payload(data: bytes) -> bool:
    """Detect common shell-script patterns in a file pretending to be an image."""
    sample = data[:4096].lstrip().lower()
    if any(sample.startswith(signature.lower()) for signature in SHELL_SIGNATURES):
        return True
    if not is_probably_text_payload(data):
        return False
    keyword_hits = sum(1 for keyword in SHELL_KEYWORDS if keyword.lower() in sample)
    shell_syntax_hits = sum(token in sample for token in [b"#!/", b"function ", b"; then", b"fi\n", b"for ", b"do\n", b"done\n"])
    return keyword_hits >= 2 or (keyword_hits >= 1 and shell_syntax_hits >= 1)


def security_destroy_for_disguised_image(room: str) -> None:
    deleted_count = panic_clear_messages(room)
    reset_media_packet("image_packet")
    st.error(
        "SECURITY ALERT: Image Packet terdeteksi sebagai file shell/script yang menyamar. "
        f"Payload diblokir dan {deleted_count} pesan di room ini langsung dihancurkan."
    )
    st.rerun()


def validate_media_file(uploaded_file: Any, expected_prefix: str, room: str | None = None) -> tuple[bytes, str, str] | None:
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

    if expected_prefix == "image":
        if looks_like_shell_payload(data) and room:
            security_destroy_for_disguised_image(room)

        real_image_format = detect_image_format(data)

        if real_image_format is None:
            st.error("File yang dikirim bukan gambar valid. Payload diblokir dan tidak disimpan.")
            return None

        normalized_filename = filename.lower()
        allowed_extension = any(normalized_filename.endswith(f".{ext}") for ext in ALLOWED_IMAGE_TYPES)
        if not mime_type.startswith("image/") or not allowed_extension:
            st.error("Metadata file tidak cocok dengan Image Packet. Payload diblokir dan tidak disimpan.")
            return None

        # Pastikan MIME yang disimpan mengikuti hasil magic-byte, bukan hanya klaim browser.
        mime_type = "image/jpeg" if real_image_format == "jpg" else f"image/{real_image_format}"

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
# SOUND NOTIFICATION HELPERS
# ==============================
def latest_foreign_message_signature(messages: list[dict[str, Any]], username: str) -> str:
    """Return a stable signature for the latest message sent by another user."""
    for msg in reversed(messages):
        if str(msg.get("username", "")) != username:
            return str(msg.get("id") or f"{msg.get('created_at', '')}:{msg.get('time', '')}:{msg.get('username', '')}")
    return ""


def render_hacker_sound_runtime(show_unlock_button: bool = True) -> None:
    """Install a reusable browser-side sound runtime and optionally show an unlock/test button."""
    button_html = """
      <button id="unlockSound" class="sound-btn">UNLOCK / TEST SOUND</button>
      <span id="soundState" class="sound-state">sound=standby</span>
    """ if show_unlock_button else """<span id="soundState" class="sound-state">sound=armed</span>"""

    components.html(
        f"""
        <style>
          body {{ margin: 0; background: transparent; font-family: 'Share Tech Mono', monospace; }}
          .sound-wrap {{ display: flex; align-items: center; gap: 8px; color: #00ff66; }}
          .sound-btn {{
            cursor: pointer;
            border: 1px solid rgba(0,255,102,.85);
            background: #020b04;
            color: #00ff66;
            padding: 7px 10px;
            border-radius: 4px;
            font-family: 'Share Tech Mono', monospace;
            box-shadow: 0 0 10px rgba(0,255,102,.18);
          }}
          .sound-btn:hover {{ background: rgba(0,255,102,.12); }}
          .sound-state {{ font-size: 12px; color: rgba(0,255,102,.75); }}
        </style>
        <div class="sound-wrap">{button_html}</div>
        <script>
        (function () {{
          function getRoot() {{
            try {{
              if (window.parent && window.parent !== window) return window.parent;
            }} catch (error) {{}}
            return window;
          }}

          const root = getRoot();
          const storage = (() => {{
            try {{ return root.localStorage || window.localStorage; }} catch (error) {{ return null; }}
          }})();
          const AudioContextClass = root.AudioContext || root.webkitAudioContext || window.AudioContext || window.webkitAudioContext;

          function isUnlocked() {{
            try {{
              return root.__chatsecretsSoundUnlocked === true ||
                     (storage && storage.getItem("chatsecrets_sound_unlocked") === "1");
            }} catch (error) {{
              return root.__chatsecretsSoundUnlocked === true;
            }}
          }}

          function markUnlocked() {{
            root.__chatsecretsSoundUnlocked = true;
            try {{ if (storage) storage.setItem("chatsecrets_sound_unlocked", "1"); }} catch (error) {{}}
          }}

          function getContext() {{
            if (!AudioContextClass) return null;
            if (!root.__chatsecretsAudioContext) {{
              root.__chatsecretsAudioContext = new AudioContextClass();
            }}
            return root.__chatsecretsAudioContext;
          }}

          async function playHackerBeep(forceUnlock) {{
            try {{
              const ctx = getContext();
              if (!ctx) return false;

              if (forceUnlock) markUnlocked();
              if (ctx.state === "suspended") await ctx.resume();
              if (ctx.state === "suspended") return false;
              if (!forceUnlock && !isUnlocked()) return false;

              const now = ctx.currentTime + 0.025;
              const master = ctx.createGain();
              master.gain.setValueAtTime(0.0001, now);
              master.gain.exponentialRampToValueAtTime(0.10, now + 0.018);
              master.gain.exponentialRampToValueAtTime(0.0001, now + 0.90);
              master.connect(ctx.destination);

              const sequence = [
                {{ f: 740,  t: 0.00, d: 0.075, type: "square" }},
                {{ f: 1110, t: 0.08, d: 0.065, type: "square" }},
                {{ f: 1480, t: 0.16, d: 0.070, type: "sawtooth" }},
                {{ f: 620,  t: 0.29, d: 0.090, type: "square" }},
                {{ f: 930,  t: 0.40, d: 0.110, type: "triangle" }}
              ];

              sequence.forEach((note) => {{
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                const start = now + note.t;
                const end = start + note.d;

                osc.type = note.type;
                osc.frequency.setValueAtTime(note.f, start);
                osc.frequency.exponentialRampToValueAtTime(Math.max(50, note.f * 0.66), end);

                gain.gain.setValueAtTime(0.0001, start);
                gain.gain.exponentialRampToValueAtTime(0.50, start + 0.010);
                gain.gain.exponentialRampToValueAtTime(0.0001, end);

                osc.connect(gain);
                gain.connect(master);
                osc.start(start);
                osc.stop(end + 0.03);
              }});

              const length = Math.floor(ctx.sampleRate * 0.10);
              const noiseBuffer = ctx.createBuffer(1, length, ctx.sampleRate);
              const output = noiseBuffer.getChannelData(0);
              for (let i = 0; i < length; i++) output[i] = (Math.random() * 2 - 1) * 0.16;

              const noise = ctx.createBufferSource();
              const noiseGain = ctx.createGain();
              noise.buffer = noiseBuffer;
              noiseGain.gain.setValueAtTime(0.0001, now + 0.53);
              noiseGain.gain.exponentialRampToValueAtTime(0.10, now + 0.55);
              noiseGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.66);
              noise.connect(noiseGain);
              noiseGain.connect(master);
              noise.start(now + 0.53);
              noise.stop(now + 0.68);
              return true;
            }} catch (error) {{
              return false;
            }}
          }}

          root.__chatsecretsPlayHackerSound = playHackerBeep;
          root.__chatsecretsUnlockHackerSound = async function () {{
            markUnlocked();
            return await playHackerBeep(true);
          }};

          const state = document.getElementById("soundState");
          const button = document.getElementById("unlockSound");
          function refreshState() {{
            if (!state) return;
            state.textContent = isUnlocked() ? "sound=unlocked" : "sound=locked_click_unlock";
          }}

          refreshState();
          if (button) {{
            button.addEventListener("click", async function () {{
              button.disabled = true;
              button.textContent = "TESTING...";
              const ok = await root.__chatsecretsUnlockHackerSound();
              button.textContent = ok ? "SOUND ARMED" : "CLICK AGAIN";
              button.disabled = false;
              refreshState();
            }});
          }}
        }})();
        </script>
        """,
        height=48 if show_unlock_button else 22,
    )


def render_hacker_sound_alert() -> None:
    """Ask the browser-side runtime to play a short terminal-style synth alert."""
    components.html(
        """
        <script>
        (async function () {
          function getRoot() {
            try {
              if (window.parent && window.parent !== window) return window.parent;
            } catch (error) {}
            return window;
          }

          const root = getRoot();
          try {
            if (typeof root.__chatsecretsPlayHackerSound === "function") {
              await root.__chatsecretsPlayHackerSound(false);
            }
          } catch (error) {}
        })();
        </script>
        """,
        height=0,
    )

# ==============================
# UI HELPERS
# ==============================
def render_header() -> None:
    st.markdown(
        """
        <h1>./chatsecrets --stealth <span class="cursor-blink"></span></h1>
        <div class="terminal-bar">
          <p class="terminal-line">encrypted_room=on | media_packet=on | hacker_sound=armed | panic_destroy=armed | shell_image_guard=on</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> tuple[bool, int, bool]:
    with st.sidebar:
        st.markdown("### ./system")
        auto_refresh_enabled = st.toggle("auto_refresh", value=True)
        refresh_seconds = st.slider("refresh_sec", min_value=2, max_value=15, value=5, step=1)
        sound_enabled = st.toggle("hacker_sound", value=True, help="Putar efek suara terminal saat ada pesan baru masuk dari user lain.")
        if sound_enabled:
            render_hacker_sound_runtime(show_unlock_button=True)
            st.caption("Klik UNLOCK / TEST SOUND sekali jika browser memblokir audio.")
        st.caption(f"media_limit={MAX_MEDIA_BYTES // (1024 * 1024)}MB")
    return auto_refresh_enabled, refresh_seconds, sound_enabled


def render_auto_destroy_control(room: str) -> str:
    config = get_room_config(room)
    current_choice = choice_from_minutes(config.get("auto_destroy_minutes"))
    if current_choice not in AUTO_DESTROY_CHOICES:
        current_choice = "30 menit"

    choice = st.selectbox(
        "auto_destroy_idle:",
        options=AUTO_DESTROY_CHOICES,
        index=AUTO_DESTROY_CHOICES.index(current_choice),
        help="Default 30 menit. Pilih Never jika pesan hanya ingin dihancurkan lewat Panic Destroy.",
    )

    if choice != current_choice:
        set_room_destroy_choice(room, choice)
        st.success(f"Auto Destroy untuk room `{room}` diubah menjadi: {choice}")

    return choice


def render_panic_destroy(room: str) -> None:
    st.markdown(
        """
        <div class="panic-panel">
          <div class="panic-title">[panic_destroy]</div>
          <p class="panic-copy">hapus semua pesan room aktif; room dan config tetap ada</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    panic_pressed = st.button("PANIC DESTROY", type="primary", key="panic_destroy_messages", use_container_width=True)

    if panic_pressed:
        deleted_count = panic_clear_messages(room)
        reset_media_packet("image_packet")
        reset_media_packet("voice_record_packet")
        reset_media_packet("voice_upload_packet")
        st.success(f"panic_destroy=success | deleted={deleted_count} | room={room}")
        st.rerun()


def reset_media_packet(packet_name: str) -> None:
    """Reset file/audio widgets by rotating their Streamlit keys."""
    nonce_key = f"{packet_name}_nonce"
    st.session_state[nonce_key] = int(st.session_state.get(nonce_key, 0)) + 1


def render_message_composer(room: str, username: str) -> None:
    st.markdown("### ./send_packet")

    # Streamlit file/audio widgets cannot reliably be cleared by assigning None.
    # Rotating the widget key after a successful send forces a fresh empty packet slot.
    image_nonce = int(st.session_state.get("image_packet_nonce", 0))
    voice_record_nonce = int(st.session_state.get("voice_record_packet_nonce", 0))
    voice_upload_nonce = int(st.session_state.get("voice_upload_packet_nonce", 0))

    with st.form("send_message_form", clear_on_submit=True):
        message = st.text_input("msg:", placeholder="type encrypted message...")
        col1, col2 = st.columns([3, 1])
        send = col1.form_submit_button("SEND")
        ping = col2.form_submit_button("PING")

    if send and message.strip():
        append_text_message(room, username, message.strip())
        st.rerun()

    if ping:
        append_text_message(room, username, "PING!")
        st.rerun()

    image_tab, voice_tab = st.tabs(["image_packet", "voice_packet"])

    with image_tab:
        image_file = st.file_uploader(
            "upload_image:",
            type=ALLOWED_IMAGE_TYPES,
            accept_multiple_files=False,
            key=f"image_payload_{image_nonce}",
            help="Format: PNG, JPG/JPEG, WEBP. File divalidasi dari magic bytes; shell/script yang menyamar akan memicu destroy pesan.",
        )
        if image_file is not None:
            st.image(image_file, caption="preview", width=220)
        if st.button("SEND IMAGE", key="send_image_packet"):
            validated = validate_media_file(image_file, "image", room=room)
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

        if recorder_supported and st.button("SEND RECORDED VOICE", key="send_recorded_voice_packet"):
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
        if st.button("SEND UPLOADED VOICE", key="send_uploaded_voice_packet"):
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

auto_refresh_enabled, refresh_seconds, sound_enabled = render_sidebar()
if sound_enabled:
    render_hacker_sound_runtime(show_unlock_button=False)
if auto_refresh_enabled:
    if st_autorefresh is not None:
        st_autorefresh(interval=refresh_seconds * 1000, key="chat_auto_refresh")
    else:
        st.warning("Auto-refresh belum aktif. Jalankan: pip install streamlit-autorefresh")

col_room, col_user = st.columns(2)
with col_room:
    room = st.text_input("room:", placeholder="black-room-01")
with col_user:
    username = st.text_input("user:", placeholder="zero_cool")

if not room or not username:
    st.info("input room + user untuk masuk terminal")
    st.caption("python/streamlit/fernet")
    st.stop()

st.markdown("---")
st.markdown(f"### ./room --name `{room}` --user `{username}`")

auto_destroy_choice = render_auto_destroy_control(room)
online_users = update_online_status(room, username)

if auto_destroy_choice == "Never":
    st.info("auto_destroy=never | panic_destroy_only=true")
else:
    st.info(f"auto_destroy={auto_destroy_choice} | trigger=no_active_user")

render_panic_destroy(room)

messages = load_json(CHAT_FILE).get(room, [])

latest_foreign_signature = latest_foreign_message_signature(messages, username)
last_seen_signature_key = f"last_seen_foreign_message::{room}::{username}"
previous_foreign_signature = st.session_state.get(last_seen_signature_key, "")

if latest_foreign_signature and previous_foreign_signature and latest_foreign_signature != previous_foreign_signature and sound_enabled:
    render_hacker_sound_alert()

st.session_state[last_seen_signature_key] = latest_foreign_signature

components.html(render_chat_box(messages, username), height=495, scrolling=False)

if online_users:
    st.success(f"online={', '.join(online_users)}")
else:
    st.info("online=none")

render_message_composer(room, username)

st.caption("encrypted_local_storage=true | use panic_destroy/manual_destroy after session")
