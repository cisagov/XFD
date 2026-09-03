PYTHON ?= ../../cd_WAS_update/bin/python
REPO_ROOT ?= ../..
ROOT_PYTHON ?= ./cd_WAS_update/bin/python
IMAGE ?= was-reporting
ENV_FILE ?= .env
OUTPUT_DIR ?= $(PWD)/local-output
TRACKER_CSV ?= $(OUTPUT_DIR)/was-daily-tracker.csv
STAKEHOLDER_CSV ?= $(OUTPUT_DIR)/was-stakeholders.csv
TEST_RECIPIENTS ?= operator@example.gov
TAG ?=
DAYS_BACK ?= 7
ASSIGNEE ?=
REPORT_STATUS ?=
TRACKER_ID ?=
SENT_DATE ?=

.PHONY: install test lint build menu help report-help xml-help inventory admin-help mailer-help stakeholders-help special-cases stakeholder-export tracker-csv tracker-table tracker-mark-sent report-errors update-tracker update-tracker-delete-apps assignee-digests recent-scan-batch recent-scan-batch-test single-report manual-report

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
	docker run --rm -it --user "$$(id -u):$$(id -g)" --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) was-menu

help:
	docker run --rm $(IMAGE) --help

report-help:
	docker run --rm $(IMAGE) was-reports --help

xml-help:
	docker run --rm $(IMAGE) was-export-xml --help

inventory:
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) was-inventory

admin-help:
	docker run --rm $(IMAGE) was-admin --help

mailer-help:
	docker run --rm --entrypoint ./worker/was-mailer-start.sh $(IMAGE) --help

stakeholders-help:
	docker run --rm $(IMAGE) was-stakeholders --help

recent-scan-batch:
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) --recent-scans --create-missing-password --continue-on-error --send-email --send-assignee-digests

recent-scan-batch-test:
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) --recent-scans --create-missing-password --continue-on-error --send-email --send-assignee-digests --test-recipients "$(TEST_RECIPIENTS)" --dry-run-email --limit 1

single-report:
	@test -n "$(TAG)" || (echo 'TAG is required. Use: make single-report TAG="CUSTOMER_TAG"' >&2; exit 1)
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) --recent-scans --tag "$(TAG)" --create-missing-password --send-email

manual-report:
	@test -n "$(TAG)" || (echo 'TAG is required. Use: make manual-report TAG="CUSTOMER_TAG"' >&2; exit 1)
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) --recent-scans --skip-tracker-refresh --tag "$(TAG)" --include-manual --create-missing-password --continue-on-error --send-email --limit 1

special-cases:
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) was-special-cases list

stakeholder-export:
	mkdir -p $(OUTPUT_DIR)
	docker run --rm --user "$$(id -u):$$(id -g)" --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) was-stakeholders export-csv --output /output/was-stakeholders.csv

tracker-csv:
	mkdir -p $(OUTPUT_DIR)
	@if [ -n "$(ASSIGNEE)" ]; then \
		docker run --rm --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) was-tracker export-csv --assignee "$(ASSIGNEE)" --days-back "$(DAYS_BACK)" --output /output/was-daily-tracker.csv; \
	else \
		docker run --rm --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) was-tracker export-csv --output /output/was-daily-tracker.csv; \
	fi

tracker-table:
	@set -- was-tracker show --days-back "$(DAYS_BACK)"; \
	if [ -n "$(ASSIGNEE)" ]; then set -- "$$@" --assignee "$(ASSIGNEE)"; fi; \
	if [ -n "$(REPORT_STATUS)" ]; then set -- "$$@" --report-status "$(REPORT_STATUS)"; fi; \
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) "$$@"

report-errors:
	@set -- was-tracker errors --days-back "$(DAYS_BACK)"; \
	if [ -n "$(TAG)" ]; then set -- "$$@" --tag "$(TAG)"; fi; \
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) "$$@"

tracker-mark-sent:
	@test -n "$(TRACKER_ID)" || (echo 'TRACKER_ID is required.' >&2; exit 1)
	@test -n "$(SENT_DATE)" || (echo 'SENT_DATE is required in YYYY-MM-DD format.' >&2; exit 1)
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) was-tracker mark-sent --tracker-id "$(TRACKER_ID)" --sent-date "$(SENT_DATE)" --confirm

update-tracker:
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) was-update-tracker

update-tracker-delete-apps:
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) was-update-tracker --delete-apps

assignee-digests:
	docker run --rm --env-file $(ENV_FILE) --entrypoint ./worker/was-mailer-start.sh $(IMAGE) --assignee-digests --dry-run
