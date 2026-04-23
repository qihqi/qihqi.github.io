#!/usr/bin/env python3

from __future__ import annotations

import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_ROOT = REPO_ROOT / "build"
SOURCE_DOCS_DIR = REPO_ROOT / "docs"
BUILD_DOCS_DIR = BUILD_ROOT / "docs"
SOURCE_MKDOCS_CONFIG = REPO_ROOT / "mkdocs.yml"
BUILD_MKDOCS_CONFIG = BUILD_ROOT / "mkdocs.yml"


def main() -> int:
    if BUILD_ROOT.exists():
        shutil.rmtree(BUILD_ROOT)

    BUILD_DOCS_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE_DOCS_DIR, BUILD_DOCS_DIR)
    BUILD_MKDOCS_CONFIG.write_text(build_mkdocs_config())
    print("Prepared build/docs and build/mkdocs.yml")
    return 0


def build_mkdocs_config() -> str:
    original = SOURCE_MKDOCS_CONFIG.read_text()
    lines = []
    for line in original.splitlines():
        if line.startswith("docs_dir:") or line.startswith("site_dir:"):
            continue
        lines.append(line)

    staged = ["docs_dir: docs", "site_dir: site", *lines]
    return "\n".join(staged).rstrip() + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
