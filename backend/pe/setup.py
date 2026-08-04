"""Setup for the PE worker Python package."""

# Standard Python Libraries
from pathlib import Path

# Third-Party Libraries
from setuptools import find_packages, setup

ROOT = Path(__file__).parent


def load_requirements(path: Path) -> list[str]:
    """Read a requirements file, expanding ``-r`` includes."""
    requirements: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r "):
            included = path.parent / line[3:].strip()
            requirements.extend(load_requirements(included))
            continue
        requirements.append(line)
    return requirements


setup(
    name="pe_worker",
    version="0.1.0",
    description="Posture & Exposure worker (dnstwist scan + in-container API)",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    package_data={
        "pe_source": ["dnstwist/*.dict"],
        "pe_reports": [
            "assets/*",
            "assets_asm/*",
            "fonts/*",
        ],
    },
    include_package_data=True,
    install_requires=load_requirements(ROOT / "requirements.txt"),
    extras_require={
        "test": ["httpx2"],
    },
    entry_points={
        "console_scripts": [
            "pe-source=pe_source.pe_scripts:main",
            "pe-reports=pe_reports.report_generator:main",
        ],
    },
    python_requires=">=3.10",
)
