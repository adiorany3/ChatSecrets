# ChatSecrets

Streamlit chat with password-protected rooms and encrypted messages/attachments.

## Rooms and storage

- Creating a room sets its shared password (8–1024 characters); joining requires that password. Every authenticated member can destroy the room.
- Server-enforced sessions expire 30 minutes after joining; activity does not extend them. Join again after expiry.
- Destruction deletes active messages and all room sessions/presence. A server-enforced 30-second cooldown blocks name reuse; afterward, that name creates a fresh room with a new password and no old messages. Old session tokens remain invalid.
- Active data uses `chatsecrets.sqlite3`. SQLite `BEGIN IMMEDIATE` transactions commit or roll back room, message, and session changes.
- Encryption is server-side Fernet, **not end-to-end (E2E)**: the server holds the key and can decrypt content. Room names and session usernames remain plaintext in SQLite.
- Legacy `chat_rooms.json`, `online_status.json`, `destroyed_rooms.json`, and `private_links.json` remain untouched. Their original bytes are archived once in SQLite's `legacy_archive`, not automatically imported into active rooms or displayed. Rooms start fresh with passwords, even when reusing legacy names. Destruction does not erase legacy files, archives, backups, or other copies; it is not guaranteed secure erasure.

## Encryption key safety

Existing keys in `.streamlit/secrets.toml` are retained; the file is never rewritten. Configured keys and any sidecar must agree or startup fails.

New installations without existing data or keys create `.streamlit/fernet.key` atomically with owner-only permissions, using `.streamlit/fernet.lock` and Linux/macOS `fcntl` locking. Existing data without a key blocks startup instead of generating a replacement. Native Windows locking is unsupported.

**The encryption key was previously committed. This exposure remains unresolved until coordinated key rotation and re-encryption of retained data, plus repository history cleanup, are completed. Never delete the old key before data migration and verification. `.gitignore` does not remove committed files or Git history; history cleanup cannot revoke copies already obtained.**

## Install and run

Python 3.11+ on Linux/macOS. From the project directory:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Tests

Storage tests use temporary data, including the Streamlit UI check; attachment checks also use temporary storage.

```bash
python -m unittest test_storage
python test_attachments.py
```
