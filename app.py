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
  height: 430px;
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
def make_message(username: str, text: str) -> dict[str, str]:
    return {
        "id": str(uuid.uuid4()),
        "username": username,
        "text": encrypt_message(text),
        "time": wib_now(),
        "created_at": str(epoch_now()),
    }


def append_message(room: str, username: str, message_text: str) -> None:
    rooms = load_json(CHAT_FILE)
    rooms.setdefault(room, [])
    rooms[room].append(make_message(username, message_text))
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


def render_chat_box(messages: list[dict[str, Any]], username: str) -> str:
    if not messages:
        rows = '<div class="empty-line">[EMPTY] Belum ada pesan terenkripsi di room ini.</div>'
    else:
        rows = ""
        for msg in messages:
            msg_user = str(msg.get("username", "unknown"))
            is_me = msg_user == username
            css_class = "chat-bubble me" if is_me else "chat-bubble"
            safe_user = html.escape(msg_user)
            safe_text = html.escape(decrypt_message(str(msg.get("text", ""))))
            safe_time = html.escape(str(msg.get("time", "")))
            rows += f"""
            <div class="chat-line">
              <div class="{css_class}">{safe_text}</div>
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
          <p class="status-line">[PURGE] Auto-destroy tersedia: Never / 10 / 20 / 30 / 40 / 50 / 60 menit...</p>
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

messages = load_json(CHAT_FILE).get(room, [])
components.html(render_chat_box(messages, username), height=455, scrolling=False)

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

st.caption(
    "Pesan terenkripsi di file lokal. Untuk keamanan, pilih auto-destroy atau gunakan Destroy Chat Room setelah selesai."
)
