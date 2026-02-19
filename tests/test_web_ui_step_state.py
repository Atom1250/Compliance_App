from pathlib import Path

WEB_ROOT = Path("apps/web")


def test_step_state_helper_defines_explicit_transitions() -> None:
    flow_state = (WEB_ROOT / "lib/flow-state.ts").read_text()
    assert "export type StepState" in flow_state
    assert 'idle: ["validating", "submitting", "error"]' in flow_state
    assert 'validating: ["submitting", "error"]' in flow_state
    assert 'submitting: ["success", "error"]' in flow_state
    assert "export function transitionOrStay" in flow_state
    assert "export function stateLabel" in flow_state


def test_run_setup_pages_use_step_state_transitions() -> None:
    company_page = (WEB_ROOT / "app/company/page.tsx").read_text()
    upload_page = (WEB_ROOT / "app/upload/page.tsx").read_text()
    run_config_page = (WEB_ROOT / "app/run-config/page.tsx").read_text()
    run_status_page = (WEB_ROOT / "app/run-status/page.tsx").read_text()

    assert "useState<StepState>" in company_page
    assert 'transitionOrStay(state, "validating")' in company_page
    assert "Step Key:" in company_page
    assert "Company setup failed:" in company_page

    assert "useState<StepState>" in upload_page
    assert 'transitionOrStay(state, "validating")' in upload_page
    assert 'transitionOrStay(state, "error")' in upload_page
    assert "Step Key:" in upload_page
    assert "Auto-discovery failed:" in upload_page

    assert "useState<StepState>" in run_config_page
    assert 'transitionOrStay(state, "submitting")' in run_config_page
    assert "Step Key:" in run_config_page
    assert "Run start failed:" in run_config_page

    assert "useState<StepState>" in run_status_page
    assert 'transitionOrStay(state, "error")' in run_status_page
    assert "Step Key:" in run_status_page
    assert "Status fetch failed:" in run_status_page


def test_report_page_uses_step_state_and_actionable_errors() -> None:
    report_page = (WEB_ROOT / "app/report/page.tsx").read_text()

    assert "useState<StepState>" in report_page
    assert 'transitionOrStay(state, "submitting")' in report_page
    assert 'transitionOrStay(state, "success")' in report_page
    assert "Step Key:" in report_page
    assert "Report preview failed:" in report_page
    assert "Evidence pack download failed:" in report_page
