# 💬🔒 Secret Multi-Room Chat

Aplikasi chat multi-room rahasia berbasis Streamlit. Setiap user dapat membuat room, bercakap secara privat, dan menghapus seluruh chat dengan kode kunci.

## Fitur
- Multi-room chat, setiap room terpisah
- Username bebas, status online lawan bicara
- Pesan hanya bisa dilihat user di room yang sama
- Auto-scroll ke pesan terbaru
- Destroy chat room dengan kode kunci rahasia
- UI dengan emoji/icon modern

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
   - Buka http://localhost:8501

## Penggunaan
- Masukkan nama room dan username untuk masuk.
- Chat dengan user lain di room yang sama.
- Set kode kunci untuk room, gunakan untuk menghapus seluruh chat room.
- Klik 🔄 Refresh Chat untuk update pesan.

## Catatan
- Pesan dan status online hanya tersimpan selama server berjalan.
- Untuk privasi lebih, jalankan di server sendiri.

---

Made with ❤️ using Streamlit.
