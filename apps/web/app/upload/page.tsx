"use client";

import Link from "next/link";
import { useState } from "react";

import { autoDiscoverDocuments, uploadDocument } from "../../lib/api-client";
import { stateLabel, StepState, transitionOrStay } from "../../lib/flow-state";

export default function UploadPage() {
  const [stepState, setStepState] = useState<StepState>("idle");
  const [status, setStatus] = useState(stateLabel("idle"));
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isAutoDiscovering, setIsAutoDiscovering] = useState(false);
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
