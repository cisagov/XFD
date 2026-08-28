# Live Qualys Report Equivalence Runbook

## Purpose

Use this runbook to compare the legacy and extracted WAS report pipelines with
approved nonproduction Qualys data. The validation must prove report-content,
artifact, encryption, and cleanup equivalence before the extracted pipeline can
become the default.

This procedure does not change the default report route. The legacy pipeline
remains the default unless a later reviewed change explicitly switches it.

## Security Rules

- Use only approved nonproduction Qualys credentials and stakeholder tags.
- Do not place Qualys or report passwords in commands, logs, tickets, or Git.
- Do not run `source .env`. Docker reads `.env` through `--env-file` without
  requiring the values to be valid shell syntax.
- Disable shell command tracing before handling credentials with `set +x`.
- Keep the run directory private and remove it according to the approved data
  retention policy after results are recorded.
- Do not use `--allow-unencrypted` during equivalence testing.
- Do not use `--create-missing-password`. The approved test stakeholder must
  already have a stored Postgres report password.

## Preconditions

Confirm all of the following before starting:

- The branch and commit under test are approved for nonproduction validation.
- The worktree contains no uncommitted source changes.
- `backend/was/.env` contains approved nonproduction database and Qualys values.
- `.env` permissions are restricted to the operator.
- The Postgres `was_stakeholders` row exists and has a report password.
- The Qualys stakeholder tag exists and contains representative web apps and
  findings.
- No scan, tag, or finding-status changes are planned during the comparison.
- Docker Desktop is running and has access to the required output directory.
- The operator has permission to view generated Qualys reports and audit their
  deletion.

When Postgres is reached through an EC2 port-forwarding session, keep the
tunnel active for both runs. A container normally reaches the Mac host through
`host.docker.internal`, not container-local `localhost`. Set the nonproduction
`.env` database host and port accordingly.

## Required Test Matrix

Complete at least these cases before approving a default-route cutover:

| Case | Test Data | Expected Coverage |
| --- | --- | --- |
| Detail attachment | Stakeholder with fewer than 35 web applications | Qualys detail PDF creation, download, redaction, watermarking, and attachment |
| No detail attachment | Stakeholder with at least 35 web applications | Main report path without a Qualys detail PDF attachment |
| Representative findings | Stakeholder with multiple severities and statuses | Metrics, trends, charts, finding ages, and CSV attachments |
| Low or empty findings | Approved stakeholder with few or no active findings | Empty-state calculations and rendering |

The first live test may use one representative stakeholder. Do not approve the
default-route cutover until the required matrix is complete.

## Prepare The Run

Run these commands from `backend/was`:

```bash
set +x
set -o pipefail

test -f .env
test "$(stat -f '%Lp' .env)" = "600"
test -z "$(git status --porcelain --untracked-files=no)"

export WAS_EQUIVALENCE_TAG="REPLACE_WITH_APPROVED_NONPRODUCTION_TAG"
export WAS_EQUIVALENCE_DATE="$(date -u +%F)"
export WAS_EQUIVALENCE_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
export WAS_EQUIVALENCE_ROOT="$(pwd)/local-output/equivalence/${WAS_EQUIVALENCE_RUN_ID}"
export WAS_EQUIVALENCE_IMAGE="was-reporting:equivalence-$(git rev-parse --short HEAD)"
export WAS_EQUIVALENCE_PDF="${WAS_EQUIVALENCE_TAG}_report_${WAS_EQUIVALENCE_DATE}.pdf"

mkdir -p \
  "${WAS_EQUIVALENCE_ROOT}/legacy" \
  "${WAS_EQUIVALENCE_ROOT}/extracted" \
  "${WAS_EQUIVALENCE_ROOT}/build-context"
chmod 700 "${WAS_EQUIVALENCE_ROOT}"

git rev-parse HEAD > "${WAS_EQUIVALENCE_ROOT}/commit-sha.txt"
git archive HEAD:backend/was \
  | tar -x -C "${WAS_EQUIVALENCE_ROOT}/build-context"
docker build \
  -t "${WAS_EQUIVALENCE_IMAGE}" \
  "${WAS_EQUIVALENCE_ROOT}/build-context"
docker image inspect "${WAS_EQUIVALENCE_IMAGE}" \
  --format '{{.Id}} {{.Created}}' \
  > "${WAS_EQUIVALENCE_ROOT}/image.txt"
```

On Linux, replace the macOS `stat -f '%Lp' .env` command with
`stat -c '%a' .env`.

The image is built from `git archive HEAD:backend/was`, not the working
directory. This prevents local untracked files, including schema update files,
from entering the validation image and ensures the image corresponds to the
recorded commit SHA.

## Generate The Legacy Report

The command intentionally omits `--encrypt`. The modern boundary reads the
stored Postgres password and passes it to the legacy subprocess without placing
it in process arguments.

```bash
set +e
docker run --rm \
  --env-file .env \
  -v "${WAS_EQUIVALENCE_ROOT}/legacy:/WAS_REPORT_GENERATION/docs" \
  "${WAS_EQUIVALENCE_IMAGE}" \
  was-reports \
  --tag "${WAS_EQUIVALENCE_TAG}" \
  2>&1 | tee "${WAS_EQUIVALENCE_ROOT}/legacy.log"
export WAS_EQUIVALENCE_LEGACY_STATUS="${PIPESTATUS[0]}"
set -e

docker run --rm \
  -v "${WAS_EQUIVALENCE_ROOT}/legacy:/cleanup" \
  --entrypoint rm \
  "${WAS_EQUIVALENCE_IMAGE}" \
  -f /cleanup/was_config.txt

test ! -e "${WAS_EQUIVALENCE_ROOT}/legacy/was_config.txt"
test "${WAS_EQUIVALENCE_LEGACY_STATUS}" -eq 0
test -f "${WAS_EQUIVALENCE_ROOT}/legacy/${WAS_EQUIVALENCE_PDF}"
```

The cleanup container is required because the compatibility path generates a
credential-bearing `was_config.txt` inside the mounted `docs` directory. Run
the cleanup even when report generation fails.

## Generate The Extracted Report

Run the extracted pipeline immediately after the legacy pipeline to reduce the
chance of Qualys data changing between requests.

```bash
set +e
docker run --rm \
  --env-file .env \
  -v "${WAS_EQUIVALENCE_ROOT}/extracted:/WAS_REPORT_GENERATION/docs" \
  "${WAS_EQUIVALENCE_IMAGE}" \
  was-reports \
  --tag "${WAS_EQUIVALENCE_TAG}" \
  --use-extracted-pipeline \
  2>&1 | tee "${WAS_EQUIVALENCE_ROOT}/extracted.log"
export WAS_EQUIVALENCE_EXTRACTED_STATUS="${PIPESTATUS[0]}"
set -e

docker run --rm \
  -v "${WAS_EQUIVALENCE_ROOT}/extracted:/cleanup" \
  --entrypoint rm \
  "${WAS_EQUIVALENCE_IMAGE}" \
  -f /cleanup/was_config.txt

test ! -e "${WAS_EQUIVALENCE_ROOT}/extracted/was_config.txt"
test "${WAS_EQUIVALENCE_EXTRACTED_STATUS}" -eq 0
test -f "${WAS_EQUIVALENCE_ROOT}/extracted/${WAS_EQUIVALENCE_PDF}"
```

## Compare The Reports

Read the report password without echoing it. Passing only the environment
variable name to Docker keeps the password out of the command line.

```bash
read -s -p "Report comparison password: " WAS_REPORT_COMPARISON_PASSWORD
printf '\n'
export WAS_REPORT_COMPARISON_PASSWORD

set +e
docker run --rm \
  --env WAS_REPORT_COMPARISON_PASSWORD \
  -v "${WAS_EQUIVALENCE_ROOT}:/reports:ro" \
  --entrypoint was-compare-reports \
  "${WAS_EQUIVALENCE_IMAGE}" \
  "/reports/legacy/${WAS_EQUIVALENCE_PDF}" \
  "/reports/extracted/${WAS_EQUIVALENCE_PDF}" \
  | tee "${WAS_EQUIVALENCE_ROOT}/comparison.json"
export WAS_EQUIVALENCE_COMPARISON_STATUS="${PIPESTATUS[0]}"
set -e

unset WAS_REPORT_COMPARISON_PASSWORD
test "${WAS_EQUIVALENCE_COMPARISON_STATUS}" -eq 0
```

The comparator returns `0` only when all checked fields match. It compares:

- Encryption state
- Page count
- Page dimensions
- Normalized page-text hashes
- Embedded attachment names and content hashes
- Selected PDF metadata

Do not treat exit code `1` as an approved difference. Investigate and document
each reported field before deciding whether a difference is expected.

## Verify Security And Cleanup

Confirm no unencrypted or temporary report remains on the host:

```bash
test -z "$(find "${WAS_EQUIVALENCE_ROOT}" -type f \
  \( -name '*UNENCRYPTED*' -o -name '*temp_encrypt*' -o \
     -name '*.tex' -o -name 'was_config.txt' \) \
  -print)"

shasum -a 256 \
  "${WAS_EQUIVALENCE_ROOT}/legacy/${WAS_EQUIVALENCE_PDF}" \
  "${WAS_EQUIVALENCE_ROOT}/extracted/${WAS_EQUIVALENCE_PDF}" \
  > "${WAS_EQUIVALENCE_ROOT}/pdf-sha256.txt"
```

Use the approved Qualys administration interface or audit history to confirm
that temporary XML and detail reports created by both runs were deleted. The
current comparator cannot verify Qualys-side cleanup.

Review both logs for API failures, retries, unexpected tracebacks, and any
sensitive values. Do not attach raw reports or logs to a ticket unless the
approved handling process permits it.

## Acceptance Criteria

An individual case passes only when:

- Both commands exit successfully.
- Both expected encrypted PDFs exist.
- The comparator exits with status `0` and reports `"matches": true`.
- Expected attachment names and hashes match.
- No unencrypted or temporary report artifacts remain.
- Qualys temporary reports are confirmed deleted.
- Logs contain no credentials, report passwords, or unexpected sensitive data.
- The commit SHA, image ID, tag, date, operator, and outcome are recorded in the
  approved validation record.

Default-route cutover requires every required matrix case to pass.

## Failure Handling

If either generation command or the comparator fails:

1. Do not change the default pipeline.
2. Preserve the private run directory until the investigation is complete.
3. Record the failing command, exit code, commit SHA, image ID, and comparison
   fields without recording credentials or report content.
4. Determine whether Qualys data changed between runs.
5. Confirm temporary Qualys reports were deleted even when generation failed.
6. Add or update a fixture-based regression test before changing code.
7. Repeat the affected case after review.

## Completion And Cleanup

After the approved validation record is complete:

```bash
unset WAS_EQUIVALENCE_TAG
unset WAS_EQUIVALENCE_DATE
unset WAS_EQUIVALENCE_RUN_ID
unset WAS_EQUIVALENCE_IMAGE
unset WAS_EQUIVALENCE_PDF
unset WAS_EQUIVALENCE_ROOT
unset WAS_EQUIVALENCE_LEGACY_STATUS
unset WAS_EQUIVALENCE_EXTRACTED_STATUS
unset WAS_EQUIVALENCE_COMPARISON_STATUS
```

Remove the run directory only when permitted by the approved retention and
evidence-handling process. Do not commit generated reports, logs, comparison
JSON, checksums, `.env`, or generated `was_config.txt` files.
