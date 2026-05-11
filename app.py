import base64
import hashlib
import html
import io
import json
import math
import os
import secrets
import struct
import time
import uuid
import wave
from urllib.parse import quote
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
APP_ICON = ""
FERNET_KEY_FILE = "fernet.key"
CHAT_FILE = "chat_rooms.json"
ONLINE_FILE = "online_status.json"
DESTROYED_ROOMS_FILE = "destroyed_rooms.json"
PRIVATE_LINKS_FILE = "private_links.json"
ADMIN_PASSWORD_FILE = "admin_password.txt"
PRIVATE_ACCESS_TOKEN_PARAM = "access"
PRIVATE_ROOM_PARAM = "room"
ROOM_INPUT_KEY = "room_name_input"
USERNAME_INPUT_KEY = "username_input"
WIB = timezone(timedelta(hours=7))

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="centered")

# ==============================
# CSS: MAIN STREAMLIT PAGE
# ==============================
APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

:root {
  --terminal-bg: #020403;
  --terminal-green: #00ff66;
  --terminal-dim: rgba(120, 255, 165, 0.82);
  --terminal-panel: rgba(0, 18, 7, 0.92);
  --terminal-danger: #ff3131;
}

html, body, [data-testid="stAppViewContainer"] {
  background: radial-gradient(circle at top, #082313 0%, #020403 40%, #000 100%) !important;
  color: var(--terminal-green) !important;
  font-family: 'Share Tech Mono', monospace !important;
}

[data-testid="stSidebar"] {
  background: #010301 !important;
  border-right: 1px solid rgba(0,255,102,.34);
}

[data-testid="stSidebar"] * {
  color: var(--terminal-green) !important;
  font-family: 'Share Tech Mono', monospace !important;
}

h1, h2, h3, p, label, span, div, textarea, input, button {
  font-family: 'Share Tech Mono', monospace !important;
}

h1, h2, h3 {
  color: var(--terminal-green) !important;
  text-shadow: 0 0 10px rgba(0,255,102,.75);
  letter-spacing: 1px;
}

[data-testid="stTextInput"] input {
  background: rgba(0, 0, 0, 0.86) !important;
  color: var(--terminal-green) !important;
  border: 1px solid rgba(0,255,102,.65) !important;
  border-radius: 0 !important;
  box-shadow: inset 0 0 14px rgba(0,255,102,.12);
}

.stButton > button, [data-testid="stFormSubmitButton"] button {
  background: #001a08 !important;
  color: var(--terminal-green) !important;
  border: 1px solid var(--terminal-green) !important;
  border-radius: 0 !important;
  text-transform: uppercase;
  letter-spacing: 1px;
  box-shadow: 0 0 10px rgba(0,255,102,.16);
}

.stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
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

.panic-panel {
  border: 1px solid rgba(255,49,49,.75);
  box-shadow: 0 0 20px rgba(255,49,49,.22);
  padding: 12px;
  background: rgba(30, 0, 0, .45);
  margin-top: 12px;
}

.panic-title {
  color: var(--terminal-danger);
  text-shadow: 0 0 10px rgba(255,49,49,.72);
  margin-bottom: 8px;
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
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_json(path: str, data: dict[str, Any]) -> None:
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


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


def wib_timestamp() -> str:
    return datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")

# ==============================
# PRIVATE LINK + ADMIN HELPERS
# ==============================
def get_query_param(name: str) -> str:
    """Return a query-param value with compatibility for older/newer Streamlit."""
    try:
        value = st.query_params.get(name, "")
    except Exception:
        try:
            params = st.experimental_get_query_params()
            value = params.get(name, "")
        except Exception:
            value = ""

    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value) if value is not None else ""


def get_private_links() -> dict[str, Any]:
    return load_json(PRIVATE_LINKS_FILE)


def save_private_links(links: dict[str, Any]) -> None:
    save_json(PRIVATE_LINKS_FILE, links)


def get_admin_password() -> str:
    """Use env secret first; otherwise create a local random password once."""
    env_password = os.environ.get("CHATSECRETS_ADMIN_PASSWORD", "").strip()
    if env_password:
        return env_password

    if os.path.exists(ADMIN_PASSWORD_FILE):
        try:
            with open(ADMIN_PASSWORD_FILE, "r", encoding="utf-8") as file:
                password = file.read().strip()
            if password:
                return password
        except OSError:
            pass

    password = secrets.token_urlsafe(18)
    with open(ADMIN_PASSWORD_FILE, "w", encoding="utf-8") as file:
        file.write(password)
    try:
        os.chmod(ADMIN_PASSWORD_FILE, 0o600)
    except OSError:
        pass
    return password


def require_admin_login() -> bool:
    if st.session_state.get("admin_authenticated"):
        return True

    st.info("Masukkan password admin untuk membuat dan mengelola private link.")
    st.caption("Set env `CHATSECRETS_ADMIN_PASSWORD` untuk password permanen. Jika belum diset, aplikasi membuat `admin_password.txt` otomatis di folder project.")
    password = st.text_input("Admin password:", type="password", key="admin_password_input")
    if st.button("Login Admin", use_container_width=True):
        if password and password == get_admin_password():
            st.session_state["admin_authenticated"] = True
            st.success("Login admin berhasil.")
            st.rerun()
        else:
            st.error("Password admin salah.")
    return False


def create_private_link(room: str, created_by: str = "admin") -> tuple[str, str]:
    clean_room = sanitize_room_name(room)
    token = secrets.token_urlsafe(24)
    links = get_private_links()
    links[token] = {
        "room": clean_room,
        "active": True,
        "created_at": wib_timestamp(),
        "created_by": created_by,
    }
    save_private_links(links)
    relative_link = f"?{PRIVATE_ROOM_PARAM}={quote(clean_room, safe='')}&{PRIVATE_ACCESS_TOKEN_PARAM}={quote(token, safe='')}"
    return token, relative_link


def validate_private_access() -> tuple[bool, str, str]:
    token = get_query_param(PRIVATE_ACCESS_TOKEN_PARAM).strip()
    room_from_url = sanitize_room_name(get_query_param(PRIVATE_ROOM_PARAM))
    if not token:
        return False, "", "Private access token tidak ditemukan."

    link_data = get_private_links().get(token)
    if not isinstance(link_data, dict):
        return False, "", "Private link tidak valid atau sudah dihapus."

    if not link_data.get("active", True):
        return False, "", "Private link sudah dinonaktifkan oleh admin."

    linked_room = sanitize_room_name(str(link_data.get("room", "")))
    if not linked_room:
        return False, "", "Private link rusak: room tidak ditemukan."

    if room_from_url and room_from_url != linked_room:
        return False, "", "Private link tidak cocok dengan room pada URL."

    if is_room_destroyed(linked_room):
        return False, linked_room, "Room pada private link ini sudah dihancurkan."

    return True, linked_room, token


def render_full_reload_script(remove_query_params: bool = False) -> None:
    target = "window.parent.location.pathname" if remove_query_params else "window.parent.location.href"
    components.html(
        f"""
        <!doctype html>
        <html>
        <body>
          <script>
            setTimeout(function() {{
              window.parent.location.replace({target});
            }}, 80);
          </script>
        </body>
        </html>
        """,
        height=0,
        scrolling=False,
    )


def render_private_link_builder(relative_link: str) -> None:
    relative_js = json.dumps(relative_link)
    components.html(
        f"""
        <!doctype html>
        <html>
        <body style="margin:0;padding:0;background:transparent;font-family:monospace;color:#00ff66;">
          <div style="border:1px solid #00ff66;padding:10px;background:#020403;">
            <div style="margin-bottom:8px;">PRIVATE LINK:</div>
            <input id="privateLink" readonly style="width:100%;box-sizing:border-box;background:#000;color:#00ff66;border:1px solid #00ff66;padding:8px;font-family:monospace;" />
            <button id="copyLink" style="margin-top:8px;background:#001a08;color:#00ff66;border:1px solid #00ff66;padding:7px 10px;font-family:monospace;cursor:pointer;">COPY LINK</button>
            <span id="copyStatus" style="margin-left:8px;font-size:12px;"></span>
          </div>
          <script>
            const relative = {relative_js};
            const full = window.parent.location.origin + window.parent.location.pathname + relative;
            const input = document.getElementById('privateLink');
            const status = document.getElementById('copyStatus');
            input.value = full;
            document.getElementById('copyLink').addEventListener('click', async () => {{
              try {{
                await navigator.clipboard.writeText(full);
                status.textContent = 'copied';
              }} catch (e) {{
                input.focus();
                input.select();
                status.textContent = 'select manual';
              }}
            }});
          </script>
        </body>
        </html>
        """,
        height=125,
        scrolling=False,
    )

# ==============================
# ROOM DESTROY HELPERS
# ==============================
def sanitize_room_name(room: str) -> str:
    return room.strip()


def get_destroyed_rooms() -> dict[str, Any]:
    return load_json(DESTROYED_ROOMS_FILE)


def is_room_destroyed(room: str) -> bool:
    clean_room = sanitize_room_name(room)
    if not clean_room:
        return False
    return clean_room in get_destroyed_rooms()


def destroy_room_completely(room: str, username: str = "system", reason: str = "panic") -> None:
    """Delete chat data, online presence, and mark room as destroyed.

    The destroyed-room marker prevents the same room from being silently recreated
    by users whose browser still has the old room name in session state.
    """
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

    private_links = get_private_links()
    private_links_changed = False
    for token, link_data in private_links.items():
        if not isinstance(link_data, dict):
            continue
        if sanitize_room_name(str(link_data.get("room", ""))) == clean_room:
            link_data["active"] = False
            link_data["revoked_at"] = wib_timestamp()
            link_data["revoked_reason"] = f"room_destroyed:{reason}"
            private_links[token] = link_data
            private_links_changed = True
    if private_links_changed:
        save_private_links(private_links)


def clear_current_room_session(room: str | None = None) -> None:
    if ROOM_INPUT_KEY in st.session_state:
        st.session_state[ROOM_INPUT_KEY] = ""
    st.session_state.pop("last_message_signature", None)
    if room:
        st.session_state["destroyed_room_notice"] = sanitize_room_name(room)


def panic_destroy_current_room(room: str, username: str) -> None:
    clean_room = sanitize_room_name(room)
    destroy_room_completely(clean_room, username=username, reason="panic_button")
    clear_current_room_session(clean_room)
    st.session_state["force_browser_reload_after_destroy"] = True


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
        st.session_state["force_browser_reload_after_destroy"] = True
    else:
        st.session_state["destroy_code_error"] = True


def auto_clear_destroyed_room_before_widgets() -> None:
    """Kick any stale browser session out of a destroyed room before widgets render."""
    room_in_session = sanitize_room_name(str(st.session_state.get(ROOM_INPUT_KEY, "")))
    if room_in_session and is_room_destroyed(room_in_session):
        clear_current_room_session(room_in_session)

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
    clean_room = sanitize_room_name(room)
    if is_room_destroyed(clean_room):
        st.session_state["blocked_destroyed_room"] = clean_room
        clear_current_room_session(clean_room)
        return

    rooms = load_json(CHAT_FILE)
    rooms.setdefault(clean_room, [])
    rooms[clean_room].append(make_message(username, message_text))
    save_json(CHAT_FILE, rooms)

# ==============================
# AUDIO HELPERS
# ==============================
def build_hacker_wav_data_uri() -> str:
    """Generate a short hacker-style beep as an inline WAV data URI."""
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


HACKER_SOUND_DATA_URI = build_hacker_wav_data_uri()


def render_page_sound_trigger(sound_data_uri: str) -> str:
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
          <p class="status-line">[BOOT] Secure channel initialized... Dark Mode recommended.. Screen must be on..</p>
          <p class="status-line">[CRYPTO] Fernet encryption active..</p>
          <p class="status-line">[MODE] Private multi-room communication..</p>
          <p class="status-line">[WARNING] Destroy room after use for maximum privacy..</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> tuple[str, bool, int, bool, bool]:
    with st.sidebar:
        st.markdown("### NAVIGATION")
        page_mode = st.radio("Halaman", ["Chat", "Admin"], index=0, key="page_mode")
        st.markdown("### SYSTEM CONTROL")
        auto_refresh_enabled = st.toggle("Aktifkan auto refresh", value=True)
        refresh_seconds = st.slider("Interval refresh", min_value=2, max_value=15, value=3, step=1)
        sound_enabled = st.toggle("Suara pesan masuk", value=True)
        test_sound_requested = st.button("Test Hacker Sound", use_container_width=True)
        st.caption("Klik Test Hacker Sound sekali. Setelah browser mengizinkan audio, pesan masuk dari user lain akan berbunyi otomatis.")
        st.caption("Room hanya bisa dibuka lewat private link dari admin.")
        return page_mode, auto_refresh_enabled, refresh_seconds, sound_enabled, test_sound_requested


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
        user for user, last_seen in online.get(clean_room, {}).items()
        if user != username and now_epoch - int(last_seen) <= 10
    ]


def render_admin_page() -> None:
    st.subheader("Admin // Private Link Control")
    st.write("Buat private link untuk room. User hanya bisa masuk chat jika membuka URL yang membawa token akses valid.")

    if not require_admin_login():
        st.stop()

    with st.form("create_private_link_form", clear_on_submit=False):
        admin_name = st.text_input("Admin name:", value="admin", key="admin_creator_name")
        target_room = st.text_input("Room untuk private link:", placeholder="contoh: black-room-01", key="admin_target_room")
        create_link = st.form_submit_button("Create Private Link")

    if create_link:
        clean_room = sanitize_room_name(target_room)
        if not clean_room:
            st.error("Nama room tidak boleh kosong.")
        elif is_room_destroyed(clean_room):
            st.error("Room ini sudah dihancurkan. Gunakan nama room baru.")
        else:
            token, relative_link = create_private_link(clean_room, created_by=admin_name.strip() or "admin")
            st.session_state["last_private_relative_link"] = relative_link
            st.session_state["last_private_token"] = token
            st.session_state["last_private_room"] = clean_room
            st.success("Private link berhasil dibuat.")

    last_link = st.session_state.get("last_private_relative_link")
    if last_link:
        st.markdown("#### Link terbaru")
        render_private_link_builder(str(last_link))
        st.caption("Bagikan link ini ke user yang boleh masuk. Tanpa token pada link, room tidak bisa dibuka.")

    st.markdown("---")
    st.markdown("#### Private link aktif")
    links = get_private_links()
    if not links:
        st.info("Belum ada private link.")
        return

    for token, data in sorted(links.items(), key=lambda item: str(item[1].get("created_at", "")), reverse=True):
        if not isinstance(data, dict):
            continue
        room_name = sanitize_room_name(str(data.get("room", "")))
        active = bool(data.get("active", True))
        created_at = str(data.get("created_at", "-"))
        created_by = str(data.get("created_by", "admin"))
        relative_link = f"?{PRIVATE_ROOM_PARAM}={quote(room_name, safe='')}&{PRIVATE_ACCESS_TOKEN_PARAM}={quote(token, safe='')}"
        status = "ACTIVE" if active else "REVOKED"
        with st.expander(f"{room_name} // {status} // {created_at}", expanded=False):
            st.write(f"Created by: `{created_by}`")
            st.code(relative_link, language="text")
            col_a, col_b, col_c = st.columns(3)
            if active:
                if col_a.button("Revoke", key=f"revoke_{token}"):
                    links[token]["active"] = False
                    links[token]["revoked_at"] = wib_timestamp()
                    save_private_links(links)
                    st.rerun()
            else:
                if col_a.button("Activate", key=f"activate_{token}"):
                    links[token]["active"] = True
                    links[token].pop("revoked_at", None)
                    save_private_links(links)
                    st.rerun()
            if col_b.button("Delete Link", key=f"delete_{token}"):
                links.pop(token, None)
                save_private_links(links)
                st.rerun()
            if col_c.button("Copy as latest", key=f"copy_latest_{token}"):
                st.session_state["last_private_relative_link"] = relative_link
                st.session_state["last_private_token"] = token
                st.session_state["last_private_room"] = room_name
                st.rerun()

def render_destroy_room(room: str, username: str) -> None:
    clean_room = sanitize_room_name(room)
    with st.expander("Destroy / Panic Room", expanded=False):
        st.markdown(
            """
            <div class="panic-panel">
              <div class="panic-title">[PANIC ROOM]</div>
              <div>Tekan tombol ini untuk menghapus data room, menghapus status online room, mengunci nama room, lalu mengeluarkan user dari room.</div>
            </div>
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

        st.markdown("---")
        st.caption("Opsional: pakai kode destroy kalau ingin tombol destroy dengan verifikasi.")
        secret_key = f"destroy_secret_{clean_room}"
        if secret_key not in st.session_state:
            st.session_state[secret_key] = ""

        new_secret = st.text_input("Set kode destroy minimal 6 karakter:", type="password", key=f"new_destroy_secret_{clean_room}")
        if st.button("Set Destroy Code", key=f"set_destroy_code_{clean_room}"):
            if len(new_secret) >= 6:
                st.session_state[secret_key] = new_secret
                st.success("Kode destroy berhasil disimpan untuk room ini.")
            else:
                st.error("Kode destroy minimal 6 karakter.")

        st.text_input("Masukkan kode destroy:", type="password", key="destroy_key_input")
        st.button(
            "Destroy Chat Room dengan Kode",
            use_container_width=True,
            key=f"destroy_room_code_{clean_room}",
            on_click=destroy_current_room_with_code,
            args=(clean_room, username),
        )

# ==============================
# APP FLOW
# ==============================
st.markdown(APP_CSS, unsafe_allow_html=True)

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

# Important: clear stale destroyed room before widgets are created.
auto_clear_destroyed_room_before_widgets()

render_header()
page_mode, auto_refresh_enabled, refresh_seconds, sound_enabled, test_sound_requested = render_sidebar()

if st.session_state.pop("force_browser_reload_after_destroy", False):
    st.success("Room dihancurkan. Browser akan di-refresh dan query private link dibersihkan.")
    render_full_reload_script(remove_query_params=True)
    st.stop()

if page_mode == "Admin":
    render_admin_page()
    st.stop()

valid_access, linked_room, access_status = validate_private_access()
if not valid_access:
    st.error(access_status)
    st.info("Room tidak bisa dibuka manual. Minta private link dari admin, atau masuk ke halaman Admin untuk membuat link.")
    st.caption("Format link: `?room=nama-room&access=token-rahasia`.")
    if linked_room:
        render_full_reload_script(remove_query_params=True)
    st.stop()

room = sanitize_room_name(linked_room)
st.session_state[ROOM_INPUT_KEY] = room

if auto_refresh_enabled:
    if st_autorefresh is not None:
        st_autorefresh(interval=refresh_seconds * 1000, key="chat_auto_refresh")
    else:
        st.warning("Auto-refresh belum aktif. Jalankan: pip install streamlit-autorefresh")

notice_room = st.session_state.pop("destroyed_room_notice", None)
if notice_room:
    st.success(f"Room `{notice_room}` sudah dihancurkan. Data terhapus, status online dihapus, private link tidak bisa dipakai, dan browser akan keluar dari room.")

if st.session_state.pop("destroy_code_error", False):
    st.error("Kode destroy salah atau belum diset.")

if room and is_room_destroyed(room):
    st.error("Room ini sudah dihancurkan dan tidak bisa dipakai lagi.")
    render_full_reload_script(remove_query_params=True)
    st.stop()

st.session_state["locked_room_name_display"] = room
st.text_input(
    "room_name:",
    value=room,
    disabled=True,
    key="locked_room_name_display",
    help="Room dikunci dari private link. User tanpa token tidak bisa masuk.",
)
username = st.text_input(
    "username:",
    placeholder="contoh: zero_cool",
    key=USERNAME_INPUT_KEY,
)
username = username.strip()

if not username:
    st.info("Masukkan username untuk mulai chat terenkripsi lewat private link ini.")
    st.caption("Software dibuat dengan Python + Streamlit + Fernet encryption.")
    st.stop()

online_users = update_online_status(room, username)

st.markdown("---")
st.subheader(f"Room: {room}")
st.write(f"Login sebagai: `{username}`")
st.info(
    f"Private link verified. Auto-refresh: {'ON' if auto_refresh_enabled else 'OFF'} "
    f"setiap {refresh_seconds} detik. Suara: {'ON' if sound_enabled else 'OFF'}."
)

render_destroy_room(room, username)

# Stop immediately if a callback destroyed the room and cleared the field.
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

if online_users:
    st.success(f"Online: {', '.join(online_users)}")
else:
    st.info("Belum ada lawan bicara online di room ini.")

if send and message.strip():
    append_message(room, username, message.strip())
    st.rerun()

if ping:
    append_message(room, username, "PING!")
    st.rerun()

st.caption("Pesan terenkripsi di file lokal. Untuk keamanan, gunakan Panic Room / Destroy Room setelah selesai digunakan.")
