# OpenCTI VS (VulnScanning) Connector — Planning Doc

Living doc for planning a custom OpenCTI connector that ingests VulnScanning ("VS") data. Update
this as understanding solidifies and as implementation decisions get made — it's meant to track
reality and open questions, not be a one-time snapshot. See also [`open-cti/STATUS.md`](STATUS.md)
for the separate (unrelated) EC2 bootstrap-automation / gov-cloud migration thread.

## 1. What "VS data" actually is

"VS" = CISA's VulnScanning service (Nessus/nmap-based scanning of stakeholder-owned IP space).
The data does **not** come from VS directly — it's synced from **Redshift** into this repo's
Postgres RDS instance, and *that* Postgres copy (`mini_data_lake`) is what the connector will read
from. Chain:

```text
VS scanners --> Redshift (vmtableau schema)  --> [two separate sync tasks] --> RDS Postgres (mini_data_lake DB) --> [new] OpenCTI connectors --> OpenCTI
```

**It's two separate sync tasks, not one** — this matters for the connectors' own scheduling/
dependency assumptions:

- **`VulnScanningSync`**
  ([`vulnScanningSync.py`](../backend/src/xfd_django/xfd_api/tasks/vulnScanningSync.py)) — pulls
  `vmtableau.vuln_scans`, `.port_scans`, `.tickets` from Redshift into `VulnScan`/`PortScan`/
  `LatestPortScan`/`Ticket`. This is the task Connectors A and C ultimately depend on. Notably, it
  does **not** sync organizations itself — it only *reads* already-populated `Organization` rows
  via a plain Postgres lookup
  (`fetch_org_id_dict_fast()` in
  [`vs_requests.py:38`](../backend/src/xfd_django/xfd_api/tasks/utils/vs_requests.py#L38)), on the
  assumption that org sync has already run.
- **`vs_org_sync`** ([`vs_org_sync.py`](../backend/src/xfd_django/xfd_api/tasks/vs_org_sync.py)) —
  the task that *actually* pulls `vmtableau.requests` from Redshift
  (`fetch_orgs_from_redshift()` in
  [`vs_requests.py:29`](../backend/src/xfd_django/xfd_api/tasks/utils/vs_requests.py#L29)) and
  populates/updates `Organization`, `Sector`, `Cidr`/`CidrOrgs`, and `Location`. Same run also
  retires unseen CIDRs (`flag_cidr_changes()`), re-links IPs to CIDRs
  (`bulk_assign_ips_to_cidrs()`), rebuilds `HostSummary`, refreshes `Cidr.live_ips`, and —
  separately from all the Postgres-side work — **pushes org/CIDR/sector data out to a "DMZ" HTTP
  sync endpoint** (`send_organizations_to_dmz()` in
  [`vs_send_orgs_to_dmz.py`](../backend/src/xfd_django/xfd_api/tasks/utils/vs_send_orgs_to_dmz.py)).
  That last step is one-way, outbound, HTTP-based (not a DB replication) — it confirms
  `mini_data_lake` in this (LZ) environment is the canonical source for org data, and the DMZ side
  is a downstream consumer, consistent with where OpenCTI's own DB connectivity already points
  (§2).

Practical implication for the connectors: **Identity (organization) data in OpenCTI is only as
fresh as `vs_org_sync`'s last run, which is an independent schedule from `VulnScanningSync`'s.** A
new/renamed org, or a CIDR change, won't be visible to any of the other three connectors until
`vs_org_sync` has run — worth confirming that cadence alongside `VulnScanningSync`'s (§6, both
still unresolved).

Redshift source tables referenced across both sync tasks (schema `vmtableau`): `requests` (orgs),
`vuln_scans`, `port_scans`, `hosts`, `tickets`. The connectors should **not** talk to Redshift at
all — they only need the `mini_data_lake` Postgres side.

## 2. Where the data lives (connectivity)

- Same RDS instance as the main Crossfeed app DB (`aws_db_instance.db` in
  [`infrastructure/database.tf`](../infrastructure/database.tf)), Postgres 17.9, but a **separate
  database** on that instance: `mini_data_lake` (env var `MDL_NAME`), distinct from the app's
  `crossfeed-stage-db`. See `DATABASES["mini_data_lake"]` in
  [`backend/src/xfd_django/xfd_django/settings.py:145`](../backend/src/xfd_django/xfd_django/settings.py#L145).
- **No read replica exists** — the connector will query the same primary the app and the
  VulnScanningSync bulk-writer use. Worth flagging as a load concern (see §5).
- **IAM DB auth is already scaffolded for OpenCTI specifically**, in
  [`infrastructure/open_cti.tf`](../infrastructure/open_cti.tf):
  - `aws_iam_role_policy.open_cti_rds_iam_auth` grants OpenCTI's EC2 instance role
    `rds-db:connect` scoped to one Postgres role, `var.open_cti_db_username` (default
    `open_cti`), via short-lived IAM auth tokens instead of a static password.
  - `aws_security_group.open_cti_db_access` opens `var.db_port` (5432) from OpenCTI's EC2 SG to
    the DB instance.
  - **Only wired up in the LZ (`!is_dmz`, i.e. gov-cloud `stage`/`prod`) branch** — stage-cd
    (commercial DMZ) currently has *no* DB connectivity of this kind. Per
    [`open-cti/STATUS.md`](STATUS.md) the whole instance is mid-migration from stage-cd into the
    LZ; the VS connector likely only becomes practical to run once that migration lands (or the
    same IAM-auth/SG pattern gets backported to stage-cd).
  - Still needed, out-of-band (not Terraform-managed): the actual `open_cti` Postgres role and a
    `GRANT rds_iam TO open_cti` in the DB itself, plus read grants on whatever `mini_data_lake`
    tables the connector needs. Nothing here yet suggests that grant has been done — confirm
    before assuming connectivity works.
- Auth model for the connector to plan around: **IAM database authentication**, not a static
  password — generate a token per connection (`aws rds generate-db-auth-token`), over TLS
  (required for IAM auth regardless of `rds.force_ssl`). Tokens are short-lived (~15 min), so the
  connector needs to refresh them per-connection/on-reconnect, not cache one long-term.

## 3. Django ORM model = de facto schema reference

The `mini_data_lake` tables are defined as Django models in
[`backend/src/xfd_django/xfd_mini_dl/models.py`](../backend/src/xfd_django/xfd_mini_dl/models.py)
(~7000 lines, `managed = False` in most `Meta` classes — Django doesn't own migrations for this
DB, it's describing an externally-managed schema). This is the fastest way to get accurate column
names/types/nullability without a live DB connection. Core VS-relevant tables:

| Model | `db_table` | PK | Purpose |
|---|---|---|---|
| `VulnScan` | `vuln_scan` | `id` (string) | Raw per-finding vuln scan record (1 row per vuln instance per host/port/time) |
| `VulnScanSummary` | `vuln_scan_summary` | (`summary_date`, `organization`) | Daily rollup per org: severity counts, KEV counts, top CVEs, top risky hosts |
| `Ticket` | `ticket` | `id` (string) | The **stateful** vuln record — open/closed lifecycle, false-positive flag, KEV flag, risky-service flag. Distinct from `VulnScan` (see §4) |
| `TicketEvent` | (n/a, not yet inspected) | — | Presumably ticket state-change history |
| `Host` | `host` | `id` (string) | Per-IP scan-lifecycle metadata (stage, priority, last scan timestamps) |
| `HostSummary` | `host_summary` | (`organization`, `summary_date`) | Daily rollup of host scan status counts per org |
| `PortScan` | `port_scan` | `id` (string) | Raw per-port-scan record |
| `LatestPortScan` | `latest_port_scan` | UUID | Materialized "current open port" per (org, ip, port, protocol) — dedup of `PortScan` |
| `PortScanSummary` / `PortScanServiceSummary` | `port_scan_summary` / `port_scan_service_summary` | (org, date[, service]) | Daily rollups |
| `Ip` | `ip` | UUID | Canonical IP record per org; `ip_hash` used elsewhere for privacy-preserving joins |
| `IpsSubs` | `ips_subs` | UUID | IP ↔ subdomain link table |
| `Cidr` / `CidrOrgs` | `cidr` / `cidr_orgs` | UUID | Org-owned network blocks, used to compute `assets_owned_count` |
| `Cve` | `cve` | UUID | CVE master record — CVSS v2/v3/v4, weaknesses (CWE), references, CNA/ADP JSON blobs |
| `CveSsvc` | (1:1 with `Cve`) | — | SSVC triplet (Exploitation/Automatable/Technical Impact) + ADP provenance |
| `CisaKevCatalog` | `cisa_kev_catalog` | UUID | Full CISA KEV catalog (not VS-specific, but joined against for `is_kev`) |
| `Organization` | `organization` | UUID | Stakeholder org; `acronym` is the join key back to Redshift's `owner`/`_id` fields |
| `RiskyServiceGroup` / `NMIServiceGroup` | — | — | Lookup tables mapping service names to risk categories, applied during sync |

Full field-level detail for the highest-value tables (`VulnScan`, `Ticket`, `Organization`) is in
models.py at:
[`VulnScan` (L1737)](../backend/src/xfd_django/xfd_mini_dl/models.py#L1737),
[`VulnScanSummary` (L2045)](../backend/src/xfd_django/xfd_mini_dl/models.py#L2045),
[`Ticket` (L2846)](../backend/src/xfd_django/xfd_mini_dl/models.py#L2846),
[`Host`/`HostSummary` (L2466)](../backend/src/xfd_django/xfd_mini_dl/models.py#L2466),
[`PortScan`/`LatestPortScan` (L3116)](../backend/src/xfd_django/xfd_mini_dl/models.py#L3116),
[`Organization` (L617)](../backend/src/xfd_django/xfd_mini_dl/models.py#L617),
[`Cve`/`CveSsvc` (L255)](../backend/src/xfd_django/xfd_mini_dl/models.py#L255).

## 4. `VulnScan` vs `Ticket` — the key modeling distinction

This matters a lot for connector design (what becomes an OpenCTI Vulnerability/Observation vs.
what becomes a Case/Incident-style stateful object):

- **`VulnScan`** — near-raw scanner output. One row per detection event; carries plugin
  metadata, CVSS vectors (v2 + v3), solution text, exploit-availability flags, `latest` boolean.
  No open/closed lifecycle of its own.
- **`Ticket`** — CyHy's derived, stateful notion of "this vulnerability, on this host, is
  currently a problem." Has `is_open`, `opened_timestamp`/`closed_timestamp`, `false_positive`,
  `is_kev`/`is_kev_ransomware`, `is_risky`, `vuln_source` (`"nessus"` vs `"nmap"` — i.e. vuln scan
  vs port scan derived tickets). **`VulnScanSummary` is built almost entirely from `Ticket`, not
  `VulnScan`** — see `create_vuln_scan_summary()` in
  [`vs_vuln_scans.py:322`](../backend/src/xfd_django/xfd_api/tasks/utils/vs_vuln_scans.py#L322),
  which filters `Ticket` on `is_open=True, false_positive in (False, None), vuln_source="nessus"`
  as its base "included" set.
- **Decision (2026-08-25): split into two connectors along exactly this line** rather than picking
  one table — see §7 for the full architecture. `Ticket` drives ingestion, `VulnScan` drives
  enrichment.

## 5. Sync cadence / freshness / write pattern (informs polling design)

- `VulnScanningSync` runs on a fixed window, not full-table: default `VS_PULL_DATE_RANGE=2` days,
  computed via `freeze_window()` in
  [`datetime_utils.py:69`](../backend/src/xfd_django/xfd_api/tasks/utils/datetime_utils.py#L69)
  (midnight UTC to midnight UTC, so there's a rolling window, not "since last run" tracking).
  Could not find the CloudWatch/EventBridge schedule expression for how often this task itself
  fires — only found a CloudWatch dashboard widget referencing it
  ([`cloudwatch_dashboards.tf:392`](../infrastructure/cloudwatch_dashboards.tf#L392)). **Open
  item: find the actual schedule** (likely daily, given the 2-day window) before assuming how
  fresh `mini_data_lake` is at any given moment.
- Writes are bulk (`bulk_create(..., ignore_conflicts=True)`), chunked (10k row chunks for vuln
  scans, keyset-paginated from Redshift), and organization-scoped per run
  (`org_list`/`org_id_dict` passed into the task event). This means the connector could see
  large bursts of new/updated rows within short windows right after a sync run, not a steady
  trickle — relevant for polling interval / batch-size choices.
- No explicit "updated_at" watermark column on `VulnScan` itself (`vuln_detection_timestamp` is
  the closest thing — mirrors Redshift's `time` column). `Ticket.updated_timestamp` and
  `PortScan.time_scanned` / `LatestPortScan.time_scanned` are the more reliable incremental-sync
  anchors.
- **Verified: no hard deletes.** Grepped the task codebase for `.delete()` calls against `Ticket`,
  `VulnScan`, `PortScan`/`LatestPortScan` — none exist (the only model-deletion patterns found
  anywhere in `xfd_api/tasks/` are unrelated: `ScanResult` pruning, `CisaKevCatalog`'s own
  truncate-and-reload, `Blocklist`/`User` cleanup). This matters because it rules out the one
  failure mode a pure timestamp-watermark poll genuinely can't handle — a row vanishing outright
  between polls with no trace. Connector A and C's incremental strategies (§7a, §7c) only have to
  account for state *transitions* (open→closed, current→stale), not disappearance, and that's now
  a checked assumption rather than an implicit one.

## 6. Constraints & open questions to resolve before designing the connector

#### Connectivity / access

- [ ] Confirm the `open_cti` Postgres role + `GRANT rds_iam TO open_cti` actually exist in
  `mini_data_lake` today (Terraform only creates the *IAM* side of this grant, not the DB-side
  role — see §2).
- [ ] Confirm which environment (stage-cd DMZ vs. LZ stage/prod) the connector is meant to target
  first — DB connectivity as currently built only exists in the LZ branch.
- [ ] Decide connector auth refresh strategy for IAM tokens (~15 min TTL) — connection-pooling
  approach matters here (a long-lived pool needs per-checkout token refresh, not a single token
  reused for the pool's lifetime).

#### Data scope / modeling

- [x] `Ticket` vs `VulnScan` as the primary sync source (§4) — resolved by splitting into two
  connectors, see §7.
- [ ] Multi-tenancy: does the connector pull VS data for *all* organizations, or a filtered subset
  (e.g. only orgs with `vs_stakeholder=True` and `retired=False` on `Organization`)? All the sync
  task's own org-scoping happens by list of org acronyms passed in per Lambda invocation — the
  connector will need its own equivalent org-selection logic against `Organization`.
- [ ] KEV overlay: `CisaKevCatalog` is a separate table joined in only at summary-build time
  (`Ticket.is_kev`) — decide whether the connector re-derives/join this itself or trusts the
  already-flagged `Ticket.is_kev` / `is_kev_ransomware` columns.
- [ ] CVE enrichment: `Cve`/`CveSsvc` carry CVSS v2/v3/v4 + SSVC + CNA/ADP raw JSON — decide how
  much of this rides along vs. being left to OpenCTI's own CVE/NVD connectors to fill in
  (potential duplicate-enrichment risk if both write CVE objects).
- [ ] Several fields in the model have literal `"????"`/`"??????"` help text (e.g.
  `VulnScan.cisa_known_exploited`, `.asset_inventory`, `.cisco_bug_id`, `.cisco_sa`,
  `WasFindings.potential`) — meaning is genuinely unclear even to whoever wrote the model
  docstrings; don't build connector logic that depends on these without checking real data first.

#### Load / operational

- [ ] No read replica exists (§2) — querying `mini_data_lake` from the connector hits the same
  primary the app and the bulk sync writer use. Needs a load-conscious query pattern (indexed
  incremental pulls, not table scans) — see indexes already defined on `Ticket`
  (`tickets_is_open_idx`, `ticket_last_seen_idx`) and `PortScan`/`LatestPortScan` for what's cheap
  to filter on today.
- [ ] Actual `VulnScanningSync` **and** `vs_org_sync` schedule/cadence (§1, §5) — both unresolved.
  `vs_org_sync` populates `Organization`/`Cidr`/`Sector` independently of `VulnScanningSync`, so
  Identity freshness in OpenCTI depends on finding *that* cadence too, not just the ticket/scan
  one.
- [ ] Confirm the acronym-based External Reference contract in §7d actually resolves reliably —
  i.e. no pre-existing OpenCTI Identities for these orgs already exist under a *different* key
  (e.g. from manual analyst entry) that Connector D's upserts would end up duplicating instead of
  matching.
- [ ] Check the actual overlap between CISA's ~20 VS sector acronyms/country-state `Location`
  values and whatever `connector-opencti` (the built-in "Datasets" connector, already running —
  see §7d) seeded by default. Decide the name-matching rule Connector D uses to reuse existing
  `Identity`(sector)/`Location` objects instead of creating a parallel taxonomy.
- [ ] Data volumes: not yet measured. Need row counts / growth rate on `vuln_scan`, `ticket`,
  `port_scan` before deciding batch sizes.
- [ ] Connector C specifically: confirm whether a full-table poll of `LatestPortScan` per run
  (needed to catch `current` flipping `False` without a timestamp change — see §7c) stays cheap.
  `LatestPortScan` is bounded to one row per `(org, ip, port, protocol)` rather than growing
  per-scan-event like `PortScan`, but the actual row count across all in-scope orgs isn't known yet.

## 7. Connector architecture: four connectors

Splitting `Ticket` (vulnerability ingestion), `VulnScan` (enrichment), `LatestPortScan`
(port/service inventory ingestion), and now `Organization`/`Sector`/`Cidr`/`Location` (org/CIDR
bootstrap) into four separate connectors instead of one monolithic one. This isn't just a
data-source split — it maps cleanly onto OpenCTI's own connector-type taxonomy, and mirrors what's
**already running in this exact deployment**: see
[`open-cti/docker-compose.yml`](docker-compose.yml) — `connector-cisa-known-exploited-vulnerabilities`
(L392) and `connector-vulncheck` (L378) are `EXTERNAL_IMPORT` connectors that poll a source on a
schedule and create/update STIX objects; `connector-qualys-cve-enrichment` (L408) and
`connector-censys-enrichment` (L362) are `INTERNAL_ENRICHMENT` connectors that decorate an
already-existing entity on demand. Our four connectors are the same two shapes (three
`EXTERNAL_IMPORT`, one `INTERNAL_ENRICHMENT`), pointed at `mini_data_lake` instead of a
third-party API.

**At a glance:**

| | **A — Ticket Ingestion** | **B — VulnScan Enrichment** | **C — Port/Service Inventory** | **D — Org/CIDR Bootstrap** |
|---|---|---|---|---|
| **Type** | `EXTERNAL_IMPORT` | `INTERNAL_ENRICHMENT` | `EXTERNAL_IMPORT` | `EXTERNAL_IMPORT` |
| **Reads** | `Ticket` | `VulnScan` (per-entity lookup) | `LatestPortScan` | `Organization`, `Sector`, `Cidr`/`CidrOrgs`, `Location` |
| **Trigger** | Scheduled, incremental on `COALESCE(closed_timestamp, updated_timestamp)` | Manual "Enrich" / auto on A's entities | Scheduled, full-table diff per run (§7c) | Scheduled, slow cadence, incremental on `Organization.updated_at` |
| **Creates** | `IPv4-Addr`/`IPv6-Addr`; `Vulnerability` | `Note` only | Reuses A's IP; `Network-Traffic`; `Software` | `Identity` (organization + sector); `Location`; `IPv4-Addr`/`IPv6-Addr` (CIDR-notation) |
| **Depends on** | Connector D (org Identity must exist) | Connector A (entity to enrich must exist) | Connector D (org Identity must exist) | Nothing — this is the root of the dependency chain |

### 7a. Connector A — VS Ticket Ingestion (`EXTERNAL_IMPORT`)

**Source:** `Ticket` table, scoped by org and by `is_open` / recency.

**Trigger/cadence:** Polls on a schedule (`CONNECTOR_DURATION_PERIOD`, same knob
`connector-cisa-known-exploited-vulnerabilities` uses, currently `P1D` there). Should not poll
tighter than `VulnScanningSync`'s own cadence (§5, still unresolved) — no point checking for
updates more often than the source data actually changes.

**Incremental strategy:** Use OpenCTI's built-in connector state store (`helper.get_state()` /
`set_state()`, keyed by `CONNECTOR_ID` — no separate watermark table needed on our side) to track
the last-seen high-water mark, and query `Ticket` on `COALESCE(closed_timestamp,
updated_timestamp)` — already indexed as `ticket_last_seen_idx`
([`models.py:3044`](../backend/src/xfd_django/xfd_mini_dl/models.py#L3044)). This also means a
ticket flipping *open → closed*, or *not-false-positive → false-positive*, shows up naturally as
an "updated" row on the next poll — the connector doesn't need separate logic to detect closures,
just to react to them (see idempotency below).

**STIX mapping (per ticket):**

- `IPv4-Addr` / `IPv6-Addr` observable for `ip_string`.
- `Vulnerability` SDO keyed by `cve_string` when present — **but minimal: name only, no CVSS/
  description of our own.** [`docker-compose.yml`](docker-compose.yml)'s `connector-cve` (L338) is
  already running continuously (`CVE_INTERVAL=2` hours, `MAINTAIN_DATA=true`, NVD-sourced back to
  `CVE_HISTORY_START_YEAR=2019`) — by the time Connector A sees a `cve_string`, a `Vulnerability`
  for that CVE almost certainly already exists (or will shortly), created and kept current by
  `connector-cve`. A bare-minimum upsert naturally resolves to the same object rather than forking
  a second, VS-flavored copy of the same CVE's data — same "additive, not overwriting" principle
  §7b already applies to Connector B, just realized here as "don't populate it at all," since
  there's a dedicated connector whose whole job is keeping this object's CVSS/description current
  from the authoritative source. For CVE-less tickets (e.g. `nmap`-sourced risky-service tickets,
  `vuln_source="nmap"`), still create a `Vulnerability` named from `vuln_name`/`service_name` rather
  than skipping the ticket — STIX `Vulnerability` doesn't require a CVE ID, and there's no
  `connector-cve` equivalent for these to defer to.
- `Identity` (organization, class `organization`) resolved by `acronym` via the External Reference
  Connector D creates (§7d) — **look up, don't blindly create**. Sourced from a *different* task
  than the rest of this connector's data — see §1 on `vs_org_sync` — so treat org/CIDR freshness as
  its own dependency, owned by Connector D, not something `VulnScanningSync` keeps current as a
  side effect.
- Relationship (SRO) connecting the IP observable to the `Vulnerability`, carrying the ticket's
  lifecycle as native SRO fields rather than inventing a new container object: `start_time` =
  `opened_timestamp`, `stop_time` = `closed_timestamp` (omitted while open). Severity
  (`cvss_severity` → low/medium/high/critical), `is_kev`, `is_kev_ransomware`, `is_risky`,
  `vuln_source` become labels; an `External Reference` with `source_name="VS"`,
  `external_id=Ticket.id` for our own bookkeeping. **Correction from an earlier version of this
  doc:** the External Reference does *not* itself make the relationship idempotent — see §10 for
  what actually does and what to build instead.
- **False positives:** don't ingest tickets already `false_positive=True`. If a previously-ingested
  ticket flips to `false_positive=True` on a later poll, revoke (or delete) its relationship rather
  than leaving a stale "still vulnerable" edge in the graph.

**Case/Incident decision — recommendation: don't use one.** Model tickets as the
observable/Vulnerability/relationship graph above, with no `Case-Incident`/`Case-RFI` container in
the loop. Reasoning:

- None of the connectors already running in this stack use Cases — Cases in OpenCTI are meant for
  analyst-tracked investigations with a bounded scope, and CyHy tickets can number in the
  thousands and stay open for months, which would flood the Case list rather than help an analyst.
- SRO `start_time`/`stop_time` already model the open/close lifecycle natively — a Case adds a
  second, redundant place to track the same state and a second thing to keep in sync.
- If org-level analyst-facing rollups are wanted later (a periodic "here's this org's vuln posture"
  digest), that's better sourced from `VulnScanSummary` — which already *is* that rollup, built
  daily by the existing sync task (§3/§4) — as a **separate, later** connector or report generator,
  not folded into raw per-ticket ingestion. Flagging this as a phase-2 idea, not in scope now.
- Open to revisiting if you have a specific analyst workflow in mind that needs a Case — flag it
  and we can design around it, but there's no default reason to add one here.

### 7b. Connector B — VulnScan Enrichment (`INTERNAL_ENRICHMENT`)

**Source:** `VulnScan` table, looked up per-entity rather than polled wholesale.

**Trigger:** `CONNECTOR_SCOPE` on the `Vulnerability` and/or `IPv4-Addr`/`IPv6-Addr` types Connector
A creates (mirrors `connector-censys-enrichment`'s
`CONNECTOR_SCOPE=IPv4-Addr,IPv6-Addr,X509-Certificate,Domain-Name`). Every existing enrichment
connector in this deployment runs `CONNECTOR_AUTO=false` (manual "Enrich" trigger in the OpenCTI
UI, not automatic on every entity write) — recommend matching that convention to start, since
auto-triggering enrichment on every one of Connector A's writes means one `VulnScan` lookup per
ticket per poll, hitting the same primary DB Connector A just queried. Can revisit once real data
volume (§6) is known.

**Behavior:** Given a triggered entity (an IP, or a Vulnerability/CVE), query `VulnScan` by
`ip_string` (+ `cve_string` when scoped to a specific Vulnerability) and surface scanner-level
detail: CVSS v2/v3 vectors, `plugin_name`/`plugin_id`/`plugin_family`, `solution`, `synopsis`,
`description`, `exploit_available`/`exploitability_ease`, `risk_factor`, and `see_also`/`xref` as
external references.

**Output shape — additive, not overwriting:** write enrichment as a `Note` attached to the
triggered entity (same pattern Qualys/Censys enrichment connectors use), rather than mutating the
`Vulnerability` SDO's own CVSS fields directly. This resolves the "duplicate enrichment" concern
in §6 — `connector-vulncheck` and `connector-qualys-cve-enrichment` already write to `Vulnerability`
objects for CVE data; Connector B shouldn't clobber that by overwriting the same fields with VS's
Nessus-flavored numbers. If a field is genuinely worth promoting onto the SDO itself (e.g.
`exploit_available` if no other connector supplies it), that's a targeted, individually-justified
addition, not a blanket overwrite policy.

**Dependency note:** Connector B only has something to enrich once Connector A (or some other
process) has created the `Vulnerability`/observable in the first place — it's not a standalone
ingestion path.

### 7c. Connector C — VS Port/Service Inventory (`EXTERNAL_IMPORT`)

**Source:** `LatestPortScan` — deliberately **not** raw `PortScan` (an unbounded, append-only scan
history log). `LatestPortScan` is already deduped to one row per `(organization, ip, port,
protocol)` by the sync task's own upsert
([`insert_port_scans_sql()`](../backend/src/xfd_django/xfd_api/tasks/utils/vs_port_scans.py#L230)),
so it's the "current state of the world" table — exactly the shape an inventory-style connector
wants, and much cheaper to poll than the raw log.

**Why this is a separate connector from 7a, not folded into it:** `Ticket` already captures a
*curated subset* of port-scan findings — rows where `vuln_source="nmap"` and `is_risky=True`
(service name matched `"Potentially Risky Service Detected:"`, see
[`vs_tickets.py:316`](../backend/src/xfd_django/xfd_api/tasks/utils/vs_tickets.py#L316)) already
flow into OpenCTI via Connector A as `Vulnerability` relationships. Connector C's job is the
**complementary full inventory** — every open port/service, risky or not — which is a materially
different STIX shape (network/asset exposure, not vulnerability findings) and, as below, a
different incremental-sync strategy. Keeping them separate keeps each connector's polling/diffing
logic single-purpose, matching this deployment's existing one-connector-per-concern convention;
they can still share a small internal helper module (e.g. "resolve org Identity," "get-or-create
IP observable") without merging into one process.

**Incremental strategy — cannot be a simple timestamp watermark, unlike Connector A.** This is the
important gotcha: a port going stale is driven by
[`mark_stale_latest_port_scans()`](../backend/src/xfd_django/xfd_api/tasks/utils/vs_port_scans.py#L771),
which flips `current` to `False` after 14 days (`LATEST_PORT_SCAN_CUTOFF`) **without touching
`time_scanned`**. A pure `WHERE time_scanned > last_watermark` poll would never see that
transition, and the connector would keep reporting a closed port as open indefinitely. Recommended
approach instead: since `LatestPortScan` is bounded (one row per unique key, not per scan event),
**poll the full current-scope table each run** — all `LatestPortScan` rows for in-scope
organizations — and diff against the connector's own last-known `(org, ip, port, protocol) →
current` map (kept in OpenCTI connector state) to compute newly-opened / still-open / newly-closed
per run, rather than relying on `time_scanned` as a change indicator. Needs the row-count question
in §6 answered to confirm "full poll per run" stays cheap as org coverage grows.

**Note on first-seen:** `LatestPortScan` only retains the *latest* `time_scanned` for a key (it's
an upsert target), not a first-observed timestamp. The connector needs to preserve `start_time` on
the OpenCTI-side relationship itself once set (only write it on first creation of that key, never
overwrite on subsequent updates) — the source table can't supply "first seen" after the fact.

**STIX mapping (per `LatestPortScan` row):**

- Reuses the same `IPv4-Addr`/`IPv6-Addr` observable Connector A creates — STIX SCOs for these
  types get deterministic, value-derived IDs, so OpenCTI naturally merges them into the same
  object with no coordination code needed between the two connectors.
- `Network-Traffic` SCO per `(ip, port, protocol)`: `src_ref` = the IP observable, `src_port` =
  `port`, `protocols` = `[protocol]` (kept to valid IANA-style tcp/udp values — `service_name` is
  often not a valid STIX protocol string, so it goes on a label/description instead, not crammed
  into `protocols`).
- `Software` SCO when `service_product`/`service_version`/`service_cpe` are present — `service_cpe`
  maps directly onto STIX `Software.cpe`, `service_product`/`service_version` onto `name`/`version`.
  Related to the `Network-Traffic` object via a relationship (STIX 2.1 allows SROs between SCOs).
- Labels reused verbatim from the same fields `Ticket` also carries (`risky_service_group`,
  `nmi_service_group`, `source`, `state`) — keeps filtering/labeling consistent between what
  Connector A and Connector C both produce.
- Relationship lifecycle: `start_time` set once (see above), `stop_time` set once `current` flips
  to `False` on a poll (using that poll's run time, since the source itself doesn't timestamp the
  transition either). Same idempotency caveat as Connector A — see §10 for the actual mechanism to
  rely on.
- Same organization-`Identity` resolution/reuse pattern as Connector A — resolved by `acronym` via
  Connector D's External Reference (§7d).

**Out of scope for now:** `PortScanSummary`/`PortScanServiceSummary` (daily org rollups) — same
"phase 2, seed a rollup/Case from the existing summary tables" bucket as `VulnScanSummary` in §7a,
not part of raw inventory ingestion.

### 7d. Connector D — VS Organization & CIDR Bootstrap (`EXTERNAL_IMPORT`)

**Why this exists:** Connectors A and C both resolve an org `Identity` by "look up, don't create,"
which was only ever an assumption that one exists. Nothing owned actually creating/maintaining it
from VS's own org data. This connector is that owner — and the root of the dependency chain: A and
C both need it to have run at least once for a given org before their own polls produce anything
useful.

**Source:** `Organization`, `Sector`, `Cidr`/`CidrOrgs`, `Location` — all populated by `vs_org_sync`
from Redshift's `vmtableau.requests` (§1). Like the other connectors, this one only reads
`mini_data_lake`; it never talks to Redshift.

**Cadence — deliberately slower than A/B/C:** org/sector/CIDR data is reference data (stakeholder
onboarding, network ownership) that churns far less often than scan findings. Unlike `Ticket`/
`LatestPortScan`, `Organization` actually has a plain `updated_at` auto-now column
([`models.py`](../backend/src/xfd_django/xfd_mini_dl/models.py#L630-634)) — no watermark gotchas
here, a simple `updated_at > last_watermark` poll works. `Sector` has no timestamp at all, but it's
a small, low-cardinality table (CISA's sector taxonomy, ~20 rows) — cheap to poll in full every run
rather than tracking incrementally. `CidrOrgs.last_seen`/`current` mirrors the same open/closed
pattern `Ticket.is_open` and `LatestPortScan.current` use, for detecting a CIDR no longer claimed
by an org.

**STIX mapping:**

- `Organization` → `Identity` (class `organization`): `name` = `Organization.name`. Use
  `acronym` as the durable join key — carried as an `External Reference`
  (`source_name="VS"`, `external_id=Organization.acronym`) on the Identity, the same
  idempotency pattern Connector A uses for tickets — so Connectors A/C can resolve "the Identity
  for org X" by that stable reference instead of fuzzy-matching on `name` (which can drift in
  formatting; `acronym` is the actual join key this whole data model already keys on, e.g.
  `fetch_org_id_dict_fast()`). Labels for `stakeholder`/`retired`/`vs_stakeholder`-equivalent
  flags. `Organization.parent` → a `part-of` relationship from child Identity to parent Identity.
- `Sector` → `Identity` (class `sector`): `name`, `acronym` as its own External Reference. Each
  member org gets a `part-of` relationship from its Organization Identity to the Sector Identity
  (from the `Sector.organizations` M2M). **Collision risk found:**
  [`docker-compose.yml`](docker-compose.yml)'s `connector-opencti` (L430, `CONNECTOR_SCOPE=
  marking-definition,identity,location`) is OpenCTI's own built-in "Datasets" connector, and it
  already seeds a default set of `identity` (including generic sectors) and `location` objects on
  install. There's a real chance CISA's ~20 VS sector acronyms substantially overlap with whatever
  generic sector taxonomy that connector already seeded. **Look up by name before creating** — a
  duplicate parallel sector taxonomy is worse than reusing what's already there — and confirm the
  actual overlap during ground-truthing (§8) rather than assuming either way.
- `Location` → OpenCTI `Location` entity (country/administrative-area, per STIX 2.1's location
  extensions OpenCTI supports), built from `country`/`country_abrv`/`state`/`state_abrv`/`county`.
  Related to the Organization Identity via `located-at`. Low cardinality (one per `gnis_id`) —
  resolve/create as a side effect of processing each org row rather than polling `Location`
  independently. Same collision risk as `Sector` above — `connector-opencti` likely already seeded
  country-level `Location` entities; look up (e.g. by country/state name) before creating.
- `Cidr` → `IPv4-Addr`/`IPv6-Addr` observable using the CIDR-notation value directly (STIX 2.1
  explicitly allows a CIDR block as an address SCO's `value`, e.g. `"198.51.100.0/24"` — no custom
  observable type needed). Related to the Organization Identity (`related-to`/an "owns"-flavored
  relationship), with `start_time` = `CidrOrgs.first_seen` and `stop_time` set once
  `CidrOrgs.current` flips to `False` (retired) — same lifecycle-via-SRO pattern as Connectors A
  and C, kept consistent across all three ingestion connectors rather than inventing a fourth way
  to represent "still active vs. no longer." Same idempotency caveat as A/C — see §10.

**Resilience note:** given A/C's own polls could in principle run before D has ever seen a
brand-new org, consider a defensive fallback in A/C — if an Identity lookup-by-acronym misses,
create a minimal placeholder Identity (acronym + name only) rather than dropping the
ticket/port-scan row, and let D's next run enrich it fully via the same upsert-by-External-Reference
path. Avoids a hard ordering dependency turning into dropped data if schedules ever drift.

## 8. Recommended build order: D → A → B → C

Dependency graph is simple — D has no dependencies, A and C both depend on D, B depends on A:

```text
        ┌── A (Ticket Ingestion) ──── B (VulnScan Enrichment)
D ──────┤
(Org/CIDR)   └── C (Port/Service Inventory)
```

That graph alone only forces D first and B after A — it leaves A-vs-C and B-vs-C open. Recommended
sequence, and why it's **D → A → B → C** rather than, say, D → A → C → B:

1. **D — Org/CIDR Bootstrap.** Nothing else can produce a correctly-linked object until stakeholder
   `Identity`/`Location`/`Sector` data exists. Also the lowest-risk connector to build first:
   simple `updated_at` watermark (§7d), no timestamp gotchas like A/C have. Its output (the
   acronym-keyed External Reference convention) is a contract every other connector consumes, so
   getting it right early matters more than getting to A or C fast.
2. **A — Ticket Ingestion.** The actual point of this whole effort — open, actionable
   vulnerabilities in OpenCTI. Straightforward incremental strategy (timestamp watermark, no
   gotchas — see the "verified: no hard deletes" note in §5) makes it the natural second build.
3. **B — VulnScan Enrichment.** Small, additive, and low-risk (writes `Note`s, touches nothing
   else) — and building it right after A closes the loop on a **complete, useful, shippable
   vertical slice** (org data → open vulns → enriched detail) before taking on C's structurally
   different, harder problem. Validating the Identity/Vulnerability graph actually enriches
   cleanly here also de-risks C, which reuses the same Identity-resolution and IP-observable
   patterns.
4. **C — Port/Service Inventory.** Saved for last on purpose: it's the one connector whose
   incremental strategy isn't a simple timestamp watermark (§7c's full-poll-per-run diff to catch
   `current` flipping without a timestamp change) and whose row-count/performance question (§6)
   is still open. Better to tackle that novel piece once the team has already shipped two
   watermark-style connectors (D, A) and has real production experience with this DB and OpenCTI's
   connector-state store to lean on.

**Legitimate alternative:** if full asset-inventory coverage matters more up front than enrichment
depth, C and B can swap — both only depend on A/D, not on each other, so D → A → C → B is equally
valid dependency-wise. The order above is a value/risk call, not a hard constraint; revisit if
priorities differ.

## 9. Development & testing workflow

The concern driving this section: nothing in the platform stops a connector from flooding the
queue. `rabbitmq.conf` sets `max_message_size = 536870912` (512MB) and `consumer_timeout =
86400000` (24 hours for the `worker` service to ack one message) — RabbitMQ will happily accept
and sit on a huge bundle. The `worker` service (`docker-compose.yml`, L194) runs 3 replicas total,
shared across *every* connector in the stack, not just ours — a runaway pull during dev doesn't
just slow our own iteration, it eats capacity from whatever else is running. Nothing here is a
platform guardrail; it has to be connector-side discipline, built in from the start rather than
bolted on.

### 9a. Reuse this codebase's own convention: `IS_LOCAL` fixture mode

This isn't a new idea to introduce — it's already the house style. `IS_LOCAL` is checked in
*nearly every* sync task in this repo (`vulnScanningSync.py`, `vs_org_sync.py`, `vs_requests.py`,
`vs_port_scans.py`, `vs_vuln_scans.py`, and a dozen unrelated tasks besides). Concretely, in
[`query_redshift.py:136-169`](../backend/src/xfd_django/xfd_api/tasks/utils/query_redshift.py#L136),
`fetch_from_redshift()`/`fetch_from_redshift_with_params()` short-circuit under `IS_LOCAL` to
`load_test_data()`, which loads a small canned JSON sample per dataset instead of ever touching
Redshift.

Our four connectors should do the exact same thing against `mini_data_lake`: an `IS_LOCAL`- (or
`CONNECTOR_LOCAL_FIXTURES`-) gated mode that loads a handful of representative `Ticket`/
`LatestPortScan`/`Organization`/`Cidr` rows from small local JSON fixture files instead of
querying Postgres at all. Zero DB connection, zero IAM token, zero network — the fastest possible
loop for iterating on the row→STIX mapping logic, which is where most connector bugs will
actually live.

Getting the fixtures: capture them as part of the ground-truthing session already planned (§10
step 1) — one supervised, capped pull (`LIMIT 10`, one or two known low-volume test orgs) from
each source table, saved as JSON. This is real government vuln-scanning data even at 10 rows —
review before committing anything derived from it to the repo, same as any other sample-data
handling on this program.

### 9b. Three separate test loops, from fastest/cheapest to slowest/most-real

Keeping these distinct (rather than always testing end-to-end) is what actually protects the
queue, because only the last one touches RabbitMQ at all:

1. **Pure unit tests — no I/O.** Structure each connector's row→STIX mapping as pure functions
   (a Postgres row dict in, `stix2` objects out). Test against the §9a fixtures. No DB, no
   OpenCTI, no queue. This is where the bulk of iteration should happen — instant feedback,
   run on every save.
2. **Dry-run against real data — no queue writes.** A `CONNECTOR_DRY_RUN` mode that runs the real
   poll-and-map pipeline against a scoped/capped `mini_data_lake` query (see §9c), but writes the
   resulting STIX bundle to a local JSON file (or just logs it) instead of calling the OpenCTI
   helper's bundle-submission step — the actual point where a message would hit RabbitMQ. Validates
   real column types/data quirks against production data shapes without ever touching the queue.
3. **Real submission — capped and scoped, never "everything."** Only after 1 and 2 look right,
   actually run the connector against a real OpenCTI instance — but always through the scoping
   levers in §9c, never a bare unscoped run during development.

### 9c. Scoping levers to build in from day one, not bolt on later

- **Org allowlist** (`CONNECTOR_VS_TEST_ORG_ACRONYMS` or similar), comma-separated — mirrors the
  `org_list` parameter `VulnScanningSync` itself already accepts per invocation. Dev/staging config
  pins this to one or two known low-volume orgs; empty/unset = full production scope. Every
  connector (A/C/D) should take this from day one, not as an afterthought.
- **Hard row cap** (`CONNECTOR_MAX_ROWS_PER_RUN`) as a second, independent safety net — so a bug in
  org-scoping logic can't turn into an accidental full-table pull.
- **Lookback override** for Connector A's incremental poll — force a short window (e.g. "last
  hour") during dev instead of picking up whatever backlog has accumulated since the connector
  state was last reset. Matters especially the first time a fresh connector state points at a real
  environment.
- **Connector C needs this most.** Its whole strategy (§7c) is "poll everything in scope, diff
  against last-known state" — without a tight org allowlist, *every single manual dev run*
  re-pulls and re-diffs the entire `LatestPortScan` table for every org. This is the sharpest
  version of the risk being guarded against here; C should refuse to run with an empty org
  allowlist outside of `CONNECTOR_AUTO`-style production config, not just default to "all orgs."

### 9d. Don't point early dev at the shared instance's queue

`open-cti/docker-compose.yml` already runs a complete, self-contained stack (OpenCTI platform +
Redis + Elasticsearch + MinIO + RabbitMQ + workers), with both the platform (`${OPENCTI_PORT}`)
and RabbitMQ's management UI (port 15672, `rabbitmq:4.3-management` image) published to the host.
That means a disposable local stack — `docker compose up` against this same compose file, pointed
at throwaway local containers instead of the real EC2 instance — is already one command away, and
`docker compose down -v` is a clean, total reset (wipes RabbitMQ/OpenCTI/Elasticsearch state
entirely) between iterations. No local-dev override file for `open-cti/` exists yet (unlike the
main app's `docker-compose.override.local.yml`) — worth adding one so this isn't reinvented each
time.

Recommend defaulting to that local stack for the bulk of connector development (loops 2 and 3 in
§9b), and reserving the real EC2 instance for the things a local stack genuinely can't
replicate — namely testing actual IAM DB-auth connectivity to `mini_data_lake` (§2) once that's
wired up. When the shared instance is unavoidable, keep the §9c scoping caps engaged for every run
and watch the RabbitMQ management UI (already enabled, no setup needed) for queue depth so a
runaway push gets caught immediately rather than silently backing up the 3-replica `worker` pool
other connectors also depend on.

## 10. Connector-side implementation discipline

"Nothing protects the queue except connector-side discipline" (§9) is really a statement about
correctness generally, not just queue safety — most of what follows is the same handful of
principles applied to idempotency, DB load, and error handling, not a new topic each time.

### 10a. Idempotency — corrected, and more specific than "attach an External Reference"

An earlier version of this doc claimed an `External Reference` makes a relationship idempotent
across re-syncs. Checked that against
[OpenCTI's actual deduplication rule](https://docs.opencti.io/latest/usage/deduplication/) and
it's not quite right, which matters a lot here since all three ingestion connectors' lifecycle
modeling (open→closed, current→stale, active→retired) lives entirely on relationships:

- **What OpenCTI actually keys relationship dedup on:** `relationship_type` + `source_ref` +
  `target_ref` + `start_time` (±30 days) + `stop_time` (±30 days) — a fuzzy windowed match. The
  External Reference we attach is bookkeeping metadata; it plays no role in whether a resubmission
  merges into an existing relationship or creates a new one.
- **The fuzzy window is fine for the common case** (any poll cadence in the daily-ish range this
  plan assumes throughout), but **the null→set `stop_time` transition specifically — a ticket open
  for months, then finally closing — isn't clearly documented at that boundary.** Not something to
  assume either way; verify it empirically against a real OpenCTI instance (the dry-run/local-stack
  loop in §9b/§9d is exactly for this) before Connector A ships, since that transition is the single
  most common lifecycle event all three ingestion connectors need to get right.
- **The robust pattern, independent of how the fuzzy window actually behaves:** each connector
  persists its own `(external key → OpenCTI object ID)` map in connector state — `Ticket.id →`
  relationship ID for A, the `(org, ip, port, protocol)` key `→` relationship ID for C,
  `Organization.acronym`/`Cidr.network` → `Identity`/observable ID for D — and explicitly updates
  the known object (via the STIX ID pycti returns on creation, or a GraphQL lookup by the External
  Reference already attached) rather than resubmitting blind and hoping the platform's fuzzy match
  finds it. Costs little to build in from the start and turns an assumption into a guarantee.
- SCOs (`IPv4-Addr` etc.) are the one type this doc's dedup claims (§7c) can stay confident about
  as written — deterministic per the STIX 2.1 spec itself, not an OpenCTI-specific behavior. SDOs
  (`Vulnerability`, `Identity`) use OpenCTI's own content-based "ID contributing properties" per
  type — generally reliable, but confirm per-type rather than assuming it extends to every field
  we might set, the same way relationships turned out to need a closer look.

### 10b. Bundle construction — use what pycti already provides, confirm rather than assume its defaults

pycti's client ships bundle-splitting (`OpenCTIStix2Splitter`, used internally by
`send_stix2_bundle()`) — capping bundle size isn't something to hand-roll. What to actually do:
confirm its default thresholds/behavior against the pycti version this stack pins (couldn't pin
that down from public docs alone) before assuming it does the right thing unconfigured. Separately,
**keep DB page/chunk size and STIX-bundle size as two independent knobs** — how many rows a
connector pulls from `mini_data_lake` in one query (tuned against DB load, §6) and how many STIX
objects go in one message to RabbitMQ (tuned against queue/worker load, §9) are different
constraints; don't let one implicitly set the other.

### 10c. Attribution and marking — a real open decision, not a default to pick alone

Two things every one of the four connectors needs to set *consistently*, not ad hoc per-connector:

- **`createdBy` (author Identity):** all VS-sourced content should trace back to one consistent
  system Identity (e.g. "CISA VulnScanning") across all four connectors, not left unset or
  inconsistent, so it's filterable/attributable as a single source in OpenCTI.
- **TLP/marking definition — flagging this as a genuine open question, not something to default
  silently.** This is government vulnerability-scan data describing specific stakeholder
  organizations' live, unpatched exposures. `TLP:CLEAR` is very unlikely to be the right default
  for that; something more restricted (`TLP:AMBER` or an internal/custom marking) is the safer
  starting assumption, but the actual policy call belongs to whoever owns data-handling rules for
  this program, not this planning doc. **Needs an explicit answer before any real data flows**,
  not just before "launch" — even the dry-run/local-stack dev loop in §9 should use whatever
  marking is eventually decided, so dev habits match production from the start.
- Confidence score: pick one fixed value per connector (existing connectors in
  [`docker-compose.yml`](docker-compose.yml) set this per-connector, e.g. `100` for
  `connector-opencti`, `75` for `connector-mitre`) — decide once, not per-run or per-row.

### 10d. Database query discipline

- **Explicit column projection, never `SELECT *`** — every query should name only the columns a
  connector actually maps to STIX. Cheaper on the no-read-replica primary (§2/§6), and more
  resilient to schema drift on columns we don't care about.
- **Shape `WHERE` clauses to hit existing indexes**, not whatever's convenient to write —
  `ticket_last_seen_idx`, `tickets_is_open_idx` for Connector A, `LatestPortScan`'s compound
  `(organization, ip, port, protocol)`/`(ip, current, time_scanned)` indexes for Connector C,
  `Organization.updated_at` for D. A query shape that doesn't match one of these forces a
  sequential scan on a primary that already has no failover capacity to spare.
- **Resolve Identity/org lookups once per run, not once per row.** Fetch the acronym→Identity
  mapping (or whatever Connector D's lookup produces) into memory at the start of a run and reuse
  it — avoid N+1 GraphQL calls against OpenCTI itself, a separate rate/latency concern from the DB
  side entirely.
- **Reuse this codebase's own connection-pooling pattern** (`SimpleConnectionPool` in
  [`query_redshift.py`](../backend/src/xfd_django/xfd_api/tasks/utils/query_redshift.py)) rather
  than opening a fresh connection per poll — but remember IAM auth tokens are ~15 minutes (§2), so
  pooled connections need per-checkout token refresh, not a connect-once-at-startup assumption.

### 10e. Error handling — mirror the isolation pattern already used in this codebase

`create_port_scan_summaries_bulk()` and `create_vuln_scan_summary()` (§3/§4) both isolate failures
per-chunk/per-org — log and continue, don't abort the whole run over one bad row. Every connector
should do the same at row-mapping granularity: one `Ticket`/`LatestPortScan` row with unexpected
data shouldn't sink an entire poll's bundle. This is an existing house convention to follow, not a
new pattern to invent.

### 10f. State-checkpoint ordering and processing guarantees

Only advance the connector-state watermark **after** the corresponding bundle has been confirmed
accepted by OpenCTI (via `send_stix2_bundle()`'s work-tracking, not just after building it locally)
— advancing first risks losing rows if the connector crashes mid-run. Prefer **at-least-once**
processing (safe to resend a poll's results if a run is interrupted) over engineering for
exactly-once, which is fragile and, given §10a's idempotent-write pattern, unnecessary — a resent
bundle should be a safe no-op, not a risk to guard against separately.

### 10g. Scheduling discipline across all four connectors

Stagger `CONNECTOR_DURATION_PERIOD` start offsets for D/A/C rather than letting them all fire at
the same wall-clock moment — otherwise every scheduled run piles three connectors' queries onto
the same no-read-replica primary (§2) and three ingestion runs' bundles onto the same 3-replica
`worker` pool (§9) simultaneously, for no benefit over spacing them out.

### 10h. Observability

Check what OpenCTI's own connector status page (backed by `helper.api.work`) already surfaces
(last run, duration, errors) before building custom metrics on top of it. Where that doesn't
reach — DB-side query duration, actual bundle sizes sent, row-to-STIX-object conversion counts —
mirror the `@cloudwatch_metric()` decorator pattern already used pervasively across the sync tasks
(§3) rather than inventing a separate observability convention for just these four connectors.

## 11. Implementation status

**Connector D scaffolded** at [`connectors/vs-org-bootstrap/`](connectors/vs-org-bootstrap/) (see
its own README.md) — config loading with the §10c/§9c fail-closed checks, `mini_data_lake` access
with an `IS_LOCAL` fixture fallback, the full row→STIX mapping, and the state-based idempotency
pattern from §10a. Both test loops from §9b are real and passing, not just described: 14 pure
unit tests (Loop 1) and 3 full-pipeline dry-run tests against fixtures with the OpenCTI helper
stubbed out (Loop 2, no network/queue at all) — `python3 -m pytest tests/ -v` in that directory.
Wired into [`docker-compose.yml`](docker-compose.yml) as `connector-vs-org-bootstrap` (build-based,
since this has no published image).

Building this against a real, installed `pycti==7.260824.0` (rather than reasoning about the SDK
from memory) surfaced two concrete corrections to earlier sections of this doc:

- **§10a/§10b upgraded from "confirm" to actually confirmed**, by reading the installed source:
  `send_stix2_bundle()` always splits via `OpenCTIStix2Splitter` unless `no_split=True` is passed
  (§10b's bundle-splitting question), and its docstring states outright that "OpenCTI always
  upserts data by standard id/hash regardless of \[the `update`\] flag" — the `update` kwarg only
  matters for a rare ambiguous-multi-match case, not for whether upserting happens at all. This
  directly validates §10a's recommended pattern: pin a relationship's id once (via
  `pycti.StixCoreRelationship.generate_id`) and reuse it verbatim on every later write, letting the
  changed field (e.g. `stop_time`) be the update OpenCTI applies to that same id — proven working
  end-to-end in `tests/test_connector_dry_run.py`, including the specific case (a CIDR retiring)
  that motivated §10a in the first place.
- **New gotcha, not previously documented: `DateField`-sourced values need timestamp
  normalization before use in STIX.** `CidrOrgs.first_seen`/`last_seen` are `DateField` (date-only)
  in `mini_data_lake`, and come back as bare dates — which `stix2`'s `TimestampProperty` rejects
  outright (`must be a datetime object, date object, or timestamp string in a recognizable
  format`, but a bare `"2025-01-01"` string does *not* count as recognizable to it, despite being
  ISO 8601). Found by actually running the dry-run test against fixture data, not by inspection —
  `mapping.normalize_timestamp()` handles it now. **Worth checking for the same issue on any other
  `DateField` column Connectors A/C/B end up touching** (e.g. `VulnScanSummary.summary_date`,
  `HostSummary.summary_date`) rather than assuming this was a one-off.

**Deliberately not done yet, and why:**

- **Not wired to a real OpenCTI or `mini_data_lake` instance.** Verified as far as is possible
  without one: `python3 -m src.main` with `IS_LOCAL=true` correctly loads fixtures, passes
  fail-closed config validation, initializes `OpenCTIConnectorHelper`, and fails at the GraphQL
  health check against an intentionally-unreachable OpenCTI URL — i.e. it fails at exactly the
  first point that genuinely requires infrastructure this session doesn't have, not anywhere in
  the connector's own code. Real validation needs §9d's local stack (or real credentials).
- **DB connectivity and the OpenCTI API token are not plumbed through yet.** The
  `docker-compose.yml` service references `VS_ORG_BOOTSTRAP_DB_HOST`, `AWS_REGION`, and
  `CONNECTOR_VS_ORG_BOOTSTRAP_API_KEY`, none of which exist yet in
  [`env.static`](env.static)/[`bootstrap.sh`](bootstrap.sh) or Terraform's
  `open_cti_secret_keys` (`infrastructure/vars.tf`). Deliberately not touched in this pass —
  `bootstrap.sh` has unrelated in-flight edits on the current branch, and this is real
  infra/secrets work worth its own deliberate change, not a drive-by edit alongside connector code.
- **The §7d/§6 sector/location "look up before create" logic is a stubbed `TODO`** in
  `connector.py`, not implemented — it creates `Identity`(class=sector)/`Location` objects
  unconditionally for now. Needs the actual overlap-with-`connector-opencti`'s-default-taxonomy
  question answered first (§10, next steps below) before this is safe to run against a real
  instance with real data.

## 12. Next steps

1. **Get the TLP/marking policy decision from whoever owns data-handling rules for this program**
   (§10c) — the single thing actually blocking Connector D from running anywhere real; everything
   else in §11's "not done yet" list can proceed in parallel with this.
2. Stand up the disposable local OpenCTI stack described in §9d (a `docker-compose.override.local.yml`
   sibling under `open-cti/`) — the next concrete step for Connector D specifically: it's built and
   test-passing, but has never talked to a real OpenCTI. Use it to empirically verify the
   null→set `stop_time` relationship-merge behavior (§10a) with real platform round-trips, not
   just the stubbed-helper dry run already passing.
3. Plumb `VS_ORG_BOOTSTRAP_DB_HOST`/`AWS_REGION`/`CONNECTOR_VS_ORG_BOOTSTRAP_API_KEY` through
   `env.static`/`bootstrap.sh`/Terraform's `open_cti_secret_keys` (§11) — real infra work,
   deliberately deferred rather than bundled into the connector code change.
4. Get a live psql session against `mini_data_lake` (once `open_cti` role/grant is confirmed) and
   pull real row counts, distinct `owner`/org counts, and samples of `Ticket`/`VulnScan`/
   `LatestPortScan` rows to ground-truth this doc against actual data — `LatestPortScan` row count
   is specifically needed to validate Connector C's full-poll-per-run strategy (§7c). While in
   there: check the actual `Identity`/`Location` taxonomy already in OpenCTI against CISA's VS
   sector list (resolves §11's sector/location `TODO` in `connector.py`), confirm the
   `sector_organizations` join-table name assumption (`db.py`'s one unverified query), and replace
   Connector D's synthetic test fixtures with real (scrubbed, reviewed) samples from one or two
   low-volume test orgs.
5. Resolve the remaining open questions in §6 (org filtering, KEV re-derivation, data volumes,
   actual `VulnScanningSync`/`vs_org_sync` schedules).
6. Confirm the Case/Incident recommendation in §7a, or flag the analyst workflow that would
   change it.
7. Build Connectors A, C, and B in that order (§8), following the same structure Connector D just
   established (`config.py`/`db.py`/`mapping.py`/`connector.py` split, both test loops from §9b
   passing before ever running unscoped) and the discipline in §10.
