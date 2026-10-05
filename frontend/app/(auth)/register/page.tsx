"use client";

import * as React from "react";
import Link from "next/link";
import { CircleAlert } from "lucide-react";
import { Alert, Button, Card, CardBody, Input, Label, Select } from "@/components/ui";

export default function RegisterPage() {
  const [submitted, setSubmitted] = React.useState(false);

  return (
    <Card className="w-full max-w-[460px]">
      <CardBody className="space-y-4">
        <div>
          <h1 className="font-display text-[24px] text-foreground">Tạo tài khoản</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">
            Tài khoản chỉ dành cho nhân viên y tế có nhiệm vụ đánh giá an toàn thuốc. Bản MVP chưa mở đăng ký.
          </p>
        </div>

        <Alert tone="caution" title="Chưa mở đăng ký trong MVP">
          Biểu mẫu này mô tả luồng sẽ có: xác minh đơn vị công tác, phê duyệt bởi quản trị viên, và gán vai trò điều tra
          viên hoặc dược sĩ duyệt.
        </Alert>

        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            setSubmitted(true);
          }}
        >
          <div>
            <Label htmlFor="full-name">Họ và tên</Label>
            <Input id="full-name" placeholder="Nguyễn Minh An" required />
          </div>
          <div>
            <Label htmlFor="work-email">Email công việc</Label>
            <Input id="work-email" type="email" placeholder="ten@donvi.vn" required />
          </div>
          <div>
            <Label htmlFor="unit">Đơn vị công tác</Label>
            <Input id="unit" placeholder="Khoa Dược — Bệnh viện …" required />
          </div>
          <div>
            <Label htmlFor="requested-role">Vai trò đề nghị</Label>
            <Select id="requested-role" defaultValue="investigator">
              <option value="investigator">Điều tra viên</option>
              <option value="reviewer">Dược sĩ duyệt</option>
            </Select>
          </div>
          {submitted ? (
            <p className="flex items-start gap-2 text-[13px] text-caution-fg">
              <CircleAlert className="mt-0.5 h-4 w-4" aria-hidden />
              Yêu cầu đã được ghi nhận cục bộ. Bản MVP không gửi dữ liệu đi đâu và không tạo tài khoản thật.
            </p>
          ) : null}
          <Button type="submit" className="w-full">
            Gửi yêu cầu
          </Button>
        </form>

        <Link href="/login" className="block text-center text-[13px] text-muted-foreground underline">
          Đã có tài khoản? Đăng nhập
        </Link>
      </CardBody>
    </Card>
  );
}
