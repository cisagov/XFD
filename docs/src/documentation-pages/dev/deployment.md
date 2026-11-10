---
title: Deployment
sidenav: dev
---

### Automatic deployment of CISA Crossfeed

Deployment of CISA Crossfeed is done automatically through GitHub Actions from the [cisagov/crossfeed](https://github.com/cisagov/crossfeed) GitHub repository.

Any code pushed to the `master` branch is automatically deployed to the [staging site](https://staging.crossfeed.cyber.dhs.gov/), and any code pushed to the `production` branch is automatically deployed to the [production site](https://crossfeed.cyber.dhs.gov/).

[Environments](https://docs.github.com/en/actions/reference/environments) are configured to ensure that only specific users with the appropriate permissions can trigger workflows on GitHub Actions or access secrets that perform deployments. At the moment, GitHub Actions jobs that deploy to staging and prod or access credentials for those AWS environments must be [manually approved](https://docs.github.com/en/actions/managing-workflow-runs/reviewing-deployments).

#### Setting up automatic deployment

To set up automatic deployment to your own AWS environment, you must first create an IAM user with enough permissions to the right resources on AWS. Then, set the GitHub repository's secrets `AWS_ACCESS_KEY` and `AWS_SECRET_KEY` to the access credentials of this user.

### Manual deployment steps

Here are instructions on how to deploy the different components of Crossfeed manually.

#### Infrastructure

Infrastructure is managed by Terraform. To deploy to staging, run:

```bash
cd infrastructure
make init
make plan
make apply
```

##### CyHy report sharing

Report-sharing resources are in `infrastructure/s3.tf`, with inputs in
`vars.tf`, environment settings in `stage-cd.tfvars`, and IAM/key-policy
outputs in `output.tf`. They use the existing provider, backend, and deployment
process. The existing `cisa-was-reports` bucket and manually created customer
managed KMS key are referenced; they are not created or replaced.

`stage-cd.tfvars` enables ME uploads and 14-day retention in the same change and
contains the supplied CMK, two ME producer roles, and confirmed existing
HTTPS-only bucket policy. The existing lifecycle configuration was confirmed
empty for this change. Bucket ownership is unchanged and no ownership
confirmation flag is required. ME uploads use
`reader_role_arns = []`; analyst roles do not block producer access. The grouped
input permits dependent settings to be validated with the Terraform 1.0.7
version used by the existing pipeline. Other environments default to disabled.

Before enabling it, preserve the complete current bucket policy in
`existing_bucket_policy_json`. This is the **S3 bucket policy**, not the KMS key
policy. Use an empty
Statement array only after confirming there is no current policy, and retain
the original policy as the input for later changes. This change does not modify
ownership, ACLs, public-access settings, or the bucket's default encryption.
Confirm that
no other Terraform state owns its bucket policy or lifecycle configuration;
adopt existing controls into the current environment's state where necessary.

The new grants and CMK upload requirements cover only `cybex_scorecard/`,
`cyhy_ad-hoc_notifications/`, `cyhy_vs_reports/`, `https_reports/`, and
`trustymail_reports/`. They exclude existing `was_reports/` and `capacity/`
objects, including customer CSV exports. All configured readers can access all
five prefixes, so every reader must be approved for that scope. Existing grants
are preserved rather than revoked. The new TLS object denial covers only ME
objects; secure transport is required on the new bucket-level grants without
adding a bucket-wide denial affecting WAS operations. Confirm the bucket
account/region, ATO approval, audit coverage, and organizational restrictions
before deployment.

Producers must request `aws:kms` and the exact CMK ARN on uploads. The external
role owners must attach the generated producer IAM policy. When analyst access
is ready, add approved roles to `reader_role_arns`. Only then are analyst
download/list grants and reader IAM/key-policy outputs generated. Analyst role
owners and the CMK owner must review those policies. Append the reader
key-policy statement to the existing key policy, preserving its administrator
and producer statements. This configuration does not change the shared bucket's
default encryption or re-encrypt existing objects.
Ownership of newly uploaded ME objects follows the bucket's existing ownership
mode. Upload access does not require changing that mode. Any later analyst
download setup must account for the actual object ownership and permissions.

`manage_retention` is enabled in `stage-cd.tfvars`, and
`existing_lifecycle_configuration_reviewed_empty` records confirmation that no
existing lifecycle rules are configured. Confirm no other Terraform state owns
the configuration. If rules are subsequently added, preserve them in the
complete lifecycle configuration before deployment.
The retention rules use a separate fixed list containing only the five ME
prefixes. No expiration, version cleanup, delete-marker cleanup, or incomplete
upload cleanup rule added by this change matches `was_reports/` or `capacity/`.
Changing access permissions does not expand the retention scope. Existing WAS
lifecycle rules must not be removed or replaced; if any exist, the current
ME-only lifecycle resource remains blocked until preservation is addressed.
The optional rules expire reports after 14 days, noncurrent versions one day
after becoming noncurrent, and incomplete uploads after one day, with separate
delete-marker cleanup. Versioning, Object Lock, replication, backups, and
asynchronous S3 processing mean this is not a strict 14-day permanent-deletion
guarantee. Review old matching objects before activation.

Terraform tests and validation tooling stay local, outside the repository.
Do not access AWS, run a live plan, import resources, or deploy from the
development environment. The existing workflow can apply this infrastructure
after a merge; enablement requires deployment review. COOL organization access
and possible long-term copying require separate source/destination details and
are not configured by these report-sharing resources.

#### Backend

The backend API is managed by the Serverless Framework. To deploy, run:

```bash
cd backend
npx sls create_domain --stage=staging
npx sls deploy --stage=staging
```

To change the environment variables used to build the backend, edit `env.yaml`. Most of these
variables are set through SSM variables (which should be set manually / through Terraform -- see below),
but some of these variables are hard-coded and configurable by just editing `env.yaml`.

#### Worker

Deploying the worker involves building the Docker image and pushing it to ECR:

```bash
cd backend
npm run deploy-worker
```

If the `worker_ecs_repository_url` output from Terraform changes, you will need to modify `./src/tools/deploy-worker.sh`.

#### Frontend

Deploying the frontend involves building the React code, uploading it to an S3 bucket, then invalidating the Cloudfront cache:

```bash
cd frontend
cp stage.env .env
npm run build
aws s3 sync build/ s3://staging.crossfeed.cyber.dhs.gov --delete
```
