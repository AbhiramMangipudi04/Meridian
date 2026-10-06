"""
Local knowledge-base document access abstraction.

Backs the `knowledgebase://{document_id}/excerpt` MCP Resource. Reuses
the existing `data/docs/` folders as-is -- no new database table is
introduced for this. A "document_id" is simply the Markdown file's stem
(filename without the .md extension), e.g. "premium_auto_debit_policy".

Only a single document's excerpt is ever returned, never the whole
knowledge base -- see read_excerpt().
"""
from __future__ import annotations

from pathlib import Path

DOCS_ROOT = Path(__file__).resolve().parents[1] / "data" / "docs"
DOC_SUBDIRS = ("communication_templates", "policy_docs", "product_docs", "faqs")

DEFAULT_EXCERPT_MAX_CHARS = 800


class DocumentNotFoundError(Exception):
    def __init__(self, document_id: str):
        self.document_id = document_id
        super().__init__(f"Knowledge-base document '{document_id}' was not found.")


def _find_document_path(document_id: str) -> Path | None:
    for subdir in DOC_SUBDIRS:
        candidate = DOCS_ROOT / subdir / f"{document_id}.md"
        if candidate.is_file():
            return candidate
    return None


def _split_front_matter(raw_text: str) -> tuple[dict, str]:
    """
    Minimal, dependency-free YAML-front-matter splitter. Front matter in
    this project is always a flat `key: value` block delimited by `---`
    lines (see data/docs/*/*.md), so a tiny hand-rolled parser avoids
    pulling in a YAML dependency for something this simple.
    """
    lines = raw_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, raw_text

    metadata: dict[str, str] = {}
    end_index = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_index = i
            break
        if ":" in lines[i]:
            key, _, value = lines[i].partition(":")
            metadata[key.strip()] = value.strip().strip('"')

    if end_index is None:
        return {}, raw_text

    body = "\n".join(lines[end_index + 1 :])
    return metadata, body


def read_excerpt(document_id: str, max_chars: int = DEFAULT_EXCERPT_MAX_CHARS) -> dict:
    """
    Returns: {"document_id": ..., "metadata": {...}, "excerpt": "..."}

    Raises DocumentNotFoundError if no matching file exists in any of
    the four knowledge-base subdirectories.
    """
    path = _find_document_path(document_id)
    if path is None:
        raise DocumentNotFoundError(document_id)

    raw_text = path.read_text(encoding="utf-8")
    metadata, body = _split_front_matter(raw_text)
    excerpt = body.strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars].rstrip() + "..."

    return {"document_id": document_id, "metadata": metadata, "excerpt": excerpt}
