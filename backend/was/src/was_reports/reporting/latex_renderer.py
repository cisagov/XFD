"""Render and compile the legacy Mustache and LaTeX WAS report."""

# Standard Python Libraries
import html
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

# Third-Party Libraries
import pystache

LATEX_ESCAPE_MAP = {
    "$": r"\$",
    "%": r"\%",
    "&": r"\&",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "[": "{[}",
    "]": "{]}",
    "<": "\\textless{}",
    ">": "\\textgreater{}",
}
LATEX_TEMPORARY_EXTENSIONS = (".log", ".toc", ".atfi", ".out", ".aux")


@dataclass(frozen=True)
class LatexRenderResult:
    """Paths created by the legacy-compatible LaTeX renderer."""

    tex_path: Path
    pdf_path: Path


def escape_latex(value: object) -> str:
    """Escape the character set handled by the legacy report generator."""
    escaped_value = str(value)
    for latex_character, replacement in LATEX_ESCAPE_MAP.items():
        escaped_value = escaped_value.replace(latex_character, replacement)
    return escaped_value


def organization_name_width(organization_name: str) -> str:
    """Return the legacy title width for an escaped organization name."""
    name_length = len(organization_name)
    if name_length >= 55:
        return "18cm"
    if name_length >= 45:
        return "16cm"
    if name_length >= 40:
        return "13cm"
    if name_length >= 35:
        return "12cm"
    if name_length >= 25:
        return "10cm"
    if name_length >= 14:
        return "8.5cm"
    return "6cm"


def validate_filename_component(value: str) -> str:
    """Reject values that could write a report outside its working directory."""
    if not value or value in (".", ".."):
        raise ValueError("Report filename component cannot be empty or relative.")
    if "/" in value or "\\" in value or "\x00" in value:
        raise ValueError("Report filename component contains an unsafe character.")
    return value


def render_latex_template(
    template_path: Path,
    template_data: Mapping[str, object],
    stakeholder_tag: str,
    working_directory: Path,
    report_date: Optional[date] = None,
) -> Path:
    """Render the legacy Mustache template to a dated LaTeX source file."""
    if not template_path.is_file():
        raise FileNotFoundError(
            "WAS Mustache template not found at {}.".format(template_path)
        )
    safe_tag = validate_filename_component(stakeholder_tag)
    resolved_report_date = report_date or date.today()
    tex_filename = "{}_report_{}.tex".format(
        safe_tag,
        resolved_report_date.isoformat(),
    )
    working_directory.mkdir(parents=True, exist_ok=True)
    template_text = template_path.read_text(encoding="utf-8")
    rendered_text = pystache.render(template_text, dict(template_data))
    rendered_text = html.unescape(rendered_text)
    tex_path = working_directory / tex_filename
    tex_path.write_text(rendered_text, encoding="utf-8")
    return tex_path


def compile_latex_pdf(
    tex_path: Path,
    output_directory: Path,
    command_runner: Callable = subprocess.run,
    xelatex_executable: str = "xelatex",
) -> Path:
    """Compile LaTeX twice and return the expected PDF output path."""
    if not tex_path.is_file():
        raise FileNotFoundError(
            "WAS LaTeX source not found at {}.".format(tex_path)
        )
    output_directory.mkdir(parents=True, exist_ok=True)
    command: Sequence[str] = (
        xelatex_executable,
        "-output-directory={}".format(output_directory),
        tex_path.name,
    )
    for unused_pass_number in range(2):
        command_runner(
            command,
            cwd=tex_path.parent,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    pdf_path = output_directory / "{}.pdf".format(tex_path.stem)
    if not pdf_path.is_file():
        raise FileNotFoundError(
            "XeLaTeX completed without creating {}.".format(pdf_path)
        )
    return pdf_path


def cleanup_latex_files(tex_path: Path, output_directory: Path) -> None:
    """Delete only temporary files created for one LaTeX report."""
    for extension in LATEX_TEMPORARY_EXTENSIONS:
        temporary_path = output_directory / "{}{}".format(
            tex_path.stem,
            extension,
        )
        temporary_path.unlink(missing_ok=True)
    tex_path.unlink(missing_ok=True)


def render_report_pdf(
    template_path: Path,
    template_data: Mapping[str, object],
    stakeholder_tag: str,
    working_directory: Path,
    output_directory: Path,
    report_date: Optional[date] = None,
    command_runner: Callable = subprocess.run,
    xelatex_executable: str = "xelatex",
    remove_temporary_files: bool = True,
) -> LatexRenderResult:
    """Render and compile one report using the preserved legacy template."""
    tex_path = render_latex_template(
        template_path=template_path,
        template_data=template_data,
        stakeholder_tag=stakeholder_tag,
        working_directory=working_directory,
        report_date=report_date,
    )
    pdf_path = compile_latex_pdf(
        tex_path=tex_path,
        output_directory=output_directory,
        command_runner=command_runner,
        xelatex_executable=xelatex_executable,
    )
    result = LatexRenderResult(tex_path=tex_path, pdf_path=pdf_path)
    if remove_temporary_files:
        cleanup_latex_files(tex_path, output_directory)
    return result
