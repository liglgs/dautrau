// @vitest-environment jsdom
import * as React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AdminIngestionPage from "@/app/admin/ingestion/page";
import { BackendError } from "@/lib/api/errors";
import type { IngestDocumentInput, IngestDocumentResult, IngestionEventsResult } from "@/lib/api/types";

/**
 * Bài kiểm thử ở mức trang cho `/admin/ingestion` (biểu mẫu nạp tài liệu).
 *
 * Điểm chặn tái phát quan trọng: nút "Tạo phiên bản mới" trong cảnh báo 409 nằm trong `<form>` nạp
 * tài liệu, nên nó phải có `type="button"` — nếu không, một cú nhấp sẽ gửi biểu mẫu thật và nạp
 * thêm tài liệu ngoài ý muốn.
 */

const state = vi.hoisted(() => ({
  events: undefined as IngestionEventsResult | undefined,
  ingestError: null as unknown,
  ingestResult: undefined as IngestDocumentResult | undefined,
  calls: [] as IngestDocumentInput[],
}));

vi.mock("@/lib/hooks/use-data", async () => {
  const React = await import("react");
  return {
    useIngestionEvents: () => ({
      data: state.events,
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: () => undefined,
    }),
    // Mô phỏng mutation của react-query: mutate gọi callback onSuccess của nơi gọi khi thành công.
    useIngestDocument: () => {
      const [outcome, setOutcome] = React.useState<{ data?: IngestDocumentResult; error?: unknown; isSuccess: boolean }>({
        isSuccess: false,
      });
      return {
        data: outcome.data,
        error: outcome.error,
        isPending: false,
        isSuccess: outcome.isSuccess,
        reset: () => setOutcome({ isSuccess: false }),
        mutate: (input: IngestDocumentInput, options?: { onSuccess?: (payload: IngestDocumentResult) => void }) => {
          state.calls.push(input);
          if (state.ingestError) {
            setOutcome({ isSuccess: false, error: state.ingestError });
            return;
          }
          const payload = state.ingestResult as IngestDocumentResult;
          setOutcome({ isSuccess: true, data: payload });
          options?.onSuccess?.(payload);
        },
      };
    },
  };
});

vi.mock("@/lib/api/real", () => ({
  SESSION_AUTH: false,
  request: () => {
    throw new Error("Bài kiểm thử trang không gọi mạng thật");
  },
  createApiSource: () => {
    throw new Error("Bài kiểm thử trang không dùng nguồn API thật");
  },
}));

const TEXT =
  "Ibuprofen làm tăng nguy cơ xuất huyết tiêu hoá ở bệnh nhân trên 65 tuổi; ghi chú nội bộ của dược sĩ duyệt.";

const RESULT: IngestDocumentResult = {
  doc_id: "doc-manual-ghi-chu-noi-bo-01-v1",
  created: true,
  sha256: "b".repeat(64),
  text_chars: TEXT.length,
  quality_status: "keep",
  quality_flags: ["manual_ingest"],
  rag: {
    indexed: true,
    chunks_written: 4,
    documents_indexed: 1,
    collection: "vigilens_docs__gemini",
    embedding_model: "gemini-embedding-001",
  },
  event_id: "event-1",
};

const EVENTS: IngestionEventsResult = {
  events: [
    {
      event_id: "event-1",
      kind: "ingest_document",
      status: "completed",
      title: "Nạp tài liệu ghi-chu-noi-bo-01",
      detail: { chunks_written: 4 },
      created_at: "2026-10-05T08:00:00Z",
    },
  ],
  count: 1,
};

beforeEach(() => {
  state.events = EVENTS;
  state.ingestError = null;
  state.ingestResult = RESULT;
  state.calls = [];
});

afterEach(() => {
  cleanup();
});

async function dienBieuMau(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/Mã nguồn \(source_id\)/), "ghi-chu-noi-bo-01");
  await user.type(screen.getByLabelText(/Tiêu đề/), "Ghi chú nội bộ về ibuprofen");
  await user.type(screen.getByLabelText(/Văn bản đầy đủ/), TEXT);
}

function nutNhap() {
  return screen.getByRole("button", { name: /Nạp vào kho/ });
}

describe("/admin/ingestion — gửi biểu mẫu", () => {
  it("gửi biểu mẫu hợp lệ thì hiện kết quả nạp kèm nhãn tiếng Việt cho cờ chất lượng", async () => {
    const user = userEvent.setup();
    render(<AdminIngestionPage />);

    await dienBieuMau(user);
    await user.click(nutNhap());

    expect(state.calls).toEqual([
      {
        source: "manual",
        source_id: "ghi-chu-noi-bo-01",
        version: 1,
        title: "Ghi chú nội bộ về ibuprofen",
        text: TEXT,
      },
    ]);

    expect(await screen.findByText("Đã nạp tài liệu mới")).toBeTruthy();
    expect(screen.getByText("doc-manual-ghi-chu-noi-bo-01-v1")).toBeTruthy();
    expect(screen.getByText("cờ: nạp tay")).toBeTruthy();
    expect(screen.queryByText(/manual_ingest/)).toBeNull();
    expect(screen.getByText(/đã đánh chỉ mục 4 đoạn vào vigilens_docs__gemini/)).toBeTruthy();
  });

  it("thiếu mã nguồn và tiêu đề thì chặn tại chỗ, không gửi lên kho", async () => {
    const user = userEvent.setup();
    render(<AdminIngestionPage />);

    await user.click(nutNhap());

    expect(await screen.findByText("Cần mã nguồn và tiêu đề tài liệu.")).toBeTruthy();
    expect(screen.getByText("Chưa gửi được")).toBeTruthy();
    expect(state.calls).toHaveLength(0);
  });

  it("dòng sự kiện nạp hiện sự kiện đã có trong kho", () => {
    render(<AdminIngestionPage />);

    expect(screen.getByText("Nạp tài liệu ghi-chu-noi-bo-01")).toBeTruthy();
    expect(screen.getByText("completed")).toBeTruthy();
  });
});

describe("/admin/ingestion — lỗi từ backend", () => {
  it("lỗi 409 thì hiện cảnh báo trùng phiên bản và nút tạo phiên bản mới", async () => {
    const user = userEvent.setup();
    state.ingestError = new BackendError(409, "document_version_conflict", "Trùng mã nguồn và phiên bản với nội dung khác.");
    render(<AdminIngestionPage />);

    await dienBieuMau(user);
    await user.click(nutNhap());

    expect(await screen.findByText("Trùng mã nguồn và phiên bản")).toBeTruthy();
    expect(screen.getByText(/Cùng mã nguồn và phiên bản nhưng nội dung khác/)).toBeTruthy();
    expect(state.calls).toHaveLength(1);
  });

  it("nút \"Tạo phiên bản mới\" là type=button: nhấp chỉ tăng phiên bản, không gửi biểu mẫu", async () => {
    const user = userEvent.setup();
    state.ingestError = new BackendError(409, "document_version_conflict", "Trùng mã nguồn và phiên bản với nội dung khác.");
    render(<AdminIngestionPage />);

    await dienBieuMau(user);
    await user.click(nutNhap());

    const bump = await screen.findByRole("button", { name: "Tạo phiên bản mới" });
    // Nút nằm trong <form> nạp tài liệu, nên thiếu type="button" sẽ khiến nó gửi biểu mẫu.
    expect(bump.closest("form")).not.toBeNull();
    expect(bump.getAttribute("type")).toBe("button");

    await user.click(bump);

    expect((screen.getByLabelText("Phiên bản") as HTMLInputElement).value).toBe("2");
    expect(state.calls).toHaveLength(1);
  });

  it("lỗi 403 thì hiện cảnh báo cần vai trò dược sĩ duyệt", async () => {
    const user = userEvent.setup();
    state.ingestError = new BackendError(403, "forbidden", "Token hiện tại không có quyền nạp tài liệu.");
    render(<AdminIngestionPage />);

    await dienBieuMau(user);
    await user.click(nutNhap());

    expect(await screen.findByText("Cần vai trò dược sĩ duyệt")).toBeTruthy();
    expect(screen.getByText(/Token hiện tại không có quyền nạp tài liệu\./)).toBeTruthy();
  });
});
