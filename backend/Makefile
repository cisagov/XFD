.PHONY: syncdb
.PHONY: populate-cache
.PHONY: pytest
.PHONY: pe-test
.PHONY: pe-requirements-audit
.PHONY: pe-worker-smoke

# Synchronize and populate the database
syncdb:
	docker compose exec backend python manage.py syncdb

syncdb-populate:
	docker compose exec backend python manage.py syncdb --populate

syncdb-dangerously-force:
	docker compose exec backend python manage.py syncdb --dangerouslyforce


# Synchronize and populate the database
syncmdl:
	docker compose exec backend python manage.py syncmdl

syncmdl-populate:
	docker compose exec backend python manage.py syncmdl --populate

syncmdl-dangerously-force:
	docker compose exec backend python manage.py syncmdl --dangerouslyforce

syncmdl-metrics:
	docker compose exec backend python manage.py syncmdl --metrics

# Synchronize the secondary database
syncmdl_secondary:
	docker compose exec backend python manage.py syncmdl_secondary

syncmdl_secondary-dangerously-force:
	docker compose exec backend python manage.py syncmdl_secondary --dangerouslyforce

# Pytest
# i.e. make pytest FILE=xfd_api/tests/test_domain.py
pytest:
	docker compose exec backend python manage.py makemigrations
ifeq ($(MODE),reset)
	docker compose exec backend pytest --create-db $(FILE)
else
	docker compose exec backend pytest --no-migrations --reuse-db $(FILE)
endif

pylint:
	docker compose exec backend sh -c "PYTHONPATH=/app pylint ."

# PE unit tests (unittest; no Docker required)
pe-test:
	cd pe && pip install -q -e . && \
	  PYTHONPATH=..:.:src:pe_reports_django_project \
	  python -m unittest discover -s tests -v

# Audit pinned PE worker dependencies for known CVEs
pe-requirements-audit:
	python -m pip install -q pip-audit
	pip-audit -r pe/requirements.txt

# Verify the pe-worker image built from backend/pe/Dockerfile
pe-worker-smoke:
	docker run --rm pe-worker pe-source --help
	docker run --rm pe-worker python -c "import pe_source.dnstwistscript"

# Redis lambdas
populate-cache:
	docker compose exec backend python manage.py populate_services_cache
	docker compose exec backend python manage.py populate_ports_cache
	docker compose exec backend python manage.py populate_vulns_cache
	docker compose exec backend python manage.py populate_most_common_vulns_cache
	docker compose exec backend python manage.py populate_latest_vulns_cache
	docker compose exec backend python manage.py populate_severity_count_cache
	docker compose exec backend python manage.py populate_by_orgs_cache

# Run scan execution locally with RabbitMQ and Docker
local-scan-execution:
	docker compose exec backend python manage.py local_scan_execution --scan-type=dnstwist --desired-count=1 --org-list="National Science Foundation (NSF) - CISA"

# Create local dev api key. ONLY run this after initial login, since that is when the user(user is tied to api_key) is created
generate-dev-api-key:
	docker compose exec backend python manage.py generate_dev_api_key

# Import test users to db
import-test-users:
	FILE_BASENAME=$$(basename $(FILE)); \
	docker compose cp $(FILE) backend:/tmp/$$FILE_BASENAME; \
	docker compose exec backend python manage.py import_test_users /tmp/$$FILE_BASENAME
