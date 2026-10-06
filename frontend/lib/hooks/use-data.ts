"use client";

import { useEffect } from "react";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getDataSource } from "@/lib/api";
import type { CreateInvestigationInput, IngestDocumentInput, RagSearchInput, WarehouseDocumentsParams } from "@/lib/api/types";
import type { Investigation, ReviewAction } from "@/lib/types";

export const qk = {
  investigations: ["investigations"] as const,
  investigation: (id: string) => ["investigation", id] as const,
  timeline: (id: string) => ["timeline", id] as const,
  evidence: (id: string) => ["evidence", id] as const,
  dossier: (id: string) => ["dossier", id] as const,
  audit: (id: string) => ["audit", id] as const,
  gaps: (id: string) => ["gaps", id] as const,
  drugLookup: (name: string) => ["drug-lookup", name] as const,
  warehouseOverview: ["warehouse-overview"] as const,
  warehouseDocuments: (params: WarehouseDocumentsParams) => ["warehouse-documents", params] as const,
  warehouseDocument: (docId: string) => ["warehouse-document", docId] as const,
  ingestionEvents: ["ingestion-events"] as const,
};

/**
 * Danh sách cuộc điều tra.
 *
 * Có nhịp làm mới vì dashboard, hàng chờ duyệt và số đếm ở thanh điều hướng đều đọc từ đây;
 * chỉ làm mới khi tab đang hiện để không gọi backend vô ích.
 */
export function useInvestigations(enabled = true) {
  return useQuery({
    queryKey: qk.investigations,
    enabled,
    queryFn: () => getDataSource().listInvestigations(),
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
  });
}

export function useInvestigation(id: string) {
  const client = useQueryClient();
  const result = useQuery({
    queryKey: qk.investigation(id),
    queryFn: () => getDataSource().getInvestigation(id),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const status = query.state.data?.runStatus;
      return status === "running" || status === "queued" ? 2000 : false;
    },
  });
  const version = result.data?.version;
  useEffect(() => {
    if (version == null) return;
    for (const key of [qk.evidence(id), qk.gaps(id), qk.dossier(id), qk.timeline(id), qk.audit(id)]) {
      void client.invalidateQueries({ queryKey: key });
    }
  }, [id, version, client]);
  return result;
}

/**
 * Dòng sự kiện của cuộc điều tra.
 *
 * Backend không đánh dấu bước "đang chạy" trong `/events`, nên nhịp làm mới bám theo trạng thái
 * chạy của cuộc điều tra (đang chạy / đang xếp hàng) do `useInvestigation` cung cấp.
 */
export function useTimeline(id: string, active = false) {
  return useQuery({
    queryKey: qk.timeline(id),
    queryFn: () => getDataSource().getTimeline(id),
    enabled: Boolean(id),
    refetchInterval: active ? 2000 : false,
  });
}

export function useEvidence(id: string) {
  return useQuery({ queryKey: qk.evidence(id), queryFn: () => getDataSource().getEvidence(id), enabled: Boolean(id) });
}

export function useDossier(id: string) {
  return useQuery({ queryKey: qk.dossier(id), queryFn: () => getDataSource().getDossier(id), enabled: Boolean(id) });
}

export function useAudit(id: string) {
  return useQuery({ queryKey: qk.audit(id), queryFn: () => getDataSource().getAudit(id), enabled: Boolean(id) });
}

export function useGaps(id: string) {
  return useQuery({ queryKey: qk.gaps(id), queryFn: () => getDataSource().getGaps(id), enabled: Boolean(id) });
}

export function useCreateInvestigation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ input, key }: { input: CreateInvestigationInput; key: string }) => getDataSource().createInvestigation(input, key),
    onSuccess: () => client.invalidateQueries({ queryKey: qk.investigations }),
  });
}

export function useReviewAction(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (action: ReviewAction) => getDataSource().submitReview(id, action),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: qk.investigation(id) });
      void client.invalidateQueries({ queryKey: qk.audit(id) });
      void client.invalidateQueries({ queryKey: qk.dossier(id) });
      void client.invalidateQueries({ queryKey: qk.timeline(id) });
      void client.invalidateQueries({ queryKey: qk.evidence(id) });
      void client.invalidateQueries({ queryKey: qk.gaps(id) });
      void client.invalidateQueries({ queryKey: qk.investigations });
    },
  });
}

export function useContinueRun(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => getDataSource().continueRun(id, client.getQueryData<Investigation>(qk.investigation(id))?.version),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: qk.investigation(id) });
      void client.invalidateQueries({ queryKey: qk.timeline(id) });
    },
  });
}

export function useExportDossier(id: string) {
  return useMutation({ mutationFn: () => getDataSource().exportDossier(id) });
}

export function useCancelRun(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => getDataSource().cancelRun(id),
    onSuccess: () => {
      for (const key of [qk.investigation(id), qk.timeline(id), qk.dossier(id), qk.investigations]) void client.invalidateQueries({ queryKey: key });
    },
  });
}

// -----------------------------------------------------------------------------------------
// Kho bằng chứng (ELT + Postgres + ChromaDB)
// -----------------------------------------------------------------------------------------

/** Tra thuốc theo tên; chỉ gọi khi đã có từ khoá (ít nhất 3 ký tự ở các ô gợi ý). */
export function useDrugLookup(name: string, enabled = true) {
  const query = name.trim();
  return useQuery({
    queryKey: qk.drugLookup(query),
    queryFn: () => getDataSource().lookupDrug(query),
    enabled: enabled && query.length >= 2,
    staleTime: 30_000,
    retry: false,
  });
}

export function useWarehouseOverview(enabled = true) {
  return useQuery({
    queryKey: qk.warehouseOverview,
    queryFn: () => getDataSource().warehouseOverview(),
    enabled,
    retry: false,
  });
}

export function useWarehouseDocuments(params: WarehouseDocumentsParams = {}, enabled = true) {
  return useQuery({
    queryKey: qk.warehouseDocuments(params),
    queryFn: () => getDataSource().warehouseDocuments(params),
    enabled,
    retry: false,
  });
}

export function useWarehouseDocument(docId: string, previewChars?: number) {
  return useQuery({
    queryKey: qk.warehouseDocument(docId),
    queryFn: () => getDataSource().warehouseDocument(docId, previewChars),
    enabled: Boolean(docId),
    retry: false,
  });
}

/** Tìm ngữ nghĩa trên kho; chạy theo yêu cầu (mutation) để không gọi backend khi chưa bấm. */
export function useRagSearch() {
  return useMutation({ mutationFn: (input: RagSearchInput) => getDataSource().ragSearch(input) });
}

export function useIngestionEvents(limit?: number) {
  return useQuery({
    queryKey: qk.ingestionEvents,
    queryFn: () => getDataSource().ingestionEvents(limit),
    refetchInterval: 10_000,
    retry: false,
  });
}

export function useIngestDocument() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: IngestDocumentInput) => getDataSource().ingestDocument(input),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: qk.ingestionEvents });
      void client.invalidateQueries({ queryKey: qk.warehouseOverview });
      void client.invalidateQueries({ queryKey: ["warehouse-documents"] });
    },
  });
}
