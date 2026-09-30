# Manual AWS setup for the existing delivery workflow

Create the infrastructure in the AWS Console once. GitHub Actions then publishes
the tested image and deploys subsequent application changes. No Terraform commands
are needed for this route. The existing delivery workflow does not run Terraform.

## 1. Create the image repository

Choose your deployment region (the existing example uses `us-east-1`). In Amazon
ECR, open **Private repositories → Create repository**:

- Name: `trip-planner-staging`
- Image tags: immutable
- Enable basic scan on push through the available repository/registry scanning settings.
- Keep encryption enabled.

Save the repository URI, without `https://` or an image tag. It becomes the GitHub
`ECR_REPOSITORY` variable. An empty repository is expected at this point.

## 2. Prepare the network, database, secrets, and hostnames

Use one VPC with two public subnets in different availability zones for the load
balancer, and private subnets with NAT egress for application tasks. External model
and travel APIs require outbound connectivity. Use private PostgreSQL in this VPC,
with backups enabled. These resources, especially NAT, RDS, ALB, and running tasks,
incur charges; choose sizing before creating them.

Create security groups:

- Load balancer: inbound TCP 443 from clients; outbound to application tasks.
- Tasks: inbound TCP 8000 and 8501 from the load balancer security group only;
  allow outbound access for database, provider APIs, and AWS services.
- Database: inbound TCP 5432 from the task security group only.

In Secrets Manager, store a JSON secret with `DATABASE_URL`, `GROQ_API_KEY`,
`OPENROUTERNIT_API_KEY`, `SERP_API_KEY`, `WEATHER_API_KEY`, and
`EXCHANGE_RATE_API_KEY`. Adjust provider keys to match the configured application.
Use the private database endpoint and URL-encoded credentials in `DATABASE_URL`,
with TLS enabled. Enter secret values only in AWS, not GitHub variables or Git.

Choose API and UI hostnames under a domain you control. Request and DNS-validate
an ACM certificate covering both names in the same region. Configure an application
OIDC issuer, audience, and HTTPS JWKS URL for RS256 tokens. This application identity
provider is separate from GitHub's AWS deployment identity. The UI currently asks
for a bearer token rather than implementing a hosted login flow.

## 3. Create ECS roles and logs

Create a CloudWatch log group `/ecs/trip-planner-staging`, with 30-day retention.
Create three ECS task execution roles, one for each API/worker/UI task, trusting
`ecs-tasks.amazonaws.com`. Attach `AmazonECSTaskExecutionRolePolicy` to each.
Give API and worker execution roles `secretsmanager:GetSecretValue` on the runtime
secret ARN; add `kms:Decrypt` on its key if using a customer-managed KMS key.
The UI execution role does not need application secret access.

Create an application task role trusting `ecs-tasks.amazonaws.com`; no additional
AWS permissions are required by the baseline configuration.

## 4. Create the cluster and task definitions

In ECS create a Fargate cluster named `trip-planner-staging`. Create three task
definition families: `trip-planner-staging-api`, `trip-planner-staging-worker`,
and `trip-planner-staging-ui`.

Each uses Linux/X86_64, Fargate, `awsvpc`, 0.5 vCPU, 1 GB memory, the appropriate
execution role, the application task role, and one essential container named
**app**. Set the image to `<ECR_REPOSITORY>:bootstrap`; this is a placeholder and
must not be started. The pipeline replaces it with the actual tested image.
Configure awslogs using the log group above and a stream prefix per service.

| Task | Container command (individual arguments) | Port |
| --- | --- | --- |
| API | `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` | 8000 |
| Worker | `python -m Backend.Memory.worker` | None |
| UI | `python -m streamlit run FrontEnd/app.py --server.address=0.0.0.0 --server.port=8501` | 8501 |

For API and worker set `APP_ENV=production`, `TRAVEL_AUTH_MODE=oidc`,
`TRAVEL_OIDC_ISSUER`, `TRAVEL_OIDC_AUDIENCE`, and `TRAVEL_OIDC_JWKS_URL`.
Map each runtime secret key to its environment variable using ECS secret references
of the form `<secret-arn>:<JSON-key>::`. For UI set only
`TRAVEL_API_URL=https://<api-hostname>`; do not inject database/provider secrets.

## 5. Create HTTPS routing and services

Create two HTTP target groups with **IP** targets: API on 8000 with health path
`/`, and UI on 8501 with health path `/_stcore/health`; expect status 200.
Enable load-balancer cookie stickiness for UI.

Create an internet-facing Application Load Balancer in the two public subnets,
using its security group. Set idle timeout to 600 seconds. Add an HTTPS 443
listener with the issued certificate. Route the API hostname to the API target
group and the UI hostname to the UI target group, with a default 404 response.
Point both DNS names to the load balancer.

Create three services in the cluster, named after their respective task families.
Use Fargate platform 1.4.0 or a compatible later version, private task subnets,
the task security group, and no public IP. Choose rolling ECS deployment and
enable circuit-breaker rollback. Set **desired tasks to 0** for bootstrap.
Attach API/UI to their respective target groups, container `app`, correct port,
and a 180-second health grace period. Worker has no load balancer.

## 6. Connect GitHub Actions to AWS

In IAM, add an OpenID Connect identity provider if it does not already exist:
provider URL `https://token.actions.githubusercontent.com`, audience
`sts.amazonaws.com`. Create `trip-planner-staging-github` trusting that provider
for `sts:AssumeRoleWithWebIdentity`. Require audience `sts.amazonaws.com` and
the repository/environment subject
`repo:pzerry/AgenticAiTripPlannar:environment:aws-staging` (verify against your
repository's actual OIDC subject configuration if customized).

Grant the deployment role these permissions with the indicated scope:

- `ecr:GetAuthorizationToken`, `ecs:RegisterTaskDefinition`, and
  `ecs:DescribeTaskDefinition` on `*`.
- `ecr:BatchCheckLayerAvailability`, `ecr:InitiateLayerUpload`,
  `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`, `ecr:PutImage`, and
  `ecr:DescribeImages` on this ECR repository ARN.
- `ecs:DescribeServices` and `ecs:UpdateService` on the three service ARNs.
- `ecs:RunTask` on `trip-planner-staging-api:*` task-definition revisions,
  constrained by `ecs:cluster` to this cluster ARN.
- `ecs:DescribeTasks` and `ecs:StopTask` on tasks in this cluster.
- `iam:PassRole` on the task and three execution roles, constrained by
  `iam:PassedToService=ecs-tasks.amazonaws.com`.

In GitHub repository Settings → Environments, create `aws-staging`, restrict
deployment branches to `main`, and add these **environment variables**:

| Variable | Value |
| --- | --- |
| AWS_REGION | Your selected region |
| AWS_DEPLOY_ROLE_ARN | ARN of `trip-planner-staging-github` |
| ECR_REPOSITORY | Full ECR repository URI, no tag or scheme |
| ECS_CLUSTER | `trip-planner-staging` |
| ECS_API_SERVICE | `trip-planner-staging-api` |
| ECS_WORKER_SERVICE | `trip-planner-staging-worker` |
| ECS_UI_SERVICE | `trip-planner-staging-ui` |
| API_HEALTH_URL | `https://<api-hostname>/` |
| UI_HEALTH_URL | `https://<ui-hostname>/_stcore/health` |

After every prerequisite is ready, add **repository-level** Actions variable
`AWS_DEPLOY_ENABLED=true`. GitHub does not need long-lived AWS access keys.

## 7. Run delivery

Merge the reviewed PR into `main`, or manually run **CI and container build** on
`main` if the changes are already merged. A PR run will continue to skip deployment.
The main run tests, builds, saves the image, publishes it to ECR, runs migrations,
starts API/worker/UI, and checks HTTPS health. Inspect Actions and ECS events;
confirm the API/UI target groups are healthy and worker logs show normal startup.

## References

- [ECS Fargate setup](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/getting-started-fargate.html)
- [GitHub OIDC with AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)
- [ECS secret injection](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/secrets-envvar-secrets-manager.html)
