.PHONY: init plan apply format

# Password is passed at plan/apply time, not stored in a file:
# make plan DEVHOST_PASSWORD=xxxxxxxx
# make apply

init:
	terraform init -backend-config=devhost.config -input=false
plan:
	terraform plan -var-file=devhost.tfvars -var="devhost_password=$(DEVHOST_PASSWORD)" -out plan
apply:
	terraform apply plan
format:
	terraform validate && terraform fmt -recursive
