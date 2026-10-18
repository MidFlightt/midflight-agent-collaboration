"""Build only the shared backend's Lambda archive, without credentials or local runs."""

import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build/shared"


def main():
    if BUILD.exists():
        shutil.rmtree(BUILD)
    site = BUILD / "site"
    site.mkdir(parents=True)
    uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
    subprocess.run(
        [
            uv,
            "export",
            "--no-dev",
            "--no-hashes",
            "--no-emit-project",
            "--locked",
            "--extra",
            "falkordb",
            "-o",
            str(BUILD / "requirements.txt"),
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        [
            uv,
            "pip",
            "install",
            "--quiet",
            "-r",
            str(BUILD / "requirements.txt"),
            "--target",
            str(site),
            "--python-platform",
            "aarch64-manylinux2014",
            "--python-version",
            "3.12",
        ],
        check=True,
    )
    shutil.copytree(
        ROOT / "midflight", site / "midflight", ignore=shutil.ignore_patterns("__pycache__")
    )
    # One archive, two functions: the token RPC API and the hosted connector choose their
    # app through MIDFLIGHT_APP (default: the RPC API, unchanged).
    script = """#!/bin/bash
export PYTHONPATH=/var/task:$PYTHONPATH
cd /var/task
exec python3 -m uvicorn "${MIDFLIGHT_APP:-midflight.communication.cloud:create_app}" --factory \\
    --host 0.0.0.0 --port 8080 --no-access-log --log-level warning
"""
    archive = BUILD / "lambda.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(site.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                zipped.write(path, path.relative_to(site).as_posix())
        entry = zipfile.ZipInfo("run.sh")
        entry.external_attr = 0o100755 << 16
        zipped.writestr(entry, script)
    print(f"Built {archive} ({archive.stat().st_size // 1_000_000} MB)")


if __name__ == "__main__":
    main()
