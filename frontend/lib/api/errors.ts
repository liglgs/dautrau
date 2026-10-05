/** One safe error envelope for JSON requests and Markdown downloads. */
export class BackendError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: unknown, public requestId?: string) {
    super(message);
    this.name = "BackendError";
  }
}

export function responseError(status: number, text: string): BackendError {
  let payload: Record<string, unknown> = {};
  try { payload = JSON.parse(text); } catch { /* Never render a proxy HTML error as application content. */ }
  const error = (payload.error ?? payload) as Record<string, unknown>;
  const hints: Record<number, string> = {
    401: "Phiên truy cập đã hết hạn. Đăng nhập lại để tiếp tục.",
    403: "Bạn không có quyền thực hiện thao tác này.",
    409: "Nội dung đã thay đổi. Tải phiên bản mới rồi kiểm tra lại quyết định.",
    422: "Dữ liệu chưa hợp lệ. Kiểm tra các trường trước khi gửi lại.",
    429: "Runner đang bận. Giữ nguyên yêu cầu và thử lại khi runner rảnh.",
    503: "Dịch vụ chưa sẵn sàng. Dữ liệu hiện có vẫn được giữ lại.",
  };
  return new BackendError(status, String(error.code ?? `http_${status}`),
    `${hints[status] ?? "Không thực hiện được yêu cầu."}${typeof error.message === "string" ? ` ${error.message}` : ""}`,
    error.details, typeof error.request_id === "string" ? error.request_id : undefined);
}
