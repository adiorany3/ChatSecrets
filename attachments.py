"""Bounded attachment validation; no uploaded files written to disk."""
import io
from pathlib import PurePosixPath
import zipfile

MAX_FILE_BYTES = 5 * 1024 * 1024
FILE_TYPES = ("png", "jpg", "jpeg", "gif", "webp", "pdf", "txt", "csv", "docx", "xlsx", "pptx")


def validate_attachment(name: str, data: bytes) -> dict[str, str]:
    name = PurePosixPath(name.replace("\\", "/")).name
    if not name or len(name) > 255 or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise ValueError("Nama file tidak valid (maksimal 255 karakter).")
    if not 0 < len(data) <= MAX_FILE_BYTES:
        raise ValueError("File harus berisi data dan maksimal 5 MiB.")
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if extension not in FILE_TYPES:
        raise ValueError("Format file tidak didukung.")
    # ponytail: signatures only, not malware scanning; add a scanner for untrusted public uploads.
    mime = "application/octet-stream"
    valid = True
    if extension == "png":
        valid, mime = data.startswith(b"\x89PNG\r\n\x1a\n"), "image/png"
    elif extension in ("jpg", "jpeg"):
        valid, mime = data.startswith(b"\xff\xd8\xff"), "image/jpeg"
    elif extension == "gif":
        valid, mime = data[:6] in (b"GIF87a", b"GIF89a"), "image/gif"
    elif extension == "webp":
        valid, mime = data[:4] == b"RIFF" and data[8:12] == b"WEBP", "image/webp"
    elif extension == "pdf":
        valid = data.startswith(b"%PDF-")
    elif extension in ("txt", "csv"):
        try:
            text = data.decode("utf-8-sig")
            valid = "\x00" not in text
        except UnicodeDecodeError:
            valid = False
    else:
        required = {"docx": "word/document.xml", "xlsx": "xl/workbook.xml", "pptx": "ppt/presentation.xml"}
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = archive.namelist()
                valid = "[Content_Types].xml" in names and required[extension] in names
                valid = valid and not any(n.lower().endswith("vbaproject.bin") for n in names)
        except (zipfile.BadZipFile, OSError, ValueError):
            valid = False
    if not valid:
        raise ValueError("Isi file tidak sesuai format atau tidak didukung.")
    return {"name": name, "mime": mime}
