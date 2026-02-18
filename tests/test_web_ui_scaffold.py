from pathlib import Path

WEB_ROOT = Path("apps/web")


def test_nextjs_scaffold_contains_required_workflow_pages() -> None:
    required_pages = [
        WEB_ROOT / "app/company/page.tsx",
        WEB_ROOT / "app/upload/page.tsx",
        WEB_ROOT / "app/run-config/page.tsx",
        WEB_ROOT / "app/run-status/page.tsx",
        WEB_ROOT / "app/report/page.tsx",
    ]

    for page in required_pages:
        assert page.exists(), f"missing page: {page}"


def test_pages_use_shared_api_client() -> None:
    api_client = (WEB_ROOT / "lib/api-client.ts").read_text()
    assert "export async function uploadDocument" in api_client
    assert "export async function configureRun" in api_client
    assert "export async function fetchRunStatus" in api_client
    assert "export async function fetchReportDownload" in api_client

    run_status_page = (WEB_ROOT / "app/run-status/page.tsx").read_text()
    report_page = (WEB_ROOT / "app/report/page.tsx").read_text()
    assert "fetchRunStatus" in run_status_page
    assert "fetchReportDownload" in report_page
