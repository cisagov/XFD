"""Unit tests for PE schema synchronization database queries."""

# Standard Python Libraries
import unittest
from unittest.mock import MagicMock, patch

# Third-Party Libraries
from django.db.utils import OperationalError

# First-Party Libraries
from home.tasks import syncdb_task


class TableExistsTests(unittest.TestCase):
    """Verify physical-table existence queries."""

    @patch("home.tasks.syncdb_task.connections")
    def test_table_exists_uses_parameterized_catalog_query(self, connections_mock):
        """Query PostgreSQL catalogs using a table-name parameter."""
        cursor = MagicMock()
        cursor.fetchone.return_value = (True,)
        connections_mock.__getitem__.return_value.cursor.return_value.__enter__.return_value = (
            cursor
        )

        result = syncdb_task.table_exists_in_db("organizations", "default")

        self.assertTrue(result)
        self.assertEqual(cursor.execute.call_args.args[1], ["organizations"])
        self.assertIn("pg_catalog.pg_class", cursor.execute.call_args.args[0])


class ModelOrderingTests(unittest.TestCase):
    """Verify model dependency ordering."""

    @patch("home.tasks.syncdb_task._local_sync_models")
    def test_get_ordered_models_places_referenced_model_first(self, models_mock):
        """Create referenced tables before tables containing foreign keys."""
        parent = MagicMock()
        parent.__name__ = "Parent"
        child = MagicMock()
        child.__name__ = "Child"
        parent._meta.get_fields.return_value = []
        relation = MagicMock(is_relation=True, related_model=parent)
        child._meta.get_fields.return_value = [relation]
        models_mock.return_value = [child, parent]

        result = syncdb_task.get_ordered_models("home")

        self.assertEqual(result, [parent, child])


class ProcessModelTests(unittest.TestCase):
    """Verify create/update branches and transaction handling."""

    @patch("home.tasks.syncdb_task.transaction")
    @patch("home.tasks.syncdb_task.update_table")
    @patch("home.tasks.syncdb_task.table_exists_in_db", return_value=True)
    def test_existing_table_is_updated(
        self, _exists_mock, update_mock, transaction_mock
    ):
        """Update a model when its table already exists."""
        model = MagicMock()
        model.__name__ = "Organizations"
        model._meta.db_table = "organizations"
        editor = MagicMock()
        transaction_mock.savepoint.return_value = "savepoint"

        syncdb_task.process_model(editor, model, "default", {"organizations"})

        update_mock.assert_called_once_with(editor, model, "default", {"organizations"})
        transaction_mock.savepoint_commit.assert_called_once_with(
            "savepoint", using="default"
        )

    @patch("home.tasks.syncdb_task.transaction")
    @patch("home.tasks.syncdb_task.table_exists_in_db", return_value=False)
    def test_missing_table_is_created(self, _exists_mock, transaction_mock):
        """Create a model when its table does not exist."""
        model = MagicMock()
        model.__name__ = "Organizations"
        model._meta.db_table = "organizations"
        editor = MagicMock()
        transaction_mock.savepoint.return_value = "savepoint"

        syncdb_task.process_model(editor, model, "default", {"organizations"})

        editor.create_model.assert_called_once_with(model)
        transaction_mock.savepoint_commit.assert_called_once()

    @patch("home.tasks.syncdb_task.transaction")
    @patch(
        "home.tasks.syncdb_task.table_exists_in_db",
        side_effect=OperationalError("down"),
    )
    def test_database_error_rolls_back_savepoint(self, _exists_mock, transaction_mock):
        """Roll back the model savepoint when a database operation fails."""
        model = MagicMock()
        model.__name__ = "Organizations"
        model._meta.db_table = "organizations"
        transaction_mock.savepoint.return_value = "savepoint"

        syncdb_task.process_model(MagicMock(), model, "default", set())

        transaction_mock.savepoint_rollback.assert_called_once_with(
            "savepoint", using="default"
        )


class IndexExistsTests(unittest.TestCase):
    """Verify duplicate-index detection."""

    def test_matching_index_name_is_found(self):
        """Treat an identical index name as already existing."""
        model_index = MagicMock(name="index")
        model_index.name = "organizations_name_idx"
        model_index.fields = ["name"]
        model_index.condition = None

        result = syncdb_task.index_exists_in_db(
            model_index,
            [("organizations_name_idx", "CREATE INDEX other_definition")],
        )

        self.assertTrue(result)

    def test_matching_field_definition_is_found(self):
        """Treat an equivalent field index as already existing."""
        model_index = MagicMock(name="index")
        model_index.name = "new_name"
        model_index.fields = ["name", "report_on"]
        model_index.condition = None

        result = syncdb_task.index_exists_in_db(
            model_index,
            [("old_name", "CREATE INDEX ON organizations (name, report_on)")],
        )

        self.assertTrue(result)


class CleanupAndResetTests(unittest.TestCase):
    """Verify stale-table cleanup and full schema reset queries."""

    @patch("home.tasks.syncdb_task.connections")
    def test_cleanup_drops_only_stale_physical_tables(self, connections_mock):
        """Preserve expected tables and views while dropping stale tables."""
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [("organizations",), ("old_table",), ("vw_report",)],
            [("vw_report",)],
            [],
        ]
        database = MagicMock()
        database.cursor.return_value.__enter__.return_value = cursor
        database.ops.quote_name.side_effect = lambda name: f'"{name}"'
        connections_mock.__getitem__.return_value = database
        model = MagicMock()
        model._meta.db_table = "organizations"
        model._meta.local_many_to_many = []

        syncdb_task.cleanup_stale_tables([model], "default")

        drop_calls = [
            call.args[0]
            for call in cursor.execute.call_args_list
            if call.args and call.args[0].startswith("DROP TABLE")
        ]
        self.assertEqual(drop_calls, ['DROP TABLE "old_table" CASCADE;'])

    @patch("home.tasks.syncdb_task.connections")
    def test_drop_all_tables_recreates_and_grants_public_schema(self, connections_mock):
        """Execute the complete schema reset sequence."""
        cursor = MagicMock()
        connections_mock.__getitem__.return_value.cursor.return_value.__enter__.return_value = (
            cursor
        )

        with patch.dict(
            "os.environ",
            {"PE_DB_USERNAME": "pe_user", "DB_USERNAME": "admin_user"},
            clear=False,
        ):
            syncdb_task.drop_all_tables()

        statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertEqual(
            statements,
            [
                "DROP SCHEMA public CASCADE;",
                "CREATE SCHEMA public;",
                "GRANT ALL ON SCHEMA public TO admin_user;",
                "GRANT ALL ON SCHEMA public TO pe_user;",
                "GRANT ALL ON SCHEMA public TO public;",
            ],
        )

    def test_drop_all_tables_rejects_other_apps(self):
        """Prevent the PE command from resetting unrelated app schemas."""
        with self.assertRaises(ValueError):
            syncdb_task.drop_all_tables("other")


if __name__ == "__main__":
    unittest.main()
