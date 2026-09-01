import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .errors import ConflictError


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


class AtomicStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def path(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    def read(self, *parts: str) -> dict[str, Any] | None:
        path = self.path(*parts)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write(self, payload: dict[str, Any], *parts: str, immutable: bool = False) -> Path:
        path = self.path(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        if immutable and path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if digest(existing) != digest(payload):
                raise ConflictError(f"immutable artifact conflict: {path}")
            return path

        data = canonical_bytes(payload)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        return path
