# VS Ticket Ingestion Connector

Connector A in the four-connector VS architecture — see
[`../../OpenCTI-connector.md`](../../OpenCTI-connector.md) §7a for the full design, §8 for build
order (this one depends on connector D), and §10 (especially §10i) for the implementation
discipline this code follows.

Depends on [connector D](../vs-org-bootstrap/) — the organization `Identity` a ticket resolves to
must already exist. Deploy order: D, then this one.

## What it does

Reads `Ticket` from `mini_data_lake` and upserts `IPv4-Addr`/`IPv6-Addr` (scanned host) and
`Vulnerability` (CVE, or a named risky-service finding for CVE-less tickets) objects, plus two
kinds of relationship:

- IP `related-to` Vulnerability, carrying the ticket's open/closed lifecycle as native
  `start_time`/`stop_time` — no `Case`/`Incident` container (§7a's reasoning for why not). Also
  carries `Ticket.updated_timestamp` as a custom property, `x_opencti_updated_timestamp` — see
  "Ticket.updated_timestamp" below.
- Organization `related-to` IP, so the finding is actually reachable from its owning org in the
  graph (the org `Identity` itself is *looked up*, never created here — that's connector D's job).

### `Ticket.updated_timestamp`

Carried onto the IP↔Vulnerability relationship (not dropped after being used for the watermark,
and deliberately not stamped onto the `Vulnerability` SDO — see below) as
`x_opencti_updated_timestamp`, a plain custom property rather than stix2's native `modified`.

Why not `modified`: OpenCTI/stix2 give that field real merge/versioning semantics, and this
connector's own bootstrap poll can legitimately hand back tickets whose `updated_timestamp` is
older than what's already stored for a given relationship — driving `modified` from it risks the
platform treating an old bootstrap row as stale and silently skipping the write. A plain custom
property carries the same information with none of that risk. Verified directly against the
installed `stix2` library that a real `datetime.datetime` passed through `custom_properties`
serializes correctly to a proper `Z`-suffixed ISO string, and that custom properties have no
bearing on this relationship's id either way (it's always explicitly pinned via `existing_id`,
never derived from its own content).

Why not on the `Vulnerability` SDO: that object is deliberately minimal and shared/deduped across
every ticket and org referencing the same CVE (see `mapping.py`'s `map_vulnerability()` docstring)
— stamping one ticket's update time onto it would mean whichever connector run happened to touch
that CVE last overwrites a fact that has nothing to do with the CVE itself. The relationship,
scoped to one specific (ip, vulnerability) pair, is the correct home — the same place
`opened_timestamp`/`closed_timestamp` already live as `start_time`/`stop_time`.

A ticket that flips to `false_positive=True` on a later poll has its relationship **revoked**
(deleted via the OpenCTI API directly, not through the STIX bundle — bundles only upsert) rather
than left in the graph as a stale "still vulnerable" edge.

## Structure

```text
src/
  config.py      # env/yaml config loading, fails closed on tlp_marking + org scope
  db.py          # mini_data_lake access + IS_LOCAL fixture fallback
  mapping.py     # pure row -> STIX mapping functions (no I/O) -- Loop 1 test target
  connector.py   # orchestration: fetch -> map -> bundle -> send, state/idempotency, revocation
  main.py        # entry point
tests/
  fixtures/                  # small synthetic sample rows, shaped like real mini_data_lake queries
  test_mapping.py            # Loop 1: pure unit tests, no DB/OpenCTI/queue at all
  test_connector_dry_run.py  # Loop 2: full pipeline against fixtures, OpenCTI helper stubbed out
```

Structurally identical to [connector D](../vs-org-bootstrap/) on purpose (§10i: apply the same
discipline from the start, don't reinvent it per connector). Run the fast loops constantly:

```bash
pip install -r requirements.txt
python3 -m pytest tests/ -v
```

## Two things this connector refuses to start without

Same two fail-closed checks as connector D, in `src/config.py`:

- **`VS_TICKET_INGESTION_TLP_MARKING`** — must match connector D's value once the TLP/marking
  policy decision (`OpenCTI-connector.md` §10c) is actually made; it's one shared decision across
  all four connectors, not a per-connector default to pick independently.
- **`VS_TICKET_INGESTION_ORG_ACRONYM_ALLOWLIST`** (or explicit
  `VS_TICKET_INGESTION_ALLOW_UNSCOPED_RUN=true`) — an empty allowlist means "scoped to nothing,"
  not "all orgs" (§9c).

## Keeping a first run fast: `VS_TICKET_INGESTION_LOOKBACK_DAYS`

A fresh (or reset) connector state has no watermark yet, so the first poll pulls *every* ticket
ever recorded for the scoped orgs — slow to iterate against for any org with real history. Set
`VS_TICKET_INGESTION_LOOKBACK_DAYS` (e.g. `7`) to bound that first poll to the last N days
instead; unset/empty (the default) means no bound, matching the original full-backfill behavior.

This only ever affects a poll with **no existing watermark** — once one exists, `lookback_days`
is ignored, deliberately. Clamping every ongoing poll to a rolling window would silently create a
permanent gap: a still-open ticket whose last-seen timestamp never changes again would fall
outside the window and then never get picked up, since the watermark only ever advances forward
from here.

**That gap is real, not theoretical — measured against the live box (2026-08-28):** with a 60-day
lookback, 413,925 real `is_open=true` tickets on `cyhy_mini_data_lake_staging` had a last-touch
older than the cutoff. A plain lookback would have silently, permanently dropped every one of
them, not "eventually" ingested them. The fix: the bootstrap poll (and *only* the bootstrap poll —
`connector.run()` computes `is_first_run = state.get("last_seen_watermark") is None` and passes
it straight through as `include_stale_open`) also pulls in every currently-open ticket regardless
of how stale its last-touch date is, alongside whatever falls inside the lookback window. So
`lookback_days` still controls "how much recent history to also pull on top of that," but no
longer controls "whether currently-actionable findings get missed forever" — those two concerns
used to be conflated in one knob, and aren't anymore. See `db.py`'s `_fetch_tickets_live()` for
the query-level detail and the real-Postgres verification behind it.

`VS_TICKET_INGESTION_MAX_ROWS_PER_RUN` (also tunable via `docker-compose.yml`) is the
complementary, always-safe lever for both the lookback window and the stale-open backlog — it
only paginates slower across multiple polls, it never skips data. Size it off the real numbers
for your environment (`SELECT count(*) FROM ticket WHERE is_open = true AND
COALESCE(closed_timestamp, updated_timestamp) <= now() - interval 'N days'` via
`crossfeed-staging-bastion`, plus the in-window count) rather than guessing — a large stale-open
count divided by a small row cap is a lot of daily polls before the backlog actually clears.

## Running it

Same two modes as connector D — see its README for the fuller explanation of each:

- **Fixture mode** (`IS_LOCAL=true`) — `db.py` loads `tests/fixtures/tickets.json` instead of
  querying Postgres. Still needs a real (or locally stacked) OpenCTI to send to.
- **Against real `mini_data_lake` + OpenCTI** — copy `config.yml.sample` to `config.yml`, fill in
  `db_host` and a real `org_acronym_allowlist` scoped to one or two low-volume test orgs, then:

  ```bash
  python3 -m src.main
  ```

  (Must run as a module — relative imports. The Dockerfile's `ENTRYPOINT` already does this.)

## TLS interception (Zscaler)

Identical setup to connector D — see [its README](../vs-org-bootstrap/README.md#tls-interception-zscaler--required-manual-per-instance-setup-not-git-managed)
for the full explanation. This is a property of the network the EC2 host sits behind, already set
up once for connector D; nothing additional to do per-connector beyond the `additional_contexts`
block in `docker-compose.yml` (already present for this service).

## Known gaps / things to verify before this is production-ready

- **Real per-run timings not yet measured.** `max_rows_per_run` starts at the same 5000 default
  connector D used for its first scoped runs, but tickets outnumber orgs/CIDRs by a lot (§7a) --
  watch actual poll duration once this runs against real data before assuming that cap is right
  at full (unscoped) production scale.
- **`resolve_org_identity_id()`'s coupling to connector D:** this connector never creates or
  verifies an org `Identity` — it recomputes the same content-derived id connector D's
  `map_organization()` would produce for the same `organization.name`, assuming that name hasn't
  drifted between D's last sync and this row's join. Real but narrow; both connectors read the
  same source-of-truth column, just at different times.
- **Severity bucketing (`mapping.severity_label`) uses the standard CVSS v3 qualitative scale**
  (low/medium/high/critical cutoffs at 4.0/7.0/9.0) — not yet checked against the actual
  distribution of real `Ticket.cvss_severity` values in `mini_data_lake`; verify before trusting
  the resulting labels for any downstream triage/reporting use.
- Not yet run against a real OpenCTI instance — the fixture-based dry-run pipeline (Loop 2, §9b)
  and a throwaway real-Postgres type check (Loop 4, §9b — confirmed `cvss_severity` returns
  `decimal.Decimal`, `organization_id`'s join needs no `uuid` cast, and every timestamp column
  returns a real `datetime.datetime`) are both done; the actual send-and-verify-in-OpenCTI step is
  next, the same order connector D went through.
