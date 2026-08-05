.PHONY: setup setup-browser demo dev stop test test-all lint build build-images schemas worker-demo deploy-dev tf-init-dev tf-init-prod

setup:
	uv sync
	cd dashboard && npm ci

setup-browser:
	cd dashboard && npx playwright install --with-deps chromium

demo:
	cd dashboard && ANNEAL_DATA_SOURCE=seed ANNEAL_DEMO_MODE=true npm run dev

dev:
	bash scripts/dev.sh

stop:
	docker compose down

test:
	uv run pytest -v

test-all: test
	cd dashboard && npm test -- --runInBand
	cd dashboard && npm run test:e2e

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy core/src worker/src shared/src sdk/src
	cd dashboard && npm run typecheck

build:
	cd dashboard && npm run build

build-images:
	docker build -f core/Dockerfile -t anneal-core:local .
	docker build -f worker/Dockerfile -t anneal-worker:local .
	docker build -f dashboard/Dockerfile -t anneal-dashboard:local dashboard

worker-demo:
	ANNEAL_MODE=demo ANNEAL_TRIGGER_NOW=true uv run python -m worker.main

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
