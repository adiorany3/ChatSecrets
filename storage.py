"""Transactional active rooms. Legacy files are archived, never joined or decrypted."""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import tempfile
import time
import tomllib
import uuid
from contextlib import contextmanager
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from attachments import MAX_FILE_BYTES, validate_attachment

SESSION_SECONDS = 1800
COOLDOWN_SECONDS = 30
ONLINE_SECONDS = 10
LEGACY_FILES = ("chat_rooms.json", "online_status.json", "destroyed_rooms.json", "private_links.json")


class AuthError(ValueError):
    pass


def provision_key(secrets_file: Path, configured: str | None = None) -> bytes:
    """Never rewrite TOML. Publish a complete sidecar key atomically under a process lock."""
    try:
        import fcntl  # macOS/Linux deployment; fail closed on unsupported platforms.
    except ImportError:
        fcntl = None  # type: ignore[assignment]
    secrets_file.parent.mkdir(parents=True, exist_ok=True)
    lock_path = secrets_file.parent / "fernet.lock"
    with open(lock_path, "a+b") as lock:
        os.chmod(lock.name, 0o600)
        if fcntl is not None:
            fcntl.flock(lock, fcntl.LOCK_EX)
        config = tomllib.loads(secrets_file.read_text()) if secrets_file.exists() else {}
        local = config.get("secrets", {}).get("fernet_key") or config.get("fernet_key")
        key_file = secrets_file.parent / "fernet.key"
        stored = key_file.read_bytes().strip() if key_file.exists() else None
        candidates = [value.encode() if isinstance(value, str) else value
                      for value in (configured, local, stored) if value is not None]
        for key in candidates:
            Fernet(key)
        if candidates:
            if any(key != candidates[0] for key in candidates):
                raise ValueError("Conflicting Fernet keys; restore matching configuration. No keys changed.")
            return candidates[0]
        root = secrets_file.parent.parent
        if (root / "chatsecrets.sqlite3").exists() or any(
            (root / name).exists() and (root / name).read_text().strip() not in ("", "{}")
            for name in LEGACY_FILES
        ):
            raise ValueError("Existing storage has no Fernet key. Restore original key; no key generated.")
        key = Fernet.generate_key()
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=secrets_file.parent, delete=False) as output:
                temporary = Path(output.name)
                os.chmod(temporary, 0o600)
                output.write(key)
                output.flush()
                os.fsync(output.fileno())
            try:
                os.link(temporary, key_file)  # Exclusive publication; never overwrite a key.
            except FileExistsError:
                return key_file.read_bytes().strip()
            directory = os.open(secrets_file.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if fcntl is not None:
                try:
                    fcntl.flock(lock, fcntl.LOCK_UN)
                except OSError:
                    pass
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
        return key


class Store:
    def __init__(self, path: Path, key: bytes, legacy_dir: Path | None = None, clock=time.time):
        self.path, self.fernet, self.clock = Path(path), Fernet(key), clock
        descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
        finally:
            os.close(descriptor)
        with self.transaction() as db:
            for statement in (
                "CREATE TABLE IF NOT EXISTS rooms (name TEXT PRIMARY KEY, generation TEXT NOT NULL, salt BLOB, password BLOB, destroyed_at REAL)",
                "CREATE TABLE IF NOT EXISTS sessions (token BLOB PRIMARY KEY, room TEXT NOT NULL, generation TEXT NOT NULL, username TEXT NOT NULL, expires REAL NOT NULL, seen REAL)",
                "CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, room TEXT NOT NULL, generation TEXT NOT NULL, payload BLOB NOT NULL)",
                "CREATE INDEX IF NOT EXISTS message_room ON messages(room, generation, id)",
                "CREATE TABLE IF NOT EXISTS legacy_archive (name TEXT PRIMARY KEY, content BLOB NOT NULL)",
            ):
                db.execute(statement)
            sentinel = b"chatsecrets storage key verification v1"
            has_sentinel = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='key_verification'"
            ).fetchone()
            try:
                if has_sentinel:
                    rows = db.execute("SELECT payload FROM key_verification").fetchall()
                    if len(rows) != 1 or self.fernet.decrypt(rows[0][0]) != sentinel:
                        raise InvalidToken
                else:
                    for row in db.execute("SELECT payload FROM messages"):
                        self.fernet.decrypt(row[0])
                    db.execute("CREATE TABLE key_verification (payload BLOB NOT NULL)")
                    db.execute("INSERT INTO key_verification VALUES (?)", (self.fernet.encrypt(sentinel),))
            except (InvalidToken, TypeError) as exc:
                raise ValueError("Storage key verification failed; restore the matching Fernet key. No data changed.") from exc
            if legacy_dir is not None:
                for name in LEGACY_FILES:
                    source = Path(legacy_dir) / name
                    if source.exists() and not db.execute("SELECT 1 FROM legacy_archive WHERE name=?", (name,)).fetchone():
                        db.execute("INSERT INTO legacy_archive VALUES (?,?)", (name, source.read_bytes()))
        os.chmod(self.path, 0o600)

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.execute("PRAGMA journal_mode=WAL")
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _text(value, label, maximum):
        if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value):
            raise ValueError(f"Invalid {label}.")
        return value.strip()

    @staticmethod
    def _password(password, salt):
        if not isinstance(password, str) or not 8 <= len(password) <= 1024:
            raise ValueError("Password must contain 8–1024 characters.")
        return hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)

    @staticmethod
    def _token(token):
        if not isinstance(token, str) or len(token) != 64:
            raise AuthError("Authentication required. Join again.")
        return hashlib.sha256(token.encode()).digest()

    def _auth(self, db, token):
        now = self.clock()
        db.execute("DELETE FROM sessions WHERE expires<=?", (now,))
        db.execute("UPDATE sessions SET seen=NULL WHERE seen<=?", (now - ONLINE_SECONDS,))
        session = db.execute(
            "SELECT s.* FROM sessions s JOIN rooms r ON r.name=s.room AND r.generation=s.generation "
            "WHERE s.token=? AND s.expires>? AND r.destroyed_at IS NULL",
            (self._token(token), now),
        ).fetchone()
        if session is None:
            raise AuthError("Session expired or room destroyed. Join again.")
        return session

    def join(self, room, username, password):
        room = self._text(room, "room name", 128)
        username = self._text(username, "username", 80)
        with self.transaction() as db:
            now = self.clock()
            db.execute("DELETE FROM sessions WHERE expires<=?", (now,))
            record = db.execute("SELECT * FROM rooms WHERE name=?", (room,)).fetchone()
            if record is not None and record["destroyed_at"] is not None and now < record["destroyed_at"] + COOLDOWN_SECONDS:
                raise ValueError("Room destroyed. Wait 30 seconds before creating it again.")
            if record is None or record["destroyed_at"] is not None:
                salt, generation = secrets.token_bytes(16), uuid.uuid4().hex
                digest = self._password(password, salt)
                db.execute("INSERT OR REPLACE INTO rooms VALUES (?,?,?,?,NULL)", (room, generation, salt, digest))
            else:
                generation = record["generation"]
                if not hmac.compare_digest(self._password(password, record["salt"]), record["password"]):
                    raise AuthError("Wrong room password.")
            token = secrets.token_hex(32)
            db.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?)", (self._token(token), room, generation, username, now + SESSION_SECONDS, now))
            return token

    def read(self, token):
        with self.transaction() as db:
            session = self._auth(db, token)
            return [json.loads(self.fernet.decrypt(row[0])) for row in db.execute(
                "SELECT payload FROM messages WHERE room=? AND generation=? ORDER BY id",
                (session["room"], session["generation"]),
            )]

    def send(self, token, text, attachment=None):
        if not isinstance(text, str) or len(text) > 20000 or (not text.strip() and attachment is None):
            raise ValueError("Message must contain text or attachment; maximum 20000 characters.")
        with self.transaction() as db:
            session = self._auth(db, token)
            message = {"id": uuid.uuid4().hex, "username": session["username"], "time": time.strftime("%H:%M", time.gmtime(self.clock() + 7 * 3600)), "text": self.fernet.encrypt(text.encode()).decode()}
            if attachment is not None:
                if not isinstance(attachment, dict) or not isinstance(attachment.get("data"), str) or len(attachment["data"]) > (MAX_FILE_BYTES + 1024) * 4 // 3:
                    raise ValueError("Invalid attachment.")
                data = self.fernet.decrypt(attachment["data"].encode())
                if not isinstance(attachment.get("name"), str):
                    raise ValueError("Invalid attachment name.")
                info = validate_attachment(attachment["name"], data)
                message["attachment"] = {**info, "data": attachment["data"]}
            payload = self.fernet.encrypt(json.dumps(message, ensure_ascii=False).encode())
            db.execute("INSERT INTO messages(room,generation,payload) VALUES (?,?,?)", (session["room"], session["generation"], payload))

    def presence(self, token):
        with self.transaction() as db:
            session = self._auth(db, token)
            db.execute("UPDATE sessions SET seen=? WHERE token=?", (self.clock(), self._token(token)))
            return [row[0] for row in db.execute(
                "SELECT DISTINCT username FROM sessions WHERE room=? AND generation=? AND seen>? AND token<>? ORDER BY username",
                (session["room"], session["generation"], self.clock() - ONLINE_SECONDS, self._token(token)),
            )]

    def destroy(self, token):
        with self.transaction() as db:
            session = self._auth(db, token)
            db.execute("DELETE FROM messages WHERE room=?", (session["room"],))
            db.execute("DELETE FROM sessions WHERE room=?", (session["room"],))
            db.execute("UPDATE rooms SET destroyed_at=? WHERE name=?", (self.clock(), session["room"]))
