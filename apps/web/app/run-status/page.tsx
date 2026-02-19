"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchRunStatus } from "../../lib/api-client";
import { stateLabel, StepState, transitionOrStay } from "../../lib/flow-state";

export default function RunStatusPage() {
  const searchParams = useSearchParams();
  const [runId, setRunId] = useState(0);
  const [stepState, setStepState] = useState<StepState>("idle");
  const [statusLabel, setStatusLabel] = useState(stateLabel("idle"));
  const [status, setStatus] = useState("queued");
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
        if (isMounted) {
          setError("");
          setStatus(response.status);
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
        {error ? <p>{error}</p> : null}
        <button type="button" onClick={refreshStatus}>
          Retry Status Check
        </button>
      </div>
      <p>Continue to <Link href={`/report?runId=${runId}`}>Report Download</Link>.</p>
    </main>
  );
}
