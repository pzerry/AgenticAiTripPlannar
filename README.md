# Agentic AI Trip Planner

A travel planner you can talk to. Describe the trip you have in mind, answer any missing details, and get flight, hotel, activity, weather, and cost information in one conversation.

Planning usually means switching between search results, comparing prices, and entering the same preferences again. This project brings those steps into a chat interface and keeps a small set of travel preferences for future conversations.

Built with **FastAPI, Streamlit, LangGraph, and PostgreSQL**. The project includes a Docker image and GitHub Actions checks for tests and container builds. Cloud deployment is not complete yet.

## What you can do

- Ask for a full trip plan or help with a particular part of a trip.
- Answer follow-up questions when the destination, dates, or other details are missing.
- Get suggestions backed by external flight, hotel, activity, weather, and exchange-rate services.
- Continue a conversation using its saved state in PostgreSQL.
- Reuse saved flight, hotel, and travel-style preferences across conversations.
- View and delete saved preferences from the sidebar.
- See a budget estimate calculated from available quotes, with missing prices called out.

For example, you could start with:

> Help me plan a five-day trip from Delhi to Singapore next month. I prefer direct flights and four-star hotels. Ask me anything else you need.

The planner asks for clarification when it needs more information. Suggestions depend on the configured models and the data returned by the travel services. This is a planning tool; it does not book tickets or make reservations.

## How it works

The Streamlit interface sends authenticated messages to FastAPI. The API checks who owns the conversation, loads relevant preferences, and passes the message to a LangGraph workflow.

1. **Understand the request.** The analyzer updates the trip details and asks follow-up questions if needed.
2. **Choose the work.** The orchestrator selects the flight, hotel, activity, or weather steps required for the request.
3. **Gather information.** The selected steps call the relevant travel services and prepare recommendations.
4. **Prepare the answer.** Currency handling and response generation bring the results together. For a full plan, Python calculates the budget from quoted prices instead of asking the model to add them.
5. **Process preferences separately.** A background worker reads queued messages and checks whether they contain a lasting preference worth saving.

PostgreSQL stores conversation checkpoints, message receipts, preference events, and saved preferences. Keeping preference extraction separate means the chat does not have to wait for that extra model call.

### What the planner remembers

Saved preferences are deliberately limited to three fields:

| Preference | Supported values |
| --- | --- |
| Flight type | Non-stop or connections allowed |
| Hotel class | One to five stars |
| Trip style | Budget-friendly, balanced, or luxury |

A saved preference supplies a default, not a rule. “Use a five-star hotel for this trip” can override a saved four-star preference without changing the long-term profile. Extraction is model-dependent, so not every message produces a saved preference.

Retrieval uses these structured fields directly; it does not need embeddings or a vector database. Deleting a preference removes the active preference, not conversation history or database backups.

## Technology

| Part | Implementation |
| --- | --- |
| Chat interface | Streamlit |
| HTTP API and validation | FastAPI and Pydantic |
| Planning workflow | LangGraph and LangChain |
| Model access | Ollama, Groq, and OpenRouter |
| Conversation and preference storage | PostgreSQL |
| Travel data | SerpAPI, OpenWeatherMap, and ExchangeRate-API |
| Authentication | Development JWTs; OIDC verification support for deployment |
| Dependency management | uv and a committed lockfile |
| Packaging and CI | Docker and GitHub Actions |

## Run locally

### Prerequisites

- Python 3.14 and uv.
- PostgreSQL; CI uses PostgreSQL 18. Docker is an easy way to start a local database.
- The PostgreSQL client library, `libpq`, available to Python's database driver.
- Ollama with `qwen3:8b` for the current analyzer and activity-agent configuration. Allow enough local memory to run this model.
- Credentials for Groq, OpenRouter, SerpAPI, OpenWeatherMap, and ExchangeRate-API.

Local Ollama does not replace every hosted model call. The current code uses different providers for different steps.

### 1. Install dependencies

```sh
git clone https://github.com/pzerry/AgenticAiTripPlannar.git
cd AgenticAiTripPlannar
uv sync --locked
```

Run the remaining commands from this directory.

### 2. Start a development database

If you already have a development PostgreSQL database, use its connection details instead. Otherwise:

```sh
docker run --name trip-planner-db \
  -e POSTGRES_USER=trip \
  -e POSTGRES_PASSWORD=local-dev-only \
  -e POSTGRES_DB=trip_planner \
  -p 127.0.0.1:5432:5432 \
  -v trip-planner-pgdata:/var/lib/postgresql \
  -d postgres:18
```

The password above is only for this local example. The named volume keeps database files across container restarts. If port 5432 is already in use, choose another host port and update the connection URL below.

### 3. Configure your environment

Create a `.env` file in the project root and fill in your own values:

```dotenv
DATABASE_URL=postgresql://trip:local-dev-only@localhost:5432/trip_planner

APP_ENV=development
TRAVEL_AUTH_MODE=development
TRAVEL_DEV_JWT_SECRET=replace-with-a-random-secret-at-least-32-bytes-long

GROQ_API_KEY=your-groq-key
OPENROUTERNIT_API_KEY=your-openrouter-key
SERP_API_KEY=your-serpapi-key
OPENWEATHERMAP_API_KEY=your-openweathermap-key
EXCHANGE_RATE_API_KEY=your-exchange-rate-key
```

`OPENROUTERNIT_API_KEY` is the variable name currently read by the OpenRouter client. The weather client reads `OPENWEATHERMAP_API_KEY`. Keep those spellings when configuring the app.

Generate a development signing secret with:

```sh
uv run python -c 'import secrets; print(secrets.token_hex(32))'
```

Paste the result into `TRAVEL_DEV_JWT_SECRET`. Keep `.env` and bearer tokens out of version control. External API usage is subject to each provider's limits and pricing.

Model names and service settings live in [`Backend/Config/config.yaml`](Backend/Config/config.yaml). Check that the configured hosted models are available to your accounts. Several graph steps select providers explicitly, so changing `default_provider` alone does not switch the whole application.

### 4. Prepare Ollama and the database

With Ollama running locally:

```sh
ollama pull qwen3:8b
uv run python -m Backend.Memory.migrate
```

Run migrations before starting the API or worker. API startup also prepares the LangGraph checkpoint tables, so the development database user needs permission to create tables.

### 5. Start the application

Open three terminals in the project directory.

**Terminal 1 — API**

```sh
uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — preference worker**

```sh
uv run python -m Backend.Memory.worker --provider groq
```

**Terminal 3 — chat interface**

```sh
uv run python -m streamlit run FrontEnd/app.py
```

Open the interface at **http://localhost:8501**. API documentation is available at **http://localhost:8000/docs** once the API starts.

### 6. Connect a development account

In another terminal, generate a one-hour token:

```sh
uv run python -m app.dev_token \
  --user-id 00000000-0000-0000-0000-000000000001
```

Paste the token into **Connect account** in the Streamlit sidebar. Reuse the same user UUID to keep the same preference profile. Generate a new token when it expires.

This is the local development sign-in flow. A hosted login page is not implemented.

## API example

After starting the API, send a message with your development token:

```sh
curl http://localhost:8000/travel/chat \
  -H 'Authorization: Bearer YOUR_DEVELOPMENT_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "thread_id": "singapore-trip",
    "message_id": "00000000-0000-0000-0000-000000000010",
    "message": "Help me plan a five-day trip from Delhi to Singapore."
  }'
```

Keep the same `thread_id` when replying in the conversation. Use a new UUID `message_id` for each new message. If a request times out, retry with the original ID and text so the API can recover or return the previous response.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | Basic API status |
| GET | `/travel/me` | Current authenticated user |
| POST | `/travel/chat` | Send a message or answer a clarification |
| GET | `/travel/memories` | Read saved preferences |
| DELETE | `/travel/memories/{memory_key}` | Delete a preference; requires a UUID `Idempotency-Key` header |
| GET | `/travel/memory-events/{message_id}` | Check preference-processing status |

All `/travel` endpoints above require a bearer token. The API derives the user from that token rather than trusting a user ID supplied in the message.

## Tests and CI

Tests cover authentication, user isolation, preference extraction and retrieval, concurrent updates, message retries, conversation recovery, budget calculations, UI behavior, and deployment failure handling. External model and travel-service calls are mocked; these tests do not measure live recommendation quality.

For a quick local run:

```sh
uv run python -m unittest discover -s tests -v
```

Database tests are skipped unless `MEMORY_TEST_DATABASE_URL` is set. To run the full suite, first create a separate test database. With the local database container above:

```sh
docker exec trip-planner-db createdb -U trip trip_planner_test
```

Then run with synthetic provider credentials and `.env` loading disabled:

```sh
PYTHON_DOTENV_DISABLED=1 \
MEMORY_TEST_DATABASE_URL=postgresql://trip:local-dev-only@localhost:5432/trip_planner_test \
DATABASE_URL=postgresql://trip:local-dev-only@localhost:5432/trip_planner_test \
GROQ_API_KEY=ci-placeholder \
OPENROUTERNIT_API_KEY=ci-placeholder \
OPENROUTER_API_KEY=ci-placeholder \
OPENROUTERN_API_KEY=ci-placeholder \
SERP_API_KEY=ci-placeholder \
uv run python scripts/ci_tests.py
```

Use a disposable test database, never a production database. The CI runner treats skipped tests as a failure.

GitHub Actions runs on pull requests, pushes to `main`, and manual triggers. It checks for tracked runtime secrets and logs, installs locked dependencies, checks Python syntax, runs tests against PostgreSQL 18, and builds and smoke-checks the Docker image. Non-PR runs also upload the image as an artifact.

## Docker and deployment

Build the application image with:

```sh
docker build -t trip-planner:local .
```

One image supports the API, worker, and UI through different startup commands. It runs as a non-root user and excludes the local `.env` file. See the [container run instructions](docs/ci-cd.md#running-the-image) for separate service commands.

When running containers, configure database and Ollama addresses that the containers can reach. `localhost` inside a container refers to that container, not your computer. The current Ollama URL is configured in `Backend/Config/config.yaml`.

**Current status:** tests and the container build have passed in GitHub Actions. AWS deployment has not been completed or verified end to end.

The repository includes an optional delivery workflow for ECR and ECS/Fargate. It runs only from `main` when `AWS_DEPLOY_ENABLED=true` and the required AWS resources and GitHub environment variables are configured. It publishes the tested image, runs database migrations, updates services, and checks their health.

For manual AWS setup, see the [AWS Console guide](docs/aws-console-deployment.md). Infrastructure definitions also exist under `infra/aws`; they are an alternative setup route. The current provider configuration, including access to Ollama, must be addressed before a hosted deployment can serve real requests.

## Project layout

```text
app/                    FastAPI application, authentication, and chat service
FrontEnd/               Streamlit interface and API client
Backend/
  Config/               Environment loading and provider settings
  Graph/                Planning workflow, agents, routing, and budget logic
  Memory/               Preferences, background worker, and SQL migrations
  integrations/         Clients for external travel services
  tools/                Travel tools used by the workflow
  Schemas/              Validated request and response models
  Prompts/              Instructions used by the model-backed steps
  Logger/               Application logging
tests/                  Unit and integration tests
scripts/                CI checks and ECS deployment helper
.github/workflows/      CI and optional AWS delivery workflows
docs/                   Setup notes and implementation walkthroughs
infra/aws/              Optional Terraform infrastructure definitions
Dockerfile              Shared API, worker, and UI image
```

## Known limits

- Travel suggestions and availability depend on third-party data and model responses. Confirm details with the provider before booking.
- Budget totals include only usable quoted prices. Meals, local transport, insurance, missing prices, and unclear traveler or room coverage are not automatically included.
- Preference updates are asynchronous. If the worker is stopped, messages can remain pending.
- PostgreSQL connections must support session-level advisory locks. Transaction-mode connection pooling is not suitable for the current chat-locking design.
- Production login, live cloud deployment, broader model-quality evaluation, and full data-retention/account-erasure handling remain unfinished.

## Further reading

- [Conversation and memory walkthrough](docs/memory-integration-walkthrough.md)
- [Long-term memory design](docs/long-term-memory.md)
- [Memory backend decision](docs/memory-backend-decision.md)
- [CI and container delivery](docs/ci-cd.md)
- [Manual AWS Console setup](docs/aws-console-deployment.md)
- [AWS infrastructure and delivery details](docs/aws-deployment.md)
