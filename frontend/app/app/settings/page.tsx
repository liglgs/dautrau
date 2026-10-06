"use client";

import { Card, CardBody, CardHeader, CardTitle, Chip, Label, Select } from "@/components/ui";
import { BRAND } from "@/lib/brand";
import { DATA_MODE } from "@/lib/api";
import { useAppStore, ROLE_LABEL } from "@/lib/store/app-store";
import type { Density } from "@/lib/store/app-store";
import type { Role } from "@/lib/types";

export default function SettingsPage() {
  const { role, setRole, density, setDensity, demoMode, toggleDemoMode } = useAppStore();

  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Cài đặt</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">Tuỳ chọn hiển thị và chế độ dữ liệu của phiên làm việc này.</p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Vai trò hiển thị</CardTitle>
          <Chip tone="ai">Chế độ minh họa</Chip>
        </CardHeader>
        <CardBody className="grid gap-3 sm:grid-cols-2">
          <div>
            <Label htmlFor="role">Vai trò</Label>
            <Select disabled={DATA_MODE === "api"} id="role" value={role} onChange={(event) => setRole(event.target.value as Role)}>
              {(Object.keys(ROLE_LABEL) as Role[]).map((key) => (
                <option key={key} value={key}>
                  {ROLE_LABEL[key]}
                </option>
              ))}
            </Select>
            <p className="mt-1 text-[12px] text-muted-foreground">
              {DATA_MODE === "api" ? "Vai trò do phiên máy chủ xác định. Đăng xuất để đổi tài khoản." : "Đổi vai trò chỉ dành cho chế độ minh họa."}
            </p>
          </div>
          <div>
            <Label htmlFor="density">Mật độ bảng</Label>
            <Select id="density" value={density} onChange={(event) => setDensity(event.target.value as Density)}>
              <option value="comfortable">Thoáng</option>
              <option value="compact">Gọn</option>
            </Select>
          </div>
          <div className="sm:col-span-2 flex items-center justify-between rounded-[var(--radius-card)] border border-border px-4 py-3">
            <div>
              <p className="text-[14px] text-foreground">Nút đổi vai trò nổi</p>
              <p className="text-[12px] text-muted-foreground">Hiện ở giữa mép dưới màn hình để thử nhanh bốn vai trò.</p>
            </div>
            <button
              type="button"
              onClick={toggleDemoMode}
              aria-pressed={demoMode}
              className={"h-6 w-11 rounded-full border transition-colors " + (demoMode ? "border-ai-border bg-ai-soft" : "border-border bg-muted")}
            >
              <span className={"block h-4 w-4 rounded-full bg-foreground transition-transform " + (demoMode ? "translate-x-6" : "translate-x-1")} />
            </button>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Nguồn dữ liệu</CardTitle>
          <Chip tone={DATA_MODE === "api" ? "support" : "caution"}>{DATA_MODE === "api" ? "Backend thật" : "Dữ liệu minh họa"}</Chip>
        </CardHeader>
        <CardBody className="space-y-2 text-[13px] text-muted-foreground">
          <p>
            Đặt <code className="mono">NEXT_PUBLIC_VIGILENS_DATA_MODE=api</code> để giao diện gọi backend FastAPI qua cầu nối máy chủ{" "}
            <code className="mono">/api/backend/*</code> (biến <code className="mono">VIGILENS_API_BASE</code>). Token vai trò không bao giờ vào bundle trình duyệt.
          </p>
          <p>
            "Chế độ API dùng cookie HttpOnly từ phiên máy chủ. Mật khẩu chỉ dùng lúc đăng nhập, không được lưu trong localStorage. Vai trò hiển thị lấy từ phiên đã xác nhận, và trình duyệt không gửi vai cho máy chủ."
          </p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Về sản phẩm</CardTitle>
        </CardHeader>
        <CardBody className="space-y-1 text-[13px] text-muted-foreground">
          <p>{BRAND.name} — {BRAND.tagline}</p>
          <p>{BRAND.demoNotice}</p>
          <p>{BRAND.disclaimer}</p>
        </CardBody>
      </Card>
    </div>
  );
}
