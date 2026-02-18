"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchReportDownload } from "../../lib/api-client";

export default function ReportPage() {
  const searchParams = useSearchParams();
  const [runId, setRunId] = useState(0);
  const [downloadUrl, setDownloadUrl] = useState<string>("");

  useEffect(() => {
    const fromQuery = Number(searchParams.get("runId") ?? "0");
    const fromStorage = Number(window.localStorage.getItem("run_id") ?? "0");
    setRunId(fromQuery || fromStorage);
  }, [searchParams]);

  return (
    <main>
      <h1>Report Download</h1>
      <nav>
        <Link href="/run-status">Back to Status</Link>
      </nav>
      <div className="panel">
        <p>Run ID: {runId || "N/A"}</p>
        <button
          type="button"
          onClick={async () => {
            try {
              const response = await fetchReportDownload(runId);
              setDownloadUrl(response.url);
            } catch {
              setDownloadUrl(`/reports/demo-report-${runId || "latest"}.html`);
            }
          }}
        >
          Generate Download Link
        </button>
      </div>
      {downloadUrl ? (
        <p>
          <a href={downloadUrl}>Download Report</a>
        </p>
      ) : null}
    </main>
  );
}
