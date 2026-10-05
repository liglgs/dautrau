"use client";

import { Card, CardBody, CardHeader, CardTitle, Chip } from "@/components/ui";

const ROLES = [
  { name: "Khách", scope: "Xem trang công khai, đọc ví dụ và tài liệu.", mvp: "Không cần token" },
  { name: "Điều tra viên", scope: "Tạo cuộc điều tra, chạy agent, gửi yêu cầu tìm thêm.", mvp: "Token vai trò dùng chung" },
  { name: "Dược sĩ duyệt", scope: "Duyệt, từ chối, sửa bằng chứng, yêu cầu duyệt lại.", mvp: "Token vai trò dùng chung" },
  { name: "Quản trị", scope: "Cấu hình nguồn, guardrail, ngân sách, xem audit toàn hệ thống.", mvp: "Chưa có token riêng" },
];

const ACCOUNTS = [
  { id: "USR-DEMO-01", name: "Nguyễn Minh An", role: "Dược sĩ duyệt", state: "đang hoạt động" },
  { id: "USR-DEMO-02", name: "Trần Hà", role: "Điều tra viên", state: "đang hoạt động" },
  { id: "USR-DEMO-03", name: "Lê Quang", role: "Quản trị", state: "đang hoạt động" },
  { id: "USR-DEMO-04", name: "Phạm Thu", role: "Điều tra viên", state: "tạm dừng" },
];

export default function AdminUsersPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Người dùng & vai trò</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Bản MVP dùng hai token vai trò dùng chung. Bảng tài khoản dưới đây là dữ liệu minh họa cho giai đoạn có xác thực
          người dùng thật.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Bốn vai trò</CardTitle>
          <Chip tone="caution">Chưa có tài khoản riêng trong MVP</Chip>
        </CardHeader>
        <CardBody className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-[13px]">
            <thead className="text-[12px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="py-2 pr-4">Vai trò</th>
                <th className="py-2 pr-4">Phạm vi</th>
                <th className="py-2">Trạng thái trong MVP</th>
              </tr>
            </thead>
            <tbody>
              {ROLES.map((role) => (
                <tr key={role.name} className="border-t border-border">
                  <td className="py-2 pr-4 font-medium text-foreground">{role.name}</td>
                  <td className="py-2 pr-4 text-muted-foreground">{role.scope}</td>
                  <td className="py-2 text-muted-foreground">{role.mvp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Tài khoản (minh họa)</CardTitle>
        </CardHeader>
        <CardBody className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-[13px]">
            <thead className="text-[12px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="py-2 pr-4">Mã</th>
                <th className="py-2 pr-4">Tên</th>
                <th className="py-2 pr-4">Vai trò</th>
                <th className="py-2">Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {ACCOUNTS.map((account) => (
                <tr key={account.id} className="border-t border-border">
                  <td className="mono py-2 pr-4 text-muted-foreground">{account.id}</td>
                  <td className="py-2 pr-4 text-foreground">{account.name}</td>
                  <td className="py-2 pr-4 text-muted-foreground">{account.role}</td>
                  <td className="py-2">
                    <Chip tone={account.state === "đang hoạt động" ? "support" : "neutral"}>{account.state}</Chip>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>
    </div>
  );
}
