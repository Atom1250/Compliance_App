# NotebookLM Monitoring Checklist

## Scope
NotebookLM is workflow-only. Monitoring focuses on reliability and safe degradation.

## Signals
- Error rate (`NotebookLMMCPError` count / total requests)
- p95 latency (ms) for research query endpoint/CLI path
- Cache hit ratio (`regulatory_research_cache` hits vs misses)
- Citation validation failures (strict-mode rejects)

## Alert guidance
- Error rate > 10% for 15 min: investigate sidecar and auth session.
- p95 latency > 10s for 15 min: investigate MCP health/network.
- Cache hit ratio < 20% with repeated workloads: review request normalization.

## Dashboards/queries
- Track research request counts by `provider` and `status`.
- Track `regulatory_research_cache.status` distribution.
- Track note persistence volume in `regulatory_requirement_research_notes`.
