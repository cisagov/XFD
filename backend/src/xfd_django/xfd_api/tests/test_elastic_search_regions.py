"""Regression tests for region filters in Elasticsearch domain searches."""

# Standard Python Libraries
import unittest

# Third-Party Libraries
from xfd_api.helpers.elastic_search import (
    build_request,
    build_request_filter,
    get_term_filter,
)
from xfd_api.schema_models.search import DomainSearchBody


class TestRegionFilters(unittest.TestCase):
    """Keep region conjunctions valid without changing union or access filters."""

    def test_all_uses_scalar_term_queries(self):
        """Each conjunct must be a term query, not a terms query with a scalar."""
        for values in ([1], [1, 2], [1, 1], ["1", "2"]):
            with self.subTest(values=values):
                result = get_term_filter(
                    {"field": "organization.region_id", "type": "all", "values": values}
                )
                self.assertEqual(
                    result,
                    {
                        "bool": {
                            "filter": [
                                {"term": {"organization.region_id": value}}
                                for value in values
                            ]
                        }
                    },
                )

    def test_any_keeps_one_terms_query(self):
        """Union selections still pass the complete array to a terms query."""
        for values in ([1], [1, 2], ["1", "2"]):
            with self.subTest(values=values):
                result = get_term_filter(
                    {"field": "organization.region_id", "type": "any", "values": values}
                )
                self.assertEqual(
                    result,
                    {
                        "bool": {
                            "should": [{"terms": {"organization.region_id": values}}],
                            "minimum_should_match": 1,
                        }
                    },
                )

    def test_empty_all_is_unchanged(self):
        """An empty conjunction retains the existing no-op representation."""
        self.assertEqual(
            get_term_filter(
                {"field": "organization.region_id", "type": "all", "values": []}
            ),
            {"bool": {"filter": []}},
        )

    def test_region_and_other_filters_are_combined(self):
        """The fix must preserve sibling filters and the post-filter boundary."""
        filters, post_filter = build_request_filter(
            [
                {"field": "organization.region_id", "type": "all", "values": [1]},
                {"field": "from_root_domain", "type": "all", "values": [True]},
            ],
            False,
        )
        self.assertEqual(
            filters,
            [
                {"bool": {"filter": [{"term": {"organization.region_id": 1}}]}},
                {"bool": {"filter": [{"term": {"from_root_domain": True}}]}},
            ],
        )
        self.assertIsNone(post_filter)

    def test_domain_request_retains_organization_scope(self):
        """The complete request keeps its organization restriction intact."""
        request = build_request(
            DomainSearchBody(
                filters=[
                    {
                        "field": "organization_id",
                        "type": "any",
                        "values": [{"id": "visible-org"}],
                    },
                    {"field": "organization.region_id", "type": "all", "values": [1]},
                ]
            )
        )
        scoped_query = request["query"]["bool"]["must"]
        self.assertEqual(
            scoped_query[0], {"terms": {"organization.id.keyword": ["visible-org"]}}
        )
        self.assertEqual(
            scoped_query[1]["bool"]["filter"],
            [{"bool": {"filter": [{"term": {"organization.region_id": 1}}]}}],
        )


if __name__ == "__main__":
    unittest.main()
