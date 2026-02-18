"""Run the deterministic UAT harness and validate against golden artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
from compliance_app.uat_harness import run_uat_harness


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--work-dir",
        default="outputs/uat",
        help="Directory used for temporary DB/object/evidence artifacts.",
    )
    parser.add_argument(
        "--golden",
        default="tests/golden/uat_harness_snapshot.json",
        help="Golden summary snapshot file.",
    )
    parser.add_argument(
        "--update-golden",
        action="store_true",
        help="Overwrite golden file with current harness summary.",
    )
    args = parser.parse_args()

    summary = run_uat_harness(work_dir=Path(args.work_dir))
    golden_path = Path(args.golden)
    if args.update_golden:
        golden_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
        print(f"Updated golden snapshot: {golden_path}")
        return 0

    expected = json.loads(golden_path.read_text())
    if summary != expected:
        print("UAT harness summary mismatch.")
        print("Expected:")
        print(json.dumps(expected, indent=2, sort_keys=True))
        print("Actual:")
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 1

    print("UAT harness summary matches golden snapshot.")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
