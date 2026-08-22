from pathlib import Path


class LocalObjectStore:
    """Development object store; the interface is intentionally replaceable by Cloud Storage."""

    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, object_key: str, content: bytes) -> str:
        target = self.root / object_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return object_key

    def read_text(self, object_key: str) -> str:
        return (self.root / object_key).read_text(encoding="utf-8")
