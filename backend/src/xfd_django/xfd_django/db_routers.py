"""Database app router."""
# Standard Python Libraries
import logging

LOGGER = logging.getLogger(__name__)


class MyAppRouter:
    """App router."""

    def db_for_read(self, model, **hints):
        """Database for read."""
        # Specify the app you want to route to the mini_data_lake database
        if model._meta.app_label == "xfd_mini_dl":
            return "mini_data_lake"
        return "default"  # All other models go to the default database

    def db_for_write(self, model, **hints):
        """Database for write."""
        # Check if a target database is provided in hints
        LOGGER.debug(self)
        # Uncomment the below "if clause" for local testing
        # ##################################################
        target_db = hints["instance"]._state.db if hints.get("instance", None) else None
        if target_db == "mini_data_lake_secondary":
            return "mini_data_lake_secondary"
        # ##################################################
        # Default behavior based on app label
        if model._meta.app_label == "xfd_mini_dl":
            return "mini_data_lake"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relation."""
        # Check the app labels of both objects
        app_label1 = obj1._meta.app_label
        app_label2 = obj2._meta.app_label

        # If both objects are from the specific app, allow the relation
        if app_label1 == "xfd_mini_dl" and app_label2 == "xfd_mini_dl":
            return True

        # If only one of them is from the specific app, disallow the relation
        if app_label1 == "xfd_mini_dl" or app_label2 == "xfd_mini_dl":
            return False

        # Allow relations between all other models
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Allow migrate."""
        if app_label == "xfd_mini_dl":
            return (
                db == "mini_data_lake"
            )  # Migrate the specific app to the mini_data_lake database
        return db == "default"  # All other apps migrate to the default database
