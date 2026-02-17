PYTHON ?= python3

.PHONY: lint test

lint:
	$(PYTHON) -m ruff check src tests

test:
	$(PYTHON) -m pytest
