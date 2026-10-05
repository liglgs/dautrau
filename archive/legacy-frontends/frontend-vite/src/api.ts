export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code = "",
    public retryable = false,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  body?: unknown,
  options: { method?: string; key?: string } = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method: options.method ?? (body === undefined ? "GET" : "POST"),
      credentials: "include",
      headers: {
        ...(body instanceof FormData
          ? {}
          : { "Content-Type": "application/json" }),
        ...(import.meta.env.VITE_API_MODE === "live"
          ? {}
          : { "X-Demo-User": sessionStorage.getItem("demo-user") ?? "" }),
        ...(body === undefined
          ? {}
          : { "Idempotency-Key": options.key ?? crypto.randomUUID() }),
      },
      body:
        body === undefined
          ? undefined
          : body instanceof FormData
            ? body
            : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      0,
      "Chưa xác định kết quả gửi. Kiểm tra kết nối và thử lại cùng thao tác.",
      "NETWORK_ERROR",
      true,
    );
  }
  if (!response.ok) {
    const error = await response.json();
    throw new ApiError(
      response.status,
      error.message,
      error.code,
      error.retryable,
    );
  }
  return response.json();
}
