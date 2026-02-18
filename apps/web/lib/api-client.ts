export type CompanySetupPayload = {
  name: string;
  employees?: number;
  turnover?: number;
  listedStatus?: boolean;
  reportingYear?: number;
};

export type UploadPayload = {
  companyId: number;
  file: File;
};

export type RunConfigPayload = {
  companyId: number;
  bundleId: string;
  bundleVersion: string;
  greenFinanceEnabled: boolean;
  llmProvider: "deterministic_fallback" | "local_lm_studio";
};

export type LLMHealthResponse = {
  base_url: string;
  model: string;
  reachable: boolean | null;
  detail: string;
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
      reporting_year: payload.reportingYear
    })
  });
  return { id: response.id };
}

export async function uploadDocument(payload: UploadPayload): Promise<{ documentId: number } | null> {
  const form = new FormData();
  form.append("company_id", String(payload.companyId));
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

export async function fetchReportDownload(runId: number): Promise<{ url: string }> {
  return request<{ url: string }>(`/runs/${runId}/report`);
}

export function buildEvidencePackDownloadUrl(runId: number): string {
  return `${API_BASE_URL}/runs/${runId}/evidence-pack`;
}

export async function fetchLLMHealth(probe = false): Promise<LLMHealthResponse> {
  const query = probe ? "?probe=true" : "";
  return request<LLMHealthResponse>(`/llm-health${query}`);
}
