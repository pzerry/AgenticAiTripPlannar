# CI and container delivery

The pipeline tests the application and builds a container. Once configured,
successful main builds deliver that exact image to AWS ECR and ECS/Fargate.
See [AWS deployment setup](aws-deployment.md) for infrastructure and activation.

## What happens on GitHub

1. Pull requests, pushes to `main`, and manual runs trigger
   `.github/workflows/ci.yml`.
2. The repository check rejects tracked `.env`, private-key files, and runtime
   logs. It examines filenames only and never prints their contents.
3. The test job starts a disposable PostgreSQL 18 service, installs Python 3.14
   and uv 0.11.26, and installs dependencies from `uv.lock` with `--locked`.
4. Python syntax and all tests run. Missing PostgreSQL configuration or skipped
   tests fail CI. Model and travel-provider calls are mocked; CI needs no real
   provider API keys.
5. Only after tests pass, the container job builds the application and checks
   imports, its non-root runtime user, and absence of `/app/.env`.
6. Main/manual runs upload `trip-planner-image-<commit SHA>` as a workflow
   artifact retained for three days. PR builds validate the image but do not
   upload it.
7. When repository variable `AWS_DEPLOY_ENABLED=true`, successful main runs
   deploy through the `aws-staging` GitHub environment: publish to ECR, run
   migrations, update API/worker/UI services, and check HTTPS health.

CI also validates Terraform. Pull requests cancel superseded runs; main and AWS
deployments are serialized to avoid interrupting migrations. Repository access
is read-only; only the AWS delivery job has permission to request an OIDC token.

## Required before the first push

The repository previously tracked `.env`, `logs/travel.log`, and `logs/error.log`.
This change removed those three paths from the Git index while preserving the
local files. Their staged deletions must be included in your next commit.
Adding `.gitignore` alone would not have untracked them. The command used was:

```sh
git rm --cached -- .env logs/travel.log logs/error.log
```

Review and commit those removals along with the pipeline and intended source,
test, and migration changes. No other existing changes were staged, and nothing
was committed or pushed. If real credentials were previously pushed, rotate them;
removing a tracked file now does not remove it from Git history.

In GitHub:

1. Enable Actions for `pzerry/AgenticAiTripPlannar` and allow the official
   `actions/*` and `astral-sh/setup-uv` actions if organization policy restricts
   actions.
2. Push the reviewed changes and open the **Actions** tab. Select
   **CI and container build** to see the test, infrastructure, build, and deployment jobs.
3. After its first run, protect `main` and require these checks before merging:
   **Tests (Python 3.14 + PostgreSQL 18)** and **Build application container**.

No GitHub secrets, AWS account, paid model calls, or live application database
are required for this CI/build stage.

## Local verification

```sh
# This fails if runtime files become tracked again.
.venv/bin/python scripts/check_repository_files.py

# Use an isolated database, never your application database.
MEMORY_TEST_DATABASE_URL='<test PostgreSQL URL>' PYTHON_DOTENV_DISABLED=1 \
  .venv/bin/python scripts/ci_tests.py

docker build --tag trip-planner:local .
```

The CI job supplies dummy provider keys. If a locally imported provider client
requires credentials, use the same dummy environment values from the workflow
when running tests; do not supply production secrets.

## AWS delivery

Follow [AWS deployment setup](aws-deployment.md) to configure infrastructure,
OIDC, secrets, and GitHub environment variables. The deployment job summary
records the ECR digest. GHCR publishing has been replaced with AWS delivery.

## Running the image

The image contains the API, worker, and UI. Run them as separate processes or
containers with different commands. It excludes `.env`, logs, tests, Git
history, and evaluation artifacts. Supply configuration at runtime through a
private environment file or a secret manager.

Download the image artifact from a successful GitHub run, extract its archive,
then load the image (replace `COMMIT_SHA` below with that run's revision):

```sh
docker load --input trip-planner-image.tar.gz
docker image inspect trip-planner:COMMIT_SHA
```

Before API/worker startup, run migrations as a separate controlled command
against your intended development database:

```sh
docker run --rm --env-file .env trip-planner:COMMIT_SHA \
  python -m Backend.Memory.migrate
```

The existing `.env` must contain a `DATABASE_URL` reachable from the container.
`localhost` inside a container refers to that container, not your Mac. Use a
database service hostname on a shared Docker network, or `host.docker.internal`
for a database on Docker Desktop's host with TCP access enabled. Do not expose
PostgreSQL publicly just to make this connection work.

Example commands for a shared Docker network and an already reachable database:

```sh
docker network create trip-planner

# API (uses the image's default command)
docker run --rm --name trip-api --network trip-planner \
  --env-file .env -p 127.0.0.1:8000:8000 trip-planner:COMMIT_SHA

# Run in another terminal: independent memory worker
docker run --rm --name trip-worker --network trip-planner \
  --env-file .env trip-planner:COMMIT_SHA \
  python -m Backend.Memory.worker --provider groq

# Run in another terminal: UI; it does not need database or provider secrets
docker run --rm --name trip-ui --network trip-planner \
  -e TRAVEL_API_URL=http://trip-api:8000 -p 127.0.0.1:8501:8501 \
  trip-planner:COMMIT_SHA python -m streamlit run FrontEnd/app.py \
  --server.address=0.0.0.0 --server.port=8501
```

API and worker need the configured model/provider credentials and database
connection. The API also needs development JWT or production OIDC settings.
Pass environment variables into containers; automatic `.env` loading inside
the image is disabled. The existing token UI remains a development interface.

## Verification recorded 2026-09-16

- The CI test entry point passed all 61 tests with PostgreSQL 18 and no skips,
  with `.env` loading disabled and dummy provider credentials.
- A Linux/amd64 image built successfully from the committed dependency lock.
- The container import check passed for API, memory worker, Streamlit, and
  psycopg, using a non-root user and with no `/app/.env` file.
- Workflow YAML parsing and Python syntax checks passed. The workflow has not
  yet run on GitHub because these changes have not been pushed.

## References

- [uv in GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)
- [GitHub PostgreSQL service containers](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers)
- [Workflow artifacts](https://docs.github.com/en/actions/tutorials/store-and-share-data)
