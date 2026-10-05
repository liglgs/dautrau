/**
 * Guardrail sản phẩm (PHẦN C của brief):
 *  1. Không bao giờ kết luận nhân quả.
 *  2. Không suy ra tỷ lệ mắc (incidence) từ báo cáo tự nguyện.
 *  3. Không khẳng định "an toàn tuyệt đối".
 *
 * Hàm `assertNoCausalClaim` được dùng cho dữ liệu mock, đầu ra chatbot và dossier preview.
 */

export const CAUSAL_PATTERNS: { pattern: RegExp; reason: string }[] = [
  { pattern: /\b(chắc chắn|đã chứng minh|chứng minh được)\b[^.]{0,40}\bgây\b/i, reason: "khẳng định nhân quả đã được chứng minh" },
  { pattern: /\b(gây ra|dẫn đến|nguyên nhân (của|gây))\b/i, reason: "khẳng định nhân quả trực tiếp" },
  { pattern: /\bcaused by\b|\bproves? that\b|\bdefinitely causes\b/i, reason: "causal claim (English)" },
  { pattern: /\b(thuốc|hoạt chất)\b[^.]{0,30}\b(an toàn tuyệt đối|không có nguy cơ|hoàn toàn an toàn)\b/i, reason: "khẳng định an toàn tuyệt đối" },
  { pattern: /\b(tỷ lệ mắc|tần suất mắc|incidence)\b[^.]{0,40}\b(tăng|giảm|cao|thấp)\b/i, reason: "suy diễn tỷ lệ mắc" },
];

export const ALLOWED_SCOPE_PHRASES = [
  "được bằng chứng ủng hộ trong phạm vi",
  "bị bằng chứng phản bác trong phạm vi",
  "chưa đủ bằng chứng để kết luận",
  "lệch phạm vi so với nhận định",
  "cần chuyên viên can thiệp",
];

export interface GuardrailViolation {
  rule: "no_causal_claim" | "no_incidence_inference" | "no_absolute_safety";
  matched: string;
  reason: string;
}

export function findCausalClaims(text: string): GuardrailViolation[] {
  const violations: GuardrailViolation[] = [];
  for (const { pattern, reason } of CAUSAL_PATTERNS) {
    const match = text.match(pattern);
    if (match) {
      const rule = /an toàn tuyệt đối|hoàn toàn an toàn/.test(match[0])
        ? "no_absolute_safety"
        : /tỷ lệ mắc|incidence|tần suất/.test(match[0])
          ? "no_incidence_inference"
          : "no_causal_claim";
      violations.push({ rule, matched: match[0], reason });
    }
  }
  return violations;
}

export class GuardrailError extends Error {
  violations: GuardrailViolation[];
  constructor(violations: GuardrailViolation[]) {
    super(
      `Vi phạm guardrail: ${violations.map((item) => item.reason).join("; ")}. ` +
        "Chỉ dùng ngôn ngữ phạm vi: “được bằng chứng ủng hộ trong phạm vi…”, “chưa đủ bằng chứng…”.",
    );
    this.name = "GuardrailError";
    this.violations = violations;
  }
}

/** Ném lỗi nếu văn bản chứa câu khẳng định nhân quả / an toàn tuyệt đối / suy diễn tỷ lệ mắc. */
export function assertNoCausalClaim(text: string): string {
  const violations = findCausalClaims(text);
  if (violations.length > 0) throw new GuardrailError(violations);
  return text;
}

/** Phiên bản không ném lỗi, dùng để tô cảnh báo trong UI (ví dụ ô chat). */
export function hasGuardrailRisk(text: string): boolean {
  return findCausalClaims(text).length > 0;
}

/** Phát hiện mẫu giống thông tin định danh bệnh nhân (số điện thoại, email, CCCD 12 số). */
export function looksLikePatientIdentifier(text: string): boolean {
  return (
    /\b0\d{9,10}\b/.test(text) ||
    /[\w.+-]+@[\w-]+\.[\w.]{2,}/.test(text) ||
    /\b\d{12}\b/.test(text) ||
    /\b(CCCD|CMND|hộ chiếu|passport)\b/i.test(text)
  );
}
