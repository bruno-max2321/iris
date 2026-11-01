"""Filesystem layout. The repository root holds the registry and schemas; the workspace root holds
runtime state. On the Grok Bot VM both are /workspace/iris; during development they may differ."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = REPO_ROOT / "registry"
SCHEMAS_DIR = REPO_ROOT / "schemas"
FIXTURES_DIR = REPO_ROOT / "fixtures"

VOCABULARY_FILE = REGISTRY_DIR / "vocabulary.yaml"
VOCABULARY_SCHEMA = REGISTRY_DIR / "vocabulary.schema.json"
STYLE_BIBLE_SCHEMA = SCHEMAS_DIR / "style_bible.schema.json"
STYLE_BIBLE_EXAMPLE = SCHEMAS_DIR / "examples" / "style_bible.example.json"


def workspace_root() -> Path:
    """Runtime state root. Override with IRIS_WORKSPACE; defaults to the repository root."""
    return Path(os.environ.get("IRIS_WORKSPACE", str(REPO_ROOT))).resolve()


def runtime_dirs() -> dict[str, Path]:
    w = workspace_root()
    return {
        "secrets": w / "secrets",
        "db": w / "db",
        "artifacts": w / "artifacts",
        "refs": w / "refs",
        "styles": w / "styles",
        "checks": w / "checks",
        "ledger": w / "ledger",
    }
