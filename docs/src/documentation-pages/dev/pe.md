# P&E local development

## Runbook (dnstwist)

### 1. Environment

From the repo root, create or refresh your local `.env` from the example file:

```bash
cp dev.env.example .env
```

If you already have a `.env`, make sure these P&E variables are present (defaults from `dev.env.example`):

```bash
PE_DB_NAME=pe
PE_DB_USERNAME=pe
PE_DB_PASSWORD=password

PE_API_KEY=local-dev-key
PE_API_URL=http://127.0.0.1:8000

PE_QUEUE_PREFIX=staging
PE_WORKER_SCAN_TYPE=dnstwist

QUEUE_URL=http://elasticmq:9324
SQS_ENDPOINT_URL=http://elasticmq:9324
IS_LOCAL=1
```

Crossfeed postgres admin credentials (used by `pesyncdb` to create the `pe` database) come from the same file:

```bash
DB_HOST=db
DB_USERNAME=crossfeed
DB_PASSWORD=password
```

### 2. Start the stack

```bash
npm start
```

This starts **db**, **backend**, and **ElasticMQ**. It does **not** start `pe-worker` (compose profile `pe`).

### 3. One-time PE setup

Build the PE worker image (first time, or after PE Dockerfile / dependency changes):

```bash
make -C backend/pe build
# or build all workers: cd backend && npm run build-worker
```

Scan targets start a **new container** from the existing `pe-worker` image via the Docker API (same as Crossfeed `ECSClient` local mode). Rebuild only when the Dockerfile or `requirements.txt` changes.

Initialize the PE database (schema + sample orgs):

```bash
make -C backend/pe syncdb-populate
```

This runs `manage.py pesyncdb --populate`, which:

- Creates the `pe` database and `pe` user (via the Crossfeed admin connection)
- Syncs **all PE table models** from `home/models.py` (SQL views named `vw_*` / `mat_vw_*` are skipped)
- Loads `DNSTwist` / `findomain` data sources, sample orgs **DHS** and **DHS_CISA** (`report_on=true`), and root domains `dhs.gov` / `cisa.gov`

After changing models or to pick up newly added tables: `make -C backend/pe syncdb`

To rebuild from scratch: `make -C backend/pe syncdb-dangerously-force` then `syncdb-populate`

### 4. Run a scan

`run` invokes the local **peScanController** (same interface as production Lambda / EC2 `pe_sqs.py`): queue org messages to ElasticMQ, then start detached `pe-worker` containers via the Docker API.

| Parameter  | Make                              | CLI / Lambda              |
| ---------- | --------------------------------- | ------------------------- |
| Scan       | `SCANS=dnstwist`                  | `--scans dnstwist`        |
| Orgs       | `ORGS=DHS` or `ORGS=DHS,DHS_CISA` | `--orgs DHS,DHS_CISA`     |
| Workers    | `COUNT=3`                         | `--count 3` / `taskCount` |
| Queue only | `QUEUE_ONLY=true`                 | `--queue-only`            |

**Org values** — comma-separated `cyhy_db_name` values (e.g. `DHS`, not the full display name).

| ORGS value     | Queue                                        | What runs                                                                                                              |
| -------------- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `DHS,DHS_CISA` | 2 messages (one per org)                     | Each worker scans one org. `COUNT` = concurrent workers.                                                               |
| `all`          | **1 message** (batch)                        | One worker runs `pe-source --orgs=all` and scans every `report_on` org **sequentially in one process**. Use `COUNT=1`. |
| `DEMO`         | **1 message** (batch)                        | Same as `all`, but for demo orgs only.                                                                                 |
| `all-orgs`     | **1 message per** `report_on` org (parallel) | Controller queries the PE DB and enqueues each org separately. Use `COUNT=N` for N concurrent workers.                 |
| `demo-orgs`    | **1 message per** demo org (parallel)        | Same as `all-orgs`, but for demo orgs.                                                                                 |

Use **batch** (`all` / `DEMO`) for a simple single-worker run. Use **parallel** (`all-orgs` / `demo-orgs`) when you want multiple workers draining the queue at once. Do not combine a shortcut with named orgs.

```bash
make -C backend/pe run SCANS=dnstwist ORGS=DHS,DHS_CISA COUNT=2
make -C backend/pe run SCANS=dnstwist ORGS=all COUNT=1
make -C backend/pe run SCANS=dnstwist ORGS=all-orgs COUNT=3
```

Sample orgs fixture (`backend/pe/fixtures/sample-orgs.json`):

```bash
make -C backend/pe scans SCANS=dnstwist COUNT=1
```

Watch worker logs: `docker logs -f pe_worker_dnstwist_<id>`

Workers drain their scan queue and **exit when it is empty** (same pattern as Crossfeed `worker.py`). Rebuild after worker changes: `make -C backend/pe build`.

Queue only (no worker start): `make -C backend/pe queue SCANS=dnstwist ORGS=DHS`

Other targets: `make -C backend/pe help` (`logs`, `test`, etc.)

---

## Connect with DBeaver (local)

With `npm start` running, postgres is exposed on **localhost:5432**.

### PE database

| Field    | Value                                             |
| -------- | ------------------------------------------------- |
| Host     | `localhost`                                       |
| Port     | `5432`                                            |
| Database | `pe`                                              |
| Username | `pe`                                              |
| Password | `password` (or your `PE_DB_PASSWORD` from `.env`) |

In DBeaver: **Database → New Database Connection → PostgreSQL**, enter the values above, **Test Connection**, then **Finish**.

Run `make -C backend/pe syncdb-populate` first so the `pe` database exists.

Useful tables after a populate + scan: `organizations`, `data_source`, `root_domains`, `sub_domains`, `domain_permutations`.

### Crossfeed database (optional)

Same host/port, different database:

| Field    | Value                                          |
| -------- | ---------------------------------------------- |
| Database | `crossfeed`                                    |
| Username | `crossfeed`                                    |
| Password | `password` (or your `DB_PASSWORD` from `.env`) |

### psql (alternative)

```bash
psql -h localhost -p 5432 -U pe -d pe
```

---

## Remote / accessor (non-local)

### Add credentials to SSM

Before deploying. Generate a secure secret value for a database password, then run the following commands on the terraformer instance:

```bash
aws ssm put-parameter --name "/crossfeed/staging/PE_DB_NAME" --value "pe" --type "SecureString"
aws ssm put-parameter --name "/crossfeed/staging/PE_DB_USER" --value "pe" --type "SecureString"
aws ssm put-parameter --name "/crossfeed/staging/PE_DB_PASSWORD" --value "[generated secret password]" --type "SecureString"
```

### Sync DB (accessor)

```bash
aws lambda invoke --function-name crossfeed-prod-pesyncdb --log-type Tail --region us-east-1 /dev/stderr --query 'LogResult' --output text | base64 -d
```

### Remote credentials

```bash
aws ssm get-parameter --name "/crossfeed/staging/DATABASE_HOST" --with-decryption
aws ssm get-parameter --name "/crossfeed/staging/PE_DB_NAME" --with-decryption
aws ssm get-parameter --name "/crossfeed/staging/PE_DB_USER" --with-decryption
aws ssm get-parameter --name "/crossfeed/staging/PE_DB_PASSWORD" --with-decryption
```

### pg_restore (accessor)

```bash
pg_restore -U pe -d pe "[path to sql dump file]"
```
