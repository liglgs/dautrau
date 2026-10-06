// @vitest-environment jsdom
import * as React from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DrugLookupPage from "@/app/app/drugs/page";
import { BackendError } from "@/lib/api/errors";
import type { DrugLookupResult, RagSearchInput, RagSearchResult, WarehouseDocumentDetail } from "@/lib/api/types";

/**
 * Bài kiểm thử ở mức trang cho `/app/drugs` (tra cứu thuốc + tìm kiếm ngữ nghĩa RAG).
 *
 * Toàn bộ hook dữ liệu và nguồn API thật bị thay bằng mock: bài kiểm thử không gọi mạng.
 * Môi trường jsdom chỉ bật cho tệp này bằng khối `@vitest-environment`, mặc định của các bài
 * kiểm thử hiện có vẫn là `node`.
 */

const state = vi.hoisted(() => ({
  drug: undefined as DrugLookupResult | undefined,
  drugError: null as unknown,
  rag: undefined as RagSearchResult | undefined,
  ragError: null as unknown,
  ragCalls: [] as RagSearchInput[],
  detail: undefined as WarehouseDocumentDetail | undefined,
}));

vi.mock("@/lib/hooks/use-data", async () => {
  const React = await import("react");
  return {
    useDrugLookup: (name: string, enabled: boolean) => ({
      data: enabled ? state.drug : undefined,
      isLoading: false,
      isFetching: false,
      error: enabled ? state.drugError : null,
    }),
    // Mô phỏng mutation của react-query: gọi mutate thì dữ liệu mới và component dựng lại.
    useRagSearch: () => {
      const [outcome, setOutcome] = React.useState<{ data?: RagSearchResult; error?: unknown }>({});
      return {
        data: outcome.data,
        error: outcome.error,
        isPending: false,
        mutate: (input: RagSearchInput) => {
          state.ragCalls.push(input);
          setOutcome({ data: state.rag, error: state.ragError });
        },
      };
    },
    useWarehouseDocument: () => ({ data: state.detail, isLoading: false, error: null }),
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

const IBUPROFEN: DrugLookupResult = {
  query: "ibuprofen",
  matched: true,
  origin: "warehouse",
  drugs: [{ drug_id: "drug-ibuprofen", name: "Ibuprofen", ingredient: "ibuprofen", verified: true, aliases: ["brufen"] }],
  pairs: [
    {
      pair_id: "pair-1",
      drug_name: "Ibuprofen",
      event_term: "xuất huyết tiêu hoá",
      status: "candidate_not_gold",
      source: "faers",
    },
  ],
  documents: { pubmed: 3 },
};

const RAG_HIT: RagSearchResult = {
  query: "ibuprofen xuất huyết tiêu hoá",
  k: 6,
  embedding_model: "gemini-embedding-001",
  hits: [
    {
      chunk_id: "chunk-1",
      score: 0.82,
      text: "Ibuprofen làm tăng nguy cơ xuất huyết tiêu hoá ở bệnh nhân trên 65 tuổi.",
      ordinal: 0,
      char_start: 0,
      char_end: 72,
      in_postgres: true,
      document: {
        doc_id: "doc-pubmed-1",
        source: "pubmed",
        source_id: "pmid-1",
        version: 2,
        title: "Nguy cơ xuất huyết tiêu hoá khi dùng NSAID",
        source_url: "https://pubmed.ncbi.nlm.nih.gov/1/",
        quality_status: "keep",
        quality_flags: ["missing_abstract", "not_primary_evidence"],
        pair_id: "pair-1",
        retrieved_at: "2026-10-01T08:00:00Z",
      },
    },
  ],
};

const DETAIL: WarehouseDocumentDetail = {
  doc_id: "doc-pubmed-1",
  source: "pubmed",
  source_id: "pmid-1",
  version: 2,
  title: "Nguy cơ xuất huyết tiêu hoá khi dùng NSAID",
  source_url: "https://pubmed.ncbi.nlm.nih.gov/1/",
  quality_status: "keep",
  quality_flags: ["missing_abstract"],
  pair_id: "pair-1",
  retrieved_at: "2026-10-01T08:00:00Z",
  text_sha256: "a".repeat(64),
  sections: [{ title: "Kết quả", start: 0, end: 72 }],
  text_preview: "Toàn văn tài liệu dùng cho phần xem trước trong bài kiểm thử.",
};

beforeEach(() => {
  state.drug = undefined;
  state.drugError = null;
  state.rag = undefined;
  state.ragError = null;
  state.ragCalls = [];
  state.detail = DETAIL;
});

afterEach(() => {
  cleanup();
});

async function traCuu(user: ReturnType<typeof userEvent.setup>, name: string) {
  await user.type(screen.getByLabelText("Tên thuốc cần tra cứu"), name);
  await user.click(screen.getByRole("button", { name: "Tra cứu" }));
}

/** Bấm "Tìm trong kho" ở dòng cặp thuốc–biến cố đầu tiên để chạy tìm kiếm RAG. */
async function hoiKhoTheoCap(user: ReturnType<typeof userEvent.setup>) {
  const cell = await screen.findByText("Ibuprofen → xuất huyết tiêu hoá");
  const row = cell.closest("tr") as HTMLElement;
  await user.click(within(row).getByRole("button", { name: /Tìm trong kho/ }));
}

describe("/app/drugs — tra cứu thuốc", () => {
  it("nhập tên thuốc rồi gửi thì hiện kết quả tra cứu", async () => {
    const user = userEvent.setup();
    state.drug = IBUPROFEN;
    render(<DrugLookupPage />);

    expect(screen.queryByText("Ibuprofen")).toBeNull();

    await traCuu(user, "ibuprofen");

    expect(await screen.findByText("Ibuprofen")).toBeTruthy();
    expect(screen.getByText("đã xác minh")).toBeTruthy();
    expect(screen.getByText("Ibuprofen → xuất huyết tiêu hoá")).toBeTruthy();
    expect(screen.getByText("ứng viên — NOT gold")).toBeTruthy();
    expect(screen.getByText("nguồn tra: kho đã nạp")).toBeTruthy();
    expect(screen.getByText("Tài liệu liên quan trong kho:")).toBeTruthy();
  });

  it("không tra được kho thì hiện thông báo lỗi tiếng Việt", async () => {
    const user = userEvent.setup();
    state.drugError = new BackendError(500, "internal_error", "Lỗi máy chủ khi đọc kho.");
    render(<DrugLookupPage />);

    await traCuu(user, "ibuprofen");

    expect(await screen.findByText("Không tra được kho: Lỗi máy chủ khi đọc kho.")).toBeTruthy();
  });

  it("kho chưa sẵn sàng (503) thì hiện cảnh báo khởi động kho", async () => {
    const user = userEvent.setup();
    state.drugError = new BackendError(503, "WAREHOUSE_UNAVAILABLE", "Kho bằng chứng chưa được dựng.");
    render(<DrugLookupPage />);

    await traCuu(user, "ibuprofen");

    expect(await screen.findByText("Kho bằng chứng chưa sẵn sàng")).toBeTruthy();
    expect(screen.getByText(/docker compose -f docker-compose.elt.yml up -d --wait/)).toBeTruthy();
  });

  it("không khớp hoạt chất nào thì hiện trạng thái rỗng tiếng Việt", async () => {
    const user = userEvent.setup();
    state.drug = { query: "zzz", matched: false, origin: "dictionary", drugs: [], pairs: [], documents: {} };
    render(<DrugLookupPage />);

    await traCuu(user, "zzz");

    expect(await screen.findByText("Không tìm thấy thuốc trong kho")).toBeTruthy();
    expect(screen.getByText(/Không có hoạt chất nào khớp/)).toBeTruthy();
  });
});

describe("/app/drugs — tìm kiếm ngữ nghĩa RAG", () => {
  it("thẻ kết quả hiện nhãn tiếng Việt cho cờ chất lượng, không hiện mã thô", async () => {
    const user = userEvent.setup();
    state.drug = IBUPROFEN;
    state.rag = RAG_HIT;
    render(<DrugLookupPage />);

    await traCuu(user, "ibuprofen");
    await hoiKhoTheoCap(user);

    expect(await screen.findByText("thiếu tóm tắt, chỉ có metadata")).toBeTruthy();
    expect(screen.getByText("không phải nghiên cứu gốc")).toBeTruthy();
    expect(screen.queryByText(/missing_abstract/)).toBeNull();
    expect(screen.queryByText(/not_primary_evidence/)).toBeNull();

    expect(state.ragCalls).toEqual([{ query: "Ibuprofen xuất huyết tiêu hoá", k: 6, pairId: "pair-1" }]);
    expect(screen.getByText("Nguy cơ xuất huyết tiêu hoá khi dùng NSAID")).toBeTruthy();
    expect(screen.getByText(/1 đoạn gần nhất/)).toBeTruthy();
  });

  it("không có đoạn nào phù hợp thì hiện trạng thái rỗng của kho", async () => {
    const user = userEvent.setup();
    state.drug = IBUPROFEN;
    state.rag = { query: "ibuprofen xuất huyết tiêu hoá", k: 6, embedding_model: "gemini-embedding-001", hits: [] };
    render(<DrugLookupPage />);

    await traCuu(user, "ibuprofen");
    await hoiKhoTheoCap(user);

    expect(await screen.findByText("Không có đoạn nào phù hợp")).toBeTruthy();
  });

  it("lỗi tìm kiếm RAG cũng hiện thông báo tiếng Việt", async () => {
    const user = userEvent.setup();
    state.drug = IBUPROFEN;
    state.ragError = new BackendError(500, "rag_failed", "Chỉ mục RAG lỗi.");
    render(<DrugLookupPage />);

    await traCuu(user, "ibuprofen");
    await hoiKhoTheoCap(user);

    expect(await screen.findByText("Không tìm được trong kho: Chỉ mục RAG lỗi.")).toBeTruthy();
  });

  it("mở tài liệu từ thẻ kết quả thì hiện chi tiết và đóng lại được", async () => {
    const user = userEvent.setup();
    state.drug = IBUPROFEN;
    state.rag = RAG_HIT;
    render(<DrugLookupPage />);

    await traCuu(user, "ibuprofen");
    await hoiKhoTheoCap(user);
    await user.click(await screen.findByRole("button", { name: "Mở tài liệu" }));

    expect(await screen.findByText("Toàn văn tài liệu dùng cho phần xem trước trong bài kiểm thử.")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Đóng" }));
    expect(screen.queryByText("Toàn văn tài liệu dùng cho phần xem trước trong bài kiểm thử.")).toBeNull();
  });
});
