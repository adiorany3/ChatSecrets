"""Run: python3 /Users/macbookpro/Documents/GitHub/ChatSecrets/test_attachments.py"""
import io
from pathlib import Path
import zipfile

from attachments import MAX_FILE_BYTES, validate_attachment

assert validate_attachment("../../note.txt", b"hello")["name"] == "note.txt"
assert validate_attachment("C:\\fakepath\\photo.PNG", b"\x89PNG\r\n\x1a\n")["mime"] == "image/png"
assert validate_attachment("report.pdf", b"%PDF-1.7")["mime"] == "application/octet-stream"
assert validate_attachment("table.csv", b"name,value\na,1")
for name, data in [("x.svg", b"<svg/>"), ("x.png", b"<script>"), ("x.txt", b""),
                   ("x.txt", b"\xff"), ("x.txt", b"\x00"), ("x.docx", b"invalid"),
                   ("x.txt", b"a" * (MAX_FILE_BYTES + 1)), ("x\n.txt", b"a")]:
    try:
        validate_attachment(name, data)
    except ValueError:
        pass
    else:
        raise AssertionError(name)
for extension, entry in [("docx", "word/document.xml"), ("xlsx", "xl/workbook.xml"), ("pptx", "ppt/presentation.xml")]:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "")
        archive.writestr(entry, "")
    assert validate_attachment("test." + extension, buffer.getvalue())

# Test authenticated SQLite attachment persistence without touching production data.
import tempfile
from cryptography.fernet import Fernet
from storage import Store
temporary = tempfile.TemporaryDirectory()
store = Store(Path(temporary.name) / "rooms.sqlite3", Fernet.generate_key())
token = store.join("room", "user", "password123")
attachment = {"name": "test.txt", "mime": "application/octet-stream", "data": store.fernet.encrypt(b"attachment bytes").decode()}
store.send(token, "caption", attachment)
store.send(token, "text only")
messages = store.read(token)
assert messages[0]["attachment"] == attachment
assert store.fernet.decrypt(messages[0]["text"].encode()) == b"caption"
assert "attachment" not in messages[1]
temporary.cleanup()
print("Attachment checks passed")
