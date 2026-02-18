"use client";

import Link from "next/link";
import { useState } from "react";

import { uploadDocument } from "../../lib/api-client";

export default function UploadPage() {
  const [status, setStatus] = useState("Idle");

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
          const file = form.get("file");
          const companyId = Number(localStorage.getItem("company_id") ?? "0");
          if (!(file instanceof File) || !companyId) {
            setStatus("Missing file or company id.");
            return;
          }
          try {
            const uploaded = await uploadDocument({ companyId, file });
            setStatus(uploaded?.documentId ? `Uploaded document ${uploaded.documentId}` : "Upload complete");
          } catch (error) {
            setStatus(`Upload API unavailable. Demo mode continues. (${String(error)})`);
          }
        }}
      >
        <label>
          Select File
          <input name="file" type="file" accept=".pdf,.docx" required />
        </label>
        <button type="submit">Upload</button>
      </form>
      <p>{status}</p>
      <p>
        Continue to <Link href="/run-config">Run Configuration</Link>.
      </p>
    </main>
  );
}
