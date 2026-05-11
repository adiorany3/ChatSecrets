# ChatSecrets Terminal

Aplikasi chat terminal-style berbasis Streamlit dengan enkripsi Fernet, auto-refresh, panic room, dan akses private link.

## Cara menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Admin private link

1. Buka sidebar, pilih halaman **Admin**.
2. Masukkan password admin.
   - Disarankan set environment variable:
     ```bash
     export CHATSECRETS_ADMIN_PASSWORD="password-kuat-anda"
     ```
   - Jika env belum diset, aplikasi akan membuat file `admin_password.txt` otomatis di folder project. Buka file tersebut untuk melihat password awal.
3. Isi nama room.
4. Klik **Create Private Link**.
5. Bagikan link yang muncul ke user yang diizinkan masuk.

## Aturan akses room

- Room tidak bisa lagi dimasuki manual hanya dengan mengetik nama room.
- User hanya bisa masuk jika URL membawa token private link valid dalam format:
  ```text
  ?room=nama-room&access=token-rahasia
  ```
- Private link bisa di-revoke, diaktifkan kembali, atau dihapus dari halaman Admin.

## Panic Room

Saat tombol **PANIC ROOM // DESTROY NOW** ditekan:

- Semua pesan/data room dihapus dari `chat_rooms.json`.
- Status online room dihapus dari `online_status.json`.
- Room ditandai hancur di `destroyed_rooms.json` supaya tidak bisa dibuat ulang otomatis.
- Semua private link untuk room tersebut otomatis di-revoke di `private_links.json`.
- Browser user yang menekan panic langsung refresh dan query private link dibersihkan dari URL.
- User lain akan otomatis keluar dari room pada refresh berikutnya.

## File storage lokal

Aplikasi menyimpan data lokal pada file JSON:

- `chat_rooms.json`
- `online_status.json`
- `destroyed_rooms.json`
- `private_links.json`

Untuk produksi, gunakan storage yang lebih aman dan batasi akses file server.
