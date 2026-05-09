# ChatSecrets - Hacker Terminal Edition

Aplikasi chat multi-room rahasia berbasis Streamlit dengan tampilan terminal ala film hacker.

## Fitur

- Multi-room chat
- Username bebas
- Status online lawan bicara
- Pesan terenkripsi menggunakan Fernet
- Destroy chat room menggunakan kode rahasia
- UI terminal gelap dengan neon green, scanline CRT, dan font monospace

## Cara Menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Catatan Keamanan

Pesan disimpan di file lokal `chat_rooms.json` dalam bentuk terenkripsi. Gunakan fitur Destroy Chat Room setelah selesai memakai room.
