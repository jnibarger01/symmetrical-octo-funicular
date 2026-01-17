"""Repository Inspector - Codebase analysis and context extraction."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.models import FileIndex, Symbol

logger = logging.getLogger(__name__)


class RepositoryInspector:
    """
    Repository inspector for analyzing codebases.

    Provides file indexing, symbol extraction, dependency tracking,
    and context selection for LLM prompts.
    """

    def __init__(self, root_path: Path) -> None:
        """
        Initialize the repository inspector.

        Args:
            root_path: Root directory of the repository
        """
        self.root_path = root_path
        self.file_index: dict[str, FileIndex] = {}
        self._language_extensions = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "jsx": "javascript",
            "tsx": "typescript",
            "java": "java",
            "go": "go",
            "rs": "rust",
            "c": "c",
            "cpp": "cpp",
            "h": "c",
            "hpp": "cpp",
            "md": "markdown",
            "yaml": "yaml",
            "yml": "yaml",
            "json": "json",
            "toml": "toml",
            "sql": "sql",
        }

    def index_repository(self, exclude_patterns: Optional[list[str]] = None) -> None:
        """
        Index all files in the repository.

        Args:
            exclude_patterns: Patterns to exclude (e.g., ['*.pyc', '__pycache__'])
        """
        if exclude_patterns is None:
            exclude_patterns = [
                "*.pyc",
                "__pycache__",
                ".git",
                "node_modules",
                ".venv",
                "venv",
                "dist",
                "build",
                ".codex",
            ]

        logger.info(f"Indexing repository at {self.root_path}")

        for file_path in self.root_path.rglob("*"):
            # Skip directories
            if file_path.is_dir():
                continue

            # Skip excluded patterns
            if self._should_exclude(file_path, exclude_patterns):
                continue

            # Index the file
            try:
                self._index_file(file_path)
            except Exception as e:
                logger.warning(f"Failed to index {file_path}: {e}")

        logger.info(f"Indexed {len(self.file_index)} files")

    def _should_exclude(self, file_path: Path, exclude_patterns: list[str]) -> bool:
        """Check if a file should be excluded."""
        for pattern in exclude_patterns:
            if file_path.match(pattern):
                return True
            # Check if any parent matches the pattern
            for parent in file_path.parents:
                if parent.match(pattern):
                    return True
        return False

    def _index_file(self, file_path: Path) -> None:
        """Index a single file."""
        relative_path = str(file_path.relative_to(self.root_path))

        # Determine language
        language = self._detect_language(file_path)

        # Read file content
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Skip binary files
            logger.debug(f"Skipping binary file: {relative_path}")
            return

        # Calculate hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Extract symbols
        symbols = self._extract_symbols(content, language)

        # Extract imports/exports
        imports, exports = self._extract_imports_exports(content, language)

        # Create index entry
        file_index = FileIndex(
            path=relative_path,
            language=language,
            size_bytes=file_path.stat().st_size,
            hash=content_hash,
            symbols=symbols,
            imports=imports,
            exports=exports,
            last_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
        )

        self.file_index[relative_path] = file_index

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        suffix = file_path.suffix.lstrip(".")
        return self._language_extensions.get(suffix, "text")

    def _extract_symbols(self, content: str, language: str) -> list[Symbol]:
        """
        Extract symbols (functions, classes) from code.

        This is a simple implementation. For production, consider using
        tree-sitter or language-specific parsers.
        """
        symbols: list[Symbol] = []

        # Simple regex-based extraction for Python
        if language == "python":
            import re

            # Find function definitions
            func_pattern = r"^def\s+(\w+)\s*\((.*?)\):"
            for i, line in enumerate(content.split("\n"), 1):
                match = re.match(func_pattern, line.strip())
                if match:
                    symbols.append(
                        Symbol(
                            name=match.group(1),
                            type="function",
                            line_start=i,
                            line_end=i,  # TODO: Find actual end
                            signature=f"def {match.group(1)}({match.group(2)})",
                        )
                    )

            # Find class definitions
            class_pattern = r"^class\s+(\w+)"
            for i, line in enumerate(content.split("\n"), 1):
                match = re.match(class_pattern, line.strip())
                if match:
                    symbols.append(
                        Symbol(
                            name=match.group(1),
                            type="class",
                            line_start=i,
                            line_end=i,  # TODO: Find actual end
                        )
                    )

        # TODO: Add support for other languages

        return symbols

    def _extract_imports_exports(self, content: str, language: str) -> tuple[list[str], list[str]]:
        """Extract import and export statements."""
        imports: list[str] = []
        exports: list[str] = []

        if language == "python":
            import re

            # Find imports
            import_pattern = r"^(?:from\s+(\S+)\s+)?import\s+(.+)"
            for line in content.split("\n"):
                match = re.match(import_pattern, line.strip())
                if match:
                    if match.group(1):
                        imports.append(match.group(1))
                    imports.extend(
                        item.strip().split()[0] for item in match.group(2).split(",")
                    )

        # TODO: Add support for other languages

        return imports, exports

    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get the content of a file."""
        full_path = self.root_path / file_path

        if not full_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None

    def find_related_files(self, target_file: str, max_files: int = 5) -> list[str]:
        """
        Find files related to the target file.

        Related files are determined by:
        - Import/export relationships
        - Similar file paths
        - Shared symbols

        Args:
            target_file: Target file path
            max_files: Maximum number of related files to return

        Returns:
            List of related file paths
        """
        if target_file not in self.file_index:
            return []

        target_index = self.file_index[target_file]
        related: dict[str, float] = {}

        for file_path, file_index in self.file_index.items():
            if file_path == target_file:
                continue

            score = 0.0

            # Check import relationships
            if any(imp in file_index.exports for imp in target_index.imports):
                score += 10.0

            if any(exp in file_index.imports for exp in target_index.exports):
                score += 10.0

            # Check path similarity
            target_parts = Path(target_file).parts
            file_parts = Path(file_path).parts
            common_parts = len(set(target_parts) & set(file_parts))
            score += common_parts * 2.0

            # Check symbol overlap
            target_symbols = {s.name for s in target_index.symbols}
            file_symbols = {s.name for s in file_index.symbols}
            symbol_overlap = len(target_symbols & file_symbols)
            score += symbol_overlap * 5.0

            if score > 0:
                related[file_path] = score

        # Sort by score and return top N
        sorted_related = sorted(related.items(), key=lambda x: x[1], reverse=True)
        return [file_path for file_path, _ in sorted_related[:max_files]]

    def get_files_by_language(self, language: str) -> list[str]:
        """Get all files of a specific language."""
        return [
            file_path
            for file_path, index in self.file_index.items()
            if index.language == language
        ]

    def search_symbols(self, name: str) -> list[tuple[str, Symbol]]:
        """
        Search for symbols by name.

        Args:
            name: Symbol name to search for

        Returns:
            List of (file_path, symbol) tuples
        """
        results: list[tuple[str, Symbol]] = []

        for file_path, index in self.file_index.items():
            for symbol in index.symbols:
                if name.lower() in symbol.name.lower():
                    results.append((file_path, symbol))

        return results

    def get_modified_files(self, since: datetime) -> list[str]:
        """Get files modified since a given timestamp."""
        return [
            file_path
            for file_path, index in self.file_index.items()
            if index.last_modified > since
        ]

    def get_index_stats(self) -> dict[str, int]:
        """Get statistics about the file index."""
        stats = {
            "total_files": len(self.file_index),
            "total_symbols": sum(len(index.symbols) for index in self.file_index.values()),
        }

        # Count by language
        language_counts: dict[str, int] = {}
        for index in self.file_index.values():
            language_counts[index.language] = language_counts.get(index.language, 0) + 1

        stats["by_language"] = language_counts

        return stats
