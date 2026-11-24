
"""Controlled Git operations with immutable commit resolution and detached snapshots."""
from __future__ import annotations

import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory


def git(repo: Path, *args: str, timeout: int = 90) -> str:
    p = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if p.returncode:
        raise RuntimeError(
            f"git {args[0]} failed ({p.returncode}): "
            f"{p.stderr.strip()[:1000]}"
        )
    return p.stdout.strip()


def acquire_repository(
    source: str,
    cache_dir: Path,
    repository_id: str,
) -> Path:
    if source.startswith("https://"):
        dest = cache_dir / repository_id
        cache_dir.mkdir(parents=True, exist_ok=True)

        def normalized_url(value: str) -> str:
            return (
                value.strip()
                .lower()
                .rstrip("/")
                .removesuffix(".git")
            )

        # Reuse only a valid Git repository with the expected origin.
        if dest.is_dir():
            check = subprocess.run(
                [
                    "git", "-C", str(dest),
                    "rev-parse", "--is-inside-work-tree",
                ],
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
            )

            if check.returncode == 0:
                actual_origin = git(
                    dest, "remote", "get-url", "origin"
                )
                if normalized_url(actual_origin) != normalized_url(source):
                    raise RuntimeError(
                        f"Cache source mismatch for {repository_id}: "
                        f"{actual_origin!r} != {source!r}"
                    )
                return dest

            # Remove only an invalid/incomplete clone.
            shutil.rmtree(dest)

        # Clone to a temporary directory before placing it in cache.
        # Partial clone downloads file contents only when needed.
        with TemporaryDirectory(prefix="team7-clone-") as temp:
            clone_path = Path(temp) / repository_id

            p = subprocess.run(
                [
                    "git", "clone", "--quiet",
                    "--filter=blob:none",
                    "--no-checkout",
                    source, str(clone_path),
                ],
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
                check=False,
            )

            if p.returncode:
                raise RuntimeError(
                    f"clone failed: {p.stderr.strip()[:1000]}"
                )

            shutil.move(str(clone_path), str(dest))

        return dest

    path = Path(source).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(
            f"Local repository does not exist: {path}"
        )

    git(path, "rev-parse", "--is-inside-work-tree")
    return path


def commit_sha(repo: Path, ref: str) -> str:
    if not ref or ref.startswith("-"):
        raise ValueError("Invalid Git reference")

    return git(
        repo,
        "rev-parse",
        "--verify",
        f"{ref}^{{commit}}",
    )


def ensure_ancestor(
    repo: Path,
    baseline: str,
    followup: str,
) -> None:
    p = subprocess.run(
        [
            "git", "-C", str(repo),
            "merge-base", "--is-ancestor",
            baseline, followup,
        ],
        capture_output=True,
        timeout=60,
        check=False,
    )

    if p.returncode != 0:
        raise ValueError(
            "snapshot_ref is not an ancestor of followup_ref"
        )


def future_commits(
    repo: Path,
    baseline: str,
    followup: str,
) -> list[str]:
    if baseline == followup:
        return []

    ensure_ancestor(repo, baseline, followup)

    result = git(
        repo,
        "rev-list",
        "--reverse",
        "--ancestry-path",
        f"{baseline}..{followup}",
        timeout=180,
    )

    return result.splitlines() if result else []


@contextmanager
def snapshot_checkout(repo: Path, sha: str):
    """Use detached git worktree, never modify the user's active checkout."""
    with TemporaryDirectory(prefix="team7-snapshot-") as temp:
        path = Path(temp) / "source"

        git(
            repo,
            "worktree",
            "add",
            "--detach",
            "--quiet",
            str(path),
            sha,
            timeout=180,
        )

        try:
            yield path
        finally:
            git(
                repo,
                "worktree",
                "remove",
                "--force",
                str(path),
                timeout=180,
            )
