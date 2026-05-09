# ChatSecrets Terminal

Private multi-room chat dengan tampilan terminal hacker, enkripsi Fernet, auto-refresh, dan suara pesan masuk.

## Fitur

- Tema terminal hacker / CRT
- Multi-room chat
- Pesan terenkripsi dengan Fernet
- Auto-refresh Streamlit
- Suara notifikasi ketika pesan masuk dari user lain
- Destroy room dengan kode rahasia

## Cara Menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Catatan Suara

Browser biasanya memblokir suara otomatis sampai user melakukan interaksi. Setelah masuk room, klik tombol **Unlock Sound** di panel chat satu kali. Setelah itu, pesan masuk dari user lain akan berbunyi otomatis.
