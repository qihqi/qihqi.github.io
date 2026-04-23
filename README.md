# Cero vale todo

This repository now uses MkDocs instead of Jekyll.

## Local development

```bash
uv venv
source .venv/bin/activate
uv sync
mkdocs serve
```

## Build

```bash
source .venv/bin/activate
uv sync
make
```

## Serve

```bash
source .venv/bin/activate
uv sync
make serve
```

## External GitHub Content

Use `external-content.toml` to map files or directories from other GitHub repositories into this blog before the MkDocs build.

Example:

```toml
[[mappings]]
repo = "your-org/notes"
ref = "main"
source = "posts/ml/tpu.md"
target = "docs/posts/tpu-notes.md"
mode = "copy"
```

The GitHub Actions workflow runs `python scripts/sync_external_content.py` before `mkdocs build --strict`.

Use `mode = "symlink"` when you want the blog to point at the fetched checkout inside `.cache/`, or `mode = "copy"` when you want a plain copied file or directory in the target location.

If you need to fetch private repositories outside the default `GITHUB_TOKEN` scope, add an `EXTERNAL_CONTENT_GITHUB_TOKEN` repository secret with read access to those repos.

Local builds stage content into `build/`: `make` copies `docs/` to `build/docs`, syncs external content into that staged tree, and then runs MkDocs with `build/mkdocs.yml`.
