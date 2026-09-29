"""Run: python -m unittest test_storage. Production files never opened."""
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet
from storage import AuthError, Store, provision_key


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.key = Fernet.generate_key()
        self.now = 1000.0
        self.store = Store(self.root / "test.sqlite3", self.key, clock=lambda: self.now)
        self.token = self.store.join("room", "alice", "password123")

    def test_wrong_key_preserves_history(self):
        self.store.send(self.token, "original")
        history = self.store.read(self.token)
        source = self.root / "chat_rooms.json"
        source.write_bytes(b'{"legacy": []}')
        for sentinel in (True, False):
            with self.subTest(sentinel=sentinel):
                if not sentinel:
                    with self.store.transaction() as db:
                        db.execute("DROP TABLE IF EXISTS key_verification")
                before = self.store.path.read_bytes()
                with self.assertRaisesRegex(ValueError, "key verification failed"):
                    wrong = Store(self.store.path, Fernet.generate_key(), legacy_dir=self.root,
                                  clock=lambda: self.now)
                    wrong.send(self.token, "must not be written")
                self.assertEqual(self.store.path.read_bytes(), before)
                self.assertEqual(source.read_bytes(), b'{"legacy": []}')
                restored = Store(self.store.path, self.key, clock=lambda: self.now)
                self.assertEqual(restored.read(self.token), history)
                self.assertEqual(restored.fernet.decrypt(history[0]["text"].encode()), b"original")
                with restored.transaction() as db:
                    self.assertEqual(db.execute("SELECT count(*) FROM messages").fetchone()[0], 1)
                    self.assertEqual(db.execute("SELECT count(*) FROM legacy_archive").fetchone()[0], 0)

    def test_migration_checks_all_payloads(self):
        self.store.send(self.token, "first")
        other = self.store.join("other-room", "bob", "password123")
        self.store.send(other, "last")
        with self.store.transaction() as db:
            db.execute("DROP TABLE IF EXISTS key_verification")
            db.execute("UPDATE messages SET payload=? WHERE room='other-room'",
                       (Fernet(Fernet.generate_key()).encrypt(b"unreadable"),))
        before = self.store.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "key verification failed"):
            Store(self.store.path, self.key)
        self.assertEqual(self.store.path.read_bytes(), before)

    def test_empty_database_key_verification(self):
        for sentinel in (True, False):
            with self.subTest(sentinel=sentinel):
                if not sentinel:
                    with self.store.transaction() as db:
                        db.execute("DROP TABLE IF EXISTS key_verification")
                Store(self.store.path, self.key)
                before = self.store.path.read_bytes()
                with self.assertRaisesRegex(ValueError, "key verification failed"):
                    Store(self.store.path, Fernet.generate_key())
                self.assertEqual(self.store.path.read_bytes(), before)

    def test_concurrent_messages(self):
        def send(number):
            other = Store(self.store.path, self.key, clock=lambda: self.now)
            other.send(self.token, str(number))
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(send, range(80)))
        messages = self.store.read(self.token)
        self.assertEqual(len(messages), 80)
        self.assertEqual({self.store.fernet.decrypt(m["text"].encode()).decode() for m in messages}, {str(i) for i in range(80)})

    def test_password_expiry_presence(self):
        with self.assertRaises(AuthError):
            self.store.join("room", "intruder", "wrongpass")
        for action in (self.store.read, self.store.presence, self.store.destroy):
            with self.assertRaises(AuthError):
                action("0" * 64)
        with self.assertRaises(AuthError):
            self.store.send("0" * 64, "unauthorized")
        bob = self.store.join("room", "bob", "password123")
        self.assertEqual(self.store.presence(self.token), ["bob"])
        self.now += 11
        self.assertEqual(self.store.presence(self.token), [])
        with self.store.transaction() as db:
            self.assertIsNone(db.execute("SELECT seen FROM sessions WHERE username='bob'").fetchone()[0])
        self.now = 2800
        for action in (self.store.read, self.store.presence, self.store.destroy):
            with self.assertRaises(AuthError):
                action(bob)
        with self.assertRaises(AuthError):
            self.store.send(self.token, "expired")
        fresh = self.store.join("room", "alice", "password123")
        self.assertEqual(self.store.read(fresh), [])

    def test_destroy_race_and_reuse(self):
        bob = self.store.join("room", "bob", "password123")
        barrier = threading.Barrier(2)
        def send():
            barrier.wait()
            try:
                self.store.send(self.token, "racing")
            except AuthError:
                pass
        def destroy():
            barrier.wait()
            self.store.destroy(bob)
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(send), pool.submit(destroy)]
            for job in jobs:
                job.result()
        with self.assertRaises(ValueError):
            self.store.join("room", "bob", "newpassword")
        with self.store.transaction() as db:
            old_generation = db.execute("SELECT generation FROM rooms").fetchone()[0]
            self.assertEqual(db.execute("SELECT count(*) FROM messages").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM sessions").fetchone()[0], 0)
        self.now += 30
        restarted = Store(self.store.path, self.key, clock=lambda: self.now)
        fresh = restarted.join("room", "bob", "newpassword")
        with restarted.transaction() as db:
            self.assertNotEqual(old_generation, db.execute("SELECT generation FROM rooms").fetchone()[0])
        for action in (restarted.read, restarted.presence, restarted.destroy):
            with self.assertRaises(AuthError):
                action(self.token)
        with self.assertRaises(AuthError):
            restarted.send(self.token, "stale")
        self.assertEqual(restarted.read(fresh), [])

    def test_clear_messages_keeps_room_and_session(self):
        self.store.send(self.token, "to clear")
        self.assertEqual(len(self.store.read(self.token)), 1)

        self.store.clear_messages(self.token)

        self.assertEqual(self.store.read(self.token), [])
        self.store.send(self.token, "room still works")
        self.assertEqual(len(self.store.read(self.token)), 1)

    def test_attachments_and_quarantine(self):
        attachment = {"name": "note.txt", "mime": "application/octet-stream", "data": self.store.fernet.encrypt(b"private attachment").decode()}
        self.store.send(self.token, "caption", attachment)
        message = self.store.read(self.token)[0]
        self.assertEqual(message["attachment"], attachment)
        legacy = json.dumps({"legacy": [message]}).encode()
        source = self.root / "chat_rooms.json"
        source.write_bytes(legacy)
        migrated = Store(self.store.path, self.key, legacy_dir=self.root, clock=lambda: self.now)
        claimant = migrated.join("legacy", "intruder", "password123")
        self.assertEqual(migrated.read(claimant), [])
        self.assertEqual(source.read_bytes(), legacy)
        with migrated.transaction() as db:
            self.assertEqual(db.execute("SELECT content FROM legacy_archive").fetchone()[0], legacy)
        migrated.destroy(claimant)
        Store(self.store.path, self.key, legacy_dir=self.root)
        self.assertEqual(source.read_bytes(), legacy)
        self.assertEqual(migrated.read(self.token)[0]["attachment"], attachment)

    def test_ui_explicit_join(self):
        import shutil
        from streamlit.testing.v1 import AppTest
        source = Path(__file__).parent
        shutil.copy(source / "app.py", self.root / "app.py")
        shutil.copytree(source / "static", self.root / "static")
        with patch("streamlit.secrets", {}):
            app = AppTest.from_file(str(self.root / "app.py"), default_timeout=15).run()
            self.assertFalse(app.exception)
            self.assertNotIn("room_token", app.session_state)
            app.text_input[0].input("ui-room")
            app.text_input[1].input("alice")
            app.text_input[2].input("password123")
            app.button(key="FormSubmitter:join_room-Create / join room").click().run()
            self.assertFalse(app.exception)
            self.assertIn("room_token", app.session_state)
            app.text_input(key="message_0").input("UI message")
            app.button(key="FormSubmitter:send_message_form_0-Kirim").click().run()
            self.assertFalse(app.exception)
            key = (self.root / ".streamlit" / "fernet.key").read_bytes()
            store = Store(self.root / "chatsecrets.sqlite3", key)
            self.assertEqual(len(store.read(app.session_state["room_token"])), 1)
            app.button(key="panic_room_ui-room").click().run()
            self.assertFalse(app.exception)
            self.assertNotIn("room_token", app.session_state)

    def test_key_provision(self):
        path = self.root / ".streamlit" / "secrets.toml"
        path.parent.mkdir()
        original = f'# keep comments\n[secrets]\nfernet_key = "{self.key.decode()}"\nother = "unchanged"\n'
        path.write_text(original)
        self.assertEqual(provision_key(path), self.key)
        self.assertEqual(path.read_text(), original)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / ".streamlit" / "secrets.toml"
            target.parent.mkdir()
            target.write_text('[other]\nvalue = "preserved"\n')
            with ProcessPoolExecutor(max_workers=4) as pool:
                keys = list(pool.map(provision_key, [target] * 8))
            self.assertEqual(len(set(keys)), 1)
            self.assertEqual(target.read_text(), '[other]\nvalue = "preserved"\n')
            self.assertEqual((target.parent / "fernet.key").stat().st_mode & 0o777, 0o600)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / ".streamlit" / "secrets.toml"
            (Path(directory) / "chat_rooms.json").write_text('{"old": ["encrypted"]}')
            with self.assertRaises(ValueError):
                provision_key(target)
            self.assertFalse((target.parent / "fernet.key").exists())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / ".streamlit" / "secrets.toml"
            with patch("storage.os.link", side_effect=OSError("disk failure")):
                with self.assertRaises(OSError):
                    provision_key(target)
            self.assertFalse((target.parent / "fernet.key").exists())


if __name__ == "__main__":
    unittest.main()
