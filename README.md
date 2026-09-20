# Agentic AI Trip Planner

Python travel planner with a FastAPI API, Streamlit UI, and PostgreSQL-backed
conversation and preference memory.

## CI and AWS delivery

Pull requests run tests against PostgreSQL, validate Terraform, and build the
application container. When AWS delivery is enabled, successful `main` builds
publish the tested image to ECR, run migrations, and deploy separate API,
memory-worker, and UI services to ECS/Fargate.

- [CI setup and local verification](docs/ci-cd.md)
- [AWS infrastructure, configuration, and deployment](docs/aws-deployment.md)
