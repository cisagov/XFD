# WAS AWS Access Scripts

These Python scripts provide the WAS EC2 access workflow on Windows, macOS,
and Linux without Bash, GNU Screen, `lsof`, or `nc`.

## Prerequisites

- Python 3.10 or newer.
- AWS CLI v2.
- AWS Session Manager plugin.
- OpenSSH client.
- An AWS CLI profile authorized for EC2, EC2 Instance Connect, and SSM access.
- The private key at `~/.ssh/accessor_rsa` and public key at
  `~/.ssh/accessor_rsa.pub`.

Configuration can be overridden with `WAS_AWS_PROFILE`, `WAS_AWS_REGION`,
`WAS_LOCAL_SSH_PORT`, `WAS_EC2_USER`, `WAS_SSH_PRIVATE_KEY`, and
`WAS_SSH_PUBLIC_KEY`.

## Windows PowerShell

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

```bash
export INSTANCE_ID_WAS="i-replace-with-approved-instance-id"
python3 checkAccessorWAS.py
python3 sshConnectWAS.py
```

Tunnel diagnostics are written to `~/.was-access/tunnel.log`.
