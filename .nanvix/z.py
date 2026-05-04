# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.

"""Nanvix build script for lxml.

Usage:
    ./z setup     # Download Nanvix sysroot
    ./z build     # Cross-compile lxml C extensions
    ./z test      # Run test suite (smoke)
    ./z release   # Package release tarball
    ./z clean     # Remove build artifacts
"""

import sys
from pathlib import Path

from nanvix_zutil import CFG_SYSROOT, CFG_TOOLCHAIN, EXIT_MISSING_DEP, ZScript, log

IS_WINDOWS = sys.platform == "win32"

_MAKE_VAR_CONFIG = "CONFIG_NANVIX"
_MAKE_VAR_HOME = "NANVIX_HOME"
_MAKE_VAR_TOOLCHAIN = "NANVIX_TOOLCHAIN"
_MAKE_VAR_PLATFORM = "PLATFORM"
_MAKE_VAR_PROCESS_MODE = "PROCESS_MODE"
_MAKE_VAR_MEMORY_SIZE = "MEMORY_SIZE"


class LxmlBuild(ZScript):
    """Build script for nanvix/lxml."""

    def _make_args(self, *targets: str) -> list[str]:
        """Build the common make argument list."""
        sysroot = self.config.get(CFG_SYSROOT, "")
        if not sysroot:
            log.fatal(
                f"{CFG_SYSROOT} is not set.",
                code=EXIT_MISSING_DEP,
                hint="Run `./z setup` first to download the sysroot.",
            )
        toolchain = self.config.get(CFG_TOOLCHAIN, "/opt/nanvix") or "/opt/nanvix"
        sysroot_p = self.translate_path(Path(sysroot))
        toolchain_p = self.translate_path(Path(toolchain))

        args = [
            "make",
            "-f",
            ".nanvix/Makefile.nanvix",
            f"{_MAKE_VAR_CONFIG}=y",
            f"{_MAKE_VAR_HOME}={sysroot_p}",
            f"{_MAKE_VAR_TOOLCHAIN}={toolchain_p}",
        ]

        args.extend(
            [
                f"{_MAKE_VAR_PLATFORM}={self.config.machine}",
                f"{_MAKE_VAR_PROCESS_MODE}={self.config.deployment_mode}",
                f"{_MAKE_VAR_MEMORY_SIZE}={self.config.memory_size}",
            ]
        )

        args.extend(targets)
        return args

    def setup(self) -> bool:
        """Download the Nanvix sysroot."""
        return super().setup()

    def build(self) -> None:
        """Cross-compile lxml C extensions for Nanvix."""
        self.run(*self._make_args("all"), cwd=self.repo_root)

    def test(self) -> None:
        """Run the lxml test suite."""
        if IS_WINDOWS:
            print("Skipping tests on Windows (no runtime test binaries for lxml).")
            return
        targets = self.targets if self.targets else ["test"]
        self.run(*self._make_args(*targets), cwd=self.repo_root)

    def release(self) -> None:
        """Package the lxml release tarball and verify it."""
        self.run(*self._make_args("package"), cwd=self.repo_root)
        self.run(*self._make_args("verify-package"), cwd=self.repo_root)

    def clean(self) -> None:
        """Remove build artifacts."""
        self.run(
            "make",
            "-f",
            ".nanvix/Makefile.nanvix",
            "clean",
            cwd=self.repo_root,
        )


if __name__ == "__main__":
    LxmlBuild.main()
