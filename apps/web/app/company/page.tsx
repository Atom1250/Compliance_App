"use client";

import Link from "next/link";
import { useState } from "react";

import { createCompany } from "../../lib/api-client";

export default function CompanySetupPage() {
  const [name, setName] = useState("Atom Climate Holdings");
  const [reportingYear, setReportingYear] = useState("2026");
  const [companyId, setCompanyId] = useState<number | null>(null);

  return (
    <main>
      <h1>Company Setup</h1>
      <nav>
        <Link href="/">Home</Link>
      </nav>
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          const created = await createCompany({
            name,
            reportingYear: Number(reportingYear),
            listedStatus: true
          });
          if (created?.id) {
            localStorage.setItem("company_id", String(created.id));
            setCompanyId(created.id);
          }
        }}
      >
        <label>
          Company Name
          <input value={name} onChange={(event) => setName(event.target.value)} required />
        </label>
        <label>
          Reporting Year
          <input
            type="number"
            value={reportingYear}
            onChange={(event) => setReportingYear(event.target.value)}
            required
          />
        </label>
        <button type="submit">Save Company</button>
      </form>
      {companyId ? (
        <p>
          Company created with id <strong>{companyId}</strong>. Continue to <Link href="/upload">Upload</Link>.
        </p>
      ) : null}
    </main>
  );
}
