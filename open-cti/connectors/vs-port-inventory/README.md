# VS Port/Service Inventory Connector

Connector C in the four-connector VS architecture — see
[`../../OpenCTI-connector.md`](../../OpenCTI-connector.md) §7c for the full design and §10 for
the implementation discipline this code follows.

Depends on [connector D](../vs-org-bootstrap/) (org Identity must exist) — otherwise independent
of connectors A/B.

## What it does — and the one thing that makes it structurally different from A/D

Reads `LatestPortScan` — already deduped to one row per `(organization, ip, port, protocol)` by
the sync task's own upsert, i.e. "current state of the world," not a raw scan log — and produces
`IPv4-Addr`/`IPv6-Addr` (reused from connector A), `Network-Traffic`, and (when scanner-reported
product/version/cpe detail exists) `Software` objects, plus the relationships tying them to their
owning org.

**No timestamp watermark is possible here (§7c's core gotcha).**
`mark_stale_latest_port_scans()` (`backend/.../vs_port_scans.py:771`) flips a port's `current` to
`False` after 14 days via a plain `UPDATE ... SET current = FALSE WHERE time_scanned < cutoff` —
confirmed by reading that function directly — and it never touches `time_scanned` itself. A
`WHERE time_scanned > watermark` poll would never see that transition and would report a closed
port as open forever. So this connector polls the **entire in-scope table every run** and diffs
it against a `(org, ip, port, protocol) -> last-known-state` map kept in connector state — closer
to a reconciliation loop than to connector A's incremental polls.

## Structure

```text
src/
  config.py      # env/yaml config loading, fails closed on tlp_marking + org scope
  db.py          # mini_data_lake access + IS_LOCAL fixture fallback -- one full-table query
  mapping.py     # pure row -> STIX mapping functions (no I/O) -- Loop 1 test target
  connector.py   # orchestration: full poll -> diff against state -> bundle only what changed
  main.py        # entry point
tests/
  fixtures/                  # small synthetic sample rows, shaped like real mini_data_lake queries
  test_mapping.py            # Loop 1: pure unit tests, no DB/OpenCTI/queue at all
  test_connector_dry_run.py  # Loop 2: full reconciliation pipeline against fixtures
```

Run the fast loops constantly:

```bash
pip install -r requirements.txt
python3 -m pytest tests/ -v
```

## Two things this connector refuses to start without

- **`VS_PORT_INVENTORY_TLP_MARKING`** — must match the other three connectors' value once the
  TLP/marking policy decision (§10c) is actually made.
- **`VS_PORT_INVENTORY_ORG_ACRONYM_ALLOWLIST`** (or explicit
  `VS_PORT_INVENTORY_ALLOW_UNSCOPED_RUN=true`) — matters *more* here than for connectors A/D: since
  this connector always does a full poll (never an incremental one), an accidentally unscoped run
  means re-pulling and re-diffing the entire `LatestPortScan` table on every single manual dev
  run, not just a bounded incremental slice.

## A STIX id gotcha found and steered around before it could bite, not after

`stix2.NetworkTraffic`'s `start`/`end` are genuine ID Contributing Properties — verified directly
against the installed `stix2` library that two otherwise-identical `NetworkTraffic` objects with
different `start` values get *different* ids. Putting this port's open/stale lifecycle directly
on the `NetworkTraffic` SCO (the STIX-native-looking choice) would have fragmented one port's
history into a new object every time it changed, instead of updating one object in place — the
third time this exact bug class has shown up across the four connectors (Notes' content-hash for
Connector B, relationships' `start_time`/`stop_time` for Connector A/D). The `NetworkTraffic` SCO
here is built from stable fields only; the lifecycle lives entirely on a separate,
`§10a`-pinned `Relationship` (org → Network-Traffic), the same idempotency pattern every other
connector already uses.

## Running it

Same two modes as the other three connectors — see connector D's README for the fuller
explanation of each. `IS_LOCAL=true` loads `tests/fixtures/port_scans.json`; against real
`mini_data_lake` + OpenCTI, copy `config.yml.sample` to `config.yml`, fill in `db_host` and a
real `org_acronym_allowlist` scoped to one or two low-volume test orgs, then `python3 -m src.main`.

## TLS interception (Zscaler)

Identical setup to the other three connectors — see
[connector D's README](../vs-org-bootstrap/README.md#tls-interception-zscaler--required-manual-per-instance-setup-not-git-managed).
Already set up once for this network.

## Known gaps / things to verify before this is production-ready

- **A key that vanishes from the source entirely (not just `current` flipping to `False`) is
  left untouched in state, not revoked.** `state["port_scan_state"]` is only ever added to or
  updated for rows actually seen in a given poll — never wholesale-replaced — specifically so a
  partial/empty poll (a transient DB issue, or a deliberately narrowed org scope) can't silently
  erase previously-recorded history. The tradeoff: a genuine hard delete of a `LatestPortScan`
  row (unconfirmed whether this ever happens — `mark_stale_latest_port_scans()` only sets
  `current=False`, never deletes) would leave a stale relationship un-revoked forever. Same
  category of known gap as connector B's un-revoked stale Note.
- **Row-count growth is structurally different from connector A's backlog.** `LatestPortScan`
  rows never get deleted when a port goes stale, only flagged — so the in-scope row count only
  ever grows over time, unlike a ticket backlog a watermark eventually catches up past. Real row
  counts for this table are still unconfirmed (`OpenCTI-connector.md` §6); size
  `max_vulnscan_rows_per_entity`'s sibling here, `max_rows_per_run`, off real numbers once known,
  the same way connector A's was resized off its own real backlog count.
- **Reopened-port semantics (clear `stop_time`, keep the original `start_time`) are a documented
  judgment call, not something the design doc explicitly specifies** — see
  `connector.py`'s `_resolve_lifecycle()` docstring for the reasoning.
- Not yet run against a real OpenCTI instance — the fixture-based dry-run pipeline (Loop 2, §9b)
  and a throwaway real-Postgres check (Loop 4 — confirmed `current` returns a real Python `bool`,
  `time_scanned` a real `datetime`, and the join/scoping query plan works as expected) are both
  done; the actual send-and-verify-in-OpenCTI step is next, the same order every other connector
  in this set went through.
