#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


SKILL_NAME = "agent-forest"
BUNDLE_ENTRIES = [
    "SKILL.md",
    "agents",
    "assets",
    "references",
    "scripts",
    "README.md",
    "README_ZH.md",
]
CONFIG_EXAMPLE_NAME = "agent-forest.config.example.json"
CONFIG_NAME = "agent-forest.config.json"


def default_codex_home() -> Path:
    raw = os.environ.get("CODEX_HOME")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".codex"


def default_claude_home() -> Path:
    raw = os.environ.get("CLAUDE_HOME")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".claude"


def source_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def log(message: str) -> None:
    print(message)


def remove_path(path: Path, dry_run: bool) -> None:
    if not path.exists():
        return
    if dry_run:
        log(f"[dry-run] remove {path}")
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def copy_entry(source: Path, destination: Path, dry_run: bool) -> None:
    if dry_run:
        log(f"[dry-run] copy {source} -> {destination}")
        return

    if source.is_dir():
        shutil.copytree(
            source,
            destination,
            dirs_exist_ok=False,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def copy_bundle(source_root: Path, destination_root: Path, force: bool, dry_run: bool) -> None:
    if destination_root.exists():
        if not force:
            raise FileExistsError(
                f"Destination already exists: {destination_root}. Re-run with --force to replace it."
            )
        remove_path(destination_root, dry_run=dry_run)

    if not dry_run:
        destination_root.mkdir(parents=True, exist_ok=True)

    for entry in BUNDLE_ENTRIES:
        source = source_root / entry
        if not source.exists():
            raise FileNotFoundError(f"Missing bundle entry: {source}")
        copy_entry(source, destination_root / entry, dry_run=dry_run)


def ensure_config_copy(bundle_root: Path, dry_run: bool) -> Path:
    example_path = bundle_root / "assets" / CONFIG_EXAMPLE_NAME
    config_path = bundle_root / "assets" / CONFIG_NAME
    if config_path.exists():
        return config_path

    if dry_run:
        log(f"[dry-run] create {config_path} from {example_path}")
        return config_path

    if not example_path.exists():
        raise FileNotFoundError(f"Missing config example: {example_path}")

    shutil.copy2(example_path, config_path)
    return config_path


def install_codex(source_root: Path, codex_home: Path, force: bool, dry_run: bool) -> dict[str, Path]:
    bundle_root = codex_home / "skills" / SKILL_NAME
    copy_bundle(source_root, bundle_root, force=force, dry_run=dry_run)
    config_path = ensure_config_copy(bundle_root, dry_run=dry_run)
    return {"bundle_root": bundle_root, "config_path": config_path}


def install_claude(source_root: Path, claude_home: Path, force: bool, dry_run: bool) -> dict[str, Path]:
    bundle_root = claude_home / "skills" / SKILL_NAME
    copy_bundle(source_root, bundle_root, force=force, dry_run=dry_run)
    config_path = ensure_config_copy(bundle_root, dry_run=dry_run)
    return {"bundle_root": bundle_root, "config_path": config_path}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Agent Forest for Codex and Claude Code")
    parser.add_argument(
        "--target",
        choices=["codex", "claude", "all"],
        default="all",
        help="Which platform to install for",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=source_root_from_script(),
        help="Path to the source repository root",
    )
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=default_codex_home(),
        help="Codex home directory. Defaults to $CODEX_HOME or ~/.codex",
    )
    parser.add_argument(
        "--claude-home",
        type=Path,
        default=default_claude_home(),
        help="Claude home directory. Defaults to $CLAUDE_HOME or ~/.claude",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing installation",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without writing files",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source_root = args.source_root.resolve()

    if not (source_root / "SKILL.md").exists():
        print(f"Source root does not look like the Agent Forest repository: {source_root}", file=sys.stderr)
        return 1

    try:
        if args.target in {"codex", "all"}:
            codex_result = install_codex(
                source_root=source_root,
                codex_home=args.codex_home.expanduser(),
                force=args.force,
                dry_run=args.dry_run,
            )
            log(f"Installed Codex skill bundle at {codex_result['bundle_root']}")
            log(f"Codex config path: {codex_result['config_path']}")

        if args.target in {"claude", "all"}:
            claude_result = install_claude(
                source_root=source_root,
                claude_home=args.claude_home.expanduser(),
                force=args.force,
                dry_run=args.dry_run,
            )
            log(f"Installed Claude bundle at {claude_result['bundle_root']}")
            log(f"Claude config path: {claude_result['config_path']}")
    except (FileExistsError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.dry_run:
        log("Dry run complete.")
    else:
        log("Restart Codex or Claude Code if the top-level skills directory was created during this session.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
