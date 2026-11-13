from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass
class FileClassification:
    should_index: bool
    language: str | None
    skip_reason: str | None = None


_BINARY_EXTENSIONS = frozenset(
    {
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".bmp", ".webp", ".tiff",
        ".svg", ".woff", ".woff2", ".ttf", ".eot", ".otf",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".tgz",
        ".exe", ".dll", ".so", ".dylib", ".a", ".lib",
        ".pyc", ".pyo", ".pyd", ".class", ".jar", ".war", ".ear",
        ".mp3", ".mp4", ".avi", ".mov", ".mkv", ".wav", ".flac",
        ".db", ".sqlite", ".sqlite3",
        ".bin", ".dat", ".img", ".iso",
        ".lock",  # generic lock files
    }
)

_LOCK_FILES = frozenset(
    {
        "package-lock.json",
        "yarn.lock",
        "poetry.lock",
        "pipfile.lock",
        "pnpm-lock.yaml",
        "composer.lock",
        "gemfile.lock",
        "cargo.lock",
        "flake.lock",
    }
)

_VENDOR_PATH_SEGMENTS = frozenset(
    {
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".env",
        "dist",
        "build",
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
        "vendor",
        "third_party",
        "third-party",
        "thirdparty",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "coverage",
        ".coverage",
        "htmlcov",
        ".tox",
        "site-packages",
        ".next",
        ".nuxt",
        ".cache",
        "target",  # Rust/Maven build output
    }
)

_MAX_FILE_SIZE = 500 * 1024  # 500 KB

_PYTHON_EXTS = frozenset({".py"})
_JAVASCRIPT_EXTS = frozenset({".js", ".jsx", ".mjs", ".cjs"})
_TYPESCRIPT_EXTS = frozenset({".ts", ".tsx", ".mts", ".cts"})
_TEXT_EXTS = frozenset(
    {
        ".md", ".mdx", ".txt", ".rst",
        ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg",
        ".env.example", ".env.sample",
        ".gitignore", ".dockerignore", ".editorconfig",
        ".xml", ".html", ".htm", ".css", ".scss", ".sass", ".less",
        ".sh", ".bash", ".zsh", ".fish",
        ".sql",
        ".graphql", ".gql",
        ".proto",
    }
)


class FileClassifier:
    """Classify repository files for indexing."""

    def classify(self, path: str, size_bytes: int) -> FileClassification:
        p = PurePosixPath(path)
        filename = p.name.lower()
        suffix = p.suffix.lower()

        # Check vendor/generated path segments
        parts = set(part.lower() for part in p.parts[:-1])  # exclude filename
        if parts & _VENDOR_PATH_SEGMENTS:
            return FileClassification(
                should_index=False,
                language=None,
                skip_reason="vendor_or_generated_path",
            )

        # Check lock files by name
        if filename in _LOCK_FILES:
            return FileClassification(
                should_index=False, language=None, skip_reason="lock_file"
            )

        # Check file size
        if size_bytes > _MAX_FILE_SIZE:
            return FileClassification(
                should_index=False, language=None, skip_reason="file_too_large"
            )

        # Check binary extensions
        if suffix in _BINARY_EXTENSIONS:
            return FileClassification(
                should_index=False, language=None, skip_reason="binary_file"
            )

        # Classify by language
        if suffix in _PYTHON_EXTS:
            return FileClassification(should_index=True, language="python")

        if suffix in _JAVASCRIPT_EXTS:
            return FileClassification(should_index=True, language="javascript")

        if suffix in _TYPESCRIPT_EXTS:
            return FileClassification(should_index=True, language="typescript")

        if suffix in _TEXT_EXTS or filename.startswith(".env"):
            return FileClassification(should_index=True, language="text")

        # Unknown extension — skip
        return FileClassification(
            should_index=False, language=None, skip_reason="unknown_extension"
        )
