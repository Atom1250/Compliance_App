PYTHON ?= python3

.PHONY: lint test uat

lint:
	$(PYTHON) -m ruff check src apps tests

test:
	$(PYTHON) -m pytest

uat:
	$(PYTHON) scripts/run_uat_harness.py
