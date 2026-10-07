"""Report-encryption helpers ported from atc-framework's pe_reports/helpers/.

Each module here is a standalone Lambda handler mirroring one of the
original EC2 CLI scripts. None of them are wired to a trigger, IAM role,
or Terraform resource yet — they exist so the ported logic can be
invoked and exercised in a Lambda runtime ahead of that integration work.
"""
