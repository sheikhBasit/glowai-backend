import os
import uuid
from pathlib import Path

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))


def save(data: bytes, folder: str, ext: str = "jpg") -> str:
    dest = UPLOAD_DIR / folder
    dest.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}.{ext}"
    (dest / filename).write_bytes(data)
    return f"{folder}/{filename}"


def read(path: str) -> bytes:
    return (UPLOAD_DIR / path).read_bytes()


def delete(path: str) -> None:
    target = UPLOAD_DIR / path
    if target.exists():
        target.unlink()
