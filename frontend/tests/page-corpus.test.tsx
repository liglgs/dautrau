// @vitest-environment jsdom
import * as React from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AdminCorpusPage from "@/app/admin/corpus/page";
import type { WarehouseDocumentSummary, WarehouseDocumentsParams, WarehouseDocumentsResult, WarehouseOverview } from "@/lib/api/types";
import { useAppStore } from "@/lib/store/app-store";

/**
 * Bài kiểm thử ở mức trang cho `/admin/corpus` (tổng quan kho, bảng tài liệu, lọc, chỉ mục RAG).
 *
 * Hook dữ liệu bị thay bằng mock nên không có lời gọi mạng nào; môi trường jsdom chỉ bật cho tệp này.
 */

const state = vi.hoisted(() => ({
  overview: undefined as WarehouseOverview | undefined,
  documents: undefined as WarehouseDocumentsResult | undefined,
  params: [] as WarehouseDocumentsParams[],
}));

vi.mock("@/lib/hooks/use-data", () => ({
  useWarehouseOverview: (enabled: boolean) => ({ data: enabled ? state.overview : undefined, isLoading: false, error: null }),
  useWarehouseDocuments: (params: WarehouseDocumentsParams, enabled: boolean) => {
    state.params.push(params);
    return { data: enabled ? state.documents : undefined, isLoading: false, error: null };
  },
  useWarehouseDocument: () => ({ data: undefined, isLoading: false, error: null }),
}));

vi.mock("@/lib/api/real", () => ({
  SESSION_AUTH: false,
  request: () => {
    throw new Error("Bài kiểm thử trang không gọi mạng thật");
  },
  createApiSource: () => {
    throw new Error("Bài kiểm thử trang không dùng nguồn API thật");
  },
}));

const DOCUMENTS: WarehouseDocumentSummary[] = [
  {
    doc_id: "doc-pubmed-1",
    source: "pubmed",
    source_id: "pmid-1",
    version: 2,
    title: "Ibuprofen và xuất huyết tiêu hoá",
    source_url: "",
    quality_status: "keep",
    quality_flags: ["missing_abstract"],
    pair_id: "pair-1",
    retrieved_at: "2026-10-01T08:00:00Z",
  },
  {
    doc_id: "doc-dailymed-1",
    source: "dailymed",
    source_id: "setid-1",
    version: 1,
    title: "Nhãn Metformin",
    source_url: "",
    quality_status: "quarantine",
    quality_flags: [],
    pair_id: null,
    retrieved_at: "2026-10-02T08:00:00Z",
  },
  {
    doc_id: "doc-manual-1",
    source: "manual",
    source_id: "ghi-chu-1",
    version: 3,
    title: "Ghi chú nội bộ về Warfarin",
    source_url: "",
    quality_status: "keep",
    quality_flags: ["manual_ingest"],
    pair_id: null,
    retrieved_at: "2026-10-03T08:00:00Z",
  },
];

function overview(overrides: Partial<WarehouseOverview> = {}): WarehouseOverview {
  return {
    documents_by_source: [
      { source: "pubmed", documents: 2, latest_retrieved_at: "2026-10-01T08:00:00Z", by_content_level: { full: 2 } },
      { source: "manual", documents: 1, latest_retrieved_at: null, by_content_level: { full: 1 } },
    ],
    documents_by_quality_status: { keep: 2, quarantine: 1 },
    quality_findings: [],
    table_counts: { documents: 3, chunks: 120 },
    rag: {
      collection: "vigilens_docs__gemini",
      chroma_chunks: 120,
      postgres_chunks: 120,
      embedding_provider: "gemini",
      embedding_model: "gemini-embedding-001",
      persist_dir: "data/chroma",
    },
    ...overrides,
  };
}

function renderPage() {
  return render(<AdminCorpusPage />);
}

function tableRows(container: HTMLElement) {
  return Array.from(container.querySelectorAll("tbody tr"));
}

beforeEach(() => {
  state.overview = overview();
  state.documents = { documents: DOCUMENTS, count: DOCUMENTS.length };
  state.params = [];
  useAppStore.setState({ role: "investigator" });
});

afterEach(() => {
  useAppStore.setState({ role: "investigator" });
  cleanup();
});

describe("/admin/corpus — bảng tài liệu", () => {
  it("hiện đúng số tài liệu trong bảng và trên nhãn đếm", () => {
    const { container } = renderPage();

    expect(screen.getByText("3 tài liệu")).toBeTruthy();
    expect(tableRows(container)).toHaveLength(3);
    expect(screen.getByText("Ibuprofen và xuất huyết tiêu hoá")).toBeTruthy();
    expect(screen.getByText("Nhãn Metformin")).toBeTruthy();
    expect(screen.getByText("Ghi chú nội bộ về Warfarin")).toBeTruthy();
  });

  it("cột chất lượng hiện nhãn tiếng Việt cho cờ chất lượng, không hiện mã thô", () => {
    const { container } = renderPage();
    const rows = tableRows(container);

    expect(within(rows[0]).getByText("thiếu tóm tắt, chỉ có metadata")).toBeTruthy();
    expect(within(rows[2]).getByText("nạp tay")).toBeTruthy();

    expect(screen.queryByText(/missing_abstract/)).toBeNull();
    expect(screen.queryByText(/manual_ingest/)).toBeNull();
  });

  it("lọc theo từ khoá thì thu hẹp bảng còn đúng tài liệu khớp", async () => {
    const user = userEvent.setup();
    const { container } = renderPage();
    expect(tableRows(container)).toHaveLength(3);

    await user.type(screen.getByLabelText("Tìm tài liệu trong kho"), "metformin");

    const rows = tableRows(container);
    expect(rows).toHaveLength(1);
    expect(within(rows[0]).getByText("Nhãn Metformin")).toBeTruthy();
  });

  it("không tài liệu nào khớp bộ lọc thì hiện trạng thái rỗng", async () => {
    const user = userEvent.setup();
    const { container } = renderPage();

    await user.type(screen.getByLabelText("Tìm tài liệu trong kho"), "khong-co-tai-lieu-nao");

    expect(screen.getByText("Không có tài liệu nào khớp bộ lọc")).toBeTruthy();
    expect(tableRows(container)).toHaveLength(0);
  });

  it("chọn lọc theo nguồn thì truyền nguồn đó xuống hook dữ liệu", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.selectOptions(screen.getByLabelText("Lọc theo nguồn"), "pubmed");

    expect(state.params.at(-1)).toMatchObject({ source: "pubmed", limit: 200 });
  });
});

describe("/admin/corpus — chất lượng và chỉ mục RAG", () => {
  it("chỉ mục RAG hiện trạng thái khớp khi số đoạn Chroma bằng Postgres", () => {
    renderPage();

    expect(screen.getByText("khớp")).toBeTruthy();
    expect(screen.getByText(/Chroma:/)).toBeTruthy();
  });

  it("chỉ mục RAG hiện trạng thái lệch khi số đoạn Chroma khác Postgres", () => {
    state.overview = overview({
      rag: {
        collection: "vigilens_docs__gemini",
        chroma_chunks: 118,
        postgres_chunks: 120,
        embedding_provider: "gemini",
        embedding_model: "gemini-embedding-001",
        persist_dir: "data/chroma",
      },
    });
    renderPage();

    expect(screen.getByText("lệch")).toBeTruthy();
  });

  it("phát hiện chất lượng hiện nhãn tiếng Việt kèm mã kiểm tra gốc", () => {
    state.overview = overview({ quality_findings: [{ check_name: "missing_abstract", severity: "warn", count: 12 }] });
    renderPage();

    const item = screen.getByText("(missing_abstract)").closest("li") as HTMLElement;
    expect(within(item).getByText(/thiếu tóm tắt, chỉ có metadata/)).toBeTruthy();
    expect(within(item).getByText("12")).toBeTruthy();
  });
});

describe("/admin/corpus — quyền xem", () => {
  it("vai trò khách thì chặn xem kho bằng thông báo tiếng Việt", () => {
    useAppStore.setState({ role: "visitor" });
    renderPage();

    expect(screen.getByText("Không có quyền xem kho tài liệu")).toBeTruthy();
    expect(screen.queryByText("Danh sách tài liệu")).toBeNull();
  });
});
