"""Syncdb helpers."""
# File: xfd_api/utils/db_utils.py
# Standard Python Libraries
from collections import defaultdict, deque
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


def table_exists_in_db(table_name, database):
    """Check table exists."""
    with connections[database].cursor() as cursor:
        cursor.execute("SELECT to_regclass(%s);", [table_name])
        return cursor.fetchone()[0] is not None


def synchronize(target_app_label=None):
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
    print(
        "Synchronizing database schema for app '{}' in database '{}'...".format(
            target_app_label, database
        )
    )

    # Warning: Cursor automatically closes after use of 'with'
    with connections[database].schema_editor() as schema_editor:
        ordered_models = get_ordered_models(target_app_label)
        # Compute allowed table names from the models we are syncing.
        allowed_tables = {m._meta.db_table for m in ordered_models}
        for model in ordered_models:
            print("Processing model: {}".format(model.__name__))
            process_model(schema_editor, model, database, allowed_tables)

        print("Processing Many-to-Many tables...")
        process_m2m_tables(schema_editor, ordered_models, database)
        create_normal_views(database)
        create_materialized_views(database)
        cleanup_stale_tables(ordered_models, database)

    print("Database synchronization complete.")


def get_ordered_models(target_app_label):
    """
    Get models in dependency order to ensure foreign key constraints are respected.

    Only consider dependencies among models within the same app, and break cycles
    deterministically (alphabetically by model name).
    """
    # Get all models for the app and create a set for quick membership checks.
    models = list(apps.get_app_config(target_app_label).get_models())
    model_set = set(models)

    # Build dependency graph, but only include dependencies to models within the app.
    dependencies = defaultdict(set)
    dependents = defaultdict(set)
    for model in models:
        for field in model._meta.get_fields():
            # Only add a dependency if the related model is in our app's set.
            if field.is_relation and field.related_model in model_set:
                dependencies[model].add(field.related_model)
                dependents[field.related_model].add(model)

    # Start with models that have no dependencies.
    ordered = []
    independent_models = deque([model for model in models if not dependencies[model]])

    while independent_models:
        model = independent_models.popleft()
        ordered.append(model)
        # Remove this model as a dependency from its dependents.
        for dependent in list(dependents[model]):
            dependencies[dependent].discard(model)
            dependents[model].discard(dependent)
            if not dependencies[dependent]:
                independent_models.append(dependent)

    # Any models not yet added are in a dependency cycle.
    remaining = [model for model in models if model not in ordered]
    if remaining:
        print(
            "Circular dependencies detected among: {}".format(
                ", ".join(m.__name__ for m in remaining)
            )
        )
        # Sort them deterministically (alphabetically) so that, for example, 'User' comes before 'Organization'
        remaining_sorted = sorted(remaining, key=lambda m: m.__name__)
        ordered.extend(remaining_sorted)

    return ordered


def process_model(
    schema_editor: BaseDatabaseSchemaEditor, model, database, allowed_tables
):
    """Process a single model: create or update its table."""
    table_name = model._meta.db_table

    with connections[database].cursor() as cursor:
        try:
            # Check if the table exists
            cursor.execute("SELECT to_regclass(%s);", [table_name])
            table_exists = cursor.fetchone()[0] is not None

            if table_exists:
                print("Updating table for model: {}".format(model.__name__))
                update_table(schema_editor, model, database, allowed_tables)
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


def update_table(
    schema_editor: BaseDatabaseSchemaEditor, model, database, allowed_tables
):
    """Update an existing table for the given model. Ensure columns match fields."""
    table_name = model._meta.db_table
    db_fields = {field.column for field in model._meta.fields}

    with connections[database].cursor() as cursor:
        # Get existing columns
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s;",
            [table_name],
        )
        existing_columns = {row[0] for row in cursor.fetchall()}

        # Add missing columns
        missing_columns = db_fields - existing_columns
        for field in model._meta.fields:
            if field.column in missing_columns:
                if hasattr(field, "remote_field") and field.remote_field:
                    related_table = field.remote_field.model._meta.db_table
                    # If the related table isn't in allowed_tables or doesn't exist yet, skip adding this field.
                    if related_table not in allowed_tables or not table_exists_in_db(
                        related_table, database
                    ):
                        print(
                            "Skipping addition of foreign key field '{}' on model '{}' because referenced table '{}' does not exist yet.".format(
                                field.column, model.__name__, related_table
                            )
                        )
                        continue
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
                safe_table_name = connections[database].ops.quote_name(table_name)
                safe_column_name = connections[database].ops.quote_name(column)
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

def create_normal_views(database):
    with connections[database].cursor() as cursor:
        print("Creating normal views...")

        cursor.execute("""
            CREATE OR REPLACE VIEW vw_ticket_vulns AS
            -- Query for VS Ticket Vulns
            SELECT 
                'vuln_scanning_tickets' as scan_source,
                t.id as id,
                t.opened_timestamp as first_seen,
                coalesce(t.closed_timestamp, t.updated_timestamp) as last_seen,
                t.cve_string as cve,
                t.vuln_name as title,
                vs.cpe as product,	
                t.ip_string as domain,
                t.ip_id as domain_id,
                t.port_protocol as protocol,
                t.vuln_port::text as port,
                t.cvss_base_score,
                t.cvss_severity::text as severity,
                t.organization_id,
                --t.kev, as is_kev,
                --t.service,
                --t.risky_service = is_risky_service,
                --t.os as os --Not seeing this in the ticket
                te."action" as state,
                t.vuln_source as data_source,
                vs.description
            FROM ticket t
            LEFT JOIN ticket_event te 
            ON te.ticket_id = t.id
            LEFT JOIN vuln_scan vs 
            ON vs.id = te.vuln_scan_id
            WHERE te.event_timestamp = (
                SELECT MAX(event_timestamp)
                FROM ticket_event
                WHERE ticket_id = t.id
            )
        """)

        cursor.execute("""
            CREATE OR REPLACE VIEW vw_shodan_vulns AS
            -- Query for ShodanVulns
            SELECT
                'shodan_vulnerability' as scan_source,
                sv.shodan_vuln_uid::text as id,
                null as first_seen,
                sv."timestamp" as last_seen,
                sv.cve as cve,
                sv.name as title,
                array_to_string(sv.cpe, ', ') as product,
                sv.ip_string as domain,
                sv.ip_id as domain_id,
                sv.protocol as protocol,
                sv.port as port,
                sv.cvss as cvss_base_score,
                sv.severity as severity,
                sv.organization_uid as organization_id,
                'Open' as state,
                'Shodan' as data_source,
                null as description
            FROM shodan_vulns as sv
        """)

        cursor.execute("""
            CREATE OR REPLACE VIEW vw_credential_breaches AS
            SELECT DISTINCT 
                'credential_breach' as scan_source,
                cb.credential_breaches_uid::text as id,
                cb.breach_date as first_seen,
                cb.modified_date as last_seen,
                null as cve,
                cb.breach_name as title,
                null as product,
                ce.sub_domain_string as domain,
                ce.sub_domain_id as domain_id,
                'SMTP,IMAP,POP3' as protocol, --"Unsure on this one"
                null as port,
                null::float as cvss_base_score,
                'Medium' as severity,
                ce.organization_id,
                'Open' as state,
                ds.name as data_source,
                cb.description 
            FROM credential_breaches cb
            JOIN credential_exposures ce on cb.credential_breaches_uid = ce.credential_breach_id
            JOIN data_source ds on ds.data_source_uid = cb.data_source_uid
        """)
        print("Normal views created.")

def create_materialized_views(database):
    with connections[database].cursor() as cursor:
        print("Creating materialized views...")

        cursor.execute("DROP MATERIALIZED VIEW IF EXISTS mat_vw_combined_vulns;")

        # Example materialized view
        cursor.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS mat_vw_combined_vulns AS
            SELECT * from vw_shodan_vulns
            union 
            SELECT * from vw_credential_breaches
        """)

        # Optional refresh
        cursor.execute("REFRESH MATERIALIZED VIEW mat_vw_combined_vulns;")

        print("Materialized views created.")

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
