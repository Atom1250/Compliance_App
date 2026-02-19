VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
API_HOST ?= 127.0.0.1
API_PORT ?= 8001
WEB_HOST ?= 127.0.0.1
WEB_PORT ?= 3001
API_BIND_HOST ?= $(API_HOST)
WEB_BIND_HOST ?= $(WEB_HOST)
DEV_API_BASE_URL ?= http://$(API_HOST):$(API_PORT)
DEV_API_KEY ?= dev-key
DEV_TENANT_ID ?= default
DEV_DATABASE_URL ?= postgresql+psycopg://compliance:compliance@127.0.0.1:5432/compliance_app
POSTGRES_USER ?= compliance
POSTGRES_DB ?= compliance_app
DEV_USE_COMPOSE ?= true
DEV_PUBLIC ?= false

.PHONY: setup setup-refresh seed-requirements lint test uat ui-setup dev dev-api dev-web compose-up compose-down db-wait

setup:
	@if [ ! -x "$(PYTHON)" ]; then \
		python3 -m venv $(VENV); \
		$(PYTHON) -m pip install --upgrade pip; \
		$(PYTHON) -m pip install -e '.[dev]'; \
	fi

setup-refresh:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e '.[dev]'

seed-requirements: setup
	@/bin/zsh -lc 'set -e; \
	if [ -f .env ]; then set -a; source .env; set +a; fi; \
	COMPLIANCE_APP_DATABASE_URL=$${COMPLIANCE_APP_DATABASE_URL:-$(DEV_DATABASE_URL)} \
	$(PYTHON) -m app.requirements import --bundle requirements/esrs_mini/bundle.json >/dev/null; \
	COMPLIANCE_APP_DATABASE_URL=$${COMPLIANCE_APP_DATABASE_URL:-$(DEV_DATABASE_URL)} \
	$(PYTHON) -m app.requirements import --bundle requirements/esrs_mini_legacy/bundle.json >/dev/null; \
	COMPLIANCE_APP_DATABASE_URL=$${COMPLIANCE_APP_DATABASE_URL:-$(DEV_DATABASE_URL)} \
	$(PYTHON) -m app.requirements import --bundle requirements/green_finance_icma_eugb/bundle.json >/dev/null'

lint: setup
	$(PYTHON) -m ruff check src apps tests

test: setup
	$(PYTHON) -m pytest

uat: setup
	$(PYTHON) scripts/run_uat_harness.py

compose-up:
	docker compose up -d postgres minio

compose-down:
	docker compose down

db-wait:
	@for i in $$(seq 1 60); do \
		if docker compose exec -T postgres pg_isready -U $(POSTGRES_USER) -d $(POSTGRES_DB) >/dev/null 2>&1; then \
			echo "postgres_ready=1"; \
			exit 0; \
		fi; \
		sleep 1; \
	done; \
	echo "postgres_ready=0"; \
	exit 1

ui-setup:
	cd apps/web && npm install

dev-api: setup
	@/bin/zsh -lc 'set -e; \
	if [ -f .env ]; then set -a; source .env; set +a; fi; \
	mkdir -p outputs/dev; \
	COMPLIANCE_APP_DATABASE_URL=$${COMPLIANCE_APP_DATABASE_URL:-$(DEV_DATABASE_URL)} \
	$(PYTHON) -m alembic upgrade head; \
	COMPLIANCE_APP_DATABASE_URL=$${COMPLIANCE_APP_DATABASE_URL:-$(DEV_DATABASE_URL)} \
	$(PYTHON) -m app.requirements import --bundle requirements/esrs_mini/bundle.json >/dev/null; \
	COMPLIANCE_APP_DATABASE_URL=$${COMPLIANCE_APP_DATABASE_URL:-$(DEV_DATABASE_URL)} \
	$(PYTHON) -m app.requirements import --bundle requirements/esrs_mini_legacy/bundle.json >/dev/null; \
	COMPLIANCE_APP_DATABASE_URL=$${COMPLIANCE_APP_DATABASE_URL:-$(DEV_DATABASE_URL)} \
	$(PYTHON) -m app.requirements import --bundle requirements/green_finance_icma_eugb/bundle.json >/dev/null; \
	COMPLIANCE_APP_DATABASE_URL=$${COMPLIANCE_APP_DATABASE_URL:-$(DEV_DATABASE_URL)} \
	$(PYTHON) -m uvicorn apps.api.main:app --host $(API_HOST) --port $(API_PORT) --reload'

dev-web:
	@/bin/zsh -lc 'set -e; \
	if [ -f .env ]; then set -a; source .env; set +a; fi; \
	cd apps/web; \
	if [ ! -x node_modules/.bin/next ]; then npm install; fi; \
	NEXT_PUBLIC_API_BASE_URL=$${NEXT_PUBLIC_API_BASE_URL:-$(DEV_API_BASE_URL)} \
	NEXT_PUBLIC_API_KEY=$${NEXT_PUBLIC_API_KEY:-$(DEV_API_KEY)} \
	NEXT_PUBLIC_TENANT_ID=$${NEXT_PUBLIC_TENANT_ID:-$(DEV_TENANT_ID)} \
	npm run dev -- --hostname $(WEB_HOST) --port $(WEB_PORT)'

dev: setup
	@/bin/zsh -lc 'set -e; \
	if [ -f .env ]; then set -a; source .env; set +a; fi; \
	if [ "$(DEV_USE_COMPOSE)" = "true" ]; then \
		docker compose up -d postgres minio >/dev/null; \
		postgres_ready=0; \
		set +e; \
		for i in {1..60}; do \
			docker compose exec -T postgres pg_isready -U $(POSTGRES_USER) -d $(POSTGRES_DB) >/dev/null 2>&1; \
			rc=$$?; \
			if [ $$rc -eq 0 ]; then \
				postgres_ready=1; \
				break; \
			fi; \
			sleep 1; \
		done; \
		set -e; \
		if [ $$postgres_ready -ne 1 ]; then \
			echo "Postgres failed to become ready in time."; \
			exit 1; \
		fi; \
	fi; \
	api_bind="$(API_BIND_HOST)"; \
	web_bind="$(WEB_BIND_HOST)"; \
	if [ "$(DEV_PUBLIC)" = "true" ]; then \
		api_bind="0.0.0.0"; \
		web_bind="0.0.0.0"; \
	fi; \
	mkdir -p outputs/dev; \
	COMPLIANCE_APP_DATABASE_URL=$${COMPLIANCE_APP_DATABASE_URL:-$(DEV_DATABASE_URL)} $(PYTHON) -m alembic upgrade head >/tmp/compliance-api.log 2>&1; \
	COMPLIANCE_APP_DATABASE_URL=$${COMPLIANCE_APP_DATABASE_URL:-$(DEV_DATABASE_URL)} $(PYTHON) -m app.requirements import --bundle requirements/esrs_mini/bundle.json >>/tmp/compliance-api.log 2>&1; \
	COMPLIANCE_APP_DATABASE_URL=$${COMPLIANCE_APP_DATABASE_URL:-$(DEV_DATABASE_URL)} $(PYTHON) -m app.requirements import --bundle requirements/esrs_mini_legacy/bundle.json >>/tmp/compliance-api.log 2>&1; \
	COMPLIANCE_APP_DATABASE_URL=$${COMPLIANCE_APP_DATABASE_URL:-$(DEV_DATABASE_URL)} $(PYTHON) -m app.requirements import --bundle requirements/green_finance_icma_eugb/bundle.json >>/tmp/compliance-api.log 2>&1; \
	COMPLIANCE_APP_DATABASE_URL=$${COMPLIANCE_APP_DATABASE_URL:-$(DEV_DATABASE_URL)} \
	$(PYTHON) -m uvicorn apps.api.main:app --host $$api_bind --port $(API_PORT) --reload >>/tmp/compliance-api.log 2>&1 & \
	api_pid=$$!; \
	trap "kill $$api_pid 2>/dev/null || true" EXIT INT TERM; \
	for i in {1..30}; do \
		if curl -fsS "http://$(API_HOST):$(API_PORT)/healthz" >/dev/null 2>&1; then \
			break; \
		fi; \
		sleep 0.5; \
	done; \
	if ! curl -fsS "http://$(API_HOST):$(API_PORT)/healthz" >/dev/null 2>&1; then \
		echo "API failed to start on $(API_HOST):$(API_PORT). Recent /tmp/compliance-api.log:"; \
		tail -n 80 /tmp/compliance-api.log; \
		exit 1; \
	fi; \
	cd apps/web; \
	if [ ! -x node_modules/.bin/next ]; then npm install; fi; \
	NEXT_PUBLIC_API_BASE_URL=$${NEXT_PUBLIC_API_BASE_URL:-$(DEV_API_BASE_URL)} \
	NEXT_PUBLIC_API_KEY=$${NEXT_PUBLIC_API_KEY:-$(DEV_API_KEY)} \
	NEXT_PUBLIC_TENANT_ID=$${NEXT_PUBLIC_TENANT_ID:-$(DEV_TENANT_ID)} \
	npm run dev -- --hostname $$web_bind --port $(WEB_PORT) & \
	web_pid=$$!; \
	sleep 2; \
	echo "UI:  http://$(WEB_HOST):$(WEB_PORT)"; \
	echo "API: http://$(API_HOST):$(API_PORT)"; \
	if [ "$(DEV_PUBLIC)" = "true" ]; then \
		echo "Public bind enabled (0.0.0.0). Share your machine IP with testers."; \
	fi; \
	open "http://$(WEB_HOST):$(WEB_PORT)" >/dev/null 2>&1 || true; \
	wait $$web_pid'
