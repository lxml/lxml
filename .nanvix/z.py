"""Nanvix build integration for lxml."""

from __future__ import annotations

import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# zutil bootstrap helpers
# ---------------------------------------------------------------------------
import importlib, sys
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

def _zutil_import(name: str):
    return importlib.import_module(name)

try:
    from nanvix.zutil import ZScript
except ImportError:
    ZScript = None  # type: ignore[misc,assignment]

DOCKER_IMAGE = "nanvix/toolchain:latest-minimal"

class LxmlBuild:
    def __init__(self) -> None:
        self.root = _HERE.parent
        self.nanvix_dir = _HERE
        self.makefile = _HERE / "Makefile.nanvix"

    def build(self, platform: str = "microvm", mode: str = "multi-process", memory: str = "256mb") -> Path:
        build_dir = self.root / "build"
        build_dir.mkdir(exist_ok=True)

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.root}:/workspace",
            "-w", "/workspace/.nanvix",
            DOCKER_IMAGE,
            "make", "-f", "Makefile.nanvix",
            f"PLATFORM={platform}",
            f"MODE={mode}",
            f"MEMORY={memory}",
        ]
        print(f"[lxml] Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

        tarball = build_dir / f"lxml-{platform}-{mode}-{memory}.tar.bz2"
        if not tarball.is_file():
            raise RuntimeError(f"Expected tarball not found: {tarball}")
        return tarball


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Build lxml for Nanvix")
    parser.add_argument("--platform", default="microvm")
    parser.add_argument("--mode", default="multi-process")
    parser.add_argument("--memory", default="256mb")
    args = parser.parse_args()

    builder = LxmlBuild()
    tarball = builder.build(args.platform, args.mode, args.memory)
    print(f"[lxml] Built: {tarball}")


if __name__ == "__main__":
    main()
