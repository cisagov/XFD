.PHONY: init plan apply format

# Runner token is passed at plan/apply time, not stored in a file:
# make plan RUNNER_TOKEN=xxxxxxxx
# make apply

init:
	terraform init -backend-config=cisadev.config -input=false
plan:
	terraform plan -var-file=cisadev.tfvars -var="runner_token=$(RUNNER_TOKEN)" -out plan
apply:
	terraform apply plan
format:
	terraform validate && terraform fmt -recursive
