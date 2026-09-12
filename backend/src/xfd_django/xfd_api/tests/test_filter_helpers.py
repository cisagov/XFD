"""Unit tests for organization search filter construction."""

# Third-Party Libraries
from django.db.models import Q
import pytest
from xfd_api.helpers.filter_helpers import apply_organization_filters


@pytest.mark.parametrize(
    "region_id,expected",
    [
        (1, [1]),
        ("2", [2]),
        ([1], [1]),
        ([1, 2], [1, 2]),
        (["1", "2"], [1, 2]),
        ([1, "2", None, ""], [1, 2]),
        ([None, ""], []),
        ("invalid", [-1]),
        (["invalid"], [-1]),
        ([1, "invalid"], [-1]),
    ],
)
def test_organization_region_filters(region_id, expected):
    """Scalar and list selections must constrain regions, including invalid IDs."""
    result = apply_organization_filters(Q(), {"region_id": region_id})
    assert result == Q(retired=False) & Q(region_id__in=expected)


@pytest.mark.parametrize(
    "filters", [{}, {"region_id": None}, {"region_id": ""}, {"region_id": []}]
)
def test_empty_region_filters(filters):
    """Missing or empty selections keep the active-organization filter."""
    assert apply_organization_filters(Q(), filters) == Q(retired=False)


def test_region_list_preserves_other_filters():
    """Region selections must combine with existing membership and other filters."""
    base_q = Q(id__in=["member-organization"])
    filters = {
        "region_id": [1, "2"],
        "state": ["va"],
        "name": " Agency ",
        "acronym": " TEST ",
    }
    result = apply_organization_filters(base_q, filters)
    assert result == (
        Q(id__in=["member-organization"])
        & Q(retired=False)
        & Q(acronym__icontains="TEST")
        & Q(name__icontains="Agency")
        & Q(state__in=["VA"])
        & Q(region_id__in=[1, 2])
    )
    assert base_q == Q(id__in=["member-organization"])
    assert filters["region_id"] == [1, "2"]
