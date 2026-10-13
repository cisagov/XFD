"""Load and validate the reviewed WAS host software manifest."""

# Standard Python Libraries
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, Tuple

DEFAULT_MANIFEST_PATH = (
    Path(__file__).resolve().parents[1] / "host-software-manifest.json"
)
PACKAGE_CHARACTERS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789+.-")


@dataclass(frozen=True)
class ToolSpec:
    """Describe one executable whose path and version must be inventoried."""

    name: str
    version_arguments: Tuple[str, ...]


@dataclass(frozen=True)
class HostSoftwareManifest:
    """Represent the reviewed, non-secret software state for a WAS host."""

    os_id: str
    os_version: str
    architecture: str
    docker_suite: str
    apt_packages: Tuple[str, ...]
    docker_packages: Tuple[str, ...]
    required_tools: Tuple[ToolSpec, ...]
    inventory_only_tools: Tuple[ToolSpec, ...]
    aws_cli_version: str
    aws_cli_archive: str
    aws_cli_url: str
    aws_cli_sha256: str
    uv_version: str
    uv_archive: str
    uv_url: str
    uv_sha256: str
    python_version: str
    manual_restore_items: Tuple[str, ...]


def require_mapping(value: Any, name: str) -> Dict[str, Any]:
    """Return a JSON object or reject an invalid manifest field."""
    if not isinstance(value, dict):
        raise ValueError("{} must be a JSON object.".format(name))
    return value


def require_string(value: Any, name: str) -> str:
    """Return a nonempty string or reject an invalid manifest field."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("{} must be a nonempty string.".format(name))
    return value


def require_string_list(value: Any, name: str) -> Tuple[str, ...]:
    """Return a unique list of nonempty strings from the manifest."""
    if not isinstance(value, list):
        raise ValueError("{} must be a JSON list.".format(name))
    items = tuple(require_string(item, "{} item".format(name)) for item in value)
    if len(items) != len(set(items)):
        raise ValueError("{} must not contain duplicates.".format(name))
    return items


def validate_package_names(packages: Tuple[str, ...], name: str) -> None:
    """Reject package names that cannot safely become APT arguments."""
    for package in packages:
        if not package[0].isalnum() or any(
            character not in PACKAGE_CHARACTERS for character in package
        ):
            raise ValueError("{} contains an invalid package name.".format(name))


def require_sha256(value: Any, name: str) -> str:
    """Return a lowercase SHA-256 digest or reject malformed input."""
    checksum = require_string(value, name)
    if len(checksum) != 64 or any(
        character not in "0123456789abcdef" for character in checksum
    ):
        raise ValueError("{} must be lowercase SHA-256.".format(name))
    return checksum


def load_tool_specs(value: Any, name: str) -> Tuple[ToolSpec, ...]:
    """Load unique executable names and their bounded version arguments."""
    if not isinstance(value, list):
        raise ValueError("{} must be a JSON list.".format(name))
    tools = []
    for item in value:
        mapping = require_mapping(item, "{} item".format(name))
        tool_name = require_string(mapping.get("name"), "{}.name".format(name))
        arguments = require_string_list(
            mapping.get("version_arguments"),
            "{}.version_arguments".format(name),
        )
        if not arguments:
            raise ValueError("{}.version_arguments must not be empty.".format(name))
        tools.append(ToolSpec(name=tool_name, version_arguments=arguments))
    if len(tools) != len({tool.name for tool in tools}):
        raise ValueError("{} must not contain duplicate tool names.".format(name))
    return tuple(tools)


def load_manifest(path: Path = DEFAULT_MANIFEST_PATH) -> HostSoftwareManifest:
    """Load the versioned manifest and fail closed on missing or invalid fields."""
    contents = json.loads(path.read_text(encoding="utf-8"))
    root = require_mapping(contents, "manifest")
    if root.get("schema_version") != 1:
        raise ValueError("Unsupported host software manifest schema version.")

    operating_system = require_mapping(root.get("operating_system"), "operating_system")
    managed_tools = require_mapping(root.get("managed_tools"), "managed_tools")
    aws_cli_settings = require_mapping(
        managed_tools.get("aws_cli"), "managed_tools.aws_cli"
    )
    uv_settings = require_mapping(managed_tools.get("uv"), "managed_tools.uv")
    python_settings = require_mapping(
        managed_tools.get("python"), "managed_tools.python"
    )
    apt_packages = require_string_list(root.get("apt_packages"), "apt_packages")
    docker_packages = require_string_list(
        root.get("docker_packages"), "docker_packages"
    )
    validate_package_names(apt_packages, "apt_packages")
    validate_package_names(docker_packages, "docker_packages")

    required_tools = load_tool_specs(root.get("required_tools"), "required_tools")
    inventory_only_tools = load_tool_specs(
        root.get("inventory_only_tools"), "inventory_only_tools"
    )
    required_names = {tool.name for tool in required_tools}
    inventory_names = {tool.name for tool in inventory_only_tools}
    if required_names.intersection(inventory_names):
        raise ValueError("Tool names cannot be both required and inventory-only.")

    aws_cli_sha256 = require_sha256(
        aws_cli_settings.get("sha256"), "managed_tools.aws_cli.sha256"
    )
    aws_cli_version = require_string(
        aws_cli_settings.get("version"), "managed_tools.aws_cli.version"
    )
    if not aws_cli_version.startswith("2."):
        raise ValueError("managed_tools.aws_cli.version must select AWS CLI v2.")
    expected_aws_cli_archive = "awscli-exe-linux-x86_64-{}.zip".format(aws_cli_version)
    aws_cli_archive = require_string(
        aws_cli_settings.get("archive"), "managed_tools.aws_cli.archive"
    )
    if aws_cli_archive != expected_aws_cli_archive:
        raise ValueError("managed_tools.aws_cli.archive must match its version.")
    aws_cli_url = require_string(
        aws_cli_settings.get("url"), "managed_tools.aws_cli.url"
    )
    expected_aws_cli_url = "https://awscli.amazonaws.com/{}".format(
        expected_aws_cli_archive
    )
    if aws_cli_url != expected_aws_cli_url:
        raise ValueError("managed_tools.aws_cli.url must use the versioned AWS URL.")
    uv_sha256 = require_sha256(uv_settings.get("sha256"), "managed_tools.uv.sha256")

    return HostSoftwareManifest(
        os_id=require_string(operating_system.get("id"), "operating_system.id"),
        os_version=require_string(
            operating_system.get("version_id"), "operating_system.version_id"
        ),
        architecture=require_string(
            operating_system.get("architecture"), "operating_system.architecture"
        ),
        docker_suite=require_string(
            operating_system.get("docker_suite"),
            "operating_system.docker_suite",
        ),
        apt_packages=apt_packages,
        docker_packages=docker_packages,
        required_tools=required_tools,
        inventory_only_tools=inventory_only_tools,
        aws_cli_version=aws_cli_version,
        aws_cli_archive=aws_cli_archive,
        aws_cli_url=aws_cli_url,
        aws_cli_sha256=aws_cli_sha256,
        uv_version=require_string(
            uv_settings.get("version"), "managed_tools.uv.version"
        ),
        uv_archive=require_string(
            uv_settings.get("archive"), "managed_tools.uv.archive"
        ),
        uv_url=require_string(uv_settings.get("url"), "managed_tools.uv.url"),
        uv_sha256=uv_sha256,
        python_version=require_string(
            python_settings.get("version"), "managed_tools.python.version"
        ),
        manual_restore_items=require_string_list(
            root.get("manual_restore_items"), "manual_restore_items"
        ),
    )
