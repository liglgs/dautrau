"use client";

import * as React from "react";
import Link from "next/link";
import { CircleAlert, RotateCcw } from "lucide-react";
import { Button, Card, CardBody } from "@/components/ui";

/** Lưới an toàn cho mọi tuyến trong không gian làm việc: lỗi hiển thị rõ thay vì màn hình trắng. */
export default function AppError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  React.useEffect(() => {
    console.error("VigiLens gặp lỗi khi hiển thị trang:", error);
  }, [error]);

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-[60ch] items-center px-6">
      <Card className="w-full">
        <CardBody className="space-y-3">
          <span className="inline-flex items-center gap-2 text-[13px] font-semibold text-contradict-fg">
            <CircleAlert className="h-4 w-4" aria-hidden /> Không hiển thị được trang
          </span>
          <h1 className="font-display text-[22px] text-foreground">Đã xảy ra lỗi khi tải dữ liệu</h1>
          <p className="text-[14px] leading-relaxed text-muted-foreground">
            Trang này không tải được. Dữ liệu điều tra vẫn nằm ở backend, bạn có thể thử lại.
          </p>
          <p className="mono break-all rounded-[var(--radius-control)] border border-border bg-muted px-3 py-2 text-[12px] text-muted-foreground">
            {error.message || "Lỗi không xác định"}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={reset}>
              <RotateCcw className="h-4 w-4" aria-hidden /> Thử lại
            </Button>
            <Link href="/app" className="text-[13px] text-muted-foreground underline-offset-4 hover:underline">
              Về dashboard
            </Link>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
