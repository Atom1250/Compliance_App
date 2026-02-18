"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { configureRun, fetchLLMHealth, LLMHealthResponse } from "../../lib/api-client";

export default function RunConfigPage() {
  const router = useRouter();
  const [bundleId, setBundleId] = useState("esrs_mini");
  const [bundleVersion, setBundleVersion] = useState("2026.01");
  const [llmProvider, setLlmProvider] = useState<
    "deterministic_fallback" | "local_lm_studio" | "openai_cloud"
  >(
    "deterministic_fallback"
  );
  const [llmHealth, setLlmHealth] = useState<LLMHealthResponse | null>(null);
  const [llmHealthStatus, setLlmHealthStatus] = useState("Checking local LLM config...");
  const [runError, setRunError] = useState("");
  const [isStarting, setIsStarting] = useState(false);

  async function startRun() {
    const companyId = Number(localStorage.getItem("company_id") ?? "0");
    if (!companyId) {
      setRunError("Company ID is missing. Complete Company Setup first.");
      return;
    }
    setRunError("");
    setIsStarting(true);
    try {
      const configured = await configureRun({
        companyId,
        bundleId,
        bundleVersion,
        llmProvider
      });
      if (!configured?.runId) {
        throw new Error("Missing run id in API response.");
      }
      localStorage.setItem("run_id", String(configured.runId));
      router.push(`/run-status?runId=${configured.runId}`);
    } catch (caught) {
      setRunError(`Run start failed: ${String(caught)}`);
    } finally {
      setIsStarting(false);
    }
  }

  useEffect(() => {
    let isMounted = true;

    async function loadHealth() {
      try {
        const provider = llmProvider === "openai_cloud" ? "openai_cloud" : "local_lm_studio";
        const response = await fetchLLMHealth(provider, false);
        if (isMounted) {
          setLlmHealth(response);
          setLlmHealthStatus("LLM config loaded.");
        }
      } catch (error) {
        if (isMounted) {
          setLlmHealth(null);
          setLlmHealthStatus(`Unable to read /llm-health (${String(error)}).`);
        }
      }
    }

    void loadHealth();
    return () => {
      isMounted = false;
    };
  }, [llmProvider]);

  useEffect(() => {
    const endYear = Number(window.localStorage.getItem("company_reporting_year_end") ?? "0");
    if (Number.isFinite(endYear) && endYear > 0 && endYear < 2026) {
      setBundleVersion("2024.01");
    }
  }, []);

  return (
    <main>
      <h1>Run Configuration</h1>
      <nav>
        <Link href="/upload">Back to Upload</Link>
      </nav>
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          await startRun();
        }}
      >
        <label>
          Bundle ID
          <input value={bundleId} onChange={(event) => setBundleId(event.target.value)} required />
        </label>
        <label>
          Bundle Version
          <select value={bundleVersion} onChange={(event) => setBundleVersion(event.target.value)}>
            <option value="2026.01">2026.01 (current CSRD/ESRS)</option>
            <option value="2024.01">2024.01 (legacy/pre-2026 test)</option>
          </select>
        </label>
        <label>
          Execution Provider
          <select
            value={llmProvider}
            onChange={(event) =>
              setLlmProvider(
                event.target.value as
                  | "deterministic_fallback"
                  | "local_lm_studio"
                  | "openai_cloud"
              )
            }
          >
            <option value="deterministic_fallback">deterministic_fallback</option>
            <option value="local_lm_studio">local_lm_studio</option>
            <option value="openai_cloud">openai_cloud</option>
          </select>
        </label>
        <div className="panel">
          <p>LLM Health</p>
          <p>Status: {llmHealthStatus}</p>
          <p>Base URL: {llmHealth?.base_url ?? "N/A"}</p>
          <p>Model: {llmHealth?.model ?? "N/A"}</p>
          <p>Reachable: {String(llmHealth?.reachable ?? "unknown")}</p>
          <p>Detail: {llmHealth?.detail ?? "N/A"}</p>
          <button
            type="button"
            onClick={async () => {
              const provider = llmProvider === "openai_cloud" ? "openai_cloud" : "local_lm_studio";
              setLlmHealthStatus(`Probing ${provider}...`);
              try {
                const probed = await fetchLLMHealth(provider, true);
                setLlmHealth(probed);
                setLlmHealthStatus("Probe completed.");
              } catch (error) {
                setLlmHealth(null);
                setLlmHealthStatus(`Probe failed (${String(error)}).`);
              }
            }}
          >
            Run LLM Probe
          </button>
        </div>
        <button type="submit" disabled={isStarting}>
          {isStarting ? "Starting..." : "Start Run"}
        </button>
      </form>
      {runError ? (
        <div className="panel">
          <p>{runError}</p>
          <button type="button" onClick={startRun} disabled={isStarting}>
            Retry Start Run
          </button>
        </div>
      ) : null}
    </main>
  );
}
