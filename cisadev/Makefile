.PHONY: init plan apply format

# The runner registration token is NOT stored in a file. Pass it at plan/apply time 😭
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
