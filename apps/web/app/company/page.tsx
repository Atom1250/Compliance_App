"use client";

import Link from "next/link";
import { useState } from "react";

import { createCompany } from "../../lib/api-client";

export default function CompanySetupPage() {
  const [name, setName] = useState("Atom Climate Holdings");
  const [reportingYearStart, setReportingYearStart] = useState("2024");
  const [reportingYearEnd, setReportingYearEnd] = useState("2026");
  const [companyId, setCompanyId] = useState<number | null>(null);
  const [status, setStatus] = useState("Idle");
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  async function saveCompany() {
    const startYear = Number(reportingYearStart);
    const endYear = Number(reportingYearEnd);
    if (!Number.isFinite(startYear) || !Number.isFinite(endYear) || startYear > endYear) {
      setStatus("Save failed.");
      setError("Reporting year range is invalid. Ensure start year is less than or equal to end year.");
      return;
    }
    setIsSaving(true);
    setError("");
    setStatus("Saving company...");
    try {
      const created = await createCompany({
        name,
        reportingYear: endYear,
        reportingYearStart: startYear,
        reportingYearEnd: endYear,
        listedStatus: true
      });
      if (!created?.id) {
        throw new Error("Missing company id in API response.");
      }
      localStorage.setItem("company_id", String(created.id));
      localStorage.setItem("company_name", name);
      localStorage.setItem("company_reporting_year", reportingYearEnd);
      localStorage.setItem("company_reporting_year_start", reportingYearStart);
      localStorage.setItem("company_reporting_year_end", reportingYearEnd);
      setCompanyId(created.id);
      setStatus(`Company ${created.id} saved.`);
    } catch (caught) {
      setError(`Company setup failed: ${String(caught)}`);
      setStatus("Save failed.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main>
      <h1>Company Setup</h1>
      <nav>
        <Link href="/">Home</Link>
      </nav>
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          await saveCompany();
        }}
      >
        <label>
          Company Name
          <input value={name} onChange={(event) => setName(event.target.value)} required />
        </label>
        <label>
          Reporting Year Start
          <input
            type="number"
            value={reportingYearStart}
            onChange={(event) => setReportingYearStart(event.target.value)}
            required
          />
        </label>
        <label>
          Reporting Year End
          <input
            type="number"
            value={reportingYearEnd}
            onChange={(event) => setReportingYearEnd(event.target.value)}
            required
          />
        </label>
        <button type="submit" disabled={isSaving}>
          {isSaving ? "Saving..." : "Save Company"}
        </button>
      </form>
      <p>{status}</p>
      {error ? (
        <div className="panel">
          <p>{error}</p>
          <button type="button" onClick={saveCompany} disabled={isSaving}>
            Retry Save
          </button>
        </div>
      ) : null}
      {companyId ? (
        <p>
          Company created with id <strong>{companyId}</strong>. Continue to <Link href="/upload">Upload</Link>.
        </p>
      ) : null}
    </main>
  );
}
