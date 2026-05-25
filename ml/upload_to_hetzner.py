#!/usr/bin/env python3
"""Generate an rsync-compatible file list from the dataset manifest and launch
the upload to the Hetzner training server.

Reads ml/authentic_sampled.json, extracts the path of each FLAC, converts it
to a path relative to the source root (`D:/FLAC/`), and writes that list to
ml/upload_list.txt. Then prints the rsync command to run (or runs it directly
with --execute).

We rsync rather than scp because:
  * Resumable across interruptions
  * Single SSH channel handles all 890 files (no per-file overhead)
  * --progress shows transfer rate live
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path


def to_relative_posix(path_str: str, source_root: Path) -> str:
    """Convert a Windows absolute path to a posix-style relative path from source_root."""
    p = Path(path_str)
    rel = p.relative_to(source_root)
    return rel.as_posix()


def to_msys_path(windows_path: Path) -> str:
    """Convert C:/Users/foo to /c/Users/foo for Git Bash / MSYS rsync."""
    parts = windows_path.as_posix().split("/", 1)
    drive = parts[0].rstrip(":").lower()
    rest = parts[1] if len(parts) > 1 else ""
    return f"/{drive}/{rest}".rstrip("/") + "/"


def main(manifest_path: str, source_root_str: str, list_output: str,
         execute: bool, key_path: str, dest_host: str, dest_path: str,
         dry_run: bool):
    manifest_p = Path(manifest_path)
    if not manifest_p.is_file():
        print(f"ERROR: manifest not found at {manifest_p}", file=sys.stderr)
        return 1

    with open(manifest_p, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    source_root = Path(source_root_str).resolve()

    # Build relative paths
    rel_paths: list[str] = []
    missing = 0
    for entry in manifest["files"]:
        try:
            rel = to_relative_posix(entry["path"], source_root)
        except ValueError:
            missing += 1
            continue
        # rsync respects the list literally; skip files that no longer exist
        if not Path(entry["path"]).is_file():
            missing += 1
            continue
        rel_paths.append(rel)

    print(f"Files in manifest    : {len(manifest['files'])}")
    print(f"Files to upload      : {len(rel_paths)}")
    print(f"Files missing/skipped: {missing}")

    list_p = Path(list_output)
    list_p.parent.mkdir(parents=True, exist_ok=True)
    with open(list_p, "w", encoding="utf-8", newline="\n") as f:
        for r in rel_paths:
            f.write(r + "\n")
    print(f"List written to      : {list_p}")

    # Build the rsync command. Note: requires Git Bash / MSYS environment.
    source_msys = to_msys_path(source_root)
    # MSYS path for the SSH key
    key_msys = to_msys_path(Path(key_path).parent) + Path(key_path).name

    rsync_cmd = [
        "rsync",
        "-avhP",
        "--files-from", str(list_p).replace("\\", "/"),
        "-e", f"ssh -i {key_msys} -o StrictHostKeyChecking=accept-new",
        source_msys,
        f"{dest_host}:{dest_path}",
    ]
    if dry_run:
        rsync_cmd.insert(1, "--dry-run")

    print("\nRsync command (run from Git Bash):")
    print("  " + " ".join(shlex.quote(a) for a in rsync_cmd))

    if execute:
        print("\nLaunching rsync...")
        return subprocess.call(rsync_cmd)
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--manifest", default="ml/authentic_sampled.json")
    p.add_argument("--source-root", default="D:/FLAC")
    p.add_argument("--list-output", default="ml/upload_list.txt")
    p.add_argument("--key", default=str(Path.home() / ".ssh" / "secours_madactylo_2026-05-11"))
    p.add_argument("--dest-host", default="root@144.76.203.6")
    p.add_argument("--dest-path", default="/root/flac-detective-ml/dataset/authentic/")
    p.add_argument("--execute", action="store_true",
                   help="Actually run rsync; otherwise just print the command")
    p.add_argument("--dry-run", action="store_true",
                   help="Pass --dry-run to rsync (no actual transfer)")
    args = p.parse_args()
    sys.exit(main(args.manifest, args.source_root, args.list_output,
                  args.execute, args.key, args.dest_host, args.dest_path,
                  args.dry_run))
