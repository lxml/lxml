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

import subprocess
import shutil
import sys
import tempfile
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

    def docker_image(self) -> str:
        """Return the Docker image for cross-compilation."""
        return "ghcr.io/nanvix/toolchain-gcc"

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
        # Dependencies are now shipped as .tar.gz; override the default
        # artifact_pattern (which still targets .tar.bz2 in zutil <=0.8.1).
        _gz = "{name}-{machine}-{mode}-{mem}.tar.gz"
        for dep in self.manifest.dependencies:  # type: ignore[attr-defined]
            dep.artifact_pattern = _gz  # type: ignore[attr-defined]

        # Monkey-patch tarfile.open to auto-detect compression so that
        # buildroot.install_dep (which hardcodes "r:bz2") can extract
        # .tar.gz archives produced by newer dependency releases.
        import tarfile

        _orig_tarfile_open = tarfile.open

        def _tarfile_open_auto(
            name: object = None,
            mode: str = "r",
            *args: object,
            **kwargs: object,
        ) -> tarfile.TarFile:
            if mode == "r:bz2":
                mode = "r:*"
            return _orig_tarfile_open(name, mode, *args, **kwargs)  # type: ignore[arg-type]

        tarfile.open = _tarfile_open_auto  # type: ignore[assignment]
        try:
            return super().setup()
        finally:
            tarfile.open = _orig_tarfile_open  # type: ignore[assignment]

    def build(self) -> None:
        """Cross-compile lxml C extensions for Nanvix."""
        self.run(*self._make_args("all"), cwd=self.repo_root)

    def test(self) -> None:
        """Run the lxml test suite."""
        if IS_WINDOWS:
            self._run_tests_windows()
            return
        targets = self.targets if self.targets else ["test"]
        self.run(*self._make_args(*targets), cwd=self.repo_root)

    def _run_tests_windows(self) -> None:
        """Run tests natively on Windows via nanvixd.exe."""
        if self.config.deployment_mode != "standalone":
            print(
                f"Skipping tests on Windows for mode '{self.config.deployment_mode}' (requires linuxd)."
            )
            return

        sysroot = self.config.get(CFG_SYSROOT, "")
        if not sysroot:
            log.fatal(
                f"{CFG_SYSROOT} is not set.",
                code=EXIT_MISSING_DEP,
                hint="Run `./z setup` first.",
            )
        sysroot_path = Path(sysroot)
        nanvixd = sysroot_path / "bin" / "nanvixd.exe"
        mkramfs = sysroot_path / "bin" / "mkramfs.exe"
        if not nanvixd.is_file():
            log.fatal(
                "nanvixd.exe not found.",
                code=EXIT_MISSING_DEP,
                hint="Run `./z setup` first.",
            )
        if not mkramfs.is_file():
            log.fatal(
                "mkramfs.exe not found.",
                code=EXIT_MISSING_DEP,
                hint="Run `./z setup` first.",
            )

        test_allowlist = {"test_lxml.elf"}
        test_binaries: list[Path] = []
        for candidate in [self.repo_root, self.repo_root / "build"]:
            if candidate.is_dir():
                for elf in sorted(candidate.glob("*.elf")):
                    if elf.name in test_allowlist and elf.name not in {
                        x.name for x in test_binaries
                    }:
                        test_binaries.append(elf)

        if not test_binaries:
            print("No test binaries found; skipping Windows tests.")
            return

        failed: list[str] = []
        for binary in test_binaries:
            name = binary.stem
            print(f"RUN  {name}...")
            with tempfile.TemporaryDirectory(prefix=f"nanvix_{name}_") as tmpdir:
                tmpdir_path = Path(tmpdir)
                ramfs_dir = tmpdir_path / "ramfs"
                ramfs_dir.mkdir()
                (ramfs_dir / "tmp").mkdir(exist_ok=True)
                shutil.copy2(binary, ramfs_dir / binary.name)
                ramfs_img = tmpdir_path / f"rootfs_{name}.img"
                try:
                    subprocess.run(
                        [str(mkramfs.resolve()), "-o", str(ramfs_img), str(ramfs_dir)],
                        check=True,
                        timeout=60,
                    )
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    print(f"FAIL {name} (mkramfs: {e})")
                    failed.append(name)
                    continue
                try:
                    result = subprocess.run(
                        [
                            str(nanvixd.resolve()),
                            "-bin-dir",
                            str((sysroot_path / "bin").resolve()),
                            "-ramfs",
                            str(ramfs_img),
                            "--",
                            f"./{binary.name}",
                        ],
                        stdin=subprocess.DEVNULL,
                        timeout=120,
                    )
                    if result.returncode != 0:
                        print(f"FAIL {name} (exit code {result.returncode})")
                        failed.append(name)
                    else:
                        print(f"OK   {name}")
                except subprocess.TimeoutExpired:
                    print(f"FAIL {name} (timeout)")
                    failed.append(name)

        if failed:
            raise RuntimeError(f"{len(failed)} test(s) failed: {' '.join(failed)}")
        print(f"\t\t*** All {len(test_binaries)} tests PASSED ***")

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
