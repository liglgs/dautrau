/**
 * BRAND — đổi một chỗ là đổi cả site (tên, slogan, tên viết tắt, liên hệ).
 * Không hard-code tên thương hiệu ở bất kỳ component nào.
 */
export const BRAND = {
  name: "VigiLens",
  shortName: "VigiLens",
  tagline: "Điều tra nhận định an toàn thuốc, có bằng chứng và có người duyệt",
  description:
    "VigiLens điều tra nhận định về an toàn thuốc trên PubMed, DailyMed và openFDA FAERS, tự đổi chiến lược khi thiếu dữ liệu và từ chối kết luận khi chưa đủ căn cứ.",
  project: "Đề tài P-066 — AI Agent chủ động điều tra và kiểm chứng nhận định an toàn thuốc",
  org: "Nhóm nghiên cứu P-066",
  contactEmail: "lien-he@vigilens.demo",
  demoNotice: "Dữ liệu minh họa — không dùng cho quyết định lâm sàng",
  projectNotice: "Đề tài P-066 · bản trình diễn với dữ liệu minh họa",
  liveNotice: "Đang nối API máy chủ — cần xác nhận chế độ nguồn; không dùng cho quyết định lâm sàng",
  liveProjectNotice: "Đề tài P-066 · bản trình diễn nối API",
  disclaimer:
    "VigiLens là công cụ hỗ trợ nghiên cứu cảnh giác dược. Kết quả không thay thế phán đoán chuyên môn của dược sĩ lâm sàng/chuyên viên an toàn thuốc và không phải khuyến cáo điều trị.",
  locales: ["vi", "en"] as const,
  defaultLocale: "vi" as const,
} as const;

