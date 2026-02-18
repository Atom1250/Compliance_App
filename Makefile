PYTHON ?= python3
API_HOST ?= 127.0.0.1
API_PORT ?= 8001
WEB_HOST ?= 127.0.0.1
WEB_PORT ?= 3001
DEV_API_BASE_URL ?= http://$(API_HOST):$(API_PORT)
DEV_API_KEY ?= dev-key
DEV_TENANT_ID ?= default

.PHONY: lint test uat ui-setup dev dev-api dev-web

lint:
	$(PYTHON) -m ruff check src apps tests

test:
	$(PYTHON) -m pytest

uat:
	$(PYTHON) scripts/run_uat_harness.py

ui-setup:
	cd apps/web && npm install

dev-api:
	$(PYTHON) -m uvicorn apps.api.main:app --host $(API_HOST) --port $(API_PORT) --reload

dev-web:
	cd apps/web && \
	if [ ! -x node_modules/.bin/next ]; then npm install; fi && \
	NEXT_PUBLIC_API_BASE_URL=$(DEV_API_BASE_URL) \
	NEXT_PUBLIC_API_KEY=$(DEV_API_KEY) \
	NEXT_PUBLIC_TENANT_ID=$(DEV_TENANT_ID) \
	npm run dev -- --hostname $(WEB_HOST) --port $(WEB_PORT)

dev:
	@/bin/zsh -lc 'set -e; \
	$(PYTHON) -m uvicorn apps.api.main:app --host $(API_HOST) --port $(API_PORT) --reload >/tmp/compliance-api.log 2>&1 & \
	api_pid=$$!; \
	trap "kill $$api_pid 2>/dev/null || true" EXIT INT TERM; \
	cd apps/web; \
	if [ ! -x node_modules/.bin/next ]; then npm install; fi; \
	NEXT_PUBLIC_API_BASE_URL=$(DEV_API_BASE_URL) \
	NEXT_PUBLIC_API_KEY=$(DEV_API_KEY) \
	NEXT_PUBLIC_TENANT_ID=$(DEV_TENANT_ID) \
	npm run dev -- --hostname $(WEB_HOST) --port $(WEB_PORT) & \
	web_pid=$$!; \
	sleep 2; \
	open "http://$(WEB_HOST):$(WEB_PORT)" >/dev/null 2>&1 || true; \
	wait $$web_pid'
