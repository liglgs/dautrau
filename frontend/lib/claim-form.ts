import type { CreateInvestigationInput } from "@/lib/api/types";

export const DEFAULT_STEPS = 8;
export const DEFAULT_DOCS = 50;
export const MAX_STEPS = 20;
export const MAX_DOCS = 100;

export function validateClaim(input: CreateInvestigationInput): string | null {
  for (const [value, limit, label] of [
    [input.claimText, 5000, "Nhận định"], [input.drug, 200, "Hoạt chất"], [input.adverseEvent, 200, "Biến cố"],
    [input.population ?? "", 200, "Quần thể"], [input.dose ?? "", 120, "Liều"],
    [input.route ?? "", 120, "Đường dùng"], [input.timeWindow ?? "", 120, "Cửa sổ thời gian"],
  ] as const) {
    if ([...value].length > limit) return `${label} vượt quá ${limit} ký tự.`;
  }
  if (!input.claimText.trim() || !input.drug.trim() || !input.adverseEvent.trim()) return "Cần nhận định, hoạt chất và biến cố.";
  if (!input.sources.length) return "Chọn ít nhất một nguồn.";
  if (new Set(input.sources).size !== input.sources.length || input.sources.some((source) => !["pubmed", "dailymed", "faers"].includes(source))) return "Nguồn không hợp lệ hoặc bị lặp.";
  if (!Number.isInteger(input.maxSteps) || input.maxSteps < 1 || input.maxSteps > MAX_STEPS) return "Ngân sách phải từ 1 đến 20 bước.";
  if (!Number.isInteger(input.maxDocs) || input.maxDocs < 1 || input.maxDocs > MAX_DOCS) return "Ngân sách phải từ 1 đến 100 tài liệu.";
  return null;
}

/** Keeps the same key after an uncertain network failure; edits start a different operation. */
export class SubmissionIdentity {
  private fingerprint = "";
  private key = "";
  forInput(input: CreateInvestigationInput): string {
    const fingerprint = JSON.stringify(input);
    if (fingerprint !== this.fingerprint || !this.key) {
      this.fingerprint = fingerprint;
      this.key = crypto.randomUUID();
    }
    return this.key;
  }
}
