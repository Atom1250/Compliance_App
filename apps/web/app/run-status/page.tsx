"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  fetchRunDiagnostics,
  fetchRunStatus,
  rerunWithoutCache,
  RunDiagnosticsResponse
} from "../../lib/api-client";
import { stateLabel, StepState, transitionOrStay } from "../../lib/flow-state";

const STAGE_ORDER = [
  "run.created",
  "run.execution.queued",
  "run.execution.started",
  "assessment.pipeline.started",
  "assessment.pipeline.completed",
  "run.execution.completed"
] as const;

function stageLabel(stage: string): string {
  const labels: Record<string, string> = {
    "run.created": "Run Created",
    "run.execution.queued": "Queued",
    "run.execution.started": "Execution Started",
    "assessment.pipeline.started": "Assessment Running",
    "assessment.pipeline.completed": "Assessment Done",
    "run.execution.completed": "Run Completed"
  };
  return labels[stage] ?? stage;
}

export default function RunStatusPage() {
  const searchParams = useSearchParams();
  const [runId, setRunId] = useState(0);
  const [stepState, setStepState] = useState<StepState>("idle");
  const [statusLabel, setStatusLabel] = useState(stateLabel("idle"));
  const [status, setStatus] = useState("queued");
  const [diagnostics, setDiagnostics] = useState<RunDiagnosticsResponse | null>(null);
  const [rerunProvider, setRerunProvider] = useState<
    "deterministic_fallback" | "local_lm_studio" | "openai_cloud"
  >("deterministic_fallback");
  const [isRerunning, setIsRerunning] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const fromQuery = Number(searchParams.get("runId") ?? "0");
    const fromStorage = Number(window.localStorage.getItem("run_id") ?? "0");
    setRunId(fromQuery || fromStorage);
  }, [searchParams]);

  async function refreshStatus() {
    setStepState((state) => transitionOrStay(state, "validating"));
    setStatusLabel(stateLabel("validating"));
    if (!runId) {
      setError("Run ID is missing.");
      setStepState((state) => transitionOrStay(state, "error"));
      setStatusLabel(stateLabel("error"));
      return;
    }
    setError("");
    try {
      setStepState((state) => transitionOrStay(state, "submitting"));
      setStatusLabel(stateLabel("submitting"));
      const response = await fetchRunStatus(runId);
      setStatus(response.status);
      const diag = await fetchRunDiagnostics(runId);
      setDiagnostics(diag);
      if (diag.llm_provider) {
        setRerunProvider(diag.llm_provider as "deterministic_fallback" | "local_lm_studio" | "openai_cloud");
      }
      setStepState((state) => transitionOrStay(state, "success"));
      setStatusLabel(`Completed: ${response.status}`);
    } catch (caught) {
      setError(`Status fetch failed: ${String(caught)}. Ensure API is running and retry.`);
      setStepState((state) => transitionOrStay(state, "error"));
      setStatusLabel(stateLabel("error"));
    }
  }

  useEffect(() => {
    let isMounted = true;

    async function refresh() {
      try {
        if (!runId) {
          return;
        }
        const response = await fetchRunStatus(runId);
        const diag = await fetchRunDiagnostics(runId);
        if (isMounted) {
          setError("");
          setStatus(response.status);
          setDiagnostics(diag);
          if (diag.llm_provider) {
            setRerunProvider(
              diag.llm_provider as "deterministic_fallback" | "local_lm_studio" | "openai_cloud"
            );
          }
          setStepState((state) => transitionOrStay(state, "success"));
          setStatusLabel(`Completed: ${response.status}`);
        }
      } catch (caught) {
        if (isMounted) {
          setError(`Status fetch failed: ${String(caught)}. Ensure API is running and retry.`);
          setStepState((state) => transitionOrStay(state, "error"));
          setStatusLabel(stateLabel("error"));
        }
      }
    }

    void refresh();
    return () => {
      isMounted = false;
    };
  }, [runId]);

  useEffect(() => {
    if (!runId) {
      return;
    }
    const interval = window.setInterval(() => {
      void refreshStatus();
    }, 2000);
    return () => window.clearInterval(interval);
  }, [runId]);

  const stageOutcomes = diagnostics?.stage_outcomes ?? {};
  const completedStages = STAGE_ORDER.filter((stage) => stageOutcomes[stage]).length;
  const progressPct = Math.round((completedStages / STAGE_ORDER.length) * 100);
  const currentStage =
    status === "failed"
      ? "run.execution.failed"
      : STAGE_ORDER.find((stage) => !stageOutcomes[stage]) ?? "run.execution.completed";

  return (
    <main>
      <h1>Run Status</h1>
      <nav>
        <Link href="/run-config">Back to Config</Link>
      </nav>
      <div className="panel">
        <p>Run ID: {runId || "N/A"}</p>
        <p>Step Key: {stepState}</p>
        <p>Step State: {statusLabel}</p>
        <p>Current Status: {status}</p>
        <div className="progress-wrap">
          <div className="progress-bar" style={{ width: `${progressPct}%` }} />
        </div>
        <p>Stage Progress: {progressPct}%</p>
        <ul className="stage-list">
          {STAGE_ORDER.map((stage) => {
            const done = Boolean(stageOutcomes[stage]);
            const active = !done && currentStage === stage && status !== "failed";
            return (
              <li key={stage} className={`stage-item ${done ? "done" : ""}`}>
                <span className={`stage-dot ${done ? "done" : active ? "active" : ""}`} />
                <span>{stageLabel(stage)}</span>
              </li>
            );
          })}
          {status === "failed" ? (
            <li className="stage-item failed">
              <span className="stage-dot failed active" />
              <span>Run Failed</span>
            </li>
          ) : null}
        </ul>
        {error ? <p>{error}</p> : null}
        <button type="button" onClick={refreshStatus}>
          Retry Status Check
        </button>
        <div className="row">
          <label>
            Re-run Provider
            <select
              value={rerunProvider}
              onChange={(event) =>
                setRerunProvider(
                  event.target.value as "deterministic_fallback" | "local_lm_studio" | "openai_cloud"
                )
              }
            >
              <option value="deterministic_fallback">deterministic_fallback</option>
              <option value="openai_cloud">openai_cloud</option>
              <option value="local_lm_studio">local_lm_studio</option>
            </select>
          </label>
          <button
            type="button"
            onClick={async () => {
              if (!runId) {
                return;
              }
              setIsRerunning(true);
              setError("");
              try {
                const rerun = await rerunWithoutCache(runId, rerunProvider);
                window.localStorage.setItem("run_id", String(rerun.run_id));
                setRunId(rerun.run_id);
                setStatus("queued");
                setStatusLabel(`Completed: rerun queued (${rerun.run_id})`);
                setStepState((state) => transitionOrStay(state, "success"));
              } catch (caught) {
                setError(`Rerun failed: ${String(caught)}.`);
                setStepState((state) => transitionOrStay(state, "error"));
                setStatusLabel(stateLabel("error"));
              } finally {
                setIsRerunning(false);
              }
            }}
            disabled={isRerunning}
          >
            {isRerunning ? "Starting Rerun..." : "Re-run Without Cache"}
          </button>
        </div>
      </div>
      {diagnostics ? (
        <div className="panel">
          <h2>Run Summary</h2>
          <p>Provider: {diagnostics.llm_provider ?? "unknown"}</p>
          <p>Cache Hit: {diagnostics.cache_hit === null ? "unknown" : String(diagnostics.cache_hit)}</p>
          <p>
            Documents in Scope: {diagnostics.scoped_document_count} (direct:{" "}
            {diagnostics.direct_document_count}, shared: {diagnostics.shared_document_count})
          </p>
          <p>Chunks in Scope: {diagnostics.chunk_count}</p>
          <p>Assessments: {diagnostics.assessment_count}</p>
          <p>
            Diagnostics Failures: {diagnostics.diagnostics_failures}/{diagnostics.diagnostics_count}
          </p>
          {diagnostics.shared_document_count > 0 ? (
            <p className="badge">Using linked/shared documents</p>
          ) : null}
          {diagnostics.latest_failure_reason ? (
            <p>Latest Failure Reason: {diagnostics.latest_failure_reason}</p>
          ) : null}
        </div>
      ) : null}
      <p>Continue to <Link href={`/report?runId=${runId}`}>Report Download</Link>.</p>
    </main>
  );
}
