# WAS AWS Access Scripts

These Python scripts provide the WAS EC2 access workflow on Windows, macOS,
and Linux without Bash, GNU Screen, `lsof`, or `nc`.

## Prerequisites

- Python 3.10 or newer.
- AWS CLI v2.
- AWS Session Manager plugin.
- OpenSSH client.
- An organization-approved AWS CLI profile that is already authenticated.
- The private key at `~/.ssh/accessor_rsa` and public key at
  `~/.ssh/accessor_rsa.pub`.

The operator profile needs resource-scoped permission for
`ec2:DescribeInstances`, `ec2:StartInstances` when the instance can be stopped,
`ec2-instance-connect:SendSSHPublicKey`, and `ssm:StartSession` with the
`AWS-StartPortForwardingSession` document. Scope these permissions to the
approved WAS instance, document, Region, OS user, and organizational conditions
where the AWS action supports that scope. Do not use a wildcard administrator
policy as an access prerequisite.

The instance must be registered and online in Systems Manager, have an instance
role that supports Session Manager, support EC2 Instance Connect for the chosen
OS user, and have OpenSSH listening on remote port 22. These scripts do not
provision the instance, its role, SSM agent, SSH service, network path, or
operator permissions.

Keep the private key outside the repository with owner-only permissions. The
script reads the public key and submits it through EC2 Instance Connect; it
never uploads the private key. Do not put AWS credentials, private keys, or the
instance ID in `dev.env` or any tracked file. AWS CLI credential and SSO setup is
owned by the organization's approved workstation-access process.

Configuration can be overridden with `WAS_AWS_PROFILE`, `WAS_AWS_REGION`,
`WAS_LOCAL_SSH_PORT`, `WAS_EC2_USER`, `WAS_SSH_PRIVATE_KEY`, and
`WAS_SSH_PUBLIC_KEY`.

Defaults are AWS profile `default`, Region `us-east-1`, local port `7777`, EC2
user `ubuntu`, and the key paths listed above. `INSTANCE_ID_WAS` is required for
each shell and has no default. Confirm that the profile, Region, instance ID,
and OS user all refer to the approved WAS host before starting a session.

## Windows PowerShell

Start PowerShell in the `backend/was/scripts/awsAccessScripts` directory.

Set the instance ID for the current PowerShell window:

```powershell
$env:INSTANCE_ID_WAS = "i-replace-with-approved-instance-id"
```

Prepare the instance and tunnel:

```powershell
py .\checkAccessorWAS.py
```

Connect after the tunnel reports that port 7777 is ready:

```powershell
py .\sshConnectWAS.py
```

Tunnel diagnostics are written to `%USERPROFILE%\.was-access\tunnel.log`.

## macOS Or Linux

Start a shell in the `backend/was/scripts/awsAccessScripts` directory.

```bash
export INSTANCE_ID_WAS="i-replace-with-approved-instance-id"
python3 checkAccessorWAS.py
python3 sshConnectWAS.py
```

Tunnel diagnostics are written to `~/.was-access/tunnel.log`.

## Tunnel lifecycle and safety

`checkAccessorWAS.py` inspects the instance, starts it only when it is stopped,
uploads the configured public key, and launches a detached Session Manager port
forward. It records the managed PID and random launch token in
`~/.was-access/tunnel.pid`. If the
command is run again, it validates the recorded PID against both the expected
starter script and a random launch token before stopping that exact process
group. The state file is JSON containing the PID and token, not a bare PID. A
stale or reused PID is reported and never terminated. The script also refuses
to terminate an unknown process when the configured local port remains occupied.

`sshConnectWAS.py` opens the interactive SSH client through the existing local
tunnel. Ending the SSH session does not end the detached tunnel. The repository
does not currently provide a supported stop-only command. When access is no
longer needed, inspect `tunnel.pid` and `tunnel.log`, verify that the recorded
identity belongs to the tunnel started by these scripts, and terminate that
exact process through the organization-approved OS process controls. Do not kill
an arbitrary process merely because it is listening on port 7777. A future
repository change should add an explicit cross-platform stop command.

The state directory is created with owner-only permissions. Treat the PID/token
state and log as operationally sensitive because they can contain AWS account,
instance, Region, user, and connection metadata. Do not attach either file to a
ticket until it has been reviewed and sanitized. The scripts do not disable SSH
host-key checking; resolve any host-key warning through the approved host
identity process rather than bypassing it.

The script reporting that port 7777 is ready proves only that the local tunnel
accepts connections. Confirm the SSH login reaches the expected WAS host before
performing operational work. A failed run should be investigated from the
terminal message and the sanitized tail of `tunnel.log`; do not expose AWS
credentials or key material while troubleshooting.
