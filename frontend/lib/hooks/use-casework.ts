"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getCaseworkSource } from "@/lib/api/casework";
import type { IntakeCreateInput, WorkflowAggregate, WorkItemSummary } from "@/lib/api/casework-types";

export const caseworkKeys = {
  list: (actor = "session") => ["casework", actor, "list"] as const,
  workflow: (id: string, actor = "session") => ["casework", actor, id, "workflow"] as const,
  draft: (id: string, actor = "session") => ["casework", actor, id, "editor-draft"] as const,
  events: (id: string, actor = "session") => ["casework", actor, id, "events"] as const,
};

const active = (aggregate?: WorkflowAggregate) => ["queued", "running"].includes(aggregate?.work_item.run_status ?? "");
const invalidate = (client: ReturnType<typeof useQueryClient>, id?: string) => {
  void client.invalidateQueries({ queryKey: caseworkKeys.list() });
  if (id) { void client.invalidateQueries({ queryKey: caseworkKeys.workflow(id) }); void client.invalidateQueries({ queryKey: caseworkKeys.draft(id) }); }
};

export function useWorkItems() {
  return useQuery({ queryKey: caseworkKeys.list(), queryFn: () => getCaseworkSource().listWorkItems(), refetchInterval: 10_000 });
}
export function useWorkflow(id: string) {
  return useQuery({ queryKey: caseworkKeys.workflow(id), queryFn: () => getCaseworkSource().getWorkflow(id), enabled: Boolean(id), refetchInterval: (query) => active(query.state.data) ? 2_500 : false });
}
export function useCreateIntake() {
  const client = useQueryClient();
  return useMutation({ mutationFn: ({ input, idempotencyKey }: { input: IntakeCreateInput; idempotencyKey: string }) => getCaseworkSource().createIntake(input, idempotencyKey), onSuccess: () => invalidate(client) });
}
export function useFieldUpdate(id: string) {
  const client = useQueryClient();
  return useMutation({ mutationFn: (input: Parameters<ReturnType<typeof getCaseworkSource>["patchFields"]>[1] extends never ? never : { expectedVersion: number; operations: Parameters<ReturnType<typeof getCaseworkSource>["patchFields"]>[2]; idempotencyKey: string }) => getCaseworkSource().patchFields(id, input.expectedVersion, input.operations, input.idempotencyKey), onSuccess: () => invalidate(client, id) });
}
export function useClarificationAnswer(id: string) {
  const client = useQueryClient();
  return useMutation({ mutationFn: (input: { expectedVersion: number; answers: Parameters<ReturnType<typeof getCaseworkSource>["answerClarifications"]>[2]; idempotencyKey: string }) => getCaseworkSource().answerClarifications(id, input.expectedVersion, input.answers, input.idempotencyKey), onSuccess: () => invalidate(client, id) });
}
export function useStartCaseworkRun(id: string) {
  const client = useQueryClient();
  return useMutation({ mutationFn: (input: { expectedVersion: number; purpose: "preliminary" | "scoped_analysis"; idempotencyKey: string }) => getCaseworkSource().startRun(id, input.expectedVersion, input.purpose, input.idempotencyKey), onSuccess: () => invalidate(client, id) });
}
export function useEditorDraft(id: string) {
  return useQuery({ queryKey: caseworkKeys.draft(id), queryFn: () => getCaseworkSource().getEditorDraft(id), enabled: Boolean(id) });
}
export function useSaveEditorDraft(id: string) {
  const client = useQueryClient();
  return useMutation({ mutationFn: (input: { base_versions: Record<string, number>; content: Record<string, string>; version?: number; idempotencyKey: string }) => getCaseworkSource().saveEditorDraft(id, input, input.idempotencyKey), onSuccess: () => invalidate(client, id) });
}
export function useReviewDecision(workItemId: string, responseId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { expected_version: number; expected_work_version: number; basis_hash: string; action: "approve" | "reject" | "changes_requested"; reason: string; idempotencyKey: string }) =>
      getCaseworkSource().reviewResponse(responseId, input, input.idempotencyKey),
    onSuccess: () => invalidate(client, workItemId),
  });
}
export function useCreateResponse(id: string) {
  const client = useQueryClient();
  return useMutation({ mutationFn: (input: { expected_version: number; expected_input_revision: number; sections: Record<string, string>; idempotencyKey: string }) => getCaseworkSource().createDraft(id, input, input.idempotencyKey), onSuccess: () => invalidate(client, id) });
}
export function useSubmitReview(id: string, responseId: string) {
  const client = useQueryClient();
  return useMutation({ mutationFn: (input: { expected_version: number; expected_work_version: number; basis_hash: string; idempotencyKey: string }) => getCaseworkSource().submitReview(responseId, input, input.idempotencyKey), onSuccess: () => invalidate(client, id) });
}
export function useApprovedExport(id: string) {
  return useMutation({ mutationFn: () => getCaseworkSource().exportApprovedResponse(id) });
}
export function useAdrReportability(id: string) {
  const client = useQueryClient();
  return useMutation({ mutationFn: (input: { expected_version: number; status: "not_assessed" | "needs_information" | "reportable" | "not_reportable"; reason?: string; policy_reference?: string; idempotencyKey: string }) => getCaseworkSource().setAdrReportability(id, input, input.idempotencyKey), onSuccess: () => invalidate(client, id) });
}
export function useAdrIntakePatch(id: string) {
  const client = useQueryClient();
  return useMutation({ mutationFn: (input: { expected_version: number; patch: Record<string, unknown>; reason?: string; idempotencyKey: string }) => getCaseworkSource().patchAdrIntake(id, input, input.idempotencyKey), onSuccess: () => invalidate(client, id) });
}
export function useCloseFollowUp(id: string) {
  const client = useQueryClient();
  return useMutation({ mutationFn: (input: { followUpId: string; expected_version: number; status: "done" | "cancelled"; resolution: string; idempotencyKey: string }) => getCaseworkSource().closeFollowUp(id, input.followUpId, input, input.idempotencyKey), onSuccess: () => invalidate(client, id) });
}
export function useCaseworkEvents(id: string) {
  return useQuery({ queryKey: caseworkKeys.events(id), queryFn: () => getCaseworkSource().getEvents(id), enabled: Boolean(id) });
}
export type CaseworkSummary = WorkItemSummary;
