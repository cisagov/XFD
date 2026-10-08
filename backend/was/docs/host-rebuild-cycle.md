# WAS biweekly host rebuild cycle

## Purpose and boundaries

Use this procedure to replace the WAS reporting EC2 on its approved two-week
cycle while keeping Ubuntu 24.04 and the required host software reproducible.
Run host commands as the normal EC2 operator from `backend/was`; do not run the
capture or rebuild scripts as root.

The committed `host-software-manifest.json` is the reviewed source of truth for
host APT packages, Docker packages, required command-line tools, the pinned
`uv` binary, and the `uv`-managed Python version. Captured state is evidence for
review; it must never update the manifest automatically. This prevents
unreviewed host drift or a compromised executable from being copied into every
future replacement.

The host manifest does not replace application dependency controls. Python
runtime dependencies remain pinned in `requirements.txt`, container operating
system packages remain declared in `Dockerfile`, and the application image must
be rebuilt from the approved repository commit.

Terraform first boot is intentionally the first of two stages. The dedicated
`infrastructure/was-reporting-bootstrap.sh` installs only `git`, `make`,
`openssh-client`, `python3`, `sudo`, and the certificate bundle required to
retrieve and run the approved repository. It does not install Docker, AWS CLI,
`uv`, managed Python, or application dependencies. The manifest-driven Make
workflow below is the second stage and remains the reviewed source of truth for
that software.

This workflow does not copy secrets, application data, custom script contents,
cron jobs, systemd units, certificates, mounts, shell profiles, logs, or Docker
images. Back up and restore each approved item separately. Never source `.env`
as shell code or place its contents in inventory output, Git, logs, or command
arguments.

## 1. Capture the operational host

Before every replacement, confirm the current checkout is the approved commit
and run:

```bash
cd "$HOME/code/cd_WAS_update/backend/was"
make host-software-capture HOST_SOFTWARE_SINCE="YYYY-MM-DD"
```

The command creates a private mode-`0700` directory beneath `local-output` by
default and prints its absolute path. Supply an explicit unused destination
when required:

```bash
make host-software-capture \
  HOST_SOFTWARE_INVENTORY_DIR="$HOME/was-host-inventory-YYYYMMDDTHHMMSSZ" \
  HOST_SOFTWARE_SINCE="YYYY-MM-DD"
```

The inventory includes:

- installed, manually selected, and held APT packages;
- package-manager history still retained on the host;
- required and inventory-only tool paths, versions, executable SHA-256 values,
  symlink targets, and APT ownership evidence;
- offline `uv` managed-tool and Python inventories;
- offline global npm package evidence when npm exists;
- Snap package evidence when Snap exists;
- metadata for relevant user scripts, profiles, cron files, and systemd units;
- the exact committed manifest checksum; and
- `software-manifest-comparison.json`.

Review every warning. `missing_required_packages` and
`missing_required_tools` identify declared software absent from the host.
`manual_packages_not_in_manifest` is a review queue, not an automatic install
list. Classify each entry as required, an Ubuntu base-image package, obsolete,
or intentionally unmanaged. Change the committed manifest only through review.

Copy the complete inventory directory to approved off-host storage and verify
the copy before touching the operational instance. The inventory contains
paths, usernames, versions, and host metadata and must not be published.

## 2. Prepare and approve the replacement

Before applying Terraform:

1. Verify the proposed AMI is an available Canonical-owned Ubuntu 24.04 x86-64
   image in `us-east-1`.
2. Capture and retain an EBS snapshot or other approved rollback backup of the
   operational root volume.
3. Back up `.env`, approved custom scripts, required logs and batch evidence,
   cron and systemd definitions, certificates, and other manual items through
   their approved mechanisms.
4. Review the exact Terraform plan and confirm the replacement scope, expected
   instance-ID and private-IP changes, root-volume disposition, and maintenance
   window.
5. Prove the process first on a disposable instance built from the exact AMI
   and Terraform user data.

Do not terminate the operational host merely because inventory capture or a
Terraform plan completed successfully.

## 3. Install the declared software

After the replacement is reachable, clone the approved `develop` commit and
preview the host changes:

```bash
cd "$HOME/code/cd_WAS_update/backend/was"
make host-software-preview
```

Review the APT and Docker package lists, pinned `uv` checksum, Python version,
pinned AWS CLI v2 checksum, root-equivalent Docker group access, and every
manual restore item. Apply only during the approved change window:

```bash
make host-software-apply APPLY=1
```

The helper:

- refuses non-Ubuntu 24.04 and non-x86-64 hosts;
- refuses root or `sudo` invocation;
- simulates APT installation with `--no-remove` before installing;
- rejects conflicting Docker packages and incompatible or unsigned Docker
  repository definitions;
- never performs a distribution upgrade or automatic package removal;
- installs only checksum-verified AWS CLI and `uv` archives;
- grants the invoking operator root-equivalent Docker group access when
  needed; and
- does not restore secrets, services, data, or application state.

If the apply step adds Docker group membership, end that login session and
reconnect before verification. Existing shells do not acquire new
supplementary groups.

## 4. Restore and validate

Restore the separately approved manual items, then run:

```bash
cd "$HOME/code/cd_WAS_update/backend/was"
make host-software-verify
cd ../..
"$HOME/.local/bin/uv" venv \
  --python 3.12.14 \
  --seed \
  cd_WAS_update
cd backend/was
../../cd_WAS_update/bin/python --version
../../cd_WAS_update/bin/python -m pip --version
make install
make host-shell-preview
make host-shell-install APPLY=1
make test
make lint
make build
```

`host-software-verify` fails unless the current operator session can query the
Docker daemon without `sudo`, Docker Compose works, and AWS CLI matches the
pinned manifest version. The rebuild helper installs checksum-verified `uv`
and its managed Python 3.12.14. The `uv venv` command creates the named
`cd_WAS_update` environment expected by the Makefile and seeds it with `pip`.
The guarded shell installer backs up `~/.bashrc`, appends exactly one loader for
the tracked non-secret `config/was-operator-shell.sh`, validates both files, and
requires a new login shell before the configuration takes effect.

Run another inventory on the replacement and require empty
`missing_required_packages` and `missing_required_tools` arrays. Review every
remaining manual package and warning rather than suppressing it.

Also verify:

- cloud-init completed without error;
- SSM and approved operator access work;
- Docker Engine and Compose work as the normal operator;
- the cleanup timer and required service definitions are installed and active;
- `.env` came from the approved secret source and has mode `0600`;
- database identity and connectivity are correct without printing credentials;
- S3 and SES permissions work through the instance role;
- a read-only WAS preflight completes; and
- an explicitly approved test-recipient workflow succeeds before customer use.

Do not treat successful package verification, image creation, or Terraform
application as proof that report generation or delivery works.

## 5. Cutover, rollback, and evidence

Cut over only after the new host passes every required check. Preserve the old
instance or root-volume snapshot for the approved rollback period. If a check
fails, stop the cutover, preserve logs and inventory evidence, and restore the
previous host according to the approved change plan.

Record the following for every cycle:

- old and new instance IDs and AMI IDs;
- approved commit and manifest SHA-256;
- inventory locations and review outcome;
- Terraform plan and apply evidence;
- package, service, access, build, and non-destructive application checks;
- cutover approval and time; and
- rollback disposition and eventual approved removal of old resources.
