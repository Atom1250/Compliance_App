"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { configureRun, fetchLLMHealth, LLMHealthResponse } from "../../lib/api-client";
import { stateLabel, StepState, transitionOrStay } from "../../lib/flow-state";

export default function RunConfigPage() {
  const router = useRouter();
  const [bundlePreset, setBundlePreset] = useState<
    "eu_pre_2026" | "eu_post_2026" | "eu_with_jurisdiction_overlay"
  >("eu_post_2026");
  const [bundleVersion, setBundleVersion] = useState("2026.01");
  const [jurisdiction, setJurisdiction] = useState("NO");
  const [llmProvider, setLlmProvider] = useState<
    "deterministic_fallback" | "local_lm_studio" | "openai_cloud"
  >(
    "deterministic_fallback"
  );
  const [llmHealth, setLlmHealth] = useState<LLMHealthResponse | null>(null);
  const [llmHealthStatus, setLlmHealthStatus] = useState("Checking local LLM config...");
  const [runError, setRunError] = useState("");
  const [stepState, setStepState] = useState<StepState>("idle");
  const [runStatusLabel, setRunStatusLabel] = useState(stateLabel("idle"));
  const [isStarting, setIsStarting] = useState(false);

  async function startRun() {
    setStepState((state) => transitionOrStay(state, "validating"));
    setRunStatusLabel(stateLabel("validating"));
    const companyId = Number(localStorage.getItem("company_id") ?? "0");
    if (!companyId) {
      setRunError("Company ID is missing. Complete Company Setup first.");
      setStepState((state) => transitionOrStay(state, "error"));
      setRunStatusLabel(stateLabel("error"));
      return;
    }
    setRunError("");
    setIsStarting(true);
    setStepState((state) => transitionOrStay(state, "submitting"));
    setRunStatusLabel(stateLabel("submitting"));
    try {
      const configured = await configureRun({
        companyId,
        bundleVersion,
        bundlePreset,
        compilerMode: bundlePreset === "eu_with_jurisdiction_overlay" ? "registry" : "legacy",
        jurisdictions:
          bundlePreset === "eu_with_jurisdiction_overlay" ? ["EU", jurisdiction] : ["EU"],
        regimes: ["CSRD_ESRS"],
        llmProvider
      });
      if (!configured?.runId) {
        throw new Error("Missing run id in API response.");
      }
      localStorage.setItem("run_id", String(configured.runId));
      setStepState((state) => transitionOrStay(state, "success"));
      setRunStatusLabel(`Completed: run ${configured.runId} started.`);
      router.push(`/run-status?runId=${configured.runId}`);
    } catch (caught) {
      setRunError(`Run start failed: ${String(caught)}. Verify provider credentials and try again.`);
      setStepState((state) => transitionOrStay(state, "error"));
      setRunStatusLabel(stateLabel("error"));
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
      setBundlePreset("eu_pre_2026");
      setBundleVersion("2024.01");
      return;
    }
    setBundlePreset("eu_post_2026");
    setBundleVersion("2026.01");
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
          Bundle
          <select
            value={bundlePreset}
            onChange={(event) =>
              setBundlePreset(
                event.target.value as
                  | "eu_pre_2026"
                  | "eu_post_2026"
                  | "eu_with_jurisdiction_overlay"
              )
            }
          >
            <option value="eu_pre_2026">EU regs pre-2026</option>
            <option value="eu_post_2026">EU regs post-2026 update</option>
            <option value="eu_with_jurisdiction_overlay">EU + jurisdiction overlay</option>
          </select>
        </label>
        <label>
          Bundle Version
          <select value={bundleVersion} onChange={(event) => setBundleVersion(event.target.value)}>
            <option value="2026.01">2026.01 (current CSRD/ESRS)</option>
            <option value="2024.01">2024.01 (legacy/pre-2026 test)</option>
          </select>
        </label>
        {bundlePreset === "eu_with_jurisdiction_overlay" ? (
          <label>
            Jurisdiction Overlay
            <select value={jurisdiction} onChange={(event) => setJurisdiction(event.target.value)}>
              <option value="NO">Norway (NO)</option>
              <option value="ES">Spain (ES)</option>
              <option value="FR">France (FR)</option>
              <option value="DE">Germany (DE)</option>
              <option value="NL">Netherlands (NL)</option>
              <option value="UK">United Kingdom (UK)</option>
            </select>
          </label>
        ) : null}
        <p>
          Bundle maps to concrete <code>bundle_id</code> + <code>bundle_version</code> at run start.
          Version pins the exact rules release used for deterministic outputs.
        </p>
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
          <p>Step Key: {stepState}</p>
          <p>Step State: {runStatusLabel}</p>
          <p>{runError}</p>
          <button type="button" onClick={startRun} disabled={isStarting}>
            Retry Start Run
          </button>
        </div>
      ) : (
        <div>
          <p>Step Key: {stepState}</p>
          <p>Step State: {runStatusLabel}</p>
        </div>
      )}
    </main>
  );
}
