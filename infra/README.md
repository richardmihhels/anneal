# Anneal Infrastructure

Azure deployment via Terraform. Three Container Apps (core API, dashboard, worker job)
backed by Azure Database for PostgreSQL and ClickHouse Cloud.

## Architecture decisions

**Container Apps over AKS** — solo operator, ~60% lower cost at launch scale, no
Kubernetes operational surface. Built-in KEDA scaling, cron job support, and managed
ingress handle everything Anneal needs.

**ClickHouse Cloud over self-hosted** — removes backup, upgrade, and HA burden. Dev
tier idles to zero; cost delta vs a self-managed container with persistent disk is
small at launch volume. Production tier stays always-on.

## Prerequisites

- Azure CLI (`az`) logged in: `az login`
- Terraform >= 1.9: `brew install terraform`
- A ClickHouse Cloud account with an API key pair
- A GitHub App registered for PR publishing

## First-time setup

### 1. Bootstrap remote state

Run once to create the Azure Storage Account that holds Terraform state:

```bash
bash infra/scripts/bootstrap-state.sh
```

This creates `rg-anneal-tfstate` and storage account `stannealtfstate` with
separate containers for dev and prod state.

### 2. Configure secrets

All secrets are passed as environment variables — never stored in `.tfvars` files.

```bash
export TF_VAR_auth_secret="$(openssl rand -hex 32)"
export TF_VAR_clickhouse_org_id="<your ClickHouse Cloud org ID>"
export TF_VAR_clickhouse_token_key="<key>"
export TF_VAR_clickhouse_token_secret="<secret>"
export TF_VAR_anthropic_api_key="sk-ant-..."
export TF_VAR_github_app_id="<GitHub App ID>"
export TF_VAR_github_app_private_key="$(cat path/to/private-key.pem)"
export TF_VAR_github_webhook_secret="$(openssl rand -hex 32)"
```

In CI, store these as GitHub Actions secrets (Settings → Secrets → Actions).

### 3. Deploy dev

```bash
make deploy-dev
```

Or step by step:

```bash
make tf-init-dev
cd infra
terraform plan  -var-file=environments/dev.tfvars
terraform apply -var-file=environments/dev.tfvars
```

After apply, run migrations:

```bash
PG_URL=$(terraform output -raw postgres_fqdn)
psql "postgresql://anneal:<password>@$PG_URL:5432/anneal?sslmode=require" \
  -f ../core/src/core/db/postgres.sql
```

The ClickHouse migration runs via the same SQL file against ClickHouse Cloud.

### 4. Deploy prod

Prod deployment is gated on manual approval in GitHub Actions:

1. Go to Actions → Deploy → Run workflow → select `prod`
2. The workflow pauses at the `prod` environment gate and notifies required reviewers
3. A reviewer approves; deployment proceeds

Or from the command line (CI credentials required):

```bash
make tf-init-prod
cd infra && terraform apply -var-file=environments/prod.tfvars
```

## Switching environments

Each environment has its own Terraform state backend. Switch by re-initialising:

```bash
make tf-init-dev   # point at dev state
make tf-init-prod  # point at prod state
```

## Rolling back

Terraform manages infrastructure state, not application code. To roll back a bad
image deploy without touching infrastructure:

```bash
# Point the Container App to the previous image tag
az containerapp update \
  --name ca-anneal-dev-core \
  --resource-group rg-anneal-dev \
  --image <ACR_SERVER>/anneal-core:<previous-tag>
```

To roll back infrastructure changes:
```bash
# Restore previous state snapshot from Azure Storage, then re-apply
terraform apply -var-file=environments/dev.tfvars -target=<resource>
```

For a complete environment teardown:
```bash
terraform destroy -var-file=environments/dev.tfvars
```

## Smoke test

```bash
CORE_URL=$(cd infra && terraform output -raw core_url) \
DASHBOARD_URL=$(cd infra && terraform output -raw dashboard_url) \
bash infra/scripts/smoke-test.sh
```

## Monthly cost estimate (dev, low volume, westeurope)

| Resource | SKU | ~EUR/mo |
|---|---|---|
| PostgreSQL Flexible Server | B_Standard_B1ms (1 vCPU, 2 GB) | €15 |
| ClickHouse Cloud | Development (idles to zero) | €47 |
| Container Apps (core + dashboard) | Scale-to-zero, ~10h/day active | €8 |
| Container Apps Job (worker) | 1×/week, 1 CPU-hr | <€1 |
| Container Registry | Basic | €5 |
| Log Analytics | <1 GB/mo ingestion | €3 |
| Key Vault Standard | <10k ops/mo | <€1 |
| **Total** | | **~€79–100** |

Prod estimate: ~€150–180/mo with always-on replicas, B2ms postgres, and
ClickHouse Cloud Production tier.

## GitHub Actions secrets required

| Secret | Description |
|---|---|
| `AZURE_CLIENT_ID` | Service principal client ID (OIDC) |
| `AZURE_TENANT_ID` | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `ACR_NAME` | Container registry name (e.g. `acrannealprod`) |
| `ACR_LOGIN_SERVER` | Registry server (e.g. `acrannealprod.azurecr.io`) |
| `CLICKHOUSE_ORG_ID` | ClickHouse Cloud organisation ID |
| `CLICKHOUSE_TOKEN_KEY` | ClickHouse Cloud API token key |
| `CLICKHOUSE_TOKEN_SECRET` | ClickHouse Cloud API token secret |
| `AUTH_SECRET` | Dashboard auth secret (random 32-byte hex) |
| `ANTHROPIC_API_KEY` | Anthropic API key for the optimization engine |
| `OPENAI_API_KEY` | OpenAI API key (optional) |
| `GITHUB_APP_ID` | GitHub App ID for PR publishing |
| `GITHUB_APP_PRIVATE_KEY` | GitHub App private key (PEM) |
| `GITHUB_WEBHOOK_SECRET` | GitHub webhook HMAC secret |

Set `AZURE_CLIENT_ID` via a federated identity credential (OIDC) on a service
principal with `Contributor` on the subscription and `Key Vault Secrets Officer`
on both Key Vaults. This avoids storing long-lived credentials in GitHub.
