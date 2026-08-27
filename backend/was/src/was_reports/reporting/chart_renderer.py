"""Render legacy-compatible WAS chart images from calculated metrics."""

# Standard Python Libraries
from dataclasses import dataclass
from datetime import datetime
from math import pi
from pathlib import Path
from typing import Dict, List

# Third-Party Libraries
import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.ticker import FormatStrFormatter  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

# First-Party Libraries
from was_reports.reporting.report_metrics import (  # noqa: E402
    FindingMetrics,
    GROUP_LABELS,
    OWASP_LABELS,
    fixed_percentage,
)

OWASP_GRAPH_FILENAME = "owasp_graph.png"
GROUP_GRAPH_FILENAME = "figure3.png"
DONUT_FILENAME = "donut.png"
HISTOGRAM_FILENAME = "histogram.png"
MONTHLY_FILENAME = "monthly.png"


@dataclass(frozen=True)
class ChartArtifacts:
    """Paths to chart images consumed by the legacy report template."""

    owasp_graph: Path
    group_graph: Path
    donut: Path
    histogram: Path
    monthly: Path


def render_owasp_graph(owasp_counts: Dict[str, int], output_path: Path) -> Path:
    """Render the horizontal OWASP category chart."""
    labels = [""] + list(OWASP_LABELS.values())
    values = [0] + [owasp_counts.get(label, 0) for label in OWASP_LABELS.values()]
    positions = np.arange(len(labels))
    figure, axis = plt.subplots()
    axis.barh(positions, values, align="center", color="#005288")
    axis.set_xlabel("Number of Vulnerabilities")
    axis.set_title("Number of Vulnerabilities by OWASP Category")
    axis.set_yticks(positions)
    axis.set_yticklabels(labels)
    figure.subplots_adjust(left=0.5)
    figure.savefig(output_path)
    plt.close(figure)
    return output_path


def percentage_values(values: List[int]) -> List[float]:
    """Return percentage values for the legacy group pie chart."""
    total = sum(values)
    if total == 0:
        return [0.0 for value in values]
    return [value / total * 100 for value in values]


def render_group_graph(group_counts: Dict[str, int], output_path: Path) -> Path:
    """Render the vulnerabilities-by-group pie chart."""
    labels = list(GROUP_LABELS.values())
    values = [group_counts.get(label, 0) for label in labels]
    percentages = percentage_values(values)
    colors = ["#001726", "#003e67", "#d6e9f2", "#7ab9d5", "#7aa5c1", "#0078ae"]
    figure, axis = plt.subplots()
    try:
        axis.pie(
            values,
            shadow=False,
            startangle=90,
            colors=colors,
            labeldistance=1.05,
        )
        axis.axis("equal")
    except ValueError:
        pass
    legend_labels = [
        "{}, {:.1f} %".format(label, percentage)
        for label, percentage in zip(labels, percentages)
    ]
    axis.legend(
        bbox_to_anchor=(-0.15, 0.25),
        loc="upper left",
        labels=legend_labels,
    )
    figure.savefig(output_path)
    plt.close(figure)
    return output_path


def render_fixed_donut(
    fixed_count: int,
    total_count: int,
    output_path: Path,
) -> Path:
    """Render the fixed-vulnerability percentage donut chart."""
    percent = fixed_percentage(fixed_count, total_count)
    figure = plt.figure(figsize=(6, 6))
    axis = figure.add_subplot(projection="polar")
    axis.set_facecolor("#e5eede")
    data = [100, percent]
    start_angle = 90
    colors = ["#c0c2c4", "#5e9732"]
    widths = [(value * pi * 2) / 100 for value in data]
    positions = [3.1, 3.1]
    left = (start_angle * pi * 2) / 360
    for index, width in enumerate(widths):
        axis.barh(
            positions[index],
            width,
            left=left,
            height=2,
            color=colors[index],
        )
        if index == 1:
            axis.scatter(
                width + left,
                positions[index],
                s=1650,
                color=colors[index],
                zorder=2,
            )
    axis.set_ylim(-4, 4)
    axis.text(
        0.5,
        0.5,
        "{}%".format(percent),
        transform=axis.transAxes,
        horizontalalignment="center",
        verticalalignment="center",
        fontsize=36,
    )
    axis.set_xticks([])
    axis.set_yticks([])
    axis.spines.clear()
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)
    return output_path


def render_age_histogram(
    ages: List[int],
    severities: List[str],
    output_path: Path,
) -> Path:
    """Render vulnerability age and severity distribution bars."""
    figure = plt.figure(figsize=(7, 5))
    axis = figure.add_subplot(1, 1, 1)
    data_frame = pd.DataFrame(
        {
            "age": np.array(ages),
            "Severity": np.array(severities),
        }
    )
    if not ages or not severities:
        sns.histplot(data=data_frame, ax=axis)
    else:
        sns.histplot(
            data=data_frame,
            ax=axis,
            stat="count",
            multiple="stack",
            x="age",
            bins="auto",
            kde=False,
            palette=["#eebdc5", "#e08493", "#d24b62", "#c41230", "#950e24"],
            hue="Severity",
            hue_order=["1", "2", "3", "4", "5"],
            element="bars",
            alpha=None,
            legend=True,
        )
    axis.set_title("Vulnerability Distribution by Age and Severity")
    axis.set_xlabel("Age (Days)")
    axis.set_ylabel(None)
    axis.xaxis.set_major_formatter(FormatStrFormatter("%d"))
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)
    return output_path


def format_month_year(month_year: str) -> str:
    """Return the legacy numeric month and two-digit year label."""
    month_date = datetime.strptime(month_year, "%B %Y")
    return "{}/{}".format(month_date.month, month_date.strftime("%y"))


def render_monthly_trend(
    fixed_monthly: Dict[str, int],
    vulnerabilities_monthly: Dict[str, int],
    output_path: Path,
) -> Path:
    """Render the legacy oldest-to-newest monthly stacked-area chart."""
    months = list(reversed(fixed_monthly.keys()))
    fixed_values = [fixed_monthly[month] for month in months]
    vulnerability_values = [vulnerabilities_monthly[month] for month in months]
    figure, axis = plt.subplots(figsize=(7.5, 2))
    axis.stackplot(
        months,
        fixed_values,
        vulnerability_values,
        colors=["#bfeca9", "#7ab9d5"],
        labels=["Fixed Vulnerabilities", "Total Vulnerabilities"],
        alpha=None,
    )
    axis.set_xticks(months)
    axis.set_xticklabels(
        [format_month_year(month) for month in months],
        rotation=30,
    )
    axis.legend(loc=2)
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)
    return output_path


def render_report_charts(
    finding_metrics: FindingMetrics,
    ages: List[int],
    severities: List[str],
    asset_directory: Path,
) -> ChartArtifacts:
    """Render every active chart image consumed by the WAS template."""
    asset_directory.mkdir(parents=True, exist_ok=True)
    return ChartArtifacts(
        owasp_graph=render_owasp_graph(
            finding_metrics.owasp_counts,
            asset_directory / OWASP_GRAPH_FILENAME,
        ),
        group_graph=render_group_graph(
            finding_metrics.group_counts,
            asset_directory / GROUP_GRAPH_FILENAME,
        ),
        donut=render_fixed_donut(
            finding_metrics.fixed_count,
            finding_metrics.total_count,
            asset_directory / DONUT_FILENAME,
        ),
        histogram=render_age_histogram(
            ages,
            severities,
            asset_directory / HISTOGRAM_FILENAME,
        ),
        monthly=render_monthly_trend(
            finding_metrics.fixed_monthly,
            finding_metrics.vulnerabilities_monthly,
            asset_directory / MONTHLY_FILENAME,
        ),
    )
