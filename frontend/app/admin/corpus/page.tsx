"use client";

import { Card, CardBody, Chip, Input } from "@/components/ui";
import { HashChip, SourceChip } from "@/components/pv/badges";
import { DEMO_DOCUMENTS } from "@/lib/mock/seed";
import { formatDateTime } from "@/lib/utils";

export default function AdminCorpusPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Kho tài liệu</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">Toàn bộ tài liệu đã lấy, kèm hash và phiên bản.</p>
      </header>

      <Card>
        <CardBody className="py-3">
          <Input placeholder="Tìm theo tiêu đề, mã tài liệu hoặc mã nguồn…" aria-label="Tìm tài liệu trong kho" />
        </CardBody>
      </Card>

      <Card>
        <CardBody className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-[13px]">
            <thead className="text-[12px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="py-2 pr-4">Mã</th>
                <th className="py-2 pr-4">Nguồn</th>
                <th className="py-2 pr-4">Tiêu đề</th>
                <th className="py-2 pr-4">Hash</th>
                <th className="py-2">Lấy lúc</th>
              </tr>
            </thead>
            <tbody>
              {DEMO_DOCUMENTS.map((document) => (
                <tr key={document.id} className="border-t border-border">
                  <td className="mono py-2 pr-4 text-muted-foreground">{document.id}</td>
                  <td className="py-2 pr-4">
                    <SourceChip source={document.source} />
                  </td>
                  <td className="py-2 pr-4 text-foreground">{document.title}</td>
                  <td className="py-2 pr-4">
                    <HashChip hash={document.sha256} status={document.hashStatus} />
                  </td>
                  <td className="py-2 text-muted-foreground">{formatDateTime(document.retrievedAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>

      <p className="text-[12px] text-muted-foreground">
        <Chip tone="neutral">MVP</Chip> Màn hình này hiển thị dữ liệu minh họa. Kho tài liệu thật nằm trong bảng
        <code className="mono"> documents</code> của backend.
      </p>
    </div>
  );
}
