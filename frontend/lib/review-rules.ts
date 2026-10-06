/**
 * Quy tắc gửi quyết định duyệt, dùng chung một con số với máy chủ.
 *
 * RV-04: trước đây giao diện đòi lý do dài ít nhất 15 ký tự còn máy chủ chỉ cần khác rỗng, nên
 * gọi thẳng API là bỏ qua được yêu cầu ghi lý do. Nay máy chủ cũng đòi đúng ngưỡng này
 * (`MIN_REVIEW_REASON` trong `src/models/schemas.py`); đổi số thì phải đổi cả hai nơi.
 */
export const MIN_REVIEW_REASON = 15;
