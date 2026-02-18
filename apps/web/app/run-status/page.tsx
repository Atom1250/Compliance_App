"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchRunStatus } from "../../lib/api-client";

export default function RunStatusPage() {
  const searchParams = useSearchParams();
  const [runId, setRunId] = useState(0);
  const [status, setStatus] = useState("queued");
  const [error, setError] = useState("");

  useEffect(() => {
    const fromQuery = Number(searchParams.get("runId") ?? "0");
    const fromStorage = Number(window.localStorage.getItem("run_id") ?? "0");
    setRunId(fromQuery || fromStorage);
  }, [searchParams]);

  async function refreshStatus() {
    if (!runId) {
      setError("Run ID is missing.");
      return;
    }
    setError("");
    try {
      const response = await fetchRunStatus(runId);
      setStatus(response.status);
    } catch (caught) {
      setError(`Status fetch failed: ${String(caught)}`);
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
        }
      } catch (caught) {
        if (isMounted) {
          setError(`Status fetch failed: ${String(caught)}`);
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
