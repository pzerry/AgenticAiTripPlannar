# AWS deployment

The pipeline targets ECS/Fargate in AWS using ECR and GitHub OIDC. Infrastructure
is defined in `infra/aws`; deployment is in `.github/workflows/aws-deploy.yml`
and `scripts/deploy_ecs.py`. No resources have been provisioned yet.

## Required inputs

The default region is `us-east-1`, matching the local AWS profile. Set `region`
in Terraform if a different region is intended. Start with staging.

This stack creates ECR, an ECS cluster, API/worker/UI services, CloudWatch logs,
an HTTPS application load balancer, security groups, and IAM roles. It reuses:

- An existing VPC, two public subnets in different availability zones, and
  private task subnets with NAT egress for model/travel APIs and AWS services.
- A private PostgreSQL database reachable in that VPC, with backups enabled.
  The stack adds PostgreSQL ingress from its task security group only.
- An issued ACM certificate in the deployment region covering API and UI
  hostnames, and DNS control for those hostnames.
- An IAM OIDC provider for `https://token.actions.githubusercontent.com` with
  audience `sts.amazonaws.com` (create once per account).
- An application OIDC issuer, audience, and HTTPS JWKS endpoint issuing RS256
  tokens. This is separate from GitHub's deployment identity. The current UI
  accepts a bearer token; it does not implement a hosted login flow.
- A Secrets Manager JSON secret containing `DATABASE_URL` and required provider
  keys. Use the keys listed in `runtime_secret_keys`, adjusting that set to
  match the provider configuration. Every listed key must exist. DATABASE_URL
  must use the private database endpoint, URL-encoded credentials, and TLS
  (`sslmode=require`, or verified TLS with the appropriate CA). The database
  role needs schema permissions for memory and LangGraph checkpoint setup.

Supply secret values through Secrets Manager, never Terraform variables or
GitHub variables. Terraform stores only the secret ARN and key names. With a
customer-managed secret encryption key, set `secret_kms_key_arn` and ensure its
key policy allows the ECS execution roles to decrypt. The UI task has no
runtime secret access.

The current local AWS credentials return `InvalidClientTokenId`. Refresh the
appropriate AWS profile (for example, `aws sso login --profile YOUR_PROFILE`
for SSO), then verify `aws sts get-caller-identity`. Do not put access keys in
repository files or send them in chat.

## Bootstrap

1. Copy `infra/aws/terraform.tfvars.example` to `infra/aws/terraform.tfvars` and
   fill in the inputs above. The local input file is ignored by Git.
2. Choose durable encrypted Terraform state storage with locking before shared
   operations. This module does not force a backend; the default is local state.
   Retain the state securely and never commit state or plan files.
3. Run:

   ```sh
   terraform -chdir=infra/aws init
   terraform -chdir=infra/aws plan -out=staging.tfplan
   terraform -chdir=infra/aws apply staging.tfplan
   terraform -chdir=infra/aws output github_variables
   terraform -chdir=infra/aws output -raw load_balancer_dns_name
   ```

   Review the plan before applying. Applying creates billable ALB and associated
   resources; starting delivery creates three billable Fargate tasks. Existing
   NAT, database, logging, registry, and data-transfer costs also apply.
4. Point both hostnames at the load balancer DNS name. ECS services initially
   have zero tasks so no placeholder image starts before migration.
5. Create GitHub environment **aws-staging**, restrict its deployment branches
   to **main**, and copy each `github_variables` output as an environment
   variable. The IAM role trust is restricted to this repository/environment.
   If changing the environment name, update both Terraform and the reusable
   workflow. Production should have its own environment and infrastructure.
6. Set repository variable **AWS_DEPLOY_ENABLED=true** only after bootstrap,
   DNS, secrets, and environment configuration are complete. This variable must
   be repository-level because the caller evaluates it before entering the
   deployment environment. No long-lived AWS keys are needed in GitHub.
7. Commit the intended application changes, workflow, scripts, tests,
   infrastructure, and provider lock file; push `main` or run CI manually on
   `main`. Require the test, infrastructure-validation, and container-build
   checks for pull requests.

Infrastructure is applied separately from application delivery. After changing
Terraform-managed task settings, apply Terraform first; the next deployment
uses the latest family configuration while preserving the running revision for
rollback. Terraform ignores CI-managed service image revisions and counts.

## Delivery and failure behavior

1. CI runs tests with PostgreSQL, validates Terraform, builds a Linux x86-64
   image, smoke-checks it, and stores the image artifact.
2. The deployment job assumes its AWS role using GitHub OIDC. It loads that
   exact image, pushes an immutable `sha-<commit>` ECR tag, and resolves its digest.
   A rerun reuses an existing commit tag. GHCR is no longer needed.
3. It registers API, worker, and UI task revisions using that digest. A separate
   API task runs `python -m Backend.Memory.migrate`. Failure prevents rollout;
   a migration exceeding ten minutes is stopped.
4. It deploys API, worker, and UI sequentially, preserving existing replica
   counts (or starting one replica at bootstrap), waits for stability, and checks
   that ECS actually runs the requested revision. Circuit-breaker rollback must
   not be mistaken for success. HTTPS API/UI checks finish delivery.
5. On rollout or health-check failure, the script requests restoration of the
   previous revision/count for every changed service. Inspect ECS to confirm
   those restores finish. Database migrations are not reversed; use backward
   compatible migrations and maintain database backups. Initial deployment has
   no healthy prior revision, so failure restores the zero-task bootstrap state.

Main deployments are serialized and are not automatically cancelled by later
pushes. A manually cancelled job can interrupt cleanup: check ECS for a running
migration and partially updated services before restarting. Worker stability
confirms the process is running; it does not verify live model extraction.
Provider availability and extraction quality still need a separate live eval.

To recover an older release, inspect ECS task-definition history and explicitly
update each affected service to its previous revision, then wait for stability
and check HTTPS health. Do not rebuild an old image under an existing immutable
tag. Do not use an old application revision with incompatible database schema.

## Validation

Local Terraform validation, workflow YAML/shell parsing, and deployment unit
tests can run without valid AWS credentials. A real `terraform plan`, AWS
provisioning, GitHub OIDC exchange, and live rollout require a valid account and
the inputs listed above. These have not yet been verified against AWS.

On 2026-09-16, Terraform provider/schema validation and formatting passed, both
workflow files passed YAML/shell syntax checks, and all six deployment tests
passed. The earlier application/container verification passed 61 application
tests and the container smoke check.

## References

- [GitHub OIDC in AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)
- [ECS Secrets Manager injection](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data-tutorial.html)
- [ECS deployment failure detection](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-failure-detection.html)
