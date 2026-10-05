// Generated from docs/openapi.json (SHA-256 eca8d6fd7ed15d3ea3c1a5902d006917b6d5563d3c5d735e90d014d16ee732fc). Do not edit.
export type Body_append_sources_api_v1_cases__case_id__sources_post = { "expected_revision": number; "files": Array<string>; "manifest": string; };
export type Body_import_case_api_v1_cases_import_post = { "files": Array<string>; "manifest": string; };
export type CancelResponse = { "cancelled": boolean; "investigation_id": string; "message"?: string; "run_status": RunStatus; };
export type CheckpointKind = "normalization" | "assessment" | "dossier";
export type ClaimInput = { "claim_text": string; "config"?: InvestigationConfig | null; "dose"?: string | null; "drug": string; "event": string; "population"?: string | null; "route"?: string | null; "time_window"?: string | null; };
export type ContinueRequest = { "expected_version"?: number | null; };
export type HTTPValidationError = { "detail"?: Array<ValidationError>; };
export type InvestigationConfig = { "max_documents"?: number; "max_steps"?: number; "sources"?: Array<string>; };
export type LoginRequest = { "password"?: string | null; "role"?: Role | null; "token"?: string | null; "username"?: string | null; };
export type ReviewAction = "approve" | "reject" | "edit_claim" | "edit_evidence" | "exclude_evidence" | "request_more";
export type ReviewRequest = { "action": ReviewAction; "checkpoint": CheckpointKind; "decision_id": string; "expected_version": number; "payload"?: Record<string, unknown>; "reason"?: string; "target_evidence_id"?: string | null; };
export type Role = "investigator" | "reviewer";
export type RunStatus = "queued" | "running" | "waiting_for_review" | "completed" | "cancelled" | "interrupted" | "failed";
export type ValidationError = { "ctx"?: Record<string, unknown>; "input"?: unknown; "loc": Array<string | number>; "msg": string; "type": string; };
