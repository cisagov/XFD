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
TAG ?=
DAYS_BACK ?= 7
ASSIGNEE ?=
REPORT_STATUS ?=
TRACKER_ID ?=
SENT_DATE ?=
SEND_EMAIL ?= 0
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

recent-scan-batch-preflight:
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) --entrypoint python $(IMAGE) -m was_reports.commands.batch_preflight --days-back "$(BATCH_DAYS_BACK)" $(if $(strip $(TAG)),--tag "$(TAG)")

recent-scan-batch-preflight-local:
	PYTHONPATH=src $(PYTHON) -m was_reports.commands.batch_preflight --days-back "$(BATCH_DAYS_BACK)" $(if $(strip $(TAG)),--tag "$(TAG)")

recent-scan-batch:
	mkdir -p $(OUTPUT_DIR)
	@case "$(BATCH_WORKERS)" in ''|*[!0-9]*) echo 'BATCH_WORKERS must be an integer from 1 through 30.' >&2; exit 2 ;; esac
	@test "$(BATCH_WORKERS)" -ge 1 -a "$(BATCH_WORKERS)" -le 30 || (echo 'BATCH_WORKERS must be from 1 through 30.' >&2; exit 2)
	@echo 'Phase 1/5: Refreshing the daily tracker.'
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) was-update-tracker --lookback-days "$(TRACKER_LOOKBACK_DAYS)"
	@echo 'Phase 2/5: Calculating the report workload before generation.'
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) --recent-scans --skip-tracker-refresh --preflight-only --days-back "$(BATCH_DAYS_BACK)"
	@echo 'Phase 3/5: Generating reports with $(BATCH_WORKERS) parallel workers.'
	@set -u; \
	worker_pids=''; \
	stop_workers() { \
		if [ -n "$$worker_pids" ]; then kill $$worker_pids 2>/dev/null || true; fi; \
	}; \
	trap 'stop_workers; exit 130' INT TERM; \
	worker_index=0; \
	while [ "$$worker_index" -lt "$(BATCH_WORKERS)" ]; do \
		echo "Starting WAS report container $$((worker_index + 1)) of $(BATCH_WORKERS)."; \
		docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) \
			-v $(OUTPUT_DIR):/output \
			$(IMAGE) \
			--recent-scans \
			--skip-tracker-refresh \
			--worker-count "$(BATCH_WORKERS)" \
			--worker-index "$$worker_index" \
			--create-missing-password \
			--continue-on-error \
			$(if $(strip $(BATCH_DAYS_BACK)),--days-back "$(BATCH_DAYS_BACK)") \
			--send-email \
			$(if $(strip $(BATCH_TEST_RECIPIENTS)),--test-recipients "$(BATCH_TEST_RECIPIENTS)") \
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
		-v $(OUTPUT_DIR):/output \
		--entrypoint was-mailer \
		$(IMAGE) --all-ready --include-previous-failures \
		$(if $(strip $(BATCH_DAYS_BACK)),--days-back "$(BATCH_DAYS_BACK)") \
		$(if $(strip $(BATCH_TEST_RECIPIENTS)),--test-recipients "$(BATCH_TEST_RECIPIENTS)") || mailer_status=$$?; \
	echo 'Phase 5/5: Report delivery finished. Sending assignee digests once.'; \
	digest_status=0; \
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) \
		-v $(OUTPUT_DIR):/output \
		--entrypoint was-mailer \
		$(IMAGE) --assignee-digests --include-previous-failures \
		$(if $(strip $(BATCH_DAYS_BACK)),--days-back "$(BATCH_DAYS_BACK)") \
		$(if $(strip $(BATCH_TEST_RECIPIENTS)),--test-recipients "$(BATCH_TEST_RECIPIENTS)") || digest_status=$$?; \
	if [ "$$worker_status" -ne 0 ] || [ "$$mailer_status" -ne 0 ] || [ "$$digest_status" -ne 0 ]; then \
		echo 'Parallel WAS batch completed with one or more failures. Review local-output/logs.' >&2; \
		exit 1; \
	fi; \
	echo 'Parallel WAS batch completed successfully.'

recent-scan-batch-assignee-test:
	@test -n "$(TEST_RECIPIENTS)" -a "$(TEST_RECIPIENTS)" != 'operator@example.gov' || (echo 'Set TEST_RECIPIENTS to an email-enabled WAS functional-test recipient.' >&2; exit 2)
	@echo 'All batch reports and digests will be sent only to $(TEST_RECIPIENTS).'
	@echo 'Only tracker work from the previous 30 calendar days will be processed.'
	$(MAKE) recent-scan-batch BATCH_WORKERS="$(BATCH_WORKERS)" BATCH_TEST_RECIPIENTS="$(TEST_RECIPIENTS)" BATCH_DAYS_BACK="30"

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
	mkdir -p $(OUTPUT_DIR)
	docker run --rm $(DOCKER_HOST_USER) --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output --entrypoint ./worker/was-mailer-start.sh $(IMAGE) --assignee-digests --dry-run
