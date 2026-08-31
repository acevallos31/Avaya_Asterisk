from pathlib import Path


class RepositoryTextSource:
    """Single responsibility: read text files from the repository."""

    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[2])

    def read(self, relative_path):
        path = self.root / relative_path
        return path.read_text(encoding="utf-8", errors="replace")

    def exists(self, relative_path):
        return (self.root / relative_path).exists()


class TextPolicy:
    """Small reusable policy object for deterministic text assertions."""

    @staticmethod
    def contains_any(text, tokens):
        return [token for token in tokens if token in text]

    @staticmethod
    def contains_all(text, tokens):
        return all(token in text for token in tokens)
