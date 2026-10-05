// Cấu hình chế độ chạy: `live` gọi FastAPI thật, mặc định `replay` dùng MSW + IndexedDB.
// Nguồn: biến môi trường NEXT_PUBLIC_API_MODE (tương đương VITE_API_MODE của bản Vite).
export const API_MODE = process.env.NEXT_PUBLIC_API_MODE ?? "replay";
export const isLive = API_MODE === "live";
export const API_PREFIX = "/api/v1";
