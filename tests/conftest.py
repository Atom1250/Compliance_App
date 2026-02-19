from __future__ import annotations

import os

# Test suite runs predominantly against SQLite fixtures; keep runtime mode explicit.
os.environ.setdefault("COMPLIANCE_APP_RUNTIME_ENVIRONMENT", "test")
os.environ.setdefault("COMPLIANCE_APP_ALLOW_SQLITE_TRANSITIONAL", "true")
