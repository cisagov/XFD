#!/usr/bin/env python3
"""Preview or restore the reviewed WAS host software on Ubuntu 24.04 x86-64.

The committed host-software-manifest.json is the reviewed software source of
truth. Its initial package set was derived from the September 4, 2026 host
inventory; every replacement must capture and review fresh evidence.

Default: print the plan without running commands or writing files.
--apply --acknowledge-manual-items: install missing reviewed packages and tools.
--verify: read-only software checks. Exit 0 means the declared software passed;
exit 1 means a failure or mismatch. Manual restore items remain a separate gate.
Run as the normal EC2 operator, not root or via sudo. Privileged package steps
use sudo individually. No tests, reports, email, or application jobs are run.

Sources:
https://docs.docker.com/engine/install/ubuntu/
https://docs.aws.amazon.com/cli/latest/userguide/getting-started-version.html
https://github.com/astral-sh/uv/releases/tag/0.12.8
https://docs.astral.sh/uv/guides/install-python/
"""

# Standard Python Libraries
import argparse
import grp
import hashlib
import os
from pathlib import Path, PurePosixPath
import platform
import pwd
import shlex
import shutil
import stat
import subprocess  # nosec B404
import sys
import tarfile
from tempfile import TemporaryDirectory
from typing import List, Tuple
import zipfile

# Third-Party Libraries
# Local scripts
from host_software_manifest import PACKAGE_CHARACTERS, load_manifest

SOFTWARE_MANIFEST = load_manifest()
APT_PACKAGES = SOFTWARE_MANIFEST.apt_packages
DOCKER_PACKAGES = SOFTWARE_MANIFEST.docker_packages
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
UV_VERSION = SOFTWARE_MANIFEST.uv_version
PYTHON_VERSION = SOFTWARE_MANIFEST.python_version
UV_ARCHIVE = SOFTWARE_MANIFEST.uv_archive
UV_URL = SOFTWARE_MANIFEST.uv_url
UV_SHA256 = SOFTWARE_MANIFEST.uv_sha256
AWS_CLI_VERSION = SOFTWARE_MANIFEST.aws_cli_version
AWS_CLI_ARCHIVE = SOFTWARE_MANIFEST.aws_cli_archive
AWS_CLI_URL = SOFTWARE_MANIFEST.aws_cli_url
AWS_CLI_SHA256 = SOFTWARE_MANIFEST.aws_cli_sha256
DOCKER_KEY_URL = "https://download.docker.com/linux/ubuntu/gpg"
DOCKER_REPOSITORY_URL = "https://download.docker.com/linux/ubuntu"
DOCKER_SOURCE = (
    "Types: deb\nURIs: https://download.docker.com/linux/ubuntu\n"
    "Suites: {}\nComponents: stable\nArchitectures: amd64\n"
    "Signed-By: /etc/apt/keyrings/was-docker.asc\n".format(
        SOFTWARE_MANIFEST.docker_suite
    )
)
MANUAL_ITEMS = SOFTWARE_MANIFEST.manual_restore_items


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
    if (
        values.get("ID") != SOFTWARE_MANIFEST.os_id
        or values.get("VERSION_ID") != SOFTWARE_MANIFEST.os_version
    ):
        raise RuntimeError(
            "Installation and verification require Ubuntu {}.".format(
                SOFTWARE_MANIFEST.os_version
            )
        )
    if platform.machine() not in ("x86_64", "amd64"):
        raise RuntimeError("This inventory and pinned uv binary require x86-64.")
    if os.geteuid() == 0 or os.environ.get("SUDO_USER"):
        raise RuntimeError("Run as the normal EC2 operator, without sudo.")


def show_plan(extra_packages: List[str]) -> None:
    """Separate automatically restorable software from unknown or missing data."""
    write_output(
        "WAS Ubuntu {} host rebuild from the reviewed software manifest".format(
            SOFTWARE_MANIFEST.os_version
        )
    )
    write_output("APT: {}".format(", ".join(APT_PACKAGES + tuple(extra_packages))))
    write_output(
        "Docker official {} repository: {}".format(
            SOFTWARE_MANIFEST.docker_suite, ", ".join(DOCKER_PACKAGES)
        )
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
        "AWS CLI: pinned v{} system installation, SHA256-verified from {}.".format(
            AWS_CLI_VERSION, AWS_CLI_URL
        )
    )
    write_output(
        "No Node/npm installation: none was detected; npm globals and uv tool lists were empty."
    )
    write_output(
        "Docker access: add the current operator to the root-equivalent docker group when needed."
    )
    write_output(
        "No package removals, distro upgrades, unrelated service restores, or reboots."
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


def file_sha256(path: Path) -> str:
    """Return a streaming SHA-256 digest for a downloaded artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while True:
            block = source.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def extract_zip_archive(archive_path: Path, destination: Path) -> None:
    """Extract a bounded ZIP archive without links or directory traversal."""
    total_size = 0
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        if len(members) > 50_000:
            raise RuntimeError("AWS CLI archive contains too many members.")
        for archive_member in members:
            relative_path = PurePosixPath(archive_member.filename)
            if (
                not relative_path.parts
                or relative_path.is_absolute()
                or ".." in relative_path.parts
            ):
                raise RuntimeError("AWS CLI archive contains an unsafe path.")
            member_mode = archive_member.external_attr >> 16
            if stat.S_ISLNK(member_mode):
                raise RuntimeError("AWS CLI archive contains an unexpected symlink.")
            total_size += archive_member.file_size
            if total_size > 1_500_000_000:
                raise RuntimeError("AWS CLI archive is unexpectedly large.")
            target = destination.joinpath(*relative_path.parts)
            if archive_member.is_dir():
                target.mkdir(mode=0o755, parents=True, exist_ok=True)
                continue
            target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            with archive.open(archive_member) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
            permissions = member_mode & 0o777
            if permissions:
                target.chmod(permissions)


def parse_aws_cli_version(output: str) -> str:
    """Return the version from the stable first field of `aws --version`."""
    fields = output.strip().split()
    prefix = "aws-cli/"
    if not fields or not fields[0].startswith(prefix):
        return ""
    return fields[0][len(prefix) :]


def installed_aws_cli_version() -> str:
    """Return the installed AWS CLI version, or an empty string when absent."""
    try:
        result = command(["aws", "--version"], check=False)
    except OSError:
        return ""
    if result.returncode:
        return ""
    return parse_aws_cli_version(result.stdout or result.stderr)


def install_aws_cli() -> None:
    """Install the checksum-pinned AWS CLI v2 without trusting an APT package."""
    current_version = installed_aws_cli_version()
    if current_version == AWS_CLI_VERSION:
        write_output("AWS CLI {} is already installed.".format(AWS_CLI_VERSION))
        return

    binary_path = Path("/usr/local/bin/aws")
    install_root = Path("/usr/local/aws-cli")
    update_existing = binary_path.exists() or install_root.exists()
    if update_existing:
        if not binary_path.is_symlink() or not install_root.is_dir():
            raise RuntimeError(
                "Existing AWS CLI paths differ from the managed system installation."
            )
        resolved_binary = binary_path.resolve(strict=True)
        if install_root not in resolved_binary.parents:
            raise RuntimeError(
                "Existing AWS CLI symlink is outside the managed installation."
            )

    with TemporaryDirectory(prefix="was-aws-cli-download-") as directory:
        download_root = Path(directory)
        archive_path = download_root / AWS_CLI_ARCHIVE
        fetch(AWS_CLI_URL, archive_path)
        if file_sha256(archive_path) != AWS_CLI_SHA256:
            raise RuntimeError(
                "AWS CLI archive checksum mismatch; installation stopped."
            )
        extract_root = download_root / "extracted"
        extract_root.mkdir(mode=0o700)
        extract_zip_archive(archive_path, extract_root)
        installer = extract_root / "aws/install"
        if not installer.is_file() or installer.is_symlink():
            raise RuntimeError(
                "AWS CLI archive does not contain the expected installer."
            )
        arguments = [
            "sudo",
            str(installer),
            "--install-dir",
            str(install_root),
            "--bin-dir",
            str(binary_path.parent),
        ]
        if update_existing:
            arguments.append("--update")
        command(arguments)

    if installed_aws_cli_version() != AWS_CLI_VERSION:
        raise RuntimeError("AWS CLI version verification failed after installation.")


def operator_identity() -> Tuple[str, int]:
    """Return the normal operator name and primary group from the current UID."""
    operator = pwd.getpwuid(os.getuid())
    return operator.pw_name, operator.pw_gid


def docker_group_membership(operator_name: str, primary_group_id: int) -> bool:
    """Return whether account configuration grants the operator Docker access."""
    try:
        docker_group = grp.getgrnam("docker")
    except KeyError:
        return False
    return (
        docker_group.gr_gid == primary_group_id or operator_name in docker_group.gr_mem
    )


def grant_docker_operator_access() -> bool:
    """Grant the current operator root-equivalent Docker daemon access if needed."""
    operator_name, primary_group_id = operator_identity()
    if docker_group_membership(operator_name, primary_group_id):
        write_output("Docker group access is already configured for the operator.")
        return False
    try:
        grp.getgrnam("docker")
    except KeyError as error:
        raise RuntimeError(
            "Docker installation did not create the docker group."
        ) from error
    write_output(
        "SECURITY: docker group membership grants root-equivalent host access."
    )
    command(
        [
            "sudo",
            "usermod",
            "--append",
            "--groups",
            "docker",
            operator_name,
        ]
    )
    if not docker_group_membership(operator_name, primary_group_id):
        raise RuntimeError("Docker group membership was not recorded for the operator.")
    return True


def docker_access_failures() -> List[str]:
    """Return configuration and live-session Docker access failures."""
    failures = []
    operator_name, primary_group_id = operator_identity()
    if not docker_group_membership(operator_name, primary_group_id):
        failures.append(
            "The operator is not configured for root-equivalent docker group access."
        )
    try:
        result = command(["docker", "info", "--format", "{{.ServerVersion}}"])
        write_output(result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        failures.append(
            "The current operator session cannot access the Docker daemon without sudo."
        )
    return failures


def docker_source_is_compatible(contents: str) -> bool:
    """Recognize Docker's signed repository for the manifest OS suite."""
    lines = [
        line.strip()
        for line in contents.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    for line in lines:
        fields = line.split()
        if fields and fields[0] == "deb" and DOCKER_REPOSITORY_URL in fields:
            return (
                SOFTWARE_MANIFEST.docker_suite in fields
                and "stable" in fields
                and any("arch=amd64" in field for field in fields)
                and any(field.startswith("signed-by=") for field in fields)
            )

    values = {}
    for line in lines:
        name, separator, value = line.partition(":")
        if separator:
            values[name.lower()] = value.split()
    architectures = values.get("architectures", [])
    return (
        DOCKER_REPOSITORY_URL in values.get("uris", [])
        and SOFTWARE_MANIFEST.docker_suite in values.get("suites", [])
        and "stable" in values.get("components", [])
        and (not architectures or "amd64" in architectures)
        and bool(values.get("signed-by"))
    )


def docker_repository() -> None:
    """Add or accept the signed manifest source without overwriting configuration."""
    source_path = Path("/etc/apt/sources.list.d/was-docker.sources")
    key_path = Path("/etc/apt/keyrings/was-docker.asc")
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

    other_sources = [Path("/etc/apt/sources.list")]
    other_sources += list(Path("/etc/apt/sources.list.d").glob("*.list"))
    other_sources += list(Path("/etc/apt/sources.list.d").glob("*.sources"))
    compatible_sources = []
    for path in other_sources:
        if path == source_path or not path.is_file():
            continue
        contents = path.read_text()
        if DOCKER_REPOSITORY_URL not in contents:
            continue
        if not docker_source_is_compatible(contents):
            raise RuntimeError(
                "An existing Docker source is not the signed Ubuntu {} stable repository.".format(
                    SOFTWARE_MANIFEST.docker_suite
                )
            )
        compatible_sources.append(path)
    if compatible_sources:
        write_output(
            "Using existing signed Docker {} repository: {}".format(
                SOFTWARE_MANIFEST.docker_suite, compatible_sources[0]
            )
        )
        return
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
        if file_sha256(archive_path) != UV_SHA256:
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
    try:
        result = command(["aws", "--version"])
        aws_cli_output = (result.stdout or result.stderr).strip()
        write_output(aws_cli_output)
        if parse_aws_cli_version(aws_cli_output) != AWS_CLI_VERSION:
            failures.append("AWS CLI version differs from the manifest.")
    except (OSError, subprocess.SubprocessError):
        failures.append("AWS CLI is unavailable.")
    for tool in SOFTWARE_MANIFEST.required_tools:
        if tool.name in ("aws", "uv"):
            continue
        arguments = [tool.name] + list(tool.version_arguments)
        try:
            result = command(arguments)
            write_output((result.stdout or result.stderr).strip())
        except (OSError, subprocess.SubprocessError):
            failures.append("Unavailable tool: {}".format(" ".join(arguments)))
    try:
        result = command(["docker", "compose", "version"])
        write_output((result.stdout or result.stderr).strip())
    except (OSError, subprocess.SubprocessError):
        failures.append("Unavailable tool: docker compose")
    failures.extend(docker_access_failures())
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
        "Declared software checks passed. Manual rebuild items remain UNVERIFIED."
    )
    return 0


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
        help="Additional operator-reviewed Ubuntu {} package names.".format(
            SOFTWARE_MANIFEST.os_version
        ),
    )
    args = parser.parse_args()
    for package in args.extra_apt:
        if (
            not package
            or not package[0].isalnum()
            or any(character not in PACKAGE_CHARACTERS for character in package)
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
        docker_membership_changed = grant_docker_operator_access()
        install_aws_cli()
        install_uv()
        command(
            [str(Path.home() / ".local/bin/uv"), "python", "install", PYTHON_VERSION]
        )
        if docker_membership_changed:
            write_output(
                "Installation completed. End this login session, reconnect, and run "
                "make host-software-verify so docker group access takes effect."
            )
            return 0
        return verify(packages)
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        tarfile.TarError,
        zipfile.BadZipFile,
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
