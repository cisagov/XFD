"""Tests for local report SQL/mat view creation."""

# Standard Python Libraries
import os
import unittest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pe_reports_django.settings")
os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")  # nosec B105

# Third-Party Libraries
import django

django.setup()

# Third-Party Libraries
from home.tasks.local_report_views import build_local_report_views  # noqa: E402


class LocalReportViewTests(unittest.TestCase):
    """build_local_report_views bundles production-equivalent DDL."""

    def test_includes_flare_and_breach_views(self):
        """Bundle includes report views and excludes unused attack-surface views."""
        view_definitions = dict(build_local_report_views())
        self.assertIn("mat_vw_breachcomp", view_definitions)
        self.assertIn("vw_flare_breachcomp", view_definitions)
        self.assertNotIn("top_cves_shodan", view_definitions)
        self.assertNotIn("mat_vw_orgs_attacksurface", view_definitions)
        self.assertNotIn("vw_orgs_total_ports", view_definitions)

    def test_view_sql_queries_real_tables(self):
        """Each bundled view references real tables instead of empty stubs."""
        view_definitions = dict(build_local_report_views())
        for name, ddl in view_definitions.items():
            with self.subTest(view=name):
                self.assertNotIn(
                    "where false",
                    ddl.lower(),
                    msg=name,
                )
                self.assertTrue(
                    " from " in ddl.lower() or " join " in ddl.lower(),
                    msg=name,
                )

    def test_flare_views_filter_flare_data_source(self):
        """Flare breach views filter credential_exposures by Flare source UUID."""
        view_definitions = dict(build_local_report_views())
        flare_ddl = view_definitions["vw_flare_breachcomp"].lower()
        self.assertIn("credential_exposures", flare_ddl)
        self.assertIn("751a4ff4-ac0c-11ef-8c7d-02527bfc647f", flare_ddl)
        self.assertIn("creds.login_url", flare_ddl)
        self.assertIn("creds.modified_date", flare_ddl)
        self.assertIn(
            "from vw_flare_breachcomp",
            view_definitions["vw_flare_breachcomp_breachdetails"].lower(),
        )
        self.assertIn(
            "from vw_flare_breachcomp",
            view_definitions["vw_flare_breachcomp_credsbydate"].lower(),
        )

    def test_breachcomp_filters_non_flare_sources(self):
        """Core breach view excludes Flare credential source rows."""
        view_definitions = dict(build_local_report_views())
        breach_ddl = view_definitions["vw_breachcomp"].lower()
        self.assertIn("fa4e7454-8baa-11ed-b121-02c6a3fe975b", breach_ddl)
        self.assertIn("744fb0ec-981d-11ec-a0ff-02589a36c9d7", breach_ddl)


if __name__ == "__main__":
    unittest.main()
