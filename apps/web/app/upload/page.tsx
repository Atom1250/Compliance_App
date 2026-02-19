"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { autoDiscoverDocuments, orchestrateDiscoveryAndRun, uploadDocument } from "../../lib/api-client";
import { stateLabel, StepState, transitionOrStay } from "../../lib/flow-state";

export default function UploadPage() {
  const router = useRouter();
  const [stepState, setStepState] = useState<StepState>("idle");
  const [status, setStatus] = useState(stateLabel("idle"));
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isAutoDiscovering, setIsAutoDiscovering] = useState(false);
  const [isGuidedRunning, setIsGuidedRunning] = useState(false);
  const [title, setTitle] = useState("Annual ESG Report");

  async function runUpload(form: FormData) {
    setStepState((state) => transitionOrStay(state, "validating"));
    setStatus(stateLabel("validating"));
    const file = form.get("file");
    const companyId = Number(localStorage.getItem("company_id") ?? "0");
    if (!(file instanceof File) || !companyId) {
      setStepState((state) => transitionOrStay(state, "error"));
      setStatus(stateLabel("error"));
      setError("Missing file or company id.");
      return;
    }
    setIsUploading(true);
    setError("");
    setStepState((state) => transitionOrStay(state, "submitting"));
    setStatus(stateLabel("submitting"));
    try {
      const uploaded = await uploadDocument({ companyId, file, title });
      if (!uploaded?.documentId) {
        throw new Error("Missing document id in API response.");
      }
      setStepState((state) => transitionOrStay(state, "success"));
      setStatus(`Completed: uploaded document ${uploaded.documentId}`);
    } catch (caught) {
      setStepState((state) => transitionOrStay(state, "error"));
      setStatus(stateLabel("error"));
      setError(`Upload failed: ${String(caught)}. Confirm title/file and API connectivity.`);
    } finally {
      setIsUploading(false);
    }
  }

  async function runAutoDiscovery() {
    setStepState((state) => transitionOrStay(state, "validating"));
    setStatus(stateLabel("validating"));
    const companyId = Number(localStorage.getItem("company_id") ?? "0");
    if (!companyId) {
      setStepState((state) => transitionOrStay(state, "error"));
      setStatus(stateLabel("error"));
      setError("Missing company id.");
      return;
    }
    setIsAutoDiscovering(true);
    setError("");
    setStepState((state) => transitionOrStay(state, "submitting"));
    setStatus(stateLabel("submitting"));
    try {
      const result = await autoDiscoverDocuments(companyId, 3);
      setStepState((state) => transitionOrStay(state, "success"));
      setStatus(
        `Completed: auto-discovery ingested ${result.ingested_count} documents ` +
          `(from ${result.candidates_considered} candidates).`
      );
    } catch (caught) {
      setStepState((state) => transitionOrStay(state, "error"));
      setStatus(stateLabel("error"));
      setError(`Auto-discovery failed: ${String(caught)}. Check Tavily key and network settings.`);
    } finally {
      setIsAutoDiscovering(false);
    }
  }

  async function runGuidedFlow() {
    setStepState((state) => transitionOrStay(state, "validating"));
    setStatus(stateLabel("validating"));
    const companyId = Number(localStorage.getItem("company_id") ?? "0");
    if (!companyId) {
      setStepState((state) => transitionOrStay(state, "error"));
      setStatus(stateLabel("error"));
      setError("Missing company id.");
      return;
    }
    const reportingYearEnd = Number(localStorage.getItem("company_reporting_year_end") ?? "2026");
    const bundleVersion = Number.isFinite(reportingYearEnd) && reportingYearEnd < 2026 ? "2024.01" : "2026.01";
    setIsGuidedRunning(true);
    setError("");
    setStepState((state) => transitionOrStay(state, "submitting"));
    setStatus("Submitting...");
    try {
      const result = await orchestrateDiscoveryAndRun({
        companyId,
        bundleId: "esrs_mini",
        bundleVersion,
        llmProvider: "deterministic_fallback",
        maxDocuments: 3
      });
      if (!result.runId) {
        throw new Error("Missing run id in guided flow response.");
      }
      localStorage.setItem("run_id", String(result.runId));
      setStepState((state) => transitionOrStay(state, "success"));
      setStatus(
        `Completed: stages=${result.stages.join(" -> ")}; ingested=${result.discovery.ingested_count}; run=${result.runId}`
      );
      router.push(`/run-status?runId=${result.runId}`);
    } catch (caught) {
      setStepState((state) => transitionOrStay(state, "error"));
      setStatus(stateLabel("error"));
      setError(`Guided flow failed: ${String(caught)}. Check discovery settings and run configuration.`);
    } finally {
      setIsGuidedRunning(false);
    }
  }

  return (
    <main>
      <h1>Upload Documents</h1>
      <nav>
        <Link href="/company">Back to Company</Link>
      </nav>
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          await runUpload(form);
        }}
      >
        <label>
          Document Title
          <input value={title} onChange={(event) => setTitle(event.target.value)} required />
        </label>
        <label>
          Select File
          <input name="file" type="file" accept=".pdf,application/pdf" required />
        </label>
        <button type="submit" disabled={isUploading}>
          {isUploading ? "Uploading..." : "Upload"}
        </button>
      </form>
      <button type="button" onClick={runAutoDiscovery} disabled={isAutoDiscovering}>
        {isAutoDiscovering ? "Discovering..." : "Auto-Find ESG Documents"}
      </button>
      <button type="button" onClick={runGuidedFlow} disabled={isGuidedRunning}>
        {isGuidedRunning ? "Running Guided Flow..." : "Auto-Find + Start Run"}
      </button>
      <p>{status}</p>
      <p>Step Key: {stepState}</p>
      {error ? (
        <div className="panel">
          <p>{error}</p>
          <p>Retry upload after fixing the issue.</p>
        </div>
      ) : null}
      <p>
        Continue to <Link href="/run-config">Run Configuration</Link>.
      </p>
    </main>
  );
}
