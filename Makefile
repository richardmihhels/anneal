.PHONY: setup dev test lint build schemas deploy-dev tf-init-dev tf-init-prod

setup:
	uv sync
	cd dashboard && npm install

dev:
	docker-compose up -d
	cd dashboard && npm run dev &
	uv run uvicorn core.main:app --reload --port 8000

test:
	uv run pytest -v

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy core/src worker/src shared/src
	cd dashboard && npm run typecheck

build:
	cd dashboard && npm run build

schemas:
	uv run python shared/generate_schemas.py

# ── Infrastructure ────────────────────────────────────────────────────────────

tf-init-dev:
	cd infra && terraform init -backend-config=backends/dev.hcl -reconfigure

tf-init-prod:
	cd infra && terraform init -backend-config=backends/prod.hcl -reconfigure

deploy-dev: tf-init-dev
	cd infra && terraform apply \
		-var-file=environments/dev.tfvars \
		-auto-approve \
		-input=false
	@CORE_URL=$$(cd infra && terraform output -raw core_url) \
	 DASHBOARD_URL=$$(cd infra && terraform output -raw dashboard_url) \
	 bash infra/scripts/smoke-test.sh
