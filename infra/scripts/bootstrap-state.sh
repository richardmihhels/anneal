#!/usr/bin/env bash
# Bootstrap remote Terraform state storage in Azure.
# Run once before the first `terraform init`. Idempotent.
#
# Usage: ./infra/scripts/bootstrap-state.sh
# Requires: az CLI logged in with sufficient permissions.

set -euo pipefail

LOCATION="${AZURE_LOCATION:-westeurope}"
RG="rg-anneal-tfstate"
SA="stannealtfstate"

echo "==> Creating resource group: $RG"
az group create \
  --name "$RG" \
  --location "$LOCATION" \
  --output none

echo "==> Creating storage account: $SA"
az storage account create \
  --name "$SA" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --allow-blob-public-access false \
  --min-tls-version TLS1_2 \
  --output none

echo "==> Creating state containers"
for env in dev prod; do
  az storage container create \
    --name "tfstate-${env}" \
    --account-name "$SA" \
    --auth-mode login \
    --output none
  echo "    tfstate-${env} ready"
done

echo "==> Done. State backend is ready."
echo "    Run: cd infra && terraform init -backend-config=backends/dev.hcl"
