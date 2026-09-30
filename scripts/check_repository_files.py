"""Check tracked filenames only; never read or print secret file contents."""

from pathlib import PurePosixPath
import subprocess
import sys


def main():
    tracked = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    blocked = []
    for name in filter(None, tracked):
        path = PurePosixPath(name)
        secret = (path.name == ".env" or path.name.startswith(".env.")) and path.name not in {
            ".env.example", ".env.sample",
        }
        if secret or path.suffix in {".pem", ".key"} or name.startswith("logs/"):
            blocked.append(name)
    if blocked:
        print("Remove these runtime files from Git tracking before publishing:")
        for name in blocked:
            print(f"  {name}")
        print("Use git rm --cached for the listed paths to retain local copies. See docs/ci-cd.md.")
        return 1
    print("Repository runtime-file check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
