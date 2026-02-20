export type CompanySetupPayload = {
  name: string;
  employees?: number;
  turnover?: number;
  listedStatus?: boolean;
  reportingYear?: number;
  reportingYearStart?: number;
  reportingYearEnd?: number;
};

export type UploadPayload = {
  companyId: number;
  file: File;
  title?: string;
};

export type RunConfigPayload = {
  companyId: number;
  bundlePreset?: "eu_pre_2026" | "eu_post_2026" | "eu_with_jurisdiction_overlay";
  bundleId?: string;
  bundleVersion?: string;
  jurisdictions?: string[];
  regimes?: string[];
  compilerMode?: "legacy" | "registry";
  llmProvider: "deterministic_fallback" | "local_lm_studio" | "openai_cloud";
};

export type LLMHealthResponse = {
  provider: string;
  base_url: string;
  model: string;
  reachable: boolean | null;
  detail: string;
};

export type AutoDiscoverResponse = {
  company_id: number;
  candidates_considered: number;
  raw_candidates: number;
  ingested_count: number;
  ingested_documents: Array<{
    document_id: number;
    title: string;
    source_url: string;
    duplicate: boolean;
  }>;
  skipped: Array<{
    source_url: string;
    reason: string;
  }>;
};

export type GuidedRunFlowResult = {
  runId: number | null;
  stages: string[];
  discovery: AutoDiscoverResponse;
};

export type RunDiagnosticsResponse = {
  run_id: number;
  company_id: number;
  status: string;
  compiler_mode: string;
  llm_provider: string | null;
  cache_hit: boolean | null;
  manifest_present: boolean;
  direct_document_count: number;
  scoped_document_count: number;
  shared_document_count: number;
  chunk_count: number;
  required_datapoints_count: number | null;
  required_datapoints_error: string | null;
  assessment_count: number;
  assessment_status_counts: Record<string, number>;
  retrieval_hit_count: number;
  diagnostics_count: number;
  diagnostics_failures: number;
  integrity_warning: boolean;
  latest_failure_reason: string | null;
  stage_outcomes: Record<string, boolean>;
  stage_event_counts: Record<string, number>;
};

function resolveBundleIdVersion(payload: RunConfigPayload): { bundleId: string; bundleVersion: string } {
  if (payload.bundleId && payload.bundleVersion) {
    return { bundleId: payload.bundleId, bundleVersion: payload.bundleVersion };
  }
  const preset = payload.bundlePreset ?? "eu_post_2026";
  if (preset === "eu_pre_2026") {
    return { bundleId: "esrs_mini", bundleVersion: payload.bundleVersion ?? "2024.01" };
  }
  if (preset === "eu_with_jurisdiction_overlay") {
    return { bundleId: "esrs_mini", bundleVersion: payload.bundleVersion ?? "2026.01" };
  }
  return { bundleId: "esrs_mini", bundleVersion: payload.bundleVersion ?? "2026.01" };
}

export type EvidencePackPreviewResponse = {
  run_id: number;
  entries: string[];
  pack_files: Array<{
    path: string;
    sha256: string;
  }>;
  pack_file_count: number;
  document_count: number;
  has_assessments: boolean;
  has_evidence: boolean;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";
const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID ?? "";

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }
  if (TENANT_ID) {
    headers["X-Tenant-ID"] = TENANT_ID;
  }
  return headers;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API ${path} failed (${response.status}): ${detail}`);
  }

  return (await response.json()) as T;
}

export async function createCompany(payload: CompanySetupPayload): Promise<{ id: number } | null> {
  const response = await request<{
    id: number;
  }>("/companies", {
    method: "POST",
    body: JSON.stringify({
      name: payload.name,
      employees: payload.employees,
      turnover: payload.turnover,
      listed_status: payload.listedStatus,
      reporting_year: payload.reportingYear,
      reporting_year_start: payload.reportingYearStart,
      reporting_year_end: payload.reportingYearEnd
    })
  });
  return { id: response.id };
}

export async function uploadDocument(payload: UploadPayload): Promise<{ documentId: number } | null> {
  const form = new FormData();
  form.append("company_id", String(payload.companyId));
  form.append("title", payload.title ?? payload.file.name ?? "Uploaded Document");
  form.append("file", payload.file);

  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: form
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API /documents/upload failed (${response.status}): ${detail}`);
  }

  const json = (await response.json()) as { document_id: number };
  return { documentId: json.document_id };
}

export async function autoDiscoverDocuments(
  companyId: number,
  maxDocuments = 3
): Promise<AutoDiscoverResponse> {
  return request<AutoDiscoverResponse>("/documents/auto-discover", {
    method: "POST",
    body: JSON.stringify({
      company_id: companyId,
      max_documents: maxDocuments
    })
  });
}

export async function configureRun(payload: RunConfigPayload): Promise<{ runId: number } | null> {
  const resolved = resolveBundleIdVersion(payload);
  const created = await request<{ run_id: number; status: string }>("/runs", {
    method: "POST",
    body: JSON.stringify({
      company_id: payload.companyId
    })
  });

  await request<{ run_id: number; status: string; assessment_count: number }>(
    `/runs/${created.run_id}/execute`,
    {
      method: "POST",
      body: JSON.stringify({
        bundle_id: resolved.bundleId,
        bundle_version: resolved.bundleVersion,
        llm_provider: payload.llmProvider,
        compiler_mode: payload.compilerMode,
        regulatory_jurisdictions: payload.jurisdictions,
        regulatory_regimes: payload.regimes
      })
    }
  );

  return { runId: created.run_id };
}

export async function orchestrateDiscoveryAndRun(
  payload: RunConfigPayload & { maxDocuments?: number }
): Promise<GuidedRunFlowResult> {
  const stages: string[] = [];

  stages.push("discovery.started");
  const discovery = await autoDiscoverDocuments(payload.companyId, payload.maxDocuments ?? 3);
  stages.push("discovery.completed");

  stages.push("run.configure.started");
  const configured = await configureRun(payload);
  stages.push("run.configure.completed");

  return {
    runId: configured?.runId ?? null,
    stages,
    discovery
  };
}

export async function fetchRunStatus(runId: number): Promise<{ status: string }> {
  return request<{ status: string }>(`/runs/${runId}/status`);
}

export async function fetchRunDiagnostics(runId: number): Promise<RunDiagnosticsResponse> {
  return request<RunDiagnosticsResponse>(`/runs/${runId}/diagnostics`);
}

export async function rerunWithoutCache(
  runId: number,
  llmProvider?: "deterministic_fallback" | "local_lm_studio" | "openai_cloud"
): Promise<{ source_run_id: number; run_id: number; status: string }> {
  return request<{ source_run_id: number; run_id: number; status: string }>(
    `/runs/${runId}/rerun`,
    {
      method: "POST",
      body: JSON.stringify({
        bypass_cache: true,
        llm_provider: llmProvider
      })
    }
  );
}

export async function fetchReportHtml(runId: number): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/runs/${runId}/report`, {
    method: "GET",
    headers: authHeaders()
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API /runs/${runId}/report failed (${response.status}): ${detail}`);
  }
  return response.text();
}

export async function fetchEvidencePackPreview(
  runId: number
): Promise<EvidencePackPreviewResponse> {
  return request<EvidencePackPreviewResponse>(`/runs/${runId}/evidence-pack-preview`);
}

export function buildEvidencePackDownloadUrl(runId: number): string {
  return `${API_BASE_URL}/runs/${runId}/evidence-pack`;
}

async function downloadWithAuth(path: string, filename: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    headers: authHeaders()
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API ${path} failed (${response.status}): ${detail}`);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function downloadRunReport(runId: number): Promise<void> {
  await downloadWithAuth(`/runs/${runId}/report`, `run-${runId}-report.html`);
}

export async function downloadEvidencePack(runId: number): Promise<void> {
  await downloadWithAuth(`/runs/${runId}/evidence-pack`, `run-${runId}-evidence-pack.zip`);
}

export async function fetchLLMHealth(
  provider: "local_lm_studio" | "openai_cloud",
  probe = false
): Promise<LLMHealthResponse> {
  const params = new URLSearchParams({ provider });
  if (probe) {
    params.set("probe", "true");
  }
  const query = `?${params.toString()}`;
  return request<LLMHealthResponse>(`/llm-health${query}`);
}
