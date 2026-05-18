# ChatSecrets Hacker Terminal

Aplikasi chat multi-room berbasis Streamlit dengan tampilan terminal hacker, auto-refresh, enkripsi Fernet, dan suara pesan masuk.

## Perubahan Fernet Key TOML

Versi ini sudah dimodifikasi agar Fernet key tidak lagi dibaca dari file `fernet.key`. Key sekarang disimpan di file TOML tersembunyi:

```text
.streamlit/secrets.toml
```

Format isi file:

```toml
[secrets]
fernet_key = "ISI_DENGAN_FERNET_KEY"
```

Aplikasi akan membaca key dari `st.secrets` / `.streamlit/secrets.toml`. Jika file belum ada, aplikasi akan membuat Fernet key baru otomatis dan menyimpannya ke `.streamlit/secrets.toml`.

## Cara Membuat Fernet Key Baru

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Masukkan hasilnya ke `.streamlit/secrets.toml`.

## Cara Menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Perubahan Panic Room

Ketika tombol **PANIC ROOM // DESTROY NOW** ditekan:

1. Data pesan room dihapus dari `chat_rooms.json`.
2. Status online room dihapus dari `online_status.json`.
3. Nama room dimasukkan ke `destroyed_rooms.json`, sehingga room tidak otomatis dibuat ulang oleh user yang masih membuka halaman lama.
4. Input `room_name` pada sesi user yang menekan panic dikosongkan, sehingga user langsung keluar dari room.
5. User lain yang masih berada di room akan otomatis dikeluarkan pada auto-refresh berikutnya.

## Catatan Keamanan

- File `fernet.key` sudah tidak digunakan.
- `.streamlit/secrets.toml` sudah dimasukkan ke `.gitignore` agar key asli tidak ikut ter-commit ke GitHub.
- Jika ingin upload project ke publik, hapus `.streamlit/secrets.toml` dan gunakan `.streamlit/secrets.example.toml` sebagai contoh format.
