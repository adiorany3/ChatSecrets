import streamlit as st
import uuid
from collections import defaultdict
from datetime import datetime
import json
import os
import time

# Force Streamlit to use dark theme if user's OS is in dark mode
st.markdown("""
<style>
body, .stApp { color-scheme: dark; }
</style>
""", unsafe_allow_html=True)

# Fernet encryption
from cryptography.fernet import Fernet

# Path for encryption key
FERNET_KEY_FILE = "fernet.key"
def get_fernet():
    if not os.path.exists(FERNET_KEY_FILE):
        key = Fernet.generate_key()
        with open(FERNET_KEY_FILE, "wb") as f:
            f.write(key)
    else:
        with open(FERNET_KEY_FILE, "rb") as f:
            key = f.read()
    return Fernet(key)

st.set_page_config(
    page_title="Secret Multi-Room Chat",
    page_icon="static/favicon.ico",  # use relative path for Streamlit local static asset
    layout="centered"
)

# Path file untuk penyimpanan pesan bersama
CHAT_FILE = "chat_rooms.json"

# Fungsi untuk load dan save pesan ke file
def load_rooms():
    if os.path.exists(CHAT_FILE):
        with open(CHAT_FILE, "r") as f:
            return json.load(f)
    return {}

def save_rooms(rooms):
    with open(CHAT_FILE, "w") as f:
        json.dump(rooms, f)

# Path file untuk status online user
ONLINE_FILE = "online_status.json"

def load_online():
    if os.path.exists(ONLINE_FILE):
        try:
            with open(ONLINE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_online(online):
    with open(ONLINE_FILE, "w") as f:
        json.dump(online, f)

# Simpan pesan di session_state (hanya bertahan selama server berjalan)
if 'rooms' not in st.session_state:
    st.session_state['rooms'] = load_rooms()


if 'usernames' not in st.session_state:
    st.session_state['usernames'] = {}

# Streamlit's st.title does not support HTML, so use st.markdown for styled title
st.markdown("<h1 style='color:#00ff00;text-shadow:0 0 10px #00ff00;'>🔒 Secret Multi-Room Chat 🔒</h1>", unsafe_allow_html=True)

# Pilih atau buat room
st.markdown("""
<div style='background:#111;padding:16px;border-radius:8px;border:1px solid #00ff00;box-shadow:0 0 10px #00ff00;'>
<b>Masukkan nama room dibawah ini (buatlah nama unik, dan share ke lawan bicara):</b>
</div>
""", unsafe_allow_html=True)
room = st.text_input("", key="room_input")
st.markdown("""
<div style='background:#111;padding:16px;border-radius:8px;border:1px solid #00ff00;box-shadow:0 0 10px #00ff00;margin-top:8px;'>
<b>Masukkan username Anda dibawah ini:</b>
</div>
""", unsafe_allow_html=True)
username = st.text_input("", key="username_input")

# Reset flag form_submitted di awal setiap render agar auto-refresh bisa aktif lagi setelah submit selesai
if st.session_state.get('form_submitted', False):
    st.session_state['form_submitted'] = False

if room and username:
    # Fitur set kode kunci destroy secret
    st.markdown("---")
    st.subheader("🔑 Set Kode Kunci Destroy Chat Room")
    st.caption("Masukkan kode kunci rahasia untuk room ini. Kode ini diperlukan untuk menghapus seluruh chat di room ini.")
    if f"destroy_secret_{room}" not in st.session_state:
        st.session_state[f"destroy_secret_{room}"] = ""
    new_secret = st.text_input("Set kode kunci (minimal 6 karakter):", type="password", key="set_destroy_secret")
    if st.button("Set Kode Kunci"):
        if len(new_secret) >= 6:
            st.session_state[f"destroy_secret_{room}"] = new_secret
            st.success("✅ Kode kunci berhasil disimpan untuk room ini.")
        else:
            st.error("Kode kunci minimal 6 karakter.")

    # Fitur Destroy Chat (hapus session dan pesan di room)
    st.markdown("---")
    st.subheader("🛑 Destroy Chat Room")
    destroy_key = st.text_input("Masukkan kode kunci untuk hapus chat room:", type="password", key="destroy_key")
    DESTROY_SECRET = st.session_state.get(f"destroy_secret_{room}", "")
    if st.button("Destroy Chat Room"):
        if destroy_key == DESTROY_SECRET and DESTROY_SECRET:
            # Hapus pesan di room
            rooms = load_rooms()
            if room in rooms:
                del rooms[room]
                save_rooms(rooms)
            # Hapus status online di room
            online = load_online()
            if room in online:
                del online[room]
                save_online(online)
            # Hapus session user
            for k in [
                'rooms', 'usernames', 'user_id', 'input_counter', 'last_message_count', 'form_submitted', 'refresh_countdown', 'room_input', 'username_input', 'message_input_box_' + room + '_' + username + '_' + str(st.session_state.get('input_counter',0)), 'destroy_key'
            ]:
                if k in st.session_state:
                    del st.session_state[k]
            st.success("🗑️ Chat room dan session berhasil dihapus. Silakan refresh halaman.")
            st.stop()
        else:
            st.error("❌ Kode kunci salah! Tidak dapat menghapus chat room.")
    # Update status online user di room
    online = load_online()
    now_epoch = int(time.time())
    if room not in online:
        online[room] = {}
    online[room][username] = now_epoch
    save_online(online)

    # Ambil pesan hanya sekali per render
    messages = load_rooms().get(room, [])
    # Notifikasi jika ada pesan baru dari user lain
    if 'last_message_count' not in st.session_state:
        st.session_state['last_message_count'] = 0
    if len(messages) > st.session_state['last_message_count']:
        last_msg = messages[-1]
        if last_msg['username'] != username:
            st.toast(f"Pesan baru dari {last_msg['username']}: {last_msg['text']}")
            # Play sound notification using HTML5 Audio
            st.markdown('''
                <audio id="notif-audio" src="https://cdn.pixabay.com/download/audio/2026/01/24/audio_f7ed9fb119.mp3" autoplay></audio>
                <script>
                var audio = document.getElementById('notif-audio');
                if(audio){ audio.play(); }
                </script>
            ''', unsafe_allow_html=True)
    st.session_state['last_message_count'] = len(messages)
    # Counter untuk reset input box
    if 'input_counter' not in st.session_state:
        st.session_state['input_counter'] = 0
    # Buat ID user unik per session
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = str(uuid.uuid4())
    st.session_state['usernames'][st.session_state['user_id']] = username
    st.subheader(f"Room: {room}")
    st.write(f"Anda masuk sebagai: {username}")
    st.info("Waktu Anda adalah 30 menit sejak masuk, klik Refresh Chat di bawah, jika membutuhkan tambahan waktu")

    # Tampilkan status online lawan bicara di room
    online = load_online()
    online_users = []
    if room in online:
        for user, last_seen in online[room].items():
            if user != username and now_epoch - last_seen <= 10:
                online_users.append(user)
    if online_users:
        st.success(f"🟢 Online: {', '.join(online_users)}")
    else:
        st.info("🔴 Tidak ada lawan bicara online di room ini.")

    # Tampilkan pesan di room dalam box scrollable, bubble chat, auto-scroll, dan waktu
    # Selalu reload pesan terbaru dari file
    st.session_state['rooms'] = load_rooms()
    messages = st.session_state['rooms'].get(room, [])
    chat_box_style = """
        <style>
        .chat-box {
            height: 350px;
            overflow-y: auto;
            background: #f7f7fa;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 12px 8px 12px 8px;
            margin-bottom: 10px;
            display: flex;
            flex-direction: column;
        }
        .chat-message {
            margin-bottom: 8px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
        }
        .chat-bubble {
            display: inline-block;
            padding: 8px 14px;
            border-radius: 18px;
            background: #e0e7ff;
            color: #222;
            max-width: 80%;
            word-break: break-word;
            font-size: 15px;
        }
        .chat-bubble.me {
            background: #6366f1;
            color: #fff;
            align-self: flex-end;
        }
        .chat-meta {
            font-size: 11px;
            color: #888;
            margin-top: 2px;
            margin-left: 4px;
        }
        </style>
        <script>
        // Auto-scroll chat box ke bawah jika ada pesan baru atau refresh
        setTimeout(function() {
            var chatBox = window.parent.document.getElementById('chat-box');
            if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
        }, 100);
        </script>
    """
    st.markdown(chat_box_style, unsafe_allow_html=True)
    chat_html = '<div class="chat-box" id="chat-box">'
    for msg in messages:
        is_me = (msg["username"] == username)
        bubble_class = "chat-bubble me" if is_me else "chat-bubble"
        time_str = msg.get("time", "")
        user_icon = "🧑‍💻" if is_me else "👤"
        # Dekripsi pesan
        try:
            fernet = get_fernet()
            decrypted_text = fernet.decrypt(msg["text"].encode()).decode()
        except Exception:
            decrypted_text = "[Pesan tidak dapat didekripsi]"
        chat_html += f'<div class="chat-message" style="align-items: {"flex-end" if is_me else "flex-start"};">'
        chat_html += f'<div class="{bubble_class}">{user_icon} {decrypted_text}</div>'
        chat_html += f'<div class="chat-meta">{msg["username"]} {"(Anda)" if is_me else ""} {time_str}</div>'
        chat_html += '</div>'
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)

    # Form kirim pesan
    with st.form(key="send_message_form"):
        input_key = f"message_input_box_{room}_{username}_{st.session_state['input_counter']}"
        message = st.text_input("Ketik pesan...", key=input_key)
        col1, col2 = st.columns([3,1])
        with col1:
            send = st.form_submit_button("Kirim")
        with col2:
            ping = st.form_submit_button("Ping 🏓")
        if send and message:
            # Set flag agar auto-refresh tidak aktif saat submit
            st.session_state['form_submitted'] = True
            # Set waktu ke UTC+7 (WIB)
            from datetime import timezone, timedelta
            wib = timezone(timedelta(hours=7))
            now = datetime.now(wib).strftime('%H:%M')
            # Tambahkan pesan baru dan simpan (dengan enkripsi)
            rooms = load_rooms()
            if room not in rooms:
                rooms[room] = []
            fernet = get_fernet()
            encrypted_text = fernet.encrypt(message.encode()).decode()
            rooms[room].append({
                'username': username,
                'text': encrypted_text,
                'time': now
            })
            save_rooms(rooms)
            st.session_state['input_counter'] += 1  # Ganti key input agar box kosong
            # Setelah submit, rerun dan flag akan direset di awal render
            try:
                st.rerun()
            except AttributeError:
                st.experimental_rerun()
        # Tombol Ping
        if ping:
            st.session_state['form_submitted'] = True
            from datetime import timezone, timedelta
            wib = timezone(timedelta(hours=7))
            now = datetime.now(wib).strftime('%H:%M')
            rooms = load_rooms()
            if room not in rooms:
                rooms[room] = []
            fernet = get_fernet()
            ping_text = f"PING! 🏓"
            encrypted_text = fernet.encrypt(ping_text.encode()).decode()
            rooms[room].append({
                'username': username,
                'text': encrypted_text,
                'time': now
            })
            save_rooms(rooms)
            st.session_state['input_counter'] += 1
            try:
                st.rerun()
            except AttributeError:
                st.experimental_rerun()
    # Reset flag form_submitted di awal blok agar auto-refresh bisa aktif lagi setelah submit selesai
    if st.session_state.get('form_submitted', False):
        st.session_state['form_submitted'] = False
else:
    st.info("Masukkan nama room (unik) dan username untuk mulai chat.")


st.caption("Software ini dibuat dengan 100% python, dan memanfaatkan teknologi Streamlit. 🔒 Pesan dienkripsi dan bersifat temporary, dan akan hilang dengan cara destroy atau saat server reboot. Untuk keamanan ganda, jangan lupa hapus session dan chat room setelah selesai dengan fitur Destroy Chat Room.")

# Tombol manual refresh chat
if room and username:
    # Countdown refresh versi sebelumnya: refresh otomatis setiap 2 detik, reset ke 2 setelah refresh
    import time
    if 'refresh_countdown' not in st.session_state:
        st.session_state['refresh_countdown'] = 1800
    refresh_placeholder = st.empty()
    refresh_btn = refresh_placeholder.button(f"🔄 Refresh Chat ({st.session_state['refresh_countdown']})")
    # JavaScript untuk klik otomatis setiap 30 menit (1800 detik) agar chat tetap update walau user lupa klik refresh
    js = f"""
    <script>
    var btn = window.parent.document.querySelector('button[kind=\"secondary\"]');
    if (btn) {{
        setTimeout(function() {{ btn.click(); }}, 1800000);
    }}
    </script>
    """
    st.markdown(js, unsafe_allow_html=True)
    if refresh_btn:
        st.session_state['refresh_countdown'] = 1800
        try:
            st.rerun()
        except AttributeError:
            st.experimental_rerun()
    else:
        if st.session_state['refresh_countdown'] > 0:
            time.sleep(1)
            st.session_state['refresh_countdown'] -= 1
            try:
                st.rerun()
            except AttributeError:
                st.experimental_rerun()
