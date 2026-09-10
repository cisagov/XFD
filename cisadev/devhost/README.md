# CISADEV Developer Dev Host

Terraform configuration for provisioning the XFD developer dev host in CISADEV —
an Ubuntu workstation with a desktop environment, RDP access, and developer
tooling. Based on the bootstrap script provided by CISADEV.

This is separate from the GitHub Actions runner (see `../runner/`): the runner
is a headless CI worker, the dev host is a GUI workstation developers RDP into.

## What it provisions

- Desktop environment (Cinnamon by default; `ubuntu` or `xfce` selectable)
- xrdp on port 3389, smart card support (pcscd/opensc)
- AWS CLI v2 (GPG-verified install)
- Flatpak apps: VS Code, GitHub Desktop, Figma, draw.io, LibreOffice, KeePassXC
- UFW allowing SSH (22) and RDP (3389)
- A login user (default `cisadev`) added to sudo

## Prerequisites

- Terraform state S3 bucket exists and is set in `devhost.config` (separate ticket).
- SSM parameters exist for the AMI, subnet, and security group at the paths in
  `devhost.tfvars` (separate ticket).
- Placeholder values in `devhost.tfvars` (`<...>`) are filled in.

## Provision

From the `devhost/` directory:

```bash
./bootstrap.sh <DEVHOST_PASSWORD>
```

Or manually:

```bash
make init
make plan DEVHOST_PASSWORD=<password>
make apply
```

The password is passed via `-var` and never written to a file. **Change it on
first login.**

After boot, RDP to the instance IP on port 3389 with the configured username.
