export const formatDateTime = (value: string | null | undefined) =>
  value ? new Date(value).toLocaleString("vi-VN") : "Không rõ thời điểm";

export const formatDate = (value: string | null | undefined) =>
  value ? new Date(value).toLocaleDateString("vi-VN") : "Không rõ thời điểm";

export const formatTime = (value: string | null | undefined) =>
  value
    ? new Date(value).toLocaleTimeString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "--:--";

export const formatClock = (value: string | null | undefined) =>
  value
    ? new Date(value).toLocaleTimeString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      })
    : "--:--:--";

export const initials = (name: string) =>
  name
    .split(/[\s·]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
