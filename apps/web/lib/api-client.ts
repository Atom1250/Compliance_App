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
  bundleId: string;
  bundleVersion: string;
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

export type EvidencePackPreviewResponse = {
  run_id: number;
  entries: string[];
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
        bundle_id: payload.bundleId,
        bundle_version: payload.bundleVersion,
        llm_provider: payload.llmProvider
      })
    }
  );

  return { runId: created.run_id };
}

export async function fetchRunStatus(runId: number): Promise<{ status: string }> {
  return request<{ status: string }>(`/runs/${runId}/status`);
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
