# Posture & Exposure (P&E) — run from repo root or backend/pe:
#   make -C backend/pe start
#   make -C backend/pe build
#   make -C backend/pe syncdb-populate
#   make -C backend/pe run SCANS=dnstwist ORGS=DHS COUNT=1

REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
PE_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
COMPOSE := docker compose -f $(REPO_ROOT)/docker-compose.yml -f $(REPO_ROOT)/docker-compose.override.local.yml
COMPOSE_PE := $(COMPOSE) --profile pe
PE_STACK_SERVICES := db elasticmq backend

# Queue local scans via peScanController (backend container must be running).
PE_QUEUE = $(COMPOSE) exec -T -e PYTHONPATH=/app:/app/pe/src backend python /app/pe/tools/queue_local_scans.py
PE_REPORT_QUEUE = $(COMPOSE) exec -T -e PYTHONPATH=/app backend python /app/pe/tools/queue_local_reports.py

.PHONY: help start stop build up down logs test syncdb syncdb-populate syncdb-dangerously-force run queue scans scans-orgs watch-queues queue-status run-reports

REPORT_CONTAINER_PATH ?= /tmp/pe-reports
PE_MANAGE = $(COMPOSE) exec -T -w /app/pe/pe_reports_django_project \
	-e DJANGO_SETTINGS_MODULE=pe_reports_django.settings \
	-e PYTHONPATH=/app/pe/pe_reports_django_project:/app/pe/src \
	backend python manage.py

help:
	@echo "P&E Makefile targets:"
	@echo "  start            Start db, elasticmq, and backend (slim local stack)"
	@echo "  stop             Stop db, elasticmq, and backend"
	@echo "  build            Build pe-worker Docker image"
	@echo "  up               Start pe-worker (compose profile pe)"
	@echo "  down             Stop pe-worker"
	@echo "  logs             Tail pe-worker logs"
	@echo "  test             Run pe/ unit tests"
	@echo "  syncdb           Create PE DB and sync all table models from home/models.py"
	@echo "  syncdb-populate  syncdb + sample data sources/orgs (dnstwist, flare_events, ...)"
	@echo "  run              Queue orgs + start workers (SCANS= ORGS= COUNT=)"
	@echo "  queue            run with QUEUE_ONLY=true"
	@echo "  scans            run with sample orgs fixture"
	@echo "  scans-orgs       Alias for run with explicit ORGS="
	@echo "  watch-queues     Poll AWS queues until empty (SCANS= INTERVAL=)"
	@echo "  queue-status     One-shot queue depth (SCANS=)"
	@echo "  run-reports      Start report container; OUTPUT_DIR= copies PDFs when done"
	@echo ""
	@echo "ORGS is comma-separated (e.g. ORGS=DHS,DHS_CISA). Shortcuts must be used alone:"
	@echo "  all / DEMO       batch: 1 queue message -> one worker scans all orgs in one job"
	@echo "  all-orgs / demo-orgs  parallel: 1 queue message per org from PE DB; use COUNT=N"

start:
	$(COMPOSE) up -d --build $(PE_STACK_SERVICES)

stop:
	$(COMPOSE) stop $(PE_STACK_SERVICES)

build:
	$(PE_DIR)/tools/build.sh

up:
	$(COMPOSE_PE) up -d --no-build pe-worker

down:
	$(COMPOSE_PE) stop pe-worker

logs:
	$(COMPOSE_PE) logs -f pe-worker

test:
	cd $(PE_DIR) && pip install -q -e ".[test]" && PYTHONPATH=..:.:src:pe_reports_django_project python -m unittest discover -s tests -v

syncdb:
	$(PE_MANAGE) pesyncdb

syncdb-populate:
	$(PE_MANAGE) pesyncdb --populate

syncdb-dangerously-force:
	$(PE_MANAGE) pesyncdb --dangerouslyforce

# Invoke peScanController locally
#   make -C backend/pe run SCANS=dnstwist ORGS=DHS COUNT=1
#   make -C backend/pe run SCANS=dnstwist ORGS=DHS,DHS_CISA COUNT=2   # one message per org
#   make -C backend/pe run SCANS=dnstwist ORGS=all COUNT=1     # batch: one job, all report_on orgs
#   make -C backend/pe run SCANS=dnstwist ORGS=all-orgs COUNT=3 # parallel: one message per org
PE_RUN_EXTRA = $(if $(COUNT),--count $(COUNT),) $(if $(filter true,$(QUEUE_ONLY)),--queue-only,) $(if $(filter true,$(TASKS_ONLY)),--tasks-only,)

run:
	@test -n "$(SCANS)" || (echo "SCANS is required, e.g. make run SCANS=dnstwist ORGS=DHS" && exit 1)
ifdef ORGS_FILE
	$(PE_QUEUE) --scans=$(SCANS) --orgs-file $(ORGS_FILE) $(PE_RUN_EXTRA)
else ifdef TASKS_ONLY
	$(PE_QUEUE) --scans=$(SCANS) $(PE_RUN_EXTRA)
else
	@test -n "$(ORGS)" || (echo "ORGS is required (or set ORGS_FILE= or TASKS_ONLY=true)" && exit 1)
	$(PE_QUEUE) --scans=$(SCANS) --orgs=$(ORGS) $(PE_RUN_EXTRA)
endif

queue:
	@$(MAKE) -C $(PE_DIR) run SCANS=$(SCANS) ORGS=$(ORGS) COUNT=$(COUNT) QUEUE_ONLY=true

scans:
	@$(MAKE) -C $(PE_DIR) run SCANS=$(SCANS) ORGS_FILE=/app/pe/fixtures/sample-orgs.json COUNT=$(COUNT)

scans-orgs:
	@$(MAKE) -C $(PE_DIR) run SCANS=$(SCANS) ORGS=$(ORGS) COUNT=$(COUNT)

WATCH_INTERVAL ?= 30
watch-queues:
	@test -n "$(SCANS)" || (echo "SCANS is required, e.g. make watch-queues SCANS=dnstwist" && exit 1)
	$(PE_DIR)/tools/watch_queues.sh --scans "$(SCANS)" --interval "$(WATCH_INTERVAL)"

queue-status:
	@test -n "$(SCANS)" || (echo "SCANS is required, e.g. make queue-status SCANS=dnstwist" && exit 1)
	$(PE_DIR)/tools/watch_queues.sh --scans "$(SCANS)" --once

# Invoke peReportController locally (self-contained pe-worker container, like scans).
#   make -C backend/pe start build
#   make -C backend/pe run-reports REPORT_DATE=2026-07-15 ORGS=DHS OUTPUT_DIR=~/reports
run-reports:
	@test -n "$(REPORT_DATE)" || (echo "REPORT_DATE is required (YYYY-MM-DD)" && exit 1)
	REPORT_DATE="$(REPORT_DATE)" ORGS="$(or $(ORGS),all)" OUTPUT_DIR="$(OUTPUT_DIR)" \
		COUNT="$(COUNT)" SOC_MED="$(or $(SOC_MED),false)" \
		REPORT_CONTAINER_PATH="$(REPORT_CONTAINER_PATH)" \
		"$(PE_DIR)/tools/run_local_reports.sh"
