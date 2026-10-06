/** Nhãn tiếng Việt cho các cờ chất lượng của kho ELT; tách khỏi component để kiểm thử được. */

export const WAREHOUSE_FLAG_LABEL: Record<string, string> = {
  // Nhóm chung
  no_title: "thiếu tiêu đề",
  text_too_short: "văn bản quá ngắn",
  raw_hash_missing: "không xác định được băm bản thô",
  possible_markup: "văn bản có ký tự giống thẻ HTML",
  duplicate_in_run: "trùng định danh trong cùng lần chạy",
  // PubMed
  has_abstract: "có tóm tắt",
  missing_abstract: "thiếu tóm tắt, chỉ có metadata",
  retracted_publication: "bài báo đã bị rút",
  not_primary_evidence: "không phải nghiên cứu gốc",
  missing_doi: "không có DOI",
  has_journal: "có tên tạp chí",
  // DailyMed
  multi_ingredient: "nhiều hoạt chất",
  missing_route: "nhãn thiếu đường dùng",
  route_not_oral: "không dùng đường uống",
  missing_effective_time: "nhãn thiếu ngày hiệu lực",
  missing_sections: "nhãn không có mục nội dung",
  few_sections: "nhãn có ít mục nội dung",
  // FAERS
  no_reactions: "báo cáo không có phản ứng",
  no_drugs: "báo cáo không có thuốc",
  report_too_large: "báo cáo quá lớn",
  missing_age: "thiếu tuổi bệnh nhân",
  missing_sex: "thiếu giới tính bệnh nhân",
  multiple_drugs: "báo cáo có nhiều thuốc",
  missing_drug_start_date: "thiếu ngày bắt đầu dùng thuốc",
  missing_drug_route: "thiếu đường dùng của thuốc",
  missing_receivedate: "thiếu ngày FDA nhận báo cáo",
  suspicion_not_causality: "chỉ là nghi ngờ, không phải quan hệ nhân quả",
  // Nạp tay
  manual_ingest: "nạp tay",
  manual_entry_not_verified_with_source: "chưa đối chiếu nguồn gốc",
  // Nguồn tham chiếu
  reference_material_not_primary_evidence: "tài liệu tham chiếu, không phải bằng chứng chính",
};

export function warehouseFlagLabel(flag: string) {
  return WAREHOUSE_FLAG_LABEL[flag] ?? flag;
}

