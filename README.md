# ChatSecrets Hacker Terminal

Aplikasi chat multi-room berbasis Streamlit dengan tampilan terminal hacker, auto-refresh, enkripsi Fernet, dan suara pesan masuk.

## Fitur

- Tampilan terminal hacker / CRT
- Multi-room chat
- Pesan terenkripsi dengan Fernet
- Auto-refresh via `streamlit-autorefresh`
- Suara pesan masuk ala hacker
- Tombol `Test Hacker Sound` di sidebar
- Render chat via `components.html()` agar HTML tidak bocor sebagai teks

## Cara Menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Catatan Suara

Browser modern sering memblokir audio otomatis. Klik tombol **Test Hacker Sound** di sidebar sekali setelah aplikasi terbuka. Setelah itu, pesan masuk dari user lain akan mencoba memutar suara otomatis.

Jika masih belum terdengar:

1. Pastikan volume laptop/browser tidak mute.
2. Klik ikon izin audio/site settings di browser dan izinkan sound.
3. Jalankan dari browser desktop, bukan preview terbatas.
4. Pastikan pesan yang masuk berasal dari username lain, karena pesan sendiri tidak memicu suara.
