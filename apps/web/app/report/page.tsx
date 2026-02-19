"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  EvidencePackPreviewResponse,
  downloadEvidencePack,
  downloadRunReport,
  fetchEvidencePackPreview,
  fetchReportHtml
} from "../../lib/api-client";
import { stateLabel, StepState, transitionOrStay } from "../../lib/flow-state";

export default function ReportPage() {
  const searchParams = useSearchParams();
  const [runId, setRunId] = useState(0);
  const [stepState, setStepState] = useState<StepState>("idle");
  const [statusLabel, setStatusLabel] = useState(stateLabel("idle"));
  const [reportHtml, setReportHtml] = useState<string>("");
  const [evidencePreview, setEvidencePreview] = useState<EvidencePackPreviewResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const fromQuery = Number(searchParams.get("runId") ?? "0");
    const fromStorage = Number(window.localStorage.getItem("run_id") ?? "0");
    setRunId(fromQuery || fromStorage);
  }, [searchParams]);

  return (
    <main>
      <h1>Report Review and Download</h1>
      <nav>
        <Link href="/run-status">Back to Status</Link>
      </nav>
      <div className="panel">
        <p>Run ID: {runId || "N/A"}</p>
        <p>Step Key: {stepState}</p>
        <button
          type="button"
          onClick={async () => {
            try {
              setStepState((state) => transitionOrStay(state, "submitting"));
              setStatusLabel(stateLabel("submitting"));
              setError("");
              const html = await fetchReportHtml(runId);
              setReportHtml(html);
              setStepState((state) => transitionOrStay(state, "success"));
              setStatusLabel("Completed: report preview loaded.");
            } catch (caught) {
              setReportHtml("");
              setError(`Report preview failed: ${String(caught)}. Confirm run is completed and retry.`);
              setStepState((state) => transitionOrStay(state, "error"));
              setStatusLabel(stateLabel("error"));
            }
          }}
        >
          Preview Report
        </button>
        <button
          type="button"
          onClick={async () => {
            try {
              setStepState((state) => transitionOrStay(state, "submitting"));
              setStatusLabel(stateLabel("submitting"));
              setError("");
              const preview = await fetchEvidencePackPreview(runId);
              setEvidencePreview(preview);
              setStepState((state) => transitionOrStay(state, "success"));
              setStatusLabel("Completed: evidence preview loaded.");
            } catch (caught) {
              setEvidencePreview(null);
              setError(`Evidence preview failed: ${String(caught)}. Confirm run is completed and retry.`);
              setStepState((state) => transitionOrStay(state, "error"));
              setStatusLabel(stateLabel("error"));
            }
          }}
        >
          Preview Evidence Pack
        </button>
        <button
          type="button"
          onClick={async () => {
            try {
              setStepState((state) => transitionOrStay(state, "submitting"));
              setStatusLabel(stateLabel("submitting"));
              setError("");
              await downloadRunReport(runId);
              setStepState((state) => transitionOrStay(state, "success"));
              setStatusLabel("Completed: report downloaded.");
            } catch (caught) {
              setError(`Report download failed: ${String(caught)}. Verify browser download permissions.`);
              setStepState((state) => transitionOrStay(state, "error"));
              setStatusLabel(stateLabel("error"));
            }
          }}
        >
          Download Report
        </button>
        <button
          type="button"
          onClick={async () => {
            try {
              setStepState((state) => transitionOrStay(state, "submitting"));
              setStatusLabel(stateLabel("submitting"));
              setError("");
              await downloadEvidencePack(runId);
              setStepState((state) => transitionOrStay(state, "success"));
              setStatusLabel("Completed: evidence pack downloaded.");
            } catch (caught) {
              setError(`Evidence pack download failed: ${String(caught)}. Verify browser download permissions.`);
              setStepState((state) => transitionOrStay(state, "error"));
              setStatusLabel(stateLabel("error"));
            }
          }}
        >
          Download Evidence Pack
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
      <p>Step State: {statusLabel}</p>
      {reportHtml ? (
        <section className="panel">
          <h2>Report Preview</h2>
          <iframe
            title="Report Preview"
            srcDoc={reportHtml}
            style={{ width: "100%", minHeight: "480px", border: "1px solid #ccc" }}
          />
        </section>
      ) : null}
      {evidencePreview ? (
        <section className="panel">
          <h2>Evidence Pack Preview</h2>
          <p>Run: {evidencePreview.run_id}</p>
          <p>Pack files: {evidencePreview.pack_file_count}</p>
          <p>Referenced documents: {evidencePreview.document_count}</p>
          <p>Has assessments: {String(evidencePreview.has_assessments)}</p>
          <p>Has evidence rows: {String(evidencePreview.has_evidence)}</p>
          <p>Entries: {evidencePreview.entries.join(", ")}</p>
        </section>
      ) : null}
    </main>
  );
}
