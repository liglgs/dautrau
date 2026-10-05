"use client";

import * as React from "react";

/** Lưới an toàn cuối cùng khi cả layout gốc không dựng được. */
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  React.useEffect(() => {
    console.error("VigiLens lỗi ở layout gốc:", error);
  }, [error]);

  return (
    <html lang="vi">
      <body
        style={{
          fontFamily: "system-ui, sans-serif",
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#faf9f7",
          color: "#1c1b19",
        }}
      >
        <div style={{ maxWidth: "52ch", padding: "32px" }}>
          <h1 style={{ fontSize: 22, marginBottom: 8 }}>VigiLens không khởi động được</h1>
          <p style={{ lineHeight: 1.6, color: "#57534e" }}>
            Ứng dụng gặp lỗi khi dựng giao diện. Dữ liệu điều tra vẫn nằm ở backend.
          </p>
          <p style={{ fontFamily: "ui-monospace, monospace", fontSize: 12, color: "#78716c" }}>
            {error.message || "Lỗi không xác định"}
          </p>
          <button
            type="button"
            onClick={reset}
            style={{
              marginTop: 12,
              padding: "8px 14px",
              borderRadius: 8,
              border: "1px solid #1c1b19",
              background: "#1c1b19",
              color: "#faf9f7",
              cursor: "pointer",
            }}
          >
            Thử lại
          </button>
        </div>
      </body>
    </html>
  );
}
