#!/usr/bin/env python3
"""Preview or restore the reviewed WAS host software on Ubuntu 24.04 x86-64.

Tailored to was-host-inventory-20260904T123202Z.tar.gz, SHA256:
e59fbb9bbfb55fd11ce04960ffdaedd43718c4bbe64d82c7f22ed50bb93f0088

Default: print the plan without running commands or writing files.
--apply --acknowledge-manual-items: install missing reviewed packages and tools.
--verify: read-only software checks. Exit 2 means software passed but manual
backup/restore items still require review; exit 1 means a failure or mismatch.
Run as the normal EC2 operator, not root or via sudo. Privileged package steps
use sudo individually. No tests, reports, email, or application jobs are run.

Sources:
https://docs.docker.com/engine/install/ubuntu/
https://github.com/astral-sh/uv/releases/tag/0.12.8
https://docs.astral.sh/uv/guides/install-python/
"""

# Standard Python Libraries
import argparse
import hashlib
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess  # nosec B404
import sys
import tarfile
from tempfile import TemporaryDirectory
from typing import List

APT_PACKAGES = (
    "awscli",
    "ca-certificates",
    "cron",
    "curl",
    "figlet",
    "git",
    "gnupg",
    "imagemagick",
    "make",
    "openssh-client",
    "rsync",
    "screen",
    "tar",
    "wget",
)
DOCKER_PACKAGES = (
    "containerd.io",
    "docker-buildx-plugin",
    "docker-ce",
    "docker-ce-cli",
    "docker-ce-rootless-extras",
    "docker-compose-plugin",
)
DOCKER_CONFLICTS = (
    "docker.io",
    "docker-compose",
    "docker-compose-v2",
    "docker-doc",
    "docker-buildx",
    "podman-docker",
    "containerd",
    "runc",
)
UV_VERSION = "0.12.8"
PYTHON_VERSION = "3.12.14"
UV_ARCHIVE = "uv-x86_64-unknown-linux-gnu.tar.gz"
UV_URL = "https://releases.astral.sh/github/uv/releases/download/{}/{}".format(
    UV_VERSION, UV_ARCHIVE
)
UV_SHA256 = "2e2b37e9811e17675a9e70bed5e1a58fc8c0388be63d751d72cc735188c149ff"
DOCKER_KEY_URL = "https://download.docker.com/linux/ubuntu/gpg"
DOCKER_SOURCE = (
    "Types: deb\nURIs: https://download.docker.com/linux/ubuntu\n"
    "Suites: noble\nComponents: stable\nArchitectures: amd64\n"
    "Signed-By: /etc/apt/keyrings/was-docker.asc\n"
)
MANUAL_ITEMS = (
    "Back up and restore ~/bin/getcloneBranch and ~/bin/updateWAS; contents are absent from the inventory.",
    'Review/restore ~/.bashrc and ~/.profile; export PATH="$HOME/.local/bin:$HOME/bin:$PATH" if appropriate.',
    "Reclone the application repository and rebuild its Docker image from source.",
    "Recreate project virtualenvs from dependency files if needed; installed virtualenv dependencies were not captured.",
    "Restore .env/secrets through approved secure sources, not from this inventory.",
    "Verify IAM instance profile, S3/SES access, database connectivity, firewall rules, mounts, and certificates.",
    "Review cron jobs and service definitions; metadata alone cannot restore their contents or enablement.",
    "LXD 4.0.13 was present. Decide whether it is needed and select an approved supported channel; it is NOT installed here.",
    "SSM and Snap base/runtime packages belong to the new AMI; this script checks SSM but does not replace or restart it.",
    "Review omitted Ubuntu base packages/libraries and any additional tool dependencies against the inventory.",
)


def write_output(message: str) -> None:
    """Write one user-facing line to standard output."""
    sys.stdout.write("{}\n".format(message))
    sys.stdout.flush()


def command(arguments: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a bounded command without shell interpolation or inherited virtualenv tools."""
    write_output("$ {}".format(shlex.join(arguments)))
    environment = os.environ.copy()
    environment["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    environment["LC_ALL"] = "C"
    environment["UV_PYTHON_INSTALL_DIR"] = str(Path.home() / ".local/share/uv/python")
    return subprocess.run(  # nosec B603
        arguments,
        check=check,
        text=True,
        capture_output=True,
        timeout=1800,
        env=environment,
    )


def installed(package: str) -> bool:
    """Check installed status, not residual dpkg configuration records."""
    result = command(
        ["dpkg-query", "-W", "-f=${db:Status-Status}", package], check=False
    )
    return result.returncode == 0 and result.stdout.strip() == "installed"


def check_host() -> None:
    """Refuse old/unsupported hosts and root-owned user-local installations."""
    values = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        name, separator, value = line.partition("=")
        if separator:
            values[name] = value.strip('"')
    if values.get("ID") != "ubuntu" or values.get("VERSION_ID") != "24.04":
        raise RuntimeError("Installation and verification require Ubuntu 24.04.")
    if platform.machine() not in ("x86_64", "amd64"):
        raise RuntimeError("This inventory and pinned uv binary require x86-64.")
    if os.geteuid() == 0 or os.environ.get("SUDO_USER"):
        raise RuntimeError("Run as the normal EC2 operator, without sudo.")


def show_plan(extra_packages: List[str]) -> None:
    """Separate automatically restorable software from unknown or missing data."""
    write_output("WAS Ubuntu 24.04 host rebuild, based on the 2026-09-04 inventory")
    write_output("APT: {}".format(", ".join(APT_PACKAGES + tuple(extra_packages))))
    write_output(
        "Docker official noble repository: {}".format(", ".join(DOCKER_PACKAGES))
    )
    write_output(
        "APT/Docker: install missing packages at configured repository candidates, not old focal versions."
    )
    write_output(
        "uv: {} in ~/.local/bin, SHA256-verified download from {}".format(
            UV_VERSION, UV_URL
        )
    )
    write_output(
        "Python: uv-managed {}, without replacing /usr/bin/python3.".format(
            PYTHON_VERSION
        )
    )
    write_output(
        "AWS CLI: use Ubuntu 24.04's awscli package; validate scripts against the resulting version."
    )
    write_output(
        "No Node/npm installation: none was detected; npm globals and uv tool lists were empty."
    )
    write_output(
        "No package removals, distro upgrades, docker-group changes, service restores, or reboots."
    )
    write_output("MANUAL ITEMS (not restored or verified by this script):")
    for item in MANUAL_ITEMS:
        write_output("  - {}".format(item))


def fetch(url: str, destination: Path) -> None:
    """Download over verified HTTPS with bounded retries and no TLS bypass."""
    command(
        [
            "curl",
            "--fail",
            "--location",
            "--proto",
            "=https",
            "--proto-redir",
            "=https",
            "--tlsv1.2",
            "--retry",
            "3",
            "--connect-timeout",
            "20",
            "--max-time",
            "300",
            "--output",
            str(destination),
            url,
        ]
    )


def install_apt(packages: List[str]) -> None:
    """Install only missing packages after a no-removal dependency simulation."""
    missing = [package for package in packages if not installed(package)]
    if not missing:
        write_output("All selected packages are already installed.")
        return
    simulation = command(["apt-get", "--simulate", "--no-remove", "install"] + missing)
    write_output(simulation.stdout)
    command(["sudo", "apt-get", "--yes", "--no-remove", "install"] + missing)


def docker_repository() -> None:
    """Add only this script's scoped noble source, never overwrite existing sources."""
    source_path = Path("/etc/apt/sources.list.d/was-docker.sources")
    key_path = Path("/etc/apt/keyrings/was-docker.asc")
    other_sources = [Path("/etc/apt/sources.list")]
    other_sources += list(Path("/etc/apt/sources.list.d").glob("*.list"))
    other_sources += list(Path("/etc/apt/sources.list.d").glob("*.sources"))
    for path in other_sources:
        if path == source_path or not path.is_file():
            continue
        if "download.docker.com" in path.read_text():
            raise RuntimeError(
                "An existing Docker source needs review. Configure its noble packages manually, then rerun."
            )
    if source_path.is_symlink() or key_path.is_symlink():
        raise RuntimeError("Refusing symlinked Docker repository configuration.")
    if source_path.exists():
        if source_path.read_text() != DOCKER_SOURCE or not key_path.is_file():
            raise RuntimeError(
                "Existing Docker repository configuration differs from this script."
            )
        return
    if key_path.exists():
        raise RuntimeError(
            "A Docker key already exists without this script's source; review before retrying."
        )
    with TemporaryDirectory(prefix="was-docker-repository-") as directory:
        root = Path(directory)
        key = root / "docker.asc"
        fetch(DOCKER_KEY_URL, key)
        source = root / "docker.sources"
        source.write_text(DOCKER_SOURCE)
        command(["sudo", "install", "-d", "-m", "0755", "/etc/apt/keyrings"])
        command(["sudo", "install", "-m", "0644", str(key), str(key_path)])
        command(["sudo", "install", "-m", "0644", str(source), str(source_path)])


def install_uv() -> None:
    """Install only checksum-verified uv/uvx members, without running an installer."""
    destination = Path.home() / ".local/bin"
    uv_path = destination / "uv"
    if uv_path.exists():
        version = command([str(uv_path), "--version"]).stdout.split()
        if len(version) < 2 or version[1] != UV_VERSION:
            raise RuntimeError(
                "An existing uv version differs; it will not be overwritten."
            )
        if not (destination / "uvx").is_file():
            raise RuntimeError(
                "uv exists but uvx is missing; repair explicitly before retrying."
            )
        write_output("uv {} is already installed.".format(UV_VERSION))
        return
    if (
        uv_path.is_symlink()
        or (destination / "uvx").exists()
        or (destination / "uvx").is_symlink()
    ):
        raise RuntimeError(
            "Existing uv/uvx paths require review; no files were overwritten."
        )
    with TemporaryDirectory(prefix="was-uv-download-") as directory:
        archive_path = Path(directory) / UV_ARCHIVE
        fetch(UV_URL, archive_path)
        if hashlib.sha256(archive_path.read_bytes()).hexdigest() != UV_SHA256:
            raise RuntimeError("uv archive checksum mismatch; installation stopped.")
        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive_path, "r:gz") as archive:
            for name in ("uv", "uvx"):
                member = archive.getmember(
                    "uv-x86_64-unknown-linux-gnu/{}".format(name)
                )
                if not member.isfile() or member.size > 150_000_000:
                    raise RuntimeError("Unexpected uv archive member.")
                source = archive.extractfile(member)
                if source is None:
                    raise RuntimeError("Unable to read uv archive member.")
                with source, (destination / name).open("xb") as target:
                    shutil.copyfileobj(source, target)
                (destination / name).chmod(0o755)


def verify(packages: List[str]) -> int:
    """Report software checks without claiming missing backups were restored."""
    failures = []
    for package in packages + list(DOCKER_PACKAGES):
        if not installed(package):
            failures.append("Missing package: {}".format(package))
    uv_path = Path.home() / ".local/bin/uv"
    try:
        result = command([str(uv_path), "--version"]).stdout.strip()
        write_output(result)
        if len(result.split()) < 2 or result.split()[1] != UV_VERSION:
            failures.append("uv version differs from the inventory.")
        result = command(
            [
                str(uv_path),
                "--offline",
                "python",
                "find",
                "--managed-python",
                PYTHON_VERSION,
            ]
        )
        python_path = Path(result.stdout.strip())
        version = command([str(python_path), "--version"]).stdout.strip()
        write_output(version)
        if version != "Python {}".format(PYTHON_VERSION):
            failures.append("Managed Python version mismatch.")
    except (OSError, subprocess.SubprocessError):
        failures.append("uv or its required managed Python is unavailable.")
    for arguments in (
        ["docker", "--version"],
        ["docker", "compose", "version"],
        ["aws", "--version"],
    ):
        try:
            result = command(arguments)
            write_output((result.stdout or result.stderr).strip())
        except (OSError, subprocess.SubprocessError):
            failures.append("Unavailable tool: {}".format(" ".join(arguments)))
    if command(["systemctl", "is-active", "docker"], check=False).returncode:
        failures.append(
            "Docker service is not active; inspect it before starting workloads."
        )
    ssm_services = ("amazon-ssm-agent", "snap.amazon-ssm-agent.amazon-ssm-agent")
    if not any(
        command(["systemctl", "is-active", service], check=False).returncode == 0
        for service in ssm_services
    ):
        failures.append(
            "SSM Agent is not active; verify AMI bootstrap and access before proceeding."
        )
    for failure in failures:
        write_output("FAIL: {}".format(failure))
    if failures:
        return 1
    write_output(
        "Software checks passed. Manual rebuild items remain UNVERIFIED (exit 2)."
    )
    return 2


def main() -> int:
    """Require explicit approval for writes and leave unrelated host state alone."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    parser.add_argument("--acknowledge-manual-items", action="store_true")
    parser.add_argument(
        "--extra-apt",
        nargs="*",
        default=[],
        help="Additional operator-reviewed Ubuntu 24.04 package names.",
    )
    args = parser.parse_args()
    for package in args.extra_apt:
        if (
            not package
            or not package[0].isalnum()
            or any(
                character not in "abcdefghijklmnopqrstuvwxyz0123456789+.-"
                for character in package
            )
        ):
            parser.error("Invalid extra APT package name.")
    show_plan(args.extra_apt)
    if not args.apply and not args.verify:
        write_output("PREVIEW ONLY: no commands executed and no files changed.")
        return 0
    if args.apply and not args.acknowledge_manual_items:
        parser.error(
            "Review the plan and add --acknowledge-manual-items before applying."
        )
    try:
        check_host()
        packages = list(dict.fromkeys(APT_PACKAGES + tuple(args.extra_apt)))
        if args.verify:
            return verify(packages)
        conflicts = [package for package in DOCKER_CONFLICTS if installed(package)]
        if conflicts:
            raise RuntimeError(
                "Conflicting Docker packages require manual review: {}".format(
                    ", ".join(conflicts)
                )
            )
        command(["sudo", "-v"])
        command(["sudo", "apt-get", "update"])
        install_apt(packages)
        if not all(installed(package) for package in DOCKER_PACKAGES):
            docker_repository()
            command(["sudo", "apt-get", "update"])
            install_apt(list(DOCKER_PACKAGES))
        install_uv()
        command(
            [str(Path.home() / ".local/bin/uv"), "python", "install", PYTHON_VERSION]
        )
        return verify(packages)
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        tarfile.TarError,
        subprocess.SubprocessError,
    ) as error:
        if isinstance(error, RuntimeError):
            write_output("STOPPED: {}".format(error))
        else:
            write_output(
                "STOPPED ({}). Review the last command; no automatic rollback was attempted.".format(
                    type(error).__name__
                )
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
