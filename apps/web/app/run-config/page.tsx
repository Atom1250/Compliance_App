"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { configureRun } from "../../lib/api-client";

export default function RunConfigPage() {
  const router = useRouter();
  const [bundleId, setBundleId] = useState("esrs_mini");
  const [bundleVersion, setBundleVersion] = useState("2026.01");
  const [greenFinanceEnabled, setGreenFinanceEnabled] = useState(true);

  return (
    <main>
      <h1>Run Configuration</h1>
      <nav>
        <Link href="/upload">Back to Upload</Link>
      </nav>
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          const companyId = Number(localStorage.getItem("company_id") ?? "0");
          if (!companyId) {
            return;
          }
          const configured = await configureRun({
            companyId,
            bundleId,
            bundleVersion,
            greenFinanceEnabled
          });
          if (configured?.runId) {
            localStorage.setItem("run_id", String(configured.runId));
            router.push(`/run-status?runId=${configured.runId}`);
          }
        }}
      >
        <label>
          Bundle ID
          <input value={bundleId} onChange={(event) => setBundleId(event.target.value)} required />
        </label>
        <div className="row">
          <label>
            Bundle Version
            <input
              value={bundleVersion}
              onChange={(event) => setBundleVersion(event.target.value)}
              required
            />
          </label>
          <label>
            Green Finance Mode
            <select
              value={greenFinanceEnabled ? "enabled" : "disabled"}
              onChange={(event) => setGreenFinanceEnabled(event.target.value === "enabled")}
            >
              <option value="enabled">Enabled</option>
              <option value="disabled">Disabled</option>
            </select>
          </label>
        </div>
        <button type="submit">Start Run</button>
      </form>
    </main>
  );
}
