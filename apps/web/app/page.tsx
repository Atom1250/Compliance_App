import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <h1>Compliance App Workflow</h1>
      <p>Run the full happy path from company setup to report download.</p>
      <nav>
        <Link href="/company">1. Company Setup</Link>
        <Link href="/upload">2. Upload Docs</Link>
        <Link href="/run-config">3. Run Config</Link>
        <Link href="/run-status">4. Run Status</Link>
        <Link href="/report">5. Report Download</Link>
      </nav>
      <div className="panel">
        <p>
          This UI is intentionally minimal and deterministic. It uses a shared API client and supports a
          complete local flow when backend endpoints are unavailable.
        </p>
      </div>
    </main>
  );
}
