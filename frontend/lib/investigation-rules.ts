import type { CoverageField, Investigation, Role } from "@/lib/types";

/**
 * `/continue` chỉ hợp lệ khi cuộc điều tra đang chờ người duyệt và không còn checkpoint nào đang chờ.
 *
 * Không dùng `reviewState` ở đây: trường đó nói về phiên bản hồ sơ, mà duyệt ở checkpoint
 * `assessment` thì chưa tạo hồ sơ nào (`review_status = null`), còn `review_status = "approved"`
 * chỉ xuất hiện khi hồ sơ đã duyệt xong — lúc đó run đã `completed` và nút này không còn nghĩa.
 * Trạng thái đúng để xét là `runStatus === "waiting_for_review"` và `checkpoint == null`.
 */
export function canContinueRun(
  investigation: Pick<Investigation, "runStatus" | "checkpoint"> | null | undefined,
  role: Role,
): boolean {
  if (!investigation) return false;
  return (
    investigation.runStatus === "waiting_for_review" &&
    !investigation.checkpoint &&
    (role === "investigator" || role === "admin")
  );
}

/** Nhãn tiếng Việt của sáu trường phạm vi, dùng chung cho lưới phủ và chip khoảng trống. */
export const COVERAGE_FIELD_LABEL: Record<CoverageField, string> = {
  drug: "Hoạt chất",
  adverseEvent: "Biến cố",
  population: "Quần thể",
  dose: "Liều",
  route: "Đường dùng",
  timeWindow: "Cửa sổ thời gian",
};

/**
 * Trả nhãn tiếng Việt cho một trường phạm vi. Khóa lạ (backend có thể gửi `time_window` chẳng
 * hạn) được in nguyên văn để không bịa ra nhãn không có trong dữ liệu.
 */
export function coverageFieldLabel(field: string): string {
  return COVERAGE_FIELD_LABEL[field as CoverageField] ?? field;
}
