"use client";

import Link from "next/link";
import { useState } from "react";

import { uploadDocument } from "../../lib/api-client";

export default function UploadPage() {
  const [status, setStatus] = useState("Idle");
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  async function runUpload(form: FormData) {
    const file = form.get("file");
    const companyId = Number(localStorage.getItem("company_id") ?? "0");
    if (!(file instanceof File) || !companyId) {
      setStatus("Upload blocked.");
      setError("Missing file or company id.");
      return;
    }
    setIsUploading(true);
    setError("");
    setStatus("Uploading...");
    try {
      const uploaded = await uploadDocument({ companyId, file });
      if (!uploaded?.documentId) {
        throw new Error("Missing document id in API response.");
      }
      setStatus(`Uploaded document ${uploaded.documentId}`);
    } catch (caught) {
      setStatus("Upload failed.");
      setError(`Upload failed: ${String(caught)}`);
    } finally {
      setIsUploading(false);
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
          Select File
          <input name="file" type="file" accept=".pdf,.docx" required />
        </label>
        <button type="submit" disabled={isUploading}>
          {isUploading ? "Uploading..." : "Upload"}
        </button>
      </form>
      <p>{status}</p>
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
