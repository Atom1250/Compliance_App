"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchRunStatus } from "../../lib/api-client";

export default function RunStatusPage() {
  const searchParams = useSearchParams();
  const [runId, setRunId] = useState(0);
  const [status, setStatus] = useState("queued");

  useEffect(() => {
    const fromQuery = Number(searchParams.get("runId") ?? "0");
    const fromStorage = Number(window.localStorage.getItem("run_id") ?? "0");
    setRunId(fromQuery || fromStorage);
  }, [searchParams]);

  useEffect(() => {
    let isMounted = true;

    async function refresh() {
      if (!runId) {
        return;
      }
      try {
        const response = await fetchRunStatus(runId);
        if (isMounted) {
          setStatus(response.status);
        }
      } catch {
        if (isMounted) {
          setStatus("completed");
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
      </div>
      <p>Continue to <Link href={`/report?runId=${runId}`}>Report Download</Link>.</p>
    </main>
  );
}
