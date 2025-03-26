"""Syncdb helpers."""
# File: xfd_api/utils/db_utils.py
# Standard Python Libraries
from datetime import datetime
import hashlib
from itertools import islice
import json
import os
import random
import secrets

# Third-Party Libraries
from django.apps import apps
from django.conf import settings
from django.db import connections, transaction
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.utils import OperationalError
from xfd_api.models import (
    ApiKey,
    Domain,
    Organization,
    OrganizationTag,
    Service,
    User,
    UserType,
    Vulnerability,
)
from xfd_api.tasks.es_client import ESClient

# Constants for sample data generation
SAMPLE_TAG_NAME = "Sample Data"
NUM_SAMPLE_ORGS = 10
NUM_SAMPLE_DOMAINS = 10
PROB_SAMPLE_SERVICES = 0.5
PROB_SAMPLE_VULNERABILITIES = 0.5
SAMPLE_STATES = ["Virginia", "California", "Colorado"]
SAMPLE_REGION_IDS = ["1", "2", "3"]
ORGANIZATION_CHUNK_SIZE = 50

# Load sample data files
SAMPLE_DATA_DIR = os.path.join(settings.BASE_DIR, "xfd_api", "tasks", "sample_data")
services = json.load(open(os.path.join(SAMPLE_DATA_DIR, "services.json")))
cpes = json.load(open(os.path.join(SAMPLE_DATA_DIR, "cpes.json")))
vulnerabilities = json.load(open(os.path.join(SAMPLE_DATA_DIR, "vulnerabilities.json")))
nouns = json.load(open(os.path.join(SAMPLE_DATA_DIR, "nouns.json")))
adjectives = json.load(open(os.path.join(SAMPLE_DATA_DIR, "adjectives.json")))

# Elasticsearch client
es_client = ESClient()


def manage_elasticsearch_indices(dangerouslyforce):
    """Handle Elasticsearch index setup and teardown."""
    try:
        if dangerouslyforce:
            es_client.delete_all()
        es_client.sync_organizations_index()
        es_client.sync_domains_index()
        print("Elasticsearch indices synchronized.")
    except Exception as e:
        print("Error managing Elasticsearch indices: {}".format(e))


def populate_sample_data():
    """Populate sample data into the database."""
    with transaction.atomic():
        tag, _ = OrganizationTag.objects.get_or_create(name=SAMPLE_TAG_NAME)
        for _ in range(NUM_SAMPLE_ORGS):
            # Create organization
            org = Organization.objects.create(
                acronym="".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5)),
                name=generate_random_name(),
                rootDomains=["crossfeed.local"],
                ipBlocks=[],
                isPassive=False,
                state=random.choice(SAMPLE_STATES),
                regionId=random.choice(SAMPLE_REGION_IDS),
            )
            org.tags.add(tag)

            # Create sample domains, services, and vulnerabilities
            for _ in range(NUM_SAMPLE_DOMAINS):
                domain = create_sample_domain(org)
                create_sample_services_and_vulnerabilities(domain)

        # Create a user for the organization
        user = create_sample_user(org)

        # Create an API key for the user
        create_api_key_for_user(user)

        test_user = create_test_user(org)

        create_api_key_for_user(test_user)


def create_sample_user(organization):
    """Create a sample user linked to an organization."""
    user = User.objects.create(
        firstName="Sample",
        lastName="User",
        email="user{}@example.com".format(random.randint(1, 1000)),
        userType=UserType.GLOBAL_ADMIN,
        state=random.choice(SAMPLE_STATES),
        regionId=random.choice(SAMPLE_REGION_IDS),
    )
    # Set user as the creator of the organization (optional)
    organization.createdBy = user
    organization.save()
    return user


def create_test_user(organization):
    """Create a test user linked to an organization."""
    email = os.environ.get("PW_XFD_USERNAME")

    existing_user = User.objects.filter(email=email).first()

    if existing_user:
        return existing_user

    if not email:
        user = User.objects.create(
            firstName="Test",
            lastName="User",
            email=os.environ.get("PW_XFD_USERNAME"),
            userType=UserType.GLOBAL_ADMIN,
            state=random.choice(SAMPLE_STATES),
            regionId=random.choice(SAMPLE_REGION_IDS),
            organization=organization,
        )

    return user


def create_api_key_for_user(user):
    """Create a sample API key linked to a user."""
    # Generate a random 16-byte API key
    key = secrets.token_hex(16)

    # Hash the API key
    hashed_key = hashlib.sha256(key.encode()).hexdigest()

    # Create the API key record
    ApiKey.objects.create(
        hashedKey=hashed_key,
        lastFour=key[-4:],
        user=user,
        createdAt=datetime.utcnow(),
        updatedAt=datetime.utcnow(),
    )

    # Print the raw key for debugging or manual testing
    print("Created API key for user {}: {}".format(user.email, key))


def generate_random_name():
    """Generate a random organization name using an adjective and entity noun."""
    adjective = random.choice(adjectives)
    noun = random.choice(nouns)
    entity = random.choice(["City", "County", "Agency", "Department"])
    return "{} {} {}".format(adjective.capitalize(), entity, noun.capitalize())


def create_sample_domain(organization):
    """Create a sample domain linked to an organization."""
    domain_name = "{}-{}.crossfeed.local".format(
        random.choice(adjectives), random.choice(nouns)
    ).lower()
    ip = ".".join(map(str, (random.randint(0, 255) for _ in range(4))))
    return Domain.objects.create(
        name=domain_name,
        ip=ip,
        fromRootDomain="crossfeed.local",
        isFceb=True,
        subdomainSource="findomain",
        organization=organization,
    )


def create_sample_services_and_vulnerabilities(domain):
    """Create sample services and vulnerabilities for a domain."""
    # Add random services
    if random.random() < PROB_SAMPLE_SERVICES:
        Service.objects.create(
            domain=domain,
            port=random.choice([80, 443]),
            service="http",
            serviceSource="shodan",
            wappalyzerResults=[
                {"technology": {"cpe": random.choice(cpes)}, "version": ""}
            ],
        )

    # Add random vulnerabilities
    if random.random() < PROB_SAMPLE_VULNERABILITIES:
        state = random.choice(["open", "closed"])
        Vulnerability.objects.create(
            title="Sample Vulnerability "
            + "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=3)),
            domain=domain,
            service=None,
            description="Sample description",
            severity=random.choice(
                [
                    None,
                    "N/A",
                    "n/a",
                    "Null",
                    "null",
                    "Undefined",
                    "undefined",
                    "",
                    "Low",
                    "Medium",
                    "High",
                    "Critical",
                    "Other",
                    "!@#$%^&*()",
                    1234,
                    "low",
                    "medium",
                    "high",
                    "critical",
                    "other",
                ]
            ),
            cve="CVE-"
            + random.choice(
                [
                    "2024-47421",
                    "2021-22501",
                    "2024-53959",
                    "2024-47422",
                    "2024-47423",
                    "2020-28163",
                    "2020-29312",
                ]
            ),
            needsPopulation=True,
            state=state,
            substate=random.choice(["unconfirmed", "exploitable"])
            if state == "open"
            else random.choice(["false-positive", "accepted-risk", "remediated"]),
            source="sample_source",
            actions=[],
            structuredData={},
        )


def synchronize(target_app_label=None, using=None):
    """
    Synchronize the database schema with Django models.

    Handles creation, update, and removal of tables and fields dynamically,
    including Many-to-Many linking tables.
    """
    allowed_labels = ["xfd_mini_dl", "xfd_api"]
    db_mapping = {
        "xfd_mini_dl": "mini_data_lake",
        "xfd_api": "default",
    }

    if target_app_label is None:
        raise ValueError(
            "The 'target_app_label' parameter is required to synchronize specific models. "
            "Please provide an app label."
        )

    if target_app_label not in allowed_labels:
        raise ValueError(
            "Invalid 'target_app_label' provided. Must be one of: {}.".format(
                ", ".join(allowed_labels)
            )
        )

    # Get database name for 'connections':
    # The 'connections' object gets all databases defined in settings.py
    database = db_mapping.get(target_app_label, "default")
    # Used only for syncing a duplicate database that mirrors the xfd_mini_dl schema
    if using:
        database = using
    print(
        "Synchronizing database schema for app '{}' in database '{}'...".format(
            target_app_label, database
        )
    )

    # Warning: Cursor automatically closes after use of 'with'
    with connections[database].schema_editor() as schema_editor:
        # Step 1: Process models in dependency order
        ordered_models = get_ordered_models(target_app_label)
        for model in ordered_models:
            print("Processing model: {}".format(model.__name__))
            process_model(schema_editor, model, database)

        # Step 2: Handle Many-to-Many tables
        print("Processing Many-to-Many tables...")
        process_m2m_tables(schema_editor, ordered_models, database)

        # Step 3: Cleanup stale tables
        cleanup_stale_tables(ordered_models, database)

    print("Database synchronization complete.")


def get_ordered_models(target_app_label):
    """
    Get models in dependency order to ensure foreign key constraints are respected.

    Handles circular dependencies gracefully by breaking cycles.
    """
    # Standard Python Libraries
    from collections import defaultdict, deque

    dependencies = defaultdict(set)
    dependents = defaultdict(set)

    models = list(apps.get_app_config(target_app_label).get_models())

    for model in models:
        for field in model._meta.get_fields():
            if field.is_relation and field.related_model:
                dependencies[model].add(field.related_model)
                dependents[field.related_model].add(model)

    ordered = []
    independent_models = deque(model for model in models if not dependencies[model])

    while independent_models:
        model = independent_models.popleft()
        ordered.append(model)
        for dependent in list(dependents[model]):
            dependencies[dependent].remove(model)
            dependents[model].remove(dependent)
            if not dependencies[dependent]:
                independent_models.append(dependent)

    # Handle circular dependencies
    if any(dependencies.values()):
        print("Circular dependencies detected. Breaking cycles arbitrarily.")
        for model, deps in dependencies.items():
            if deps:
                print("Breaking dependency for model: {}".format(model.__name__))
                dependencies[model] = set()

        ordered.extend(dependencies.keys())

    return ordered


def process_model(schema_editor: BaseDatabaseSchemaEditor, model, database):
    """Process a single model: create or update its table."""
    table_name = model._meta.db_table

    with connections[database].cursor() as cursor:
        try:
            # Check if the table exists
            cursor.execute("SELECT to_regclass(%s);", [table_name])
            table_exists = cursor.fetchone()[0] is not None

            if table_exists:
                print("Updating table for model: {}".format(model.__name__))
                update_table(schema_editor, model, database)
            else:
                print("Creating table for model: {}".format(model.__name__))
                schema_editor.create_model(model)
        except Exception as e:
            print("Error processing model {}: {}".format(model.__name__, e))


def process_m2m_tables(schema_editor: BaseDatabaseSchemaEditor, models, database):
    """Handle creation of Many-to-Many linking tables."""
    with connections[database].cursor() as cursor:
        for model in models:
            for field in model._meta.local_many_to_many:
                m2m_table_name = field.m2m_db_table()

                # Check if the M2M table exists
                cursor.execute("SELECT to_regclass('{}');".format(m2m_table_name))
                table_exists = cursor.fetchone()[0] is not None

                if not table_exists:
                    print("Creating Many-to-Many table: {}".format(m2m_table_name))
                    schema_editor.create_model(field.remote_field.through)
                else:
                    print(
                        "Many-to-Many table {} already exists. Skipping.".format(
                            m2m_table_name
                        )
                    )


def update_table(schema_editor: BaseDatabaseSchemaEditor, model, database):
    """Update an existing table for the given model. Ensure columns match fields."""
    table_name = model._meta.db_table
    db_fields = {field.column for field in model._meta.fields}

    with connections[database].cursor() as cursor:
        # Get existing columns
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s;",
            [table_name],  # Pass the table name as a parameter
        )
        existing_columns = {row[0] for row in cursor.fetchall()}

        # Add missing columns
        missing_columns = db_fields - existing_columns
        for field in model._meta.fields:
            if field.column in missing_columns:
                print(
                    "Adding column '{}' to table '{}'".format(field.column, table_name)
                )
                schema_editor.add_field(model, field)

        # Remove extra columns
        extra_columns = existing_columns - db_fields
        for column in extra_columns:
            print(
                "Removing extra column '{}' from table '{}'".format(column, table_name)
            )
            try:
                # Safely quote table and column names
                safe_table_name = connections[database].ops.quote_name(table_name)
                safe_column_name = connections[database].ops.quote_name(column)
                # Construct and execute the query without f-strings
                query = "ALTER TABLE {} DROP COLUMN IF EXISTS {};".format(
                    safe_table_name, safe_column_name
                )
                cursor.execute(query)
            except Exception as e:
                print(
                    "Error dropping column '{}' from table '{}': {}".format(
                        column, table_name, e
                    )
                )


def cleanup_stale_tables(models, database):
    """Remove tables that no longer correspond to any Django model or Many-to-Many relationship."""
    print("Checking for stale tables...")

    with connections[database].cursor() as cursor:
        model_tables = {model._meta.db_table for model in models}
        m2m_tables = {
            field.m2m_db_table()
            for model in models
            for field in model._meta.local_many_to_many
        }
        expected_tables = model_tables.union(m2m_tables)

        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        existing_tables = {row[0] for row in cursor.fetchall()}

        stale_tables = existing_tables - expected_tables
        for table in stale_tables:
            print("Removing stale table: {}".format(table))
            try:
                # Use `quote_ident` to safely handle table names with special characters or reserved words
                cursor.execute(
                    "DROP TABLE {} CASCADE;".format(
                        connections[database].ops.quote_name(table)
                    )
                )
            except OperationalError as e:
                print("Error dropping stale table {}: {}".format(table, e))


def drop_all_tables(app_label=None):
    """Drop all tables in the database. Used with `dangerouslyforce`."""
    allowed_labels = ["xfd_mini_dl", "xfd_api"]
    db_mapping = {
        "xfd_mini_dl": "mini_data_lake",
        "xfd_api": "default",
    }

    if app_label is None:
        raise ValueError(
            "The 'app_label' parameter is required to synchronize specific models."
        )

    if app_label not in allowed_labels:
        raise ValueError(
            "Invalid 'app_label' provided. Must be one of: {}.".format(
                ", ".join(allowed_labels)
            )
        )

    database = db_mapping.get(app_label, "default")
    print(
        "Resetting database schema for app '{}' in database '{}'...".format(
            app_label, database
        )
    )

    with connections[database].cursor() as cursor:
        try:
            # Drop all constraints first to avoid foreign key dependency issues
            cursor.execute("DROP SCHEMA public CASCADE;")
            cursor.execute("CREATE SCHEMA public;")
            cursor.execute(
                "GRANT ALL ON SCHEMA public TO {};".format(os.getenv("DB_USERNAME"))
            )
            cursor.execute("GRANT ALL ON SCHEMA public TO public;")
        except Exception as e:
            print("Error resetting schema: {}".format(e))

    print("Database schema reset successfully.")


def chunked_iterable(iterable, size):
    """Yield successive chunks of size `size` from `iterable`."""
    iterator = iter(iterable)
    while True:
        chunk = list(islice(iterator, size))
        if not chunk:
            break
        yield chunk


def update_organization_chunk(es_client, organizations):
    """Update a chunk of organizations."""
    es_client.update_organizations(organizations)


def sync_es_organizations():
    """Sync elastic search organizations."""
    try:
        # Fetch all organization IDs
        organization_ids = list(Organization.objects.values_list("id", flat=True))
        print("Found {} organizations to sync.".format(len(organization_ids)))

        if organization_ids:
            # Split IDs into chunks
            for organization_chunk in chunked_iterable(
                organization_ids, ORGANIZATION_CHUNK_SIZE
            ):
                # Fetch full organization data for the current chunk
                organizations = list(
                    Organization.objects.filter(id__in=organization_chunk).values(
                        "id", "name", "country", "state", "regionId", "tags"
                    )
                )
                print("Syncing {} organizations...".format(len(organizations)))

                # Attempt to update Elasticsearch
                update_organization_chunk(es_client, organizations)

            print("Organization sync complete.")
        else:
            print("No organizations to sync.")

    except Exception as e:
        print("Error syncing organizations: {}".format(e))
        raise e
