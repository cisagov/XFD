PYTHON ?= ../../cd_WAS_update/bin/python
REPO_ROOT ?= ../..
ROOT_PYTHON ?= ./cd_WAS_update/bin/python
IMAGE ?= was-reporting
ENV_FILE ?= .env
OUTPUT_DIR ?= $(PWD)/local-output
DOCKER_HOST_USER ?= --user "$$(id -u):$$(id -g)"
TRACKER_CSV ?= $(OUTPUT_DIR)/was-daily-tracker.csv
STAKEHOLDER_CSV ?= $(OUTPUT_DIR)/was-stakeholders.csv
TEST_RECIPIENTS ?= operator@example.gov
BATCH_WORKERS ?= 30
BATCH_TEST_RECIPIENTS ?=
BATCH_DAYS_BACK ?= 7
TRACKER_LOOKBACK_DAYS ?= 3
DIAGNOSTIC_OUTPUT ?= $(OUTPUT_DIR)/report-alignment-$(shell date -u +%Y%m%dT%H%M%SZ).json
DIAGNOSTIC_SNAPSHOT ?=
TAG ?=
DAYS_BACK ?= 7
ASSIGNEE ?=
REPORT_STATUS ?=
TRACKER_ID ?=
SENT_DATE ?=
SEND_EMAIL ?= 0
REPLAY_ID ?=
REPORT_RUN_IDS ?=
MANUAL_TRACKER_IDS ?=
APPLY ?= 0
IMPORT_DIR ?= $(PWD)
INPUT_CSV ?=
INPUT_XLSX ?=
STAKEHOLDER_IMPORT_OUTPUT ?= $(OUTPUT_DIR)/WAS_Stakeholders_import_ready.csv

.PHONY: install test lint build menu help report-help xml-help inventory admin-help mailer-help stakeholders-help special-cases stakeholder-export stakeholder-import tracker-csv tracker-import tracker-table tracker-mark-sent report-errors update-tracker update-tracker-delete-apps assignee-digests recent-scan-batch recent-scan-batch-assignee-test recent-scan-batch-test single-report manual-report

install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install --no-deps -e .

test:
	cd $(REPO_ROOT) && PYTHONPATH=backend/was/src $(ROOT_PYTHON) -m unittest discover -s backend/was/tests

lint:
	cd $(REPO_ROOT) && $(ROOT_PYTHON) -m flake8 \
		--extend-exclude=backend/was/src/was_reports/resources/pdf_redactor.py,backend/was/src/was_reports/resources/redact_qualys.py \
		backend/was/src/was_reports backend/was/src/was_mailer backend/was/tests

build:
	docker build -t $(IMAGE) .

menu:
	mkdir -p $(OUTPUT_DIR)
	docker run --rm -it $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output -v $(IMPORT_DIR):/backend/was:ro $(IMAGE) was-menu

help:
	docker run --rm $(IMAGE) --help

report-help:
	docker run --rm $(IMAGE) was-reports --help

xml-help:
	docker run --rm $(IMAGE) was-export-xml --help

inventory:
	mkdir -p $(OUTPUT_DIR)
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) was-inventory

admin-help:
	docker run --rm $(IMAGE) was-admin --help

mailer-help:
	docker run --rm --entrypoint ./worker/was-mailer-start.sh $(IMAGE) --help

stakeholders-help:
	docker run --rm $(IMAGE) was-stakeholders --help

.PHONY: recent-scan-batch-preflight recent-scan-batch-preflight-local

.PHONY: report-alignment-diagnostic-local

report-alignment-diagnostic-local:
	mkdir -p "$(dir $(DIAGNOSTIC_OUTPUT))"
	PYTHONPATH=src $(PYTHON) scripts/diagnose_report_alignment.py --days-back "$(BATCH_DAYS_BACK)" --discovery-days "$(TRACKER_LOOKBACK_DAYS)" --output "$(DIAGNOSTIC_OUTPUT)" $(if $(strip $(DIAGNOSTIC_SNAPSHOT)),--snapshot "$(DIAGNOSTIC_SNAPSHOT)")

recent-scan-batch-preflight:
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) --entrypoint python $(IMAGE) -m was_reports.commands.batch_preflight --days-back "$(BATCH_DAYS_BACK)" $(if $(strip $(TAG)),--tag "$(TAG)")

recent-scan-batch-preflight-local:
	PYTHONPATH=src $(PYTHON) -m was_reports.commands.batch_preflight --days-back "$(BATCH_DAYS_BACK)" $(if $(strip $(TAG)),--tag "$(TAG)")

recent-scan-batch:
	mkdir -p $(OUTPUT_DIR)
	@case "$(BATCH_WORKERS)" in ''|*[!0-9]*) echo 'BATCH_WORKERS must be an integer from 1 through 30.' >&2; exit 2 ;; esac
	@test "$(BATCH_WORKERS)" -ge 1 -a "$(BATCH_WORKERS)" -le 30 || (echo 'BATCH_WORKERS must be from 1 through 30.' >&2; exit 2)
	@set -u; \
	batch_id=$$(docker run --rm --entrypoint python $(IMAGE) -c 'import uuid; print(uuid.uuid4())') || exit 1; \
	test -n "$$batch_id" || exit 1; \
	echo "WAS analyst batch ID: $$batch_id"; \
	send_summary() { \
		docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) \
			-e WAS_ANALYST_BATCH_ID="$$batch_id" -v $(OUTPUT_DIR):/output \
			--entrypoint python $(IMAGE) -m was_reports.reporting.analyst_summaries \
			--phase "$$1" --batch-id "$$batch_id" --days-back "$(BATCH_DAYS_BACK)" \
			$(if $(strip $(BATCH_TEST_RECIPIENTS)),--test-recipients "$(BATCH_TEST_RECIPIENTS)"); \
	}; \
	echo 'Phase 1/5: Refreshing the daily tracker.'; \
	if ! docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) \
		-e WAS_ANALYST_BATCH_ID="$$batch_id" -v $(OUTPUT_DIR):/output \
		$(IMAGE) was-update-tracker --lookback-days "$(TRACKER_LOOKBACK_DAYS)"; then \
		send_summary final || true; exit 1; \
	fi; \
	echo 'Phase 2/5: Calculating workload and sending one tracker summary.'; \
	if ! docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) \
		-e WAS_ANALYST_BATCH_ID="$$batch_id" -v $(OUTPUT_DIR):/output \
		$(IMAGE) --recent-scans --skip-tracker-refresh --preflight-only --days-back "$(BATCH_DAYS_BACK)"; then \
		send_summary final || true; exit 1; \
	fi; \
	send_summary tracker || exit 1; \
	echo 'Phase 3/5: Generating reports with $(BATCH_WORKERS) parallel workers.'; \
	worker_pids=''; \
	stop_workers() { \
		if [ -n "$$worker_pids" ]; then kill $$worker_pids 2>/dev/null || true; fi; \
	}; \
	trap 'stop_workers; exit 130' INT TERM; \
	worker_index=0; \
	while [ "$$worker_index" -lt "$(BATCH_WORKERS)" ]; do \
		echo "Starting WAS report container $$((worker_index + 1)) of $(BATCH_WORKERS)."; \
		docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) \
			-e WAS_ANALYST_BATCH_ID="$$batch_id" -v $(OUTPUT_DIR):/output \
			$(IMAGE) --recent-scans --skip-tracker-refresh \
			--worker-count "$(BATCH_WORKERS)" --worker-index "$$worker_index" \
			--create-missing-password --continue-on-error --days-back "$(BATCH_DAYS_BACK)" \
			--send-email $(if $(strip $(BATCH_TEST_RECIPIENTS)),--test-recipients "$(BATCH_TEST_RECIPIENTS)") \
			--skip-ready-email-retry & \
		worker_pids="$$worker_pids $$!"; \
		worker_index=$$((worker_index + 1)); \
	done; \
	worker_status=0; \
	for worker_pid in $$worker_pids; do \
		if ! wait "$$worker_pid"; then worker_status=1; fi; \
	done; \
	trap - INT TERM; \
	echo 'Phase 4/5: Report workers finished. Delivering completed reports once.'; \
	mailer_status=0; \
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) \
		-e WAS_ANALYST_BATCH_ID="$$batch_id" -v $(OUTPUT_DIR):/output \
		--entrypoint was-mailer $(IMAGE) --all-ready --include-previous-failures \
		--days-back "$(BATCH_DAYS_BACK)" \
		$(if $(strip $(BATCH_TEST_RECIPIENTS)),--test-recipients "$(BATCH_TEST_RECIPIENTS)") || mailer_status=$$?; \
	echo 'Phase 5/5: Sending one combined analyst batch summary.'; \
	digest_status=0; \
	send_summary final || digest_status=$$?; \
	if [ "$$worker_status" -ne 0 ] || [ "$$mailer_status" -ne 0 ] || [ "$$digest_status" -ne 0 ]; then \
		echo 'Parallel WAS batch completed with one or more failures. Review local-output/logs.' >&2; \
		exit 1; \
	fi; \
	echo 'Parallel WAS batch completed successfully.'

recent-scan-batch-assignee-test:
	@test -n "$(TEST_RECIPIENTS)" -a "$(TEST_RECIPIENTS)" != 'operator@example.gov' || (echo 'Set TEST_RECIPIENTS to an email-enabled WAS functional-test recipient.' >&2; exit 2)
	@echo 'All batch reports and digests will be sent only to $(TEST_RECIPIENTS).'
	@echo 'Report lookback: $(BATCH_DAYS_BACK) calendar days (all removes the date limit).'
	$(MAKE) recent-scan-batch BATCH_WORKERS="$(BATCH_WORKERS)" BATCH_TEST_RECIPIENTS="$(TEST_RECIPIENTS)" BATCH_DAYS_BACK="$(BATCH_DAYS_BACK)"

recent-scan-batch-test:
	mkdir -p $(OUTPUT_DIR)
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) --recent-scans --create-missing-password --continue-on-error --send-email --send-assignee-digests --test-recipients "$(TEST_RECIPIENTS)" --dry-run-email --limit 1

single-report:
	@test -n "$(TAG)" || (echo 'TAG is required. Use: make single-report TAG="CUSTOMER_TAG"' >&2; exit 1)
	mkdir -p $(OUTPUT_DIR)
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) --recent-scans --tag "$(TAG)" --create-missing-password --send-email

manual-report:
	@test -n "$(TAG)" || (echo 'TAG is required. Use: make manual-report TAG="CUSTOMER_TAG"' >&2; exit 1)
	mkdir -p $(OUTPUT_DIR)
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) --recent-scans --skip-tracker-refresh --tag "$(TAG)" --include-manual --create-missing-password --continue-on-error --send-email --limit 1

.PHONY: on-demand-report

on-demand-report:
	@test -n "$(TAG)" || (echo 'TAG is required.' >&2; exit 1)
	mkdir -p $(OUTPUT_DIR)
	@set -- --tag "$(TAG)" --create-missing-password; \
	if [ -n "$(TRACKER_ID)" ]; then set -- "$$@" --tracker-id "$(TRACKER_ID)"; fi; \
	case "$(SEND_EMAIL)" in \
	  0) ;; \
	  1) test -n "$(TEST_RECIPIENTS)" && test "$(TEST_RECIPIENTS)" != 'operator@example.gov' || { echo 'Set TEST_RECIPIENTS to an approved address.' >&2; exit 1; }; \
	     set -- "$$@" --send-email --test-recipients "$(TEST_RECIPIENTS)" ;; \
	  *) echo 'SEND_EMAIL must be 0 or 1.' >&2; exit 1 ;; \
	esac; \
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output --entrypoint was-report-on-demand $(IMAGE) "$$@"

.PHONY: test-report-replay

test-report-replay:
	@test -n "$(TEST_RECIPIENTS)" -a "$(TEST_RECIPIENTS)" != 'operator@example.gov' || (echo 'Set TEST_RECIPIENTS to an email-enabled assignee.' >&2; exit 2)
	@set -- --days-back "$(DAYS_BACK)" --test-recipients "$(TEST_RECIPIENTS)"; \
	if [ -n "$(REPORT_RUN_IDS)" ]; then set -- "$$@" --report-run-ids "$(REPORT_RUN_IDS)"; fi; \
	if [ -n "$(MANUAL_TRACKER_IDS)" ]; then set -- "$$@" --manual-tracker-ids "$(MANUAL_TRACKER_IDS)"; fi; \
	if [ -n "$(REPLAY_ID)" ]; then set -- "$$@" --replay-id "$(REPLAY_ID)"; fi; \
	case "$(APPLY)" in \
	  0) ;; \
	  1) test -n "$(REPLAY_ID)" || { echo 'APPLY=1 requires REPLAY_ID, a stable UUID.' >&2; exit 2; }; \
	     mkdir -p "$(OUTPUT_DIR)"; set -- "$$@" --apply ;; \
	  *) echo 'APPLY must be 0 or 1.' >&2; exit 2 ;; \
	esac; \
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output \
	  --entrypoint python $(IMAGE) -m was_reports.commands.test_replay "$$@"

special-cases:
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) was-special-cases list

stakeholder-export:
	mkdir -p $(OUTPUT_DIR)
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) was-stakeholders export-csv --output /output/was-stakeholders.csv

stakeholder-import:
	@test -n "$(INPUT_CSV)" || (echo 'INPUT_CSV is required. Use: make stakeholder-import INPUT_CSV="/path/to/file.csv"' >&2; exit 1)
	@test -f "$(INPUT_CSV)" || (echo 'INPUT_CSV does not exist or is not a file.' >&2; exit 1)
	mkdir -p $(OUTPUT_DIR)
	@input_directory="$$(cd "$$(dirname "$(INPUT_CSV)")" && pwd)"; \
	input_name="$$(basename "$(INPUT_CSV)")"; \
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) \
		-v "$$input_directory:/input:ro" \
		-v "$(OUTPUT_DIR):/output" \
		$(IMAGE) was-stakeholders import-csv \
		--input "/input/$$input_name" \
		--prepared-output "/output/$$(basename "$(STAKEHOLDER_IMPORT_OUTPUT)")" \
		--confirm

tracker-csv:
	mkdir -p $(OUTPUT_DIR)
	@if [ -n "$(ASSIGNEE)" ]; then \
		docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) was-tracker export-csv --assignee "$(ASSIGNEE)" --days-back "$(DAYS_BACK)" --output /output/was-daily-tracker.csv; \
	else \
		docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) was-tracker export-csv --output /output/was-daily-tracker.csv; \
	fi

tracker-import:
	@test -n "$(INPUT_XLSX)" || (echo 'INPUT_XLSX is required. Use: make tracker-import INPUT_XLSX="/path/to/file.xlsx"' >&2; exit 1)
	@test -f "$(INPUT_XLSX)" || (echo 'INPUT_XLSX does not exist or is not a file.' >&2; exit 1)
	@input_directory="$$(cd "$$(dirname "$(INPUT_XLSX)")" && pwd)"; \
	input_name="$$(basename "$(INPUT_XLSX)")"; \
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) \
		-v "$$input_directory:/input:ro" \
		$(IMAGE) was-tracker import-xlsx --input "/input/$$input_name" --confirm

tracker-table:
	mkdir -p $(OUTPUT_DIR)
	@set -- was-tracker show --days-back "$(DAYS_BACK)"; \
	if [ -n "$(ASSIGNEE)" ]; then set -- "$$@" --assignee "$(ASSIGNEE)"; fi; \
	if [ -n "$(REPORT_STATUS)" ]; then set -- "$$@" --report-status "$(REPORT_STATUS)"; fi; \
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) "$$@"

report-errors:
	mkdir -p $(OUTPUT_DIR)
	@set -- was-tracker errors --days-back "$(DAYS_BACK)"; \
	if [ -n "$(TAG)" ]; then set -- "$$@" --tag "$(TAG)"; fi; \
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) "$$@"

tracker-mark-sent:
	@test -n "$(TRACKER_ID)" || (echo 'TRACKER_ID is required.' >&2; exit 1)
	@test -n "$(SENT_DATE)" || (echo 'SENT_DATE is required in YYYY-MM-DD format.' >&2; exit 1)
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) was-tracker mark-sent --tracker-id "$(TRACKER_ID)" --sent-date "$(SENT_DATE)" --confirm

update-tracker:
	mkdir -p $(OUTPUT_DIR)
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) was-update-tracker

update-tracker-delete-apps:
	mkdir -p $(OUTPUT_DIR)
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) was-update-tracker --delete-apps

assignee-digests:
	@test -n "$(BATCH_ID)" || (echo 'BATCH_ID is required for a combined batch summary.' >&2; exit 1)
	mkdir -p $(OUTPUT_DIR)
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output --entrypoint python $(IMAGE) -m was_reports.reporting.analyst_summaries --phase final --batch-id "$(BATCH_ID)" --dry-run
