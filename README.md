# ChatSecrets Hacker Terminal

Versi ini sudah diperbarui:
- Room yang dihancurkan langsung menghapus data chat dan status online.
- Nama room terkunci sementara 30 detik.
- Setelah 30 detik, nama room otomatis bisa digunakan kembali.
- Catatan kedaluwarsa pada destroyed_rooms.json dibersihkan saat aplikasi mengaksesnya; backup dan salinan lain tidak ikut terhapus.
- Pesan dienkripsi di server, bukan end-to-end. Nama room dan username tidak dienkripsi.
- Penyimpanan JSON belum mendukung transaksi pembaruan bersamaan; gunakan SQLite sebelum penggunaan multi-user yang membutuhkan jaminan tidak kehilangan pembaruan.

Jalankan aplikasi:
```bash
pip install -r requirements.txt
streamlit run app.py
```
