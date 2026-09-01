PYTHON ?= ../../cd_WAS_update/bin/python
REPO_ROOT ?= ../..
ROOT_PYTHON ?= ./cd_WAS_update/bin/python
IMAGE ?= was-reporting
ENV_FILE ?= .env
OUTPUT_DIR ?= $(PWD)/local-output
TRACKER_CSV ?= $(OUTPUT_DIR)/was-daily-tracker.csv
TEST_RECIPIENTS ?= operator@example.gov
TAG ?=
DAYS_BACK ?= 7
ASSIGNEE ?=

.PHONY: install test lint build help report-help xml-help inventory admin-help mailer-help special-cases tracker-csv tracker-table update-tracker update-tracker-delete-apps assignee-digests recent-scan-batch recent-scan-batch-test single-report

install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install --no-deps -e .

test:
	cd $(REPO_ROOT) && PYTHONPATH=backend/was/src $(ROOT_PYTHON) -m unittest discover -s backend/was/tests

lint:
	cd $(REPO_ROOT) && $(ROOT_PYTHON) -m flake8 \
		--extend-exclude=backend/was/src/was_reports/resources/pdf_redactor.py,backend/was/src/was_reports/resources/redact_qualys.py \
		backend/was/src/was_reports backend/was/src/was_mailer backend/was/tests backend/was/update_tracker/update_tracker/set_up.py backend/was/update_tracker/update_tracker/data/search_customer_data.py backend/was/update_tracker/update_tracker/data/update_customer_data.py backend/was/update_tracker/update_tracker/data/special_reqs.py backend/was/update_tracker/update_tracker/utils/qualys_api_search/search_schedules.py backend/was/update_tracker/update_tracker/utils/tracker_operations/update_tracker.py

build:
	docker build -t $(IMAGE) .

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

recent-scan-batch:
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) --recent-scans --create-missing-password --continue-on-error --send-email --send-assignee-digests

recent-scan-batch-test:
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) --recent-scans --create-missing-password --continue-on-error --send-email --send-assignee-digests --test-recipients "$(TEST_RECIPIENTS)" --dry-run-email --limit 1

single-report:
	@test -n "$(TAG)" || (echo 'TAG is required. Use: make single-report TAG="CUSTOMER_TAG"' >&2; exit 1)
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) --recent-scans --tag "$(TAG)" --create-missing-password --send-email

special-cases:
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) was-special-cases list

tracker-csv:
	mkdir -p $(OUTPUT_DIR)
	docker run --rm --env-file $(ENV_FILE) -v $(OUTPUT_DIR):/output $(IMAGE) was-tracker export-csv --output /output/was-daily-tracker.csv

tracker-table:
	@test -n "$(ASSIGNEE)" || (echo 'ASSIGNEE is required. Use: make tracker-table ASSIGNEE="ASSIGNEE NAME" DAYS_BACK=7' >&2; exit 1)
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) was-tracker show --assignee "$(ASSIGNEE)" --days-back "$(DAYS_BACK)"

update-tracker:
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) was-update-tracker

update-tracker-delete-apps:
	docker run --rm --env-file $(ENV_FILE) $(IMAGE) was-update-tracker --delete-apps

assignee-digests:
	docker run --rm --env-file $(ENV_FILE) --entrypoint ./worker/was-mailer-start.sh $(IMAGE) --assignee-digests --dry-run
