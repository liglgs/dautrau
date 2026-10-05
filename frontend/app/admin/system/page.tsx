"use client";

import { Card, CardBody, CardHeader, CardTitle, Chip } from "@/components/ui";
import { DATA_MODE } from "@/lib/api";
import { BRAND } from "@/lib/brand";

const CHECKS = [
  { name: "Backend FastAPI", state: DATA_MODE === "api" ? "đang dùng" : "chưa nối", note: "GET /health, GET /ready" },
  { name: "Nguồn dữ liệu", state: "chưa nối", note: "Kiểm tra ở /admin/sources" },
  { name: "Hàng đợi chạy agent", state: "chưa nối", note: "Runner trong tiến trình, một cuộc điều tra một lúc" },
  { name: "Cổng LLM", state: "chưa nối", note: "Ngân sách và sổ usage do máy chủ giữ" },
  { name: "Kho tài liệu", state: "chưa nối", note: "SQLite trong MVP" },
];

export default function AdminSystemPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Sức khỏe hệ thống</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Trạng thái các thành phần. Giao diện chỉ hiển thị thứ backend công bố, không tự đoán.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {CHECKS.map((check) => (
          <Card key={check.name}>
            <CardHeader>
              <CardTitle>{check.name}</CardTitle>
              <Chip tone={check.state === "đang dùng" ? "support" : "neutral"}>{check.state}</Chip>
            </CardHeader>
            <CardBody className="text-[13px] text-muted-foreground">{check.note}</CardBody>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Giới hạn đã biết của MVP</CardTitle>
        </CardHeader>
        <CardBody className="space-y-1.5 text-[13px] text-muted-foreground">
          <p>Chỉ hai token vai trò dùng chung; chưa có tài khoản, phiên đăng nhập hay CSRF.</p>
          <p>Chưa có endpoint hủy cuộc điều tra.</p>
          <p>Một số phản hồi chưa khai báo schema đầy đủ trong OpenAPI.</p>
          <p>Trang này hiển thị {BRAND.name} ở chế độ {DATA_MODE === "api" ? "backend thật" : "dữ liệu minh họa"}.</p>
        </CardBody>
      </Card>
    </div>
  );
}
