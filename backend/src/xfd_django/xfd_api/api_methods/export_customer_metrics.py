"""Utility to export CustomerMetrics rows as CSV."""
# Standard Python Libraries
from datetime import timedelta
from typing import Iterable, List, Optional, Sequence, Tuple

# Third-Party Libraries
from django.core.exceptions import FieldDoesNotExist
from django.db.models import DateField, DateTimeField, Field
from django.utils import timezone
from xfd_api.utils import csv_utils
from xfd_mini_dl.models import CustomerMetrics

EXCLUDED_FIELDS: tuple[str, ...] = ("id", "created_at")


def export_customer_metrics(
    fieldnames: Optional[Sequence[str]] = None,
    date_field_candidates: Iterable[str] = ("metrics_date", "date", "as_of_date"),
) -> Tuple[str, bytes]:
    """Export CustomerMetrics rows for yesterday as a CSV."""
    yesterday = (timezone.now() - timedelta(days=1)).date()

    date_field_name, date_field = _resolve_date_field(
        CustomerMetrics, date_field_candidates
    )

    if isinstance(date_field, DateField) and not isinstance(date_field, DateTimeField):
        qs = CustomerMetrics.objects.filter(**{date_field_name: yesterday})
    else:
        qs = CustomerMetrics.objects.filter(
            **{"{}__date".format(date_field_name): yesterday}
        )

    if fieldnames is None:
        fieldnames = _default_fieldnames(CustomerMetrics)
    fieldnames = [f for f in fieldnames if f not in EXCLUDED_FIELDS]

    csv_text = csv_utils.queryset_to_csv(qs, fieldnames, sanitize=True, newline="")

    filename = "cyhy_dashboard_customer_metrics_{}.csv".format(yesterday.isoformat())
    return filename, csv_text.encode("utf-8")


def _resolve_date_field(model, candidates: Iterable[str]) -> Tuple[str, Field]:
    """
    Pick the first existing field from candidates and return (name, field).

    Raises ValueError if none found.
    """
    for name in candidates:
        try:
            field = model._meta.get_field(name)
            return name, field
        except FieldDoesNotExist:
            continue
    raise ValueError(
        "None of the date field candidates {} exist on {}.".format(
            list(candidates), model.__name__
        )
    )


def _default_fieldnames(model) -> List[str]:
    """Use all concrete, non-relation fields in model-defined order (excludes M2M and reverse relations)."""
    names: List[str] = []
    for f in model._meta.get_fields():
        if (
            getattr(f, "concrete", False)
            and not getattr(f, "many_to_many", False)
            and not getattr(f, "one_to_many", False)
        ):
            names.append(f.name)
    return names
