"""
Terraform pre-commit helper.

───────────────────────────
* Removes duplicate blocks (resource / data / variable / …)
* Alphabetises & de-dupes quoted-string HCL lists
* Cleans heredoc JSON:
    – accepts IAM-style “relaxed JSON”  (comments, trailing commas,
      bare ${…} interpolations)
    – deduplicates & *always* alphabetises every `secrets` array
    – deduplicates & alphabetises plain string lists

Exit-code: 1 when a file is modified (good for pre-commit).
"""

from __future__ import annotations

# Standard Python Libraries
import json
from pathlib import Path
import re
import sys
from typing import Iterable

# ───────────────────────── Regex patterns ──────────────────────────
BLOCK_PATTERN = re.compile(
    r"^\s*(?P<block_type>resource|data|module|variable|output|provider)"
    r'\s+"(?P<label_primary>[^"]+)"'
    r'(?:\s+"(?P<label_secondary>[^"]+)")?',
    re.MULTILINE,
)

HCL_LIST_PATTERN = re.compile(
    r"^(?P<indent>[ \t]*)(?P<list_key>[\w\-]+)\s*=\s*\[\s*\n"
    r'(?P<list_body>(?:[ \t]*".*?",?\n)+)'
    r"(?P<close_indent>[ \t]*)\]\s*$",
    re.MULTILINE,
)

HEREDOC_JSON_PATTERN = re.compile(
    r"<<EOF\s*\n(?P<json_content>[\s\S]*?)\n[ \t]*EOF",
    re.MULTILINE,
)

# ─────────────── Relaxed-JSON → strict-JSON helpers ───────────────
_TRAILING_COMMA_PATTERN = re.compile(r",(\s*[}\]])")
_BARE_INTERPOLATION_PATTERN = re.compile(r"(?P<prefix>[:\[,]\s*)\${(?P<body>[^}\n]+)}")


def _quote_bare_interpolations(text: str) -> str:
    """
    Quote Terraform interpolations that appear bare inside a JSON object/array.

        : ${foo.bar}   →  : "${foo.bar}"
        , ${foo.bar}   →  , "${foo.bar}"
        [ ${foo.bar}   →  [ "${foo.bar}"
    """
    return _BARE_INTERPOLATION_PATTERN.sub(
        lambda match: f'{match.group("prefix")}"${{{match.group("body")}}}"',
        text,
    )


def _canonical_json(raw_json: str) -> str:
    """Strip comments, trailing commas, bare interpolations → strict JSON."""
    without_comments = re.sub(r"^\s*(//|#).*$", "", raw_json, flags=re.MULTILINE)
    with_quoted_interps = _quote_bare_interpolations(without_comments)
    without_trailing_commas = _TRAILING_COMMA_PATTERN.sub(r"\1", with_quoted_interps)
    return without_trailing_commas.strip()


# ───────────────────────── Block helpers ──────────────────────────
def find_duplicate_block_keys(file_text: str) -> list[tuple[str, str, str]]:
    """Find duplicate block keys in the given file text."""
    duplicates: list[tuple[str, str, str]] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for match in BLOCK_PATTERN.finditer(file_text):
        block_type = match.group("block_type")
        label_primary = match.group("label_primary")
        label_secondary = match.group("label_secondary") or ""

        # provider "aws" { alias = "foo" }
        if block_type == "provider" and not label_secondary:
            alias_search = file_text[match.end() :]
            alias_match = re.search(r'alias\s*=\s*"([^"]+)"', alias_search)
            if alias_match:
                label_secondary = alias_match.group(1)

        key = (block_type, label_primary, label_secondary)
        if key in seen_keys:
            duplicates.append(key)
        else:
            seen_keys.add(key)

    return duplicates


def remove_duplicate_blocks(file_text: str) -> str:
    """Remove duplicate blocks from the given file text."""
    lines = file_text.splitlines(keepends=True)
    kept_lines: list[str] = []
    seen_keys: set[tuple[str, str, str]] = set()

    index = 0
    while index < len(lines):
        current_line = lines[index]
        header_match = BLOCK_PATTERN.match(current_line)

        if header_match:
            block_type = header_match.group("block_type")
            label_primary = header_match.group("label_primary")
            label_secondary = header_match.group("label_secondary") or ""

            if block_type == "provider" and not label_secondary:
                depth = 0
                buffer: list[str] = []
                lookahead = index
                while lookahead < len(lines):
                    depth += lines[lookahead].count("{") - lines[lookahead].count("}")
                    buffer.append(lines[lookahead])
                    lookahead += 1
                    if depth <= 0:
                        break
                alias_match = re.search(r'alias\s*=\s*"([^"]+)"', "".join(buffer))
                if alias_match:
                    label_secondary = alias_match.group(1)

            key = (block_type, label_primary, label_secondary)
            if key in seen_keys:
                # Skip entire duplicate block
                depth = current_line.count("{") - current_line.count("}")
                index += 1
                while index < len(lines) and depth > 0:
                    depth += lines[index].count("{") - lines[index].count("}")
                    index += 1
                continue
            seen_keys.add(key)

        kept_lines.append(current_line)
        index += 1

    return "".join(kept_lines)


# ──────────────────────── HCL list helper ─────────────────────────
def sort_hcl_lists(file_text: str) -> str:
    """Return `file_text` with all HCL lists sorted and de-duped."""

    def _replace(match: re.Match[str]) -> str:
        """Replace matched HCL list with sorted version."""
        indent = match.group("indent")
        list_key = match.group("list_key")
        list_body = match.group("list_body")
        closing_indent = match.group("close_indent")

        items: list[tuple[str, str, str]] = []
        for body_line in list_body.splitlines():
            item_match = re.match(r'^([ \t]*)(".*?")(,?)', body_line)
            if item_match:
                items.append(
                    (item_match.group(1), item_match.group(2), item_match.group(3))
                )

        unique_items = {value: (prefix, comma) for prefix, value, comma in items}
        sorted_values = sorted(unique_items.keys(), key=lambda v: v.strip('"').lower())

        rebuilt_lines = [
            f"{unique_items[val][0]}{val}{unique_items[val][1]}"
            for val in sorted_values
        ]

        return (
            f"{indent}{list_key} = [\n"
            + "\n".join(rebuilt_lines)
            + f"\n{closing_indent}]"
        )

    return HCL_LIST_PATTERN.sub(_replace, file_text)


# ───────────────────────── JSON helpers ────────────────────────────
def _parse_json(fragment: str) -> object | None:
    """Parse a JSON fragment, returning None if it fails."""
    try:
        return json.loads(_canonical_json(fragment))
    except json.JSONDecodeError:
        return None


def _normalise_json(element: object) -> object:
    """
    Dedupe & alphabetise plain string lists.

    dedupe & alphabetise *every* `secrets` array by the secret `name`
    """

    def _clean(node: object) -> object:
        # Plain list of strings
        if isinstance(node, list) and all(isinstance(item, str) for item in node):
            return sorted(set(node), key=str.lower)

        # Dict – recurse into values, but treat `secrets` specially
        if isinstance(node, dict):
            cleaned: dict[str, object] = {}
            for key, value in node.items():
                if key == "secrets" and isinstance(value, list):
                    unique_map = {
                        secret["name"]: secret
                        for secret in value
                        if isinstance(secret, dict) and "name" in secret
                    }
                    cleaned[key] = [
                        unique_map[name]
                        for name in sorted(unique_map.keys(), key=str.lower)
                    ]
                else:
                    cleaned[key] = _clean(value)
            return cleaned

        # Generic list – recurse
        if isinstance(node, list):
            return [_clean(item) for item in node]

        return node  # Primitive

    return _clean(element)


def clean_json_heredoc_blocks(file_text: str) -> str:
    """Return `file_text` with every JSON heredoc normalised."""

    def _replace(match: re.Match[str]) -> str:
        raw_json = match.group("json_content")
        parsed = _parse_json(raw_json)
        if parsed is None:
            return match.group(0)  # leave untouched if still not parseable
        cleaned = _normalise_json(parsed)
        return f"<<EOF\n{json.dumps(cleaned, indent=2)}\nEOF"

    return HEREDOC_JSON_PATTERN.sub(_replace, file_text)


# ────────────────────────── Top-level driver ───────────────────────
def process_terraform_file(path: Path) -> bool:
    """Return True when no changes were made; False when file rewritten."""
    original_text = path.read_text()

    current_text = original_text

    # 1. Block duplicates
    duplicate_keys = find_duplicate_block_keys(current_text)
    if duplicate_keys:
        print(f"Removing {len(duplicate_keys)} duplicate blocks in {path} …")
        current_text = remove_duplicate_blocks(current_text)

    # 2. Sort HCL lists
    current_text = sort_hcl_lists(current_text)
    print(f"✔️  Sorted HCL lists in {path}")

    # 3. Normalise *all* JSON heredocs (idempotent)
    before_json_cleanup = current_text
    current_text = clean_json_heredoc_blocks(current_text)
    if current_text != before_json_cleanup:
        print(f"✔️  Normalised JSON heredocs in {path}")

    # 4. Write back if changed
    if current_text != original_text:
        path.write_text(current_text)
        print(f"✔️  Applied all changes to {path}")
        return False
    return True


def main(arguments: Iterable[str]) -> None:
    """
    Pre-commit entry-point.

    Parameters
    ----------
    arguments : Iterable[str]
        The file paths that pre-commit passes to the hook—each should point
        to a Terraform (*.tf*) file to be analysed and potentially rewritten.

    Behaviour
    ---------
    For each path:
    1. Skips and warns if the file is missing.
    2. Calls :pyfunc:`process_terraform_file`, which rewrites the file when
       duplicates, unsorted lists, or unsanitised JSON heredocs are found.
    3. Tracks whether any file changed:
       * exits **1** if at least one file was modified
       * exits **0** when everything is already clean.

    This exit-code contract lets the hook fail in CI when formatting fixes
    are required, mirroring tools like ``terraform fmt -check``.
    """
    exit_code = 0
    for filename in arguments:
        file_path = Path(filename)
        if not file_path.exists():
            print(f"⚠️  Skipping missing file: {file_path}")
            continue
        if not process_terraform_file(file_path):
            exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main(sys.argv[1:])
