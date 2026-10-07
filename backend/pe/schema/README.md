# PE database schema

This directory holds **reference-only** PostgreSQL schema dumps for the PE database.
Nothing here is applied automatically.

## Files

| File | Purpose |
|------|---------|
| `data_schema.sql` | Full `pg_dump` snapshot of the production PE database (tables, views, indexes, etc.) |

## What the repo uses at runtime

| Layer | Local development | Production (today) |
|-------|-------------------|---------------------|
| **Tables** | `pe_reports_django_project/home/models.py` → `pesyncdb` | Manual Structured Query Language (SQL) on the database, then `pesyncdb` Lambda |
| **Views** | `pe_reports_django_project/home/tasks/sql/local_report_views.sql` | Manual SQL on the database |
| **Application Programming Interface (API)** | `pe_reports_django_project/dataAPI/report_views.py` | Same code, deployed with the backend |
| **Reports and workers** | `src/pe_reports/data/db_query.py` calls the API over HTTP | Same |

Use `data_schema.sql` to look up existing definitions or compare local changes against
production. **After every table or view change in the database, dump the schema and commit
an updated `data_schema.sql`** so this repository stays the preservation copy of production.

**Current snapshot:** copied from ATC-Framework on 2026-07-14 (PostgreSQL 15.3, ~6.7k lines).
ATC-Framework is deprecated; this repository owns ongoing maintenance.

---

## Updating `data_schema.sql` (required after schema changes)

Whenever you add or change a table or view in the database, export a fresh schema dump and
replace `backend/pe/schema/data_schema.sql` in the same pull request as your code changes.

### Option A: `pg_dump` from the command line

From a host that can reach the database (accessor, terraformer, or your machine with VPN):

```bash
# credentials from AWS Systems Manager Parameter Store (see below)
pg_dump \
  -h "$DATABASE_HOST" \
  -U pe \
  -d pe \
  --schema-only \
  --no-owner \
  --no-privileges \
  -f backend/pe/schema/data_schema.sql
```

`--schema-only` matches the existing archive (tables, views, indexes — no row data).
Omit `--no-owner` / `--no-privileges` if your team prefers the full `pg_dump` format.

### Option B: DBeaver

1. Connect to the `pe` database.
2. Right-click the database (or `public` schema) → **Tools** → **Dump database** (or
   **Generate SQL** → **DDL** depending on DBeaver version).
3. Choose **schema only** (no data).
4. Save the file as `backend/pe/schema/data_schema.sql`, overwriting the previous copy.

### Commit the dump

Include the updated `data_schema.sql` in your pull request. Note the environment and date in
the commit message, for example: `Update PE schema dump after adding my_new_thing (staging, 2026-07-27)`.

---

## Connecting to the production database

Production credentials live in AWS Systems Manager Parameter Store. From an accessor or
terraformer host:

```bash
aws ssm get-parameter --name "/crossfeed/staging/DATABASE_HOST" --with-decryption
aws ssm get-parameter --name "/crossfeed/staging/PE_DB_NAME" --with-decryption
aws ssm get-parameter --name "/crossfeed/staging/PE_DB_USER" --with-decryption
aws ssm get-parameter --name "/crossfeed/staging/PE_DB_PASSWORD" --with-decryption
```

Use those values in a database client such as **DBeaver**, **pgAdmin**, or `psql`.

**Typical manual change in DBeaver:**

1. Open a new SQL editor connected to the `pe` database.
2. Paste your `CREATE TABLE`, `ALTER TABLE`, or `CREATE VIEW` statement.
3. Review it (especially foreign keys and `DROP` statements).
4. Execute against the correct environment (staging before production).
5. Confirm the object exists (`\d table_name` in `psql`, or refresh the schema tree in DBeaver).

For materialized views that reports refresh at runtime, you may also need a one-time
`REFRESH MATERIALIZED VIEW ... WITH DATA` after creation.

---

## Adding a table

### 1. Design the table

Choose the table name, columns, primary key, foreign keys, and indexes. Follow existing
conventions: `snake_case` names, `*_uid` columns with Universally Unique Identifier (UUID)
primary keys where appropriate.

### 2. Apply the change in production (manual)

Write the Data Definition Language (DDL) and run it in DBeaver (or equivalent):

```sql
CREATE TABLE public.my_new_thing (
    my_new_thing_uid uuid PRIMARY KEY,
    organizations_uid uuid NOT NULL REFERENCES organizations(organizations_uid),
    created_at timestamp with time zone DEFAULT now()
);
```

Repeat for staging first if your team uses a staging database.

### 3. Dump the schema and update `data_schema.sql`

Export a fresh schema dump from the database where you applied the change (see
[Updating `data_schema.sql`](#updating-data_schemasql-required-after-schema-changes))
and replace `backend/pe/schema/data_schema.sql`. Commit the dump with your other changes.

### 4. Mirror the table in this repository

Add a Django model in `pe_reports_django_project/home/models.py`:

```python
class MyNewThing(models.Model):
    my_new_thing_uid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    organizations_uid = models.ForeignKey("Organizations", models.DO_NOTHING)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "my_new_thing"
```

All PE models use `managed = False`, but local `pesyncdb` still creates and updates
**tables** from these models. View models (`vw_*`, `mat_vw_*`) are excluded from that sync.

### 5. Apply locally

```bash
make -C backend/pe syncdb
```

Or rebuild from scratch:

```bash
make -C backend/pe syncdb-dangerously-force
make -C backend/pe syncdb-populate
```

### 6. Optional: sample data for local testing

If scans or reports need rows to exercise the new table, add inserts in
`pe_reports_django_project/home/tasks/helpers/create_sample_data.py`.

### 7. Optional: align production schema via Lambda

After manual DDL in production, run the `pesyncdb` Lambda so deployed environments stay
aligned with `models.py` (adds missing columns, etc.):

```bash
aws lambda invoke --function-name crossfeed-prod-pesyncdb --log-type Tail --region us-east-1 /dev/stderr --query 'LogResult' --output text | base64 -d
```

### 8. If scan code writes to the table

Update the relevant `pe_source` scan module to insert or read from the new table.

---

## Adding a view

Views are **not** created from Django models. Models are read-only Object-Relational
Mapping (ORM) mirrors used by the API.

### 1. Write the view SQL

```sql
CREATE VIEW vw_my_new_view AS
 SELECT ...
   FROM some_table
  WHERE ...;
```

For a materialized view:

```sql
CREATE MATERIALIZED VIEW mat_vw_my_new_view AS
 SELECT ...
   FROM some_table
  WHERE ...;
```

### 2. Apply the change in production (manual)

Run the `CREATE VIEW` or `CREATE MATERIALIZED VIEW` statement in DBeaver against the
`pe` database (staging first). For materialized views, run:

```sql
REFRESH MATERIALIZED VIEW mat_vw_my_new_view WITH DATA;
```

### 3. Dump the schema and update `data_schema.sql`

Export a fresh schema dump from the database where you applied the change (see
[Updating `data_schema.sql`](#updating-data_schemasql-required-after-schema-changes))
and replace `backend/pe/schema/data_schema.sql`. Commit the dump with your other changes.

### 4. Add the view for local development

Edit these files:

- `pe_reports_django_project/home/tasks/sql/local_report_views.sql` — paste the full
  `CREATE VIEW` / `CREATE MATERIALIZED VIEW` statement
- `pe_reports_django_project/home/tasks/sql/local_report_view_order.txt` — add the view
  name **after** any views it depends on (for example, `vw_breachcomp` before
  `vw_flare_breachcomp`)

### 5. Apply locally

```bash
make -C backend/pe syncdb
```

`pesyncdb` runs `ensure_local_report_views()`, which creates any missing views.

### 6. Add a Django model (ORM mirror)

In `home/models.py`:

```python
class VwMyNewView(models.Model):
    # fields matching the view SELECT list
    class Meta:
        managed = False  # Created from a view. Don't remove.
        db_table = "vw_my_new_view"
```

### 7. If reports must refresh a materialized view

Add the view name to `refresh_asset_counts_vw()` in
`src/pe_reports/data/db_query.py` (report generation calls this at startup).

---

## Exposing data through the API

The PE API is a FastAPI application inside the Django project. Report routes live in
`pe_reports_django_project/dataAPI/report_views.py` and are mounted at `/apiv1`.

### 1. Response schema

Add a Pydantic model in `dataAPI/report_schemas.py`:

```python
class VwMyNewViewRow(BaseModel):
    some_uid: str
    organizations_uid: str
```

### 2. API endpoint

Add a route in `dataAPI/report_views.py` (follow `breachcomp_by_org` as a template):

```python
@report_router.post(
    "/my_new_view_by_org",
    dependencies=[Depends(verify_api_key)],
    response_model=List[schemas.VwMyNewViewRow],
)
def my_new_view_by_org(data: schemas.GenInputOrgUIDDateRange, ...):
    rows = list(
        VwMyNewView.objects.filter(
            organizations_uid=data.org_uid,
            modified_date__date__range=(data.start_date, data.end_date),
        ).values()
    )
    # convert UUIDs and dates to strings (see breachcomp_by_org)
    return rows
```

Routes register automatically via `pe_reports_django/asgi.py`.

### 3. Client for reports and workers

Add a function in `src/pe_reports/data/db_query.py` that POSTs to the new endpoint
(copy the pattern from `query_creds_view()`):

```python
def query_my_new_view(org_uid, start_date, end_date):
    endpoint_url = pe_api_url + "my_new_view_by_org"
    ...
    result = requests.post(endpoint_url, headers=headers, data=data, ...).json()
    return _dataframe_from_api_json(result)
```

### 4. Use the data

Call the new `query_*` function from `metrics.py`, `report_generator.py`, or other
consumers.

### 5. Test locally

- `npm start` (backend must be running for API calls)
- `make -C backend/pe test`

### Preferred pattern vs legacy

| Preferred | Legacy (being replaced) |
|-----------|-------------------------|
| Table or view → Django model → FastAPI route → `db_query.py` HTTP client | Direct SQL in `db_query.py` via `psycopg2` |

Functions tagged `# TODO: Convert to API endpoint in CRASM-4061` still use direct SQL.

---

## Quick checklists

### New table

1. Run `CREATE TABLE` in DBeaver (staging, then production)
2. Dump schema → update `backend/pe/schema/data_schema.sql`
3. Add model to `home/models.py`
4. `make -C backend/pe syncdb`
5. Optional: sample data, scan write path, `pesyncdb` Lambda

### New view

1. Run `CREATE VIEW` in DBeaver (staging, then production)
2. Dump schema → update `backend/pe/schema/data_schema.sql`
3. Add SQL to `local_report_views.sql` and `local_report_view_order.txt`
4. Add `Vw...` model to `home/models.py`
5. `make -C backend/pe syncdb`
6. Optional: `refresh_asset_counts_vw()`

### New API for reports

1. `report_schemas.py` — response model
2. `report_views.py` — endpoint
3. `db_query.py` — HTTP client function
4. Wire into report or scan code
5. Tests
