"use client";

import * as React from "react";
import Link from "next/link";
import { CircleCheck } from "lucide-react";
import { Button, Card, CardBody, Input, Label } from "@/components/ui";

export default function ForgotPasswordPage() {
  const [sent, setSent] = React.useState(false);

  return (
    <Card className="w-full max-w-[440px]">
      <CardBody className="space-y-4">
        <div>
          <h1 className="font-display text-[24px] text-foreground">Đặt lại mật khẩu</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">
            Nhập email công việc. Bản MVP chưa gửi email; màn hình này mô tả luồng sẽ có.
          </p>
        </div>

        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            setSent(true);
          }}
        >
          <div>
            <Label htmlFor="reset-email">Email công việc</Label>
            <Input id="reset-email" type="email" placeholder="ten@donvi.vn" required />
          </div>
          <Button type="submit" className="w-full">
            Gửi liên kết đặt lại
          </Button>
        </form>

        {sent ? (
          <p className="flex items-start gap-2 text-[13px] text-support-fg">
            <CircleCheck className="mt-0.5 h-4 w-4" aria-hidden />
            Đã ghi nhận yêu cầu cục bộ. Không có email nào được gửi trong bản MVP.
          </p>
        ) : null}

        <Link href="/login" className="block text-center text-[13px] text-muted-foreground underline">
          Quay lại đăng nhập
        </Link>
      </CardBody>
    </Card>
  );
}
