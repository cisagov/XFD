"""Setup for the PE worker Python package."""

# Standard Python Libraries
from pathlib import Path

# Third-Party Libraries
from setuptools import find_packages, setup

ROOT = Path(__file__).parent

setup(
  name="pe_worker",
  version="0.1.0",
  description="Posture & Exposure worker (dnstwist scan + in-container API)",
  package_dir={"": "src"},
  packages=find_packages(where="src"),
  package_data={
    "pe_source": ["data/*.dict", "data/pe_db/*"],
  },
  include_package_data=True,
  install_requires=[
    line.strip()
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.startswith("#")
  ],
  entry_points={
    "console_scripts": [
      "pe-source=pe_source.pe_scripts:main",
    ],
  },
  python_requires=">=3.10",
)
