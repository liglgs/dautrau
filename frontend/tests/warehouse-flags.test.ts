import { describe, expect, it } from "vitest";
import { WAREHOUSE_FLAG_LABEL, warehouseFlagLabel } from "@/lib/warehouse-flags";

/** Mọi mã cờ do `scripts/elt/quality.py` và `src/services/warehouse/ingest.py` sinh ra. */
const REAL_FLAGS = [
  // chung
  "no_title",
  "text_too_short",
  "raw_hash_missing",
  "possible_markup",
  "duplicate_in_run",
  // PubMed
  "has_abstract",
  "missing_abstract",
  "retracted_publication",
  "not_primary_evidence",
  "missing_doi",
  "has_journal",
  // DailyMed
  "multi_ingredient",
  "missing_route",
  "route_not_oral",
  "missing_effective_time",
  "missing_sections",
  "few_sections",
  // FAERS
  "no_reactions",
  "no_drugs",
  "report_too_large",
  "missing_age",
  "missing_sex",
  "multiple_drugs",
  "missing_drug_start_date",
  "missing_drug_route",
  "missing_receivedate",
  "suspicion_not_causality",
  // nạp tay
  "manual_ingest",
  "manual_entry_not_verified_with_source",
];

describe("nhãn cờ chất lượng của kho", () => {
  it("có nhãn tiếng Việt cho mọi mã cờ thật", () => {
    const missing = REAL_FLAGS.filter((flag) => !WAREHOUSE_FLAG_LABEL[flag]);
    expect(missing).toEqual([]);
  });

  it("không giữ nhãn cho mã cờ không tồn tại trong mã nguồn", () => {
    const stale = Object.keys(WAREHOUSE_FLAG_LABEL).filter(
      (flag) => !REAL_FLAGS.includes(flag) && flag !== "reference_material_not_primary_evidence",
    );
    expect(stale).toEqual([]);
  });

  it("trả nguyên mã khi gặp cờ lạ", () => {
    expect(warehouseFlagLabel("co_moi_chua_biet")).toBe("co_moi_chua_biet");
    expect(warehouseFlagLabel("missing_abstract")).toBe("thiếu tóm tắt, chỉ có metadata");
  });
});
