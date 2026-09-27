"""Run: python3 /Users/macbookpro/Documents/GitHub/ChatSecrets/test_attachments.py"""
import ast
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

# Extract storage helpers without starting Streamlit or touching real room data.
tree = ast.parse(Path(__file__).with_name("app.py").read_text())
helpers = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef)
                         and node.name in ("make_message", "append_message")], type_ignores=[])
from typing import Any
import uuid
rooms = {}
saved = []
namespace = dict(Any=Any, uuid=uuid, encrypt_message=lambda text: "encrypted:" + text,
                 wib_now=lambda: "12:00", sanitize_room_name=str.strip,
                 is_room_destroyed=lambda room: False, load_json=lambda path: rooms,
                 save_json=lambda path, data: saved.append(data), CHAT_FILE="unused")
exec(compile(helpers, "app.py", "exec"), namespace)
attachment = {"name": "test.txt", "mime": "application/octet-stream", "data": "encrypted bytes"}
namespace["append_message"]("room", "user", "caption", attachment)
assert saved[0]["room"][0]["attachment"] == attachment
assert saved[0]["room"][0]["text"] == "encrypted:caption"
namespace["append_message"]("room", "user", "text only")
assert "attachment" not in rooms["room"][1]
print("Attachment checks passed")
