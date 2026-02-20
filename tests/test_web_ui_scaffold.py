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
    assert "export async function fetchRunDiagnostics" in api_client
    assert "export async function rerunWithoutCache" in api_client
    assert "export async function fetchReportHtml" in api_client
    assert "export async function fetchEvidencePackPreview" in api_client
    assert "export async function fetchLLMHealth" in api_client
    assert "export async function autoDiscoverDocuments" in api_client
    assert "export async function orchestrateDiscoveryAndRun" in api_client
    assert "export function buildEvidencePackDownloadUrl" in api_client
    assert "/llm-health" in api_client
    assert "llm_provider" in api_client
    assert "/runs/${runId}/evidence-pack" in api_client
    assert "Demo mode continues" not in api_client

    company_page = (WEB_ROOT / "app/company/page.tsx").read_text()
    upload_page = (WEB_ROOT / "app/upload/page.tsx").read_text()
    run_config_page = (WEB_ROOT / "app/run-config/page.tsx").read_text()
    run_status_page = (WEB_ROOT / "app/run-status/page.tsx").read_text()
    report_page = (WEB_ROOT / "app/report/page.tsx").read_text()
    assert "Retry Save" in company_page
    assert "Retry upload" in upload_page
    assert "Auto-Find ESG Documents" in upload_page
    assert "Auto-Find + Start Run" in upload_page
    assert "Guided Run Bundle" in upload_page
    assert "Jurisdiction Overlay" in upload_page
    assert "Bundle Version" in run_config_page
    assert "Jurisdiction Overlay" in run_config_page
    assert "Execution Provider" in run_config_page
    assert "fetchLLMHealth" in run_config_page
    assert "Run LLM Probe" in run_config_page
    assert "Retry Start Run" in run_config_page
    assert "fetchRunStatus" in run_status_page
    assert "Retry Status Check" in run_status_page
    assert "Re-run Without Cache" in run_status_page
    assert "Stage Progress:" in run_status_page
    assert "Preview Report" in report_page
    assert "Preview Evidence Pack" in report_page
    assert "Download Evidence Pack" in report_page
    assert "demo-report" not in report_page
