# VS Organization & CIDR Bootstrap Connector

Connector D in the four-connector VS architecture — see
[`../../OpenCTI-connector.md`](../../OpenCTI-connector.md) §7d for the full design, §8 for why
this one is built first, and §10 for the implementation discipline this code follows.

Root of the dependency chain: Connectors A (Ticket Ingestion) and C (Port/Service Inventory) both
resolve their organization `Identity` against what this connector creates.

## What it does

Reads `Organization`, `Sector`, `Cidr`/`CidrOrgs`, `Location` from `mini_data_lake` and upserts
them into OpenCTI as `Identity` (organization + sector), `Location`, and `IPv4-Addr`/`IPv6-Addr`
(CIDR-notation) objects, plus the relationships between them (`part-of`, `located-at`,
`related-to`).

## Structure

```text
src/
  config.py      # env/yaml config loading, fails closed on tlp_marking + org scope (see below)
  db.py          # mini_data_lake access + IS_LOCAL fixture fallback
  mapping.py     # pure row -> STIX mapping functions (no I/O) -- Loop 1 test target
  connector.py   # orchestration: fetch -> map -> bundle -> send, state/idempotency handling
  main.py        # entry point
tests/
  fixtures/              # small synthetic sample rows, shaped like real mini_data_lake queries
  test_mapping.py        # Loop 1: pure unit tests, no DB/OpenCTI/queue at all
  test_connector_dry_run.py  # Loop 2: full pipeline against fixtures, OpenCTI helper stubbed out
```

This mirrors the three test loops in `OpenCTI-connector.md` §9b. Run the fast ones constantly:

```bash
pip install -r requirements.txt
python3 -m pytest tests/ -v
```

## Two things this connector refuses to start without

Both are deliberate fail-closed checks in `src/config.py`, not oversights:

- **`VS_ORG_BOOTSTRAP_TLP_MARKING`** — the TLP/marking policy decision (`OpenCTI-connector.md`
  §10c) hasn't been made yet. Rather than default to something permissive like `TLP:CLEAR` for
  stakeholder vulnerability data, this connector won't start until a value is set.
- **`VS_ORG_BOOTSTRAP_ORG_ACRONYM_ALLOWLIST`** (or explicit `VS_ORG_BOOTSTRAP_ALLOW_UNSCOPED_RUN=true`)
  — an empty allowlist means "scoped to nothing," not "all orgs" (§9c), so an unscoped run during
  dev never happens by accident.

## Running it

**Fixture mode (fastest, no DB/OpenCTI at all)** — set `IS_LOCAL=true`; `db.py` loads
`tests/fixtures/*.json` instead of querying Postgres. Still needs a real (or locally stacked)
OpenCTI to actually send to, since only the DB side is stubbed here — see `test_connector_dry_run.py`
for the fully-stubbed version that needs neither.

**Against real `mini_data_lake` + a local OpenCTI stack** — see `OpenCTI-connector.md` §9d for
standing up the disposable local stack this should be developed against before ever pointing at
the shared EC2 instance. Copy `config.yml.sample` to `config.yml`, fill in `db_host` and a real
`org_acronym_allowlist` scoped to one or two low-volume test orgs, and run:

```bash
python3 -m src.main
```

(Must run as a module — `src/main.py` uses relative imports. The Dockerfile's `ENTRYPOINT` already
does this correctly; running it directly outside Docker, `cd` into this directory first.)

## TLS interception (Zscaler) — required manual, per-instance setup, not git-managed

If this connector's build fails with `pip` complaining about a "self-signed certificate in
certificate chain," it means the network this instance sits behind (Zscaler, confirmed on the
CAWS-staging box) TLS-inspects outbound HTTPS and re-signs it with an org root CA. The EC2 host
already trusts that CA; a fresh Docker build container doesn't inherit it, and neither does the
running container at runtime (`boto3`'s AWS calls and `pycti`'s GraphQL client to `OPENCTI_URL`
would hit the identical failure the moment the container starts, not just `pip install` at build
time) — which is why the Dockerfile installs it into the image's own CA bundle (Debian's
`update-ca-certificates`, appending rather than replacing, so normal public-CA verification still
works for anything that isn't actually Zscaler-intercepted) and sets `PIP_CERT`/
`REQUESTS_CA_BUNDLE`/`AWS_CA_BUNDLE`/`SSL_CERT_FILE` to point at the combined result for both.

**The cert itself never touches this repo, not even untracked.** `docker-compose.yml` declares a
named build context (`additional_contexts: zscaler_cert=${ZSCALER_CERT_DIR:-/opt/open-cti/tls}`)
and the Dockerfile pulls from it directly (`COPY --from=zscaler_cert`) — the file lives in
`/opt/open-cti` (this stack's runtime state, same place `.env`/`env.deploy` already live, and
distinct from `/opt/open-cti-repo`, the replaceable git checkout) and is never read from or
written into any path git tracks. Requires BuildKit; there's a known regression for
`additional_contexts` in Compose 2.24.0 specifically (docker/compose#11351) — confirm
`docker compose build` actually resolves it on your Compose version before trusting this blindly.

This is real infrastructure setup specific to a *network*, not to this codebase — same category
as the `open_cti` DB role/grant or the OpenCTI API token: manual, out-of-band, done once per
instance rather than automated. A genuinely new instance needs this step too; it's not a
one-time fix for all environments:

```bash
mkdir -p /opt/open-cti/tls
cp /home/ec2-user/tmp/zscaler.pem /opt/open-cti/tls/zscaler.pem
docker compose --env-file /opt/open-cti/.env up -d --build
```

## Known gaps / things to verify before this is production-ready

- **Sector/Location collision risk (§7d/§6):** this connector currently creates
  `Identity(class="class")`/`Location` objects unconditionally. `connector-opencti` (OpenCTI's
  built-in "Datasets" seeder) likely already seeded a default sector/location taxonomy —
  `connector.py`'s `_process()` has a `TODO` marking where a look-up-by-name pass needs to go
  before this is safe to run against a real instance with real data.
- **State growth:** the `part_of_relationship_ids`/`located_at_relationship_ids`/
  `cidr_relationship_ids` maps in connector state grow with the number of distinct external keys
  ever seen and never shrink. Fine at VS's scale (hundreds of orgs, thousands of CIDRs at most),
  but worth knowing if that assumption ever needs revisiting.
- Not yet run against a real OpenCTI instance — everything up through `OpenCTIConnectorHelper`
  initialization and the GraphQL health check has been verified locally (it fails, correctly, at
  "no OpenCTI reachable" rather than anywhere in this connector's own code); the actual
  send-and-verify-in-OpenCTI step is next, once the local stack (§9d) exists.
