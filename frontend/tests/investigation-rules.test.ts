import { describe, expect, it } from "vitest";

import { COVERAGE_FIELD_LABEL, canContinueRun, coverageFieldLabel } from "@/lib/investigation-rules";
import type { Role, RunStatus } from "@/lib/types";

/** Dựng một `Investigation` tối thiểu, chỉ gồm hai trường mà `canContinueRun` đọc. */
function state(runStatus: RunStatus, checkpoint: string | null | undefined) {
  return { runStatus, checkpoint };
}

describe("canContinueRun", () => {
  it("bật khi run đang chờ duyệt và không còn checkpoint", () => {
    expect(canContinueRun(state("waiting_for_review", null), "investigator")).toBe(true);
    expect(canContinueRun(state("waiting_for_review", undefined), "admin")).toBe(true);
  });

  it("tắt khi vẫn còn checkpoint đang chờ", () => {
    for (const checkpoint of ["normalization", "assessment", "dossier"]) {
      expect(canContinueRun(state("waiting_for_review", checkpoint), "investigator")).toBe(false);
    }
  });

  it("tắt ở mọi trạng thái khác waiting_for_review", () => {
    for (const runStatus of ["queued", "running", "completed", "failed", "interrupted"] as RunStatus[]) {
      expect(canContinueRun(state(runStatus, null), "investigator")).toBe(false);
    }
  });

  it("chỉ cho điều tra viên và quản trị viên chạy tiếp", () => {
    for (const role of ["visitor", "reviewer"] as Role[]) {
      expect(canContinueRun(state("waiting_for_review", null), role)).toBe(false);
    }
  });

  it("chịu được dữ liệu chưa tải xong", () => {
    expect(canContinueRun(null, "admin")).toBe(false);
    expect(canContinueRun(undefined, "admin")).toBe(false);
  });

  // Hồi quy: bản cũ xét `reviewState === "approved" || reviewState === "changes_requested"`.
  // Duyệt ở checkpoint `assessment` không tạo hồ sơ nào nên `review_status = null`; trạng thái
  // đó phải bật nút, còn hồ sơ đã duyệt xong thì run đã `completed` nên phải tắt nút.
  it("bật đúng ở checkpoint assessment sau khi người duyệt đồng ý", () => {
    expect(canContinueRun({ runStatus: "waiting_for_review", checkpoint: null }, "investigator")).toBe(true);
    expect(canContinueRun({ runStatus: "completed", checkpoint: null }, "investigator")).toBe(false);
  });
});

describe("coverageFieldLabel", () => {
  it("dịch đủ sáu trường phạm vi", () => {
    expect(COVERAGE_FIELD_LABEL).toEqual({
      drug: "Hoạt chất",
      adverseEvent: "Biến cố",
      population: "Quần thể",
      dose: "Liều",
      route: "Đường dùng",
      timeWindow: "Cửa sổ thời gian",
    });
  });

  it("giữ nguyên khóa lạ thay vì bịa nhãn", () => {
    expect(coverageFieldLabel("time_window")).toBe("time_window");
    expect(coverageFieldLabel("study_type")).toBe("study_type");
  });
});
