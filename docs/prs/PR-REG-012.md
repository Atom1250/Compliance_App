# PR-REG-012 — Metric Datapoint Type System

## Scope implemented
- Extended datapoint definition schema with `datapoint_type` (`narrative|metric`) and `requires_baseline`.
- Added metric verification contract with structured metric payload extraction.
- Implemented downgrade logic for missing numeric/unit/year evidence and baseline-required metrics.
- Added tests for metric validation and baseline failure semantics.

## Commands run
- `make lint` ✅
- `make test` ✅
