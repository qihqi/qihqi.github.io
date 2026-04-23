#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import argparse
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "external-content.toml"
DEFAULT_CACHE_ROOT = REPO_ROOT / ".cache" / "external-content"
DEFAULT_MANIFEST_PATH = REPO_ROOT / ".external-content-manifest.json"


@dataclass(frozen=True)
class Mapping:
    repo: str
    ref: str
    source: Path
    target: Path
    mode: str


def main() -> int:
    args = parse_args()
    config_path = args.config.resolve() if args.config else DEFAULT_CONFIG_PATH
    config = load_config(config_path)

    cache_root = resolve_repo_path(config.get("cache_dir", ".cache/external-content"))
    manifest_raw_path = args.manifest_path or config.get("manifest_path", ".external-content-manifest.json")
    manifest_path = resolve_repo_path(manifest_raw_path)
    target_root = Path(args.target_root or config.get("target_root", "."))
    mappings = parse_mappings(config, target_root)

    cleanup_previous_targets(manifest_path)

    if not mappings:
        write_manifest(manifest_path, [])
        print(f"No mappings configured in {config_path.relative_to(REPO_ROOT)}")
        return 0

    grouped_sources: dict[tuple[str, str], set[Path]] = {}
    for mapping in mappings:
        grouped_sources.setdefault((mapping.repo, mapping.ref), set()).add(mapping.source)

    for (repo, ref), sources in grouped_sources.items():
        fetch_repo_snapshot(repo=repo, ref=ref, sources=sorted(sources), cache_root=cache_root)

    written_targets: list[str] = []
    for mapping in mappings:
        checkout_dir = cache_checkout_path(cache_root, mapping.repo, mapping.ref)
        source_path = cache_source_path(cache_root, mapping.repo, mapping.ref, mapping.source)
        target_path = repo_abspath(mapping.target)

        if not source_path.exists():
            raise SystemExit(f"Configured source does not exist after fetch: {mapping.repo}:{mapping.source}")

        apply_git_published_dates(checkout_dir=checkout_dir, source_path=source_path)

        ensure_within_repo(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if target_path.exists() or target_path.is_symlink():
            remove_path(target_path)

        if mapping.mode == "copy":
            copy_path(source_path, target_path)
        else:
            os.symlink(os.path.relpath(source_path, start=target_path.parent), target_path)

        written_targets.append(str(target_path.relative_to(REPO_ROOT)))
        print(f"{mapping.mode:7} {mapping.repo}@{mapping.ref}:{mapping.source} -> {mapping.target}")

    write_manifest(manifest_path, written_targets)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", nargs="?", type=Path)
    parser.add_argument("--manifest-path")
    parser.add_argument("--target-root")
    return parser.parse_args()


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise SystemExit(f"Missing config file: {config_path}")

    with config_path.open("rb") as fh:
        return tomllib.load(fh)


def parse_mappings(config: dict, target_root: Path) -> list[Mapping]:
    mappings = []
    raw_mappings = config.get("mappings", [])
    if not isinstance(raw_mappings, list):
        raise SystemExit("`mappings` must be an array of tables")

    for index, raw_mapping in enumerate(raw_mappings, start=1):
        try:
            repo = raw_mapping["repo"]
            source = Path(raw_mapping["source"])
            target = Path(raw_mapping["target"])
        except KeyError as exc:
            raise SystemExit(f"Missing required key in mappings[{index}]: {exc.args[0]}") from exc

        ref = raw_mapping.get("ref", "main")
        mode = raw_mapping.get("mode", "symlink")

        if mode not in {"symlink", "copy"}:
            raise SystemExit(f"Unsupported mode in mappings[{index}]: {mode}")

        if source.is_absolute() or target.is_absolute() or target_root.is_absolute():
            raise SystemExit(f"Absolute paths are not allowed in mappings[{index}]")
        if has_parent_traversal(source) or has_parent_traversal(target) or has_parent_traversal(target_root):
            raise SystemExit(f"`..` is not allowed in mappings[{index}] source/target paths")

        mappings.append(
            Mapping(
                repo=repo,
                ref=ref,
                source=source,
                target=target_root / target,
                mode=mode,
            )
        )

    return mappings


def cleanup_previous_targets(manifest_path: Path) -> None:
    if not manifest_path.exists():
        return

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid manifest file {manifest_path}: {exc}") from exc

    for relative_target in manifest.get("targets", []):
        target_path = repo_abspath(relative_target)
        ensure_within_repo(target_path)
        if target_path.exists() or target_path.is_symlink():
            remove_path(target_path)


def fetch_repo_snapshot(repo: str, ref: str, sources: list[Path], cache_root: Path) -> None:
    checkout_dir = cache_checkout_path(cache_root, repo, ref)
    checkout_dir.parent.mkdir(parents=True, exist_ok=True)

    clone_url = github_clone_url(repo)
    if not is_git_checkout(checkout_dir):
        if checkout_dir.exists():
            shutil.rmtree(checkout_dir)
        run_git(
            [
                "clone",
                clone_url,
                str(checkout_dir),
            ]
        )
    run_git(["-C", str(checkout_dir), "remote", "set-url", "origin", clone_url])
    run_git(["-C", str(checkout_dir), "fetch", "origin", ref, "--tags"])

    run_git(["-C", str(checkout_dir), "checkout", "--force", "FETCH_HEAD"])
    run_git(["-C", str(checkout_dir), "clean", "-fd"])
    run_git(["-C", str(checkout_dir), "checkout", ref, "--", *[str(path) for path in sources]])


def github_clone_url(repo: str) -> str:
    token = os.environ.get("EXTERNAL_CONTENT_GITHUB_TOKEN")
    if token:
        return f"https://x-access-token:{token}@github.com/{repo}.git"
    return f"https://github.com/{repo}.git"


def run_git(args: list[str]) -> None:
    completed = subprocess.run(["git", *args], cwd=REPO_ROOT, check=False)
    if completed.returncode != 0:
        raise SystemExit("git command failed while syncing external content")


def is_git_checkout(path: Path) -> bool:
    return path.is_dir() and (path / ".git").exists()


def resolve_repo_path(raw_path: str) -> Path:
    resolved = repo_abspath(raw_path)
    ensure_within_repo(resolved)
    return resolved


def has_parent_traversal(path: Path) -> bool:
    return ".." in path.parts


def repo_abspath(raw_path: str | Path) -> Path:
    return Path(os.path.abspath(REPO_ROOT / raw_path))


def ensure_within_repo(path: Path) -> None:
    try:
        path.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise SystemExit(f"Path escapes repository root: {path}") from exc


def cache_checkout_path(cache_root: Path, repo: str, ref: str) -> Path:
    safe_repo = repo.replace("/", "__")
    safe_ref = ref.replace("/", "__")
    return cache_root / f"{safe_repo}__{safe_ref}"


def cache_source_path(cache_root: Path, repo: str, ref: str, source: Path) -> Path:
    return cache_checkout_path(cache_root, repo, ref) / source


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def copy_path(source: Path, target: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)


def apply_git_published_dates(checkout_dir: Path, source_path: Path) -> None:
    if source_path.is_dir():
        for markdown_path in source_path.rglob("*.md"):
            maybe_apply_git_published_date(checkout_dir, markdown_path)
        repair_markdown_links(source_path)
        return

    maybe_apply_git_published_date(checkout_dir, source_path)


def maybe_apply_git_published_date(checkout_dir: Path, markdown_path: Path) -> None:
    if markdown_path.suffix.lower() != ".md" or markdown_path.is_dir():
        return

    relative_source_path = markdown_path.relative_to(checkout_dir)
    published_date = git_last_commit_date(checkout_dir, relative_source_path)
    if not published_date:
        return

    original = markdown_path.read_text()
    updated = inject_or_replace_published_date(original, published_date)
    if updated != original:
        markdown_path.write_text(updated)


def git_last_commit_date(checkout_dir: Path, source_path: Path) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(checkout_dir), "log", "-1", "--format=%cs", "--", str(source_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None

    published_date = completed.stdout.strip()
    return published_date or None


def inject_or_replace_published_date(content: str, published_date: str) -> str:
    published_line = f"*Published: {published_date}*"

    if re.search(r"^\*Published: .+\*$", content, flags=re.MULTILINE):
        return re.sub(
            r"^\*Published: .+\*$",
            published_line,
            content,
            count=1,
            flags=re.MULTILINE,
        )

    lines = content.splitlines()
    if lines and lines[0].startswith("# "):
        updated_lines = [lines[0], "", published_line, ""]
        updated_lines.extend(lines[1:])
        return "\n".join(updated_lines).rstrip() + "\n"

    return published_line + "\n\n" + content.lstrip()


def repair_markdown_links(root_dir: Path) -> None:
    for markdown_path in root_dir.rglob("*.md"):
        original = markdown_path.read_text()
        updated = rewrite_missing_numbered_links(markdown_path, original)
        if updated != original:
            markdown_path.write_text(updated)


def rewrite_missing_numbered_links(markdown_path: Path, content: str) -> str:
    pattern = re.compile(r"\(([^)#?]+\.md)\)")

    def replace(match: re.Match[str]) -> str:
        link_target = match.group(1)
        link_path = Path(link_target)
        if link_path.is_absolute() or len(link_path.parts) != 1:
            return match.group(0)

        resolved = markdown_path.parent / link_path
        if resolved.exists():
            return match.group(0)

        prefix = link_path.name.split("-", 1)[0]
        if not prefix.isdigit():
            return match.group(0)

        candidates = sorted(markdown_path.parent.glob(f"{prefix}-*.md"))
        if len(candidates) != 1:
            return match.group(0)

        return f"({candidates[0].name})"

    return pattern.sub(replace, content)


def write_manifest(manifest_path: Path, targets: list[str]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"targets": sorted(targets)}, indent=2) + "\n")




if __name__ == "__main__":
    raise SystemExit(main())
