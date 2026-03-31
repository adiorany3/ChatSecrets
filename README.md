# 💬🔒 Secret Multi-Room Chat

Aplikasi chat multi-room rahasia berbasis Streamlit. Setiap user dapat membuat room, bercakap secara privat, ter-enkripsi, dan menghapus seluruh chat dengan kode kunci dengan mudah.

## Fitur
- Multi-room chat, setiap room terpisah
- Username bebas, status online lawan bicara
- Pesan hanya bisa dilihat user di room yang sama, dengan enkripsi di setiap pesannya.
- Auto-scroll ke pesan terbaru
- Destroy chat room dengan kode kunci rahasia yang dapat dibuat user dan diterapkan untuk menghapus semua chat tanpa sisa.
- UI dengan emoji/icon modern

## Keamanan & Fitur Tambahan
- **Enkripsi Pesan:** Semua pesan dienkripsi otomatis menggunakan Fernet (cryptography) sebelum disimpan ke file. Hanya aplikasi ini yang dapat membaca pesan.
- **Zona Waktu:** Waktu pengiriman pesan otomatis disesuaikan ke UTC+7 (WIB).
- **Favicon:** Favicon custom dapat diubah di folder `static/`.
- **Tampilan Hacker Style:** UI gelap, aksen hijau neon, dan font monospace ala terminal hacker. Dapat diubah menjadi mode terang juga.

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
   - Akses web online : [https://ngobrol.streamlit.app](https://ngobrol.streamlit.app/)

## Penggunaan
- Masukkan nama room dan username untuk masuk.
- Chat dengan user lain di room yang sama. Diberikan waktu selama 30 menit, dan untuk memperpanjang percakapan bisa klik 🔄 Refresh Chat
- Set kode kunci untuk room, gunakan untuk menghapus seluruh chat room jika sudah selesai chat, untuk menghapus semua percakapan yang ada.

## Catatan
- Pesan dan status online hanya tersimpan selama server berjalan, dan akan terhapus secara automatis jika server restart.
- Untuk privasi lebih, hapus chat dengan cara Destroy Chat, setelah selesai dipergunakan.
- Pesan yang ada dilakukan proses enkripsi, sehingga dalam perjalanan pesan, dipastikan akan dalam mode enkripsi.

## Troubleshooting
- Jika terjadi error JSONDecodeError, pastikan file `chat_rooms.json` dan `online_status.json` berisi `{}` (objek kosong).
- Jika pesan tidak dapat didekripsi, pastikan file `fernet.key` tidak hilang/berubah setelah pesan dibuat.

---

Made with ❤️ by adioranye using Streamlit, 100% python, and encrypted.
