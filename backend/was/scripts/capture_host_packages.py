#!/usr/bin/env python3
"""Capture Ubuntu packages and user-local tools before rebuilding the host.

Compatible with Ubuntu 20.04's Python 3.8. No third-party packages are required.
Run as the normal operator, not through sudo, to include that user's tools.
This inventories the host, not packages inside Docker images or project virtualenvs.
"""

# Standard Python Libraries
import argparse
import csv
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess  # nosec B404
import sys
from typing import Dict, List, Optional, TextIO, cast


def run_command(
    arguments: List[str], environment: Optional[Dict[str, str]] = None
) -> str:
    """Run a bounded read-only inventory command without a shell."""
    result = subprocess.run(  # nosec B603
        arguments,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
        env=environment,
    )
    return result.stdout


def write_output(message: str) -> None:
    """Write one user-facing line to standard output."""
    sys.stdout.write("{}\n".format(message))
    sys.stdout.flush()


def open_history(path: Path) -> TextIO:
    """Open one plain-text or compressed package history file."""
    if path.suffix == ".gz":
        return cast(
            TextIO,
            gzip.open(path, "rt", encoding="utf-8", errors="replace"),
        )
    return path.open("rt", encoding="utf-8", errors="replace")


def installed_packages(output: str) -> List[Dict[str, str]]:
    """Parse dpkg-query output, excluding removed and partially installed rows."""
    packages = []
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) == 4 and fields[3] == "installed":
            packages.append(
                dict(package=fields[0], version=fields[1], architecture=fields[2])
            )
    return sorted(packages, key=lambda package: package["package"])


def read_history(
    log_directory: Path, since: Optional[str], warnings: List[str]
) -> List[Dict[str, str]]:
    """Extract package events, not command lines that might contain credentials."""
    events = []
    paths = sorted(log_directory.glob("dpkg.log*"))
    if not paths:
        warnings.append("No retained dpkg logs were found.")
    for path in paths:
        if not path.is_file():
            continue
        try:
            with open_history(path) as history:
                for line in history:
                    fields = line.split()
                    if len(fields) != 6 or fields[2] not in (
                        "install",
                        "upgrade",
                        "remove",
                        "purge",
                        "downgrade",
                    ):
                        continue
                    if since and fields[0] < since:
                        continue
                    events.append(
                        dict(
                            timestamp=" ".join(fields[:2]),
                            action=fields[2],
                            package=fields[3],
                            old_version=fields[4],
                            new_version=fields[5],
                            source=path.name,
                        )
                    )
        except (OSError, EOFError) as error:
            warnings.append(
                "Could not fully read {} ({}).".format(path, type(error).__name__)
            )
    return sorted(events, key=lambda event: (event["timestamp"], event["package"]))


def write_csv(path: Path, fields: List[str], rows: List[Dict[str, str]]) -> None:
    """Write a UTF-8 inventory with explicit columns."""
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def tool_directories(home: Path) -> List[Path]:
    """Find common user tool locations even when absent from the active PATH."""
    directories = [
        home / ".local/bin",
        home / "bin",
        home / ".cargo/bin",
        Path("/usr/local/bin"),
        Path("/usr/local/sbin"),
    ]
    directories.extend(sorted((home / ".nvm/versions/node").glob("*/bin")))
    directories.extend(Path(value) for value in os.get_exec_path() if value)
    return list(dict.fromkeys(directories))


def package_owner(path: Path) -> str:
    """Return exact dpkg ownership evidence, never infer the installer used."""
    try:
        result = run_command(["dpkg-query", "-S", str(path)])
    except subprocess.CalledProcessError:
        return ""
    owners = []
    for line in result.splitlines():
        owner, separator, owned_path = line.rpartition(": ")
        if separator and owned_path == str(path):
            owners.append(owner)
    return "; ".join(owners)


def capture_tools(output: Path, warnings: List[str]) -> List[Dict[str, str]]:
    """Record versions, resolved paths, and ownership for each detected tool."""
    rows = []
    for name in ("uv", "npm", "node", "docker", "python3", "git", "curl", "jq", "aws"):
        seen = set()
        for directory in tool_directories(Path.home()):
            path = directory / name
            if not path.is_file() or not os.access(path, os.X_OK):
                continue
            executable = str(path.absolute())
            if executable in seen:
                continue
            seen.add(executable)
            try:
                resolved = path.resolve(strict=True)
                environment = os.environ.copy()
                environment["PATH"] = (
                    str(directory) + os.pathsep + os.environ.get("PATH", "")
                )
                version = run_command([executable, "--version"], environment).strip()
                owner = package_owner(path.absolute()) or package_owner(resolved)
            except (subprocess.SubprocessError, OSError, RuntimeError) as error:
                version, owner, resolved = "unavailable", "", path
                warnings.append(
                    "Incomplete tool evidence for {} ({}).".format(
                        path, type(error).__name__
                    )
                )
            rows.append(
                dict(
                    tool=name,
                    executable=executable,
                    resolved_path=str(resolved),
                    version=version,
                    dpkg_owner=owner,
                    installation_source="dpkg-owned; original installer unknown"
                    if owner
                    else "unknown",
                )
            )
    write_csv(
        output / "host-tools.csv",
        [
            "tool",
            "executable",
            "resolved_path",
            "version",
            "dpkg_owner",
            "installation_source",
        ],
        rows,
    )
    if not any(row["tool"] == "uv" for row in rows):
        warnings.append(
            "uv was not found on PATH or in the searched user-local tool directories."
        )
    return rows


def capture_managed_tools(
    output: Path, tools: List[Dict[str, str]], warnings: List[str]
) -> None:
    """Collect offline uv and npm inventories without saving package sources or tokens."""
    npm_rows = []
    seen = set()
    for index, tool in enumerate(tools, start=1):
        identity = (tool["tool"], tool["resolved_path"])
        if identity in seen or tool["tool"] not in ("uv", "npm"):
            continue
        seen.add(identity)
        executable = tool["executable"]
        environment = os.environ.copy()
        environment["PATH"] = (
            str(Path(executable).parent) + os.pathsep + os.environ.get("PATH", "")
        )
        environment.update(
            {
                "UV_OFFLINE": "true",
                "NO_COLOR": "1",
                "NPM_CONFIG_UPDATE_NOTIFIER": "false",
            }
        )
        if tool["tool"] == "uv":
            for label, arguments in (
                ("tools", ["tool", "list"]),
                ("python", ["python", "list", "--only-installed"]),
            ):
                destination = output / "uv-{}-{}.txt".format(label, index)
                try:
                    contents = run_command([executable] + arguments, environment)
                    destination.write_text(
                        "Executable: {}\n{}".format(executable, contents),
                        encoding="utf-8",
                    )
                except (subprocess.SubprocessError, OSError) as error:
                    warnings.append(
                        "uv {} inventory failed ({}).".format(
                            label, type(error).__name__
                        )
                    )
        else:
            try:
                arguments = [
                    executable,
                    "--offline",
                    "list",
                    "--global",
                    "--depth=0",
                    "--json",
                    "--ignore-scripts",
                ]
                try:
                    raw = run_command(arguments, environment)
                except subprocess.CalledProcessError as error:
                    raw = error.stdout or ""
                    warnings.append(
                        "npm returned a nonzero status; its package list may be incomplete."
                    )
                result = json.loads(raw)
                for name, details in result.get("dependencies", {}).items():
                    npm_rows.append(
                        dict(
                            npm_executable=executable,
                            package=name,
                            version=str(details.get("version", "unknown")),
                        )
                    )
            except (
                subprocess.SubprocessError,
                OSError,
                ValueError,
                AttributeError,
            ) as error:
                warnings.append(
                    "npm inventory failed ({}).".format(type(error).__name__)
                )
    write_csv(
        output / "npm-global-packages.csv",
        ["npm_executable", "package", "version"],
        npm_rows,
    )


def capture_backup_manifest(output: Path, warnings: List[str]) -> None:
    """List rebuild inputs without copying scripts or configurations containing secrets."""
    home = Path.home()
    paths = [
        home / name for name in (".bashrc", ".profile", ".bash_profile", ".nvm/nvm.sh")
    ]
    for directory in (
        home / "bin",
        home / ".local/bin",
        Path("/usr/local/bin"),
        Path("/usr/local/sbin"),
    ):
        if directory.is_dir():
            try:
                paths.extend(directory.iterdir())
            except OSError:
                warnings.append(
                    "Unable to list {} for backup planning.".format(directory)
                )
    for directory in (
        Path("/etc/systemd/system"),
        home / ".config/systemd/user",
        Path("/etc/cron.d"),
    ):
        if directory.is_dir():
            for root, directories, filenames in os.walk(
                directory,
                followlinks=False,
                onerror=lambda error: warnings.append(
                    "Service backup listing incomplete ({}).".format(
                        type(error).__name__
                    )
                ),
            ):
                paths.extend(Path(root) / name for name in filenames)
    rows = []
    for path in sorted(set(paths)):
        if not path.is_file() and not path.is_symlink():
            continue
        try:
            metadata = path.lstat()
            rows.append(
                dict(
                    path=str(path),
                    symlink_target=os.readlink(path) if path.is_symlink() else "",
                    mode=oct(metadata.st_mode & 0o777),
                    size_bytes=str(metadata.st_size),
                )
            )
        except OSError:
            warnings.append("Unable to inventory {}.".format(path))
    write_csv(
        output / "backup-manifest.csv",
        ["path", "symlink_target", "mode", "size_bytes"],
        rows,
    )
    (output / "REBUILD-NOTES.txt").write_text(
        "This directory is evidence, NOT a full backup or a restore script.\n"
        "1. Review APT/Snap packages for Ubuntu 24.04 compatibility.\n"
        "2. Review host-tools.csv, npm-global-packages.csv, and uv-*.txt.\n"
        "3. Unknown installation sources require investigation, not guessed install commands.\n"
        "4. Securely back up custom scripts and required configurations listed in backup-manifest.csv.\n"
        "   Only file metadata was collected. Review symlink targets separately.\n"
        "5. Separately preserve application data, cron jobs, service enablement, repositories,\n"
        "   dependency lockfiles, mounts, certificates, and authorized secret sources.\n"
        "   These are NOT included in this inventory. Do not copy secrets into this directory.\n"
        "6. Run as each relevant operator to capture their user-local tools.\n"
        "7. Copy this inventory off the old EC2 before teardown, then verify the rebuilt host.\n",
        encoding="utf-8",
    )


def baseline_additions(
    current: List[Dict[str, str]], baseline: Path
) -> List[Dict[str, str]]:
    """Compare current packages to an inventory from the original AMI."""
    with baseline.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or not {"package", "architecture"}.issubset(
            reader.fieldnames
        ):
            raise ValueError("Baseline must be an installed-packages.csv inventory.")
        original = {(row["package"], row["architecture"]) for row in reader}
    return [
        row for row in current if (row["package"], row["architecture"]) not in original
    ]


def capture(output: Path, since: Optional[str], baseline: Optional[Path]) -> None:
    """Write package evidence and limitations without accessing application secrets."""
    for executable in ("dpkg-query", "apt-mark"):
        if not shutil.which(executable):
            raise RuntimeError("Run this on the Ubuntu EC2 host, not in Docker.")
    os.umask(0o077)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    warnings: List[str] = []
    tools = capture_tools(output, warnings)
    capture_managed_tools(output, tools, warnings)
    capture_backup_manifest(output, warnings)
    package_fields = ["package", "version", "architecture"]
    packages = installed_packages(
        run_command(
            [
                "dpkg-query",
                "-W",
                "-f=${binary:Package}\t${Version}\t${Architecture}\t${db:Status-Status}\n",
            ]
        )
    )
    write_csv(output / "installed-packages.csv", package_fields, packages)
    manual = sorted(run_command(["apt-mark", "showmanual"]).splitlines())
    (output / "apt-manual-packages.txt").write_text(
        "\n".join(manual) + "\n", encoding="utf-8"
    )
    (output / "apt-held-packages.txt").write_text(
        run_command(["apt-mark", "showhold"]), encoding="utf-8"
    )
    events = read_history(Path("/var/log"), since, warnings)
    event_fields = [
        "timestamp",
        "action",
        "package",
        "old_version",
        "new_version",
        "source",
    ]
    write_csv(output / "package-history.csv", event_fields, events)
    installs = [event for event in events if event["action"] == "install"]
    write_csv(output / "observed-installations.csv", event_fields, installs)
    if baseline:
        write_csv(
            output / "added-since-baseline.csv",
            package_fields,
            baseline_additions(packages, baseline),
        )
    else:
        warnings.append(
            "No original AMI inventory supplied: post-launch additions cannot "
            "be conclusively distinguished from packages baked into the AMI."
        )
    if shutil.which("snap"):
        try:
            (output / "snap-packages.txt").write_text(
                run_command(["snap", "list"]), encoding="utf-8"
            )
        except (subprocess.SubprocessError, OSError) as error:
            warnings.append(
                "Snap inventory unavailable ({}).".format(type(error).__name__)
            )
    report = {
        "inventory_version": 2,
        "operator": pwd.getpwuid(os.getuid()).pw_name,
        "operator_home": str(Path.home()),
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "os_release": Path("/etc/os-release").read_text(encoding="utf-8"),
        "history_since_inclusive": since,
        "installed_package_count": len(packages),
        "retained_event_count": len(events),
        "observed_installation_count": len(installs),
        "detected_uv_paths": [
            tool["executable"] for tool in tools if tool["tool"] == "uv"
        ],
        "warnings": warnings,
        "limitations": [
            "Rotated or deleted logs can omit installations. Dates use the host log timezone.",
            "History without --since may include AMI-build events, not just this instance.",
            "Install events can include packages that were subsequently removed.",
            "APT manual marking is not proof that an operator installed a package.",
            "Project virtualenv dependencies, arbitrary source installs, and container contents are not inventoried.",
            "Tool discovery covers PATH and selected user-local directories, not every location or user.",
            "Executable versions and dpkg ownership do not prove installation dates or installer commands.",
            "npm globals and uv tools/Python lists reflect the detected runtimes and current user's configuration.",
            "backup-manifest.csv contains metadata only; no script or service file contents were backed up.",
            "No .env, AWS credentials, shell history, or raw APT command lines are collected.",
            "This is an inventory, not a restore script; review package compatibility on Ubuntu 24.04.",
        ],
    }
    (output / "summary.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    write_output("Inventory saved to {}".format(output.resolve()))
    write_output("uv evidence is in host-tools.csv and summary.json.")
    for tool in tools:
        if tool["tool"] == "uv":
            write_output(
                "Detected uv: {} ({})".format(
                    tool["executable"],
                    tool["version"],
                )
            )
    for warning in warnings:
        write_output("WARNING: {}".format(warning))


def main() -> int:
    """Accept an optional launch-date filter and original AMI inventory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version="WAS host inventory 2")
    parser.add_argument(
        "--output",
        type=Path,
        help="New output directory; never overwrite an existing one.",
    )
    parser.add_argument(
        "--since", help="Inclusive YYYY-MM-DD launch-date filter for retained logs."
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="installed-packages.csv captured from the original AMI.",
    )
    args = parser.parse_args()
    if os.environ.get("SUDO_USER"):
        parser.error(
            "Run as your normal EC2 user, without sudo, to capture that user's tools."
        )
    if args.since:
        try:
            parsed_date = datetime.strptime(args.since, "%Y-%m-%d")
            if parsed_date.strftime("%Y-%m-%d") != args.since:
                raise ValueError()
        except ValueError:
            parser.error("--since must be YYYY-MM-DD.")
    output = args.output or Path.home() / datetime.now(timezone.utc).strftime(
        "was-host-inventory-%Y%m%dT%H%M%SZ"
    )
    try:
        capture(output, args.since, args.baseline)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        write_output(
            "Inventory incomplete ({}). Check prerequisites and output directory.".format(
                type(error).__name__
            )
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
