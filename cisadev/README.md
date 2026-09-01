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

## Notes

- The `infrastructure/` pipeline pins Terraform **1.0.7**. For provisioning the
  runner EC2 (a simple, standalone `main.tf`), the latest version is generally
  fine, but pin to 1.0.7 if you want to avoid any state/syntax drift.
- Using the APT repo means `apt upgrade` keeps Terraform patched automatically,
  which helps with CISADEV's weekly patching requirement.
