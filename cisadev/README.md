# CISADEV GitHub Actions Runner

Terraform configuration for provisioning the self-hosted GitHub Actions runner
EC2 instance in the CISADEV environment.

## Installing Terraform on the Worker EC2

The runner EC2 is provisioned by running Terraform from a worker EC2 inside
CISADEV. Install Terraform on that worker (Ubuntu) using the official HashiCorp
APT repository.

From an SSH session on the worker EC2:

### 1. Install prerequisites

```bash
sudo apt-get update
sudo apt-get install -y gnupg software-properties-common curl
```

### 2. Add the HashiCorp GPG key

```bash
wget -O- https://apt.releases.hashicorp.com/gpg | \
  gpg --dearmor | \
  sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null
```

### 3. Add the HashiCorp repository

```bash
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list
```

### 4. Install Terraform

```bash
sudo apt-get update
sudo apt-get install -y terraform
```

To pin a specific version (e.g., to match the `infrastructure/` pipeline which
uses Terraform 1.0.7):

```bash
sudo apt-get install -y terraform=1.0.7-*
```

### 5. Verify

```bash
terraform -version
```

## Provisioning the Runner EC2

The config follows the `infrastructure/` pattern: variables in `vars.tf`,
values in `cisadev.tfvars`, S3 backend in `cisadev.config`, and the bootstrap
script templated from `user_data.sh.tpl`. Sensitive infrastructure IDs (AMI,
subnet, security group) are read from SSM Parameter Store, not committed.

### Prerequisites

- **Terraform state S3 bucket** exists and its name is set in `cisadev.config`
  (tracked in a separate ticket).
- **SSM parameters** exist for the AMI, subnet, and security group at the paths
  referenced in `cisadev.tfvars` (tracked in a separate ticket).
- Placeholder values in `cisadev.tfvars` (`<...>`) are filled in.
- A fresh **runner registration token** from the GitHub Enterprise team
  (ephemeral, expires ~1 hour) and the **CrowdStrike CID**.

### One-command provision

From the `cisadev/` directory:

```bash
./bootstrap.sh <RUNNER_TOKEN> <CROWDSTRIKE_CID>
```

This runs `terraform init` with the S3 backend, then `terraform apply` with the
tfvars plus the token and CID passed via `-var` (never written to a file).

### Or run the steps manually

```bash
make init
make plan RUNNER_TOKEN=<token>   # add -var crowdstrike_cid=<cid> if planning apply
make apply
```

The runner EC2 boots, installs dependencies via `user_data` (CrowdStrike + the
GitHub Actions runner), registers with the enterprise runner group, and comes
online in a few minutes.

## Verifying CrowdStrike Installation

After the runner EC2 boots, SSH into it (the newly created runner instance, not
the worker) and run these checks to confirm the CrowdStrike Falcon sensor
installed correctly via `user_data`.

### 1. Check the service is running

```bash
sudo systemctl status falcon-sensor
```

Look for `active (running)`.

### 2. Confirm the process is alive

```bash
ps -e | grep falcon-sensor
```

### 3. Verify the kernel module is loaded

```bash
lsmod | grep falcon
```

### 4. Confirm the CID is set

```bash
sudo /opt/CrowdStrike/falconctl -g --cid
```

Should return the configured CID.

### 5. Confirm the grouping tag

```bash
sudo /opt/CrowdStrike/falconctl -g --tags
```

Should return `CISADEV-Projects`.

### 6. Review the bootstrap log (for debugging)

```bash
sudo cat /var/log/bootstrap-runner.log
```

Shows the full `user_data` run — CrowdStrike download, install, config, and
verification output. Start here if the sensor did not install.

**Common failure causes:**

- `aws s3 cp` failed → the instance profile lacks S3 read access on the software
  bucket, or the S3 path is wrong.
- `dpkg` dependency error → confirm `apt-get -f install` ran.

## Notes

- The `infrastructure/` pipeline pins Terraform **1.0.7**. For provisioning the
  runner EC2 (a simple, standalone `main.tf`), the latest version is generally
  fine, but pin to 1.0.7 if you want to avoid any state/syntax drift.
- Using the APT repo means `apt upgrade` keeps Terraform patched automatically,
  which helps with CISADEV's weekly patching requirement.
