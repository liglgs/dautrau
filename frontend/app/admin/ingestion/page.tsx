"use client";

import { Card, CardBody, CardHeader, CardTitle, Chip, Progress } from "@/components/ui";
import { SourceChip } from "@/components/pv/badges";
import { DEMO_INGESTION } from "@/lib/mock/seed";
import { formatDateTime } from "@/lib/utils";

const STAGE_LABEL: Record<string, string> = {
  uploaded: "đã tải lên",
  parsing: "đang tách nội dung",
  normalizing: "đang chuẩn hoá",
  hashing: "đang băm",
  indexing: "đang đánh chỉ mục",
  done: "hoàn tất",
};

const STATUS_TONE: Record<string, "support" | "caution" | "contradict" | "ai" | "neutral"> = {
  completed: "support",
  partial: "caution",
  failed: "contradict",
  running: "ai",
  queued: "neutral",
};

export default function AdminIngestionPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Nạp tài liệu</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Tài liệu công khai được lấy trong lúc agent chạy. Màn hình này theo dõi các lô nạp và tài liệu nội bộ bổ sung.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Lô nạp</CardTitle>
          <Chip tone="caution">Dữ liệu minh họa</Chip>
        </CardHeader>
        <CardBody className="space-y-3">
          {DEMO_INGESTION.map((job) => {
            const progress = job.total === 0 ? 0 : Math.round(((job.ok + job.failed) / job.total) * 100);
            return (
              <div key={job.id} className="rounded-[var(--radius-card)] border border-border px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="mono text-[12px] text-muted-foreground">{job.id}</span>
                  {job.source ? <SourceChip source={job.source} /> : null}
                  <Chip tone={STATUS_TONE[job.status] ?? "neutral"}>{job.status}</Chip>
                  <span className="text-[12px] text-muted-foreground">{STAGE_LABEL[job.stage] ?? job.stage}</span>
                  <span className="ml-auto text-[12px] text-muted-foreground">{formatDateTime(job.createdAt)}</span>
                </div>
                <Progress className="mt-2" value={progress} tone={job.status === "failed" ? "contradict" : "ai"} />
                <p className="mt-1 text-[12px] text-muted-foreground">
                  {job.ok}/{job.total} thành công · {job.failed} lỗi · tạo bởi {job.createdBy} · kiểu {job.kind}
                </p>
              </div>
            );
          })}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Quy tắc nạp</CardTitle>
        </CardHeader>
        <CardBody className="space-y-1.5 text-[13px] text-muted-foreground">
          <p>Mỗi tài liệu lưu hash SHA-256 tại thời điểm lấy; hash hiện trong trình xem nguồn.</p>
          <p>Tài liệu nội bộ được đánh dấu rõ là “nội bộ”, không trộn với nguồn công khai.</p>
          <p>Nạp lại cùng tài liệu tạo phiên bản mới thay vì ghi đè, để hồ sơ cũ vẫn truy vết được.</p>
          <p className="text-caution-fg">Màn hình này chưa nối vào backend; chưa có endpoint nạp tài liệu trong MVP.</p>
        </CardBody>
      </Card>
    </div>
  );
}
