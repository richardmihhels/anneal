# Anneal infrastructure

Terraform deploys Anneal to Azure Container Apps with:

- A public FastAPI core service and Next.js dashboard.
- A Monday 02:00 UTC optimization job.
- An hourly rolling-window regression-alarm job.
- Azure Database for PostgreSQL, ClickHouse Cloud, ACR, Key Vault, Log Analytics, and Application Insights.

Application startup applies idempotent Postgres and ClickHouse schema changes.
Production services fail closed when required databases, authentication, or
worker integrations are missing.

## Prerequisites

- Azure CLI authenticated with `az login`.
- Terraform 1.9 or newer.
- Docker.
- A ClickHouse Cloud organization and API token.
- A GitHub App installed on each target repository, with Contents read/write and Pull requests write access.
- A customer-owned agent replay endpoint for held-out evaluations.

## 1. Bootstrap Terraform state

From the repository root:

```sh
bash infra/scripts/bootstrap-state.sh
```

The script creates separate `dev` and `prod` state containers. Review its
resource names before running it in an existing Azure subscription.

## 2. Supply variables

Secret values must come from `TF_VAR_*` environment variables locally or
GitHub environment secrets in CI. Do not put them in `.tfvars` files.

```sh
export TF_VAR_clickhouse_org_id=...
export TF_VAR_clickhouse_token_key=...
export TF_VAR_clickhouse_token_secret=...
export TF_VAR_auth_secret="$(openssl rand -hex 32)"
export TF_VAR_api_key="$(openssl rand -hex 32)"
export TF_VAR_dashboard_email=lead@example.com
export TF_VAR_dashboard_password=...
export TF_VAR_anthropic_api_key=...
export TF_VAR_openai_api_key=...
export TF_VAR_github_app_id=...
export TF_VAR_github_app_private_key="$(<path/to/anneal-app.pem)"
export TF_VAR_customers_json="$(jq -c . customers.json)"
export TF_VAR_agent_runner_url=https://agent.example.com/internal/anneal-eval
export TF_VAR_agent_runner_api_key=...
export TF_VAR_image_tag=<git-sha>
```

`customers.json` can be a single object, a list, or an object with a
`customers` list. Each entry has the same fields as `anneal.example.yml`.

Optional waitlist delivery uses `TF_VAR_waitlist_webhook_url` and
`TF_VAR_waitlist_webhook_token`. With no webhook, the production waitlist route
returns `503` instead of pretending that a signup was stored.

## 3. Bootstrap the registry on a new environment

The deploy workflow pushes images before the full Terraform apply, so a brand
new environment needs its registry once. Initialize the desired backend and
create only the resource group and ACR:

```sh
make tf-init-dev
terraform -chdir=infra apply \
  -var-file=environments/dev.tfvars \
  -target=azurerm_resource_group.main \
  -target=azurerm_container_registry.main
```

Record the `registry_server` output and the registry name as the corresponding
GitHub environment secrets. This targeted apply is a one-time bootstrap; use
normal full plans afterward.

## 4. Plan and deploy

Local development plan:

```sh
make tf-init-dev
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate
terraform -chdir=infra plan -var-file=environments/dev.tfvars
```

The checked-in `Deploy` workflow is manual for both environments. Choose
`dev` or `prod`; it builds immutable SHA-tagged images, pushes them to ACR,
applies Terraform, and smoke-tests both public health routes. Protect the
GitHub `prod` environment with required reviewers.

To apply locally after pushing the selected image tag:

```sh
terraform -chdir=infra apply -var-file=environments/dev.tfvars
```

## GitHub environment secrets

Create `dev` and `prod` GitHub environments and provide:

| Secret | Purpose |
| --- | --- |
| `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` | Azure OIDC login |
| `ACR_NAME`, `ACR_LOGIN_SERVER` | Image push target |
| `CLICKHOUSE_ORG_ID`, `CLICKHOUSE_TOKEN_KEY`, `CLICKHOUSE_TOKEN_SECRET` | ClickHouse provider |
| `AUTH_SECRET` | Dashboard session signing |
| `ANNEAL_API_KEY` | Core API and dashboard service authentication |
| `ANNEAL_DASHBOARD_EMAIL`, `ANNEAL_DASHBOARD_PASSWORD` | Self-hosted dashboard login |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | Judge, mutation, labels, and embeddings |
| `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY` | Gated PR publishing |
| `ANNEAL_CUSTOMERS_JSON` | Validated customer/agent configuration |
| `ANNEAL_AGENT_RUNNER_URL`, `ANNEAL_AGENT_RUNNER_API_KEY` | Isolated holdout replay |
| `ANNEAL_WAITLIST_WEBHOOK_URL`, `ANNEAL_WAITLIST_WEBHOOK_TOKEN` | Optional waitlist delivery |

The Azure service principal should use a GitHub OIDC federated identity. It
needs enough subscription scope to manage these resources and push images;
application identities receive only ACR pull and Key Vault secret-read roles.

## Operations

Run the post-deploy check manually with Terraform outputs:

```sh
CORE_URL="$(terraform -chdir=infra output -raw core_url)" \
DASHBOARD_URL="$(terraform -chdir=infra output -raw dashboard_url)" \
bash infra/scripts/smoke-test.sh
```

Roll back application code by setting `image_tag` to a previously pushed SHA
and applying Terraform. Review a destroy plan carefully before removing an
environment; PostgreSQL and Terraform state contain durable data.

Cloud prices and ClickHouse tiers change. Use the Azure and ClickHouse pricing
calculators with the selected environment tfvars before deployment rather than
relying on a static estimate in this repository.
