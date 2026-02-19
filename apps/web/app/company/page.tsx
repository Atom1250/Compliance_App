"use client";

import Link from "next/link";
import { useState } from "react";

import { createCompany } from "../../lib/api-client";
import { stateLabel, StepState, transitionOrStay } from "../../lib/flow-state";

export default function CompanySetupPage() {
  const [name, setName] = useState("Atom Climate Holdings");
  const [reportingYearStart, setReportingYearStart] = useState("2024");
  const [reportingYearEnd, setReportingYearEnd] = useState("2026");
  const [companyId, setCompanyId] = useState<number | null>(null);
  const [stepState, setStepState] = useState<StepState>("idle");
  const [status, setStatus] = useState(stateLabel("idle"));
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  async function saveCompany() {
    setStepState((state) => transitionOrStay(state, "validating"));
    setStatus(stateLabel("validating"));
    const startYear = Number(reportingYearStart);
    const endYear = Number(reportingYearEnd);
    if (!Number.isFinite(startYear) || !Number.isFinite(endYear) || startYear > endYear) {
      setStepState((state) => transitionOrStay(state, "error"));
      setStatus(stateLabel("error"));
      setError("Reporting year range is invalid. Ensure start year is less than or equal to end year.");
      return;
    }
    setIsSaving(true);
    setError("");
    setStepState((state) => transitionOrStay(state, "submitting"));
    setStatus(stateLabel("submitting"));
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
      setStepState((state) => transitionOrStay(state, "success"));
      setStatus(`Completed: company ${created.id} saved.`);
    } catch (caught) {
      setError(`Company setup failed: ${String(caught)}. Verify API URL/keys and retry.`);
      setStepState((state) => transitionOrStay(state, "error"));
      setStatus(stateLabel("error"));
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
      <p>Step Key: {stepState}</p>
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
