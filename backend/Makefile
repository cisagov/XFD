.PHONY: syncdb
.PHONY: populate-cache
.PHONY: pytest

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

syncmdl-dangerously-force:
	docker compose exec backend python manage.py syncmdl --dangerouslyforce

# Syncronize the secondary database
syncmdl_secondary:
	docker compose exec backend python manage.py syncmdl_secondary

syncmdl_secondary-dangerously-force:
	docker compose exec backend python manage.py syncmdl_secondary --dangerouslyforce

# Pytest
# i.e. make pytest FILE=xfd_api/tests/test_domain.py
pytest:
	docker compose exec backend python manage.py makemigrations
	docker compose exec backend pytest --no-migrations --reuse-db $(FILE)

pylint:
	docker compose exec backend sh -c "PYTHONPATH=/app pylint ."

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
