"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { buildEvidencePackDownloadUrl, fetchReportDownload } from "../../lib/api-client";

export default function ReportPage() {
  const searchParams = useSearchParams();
  const [runId, setRunId] = useState(0);
  const [downloadUrl, setDownloadUrl] = useState<string>("");
  const [evidencePackUrl, setEvidencePackUrl] = useState<string>("");
  const [error, setError] = useState("");

  useEffect(() => {
    const fromQuery = Number(searchParams.get("runId") ?? "0");
    const fromStorage = Number(window.localStorage.getItem("run_id") ?? "0");
    setRunId(fromQuery || fromStorage);
  }, [searchParams]);

  useEffect(() => {
    if (!runId) {
      setEvidencePackUrl("");
      return;
    }
    setEvidencePackUrl(buildEvidencePackDownloadUrl(runId));
  }, [runId]);

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
              setError("");
              const response = await fetchReportDownload(runId);
              setDownloadUrl(response.url);
            } catch (caught) {
              setDownloadUrl("");
              setError(`Report link generation failed: ${String(caught)}`);
            }
          }}
        >
          Generate Download Link
        </button>
        {error ? (
          <div>
            <p>{error}</p>
            <button type="button" onClick={() => setError("")}>
              Clear Error
            </button>
          </div>
        ) : null}
      </div>
      {downloadUrl ? (
        <p>
          <a href={downloadUrl}>Download Report</a>
        </p>
      ) : null}
      {evidencePackUrl ? (
        <p>
          <a href={evidencePackUrl}>Download Evidence Pack</a>
        </p>
      ) : null}
    </main>
  );
}
