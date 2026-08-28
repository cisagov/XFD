# VS VulnScan Enrichment Connector

Connector B in the four-connector VS architecture — see
[`../../OpenCTI-connector.md`](../../OpenCTI-connector.md) §7b for the full design, §8 for build
order (this one depends on connector A), and §10 for the implementation discipline this code
follows.

Depends on [connector A](../vs-ticket-ingestion/) (or some other process) having already created
the `Vulnerability`/`IPv4-Addr`/`IPv6-Addr` entity being enriched — this is not a standalone
ingestion path.

## What it does — and how it's structurally different from connectors A/D

Given an analyst-triggered "Enrich" click on an IP or Vulnerability entity in OpenCTI, looks up
`VulnScan` scanner-level detail (CVSS v2/v3, plugin name/family, solution, synopsis, risk factor,
exploit availability, see-also references) and attaches it as a `Note` — additive, never
overwriting the `Vulnerability` SDO's own CVSS fields, which `connector-cve`/
`connector-vulncheck` already own (§7b).

This is `INTERNAL_ENRICHMENT`, not `EXTERNAL_IMPORT` — one real structural difference from
connectors A/D, not just a different table:

- Triggered per-entity via `helper.listen()`, not polled on a schedule via `helper.schedule_iso()`.
  There's no `run()`/watermark/`duration_period` here — each invocation is already scoped to
  exactly one entity by construction, so there's no "accidentally unscoped run" failure mode to
  guard against the way A/D's `org_acronym_allowlist`/`allow_unscoped_run` pair does.
- `CONNECTOR_AUTO=false` (manual trigger only) to start, matching every other enrichment
  connector already running in this deployment (`connector-censys-enrichment`, etc.) — see
  `config.yml.sample` for the reasoning.

## Structure

```text
src/
  config.py      # env/yaml config loading, fails closed on tlp_marking
  db.py          # mini_data_lake access + IS_LOCAL fixture fallback, by-ip / by-cve lookups
  mapping.py     # pure row -> STIX mapping functions (no I/O) -- Loop 1 test target
  connector.py   # process_message(): lookup -> map -> bundle -> send, Note idempotency
  main.py        # entry point (helper.listen(), not schedule_iso())
tests/
  fixtures/                  # small synthetic sample rows, shaped like real mini_data_lake queries
  test_mapping.py            # Loop 1: pure unit tests, no DB/OpenCTI/queue at all
  test_connector_dry_run.py  # Loop 2: full pipeline against fixtures, OpenCTI helper stubbed out
```

Structurally identical to connectors A/D wherever the different lifecycle allows (§10i: apply
the same discipline from the start, don't reinvent it per connector). Run the fast loops
constantly:

```bash
pip install -r requirements.txt
python3 -m pytest tests/ -v
```

## The one thing this connector refuses to start without

- **`VS_VULNSCAN_ENRICHMENT_TLP_MARKING`** — must match connectors A/D's value once the
  TLP/marking policy decision (`OpenCTI-connector.md` §10c) is actually made; it's one shared
  decision across all four connectors.

(No `ORG_ACRONYM_ALLOWLIST`/`ALLOW_UNSCOPED_RUN` pair here — see "What it does" above for why
that lever doesn't apply to a per-entity-triggered connector.)

## Idempotency: why a Note needs its id pinned too, not just relationships

`pycti.Note.generate_id()` hashes the Note's own `content` (verified against the installed pycti
source) — recomputing it fresh on every re-enrichment would produce a *different* Note id the
moment scanner data changes even slightly, the same failure mode §10a already documented for
relationships' `start_time`/`stop_time`. `connector.py` pins the first-seen Note id per triggered
entity in connector state (`state["note_ids"][entity_id]`) and reuses it verbatim on every later
enrichment of that same entity — OpenCTI's own "always upserts by standard id" behavior (already
confirmed while building connector D) is what turns that into an update-in-place, not a pile of
near-duplicate Notes accumulating on the same entity every time someone clicks "Enrich" again.

## Running it

Same two modes as connectors A/D:

- **Fixture mode** (`IS_LOCAL=true`) — `db.py` loads `tests/fixtures/vuln_scans.json` instead of
  querying Postgres.
- **Against real `mini_data_lake` + OpenCTI** — copy `config.yml.sample` to `config.yml`, fill in
  `db_host`, then:

  ```bash
  python3 -m src.main
  ```

  Unlike A/D, this blocks on `helper.listen()` waiting for a real "Enrich" trigger from OpenCTI —
  there's nothing to observe until you actually click it on a real `IPv4-Addr`/`IPv6-Addr`/
  `Vulnerability` entity that connector A has already created.

## TLS interception (Zscaler)

Identical setup to connectors A/D — see
[connector D's README](../vs-org-bootstrap/README.md#tls-interception-zscaler--required-manual-per-instance-setup-not-git-managed).
Already set up once for this network; nothing additional needed beyond the `additional_contexts`
block already present in `docker-compose.yml`.

## Known gaps / things to verify before this is production-ready

- **`VulnScan` has no indexes at all** (`backend/src/xfd_django/xfd_mini_dl/models.py`'s
  `VulnScan.Meta` defines none, unlike `Ticket`'s `tickets_is_open_idx`/`ticket_last_seen_idx`)
  — `ip_string`/`cve_string` lookups may currently be sequential scans over the whole table.
  Matters more here than for A/D's background polls, since this runs synchronously while an
  analyst is waiting on the "Enrich" button. Confirm the real query plan (`EXPLAIN ANALYZE` via
  `crossfeed-staging-bastion`) before treating this as production-ready — not yet done.
- **`see_also`/`xref` format is unconfirmed.** `mapping.build_external_references()`
  conservatively only turns a `see_also` value into a clickable External Reference when it
  already looks like a URL; everything else is still captured in the Note's own content, just
  not double-represented as a reference. Worth revisiting once real values are inspected.
- **A Note that no longer has any matching VulnScan rows on re-enrichment is left as-is, not
  revoked.** Low-priority in practice (scanner data essentially only grows/updates), but a real,
  documented gap rather than an oversight — connector A's false-positive revocation path (§7a)
  doesn't have an equivalent here yet.
- Not yet run against a real OpenCTI instance — the fixture-based dry-run pipeline (Loop 2, §9b)
  is done and passing; the actual "Enrich" click against real `mini_data_lake` data is next, the
  same order connectors D and A went through.
