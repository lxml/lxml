"""
Streamed ultra-minimal patch applier.

Assumptions:
- git-style headers '--- a/...' and '+++ b/...' (or '/dev/null' for adds).
- Hunks contain contiguous blocks of '-' lines followed by '+' lines (no context, nointerleaving).
- No deletions/renames of files; additions allowed where src is /dev/null.
- Every modified file exists and has the expected lines to be removed.
- Reads the patch line-by-line and applies each file as parsed.
"""

import os
import pathlib
from typing import List, Tuple, Optional


def _parse_patch_file_path(file_path: str) -> Optional[str]:
    if file_path == "/dev/null":
        return None
    return file_path[2:] if file_path.startswith(("a/", "b/")) else file_path


def _write_file(path: pathlib.Path, lines_without_linebreaks):
    path.parent.mkdir(exist_ok=True)
    with path.open(mode="w", encoding="utf-8", newline="\n") as f:
        for line in lines_without_linebreaks:
            f.write(line + "\n")


def _parse_hunk_header(hdr: str) -> Tuple[int, int, int, int]:
    """
    Parse a unified diff hunk header like:
      @@ -old_start,old_count +new_start,new_count @@ optional
    where the counts may be omitted (meaning 1).

    Returns (old_start, old_count, new_start, new_count).
    """
    parts = hdr.split()
    old = parts[1]  # like -12,3 or -12
    new = parts[2]  # like +12,4 or +12
    def pr(r: str) -> Tuple[int, int]:
        r = r[1:]
        if ',' in r:
            a, b = r.split(',', 1)
            return int(a), int(b)
        return int(r), 1
    old_s, old_c = pr(old)
    new_s, new_c = pr(new)
    return old_s, old_c, new_s, new_c


def _write_new_file(file_path: pathlib.Path, body_lines):
    lines = [ln[1:] for ln in body_lines if ln and ln[0] == "+"]
    _write_file(file_path, lines)
    return


def _apply_hunk(source_path: pathlib.Path, target_path: pathlib.Path, body_lines: List[str]) -> None:
    """
    Parse and apply a single patch section.

    - body_lines: lines between the +++ header and the next --- header (raw diff lines).
    """
    # Modification: apply contiguous delete-blocks then insert-blocks
    with open(source_path, "r", encoding="utf-8", newline="") as f:
        orig = f.read().splitlines()

    result_lines: List[str] = []
    orig_idx = 0  # 0-based index into orig

    # process hunk by hunk
    patch_lines = iter(body_lines)
    for line in patch_lines:
        if not line.startswith('@@ '):
            continue
        # parse hunk header
        old_start, old_count, _, new_count = _parse_hunk_header(line)
        # append unchanged lines before this hunk (old_start is 1-based)
        before = old_start - 1 - orig_idx
        if before > 0:
            result_lines.extend(orig[orig_idx: orig_idx + before])
            orig_idx += before

        # now process hunk body: consume exactly old_count deletions ('-') and new_count additions ('+')
        deleted = 0
        added = 0

        # first consume body lines until we've seen old_count deletions and new_count additions
        # but we process sequentially and append additions immediately
        while deleted < old_count or added < new_count:
            line = next(patch_lines)
            if not line or line[0] not in '+-':
                continue
            if line[0] == '-':
                if deleted < old_count:
                    # consume one original line (drop it)
                    assert line[1:] == orig[orig_idx], f"Deleted line mismatches: {line[1:]!r} != {orig[orig_idx]!r}"
                    orig_idx += 1
                    deleted += 1
            else:
                if added < new_count:
                    result_lines.append(line[1:])
                    added += 1

    # append remainder of original
    if orig_idx < len(orig):
        result_lines.extend(orig[orig_idx:])

    _write_file(target_path, result_lines)


def apply_patch(lines, root: str = ".") -> None:
    root_path = pathlib.Path(root)
    it = iter(lines)

    for line in it:
        if not line.startswith("--- "):
            continue
        source = _parse_patch_file_path(line[4:-1])
        line = next(it)
        assert line.startswith('+++ '), line
        target = _parse_patch_file_path(line[4:-1])

        # collect body for this file until next '--- ' or EOF
        body: List[str] = []
        for line in it:
            if not line or line[0] not in '+-@ ':
                break
            body.append(line.rstrip('\n'))

        if body:
            if source:
                print(f"Patching file {target}")
                _apply_hunk(root_path / source, root_path / target, body)
            else:
                print(f"Creating file {target}")
                _write_new_file(root_path / target, body)


def apply_patch_file(patch_file: str, root: str = ".") -> None:
    with open(patch_file) as f:
        patch_lines = f.readlines()
    apply_patch(patch_lines, root)
