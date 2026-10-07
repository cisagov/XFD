.PHONY: init plan apply format migrate

init:
	terraform init -input=false
plan:
	terraform plan -out plan
apply:
	terraform apply plan
format:
	terraform validate && terraform fmt -recursive
migrate:
	terraform init -backend-config=state.config -migrate-state
