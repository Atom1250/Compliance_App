# ADR-0001: Architecture and Determinism Principles

Date: 2026-02-17
Status: Accepted

## Context
We are building an application to help EU clients assess compliance with CSRD and ESRS, and where relevant map disclosures to green finance standards (ICMA Green Bond Principles and EU Green Bond Standard / EuGB). The system must produce consistent, repeatable outputs with audit-grade citations and evidence packs.

The core challenge is balancing:
- depth of compliance coverage (datapoint-level)
- speed and low token usage
- deterministic outputs suitable for assurance workflows

## Decision
We adopt a requirements-first, datapoint-native compliance engine with evidence-gated extraction and reproducible run manifests.

Key decisions:
1. **Requirements-first**: Requirements are stored as versioned bundles (repo-controlled), imported into DB. The LLM never invents requirements.
2. **Datapoint-native**: Assessments are performed at datapoint granularity using a strict schema:
   - status: Present / Partial / Absent / NA
   - evidence IDs required for Present/Partial
   - optional extracted value, units, period
3. **Evidence-gated**: "Present" cannot be emitted without supporting evidence references.
4. **Deterministic pipeline**:
   - Deterministic parsing and chunking
   - Stable chunk IDs derived from doc hash + page + offsets
   - Hybrid retrieval (FTS + vector) with deterministic tie-breaks
   - LLM calls configured for deterministic output (temperature=0) and schema-only JSON
5. **Run reproducibility**:
   - Every run stores a manifest including document hashes, bundle versions, retrieval params, model + prompt hash, and git SHA.
   - Run-hash caching guarantees same inputs return identical outputs.
6. **Storage**:
   - Postgres as system-of-record
   - pgvector for embeddings
   - S3-compatible storage for original documents and exported evidence packs

## Consequences
Pros:
- High consistency and auditability
- Easier regression testing and golden run harness
- Reduced LLM token usage via RAG and structured extraction

Cons:
- Requires curated requirements bundles (content workstream)
- More engineering upfront vs ad-hoc LLM prompting
- Needs robust deterministic parsing and indexing

## Alternatives Considered
1. Prompt-only analysis (rejected): too variable, lacks evidence discipline and repeatability.
2. LLM-based chunking/indexing (rejected): non-deterministic and hard to regression test.
3. Dedicated vector DB from day 1 (deferred): pgvector is sufficient for MVP; may revisit for scale.

## Follow-ups
- ADR for DB schema once finalized
- ADR for worker/job system selection
- ADR for PDF extraction strategy
