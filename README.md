# 💬🔒 Secret Multi-Room Chat

Aplikasi chat multi-room rahasia berbasis Streamlit. Setiap user dapat membuat room, bercakap secara privat, dan menghapus seluruh chat dengan kode kunci.

## Fitur
- Multi-room chat, setiap room terpisah
- Username bebas, status online lawan bicara
- Pesan hanya bisa dilihat user di room yang sama
- Auto-scroll ke pesan terbaru
- Destroy chat room dengan kode kunci rahasia
- UI dengan emoji/icon modern

## Keamanan & Fitur Tambahan
- **Enkripsi Pesan:** Semua pesan dienkripsi otomatis menggunakan Fernet (cryptography) sebelum disimpan ke file. Hanya aplikasi ini yang dapat membaca pesan.
- **Zona Waktu:** Waktu pengiriman pesan otomatis disesuaikan ke UTC+7 (WIB).
- **Favicon:** Favicon custom dapat diubah di folder `static/`.
- **Tampilan Hacker Style:** UI gelap, aksen hijau neon, dan font monospace ala terminal hacker.

## Cara Menjalankan
1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Jalankan aplikasi**
   ```bash
   streamlit run app.py
   ```
3. **Akses di browser**
   - Buka [https://ngobrol.streamlit.app](https://ngobrol.streamlit.app/)

## Penggunaan
- Masukkan nama room dan username untuk masuk.
- Chat dengan user lain di room yang sama.
- Set kode kunci untuk room, gunakan untuk menghapus seluruh chat room.
- Klik 🔄 Refresh Chat untuk update pesan.

## Catatan
- Pesan dan status online hanya tersimpan selama server berjalan.
- Untuk privasi lebih, jalankan di server sendiri.

## Troubleshooting
- Jika terjadi error JSONDecodeError, pastikan file `chat_rooms.json` dan `online_status.json` berisi `{}` (objek kosong).
- Jika pesan tidak dapat didekripsi, pastikan file `fernet.key` tidak hilang/berubah setelah pesan dibuat.

---

Made with ❤️ using Streamlit.
